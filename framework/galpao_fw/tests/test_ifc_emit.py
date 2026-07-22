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


def test_emitir_do_spec_tapered_retorna_none(tmp_path):
    # portico tapered (sem perfil laminado) -> None (segue via FreeCAD)
    spec = {"geometria": _GEO, "estrutura": {"perfil_col_adotado": None,
                                             "perfil_raf_adotado": None}}
    assert EM.emitir_ifc_do_spec(spec, str(tmp_path / "x.ifc")) is None
