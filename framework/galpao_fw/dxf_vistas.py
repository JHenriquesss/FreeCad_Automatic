# ============================================================================
# dxf_vistas.py - GERADOR DE VISTAS DXF (padrao prancha AutoCAD)
# Desenha o galpao PARAMETRICAMENTE (nao projeta solidos): portico transversal,
# elevacao longitudinal, planta de cobertura e legenda, em CAMADAS e COTADO, a
# partir do design ADOTADO (geometria + perfis + base do calculo). Unidades: mm.
# CONCEITUAL - PENDENTE REVISAO E ART DO ENGENHEIRO RESPONSAVEL.
# ============================================================================
"""Gera um DXF com as vistas estruturais do galpao (ezdxf). So desenho 2D."""

from __future__ import annotations

import math

import ezdxf


# ---- camadas (nome, cor ACI, linetype) -------------------------------------
CAMADAS = [
    ("EIXOS", 4, "CENTER"),        # linhas de eixo (ciano, traco-ponto)
    ("ACO", 7, "CONTINUOUS"),      # perfis metalicos (branco/preto)
    ("BASE", 2, "CONTINUOUS"),     # placas de base / concreto (amarelo)
    ("FURACAO", 1, "CONTINUOUS"),  # chumbadores / parafusos (vermelho)
    ("COTAS", 3, "CONTINUOUS"),    # dimensoes (verde)
    ("TEXTO", 7, "CONTINUOUS"),
    ("CONTRAV", 5, "DASHED"),      # contraventamento (azul, tracejado)
]


def _setup(doc):
    for nome, cor, lt in CAMADAS:
        ly = doc.layers.add(nome)
        ly.color = cor
        try:
            ly.linetype = lt
        except Exception:
            pass
    # estilo de cota legivel
    if "GALPAO" not in doc.dimstyles:
        ds = doc.dimstyles.add("GALPAO")
        ds.dxf.dimtxt = 90      # altura do texto de cota (mm)
        ds.dxf.dimasz = 90      # tamanho da seta
        ds.dxf.dimexe = 40
        ds.dxf.dimexo = 40
        ds.dxf.dimtad = 1       # texto acima da linha


def _txt(msp, s, p, h=120, layer="TEXTO", align="LEFT"):
    t = msp.add_text(s, height=h, dxfattribs={"layer": layer})
    try:
        t.set_placement(p, align=ezdxf.enums.TextEntityAlignment[align])
    except Exception:
        t.dxf.insert = p
    return t


def _poly(msp, pts, layer="ACO", closed=True):
    msp.add_lwpolyline([(x, y) for x, y in pts], close=closed,
                       dxfattribs={"layer": layer})


def _line(msp, a, b, layer="ACO"):
    msp.add_line(a, b, dxfattribs={"layer": layer})


def _cota_h(msp, x1, x2, y, txt=None, off=-350):
    d = msp.add_linear_dim(base=(0, y + off), p1=(x1, y), p2=(x2, y),
                           dimstyle="GALPAO", text=txt or "<>",
                           dxfattribs={"layer": "COTAS"})
    d.render()


def _cota_v(msp, y1, y2, x, txt=None, off=-350):
    d = msp.add_linear_dim(base=(x + off, 0), p1=(x, y1), p2=(x, y2),
                           angle=90, dimstyle="GALPAO", text=txt or "<>",
                           dxfattribs={"layer": "COTAS"})
    d.render()


