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
import perfis
import redimensionamento as redim
import tercas_iteracao as ti
import base_chumbador as bc
import fundacao_sapata as fs
import junta_dilatacao as jd
import sismo_nbr15421 as sismo
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


def _casos_base_envelope():
    """Todos os casos de base (por combinacao ELU) como lista (nome, N, V, M) -
    para o ENVELOPE da sapata (bearing pega N max; tombamento pega N min + M)."""
    casos = _casos_mf_reac()
    _, _, ix = casos["G"]
    nbL = ix["nBaseL"]
    combos = gp._combos_elu(gp.PONTE)
    out = []
    for nm, c in combos.items():
        R = sum(fac * casos[cs][1] for cs, fac in c.items())
        N, V, M = R[3 * nbL + 1], R[3 * nbL], R[3 * nbL + 2]
        out.append((nm, N, V, M))
    return out


def rodar(params, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    def save(nome, txt):
        with open(os.path.join(out_dir, nome), "w", encoding="utf-8") as f:
            f.write(txt + "\n")
        return txt

    gp.reset(); vento.reset()          # estado limpo (sem vazamento entre projetos)
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
    save("gate5-vento.txt", vento.relatorio_pt(vento.compute(
        larg_b=g["span"], alt_h=g["eave"], comp_a=g.get("comprimento", 2 * g["span"]))))
    vl = vento.compute_longitudinal(b=g["span"], eave=g["eave"], ridge=g["ridge"],
                                    ca=params.get("ca_arrasto", 1.2))
    save("gate5-vento-longitudinal.txt", vento.relatorio_longitudinal_pt(vl))
    res["Fa_long_kN"] = vl["Fa_kN"]; res["Fa_por_lado_kN"] = vl["Fa_por_lado_kN"]
    # Gate 6 - analise
    save("gate6-portico.txt", gp.memoria_pt(gp.analyse()))
    a = est.analyse()
    save("gate6-2a-ordem.txt", est.memoria_pt(a))
    # Gate 7 - REDIMENSIONAMENTO: adota o par (coluna, viga) MAIS LEVE que passa
    # (interacao<=1 + flecha<=H/150), partindo do seed HEA200/HEA180. Recomputa os
    # esforcos com o perfil adotado -> tudo a jusante (mao-francesa, check, modelo)
    # usa o perfil que ATENDE. Referencia 20x10 ja passa no seed -> inalterada.
    adoc = redim.melhor(fixed=params.get("base_fixed", True),
                        lb_col=params["Lb"]["col"], lb_raf=params["Lb"]["raf"],
                        seed=("HEA200", "HEA180"))
    save("gate7-redimensionamento.txt", adoc["tabela"])
    if adoc["aprovado"]:
        ap = adoc["aprovado"]
        sc["perfil_col"] = perfis.PERFIS[ap["col"]]
        sc["perfil_raf"] = perfis.PERFIS[ap["raf"]]
        a = est.analyse()                       # esforcos com o perfil adotado
        res["perfil_col"], res["perfil_raf"] = ap["col"], ap["raf"]
        res["atende"] = True
        if ap.get("lim_flecha"):                # ELS: flecha lateral / (H/150)
            res["flecha_util"] = round(ap["drift"] / ap["lim_flecha"], 2)
    else:
        res["perfil_col"], res["perfil_raf"] = "HEA200", "HEA180"
        res["atende"] = False
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
    # Gate 7 - tercas: adota a Ue mais leve que passa (ELU + ELS); o modelo desenha
    # a ADOTADA (terca_dims).
    save("gate7-tercas.txt", ti.memoria_pt())
    _rt = ti.melhor()
    res["terca_inter"] = round(_rt["interacao"], 2)
    res["terca_flecha_mm"] = round(_rt.get("flecha_v", 0.0), 1)
    res["terca_ok"] = bool(_rt.get("OK"))
    res["terca_dims"] = list(_rt.get("_dims", (200.0, 75.0, 25.0, 2.65)))
    res["terca_perfil"] = _rt.get("perfil")
    # Gate 7 - pecas secundarias (longarina de parede U + escora/cumeeira I)
    vr = vento.compute()
    net_par = [abs(vr["net"][c][s]) for c in vr["net"] for s in vr["net"][c]
               if s.startswith("parede")]
    sp = dict(params["secundarios"])
    sp["longarina"]["vao"] = g["bay"]; sp["escora"]["vao"] = g["bay"]
    sp["longarina"]["q_vento"] = max(net_par) * vr["q_kN_m2"]
    sp["escora"]["Nsd"] = vl["Fa_por_lado_kN"]     # axial = arrasto longitudinal/lado
    # Montante de oitao: n postos no oitao -> trib e altura governante da empena
    n_mont = params["secundarios"].get("n_montantes_oitao", 2)
    trib_m = g["span"] / (n_mont + 1)
    y_gov = trib_m if trib_m <= g["span"] / 2 else g["span"] - trib_m
    h_gov = g["eave"] + (g["ridge"] - g["eave"]) / (g["span"] / 2) * min(y_gov, g["span"] - y_gov)
    net_oit = max(abs(vl["net"][c][s]) for c in vl["net"] for s in vl["net"][c]
                  if s.startswith("oitao"))
    cfg_m = dict(params["secundarios"].get("montante", {}))
    cfg_m.update(altura=round(h_gov, 2), q_gable=net_oit * vl["q_kN_m2"], trib=trib_m,
                 nome="Montante de oitao (HEA)")
    # DIMENSIONA os secundarios: longarina por tirantes (sag rods), escora/montante
    # pela escada HEA. So geometria/perfis (nao inventa dado de catalogo do U).
    dsec = secmod.dimensiona_secundarios(
        params["fy"], sp["longarina"], sp["escora"], cfg_m,
        n_tir_seed=int(params.get("n_tirante_parede", 2)))
    rl = dsec["resultados"]["longarina"]; re_ = dsec["resultados"]["escora"]
    rm = dsec["resultados"]["montante"]
    save("gate7-secundarios.txt",
         "\n".join([f"ADOTADO: longarina {dsec['longarina']['perfil']} c/ "
                    f"{dsec['longarina']['n_tirantes']} "
                    f"linhas de tirante ; escora {dsec['escora']['perfil']} ; "
                    f"montante {dsec['montante']['perfil']}", ""]
                   + [secmod.relatorio_pt(x) for x in (rl, re_, rm)]))
    res["longarina_inter"] = dsec["longarina"]["inter"]; res["longarina_ok"] = dsec["longarina"]["ok"]
    res["longarina_perfil"] = dsec["longarina"]["perfil"]
    res["longarina_dims"] = list(dsec["longarina"]["dims"])
    res["escora_inter"] = dsec["escora"]["inter"]; res["escora_ok"] = dsec["escora"]["ok"]
    res["montante_inter"] = dsec["montante"]["inter"]; res["montante_ok"] = dsec["montante"]["ok"]
    res["n_tirante_parede"] = dsec["longarina"]["n_tirantes"]
    res["perfil_escora"] = dsec["escora"]["perfil"]
    res["perfil_montante"] = dsec["montante"]["perfil"]
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
    if res.get("perfil_col") in perfis.PERFIS:      # base ve o pilar ADOTADO
        pc = perfis.PERFIS[res["perfil_col"]]
        b["d_col"] = pc["d"]; b["bf_col"] = pc["bf"]; b["beff_tracao"] = pc["bf"]
    dimb = bc.dimensiona_base(b)                     # dimensiona ao esforco real
    save("gate7-base.txt", dimb["tabela"])
    if dimb["aprovado"]:
        B, Lm, tb, db, nb, rb, cb = dimb["aprovado"]
        save("gate7-base-detalhe.txt", bc.relatorio_pt(rb, cb))
        res["base_adotada"] = {"B": B, "L": Lm, "t": tb, "db": db, "n": nb}
        res["base_util"] = round(max(rb["u_tracao"], rb["u_corte"], rb["u_concreto"]), 2)
        res["base_ok"] = True
    else:
        res["base_adotada"] = {"B": b["B"], "L": b["L"], "t": b["t_placa"],
                               "db": b["db"], "n": b["n_chumbadores"]}
        res["base_ok"] = False
    # Gate 7 - SAPATA (NBR 6118) pelo ENVELOPE de combinacoes: cada verificacao
    # pega a combinacao que a governa (bearing = N max gravitacional ; tombamento
    # = N min + M ; etc). Pedestal ~ pilar adotado.
    sap = dict(params["fundacao"])
    if res.get("perfil_col") in perfis.PERFIS:
        pc = perfis.PERFIS[res["perfil_col"]]
        sap["b_ped"] = max(sap.get("b_ped", 0.30), round(pc["bf"] + 0.10, 2))
        sap["d_ped"] = max(sap.get("d_ped", 0.30), round(pc["d"] + 0.10, 2))
    casos_base = _casos_base_envelope()
    dims = fs.dimensiona_sapata_env(sap, casos_base)
    save("gate7-fundacao.txt", dims["tabela"])

    # Junta de dilatacao / movimento termico (temperatura) - nivel do edificio.
    rj = jd.verifica_junta(g["comprimento"], dT=params.get("dT_termico", jd.DT_BRASIL),
                           base_fixa=params.get("base_fixed", True),
                           aquecido=params.get("aquecido", False),
                           ar_condicionado=params.get("ar_condicionado", False))
    save("gate7-junta-dilatacao.txt", jd.relatorio_pt(rj))
    res["junta_dilatacao"] = {"L_max_m": rj["L_max_junta"], "precisa": rj["precisa_junta"],
                              "n_juntas": rj["n_juntas"], "delta_mm": rj["delta_segmento_mm"]}

    # Acao sismica (NBR 15421) - metodo das forcas horizontais equivalentes.
    # zona/classe/sistema/I/peso = dados do sitio (a skill confirma). Default zona
    # 0 -> dispensado (maior parte do Brasil). peso_efetivo_kN so exigido em zona>1.
    ps = params.get("sismo", {})
    rs = sismo.verifica_sismo(
        W=ps.get("peso_efetivo_kN", 0.0), zona=ps.get("zona", 0),
        classe=ps.get("classe_terreno", "C"), sistema=ps.get("sistema", "aco_momento"),
        I=ps.get("I", 1.0), hn=ps.get("hn", g.get("ridge")), ag=ps.get("ag"))
    save("gate7-sismo.txt", sismo.relatorio_pt(rs))
    res["sismo"] = {"zona": rs["zona"], "categoria": rs["categoria"],
                    "dispensado": rs.get("dispensado"), "H_kN": rs.get("H"),
                    "Cs": rs.get("Cs")}
    if dims["aprovado"]:
        sB, sL, sh, sr, _ = dims["aprovado"]
        rB = dims["parte_B"]; gv = dims["governantes"]
        def _arm(f):
            b = f.get("barras")
            return (f"{b['n']} phi {b['phi']:.1f} c/{b['s']*100:.0f}" if b else None)
        res["sapata_adotada"] = {"B": sB, "L": sL, "h": sh,
                                 "As_L": rB["flexao_L"]["As_adot"],
                                 "As_B": rB["flexao_B"]["As_adot"], "rigida": rB["rigida"],
                                 "arm_L": _arm(rB["flexao_L"]), "arm_B": _arm(rB["flexao_B"])}
        # util do envelope: pior entre solo, compr.diagonal e 1/FS (gov por combo)
        res["sapata_util"] = round(max(gv.get("solo", ("", 0))[1], gv.get("compr", ("", 0))[1],
                                       1.0 / gv.get("tomb", ("", 9))[1],
                                       1.0 / gv.get("desl", ("", 9))[1]), 2)
        res["sapata_ok"] = res["sapata_util"] <= 1.001
        # quantitativo (concreto + aco) - n_sapatas = 2 pilares x n_porticos
        n_port = int(round(g["comprimento"] / g["bay"])) + 1
        q = fs.quantitativo(sr, rB, n_sapatas=2 * n_port,
                            h_ped=params["fundacao"].get("h_ped", 0.5))
        res["sapata_quant"] = q
        save("gate7-fundacao.txt", dims["tabela"] + "\n\n" +
             f"QUANTITATIVO ({q['n']} sapatas = 2 pilares x {n_port} porticos):\n"
             f"  Concreto: {q['vol_conc_un']:.2f} m3/sapata  ->  TOTAL {q['vol_conc_tot']:.1f} m3\n"
             f"  Aco (flexao): {q['massa_aco_un']:.1f} kg/sapata (taxa {q['taxa_aco']:.0f} kg/m3)"
             f"  ->  TOTAL {q['massa_aco_tot']:.0f} kg".replace(".", ","))
    else:
        res["sapata_adotada"] = None
        res["sapata_ok"] = False
    dr = sc["perfil_raf"]["d"]; tf = sc["perfil_raf"]["tf"]   # viga ADOTADA
    Tf = abs(kM) / (dr - tf) + abs(kN) / 2.0
    knee = dict(params["joelho"]); knee.update(N=Tf, V=abs(kV) * 4 / 8.0,
                                               nome=f"Joelho - {knm} (M={abs(kM):.1f})")
    dimj = lg.dimensiona_ligacao(knee)               # dimensiona ao momento real
    save("gate7-joelho.txt", dimj["tabela"])
    if dimj["aprovado"]:
        jn, jdb, jt, jr, _ = dimj["aprovado"]
        res["joelho_adotado"] = {"n": jn, "db": jdb, "t": jt}
        res["joelho_util"] = round(jr["interacao"], 2)
        res["joelho_ok"] = True
    else:
        j = params["joelho"]
        res["joelho_adotado"] = {"n": j["n"], "db": j["db"], "t": j["t_chapa"]}
        res["joelho_ok"] = False
    clip = params["clip_terca"]
    save("gate7-ligacoes.txt", lg.relatorio_pt([lg.verifica_ligacao(clip)]))
    # Gate 9 - consolidado
    _consolidar(out_dir, save, g, params, res)
    return res


def _consolidar(out_dir, save, g, params, res=None):
    ordem = [("1. VENTO", "gate5-vento.txt"),
             ("1b. VENTO LONGITUDINAL", "gate5-vento-longitudinal.txt"),
             ("1c. PONTE ROLANTE", "gate5-ponte.txt"),
             ("2. PORTICO 1a ORDEM", "gate6-portico.txt"),
             ("3. 2a ORDEM (MAES)", "gate6-2a-ordem.txt"), ("4. PERFIS", "gate7-check-perfis.txt"),
             ("5. MAO-FRANCESA", "gate7-mao-francesa.txt"), ("6. TERCAS", "gate7-tercas.txt"),
             ("7. SECUNDARIOS", "gate7-secundarios.txt"),
             ("8. CONTRAVENTAMENTO", "gate7-contraventamento.txt"),
             ("9. VERGA DA PORTA", "gate7-verga.txt"),
             ("10. BASE", "gate7-base.txt"), ("11. SAPATA (FUNDACAO)", "gate7-fundacao.txt"),
             ("12. LIGACOES", "gate7-ligacoes.txt")]
    try:
        import framework as FW
        carimbo = FW.carimbo_versao()
    except Exception:
        carimbo = "framework galpao_fw"
    L = ["=" * 70, f"MEMORIAL CONSOLIDADO - GALPAO {g['comprimento']:.0f}x{g['span']:.0f} m",
         f"{carimbo} - CONCEITUAL, PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
         "=" * 70, ""]
    # QUADRO DE VERIFICACOES no topo + ALERTA gritante se algo nao atende.
    if res is not None:
        checks = [("Coluna", res.get("interacao_col")), ("Viga", res.get("interacao_raf")),
                  ("Flecha portico", res.get("flecha_util")), ("Base", res.get("base_util")),
                  ("Sapata (fundacao)", res.get("sapata_util")),
                  ("Joelho", res.get("joelho_util")), ("Terca", res.get("terca_inter")),
                  ("Longarina", res.get("longarina_inter")), ("Escora", res.get("escora_inter")),
                  ("Montante", res.get("montante_inter")), ("Verga", res.get("verga_inter")),
                  ("Viga rolamento", res.get("ponte_viga_inter"))]
        L.append("QUADRO DE VERIFICACOES (util = solicitacao/resistencia <= 1,0):")
        for nome, u in checks:
            if u is None:
                continue
            L.append(f"  {nome:<16} {u:5.2f}   "
                     f"{'OK' if u <= 1.001 else '*** NAO ATENDE ***'}")
        falhas = [(n, u) for n, u in checks if u is not None and u > 1.001]
        L.append("")
        if falhas:
            L += ["!" * 70,
                  "ATENCAO: ELEMENTOS QUE NAO ATENDEM (util > 1,0) - REVER O PROJETO:",
                  *[f"     - {n} = {u:.2f}" for n, u in falhas],
                  "!" * 70, ""]
        else:
            L += ["Todos os elementos verificados ATENDEM (util <= 1,0).", ""]
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
        # mesa_interna_travada (gate): False = mesa interna livre sob succao,
        # Lb=vao cheio (conservador, default). True = ha mao-francesa travando a
        # mesa interna -> Lb=vao/(n_maos_francesas+1). Ver REVISAO-SECUNDARIOS 9.1.
        "longarina": {"vao": 5.0, "q_vento": None, "trib": 2.0, "g_tapamento": 0.10,
                      "peso_proprio": 0.10, "n_tirantes": 2, "continua": False,
                      "mesa_interna_travada": False},
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
    # Sapata isolada (NBR 6118). sigma_solo_adm e parametros do solo = INPUT da
    # sondagem/geotecnia (A CONFIRMAR); pedestal ~ dim do pilar.
    "fundacao": {"sigma_solo_adm": 200.0, "mu": 0.5, "coesao": 0.0,
                 "h_reaterro": 0.5, "d_ped": 0.30, "b_ped": 0.30, "h_ped": 0.50,
                 "fck": 25e3, "fyk": 500e3, "cobrimento": 0.05, "phi_barra": 0.0125,
                 "gamma_f": 1.4},
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
    print(f"  longarina {r['longarina_perfil']} = {r['longarina_inter']:.2f} "
          f"({'OK' if r['longarina_ok'] else 'NAO'}, "
          f"{r['n_tirante_parede']} tirantes de parede)")
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
