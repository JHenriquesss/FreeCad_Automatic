# ============================================================================
# desenho_pavimento.py - O QUE ESTE SCRIPT FAZ / DESENHA
# PLANTA DE FORMAS do pavimento-tipo (G3, edificio multipavimento): a malha em
# escala, com pilares, vigas, paineis de laje, cotas dos vaos, o caso de vinculacao
# de cada painel e o quadro da carga que chega a cada pilar.
#
# Por que este modulo existe: a barra verde nao cobre o artefato final. O historico
# do projeto tem tres achados que so apareceram ao ABRIR o desenho (quadro de
# materiais sumindo em silencio, SVG XML-malformado, faixa de armadura tapando a
# malha inteira). Uma planta de formas cujo desenho nao corresponda a malha que foi
# calculada e o mesmo tipo de erro - e nao ha teste de numero que o pegue.
#
# CONFERENCIAS EMBUTIDAS (drawing-vs-data, o padrao que pegou a grade da planta de
# incendio desenhando cols*rows != N):
#   - o numero de pilares DESENHADOS tem de ser igual ao numero de pilares da
#     descida de cargas (nao (nx+1)*(ny+1) recalculado aqui);
#   - o numero de paineis desenhados tem de ser igual ao numero de paineis;
#   - todo texto passa por `desenho_svg_base.esc` (o SVG e XML).
# `confere_desenho` devolve essas contagens para o teste comparar.
#
# Unidades de entrada: m. Saida: SVG (string ou arquivo).
# ============================================================================
"""Planta de formas do pavimento-tipo: malha, pilares, vigas, paineis de laje,
cotas e o quadro de cargas por pilar. Reusa as primitivas de desenho_svg_base."""

from __future__ import annotations

import desenho_svg_base as sb

COR_PILAR = "#333"
COR_VIGA = "#1f6feb"
COR_LAJE = "#eef2f7"
COR_COTA = "#666"
COR_ENGASTE = "#c22"


def _escala(vaos_x, vaos_y, larg_util, alt_util):
    """Escala (px/m) que faz a malha caber na area util, mantendo a proporcao."""
    lx, ly = sum(vaos_x), sum(vaos_y)
    return min(larg_util / lx, alt_util / ly)


