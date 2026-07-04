# FreeCAD Modeling Workflow

How to turn approved inputs into FreeCAD geometry and deliverables using the
Robust MCP Bridge. Assumes the bridge is running (auto-starts a few seconds
after FreeCAD launch; XML-RPC on localhost:9875).

## Principles

- One parametric, re-runnable script per project: `projects/<slug>/work/build_<slug>.py`.
- The script closes and rebuilds its own document so re-runs are clean.
- All dimensions come from parameters at the top of the script (from the gate
  answers), never hard-coded mid-body.
- Section sizes are placeholders until Gate 5 (see `geometry-conventions.md`).

## Execution via the bridge

The MCP tool `execute_python` (or XML-RPC `execute`) runs code inside FreeCAD.
Set `_result_` to return data. Pattern to run the project script:

```python
# From an MCP client: call execute_python with the file contents, or:
code = open("projects/<slug>/work/build_<slug>.py", encoding="utf-8").read()
# the script ends with: _result_ = run()
```

The script's `run()` should return a small dict: object count, key heights, and
export paths. Guard long calls; a healthy bridge returns quickly. If `execute`
hangs while port 9875 is listening, fully restart FreeCAD (stale in-memory
bridge) — see the repo wiki open-threads.

## Helper: placeholder member

Create a member as a box of section (w x h) swept from p1 to p2, centred on the
axis:

```python
import math
import FreeCAD as App
import Part

def member(doc, p1, p2, section, name):
    v1, v2 = App.Vector(*p1), App.Vector(*p2)
    d = v2.sub(v1)
    L = d.Length
    if L < 1e-6:
        return None
    w, h = section
    box = Part.makeBox(L, w, h)
    box.translate(App.Vector(0, -w / 2.0, -h / 2.0))
    rot = App.Rotation(App.Vector(1, 0, 0), d)
    if abs(rot.Angle) > 1e-9:
        box.rotate(App.Vector(0, 0, 0), rot.Axis, math.degrees(rot.Angle))
    box.translate(v1)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box
    return obj
```

## Detailing helpers (Gates 7-9)

See `constructability-detailing.md` for the rules; these are the geometric
operations. All thresholds are asked with a suggestion, never hard-coded.

- Grout gap: build the whole steel frame with column bases at
  `z0 = GROUT_GAP` (ask; suggest 30 mm), not at 0. Z = 0 is top of concrete.
- Field splice: if a member length > `L_TRANSPORT_MAX` (ask; suggest 12 m),
  split it at a chosen station into `_SEG_A` / `_SEG_B` and add a thin
  `_SPLICE_01` plate placeholder straddling the cut.
- Drain/vent holes (galvanised tubes): boolean-cut small cylinders near each
  end, diametrically opposed:
  `tube.cut(Part.makeCylinder(r, t, pos, dir))`.
- Stiffener / gusset / base plate: model as thin `Part::Feature` plates sized to
  the node; name per `geometry-conventions.md`. Necessity comes from the
  engineer.
- Camber: do NOT bend geometry. Add an object property or a drawing note, e.g.
  `obj.addProperty("App::PropertyLength", "Camber"); obj.Camber = value`.

## Exports

Write into `projects/<slug>/exports/`:

- `freecad/<slug>.FCStd` via `doc.saveAs(...)`.
- `step/<slug>.step` via `Part.export(shapes, path)`.
- `img/<slug>_iso.png` via GUI: `viewIsometric()`, `ViewFit`, then
  `Gui.activeDocument().activeView().saveImage(path, 1600, 1000, "White")`.
- DXF/PDF/takeoff in Gate 6.

Always capture a screenshot after each gate so the user can verify visually
before approving.

## After each gate

- Update `context/decisions.md` (answers given) and `context/pending.md` (open).
- Update `notes/assumptions.md` for any assumed value.
- Keep the script runnable end-to-end so the model can be regenerated.
```
