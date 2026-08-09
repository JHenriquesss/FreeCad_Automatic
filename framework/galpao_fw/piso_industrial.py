# ============================================================================
# piso_industrial.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Dimensiona o PISO INDUSTRIAL de um galpao: placa de concreto SOBRE O SOLO
# (radier/pavimento rigido), o item mais caro e o que mais gera patologia. O solo
# e' modelado pela HIPOTESE DE WINKLER (molas lineares, q = k.w) e a placa como
# placa delgada sobre essa base elastica (Veloso & Lopes, "Fundacoes", eq. 4.75/
# 4.76: rigidez a flexao D = E.t^3 / [12(1-nu^2)]; raio de rigidez relativa
# l = (D/k)^(1/4)). As tensoes de flexao sob carga concentrada (roda de
# empilhadeira, pe de porta-palete) usam a solucao fechada classica de WESTERGAARD
# (1926, nu=0,15) para os 3 pontos criticos: INTERIOR, BORDA (junta) e CANTO. A
# resistencia de projeto e' a tracao NA FLEXAO (modulo de ruptura) do concreto pela
# NBR 6118 8.2.5 (fct = 0,7.fct,f => fct,f,d = fct,m/gamma_c = 0,3.fck^(2/3)/1,4,
# ~1,43x a tracao axial). A placa flexiona: o estado-limite e' a flexao, nao a
# tracao direta. STATELESS por design: verifica_piso(caso) recebe um dict e
# devolve espessura adotada, tensoes/utilizacao por ponto de carga, juntas e reforco
# (fibra ou tela), com gate OK/REPROVA. Dados de sitio (k do subleito, cargas de
# operacao) marcados A CONFIRMAR quando ausentes - nunca inventados.
# Unidades de ENTRADA: m, kN, MPa. Internamente a placa e' resolvida em N e mm
# (onde as formulas de Westergaard sao classicamente escritas).
# ============================================================================
"""Piso industrial de concreto (placa sobre solo de Winkler): espessura por
Westergaard (interior/borda/canto), resistencia NBR 6118, juntas e reforco.
STATELESS: verifica_piso(caso) -> gate OK/REPROVA. Fonte da placa-sobre-base:
Veloso & Lopes, Fundacoes; tensoes: Westergaard 1926; material: NBR 6118."""

from __future__ import annotations

import math

# --- constantes de material/modelo -----------------------------------------
NU_CONCRETO = 0.15              # Poisson do concreto p/ Westergaard (classico)
GAMMA_C = 1.4                   # coef. de minoracao do concreto (NBR 6118)
GAMMA_F = 1.4                   # coef. de majoracao da carga (ELU, NBR 8681)
GAMMA_CONC_KN_M3 = 25.0        # peso especifico do concreto armado
ESPESSURAS_COMERCIAIS_MM = [100, 110, 120, 130, 140, 150, 160, 180,
                            200, 220, 250, 280, 300]

# Coeficiente de reacao vertical k (subleito) por qualidade, faixa tipica
# brasileira (MN/m3). E' um DADO DE SITIO: o correto vem do ensaio de placa /
# relatorio geotecnico (Winkler, Veloso & Lopes 4.6.1). Estes sao apenas defaults
# conservadores rotulados por CBR aproximado - A CONFIRMAR em projeto real.
_K_POR_CBR = [                  # (CBR_min_%, k_MN_m3)
    (2, 20.0), (3, 27.0), (4, 35.0), (5, 42.0), (6, 48.0),
    (8, 54.0), (10, 60.0), (15, 75.0), (20, 90.0),
]


def modulo_elasticidade_concreto(fck_MPa):
    """Ecs (secante) da NBR 6118, agregado granito/gnaisse (alpha_E=1,0):
    Eci = 5600.sqrt(fck) ; Ecs = alpha_i.Eci, alpha_i = 0,8+0,2.fck/80 <= 1,0.
    Retorna MPa."""
    eci = 5600.0 * math.sqrt(fck_MPa)
    alpha_i = min(1.0, 0.8 + 0.2 * fck_MPa / 80.0)
    return alpha_i * eci


