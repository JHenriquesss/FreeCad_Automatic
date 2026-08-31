# ============================================================================
# hidraulica_edificio.py - AGUA, ESGOTO E PLUVIAL DO EDIFICIO MULTIPAVIMENTO
#
# `hidraulica_predial` ja tinha agua fria (NBR 5626:2020), esgoto (NBR 8160) e
# pluvial (NBR 10844) como PRIMITIVAS aferidas, e `hidraulica_residencial` ja as
# encadeava para uma CASA. O que muda num predio de nove pavimentos e' a
# VERTICAL: um reservatorio superior que alimenta todo mundo por gravidade, uma
# coluna de distribuicao que ganha pressao a cada andar que desce, e um tubo de
# queda que recolhe o esgoto de todos eles. Este modulo e' essa fronteira - nao
# reimplementa tabela nenhuma.
#
#     populacao + consumo per capita declarado
#          -> volume de consumo diario         (5626 6.5.4)
#          -> reservacao 24 h e compartimentos (6.5.6.2 / 6.5.6.5)
#          -> alimentador predial: repor em 6 h (6.7.2) -> DN por v <= 3 m/s
#          -> COLUNA DE DISTRIBUICAO: DN por vazao, pressao ESTATICA no ponto
#             mais baixo (6.9.5, teto de 400 kPa) e DINAMICA no mais alto (6.9.2)
#          -> TUBO DE QUEDA de esgoto: UHC de todas as unidades, coluna > 3 pav
#             (8160 Tab.6) + ventilacao
#          -> pluvial da cobertura (10844)
#          -> gates
#
# O QUE E' DECLARADO, e por que:
#   - CONSUMO PER CAPITA. A NBR 5626:2020 6.5.4 nao tabela consumo: manda
#     considerar "as peculiaridades de cada instalacao, as condicoes climaticas,
#     as caracteristicas de utilizacao, a tipologia do edificio e a populacao",
#     e a NOTA remete a "referencias tecnicas, manuais de orientacao de
#     concessionarias e dados historicos". Nao ha default a inventar: sem o dado
#     nao ha volume de reservacao.
#   - RESERVACAO ADOTADA. O volume do reservatorio e' projeto de arquitetura e
#     estrutura (a caixa d'agua pesa sobre a laje da cobertura); aqui ele e'
#     VERIFICADO contra as 24 h de 6.5.6.2, nao arbitrado.
#   - A POPULACAO vem da MESMA declaracao que a NBR 9077 usa (os dormitorios de
#     `incendio.pavimentos`) quando o vertical de incendio esta declarado. Duas
#     populacoes para o mesmo predio seria o defeito das duas escadas outra vez.
#
# O QUE NAO ENTRA (publicado no escopo): agua quente e seu sistema de geracao,
# reservatorio inferior + recalque (bombas), zonas de pressao e valvulas
# redutoras (6.9.8-6.9.16 - so o GATE de 400 kPa diz que elas sao necessarias),
# combate a incendio armazenado junto (a reserva de incendio sai do vertical de
# incendio e NAO e' somada aqui), e o tracado/leiaute das prumadas.
#
# Unidades: m, L, L/s, kPa, mm. STATELESS.
# CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# ============================================================================
"""Hidraulica do edificio multipavimento: reservacao superior, coluna de
distribuicao, tubo de queda e pluvial, reusando as primitivas de
hidraulica_predial (NBR 5626:2020 / 8160 / 10844)."""

from __future__ import annotations

import math

import hidraulica_predial as hp

