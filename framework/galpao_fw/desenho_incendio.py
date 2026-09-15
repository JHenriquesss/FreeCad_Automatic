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
# Simbologia conforme a pratica da NBR 16820 (formas/cores de sinalizacao). As
# CONTAGENS vem do rodar(); as POSICOES sao esquematicas (grade proporcional ao
# retangulo) - o projetista ajusta ao leiaute real. O SVG abre em navegador/CAD.
# Unidades do desenho: mm no galpao -> px na tela (escala automatica).
# ============================================================================
"""Planta de seguranca contra incendio (rotas de fuga / AVCB) em SVG puro-Python
(sem FreeCAD), a partir de galpao_seguranca_incendio.rodar()."""

from __future__ import annotations

import math


# Primitivas (escape XML + texto + linha) unificadas em desenho_svg_base (G56):
# uma copia de _esc por modulo e o berco do bug de dupla-escapa do residencial.
from desenho_svg_base import (  # noqa: E402
    esc as _esc,
    linha as _line,
    texto as _t,
)


# ------------------------------------------------------------- simbolos
# cores da pratica NBR 16820: verde = salvamento/rota; vermelho = combate.
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

    # G77: a legenda passa a sair do que foi DESENHADO. Ela era uma lista fixa
    # de 10 itens enquanto a planta e' count-driven: sem hidrante projetado, a
    # folha entregue anunciava o simbolo de hidrante e o leitor procurava na
    # planta um equipamento que ninguem dimensionou. Mesmo criterio que
    # `desenho_coordenacao` ja aplica a suas disciplinas.
    desenhado = set()

    # --- CHUVEIROS (grade vermelha) - EXATAMENTE N_chuveiros (== resumo)
    if g["sprinklers"]["N_chuveiros"]:
        desenhado.add("sprinkler")
        nc = int(g["sprinklers"]["N_chuveiros"])
        for (px, py) in _pontos_exatos(nc, x0, y0, gw, gh, C, L):
            s.append(_sym_sprinkler(px, py))

    # --- DETECTORES (grade preta) - EXATAMENTE N_detectores ; so pontual (linear = feixes)
    nd = int(g["deteccao_alarme"]["N_detectores"])
    if g["deteccao_alarme"]["tipo_detector"] == "pontual":
        if nd:
            desenhado.add("detector")
        for (px, py) in _pontos_exatos(nd, x0, y0, gw, gh, C, L):
            s.append(_sym_detector(px, py))
    else:
        # detector LINEAR nao usa o simbolo pontual: a legenda diz o que a
        # planta mostra (feixe), nao o que o catalogo tem.
        if nd:
            desenhado.add("detector_linear")
        # detector linear: feixes horizontais ao longo do comprimento
        for j in range(min(nd, 6)):
            yy = y0 + (j + 0.5) * gh / min(nd, 6)
            s.append(_line(x0 + 6, yy, x0 + gw - 6, yy, 1.2, "#111", dash="6 4"))

    # --- ILUMINACAO DE EMERGENCIA (NBR 10898): count-driven (== resumo/BIM).
    # ACLARAMENTO: EXATAMENTE N_aclaramento no teto (grade proporcional). Antes usava
    # uma grade FIXA 2x2 (chave 'grade' inexistente -> sempre 4), divergindo do resumo
    # (N_aclaramento=6). Ver [[varredura-rotulo-takeoff]].
    nac_l = int(g["iluminacao_emergencia"]["N_aclaramento"] or 0)
    if nac_l:
        desenhado.add("aclaramento")
    for (px, py) in _pontos_exatos(nac_l, x0, y0, gw, gh, C, L):
        s.append(_sym_bloco(px, py))
    # BALIZAMENTO: EXATAMENTE N_balizamento rente as paredes (perimetro).
    nbal = int(g["iluminacao_emergencia"]["N_balizamento"] or 0)
    if nbal:
        desenhado.add("balizamento")
    for (px, py) in _pontos_perimetro(nbal, x0, y0, gw, gh):
        s.append(_sym_baliz(px, py))

    # --- SAIDAS de emergencia nos dois topos (comprimento) + setas de rota
    ys = y0 + gh / 2
    desenhado.update({"saida", "rota", "extintor"})     # sempre desenhados
    s.append(_sym_saida(x0 - 2, ys))                    # saida esquerda
    s.append(_sym_saida(x0 + gw + 2, ys))               # saida direita
    s.append(_sym_seta_rota(x0 + gw * 0.30, ys, -1, 0))
    s.append(_sym_seta_rota(x0 + gw * 0.70, ys, 1, 0))
    # ACIONADORES: exatamente N_acionadores (mesma contagem do resumo), junto as
    # saidas primeiro e o excedente distribuido ao longo da parede.
    na = int(g["deteccao_alarme"]["N_acionadores"])
    if na:
        desenhado.add("acionador")
    fracs_ac = [0.0, 1.0] + [k / (na + 1.0) for k in range(1, max(0, na - 2) + 1)]
    for k in range(na):
        s.append(_sym_acionador(x0 + gw * fracs_ac[k], ys - 26))
    # PLACAS de sinalizacao: EXATAMENTE N_placas ao longo da rota central (== resumo).
    np = int(g["sinalizacao"]["N_placas"])
    if np:
        desenhado.add("placa")
    for k in range(max(np, 0)):
        frac = (k + 0.5) / np
        s.append(_sym_placa(x0 + gw * frac, ys - 40))
    # extintores nos cantos
    for (fx, fy) in ((0.06, 0.10), (0.94, 0.10), (0.06, 0.90), (0.94, 0.90)):
        s.append(_sym_extintor(x0 + gw * fx, y0 + gh * fy))
    # HIDRANTES (NBR 13714): N_hidrantes distribuidos junto ao perimetro (<= 5 m das
    # portas, 5.2.1). count-driven -> a planta acompanha o resumo.
    nh = int(g["hidrantes"]["N_hidrantes"] or 0)
    if nh:
        desenhado.add("hidrante")
    for k in range(nh):
        frac = (k + 0.5) / nh
        s.append(_sym_hidrante(x0 + gw * frac, y0 + gh - 14))     # rente a parede inferior

    # --------------------------------------------------------- LEGENDA
    lx, ly = 730, 70
    #: (chave do que foi desenhado, desenhista do simbolo, rotulo). A ordem e' a
    #: da planta; so entra o que a planta mostra.
    catalogo = [
        ("saida", lambda y: _sym_saida(lx + 20, y, 11), "Saida de emergencia"),
        ("rota", lambda y: _sym_seta_rota(lx + 12, y, 1, 0, 20), "Rota de fuga"),
        ("detector", lambda y: _sym_detector(lx + 20, y), "Detector de fumaca"),
        ("detector_linear", lambda y: _line(lx + 8, y, lx + 32, y, 1.2, "#111",
                                            dash="6 4"),
         "Detector linear (feixe)"),
        ("sprinkler", lambda y: _sym_sprinkler(lx + 20, y), "Chuveiro automatico"),
        ("hidrante", lambda y: _sym_hidrante(lx + 20, y), "Hidrante (NBR 13714)"),
        ("aclaramento", lambda y: _sym_bloco(lx + 20, y), "Aclaramento (teto)"),
        ("balizamento", lambda y: _sym_baliz(lx + 20, y), "Balizamento (rota)"),
        ("acionador", lambda y: _sym_acionador(lx + 20, y), "Acionador manual"),
        ("placa", lambda y: _sym_placa(lx + 20, y), "Sinalizacao de rota"),
        ("extintor", lambda y: _sym_extintor(lx + 20, y), "Extintor"),
    ]
    itens = [(dez, txt) for chave, dez, txt in catalogo if chave in desenhado]
    ys_leg = [48 + 26 * k for k in range(len(itens))]
    altura_leg = (ys_leg[-1] if ys_leg else 48) + 32
    s.append(f'<rect x="{lx}" y="{ly}" width="230" height="{altura_leg}" '
             f'fill="white" stroke="#111" stroke-width="1"/>')
    s.append(_t(lx + 115, ly + 22, "LEGENDA", 14, weight="bold"))
    for (dez, txt), yy in zip(itens, ys_leg):
        s.append(dez(ly + yy))
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


