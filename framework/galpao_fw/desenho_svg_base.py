# ============================================================================
# desenho_svg_base.py - PRIMITIVAS SVG COMPARTILHADAS dos desenhos eletricos
# (escape XML, texto, linha e simbologia ABNT NBR 5444/IEC). Extraido de
# desenho_eletrico.py para que a camada grafica RESIDENCIAL reuse as MESMAS
# primitivas em vez de duplica-las - em especial o `esc()`, cujo esquecimento
# gerou SVG XML-malformado ("R <= 10 ohm" com '<' cru). Uma copia = risco de o
# bug voltar por um dos lados.
#
# Este modulo NAO conhece nenhum shape de resultado: recebe numeros e strings.
# Quem monta o desenho e' desenho_eletrico (industrial) ou
# desenho_eletrico_residencial (residencial).
# ============================================================================
"""Primitivas SVG puras (escape XML + simbologia eletrica) sem shape de calculo."""

from __future__ import annotations

PALETA_CIRCUITO = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c",
                   "#0891b2", "#ca8a04", "#4b5563", "#db2777", "#65a30d"]


def esc(txt):
    """Escapa &<> p/ o texto ser XML-valido (SVG e' XML). Sem isso, um '<' cru
    (ex.: 'R <= 10 ohm') quebra o SVG inteiro em renderers estritos (QtSvg/
    TechDraw DrawViewSymbol)."""
    return (str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def texto(x, y, txt, size=13, anchor="middle", weight="normal", color="#111"):
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-family="Arial" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}" fill="{color}">{esc(txt)}</text>')


def linha(x1, y1, x2, y2, w=1.5, color="#111"):
    return (f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
            f'stroke="{color}" stroke-width="{w}"/>')


def sym_trafo(cx, cy, r=18):
    """Transformador: dois circulos sobrepostos (Dy)."""
    return (f'<circle cx="{cx:.0f}" cy="{cy - r * 0.5:.0f}" r="{r}" fill="none" '
            f'stroke="#111" stroke-width="1.6"/>'
            f'<circle cx="{cx:.0f}" cy="{cy + r * 0.5:.0f}" r="{r}" fill="none" '
            f'stroke="#111" stroke-width="1.6"/>')


def sym_disjuntor(cx, cy):
    """Disjuntor: quadrado com um X (chave)."""
    return (f'<rect x="{cx - 9:.0f}" y="{cy - 9:.0f}" width="18" height="18" '
            f'fill="white" stroke="#111" stroke-width="1.4"/>'
            + linha(cx - 6, cy - 6, cx + 6, cy + 6, 1.2)
            + linha(cx - 6, cy + 6, cx + 6, cy - 6, 1.2))


def sym_dps(cx, cy):
    """DPS: retangulo com seta (limitador de tensao)."""
    return (f'<rect x="{cx - 8:.0f}" y="{cy - 11:.0f}" width="16" height="22" '
            f'fill="white" stroke="#111" stroke-width="1.3"/>'
            + linha(cx, cy - 6, cx, cy + 6, 1.2)
            + f'<path d="M{cx - 4:.0f} {cy:.0f} L{cx + 4:.0f} {cy:.0f} '
              f'L{cx:.0f} {cy + 6:.0f} Z" fill="#111"/>')


def sym_motor(cx, cy, r=15):
    """Motor: circulo com M."""
    return (f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="none" '
            f'stroke="#111" stroke-width="1.5"/>' + texto(cx, cy + 5, "M", 15, weight="bold"))


def sym_lampada(cx, cy, r=13):
    """Iluminacao: circulo com X."""
    return (f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="none" '
            f'stroke="#111" stroke-width="1.4"/>'
            + linha(cx - 9, cy - 9, cx + 9, cy + 9, 1.1)
            + linha(cx - 9, cy + 9, cx + 9, cy - 9, 1.1))


def sym_tomada(cx, cy, r=13):
    """Tomada: semicirculo."""
    return (f'<path d="M{cx - r:.0f} {cy:.0f} A{r} {r} 0 0 1 {cx + r:.0f} {cy:.0f}" '
            f'fill="none" stroke="#111" stroke-width="1.5"/>'
            + linha(cx - r, cy, cx + r, cy, 1.5))


def sym_capacitor(cx, cy):
    """Banco de capacitores: duas placas paralelas."""
    return (linha(cx - 12, cy - 4, cx + 12, cy - 4, 2.0)
            + linha(cx - 12, cy + 4, cx + 12, cy + 4, 2.0))


def sym_terra(cx, cy):
    """Aterramento: 3 tracos horizontais decrescentes."""
    return (linha(cx - 14, cy, cx + 14, cy, 1.8)
            + linha(cx - 9, cy + 5, cx + 9, cy + 5, 1.6)
            + linha(cx - 4, cy + 10, cx + 4, cy + 10, 1.4))


def sym_lampada_cor(cx, cy, cor, r=9):
    """Ponto de luz colorido pelo circuito."""
    return (f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="none" '
            f'stroke="{cor}" stroke-width="1.6"/>'
            + linha(cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7, 1.1, cor)
            + linha(cx - r * 0.7, cy + r * 0.7, cx + r * 0.7, cy - r * 0.7, 1.1, cor))


def sym_tomada_cor(cx, cy, cor, r=8):
    """Tomada colorida pelo circuito."""
    return (f'<path d="M{cx - r:.0f} {cy:.0f} A{r} {r} 0 0 1 {cx + r:.0f} {cy:.0f}" '
            f'fill="none" stroke="{cor}" stroke-width="1.8"/>'
            + linha(cx - r, cy, cx + r, cy, 1.8, cor))


def abre_svg(largura, altura, titulo=None, titulo_size=20):
    """Cabecalho do SVG + fundo branco (+ titulo centrado, opcional)."""
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" '
              f'height="{altura}" viewBox="0 0 {largura} {altura}" font-family="Arial">',
              f'<rect x="0" y="0" width="{largura}" height="{altura}" fill="white"/>']
    if titulo is not None:
        partes.append(texto(largura / 2, 34, titulo, titulo_size, weight="bold"))
    return partes
