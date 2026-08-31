"""População de depósitos conforme a NBR 9077:2025.

Este módulo calcula somente a população exata da área computável. A norma não
declara, na evidência consultada, como converter a divisão em população inteira;
por isso nenhuma política de arredondamento é aplicada aqui.
"""

from __future__ import annotations

import math
from numbers import Real


DENSIDADE_DEPOSITO_M2_POR_PESSOA = 30.0
ARREDONDAMENTO_NORMATIVO = "não declarado pela NBR 9077:2025"


def _numero_real_finito(nome, valor, *, positivo=False, nao_negativo=False):
    if isinstance(valor, bool) or not isinstance(valor, Real):
        raise ValueError(f"{nome} deve ser um número real finito")
    valor = float(valor)
    if not math.isfinite(valor):
        raise ValueError(f"{nome} deve ser um número real finito")
    if positivo and valor <= 0:
        raise ValueError(f"{nome} deve ser positivo")
    if nao_negativo and valor < 0:
        raise ValueError(f"{nome} não pode ser negativo")
    return valor


def _areas_validas(nome, valores):
    if valores is None or isinstance(valores, (str, bytes)):
        raise ValueError(f"{nome} deve ser uma coleção de áreas")
    try:
        valores = list(valores)
    except TypeError as error:
        raise ValueError(f"{nome} deve ser uma coleção de áreas") from error
    return [
        _numero_real_finito(f"{nome}[{indice}]", valor, nao_negativo=True)
        for indice, valor in enumerate(valores)
    ]


def dimensiona_populacao_deposito(
    area_pavimento_m2,
    *,
    areas_excluidas_m2=(),
    areas_incluidas_m2=(),
):
    """Calcula população exata de um depósito pela área computável.

    ``areas_incluidas_m2`` deve conter somente áreas descobertas com presença
    humana que ainda não estejam na área bruta informada. A classificação das
    áreas é responsabilidade explícita do chamador; este módulo não a infere.
    """
    area_pavimento = _numero_real_finito(
        "area_pavimento_m2", area_pavimento_m2, positivo=True
    )
    excluidas = _areas_validas("areas_excluidas_m2", areas_excluidas_m2)
    incluidas = _areas_validas("areas_incluidas_m2", areas_incluidas_m2)
    area_computavel = area_pavimento - math.fsum(excluidas) + math.fsum(incluidas)
    if area_computavel <= 0 or not math.isfinite(area_computavel):
        raise ValueError("area computável deve ser positiva e finita")
    populacao_exata = area_computavel / DENSIDADE_DEPOSITO_M2_POR_PESSOA
    return {
        "area_pavimento_m2": area_pavimento,
        "areas_excluidas_m2": excluidas,
        "areas_incluidas_m2": incluidas,
        "area_computavel_m2": area_computavel,
        "densidade_m2_por_pessoa": DENSIDADE_DEPOSITO_M2_POR_PESSOA,
        "populacao_exata": populacao_exata,
        "populacao_inteira": None,
        "politica_arredondamento": None,
        "arredondamento_normativo": ARREDONDAMENTO_NORMATIVO,
        "requer_decisao_arredondamento": True,
        "pronto_para_rotas": False,
        "calculo_ok": True,
        "OK": True,
    }


# ===========================================================================
# TABELA 4 COMPLETA - densidade populacional por atividade
#
# `dimensiona_populacao_deposito` acima cobre UMA linha da Tabela 4 (depósito,
# 30 m²/pessoa), que era a única de que o galpão precisava. O edifício
# multipavimento precisa das demais: um prédio residencial não se dimensiona
# por área, e sim por DORMITÓRIO ("duas pessoas por dormitório"), e um andar de
# escritórios por 7 m². Transcrito LITERALMENTE da Tabela 4 da NBR 9077:2025;
# cada entrada carrega o texto da coluna "Densidade" como o leu.
#
# ARREDONDAMENTO: a norma continua sem declarar a política (ver
# ARREDONDAMENTO_NORMATIVO). Aqui ela deixa de travar o projeto e passa a ser
# uma DECISÃO DECLARADA: o default é 'cima', que é o piso conservador para
# saída de emergência (arredondar população para baixo estreitaria a escada),
# e fica registrado no resultado como decisão de projeto - nunca como valor
# normativo. Quem quiser outra política declara.
# ===========================================================================

