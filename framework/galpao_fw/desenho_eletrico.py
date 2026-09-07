# ============================================================================
# desenho_eletrico.py - O QUE ESTE SCRIPT FAZ / DESENHA
# Gera o DIAGRAMA UNIFILAR e o QUADRO DE CARGAS do projeto eletrico em SVG puro-
# Python (autocontido, sem FreeCAD/TechDraw) - a camada grafica do executivo
# eletrico, sobre o resultado de galpao_eletrico.rodar(). O unifilar e o desenho-
# assinatura do projeto eletrico (esquema, nao vista do 3D): entrada em MT ->
# transformador -> QGF (disjuntor geral + DPS) -> circuitos (motores, iluminacao,
# tomadas, banco de capacitores), com o simbolo de aterramento/SPDA. Simbologia
# conforme a pratica ABNT (NBR 5444/IEC). O SVG abre em qualquer navegador/CAD.
# ============================================================================
"""Diagrama unifilar + quadro de cargas do projeto eletrico em SVG puro-Python
(sem FreeCAD), a partir de galpao_eletrico.rodar()."""

from __future__ import annotations


# As primitivas (escape XML + simbologia) vivem em desenho_svg_base para serem
# compartilhadas com a camada residencial; os aliases privados abaixo preservam
# os nomes historicos deste modulo. UMA implementacao de _esc, nao duas.
from desenho_svg_base import (  # noqa: E402
    esc as _esc,
    linha as _line,
    sym_capacitor as _sym_capacitor,
    sym_disjuntor as _sym_disjuntor,
    sym_dps as _sym_dps,
    sym_lampada as _sym_lampada,
    sym_motor as _sym_motor,
    sym_terra as _sym_terra,
    sym_tomada as _sym_tomada,
    sym_trafo as _sym_trafo,
    texto as _t,
)


