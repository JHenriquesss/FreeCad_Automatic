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


# ---- camadas (nome, ACI index, linetype) ------------------------------------
# ACI (AutoCAD Color Index) para compatibilidade com TODOS os visualizadores
# incluindo FreeCAD (que ignora RGB true color). Cores definidas por funcao
# padrao do DXF -> visiveis em fundo branco E preto.
CAMADAS = [
    ("EIXOS", 8, "CENTER"),          # eixos (cinza escuro ACI 8)
    ("ACO", 7, "CONTINUOUS"),        # perfis metalicos (preto/branco ACI 7)
    ("BASE", 6, "CONTINUOUS"),       # placas de base (magenta ACI 6)
    ("FURACAO", 1, "CONTINUOUS"),    # chumbadores/parafusos (vermelho ACI 1)
    ("COTAS", 3, "CONTINUOUS"),      # dimensoes (verde ACI 3)
    ("TEXTO", 7, "CONTINUOUS"),      # textos (preto/branco ACI 7)
    ("CONTRAV", 5, "DASHED"),        # contraventamento (azul ACI 5)
    ("TELHA", 9, "CONTINUOUS"),      # telha/terca (cinza claro ACI 9)
    ("CONCRETO", 4, "CONTINUOUS"),   # concreto/fundacao (ciano ACI 4)
    ("ARMADURA", 1, "CONTINUOUS"),   # armadura (vermelho ACI 1)
]


def _setup(doc):
    for nome, aci, lt in CAMADAS:
        ly = doc.layers.add(nome)
        ly.color = aci
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