def resistencia_flexao_projeto(fck_MPa):
    """Resistencia de projeto a tracao NA FLEXAO (modulo de ruptura) da placa,
    NBR 6118 8.2.5. A placa de piso trabalha a FLEXAO, nao a tracao axial; a norma
    da fct = 0,7.fct,f (a tracao na flexao e' ~1/0,7 = 1,43x a tracao direta):
      fct,m       = 0,3.fck^(2/3)           (tracao axial media, fck<=50)
      fct,f,m     = fct,m / 0,7             (tracao na flexao media)
      fct,f,k,inf = 0,7.fct,f,m = fct,m     (caracteristico inferior, CV=0,7)
      fct,f,d     = fct,f,k,inf / gamma_c   = 0,3.fck^(2/3) / 1,4
    Retorna MPa. (Contrasta com fundacao_sapata.py, que usa a tracao AXIAL fctd
    para ancoragem/cisalhamento - la o estado-limite e' outro.)"""
    fctm = 0.3 * fck_MPa ** (2.0 / 3.0)
    fct_f_k_inf = fctm                      # = 0,7.(fct,m/0,7)
    return fct_f_k_inf / GAMMA_C


def k_por_cbr(cbr_pct):
    """Estimativa APROXIMADA do coeficiente de reacao k (MN/m3) a partir do CBR
    do subleito. Correlacao de projeto (nao substitui ensaio de placa) - marcada
    A CONFIRMAR. Retorna k em MN/m3."""
    k = _K_POR_CBR[0][1]
    for cbr_min, kk in _K_POR_CBR:
        if cbr_pct >= cbr_min:
            k = kk
    return k


def rigidez_flexao_placa(E_MPa, h_mm, nu=NU_CONCRETO):
    """D = E.h^3 / [12(1-nu^2)]  (Veloso & Lopes eq. 4.76). E em MPa=N/mm2, h em
    mm -> D em N.mm."""
    return E_MPa * h_mm ** 3 / (12.0 * (1.0 - nu ** 2))


def raio_rigidez_relativa(D_Nmm, k_MN_m3):
    """Raio de rigidez relativa l = (D/k)^(1/4) (Westergaard/Hetenyi; Veloso &
    Lopes 4.7.3). k em MN/m3 -> N/mm3 (1 MN/m3 = 1e-3 N/mm3). Retorna mm."""
    k_Nmm3 = k_MN_m3 * 1e-3
    return (D_Nmm / k_Nmm3) ** 0.25


def raio_contato_equivalente(a_mm, h_mm):
    """Raio equivalente b da area carregada (Westergaard): para carga proxima do
    tamanho da placa a formula de flexao usa um raio 'corrigido'.
    b = sqrt(1,6.a^2 + h^2) - 0,675.h  se a < 1,724.h ; senao b = a. (mm)"""
    if a_mm < 1.724 * h_mm:
        return math.sqrt(1.6 * a_mm ** 2 + h_mm ** 2) - 0.675 * h_mm
    return a_mm


def tensao_westergaard(P_N, h_mm, l_mm, b_mm, a_mm, posicao):
    """Tensao de flexao maxima sob carga concentrada P (Westergaard 1926, nu=0,15).
    posicao: 'interior' | 'borda' | 'canto'. l = raio de rigidez relativa; b = raio
    de contato equivalente (interior/borda); a = raio real da area carregada (canto).
    Retorna MPa (P em N, dimensoes em mm -> P/h^2 em N/mm2 = MPa)."""
    ph2 = P_N / h_mm ** 2
    if posicao == "interior":
        return 0.316 * ph2 * (4.0 * math.log10(l_mm / b_mm) + 1.069)
    if posicao == "borda":
        return 0.572 * ph2 * (4.0 * math.log10(l_mm / b_mm) + 0.359)
    if posicao == "canto":
        a1 = a_mm * math.sqrt(2.0)                 # distancia diagonal ao canto
        return 3.0 * ph2 * (1.0 - (a1 / l_mm) ** 0.6)
    raise ValueError("posicao invalida: %r (use interior/borda/canto)" % posicao)


def _raio_area(area_mm2=None, raio_mm=None):
    """Raio equivalente de uma area de contato (pneu/placa de apoio). Se dada a
    area, a = sqrt(area/pi)."""
    if raio_mm:
        return float(raio_mm)
    if area_mm2:
        return math.sqrt(area_mm2 / math.pi)
    raise ValueError("informe area_contato_cm2 ou raio_contato_mm da carga")


