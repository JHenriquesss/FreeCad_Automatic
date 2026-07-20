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
SPANS = [10000.0]          # largura de cada vao transversal (Y), lista para N vaos
LENGTH = 20000.0           # comprimento (X)
EAVE_H = 6000.0            # pe-direito (do topo do concreto)
SLOPE = 0.10               # inclinacao 10%
BAY = 5000.0               # espacamento entre porticos
AGUAS = 2                  # 2=duas aguas (cumeeira central) ; 1=uma agua (shed:
                           # telhado sobe monotonicamente de Y=0 ate Y=SPAN)
GROUT_GAP = 30.0

TOTAL_Y = sum(SPANS)
Z0 = GROUT_GAP


def _col_ys():
    """Posicoes Y das linhas de coluna (N+1)."""
    return [sum(SPANS[:i]) for i in range(len(SPANS) + 1)]

def _ridge_ys():
    """Posicoes Y das cumeeiras (N)."""
    return [sum(SPANS[:i]) + SPANS[i] / 2.0 for i in range(len(SPANS))]


def rafter_z(y):
    """Cota Z no plano do telhado para um dado Y. Suporta N vaos (2 aguas) e o
    telhado de UMA AGUA (shed: sobe de EAVE_H em Y=0 ate EAVE_H+SLOPE*SPAN em Y=SPAN;
    a cota da coluna alta segue esta funcao)."""
    cols = _col_ys()
    if AGUAS == 1:                         # shed: uma agua monotonica
        return EAVE_H + SLOPE * (y - cols[0])
    ridges = _ridge_ys()
    for i in range(len(SPANS)):
        c0, c1 = cols[i], cols[i + 1]
        if c0 - 1e-6 <= y <= c1 + 1e-6:
            ry = ridges[i]
            if y <= ry:
                return EAVE_H + SLOPE * (y - c0)
            else:
                return EAVE_H + SLOPE * (c1 - y)
    return EAVE_H


def _span_idx(y):
    """Indice do vao que contem a coordenada Y."""
    cols = _col_ys()
    for i in range(len(SPANS)):
        if cols[i] - 1e-6 <= y <= cols[i + 1] + 1e-6:
            return i
    return 0

# Retrocompatibilidade 1 vao: SPAN, RIDGE_Y, RIDGE_H
SPAN = TOTAL_Y
RIDGE_Y = _ridge_ys()[0] if len(SPANS) > 0 else SPAN / 2.0
RIDGE_H = EAVE_H + SLOPE * RIDGE_Y
EXPORT_DIR = "exports"
DOC_NAME = "galpao"


def configurar(length=None, spans=None, span=None, eave_h=None, slope=None, bay=None,
               export_dir=None, doc_name=None, mf_stride=None, n_terca=None,
               n_tirante_parede=None, aberturas=None, terreno_pts=None,
               fechamento=None, ponte_modelo=None,
               perfil_col=None, perfil_raf=None,
               perfil_col_nome=None, perfil_raf_nome=None, base=None,
               perfil_esc=None, perfil_esc_nome=None, joelho=None, terca=None,
               calha=None, condutor_d=None,
               longarina=None, longarina_nome=None, sapata=None,
               estaca=None, bloco=None, baldrame=None,
               tipo_portico=None, tapered=None, trelica=None, reforco_joelho=None,
               aguas=None):
    """Define a geometria (mm) e o destino do projeto (do gate) e RECOMPUTA os
    derivados. Nao muda a modelagem - so os parametros. Chamar antes de run().
    mf_stride vem do calc/mao_francesa.py (1 braco a cada N tercas).
    perfil_col/perfil_raf (h,b,tw,tf em mm) vem do redimensionamento (perfil
    ADOTADO); default = referencia."""
    global LENGTH, SPANS, EAVE_H, SLOPE, BAY, EXPORT_DIR, DOC_NAME, AGUAS
    global MF_STRIDE, N_TERCA, N_TIRANTE_PAREDE, ABERTURAS, TERRENO_PTS, FECHAMENTO
    global PONTE_MODELO, COL_SEC, RAF_SEC, COL_NOME, RAF_NOME, BASE_PLATE
    global HEA_ESC, ESC_NOME, JOELHO_CFG, UE_SEC, UPE_LONG, LONG_NOME, SAPATA_MODEL
    global ESTACA_MODEL, BLOCO_MODEL, BALDRAME_MODEL, TAPERED_MODEL, TRELICA_MODEL
    global REFORCO_JOELHO, CALHA_SEC, CONDUTOR_D
    if calha is not None:
        # (B_mm, H_mm) do calc -> (h=largura, b=ALTURA, tw, tf); a calha e rolada 90.
        _b, _h = float(calha[0]), float(calha[1])
        CALHA_SEC = (_b, _h, CALHA_SEC[2], CALHA_SEC[3])
    if condutor_d is not None: CONDUTOR_D = float(condutor_d)
    if aguas is not None: AGUAS = int(aguas)
    if n_terca is not None: N_TERCA = max(1, int(n_terca))
    if reforco_joelho is not None:
        REFORCO_JOELHO = dict(reforco_joelho) if reforco_joelho else None
    if tapered is not None: TAPERED_MODEL = dict(tapered) if tapered else None
    if trelica is not None: TRELICA_MODEL = dict(trelica) if trelica else None
    if base is not None: BASE_PLATE = dict(BASE_PLATE, **base)
    if sapata is not None: SAPATA_MODEL = dict(sapata) if sapata else None
    if estaca is not None: ESTACA_MODEL = dict(estaca) if estaca else None
    if bloco is not None: BLOCO_MODEL = dict(bloco) if bloco else None
    if baldrame is not None: BALDRAME_MODEL = dict(baldrame) if baldrame else None
    if terca is not None: UE_SEC = tuple(float(v) for v in terca)
    if longarina is not None: UPE_LONG = tuple(float(v) for v in longarina)
    if longarina_nome is not None: LONG_NOME = str(longarina_nome)
    if perfil_esc is not None: HEA_ESC = tuple(float(v) for v in perfil_esc)
    if perfil_esc_nome is not None: ESC_NOME = str(perfil_esc_nome)
    if joelho is not None: JOELHO_CFG = dict(JOELHO_CFG, **joelho)
    if perfil_col is not None: COL_SEC = tuple(float(v) for v in perfil_col)
    if perfil_raf is not None: RAF_SEC = tuple(float(v) for v in perfil_raf)
    if perfil_col_nome is not None: COL_NOME = str(perfil_col_nome)
    if perfil_raf_nome is not None: RAF_NOME = str(perfil_raf_nome)
    if aberturas is not None: ABERTURAS = dict(ABERTURAS, **aberturas)
    if terreno_pts is not None: TERRENO_PTS = terreno_pts
    if fechamento is not None: FECHAMENTO = dict(FECHAMENTO, **fechamento)
    if ponte_modelo is not None:
        PONTE_MODELO = ponte_modelo if ponte_modelo else None
    if length is not None: LENGTH = float(length)
    if spans is not None:
        SPANS = [float(s) for s in spans]
    elif span is not None:
        SPANS = [float(span)]
    if eave_h is not None: EAVE_H = float(eave_h)
    if slope is not None:  SLOPE = float(slope)
    if bay is not None:    BAY = float(bay)
    if export_dir is not None: EXPORT_DIR = export_dir
    if doc_name is not None:   DOC_NAME = doc_name
    if mf_stride is not None:  MF_STRIDE = max(1, int(mf_stride))
    if n_tirante_parede is not None: N_TIRANTE_PAREDE = max(0, int(n_tirante_parede))