def _bolha(msp, p, label, r=400):
    """Bolha de eixo (circulo + rotulo centrado)."""
    msp.add_circle(p, r, dxfattribs={"layer": "EIXOS"})
    t = msp.add_text(str(label), height=r * 0.85, dxfattribs={"layer": "TEXTO"})
    try:
        t.set_placement(p, align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    except Exception:
        t.dxf.insert = (p[0] - r / 2, p[1] - r / 2)


def _nivel(msp, p, texto, s=180):
    """Simbolo de nivel (triangulo) + cota de elevacao."""
    x, y = p
    _poly(msp, [(x, y), (x - s, y + s), (x + s, y + s)], layer="COTAS")
    _txt(msp, texto, (x + s + 100, y + s - 40), h=170, layer="COTAS")


def _circ(msp, p, r, layer="FURACAO"):
    msp.add_circle(p, r, dxfattribs={"layer": layer})


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
    nv = d.get("n_vaos", 1)
    cols = d.get("col_ys", [0.0, d["span"]])
    ridges = d.get("ridge_ys", [d["span"] / 2.0])
    eave, ridge0 = d["eave"], d["ridge"]
    dc, dr = d["col_d"], d["raf_d"]
    B = d["base"]
    bl, bt = B["L"], B["t"]
    span_total = cols[-1]

    def P(y, z):
        return (ox + y, oy + z)

    def _z_ridge(y):
        for j in range(nv):
            c0, c1 = cols[j], cols[j + 1]
            if c0 - 1 <= y <= c1 + 1:
                rj = ridges[j]
                if y <= rj:
                    return eave + (d["ridges"][j] - eave) / (rj - c0) * (y - c0)
                else:
                    return eave + (d["ridges"][j] - eave) / (c1 - rj) * (c1 - y)
        return eave

    # Colunas (N+1)
    for yc in cols:
        _perf_rect(msp, P(yc, 0), P(yc, eave), dc)
    # Vigas (2 por vao)
    for j in range(nv):
        y0, y1 = cols[j], cols[j + 1]; rj = ridges[j]; zj = d["ridges"][j]
        _perf_rect(msp, P(y0, eave), P(rj, zj), dr)
        _perf_rect(msp, P(y1, eave), P(rj, zj), dr)
    # Misulas (joelho) em cada coluna
    hl = 800.0
    for yc in cols:
        if yc == cols[0]:
            yb = yc + hl; zc = _z_ridge(yb)
            _poly(msp, [P(yc, eave - dr / 2.0), P(yc, eave - dr / 2.0 - 450),
                        P(yb, zc - dr / 2.0)], layer="ACO")
        elif yc == cols[-1]:
            yb = yc - hl; zc = _z_ridge(yb)
            _poly(msp, [P(yc, eave - dr / 2.0), P(yc, eave - dr / 2.0 - 450),
                        P(yb, zc - dr / 2.0)], layer="ACO")
        else:
            for sgn in (+1, -1):
                yb = yc + sgn * hl; zc = _z_ridge(yb)
                _poly(msp, [P(yc, eave - dr / 2.0), P(yc, eave - dr / 2.0 - 450),
                            P(yb, zc - dr / 2.0)], layer="ACO")
    # Tercas + telha por vao
    nt = 3
    ys_t = list(cols)
    for j in range(nv):
        rj = ridges[j]
        ys_t.append(rj)
        for k in range(1, nt):
            ys_t.append(cols[j] + (rj - cols[j]) * k / nt)
            ys_t.append(cols[j + 1] - (cols[j + 1] - rj) * k / nt)
    for y in set(ys_t):
        z = _z_ridge(y) + dr / 2.0 + 90.0
        _poly(msp, [P(y - 90, z - 90), P(y + 90, z - 90),
                    P(y + 90, z + 90), P(y - 90, z + 90)], layer="TELHA")
    tz = dr / 2.0 + 240.0
    for j in range(nv):
        y0, y1 = cols[j], cols[j + 1]; rj = ridges[j]; zj = d["ridges"][j]
        _line(msp, P(y0, eave + tz), P(rj, zj + tz), "TELHA")
        _line(msp, P(y1, eave + tz), P(rj, zj + tz), "TELHA")
    # Eixos de colunas + bolhas (letras A, B, C...)
    for i, yc in enumerate(cols):
        lbl = chr(65 + i) if i < 26 else f"X{i}"
        _line(msp, P(yc, -700), P(yc, eave + 500), "EIXOS")
        _bolha(msp, P(yc, eave + 900), lbl)
    # Eixos de cumeeiras
    for rj in ridges:
        zj = _z_ridge(rj)
        _line(msp, P(rj, eave), P(rj, zj + 400), "EIXOS")
    # Niveis
    _nivel(msp, P(-dc / 2.0 - 250, 0), "+0,00")
    _nivel(msp, P(-dc / 2.0 - 250, eave), f"+{eave/1000:.2f}".replace(".", ","))
    for j in range(nv):
        _nivel(msp, P(ridges[j] + 250, d['ridges'][j]),
               f"+{d['ridges'][j]/1000:.2f}".replace(".", ","))
    # Placas de base (N+1)
    for yc in cols:
        _poly(msp, [P(yc - bl / 2.0, 0), P(yc + bl / 2.0, 0),
                    P(yc + bl / 2.0, -bt), P(yc - bl / 2.0, -bt)], layer="BASE")
        gy = bl / 2.0 - 60.0
        ys_c = [-gy, 0.0, gy] if B["n"] >= 6 else [-gy, gy]
        for yy in ys_c:
            _line(msp, P(yc + yy, 20), P(yc + yy, -bt - 120), "FURACAO")
    # Cotas horizontais (cada vao)
    for j in range(nv):
        _cota_h(msp, ox + cols[j], ox + cols[j + 1], oy,
                txt=f"{d['spans'][j]/1000:.2f} m".replace(".", ","), off=-1200)
    _cota_v(msp, oy, oy + eave, ox, txt=f"{eave/1000:.2f}".replace(".", ","), off=-900)
    _cota_v(msp, oy + eave, oy + d['ridges'][-1], ox + span_total + 900,
            txt=f"+{(d['ridges'][-1]-eave)/1000:.2f}".replace(".", ","), off=300)
    # Rotulos
    _txt(msp, d["perfil_col"], P(-dc - 550, eave / 2.0), h=150)
    _txt(msp, d["perfil_raf"], P(cols[0] + 300, (eave + d['ridges'][0]) / 2.0 + 250), h=150)
    _txt(msp, f"Base {B['B']:.0f}x{B['L']:.0f}x{B['t']:.0f} - "
              f"{B['n']} chumb. d{B['db']:.0f}", P(-dc - 550, -bt - 700), h=140)
    _txt(msp, f"PORTICO TRANSVERSAL ({nv} vao(s))", P(span_total / 2.0 - 1600, -bt - 1500), h=220)
    # Chamadas de detalhe (círculos numerados)
    for yc, tag, texto in ((cols[0], "1", "DET. JOELHO"),
                            (cols[0], "2", "DET. BASE"),
                            (ridges[0] if ridges else cols[0], "3", "DET. TERCA"),
                            (cols[0] + span_total / 4, "4", "DET. CONTRAV"),
                            (cols[-1], "5", "DET. CALHA")):
        _circ(msp, P(yc - 250, eave - 500), 300, layer="TEXTO")
        _txt(msp, tag, P(yc - 280, eave - 590), h=250, layer="TEXTO", align="MIDDLE_CENTER")


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
    # eixos numerados (bolhas 1..n) e cotas dos vaos
    for i, x in enumerate(xs, start=1):
        _line(msp, P(x, 0), P(x, -1050), "EIXOS")
        _bolha(msp, P(x, -1450), i)
    for i in range(len(xs) - 1):
        _cota_h(msp, ox + xs[i], ox + xs[i + 1], oy, off=-600)
    _cota_v(msp, oy, oy + eave, ox - 200, txt=f"{eave/1000:.2f}".replace(".", ","),
            off=-900)
    _txt(msp, "ELEVACAO LONGITUDINAL", P(comp / 2.0 - 1600, -2400), h=220)
    # Indicador de corte A-A na elevação
    mx = comp / 2.0
    _line(msp, P(mx, -300), P(mx, eave + 500), "TEXTO")
    _line(msp, P(mx - 200, -300), P(mx + 200, -300), "TEXTO")
    _txt(msp, "CORTE A-A", P(mx + 300, eave + 200), h=160, layer="TEXTO")


# ---- VISTA 3: PLANTA DE COBERTURA (plano X-Y) ------------------------------
def _planta(msp, d, ox, oy):
    nv = d.get("n_vaos", 1)
    cols = d.get("col_ys", [0.0, d["span"]])
    ridges = d.get("ridge_ys", [d["span"] / 2.0])
    span_total = cols[-1]
    comp = d["comprimento"]
    xs = d["frame_x"]

    def P(x, y):
        return (ox + x, oy + y)

    _poly(msp, [P(0, 0), P(comp, 0), P(comp, span_total), P(0, span_total)], layer="ACO")
    for rj in ridges:
        _line(msp, P(0, rj), P(comp, rj), "EIXOS")
    for x in xs:
        _line(msp, P(x, 0), P(x, span_total), "EIXOS")
    nt = 3
    for j in range(nv):
        y0, y1 = cols[j], cols[j + 1]; rj = ridges[j]
        for k in range(1, nt):
            yl = y0 + (rj - y0) * k / nt
            _line(msp, P(0, yl), P(comp, yl), "ACO")
            yr = y1 - (y1 - rj) * k / nt
            _line(msp, P(0, yr), P(comp, yr), "ACO")
    _line(msp, P(0, cols[0]), P(comp, cols[0]), "ACO")
    _line(msp, P(0, cols[-1]), P(comp, cols[-1]), "ACO")
    for (x0, x1) in ((xs[0], xs[1]), (xs[-2], xs[-1])):
        _line(msp, P(x0, cols[0]), P(x1, cols[-1]), "CONTRAV")
        _line(msp, P(x1, cols[0]), P(x0, cols[-1]), "CONTRAV")
    for i, x in enumerate(xs, start=1):
        _bolha(msp, P(x, span_total + 900), i)
    _bolha(msp, P(-900, 0), "A")
    _bolha(msp, P(-900, span_total), "B")
    _cota_h(msp, ox, ox + comp, oy, txt=f"{comp/1000:.2f} m".replace(".", ","),
            off=-900)
    _cota_v(msp, oy, oy + span_total, ox - 200,
            txt=f"{span_total/1000:.2f}".replace(".", ","), off=-900)
    _txt(msp, "PLANTA DE COBERTURA", P(comp / 2.0 - 1400, -2200), h=220)
    # Linha de corte A-A com setas nas extremidades
    cy = span_total / 2.0
    _line(msp, P(-500, cy), P(comp + 500, cy), "TEXTO")
    _line(msp, P(-500, cy), P(-300, cy + 300), "TEXTO")
    _line(msp, P(-500, cy), P(-300, cy - 300), "TEXTO")
    _txt(msp, "A", P(-600, cy + 400), h=200, layer="TEXTO")
    _line(msp, P(comp + 500, cy), P(comp + 300, cy + 300), "TEXTO")
    _line(msp, P(comp + 500, cy), P(comp + 300, cy - 300), "TEXTO")
    _txt(msp, "A", P(comp + 500, cy + 400), h=200, layer="TEXTO")
    # Chamadas de detalhe na planta
    for x, texto in ((comp / 4, "DET. 1 - JOELHO"), (comp * 3 / 4, "DET. 2 - BASE"),
                     (comp / 2, "DET. 3 - TERCA"), (comp / 5, "DET. 4 - CONTRAV"),
                     (comp * 4 / 5, "DET. 5 - CALHA")):
        _txt(msp, texto, P(x, span_total + 1400), h=130, layer="TEXTO")


# ---- DETALHE DO JOELHO (ampliado) ------------------------------------------
def _detalhe_joelho(msp, d, ox, oy):
    dc, dr = d["col_d"], d["raf_d"]
    ang = math.atan(d["slope"])
    ux, uy = math.cos(ang), math.sin(ang)          # direcao da viga
    nx, ny = -uy, ux                               # normal a viga

    def P(x, y):
        return (ox + x, oy + y)

    Hc = 1400.0
    _poly(msp, [P(0, 0), P(dc, 0), P(dc, Hc), P(0, Hc)])    # coluna
    bx, by = dc / 2.0, Hc                          # eixo da viga no topo da coluna
    Lr = 1900.0
    A = (bx + nx * dr / 2, by + ny * dr / 2)
    B = (bx + ux * Lr + nx * dr / 2, by + uy * Lr + ny * dr / 2)
    C = (bx + ux * Lr - nx * dr / 2, by + uy * Lr - ny * dr / 2)
    E = (bx - nx * dr / 2, by - ny * dr / 2)
    _poly(msp, [P(*A), P(*B), P(*C), P(*E)])       # viga
    # misula (haunch): da face inferior da viga descendo no no
    hl, hd = 900.0, 450.0
    Fi = (bx - nx * dr / 2, by - ny * dr / 2)
    Fo = (bx + ux * hl - nx * dr / 2, by + uy * hl - ny * dr / 2)
    Fb = (Fi[0] - nx * hd, Fi[1] - ny * hd)
    _poly(msp, [P(*Fi), P(*Fb), P(*Fo)])
    # chapa de topo (splice) + 4 parafusos
    sx, sy = bx + ux * hl, by + uy * hl
    pdepth = dr + 40.0
    P1 = (sx + nx * pdepth / 2, sy + ny * pdepth / 2)
    P2 = (sx - nx * pdepth / 2 - nx * hd, sy - ny * pdepth / 2 - ny * hd)
    _line(msp, P(sx + nx * (pdepth / 2), sy + ny * (pdepth / 2)),
          P(sx - nx * (pdepth / 2 + hd), sy - ny * (pdepth / 2 + hd)), "ACO")
    for f in (0.3, 0.7):
        cx = sx - nx * (pdepth * (f - 0.5) + 0)
        cy = sy - ny * (pdepth * (f - 0.5))
        _circ(msp, P(sx + nx * pdepth * (0.35 - f), sy + ny * pdepth * (0.35 - f)), 55)
        _circ(msp, P(sx + nx * pdepth * (0.35 - f) - nx * hd,
                     sy + ny * pdepth * (0.35 - f) - ny * hd), 55)
    # enrijecedor no pilar
    _line(msp, P(0, Hc - 120), P(dc, Hc - 120), "ACO")
    _txt(msp, "DETALHE DO JOELHO", P(0, -450), h=200)
    j = d.get("joelho")
    sub = (f"misula + chapa {j['t']*1000:.0f} mm + {j['n']} paraf. d{j['db']*1000:.0f} "
           f"mm + enrijecedor" if j else
           "misula + chapa de topo + parafusos + enrijecedor")
    _txt(msp, sub, P(0, -750), h=140)


# ---- DETALHE DA BASE (planta + corte) --------------------------------------
def _detalhe_base(msp, d, ox, oy):
    B = d["base"]
    Bp, Lp, tp, db, n = B["B"], B["L"], B["t"], B["db"], B["n"]
    dc, bf = d["col_d"], d.get("col_bf", d["col_d"])
    gx, gy = Bp / 2.0 - 60.0, Lp / 2.0 - 60.0
    ys = [-gy, 0.0, gy] if n >= 6 else [-gy, gy]

    def P(x, y):
        return (ox + x, oy + y)

    # ---- PLANTA da base ----
    _poly(msp, [P(-Bp / 2, -Lp / 2), P(Bp / 2, -Lp / 2),
                P(Bp / 2, Lp / 2), P(-Bp / 2, Lp / 2)], layer="BASE")
    _poly(msp, [P(-dc / 2, -bf / 2), P(dc / 2, -bf / 2),
                P(dc / 2, bf / 2), P(-dc / 2, bf / 2)], layer="ACO")   # pilar
    for xx in (-gx, gx):
        for yy in ys:
            _circ(msp, P(xx, yy), db / 2.0 + 6.0)
    _cota_h(msp, ox - Bp / 2, ox + Bp / 2, oy - Lp / 2, off=-450)
    _cota_v(msp, oy - Lp / 2, oy + Lp / 2, ox - Bp / 2, off=-450)
    _txt(msp, "PLANTA DA BASE", P(-Bp / 2, Lp / 2 + 200), h=180)
    # ---- CORTE da base (deslocado abaixo) ----
    oy2 = oy - Lp / 2 - 2200.0
    def Q(x, z):
        return (ox + x, oy2 + z)
    _poly(msp, [Q(-Lp / 2, 0), Q(Lp / 2, 0), Q(Lp / 2, tp), Q(-Lp / 2, tp)],
          layer="BASE")                                     # placa (corte em Y)
    _poly(msp, [Q(-dc / 2, tp), Q(dc / 2, tp), Q(dc / 2, tp + 900),
                Q(-dc / 2, tp + 900)], layer="ACO")         # arranque do pilar
    for yy in ys:
        _line(msp, Q(yy, tp + 700), Q(yy, -350), "FURACAO")  # chumbador
        _line(msp, Q(yy, -350), Q(yy - 90, -350), "FURACAO")  # gancho
    _poly(msp, [Q(dc / 2, tp), Q(dc / 2 + 240, tp), Q(dc / 2, tp + 500)], layer="ACO")  # nervura
    _cota_v(msp, oy2, oy2 + tp, ox - Lp / 2 - 200,
            txt=f"{tp:.0f}".replace(".", ","), off=-250)
    _txt(msp, f"CORTE - chapa {tp:.0f} mm ; {n} chumb. d{db:.0f}",
         Q(-Lp / 2, -800), h=160)
    # ---- SAPATA (fundacao) sob a base: bloco + pedestal + nota de armadura ----
    sap = d.get("sapata")
    if sap:
        sL, sh = sap["L"], sap["h"]
        pd = max(dc + 200.0, 300.0)                 # pedestal (dim // L)
        zt = -350.0                                 # topo da sapata (abaixo dos ganchos)
        zb = zt - sh
        _poly(msp, [Q(-sL / 2, zt), Q(sL / 2, zt), Q(sL / 2, zb), Q(-sL / 2, zb)],
              layer="BASE")                         # bloco da sapata (corte)
        _poly(msp, [Q(-pd / 2, tp), Q(pd / 2, tp), Q(pd / 2, zt), Q(-pd / 2, zt)],
              layer="BASE")                         # pedestal
        # armadura de flexao (malha inferior) - representacao
        x0, x1 = -sL / 2 + 60, sL / 2 - 60
        for i in range(7):
            xx = x0 + (x1 - x0) * i / 6.0
            _circ(msp, Q(xx, zb + 60), 12.0, layer="FURACAO")
        _line(msp, Q(-sL / 2 + 60, zb + 60), Q(sL / 2 - 60, zb + 60), "FURACAO")
        _cota_v(msp, oy2 + zb, oy2 + zt, ox - sL / 2 - 200,
                txt=f"{sh:.0f}".replace(".", ","), off=-250)
        _cota_h(msp, ox - sL / 2, ox + sL / 2, oy2 + zb, off=-450)
        _txt(msp, f"SAPATA {sap['B']/1000:.2f}x{sap['L']/1000:.2f}x{sh/1000:.2f} m"
                  f" ({'RIGIDA' if sap['rigida'] else 'FLEXIVEL'})".replace(".", ","),
             Q(-sL / 2, zb - 350), h=160)
        arm = (f"Arm. flexao: L={sap['arm_L']} mm ; B={sap['arm_B']} mm (NBR 6118)"
               if sap.get("arm_L") else
               f"Arm. flexao: As_L={sap['As_L']:.1f} ; As_B={sap['As_B']:.1f} cm2 (NBR 6118)")
        _txt(msp, arm.replace(".", ","), Q(-sL / 2, zb - 620), h=140)
        q = d.get("sapata_quant")
        if q:
            _txt(msp, (f"Quant.: {q['n']} sapatas ; concreto {q['vol_conc_tot']:.1f} m3 ; "
                       f"aco {q['massa_aco_tot']:.0f} kg (taxa {q['taxa_aco']:.0f} kg/m3)")
                 .replace(".", ","), Q(-sL / 2, zb - 760), h=140)
        _txt(msp, "DETALHE DA BASE + SAPATA", Q(-sL / 2, zb - 1080), h=200)
    else:
        _txt(msp, "DETALHE DA BASE", P(-Bp / 2, -Lp / 2 - 1400), h=200)


# ---- TABELAS (quadros) -----------------------------------------------------
def _tabela(msp, ox, oy, titulo, header, rows, wcol, rh=430):
    W = sum(wcol)
    nlin = len(rows) + 1
    _txt(msp, titulo, (ox, oy + 200), h=190)
    for i in range(nlin + 1):
        y = oy - i * rh
        _line(msp, (ox, y), (ox + W, y), "TEXTO")
    xs, x = [ox], ox
    for w in wcol:
        x += w
        xs.append(x)
    for xv in xs:
        _line(msp, (xv, oy), (xv, oy - nlin * rh), "TEXTO")

    def _cell(r, c, s):
        _txt(msp, str(s), (xs[c] + 90, oy - (r + 1) * rh + 130), h=150)
    for c, hh in enumerate(header):
        _cell(0, c, hh)
    for ri, row in enumerate(rows, start=1):
        for c, v in enumerate(row):
            _cell(ri, c, v)


def _quadro_verif(msp, d, ox, oy):
    rows = []
    for nome, u in (d.get("resultados") or {}).items():
        if u is None:
            continue
        situ = "OK" if u <= 1.001 else "REVER"
        rows.append([nome, f"{u:.2f}".replace(".", ","), situ])
    if not rows:
        return
    _tabela(msp, ox, oy, "QUADRO DE VERIFICACOES",
            ["Elemento", "util", "situacao"], rows, [2700, 900, 1200])


def _quadro_materiais(msp, d, ox, oy):
    rows, total = [], 0.0
    for g in (d.get("takeoff") or []):
        cat, prof, cnt, comp, massa = g[0], g[1], g[2], g[3], g[4]
        if "Alvenaria" in cat:
            continue
        rows.append([cat, prof, str(cnt), f"{comp:.1f}".replace(".", ","),
                     f"{massa:.0f}"])
        total += massa
    if not rows:
        return
    rows.append(["TOTAL ACO", "", "", "", f"{total:.0f}"])
    _tabela(msp, ox, oy, "QUADRO DE MATERIAIS (aco)",
            ["Item", "Perfil", "Qtd", "Comp (m)", "Massa (kg)"], rows,
            [3400, 1600, 700, 1200, 1400])


# ---- LEGENDA / CARIMBO -----------------------------------------------------
def _legenda(msp, d, ox, oy):
    w, h = 7000.0, 3200.0
    _poly(msp, [(ox, oy), (ox + w, oy), (ox + w, oy + h), (ox, oy + h)], layer="TEXTO")
    import datetime
    data = datetime.date.today().strftime("%d/%m/%Y")
    sap = d.get("sapata")
    linhas = [
        f"PROJETO: {d.get('slug','galpao')}",
        d.get("descricao", "") or "Galpao em aco - Projeto Estrutural",
        f"Vao {d['span']/1000:.1f} m x Comp {d['comprimento']/1000:.1f} m x "
        f"Pe-direito {d['eave']/1000:.1f} m".replace(".", ","),
        f"Colunas {d['perfil_col']} | Vigas {d['perfil_raf']}",
        f"Base {d['base']['B']:.0f}x{d['base']['L']:.0f}x{d['base']['t']:.0f} mm - "
        f"{d['base']['n']} chumb. d{d['base']['db']:.0f} mm",
        (f"Sapata {sap['B']/1000:.2f}x{sap['L']/1000:.2f}x{sap['h']/1000:.2f} m"
         if sap else "Sapata: N/A").replace(".", ","),
        f"Data: {data}  |  Revisao: 00  |  Escala: 1:50 (portico) / 1:100 (demais)",
        "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
        "NBR 8800:2008  |  NBR 6123:1988  |  NBR 6118:2014  |  NBR 6122:2022",
    ]
    for i, s in enumerate(linhas):
        _txt(msp, s, (ox + 150, oy + h - 350 - i * 320), h=170 if i == 0 else 130)


# ---- NOTAS TECNICAS GERAIS --------------------------------------------------
def _notas_tecnicas(msp, d, ox, oy):
    w, h = 8000.0, 4000.0
    _poly(msp, [(ox, oy), (ox + w, oy), (ox + w, oy + h), (ox, oy + h)], "TEXTO")
    linhas = [
        "NOTAS TECNICAS GERAIS",
        "",
        "1. PROJETO CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.",
        "2. COTAS EM MILIMETROS (mm) SALVO INDICACAO EM CONTRARIO.",
        "3. RN: +0,00 = TOPO DO CONCRETO (BASE DAS PLACAS).",
        "4. ACO ESTRUTURAL: MR250 (fy=250 MPa, fu=400 MPa) NBR 8800.",
        "5. ACO ARMADURA: CA-50 (fyk=500 MPa) NBR 7480.",
        "6. CONCRETO: fck=25 MPa (NBR 6118). COBRIMENTO: 5 cm (fund.), 3 cm (superestrut.).",
        "7. PARAFUSOS: ASTM A325 (fub=825 MPa) ou A307 (fub=400 MPa) conforme indicado.",
        "8. SOLDAS: Eletrodo E70XX (fw=485 MPa). Filete min. 6 mm.",
        "9. CHUMBADORES: Aco ASTM A36, gancho 180 mm.",
        "10. CONTRAVENTAMENTO: Barras redondas pretensionadas d20 c/ esticadores.",
        "11. TERÇAS: Ue formado a frio (NBR 14762) - face aberta p/ o beiral.",
        "12. TAPAMENTO: Telha trapezoidal 0,65 mm parafusada nas terças/longarinas.",
        "13. MAO-FRANCESA: d16 mm a cada 2 terças (Lb da viga = 3,35 m).",
        "14. TOLERANCIAS: NBR 8800 Anexo N (fabricacao/montagem).",
        "15. TODAS AS LIGACOES DEVEM SER VERIFICADAS PELO ENGENHEIRO RESPONSAVEL.",
    ]
    for i, s in enumerate(linhas):
        _txt(msp, s, (ox + 150, oy + h - 350 - i * 220), h=180 if i == 0 else 130)


# ---- DETALHE TERÇA x VIGA --------------------------------------------------
def _detalhe_terca_viga(msp, d, ox, oy):
    dr = d["raf_d"]; bf = d.get("col_bf", dr)
    th = d.get("terca_dims", [200, 75, 0, 0])[0]; tb = d.get("terca_dims", [200, 75, 0, 0])[1]

    def P(x, y): return (ox + x, oy + y)
    _poly(msp, [P(-bf/2, 0), P(bf/2, 0), P(bf/2, dr), P(-bf/2, dr)], "ACO")
    _line(msp, P(0, 0), P(0, dr), "EIXOS")
    ty = dr + 30
    _poly(msp, [P(-tb/2, ty), P(tb/2, ty), P(tb/2, ty+th), P(-tb/2, ty+th)], "TELHA")
    _poly(msp, [P(-tb/2-15, dr), P(-tb/2-15, ty+20), P(-tb/2+5, ty+20)], "BASE")
    _circ(msp, P(-tb/2+30, dr+30), 6, "FURACAO")
    _cota_v(msp, oy, oy+dr, ox-bf/2-200, txt=f"{dr:.0f}".replace(".",","), off=-400)
    _txt(msp, f"Ue{th:.0f}x{tb:.0f}x25x2,65", P(-bf/2-200, ty+th/2-50), h=120)
    _txt(msp, f"CLIPE L 90x120x8 c/ 2 M12", P(tb/2+50, dr+100), h=120)
    _txt(msp, "DET. TERÇA x VIGA", P(-200, -500), h=180)


# ---- DETALHE TIRANTE / CONTRAVENTAMENTO ------------------------------------
def _detalhe_contraventamento(msp, d, ox, oy):
    def P(x, y): return (ox + x, oy + y)
    _poly(msp, [P(0, 0), P(250, 0), P(0, 250)], "ACO")
    for xx, yy in [(70, 70), (180, 70), (70, 180)]: _circ(msp, P(xx, yy), 11, "FURACAO")
    ang = math.radians(45); Lb = 600
    xb, yb = 250 + Lb*math.cos(ang), Lb*math.sin(ang)
    _line(msp, P(250, 0), P(xb, yb), "CONTRAV")
    xm, ym = (250+xb)/2, yb/2
    _poly(msp, [P(xm-60, ym-30), P(xm+60, ym-30), P(xm+60, ym+30), P(xm-60, ym+30)], "CONTRAV")
    _line(msp, P(xm-80, ym), P(xm+80, ym), "CONTRAV")
    _line(msp, P(0, -50), P(0, 300), "ACO")
    _txt(msp, "CH. GUSSET t=12 mm", P(10, -100), h=120)
    _txt(msp, "d20 mm (pretensionada)", P(300, yb/2-50), h=120)
    _txt(msp, "ESTICADOR M20", P(xm-80, ym-80), h=120)
    _txt(msp, "DET. CONTRAVENTAMENTO", P(0, -300), h=180)


# ---- DETALHE CALHA / FECHAMENTO LATERAL ------------------------------------
def _detalhe_calha_fechamento(msp, d, ox, oy):
    dr = d["raf_d"]; bf = d.get("col_bf", dr)
    def P(x, y): return (ox + x, oy + y)
    _poly(msp, [P(-bf/2, 0), P(bf/2, 0), P(bf/2, dr), P(-bf/2, dr)], "ACO")
    ch, cb = 300, 200
    _poly(msp, [P(-cb/2, dr), P(cb/2, dr), P(cb/2, dr+ch), P(-cb/2, dr+ch)], "TELHA")
    _line(msp, P(-cb/2+10, dr+20), P(cb/2-10, dr+20), "EIXOS")
    _txt(msp, "CALHA 200x300 mm", P(cb/2+50, dr+ch/2), h=120)
    fx, fh = bf/2+100, 600
    _line(msp, P(fx, dr), P(fx, dr+fh), "TELHA")
    _poly(msp, [P(fx+5, dr+fh/2-30), P(fx+60, dr+fh/2-30),
                P(fx+60, dr+fh/2+30), P(fx+5, dr+fh/2+30)], "ACO")
    _circ(msp, P(fx+20, dr+fh/2), 6, "FURACAO")
    _txt(msp, "TELHA TRAPEZOIDAL 0,65 mm", P(fx+5, dr+fh+100), h=110)
    _txt(msp, "LONGARINA UPE (girt)", P(fx+70, dr+fh/2-20), h=110)
    cx = -cb/2 - 50
    _line(msp, P(cx, dr), P(cx, -200), "FURACAO")
    _line(msp, P(cx-40, dr-100), P(cx+40, dr-100), "FURACAO")
    _txt(msp, "CONDUTOR d=100 mm", P(cx-150, -100), h=110)
    _txt(msp, "DET. CALHA + FECHAMENTO", P(-bf/2-50, -500), h=180)


# ---- PLANTA DE FUNDACOES ----------------------------------------------------
def _planta_fundacoes(msp, d, ox, oy):
    xs = d["frame_x"]; nv = d.get("n_vaos", 1)
    cols = d.get("col_ys", [0.0, d["span"]]); sap = d.get("sapata")
    comp = d["comprimento"]; span = cols[-1]
    def P(x, y): return (ox + x, oy + y)
    # Contorno da edificacao
    _poly(msp, [P(0, 0), P(comp, 0), P(comp, span), P(0, span)], "EIXOS")
    for x in xs:
        _line(msp, P(x, 0), P(x, span), "EIXOS")
    for yc in cols:
        _line(msp, P(0, yc), P(comp, yc), "EIXOS")
    # Sapatas
    if sap:
        sB, sL = sap["B"], sap["L"]
        for x in xs:
            for yc in cols:
                _poly(msp, [P(x-sB/2, yc-sL/2), P(x+sB/2, yc-sL/2),
                            P(x+sB/2, yc+sL/2), P(x-sB/2, yc+sL/2)], "CONCRETO")
                _line(msp, P(x-sB/2+40, yc-sL/2+40), P(x+sB/2-40, yc-sL/2+40), "ARMADURA")
                _line(msp, P(x-sB/2+40, yc+sL/2-40), P(x+sB/2-40, yc+sL/2-40), "ARMADURA")
                _line(msp, P(x-sB/2+40, yc-sL/2+40), P(x-sB/2+40, yc+sL/2-40), "ARMADURA")
                _line(msp, P(x+sB/2-40, yc-sL/2+40), P(x+sB/2-40, yc+sL/2-40), "ARMADURA")
    # Vigas baldrame (linhas entre sapatas)
    for i in range(len(xs)):
        for j in range(len(cols)-1):
            x0, x1 = xs[i], xs[i] if i < len(xs)-1 else xs[i]
            _line(msp, P(xs[i], cols[j]), P(xs[i], cols[j+1]), "CONCRETO")
    for i in range(len(xs)-1):
        for j in range(len(cols)):
            _line(msp, P(xs[i], cols[j]), P(xs[i+1], cols[j]), "CONCRETO")
    # Cotas e eixos
    for i, x in enumerate(xs, 1):
        _bolha(msp, P(x, span+900), i)
    _bolha(msp, P(-900, 0), "A"); _bolha(msp, P(-900, span), "B")
    _cota_h(msp, ox, ox+comp, oy, txt=f"{comp/1000:.2f} m", off=-900)
    _cota_v(msp, oy, oy+span, ox-200, txt=f"{span/1000:.2f}", off=-900)
    _txt(msp, "PLANTA DE FUNDACOES", P(comp/2-1400, -2200), h=220)


# ---- CORTE A-A (secao construtiva) -----------------------------------------
def _corte_aa(msp, d, ox, oy):
    nv = d.get("n_vaos", 1); cols = d.get("col_ys", [0.0, d["span"]])
    ridges = d.get("ridge_ys", [d["span"]/2.0]); eave = d["eave"]
    dc, dr = d["col_d"], d["raf_d"]; B = d["base"]; sap = d.get("sapata")
    span_total = cols[-1]
    def P(y, z): return (ox + y, oy + z)
    def _zr(y):
        for j in range(nv):
            c0, c1 = cols[j], cols[j+1]
            if c0-1 <= y <= c1+1:
                rj = ridges[j]; zrj = d["ridges"][j]
                return eave + (zrj-eave)/(rj-c0)*(y-c0) if y <= rj else eave + (zrj-eave)/(c1-rj)*(c1-y)
        return eave
    # Terreno
    _line(msp, P(-500, -300), P(span_total+500, -300), "TEXTO")
    for yc in cols:
        if sap:
            sB, sh = sap["B"], sap["h"]; pd = max(dc+200, 300)
            zt, zb = -350, -350-sh
            _poly(msp, [P(yc-sB/2, zt), P(yc+sB/2, zt), P(yc+sB/2, zb), P(yc-sB/2, zb)], "CONCRETO")
            _poly(msp, [P(yc-pd/2, 0), P(yc+pd/2, 0), P(yc+pd/2, zt), P(yc-pd/2, zt)], "CONCRETO")
            _line(msp, P(yc-sB/2+60, zb+60), P(yc+sB/2-60, zb+60), "ARMADURA")
        bl, bt = B["L"], B["t"]
        _poly(msp, [P(yc-bl/2, 0), P(yc+bl/2, 0), P(yc+bl/2, -bt), P(yc-bl/2, -bt)], "BASE")
        _perf_rect(msp, P(yc, 0), P(yc, eave), dc)
        # Joelho
        hl = 800
        if yc == cols[0]:
            yb = yc+hl; zc = _zr(yb)
            _poly(msp, [P(yc, eave-dr/2), P(yc, eave-dr/2-450), P(yb, zc-dr/2)], "ACO")
        elif yc == cols[-1]:
            yb = yc-hl; zc = _zr(yb)
            _poly(msp, [P(yc, eave-dr/2), P(yc, eave-dr/2-450), P(yb, zc-dr/2)], "ACO")
        else:
            for sgn in (+1, -1):
                yb = yc+sgn*hl; zc = _zr(yb)
                _poly(msp, [P(yc, eave-dr/2), P(yc, eave-dr/2-450), P(yb, zc-dr/2)], "ACO")
    for j in range(nv):
        y0, y1 = cols[j], cols[j+1]; rj = ridges[j]; zj = d["ridges"][j]
        _perf_rect(msp, P(y0, eave), P(rj, zj), dr)
        _perf_rect(msp, P(y1, eave), P(rj, zj), dr)
    nt = 3
    for j in range(nv):
        y0, y1 = cols[j], cols[j+1]; rj = ridges[j]
        for k in range(1, nt):
            for y, z in [(y0+(rj-y0)*k/nt, _zr(y0+(rj-y0)*k/nt)),
                         (y1-(y1-rj)*k/nt, _zr(y1-(y1-rj)*k/nt))]:
                _poly(msp, [P(y-90, z+dr/2), P(y+90, z+dr/2),
                            P(y+90, z+dr/2+180), P(y-90, z+dr/2+180)], "TELHA")
    tz = dr/2+240
    for j in range(nv):
        y0, y1 = cols[j], cols[j+1]; rj = ridges[j]; zj = d["ridges"][j]
        _line(msp, P(y0, eave+tz), P(rj, zj+tz), "TELHA")
        _line(msp, P(y1, eave+tz), P(rj, zj+tz), "TELHA")
    # Calha nos beirais (esq+dir)
    for yc in (cols[0], cols[-1]):
        _poly(msp, [P(yc-100, eave+dr/2+200), P(yc+100, eave+dr/2+200),
                    P(yc+100, eave+dr/2+500), P(yc-100, eave+dr/2+500)], "TELHA")
    # Eixos
    for i, yc in enumerate(cols):
        _line(msp, P(yc, -700), P(yc, eave+500), "EIXOS")
        _bolha(msp, P(yc, eave+900), chr(65+i) if i < 26 else f"X{i}")
    _line(msp, P(-500, eave/2), P(span_total+500, eave/2), "TEXTO")  # linha de chamada
    _nivel(msp, P(-dc/2-250, 0), "+0,00")
    _nivel(msp, P(-dc/2-250, eave), f"+{eave/1000:.2f}")
    for j in range(nv):
        _nivel(msp, P(ridges[j]+250, d['ridges'][j]), f"+{d['ridges'][j]/1000:.2f}")
    _cota_v(msp, oy, oy+eave, ox, txt=f"{eave/1000:.2f}", off=-900)
    _txt(msp, f"CORTE A-A (secao construtiva) - {nv} vao(s)", P(span_total/2-1800, -bt-1200), h=220)


def gerar_dxf(design, path):
    """design: dict com geometria do galpao (1 ou N vaos). Escreve o DXF."""
    doc = ezdxf.new("R2010", setup=True)
    _setup(doc)
    msp = doc.modelspace()
    span, comp = design["span"], design["comprimento"]
    eave = design["eave"]
    span_total = design["span"]
    XD = span_total + 7000.0

    # L1 (oy=0): Portico(0)  |  Elevacao(XD)
    _portico(msp, design, ox=0.0, oy=0.0)
    _elev_long(msp, design, ox=XD, oy=0.0)
    # fundo L1 = -2400 (elevacao)

    # L2 (oy=-13000): Corte AA(0) [-14600,-5600]  |  Planta(XD) [-15200,-3000]
    # Planta topo=-3000 < fundo L1-500=-2900 ✓
    oy2 = -13000.0
    _corte_aa(msp, design, ox=0.0, oy=oy2)
    _planta(msp, design, ox=XD, oy=oy2)

    # L3 (oy=-18500): Joelho(0)+Base(7000)  |  Terca(XD)+Contrav(XD,-2500)+Calha(XD,-5000)
    # Joelho topo=-16100 < fundo L2-500=-15700 ✓
    oy3 = -18500.0
    _detalhe_joelho(msp, design, ox=0.0, oy=oy3)
    _detalhe_base(msp, design, ox=7000.0, oy=oy3)
    _detalhe_terca_viga(msp, design, ox=XD, oy=oy3)
    _detalhe_contraventamento(msp, design, ox=XD, oy=oy3 - 2500.0)
    _detalhe_calha_fechamento(msp, design, ox=XD, oy=oy3 - 5000.0)

    # L4 (oy=-20500): Quadros(XD)  |  fundo L3=-19250, topo quadros=-20300 ✓
    oy4 = -20500.0
    _quadro_verif(msp, design, ox=XD, oy=oy4)
    _quadro_materiais(msp, design, ox=XD + 6000.0, oy=oy4)

    # L5 (oy=-37000): Planta Fundacoes(0) full  |  topo=-27000 < fundo L4-500=-26500 ✓
    oy5 = -37000.0
    _planta_fundacoes(msp, design, ox=0.0, oy=oy5)

    # L6 (oy=-44000): Notas(0)+Legenda(10000)  |  topo=-40000 < fundo L5-500=-39700 ✓
    oy6 = -44000.0
    _notas_tecnicas(msp, design, ox=0.0, oy=oy6)
    _legenda(msp, design, ox=10000.0, oy=oy6)
    doc.saveas(path)
    return path


def design_de_spec(spec):
    """Monta o 'design' do DXF a partir do spec. Suporta 1 ou N vaos."""
    import perfis
    g = spec["geometria"]
    est = spec.get("estrutura", {})
    col_nome = est.get("perfil_col_adotado", "HEA200")
    raf_nome = est.get("perfil_raf_adotado", "HEA180")
    ba = est.get("base_adotada", {"B": 0.45, "L": 0.55, "t": 0.04, "db": 0.02, "n": 4})
    # Multi-vao: spans ou span?
    if "spans" in g:
        spans_m = [s * 1000.0 for s in g["spans"]]
    else:
        spans_m = [g["span"] * 1000.0]
    total_span = sum(spans_m)
    comp = g["comprimento"] * 1000.0
    eave = g["eave"] * 1000.0
    slope = spec["cobertura"]["slope"]
    ridges_m = [eave + slope * s / 2.0 for s in spans_m]
    bay = g["bay"] * 1000.0
    n = int(round(comp / bay))
    col_ys = [sum(spans_m[:i]) for i in range(len(spans_m) + 1)]
    ridge_ys = [sum(spans_m[:i]) + spans_m[i] / 2.0 for i in range(len(spans_m))]
    return {
        "slug": spec.get("slug", "galpao"), "descricao": spec.get("descricao", ""),
        "span": total_span, "spans": spans_m, "comprimento": comp,
        "eave": eave, "ridge": ridges_m[0], "ridges": ridges_m,
        "slope": slope, "bay": bay, "frame_x": [i * bay for i in range(n + 1)],
        "col_ys": col_ys, "ridge_ys": ridge_ys, "n_vaos": len(spans_m),
        "col_d": perfis.PERFIS[col_nome]["d"] * 1000.0,
        "col_bf": perfis.PERFIS[col_nome]["bf"] * 1000.0,
        "raf_d": perfis.PERFIS[raf_nome]["d"] * 1000.0,
        "perfil_col": col_nome, "perfil_raf": raf_nome,
        "base": {"B": ba["B"] * 1000.0, "L": ba["L"] * 1000.0,
                 "t": ba["t"] * 1000.0, "db": ba["db"] * 1000.0, "n": ba["n"]},
        "joelho": est.get("joelho_adotado"),
        "sapata": ({"B": sp["B"] * 1000.0, "L": sp["L"] * 1000.0, "h": sp["h"] * 1000.0,
                    "As_L": sp.get("As_L", 0.0) * 1e4, "As_B": sp.get("As_B", 0.0) * 1e4,
                    "arm_L": sp.get("arm_L"), "arm_B": sp.get("arm_B"),
                    "rigida": sp.get("rigida", True)}
                   if (sp := est.get("sapata_adotada")) else None),
        "sapata_quant": est.get("sapata_quant"),
        "resultados": est.get("resultados", {}),
        "takeoff": est.get("takeoff", []),
        "terca_dims": est.get("terca_dims", [200, 75, 25, 2.65]),
    }
