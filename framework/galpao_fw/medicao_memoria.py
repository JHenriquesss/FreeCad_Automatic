# ============================================================================
# medicao_memoria.py - G121: pico de memoria da rodada (stdlib-only, Windows).
# SCRIPT AVULSO: instrumento da producao usado pelo portao do G102 (o teste
# importa daqui, fonte unica) e rodavel a mao (python medicao_memoria.py)
# para sondar a maquina antes da rodada oficial.
#
# O portao do G102 media so TEMPO (CUSTO_TETO_SEG = 1800). Nas quatro mortes
# do G113 o tempo nunca chegou perto do teto - o processo era morto antes
# por falta de memoria. O portao nao via o que o matava (D145/G119, G121).
#
# Este modulo mede o pico RESIDENTE (working set) durante a rodada:
#   - o processo pytest/Python atual (via psapi.GetProcessMemoryInfo), e
#   - a soma de todos os `freecad.exe` visiveis (via EnumProcesses +
#     GetModuleBaseName + GetProcessMemoryInfo, sem psutil, sem parse de
#     `tasklist` dependente de locale).
#
# Limite declarado (nao escondido): a soma do `freecad.exe` e' de TODOS os
# processos visiveis com esse nome, nao so dos filhos desta rodada. Em
# corrida isolada (maquina livre, sem FreeCAD aberto ao lado) equivale aos
# filhos; com outro freecad.exe alheio o numero sai MAIOR (conservador -
# nunca esconde pico). O sampler registra `n_amostras` e
# `n_freecad_max` para auditar.
#
# Sem psutil de proposito: a suite nao depende dele e o G121 nao adiciona
# dependencia para medir. Em nao-Windows, o pico do processo sai via
# `resource.getrusage` e o freecad via `pgrep`/soma zero declarada.
# ============================================================================
"""Pico de memoria residente da rodada (G121). Stdlib-only."""

from __future__ import annotations

import subprocess
import sys
import threading
import time


def memoria_livre_mb():
    """MB livres na maquina (GlobalMemoryStatusEx no Windows). None se falhar."""
    try:
        if sys.platform != "win32":
            return None
        import ctypes

        class _MEMSTAT(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = _MEMSTAT()
        stat.dwLength = ctypes.sizeof(_MEMSTAT)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return None
        return float(stat.ullAvailPhys) / (1024.0 * 1024.0)
    except Exception:
        return None


def memoria_processo_atual_mb():
    """RSS atual do processo pytest/Python em MB. None se nao mensuravel."""
    try:
        if sys.platform == "win32":
            import ctypes
            import ctypes.wintypes

            class _COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_ulong),
                    ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            kernel = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi
            kernel.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [
                ctypes.wintypes.HANDLE,
                ctypes.POINTER(_COUNTERS),
                ctypes.wintypes.DWORD,
            ]
            psapi.GetProcessMemoryInfo.restype = ctypes.wintypes.BOOL
            proc = kernel.GetCurrentProcess()
            cont = _COUNTERS()
            cont.cb = ctypes.sizeof(_COUNTERS)
            if not psapi.GetProcessMemoryInfo(proc, ctypes.byref(cont), cont.cb):
                return None
            return float(cont.WorkingSetSize) / (1024.0 * 1024.0)
        import resource
        return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0
    except Exception:
        return None


def _freecad_mb_ctypes():
    """Soma o RSS de todos os freecad.exe via EnumProcesses. None se falhar."""
    import ctypes
    import ctypes.wintypes

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010

    psapi = ctypes.windll.psapi
    kernel = ctypes.windll.kernel32

    class _COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    psapi.EnumProcesses.argtypes = [
        ctypes.POINTER(ctypes.c_ulong),
        ctypes.wintypes.DWORD,
        ctypes.POINTER(ctypes.wintypes.DWORD),
    ]
    psapi.EnumProcesses.restype = ctypes.wintypes.BOOL
    kernel.OpenProcess.argtypes = [
        ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
    kernel.OpenProcess.restype = ctypes.wintypes.HANDLE
    psapi.GetModuleBaseNameW.argtypes = [
        ctypes.wintypes.HANDLE, ctypes.wintypes.HMODULE,
        ctypes.wintypes.LPWSTR, ctypes.wintypes.DWORD]
    psapi.GetModuleBaseNameW.restype = ctypes.wintypes.DWORD
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.wintypes.HANDLE, ctypes.POINTER(_COUNTERS),
        ctypes.wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = ctypes.wintypes.BOOL

    n = 2048
    pids = (ctypes.c_ulong * n)()
    needed = ctypes.wintypes.DWORD()
    if not psapi.EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(needed)):
        return None
    total = 0.0
    achou = 0

    for i in range(needed.value // ctypes.sizeof(ctypes.c_ulong)):
        pid = pids[i]
        if pid in (0, 4):
            continue
        h = kernel.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                               False, pid)
        if not h:
            continue
        try:
            nome = ctypes.create_unicode_buffer(260)
            if psapi.GetModuleBaseNameW(h, None, nome, 260) <= 0:
                continue
            if nome.value.lower() not in ("freecad.exe", "freecadcmd.exe"):
                continue
            cont = _COUNTERS()
            cont.cb = ctypes.sizeof(_COUNTERS)
            if not psapi.GetProcessMemoryInfo(h, ctypes.byref(cont), cont.cb):
                continue
            total += float(cont.WorkingSetSize) / (1024.0 * 1024.0)
            achou += 1
        finally:
            kernel.CloseHandle(h)
    return total, achou