# ---------------------------------------------------------------------------
# PRANCHAS DO EDIFICIO (G56) - PPCI por pavimento + detalhes
# ---------------------------------------------------------------------------
# O emissor do galpao desenha um pavimento terrio isolado. O predio repete o
# pavimento N vezes empilhado e a escada vira rota vertical: a planta sai por
# pavimento-tipo (parametro) e os hidrantes ganham o corte da coluna DN65.
# Parametro, nao um desenho_incendio_edificio.py paralelo.

def _edificio_C_L(estrutura):
    pav = (estrutura or {}).get("pavimento") or {}
    try:
        return float(sum(pav["vaos_x"])), float(sum(pav["vaos_y"]))
    except Exception:
        return 14.0, 9.0


def planta_pavimento_edificio_svg(inc, estrutura, pavimento=None):
    """PE-IN-01 PPCI do pavimento-tipo: saidas + rotas, hidrantes, detectores,
    sinalizacao e iluminacao - contagens == sistemas calculados."""
    C, L = _edificio_C_L(estrutura)
    sist = inc.get("sistemas") or {}
    det = sist.get("deteccao_alarme") or {}
    hid = sist.get("hidrantes") or {}
    sin = sist.get("sinalizacao") or {}
    ilu = sist.get("iluminacao_emergencia") or {}
    n_det = int(det.get("N_detectores") or 0)
    n_hid = int(hid.get("N_hidrantes") or 0)
    n_placas = int(sin.get("N_total") or 0)
    rot = pavimento or "PAVIMENTO-TIPO"
    W, Hh = 1000, 640
    mx, my, aw, ah = 50, 90, 620, 460
    esc = min(aw / C, ah / L)
    gw, gh = C * esc, L * esc
    x0 = mx + (aw - gw) / 2.0
    y0 = my + (ah - gh) / 2.0
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" '
         f'viewBox="0 0 {W} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         _t(W / 2, 34, "PPCI - PLANTA %s" % rot.upper(), 19, weight="bold"),
         f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{gw:.0f}" height="{gh:.0f}" '
         f'fill="#fafafa" stroke="#111" stroke-width="2"/>']
    # detectores: EXATAMENTE N_detectores (drawing-vs-data)
    for k, (px, py) in enumerate(_pontos_exatos(n_det, x0, y0, gw, gh, C, L)):
        s.append(_sym_detector(px, py))
        s.append(_t(px, py - 12, "DET-%d" % (k + 1), 9, color="#111"))
    # saidas nos topos + setas de rota
    ys = y0 + gh / 2
    s.append(_sym_saida(x0 - 2, ys))
    s.append(_sym_saida(x0 + gw + 2, ys))
    s.append(_sym_seta_rota(x0 + gw * 0.30, ys, -1, 0))
    s.append(_sym_seta_rota(x0 + gw * 0.70, ys, 1, 0))
    # hidrantes: EXATAMENTE N_hidrantes rente a parede inferior
    for k in range(n_hid):
        frac = (k + 0.5) / n_hid
        s.append(_sym_hidrante(x0 + gw * frac, y0 + gh - 14))
    # placas de sinalizacao ao longo da rota (simbolo, sem rotulo)
    for k in range(max(n_placas, 0)):
        frac = (k + 0.5) / n_placas
        s.append(_sym_placa(x0 + gw * frac, ys - 40))
    # aclaramento no teto (simbolo, sem rotulo)
    for (px, py) in _pontos_exatos(int(ilu.get("N_aclaramento") or 0),
                                   x0, y0, gw, gh, C, L):
        s.append(_sym_bloco(px, py))
    lx, ly = 710, 100
    s.append(f'<rect x="{lx}" y="{ly}" width="250" height="220" fill="white" '
             f'stroke="#111" stroke-width="1"/>')
    s.append(_t(lx + 125, ly + 24, "RESUMO DO PAVIMENTO", 13, weight="bold"))
    for i, ln in enumerate([
            "Detectores: %d" % n_det,
            "Acionadores: %d" % int(det.get("N_acionadores") or 0),
            "Hidrantes: %d (tipo %s)" % (n_hid, hid.get("tipo", "?")),
            "Placas de rota: %d" % n_placas,
            "Aclaramento: %d pts" % int(ilu.get("N_aclaramento") or 0),
            "Populacao total: %d" % int(inc.get("populacao_total") or 0)]):
        s.append(_t(lx + 14, ly + 52 + i * 24, ln, 11, anchor="start"))
    s.append('</svg>')
    return "\n".join(s)


