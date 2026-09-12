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

import desenho_svg_base as dsb

import math

try:
    from edicao_nbr6118_g123 import (
        edicao_de_resultado as _edicao_de_r,
        sufixo_folha_edicao as _sufixo_ed,
    )
except ImportError:  # uso isolado fora do pacote
    _edicao_de_r = None
    _sufixo_ed = None


def _carimbo_edicao(r):
    """Sufixo de edicao da NBR 6118 para o titulo da folha (G123, fonte unica).

    Sem o parametro no resultado, o comportamento e o de hoje (2014) e a
    folha diz qual e (chave DESLIGADA, sem default silencioso).
    """
    try:
        ed = _edicao_de_r(r) if _edicao_de_r is not None else None
    except ValueError:
        raise
    if _sufixo_ed is not None:
        return _sufixo_ed(ed)
    return " (NBR 6118:2014)" if not ed else (" (NBR 6118:%s)" % ed)


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
    """Escape XML - delega para a primitiva compartilhada (uma so implementacao:
    foi a copia solta de esc() que deixou passar o SVG XML-malformado do S41)."""
    return dsb.esc(t)


#: G77: geometria da folha de armacao. A folha nao tem altura fixa - ela e'
#: calculada a partir da MAIOR secao, porque a cota de largura de cada secao e'
#: desenhada 16 px abaixo dela.
TOPO_SECAO = 60.0      # primeira linha da secao mais alta (abaixo do titulo)
FOLGA_COTA = 34.0      # cota (y0+h+16) + descida do texto + margem inferior
ALTURA_NOTA = 24.0     # linha da NOTA C55-C90, quando exigida


def _exige_gancho_135(r):
    """NBR 6118 18.4.3 NOTA: estribo do pilar com gancho a 135 em C55-C90."""
    try:
        return (bool((r.get("pilar") or {}).get("gancho_135_exigido"))
                or float((r.get("spec") or {}).get("fck_MPa", 0.0)) > 50.0)
    except (TypeError, ValueError):
        return False


