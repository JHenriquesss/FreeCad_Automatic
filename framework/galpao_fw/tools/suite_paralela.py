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
import glob
import json
import os
import subprocess
import sys
import tempfile
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


def ambiente_suite(base, censo_dir, env_dir, blas):
    """Ambiente do pytest da corrida paralela.

    PYTHONUTF8=1 (D169/D170): nesta maquina (console cp850, repo em caminho
    com "Área") o spawn dos workers xdist quebrava com `UnicodeEncodeError
    ... surrogates not allowed`, e os 3 G21-C (pytest em subprocesso) caiam
    com saida vazia; so fechava verde com a variavel posta a mao no shell.
    Fica no runner para nao depender de quem roda. O repo abre arquivo com
    encoding explicito; a serial de referencia (sem o runner) segue sem ela.
    """
    env = dict(base, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    env[env_dir] = censo_dir
    if blas != "padrao":
        for var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
            env[var] = str(int(blas))
    return env


# G148 parte 1 - piso de memoria livre (derivado do medido; numero e motivo
# escritos aqui, fonte unica - a producao le desta constante, nunca de copia).
# Medido (fontes vivas, sem fechar os aplicativos do usuario):
# - menor minimo que PASSOU numa corrida inteira pelo runner: 159 MB (G142,
#   3869 passed); a serial de referencia foi morta pelo harness por memoria
#   baixa em 24 % (D172; a relancada passou com 1,1-1,6 GB livres) - ou seja,
#   159 MB ja e zona de morte, nao folga;
# - pico do G102-galpao: 1679,0 MB no congelado (G146: proc 207,1 + fc 1535,4,
#   teto 2500), maximo historico 2111,3 MB (G139: fc 1968,4); producao cheia
#   G147 2019-2041 MB; freecad.exe sozinho 1535-1968 MB numa maquina de 8 GB
#   (SO + fundo ~2 GB);
# - minimas normais recentes pelo runner: 258 MB (G147), 460 MB (G146),
#   308/416 MB (D172).
# Piso 200 MB: acima da zona onde a morte ja ocorreu (159), abaixo das minimas
# normais (258+), com folga para o amostrador de 5 s abortar antes de o harness
# matar. Cruzado o piso, o runner grava quais testes estavam em cada worker (o
# censo ja sabe: registros freecad-* + coletados-*) e sai como quebra nomeada -
# sem matar processo do usuario (so o proprio filho pytest e terminado).
PISO_MEMORIA_LIVRE_MB = 200


def veredito_piso_memoria(livre_mb, piso_mb=PISO_MEMORIA_LIVRE_MB):
    """Gap textual quando a memoria livre cruza o piso; None quando respira.

    Funcao pura para o vermelho por injecao (amostrador falso): livre abaixo do
    piso reprova nomeando piso + livre; livre no piso ou acima passa; livre None
    (fora do Windows ou amostrador cego) nao reprova - a ausencia se declara no
    resumo, nunca vira gap silencioso nem aprovacao inventada.
    """
    if livre_mb is None or piso_mb is None:
        return None
    try:
        livre = float(livre_mb)
        piso = float(piso_mb)
    except (TypeError, ValueError):
        return None
    if livre < piso:
        return ("piso de memoria livre (G148): %.0f MB livres < piso %.0f MB - "
                "suite abortada como quebra nomeada; testes por worker em "
                "resumo[testes_por_worker]; nenhum processo do usuario foi "
                "morto (so a arvore do proprio filho pytest, D176)"
                % (livre, piso))
    return None


def testes_por_worker(censo_dir):
    """{worker: {coletados: [...], freecad_testes: [...]}} do censo parcial.

    O censo ja sabe: cada worker escreve coletados-<worker>.json (arquivos da
    sua fatia) e freecad-<worker>.jsonl (primeiro avistamento de cada freecad
    descendente com o teste corrente). Em diretorio vazio ou ilegivel devolve
    {} - a ausencia se declara, nunca levanta.
    """
    saida = {}
    try:
        for caminho in sorted(glob.glob(os.path.join(censo_dir or "",
                                                     "coletados-*.json"))):
            worker = os.path.basename(caminho)[len("coletados-"):-len(".json")]
            try:
                with open(caminho, encoding="utf-8") as fh:
                    dados = json.load(fh)
            except Exception:
                continue
            item = saida.setdefault(worker, {"coletados": [], "freecad_testes": []})
            if isinstance(dados, list):
                item["coletados"] = sorted(str(a) for a in dados)
        for caminho in sorted(glob.glob(os.path.join(censo_dir or "",
                                                     "freecad-*.jsonl"))):
            try:
                with open(caminho, encoding="utf-8") as fh:
                    linhas = [l for l in fh if l.strip()]
            except Exception:
                continue
            for linha in linhas:
                try:
                    reg = json.loads(linha)
                except Exception:
                    continue
                worker = str(reg.get("worker") or "?")
                nodeid = str(reg.get("nodeid") or "")
                item = saida.setdefault(worker, {"coletados": [],
                                                 "freecad_testes": []})
                if nodeid and nodeid not in item["freecad_testes"]:
                    item["freecad_testes"].append(nodeid)
    except Exception:
        return {}
    return dict(sorted(saida.items()))


def arvore_descendentes(pares, raiz):
    """PIDs descendentes de `raiz` (sem ela) a partir de pares (pid, ppid).

    Funcao pura (D176): o piso do G148 terminava so o pytest pai e os workers
    xdist (e o freecad.exe de um teste do grupo) seguiam vivos ate o teste
    corrente acabar - medido: 4 processos vivos 10 s depois do aborto. Aqui
    so entra quem descende do proprio filho do runner; processo do usuario
    nunca descende dele. Ciclo de ppid (PID reusado) nao trava.
    """
    filhos = {}
    for pid, ppid in pares or ():
        try:
            filhos.setdefault(int(ppid), []).append(int(pid))
        except (TypeError, ValueError):
            continue
    vistos, fila = [], [int(raiz)]
    while fila:
        atual = fila.pop(0)
        for f in filhos.get(atual, []):
            if f != int(raiz) and f not in vistos:
                vistos.append(f)
                fila.append(f)
    return sorted(vistos)


def _pares_processos():
    """[(pid, ppid)] da maquina via CIM; [] fora do Windows ou se falhar."""
    if sys.platform != "win32":
        return []
    cmd = ("Get-CimInstance Win32_Process | Select-Object ProcessId,"
           "ParentProcessId | ConvertTo-Json -Compress")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                             capture_output=True, encoding="utf-8",
                             errors="replace", timeout=60).stdout
        dados = json.loads(out or "[]")
    except Exception:
        return []
    if isinstance(dados, dict):
        dados = [dados]
    return [(d.get("ProcessId"), d.get("ParentProcessId")) for d in dados
            if isinstance(d, dict)]


