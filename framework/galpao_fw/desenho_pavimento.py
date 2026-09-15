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


def _sufixo_edicao(edicao=None):
    """Sufixo de edicao da NBR 6118 no titulo (G123/G125, auditoria do G123).

    G128: a edicao declarada no projeto chega aqui (casa e predio leem a
    chave; ausente = comportamento de hoje, 2014 declarado). O sufixo vem
    da fonte unica (sem literal).
    G132: a folha declara a edicao que a SUA conta usou (fonte unica
    edicao_da_peca): o desenho nao calcula nenhum dos 2 pontos de troca,
    entao declara 2014 com qualquer chave (a composicao mora no carimbo
    do projeto). Invalida continua levantando."""
    from edicao_nbr6118_g123 import edicao_da_peca, sufixo_folha_edicao
    return sufixo_folha_edicao(edicao_da_peca(edicao, False))

COR_PILAR = "#333"
COR_VIGA = "#1f6feb"
COR_LAJE = "#eef2f7"
COR_COTA = "#666"
COR_ENGASTE = "#c22"


def _escala(vaos_x, vaos_y, larg_util, alt_util):
    """Escala (px/m) que faz a malha caber na area util, mantendo a proporcao."""
    lx, ly = sum(vaos_x), sum(vaos_y)
    return min(larg_util / lx, alt_util / ly)


def planta_formas_svg(pav, descida=None, titulo=None, edicao=None,
                      ausencias=None):
    """Monta a planta de formas.

    pav     : dict devolvido por `pavimento_tipo.monta`.
    descida : (opc) dict de `descida_cargas.descer` - se dado, o quadro mostra o
              N acumulado na BASE de cada pilar em vez do N do pavimento.
    edicao  : (opc, G128) '2014' ou '2023+Em1' declarada no projeto; ausente =
              comportamento de hoje (2014) declarado no titulo.
    ausencias : (opc, G146) lista de campos que o calculo nao produz para
              esta folha - com a lista a folha desenha a mesma planta e
              declara a caixa vermelha; com None (default) o caminho do
              predio/casa sai byte-identico.
    """
    vaos_x, vaos_y = pav["vaos_x"], pav["vaos_y"]
    nx, ny = len(vaos_x), len(vaos_y)

    W, H = 1180, 760
    # G146: a caixa de ausencias mora na faixa extra abaixo da legenda - a
    # malha e a legenda nao se movem (o predio, com ausencias=None, nao muda
    # um byte).
    Hh = H + (48 + 20 * len(list(ausencias)) if ausencias else 0)
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
    tit += _sufixo_edicao(edicao)
    P = sb.abre_svg(W, Hh, tit)

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
    if ausencias:
        # G146: a caixa vermelha mora na faixa extra (H..Hh) - a legenda e a
        # malha ficam onde sempre estiveram.
        ax, ay = MX, H + 12
        alt = Hh - H - 20
        P.append(f'<rect x="{ax}" y="{ay}" width="{W - MX - 40}" height="{alt}" '
                 f'fill="white" stroke="{COR_ENGASTE}" stroke-width="1.5"/>')
        P.append(sb.texto(ax + (W - MX - 40) / 2, ay + 22,
                          "DADOS NAO DECLARADOS PELO CALCULO DO MEZANINO (G146)",
                          12, weight="bold", color=COR_ENGASTE))
        for k, campo in enumerate(list(ausencias)):
            P.append(sb.texto(ax + 14, ay + 44 + k * 20,
                              "nao declarado: %s" % campo, 11, anchor="start"))
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


