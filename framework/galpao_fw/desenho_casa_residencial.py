# ============================================================================
# desenho_casa_residencial.py - O QUE ESTE MODULO DESENHA
# Pranchas SVG do adaptador residencial real (sem FreeCAD, so o JSON calculado):
#   1. quadro-ambientes.svg      - programa de ambientes + previsao de carga
#                                  NBR 5410 9.5.2 (area, perimetro, criterio);
#   2. conferencia-nbr5410.svg   - minimo normativo x declarado, por ambiente,
#                                  com o deficit destacado;
#   3. esquema-hidraulico.svg    - esquema vertical das tres redes com os DN
#                                  calculados (NBR 5626 / 8160 / 10844).
#   4. planta-baixa.svg            - PE-AR-02 (G78): retangulos do LAYOUT
#                                  declarado (canonico: turnkey.arquitetura.
#                                  layout) com nome, dimensoes, area do
#                                  programa e cotas gerais do envelope.
#
# O que NAO ha aqui e' implantacao nem cortes/fachadas (PE-AR-01/PE-AR-03):
# o spec nao declara lote (dimensoes, recuos, orientacao) nem niveis (cota de
# soleira/terreno), e arbitrar recuo ou soleira seria geometria inventada -
# pior que folha ausente. As duas ficam `not_available` com o dado nomeado.
#
# A planta baixa tambem ja foi ausencia: o programa declara area e perimetro,
# nao posicoes, e desenhar comodos em posicoes inventadas seria um desenho que
# nao corresponde ao dado. O que destrava a folha e' o LAYOUT declarado - sem
# ele a prancha volta a motivo explicito em 'skipped'.
#
# Todo texto sai por texto(), que ja aplica esc() (SVG e' XML: um '<' cru quebra
# o arquivo inteiro). NUNCA escapar antes de chamar texto(): a dupla escapa
# imprime "&lt;" literal na prancha - so o parse do SVG pega isso, substring nao.
# ============================================================================
"""Pranchas SVG da casa residencial: quadro de ambientes, conferencia
NBR 5410 9.5.2 e esquema hidraulico. Stateless."""

from __future__ import annotations

from pathlib import Path

from desenho_svg_base import abre_svg, linha, texto

COR_COTA = "#1d4ed8"
COR_FUNDO_COMODO = "#f1f5f9"

MARGEM = 40
LINHA_H = 26          # altura da linha da tabela
CABECALHO_Y = 90
COR_DEFICIT = "#b91c1c"
COR_OK = "#15803d"


def _num(valor, fmt="%.2f"):
    if valor is None:
        return "-"
    if isinstance(valor, bool):
        return "sim" if valor else "nao"
    if isinstance(valor, (int, float)):
        return fmt % valor
    return str(valor)


# largura media de um caractere Arial como fracao do corpo da fonte. Serve para
# a checagem GEOMETRICA de transbordo: um nome de ambiente longo nao pode invadir
# a coluna vizinha (a prancha mente sem que o teste de substring perceba).
FATOR_LARGURA_CHAR = 0.55
FOLGA_CELULA_PX = 12          # 6 px de recuo de cada lado


def largura_texto_px(valor, size):
    """Largura aproximada do texto renderizado, em px."""
    return len(str(valor)) * FATOR_LARGURA_CHAR * size


def ajusta_a_coluna(valor, largura_coluna, size=12):
    """Trunca o texto que nao cabe na coluna, com reticencias explicitas.

    Transbordo nao e' erro de calculo, e' prancha ilegivel: o nome comprido
    passaria por cima da celula vizinha. Melhor cortar e mostrar que cortou."""
    texto_bruto = str(valor)
    disponivel = max(largura_coluna - FOLGA_CELULA_PX, 0.0)
    if largura_texto_px(texto_bruto, size) <= disponivel:
        return texto_bruto
    max_chars = int(disponivel / (FATOR_LARGURA_CHAR * size))
    if max_chars <= 3:
        return texto_bruto[:max(max_chars, 1)]
    return texto_bruto[:max_chars - 3] + "..."


def _tabela(partes, x, y, colunas, linhas, largura_total):
    """Desenha uma tabela simples. colunas: [(titulo, largura, ancora)]."""
    cursor = x
    for titulo, largura, _ancora in colunas:
        partes.append(texto(cursor + 6, y, titulo, 12, anchor="start",
                            weight="bold"))
        cursor += largura
    partes.append(linha(x, y + 8, x + largura_total, y + 8, 1.2))
    fila = y + 8
    for celulas, cor in linhas:
        fila += LINHA_H
        cursor = x
        for (valor, (_titulo, largura, ancora)) in zip(celulas, colunas):
            if ancora == "end":
                px = cursor + largura - 6
            elif ancora == "middle":
                px = cursor + largura / 2
            else:
                px = cursor + 6
            partes.append(texto(px, fila, ajusta_a_coluna(valor, largura), 12,
                                anchor=ancora, color=cor))
            cursor += largura
        partes.append(linha(x, fila + 6, x + largura_total, fila + 6, 0.4,
                            "#cbd5e1"))
    return fila


