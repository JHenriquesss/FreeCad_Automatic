"""Parametric conceptual model of a 20x10 m steel warehouse (galpao), v2.

Rebuilt to exercise the build-warehouse skill end to end (audit run). Applies the
skill's Gate 0-2 structural rules: grout gap, base plates + anchor rods, eave
struts, gable-end posts (oitao), sag rods (tirantes) closing at the ridge, flange
braces (mao-francesa) to the rafter bottom flange, purlins oriented open-face to
the eave, and tension-only cross bracing (thin rods).

CONCEPTUAL / DRAFTING ONLY. Section sizes are placeholders, not verified profiles.
Units: millimetres. Z = 0 is the top of concrete; steel rises by the grout gap.
"""

import math
import os

import FreeCAD as App
import Part

# ---- Parameters (mm) --------------------------------------------------------
LENGTH = 20000.0
SPAN = 10000.0
EAVE_H = 6000.0
SLOPE = 0.10
BAY = 5000.0
GROUT_GAP = 30.0            # skill: steel base above concrete (Z=0)

RIDGE_Y = SPAN / 2.0
RIDGE_H = EAVE_H + SLOPE * RIDGE_Y

Z0 = GROUT_GAP             # base of steel columns

SEC = {
    "COL": (200.0, 200.0),
    "RAFTER": (200.0, 150.0),
    "EAVE_STRUT": (150.0, 100.0),
    "RIDGE": (150.0, 100.0),
    "PURLIN": (150.0, 60.0),
    "GIRT": (150.0, 60.0),
    "GABLE_POST": (150.0, 150.0),
    "FLANGE_BRACE": (60.0, 60.0),
    "TIEROD": (25.0, 25.0),      # tension-only, thin
    "BRACE_ROD": (25.0, 25.0),   # tension-only cross bracing
}

EXPORT_DIR = "D:/dev/FreeCad_Automatic/projects/galpao/exports"


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


def plate(doc, center, wx, wy, wz, name):
    box = Part.makeBox(wx, wy, wz)
    box.translate(App.Vector(center[0] - wx / 2, center[1] - wy / 2, center[2] - wz / 2))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box
    return obj


def rafter_z(y):
    if y <= RIDGE_Y:
        return EAVE_H + SLOPE * y
    return EAVE_H + SLOPE * (SPAN - y)


def frame_axes():
    n = int(round(LENGTH / BAY))
    return [i * BAY for i in range(n + 1)]


