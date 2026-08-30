# ============================================================================
# galpao_hidraulica.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Vertical de HIDRAULICA PREDIAL do galpao: DIMENSIONA a rede (pela norma, modulo
# hidraulica_predial) E a roteia no MODELO FEDERADO e no CLASH do turnkey.
#
#   DIMENSIONAMENTO (hidraulica_predial, lido dos PDFs - regra AR300):
#     - PLUVIAL (NBR 10844): Q = i*A/60 a partir da AREA DE TELHADO (geometria do
#       galpao) -> DN do condutor (Tab.4). Sempre calculado; i (intensidade local)
#       e' DADO DE SITIO -> default 150 mm/h flagado [A CONFIRMAR] (Tab.5 por cidade).
#     - AGUA FRIA (NBR 5626:2020): se 'aparelhos_agua' informado, soma as vazoes de
#       projeto (Tab.B.4) e dimensiona por velocidade (v<=3 m/s, Sec.6.8.3) -> DN.
#     - ESGOTO (NBR 8160): se 'aparelhos_esgoto' informado, soma UHC (Tab.3) e
#       dimensiona o coletor (Tab.7) -> DN.
#   Sem os aparelhos, agua/esgoto caem em DEFAULT comercial explicitamente flagado
#   (nunca um valor de norma inventado). O override por diametro no spec sempre vence.
#
#   COORDENACAO: a rede vira membros (tubos) no federado -> o clash acha interferencia
#   tubo x estrutura/duto/eletrocalha (coordenacao real).
#     - pluvial: condutores verticais (descidas) no perimetro (do beiral ao solo);
#     - esgoto: coletor horizontal sob o piso ao longo do comprimento;
#     - agua fria: barrilete no forro ao longo do comprimento.
# Frame comum do turnkey (X=comprimento, Y=largura, Z=altura; mm; secao de barra m).
# ============================================================================
"""Vertical de hidraulica predial: DIMENSIONA (NBR 5626:2020/8160/10844 via
hidraulica_predial) e roteia pluvial/esgoto/agua fria no modelo federado + clash."""

from __future__ import annotations

import hidraulica_predial as hp

# diametros COMERCIAIS de fallback (mm) quando agua/esgoto nao tem aparelhos no spec
# -> explicitamente [A CONFIRMAR] (nunca norma inventada). Pluvial NAO tem fallback:
# e' sempre calculado a partir da area de telhado (geometria).
D_ESGOTO_DEFAULT_MM = 100.0     # [A CONFIRMAR] coletor de esgoto (informar aparelhos_esgoto)
D_AGUA_DEFAULT_MM = 50.0        # [A CONFIRMAR] barrilete de agua fria (informar aparelhos_agua)
N_CONDUTORES_PADRAO = 4         # condutores pluviais (1 por canto), sobrescrivivel


