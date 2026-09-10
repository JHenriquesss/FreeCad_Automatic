# ============================================================================
# desenho_terraplenagem.py - O QUE ESTE SCRIPT DESENHA (G79)
# Duas folhas prometidas por pacote_legal._PRANCHAS["terraplenagem"] e nunca
# emitidas (o modulo de calculo nao tinha uma unica funcao *_svg):
#   - PE-TP-01 mapa_corte_aterro_svg: mapa de corte/aterro por celula da malha
#     (com o greide de equilibrio cotado) + quadro-resumo com os volumes e o
#     empolamento DECLARADO, nunca assumido.
#   - PE-TP-02 planta_drenagem_svg: planta de drenagem (canaleta retangular com
#     Q, largura, declividade, n de Manning) + secao transversal com a lamina
#     d'agua + quadro com C, IDF e area.
# Ambas leem o que terraplenagem.py ja calcula (volumes_corte_aterro,
# greide_equilibrio, movimento_terra, dimensiona_drenagem). As folhas sao
# COUNT-DRIVEN: celulas desenhadas == celulas da malha; canaletas desenhadas
# == canaletas dimensionadas (a armadilha medida: incendio desenhou
# cols*rows != N uma vez). Cada celula/canaleta carrega data-celula /
# data-canaleta para a contagem ser por PARSE, nunca substring (a escada).
# ============================================================================
"""Folhas PE-TP-01 (corte/aterro) e PE-TP-02 (drenagem) em SVG puro-Python,
a partir de terraplenagem.py. STATELESS."""

from __future__ import annotations

from desenho_svg_base import esc as _esc  # noqa: E402
from desenho_svg_base import linha as _line  # noqa: E402
from desenho_svg_base import texto as _t  # noqa: E402

COR_CORTE = "#e8a37a"
COR_ATERRO = "#9ec2e8"
COR_ZERO = "#d9d9d9"


def _quadro(x, y, w, titulo, linhas):
    """Caixa de quadro-resumo; linhas = [(chave, valor)]."""
    out = [f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" '
           f'height="{28 * len(linhas) + 44:.0f}" fill="#fafafa" '
           f'stroke="#111" stroke-width="1.2"/>',
           _t(x + w / 2, y + 26, titulo, 14, weight="bold")]
    for i, (k, v) in enumerate(linhas):
        yy = y + 52 + i * 28
        out.append(_t(x + 12, yy, k, 12, anchor="start", color="#333"))
        out.append(_t(x + w - 12, yy, v, 12, anchor="end", weight="bold"))
    return out


