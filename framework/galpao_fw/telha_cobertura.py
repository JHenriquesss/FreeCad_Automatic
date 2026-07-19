# ============================================================================
# telha_cobertura.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica a TELHA de cobertura (ou de tapamento) vencendo o VAO entre tercas.
#   Modela a telha como viga de 1 m de largura sobre apoios (as tercas):
#   ELU (flexao NBR 14762): M_Sd <= M_Rd = Wef*fy/gamma ; combinacoes de
#   gravidade (G+Q) e de sucao de vento (W + G favoravel).
#   ELS (flecha): delta <= L/180 (gravidade) e L/120 (vento), com Ief.
#   Tambem inverte as duas verificacoes -> VAO MAXIMO admissivel (tabela vao x carga).
# As propriedades da secao (Wef, Ief, peso) sao do CATALOGO do fabricante - entram
# como parametros marcados "A CONFIRMAR" (nao ha secao normativa que as fixe).
# NAO dimensiona o fixador (parafuso da telha) - so a telha entre apoios.
# ============================================================================
"""Verificacao da telha de cobertura pela ABNT NBR 14762 (perfil formado a frio),
vencendo o vao entre tercas. Metodo (flexao Wef*fy/gamma, flecha com Ief, limites
L/180 e L/120) identico ao das tercas - reaproveita as constantes. Saidas em
portugues. Unidades: m, kN, kN/m2 nas cargas; Wef em cm3/m e Ief em cm4/m (catalogo).

Propriedades da telha (Wef, Ief, peso) sao do CATALOGO do fabricante -> parametros
"A CONFIRMAR". Carga de sucao local vem de vento_nbr6123 (Cpe medio de borda/canto).
"""

from __future__ import annotations

E = 200e6          # kN/m2 - modulo de elasticidade do aco (NBR 14762)
GA = 1.10          # gamma de flexao (NBR 14762 9.8)

# Coeficientes de momento/flecha por continuidade da telha sobre as tercas.
# (viga biapoiada, 2 vaos, ou continua 3+ vaos - valores classicos de resistencia
# dos materiais para carga uniforme; o pior M e a pior flecha de cada esquema.)
_CONTINUIDADE = {
    # nome:        (coef_M,  coef_flecha)   M = cM*w*L^2 ; flecha = cD*w*L^4/(E*I)
    "simples":     (1.0 / 8.0,  5.0 / 384.0),     # 1 vao biapoiado
    "2vaos":       (1.0 / 8.0,  2.6 / 384.0),     # 2 vaos: M no apoio central = wL2/8
    "continua":    (1.0 / 10.0, 2.6 / 384.0),     # 3+ vaos: M ~ wL2/10, flecha reduzida
}


def m_rd(Wef_cm3_m, fy_MPa):
    """Momento resistente de projeto por metro de largura (NBR 14762 9.8):
    M_Rd = Wef*fy/gamma. Wef [cm3/m] -> m3/m ; fy [MPa]=1e3 kN/m2. Retorna kN*m/m."""
    Wef = Wef_cm3_m * 1e-6            # cm3/m -> m3/m
    fy = fy_MPa * 1e3                 # MPa -> kN/m2
    return Wef * fy / GA


def flecha(w_kN_m, L, Ief_cm4_m, cD):
    """Flecha da telha (1 m de largura): delta = cD*w*L^4/(E*Ief). Ief [cm4/m]->m4/m."""
    Ief = Ief_cm4_m * 1e-8           # cm4/m -> m4/m
    return cD * w_kN_m * L ** 4 / (E * Ief)


