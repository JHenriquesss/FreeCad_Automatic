# ============================================================================
# rodar_galpao.py - ORQUESTRADOR PARAMETRICO da cadeia de calculo (Gates 5-9)
# Recebe os PARAMETROS do projeto (respostas dos gates), configura os modulos
# (geometria, base, perfis, terca), roda a cadeia na ordem dos gates e emite um
# memorial por modulo + o consolidado. EXTRAI os esforcos de base e de joelho do
# proprio portico (nao hardcoded), entao serve para QUALQUER geometria.
# Modulos: vento_nbr6123, galpao_portico, estabilidade_b1b2, check_nbr8800,
# tercas_iteracao (+distorcional_fsm), base_chumbador, ligacoes.
# Nao redefine metodo - so orquestra os modulos ja validados. Saidas em PT.
# ============================================================================
"""Orquestrador do fluxo de calculo do galpao. Um projeto = um dict de params."""

from __future__ import annotations

import math
import os

import vento_nbr6123 as vento
import galpao_portico as gp
import estabilidade_b1b2 as est
import check_nbr8800 as chk
import tercas_iteracao as ti
import base_chumbador as bc
import ligacoes as lg
import mao_francesa as maofr
import secundarios_nbr8800 as secmod
import contraventamento as ctv
import ponte_rolante as pr

# --- combinacoes (mesmas do portico/estabilidade) para extrair reacoes -------
_COMB = {"C1_grav": {"G": 1.25, "Q": 1.50, "W2": 0.6 * 1.40},
         "C2_uplift": {"G": 1.00, "W1": 1.40},
         "C3_Gdesf": {"G": 1.25, "W2": 1.40, "Q": 0.8 * 1.50},
         "C3_Gfav": {"G": 1.00, "W2": 1.40}}


def _casos_mf_reac():
    """member-forces e reacoes por caso base (G, Q, W1, W2)."""
    out = {}
    for nm, fn in (("G", gp.case_G), ("Q", gp.case_Q)):
        fr, ix = gp._frame(); fn(fr, ix); _, mf = fr.solve()
        out[nm] = (mf, fr.reactions(), ix)
    for nm, key in (("W1", "portao_barlavento"), ("W2", "portao_sotavento")):
        apply, _ = gp._wind(key)
        fr, ix = gp._frame(); apply(fr, ix); _, mf = fr.solve()
        out[nm] = (mf, fr.reactions(), ix)
    if gp.PONTE:
        fr, ix = gp._frame(); gp.case_ponte(fr, ix); _, mf = fr.solve()
        out["PONTE"] = (mf, fr.reactions(), ix)
    return out


def _esforcos_base_joelho():
    """Extrai (por combinacao) os esforcos de base e de joelho do portico atual.
    Retorna o caso de base governante (max |M|) e o de joelho (max |M|)."""
    casos = _casos_mf_reac()
    _, _, ix = casos["G"]
    nbL = ix["nBaseL"]
    eKnee = ix["colL"][-1]
    combos = gp._combos_elu(gp.PONTE)      # envelope (cruza W1 e W2)
    base_best = knee_best = None
    for nm, c in combos.items():
        R = sum(fac * casos[cs][1] for cs, fac in c.items())
        N, V, M = R[3 * nbL + 1], R[3 * nbL], R[3 * nbL + 2]
        if base_best is None or abs(M) > abs(base_best[3]):
            base_best = (nm, N, V, M)
        f = sum(fac * casos[cs][0][eKnee] for cs, fac in c.items())
        Mk, Vk, Nk = f[5], f[4], -f[3]
        if knee_best is None or abs(Mk) > abs(knee_best[3]):
            knee_best = (nm, Nk, Vk, Mk)
    return base_best, knee_best