def mapa_corte_aterro_svg(dados):
    """PE-TP-01. dados: {grid_terreno, cota_plataforma, area_celula_m2,
    empolamento?, volumes?, greide?, movimento?}. volumes/greide/movimento,
    quando ausentes, sao calculados pelo proprio terraplenagem.py (mesma
    fonte, sem numero inventado). empolamento ausente sai como
    "... nao declarado" - nunca 1.0 silencioso."""
    import terraplenagem as tp

    grid = dados["grid_terreno"]
    cota = float(dados["cota_plataforma"])
    area = float(dados["area_celula_m2"])
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    emp = dados.get("empolamento")
    emp_txt = ("%.2f" % emp) if emp is not None else "... nao declarado"

    volumes = dados.get("volumes") or tp.volumes_corte_aterro(grid, cota, area)
    greide = dados.get("greide")
    if greide is None and emp is not None:
        greide = tp.greide_equilibrio(grid, area, empolamento=emp)
    movimento = dados.get("movimento")
    if movimento is None and emp is not None:
        movimento = tp.movimento_terra(volumes["corte_m3"], volumes["aterro_m3"], emp)

    W, H = 1120, 780
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Arial">',
           f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
           _t(W / 2, 34, "PE-TP-01 - TERRAPLENAGEM (CORTE/ATERRO POR GRADE)", 20,
              weight="bold"),
           _t(W / 2, 58, "Plataforma %.2f m - greide de equilibrio cotado no quadro"
              % cota, 13, color="#333")]

    # mapa da malha (count-driven: um rect por no da grade)
    ax0, ay0, aw, ah = 80, 100, 600, 480
    cw, ch = aw / max(cols, 1), ah / max(rows, 1)
    for i, linha in enumerate(grid):
        for j, z in enumerate(linha):
            dh = float(z) - cota
            fill = COR_CORTE if dh > 0 else (COR_ATERRO if dh < 0 else COR_ZERO)
            x, y = ax0 + j * cw, ay0 + i * ch
            out.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" '
                f'fill="{fill}" stroke="#111" stroke-width="1.2" '
                f'data-celula="{i}-{j}" data-dh="{dh:+.2f}"/>')
            out.append(_t(x + cw / 2, y + ch / 2 - 4, "%.2f" % z, 11, weight="bold"))
            out.append(_t(x + cw / 2, y + ch / 2 + 14, "%+.2f" % dh, 11,
                          color="#7a1f1f" if dh > 0 else "#1f3a7a"))
    out.append(_t(ax0 + aw / 2, ay0 + ah + 28,
                  "Malha %d x %d = %d celulas - corte (terreno acima do greide) "
                  "x aterro (abaixo)" % (rows, cols, rows * cols), 12,
                  color="#333"))
    # legenda
    ly = ay0 + ah + 52
    out.append(f'<rect x="{ax0:.0f}" y="{ly:.0f}" width="16" height="16" '
               f'fill="{COR_CORTE}" stroke="#111"/>')
    out.append(_t(ax0 + 24, ly + 13, "corte", 12, anchor="start"))
    out.append(f'<rect x="{ax0 + 110:.0f}" y="{ly:.0f}" width="16" height="16" '
               f'fill="{COR_ATERRO}" stroke="#111"/>')
    out.append(_t(ax0 + 134, ly + 13, "aterro", 12, anchor="start"))
    out.append(f'<rect x="{ax0 + 220:.0f}" y="{ly:.0f}" width="16" height="16" '
               f'fill="{COR_ZERO}" stroke="#111"/>')
    out.append(_t(ax0 + 244, ly + 13, "no greide", 12, anchor="start"))

    # quadro-resumo (lado direito)
    greide_txt = ("%.3f m" % greide["cota_equilibrio"]) if greide else "... nao declarado"
    linhas = [
        ("Cota plataforma", "%.2f m" % cota),
        ("Greide equilibrio", greide_txt),
        ("Corte", "%.1f m3" % volumes["corte_m3"]),
        ("Aterro", "%.1f m3" % volumes["aterro_m3"]),
        ("Celulas", "%d" % volumes["n_celulas"]),
        ("Empolamento", emp_txt),
    ]
    if movimento is not None:
        linhas.append(("Saldo", "%.1f m3 - %s" % (movimento["saldo_m3"],
                                                 movimento["acao"])))
    else:
        linhas.append(("Saldo", "... nao declarado (empolamento ausente)"))
    out.extend(_quadro(730, 110, 340, "QUADRO-RESUMO", linhas))
    qy = 110 + 28 * len(linhas) + 44 + 24
    out.append(_t(730, qy, "Metodo da grade: V = soma(dh . area).", 11,
                  anchor="start", color="#666"))
    out.append(_t(730, qy + 22, "Corte util = corte / empolamento.", 11,
                  anchor="start", color="#666"))
    out.append(_t(730, qy + 44, "Empolamento e propriedade do solo", 11,
                  anchor="start", color="#666"))
    out.append(_t(730, qy + 66, "(A CONFIRMAR ensaio) - nunca default.", 11,
                  anchor="start", color="#666"))
    out.append("</svg>")
    return "\n".join(out)


