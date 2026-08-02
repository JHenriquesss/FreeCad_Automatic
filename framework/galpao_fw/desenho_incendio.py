# ============================================================================
# desenho_incendio.py - O QUE ESTE SCRIPT FAZ / DESENHA
# Gera a PLANTA DE SEGURANCA CONTRA INCENDIO (planta de emergencia / rotas de fuga
# do AVCB) em SVG puro-Python (autocontido, sem FreeCAD/TechDraw), sobre o resultado
# de galpao_seguranca_incendio.rodar(). E o desenho-assinatura do vertical de
# incendio: e' um ESQUEMA de leiaute (nao vista do 3D), como o unifilar e' do
# eletrico. Desenha, sobre o contorno do galpao em escala:
#   - SAIDAS de emergencia nos topos + SETAS de rota de fuga apontando p/ a saida;
#   - grade de DETECTORES de fumaca (NBR 17240) e de CHUVEIROS/sprinklers (NBR 10897);
#   - BLOCOS de iluminacao de emergencia / aclaramento (NBR 10898);
#   - ACIONADORES manuais junto as saidas; PLACAS de sinalizacao de rota (NBR 16820);
#   - EXTINTORES (marcadores de referencia).
# Simbologia conforme a pratica da NBR 13434 (formas/cores de sinalizacao). As
# CONTAGENS vem do rodar(); as POSICOES sao esquematicas (grade proporcional ao
# retangulo) - o projetista ajusta ao leiaute real. O SVG abre em navegador/CAD.
# Unidades do desenho: mm no galpao -> px na tela (escala automatica).
# ============================================================================
"""Planta de seguranca contra incendio (rotas de fuga / AVCB) em SVG puro-Python
(sem FreeCAD), a partir de galpao_seguranca_incendio.rodar()."""

from __future__ import annotations

import math


# ------------------------------------------------------------- primitivas
def _t(x, y, txt, size=13, anchor="middle", weight="normal", color="#111"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}" fill="{color}">{txt}</text>')


def _line(x1, y1, x2, y2, w=1.5, color="#111", dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="{w}"{d}/>')


# ------------------------------------------------------------- simbolos
# cores da pratica NBR 13434: verde = salvamento/rota; vermelho = combate.
VERDE = "#0a7d34"
VERMELHO = "#c02128"


def _sym_saida(cx, cy, r=13):
    """Saida de emergencia: quadrado verde com figura correndo (esquematica)."""
    return (f'<rect x="{cx - r:.1f}" y="{cy - r:.1f}" width="{2 * r}" height="{2 * r}" '
            f'rx="2" fill="{VERDE}" stroke="#063f1a" stroke-width="1"/>'
            + _t(cx, cy + 4, "S", 15, weight="bold", color="white"))


def _sym_seta_rota(cx, cy, dx, dy, ln=26):
    """Seta de rota de fuga (verde) apontando na direcao (dx,dy) normalizada."""
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    x2, y2 = cx + ux * ln, cy + uy * ln
    px, py = -uy, ux                                    # perpendicular p/ a ponta
    return (_line(cx, cy, x2, y2, 3.0, VERDE)
            + f'<path d="M{x2:.1f} {y2:.1f} L{x2 - ux * 8 + px * 5:.1f} {y2 - uy * 8 + py * 5:.1f} '
              f'L{x2 - ux * 8 - px * 5:.1f} {y2 - uy * 8 - py * 5:.1f} Z" fill="{VERDE}"/>')


def _sym_detector(cx, cy, r=7):
    """Detector de fumaca: circulo com ponto central."""
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="white" '
            f'stroke="#111" stroke-width="1.3"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2" fill="#111"/>')


def _sym_sprinkler(cx, cy, r=6):
    """Chuveiro automatico: circulo vermelho com cruz."""
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="none" '
            f'stroke="{VERMELHO}" stroke-width="1.4"/>'
            + _line(cx - r, cy, cx + r, cy, 1.0, VERMELHO)
            + _line(cx, cy - r, cx, cy + r, 1.0, VERMELHO))


def _sym_bloco(cx, cy, r=6):
    """Bloco autonomo de iluminacao de emergencia / aclaramento: quadradinho amarelo."""
    return (f'<rect x="{cx - r:.1f}" y="{cy - r:.1f}" width="{2 * r}" height="{2 * r}" '
            f'fill="#f2c200" stroke="#7a6300" stroke-width="1"/>')


def _sym_baliz(cx, cy, r=3):
    """Balizamento de rota (luminaria de sinalizacao rente ao piso): ponto amarelo
    pequeno, junto as paredes."""
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="#f2c200" '
            f'stroke="#7a6300" stroke-width="0.8"/>')