# --- NBR 5626:2020 ---------------------------------------------------------
# 6.5.6.2: "O volume total de agua reservado deve atender no minimo 24 h de
# consumo normal no edificio".
RESERVACAO_MIN_DIAS = 1.0
# 6.5.6.3 NOTA: "recomenda-se limitar o volume total ao valor que corresponda a
# tres dias de consumo diario". E' RECOMENDACAO ("recomenda-se"), por isso sai
# como aviso e nao como gate - a norma nao a torna exigencia.
RESERVACAO_MAX_DIAS_RECOMENDADO = 3.0
# 6.5.6.5: "a excecao das residencias unifamiliares isoladas, os demais
# reservatorios elevados DEVEM ser divididos em dois ou mais compartimentos".
COMPARTIMENTOS_MIN_SUPERIOR = 2
# 6.7.2: "a vazao a considerar no abastecimento do reservatorio deve ser
# suficiente para a reposicao total do volume destinado ao consumo diario de
# agua em ate 6 h" (3 h em residencia unifamiliar).
TEMPO_REPOSICAO_H = 6.0
# 6.9.5: pressao ESTATICA nos pontos de utilizacao <= 400 kPa. E' o teto que um
# predio alto estoura: e' ele que obriga a zona de pressao.
P_EST_MAX_KPA = hp.P_EST_MAX_KPA
PESO_ESPEC_AGUA_KPA_M = hp.PESO_ESPEC_AGUA_KPA_M
# 6.9.7: sobrepressoes de transiente admitidas ate 200 kPa acima da dinamica.
SOBREPRESSAO_TRANSIENTE_MAX_KPA = 200.0
# NBR 8160 Tab.6 tem duas colunas: ate 3 pavimentos e acima de 3.
QUEDA_LIMITE_PAVIMENTOS = 3


class EntradaHidraulica(ValueError):
    """A entrada declarada nao permite dimensionar a hidraulica do edificio."""


def declarada(spec_hidraulica) -> bool:
    """Ha o minimo: consumo per capita e os aparelhos de uma unidade?

    A pergunta tem UMA resposta aqui, para que o escopo publicado pelo adaptador
    e o que o calculo faz nao usem criterios diferentes.
    """
    if not isinstance(spec_hidraulica, dict):
        return False
    unidade = spec_hidraulica.get("unidade") or {}
    return bool(spec_hidraulica.get("consumo_per_capita_L_dia")
                and isinstance(unidade, dict)
                and unidade.get("aparelhos_agua"))


def _positivo(valor):
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor) and valor > 0)


def _valida(spec):
    erros = []
    if not _positivo(spec.get("consumo_per_capita_L_dia")):
        erros.append("consumo_per_capita_L_dia deve ser > 0 (L/pessoa.dia). A "
                     "NBR 5626:2020 6.5.4 NAO tabela consumo: ele vem de "
                     "referencia tecnica, manual da concessionaria ou dado "
                     "historico, e e' declarado pelo projetista")
    unidade = spec.get("unidade")
    if not isinstance(unidade, dict):
        erros.append("hidraulica.unidade deve ser um objeto com os aparelhos de "
                     "UMA unidade autonoma")
    else:
        if not isinstance(unidade.get("aparelhos_agua"), dict) \
                or not unidade["aparelhos_agua"]:
            erros.append("hidraulica.unidade.aparelhos_agua deve listar os "
                         "aparelhos de uma unidade (Tab.B.4). Sem aparelhos nao "
                         "ha vazao, e um DN comercial plausivel nao e' projeto")
        if not _positivo(unidade.get("unidades_por_pavimento")):
            erros.append("hidraulica.unidade.unidades_por_pavimento deve ser > 0")
    reservacao = spec.get("reservacao")
    if not isinstance(reservacao, dict):
        erros.append("hidraulica.reservacao deve declarar o volume adotado")
    else:
        if not _positivo(reservacao.get("superior_L")):
            erros.append("hidraulica.reservacao.superior_L deve ser > 0 (o volume "
                         "do reservatorio superior e' projeto de arquitetura e "
                         "estrutura; aqui ele e' VERIFICADO, nao arbitrado)")
        inferior = reservacao.get("inferior_L")
        if inferior is not None and not _positivo(inferior):
            erros.append("hidraulica.reservacao.inferior_L deve ser > 0 quando "
                         "declarado")
        comp = reservacao.get("compartimentos_superior")
        if comp is not None and (not isinstance(comp, int) or isinstance(comp, bool)
                                 or comp < 1):
            erros.append("reservacao.compartimentos_superior deve ser inteiro >= 1")
    if erros:
        raise EntradaHidraulica("; ".join(erros))


