"""Validação de armazenamento protegido por chuveiros (ABNT NBR 16981:2021).

O módulo é deliberadamente um gate de dados: não dimensiona bombas, RTI ou a
tabela completa de chuveiros. Dados ausentes permanecem inconclusivos e não
recebem valores normativos implícitos.

As condições de ESFR e encapsulamento seguem as citações autorizadas desta
tarefa: [1] limitações por extração/barreira de fumaça, [3] acréscimo de 25 %
para armazenamento encapsulado e [4] área de operação ESFR. As condições de
armazenamento em porta-paletes são mantidas no contrato executável dos testes;
nenhum critério adicional é inferido de outra norma.
"""

from __future__ import annotations

import math
from numbers import Real


# Limites do contrato executável desta tarefa.
ALTURA_ARMAZENAMENTO_ALTA_M = 3.7
DENSIDADE_MIN_ALTA_LMIN_M2 = 6.1
AREA_OPERACAO_MIN_M2 = 186.0
AUMENTO_ENCAPSULADO = 1.25
N_CHUVEIROS_ESFR = 12
N_RAMAIS_ESFR = 3
AREA_INTRAPRATELEIRA_MAX_M2 = 3700.0
VAZAO_INTRAPRATELEIRA_MIN_LMIN = 115.0
ALTURA_BOBINAS_PAPEL_M = 4.6
AREA_CHUVEIRO_MIN_M2 = 6.5
AREA_CHUVEIRO_MAX_M2 = 9.3
ALTURA_TISSUE_LACUNA_M = 6.1


def _ausente(caso, campo):
    return campo not in caso or caso[campo] is None


def _adiciona_unico(itens, valor):
    if valor not in itens:
        itens.append(valor)


def _numero(caso, campo, faltantes, violacoes):
    """Lê um número explícito, distinguindo ausência de valor inválido."""
    if _ausente(caso, campo):
        _adiciona_unico(faltantes, campo)
        return None
    valor = caso[campo]
    if isinstance(valor, bool) or not isinstance(valor, Real):
        violacoes.append(f"{campo} deve ser numérico")
        return None
    valor = float(valor)
    if not math.isfinite(valor):
        violacoes.append(f"{campo} deve ser finito")
        return None
    return valor


def _booleano(caso, campo, faltantes, violacoes):
    """Lê um booleano explícito, sem converter strings ou números."""
    if _ausente(caso, campo):
        _adiciona_unico(faltantes, campo)
        return None
    valor = caso[campo]
    if not isinstance(valor, bool):
        violacoes.append(f"{campo} deve ser booleano")
        return None
    return valor


def _opcional_booleano(caso, campo, violacoes):
    if campo not in caso or caso[campo] is None:
        return None
    if not isinstance(caso[campo], bool):
        violacoes.append(f"{campo} deve ser booleano")
        return None
    return caso[campo]


