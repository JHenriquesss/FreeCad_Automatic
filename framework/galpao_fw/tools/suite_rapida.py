#!/usr/bin/env python
"""Fase 1 do plano de 2026-10-08 - a camada RAPIDA da suite.

Roda `pytest -m "not slow"`: motores e modelo, sem FreeCAD e sem os arquivos
medidos como lentos (`tests/camada_lenta.py`). E' a suite de toda alteracao;
a suite inteira (`tools/suite_paralela.py`) continua sendo a de antes de
entrega.

Alem do verde do pytest, cobra duas coisas (cada uma reprova a corrida):
  1. ORCAMENTO de parede: a camada rapida que passa de `--orcamento` segundos
     deixou de ser rapida (o plano pede "poucos minutos");
  2. nenhum arquivo da camada rapida soma `FOLGA` x `CORTE_S` ou mais: quem
     dobrou o corte tem de entrar em `LENTOS_MEDIDOS` com o tempo medido. A
     folga existe porque o tempo de um arquivo varia com a carga da maquina
     (medido em 2026-10-08: cinco arquivos de 6 a 9 s numa corrida somaram de
     11 a 14 s na seguinte); sem ela o runner reprovava por ruido.

Uso (da pasta framework/galpao_fw, pelo interpretador de nome curto 8.3 - o
acento do caminho mata o execnet):
    python tools/suite_rapida.py            # -n 2
    python tools/suite_rapida.py -n 3 [args extras do pytest]
"""
import argparse
import collections
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
ORCAMENTO_S = 600.0
FOLGA = 2.0


def _camada():
    spec = importlib.util.spec_from_file_location(
        "_camada_lenta", os.path.join(GALPAO, "tests", "camada_lenta.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tempos_por_arquivo(junit):
    soma = collections.defaultdict(float)
    for caso in ET.parse(junit).getroot().iter("testcase"):
        soma[caso.get("classname").replace(".", "/") + ".py"] += float(caso.get("time") or 0)
    return dict(soma)


def confere(tempos, parede_s, corte_s, orcamento_s, folga=FOLGA):
    """Lista de quebras da camada rapida (vazia = verde)."""
    limite = corte_s * folga
    quebras = []
    if parede_s > orcamento_s:
        quebras.append("camada rapida levou %.0f s de parede (orcamento %.0f s)"
                       % (parede_s, orcamento_s))
    for arq, t in sorted(tempos.items(), key=lambda x: -x[1]):
        if t >= limite:
            quebras.append("%s somou %.1f s (limite %.1f s): declarar em "
                           "tests/camada_lenta.py LENTOS_MEDIDOS" % (arq, t, limite))
    return quebras


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=2)
    ap.add_argument("--orcamento", type=float, default=ORCAMENTO_S)
    args, extras = ap.parse_known_args(argv)
    junit = os.path.join(tempfile.mkdtemp(prefix="suite_rapida_"), "junit.xml")
    amb = dict(os.environ, OPENBLAS_NUM_THREADS="1", PYTHONUTF8="1")
    cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q",
           "-m", "not slow", "-n", str(args.n), "--dist", "loadgroup",
           "--junitxml=" + junit, "tests/"] + extras
    t0 = time.time()
    rc = subprocess.call(cmd, cwd=GALPAO, env=amb)
    parede = time.time() - t0
    quebras = []
    if os.path.exists(junit):
        tempos = tempos_por_arquivo(junit)
        quebras = confere(tempos, parede, _camada().CORTE_S, args.orcamento)
        print("camada rapida: %d arquivos, %.0f s somados, %.0f s de parede (-n %d)"
              % (len(tempos), sum(tempos.values()), parede, args.n))
    for q in quebras:
        print("QUEBRA:", q)
    return 1 if (rc or quebras) else 0


if __name__ == "__main__":
    sys.exit(main())