def rodar(params, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    def save(nome, txt):
        with open(os.path.join(out_dir, nome), "w", encoding="utf-8") as f:
            f.write(txt + "\n")
        return txt

    g = params["geometria"]
    sc = params["secoes"]
    # configura geometria + perfis + base
    gp.configurar(span=g["span"], eave=g["eave"], ridge=g["ridge"], bay=g["bay"],
                  base_fixed=params.get("base_fixed", True),
                  A_col=sc["A_col"], I_col=sc["I_col"],
                  A_raf=sc["A_raf"], I_raf=sc["I_raf"],
                  G_roof=params["cargas"]["G"], rafter_self=params["cargas"]["self"],
                  Q_roof=params["cargas"]["Q"])
    ti.configurar(bay=g["bay"], ly=g["bay"] / 2.0,
                  trib=params["terca"]["trib"], theta=gp.THETA,
                  fy=params["terca"]["fy"])
    if params.get("vento"):                       # parametros de sitio (Gate 5)
        vt = params["vento"]
        vento.configurar(v0=vt.get("v0"), cat=vt.get("cat"), classe=vt.get("classe"),
                         s1=vt.get("s1"), s3=vt.get("s3"), z=vt.get("z"),
                         theta=math.degrees(gp.THETA))

    res = {}
    # Ponte rolante (opcional): calcula a acao e injeta a reacao no portico como
    # caso de carga + combinacoes (C4/C5). Sem "ponte" nos params -> galpao SEM
    # ponte, portico identico a referencia.
    if params.get("ponte"):
        pcfg = dict(params["ponte"]); pcfg.setdefault("vao_viga", g["bay"])
        pcfg.setdefault("vao_ponte", g["span"] - pcfg.get("folga_trilho", 0.5))
        esf, viga, reac = pr.analisa(pcfg)
        save("gate5-ponte.txt", pr.relatorio_pt(esf, viga, reac))
        gp.configurar(ponte={"R_vert": reac["R_vertical_kN"],
                             "M_exc": reac["M_excentrico_kNm"],
                             "H_transv": reac["H_transversal_kN"],
                             "Hvr": pcfg["Hvr"]})
        res["ponte_R_vert"] = round(reac["R_vertical_kN"], 1)
        res["ponte_viga_inter"] = round(viga["inter"], 2)
    else:
        gp.configurar(ponte=False)
    # Gate 5 - vento (transversal + longitudinal)
    save("gate5-vento.txt", vento.relatorio_pt(vento.compute()))
    vl = vento.compute_longitudinal(b=g["span"], eave=g["eave"], ridge=g["ridge"],
                                    ca=params.get("ca_arrasto", 1.2))
    save("gate5-vento-longitudinal.txt", vento.relatorio_longitudinal_pt(vl))
    res["Fa_long_kN"] = vl["Fa_kN"]; res["Fa_por_lado_kN"] = vl["Fa_por_lado_kN"]
    # Gate 6 - analise
    save("gate6-portico.txt", gp.memoria_pt(gp.analyse()))
    a = est.analyse()
    save("gate6-2a-ordem.txt", est.memoria_pt(a))
    # Gate 7 - mao-francesa: define o Lb da viga (contencao da mesa inferior)
    # pela inversao da interacao. Combo governante = maior |Msd| na viga.
    slope = (g["ridge"] - g["eave"]) / (g["span"] / 2.0)
    n_terca = params["terca"].get("n_por_agua", 3)
    cbm = max(a["combos"], key=lambda r: abs(r["viga"]["Msd"]))
    plano_mf = maofr.plano_mao_francesa(
        sc["perfil_raf"], params["fy"], max(0.0, cbm["viga"]["Nsd"]),
        abs(cbm["viga"]["Msd"]), abs(cbm["viga"]["Vsd"]),
        span=g["span"], slope=slope, n_terca=n_terca)
    save("gate7-mao-francesa.txt", maofr.relatorio_pt(plano_mf, "viga (mesa inferior)"))
    Lb_raf = plano_mf["Lb_usado"] if plano_mf.get("ok") else params["Lb"]["raf"]
    res["mf_bracos_portico"] = plano_mf.get("n_bracos_portico")
    res["mf_stride"] = plano_mf.get("stride")
    res["Lb_raf"] = round(Lb_raf, 3)
    # Gate 7 - perfis (Lb da viga vem da mao-francesa; coluna e parametro)
    pecas = {"coluna": (sc["perfil_col"], est.SEC["coluna"]["L"], params["Lb"]["col"]),
             "viga": (sc["perfil_raf"], est.SEC["viga"]["L"], Lb_raf)}
    finais = []
    for gname, (sec, Lr, Lb) in pecas.items():
        cands = [chk.verifica(sec, params["fy"], L=Lr, Nsd=r[gname]["Nsd"],
                              Msd=r[gname]["Msd"], Vsd=r[gname]["Vsd"], Kx=1, Ky=1,
                              Lb=Lb, nome=f"{gname.capitalize()} (K=1; gov {r['nome']})")
                 for r in a["combos"]]
        finais.append(max(cands, key=lambda x: x["interacao"]))
    save("gate7-check-perfis.txt", chk.relatorio_pt(finais, params["fy"]))
    res["interacao_col"] = finais[0]["interacao"]
    res["interacao_raf"] = finais[1]["interacao"]
    # Gate 7 - tercas
    save("gate7-tercas.txt", ti.memoria_pt())
    # Gate 7 - pecas secundarias (longarina de parede U + escora/cumeeira I)
    vr = vento.compute()
    net_par = [abs(vr["net"][c][s]) for c in vr["net"] for s in vr["net"][c]
               if s.startswith("parede")]
    sp = dict(params["secundarios"])
    sp["longarina"]["vao"] = g["bay"]; sp["escora"]["vao"] = g["bay"]
    sp["longarina"]["q_vento"] = max(net_par) * vr["q_kN_m2"]
    sp["escora"]["Nsd"] = vl["Fa_por_lado_kN"]     # axial = arrasto longitudinal/lado
    rl = secmod.verifica_longarina(sp["perfil_long"], params["fy"], sp["longarina"])
    re_ = secmod.verifica_escora(sp["perfil_esc"], params["fy"], sp["escora"])
    # Montante de oitao: n postos no oitao -> trib e altura governante da empena
    n_mont = params["secundarios"].get("n_montantes_oitao", 2)
    trib_m = g["span"] / (n_mont + 1)
    y_gov = trib_m if trib_m <= g["span"] / 2 else g["span"] - trib_m
    h_gov = g["eave"] + (g["ridge"] - g["eave"]) / (g["span"] / 2) * min(y_gov, g["span"] - y_gov)
    net_oit = max(abs(vl["net"][c][s]) for c in vl["net"] for s in vl["net"][c]
                  if s.startswith("oitao"))
    cfg_m = dict(params["secundarios"].get("montante", {}))
    cfg_m.update(altura=round(h_gov, 2), q_gable=net_oit * vl["q_kN_m2"], trib=trib_m,
                 nome="Montante de oitao (HEA160)")
    rm = secmod.verifica_montante_oitao(sp["perfil_esc"], params["fy"], cfg_m)
    save("gate7-secundarios.txt", "\n\n".join(secmod.relatorio_pt(x)
                                              for x in (rl, re_, rm)))
    res["longarina_inter"] = rl.get("inter"); res["longarina_ok"] = rl["OK"]
    res["escora_inter"] = re_["interacao"]; res["escora_ok"] = re_["OK"]
    res["montante_inter"] = rm["interacao"]; res["montante_ok"] = rm["OK"]
    # Gate 7 - barras tracionadas (contraventamento + mao-francesa), forca do Fa
    cb = params["barras"]; fyb, fub = cb["fy"], cb["fu"]
    Fp = vl["Fa_por_lado_kN"]
    Ndp, Ldp = ctv.n_diagonal(Fp, g["bay"], g["eave"])           # parede
    Ndc, Ldc = ctv.n_diagonal(Fp, g["bay"], g["span"] / 2.0)     # cobertura
    Nmf = ctv.forca_estabilizacao_2pct(abs(cbm["viga"]["Msd"]), sc["d_raf"])
    barras = [
        ctv.verifica_barra("Contravento de parede (d20)", cb["d_contrav"], fyb, fub,
                           Ndp, Ldp, pretensionada=True),
        ctv.verifica_barra("Contravento de cobertura (d20)", cb["d_contrav"], fyb, fub,
                           Ndc, Ldc, pretensionada=True),
        ctv.verifica_barra("Tirante de cobertura (d16)", cb["d_tirante"], fyb, fub,
                           cb["Nsd_tirante"], g["bay"] / 2.0, pretensionada=True),
        ctv.verifica_barra("Mao-francesa (d16)", cb["d_tirante"], fyb, fub, Nmf, 0.40)]
    save("gate7-contraventamento.txt", ctv.relatorio_pt(barras))
    res["barras_ok"] = all(x["OK"] for x in barras)
    res["barras_u_max"] = max(x["u"] for x in barras)
    # Gate 7 - verga da porta (UPE100 sobre o vao da abertura): flexao do U, vao
    # = largura da porta, sem tirante (Lb = vao). Vento na parede + peso da porta.
    vg = dict(params["verga"]); vg["q_vento"] = max(net_par) * vr["q_kN_m2"]
    rv = secmod.verifica_longarina(sp["perfil_long"], params["fy"], vg)
    save("gate7-verga.txt", secmod.relatorio_pt(rv))
    res["verga_inter"] = rv.get("inter"); res["verga_ok"] = rv["OK"]
    # Gate 7 - base + ligacoes (esforcos extraidos do portico)
    (bnm, bN, bV, bM), (knm, kN, kV, kM) = _esforcos_base_joelho()
    res["base_gov"] = (bnm, round(bN, 1), round(bV, 1), round(bM, 1))
    res["knee_gov"] = (knm, round(kN, 1), round(kV, 1), round(kM, 1))
    b = dict(params["base"])
    b.update(N=abs(bN) if bN > 0 else bN, V=abs(bV), M=abs(bM),
             nome=f"Base engastada - {bnm} (M={abs(bM):.1f})")
    save("gate7-base.txt", bc.relatorio_pt(bc.verifica_base(b), b))
    dr = sc["d_raf"]; tf = sc["tf_raf"]
    Tf = abs(kM) / (dr - tf) + abs(kN) / 2.0
    knee = dict(params["joelho"]); knee.update(N=Tf, V=abs(kV) * 4 / 8.0,
                                               nome=f"Joelho - {knm} (M={abs(kM):.1f})")
    clip = params["clip_terca"]
    save("gate7-ligacoes.txt", lg.relatorio_pt([lg.verifica_ligacao(knee),
                                                lg.verifica_ligacao(clip)]))
    # Gate 9 - consolidado
    _consolidar(out_dir, save, g, params)
    return res


def _consolidar(out_dir, save, g, params):
    ordem = [("1. VENTO", "gate5-vento.txt"),
             ("1b. VENTO LONGITUDINAL", "gate5-vento-longitudinal.txt"),
             ("1c. PONTE ROLANTE", "gate5-ponte.txt"),
             ("2. PORTICO 1a ORDEM", "gate6-portico.txt"),
             ("3. 2a ORDEM (MAES)", "gate6-2a-ordem.txt"), ("4. PERFIS", "gate7-check-perfis.txt"),
             ("5. MAO-FRANCESA", "gate7-mao-francesa.txt"), ("6. TERCAS", "gate7-tercas.txt"),
             ("7. SECUNDARIOS", "gate7-secundarios.txt"),
             ("8. CONTRAVENTAMENTO", "gate7-contraventamento.txt"),
             ("9. VERGA DA PORTA", "gate7-verga.txt"),
             ("10. BASE", "gate7-base.txt"), ("11. LIGACOES", "gate7-ligacoes.txt")]
    L = ["=" * 70, f"MEMORIAL CONSOLIDADO - GALPAO {g['comprimento']:.0f}x{g['span']:.0f} m",
         "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL", "=" * 70, ""]
    if not params.get("ponte"):
        ordem = [x for x in ordem if x[1] != "gate5-ponte.txt"]
    for tit, f in ordem:
        p = os.path.join(out_dir, f)
        body = open(p, encoding="utf-8").read().rstrip() if os.path.exists(p) else "(falta)"
        L += ["#" * 70, tit, "#" * 70, "", body, "", ""]
    save("MEMORIAL-CONSOLIDADO.txt", "\n".join(L))


# --- params de referencia (galpao 20x10, base engastada) --------------------
PARAMS_REF = {
    "geometria": {"span": 10.0, "comprimento": 20.0, "eave": 6.0, "ridge": 6.5, "bay": 5.0},
    "base_fixed": True, "fy": 250e3, "ca_arrasto": 1.2,  # Ca Figura 4 (A CONFIRMAR)
    "secoes": {"perfil_col": chk.HEA200, "perfil_raf": chk.HEA180,
               "A_col": 53.8e-4, "I_col": 3692e-8, "A_raf": 45.3e-4, "I_raf": 2510e-8,
               "d_raf": 0.171, "tf_raf": 0.0095},
    "cargas": {"G": 0.27, "self": 0.35, "Q": 0.25},
    "Lb": {"col": 2.0, "raf": 1.67},
    "terca": {"trib": 1.675, "fy": 250e3, "n_por_agua": 3},
    # Pecas secundarias (gate: trib, tapamento, n_tirantes, Nsd escora = A CONFIRMAR)
    "secundarios": {
        "perfil_long": secmod.UPE100, "perfil_esc": secmod.HEA160,
        "longarina": {"vao": 5.0, "q_vento": None, "trib": 2.0, "g_tapamento": 0.10,
                      "peso_proprio": 0.10, "n_tirantes": 2, "continua": False},
        # Nsd da escora e SOBRESCRITO pelo arrasto longitudinal (Fa/lado).
        "escora": {"vao": 5.0, "Nsd": 60.0, "peso_proprio": 0.31, "Lb": 5.0,
                   "nome": "Escora de beiral / cumeeira (HEA160)"},
        # Montante de oitao: altura/trib/q_gable vem da geometria + vento long.
        "n_montantes_oitao": 2,
        "montante": {"Nsd": 5.0, "Lb": 2.0}},
    # Barras tracionadas (aco MR250). Nsd_tirante = componente do peso na agua
    # (A CONFIRMAR); demais forcas vem do Fa e do Msd da viga.
    "barras": {"fy": 250e3, "fu": 400e3, "d_contrav": 0.020, "d_tirante": 0.016,
               "Nsd_tirante": 8.0},
    # Verga da porta (UPE100 sobre a abertura). vao = largura da porta (gate).
    "verga": {"vao": 0.90, "trib": 2.0, "g_tapamento": 0.15, "peso_proprio": 0.10,
              "n_tirantes": 0, "continua": False, "nome": "Verga da porta (UPE100)"},
    "base": {"fck": 25e3, "B": 0.45, "L": 0.55, "A2": 0.60 * 0.70, "n_chumbadores": 4,
             "n_tracionados": 2, "db": 0.020, "fub": 400e3, "d_col": 0.190,
             "bf_col": 0.200, "beff_tracao": 0.200, "d_anchor": 0.50, "borda": 0.05,
             "fy_placa": 250e3, "t_placa": 0.040, "rosca_no_plano": True},
    "joelho": {"tipo": "parafusos", "n": 4, "db": 0.024, "fub": 825e3,
               "t_chapa": 0.0125, "fu_chapa": 400e3, "lf": 0.040, "rosca_no_plano": True},
    "clip_terca": {"nome": "Chapa de terca (2 M12) - excecao", "tipo": "parafusos",
                   "n": 2, "db": 0.012, "fub": 400e3, "t_chapa": 0.006,
                   "fu_chapa": 400e3, "lf": 0.025, "V": 8.0, "excecao_terca": True},
    # "ponte": None -> galpao SEM ponte (portico identico a referencia).
}


def params_com_ponte():
    """PARAMS_REF + uma ponte rolante de 100 kN (exemplo; dados A CONFIRMAR do
    fabricante/NBR 8400). Demonstra o galpao COM ponte de ponta a ponta."""
    import copy
    p = copy.deepcopy(PARAMS_REF)
    p["ponte"] = {"Q": 100.0, "peso_ponte": 60.0, "peso_trole": 15.0,
                  "aprox_min": 1.0, "n_rodas_lado": 2, "phi": 1.10,
                  "frac_lateral": 0.10, "frac_long": 0.10, "d_rodas": 3.0,
                  "fy": 250e3, "perfil_viga": pr.VS500, "siderurgica": False,
                  "excentricidade": 0.30, "Hvr": 4.5,
                  "E_Ix": pr.ck.E * pr.VS500["Ix"]}
    return p


if __name__ == "__main__":
    import sys
    com_ponte = "--ponte" in sys.argv
    P = params_com_ponte() if com_ponte else PARAMS_REF
    out = os.path.join(os.path.dirname(__file__), "..", "exports",
                       "memoria-ponte" if com_ponte else "memoria-orq")
    r = rodar(P, os.path.abspath(out))
    print(f"RESUMO (20x10 engastado{' + PONTE 100 kN' if com_ponte else ''}):")
    if com_ponte:
        print(f"  ponte: R_vert={r['ponte_R_vert']} kN ; viga de rolamento "
              f"interacao={r['ponte_viga_inter']}")
    print(f"  interacao coluna = {r['interacao_col']:.2f} (ref 0,67 s/ ponte)")
    print(f"  interacao viga   = {r['interacao_raf']:.2f} (ref 0,93 c/ Lb da mao-francesa)")
    print(f"  mao-francesa     = {r['mf_bracos_portico']} bracos/portico ; "
          f"1 a cada {r['mf_stride']} terca(s) ; Lb={r['Lb_raf']} m")
    print(f"  longarina UPE100 = {r['longarina_inter']:.2f} "
          f"({'OK' if r['longarina_ok'] else 'NAO'}, 2 tirantes de parede)")
    print(f"  vento long. Fa   = {r['Fa_long_kN']:.1f} kN (arrasto) ; "
          f"{r['Fa_por_lado_kN']:.1f} kN/lado -> Nsd escora")
    print(f"  escora HEA160    = {r['escora_inter']:.2f} "
          f"({'OK' if r['escora_ok'] else 'NAO'})")
    print(f"  montante oitao   = {r['montante_inter']:.2f} "
          f"({'OK' if r['montante_ok'] else 'NAO'}, HEA160)")
    print(f"  barras tracao    = u_max {r['barras_u_max']:.2f} "
          f"({'OK' if r['barras_ok'] else 'NAO'}, contrav.+tirante+mao-francesa)")
    print(f"  verga da porta   = {r['verga_inter']:.2f} "
          f"({'OK' if r['verga_ok'] else 'NAO'}, UPE100)")
    print(f"  base governa     = {r['base_gov']}")
    print(f"  joelho governa   = {r['knee_gov']}")
    print(f"  memoriais em: {os.path.abspath(out)}")
