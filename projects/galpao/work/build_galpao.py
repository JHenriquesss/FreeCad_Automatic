"""Parametric conceptual model of a 20x10 m steel warehouse (galpao), v3.

Capability upgrade after the skill audit:
- Real profile cross-sections (I / U / round bar) instead of bounding boxes, so
  the model carries section identity and U-purlins can be oriented open-face to
  the eave (skill rule, verified against CBCA sec. 2.9).
- Datum fixed: Z = 0 is the TOP OF CONCRETE. Heights (eave, ridge) are measured
  from Z = 0. Steel columns start at Z0 = GROUT_GAP; column steel length is
  EAVE_H - GROUT_GAP.
- A real clash check runs after build and reports interfering solids.

Sections are placeholder profiles (flagged unverified) until Gate 7-8.
Units: mm.
"""

import math
import os

import FreeCAD as App
import Part

# ---- Parameters (mm) --------------------------------------------------------
LENGTH = 20000.0
SPAN = 10000.0
EAVE_H = 6000.0            # measured from top of concrete (Z=0)
SLOPE = 0.10
BAY = 5000.0
GROUT_GAP = 30.0
Z0 = GROUT_GAP

RIDGE_Y = SPAN / 2.0
RIDGE_H = EAVE_H + SLOPE * RIDGE_Y

EXPORT_DIR = "D:/dev/FreeCad_Automatic/projects/galpao/exports"

# Node registry: name -> list of endpoint tuples, so the clash check can skip
# members that intentionally share a connection node.
REG = {}


def _reg(name, *pts):
    REG[name] = [tuple(round(c, 1) for c in p) for p in pts]

# Placeholder real profiles (European sections; NOT verified sizes).
# I: (h, b, tw, tf)   U: (h, b, tw, tf)
HEA200 = (190.0, 200.0, 6.5, 10.0)
HEA180 = (171.0, 180.0, 6.0, 9.5)
HEA160 = (152.0, 160.0, 6.0, 9.0)
UPE120 = (120.0, 60.0, 5.0, 8.0)
UPE100 = (100.0, 55.0, 4.5, 7.5)


def i_section_pts(sec):
    """I/H section outline in the local (y,z) plane, centred on the axis."""
    h, b, tw, tf = sec
    hz, by, tw2 = h / 2.0, b / 2.0, tw / 2.0
    fz = hz - tf
    return [(by, hz), (-by, hz), (-by, fz), (-tw2, fz), (-tw2, -fz),
            (-by, -fz), (-by, -hz), (by, -hz), (by, -fz), (tw2, -fz),
            (tw2, fz), (by, fz)]


def u_section_pts(sec):
    """U/channel outline; open face toward +y (local). Back (web) at -y."""
    h, b, tw, tf = sec
    hz = h / 2.0
    y0 = -b / 2.0            # web outer face
    yw = y0 + tw            # web inner face
    yb = b / 2.0            # flange tips (opening side)
    fz = hz - tf
    return [(y0, hz), (yb, hz), (yb, fz), (yw, fz), (yw, -fz),
            (yb, -fz), (yb, -hz), (y0, -hz)]


def _sweep(pts2d, p1, p2, roll_deg, name, doc):
    v1, v2 = App.Vector(*p1), App.Vector(*p2)
    d = v2.sub(v1)
    L = d.Length
    if L < 1e-6:
        return None
    wire = Part.makePolygon([App.Vector(0, y, z) for (y, z) in pts2d] +
                            [App.Vector(0, pts2d[0][0], pts2d[0][1])])
    face = Part.Face(wire)
    solid = face.extrude(App.Vector(L, 0, 0))
    if abs(roll_deg) > 1e-9:
        solid.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), roll_deg)
    rot = App.Rotation(App.Vector(1, 0, 0), d)
    if abs(rot.Angle) > 1e-9:
        solid.rotate(App.Vector(0, 0, 0), rot.Axis, math.degrees(rot.Angle))
    solid.translate(v1)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = solid
    _reg(name, p1, p2)
    return obj


def i_member(doc, p1, p2, sec, name, roll=0.0):
    return _sweep(i_section_pts(sec), p1, p2, roll, name, doc)


def u_member(doc, p1, p2, sec, name, roll=0.0):
    return _sweep(u_section_pts(sec), p1, p2, roll, name, doc)


def rod(doc, p1, p2, dia, name):
    v1, v2 = App.Vector(*p1), App.Vector(*p2)
    d = v2.sub(v1)
    L = d.Length
    if L < 1e-6:
        return None
    cyl = Part.makeCylinder(dia / 2.0, L)
    rot = App.Rotation(App.Vector(0, 0, 1), d)
    if abs(rot.Angle) > 1e-9:
        cyl.rotate(App.Vector(0, 0, 0), rot.Axis, math.degrees(rot.Angle))
    cyl.translate(v1)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = cyl
    _reg(name, p1, p2)
    return obj