def quadro_ambientes_svg(arquitetura) -> str:
    """Programa de ambientes com a previsao de carga da NBR 5410 9.5.2."""
    ambientes = arquitetura.get("ambientes") or []
    colunas = [("Ambiente", 190, "start"), ("Tipo", 130, "start"),
               ("Area (m2)", 90, "end"), ("Perim. (m)", 90, "end"),
               ("Ilum. (VA)", 90, "end"), ("Tomadas", 80, "end"),
               ("TUG (VA)", 90, "end"), ("Criterio 9.5.2.2.1", 170, "start")]
    largura_total = sum(c[1] for c in colunas)
    largura = largura_total + 2 * MARGEM
    altura = CABECALHO_Y + LINHA_H * (len(ambientes) + 4) + 60
    partes = abre_svg(largura, altura,
                      "PREVISAO DE CARGA - NBR 5410:2004 9.5.2")
    partes.append(texto(largura / 2, 56,
                        "Programa de ambientes (%d) - area util %s m2"
                        % (len(ambientes),
                           _num((arquitetura.get("totais") or {}).get(
                               "area_util_m2"))),
                        13))
    linhas = []
    for ambiente in ambientes:
        cor = "#111" if ambiente.get("geometria_ok") else COR_DEFICIT
        linhas.append(([
            ambiente.get("nome"),
            ambiente.get("tipo"),
            _num(ambiente.get("area_m2")),
            _num(ambiente.get("perimetro_m")),
            _num(ambiente.get("carga_iluminacao_va"), "%.0f"),
            _num(ambiente.get("n_tomadas_min"), "%d"),
            _num(ambiente.get("carga_tomadas_va"), "%.0f"),
            ambiente.get("criterio_tomadas") or "GEOMETRIA INVALIDA",
        ], cor))
    fila = _tabela(partes, MARGEM, CABECALHO_Y, colunas, linhas, largura_total)

    totais = arquitetura.get("totais") or {}
    fila += LINHA_H + 6
    partes.append(linha(MARGEM, fila - 18, MARGEM + largura_total, fila - 18, 1.2))
    partes.append(texto(MARGEM + 6, fila,
                        "TOTAL: iluminacao %s VA + tomadas %s VA em %s ponto(s)"
                        % (_num(totais.get("carga_iluminacao_va"), "%.0f"),
                           _num(totais.get("carga_tomadas_va"), "%.0f"),
                           _num(totais.get("n_tomadas_min"), "%d")),
                        13, anchor="start", weight="bold"))
    if totais.get("alternativa_9_5_2_2_2_disponivel"):
        fila += LINHA_H
        partes.append(texto(
            MARGEM + 6, fila,
            "9.5.2.2.2: o conjunto molhado tem %s pontos (> 6). A norma ADMITE "
            "600 VA ate dois pontos (%s VA) - nao adotado."
            % (_num(totais.get("pontos_molhados"), "%d"),
               _num(totais.get("carga_tomadas_va_alternativa"), "%.0f")),
            12, anchor="start", color="#92400e"))
    partes.append("</svg>")
    return "\n".join(partes)


def conferencia_svg(conferencia) -> str:
    """Minimo normativo x declarado, por ambiente, com o deficit destacado."""
    registros = conferencia.get("por_ambiente") or []
    colunas = [("Ambiente", 200, "start"), ("Criterio", 150, "start"),
               ("Tomadas min", 110, "end"), ("Tomadas decl.", 110, "end"),
               ("Luz min", 90, "end"), ("Luz decl.", 90, "end"),
               ("Situacao", 130, "start")]
    largura_total = sum(c[1] for c in colunas)
    largura = largura_total + 2 * MARGEM
    altura = CABECALHO_Y + LINHA_H * (len(registros) + 5) + 60
    partes = abre_svg(largura, altura,
                      "CONFERENCIA DA PREVISAO - NBR 5410:2004 9.5.2")
    totais = conferencia.get("totais") or {}
    partes.append(texto(largura / 2, 56,
                        "%s tomada(s) exigida(s) / %s declarada(s)"
                        % (_num(totais.get("tomadas_minimo"), "%d"),
                           _num(totais.get("tomadas_declaradas"), "%d")), 13))
    linhas = []
    for registro in registros:
        falta_tug = registro["tomadas_declaradas"] < registro["tomadas_minimo"]
        falta_luz = registro["pontos_luz_declarados"] < registro["pontos_luz_minimo"]
        cor = COR_DEFICIT if (falta_tug or falta_luz) else COR_OK
        situacao = "ATENDE"
        if falta_tug and falta_luz:
            situacao = "FALTAM TUG E LUZ"
        elif falta_tug:
            situacao = "FALTAM %d TUG" % (registro["tomadas_minimo"]
                                          - registro["tomadas_declaradas"])
        elif falta_luz:
            situacao = "FALTA PONTO DE LUZ"
        linhas.append(([
            registro["ambiente"], registro["criterio_tomadas"],
            _num(registro["tomadas_minimo"], "%d"),
            _num(registro["tomadas_declaradas"], "%d"),
            _num(registro["pontos_luz_minimo"], "%d"),
            _num(registro["pontos_luz_declarados"], "%d"),
            situacao,
        ], cor))
    fila = _tabela(partes, MARGEM, CABECALHO_Y, colunas, linhas, largura_total)
    fila += LINHA_H + 6
    orfaos = (conferencia.get("totais") or {}).get("pontos_orfaos") or 0
    if orfaos:
        partes.append(texto(
            MARGEM + 6, fila,
            "%d ponto(s) declarado(s) em ambiente inexistente no programa"
            % orfaos, 12, anchor="start", color=COR_DEFICIT))
        fila += LINHA_H
    partes.append(texto(
        MARGEM + 6, fila,
        "Resultado: %s" % ("previsao atendida" if conferencia.get("ok")
                           else "previsao NAO atendida"),
        13, anchor="start", weight="bold",
        color=COR_OK if conferencia.get("ok") else COR_DEFICIT))
    partes.append("</svg>")
    return "\n".join(partes)