def tensoes_por_carga(carga, h_mm, E_MPa, k_MN_m3, nu=NU_CONCRETO):
    """Para UMA carga concentrada (dict: P_kN, area_contato_cm2 OU raio_contato_mm,
    posicoes=list) devolve a tensao de flexao (MPa) em cada posicao pedida.
    Aplica gamma_f (ELU) sobre P."""
    P_N = carga["P_kN"] * GAMMA_F * 1e3
    a_mm = _raio_area(area_mm2=carga.get("area_contato_cm2", 0.0) * 100.0 or None,
                      raio_mm=carga.get("raio_contato_mm"))
    D = rigidez_flexao_placa(E_MPa, h_mm, nu)
    l = raio_rigidez_relativa(D, k_MN_m3)
    b = raio_contato_equivalente(a_mm, h_mm)
    out = {}
    # DEFAULT: interior + borda. Juntas de piso industrial tem transferencia de
    # carga (barras de transferencia / intertravamento), entao 'canto' (canto LIVRE,
    # sem transferencia - o caso mais severo) e' OPT-IN: some 'canto' as posicoes
    # apenas onde ha borda livre real (portas, limites do piso).
    for pos in carga.get("posicoes", ["interior", "borda"]):
        out[pos] = tensao_westergaard(P_N, h_mm, l, b, a_mm, pos)
    return {"l_mm": l, "b_mm": b, "a_mm": a_mm, "sigma_MPa": out}


def juntas_serragem(h_mm):
    """Espacamento maximo entre juntas serradas de retracao. Pratica consagrada
    (ACI 360 / Rodrigues-IBTS): 24 a 36 x a espessura; adota-se 24.h como limite
    conservador e teto de 6,0 m. Retorna m."""
    esp_m = min(6.0, 24.0 * h_mm / 1000.0)
    return round(esp_m, 2)


def _malha_juntas(L_m, W_m, h_mm):
    """Divide o piso em paineis <= espacamento de junta; devolve grade e n paineis."""
    s = juntas_serragem(h_mm)
    nx = max(1, math.ceil(L_m / s))
    ny = max(1, math.ceil(W_m / s))
    return {"espac_max_m": s, "paineis_x": nx, "paineis_y": ny,
            "n_paineis": nx * ny, "painel_m": (round(L_m / nx, 2), round(W_m / ny, 2))}


def _reforco(h_mm, fissuras_controladas=True):
    """Reforco do piso: piso industrial moderno e' de concreto SIMPLES (a placa
    trabalha a flexao pela propria resistencia) com FIBRAS para tenacidade/retracao,
    ou tela soldada de retracao no terco superior. Retorna recomendacao + taxa.
    Dosagem de fibra de aco tipica: 20-40 kg/m3 (fornecedor A CONFIRMAR)."""
    # tela de retracao (armadura minima de pele) ~ 0,1% da secao, no terco superior
    as_min_cm2_m = 0.10e-2 * h_mm * 1000.0 / 100.0      # cm2/m de largura
    return {"tipo_recomendado": "concreto com fibras de aco (tenacidade) OU tela "
            "soldada de retracao Q no terco superior",
            "fibra_aco_kg_m3": "20 a 40 (A CONFIRMAR fornecedor/classe)",
            "tela_retracao_As_cm2_m": round(as_min_cm2_m, 2),
            "obs": "concreto SIMPLES a flexao (Westergaard); reforco controla "
                   "retracao/tenacidade, nao a flexao da placa"}


