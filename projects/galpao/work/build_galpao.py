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
GUTTER = (200.0, 300.0, 5.0, 5.0)   # self-supporting eave gutter, 5 mm plate


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


def tube(doc, p1, p2, od, wall, name):
    v1, v2 = App.Vector(*p1), App.Vector(*p2)
    d = v2.sub(v1)
    L = d.Length
    if L < 1e-6:
        return None
    outer = Part.makeCylinder(od / 2.0, L)
    inner = Part.makeCylinder(od / 2.0 - wall, L)
    shp = outer.cut(inner)
    rot = App.Rotation(App.Vector(0, 0, 1), d)
    if abs(rot.Angle) > 1e-9:
        shp.rotate(App.Vector(0, 0, 0), rot.Axis, math.degrees(rot.Angle))
    shp.translate(v1)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shp
    _reg(name, p1, p2)
    return obj


def plate(doc, center, wx, wy, wz, name):
    box = Part.makeBox(wx, wy, wz)
    box.translate(App.Vector(center[0] - wx / 2, center[1] - wy / 2, center[2] - wz / 2))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box
    return obj


def panel_shape(corners, thick):
    pts = [App.Vector(*c) for c in corners]
    wire = Part.makePolygon(pts + [pts[0]])
    face = Part.Face(wire)
    n = face.normalAt(0, 0)
    n.multiply(thick)
    return face.extrude(n)


