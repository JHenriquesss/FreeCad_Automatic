"""Revisao total (gaps/bugs): entrada DEGENERADA (geometria/tensao/area/fator = 0 ou
negativa) deve virar ValueError LIMPO no padrao da casa, nao ZeroDivisionError cru.
Todos os pontos foram achados por harness adversarial. Puro -> CI."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_seguranca_incendio as gsi
import galpao_eletrico as ge
import galpao_concreto as gc
import luminotecnica_nbr8995 as lt
import fator_potencia as fpot
import curto_circuito as cc
import subestacao_nbr14039 as sub
import aterramento_nbr15749 as at
import spda_nbr5419 as spda
import condutores_nbr5410 as cond
import cargas_eletricas as cel


def test_incendio_geometria_nao_positiva():
    for geo in ({"L": 0, "W": 20, "H": 6}, {"L": 40, "W": 0, "H": 6},
                {"L": 40, "W": 20, "H": 0}, {"L": -40, "W": 20, "H": 6}):
        with pytest.raises(ValueError):
            gsi.rodar({"geometria": geo})
    # geometria valida ainda roda
    assert isinstance(gsi.rodar({"geometria": {"L": 40, "W": 20, "H": 6}})["ATENDE"], bool)


def test_eletrico_tensao_nao_positiva():
    with pytest.raises(ValueError):
        ge.rodar({"tensao_V": 0, "cargas": {"iluminacao_kW": 10}, "alimentador": {"L_km": 0.05}})
    with pytest.raises(ValueError):
        ge.rodar({"tensao_V": -380, "cargas": {"iluminacao_kW": 10}, "alimentador": {"L_km": 0.05}})


def test_concreto_geometria_nao_positiva():
    with pytest.raises(ValueError):
        gc.rodar({"vao": 0, "comprimento": 40, "pe_direito": 6, "sigma_solo_adm": 250})
    with pytest.raises(ValueError):
        gc.rodar({"vao": 10, "comprimento": 40, "pe_direito": 0, "sigma_solo_adm": 250})


def test_luminotecnica_area_e_fatores():
    base = {"pe_direito": 6, "atividade": "producao", "ambiente": "medio",
            "luminaria": "high_bay_led_100W"}
    with pytest.raises(ValueError):
        lt.projeto_luminotecnico(dict(base, C=0, L=0, Fu=0.6))
    with pytest.raises(ValueError):
        lt.projeto_luminotecnico(dict(base, C=40, L=20, Fu=0.0))
    # valido roda
    assert lt.projeto_luminotecnico(dict(base, C=40, L=20, Fu=0.6))["N_luminarias"] > 0


def test_turnkey_isola_geometria_invalida():
    # no turnkey, a geometria invalida vira ERRO ISOLADO da disciplina (nao derruba tudo)
    import galpao_turnkey as tk
    R = tk.rodar({"geometria": {"L": 0, "W": 0, "H": 0}, "incendio": {}})
    assert R["disciplinas"]["incendio"]["rodou"] is False
    assert "erro" in R["disciplinas"]["incendio"] and R["ATENDE"] is False


# --------- calculo eletrico: 2a varredura de entrada degenerada (modulos puros) -----
# Antes: divisao/dominio cru (ZeroDivisionError, math domain) com fator/tensao/geometria
# = 0. Agora: ValueError LIMPO [A CONFIRMAR]. Cada caso e' um ponto de crash real.

def test_fator_potencia_fp_fora_de_dominio():
    for fp in (0.0, -0.5, 1.5):
        with pytest.raises(ValueError):
            fpot.corrige_fator_potencia(100.0, fp)
    # fp valido roda
    assert fpot.corrige_fator_potencia(100.0, 0.80)["Qc_kVAr"] > 0


def test_curto_circuito_tensao_e_impedancia_e_xr():
    with pytest.raises(ValueError):
        cc.icc_simetrica(300.0, 0.0, 4.5)          # Vn = 0
    with pytest.raises(ValueError):
        cc.icc_simetrica(300.0, 0.38, 0.0)         # z% = 0
    with pytest.raises(ValueError):
        cc.fator_assimetria(0.0)                    # X/R = 0
    assert cc.icc_simetrica(300.0, 0.38, 4.5)["Ik3"] > 0


def test_subestacao_tensao_nao_positiva():
    with pytest.raises(ValueError):
        sub.corrente_nominal(225.0, 0.0)
    with pytest.raises(ValueError):
        sub.dimensiona_subestacao({"D_kVA": 210.0, "V_primaria_kV": 0.0})
    assert sub.dimensiona_subestacao({"D_kVA": 210.0})["Sn_kVA"] == 225


def test_aterramento_geometria_e_fatores():
    with pytest.raises(ValueError):
        at.resistencia_haste(100.0, 0.0, 0.02)     # L = 0
    with pytest.raises(ValueError):
        at.resistencia_haste(100.0, 3.0, 0.0)      # d = 0
    with pytest.raises(ValueError):
        at.resistencia_hastes_paralelo(33.9, 0, 0.75)   # n = 0
    with pytest.raises(ValueError):
        at.resistencia_hastes_paralelo(33.9, 4, 0.0)    # K = 0
    with pytest.raises(ValueError):
        at.resistencia_malha(100.0, 0.0, 400.0)    # A = 0
    with pytest.raises(ValueError):
        at.resistencia_malha(100.0, 1200.0, 0.0)   # L_cond = 0
    assert at.resistencia_haste(100.0, 3.0, 0.02) > 0


def test_spda_nivel_de_protecao_invalido():
    with pytest.raises(ValueError):
        spda.numero_descidas(120.0, "V")           # NP inexistente
    with pytest.raises(ValueError):
        spda.dimensiona_spda({"L": 40, "W": 20, "H": 6, "NP": "Z"})
    assert spda.dimensiona_spda({"L": 40, "W": 20, "H": 6, "NP": "III"})["n_descidas"] == 8


def test_condutores_tensao_nao_positiva():
    with pytest.raises(ValueError):
        cond.queda_pct(6, 27.0, 0.018, 0.0, "monofasico", 1.0)   # V = 0
    with pytest.raises(ValueError):
        cond.dimensiona_condutor({"IB": 27.0, "V": 0.0, "L_km": 0.018,
                                  "sistema": "monofasico", "n_cond": 2, "dv_max": 4.0})
    assert cond.queda_pct(6, 27.0, 0.018, 220.0, "monofasico", 1.0) > 0


def test_cargas_motor_eta_fp_e_iluminacao_fp():
    with pytest.raises(ValueError):
        cel.demanda_motor({"P_cv": 75.0, "eta": 0.0, "Fp": 0.86})   # eta = 0
    with pytest.raises(ValueError):
        cel.demanda_motor({"P_cv": 75.0, "eta": 0.92, "Fp": 0.0})   # Fp = 0
    with pytest.raises(ValueError):
        cel.demanda_iluminacao(10.0, fp=0.0)                        # fp = 0
    assert cel.demanda_motor({"P_cv": 75.0, "eta": 0.92, "Fp": 0.86})["D_kW"] > 0