def vao_max(perfil, cfg):
    """Inverte ELU e ELS para o VAO MAXIMO admissivel (tabela vao x carga).
    ELU: cM*w*L^2 = M_Rd -> L = sqrt(M_Rd/(cM*w)).
    ELS: cD*w*L^4/(E*I) = L/lim -> L = ((E*I)/(cD*w*lim))^(1/3)."""
    import math
    fy = perfil["fy"]; Wef = perfil["Wef"]; Ief = perfil["Ief"]
    cM, cD = _CONTINUIDADE[cfg.get("continuidade", "simples")]
    g = cfg.get("gamma", {"G": 1.25, "Q": 1.50, "W": 1.40, "G_fav": 0.90})
    G = perfil["peso"] + cfg.get("G_extra", 0.0)
    Q = cfg.get("Q", 0.25)
    W = abs(cfg.get("W_sucao", 0.0))
    MRd = m_rd(Wef, fy)
    # ELU: pior de gravidade (G+Q) e sucao (W - G favoravel, tudo em modulo)
    w_grav = g["G"] * G + g["Q"] * Q
    w_upl = max(g["W"] * W - g["G_fav"] * G, 0.0)
    w_elu = max(w_grav, w_upl)
    L_elu = math.sqrt(MRd / (cM * w_elu)) if w_elu > 0 else float("inf")
    # ELS (cargas caracteristicas): gravidade lim L/180 ; vento lim L/120
    Ief_m = Ief * 1e-8
    wk_grav = G + Q
    wk_vento = W
    def _L_els(wk, lim_div):
        if wk <= 0:
            return float("inf")
        return ((E * Ief_m) / (cD * wk * lim_div)) ** (1.0 / 3.0)
    L_els_g = _L_els(wk_grav, 180.0)
    L_els_v = _L_els(wk_vento, 120.0)
    Lmax = min(L_elu, L_els_g, L_els_v)
    gov = min((("ELU", L_elu), ("ELS_grav(L/180)", L_els_g),
               ("ELS_vento(L/120)", L_els_v)), key=lambda kv: kv[1])
    return {"vao_max_m": round(Lmax, 3), "governa": gov[0],
            "L_elu": round(L_elu, 3), "L_els_grav": round(L_els_g, 3),
            "L_els_vento": round(L_els_v, 3)}


def verifica_telha(perfil, cfg):
    """Verifica a telha para o VAO dado (cfg['vao'] = espacamento das tercas).
    perfil: {Wef [cm3/m], Ief [cm4/m], peso [kN/m2], fy [MPa], t [mm], nome}.
    cfg: {vao, continuidade, Q, W_sucao, G_extra, gamma}. 1 m de largura."""
    L = cfg["vao"]
    cM, cD = _CONTINUIDADE[cfg.get("continuidade", "simples")]
    g = cfg.get("gamma", {"G": 1.25, "Q": 1.50, "W": 1.40, "G_fav": 0.90})
    G = perfil["peso"] + cfg.get("G_extra", 0.0)
    Q = cfg.get("Q", 0.25)
    W = abs(cfg.get("W_sucao", 0.0))
    MRd = m_rd(perfil["Wef"], perfil["fy"])
    # ---- ELU: flexao ------------------------------------------------------
    w_grav = g["G"] * G + g["Q"] * Q          # kN/m (faixa de 1 m)
    w_upl = max(g["W"] * W - g["G_fav"] * G, 0.0)
    combos = {"gravidade (1,25G+1,50Q)": w_grav, "sucao (1,40W-0,90G)": w_upl}
    elu = {}
    for nome, w in combos.items():
        M = cM * w * L ** 2
        elu[nome] = {"w": round(w, 3), "M_Sd": round(M, 4),
                     "util": round(M / MRd, 3) if MRd > 0 else float("inf"),
                     "ok": M <= MRd}
    util_elu = max(v["util"] for v in elu.values())
    # ---- ELS: flecha (cargas caracteristicas) -----------------------------
    d_grav = flecha(G + Q, L, perfil["Ief"], cD)
    d_vento = flecha(W, L, perfil["Ief"], cD)
    els = {"d_grav": round(d_grav * 1000, 2), "lim_grav_mm": round(L / 180.0 * 1000, 2),
           "ok_grav": d_grav <= L / 180.0,
           "d_vento": round(d_vento * 1000, 2), "lim_vento_mm": round(L / 120.0 * 1000, 2),
           "ok_vento": d_vento <= L / 120.0}
    ok = (util_elu <= 1.0) and els["ok_grav"] and els["ok_vento"]
    return {"perfil": perfil.get("nome", "telha"), "vao": L, "M_Rd": round(MRd, 4),
            "elu": elu, "util_elu": util_elu, "els": els, "OK": ok,
            "ilustrativo": bool(perfil.get("ilustrativo", False)),
            "tipo": perfil.get("tipo"), "vao_max": vao_max(perfil, cfg)}


