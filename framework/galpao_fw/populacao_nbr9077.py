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