def _sym_acionador(cx, cy, r=7):
    """Acionador manual: quadrado vermelho com M."""
    return (f'<rect x="{cx - r:.1f}" y="{cy - r:.1f}" width="{2 * r}" height="{2 * r}" '
            f'fill="{VERMELHO}" stroke="#5f0f13" stroke-width="1"/>'
            + _t(cx, cy + 4, "A", 11, weight="bold", color="white"))


def _sym_extintor(cx, cy):
    """Extintor: triangulo vermelho (marcador de referencia)."""
    return (f'<path d="M{cx:.1f} {cy - 8:.1f} L{cx + 7:.1f} {cy + 6:.1f} '
            f'L{cx - 7:.1f} {cy + 6:.1f} Z" fill="{VERMELHO}" stroke="#5f0f13" '
            f'stroke-width="1"/>')


def _sym_hidrante(cx, cy, r=7):
    """Hidrante/mangotinho: quadrado vermelho com H (abrigo de mangueira)."""
    return (f'<rect x="{cx - r:.1f}" y="{cy - r:.1f}" width="{2 * r}" height="{2 * r}" '
            f'fill="white" stroke="{VERMELHO}" stroke-width="2"/>'
            + _t(cx, cy + 4, "H", 11, weight="bold", color=VERMELHO))


def _sym_placa(cx, cy, r=6):
    """Placa de sinalizacao de rota: losango verde."""
    return (f'<path d="M{cx:.1f} {cy - r:.1f} L{cx + r:.1f} {cy:.1f} '
            f'L{cx:.1f} {cy + r:.1f} L{cx - r:.1f} {cy:.1f} Z" fill="{VERDE}" '
            f'stroke="#063f1a" stroke-width="1"/>')


# ----------------------------------------------------------- leiaute
def _grade(n, C, L):
    """Distribui n pontos numa grade proporcional ao retangulo C x L. Devolve
    (cols, rows) com cols*rows >= n e proporcao ~ C/L."""
    if n <= 1:
        return 1, 1
    razao = (C / L) if L else 1.0
    cols = max(1, int(round(math.sqrt(n * razao))))
    rows = max(1, math.ceil(n / cols))
    return cols, rows


def _pontos_grade(x0, y0, w, h, cols, rows):
    """Centros das celulas de uma grade cols x rows dentro do retangulo (margem meia
    celula das bordas)."""
    pts = []
    for j in range(rows):
        for i in range(cols):
            px = x0 + (i + 0.5) * w / cols
            py = y0 + (j + 0.5) * h / rows
            pts.append((px, py))
    return pts


def _pontos_exatos(n, x0, y0, w, h, C, L):
    """EXATAMENTE n pontos numa grade proporcional (cols*rows >= n, cortado em n).
    Sem isso, cols*rows > n desenharia MAIS simbolos do que a contagem do resumo
    (drawing != data). Ver [[varredura-rotulo-takeoff]]."""
    if n <= 0:
        return []
    cols, rows = _grade(n, C, L)
    return _pontos_grade(x0, y0, w, h, cols, rows)[:n]


def _pontos_perimetro(n, x0, y0, w, h, inset=8.0):
    """EXATAMENTE n pontos igualmente espacados no perimetro do retangulo (recuado de
    `inset` px), para elementos rente as paredes (balizamento)."""
    if n <= 0:
        return []
    ax, ay, bx, by = x0 + inset, y0 + inset, x0 + w - inset, y0 + h - inset
    pw, ph = max(bx - ax, 0.0), max(by - ay, 0.0)
    per = 2.0 * (pw + ph) or 1.0
    pts = []
    for k in range(n):
        d = (k + 0.5) * per / n
        if d <= pw:
            px, py = ax + d, ay
        elif d <= pw + ph:
            px, py = bx, ay + (d - pw)
        elif d <= 2.0 * pw + ph:
            px, py = bx - (d - pw - ph), by
        else:
            px, py = ax, by - (d - 2.0 * pw - ph)
        pts.append((px, py))
    return pts


