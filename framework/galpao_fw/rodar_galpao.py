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
"""Orquestrador do fluxo de calculo do galpao. Suporta 1 ou N vaos.
Um projeto = um dict de params. Se params['geometria']['spans'] existir,
usa multi-vao; senao, usa 'span' (retrocompativel)."""

from __future__ import annotations

import math
import os

import vento_nbr6123 as vento
import telha_cobertura as telha
import galpao_portico as gp
import estabilidade_b1b2 as est
import check_nbr8800 as chk
import perfis
import redimensionamento as redim
import tercas_iteracao as ti
import base_chumbador as bc
import fundacao_sapata as fs
import viga_baldrame as vbal
import estaca_profunda as ep
import junta_dilatacao as jd
import sismo_nbr15421 as sismo
import ligacoes as lg
import mao_francesa as maofr
import secundarios_nbr8800 as secmod
import contraventamento as ctv
import gusset_ligacao as gus
import calhas
import sapata_divisa as sd
import alma_variavel as av
import ponte_rolante as pr
import console_ponte as cons
import fogo_nbr14323 as fogo
import escada as esc
import plataforma

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
    if gp.SISMO:
        fr, ix = gp._frame(); gp.case_sismo(fr, ix); _, mf = fr.solve()
        out["SISMO"] = (mf, fr.reactions(), ix)
    return out


def _esforcos_base_joelho():
    """Extrai esforcos de base + joelho do portico. Para N>1, retorna o pior
    caso entre todas as colunas. Cada resultado = (nome, N, V, M)."""
    casos = _casos_mf_reac()
    _, _, ix = casos["G"]
    bases = ix.get("nBases", [ix.get("nBaseL"), ix.get("nBaseR")])
    combos = gp._combos_elu(gp.PONTE, gp.SISMO)
    base_best = knee_best = None
    for nm, c in combos.items():
        for i, nb in enumerate(bases):
            R = sum(fac * casos[cs][1] for cs, fac in c.items())
            N, V, M = R[3 * nb + 1], R[3 * nb], R[3 * nb + 2]
            if base_best is None or abs(M) > abs(base_best[3]):
                base_best = (nm, N, V, M)
            eKnee = ix["cols"][i][-1]
            f = sum(fac * casos[cs][0][eKnee] for cs, fac in c.items())
            Mk, Vk, Nk = f[5], f[4], -f[3]
            if knee_best is None or abs(Mk) > abs(knee_best[3]):
                knee_best = (nm, Nk, Vk, Mk)
    return base_best, knee_best