def memoria_freecad_mb():
    """(soma_mb, n_processos) de freecad.exe+freecadcmd.exe. (0.0, 0) sem nenhum.

    Fallback: `tasklist` quando o ctypes falha. Nunca levanta: em falha
    total devolve (None, 0) para o chamador declarar, nao inventar.
    """
    try:
        if sys.platform == "win32":
            try:
                out = _freecad_mb_ctypes()
                if out is not None:
                    return out
            except Exception:
                pass
            try:
                res = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq freecad.exe", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, timeout=20)
                total = 0.0
                n = 0
                for linha in (res.stdout or "").splitlines():
                    partes = [p.strip().strip('"') for p in linha.split('","')]
                    if len(partes) < 5:
                        continue
                    if partes[0].lower() != "freecad.exe":
                        continue
                    digitos = "".join(c for c in partes[4] if c.isdigit())
                    if digitos:
                        total += float(int(digitos)) / 1024.0
                        n += 1
                return total, n
            except Exception:
                return None, 0
        try:
            res = subprocess.run(["pgrep", "-a", "-i", "freecad"],
                                 capture_output=True, text=True, timeout=20)
            n = len([l for l in (res.stdout or "").splitlines() if l.strip()])
            return 0.0, n
        except Exception:
            return None, 0
    except Exception:
        return None, 0


class MedidorPico:
    """Amostra em thread o RSS do processo + freecad.exe e guarda o pico.

    `pico_total_mb` = max sobre as amostras de (processo + freecad) na
    MESMA amostra - nao a soma dos picos (que podem ser de horas
    distintas). `pico_processo_mb`/`pico_freecad_mb` sao os maximos
    individuais, para dizer onde o pico mora.
    """

    def __init__(self, intervalo_s=1.0):
        # Faixa de validade de intervalo_s: entre 0,2 e 5 s. Abaixo de
        # 0,2 s o proprio EnumProcesses (~50-200 ms) perturba a medida;
        # acima de 5 s um filho freecad.exe curto passa entre duas
        # amostras e o pico sai subestimado. Fora da faixa, erro - nunca
        # clamp silencioso.
        if not 0.2 <= float(intervalo_s) <= 5.0:
            raise ValueError(
                "intervalo_s fora da faixa de validade [0,2..5] s: %r"
                % (intervalo_s,))
        self.intervalo_s = float(intervalo_s)
        self.pico_processo_mb = 0.0
        self.pico_freecad_mb = 0.0
        self.pico_total_mb = 0.0
        self.n_amostras = 0
        self.n_freecad_max = 0
        self.falhou = False
        # G125 (auditoria do G121): amostra em que o PROCESSO mediu e o
        # freecad.exe NAO. Antes virava 0,0 MB em silencio e `falhou` so
        # acendia com os dois lados perdidos - no galpao, onde o freecad e'
        # 91 % do pico, o teto passava sem ter medido o que carrega a rodada.
        self.n_amostras_sem_freecad = 0
        self._parar = threading.Event()
        self._fio = None

    def _amostra(self):
        proc = memoria_processo_atual_mb()
        soma_fc, n_fc = memoria_freecad_mb()
        if proc is None and soma_fc is None:
            self.falhou = True
            return
        if soma_fc is None:
            self.n_amostras_sem_freecad += 1
        proc = proc or 0.0
        soma_fc = soma_fc or 0.0
        self.pico_processo_mb = max(self.pico_processo_mb, proc)
        self.pico_freecad_mb = max(self.pico_freecad_mb, soma_fc)
        self.pico_total_mb = max(self.pico_total_mb, proc + soma_fc)
        self.n_amostras += 1
        self.n_freecad_max = max(self.n_freecad_max, int(n_fc or 0))

    def _laco(self):
        while not self._parar.is_set():
            try:
                self._amostra()
            except Exception:
                self.falhou = True
            self._parar.wait(self.intervalo_s)

    def start(self):
        self._amostra()
        self._fio = threading.Thread(target=self._laco, daemon=True)
        self._fio.start()
        return self

    def stop(self):
        self._parar.set()
        if self._fio is not None:
            self._fio.join(timeout=5.0)
        try:
            self._amostra()
        except Exception:
            self.falhou = True
        return self.resumo()

    def resumo(self):
        return {
            "pico_processo_mb": round(self.pico_processo_mb, 1),
            "pico_freecad_mb": round(self.pico_freecad_mb, 1),
            "pico_total_mb": round(self.pico_total_mb, 1),
            "n_amostras": self.n_amostras,
            "n_freecad_max": self.n_freecad_max,
            "falhou": self.falhou,
            "n_amostras_sem_freecad": self.n_amostras_sem_freecad,
            "freecad_mensuravel": self.n_amostras_sem_freecad == 0,
        }

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
        return False


if __name__ == "__main__":
    import sys as _sys
    try:
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    _soma_fc, _n_fc = memoria_freecad_mb()
    print("livre_MB=%.1f processo_MB=%s freecad_MB=%s n_freecad=%d"
          % (memoria_livre_mb() or -1.0, memoria_processo_atual_mb(),
             _soma_fc, _n_fc))


def veredito_memoria(pico_mb, teto_mb):
    """Gap textual quando o pico estoura o teto; None quando cabe.

    Funcao pura para o vermelho por injecao: teto artificialmente baixo
    reprova, caso bom passa. Pico None (nao mensuravel) nao reprova -
    a ausencia se declara no print, nunca vira gap silencioso nem
    aprovacao inventada.
    """
    if pico_mb is None:
        return None
    try:
        pico = float(pico_mb)
        teto = float(teto_mb)
    except (TypeError, ValueError):
        return None
    if pico > teto:
        return ("memoria pico %.1f MB estoura o teto %.1f MB"
                % (pico, teto))
    return None
