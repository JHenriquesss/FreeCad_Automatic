"""Torcao e efeitos combinados (NBR 8800 5.5.2)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torcao_nbr8800 as tor


def test_J_perfil_I_formula():
    J, tmax = tor.J_perfil_I(bf=0.20, tf=0.012, d=0.20, tw=0.008)
    hw = 0.20 - 2 * 0.012
    esperado = (2 * 0.20 * 0.012 ** 3 + hw * 0.008 ** 3) / 3.0
    assert abs(J - esperado) < 1e-12 and abs(tmax - 0.012) < 1e-12


def test_aberta_torcao_nula_desprezivel():
    J, tmax = tor.J_perfil_I(0.20, 0.012, 0.20, 0.008)
    r = tor.verifica_torcao_aberta(0.0, J, tmax, 250e3)
    assert r["desprezivel"] and r["OK"] and not r["exige_analise_empenamento"]


def test_aberta_torcao_significativa_exige_empenamento():
    J, tmax = tor.J_perfil_I(0.20, 0.012, 0.20, 0.008)
    r = tor.verifica_torcao_aberta(5.0, J, tmax, 250e3)
    assert not r["desprezivel"] and r["exige_analise_empenamento"] and not r["OK"]
    assert abs(r["tau_t"] - 5.0 * tmax / J) < 1e-6
    assert "FLEXO-TORCAO" in r["flag"]


def test_limite_tau_60pct_fy():
    J, tmax = tor.J_perfil_I(0.20, 0.012, 0.20, 0.008)
    r = tor.verifica_torcao_aberta(1.0, J, tmax, 250e3)
    assert abs(r["tau_rd"] - 0.60 * 250e3 / tor.GA1) < 1e-6


def test_tubular_Trd_e_criterio_desprezar():
    Trd = tor.Trd_tubular_retangular(0.20, 0.20, 0.008, 250e3)
    assert Trd > 0
    it = tor.interacao_tubular(100.0, 800.0, 20.0, 90.0, 30.0, 300.0, 0.1 * Trd, Trd)
    assert it["desprezivel"] and abs(it["criterio_desprezar"] - 0.20 * Trd) < 1e-9


def test_tubular_interacao_quadratica_no_cortante_torcao():
    Trd = tor.Trd_tubular_retangular(0.20, 0.20, 0.008, 250e3)
    # V/Vrd + T/Trd entram ao QUADRADO (5.5.2.2)
    it = tor.interacao_tubular(0.0, 800.0, 0.0, 90.0, 150.0, 300.0, 0.5 * Trd, Trd)
    esperado = (150.0 / 300.0 + 0.5) ** 2
    assert abs(it["u"] - esperado) < 1e-9


def test_parede_fina_reduz_Trd():
    assert (tor.Trd_tubular_retangular(0.30, 0.30, 0.012, 250e3) >
            tor.Trd_tubular_retangular(0.30, 0.30, 0.004, 250e3))
