# ============================================================================
# planta_eletrica_dxf.py - O ELETRICO DESENHADO SOBRE A PLANTA DO CLIENTE (plano
# de 2026-10-08, Fase 5, quarto passo). Abre o DXF recebido, acrescenta camadas
# proprias (prefixo ELE-) e grava em OUTRO arquivo; nada do desenho original e'
# apagado nem movido.
#
# O QUE VAI AO DESENHO
#   - o quadro, na posicao marcada pelo cliente (camada QUADRO), se houver;
#   - um ponto de luz por ambiente, no centro do poligono;
#   - os pontos de tomada do ambiente, repartidos por igual ao longo do
#     perimetro;
#   - os equipamentos declarados, ao lado do ponto de luz do ambiente;
#   - junto de cada ponto, o circuito que o alimenta;
#   - a tabela dos circuitos ao lado da planta (com condutor e protecao quando
#     ha dimensionamento) e a legenda dos simbolos.
#
# AS POSICOES SAO SUGESTAO DE PARTIDA, nao projeto: a planta recebida nao diz
# onde ficam portas, bancadas e moveis. A nota vai escrita no desenho.
#
# ELETRODUTO: so um ESBOCO de ligacao, em camada propria, quando o quadro esta
# marcado. O ponto de luz de cada ambiente e' o no do ambiente; os nos se
# ligam ao quadro pela arvore de menor comprimento total (cada no se liga ao
# no ja ligado mais proximo, a comecar do quadro) e cada tomada ou equipamento
# se liga ao no do seu ambiente. Sao retas: nao desviam de parede, nao dizem
# por onde o eletroduto passa nem quantos condutores leva. O comprimento dos
# circuitos NAO sai deste esboco (segue o criterio declarado de tracado).
#
# SIMBOLOS: o acervo nao tem norma de simbologia; os simbolos sao ADOTADOS e
# explicados na legenda do proprio desenho.
#
# Biblioteca: quem a chama pela linha de comando e' o ambientes_dxf (dxf=<saida>).
# ============================================================================
"""Camadas do eletrico (pontos, circuitos, tabela) sobre a planta DXF recebida."""

from __future__ import annotations

CAMADAS = {"ELE-QUADRO": 1, "ELE-ILUMINACAO": 2, "ELE-TOMADA": 3, "ELE-EQUIPAMENTO": 6,
           "ELE-TEXTO": 7, "ELE-TABELA": 7, "ELE-ELETRODUTO-ESBOCO": 8}
NOTA_ESBOCO = ("ELETRODUTO: ESBOCO DE LIGACAO EM LINHA RETA - O TRACADO REAL E' DEFINIDO "
               "NA REVISAO")
BLOCOS = {"lighting": ("ELE_LUZ", "ELE-ILUMINACAO"), "tug": ("ELE_TOMADA", "ELE-TOMADA"),
          "tue": ("ELE_EQUIPAMENTO", "ELE-EQUIPAMENTO")}
BLOCO_QUADRO = "ELE_QUADRO"
LEGENDA = (("ELE_LUZ", "ELE-ILUMINACAO", "ponto de luz no teto"),
           ("ELE_TOMADA", "ELE-TOMADA", "ponto de tomada"),
           ("ELE_EQUIPAMENTO", "ELE-EQUIPAMENTO", "ponto de equipamento de uso especifico"),
           (BLOCO_QUADRO, "ELE-QUADRO", "quadro de distribuicao"))
NOTA = "POSICOES DOS PONTOS: SUGESTAO DE PARTIDA - AJUSTAR NA REVISAO DO PROJETO"
# tamanho do texto no papel nao e' conta: e' escolha de apresentacao
ALTURA_TEXTO_M = 0.12
# o simbolo da tomada fica encostado na parede, deste tanto para dentro
AFASTADA_M = 1.2 * ALTURA_TEXTO_M


def _centro(pts):
    """Centro de area do poligono."""
    a2 = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        cruz = x0 * y1 - x1 * y0
        a2 += cruz
        cx += (x0 + x1) * cruz
        cy += (y0 + y1) * cruz
    return cx / (3.0 * a2), cy / (3.0 * a2)