# Perfis placeholder (secoes europeias; tamanhos NAO verificados).
# I: (h, b, tw, tf)   U: (h, b, tw, tf)
HEA200 = (190.0, 200.0, 6.5, 10.0)
HEA180 = (171.0, 180.0, 6.0, 9.5)
HEA160 = (152.0, 160.0, 6.0, 9.0)
# Secoes ATIVAS de coluna/viga (parametrizaveis pelo perfil ADOTADO no
# redimensionamento). Default = referencia 20x10. Todas as cotas de conexao
# (joelho, base, terca) leem COL_SEC/RAF_SEC, nao os literais.
COL_SEC = HEA200
RAF_SEC = HEA180
COL_NOME, RAF_NOME = "HEA200", "HEA180"
# Base ENGASTADA parametrica (mm): placa B x L x t + n chumbadores d=db. Default =
# referencia 20x10; sobrescrita pelo dimensionamento (base_adotada) no run real.
BASE_PLATE = {"B": 450.0, "L": 550.0, "t": 40.0, "db": 20.0, "n": 4}
# Secao das escoras de beiral/cumeeira e montantes de oitao (dimensionamento dos
# secundarios). Ligacao do joelho no MODELO (chapa/parafuso). Default = referencia.
HEA_ESC = HEA160
ESC_NOME = "HEA160"
JOELHO_CFG = {"t": 22.0, "db": 24.0, "n": 4}
# Sapata de fundacao (concreto) - opcional. None = nao desenha (so a placa de
# base). Dims em mm: bloco B x L x h + pedestal de altura 'ped' ate a placa.
SAPATA_MODEL = None
# Fundacao PROFUNDA (concreto) - opcional e EXCLUSIVA da sapata. Dims em mm, do
# CALCULO (estaca_profunda / rodar_galpao): estaca {D, L, n, espacamento, tipo};
# bloco de coroamento {h, a}; viga de baldrame {b, h, vao}. None = nao desenha.
ESTACA_MODEL = None
BLOCO_MODEL = None
BALDRAME_MODEL = None
# Portico de alma variavel (tapered): None = rafter prismatico. dict (mm)
# {h_joelho, h_cumeeira, bf, tw, tf} -> rafter em loft (funda no joelho -> rasa na
# cumeeira). O calculo (galpao_portico) ja usou a rigidez variavel.
TAPERED_MODEL = None
# Portico trelicado (tesoura): None = rafter cheio. dict {h(m), n_paineis, tipo,
# d_banzo(mm), d_diag(mm)} -> rafter vira trelica de barras (banzos+diagonais).
TRELICA_MODEL = None
# Reforco da zona de painel do joelho: None = nenhum. dict {t_doubler (mm),
# enrijecedor (bool)} vindo do calculo (zona_painel). So desenha quando exigido.
REFORCO_JOELHO = None
UPE120 = (120.0, 60.0, 5.0, 8.0)
UPE100 = (100.0, 55.0, 4.5, 7.5)
# Gate 8: secoes VERIFICADAS (toolkit). Terca Ue (bw, bf, D, t).
UE_TERCA = (200.0, 75.0, 25.0, 2.65)
UE_SEC = UE_TERCA          # secao da terca de cobertura (parametrizavel pelo calc)
UPE_LONG = UPE100          # secao da longarina de parede (parametrizavel pelo calc)
LONG_NOME = "UPE100"
# Calha autoportante (h, b, tw, tf) em mm, chapa 5 mm. ATENCAO a orientacao: a
# calha e desenhada rolada 90 graus, entao CALHA_SEC[1] (=b) e a ALTURA e
# CALHA_SEC[0] (=h) e a LARGURA da boca. B/H vem do calc (calhas.dimensiona sobe
# a escada de secoes ate drenar a vazao + borda livre + regra de Bellei); ficavam
# fixos aqui e o modelo desenhava 200x300 enquanto a memoria dizia 200x150.
CALHA_SEC = (200.0, 300.0, 5.0, 5.0)
# Diametro do condutor (mm) - do calc (NBR 10844, por vazao); default so p/ o
# modulo rodar isolado.
CONDUTOR_D = 100.0
# Passo da mao-francesa: 1 braco a cada MF_STRIDE tercas. NAO e chute - vem da
# inversao da interacao flexo-compressao no calc/mao_francesa.py (Lb da viga).
# Ref 20x10: stride=2 -> 2 bracos/portico (Lb=3,35 m, interacao 0,93).
MF_STRIDE = 2
# Nº de TERCAS por agua (= nº de espacos entre terca de beiral e cumeeira). NAO e
# escolha de modelagem: o espacamento das tercas E O VAO DA TELHA, e o calc
# (rodar_galpao gate 7) sobe n_terca ate esp_terca <= vao_max da telha (NBR 14762).
# Ficava HARDCODED em 3 aqui dentro, entao o modelo/pranchas/takeoff saiam com 3
# enquanto a memoria certificava 5: na amostra o vao real ia a 3,37 m contra um
# vao_max de 2,14 m (+57%) - o montador compraria e instalaria terca de menos.
# Default 3 so p/ o modulo rodar isolado; o pipeline SEMPRE passa o valor do calc.
N_TERCA = 3
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


def _sweep_tapered(pts1, pts2, p1, p2, roll_deg, name, doc):
    """Como _sweep, mas LOFT entre duas secoes (pts1 em p1, pts2 em p2) -> membro
    de altura variavel (alma variavel/misula). Mesma base local que _sweep."""
    v1, v2 = App.Vector(*p1), App.Vector(*p2)
    d = v2.sub(v1)
    L = d.Length
    if L < 1e-6:
        return None
    w1 = Part.makePolygon([App.Vector(0, y, z) for (y, z) in pts1] +
                          [App.Vector(0, pts1[0][0], pts1[0][1])])
    w2 = Part.makePolygon([App.Vector(L, y, z) for (y, z) in pts2] +
                          [App.Vector(L, pts2[0][0], pts2[0][1])])
    solid = Part.makeLoft([w1, w2], True)          # True = solido
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


def tapered_rafter(doc, p1, p2, name, roll=0.0):
    """Rafter de alma variavel: secao funda no joelho (p1) -> rasa na cumeeira (p2).
    Dims (mm) do TAPERED_MODEL. Perfil I duplamente simetrico. Cai no i_member
    prismatico se as alturas forem iguais (h1==h2)."""
    t = TAPERED_MODEL
    bf, tw, tf = t.get("bf", 200.0), t.get("tw", 8.0), t.get("tf", 12.5)
    h1, h2 = t["h_joelho"], t["h_cumeeira"]
    if abs(h1 - h2) < 1e-6:
        return i_member(doc, p1, p2, (h1, bf, tw, tf), name, roll)
    return _sweep_tapered(i_section_pts((h1, bf, tw, tf)),
                          i_section_pts((h2, bf, tw, tf)), p1, p2, roll, name, doc)


def tapered_column(doc, p1, p2, name, roll=0.0):
    """Coluna de alma variavel: secao RASA na base (p1, h_col_base) -> FUNDA no
    joelho (p2, h_joelho, casa a base do rafter). Dims (mm) do TAPERED_MODEL.
    Cai no i_member prismatico se as alturas forem iguais (h_col_base==h_joelho)."""
    t = TAPERED_MODEL
    bf, tw, tf = t.get("bf", 200.0), t.get("tw", 8.0), t.get("tf", 12.5)
    h1, h2 = t["h_col_base"], t["h_joelho"]
    if abs(h1 - h2) < 1e-6:
        return i_member(doc, p1, p2, (h1, bf, tw, tf), name, roll)
    return _sweep_tapered(i_section_pts((h1, bf, tw, tf)),
                          i_section_pts((h2, bf, tw, tf)), p1, p2, roll, name, doc)


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


def _estaca_offsets(n, esp):
    """Posicoes (dx,dy) das n estacas sob o bloco, do calculo (grupo). 1=central,
    2=linha em X, 4=malha 2x2, demais=fileira em X centrada (espacamento esp)."""
    if n <= 1:
        return [(0.0, 0.0)]
    if n == 2:
        return [(-esp / 2.0, 0.0), (esp / 2.0, 0.0)]
    if n == 4:
        return [(sx * esp / 2.0, sy * esp / 2.0) for sx in (-1, 1) for sy in (-1, 1)]
    return [((k - (n - 1) / 2.0) * esp, 0.0) for k in range(n)]


def _desenha_estaca(doc, x, yw, pbot, pdim, lado, i):
    """Fundacao profunda em um pe: pedestal + bloco de coroamento (concreto) e as
    n estacas (cilindros) descendo do bloco. Dims (mm) do ESTACA_MODEL/BLOCO_MODEL,
    que vem do calculo (estaca_profunda). O bloco em planta cobre o grupo + coroa."""
    D = ESTACA_MODEL["D"]; L = ESTACA_MODEL["L"]
    n = int(ESTACA_MODEL.get("n", 1)); esp = ESTACA_MODEL.get("espacamento", 3.0 * D)
    bh = (BLOCO_MODEL or {}).get("h", max(400.0, 1.2 * D))
    offs = _estaca_offsets(n, esp)
    # coroa (aba de concreto da face da estaca a borda do bloco): praxe 150 mm,
    # mas no minimo D/2 p/ estacas de grande diametro (Q3, Velloso & Lopes/Alonso)
    coroa = max(150.0, D / 2.0)
    xs = [o[0] for o in offs]; ys = [o[1] for o in offs]
    Bx = (max(xs) - min(xs)) + D + 2.0 * coroa
    Ly = (max(ys) - min(ys)) + D + 2.0 * coroa
    # pedestal (pescoco) do pilar ate o bloco = cota de arrasamento da sondagem
    # (Q4): parametro do modelo, default 500 mm A CONFIRMAR pela topografia.
    ped = (BLOCO_MODEL or {}).get("ped", ESTACA_MODEL.get("ped", 500.0))
    z_ped_top = pbot; z_ped_bot = z_ped_top - ped
    z_blk_top = z_ped_bot; z_blk_bot = z_blk_top - bh
    plate(doc, (x, yw, (z_ped_top + z_ped_bot) / 2.0), pdim, pdim, ped,
          f"PEDESTAL_{lado}_{i:02d}")
    plate(doc, (x, yw, (z_blk_top + z_blk_bot) / 2.0), Bx, Ly, bh,
          f"BLOCO_{lado}_{i:02d}")
    for k, (dx, dy) in enumerate(offs, start=1):
        cyl = Part.makeCylinder(D / 2.0, L)
        cyl.translate(App.Vector(x + dx, yw + dy, z_blk_bot - L))
        ob = doc.addObject("Part::Feature", f"ESTACA_{lado}_{i:02d}_{k:02d}")
        ob.Shape = cyl


def _trelica_geom(L, h, n_paineis, tipo):
    """Geometria da tesoura (nos + barras) - copia numpy-free de tesoura.gera_trelica
    (build e self-contained). Retorna (nos[(x,y)], barras[(i,j)])."""
    dx = L / n_paineis
    # banzo superior RETO em duas aguas (segue o telhado; sincronizado com
    # tesoura.gera_trelica apos o parecer Q5): y = (2h/L)*min(x, L-x)
    nos = [(i * dx, (2.0 * h / L) * min(i * dx, L - i * dx) if L > 0 else 0.0)
           for i in range(n_paineis + 1)]
    n_sup = n_paineis + 1
    bars = [(i, i + 1) for i in range(n_paineis)]              # banzo superior
    if tipo == "warren":
        for i in range(n_paineis):
            nos.append(((i + 0.5) * dx, 0.0))
        for i in range(n_paineis - 1):
            bars.append((n_sup + i, n_sup + i + 1))            # banzo inferior
        for i in range(n_paineis):
            bars.append((n_sup + i, i)); bars.append((n_sup + i, i + 1))  # diagonais
    else:  # pratt
        for i in range(1, n_paineis):
            nos.append((i * dx, 0.0))
        n_inf = len(nos)
        bars.append((0, n_sup))
        for i in range(n_sup, n_inf - 1):
            bars.append((i, i + 1))
        bars.append((n_inf - 1, n_paineis))
        for i in range(1, n_paineis):
            bars.append((i, n_sup + i - 1))                    # montantes
        for i in range(1, n_paineis - 1):
            bars.append((i + 1, n_sup + i - 1) if i < n_paineis / 2 else (i, n_sup + i))
    return nos, bars


