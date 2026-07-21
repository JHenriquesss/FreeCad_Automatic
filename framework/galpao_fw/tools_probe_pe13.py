# Harness RAPIDO do PE13: roda dentro do freecad.exe (unico lugar onde a cena
# grafica existe e getEdgeByIndex popula), gera SO o detalhe do clipe de girt e
# mede as arestas do corte para VARIAS combinacoes numa unica execucao.
# Sem isto cada experimento custava um executivo completo (12-20 min).
import json
import os
import sys

GAL = os.path.dirname(os.path.abspath(__file__))       # <repo>/framework/galpao_fw
BASE = os.path.dirname(os.path.dirname(GAL))
sys.path.insert(0, GAL)

import techdraw_exec as TD
import projeto_spec as PS

FCSTD = os.path.join(BASE, "projects", "amostra_engenheiro", "saida",
                     "freecad", "amostra_engenheiro.FCStd")
OUT = os.path.join(os.environ.get("TEMP", "."), "probe_pe13.json")

with open(os.path.join(GAL, "spec_amostra_engenheiro.json"), encoding="utf-8") as fh:
    spec = json.load(fh)
cfg = TD.config_de_spec(spec, FCSTD, os.path.dirname(FCSTD))

# combinacoes a testar: (rotulo, sec_normal, frac_offset)
#   sec_normal: eixo da normal do corte (None = perpendicular a elevacao)
#   frac_offset: deslocamento da origem ao longo da normal, em fracao da peca
COMBOS = [
    ("base_nY_0",   None, 0.0),      # comportamento historico
    ("nX_0",        "x",  0.0),      # transversal a girt (o que esta no tree)
    ("nY_0",        "y",  0.0),
    ("nZ_0",        "z",  0.0),
]

script = (
    "# -*- coding: utf-8 -*-\n"
    "_CFG_ = %r\n" % (TD._para_nativo(cfg),) +
    "_COMBOS_ = %r\n" % (COMBOS,) +
    "_OUT_ = %r\n" % (OUT,) +
    TD.codigo_fonte() + r'''

def _probe():
    import json, time, traceback
    import FreeCAD as App
    import FreeCADGui as Gui
    res = {}
    try:
        doc = App.openDocument(_CFG_["fcstd"])
        todos = [o for o in doc.Objects
                 if o.TypeId == "Part::Feature" and hasattr(o, "Shape")
                 and not o.Shape.isNull()]
        for rot, snorm, frac in _COMBOS_:
            try:
                pg, _cts = _detalhe_ligacao(
                    doc, _CFG_, todos, "CLIPE_GIRT", "PROBE", "PROBE_%s" % rot,
                    400, "x", "y", "PG_%s" % rot, None, sec_normal=snorm)
                if pg is None:
                    res[rot] = "sem pagina"
                    continue
                try:
                    pg.ViewObject.doubleClicked()
                except Exception:
                    pass
                Gui.updateGui(); time.sleep(1.0); Gui.updateGui()
                doc.recompute(); Gui.updateGui()
                sec = [v for v in doc.Objects
                       if v.Name.startswith("VLIG_SEC") and "PROBE_%s" % rot in v.Name]
                if not sec:
                    sec = [v for v in doc.Objects if v.Name.startswith("VLIG_SEC")]
                res[rot] = {"sec_edges": _n_edges(sec[-1]) if sec else -1}
            except Exception:
                res[rot] = "erro: " + traceback.format_exc()[-300:]
    except Exception:
        res["_fatal"] = traceback.format_exc()[-500:]
    try:
        with open(_OUT_, "w", encoding="utf-8") as f:
            json.dump(res, f, default=str, indent=1)
    except Exception:
        pass
    try:
        from PySide import QtCore
        for d in list(App.listDocuments().values()):
            App.closeDocument(d.Name)
        QtCore.QTimer.singleShot(200, Gui.getMainWindow().close)
    except Exception:
        pass

from PySide import QtCore
QtCore.QTimer.singleShot(1500, _probe)
''')

import tempfile
f = tempfile.NamedTemporaryFile("w", suffix="_probe.py", delete=False, encoding="utf-8")
f.write(script)
f.close()
print("script:", f.name)
print("saida :", OUT)
if os.path.exists(OUT):
    os.remove(OUT)

import subprocess
exe = os.environ.get("FREECAD_EXE",
                     r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe")
p = subprocess.Popen([exe, f.name])
print("freecad pid:", p.pid, flush=True)
p.wait(timeout=900)
print("saiu com", p.returncode)
if os.path.exists(OUT):
    print(open(OUT, encoding="utf-8").read())
else:
    print("SEM SAIDA")
