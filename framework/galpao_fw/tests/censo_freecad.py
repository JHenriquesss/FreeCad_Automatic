"""D164 - censo de quem sobe o FreeCAD dentro da suite (infra de teste).

A suite roda em paralelo (pytest-xdist, `tools/suite_paralela.py`) e o
freecad.exe pesa ~2 GB numa maquina de 8 GB: dois ao mesmo tempo matam a
corrida por memoria (G113), e o portao de memoria do G102 soma todo
freecad.exe visivel. Os arquivos que sobem freecad.exe/freecadcmd.exe ficam
num grupo xdist unico (um por vez); o resto se espalha.

Grupo escrito a mao sem medir apodrece nos dois sentidos, entao a lista e
cobrada por medicao: cada worker amostra a arvore de processos (Toolhelp32,
stdlib/ctypes, sem psutil) e anota qual teste estava rodando quando um
freecad descendente apareceu pela primeira vez. `confere_censo` reprova
  - teste FORA do grupo que subiu freecad (vizinho de memoria nao declarado);
  - arquivo DO grupo que, numa corrida inteira, nao subiu nenhum (isencao
    morta: serializa a toa e esconde custo).
"""
import ctypes
import glob
import json
import os
import sys
import threading

ENV_DIR = "GALPAO_CENSO_FREECAD"
NOME_GRUPO = "freecad"
EXES_FREECAD = ("freecad.exe", "freecadcmd.exe")

# arquivo (relativo a framework/galpao_fw) -> motivo medido.
GRUPO_FREECAD = {
    # Medido na corrida inteira D164 (2026-09-13, -n 3, 3837 passed): cada
    # entrada subiu freecad.exe/freecadcmd.exe descendente do worker, no
    # teste citado. Os 25 arquivos que o grep apontava e NAO subiram (subprocesso
    # Python, FreeCAD simulado ou rota SVG) sairam: serializavam a toa.
    "tests/branches/g8/test_g8_entregaveis_no_loop.py":
        "1 freecadcmd.exe em test_o_3d_da_arquitetura_sem_solido_declarado_"
        "e_indisponivel (D164)",
    "tests/branches/g8/test_g8_xcheck_freecad.py":
        "1 freecadcmd.exe em test_o_build_gera_os_tres_arquivos (D164)",
    "tests/test_build_concreto.py":
        "1 freecadcmd.exe em test_build_headless_gera_solidos_sem_"
        "interferencia (D164)",
    "tests/test_build_eletrico.py":
        "1 freecadcmd.exe em test_build_headless_gera_solidos_sem_clash (D164)",
    "tests/test_build_federado.py":
        "2 processos: freecadcmd.exe em test_montar_3d_federado_vivo_e_"
        "consistente_com_aabb, freecad.exe em test_render_federado_gera_pngs "
        "(D164)",
    "tests/test_executivo_eletrico.py":
        "2 processos (freecadcmd.exe + freecad.exe) em "
        "test_build_gera_pranchas_pdf (D164)",
    "tests/test_fase3_fundacao_profunda.py":
        "1 freecadcmd.exe em test_build_desenha_estaca_bloco_baldrame (D164)",
    "tests/test_fase5_corte_seccionado.py":
        "1 freecadcmd.exe em test_secao_ligacao_gera_corte_com_arestas (D164)",
    "tests/test_fase64_coluna_tapered.py":
        "1 freecadcmd.exe em test_build_coluna_tapered (D164)",
    "tests/test_fase65_zona_painel.py":
        "1 freecadcmd.exe em test_build_sem_reforco_nao_cria_doubler (D164)",
    "tests/test_fase6b_alma_variavel.py":
        "1 freecadcmd.exe em test_build_rafter_tapered (D164)",
    "tests/test_fase6c_tesoura.py":
        "1 freecadcmd.exe em test_build_tesoura_barras (D164)",
    "tests/test_ifc_secundarios_xcheck.py":
        "1 freecadcmd.exe em test_terca_puro_bate_com_o_build (D164)",
    # D177: tests/test_indice_disco_rodada_g102.py saiu. Os 7 processos do
    # D164 eram da rodada do galpao, que foi para o test_10 (auditoria do
    # lote, GALPAO_AUDITORIA=1, serial, como o aco do D165); casa e predio
    # no test_01 nao sobem freecad (CUSTO_MEDIDO_N_FREECAD 0/0). Ficar aqui
    # seria isencao morta na corrida do goal.
    "tests/test_techdraw_concreto.py":
        "2 processos em test_build_gera_pranchas_pdf (D164)",
}


def arquivo_do_nodeid(nodeid):
    """'tests/x.py::t[p]@freecad' -> 'tests/x.py'."""
    return nodeid.split("::", 1)[0].replace("\\", "/")


# --- arvore de processos (Windows, Toolhelp32) -------------------------------

class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.c_ulong), ("cntUsage", ctypes.c_ulong),
                ("th32ProcessID", ctypes.c_ulong),
                ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", ctypes.c_ulong), ("cntThreads", ctypes.c_ulong),
                ("th32ParentProcessID", ctypes.c_ulong),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", ctypes.c_ulong),
                ("szExeFile", ctypes.c_wchar * 260)]