def diagrama_unifilar_svg(r):
    """Diagrama unifilar do projeto eletrico a partir de r=rodar(). String SVG."""
    g = r["gates"]
    W, Hh = 940, 640
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" '
         f'viewBox="0 0 {W} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         _t(W / 2, 34, "DIAGRAMA UNIFILAR GERAL", 20, weight="bold")]
    xg = 120                                            # coluna da entrada/trafo
    y = 70
    # entrada MT + transformador (se subestacao)
    if g["subestacao"]["necessaria"]:
        s.append(_t(xg, y, "ENTRADA %g kV" % (r["subestacao"]["V_primaria_kV"]), 13))
        s.append(_line(xg, y + 8, xg, y + 40))
        s.append(_sym_disjuntor(xg, y + 55))            # protecao geral MT
        s.append(_t(xg + 70, y + 60, r["subestacao"]["protecao"]["tipo"].replace("_", " "), 11, "start"))
        s.append(_line(xg, y + 64, xg, y + 92))
        s.append(_sym_trafo(xg, y + 112))
        s.append(_t(xg + 55, y + 108, "TR1  %g kVA" % r["subestacao"]["Sn_kVA"], 13, "start", "bold"))
        s.append(_t(xg + 55, y + 126, "%g/%g kV  z=%s%%" % (
            r["subestacao"]["V_primaria_kV"], r["subestacao"]["V_secundaria_V"] / 1000.0,
            r["subestacao"]["z_pct"]), 11, "start"))
        y = y + 150
    else:
        s.append(_t(xg, y, "ENTRADA BT (rede publica)", 13))
        y = y + 30
    s.append(_line(xg, y, xg, y + 30))
    # disjuntor geral (na linha) + DPS (ramo a direita, aterrado)
    s.append(_sym_disjuntor(xg, y + 45))
    s.append(_t(xg + 22, y + 41, "DISJ. GERAL %s A" % g["protecao"]["IN_geral_A"], 12, "start", "bold"))
    s.append(_line(xg, y + 45, xg + 215, y + 45, 1.0))
    s.append(_sym_dps(xg + 225, y + 45))
    s.append(_t(xg + 225, y + 72, "DPS cl. %s" % g["protecao"]["dps_classe"], 10, "middle"))
    s.append(_sym_terra(xg + 225, y + 84))
    s.append(_line(xg, y + 54, xg, y + 78))
    ybus = y + 90
    # barramento do QGF
    xb0, xb1 = 90, W - 110
    s.append(_line(xb0, ybus, xb1, ybus, 5.0))
    s.append(_t(xb0, ybus - 12, "QGF - %g V" % r["spec"]["tensao_V"], 14, "start", "bold"))
    if g["curto"]["Icc_kA"]:
        s.append(_t(W / 2, ybus - 12, "Icc presumida = %g kA" % g["curto"]["Icc_kA"],
                    11, "middle", color="#a00"))
    s.append(_t(xb1, ybus - 12, "alimentador %s mm2" % g["alimentador"]["secao_mm2"], 11, "end"))

    # circuitos derivados do barramento
    circuitos = []
    for grp in r["cargas"]["por_grupo"]:
        circuitos.append(grp)
    # simbolo por grupo
    simbolos = {"motores": _sym_motor, "iluminacao": _sym_lampada,
                "tomadas": _sym_tomada}
    xs = [x for x in range(220, xb1 - 40, 150)]
    yfim = ybus + 120
    for i, grp in enumerate(circuitos):
        x = xs[i] if i < len(xs) else xs[-1] + 150 * (i - len(xs) + 1)
        s.append(_line(x, ybus, x, ybus + 25))
        s.append(_sym_disjuntor(x, ybus + 40))          # disjuntor do circuito
        s.append(_line(x, ybus + 49, x, ybus + 72))
        sym = simbolos.get(grp, _sym_lampada)
        s.append(sym(x, yfim))
        d = r["cargas"]["por_grupo"][grp]
        s.append(_t(x, yfim + 32, grp, 11))
        s.append(_t(x, yfim + 46, "%.0f kW" % d["D_kW"], 10, color="#555"))
    # banco de capacitores (se necessario)
    if g["fator_potencia"]["precisa_corrigir"]:
        xc = (xs[len(circuitos)] if len(circuitos) < len(xs)
              else xb1 - 60)
        s.append(_line(xc, ybus, xc, ybus + 25))
        s.append(_sym_disjuntor(xc, ybus + 40))
        s.append(_line(xc, ybus + 49, xc, yfim - 6))
        s.append(_sym_capacitor(xc, yfim))
        s.append(_t(xc, yfim + 32, "BANCO CAP.", 11))
        s.append(_t(xc, yfim + 46, "%.0f kVAr" % g["fator_potencia"]["Qc_kVAr"], 10, color="#555"))

    # aterramento + SPDA (do lado esquerdo, descendo do barramento)
    yt = Hh - 70
    s.append(_line(xb0 + 10, ybus, xb0 + 10, yt - 12))
    s.append(_sym_terra(xb0 + 10, yt))
    at_txt = ("R = %g ohm" % g["aterramento"]["R_ohm"] if g["aterramento"]["R_ohm"]
              else "R <= 10 ohm (A CONFIRMAR)")
    s.append(_t(xb0 + 34, yt, "ATERRAMENTO  " + at_txt, 12, "start"))
    if g["spda"]["NP"]:
        s.append(_t(xb0 + 34, yt + 18, "SPDA NP %s - %s descidas (NBR 5419)" % (
            g["spda"]["NP"], g["spda"]["n_descidas"]), 11, "start"))
    s.append('</svg>')
    return "\n".join(s)