def verifica_armazenamento_nbr16981(caso):
    """Verifica requisitos explícitos de armazenamento protegido por chuveiros.

    O retorno sempre contém ``OK``, ``inconclusivo``, ``faltantes``,
    ``violacoes`` e ``requisitos_aplicados``. Campos condicionais só são
    exigidos quando a condição correspondente foi declarada.
    """
    if not isinstance(caso, dict):
        raise ValueError("caso deve ser um dicionário de parâmetros")

    faltantes = []
    violacoes = []
    requisitos_aplicados = []

    mercadoria_declarada = _booleano(
        caso, "mercadoria_risco_mais_grave_declarada", faltantes, violacoes
    )
    altura_armazenamento = _numero(
        caso, "altura_armazenamento_m", faltantes, violacoes
    )
    altura_teto = _numero(caso, "altura_teto_m", faltantes, violacoes)
    interpolacao = _booleano(
        caso, "interpolacao_densidade_area", faltantes, violacoes
    )

    if mercadoria_declarada is False:
        violacoes.append(
            "mercadoria_risco_mais_grave_declarada deve ser verdadeira"
        )
    if altura_armazenamento is not None and altura_armazenamento <= 0:
        violacoes.append("altura_armazenamento_m deve ser maior que zero")
    if altura_teto is not None and altura_teto <= 0:
        violacoes.append("altura_teto_m deve ser maior que zero")
    if interpolacao is True:
        violacoes.append(
            "interpolação de densidade e área de operação não é permitida"
        )

    if not faltantes and not violacoes:
        requisitos_aplicados.append(
            "requisitos gerais de proteção para o método de armazenamento [1]"
        )

    # As condições abaixo usam somente os limites fixados no contrato desta
    # tarefa; a ausência de qualquer dado requerido não é preenchida por default.
    if (
        altura_armazenamento is not None
        and altura_armazenamento > ALTURA_ARMAZENAMENTO_ALTA_M
    ):
        densidade = _numero(
            caso, "densidade_projeto_Lmin_m2", faltantes, violacoes
        )
        area_operacao = _numero(caso, "area_operacao_m2", faltantes, violacoes)
        requisitos_aplicados.append(
            "armazenamento acima de 3,7 m: densidade e área de operação"
        )
        if densidade is not None and densidade < DENSIDADE_MIN_ALTA_LMIN_M2:
            violacoes.append(
                "densidade_projeto_Lmin_m2 deve ser pelo menos 6,1"
            )
        if area_operacao is not None and area_operacao < AREA_OPERACAO_MIN_M2:
            violacoes.append("area_operacao_m2 deve ser pelo menos 186")

    encapsulado = _opcional_booleano(
        caso, "armazenamento_encapsulado", violacoes
    )
    if encapsulado is True:
        densidade_base = _numero(
            caso, "densidade_base_Lmin_m2", faltantes, violacoes
        )
        densidade_projeto = _numero(
            caso, "densidade_projeto_Lmin_m2", faltantes, violacoes
        )
        requisitos_aplicados.append(
            "armazenamento encapsulado: acréscimo mínimo de 25 % [3]"
        )
        if densidade_base is not None and densidade_base <= 0:
            violacoes.append("densidade_base_Lmin_m2 deve ser maior que zero")
        if (
            densidade_base is not None
            and densidade_projeto is not None
            and densidade_projeto < densidade_base * AUMENTO_ENCAPSULADO
        ):
            violacoes.append(
                "densidade_projeto_Lmin_m2 deve ser pelo menos 25% maior que a base"
            )

    esfr = _opcional_booleano(caso, "sistema_esfr", violacoes)
    if esfr is True:
        sem_fumaca = _booleano(
            caso,
            "sem_extracao_ou_barreira_fumaca",
            faltantes,
            violacoes,
        )
        n_chuveiros = _numero(
            caso, "n_chuveiros_operacao", faltantes, violacoes
        )
        n_ramais = _numero(caso, "n_ramais_operacao", faltantes, violacoes)
        requisitos_aplicados.append(
            "ESFR sem extração/barreira de fumaça e área com 12 chuveiros em 3 ramais [1][4]"
        )
        if sem_fumaca is False:
            violacoes.append(
                "sistema ESFR não pode ter extração ou barreira de fumaça"
            )
        if n_chuveiros is not None and n_chuveiros != N_CHUVEIROS_ESFR:
            violacoes.append("a área ESFR deve ter 12 chuveiros")
        if n_ramais is not None and n_ramais != N_RAMAIS_ESFR:
            violacoes.append("a área ESFR deve ter 3 ramais")

    intrarack = _opcional_booleano(
        caso, "chuveiros_intraprateleiras", violacoes
    )
    if intrarack is True:
        area_porta_paletes = _numero(
            caso, "area_porta_paletes_m2", faltantes, violacoes
        )
        requisitos_aplicados.append(
            "chuveiros intraprateleiras e área de porta-paletes [6]"
        )
        if (
            area_porta_paletes is not None
            and area_porta_paletes > AREA_INTRAPRATELEIRA_MAX_M2
        ):
            violacoes.append("area_porta_paletes_m2 não pode exceder 3700")
        if (
            altura_armazenamento is not None
            and altura_armazenamento > ALTURA_ARMAZENAMENTO_ALTA_M
        ):
            vazao_intraprateleira = _numero(
                caso, "vazao_intraprateleira_Lmin", faltantes, violacoes
            )
            if (
                vazao_intraprateleira is not None
                and vazao_intraprateleira < VAZAO_INTRAPRATELEIRA_MIN_LMIN
            ):
                violacoes.append(
                    "vazao_intraprateleira_Lmin deve ser pelo menos 115"
                )

    bobinas = _opcional_booleano(caso, "bobinas_papel", violacoes)
    if (
        bobinas is True
        and altura_armazenamento is not None
        and altura_armazenamento >= ALTURA_BOBINAS_PAPEL_M
    ):
        temperatura_alta = _booleano(
            caso, "chuveiro_temperatura_alta", faltantes, violacoes
        )
        requisitos_aplicados.append(
            "bobinas de papel a partir de 4,6 m: chuveiro de alta temperatura"
        )
        if temperatura_alta is False:
            violacoes.append(
                "bobinas de papel exigem chuveiro de temperatura alta"
            )
        metodo_area_densidade = _opcional_booleano(
            caso, "metodo_area_densidade", violacoes
        )
        if metodo_area_densidade is True:
            area_por_chuveiro = _numero(
                caso, "area_por_chuveiro_m2", faltantes, violacoes
            )
            requisitos_aplicados.append(
                "método área-densidade: 6,5 m² a 9,3 m² por chuveiro"
            )
            if area_por_chuveiro is not None and not (
                AREA_CHUVEIRO_MIN_M2 <= area_por_chuveiro <= AREA_CHUVEIRO_MAX_M2
            ):
                violacoes.append(
                    "area_por_chuveiro_m2 deve estar entre 6,5 e 9,3"
                )

    tissue = _opcional_booleano(caso, "papel_tissue", violacoes)
    if (
        tissue is True
        and altura_armazenamento is not None
        and altura_armazenamento > ALTURA_TISSUE_LACUNA_M
    ):
        _adiciona_unico(
            faltantes,
            "critério para papel tissue acima de 6,1 m",
        )
        requisitos_aplicados.append(
            "papel tissue acima de 6,1 m: critério normativo não citado"
        )

    return {
        "OK": not faltantes and not violacoes,
        "inconclusivo": bool(faltantes) and not violacoes,
        "faltantes": faltantes,
        "violacoes": violacoes,
        "requisitos_aplicados": requisitos_aplicados,
    }
