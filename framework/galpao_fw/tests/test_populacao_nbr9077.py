"""Testes da população de depósitos conforme NBR 9077:2025."""

import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import populacao_nbr9077 as pop


def test_deposito_usa_trinta_metros_quadrados_por_pessoa():
    resultado = pop.dimensiona_populacao_deposito(600.0)

    assert resultado["area_pavimento_m2"] == 600.0
    assert resultado["areas_excluidas_m2"] == []
    assert resultado["areas_incluidas_m2"] == []
    assert resultado["area_computavel_m2"] == 600.0
    assert resultado["densidade_m2_por_pessoa"] == 30.0
    assert resultado["populacao_exata"] == 20.0
    assert resultado["populacao_inteira"] is None
    assert resultado["politica_arredondamento"] is None
    assert resultado["requer_decisao_arredondamento"] is True
    assert resultado["pronto_para_rotas"] is False
    assert resultado["calculo_ok"] is True
    assert resultado["OK"] is True


def test_areas_excluidas_e_incluidas_sao_explicitas():
    excluida = pop.dimensiona_populacao_deposito(
        650.0,
        areas_excluidas_m2=[50.0],
    )
    incluida = pop.dimensiona_populacao_deposito(
        600.0,
        areas_incluidas_m2=[30.0],
    )

    assert excluida["area_computavel_m2"] == 600.0
    assert excluida["populacao_exata"] == 20.0
    assert incluida["area_computavel_m2"] == 630.0
    assert incluida["populacao_exata"] == 21.0
    assert excluida["areas_excluidas_m2"] == [50.0]
    assert incluida["areas_incluidas_m2"] == [30.0]


def test_populacao_fracionaria_nao_e_arredondada():
    resultado = pop.dimensiona_populacao_deposito(625.0)

    assert math.isclose(resultado["populacao_exata"], 625.0 / 30.0)
    assert resultado["populacao_inteira"] is None
    assert resultado["politica_arredondamento"] is None
    assert resultado["arredondamento_normativo"] == (
        "não declarado pela NBR 9077:2025"
    )
    assert resultado["pronto_para_rotas"] is False


@pytest.mark.parametrize(
    "area",
    [0.0, -1.0, True, False, "600", float("nan"), float("inf")],
)
def test_area_do_pavimento_invalida_levanta_value_error(area):
    with pytest.raises(ValueError):
        pop.dimensiona_populacao_deposito(area)


@pytest.mark.parametrize(
    "areas",
    [None, 50.0, "50", [True], ["50"], [float("nan")], [float("inf")], [-1.0]],
)
def test_colecoes_de_areas_invalidas_levantam_value_error(areas):
    with pytest.raises(ValueError):
        pop.dimensiona_populacao_deposito(600.0, areas_excluidas_m2=areas)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"areas_excluidas_m2": [600.0]},
        {"areas_excluidas_m2": [601.0]},
        {"areas_incluidas_m2": [float("inf")]},
    ],
)
def test_area_computavel_invalida_levanta_value_error(kwargs):
    with pytest.raises(ValueError):
        pop.dimensiona_populacao_deposito(600.0, **kwargs)