def build(doc):
    axes = frame_axes()
    end_axes = (axes[0], axes[-1])

    # --- Primary frames: columns + rafters --------------------------------
    for i, x in enumerate(axes, start=1):
        tag = f"FRAME_{i:02d}"
        member(doc, (x, 0, Z0), (x, 0, EAVE_H), SEC["COL"], f"{tag}_COL_L")
        member(doc, (x, SPAN, Z0), (x, SPAN, EAVE_H), SEC["COL"], f"{tag}_COL_R")
        member(doc, (x, 0, EAVE_H), (x, RIDGE_Y, RIDGE_H), SEC["RAFTER"], f"{tag}_RAFTER_L")
        member(doc, (x, SPAN, EAVE_H), (x, RIDGE_Y, RIDGE_H), SEC["RAFTER"], f"{tag}_RAFTER_R")

    # --- Base plates + anchor rods (L-hook) per column --------------------
    for i, x in enumerate(axes, start=1):
        for yw, side in ((0, "L"), (SPAN, "R")):
            plate(doc, (x, yw, Z0 - 11), 350, 350, 22, f"BASEPLATE_{side}_{i:02d}")
            for dx in (-90, 90):
                # vertical rod embedded to -300, projecting +40 above base
                member(doc, (x + dx, yw, -300), (x + dx, yw, Z0 + 40),
                       (25, 25), f"ANCHOR_{side}_{i:02d}_{'a' if dx<0 else 'b'}")
                # 90-deg hook leg at bottom
                member(doc, (x + dx, yw, -300), (x + dx + 60, yw, -300),
                       (25, 25), f"ANCHORHOOK_{side}_{i:02d}_{'a' if dx<0 else 'b'}")
                plate(doc, (x + dx, yw, Z0 - 22), 80, 80, 10,
                      f"WASHER_{side}_{i:02d}_{'a' if dx<0 else 'b'}")

    # --- Eave struts + ridge beam (longitudinal, per bay) -----------------
    for b in range(len(axes) - 1):
        x0, x1 = axes[b], axes[b + 1]
        tag = f"BAY_{b + 1:02d}"
        member(doc, (x0, 0, EAVE_H), (x1, 0, EAVE_H), SEC["EAVE_STRUT"], f"{tag}_EAVESTRUT_L")
        member(doc, (x0, SPAN, EAVE_H), (x1, SPAN, EAVE_H), SEC["EAVE_STRUT"], f"{tag}_EAVESTRUT_R")
        member(doc, (x0, RIDGE_Y, RIDGE_H), (x1, RIDGE_Y, RIDGE_H), SEC["RIDGE"], f"{tag}_RIDGE")

    # --- Purlins (full length) + purlin Y set -----------------------------
    n_purlin = 3
    purlin_ys = []
    for k in range(1, n_purlin):
        yl = RIDGE_Y * k / n_purlin
        purlin_ys.append(yl)
        member(doc, (0, yl, rafter_z(yl)), (LENGTH, yl, rafter_z(yl)), SEC["PURLIN"], f"PURLIN_L_{k:02d}")
        yr = SPAN - RIDGE_Y * k / n_purlin
        purlin_ys.append(yr)
        member(doc, (0, yr, rafter_z(yr)), (LENGTH, yr, rafter_z(yr)), SEC["PURLIN"], f"PURLIN_R_{k:02d}")
    # eave + ridge purlins
    for y in (0.0, SPAN):
        member(doc, (0, y, EAVE_H), (LENGTH, y, EAVE_H), SEC["PURLIN"], f"PURLIN_EAVE_{'L' if y==0 else 'R'}")

    # --- Girts on side walls ----------------------------------------------
    for lvl, z in enumerate((2000.0 + Z0, 4000.0 + Z0), start=1):
        member(doc, (0, 0, z), (LENGTH, 0, z), SEC["GIRT"], f"GIRT_L_{lvl:02d}")
        member(doc, (0, SPAN, z), (LENGTH, SPAN, z), SEC["GIRT"], f"GIRT_R_{lvl:02d}")

    # --- Gable-end posts (oitao) on end frames ----------------------------
    for i, x in ((1, end_axes[0]), (len(axes), end_axes[1])):
        lbl = "FRONT" if x == 0 else "BACK"
        for p, yg in enumerate((SPAN / 3.0, 2 * SPAN / 3.0), start=1):
            member(doc, (x, yg, Z0), (x, yg, rafter_z(yg)), SEC["GABLE_POST"], f"GABLE_{lbl}_POST_{p:02d}")

    # --- Sag rods (tirantes): one line mid-bay, closing crossed at ridge ---
    for b in range(len(axes) - 1):
        xm = (axes[b] + axes[b + 1]) / 2.0
        tag = f"BAY_{b + 1:02d}"
        # left slope chain: eave->p1->p2->ridge
        left_chain = [0.0] + sorted([y for y in purlin_ys if y < RIDGE_Y]) + [RIDGE_Y]
        for s in range(len(left_chain) - 1):
            y_a, y_b = left_chain[s], left_chain[s + 1]
            member(doc, (xm, y_a, rafter_z(y_a)), (xm, y_b, rafter_z(y_b)), SEC["TIEROD"], f"TIEROD_L_{tag}_{s:02d}")
        right_chain = [SPAN] + sorted([y for y in purlin_ys if y > RIDGE_Y], reverse=True) + [RIDGE_Y]
        for s in range(len(right_chain) - 1):
            y_a, y_b = right_chain[s], right_chain[s + 1]
            member(doc, (xm, y_a, rafter_z(y_a)), (xm, y_b, rafter_z(y_b)), SEC["TIEROD"], f"TIEROD_R_{tag}_{s:02d}")
        # ridge crossed ties between the two mid-bay points (both reach ridge apex)
        member(doc, (xm, RIDGE_Y, RIDGE_H), (axes[b], RIDGE_Y, RIDGE_H), SEC["TIEROD"], f"TIEROD_RIDGE_{tag}_a")
        member(doc, (xm, RIDGE_Y, RIDGE_H), (axes[b + 1], RIDGE_Y, RIDGE_H), SEC["TIEROD"], f"TIEROD_RIDGE_{tag}_b")

    # --- Flange braces (mao-francesa): purlin -> rafter bottom flange ------
    for x in axes:
        for k, y in enumerate(sorted(set(purlin_ys)), start=1):
            zt = rafter_z(y)
            # short knee from purlin level down-inboard to rafter underside
            member(doc, (x, y, zt), (x, y + (150 if y < RIDGE_Y else -150), zt - 150),
                   SEC["FLANGE_BRACE"], f"FLANGEBRACE_{int(x)//1000:02d}_{k:02d}")

    # --- Tension-only cross bracing (thin rods), end bays ------------------
    end_bays = [(axes[0], axes[1]), (axes[-2], axes[-1])]
    for j, (x0, x1) in enumerate(end_bays, start=1):
        # roof plane crossed rods at eave level
        member(doc, (x0, 0, EAVE_H), (x1, SPAN, EAVE_H), SEC["BRACE_ROD"], f"BRACE_ROOF_{j:02d}_A")
        member(doc, (x1, 0, EAVE_H), (x0, SPAN, EAVE_H), SEC["BRACE_ROD"], f"BRACE_ROOF_{j:02d}_B")
        for yw, side in ((0, "L"), (SPAN, "R")):
            member(doc, (x0, yw, Z0), (x1, yw, EAVE_H), SEC["BRACE_ROD"], f"BRACE_WALL_{side}_{j:02d}_A")
            member(doc, (x1, yw, Z0), (x0, yw, EAVE_H), SEC["BRACE_ROD"], f"BRACE_WALL_{side}_{j:02d}_B")

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
    return {"objects": count, "frames": len(frame_axes()),
            "ridge_height_mm": RIDGE_H, "grout_gap_mm": GROUT_GAP,
            "fcstd": fcstd, "step": step}


_result_ = run()
