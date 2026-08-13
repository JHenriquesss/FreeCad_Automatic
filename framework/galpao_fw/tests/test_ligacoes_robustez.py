"""Contratos de entrada para os cálculos de ligações."""

import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import ligacoes


CASO_PARAFUSOS = {
    "n": 4,
    "db": 0.020,
    "fub": 825e3,
    "t_chapa": 0.0125,
    "fu_chapa": 400e3,
    "lf": 0.025,
    "V": 130.0,
    "N": 90.0,
}


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("n", 0),
        ("n", math.nan),
        ("db", 0.0),
        ("db", math.inf),
        ("fub", 0.0),
        ("t_chapa", 0.0),
        ("fu_chapa", 0.0),
        ("lf", -0.001),
        ("lf", math.nan),
    ],
)
def test_parafusos_rejeita_parametro_fisico_invalido(campo, valor):
    caso = dict(CASO_PARAFUSOS)
    caso[campo] = valor

    with pytest.raises(ValueError, match=campo):
        ligacoes.parafusos(caso)