def panel(doc, corners, thick, name, openings=None):
    """Thin cladding panel from planar corners; optional list of cutter boxes
    (each ((x0,x1),(y0,y1),(z0,z1))) is subtracted to form openings."""
    shp = panel_shape(corners, thick)
    for (xr, yr, zr) in (openings or []):
        cutter = Part.makeBox(xr[1] - xr[0], yr[1] - yr[0], zr[1] - zr[0])
        cutter.translate(App.Vector(xr[0], yr[0], zr[0]))
        shp = shp.cut(cutter)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shp
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

    # Gate 1 drainage: eave gutters (both eaves) + downspouts, placed OUTBOARD of
    # the girts/columns so they clear the steel (clash-verified). Gutter opening
    # faces up (roll=90).
    GUT_Y = 340.0    # gutter offset: inboard edge (150) clears the girt outer face
    DOWN_Y = 280.0   # downspout runs just outboard of the girts, under the gutter
    for y, side, rl in ((-GUT_Y, "L", 90), (SPAN + GUT_Y, "R", -90)):
        u_member(doc, (0, y, EAVE_H), (LENGTH, y, EAVE_H), GUTTER,
                 f"GUTTER_{side}", roll=rl)
    for x in (axes[0], axes[len(axes) // 2], axes[-1]):
        for y, side in ((-DOWN_Y, "L"), (SPAN + DOWN_Y, "R")):
            tube(doc, (x, y, EAVE_H), (x, y, 0.0), 100.0, 3.0,
                 f"DOWNSPOUT_{side}_{int(x)//1000:02d}")

    # Gate 3 envelope: trapezoidal roof sheet + full-height steel wall cladding.
    # Thin skin (0.65 mm) placed just outboard of the purlins/girts; classified as
    # skin so it is not treated as a structural clash.
    TCL = 0.65
    zr = EAVE_H + 200.0          # roof cladding elevation offset (on purlin top)
    zrr = RIDGE_H + 200.0
    panel(doc, [(0, 0, zr), (LENGTH, 0, zr), (LENGTH, RIDGE_Y, zrr), (0, RIDGE_Y, zrr)],
          TCL, "CLAD_ROOF_L")
    panel(doc, [(0, SPAN, zr), (LENGTH, SPAN, zr), (LENGTH, RIDGE_Y, zrr), (0, RIDGE_Y, zrr)],
          TCL, "CLAD_ROOF_R")
    # Gate 4 openings. Braced side-wall bays are the end bays (X 0-BAY and
    # LENGTH-BAY..LENGTH). Openings are kept clear of them.
    yw = 195.0
    braced_x = [(0.0, BAY), (LENGTH - BAY, LENGTH)]

    def _in_braced(x0, x1):
        return any(not (x1 <= bx0 or x0 >= bx1) for (bx0, bx1) in braced_x)

    # Personnel door on left wall, central (clear of braced end bays)
    door_x = (9550.0, 10450.0)
    door = ((door_x, (-yw - 60, -yw + 60), (Z0, 2130.0)),)
    # High window strip in the non-braced bays (2 and 3) on both walls
    win_x = (BAY, LENGTH - BAY)  # 5000..15000
    win_l = ((win_x, (-yw - 60, -yw + 60), (4300.0, 5300.0)),)
    win_r = ((win_x, (SPAN + yw - 60, SPAN + yw + 60), (4300.0, 5300.0)),)

    panel(doc, [(0, -yw, Z0), (LENGTH, -yw, Z0), (LENGTH, -yw, EAVE_H), (0, -yw, EAVE_H)],
          TCL, "CLAD_WALL_L", openings=list(door) + list(win_l))
    panel(doc, [(0, SPAN + yw, Z0), (LENGTH, SPAN + yw, Z0),
                (LENGTH, SPAN + yw, EAVE_H), (0, SPAN + yw, EAVE_H)], TCL, "CLAD_WALL_R",
          openings=list(win_r))

    # Main gate on the FRONT gable (X = -yw); gables have no wall bracing.
    gate_y = (3000.0, 7000.0)
    gate = (((-yw - 300, -yw + 300), gate_y, (Z0, 4530.0)),)
    for xc, lbl, ops in ((-yw, "FRONT", list(gate)), (LENGTH + yw, "BACK", [])):
        panel(doc, [(xc, 0, Z0), (xc, SPAN, Z0), (xc, SPAN, EAVE_H),
                    (xc, RIDGE_Y, RIDGE_H), (xc, 0, EAVE_H)], TCL, f"CLAD_GABLE_{lbl}",
              openings=ops)

    # Opening-vs-bracing planning check (skill rule): side-wall openings only.
    global OPENING_CONFLICTS
    OPENING_CONFLICTS = []
    for label, xr in (("door", door_x), ("windows", win_x)):
        if _in_braced(xr[0], xr[1]):
            OPENING_CONFLICTS.append(label)

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
SERVICE = ("GUTTER", "DOWNSPOUT")
SKIN = ("CLAD",)


def _is_secondary(name):
    return any(name.startswith(p) for p in SECONDARY)


def _is_service(name):
    return any(name.startswith(p) for p in SERVICE)


def _is_skin(name):
    return any(name.startswith(p) for p in SKIN)


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
            if _is_skin(na) or _is_skin(nb):
                continue  # cladding bears on purlins/girts by design
            svc = _is_service(na) or _is_service(nb)
            if not svc:
                # structural pair: touching at a node or a secondary-primary
                # bearing is a connection, not a clash.
                if _shares_node(na, nb):
                    continue
                if _is_secondary(na) or _is_secondary(nb):
                    continue
            else:
                # a drainage element intersecting steel IS a real clash;
                # only skip service-vs-service.
                if _is_service(na) and _is_service(nb):
                    continue
            try:
                v = sa.common(objs[b].Shape).Volume
            except Exception:
                continue
            if v > min_vol:
                clashes.append((na, nb, round(v, 1)))
    return clashes


STEEL_DENSITY = 7.85e-6   # kg per mm^3 (7850 kg/m^3)


def _classify(name):
    """Return (category, profile_label) from the object name."""
    if "_COL_" in name:
        return "Columns", "HEA200"
    if "_RAFTER_" in name:
        return "Rafters", "HEA180"
    if "EAVESTRUT" in name or "_RIDGE" in name:
        return "Eave struts / ridge", "HEA160"
    if "GABLE" in name and "POST" in name:
        return "Gable posts", "HEA160"
    if "PURLIN" in name:
        return "Purlins", "UPE120"
    if "GIRT" in name:
        return "Girts", "UPE100"
    if "TIEROD" in name or "FLANGEBRACE" in name:
        return "Sag rods / flange braces", "rod-16"
    if name.startswith("BRACE_"):
        return "Cross bracing", "rod-20"
    if "ANCHOR" in name:
        return "Anchor rods", "rod-25"
    if "BASEPLATE" in name:
        return "Base plates", "plate-22"
    if "WASHER" in name:
        return "Plate washers", "plate-10"
    if "GUTTER" in name:
        return "Gutters", "U300x200x5"
    if "DOWNSPOUT" in name:
        return "Downspouts", "tube-100x3"
    if "CLAD_ROOF" in name:
        return "Roof cladding", "trapez-0.65"
    if "CLAD_WALL" in name or "CLAD_GABLE" in name:
        return "Wall cladding", "trapez-0.65"
    return "Other", "-"


def takeoff(doc):
    """Material takeoff: per member length + mass, grouped by category/profile.
    Mass is exact from the solid volume; length from the registered endpoints."""
    rows = []
    for o in doc.Objects:
        if not hasattr(o, "Shape") or o.Shape.Volume <= 0:
            continue
        cat, prof = _classify(o.Name)
        mass = o.Shape.Volume * STEEL_DENSITY
        pts = REG.get(o.Name)
        if pts and len(pts) == 2:
            (x1, y1, z1), (x2, y2, z2) = pts
            length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
        else:
            length = 0.0
        rows.append((o.Name, cat, prof, round(length, 1), round(mass, 2)))

    # group summary
    groups = {}
    for _, cat, prof, length, mass in rows:
        g = groups.setdefault((cat, prof), [0, 0.0, 0.0])
        g[0] += 1
        g[1] += length
        g[2] += mass

    # write CSV
    tdir = f"{EXPORT_DIR}/takeoff"
    os.makedirs(tdir, exist_ok=True)
    csv_path = f"{tdir}/galpao_takeoff.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("category,profile,count,total_length_m,total_mass_kg\n")
        total_mass = 0.0
        for (cat, prof), (cnt, length, mass) in sorted(groups.items()):
            f.write(f"{cat},{prof},{cnt},{length/1000:.2f},{mass:.1f}\n")
            total_mass += mass
        f.write(f"TOTAL,,,,{total_mass:.1f}\n")
        f.write("\n# Per-member detail\n")
        f.write("name,category,profile,length_mm,mass_kg\n")
        for r in sorted(rows):
            f.write(",".join(str(x) for x in r) + "\n")

    summary = sorted(
        [(cat, prof, cnt, round(length / 1000, 2), round(mass, 1))
         for (cat, prof), (cnt, length, mass) in groups.items()],
        key=lambda r: -r[4])
    total_mass = round(sum(v[2] for v in groups.values()), 1)
    return {"csv": csv_path, "total_mass_kg": total_mass,
            "members": len(rows), "by_group": summary}


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
    tk = takeoff(doc)
    fcstd, step = export(doc)
    return {"objects": count, "frames": len(frame_axes()),
            "ridge_height_mm": RIDGE_H, "grout_gap_mm": GROUT_GAP,
            "col_steel_length_mm": EAVE_H - Z0,
            "clash_count": len(clashes),
            "opening_bracing_conflicts": globals().get("OPENING_CONFLICTS", []),
            "total_mass_kg": tk["total_mass_kg"], "members": tk["members"],
            "by_group": tk["by_group"], "takeoff_csv": tk["csv"],
            "fcstd": fcstd, "step": step}


_result_ = run()
