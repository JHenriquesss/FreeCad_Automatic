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
import viga_equilibrio as veq
import alma_variavel as av
import tesoura as tes
import ponte_rolante as pr
import console_ponte as cons
import zona_painel as zpn
import flt_misula as fltm
import dg25_ltb as dg25
import alma_esbelta as ae
import tensao_ponto as tsp
import cortante_tapered as cta
import enrijecedor_painel as enp
import fogo_nbr14323 as fogo
import escada as esc
import plataforma
import terreno

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


def _casos_base_envelope(n_wall_perm_ext=0.0):
    """Todos os casos de base (por combinacao ELU) como lista (nome, N, V, M) -
    para o ENVELOPE da sapata. Para N>1, retorna o PIOR caso entre as colunas.

    O fechamento LEVE ja entra na reacao de base via UDL das colunas no case_G
    (galpao_portico.W_WALL_COL). n_wall_perm_ext: reacao vertical PERMANENTE da
    ALVENARIA autoportante (kN, COMPRESSAO=+ apos o conserto do sinal do frame2d),
    que desce direto na fundacao (nao pela coluna de aco); aplicada nas colunas
    EXTERNAS e fatorada como acao permanente (fator 'G' de cada combinacao ->
    desfavoravel na gravidade, favoravel/estabilizante no uplift)."""
    casos = _casos_mf_reac()
    _, _, ix = casos["G"]
    bases = ix.get("nBases", [ix.get("nBaseL"), ix.get("nBaseR")])
    externas = {bases[0], bases[-1]}
    combos = gp._combos_elu(gp.PONTE, gp.SISMO)
    out = []
    for nm, c in combos.items():
        for nb in bases:
            R = sum(fac * casos[cs][1] for cs, fac in c.items())
            N, V, M = R[3 * nb + 1], R[3 * nb], R[3 * nb + 2]
            if n_wall_perm_ext and nb in externas:
                N += c.get("G", 0.0) * n_wall_perm_ext   # alvenaria: permanente (compressao +)
            out.append((nm, N, V, M))
    return out