def quadro_cargas_svg(r):
    """Quadro de cargas do projeto (tabela) em SVG. String SVG."""
    g = r["gates"]
    linhas = [("CIRCUITO", "DEMANDA", "CONDUTOR", "PROTECAO")]
    linhas.append(("Alimentador geral (QGF)",
                   "%.0f kVA" % g["cargas"]["D_kVA"],
                   "%s mm2" % g["alimentador"]["secao_mm2"],
                   "%s A" % g["protecao"]["IN_geral_A"]))
    for grp, d in r["cargas"]["por_grupo"].items():
        linhas.append((grp, "%.1f kW / %.1f kVA" % (d["D_kW"], d["D_kVA"]), "-", "-"))
    if g["fator_potencia"]["precisa_corrigir"]:
        linhas.append(("Banco de capacitores",
                       "%.0f kVAr" % g["fator_potencia"]["Qc_kVAr"], "-", "-"))
    W = 720
    rh = 30
    Hh = rh * (len(linhas) + 1) + 40
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" '
         f'viewBox="0 0 {W} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         _t(W / 2, 26, "QUADRO DE CARGAS", 18, weight="bold")]
    cols = [20, 300, 470, 600, W - 20]
    y0 = 44
    for i, row in enumerate(linhas):
        y = y0 + i * rh
        fill = "#dfe7ef" if i == 0 else ("#f4f4f0" if i % 2 else "white")
        s.append(f'<rect x="20" y="{y:.0f}" width="{W - 40}" height="{rh}" '
                 f'fill="{fill}" stroke="#888" stroke-width="0.6"/>')
        for c, txt in enumerate(row):
            wt = "bold" if i == 0 else "normal"
            s.append(_t(cols[c] + 8, y + 20, str(txt), 12, "start", wt))
    s.append('</svg>')
    return "\n".join(s)


from desenho_svg_base import (  # noqa: E402
    PALETA_CIRCUITO as _PALETA_CIRC,
    sym_lampada_cor as _lampada_cor,
    sym_tomada_cor as _tomada_cor,
)


