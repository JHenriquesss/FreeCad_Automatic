"""Modelo parametrico conceitual do galpao 20x10 m (estrutura metalica), v4.

Nomes de todos os elementos em PORTUGUES (equipe/engenheiro nao leem ingles).
Aplica as regras da skill: gap de graute, placas de base + chumbadores + arruelas,
escoras de beiral, montantes de oitao, tirantes fechando na cumeeira, maos-
francesas, tercas com face aberta para o beiral, contraventamento so-tracao.

Gate 8: secoes VERIFICADAS pelo toolkit de calculo (pendente revisao do eng.):
colunas HEA200, vigas HEA180 (base ENGASTADA), tercas Ue 200x75x25x2,65, placa
de base 450x550x40 + 4 chumbadores d20 A307. Secoes secundarias (escora/cumeeira
HEA160, longarinas UPE100) permanecem placeholder ate verificacao propria.
Unidades: mm. Z = 0 no topo do concreto; aco sobe pelo gap de graute.
"""

import math
import os

import FreeCAD as App
import Part

# ---- Parametros (mm) --------------------------------------------------------
LENGTH = 20000.0            # comprimento (X)
SPAN = 10000.0             # vao transversal (Y)
EAVE_H = 6000.0            # pe-direito (do topo do concreto)
SLOPE = 0.10              # inclinacao 10%
BAY = 5000.0             # espacamento entre porticos
GROUT_GAP = 30.0

RIDGE_Y = SPAN / 2.0
RIDGE_H = EAVE_H + SLOPE * RIDGE_Y
Z0 = GROUT_GAP

EXPORT_DIR = "D:/dev/FreeCad_Automatic/projects/galpao/exports"

# Perfis placeholder (secoes europeias; tamanhos NAO verificados).
# I: (h, b, tw, tf)   U: (h, b, tw, tf)
HEA200 = (190.0, 200.0, 6.5, 10.0)
HEA180 = (171.0, 180.0, 6.0, 9.5)
HEA160 = (152.0, 160.0, 6.0, 9.0)
UPE120 = (120.0, 60.0, 5.0, 8.0)
UPE100 = (100.0, 55.0, 4.5, 7.5)
# Gate 8: secoes VERIFICADAS (toolkit). Terca Ue (bw, bf, D, t).
UE_TERCA = (200.0, 75.0, 25.0, 2.65)
CALHA_SEC = (200.0, 300.0, 5.0, 5.0)   # calha autoportante, chapa 5 mm

# Registro de nos: nome -> extremidades (para o check de interferencia)
REG = {}


def _reg(name, *pts):
    REG[name] = [tuple(round(c, 1) for c in p) for p in pts]


# ---- geradores de perfil ---------------------------------------------------
def i_section_pts(sec):
    h, b, tw, tf = sec
    hz, by, tw2 = h / 2.0, b / 2.0, tw / 2.0
    fz = hz - tf
    return [(by, hz), (-by, hz), (-by, fz), (-tw2, fz), (-tw2, -fz),
            (-by, -fz), (-by, -hz), (by, -hz), (by, -fz), (tw2, -fz),
            (tw2, fz), (by, fz)]


def u_section_pts(sec):
    h, b, tw, tf = sec
    hz = h / 2.0
    y0, yw, yb = -b / 2.0, -b / 2.0 + tw, b / 2.0
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
    solid = Part.Face(wire).extrude(App.Vector(L, 0, 0))
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


def ue_section_pts(sec):
    """Perfil U ENRIJECIDO (Ue) = (bw, bf, D, t) ; espessura uniforme t."""
    bw, bf, D, t = sec
    hz = bw / 2.0
    fz = hz - t
    y0, yw, yb, yl = -bf / 2.0, -bf / 2.0 + t, bf / 2.0, bf / 2.0 - t
    return [(y0, hz), (yb, hz), (yb, hz - D), (yl, hz - D), (yl, fz),
            (yw, fz), (yw, -fz), (yl, -fz), (yl, -hz + D), (yb, -hz + D),
            (yb, -hz), (y0, -hz)]