def _populacao(spec, contexto):
    """A populacao do predio: declarada, ou a MESMA que a NBR 9077 usou.

    Duas populacoes para o mesmo predio e' o defeito das duas escadas em outra
    disciplina. Quando as duas sao declaradas e divergem, isso e' ERRO de
    entrada - nao se escolhe uma em silencio.
    """
    da_9077 = contexto.get("populacao_por_pavimento")
    total_9077 = (sum(linha["populacao"] for linha in da_9077)
                  if da_9077 else None)
    declarada_ = spec.get("populacao")
    if declarada_ is not None and not _positivo(declarada_):
        raise EntradaHidraulica("hidraulica.populacao deve ser > 0")
    if declarada_ is not None and total_9077 is not None \
            and int(declarada_) != int(total_9077):
        raise EntradaHidraulica(
            "hidraulica.populacao (%d) diverge da populacao calculada pela NBR "
            "9077 a partir de incendio.pavimentos (%d). O predio tem UMA "
            "populacao: corrija a declaracao divergente em vez de deixar cada "
            "disciplina dimensionar para um predio diferente"
            % (int(declarada_), int(total_9077)))
    if declarada_ is not None:
        return int(declarada_), "declarada em hidraulica.populacao"
    if total_9077 is not None:
        return int(total_9077), ("a MESMA populacao da NBR 9077 (Tab.4 sobre "
                                 "incendio.pavimentos)")
    raise EntradaHidraulica(
        "nao ha populacao: declare hidraulica.populacao, ou declare o vertical "
        "de incendio (turnkey.incendio.pavimentos), de onde ela e' lida. O "
        "consumo de agua nao e' estimavel pela area do envelope")


def _reservacao(spec, populacao):
    """Volume de consumo diario, reservacao adotada e os gates de 6.5.6."""
    per_capita = float(spec["consumo_per_capita_L_dia"])
    v_diario = populacao * per_capita
    reserv = spec["reservacao"]
    v_sup = float(reserv["superior_L"])
    v_inf = float(reserv.get("inferior_L") or 0.0)
    v_total = v_sup + v_inf
    comp = int(reserv.get("compartimentos_superior") or 1)
    return {
        "populacao": populacao,
        "consumo_per_capita_L_dia": per_capita,
        "consumo_diario_L": round(v_diario, 1),
        "superior_L": v_sup, "inferior_L": v_inf, "total_L": v_total,
        "autonomia_dias": round(v_total / v_diario, 3) if v_diario else None,
        "compartimentos_superior": comp,
        "gate_24h": {
            "OK": v_total >= v_diario * RESERVACAO_MIN_DIAS - 1e-6,
            "exigido_L": round(v_diario * RESERVACAO_MIN_DIAS, 1),
            "adotado_L": v_total,
            "referencia": "NBR 5626:2020 6.5.6.2 (minimo 24 h de consumo normal)"},
        "gate_compartimentos": {
            "OK": comp >= COMPARTIMENTOS_MIN_SUPERIOR,
            "minimo": COMPARTIMENTOS_MIN_SUPERIOR, "declarado": comp,
            "referencia": "NBR 5626:2020 6.5.6.5 (reservatorio elevado dividido "
                          "em dois ou mais compartimentos, exceto residencia "
                          "unifamiliar isolada)"},
    }


def _alimentador(reservacao, spec):
    """Alimentador predial: repor o consumo diario em ate 6 h (6.7.2)."""
    horas = float(spec.get("tempo_reposicao_h", TEMPO_REPOSICAO_H))
    if not _positivo(horas) or horas > TEMPO_REPOSICAO_H + 1e-9:
        raise EntradaHidraulica(
            "tempo_reposicao_h deve estar em (0; %.0f]: 6.7.2 exige repor o "
            "volume de consumo diario em ATE 6 h" % TEMPO_REPOSICAO_H)
    q_ls = reservacao["consumo_diario_L"] / (horas * 3600.0)
    dn = hp.dn_por_vazao(q_ls)
    dn["tempo_reposicao_h"] = horas
    dn["referencia"] = "NBR 5626:2020 6.7.2 + 6.8.3 (v <= 3 m/s)"
    return dn