def _dentro(ponto, pts):
    x, y = ponto
    dentro = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            dentro = not dentro
    return dentro


def _no_perimetro(pts, n):
    """n posicoes igualmente espacadas ao longo do contorno, a meio passo do
    primeiro vertice, cada uma AFASTADA_M para dentro do ambiente: em parede
    comum a dois ambientes o simbolo fica do lado de quem ele serve."""
    lados = [(p, q, ((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5)
             for p, q in zip(pts, pts[1:] + pts[:1])]
    total = sum(c for _p, _q, c in lados)
    saida = []
    for k in range(n):
        alvo = (k + 0.5) * total / n
        for p, q, c in lados:
            if alvo <= c:
                # fora do canto: no vertice nao ha "lado de dentro" de uma parede so
                if c >= 2.0 * AFASTADA_M:
                    alvo = min(max(alvo, AFASTADA_M), c - AFASTADA_M)
                t = alvo / c
                x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
                nx, ny = -(q[1] - p[1]) / c * AFASTADA_M, (q[0] - p[0]) / c * AFASTADA_M
                if _dentro((x + nx, y + ny), pts):
                    x, y = x + nx, y + ny
                elif _dentro((x - nx, y - ny), pts):
                    x, y = x - nx, y - ny
                saida.append((x, y))
                break
            alvo -= c
    return saida


def posicoes_sugeridas(divisao, geometria):
    """{ponto: (x_m, y_m)} e os erros. Ambiente cujo centro cai fora do
    proprio poligono (planta em L, em U) nao recebe ponto adivinhado."""
    posicoes, erros = {}, []
    por_ambiente = {}
    for p in divisao["pontos"]:
        por_ambiente.setdefault(p["room"], []).append(p)
    for nome, pontos in por_ambiente.items():
        if nome not in geometria:
            erros.append({"code": "ambiente_sem_geometria", "ambiente": nome,
                          "detail": "sem poligono lido da planta para posicionar os pontos"})
            continue
        pts = [tuple(v) for v in geometria[nome]]
        centro = _centro(pts)
        if not _dentro(centro, pts):
            erros.append({"code": "centro_fora_do_ambiente", "ambiente": nome,
                          "detail": "o centro do poligono cai fora dele; posicione os pontos "
                                    "deste ambiente a mao"})
            continue
        tomadas = [p for p in pontos if p["kind"] == "tug"]
        for p, pos in zip(tomadas, _no_perimetro(pts, len(tomadas))):
            posicoes[p["id"]] = pos
        outros = [p for p in pontos if p["kind"] != "tug"]
        for j, p in enumerate(sorted(outros, key=lambda p: p["kind"] != "lighting")):
            # equipamentos em fila ao lado do ponto de luz
            posicoes[p["id"]] = (centro[0] + 4.0 * ALTURA_TEXTO_M * j, centro[1])
    return posicoes, erros


def esboco_de_eletroduto(divisao, posicoes, quadro_m):
    """[(origem, destino)] em metros: arvore dos pontos de luz a partir do
    quadro e, em cada ambiente, uma reta do ponto de luz a cada outro ponto.
    Sem quadro marcado nao ha esboco."""
    if quadro_m is None:
        return []
    nos = {}                                           # ambiente -> posicao do ponto de luz
    for p in divisao["pontos"]:
        if p["kind"] == "lighting" and p["id"] in posicoes:
            nos[p["room"]] = posicoes[p["id"]]
    dist = lambda a, b: ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    trechos, ligados, soltos = [], [tuple(quadro_m)], dict(nos)
    while soltos:
        nome, de = min(((n, l) for n in sorted(soltos) for l in ligados),
                       key=lambda par: dist(soltos[par[0]], par[1]))
        trechos.append((de, soltos[nome]))
        ligados.append(soltos.pop(nome))
    for p in divisao["pontos"]:
        if p["kind"] != "lighting" and p["id"] in posicoes and p["room"] in nos:
            trechos.append((nos[p["room"]], posicoes[p["id"]]))
    return trechos


def _blocos(doc, r):
    """Simbolos adotados, desenhados uma vez como blocos de raio r."""
    def _novo(nome):
        return doc.blocks.new(nome) if nome not in doc.blocks else None

    b = _novo("ELE_LUZ")
    if b is not None:                                  # circulo com um X
        b.add_circle((0, 0), r)
        d = r * 0.7071
        b.add_line((-d, -d), (d, d))
        b.add_line((-d, d), (d, -d))
    b = _novo("ELE_TOMADA")
    if b is not None:                                  # triangulo
        b.add_lwpolyline([(-r, -r * 0.6), (r, -r * 0.6), (0, r)], close=True)
    b = _novo("ELE_EQUIPAMENTO")
    if b is not None:                                  # triangulo dentro de circulo
        b.add_circle((0, 0), r)
        b.add_lwpolyline([(-r * 0.6, -r * 0.4), (r * 0.6, -r * 0.4), (0, r * 0.7)], close=True)
    b = _novo(BLOCO_QUADRO)
    if b is not None:                                  # retangulo com a diagonal
        b.add_lwpolyline([(-1.5 * r, -r), (1.5 * r, -r), (1.5 * r, r), (-1.5 * r, r)],
                         close=True)
        b.add_line((-1.5 * r, -r), (1.5 * r, r))


def _linhas_da_tabela(divisao, dimensionamento):
    resumo = {}
    if dimensionamento is not None:
        resumo = {r["id"]: r for r in dimensionamento["resumo"]}
    cab = ["CIRC", "CLASSE", "PTS", "VA", "V", "A", "FASE"]
    if resumo:
        cab += ["L (m)", "mm2", "DJ (A)", "DR"]
    linhas = [cab]
    for c in divisao["circuitos"]:
        linha = [c["id"], c["classe"], "%d" % len(c["point_ids"]), "%.0f" % c["potencia_va"],
                 "%.0f" % c["tensao_v"], "%.2f" % c["corrente_a"], "".join(c["fases"])]
        if resumo:
            if c["id"] in resumo:
                r = resumo[c["id"]]
                linha += ["%.1f" % r["comprimento_m"], "%g" % r["secao_mm2"],
                          "%d" % r["disjuntor_a"], "sim" if r["dr"] else "nao"]
            else:                                      # circuito que o calculo recusou
                linha += ["NAO DIMENSIONADO", "-", "-", "-"]
        linhas.append(linha)
    return linhas


def desenhar(planta_dxf, destino_dxf, leitura, divisao, dimensionamento=None):
    """Grava `destino_dxf` = planta recebida + camadas ELE-. `leitura` e' o
    bloco `leitura_dxf` do leitor (geometria, quadro_m, metros_por_unidade).
    Devolve {arquivo, pontos_desenhados, pontos_sem_posicao, erros, ATENDE}."""
    import ezdxf

    if divisao["quadro"] is None:
        return {"arquivo": None, "pontos_desenhados": 0, "pontos_sem_posicao": [],
                "trechos_de_esboco": 0,
                "erros": [{"code": "divisao_nao_feita",
                           "detail": "sem circuitos nao ha o que desenhar"}], "ATENDE": False}
    doc = ezdxf.readfile(planta_dxf)
    msp = doc.modelspace()
    esc = leitura["metros_por_unidade"]
    u = lambda metros: metros / esc                    # metros -> unidade do desenho
    h = u(ALTURA_TEXTO_M)
    for nome, cor in CAMADAS.items():
        if nome not in doc.layers:
            doc.layers.add(nome, color=cor)
    _blocos(doc, h)

    posicoes, erros = posicoes_sugeridas(divisao, leitura["geometria"])
    circuito_de = {pid: c["id"] for c in divisao["circuitos"] for pid in c["point_ids"]}
    desenhados, sem_posicao = 0, []
    for p in divisao["pontos"]:
        if p["id"] not in posicoes or p["id"] not in circuito_de:
            sem_posicao.append(p["id"])
            continue
        x, y = posicoes[p["id"]]
        bloco, camada = BLOCOS[p["kind"]]
        msp.add_blockref(bloco, (u(x), u(y)), dxfattribs={"layer": camada})
        rotulo = circuito_de[p["id"]]
        if p["kind"] == "tue":
            rotulo += " " + p["nome"]
        msp.add_text(rotulo, dxfattribs={"layer": "ELE-TEXTO", "height": h * 0.8,
                                         "insert": (u(x) + 1.3 * h, u(y) + 0.6 * h)})
        desenhados += 1

    if leitura["quadro_m"] is not None:
        qx, qy = leitura["quadro_m"]
        msp.add_blockref(BLOCO_QUADRO, (u(qx), u(qy)), dxfattribs={"layer": "ELE-QUADRO"})
        msp.add_text("QD", dxfattribs={"layer": "ELE-QUADRO", "height": h,
                                       "insert": (u(qx) + 2.0 * h, u(qy) + 1.2 * h)})

    trechos = esboco_de_eletroduto(divisao, posicoes, leitura["quadro_m"])
    for (xa, ya), (xb, yb) in trechos:
        msp.add_line((u(xa), u(ya)), (u(xb), u(yb)),
                     dxfattribs={"layer": "ELE-ELETRODUTO-ESBOCO"})

    # tabela, legenda e nota a direita da planta
    vertices = [v for pts in leitura["geometria"].values() for v in pts]
    if leitura["quadro_m"] is not None:
        vertices.append(leitura["quadro_m"])
    x0 = u(max(v[0] for v in vertices) + 1.0)
    y = u(max(v[1] for v in vertices))
    linhas = _linhas_da_tabela(divisao, dimensionamento)
    larguras = [max(len(linha[i]) for linha in linhas) + 2 for i in range(len(linhas[0]))]
    passo = 2.0 * h
    msp.add_text("QUADRO DE CARGAS", dxfattribs={"layer": "ELE-TABELA", "height": 1.2 * h,
                                                  "insert": (x0, y)})
    y -= passo
    largura_total = sum(larguras) * 0.8 * h
    for linha in linhas:
        msp.add_line((x0, y + 0.75 * passo), (x0 + largura_total, y + 0.75 * passo),
                     dxfattribs={"layer": "ELE-TABELA"})
        x = x0
        for celula, larg in zip(linha, larguras):
            msp.add_text(celula, dxfattribs={"layer": "ELE-TABELA", "height": h,
                                             "insert": (x + 0.4 * h, y)})
            x += larg * 0.8 * h
        y -= passo
    msp.add_line((x0, y + 0.75 * passo), (x0 + largura_total, y + 0.75 * passo),
                 dxfattribs={"layer": "ELE-TABELA"})
    q = divisao["quadro"]
    msp.add_text("CARGA INSTALADA %.0f VA; POR FASE %s" % (
        q["carga_instalada_va"],
        ", ".join("%s=%.0f" % par for par in sorted(q["carga_por_fase_va"].items()))),
        dxfattribs={"layer": "ELE-TABELA", "height": h, "insert": (x0, y)})
    y -= 2.0 * passo
    msp.add_text("LEGENDA", dxfattribs={"layer": "ELE-TABELA", "height": 1.2 * h,
                                         "insert": (x0, y)})
    for bloco, _camada, descricao in LEGENDA:
        y -= 1.5 * passo
        # na camada da TABELA: quem conta pontos por camada nao conta a legenda
        msp.add_blockref(bloco, (x0 + 2.0 * h, y + 0.4 * h),
                         dxfattribs={"layer": "ELE-TABELA"})
        msp.add_text(descricao, dxfattribs={"layer": "ELE-TABELA", "height": h,
                                            "insert": (x0 + 5.0 * h, y)})
    y -= 2.0 * passo
    msp.add_text(NOTA, dxfattribs={"layer": "ELE-TABELA", "height": h, "insert": (x0, y)})
    if trechos:
        y -= passo
        msp.add_text(NOTA_ESBOCO, dxfattribs={"layer": "ELE-TABELA", "height": h,
                                              "insert": (x0, y)})

    doc.saveas(destino_dxf)
    dimensionado = dimensionamento is None or bool(dimensionamento["ATENDE"])
    atende = bool(divisao["ATENDE"]) and dimensionado and not erros and not sem_posicao
    return {"arquivo": destino_dxf, "pontos_desenhados": desenhados,
            "pontos_sem_posicao": sem_posicao, "trechos_de_esboco": len(trechos),
            "erros": erros, "ATENDE": atende}