# por_area      : m² de área computável por pessoa
# por_dormitorio: pessoas por dormitório
# por_vaga      : vagas de veículo por pessoa
# As linhas com célula de densidade MESCLADA na Tabela 4 repetem aqui o mesmo
# valor, uma entrada por atividade, para que a chave do projeto seja a atividade
# e não a célula.
DENSIDADES = {
    # --- Residencial ------------------------------------------------------
    "habitacao_unifamiliar": {
        "por_dormitorio": 2.0,
        "texto": "Duas pessoas por dormitório",
        "exemplos": "Casas térreas ou assobradadas, isoladas ou não"},
    "habitacao_multifamiliar": {
        "por_dormitorio": 2.0,
        "texto": "Duas pessoas por dormitório",
        "exemplos": "Edifícios de apartamentos em geral"},
    "habitacao_coletiva": {
        "por_dormitorio": 2.0, "por_area_alojamento": 4.0,
        "texto": "Duas pessoas por dormitório e uma pessoa por 4 m² de área "
                 "de alojamento",
        "exemplos": "Pensionatos, internatos, alojamentos, mosteiros, "
                    "conventos, residenciais geriátricos, todos com capacidade "
                    "máxima de 16 leitos"},
    # --- Serviços de hospedagem -------------------------------------------
    "hotel": {"por_area": 15.0,
              "texto": "Uma pessoa por 15 m² de área computável",
              "exemplos": "Hotéis, motéis, pensões, hospedarias, pousadas"},
    "hotel_residencial": {
        "por_area": 15.0, "texto": "Uma pessoa por 15 m² de área computável",
        "exemplos": "Hotéis e assemelhados com cozinha própria nos apartamentos"},
    # --- Comercial ---------------------------------------------------------
    "comercio_geral": {"por_area": 3.0,
                       "texto": "Uma pessoa por 3 m² de área computável",
                       "exemplos": "Edifícios de lojas, magazines, supermercados"},
    "centro_de_compras": {"por_area": 3.0,
                          "texto": "Uma pessoa por 3 m² de área computável",
                          "exemplos": "Shopping Centers"},
    # --- Serviços profissionais -------------------------------------------
    "servico_profissional": {
        "por_area": 7.0, "texto": "Uma pessoa por 7 m² de área computável",
        "exemplos": "Escritórios administrativos ou técnicos, consultórios, "
                    "instituições financeiras, data centers"},
    "agencia_bancaria": {"por_area": 7.0,
                         "texto": "Uma pessoa por 7 m² de área computável",
                         "exemplos": "Agências bancárias e assemelhados"},
    "servico_reparacao": {"por_area": 7.0,
                          "texto": "Uma pessoa por 7 m² de área computável",
                          "exemplos": "Lavanderias, assistências técnicas"},
    "laboratorio": {"por_area": 7.0,
                    "texto": "Uma pessoa por 7 m² de área computável",
                    "exemplos": "Laboratórios de análises clínicas sem internação"},
    "call_center": {"por_area": 1.5,
                    "texto": "Uma pessoa por 1,50 m² de área computável",
                    "exemplos": "Call center e assemelhados"},
    # --- Educacional e cultura física (área de SALA DE AULA) ---------------
    "pre_escola": {"por_area": 1.5, "area_de": "sala_de_aula",
                   "texto": "Uma pessoa por 1,50 m² de área de sala de aula",
                   "exemplos": "Creches, escolas maternais, jardins de infância"},
    "escola_geral": {"por_area": 1.5, "area_de": "sala_de_aula",
                     "texto": "Uma pessoa por 1,50 m² de área de sala de aula",
                     "exemplos": "Escolas de primeiro, segundo e terceiro graus"},
    "escola_deficientes": {"por_area": 1.5, "area_de": "sala_de_aula",
                           "texto": "Uma pessoa por 1,50 m² de área de sala de aula",
                           "exemplos": "Escolas para pessoas com deficiência"},
    "centro_treinamento_profissional": {
        "por_area": 1.5, "area_de": "sala_de_aula",
        "texto": "Uma pessoa por 1,50 m² de área de sala de aula",
        "exemplos": "Escolas profissionais em geral"},
    "espaco_cultura_fisica": {
        "por_area": 1.5,
        "texto": "Uma pessoa por 1,50 m² de área computável",
        "exemplos": "Artes marciais, natação, ginástica, esportes coletivos, "
                    "sauna e fisioterapia, todos sem arquibancada"},
    # --- Local de reunião de público ---------------------------------------
    "objetos_valor_inestimavel": {
        "por_area": 3.0, "texto": "Uma pessoa por 3 m² de área computável",
        "exemplos": "Museus, galerias de arte, bibliotecas"},
    "praticas_religiosas_velorios": {
        "por_area": 1.0,
        "texto": "Uma pessoa por metro quadrado de área computável",
        "exemplos": "Igrejas, sinagogas, templos, mesquitas, crematórios"},
    "terminal_passageiros_aeroporto": {
        "por_area": 0.5,
        "texto": "Duas pessoas por metro quadrado de área computável",
        "exemplos": "Aeroportos, heliponto e assemelhados"},
    "artes_cenicas_auditorios": {
        "por_area": 1.0,
        "texto": "Uma pessoa por metro quadrado de área computável",
        "exemplos": "Teatros, cinemas, óperas, auditórios de estúdios"},
    "clubes_sociais_salao_festas": {
        "por_area": 0.5,
        "texto": "Duas pessoas por metro quadrado de área computável",
        "exemplos": "Salão de festas (buffet), restaurantes dançantes, clubes"},
    "local_refeicao": {
        "por_area": 1.0,
        "texto": "Uma pessoa por metro quadrado de área computável",
        "exemplos": "Restaurantes, lanchonetes, bares, refeitórios, cantinas"},
    "recreacao_publica": {
        "por_area": 0.5,
        "texto": "Duas pessoas por metro quadrado de área computável",
        "exemplos": "Jardim zoológico, parques recreativos"},
    "exposicao_objetos_animais": {
        "por_area": 3.0, "texto": "Uma pessoa por 3 m² de área computável",
        "exemplos": "Salões e salas para exposição de objetos e animais"},
    "boates": {"por_area": 1.0 / 3.0,
               "texto": "Três pessoas por metro quadrado de área computável",
               "exemplos": "Casas noturnas, danceterias, discotecas"},
    # --- Serviço automotivo -------------------------------------------------
    "garagem_sem_publico": {
        "por_vaga": 40.0, "texto": "Uma pessoa por 40 vagas de veículo",
        "exemplos": "Garagens automáticas, garagens com manobrista"},
    "garagem_com_publico": {
        "por_vaga": 20.0, "texto": "Uma pessoa por 20 vagas de veículo",
        "exemplos": "Garagens coletivas sem automação, sem abastecimento"},
    "local_abastecimento_combustivel": {
        "por_area": 20.0, "texto": "Uma pessoa por 20 m² de área computável",
        "exemplos": "Postos de abastecimento e serviços"},
    "servicos_conservacao_manutencao": {
        "por_area": 20.0, "texto": "Uma pessoa por 20 m² de área computável",
        "exemplos": "Oficinas de conserto de veículos, borracharias"},
    "hangar": {"por_area": 20.0,
               "texto": "Uma pessoa por 20 m² de área computável",
               "exemplos": "Abrigos para aeronaves com e sem abastecimento"},
    # --- Industrial / depósito / energia -----------------------------------
    "industria_geral": {"por_area": 10.0,
                        "texto": "Uma pessoa por 10 m² de área computável",
                        "exemplos": "Atividades industriais em geral"},
    "deposito_geral": {
        "por_area": DENSIDADE_DEPOSITO_M2_POR_PESSOA,
        "texto": "Uma pessoa por 30 m² de área computável",
        "exemplos": "Edificações sem processo industrial destinadas "
                    "exclusivamente à armazenagem de produtos"},
    "central_energia": {"por_area": 10.0,
                        "texto": "Uma pessoa por 10 m² de área computável",
                        "exemplos": "Subestação elétrica, usina de geração"},
    # --- Materiais explosivos / situações especiais -------------------------
    "explosivos_comercio": {"por_area": 3.0,
                            "texto": "Uma pessoa por 3 m² de área computável",
                            "exemplos": "Comércio de fogos de artifício"},
    "explosivos_industria": {"por_area": 10.0,
                             "texto": "Uma pessoa por 10 m² de área computável",
                             "exemplos": "Indústria de materiais explosivos"},
    "explosivos_deposito": {"por_area": 10.0,
                            "texto": "Uma pessoa por 10 m² de área computável",
                            "exemplos": "Depósito de materiais explosivos"},
    "liquido_gas_inflamavel": {
        "por_area": 10.0, "texto": "Uma pessoa por 10 m² de área computável",
        "exemplos": "Produção, manipulação, armazenamento e distribuição de "
                    "líquidos ou gases inflamáveis ou combustíveis"},
    "central_comunicacao": {"por_area": 10.0,
                            "texto": "Uma pessoa por 10 m² de área computável",
                            "exemplos": "Central telefônica, centros de comunicação"},
}