def processos():
    """[(pid, ppid, exe_minusculo)]; lista vazia fora do Windows ou em falha."""
    if sys.platform != "win32":
        return []
    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    snap = k32.CreateToolhelp32Snapshot(0x00000002, 0)   # TH32CS_SNAPPROCESS
    if not snap or snap == ctypes.c_void_p(-1).value:
        return []
    saida = []
    try:
        ent = _PROCESSENTRY32W()
        ent.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
        ok = k32.Process32FirstW(ctypes.c_void_p(snap), ctypes.byref(ent))
        while ok:
            saida.append((int(ent.th32ProcessID), int(ent.th32ParentProcessID),
                          ent.szExeFile.lower()))
            ok = k32.Process32NextW(ctypes.c_void_p(snap), ctypes.byref(ent))
    finally:
        k32.CloseHandle(ctypes.c_void_p(snap))
    return saida


def freecad_descendentes(raiz_pid, tabela=None, exes=EXES_FREECAD):
    """[(pid, exe)] dos freecad cuja cadeia de pais chega a raiz_pid."""
    tabela = processos() if tabela is None else tabela
    pai = {pid: ppid for pid, ppid, _exe in tabela}
    achados = []
    for pid, _ppid, exe in tabela:
        if exe not in exes:
            continue
        atual, vistos = pid, set()
        while atual in pai and atual not in vistos and len(vistos) < 32:
            vistos.add(atual)
            atual = pai[atual]
            if atual == raiz_pid:
                achados.append((pid, exe))
                break
    return achados


class Amostrador(threading.Thread):
    """Anota o primeiro avistamento de cada freecad descendente deste processo
    com o teste que estava rodando (ou o ultimo que rodou)."""

    def __init__(self, destino, worker, intervalo_s=0.5, exes=EXES_FREECAD):
        super().__init__(daemon=True)
        self.destino = destino
        self.worker = worker
        self.intervalo_s = intervalo_s
        self.exes = tuple(exes)
        self.atual = None
        self._vistos = set()
        self._parar = threading.Event()
        self._raiz = os.getpid()

    def run(self):
        while not self._parar.wait(self.intervalo_s):
            self.amostra()

    def amostra(self):
        try:
            novos = [(pid, exe) for pid, exe
                     in freecad_descendentes(self._raiz, exes=self.exes)
                     if pid not in self._vistos]
        except Exception:                                   # noqa: BLE001
            return
        if not novos:
            return
        with open(self.destino, "a", encoding="utf-8") as fh:
            for pid, exe in novos:
                self._vistos.add(pid)
                fh.write(json.dumps({"worker": self.worker, "pid": pid,
                                     "exe": exe, "nodeid": self.atual}) + "\n")

    def parar(self):
        self.amostra()
        self._parar.set()


# --- leitura e conferencia ---------------------------------------------------

def ler_registros(pasta):
    registros = []
    for caminho in sorted(glob.glob(os.path.join(pasta, "freecad-*.jsonl"))):
        with open(caminho, encoding="utf-8") as fh:
            registros.extend(json.loads(l) for l in fh if l.strip())
    return registros


def ler_coletados(pasta):
    coletados = set()
    for caminho in glob.glob(os.path.join(pasta, "coletados-*.json")):
        with open(caminho, encoding="utf-8") as fh:
            coletados.update(json.load(fh))
    return coletados


def arquivos_que_subiram(registros):
    """{arquivo: {"processos": n, "testes": [nodeids]}}."""
    saida = {}
    for r in registros:
        arq = arquivo_do_nodeid(r.get("nodeid") or "(fora de teste)")
        item = saida.setdefault(arq, {"processos": 0, "testes": []})
        item["processos"] += 1
        nodeid = (r.get("nodeid") or "").split("@", 1)[0]
        if nodeid and nodeid not in item["testes"]:
            item["testes"].append(nodeid)
    return dict(sorted(saida.items()))


def confere_censo(registros, coletados, corrida_inteira, grupo=None):
    """(violacoes, mortas): listas de mensagens; vazias = censo fechado."""
    grupo = GRUPO_FREECAD if grupo is None else grupo
    subiram = arquivos_que_subiram(registros)
    violacoes = []
    for arq, item in subiram.items():
        if arq not in grupo:
            violacoes.append(
                "censo FreeCAD: %s subiu %d freecad fora do grupo serial "
                "(%s) - declare em tests/censo_freecad.GRUPO_FREECAD com o "
                "motivo medido" % (arq, item["processos"],
                                   ", ".join(item["testes"]) or "sem teste"))
    mortas = []
    if corrida_inteira:
        for arq in sorted(grupo):
            if arq in coletados and arq not in subiram:
                mortas.append(
                    "censo FreeCAD: %s esta no grupo serial e nao subiu "
                    "freecad na corrida inteira (isencao morta)" % arq)
    return violacoes, mortas