def relatorio_pt(r):
    L = ["TELHA DE COBERTURA (ABNT NBR 14762 - formado a frio, vao entre tercas)",
         f"  Perfil: {r['perfil']} ; vao (espacamento das tercas) = {r['vao']:.2f} m",
         f"  M_Rd = Wef*fy/gamma = {r['M_Rd']:.4f} kN*m/m",
         "  ELU (flexao, faixa de 1 m):"]
    for nome, e in r["elu"].items():
        L.append(f"    {nome}: w={e['w']:.3f} kN/m ; M_Sd={e['M_Sd']:.4f} ; "
                 f"util={e['util']:.3f} {'OK' if e['ok'] else 'REPROVA'}")
    el = r["els"]
    L += [f"  ELS (flecha, cargas caracteristicas):",
          f"    gravidade: {el['d_grav']:.2f} mm <= L/180={el['lim_grav_mm']:.2f} mm "
          f"{'OK' if el['ok_grav'] else 'REPROVA'}",
          f"    vento    : {el['d_vento']:.2f} mm <= L/120={el['lim_vento_mm']:.2f} mm "
          f"{'OK' if el['ok_vento'] else 'REPROVA'}"]
    vm = r["vao_max"]
    L += [f"  VAO MAXIMO admissivel = {vm['vao_max_m']:.3f} m (governa {vm['governa']}: "
          f"ELU={vm['L_elu']:.2f} / ELS_g={vm['L_els_grav']:.2f} / ELS_v={vm['L_els_vento']:.2f})",
          f"  RESULTADO: {'APROVADA' if r['OK'] else 'REPROVADA'} (util ELU {r['util_elu']:.3f})"]
    if r.get("ilustrativo"):
        L += [f"  [!] PERFIL ILUSTRATIVO por tipo '{r.get('tipo','?')}' (Wef/Ief NAO",
              "      sao de catalogo real) - informe as props do fabricante no spec"]
    L += ["  [A CONFIRMAR: Wef, Ief e peso do CATALOGO do fabricante da telha; a",
          "   continuidade (n de vaos); a sobrecarga Q e a sucao local W do vento.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


# Exemplo de perfil de telha (trapezoidal 40 mm, 0,65 mm) - VALORES ILUSTRATIVOS,
# A CONFIRMAR com o catalogo do fabricante. NAO sao valores normativos.
TELHA_EXEMPLO = {"nome": "Trapezoidal 40/0,65 (exemplo)", "Wef": 7.5, "Ief": 18.0,
                 "peso": 0.06, "fy": 280.0, "t": 0.65}

# Catalogo ILUSTRATIVO por TIPO de telha (o campo cobertura.telha_tipo do wizard).
# Ordem fisica de rigidez: ondulada (perfil raso) < trapezoidal < sanduiche (peles
# separadas pelo nucleo). VALORES ILUSTRATIVOS, NAO normativos e NAO de fabricante:
# servem para o gate DIFERENCIAR os tipos (uma telha mais fraca exige tercas mais
# proximas) enquanto o eng nao informa Wef/Ief/peso do CATALOGO real. Todos marcados
# `ilustrativo=True` -> o relatorio flag "A CONFIRMAR". Conservador de proposito
# (Wef/Ief da ondulada baixos) para NAO sub-prover tercas. Sobrescrever com o
# catalogo do fabricante via spec (fundacao.telha.perfil) sempre que disponivel.
_CATALOGO_TELHA = {
    "ondulada":    {"nome": "Ondulada 17/0,50 (ilustrativo)", "Wef": 3.0, "Ief": 5.0,
                    "peso": 0.05, "fy": 250.0, "t": 0.50},
    "trapezoidal": {"nome": "Trapezoidal 40/0,65 (ilustrativo)", "Wef": 7.5, "Ief": 18.0,
                    "peso": 0.06, "fy": 280.0, "t": 0.65},
    "sanduiche":   {"nome": "Sanduiche 30/0,50 (ilustrativo)", "Wef": 15.0, "Ief": 50.0,
                    "peso": 0.11, "fy": 280.0, "t": 0.50},
}


def catalogo_por_tipo(telha_tipo, peso_override=None):
    """Perfil ILUSTRATIVO da telha a partir do tipo (cobertura.telha_tipo). Se
    `peso_override` (kN/m2) vier do spec (cobertura.telha_peso, dado real do
    usuario), ele SUBSTITUI o peso ilustrativo. Retorna dict com `ilustrativo=True`
    (o gate deixa claro que Wef/Ief sao a CONFIRMAR com o catalogo do fabricante).
    Tipo desconhecido -> trapezoidal (default do wizard)."""
    base = _CATALOGO_TELHA.get(str(telha_tipo).strip().lower(),
                               _CATALOGO_TELHA["trapezoidal"])
    perfil = dict(base)
    perfil["ilustrativo"] = True
    perfil["tipo"] = str(telha_tipo)
    if peso_override not in (None, 0) and peso_override > 0:
        perfil["peso"] = float(peso_override)
    return perfil


def _selftest():
    import math
    # M_Rd: Wef=7,5 cm3/m, fy=280 MPa, gamma 1,10
    MRd = m_rd(7.5, 280.0)
    assert abs(MRd - 7.5e-6 * 280e3 / 1.10) < 1e-9, MRd     # = 1,9090... kN*m/m
    # vao 1,67 m, sucao local -2,203 kN/m2 (do vento §8), biapoiada
    cfg = {"vao": 1.67, "continuidade": "simples", "Q": 0.25, "W_sucao": -2.203}
    r = verifica_telha(TELHA_EXEMPLO, cfg)
    # combos batem com a mao
    w_g = 1.25 * 0.06 + 1.50 * 0.25
    w_u = 1.40 * 2.203 - 0.90 * 0.06
    assert abs(r["elu"]["gravidade (1,25G+1,50Q)"]["w"] - round(w_g, 3)) < 1e-9, r
    assert abs(r["elu"]["sucao (1,40W-0,90G)"]["w"] - round(w_u, 3)) < 1e-9, r
    # sucao governa (|W| >> G+Q); M_Sd = wL2/8
    M_u = w_u * 1.67 ** 2 / 8.0
    assert abs(r["elu"]["sucao (1,40W-0,90G)"]["M_Sd"] - round(M_u, 4)) < 1e-4, r
    # vao_max coerente: reduz o vao ate passar
    vm = r["vao_max"]["vao_max_m"]
    assert vm > 0 and math.isfinite(vm), r
    # no vao_max, util ELU ~ 1 OU flecha no limite (governante)
    r2 = verifica_telha(TELHA_EXEMPLO, {**cfg, "vao": vm})
    assert r2["util_elu"] <= 1.001, r2
    # sanidade: vao curto passa, vao longo reprova
    assert verifica_telha(TELHA_EXEMPLO, {**cfg, "vao": vm * 0.8})["OK"]
    assert not verifica_telha(TELHA_EXEMPLO, {**cfg, "vao": vm * 1.3})["OK"]
    print("telha self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        cfg = {"vao": 1.67, "continuidade": "simples", "Q": 0.25, "W_sucao": -2.203}
        print(relatorio_pt(verifica_telha(TELHA_EXEMPLO, cfg)))
