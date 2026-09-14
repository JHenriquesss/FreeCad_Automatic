#!/usr/bin/env python
"""D164 - a suite inteira em paralelo, com o FreeCAD em fila unica.

Medido (2026-09-13): a suite serial levava 47 min por corrida e cada goal
roda a suite ao fechar (5 goals ~ 4 h so de suite). O perfil da rodada real
do galpao (G102, 997 s) deu 937 s esperando o freecad.exe; o resto da suite
e Python de nucleo unico numa maquina de 8 nucleos. Paralelizar tudo mata o
processo por memoria (freecad.exe ~2 GB, maquina de 8 GB): os testes que
sobem freecad.exe/freecadcmd.exe ficam num grupo xdist unico
(`tests/conftest.py: GRUPO_FREECAD`), um por vez, e o resto se espalha.

O que este runner cobra alem do verde do pytest (cada um reprova a corrida):
  1. lista nominal: os arquivos coletados sao `find tests -name 'test_*.py'`
     (convencao 10) - nenhum arquivo fora;
  2. censo do FreeCAD nos dois sentidos: teste fora do grupo que sobe
     freecad reprova (vizinho de memoria nao declarado); arquivo do grupo
     que nao subiu freecad em corrida inteira reprova (isencao morta:
     serializa a toa e esconde o custo);
  3. o repositorio vivo sai byte a byte igual (`git status --porcelain`
     antes == depois; D81: teste que muta o repo nao roda em paralelo).

Uso (da pasta framework/galpao_fw, pelo interpretador de nome curto 8.3 -
o acento do caminho mata o execnet, D80):
    python tools/suite_paralela.py            # -n 3
    python tools/suite_paralela.py -n 2 [args extras do pytest]
Grava resumo em <saida>/resumo.json (saida: --saida DIR ou tmp).
"""
import argparse
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
TESTS = os.path.join(GALPAO, "tests")
sys.path.insert(0, TESTS)


def lista_nominal():
    """`find tests -name 'test_*.py'`, relativo a GALPAO, com barra /."""
    achados = []
    for raiz, _dirs, arquivos in os.walk(TESTS):
        for nome in arquivos:
            if nome.startswith("test_") and nome.endswith(".py"):
                rel = os.path.relpath(os.path.join(raiz, nome), GALPAO)
                achados.append(rel.replace("\\", "/"))
    return sorted(achados)


def _git_status():
    r = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                       cwd=GALPAO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return sorted(l for l in r.stdout.splitlines()
                  if "__pycache__" not in l and ".pytest_cache" not in l)


class _MEMSTAT(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def memoria_livre_mb():
    """RAM fisica livre da maquina (GlobalMemoryStatusEx); None fora do Windows."""
    if sys.platform != "win32":
        return None
    st = _MEMSTAT()
    st.dwLength = ctypes.sizeof(_MEMSTAT)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
        return None
    return st.ullAvailPhys / (1024.0 * 1024.0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=3)
    ap.add_argument("--saida", default=None)
    # Medido (D164): os testes pesados usam ~4 nucleos cada pelo pool do
    # OpenBLAS; com 2-3 workers a maquina de 8 nucleos satura e a corrida
    # paralela fica MAIS lenta que a serial. Com 1 thread por processo a
    # conta difere do padrao no ultimo ulp (predio: 148 linhas do resultado,
    # ~1e-13 relativo) - por isso e opcao declarada, nunca silenciosa: o
    # resumo grava o valor usado, e `pytest tests` serial (sem este runner)
    # segue sendo a referencia bit a bit. Com 1 thread: 3837 passed em 29 min
    # contra 48 min 33 s da serial; com o padrao, -n 2/-n 3 ficam mais lentos
    # que a serial.
    ap.add_argument("--blas", default="1",
                    help="threads do OpenBLAS por processo ('padrao' = nao mexe)")
    args, extras = ap.parse_known_args(argv)
    import censo_freecad as cf

    saida = args.saida or tempfile.mkdtemp(prefix="suite_paralela_")
    os.makedirs(saida, exist_ok=True)
    censo_dir = os.path.join(saida, "censo")
    os.makedirs(censo_dir, exist_ok=True)
    lista = lista_nominal()
    faltam_no_disco = [a for a in cf.GRUPO_FREECAD if a not in lista]

    git_antes = _git_status()
    minimo = {"mb": memoria_livre_mb()}
    parar = threading.Event()

    def _amostra():
        while not parar.wait(5.0):
            m = memoria_livre_mb()
            if m is not None and (minimo["mb"] is None or m < minimo["mb"]):
                minimo["mb"] = m

    fio = threading.Thread(target=_amostra, daemon=True)
    fio.start()
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env[cf.ENV_DIR] = censo_dir
    if args.blas != "padrao":
        for var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
            env[var] = str(int(args.blas))
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "-W", "ignore", "-n", str(args.n), "--dist", "loadgroup",
           "--durations=40"] + (extras or ["tests"])
    inicio = time.perf_counter()
    with open(os.path.join(saida, "pytest.txt"), "w", encoding="utf-8") as fh:
        rc = subprocess.call(cmd, cwd=GALPAO, env=env, stdout=fh,
                             stderr=subprocess.STDOUT)
    segundos = time.perf_counter() - inicio
    parar.set()
    fio.join()
    git_depois = _git_status()

    registros = cf.ler_registros(censo_dir)
    coletados = cf.ler_coletados(censo_dir)
    corrida_inteira = not extras
    quebras = []
    if corrida_inteira:
        fora = sorted(set(lista) - coletados)
        if fora:
            quebras.append("lista nominal: %d arquivo(s) de teste nao coletados: %s"
                           % (len(fora), fora))
    violacoes, mortas = cf.confere_censo(registros, coletados, corrida_inteira)
    quebras.extend(violacoes)
    quebras.extend(mortas)
    if faltam_no_disco:
        quebras.append("GRUPO_FREECAD cita arquivo inexistente: %s"
                       % faltam_no_disco)
    if git_antes != git_depois:
        quebras.append("repositorio vivo mudou durante a suite: antes=%r depois=%r"
                       % (sorted(set(git_antes) - set(git_depois)),
                          sorted(set(git_depois) - set(git_antes))))
    with open(os.path.join(saida, "pytest.txt"), encoding="utf-8") as fh:
        linhas = fh.read().splitlines()
    ultima = linhas[-1] if linhas else ""
    resumo = {"rc_pytest": rc, "segundos": round(segundos, 1), "n": args.n,
              "blas": args.blas,
              "arquivos_lista": len(lista), "arquivos_coletados": len(coletados),
              "ultima_linha": ultima,
              "memoria_livre_min_mb": (round(minimo["mb"], 0)
                                       if minimo["mb"] is not None else None),
              "freecad_por_arquivo": cf.arquivos_que_subiram(registros),
              "quebras": quebras}
    with open(os.path.join(saida, "resumo.json"), "w", encoding="utf-8") as fh:
        json.dump(resumo, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in resumo.items()
                      if k != "freecad_por_arquivo"}, ensure_ascii=False, indent=1))
    print("saida:", saida)
    return 1 if (rc != 0 or quebras) else 0


if __name__ == "__main__":
    sys.exit(main())
