"""Emissor IFC4 puro-Python (ifcopenshell), SEM FreeCAD - item 2 do roteiro.

Se o ifcopenshell nao estiver instalado, o modulo inteiro e pulado (o export via
FreeCAD, build_galpao._export_ifc, cobre o caso sem a lib).
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytest.importorskip("ifcopenshell")   # pula tudo se a lib nao estiver instalada

import ifcopenshell
import modelo_neutro as MN
import ifc_emit as EM

_SEC = {"col": {"nome": "HEA200", "d": 0.190, "bf": 0.200, "tw": 0.0065, "tf": 0.010},
        "raf": {"nome": "HEA180", "d": 0.171, "bf": 0.180, "tw": 0.006, "tf": 0.0095}}
_GEO = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}


@pytest.fixture(scope="module")
def ifc_model(tmp_path_factory):
    membros = MN.frame_primario(_GEO, _SEC)            # 18 col + 18 beam
    f = str(tmp_path_factory.mktemp("ifc") / "g.ifc")
    EM.emitir_ifc(membros, f, nome="Amostra")
    return ifcopenshell.open(f)


def test_disponivel():
    assert EM.disponivel() is True


def test_schema_ifc4(ifc_model):
    assert ifc_model.schema == "IFC4"


def test_contagem_tipada(ifc_model):
    assert len(ifc_model.by_type("IfcColumn")) == 18
    assert len(ifc_model.by_type("IfcBeam")) == 18


def test_predefined_types(ifc_model):
    assert ifc_model.by_type("IfcColumn")[0].PredefinedType == "COLUMN"
    assert ifc_model.by_type("IfcBeam")[0].PredefinedType == "BEAM"


def test_marcas_preservadas(ifc_model):
    assert {e.Name for e in ifc_model.by_type("IfcColumn")} == {"C1"}
    assert {e.Name for e in ifc_model.by_type("IfcBeam")} == {"V1"}


def test_perfil_I_reusado(ifc_model):
    profs = ifc_model.by_type("IfcIShapeProfileDef")
    assert len(profs) == 2                             # col + raf, cacheados
    nomes = {p.ProfileName for p in profs}
    assert nomes == {"HEA200", "HEA180"}
    # dims em mm (catalogo em m * 1000)
    hea200 = [p for p in profs if p.ProfileName == "HEA200"][0]
    assert abs(hea200.OverallWidth - 200.0) < 1e-6
    assert abs(hea200.OverallDepth - 190.0) < 1e-6


def test_hierarquia_espacial(ifc_model):
    assert len(ifc_model.by_type("IfcProject")) == 1
    assert len(ifc_model.by_type("IfcBuildingStorey")) == 1
    # todo elemento contido em um storey
    assert len(ifc_model.by_type("IfcRelContainedInSpatialStructure")) >= 1


def test_emitir_do_spec_frame_laminado(tmp_path):
    spec = {"slug": "amostra", "geometria": _GEO,
            "estrutura": {"perfil_col_adotado": "HEA200",
                          "perfil_raf_adotado": "HEA180"}}
    f = str(tmp_path / "spec.ifc")
    out = EM.emitir_ifc_do_spec(spec, f)
    assert out == f and os.path.exists(f)
    m = ifcopenshell.open(f)
    assert len(m.by_type("IfcColumn")) == 18 and len(m.by_type("IfcBeam")) == 18


def test_emitir_do_spec_com_tercas(tmp_path):
    # terca_dims [h,bf,lip,t] mm + n_terca -> IfcMember (perfil C) alem do primario
    spec = {"slug": "amostra", "geometria": _GEO,
            "estrutura": {"perfil_col_adotado": "HEA200",
                          "perfil_raf_adotado": "HEA180",
                          "n_terca": 5, "terca_perfil": "Ue300",
                          "terca_dims": [300.0, 85.0, 25.0, 3.35],
                          "longarina_perfil": "UPE140",
                          "longarina_dims": [140.0, 65.0, 5.0, 9.0]}}
    f = str(tmp_path / "spec_t.ifc")
    EM.emitir_ifc_do_spec(spec, f)
    m = ifcopenshell.open(f)
    assert len(m.by_type("IfcColumn")) == 18 and len(m.by_type("IfcBeam")) == 18
    # 10 tercas (8 interm + 2 beiral) + 4 girts (2 niveis x 2 paredes) = 14
    assert len(m.by_type("IfcMember")) == (2 * (5 - 1) + 2) + 4
    # perfil formado a frio -> IfcCShapeProfileDef ; girt U -> IfcUShapeProfileDef
    cs = m.by_type("IfcCShapeProfileDef")
    assert len(cs) == 1 and abs(cs[0].Depth - 300.0) < 1e-6 and abs(cs[0].Girth - 25.0) < 1e-6
    us = m.by_type("IfcUShapeProfileDef")
    assert len(us) == 1 and abs(us[0].Depth - 140.0) < 1e-6


def test_emitir_do_spec_tapered_retorna_none(tmp_path):
    # portico tapered (sem perfil laminado) -> None (segue via FreeCAD)
    spec = {"geometria": _GEO, "estrutura": {"perfil_col_adotado": None,
                                             "perfil_raf_adotado": None}}
    assert EM.emitir_ifc_do_spec(spec, str(tmp_path / "x.ifc")) is None
