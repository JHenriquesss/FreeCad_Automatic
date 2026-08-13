"""Contrato de entrada física para o cálculo sísmico NBR 15421."""

import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import sismo_nbr15421 as S


def test_verifica_sismo_rejeita_zona_fora_do_zoneamento():
    for zona in (-1, 5, None):
        with pytest.raises(ValueError):
            S.verifica_sismo(1000.0, zona=zona)


def test_verifica_sismo_rejeita_peso_efetivo_invalido():
    for peso in (0.0, -1.0, math.nan, math.inf):
        with pytest.raises(ValueError):
            S.verifica_sismo(peso, zona=1)


def test_verifica_sismo_rejeita_dados_finitos_e_positivos_no_metodo_completo():
    casos = [
        {"hn": 0.0},
        {"hn": -1.0},
        {"hn": math.nan},
        {"hn": math.inf},
        {"I": 0.0},
        {"I": -1.0},
        {"I": math.nan},
        {"ag": 0.0},
        {"ag": -1.0},
        {"ag": math.nan},
        {"ag": math.inf},
    ]
    for alteracao in casos:
        parametros = {"W": 1000.0, "zona": 3, "hn": 6.0}
        parametros.update(alteracao)
        with pytest.raises(ValueError):
            S.verifica_sismo(**parametros)


def test_verifica_sismo_rejeita_classe_e_sistema_desconhecidos():
    with pytest.raises(ValueError):
        S.verifica_sismo(1000.0, zona=3, hn=6.0, classe="F")
    with pytest.raises(ValueError):
        S.verifica_sismo(1000.0, zona=3, hn=6.0, sistema="desconhecido")
