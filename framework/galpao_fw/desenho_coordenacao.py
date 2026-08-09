# ============================================================================
# desenho_coordenacao.py - O QUE ESTE SCRIPT FAZ / DESENHA
# Gera a PRANCHA DE COORDENACAO do modelo FEDERADO em SVG puro-Python (autocontido,
# sem FreeCAD/TechDraw), a partir dos membros federados do turnkey
# (galpao_turnkey._membros_federados) e do relatorio de clash
# (checa_interferencia_federada). E' o desenho-assinatura da COORDENACAO: mostra as
# 6 disciplinas JUNTAS no frame comum, coloridas por disciplina, em duas projecoes:
#   - PLANTA (X-Y: comprimento x largura), no topo;
#   - ELEVACAO (X-Z: comprimento x altura), embaixo (pega os verticais - descidas
#     pluviais, colunas, prumadas - que somem na planta).
# Sobre as projecoes, marca em VERMELHO os pontos de CLASH A REVISAR (os candidatos
# reais de conflito), com legenda de disciplinas e um quadro-resumo de clash.
#
# Frame comum do turnkey: X=comprimento, Y=largura, Z=altura (mm). Cada membro tem
# p1/p2 (barra) OU centro/dims (caixa: UTA, reservatorio). Cor por disciplina, lida
# do PREFIXO da marca (C-=concreto, A-=aco, E-=eletrico, I-=incendio, H-=climatizacao,
# P-=hidraulica), o mesmo prefixo que o federado aplica.
# ============================================================================
"""Prancha de coordenacao do modelo federado (planta + elevacao, 6 disciplinas
coloridas + clash a revisar) em SVG puro-Python, sem FreeCAD."""

from __future__ import annotations

# cor e rotulo por disciplina (chave = prefixo da marca no federado)
DISCIPLINAS = {
    "C": ("#6b7280", "Concreto"), "A": ("#2563eb", "Aco"),
    "E": ("#f59e0b", "Eletrico"), "I": ("#dc2626", "Incendio"),
    "H": ("#0891b2", "Climatizacao"), "P": ("#16a34a", "Hidraulica"),
}
CLASH_COR = "#e11d48"