def rodar(params, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    def save(nome, txt):
        with open(os.path.join(out_dir, nome), "w", encoding="utf-8") as f:
            f.write(txt + "\n")
        return txt

    gp.reset(); vento.reset()          # estado limpo (sem vazamento entre projetos)
    try:
        import estabilidade_b1b2 as est
        est.reset()
    except Exception:
        pass

    g = params["geometria"]
    sc = params["secoes"]
    # NEVE (EN 1991-1-3) - acao variavel de coberta, so em regioes serranas do Sul.
    # O caso SIMETRICO governa a carga gravitacional de coberta (nao age junto com
    # a sobrecarga de USO -> Q_efetivo = max(Q, neve_sim)); os casos ASSIMETRICOS
    # (vento varrendo neve) ficam calculados e SINALIZADOS (carga desbalanceada, nao
    # auto-combinada no portico - o engenheiro inclui a combinacao se a regiao exigir).
    q_ef = params["cargas"]["Q"]
    neve_res = None
    _nv = params.get("neve")
    if _nv and _nv.get("sk"):
        import neve as _neve
        _span0 = g["spans"][0] if "spans" in g else g["span"]
        _th = math.degrees(math.atan((g["ridge"] - g["eave"]) / (_span0 / 2.0)))
        _rnv = _neve.carga_neve(sk_kN_m2=_nv.get("sk", 0.0), theta_graus=_th,
                                Ce=_nv.get("Ce", 1.0), Ct=_nv.get("Ct", 1.0),
                                deslizamento_livre=_nv.get("deslizamento_livre", True))
        neve_sim = max(_rnv["simetrico_kN_m2"])
        neve_assim = max(max(_rnv["assimetrico_1_kN_m2"]),
                         max(_rnv["assimetrico_2_kN_m2"]))
        q_ef = max(q_ef, neve_sim)
        _extra = [
            "", "  >> Simetrico governante = %.3f kN/m2" % neve_sim,
            "     Q_efetivo da coberta (portico) = max(Q=%.3f, neve=%.3f) = %.3f kN/m2"
            % (params["cargas"]["Q"], neve_sim, q_ef),
            "  >> ASSIMETRICO (max %.3f kN/m2): carga DESBALANCEADA, NAO auto-combinada"
            % neve_assim,
            "     no portico - o engenheiro inclui a combinacao se a regiao exigir.",
            "  >> Tercas/telha usam a sobrecarga padrao; se a neve governar, revisar."]
        save("gate5-neve.txt", _neve.relatorio_pt(_rnv) + "\n" + "\n".join(_extra))
        neve_res = {"sk": _nv.get("sk"), "simetrico": neve_sim,
                    "assimetrico": neve_assim, "q_efetivo": round(q_ef, 3),
                    "governa": neve_sim > params["cargas"]["Q"]}
    # Multi-vao: se 'spans' existir, usa lista; senao, usa 'span' (retro)
    # peso da parede de fechamento como UDL vertical nas colunas externas (kN/m de
    # altura de coluna). Antes: coletado e IGNORADO (contra-seguranca). 0 = sem parede.
    _par = params.get("parede") or {}
    _w_wall_col = _par.get("w_col_kN_m", 0.0)
    _abert = (params.get("vento") or {}).get("abertura_dominante", "portao_oitao")
    _aguas = int(params.get("aguas", 2))
    if "spans" in g:
        gp.configurar(spans=g["spans"], eave=g["eave"], ridge=g["ridge"], bay=g["bay"],
                      base_fixed=params.get("base_fixed", True),
                      A_col=sc["A_col"], I_col=sc["I_col"],
                      A_raf=sc["A_raf"], I_raf=sc["I_raf"],
                      G_roof=params["cargas"]["G"], rafter_self=params["cargas"]["self"],
                      Q_roof=q_ef, tapered=params.get("tapered"), w_wall_col=_w_wall_col,
                      abertura_dominante=_abert, aguas=_aguas)
    else:
        gp.configurar(span=g["span"], eave=g["eave"], ridge=g["ridge"], bay=g["bay"],
                      base_fixed=params.get("base_fixed", True),
                      A_col=sc["A_col"], I_col=sc["I_col"],
                      A_raf=sc["A_raf"], I_raf=sc["I_raf"],
                      G_roof=params["cargas"]["G"], rafter_self=params["cargas"]["self"],
                      tapered=params.get("tapered"),
                      Q_roof=q_ef, w_wall_col=_w_wall_col, abertura_dominante=_abert,
                      aguas=_aguas)
    ti.configurar(bay=g["bay"], ly=g["bay"] / 2.0,
                  trib=params["terca"]["trib"], theta=gp.THETA,
                  fy=params["terca"]["fy"])
    if params.get("vento"):                       # parametros de sitio (Gate 5)
        vt = params["vento"]
        vento.configurar(v0=vt.get("v0"), cat=vt.get("cat"), classe=vt.get("classe"),
                         s1=vt.get("s1"), s3=vt.get("s3"), z=vt.get("z"),
                         theta=math.degrees(gp.THETA))

    res = {}
    if neve_res:
        res["neve"] = neve_res
    # Ponte rolante (opcional): calcula a acao e injeta a reacao no portico como
    # caso de carga + combinacoes (C4/C5). Sem "ponte" nos params -> galpao SEM
    # ponte, portico identico a referencia.
    if params.get("ponte"):
        pcfg = dict(params["ponte"]); pcfg.setdefault("vao_viga", g["bay"])
        pcfg.setdefault("vao_ponte", g["span"] - pcfg.get("folga_trilho", 0.5))
        pcfg.setdefault("Hvr", 4.5)      # altura do trilho: opcional -> default (wiki 07 C)
        esf, viga, reac = pr.analisa(pcfg)
        save("gate5-ponte.txt", pr.relatorio_pt(esf, viga, reac))
        gp.configurar(ponte={"R_vert": reac["R_vertical_kN"],
                             "R_vert_min": reac.get("R_vertical_min_kN", reac["R_vertical_kN"]),
                             "M_exc": reac["M_excentrico_kNm"],
                             "H_transv": reac["H_transversal_kN"],
                             "Hvr": pcfg["Hvr"]})
        res["ponte_R_vert"] = round(reac["R_vertical_kN"], 1)
        res["ponte_viga_inter"] = round(viga["inter"], 2)
        # viga["OK"] engloba flexao biaxial + FADIGA (Anexo K) + FLECHA (L/600..1000):
        # sem isto, uma reprovacao de fadiga/flecha (inter < 1) passaria silenciosa.
        res["ponte_viga_ok"] = bool(viga.get("OK", True))
        # Ligacao do CONSOLE a coluna (chapa+solda que recebe a viga de
        # rolamento excentrica). Dimensiona a perna do filete. L = altura de
        # solda ~ misula do console (build BRACKET 450mm); chapa 16mm (build).
        rc = cons.verifica_console({
            "Rv": reac["R_vertical_kN"], "Ht": reac.get("H_transversal_kN", 0.0),
            "ecc": pcfg.get("excentricidade", 0.30), "t": 0.016, "L": 0.45,
            "fy": params["fy"], "fu": params.get("fu", 400e3),
            "n_ciclos": reac.get("n_ciclos")})     # fadiga da solda (Anexo K cat.F)
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
        larg_b=g["span"], alt_h=g["eave"], comp_a=g.get("comprimento", 2 * g["span"]),
        abertura_dominante=_abert)))
    vl = vento.compute_longitudinal(b=g["span"], eave=g["eave"], ridge=g["ridge"],
                                    ca=params.get("ca_arrasto", 1.2),
                                    comp=g.get("comprimento", 2 * g["span"]),
                                    cf_atrito=params.get("cf_atrito", 0.04))
    save("gate5-vento-longitudinal.txt", vento.relatorio_longitudinal_pt(vl))
    res["Fa_long_kN"] = vl["Fa_kN"]; res["Fa_por_lado_kN"] = vl["Fa_por_lado_kN"]
    res["F_atrito_long_kN"] = vl["F_atrito_kN"]     # atrito 6.4 (soma no contravent.)
    # Gate 6 - analise
    a_gp = gp.analyse()                               # 1a ordem (tem os segmentos)
    save("gate6-portico.txt", gp.memoria_pt(a_gp))
    a = est.analyse()                                 # 2a ordem MAES (B1/B2 por grupo)
    save("gate6-2a-ordem.txt", est.memoria_pt(a))
    # envelope por segmento do rafter tapered: capturado do gp.analyse (tapered ainda
    # ativo; o redim adiante reseta TAPERED). B2 global do MAES amplifica os M (nao
    # muda QUAL segmento governa - so a magnitude).
    segs_tapered = a_gp.get("rafter_segmentos", []) if a_gp.get("tapered") else []
    segs_col_tapered = a_gp.get("coluna_segmentos", []) if a_gp.get("coluna_tapered") else []
    B2_amp = a.get("B2max", 1.0)
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
        # REGENERA o memorial do portico com as SECOES ADOTADAS. Os gates gate6-*
        # foram salvos ANTES do redimensionamento (secoes-semente), reportando um
        # drift/esforcos do frame que NAO e o adotado (ex.: drift 182 mm da semente
        # vs 26 mm do adotado). Apos a adocao, gp/est estao nas secoes que ATENDEM.
        # So no caminho prismatico (tapered mantem o memorial do rafter de alma
        # variavel capturado antes do reset do redim).
        if not segs_tapered and not segs_col_tapered:
            a_gp = gp.analyse()
            save("gate6-portico.txt", gp.memoria_pt(a_gp))
            save("gate6-2a-ordem.txt", est.memoria_pt(a))
    else:
        sc["perfil_col"] = perfis.PERFIS["HEA200"]
        sc["perfil_raf"] = perfis.PERFIS["HEA180"]
        # N_VAOS+1 colunas (o loop de verificacao percorre range(nv+1)). Com
        # N_VAOS o acesso cols_prof[nv] estourava (IndexError) na REPROVACAO, em
        # vez de retornar o veredito atende=False. Ver wiki 07 item E.
        res["perfil_colunas"] = ["HEA200"] * (gp.N_VAOS + 1)
        res["perfil_raf"] = "HEA180"
        res["atende"] = False
    # Gate 7 - mao-francesa
    slope = (g["ridge"] - g["eave"]) / (g["span"] / 2.0)
    n_terca = params["terca"].get("n_por_agua", 3)
    # AUTO-DIMENSIONA o n de tercas/agua: o espacamento das tercas e o VAO da telha;
    # sob a sucao local de vento a telha exige vao <= vao_max. Sobe n_terca ate
    # esp_terca <= vao_max (cap 12). Propaga em params -> terca, telha, Lb do rafter e 3D.
    if params.get("telha"):
        _w_agua = math.hypot(g["span"] / 2.0, g["ridge"] - g["eave"])
        _vt = vento.compute(larg_b=g["span"], alt_h=g["eave"],
                            comp_a=g.get("comprimento", 2 * g["span"]))
        _tc = dict(params["telha"].get("cfg", {}))
        _tc["W_sucao"] = _vt["local"]["p_local_cob_kN_m2"]
        _tc["Q"] = params["cargas"].get("Q", 0.25)
        _vmax = telha.vao_max(params["telha"]["perfil"], _tc)["vao_max_m"]
        if _vmax and _vmax > 0:
            _need = int(math.ceil(_w_agua / _vmax - 1e-6))
            if _need > n_terca:
                n_terca = min(_need, 12)
                params["terca"] = dict(params["terca"]); params["terca"]["n_por_agua"] = n_terca
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
    # EXPOE o n de tercas/agua auto-dimensionado: e o VAO DA TELHA, e o 3D precisa
    # construir com o MESMO valor que a memoria certificou (antes o build usava 3
    # hardcoded -> modelo/pranchas/takeoff com menos terca que o calculo exige).
    res["n_terca"] = n_terca
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
    # LARGURA DE INFLUENCIA = ESPACAMENTO REAL das tercas. O `ti.configurar` la em
    # cima roda ANTES da auto-dimensao do n_terca e usava params["terca"]["trib"],
    # que e o 1,675 m do galpao de REFERENCIA (vao 10 m, agua 5,025, n=3). No
    # galpao real a agua tem outro comprimento e o n_terca sobe ate a telha passar
    # -> a terca era verificada com carga MENOR do que recebe (na amostra 1,675
    # contra 2,022 m = 21% a menos). Reconfigura aqui, com o n_terca ja final.
    _w_agua_t = math.hypot(g["span"] / 2.0, g["ridge"] - g["eave"])
    _trib_real = _w_agua_t / max(n_terca, 1)
    ti.configurar(trib=_trib_real)
    save("gate7-tercas.txt", ti.memoria_pt())
    _rt = ti.melhor()
    res["terca_inter"] = round(_rt["interacao"], 2)
    res["terca_flecha_mm"] = round(_rt.get("flecha_v", 0.0), 1)
    res["terca_ok"] = bool(_rt.get("OK"))
    res["terca_dims"] = list(_rt.get("_dims", (200.0, 75.0, 25.0, 2.65)))
    res["terca_perfil"] = _rt.get("perfil")
    # Gate 7b - a PECA da mao-francesa (NBR 8800 4.11.3.4 + 5.3.2 + 5.3.4.1).
    # O gate 7 acima decide ONDE por o braco (stride); este decide se a peca
    # DESENHADA aguenta. Precisa da terca dimensionada (acima) para saber a
    # geometria do braco, por isso vem depois.
    try:
        import contencao_lateral as cl
        import mao_francesa_geom as mfg
        _raf = sc["perfil_raf"]
        _h0 = _raf["d"] - _raf["tf"]                       # centros das mesas (m)
        _ue_h = res["terca_dims"][0] / 1000.0              # terca dimensionada (m)
        _Lbr, _ = mfg.comprimento_braco(_raf["d"], _raf["bf"], _ue_h,
                                        math.atan(slope))
        # A SECAO e escolha do engenheiro: cantoneira (b,t) pelo spec, ou a barra
        # redonda historica. O gate verifica EXATAMENTE a peca que o 3D desenha.
        _mfs = params.get("mf_sec")
        _sec_br = (cl.secao_cantoneira(_mfs[0], _mfs[1], params["fy"]) if _mfs
                   else cl.secao_barra_redonda(mfg.DIAM_BRACO / 1000.0))
        _mf = cl.verifica_braco(
            Msd=abs(cbm_v["Msd"]), h0=_h0, Lbb=Lb_raf, L_braco=_Lbr,
            ang_graus=45.0, fy=params["fy"], sec=_sec_br)
        res["mf_peca_secao"] = _sec_br["nome"]
        save("gate7b-mao-francesa-peca.txt", cl.relatorio_pt(_mf))
        res["mf_peca_ok"] = bool(_mf["ok"])
        # float() explicito: Msd pode vir como np.float64 do frame2d e o repr de
        # numpy>=2 e "np.float64(5.02)" - literal invalido dentro do freecad, que
        # nao importa numpy. Foi exatamente isso que travou a tesoura executiva.
        res["mf_peca_u"] = round(float(max(
            _mf["N_braco"] / max(_mf["Nc_Rd"], 1e-9),
            _mf["esbeltez"] / cl.ESBELTEZ_MAX,
            _mf["Sbr_Sd"] / max(_mf["S_braco"], 1e-9))), 2)
        res["mf_peca_motivo"] = str(_mf["motivo"])
        if _mf.get("minimo"):
            res["mf_peca_minimo"] = {
                "r_min_mm": round(float(_mf["minimo"]["r_min"]) * 1000.0, 1),
                "Ag_min_cm2": round(float(_mf["minimo"]["A_min"]) * 1e4, 2)}
    except Exception as _ex:                               # gate opcional/gracioso
        res["mf_peca_erro"] = str(_ex)
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
    # Gate 7 - EMPOCAMENTO progressivo (NBR 8800 9.3): declividade < 3% exige
    # verificacao adicional do peso da agua acumulada. Cobre shed/aguas rasas,
    # que antes passavam sem qualquer verificacao de empocamento.
    import empocamento_nbr8800 as emp
    r_emp = emp.verifica_empocamento(emp.incl_pct_de_theta(gp.THETA))
    save("gate7-empocamento.txt", emp.relatorio_pt(r_emp))
    res["empocamento_incl_pct"] = round(r_emp["incl_pct"], 2)
    res["empocamento_ok"] = r_emp["OK"]
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
    Nmf = ctv.forca_estabilizacao_2pct(abs(cbm_v["Msd"]), sc["d_raf"])
    # Nsd do TIRANTE DE COBERTURA (sag rod): componente TANGENCIAL (down-slope) do
    # peso da cobertura (telhas + tercas G + sobrecarga Q), acumulada nas tercas de
    # uma agua ate a linha de tirante (NBR 8800 / Manual CBCA). A soma das
    # componentes das n_terca tercas equivale a:
    #   T_d = (1,25 G + 1,5 Q) * w_agua * sin(theta) * trib_tir
    # e w_agua*sin(theta) = (span/2)*tan(theta) = (ridge - eave). Assim a tracao
    # ESCALA com a inclinacao e o vao (nao mais fixa em 8 kN, que subestimava
    # telhados ingremes/longos). Mantem-se o valor da config como piso pratico
    # (pre-tensao de montagem). NAO inclui o peso proprio do rafter (self).
    n_tir_cob = max(int(sp["longarina"].get("n_tirantes", 2)), 1)
    trib_tir = g["bay"] / (n_tir_cob + 1)
    N_tir_d = ((1.25 * params["cargas"]["G"] + 1.5 * params["cargas"]["Q"])
               * (g["ridge"] - g["eave"]) * trib_tir)
    Nsd_tirante = max(N_tir_d, float(cb.get("Nsd_tirante", 0.0)))
    res["Nsd_tirante_kN"] = round(Nsd_tirante, 2)
    # AUTO-DIMENSIONA a bitola do contravento (parede+cobertura): menor diametro
    # padrao de barra redonda (mm) que faz AMBAS as diagonais passarem a tracao.
    # Antes era fixo em d20 e reprovava sob vento alto -> agora sobe a escada.
    _ROSCAS_MM = [20, 22, 25, 27, 32, 36, 40, 45, 50]
    _d0 = cb["d_contrav"] * 1000.0
    d_ctv = cb["d_contrav"]
    for _dmm in _ROSCAS_MM:
        if _dmm < _d0:
            continue
        _d = _dmm / 1000.0
        _bp = ctv.verifica_barra("_", _d, fyb, fub, Ndp, Ldp, pretensionada=True)
        _bc = ctv.verifica_barra("_", _d, fyb, fub, Ndc, Ldc, pretensionada=True)
        if _bp["OK"] and _bc["OK"]:
            d_ctv = _d
            break
    else:
        d_ctv = _ROSCAS_MM[-1] / 1000.0            # esgotou a escada: adota a maior
    cb["d_contrav"] = d_ctv                          # propaga p/ o gusset e o build
    _dtxt = "d%.0f" % (d_ctv * 1000.0)
    barras = [
        ctv.verifica_barra("Contravento de parede (%s)" % _dtxt, d_ctv, fyb, fub,
                           Ndp, Ldp, pretensionada=True),
        ctv.verifica_barra("Contravento de cobertura (%s)" % _dtxt, d_ctv, fyb, fub,
                           Ndc, Ldc, pretensionada=True),
        ctv.verifica_barra("Tirante de cobertura (d16)", cb["d_tirante"], fyb, fub,
                           Nsd_tirante, g["bay"] / 2.0, pretensionada=True),
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
        rg = gus.verifica_gusset({"N": gN, "t": G_T, "d_barra": cb["d_contrav"],
                                  "Lc": G_LC, "fy": params["fy"], "fu": params.get("fu", 400e3),
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
    # float() explicito: no numpy>=2 round(np.float64) segue np.float64 (repr
    # "np.float64(...)" polui prints e quebra json.dump). Coage a float nativo.
    res["base_gov"] = (bnm, round(float(bN), 1), round(float(bV), 1), round(float(bM), 1))
    res["knee_gov"] = (knm, round(float(kN), 1), round(float(kV), 1), round(float(kM), 1))
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
    # Gate 7 - ZONA DE PAINEL DO JOELHO (no rigido viga-coluna; NBR 8800 5.7.7 +
    # estados locais 5.7.2/5.7.3/5.7.6). So para porticos de NO RIGIDO (prismatico
    # e alma variavel); a tesoura e biapoiada (sem joelho) e nao dispara. Esforcos
    # do joelho (kM/kN/kV) ja extraidos em _esforcos_base_joelho.
    if params.get("tipo_portico") in (None, "prismatico", "alma_variavel"):
        tap = params.get("tapered") if params.get("tipo_portico") == "alma_variavel" else None
        if isinstance(tap, dict):
            # no tapered a secao do joelho (pilar e viga) e a mais funda (h_joelho).
            pj = av.props_I(tap["h_joelho"], tap.get("bf", 0.20),
                            tap.get("tw", 0.008), tap.get("tf", 0.0125))
            dc, tw_c, tf_c, bf_c, Ag_c = pj["d"], pj["tw"], pj["tf"], pj["bf"], pj["A"]
            d_viga, tf_viga = tap["h_joelho"], tap.get("tf", 0.0125)
        else:
            pc = perfis.PERFIS.get(res.get("perfil_col"), sc["perfil_col"])
            praf = sc["perfil_raf"]
            dc, tw_c, tf_c, bf_c, Ag_c = pc["d"], pc["tw"], pc["tf"], pc["bf"], pc["A"]
            d_viga, tf_viga = praf["d"], praf["tf"]
        caso_zp = {"M_Sd": abs(kM), "N_Sd": abs(kN), "V_col": abs(kV),
                   "dc": dc, "tw_col": tw_c, "bf_col": bf_c, "tf_col": tf_c,
                   "Ag_col": Ag_c, "d_viga": d_viga, "tf_viga": tf_viga,
                   "fy": params["fy"], "extremidade": False}
        rzp = zpn.verifica_painel(caso_zp)
        save("gate-zona-painel.txt", zpn.relatorio_pt(rzp, caso_zp))
        res["zona_painel"] = {
            "u_painel": round(rzp["u_painel"], 2), "u_local": round(rzp["u_local"], 2),
            "u_max": round(rzp["u_max"], 2),
            "precisa_reforco": rzp["precisa_reforco"], "t_doubler_mm": rzp["t_doubler_mm"],
            "precisa_enrijecedor": rzp["precisa_enrijecedor"],
            "FSd_kN": round(rzp["FSd"], 1), "F_Rd_kN": round(rzp["F_Rd"], 1)}

        # Enrijecedor transversal da alma do joelho (NBR 8800 §5.4.3.1) - so quando a
        # alma do joelho e esbelta E o V_Sd de pico excede o V_Rd sem enrijecedor
        # (kv=5). Sugere o MAIOR espacamento "a" que atende (menos enrijecedores),
        # reporta V_Rd(a), kv, I_st minimo. INFORMATIVO/opt-in: nao muda a utilizacao
        # a menos que o engenheiro adote os enrijecedores.
        if isinstance(tap, dict):
            sj = av.props_I(tap["h_joelho"], tap.get("bf", 0.20),
                            tap.get("tw", 0.008), tap.get("tf", 0.0125))
            V_sd_j = abs(kV)
            if ae.e_esbelta(sj, params["fy"]) and \
               enp.vrd(sj, params["fy"], None)["Vrd"] < V_sd_j:
                a_sug = enp.a_max_para_vsd(sj, params["fy"], V_sd_j)
                if a_sug is not None:
                    ve = enp.vrd(sj, params["fy"], a_sug)
                    ireq = enp.ist_req(sj, a_sug)
                    res["zona_painel"].update({
                        "enrij_a_sug_mm": round(a_sug * 1000, 0),
                        "enrij_kv": round(ve["kv"], 2),
                        "enrij_Vrd_kN": round(ve["Vrd"], 1),
                        "enrij_Vrd_sem_kN": round(
                            enp.vrd(sj, params["fy"], None)["Vrd"], 1),
                        "enrij_Ist_req_cm4": round(ireq * 1e8, 1)})

    # Gate 7 - SAPATA (NBR 6118) pelo ENVELOPE de combinacoes: cada verificacao
    # pega a combinacao que a governa (bearing = N max gravitacional ; tombamento
    # = N min + M ; etc). Pedestal ~ pilar adotado.
    sap = dict(params["fundacao"])
    if res.get("perfil_col") in perfis.PERFIS:
        pc = perfis.PERFIS[res["perfil_col"]]
        sap["b_ped"] = max(sap.get("b_ped", 0.30), round(pc["bf"] + 0.10, 2))
        sap["d_ped"] = max(sap.get("d_ped", 0.30), round(pc["d"] + 0.10, 2))
    # alvenaria autoportante: desce direto na fundacao (nao pela coluna de aco) ->
    # entra no envelope como permanente nas colunas externas (compressao + estabiliza
    # o uplift). Fechamento leve ja veio pela reacao de base (UDL no case_G).
    _N_mas = (params.get("parede") or {}).get("N_masonry_ext_kN", 0.0)
    casos_base = _casos_base_envelope(n_wall_perm_ext=_N_mas)
    _fund_tipo = params.get("fundacao", {}).get("tipo", "sapata")
    if _fund_tipo == "bloco":              # bloco de concreto simples (NBR 6122 7.8.2)
        dims = fs.dimensiona_bloco_env(sap, casos_base)
    else:
        dims = fs.dimensiona_sapata_env(sap, casos_base)
    save("gate7-fundacao.txt", dims["tabela"])

    # Alvenaria: a viga de baldrame sob a parede e dimensionada p/ o peso da alvenaria.
    _w_mas = (params.get("parede") or {}).get("w_masonry_kN_m", 0.0)
    if _w_mas > 0:
        params = dict(params)
        params["baldrame"] = dict(params.get("baldrame") or
                                  {"b": 0.20, "h": 0.40, "cobrimento": 0.05,
                                   "continuidade": "simples"})
        # sobrescreve (o default do PARAMS_REF traz q_parede=0.0 -> setdefault falharia)
        params["baldrame"]["q_parede"] = round(_w_mas, 3)

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
        M_base = max(abs(m) for _, _, _, m in casos_base)      # momento na base (envelope)
        ecfg = dict(params["estaca"]); ecfg.setdefault("N_pilar", round(N_pilar, 1))
        ecfg.setdefault("N_uplift", round(N_tr, 1))
        ecfg.setdefault("Mx", round(M_base, 1))                # flexo-compressao no grupo (Q2)
        ecfg.setdefault("D", 0.30); ecfg.setdefault("L", 10.0)
        # garante o bloco de coroamento no calculo (dims p/ desenhar o 3D)
        ecfg.setdefault("bloco", {"a_pilar": 0.30, "fck": 25e3, "fyk": 500e3})
        re_ = ep.verifica_estaca(ecfg)
        save("gate7-estaca.txt", ep.relatorio_pt(re_))
        Dp = ecfg["D"]; a_pil = (ecfg.get("bloco") or {}).get("a_pilar", 0.30)
        esp = (ecfg.get("bloco") or {}).get("espacamento", 3.0 * Dp)
        h_bloco = (re_.get("bloco") or {}).get("h", max(0.40, 1.2 * Dp))
        # OK/util consolidado da fundacao profunda (grupo + tracao + bloco), p/ o
        # QUADRO DE VERIFICACOES global (senao falha de fundacao passa silenciosa).
        _g = re_["grupo"]
        _ok_grupo = _g.get("OK")
        if _ok_grupo is None:
            _ok_grupo = (_g.get("util") or 0.0) <= 1.0
        _ok_est = bool(_ok_grupo and re_.get("tracao", {}).get("OK", True)
                       and re_.get("bloco", {}).get("OK", True))
        res["estaca"] = {"tipo": re_["capacidade"]["tipo_estaca"],
                         "P_adm_kN": re_["capacidade"]["P_adm_kN"],
                         "n_estacas": re_["grupo"]["n"], "N_pilar_kN": round(N_pilar, 1),
                         # geometria p/ o build 3D (tudo do calculo / envelope)
                         "D": Dp, "L": ecfg["L"], "espacamento": esp,
                         "bloco_h": h_bloco, "bloco_a": a_pil,
                         "uplift": bool(N_tr > 1e-6),
                         "util": _g.get("util"), "ok": _ok_est}

        # NBR 6122 8.5.6.1: blocos sobre 1 estaca (n=1) ou 1 linha de 2 estacas
        # (n=2) NAO tem rigidez rotacional na direcao perpendicular a linha das
        # estacas -> TRAVAMENTO em 2 direcoes ortogonais e OBRIGATORIO. O baldrame
        # longitudinal (gate7-baldrame) trava a direcao do comprimento; aqui
        # dimensiona-se a CINTA TRANSVERSAL, para a excentricidade executiva
        # acidental (>= 10% da carga vertical, NBR 6122 / Alonso).
        n_est_blk = re_["grupo"]["n"]
        if n_est_blk <= 2:
            blk = ecfg.get("bloco") or {}
            vao_tr = g.get("span") or (g["spans"][0] if g.get("spans") else g["bay"])
            N_cinta = 0.10 * N_pilar                     # amarracao acidental
            cfg_cinta = {"vao": vao_tr, "b": 0.20, "h": 0.40, "cobrimento": 0.05,
                         "q_parede": 0.0, "N_amarracao": round(N_cinta, 2),
                         "fck": blk.get("fck", 25e3), "fyk": blk.get("fyk", 500e3),
                         "continuidade": "simples"}
            rct = vbal.verifica_baldrame(cfg_cinta)
            save("gate7-travamento-transversal.txt",
                 f"TRAVAMENTO TRANSVERSAL OBRIGATORIO (NBR 6122 8.5.6 - bloco de "
                 f"{n_est_blk} estaca(s))\n"
                 f"Cinta de amarracao dimensionada p/ excentricidade executiva "
                 f"acidental N = 0,10*N_pilar = {N_cinta:.1f} kN "
                 f"(vao transversal {vao_tr:.2f} m).\n\n" + vbal.relatorio_pt(rct))
            res["travamento_transversal"] = {
                "obrigatorio": True, "n_estacas": n_est_blk,
                "N_amarracao_kN": round(N_cinta, 2), "vao": round(vao_tr, 2),
                "secao": f"{rct['b']*100:.0f}x{rct['h']*100:.0f}",
                "As_inf_cm2": rct["As_inf_cm2"], "ok": rct["OK"],
                "b": rct["b"], "h": rct["h"]}

    # Gate - CALHA (dimensionamento hidraulico, NBR 10844 / Bellei). Roda quando
    # ha calha na cobertura. Area de contribuicao da geometria: comprimento (ao
    # longo da calha) x meia-largura (uma agua) projetada; I pluviometrica do gate.
    if params.get("calha"):
        agua = g["span"] / 2.0 / max(math.cos(math.atan(slope)), 1e-6)
        # NBR 10844: parede vertical adjacente (platibanda/oitao acima da calha)
        # contribui com 50% da sua area (chuva com vento). h_elevacao = altura
        # dessa face vertical (m); 0,0 p/ calha de beiral sem platibanda.
        _cal = params["calha"]
        h_elev_calha = _cal.get("h_elevacao", 0.0) if isinstance(_cal, dict) else 0.0
        # AUTO-DIMENSIONA a secao da calha (B x H): sobe a secao ate drenar a vazao
        # de projeto (hidraulica + borda livre 25% + regra de Bellei 1 cm2/m2 de
        # telhado). Antes era fixa 100x80 mm e reprovava sob area/chuva grandes.
        _cand_bh = [(0.10, 0.08), (0.15, 0.10), (0.20, 0.12), (0.20, 0.15),
                    (0.25, 0.15), (0.25, 0.20), (0.30, 0.20), (0.30, 0.25),
                    (0.35, 0.25), (0.40, 0.30)]
        rca = None
        for _bb, _hh in _cand_bh:
            _r = calhas.dimensiona(g["comprimento"], agua, h_elevacao=h_elev_calha,
                                   I_mm_h=params.get("chuva_I_mm_h", 150.0),
                                   B_base=_bb, H_calha=_hh)
            if _r["ok"]:
                rca = _r
                break
        if rca is None:                                   # esgotou a escada de secoes
            rca = calhas.dimensiona(g["comprimento"], agua, h_elevacao=h_elev_calha,
                                    I_mm_h=params.get("chuva_I_mm_h", 150.0),
                                    B_base=0.40, H_calha=0.30)
        save("gate-calha.txt", calhas.relatorio_pt(rca))
        res["calha"] = {"vazao_Lmin": rca["vazao_Lmin"],
                        "B_mm": rca["secao"].get("B_base_m", 0) * 1000,
                        "H_mm": rca["secao"].get("H_max_m", 0) * 1000,
                        "condutor_mm": rca.get("condutor_diam_mm"),
                        "ok": rca["ok"]}

    # Gate - TERRENO (viabilidade urbanistica: TO/CA/TP + recuos, terreno.py). So
    # roda com params["terreno"] (lote KML/pontos + limites do zoneamento). Antes o
    # modulo era orfao (nunca importado); agora entra no quadro. Defensivo: qualquer
    # erro de parsing do lote nao derruba o dimensionamento estrutural.
    if params.get("terreno"):
        try:
            terr = terreno.analisa_terreno(params["terreno"])
            ver = terreno.verifica_galpao(
                terr, g["comprimento"], g["span"],
                n_pav=params["terreno"].get("n_pav", 1),
                area_pavimentada=params["terreno"].get("area_pavimentada", 0.0))
            save("gate-terreno.txt", terreno.relatorio_pt(terr, ver))
            res["terreno"] = {"area_lote_m2": terr["area_lote_m2"],
                              "footprint_m2": ver["footprint_m2"], "ok": ver["OK"]}
        except Exception as _e:
            res["terreno"] = {"erro": str(_e), "ok": None}

    # Gate 7 - FUNDACAO DE DIVISA (pilar na linha do lote). Duas variantes:
    #  - RASA  (sem estaca): sapata excentrica + viga alavanca (sapata_divisa).
    #  - PROFUNDA (com estaca): bloco excentrico sobre estacas + viga de equilibrio
    #    (viga_equilibrio), usando a P_adm da estaca ja calculada acima.
    # Carga = maior compressao da base (envelope); vizinho interno = mesma ordem;
    # vao da viga = bay.
    if params.get("divisa"):
        dvg = dict(params["divisa"])
        N_comp_d = abs(max(n for _, n, _, _ in casos_base))
        if params.get("estaca") and res.get("estaca"):          # variante PROFUNDA
            est_res = res["estaca"]
            rve = veq.dimensiona_viga_equilibrio(
                P_divisa=round(N_comp_d, 1), P_interno=round(N_comp_d, 1),
                dist_eixos=g["bay"], dist_divisa=dvg["dist_divisa"],
                P_estaca_adm=est_res["P_adm_kN"], a_pilar=est_res.get("bloco_a", 0.30),
                D_estaca=est_res.get("D", 0.30), e=dvg.get("e"),
                espacamento=est_res.get("espacamento"),
                fck=sap.get("fck", 25e3), fyk=sap.get("fyk", 500e3))
            save("gate7-divisa.txt", veq.relatorio_pt(rve))
            res["divisa"] = {"tipo": "estaca", "R_kN": rve["divisa"]["R"],
                             "e_m": rve["divisa"]["e"],
                             "n_estacas": rve["divisa"]["n_estacas"],
                             "viga_As_cm2": rve["viga"]["As_adot_cm2"],
                             "ok": bool(rve["viga"]["ok"])}
        else:                                                    # variante RASA
            rdv = sd.dimensiona_divisa(
                P_divisa=round(N_comp_d, 1), P_interno=round(N_comp_d, 1),
                dist_eixos=g["bay"], dist_divisa=dvg["dist_divisa"],
                sigma_solo=sap.get("sigma_solo_adm", 200.0),
                fck=sap.get("fck", 25e3), fyk=sap.get("fyk", 500e3))
            save("gate7-divisa.txt", sd.relatorio_pt(rdv))
            res["divisa"] = {"tipo": "sapata", "B": rdv["divisa"]["B"],
                             "L": rdv["divisa"]["L"], "R_kN": rdv["divisa"]["R"],
                             "e_m": rdv["divisa"]["e"],
                             "viga_As_cm2": rdv["viga"]["As_adot_cm2"],
                             "ok": bool(rdv["viga"]["ok"])}

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
        # VERIFICACAO DE ESTADOS-LIMITE (parecer Q2/2, correcoes):
        #  - FLA/FLM/flexo-compressao: LOCAIS -> por segmento com a secao local
        #    (dependem so de b/t e h/t locais). No verifica, Lb minusculo neutraliza
        #    a FLT (isola os estados locais).
        #  - FLT: fenomeno de TRECHO (nao por fatia). Calculada UMA vez por trecho
        #    destravado, com a MAIOR secao do trecho (a mais funda, conservador -
        #    AISC DG25 / NBR 8800 Anexo H) e o Lb correto:
        #      * gravidade domina -> mesa SUPERIOR comprimida -> Lb = tercas.
        #      * succao (vento) domina -> mesa INFERIOR comprimida -> Lb = maos-francesas.
        #    Aplicada como TETO a todos os segmentos (M_max*B2 vs M_Rd,FLT).
        segs_env = segs_tapered
        L_raft = math.hypot(g["span"] / 2.0, g["ridge"] - g["eave"])
        # CORTANTE DA ALMA com mesas inclinadas (equilibrio; Anexo J omisso em
        # cortante -> refino, nao clausula). Alivio favoravel so com opt-in; adverso
        # sempre contado. dh/dx do rafter = (h_joelho - h_cumeeira)/L_raft.
        creditar_cme = bool(params.get("creditar_cortante_mesa_inclinada", False))
        dhdx_raf = cta.dh_dx(tp["h_cumeeira"], tp["h_joelho"], L_raft)
        sent_raf = cta.sentido_haunch(segs_env)
        cme_alivio_max = 0.0                             # maior reserva/acrescimo (kN)
        n_terca = params["terca"].get("n_por_agua", 3)
        # n_por_agua = numero de VAOS (espacos) entre tercas na meia-agua, com
        # travamento tambem no beiral e na cumeeira -> espacamento = L_raft/n_terca
        # (mesmo divisor do vao da telha na L300 e do modelo em build_galpao). NAO
        # dividir por n_terca+1 (fencepost): subestimaria Lb e superestimaria a FLT.
        Lb_terca = L_raft / n_terca                     # mesa sup (gravidade)
        Lb_mf = Lb_raf                                   # mesa inf (succao) - mao-francesa
        # secao mais funda do rafter (governa a FLT do trecho)
        deep = max((s for s in segs_env if s.get("sec_props")),
                   key=lambda s: s.get("h_m") or 0, default=None)
        # LOCAIS por segmento (FLT neutralizada com Lb->0)
        verifs = []
        for seg in segs_env:
            sp = seg.get("sec_props")
            if not sp:
                continue
            sec_seg = dict(sp); sec_seg["nome"] = "seg%d%s" % (
                seg["seg"], "E" if seg["lado"] == 0 else "D")
            Msd_s = seg["M"] * B2_amp; Nsd_s = seg["N"] * B2_amp
            cme = cta.cortante_efetivo_conservador(
                Msd_s, seg["V"], seg.get("h_m") or sec_seg["d"], dhdx_raf,
                sent_raf, creditar_cme, tf=sec_seg["tf"])
            cme_alivio_max = max(cme_alivio_max, cme["alivio"], cme["acrescimo"])
            v = chk.verifica(sec_seg, params["fy"], L=seg.get("L_seg") or Lb_raf,
                             Nsd=Nsd_s, Msd=Msd_s, Vsd=cme["V_usar"], Kx=1, Ky=1,
                             Lb=1e-3, nome=sec_seg["nome"])   # Lb->0: sem FLT local
            v["_seg"] = seg
            verifs.append(v)
        # FLT de TRECHO (member-level) por NBR 8800 ANEXO J: lambda da secao de MAIOR
        # altura (J.4.2), Cb por analise racional (J.4.1, 5.4.2.3a) do diagrama de M
        # do trecho e demanda na secao de MAIOR tensao M/Wx (nao M_max cego). Dois
        # regimes de Lb (gravidade=tercas / succao=maos-francesas). B2 amplifica M.
        M_max = max((s["M"] for s in segs_env), default=0.0) * B2_amp
        segs_flt = [{"M": s["M"] * B2_amp, "props": s["sec_props"], "h_m": s["h_m"]}
                    for s in segs_env if s.get("sec_props")]
        flt = {}
        cb_raf = 1.0
        if segs_flt:
            for regime, Lb_f, mesa in (("gravidade(tercas)", Lb_terca, "superior"),
                                       ("succao(maos-francesas)", Lb_mf, "inferior")):
                rj = fltm.flt_misula(segs_flt, params["fy"], Lb_f)
                cb_raf = rj["Cb"]
                flt[regime] = {"Lb": Lb_f, "mesa": mesa, "M_Rd_flt": rj["M_Rd"],
                               "u": rj["util"], "secao_critica": rj["secao_critica"]}
        u_flt = max((f["u"] for f in flt.values()), default=0.0)
        flt_sec_crit = next(iter(flt.values()), {}).get("secao_critica")
        # CROSS-CHECK DG25 (validacao INFORMATIVA; nao altera dimensionamento). Compara
        # o M_eLTB elastico do DG25 (secao do MEIO, 5.4.3) com o Mcr do NBR Anexo J
        # (secao mais funda, J.4.2). Lb do regime que governa a FLT.
        cc_raf = None; ccap_raf = None
        if segs_flt and flt:
            Lb_gov = max(flt.values(), key=lambda f: f["u"])["Lb"]
            cc_raf = dg25.cross_check_flt(segs_flt, params["fy"], Lb_gov, Cb=cb_raf)
            # fase 6.14: cross-check de CAPACIDADE (Mn nominal completo, Rpc/Rpg/3
            # regioes; Cb NAO cancela). INFORMATIVO - nao muda dimensionamento.
            ccap_raf = dg25.cross_check_capacidade(segs_flt, params["fy"], Lb_gov,
                                                   Cb=cb_raf)
        # relatorio
        L += ["", "  ESTADOS LOCAIS POR SEGMENTO (FLA/FLM/flexo-compressao; FLT a parte):",
              "    seg |  h(mm) | Msd(kN.m) | interacao_local | governa"]
        gov_seg = None
        for v in verifs:
            s = v["_seg"]
            L.append("    %3d%s | %6.0f | %9.1f | %14.2f | %s" %
                     (s["seg"], "E" if s["lado"] == 0 else "D", (s["h_m"] or 0) * 1000,
                      s["M"], v["interacao"], s.get("gov", "")))
            if gov_seg is None or v["interacao"] > gov_seg["interacao"]:
                gov_seg = v
        L += ["", "  FLT DE TRECHO (member-level, NBR 8800 Anexo J; secao de maior "
              "altura h=%.0f mm, Cb=%.2f):"
              % ((deep["h_m"] or 0) * 1000 if deep else 0, cb_raf)]
        for regime, f in flt.items():
            L.append("    %-24s Lb=%.2f m (mesa %s) -> M_Rd,FLT=%.1f kN.m ; "
                     "demanda na secao %s (max M/Wx, J.4.1) -> u=%.2f" %
                     (regime, f["Lb"], f["mesa"], f["M_Rd_flt"],
                      f.get("secao_critica"), f["u"]))
        u_local = gov_seg["interacao"] if gov_seg else 0.0
        gs = gov_seg["_seg"] if gov_seg else {}
        no_joelho = bool(gov_seg) and not (
            (gs.get("seg") == 0 and gs.get("lado") == 0) or
            (gs.get("seg") == gp.NSEG - 1 and gs.get("lado") == 1))
        u_geral = max(u_local, u_flt)
        L += ["",
              "  >> util local max = %.2f (seg %s%s)%s" % (
                  u_local, gs.get("seg", "?"), "E" if gs.get("lado") == 0 else "D",
                  "  [!] NAO e o joelho (Wx cai mais rapido que M)" if no_joelho else ""),
              "  >> util FLT trecho = %.2f (%s)" % (
                  u_flt, "succao(mesa inf) governa" if flt and
                  flt.get("succao(maos-francesas)", {}).get("u", 0) >= u_flt - 1e-9
                  else "gravidade(mesa sup)"),
              "  >> UTILIZACAO GOVERNANTE = %.2f (%s)" % (
                  u_geral, "FLT de trecho" if u_flt >= u_local else "estado local do segmento"),
              "  [NBR 8800 Anexo J] FLT: lambda da secao de maior altura (J.4.2), Cb",
              "         racional (J.4.1, 5.4.2.3a), demanda na secao de max M/Wx. O",
              "         fator gamma (AISC DG25) NAO e adotado - nao e normativo na NBR.",
              "  >> Portico resolvido com rigidez variavel (secao por segmento)."]
        if cc_raf is not None:
            L += ["  [CROSS-CHECK DG25 (informativo, nao-normativo)] M_eLTB elastico "
                  "AISC DG25 5.4.3:",
                  "         M_eLTB(secao MEIO h=%.0fmm)=%.1f kN.m ; Mcr(NBR Anexo J, "
                  "secao FUNDA h=%.0fmm)=%.1f kN.m" % (
                      cc_raf["sec_meio"], cc_raf["M_dg"], cc_raf["sec_funda"],
                      cc_raf["M_nbr"]),
                  "         razao DG25/NBR = %.3f -> %s (tol +-%.0f%%). NAO altera o "
                  "dimensionamento (segue a NBR)." % (
                      cc_raf["razao"], "CONVERGE" if cc_raf["converge"] else "DIVERGE",
                      cc_raf["tol"] * 100)]
        if ccap_raf is not None:
            L += ["  [CROSS-CHECK DG25 CAPACIDADE (informativo)] Mn nominal completo "
                  "(Rpc/Rpg/3 regioes, regiao %s):" % ccap_raf["regiao_dg"],
                  "         Mn_DG(meio h=%.0fmm)=%.1f kN.m ; Mn_NBR(funda h=%.0fmm)="
                  "%.1f kN.m -> razao=%.3f %s" % (
                      ccap_raf["sec_meio"], ccap_raf["Mn_dg"], ccap_raf["sec_funda"],
                      ccap_raf["Mn_nbr"], ccap_raf["razao"],
                      "CONVERGE" if ccap_raf["converge"] else "DIVERGE")]
        # ---- COLUNA TAPERED (opcional; h_col_base no gate) ----
        # Mesma logica do rafter: estados LOCAIS por segmento (Lb->0 neutraliza FLT)
        # + FLT de TRECHO (member-level) com a secao mais funda da coluna (o joelho).
        # Lb da coluna = contrato de travamento (params["Lb"]["col"]): mesa externa
        # travada pela longarina de fechamento, mesa interna pela mao-francesa.
        col_res = None
        if segs_col_tapered:
            Lb_col = params["Lb"]["col"]
            # cortante da alma com mesas inclinadas (coluna): dh/dx = (h_joelho -
            # h_col_base)/H_col ; sentido pela geometria dos segmentos.
            dhdx_col = cta.dh_dx(tp["h_col_base"], tp["h_joelho"], g["eave"])
            sent_col = cta.sentido_haunch(segs_col_tapered)
            verifs_c = []
            for seg in segs_col_tapered:
                sp = seg.get("sec_props")
                if not sp:
                    continue
                sec_c = dict(sp); sec_c["nome"] = "col%d_%d" % (seg["coluna"], seg["seg"])
                Msd_c = seg["M"] * B2_amp; Nsd_c = seg["N"] * B2_amp
                cme_c = cta.cortante_efetivo_conservador(
                    Msd_c, seg["V"], seg.get("h_m") or sec_c["d"], dhdx_col,
                    sent_col, creditar_cme, tf=sec_c["tf"])
                cme_alivio_max = max(cme_alivio_max, cme_c["alivio"], cme_c["acrescimo"])
                v = chk.verifica(sec_c, params["fy"], L=seg.get("L_seg") or Lb_col,
                                 Nsd=Nsd_c, Msd=Msd_c, Vsd=cme_c["V_usar"], Kx=1, Ky=1,
                                 Lb=1e-3, nome=sec_c["nome"])   # Lb->0: sem FLT local
                v["_seg"] = seg
                verifs_c.append(v)
            # FLT da coluna por Anexo J (seção maior altura J.4.2 + Cb racional J.4.1)
            segs_col_flt = [{"M": s["M"] * B2_amp, "props": s["sec_props"],
                             "h_m": s["h_m"]} for s in segs_col_tapered
                            if s.get("sec_props")]
            rj_c = fltm.flt_misula(segs_col_flt, params["fy"], Lb_col) if segs_col_flt \
                else {"util": 0.0, "Cb": 1.0}
            u_col_flt = rj_c["util"]
            cb_col = rj_c["Cb"]
            cc_col = dg25.cross_check_flt(segs_col_flt, params["fy"], Lb_col,
                                          Cb=cb_col) if segs_col_flt else None
            # COMPRESSAO GLOBAL da coluna (Anexo J.3): a verificacao por segmento usa
            # L=L_seg (~0,75 m) e NAO captura a flambagem GLOBAL por flexao ao longo
            # dos ~H metros. J.3 exige Nc,Rd pela secao de MENOR altura (base) com o
            # comprimento de flambagem do membro inteiro (K racional; aqui K=1 no
            # plano nao-sway + B2 do MAES ja amplifica o sway). N_Sd = axial maximo.
            sec_min = av.props_I(tp["h_col_base"], tp.get("bf", 0.20),
                                 tp.get("tw", 0.008), tp.get("tf", 0.0125))
            sec_min["nome"] = "coluna_base(menor_altura)"
            N_col_max = max((abs(s["N"]) for s in segs_col_tapered), default=0.0) * B2_amp
            H_col = g["eave"]
            vg = chk.verifica(sec_min, params["fy"], L=H_col, Nsd=N_col_max, Msd=0.0,
                              Vsd=0.0, Kx=1.0, Ky=1.0, Lb=Lb_col,
                              nome=sec_min["nome"])
            u_col_global = vg["u_N"]
            # INTERACAO M-V no joelho (5.5.2.3): a alma esbelta do joelho ve o M e o
            # V de pico juntos; as checagens separadas (flexao Anexo J + cortante
            # 5.4.3) nao capturam a tensao COMBINADA no ponto (juncao mesa-alma).
            # So dispara se a alma do joelho for esbelta (Anexo H); chi_v vem da
            # esbeltez ao cisalhamento da propria alma. chi_n=1 (a flambagem normal
            # ja e coberta pela FLT/FLM de trecho). Esforcos amplificados por B2.
            u_col_5523 = 0.0; r5523 = None
            sec_joelho = av.props_I(tp["h_joelho"], tp.get("bf", 0.20),
                                    tp.get("tw", 0.008), tp.get("tf", 0.0125))
            if ae.e_esbelta(sec_joelho, params["fy"]):
                Awj = sec_joelho["d"] * sec_joelho["tw"]
                chi_v = min(1.0, vg["Vrd"] * chk.GA1 / (0.6 * Awj * params["fy"]))
                r5523 = tsp.verifica_5523(sec_joelho, params["fy"],
                                          Nsd=abs(kN) * B2_amp, Msd=abs(kM) * B2_amp,
                                          Vsd=abs(kV), chi_n=1.0, chi_v=chi_v)
                u_col_5523 = max(r5523["u_sigma_a"], r5523["u_tau_b"],
                                 r5523["u_sigma_c"], r5523["u_tau_d"], r5523["u_vm"])
            gov_c = None
            for v in verifs_c:
                if gov_c is None or v["interacao"] > gov_c["interacao"]:
                    gov_c = v
            u_col_local = gov_c["interacao"] if gov_c else 0.0
            u_col_geral = max(u_col_local, u_col_flt, u_col_global, u_col_5523)
            L += ["", "  COLUNA TAPERED (base rasa -> joelho fundo; h_col_base=%.0f mm):"
                  % (tp["h_col_base"] * 1000),
                  "    seg |  h(mm) | Msd(kN.m) | interacao_local | governa"]
            for v in verifs_c:
                s = v["_seg"]
                L.append("    %3d | %6.0f | %9.1f | %14.2f | %s" %
                         (s["seg"], (s["h_m"] or 0) * 1000, s["M"], v["interacao"],
                          s.get("gov", "")))
            _gov_nome = max((("local", u_col_local), ("FLT de trecho", u_col_flt),
                             ("compressao global J.3", u_col_global),
                             ("interacao M-V joelho 5.5.2.3", u_col_5523)),
                            key=lambda x: x[1])[0]
            L += ["  >> COLUNA: util local max = %.2f ; FLT trecho (Anexo J, Lb=%.2f m, "
                  "Cb=%.2f) = %.2f" % (u_col_local, Lb_col, cb_col, u_col_flt),
                  "     compressao GLOBAL (Anexo J.3, secao menor altura h=%.0f mm, "
                  "H=%.2f m, N_Sd=%.1f kN) = %.2f" % (
                      tp["h_col_base"] * 1000, H_col, N_col_max, u_col_global)]
            if r5523 is not None:
                L += ["     interacao M-V no JOELHO esbelto (5.5.2.3 tensoes, "
                      "juncao mesa-alma; govs a/b/c/d + vonMises): %.2f (gov %s ; "
                      "von Mises=%.2f)" % (u_col_5523, r5523["gov"], r5523["u_vm"])]
            L += ["     GOVERNANTE = %.2f (%s)" % (u_col_geral, _gov_nome)]
            if cc_col is not None:
                L += ["     [cross-check DG25 (informativo)] M_eLTB(meio h=%.0fmm)=%.1f "
                      "; Mcr(NBR funda h=%.0fmm)=%.1f -> razao=%.3f %s" % (
                          cc_col["sec_meio"], cc_col["M_dg"], cc_col["sec_funda"],
                          cc_col["M_nbr"], cc_col["razao"],
                          "CONVERGE" if cc_col["converge"] else "DIVERGE")]
            col_res = {"util_col_local_max": round(u_col_local, 2),
                       "util_col_flt": round(u_col_flt, 2),
                       "util_col_global": round(u_col_global, 2),
                       "util_col_mv_5523": round(u_col_5523, 2),
                       "interacao_max_col": round(u_col_geral, 2),
                       "cb_misula_col": round(cb_col, 3),
                       "h_col_base_mm": tp["h_col_base"] * 1000,
                       "dg25_razao_col": round(cc_col["razao"], 3) if cc_col else None,
                       "dg25_converge_col": cc_col["converge"] if cc_col else None}
        L.append("=" * 66)
        save("gate6-alma-variavel.txt", "\n".join(L))
        res["alma_variavel"] = {
            "h_joelho_mm": tp["h_joelho"] * 1000, "h_cumeeira_mm": tp["h_cumeeira"] * 1000,
            "peso_kN_m": round(peso, 2), "nseg": gp.NSEG,
            "I_joelho_cm4": round(secs[0]["I_m4"] * 1e8, 0),
            "I_cumeeira_cm4": round(secs[-1]["I_m4"] * 1e8, 0),
            "util_local_max": round(u_local, 2),
            "util_flt_trecho": round(u_flt, 2),
            "interacao_max_seg": round(u_geral, 2),
            "seg_governante": ("%d%s" % (gs.get("seg"),
                               "E" if gs.get("lado") == 0 else "D")) if gov_seg else None,
            "governa_joelho": not no_joelho if gov_seg else None,
            "governa_flt": bool(u_flt >= u_local),
            "cb_misula_raf": round(cb_raf, 3),
            "flt_secao_critica": flt_sec_crit,
            "cortante_mesa_alivio_kN": round(cme_alivio_max, 1),
            "cortante_mesa_creditado": creditar_cme,
            "cortante_mesa_sentido": ("haunch/alivio" if sent_raf >= 0
                                      else "adverso/acrescimo"),
            "dg25_razao_raf": round(cc_raf["razao"], 3) if cc_raf else None,
            "dg25_converge_raf": cc_raf["converge"] if cc_raf else None,
            "dg25_cap_razao_raf": round(ccap_raf["razao"], 3) if ccap_raf else None,
            "dg25_cap_regiao_raf": ccap_raf["regiao_dg"] if ccap_raf else None,
            "dg25_cap_converge_raf": ccap_raf["converge"] if ccap_raf else None}
        if col_res:
            res["alma_variavel"].update(col_res)

    # Gate 6 - PORTICO TRELICADO (tesoura). So com tipo_portico=tesoura: a
    # cobertura vira trelica biapoiada nos pilares. Carga por metro de banzo = carga
    # de cobertura (permanente+sobrecarga) x largura tributaria (bay). Sucção de
    # vento AUTO-ACOPLADA da NBR 6123 (envelope da zona de cobertura), salvo override.
    if params.get("tipo_portico") == "tesoura" and params.get("trelica"):
        tr = dict(params["trelica"])
        c = params["cargas"]
        w_grav = (c["G"] + c["Q"] + c.get("self", 0.0)) * g["bay"]   # combo gravidade
        w_dead = (c["G"] + c.get("self", 0.0)) * g["bay"]            # estabiliza uplift (sem Q)
        # SUCCAO de vento auto-acoplada (NBR 6123 Tabela 5). Cpi CONSISTENTE (parecer
        # item 41, pt.1): um unico Cpi (o mais desfavoravel = mais positivo) aplicado
        # SIMULTANEAMENTE a todas as superficies - net = Cpe - Cpi_max (par fixo, nao
        # min independente por agua). qb = q * bay.
        qb = vr["q_kN_m2"] * g["bay"]
        cpe = vr["cpe"]; cpi_max = max(vr["cpi_cases"].values())
        # (a) vento a 90 (transversal): Cpe por AGUA, barlavento (EF) x sotavento (GH),
        #     ASSIMETRICO e simultaneo.
        net_barl = round(cpe["cobertura_barlavento"] - cpi_max, 2)
        net_sot = round(cpe["cobertura_sotavento"] - cpi_max, 2)
        w_barl = round(net_barl * qb, 3); w_sot = round(net_sot * qb, 3)
        # (b) vento a 0 (longitudinal): as DUAS aguas do portico ficam na MESMA zona
        #     (EG, mais negativa) -> uplift SIMETRICO. Parecer item 41 pt.2: este caso
        #     pode governar (simetria) e NAO pode ser omitido.
        cl = vento.cpe_telhado_longitudinal(vr["theta"])
        net_eg = round(cl["cobertura_long_EG"] - cpi_max, 2)
        w_long = round(net_eg * qb, 3)
        # (c) comparacao: uniforme-pior antigo (min de tudo em todo o vao).
        w_vento_uniforme = round(min(net_barl, net_sot, net_eg) * qb, 3)
        w_vento_in = tr.get("w_vento_kN_m")
        base = {"L": g["span"], "h": tr["h"], "n_paineis": tr.get("n_paineis", 8),
                "tipo": tr.get("tipo", "warren"),
                "w_grav_kN_m": tr.get("w_grav_kN_m", round(w_grav, 3)),
                "w_dead_kN_m": tr.get("w_dead_kN_m", round(w_dead, 3)),
                "fy": tr.get("fy", 250e3),
                "perfil_banzo": tr["perfil_banzo"], "perfil_diagonal": tr["perfil_diagonal"]}
        # ENVELOPE dos casos de vento: override manual (uniforme) tem prioridade;
        # senao envelopa 90 (por agua) + 0 (simetrico longitudinal). Pior u_max.
        if w_vento_in is not None:
            casos_v = [("input(uniforme)", dict(base, w_vento_kN_m=w_vento_in))]
            fonte = "input"
        else:
            casos_v = [("vento 90 (transversal, por agua)",
                        dict(base, w_vento_zonas=(w_barl, w_sot))),
                       ("vento 0 (longitudinal, simetrico EG)",
                        dict(base, w_vento_zonas=(w_long, w_long)))]
            fonte = "auto"
        rt = None; caso_gov = None
        for nome_v, cfg_v in casos_v:
            rti = tes.verifica_tesoura(cfg_v)
            if rt is None or rti["u_max"] > rt["u_max"]:
                rt = rti; caso_gov = nome_v
        rel = tes.relatorio_tesoura_pt(rt)
        rel += ("\n\n  SUCCAO DE VENTO (NBR 6123 Tabela 5, Cpi consistente = %.2f):\n"
                "    q = %.3f kN/m2 ; bay = %.2f m\n"
                "    (a) 90 transversal: barlavento(EF) net=%.2f -> %.3f kN/m ; "
                "sotavento(GH) net=%.2f -> %.3f kN/m (assimetrico)\n"
                "    (b) 0 longitudinal: EG net=%.2f -> %.3f kN/m nas DUAS aguas "
                "(simetrico)\n"
                "    [comparacao] uniforme-pior antigo = %.3f kN/m\n"
                "    combinacao: 1,4 w_vento(agua) + gamma_g w_dead (0,9 succao / 1,4 "
                "pressao) ; cumeeira = media das aguas ; envelope 90+0 + 2 direcoes.\n"
                "    -> CASO GOVERNANTE: %s ; u_max = %.2f (%s)"
                % (cpi_max, vr["q_kN_m2"], g["bay"], net_barl, w_barl, net_sot, w_sot,
                   net_eg, w_long, w_vento_uniforme, caso_gov, rt["u_max"],
                   "OK" if rt["OK"] else "NAO PASSA"))
        save("gate6-tesoura.txt", rel)
        res["tesoura"] = {"tipo": rt["tipo"], "u_max": rt["u_max"], "OK": rt["OK"],
                          "N_banzo_sup_max": rt["N_banzo_sup_max"],
                          "N_banzo_inf_max": rt["N_banzo_inf_max"],
                          "n_paineis": rt["n_paineis"], "h_m": rt["h_m"],
                          "w_vento_barl_kN_m": w_barl, "w_vento_sot_kN_m": w_sot,
                          "w_vento_long_kN_m": w_long, "vento_caso_governante": caso_gov,
                          "w_vento_uniforme_kN_m": w_vento_uniforme, "w_vento_fonte": fonte,
                          # back-compat (contrato do item 37)
                          "w_vento_auto_kN_m": w_vento_uniforme,
                          "w_vento_usado_kN_m": (w_vento_in if w_vento_in is not None
                                                 else w_vento_uniforme)}

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
    if _fund_tipo == "bloco":              # bloco: concreto simples, sem armadura
        if dims["aprovado"]:
            bB, bL, bh, beta = dims["aprovado"]; gv = dims["governantes"]
            res["sapata_adotada"] = {"B": bB, "L": bL, "h": bh, "tipo": "bloco",
                                     "beta": round(beta, 1), "As_L": 0.0, "As_B": 0.0,
                                     "rigida": True, "arm_L": None, "arm_B": None}
            res["sapata_util"] = round(max(gv.get("solo", ("", 0))[1],
                                           1.0 / gv.get("tomb", ("", 9))[1],
                                           1.0 / gv.get("desl", ("", 9))[1]), 2)
            res["sapata_ok"] = bool(res["sapata_util"] <= 1.001)
        else:
            res["sapata_adotada"] = None; res["sapata_ok"] = False
    elif dims["aprovado"]:
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
        # OK = geotecnico (solo/tombamento/desliz.) E estrutural do concreto
        # (flexao B/L, compressao diagonal, puncao) via rB["OK_B"]. Sem o OK_B,
        # uma ruptura de armadura/puncao passaria com sapata_util<=1 (so solo).
        res["sapata_ok"] = bool(res["sapata_util"] <= 1.001 and rB.get("OK_B", True))
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
        res["fogo_theta"] = rf["theta_aco_C"]
        res["fogo_ky"] = rf["ky"]
        res["fogo_TRRF"] = rf["TRRF_min"]
        # A temperatura (C) NAO e uma utilizacao (bug 8.34: 550 C virava
        # "util 550 > 1 -> NAO ATENDE" sempre). Verificacao ao fogo: aco abaixo da
        # temperatura critica no TRRF. theta_critica (NBR 14323, ~550 C p/ mu~0,6,
        # A CONFIRMAR pelo eng.) configuravel. util = theta/theta_critica.
        theta_cr = fg.get("theta_critica_C", 550.0)
        res["fogo_util"] = round(rf["theta_aco_C"] / theta_cr, 2)
        res["fogo_ok"] = bool(rf["theta_aco_C"] <= theta_cr)
        # Ask-Do-Not-Invent: theta_critica e lambda_p da protecao vem do eng./
        # boletim. Se defaultados, flaga no memorial (nao bloqueia - o gate do
        # ProjetoSpec ja avisa; aqui deixa o rastro na memoria de calculo).
        res["fogo_theta_cr"] = theta_cr
        res["fogo_theta_cr_default"] = fg.get("theta_critica_C") is None
        res["fogo_lambda_p_default"] = bool(rf.get("lambda_p_default"))
        _txt_fogo = fogo.relatorio_pt(rf)
        if res["fogo_theta_cr_default"]:
            _txt_fogo += ("\n  [DEFAULT - CONFIRMAR: theta_critica = 550 C (mu~0,6, "
                          "NBR 14323) assumida; depende do nivel de carregamento a "
                          "quente. Informe params['fogo']['theta_critica_C'].]")
        save("gate8-fogo.txt", _txt_fogo)
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
             ("3c. PORTICO TRELICADO (TESOURA)", "gate6-tesoura.txt"),
             ("4. PERFIS", "gate7-check-perfis.txt"),
             ("5. MAO-FRANCESA", "gate7-mao-francesa.txt"), ("6. TERCAS", "gate7-tercas.txt"),
             ("6b. TELHA", "gate7-telha.txt"),
             ("7. SECUNDARIOS", "gate7-secundarios.txt"),
             ("8. CONTRAVENTAMENTO", "gate7-contraventamento.txt"),
             ("8b. GUSSET DE CONTRAVENTO", "gate7-gusset.txt"),
             ("9. VERGA DA PORTA", "gate7-verga.txt"),
             ("10. BASE", "gate7-base.txt"),
             ("11. %s (FUNDACAO)" % ("BLOCO DE CONCRETO SIMPLES"
                 if params.get("fundacao", {}).get("tipo") == "bloco" else "SAPATA"),
              "gate7-fundacao.txt"),
             ("11b. VIGA DE BALDRAME", "gate7-baldrame.txt"),
             ("11c. FUNDACAO PROFUNDA (ESTACA)", "gate7-estaca.txt"),
             ("11d. TRAVAMENTO TRANSVERSAL (CINTA)", "gate7-travamento-transversal.txt"),
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
        # Converte um estado booleano (OK/nao) em "util-like": None se o gate nao
        # rodou (chave ausente -> pulado no quadro); 0,0 se OK; 1,99 se NAO ATENDE
        # (>1,0 -> aparece como falha). Antes usava-se "0 if ok else None", que
        # PULAVA as falhas (None), escondendo-as do quadro.
        def _bok(key, okfield="ok"):
            if key not in res:
                return None
            d = res[key]
            ok = d.get(okfield, True) if isinstance(d, dict) else bool(d)
            return 0.0 if ok else 1.99
        # util-like a partir de uma util PLANA + flag de OK (chaves separadas em res):
        # forca >1,0 se o OK reprovar mesmo com util <= 1 (ex.: base sob interacao,
        # sapata sob puncao, viga de rolamento sob fadiga/flecha).
        def _uok(util_key, ok_key):
            u = res.get(util_key)
            if u is None:
                return None
            return u if res.get(ok_key, True) else max(u, 1.99)
        # idem para util ANINHADA em res[key] (dict com ufield/okfield).
        def _uokd(key, ufield="u_max", okfield="OK"):
            d = res.get(key)
            if not isinstance(d, dict):
                return None
            u = d.get(ufield)
            if u is None:
                return _bok(key, okfield)
            return u if d.get(okfield, True) else max(u, 1.99)
        # Estaca: usa a util real do grupo, forcando >1,0 se qualquer estado (grupo/
        # tracao/bloco) reprovar mesmo com util <= 1.
        est = res.get("estaca")
        u_est = None
        if est is not None:
            u_est = est.get("util") or 0.0
            if not est.get("ok", True):
                u_est = max(u_est, 1.99)
        # Junta de dilatacao: "precisa" = excede o comprimento sem junta -> acao
        # requerida (o modulo trata como nao-OK). Ausente -> pulado.
        u_junta = None
        if "junta_dilatacao" in res:
            u_junta = 1.99 if res["junta_dilatacao"].get("precisa") else 0.0
        checks = [("Coluna", res.get("interacao_col")), ("Viga", res.get("interacao_raf")),
                  ("Tesoura (trelica)", _uokd("tesoura", "u_max", "OK")),
                  ("Flecha portico", res.get("flecha_util")),
                  ("Base (placa+chumbador)", _uok("base_util", "base_ok")),
                  ("Bloco (fundacao)" if (res.get("sapata_adotada") or {}).get("tipo")
                   == "bloco" else "Sapata (fundacao)",
                   _uok("sapata_util", "sapata_ok")),
                  ("Joelho", res.get("joelho_util")),
                  ("Zona de painel (joelho)", _uokd("zona_painel", "u_max", "OK")),
                  ("Terca", res.get("terca_inter")), ("Telha", _uok("telha_util", "telha_ok")),
                  ("Empocamento (9.3)", None if "empocamento_ok" not in res
                   else (0.0 if res["empocamento_ok"] else 1.99)),
                  ("Longarina", res.get("longarina_inter")), ("Escora", res.get("escora_inter")),
                  ("Montante", res.get("montante_inter")), ("Verga", res.get("verga_inter")),
                  ("Contrav./tirantes", _uok("barras_u_max", "barras_ok")),
                  ("Gusset contravento", _uok("gusset_u_max", "gusset_ok")),
                  ("Mao-francesa (peca)", res.get("mf_peca_u")),
                  ("Viga rolamento", _uok("ponte_viga_inter", "ponte_viga_ok")),
                  ("Console ponte", _uok("console_u_max", "console_ok")),
                  ("Fogo (theta/theta_cr)", _uok("fogo_util", "fogo_ok")),
                  # Verificacoes globais antes ausentes do quadro (falha silenciosa):
                  ("Estaca (fund. profunda)", u_est),
                  ("Travamento transversal", _bok("travamento_transversal")),
                  ("Baldrame longitudinal", _bok("baldrame")),
                  ("Sismo (theta 2a ordem)", _bok("sismo_theta")),
                  ("Junta de dilatacao", u_junta),
                  ("Calha (hidraulica)", _bok("calha")),
                  ("Fundacao de divisa", _bok("divisa")),
                  ("Terreno (TO/CA/TP)", _bok("terreno")),
                  ("Escada", None if "escada_ok" not in res else (0.0 if res["escada_ok"] else 1.99)),
                  ("Plataforma", None if "plataforma_ok" not in res else (0.0 if res["plataforma_ok"] else 1.99))]
        L.append("QUADRO DE VERIFICACOES (util = solicitacao/resistencia <= 1,0):")
        for nome, u in checks:
            if u is None:
                continue
            L.append(f"  {nome:<16} {u:5.2f}   "
                     f"{'OK' if u <= 1.001 else '*** NAO ATENDE ***'}")
        falhas = [(n, u) for n, u in checks if u is not None and u > 1.001]
        # veredito GLOBAL agregado (todos os gates que rodaram, nao so o portico):
        # exposto no res p/ o rodar_tudo/relatorio consolidado. res["atende"] segue
        # sendo o do redimensionamento do portico (nao quebra chamadores).
        res["falhas_verificacao"] = [(n, round(float(u), 2)) for n, u in falhas]
        res["atende_global"] = not falhas
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