def planta_formas_svg(pav, descida=None, titulo=None):
    """Monta a planta de formas.

    pav     : dict devolvido por `pavimento_tipo.monta`.
    descida : (opc) dict de `descida_cargas.descer` - se dado, o quadro mostra o
              N acumulado na BASE de cada pilar em vez do N do pavimento.
    """
    vaos_x, vaos_y = pav["vaos_x"], pav["vaos_y"]
    nx, ny = len(vaos_x), len(vaos_y)

    W, H = 1180, 760
    MX, MY = 90, 90                      # margens do desenho
    LARG_QUADRO = 300
    larg_util = W - MX - LARG_QUADRO - 40
    alt_util = H - MY - 90
    esc = _escala(vaos_x, vaos_y, larg_util, alt_util)

    # coordenadas acumuladas das linhas da malha, em px
    xs = [MX]
    for v in vaos_x:
        xs.append(xs[-1] + v * esc)
    ys = [MY]
    for v in vaos_y:
        ys.append(ys[-1] + v * esc)
    # o eixo Y do SVG cresce para baixo; a planta e desenhada com Y crescendo para
    # CIMA, entao a linha j da malha fica em ys_inv[j].
    y_top, y_bot = ys[0], ys[-1]
    ys_inv = [y_bot - (y - y_top) for y in ys]

    tit = titulo or ("PLANTA DE FORMAS - PAVIMENTO-TIPO  (%d x %d vaos ; %.1f m2)"
                     % (nx, ny, pav["area_m2"]))
    P = sb.abre_svg(W, H, tit)

    # --- paineis de laje ---------------------------------------------------
    n_paineis_desenhados = 0
    por_ij = {(p["i"], p["j"]): p for p in pav["paineis"]}
    for i in range(nx):
        for j in range(ny):
            p = por_ij[(i, j)]
            x0, x1 = xs[i], xs[i + 1]
            y0, y1 = ys_inv[j + 1], ys_inv[j]        # y0 = topo do retangulo
            P.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" '
                     f'height="{y1 - y0:.1f}" fill="{COR_LAJE}" stroke="#c9d4e0" '
                     f'stroke-width="1"/>')
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            P.append(sb.texto(cx, cy - 4, "L%d%d" % (i + 1, j + 1), 13, weight="bold"))
            P.append(sb.texto(cx, cy + 13, "caso %d" % p["caso"], 11, color="#555"))
            P.append(sb.texto(cx, cy + 28, "%.2f x %.2f" % (p["lx"], p["ly"]), 10,
                              color="#777"))
            # marca as bordas continuas (engastadas) com traco vermelho interno
            e = p["engastes"]
            d = 5.0
            if e["esq"]:
                P.append(sb.linha(x0 + d, y0 + d, x0 + d, y1 - d, 2.0, COR_ENGASTE))
            if e["dir"]:
                P.append(sb.linha(x1 - d, y0 + d, x1 - d, y1 - d, 2.0, COR_ENGASTE))
            if e["inf"]:
                P.append(sb.linha(x0 + d, y1 - d, x1 - d, y1 - d, 2.0, COR_ENGASTE))
            if e["sup"]:
                P.append(sb.linha(x0 + d, y0 + d, x1 - d, y0 + d, 2.0, COR_ENGASTE))
            n_paineis_desenhados += 1

    # --- vigas (linhas da malha) -------------------------------------------
    n_vigas_desenhadas = 0
    for j in range(ny + 1):
        P.append(sb.linha(xs[0], ys_inv[j], xs[-1], ys_inv[j], 4.0, COR_VIGA))
        P.append(sb.texto(xs[0] - 32, ys_inv[j] + 4, "VX%d" % j, 10, anchor="middle",
                          color=COR_VIGA))
        n_vigas_desenhadas += 1
    for i in range(nx + 1):
        P.append(sb.linha(xs[i], ys_inv[0], xs[i], ys_inv[-1], 4.0, COR_VIGA))
        P.append(sb.texto(xs[i], ys_inv[-1] - 30, "VY%d" % i, 10, color=COR_VIGA))
        n_vigas_desenhadas += 1

    # --- pilares: um por PILAR DA LISTA (nao recalculado da malha) ---------
    lado = 16.0
    n_pilares_desenhados = 0
    for p in pav["pilares"]:
        i, j = p["i"], p["j"]
        cx, cy = xs[i], ys_inv[j]
        P.append(f'<rect x="{cx - lado / 2:.1f}" y="{cy - lado / 2:.1f}" '
                 f'width="{lado:.1f}" height="{lado:.1f}" fill="{COR_PILAR}"/>')
        # O rotulo da ULTIMA coluna vai para a ESQUERDA do pilar: ancorado a direita
        # ele avanca sobre o quadro de cargas e sai cortado. Isso nao aparece em
        # nenhuma contagem nem em nenhum assert de substring - so ABRINDO o PNG (ou
        # no teste geometrico de colisao, que reproduz a caixa do texto).
        ultima_coluna = (i == nx)
        if ultima_coluna:
            tx, anchor = cx - 16, "end"
        else:
            tx, anchor = cx + 16, "start"
        P.append(sb.texto(tx, cy - 10, p["nome"], 10, anchor=anchor, weight="bold"))
        n_pilares_desenhados += 1

    # --- cotas dos vaos -----------------------------------------------------
    y_cota = ys_inv[0] + 34
    for i in range(nx):
        xm = (xs[i] + xs[i + 1]) / 2
        P.append(sb.linha(xs[i], y_cota, xs[i + 1], y_cota, 1.0, COR_COTA))
        P.append(sb.texto(xm, y_cota - 6, "%.2f" % vaos_x[i], 11, color=COR_COTA))
    x_cota = xs[0] - 56
    for j in range(ny):
        ym = (ys_inv[j] + ys_inv[j + 1]) / 2
        P.append(sb.linha(x_cota, ys_inv[j], x_cota, ys_inv[j + 1], 1.0, COR_COTA))
        P.append(sb.texto(x_cota - 4, ym + 4, "%.2f" % vaos_y[j], 11, anchor="end",
                          color=COR_COTA))

    # --- quadro de cargas ---------------------------------------------------
    qx = W - LARG_QUADRO - 20
    qy = MY - 20
    # a guarda geometrica contra invasao do quadro esta em colisoes_de_rotulo(),
    # exercitada pelo teste - aqui o desenho so precisa da posicao ja corrigida.
    P.append(f'<rect x="{qx}" y="{qy}" width="{LARG_QUADRO}" height="{H - qy - 40}" '
             f'fill="#fbfcfd" stroke="#c9d4e0" stroke-width="1"/>')
    if descida:
        cab = "CARGA NA BASE DO PILAR (kN)"
        linhas = [(n, descida["pilares"][n]["posicao"], descida["pilares"][n]["N_base_k"])
                  for n in sorted(descida["pilares"])]
    else:
        cab = "CARGA DO PAVIMENTO POR PILAR (kN)"
        linhas = [(p["nome"], p["posicao"], p["N_k"]) for p in pav["pilares"]]
    P.append(sb.texto(qx + LARG_QUADRO / 2, qy + 24, cab, 12, weight="bold"))
    P.append(sb.linha(qx + 12, qy + 34, qx + LARG_QUADRO - 12, qy + 34, 1.0, "#c9d4e0"))
    yy = qy + 54
    P.append(sb.texto(qx + 24, yy, "PILAR", 11, anchor="start", weight="bold"))
    P.append(sb.texto(qx + 110, yy, "POSICAO", 11, anchor="start", weight="bold"))
    P.append(sb.texto(qx + LARG_QUADRO - 20, yy, "N", 11, anchor="end", weight="bold"))
    yy += 8
    for nome, pos, N in linhas:
        yy += 19
        if yy > H - 70:
            P.append(sb.texto(qx + LARG_QUADRO / 2, yy, "... (%d pilares no total)"
                              % len(linhas), 10, color="#777"))
            break
        P.append(sb.texto(qx + 24, yy, nome, 11, anchor="start"))
        P.append(sb.texto(qx + 110, yy, pos, 11, anchor="start", color="#555"))
        P.append(sb.texto(qx + LARG_QUADRO - 20, yy, "%.1f" % N, 11, anchor="end"))

    # --- legenda / notas ----------------------------------------------------
    P.append(sb.texto(MX, H - 46,
                      "g = %.2f kN/m2 ; q = %.2f kN/m2 (NBR 6120 Tab.10)"
                      % (pav["g_kN_m2"], pav["q_kN_m2"]), 11, anchor="start",
                      color="#444"))
    P.append(sb.texto(MX, H - 28,
                      "traco vermelho = borda CONTINUA (engastada) ; "
                      "reacoes por 14.7.6.1 ; vigas por 14.6.6", 11, anchor="start",
                      color="#444"))
    P.append("</svg>")
    return "\n".join(P)


