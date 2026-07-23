"""BIM (IFC4) do galpao de concreto - galpao_concreto.membros_bim / emitir_bim.

FreeCAD-free (via ifc_emit.emitir_ifc). Pilares (IfcColumn), vigas de cobertura
(IfcBeam) e sapatas (IfcFooting) com secao retangular e IfcMaterial 'Concreto Cxx'.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import galpao_concreto as gc
import ifc_emit


def _r(vao=10.0, n=7):
    return gc.rodar({"vao": vao, "comprimento": 40.0, "pe_direito": 6.0,
                     "n_porticos": n, "v0": 40.0, "cat": "IV", "classe": "B",
                     "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "sigma_solo_adm": 250.0})


def test_lista_de_membros_conta_certo():
    r = _r(n=7)
    ms = gc.membros_bim(r)
    cols = [m for m in ms if m["tipo"] == "Column"]
    beams = [m for m in ms if m["tipo"] == "Beam"]
    foots = [m for m in ms if m["tipo"] == "Footing"]
    assert len(cols) == 7 * 2                       # 7 porticos x 2 lados
    assert len(beams) == 7                          # 1 viga de cobertura por portico
    assert len(foots) == 7 * 2                      # 1 sapata por pilar


def test_pilar_vai_do_chao_ao_topo():
    r = _r()
    col = next(m for m in gc.membros_bim(r) if m["tipo"] == "Column")
    assert col["p1"][2] == 0.0                       # base no z=0
    assert abs(col["p2"][2] - r["spec"]["H"] * 1000.0) < 1e-6   # topo em H (mm)
    assert col["secao"]["forma"] == "RECT"


def test_membros_carregam_material_concreto():
    r = _r()
    for m in gc.membros_bim(r):
        assert m["material"] == "Concreto C30"


@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_emite_ifc_com_entidades_e_material(tmp_path):
    import ifcopenshell
    r = _r(n=7)
    p = str(tmp_path / "galpao_concreto.ifc")
    gc.emitir_bim(r, p)
    m = ifcopenshell.open(p)
    assert len(m.by_type("IfcColumn")) == 14
    assert len(m.by_type("IfcBeam")) == 7
    assert len(m.by_type("IfcFooting")) == 14
    # material de concreto associado a todos os 35 elementos
    assert [x.Name for x in m.by_type("IfcMaterial")] == ["Concreto C30"]
    assert len(m.by_type("IfcRelAssociatesMaterial")) == 35


@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_xcheck_contagem_pura_bate_com_ifc(tmp_path):
    # a contagem do modelo puro (membros_bim) deve bater com o IFC emitido
    import ifcopenshell
    r = _r(n=5)
    ms = gc.membros_bim(r)
    p = str(tmp_path / "g.ifc")
    gc.emitir_bim(r, p)
    m = ifcopenshell.open(p)
    assert len([x for x in ms if x["tipo"] == "Column"]) == len(m.by_type("IfcColumn"))
    assert len([x for x in ms if x["tipo"] == "Beam"]) == len(m.by_type("IfcBeam"))
    assert len([x for x in ms if x["tipo"] == "Footing"]) == len(m.by_type("IfcFooting"))
