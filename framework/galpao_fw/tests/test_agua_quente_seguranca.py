"""Contratos de segurança da rede de água quente conforme NBR 5626:2020."""

import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_hidraulica as gh
import hidraulica_predial as hp


def _config(**changes):
    value = {
        "vazao_normal_Ls": 0.20,
        "vazao_maxima_Ls": 0.40,
        "pressao_estatica_kPa": 250.0,
        "pressao_fria_quente_compativel": True,
        "temperatura_max_C": 60.0,
        "misturadores_sanitarios": True,
        "uso_corporal": True,
        "limitador_automatico_45C": True,
        "superficies_protegidas": True,
        "reducao_perdas_termicas": True,
        "perdas_termicas_estimadas": True,
        "dilatacao_considerada": True,
        "movimentacoes_absorvidas": True,
        "aquecedor_acumulacao": True,
        "limitador_automatico_temperatura": True,
        "valvula_seguranca_temperatura": True,
        "limitador_automatico_pressao": True,
    }
    value.update(changes)
    return value


def test_missing_hot_water_safety_data_is_inconclusive_and_not_ok():
    result = hp.verifica_agua_quente_seguranca({}, None, None)

    assert result["OK"] is False
    assert result["inconclusivo"] is True
    assert result["faltantes"]


def test_complete_hot_water_safety_contract_is_ok():
    result = hp.verifica_agua_quente_seguranca(_config(), 0.20, 50.0)

    assert result["OK"] is True
    assert result["inconclusivo"] is False
    assert result["violacoes"] == []


def test_body_use_above_45_c_without_automatic_limiter_reproves():
    result = hp.verifica_agua_quente_seguranca(
        _config(limitador_automatico_45C=False), 0.20, 50.0
    )

    assert result["OK"] is False
    assert result["inconclusivo"] is False
    assert any("45" in item for item in result["violacoes"])


def test_static_pressure_above_400_kpa_reproves():
    result = hp.verifica_agua_quente_seguranca(
        _config(pressao_estatica_kPa=400.1), 0.20, 50.0
    )

    assert result["OK"] is False
    assert any("400" in item for item in result["violacoes"])


def test_accumulation_heater_requires_temperature_and_pressure_safety_devices():
    result = hp.verifica_agua_quente_seguranca(
        _config(
            limitador_automatico_temperatura=False,
            valvula_seguranca_temperatura=False,
            limitador_automatico_pressao=False,
        ),
        0.20,
        50.0,
    )

    assert result["OK"] is False
    assert result["inconclusivo"] is False
    assert len(result["violacoes"]) == 3


def test_hot_water_integration_requires_explicit_safety_block():
    result = gh.rodar(
        {
            "geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "hidraulica": {
                "aparelhos_agua": {"lavatorio": 2},
                "aparelhos_agua_quente": {"lavatorio": 2},
                "p_alim_kPa": 300.0,
            },
        }
    )

    assert result["gates"]["seguranca_agua_quente"]["OK"] is False
    assert result["gates"]["seguranca_agua_quente"]["inconclusivo"] is True
    assert result["dimensionamento_completo"] is False
    assert result["ATENDE"] is False