def ue_member(doc, p1, p2, sec, name, roll=0.0):
    return _sweep(ue_section_pts(sec), p1, p2, roll, name, doc)


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
    shp = Part.makeCylinder(od / 2.0, L).cut(Part.makeCylinder(od / 2.0 - wall, L))
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
    face = Part.Face(Part.makePolygon(pts + [pts[0]]))
    n = face.normalAt(0, 0)
    n.multiply(thick)
    return face.extrude(n)


def panel(doc, corners, thick, name, openings=None):
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


# ---- montagem do modelo ----------------------------------------------------
def build(doc):
    axes = frame_axes()

    # Porticos principais: colunas + vigas (perfil I)
    for i, x in enumerate(axes, start=1):
        t = f"PORTICO_{i:02d}"
        i_member(doc, (x, 0, Z0), (x, 0, EAVE_H), HEA200, f"{t}_COLUNA_E")
        i_member(doc, (x, SPAN, Z0), (x, SPAN, EAVE_H), HEA200, f"{t}_COLUNA_D")
        i_member(doc, (x, 0, EAVE_H), (x, RIDGE_Y, RIDGE_H), HEA180, f"{t}_VIGA_E")
        i_member(doc, (x, SPAN, EAVE_H), (x, RIDGE_Y, RIDGE_H), HEA180, f"{t}_VIGA_D")

    # Placas de base ENGASTADAS + chumbadores (gancho L) + arruelas.
    # Gate 8: base 450 (X) x 550 (Y=direcao do momento) x 40 mm ; 4 chumbadores
    # d20 A307, straddle em Y para o braco do momento do engaste.
    for i, x in enumerate(axes, start=1):
        for yw, lado in ((0, "E"), (SPAN, "D")):
            plate(doc, (x, yw, Z0 - 20), 450, 550, 40, f"PLACA_BASE_{lado}_{i:02d}")
            for ddx in (-70, 70):
                for ddy in (-225, 225):
                    sfx = f"{'a' if ddx < 0 else 'b'}{'1' if ddy < 0 else '2'}"
                    rod(doc, (x + ddx, yw + ddy, -300), (x + ddx, yw + ddy, Z0 + 40),
                        20, f"CHUMBADOR_{lado}_{i:02d}_{sfx}")
                    rod(doc, (x + ddx, yw + ddy, -300), (x + ddx, yw + ddy - 60, -300),
                        20, f"CHUMBADOR_GANCHO_{lado}_{i:02d}_{sfx}")
                    plate(doc, (x + ddx, yw + ddy, Z0 - 40), 80, 80, 12,
                          f"ARRUELA_{lado}_{i:02d}_{sfx}")

    # Escoras de beiral + viga de cumeeira (perfil I, por vao)
    for b in range(len(axes) - 1):
        x0, x1 = axes[b], axes[b + 1]
        t = f"VAO_{b + 1:02d}"
        i_member(doc, (x0, 0, EAVE_H), (x1, 0, EAVE_H), HEA160, f"{t}_ESCORA_BEIRAL_E")
        i_member(doc, (x0, SPAN, EAVE_H), (x1, SPAN, EAVE_H), HEA160, f"{t}_ESCORA_BEIRAL_D")
        i_member(doc, (x0, RIDGE_Y, RIDGE_H), (x1, RIDGE_Y, RIDGE_H), HEA160, f"{t}_CUMEEIRA")

    # Tercas: perfil U com face aberta para o BEIRAL (regra CBCA), apoiadas sobre
    # a mesa superior da viga (offset para cima).
    POFF = 130.0
    n_terca = 3
    terca_ys = []
    for k in range(1, n_terca):
        yl = RIDGE_Y * k / n_terca
        terca_ys.append(yl)
        ue_member(doc, (0, yl, rafter_z(yl) + POFF), (LENGTH, yl, rafter_z(yl) + POFF),
                  UE_TERCA, f"TERCA_E_{k:02d}", roll=180)
        yr = SPAN - RIDGE_Y * k / n_terca
        terca_ys.append(yr)
        ue_member(doc, (0, yr, rafter_z(yr) + POFF), (LENGTH, yr, rafter_z(yr) + POFF),
                  UE_TERCA, f"TERCA_D_{k:02d}", roll=0)
    for y, lado, rl in ((0.0, "E", 180), (SPAN, "D", 0)):
        ue_member(doc, (0, y, EAVE_H + POFF), (LENGTH, y, EAVE_H + POFF), UE_TERCA,
                  f"TERCA_BEIRAL_{lado}", roll=rl)

    # Tercas de parede (girts): apoiadas na face externa das colunas. A inferior
    # esquerda e interrompida sobre a porta com uma verga.
    GOFF = 130.0
    DOOR_X = (7300.0, 8200.0)
    for lvl, z in enumerate((2000.0, 4000.0), start=1):
        if lvl == 1:
            u_member(doc, (0, -GOFF, z), (DOOR_X[0], -GOFF, z), UPE100, "TERCA_PAREDE_E_01a", roll=90)
            u_member(doc, (DOOR_X[1], -GOFF, z), (LENGTH, -GOFF, z), UPE100, "TERCA_PAREDE_E_01b", roll=90)
            u_member(doc, (DOOR_X[0], -GOFF, 2250.0), (DOOR_X[1], -GOFF, 2250.0),
                     UPE100, "VERGA_PORTA_E", roll=90)
        else:
            u_member(doc, (0, -GOFF, z), (LENGTH, -GOFF, z), UPE100, f"TERCA_PAREDE_E_{lvl:02d}", roll=90)
        u_member(doc, (0, SPAN + GOFF, z), (LENGTH, SPAN + GOFF, z), UPE100, f"TERCA_PAREDE_D_{lvl:02d}", roll=90)

    # Montantes de oitao. O oitao da FRENTE recebe o portao, entao seus montantes
    # ficam nos batentes; o oitao do FUNDO tem montantes nos tercos do vao.
    GATE_Y = (3000.0, 7000.0)
    for i, x in ((1, axes[0]), (len(axes), axes[-1])):
        lbl = "FRENTE" if x == 0 else "FUNDO"
        mont_ys = GATE_Y if lbl == "FRENTE" else (SPAN / 3.0, 2 * SPAN / 3.0)
        for p, yg in enumerate(mont_ys, start=1):
            i_member(doc, (x, yg, Z0), (x, yg, rafter_z(yg) - 95), HEA160,
                     f"MONTANTE_OITAO_{lbl}_{p:02d}")

    # Tirantes (barras redondas): uma linha por vao/agua, fechando na cumeeira
    for b in range(len(axes) - 1):
        xm = (axes[b] + axes[b + 1]) / 2.0
        t = f"VAO_{b + 1:02d}"
        pz = 130.0
        lc = [0.0] + sorted([y for y in terca_ys if y < RIDGE_Y]) + [RIDGE_Y]
        for s in range(len(lc) - 1):
            ya, yb = lc[s], lc[s + 1]
            rod(doc, (xm, ya, rafter_z(ya) + pz), (xm, yb, rafter_z(yb) + pz), 16, f"TIRANTE_E_{t}_{s:02d}")
        rc = [SPAN] + sorted([y for y in terca_ys if y > RIDGE_Y], reverse=True) + [RIDGE_Y]
        for s in range(len(rc) - 1):
            ya, yb = rc[s], rc[s + 1]
            rod(doc, (xm, ya, rafter_z(ya) + pz), (xm, yb, rafter_z(yb) + pz), 16, f"TIRANTE_D_{t}_{s:02d}")

    # Maos-francesas: contencao da mesa inferior da viga (sob succao de vento)
    for x in axes:
        for k, y in enumerate(sorted(set(terca_ys)), start=1):
            zt = rafter_z(y)
            dy = 300 if y < RIDGE_Y else -300
            rod(doc, (x, y, zt - 90), (x, y + dy, zt - 250), 16, f"MAO_FRANCESA_{int(x)//1000:02d}_{k:02d}")

    # Contraventamento so-tracao (barras redondas), vaos de extremidade
    for j, (x0, x1) in enumerate([(axes[0], axes[1]), (axes[-2], axes[-1])], start=1):
        rod(doc, (x0, 0, EAVE_H), (x1, SPAN, EAVE_H), 20, f"CONTRAV_COBERTURA_{j:02d}_A")
        rod(doc, (x1, 0, EAVE_H), (x0, SPAN, EAVE_H), 20, f"CONTRAV_COBERTURA_{j:02d}_B")
        for yw, lado in ((0, "E"), (SPAN, "D")):
            rod(doc, (x0, yw, Z0), (x1, yw, EAVE_H), 20, f"CONTRAV_PAREDE_{lado}_{j:02d}_A")
            rod(doc, (x1, yw, Z0), (x0, yw, EAVE_H), 20, f"CONTRAV_PAREDE_{lado}_{j:02d}_B")

    # Drenagem (Gate 1): calhas nos dois beirais + condutores, para fora do aco.
    GUT_Y = 340.0
    DOWN_Y = 340.0    # sob a calha; livra a placa de base engastada (550 mm em Y)
    for y, lado, rl in ((-GUT_Y, "E", 90), (SPAN + GUT_Y, "D", -90)):
        u_member(doc, (0, y, EAVE_H), (LENGTH, y, EAVE_H), CALHA_SEC, f"CALHA_{lado}", roll=rl)
    for x in (axes[0], axes[len(axes) // 2], axes[-1]):
        for y, lado in ((-DOWN_Y, "E"), (SPAN + DOWN_Y, "D")):
            tube(doc, (x, y, EAVE_H), (x, y, 0.0), 100.0, 3.0, f"CONDUTOR_{lado}_{int(x)//1000:02d}")

    # Envelope (Gate 3): telha trapezoidal + tapamento metalico. Pele fina.
    TCL = 0.65
    zr = EAVE_H + 200.0
    zrr = RIDGE_H + 200.0
    panel(doc, [(0, 0, zr), (LENGTH, 0, zr), (LENGTH, RIDGE_Y, zrr), (0, RIDGE_Y, zrr)],
          TCL, "TELHA_E")
    panel(doc, [(0, SPAN, zr), (LENGTH, SPAN, zr), (LENGTH, RIDGE_Y, zrr), (0, RIDGE_Y, zrr)],
          TCL, "TELHA_D")

    # Aberturas (Gate 4). Vaos contraventados = vaos de extremidade.
    yw = 195.0
    braced_x = [(0.0, BAY), (LENGTH - BAY, LENGTH)]

    def _in_braced(x0, x1):
        return any(not (x1 <= bx0 or x0 >= bx1) for (bx0, bx1) in braced_x)

    door_x = DOOR_X
    porta = ((door_x, (-yw - 60, -yw + 60), (Z0, 2130.0)),)
    win_x = (BAY, LENGTH - BAY)
    jan_e = ((win_x, (-yw - 60, -yw + 60), (4300.0, 5300.0)),)
    jan_d = ((win_x, (SPAN + yw - 60, SPAN + yw + 60), (4300.0, 5300.0)),)

    panel(doc, [(0, -yw, Z0), (LENGTH, -yw, Z0), (LENGTH, -yw, EAVE_H), (0, -yw, EAVE_H)],
          TCL, "TAPAMENTO_LATERAL_E", openings=list(porta) + list(jan_e))
    panel(doc, [(0, SPAN + yw, Z0), (LENGTH, SPAN + yw, Z0),
                (LENGTH, SPAN + yw, EAVE_H), (0, SPAN + yw, EAVE_H)], TCL,
          "TAPAMENTO_LATERAL_D", openings=list(jan_d))

    # Portao no oitao da FRENTE, vao livre ENTRE os montantes-batente.
    GATE_CLEAR = (GATE_Y[0] + 80.0, GATE_Y[1] - 80.0)
    portao = (((-yw - 300, -yw + 300), GATE_CLEAR, (Z0, 4530.0)),)
    for xc, lbl, ops in ((-yw, "FRENTE", list(portao)), (LENGTH + yw, "FUNDO", [])):
        panel(doc, [(xc, 0, Z0), (xc, SPAN, Z0), (xc, SPAN, EAVE_H),
                    (xc, RIDGE_Y, RIDGE_H), (xc, 0, EAVE_H)], TCL,
              f"TAPAMENTO_OITAO_{lbl}", openings=ops)

    # Check abertura x contraventamento (aberturas de parede)
    global CONFLITOS_ABERTURA_CONTRAV, ABERTURAS_PASSAGEM
    CONFLITOS_ABERTURA_CONTRAV = []
    for label, xr in (("porta", door_x), ("janelas", win_x)):
        if _in_braced(xr[0], xr[1]):
            CONFLITOS_ABERTURA_CONTRAV.append(label)

    # Aberturas de passagem (portao/porta): devem estar livres de estrutura.
    ABERTURAS_PASSAGEM = [
        ("portao_frente", (-yw - 200, -yw + 200, GATE_CLEAR[0], GATE_CLEAR[1], Z0, 4530.0)),
        ("porta_lateral", (door_x[0], door_x[1], -yw - 200, -yw + 200, Z0, 2130.0)),
    ]

    doc.recompute()
    return len(doc.Objects)


# ---- verificacoes ----------------------------------------------------------
SECUNDARIOS = ("TERCA", "TIRANTE", "CONTRAV", "MONTANTE_OITAO", "MAO_FRANCESA",
               "CHUMBADOR", "ARRUELA", "PLACA_BASE")
SERVICO = ("CALHA", "CONDUTOR")
PELE = ("TELHA", "TAPAMENTO")
ESTRUTURA = ("PORTICO_", "MONTANTE_OITAO", "TERCA", "ESCORA_BEIRAL", "CUMEEIRA", "VAO_")


def _e_secundario(n):
    return any(n.startswith(p) for p in SECUNDARIOS)


def _e_servico(n):
    return any(n.startswith(p) for p in SERVICO)


def _e_pele(n):
    return any(n.startswith(p) for p in PELE)


def _compartilha_no(na, nb, tol=250.0):
    pa, pb = REG.get(na), REG.get(nb)
    if not pa or not pb:
        return False
    for a in pa:
        for b in pb:
            if all(abs(a[k] - b[k]) <= tol for k in range(3)):
                return True
    return False


def checa_interferencia(doc, vol_min=200.0):
    """Reporta interferencias reais primario x primario (nao conexoes)."""
    objs = [o for o in doc.Objects if hasattr(o, "Shape") and o.Shape.Volume > 0]
    itf = []
    for a in range(len(objs)):
        na, sa, ba = objs[a].Name, objs[a].Shape, objs[a].Shape.BoundBox
        for b in range(a + 1, len(objs)):
            nb = objs[b].Name
            if not ba.intersect(objs[b].Shape.BoundBox):
                continue
            if _e_pele(na) or _e_pele(nb):
                continue
            servico = _e_servico(na) or _e_servico(nb)
            if not servico:
                if _compartilha_no(na, nb):
                    continue
                if _e_secundario(na) or _e_secundario(nb):
                    continue
            else:
                if _e_servico(na) and _e_servico(nb):
                    continue
            try:
                if sa.common(objs[b].Shape).Volume > vol_min:
                    itf.append((na, nb, round(sa.common(objs[b].Shape).Volume, 1)))
            except Exception:
                pass
    return itf


def estrutura_em_aberturas(doc, vol_min=200.0):
    """Abertura de passagem (portao/porta) deve estar livre de TODA estrutura."""
    hits = []
    for label, (x0, x1, y0, y1, z0, z1) in globals().get("ABERTURAS_PASSAGEM", []):
        box = Part.makeBox(x1 - x0, y1 - y0, z1 - z0)
        box.translate(App.Vector(x0, y0, z0))
        for o in doc.Objects:
            if not hasattr(o, "Shape") or o.Shape.Volume <= 0:
                continue
            if not any(o.Name.startswith(p) for p in ESTRUTURA):
                continue
            if o.Name.startswith("VERGA"):
                continue
            try:
                if box.common(o.Shape).Volume > vol_min:
                    hits.append((label, o.Name))
            except Exception:
                pass
    return hits


# ---- levantamento de material (takeoff) ------------------------------------
DENSIDADE_ACO = 7.85e-6   # kg/mm^3


def _classifica(n):
    if "_COLUNA_" in n:
        return "Colunas", "HEA200"
    if "_VIGA_" in n:
        return "Vigas", "HEA180"
    if "ESCORA_BEIRAL" in n or "_CUMEEIRA" in n:
        return "Escoras de beiral / cumeeira", "HEA160"
    if n.startswith("MONTANTE_OITAO"):
        return "Montantes de oitao", "HEA160"
    if n.startswith("TERCA_PAREDE"):
        return "Tercas de parede", "UPE100"
    if n.startswith("TERCA"):
        return "Tercas", "Ue200x75x25x2.65"
    if n.startswith("TIRANTE") or n.startswith("MAO_FRANCESA"):
        return "Tirantes / maos-francesas", "barra-16"
    if n.startswith("CONTRAV"):
        return "Contraventamento", "barra-20"
    if n.startswith("CHUMBADOR"):
        return "Chumbadores", "barra-20"
    if n.startswith("PLACA_BASE"):
        return "Placas de base", "chapa-40"
    if n.startswith("ARRUELA"):
        return "Arruelas", "chapa-10"
    if n.startswith("CALHA"):
        return "Calhas", "U300x200x5"
    if n.startswith("CONDUTOR"):
        return "Condutores", "tubo-100x3"
    if n.startswith("TELHA"):
        return "Telha de cobertura", "trapez-0.65"
    if n.startswith("TAPAMENTO"):
        return "Tapamento", "trapez-0.65"
    if n.startswith("VERGA"):
        return "Vergas", "UPE100"
    return "Outros", "-"


def takeoff(doc):
    rows = []
    for o in doc.Objects:
        if not hasattr(o, "Shape") or o.Shape.Volume <= 0:
            continue
        cat, prof = _classifica(o.Name)
        massa = o.Shape.Volume * DENSIDADE_ACO
        pts = REG.get(o.Name)
        if pts and len(pts) == 2:
            (x1, y1, z1), (x2, y2, z2) = pts
            comp = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
        else:
            comp = 0.0
        rows.append((o.Name, cat, prof, round(comp, 1), round(massa, 2)))

    grupos = {}
    for _, cat, prof, comp, massa in rows:
        g = grupos.setdefault((cat, prof), [0, 0.0, 0.0])
        g[0] += 1
        g[1] += comp
        g[2] += massa

    tdir = f"{EXPORT_DIR}/takeoff"
    os.makedirs(tdir, exist_ok=True)
    csv_path = f"{tdir}/galpao_levantamento_material.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("categoria,perfil,quantidade,comprimento_total_m,massa_total_kg\n")
        massa_total = 0.0
        for (cat, prof), (cnt, comp, massa) in sorted(grupos.items()):
            f.write(f"{cat},{prof},{cnt},{comp/1000:.2f},{massa:.1f}\n")
            massa_total += massa
        f.write(f"TOTAL,,,,{massa_total:.1f}\n")
        f.write("\n# Detalhe por elemento\n")
        f.write("nome,categoria,perfil,comprimento_mm,massa_kg\n")
        for r in sorted(rows):
            f.write(",".join(str(x) for x in r) + "\n")

    resumo = sorted([(cat, prof, cnt, round(comp / 1000, 2), round(massa, 1))
                     for (cat, prof), (cnt, comp, massa) in grupos.items()],
                    key=lambda r: -r[4])
    return {"csv": csv_path, "massa_total_kg": round(sum(v[2] for v in grupos.values()), 1),
            "elementos": len(rows), "por_grupo": resumo}


def export(doc):
    os.makedirs(f"{EXPORT_DIR}/freecad", exist_ok=True)
    os.makedirs(f"{EXPORT_DIR}/step", exist_ok=True)
    fcstd = f"{EXPORT_DIR}/freecad/galpao_20x10.FCStd"
    step = f"{EXPORT_DIR}/step/galpao_20x10.step"
    doc.saveAs(fcstd)
    Part.export([o for o in doc.Objects if hasattr(o, "Shape")], step)
    return fcstd, step


def run():
    name = "galpao_20x10"
    for d in list(App.listDocuments().values()):
        if d.Name == name:
            App.closeDocument(name)
            break
    doc = App.newDocument(name)
    count = build(doc)
    itf = checa_interferencia(doc)
    est_ab = estrutura_em_aberturas(doc)
    tk = takeoff(doc)
    fcstd, step = export(doc)
    return {"elementos": count, "porticos": len(frame_axes()),
            "altura_cumeeira_mm": RIDGE_H, "gap_graute_mm": GROUT_GAP,
            "comprimento_aco_coluna_mm": EAVE_H - Z0,
            "interferencias": len(itf),
            "conflito_abertura_contrav": globals().get("CONFLITOS_ABERTURA_CONTRAV", []),
            "estrutura_em_aberturas": est_ab,
            "massa_total_kg": tk["massa_total_kg"], "elementos_takeoff": tk["elementos"],
            "por_grupo": tk["por_grupo"], "csv": tk["csv"],
            "fcstd": fcstd, "step": step}


_result_ = run()