def rodar(spec):
    """Dimensiona e roteia a rede hidraulica do galpao.
    spec: {geometria{L,W,H} (m), hidraulica{ n_condutores, i_pluvial_mm_h,
           decl_pluvial_pct, decl_esgoto_pct, area_telhado_m2, aparelhos_agua{tipo:qtd},
           aparelhos_esgoto{tipo:qtd}, D_pluvial_mm/D_esgoto_mm/D_agua_mm (override) }(opc)}.
    Retorna {geometria, redes, gates, reprovados, ATENDE, dimensionamento}."""
    geo = spec.get("geometria") or {}
    if not all(k in geo for k in ("L", "W", "H")):
        raise ValueError("[A CONFIRMAR] geometria {L,W,H} (m) obrigatoria p/ hidraulica.")
    L = float(geo["L"]); W = float(geo["W"]); H = float(geo["H"])
    if L <= 0 or W <= 0 or H <= 0:
        raise ValueError("[A CONFIRMAR] geometria do galpao invalida (L,W,H > 0); "
                         "recebido L=%s W=%s H=%s." % (L, W, H))
    # aceita os parametros aninhados em spec['hidraulica'] (uso standalone) OU no topo
    # do spec (como o turnkey passa o sub-spec de cada disciplina).
    hid = spec.get("hidraulica") or spec
    n_cond = int(hid.get("n_condutores", N_CONDUTORES_PADRAO))

    # --- PLUVIAL: dimensionado pela area de telhado (NBR 10844 Sec.5.3.1) ---
    if hid.get("D_pluvial_mm") is not None:
        d_pl = float(hid["D_pluvial_mm"]); pluv = {"D_mm": d_pl, "fonte": "spec"}
    else:
        i_pl = float(hid.get("i_pluvial_mm_h", hp.I_PLUVIAL_PADRAO_MM_H))
        decl_pl = float(hid.get("decl_pluvial_pct", 1.0))
        area_tel = float(hid.get("area_telhado_m2", L * W))     # projecao horizontal
        # cada CONDUTOR/CALHA drena uma FRACAO do telhado (area / n de pontos de descida),
        # nao o telhado inteiro. Sem isso o condutor era superdimensionado e a calha
        # SATURAVA em silencio (Q do telhado todo numa unica calha).
        area_ponto = area_tel / max(1, n_cond)
        plc = hp.diametro_pluvial(area_ponto, i_pl, decl_pl)
        d_pl = float(plc["DN_mm"])
        pluv = {"D_mm": d_pl, "fonte": "NBR 10844", "Q_Lmin": plc["Q_Lmin"],
                "i_mm_h": plc["i_mm_h"], "i_default": plc["i_default"],
                "area_m2": round(area_tel, 1), "area_por_ponto_m2": round(area_ponto, 1),
                "saturado": plc["saturado"]}
        # CALHA semicircular (NBR 10844 Tab.3): pela area por ponto de drenagem. Default de
        # declividade 1% (o minimo da norma e' 0,5%, Sec.5.7.1, mas 1% e' a pratica usual).
        cal = hp.diametro_calha(area_ponto, plc["i_mm_h"],
                                declividade_pct=float(hid.get("decl_calha_pct", 1.0)))
        pluv["calha_mm"] = cal["DN_mm"]
        pluv["calha_saturada"] = cal["saturado"]
    pluv["n_condutores"] = n_cond
    pluv["default"] = False        # pluvial e' sempre dimensionado (geometria) ou do spec

    # --- AGUA FRIA: dimensionada se aparelhos informados. Metodo de vazao selecionavel
    # (ambos aceitos pela NBR 5626:2020 Sec.6.14.2): "soma" (Tab.B.4, conservador; default)
    # ou "pesos" (NBR 5626:1998 Anexo A, Q=0,3*raiz(SP), simultaneo). ---
    apar_ag = hid.get("aparelhos_agua")
    metodo_ag = hid.get("metodo_agua", "soma")
    if hid.get("D_agua_mm") is not None:
        agua = {"D_mm": float(hid["D_agua_mm"]), "fonte": "spec", "default": False}
    elif apar_ag:
        agc = hp.diametro_agua(apar_ag, metodo=metodo_ag)
        fonte = "NBR 5626:1998 (pesos)" if metodo_ag == "pesos" else "NBR 5626:2020 (soma)"
        agua = {"D_mm": float(agc["DN_mm"]), "fonte": fonte, "default": False,
                "metodo": agc["metodo"], "Q_Ls": agc["Q_Ls"], "v_real_ms": agc["v_real_ms"]}
        if "soma_P" in agc:
            agua["soma_P"] = agc["soma_P"]
        # VERIFICACAO DE PRESSAO do barrilete (NBR 5626:1998 Anexo A.2, Fair-Whipple-Hsiao)
        # ate o ponto mais desfavoravel. Traçado a partir da geometria: barrilete corre no
        # comprimento (L) e desce ao ponto; queda = pe-direito. p_alim (pressao disponivel no
        # inicio) e' DADO DE SITIO -> default flagado. Conexoes representativas do trecho.
        p_alim = float(hid.get("p_alim_kPa", 100.0))       # [A CONFIRMAR] rede/reservatorio
        L_real = L + H                                     # barrilete + queda ao ponto (m)
        dcota = H - 1.0                                    # barrilete (~forro) ao ponto (~1 m)
        # ponto de utilizacao mais EXIGENTE do conjunto governa o minimo (Sec.5.3.5.1):
        # valvula de descarga de bacia -> 15 kPa; senao 10 kPa (geral).
        tipo_ponto = "valvula_descarga" if "bacia_valvula" in (apar_ag or {}) else "geral"
        vp = hp.verifica_pressao(agc["Q_Ls"], agc["DN_mm"], L_real, p_alim,
                                 conexoes={"cotovelo_90": 3, "te_direta": 1, "te_lateral": 1},
                                 dcota_m=dcota, tipo_ponto=tipo_ponto)
        vp["p_alim_default"] = "p_alim_kPa" not in hid
        agua["pressao"] = vp
    else:
        agua = {"D_mm": D_AGUA_DEFAULT_MM, "fonte": "default", "default": True}

    # --- AGUA QUENTE (NBR 5626:2020): a norma UNIFICOU agua fria e quente (SPAFAQ) - as
    # vazoes de projeto, o limite de velocidade (3 m/s, Sec.6.8.3) e as pressoes (Sec.6.9)
    # aplicam-se IDENTICAMENTE. So dimensiona se 'aparelhos_agua_quente' informado (o
    # subconjunto de pecas com ponto quente: misturadores/chuveiro/banheira/pia). Material
    # liso (CPVC/cobre) -> mesmo Fair-Whipple-Hsiao. Reusa as mesmas ferramentas da fria. ---
    apar_aq = hid.get("aparelhos_agua_quente")
    agua_quente = None
    if apar_aq:
        aqc = hp.diametro_agua(apar_aq, metodo=metodo_ag)
        agua_quente = {"D_mm": float(aqc["DN_mm"]), "fonte": "NBR 5626:2020 (quente)",
                       "metodo": aqc["metodo"], "Q_Ls": aqc["Q_Ls"],
                       "v_real_ms": aqc["v_real_ms"]}
        if "soma_P" in aqc:
            agua_quente["soma_P"] = aqc["soma_P"]
        tipo_q = "valvula_descarga" if "bacia_valvula" in apar_aq else "geral"
        vpq = hp.verifica_pressao(aqc["Q_Ls"], aqc["DN_mm"], L + H,
                                  float(hid.get("p_alim_kPa", 100.0)),
                                  conexoes={"cotovelo_90": 3, "te_direta": 1},
                                  dcota_m=H - 1.0, tipo_ponto=tipo_q)
        vpq["p_alim_default"] = "p_alim_kPa" not in hid
        agua_quente["seguranca"] = hp.verifica_agua_quente_seguranca(
            hid.get("agua_quente_seguranca"), aqc["Q_Ls"], vpq["p_residual_kPa"])
        agua_quente["pressao"] = vpq

    # --- ESGOTO: dimensionado se aparelhos informados (NBR 8160) ---
    apar_es = hid.get("aparelhos_esgoto")
    if hid.get("D_esgoto_mm") is not None:
        esgoto = {"D_mm": float(hid["D_esgoto_mm"]), "fonte": "spec", "default": False}
    elif apar_es:
        decl_es = float(hid.get("decl_esgoto_pct", 1.0))
        uhc, dn_desc = hp.uhc_de_aparelhos(apar_es)
        colc = hp.diametro_coletor_sat(uhc, decl_es)
        d_es = float(colc["DN_mm"])
        # VENTILACAO (NBR 8160 Sec.5.2.2): ramal de ventilacao por UHC (Tab.8; com bacia se
        # ha bacia sanitaria no conjunto) + coluna pelo DN do esgoto (Tab.D.1).
        com_bacia = "bacia" in apar_es
        ventc = hp.diametro_ramal_ventilacao_sat(uhc, com_bacia=com_bacia)
        vent = float(ventc["DN_mm"])
        vent_col = float(hp.diametro_coluna_ventilacao(d_es))
        # SATURACAO: a Tab.7 (coletor) e a Tab.8 (ventilacao) tem teto. Quando a UHC
        # excede a ultima linha, o DN sai igual ao maior tabelado e NAO comporta o
        # fluxo - antes isso passava em silencio (ver saturacao-silenciosa).
        esgoto = {"D_mm": d_es, "fonte": "NBR 8160", "default": False,
                  "uhc": uhc, "dn_ramal_min_mm": dn_desc,
                  "ventilacao_ramal_mm": vent, "ventilacao_coluna_mm": vent_col,
                  "coletor_saturado": bool(colc["saturado"]),
                  "ventilacao_saturada": bool(ventc["saturado"])}
    else:
        esgoto = {"D_mm": D_ESGOTO_DEFAULT_MM, "fonte": "default", "default": True}

    redes = {"pluvial": pluv, "esgoto": esgoto, "agua_fria": agua}
    if agua_quente:
        redes["agua_quente"] = agua_quente

    # mensagem de dimensionamento: o que foi calculado e o que ficou [A CONFIRMAR]
    partes = []
    if pluv["fonte"] == "NBR 10844":
        cav = " [A CONFIRMAR i local]" if pluv.get("i_default") else ""
        cal = (" + calha DN%.0f" % pluv["calha_mm"]) if pluv.get("calha_mm") else ""
        sat = (" [SATURADO - aumentar declividade ou n condutores]"
               if pluv.get("saturado") or pluv.get("calha_saturada") else "")
        partes.append("pluvial DN%.0f%s calculado NBR 10844 (Q=%.0f L/min/ponto; "
                      "i=%.0f mm/h%s)%s"
                      % (pluv["D_mm"], cal, pluv["Q_Lmin"], pluv["i_mm_h"], cav, sat))
    else:
        partes.append("pluvial DN%.0f (spec)" % pluv["D_mm"])
    if agua.get("metodo") == "pesos":
        partes.append("agua fria DN%.0f calculado NBR 5626:1998 metodo dos pesos "
                      "(ΣP=%.1f; Q=%.2f L/s; v=%.1f m/s)"
                      % (agua["D_mm"], agua.get("soma_P", 0.0), agua["Q_Ls"],
                         agua["v_real_ms"]))
    elif agua.get("metodo") == "soma":
        partes.append("agua fria DN%.0f calculado NBR 5626:2020 metodo da soma "
                      "(Q=%.2f L/s; v=%.1f m/s)"
                      % (agua["D_mm"], agua["Q_Ls"], agua["v_real_ms"]))
    elif agua["fonte"] == "spec":
        partes.append("agua fria DN%.0f (spec)" % agua["D_mm"])
    else:
        partes.append("agua fria DN%.0f default comercial [A CONFIRMAR - informe "
                      "aparelhos_agua]" % agua["D_mm"])
    if agua.get("pressao"):     # verificacao de pressao do barrilete (Fair-Whipple-Hsiao)
        vp = agua["pressao"]
        cav = " [A CONFIRMAR p_alim]" if vp.get("p_alim_default") else ""
        partes.append("pressao residual %.0f kPa (min %.0f, %s%s)"
                      % (vp["p_residual_kPa"], vp["p_min_kPa"],
                         "OK" if vp["OK"] else "INSUF.", cav))
    if agua_quente:
        aq = agua_quente; vpq = aq["pressao"]
        cavq = " [A CONFIRMAR p_alim]" if vpq.get("p_alim_default") else ""
        partes.append("agua quente DN%.0f calculado NBR 5626:2020 SPAFAQ (Q=%.2f L/s; "
                      "v=%.1f m/s; p.res %.0f kPa %s%s)"
                      % (aq["D_mm"], aq["Q_Ls"], aq["v_real_ms"], vpq["p_residual_kPa"],
                         "OK" if vpq["OK"] else "INSUF.", cavq))
        partes.append("seguranca agua quente: %s"
                      % ("OK" if aq["seguranca"]["OK"] else "INCONCLUSIVA/REPROVA"))
    if esgoto["fonte"] == "NBR 8160":
        sat_es = (" [SATURADO - subdividir o trecho ou aumentar a declividade]"
                  if esgoto.get("coletor_saturado") or esgoto.get("ventilacao_saturada")
                  else "")
        partes.append("esgoto DN%.0f (ventilacao ramal DN%.0f/coluna DN%.0f) calculado "
                      "NBR 8160 (UHC=%.1f)%s"
                      % (esgoto["D_mm"], esgoto["ventilacao_ramal_mm"],
                         esgoto["ventilacao_coluna_mm"], esgoto["uhc"], sat_es))
    elif esgoto["fonte"] == "spec":
        partes.append("esgoto DN%.0f (spec)" % esgoto["D_mm"])
    else:
        partes.append("esgoto DN%.0f default comercial [A CONFIRMAR - informe "
                      "aparelhos_esgoto]" % esgoto["D_mm"])
    dimensionamento = "; ".join(partes)
    completo = not (agua["default"] or esgoto["default"])
    if agua_quente and not agua_quente["seguranca"]["OK"]:
        completo = False

    pluvial_sat = bool(pluv.get("saturado") or pluv.get("calha_saturada"))
    esgoto_sat = bool(esgoto.get("coletor_saturado") or esgoto.get("ventilacao_saturada"))
    gates = {"rede": {"n_condutores_pluvial": n_cond, "D_pluvial_mm": pluv["D_mm"],
                      "D_esgoto_mm": esgoto["D_mm"], "D_agua_mm": agua["D_mm"],
                      "dimensionamento": dimensionamento, "pluvial_saturado": pluvial_sat,
                      "dimensionamento_completo": completo, "OK": n_cond >= 1}}
    if esgoto["fonte"] == "NBR 8160":
        # gate EFETIVO: tabela saturada = trecho fora do alcance da norma, REPROVA
        # (subdividir o coletor/a ventilacao ou aumentar a declividade).
        gates["esgoto_saturacao"] = {
            "coletor_saturado": bool(esgoto.get("coletor_saturado")),
            "ventilacao_saturada": bool(esgoto.get("ventilacao_saturada")),
            "uhc": esgoto["uhc"], "OK": not esgoto_sat}
    if agua.get("pressao"):
        vp = agua["pressao"]
        # gate INFORMATIVO se p_alim foi assumido (dado de sitio); EFETIVO se informado
        # no spec (ai a pressao insuficiente reprova de verdade).
        gates["pressao_agua"] = {
            "p_residual_kPa": vp["p_residual_kPa"], "p_min_kPa": vp["p_min_kPa"],
            "perda_kPa": vp["perda_kPa"], "p_alim_assumida": vp.get("p_alim_default", False),
            "OK": vp["OK"] or vp.get("p_alim_default", False)}
    if agua_quente:
        vpq = agua_quente["pressao"]
        gates["pressao_agua_quente"] = {
            "p_residual_kPa": vpq["p_residual_kPa"], "p_min_kPa": vpq["p_min_kPa"],
            "perda_kPa": vpq["perda_kPa"], "p_alim_assumida": vpq.get("p_alim_default", False),
            "OK": vpq["OK"] or vpq.get("p_alim_default", False)}
        seg = agua_quente["seguranca"]
        gates["seguranca_agua_quente"] = {
            "OK": seg["OK"], "inconclusivo": seg["inconclusivo"],
            "faltantes": list(seg["faltantes"]),
            "violacoes": list(seg["violacoes"]),
        }
    r = {"geometria": {"L": L, "W": W, "H": H}, "redes": redes,
         "dimensionamento": dimensionamento, "dimensionamento_completo": completo,
         "gates": gates}
    r["reprovados"] = [k for k, g in gates.items() if not g["OK"]]
    r["ATENDE"] = len(r["reprovados"]) == 0
    return r