def _coluna_agua(spec, contexto, n_pavimentos_servidos):
    """Coluna de distribuicao: DN, pressao estatica no pe e dinamica no topo.

    O ponto CRITICO de pressao dinamica num sistema por gravidade e' o mais ALTO
    (o menor desnivel ate o reservatorio); o critico de pressao ESTATICA e' o
    mais BAIXO (a maior coluna d'agua). Sao dois pontos diferentes, e verificar
    so um deles deixa metade do predio sem conferencia.
    """
    unidade = spec["unidade"]
    por_pav = int(unidade["unidades_por_pavimento"])
    aparelhos_unidade = dict(unidade["aparelhos_agua"])
    total = {tipo: qtd * por_pav * n_pavimentos_servidos
             for tipo, qtd in aparelhos_unidade.items()}
    coluna_spec = spec.get("coluna") or {}
    metodo = coluna_spec.get("metodo_vazao", "soma")
    dn = hp.diametro_agua(total, metodo=metodo)

    pe = contexto["pe_direito"]
    # desnivel do NA mais baixo do reservatorio ao ponto: declarado, ou derivado
    # da altura do reservatorio sobre a laje da cobertura.
    h_reserv = float(coluna_spec.get("altura_na_sobre_cobertura_m", 1.0))
    # ponto mais alto servido: ultimo pavimento servido; ponto mais baixo: 1o.
    desnivel_topo = h_reserv
    desnivel_pe = h_reserv + (n_pavimentos_servidos - 1) * pe

    p_est_pe = desnivel_pe * PESO_ESPEC_AGUA_KPA_M
    gate_estatica = {
        "OK": p_est_pe <= P_EST_MAX_KPA + 1e-9,
        "desnivel_m": round(desnivel_pe, 3),
        "p_estatica_kPa": round(p_est_pe, 1),
        "p_max_kPa": P_EST_MAX_KPA,
        "ponto": "ponto de utilizacao mais BAIXO servido pela coluna",
        "referencia": "NBR 5626:2020 6.9.5 (pressao estatica <= 400 kPa)"}
    if not gate_estatica["OK"]:
        gate_estatica["erro"] = (
            "a coluna d'agua de %.2f m produz %.0f kPa de pressao estatica, "
            "acima dos 400 kPa de 6.9.5: o edificio precisa ser dividido em "
            "ZONAS DE PRESSAO com estacoes redutoras (6.9.8 a 6.9.16), que este "
            "modulo NAO dimensiona" % (desnivel_pe, p_est_pe))

    # Dinamica no ponto mais desfavoravel: o mais ALTO, que tem o menor desnivel
    # ate o reservatorio. A VAZAO desse trecho NAO e' a da coluna inteira - o
    # trecho entre o barrilete e o ultimo pavimento so conduz a demanda DESSE
    # pavimento; a vazao total so aparece la embaixo, onde ja ha 20 m de coluna
    # d'agua sobrando. Usar a vazao total no trecho de cima seria carregar o
    # ponto mais alto com a perda de carga do predio inteiro e reprovar por
    # modelo, nao por hidraulica.
    aparelhos_topo = {tipo: qtd * por_pav for tipo, qtd in aparelhos_unidade.items()}
    dn_topo = hp.diametro_agua(aparelhos_topo, metodo=metodo)
    conexoes = coluna_spec.get("conexoes")
    l_ramal = float(coluna_spec.get("comprimento_ramal_m", 0.0))
    tipo_ponto = coluna_spec.get("tipo_ponto_critico", "geral")
    pressao = hp.verifica_pressao(
        dn_topo["Q_Ls"], dn["DN_mm"], l_ramal, 0.0, conexoes=conexoes,
        dcota_m=desnivel_topo, tipo_ponto=tipo_ponto)
    gate_dinamica = dict(pressao)
    gate_dinamica.update({
        "ponto": "ponto de utilizacao mais ALTO servido pela coluna",
        "desnivel_m": round(desnivel_topo, 3),
        "Q_do_trecho_Ls": dn_topo["Q_Ls"],
        "nota_vazao": ("o trecho ate o ponto mais alto conduz so a demanda do "
                       "ultimo pavimento, nao a da coluna inteira"),
        "referencia": "NBR 5626:2020 6.9.2 (>= 10 kPa no ponto) / 6.9.4"})
    return {
        "aparelhos_totais": total,
        "n_pavimentos_servidos": n_pavimentos_servidos,
        "unidades_por_pavimento": por_pav,
        "dn": dn,
        "gate_dn": {"OK": bool(dn["OK"]), "DN_mm": dn["DN_mm"],
                    "Q_Ls": dn["Q_Ls"], "v_real_ms": dn["v_real_ms"],
                    "metodo_vazao": metodo,
                    "referencia": "NBR 5626:2020 6.8.3 (v <= 3 m/s)"},
        "gate_pressao_estatica": gate_estatica,
        "gate_pressao_dinamica": gate_dinamica,
    }