def _desenha_tesoura(doc, x, y0, y1, tag):
    """Desenha a tesoura (trelica) no plano do portico em X=x, de y0 a y1 (span),
    apoiada no topo das colunas (EAVE_H). Barras como cilindros (banzos+web). Dims
    do TRELICA_MODEL. Banzo superior parabolico ate EAVE_H + h."""
    t = TRELICA_MODEL
    L = abs(y1 - y0) / 1000.0                                  # span em m
    h = t["h"]; npn = int(t.get("n_paineis", 8)); tipo = t.get("tipo", "warren")
    d_banzo = t.get("d_banzo", 100.0); d_diag = t.get("d_diag", 75.0)
    nos, bars = _trelica_geom(L, h, npn, tipo)
    ybase = min(y0, y1)
    P3 = [(x, ybase + xn * 1000.0, EAVE_H + yn * 1000.0) for (xn, yn) in nos]
    n_sup = npn + 1
    for k, (i, j) in enumerate(bars):
        # banzo (sup: i,j<n_sup e |i-j|==1 ; inf idem no range inferior) x web
        banzo = (i < n_sup and j < n_sup) or (i >= n_sup and j >= n_sup)
        dia = d_banzo if banzo else d_diag
        rod(doc, P3[i], P3[j], dia, f"TRELICA_{tag}_{k:02d}")


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