def esquema_hidraulico_svg(hidraulica) -> str:
    """Esquema das tres redes com os DN calculados (sem geometria inventada)."""
    redes = hidraulica.get("redes") or {}
    largura, altura = 900, 520
    partes = abre_svg(largura, altura, "ESQUEMA HIDRAULICO - CASA RESIDENCIAL")
    partes.append(texto(largura / 2, 56,
                        "NBR 5626:2020 (agua fria) / NBR 8160 (esgoto) / "
                        "NBR 10844 (pluvial)", 12))
    blocos = []
    agua = redes.get("agua_fria")
    if agua:
        itens = ["Q = %s L/s (%s)" % (_num(agua["Q_Ls"]), agua["metodo"]),
                 "DN %s mm ; v = %s m/s (max %s)"
                 % (_num(agua["DN_mm"], "%.0f"), _num(agua["v_real_ms"]),
                    _num(agua["v_max_ms"], "%.1f"))]
        pressao = agua.get("pressao")
        if pressao:
            itens.append("pressao residual %s kPa (min %s kPa) - %s%s"
                         % (_num(pressao["p_residual_kPa"], "%.0f"),
                            _num(pressao["p_min_kPa"], "%.0f"),
                            "OK" if pressao["OK"] else "INSUFICIENTE",
                            " [A CONFIRMAR p_alim]"
                            if pressao.get("p_alim_default") else ""))
        blocos.append(("AGUA FRIA", itens, "#1d4ed8"))
    esgoto = redes.get("esgoto")
    if esgoto:
        itens = ["UHC = %s ; ramal DN %s ; coletor DN %s a %s%%"
                 % (_num(esgoto["uhc"], "%.1f"),
                    _num(esgoto["ramal_DN_mm"], "%.0f"),
                    _num(esgoto["coletor_DN_mm"], "%.0f"),
                    _num(esgoto["declividade_pct"], "%.1f")),
                 "ventilacao: ramal DN %s ; coluna DN %s"
                 % (_num(esgoto["ventilacao_ramal_DN_mm"], "%.0f"),
                    _num(esgoto["ventilacao_coluna_DN_mm"], "%.0f"))]
        if "tubo_queda_DN_mm" in esgoto:
            itens.append("tubo de queda DN %s (%s pavimentos)"
                         % (_num(esgoto["tubo_queda_DN_mm"], "%.0f"),
                            _num(esgoto["pavimentos"], "%d")))
        if (esgoto["ramal_saturado"] or esgoto["coletor_saturado"]
                or esgoto["ventilacao_saturada"]):
            itens.append("TABELA SATURADA - subdividir o trecho")
        blocos.append(("ESGOTO E VENTILACAO", itens, "#78350f"))
    pluvial = redes.get("pluvial")
    if pluvial:
        itens = ["cobertura %s m2 em %s ponto(s) -> %s m2/ponto"
                 % (_num(pluvial["area_m2"], "%.1f"),
                    _num(pluvial["n_condutores"], "%d"),
                    _num(pluvial["area_por_ponto_m2"])),
                 "Q = %s L/min ; i = %s mm/h%s"
                 % (_num(pluvial["Q_Lmin"], "%.0f"),
                    _num(pluvial["i_mm_h"], "%.0f"),
                    " [A CONFIRMAR]" if pluvial["i_default"] else ""),
                 "condutor DN %s ; calha DN %s"
                 % (_num(pluvial["condutor_DN_mm"], "%.0f"),
                    _num(pluvial["calha_DN_mm"], "%.0f"))]
        if pluvial["condutor_saturado"] or pluvial["calha_saturada"]:
            itens.append("TABELA SATURADA - mais pontos de descida")
        blocos.append(("AGUAS PLUVIAIS", itens, "#0e7490"))

    y = 100
    for titulo, itens, cor in blocos:
        altura_bloco = 34 + LINHA_H * len(itens)
        partes.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" '
                      'stroke="%s" stroke-width="1.5"/>'
                      % (MARGEM, y, largura - 2 * MARGEM, altura_bloco, cor))
        partes.append(texto(MARGEM + 12, y + 24, titulo, 14, anchor="start",
                            weight="bold", color=cor))
        for indice, item in enumerate(itens):
            partes.append(texto(MARGEM + 24, y + 24 + LINHA_H * (indice + 1),
                                item, 12, anchor="start"))
        y += altura_bloco + 20
    if not blocos:
        partes.append(texto(largura / 2, 200,
                            "nenhuma rede dimensionada: entradas ausentes", 14))
    partes.append("</svg>")
    return "\n".join(partes)


