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


def test_janelas_laterais_LxH_viram_faixa_z():
    # BUG historico: o usuario informa janela L x H, mas o build espera a FAIXA
    # (z_base, z_topo). Sem conversao, o build recebia (L,H) e a altura z_topo-z_base
    # ficava NEGATIVA -> quebrava o 3D. Agora o wizard converte via peitoril.
    r = dict(area_lote_m2=1200, span=10, comprimento=20, eave=6, v0=40, sigma_solo=200,
             ab_janelas_lat=(3000.0, 1000.0), janela_peitoril=1200.0)
    s = WZ.construir_spec(r, slug="t_jan")
    jl = s["aberturas"]["janelas_laterais"]
    assert jl == (1200.0, 2200.0) and jl[1] > jl[0]      # faixa crescente (z_base, z_topo)
    assert PS.validar(s)["ok"]


def test_janelas_laterais_peitoril_default():
    # sem peitoril informado -> default 1000 mm ; janela 1500 de altura -> (1000, 2500)
    r = dict(area_lote_m2=1200, span=10, comprimento=20, eave=6, v0=40, sigma_solo=200,
             ab_janelas_lat=(2000.0, 1500.0))
    s = WZ.construir_spec(r, slug="t_jan2")
    assert s["aberturas"]["janelas_laterais"] == (1000.0, 2500.0)


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