# G138 (D168): o que o calculo do galpao NAO produz para o corte de
# hidrantes — medido em 2026-09-14 contra `galpao_seguranca_incendio.rodar`
# (gates: iluminacao/sinalizacao/deteccao/sprinklers/hidrantes; spec C/L/H)
# e o que `detalhes_hidrantes_rotas_svg` le (shape do predio:
# inc.sistemas.hidrantes + inc.gates.rotas_verticais/escada_largura +
# inc.estrategia_abandono/populacao_total/altura_edificacao_m +
# estrutura.pavimentos). Uma fonte so: esta lista mora na producao e a
# folha a declara, nunca inventa.
AUSENCIAS_GALPAO_DETALHES = (
    "gates.rotas_verticais (n_minimo/n_declarado)",
    "gates.escada_largura (largura_exigida_m)",
    "estrategia_abandono",
    "populacao_total",
    "altura_edificacao_m",
    "estrutura.pavimentos (galpao terreo, nivel unico)",
)


def adaptar_galpao_para_detalhes(r):
    """Adapta o resultado de `galpao_seguranca_incendio.rodar` para o emissor
    de detalhes de hidrantes (shape do predio), sem recalcular nada.

    Devolve (inc, estrutura, ausentes): `inc`/`estrutura` no shape que
    `detalhes_hidrantes_rotas_svg` le, lidos do calculo (o `hidrantes` cru
    de `r["hidrantes"]`, com `reserva_incendio_m3` original — nunca o gate
    reescrito `reserva_m3`); `ausentes` e o subconjunto de
    `AUSENCIAS_GALPAO_DETALHES` que o calculo nao produz nesta rodada, mais
    `hidrantes (N_hidrantes/tipo/reserva)` quando o spec nao declarou
    hidrantes. Ausencia se declara na folha, nunca vira default silencioso.
    """
    hid_raw = (r or {}).get("hidrantes") if isinstance(r, dict) else None
    if isinstance(hid_raw, dict):
        hid = {"N_hidrantes": hid_raw.get("N_hidrantes"),
               "tipo": hid_raw.get("tipo"),
               "reserva_incendio_m3": hid_raw.get("reserva_incendio_m3")}
    else:
        hid = {"N_hidrantes": None, "tipo": None,
               "reserva_incendio_m3": None}
    inc = {"sistemas": {"hidrantes": hid}, "gates": {},
           "estrategia_abandono": None, "populacao_total": None,
           "altura_edificacao_m": None}
    ausentes = list(AUSENCIAS_GALPAO_DETALHES)
    if not isinstance(hid_raw, dict):
        ausentes = (["hidrantes (N_hidrantes/tipo/reserva_incendio_m3) "
                     "nao calculados: hidrantes ausente no spec"] + ausentes)
    return inc, {}, ausentes