def _casos_base_envelope():
    """Todos os casos de base (por combinacao ELU) como lista (nome, N, V, M) -
    para o ENVELOPE da sapata. Para N>1, retorna o PIOR caso entre as colunas."""
    casos = _casos_mf_reac()
    _, _, ix = casos["G"]
    bases = ix.get("nBases", [ix.get("nBaseL"), ix.get("nBaseR")])
    combos = gp._combos_elu(gp.PONTE, gp.SISMO)
    out = []
    for nm, c in combos.items():
        for nb in bases:
            R = sum(fac * casos[cs][1] for cs, fac in c.items())
            N, V, M = R[3 * nb + 1], R[3 * nb], R[3 * nb + 2]
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
    # Multi-vao: se 'spans' existir, usa lista; senao, usa 'span' (retro)
    if "spans" in g:
        gp.configurar(spans=g["spans"], eave=g["eave"], ridge=g["ridge"], bay=g["bay"],
                      base_fixed=params.get("base_fixed", True),
                      A_col=sc["A_col"], I_col=sc["I_col"],
                      A_raf=sc["A_raf"], I_raf=sc["I_raf"],
                      G_roof=params["cargas"]["G"], rafter_self=params["cargas"]["self"],
                      Q_roof=params["cargas"]["Q"], tapered=params.get("tapered"))
    else:
        gp.configurar(span=g["span"], eave=g["eave"], ridge=g["ridge"], bay=g["bay"],
                      base_fixed=params.get("base_fixed", True),
                      A_col=sc["A_col"], I_col=sc["I_col"],
                      A_raf=sc["A_raf"], I_raf=sc["I_raf"],
                      G_roof=params["cargas"]["G"], rafter_self=params["cargas"]["self"],
                      tapered=params.get("tapered"),
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
                             "R_vert_min": reac.get("R_vertical_min_kN", reac["R_vertical_kN"]),
                             "M_exc": reac["M_excentrico_kNm"],
                             "H_transv": reac["H_transversal_kN"],
                             "Hvr": pcfg["Hvr"]})
        res["ponte_R_vert"] = round(reac["R_vertical_kN"], 1)
        res["ponte_viga_inter"] = round(viga["inter"], 2)
        # Ligacao do CONSOLE a coluna (chapa+solda que recebe a viga de
        # rolamento excentrica). Dimensiona a perna do filete. L = altura de
        # solda ~ misula do console (build BRACKET 450mm); chapa 16mm (build).
        rc = cons.verifica_console({
            "Rv": reac["R_vertical_kN"], "Ht": reac.get("H_transversal_kN", 0.0),
            "ecc": pcfg.get("excentricidade", 0.30), "t": 0.016, "L": 0.45,
            "fy": params["fy"], "fu": 400e3})
        save("gate7-console.txt", cons.relatorio_pt(rc))
        res["console_adotado"] = rc["adotado"]
        res["console_u_max"] = rc["u_max"]
        res["console_ok"] = rc["OK"]
    else:
        gp.configurar(ponte=False)
    # Acao SISMICA (NBR 15421) - calculada ANTES da analise para ENTRAR no envelope
    # do portico (combinacao excepcional). zona/classe/sistema/I/peso = sitio (skill
    # confirma). zona 0 (default, maior parte do Brasil) -> H=0 -> nada muda.
    ps = params.get("sismo", {})
    rs = sismo.verifica_sismo(
        W=ps.get("peso_efetivo_kN", 0.0), zona=ps.get("zona", 0),
        classe=ps.get("classe_terreno", "C"), sistema=ps.get("sistema", "aco_momento"),
        I=ps.get("I", 1.0), hn=ps.get("hn", g.get("ridge")), ag=ps.get("ag"))
    # Cortante de piso atribuido a UM portico = H_total * (vao tributario / comprimento).
    H_sismo = rs.get("H", 0.0) or 0.0
    E_frame = H_sismo * g["bay"] / g.get("comprimento", 2 * g["span"])
    gp.configurar(sismo={"E": E_frame} if E_frame > 1e-9 else False)
    res["sismo_E_portico_kN"] = round(E_frame, 2)
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
                        lb_col=params["Lb"]["col"], lb_raf=params["Lb"]["raf"])
    save("gate7-redimensionamento.txt", adoc["tabela"])
    if adoc["aprovado"]:
        ap = adoc["aprovado"]
        for i, p in enumerate(ap["cols"]):
            sc[f"perfil_col_{i}"] = perfis.PERFIS[p]
        sc["perfil_col"] = perfis.PERFIS[ap["cols"][0]]
        sc["perfil_raf"] = perfis.PERFIS[ap["raf"]]
        a = est.analyse()
        res["perfil_colunas"] = ap["cols"]
        res["perfil_raf"] = ap["raf"]
        res["atende"] = True
        if ap.get("lim_flecha"):
            res["flecha_util"] = round(ap["drift"] / ap["lim_flecha"], 2)
    else:
        sc["perfil_col"] = perfis.PERFIS["HEA200"]
        sc["perfil_raf"] = perfis.PERFIS["HEA180"]
        res["perfil_colunas"] = ["HEA200"] * gp.N_VAOS
        res["perfil_raf"] = "HEA180"
        res["atende"] = False
    # Gate 7 - mao-francesa
    slope = (g["ridge"] - g["eave"]) / (g["span"] / 2.0)
    n_terca = params["terca"].get("n_por_agua", 3)
    cbm = max(a["combos"], key=lambda r: abs(r.get("viga", {}).get("Msd", 0) or
                  max(r.get(f"viga_{j}_{s}", {}).get("Msd", 0) for j in range(gp.N_VAOS) for s in ("E","D"))))
    cbm_v = cbm.get("viga", cbm.get("viga_0_E", cbm.get("viga_0_D", {"Nsd":0,"Msd":0,"Vsd":0})))
    plano_mf = maofr.plano_mao_francesa(
        sc["perfil_raf"], params["fy"], max(0.0, cbm_v["Nsd"]),
        abs(cbm_v["Msd"]), abs(cbm_v["Vsd"]),
        span=g["span"], slope=slope, n_terca=n_terca)
    save("gate7-mao-francesa.txt", maofr.relatorio_pt(plano_mf, "viga (mesa inferior)"))
    Lb_raf = plano_mf["Lb_usado"] if plano_mf.get("ok") else params["Lb"]["raf"]
    res["mf_bracos_portico"] = plano_mf.get("n_bracos_portico")
    res["mf_stride"] = plano_mf.get("stride")
    res["Lb_raf"] = round(Lb_raf, 3)
    # Gate 7 - perfis (verifica por grupo)
    finais = []
    nv = gp.N_VAOS
    cols_prof = res.get("perfil_colunas", [sc.get("perfil_col_nome","HEA200")]*(nv+1))
    for i in range(nv + 1):
        gname = f"col_{i}"
        sec = perfis.PERFIS[cols_prof[i]]
        cands = [chk.verifica(sec, params["fy"], L=gp.EAVE, Nsd=r[gname]["Nsd"],
                              Msd=r[gname]["Msd"], Vsd=r[gname]["Vsd"], Kx=1, Ky=1,
                              Lb=params["Lb"]["col"], nome=f"Col {i} (K=1; gov {r['nome']})")
                 for r in a["combos"]]
        finais.append(max(cands, key=lambda x: x["interacao"]))
    for i in range(nv):
        for side, sname in ((0, "E"), (1, "D")):
            gname = f"viga_{i}_{sname}"
            cands = [chk.verifica(sc["perfil_raf"], params["fy"], L=est.SEC_VIGAS[0]["L"],
                                  Nsd=r[gname]["Nsd"], Msd=r[gname]["Msd"],
                                  Vsd=r[gname]["Vsd"], Kx=1, Ky=1,
                                  Lb=Lb_raf, nome=f"Viga {i}{sname} (K=1; gov {r['nome']})")
                     for r in a["combos"]]
            finais.append(max(cands, key=lambda x: x["interacao"]))
    save("gate7-check-perfis.txt", chk.relatorio_pt(finais, params["fy"]))
    res["interacao_max"] = max(f["interacao"] for f in finais) if finais else 0
    n_col = nv + 1
    col_f = finais[:n_col]
    raf_f = finais[n_col:]
    res["interacao_col"] = max(f["interacao"] for f in col_f) if col_f else 0
    res["interacao_raf"] = max(f["interacao"] for f in raf_f) if raf_f else 0
    # Gate 7 - tercas: adota a Ue mais leve que passa (ELU + ELS); o modelo desenha
    # a ADOTADA (terca_dims).
    save("gate7-tercas.txt", ti.memoria_pt())
    _rt = ti.melhor()
    res["terca_inter"] = round(_rt["interacao"], 2)
    res["terca_flecha_mm"] = round(_rt.get("flecha_v", 0.0), 1)
    res["terca_ok"] = bool(_rt.get("OK"))
    res["terca_dims"] = list(_rt.get("_dims", (200.0, 75.0, 25.0, 2.65)))
    res["terca_perfil"] = _rt.get("perfil")
    # Gate 7 - TELHA: verifica a telha vencendo o espacamento das tercas sob a
    # sucao LOCAL de borda/canto (vento §8). Perfil da telha = catalogo (params).
    if params.get("telha"):
        vt_loc = vento.compute(larg_b=g["span"], alt_h=g["eave"],
                               comp_a=g.get("comprimento", 2 * g["span"]))
        w_agua = math.hypot(g["span"] / 2.0, g["ridge"] - g["eave"])   # comprimento da agua
        esp_terca = w_agua / max(n_terca, 1)                           # vao da telha
        tcfg = dict(params["telha"].get("cfg", {}))
        tcfg.setdefault("vao", round(esp_terca, 3))
        tcfg.setdefault("W_sucao", vt_loc["local"]["p_local_cob_kN_m2"])
        tcfg.setdefault("Q", params["cargas"].get("Q", 0.25))
        rt_telha = telha.verifica_telha(params["telha"]["perfil"], tcfg)
        save("gate7-telha.txt", telha.relatorio_pt(rt_telha))
        res["telha_util"] = rt_telha["util_elu"]
        res["telha_vao"] = rt_telha["vao"]
        res["telha_vao_max"] = rt_telha["vao_max"]["vao_max_m"]
        res["telha_ok"] = rt_telha["OK"]
    # Gate 7 - pecas secundarias (longarina de parede U + escora/cumeeira I)
    vr = vento.compute(larg_b=g["span"], alt_h=g["eave"],
                       comp_a=g.get("comprimento", 2 * g["span"]))
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
    # Gate 7 - GUSSET dos contraventamentos (chapa de no; verifica a chapa que
    # recebe a diagonal tracionada). Geometria do build_galpao (_gusset_tri
    # L=150, t=12). Verifica o no de PAREDE e o de COBERTURA; adota o pior.
    G_T, G_LC = 0.012, 0.150                              # t, Lc (m) - build
    gcasos = [("Gusset de contravento - PAREDE", abs(Ndp)),
              ("Gusset de contravento - COBERTURA", abs(Ndc))]
    gres, gtxt = [], []
    for gnome, gN in gcasos:
        rg = gus.verifica_gusset({"N": gN, "t": G_T, "w0": 0.0, "Lc": G_LC,
                                  "fy": params["fy"], "fu": 400e3,
                                  "Lsolda": 2.0 * G_LC})
        gres.append(rg)
        gtxt.append(gus.relatorio_pt(rg, gnome))
    save("gate7-gusset.txt", "\n\n".join(gtxt))
    gpior = max(gres, key=lambda r: r["u_max"])
    res["gusset_adotado"] = {"t_mm": gpior["adotado"]["t_mm"],
                             "perna_solda_mm": round(
                                 gus.LG.solda_filete_minimo(G_T * 1000.0), 1)}
    res["gusset_u_max"] = gpior["u_max"]
    res["gusset_ok"] = all(r["OK"] for r in gres)
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

    # Gate 7 - VIGA DE BALDRAME / AMARRACAO entre sapatas (NBR 6118). Amarra as
    # sapatas e absorve a reacao HORIZONTAL da base (empuxo do portico) como tracao;
    # baldrame sob a parede de fechamento. N_amarracao = max|V| da base no envelope.
    if params.get("baldrame"):
        V_base_max = max(abs(v) for _, _, v, _ in casos_base)
        bd = dict(params["baldrame"])
        bd.setdefault("vao", g["bay"])
        bd.setdefault("N_amarracao", round(V_base_max, 2))
        bd.setdefault("fck", sap.get("fck", 25e3)); bd.setdefault("fyk", sap.get("fyk", 500e3))
        rbd = vbal.verifica_baldrame(bd)
        save("gate7-baldrame.txt", vbal.relatorio_pt(rbd))
        res["baldrame"] = {"secao": f"{rbd['b']*100:.0f}x{rbd['h']*100:.0f}",
                           "As_inf_cm2": rbd["As_inf_cm2"], "N_tie_kN": rbd["N_tie"],
                           "ok": rbd["OK"],
                           # geometria p/ o build 3D
                           "b": rbd["b"], "h": rbd["h"], "vao": bd["vao"]}

    # Gate 7 - FUNDACAO PROFUNDA (opcional): estaca (Aoki-Velloso) + bloco de
    # coroamento. So roda com params["estaca"] (escolha de sitio: sondagem SPT).
    # N_pilar = maior reacao vertical de compressao na base (envelope).
    if params.get("estaca"):
        N_comp = max(n for _, n, _, _ in casos_base)          # maior compressao
        N_pilar = abs(N_comp)
        N_tr = max(0.0, -min(n for _, n, _, _ in casos_base))  # uplift (reacao negativa)
        ecfg = dict(params["estaca"]); ecfg.setdefault("N_pilar", round(N_pilar, 1))
        ecfg.setdefault("N_uplift", round(N_tr, 1))
        ecfg.setdefault("D", 0.30); ecfg.setdefault("L", 10.0)
        # garante o bloco de coroamento no calculo (dims p/ desenhar o 3D)
        ecfg.setdefault("bloco", {"a_pilar": 0.30, "fck": 25e3, "fyk": 500e3})
        re_ = ep.verifica_estaca(ecfg)
        save("gate7-estaca.txt", ep.relatorio_pt(re_))
        Dp = ecfg["D"]; a_pil = (ecfg.get("bloco") or {}).get("a_pilar", 0.30)
        esp = (ecfg.get("bloco") or {}).get("espacamento", 3.0 * Dp)
        h_bloco = (re_.get("bloco") or {}).get("h", max(0.40, 1.2 * Dp))
        res["estaca"] = {"tipo": re_["capacidade"]["tipo_estaca"],
                         "P_adm_kN": re_["capacidade"]["P_adm_kN"],
                         "n_estacas": re_["grupo"]["n"], "N_pilar_kN": round(N_pilar, 1),
                         # geometria p/ o build 3D (tudo do calculo / envelope)
                         "D": Dp, "L": ecfg["L"], "espacamento": esp,
                         "bloco_h": h_bloco, "bloco_a": a_pil,
                         "uplift": bool(N_tr > 1e-6)}

    # Gate - CALHA (dimensionamento hidraulico, NBR 10844 / Bellei). Roda quando
    # ha calha na cobertura. Area de contribuicao da geometria: comprimento (ao
    # longo da calha) x meia-largura (uma agua) projetada; I pluviometrica do gate.
    if params.get("calha"):
        agua = g["span"] / 2.0 / max(math.cos(math.atan(slope)), 1e-6)
        rca = calhas.dimensiona(g["comprimento"], agua,
                                I_mm_h=params.get("chuva_I_mm_h", 150.0))
        save("gate-calha.txt", calhas.relatorio_pt(rca))
        res["calha"] = {"vazao_Lmin": rca["vazao_Lmin"],
                        "B_mm": rca["secao"].get("B_base_m", 0) * 1000,
                        "H_mm": rca["secao"].get("H_max_m", 0) * 1000,
                        "condutor_mm": rca.get("condutor_diam_mm"),
                        "ok": rca["ok"]}

    # Gate 7 - SAPATA DE DIVISA (excentrica + viga alavanca, Alonso). So quando o
    # gate fundacao.divisa e informado: pilar na linha do lote. Carga = maior
    # compressao da base (envelope); vizinho interno = mesma ordem; vao = bay.
    if params.get("divisa"):
        dvg = dict(params["divisa"])
        N_comp_d = abs(max(n for _, n, _, _ in casos_base))
        rdv = sd.dimensiona_divisa(
            P_divisa=round(N_comp_d, 1), P_interno=round(N_comp_d, 1),
            dist_eixos=g["bay"], dist_divisa=dvg["dist_divisa"],
            sigma_solo=sap.get("sigma_solo_adm", 200.0),
            fck=sap.get("fck", 25e3), fyk=sap.get("fyk", 500e3))
        save("gate7-divisa.txt", sd.relatorio_pt(rdv))
        res["divisa"] = {"B": rdv["divisa"]["B"], "L": rdv["divisa"]["L"],
                         "R_kN": rdv["divisa"]["R"], "e_m": rdv["divisa"]["e"],
                         "viga_As_cm2": rdv["viga"]["As_adot_cm2"]}

    # Gate 6 - PORTICO DE ALMA VARIAVEL (misula tapered). So com tipo_portico=
    # alma_variavel: o portico ja foi resolvido com a secao por segmento (rafter
    # tapered); aqui gera o memorial da misula (secao_tapered + peso) e sinaliza
    # que a SECAO DO JOELHO (mais funda) governa a flexo-compressao.
    if params.get("tipo_portico") == "alma_variavel" and params.get("tapered"):
        tp = params["tapered"]
        secs = av.secao_tapered(tp["h_joelho"], tp["h_cumeeira"], tp.get("bf", 0.20),
                                tp.get("tw", 0.008), tp.get("tf", 0.0125), nseg=gp.NSEG)
        peso = av.peso_tapered(tp["h_joelho"], tp["h_cumeeira"], tp.get("bf", 0.20),
                               tp.get("tw", 0.008), tp.get("tf", 0.0125), g["span"])
        L = ["=" * 66, "PORTICO DE ALMA VARIAVEL (misula tapered)", "=" * 66,
             f"  h_joelho = {tp['h_joelho']*1000:.0f} mm ; h_cumeeira = "
             f"{tp['h_cumeeira']*1000:.0f} mm ; nseg = {gp.NSEG}",
             f"  Peso linear medio = {peso:.2f} kN/m",
             "  Secoes por segmento (joelho -> cumeeira):",
             "    seg |  h(mm) |  A(cm2) |  I(cm4)  |  Wx(cm3)"]
        for s in secs:
            L.append("    %3d | %6.0f | %7.1f | %8.0f | %8.0f" %
                     (s["segmento"], s["h_m"] * 1000, s["A_m2"] * 1e4,
                      s["I_m4"] * 1e8, s["Wx_m3"] * 1e6))
        L += ["  >> A secao do JOELHO (mais funda) governa a flexo-compressao; o",
              "     portico foi resolvido com a rigidez variavel (secao por segmento).",
              "  >> Verificacao de estados-limite por segmento = A CONFIRMAR (sensor).",
              "=" * 66]
        save("gate6-alma-variavel.txt", "\n".join(L))
        res["alma_variavel"] = {
            "h_joelho_mm": tp["h_joelho"] * 1000, "h_cumeeira_mm": tp["h_cumeeira"] * 1000,
            "peso_kN_m": round(peso, 2), "nseg": gp.NSEG,
            "I_joelho_cm4": round(secs[0]["I_m4"] * 1e8, 0),
            "I_cumeeira_cm4": round(secs[-1]["I_m4"] * 1e8, 0)}

    # Junta de dilatacao / movimento termico (temperatura) - nivel do edificio.
    rj = jd.verifica_junta(g["comprimento"], dT=params.get("dT_termico", jd.DT_BRASIL),
                           base_fixa=params.get("base_fixed", True),
                           aquecido=params.get("aquecido", False),
                           ar_condicionado=params.get("ar_condicionado", False))
    save("gate7-junta-dilatacao.txt", jd.relatorio_pt(rj))
    res["junta_dilatacao"] = {"L_max_m": rj["L_max_junta"], "precisa": rj["precisa_junta"],
                              "n_juntas": rj["n_juntas"], "delta_mm": rj["delta_segmento_mm"]}

    # Acao sismica (NBR 15421) - ja calculada no inicio (rs) e injetada no envelope
    # do portico como combinacao excepcional (C6). Aqui so gera o memorial + resumo.
    extra = ""
    if E_frame > 1e-9:
        comp = g.get("comprimento", 2 * g["span"])
        extra = (f"\n\n>> Forca de calculo por portico (cortante de piso, vao tributario "
                 f"{g['bay']:.1f} m / {comp:.1f} m):\n"
                 f"   E = {E_frame:.1f} kN, aplicada no beiral -> combinacao EXCEPCIONAL C6\n"
                 f"   (1,2G+-E desfav / 1,0G+-E fav ; sem vento e sem Q, NBR 15421 5.4).")
        # Efeitos de 2a ordem (9.6): coeficiente de estabilidade theta
        Cd = sismo.SISTEMA_R.get(ps.get("sistema", "aco_momento"), (0, 0, 3.0))[2]
        d_xe = gp.analyse().get("drift_sismo", 0.0)
        Px = (rs.get("W", 0.0) or 0.0) * g["bay"] / comp        # vertical servico tributario
        dt = sismo.deslocamento_theta(d_xe, Cd=Cd, I=ps.get("I", 1.0),
                                      Px=Px, Hx=E_frame, hsx=g["eave"])
        extra += (f"\n>> Deslocamentos (9.5) e 2a ordem (9.6): delta_xe={d_xe*1000:.1f} mm ; "
                  f"delta_x=Cd*delta_xe/I={dt['delta_x']*1000:.1f} mm (Cd={Cd})\n"
                  f"   theta = Px*Dx/(Hx*hsx*Cd) = {dt['theta']:.4f} "
                  f"(theta_max={dt['theta_max']:.3f}) -> {dt['situacao']}\n"
                  f"   fator de amplificacao de 2a ordem = {dt['amplif_2a_ordem']:.3f}")
        res["sismo_theta"] = {"theta": dt["theta"], "amplif": dt["amplif_2a_ordem"],
                              "dispensa": dt["dispensa_2a_ordem"], "ok": dt["ok"]}
    else:
        extra = "\n\n>> Zona sem exigencia -> nao entra no envelope."
    save("gate7-sismo.txt", sismo.relatorio_pt(rs) + extra)
    res["sismo"] = {"zona": rs["zona"], "categoria": rs["categoria"],
                    "dispensado": rs.get("dispensado"), "H_kN": rs.get("H"),
                    "Cs": rs.get("Cs"), "E_portico_kN": round(E_frame, 2)}
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
    dr = sc["perfil_raf"]["d"]; tf = sc["perfil_raf"]["tf"]
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
    # Gate 8 - FOGO (NBR 14323): verifica o perfil adotado em situacao de incendio
    if params.get("fogo") and res.get("perfil_colunas"):
        fg = params["fogo"]
        sec_fogo = {"h": sc["perfil_col"]["d"]*1000, "b": sc["perfil_col"]["bf"]*1000,
                    "tw": sc["perfil_col"]["tw"]*1000, "tf": sc["perfil_col"]["tf"]*1000}
        Gk = params["cargas"]["G"] * g["bay"] * g["span"] / 2.0
        Qk = params["cargas"]["Q"] * g["bay"] * g["span"] / 2.0
        rf = fogo.verifica_fogo(sec_fogo, params["fy"], Gk, Qk,
                                TRRF_min=fg.get("TRRF_min", 60),
                                protecao=fg.get("protecao"))
        save("gate8-fogo.txt", fogo.relatorio_pt(rf))
        res["fogo_theta"] = rf["theta_aco_C"]
        res["fogo_ky"] = rf["ky"]
        res["fogo_TRRF"] = rf["TRRF_min"]
    # Gate 8 - ESCADA INDUSTRIAL
    if params.get("escada"):
        esc_cfg = params["escada"]
        re = esc.dimensiona(esc_cfg["desnivel"], esc_cfg["projecao"],
                            esc_cfg.get("largura", 1.20),
                            q_acidental=esc_cfg.get("q_acidental", 3.0))
        save("gate8-escada.txt", esc.relatorio_pt(re))
        res["escada_ok"] = re.get("ok", False)
        res["escada_perfil"] = re.get("perfil")
    # Gate 8 - PLATAFORMA / PASSARELA
    if params.get("plataforma"):
        plt_cfg = params["plataforma"]
        rp = plataforma.viga_secundaria(plt_cfg["L"], plt_cfg["b_trib"],
                                        plt_cfg.get("q_perm", 2.0),
                                        plt_cfg.get("q_acidental", 3.0))
        save("gate8-plataforma.txt", plataforma.relatorio_pt(rp))
        res["plataforma_ok"] = rp.get("ok", False)
        res["plataforma_perfil"] = rp.get("perfil")
    # Gate 9 - consolidado
    _consolidar(out_dir, save, g, params, res)
    return res