def verifica_piso(caso):
    """Dimensiona o piso industrial. caso:
      'L','W'          : dimensoes do piso (m).
      'fck_MPa'        : (default 30). concreto da placa.
      'k_MN_m3'        : coef. de reacao do subleito [A CONFIRMAR ensaio de placa].
                         Alternativamente 'cbr_pct' -> k_por_cbr (aproximado).
      'cargas'         : lista de cargas concentradas de operacao, cada uma:
                         {'nome','P_kN','area_contato_cm2' ou 'raio_contato_mm',
                          'posicoes'(opc)}. Ex.: roda de empilhadeira, pe de rack.
                         Se ausente -> A CONFIRMAR (nao inventa a carga).
      'udl_kN_m2'      : carga distribuida de estoque (opc), checada contra o solo.
      'sigma_solo_adm_kN_m2': tensao admissivel do solo p/ a UDL (opc).
    Devolve espessura adotada, utilizacao por ponto, juntas, reforco e OK.
    """
    L = caso.get("L"); W = caso.get("W")
    if not L or not W or L <= 0 or W <= 0:
        raise ValueError("[A CONFIRMAR] dimensoes do piso invalidas: L=%r W=%r" % (L, W))
    fck = caso.get("fck_MPa", 30.0)
    if fck <= 0:
        raise ValueError("[A CONFIRMAR] fck invalido: %r" % fck)
    E = modulo_elasticidade_concreto(fck)
    fctd = resistencia_flexao_projeto(fck)

    if caso.get("k_MN_m3"):
        k = float(caso["k_MN_m3"]); k_fonte = "ensaio/relatorio"
    elif caso.get("cbr_pct"):
        k = k_por_cbr(caso["cbr_pct"]); k_fonte = "CBR %g%% (correlacao A CONFIRMAR)" % caso["cbr_pct"]
    else:
        k = 35.0; k_fonte = "DEFAULT 35 MN/m3 (A CONFIRMAR - subleito nao informado)"

    cargas = caso.get("cargas")
    if not cargas:
        return {"OK": False, "motivo": "[A CONFIRMAR] cargas de operacao nao "
                "informadas (roda de empilhadeira / pe de porta-palete); a "
                "espessura do piso nao pode ser inventada.",
                "fck_MPa": fck, "k_MN_m3": k, "fctfd_MPa": round(fctd, 3)}

    # itera a espessura comercial: adota a MENOR que faz todas as tensoes <= fctd
    escolhido = None
    memoria = []
    for h in ESPESSURAS_COMERCIAIS_MM:
        pontos = []
        ok_h = True
        for c in cargas:
            res = tensoes_por_carga(c, h, E, k)
            sig = res["sigma_MPa"]
            gov_pos = max(sig, key=sig.get)
            gov = sig[gov_pos]
            util = gov / fctd
            pontos.append({"nome": c.get("nome", "carga"), "P_kN": c["P_kN"],
                           "sigma_MPa": {p: round(v, 3) for p, v in sig.items()},
                           "pos_governante": gov_pos, "sigma_gov_MPa": round(gov, 3),
                           "util": round(util, 3), "l_mm": round(res["l_mm"], 1),
                           "OK": util <= 1.0})
            if util > 1.0:
                ok_h = False
        memoria.append({"h_mm": h, "OK": ok_h,
                        "util_max": round(max(p["util"] for p in pontos), 3)})
        if ok_h:
            escolhido = {"h_mm": h, "pontos": pontos}
            break

    # UDL: verificacao geotecnica simples (pressao <= admissivel do solo)
    udl = caso.get("udl_kN_m2"); sig_solo = caso.get("sigma_solo_adm_kN_m2")
    udl_res = None
    if udl:
        peso_placa = GAMMA_CONC_KN_M3 * (escolhido["h_mm"] / 1000.0) if escolhido else 0.0
        pressao = udl + peso_placa
        udl_res = {"udl_kN_m2": udl, "pressao_total_kN_m2": round(pressao, 1),
                   "sigma_solo_adm_kN_m2": sig_solo,
                   "OK": (sig_solo is None) or (pressao <= sig_solo),
                   "nota": ("sigma_solo_adm nao informado - A CONFIRMAR"
                            if sig_solo is None else "")}

    if not escolhido:
        # nem a maior espessura comercial atende -> REPROVA (carga extrema)
        return {"OK": False, "motivo": "carga excede a maior espessura comercial "
                "(%d mm) - revisar fck, subleito (k) ou distribuir a carga" %
                ESPESSURAS_COMERCIAIS_MM[-1], "memoria": memoria,
                "fck_MPa": fck, "k_MN_m3": k, "fctfd_MPa": round(fctd, 3)}

    h = escolhido["h_mm"]
    juntas = _malha_juntas(L, W, h)
    reforco = _reforco(h)
    vol_m3 = L * W * h / 1000.0
    ok = all(p["OK"] for p in escolhido["pontos"]) and (udl_res is None or udl_res["OK"])
    return {"OK": ok, "h_mm": h, "h_cm": h / 10.0,
            "fck_MPa": fck, "E_MPa": round(E, 0), "fctfd_MPa": round(fctd, 3),
            "k_MN_m3": k, "k_fonte": k_fonte,
            "pontos": escolhido["pontos"], "udl": udl_res,
            "juntas": juntas, "reforco": reforco,
            "volume_concreto_m3": round(vol_m3, 1),
            "area_m2": round(L * W, 1),
            "norma": "Placa/Winkler: Veloso&Lopes (Fundacoes) eq.4.75/4.76; "
                     "tensoes: Westergaard 1926; material: NBR 6118 (fct,f,d 8.2.5); "
                     "juntas: ACI 360/IBTS-Rodrigues"}