def detalhes_hidrantes_rotas_svg(inc, estrutura, titulo=None, ausencias=None,
                                 nivel_unico=False):
    """PE-IN-02 Detalhes: corte da coluna de hidrantes DN65 (NBR 13714) com um
    hidrante por pavimento servido + quadro da escada/rotas + reserva.

    G138: `nivel_unico=True` desenha o galpao terreo (N hidrantes lado a
    lado no nivel unico, nunca N pavimentos inventados) e `ausencias`
    declara na folha os campos que o calculo do galpao nao produz. Com os
    defaults (None/False) o caminho do predio e byte-identico."""
    sist = inc.get("sistemas") or {}
    hid = sist.get("hidrantes") or {}
    gates = inc.get("gates") or {}
    n_decl = hid.get("N_hidrantes")
    n = int(n_decl or 0) or 1
    n_pav = len((estrutura or {}).get("pavimentos") or []) or n
    reserva = hid.get("reserva_incendio_m3")
    if titulo is None and nivel_unico:
        titulo = "DETALHES - HIDRANTES (GALPAO TERREO) E ROTAS DE FUGA"
    W, Hh = 940, max(480, 180 + n_pav * 44)
    if ausencias:
        Hh += 40 + len(list(ausencias)) * 20
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" '
         f'viewBox="0 0 {W} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         _t(W / 2, 34, titulo or "DETALHES - HIDRANTES E ROTAS DE FUGA", 19, weight="bold")]
    x = 220
    y0, y1 = 110, Hh - 130 - (40 + len(list(ausencias or [])) * 20 if ausencias else 0)
    passo = (y1 - y0) / max(n_pav, 1)
    s.append(_line(x, y0 - 20, x, y1 + 20, 4.0, VERMELHO))
    s.append(_t(x, y0 - 32, "COLUNA DN65 (NBR 13714)", 12, color=VERMELHO, weight="bold"))
    if nivel_unico:
        # Galpao terreo: N hidrantes no nivel unico, lado a lado (count-driven:
        # EXATAMENTE N simbolos == N_hidrantes do calculo, nunca N pavimentos).
        y = y1 - passo * 0.5
        largura = 200.0
        x_ini = x - 40.0
        if not n_decl:
            # D172: sem N calculado (None) ou N=0 nao ha simbolo a desenhar
            # - o `or 1` do predio desenhava HID-1 inventado ao lado da
            # caixa que diz "nao calculados".
            s.append(_t(x, y1 + 44, (
                "hidrantes nao calculados: nenhum simbolo"
                if n_decl is None else
                "0 hidrantes no calculo: nenhum simbolo"), 11, color=VERMELHO))
        else:
            for i in range(n):
                xi = x_ini + (largura * i / max(n - 1, 1) if n > 1 else 60.0)
                s.append(_sym_hidrante(xi, y))
                s.append(_t(xi, y + 22, "HID-%d (terreo)" % (i + 1), 10))
            s.append(_t(x, y1 + 44, "nivel unico (terreo): %d hidrante(s) "
                       "no mesmo nivel" % n, 11, color=VERMELHO))
    else:
        for i in range(n_pav):
            y = y1 - passo * (i + 0.5)
            s.append(_line(x, y, x + 90, y, 2.0, VERMELHO))
            s.append(_sym_hidrante(x + 110, y))
            s.append(_t(x + 130, y + 4, "hidrante N%d" % (i + 1), 10, "start"))
    qx, qy = 470, 110
    rotas = gates.get("rotas_verticais") or {}
    larg = gates.get("escada_largura") or {}
    linhas = [
        ("RESERVA DE INCENDIO: nao calculada"
         if nivel_unico and reserva is None else
         "RESERVA DE INCENDIO %.1f m3" % (reserva or 0)),
        "Rotas verticais: min %s / decl %s" % (
            rotas.get("n_minimo", "?"), rotas.get("n_declarado", "?")),
        "Largura escada exigida: %s m" % (larg.get("largura_exigida_m", "?"),),
        "Estrategia: %s" % (inc.get("estrategia_abandono", "?"),),
        "Populacao total: %d" % int(inc.get("populacao_total") or 0),
        "Altura: %s m" % (inc.get("altura_edificacao_m", "?"),)]
    s.append(f'<rect x="{qx}" y="{qy}" width="430" height="{40 + len(linhas) * 26}" '
             f'fill="white" stroke="#111" stroke-width="1"/>')
    s.append(_t(qx + 215, qy + 26, "QUADRO DE ROTAS", 13, weight="bold"))
    for i, ln in enumerate(linhas):
        s.append(_t(qx + 14, qy + 52 + i * 26, ln, 11, anchor="start"))
    if ausencias:
        ax, ay = 40, qy + 40 + len(linhas) * 26 + 20
        alt = 40 + len(list(ausencias)) * 20
        s.append(f'<rect x="{ax}" y="{ay}" width="860" height="{alt}" '
                 f'fill="white" stroke="{VERMELHO}" stroke-width="1.5"/>')
        s.append(_t(ax + 430, ay + 24, "DADOS NAO DECLARADOS PELO CALCULO "
                   "DO GALPAO (G138)", 12, weight="bold", color=VERMELHO))
        for i, campo in enumerate(list(ausencias)):
            s.append(_t(ax + 14, ay + 46 + i * 20,
                       "nao declarado: %s" % campo, 11, anchor="start"))
    s.append('</svg>')
    return "\n".join(s)


