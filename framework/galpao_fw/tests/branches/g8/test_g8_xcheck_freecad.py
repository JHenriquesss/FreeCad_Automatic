"""CROSS-CHECK (build): o 3D do FreeCAD x o IFC puro-Python das tipologias novas.

O galpao de aco ja trava as suas duas descricoes uma contra a outra
(`test_ifc_secundarios_xcheck`). As tipologias do G8 ganham a mesma guarda: o
emissor IFC PURO e o build SOLIDO no FreeCAD montam o mesmo predio por caminhos
independentes, entao numero de pecas, volume de concreto e contagem tipada tem
de bater - e o 3D nao pode acusar interpenetracao sobre os solidos REAIS (OCCT
common(), que e' o que as caixas envolventes do teste puro nao respondem).

Marcado `build` (exige freecadcmd) -> roda na guarda local, nao no CI de nuvem.
"""

import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
GALPAO = HERE.parents[3]
sys.path.insert(0, str(GALPAO))

import bim_edificio as be
import edificio_multipavimento as em

FREECADCMD = os.environ.get(
    "FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")
SPEC = GALPAO.parents[1] / "projects" / "edificio-multipavimento" / "project-spec.json"

pytestmark = [
    pytest.mark.build,
    pytest.mark.skipif(not os.path.exists(FREECADCMD), reason="freecadcmd ausente"),
]


@pytest.fixture(scope="module")
def estrutura():
    payload = json.loads(SPEC.read_text(encoding="utf-8"))["turnkey"]["estrutura"]
    return em.rodar({chave: payload[chave] for chave in
                     ("geometria", "pavimentos", "laje", "viga", "materiais",
                      "vento") if chave in payload})


@pytest.fixture(scope="module")
def montagem(estrutura, tmp_path_factory):
    destino = tmp_path_factory.mktemp("edificio3d")
    saida = be.montar_3d(estrutura, str(destino), doc_name="edificio_g8",
                         headless=True, timeout=900)
    assert isinstance(saida, dict) and not saida.get("erro"), saida
    return saida["result"], destino


def test_o_build_gera_os_tres_arquivos(montagem):
    modelo, _ = montagem
    for chave in ("fcstd", "step", "ifc"):
        assert modelo.get(chave), chave
        assert Path(modelo[chave]).is_file(), chave


def test_o_numero_de_solidos_bate_com_o_modelo_puro(estrutura, montagem):
    modelo, _ = montagem
    assert modelo["elementos"] == len(be.membros_bim(estrutura))


def test_o_volume_de_concreto_bate_com_o_modelo_puro(estrutura, montagem):
    modelo, _ = montagem
    puro = be.quantitativo(be.membros_bim(estrutura))["vol_concreto_m3"]
    assert abs(modelo["vol_concreto_m3"] - puro) <= 0.005


def test_os_solidos_reais_nao_se_interpenetram(montagem):
    """A caixa envolvente do teste puro nao responde isto; o OCCT responde."""
    modelo, _ = montagem
    assert modelo["interferencias"] == 0, modelo["interferencias_lista"][:5]


def test_o_ifc_do_freecad_tem_a_mesma_contagem_tipada_do_ifc_puro(
        estrutura, montagem, tmp_path):
    ifcopenshell = pytest.importorskip("ifcopenshell")
    modelo, _ = montagem
    do_freecad = ifcopenshell.open(modelo["ifc"])
    destino = tmp_path / "puro.ifc"
    be.emitir_bim(estrutura, str(destino))
    do_puro = ifcopenshell.open(str(destino))
    for classe in ("IfcColumn", "IfcBeam", "IfcSlab"):
        assert len(do_freecad.by_type(classe)) == len(do_puro.by_type(classe)), classe