def planta_eletrica_svg(r):
    """PLANTA DE ILUMINACAO E TOMADAS (leiaute da instalacao eletrica) em SVG puro.
    Desenha, sobre o contorno do galpao: os PONTOS DE LUZ (grade da luminotecnica),
    as TOMADAS (TUG no perimetro), os interruptores e o QGF, coloridos e ligados por
    CIRCUITO (iluminacao e tomada SEPARADOS, NBR 5410 4.2.5.5). A partir de
    galpao_eletrico.rodar(r) + instalacao_eletrica.projeto_instalacao."""
    import instalacao_eletrica as ie
    inst = r.get("instalacao") or ie.projeto_instalacao(r)
    geo = r.get("geometria") or {}
    L = float(geo.get("L", 40.0)); W = float(geo.get("W", 20.0))
    Wc, Hh = 1180, 830
    ax0, ay0, aw, ah = 70, 110, 720, 470
    sc = min(aw / L, ah / W) if L > 0 and W > 0 else 1.0

    def px(xm):
        return ax0 + xm * sc

    def py(ym):
        return ay0 + (W - ym) * sc          # y=0 embaixo (flip para o SVG)

    # cor por circuito: cada ponto herda a cor do seu circuito
    cor_de = {}
    for i, c in enumerate(inst["circuitos"]["iluminacao"]):
        for pid in c["pontos"]:
            cor_de[pid] = _PALETA_CIRC[i % len(_PALETA_CIRC)]
    for i, c in enumerate(inst["circuitos"]["tomada"]):
        for pid in c["pontos"]:
            cor_de[pid] = _PALETA_CIRC[i % len(_PALETA_CIRC)]
    pos = {p["id"]: p for p in inst["luzes"] + inst["tomadas"]}

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wc}" height="{Hh}" '
         f'viewBox="0 0 {Wc} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{Wc}" height="{Hh}" fill="white"/>',
         _t(Wc / 2, 40, "PLANTA DE ILUMINACAO E TOMADAS", 20, weight="bold"),
         # contorno do galpao
         f'<rect x="{px(0):.0f}" y="{py(W):.0f}" width="{L * sc:.0f}" height="{W * sc:.0f}" '
         f'fill="#fafafa" stroke="#111" stroke-width="2"/>',
         _t(px(L / 2), py(0) + 26, "%.0f m" % L, 13),
         _t(px(0) - 26, py(W / 2), "%.0f m" % W, 13)]

    # roteamento dos circuitos (polilinha ligando os pontos na ordem, faint)
    for grupo in inst["circuitos"]["iluminacao"] + inst["circuitos"]["tomada"]:
        pids = [pid for pid in grupo["pontos"] if pid in pos]
        if len(pids) < 2:
            continue
        cor = cor_de.get(pids[0], "#888")
        pts = " ".join("%.0f,%.0f" % (px(pos[p]["x"]), py(pos[p]["y"])) for p in pids)
        s.append(f'<polyline points="{pts}" fill="none" stroke="{cor}" '
                 f'stroke-width="0.8" stroke-dasharray="4,3" opacity="0.55"/>')

    # QGF
    q = inst["quadro"]
    s.append(_sym_disjuntor(px(q["x"]), py(q["y"])))
    s.append(_t(px(q["x"]) + 16, py(q["y"]) + 4, "QGF", 11, anchor="start", weight="bold"))
    # pontos de luz
    for p in inst["luzes"]:
        s.append(_lampada_cor(px(p["x"]), py(p["y"]), cor_de.get(p["id"], "#111")))
    # tomadas
    for p in inst["tomadas"]:
        s.append(_tomada_cor(px(p["x"]), py(p["y"]), cor_de.get(p["id"], "#111")))
    # interruptores
    for p in inst["interruptores"]:
        s.append(f'<rect x="{px(p["x"]) - 7:.0f}" y="{py(p["y"]) - 7:.0f}" width="14" '
                 f'height="14" fill="white" stroke="#111" stroke-width="1.3"/>')
        s.append(_t(px(p["x"]), py(p["y"]) + 4, "S", 10, weight="bold"))

    # LEGENDA (direita)
    lx, ly = 900, 150
    s.append(f'<rect x="{lx - 20}" y="{ly - 30}" width="260" height="170" fill="white" '
             f'stroke="#111" stroke-width="1"/>')
    s.append(_t(lx + 110, ly - 8, "LEGENDA", 14, weight="bold"))
    s.append(_lampada_cor(lx, ly + 22, "#111")); s.append(_t(lx + 24, ly + 26, "Ponto de luz", 12, anchor="start"))
    s.append(_tomada_cor(lx, ly + 52, "#111")); s.append(_t(lx + 24, ly + 56, "Tomada (TUG)", 12, anchor="start"))
    s.append(f'<rect x="{lx - 7}" y="{ly + 75}" width="14" height="14" fill="white" stroke="#111" stroke-width="1.3"/>')
    s.append(_t(lx, ly + 86, "S", 10, weight="bold")); s.append(_t(lx + 24, ly + 90, "Interruptor", 12, anchor="start"))
    s.append(_sym_disjuntor(lx, ly + 116)); s.append(_t(lx + 24, ly + 120, "Quadro (QGF)", 12, anchor="start"))

    # RESUMO (direita, abaixo)
    q2 = inst["quantitativos"]
    rx, ry = 900, 360
    linhas = [
        "RESUMO", "",
        "Pontos de luz: %d" % q2["n_pontos_luz"],
        "Tomadas (TUG): %d" % q2["n_tomadas"],
        "Interruptores: %d" % q2["n_interruptores"],
        "Circuitos ilum.: %d" % q2["n_circuitos_ilum"],
        "Circuitos TUG: %d" % q2["n_circuitos_tug"],
        "Carga ilum.: %.0f VA" % q2["carga_ilum_va"],
        "Carga TUG: %.0f VA" % q2["carga_tug_va"],
        "", "Ilum. e TUG em circuitos",
        "SEPARADOS (NBR 5410 4.2.5.5)",
    ]
    s.append(f'<rect x="{rx - 20}" y="{ry - 24}" width="260" height="230" fill="white" '
             f'stroke="#111" stroke-width="1"/>')
    for i, ln in enumerate(linhas):
        s.append(_t(rx + (110 if i == 0 else 0), ry + i * 17, ln,
                    13 if i == 0 else 11, anchor="middle" if i == 0 else "start",
                    weight="bold" if i == 0 else "normal"))

    # FAIXA DE CIRCUITOS (bitola + eletroduto por circuito) - QDC resumido, ao pe da planta
    qdc = inst.get("qdc") or []
    ty = py(0) + 72
    s.append(_t(px(0), ty - 16, "CIRCUITOS - BITOLA E ELETRODUTO (QDC)", 12,
                anchor="start", weight="bold"))
    colx = [px(0), px(0) + 150, px(0) + 250, px(0) + 350, px(0) + 470]
    for cx, h in zip(colx, ["CIRCUITO", "PONTOS", "SECAO", "DISJUNTOR", "ELETRODUTO"]):
        s.append(_t(cx, ty, h, 10, anchor="start", weight="bold", color="#555"))
    todos_circ = inst["circuitos"]["iluminacao"] + inst["circuitos"]["tomada"]
    for i, d in enumerate(qdc):
        yy = ty + 18 + i * 15
        # cor do circuito (mesma da planta): 1o ponto do circuito correspondente
        cor = "#111"
        if i < len(todos_circ) and todos_circ[i]["pontos"]:
            cor = cor_de.get(todos_circ[i]["pontos"][0], "#111")
        vals = [d["circuito"], "%d" % d["n_pontos"], "%s mm2" % d["secao_mm2"],
                "%s A" % d["disjuntor_A"], "ø%s mm" % d["eletroduto_mm"]]
        for j, (cx, v) in enumerate(zip(colx, vals)):
            s.append(_t(cx, yy, v, 10, anchor="start", color=cor if j == 0 else "#111"))
    s.append('</svg>')
    return "\n".join(s)