def _esticador(doc, p1, p2, name, od=45.0, ln=180.0):
    """Esticador (lanterna/turnbuckle) no meio de uma barra: manga cilindrica de
    maior diametro, alinhada a barra, centrada no meio."""
    a, b = App.Vector(*p1), App.Vector(*p2)
    d = b.sub(a)
    u = App.Vector(d)
    u.normalize()
    mid = App.Vector((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0,
                     (p1[2] + p2[2]) / 2.0)
    start = mid.sub(App.Vector(u).multiply(ln / 2.0))
    cyl = Part.makeCylinder(od / 2.0, ln)
    rot = App.Rotation(App.Vector(0, 0, 1), d)
    if abs(rot.Angle) > 1e-9:
        cyl.rotate(App.Vector(0, 0, 0), rot.Axis, math.degrees(rot.Angle))
    cyl.translate(start)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = cyl
    _reg(name, p1, p2)
    return obj


def _gusset_tri(doc, node, d1, d2, name, L=150.0, thick=12.0):
    """Chapa gusset triangular no CANTO de um painel de contravento: no + duas
    direcoes de aresta (no plano do painel). Espessura perpendicular ao plano."""
    A = App.Vector(*node)
    B = A.add(App.Vector(*d1).multiply(L))
    C = A.add(App.Vector(*d2).multiply(L))
    face = Part.Face(Part.makePolygon([A, B, C, A]))
    n = face.normalAt(0, 0)
    n.multiply(thick)
    sol = face.extrude(n)
    sol.translate(App.Vector(n).multiply(-0.5))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = sol
    _reg(name, node, node)
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
    # cross(dirn,u) troca de sinal entre os beirais (dirn inverte em Y no cume),
    # entao +v aponta p/ cima num lado e p/ baixo no outro. Forca +v p/ BAIXO para
    # a misula pendurar sob a viga nos DOIS lados (senao um joelho fica invertido).
    if v[2] > 0.0:
        v = (-v[0], -v[1], -v[2])
    cx, cy, cz = node
    hlen = 800.0                        # alcance da misula ao longo da viga
    hdep = 450.0                        # profundidade da misula abaixo da viga (no beiral)
    hhalf = RAF_SEC[0] / 2.0            # meia-altura da viga (face inferior = +hhalf*v)

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
    jt, jdb = JOELHO_CFG["t"], JOELHO_CFG["db"]
    plate_basis(doc, ec, dirn, u, v, jt, 220.0, 250.0, f"CONEX_JOELHO_{tag}_CHAPA")
    # parafusos pela chapa (2 por mesa: +-u no comprimento, +-v junto das mesas).
    b = 0
    for sv in (-1.0, 1.0):
        for su in (-1.0, 1.0):
            b += 1
            p = _p(_p(ec, su * 70.0, u), sv * 90.0, v)
            rod(doc, _p(p, -60.0, dirn), _p(p, 60.0, dirn),
                jdb, f"CONEX_JOELHO_{tag}_M24_{b:02d}")
    # Enrijecedores de continuidade no pilar (preenchem a secao entre as mesas).
    for dz, nm in ((-95.0, "INF"), (-15.0, "SUP")):
        plate(doc, (cx, cy, cz + dz), COL_SEC[0], COL_SEC[1], 12.0,
              f"CONEX_JOELHO_{tag}_ENRIJ_{nm}")
    # CHAPA DE REFORCO DE ALMA (doubler, NBR 8800 5.7.7.2) - SO quando o calculo da
    # zona de painel exigiu (REFORCO_JOELHO.t_doubler > 0). Duas chapas, uma de cada
    # lado da alma do pilar (paralelas a alma, plano X-Z), cobrindo o painel + 150 mm.
    rj = REFORCO_JOELHO
    if isinstance(rj, dict) and rj.get("t_doubler", 0.0) > 0.0:
        td = float(rj["t_doubler"])                 # espessura total (mm), dividida nos 2 lados
        t_lado = max(td / 2.0, 4.0)
        tw_col = COL_SEC[2]
        painel_h = RAF_SEC[0] + 300.0               # altura do painel + 150 mm cada lado
        wx = COL_SEC[0] * 0.7                        # dentro da altura da alma do pilar
        for sy, nm in ((-1.0, "L"), (1.0, "R")):
            offy = sy * (tw_col / 2.0 + t_lado / 2.0)
            plate(doc, (cx, cy + offy, cz - RAF_SEC[0] / 2.0),
                  wx, t_lado, painel_h, f"CONEX_JOELHO_{tag}_DOUBLER_{nm}")


def cumeeira_conn(doc, x, tag, ry=None, rh=None):
    """Ligacao de momento no APICE (cumeeira): CHAPA DE TOPO no encontro das duas
    vigas + parafusos, no plano vertical do portico (normal em Y). Conceitual -
    dimensionamento/parafusamento sao detalhe do eng. responsavel. Fecha a lacuna
    de as duas vigas se encontrarem no apice sem ligacao modelada.

    ry/rh: posicao (Y,Z) da cumeeira DESTE vao. Sem eles caia no global estatico
    RIDGE_Y/RIDGE_H (=5000/6500), desenhando a ligacao fora do apice em vaos !=10m
    e sobrepondo todos os vaos no mesmo ponto em multi-vao (wiki 07 item H)."""
    ry = RIDGE_Y if ry is None else ry
    rh = RIDGE_H if rh is None else rh
    jt, jdb = JOELHO_CFG["t"], JOELHO_CFG["db"]
    dep = RAF_SEC[0]                       # altura da viga (Z)
    wid = RAF_SEC[1]                       # largura da mesa (X)
    # chapa de topo: fina em Y, cobre a secao da viga (+ folga vertical p/ mesas).
    plate(doc, (x, ry, rh), wid, jt, dep + 140.0, f"CONEX_CUMEEIRA_{tag}_CHAPA")
    # 4 parafusos passando pela chapa (2 por mesa), ao longo de Y.
    bx = wid / 2.0 - 35.0
    bz = dep / 2.0 - 25.0
    b = 0
    for sz in (-1.0, 1.0):
        for sx in (-1.0, 1.0):
            b += 1
            rod(doc, (x + sx * bx, ry - 70.0, rh + sz * bz),
                     (x + sx * bx, ry + 70.0, rh + sz * bz),
                jdb, f"CONEX_CUMEEIRA_{tag}_M{int(jdb)}_{b:02d}")


def frame_axes():
    n = int(round(LENGTH / BAY))
    return [i * BAY for i in range(n + 1)]


# ---- montagem do modelo ----------------------------------------------------
def build(doc):
    axes = frame_axes()
    nv = len(SPANS)
    cols_y = _col_ys()
    ridges_y = _ridge_ys()
    SPAN = cols_y[-1]
    RIDGE_Y = ridges_y[0]
    RIDGE_H = rafter_z(RIDGE_Y)

    # Porticos principais: colunas + vigas (I)
    for i, x in enumerate(axes, start=1):
        t = f"PORTICO_{i:02d}"
        col_tap = bool(TAPERED_MODEL) and TAPERED_MODEL.get("h_col_base") is not None
        if AGUAS == 1:                          # SHED: 2 colunas de alturas diferentes + 1 rafter
            y_lo, y_hi = cols_y[0], cols_y[-1]
            z_lo, z_hi = rafter_z(y_lo), rafter_z(y_hi)
            i_member(doc, (x, y_lo, Z0), (x, y_lo, z_lo), COL_SEC, f"{t}_C00")
            i_member(doc, (x, y_hi, Z0), (x, y_hi, z_hi), COL_SEC, f"{t}_C01")
            i_member(doc, (x, y_lo, z_lo), (x, y_hi, z_hi), RAF_SEC, f"{t}_V00")
            continue
        for j in range(nv + 1):
            yc = cols_y[j]
            if col_tap:                              # alma variavel: coluna afina
                tapered_column(doc, (x, yc, Z0), (x, yc, EAVE_H), f"{t}_C{j:02d}")
            else:
                i_member(doc, (x, yc, Z0), (x, yc, EAVE_H), COL_SEC, f"{t}_C{j:02d}")
        for j in range(nv):
            yr = ridges_y[j]; y0 = cols_y[j]; y1 = cols_y[j + 1]
            zh = rafter_z(yr)
            if TRELICA_MODEL:                        # tesoura: trelica no lugar do rafter
                _desenha_tesoura(doc, x, y0, y1, f"{i:02d}_{j:02d}")
            elif TAPERED_MODEL:                      # alma variavel: loft tapered
                tapered_rafter(doc, (x, y0, EAVE_H), (x, yr, zh), f"{t}_V{j:02d}_E")
                tapered_rafter(doc, (x, y1, EAVE_H), (x, yr, zh), f"{t}_V{j:02d}_D")
            else:
                i_member(doc, (x, y0, EAVE_H), (x, yr, zh), RAF_SEC, f"{t}_V{j:02d}_E")
                i_member(doc, (x, y1, EAVE_H), (x, yr, zh), RAF_SEC, f"{t}_V{j:02d}_D")

    # Base ENGASTADA PARAMETRICA (dims do dimensionamento -> BASE_PLATE): placa
    # B x L x t + n chumbadores d=db gancho-L (straddle em Y = direcao do momento)
    # + arruela + PORCA superior + PORCA DE NIVEL sob a placa + NERVURAS (gussets)
    # no plano do momento. Ptop = topo da placa = Z0.
    Bp, Lp, tp = BASE_PLATE["B"], BASE_PLATE["L"], BASE_PLATE["t"]
    dbp, npc = BASE_PLATE["db"], int(BASE_PLATE["n"])
    ptop = Z0
    pbot = Z0 - tp
    edge = 60.0
    gx, gy = Bp / 2.0 - edge, Lp / 2.0 - edge
    ys = [-gy, 0.0, gy] if npc >= 6 else [-gy, gy]      # straddle em Y (+ meia p/ n=6)
    ancoras = [(dx, dy) for dx in (-gx, gx) for dy in ys]
    wsz = 2.0 * dbp + 40.0                              # arruela
    pod = 1.7 * dbp + 8.0                               # diametro da porca
    for i, x in enumerate(axes, start=1):
        for j, yw in enumerate(cols_y):
            lado = f"C{j:02d}"
            plate(doc, (x, yw, Z0 - tp / 2.0), Bp, Lp, tp, f"PLACA_BASE_{lado}_{i:02d}")
            for k, (dx, dy) in enumerate(ancoras, start=1):
                ax, ay, sfx = x + dx, yw + dy, f"{k:02d}"
                rod(doc, (ax, ay, -300), (ax, ay, ptop + 55.0),
                    dbp, f"CHUMBADOR_{lado}_{i:02d}_{sfx}")
                rod(doc, (ax, ay, -300), (ax, ay - 60, -300),
                    dbp, f"CHUMBADOR_GANCHO_{lado}_{i:02d}_{sfx}")
                plate(doc, (ax, ay, ptop + 6.0), wsz, wsz, 12,
                      f"ARRUELA_{lado}_{i:02d}_{sfx}")
                rod(doc, (ax, ay, ptop + 12.0), (ax, ay, ptop + 30.0), pod,
                    f"PORCA_{lado}_{i:02d}_{sfx}")
                rod(doc, (ax, ay, pbot - 28.0), (ax, ay, pbot), pod,
                    f"PORCA_NIVEL_{lado}_{i:02d}_{sfx}")
            for sgn, nm in ((1.0, "P"), (-1.0, "N")):
                ftip = COL_SEC[1] / 2.0
                V1 = App.Vector(x, yw + sgn * ftip, ptop)
                V2 = App.Vector(x, yw + sgn * min(ftip + 140.0, gy + edge), ptop)
                V3 = App.Vector(x, yw + sgn * ftip, ptop + 300.0)
                g = Part.Face(Part.makePolygon([V1, V2, V3, V1])).extrude(
                    App.Vector(12.0, 0, 0))
                g.translate(App.Vector(-6.0, 0, 0))
                ob = doc.addObject("Part::Feature", f"NERVURA_BASE_{lado}_{i:02d}_{nm}")
                ob.Shape = g
                _reg(ob.Name, (x, yw, ptop), (x, yw, ptop))
            pdim = max(COL_SEC[0] + 120.0, COL_SEC[1] + 120.0, 300.0)
            if ESTACA_MODEL:                        # fundacao PROFUNDA (exclusiva)
                _desenha_estaca(doc, x, yw, pbot, pdim, lado, i)
            elif SAPATA_MODEL:                       # fundacao RASA
                sB = SAPATA_MODEL["B"]; sL = SAPATA_MODEL["L"]; sh = SAPATA_MODEL["h"]
                ped = SAPATA_MODEL.get("ped", 500.0)
                z_ped_top = pbot; z_ped_bot = z_ped_top - ped; z_blk_bot = z_ped_bot - sh
                plate(doc, (x, yw, (z_ped_top + z_ped_bot) / 2.0), pdim, pdim, ped,
                      f"PEDESTAL_{lado}_{i:02d}")
                plate(doc, (x, yw, (z_ped_bot + z_blk_bot) / 2.0), sB, sL, sh,
                      f"SAPATA_{lado}_{i:02d}")

    # Viga de baldrame / amarracao: liga as fundacoes de porticos adjacentes.
    # Concreto sob a cota Z0 (topo ~ pbot). So com fundacao profunda (BALDRAME_MODEL
    # vem do calc; amarra o bloco). Q6: cada tramo vai de FACE a FACE do pedestal
    # (vao livre = tramo - pdim), evitando sobrepor o pedestal (sem dupla contagem
    # de concreto no take-off, sem clash espurio).
    if BALDRAME_MODEL:
        bb = BALDRAME_MODEL["b"]; bh = BALDRAME_MODEL["h"]
        z_bal_top = pbot; z_bal_c = z_bal_top - bh / 2.0
        pdim_b = max(COL_SEC[0] + 120.0, COL_SEC[1] + 120.0, 300.0)
        # (1) LONGITUDINAL: ao longo das baias, uma por linha de coluna.
        for j, yw in enumerate(cols_y):
            lado = f"C{j:02d}"
            for i in range(len(axes) - 1):
                x0, x1 = axes[i], axes[i + 1]
                xc = (x0 + x1) / 2.0
                wx = max(abs(x1 - x0) - pdim_b, 50.0)     # vao livre entre pedestais
                plate(doc, (xc, yw, z_bal_c), wx, bb, bh,
                      f"BALDRAME_{lado}_{i + 1:02d}")
        # (2) TRANSVERSAL (Q5): bloco de 1 ou 2 estacas NAO tem estabilidade a
        # rotacao no eixo perpendicular -> NBR 6122 exige travamento nas DUAS
        # direcoes. Desenha baldrames tambem no eixo y (entre linhas de coluna)
        # em cada portico. Malha 2x2 ou maior dispensa (grupo ja resiste em 2
        # direcoes) -> so quando n_estacas <= 2.
        n_est = int(ESTACA_MODEL.get("n", 1)) if ESTACA_MODEL else 0
        if n_est <= 2 and len(cols_y) >= 2:
            for i, x in enumerate(axes):
                lado = f"A{i:02d}"
                for j in range(len(cols_y) - 1):
                    y0, y1 = cols_y[j], cols_y[j + 1]
                    yc = (y0 + y1) / 2.0
                    wy = max(abs(y1 - y0) - pdim_b, 50.0)  # vao livre entre pedestais
                    plate(doc, (x, yc, z_bal_c), bb, wy, bh,
                          f"BALDRAME_T_{lado}_{j + 1:02d}")

    # Joelho (ligacao de momento viga-coluna) em cada portico + cumeeira por vao.
    # Tesoura: a trelica e biapoiada (rotulada) no topo dos pilares -> sem joelho
    # de momento nem chapa de cumeeira (nao ha rafter solido).
    for i, x in enumerate(axes, start=1):
        if TRELICA_MODEL or AGUAS == 1:    # tesoura/shed: sem joelho+cumeeira de 2 aguas
            break
        for j in range(nv + 1):
            yc = cols_y[j]
            # Coluna externa: 1 joelho (para dentro do vao)
            if j == 0:
                _r = rafter_z(ridges_y[0]) - EAVE_H
                joelho(doc, (x, yc, EAVE_H), (0.0, ridges_y[0] - yc, _r), f"{i:02d}_C{j:02d}")
            elif j == nv:
                _r = rafter_z(ridges_y[-1]) - EAVE_H
                joelho(doc, (x, yc, EAVE_H), (0.0, ridges_y[-1] - yc, _r), f"{i:02d}_C{j:02d}")
            else:
                # Coluna interna: 2 joelhos (esquerdo e direito)
                _rl = rafter_z(ridges_y[j - 1]) - EAVE_H
                joelho(doc, (x, yc, EAVE_H), (0.0, ridges_y[j - 1] - yc, _rl), f"{i:02d}_C{j:02d}_E")
                _rr = rafter_z(ridges_y[j]) - EAVE_H
                joelho(doc, (x, yc, EAVE_H), (0.0, ridges_y[j] - yc, _rr), f"{i:02d}_C{j:02d}_D")
        for j in range(nv):
            ry = ridges_y[j]                        # cumeeira DESTE vao (nao o global)
            cumeeira_conn(doc, x, f"{i:02d}_S{j:02d}", ry=ry, rh=rafter_z(ry))

    # Escoras de beiral + viga de cumeeira (perfil I, por vao). No SHED as escoras
    # de beiral seguem a cota REAL do topo de cada coluna (a alta e mais alta) e NAO
    # ha viga de cumeeira (uma agua so).
    for b in range(len(axes) - 1):
        x0, x1 = axes[b], axes[b + 1]
        t = f"VAO_{b + 1:02d}"
        z_e = rafter_z(cols_y[0]); z_d = rafter_z(cols_y[-1])
        i_member(doc, (x0, cols_y[0], z_e), (x1, cols_y[0], z_e), HEA_ESC,
                 f"{t}_ESCORA_BEIRAL_E")
        i_member(doc, (x0, cols_y[-1], z_d), (x1, cols_y[-1], z_d), HEA_ESC,
                 f"{t}_ESCORA_BEIRAL_D")
        if AGUAS != 1:
            for j in range(nv):
                yr = ridges_y[j]; zh = rafter_z(yr)
                i_member(doc, (x0, yr, zh), (x1, yr, zh), HEA_ESC, f"{t}_CUMEEIRA_S{j:02d}")

    # Tercas: perfil U com face aberta para o BEIRAL (regra CBCA). ASSENTAM SOBRE a
    # mesa superior da VIGA (nao penetram). A viga e INCLINADA: o topo real em Z do
    # perfil sobe (h/2)*cos(theta)+(b/2)*sin(theta) acima do eixo (canto da mesa),
    # nao so h/2. Face inferior da terca (plana) == esse topo -> toca sem penetrar.
    # Cada cruzamento com um portico ganha um clipe de apoio. Verif. verifica_conexoes.
    # Offset inicial aproximado (meia-altura projetada da viga inclinada + meia-
    # terca); o assentamento MEDIDO corrige o residual contra a mesa inclinada.
    # Terças de beiral (y=col[0] e y=col[-1]) ficam SOBRE o pilar, não sobre a viga
    # (a viga termina na face do pilar). Por isso são posicionadas SEM _assenta.
    _theta = math.atan(SLOPE)
    _rise = (RAF_SEC[0] / 2.0) * math.cos(_theta) + (RAF_SEC[1] / 2.0) * math.sin(_theta)
    POFF = _rise + UE_SEC[0] / 2.0
    vigas = [o for o in doc.Objects if "_VIGA_" in o.Name and hasattr(o, "Shape")]
    n_terca = N_TERCA                      # do calc (gate 7), nao hardcoded
    terca_ys = []
    terca_objs = []
    for j in range(nv):
        y0, y1 = cols_y[j], cols_y[j + 1]; yrj = ridges_y[j]
        for k in range(1, n_terca):
            yl = y0 + (yrj - y0) * k / n_terca
            terca_ys.append(yl)
            terca_objs.append((yl, ue_member(doc, (0, yl, rafter_z(yl) + POFF),
                              (LENGTH, yl, rafter_z(yl) + POFF), UE_SEC,
                              f"TERCA_S{j:02d}_E_{k:02d}", roll=180)))
            yr = y1 - (y1 - yrj) * k / n_terca
            terca_ys.append(yr)
            terca_objs.append((yr, ue_member(doc, (0, yr, rafter_z(yr) + POFF),
                              (LENGTH, yr, rafter_z(yr) + POFF), UE_SEC,
                              f"TERCA_S{j:02d}_D_{k:02d}", roll=0)))
    # Assenta cada terca INTERMEDIARIA sobre a viga MEDINDO a penetracao (robusto a
    # inclinacao). Terças de beiral ficam SEM _assenta (apoiam no pilar, nao na viga).
    terca_seats = []                    # (y, z_face_inferior) p/ clipes
    for y, o in terca_objs:
        ub = _assenta(o, vigas)
        terca_seats.append((y, ub))
    for y, lado, rl in ((cols_y[0], "E", 180), (cols_y[-1], "D", 0)):
        terca_objs.append((y, ue_member(doc, (0, y, EAVE_H + POFF),
                          (LENGTH, y, EAVE_H + POFF), UE_SEC,
                          f"TERCA_BEIRAL_{lado}", roll=rl)))
        terca_seats.append((y, EAVE_H))
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
    GOFF = COL_SEC[1] / 2.0 + UPE_LONG[0] / 2.0       # girt contra a mesa do pilar
    GIRT_Z = (2000.0, 4000.0)
    DOOR_X = ABERTURAS.get("porta_lateral")         # None se nao ha porta lateral
    for lvl, z in enumerate(GIRT_Z, start=1):
        if lvl == 1 and DOOR_X:
            u_member(doc, (0, -GOFF, z), (DOOR_X[0], -GOFF, z), UPE_LONG, "TERCA_PAREDE_E_01a", roll=90)
            u_member(doc, (DOOR_X[1], -GOFF, z), (LENGTH, -GOFF, z), UPE_LONG, "TERCA_PAREDE_E_01b", roll=90)
            u_member(doc, (DOOR_X[0], -GOFF, 2250.0), (DOOR_X[1], -GOFF, 2250.0),
                     UPE100, "VERGA_PORTA_E", roll=90)
        else:
            u_member(doc, (0, -GOFF, z), (LENGTH, -GOFF, z), UPE_LONG, f"TERCA_PAREDE_E_{lvl:02d}", roll=90)
        u_member(doc, (0, SPAN + GOFF, z), (LENGTH, SPAN + GOFF, z), UPE_LONG, f"TERCA_PAREDE_D_{lvl:02d}", roll=90)
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
            for y, lado in ((-GOFF, "E"), (cols_y[-1] + GOFF, "D")):
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
            i_member(doc, (x, yg, Z0), (x, yg, rafter_z(yg) - 95), HEA_ESC,
                     f"MONTANTE_OITAO_{lbl}_{p:02d}")

    # Tirantes (barras redondas): uma linha por vao/agua, fechando na cumeeira
    for b in range(len(axes) - 1):
        xm = (axes[b] + axes[b + 1]) / 2.0
        t = f"VAO_{b + 1:02d}"
        pz = POFF
        for j in range(nv):
            y0, y1 = cols_y[j], cols_y[j + 1]; yrj = ridges_y[j]
            pts_e = sorted([y for y in terca_ys if y0 <= y < yrj]) + [yrj]
            pts_e = [y0] + [p for p in pts_e if p not in (y0,)]
            for s in range(len(pts_e) - 1):
                ya, yb = pts_e[s], pts_e[s + 1]
                rod(doc, (xm, ya, rafter_z(ya) + pz), (xm, yb, rafter_z(yb) + pz),
                    16, f"TIRANTE_S{j:02d}_E_{t}_{s:02d}")
            pts_d = sorted([y for y in terca_ys if yrj < y <= y1], reverse=True) + [yrj]
            pts_d = [y1] + [p for p in pts_d if p not in (y1,)]
            for s in range(len(pts_d) - 1):
                ya, yb = pts_d[s], pts_d[s + 1]
                rod(doc, (xm, ya, rafter_z(ya) + pz), (xm, yb, rafter_z(yb) + pz),
                    16, f"TIRANTE_S{j:02d}_D_{t}_{s:02d}")

    # Maos-francesas: contencao LATERAL da mesa inferior da viga (sob succao de
    # vento). A geometria (mesa inferior -> terca, com offset LONGITUDINAL em X que
    # trava a mesa FORA do plano do portico) esta no modulo PURO mao_francesa_geom,
    # testado sem FreeCAD. Bug historico: o braco ficava em X CONSTANTE (plano do
    # portico), apontando p/ baixo sem tocar a terca -> nao travava a FLT. Ver
    # Bellei Fig 8.16/8.17 e test_mao_francesa_geom.
    import mao_francesa_geom as mfg
    brace_k = [k for k in range(1, n_terca) if k % MF_STRIDE == 0]
    for p1, p2, nm in mfg.segmentos(axes, cols_y, ridges_y, n_terca, brace_k,
                                    RAF_SEC[0], POFF, rafter_z, theta=_theta):
        rod(doc, p1, p2, 16, nm)

    # Contraventamento so-tracao (barras redondas) nos vaos de extremidade. Cada
    # diagonal recebe um ESTICADOR (lanterna) no meio; cada canto do painel recebe
    # uma CHAPA GUSSET no plano do painel.
    for j, (x0, x1) in enumerate([(axes[0], axes[1]), (axes[-2], axes[-1])], start=1):
        # cobertura (plano X-Y no beiral)
        ca = ((x0, 0, EAVE_H), (x1, SPAN, EAVE_H))
        cb = ((x1, 0, EAVE_H), (x0, SPAN, EAVE_H))
        rod(doc, *ca, 20, f"CONTRAV_COBERTURA_{j:02d}_A")
        rod(doc, *cb, 20, f"CONTRAV_COBERTURA_{j:02d}_B")
        _esticador(doc, *ca, f"ESTICADOR_COBERTURA_{j:02d}_A")
        _esticador(doc, *cb, f"ESTICADOR_COBERTURA_{j:02d}_B")
        for (nx, ny, d1, d2) in ((x0, 0.0, (1, 0, 0), (0, 1, 0)),
                                 (x1, 0.0, (-1, 0, 0), (0, 1, 0)),
                                 (x0, SPAN, (1, 0, 0), (0, -1, 0)),
                                 (x1, SPAN, (-1, 0, 0), (0, -1, 0))):
            _gusset_tri(doc, (nx, ny, EAVE_H), d1, d2,
                        f"CONEX_GUSSET_COB_{j:02d}_{int(nx)//1000:02d}_{int(ny)//1000:02d}")
        # paredes (plano X-Z em cada lado)
        for yw, lado in ((0, "E"), (SPAN, "D")):
            wa = ((x0, yw, Z0), (x1, yw, EAVE_H))
            wb = ((x1, yw, Z0), (x0, yw, EAVE_H))
            rod(doc, *wa, 20, f"CONTRAV_PAREDE_{lado}_{j:02d}_A")
            rod(doc, *wb, 20, f"CONTRAV_PAREDE_{lado}_{j:02d}_B")
            _esticador(doc, *wa, f"ESTICADOR_PAREDE_{lado}_{j:02d}_A")
            _esticador(doc, *wb, f"ESTICADOR_PAREDE_{lado}_{j:02d}_B")
            for (nx, nz, d1, d2) in ((x0, Z0, (1, 0, 0), (0, 0, 1)),
                                     (x1, Z0, (-1, 0, 0), (0, 0, 1)),
                                     (x0, EAVE_H, (1, 0, 0), (0, 0, -1)),
                                     (x1, EAVE_H, (-1, 0, 0), (0, 0, -1))):
                _gusset_tri(doc, (nx, yw, nz), d1, d2,
                            f"CONEX_GUSSET_PAR_{lado}_{j:02d}_{int(nx)//1000:02d}_"
                            f"{'B' if nz < EAVE_H else 'T'}")

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
                tg = f"{lado}_{int(x)//1000:02d}"
                cface = COL_SEC[0] / 2.0                  # face do pilar (h/2)
                # chapa de ligacao console->pilar (face do pilar, perpendicular ao console)
                plate(doc, (x, yw + sgn * cface, hvr), 240.0, 16.0, 240.0,
                      f"CONEX_CONSOLE_{tg}_CHAPA")
                # enrijecedor SOB O TRILHO: chapa transversal na alma da viga de
                # rolamento sobre o apoio (rigidez local + assento do trilho).
                plate(doc, (x, yr, hvr), 12.0, 240.0, 480.0, f"CONEX_CONSOLE_{tg}_TRILHO")
                # mao-francesa (bracket) do console: triangulo no plano do portico
                # sob o console, do pilar ate a ponta.
                _gusset_tri(doc, (x, yw + sgn * cface, hvr - 76.0),
                            (0.0, sgn * (ecc - cface), 0.0), (0.0, 0.0, -450.0),
                            f"CONEX_CONSOLE_{tg}_BRACKET", L=1.0)

    # Drenagem (Gate 1): calhas nos dois beirais + condutores.
    # A calha (CALHA_SEC rolada 90) fica CALHA_SEC[1]=300 mm alta, centrada em
    # EAVE_H e abrindo para cima -> a boca de saida (fundo) esta em EAVE_H-150.
    # O condutor DESCE a partir dessa boca (nao do centro/beiral); um bocal curto
    # de maior diametro envolve a juncao calha->tubo (conexao real, nao topo solto).
    GUT_Y = 340.0
    # condutor livra a placa de base (Y = L/2): afasta conforme a base ADOTADA.
    DOWN_Y = max(GUT_Y, BASE_PLATE["L"] / 2.0 + 70.0)
    GUT_BOTTOM = EAVE_H - CALHA_SEC[1] / 2.0        # boca de saida da calha
    # AMBAS as calhas abrem PARA CIMA (boca +Z) -> roll=+90 nos dois lados. roll=-90
    # invertia a calha do lado D (boca para baixo); o boundbox e simetrico, entao o
    # verifica_conexoes por ZMin nao pegava (ver regra de orientacao em verifica_conexoes).
    for y, lado, rl in ((-GUT_Y, "E", 90), (SPAN + GUT_Y, "D", 90)):
        u_member(doc, (0, y, EAVE_H), (LENGTH, y, EAVE_H), CALHA_SEC, f"CALHA_{lado}", roll=rl)
    for x in (axes[0], axes[len(axes) // 2], axes[-1]):
        for y, lado in ((-DOWN_Y, "E"), (SPAN + DOWN_Y, "D")):
            tag = f"{lado}_{int(x)//1000:02d}"
            # bocal/coletor: colar curto ABAIXO do fundo da calha, abracando o topo
            # do condutor -> boca de saida + emenda, sem furar para dentro da calha.
            # colar = condutor + 30 mm (folga da emenda). DERIVADO, nao fixo: com o
            # condutor vindo do calc, um 130 fixo ficaria MENOR que um tubo de 150.
            tube(doc, (x, y, GUT_BOTTOM), (x, y, GUT_BOTTOM - 120.0),
                 CONDUTOR_D + 30.0, 3.0, f"BOCAL_{tag}")
            tube(doc, (x, y, GUT_BOTTOM), (x, y, 0.0), CONDUTOR_D, 3.0,
                 f"CONDUTOR_{tag}")

    # Envelope (Gate 3): telha trapezoidal + tapamento metalico. Pele fina.
    # A telha ASSENTA SOBRE o topo das tercas (nao as atravessa): offset = topo da
    # mesa da terca acima do eixo da viga (POFF + meia-altura da terca) + meia-telha.
    # (O +200 fixo anterior deixava a telha ~94 mm ABAIXO do topo da terca, enterrada;
    # como a telha e PELE, o clash com ESTRUTURA nao pegava.)
    TCL = 0.65
    TELHA_GAP = 20.0        # folga da face inf da telha sobre o topo da terca mais
                            # alta (altura do clipe/costaneira de fixacao). Sem gap a
                            # telha (pele 0,65 mm) fica COPLANAR ao topo da terca e a
                            # aba aflora pela casca (le como "terca acima da telha").
    # offset acima do eixo da viga = topo da terca MAIS ALTA, MEDIDO apos _assenta
    # (POFF e so a estimativa inicial; o assentamento levanta a terca alguns mm).
    _off = max((zb + UE_SEC[0] - rafter_z(y)) for (y, zb) in terca_seats)
    zr = EAVE_H + _off + TELHA_GAP + TCL / 2.0
    for j in range(nv):
        y0, y1 = cols_y[j], cols_y[j + 1]; yrj = ridges_y[j]; zrrj = rafter_z(yrj) + _off + TELHA_GAP + TCL / 2.0
        panel(doc, [(0, y0, zr), (LENGTH, y0, zr), (LENGTH, yrj, zrrj), (0, yrj, zrrj)],
              TCL, f"TELHA_S{j:02d}_E")
        panel(doc, [(0, y1, zr), (LENGTH, y1, zr), (LENGTH, yrj, zrrj), (0, yrj, zrrj)],
              TCL, f"TELHA_S{j:02d}_D")

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
        pts_gable = [(xc, cols_y[0], Z0), (xc, cols_y[-1], Z0)]
        pts_gable.append((xc, cols_y[-1], EAVE_H))
        for j in range(nv - 1, -1, -1):
            pts_gable.append((xc, ridges_y[j], rafter_z(ridges_y[j])))
            if j > 0:
                pts_gable.append((xc, cols_y[j], EAVE_H))
        pts_gable.append((xc, cols_y[0], EAVE_H))
        panel(doc, pts_gable, TCL, f"TAPAMENTO_OITAO_{lbl}", openings=ops)

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
               "VIGA_ROLAMENTO", "CLIPE", "CONEX", "NERVURA", "PORCA", "ESTICADOR")
FUNDACAO = ("SAPATA", "PEDESTAL", "ESTACA", "BLOCO", "BALDRAME")
SERVICO = ("CALHA", "CONDUTOR", "BOCAL")
PELE = ("TELHA", "TAPAMENTO")
ESTRUTURA = ("PORTICO_", "MONTANTE_OITAO", "TERCA", "ESCORA_BEIRAL", "CUMEEIRA", "VAO_")


def _e_secundario(n):
    return any(n.startswith(p) for p in SECUNDARIOS)


def _e_servico(n):
    return any(n.startswith(p) for p in SERVICO)


def _e_pele(n):
    return any(n.startswith(p) for p in PELE)


def _e_fundacao(n):
    return any(n.startswith(p) for p in FUNDACAO)


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

    # --- Orientacao da calha: a BOCA deve abrir PARA CIMA (nao invertida) ---
    # Mede o centro de massa vs o centro do boundbox: numa calha U aberta para cima
    # o web (fundo) esta embaixo -> CM abaixo do centro; se invertida (boca p/ baixo),
    # o web fica em cima -> CM acima do centro. O boundbox sozinho NAO distingue
    # (simetrico), por isso o defeito da calha invertida passava despercebido.
    for o in doc.Objects:
        if o.Name.startswith("CALHA_") and hasattr(o, "Shape"):
            bb = o.Shape.BoundBox
            cm = o.Shape.CenterOfMass
            if cm.z > bb.Center.z + tol:
                defeitos.append({"conexao": o.Name, "problema":
                    "calha INVERTIDA (boca abre para baixo): CM z=%.0f acima do "
                    "centro %.0f - deve abrir para cima" % (cm.z, bb.Center.z)})

    # --- Contato secundario -> apoio (mapa por familia) + penetracao (so apoio) ---
    # (prefixo_familia, (prefixos de apoio validos), apoia_sobre?)
    # apoia_sobre=True (terca/longarina) -> assenta na mesa, penetracao e defeito.
    # False (tirante/contrav/console/montante) -> enquadra no NO, volume comum e ok.
    APOIO = [
        ("TERCA_BEIRAL",   ("PORTICO_", "VAO_"),                     False),
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
        ("NERVURA_BASE",   ("PLACA_BASE", "PORTICO_"),               False),
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

    # --- Contravento: cada diagonal deve ter um ESTICADOR encostado (tensor) ---
    esticadores = [o for o in doc.Objects
                   if o.Name.startswith("ESTICADOR") and hasattr(o, "Shape")]
    for o in doc.Objects:
        if not o.Name.startswith("CONTRAV") or not hasattr(o, "Shape"):
            continue
        bb = App.BoundBox(o.Shape.BoundBox)
        bb.enlarge(50.0)
        toca = False
        for e in esticadores:
            if not bb.intersect(e.Shape.BoundBox):
                continue
            try:
                if o.Shape.distToShape(e.Shape)[0] < tol:
                    toca = True
                    break
            except Exception:
                pass
        if not toca:
            defeitos.append({"conexao": o.Name, "problema": "diagonal sem esticador"})

    # --- Ponte: enrijecedor SOB O TRILHO deve encostar na viga de rolamento ---
    vrs = [o for o in doc.Objects
           if o.Name.startswith("VIGA_ROLAMENTO") and hasattr(o, "Shape")]
    for o in doc.Objects:
        if "CONEX_CONSOLE" not in o.Name or "TRILHO" not in o.Name:
            continue
        if not hasattr(o, "Shape"):
            continue
        toca = any(o.Shape.distToShape(vr.Shape)[0] < tol for vr in vrs
                   if o.Shape.BoundBox.intersect(vr.Shape.BoundBox))
        if not toca:
            defeitos.append({"conexao": o.Name,
                             "problema": "enrijecedor nao encosta na viga de rolamento"})
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
            # fundacao de concreto e monolitica: estaca/bloco/baldrame/pedestal/
            # sapata se interpenetram DE PROPOSITO (uma unica peca de concreto).
            if _e_fundacao(na) and _e_fundacao(nb):
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


# ---- verificacao de geometria (testes) ------------------------------------
def verificar_geometria(doc):
    """Verifica invariantes geometricos do modelo 3D. Retorna dict com
    status (ok/falha) de cada verificacao. Usado por test_build.py para
    garantir que mudancas no builder nao quebram a geometria."""
    nv = len(SPANS)
    axes = frame_axes()
    n_porticos = len(axes)
    cols_y = _col_ys()
    ridges_y = _ridge_ys()

    objetos = {o.Name: o for o in doc.Objects if hasattr(o, "Shape")}
    nomes = set(objetos.keys())

    def _tem(prefixo):
        return any(n.startswith(prefixo) for n in nomes)

    def _cnt(prefixo):
        return sum(1 for n in nomes if n.startswith(prefixo))

    checks = {}
    # C1: numero de colunas = n_porticos * (nv + 1)
    col_esperadas = n_porticos * (nv + 1)
    col_reais = _cnt("PORTICO_") - _cnt("PORTICO_01_C") - n_porticos * 2 * nv
    # contagem real: cada PORTICO_XX_CYY
    col_reais = sum(1 for n in nomes
                    if any(n.startswith(f"PORTICO_{i:02d}_C{j:02d}")
                           for i in range(1, n_porticos + 1)
                           for j in range(nv + 1)))
    checks["colunas_qtd"] = {"ok": col_reais == col_esperadas,
                             "esperado": col_esperadas, "real": col_reais,
                             "msg": f"{col_reais}/{col_esperadas} colunas"}

    # C2: numero de vigas = n_porticos * nv * 2
    vigas_esp = n_porticos * nv * 2
    vigas_real = sum(1 for n in nomes
                     if any(n.startswith(f"PORTICO_{i:02d}_V{j:02d}_{s}")
                            for i in range(1, n_porticos + 1)
                            for j in range(nv) for s in ("E", "D")))
    checks["vigas_qtd"] = {"ok": vigas_real == vigas_esp,
                           "esperado": vigas_esp, "real": vigas_real,
                           "msg": f"{vigas_real}/{vigas_esp} vigas"}

    # C3: tapamento oitao — 2 paineis (frente + fundo)
    oitao_esp = 2
    oitao_real = _cnt("TAPAMENTO_OITAO_")
    checks["oitao_qtd"] = {"ok": oitao_real == oitao_esp,
                           "esperado": oitao_esp, "real": oitao_real,
                           "msg": f"{oitao_real}/{oitao_esp} oitoes"}

    # C4: cada oitao tem shape valido e area > 1000 mm2
    for lbl in ("FRENTE", "FUNDO"):
        nome = f"TAPAMENTO_OITAO_{lbl}"
        ob = objetos.get(nome)
        valido = ob is not None and hasattr(ob.Shape, "Area") and ob.Shape.Area > 1000
        checks[f"oitao_{lbl}_valido"] = {"ok": valido, "area": ob.Shape.Area if ob and hasattr(ob.Shape, "Area") else 0}

    # C5: telhado de cobertura — 2 paineis por vao
    telha_esp = nv * 2
    telha_real = _cnt("TELHA_")
    checks["telha_qtd"] = {"ok": telha_real == telha_esp,
                           "esperado": telha_esp, "real": telha_real,
                           "msg": f"{telha_real}/{telha_esp} aguas de telhado"}

    # C6: tapamento lateral — 2 paineis (E + D)
    lat_esp = 2
    lat_real = _cnt("TAPAMENTO_LATERAL_")
    checks["lateral_qtd"] = {"ok": lat_real == lat_esp,
                             "esperado": lat_esp, "real": lat_real,
                             "msg": f"{lat_real}/{lat_esp} tapamentos laterais"}

    # C7: colunas nas posicoes Y esperadas
    for i, x in enumerate(axes, start=1):
        for j, yc in enumerate(cols_y):
            nome = f"PORTICO_{i:02d}_C{j:02d}"
            ob = objetos.get(nome)
            if ob is None:
                checks[f"col_{i}_{j}_existe"] = {"ok": False, "msg": f"{nome} ausente"}
                continue
            bb = ob.Shape.BoundBox
            y_centro = (bb.YMin + bb.YMax) / 2.0
            erro = abs(y_centro - yc)
            ok = erro < 10.0
            checks[f"col_{i}_{j}_y"] = {"ok": ok, "y_esperado": yc, "y_real": round(y_centro, 1),
                                        "erro_mm": round(erro, 1)}

    # C8: oitao = poligono simples (nao self-intersect): verifica pelo numero de
    # vertices/edges. Um poligono auto-intersectante tem edges que se cruzam.
    for lbl in ("FRENTE", "FUNDO"):
        nome = f"TAPAMENTO_OITAO_{lbl}"
        ob = objetos.get(nome)
        if ob and hasattr(ob.Shape, "Wires") and ob.Shape.Wires:
            try:
                w = ob.Shape.Wires[0]
                edges = w.Edges
                # Uma face de N vertices tem N edges com shared vertices.
                # Self-intersection e detectada por OCCT, mas aqui fazemos
                # check simples: todo edge deve compartilhar vertice com
                # no maximo 2 outros edges
                shared_count = {}
                for e in edges:
                    for v in e.Vertexes:
                        p = (round(v.X, 1), round(v.Y, 1), round(v.Z, 1))
                        shared_count[p] = shared_count.get(p, 0) + 1
                ok = all(c <= 2 for c in shared_count.values())
                checks[f"oitao_{lbl}_poligono"] = {"ok": ok,
                    "msg": f"{len(edges)} edges, {len(shared_count)} vertices"}
            except Exception:
                checks[f"oitao_{lbl}_poligono"] = {"ok": False, "msg": "erro ao ler wire"}

    # C9: verifica_conexoes() retorna 0 defeitos
    conx = verifica_conexoes(doc)
    checks["conexoes"] = {"ok": len(conx) == 0, "n": len(conx),
                          "msg": f"{len(conx)} conexoes suspeitas" if conx else "ok"}

    # C10: checa_interferencia() retorna 0
    itf = checa_interferencia(doc)
    checks["interferencias"] = {"ok": len(itf) == 0, "n": len(itf),
                                "msg": f"{len(itf)} interferencias" if itf else "ok"}

    checks["todas_ok"] = all(v.get("ok", False) for v in checks.values())
    return checks
DENSIDADE_ACO = 7.85e-6   # kg/mm^3


def _classifica(n):
    if n.startswith("PORTICO_") and "_C" in n:
        return "Colunas", COL_NOME
    if n.startswith("PORTICO_") and "_V" in n:
        return "Vigas", RAF_NOME
    if "ESCORA_BEIRAL" in n or "_CUMEEIRA" in n:
        return "Escoras de beiral / cumeeira", ESC_NOME
    if n.startswith("MONTANTE_OITAO"):
        return "Montantes de oitao", ESC_NOME
    if n.startswith("VIGA_ROLAMENTO"):
        return "Viga de rolamento (ponte)", "VS500"
    if n.startswith("CONSOLE_PONTE"):
        return "Consoles de ponte", "HEA160"
    if n.startswith("TRELICA"):
        return "Trelica (tesoura)", ("tubo-%.0f" % TRELICA_MODEL["d_banzo"]) if TRELICA_MODEL else "barra"
    if n.startswith("TERCA_PAREDE"):
        return "Tercas de parede", LONG_NOME
    if n.startswith("TERCA"):
        return "Tercas", "Ue%.0fx%.0fx%.0fx%.2f" % (UE_SEC[0],UE_SEC[1],UE_SEC[2],UE_SEC[3])
    if n.startswith("TIRANTE") or n.startswith("MAO_FRANCESA"):
        return "Tirantes / maos-francesas", "barra-16"
    if n.startswith("CONTRAV"):
        return "Contraventamento", "barra-20"
    if n.startswith("SAPATA"):
        return "Sapatas (concreto)", "%.0fx%.0fx%.0f" % (
            SAPATA_MODEL["B"], SAPATA_MODEL["L"], SAPATA_MODEL["h"]) if SAPATA_MODEL else "concreto"
    if n.startswith("PEDESTAL"):
        return "Pedestais (concreto)", "concreto"
    if n.startswith("ESTACA"):
        return "Estacas (concreto)", ("D%.0f" % ESTACA_MODEL["D"]) if ESTACA_MODEL else "concreto"
    if n.startswith("BLOCO"):
        return "Blocos de coroamento (concreto)", "concreto"
    if n.startswith("BALDRAME"):
        return "Vigas de baldrame (concreto)", ("%.0fx%.0f" % (
            BALDRAME_MODEL["b"], BALDRAME_MODEL["h"])) if BALDRAME_MODEL else "concreto"
    if n.startswith("CHUMBADOR"):
        return "Chumbadores", "barra-%.0f" % BASE_PLATE["db"]
    if n.startswith("PLACA_BASE"):
        return "Placas de base", "chapa-%.0f" % BASE_PLATE["t"]
    if n.startswith("ARRUELA"):
        return "Arruelas", "chapa-10"
    if n.startswith("PORCA_NIVEL"):
        return "Porcas de nivel", "porca-M20"
    if n.startswith("PORCA"):
        return "Porcas", "porca-M20"
    if n.startswith("NERVURA_BASE"):
        return "Nervuras da base", "chapa-12"
    if "CONEX_CONSOLE" in n and "CHAPA" in n:
        return "Chapa console-pilar (ponte)", "chapa-16"
    if "CONEX_CONSOLE" in n and "TRILHO" in n:
        return "Enrijecedor sob o trilho (ponte)", "chapa-12"
    if "CONEX_CONSOLE" in n and "BRACKET" in n:
        return "Mao-francesa do console (ponte)", "chapa-12"
    if "GUSSET" in n:
        return "Chapas gusset (contravento)", "chapa-12"
    if n.startswith("ESTICADOR"):
        return "Esticadores (contravento)", "esticador-M20"
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
        return "Chapa de topo (joelho)", "chapa-%.0f" % JOELHO_CFG["t"]
    if "JOELHO" in n and "M24" in n:
        return "Parafusos joelho", "M%.0f" % JOELHO_CFG["db"]
    if "JOELHO" in n and "ENRIJ" in n:
        return "Enrijecedores (joelho)", "chapa-12"
    return "Outros", "-"


def takeoff(doc):
    rows = []
    for o in doc.Objects:
        if not hasattr(o, "Shape") or o.Shape.Volume <= 0:
            continue
        cat, prof = _classifica(o.Name)
        # material por densidade: alvenaria (~1400), concreto de fundacao (~2500),
        # aco (7850). Cada um tem subtotal proprio (nao entram na tonelagem de aco).
        if "ALVENARIA" in o.Name:
            dens = 1.4e-6
        elif o.Name.startswith(("SAPATA", "PEDESTAL", "ESTACA", "BLOCO", "BALDRAME")):
            dens = 2.5e-6                      # concreto armado (2500 kg/m3)
        else:
            dens = DENSIDADE_ACO
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

    def _e_concreto(cat):
        return "concreto" in cat.lower()
    massa_aco = sum(m for (cat, _), (_, _, m) in grupos.items()
                    if not _e_alvenaria(cat) and not _e_concreto(cat))
    massa_alv = sum(m for (cat, _), (_, _, m) in grupos.items() if _e_alvenaria(cat))
    massa_conc = sum(m for (cat, _), (_, _, m) in grupos.items() if _e_concreto(cat))
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("categoria,perfil,quantidade,comprimento_total_m,massa_kg\n")
        for (cat, prof), (cnt, comp, massa) in sorted(grupos.items()):
            f.write(f"{cat},{prof},{cnt},{comp/1000:.2f},{massa:.1f}\n")
        f.write(f"SUBTOTAL ACO,,,,{massa_aco:.1f}\n")
        f.write(f"SUBTOTAL ALVENARIA,,,,{massa_alv:.1f}\n")
        f.write(f"SUBTOTAL CONCRETO (fundacao),,,,{massa_conc:.1f}\n")
        f.write(f"TOTAL GERAL,,,,{massa_aco + massa_alv + massa_conc:.1f}\n")
        f.write("\n# Detalhe por elemento\n")
        f.write("nome,categoria,perfil,comprimento_mm,massa_kg\n")
        for r in sorted(rows):
            f.write(",".join(str(x) for x in r) + "\n")

    resumo = sorted([(cat, prof, cnt, round(comp / 1000, 2), round(massa, 1))
                     for (cat, prof), (cnt, comp, massa) in grupos.items()],
                    key=lambda r: -r[4])
    return {"csv": csv_path, "massa_aco_kg": round(massa_aco, 1),
            "massa_alvenaria_kg": round(massa_alv, 1),
            "massa_concreto_kg": round(massa_conc, 1),
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


def capturar_vistas(doc):
    """Captura screenshots das 6 vistas padrao apos o build.
    Salva em EXPORT_DIR/vistas/. Retorna lista de paths.
    Requer FreeCAD.GuiUp (modo grafico)."""
    import time
    VISTAS = [
        ("isometrica",  "viewIsometric"),
        ("frontal",     "viewFront"),
        ("traseira",    "viewRear"),
        ("lateral_dir", "viewRight"),
        ("lateral_esq", "viewLeft"),
        ("superior",    "viewTop"),
    ]
    out = []
    vdir = f"{EXPORT_DIR}/vistas"
    os.makedirs(vdir, exist_ok=True)
    try:
        import FreeCAD
        if not FreeCAD.GuiUp:
            return out
        import FreeCADGui as Gui
        if not hasattr(Gui, "ActiveDocument") or Gui.ActiveDocument is None:
            return out
        Gui.setActiveDocument(doc.Name)
        view = Gui.ActiveDocument.ActiveView
        view.fitAll()
        time.sleep(0.2)
        for nome, metodo in VISTAS:
            getattr(view, metodo)()
            view.fitAll()
            time.sleep(0.5)
            FreeCADGui.updateGui()
            path = f"{vdir}/{nome}.png"
            view.saveImage(path, 1200, 800, "#FFFFFF")
            out.append(path)
    except Exception:
        pass
    return out


def reset():
    """Zera o estado mutavel do builder para o default (evita vazamento entre
    projetos na MESMA sessao do FreeCAD). Chamado no inicio de run()."""
    global ABERTURAS, FECHAMENTO, TERRENO_PTS, MF_STRIDE, N_TIRANTE_PAREDE
    global PONTE_MODELO, COL_SEC, RAF_SEC, COL_NOME, RAF_NOME, BASE_PLATE
    global HEA_ESC, ESC_NOME, JOELHO_CFG, UE_SEC, UPE_LONG, LONG_NOME, SAPATA_MODEL
    global ESTACA_MODEL, BLOCO_MODEL, BALDRAME_MODEL, TAPERED_MODEL, TRELICA_MODEL
    global REFORCO_JOELHO, N_TERCA, CALHA_SEC, CONDUTOR_D
    # N_TERCA/CALHA_SEC/CONDUTOR_D sao decididos pelo CALC: sem reset, um 2o projeto
    # na mesma sessao do FreeCAD herdaria os valores do 1o (a armadilha do _CFG do vento).
    N_TERCA = 3
    CALHA_SEC = (200.0, 300.0, 5.0, 5.0)
    CONDUTOR_D = 100.0
    ESTACA_MODEL = None; BLOCO_MODEL = None; BALDRAME_MODEL = None
    TAPERED_MODEL = None; TRELICA_MODEL = None; REFORCO_JOELHO = None
    UE_SEC = UE_TERCA
    UPE_LONG = UPE100
    LONG_NOME = "UPE100"
    MF_STRIDE = 2
    N_TIRANTE_PAREDE = 2
    TERRENO_PTS = None
    PONTE_MODELO = None
    COL_SEC, RAF_SEC = HEA200, HEA180
    COL_NOME, RAF_NOME = "HEA200", "HEA180"
    BASE_PLATE = {"B": 450.0, "L": 550.0, "t": 40.0, "db": 20.0, "n": 4}
    HEA_ESC = HEA160
    ESC_NOME = "HEA160"
    JOELHO_CFG = {"t": 22.0, "db": 24.0, "n": 4}
    SAPATA_MODEL = None
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
    count = len([o for o in doc.Objects if hasattr(o, "Shape")])
    geo = verificar_geometria(doc)
    vistas = capturar_vistas(doc)
    return {"elementos": count, "vistas": vistas, "porticos": len(frame_axes()),
            "altura_cumeeira_mm": rafter_z(_ridge_ys()[0]), "gap_graute_mm": GROUT_GAP,
            "comprimento_aco_coluna_mm": EAVE_H - Z0,
            "interferencias": len(itf),
            "conexoes_suspeitas": conx,
            "conflito_abertura_contrav": globals().get("CONFLITOS_ABERTURA_CONTRAV", []),
            "estrutura_em_aberturas": est_ab,
            "massa_aco_kg": tk["massa_aco_kg"], "massa_alvenaria_kg": tk["massa_alvenaria_kg"],
             "massa_total_kg": tk["massa_total_kg"], "elementos_takeoff": tk["elementos"],
             "por_grupo": tk["por_grupo"], "csv": tk["csv"],
             "fcstd": fcstd, "step": step,
             "geometria": geo}


_result_ = run()
