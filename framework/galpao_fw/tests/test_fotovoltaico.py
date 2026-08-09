"""Sistema fotovoltaico na cobertura (on-grid): area -> potencia -> geracao ->
compensacao do consumo. HSP e catalogo A CONFIRMAR. Camada PURA (CI)."""
import math
import os
import sys

from xml.dom.minidom import parseString

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import fotovoltaico as fv


def test_selftest():
    assert fv._selftest() is True


def test_potencia_instalavel():
    # 1000 m2 x 0,7 x 0,18 = 126 kWp
    assert abs(fv.potencia_instalavel(1000.0) - 126.0) < 1e-9
    with pytest.raises(ValueError):
        fv.potencia_instalavel(0)


def test_geracao_formula_cresesb():
    # E = P.HSP.PR ; 100 kWp x 5 x 0,78 = 390 kWh/dia
    g = fv.geracao(100.0, 5.0)
    assert abs(g["kwh_dia"] - 390.0) < 1e-9
    assert abs(g["kwh_ano"] - 390.0 * 365) < 1e-6
    with pytest.raises(ValueError):
        fv.geracao(100.0, 0)          # HSP nao informado


def test_n_modulos_e_inversores():
    assert fv.n_modulos(100.0) == math.ceil(100000.0 / 550.0)
    assert fv.n_inversores(100.0, 75.0) == 2
    with pytest.raises(ValueError):
        fv.n_inversores(100.0, 0)


def test_dimensiona_limitado_por_area():
    r = fv.dimensiona_fv({"area_cobertura_m2": 500.0, "HSP": 5.0,
                          "consumo_kwh_mes": 100000.0})
    assert r["OK"] and r["limitado_por"].startswith("area")
    assert r["potencia_kWp"] == r["potencia_teto_area_kWp"]
    assert r["cobertura_consumo_pct"] < 100.0


def test_dimensiona_limitado_por_consumo():
    r = fv.dimensiona_fv({"area_cobertura_m2": 2000.0, "HSP": 5.5,
                          "consumo_kwh_mes": 20000.0})
    assert r["limitado_por"].startswith("consumo")
    assert r["potencia_kWp"] < r["potencia_teto_area_kWp"]
    assert abs(r["cobertura_consumo_pct"] - 100.0) < 3.0


def test_sem_hsp_a_confirmar():
    r = fv.dimensiona_fv({"area_cobertura_m2": 800.0})
    assert r["OK"] is False and "A CONFIRMAR" in r["motivo"]
    assert r["potencia_teto_area_kWp"] > 0        # teto de area ainda e' util


def test_consumo_por_demanda_horas():
    r = fv.dimensiona_fv({"area_cobertura_m2": 2000.0, "HSP": 5.0,
                          "demanda_kW": 50.0, "horas_dia": 8.0})
    assert r["consumo_kwh_mes"] == round(50.0 * 8.0 * fv.DIAS_MES, 1)


def test_pr_e_hsp_ecoados_sem_arredondar():
    """PR e HSP sao inputs ecoados; nao devem virar 0,8 por arredondamento."""
    r = fv.dimensiona_fv({"area_cobertura_m2": 800.0, "HSP": 5.2,
                          "consumo_kwh_mes": 18000.0})
    assert r["geracao"]["PR"] == fv.PR_PADRAO      # 0,78 (nao 0,8)
    assert r["geracao"]["HSP"] == 5.2


def test_area_invalida_levanta():
    with pytest.raises(ValueError):
        fv.dimensiona_fv({"area_cobertura_m2": 0, "HSP": 5.0})


def test_grafico_svg_xml_valido():
    r = fv.dimensiona_fv({"area_cobertura_m2": 800.0, "HSP": 5.2,
                          "consumo_kwh_mes": 18000.0})
    svg = fv.grafico_svg(r)
    assert svg.startswith("<svg") and "SISTEMA FOTOVOLTAICO" in svg
    parseString(svg.encode("utf-8"))
    parseString(fv.grafico_svg({"OK": False, "motivo": "x"}).encode("utf-8"))
