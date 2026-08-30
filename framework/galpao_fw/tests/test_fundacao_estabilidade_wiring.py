"""Propagação do contrato de estabilidade pelos specs e parâmetros do galpão."""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS


def _spec_completo():
    caminho = os.path.join(GALPAO, "spec_amostra_engenheiro.json")
    return json.load(open(caminho, encoding="utf-8"))


def test_template_novo_declara_metodo_de_estabilidade():
    spec = PS.novo()
    verificacao = spec["fundacao"]["verificacao_estabilidade"]

    assert verificacao["metodo"] == "nbr6122_valores_calculo"
    assert verificacao["tipo_acoes"] == "calculo"


def test_mapper_preserva_verificacao_estabilidade():
    spec = _spec_completo()
    spec["fundacao"]["verificacao_estabilidade"] = {
        "metodo": "fs_global_legacy",
        "tipo_acoes": "caracteristicas",
        "fs_tombamento": 1.35,
        "fs_deslizamento": 1.25,
    }

    parametros = PS.to_rodar_params(spec)

    assert parametros["fundacao"]["verificacao_estabilidade"]["fs_tombamento"] == pytest.approx(1.35)
    assert parametros["fundacao"]["verificacao_estabilidade"] is not spec["fundacao"]["verificacao_estabilidade"]


def test_parametros_referencia_declararam_acoes_de_calculo():
    import rodar_galpao as R

    verificacao = R.PARAMS_REF["fundacao"]["verificacao_estabilidade"]

    assert verificacao["metodo"] == "nbr6122_valores_calculo"
    assert verificacao["tipo_acoes"] == "calculo"


def test_galpao_concreto_entrega_metodo_a_sapata():
    import galpao_concreto as gc

    resultado = gc.rodar({
        "vao": 10.0,
        "comprimento": 40.0,
        "pe_direito": 6.0,
        "n_porticos": 7,
        "v0": 40.0,
        "cat": "IV",
        "classe": "B",
        "s1": 1.0,
        "s3": 1.0,
        "G_roof": 0.30,
        "Q_roof": 0.25,
        "fck": 30e3,
        "fyk": 500e3,
        "sigma_solo_adm": 250.0,
        "verificacao_estabilidade": {
            "metodo": "nbr6122_valores_calculo",
            "tipo_acoes": "calculo",
        },
    })

    assert resultado["sapata"]["aprovado"] is not None
    rA = resultado["sapata"]["aprovado"][3]
    assert rA["metodo_verificacao"] == "nbr6122_valores_calculo"


def test_spec_bloqueia_metodo_de_estabilidade_desconhecido():
    spec = _spec_completo()
    spec["fundacao"]["verificacao_estabilidade"] = {
        "metodo": "metodo_inventado",
        "tipo_acoes": "calculo",
    }

    validacao = PS.validar(spec)

    assert not validacao["ok"]
    assert any(path == "fundacao.verificacao_estabilidade.metodo"
               for path, _ in validacao["faltando"])


def test_spec_bloqueia_fs_legacy_sem_limites_explicitos():
    spec = _spec_completo()
    spec["fundacao"]["verificacao_estabilidade"] = {
        "metodo": "fs_global_legacy",
        "tipo_acoes": "caracteristicas",
    }

    validacao = PS.validar(spec)

    assert not validacao["ok"]
    assert any(path.startswith("fundacao.verificacao_estabilidade.fs_")
               for path, _ in validacao["faltando"])


def test_spec_bloqueia_verificacao_de_estabilidade_pendente():
    spec = _spec_completo()
    spec["fundacao"]["verificacao_estabilidade"] = PS.PENDENTE

    validacao = PS.validar(spec)

    assert not validacao["ok"]
    assert any(path == "fundacao.verificacao_estabilidade"
               for path, _ in validacao["faltando"])
