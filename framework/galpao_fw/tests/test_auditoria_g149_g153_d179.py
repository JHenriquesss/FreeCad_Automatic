"""D179 - auditoria do lote G149-G153 (medida, nao lida).

Defeitos medidos e fechados aqui:
  1. O censo do FreeCAD descartava por PID: o Windows reusa PID e o freecad de
     um teste posterior com PID ja visto no mesmo worker sumia do registro -
     "isencao morta" falsa (a quebra da corrida B do G153; o processo do
     test_ifc_secundarios vive ~40 s, nao e "curto").
  2. O pytest aninhado (test_G21 roda pytest em subprocesso) herdava a pasta
     do censo e o nome do worker externo, ligava um amostrador proprio e
     sobrescrevia coletados-gwN.json da corrida de fora (A e B do G153:
     gw1/gw2 = ["tests/test_fronteiras.py"]).
  3. O G149 passou a imprimir no resultado, no memorial e na folha que o FS
     3,0 da estaca e "default normativo NBR 6122". O acervo (NBR 6122:2022
     p.18) diz 2,0 em 6.2.1.2.1 (semiempirico) e 1,6 em 6.2.1.2.2 (com prova de
     carga); o 3,00 e da Tabela 1 (fundacao rasa). O numero e a trava ficam
     (decisao do responsavel); a origem deixa de se dizer normativa.
  4. O fck/fyk do bloco "herdado do material do projeto" pode ser o valor do
     modelo PS.novo (25 MPa) que o wizard nunca pergunta: o texto diz isso.
"""
import ast
import glob
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(GALPAO))
sys.path.insert(0, GALPAO)

OCR_6122 = os.path.join(
    REPO, "fontes", "03_FUNDACOES_GEOTECNIA",
    "FUNDACOES__NBR__NBR-6122-2022__projeto-fundacoes-ocr.txt")


def _censo():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_censo_d179", os.path.join(HERE, "censo_freecad.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_01_pid_reusado_volta_a_ser_avistado(tmp_path, monkeypatch):
    cf = _censo()
    amostrador = cf.Amostrador(str(tmp_path / "freecad-gw0.jsonl"), "gw0")
    raiz = amostrador._raiz
    tabela = {"t": [(raiz, 1, "python.exe"), (500, raiz, "freecadcmd.exe")]}
    monkeypatch.setattr(cf, "processos", lambda: tabela["t"])
    amostrador.atual = "tests/x_primeiro.py::t1"
    amostrador.amostra()
    amostrador.amostra()                       # mesmo processo vivo: 1 registro
    tabela["t"] = [(raiz, 1, "python.exe")]    # morreu
    amostrador.amostra()
    tabela["t"] = [(raiz, 1, "python.exe"), (500, raiz, "freecadcmd.exe")]
    amostrador.atual = "tests/y_segundo.py::t2"
    amostrador.amostra()
    registros = cf.ler_registros(str(tmp_path))
    grupo = {"tests/x_primeiro.py": "m", "tests/y_segundo.py": "m"}
    _viol, mortas = cf.confere_censo(registros, set(grupo), True, grupo=grupo)
    assert ([(r["pid"], r["nodeid"]) for r in registros]
            == [(500, "tests/x_primeiro.py::t1"), (500, "tests/y_segundo.py::t2")]
            and mortas == []), (registros, mortas)


def _coleta_aninhada(pasta, extra):
    env = dict(os.environ, PYTHONUTF8="1", GALPAO_CENSO_FREECAD=str(pasta),
               PYTEST_XDIST_WORKER="gw7")
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "--collect-only", "tests/test_suite_paralela_d164.py"] + extra
    return subprocess.run(cmd, cwd=GALPAO, env=env, capture_output=True,
                          text=True, timeout=300)


def test_02_pytest_aninhado_nao_escreve_no_censo_de_fora(tmp_path):
    fora = tmp_path / "aninhado"
    fora.mkdir()
    r1 = _coleta_aninhada(fora, [])
    serial = tmp_path / "serial_n0"
    serial.mkdir()
    r2 = _coleta_aninhada(serial, ["-n", "0"])
    lados = []
    if r1.returncode != 0 or r2.returncode != 0:
        lados.append("coleta falhou: %s / %s" % (r1.stdout[-500:], r2.stdout[-500:]))
    if sorted(os.listdir(fora)):
        lados.append("pytest aninhado escreveu no censo de fora: %r"
                     % sorted(os.listdir(fora)))
    if not [n for n in os.listdir(serial) if n.startswith("coletados-")]:
        lados.append("-n 0 explicito deixou de escrever o censo: %r"
                     % sorted(os.listdir(serial)))
    assert not lados, "\n".join(lados)


