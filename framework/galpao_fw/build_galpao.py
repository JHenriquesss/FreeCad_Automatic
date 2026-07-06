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
DOC_NAME = "galpao_20x10"


def configurar(length=None, span=None, eave_h=None, slope=None, bay=None,
               export_dir=None, doc_name=None, mf_stride=None,
               n_tirante_parede=None, aberturas=None, terreno_pts=None,
               fechamento=None, ponte_modelo=None):
    """Define a geometria (mm) e o destino do projeto (do gate) e RECOMPUTA os
    derivados. Nao muda a modelagem - so os parametros. Chamar antes de run().
    mf_stride vem do calc/mao_francesa.py (1 braco a cada N tercas)."""
    global LENGTH, SPAN, EAVE_H, SLOPE, BAY, RIDGE_Y, RIDGE_H, EXPORT_DIR, DOC_NAME
    global MF_STRIDE, N_TIRANTE_PAREDE, ABERTURAS, TERRENO_PTS, FECHAMENTO
    global PONTE_MODELO
    if aberturas is not None: ABERTURAS = dict(ABERTURAS, **aberturas)
    if terreno_pts is not None: TERRENO_PTS = terreno_pts
    if fechamento is not None: FECHAMENTO = dict(FECHAMENTO, **fechamento)
    if ponte_modelo is not None:
        PONTE_MODELO = ponte_modelo if ponte_modelo else None
    if length is not None: LENGTH = float(length)
    if span is not None:   SPAN = float(span)
    if eave_h is not None: EAVE_H = float(eave_h)
    if slope is not None:  SLOPE = float(slope)
    if bay is not None:    BAY = float(bay)
    if export_dir is not None: EXPORT_DIR = export_dir
    if doc_name is not None:   DOC_NAME = doc_name
    if mf_stride is not None:  MF_STRIDE = max(1, int(mf_stride))
    if n_tirante_parede is not None: N_TIRANTE_PAREDE = max(0, int(n_tirante_parede))
    RIDGE_Y = SPAN / 2.0
    RIDGE_H = EAVE_H + SLOPE * RIDGE_Y

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
# Passo da mao-francesa: 1 braco a cada MF_STRIDE tercas. NAO e chute - vem da
# inversao da interacao flexo-compressao no calc/mao_francesa.py (Lb da viga).
# Ref 20x10: stride=2 -> 2 bracos/portico (Lb=3,35 m, interacao 0,93).
MF_STRIDE = 2
# Linhas de tirante de PAREDE por vao (do calc: longarina UPE100 exige 2 -> 0,99).
N_TIRANTE_PAREDE = 2

# Aberturas (Gate 4). NENHUMA e desenhada por padrao alem do que estiver aqui.
# Cada chave None = sem aquela abertura. Larguras/alturas em mm.
#   portao_frente/portao_fundo: (largura, altura) de portao de veiculos no oitao.
#   porta_frente/porta_fundo:   (largura, altura) de porta de pessoas no oitao.
#   janelas_laterais: (z_base, z_topo) da faixa de janelas nas paredes longas.
# Default = conjunto da REFERENCIA (galpao_20x10). A skill sobrescreve pelo Gate 4.
ABERTURAS = {
    "portao_frente": (4000.0, 4530.0),
    "portao_fundo": None,
    "porta_frente": None,
    "porta_fundo": None,
    "janelas_laterais": (4300.0, 5300.0),
    "porta_lateral": (7300.0, 8200.0),   # X0,X1 da porta lateral (ref); None=nenhuma
}

# Terreno (opcional): lista de pontos (x,y) do lote em mm, ja no referencial do
# galpao (a skill translada). None = nao desenha o terreno.
TERRENO_PTS = None

# Fechamento das paredes (Gate 3). tipo: "telha" | "alvenaria_telha" |
# "termoacustica" | "aberto". altura_alvenaria em mm (so p/ alvenaria_telha).
FECHAMENTO = {"tipo": "telha", "altura_alvenaria": None}

# Ponte rolante - GEOMETRIA (se houver). None = sem ponte no desenho.
#   Hvr = altura do trilho (mm) ; excentricidade = trilho fora do eixo do pilar (mm).
PONTE_MODELO = None
VR_SEC = (500.0, 250.0, 8.0, 16.0)   # viga de rolamento (I soldado) - placeholder

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


def _norm(v):
    L = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / L, v[1] / L, v[2] / L) if L > 1e-9 else v


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def plate_basis(doc, center, ex, ey, ez, wx, wy, wz, name):
    """Chapa (caixa wx x wy x wz) com eixos locais alinhados a (ex,ey,ez) - para
    chapas perpendiculares a um membro inclinado (ex.: chapa de topo do joelho)."""
    box = Part.makeBox(wx, wy, wz)
    box.translate(App.Vector(-wx / 2.0, -wy / 2.0, -wz / 2.0))
    m = App.Matrix()
    m.A11, m.A21, m.A31 = ex
    m.A12, m.A22, m.A32 = ey
    m.A13, m.A23, m.A33 = ez
    box = box.transformGeometry(m)
    box.translate(App.Vector(*center))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = box
    _reg(name, center, center)
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


