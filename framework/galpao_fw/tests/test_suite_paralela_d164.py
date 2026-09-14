"""D164 - o censo que deixa a suite rodar em paralelo sem dois FreeCAD juntos.

A lista do grupo serial (tests/censo_freecad.GRUPO_FREECAD) e cobrada por
medicao nos dois sentidos; aqui mora o vermelho por injecao da conferencia
e a prova de que o amostrador enxerga um processo de verdade.
"""
import os
import shutil
import subprocess
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import censo_freecad as cf  # noqa: E402


def _reg(nodeid, pid=1):
    return {"worker": "gw0", "pid": pid, "exe": "freecad.exe", "nodeid": nodeid}


def test_01_conferencia_vermelha_nos_dois_sentidos():
    grupo = {"tests/test_a.py": "sobe freecad (medido)"}
    coletados = {"tests/test_a.py", "tests/test_b.py"}
    lados = []
    # caso bom: quem subiu esta no grupo, e o grupo subiu
    bom = cf.confere_censo([_reg("tests/test_a.py::t1@freecad")], coletados,
                           True, grupo)
    if bom != ([], []):
        lados.append("caso bom reprova: %r" % (bom,))
    # fora do grupo subiu freecad -> violacao nomeando arquivo e teste
    v, _m = cf.confere_censo([_reg("tests/test_a.py::t1@freecad"),
                              _reg("tests/test_b.py::t9", pid=2)],
                             coletados, True, grupo)
    if not (len(v) == 1 and "tests/test_b.py" in v[0] and "t9" in v[0]):
        lados.append("fora do grupo nao acusou: %r" % (v,))
    # grupo que nao subiu em corrida inteira -> isencao morta
    v, m = cf.confere_censo([], coletados, True, grupo)
    if not (v == [] and len(m) == 1 and "tests/test_a.py" in m[0]):
        lados.append("isencao morta nao acusou: %r" % ((v, m),))
    # recorte (nao e corrida inteira) nao acusa morta, nem arquivo do grupo
    # que nao foi coletado
    for coleta, inteira in ((coletados, False), ({"tests/test_b.py"}, True)):
        res = cf.confere_censo([], coleta, inteira, grupo)
        if res != ([], []):
            lados.append("recorte %r acusou: %r" % (sorted(coleta), res))
    assert not lados, "\n".join(lados)


def test_02_arvore_de_processos_so_descendente():
    tabela = [(10, 1, "python.exe"), (11, 10, "cmd.exe"),
              (12, 11, "freecadcmd.exe"), (13, 99, "freecad.exe"),
              (14, 10, "freecad.exe"), (20, 21, "freecad.exe"),
              (21, 20, "python.exe")]                 # ciclo nao trava
    obtido = (sorted(cf.freecad_descendentes(10, tabela)),
              cf.freecad_descendentes(99, tabela),
              cf.arquivo_do_nodeid("tests/x/test_y.py::t[a::b]@freecad"))
    assert obtido == ([(12, "freecadcmd.exe"), (14, "freecad.exe")],
                      [(13, "freecad.exe")], "tests/x/test_y.py"), obtido


@pytest.mark.skipif(sys.platform != "win32", reason="Toolhelp32 e do Windows")
def test_03_amostrador_enxerga_processo_de_verdade(tmp_path):
    """Um executavel com o nome vigiado, filho deste processo, tem de aparecer
    no registro com o teste corrente; um filho de outro nome nao aparece. Sem
    isto o censo passaria por ser cego (G119). O nome vigiado aqui NAO e
    freecad*.exe: o amostrador do proprio worker (censo ligado sob xdist)
    registraria o falso como FreeCAD fora do grupo."""
    ping = shutil.which("ping") or r"C:\Windows\System32\PING.EXE"
    falso = tmp_path / "vigiado_d164.exe"
    outro = tmp_path / "outro.exe"
    shutil.copyfile(ping, falso)
    shutil.copyfile(ping, outro)
    destino = str(tmp_path / "freecad-teste.jsonl")
    amostrador = cf.Amostrador(destino, "teste", intervalo_s=0.2,
                               exes=("vigiado_d164.exe",))
    amostrador.atual = "tests/test_suite_paralela_d164.py::test_03"
    amostrador.start()
    procs = [subprocess.Popen([str(exe), "-n", "4", "127.0.0.1"],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
             for exe in (falso, outro)]
    try:
        time.sleep(1.5)
    finally:
        amostrador.parar()
        for p in procs:
            p.kill()
            p.wait()
    registros = cf.ler_registros(str(tmp_path))
    assert [(r["pid"], r["exe"], r["nodeid"]) for r in registros] == [
        (procs[0].pid, "vigiado_d164.exe",
         "tests/test_suite_paralela_d164.py::test_03")], registros


def test_04_grupo_existe_e_tem_motivo_medido():
    """Entrada do grupo aponta para arquivo que existe e diz o que foi medido
    (quantos processos, em que teste). Motivo generico reprova: o grupo e
    congelado por medicao, nao por grep (a isencao morta mora no runner)."""
    lados = []
    for arq, motivo in sorted(cf.GRUPO_FREECAD.items()):
        if not os.path.isfile(os.path.join(GALPAO, arq)):
            lados.append("%s: arquivo inexistente" % arq)
        texto = (motivo or "").lower()
        if ("d164" not in texto or " em test_" not in texto
                or "a medir" in texto or "inicial" in texto):
            lados.append("%s: motivo sem medicao (%r)" % (arq, motivo))
    assert not lados, "\n".join(lados)