def gerar_planta_formas(pav, path, descida=None, titulo=None, edicao=None):
    """Escreve a planta de formas (SVG) em `path`. Retorna o path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(planta_formas_svg(pav, descida, titulo, edicao=edicao))
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


#: colunas da tabela de vigas (x em px, mesma ordem dos valores da fileira).
_COLS_VIGAS = [("VIGA", 30), ("TR", 130), ("L(m)", 175), ("SECAO", 235),
               ("M+(kNm)", 330), ("M-(kNm)", 420), ("As_inf", 510),
               ("As_sup", 590), ("ARR INF", 670), ("ARR SUP", 780),
               ("ESTRIBO", 890), ("LB(mm)", 1020), ("FLECHA", 1090),
               ("OK", 1310)]

_SUBTITULO_VIGAS = ("flexao M+/M- (17.2.2) + cortante (17.4.2) + ancoragem (9.4) + "
                    "flecha Tab.13.3 + fissuracao -- por tramo, da envoltoria 14.6.6")


def _dados_vigas(vigas_verificacao):
    """Separa o `por_linha` em fileiras (linha, tramo) + contagens.

    Builder da secao de vigas (G110): o corpo da tabela saiu da
    `prancha_armacao_vigas_svg` para ser reusado pela combinada
    vigas+pilares sem duplicar a formatacao - a saida da prancha de
    vigas nao muda um byte (diff travado em teste manual antes/depois).
    """
    por_linha = (vigas_verificacao or {}).get("por_linha") or []
    n_tramos = int((vigas_verificacao or {}).get("n_tramos") or 0)
    linhas = []
    for linha in por_linha:
        for tramo in linha.get("tramos") or []:
            linhas.append((linha, tramo))
    return por_linha, n_tramos, linhas


def _vals_fileira_viga(linha, tramo):
    """Os 14 valores da fileira, na ordem de _COLS_VIGAS (formatacao da G34)."""
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
    return [
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


def _escreve_cabecalho_tabela(P, cols, y0, W):
    """Cabecalho em negrito + filete (mesma geometria das duas secoes)."""
    for nome, x in cols:
        P.append(sb.texto(x, y0, nome, 11, anchor="start", weight="bold"))
    P.append(sb.linha(24, y0 + 8, W - 24, y0 + 8, 1.0, "#999"))


def _escreve_fileira(P, cols, vals, yy):
    """Uma fileira da tabela (REPROVA em vermelho, o resto em #111)."""
    for (_nome, x), val in zip(cols, vals):
        cor = "#b91c1c" if (val == "REPROVA") else "#111"
        peso = "bold" if val in ("REPROVA",) else "normal"
        P.append(sb.texto(x, yy, val, 11, anchor="start", weight=peso,
                          color=cor))


def _rodape_armacao_vigas(P, yy, conceitual=True):
    """As tres linhas de rodape da secao de vigas (notas + CONCEITUAL/ART).

    Na combinada N:1 (G110) a secao de vigas sai com conceitual=False e o
    carimbo unico fecha a folha (olhar do G110: CONCEITUAL duplicado).
    """
    P.append(sb.texto(30, yy + 18,
                      "As em cm2 ; M_d/M_d_neg de projeto (envelopes x 1,4) ; "
                      "LB = lb,nec com gancho (9.4) ; flecha comparada/limite Tab.13.3",
                      11, anchor="start", color="#444"))
    P.append(sb.texto(30, yy + 36,
                      "longitudinal (L+2*LB) + estribos contam no quantitativo "
                      "armadura_viga ; traspasses e perdas nao incluidos",
                      11, anchor="start", color="#444"))
    if conceitual:
        P.append(sb.texto(30, yy + 54,
                          "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
                          11, anchor="start", weight="bold", color="#444"))


def prancha_armacao_vigas_svg(vigas_verificacao, titulo=None, edicao=None):
    """Prancha de armacao das vigas do pavimento-tipo (SVG puro-Python).

    Le `edificio_multipavimento.vigas_verificacao` (o `por_linha` de
    `estrutura_casa.verifica_vigas`): TODA viga, TODO tramo, com As de flexao
    M+/M-, cortante (estribo), ancoragem e ELS de flecha. Uma linha da tabela
    por tramo; a contagem desenhada tem de bater com `n_tramos` (drawing-vs-data,
    o mesmo padrao da planta de formas).
    """
    por_linha, n_tramos, linhas = _dados_vigas(vigas_verificacao)
    W = 1420
    H = 170 + max(len(linhas), 1) * 22 + 110
    tit = titulo or ("ARMACAO DE VIGAS - PAVIMENTO-TIPO "
                     "(%d linhas / %d tramos VERIFICADOS)" % (len(por_linha), n_tramos))
    tit += _sufixo_edicao(edicao)
    P = sb.abre_svg(W, H, tit)
    P.append(sb.texto(W / 2, 58, _SUBTITULO_VIGAS, 11, color="#444"))
    # cabecalho
    cols = _COLS_VIGAS
    y0 = 92
    _escreve_cabecalho_tabela(P, cols, y0, W)
    yy = y0 + 28
    for linha, tramo in linhas:
        _escreve_fileira(P, cols, _vals_fileira_viga(linha, tramo), yy)
        yy += 22
    _rodape_armacao_vigas(P, yy)
    P.append("</svg>")
    return "\n".join(P)


def confere_armacao_vigas(vigas_verificacao, svg):
    """Drawing-vs-data da prancha de vigas: todo TRAMO tem de estar desenhado.

    Triagem G69: o lado A e' o calculado (por_linha/tramos de
    estrutura_casa.verifica_vigas via edificio_multipavimento); o lado B e'
    o SVG emitido (prancha_armacao_vigas_svg escreve o nome da viga uma vez
    por linha de tramo). A versao anterior conferia so a presenca do NOME
    da viga (``n.split()[0] in svg``): faltando um tramo da mesma viga, a
    guarda passava — concordancia parcial consigo mesma. Agora confere a
    CONTAGEM por viga (ocorrencias do nome >= tramos da viga), relacao
    independente entre dado e desenho, nunca literal.
    """
    import re as _re
    por_linha = (vigas_verificacao or {}).get("por_linha") or []
    nomes = []
    esperado_por_viga = {}
    for linha in por_linha:
        viga = linha.get("nome")
        n_tr = len(linha.get("tramos") or [])
        if viga is not None and n_tr:
            esperado_por_viga[viga] = esperado_por_viga.get(viga, 0) + n_tr
        for tramo in linha.get("tramos") or []:
            nomes.append("%s tramo %d" % (viga, tramo.get("tramo")))
    faltando = []
    for viga, esperado in esperado_por_viga.items():
        achados = len(_re.findall(_re.escape(str(viga)) + r"(?![0-9])",
                                  svg or ""))
        if achados < esperado:
            faltando.append("%s: %d tramos calculados, %d desenhados"
                            % (viga, esperado, achados))
    return {"n_tramos": len(nomes), "faltando": faltando, "ok": not faltando}


def gerar_prancha_armacao_vigas(vigas_verificacao, path, titulo=None,
                                edicao=None):
    """Escreve a prancha de armacao de vigas (SVG) em `path`. Retorna o path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(prancha_armacao_vigas_svg(vigas_verificacao, titulo,
                                          edicao=edicao))
    return path


# ---------------------------------------------------------------------------
# QUADRO DE ARMACAO DE PILARES + COMBINADA VIGAS/PILARES (G110)
# ---------------------------------------------------------------------------
# Decisao N:1 (G110): o indice PE-CO-02 promete "Armacao pilares/vigas" nas
# duas tipologias de concreto e o arquivo da casa ja se chama
# "armacao-vigas-pilares-casa.svg" - a combinada empilha a secao de vigas
# (G34) e a secao de pilares abaixo, no MESMO <svg>. Sem arquivo novo, sem
# churn em mapas (pacote_legal._PRANCHA_ARQUIVO), indice, FOLHAS do G77 ou
# na lente varredura_indice_disco: o codigo PE-CO-02 passa a ser verdade
# no arquivo que ja o carregava no nome.
#
# O pilar e' lido do `pilar_continuo.dimensiona` (via edificio_multipavimento
# / estrutura_casa: dict por pilar com `lances` do topo a base): UMA fileira
# por TRECHO de lances iguais (G115: mesma secao e mesmo As; "lances 1-5:
# 19x30, As 2,28"). Pilar sem mudanca continua com uma fileira ("1-9").
# Os valores da fileira (secao, Nd, As, taxa, estribo, limite, arranjo) sao
# os do lance de BASE do trecho (o mais carregado). Tudo vem do dado - nada
# e' arbitrado: sem `phi_long_mm` declarada nao ha arranjo longitudinal
# honesto (a celula diz NAO DETALHADO em vez de inventar bitola).

#: subtitulo da secao de pilares: so itens VERIFICADOS em pilar_concreto.py
#: (15.8 esbeltez/2a ordem, 17.3.5.3 As min/max, 18.4.3 estribo/limite).
#: A edicao sai de _subtitulo_pilares (G128, fonte unica); a constante segue
#: como a renderizacao do parametro ausente (2014, hoje), que os testes
#: citam — ver _subtitulo_pilares.
_SUBTITULO_PILARES = ("pilares: esbeltez e 2a ordem (15.8) + As min/max (17.3.5.3) + "
                      "estribo e limite governante (18.4.3) -- NBR 6118:2014")


def _subtitulo_pilares(edicao=None):
    """Subtitulo da secao de pilares com a edicao declarada (G128).

    Ausente = o texto de sempre (2014, `_SUBTITULO_PILARES`, byte-identico);
    com a chave, o rotulo da fonte unica (sem literal aqui).
    G132: a folha declara a edicao que a SUA conta usou (sem troca: 2014
    com qualquer chave)."""
    if edicao is None:
        return _SUBTITULO_PILARES
    from edicao_nbr6118_g123 import edicao_da_peca, rotulo_edicao as _rot_ed
    return ("pilares: esbeltez e 2a ordem (15.8) + As min/max (17.3.5.3) + "
            "estribo e limite governante (18.4.3) -- %s"
            % _rot_ed(edicao_da_peca(edicao, False)))

#: declaracao de ausencia (pilares={} ou None): a secao declara em vez de
#: sair com a tabela vazia (folha vazia e' o bug irmao do G62).
_AUSENCIA_PILARES = ("pilares nao dimensionados nesta rodada "
                     "(estrutura.pilares ausente/vazio)")

#: celula do arranjo longitudinal quando a bitola nao foi declarada (G110).
_ARRANJO_NAO_DETALHADO = "NAO DETALHADO: phi_long_mm nao declarado"

_COLS_PILARES = [("PILAR", 30), ("SECAO", 120), ("LANCES", 250),
                 ("Nd(kN)", 330), ("As(cm2)", 420), ("TAXA(%)", 510),
                 ("ESTRIBO", 610), ("LIMITE GOVERNANTE", 790),
                 ("ARRANJO LONG.", 1050)]

#: base da altura dinamica da combinada: H = base + 22*(n_tramos + n_fileiras).
#: G115: n_fileiras = soma dos trechos (nao n_pilares); folha de altura fixa
#: com conteudo que cresce corta fileira (licao do G77).
_BASE_COMBINADA = 480


def _lance_base(pilar):
    """O lance de BASE (lances[-1]) ou None quando o pilar nao tem lances."""
    lances = (pilar or {}).get("lances") if isinstance(pilar, dict) else None
    if not lances:
        return None
    return lances[-1]


def _chave_trecho(lance):
    """Chave de igualdade do trecho (G115): mesma secao e mesmo As.

    `b`/`h` em m (comparados em cm arredondado, a precisao da folha) e
    `As_cm2` (arredondado a 2 casas, a precisao da celula). Nd, taxa,
    estribo e limite NAO entram: Nd sempre cresce ao descer e a fileira
    mostra o Nd de BASE do trecho; taxa/estribo/limite derivam da secao+As
    no dado medido (predio: identicos dentro do trecho).
    """
    try:
        b_cm = round(float(lance.get("b", 0)) * 100)
        h_cm = round(float(lance.get("h", 0)) * 100)
    except (TypeError, ValueError):
        b_cm, h_cm = 0, 0
    try:
        as_cm2 = round(float(lance.get("As_cm2", 0)), 2)
    except (TypeError, ValueError):
        as_cm2 = 0.0
    return (b_cm, h_cm, as_cm2)


def _trechos_pilar(pilar):
    """Agrupa os lances CONTIGUOS iguais em trechos (G115).

    Devolve [{"i_ini", "i_fim", "rotulo", "lances", "base"}]: indices 0-based
    do topo para a base, `rotulo` 1-based ("1-5" ou "6"), `base` o lance de
    BASE do trecho (o mais carregado, que assina a fileira). Pilar sem
    lances devolve []. Pilar sem mudanca devolve um trecho unico ("1-N").
    """
    lances = (pilar or {}).get("lances") if isinstance(pilar, dict) else None
    if not lances:
        return []
    trechos = []
    ini = 0
    for k in range(1, len(lances) + 1):
        if k < len(lances) and _chave_trecho(lances[k]) == _chave_trecho(lances[ini]):
            continue
        fim = k - 1
        if ini == fim:
            rotulo = "%d" % (ini + 1)
        else:
            rotulo = "%d-%d" % (ini + 1, fim + 1)
        trechos.append({"i_ini": ini, "i_fim": fim, "rotulo": rotulo,
                        "lances": lances[ini:k], "base": lances[fim]})
        ini = k
    return trechos


def _n_fileiras_pilares(pilares):
    """Total de fileiras da secao de pilares: soma dos trechos (G115).

    Pilar sem lances conta 0 (a secao declara a ausencia). Dict vazio/None
    conta 1 para a altura minima (a linha de declaracao).
    """
    if not isinstance(pilares, dict) or not pilares:
        return 1
    total = 0
    for nome in pilares:
        total += max(len(_trechos_pilar(pilares[nome])), 0)
    return max(total, 1)


def _estribo_pilar_rotulo(detalhe):
    """'f<phi> c/<s_cm> <n>R' (s em m no dado, cm na folha via round(s*100))."""
    det = detalhe if isinstance(detalhe, dict) else {}
    # G113: sem a chave a celula declara "-". Os padroes (5 mm, c/15, 2R) que
    # estavam aqui imprimiriam um estribo que ninguem calculou.
    try:
        phi = float(det["phi_estribo_mm"])
        s_cm = round(float(det["s_estribo"]) * 100)
        n_r = int(det["n_ramos_estribo"])
    except (KeyError, TypeError, ValueError):
        return "-"
    return "f%.1f c/%d %dR" % (phi, s_cm, n_r)


def _arranjo_long_rotulo(detalhe):
    """Arranjo longitudinal: nunca arbitrar `phi_long_mm`.

    A 18.4.3 so limita por 12.phi_long quando a bitola foi DECLARADA
    (pilar_concreto.py:683) - sem a chave '18.4.3 12.phi_long' em
    limites_s_m nao ha bitola honesta e a celula declara isso.
    """
    det = detalhe if isinstance(detalhe, dict) else {}
    limites = det.get("limites_s_m") or {}
    if "18.4.3 12.phi_long" not in limites:
        return _ARRANJO_NAO_DETALHADO
    try:
        phi_long = float(limites["18.4.3 12.phi_long"]) * 1000.0 / 12.0
    except (TypeError, ValueError):
        return _ARRANJO_NAO_DETALHADO
    return "f%.1f (12.phi_long declarado)" % phi_long


def _vals_fileira_trecho(nome, pilar, trecho):
    """Os 9 valores da fileira, na ordem de _COLS_PILARES (G115: um trecho).

    LANCES e' o intervalo 1-based do topo para a base ("1-5" ou "6");
    secao, Nd, As, taxa, estribo, limite e arranjo sao os do lance de BASE
    do trecho (o mais carregado). Pilar de lance unico sai "1-1"? Nao:
    trecho unico cobre "1-N" (ex. "1-9"); lance isolado no meio sai "6".
    """
    base = (trecho or {}).get("base") or {}
    det = base.get("detalhe") if isinstance(base.get("detalhe"), dict) else {}
    try:
        sec = "%dx%d" % (round(float(base.get("b", 0)) * 100),
                         round(float(base.get("h", 0)) * 100))
    except (TypeError, ValueError):
        sec = "-"
    return [
        str(nome),
        sec,
        str((trecho or {}).get("rotulo", "-")),
        "%.1f" % float(base.get("Nd", 0)),
        "%.2f" % float(base.get("As_cm2", 0)),
        "%.2f" % float(base.get("taxa_pct", 0)),
        _estribo_pilar_rotulo(det),
        str(det.get("s_limite_governante", "-")),
        _arranjo_long_rotulo(det),
    ]


# G119 (auditoria do G115): `_vals_fileira_pilar` foi removida. O G115 a
# manteve "por compatibilidade G110", mas depois da troca para fileira por
# trecho NINGUEM mais a chamava - nem producao, nem teste - e ela carregava
# uma segunda copia da montagem da fileira, livre para divergir da real
# (`_vals_fileira_trecho`). Codigo morto que duplica regra e' a mesma classe
# do filtro de nome morto: nao quebra hoje, mente amanha.


def _escreve_secao_pilares(P, pilares, y_sub, W, edicao=None):
    """Subtitulo + cabecalho + fileiras (ou a declaracao de ausencia).

    G115: uma fileira por TRECHO de lances iguais (mesma secao e mesmo As),
    do topo para a base, pilar a pilar em ordem alfabetica. Pilar sem
    mudanca sai com uma fileira ("1-N"). Devolve o yy apos a ultima fileira
    (ou linha de declaracao).
    """
    P.append(sb.texto(W / 2, y_sub, _subtitulo_pilares(edicao), 11, color="#444"))
    y0 = y_sub + 22
    if not isinstance(pilares, dict) or not pilares:
        P.append(sb.texto(30, y0 + 28, _AUSENCIA_PILARES, 12, anchor="start"))
        return y0 + 28
    _escreve_cabecalho_tabela(P, _COLS_PILARES, y0, W)
    yy = y0 + 28
    for nome in sorted(pilares):
        for trecho in _trechos_pilar(pilares[nome]):
            _escreve_fileira(P, _COLS_PILARES,
                             _vals_fileira_trecho(nome, pilares[nome], trecho), yy)
            yy += 22
    return yy


def _rodape_armacao_pilares(P, yy):
    """As tres linhas de rodape da secao de pilares (notas + CONCEITUAL/ART)."""
    P.append(sb.texto(30, yy + 18,
                      "uma fileira por trecho de lances iguais (mesma secao e "
                      "mesmo As) ; LANCES do topo para a base ; Nd, As, taxa, "
                      "estribo e limite do lance de BASE do trecho",
                      11, anchor="start", color="#444"))
    P.append(sb.texto(30, yy + 36,
                      "arranjo longitudinal so com phi_long_mm declarada "
                      "(18.4.3 12.phi_long) ; sem bitola, NAO DETALHADO",
                      11, anchor="start", color="#444"))
    P.append(sb.texto(30, yy + 54,
                      "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
                      11, anchor="start", weight="bold", color="#444"))


def prancha_armacao_pilares_svg(pilares, titulo=None, edicao=None):
    """Quadro de armacao dos pilares (SVG puro-Python, G110/G115).

    UMA fileira por TRECHO de lances iguais (G115: mesma secao e mesmo As;
    "lances 1-5: 19x30, As 2,28"): secao, intervalo de lances, Nd, As, taxa,
    estribo (phi/s/ramos), limite governante da 18.4.3 e arranjo
    longitudinal. Pilar sem mudanca sai com uma fileira ("1-N"). Pilares
    vazio/ausente declara a ausencia em vez de sair com a tabela vazia.
    """
    nomes = sorted(pilares) if isinstance(pilares, dict) else []
    W = 1420
    # G115/G77: a altura cresce com as fileiras (uma por trecho, nao por
    # pilar). Folha de altura fixa com conteudo que cresce corta fileira.
    H = 170 + max(_n_fileiras_pilares(pilares), 1) * 22 + 110
    tit = titulo or ("ARMACAO DE PILARES - PAVIMENTO-TIPO "
                     "(%d pilares VERIFICADOS)" % len(nomes))
    tit += _sufixo_edicao(edicao)
    P = sb.abre_svg(W, H, tit)
    yy = _escreve_secao_pilares(P, pilares, 58, W, edicao=edicao)
    _rodape_armacao_pilares(P, yy)
    P.append("</svg>")
    return "\n".join(P)


def _celula(svg, valor):
    """O valor sai como CELULA da tabela (`<text ...>valor</text>`)? (G119)

    O G115 conferia o intervalo por substring solta, e um trecho de um lance
    so ("6") casa em qualquer lugar do SVG - coordenada, tamanho de fonte,
    outro numero. Medido: "6", "3" e "7" aparecem numa folha que nao tem
    nenhum desses trechos, entao essa metade da guarda nunca reprovava.
    `_escreve_fileira` emite cada celula via `sb.texto`, logo a checagem
    honesta e' pelo conteudo do elemento de texto.
    """
    return (">%s<" % valor) in (svg or "")


def confere_armacao_pilares(pilares, svg):
    """Drawing-vs-data do quadro de pilares (G110/G115): todo TRECHO desenhado.

    O esperado deriva do DADO (dict pilares), nunca do svg: cada pilar conta
    >= n_trechos ocorrencias do nome (regex com fronteira, padrao G69 do
    confere_armacao_vigas) e cada trecho conta com o intervalo ("1-5" ou
    "6"), a secao e o As do lance de BASE do trecho presentes no SVG. A
    soma dos lances cobertos tem de bater com os lances do resultado
    (drawing-vs-data por soma, nao so presenca). A folha antiga (G110: uma
    fileira por pilar, so a base) reprova aqui quando ha variacao ao longo
    dos lances -- e' o vermelho por injecao do G115. Com pilares
    vazio/ausente, ok=True so se a declaracao de ausencia constar.
    """
    import re as _re

    nomes = sorted(pilares) if isinstance(pilares, dict) else []
    if not nomes:
        ok = _AUSENCIA_PILARES in (svg or "")
        return {"n_pilares": 0, "n_trechos": 0, "faltando": [], "ok": ok}
    faltando = []
    n_trechos = 0
    for nome in nomes:
        trechos = _trechos_pilar(pilares[nome])
        n_trechos += len(trechos)
        achados = len(_re.findall(_re.escape(str(nome)) + r"(?![0-9A-Za-z])",
                                  svg or ""))
        if achados < max(len(trechos), 1):
            faltando.append("%s: %d trechos calculados, %d desenhados"
                            % (nome, len(trechos), achados))
        for trecho in trechos:
            base = trecho.get("base") or {}
            try:
                sec = "%dx%d" % (round(float(base.get("b", 0)) * 100),
                                 round(float(base.get("h", 0)) * 100))
            except (TypeError, ValueError):
                sec = "-"
            try:
                as_txt = "%.2f" % float(base.get("As_cm2", 0))
            except (TypeError, ValueError):
                as_txt = "-"
            rotulo = str(trecho.get("rotulo", ""))
            if rotulo and not _celula(svg, rotulo):
                faltando.append("%s trecho %s: intervalo nao desenhado"
                                % (nome, rotulo))
            if sec != "-" and not _celula(svg, sec):
                faltando.append("%s trecho %s: secao %s nao desenhada"
                                % (nome, rotulo, sec))
            if as_txt != "-" and not _celula(svg, as_txt):
                faltando.append("%s trecho %s: As %s nao desenhado"
                                % (nome, rotulo, as_txt))
        # a folha soma exatamente os lances de cada pilar do resultado
        coberto = sum(t["i_fim"] - t["i_ini"] + 1 for t in trechos)
        n_lances = len((pilares[nome] or {}).get("lances") or [])
        if coberto != n_lances:
            faltando.append("%s: %d lances calculados, %d cobertos"
                            % (nome, n_lances, coberto))
    return {"n_pilares": len(nomes), "n_trechos": n_trechos,
            "faltando": faltando, "ok": not faltando}


def gerar_prancha_armacao_pilares(pilares, path, titulo=None, edicao=None):
    """Escreve o quadro de armacao de pilares (SVG) em `path`. Retorna o path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(prancha_armacao_pilares_svg(pilares, titulo, edicao=edicao))
    return path


def prancha_armacao_vigas_pilares_svg(vigas_verificacao, pilares, titulo=None,
                                     edicao=None):
    """Combinada N:1 de PE-CO-02 (G110/G115): secao de vigas + secao de pilares.

    Empilha no MESMO <svg> a tabela por tramo (builder da G34, mesma
    formatacao da prancha de vigas) e o quadro por TRECHO de pilar (G115).
    Altura dinamica H = base + 22*(n_tramos + n_fileiras_pilares); passa em
    desenho_svg_base.confere_folha_svg.
    """
    _por_linha, n_tramos, linhas_v = _dados_vigas(vigas_verificacao)
    nomes_p = sorted(pilares) if isinstance(pilares, dict) else []
    W = 1420
    H = _BASE_COMBINADA + 22 * (max(len(linhas_v), 1) + max(_n_fileiras_pilares(pilares), 1))
    tit = titulo or ("ARMACAO DE VIGAS E PILARES - PAVIMENTO-TIPO "
                     "(%d tramos VERIFICADOS / %d pilares VERIFICADOS)"
                     % (n_tramos, len(nomes_p)))
    tit += _sufixo_edicao(edicao)
    P = sb.abre_svg(W, H, tit)
    P.append(sb.texto(W / 2, 58, _SUBTITULO_VIGAS, 11, color="#444"))
    _escreve_cabecalho_tabela(P, _COLS_VIGAS, 92, W)
    yy = 92 + 28
    if linhas_v:
        for linha, tramo in linhas_v:
            _escreve_fileira(P, _COLS_VIGAS,
                             _vals_fileira_viga(linha, tramo), yy)
            yy += 22
    else:
        P.append(sb.texto(30, yy,
                          "vigas nao verificadas nesta rodada "
                          "(vigas_verificacao sem tramos)",
                          12, anchor="start"))
        yy += 22
    yy = _escreve_secao_pilares(P, pilares, yy + 18, W, edicao=edicao)
    _rodape_armacao_vigas(P, yy, conceitual=False)
    _rodape_armacao_pilares(P, yy + 60)
    P.append("</svg>")
    return "\n".join(P)


def gerar_prancha_armacao_vigas_pilares(vigas_verificacao, pilares, path,
                                         titulo=None, edicao=None):
    """Escreve a combinada de armacao vigas+pilares (SVG) em `path`."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(prancha_armacao_vigas_pilares_svg(vigas_verificacao, pilares,
                                                  titulo, edicao=edicao))
    return path


# G146 (D173): o que o calculo do mezanino NAO produz para as primitivas do
# predio — medido contra `galpao_mezanino.rodar` (laje 1 painel com
# `armaduras`, `viga_X`/`viga_Y` simples, `pilar` unico, `sapatas[4]` com
# `aprovado`, posicao x0/y0/Lx/Ly/h) e o que `planta_formas_svg` +
# `prancha_armacao_vigas_pilares_svg` leem (shape do predio: pav com
# vaos_x/vaos_y/area_m2/paineis[i,j,lx,ly,caso,engastes]/pilares[nome,i,j,
# posicao,N_k]/g/q + vigas_verificacao por_linha/tramos + pilares por
# lances). Uma fonte so: esta lista mora na producao e a folha a declara,
# nunca inventa.
AUSENCIAS_GALPAO_MEZANINO = (
    "engastamento entre paineis (painel unico, bordas simples)",
    "momento negativo de envoltorias nas vigas (viga simples, sem continuidade)",
    "locacao x0/y0 do mezanino no envelope do galpao "
    "(a planta mostra o mezanino isolado; ver memorial)",
)

#: declaration when the slab has no reinforcement sized in this run (conv. 13:
#: the sheet states it in words, never a number).
AUSENCIA_LAJE_SEM_ARMADURA = (
    "armadura da laje (laje sem armaduras dimensionadas nesta rodada)")


def adaptar_galpao_mezanino(r):
    """Adapta o resultado de `galpao_mezanino.rodar` para as primitivas de
    formas e armacao do predio, sem recalcular nada.

    Devolve (pav, vigas_verificacao, pilares, sapatas, ausentes): `pav` no
    shape que `planta_formas_svg` le (1 painel Lx x Ly, 4 pilares M-P1..M-P4
    nos cantos com o Nk calculado); `vigas_verificacao` com 4 linhas de 1
    tramo (M-VX1/M-VX2 do `viga_X`, M-VY1/M-VY2 do `viga_Y` calculados);
    `pilares` com 4 lances unicos do `pilar` calculado; `sapatas` com as 4
    geometrias DIMENSIONADAS (B/L/h do `aprovado`); `ausentes` e o
    subconjunto de `AUSENCIAS_GALPAO_MEZANINO` mais a armadura da laje
    quando o calculo nao a produz. Ausencia se declara na folha, nunca vira
    default silencioso. Levanta ValueError nomeando a PE-MZ-01 quando a
    fundacao nao foi dimensionada (sem sapata aprovada nao ha folha
    honesta) ou quando falta o dado de entrada da folha.
    """
    if not isinstance(r, dict):
        raise ValueError(
            "adaptar_galpao_mezanino: resultado do mezanino ausente "
            "(sem calculo nao ha folha PE-MZ-01)")
    mz = r.get("mezanino")
    if not isinstance(mz, dict):
        raise ValueError(
            "adaptar_galpao_mezanino: bloco 'mezanino' ausente no resultado "
            "(sem geometria Lx/Ly nao ha folha PE-MZ-01)")
    try:
        Lx = float(mz["Lx"])
        Ly = float(mz["Ly"])
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            "adaptar_galpao_mezanino: Lx/Ly do mezanino nao declarados "
            "(sem painel nao ha folha PE-MZ-01)")
    if not (Lx > 0 and Ly > 0):
        raise ValueError(
            "adaptar_galpao_mezanino: painel invalido (Lx=%r, Ly=%r; "
            "sem painel nao ha folha PE-MZ-01)" % (mz.get("Lx"), mz.get("Ly")))
    try:
        Nk = float(r["Nk_pilar"])
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            "adaptar_galpao_mezanino: Nk do pilar nao calculado "
            "(sem carga nao ha folha PE-MZ-01)")
    try:
        g_m2 = float(mz["g_kN_m2"])
        q_m2 = float(mz["q_uso"])
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            "adaptar_galpao_mezanino: cargas g_kN_m2/q_uso do mezanino nao "
            "calculadas (sem carga nao ha folha PE-MZ-01)")
    laje = r.get("laje")
    caso = 1
    if isinstance(laje, dict) and laje.get("caso") is not None:
        try:
            caso = int(laje["caso"])
        except (TypeError, ValueError):
            raise ValueError(
                "adaptar_galpao_mezanino: caso da laje nao numerico (%r; "
                "sem caso nao ha folha PE-MZ-01)" % (laje.get("caso"),))
    # --- formas: 1 painel, 4 pilares nos cantos (mesma ordem do membros_bim)
    cantos_ij = [(0, 0), (1, 0), (0, 1), (1, 1)]
    pilares_pav = []
    for k, (i, j) in enumerate(cantos_ij, start=1):
        pilares_pav.append({"i": i, "j": j, "nome": "M-P%d" % k,
                            "posicao": "canto", "N_k": Nk})
    pav = {"vaos_x": [Lx], "vaos_y": [Ly], "area_m2": Lx * Ly,
           "paineis": [{"i": 0, "j": 0, "lx": Lx, "ly": Ly, "caso": caso,
                        "engastes": {"esq": False, "dir": False,
                                     "inf": False, "sup": False}}],
           "pilares": pilares_pav,
           "g_kN_m2": g_m2, "q_kN_m2": q_m2}
    # --- armacao das vigas: 1 tramo por viga fisica (2 em X + 2 em Y)
    rx = r.get("viga_X")
    ry = r.get("viga_Y")
    if not isinstance(rx, dict) or not isinstance(ry, dict):
        raise ValueError(
            "adaptar_galpao_mezanino: viga_X/viga_Y nao calculadas "
            "(sem viga nao ha folha PE-MZ-01)")

    def _tramo(res_viga, nome, vao):
        try:
            md_pos = float(res_viga["M_d"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(
                "adaptar_galpao_mezanino: %s sem M_d calculado "
                "(sem esforco nao ha folha PE-MZ-01)" % nome)
        md_neg = res_viga.get("M_d_neg")
        try:
            md_neg = float(md_neg) if md_neg is not None else 0.0
        except (TypeError, ValueError):
            md_neg = 0.0
        return {"tramo": 1, "L": float(vao),
                "M_d_kNm": md_pos, "M_d_neg_envoltoria_kNm": md_neg,
                "As_inf_cm2": res_viga.get("As_inf_cm2"),
                "As_sup_cm2": res_viga.get("As_sup_cm2"),
                "els": res_viga.get("els"),
                "verificacao": res_viga,
                "OK": bool(res_viga.get("OK"))}

    por_linha = [
        {"nome": "M-VX1", "b": float(rx["b"]), "h": float(rx["h"]),
         "tramos": [_tramo(rx, "viga_X", Lx)]},
        {"nome": "M-VX2", "b": float(rx["b"]), "h": float(rx["h"]),
         "tramos": [_tramo(rx, "viga_X", Lx)]},
        {"nome": "M-VY1", "b": float(ry["b"]), "h": float(ry["h"]),
         "tramos": [_tramo(ry, "viga_Y", Ly)]},
        {"nome": "M-VY2", "b": float(ry["b"]), "h": float(ry["h"]),
         "tramos": [_tramo(ry, "viga_Y", Ly)]},
    ]
    vigas_verificacao = {"por_linha": por_linha, "n_tramos": 4}
    # --- armacao dos pilares: 1 lance por pilar fisico (4 identicos)
    rp = r.get("pilar")
    if not isinstance(rp, dict):
        raise ValueError(
            "adaptar_galpao_mezanino: pilar nao calculado "
            "(sem pilar nao ha folha PE-MZ-01)")
    try:
        nd = float(rp["Nd"])
        as_cm2 = float(rp["As_cm2"])
        taxa = float(rp["taxa_pct"])
        b_pil = float(rp.get("hy", mz.get("hy", 0.0)))
        h_pil = float(rp.get("hx", mz.get("hx", 0.0)))
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            "adaptar_galpao_mezanino: pilar sem Nd/As/taxa/secao "
            "(sem pilar nao ha folha PE-MZ-01)")
    pilares = {}
    for k in range(1, 5):
        pilares["M-P%d" % k] = {
            "lances": [{"b": b_pil, "h": h_pil, "Nd": nd,
                        "As_cm2": as_cm2, "taxa_pct": taxa,
                        "detalhe": rp}]}
    # --- sapatas: a geometria DIMENSIONADA, uma por pilar
    saps = r.get("sapatas")
    if not isinstance(saps, list) or len(saps) < 4:
        raise ValueError(
            "adaptar_galpao_mezanino: 4 sapatas dimensionadas ausentes "
            "(sem sapata aprovada nao ha folha PE-MZ-01)")
    sapatas = []
    for k, sap in enumerate(saps[:4], start=1):
        ap = (sap or {}).get("aprovado") if isinstance(sap, dict) else None
        if not ap or len(ap) < 3:
            raise ValueError(
                "adaptar_galpao_mezanino: sapata M-SAP%d sem geometria "
                "aprovada (sem sapata aprovada nao ha folha PE-MZ-01)" % k)
        sapatas.append({"marca": "M-SAP%d" % k, "B_m": float(ap[0]),
                        "L_m": float(ap[1]), "h_m": float(ap[2]),
                        "Nk_kN": Nk})
    ausentes = list(AUSENCIAS_GALPAO_MEZANINO)
    arm = laje.get("armaduras") if isinstance(laje, dict) else None
    if not arm:
        ausentes.append(AUSENCIA_LAJE_SEM_ARMADURA)
    return pav, vigas_verificacao, pilares, sapatas, ausentes