def processo_vivo(pid):
    """True se o PID existe e nao saiu (OpenProcess + GetExitCodeProcess)."""
    if sys.platform != "win32":
        return False
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        codigo = ctypes.c_ulong()
        if not k32.GetExitCodeProcess(h, ctypes.byref(codigo)):
            return False
        return codigo.value == 259                   # STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


def terminar_arvore(proc, _pares_fn=None, espera_s=20.0):
    """Termina o filho pytest E os seus descendentes; nunca outro processo.

    Snapshot da arvore ANTES de terminar o pai (depois o ppid orfao ainda
    aponta para ele, mas o PID pode ser reusado). Cada descendente vivo leva
    taskkill /F no PID dele (sem /T: a arvore ja foi resolvida aqui) e, se
    resistir, WMI Terminate (freecad.exe travado, memoria
    freecad-zumbis-wmi-kill). Devolve (terminados, sobreviventes).
    """
    pares = (_pares_fn or _pares_processos)()
    alvos = arvore_descendentes(pares, proc.pid)
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=30)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    for pid in alvos:
        if not processo_vivo(pid):
            continue
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=15)
        except Exception:
            pass
    limite = time.time() + float(espera_s)
    while time.time() < limite and any(processo_vivo(p) for p in alvos):
        time.sleep(0.5)
    for pid in [p for p in alvos if processo_vivo(p)]:
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$p=Get-CimInstance Win32_Process -Filter \"ProcessId=%d\";"
                 "if($p){Invoke-CimMethod -InputObject $p -MethodName Terminate"
                 "|Out-Null}" % pid],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        except Exception:
            pass
    sobreviventes = [p for p in alvos if processo_vivo(p)]
    return alvos, sobreviventes