def prancha_armacao_svg(r):
    """Monta a prancha de armacao (SVG) do galpao de concreto a partir do resultado
    de galpao_concreto.rodar(). Uma linha com as 3 secoes: pilar, viga, sapata."""
    esc = 3.5                                           # px por cm (escala ~1:29)
    pil = r["pilar"]; vg = r["viga"]; sp = r["spec"]
    W = 900
    # G123: a folha carimba a edicao de calculo (fonte unica; sem o parametro,
    # o comportamento e o de hoje - 2014 - e a folha diz qual e).
    _suf_ed = _carimbo_edicao(r)
    # G77: a folha NAO pode ter altura fixa - a secao cresce com a peca. Com o
    # antigo Hn = 380 e um pilar de 90 cm, a cota de largura caia em y = 383,5:
    # emitida, contada pelas guardas de atributo, e invisivel na folha entregue.
    # A guarda que existia (`test_tudo_cabe_no_canvas`, da regressao da sapata)
    # media so o X, por regex sobre a fonte do SVG: o Y nunca foi conferido.
    # A medida vem ANTES do cabecalho - remendar cabecalho depois foi o G76.
    _gancho = _exige_gancho_135(r)
    h_sapata = 0.0
    if r["sapata"]["aprovado"]:
        _B, _Ls = r["sapata"]["aprovado"][0], r["sapata"]["aprovado"][1]
        h_sapata = _Ls * 100.0 * (150.0 / (max(_B, _Ls) * 100.0))
    h_max = max(pil["hx"] * 100.0 * esc, vg["h"] * 100.0 * esc, h_sapata)
    cy = TOPO_SECAO + h_max / 2.0             # centro comum das tres secoes
    Hn = TOPO_SECAO + h_max + FOLGA_COTA + (ALTURA_NOTA if _gancho else 0.0)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hn}" '
             f'viewBox="0 0 {W} {Hn}" font-family="Arial,Helvetica,sans-serif">',
             f'<rect width="{W}" height="{Hn}" fill="#ffffff"/>',
             f'<text x="20" y="26" font-size="15" font-weight="bold" fill="#111">'
             f'ARMACAO - GALPAO DE CONCRETO C{sp["fck_MPa"]:.0f} '
             f'(vao {sp["vao"]:.0f} m, pe-direito {sp["H"]:.0f} m'
             f'{_esc(_suf_ed)})</text>']

    # ---- barras do pilar ----
    import executivo_concreto as ex
    q = ex.quadro_de_aco(r)
    n1 = next((x for x in q if x["pos"].startswith("N1")), None)
    phi_l = n1["phi_mm"] if n1 else 12.5
    n_l = (n1["n"] // (sp["n_porticos"] * 2)) if n1 else 4
    rot_pil = f'PILAR {pil["hy"]*100:.0f}x{pil["hx"]*100:.0f} - {n_l} f{phi_l:.1f}'
    parts.append(_svg_secao(180, cy, pil["hy"] * 100, pil["hx"] * 100, esc, rot_pil,
                            [(phi_l, n_l)], faces="perim"))

    # ---- viga de cobertura ----
    # A viga de cobertura de vao longo sai PROTENDIDA (sem armadura passiva de
    # tracao): arr_inf/arr_sup ficam None. Desenhar a secao como se fosse armada
    # rotulava "inf 0 f0.0" E ainda caia num fallback que INVENTAVA 2 f10 que o
    # calculo nunca produziu - a prancha mostrando aco que nao existe.
    ai = vg["arr_inf"]; asup = vg["arr_sup"]
    barras_v = []
    if ai and ai.get("n"):
        barras_v.append((ai["phi"], ai["n"]))
    if asup and asup.get("n"):
        barras_v.append((asup["phi"], asup["n"]))
    protendida = bool(vg.get("protendida")) and vg.get("n_cordoalhas")
    if protendida:
        n_cord = int(vg["n_cordoalhas"]); phi_cord = float(vg["phi_cord"])
        rot_v = (f'VIGA COB. {vg["b"]*100:.0f}x{vg["h"]*100:.0f} - PROTENDIDA '
                 f'{n_cord} cord. f{phi_cord:.1f}')
        barras_v = [(phi_cord, n_cord)]
    elif barras_v:
        rot_v = (f'VIGA COB. {vg["b"]*100:.0f}x{vg["h"]*100:.0f} - inf '
                 f'{ai["n"]} f{ai["phi"]:.1f}')
    else:
        # nem passiva nem protensao: a secao sai SEM barra e o rotulo diz isso.
        rot_v = (f'VIGA COB. {vg["b"]*100:.0f}x{vg["h"]*100:.0f} - '
                 f'ARMADURA NAO DEFINIDA (ver memorial)')
    parts.append(_svg_secao(460, cy, vg["b"] * 100, vg["h"] * 100, esc, rot_v,
                            barras_v, faces="linha"))

    # ---- sapata (planta com malha) ----
    # a sapata e em METROS (ordem de 2-3 m) -> escala PROPRIA p/ caber no slot
    # (~150 px), senao estoura a prancha e cobre a viga.
    if r["sapata"]["aprovado"]:
        B, Ls, hf = r["sapata"]["aprovado"][:3]
        esc_sap = 150.0 / (max(B, Ls) * 100.0)         # cabe em ~150 px
        parts.append(_svg_sapata(740, cy, B, Ls, hf, esc_sap, r))
    # G50: gancho 135 no ARTEFATO (SVG), nao so no dict. C55-C90 exige estribo
    # com gancho a 135 graus (NBR 6118 18.4.3 NOTA); em C50 nada muda.
    if _gancho:
        parts.append(f'<text x="20" y="{Hn - 14:.0f}" font-size="12" font-weight="bold" '
                     f'fill="#111">{_esc("NOTA C55-C90 (18.4.3): estribos do pilar com gancho a 135 graus")}</text>')
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


def planta_formas_svg(r):
    """Planta de FORMAS (vista de topo) do galpao de concreto em SVG puro-Python:
    malha de pilares (2 por portico), sapatas sob cada pilar, vigas de cobertura
    como linhas entre os topos, eixos numerados (porticos 1..n) e letreados (A/B
    das duas linhas de pilar) e cotas (vao, comprimento, espacamento). Convencao
    do papel: X = vao (horizontal), Y = comprimento (vertical)."""
    sp = r["spec"]
    vao = sp["vao"]; comp = sp["comprimento"]; n = sp["n_porticos"]; s = sp["s"]
    hy = r["pilar"]["hy"]; hx = r["pilar"]["hx"]           # secao do pilar (m)
    sap = (r.get("sapata") or {}).get("aprovado") if r.get("sapata") else None
    B = sap[0] if sap else None; Ls = sap[1] if sap else None

    margem = 108.0
    escala = min(560.0 / max(vao, 1e-6), 640.0 / max(comp, 1e-6))   # px por metro
    W = max(vao * escala + 2 * margem, 560.0)          # min p/ o titulo nao estourar
    H = comp * escala + 2 * margem

    def X(x_m):   # x_m em [-vao/2, vao/2] -> px
        return margem + (x_m + vao / 2.0) * escala

    def Y(y_m):   # y_m em [0, comp] -> px (topo = portico 1)
        return margem + y_m * escala

    s_svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
             f'viewBox="0 0 {W:.0f} {H:.0f}" font-family="sans-serif">',
             f'<rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" fill="white"/>',
             f'<text x="{margem}" y="{margem-64:.0f}" font-size="14" font-weight="bold">'
             f'PLANTA DE FORMAS - GALPAO DE CONCRETO{_esc(_carimbo_edicao(r))}</text>',
             f'<text x="{margem}" y="{margem-48:.0f}" font-size="11" fill="#444">'
             f'vao {vao:.1f} x comp {comp:.1f} m ; {n} porticos @ {s:.2f} m ; '
             f'pilar {hy*100:.0f}x{hx*100:.0f} cm</text>']
    # contorno do galpao
    s_svg.append(f'<rect x="{X(-vao/2):.1f}" y="{Y(0):.1f}" width="{vao*escala:.1f}" '
                 f'height="{comp*escala:.1f}" fill="none" stroke="#bbb" stroke-dasharray="4 3"/>')
    x_lados = [(-vao / 2.0, "A"), (vao / 2.0, "B")]
    # eixos + letras das linhas de pilar
    for xm, letra in x_lados:
        s_svg.append(f'<line x1="{X(xm):.1f}" y1="{Y(0)-20:.1f}" x2="{X(xm):.1f}" '
                     f'y2="{Y(comp)+10:.1f}" stroke="#e0e0e0"/>')
        s_svg.append(f'<circle cx="{X(xm):.1f}" cy="{Y(0)-30:.1f}" r="11" fill="white" '
                     f'stroke="#333"/><text x="{X(xm):.1f}" y="{Y(0)-26:.1f}" '
                     f'font-size="12" text-anchor="middle">{letra}</text>')
    # sapatas (por baixo), pilares (por cima), vigas (linhas), eixos numerados
    for j in range(n):
        ym = j * s
        # eixo numerado do portico (numero a esquerda)
        s_svg.append(f'<text x="{X(-vao/2)-30:.1f}" y="{Y(ym)+4:.1f}" font-size="12" '
                     f'text-anchor="middle">{j+1}</text>')
        # viga de cobertura ligando os dois pilares
        s_svg.append(f'<line x1="{X(-vao/2):.1f}" y1="{Y(ym):.1f}" x2="{X(vao/2):.1f}" '
                     f'y2="{Y(ym):.1f}" stroke="#888" stroke-width="1.5"/>')
        for xm, _ in x_lados:
            if B and Ls:                                   # sapata
                s_svg.append(f'<rect x="{X(xm)-B/2*escala:.1f}" y="{Y(ym)-Ls/2*escala:.1f}" '
                             f'width="{B*escala:.1f}" height="{Ls*escala:.1f}" fill="#f0f0f0" '
                             f'stroke="#999"/>')
            # pilar: hx e a dimensao NO PLANO DO PORTICO (// vento, o eixo em que
            # o pilar foi dimensionado como balanco) e o papel tem X = vao -> hx vai
            # no eixo X. Trocado, a forma sai girada 90 graus e a obra concreta o
            # pilar com o eixo FRACO no plano do portico (Ix/Iy = (hx/hy)^2).
            s_svg.append(f'<rect x="{X(xm)-hx/2*escala:.1f}" y="{Y(ym)-hy/2*escala:.1f}" '
                         f'width="{hx*escala:.1f}" height="{hy*escala:.1f}" fill="#555" '
                         f'stroke="black"/>')
    # cota do vao (embaixo) e do comprimento (esquerda)
    yb = Y(comp) + 35
    s_svg.append(f'<line x1="{X(-vao/2):.1f}" y1="{yb:.1f}" x2="{X(vao/2):.1f}" y2="{yb:.1f}" '
                 f'stroke="#333"/><text x="{X(0):.1f}" y="{yb-5:.1f}" font-size="12" '
                 f'text-anchor="middle">{vao:.2f} m</text>')
    xl = X(-vao / 2) - 48
    s_svg.append(f'<line x1="{xl:.1f}" y1="{Y(0):.1f}" x2="{xl:.1f}" y2="{Y(comp):.1f}" '
                 f'stroke="#333"/><text x="{xl-6:.1f}" y="{Y(comp/2):.1f}" font-size="12" '
                 f'text-anchor="middle" transform="rotate(-90 {xl-6:.1f} {Y(comp/2):.1f})">'
                 f'{comp:.2f} m</text>')
    s_svg.append('</svg>')
    return "\n".join(x for x in s_svg if x)


