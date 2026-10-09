"""Integracao: rodar_tudo produz o BIM IFC (fisico + analitico) direto do calculo,
SEM FreeCAD. Torna o entregavel BIM FreeCAD-free um passo de 1a classe do pipeline.
Pula se o ifcopenshell nao estiver instalado.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

pytest.importorskip("ifcopenshell")

import ifcopenshell
import rodar_projeto as RP


def _spec_amostra():
    with open(os.path.join(GALPAO, "spec_amostra_engenheiro.json"), encoding="utf-8") as f:
        return json.load(f)


def test_rodar_tudo_emite_ifc_sem_freecad(tmp_path):
    spec = _spec_amostra()
    RP.rodar_tudo(spec, out_dir=str(tmp_path), com_3d=False, com_executivo=False,
                  gerar_pdf=False, gerar_dossie=False, verbose=False)
    bim = spec["estrutura"].get("ifc_bim")
    assert bim and bim["fisico"] and bim["analitico"]
    assert os.path.exists(bim["fisico"]) and os.path.exists(bim["analitico"])

    # fisico: colunas + vigas (Revit fisico)
    mf = ifcopenshell.open(bim["fisico"])
    assert mf.schema == "IFC4"
    assert len(mf.by_type("IfcColumn")) >= 1 and len(mf.by_type("IfcBeam")) >= 1

    # analitico: SAM + barras + apoios (Revit analitico)
    ma = ifcopenshell.open(bim["analitico"])
    assert len(ma.by_type("IfcStructuralAnalysisModel")) == 1
    assert len(ma.by_type("IfcStructuralCurveMember")) >= 1
    assert len(ma.by_type("IfcStructuralPointConnection")) >= 1


def test_ifc_no_diretorio_ifc(tmp_path):
    spec = _spec_amostra()
    RP.rodar_tudo(spec, out_dir=str(tmp_path), com_3d=False, com_executivo=False,
                  gerar_pdf=False, gerar_dossie=False, verbose=False)
    idir = tmp_path / "ifc"
    assert idir.is_dir()
    ifcs = list(idir.glob("*.ifc"))
    assert len(ifcs) == 2                               # fisico + analitico


def test_rodar_tudo_so_gera_as_pranchas_quando_pedido(tmp_path, monkeypatch):
    import inspect
    import pranchas_ifc as PI
    assert inspect.signature(RP.rodar_tudo).parameters["com_pranchas_ifc"].default is False
    spec = _spec_amostra()
    visto = {}

    def falso(ifc, pasta, titulo, revisao, carimbo=None, **kw):
        visto.update(ifc=ifc, pasta=pasta, titulo=titulo, revisao=revisao, carimbo=carimbo)
        return {"gerado": False, "avisos": [], "nao_gerado": {"desenhos": "teste"}}

    monkeypatch.setattr(PI, "gerar", falso)
    r = RP.rodar_tudo(spec, out_dir=str(tmp_path), com_3d=False, com_executivo=False,
                      gerar_pdf=False, gerar_dossie=False, verbose=False,
                      com_pranchas_ifc=True, carimbo_pranchas={"CLIENTE": "Fulano"},
                      revisao_pranchas="03")
    assert visto["ifc"] == spec["estrutura"]["ifc_bim"]["fisico"]
    assert visto["pasta"] == os.path.join(str(tmp_path), "pranchas-ifc")
    assert (visto["titulo"], visto["revisao"]) == ("GALPAO 28.5x20 m", "03")
    assert visto["carimbo"] == {"CLIENTE": "Fulano"}
    assert r["pranchas_ifc"]["nao_gerado"] == {"desenhos": "teste"}
    assert spec["estrutura"]["pranchas_ifc"] is r["pranchas_ifc"]