def gerar_detalhes_galpao(r, path, titulo=None):
    """Escreve os detalhes de hidrantes do GALPAO (PE-IN-02) em `path`.

    G138: adapta o resultado de `galpao_seguranca_incendio.rodar` (uma fonte
    so, sem recalcular hidrantes) e declara na folha os campos que o calculo
    nao produz. Devolve (path, ausentes)."""
    inc, estrutura, ausentes = adaptar_galpao_para_detalhes(r)
    with open(path, "w", encoding="utf-8") as f:
        f.write(detalhes_hidrantes_rotas_svg(
            inc, estrutura, titulo, ausencias=ausentes, nivel_unico=True))
    return path, ausentes


def gerar_ppci_pavimento(inc, estrutura, path, pavimento=None):
    """Escreve o PPCI do pavimento-tipo (PE-IN-01) em `path`."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(planta_pavimento_edificio_svg(inc, estrutura, pavimento))
    return path


def gerar_detalhes_hidrantes(inc, estrutura, path, titulo=None,
                             ausencias=None, nivel_unico=False):
    """Escreve os detalhes de hidrantes/rotas (PE-IN-02) em `path`."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(detalhes_hidrantes_rotas_svg(
            inc, estrutura, titulo, ausencias=ausencias,
            nivel_unico=nivel_unico))
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