def planta_seguranca_svg(r):
    """Planta de seguranca contra incendio a partir de r=rodar(). String SVG.
    Escala o contorno do galpao ao canvas e posiciona os simbolos por contagem."""
    g = r["gates"]
    sp = r["spec"]
    C = float(sp["C"]); L = float(sp["L"])              # comprimento x largura (m)

    W, Hh = 1000, 620
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" '
         f'viewBox="0 0 {W} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         _t(W / 2, 30, "PLANTA DE SEGURANCA CONTRA INCENDIO - ROTAS DE FUGA", 19,
            weight="bold")]

    # area de desenho do galpao (deixa faixa lateral p/ a legenda)
    mx, my = 60, 60
    aw, ah = 640, 480
    # escala isometrica preservando proporcao C x L
    esc = min(aw / C, ah / L)
    gw, gh = C * esc, L * esc
    x0 = mx + (aw - gw) / 2.0
    y0 = my + (ah - gh) / 2.0

    # contorno do galpao
    s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{gw:.1f}" height="{gh:.1f}" '
             f'fill="#fafafa" stroke="#111" stroke-width="2"/>')
    s.append(_t(x0 + gw / 2, y0 - 8, "%.0f m" % C, 12))
    s.append(_t(x0 - 30, y0 + gh / 2, "%.0f m" % L, 12))

    # --- CHUVEIROS (grade vermelha) - EXATAMENTE N_chuveiros (== resumo)
    if g["sprinklers"]["N_chuveiros"]:
        nc = int(g["sprinklers"]["N_chuveiros"])
        for (px, py) in _pontos_exatos(nc, x0, y0, gw, gh, C, L):
            s.append(_sym_sprinkler(px, py))

    # --- DETECTORES (grade preta) - EXATAMENTE N_detectores ; so pontual (linear = feixes)
    nd = int(g["deteccao_alarme"]["N_detectores"])
    if g["deteccao_alarme"]["tipo_detector"] == "pontual":
        for (px, py) in _pontos_exatos(nd, x0, y0, gw, gh, C, L):
            s.append(_sym_detector(px, py))
    else:
        # detector linear: feixes horizontais ao longo do comprimento
        for j in range(min(nd, 6)):
            yy = y0 + (j + 0.5) * gh / min(nd, 6)
            s.append(_line(x0 + 6, yy, x0 + gw - 6, yy, 1.2, "#111", dash="6 4"))

    # --- ILUMINACAO DE EMERGENCIA (NBR 10898): count-driven (== resumo/BIM).
    # ACLARAMENTO: EXATAMENTE N_aclaramento no teto (grade proporcional). Antes usava
    # uma grade FIXA 2x2 (chave 'grade' inexistente -> sempre 4), divergindo do resumo
    # (N_aclaramento=6). Ver [[varredura-rotulo-takeoff]].
    nac_l = int(g["iluminacao_emergencia"]["N_aclaramento"] or 0)
    for (px, py) in _pontos_exatos(nac_l, x0, y0, gw, gh, C, L):
        s.append(_sym_bloco(px, py))
    # BALIZAMENTO: EXATAMENTE N_balizamento rente as paredes (perimetro).
    nbal = int(g["iluminacao_emergencia"]["N_balizamento"] or 0)
    for (px, py) in _pontos_perimetro(nbal, x0, y0, gw, gh):
        s.append(_sym_baliz(px, py))

    # --- SAIDAS de emergencia nos dois topos (comprimento) + setas de rota
    ys = y0 + gh / 2
    s.append(_sym_saida(x0 - 2, ys))                    # saida esquerda
    s.append(_sym_saida(x0 + gw + 2, ys))               # saida direita
    s.append(_sym_seta_rota(x0 + gw * 0.30, ys, -1, 0))
    s.append(_sym_seta_rota(x0 + gw * 0.70, ys, 1, 0))
    # ACIONADORES: exatamente N_acionadores (mesma contagem do resumo), junto as
    # saidas primeiro e o excedente distribuido ao longo da parede.
    na = int(g["deteccao_alarme"]["N_acionadores"])
    fracs_ac = [0.0, 1.0] + [k / (na + 1.0) for k in range(1, max(0, na - 2) + 1)]
    for k in range(na):
        s.append(_sym_acionador(x0 + gw * fracs_ac[k], ys - 26))
    # PLACAS de sinalizacao: EXATAMENTE N_placas ao longo da rota central (== resumo).
    np = int(g["sinalizacao"]["N_placas"])
    for k in range(max(np, 0)):
        frac = (k + 0.5) / np
        s.append(_sym_placa(x0 + gw * frac, ys - 40))
    # extintores nos cantos
    for (fx, fy) in ((0.06, 0.10), (0.94, 0.10), (0.06, 0.90), (0.94, 0.90)):
        s.append(_sym_extintor(x0 + gw * fx, y0 + gh * fy))
    # HIDRANTES (NBR 13714): N_hidrantes distribuidos junto ao perimetro (<= 5 m das
    # portas, 5.2.1). count-driven -> a planta acompanha o resumo.
    nh = int(g["hidrantes"]["N_hidrantes"] or 0)
    for k in range(nh):
        frac = (k + 0.5) / nh
        s.append(_sym_hidrante(x0 + gw * frac, y0 + gh - 14))     # rente a parede inferior

    # --------------------------------------------------------- LEGENDA
    lx, ly = 730, 70
    ys_leg = [48, 74, 100, 126, 152, 178, 204, 230, 256, 282]
    s.append(f'<rect x="{lx}" y="{ly}" width="230" height="{ys_leg[-1] + 32}" '
             f'fill="white" stroke="#111" stroke-width="1"/>')
    s.append(_t(lx + 115, ly + 22, "LEGENDA", 14, weight="bold"))
    itens = [
        (_sym_saida(lx + 20, ly + ys_leg[0], 11), "Saida de emergencia"),
        (_sym_seta_rota(lx + 12, ly + ys_leg[1], 1, 0, 20), "Rota de fuga"),
        (_sym_detector(lx + 20, ly + ys_leg[2]), "Detector de fumaca"),
        (_sym_sprinkler(lx + 20, ly + ys_leg[3]), "Chuveiro automatico"),
        (_sym_hidrante(lx + 20, ly + ys_leg[4]), "Hidrante (NBR 13714)"),
        (_sym_bloco(lx + 20, ly + ys_leg[5]), "Aclaramento (teto)"),
        (_sym_baliz(lx + 20, ly + ys_leg[6]), "Balizamento (rota)"),
        (_sym_acionador(lx + 20, ly + ys_leg[7]), "Acionador manual"),
        (_sym_placa(lx + 20, ly + ys_leg[8]), "Sinalizacao de rota"),
        (_sym_extintor(lx + 20, ly + ys_leg[9]), "Extintor"),
    ]
    for (sym, txt), yy in zip(itens, ys_leg):
        s.append(sym)
        s.append(_t(lx + 40, ly + yy + 4, txt, 12, anchor="start"))

    # --------------------------------------------------------- QUADRO-RESUMO
    qx, qy = 730, 415
    linhas = [
        "Detectores: %d (%s)" % (nd, g["deteccao_alarme"]["tipo_detector"]),
        "Acionadores: %d" % g["deteccao_alarme"]["N_acionadores"],
        "Placas de rota: %d" % g["sinalizacao"]["N_placas"],
        "Aclaramento: %d pts" % g["iluminacao_emergencia"]["N_aclaramento"],
        "Balizamento: %d pts" % g["iluminacao_emergencia"]["N_balizamento"],
    ]
    if g["sprinklers"]["N_chuveiros"]:
        linhas.append("Chuveiros: %d (%s)" % (g["sprinklers"]["N_chuveiros"],
                                              g["sprinklers"]["risco"]))
        linhas.append("Reserva chuv.: %.0f m3" % g["sprinklers"]["reserva_m3"])
    if g["hidrantes"]["tipo"]:
        linhas.append("Hidrantes: %d (tipo %d)" % (g["hidrantes"]["N_hidrantes"],
                                                   g["hidrantes"]["tipo"]))
        linhas.append("Reserva hidr.: %.0f m3" % g["hidrantes"]["reserva_m3"])
    box_h = 34 + len(linhas) * 17
    s.append(f'<rect x="{qx}" y="{qy}" width="230" height="{box_h}" fill="white" '
             f'stroke="#111" stroke-width="1"/>')
    s.append(_t(qx + 115, qy + 20, "RESUMO", 14, weight="bold"))
    for i, ln in enumerate(linhas):
        s.append(_t(qx + 14, qy + 40 + i * 17, ln, 12, anchor="start"))

    s.append('</svg>')
    return "\n".join(s)


def gerar_planta(r, path):
    """Escreve a planta de seguranca contra incendio (SVG) em `path`."""
    svg = planta_seguranca_svg(r)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


def _selftest():
    import galpao_seguranca_incendio as gsi
    r = gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                   "deteccao": {"viga_m": 0.0}, "sprinklers": {"altura_estoque_m": 3.0}})
    svg = planta_seguranca_svg(r)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    # a planta cita os elementos-chave do AVCB
    for termo in ("SEGURANCA CONTRA INCENDIO", "LEGENDA", "RESUMO", "Detector",
                  "Chuveiro", "Saida de emergencia"):
        assert termo in svg, termo
    # grade de detectores proporcional (10 detectores no galpao 40x20)
    c, rr = _grade(10, 40.0, 20.0)
    assert c * rr >= 10 and c >= rr                      # mais colunas (galpao comprido)
    print("desenho_incendio self-test PASSED")


if __name__ == "__main__":
    _selftest()