# 5.3: em locais com assentos fixos, a população E' a dos assentos.
ATIVIDADES_ASSENTOS_FIXOS = frozenset({
    "artes_cenicas_auditorios", "praticas_religiosas_velorios"})

POLITICAS_ARREDONDAMENTO = ("cima", "exata")
POLITICA_ARREDONDAMENTO_PADRAO = "cima"


def densidade(atividade):
    """A linha da Tabela 4 da atividade. Atividade desconhecida e' ERRO."""
    if atividade not in DENSIDADES:
        raise ValueError(
            "atividade %r nao consta da Tabela 4 da NBR 9077:2025 (use uma de: "
            "%s)" % (atividade, ", ".join(sorted(DENSIDADES))))
    return dict(DENSIDADES[atividade])


def populacao(atividade, *, area_computavel_m2=None, dormitorios=None,
              vagas=None, area_alojamento_m2=None, assentos_fixos=None,
              politica_arredondamento=POLITICA_ARREDONDAMENTO_PADRAO):
    """Populacao de um ambiente/pavimento pela Tabela 4 da NBR 9077:2025.

    O dado que a atividade exige e' o que tem de ser declarado: atividade
    residencial pede DORMITORIOS (nao area), garagem pede VAGAS, as demais pedem
    a area computavel. Faltando o dado da propria linha da tabela, o calculo
    LEVANTA - nao ha substituto plausivel, e uma area usada no lugar de
    dormitorios daria outra populacao.
    """
    linha = densidade(atividade)
    if politica_arredondamento not in POLITICAS_ARREDONDAMENTO:
        raise ValueError("politica_arredondamento deve ser uma de %s"
                         % (list(POLITICAS_ARREDONDAMENTO),))
    parcelas = []
    if assentos_fixos is not None:
        if atividade not in ATIVIDADES_ASSENTOS_FIXOS:
            raise ValueError(
                "assentos_fixos so se aplica a locais com assentos fixos (5.3): "
                "%s" % ", ".join(sorted(ATIVIDADES_ASSENTOS_FIXOS)))
        n = _numero_real_finito("assentos_fixos", assentos_fixos, positivo=True)
        return {
            "atividade": atividade, "densidade": linha,
            "criterio": "5.3 - assentos fixos: a populacao e' a dos assentos",
            "populacao_exata": n, "populacao": int(math.ceil(n - 1e-9)),
            "politica_arredondamento": "assentos fixos (5.3)",
            "arredondamento_normativo": ARREDONDAMENTO_NORMATIVO,
            "parcelas": [{"criterio": "assentos_fixos", "pessoas": n}],
            "OK": True,
        }
    if "por_dormitorio" in linha:
        if dormitorios is None:
            raise ValueError(
                "atividade %r e' medida em DORMITORIOS pela Tabela 4 (%s): "
                "declare 'dormitorios'; a area do pavimento nao substitui esse "
                "dado" % (atividade, linha["texto"]))
        n_dorm = _numero_real_finito("dormitorios", dormitorios, positivo=True)
        parcelas.append({"criterio": "dormitorios",
                         "pessoas": linha["por_dormitorio"] * n_dorm,
                         "dormitorios": n_dorm})
    if "por_area_alojamento" in linha and area_alojamento_m2 is not None:
        a = _numero_real_finito("area_alojamento_m2", area_alojamento_m2,
                                positivo=True)
        parcelas.append({"criterio": "area_alojamento",
                         "pessoas": a / linha["por_area_alojamento"],
                         "area_m2": a})
    if "por_vaga" in linha:
        if vagas is None:
            raise ValueError(
                "atividade %r e' medida em VAGAS pela Tabela 4 (%s): declare "
                "'vagas'" % (atividade, linha["texto"]))
        n_vagas = _numero_real_finito("vagas", vagas, positivo=True)
        parcelas.append({"criterio": "vagas",
                         "pessoas": n_vagas / linha["por_vaga"],
                         "vagas": n_vagas})
    if "por_area" in linha:
        if area_computavel_m2 is None:
            raise ValueError(
                "atividade %r e' medida por AREA pela Tabela 4 (%s): declare "
                "'area_computavel_m2'" % (atividade, linha["texto"]))
        a = _numero_real_finito("area_computavel_m2", area_computavel_m2,
                                positivo=True)
        parcelas.append({"criterio": linha.get("area_de", "area_computavel"),
                         "pessoas": a / linha["por_area"], "area_m2": a})
    if not parcelas:
        raise ValueError("nenhuma parcela de populacao foi calculada para %r"
                         % atividade)
    exata = math.fsum(p["pessoas"] for p in parcelas)
    inteira = (int(math.ceil(exata - 1e-9))
               if politica_arredondamento == "cima" else exata)
    return {
        "atividade": atividade, "densidade": linha, "criterio": linha["texto"],
        "populacao_exata": exata, "populacao": inteira,
        "politica_arredondamento": politica_arredondamento,
        # a norma nao declara a politica; 'cima' e' DECISAO DE PROJETO adotada
        # por ser o piso conservador para saida de emergencia.
        "arredondamento_normativo": ARREDONDAMENTO_NORMATIVO,
        "parcelas": parcelas,
        "OK": True,
    }