def _esc(txt):
    """Escapa &<> p/ o texto ser XML-valido (SVG e' XML): um '<'/'&' cru quebra o
    SVG inteiro em renderers estritos (QtSvg/TechDraw DrawViewSymbol)."""
    return (str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _t(x, y, txt, size=13, anchor="middle", weight="normal", color="#111"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}" fill="{color}">{_esc(txt)}</text>')


def _line(x1, y1, x2, y2, w=1.5, color="#111", dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="{w}"{d}/>')


def _disc_do_membro(m):
    """Prefixo de disciplina (C/A/E/I/H/P) da marca federada; None se nao prefixado."""
    marca = str(m.get("marca", ""))
    if len(marca) >= 2 and marca[1] == "-" and marca[0] in DISCIPLINAS:
        return marca[0]
    return None


def _centro(m):
    """Centro do membro (mm) no frame comum: media de p1/p2 (barra) ou 'centro' (caixa)."""
    if m.get("p1") and m.get("p2"):
        p1, p2 = m["p1"], m["p2"]
        return [(p1[k] + p2[k]) / 2.0 for k in range(3)]
    if m.get("centro"):
        return list(m["centro"])
    return None


def _extremos(membros):
    """Bounding box (xmin,xmax,ymin,ymax,zmin,zmax) de todos os membros com geometria."""
    xs, ys, zs = [], [], []
    for m in membros:
        pts = []
        if m.get("p1") and m.get("p2"):
            pts = [m["p1"], m["p2"]]
        elif m.get("centro"):
            pts = [m["centro"]]
        for p in pts:
            xs.append(p[0]); ys.append(p[1]); zs.append(p[2])
    if not xs:
        return None
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _projecao(membros, clashes, x0, y0, w, h, ejx, ejy, bb, rotulo):
    """Desenha uma projecao (planta ou elevacao) num retangulo (x0,y0,w,h).
    ejx/ejy: indices do frame (0=X,1=Y,2=Z) mapeados p/ tela (x horizontal, y ->
    invertido). bb: bounding box global. Retorna lista de fragmentos SVG."""
    xmin, xmax, ymin, ymax, zmin, zmax = bb
    lo = (xmin, ymin, zmin); hi = (xmax, ymax, zmax)
    du = (hi[ejx] - lo[ejx]) or 1.0
    dv = (hi[ejy] - lo[ejy]) or 1.0
    pad_top = 26.0                              # faixa p/ o titulo (nao invadir o desenho)
    hdes = h - pad_top
    esc = min(w / du, hdes / dv) * 0.92
    ow = du * esc; oh = dv * esc
    ox = x0 + (w - ow) / 2.0
    oy = y0 + pad_top + (hdes - oh) / 2.0

    def _map(p):
        u = (p[ejx] - lo[ejx]) * esc
        v = (p[ejy] - lo[ejy]) * esc
        return ox + u, oy + oh - v            # v invertido (tela cresce p/ baixo)

    s = [f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" '
         f'fill="#fbfbfb" stroke="#bbb" stroke-width="1"/>',
         _t(x0 + 8, y0 + 18, rotulo, 13, anchor="start", weight="bold", color="#333")]
    # membros
    for m in membros:
        dsc = _disc_do_membro(m)
        cor = DISCIPLINAS.get(dsc, ("#999", ""))[0]
        if m.get("p1") and m.get("p2"):
            a = _map(m["p1"]); b = _map(m["p2"])
            larg = 2.4 if dsc in ("C", "A") else 1.6
            s.append(_line(a[0], a[1], b[0], b[1], larg, cor))
        else:
            c = _centro(m)
            if c is not None:
                cx, cy = _map(c)
                s.append(f'<rect x="{cx - 4:.1f}" y="{cy - 4:.1f}" width="8" height="8" '
                         f'fill="{cor}" stroke="#333" stroke-width="0.7"/>')
    # marcadores de clash A REVISAR (X vermelho no ponto medio entre a e b)
    idx = {str(m.get("marca", "")): _centro(m) for m in membros}
    for c in clashes:
        ca = idx.get(str(c.get("a"))); cb = idx.get(str(c.get("b")))
        pts = [p for p in (ca, cb) if p is not None]
        if not pts:
            continue
        mid = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
        mx, my = _map(mid)
        r = 5
        s.append(_line(mx - r, my - r, mx + r, my + r, 2.0, CLASH_COR))
        s.append(_line(mx - r, my + r, mx + r, my - r, 2.0, CLASH_COR))
    return s


def coordenacao_svg(membros, clash=None, titulo="COORDENACAO - MODELO FEDERADO"):
    """Prancha de coordenacao (planta X-Y + elevacao X-Z) do modelo federado. String SVG.
    membros: lista do federado (marca prefixada por disciplina). clash: relatorio de
    checa_interferencia_federada (usa 'revisar'). Sem geometria -> SVG minimo com aviso."""
    W, Hh = 1000, 700
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" '
         f'viewBox="0 0 {W} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         _t(W / 2, 28, titulo, 18, weight="bold")]

    bb = _extremos(membros or [])
    if bb is None:
        s.append(_t(W / 2, Hh / 2, "sem geometria federada", 16, color="#999"))
        s.append('</svg>')
        return "\n".join(s)

    revisar = (clash or {}).get("revisar", [])
    if not revisar and clash:
        revisar = [c for c in clash.get("clashes", []) if not c.get("esperado")]

    # area de desenho (faixa direita p/ legenda/resumo)
    ax, aw = 40, 640
    # PLANTA (X horizontal, Y vertical) em cima ; ELEVACAO (X horizontal, Z vertical) embaixo
    s += _projecao(membros, revisar, ax, 45, aw, 300, 0, 1, bb,
                   "PLANTA (comprimento x largura)")
    s += _projecao(membros, revisar, ax, 370, aw, 300, 0, 2, bb,
                   "ELEVACAO (comprimento x altura)")

    # --- LEGENDA de disciplinas (so as presentes) ---
    presentes = []
    for m in membros:
        d = _disc_do_membro(m)
        if d and d not in presentes:
            presentes.append(d)
    lx, ly = 710, 55
    s.append(f'<rect x="{lx}" y="{ly}" width="250" height="{34 + len(presentes) * 24 + 24}" '
             f'fill="white" stroke="#111" stroke-width="1"/>')
    s.append(_t(lx + 125, ly + 22, "DISCIPLINAS", 14, weight="bold"))
    for i, d in enumerate(presentes):
        cor, rot = DISCIPLINAS[d]
        yy = ly + 44 + i * 24
        s.append(_line(lx + 16, yy, lx + 40, yy, 4.0, cor))
        s.append(_t(lx + 48, yy + 4, rot, 12, anchor="start"))
    yclash = ly + 44 + len(presentes) * 24
    s.append(_line(lx + 22, yclash, lx + 34, yclash + 12, 2.0, CLASH_COR))
    s.append(_line(lx + 22, yclash + 12, lx + 34, yclash, 2.0, CLASH_COR))
    s.append(_t(lx + 48, yclash + 10, "Clash a revisar", 12, anchor="start"))

    # --- QUADRO-RESUMO de clash ---
    qx, qy = 710, ly + 60 + len(presentes) * 24 + 30
    n_rev = (clash or {}).get("n_revisar", len(revisar))
    n_esp = (clash or {}).get("n_esperado",
                              len((clash or {}).get("esperados", [])))
    linhas = ["Membros: %d" % len(membros),
              "Conflitos: %d" % (clash or {}).get("n_clashes", n_rev + n_esp),
              "A revisar: %d" % n_rev,
              "Esperados (montagem): %d" % n_esp]
    por_par = (clash or {}).get("por_par", {})
    for k, v in sorted(por_par.items())[:6]:
        linhas.append("  %s: %d" % (k, v))
    box_h = 34 + len(linhas) * 17
    s.append(f'<rect x="{qx}" y="{qy}" width="250" height="{box_h}" fill="white" '
             f'stroke="#111" stroke-width="1"/>')
    s.append(_t(qx + 125, qy + 20, "RESUMO DE CLASH", 13, weight="bold"))
    for i, ln in enumerate(linhas):
        s.append(_t(qx + 14, qy + 40 + i * 17, ln, 11, anchor="start"))

    s.append('</svg>')
    return "\n".join(s)


def gerar_prancha(membros, clash, path, titulo="COORDENACAO - MODELO FEDERADO"):
    """Escreve a prancha de coordenacao (SVG) em `path`."""
    svg = coordenacao_svg(membros, clash, titulo)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


def _selftest():
    import galpao_turnkey as tk
    spec = {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "eletrico": {"tensao_V": 380.0,
                     "cargas": {"iluminacao_kW": 20.0, "ilum_fp": 0.92,
                                "ocupacao": "industrial"},
                     "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}},
        "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                     "deteccao": {"viga_m": 0.0}},
        "climatizacao": {"tipo": "galpao"},
        "hidraulica": {},
    }
    R = tk.rodar(spec)
    membros, disc = tk._membros_federados(R, spec)
    clash = tk.checa_interferencia_federada(R, spec)
    svg = coordenacao_svg(membros, clash)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    for termo in ("COORDENACAO", "PLANTA", "ELEVACAO", "DISCIPLINAS",
                  "RESUMO DE CLASH", "Membros:"):
        assert termo in svg, termo
    # so desenha disciplinas presentes; ao menos eletrico/incendio/hidraulica aparecem
    assert "Hidraulica" in svg and "Incendio" in svg
    # sem membros -> SVG de aviso (nao quebra)
    assert "sem geometria federada" in coordenacao_svg([], None)
    print("desenho_coordenacao self-test PASSED")


if __name__ == "__main__":
    _selftest()
