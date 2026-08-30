"""ACEITE do G8: o IFC das tipologias novas ABRE num visualizador.

"Abre no visualizador" nao e' "o arquivo existe" nem "tem N entidades": e' a
geometria ser CONSTRUIVEL. Um IFC com perfil degenerado, matriz singular ou
representacao orfa e' carregado sem erro e mostra uma tela vazia - e nenhuma
contagem de entidades percebe isso.

Duas provas, as mesmas que um visualizador faz ao abrir o arquivo:
  1. `ifcopenshell.geom.iterator` triangula o modelo inteiro. E' o mesmo motor
     que o BlenderBIM e os visualizadores IfcOpenShell usam; toda entidade com
     representacao tem de virar malha.
  2. `ifcopenshell.validate` com as regras EXPRESS do esquema: zero erros.

NOTA DE AMBIENTE: o importador IFC do FreeCAD 1.1.1 desta maquina esta quebrado
(`'Settings' object has no attribute 'USE_BREP_DATA'` - o importIFC ainda chama
uma API que o ifcopenshell 0.8 removeu). Foi conferido que ele falha igual com
um IFC EXPORTADO PELO PROPRIO FreeCAD, entao e' defeito da instalacao e nao dos
arquivos daqui; por isso a prova de renderizacao usa o iterador, e o caminho
FreeCAD e' cruzado pela via do build solido (test_g8_xcheck_freecad).
"""

import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
GALPAO = HERE.parents[3]
sys.path.insert(0, str(GALPAO))

ifcopenshell = pytest.importorskip("ifcopenshell")

import arquitetura_residencial as arq
import bim_casa_residencial as bcr
import bim_edificio as be
import edificio_multipavimento as em

PROJETOS = GALPAO.parents[1] / "projects"


@pytest.fixture(scope="module")
def ifc_edificio(tmp_path_factory):
    payload = json.loads(
        (PROJETOS / "edificio-multipavimento" / "project-spec.json").read_text(
            encoding="utf-8"))["turnkey"]["estrutura"]
    estrutura = em.rodar({chave: payload[chave] for chave in
                          ("geometria", "pavimentos", "laje", "viga", "materiais",
                           "vento") if chave in payload})
    destino = tmp_path_factory.mktemp("g8") / "edificio.ifc"
    be.emitir_bim(estrutura, str(destino))
    return str(destino)


@pytest.fixture(scope="module")
def ifc_casa(tmp_path_factory):
    turnkey = json.loads(
        (PROJETOS / "casa-residencial" / "project-spec.json").read_text(
            encoding="utf-8"))["turnkey"]
    programa = arq.rodar(turnkey["arquitetura"])
    eletrico = turnkey["eletrico"]["circuits"]["layout"]
    validacao = bcr.validar_layout(
        {"units": eletrico["units"], "rooms": copy.deepcopy(eletrico["rooms"])},
        programa)
    assert validacao["ok"], validacao["errors"]
    destino = tmp_path_factory.mktemp("g8") / "casa.ifc"
    bcr.emitir_bim(programa, validacao["layout"], str(destino))
    return str(destino)


def _triangula(path):
    """(entidades com representacao, formas geradas) - o que o viewer desenha."""
    import ifcopenshell.geom as geom

    modelo = ifcopenshell.open(path)
    ajustes = geom.settings()
    ajustes.set("use-world-coords", True)
    iterador = geom.iterator(ajustes, modelo, 1)
    geradas = 0
    if iterador.initialize():
        while True:
            geradas += 1
            if not iterador.next():
                break
    com_representacao = [e for e in modelo.by_type("IfcProduct") if e.Representation]
    return len(com_representacao), geradas


@pytest.mark.parametrize("fixture", ["ifc_edificio", "ifc_casa"])
def test_toda_peca_com_representacao_vira_malha(fixture, request):
    path = request.getfixturevalue(fixture)
    com_representacao, geradas = _triangula(path)
    assert com_representacao > 0
    assert geradas == com_representacao, (
        "%d de %d pecas nao triangularam: no visualizador elas simplesmente "
        "nao aparecem" % (com_representacao - geradas, com_representacao))


@pytest.mark.parametrize("fixture", ["ifc_edificio", "ifc_casa"])
def test_o_arquivo_passa_nas_regras_express_do_esquema(fixture, request):
    from ifcopenshell import validate

    path = request.getfixturevalue(fixture)
    modelo = ifcopenshell.open(path)
    assert modelo.schema == "IFC4"
    registro = validate.json_logger()
    validate.validate(modelo, registro, express_rules=True)
    erros = [item for item in registro.statements if item.get("level") == "error"]
    assert erros == [], erros[:3]