def gerar_planta_formas(r, path):
    """Escreve a planta de formas (SVG) em `path`. Retorna o path."""
    svg = planta_formas_svg(r)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


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
                  "fck": 30e3, "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"})
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
                  "fck": 30e3, "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"})
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(gerar_prancha(r, "armacao_galpao_concreto.svg"))


# ---------------------------------------------------------------------------
# PLANTA DE FORMAS + ARMACAO DA LAJE (laje_concreto)
# ---------------------------------------------------------------------------

def _hachura_engaste(x1, y1, x2, y2, lado, n=14, t=9.0):
    """Hachura curta indicando borda ENGASTADA (convencao das tabelas de placa:
    linha simples = apoiada, hachurada = engastada)."""
    s = []
    dx, dy = (x2 - x1) / n, (y2 - y1) / n
    for i in range(n + 1):
        x, y = x1 + i * dx, y1 + i * dy
        ox, oy = (t * lado[0], t * lado[1])
        s.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + ox:.1f}" '
                 f'y2="{y + oy:.1f}" stroke="#666" stroke-width="1"/>')
    return "".join(s)


def planta_laje_svg(r, quadro=None, extras=None, titulo_extra=None):
    """Planta de formas + armacao de um painel de laje macica, a partir do dict
    de laje_concreto.verifica_laje. Mostra o painel na escala, a convencao de
    vinculacao de cada borda (hachura = engaste), as cotas, as barras positivas
    das duas direcoes, as negativas sobre as bordas engastadas, o quadro de
    ferros e o resumo de verificacao (ELU/ELS).

    `extras` (G111): (altura_extra_px, [linhas_svg]) anexadas abaixo da folha
    de 700 px - sem ele a saida e a de sempre. `titulo_extra`: sufixo da
    segunda linha do cabecalho (diz QUAL painel e o desenho)."""
    import laje_concreto as lj
    if quadro is None:
        quadro = lj.quadro_de_ferros(r)
    lx, ly, h = r["lx"], r["ly"], r["h"]
    eng = set(lj.ENGASTES[r["caso"]]) if r["duas_direcoes"] else set()

    W, H = 1040, 700 + (extras[0] if extras else 0)
    mx, my = 90, 110                                   # margens do desenho
    larg, alt = 480.0, 430.0
    escala = min(larg / lx, alt / ly)                  # px por metro
    w_px, h_px = lx * escala, ly * escala
    x0, y0 = mx, my
    x1, y1 = x0 + w_px, y0 + h_px

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="Arial,Helvetica,sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="30" y="34" font-size="16" font-weight="bold" fill="#111">'
         f'{_esc("PLANTA DE FORMAS E ARMACAO - LAJE MACICA" + _carimbo_edicao(r))}</text>',
          f'<text x="30" y="56" font-size="12" fill="#444">'
          f'{_esc("painel %.2f x %.2f m (lambda %.2f) ; h = %.0f cm ; d = %.1f cm ; "
                  "C%.0f ; caso %d ; %s%s" % (lx, ly, r["lambda"], h * 100, r["d"] * 100, r["fck"] / 1000.0, r["caso"], "armada em 2 direcoes" if r["duas_direcoes"] else "armada em 1 direcao", titulo_extra or ""))}</text>']

    # painel (vigas de apoio como contorno grosso)
    s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w_px:.1f}" height="{h_px:.1f}" '
             f'fill="#f7f7f5" stroke="#111" stroke-width="3"/>')
    # convencao de vinculacao: hachura nas bordas engastadas
    if "x0" in eng:
        s.append(_hachura_engaste(x0, y0, x0, y1, (-1, 0)))
    if "x1" in eng:
        s.append(_hachura_engaste(x1, y0, x1, y1, (1, 0)))
    if "y0" in eng:
        s.append(_hachura_engaste(x0, y0, x1, y0, (0, -1)))
    if "y1" in eng:
        s.append(_hachura_engaste(x0, y1, x1, y1, (0, 1)))

    # armadura NEGATIVA: faixa de 0,25 lx a partir de cada borda engastada.
    # Cor SOLIDA clara de proposito: fill-opacity nao e honrado por
    # renderizadores estritos (QtSvg/TechDraw/svglib) e a faixa vira um bloco
    # vermelho que apaga a malha - visto ao ABRIR o PNG, nao na barra verde.
    faixa = lj.FRACAO_NEGATIVA * lx * escala
    for b in eng:
        if b == "x0":
            s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{faixa:.1f}" '
                     f'height="{h_px:.1f}" fill="#fbe4e4" '
                     f'stroke="#dc2626" stroke-dasharray="5 4"/>')
        elif b == "x1":
            s.append(f'<rect x="{x1 - faixa:.1f}" y="{y0:.1f}" width="{faixa:.1f}" '
                     f'height="{h_px:.1f}" fill="#fbe4e4" '
                     f'stroke="#dc2626" stroke-dasharray="5 4"/>')
        elif b == "y0":
            s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w_px:.1f}" '
                     f'height="{faixa:.1f}" fill="#fbe4e4" '
                     f'stroke="#dc2626" stroke-dasharray="5 4"/>')
        elif b == "y1":
            s.append(f'<rect x="{x0:.1f}" y="{y1 - faixa:.1f}" width="{w_px:.1f}" '
                     f'height="{faixa:.1f}" fill="#fbe4e4" '
                     f'stroke="#dc2626" stroke-dasharray="5 4"/>')

    # armadura POSITIVA: barras em x (horizontais) e em y (verticais)
    esquematico = []

    def malha(chave, direcao, cor, dash):
        a = r["armaduras"].get(chave)
        if not a or not a["malha"]["phi_mm"]:
            return
        passo = a["malha"]["s"] * escala
        n = max(int((h_px if direcao == "x" else w_px) / max(passo, 1e-6)) - 1, 1)
        if n > 60:                                      # nao poluir o desenho
            n = 60
            esquematico.append(chave)
        for i in range(1, n + 1):
            if direcao == "x":
                yy = y0 + i * (h_px / (n + 1))
                s.append(f'<line x1="{x0 + 6:.1f}" y1="{yy:.1f}" x2="{x1 - 6:.1f}" '
                         f'y2="{yy:.1f}" stroke="{cor}" stroke-width="1" '
                         f'stroke-dasharray="{dash}"/>')
            else:
                xx = x0 + i * (w_px / (n + 1))
                s.append(f'<line x1="{xx:.1f}" y1="{y0 + 6:.1f}" x2="{xx:.1f}" '
                         f'y2="{y1 - 6:.1f}" stroke="{cor}" stroke-width="1" '
                         f'stroke-dasharray="{dash}"/>')

    malha("m_x", "x", "#1d4ed8", "none")
    malha("m_y", "y", "#16a34a", "6 3")
    nota_malha = (" (malha desenhada em passo reduzido - representacao esquematica)"
                  if esquematico else "")

    # chamadas das posicoes (ligam o desenho ao quadro de ferros)
    chamadas = []
    a_x = r["armaduras"].get("m_x")
    if a_x and a_x["malha"]["phi_mm"]:
        chamadas.append((x0 + w_px * 0.55, y0 + h_px * 0.62, "#1d4ed8",
                         "N1 %.1f c/%.1f" % (a_x["malha"]["phi_mm"],
                                             a_x["malha"]["s"] * 100)))
    a_y = r["armaduras"].get("m_y")
    if a_y and a_y["malha"]["phi_mm"]:
        chamadas.append((x0 + w_px * 0.55, y0 + h_px * 0.72, "#16a34a",
                         "N2 %.1f c/%.1f" % (a_y["malha"]["phi_mm"],
                                             a_y["malha"]["s"] * 100)))
    pos_neg = {"x0": "N3", "x1": "N3", "y0": "N4", "y1": "N4"}
    for b in sorted(eng):
        chave = "x_x" if b in ("x0", "x1") else "x_y"
        a = r["armaduras"].get(chave)
        if not a or not a["malha"]["phi_mm"]:
            continue
        rot = "%s %.1f c/%.1f" % (pos_neg[b], a["malha"]["phi_mm"],
                                  a["malha"]["s"] * 100)
        if b == "x0":
            chamadas.append((x0 + faixa * 0.5, y0 + h_px * 0.30, "#b91c1c", rot))
        elif b == "x1":
            chamadas.append((x1 - faixa * 0.5, y0 + h_px * 0.30, "#b91c1c", rot))
        elif b == "y0":
            chamadas.append((x0 + w_px * 0.72, y0 + faixa * 0.5, "#b91c1c", rot))
        else:
            chamadas.append((x0 + w_px * 0.72, y1 - faixa * 0.5, "#b91c1c", rot))
    for cx, cy, cor, rot in chamadas:
        larg_rot = 7.0 * len(rot)
        # a chamada nao pode vazar do painel (visto ao abrir o PNG: a de N3 saia
        # metade fora quando a faixa de 0,25 lx e estreita)
        cx = min(max(cx, x0 + larg_rot / 2 + 2), x1 - larg_rot / 2 - 2)
        s.append(f'<rect x="{cx - larg_rot / 2:.1f}" y="{cy - 11:.1f}" '
                 f'width="{larg_rot:.1f}" height="16" fill="white" stroke="{cor}" '
                 f'stroke-width="0.8"/>')
        s.append(f'<text x="{cx:.1f}" y="{cy + 1:.1f}" font-size="11" '
                 f'text-anchor="middle" fill="{cor}">{_esc(rot)}</text>')

    # cotas
    yb = y1 + 34
    s.append(f'<line x1="{x0:.1f}" y1="{yb:.1f}" x2="{x1:.1f}" y2="{yb:.1f}" '
             f'stroke="#111"/>'
             f'<text x="{(x0 + x1) / 2:.1f}" y="{yb - 6:.1f}" font-size="12" '
             f'text-anchor="middle">{_esc("lx = %.2f m" % lx)}</text>')
    xl = x0 - 40
    s.append(f'<line x1="{xl:.1f}" y1="{y0:.1f}" x2="{xl:.1f}" y2="{y1:.1f}" '
             f'stroke="#111"/>'
             f'<text x="{xl - 6:.1f}" y="{(y0 + y1) / 2:.1f}" font-size="12" '
             f'text-anchor="middle" transform="rotate(-90 {xl - 6:.1f} '
             f'{(y0 + y1) / 2:.1f})">{_esc("ly = %.2f m" % ly)}</text>')

    # legenda das bordas
    s.append(f'<text x="{x0:.1f}" y="{y1 + 58:.1f}" font-size="11" fill="#555" '
             f'text-anchor="start">'
             f'{_esc("borda hachurada = engastada ; linha simples = apoiada ; "
                     "faixa vermelha = armadura negativa (0,25 lx)") + nota_malha}</text>')

    # ---- quadro de ferros ------------------------------------------------
    qx, qy = 620, 96
    s.append(f'<text x="{qx}" y="{qy - 12}" font-size="13" font-weight="bold">'
             f'{_esc("QUADRO DE FERROS")}</text>')
    cols = [(0, "POS"), (52, "BITOLA"), (128, "ESP."), (186, "COMP."),
            (250, "QTD"), (300, "PESO")]
    for dx, nome in cols:
        s.append(f'<text x="{qx + dx}" y="{qy + 6}" font-size="11" '
                 f'font-weight="bold">{_esc(nome)}</text>')
    s.append(f'<line x1="{qx}" y1="{qy + 11}" x2="{qx + 360}" y2="{qy + 11}" '
             f'stroke="#111"/>')
    yy = qy + 28
    for f in quadro:
        vals = [f["pos"], "%.1f mm" % f["phi_mm"], "c/ %.1f" % f["s_cm"],
                "%.2f m" % f["comprimento_m"], "%d" % f["n"], "%.1f kg" % f["peso_kg"]]
        for (dx, _), v in zip(cols, vals):
            s.append(f'<text x="{qx + dx}" y="{yy}" font-size="11">{_esc(v)}</text>')
        yy += 19
    peso = sum(f["peso_kg"] for f in quadro)
    area = lx * ly
    s.append(f'<line x1="{qx}" y1="{yy - 13}" x2="{qx + 360}" y2="{yy - 13}" '
             f'stroke="#999"/>')
    s.append(f'<text x="{qx}" y="{yy + 4}" font-size="11" font-weight="bold">'
             f'{_esc("TOTAL %.1f kg  (%.2f kg/m2 em %.1f m2)" % (peso, peso / area, area))}'
             f'</text>')

    # ---- resumo da verificacao -------------------------------------------
    ry = yy + 44
    s.append(f'<text x="{qx}" y="{ry}" font-size="13" font-weight="bold">'
             f'{_esc("VERIFICACOES")}</text>')
    fl = r["flecha"]; c = r["cortante"]
    itens = [("Momentos Md (kN.m/m)", "m_x %.2f | m_y %.2f | X_x %.2f | X_y %.2f"
              % (r["momentos"]["m_x"], r["momentos"].get("m_y", 0.0),
                 r["momentos"].get("x_x", 0.0), r["momentos"].get("x_y", 0.0))),
             ("Cortante 19.4.1", "V_Sd %.1f / V_Rd1 %.1f kN/m -> %s"
              % (c["V_sd"], c["V_rd1"], "ATENDE" if c["ok"] else "REPROVA")),
             ("Flecha total", "%.1f mm / limite %.1f mm -> %s"
              % (fl["f_total"] * 1000, r["lim_flecha"] * 1000,
                 "ATENDE" if r["ok_flecha"] else "REPROVA")),
             ("Fissuracao ELS-W", ("wk %.3f / %.1f mm -> %s"
              % (r["fissuracao"]["wk_mm"], r["fissuracao"]["wk_lim_mm"],
                 "ATENDE" if r["fissuracao"]["OK"] else "REPROVA"))
              if r["fissuracao"] else "nao aplicavel")]
    for i, (rot, val) in enumerate(itens):
        s.append(f'<text x="{qx}" y="{ry + 20 + i * 18}" font-size="11" '
                 f'font-weight="bold">{_esc(rot)}</text>')
        s.append(f'<text x="{qx + 118}" y="{ry + 20 + i * 18}" font-size="11">'
                 f'{_esc(val)}</text>')
    if r["reacoes"]:
        txt = " ; ".join("%s %.1f" % (b, v["v"])
                         for b, v in sorted(r["reacoes"].items()))
        s.append(f'<text x="{qx}" y="{ry + 20 + len(itens) * 18}" font-size="11" '
                 f'font-weight="bold">{_esc("Reacoes (kN/m)")}</text>')
        s.append(f'<text x="{qx + 118}" y="{ry + 20 + len(itens) * 18}" '
                 f'font-size="11">{_esc(txt)}</text>')
    veredito = "ATENDE" if r["OK"] else "NAO ATENDE"
    cor = "#166534" if r["OK"] else "#b91c1c"
    s.append(f'<text x="{qx}" y="{700 - 40}" font-size="14" font-weight="bold" '
             f'fill="{cor}">{_esc("RESULTADO: " + veredito)}</text>')
    if extras:
        s.extend(extras[1])
    s.append('</svg>')
    return "\n".join(s)