def telhado_tesoura_svg(telhado) -> str:
    """Elevacao da tesoura Howe + quadro de pecas e reacoes (G66).

    Desenha os nos calculados (sem inventar posicao: tudo vem de
    `geometria_nos` e das barras verificadas). Reprovada sai em
    vermelho, com o motivo - prancha que esconde reprova mente."""
    nos = telhado.get("geometria_nos") or {}
    barras = telhado.get("barras") or []
    xs = [p[0] for p in nos.values()]
    ys = [p[1] for p in nos.values()]
    xmin, xmax = min(xs), max(xs)
    hmax = max(ys) if ys else 1.0
    largura, topo_y, escala_area_h = 920, 120, 300
    esc = (largura - 2 * MARGEM) / max(xmax - xmin, 1e-9)

    def _px(x, y):
        return (MARGEM + (x - xmin) * esc,
                topo_y + escala_area_h - y * esc)

    cor_grupo = {"banzo_sup": "#7c2d12", "banzo_inf": "#7c2d12",
                 "montante": "#15803d", "diagonal": "#1d4ed8"}
    ok_geral = bool(telhado.get("ATENDE"))
    partes = abre_svg(largura, topo_y + escala_area_h + 350,
                      "TESOURA HOWE - NBR 7190-1 (%s)" % (
                          "ATENDE" if ok_geral else "REPROVA"))
    for barra in barras:
        try:
            n1, n2 = barra["barra"].split("-")
        except (KeyError, ValueError):
            continue
        if n1 not in nos or n2 not in nos:
            continue
        x1, y1 = _px(*nos[n1])
        x2, y2 = _px(*nos[n2])
        cor = "#b91c1c" if not barra.get("OK", True) else cor_grupo.get(
            barra.get("grupo"), "#111")
        partes.append(linha(x1, y1, x2, y2, 3.0, cor))
    for nid, (x, y) in nos.items():
        px, py = _px(x, y)
        partes.append(texto(px, py - 8, nid, 10, anchor="middle"))
    partes.append(texto(
        largura / 2, topo_y + escala_area_h + 30,
        "vao %.2f m ; %d tesouras ; reacao G=%.2f Q=%.2f kN por tesoura" % (
            telhado.get("vao_m", 0.0), telhado.get("n_tesouras", 0),
            (telhado.get("descida") or {}).get(
                "reacao_por_tesoura_kN", {}).get("G_kN", 0.0),
            (telhado.get("descida") or {}).get(
                "reacao_por_tesoura_kN", {}).get("Q_kN", 0.0)), 12))
    # G71: o caso de alivio e' dito na folha (renderizar-e-olhar): sem
    # vento, a linha diz que a cadeia e' gravitacional; com vento, o
    # arrancamento por tesoura e a situacao da ancoragem.
    desc = telhado.get("descida") or {}
    if telhado.get("vento_ativo"):
        arr = desc.get("arrancamento_por_tesoura_kN") or {}
        anc = telhado.get("ancoragem") or {}
        partes.append(texto(
            largura / 2, topo_y + escala_area_h + 46,
            "uplift: arrancamento L=%.2f R=%.2f kN por tesoura ; "
            "ancoragem %s (%s)" % (
                arr.get("L_kN", 0.0), arr.get("R_kN", 0.0),
                "ATENDE" if anc.get("OK") else "REPROVA",
                anc.get("tipo", "nao declarada")), 12))
    else:
        partes.append(texto(
            largura / 2, topo_y + escala_area_h + 46,
            "sem vento declarado: cadeia gravitacional (G66)", 12))
    # G73: o sistema do no e' dito na folha (renderizar-e-olhar): a
    # situacao da ligacao nao se herda do veredito global.
    contra_folha = telhado.get("contraventamento_6_6") or {}
    partes.append(texto(
        largura / 2, topo_y + escala_area_h + 70,
        "contraventamento 6.6: F1d=%.3f kN (Nd=%.2f/150) ; Fd=%.3f kN ((2/3).%d.F1d) ; Kbrmin=%.1f kN/m ; peca nao verificada" % (
            contra_folha.get("F1d_kN", 0.0),
            contra_folha.get("Nd_governante_kN", 0.0),
            contra_folha.get("Fd_extremidade_kN", 0.0),
            telhado.get("n_tesouras", 0),
            contra_folha.get("Kbrmin_kN_m", 0.0)), 12))
    lig_folha = telhado.get("ligacoes") or {}
    partes.append(texto(
        largura / 2, topo_y + escala_area_h + 58,
        "ligacao %s: %s (apoio %s, no %s)" % (
            lig_folha.get("sistema", "chapa_aco"),
            "ATENDE" if lig_folha.get("OK") else "REPROVA",
            "ATENDE" if (lig_folha.get("apoio") or {}).get("OK")
            else "REPROVA",
            "ATENDE" if (lig_folha.get("no_critico") or {}).get("OK")
            else "REPROVA"), 12))
    # "Volume total": a coluna vizinha e' POR TESOURA e esta e' o telhado
    # inteiro (x n_tesouras). Duas grandezas lado a lado com um titulo
    # so dizendo qual e' qual e' rotulo dirigindo a leitura da geometria.
    colunas = [("Peca", 150, "start"), ("Secao (cm)", 110, "middle"),
               ("L/tesoura (m)", 120, "end"),
               ("Volume total (m3)", 140, "end"),
               ("Situacao", 130, "start")]
    largura_total = sum(c[1] for c in colunas)
    x0 = (largura - largura_total) / 2
    y0 = topo_y + escala_area_h + 86
    # Situacao POR PECA, nao o veredito global repetido cinco vezes: a
    # coluna diz respeito a linha, e um telhado com uma barra reprovada
    # nao pode carimbar REPROVA nas quatro que passam.
    ok_grupo = {}
    for b in telhado.get("barras") or []:
        g = b.get("grupo", "-")
        ok_grupo[g] = ok_grupo.get(g, True) and bool(b.get("OK"))
        for chave in ("dimensoes_9_2_1", "esbeltez_9_3"):
            sub = b.get(chave)
            if isinstance(sub, dict):
                ok_grupo[g] = ok_grupo[g] and bool(sub.get("OK", True))
    terca_r = telhado.get("terca")
    if isinstance(terca_r, dict):
        ok_grupo["terca"] = bool(terca_r.get("OK"))
    linhas = []
    for peca in telhado.get("pecas") or []:
        grupo = peca.get("grupo", "-")
        ok_p = bool(ok_grupo.get(grupo, ok_geral))
        linhas.append(([
            grupo,
            "%dx%d" % (round(float(peca.get("b_m", 0)) * 100),
                       round(float(peca.get("h_m", 0)) * 100)),
            "%.2f" % float(peca.get("L_por_tesoura_m", 0)),
            "%.3f" % (float(peca.get("vol_por_tesoura_m3", 0))
                      * telhado.get("n_tesouras", 0)),
            "ATENDE" if ok_p else "REPROVA"],
            COR_OK if ok_p else COR_DEFICIT))
    _tabela(partes, x0, y0, colunas, linhas, largura_total)
    partes.append("</svg>")
    return "\n".join(partes)


def _layout_para_planta(result, turnkey=None):
    """O layout que a planta baixa desenha, e de onde ele veio (G78).

    Prioridade: 1. `result["layout_canonico"]` (o adaptador ja conferiu o
    espelho contra o canonico); 2. `turnkey.arquitetura.layout` validado aqui
    contra o programa; 3. o layout eletrico validado que viaja no resultado.
    Devolve (layout, proveniencia, erros). `layout` so vem preenchido quando
    valido; nunca ha retangulo inventado.
    """
    import layout_ambientes as la

    arquitetura = (result or {}).get("arquitetura")
    canonico = (result or {}).get("layout_canonico")
    if isinstance(canonico, dict) and canonico.get("ok") \
            and canonico.get("proveniencia"):
        # o adaptador conferiu espelho x canonico; o retangulo a desenhar e'
        # o canonico quando declarado, senao o espelho validado
        turnkey = turnkey if isinstance(turnkey, dict) else {}
        arq = turnkey.get("arquitetura") if isinstance(turnkey, dict) else None
        bruto = (arq.get("layout") if isinstance(arq, dict) else None)
        if isinstance(bruto, dict):
            import bim_casa_residencial as bim

            validacao = bim.validar_layout(bruto, arquitetura)
            if validacao["ok"]:
                return validacao["layout"], "arquitetura.layout", []
            return None, "arquitetura.layout", list(validacao["errors"])
        eletrico = ((result or {}).get("eletrico") or {}).get("circuits") or {}
        validacao = eletrico.get("layout_validation") or {}
        if validacao.get("ok") and isinstance(validacao.get("layout"), dict):
            return validacao["layout"], "eletrico.circuits.layout", []
        return None, None, list(validacao.get("errors") or [])

    # sem a conferencia do adaptador (chamada direta, fora do Loop): valida o
    # canonico aqui, com a mesma regra do BIM, e cai no espelho eletrico
    turnkey = turnkey if isinstance(turnkey, dict) else {}
    arq = turnkey.get("arquitetura")
    bruto = (arq.get("layout") if isinstance(arq, dict) else None)
    if isinstance(bruto, dict):
        import bim_casa_residencial as bim

        validacao = bim.validar_layout(bruto, arquitetura)
        if validacao["ok"]:
            return validacao["layout"], "arquitetura.layout", []
        return None, "arquitetura.layout", list(validacao["errors"])
    eletrico = ((result or {}).get("eletrico") or {}).get("circuits") or {}
    validacao = eletrico.get("layout_validation") or {}
    if validacao.get("ok") and isinstance(validacao.get("layout"), dict):
        return validacao["layout"], "eletrico.circuits.layout", []
    _ = la
    return None, None, list(validacao.get("errors") or [])


