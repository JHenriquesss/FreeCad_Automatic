"""Adaptador de edificio multipavimento: a tipologia que faltava no Loop.

O G3 entregou a cadeia de calculo (carga NBR 6120 -> laje -> viga continua ->
pilar -> descida), mas `edificio_multipavimento` era uma ilha: nenhum modulo o
importava e ele nao registrava adaptador. O Loop nao conseguia rodar um
edificio. Estes testes fixam o CONTRATO da tipologia - capacidades declaradas,
estados honestos e o entregavel - nao os calculos, que ja tem os seus arquivos.
"""

import ast
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import edificio_adapter as ea
from builtin_adapters import register_builtin_adapters
from project_loop import (classify_discipline, describe_adapters,
                          normalize_spec, run_project, verify_project_run)


ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = ROOT.parents[1]
SPEC_PERSISTIDO = REPO_ROOT / "projects" / "edificio-multipavimento" / "project-spec.json"


@pytest.fixture(scope="module")
def spec():
    return json.loads(SPEC_PERSISTIDO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module", autouse=True)
def _adaptadores():
    register_builtin_adapters()


@pytest.fixture(scope="module")
def execucao(spec, tmp_path_factory):
    destino = tmp_path_factory.mktemp("edificio") / "run"
    manifesto = run_project(spec, destino, {"generate_2d": True,
                                            "generate_ifc": False})
    return manifesto, destino


# --- contrato do adaptador -------------------------------------------------

def test_a_tipologia_edificio_existe_no_loop():
    capacidades = {item["name"]: item for item in describe_adapters()}
    assert "edificio-multipavimento" in capacidades
    real = capacidades["edificio-multipavimento"]
    assert real["project_types"] == ["edificio"]
    assert set(real["disciplines"]) == {"estrutura"}
    assert "drawings" in real["deliverables"]


def test_os_adaptadores_anteriores_continuam_registrados():
    """A tipologia nova nao pode derrubar as que ja existiam."""
    nomes = {item["name"] for item in describe_adapters()}
    assert {"casa-residencial", "casa-residencial-sintetica"} <= nomes


def test_nao_importa_o_turnkey_do_galpao():
    """Criterio 1 do desenho de generalizacao: nada do galpao no nucleo."""
    arvore = ast.parse(Path(ea.__file__).read_text(encoding="utf-8"))
    importados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module)
    assert "galpao_turnkey" not in importados
    assert "galpao_adapter" not in importados


# --- estados honestos ------------------------------------------------------

def test_estrutura_ausente_bloqueia_sem_inventar(spec):
    """Sem turnkey.estrutura o adaptador REPROVA; nao arbitra um edificio."""
    sem_estrutura = json.loads(json.dumps(spec))
    del sem_estrutura["turnkey"]["estrutura"]
    normalizado = normalize_spec(sem_estrutura)
    normalizado["requested_disciplines"] = ["estrutura"]

    resultado, registros = ea.run_edificio(normalizado, None)

    assert registros["estrutura"]["status"] == "blocked"
    assert any(e["code"] == "missing_structure_input"
               for e in registros["estrutura"]["errors"])
    assert resultado["estrutura"] is None


def test_nenhuma_disciplina_e_marcada_passed(execucao):
    """Aprovacao para obra exige responsavel tecnico e ART - nao um gate."""
    manifesto, _ = execucao
    registro = manifesto["disciplines"]["estrutura"]
    assert classify_discipline(registro) == "needs_review"
    assert manifesto["status"] == "needs_review"


def test_o_escopo_declara_o_que_ainda_nao_e_calculado(execucao):
    """Os itens abertos do REVISAO-G3 aparecem como estado, nao como silencio."""
    manifesto, _ = execucao
    escopo = manifesto["disciplines"]["estrutura"]["scope"]
    for chave in ("vento", "desaprumo", "estabilidade_global",
                  "alvenaria_estrutural", "fundacao", "vibracao_piso"):
        assert escopo[chave] == "not_available", chave


def test_os_gates_do_g3_chegam_ao_manifesto(execucao):
    manifesto, _ = execucao
    gates = manifesto["disciplines"]["estrutura"]["gates"]
    for chave in ("fechamento_carga", "reducao_6120", "pilares", "laje", "vigas"):
        assert chave in gates, chave
    assert gates["fechamento_carga"]["OK"] is True


def test_a_verificacao_do_run_fecha(execucao):
    manifesto, destino = execucao
    assert verify_project_run(destino)["ok"] is True
    assert manifesto["atende"] is False        # needs_review nunca e' atende


# --- rotulo x geometria ----------------------------------------------------

def test_envelope_declarado_confere_com_a_soma_dos_vaos(spec):
    """A geometria comum do Loop e os vaos da estrutura sao duas declaracoes
    do mesmo predio. Divergir e' erro de entrada, nao detalhe."""
    incoerente = json.loads(json.dumps(spec))
    incoerente["turnkey"]["geometria"]["comprimento"] += 3.0
    normalizado = normalize_spec(incoerente)
    normalizado["requested_disciplines"] = ["estrutura"]

    _, registros = ea.run_edificio(normalizado, None)

    assert registros["estrutura"]["status"] == "blocked"
    assert any(e["code"] == "geometry_mismatch"
               for e in registros["estrutura"]["errors"])


# --- entregavel ------------------------------------------------------------

def test_a_planta_de_formas_sai_e_e_xml_valido(execucao):
    """Licao do S41: substring nao prova que o SVG abre. Parseia."""
    manifesto, destino = execucao
    entregavel = manifesto["deliverables"]["drawings"]
    assert entregavel["status"] == "generated"
    assert entregavel["artifacts"], "nenhuma prancha emitida"
    for relativo in entregavel["artifacts"]:
        caminho = Path(destino) / relativo
        assert caminho.is_file(), relativo
        ET.parse(caminho)


def test_a_planta_desenha_todos_os_pilares_calculados(execucao):
    """Desenho x dado: a grade pode desenhar um numero que nao e' o calculado.
    Foi assim que a planta de incendio desenhava cols*rows != N."""
    manifesto, destino = execucao
    caminho = Path(destino) / manifesto["deliverables"]["drawings"]["artifacts"][0]
    raiz = ET.parse(caminho).getroot()
    rotulos = {no.text.strip() for no in raiz.iter()
               if no.tag.endswith("text") and no.text
               and re.fullmatch(r"P\d+", no.text.strip())}
    calculados = manifesto["disciplines"]["estrutura"]["gates"]["pilares"]["n"]
    assert len(rotulos) == calculados, sorted(rotulos)


def test_o_titulo_da_planta_confere_com_o_envelope_declarado(execucao, spec):
    """O rotulo da prancha e' um dado a mais para divergir do modelo."""
    _, destino = execucao
    caminho = (Path(destino) / "drawings" / "planta-formas-pavimento-tipo.svg")
    textos = " ".join(no.text for no in ET.parse(caminho).getroot().iter()
                      if no.tag.endswith("text") and no.text)
    comum = spec["turnkey"]["geometria"]
    area = comum["comprimento"] * comum["vao"]
    assert ("%.1f m2" % area) in textos, textos[:200]


def test_sem_2d_o_entregavel_e_not_requested(spec, tmp_path):
    manifesto = run_project(spec, tmp_path / "sem-2d",
                            {"generate_2d": False, "generate_caderno": False,
                             "generate_ifc": False})
    assert manifesto["deliverables"]["drawings"]["status"] == "not_requested"
