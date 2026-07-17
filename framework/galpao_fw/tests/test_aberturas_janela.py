# ============================================================================
# test_aberturas_janela.py - convencao das janelas laterais: o wizard entrega
# (L,H); o build_galpao espera FAIXA (z_base,z_topo). O mapper to_build_kwargs
# tem de converter, senao o build monta um box de altura negativa e quebra
# ('height of box too small'). Ver memoria bug-janela-lateral-convencao.
# ============================================================================
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS
import wizard as WZ


def test_janela_band_LH_para_faixa():
    # (largura, altura) -> (z_base, z_topo) com peitoril default
    b = PS._janela_band((3000, 1000), eave_mm=8000.0)
    assert b is not None
    z0, z1 = b
    assert z1 > z0                                  # box de altura POSITIVA (nao quebra)
    assert z1 - z0 == pytest.approx(1000.0)         # altura da janela preservada
    # peitoril explicito (3o valor)
    assert PS._janela_band((3000, 1000, 500), 8000.0) == (500, 1500)
    # nunca atravessa o beiral
    z0, z1 = PS._janela_band((3000, 9000), 8000.0)
    assert z1 <= 8000.0 - 100.0
    assert PS._janela_band(None, 8000.0) is None


def test_to_build_kwargs_converte_janela_do_wizard():
    # spec montado pelo wizard (janela = L,H) -> mapper produz faixa valida
    r = dict(area_lote_m2=1000, span=20, comprimento=28.5, eave=8, v0=45,
             sigma_solo=150, fund_tipo="sapata",
             ab_janelas_lat=(3000.0, 1000.0))
    s = WZ.construir_spec(r, slug="t_jan")
    assert tuple(s["aberturas"]["janelas_laterais"]) == (3000.0, 1000.0)  # spec = L,H
    bk = PS.to_build_kwargs(s)
    jb = bk["aberturas"]["janelas_laterais"]
    assert jb is not None and jb[1] > jb[0]         # build = faixa valida (nao quebra)


def test_portao_permanece_LH():
    # portao usa (L,H) no build (linha 1111 do build_galpao) - NAO converter
    ab = PS.aberturas_para_build({"portao_frente": (4500, 2500),
                                  "janelas_laterais": (3000, 1000)}, eave_mm=8000.0)
    assert tuple(ab["portao_frente"]) == (4500, 2500)          # intacto
    assert ab["janelas_laterais"][1] > ab["janelas_laterais"][0]
