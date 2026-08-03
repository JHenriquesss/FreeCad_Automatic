#!/usr/bin/env python
# ============================================================================
# run_tests.py - roda a suite NON-BUILD de forma CONFIAVEL e reproduzivel.
#
# Problema: a suite non-build tem ~1281 testes; ~28 deles (test_fase*, que rodam
# o rodar_projeto.calcular completo, + test_crashes_wiki07) levam ~20 s CADA ->
# a metade "a-l" leva ~12 min sequencial e estoura o limite de foreground do
# ambiente (~10 min). Antes: rodar "tocados + m-z" na mao.
#
# Solucao PRIMARIA: pytest-xdist (-n auto). A suite E xdist-safe (verificado S40:
# 1281 passed com -n auto). Em 8 nucleos: ~5 min, UM comando, sob o limite.
# FALLBACK (sem xdist): 2 lanes sequenciais isolando os pesados (test_fase*) dos
# rapidos, para que a lane rapida sempre feche sob o limite.
#
# Uso:  python tools/run_tests.py [args extras p/ o pytest]
#       python tools/run_tests.py -x -k terca          # passa args adiante
# ============================================================================
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)                       # framework/galpao_fw
BASE = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-m", "not build"]
EXTRA = sys.argv[1:]

# arquivos PESADOS (isolados no fallback): end-to-end que rodam o pipeline completo
PESADOS_GLOB = "*/test_fase*"
PESADOS_ALVO = ["tests/test_fase*.py", "tests/test_crashes_wiki07.py"]


def _run(args):
    print("+ pytest", " ".join(args), flush=True)
    return subprocess.call(BASE + args, cwd=GALPAO)


def main():
    if importlib.util.find_spec("xdist") is not None:
        # caminho rapido: paraleliza a suite inteira num comando
        return _run(["-n", "auto", "tests/"] + EXTRA)

    # fallback sequencial (sem xdist): rapidos primeiro, pesados depois
    print("[run_tests] pytest-xdist ausente -> lanes sequenciais "
          "(instale com: pip install -r requirements-dev.txt)", flush=True)
    rc = _run(["tests/", "--ignore-glob=" + PESADOS_GLOB,
               "-k", "not crashes_wiki07"] + EXTRA)          # lane 1: rapidos
    rc |= _run(PESADOS_ALVO + EXTRA)                         # lane 2: pesados
    return rc


if __name__ == "__main__":
    sys.exit(main())
