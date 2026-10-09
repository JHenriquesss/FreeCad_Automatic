import os
import sys

import pytest

GALPAO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)


def _carrega_censo():
    # por caminho, sem por tests/ no sys.path (nomes de teste nao sombreiam
    # modulos de producao)
    import importlib.util

    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "censo_freecad.py")
    spec = importlib.util.spec_from_file_location("_censo_freecad_suite", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


_CF = _carrega_censo()


def _carrega_camada_lenta():
    import importlib.util

    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "camada_lenta.py")
    spec = importlib.util.spec_from_file_location("_camada_lenta_suite", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# Fase 1 do plano de 2026-10-08: camada rapida = `pytest -m "not slow"`.
_LENTOS = _carrega_camada_lenta().arquivos_lentos(_CF.GRUPO_FREECAD)
_AMOSTRADOR = None


def _distribuida(config):
    return bool(getattr(config.option, "numprocesses", None)) \
        and not hasattr(config, "workerinput")


def _worker_xdist(config):
    """D179: so um worker de verdade (config.workerinput) escreve no censo.
    Um pytest aninhado (test_G21 roda pytest em subprocesso) herda
    GALPAO_CENSO_FREECAD e PYTEST_XDIST_WORKER do worker externo e, sem este
    filtro, ligava um amostrador proprio e sobrescrevia coletados-gwN.json
    da corrida de fora (medido nas corridas A/B do G153). `-n 0` explicito
    (runner sem workers) continua escrevendo como 'master'; o pytest aninhado
    nao passa `-n` (numprocesses None) e fica de fora."""
    return (hasattr(config, "workerinput")
            or getattr(config.option, "numprocesses", None) == 0)


def pytest_configure(config):
    """D164: sob xdist, o censo do FreeCAD liga sozinho (o controlador cria a
    pasta antes de subir os workers, que herdam o ambiente)."""
    global _AMOSTRADOR
    if _distribuida(config) and not os.environ.get(_CF.ENV_DIR):
        import tempfile

        os.environ[_CF.ENV_DIR] = tempfile.mkdtemp(prefix="censo_freecad_")
    pasta = os.environ.get(_CF.ENV_DIR)
    if pasta and _worker_xdist(config):
        worker = os.environ.get("PYTEST_XDIST_WORKER", "master")
        _AMOSTRADOR = _CF.Amostrador(
            os.path.join(pasta, "freecad-%s.jsonl" % worker), worker)
        _AMOSTRADOR.start()


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    """D164: quem sobe freecad vai para um grupo xdist unico (um por vez)."""
    arquivos = set()
    for item in items:
        arq = _CF.arquivo_do_nodeid(item.nodeid)
        arquivos.add(arq)
        if arq in _CF.GRUPO_FREECAD:
            item.add_marker(pytest.mark.xdist_group(name=_CF.NOME_GRUPO))
        if arq in _LENTOS:
            item.add_marker(pytest.mark.slow)
    pasta = os.environ.get(_CF.ENV_DIR)
    if pasta and _worker_xdist(config):
        import json

        worker = os.environ.get("PYTEST_XDIST_WORKER", "master")
        with open(os.path.join(pasta, "coletados-%s.json" % worker), "w",
                  encoding="utf-8") as fh:
            json.dump(sorted(arquivos), fh)


def pytest_runtest_logstart(nodeid, location):
    if _AMOSTRADOR is not None:
        _AMOSTRADOR.atual = nodeid


def pytest_sessionfinish(session, exitstatus):
    """Worker: fecha o amostrador. Controlador de corrida distribuida: teste
    fora do grupo que subiu freecad reprova a corrida (o sentido da isencao
    morta so vale em corrida inteira e mora em tools/suite_paralela.py)."""
    if _AMOSTRADOR is not None:
        _AMOSTRADOR.parar()
        return
    pasta = os.environ.get(_CF.ENV_DIR)
    if pasta and _distribuida(session.config):
        violacoes, _mortas = _CF.confere_censo(
            _CF.ler_registros(pasta), _CF.ler_coletados(pasta), False)
        if violacoes:
            rep = session.config.pluginmanager.get_plugin("terminalreporter")
            for linha in violacoes:
                if rep is not None:
                    rep.write_line(linha, red=True)
            session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture
def turnkey_fixture():
    def make(**overrides):
        value = {
            "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
            "concreto": {"vao": 20.0, "n_porticos": 7, "v0": 40.0, "cat": "IV",
                         "classe": "B", "s1": 1.0, "s3": 1.0, "G_roof": 0.30,
                         "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
                         "sigma_solo_adm": 250.0,
                         # galpao com sistema de estabilidade longitudinal: le_y
                         # segue 15.6 e nao 2H (NBR 6118 15.8.3.3.2 exige lambda<=90)
                         "travamento_longitudinal": "topo"},
            "eletrico": {"tensao_V": 380.0,
                         "cargas": {"iluminacao_kW": 20.0, "ilum_fp": 0.92,
                                    "ocupacao": "industrial"},
                         "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}},
            "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                         "deteccao": {"viga_m": 0.0}},
        }
        for key, value_override in overrides.items():
            value[key] = value_override
        return value

    return make


@pytest.fixture
def turnkey_fixture_with_hvac_and_hydraulic(turnkey_fixture):
    return turnkey_fixture(climatizacao={"tipo": "galpao"}, hidraulica={})
