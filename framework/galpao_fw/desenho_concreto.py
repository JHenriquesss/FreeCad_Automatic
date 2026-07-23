# ============================================================================
# desenho_concreto.py - O QUE ESTE SCRIPT FAZ / DESENHA
# Gera o DESENHO de FORMAS + ARMACAO do galpao de concreto em SVG puro-Python
# (autocontido, sem FreeCAD/TechDraw) - a camada grafica do executivo de concreto,
# sobre os dados de executivo_concreto/galpao_concreto:
#   - SECAO DO PILAR: retangulo hy x hx, barras longitudinais, estribo, cotas, rotulo;
#   - SECAO DA VIGA DE COBERTURA: barras inf/sup, estribo, cotas;
#   - SECAO DA SAPATA: malha nas 2 direcoes + altura.
# Escala e cotas em cm. O SVG e um deliverable que abre em qualquer navegador/CAD.
# ============================================================================
"""Desenho de formas + armacao do galpao de concreto em SVG puro-Python (sem
FreeCAD). Seccoes do pilar/viga/sapata com barras, estribos e cotas."""

from __future__ import annotations

import math


def _rebar_positions(x0, y0, w, h, cob_px, n, faces="perim"):
    """Distribui n barras. 'perim': ao longo do perimetro interno (pilar);
    'linha': numa linha horizontal (viga). Retorna [(x,y),...] em px."""
    pts = []
    if faces == "linha":
        if n <= 1:
            return [(x0 + w / 2.0, y0)]
        for i in range(n):
            pts.append((x0 + cob_px + i * (w - 2 * cob_px) / (n - 1), y0))
        return pts
    # perimetro: 4 cantos + distribui o resto nas faces
    xa, xb = x0 + cob_px, x0 + w - cob_px
    ya, yb = y0 + cob_px, y0 + h - cob_px
    cantos = [(xa, ya), (xb, ya), (xb, yb), (xa, yb)]
    if n <= 4:
        return cantos[:max(n, 1)]
    pts = list(cantos)
    resto = n - 4
    # distribui o resto nas 2 faces maiores (verticais, ao longo de h)
    por_face = resto // 2
    extra = resto - 2 * por_face
    for f, xf in ((0, xa), (1, xb)):
        nf = por_face + (1 if (f == 0 and extra) else 0)
        for i in range(1, nf + 1):
            pts.append((xf, ya + i * (yb - ya) / (nf + 1)))
    return pts


def _svg_secao(cx, cy, w_cm, h_cm, esc, rotulo, barras, estribo=True,
               cob_cm=3.0, faces="perim", cotas=True):
    """Desenha UMA secao retangular de concreto com armadura. Retorna string SVG
    (grupo). (cx,cy)=centro em px ; w/h em cm ; esc=px/cm ; barras=[(phi_mm,n),...].
    Para 'linha' cada tupla vira uma camada horizontal (inf depois sup)."""
    w, h = w_cm * esc, h_cm * esc
    x0, y0 = cx - w / 2.0, cy - h / 2.0
    cob = cob_cm * esc
    s = [f'<g>']
    # contorno da forma (concreto)
    s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" '
             f'fill="#e8e4dc" stroke="#333" stroke-width="1.5"/>')
    # estribo (retangulo interno arredondado)
    if estribo:
        s.append(f'<rect x="{x0+cob:.1f}" y="{y0+cob:.1f}" width="{w-2*cob:.1f}" '
                 f'height="{h-2*cob:.1f}" fill="none" stroke="#c0392b" '
                 f'stroke-width="1.2" rx="4"/>')
    # barras
    r_px = max(2.2, 2.0)
    if faces == "linha":
        # cada tupla = uma camada; a 1a embaixo (inf), a 2a em cima (sup)
        ys = [y0 + h - cob, y0 + cob][:len(barras)]
        for (phi, n), yb in zip(barras, ys):
            for (bx, by) in _rebar_positions(x0, y0, w, h, cob, n, faces="linha"):
                s.append(f'<circle cx="{bx:.1f}" cy="{yb:.1f}" r="{r_px}" fill="#1a1a1a"/>')
    else:
        phi, n = barras[0]
        for (bx, by) in _rebar_positions(x0, y0, w, h, cob, n, faces="perim"):
            s.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{r_px}" fill="#1a1a1a"/>')
    # cotas (largura embaixo, altura a esquerda)
    if cotas:
        s.append(f'<text x="{cx:.1f}" y="{y0+h+16:.1f}" font-size="11" '
                 f'text-anchor="middle" fill="#333">{w_cm:.0f}</text>')
        s.append(f'<text x="{x0-8:.1f}" y="{cy:.1f}" font-size="11" '
                 f'text-anchor="end" fill="#333" transform="rotate(-90 {x0-8:.1f} {cy:.1f})">'
                 f'{h_cm:.0f}</text>')
    # rotulo
    s.append(f'<text x="{cx:.1f}" y="{y0-8:.1f}" font-size="12" font-weight="bold" '
             f'text-anchor="middle" fill="#111">{_esc(rotulo)}</text>')
    s.append('</g>')
    return "\n".join(s)


