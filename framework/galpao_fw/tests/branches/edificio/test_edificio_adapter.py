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
    # G12: incendio, hidraulica e eletrico deixaram de ser ausentes. Cada uma
    # entra por uma fronteira propria e so quando o spec a declara.
    assert set(real["disciplines"]) == {"estrutura", "incendio", "hidraulica",
                                        "eletrico"}
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
    """O que segue fora do adaptador aparece como estado, nao como silencio.

    `fundacao` saiu desta lista no G9 - ela e' calculada quando a sondagem esta
    declarada, e o projeto persistido a declara. O que ficou aberto DENTRO da
    fundacao continua publicado (momento na base do pilar, baldrame, recalque).

    `vibracao_piso` saiu no G11 (NBR 8800 11.4/Anexo L), junto com o desempenho
    da NBR 15575. O que a 15575 verifica por ENSAIO e nao por conta entrou no
    lugar - e tem de continuar publicado, senao um 'desempenho: implemented'
    passaria a cobrir requisitos que ninguem verificou.
    """
    manifesto, _ = execucao
    escopo = manifesto["disciplines"]["estrutura"]["scope"]
    for chave in ("alvenaria_estrutural", "momento_base_pilar",
                  "viga_baldrame", "recalque_diferencial",
                  "desempenho_15575_impacto_corpo_mole_duro",
                  "desempenho_15575_carga_concentrada_piso",
                  "desempenho_15575_fachada"):
        assert escopo[chave] == "not_available", chave
    assert escopo["fundacao"] == "implemented"
    assert escopo["vibracao_piso"] == "implemented"
    assert escopo["desempenho_15575"] == "implemented"


def test_com_vento_declarado_a_acao_horizontal_sai_calculada(execucao):
    """Fecha os itens 1 e 2 da secao 10 do REVISAO-G3."""
    manifesto, _ = execucao
    escopo = manifesto["disciplines"]["estrutura"]["scope"]
    for chave in ("vento", "desaprumo", "estabilidade_global",
                  "deslocamento_lateral_els"):
        assert escopo[chave] == "implemented", chave


def test_sem_vento_a_acao_horizontal_volta_a_not_available(spec):
    """Sem Ca (abaco da Fig.4) nao se arbitra acao: o escopo tem de recuar, e o
    resultado tem de DIZER que a descida ficou apenas gravitacional."""
    sem_vento = json.loads(json.dumps(spec))
    del sem_vento["turnkey"]["estrutura"]["vento"]
    normalizado = normalize_spec(sem_vento)
    normalizado["requested_disciplines"] = ["estrutura"]

    _, registros = ea.run_edificio(normalizado, None)

    escopo = registros["estrutura"]["scope"]
    for chave in ("vento", "desaprumo", "estabilidade_global"):
        assert escopo[chave] == "not_available", chave
    assert any(a["code"] == "acao_horizontal_nao_avaliada"
               for a in registros["estrutura"]["warnings"])


def test_o_gate_de_estabilidade_horizontal_chega_ao_manifesto(execucao):
    manifesto, _ = execucao
    gate = manifesto["disciplines"]["estrutura"]["gates"]["estabilidade_horizontal"]
    assert gate["nos"] in ("fixos", "moveis")
    assert 1.0 < gate["gamma_z"] <= 1.3
    assert gate["els_OK"] is True
    assert gate["direcao_critica"] in ("x", "y")


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


def test_a_planta_de_laje_sai_junto_com_a_de_formas(execucao):
    """A laje era dimensionada e so existia como numero: sem prancha, o
    resultado nao chegava a obra. Alcancabilidade, nao calculo."""
    manifesto, destino = execucao
    entregavel = manifesto["deliverables"]["drawings"]
    assert "drawings/planta-laje-pavimento-tipo.svg" in entregavel["artifacts"]
    assert entregavel["skipped"] == []
    caminho = Path(destino) / "drawings" / "planta-laje-pavimento-tipo.svg"
    raiz = ET.parse(caminho).getroot()
    textos = " ".join(no.text for no in raiz.iter()
                      if no.tag.endswith("text") and no.text)
    # a prancha tem de trazer o veredito da laje, nao so a geometria
    assert "ATENDE" in textos


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


# --- G11: vibracao de piso e desempenho NBR 15575 --------------------------

def test_o_manifesto_publica_a_ressalva_de_L31_da_via_simplificada(execucao):
    """L.3.1 e' explicito: a avaliacao simplificada "pode nao constituir uma
    solucao adequada para o problema". Atender 20/9/5 mm nao e' certificado de
    conforto, e o manifesto nao pode deixar parecer que e'."""
    manifesto, _ = execucao
    avisos = manifesto["disciplines"]["estrutura"]["warnings"]
    aviso = next((a for a in avisos
                  if a["code"] == "vibracao_avaliacao_simplificada"), None)
    assert aviso is not None
    assert "L.3.1" in aviso["detail"]
    assert "biapoiadas" in aviso["detail"]
    assert aviso["d_total_mm"] is not None and aviso["d_lim_mm"] is not None


def test_o_manifesto_publica_o_que_a_15575_exige_e_ninguem_verificou(execucao):
    """A 15575 exige mais do que este framework calcula. O que ficou de fora tem
    de aparecer nomeado - confundir 'nao verificado' com 'aprovado' e' o bug que
    este framework persegue desde a saturacao silenciosa."""
    manifesto, _ = execucao
    avisos = manifesto["disciplines"]["estrutura"]["warnings"]
    aviso = next((a for a in avisos
                  if a["code"] == "desempenho_15575_incompleto"), None)
    if aviso is None:                     # spec nao habitacional: nada a exigir
        gates = manifesto["disciplines"]["estrutura"]["gates"]
        assert gates["desempenho_15575"]["aplicavel"] is False
    else:
        assert aviso["nao_verificados"]
        assert "HABITACIONAL" in aviso["detail"]


def test_os_gates_do_g11_viajam_no_manifesto(execucao):
    manifesto, _ = execucao
    gates = manifesto["disciplines"]["estrutura"]["gates"]
    assert "vibracao_piso" in gates
    assert "desempenho_15575" in gates
    # `nao_verificados` faz parte do gate, nao de um comentario solto
    assert "nao_verificados" in gates["desempenho_15575"]
