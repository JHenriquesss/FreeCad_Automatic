# ============================================================================
# desenho_hidraulica.py - O QUE ESTE SCRIPT DESENHA
# Esquema da REDE HIDRAULICA PREDIAL do galpao (planta esquematica) em SVG puro-Python
# (autocontido, sem FreeCAD), sobre galpao_hidraulica.rodar(). E' o desenho-assinatura
# do executivo de hidraulica: mostra, sobre o contorno do galpao, as 3 redes com os
# DIAMETROS ROTULADOS (calculados pela norma):
#   - PLUVIAL: condutores verticais nos cantos + calha no beiral (NBR 10844);
#   - ESGOTO: coletor no eixo + coluna de ventilacao (NBR 8160);
#   - AGUA FRIA: barrilete no forro (NBR 5626), com a pressao residual verificada.
# Posicoes esquematicas (o projetista ajusta ao leiaute real). Cores por rede.
# ============================================================================
"""Esquema da rede hidraulica predial (planta + diametros rotulados) em SVG puro-Python,
a partir de galpao_hidraulica.rodar()."""

from __future__ import annotations

COR = {"pluvial": "#16a34a", "esgoto": "#92400e", "agua": "#2563eb"}


from desenho_svg_base import (  # noqa: E402
    esc as _esc,
    linha as _line,
    texto as _t,
)


def esquema_hidraulica_svg(r):
    """Planta esquematica da rede hidraulica a partir de r=rodar(). String SVG."""
    geo = r["geometria"]
    C = float(geo["L"]); Lg = float(geo["W"])           # comprimento x largura (m)
    redes = r["redes"]

    W, Hh = 1000, 640
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" '
         f'viewBox="0 0 {W} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         _t(W / 2, 30, "ESQUEMA DA REDE HIDRAULICA PREDIAL", 19, weight="bold")]

    mx, my, aw, ah = 60, 60, 620, 480
    esc = min(aw / C, ah / Lg)
    gw, gh = C * esc, Lg * esc
    x0 = mx + (aw - gw) / 2.0
    y0 = my + (ah - gh) / 2.0
    s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{gw:.1f}" height="{gh:.1f}" '
             f'fill="#fafafa" stroke="#111" stroke-width="2"/>')
    s.append(_t(x0 + gw / 2, y0 - 8, "%.0f m" % C, 12))
    s.append(_t(x0 - 30, y0 + gh / 2, "%.0f m" % Lg, 12))

    # PLUVIAL: calha no beiral (topo) + condutores nos cantos
    if redes["pluvial"].get("calha_mm"):
        s.append(_line(x0, y0, x0 + gw, y0, 3.0, COR["pluvial"]))
        s.append(_t(x0 + gw / 2, y0 - 22, "Calha DN%.0f" % redes["pluvial"]["calha_mm"],
                    11, color=COR["pluvial"]))
    for (fx, fy) in ((0.03, 0.06), (0.97, 0.06), (0.03, 0.94), (0.97, 0.94)):
        cx, cy = x0 + gw * fx, y0 + gh * fy
        s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="none" '
                 f'stroke="{COR["pluvial"]}" stroke-width="2"/>')
    s.append(_t(x0 + gw * 0.03 + 12, y0 + gh * 0.06 - 8,
                "Cond. DN%.0f" % redes["pluvial"]["D_mm"], 10, anchor="start",
                color=COR["pluvial"]))

    # ESGOTO: coletor no eixo (horizontal) + coluna de ventilacao (ponto central)
    yc = y0 + gh / 2
    s.append(_line(x0, yc, x0 + gw, yc, 3.0, COR["esgoto"], dash="10 5"))
    s.append(_t(x0 + gw * 0.25, yc + 16, "Coletor esgoto DN%.0f" % redes["esgoto"]["D_mm"],
                11, color=COR["esgoto"]))
    if redes["esgoto"].get("ventilacao_coluna_mm"):
        vx, vy = x0 + gw * 0.5, yc
        s.append(f'<circle cx="{vx:.1f}" cy="{vy:.1f}" r="7" fill="white" '
                 f'stroke="{COR["esgoto"]}" stroke-width="2"/>')
        s.append(_t(vx, vy - 12, "Vent. DN%.0f" % redes["esgoto"]["ventilacao_coluna_mm"],
                    10, color=COR["esgoto"]))

    # AGUA FRIA: barrilete (linha a 1/4 da largura)
    ya = y0 + gh * 0.25
    s.append(_line(x0, ya, x0 + gw, ya, 3.0, COR["agua"]))
    s.append(_t(x0 + gw * 0.7, ya - 8, "Barrilete agua DN%.0f" % redes["agua_fria"]["D_mm"],
                11, color=COR["agua"]))

    # --- LEGENDA + QUADRO de diametros ---
    lx, ly = 715, 70
    itens = [(COR["pluvial"], "Pluvial (NBR 10844)"),
             (COR["esgoto"], "Esgoto (NBR 8160)"),
             (COR["agua"], "Agua fria (NBR 5626)")]
    s.append(f'<rect x="{lx}" y="{ly}" width="245" height="{34 + len(itens) * 24}" '
             f'fill="white" stroke="#111" stroke-width="1"/>')
    s.append(_t(lx + 122, ly + 22, "REDES", 14, weight="bold"))
    for i, (cor, txt) in enumerate(itens):
        yy = ly + 44 + i * 24
        s.append(_line(lx + 16, yy, lx + 40, yy, 4.0, cor))
        s.append(_t(lx + 48, yy + 4, txt, 11, anchor="start"))

    qx, qy = 715, 220
    linhas = ["Pluvial: cond. DN%.0f" % redes["pluvial"]["D_mm"]]
    if redes["pluvial"].get("calha_mm"):
        linhas.append("  calha DN%.0f" % redes["pluvial"]["calha_mm"])
    linhas.append("Esgoto: coletor DN%.0f" % redes["esgoto"]["D_mm"])
    if redes["esgoto"].get("ventilacao_coluna_mm"):
        linhas.append("  vent. ramal DN%.0f/col DN%.0f" % (
            redes["esgoto"].get("ventilacao_ramal_mm", 0),
            redes["esgoto"]["ventilacao_coluna_mm"]))
    ag = redes["agua_fria"]
    linhas.append("Agua: barrilete DN%.0f" % ag["D_mm"])
    if ag.get("metodo"):
        linhas.append("  metodo: %s" % ag["metodo"])
    if ag.get("pressao"):
        vp = ag["pressao"]
        cav = " p_alim assumido" if vp.get("p_alim_default") else ""
        linhas.append("  p.residual %.0f kPa (%s%s)" % (
            vp["p_residual_kPa"], "OK" if vp["OK"] else "INSUF", cav))
    box_h = 34 + len(linhas) * 18
    s.append(f'<rect x="{qx}" y="{qy}" width="245" height="{box_h}" fill="white" '
             f'stroke="#111" stroke-width="1"/>')
    s.append(_t(qx + 122, qy + 20, "DIAMETROS", 13, weight="bold"))
    for i, ln in enumerate(linhas):
        s.append(_t(qx + 12, qy + 40 + i * 18, ln, 10, anchor="start"))

    s.append('</svg>')
    return "\n".join(s)      # NAO aplicar virgula decimal no SVG: corromperia coordenadas