def planta_baixa_svg(arquitetura, layout) -> str:
    """Planta baixa da casa (PE-AR-02, G78): comodos posicionados.

    Desenha um retangulo por comodo do layout validado, com nome, dimensoes
    (width x depth declarados) e a area DO PROGRAMA (o numero sobre o qual a
    previsao de carga foi feita), mais as cotas gerais do envelope e um quadro
    programa x layout por ambiente (o cross-check de area, visivel na folha).

    Sem inventar parede, porta ou janela: nada disso e' declarado em lugar
    nenhum do spec, e a folha diz isso em vez de desenhar. Sem layout valido
    nao ha chamada honesta - quem chama confere antes (`_layout_para_planta`
    + `conferir_areas_programa_layout`); aqui o retangulo ja chega validado.
    """
    import layout_ambientes as la

    ambientes = (arquitetura or {}).get("ambientes") or []
    programa = {a["nome"]: a for a in ambientes
                if isinstance(a, dict) and a.get("geometria_ok")}
    rooms = list((layout or {}).get("rooms") or [])
    xs = [c["x_m"] for c in rooms] + [c["x_m"] + c["width_m"] for c in rooms]
    ys = [c["y_m"] for c in rooms] + [c["y_m"] + c["depth_m"] for c in rooms]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    largura_m = x_max - x_min
    profundidade_m = y_max - y_min

    largura = 1180
    ax0, ay0, aw, ah = 90, 110, 740, 500
    escala = min(aw / max(largura_m, 1e-9), ah / max(profundidade_m, 1e-9))

    def _px(x_m):
        return ax0 + (x_m - x_min) * escala

    def _py(y_m):
        return ay0 + (y_max - y_m) * escala

    totais = (arquitetura or {}).get("totais") or {}
    altura_quadro = 34 + LINHA_H * len(rooms)
    y_quadro = ay0 + ah + 64
    altura = y_quadro + altura_quadro + 3 * LINHA_H + MARGEM
    partes = abre_svg(largura, altura, "PLANTA BAIXA - CASA RESIDENCIAL")
    partes.append(texto(
        largura / 2, 56,
        "PE-AR-02 - %d ambiente(s), area util %s m2 (programa NBR 5410 9.5.2)"
        % (len(programa), _num(totais.get("area_util_m2"))), 13))

    for comodo in rooms:
        x = _px(comodo["x_m"])
        y = _py(comodo["y_m"] + comodo["depth_m"])
        w = comodo["width_m"] * escala
        h = comodo["depth_m"] * escala
        partes.append(
            '<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" fill="%s" '
            'stroke="#111" stroke-width="2"/>'
            % (x, y, w, h, COR_FUNDO_COMODO))
        nome = str(comodo.get("name") or comodo.get("id"))
        if largura_texto_px(nome, 12) > w - FOLGA_CELULA_PX:
            nome = ajusta_a_coluna(nome, w, 12)
        partes.append(texto(x + 8, y + 18, nome, 12, anchor="start",
                            weight="bold"))
        registro = programa.get(comodo.get("id")) \
            or programa.get(comodo.get("name")) or {}
        partes.append(texto(
            x + 8, y + 33, "%.2f x %.2f m" % (
                comodo["width_m"], comodo["depth_m"]), 10, anchor="start",
            color="#555"))
        partes.append(texto(x + 8, y + 47, "area %s m2" % _num(
            registro.get("area_m2")), 10, anchor="start", color="#555"))

    # cotas gerais do envelope (o que foi declarado: os extremos do layout)
    y_cota = ay0 + ah + 24
    partes.append(linha(ax0, y_cota, ax0 + largura_m * escala, y_cota, 1.2,
                        COR_COTA))
    partes.append(texto(ax0 + largura_m * escala / 2, y_cota + 16,
                        "%.2f m" % largura_m, 11, color=COR_COTA))
    partes.append(linha(ax0 - 24, ay0, ax0 - 24, ay0 + profundidade_m * escala,
                        1.2, COR_COTA))
    partes.append(texto(ax0 - 30, ay0 + profundidade_m * escala / 2,
                        "%.2f m" % profundidade_m, 11, anchor="end",
                        color=COR_COTA))

    # quadro programa x layout: o cross-check de area, desenhado na folha
    colunas = [("Ambiente", 220, "start"), ("Dimensoes (m)", 150, "start"),
               ("Area programa (m2)", 150, "end"),
               ("Area layout (m2)", 140, "end")]
    largura_total = sum(c[1] for c in colunas)
    linhas = []
    for comodo in rooms:
        registro = programa.get(comodo.get("id")) \
            or programa.get(comodo.get("name")) or {}
        area_layout = float(comodo["width_m"]) * float(comodo["depth_m"])
        area_programa = registro.get("area_m2")
        ok = (isinstance(area_programa, (int, float))
              and abs(area_layout - float(area_programa))
              <= la.TOL_AREA_REL * max(area_layout, float(area_programa)))
        linhas.append(([
            str(comodo.get("name") or comodo.get("id")),
            "%.2f x %.2f" % (comodo["width_m"], comodo["depth_m"]),
            _num(area_programa),
            "%.2f" % area_layout,
        ], "#111" if ok else COR_DEFICIT))
    _tabela(partes, ax0, y_quadro, colunas, linhas, largura_total)

    rodape = y_quadro + altura_quadro + LINHA_H
    partes.append(texto(
        ax0, rodape,
        "Paredes, portas, janelas e cobertura nao declaradas: fora do escopo - "
        "a folha mostra os retangulos de ambiente, nao o executivo.", 11,
        anchor="start", color="#555"))
    partes.append(texto(
        ax0, rodape + LINHA_H,
        "Retangulos do layout declarado (canonico: turnkey.arquitetura.layout); "
        "areas do programa de arquitetura.", 11, anchor="start",
        color="#555"))
    # resumo lateral (count-driven: o que foi desenhado, contado)
    rx = 900
    partes.append('<rect x="%d" y="%d" width="232" height="150" fill="white" '
                  'stroke="#111" stroke-width="1"/>' % (rx - 24, ay0 - 28))
    for i, item in enumerate(["RESUMO", "",
                              "Comodos desenhados: %d" % len(rooms),
                              "Area util (programa): %s m2" % _num(
                                  totais.get("area_util_m2")),
                              "Envelope: %.2f x %.2f m" % (
                                  largura_m, profundidade_m),
                              "Escala do desenho: 1 px = %.3f m"
                              % (1.0 / escala)]):
        partes.append(texto(rx + (80 if i == 0 else 0), ay0 + i * 20, item,
                            13 if i == 0 else 11,
                            anchor="middle" if i == 0 else "start",
                            weight="bold" if i == 0 else "normal"))
    partes.append("</svg>")
    return "\n".join(partes)


