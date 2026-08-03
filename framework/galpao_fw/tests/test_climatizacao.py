"""Climatizacao / ar-condicionado do galpao (NBR 16401): carga termica, capacidade
TR/kW/BTU, vazao de renovacao e condicoes de projeto. Puro -> CI."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import climatizacao_nbr16401 as cl


def test_selftest():
    cl._selftest()


def test_conversoes():
    assert cl.TR_KW == 3.517 and cl.TR_BTU_H == 12000.0
    assert abs(cl.kw_para_tr(3.517) - 1.0) < 1e-9
    assert cl.btu_para_tr(12000.0) == 1.0


def test_conducao_e_pessoas():
    assert cl.conducao(2.0, 100.0, 8.0) == 1600.0
    assert cl.carga_pessoas(10, "leve") == 2350.0
    import pytest
    with pytest.raises(ValueError):
        cl.carga_pessoas(1, "inexistente")


def test_vazao_ar_exterior():
    # 27/pessoa + 1,5/m2
    assert cl.vazao_ar_exterior(10, 800.0) == 1470.0


def test_estimativa_galpao():
    assert abs(cl.capacidade_estimativa(800.0, "galpao") - 33.333) < 0.01
    import pytest
    with pytest.raises(ValueError):
        cl.capacidade_estimativa(100.0, "inexistente")


def test_dimensiona_estimativa():
    r = cl.dimensiona_climatizacao({"area_m2": 800.0, "tipo": "galpao"})
    assert abs(r["capacidade_TR"] - 33.33) < 0.1
    assert r["t_interna_C"] == (23.0, 25.0) and r["UR_pct"] == (40.0, 60.0)
    assert r["vel_ar_max_ms"] == 0.20 and r["OK"]


def test_dimensiona_detalhado():
    d = cl.dimensiona_climatizacao({"area_m2": 100.0, "tipo": "escritorio",
                                    "metodo": "detalhado", "n_pessoas": 10,
                                    "envoltoria": [{"U": 2.0, "A": 100.0, "dT": 8.0}],
                                    "P_iluminacao_W": 1000.0, "P_equipamentos_W": 1500.0,
                                    "dT_ar_ext": 8.0})
    V = cl.vazao_ar_exterior(10, 100.0)
    esperado = 1600 + 2350 + 1000 + 1500 + 0.335 * V * 8
    assert abs(d["detalhe"]["carga_total_W"] - esperado) < 1.0
    assert d["capacidade_TR"] > 0


# --- DUTOS (geometria de coordenacao) ---
import math


def test_vazao_insuflamento_da_fisica_do_ar():
    # V = Q/(0,335*dT). 117200 W / (0,335*10) = 34985 m3/h
    assert abs(cl.vazao_insuflamento(117200.0, 10.0) - 34985.07) < 1.0
    import pytest
    with pytest.raises(ValueError):
        cl.vazao_insuflamento(1000.0, 0.0)


def test_dimensiona_duto_secao_e_aspecto():
    du = cl.dimensiona_duto(34985.07, 6.0, aspecto=2.0)
    assert abs(du["area_m2"] - 1.62) < 0.02              # A = V/3600/v
    assert abs(du["largura_m"] / du["altura_m"] - 2.0) < 1e-6
    assert abs(du["largura_m"] * du["altura_m"] - du["area_m2"]) < 1e-3
    import pytest
    with pytest.raises(ValueError):
        cl.dimensiona_duto(1000.0, 0.0)


def test_velocidade_duto_nbr16401_tab1():
    # NBR 16401-1:2024 Tab.1 (classes de pressao): max de velocidade por classe
    assert cl.velocidade_max_duto(250) == 12.5      # classe default
    assert cl.velocidade_max_duto(125) == 10.0 and cl.velocidade_max_duto(750) == 20.0
    import pytest
    with pytest.raises(ValueError):
        cl.velocidade_max_duto(300)                 # fora da Tab.1 -> nao inventa


def test_dimensiona_duto_verifica_velocidade():
    Vi = cl.vazao_insuflamento(117200.0, 10.0)
    assert cl.dimensiona_duto(Vi, 6.0)["vel_OK"] is True        # 6 < 12,5 (classe 250)
    assert cl.dimensiona_duto(Vi, 15.0)["vel_OK"] is False      # 15 > 12,5
    assert cl.dimensiona_duto(Vi, 15.0, classe_pa=750)["vel_OK"] is True  # 15 < 20


def test_galpao_climatizacao_reprova_velocidade_excessiva():
    import galpao_climatizacao as gcl
    # vel de projeto acima do max da classe 250 -> gate do duto reprova
    r = gcl.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "vel_duto": 15.0})
    assert r["gates"]["duto_principal"]["OK"] is False
    assert r["gates"]["duto_principal"]["vel_max_ms"] == 12.5
    # subindo a classe de pressao (mais robusta) volta a atender
    r2 = gcl.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "vel_duto": 15.0,
                    "classe_pressao_pa": 750})
    assert r2["gates"]["duto_principal"]["OK"] is True
