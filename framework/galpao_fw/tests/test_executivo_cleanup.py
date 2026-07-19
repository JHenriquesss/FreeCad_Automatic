# ============================================================================
# test_executivo_cleanup.py - rodar_executivo DEVE encerrar o freecad.exe em
# QUALQUER saida (sucesso/erro/timeout). Antes so matava no timeout, e via
# proc.kill() (TerminateProcess), que nao derruba freecad.exe travado nem filhos
# -> zumbis segurando a porta 9875 (caca sessao 14; ver freecad-zumbis-wmi-kill).
# _matar_processo_freecad escalona kill -> taskkill /F /T -> WMI Terminate.
# ============================================================================
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import rodar_projeto as RP


class _ProcDead:
    pid = 99999
    def poll(self):
        return 0                    # ja encerrou


class _ProcKillResolve:
    pid = 99998
    def __init__(self):
        self._seq = [None, 0]       # vivo; morto apos kill()
        self.killed = False
    def poll(self):
        return self._seq.pop(0) if self._seq else 0
    def kill(self):
        self.killed = True


def test_proc_ja_morto_noop():
    # nao deve chamar nada nem levantar
    RP._matar_processo_freecad(_ProcDead())


def test_kill_resolve_sem_escalar():
    p = _ProcKillResolve()
    RP._matar_processo_freecad(p)
    assert p.killed, "deveria ter chamado proc.kill()"


def test_nunca_levanta_com_proc_estranho():
    # proc que sempre reporta vivo mas kill() falha -> escalonamento e best-effort,
    # NUNCA propaga excecao (limpeza nao pode derrubar o pipeline).
    class _Ruim:
        pid = 0                     # pid invalido -> taskkill/WMI no-op
        def poll(self): return None
        def kill(self): raise OSError("nao pode")
    RP._matar_processo_freecad(_Ruim())     # nao deve levantar