def _perf_rect(msp, p1, p2, depth, layer="ACO"):
    """Membro como retangulo de profundidade 'depth' ao longo de p1->p2 (contorno
    do perfil na vista)."""
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return
    nx, ny = -dy / L * depth / 2.0, dx / L * depth / 2.0
    _poly(msp, [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
                (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], layer=layer)


# ---- VISTA 1: PORTICO TRANSVERSAL (plano Y-Z) ------------------------------
def _portico(msp, d, ox, oy):
    span, eave, ridge = d["span"], d["eave"], d["ridge"]
    dc, dr = d["col_d"], d["raf_d"]
    B = d["base"]
    bl, bt = B["L"], B["t"]

    def P(y, z):
        return (ox + y, oy + z)

    # colunas (contorno do perfil, profundidade dc)
    _perf_rect(msp, P(0, 0), P(0, eave), dc)
    _perf_rect(msp, P(span, 0), P(span, eave), dc)
    # vigas (duas aguas)
    _perf_rect(msp, P(0, eave), P(span / 2.0, ridge), dr)
    _perf_rect(msp, P(span, eave), P(span / 2.0, ridge), dr)
    # misulas (joelho) - triangulo sob a viga
    hl = 800.0
    for sgn, y0 in ((1, 0.0), (-1, span)):
        yb = y0 + sgn * hl
        zc = eave + (ridge - eave) / (span / 2.0) * min(hl, span / 2.0)
        _poly(msp, [P(y0, eave - dr / 2.0), P(y0, eave - dr / 2.0 - 450),
                    P(yb, zc - dr / 2.0)], layer="ACO")
    # eixos das colunas (linha de eixo)
    _line(msp, P(0, -700), P(0, eave + 300), "EIXOS")
    _line(msp, P(span, -700), P(span, eave + 300), "EIXOS")
    _line(msp, P(span / 2.0, eave), P(span / 2.0, ridge + 400), "EIXOS")
    # placas de base (largura L na direcao Y, espessura t)
    for y0 in (0.0, span):
        _poly(msp, [P(y0 - bl / 2.0, 0), P(y0 + bl / 2.0, 0),
                    P(y0 + bl / 2.0, -bt), P(y0 - bl / 2.0, -bt)], layer="BASE")
        # chumbadores (tracos verticais)
        gy = bl / 2.0 - 60.0
        ys = [-gy, 0.0, gy] if B["n"] >= 6 else [-gy, gy]
        for yy in ys:
            _line(msp, P(y0 + yy, 20), P(y0 + yy, -bt - 120), "FURACAO")
    # cotas
    _cota_h(msp, ox, ox + span, oy, txt=f"{span/1000:.2f} m (vao)".replace(".", ","),
            off=-1200)
    _cota_v(msp, oy, oy + eave, ox, txt=f"{eave/1000:.2f}".replace(".", ","),
            off=-900)
    _cota_v(msp, oy + eave, oy + ridge, ox + span + 900,
            txt=f"+{(ridge-eave)/1000:.2f}".replace(".", ","), off=300)
    # rotulos de perfil
    _txt(msp, d["perfil_col"], P(-dc - 550, eave / 2.0), h=150)
    _txt(msp, d["perfil_raf"], P(span / 4.0 - 300, (eave + ridge) / 2.0 + 250), h=150)
    _txt(msp, f"Base {B['B']:.0f}x{B['L']:.0f}x{B['t']:.0f} - "
              f"{B['n']} chumb. d{B['db']:.0f}", P(-dc - 550, -bt - 700), h=140)
    _txt(msp, "PORTICO TRANSVERSAL", P(span / 2.0 - 1400, -bt - 1500), h=220)


# ---- VISTA 2: ELEVACAO LONGITUDINAL (plano X-Z) ----------------------------
def _elev_long(msp, d, ox, oy):
    comp, eave = d["comprimento"], d["eave"]
    bay, dc = d["bay"], d["col_d"]
    xs = d["frame_x"]

    def P(x, z):
        return (ox + x, oy + z)

    # colunas em cada portico
    for x in xs:
        _perf_rect(msp, P(x, 0), P(x, eave), dc)
    # linha do beiral
    _line(msp, P(0, eave), P(comp, eave), "ACO")
    # contraventamento X nos vaos de extremidade
    for (x0, x1) in ((xs[0], xs[1]), (xs[-2], xs[-1])):
        _line(msp, P(x0, 0), P(x1, eave), "CONTRAV")
        _line(msp, P(x1, 0), P(x0, eave), "CONTRAV")
    # placas de base
    for x in xs:
        _line(msp, P(x - 250, 0), P(x + 250, 0), "BASE")
    # cotas dos vaos
    for i in range(len(xs) - 1):
        _cota_h(msp, ox + xs[i], ox + xs[i + 1], oy, off=-900)
    _cota_v(msp, oy, oy + eave, ox - 200, txt=f"{eave/1000:.2f}".replace(".", ","),
            off=-900)
    _txt(msp, "ELEVACAO LONGITUDINAL", P(comp / 2.0 - 1600, -2200), h=220)


# ---- VISTA 3: PLANTA DE COBERTURA (plano X-Y) ------------------------------
def _planta(msp, d, ox, oy):
    comp, span = d["comprimento"], d["span"]
    xs = d["frame_x"]

    def P(x, y):
        return (ox + x, oy + y)

    # contorno da cobertura
    _poly(msp, [P(0, 0), P(comp, 0), P(comp, span), P(0, span)], layer="ACO")
    # cumeeira (meio)
    _line(msp, P(0, span / 2.0), P(comp, span / 2.0), "EIXOS")
    # porticos (linhas transversais)
    for x in xs:
        _line(msp, P(x, 0), P(x, span), "EIXOS")
    # tercas (longitudinais) - 3 por agua
    for k in range(1, 3):
        yl = span / 2.0 * k / 3.0
        _line(msp, P(0, yl), P(comp, yl), "ACO")
        _line(msp, P(0, span - yl), P(comp, span - yl), "ACO")
    _line(msp, P(0, 0), P(comp, 0), "ACO")
    _line(msp, P(0, span), P(comp, span), "ACO")
    # contraventamento de cobertura (X) nos vaos de extremidade
    for (x0, x1) in ((xs[0], xs[1]), (xs[-2], xs[-1])):
        _line(msp, P(x0, 0), P(x1, span), "CONTRAV")
        _line(msp, P(x1, 0), P(x0, span), "CONTRAV")
    _cota_h(msp, ox, ox + comp, oy, txt=f"{comp/1000:.2f} m".replace(".", ","),
            off=-900)
    _cota_v(msp, oy, oy + span, ox - 200, txt=f"{span/1000:.2f}".replace(".", ","),
            off=-900)
    _txt(msp, "PLANTA DE COBERTURA", P(comp / 2.0 - 1400, -2200), h=220)


# ---- LEGENDA / CARIMBO -----------------------------------------------------
def _legenda(msp, d, ox, oy):
    w, h = 6000.0, 2400.0
    _poly(msp, [(ox, oy), (ox + w, oy), (ox + w, oy + h), (ox, oy + h)], layer="TEXTO")
    linhas = [
        f"PROJETO: {d.get('slug','galpao')}",
        d.get("descricao", ""),
        f"Vao {d['span']/1000:.1f} m x Comp {d['comprimento']/1000:.1f} m x "
        f"Pe-direito {d['eave']/1000:.1f} m".replace(".", ","),
        f"Colunas {d['perfil_col']} | Vigas {d['perfil_raf']}",
        f"Base {d['base']['B']:.0f}x{d['base']['L']:.0f}x{d['base']['t']:.0f} mm - "
        f"{d['base']['n']} chumbadores d{d['base']['db']:.0f} mm",
        "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
    ]
    for i, s in enumerate(linhas):
        _txt(msp, s, (ox + 150, oy + h - 350 - i * 360), h=150 if i else 200)


def gerar_dxf(design, path):
    """design: dict com span/comprimento/eave/ridge/slope/bay (mm), frame_x (lista),
    col_d/raf_d (mm), perfil_col/perfil_raf (str), base {B,L,t,db,n} (mm), slug,
    descricao. Escreve o DXF em 'path'."""
    doc = ezdxf.new("R2010", setup=True)
    _setup(doc)
    msp = doc.modelspace()
    span, comp = design["span"], design["comprimento"]
    # layout das vistas em modelspace (offsets), com folga
    _portico(msp, design, ox=0.0, oy=0.0)
    _elev_long(msp, design, ox=span + 6000.0, oy=0.0)
    _planta(msp, design, ox=span + 6000.0, oy=-(design["eave"] + 6000.0))
    _legenda(msp, design, ox=0.0, oy=-(design["eave"] + 6000.0))
    doc.saveas(path)
    return path


def design_de_spec(spec):
    """Monta o 'design' do DXF a partir do spec (com perfil/base ADOTADOS no
    calculo). Requer que calcular() ja tenha rodado (estrutura preenchida)."""
    import perfis
    g = spec["geometria"]
    est = spec.get("estrutura", {})
    col_nome = est.get("perfil_col_adotado", "HEA200")
    raf_nome = est.get("perfil_raf_adotado", "HEA180")
    ba = est.get("base_adotada", {"B": 0.45, "L": 0.55, "t": 0.04, "db": 0.02, "n": 4})
    span = g["span"] * 1000.0
    comp = g["comprimento"] * 1000.0
    eave = g["eave"] * 1000.0
    slope = spec["cobertura"]["slope"]
    ridge = eave + slope * span / 2.0
    bay = g["bay"] * 1000.0
    n = int(round(comp / bay))
    return {
        "slug": spec.get("slug", "galpao"), "descricao": spec.get("descricao", ""),
        "span": span, "comprimento": comp, "eave": eave, "ridge": ridge,
        "slope": slope, "bay": bay, "frame_x": [i * bay for i in range(n + 1)],
        "col_d": perfis.PERFIS[col_nome]["d"] * 1000.0,
        "raf_d": perfis.PERFIS[raf_nome]["d"] * 1000.0,
        "perfil_col": col_nome, "perfil_raf": raf_nome,
        "base": {"B": ba["B"] * 1000.0, "L": ba["L"] * 1000.0,
                 "t": ba["t"] * 1000.0, "db": ba["db"] * 1000.0, "n": ba["n"]},
    }
