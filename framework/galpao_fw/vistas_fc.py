"""Gera vistas 2D do galpao diretamente no FreeCAD (projeto executivo).
Converte o spec calculado em 14 vistas com cotas, textos e tabelas.
Usa Part::Feature para geometria e Draft::Text/Dimension para anotacoes.
Cria documento separado 'Vistas2D_*'. Exporta DXF ao final.

Unidades: mm. Z=0 no topo do concreto.
"""

import math, os, datetime, sys

# FreeCAD imports - so via MCP (dentro do FreeCAD)
# Fora do FreeCAD, design_de_spec() funciona sem eles
try:
    import FreeCAD as App
    import Part
    import Draft
except ImportError:
    pass

# ── helpers geométricos FreeCAD ────────────────────────────────────────
def P(x, y):
    return (x, y, 0.0)

def vec(x, y, z=0):
    return App.Vector(x, y, z)

def _cor(r, g, b):
    """Garante que todos os valores sejam float (0..1) para FreeCAD."""
    return (float(r), float(g), float(b))

def rect(doc, nome, pts, cor=None):
    o = doc.addObject("Part::Feature", nome)
    o.Shape = Part.Face(Part.makePolygon([vec(*p) for p in pts]))
    if cor is not None:
        o.ViewObject.ShapeColor = _cor(*cor)
    return o

def ln(doc, nome, a, b, cor=None):
    o = doc.addObject("Part::Feature", nome)
    o.Shape = Part.makeLine(vec(*a), vec(*b))
    if cor is not None:
        o.ViewObject.ShapeColor = _cor(*cor)
    return o

def circ(doc, nome, centro, raio, cor=None):
    o = doc.addObject("Part::Feature", nome)
    o.Shape = Part.makeCircle(raio, vec(*centro), vec(0, 0, 1))
    if cor is not None:
        o.ViewObject.ShapeColor = _cor(*cor)
    return o

def _dec(v):
    """Formata numero com virgula decimal (pt_BR)."""
    s = f"{v:.2f}" if isinstance(v, float) else str(v)
    return s.replace(".", ",")

def texto(doc, nome, txt, pos, tam=6):
    try:
        t = Draft.make_text(str(txt), vec(*pos))
        t.Label = nome
        t.ViewObject.TextSize = tam
        return t
    except Exception:
        return None

def _seta(doc, nome, ponta, direcao, tam=80):
    """Triangulo preenchido (seta de cota). direcao=(dx,dy) normalizado."""
    dx, dy = direcao
    nx, ny = -dy, dx  # perpendicular
    pts = [ponta, (ponta[0]+dx*tam+ny*tam*0.4, ponta[1]+dy*tam-nx*tam*0.4),
           (ponta[0]+dx*tam-ny*tam*0.4, ponta[1]+dy*tam+nx*tam*0.4)]
    # Filled triangle using face
    o = doc.addObject("Part::Feature", nome)
    o.Shape = Part.Face(Part.makePolygon([vec(*p) for p in pts + [pts[0]]]))
    return o

def cotah(doc, nome, p1, p2, off=-350):
    """Cota horizontal manual: extensao + linha + setas + texto."""
    x1, y1 = p1; x2, y2 = p2
    yd = min(y1, y2) + off; xm = (x1 + x2) / 2
    ln(doc, f"{nome}_E1", (x1, y1), (x1, yd))
    ln(doc, f"{nome}_E2", (x2, y2), (x2, yd))
    ln(doc, f"{nome}_DL", (x1, yd), (x2, yd))
    _seta(doc, f"{nome}_A1", (x1, yd), (1, 0))
    _seta(doc, f"{nome}_A2", (x2, yd), (-1, 0))
    texto(doc, f"{nome}_T", _dec(abs(x2-x1)/1000) + " m", (xm, yd - 150), 7)

def cotav(doc, nome, p1, p2, off=-350):
    """Cota vertical manual: extensao + linha + setas + texto."""
    x1, y1 = p1; x2, y2 = p2
    xd = min(x1, x2) + off; ym = (y1 + y2) / 2
    ln(doc, f"{nome}_E1", (x1, y1), (xd, y1))
    ln(doc, f"{nome}_E2", (x2, y2), (xd, y2))
    ln(doc, f"{nome}_DL", (xd, y1), (xd, y2))
    _seta(doc, f"{nome}_A1", (xd, y1), (0, 1))
    _seta(doc, f"{nome}_A2", (xd, y2), (0, -1))
    texto(doc, f"{nome}_T", _dec(abs(y2-y1)/1000) + " m", (xd - 400, ym), 7)

def bolha(doc, nome, p, rotulo, r=400):
    centro = vec(*p)
    circ(doc, f"{nome}_C", p, r, (0.6, 0.6, 0.6))
    texto(doc, f"{nome}_T", str(rotulo), (p[0], p[1]), r * 0.4)

