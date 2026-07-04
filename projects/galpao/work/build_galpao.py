"""Parametric conceptual model of a 20x10 m steel warehouse (galpao).

CONCEPTUAL / DRAFTING ONLY. Section sizes are placeholders for visualization,
not verified structural profiles. Units: millimetres.

Run inside FreeCAD (via the Robust MCP Bridge execute / execute_python, or from
the FreeCAD Python console). Produces a document, a placeholder frame model, and
exports FCStd + STEP into the project's exports folder.
"""

import math
import os

import FreeCAD as App
import Part

# ----------------------------------------------------------------------------
# Parameters (mm). Geometry confirmed with user; sections are placeholders.
# ----------------------------------------------------------------------------
LENGTH = 20000.0          # X, longitudinal
SPAN = 10000.0            # Y, transverse (vencido pelos porticos)
EAVE_H = 6000.0           # Z at eave / pe-direito
SLOPE = 0.10              # 10% roof slope, gable (duas aguas)
BAY = 5000.0             # frame spacing (assumption)

RIDGE_Y = SPAN / 2.0
RIDGE_H = EAVE_H + SLOPE * RIDGE_Y   # 6500 mm

# Placeholder section sizes (width x height, mm)
SEC = {
    "COL": (200.0, 200.0),
    "RAFTER": (200.0, 150.0),
    "EAVE": (150.0, 100.0),
    "RIDGE": (150.0, 100.0),
    "PURLIN": (150.0, 60.0),
    "GIRT": (150.0, 60.0),
    "BRACE": (80.0, 80.0),
}

EXPORT_DIR = "D:/dev/FreeCad_Automatic/projects/galpao/exports"


def member(doc, p1, p2, section, name):
    """Create a placeholder prismatic member (box) from p1 to p2.

    The box cross-section (w x h) is centred on the p1->p2 axis.
    """
    v1 = App.Vector(*p1)
    v2 = App.Vector(*p2)
    direction = v2.sub(v1)
    length = direction.Length
    if length < 1e-6:
        return None
    w, h = section
    box = Part.makeBox(length, w, h)
    box.translate(App.Vector(0, -w / 2.0, -h / 2.0))
    rot = App.Rotation(App.Vector(1, 0, 0), direction)
    if abs(rot.Angle) > 1e-9:
        box.rotate(App.Vector(0, 0, 0), rot.Axis, math.degrees(rot.Angle))
    box.translate(v1)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box
    return obj


def frame_axes():
    n = int(round(LENGTH / BAY))
    return [i * BAY for i in range(n + 1)]


def build(doc):
    axes = frame_axes()

    # Primary transverse frames: 2 columns + 2 rafters each
    for i, x in enumerate(axes, start=1):
        tag = f"FRAME_{i:02d}"
        member(doc, (x, 0, 0), (x, 0, EAVE_H), SEC["COL"], f"{tag}_COL_L")
        member(doc, (x, SPAN, 0), (x, SPAN, EAVE_H), SEC["COL"], f"{tag}_COL_R")
        member(doc, (x, 0, EAVE_H), (x, RIDGE_Y, RIDGE_H),
               SEC["RAFTER"], f"{tag}_RAFTER_L")
        member(doc, (x, SPAN, EAVE_H), (x, RIDGE_Y, RIDGE_H),
               SEC["RAFTER"], f"{tag}_RAFTER_R")

    # Longitudinal members: eave beams (both sides) + ridge beam, per bay
    for b in range(len(axes) - 1):
        x0, x1 = axes[b], axes[b + 1]
        tag = f"BAY_{b + 1:02d}"
        member(doc, (x0, 0, EAVE_H), (x1, 0, EAVE_H),
               SEC["EAVE"], f"{tag}_EAVE_L")
        member(doc, (x0, SPAN, EAVE_H), (x1, SPAN, EAVE_H),
               SEC["EAVE"], f"{tag}_EAVE_R")
        member(doc, (x0, RIDGE_Y, RIDGE_H), (x1, RIDGE_Y, RIDGE_H),
               SEC["RIDGE"], f"{tag}_RIDGE")

    # Purlins: run full length along X, on each roof slope
    n_purlin = 3  # spaces per slope
    for k in range(1, n_purlin):  # skip eave (0) and ridge handled separately
        # left slope: Y from 0 to RIDGE_Y
        yl = RIDGE_Y * k / n_purlin
        zl = EAVE_H + SLOPE * yl
        member(doc, (0, yl, zl), (LENGTH, yl, zl),
               SEC["PURLIN"], f"PURLIN_L_{k:02d}")
        # right slope: Y from SPAN to RIDGE_Y
        yr = SPAN - RIDGE_Y * k / n_purlin
        zr = EAVE_H + SLOPE * (SPAN - yr)
        member(doc, (0, yr, zr), (LENGTH, yr, zr),
               SEC["PURLIN"], f"PURLIN_R_{k:02d}")

    # Girts: side walls, horizontal along X, at two levels
    for lvl, z in enumerate((2000.0, 4000.0), start=1):
        member(doc, (0, 0, z), (LENGTH, 0, z), SEC["GIRT"], f"GIRT_L_{lvl:02d}")
        member(doc, (0, SPAN, z), (LENGTH, SPAN, z),
               SEC["GIRT"], f"GIRT_R_{lvl:02d}")

    # Bracing (placeholder) in end bays: horizontal roof plane X + wall X
    end_bays = [(axes[0], axes[1]), (axes[-2], axes[-1])]
    for j, (x0, x1) in enumerate(end_bays, start=1):
        # roof horizontal bracing (at eave level, crossed)
        member(doc, (x0, 0, EAVE_H), (x1, SPAN, EAVE_H),
               SEC["BRACE"], f"BRACE_ROOF_{j:02d}_A")
        member(doc, (x1, 0, EAVE_H), (x0, SPAN, EAVE_H),
               SEC["BRACE"], f"BRACE_ROOF_{j:02d}_B")
        # wall bracing both side walls (crossed)
        for yw, side in ((0, "L"), (SPAN, "R")):
            member(doc, (x0, yw, 0), (x1, yw, EAVE_H),
                   SEC["BRACE"], f"BRACE_WALL_{side}_{j:02d}_A")
            member(doc, (x1, yw, 0), (x0, yw, EAVE_H),
                   SEC["BRACE"], f"BRACE_WALL_{side}_{j:02d}_B")

    doc.recompute()
    return len(doc.Objects)


def export(doc):
    os.makedirs(f"{EXPORT_DIR}/freecad", exist_ok=True)
    os.makedirs(f"{EXPORT_DIR}/step", exist_ok=True)
    fcstd = f"{EXPORT_DIR}/freecad/galpao_20x10.FCStd"
    step = f"{EXPORT_DIR}/step/galpao_20x10.step"
    doc.saveAs(fcstd)
    shapes = [o for o in doc.Objects if hasattr(o, "Shape")]
    Part.export(shapes, step)
    return fcstd, step


def run():
    name = "galpao_20x10"
    for d in list(App.listDocuments().values()):
        if d.Name == name:
            App.closeDocument(name)
            break
    doc = App.newDocument(name)
    count = build(doc)
    fcstd, step = export(doc)
    total_len_m = sum(
        o.Shape.BoundBox.DiagonalLength for o in doc.Objects
    )  # rough only
    return {
        "objects": count,
        "frames": len(frame_axes()),
        "ridge_height_mm": RIDGE_H,
        "fcstd": fcstd,
        "step": step,
    }


if __name__ == "__main__" or True:
    _result_ = run()