def gerar_esquema(r, path):
    svg = esquema_hidraulica_svg(r)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


# ---------------------------------------------------------------------------
# PRANCHAS DO EDIFICIO (G56) - uma folha por rede, com corte vertical
# ---------------------------------------------------------------------------
# O emissor do galpao junta as 3 redes numa folha so (um pavimento, um
# retangulo). O predio tem N pavimentos empilhados e prumadas verticais: cada
# rede ganha a sua folha (PE-HI-01/02/03) com a planta do pavimento-tipo + o
# CORTE vertical da prumada que o galpao nunca teve. A saida e' PARAMETRO
# (rede), nao um desenho_hidraulica_edificio.py paralelo.

_REDES_EDIFICIO = ("agua", "esgoto", "pluvial")


def _edificio_C_L(estrutura):
    pav = (estrutura or {}).get("pavimento") or {}
    try:
        return float(sum(pav["vaos_x"])), float(sum(pav["vaos_y"]))
    except Exception:
        return 14.0, 9.0


def _dn_txt(valor):
    try:
        return "DN%.0f" % float(valor)
    except (TypeError, ValueError):
        return "DN?"


def planta_rede_edificio_svg(hid, estrutura, rede="agua", pavimento=None):
    """Planta do pavimento-tipo + corte vertical da prumada, por rede.

    rede: 'agua' (coluna DN do calculo), 'esgoto' (tubo de queda + ventilacao)
    ou 'pluvial' (condutor + descidas). DN rotulado == DN calculado."""
    if rede not in _REDES_EDIFICIO:
        raise ValueError("rede deve ser uma de %s (recebido %r)"
                         % (list(_REDES_EDIFICIO), rede))
    C, L = _edificio_C_L(estrutura)
    n = int(hid.get("pavimentos_servidos") or 0) or 1
    if rede == "agua":
        dn = ((hid.get("coluna") or {}).get("dn") or {}).get("DN_mm")
        titulo = "AGUA FRIA - PLANTA E CORTE DA PRUMADA"
        cor = COR["agua"]
        extra = "RESERVACAO %.0f L" % ((hid.get("reservacao") or {}).get("total_L") or 0)
    elif rede == "esgoto":
        esg = hid.get("esgoto") or {}
        dn = ((esg.get("tubo_de_queda") or {}).get("DN_mm")
              or (esg.get("gate_queda") or {}).get("DN_mm"))
        titulo = "ESGOTO/VENTILACAO - PLANTA E CORTE DA PRUMADA"
        cor = COR["esgoto"]
        extra = "VENTILACAO %s" % _dn_txt(esg.get("coluna_ventilacao_DN_mm"))
    else:
        plv = hid.get("pluvial") or {}
        dn = ((plv.get("condutor") or {}).get("DN_mm")
              or (plv.get("gate") or {}).get("DN_mm"))
        titulo = "PLUVIAL - PLANTA E CORTE DAS DESCIDAS"
        cor = COR["pluvial"]
        extra = "%d DESCIDAS" % int(plv.get("n_descidas") or 1)
    rot = pavimento or "PAVIMENTO-TIPO"
    Wc, Hh = 1080, 660
    ax0, ay0, aw, ah = 50, 90, 560, 420
    sc = min(aw / C, ah / L)

    def px(xm):
        return ax0 + xm * sc

    def py(ym):
        return ay0 + (L - ym) * sc

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wc}" height="{Hh}" '
         f'viewBox="0 0 {Wc} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{Wc}" height="{Hh}" fill="white"/>',
         _t(Wc / 2, 34, titulo, 18, weight="bold"),
         _t(Wc / 2, 56, "%s - %s %s" % (rot.upper(), _dn_txt(dn), extra), 12, color="#555"),
         f'<rect x="{px(0):.0f}" y="{py(L):.0f}" width="{C * sc:.0f}" height="{L * sc:.0f}" '
         f'fill="#fafafa" stroke="#111" stroke-width="2"/>',
         _t(px(C / 2), py(0) + 26, "%.1f m" % C, 12)]
    # shaft + ramal horizontal do pavimento-tipo
    sx, sy = px(1.0), py(L - 1.0)
    s.append(f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="7" fill="none" '
             f'stroke="{cor}" stroke-width="2"/>')
    s.append(_line(sx, sy, px(min(C, 5.0)), sy, 3.0, cor))
    s.append(_t(px(min(C, 5.0)) + 8, sy - 8, "ramal %s" % _dn_txt(dn), 11, "start", color=cor))
    # CORTE vertical: a prumada atravessando os N pavimentos (fura a laje)
    cx0, cw = 700, 130
    y0, y1 = 110, 560
    passo = (y1 - y0) / n
    s.append(_t(cx0 + cw / 2, y0 - 16, "CORTE VERTICAL", 13, weight="bold"))
    for i in range(n):
        y = y1 - passo * (i + 0.5)
        s.append(_line(cx0, y, cx0 + cw, y, 1.0, "#9ca3af", dash="6 4"))
        s.append(_t(cx0 + cw + 10, y + 4, "N%d" % (i + 1), 10, "start", color="#555"))
    s.append(_line(cx0 + cw / 2, y0, cx0 + cw / 2, y1, 3.5, cor))
    s.append(_t(cx0 + cw / 2, y1 + 24, "prumada %s" % _dn_txt(dn), 11, color=cor))
    qx, qy = 700, 600
    s.append(_t(qx, qy, extra, 11, "start", color="#555"))
    s.append('</svg>')
    return "\n".join(s)


def gerar_rede_edificio(hid, estrutura, path, rede="agua", pavimento=None):
    """Escreve a folha da rede (PE-HI-01/02/03) em `path`."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(planta_rede_edificio_svg(hid, estrutura, rede, pavimento))
    return path


def _selftest():
    import galpao_hidraulica as gh
    r = gh.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                  "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2},
                                 "aparelhos_esgoto": {"bacia": 2, "lavatorio": 2}}})
    svg = esquema_hidraulica_svg(r)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    for termo in ("REDE HIDRAULICA", "Pluvial", "Esgoto", "Agua", "DIAMETROS",
                  "Coletor esgoto", "Barrilete"):
        assert termo in svg, termo
    assert "Vent. DN" in svg and "Calha DN" in svg
    print("desenho_hidraulica self-test PASSED")


if __name__ == "__main__":
    _selftest()