def _esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def prancha_armacao_svg(r):
    """Monta a prancha de armacao (SVG) do galpao de concreto a partir do resultado
    de galpao_concreto.rodar(). Uma linha com as 3 secoes: pilar, viga, sapata."""
    esc = 3.5                                           # px por cm (escala ~1:29)
    pil = r["pilar"]; vg = r["viga"]; sp = r["spec"]
    W, Hn = 900, 380
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hn}" '
             f'viewBox="0 0 {W} {Hn}" font-family="Arial,Helvetica,sans-serif">',
             f'<rect width="{W}" height="{Hn}" fill="#ffffff"/>',
             f'<text x="20" y="26" font-size="15" font-weight="bold" fill="#111">'
             f'ARMACAO - GALPAO DE CONCRETO C{sp["fck_MPa"]:.0f} '
             f'(vao {sp["vao"]:.0f} m, pe-direito {sp["H"]:.0f} m)</text>']

    # ---- barras do pilar ----
    import executivo_concreto as ex
    q = ex.quadro_de_aco(r)
    n1 = next((x for x in q if x["pos"].startswith("N1")), None)
    phi_l = n1["phi_mm"] if n1 else 12.5
    n_l = (n1["n"] // (sp["n_porticos"] * 2)) if n1 else 4
    rot_pil = f'PILAR {pil["hy"]*100:.0f}x{pil["hx"]*100:.0f} - {n_l} f{phi_l:.1f}'
    parts.append(_svg_secao(180, 210, pil["hy"] * 100, pil["hx"] * 100, esc, rot_pil,
                            [(phi_l, n_l)], faces="perim"))

    # ---- viga de cobertura ----
    ai = vg["arr_inf"]; asup = vg["arr_sup"]
    barras_v = []
    if ai and ai.get("n"):
        barras_v.append((ai["phi"], ai["n"]))
    if asup and asup.get("n"):
        barras_v.append((asup["phi"], asup["n"]))
    rot_v = (f'VIGA COB. {vg["b"]*100:.0f}x{vg["h"]*100:.0f} - inf '
             f'{ai["n"] if ai else 0} f{(ai["phi"] if ai else 0):.1f}')
    parts.append(_svg_secao(460, 210, vg["b"] * 100, vg["h"] * 100, esc, rot_v,
                            barras_v or [(10.0, 2)], faces="linha"))

    # ---- sapata (planta com malha) ----
    # a sapata e em METROS (ordem de 2-3 m) -> escala PROPRIA p/ caber no slot
    # (~150 px), senao estoura a prancha e cobre a viga.
    if r["sapata"]["aprovado"]:
        B, Ls, hf = r["sapata"]["aprovado"][:3]
        esc_sap = 150.0 / (max(B, Ls) * 100.0)         # cabe em ~150 px
        parts.append(_svg_sapata(740, 210, B, Ls, hf, esc_sap, r))
    parts.append('</svg>')
    return "\n".join(parts)


def _svg_sapata(cx, cy, B, L, hf, esc, r):
    """Planta da sapata com malha ortogonal + rotulo. esc = px/cm (proprio da
    sapata, calculado p/ caber no slot; a sapata e em metros)."""
    w, h = B * 100 * esc, L * 100 * esc
    x0, y0 = cx - w / 2.0, cy - h / 2.0
    s = ['<g>', f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" '
         f'fill="#e8e4dc" stroke="#333" stroke-width="1.5"/>']
    for i in range(1, 8):                              # malha (linhas)
        xx = x0 + i * w / 8.0
        yy = y0 + i * h / 8.0
        s.append(f'<line x1="{xx:.1f}" y1="{y0:.1f}" x2="{xx:.1f}" y2="{y0+h:.1f}" '
                 f'stroke="#c0392b" stroke-width="0.7"/>')
        s.append(f'<line x1="{x0:.1f}" y1="{yy:.1f}" x2="{x0+w:.1f}" y2="{yy:.1f}" '
                 f'stroke="#2980b9" stroke-width="0.7"/>')
    s.append(f'<text x="{cx:.1f}" y="{y0-8:.1f}" font-size="12" font-weight="bold" '
             f'text-anchor="middle" fill="#111">SAPATA {B:.1f}x{L:.1f}x{hf:.2f}</text>')
    s.append(f'<text x="{cx:.1f}" y="{y0+h+16:.1f}" font-size="11" '
             f'text-anchor="middle" fill="#333">{B*100:.0f} x {L*100:.0f} cm</text>')
    s.append('</g>')
    return "\n".join(s)


def gerar_prancha(r, path):
    """Escreve a prancha de armacao (SVG) em `path`. Retorna o path."""
    svg = prancha_armacao_svg(r)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


def _selftest():
    import xml.dom.minidom as md
    import galpao_concreto as gc
    r = gc.rodar({"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
                  "v0": 40.0, "cat": "IV", "classe": "B", "G_roof": 0.30, "Q_roof": 0.25,
                  "fck": 30e3, "sigma_solo_adm": 250.0})
    svg = prancha_armacao_svg(r)
    dom = md.parseString(svg)                          # tem que ser XML bem-formado
    n_circ = svg.count("<circle")                      # barras longitudinais desenhadas
    assert n_circ >= 4, n_circ
    assert "PILAR" in svg and "VIGA COB." in svg and "SAPATA" in svg
    assert dom.documentElement.tagName == "svg"
    print("desenho_concreto self-test PASSED (%d barras desenhadas, SVG bem-formado)" % n_circ)


if __name__ == "__main__":
    import sys
    import galpao_concreto as gc
    r = gc.rodar({"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
                  "v0": 40.0, "cat": "IV", "classe": "B", "G_roof": 0.30, "Q_roof": 0.25,
                  "fck": 30e3, "sigma_solo_adm": 250.0})
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(gerar_prancha(r, "armacao_galpao_concreto.svg"))
