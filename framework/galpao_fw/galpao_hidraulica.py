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
        plc = hp.diametro_pluvial(area_tel, i_pl, decl_pl)
        d_pl = float(plc["DN_mm"])
        pluv = {"D_mm": d_pl, "fonte": "NBR 10844", "Q_Lmin": plc["Q_Lmin"],
                "i_mm_h": plc["i_mm_h"], "i_default": plc["i_default"],
                "area_m2": round(area_tel, 1)}
    pluv["n_condutores"] = n_cond
    pluv["default"] = False        # pluvial e' sempre dimensionado (geometria) ou do spec

    # --- AGUA FRIA: dimensionada se aparelhos informados (NBR 5626:2020) ---
    apar_ag = hid.get("aparelhos_agua")
    if hid.get("D_agua_mm") is not None:
        agua = {"D_mm": float(hid["D_agua_mm"]), "fonte": "spec", "default": False}
    elif apar_ag:
        agc = hp.diametro_agua(apar_ag)
        agua = {"D_mm": float(agc["DN_mm"]), "fonte": "NBR 5626:2020", "default": False,
                "Q_Ls": agc["Q_Ls"], "v_real_ms": agc["v_real_ms"]}
    else:
        agua = {"D_mm": D_AGUA_DEFAULT_MM, "fonte": "default", "default": True}

    # --- ESGOTO: dimensionado se aparelhos informados (NBR 8160) ---
    apar_es = hid.get("aparelhos_esgoto")
    if hid.get("D_esgoto_mm") is not None:
        esgoto = {"D_mm": float(hid["D_esgoto_mm"]), "fonte": "spec", "default": False}
    elif apar_es:
        decl_es = float(hid.get("decl_esgoto_pct", 1.0))
        uhc, dn_desc = hp.uhc_de_aparelhos(apar_es)
        d_es = float(hp.diametro_coletor(uhc, decl_es))
        esgoto = {"D_mm": d_es, "fonte": "NBR 8160", "default": False,
                  "uhc": uhc, "dn_ramal_min_mm": dn_desc}
    else:
        esgoto = {"D_mm": D_ESGOTO_DEFAULT_MM, "fonte": "default", "default": True}

    redes = {"pluvial": pluv, "esgoto": esgoto, "agua_fria": agua}

    # mensagem de dimensionamento: o que foi calculado e o que ficou [A CONFIRMAR]
    partes = []
    if pluv["fonte"] == "NBR 10844":
        cav = " [A CONFIRMAR i local]" if pluv.get("i_default") else ""
        partes.append("pluvial DN%.0f calculado NBR 10844 (Q=%.0f L/min; i=%.0f mm/h%s)"
                      % (pluv["D_mm"], pluv["Q_Lmin"], pluv["i_mm_h"], cav))
    else:
        partes.append("pluvial DN%.0f (spec)" % pluv["D_mm"])
    if agua["fonte"] == "NBR 5626:2020":
        partes.append("agua fria DN%.0f calculado NBR 5626:2020 (Q=%.2f L/s; v=%.1f m/s)"
                      % (agua["D_mm"], agua["Q_Ls"], agua["v_real_ms"]))
    elif agua["fonte"] == "spec":
        partes.append("agua fria DN%.0f (spec)" % agua["D_mm"])
    else:
        partes.append("agua fria DN%.0f default comercial [A CONFIRMAR - informe "
                      "aparelhos_agua]" % agua["D_mm"])
    if esgoto["fonte"] == "NBR 8160":
        partes.append("esgoto DN%.0f calculado NBR 8160 (UHC=%.1f)"
                      % (esgoto["D_mm"], esgoto["uhc"]))
    elif esgoto["fonte"] == "spec":
        partes.append("esgoto DN%.0f (spec)" % esgoto["D_mm"])
    else:
        partes.append("esgoto DN%.0f default comercial [A CONFIRMAR - informe "
                      "aparelhos_esgoto]" % esgoto["D_mm"])
    dimensionamento = "; ".join(partes)
    completo = not (agua["default"] or esgoto["default"])

    gates = {"rede": {"n_condutores_pluvial": n_cond, "D_pluvial_mm": pluv["D_mm"],
                      "D_esgoto_mm": esgoto["D_mm"], "D_agua_mm": agua["D_mm"],
                      "dimensionamento": dimensionamento,
                      "dimensionamento_completo": completo, "OK": n_cond >= 1}}
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
    # telhado 40x20 = 800 m2, i=150 -> Q = 150*800/60 = 2000 L/min -> Tab.4 1%: DN250 (1820<2000<=3310)
    assert r["redes"]["pluvial"]["D_mm"] == 250.0, r["redes"]["pluvial"]

    # com aparelhos: agua+esgoto CALCULADOS pela norma -> dimensionamento completo
    r2 = rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2, "chuveiro": 2},
                               "aparelhos_esgoto": {"bacia": 2, "lavatorio": 2, "chuveiro": 2}}})
    assert r2["redes"]["agua_fria"]["fonte"] == "NBR 5626:2020"
    assert r2["redes"]["esgoto"]["fonte"] == "NBR 8160"
    assert r2["dimensionamento_completo"] is True
    assert "A CONFIRMAR - informe" not in r2["dimensionamento"]

    # override por diametro no spec vence o calculo
    r3 = rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                "hidraulica": {"D_pluvial_mm": 150.0, "D_agua_mm": 60.0, "D_esgoto_mm": 100.0}})
    assert r3["redes"]["pluvial"]["fonte"] == "spec" and r3["redes"]["pluvial"]["D_mm"] == 150.0

    mb = membros_bim(r)
    tubos = [m for m in mb if m["tipo"] == "Pipe"]
    assert len(tubos) == r["redes"]["pluvial"]["n_condutores"] + 2   # condutores + esgoto + agua
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
