"""Contrato da área mínima de placas conforme ABNT NBR 16820:2020, 5.1.1."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sinalizacao_nbr16820 as sn


def test_area_informada_obedece_inequacao_estrita():
    reprovada = sn.dimensiona_sinalizacao(
        {"C": 20, "L": 20, "dist_visualizacao_m": 10, "area_placa_m2": 0.05}
    )
    aprovada = sn.dimensiona_sinalizacao(
        {"C": 20, "L": 20, "dist_visualizacao_m": 10, "area_placa_m2": 0.051}
    )

    assert reprovada["area_minima_m2"] == 0.05
    assert reprovada["area_atende"] is False
    assert reprovada["OK"] is False
    assert aprovada["area_atende"] is True
    assert aprovada["OK"] is True


def test_distancia_minima_de_quatro_metros_e_aplicada():
    resultado = sn.dimensiona_sinalizacao(
        {"C": 20, "L": 20, "dist_visualizacao_m": 3, "area_placa_m2": 0.009}
    )

    assert resultado["distancia_calculo_m"] == 4.0
    assert resultado["area_minima_m2"] == 0.008
    assert resultado["area_atende"] is True


def test_sem_area_preserva_modo_legado():
    resultado = sn.dimensiona_sinalizacao({"C": 40, "L": 20})

    assert resultado["area_placa_m2"] is None
    assert resultado["area_atende"] is None
    assert resultado["OK"] is True


@pytest.mark.parametrize("area", [-0.1, float("nan"), float("inf"), -float("inf"), True, "0.1"])
def test_area_invalida_falha_explicitamente(area):
    with pytest.raises(ValueError, match="area_placa_m2"):
        sn.dimensiona_sinalizacao(
            {"C": 20, "L": 20, "dist_visualizacao_m": 10, "area_placa_m2": area}
        )


@pytest.mark.parametrize("distancia", [50, float("nan"), float("inf"), -float("inf")])
def test_distancia_visualizacao_explicita_invalida_falha(distancia):
    with pytest.raises(ValueError, match="dist_visualizacao_m"):
        sn.dimensiona_sinalizacao({"C": 20, "L": 20, "dist_visualizacao_m": distancia})


def test_distancia_derivada_fora_do_dominio_reprova_sem_extrapolar_norma():
    resultado = sn.dimensiona_sinalizacao({"C": 100, "L": 60})

    assert resultado["placa_satura"] is True
    assert resultado["limite_normativo_excedido"] is True
    assert resultado["area_minima_m2"] is None
    assert resultado["area_atende"] is None
    assert resultado["OK"] is False
