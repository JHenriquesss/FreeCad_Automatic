"""G148 parte 1 - piso de memoria livre no runner (fonte: tools/suite_paralela.py).

O runner so REGISTRAVA `memoria_livre_min_mb`; cruzada a zona de morte a suite
morria pelo harness sem nome (D172: serial morta em 24 %). O piso deriva do
medido (menor minimo que passou 159 MB + pico do G102-galpao 1679-2111 MB com
freecad.exe 1535-1968 MB em 8 GB): abaixo dele o runner grava os testes de cada
worker (o censo ja sabe) e sai como quebra nomeada, sem matar processo do
usuario. Cobertura que NAO se move neste goal (parte 2, com decisao do usuario):
o galpao do G102 segue na suite do goal.

Convencoes: baseline nos dois sentidos (test_01/test_02), injecao em tmp_path
(test_03/test_04, o repo nunca e mutado), instrumento acusa por parte (o gap
nomeia piso + livre), constante medida lida pela producao (test_01, conv. 8).
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(GALPAO, "tools"))
sys.path.insert(0, HERE)

import suite_paralela as sp  # noqa: E402


def test_01_piso_derivado_do_medido_e_lido_pela_producao():
    """O piso existe, vale 200 e o motivo medido esta escrito; a producao le.

    Convencao 8: constante "medida" que a producao nao le e comentario - aqui o
    runner le o piso por default (veredito + resumo), e o motivo cita as fontes
    (159 MB do G142, pico do G102-galpao, freecad.exe). Mudar o valor ou apagar
    a leitura reprova.
    """
    lados = []
    if sp.PISO_MEMORIA_LIVRE_MB != 200:
        lados.append("PISO_MEMORIA_LIVRE_MB=%r, esperado 200 (derivado do "
                     "medido G148)" % (sp.PISO_MEMORIA_LIVRE_MB,))
    fonte = open(os.path.join(GALPAO, "tools", "suite_paralela.py"),
                 encoding="utf-8").read()
    for marca in ("159", "G102", "1679", "2111", "freecad.exe",
                  "PISO_MEMORIA_LIVRE_MB", "piso_memoria_livre_mb",
                  "testes_por_worker"):
        if marca not in fonte:
            lados.append("derivacao/leitura sem a marca %r no fonte" % marca)
    # a producao le por default: sem piso explicito, 0 acusa e folga passa
    if sp.veredito_piso_memoria(0) is None:
        lados.append("a producao nao le o piso por default (0 passou)")
    if sp.veredito_piso_memoria(100000) is not None:
        lados.append("folga de 100 GB acusou com o piso default")
    # o resumo carrega o piso usado (auditoria D165: opcao declarada, nunca
    # silenciosa) - basta o campo existir no construtor do resumo
    if '"piso_memoria_livre_mb"' not in fonte.replace("'", '"'):
        lados.append("resumo.json sem o campo piso_memoria_livre_mb")
    assert not lados, "piso G148 reprova:\n" + "\n".join(lados)


def test_02_veredito_piso_vermelho_nos_dois_sentidos():
    """Amostrador falso: abaixo acusa nomeando, no piso/acima passa, None cala.

    Cobre ausente (None), zero e presente (convencao 13 na forma do runner: uma
    so porta de entrada, a leitura da maquina).
    """
    lados = []
    baixo = sp.veredito_piso_memoria(50, 200)
    if baixo is None or "200" not in baixo or "50" not in baixo:
        lados.append("livre 50 < piso 200 nao acusou nomeando: %r" % (baixo,))
    elif "G148" not in baixo or "usuario" not in baixo:
        lados.append("gap sem nomear o goal nem a garantia: %r" % (baixo,))
    if sp.veredito_piso_memoria(0, 200) is None:
        lados.append("livre 0 (zero) passou com piso 200")
    if sp.veredito_piso_memoria(200, 200) is not None:
        lados.append("livre == piso acusou (a quebra e ao CRUZAR, <)")
    if sp.veredito_piso_memoria(5000, 200) is not None:
        lados.append("folga 5000 acusou com piso 200")
    if sp.veredito_piso_memoria(None, 200) is not None:
        lados.append("livre None (nao mensuravel) virou gap em vez de declarar")
    if sp.veredito_piso_memoria(50, None) is not None:
        lados.append("piso None virou gap em vez de declarar")
    if sp.veredito_piso_memoria(100, 500) is None:
        lados.append("piso custom 500 nao acusou livre 100")
    if sp.veredito_piso_memoria(600, 500) is not None:
        lados.append("piso custom 500 acusou livre 600")
    assert not lados, "veredito do piso reprova:\n" + "\n".join(lados)


def test_03_testes_por_worker_agrupa_o_censo_em_tmp_path(tmp_path):
    """O snapshot por worker agrupa o que o censo ja sabe; vazio declara."""
    censo = tmp_path / "censo"
    censo.mkdir()
    (censo / "coletados-gw0.json").write_text(
        json.dumps(["tests/test_b.py", "tests/test_a.py"]), encoding="utf-8")
    (censo / "coletados-gw1.json").write_text(
        json.dumps(["tests/test_c.py"]), encoding="utf-8")
    (censo / "freecad-gw0.jsonl").write_text(
        json.dumps({"worker": "gw0", "pid": 11, "exe": "freecad.exe",
                    "nodeid": "tests/test_a.py::t1"}) + "\n"
        + json.dumps({"worker": "gw1", "pid": 22, "exe": "freecadcmd.exe",
                      "nodeid": "tests/test_c.py::t9"}) + "\n",
        encoding="utf-8")
    obtido = sp.testes_por_worker(str(censo))
    lados = []
    if obtido.get("gw0", {}).get("coletados") != ["tests/test_a.py",
                                                  "tests/test_b.py"]:
        lados.append("coletados do gw0 fora: %r" % (obtido.get("gw0"),))
    if obtido.get("gw0", {}).get("freecad_testes") != ["tests/test_a.py::t1"]:
        lados.append("freecad do gw0 fora: %r" % (obtido.get("gw0"),))
    if obtido.get("gw1", {}).get("freecad_testes") != ["tests/test_c.py::t9"]:
        lados.append("freecad do gw1 fora: %r" % (obtido.get("gw1"),))
    if sp.testes_por_worker(str(tmp_path / "vazio")) != {}:
        lados.append("diretorio vazio nao declarou {}")
    assert not lados, "snapshot por worker reprova:\n" + "\n".join(lados)


def _recorte_rapido():
    return ("tests/test_suite_paralela_d164.py::"
            "test_01_conferencia_vermelha_nos_dois_sentidos")


def _ler_resumo(saida):
    with open(os.path.join(saida, "resumo.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_04_quebra_nomeada_com_amostrador_falso_sem_matar_usuario(tmp_path):
    """Injecao no runner: amostrador falso baixo aborta com quebra nomeada.

    Roda um recorte rapido pelo proprio main com o amostrador falso (convencao
    2: tmp_path, repo intacto): a 1a leitura respira, as seguintes secam. O
    resumo sai com a quebra do piso + snapshot por worker + minimo do falso, e
    um processo "do usuario" (filho deste teste, nao do runner) segue vivo -
    o runner so termina o proprio filho pytest. O outro sentido (falso sempre
    alto) fecha sem quebra do piso.

    G153: o piso agora confirma em 3 amostras seguidas (CONFIRMACAO_PISO_
    AMOSTRAS) - a sequencia 50/40/30 confirma na 3a, por isso o minimo e 30
    (antes, amostra unica, era 50) e a quebra diz "confirmado em 3".
    """
    usuario = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(120)"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        leituras = iter([5000.0, 5000.0, 50.0, 40.0, 30.0])

        def falso():
            try:
                return next(leituras)
            except StopIteration:
                return 30.0

        saida = str(tmp_path / "saida_brecha")
        rc = sp.main(["-n", "1", "--saida", saida, _recorte_rapido()],
                     _amostra_fn=falso, _intervalo_s=0.2)
        resumo = _ler_resumo(saida)
        lados = []
        if rc != 1:
            lados.append("brecha retornou rc=%r, esperado 1" % (rc,))
        if not any("piso de memoria livre" in q for q in resumo["quebras"]):
            lados.append("sem quebra nomeada do piso: %r" % (resumo["quebras"],))
        if not any("200" in q for q in resumo["quebras"]):
            lados.append("quebra sem nomear o piso 200: %r" % (resumo["quebras"],))
        if resumo.get("piso_memoria_livre_mb") != 200:
            lados.append("resumo sem o piso usado: %r" % (resumo,))
        if "testes_por_worker" not in resumo:
            lados.append("resumo sem snapshot por worker")
        if resumo.get("memoria_livre_min_mb") != 30:
            lados.append("minimo nao e o do falso (30, 3a leitura seguida): %r"
                         % (resumo.get("memoria_livre_min_mb"),))
        if not any("confirmado em 3" in q for q in resumo["quebras"]):
            lados.append("quebra sem dizer a confirmacao G153: %r"
                         % (resumo["quebras"],))
        if usuario.poll() is not None:
            lados.append("o runner matou o processo do usuario")
        assert not lados, "brecha G148 reprova:\n" + "\n".join(lados)
    finally:
        if usuario.poll() is None:
            usuario.terminate()
            try:
                usuario.wait(timeout=15)
            except Exception:
                usuario.kill()

    saida_ok = str(tmp_path / "saida_folga")
    rc_ok = sp.main(["-n", "1", "--saida", saida_ok, _recorte_rapido()],
                    _amostra_fn=lambda: 5000.0, _intervalo_s=0.2)
    resumo_ok = _ler_resumo(saida_ok)
    assert rc_ok == 0, (rc_ok, resumo_ok["quebras"])
    assert resumo_ok["quebras"] == [], resumo_ok["quebras"]
    assert resumo_ok["piso_memoria_livre_mb"] == 200, resumo_ok
