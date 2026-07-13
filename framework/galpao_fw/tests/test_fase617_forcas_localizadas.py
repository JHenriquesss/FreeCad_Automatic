# ============================================================================
# test_fase617_forcas_localizadas.py - RED tests da Fase 6.17.
# Forcas transversais localizadas + enrijecedor de apoio (NBR 8800 Secao 5.7).
# Valores conferidos a mao contra as equacoes verbatim do PDF (pgs 57-62).
# ============================================================================
import os
import sys
import math
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import forcas_localizadas as fl
import alma_variavel as av

FY = 345e3
GA1 = 1.10
E = 200e6


def _sec():
    return av.props_I(0.60, 0.25, 0.008, 0.016)


def test_flexao_local_mesa_valor():
    r = fl.flexao_local_mesa(_sec(), FY)
    esperado = 6.25 * 0.016 ** 2 * FY / GA1
    assert abs(r["F_Rd"] - esperado) < 1e-6          # ~501.8 kN


def test_flexao_local_mesa_dispensada_carga_curta():
    r = fl.flexao_local_mesa(_sec(), FY, l_carga=0.02)   # <0,15*0,25=0,0375
    assert r["aplica"] is False


def test_flexao_local_mesa_meia_perto_extremidade():
    s = _sec()
    cheia = fl.flexao_local_mesa(s, FY)["F_Rd"]
    meia = fl.flexao_local_mesa(s, FY, dist_extremidade=0.05)["F_Rd"]  # <10*0,016
    assert abs(meia - cheia / 2.0) < 1e-6


def test_escoamento_local_alma_interior_e_extremidade():
    s = _sec()
    i = fl.escoamento_local_alma(s, FY, ln=0.10, k=0.02, na_extremidade=False)
    e = fl.escoamento_local_alma(s, FY, ln=0.10, k=0.02, na_extremidade=True)
    assert abs(i["F_Rd"] - 1.10 * (5 * 0.02 + 0.10) * FY * 0.008 / GA1) < 1e-6
    assert abs(e["F_Rd"] - 1.10 * (2.5 * 0.02 + 0.10) * FY * 0.008 / GA1) < 1e-6
    assert e["F_Rd"] < i["F_Rd"]


def test_enrugamento_ramos():
    s = _sec()
    a = fl.enrugamento_alma(s, FY, ln=0.10, na_extremidade=False)
    assert a["ramo"].startswith("a")
    b1 = fl.enrugamento_alma(s, FY, ln=0.05, na_extremidade=True)   # ln/d=0.083<=0.2
    b2 = fl.enrugamento_alma(s, FY, ln=0.30, na_extremidade=True)   # ln/d=0.5>0.2
    assert "<=0,2" in b1["ramo"] and ">0,2" in b2["ramo"]
    assert a["F_Rd"] > b1["F_Rd"]                     # interior > extremidade


def test_flambagem_alma_compressao_valor_e_meia():
    s = _sec()
    h = 0.60 - 2 * 0.016
    esperado = 24.0 * 0.008 ** 3 * math.sqrt(E * FY) / (h * GA1)
    assert abs(fl.flambagem_alma_compressao(s, FY)["F_Rd"] - esperado) < 1e-3
    assert abs(fl.flambagem_alma_compressao(s, FY, True)["F_Rd"] - esperado / 2) < 1e-3


def test_flambagem_lateral_alma_aplicabilidade():
    s = _sec()
    Mr = 400.0
    # Lb grande -> l/bf grande -> razao (h/tw)/(l/bf) pequena -> aplica.
    # Lb pequeno -> razao grande -> acima de 2,30 -> nao ocorre (5.7.5.3).
    aplica = fl.flambagem_lateral_alma(s, FY, Lb=9.0, Msd=100.0, Mr=Mr)
    naoc = fl.flambagem_lateral_alma(s, FY, Lb=3.0, Msd=100.0, Mr=Mr)
    assert aplica["aplica"] is True and aplica["F_Rd"] > 0
    assert naoc["aplica"] is False                    # razao>2,30 (5.7.5.3)
    # Cr dobra quando Msd<Mr (32E) vs Msd>=Mr (16E)
    lo = fl.flambagem_lateral_alma(s, FY, 9.0, Msd=100.0, Mr=Mr)["F_Rd"]
    hi = fl.flambagem_lateral_alma(s, FY, 9.0, Msd=500.0, Mr=Mr)["F_Rd"]
    assert abs(lo / hi - 2.0) < 1e-6


def test_geometria_enrijecedor_5795():
    s = _sec()
    ok = fl.checa_geometria_enrijecedor(s, b_st=0.10, t_st=0.0125)
    assert ok["ok"] is True
    # espessura fina viola t_st>=b_st/15 e t_st>=tf/2
    ruim = fl.checa_geometria_enrijecedor(s, b_st=0.12, t_st=0.005)
    assert ruim["ok"] is False and ruim["ok_espessura_mesa"] is False


def test_enrijecedor_apoio_barra_comprimida():
    s = _sec()
    r = fl.enrijecedor_apoio(s, FY, b_st=0.10, t_st=0.0125, F_sd=500.0)
    assert r["N_Rd"] > 0 and 0 < r["chi"] <= 1.0
    assert abs(r["Lb"] - 0.75 * (0.60 - 2 * 0.016)) < 1e-9   # Lb=0,75h
    assert abs(r["faixa_alma"] - 12 * 0.008) < 1e-9          # extremidade 12tw
    assert r["atende"] is (r["N_Rd"] >= 500.0)


def test_dimensiona_enrijecedor_apoio():
    s = _sec()
    base = fl.reacao_apoio(s, FY, 0.0, ln=0.10, k=0.02)["F_Rd_min"]
    F_sd = base * 1.8                                  # excede -> exige enrijecedor
    dim = fl.dimensiona_enrijecedor_apoio(s, FY, F_sd)
    assert dim["atende"] and dim["escolha"]["t_st"] >= 0.016 / 2.0   # 5.7.9.5b


def test_reacao_apoio_precisa_enrijecedor():
    s = _sec()
    r_ok = fl.reacao_apoio(s, FY, 100.0, ln=0.10, k=0.02)
    r_no = fl.reacao_apoio(s, FY, 5000.0, ln=0.10, k=0.02)
    assert r_ok["atende"] and not r_ok["precisa_enrijecedor"]
    assert not r_no["atende"] and r_no["precisa_enrijecedor"]
    assert r_no["governa"] in r_no["estados"]