def _assenta(obj, apoios, clearance=0.5, passes=4):
    """Sobe 'obj' ate ASSENTAR sobre 'apoios' MEDINDO a penetracao real (volume
    comum) e levantando por ela. Robusto a secao inclinada/perfil qualquer - nao
    depende de formula de offset (que errava contra a mesa inclinada). Retorna o
    Z da face inferior final."""
    for _ in range(passes):
        ub = obj.Shape.BoundBox
        over = 0.0
        for a in apoios:
            if not ub.intersect(a.Shape.BoundBox):
                continue
            try:
                inter = obj.Shape.common(a.Shape)
            except Exception:
                continue
            if inter.Volume > 1.0:
                over = max(over, inter.BoundBox.ZMax - ub.ZMin)
        if over <= 0.0:
            break
        obj.Shape = obj.Shape.translated(App.Vector(0, 0, over + clearance))
    return obj.Shape.BoundBox.ZMin


def joelho(doc, node, rdir, tag):
    """Ligacao de momento viga-coluna (joelho): MISULA (haunch) soldada no plano do
    portico, CHAPA DE TOPO no splice misula-viga (perpendicular a viga, cobrindo a
    secao cheia), 4 M24 pela chapa e ENRIJECEDORES de continuidade no pilar.
    Conceitual - dimensoes/parafusamento definitivos sao detalhe do eng. responsavel."""
    dirn = _norm(rdir)
    u = (1.0, 0.0, 0.0)                 # ao longo do comprimento (mesas em +-X)
    v = _norm(_cross(dirn, u))          # perpendicular a viga, no plano do portico
    cx, cy, cz = node
    sgn = 1.0 if rdir[1] > 0 else -1.0
    hlen = 800.0                        # alcance da misula ao longo da viga
    hdep = 450.0                        # profundidade da misula abaixo da viga (no beiral)
    hhalf = HEA180[0] / 2.0             # meia-altura da viga (face inferior = +hhalf*v)

    def _p(base, s, vec):
        return (base[0] + s * vec[0], base[1] + s * vec[1], base[2] + s * vec[2])

    # Misula (haunch) SOLDADA: triangulo no plano do portico, pendurado sob a viga.
    # Fundo no beiral (A face inf da viga -> B, hdep abaixo) e afina ate a viga a
    # hlen (C na face inf). +v aponta para BAIXO (perpendicular a viga).
    A = _p(node, hhalf, v)                                   # face inf da viga no no
    B = _p(A, hdep, v)                                       # fundo da misula no beiral
    ncenter = _p(node, hlen, dirn)                           # eixo da viga a hlen
    C = _p(ncenter, hhalf, v)                                # face inf da viga a hlen
    sol = Part.Face(Part.makePolygon([App.Vector(*A), App.Vector(*B),
                                      App.Vector(*C), App.Vector(*A)])).extrude(
        App.Vector(180.0, 0, 0))
    sol.translate(App.Vector(-90.0, 0, 0))
    ob = doc.addObject("Part::Feature", f"CONEX_JOELHO_{tag}_MISULA")
    ob.Shape = sol
    _reg(ob.Name, (cx, cy, cz), (cx, cy, cz))
    # Chapa de topo no fim da misula (splice misula-viga), perpendicular a viga.
    ec = _p(node, hlen + 20.0, dirn)
    plate_basis(doc, ec, dirn, u, v, 22.0, 220.0, 250.0, f"CONEX_JOELHO_{tag}_CHAPA")
    # 4 M24 pela chapa (2 por mesa: +-u no comprimento, +-v junto das mesas).
    b = 0
    for sv in (-1.0, 1.0):
        for su in (-1.0, 1.0):
            b += 1
            p = _p(_p(ec, su * 70.0, u), sv * 90.0, v)
            rod(doc, _p(p, -60.0, dirn), _p(p, 60.0, dirn),
                24.0, f"CONEX_JOELHO_{tag}_M24_{b:02d}")
    # Enrijecedores de continuidade no pilar (mesa inf da viga ~cz-95; cap ~cz-15).
    for dz, nm in ((-95.0, "INF"), (-15.0, "SUP")):
        plate(doc, (cx, cy, cz + dz), 190.0, 200.0, 12.0,
              f"CONEX_JOELHO_{tag}_ENRIJ_{nm}")


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

    # Joelho (ligacao de momento viga-coluna) em cada portico: chapa de topo +
    # 4 M24 + enrijecedores de continuidade no pilar.
    _rise = RIDGE_H - EAVE_H
    for i, x in enumerate(axes, start=1):
        joelho(doc, (x, 0.0, EAVE_H), (0.0, RIDGE_Y, _rise), f"{i:02d}_E")
        joelho(doc, (x, SPAN, EAVE_H), (0.0, -RIDGE_Y, _rise), f"{i:02d}_D")

    # Escoras de beiral + viga de cumeeira (perfil I, por vao)
    for b in range(len(axes) - 1):
        x0, x1 = axes[b], axes[b + 1]
        t = f"VAO_{b + 1:02d}"
        i_member(doc, (x0, 0, EAVE_H), (x1, 0, EAVE_H), HEA160, f"{t}_ESCORA_BEIRAL_E")
        i_member(doc, (x0, SPAN, EAVE_H), (x1, SPAN, EAVE_H), HEA160, f"{t}_ESCORA_BEIRAL_D")
        i_member(doc, (x0, RIDGE_Y, RIDGE_H), (x1, RIDGE_Y, RIDGE_H), HEA160, f"{t}_CUMEEIRA")

    # Tercas: perfil U com face aberta para o BEIRAL (regra CBCA). ASSENTAM SOBRE a
    # mesa superior da VIGA (nao penetram). A viga e INCLINADA: o topo real em Z do
    # perfil sobe (h/2)*cos(theta)+(b/2)*sin(theta) acima do eixo (canto da mesa),
    # nao so h/2. Face inferior da terca (plana) == esse topo -> toca sem penetrar.
    # Cada cruzamento com um portico ganha um clipe de apoio. Verif. verifica_conexoes.
    # Offset inicial aproximado (meia-altura projetada da viga inclinada + meia-
    # terca); o assentamento MEDIDO corrige o residual contra a mesa inclinada.
    _theta = math.atan(SLOPE)
    _rise = (HEA180[0] / 2.0) * math.cos(_theta) + (HEA180[1] / 2.0) * math.sin(_theta)
    POFF = _rise + UE_TERCA[0] / 2.0
    vigas = [o for o in doc.Objects if "_VIGA_" in o.Name and hasattr(o, "Shape")]
    n_terca = 3
    terca_ys = []
    terca_objs = []                     # p/ assentar e depois posicionar clipes
    for k in range(1, n_terca):
        yl = RIDGE_Y * k / n_terca
        terca_ys.append(yl)
        terca_objs.append((yl, ue_member(doc, (0, yl, rafter_z(yl) + POFF),
                          (LENGTH, yl, rafter_z(yl) + POFF), UE_TERCA,
                          f"TERCA_E_{k:02d}", roll=180)))
        yr = SPAN - RIDGE_Y * k / n_terca
        terca_ys.append(yr)
        terca_objs.append((yr, ue_member(doc, (0, yr, rafter_z(yr) + POFF),
                          (LENGTH, yr, rafter_z(yr) + POFF), UE_TERCA,
                          f"TERCA_D_{k:02d}", roll=0)))
    for y, lado, rl in ((0.0, "E", 180), (SPAN, "D", 0)):
        terca_objs.append((y, ue_member(doc, (0, y, EAVE_H + POFF),
                          (LENGTH, y, EAVE_H + POFF), UE_TERCA,
                          f"TERCA_BEIRAL_{lado}", roll=rl)))
    # Assenta cada terca sobre a viga MEDINDO a penetracao (robusto a inclinacao).
    terca_seats = []                    # (y, z_face_inferior) p/ clipes
    for y, o in terca_objs:
        ub = _assenta(o, vigas)
        terca_seats.append((y, ub))
    # Clipes de apoio da terca sobre a mesa da viga/escora (chapa de assento sob a
    # terca em cada portico) - excluidos do clash (conexao), nome CLIPE_.
    for ci, x in enumerate(axes, start=1):
        for cj, (y, ztop) in enumerate(terca_seats, start=1):
            plate(doc, (x, y, ztop - 4.0), 90.0, 120.0, 8.0, f"CLIPE_TERCA_{ci:02d}_{cj:02d}")

    # Tercas de parede (girts): apoiadas na face externa das colunas. Se ha porta
    # LATERAL, a girt inferior esquerda e interrompida sobre ela com uma verga.
    # Longarina (girt) assenta CONTRA a face externa da mesa do pilar (nao penetra):
    # GOFF = meia-largura do pilar + meia-altura da girt -> face interna da girt no
    # plano da mesa. Clipe (cantoneira) em cada pilar. Verificado por verifica_conexoes.
    GOFF = HEA200[1] / 2.0 + UPE100[0] / 2.0        # 150: girt contra a mesa do pilar
    GIRT_Z = (2000.0, 4000.0)
    DOOR_X = ABERTURAS.get("porta_lateral")         # None se nao ha porta lateral
    for lvl, z in enumerate(GIRT_Z, start=1):
        if lvl == 1 and DOOR_X:
            u_member(doc, (0, -GOFF, z), (DOOR_X[0], -GOFF, z), UPE100, "TERCA_PAREDE_E_01a", roll=90)
            u_member(doc, (DOOR_X[1], -GOFF, z), (LENGTH, -GOFF, z), UPE100, "TERCA_PAREDE_E_01b", roll=90)
            u_member(doc, (DOOR_X[0], -GOFF, 2250.0), (DOOR_X[1], -GOFF, 2250.0),
                     UPE100, "VERGA_PORTA_E", roll=90)
        else:
            u_member(doc, (0, -GOFF, z), (LENGTH, -GOFF, z), UPE100, f"TERCA_PAREDE_E_{lvl:02d}", roll=90)
        u_member(doc, (0, SPAN + GOFF, z), (LENGTH, SPAN + GOFF, z), UPE100, f"TERCA_PAREDE_D_{lvl:02d}", roll=90)
    # Clipes da longarina no pilar (chapa contra a face da mesa) - conexao, CLIPE_.
    for ci, x in enumerate(axes, start=1):
        for lj, z in enumerate(GIRT_Z, start=1):
            plate(doc, (x, -100.0 - 4.0, z), 90.0, 8.0, 120.0, f"CLIPE_GIRT_E_{ci:02d}_{lj:02d}")
            plate(doc, (x, SPAN + 100.0 + 4.0, z), 90.0, 8.0, 120.0, f"CLIPE_GIRT_D_{ci:02d}_{lj:02d}")

    # Tirantes de PAREDE (barras redondas verticais): N_TIRANTE_PAREDE linhas por
    # vao, dividem o vao da longarina no eixo fraco -> Lb = bay/(n+1). Exigencia
    # do calc (secundarios_nbr8800): a UPE100 so passa com 2 linhas.
    for b in range(len(axes) - 1):
        x0 = axes[b]
        for k in range(1, N_TIRANTE_PAREDE + 1):
            xk = x0 + BAY * k / (N_TIRANTE_PAREDE + 1)
            for y, lado in ((-GOFF, "E"), (SPAN + GOFF, "D")):
                rod(doc, (xk, y, Z0), (xk, y, EAVE_H), 16,
                    f"TIRANTE_PAREDE_{lado}_{b + 1:02d}_{k:02d}")

    # Montantes de oitao. Se ha portao de veiculos no oitao, os montantes ficam
    # nos BATENTES do portao (centrado no vao); senao, nos tercos do vao.
    def _mont_ys(portao):
        if portao:
            gw = portao[0]
            return (SPAN / 2.0 - gw / 2.0, SPAN / 2.0 + gw / 2.0)
        return (SPAN / 3.0, 2 * SPAN / 3.0)
    GATE_Y = _mont_ys(ABERTURAS.get("portao_frente"))
    for x, lbl, portao in ((axes[0], "FRENTE", ABERTURAS.get("portao_frente")),
                           (axes[-1], "FUNDO", ABERTURAS.get("portao_fundo"))):
        for p, yg in enumerate(_mont_ys(portao), start=1):
            i_member(doc, (x, yg, Z0), (x, yg, rafter_z(yg) - 95), HEA160,
                     f"MONTANTE_OITAO_{lbl}_{p:02d}")

    # Tirantes (barras redondas): uma linha por vao/agua, fechando na cumeeira
    for b in range(len(axes) - 1):
        xm = (axes[b] + axes[b + 1]) / 2.0
        t = f"VAO_{b + 1:02d}"
        pz = POFF                       # no plano das tercas (que subiram para assentar)
        lc = [0.0] + sorted([y for y in terca_ys if y < RIDGE_Y]) + [RIDGE_Y]
        for s in range(len(lc) - 1):
            ya, yb = lc[s], lc[s + 1]
            rod(doc, (xm, ya, rafter_z(ya) + pz), (xm, yb, rafter_z(yb) + pz), 16, f"TIRANTE_E_{t}_{s:02d}")
        rc = [SPAN] + sorted([y for y in terca_ys if y > RIDGE_Y], reverse=True) + [RIDGE_Y]
        for s in range(len(rc) - 1):
            ya, yb = rc[s], rc[s + 1]
            rod(doc, (xm, ya, rafter_z(ya) + pz), (xm, yb, rafter_z(yb) + pz), 16, f"TIRANTE_D_{t}_{s:02d}")

    # Maos-francesas: contencao da mesa inferior da viga (sob succao de vento).
    # Passo MF_STRIDE vem do calc (inversao da interacao) - so nas tercas
    # interiores multiplas do passo; joelho e cumeeira ja sao pontos travados.
    brace_k = [k for k in range(1, n_terca) if k % MF_STRIDE == 0]
    for x in axes:
        c = 0
        for k in brace_k:
            for y in (RIDGE_Y * k / n_terca, SPAN - RIDGE_Y * k / n_terca):
                c += 1
                zt = rafter_z(y)
                dy = 300 if y < RIDGE_Y else -300
                rod(doc, (x, y, zt - 90), (x, y + dy, zt - 250), 16,
                    f"MAO_FRANCESA_{int(x)//1000:02d}_{c:02d}")

    # Contraventamento so-tracao (barras redondas), vaos de extremidade
    for j, (x0, x1) in enumerate([(axes[0], axes[1]), (axes[-2], axes[-1])], start=1):
        rod(doc, (x0, 0, EAVE_H), (x1, SPAN, EAVE_H), 20, f"CONTRAV_COBERTURA_{j:02d}_A")
        rod(doc, (x1, 0, EAVE_H), (x0, SPAN, EAVE_H), 20, f"CONTRAV_COBERTURA_{j:02d}_B")
        for yw, lado in ((0, "E"), (SPAN, "D")):
            rod(doc, (x0, yw, Z0), (x1, yw, EAVE_H), 20, f"CONTRAV_PAREDE_{lado}_{j:02d}_A")
            rod(doc, (x1, yw, Z0), (x0, yw, EAVE_H), 20, f"CONTRAV_PAREDE_{lado}_{j:02d}_B")

    # Ponte rolante (geometria): viga de rolamento sobre consoles (misulas) nos
    # pilares, no nivel do trilho Hvr, excentrica ao eixo do pilar.
    if PONTE_MODELO:
        hvr = float(PONTE_MODELO.get("Hvr", 4500.0))
        ecc = float(PONTE_MODELO.get("excentricidade", 300.0))
        for yw, lado, sgn in ((0.0, "E", +1.0), (SPAN, "D", -1.0)):
            yr = yw + sgn * ecc                      # eixo do trilho (para dentro)
            i_member(doc, (0, yr, hvr), (LENGTH, yr, hvr), VR_SEC,
                     f"VIGA_ROLAMENTO_{lado}")
            for x in axes:                           # console/misula em cada portico
                i_member(doc, (x, yw, hvr), (x, yr, hvr), HEA160,
                         f"CONSOLE_PONTE_{lado}_{int(x)//1000:02d}")

    # Drenagem (Gate 1): calhas nos dois beirais + condutores.
    # A calha (CALHA_SEC rolada 90) fica CALHA_SEC[1]=300 mm alta, centrada em
    # EAVE_H e abrindo para cima -> a boca de saida (fundo) esta em EAVE_H-150.
    # O condutor DESCE a partir dessa boca (nao do centro/beiral); um bocal curto
    # de maior diametro envolve a juncao calha->tubo (conexao real, nao topo solto).
    GUT_Y = 340.0
    DOWN_Y = 340.0    # sob a calha; livra a placa de base engastada (550 mm em Y)
    GUT_BOTTOM = EAVE_H - CALHA_SEC[1] / 2.0        # boca de saida da calha
    for y, lado, rl in ((-GUT_Y, "E", 90), (SPAN + GUT_Y, "D", -90)):
        u_member(doc, (0, y, EAVE_H), (LENGTH, y, EAVE_H), CALHA_SEC, f"CALHA_{lado}", roll=rl)
    for x in (axes[0], axes[len(axes) // 2], axes[-1]):
        for y, lado in ((-DOWN_Y, "E"), (SPAN + DOWN_Y, "D")):
            tag = f"{lado}_{int(x)//1000:02d}"
            # bocal/coletor: colar curto ABAIXO do fundo da calha, abracando o topo
            # do condutor -> boca de saida + emenda, sem furar para dentro da calha.
            tube(doc, (x, y, GUT_BOTTOM), (x, y, GUT_BOTTOM - 120.0), 130.0, 3.0,
                 f"BOCAL_{tag}")
            tube(doc, (x, y, GUT_BOTTOM), (x, y, 0.0), 100.0, 3.0, f"CONDUTOR_{tag}")

    # Envelope (Gate 3): telha trapezoidal + tapamento metalico. Pele fina.
    TCL = 0.65
    zr = EAVE_H + 200.0
    zrr = RIDGE_H + 200.0
    panel(doc, [(0, 0, zr), (LENGTH, 0, zr), (LENGTH, RIDGE_Y, zrr), (0, RIDGE_Y, zrr)],
          TCL, "TELHA_E")
    panel(doc, [(0, SPAN, zr), (LENGTH, SPAN, zr), (LENGTH, RIDGE_Y, zrr), (0, RIDGE_Y, zrr)],
          TCL, "TELHA_D")

    # Aberturas (Gate 4) - dirigidas por ABERTURAS (config). So desenha o pedido.
    yw = 195.0
    braced_x = [(0.0, BAY), (LENGTH - BAY, LENGTH)]

    def _in_braced(x0, x1):
        return any(not (x1 <= bx0 or x0 >= bx1) for (bx0, bx1) in braced_x)

    global CONFLITOS_ABERTURA_CONTRAV, ABERTURAS_PASSAGEM
    CONFLITOS_ABERTURA_CONTRAV = []
    ABERTURAS_PASSAGEM = []
    PORTA_PESSOA = (900.0, 2130.0)                  # vao de porta de pessoas padrao

    # --- paredes laterais (longas): porta lateral (opcional) + faixa de janelas
    lat_ops = {"E": [], "D": []}
    pl = ABERTURAS.get("porta_lateral")
    if pl:                                          # (X0, X1) na parede esquerda
        lat_ops["E"].append((pl, (-yw - 60, -yw + 60), (Z0, Z0 + PORTA_PESSOA[1])))
        ABERTURAS_PASSAGEM.append(("porta_lateral", (pl[0], pl[1], -yw - 200,
                                   -yw + 200, Z0, Z0 + PORTA_PESSOA[1])))
        if _in_braced(pl[0], pl[1]):
            CONFLITOS_ABERTURA_CONTRAV.append("porta_lateral")
    jl = ABERTURAS.get("janelas_laterais")
    if jl:                                          # faixa (z_base, z_topo) nos vaos centrais
        win_x = (BAY, LENGTH - BAY)
        lat_ops["E"].append((win_x, (-yw - 60, -yw + 60), jl))
        lat_ops["D"].append((win_x, (SPAN + yw - 60, SPAN + yw + 60), jl))
        if _in_braced(win_x[0], win_x[1]):
            CONFLITOS_ABERTURA_CONTRAV.append("janelas")
    # Fechamento (Gate 3): "aberto" nao desenha parede; "alvenaria_telha" faz
    # meia-parede de alvenaria (ate altura_alvenaria) + telha acima nas LATERAIS
    # (oitoes ficam em telha por causa dos portoes); demais tipos = telha cheia.
    ftipo = FECHAMENTO.get("tipo", "telha")
    h_alv = FECHAMENTO.get("altura_alvenaria") or 0.0

    def _parede_lateral(y, name, ops):
        if ftipo == "aberto":
            return
        if ftipo == "alvenaria_telha" and h_alv > Z0:
            plate(doc, (LENGTH / 2.0, y, Z0 + (h_alv - Z0) / 2.0), LENGTH, 190.0,
                  h_alv - Z0, name + "_ALVENARIA")
            zb = h_alv                                  # telha comeca no topo da alvenaria
            ops_sup = [o for o in ops if o[2][1] > zb]  # so aberturas acima
        else:
            zb, ops_sup = Z0, ops
        panel(doc, [(0, y, zb), (LENGTH, y, zb), (LENGTH, y, EAVE_H), (0, y, EAVE_H)],
              TCL, name, openings=ops_sup)
    _parede_lateral(-yw, "TAPAMENTO_LATERAL_E", lat_ops["E"])
    _parede_lateral(SPAN + yw, "TAPAMENTO_LATERAL_D", lat_ops["D"])

    # --- oitoes (empenas): portao de veiculos e/ou porta de pessoas
    for xc, lbl, sgn in ((-yw, "FRENTE", -1.0), (LENGTH + yw, "FUNDO", +1.0)):
        if ftipo == "aberto":
            continue
        ops = []
        portao = ABERTURAS.get(f"portao_{lbl.lower()}")
        porta = ABERTURAS.get(f"porta_{lbl.lower()}")
        if portao:
            gw, gh = portao
            yr = (SPAN / 2.0 - gw / 2.0 + 80.0, SPAN / 2.0 + gw / 2.0 - 80.0)
            ops.append(((xc - 300, xc + 300), yr, (Z0, Z0 + gh)))
            ABERTURAS_PASSAGEM.append((f"portao_{lbl.lower()}",
                (xc - 200, xc + 200, yr[0], yr[1], Z0, Z0 + gh)))
        if porta:
            pw, ph = porta
            yr = (SPAN / 2.0 - pw / 2.0, SPAN / 2.0 + pw / 2.0)
            ops.append(((xc - 300, xc + 300), yr, (Z0, Z0 + ph)))
            ABERTURAS_PASSAGEM.append((f"porta_{lbl.lower()}",
                (xc - 200, xc + 200, yr[0], yr[1], Z0, Z0 + ph)))
        panel(doc, [(xc, 0, Z0), (xc, SPAN, Z0), (xc, SPAN, EAVE_H),
                    (xc, RIDGE_Y, RIDGE_H), (xc, 0, EAVE_H)], TCL,
              f"TAPAMENTO_OITAO_{lbl}", openings=ops)

    doc.recompute()
    return len(doc.Objects)


def desenha_terreno(doc, pts_xy, z=0.0):
    """Desenha o poligono do lote (pts em mm, referencial do galpao) como uma
    face no nivel do solo (Z=0). So representacao - nao entra no takeoff/clash."""
    import Part
    vees = [App.Vector(x, y, z) for (x, y) in pts_xy]
    if (vees[0] - vees[-1]).Length > 1e-6:
        vees.append(vees[0])
    wire = Part.makePolygon(vees)
    obj = doc.addObject("Part::Feature", "TERRENO_LOTE")
    try:
        obj.Shape = Part.Face(wire)
    except Exception:
        obj.Shape = wire
    if hasattr(obj, "ViewObject") and obj.ViewObject:
        obj.ViewObject.Transparency = 60
    return obj


# ---- verificacoes ----------------------------------------------------------
SECUNDARIOS = ("TERCA", "TIRANTE", "CONTRAV", "MONTANTE_OITAO", "MAO_FRANCESA",
               "CHUMBADOR", "ARRUELA", "PLACA_BASE", "CONSOLE_PONTE",
               "VIGA_ROLAMENTO", "CLIPE", "CONEX")
SERVICO = ("CALHA", "CONDUTOR", "BOCAL")
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


def verifica_conexoes(doc, tol=6.0):
    """Verifica invariantes GEOMETRICOS de conexao MEDINDO as formas reais (nao
    deduz de parametros/roll). Retorna lista de defeitos {conexao, problema}. E o
    ponto de crescimento: cada conexao critica vira uma regra aqui para que o erro
    seja pego pelo build, nao pelo olho. Regras:
      - dreno: topo do condutor coincide com o FUNDO da calha; bocal cobre a junta;
      - contato: cada secundario ENCOSTA (dist<=tol) em pelo menos um apoio valido
        do seu mapa (senao 'flutuando'); um APOIO por distancia-ao-primario puro
        daria falso positivo (tirantes apoiam em secundarios), por isso o mapa;
      - apoio (terca): membro que APOIA nao pode ATRAVESSAR a viga/pilar (volume
        comum acima de vol_pen) - deve assentar sobre a mesa, nao penetrar."""
    defeitos = []
    calha_fundo = {}                       # lado -> Z do fundo (medido)
    for o in doc.Objects:
        if o.Name.startswith("CALHA_") and hasattr(o, "Shape"):
            lado = o.Name.split("_")[1]
            calha_fundo[lado] = o.Shape.BoundBox.ZMin
    for o in doc.Objects:
        if not hasattr(o, "Shape"):
            continue
        if o.Name.startswith("CONDUTOR_"):
            lado = o.Name.split("_")[1]
            fundo = calha_fundo.get(lado)
            if fundo is None:
                defeitos.append({"conexao": o.Name, "problema": "sem calha no lado"})
                continue
            topo = o.Shape.BoundBox.ZMax
            if topo > fundo + tol:
                defeitos.append({"conexao": o.Name, "problema":
                    "topo %.0f ACIMA do fundo da calha %.0f (dif %.0f)"
                    % (topo, fundo, topo - fundo)})
            elif topo < fundo - tol:
                defeitos.append({"conexao": o.Name, "problema":
                    "topo %.0f DESCOLADO do fundo da calha %.0f (gap %.0f)"
                    % (topo, fundo, fundo - topo)})
        elif o.Name.startswith("BOCAL_"):
            lado = o.Name.split("_")[1]
            fundo = calha_fundo.get(lado)
            if fundo is None:
                continue
            b = o.Shape.BoundBox
            if not (b.ZMin - tol <= fundo <= b.ZMax + tol):
                defeitos.append({"conexao": o.Name, "problema":
                    "nao cobre a junta (fundo calha %.0f fora de %.0f..%.0f)"
                    % (fundo, b.ZMin, b.ZMax)})

    # --- Contato secundario -> apoio (mapa por familia) + penetracao (so apoio) ---
    # (prefixo_familia, (prefixos de apoio validos), apoia_sobre?)
    # apoia_sobre=True (terca/longarina) -> assenta na mesa, penetracao e defeito.
    # False (tirante/contrav/console/montante) -> enquadra no NO, volume comum e ok.
    APOIO = [
        ("TERCA_BEIRAL",   ("PORTICO_", "VAO_"),                     True),
        ("TERCA_PAREDE",   ("PORTICO_",),                            True),
        ("TERCA_E",        ("PORTICO_",),                            True),
        ("TERCA_D",        ("PORTICO_",),                            True),
        ("TIRANTE_PAREDE", ("TERCA_PAREDE", "PORTICO_", "PLACA_BASE"), False),
        ("TIRANTE_E_VAO",  ("TERCA_",),                              False),
        ("TIRANTE_D_VAO",  ("TERCA_",),                              False),
        ("MAO_FRANCESA",   ("PORTICO_", "TERCA_"),                   False),
        ("CONTRAV",        ("PORTICO_",),                            False),
        ("CONSOLE_PONTE",  ("PORTICO_",),                            False),
        ("VIGA_ROLAMENTO", ("CONSOLE_PONTE",),                       False),
        ("MONTANTE_OITAO", ("PORTICO_", "VAO_"),                     False),
    ]

    def _familia(nome):
        for pref, apo, bear in APOIO:
            if nome.startswith(pref):
                return apo, bear
        return None, None

    shapes = [o for o in doc.Objects if hasattr(o, "Shape") and o.Shape.Volume > 0]
    vol_pen = 500.0                       # volume comum acima disso = atravessa
    for o in shapes:
        apo, bear = _familia(o.Name)
        if apo is None:
            continue
        bb = App.BoundBox(o.Shape.BoundBox)
        bb.enlarge(700.0)
        cand = [p for p in shapes if p.Name != o.Name
                and p.Name.startswith(tuple(apo)) and bb.intersect(p.Shape.BoundBox)]
        if not cand:
            defeitos.append({"conexao": o.Name,
                             "problema": "sem apoio %s por perto" % (apo,)})
            continue
        dmin = 1e9
        pen, pen_nome = 0.0, None
        for p in cand:
            try:
                d = o.Shape.distToShape(p.Shape)[0]
            except Exception:
                continue
            if d < dmin:
                dmin = d
            if bear and d < tol:
                try:
                    v = o.Shape.common(p.Shape).Volume
                    if v > pen:
                        pen, pen_nome = v, p.Name
                except Exception:
                    pass
        if dmin > tol:
            defeitos.append({"conexao": o.Name,
                             "problema": "flutuando: gap %.0f ao apoio" % dmin})
        elif bear and pen > vol_pen:
            defeitos.append({"conexao": o.Name, "problema":
                "atravessa %s (volume comum %.0f mm3) - deve assentar sobre a mesa"
                % (pen_nome, pen)})

    # --- Joelho: cada parafuso M24 deve estar DENTRO da chapa de topo do seu tag ---
    chapas = {}                         # tag -> BoundBox da chapa
    for o in doc.Objects:
        if "JOELHO" in o.Name and "CHAPA" in o.Name and hasattr(o, "Shape"):
            tag = o.Name.replace("CONEX_JOELHO_", "").replace("_CHAPA", "")
            chapas[tag] = o.Shape.BoundBox
    for o in doc.Objects:
        if "JOELHO" in o.Name and "M24" in o.Name and hasattr(o, "Shape"):
            tag = o.Name.replace("CONEX_JOELHO_", "").rsplit("_M24", 1)[0]
            bb = chapas.get(tag)
            if bb is None:
                defeitos.append({"conexao": o.Name, "problema": "sem chapa de topo no tag"})
                continue
            c = o.Shape.BoundBox.Center
            big = App.BoundBox(bb); big.enlarge(tol + 24.0)   # folga = tol + diametro
            if not big.isInside(c):
                defeitos.append({"conexao": o.Name,
                                 "problema": "parafuso fora da chapa de topo"})
    return defeitos


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
    if n.startswith("VIGA_ROLAMENTO"):
        return "Viga de rolamento (ponte)", "VS500"
    if n.startswith("CONSOLE_PONTE"):
        return "Consoles de ponte", "HEA160"
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
    if n.startswith("BOCAL"):
        return "Bocais (coletores calha->condutor)", "tubo-130x3"
    if "ALVENARIA" in n:
        return "Alvenaria (meia-parede)", "bloco-19"
    if n.startswith("TELHA"):
        return "Telha de cobertura", "trapez-0.65"
    if n.startswith("TAPAMENTO"):
        return "Tapamento", "trapez-0.65"
    if n.startswith("VERGA"):
        return "Vergas", "UPE100"
    if n.startswith("CLIPE"):
        return "Clipes de apoio (conexao)", "chapa-8"
    if "JOELHO" in n and "MISULA" in n:
        return "Misulas (joelho)", "chapa-9.5"
    if "JOELHO" in n and "CHAPA" in n:
        return "Chapa de topo (joelho)", "chapa-22"
    if "JOELHO" in n and "M24" in n:
        return "Parafusos M24 (joelho)", "M24"
    if "JOELHO" in n and "ENRIJ" in n:
        return "Enrijecedores (joelho)", "chapa-12"
    return "Outros", "-"


def takeoff(doc):
    rows = []
    for o in doc.Objects:
        if not hasattr(o, "Shape") or o.Shape.Volume <= 0:
            continue
        cat, prof = _classifica(o.Name)
        # alvenaria nao e aco: usa densidade de bloco (~1400 kg/m3) e nao entra
        # na tonelagem de aco (categoria propria).
        dens = 1.4e-6 if "ALVENARIA" in o.Name else DENSIDADE_ACO
        massa = o.Shape.Volume * dens
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
    # totais por MATERIAL: aco (estrutura + telha/tapamento metalico) x alvenaria.
    def _e_alvenaria(cat):
        return "Alvenaria" in cat
    massa_aco = sum(m for (cat, _), (_, _, m) in grupos.items() if not _e_alvenaria(cat))
    massa_alv = sum(m for (cat, _), (_, _, m) in grupos.items() if _e_alvenaria(cat))
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("categoria,perfil,quantidade,comprimento_total_m,massa_kg\n")
        for (cat, prof), (cnt, comp, massa) in sorted(grupos.items()):
            f.write(f"{cat},{prof},{cnt},{comp/1000:.2f},{massa:.1f}\n")
        f.write(f"SUBTOTAL ACO,,,,{massa_aco:.1f}\n")
        f.write(f"SUBTOTAL ALVENARIA,,,,{massa_alv:.1f}\n")
        f.write(f"TOTAL GERAL,,,,{massa_aco + massa_alv:.1f}\n")
        f.write("\n# Detalhe por elemento\n")
        f.write("nome,categoria,perfil,comprimento_mm,massa_kg\n")
        for r in sorted(rows):
            f.write(",".join(str(x) for x in r) + "\n")

    resumo = sorted([(cat, prof, cnt, round(comp / 1000, 2), round(massa, 1))
                     for (cat, prof), (cnt, comp, massa) in grupos.items()],
                    key=lambda r: -r[4])
    return {"csv": csv_path, "massa_aco_kg": round(massa_aco, 1),
            "massa_alvenaria_kg": round(massa_alv, 1),
            "massa_total_kg": round(massa_aco + massa_alv, 1),
            "elementos": len(rows), "por_grupo": resumo}


def export(doc):
    os.makedirs(f"{EXPORT_DIR}/freecad", exist_ok=True)
    os.makedirs(f"{EXPORT_DIR}/step", exist_ok=True)
    fcstd = f"{EXPORT_DIR}/freecad/{DOC_NAME}.FCStd"
    step = f"{EXPORT_DIR}/step/{DOC_NAME}.step"
    doc.saveAs(fcstd)
    Part.export([o for o in doc.Objects if hasattr(o, "Shape")], step)
    return fcstd, step


def reset():
    """Zera o estado mutavel do builder para o default (evita vazamento entre
    projetos na MESMA sessao do FreeCAD). Chamado no inicio de run()."""
    global ABERTURAS, FECHAMENTO, TERRENO_PTS, MF_STRIDE, N_TIRANTE_PAREDE
    global PONTE_MODELO
    MF_STRIDE = 2
    N_TIRANTE_PAREDE = 2
    TERRENO_PTS = None
    PONTE_MODELO = None
    FECHAMENTO = {"tipo": "telha", "altura_alvenaria": None}
    ABERTURAS = {"portao_frente": None, "portao_fundo": None, "porta_frente": None,
                 "porta_fundo": None, "janelas_laterais": None, "porta_lateral": None}


def run():
    name = DOC_NAME
    for d in list(App.listDocuments().values()):
        if d.Name == name:
            App.closeDocument(name)
            break
    doc = App.newDocument(name)
    count = build(doc)
    itf = checa_interferencia(doc)
    conx = verifica_conexoes(doc)
    est_ab = estrutura_em_aberturas(doc)
    tk = takeoff(doc)
    if TERRENO_PTS:                                 # lote depois do takeoff/clash
        desenha_terreno(doc, TERRENO_PTS)
        doc.recompute()
    fcstd, step = export(doc)
    return {"elementos": count, "porticos": len(frame_axes()),
            "altura_cumeeira_mm": RIDGE_H, "gap_graute_mm": GROUT_GAP,
            "comprimento_aco_coluna_mm": EAVE_H - Z0,
            "interferencias": len(itf),
            "conexoes_suspeitas": conx,
            "conflito_abertura_contrav": globals().get("CONFLITOS_ABERTURA_CONTRAV", []),
            "estrutura_em_aberturas": est_ab,
            "massa_aco_kg": tk["massa_aco_kg"], "massa_alvenaria_kg": tk["massa_alvenaria_kg"],
            "massa_total_kg": tk["massa_total_kg"], "elementos_takeoff": tk["elementos"],
            "por_grupo": tk["por_grupo"], "csv": tk["csv"],
            "fcstd": fcstd, "step": step}


_result_ = run()