def membros_bim(r):
    """Modelo neutro da rede hidraulica (tubos) no frame comum (mm; secao de barra em m).
    Pluvial: condutores verticais no perimetro (beiral->solo). Esgoto: coletor no piso
    ao longo do comprimento. Agua fria: barrilete no forro. Lista vazia sem geometria."""
    geo = r.get("geometria") or {}
    if not all(k in geo for k in ("L", "W", "H")):
        return []
    L = geo["L"] * 1000.0; W = geo["W"] * 1000.0; H = geo["H"] * 1000.0     # mm
    redes = r["redes"]
    M = []

    # PLUVIAL: condutores verticais (descidas) no perimetro, do beiral (z=H) ao solo
    n = max(0, int(redes["pluvial"].get("n_condutores", N_CONDUTORES_PADRAO)))
    Dpl = redes["pluvial"]["D_mm"] / 1000.0                                 # m
    per = [(0.0, 0.0), (L, 0.0), (L, W), (0.0, W)]                          # cantos
    for i in range(n):
        x, y = per[i % 4]
        M.append({"tipo": "Pipe", "perfil": "Condutor pluvial D%.0f" % (Dpl * 1000),
                  "marca": "PLUV%d" % (i + 1), "secao": {"forma": "ROUND", "D": Dpl},
                  "p1": [x, y, H], "p2": [x, y, 0.0], "material": "PVC"})
    # ESGOTO: coletor horizontal sob o piso (z = -300 mm), no eixo central
    Des = redes["esgoto"]["D_mm"] / 1000.0
    M.append({"tipo": "Pipe", "perfil": "Coletor esgoto D%.0f" % (Des * 1000),
              "marca": "ESG-C", "secao": {"forma": "ROUND", "D": Des},
              "p1": [0.0, W / 2.0, -300.0], "p2": [L, W / 2.0, -300.0], "material": "PVC"})
    # AGUA FRIA: barrilete no forro (z = H - 300 mm), ao longo do comprimento
    Dag = redes["agua_fria"]["D_mm"] / 1000.0
    M.append({"tipo": "Pipe", "perfil": "Barrilete agua fria D%.0f" % (Dag * 1000),
              "marca": "AGUA-B", "secao": {"forma": "ROUND", "D": Dag},
              "p1": [0.0, W / 4.0, H - 300.0], "p2": [L, W / 4.0, H - 300.0],
              "material": "PVC"})
    # AGUA QUENTE: barrilete paralelo ao de agua fria (y = W/4 + 200 mm), no forro. So
    # existe se a rede de agua quente foi dimensionada (aparelhos_agua_quente).
    if redes.get("agua_quente"):
        Daq = redes["agua_quente"]["D_mm"] / 1000.0
        M.append({"tipo": "Pipe", "perfil": "Barrilete agua quente D%.0f" % (Daq * 1000),
                  "marca": "AGUA-Q", "secao": {"forma": "ROUND", "D": Daq},
                  "p1": [0.0, W / 4.0 + 200.0, H - 300.0],
                  "p2": [L, W / 4.0 + 200.0, H - 300.0], "material": "CPVC"})
    # CALHA pluvial no beiral (z = H), ao longo do comprimento numa agua (y = 0). Cruza
    # a ponta das tercas/beiral -> clash de coordenacao.
    if redes["pluvial"].get("calha_mm"):
        Dcal = redes["pluvial"]["calha_mm"] / 1000.0
        M.append({"tipo": "Pipe", "perfil": "Calha D%.0f" % (Dcal * 1000),
                  "marca": "CALHA", "secao": {"forma": "ROUND", "D": Dcal},
                  "p1": [0.0, 0.0, H], "p2": [L, 0.0, H], "material": "PVC"})
    # COLUNA DE VENTILACAO: sobe do coletor (z = -300) atravessando o telhado ate 1 m
    # acima da cumeeira (z = H + 1000) -> cruza terca/telha (clash real).
    if redes["esgoto"].get("ventilacao_coluna_mm"):
        Dv = redes["esgoto"]["ventilacao_coluna_mm"] / 1000.0
        M.append({"tipo": "Pipe", "perfil": "Coluna de ventilacao D%.0f" % (Dv * 1000),
                  "marca": "VENT-C", "secao": {"forma": "ROUND", "D": Dv},
                  "p1": [L * 0.5, W / 2.0, -300.0], "p2": [L * 0.5, W / 2.0, H + 1000.0],
                  "material": "PVC"})
    return M