def gerar_planta_eletrica(r, path):
    """Escreve a planta de iluminacao e tomadas SVG em `path`. Retorna o path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(planta_eletrica_svg(r))
    return path


def gerar_unifilar(r, path):
    """Escreve o diagrama unifilar SVG em `path`. Retorna o path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(diagrama_unifilar_svg(r))
    return path


def gerar_quadro_cargas(r, path):
    """Escreve o quadro de cargas SVG em `path`. Retorna o path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(quadro_cargas_svg(r))
    return path


# ---------------------------------------------------------------------------
# PRANCHAS DO EDIFICIO (G56) - parametros sobre o mesmo par de primitivas
# ---------------------------------------------------------------------------
# Os emissores acima nasceram para o galpao (um pavimento, um retangulo). O
# predio e' N pavimentos empilhados com UMA PRUMADA que os alimenta: a planta
# de instalacao sai por pavimento (pavimento-tipo declarado) e o unifilar vira
# o diagrama vertical da prumada. Onde a forma do dado diverge, a saida e'
# PARAMETRO (pavimento, rede), nao um desenho_eletrico_edificio.py paralelo.

def _edificio_C_L(estrutura):
    """Envelope do pavimento-tipo (m): soma dos vaos x largura."""
    pav = (estrutura or {}).get("pavimento") or {}
    try:
        C = float(sum(pav["vaos_x"]))
        L = float(sum(pav["vaos_y"]))
    except Exception:
        C, L = 14.0, 9.0
    return C, L


def _edificio_pavimentos(estrutura, n_servidos):
    """Nomes dos pavimentos servidos, do mais baixo ao mais alto (base->topo).

    A estrutura guarda topo->base; a prumada sobe da entrada (base) ao quadro
    mais alto. Sem nomes, QD-1..QD-N."""
    pals = ((estrutura or {}).get("pavimentos")
            if isinstance(estrutura, dict) else None) or []
    nomes = [p.get("nome") for p in pals if isinstance(p, dict) and p.get("nome")]
    if len(nomes) >= n_servidos:
        nomes = nomes[-n_servidos:]
    else:
        nomes = (["PAV-%d" % i for i in range(1, n_servidos + 1 - len(nomes))]
                 + nomes)
    return nomes


def diagrama_prumada_edificio_svg(ele, estrutura, titulo=None):
    """PE-EL-01 Unifilar: diagrama vertical entrada -> prumada -> QDs.

    Um QD por pavimento SERVIDO (drawing-vs-data: len == pavimentos_servidos),
    com a secao da prumada e o disjuntor geral rotulados do calculo."""
    n = int(ele.get("pavimentos_servidos") or 0)
    if n < 1:
        raise ValueError("eletrica sem pavimentos servidos: nada a desenhar")
    pru = ele.get("prumada") or {}
    qua = ele.get("quadro_de_pavimento") or {}
    ent = ele.get("entrada") or {}
    nomes = _edificio_pavimentos(estrutura, n)
    W, Hh = 900, max(420, 120 + n * 62)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" '
         f'viewBox="0 0 {W} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         _t(W / 2, 34, titulo or "UNIFILAR - PRUMADA DO EDIFICIO", 19, weight="bold")]
    x = 200
    y_base = Hh - 60
    y_topo = 110
    faixa0, faixa1 = y_topo + 60, y_base - 100
    s.append(_t(x, y_base + 30, "ENTRADA %s" % (ent.get("origem") or "rede_publica",), 12))
    prot = (ent.get("protecao") or {})
    disj = (prot.get("disjuntor") or {})
    if disj.get("IN"):
        s.append(_t(x + 130, y_base + 4, "GERAL %s A" % disj["IN"], 11, "start", "bold"))
    s.append(_sym_disjuntor(x, y_base - 12))
    s.append(_line(x, faixa1 + 10, x, y_base - 21))
    s.append(_line(x, y_topo + 44, x, faixa1 + 10, 3.0))
    for i in range(n):
        y = faixa1 - (faixa1 - faixa0) * (i + 0.5) / n
        s.append(_line(x, y, x + 130, y, 1.0))
        s.append(_sym_disjuntor(x + 145, y))
        s.append(_t(x + 170, y + 4, "QD-%d %s" % (i + 1, nomes[i]), 11, "start"))
    s.append(_t(x + 170, y_base - 52, "PRUMADA %s mm2" % pru.get("secao_mm2", "?"),
               12, "start", "bold"))
    s.append(_t(x + 170, y_base - 32, "QD %s mm2 / %s A" % (
        (qua.get("condutor") or {}).get("secao_mm2", "?"),
        ((qua.get("protecao") or {}).get("disjuntor") or {}).get("IN", "?")),
               11, "start", color="#555"))
    s.append(_t(W - 180, Hh - 24, "CARGA TOTAL %.0f VA" % ent.get("carga_total_VA", 0),
               11, color="#555"))
    s.append('</svg>')
    return "\n".join(s)


def planta_eletrica_pavimento_svg(ele, estrutura, pavimento=None):
    """PE-EL-02 Planta de instalacao do pavimento-tipo: contorno + shaft com a
    prumada, eletrocalha atravessando o comprimento e o QDP do pavimento."""
    C, L = _edificio_C_L(estrutura)
    qua = ele.get("quadro_de_pavimento") or {}
    Wc, Hh = 1000, 640
    ax0, ay0, aw, ah = 60, 80, 620, 440
    sc = min(aw / C, ah / L)

    def px(xm):
        return ax0 + xm * sc

    def py(ym):
        return ay0 + (L - ym) * sc

    rot = pavimento or "PAVIMENTO-TIPO"
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wc}" height="{Hh}" '
         f'viewBox="0 0 {Wc} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{Wc}" height="{Hh}" fill="white"/>',
         _t(Wc / 2, 34, "ELETRICA - PLANTA %s" % rot.upper(), 19, weight="bold"),
         f'<rect x="{px(0):.0f}" y="{py(L):.0f}" width="{C * sc:.0f}" height="{L * sc:.0f}" '
         f'fill="#fafafa" stroke="#111" stroke-width="2"/>',
         _t(px(C / 2), py(0) + 26, "%.1f m" % C, 12),
         _t(px(0) - 30, py(L / 2), "%.1f m" % L, 12)]
    # shaft convencional no canto (o mesmo do federado G53) + eletrocalha
    sx, sy = px(1.0), py(L - 1.0)
    s.append(f'<rect x="{sx - 8:.0f}" y="{sy - 8:.0f}" width="16" height="16" '
             f'fill="white" stroke="#111" stroke-width="1.5"/>')
    s.append(_t(sx + 22, sy + 4, "SHAFT/PRUMADA", 11, "start"))
    s.append(_line(px(0), sy, px(C), sy, 2.0, "#b45309"))
    s.append(_t(px(C / 2), sy - 10, "eletrocalha 100x50 por pavimento", 11, color="#b45309"))
    qx, qy = px(C - 2.0), py(1.0)
    s.append(_sym_disjuntor(qx, qy))
    s.append(_t(qx + 20, qy + 4, "QDP %s mm2" % (qua.get("condutor") or {}).get("secao_mm2", "?"),
               11, "start", "bold"))
    lx, ly = 730, 110
    s.append(f'<rect x="{lx}" y="{ly}" width="230" height="150" fill="white" '
             f'stroke="#111" stroke-width="1"/>')
    s.append(_t(lx + 115, ly + 24, "LEGENDA", 14, weight="bold"))
    s.append(_t(lx + 14, ly + 52, "QDP: quadro do pavimento", 11, "start"))
    s.append(_t(lx + 14, ly + 76, "prumada no shaft (1 m do canto)", 11, "start"))
    s.append(_t(lx + 14, ly + 100, "unidades/pav: %s" % ele.get("unidades_por_pavimento", "?"),
               11, "start"))
    s.append(_t(lx + 14, ly + 124, "carga comum: %.0f VA" % (ele.get("carga_areas_comuns_VA") or 0),
               11, "start"))
    s.append('</svg>')
    return "\n".join(s)


def infra_aterramento_edificio_svg(ele, estrutura, titulo=None):
    """PE-EL-03 Infraestrutura: corte vertical do shaft (prumada + calhas por
    pavimento) descendo ao eletrodo de aterramento."""
    n = int(ele.get("pavimentos_servidos") or 0)
    if n < 1:
        raise ValueError("eletrica sem pavimentos servidos: nada a desenhar")
    pru = ele.get("prumada") or {}
    W, Hh = 900, max(440, 140 + n * 62)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" '
         f'viewBox="0 0 {W} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         _t(W / 2, 34, titulo or "INFRAESTRUTURA - PRUMADA E ATERRAMENTO", 19, weight="bold")]
    x = 250
    y_base = Hh - 110
    y_topo = 110
    passo = (y_base - y_topo) / n
    s.append(_line(x - 60, y_topo - 20, x + 60, y_topo - 20, 4.0, "#6b7280"))
    s.append(_t(x, y_topo - 32, "COBERTURA", 11, color="#555"))
    for i in range(n):
        y = y_base - passo * (i + 0.5)
        s.append(_line(x - 60, y, x + 60, y, 1.2, "#9ca3af", dash="6 4"))
        s.append(_line(x, y, x + 200, y, 2.0, "#b45309"))
        s.append(_t(x + 210, y + 4, "calha N%d" % (i + 1), 10, "start", color="#555"))
    s.append(_line(x, y_topo - 20, x, y_base + 40, 3.0, "#111"))
    s.append(_t(x + 16, (y_topo + y_base) / 2, "PRUMADA %s mm2" % pru.get("secao_mm2", "?"),
               12, "start", "bold"))
    s.append(_line(x, y_base + 40, x, y_base + 70, 2.0))
    s.append(_sym_terra(x, y_base + 82))
    s.append(_t(x + 30, y_base + 86, "ATERRAMENTO (A CONFIRMAR)", 12, "start"))
    s.append('</svg>')
    return "\n".join(s)


def qdc_edificio_svg(ele, estrutura, titulo=None):
    """PE-EL-04 Quadros/QDC: uma linha por QD (pavimento servido) com secao e
    protecao do quadro calculado + a protecao geral da entrada."""
    n = int(ele.get("pavimentos_servidos") or 0)
    if n < 1:
        raise ValueError("eletrica sem pavimentos servidos: nada a desenhar")
    qua = ele.get("quadro_de_pavimento") or {}
    ent = ele.get("entrada") or {}
    nomes = _edificio_pavimentos(estrutura, n)
    disj_q = ((qua.get("protecao") or {}).get("disjuntor") or {}).get("IN", "?")
    secao_q = (qua.get("condutor") or {}).get("secao_mm2", "?")
    W = 860
    rh = 30
    Hh = rh * (n + 2) + 130
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}" '
         f'viewBox="0 0 {W} {Hh}" font-family="Arial">',
         f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="white"/>',
         _t(W / 2, 34, titulo or "QDC - QUADROS POR PAVIMENTO", 19, weight="bold")]
    y0 = 70
    s.append(f'<rect x="40" y="{y0}" width="{W - 80}" height="{rh}" '
             f'fill="#dfe7ef" stroke="#888" stroke-width="0.6"/>')
    s.append(_t(60, y0 + 20, "QUADRO / PAVIMENTO - SECAO - DISJUNTOR", 12, "start", "bold"))
    for i in range(n):
        y = y0 + (i + 1) * rh
        fill = "#f4f4f0" if i % 2 else "white"
        s.append(f'<rect x="40" y="{y}" width="{W - 80}" height="{rh}" '
                 f'fill="{fill}" stroke="#888" stroke-width="0.6"/>')
        s.append(_t(60, y + 20, "QD-%d %s - %s mm2 - %s A" % (i + 1, nomes[i], secao_q, disj_q),
                   11, "start"))
    prot = (ent.get("protecao") or {})
    disj_g = (prot.get("disjuntor") or {}).get("IN", "?")
    s.append(_t(60, y0 + (n + 2) * rh + 16, "GERAL DA ENTRADA: %s A - %.0f VA" % (
        disj_g, ent.get("carga_total_VA", 0)), 12, "start", "bold"))
    s.append('</svg>')
    return "\n".join(s)


def gerar_prumada_edificio(ele, estrutura, path, titulo=None):
    """Escreve o unifilar da prumada (PE-EL-01) em `path`."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(diagrama_prumada_edificio_svg(ele, estrutura, titulo))
    return path