def _consolidar(out_dir, save, g, params, res=None):
    ordem = [("1. VENTO", "gate5-vento.txt"),
             ("1b. VENTO LONGITUDINAL", "gate5-vento-longitudinal.txt"),
             ("1c. PONTE ROLANTE", "gate5-ponte.txt"),
             ("1d. CONSOLE DA PONTE", "gate7-console.txt"),
             ("2. PORTICO 1a ORDEM", "gate6-portico.txt"),
             ("3. 2a ORDEM (MAES)", "gate6-2a-ordem.txt"),
             ("3b. PORTICO ALMA VARIAVEL", "gate6-alma-variavel.txt"),
             ("4. PERFIS", "gate7-check-perfis.txt"),
             ("5. MAO-FRANCESA", "gate7-mao-francesa.txt"), ("6. TERCAS", "gate7-tercas.txt"),
             ("6b. TELHA", "gate7-telha.txt"),
             ("7. SECUNDARIOS", "gate7-secundarios.txt"),
             ("8. CONTRAVENTAMENTO", "gate7-contraventamento.txt"),
             ("8b. GUSSET DE CONTRAVENTO", "gate7-gusset.txt"),
             ("9. VERGA DA PORTA", "gate7-verga.txt"),
             ("10. BASE", "gate7-base.txt"), ("11. SAPATA (FUNDACAO)", "gate7-fundacao.txt"),
             ("11b. VIGA DE BALDRAME", "gate7-baldrame.txt"),
             ("11c. FUNDACAO PROFUNDA (ESTACA)", "gate7-estaca.txt"),
             ("11g. SAPATA DE DIVISA", "gate7-divisa.txt"),
             ("11d. FOGO NBR 14323", "gate8-fogo.txt"),
             ("11e. ESCADA", "gate8-escada.txt"),
             ("11f. PLATAFORMA", "gate8-plataforma.txt"),
             ("12. LIGACOES", "gate7-ligacoes.txt"),
             ("13. CALHAS E CONDUTORES", "gate-calha.txt")]
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
                  ("Viga rolamento", res.get("ponte_viga_inter")),
                  ("Fogo theta C", res.get("fogo_theta")),
                  ("Escada", 0 if res.get("escada_ok") else None),
                  ("Plataforma", 0 if res.get("plataforma_ok") else None)]
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
    # Telha: perfil = CATALOGO do fabricante (Wef cm3/m, Ief cm4/m, peso kN/m2) -
    # A CONFIRMAR. cfg.vao e W_sucao sao auto-preenchidos (espacamento das tercas
    # e sucao local do vento §8) se omitidos.
    "telha": {"perfil": telha.TELHA_EXEMPLO, "cfg": {"continuidade": "simples"}},
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
    # Viga de baldrame / amarracao (NBR 6118). vao e N_amarracao (reacao horiz.
    # da base) auto do modelo se omitidos; q_parede = alvenaria de fechamento
    # (0 = so telha). Secao b x h e A CONFIRMAR.
    "baldrame": {"b": 0.20, "h": 0.40, "cobrimento": 0.05, "q_parede": 0.0,
                 "continuidade": "simples"},
    "joelho": {"tipo": "parafusos", "n": 4, "db": 0.024, "fub": 825e3,
               "t_chapa": 0.0125, "fu_chapa": 400e3, "lf": 0.040, "rosca_no_plano": True},
    "clip_terca": {"nome": "Chapa de terca (2 M12) - excecao", "tipo": "parafusos",
                   "n": 2, "db": 0.012, "fub": 400e3, "t_chapa": 0.006,
                   "fu_chapa": 400e3, "lf": 0.025, "V": 8.0, "excecao_terca": True},
    # Fogo: None = nao verifica. Dict = parametros (TRRF_min, protecao).
    "fogo": None,
    # Escada: None = nao dimensiona. Dict = {desnivel, projecao, largura, q_acidental}.
    "escada": None,
    # Plataforma: None = nao dimensiona. Dict = {L, b_trib, q_perm, q_acidental}.
    "plataforma": None,
    # "ponte": None -> galpao SEM ponte (portico identico a referencia).
}


def params_com_ponte():
    """PARAMS_REF + uma ponte rolante de 100 kN (exemplo; dados A CONFIRMAR do
    fabricante/NBR 8400). Demonstra o galpao COM ponte de ponta a ponta."""
    import copy
    p = copy.deepcopy(PARAMS_REF)
    p["ponte"] = {"Q": 100.0, "peso_ponte": 60.0, "peso_trole": 15.0,
                  "aprox_min": 1.0, "n_rodas_lado": 2, "n_rodas_motoras": 2,
                  "phi": 1.10, "frac_lateral": 0.10, "frac_long": 0.10,
                  "d_rodas": 3.0, "fy": 250e3, "perfil_viga": pr.VS500,
                  "siderurgica": False, "excentricidade": 0.30, "Hvr": 4.5,
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