def emitir_bim(r, path, nome="GalpaoHidraulica"):
    """Emite o IFC4 da rede hidraulica (via ifc_emit puro). None sem geometria/ifcopenshell."""
    import ifc_emit
    if not ifc_emit.disponivel():
        return None
    membros = membros_bim(r)
    if not membros:
        return None
    return ifc_emit.emitir_ifc(membros, path, nome=nome, secao_em_metros=True)


def montar_pranchas(r, out_dir, spec=None, freecad_exe=None, timeout=1200):
    """Gera o PROJETO EXECUTIVO (pranchas A1 TechDraw) da hidraulica a partir de rodar(r).
    NAO precisa de FCStd (o esquema e' SVG do desenho_hidraulica). Roda o freecad.exe
    grafico (job por QTimer, janela fecha sozinha). Mesma mecanica dos demais
    montar_pranchas. Retorna {ok, pranchas, arquivos, fcstd} | {erro}."""
    import os, json, time, tempfile, subprocess
    import techdraw_hidraulica as TDH
    import rodar_projeto as RP

    exe = freecad_exe or os.environ.get("FREECAD_EXE") or \
        r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe"
    if not os.path.exists(exe):
        return {"erro": "freecad.exe nao encontrado: %s" % exe}

    cfg = TDH.config_de_spec(r, str(out_dir), spec)
    prdir = os.path.join(str(out_dir), "pranchas")
    os.makedirs(prdir, exist_ok=True)
    status = os.path.join(prdir, "_status_hid.json")
    try:
        os.remove(status)
    except OSError:
        pass

    boot = tempfile.NamedTemporaryFile(mode="w", suffix="_exec_hid.py",
                                       delete=False, encoding="utf-8")
    boot.write(TDH.script_bootstrap(cfg))
    boot.close()

    proc = subprocess.Popen([exe, boot.name],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    res = None
    try:
        while time.time() - t0 < timeout:
            if os.path.exists(status):
                time.sleep(0.5)
                with open(status, encoding="utf-8") as f:
                    res = json.load(f)
                break
            if proc.poll() is not None and not os.path.exists(status):
                time.sleep(2)
                res = ({"erro": "freecad.exe encerrou sem status"}
                       if not os.path.exists(status)
                       else json.load(open(status, encoding="utf-8")))
                break
            time.sleep(2)
        if res is None:
            res = {"erro": "timeout %ss aguardando pranchas de hidraulica" % timeout}
    finally:
        RP._matar_processo_freecad(proc)
        try:
            os.unlink(boot.name)
        except OSError:
            pass
    return res


def relatorio_pt(r):
    g = r["gates"]["rede"]
    L = ["HIDRAULICA PREDIAL - GALPAO (NBR 5626:2020 / 8160 / 10844)",
         "  Pluvial: %d condutores DN%.0f mm" % (g["n_condutores_pluvial"],
                                                 g["D_pluvial_mm"]),
         "  Esgoto: coletor DN%.0f mm ; Agua fria: barrilete DN%.0f mm" % (
             g["D_esgoto_mm"], g["D_agua_mm"]),
         "  DIMENSIONAMENTO: %s" % g["dimensionamento"],
         "  RESULTADO: %s (%s)" % (
             "ATENDE" if r["ATENDE"] else "REPROVA",
             "dimensionamento completo" if r["dimensionamento_completo"]
             else "parcial - ver [A CONFIRMAR]")]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # sem aparelhos: pluvial JA e' calculado (geometria); agua/esgoto em default flagado
    r = rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}})
    assert r["ATENDE"] is True
    assert r["redes"]["pluvial"]["fonte"] == "NBR 10844"          # sempre dimensionado
    assert r["redes"]["pluvial"].get("i_default") is True         # i local flagado
    assert r["redes"]["agua_fria"]["default"] and r["redes"]["esgoto"]["default"]
    assert r["dimensionamento_completo"] is False
    assert "A CONFIRMAR" in r["dimensionamento"]
    # telhado 800 m2 / 4 condutores = 200 m2/ponto ; Q = 150*200/60 = 500 L/min -> Tab.4
    # 1%: DN125 (521>=500). Nao satura (cada condutor drena so a sua fracao do telhado).
    assert r["redes"]["pluvial"]["D_mm"] == 125.0, r["redes"]["pluvial"]
    assert r["redes"]["pluvial"]["area_por_ponto_m2"] == 200.0
    assert r["redes"]["pluvial"]["saturado"] is False
    assert r["gates"]["rede"]["pluvial_saturado"] is False

    # com aparelhos: agua+esgoto CALCULADOS pela norma -> dimensionamento completo
    r2 = rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2, "chuveiro": 2},
                               "aparelhos_esgoto": {"bacia": 2, "lavatorio": 2, "chuveiro": 2}}})
    assert r2["redes"]["agua_fria"]["fonte"] == "NBR 5626:2020 (soma)"    # default = soma
    assert r2["redes"]["agua_fria"]["metodo"] == "soma"
    # verificacao de pressao do barrilete (Fair-Whipple-Hsiao) presente e coerente
    vp = r2["redes"]["agua_fria"]["pressao"]
    assert vp["J_kPa_m"] > 0 and vp["p_residual_kPa"] < vp["p_disponivel_kPa"]
    assert vp["p_alim_default"] is True and "pressao_agua" in r2["gates"]
    assert "pressao residual" in r2["dimensionamento"]
    assert r2["redes"]["esgoto"]["fonte"] == "NBR 8160"
    assert r2["dimensionamento_completo"] is True
    assert "A CONFIRMAR - informe" not in r2["dimensionamento"]

    # AGUA QUENTE (SPAFAQ): reusa as ferramentas da fria nos pontos de agua quente
    rq = rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                "hidraulica": {"aparelhos_agua": {"lavatorio": 3, "chuveiro": 2},
                               "aparelhos_agua_quente": {"lavatorio": 3, "chuveiro": 2}}})
    aq = rq["redes"]["agua_quente"]
    assert aq["fonte"] == "NBR 5626:2020 (quente)" and aq["D_mm"] > 0
    assert "pressao" in aq and "pressao_agua_quente" in rq["gates"]
    assert "agua quente" in rq["dimensionamento"] and "SPAFAQ" in rq["dimensionamento"]
    assert any(m["marca"] == "AGUA-Q" for m in membros_bim(rq))
    # sem aparelhos_agua_quente -> nao ha rede quente
    assert "agua_quente" not in r2["redes"]

    # metodo dos pesos (NBR 5626:1998): mesmo conjunto -> vazao simultanea MENOR que a soma
    rp = rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                "hidraulica": {"metodo_agua": "pesos",
                               "aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2,
                                                  "chuveiro": 2}}})
    ap = rp["redes"]["agua_fria"]
    assert ap["fonte"] == "NBR 5626:1998 (pesos)" and ap["metodo"] == "pesos"
    assert ap["soma_P"] == 2.0 and ap["Q_Ls"] < r2["redes"]["agua_fria"]["Q_Ls"]
    assert "metodo dos pesos" in rp["dimensionamento"]

    # override por diametro no spec vence o calculo
    r3 = rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                "hidraulica": {"D_pluvial_mm": 150.0, "D_agua_mm": 60.0, "D_esgoto_mm": 100.0}})
    assert r3["redes"]["pluvial"]["fonte"] == "spec" and r3["redes"]["pluvial"]["D_mm"] == 150.0

    mb = membros_bim(r)
    tubos = [m for m in mb if m["tipo"] == "Pipe"]
    # condutores + esgoto + agua + calha (r sem aparelhos_esgoto -> sem coluna de ventilacao)
    assert len(tubos) == r["redes"]["pluvial"]["n_condutores"] + 3
    assert any(m["marca"] == "CALHA" for m in mb)                    # calha no beiral
    # r2 TEM aparelhos_esgoto -> coluna de ventilacao presente
    assert any(m["marca"] == "VENT-C" for m in membros_bim(r2))
    pluv = next(m for m in mb if m["marca"] == "PLUV1")
    assert pluv["p1"][2] == 6000.0 and pluv["p2"][2] == 0.0          # desce do beiral ao solo
    assert pluv["secao"]["forma"] == "ROUND"

    import pytest
    with pytest.raises(ValueError):
        rodar({"geometria": {"L": 0, "W": 20, "H": 6}})
    print(relatorio_pt(r2))
    print("galpao_hidraulica self-test PASSED (dimensiona NBR 5626:2020/8160/10844)")


if __name__ == "__main__":
    _selftest()