def caixas_de_rotulo(pav):
    """Caixas aproximadas dos rotulos de pilar e a do quadro de cargas, em px, para o
    TESTE GEOMETRICO de colisao de texto. Reproduz a mesma aritmetica do desenho.

    Um teste que so procura a string 'P41' no SVG passa mesmo com o rotulo desenhado
    por baixo do quadro: o texto esta la, so nao se ve. A colisao e geometrica, e tem
    de ser conferida como geometria."""
    vaos_x, vaos_y = pav["vaos_x"], pav["vaos_y"]
    nx, ny = len(vaos_x), len(vaos_y)
    W, H = 1180, 760
    MX, MY = 90, 90
    LARG_QUADRO = 300
    esc = _escala(vaos_x, vaos_y, W - MX - LARG_QUADRO - 40, H - MY - 90)
    xs = [MX]
    for v in vaos_x:
        xs.append(xs[-1] + v * esc)
    ys = [MY]
    for v in vaos_y:
        ys.append(ys[-1] + v * esc)
    ys_inv = [ys[-1] - (y - ys[0]) for y in ys]
    quadro = (W - LARG_QUADRO - 20, MY - 20, W - 20, H - 40)
    caixas = []
    for p in pav["pilares"]:
        cx, cy = xs[p["i"]], ys_inv[p["j"]]
        larg = len(p["nome"]) * 6.2
        if p["i"] == nx:
            x0, x1 = cx - 16 - larg, cx - 16
        else:
            x0, x1 = cx + 16, cx + 16 + larg
        caixas.append({"nome": p["nome"], "caixa": (x0, cy - 18, x1, cy - 2)})
    return {"quadro": quadro, "rotulos": caixas,
            "limites_desenho": (MX, MY, xs[-1], ys_inv[0])}


