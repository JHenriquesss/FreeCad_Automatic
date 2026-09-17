"""Camada GRÁFICA da elétrica residencial: unifilar, quadro de cargas e planta.

Consome o resultado JÁ VALIDADO de `residencial_eletrica.run_residential_electrical`
(demanda + padrão de entrada + designs dimensionados) e escreve SVG puro-Python.
Não calcula nada: se um número não está no resultado, o desenho diz
"A CONFIRMAR" em vez de inventar. As primitivas vêm de `desenho_svg_base`, as
mesmas do unifilar industrial (uma implementação de escape XML, não duas).

A planta 2D exige `circuits.layout` validado; sem layout declarado ela não é
emitida, porque posicionar cômodo e ponto sem dado do usuário seria invenção.
"""

from __future__ import annotations

from pathlib import Path

import layout_eletrico_residencial as lay
from desenho_svg_base import (
    PALETA_CIRCUITO,
    abre_svg,
    linha,
    sym_disjuntor,
    sym_dps,
    sym_lampada,
    sym_lampada_cor,
    sym_terra,
    sym_tomada,
    sym_tomada_cor,
    texto,
)


A_CONFIRMAR = "A CONFIRMAR"
_KIND_LABEL = {"lighting": "Iluminação", "tug": "TUG", "tue": "TUE"}


def _governante_label(condutor: dict) -> str:
    """Nome legível do critério que ditou a seção.

    `piso_tabela` só aparece quando a seção subiu até o menor valor tabelado,
    acima do mínimo que a norma admite: a prancha diz os dois números para o
    revisor não procurar folga térmica onde não houve critério térmico.
    """
    gov = condutor.get("governante")
    if not gov:
        return A_CONFIRMAR
    if gov == "piso_tabela":
        return "piso da tabela (norma %s mm²)" % _num(
            condutor.get("secao_minima_norma"), "%g").replace(".", ",")
    return {"secao_minima": "seção mínima (Tab.47)",
            "ampacidade": "ampacidade",
            "queda": "queda de tensão",
            "curto": "curto-circuito"}.get(gov, str(gov))


class LayoutIndisponivel(RuntimeError):
    """A planta 2D foi pedida sem layout declarado e validado."""


def _designs(result):
    circuits = (result or {}).get("circuits") or {}
    designs = circuits.get("designs")
    return list(designs) if isinstance(designs, list) else []


def _points_by_id(result):
    circuits = (result or {}).get("circuits") or {}
    points = circuits.get("points")
    if not isinstance(points, list):
        return {}
    return {point["id"]: point for point in points
            if isinstance(point, dict) and isinstance(point.get("id"), str)}


def _cor_do_circuito(index):
    return PALETA_CIRCUITO[index % len(PALETA_CIRCUITO)]


def _design_kinds(design, points):
    kinds = [points.get(point_id, {}).get("kind") for point_id in design["point_ids"]]
    return [kind for kind in kinds if kind]


def _simbolo_do_design(design, points):
    kinds = _design_kinds(design, points)
    return sym_lampada if kinds and all(k == "lighting" for k in kinds) else sym_tomada


def _largura_est(texto_dado, size):
    """Largura estimada da caixa do rotulo, na MESMA regua do censo G129.

    `desenho_svg_base.colisoes_de_rotulo_svg` estima largura ~0,6*size por
    caractere; o emissor que respeita essa regua ao posicionar nao entrega
    par novo ao censo. A lente segue medindo o SVG emitido de forma
    independente (parse do XML) - se o posicionamento falhar, o par aparece
    no censo e o portao fica vermelho.
    """
    return max(len(str(texto_dado)) * size * 0.6, size * 0.6)


def _caixa_texto(x, y, txt, size=13, anchor="middle"):
    """Caixa estimada (x0, y0, x1, y1) de um <text>, na regua do G129."""
    larg = _largura_est(txt, size)
    alt = size * 1.1
    if anchor == "middle":
        x0, x1 = x - larg / 2.0, x + larg / 2.0
    elif anchor == "end":
        x0, x1 = x - larg, x
    else:
        x0, x1 = x, x + larg
    return (x0, y - alt, x1, y + alt * 0.3)


