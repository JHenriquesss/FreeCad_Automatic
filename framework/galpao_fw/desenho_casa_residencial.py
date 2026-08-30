# ============================================================================
# desenho_casa_residencial.py - O QUE ESTE MODULO DESENHA
# Pranchas SVG do adaptador residencial real (sem FreeCAD, so o JSON calculado):
#   1. quadro-ambientes.svg      - programa de ambientes + previsao de carga
#                                  NBR 5410 9.5.2 (area, perimetro, criterio);
#   2. conferencia-nbr5410.svg   - minimo normativo x declarado, por ambiente,
#                                  com o deficit destacado;
#   3. esquema-hidraulico.svg    - esquema vertical das tres redes com os DN
#                                  calculados (NBR 5626 / 8160 / 10844).
#
# O que NAO ha aqui e' planta baixa: o programa declara area e perimetro, nao
# posicoes. Desenhar comodos em posicoes inventadas seria um desenho que nao
# corresponde ao dado - a prancha ausente vira motivo explicito em 'skipped'.
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


def gerar_desenhos_casa(result, out_dir) -> dict:
    """Escreve as pranchas da casa em `out_dir`.

    Retorna ``{"files": [...], "skipped": {...}}``. Cada prancha ausente traz o
    motivo; nenhuma sai vazia fingindo conteudo."""
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

    # planta baixa: o programa declara area e perimetro, nao posicoes
    ignorados["planta-baixa.svg"] = "posicoes_dos_ambientes_nao_declaradas"
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