def _esgoto(spec, n_pavimentos_servidos):
    """Tubo de queda, ventilacao e coletor predial (NBR 8160)."""
    unidade = spec["unidade"]
    aparelhos = unidade.get("aparelhos_esgoto")
    if not isinstance(aparelhos, dict) or not aparelhos:
        return None
    por_pav = int(unidade["unidades_por_pavimento"])
    total = {tipo: qtd * por_pav * n_pavimentos_servidos
             for tipo, qtd in aparelhos.items()}
    uhc, dn_min_descarga = hp.uhc_de_aparelhos(total)
    queda = hp.diametro_tubo_queda_sat(uhc, pavimentos=n_pavimentos_servidos)
    declividade = float((spec.get("esgoto") or {}).get("declividade_coletor_pct", 1.0))
    coletor = hp.diametro_coletor_sat(uhc, declividade_pct=declividade)
    ventilacao = hp.diametro_coluna_ventilacao(queda["DN_mm"])
    return {
        "aparelhos_totais": total, "uhc": uhc,
        "dn_min_ramal_descarga_mm": dn_min_descarga,
        "tubo_de_queda": queda, "coletor_predial": coletor,
        "coluna_ventilacao_DN_mm": ventilacao,
        "declividade_minima_pct": hp.declividade_minima_pct(coletor["DN_mm"]),
        "gate_queda": {
            "OK": not queda["saturado"],
            "DN_mm": queda["DN_mm"], "uhc": uhc,
            "coluna_da_tabela": ("ate %d pavimentos" % QUEDA_LIMITE_PAVIMENTOS
                                 if n_pavimentos_servidos <= QUEDA_LIMITE_PAVIMENTOS
                                 else "mais de %d pavimentos" % QUEDA_LIMITE_PAVIMENTOS),
            "saturado": queda["saturado"],
            "referencia": "NBR 8160 Tab.6"},
        "gate_coletor": {
            "OK": not coletor["saturado"],
            "DN_mm": coletor["DN_mm"], "saturado": coletor["saturado"],
            "declividade_pct": coletor["declividade_pct"],
            "referencia": "NBR 8160 Tab.7 + 4.2.3.2"},
    }


def _pluvial(spec, contexto):
    """Cobertura: vazao de projeto, calha e condutor vertical (NBR 10844)."""
    pluvial_spec = spec.get("pluvial") or {}
    area = float(pluvial_spec.get("area_contribuicao_m2",
                                  contexto["area_pavimento_m2"]))
    i = pluvial_spec.get("i_mm_h")
    # o `i_default` das primitivas compara o VALOR com o default do framework:
    # um i de sitio que por acaso valha 150 mm/h sairia rotulado como default.
    # Aqui o que vale e' se o projeto DECLAROU o dado, nao o valor que deu.
    i_declarado = i is not None
    n_descidas = int(pluvial_spec.get("n_descidas", 1))
    if n_descidas < 1:
        raise EntradaHidraulica("pluvial.n_descidas deve ser >= 1")
    area_por_descida = area / n_descidas
    calha = hp.diametro_calha(
        area_por_descida, i, pluvial_spec.get("declividade_calha_pct", 0.5))
    condutor = hp.diametro_pluvial(
        area_por_descida, calha["i_mm_h"],
        pluvial_spec.get("declividade_condutor_pct", 1.0))
    return {
        "area_contribuicao_m2": round(area, 2), "n_descidas": n_descidas,
        "area_por_descida_m2": round(area_por_descida, 2),
        "calha": calha, "condutor": condutor, "i_declarado": i_declarado,
        "gate": {
            "OK": not calha["saturado"] and not condutor["saturado"],
            "calha_DN_mm": calha["DN_mm"], "condutor_DN_mm": condutor["DN_mm"],
            "Q_Lmin": calha["Q_Lmin"], "i_mm_h": calha["i_mm_h"],
            "i_declarado": i_declarado,
            "referencia": "NBR 10844 5.3.1 + Tab.3 + Tab.4"},
    }