def gerar_planta_laje(r, path, quadro=None, lajes_por_painel=None):
    """Escreve a planta da laje (SVG) em `path`. Retorna o path.

    Com `lajes_por_painel` (o dict de `detalha_lajes_por_painel`) sai a
    folha G111 de todos os paineis; sem ele, a de um painel de sempre."""
    with open(path, "w", encoding="utf-8") as f:
        if lajes_por_painel is not None:
            f.write(planta_lajes_todos_paineis_svg(lajes_por_painel))
        else:
            f.write(planta_laje_svg(r, quadro))
    return path


def planta_lajes_todos_paineis_svg(det):
    """PE-CO-03, G111 opcao (a): TODOS os paineis detalhados, um quadro de
    ferros por painel, mesma h adotada.

    det: o dict de `laje_concreto.detalha_lajes_por_painel`. O desenho
    grande continua sendo o do painel critico (o que converge a
    espessura), mas o titulo diz QUAL ele e ("Lij, K de N") e a secao
    abaixo lista cada painel com o seu quadro - a lente
    drawing-vs-data conta os grupos `data-painel="i,j"` por parse XML e
    exige o conjunto exato de `pavimento["paineis"]`. Painel que nao
    atende sai com NAO ATENDE + o primeiro aviso, nunca omitido."""
    n = len(det["paineis"])
    ci, cj = det["crit_ij"]
    crit = next(it for it in det["paineis"]
                if (it["painel"]["i"], it["painel"]["j"]) == (ci, cj))
    rot = lambda p: "L%d%d" % (p["i"] + 1, p["j"] + 1)  # noqa: E731

    linhas = []
    y = 700 + 28
    linhas.append(
        f'<text x="30" y="{y}" font-size="14" font-weight="bold" fill="#111">'
        f'{_esc("QUADROS DE FERROS POR PAINEL - TODOS OS %d PAINEIS "
                "DETALHADOS (h = %.0f cm para todos)" % (n, det["h_adotada"] * 100))}</text>')
    y += 20
    linhas.append(
        f'<text x="30" y="{y}" font-size="11" fill="#555">'
        f'{_esc("desenho acima: painel critico %s (%d de %d) ; cada painel "
                "com o seu caso de vinculacao" % (rot(crit["painel"]),
                                                  det["paineis"].index(crit) + 1, n))}</text>')
    y += 10
    for it in det["paineis"]:
        p, r = it["painel"], it["resultado"]
        q = it["quadro"]
        peso = sum(f["peso_kg"] for f in q)
        area = p["lx"] * p["ly"]
        y += 22
        marca = "  [CRITICO]" if (p["i"], p["j"]) == (ci, cj) else ""
        linhas.append(f'<g data-painel="{p["i"]},{p["j"]}">')
        linhas.append(
            f'<text x="30" y="{y}" font-size="12" font-weight="bold" fill="#111">'
            f'{_esc("%s - %.2f x %.2f m ; caso %d ; TOTAL %.1f kg "
                    "(%.2f kg/m2)%s" % (rot(p), p["lx"], p["ly"], p["caso"],
                                        peso, peso / area, marca))}</text>')
        for f in q:
            y += 17
            linhas.append(
                f'<text x="48" y="{y}" font-size="11" fill="#333">'
                f'{_esc("%s %.1f mm c/ %.1f - %.2f m x %d = %.1f kg"
                        % (f["pos"], f["phi_mm"], f["s_cm"],
                           f["comprimento_m"], f["n"], f["peso_kg"]))}</text>')
        y += 17
        vok = "ATENDE" if r["OK"] else "NAO ATENDE"
        av = (" - " + r["avisos"][0]) if (not r["OK"] and r["avisos"]) else ""
        linhas.append(
            f'<text x="48" y="{y}" font-size="11" font-weight="bold" '
            f'fill="{"#166534" if r["OK"] else "#b91c1c"}">'
            f'{_esc("%s: %s%s" % (rot(p), vok, av))}</text>')
        linhas.append('</g>')
    altura_extra = (y + 20) - 700
    titulo_extra = (" ; painel critico %s (%d de %d paineis - quadros de "
                    "todos abaixo)" % (rot(crit["painel"]),
                                       det["paineis"].index(crit) + 1, n))
    return planta_laje_svg(crit["resultado"], quadro=crit["quadro"],
                           extras=(altura_extra, linhas),
                           titulo_extra=titulo_extra)
