"""Contratos de entrada para a verificação de gussets."""

import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import gusset_ligacao


CASO_GUSSET = {
    "N": 50.0,
    "t": 0.012,
    "w0": 0.020,
    "Lc": 0.100,
    "fy": 250e3,
    "fu": 400e3,
    "Lsolda": 0.300,
}


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("N", math.nan),
        ("N", math.inf),
        ("t", 0.0),
        ("t", math.nan),
        ("Lc", 0.0),
        ("Lc", math.inf),
        ("fy", 0.0),
        ("fu", -1.0),
    ],
)
def test_verifica_gusset_rejeita_parametro_fisico_invalido(campo, valor):
    caso = dict(CASO_GUSSET)
    caso[campo] = valor

    with pytest.raises(ValueError, match=campo):
        gusset_ligacao.verifica_gusset(caso)