def planta_drenagem_svg(dados):
    """PE-TP-02. dados: {caso, resultado?, trechos?}. caso: {C, i_mm_h,
    area_ha, largura_canaleta_m, declividade, n_manning?, altura_max_m?}.
    resultado, quando ausente, vem de dimensiona_drenagem (mesma fonte).
    trechos: lista opcional de {nome, comprimento_m} - cada um vira UMA
    canaleta desenhada (count-driven: desenhadas == dimensionadas); sem ela,
    uma canaleta (a dimensionada)."""
    import terraplenagem as tp

    caso = dict(dados["caso"])
    res = dados.get("resultado") or tp.dimensiona_drenagem(caso)
    can = res["canaleta"]
    trechos = dados.get("trechos") or [{"nome": "C1"}]
    n_man = float(caso.get("n_manning", 0.015))
    n_txt = ("%.3f" % n_man) if "n_manning" in caso else \
        "%.3f (default, nao declarado)" % n_man
    alt_max = float(caso.get("altura_max_m", 1.0))
    b = float(can.get("largura_m", caso["largura_canaleta_m"]))
    decl = float(caso["declividade"])

    W, H = 1120, 780
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Arial">',
           f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>',
           _t(W / 2, 34, "PE-TP-02 - DRENAGEM DO LOTE (RACIONAL + MANNING)", 20,
              weight="bold")]
    if not can.get("OK"):
        out.append(_t(W / 2, 62, "CANALETA INSUFICIENTE NA ALTURA MAX - alargar ou "
                      "aumentar declividade", 14, weight="bold", color="#b00"))
    else:
        out.append(_t(W / 2, 62, "Q = C.i.A/360 (DNIT) - canaleta retangular por Manning",
                      13, color="#333"))

    # planta: lote com uma linha de canaleta por trecho (count-driven)
    ax0, ay0, aw, ah = 80, 110, 560, 380
    out.append(f'<rect x="{ax0:.0f}" y="{ay0:.0f}" width="{aw:.0f}" height="{ah:.0f}" '
               f'fill="#f2f7f2" stroke="#111" stroke-width="2"/>')
    out.append(_t(ax0 + aw / 2, ay0 - 10,
                  "planta do lote - canaletas no perimetro", 12,
                  color="#333"))
    for k, tr in enumerate(trechos):
        yy = ay0 + 60 + k * (min(70.0, (ah - 120) / max(len(trechos), 1)))
        nome = tr.get("nome", "C%d" % (k + 1))
        out.append(f'<line x1="{ax0 + 30:.0f}" y1="{yy:.0f}" x2="{ax0 + aw - 30:.0f}" '
                   f'y2="{yy:.0f}" stroke="#0b6e4f" stroke-width="5" '
                   f'data-canaleta="{_esc(nome)}"/>')
        out.append(_t(ax0 + 34, yy - 10, "%s - b=%.2f m S=%.4f n=%.3f" % (
            _esc(nome), b, decl, n_man), 11, anchor="start", color="#0b6e4f"))
    out.append(_t(ax0 + aw / 2, ay0 + ah + 26,
                  "%d canaleta(s) dimensionada(s) - Q=%.4f m3/s" % (
                      len(trechos), res["vazao_m3s"]), 12, color="#333"))

    # secao transversal da canaleta (b x altura_max, lamina y cheia d'agua)
    sx0, sy0, sw, sh = 110, 560, 300, 130
    out.append(_t(sx0 + sw / 2, sy0 - 12, "secao da canaleta (b=%.2f m)" % b, 12,
                  weight="bold"))
    out.append(f'<rect x="{sx0:.0f}" y="{sy0:.0f}" width="{sw:.0f}" height="{sh:.0f}" '
               f'fill="white" stroke="#111" stroke-width="2"/>')
    y_m = min(float(can.get("y_m", 0.0)), alt_max)
    hw = sh * (y_m / alt_max) if alt_max > 0 else 0.0
    out.append(f'<rect x="{sx0:.0f}" y="{sy0 + sh - hw:.0f}" width="{sw:.0f}" '
               f'height="{hw:.0f}" fill="#7fb8e8" data-canaleta="secao"/>')
    out.append(_t(sx0 + sw + 12, sy0 + sh - hw, "y=%.3f m" % y_m, 12, anchor="start"))
    out.append(_t(sx0 + sw + 12, sy0 + sh, "borda=%.3f m" % float(
        can.get("borda_livre_m", alt_max - y_m)), 12, anchor="start"))
    out.append(_line(sx0, sy0 + sh + 18, sx0 + sw, sy0 + sh + 18, 1.2))
    out.append(_t(sx0 + sw / 2, sy0 + sh + 36, "b = %.2f m" % b, 12))

    # quadro-resumo
    linhas = [
        ("C (escoamento)", "%.3f (A CONFIRMAR)" % float(caso["C"])),
        ("i (IDF)", "%.1f mm/h (A CONFIRMAR)" % float(caso["i_mm_h"])),
        ("A contribuicao", "%.3f ha" % float(caso["area_ha"])),
        ("Q racional", "%.4f m3/s" % res["vazao_m3s"]),
        ("Largura b", "%.2f m" % b),
        ("Declividade S", "%.4f" % decl),
        ("n Manning", n_txt),
        ("Lamina y", "%.3f m" % float(can.get("y_m", 0.0))),
        ("Veredito", "OK" if can.get("OK") else "REPROVA"),
    ]
    out.extend(_quadro(700, 110, 370, "QUADRO DE DRENAGEM", linhas))
    qy = 110 + 28 * len(linhas) + 44 + 24
    out.append(_t(700, qy, "C e IDF sao dados de sitio (A CONFIRMAR).", 11,
                  anchor="start", color="#666"))
    out.append(_t(700, qy + 22, "n=0,015 concreto so quando declarado.", 11,
                  anchor="start", color="#666"))
    out.append("</svg>")
    return "\n".join(out)


def gerar_mapa_corte_aterro(dados, path):
    """Grava o SVG da PE-TP-01 em `path`."""
    svg = mapa_corte_aterro_svg(dados)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


def gerar_planta_drenagem(dados, path):
    """Grava o SVG da PE-TP-02 em `path`."""
    svg = planta_drenagem_svg(dados)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


def _selftest():
    import xml.etree.ElementTree as ET

    import terraplenagem as tp

    grid = [[102.3, 101.8, 101.2], [101.5, 101.0, 100.4], [100.6, 100.1, 99.5]]
    vols = tp.volumes_corte_aterro(grid, 101.0, 400.0)
    greide = tp.greide_equilibrio(grid, 400.0, empolamento=1.25)
    mov = tp.movimento_terra(vols["corte_m3"], vols["aterro_m3"], 1.25)
    svg = mapa_corte_aterro_svg({"grid_terreno": grid, "cota_plataforma": 101.0,
                                 "area_celula_m2": 400.0, "empolamento": 1.25,
                                 "volumes": vols, "greide": greide,
                                 "movimento": mov})
    ET.fromstring(svg)
    assert "PE-TP-01" in svg and "1.25" in svg

    caso = {"C": 0.75, "i_mm_h": 130.0, "area_ha": 1.2,
            "largura_canaleta_m": 0.4, "declividade": 0.008}
    svg2 = planta_drenagem_svg({"caso": caso,
                                "resultado": tp.dimensiona_drenagem(caso)})
    ET.fromstring(svg2)
    assert "PE-TP-02" in svg2
    return True


if __name__ == "__main__":
    _selftest()
    print("selftest OK")