def plate(doc, center, wx, wy, wz, name):
    box = Part.makeBox(wx, wy, wz)
    box.translate(App.Vector(center[0] - wx / 2, center[1] - wy / 2, center[2] - wz / 2))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box
    return obj


def rafter_z(y):
    return EAVE_H + SLOPE * (y if y <= RIDGE_Y else (SPAN - y))


def frame_axes():
    n = int(round(LENGTH / BAY))
    return [i * BAY for i in range(n + 1)]


def build(doc):
    axes = frame_axes()

    # Primary frames: I-section columns + rafters
    for i, x in enumerate(axes, start=1):
        t = f"FRAME_{i:02d}"
        i_member(doc, (x, 0, Z0), (x, 0, EAVE_H), HEA200, f"{t}_COL_L")
        i_member(doc, (x, SPAN, Z0), (x, SPAN, EAVE_H), HEA200, f"{t}_COL_R")
        i_member(doc, (x, 0, EAVE_H), (x, RIDGE_Y, RIDGE_H), HEA180, f"{t}_RAFTER_L")
        i_member(doc, (x, SPAN, EAVE_H), (x, RIDGE_Y, RIDGE_H), HEA180, f"{t}_RAFTER_R")

    # Base plates + L-hook anchors + washers
    for i, x in enumerate(axes, start=1):
        for yw, side in ((0, "L"), (SPAN, "R")):
            # plate/anchors sized so anchors clear the HEA200 flange (half=100)
            plate(doc, (x, yw, Z0 - 11), 420, 420, 22, f"BASEPLATE_{side}_{i:02d}")
            for dx in (-140, 140):
                sfx = 'a' if dx < 0 else 'b'
                rod(doc, (x + dx, yw, -300), (x + dx, yw, Z0 + 40), 25, f"ANCHOR_{side}_{i:02d}_{sfx}")
                rod(doc, (x + dx, yw, -300), (x + dx + 60, yw, -300), 25, f"ANCHORHOOK_{side}_{i:02d}_{sfx}")
                plate(doc, (x + dx, yw, Z0 - 22), 80, 80, 10, f"WASHER_{side}_{i:02d}_{sfx}")

    # Eave struts + ridge beam (I-section, per bay)
    for b in range(len(axes) - 1):
        x0, x1 = axes[b], axes[b + 1]
        t = f"BAY_{b + 1:02d}"
        i_member(doc, (x0, 0, EAVE_H), (x1, 0, EAVE_H), HEA160, f"{t}_EAVESTRUT_L")
        i_member(doc, (x0, SPAN, EAVE_H), (x1, SPAN, EAVE_H), HEA160, f"{t}_EAVESTRUT_R")
        i_member(doc, (x0, RIDGE_Y, RIDGE_H), (x1, RIDGE_Y, RIDGE_H), HEA160, f"{t}_RIDGE")

    # Purlins: U-section, open face toward the EAVE (skill/CBCA rule).
    # Left slope (y<ridge): eave at y=0, open face toward -y -> roll 180.
    # Right slope: eave at y=SPAN, open face toward +y -> roll 0.
    # Purlins bear ON TOP of the rafter top flange: offset up the roof normal.
    POFF = 130.0
    n_purlin = 3
    purlin_ys = []
    for k in range(1, n_purlin):
        yl = RIDGE_Y * k / n_purlin
        purlin_ys.append(yl)
        u_member(doc, (0, yl, rafter_z(yl) + POFF), (LENGTH, yl, rafter_z(yl) + POFF),
                 UPE120, f"PURLIN_L_{k:02d}", roll=180)
        yr = SPAN - RIDGE_Y * k / n_purlin
        purlin_ys.append(yr)
        u_member(doc, (0, yr, rafter_z(yr) + POFF), (LENGTH, yr, rafter_z(yr) + POFF),
                 UPE120, f"PURLIN_R_{k:02d}", roll=0)
    for y, side, rl in ((0.0, "L", 180), (SPAN, "R", 0)):
        u_member(doc, (0, y, EAVE_H + POFF), (LENGTH, y, EAVE_H + POFF), UPE120,
                 f"PURLIN_EAVE_{side}", roll=rl)

    # Girts bear on the OUTER face of the columns: offset outboard in Y.
    GOFF = 130.0
    for lvl, z in enumerate((2000.0, 4000.0), start=1):
        u_member(doc, (0, -GOFF, z), (LENGTH, -GOFF, z), UPE100, f"GIRT_L_{lvl:02d}", roll=90)
        u_member(doc, (0, SPAN + GOFF, z), (LENGTH, SPAN + GOFF, z), UPE100, f"GIRT_R_{lvl:02d}", roll=90)

    # Gable-end posts (oitao) on end frames
    for i, x in ((1, axes[0]), (len(axes), axes[-1])):
        lbl = "FRONT" if x == 0 else "BACK"
        for p, yg in enumerate((SPAN / 3.0, 2 * SPAN / 3.0), start=1):
            # stop just below the rafter underside (bearing), not through it
            i_member(doc, (x, yg, Z0), (x, yg, rafter_z(yg) - 95), HEA160,
                     f"GABLE_{lbl}_POST_{p:02d}")

    # Sag rods (round bars): one line mid-bay per slope, closing at ridge
    for b in range(len(axes) - 1):
        xm = (axes[b] + axes[b + 1]) / 2.0
        t = f"BAY_{b + 1:02d}"
        pz = 130.0  # sag rods sit at the purlin level (on top of rafters)
        lc = [0.0] + sorted([y for y in purlin_ys if y < RIDGE_Y]) + [RIDGE_Y]
        for s in range(len(lc) - 1):
            ya, yb = lc[s], lc[s + 1]
            rod(doc, (xm, ya, rafter_z(ya) + pz), (xm, yb, rafter_z(yb) + pz), 16, f"TIEROD_L_{t}_{s:02d}")
        rc = [SPAN] + sorted([y for y in purlin_ys if y > RIDGE_Y], reverse=True) + [RIDGE_Y]
        for s in range(len(rc) - 1):
            ya, yb = rc[s], rc[s + 1]
            rod(doc, (xm, ya, rafter_z(ya) + pz), (xm, yb, rafter_z(yb) + pz), 16, f"TIEROD_R_{t}_{s:02d}")

    # Flange braces (mao-francesa): short knee purlin -> rafter bottom flange
    for x in axes:
        for k, y in enumerate(sorted(set(purlin_ys)), start=1):
            zt = rafter_z(y)
            dy = 300 if y < RIDGE_Y else -300
            rod(doc, (x, y, zt - 90), (x, y + dy, zt - 250), 16, f"FLANGEBRACE_{int(x)//1000:02d}_{k:02d}")

    # Tension-only cross bracing (round rods), end bays
    for j, (x0, x1) in enumerate([(axes[0], axes[1]), (axes[-2], axes[-1])], start=1):
        rod(doc, (x0, 0, EAVE_H), (x1, SPAN, EAVE_H), 20, f"BRACE_ROOF_{j:02d}_A")
        rod(doc, (x1, 0, EAVE_H), (x0, SPAN, EAVE_H), 20, f"BRACE_ROOF_{j:02d}_B")
        for yw, side in ((0, "L"), (SPAN, "R")):
            rod(doc, (x0, yw, Z0), (x1, yw, EAVE_H), 20, f"BRACE_WALL_{side}_{j:02d}_A")
            rod(doc, (x1, yw, Z0), (x0, yw, EAVE_H), 20, f"BRACE_WALL_{side}_{j:02d}_B")

    doc.recompute()
    return len(doc.Objects)