# ----------------------------------- selftest --------------------------------
def _selftest():
    """Afere contra calculo manual independente (Westergaard) + monotonicidade."""
    # 1) resistencia a tracao na FLEXAO de projeto (NBR 6118 8.2.5) p/ C25:
    #    fct,f,d = fct,m/gamma_c = 0,3.25^(2/3)/1,4 (~1,83 MPa; > tracao axial 1,28)
    f = resistencia_flexao_projeto(25.0)
    assert abs(f - 0.3 * 25 ** (2 / 3) / 1.4) < 1e-9, f
    assert abs(f - 1.8321) < 5e-3, f                       # ~1,83 MPa
    assert f > 0.7 * 0.3 * 25 ** (2 / 3) / 1.4             # flexao > axial

    # 2) tensao interior aferida a mao: h=180, E=30000, k=30 MN/m3, P=30 kN roda
    #    a=100 mm ; l=(D/k)^0,25 ; sigma_i = 0,316(P/h^2)(4 log10(l/b)+1,069)
    E = 30000.0; h = 180.0; k = 30.0; a = 100.0
    D = E * h ** 3 / (12 * (1 - 0.15 ** 2))
    l = (D / (k * 1e-3)) ** 0.25
    b = math.sqrt(1.6 * a ** 2 + h ** 2) - 0.675 * h
    P = 30e3
    si = 0.316 * (P / h ** 2) * (4 * math.log10(l / b) + 1.069)
    si2 = tensao_westergaard(P, h, l, b, a, "interior")
    assert abs(si - si2) < 1e-9
    assert 1.2 < si < 1.6, si                              # ~1,40 MPa (conferido)
    # borda e canto sao MAIS severos que o interior p/ a mesma carga
    se = tensao_westergaard(P, h, l, b, a, "borda")
    sc = tensao_westergaard(P, h, l, b, a, "canto")
    assert se > si and sc > si, (si, se, sc)

    # 3) monotonia: a MESMA espessura, carga maior -> tensao (e util) maior
    cA = {"P_kN": 30.0, "area_contato_cm2": 300.0}
    cB = {"P_kN": 60.0, "area_contato_cm2": 300.0}
    sA = tensoes_por_carga(cA, 150.0, E, 35.0)["sigma_MPa"]["interior"]
    sB = tensoes_por_carga(cB, 150.0, E, 35.0)["sigma_MPa"]["interior"]
    assert sB > sA > 0, (sA, sB)
    # verifica_piso resolve uma carga moderada com espessura comercial
    base = {"L": 40.0, "W": 20.0, "fck_MPa": 30.0, "k_MN_m3": 35.0,
            "cargas": [{"nome": "empilhadeira 3t/roda", "P_kN": 30.0,
                        "area_contato_cm2": 300.0, "posicoes": ["interior", "borda"]}]}
    r1 = verifica_piso(base)
    assert r1["OK"] and r1["h_mm"] > 0, r1

    # 4) sem cargas -> A CONFIRMAR (nao inventa espessura)
    assert verifica_piso({"L": 10, "W": 10}).get("OK") is False

    # 5) juntas: 24.h, teto 6 m
    assert juntas_serragem(150) == round(min(6.0, 24 * 0.150), 2)
    assert juntas_serragem(300) == 6.0
    return True


if __name__ == "__main__":
    _selftest()
    import json
    demo = verifica_piso({"L": 40.0, "W": 20.0, "fck_MPa": 30.0, "cbr_pct": 6.0,
                          "cargas": [
                              {"nome": "roda empilhadeira 3t", "P_kN": 30.0,
                               "area_contato_cm2": 300.0},
                              {"nome": "pe porta-palete", "P_kN": 45.0,
                               "area_contato_cm2": 200.0},
                          ],
                          "udl_kN_m2": 40.0, "sigma_solo_adm_kN_m2": 200.0})
    print(json.dumps(demo, indent=2, ensure_ascii=False))
    print("selftest OK")
