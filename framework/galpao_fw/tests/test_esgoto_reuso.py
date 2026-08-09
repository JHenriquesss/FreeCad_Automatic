"""Saneamento do lote sem rede: fossa septica (formula NBR 7229, coeficientes de
ENTRADA - nao inventados) + reuso de agua de chuva (cisterna por Rippl). CI puro."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import esgoto_reuso as er


def test_selftest():
    assert er._selftest() is True


def test_fossa_formula_nbr7229():
    """V = 1000 + N(C.T + K.Lf), exata."""
    f = er.volume_fossa_septica(50, 160.0, 0.75, 65.0, 1.0)
    assert f["volume_util_L"] == 1000 + 50 * (160 * 0.75 + 65 * 1)
    assert f["contribuicao_diaria_L"] == 50 * 160


def test_fossa_minimo_1000():
    assert er.volume_fossa_septica(1, 0.0, 0.0, 0.0, 0.0)["volume_util_L"] == 1000.0


def test_fossa_coeficiente_ausente_a_confirmar():
    """AR300: coeficiente da NBR 7229 nao informado -> ValueError (nao inventa)."""
    with pytest.raises(ValueError):
        er.volume_fossa_septica(10, None, 0.75, 65, 1)
    with pytest.raises(ValueError):
        er.volume_fossa_septica(10, 160, 0.75, -1, 1)


def test_sumidouro_area():
    assert er.area_sumidouro(8000.0, 40.0) == 200.0
    with pytest.raises(ValueError):
        er.area_sumidouro(8000.0, 0)


def test_oferta_chuva():
    """1 mm sobre 1 m2 = 1 L ; runoff multiplica."""
    assert er.oferta_chuva_mensal([100.0], 800.0, 0.8)[0] == 100 * 800 * 0.8


def test_rippl_sazonal_pede_mais_que_regular():
    regular = er.cisterna_rippl([120] * 12, 800.0, 50000.0)
    sazonal = er.cisterna_rippl([200, 200, 200, 50, 10, 5, 5, 10, 30, 80, 150, 200],
                                800.0, 50000.0)
    assert sazonal["volume_cisterna_L"] >= regular["volume_cisterna_L"]


def test_rippl_atendimento_limitado_a_100():
    r = er.cisterna_rippl([300] * 12, 1000.0, 10000.0)
    assert r["atendimento_pct"] == 100.0        # oferta >> demanda, mas cap 100%


def test_rippl_demanda_lista_e_escalar():
    a = er.cisterna_rippl([100] * 12, 800.0, 40000.0)
    b = er.cisterna_rippl([100] * 12, 800.0, [40000] * 12)
    assert a["volume_cisterna_L"] == b["volume_cisterna_L"]


def test_rippl_valida_12_meses():
    with pytest.raises(ValueError):
        er.cisterna_rippl([100] * 11, 800.0, 40000.0)


def test_dimensiona_esgoto_completo():
    d = er.dimensiona_esgoto({"N": 50, "C": 160.0, "T": 0.75, "K": 65.0, "Lf": 1.0,
                              "taxa_infiltracao_L_m2_dia": 40.0})
    assert d["fossa"]["volume_util_m3"] == 10.25
    assert d["sumidouro_area_m2"] == 200.0


def test_dimensiona_esgoto_sem_taxa_infiltracao():
    d = er.dimensiona_esgoto({"N": 20, "C": 160.0, "T": 1.0, "K": 65.0, "Lf": 1.0})
    assert "sumidouro_nota" in d and "A CONFIRMAR" in d["sumidouro_nota"]