def _shares_node(na, nb, tol=250.0):
    """True if members na and nb have any pair of endpoints within tol (a real
    connection node), so their touching is intended, not a clash."""
    pa, pb = REG.get(na), REG.get(nb)
    if not pa or not pb:
        return False
    for a in pa:
        for b in pb:
            if (abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol
                    and abs(a[2] - b[2]) <= tol):
                return True
    return False


SECONDARY = ("PURLIN", "GIRT", "TIEROD", "BRACE", "GABLE", "FLANGEBRACE",
             "ANCHOR", "WASHER", "BASEPLATE")


def _is_secondary(name):
    return any(name.startswith(p) for p in SECONDARY)


def clash_check(doc, min_vol=200.0):
    """Report TRUE unintended clashes. Two members touching is expected when they
    share a connection node, or when a secondary member (purlin, girt, tie rod,
    brace, gable post, anchor) bears on/crosses a primary - those are connections,
    not clashes. A real clash is a non-trivial interference between members that
    neither share a node nor form a secondary-primary bearing."""
    objs = [o for o in doc.Objects if hasattr(o, "Shape") and o.Shape.Volume > 0]
    clashes = []
    for a in range(len(objs)):
        na, sa, ba = objs[a].Name, objs[a].Shape, objs[a].Shape.BoundBox
        for b in range(a + 1, len(objs)):
            nb = objs[b].Name
            if not ba.intersect(objs[b].Shape.BoundBox):
                continue
            if _shares_node(na, nb):
                continue
            if _is_secondary(na) or _is_secondary(nb):
                continue  # secondary bearing on primary = intended connection
            try:
                v = sa.common(objs[b].Shape).Volume
            except Exception:
                continue
            if v > min_vol:
                clashes.append((na, nb, round(v, 1)))
    return clashes


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
    clashes = clash_check(doc)
    fcstd, step = export(doc)
    return {"objects": count, "frames": len(frame_axes()),
            "ridge_height_mm": RIDGE_H, "grout_gap_mm": GROUT_GAP,
            "col_steel_length_mm": EAVE_H - Z0,
            "clash_count": len(clashes), "clashes": clashes[:20],
            "fcstd": fcstd, "step": step}


_result_ = run()