def motivos_arquitetura_faltante(turnkey, site=None):
    """Triagem G78 (PE-AR-01 e PE-AR-03): o que falta, nomeado, sem arbitrar.

    Implantacao precisa de lote (dimensoes, recuos, orientacao - `site.lote`
    na raiz do spec); cortes e fachadas precisam de niveis (cota de
    soleira/terreno) alem do pe-direito. O spec persistido nao declara nenhum
    dos dois - e mesmo que declarasse, ainda nao ha emissor: a folha fica
    `not_available` com o dado que falta nomeado, nunca um recuo arbitrado
    ou uma cota de soleira inventada.
    """
    turnkey = turnkey if isinstance(turnkey, dict) else {}
    if not isinstance(site, dict):
        site = turnkey.get("site") if isinstance(
            turnkey.get("site"), dict) else {}
    lote = site.get("lote")
    if isinstance(lote, dict) and lote.get("dimensoes_m") \
            and lote.get("recuos_m") and lote.get("orientacao"):
        motivo_lote = ("not_available: sem emissor de implantacao nesta "
                       "rodada (PE-AR-01)")
    else:
        motivo_lote = ("not_available: lote nao declarado "
                       "(site.lote com dimensoes_m, recuos_m e orientacao) e "
                       "sem emissor de implantacao nesta rodada (PE-AR-01)")
    niveis = turnkey.get("niveis")
    if isinstance(niveis, dict) and niveis.get("soleira_m") is not None:
        motivo_cortes = ("not_available: sem emissor de cortes/fachadas "
                         "nesta rodada (PE-AR-03)")
    else:
        motivo_cortes = ("not_available: niveis nao declarados (cota de "
                         "soleira/terreno) e sem emissor de cortes/fachadas "
                         "nesta rodada (PE-AR-03)")
    return {"implantacao.svg": motivo_lote,
            "cortes-fachadas.svg": motivo_cortes}


# ---------------------------------------------------------------------------
# CONCRETO DA CASA (G100) - reuso por primitivas, nao por copia
# ---------------------------------------------------------------------------
# PE-CO-02/03/04 da casa saem das MESMAS funcoes que desenham o predio
# (o precedente e' a planta de formas, que ja sai de desenho_pavimento
# dentro de gerar_desenhos_casa). Medido no G100: a casa de concreto
# calcula vigas verificadas tramo a tramo (G34), laje dimensionada por
# laje_concreto.dimensiona_laje e fundacao por pilar por
# fundacao_edificio.dimensiona - os mesmos contratos que os emissores do
# predio leem. Nenhuma primitiva nova, nenhum desenho duplicado: estes
# tres wrappers so adaptam a chave (a casa publica `vigas`, o predio le
# `vigas_verificacao`) e o titulo.
#
# A armadilha medida: na casa em alvenaria portante as vigas saem vazias
# (por_linha == [], G61) e a fundacao sai por linha (sapata corrida, sem
# por_pilar) - chamar a primitiva do predio com esse dado emitiria a
# folha correta e vazia. Aqui a ausencia vira ValueError com o dado
# nomeado, e gerar_desenhos_casa a registra em `skipped`, nunca em disco.


def armacao_vigas_pilares_casa_svg(estrutura, titulo=None):
    """PE-CO-02 da casa: a combinada de armacao vigas+pilares (G110, N:1).

    Le `estrutura["vigas"]` (o `por_linha` de `estrutura_casa.verifica_vigas`,
    verificado desde o G34) mais `estrutura["pilares"]` (o dict por pilar de
    `pilar_continuo.dimensiona`, P11..P43) e delega a
    `desenho_pavimento.prancha_armacao_vigas_pilares_svg` - a mesma primitiva
    que o adaptador do predio chama. Decisao N:1: o indice PE-CO-02 promete
    "Armacao pilares/vigas" e este arquivo ja se chama
    "armacao-vigas-pilares-casa.svg" - a folha empilha as duas secoes no
    mesmo <svg> em vez de um arquivo novo (mapas, indice e lente
    varredura_indice_disco intactos). Pilares ausente/vazio nao levanta:
    a secao de pilares declara a ausencia na folha.
    """
    vigas = (estrutura or {}).get("vigas") if isinstance(
        estrutura, dict) else None
    if not isinstance(vigas, dict) or not vigas.get("por_linha"):
        raise ValueError(
            "vigas de concreto nao calculadas nesta rodada (casa em "
            "alvenaria portante: laje apoia direto nas paredes, G61; "
            "estrutura.vigas.por_linha vazio); sem tramos verificados "
            "nao ha folha PE-CO-02")
    import desenho_pavimento as dp

    pilares = (estrutura or {}).get("pilares") if isinstance(
        estrutura, dict) else None
    tit = titulo or ("ARMACAO DE VIGAS E PILARES - CASA RESIDENCIAL "
                     "(%d tramos VERIFICADOS / %d pilares VERIFICADOS)"
                     % (int(vigas.get("n_tramos") or 0),
                        len(pilares) if isinstance(pilares, dict) else 0))
    return dp.prancha_armacao_vigas_pilares_svg(vigas, pilares, titulo=tit)