def _colide(caixa, outras):
    return any(caixa[0] < b[2] and b[0] < caixa[2]
               and caixa[1] < b[3] and b[1] < caixa[3] for b in outras)


def _quebra_celula(valor, largura_px, size):
    """Quebra o texto da celula em linhas que cabem em `largura_px`.

    Regua do G129 (0,6*size por caractere): nenhuma linha devolvida excede
    a largura da coluna sob a mesma metrica que o censo usa. Quebra por
    palavra; palavra sozinha mais longa que a coluna e fatiada (nunca
    corta conteudo fora). Devolve [texto] quando ja cabe (caso comum).
    """
    por_char = size * 0.6
    cabem = max(int(largura_px // por_char), 1)
    texto_dado = str(valor)
    # lista separada por virgula (ex. comodos do circuito): cada item fica
    # inteiro na linha - partir "Dormitorio 01" no meio confunde a leitura.
    if ", " in texto_dado:
        itens = [p for p in texto_dado.split(", ") if p]
        linhas, atual = [], ""
        for pos, item in enumerate(itens):
            pedaco = item + ("," if pos < len(itens) - 1 else "")
            if len(pedaco) > cabem:          # item sozinho maior que a coluna
                for parte in _quebra_celula(pedaco, largura_px, size):
                    if atual and len(atual) + 1 + len(parte) <= cabem:
                        atual = (atual + " " + parte).strip()
                    else:
                        if atual:
                            linhas.append(atual)
                        atual = parte
                continue
            candidato = (atual + " " + pedaco).strip()
            if len(candidato) <= cabem or not atual:
                atual = candidato
            else:
                linhas.append(atual)
                atual = pedaco
        if atual or not linhas:
            linhas.append(atual)
        return linhas
    palavras = texto_dado.split(" ")
    linhas, atual = [], ""
    for palavra in palavras:
        while len(palavra) > cabem:           # palavra maior que a coluna
            if atual:
                linhas.append(atual)
                atual = ""
            linhas.append(palavra[:cabem])
            palavra = palavra[cabem:]
        candidato = (atual + " " + palavra).strip()
        if len(candidato) <= cabem or not atual:
            atual = candidato
        else:
            linhas.append(atual)
            atual = palavra
    if atual or not linhas:
        linhas.append(atual)
    return linhas


def _num(value, fmt="%.1f"):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return A_CONFIRMAR
    return fmt % float(value)


def _reprovado(design):
    """True quando o próprio resultado declara que o circuito não atende.

    O desenho NÃO pode mostrar barra verde sobre um cálculo reprovado: se o
    condutor ou a proteção vierem com OK falso, a prancha diz REPROVA.
    """
    conductor_ok = (design.get("conductor") or {}).get("OK")
    protection_ok = (design.get("protection") or {}).get("OK")
    return conductor_ok is False or protection_ok is False


def circuitos_nao_dimensionados(result):
    """Circuitos que o cálculo REJEITOU, com o código do motivo.

    Um circuito que falhou não entra em `designs` — sem esta lista ele sumiria
    do desenho em silêncio, e a prancha pareceria completa faltando circuito
    (o padrão do quadro de materiais que desapareceu sem aviso).
    """
    erros = ((result or {}).get("circuits") or {}).get("errors")
    if not isinstance(erros, list):
        return []
    ausentes = []
    vistos = set()
    for erro in erros:
        if not isinstance(erro, dict):
            continue
        design_id = erro.get("design_id")
        if not isinstance(design_id, str) or design_id in vistos:
            continue
        vistos.add(design_id)
        ausentes.append({"design_id": design_id,
                         "code": str(erro.get("code") or "erro")})
    return ausentes


def _entry(result):
    entry = ((result or {}).get("service_entry") or {}).get("entry")
    return entry if isinstance(entry, dict) else None


def unifilar_residencial_svg(result) -> str:
    """Diagrama unifilar residencial: ramal de entrada -> QD -> circuitos."""
    designs = _designs(result)
    points = _points_by_id(result)
    entry = _entry(result)

    largura = max(940, 200 + 150 * max(len(designs), 1))
    altura = 640
    s = abre_svg(largura, altura, "DIAGRAMA UNIFILAR - INSTALAÇÃO RESIDENCIAL")

    xg = 130
    y = 76
    tensao = (entry or {}).get("voltage_system") or A_CONFIRMAR
    s.append(texto(xg, y, "ENTRADA BT %s V" % tensao, 13))
    s.append(texto(xg, y + 18, "ramal aéreo - concessionária", 11, color="#555"))
    s.append(linha(xg, y + 26, xg, y + 56))

    # medidor / padrão de entrada
    s.append(f'<circle cx="{xg}" cy="{y + 72}" r="14" fill="white" stroke="#111" '
             f'stroke-width="1.5"/>')
    s.append(texto(xg, y + 77, "kWh", 10, weight="bold"))
    if entry:
        s.append(texto(xg + 28, y + 66,
                       "Padrão %s - ramal %s mm²" % (entry.get("row", A_CONFIRMAR),
                                                     entry.get("entry_conductors",
                                                               A_CONFIRMAR)),
                       11, "start"))
        s.append(texto(xg + 28, y + 82,
                       "eletroduto ø%s mm" % entry.get("conduit_mm", A_CONFIRMAR),
                       11, "start", color="#555"))
    else:
        s.append(texto(xg + 28, y + 74, "padrão de entrada " + A_CONFIRMAR,
                       11, "start", color="#a00"))
    s.append(linha(xg, y + 86, xg, y + 112))

    # disjuntor geral do padrão
    s.append(sym_disjuntor(xg, y + 128))
    geral = entry.get("breaker_a") if entry else None
    s.append(texto(xg + 24, y + 124,
                   "DISJ. GERAL %s A" % (geral if geral is not None else A_CONFIRMAR),
                   12, "start", "bold"))
    # DPS derivado do barramento
    s.append(linha(xg, y + 128, xg + 205, y + 128, 1.0))
    s.append(sym_dps(xg + 215, y + 128))
    s.append(texto(xg + 215, y + 155, "DPS cl. II", 10))
    s.append(sym_terra(xg + 215, y + 167))
    s.append(linha(xg, y + 137, xg, y + 210))

    ybus = y + 210
    xb0, xb1 = 90, largura - 90
    s.append(linha(xb0, ybus, xb1, ybus, 5.0))
    s.append(texto(xb0, ybus - 12, "QD - QUADRO DE DISTRIBUIÇÃO", 14, "start", "bold"))
    demanda = (((result or {}).get("calculation") or {}).get("demand") or {}).get(
        "final_kva")
    s.append(texto(xb1, ybus - 12,
                   "demanda %s kVA" % _num(demanda, "%.2f"), 11, "end"))

    yfim = ybus + 190
    for index, design in enumerate(designs):
        x = 200 + index * 150
        cor = _cor_do_circuito(index)
        s.append(linha(x, ybus, x, ybus + 26, 1.6, cor))
        s.append(sym_disjuntor(x, ybus + 42))
        disjuntor = (design.get("protection") or {}).get("disjuntor") or {}
        s.append(texto(x, ybus + 66, "%s A" % _num(disjuntor.get("IN"), "%.0f"), 11))
        s.append(linha(x, ybus + 51, x, ybus + 78, 1.6, cor))
        ybranch = ybus + 78
        dr = (design.get("protection") or {}).get("dr") or {}
        if dr.get("requer_DR"):
            s.append(f'<rect x="{x - 16}" y="{ybranch}" width="32" height="20" '
                     f'fill="white" stroke="#111" stroke-width="1.3"/>')
            s.append(texto(x, ybranch + 14, "DR", 10, weight="bold"))
            s.append(texto(x, ybranch + 34,
                           "%s mA" % _num(dr.get("In_dif_mA"), "%.0f"), 10,
                           color="#555"))
            ybranch += 44
        s.append(linha(x, ybranch, x, yfim - 16, 1.6, cor))
        condutor = design.get("conductor") or {}
        s.append(texto(x + 6, (ybranch + yfim) / 2.0,
                       "%s mm²" % _num(condutor.get("secao_mm2"), "%g"), 10, "start",
                       color=cor))
        simbolo = _simbolo_do_design(design, points)
        s.append(simbolo(x, yfim))
        s.append(texto(x, yfim + 32, design["id"], 11, weight="bold"))
        carga = (design.get("load") or {}).get("power_va")
        s.append(texto(x, yfim + 48, "%s VA" % _num(carga, "%.0f"), 10, color="#555"))
        if _reprovado(design):
            s.append(texto(x, yfim + 64, "REPROVA", 11, weight="bold", color="#a00"))

    # aterramento do QD
    yt = altura - 60
    s.append(linha(xb0 + 10, ybus, xb0 + 10, yt - 12))
    s.append(sym_terra(xb0 + 10, yt))
    aterramento = (entry or {}).get("grounding_conductor_mm2")
    s.append(texto(xb0 + 34, yt,
                   "ATERRAMENTO  %s mm²" % _num(aterramento, "%g"), 12, "start"))
    s.append(texto(xb0 + 34, yt + 18,
                   "curto-circuito: %s" % _curto_texto(result), 11, "start",
                   color="#a00"))
    ausentes = circuitos_nao_dimensionados(result)
    if ausentes:
        s.append(texto(xb0, 56,
                       "%d CIRCUITO(S) NÃO DIMENSIONADO(S) - NÃO DESENHADO(S): %s"
                       % (len(ausentes),
                          ", ".join("%s (%s)" % (item["design_id"], item["code"])
                                    for item in ausentes)),
                       12, "start", "bold", "#a00"))
    s.append("</svg>")
    return "\n".join(s)


def _curto_texto(result):
    scope = ((result or {}).get("circuits") or {}).get("scope") or {}
    estado = scope.get("short_circuit_evaluation")
    if estado == "implemented":
        return "verificado"
    return "não avaliado (Icc não declarado)"


def quadro_cargas_residencial_svg(result) -> str:
    """Quadro de cargas residencial: uma linha por circuito dimensionado."""
    designs = _designs(result)
    points = _points_by_id(result)
    cabecalho = ("CIRCUITO", "PONTOS", "CÔMODO", "TIPO", "CARGA", "I (A)",
                 "SEÇÃO", "DISJ.", "ΔV (%)", "GOVERN.", "DR", "STATUS")
    linhas = [cabecalho]
    for design in designs:
        selecionados = [points.get(pid, {}) for pid in design["point_ids"]]
        comodos = sorted({p.get("room", A_CONFIRMAR) for p in selecionados})
        tipos = sorted({_KIND_LABEL.get(p.get("kind"), A_CONFIRMAR)
                        for p in selecionados})
        condutor = design.get("conductor") or {}
        disjuntor = (design.get("protection") or {}).get("disjuntor") or {}
        dr = (design.get("protection") or {}).get("dr") or {}
        linhas.append((
            design["id"],
            "%d" % len(design["point_ids"]),
            ", ".join(comodos),
            ", ".join(tipos),
            "%s VA" % _num((design.get("load") or {}).get("power_va"), "%.0f"),
            _num((design.get("load") or {}).get("current_a"), "%.2f"),
            "%s mm²" % _num(condutor.get("secao_mm2"), "%g"),
            "%s A" % _num(disjuntor.get("IN"), "%.0f"),
            _num(condutor.get("dv_pct"), "%.2f"),
            _governante_label(condutor),
            "sim" if dr.get("requer_DR") else "não",
            "REPROVA" if _reprovado(design) else "atende",
        ))

    ausentes = circuitos_nao_dimensionados(result)
    # G129: nenhuma celula pode transbordar a coluna. A rodada real com 7
    # comodos punha "Area de servico, Banheiro, Circulacao, Cozinha,
    # Dormitorio 01, Dormitorio 02, Sala" por cima de TIPO/CARGA/I/SECAO/
    # DISJ. (7 pares no censo, PNG casa-quadro-cargas.png) - a fixture
    # sintetica do guardiao da folha tem comodos curtos e nunca acusou.
    # Cada celula quebra em linhas que cabem na coluna (regua do G129) e a
    # altura da linha acompanha a celula mais alta; entrelinha 17 px em
    # corpo 11 (caixa do estimador: 1,1*size + 0,3*size = 15,4 < 17).
    largura = 1300
    corpo = 11
    entrelinha = 17
    topo_texto = 19
    pe_linha = 9
    # A coluna GOVERN. guarda a largura do rotulo MAIS LONGO que ela pode
    # receber ("piso da tabela (norma 1,5 mm2)", 31 caracteres, com guardiao
    # proprio em phase6b que cobra a string inteira): 230 px uteis >=
    # 31*11*0,6 na regua do G129, sem quebrar a frase.
    colunas = [20, 120, 180, 320, 430, 530, 590, 680, 750, 820, 1060, 1130]
    bordas = colunas[1:] + [largura - 40]
    larguras = [b - (c + 6) - 4 for c, b in zip(colunas, bordas)]
    # desenha primeiro para medir as alturas (a linha acompanha a celula
    # mais alta); depois emite com os y acumulados.
    blocos = []
    for linha_dados in linhas:
        celulas = [_quebra_celula(valor, larg, corpo)
                   for valor, larg in zip(linha_dados, larguras)]
        blocos.append(celulas)
    alturas = [topo_texto + (max(len(c) for c in cel) - 1) * entrelinha
               + pe_linha for cel in blocos]
    y0 = 56
    altura = (y0 + sum(alturas) + 60
              + (38 + 16 * len(ausentes) if ausentes else 0))
    s = abre_svg(largura, altura, "QUADRO DE CARGAS - INSTALAÇÃO RESIDENCIAL",
                 18)
    y = y0
    for i, (linha_dados, celulas, alt) in enumerate(zip(linhas, blocos,
                                                        alturas)):
        fundo = "#dfe7ef" if i == 0 else ("#f4f4f0" if i % 2 else "white")
        s.append(f'<rect x="20" y="{y:.0f}" width="{largura - 40}" '
                 f'height="{alt}" fill="{fundo}" stroke="#888" '
                 f'stroke-width="0.6"/>')
        reprova = i > 0 and linha_dados[-1] == "REPROVA"
        for c, (valor, partes) in enumerate(zip(linha_dados, celulas)):
            peso = "bold" if i == 0 else "normal"
            cor = "#a00" if (reprova and c == len(linha_dados) - 1) else "#111"
            for k, parte in enumerate(partes):
                s.append(texto(colunas[c] + 6, y + topo_texto + k * entrelinha,
                               parte, corpo, "start", peso, cor))
        y += alt

    rodape = y + 22
    entry = _entry(result)
    s.append(texto(24, rodape,
                   "Padrão de entrada: %s | disjuntor geral %s A | aterramento %s mm²"
                   % ((entry or {}).get("row", A_CONFIRMAR),
                      _num((entry or {}).get("breaker_a"), "%.0f"),
                      _num((entry or {}).get("grounding_conductor_mm2"), "%g")),
                   11, "start"))
    s.append(texto(24, rodape + 18,
                   "Curto-circuito: %s | seções e proteções por NBR 5410 (6.2.5, "
                   "6.2.6.1.1, 6.2.7)" % _curto_texto(result), 11, "start",
                   color="#555"))
    for i, item in enumerate(ausentes):
        s.append(texto(24, rodape + 54 + i * 16,
                       "%s - %s" % (item["design_id"], item["code"]), 11, "start",
                       color="#a00"))
    if ausentes:
        s.append(texto(24, rodape + 38, "CIRCUITOS NÃO DIMENSIONADOS (ausentes "
                                        "da tabela acima):", 11, "start", "bold",
                       "#a00"))
    s.append("</svg>")
    return "\n".join(s)


def planta_eletrica_residencial_svg(result) -> str:
    """Planta 2D: cômodos declarados + pontos posicionados + eletrodutos ao QD."""
    validacao = _layout_validado(result)
    if not validacao["ok"]:
        raise LayoutIndisponivel(
            "planta 2D exige circuits.layout válido; motivo: %s"
            % ("layout não declarado" if not validacao["declared"]
               else [item["code"] for item in validacao["errors"]]))
    layout = validacao["layout"]
    designs = _designs(result)
    points = _points_by_id(result)
    posicoes = {item["id"]: item for item in layout["points"]}

    caixa = lay.bounds(layout)
    largura_m = caixa["x_max"] - caixa["x_min"]
    profundidade_m = caixa["y_max"] - caixa["y_min"]
    largura, altura = 1180, 860
    ax0, ay0, aw, ah = 70, 110, 700, 520
    escala = min(aw / largura_m, ah / profundidade_m)

    def px(x_m):
        return ax0 + (x_m - caixa["x_min"]) * escala

    def py(y_m):
        return ay0 + (caixa["y_max"] - y_m) * escala

    cor_de = {}
    for index, design in enumerate(designs):
        for point_id in design["point_ids"]:
            cor_de[point_id] = _cor_do_circuito(index)

    s = abre_svg(largura, altura, "PLANTA DE ILUMINAÇÃO E TOMADAS - RESIDENCIAL")
    obstaculos = []
    for room in layout["rooms"]:
        x = px(room["x_m"])
        y = py(room["y_m"] + room["depth_m"])
        s.append(f'<rect x="{x:.0f}" y="{y:.0f}" '
                 f'width="{room["width_m"] * escala:.0f}" '
                 f'height="{room["depth_m"] * escala:.0f}" fill="#fafafa" '
                 f'stroke="#111" stroke-width="2"/>')
        # rotulo no canto superior esquerdo do comodo: no centro ele colidia com
        # os pontos e com o quadro (visto ao RENDERIZAR a prancha)
        s.append(texto(x + 8, y + 18, room["name"], 12, "start", color="#666"))
        s.append(texto(x + 8, y + 33,
                       "%.2f x %.2f m" % (room["width_m"], room["depth_m"]), 10,
                       "start", color="#999"))
        obstaculos.append(_caixa_texto(x + 8, y + 18, room["name"], 12,
                                       "start"))
        obstaculos.append(_caixa_texto(
            x + 8, y + 33, "%.2f x %.2f m" % (room["width_m"],
                                              room["depth_m"]), 10, "start"))

    quadro = layout["board"]
    qx, qy = px(quadro["x_m"]), py(quadro["y_m"])
    obstaculos.append(_caixa_texto(qx + 14, qy + 4, quadro["id"], 11,
                                   "start"))
    for index, design in enumerate(designs):
        cor = _cor_do_circuito(index)
        for point_id in design["point_ids"]:
            posicao = posicoes.get(point_id)
            if posicao is None:
                continue
            s.append(f'<line x1="{qx:.0f}" y1="{qy:.0f}" '
                     f'x2="{px(posicao["x_m"]):.0f}" y2="{py(posicao["y_m"]):.0f}" '
                     f'stroke="{cor}" stroke-width="1" stroke-dasharray="5,4" '
                     f'opacity="0.7"/>')

    for point_id, posicao in posicoes.items():
        cor = cor_de.get(point_id, "#111")
        kind = points.get(point_id, {}).get("kind")
        sx, sy = px(posicao["x_m"]), py(posicao["y_m"])
        if kind == "lighting":
            s.append(sym_lampada_cor(sx, sy, cor))
        else:
            s.append(sym_tomada_cor(sx, sy, cor))
        # G129: etiquetas de pontos proximos (luz + tomada no mesmo ponto do
        # layout, tags vizinhas) saiam sobrepostas e ilegíveis - 12 pares no
        # censo, PNG casa-planta-eletrica.png (ex. L-BAN/T-BAN-01/TUE-CHUV no
        # mesmo (x, y)). A etiqueta tenta deslocamentos fixos, em ordem, e
        # fica no primeiro que nao encosta em rotulo de comodo, no quadro nem
        # em etiqueta ja posta (regua do G129); se nenhum servir, sai no
        # padrao e o censo acusa (ausencia declarada pelo portao, nunca
        # silencio).
        larg_tag = _largura_est(point_id, 9)
        tentativas = [(12, -8), (12, 9), (-larg_tag - 12, -8),
                      (-larg_tag - 12, 9), (12, -25), (12, 26),
                      (-larg_tag - 12, -25), (-larg_tag - 12, 26),
                      (30, -8), (-larg_tag - 30, -8)]
        tx, ty = sx + 12, sy - 8
        for dx, dy in tentativas:
            cand = _caixa_texto(sx + dx, sy + dy, point_id, 9, "start")
            if not _colide(cand, obstaculos):
                tx, ty = sx + dx, sy + dy
                break
        obstaculos.append(_caixa_texto(tx, ty, point_id, 9, "start"))
        s.append(texto(tx, ty, point_id, 9, "start", color=cor))
    s.append(sym_disjuntor(qx, qy))
    s.append(texto(qx + 14, qy + 4, quadro["id"], 11, "start", "bold"))

    lx, ly = 900, 150
    s.append(f'<rect x="{lx - 24}" y="{ly - 32}" width="256" height="196" '
             f'fill="white" stroke="#111" stroke-width="1"/>')
    s.append(texto(lx + 104, ly - 10, "LEGENDA", 14, weight="bold"))
    s.append(sym_lampada_cor(lx, ly + 20, "#111"))
    s.append(texto(lx + 24, ly + 24, "Ponto de luz", 12, "start"))
    s.append(sym_tomada_cor(lx, ly + 52, "#111"))
    s.append(texto(lx + 24, ly + 56, "Tomada (TUG/TUE)", 12, "start"))
    s.append(sym_disjuntor(lx, ly + 88))
    s.append(texto(lx + 24, ly + 92, "Quadro de distribuição", 12, "start"))
    s.append(f'<line x1="{lx - 10}" y1="{ly + 120}" x2="{lx + 10}" '
             f'y2="{ly + 120}" stroke="#111" stroke-width="1" '
             f'stroke-dasharray="5,4"/>')
    s.append(texto(lx + 24, ly + 124, "Ligação ponto-quadro", 12, "start"))
    s.append(texto(lx + 24, ly + 140,
                   "(esquemática: NÃO é traçado", 10, "start", color="#a00"))
    s.append(texto(lx + 24, ly + 153,
                   "de eletroduto)", 10, "start", color="#a00"))

    rx, ry = 900, 350
    resumo = ["RESUMO", "",
              "Cômodos: %d" % len(layout["rooms"]),
              "Pontos posicionados: %d" % len(posicoes),
              "Circuitos: %d" % len(designs),
              "Área declarada: %.2f m²" % _area(layout),
              "", "Escala do desenho: 1 px = %.3f m" % (1.0 / escala)]
    s.append(f'<rect x="{rx - 24}" y="{ry - 28}" width="256" height="180" '
             f'fill="white" stroke="#111" stroke-width="1"/>')
    for i, item in enumerate(resumo):
        s.append(texto(rx + (104 if i == 0 else 0), ry + i * 18, item,
                       13 if i == 0 else 11, "middle" if i == 0 else "start",
                       "bold" if i == 0 else "normal"))

    ty = ay0 + ah + 60
    s.append(texto(ax0, ty - 16, "CIRCUITOS - BITOLA, PROTEÇÃO E COMPRIMENTO",
                   12, "start", "bold"))
    colunas = [ax0, ax0 + 130, ax0 + 230, ax0 + 330, ax0 + 430, ax0 + 540]
    for cx, titulo in zip(colunas, ["CIRCUITO", "PONTOS", "SEÇÃO", "DISJUNTOR",
                                    "COMPRIM.", "STATUS"]):
        s.append(texto(cx, ty, titulo, 10, "start", "bold", "#555"))
    for index, design in enumerate(designs):
        yy = ty + 18 + index * 16
        cor = _cor_do_circuito(index)
        condutor = design.get("conductor") or {}
        disjuntor = (design.get("protection") or {}).get("disjuntor") or {}
        valores = [design["id"], "%d" % len(design["point_ids"]),
                   "%s mm²" % _num(condutor.get("secao_mm2"), "%g"),
                   "%s A" % _num(disjuntor.get("IN"), "%.0f"),
                   "%s m" % _num(design.get("declared_length_m"), "%.2f"),
                   "REPROVA" if _reprovado(design) else "atende"]
        for j, (cx, valor) in enumerate(zip(colunas, valores)):
            cor_texto = cor if j == 0 else (
                "#a00" if valor == "REPROVA" else "#111")
            s.append(texto(cx, yy, valor, 10, "start", color=cor_texto))
    s.append("</svg>")
    return "\n".join(s)


def _area(layout):
    return sum(room["width_m"] * room["depth_m"] for room in layout["rooms"])


def _layout_validado(result):
    circuits = (result or {}).get("circuits") or {}
    validacao = circuits.get("layout_validation")
    if isinstance(validacao, dict) and "ok" in validacao:
        return validacao
    return {"declared": False, "ok": False, "errors": [], "layout": None}


def gerar_desenhos_residenciais(result, out_dir) -> dict:
    """Escreve os SVG do executivo residencial em `out_dir`.

    Retorna ``{"files": [...], "skipped": {...}}``. O unifilar e o quadro de
    cargas sempre saem (dependem só do JSON de cálculo); a planta só sai com
    layout válido, e o motivo da ausência é registrado, nunca silenciado.
    """
    destino = Path(out_dir)
    destino.mkdir(parents=True, exist_ok=True)
    gerados = []
    # G155: cada folha reprovada declara o veredito (lido do `circuits`
    # pela fonte unica, nunca decidido aqui). O `circuits` do
    # dimensionamento declara "ok" e os erros por design_id; sem ele, a
    # fonte nao declara veredito e a folha diz que esta indisponivel.
    # ATENDE = byte-identico.
    try:
        from veredito_folha_g152 import injetar_veredito_no_svg as _inj155
    except ImportError:
        _inj155 = lambda _s, _f: _s

    def _fonte155(res):
        cir = (res or {}).get("circuits") if isinstance(res, dict) else None
        return cir if isinstance(cir, dict) else (res if isinstance(res, dict) else {})

    for nome, funcao in (("unifilar.svg", unifilar_residencial_svg),
                         ("quadro-cargas.svg", quadro_cargas_residencial_svg)):
        caminho = destino / nome
        caminho.write_text(_inj155(funcao(result), _fonte155(result)),
                           encoding="utf-8")
        gerados.append(nome)

    ignorados = {}
    validacao = _layout_validado(result)
    if validacao["ok"]:
        caminho = destino / "planta-eletrica.svg"
        caminho.write_text(_inj155(planta_eletrica_residencial_svg(result),
                                   _fonte155(result)), encoding="utf-8")
        gerados.append("planta-eletrica.svg")
    elif not validacao["declared"]:
        ignorados["planta-eletrica.svg"] = "layout_not_declared"
    else:
        ignorados["planta-eletrica.svg"] = "invalid_layout"
    return {"files": gerados, "skipped": ignorados}


def _selftest():
    resultado = {
        "calculation": {"demand": {"final_kva": 8.58}},
        "service_entry": {"entry": {"row": "B1", "breaker_a": 50,
                                    "entry_conductors": "10 (10)",
                                    "grounding_conductor_mm2": 10,
                                    "conduit_mm": 50}},
        "circuits": {
            "points": [{"id": "L-01", "room": "sala", "kind": "lighting",
                        "power_va": 100, "voltage_v": 127}],
            "designs": [{"id": "C-L-01", "point_ids": ["L-01"],
                          "declared_length_m": 10.0,
                          "load": {"power_va": 100.0, "current_a": 0.79},
                          "conductor": {"secao_mm2": 2.5, "dv_pct": 0.1,
                                        "governante": "ampacidade", "OK": True},
                          "protection": {"disjuntor": {"IN": 6, "OK": True},
                                          "dr": {"requer_DR": False}, "OK": True}}],
            "scope": {"short_circuit_evaluation": "not_evaluated"},
        },
    }
    from xml.etree import ElementTree
    for svg in (unifilar_residencial_svg(resultado),
                quadro_cargas_residencial_svg(resultado)):
        ElementTree.fromstring(svg)
    print("desenho_eletrico_residencial self-test PASSED (unifilar + quadro, XML)")


if __name__ == "__main__":
    _selftest()