def nivel(doc, nome, p, txt, s=180):
    x, y = p
    pts = [(x, y), (x - s, y + s), (x + s, y + s), (x, y)]
    rect(doc, f"{nome}_N", pts, (0, 0.6, 0))
    texto(doc, f"{nome}_L", txt, (x + s + 100, y + s - 40), 8)

def poligono(doc, nome, pts, fechado=True, cor=None):
    pts_v = [vec(*p) for p in pts]
    if fechado:
        pts_v.append(pts_v[0])
    o = doc.addObject("Part::Feature", nome)
    o.Shape = Part.makePolygon(pts_v)
    if cor is not None:
        o.ViewObject.ShapeColor = _cor(*cor)
    return o

def perfil_ret(doc, nome, p1, p2, profundidade, cor=None):
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return None
    nx, ny = -dy / L * profundidade / 2, dx / L * profundidade / 2
    pts = [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
           (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
    return rect(doc, nome, pts, cor)


# ── VISTA 1: Pórtico Transversal ─────────────────────────────────────
def _portico(doc, d, ox, oy):
    nv = d.get("n_vaos", 1); cols = d.get("col_ys", [0.0, d["span"]])
    ridges = d.get("ridge_ys", [d["span"] / 2.0]); eave = d["eave"]
    dc, dr = d["col_d"], d["raf_d"]; B = d["base"]
    bl, bt = B["L"], B["t"]; span_t = cols[-1]

    def _zr(y):
        for j in range(nv):
            c0, c1 = cols[j], cols[j + 1]
            if c0 - 1 <= y <= c1 + 1:
                rj = ridges[j]; zr = d["ridges"][j]
                if y <= rj:
                    return eave + (zr - eave) / (rj - c0) * (y - c0)
                else:
                    return eave + (zr - eave) / (c1 - rj) * (c1 - y)
        return eave

    def Q(y, z):
        return (ox + y, oy + z)

    for i, yc in enumerate(cols):
        perfil_ret(doc, f"PC_C_{i}", Q(yc, 0), Q(yc, eave), dc, (0.3, 0.3, 0.8))
    for j in range(nv):
        y0, y1 = cols[j], cols[j + 1]; rj = ridges[j]; zj = d["ridges"][j]
        perfil_ret(doc, f"PC_V_{j}E", Q(y0, eave), Q(rj, zj), dr, (0.3, 0.3, 0.8))
        perfil_ret(doc, f"PC_V_{j}D", Q(y1, eave), Q(rj, zj), dr, (0.3, 0.3, 0.8))
    # Misulas
    hl = 800.0
    for yc in cols:
        if yc == cols[0]:
            yb = yc + hl; zc = _zr(yb)
            poligono(doc, f"PC_M_{yc:.0f}", [Q(yc, eave - dr/2), Q(yc, eave - dr/2 - 450), Q(yb, zc - dr/2)])
        elif yc == cols[-1]:
            yb = yc - hl; zc = _zr(yb)
            poligono(doc, f"PC_M_{yc:.0f}", [Q(yc, eave - dr/2), Q(yc, eave - dr/2 - 450), Q(yb, zc - dr/2)])
        else:
            for sgn in (+1, -1):
                yb = yc + sgn * hl; zc = _zr(yb)
                poligono(doc, f"PC_M_{yc:.0f}_{sgn}", [Q(yc, eave - dr/2), Q(yc, eave - dr/2 - 450), Q(yb, zc - dr/2)])
    # Placas de base
    for yc in cols:
        rect(doc, f"PC_B_{yc:.0f}", [Q(yc - bl/2, 0), Q(yc + bl/2, 0), Q(yc + bl/2, -bt), Q(yc - bl/2, -bt)], (0.8, 0.5, 0))
        gy = bl / 2 - 60
        ys_c = [-gy, 0.0, gy] if B["n"] >= 6 else [-gy, gy]
        for yy in ys_c:
            ln(doc, f"PC_CH_{yc:.0f}_{yy:.0f}", Q(yc + yy, 20), Q(yc + yy, -bt - 120))
    # Eixos
    for i, yc in enumerate(cols):
        lbl = chr(65 + i) if i < 26 else f"X{i}"
        ln(doc, f"PC_EX_{i}", Q(yc, -700), Q(yc, eave + 500))
        bolha(doc, f"PC_BL_{i}", Q(yc, eave + 900), lbl)
    # Niveis
    nivel(doc, "PC_NV0", Q(-dc/2 - 250, 0), "+0,00")
    nivel(doc, "PC_NVE", Q(-dc/2 - 250, eave), "+" + _dec(eave/1000))
    for j in range(nv):
        nivel(doc, f"PC_NV_{j}", Q(ridges[j] + 250, d["ridges"][j]), "+" + _dec(d['ridges'][j]/1000))
    # Cotas
    for j in range(nv):
        cotah(doc, f"PC_CH_{j}", Q(cols[j], 0), Q(cols[j + 1], 0), off=-1200)
    cotav(doc, "PC_CV_E", Q(0, 0), Q(0, eave), off=-900)
    cotav(doc, "PC_CV_R", Q(0, eave), Q(0, d["ridges"][-1]), off=1300)
    # Legenda
    texto(doc, "PC_LABEL_COL", d["perfil_col"], Q(-dc - 550, eave / 2), 7)
    texto(doc, "PC_LABEL_RAF", d["perfil_raf"], Q(cols[0] + 300, (eave + d["ridges"][0]) / 2 + 250), 7)
    texto(doc, "PC_LABEL_BASE", f"Base {B['B']:.0f}x{B['L']:.0f}x{B['t']:.0f} - {B['n']}x d{B['db']:.0f}",
          Q(-dc - 550, -bt - 700), 6)
    texto(doc, "PC_TITULO", f"PORTICO TRANSVERSAL ({nv} vao(s))", Q(span_t / 2 - 1800, -bt - 1500), 10)


# ── VISTA 2: Elevação Longitudinal ────────────────────────────────────
def _elev_long(doc, d, ox, oy):
    comp, eave, bay, dc = d["comprimento"], d["eave"], d["bay"], d["col_d"]
    xs = d["frame_x"]

    def Q(x, z):
        return (ox + x, oy + z)

    for x in xs:
        perfil_ret(doc, f"EL_C_{x:.0f}", Q(x, 0), Q(x, eave), dc, (0.3, 0.3, 0.8))
    ln(doc, "EL_EAVE", Q(0, eave), Q(comp, eave))
    # Contraventamento extremidades
    for (x0, x1) in ((xs[0], xs[1]), (xs[-2], xs[-1])):
        ln(doc, f"EL_CV_{x0:.0f}_A", Q(x0, 0), Q(x1, eave), (0, 0, 0.8))
        ln(doc, f"EL_CV_{x0:.0f}_B", Q(x1, 0), Q(x0, eave), (0, 0, 0.8))
    for x in xs:
        ln(doc, f"EL_B_{x:.0f}", Q(x - 250, 0), Q(x + 250, 0))
    for i, x in enumerate(xs, 1):
        ln(doc, f"EL_EX_{i}", Q(x, 0), Q(x, -1050))
        bolha(doc, f"EL_BL_{i}", Q(x, -1450), i)
    for i in range(len(xs) - 1):
        cotah(doc, f"EL_CH_{i}", Q(xs[i], 0), Q(xs[i + 1], 0), off=-600)
    cotav(doc, "EL_CV", Q(0, 0), Q(0, eave), off=-900)
    texto(doc, "EL_TIT", "ELEVACAO LONGITUDINAL", Q(comp / 2 - 1600, -2400), 10)
    # Corte A-A indicator
    mx = comp / 2.0
    ln(doc, "EL_AA", Q(mx, -300), Q(mx, eave + 500))
    ln(doc, "EL_AA_L", Q(mx - 200, -300), Q(mx + 200, -300))
    texto(doc, "EL_AA_T", "CORTE A-A", Q(mx + 300, eave + 200), 7)


# ── VISTA 3: Planta de Cobertura ──────────────────────────────────────
def _planta(doc, d, ox, oy):
    nv = d.get("n_vaos", 1); cols = d.get("col_ys", [0.0, d["span"]])
    ridges = d.get("ridge_ys", [d["span"] / 2.0]); comp = d["comprimento"]
    xs = d["frame_x"]; span = cols[-1]

    def Q(x, y):
        return (ox + x, oy + y)

    rect(doc, "PL_OUT", [Q(0, 0), Q(comp, 0), Q(comp, span), Q(0, span)], None)
    for rj in ridges:
        ln(doc, f"PL_R_{rj:.0f}", Q(0, rj), Q(comp, rj))
    for x in xs:
        ln(doc, f"PL_EX_{x:.0f}", Q(x, 0), Q(x, span))
    nt = 3
    for j in range(nv):
        y0, y1 = cols[j], cols[j + 1]; rj = ridges[j]
        for k in range(1, nt):
            yl = y0 + (rj - y0) * k / nt; yr = y1 - (y1 - rj) * k / nt
            ln(doc, f"PL_T_{j}_{k}", Q(0, yl), Q(comp, yl))
            ln(doc, f"PL_T_{j}_{k}_D", Q(0, yr), Q(comp, yr))
    ln(doc, "PL_BE", Q(0, cols[0]), Q(comp, cols[0]))
    ln(doc, "PL_BD", Q(0, cols[-1]), Q(comp, cols[-1]))
    for (x0, x1) in ((xs[0], xs[1]), (xs[-2], xs[-1])):
        ln(doc, f"PL_CV_{x0:.0f}_A", Q(x0, cols[0]), Q(x1, cols[-1]), (0, 0, 0.8))
        ln(doc, f"PL_CV_{x0:.0f}_B", Q(x1, cols[0]), Q(x0, cols[-1]), (0, 0, 0.8))
    for i, x in enumerate(xs, 1):
        bolha(doc, f"PL_BL_{i}", Q(x, span + 900), i)
    bolha(doc, "PL_BA", Q(-900, 0), "A"); bolha(doc, "PL_BB", Q(-900, span), "B")
    cotah(doc, "PL_CH", Q(0, 0), Q(comp, 0), off=-900)
    cotav(doc, "PL_CV", Q(0, 0), Q(0, span), off=-900)
    texto(doc, "PL_TIT", "PLANTA DE COBERTURA", Q(comp / 2 - 1400, -2200), 10)
    # Corte A-A na planta
    cy = span / 2.0
    ln(doc, "PL_AA", Q(-500, cy), Q(comp + 500, cy))
    ln(doc, "PL_AA_A1", Q(-500, cy), Q(-300, cy + 300))
    ln(doc, "PL_AA_A2", Q(-500, cy), Q(-300, cy - 300))
    ln(doc, "PL_AA_A3", Q(comp + 500, cy), Q(comp + 300, cy + 300))
    ln(doc, "PL_AA_A4", Q(comp + 500, cy), Q(comp + 300, cy - 300))
    texto(doc, "PL_AA_T1", "A", Q(-600, cy + 400), 8)
    texto(doc, "PL_AA_T2", "A", Q(comp + 500, cy + 400), 8)


# ── DETALHE DO JOELHO ─────────────────────────────────────────────────
def _detalhe_joelho(doc, d, ox, oy):
    dc, dr = d["col_d"], d["raf_d"]; ang = math.atan(d["slope"])
    ux, uy = math.cos(ang), math.sin(ang); nx, ny = -uy, ux

    def Q(x, y):
        return (ox + x, oy + y)

    Hc = 1400.0
    rect(doc, "DJ_COL", [Q(0, 0), Q(dc, 0), Q(dc, Hc), Q(0, Hc)], (0.3, 0.3, 0.8))
    bx, by = dc / 2.0, Hc; Lr = 1900.0
    A = (bx + nx * dr / 2, by + ny * dr / 2)
    B = (bx + ux * Lr + nx * dr / 2, by + uy * Lr + ny * dr / 2)
    C = (bx + ux * Lr - nx * dr / 2, by + uy * Lr - ny * dr / 2)
    E = (bx - nx * dr / 2, by - ny * dr / 2)
    rect(doc, "DJ_VIGA", [Q(*A), Q(*B), Q(*C), Q(*E)], (0.3, 0.3, 0.5))
    hl, hd = 900.0, 450.0
    Fi = (bx - nx * dr / 2, by - ny * dr / 2)
    Fo = (bx + ux * hl - nx * dr / 2, by + uy * hl - ny * dr / 2)
    Fb = (Fi[0] - nx * hd, Fi[1] - ny * hd)
    poligono(doc, "DJ_MIS", [Q(*Fi), Q(*Fb), Q(*Fo)], True, (0.5, 0.5, 0.5))
    # Chapa de topo
    sx, sy = bx + ux * hl, by + uy * hl
    pdepth = dr + 40.0
    ln(doc, "DJ_CHAPA", Q(sx + nx * (pdepth / 2), sy + ny * (pdepth / 2)),
       Q(sx - nx * (pdepth / 2 + hd), sy - ny * (pdepth / 2 + hd)))
    for f in (0.3, 0.7):
        for sgn in (-1, 1):
            cx = sx + nx * pdepth * (0.35 - f) - nx * hd * (0 if sgn > 0 else 1)
            cy = sy + ny * pdepth * (0.35 - f) - ny * hd * (0 if sgn > 0 else 1)
            circ(doc, f"DJ_P_{f:.0f}_{sgn}", (cx, cy), 55, (1, 0, 0))
    ln(doc, "DJ_EST", Q(0, Hc - 120), Q(dc, Hc - 120))
    texto(doc, "DJ_TIT", "DETALHE DO JOELHO", Q(0, -450), 8)
    joelho = d.get("joelho")
    sub = (f"misula + chapa {joelho['t']*1000:.0f} mm + {joelho['n']}x d{joelho['db']*1000:.0f}"
           if joelho else "misula + chapa + paraf. + enrijecedor")
    texto(doc, "DJ_SUB", sub, Q(0, -750), 6)


# ── DETALHE DA BASE + SAPATA ─────────────────────────────────────────
def _detalhe_base(doc, d, ox, oy):
    B = d["base"]; dc = d["col_d"]; bf = d.get("col_bf", dc)
    Bp, Lp, tp, db, n = B["B"], B["L"], B["t"], B["db"], B["n"]
    gx, gy = Bp / 2 - 60, Lp / 2 - 60; ys = [-gy, 0.0, gy] if n >= 6 else [-gy, gy]

    def Q(x, y):
        return (ox + x, oy + y)

    # Planta
    rect(doc, "DB_PLT", [Q(-Bp/2, -Lp/2), Q(Bp/2, -Lp/2), Q(Bp/2, Lp/2), Q(-Bp/2, Lp/2)], (0.8, 0.5, 0))
    rect(doc, "DB_PIL", [Q(-dc/2, -bf/2), Q(dc/2, -bf/2), Q(dc/2, bf/2), Q(-dc/2, bf/2)], (0.3, 0.3, 0.8))
    for xx in (-gx, gx):
        for yy in ys:
            circ(doc, f"DB_CH_{xx:.0f}_{yy:.0f}", (xx, yy), db/2 + 6, (1, 0, 0))
    cotah(doc, "DB_CH1", Q(-Bp/2, -Lp/2), Q(Bp/2, -Lp/2), off=-450)
    cotav(doc, "DB_CV1", Q(-Bp/2, -Lp/2), Q(-Bp/2, Lp/2), off=-450)
    texto(doc, "DB_TIT_PL", "PLANTA DA BASE", Q(-Bp/2, Lp/2 + 200), 8)
    # Corte
    oy2 = oy - Lp / 2 - 2200
    def Q2(x, z):
        return (ox + x, oy2 + z)
    rect(doc, "DB_CT_PL", [Q2(-Lp/2, 0), Q2(Lp/2, 0), Q2(Lp/2, tp), Q2(-Lp/2, tp)], (0.8, 0.5, 0))
    rect(doc, "DB_CT_PL", [Q2(-dc/2, tp), Q2(dc/2, tp), Q2(dc/2, tp+900), Q2(-dc/2, tp+900)], (0.3, 0.3, 0.8))
    for yy in ys:
        ln(doc, f"DB_CT_CH_{yy:.0f}", Q2(yy, tp+700), Q2(yy, -350))
        ln(doc, f"DB_CT_G_{yy:.0f}", Q2(yy, -350), Q2(yy - 90, -350))
    poligono(doc, "DB_NER", [Q2(dc/2, tp), Q2(dc/2+240, tp), Q2(dc/2, tp+500)], True, (0.3, 0.3, 0.8))
    cotav(doc, "DB_CV2", Q2(0, 0), Q2(0, tp), off=-400)
    texto(doc, "DB_SUB", f"CORTE - chapa {tp:.0f} mm; {n}x d{db:.0f}", Q2(-Lp/2, -800), 6)
    # Sapata
    sap = d.get("sapata")
    if sap:
        sL, sh = sap["L"], sap["h"]; pd = max(dc + 200, 300); zt, zb = -350, -350 - sh
        rect(doc, "DB_SAP", [Q2(-sL/2, zt), Q2(sL/2, zt), Q2(sL/2, zb), Q2(-sL/2, zb)], (0.5, 0.8, 0.8))
        rect(doc, "DB_PED", [Q2(-pd/2, tp), Q2(pd/2, tp), Q2(pd/2, zt), Q2(-pd/2, zt)], (0.5, 0.8, 0.8))
        ln(doc, "DB_ARM", Q2(-sL/2+60, zb+60), Q2(sL/2-60, zb+60), (1, 0, 0))
        cotav(doc, "DB_CV3", Q2(0, zb), Q2(0, zt), off=-400)
        cotah(doc, "DB_CH3", Q2(-sL/2, zb), Q2(sL/2, zb), off=-450)
        texto(doc, "DB_SAP_T", f"SAPATA {sap['B']/1000:.2f}x{sL/1000:.2f}x{sh/1000:.2f} m",
              Q2(-sL/2, zb - 350), 7)
        arm = (f"Arm. flexao: L={sap.get('arm_L','?')} ; B={sap.get('arm_B','?')}" or 
               f"As_L={sap.get('As_L',0):.1f} ; As_B={sap.get('As_B',0):.1f} cm2")
        texto(doc, "DB_ARM_T", arm, Q2(-sL/2, zb - 620), 6)
        q = d.get("sapata_quant")
        if q:
            texto(doc, "DB_QUANT", f"Quant.: {q['n']} sapatas; concreto {q['vol_conc_tot']:.1f} m3",
                  Q2(-sL/2, zb - 760), 6)
        texto(doc, "DB_TIT", "DETALHE DA BASE + SAPATA", Q2(-sL/2, zb - 1080), 8)
    else:
        texto(doc, "DB_TIT", "DETALHE DA BASE", Q2(-Bp/2, -Lp/2 - 1400), 8)


# ── TABELAS GRÁFICAS (uso: barras + texto Draft) ───────────────────┐
def _barra_util(doc, nome, ox, oy, w, u, base_nome):
    fill = w * min(u, 1.0)
    cor = (0, 0.6, 0) if u <= 1.001 else (0.8, 0, 0)
    rect(doc, f"{base_nome}_BAR", [(ox, oy-40), (ox+fill, oy-40), (ox+fill, oy+40), (ox, oy+40)], cor)
    texto(doc, f"{base_nome}_VAL", f"{u:.2f}", (ox+fill+50, oy-15), 5)

def _quadro_verif(doc, ck, ox, oy):
    linhas = [(n, v) for n, v in ck.items() if v is not None]
    if not linhas:
        return
    texto(doc, "QV_TIT", "QUADRO DE VERIFICACOES", (ox, oy+200), 12)
    rh, W = 400, 4500.0
    # Grid vertical (3 colunas: nome, barra, situacao)
    col_x = [ox, ox+2200, ox+3700, ox+W]
    for xv in col_x:
        ln(doc, f"QV_V_{xv:.0f}", (xv, oy), (xv, oy - rh * (len(linhas) + 1)))
    # Header
    ry0 = oy - rh
    ln(doc, "QV_HDR", (ox, ry0), (ox+W, ry0))
    texto(doc, "QV_HN", "Elemento", (ox+80, ry0+40), 7)
    texto(doc, "QV_HU", "util", (ox+2300, ry0+40), 7)
    texto(doc, "QV_HS", "OK", (ox+3800, ry0+40), 7)
    for i, (nome, val) in enumerate(linhas):
        ry = oy - rh * (i + 2)
        ln(doc, f"QV_L_{i}", (ox, ry), (ox+W, ry))
        texto(doc, f"QV_N_{i}", nome, (ox+80, ry+30), 5)
        _barra_util(doc, f"QV_B_{i}", ox+2300, ry, 1200, val, f"QV_{i}")
        texto(doc, f"QV_S_{i}", "OK" if val <= 1.001 else "REVER", (ox+3800, ry+30), 5)

def _quadro_materiais(doc, tk, ox, oy):
    rows = [(g[0], g[1], g[2], g[4]) for g in tk if "Alvenaria" not in g[0]]
    if not rows:
        return
    rows.sort(key=lambda r: -r[3]); rows = rows[:15]
    texto(doc, "QM_TIT", "MATERIAIS (aco)", (ox, oy+200), 12)
    rh, W = 380, 5500.0; mm = max(r[3] for r in rows) or 1
    col_x = [ox, ox+W]
    for xv in col_x:
        ln(doc, f"QM_V_{xv:.0f}", (xv, oy), (xv, oy - rh * (len(rows) + 1)))
    for i, (cat, prof, cnt, massa) in enumerate(rows):
        ry = oy - rh * (i + 1)
        ln(doc, f"QM_L_{i}", (ox, ry), (ox+W, ry))
        texto(doc, f"QM_C_{i}", f"{cat} ({prof})", (ox+50, ry+30), 5)
        bw = (massa / mm) * 3500
        rect(doc, f"QM_B_{i}", [(ox+2500, ry-25), (ox+2500+bw, ry-25), (ox+2500+bw, ry+25), (ox+2500, ry+25)], (0.4, 0.4, 0.6))
        texto(doc, f"QM_M_{i}", f"{massa:.0f} kg", (ox+2500+bw+50, ry+30), 5)
    ln(doc, "QM_BOT", (ox, oy - rh * (len(rows) + 1)), (ox+W, oy - rh * (len(rows) + 1)))
    texto(doc, "QM_TOT", f"Total: {sum(r[3] for r in rows):.0f} kg", (ox+50, oy - rh * (len(rows) + 1) - 200), 7)


# ── NOTAS TÉCNICAS ───────────────────────────────────────────────────
def _notas_tecnicas(doc, ox, oy):
    notas = [
        "NOTAS TECNICAS GERAIS",
        "1. COTAS EM MM SALVO INDICACAO.",
        "2. RN: +0,00 = TOPO DO CONCRETO (BASE PLACAS).",
        "3. ACO MR250 (NBR 8800). ARMADURA CA-50.",
        "4. CONCRETO fck=25 MPa. COBRIMENTO 5 cm (fund.), 3 cm (sup.).",
        "5. PARAFUSOS: A325 (fub=825 MPa) ou A307.",
        "6. SOLDAS: E70XX (fw=485 MPa). Filete min. 6 mm.",
        "7. CHUMBADORES: ASTM A36 c/ gancho 180 mm.",
        "8. CONTRAVENTAMENTO: barras d20 pretensionadas c/ esticador.",
        "9. TERÇAS: Ue formado a frio (NBR 14762).",
        "10. PROJETO CONCEITUAL - REVISAO E ART PENDENTES.",
    ]
    texto(doc, "NT_TIT", notas[0], (ox+150, oy+3650), 10)
    for i, s in enumerate(notas[1:], 1):
        texto(doc, f"NT_{i}", s, (ox+150, oy+3650-220*i), 5)


# ── LEGENDA ───────────────────────────────────────────────────────────
def _legenda(doc, d, ox, oy):
    data = datetime.date.today().strftime("%d/%m/%Y")
    sap = d.get("sapata")
    linhas = [
        f"PROJETO: {d.get('slug','galpao')}",
        f"{d.get('descricao','Galpao em aco - Projeto Estrutural')}",
        f"Vao {d['span']/1000:.1f} x Comp {d['comprimento']/1000:.1f} x Pd {d['eave']/1000:.1f} m",
        f"Colunas {d['perfil_col']} | Vigas {d['perfil_raf']}",
        f"Base {d['base']['B']:.0f}x{d['base']['L']:.0f}x{d['base']['t']:.0f} - {d['base']['n']}x d{d['base']['db']:.0f}",
        f"Sapata {sap['B']/1000:.2f}x{sap['L']/1000:.2f}x{sap['h']/1000:.2f}" if sap else "Sapata: N/A",
        f"Data: {data} | Rev.: 00 | Esc.: 1:50/1:100",
        "NBR 8800 | NBR 6123 | NBR 6118 | NBR 6122",
    ]
    for i, s in enumerate(linhas):
        texto(doc, f"LEG_{i}", s, (ox+150, oy+3100-320*i), 7 if i else 9)


# ── PLANTA DE FUNDAÇÕES ──────────────────────────────────────────────
def _planta_fundacoes(doc, d, ox, oy):
    cols = d.get("col_ys", [0.0, d["span"]]); xs = d["frame_x"]
    comp = d["comprimento"]; span = cols[-1]; sap = d.get("sapata")

    def Q(x, y):
        return (ox + x, oy + y)
    rect(doc, "PF_OUT", [Q(0, 0), Q(comp, 0), Q(comp, span), Q(0, span)], None)
    for x in xs:
        ln(doc, f"PF_EX_{x:.0f}", Q(x, 0), Q(x, span))
    for yc in cols:
        ln(doc, f"PF_EY_{yc:.0f}", Q(0, yc), Q(comp, yc))
    if sap:
        sB, sL = sap["B"], sap["L"]
        for x in xs:
            for yc in cols:
                rect(doc, f"PF_S_{x:.0f}_{yc:.0f}", [Q(x-sB/2, yc-sL/2), Q(x+sB/2, yc-sL/2),
                      Q(x+sB/2, yc+sL/2), Q(x-sB/2, yc+sL/2)], (0.5, 0.8, 0.8))
                for dxi, dyi in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                    ln(doc, f"PF_AR_{x:.0f}_{yc:.0f}_{dxi}{dyi}",
                       Q(x+dxi*(sB/2-40), yc+dyi*(sL/2-40)),
                       Q(x+dxi*(sB/2-150), yc+dyi*(sL/2-150)), (1, 0, 0))
    for i, x in enumerate(xs, 1):
        bolha(doc, f"PF_BL_{i}", Q(x, span+900), i)
    bolha(doc, "PF_BA", Q(-900, 0), "A"); bolha(doc, "PF_BB", Q(-900, span), "B")
    cotah(doc, "PF_CH", Q(0, 0), Q(comp, 0), off=-900)
    texto(doc, "PF_TIT", "PLANTA DE FUNDACOES", Q(comp/2-1600, -2200), 10)


# ── CORTE A-A ────────────────────────────────────────────────────────
def _corte_aa(doc, d, ox, oy):
    nv = d.get("n_vaos", 1); cols = d.get("col_ys", [0.0, d["span"]])
    ridges = d.get("ridge_ys", [d["span"]/2.0]); eave = d["eave"]
    dc, dr = d["col_d"], d["raf_d"]; B = d["base"]; sap = d.get("sapata")
    span_t = cols[-1]

    def Q(y, z):
        return (ox + y, oy + z)

    def _zr(y):
        for j in range(nv):
            c0, c1 = cols[j], cols[j + 1]
            if c0 - 1 <= y <= c1 + 1:
                rj = ridges[j]; zrj = d["ridges"][j]
                if y <= rj:
                    return eave + (zrj - eave) / (rj - c0) * (y - c0)
                else:
                    return eave + (zrj - eave) / (c1 - rj) * (c1 - y)
        return eave

    ln(doc, "CA_TERR", Q(-500, -300), Q(span_t+500, -300))
    for yc in cols:
        if sap:
            sB, sh = sap["B"], sap["h"]; pd = max(dc+200, 300); zt, zb = -350, -350-sh
            rect(doc, f"CA_SAP_{yc:.0f}", [Q(yc-sB/2, zt), Q(yc+sB/2, zt),
                 Q(yc+sB/2, zb), Q(yc-sB/2, zb)], (0.5, 0.8, 0.8))
            rect(doc, f"CA_PED_{yc:.0f}", [Q(yc-pd/2, 0), Q(yc+pd/2, 0),
                 Q(yc+pd/2, zt), Q(yc-pd/2, zt)], (0.5, 0.8, 0.8))
            ln(doc, f"CA_ARM_{yc:.0f}", Q(yc-sB/2+60, zb+60), Q(yc+sB/2-60, zb+60), (1, 0, 0))
        bl, bt = B["L"], B["t"]
        rect(doc, f"CA_BASE_{yc:.0f}", [Q(yc-bl/2, 0), Q(yc+bl/2, 0), Q(yc+bl/2, -bt), Q(yc-bl/2, -bt)], (0.8, 0.5, 0))
        ln(doc, f"CA_CH_{yc:.0f}", Q(yc+bl/2-60, 20), Q(yc+bl/2-60, -bt-120), (1, 0, 0))
        perfil_ret(doc, f"CA_COL_{yc:.0f}", Q(yc, 0), Q(yc, eave), dc, (0.3, 0.3, 0.8))
        hl = 800
        if yc == cols[0]:
            yb = yc+hl; zc = _zr(yb)
            poligono(doc, f"CA_MIS_{yc:.0f}", [Q(yc, eave-dr/2), Q(yc, eave-dr/2-450), Q(yb, zc-dr/2)])
        elif yc == cols[-1]:
            yb = yc-hl; zc = _zr(yb)
            poligono(doc, f"CA_MIS_{yc:.0f}", [Q(yc, eave-dr/2), Q(yc, eave-dr/2-450), Q(yb, zc-dr/2)])
        else:
            for sgn in (+1, -1):
                yb = yc+sgn*hl; zc = _zr(yb)
                poligono(doc, f"CA_MIS_{yc:.0f}_{sgn}", [Q(yc, eave-dr/2), Q(yc, eave-dr/2-450), Q(yb, zc-dr/2)])
    for j in range(nv):
        y0, y1 = cols[j], cols[j+1]; rj = ridges[j]; zj = d["ridges"][j]
        perfil_ret(doc, f"CA_VIGA_{j}E", Q(y0, eave), Q(rj, zj), dr, (0.3, 0.3, 0.8))
        perfil_ret(doc, f"CA_VIGA_{j}D", Q(y1, eave), Q(rj, zj), dr, (0.3, 0.3, 0.8))
    for i, yc in enumerate(cols):
        ln(doc, f"CA_EX_{i}", Q(yc, -700), Q(yc, eave+500))
        bolha(doc, f"CA_BL_{i}", Q(yc, eave+900), chr(65+i) if i < 26 else f"X{i}")
    nivel(doc, "CA_NV0", Q(-dc/2-250, 0), "+0,00")
    nivel(doc, "CA_NVE", Q(-dc/2-250, eave), f"+{eave/1000:.2f}")
    cotav(doc, "CA_CV", Q(0, 0), Q(0, eave), off=-900)
    texto(doc, "CA_TIT", f"CORTE A-A ({nv} vao(s))", Q(span_t/2-1800, -bt-1200), 10)


# ── MASTER: gera todas as vistas no documento ─────────────────────────
def gerar_vistas(design, doc, export_dir=None):
    """Gera todas as 14 vistas 2D no doc FreeCAD."""
    ea = design["eave"]; sp = design["span"]
    XD = sp + 7000.0
    ck = design.get("resultados", {})
    tk = design.get("takeoff", [])

    # L1 (oy=0): Portico + Elevacao
    _portico(doc, design, 0.0, 0.0)
    _elev_long(doc, design, XD, 0.0)
    _planta(doc, design, XD, -13000.0)

    # L2 (oy=-13000): Corte AA + Planta
    _corte_aa(doc, design, 0.0, -13000.0)

    # L3 (oy=-18500): Joelho + Base + Detalhes
    _detalhe_joelho(doc, design, 0.0, -18500.0)
    _detalhe_base(doc, design, 7000.0, -18000.0)

    # L4 (oy=-25000): Tabelas
    _quadro_verif(doc, ck, XD, -25000.0)
    _quadro_materiais(doc, tk, XD, -31000.0)

    # L5 (oy=-41000): Planta Fundações (full)
    _planta_fundacoes(doc, design, 0.0, -41000.0)

    # L6 (oy=-48000): Notas + Legenda
    _notas_tecnicas(doc, 0.0, -48000.0)
    _legenda(doc, design, 10000.0, -48000.0)

    doc.recompute()

    # Exporta DXF
    if export_dir:
        os.makedirs(export_dir, exist_ok=True)
        dxf_path = os.path.join(export_dir, "vistas_2d.dxf")
        try:
            import importDXF
            importDXF.export([o for o in doc.Objects if hasattr(o, "Shape")], dxf_path)
        except Exception:
            try:
                Draft.export([o for o in doc.Objects if hasattr(o, "Shape")], dxf_path)
            except Exception as ex:
                print(f"DXF export failed: {ex}")
        return dxf_path


# ── API PÚBLICA ─────────────────────────────────────────────────────
def design_de_spec(spec):
    """Monta o 'design' do DXF a partir do spec. Suporta 1 ou N vaos."""
    import perfis
    g = spec["geometria"]
    est = spec.get("estrutura", {})
    col_nome = est.get("perfil_col_adotado", "HEA200")
    raf_nome = est.get("perfil_raf_adotado", "HEA180")
    ba = est.get("base_adotada", {"B": 0.45, "L": 0.55, "t": 0.04, "db": 0.02, "n": 4})
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


def codigo_fonte():
    """Retorna o codigo fonte deste modulo para injecao via MCP."""
    dir_atual = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(dir_atual, "vistas_fc.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
