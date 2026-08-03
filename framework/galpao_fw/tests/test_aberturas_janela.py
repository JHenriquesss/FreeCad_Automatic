# ============================================================================
# test_aberturas_janela.py - convencao CANONICA das janelas laterais.
#
# O spec guarda a FAIXA (z_base, z_topo) - a mesma convencao que build_galpao,
# ifc_emit e modelo_neutro consomem, e o default do build. A conversao (L,H do
# usuario) -> faixa acontece UMA vez, no boundary de entrada (wizard.construir_spec
# via PS._janela_band). O mapper to_build_kwargs/aberturas_para_build e PASS-THROUGH
# (nao reconverte). Antes havia DUPLA-CONVERSAO (wizard convertia E o mapper
# reconvertia a faixa como se fosse (L,H)); ver memoria janela-dupla-conversao-aberta
# e open-thread T40.
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
    # _janela_band e o UNICO conversor (L,H[,peitoril]) -> (z_base, z_topo), usado
    # no boundary de entrada (wizard). (largura, altura) -> faixa com peitoril default.
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


def test_wizard_grava_faixa_no_spec():
    # convencao canonica: o wizard converte (L,H) do usuario na FAIXA e grava no spec
    # (peitoril default 1000; janela de 1000 de altura -> (1000, 2000)).
    r = dict(area_lote_m2=1000, span=20, comprimento=28.5, eave=8, v0=45,
             sigma_solo=150, fund_tipo="sapata",
             ab_janelas_lat=(3000.0, 1000.0))
    s = WZ.construir_spec(r, slug="t_jan")
    assert tuple(s["aberturas"]["janelas_laterais"]) == (1000.0, 2000.0)  # spec = FAIXA


def test_to_build_kwargs_nao_reconverte_janela():
    # REGRESSAO T40 (dupla-conversao): o mapper NAO pode reconverter a faixa ja pronta.
    # A faixa que sai de to_build_kwargs tem de ser IDENTICA a do spec (pass-through).
    r = dict(area_lote_m2=1000, span=20, comprimento=28.5, eave=8, v0=45,
             sigma_solo=150, fund_tipo="sapata",
             ab_janelas_lat=(3000.0, 1000.0), janela_peitoril=1200.0)
    s = WZ.construir_spec(r, slug="t_jan")
    faixa_spec = tuple(s["aberturas"]["janelas_laterais"])
    assert faixa_spec == (1200.0, 2200.0)                     # convertida 1x na entrada
    bk = PS.to_build_kwargs(s)
    jb = tuple(bk["aberturas"]["janelas_laterais"])
    assert jb == faixa_spec                                   # mapper = pass-through
    assert jb[1] > jb[0]                                      # faixa valida (nao quebra o build)


def test_aberturas_para_build_pass_through():
    # canonica = faixa; portao (L,H) e janela (faixa) passam INTACTOS pelo mapper.
    ab = PS.aberturas_para_build({"portao_frente": (4500, 2500),
                                  "janelas_laterais": (1000, 2000)}, eave_mm=8000.0)
    assert tuple(ab["portao_frente"]) == (4500, 2500)          # portao intacto (L,H)
    assert tuple(ab["janelas_laterais"]) == (1000, 2000)       # faixa intacta (sem reconversao)