def dimensiona(spec_hidraulica, contexto):
    """Hidraulica do edificio: reservacao, coluna, tubo de queda e pluvial.

    spec_hidraulica: {
      'consumo_per_capita_L_dia': DECLARADO (6.5.4 nao tabela consumo);
      'populacao'  : opc - por padrao a MESMA da NBR 9077;
      'reservacao' : {'superior_L', 'inferior_L' (opc),
                      'compartimentos_superior'};
      'unidade'    : {'unidades_por_pavimento', 'aparelhos_agua' (Tab.B.4),
                      'aparelhos_esgoto' (Tab.3, opc)};
      'coluna'     : {'altura_na_sobre_cobertura_m', 'comprimento_ramal_m',
                      'conexoes', 'metodo_vazao', 'tipo_ponto_critico'};
      'esgoto'     : {'declividade_coletor_pct'};
      'pluvial'    : {'i_mm_h' (DADO DE SITIO), 'area_contribuicao_m2',
                      'n_descidas', 'declividade_calha_pct'};
      'tempo_reposicao_h': opc, <= 6 h (6.7.2).
    }
    contexto: o mesmo do vertical de incendio, com 'populacao_por_pavimento'
    quando a NBR 9077 rodou.
    """
    if not isinstance(spec_hidraulica, dict):
        raise EntradaHidraulica("hidraulica deve ser um objeto JSON")
    _valida(spec_hidraulica)
    populacao, nota_pop = _populacao(spec_hidraulica, contexto)

    # a coluna serve os pavimentos com unidades; a cobertura tecnica nao conta.
    servidos = spec_hidraulica.get("pavimentos_servidos")
    if servidos is None:
        da_9077 = contexto.get("populacao_por_pavimento")
        servidos = (sum(1 for linha in da_9077 if linha["ocupado"]) if da_9077
                    else len(contexto["pavimentos"]))
    servidos = int(servidos)
    if servidos < 1:
        raise EntradaHidraulica("pavimentos_servidos deve ser >= 1")

    reservacao = _reservacao(spec_hidraulica, populacao)
    alimentador = _alimentador(reservacao, spec_hidraulica)
    coluna = _coluna_agua(spec_hidraulica, contexto, servidos)
    esgoto = _esgoto(spec_hidraulica, servidos)
    pluvial = _pluvial(spec_hidraulica, contexto)

    gates = {
        "reservacao_24h": reservacao["gate_24h"],
        "reservacao_compartimentos": reservacao["gate_compartimentos"],
        "alimentador_predial": {
            "OK": bool(alimentador["OK"] and not alimentador["saturado"]),
            "DN_mm": alimentador["DN_mm"], "Q_Ls": alimentador["Q_Ls"],
            "v_real_ms": alimentador["v_real_ms"],
            "saturado": alimentador["saturado"],
            "referencia": alimentador["referencia"]},
        "coluna_distribuicao": coluna["gate_dn"],
        "pressao_estatica": coluna["gate_pressao_estatica"],
        "pressao_dinamica": coluna["gate_pressao_dinamica"],
        "pluvial": pluvial["gate"],
    }
    if esgoto is not None:
        gates["tubo_de_queda"] = esgoto["gate_queda"]
        gates["coletor_predial"] = esgoto["gate_coletor"]

    avisos = _avisos(spec_hidraulica, reservacao, pluvial, esgoto)
    reprovados = sorted(k for k, g in gates.items() if not g["OK"])
    return {
        "populacao": populacao, "populacao_proveniencia": nota_pop,
        "pavimentos_servidos": servidos,
        "reservacao": reservacao, "alimentador": alimentador,
        "coluna": coluna, "esgoto": esgoto, "pluvial": pluvial,
        "gates": gates, "reprovados": reprovados, "ATENDE": not reprovados,
        "escopo": _escopo(esgoto is not None),
        "avisos": avisos,
    }