def detalhes_concreto_casa_svg(estrutura, titulo=None):
    """PE-CO-03 da casa: a planta da laje do predio, com o dado da casa
    (G100).

    Le `estrutura["laje"]` (o dict de `laje_concreto.dimensiona_laje`, o
    mesmo produtor que alimenta a PE-CO-03 do predio) e delega a
    `desenho_concreto.planta_laje_svg` - a mesma funcao que o adaptador do
    predio chama. Sem laje dimensionada nao ha detalhe honesto.
    """
    _ = titulo
    laje = (estrutura or {}).get("laje") if isinstance(
        estrutura, dict) else None
    if not isinstance(laje, dict) or laje.get("lx") is None:
        raise ValueError(
            "laje nao dimensionada nesta rodada (estrutura.laje ausente); "
            "sem painel dimensionado nao ha folha PE-CO-03")
    import desenho_concreto as dc
    lajes = (estrutura or {}).get("lajes_por_painel") if isinstance(
        estrutura, dict) else None
    # G111, opcao (a): com todos os paineis detalhados a folha lista os
    # N quadros; resultado antigo (sem a chave) segue na folha de 1.
    if isinstance(lajes, dict) and lajes.get("paineis"):
        return dc.planta_lajes_todos_paineis_svg(lajes)
    return dc.planta_laje_svg(laje)


def fundacao_locacao_formas_casa_svg(estrutura, titulo=None):
    """PE-CO-04 da casa: a planta de locacao/formas do predio, com o dado
    da casa (G100).

    Le `estrutura["fundacao"]` (o dict de `fundacao_edificio.dimensiona`)
    mais `estrutura` (com `pavimento`, para os vaos) e delega a
    `desenho_fundacao_edificio.planta_fundacao_svg` - a mesma funcao do
    G80. So vale no caminho com `por_pilar`; a fundacao por linha
    (sapata corrida da alvenaria portante) precisa de emissor proprio e
    continua declarada com o dado nomeado.
    """
    fundacao = (estrutura or {}).get("fundacao") if isinstance(
        estrutura, dict) else None
    if not isinstance(fundacao, dict) or not fundacao.get("por_pilar"):
        por_linha = isinstance(fundacao, dict) and fundacao.get("por_linha")
        detalhe = ("fundacao por linha (sapata corrida, sem por_pilar): "
                   "sem emissor de locacao por linha nesta rodada"
                   if por_linha else
                   "fundacao nao dimensionada nesta rodada "
                   "(sondagem/tensao nao declarada)")
        raise ValueError(
            "%s; sem pilares dimensionados nao ha folha PE-CO-04" % detalhe)
    import desenho_fundacao_edificio as dfe

    return dfe.planta_fundacao_svg(fundacao, estrutura, titulo=titulo)


