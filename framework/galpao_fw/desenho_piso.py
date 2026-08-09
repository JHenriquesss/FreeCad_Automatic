# ============================================================================
# desenho_piso.py - O QUE ESTE SCRIPT FAZ / DESENHA
# Gera a PLANTA DE JUNTAS do piso industrial em SVG puro-Python (autocontido, sem
# FreeCAD/TechDraw) a partir do resultado de piso_industrial.verifica_piso(). A
# planta mostra a malha de paineis (juntas serradas de retracao), as cotas dos
# paineis e um quadro com a espessura adotada, fck, coeficiente de reacao do
# subleito k, a resistencia a flexao de projeto e o reforco. O SVG e' XML valido
# (texto escapado com _esc: um '<' cru quebraria o render estrito QtSvg/TechDraw).
# ============================================================================
"""Planta de juntas do piso industrial (SVG puro-Python) a partir de
piso_industrial.verifica_piso()."""

from __future__ import annotations


def _esc(txt):
    """Escapa &<> p/ XML valido (SVG e' XML)."""
    return str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _t(x, y, txt, size=13, anchor="middle", weight="normal", color="#111"):
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-family="Arial" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}" fill="{color}">{_esc(txt)}</text>')


def planta_juntas_svg(r):
    """r: dict de piso_industrial.verifica_piso() (com OK, h_cm, juntas, ...).
    Devolve o SVG (str). Se o piso reprovou/A CONFIRMAR, desenha um aviso."""
    Wc, Hh = 1120, 760
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wc}" height="{Hh}" '
           f'viewBox="0 0 {Wc} {Hh}" font-family="Arial">',
           f'<rect x="0" y="0" width="{Wc}" height="{Hh}" fill="#ffffff"/>',
           _t(Wc / 2, 40, "PLANTA DE JUNTAS - PISO INDUSTRIAL", 22, weight="bold")]

    if not r.get("OK") or "juntas" not in r:
        out.append(_t(Wc / 2, Hh / 2, r.get("motivo", "piso nao dimensionado "
                      "(A CONFIRMAR cargas de operacao)"), 15, color="#b00"))
        out.append("</svg>")
        return "\n".join(out)

    j = r["juntas"]
    nx, ny = j["paineis_x"], j["paineis_y"]
    px, py = j["painel_m"]
    L = nx * px; W = ny * py

    # area de desenho (mantem proporcao L x W)
    ax0, ay0, aw, ah = 105, 90, 680, 470
    esc = min(aw / L, ah / W)
    dw, dh = L * esc, W * esc
    x0 = ax0 + (aw - dw) / 2.0
    y0 = ay0 + (ah - dh) / 2.0

    # contorno do piso
    out.append(f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{dw:.0f}" height="{dh:.0f}" '
               f'fill="#eef3f8" stroke="#111" stroke-width="2.5"/>')
    # juntas serradas (grade de paineis)
    for i in range(1, nx):
        xx = x0 + i * px * esc
        out.append(f'<line x1="{xx:.0f}" y1="{y0:.0f}" x2="{xx:.0f}" y2="{y0+dh:.0f}" '
                   f'stroke="#c0392b" stroke-width="1.2" stroke-dasharray="7 4"/>')
    for i in range(1, ny):
        yy = y0 + i * py * esc
        out.append(f'<line x1="{x0:.0f}" y1="{yy:.0f}" x2="{x0+dw:.0f}" y2="{yy:.0f}" '
                   f'stroke="#c0392b" stroke-width="1.2" stroke-dasharray="7 4"/>')
    # cotas gerais
    out.append(_t(x0 + dw / 2, y0 + dh + 30, f"L = {L:.1f} m  ({nx} paineis de {px:.2f} m)", 13))
    out.append(_t(x0 - 12, y0 + dh / 2, f"W = {W:.1f} m", 13, anchor="end"))
    out.append(_t(x0 + px * esc / 2, y0 + py * esc / 2, "painel\ntipico", 11, color="#555")
               .replace("\n", " "))

    # quadro de especificacoes (direita)
    qx, qy = 830, 110
    reforco = r.get("reforco", {})
    linhas = [
        ("Espessura da placa", f"{r['h_cm']:.0f} cm"),
        ("Concreto", f"C{r['fck_MPa']:.0f}  (fct,f,d {r.get('fctfd_MPa', 0):.2f} MPa)"),
        ("Subleito k", f"{r['k_MN_m3']:.0f} MN/m3"),
        ("Junta max (serrada)", f"{j['espac_max_m']:.2f} m"),
        ("Paineis", f"{nx} x {ny} = {j['n_paineis']}"),
        ("Reforco (retracao)", f"tela ~{reforco.get('tela_retracao_As_cm2_m', 0):.1f} cm2/m"),
        ("Volume de concreto", f"{r.get('volume_concreto_m3', 0):.0f} m3"),
        ("Area", f"{r.get('area_m2', 0):.0f} m2"),
    ]
    out.append(f'<rect x="{qx}" y="{qy}" width="260" height="{28*len(linhas)+40}" '
               f'fill="#fafafa" stroke="#111" stroke-width="1.2"/>')
    out.append(_t(qx + 130, qy + 26, "RESUMO DO PISO", 14, weight="bold"))
    for i, (k, v) in enumerate(linhas):
        yy = qy + 52 + i * 28
        out.append(_t(qx + 12, yy, k, 12, anchor="start", color="#333"))
        out.append(_t(qx + 248, yy, v, 12, anchor="end", weight="bold"))

    # legenda + cargas
    ly = ay0 + ah + 70
    out.append(_t(ax0, ly, "JUNTAS SERRADAS DE RETRACAO (linha tracejada vermelha) - "
                 "profundidade 1/3 da espessura, seladas.", 12, anchor="start", color="#333"))
    pontos = r.get("pontos", [])
    if pontos:
        cargas = "; ".join(f"{p.get('nome','carga')} {p['P_kN']:.0f} kN "
                           f"(util {p['util']:.2f})" for p in pontos)
        out.append(_t(ax0, ly + 24, "Cargas de operacao: " + cargas, 12,
                      anchor="start", color="#333"))
    out.append(_t(ax0, ly + 48, "Metodo: placa sobre solo de Winkler + Westergaard; "
                 "material NBR 6118 8.2.5 (tracao na flexao).", 11, anchor="start", color="#666"))

    out.append("</svg>")
    return "\n".join(out)


def gerar_planta_juntas(r, path):
    """Grava o SVG da planta de juntas em `path`."""
    svg = planta_juntas_svg(r)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


def _selftest():
    import piso_industrial as pi
    from xml.dom.minidom import parseString
    r = pi.verifica_piso({"L": 40.0, "W": 20.0, "fck_MPa": 30.0, "k_MN_m3": 60.0,
                          "cargas": [{"nome": "empilhadeira 3t", "P_kN": 30.0,
                                      "area_contato_cm2": 300.0}]})
    svg = planta_juntas_svg(r)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    parseString(svg.encode("utf-8"))                        # XML valido (parse)
    assert "PLANTA DE JUNTAS" in svg and "RESUMO DO PISO" in svg
    # caminho A CONFIRMAR tambem e' XML valido
    r2 = pi.verifica_piso({"L": 10, "W": 10})
    parseString(planta_juntas_svg(r2).encode("utf-8"))
    return True


if __name__ == "__main__":
    _selftest()
    print("selftest OK")
