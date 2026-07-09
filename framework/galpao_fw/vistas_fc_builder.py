"""2D views builder - runs inside FreeCAD via MCP execute.
Set _result_ = design_dict before running this.
Creates Part/2D views with Draft::Text and exports DXF."""

import json, math, os
import FreeCAD as App
import Part
import Draft

d = _result_
ea = d.get("eave", 6000)
sp = d.get("span", 10000)
dc = d.get("col_d", 190)
cols = d.get("col_ys", [0, sp])
ck = d.get("resultados", {})
dxf_out = d.get("dxf_out", "")
XR = sp + 5000
# Create a separate document for 2D views
doc_name = "Vistas2D_" + d.get("slug", "galpao")
for dd in list(App.listDocuments().values()):
    if dd.Name == doc_name:
        App.closeDocument(doc_name)
doc = App.newDocument(doc_name)

def P(x, y):
    return (x, y, 0.0)

def rect(name, pts, color=None):
    o = doc.addObject("Part::Feature", name)
    o.Shape = Part.Face(Part.makePolygon([App.Vector(*p) for p in pts]))
    if color:
        o.ViewObject.ShapeColor = color
    return o

def line(name, p1, p2):
    o = doc.addObject("Part::Feature", name)
    o.Shape = Part.makeLine(App.Vector(*p1), App.Vector(*p2))
    return o

def text(name, txt, pos, size=6):
    try:
        o = Draft.make_text(str(txt), App.Vector(*pos))
        o.Label = name
        return o
    except Exception:
        return None

# Clear old 2D views
for o in list(doc.Objects):
    if o.Name.startswith("V2D_") or o.Name.startswith("TBL_"):
        doc.removeObject(o.Name)

# === L1: Portico columns ===
for j, yc in enumerate(cols):
    rect("V2D_COL_%02d" % j, [
        P(yc-dc/2, 0), P(yc+dc/2, 0),
        P(yc+dc/2, ea), P(yc-dc/2, ea)
    ], (0.3, 0.3, 0.8))

text("V2D_TIT", "PORTICO TRANSVERSAL", (sp/4, -1800, 0), 10)

# === Table at oy=-25000 ===
oy4 = -25000.0
text("TBL_TIT", "QUADRO DE VERIFICACOES", (XR, oy4 + 200, 0), 8)
line("TBL_HDR", P(XR, oy4), P(XR + 4500, oy4))

i = 0
for nome, val in ck.items():
    if val is None:
        continue
    ry = oy4 - 360 * (i + 1)
    line("TBL_LN_%d" % i, P(XR, ry), P(XR + 4500, ry))
    text("TBL_NM_%d" % i, nome, (XR + 50, ry + 30, 0), 5)
    text("TBL_VL_%d" % i, "%.2f" % val, (XR + 2500, ry + 30, 0), 5)
    i += 1

line("TBL_BOT", P(XR, oy4 - 360 * (i + 1)), P(XR + 4500, oy4 - 360 * (i + 1)))

doc.recompute()

# Export DXF
if dxf_out:
    os.makedirs(os.path.dirname(dxf_out), exist_ok=True)
    try:
        import importDXF
        importDXF.export([o for o in doc.Objects if hasattr(o, "Shape")], dxf_out)
        print("DXF exported OK via importDXF")
    except Exception as ex:
        try:
            import Draft
            Draft.export([o for o in doc.Objects if hasattr(o, "Shape")], dxf_out)
            print("DXF exported OK via Draft")
        except Exception as ex2:
            print("DXF export error:", ex, ex2)

print("2D views DONE")
_result_ = {"ok": True, "total": len(doc.Objects)}
