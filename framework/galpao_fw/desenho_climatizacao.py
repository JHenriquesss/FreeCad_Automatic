# ============================================================================
# desenho_climatizacao.py - O QUE ESTE SCRIPT DESENHA
# Esquema da rede de CLIMATIZACAO (HVAC) do galpao em SVG puro-Python (sem FreeCAD),
# sobre galpao_climatizacao.rodar(). Desenho-assinatura do executivo de climatizacao:
# mostra, sobre o contorno do galpao, o DUTO TRONCO no eixo, os RAMAIS transversais e
# a UTA (unidade de tratamento de ar), com a secao do duto e a capacidade rotuladas.
# Posicoes esquematicas (o projetista ajusta ao leiaute real). NBR 16401.
# ============================================================================
"""Esquema da rede de climatizacao (HVAC: tronco/ramais/UTA + capacidade) em SVG
puro-Python, a partir de galpao_climatizacao.rodar()."""

from __future__ import annotations

COR_DUTO = "#0891b2"
COR_UTA = "#7c3aed"


def _t(x, y, txt, size=13, anchor="middle", weight="normal", color="#111"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}" fill="{color}">{txt}</text>')


def _line(x1, y1, x2, y2, w=1.5, color="#111"):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="{w}"/>')


def esquema_climatizacao_svg(r):
    """Planta esquematica da rede de climatizacao a partir de r=rodar(). String SVG."""
    geo = r["geometria"]
    C = float(geo["L"]); Lg = float(geo["W"])           # comprimento x largura (m)
    duto = r["duto"]
    cap = r["gates"]["capacidade"]
    dp = r["gates"]["duto_principal"]
    n_ram = int(r.get("n_ramais", 4))

    W, Hh = 1000, 640
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" '
         f'viewBox="0 0 {W} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         _t(W / 2, 30, "ESQUEMA DA REDE DE CLIMATIZACAO (HVAC)", 19, weight="bold")]

    mx, my, aw, ah = 60, 60, 620, 480
    esc = min(aw / C, ah / Lg)
    gw, gh = C * esc, Lg * esc
    x0 = mx + (aw - gw) / 2.0
    y0 = my + (ah - gh) / 2.0
    s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{gw:.1f}" height="{gh:.1f}" '
             f'fill="#fafafa" stroke="#111" stroke-width="2"/>')
    s.append(_t(x0 + gw / 2, y0 - 8, "%.0f m" % C, 12))
    s.append(_t(x0 - 30, y0 + gh / 2, "%.0f m" % Lg, 12))

    # DUTO TRONCO no eixo central (comprimento)
    yc = y0 + gh / 2
    s.append(_line(x0, yc, x0 + gw, yc, 5.0, COR_DUTO))
    s.append(_t(x0 + gw / 2, yc - 10, "Tronco %.2f x %.2f m @ %.1f m/s"
                % (duto["largura_m"], duto["altura_m"], dp["vel_ms"]), 11, color=COR_DUTO))
    # RAMAIS transversais
    for i in range(max(0, n_ram)):
        rx = x0 + (i + 0.5) * gw / n_ram
        s.append(_line(rx, y0 + 6, rx, y0 + gh - 6, 2.5, COR_DUTO))
    # UTA junto a uma empena
    ux, uy = x0 - 34, yc
    s.append(f'<rect x="{ux - 16:.1f}" y="{uy - 18:.1f}" width="32" height="36" '
             f'fill="{COR_UTA}" stroke="#4c1d95" stroke-width="1"/>')
    s.append(_t(ux, uy + 34, "UTA", 11, weight="bold", color=COR_UTA))

    # --- QUADRO de capacidade / duto ---
    qx, qy = 715, 90
    linhas = [
        "Capacidade: %.1f TR" % cap["TR"],
        "  (%.1f kW ; %.0f BTU/h)" % (cap["kW"], cap["BTU_h"]),
        "Vazao insufl.: %.0f m3/h" % dp["vazao_m3h"],
        "Duto tronco: %.2f x %.2f m" % (duto["largura_m"], duto["altura_m"]),
        "Velocidade: %.1f m/s" % dp["vel_ms"],
        "  (max %.1f m/s, classe %d Pa)" % (dp["vel_max_ms"], dp["classe_pa"]),
        "Ramais: %d" % n_ram,
    ]
    box_h = 34 + len(linhas) * 19
    s.append(f'<rect x="{qx}" y="{qy}" width="245" height="{box_h}" fill="white" '
             f'stroke="#111" stroke-width="1"/>')
    s.append(_t(qx + 122, qy + 22, "CAPACIDADE / DUTO", 13, weight="bold"))
    for i, ln in enumerate(linhas):
        s.append(_t(qx + 14, qy + 44 + i * 19, ln, 11, anchor="start"))
    s.append(_t(qx + 14, qy + box_h + 24, "NBR 16401-1 (Tab.1 velocidade)", 10,
                anchor="start", color="#555"))

    s.append('</svg>')
    return "\n".join(s)     # NAO aplicar virgula decimal no SVG (corromperia coordenadas)


def gerar_esquema(r, path):
    svg = esquema_climatizacao_svg(r)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


def _selftest():
    import galpao_climatizacao as gc
    r = gc.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "tipo": "galpao"})
    svg = esquema_climatizacao_svg(r)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    for termo in ("CLIMATIZACAO", "Tronco", "UTA", "Capacidade", "Vazao insufl",
                  "NBR 16401"):
        assert termo in svg, termo
    print("desenho_climatizacao self-test PASSED")


if __name__ == "__main__":
    _selftest()