def gerar_desenhos_casa(result, out_dir, turnkey=None, site=None) -> dict:
    """Escreve as pranchas da casa em `out_dir`.

    Retorna ``{"files": [...], "skipped": {...}}``. Cada prancha ausente traz o
    motivo; nenhuma sai vazia fingindo conteudo.

    `turnkey` (opcional, o spec normalizado): com ele, o layout canonico da
    arquitetura e' validado aqui e a planta baixa sai dele; sem ele, vale o
    layout eletrico validado que viaja no resultado. A triagem de implantacao
    e cortes (PE-AR-01/PE-AR-03) tambem precisa dele (e de `site`, o bloco de
    sitio na raiz do spec); sem os dois essas folhas ficam sem motivo neste
    dicionario e o hook da casa completa o laco."""
    destino = Path(out_dir)
    destino.mkdir(parents=True, exist_ok=True)
    gerados = []
    ignorados = {}
    resultado = result or {}

    arquitetura = resultado.get("arquitetura")
    if isinstance(arquitetura, dict) and arquitetura.get("ambientes"):
        caminho = destino / "quadro-ambientes.svg"
        caminho.write_text(quadro_ambientes_svg(arquitetura), encoding="utf-8")
        gerados.append("quadro-ambientes.svg")
    else:
        ignorados["quadro-ambientes.svg"] = "programa_de_arquitetura_ausente"

    eletrico = resultado.get("eletrico") or {}
    conferencia = eletrico.get("conferencia_nbr5410") if isinstance(
        eletrico, dict) else None
    if isinstance(conferencia, dict) and conferencia.get("por_ambiente"):
        caminho = destino / "conferencia-nbr5410.svg"
        caminho.write_text(conferencia_svg(conferencia), encoding="utf-8")
        gerados.append("conferencia-nbr5410.svg")
    else:
        ignorados["conferencia-nbr5410.svg"] = "conferencia_nao_executada"

    hidraulica = resultado.get("hidraulica")
    if isinstance(hidraulica, dict) and hidraulica.get("redes"):
        caminho = destino / "esquema-hidraulico.svg"
        caminho.write_text(esquema_hidraulico_svg(hidraulica), encoding="utf-8")
        gerados.append("esquema-hidraulico.svg")
    else:
        ignorados["esquema-hidraulico.svg"] = "rede_hidraulica_nao_dimensionada"

    # PLANTA DE FORMAS (G13): sai do MESMO desenhista do pavimento-tipo do
    # edificio - a malha de pilares, vigas e paineis de laje de uma casa e a de
    # um predio tem o mesmo desenho, e um segundo desenhista para a mesma planta
    # seria a segunda descricao que envelhece.
    estrutura = resultado.get("estrutura")
    if isinstance(estrutura, dict) and estrutura.get("pavimento"):
        import desenho_pavimento as dp

        caminho = destino / "planta-formas.svg"
        dp.gerar_planta_formas(
            estrutura["pavimento"], str(caminho),
            descida=estrutura.get("descida"),
            titulo="PLANTA DE FORMAS - CASA RESIDENCIAL")
        gerados.append("planta-formas.svg")
    else:
        ignorados["planta-formas.svg"] = "estrutura_nao_calculada"

    # CONCRETO DA CASA (G100): PE-CO-02/03/04 saem das primitivas do predio
    # (wrappers acima, sem copia). Sem dado a folha sai nomeada, nunca vazia.
    if isinstance(estrutura, dict) and estrutura.get("pavimento"):
        for _nome, _fn in (
                ("armacao-vigas-pilares-casa.svg",
                 armacao_vigas_pilares_casa_svg),
                ("detalhes-concreto-casa.svg", detalhes_concreto_casa_svg),
                ("fundacao-locacao-formas-casa.svg",
                 fundacao_locacao_formas_casa_svg)):
            try:
                caminho = destino / _nome
                caminho.write_text(_fn(estrutura), encoding="utf-8")
            except Exception as exc:                            # noqa: BLE001
                ignorados[_nome] = str(exc)
            else:
                gerados.append(_nome)
    else:
        for _nome in ("armacao-vigas-pilares-casa.svg",
                      "detalhes-concreto-casa.svg",
                      "fundacao-locacao-formas-casa.svg"):
            ignorados[_nome] = "estrutura_nao_calculada"

    # planta baixa (PE-AR-02, G78): sai do layout declarado - o canonico da
    # arquitetura quando ha turnkey, senao o espelho eletrico validado. Sem
    # posicao declarada nao ha planta honesta; com layout que diverge do
    # programa, desenhar seria publicar uma casa e calcular outra.
    import layout_ambientes as la

    arquitetura_planta = resultado.get("arquitetura")
    if isinstance(arquitetura_planta, dict) and arquitetura_planta.get(
            "ambientes"):
        layout, _prov, erros_layout = _layout_para_planta(resultado, turnkey)
        if layout is None:
            if erros_layout:
                ignorados["planta-baixa.svg"] = next(
                    (e.get("code", "layout_recusado")
                     for e in erros_layout if isinstance(e, dict)),
                    "layout_recusado")
            else:
                ignorados["planta-baixa.svg"] = \
                    "posicoes_dos_ambientes_nao_declaradas"
        else:
            conf = la.conferir_areas_programa_layout(
                arquitetura_planta.get("ambientes"), layout.get("rooms"))
            if not conf["ok"]:
                ignorados["planta-baixa.svg"] = next(
                    (e.get("code", "layout_diverge_do_programa")
                     for e in conf["erros"]), "layout_diverge_do_programa")
            else:
                caminho = destino / "planta-baixa.svg"
                caminho.write_text(
                    planta_baixa_svg(arquitetura_planta, layout),
                    encoding="utf-8")
                gerados.append("planta-baixa.svg")
    else:
        ignorados["planta-baixa.svg"] = "programa_de_arquitetura_ausente"

    if turnkey is not None:
        # triagem PE-AR-01/PE-AR-03 (G78): sem dado e sem emissor, o motivo
        # escrito - nunca um recuo arbitrado fingindo implantacao.
        ignorados.update(motivos_arquitetura_faltante(turnkey, site))

    # ALVENARIA PORTANTE (G62): elevacao + fiadas saem do MESMO desenhista
    # das paredes calculadas - um desenho_alvenaria.py com escape proprio
    # seria o berco do bug de dupla-escapa (todo texto por texto()).
    if isinstance(estrutura, dict) and (estrutura.get("alvenaria") or {}).get(
            "por_linha"):
        import desenho_alvenaria as da

        pranchas = da.gerar_pranchas_alvenaria(estrutura, destino)
        gerados.extend(pranchas["files"])
        ignorados.update(pranchas["skipped"])
    else:
        ignorados["elevacao-paredes.svg"] = "parede_portante_nao_calculada"
        ignorados["planta-fiadas.svg"] = "parede_portante_nao_calculada"

    # TELHADO DE MADEIRA (G66): elevacao da tesoura calculada + quadro de
    # pecas. Sem telhado calculado a prancha fica indisponivel com motivo.
    telhado = (estrutura or {}).get("telhado") if isinstance(
        estrutura, dict) else None
    if isinstance(telhado, dict) and telhado.get("geometria_nos"):
        caminho = destino / "telhado-tesoura.svg"
        caminho.write_text(telhado_tesoura_svg(telhado), encoding="utf-8")
        gerados.append("telhado-tesoura.svg")
    else:
        ignorados["telhado-tesoura.svg"] = "telhado_madeira_nao_calculado"
    return {"files": gerados, "skipped": ignorados}


def _selftest():
    import xml.etree.ElementTree as ET

    import arquitetura_residencial as ar
    import hidraulica_residencial as hr
    from casa_residencial import conferir_previsao_nbr5410

    arquitetura = ar.rodar({"ambientes": [
        {"nome": "Sala <estar>", "tipo": "sala", "largura_m": 4.0,
         "comprimento_m": 5.0},
        {"nome": "Cozinha", "tipo": "cozinha", "largura_m": 2.5,
         "comprimento_m": 3.6}]})
    hidraulica = hr.rodar({
        "aparelhos_agua": {"pia": 1, "lavatorio": 1},
        "aparelhos_esgoto": {"pia": 1, "lavatorio": 1},
        "agua": {"L_real_m": 12.0, "p_alim_kPa": 120.0},
        "cobertura": {"area_m2": 80.0, "i_mm_h": 150.0}})
    conferencia = conferir_previsao_nbr5410(arquitetura, {"points": [
        {"id": "L1", "room": "Sala <estar>", "kind": "lighting",
         "power_va": 280.0}]})
    for svg in (quadro_ambientes_svg(arquitetura), conferencia_svg(conferencia),
                esquema_hidraulico_svg(hidraulica)):
        # SVG e' XML: o nome com '<' cru quebraria o parse
        ET.fromstring(svg)
    print("desenho_casa_residencial self-test PASSED (3 pranchas XML-validas)")


if __name__ == "__main__":
    _selftest()