def _textos_producao():
    for caminho in sorted(glob.glob(os.path.join(GALPAO, "*.py"))):
        with open(caminho, encoding="utf-8") as fh:
            yield os.path.basename(caminho), fh.read()


def test_03_fs_da_estaca_nao_se_diz_normativo():
    import estaca_parametros_g143 as EP
    import estaca_profunda as ep
    import projeto_spec as PS

    lados = []
    linha = EP.linha_fs_g149(3.0, EP.ORIGEM_FS_ADOTADO)
    for termo in ("adotado", "D38", "6.2.1.2.1", "2,0"):
        if termo not in linha:
            lados.append("linha do FS sem %r: %r" % (termo, linha))
    if "normativo" in linha.lower():
        lados.append("linha do FS ainda se diz normativa: %r" % linha)
    for nome, texto in _textos_producao():
        if "default_normativo" in texto:
            lados.append("%s ainda carimba default_normativo" % nome)
        arvore = ast.parse(texto)
        for no in ast.walk(arvore):
            if (isinstance(no, ast.Constant) and isinstance(no.value, str)
                    and "3,0" in no.value and "NBR 6122" in no.value
                    and "6.2.1.2" not in no.value):
                lados.append("%s:%d atribui 3,0 a NBR 6122 sem o item: %r"
                             % (nome, no.lineno, no.value))
    # o numero e a trava nao mudam (decisao do responsavel, nao da auditoria)
    if ep.FS_GLOBAL != 3.0:
        lados.append("FS_GLOBAL mudou sem decisao: %r" % ep.FS_GLOBAL)
    s = PS.novo()
    s["fundacao"]["tipo"] = "estaca"
    s["fundacao"]["estaca"] = {"FS": 2.5}
    msgs = [m for _p, m in PS.validar(s)["faltando"] if "FS=2.50" in m]
    if not msgs or "regra adotada no D38" not in msgs[0] \
            or "6.2.1.2.1" not in msgs[0]:
        lados.append("trava do FS<3 sem a atribuicao corrigida: %r" % msgs)
    if os.path.isfile(OCR_6122):
        with open(OCR_6122, encoding="utf-8") as fh:
            norma = fh.read()
        trecho = norma[norma.find("6.2.1.2.1"):][:220]
        if "2,0" not in trecho or "semiempirico" not in trecho:
            lados.append("acervo nao sustenta a citacao: %r" % trecho)
    assert not lados, "D179 FS:\n" + "\n".join(lados)


def test_03b_acervo_da_6122_presente_ou_declarado():
    if not os.path.isfile(OCR_6122):
        pytest.skip("acervo fontes/ ausente (ignorado pelo git): a citacao "
                    "6.2.1.2.1 = 2,0 foi conferida no D179 na pagina 18 do PDF")
    with open(OCR_6122, encoding="utf-8") as fh:
        norma = fh.read()
    assert "fator de seguranca global a ser uilizado para deteminacao da " \
           "carga admissivel e 2,0" in norma


def _arquivo_lento_sem_raiz(texto):
    """True se o fonte gera arquivo de teste para o runner aninhado
    (`sp.main` + `"def test_`) sem por um pytest.ini ao lado (D179)."""
    return ("sp.main(" in texto and '"def test_' in texto
            and "pytest.ini" not in texto)


def test_05_runner_aninhado_com_raiz_propria(tmp_path):
    """A serial da D179 falhou no test_04 do G153: o arquivo lento morava no
    Temp sem ini, a raiz do pytest aninhado virou C:\\Users\\<user> e a coleta
    varreu o Temp (pasta do Playwright apagada no meio). Todo teste que gera
    arquivo para o runner aninhado poe um pytest.ini ao lado."""
    ruins = []
    for caminho in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
        with open(caminho, encoding="utf-8") as fh:
            if _arquivo_lento_sem_raiz(fh.read()):
                ruins.append(os.path.basename(caminho))
    injetado = ('rc = sp.main(["-n", "1", str(lento)])\n'
                'lento.write_text("def test_x(): pass")\n')
    lados = []
    if ruins:
        lados.append("sem pytest.ini ao lado do teste temporario: %r" % ruins)
    if not _arquivo_lento_sem_raiz(injetado):
        lados.append("a guarda nao acusa o caso injetado")
    if _arquivo_lento_sem_raiz(injetado + '(tmp_path / "pytest.ini")\n'):
        lados.append("a guarda acusa o caso corrigido")
    assert not lados, "\n".join(lados)


def test_04_fck_do_bloco_diz_que_pode_ser_o_modelo():
    import estaca_parametros_g143 as EP

    texto = EP._fmt_origem(EP.ORIGEM_MATERIAL_PROJETO)
    assert ("wizard nao pergunta" in texto and "PS.novo" in texto
            and "confirmar" in texto), texto
