# ============================================================================
# test_fase5_corte_seccionado.py - RED tests da Fase 5.
# Corte SECCIONADO real (DrawViewSection hachurado) nos detalhes de ligacao. O
# blocker historico (T6: "failed to create section CS" headless) foi resolvido no
# FreeCAD 1.1 - a secao constroi headless. Testa via freecadcmd (TechDraw so roda
# dentro do FreeCAD): monta chapa+parafuso, uma vista base, chama _secao_ligacao
# e exige uma DrawViewSection com arestas reais (>0) e superficie cortada hachurada.
# ============================================================================
import os
import sys
import json
import tempfile
import subprocess
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)

FREECADCMD = os.environ.get(
    "FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")

_BOOT = r'''
import sys, json
sys.path.insert(0, r"%s")
import FreeCAD as App, Part
import techdraw_exec as TD
doc = App.newDocument("sec_test")
# chapa (t=12) + 2 parafusos atravessando -> algo para o corte revelar
plate = doc.addObject("Part::Feature", "CHAPA")
plate.Shape = Part.makeBox(200, 12, 200, App.Vector(-100, -6, -100))
b1 = doc.addObject("Part::Feature", "PARAF_1")
b1.Shape = Part.makeCylinder(10, 80, App.Vector(-40, -40, 40), App.Vector(0, 1, 0))
b2 = doc.addObject("Part::Feature", "PARAF_2")
b2.Shape = Part.makeCylinder(10, 80, App.Vector(40, -40, -40), App.Vector(0, 1, 0))
doc.recompute()
comp = doc.addObject("Part::Feature", "CONEX_TESTE_CROP")
comp.Shape = Part.makeCompound([plate.Shape, b1.Shape, b2.Shape])
doc.recompute()
page = doc.addObject("TechDraw::DrawPage", "P")
tmpl = doc.addObject("TechDraw::DrawSVGTemplate", "T"); page.Template = tmpl
elev = TD._vista(doc, page, "VLIG_ELEV_TESTE", [comp], (-1, 0, 0), (0, -1, 0), 1.0, 200, 200)
doc.recompute()
sec = TD._secao_ligacao(doc, page, "TESTE", comp, elev, (0, -1, 0), 1.0, 400, 200)
doc.recompute()
res = {"tem_secao": sec is not None,
       "edges": TD._n_edges(sec) if sec is not None else 0,
       "nome": sec.Name if sec is not None else None,
       "hachura": getattr(sec, "CutSurfaceDisplay", None) if sec is not None else None}
open(r"%s", "w", encoding="utf-8").write(json.dumps(res, default=str))
'''


@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECADCMD), reason="freecadcmd ausente")
def test_secao_ligacao_gera_corte_com_arestas(tmp_path):
    stf = os.path.join(str(tmp_path), "sec.json").replace("\\", "/")
    boot = _BOOT % (GALPAO.replace("\\", "/"), stf)
    bp = tempfile.NamedTemporaryFile(mode="w", suffix="_sec.py", delete=False,
                                     encoding="utf-8")
    bp.write(boot); bp.close()
    subprocess.run([FREECADCMD, bp.name], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=300)
    os.unlink(bp.name)
    assert os.path.exists(stf), "helper _secao_ligacao nao rodou (ausente?)"
    r = json.load(open(stf, encoding="utf-8"))
    assert r["tem_secao"], "nao gerou DrawViewSection"
    assert r["nome"] and r["nome"].startswith("VLIG_SEC"), "nome deve ser VLIG_SEC_*"
    assert r["edges"] > 0, "secao sem arestas (corte vazio - mne-1)"
