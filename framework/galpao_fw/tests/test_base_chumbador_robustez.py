import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import base_chumbador


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("B", 0.0),
        ("L", 0.0),
        ("fck", 0.0),
        ("db", 0.0),
        ("n_chumbadores", 0),
        ("fy_placa", 0.0),
        ("B", float("nan")),
        ("db", float("inf")),
        ("L", -0.01),
    ],
)
def test_verifica_base_rejeita_parametros_fisicos_nulos(field, value):
    caso = dict(base_chumbador.CASO_EXEMPLO_ENGASTE)
    caso[field] = value

    with pytest.raises(ValueError, match=field):
        base_chumbador.verifica_base(caso)