def _escopo(com_esgoto):
    return {
        "agua_fria_reservacao": "implemented",
        "alimentador_predial": "implemented",
        "coluna_de_distribuicao": "implemented",
        "esgoto_tubo_de_queda": "implemented" if com_esgoto else "not_available",
        "pluvial_cobertura": "implemented",
        # nomeado em vez de omitido:
        "agua_quente": "not_available",
        "reservatorio_inferior_e_recalque": "not_available",
        "zonas_de_pressao_e_valvulas_redutoras": "not_available",
        "reserva_de_incendio_conjunta": "not_available",
        "tracado_das_prumadas": "not_available",
        "ventilacao_por_uhc_e_comprimento": "partial",
        "aprovacao_legal": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def _avisos(spec, reservacao, pluvial, esgoto):
    avisos = []
    autonomia = reservacao["autonomia_dias"]
    if autonomia is not None and autonomia > RESERVACAO_MAX_DIAS_RECOMENDADO + 1e-9:
        avisos.append({
            "code": "reservacao_acima_de_tres_dias",
            "detail": "a reservacao adotada (%.0f L) equivale a %.1f dias de "
                      "consumo. A NOTA de 6.5.6.3 RECOMENDA limitar a tres dias "
                      "para preservar a acao residual do desinfetante; acima "
                      "disso e' preciso prever meios que assegurem a "
                      "potabilidade"
                      % (reservacao["total_L"], autonomia)})
    if not reservacao["inferior_L"]:
        avisos.append({
            "code": "sem_reservatorio_inferior",
            "detail": "so ha reservatorio SUPERIOR declarado: a divisao entre "
                      "inferior e superior (6.5.6.4) e o conjunto elevatorio de "
                      "recalque nao foram avaliados. Se a rede publica nao "
                      "alimentar a cobertura por pressao propria, falta a "
                      "bomba - que este modulo nao dimensiona"})
    if not pluvial["i_declarado"]:
        avisos.append({
            "code": "intensidade_pluvial_default",
            "detail": "a intensidade de chuva usada e' o default do framework "
                      "(%.0f mm/h) e NAO o dado do sitio: a NBR 10844 Tab.5 "
                      "lista i por cidade e periodo de retorno [A CONFIRMAR]"
                      % pluvial["calha"]["i_mm_h"]})
    avisos.append({
        "code": "reserva_de_incendio_nao_somada",
        "detail": "6.5.6.2 manda considerar o volume de combate a incendio "
                  "QUANDO armazenado conjuntamente. A reserva de incendio sai do "
                  "vertical de incendio (NBR 13714) e NAO foi somada a este "
                  "volume: se os reservatorios forem o mesmo, some-os"})
    if esgoto is None:
        avisos.append({
            "code": "esgoto_nao_declarado",
            "detail": "hidraulica.unidade.aparelhos_esgoto nao declarado: o tubo "
                      "de queda, a ventilacao e o coletor predial NAO foram "
                      "dimensionados"})
    avisos.append({
        "code": "tracado_das_prumadas_nao_modelado",
        "detail": "a coluna e' dimensionada como UMA prumada servindo todos os "
                  "pavimentos. O numero real de prumadas, o seu tracado e os "
                  "ramais por unidade dependem da planta de arquitetura, que "
                  "este framework nao tem para o edificio"})
    return avisos


def relatorio_pt(resultado):
    """Quadro da hidraulica do edificio."""
    r = resultado
    res = r["reservacao"]
    col = r["coluna"]
    linhas = [
        "HIDRAULICA DO EDIFICIO MULTIPAVIMENTO - NBR 5626:2020 / 8160 / 10844",
        "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
        "  Populacao: %d pessoas (%s)" % (r["populacao"], r["populacao_proveniencia"]),
        "  Consumo: %.0f L/pessoa.dia -> %.0f L/dia (6.5.4, declarado)"
        % (res["consumo_per_capita_L_dia"], res["consumo_diario_L"]),
        "",
        "  RESERVACAO",
        "    superior %.0f L + inferior %.0f L = %.0f L (%.2f dia(s))"
        % (res["superior_L"], res["inferior_L"], res["total_L"],
           res["autonomia_dias"] or 0.0),
        "    minimo de 24 h (6.5.6.2): %.0f L -> %s"
        % (res["gate_24h"]["exigido_L"],
           "ATENDE" if res["gate_24h"]["OK"] else "REPROVA"),
        "    compartimentos do superior: %d (minimo %d, 6.5.6.5) -> %s"
        % (res["compartimentos_superior"], res["gate_compartimentos"]["minimo"],
           "ATENDE" if res["gate_compartimentos"]["OK"] else "REPROVA"),
        "",
        "  ALIMENTADOR PREDIAL (6.7.2, repor em %.0f h)" % r["alimentador"]["tempo_reposicao_h"],
        "    Q = %.3f L/s -> DN %d mm (v = %.2f m/s)"
        % (r["alimentador"]["Q_Ls"], r["alimentador"]["DN_mm"],
           r["alimentador"]["v_real_ms"]),
        "",
        "  COLUNA DE DISTRIBUICAO (%d pavimentos, %d unidade(s)/pavimento)"
        % (col["n_pavimentos_servidos"], col["unidades_por_pavimento"]),
        "    Q = %.3f L/s -> DN %d mm (v = %.2f m/s)"
        % (col["dn"]["Q_Ls"], col["dn"]["DN_mm"], col["dn"]["v_real_ms"]),
        "    pressao ESTATICA no pe: %.0f kPa (max %.0f, 6.9.5) -> %s"
        % (col["gate_pressao_estatica"]["p_estatica_kPa"], P_EST_MAX_KPA,
           "ATENDE" if col["gate_pressao_estatica"]["OK"] else "REPROVA"),
        "    pressao DINAMICA no topo: %.1f kPa (min %.0f, 6.9.2) -> %s"
        % (col["gate_pressao_dinamica"]["p_residual_kPa"],
           col["gate_pressao_dinamica"]["p_min_kPa"],
           "ATENDE" if col["gate_pressao_dinamica"]["OK"] else "REPROVA"),
    ]
    if r["esgoto"]:
        esg = r["esgoto"]
        linhas += [
            "",
            "  ESGOTO (NBR 8160)",
            "    UHC da coluna: %.1f -> tubo de queda DN %d mm (%s)"
            % (esg["uhc"], esg["tubo_de_queda"]["DN_mm"],
               esg["gate_queda"]["coluna_da_tabela"]),
            "    coletor predial DN %d mm a %.1f %% ; ventilacao DN %d mm"
            % (esg["coletor_predial"]["DN_mm"],
               esg["coletor_predial"]["declividade_pct"],
               esg["coluna_ventilacao_DN_mm"]),
        ]
    plv = r["pluvial"]
    linhas += [
        "",
        "  PLUVIAL (NBR 10844) - i = %.0f mm/h" % plv["calha"]["i_mm_h"],
        "    %.1f m2 em %d descida(s): calha DN %d mm, condutor DN %d mm (Q = %.1f L/min)"
        % (plv["area_contribuicao_m2"], plv["n_descidas"], plv["calha"]["DN_mm"],
           plv["condutor"]["DN_mm"], plv["calha"]["Q_Lmin"]),
        "",
        "  Gate: %s%s" % ("ATENDE" if r["ATENDE"] else "REPROVA",
                          "" if r["ATENDE"] else " (%s)" % ", ".join(r["reprovados"])),
    ]
    for aviso in r["avisos"]:
        linhas.append("  [aviso] %s" % aviso["detail"])
    return "\n".join(linhas)