def colisoes_de_rotulo(pav):
    """Rotulos de pilar que invadem o quadro de cargas (deveria ser vazio)."""
    d = caixas_de_rotulo(pav)
    qx0, qy0, qx1, qy1 = d["quadro"]
    fora = []
    for r in d["rotulos"]:
        x0, y0, x1, y1 = r["caixa"]
        if x1 > qx0 and x0 < qx1 and y1 > qy0 and y0 < qy1:
            fora.append(r["nome"])
    return fora


def confere_desenho(pav):
    """Contagens que o desenho DEVE reproduzir (drawing-vs-data). O teste compara
    isto com o que foi efetivamente emitido, em vez de confiar que o laco desenhou
    tudo - foi um laco que desenhava cols*rows != N que produziu a grade errada da
    planta de incendio."""
    nx, ny = len(pav["vaos_x"]), len(pav["vaos_y"])
    return {"n_pilares": len(pav["pilares"]), "n_paineis": len(pav["paineis"]),
            "n_vigas": (ny + 1) + (nx + 1)}


def gerar_planta_formas(pav, path, descida=None, titulo=None):
    """Escreve a planta de formas (SVG) em `path`. Retorna o path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(planta_formas_svg(pav, descida, titulo))
    return path


# ---------------------------------------------------------------------------
# PRANCHA DE ARMACAO DE VIGAS (G34) - o executivo que faltava
# ---------------------------------------------------------------------------
def _arr_rotulo(arr):
    """Rotulo curto do arranjo: '2 f10.0' ou '-' quando sem barra."""
    if not isinstance(arr, dict) or not arr.get("n"):
        return "-"
    try:
        return "%d f%.1f" % (int(arr["n"]), float(arr["phi"]))
    except (TypeError, ValueError):
        return "-"


def prancha_armacao_vigas_svg(vigas_verificacao, titulo=None):
    """Prancha de armacao das vigas do pavimento-tipo (SVG puro-Python).

    Le `edificio_multipavimento.vigas_verificacao` (o `por_linha` de
    `estrutura_casa.verifica_vigas`): TODA viga, TODO tramo, com As de flexao
    M+/M-, cortante (estribo), ancoragem e ELS de flecha. Uma linha da tabela
    por tramo; a contagem desenhada tem de bater com `n_tramos` (drawing-vs-data,
    o mesmo padrao da planta de formas).
    """
    por_linha = (vigas_verificacao or {}).get("por_linha") or []
    n_tramos = int((vigas_verificacao or {}).get("n_tramos") or 0)
    linhas = []
    for linha in por_linha:
        for tramo in linha.get("tramos") or []:
            linhas.append((linha, tramo))
    W = 1420
    H = 170 + max(len(linhas), 1) * 22 + 110
    tit = titulo or ("ARMACAO DE VIGAS - PAVIMENTO-TIPO "
                     "(%d linhas / %d tramos VERIFICADOS)" % (len(por_linha), n_tramos))
    P = sb.abre_svg(W, H, tit)
    P.append(sb.texto(W / 2, 58,
                      "flexao M+/M- (17.2.2) + cortante (17.4.2) + ancoragem (9.4) + "
                      "flecha Tab.13.3 + fissuracao -- por tramo, da envoltoria 14.6.6",
                      11, color="#444"))
    # cabecalho
    cols = [("VIGA", 30), ("TR", 130), ("L(m)", 175), ("SECAO", 235),
            ("M+(kNm)", 330), ("M-(kNm)", 420), ("As_inf", 510), ("As_sup", 590),
            ("ARR INF", 670), ("ARR SUP", 780), ("ESTRIBO", 890),
            ("LB(mm)", 1020), ("FLECHA", 1090), ("OK", 1310)]
    y0 = 92
    for nome, x in cols:
        P.append(sb.texto(x, y0, nome, 11, anchor="start", weight="bold"))
    P.append(sb.linha(24, y0 + 8, W - 24, y0 + 8, 1.0, "#999"))
    yy = y0 + 28
    for linha, tramo in linhas:
        ver = tramo.get("verificacao") or {}
        els = tramo.get("els") or ver.get("els") or {}
        anc = ver.get("ancoragem") or {}
        sec = "%dx%d" % (round(float(linha.get("b", 0)) * 100),
                         round(float(linha.get("h", 0)) * 100))
        flecha = ("%.1f/%.1f" % (float(els.get("d_comparado_mm", 0)),
                                 float(els.get("lim_mm", 0)))
                  if els else "-")
        estribo = ("f%.1f c/%d" % (float(ver.get("phi_estribo_mm", 5.0)),
                                   round(float(ver.get("s_estribo_max", 0.2)) * 100))
                   if ver else "-")
        vals = [
            str(linha.get("nome", "")),
            str(tramo.get("tramo", "")),
            "%.2f" % float(tramo.get("L", 0)),
            sec,
            "%.1f" % float(tramo.get("M_d_kNm", 0)),
            "%.1f" % float(tramo.get("M_d_neg_envoltoria_kNm", 0)),
            "%.2f" % float(tramo.get("As_inf_cm2", 0)),
            "%.2f" % float(tramo.get("As_sup_cm2", 0)),
            _arr_rotulo(ver.get("arr_inf")),
            _arr_rotulo(ver.get("arr_sup")),
            estribo,
            "%d" % int(anc.get("lb_nec_mm", 0)) if anc else "-",
            flecha,
            "OK" if tramo.get("OK") else "REPROVA",
        ]
        for ( _nome, x), val in zip(cols, vals):
            cor = "#b91c1c" if (val == "REPROVA") else "#111"
            peso = "bold" if val in ("REPROVA",) else "normal"
            P.append(sb.texto(x, yy, val, 11, anchor="start", weight=peso,
                              color=cor))
        yy += 22
    P.append(sb.texto(30, yy + 18,
                      "As em cm2 ; M_d/M_d_neg de projeto (envelopes x 1,4) ; "
                      "LB = lb,nec com gancho (9.4) ; flecha comparada/limite Tab.13.3",
                      11, anchor="start", color="#444"))
    P.append(sb.texto(30, yy + 36,
                      "longitudinal (L+2*LB) + estribos contam no quantitativo "
                      "armadura_viga ; traspasses e perdas nao incluidos",
                      11, anchor="start", color="#444"))
    P.append(sb.texto(30, yy + 54,
                      "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
                      11, anchor="start", weight="bold", color="#444"))
    P.append("</svg>")
    return "\n".join(P)


def confere_armacao_vigas(vigas_verificacao, svg):
    """Drawing-vs-data da prancha de vigas: todo tramo tem de estar desenhado."""
    por_linha = (vigas_verificacao or {}).get("por_linha") or []
    nomes = []
    for linha in por_linha:
        for tramo in linha.get("tramos") or []:
            nomes.append("%s tramo %d" % (linha.get("nome"), tramo.get("tramo")))
    faltando = [n for n in nomes if n.split()[0] not in svg]
    return {"n_tramos": len(nomes), "faltando": faltando, "ok": not faltando}


def gerar_prancha_armacao_vigas(vigas_verificacao, path, titulo=None):
    """Escreve a prancha de armacao de vigas (SVG) em `path`. Retorna o path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(prancha_armacao_vigas_svg(vigas_verificacao, titulo))
    return path