def main(argv=None, _amostra_fn=None, _piso_mb=None, _intervalo_s=5.0):
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
    # G148: amostrador injetavel (o teste passa um falso) e piso lido da
    # producao (default = PISO_MEMORIA_LIVRE_MB, nunca copia). Fora do Windows
    # o amostrador devolve None e o piso nao dispara (ausencia declarada).
    amostrador = _amostra_fn or memoria_livre_mb
    piso = PISO_MEMORIA_LIVRE_MB if _piso_mb is None else _piso_mb
    try:
        intervalo = float(_intervalo_s)
    except (TypeError, ValueError):
        intervalo = 5.0
    if intervalo <= 0:
        intervalo = 5.0
    try:
        primeira = amostrador()
    except Exception:
        primeira = None
    minimo = {"mb": primeira}
    brecha = {"livre": None}

    env = ambiente_suite(os.environ, censo_dir, cf.ENV_DIR, args.blas)
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "-W", "ignore", "-n", str(args.n), "--dist", "loadgroup",
           "--durations=40"] + (extras or ["tests"])
    inicio = time.perf_counter()
    with open(os.path.join(saida, "pytest.txt"), "w", encoding="utf-8") as fh:
        # Popen (nao call): cruzado o piso, o runner termina SO a arvore do
        # proprio filho pytest (pai + workers xdist + freecad deles, D176) -
        # nenhum processo do usuario e tocado (taskkill so por PID resolvido
        # como descendente).
        proc = subprocess.Popen(cmd, cwd=GALPAO, env=env, stdout=fh,
                                stderr=subprocess.STDOUT)
        arvore = {"terminados": [], "sobreviventes": []}
        while proc.poll() is None:
            time.sleep(min(intervalo, 1.0))
            try:
                m = amostrador()
            except Exception:
                m = None
            if m is not None and (minimo["mb"] is None or m < minimo["mb"]):
                minimo["mb"] = m
            if brecha["livre"] is None and veredito_piso_memoria(m, piso) is not None:
                brecha["livre"] = m
                break
        if brecha["livre"] is not None:
            terminados, sobreviventes = terminar_arvore(proc)
            arvore = {"terminados": terminados, "sobreviventes": sobreviventes}
        else:
            proc.wait()
        rc = proc.returncode if proc.returncode is not None else 1
    segundos = time.perf_counter() - inicio
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
    if brecha["livre"] is not None:
        quebras.append(veredito_piso_memoria(brecha["livre"], piso))
        if arvore["sobreviventes"]:
            quebras.append("piso de memoria livre (D176): %d descendente(s) do "
                           "filho pytest sobreviveram ao aborto: %s"
                           % (len(arvore["sobreviventes"]),
                              arvore["sobreviventes"]))
    por_worker = testes_por_worker(censo_dir) if brecha["livre"] is not None else {}
    with open(os.path.join(saida, "pytest.txt"), encoding="utf-8") as fh:
        linhas = fh.read().splitlines()
    ultima = linhas[-1] if linhas else ""
    resumo = {"rc_pytest": rc, "segundos": round(segundos, 1), "n": args.n,
              "blas": args.blas,
              "arquivos_lista": len(lista), "arquivos_coletados": len(coletados),
              "ultima_linha": ultima,
              "memoria_livre_min_mb": (round(minimo["mb"], 0)
                                       if minimo["mb"] is not None else None),
              "piso_memoria_livre_mb": piso,
              "freecad_por_arquivo": cf.arquivos_que_subiram(registros),
              "testes_por_worker": por_worker,
              "descendentes_terminados": arvore["terminados"],
              "descendentes_sobreviventes": arvore["sobreviventes"],
              "quebras": quebras}
    with open(os.path.join(saida, "resumo.json"), "w", encoding="utf-8") as fh:
        json.dump(resumo, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in resumo.items()
                      if k not in ("freecad_por_arquivo", "testes_por_worker")},
                     ensure_ascii=False, indent=1))
    print("saida:", saida)
    return 1 if (rc != 0 or quebras) else 0


if __name__ == "__main__":
    sys.exit(main())