def gerar_planta_pavimento_edificio(ele, estrutura, path, pavimento=None):
    """Escreve a planta de instalacao do pavimento-tipo (PE-EL-02)."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(planta_eletrica_pavimento_svg(ele, estrutura, pavimento))
    return path


def gerar_infra_edificio(ele, estrutura, path, titulo=None):
    """Escreve a infra/aterramento (PE-EL-03) em `path`."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(infra_aterramento_edificio_svg(ele, estrutura, titulo))
    return path


def gerar_qdc_edificio(ele, estrutura, path, titulo=None):
    """Escreve o QDC por pavimento (PE-EL-04) em `path`."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(qdc_edificio_svg(ele, estrutura, titulo))
    return path


def _selftest():
    import galpao_eletrico as ge
    spec = {"tensao_V": 380.0, "sistema": "trifasico", "origem": "subestacao_propria",
            "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2}],
                       "iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
            "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR", "temp_amb": 40.0},
            "transformador": {"Sn_kVA": 300.0, "z_pct": 4.5},
            "geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "spda": {"NP": "III", "Ng": 5.0, "R1": 2e-5},
            "aterramento": {"tipo": "malha", "rho": 100.0, "A": 800.0, "L_cond": 400.0}}
    r = ge.rodar(spec)
    uni = diagrama_unifilar_svg(r)
    assert uni.startswith("<svg") and uni.rstrip().endswith("</svg>")
    for token in ("DIAGRAMA UNIFILAR", "QGF", "TR1", "DISJ. GERAL", "ATERRAMENTO", "SPDA NP III"):
        assert token in uni, token
    qc = quadro_cargas_svg(r)
    assert "QUADRO DE CARGAS" in qc and "Alimentador geral" in qc
    print("desenho_eletrico self-test PASSED (unifilar + quadro de cargas SVG)")


if __name__ == "__main__":
    _selftest()
