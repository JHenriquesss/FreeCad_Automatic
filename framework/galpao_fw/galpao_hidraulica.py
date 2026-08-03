# ============================================================================
# galpao_hidraulica.py - O QUE ESTE SCRIPT FAZ / (NAO) CALCULA
# Vertical de HIDRAULICA PREDIAL do galpao para COORDENACAO - roteia a rede
# (aguas pluviais, esgoto e agua fria) no MODELO FEDERADO e no CLASH do turnkey.
#
# >>> ESCOPO HONESTO (leia): este vertical NAO faz o DIMENSIONAMENTO HIDRAULICO. As
#     normas de hidraulica predial (NBR 5626 agua fria, NBR 8160 esgoto, NBR 10844
#     aguas pluviais) NAO estao no repo (pesquisa/) NEM acessiveis (NotebookLM
#     offline). Pela regra da casa (nunca inventar valor de norma de memoria - licao
#     AR300), os DIAMETROS aqui vem do SPEC (o engenheiro informa) ou de defaults
#     COMERCIAIS explicitamente [A CONFIRMAR]. O calculo (unidades Hunter/UHC,
#     intensidade pluviometrica, vazoes -> diametro) fica como TODO gated na norma.
#
# O QUE ESTE VERTICAL FAZ: roteia a rede como membros (tubos) para o federado ->
# o clash acha interferencia tubo x estrutura/duto/eletrocalha (coordenacao real).
#   - pluvial: condutores verticais (descidas) no perimetro (do beiral ao solo);
#   - esgoto: coletor horizontal sob o piso ao longo do comprimento;
#   - agua fria: barrilete no forro ao longo do comprimento.
# Frame comum do turnkey (X=comprimento, Y=largura, Z=altura; mm; secao de barra m).
# ============================================================================
"""Vertical de hidraulica predial (COORDENACAO): roteia pluvial/esgoto/agua fria no
modelo federado + clash. NAO dimensiona (NBR 5626/8160/10844 pendentes) - diametros do
spec ou defaults [A CONFIRMAR]."""

from __future__ import annotations

# diametros COMERCIAIS de default (mm) - [A CONFIRMAR] o dimensionamento pela norma
# (NBR 5626/8160/10844); sobrescriviveis pelo spec['hidraulica'].
D_PLUVIAL_MM = 100.0             # [A CONFIRMAR] condutor de aguas pluviais (NBR 10844)
D_ESGOTO_MM = 100.0             # [A CONFIRMAR] coletor de esgoto (NBR 8160)
D_AGUA_FRIA_MM = 50.0           # [A CONFIRMAR] barrilete de agua fria (NBR 5626)
N_CONDUTORES_PADRAO = 4          # condutores pluviais (1 por canto), sobrescrivivel


def _d(sub, chave, default):
    """Diametro (mm) do spec ou default flagado. Marca se veio de default."""
    v = (sub or {}).get(chave)
    return (float(v), False) if v is not None else (float(default), True)


def rodar(spec):
    """Roteia a rede hidraulica de coordenacao do galpao. NAO dimensiona.
    spec: {geometria{L,W,H} (m), hidraulica{n_condutores, D_pluvial_mm, D_esgoto_mm,
           D_agua_mm}(opc)}. Retorna {geometria, redes, gates, reprovados, ATENDE,
           dimensionamento}. O gate e' INFORMATIVO (rede roteada); o dimensionamento
           fica 'A CONFIRMAR' (norma indisponivel)."""
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
    d_pl, pl_def = _d(hid, "D_pluvial_mm", D_PLUVIAL_MM)
    d_es, es_def = _d(hid, "D_esgoto_mm", D_ESGOTO_MM)
    d_ag, ag_def = _d(hid, "D_agua_mm", D_AGUA_FRIA_MM)

    flags = [n for n, dv in (("pluvial", pl_def), ("esgoto", es_def),
                             ("agua_fria", ag_def)) if dv]
    dimensionamento = ("A CONFIRMAR - NBR 5626/8160/10844 nao implementadas (normas "
                       "indisponiveis); diametros %s usam default comercial" % flags
                       if flags else "diametros informados no spec")

    redes = {"pluvial": {"n_condutores": n_cond, "D_mm": d_pl, "default": pl_def},
             "esgoto": {"D_mm": d_es, "default": es_def},
             "agua_fria": {"D_mm": d_ag, "default": ag_def}}
    gates = {"rede": {"n_condutores_pluvial": n_cond, "D_pluvial_mm": d_pl,
                      "D_esgoto_mm": d_es, "D_agua_mm": d_ag,
                      "dimensionamento": dimensionamento, "OK": n_cond >= 1}}
    r = {"geometria": {"L": L, "W": W, "H": H}, "redes": redes,
         "dimensionamento": dimensionamento, "gates": gates}
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
    n = max(0, int(redes["pluvial"]["n_condutores"]))
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
    L = ["HIDRAULICA PREDIAL - GALPAO (COORDENACAO; SEM DIMENSIONAMENTO)",
         "  Pluvial: %d condutores D%.0f mm" % (g["n_condutores_pluvial"],
                                                g["D_pluvial_mm"]),
         "  Esgoto: coletor D%.0f mm ; Agua fria: barrilete D%.0f mm" % (
             g["D_esgoto_mm"], g["D_agua_mm"]),
         "  DIMENSIONAMENTO: %s" % g["dimensionamento"],
         "  RESULTADO: %s (rede roteada p/ coordenacao)" % (
             "ATENDE" if r["ATENDE"] else "REPROVA")]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    r = rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}})
    assert r["ATENDE"] is True
    # diametros default -> flag de dimensionamento pendente (nunca inventa norma)
    assert "A CONFIRMAR" in r["dimensionamento"]
    assert r["redes"]["pluvial"]["default"] is True
    # spec com diametros informados -> sem flag de default
    r2 = rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                "hidraulica": {"D_pluvial_mm": 150.0, "D_esgoto_mm": 100.0,
                               "D_agua_mm": 60.0, "n_condutores": 6}})
    assert r2["redes"]["pluvial"]["default"] is False and r2["redes"]["pluvial"]["D_mm"] == 150.0
    assert "informados no spec" in r2["dimensionamento"]
    mb = membros_bim(r)
    tubos = [m for m in mb if m["tipo"] == "Pipe"]
    assert len(tubos) == r["redes"]["pluvial"]["n_condutores"] + 2   # condutores + esgoto + agua
    pluv = next(m for m in mb if m["marca"] == "PLUV1")
    assert pluv["p1"][2] == 6000.0 and pluv["p2"][2] == 0.0          # desce do beiral ao solo
    assert pluv["secao"]["forma"] == "ROUND"
    import pytest
    with pytest.raises(ValueError):
        rodar({"geometria": {"L": 0, "W": 20, "H": 6}})
    print(relatorio_pt(r))
    print("galpao_hidraulica self-test PASSED (coordenacao; dimensionamento A CONFIRMAR)")


if __name__ == "__main__":
    _selftest()
