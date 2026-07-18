# ============================================================================
# test_wizard_robustez.py - o wizard nao pode TRAVAR nem falhar com erro cru.
# Caca sessao 14: perguntar() com entrada nao-interativa que devolve "" para
# sempre entrava em LOOP INFINITO em campo obrigatorio (_ask_one re-perguntava
# sem limite); e construir_spec sem um obrigatorio dava KeyError cru.
# ============================================================================
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS
import wizard as WZ


def test_construir_spec_sem_obrigatorio_erro_claro():
    # falta v0 (obrigatorio, sem default) -> ValueError explicito, nao KeyError
    r = dict(area_lote_m2=1200, span=10, comprimento=20, eave=6, sigma_solo=200)
    with pytest.raises(ValueError) as ex:
        WZ.construir_spec(r)
    assert "v0" in str(ex.value)


def test_construir_spec_completo_ok():
    r = dict(area_lote_m2=1200, span=10, comprimento=20, eave=6, v0=40,
             sigma_solo=200, fund_tipo="sapata")
    s = WZ.construir_spec(r, slug="t_ok")
    assert PS.validar(s)["ok"], PS.validar(s)["faltando"]


def test_ask_one_nao_trava_entrada_vazia():
    # entrada que SEMPRE devolve "" num campo obrigatorio: antes travava (loop
    # infinito); agora levanta RuntimeError apos o cap de tentativas.
    with pytest.raises(RuntimeError):
        WZ._ask_one("v0", "V0", WZ._f, None, True,
                    entrada=lambda _="": "", saida=lambda *_: None)


def test_ask_one_eof_erro_claro():
    def _eof(_=""):
        raise EOFError("fim")
    with pytest.raises(RuntimeError) as ex:
        WZ._ask_one("v0", "V0", WZ._f, None, True, entrada=_eof, saida=lambda *_: None)
    assert "v0" in str(ex.value)


def test_perguntar_entrada_exaurida_nao_trava():
    # laco completo com respostas insuficientes (obrigatorio sem valor) nao pode
    # pendurar: deve levantar (RuntimeError) em tempo finito.
    respostas = iter(["proj", "1200"])   # so slug + area; span (obrig) fica sem
    def entrada(_=""):
        return next(respostas, "")       # devolve "" ao esgotar
    with pytest.raises(RuntimeError):
        WZ.perguntar(entrada=entrada, saida=lambda *_: None, slug=None)


def test_ask_one_aceita_valor_valido():
    got = WZ._ask_one("v0", "V0", WZ._f, None, True,
                      entrada=lambda _="": "42", saida=lambda *_: None)
    assert got == 42.0
