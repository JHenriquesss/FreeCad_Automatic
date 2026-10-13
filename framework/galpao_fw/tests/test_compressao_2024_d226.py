# ============================================================================
# test_compressao_2024_d226.py - COMPRESSAO PELA NBR 8800:2024 (D226): area
# efetiva de 5.3.4 (no lugar do fator Q do Anexo F de 2008) e flambagem por
# torcao em 5.3.5.1. Valores esperados sao contas a mao.
# ============================================================================
"""Compressao do perfil I: chi, area efetiva e forca de flambagem."""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import check_nbr8800 as C
import perfis

FY = 250e3
RE = math.sqrt(200e6 / FY)          # raiz(E/fy) = 28,284


def test_elemento_dentro_do_limite_fica_inteiro():
    # aba AL com b/t = 15 ; limite 0,56 x 28,284 / raiz(0,8) = 17,71 -> inteira
    assert C._largura_efetiva(0.150, 0.010, 0.56 * RE, C.C_AL, 0.8, FY) == 0.150


def test_largura_efetiva_da_alma_a_mao():
    # alma AA: b/t = 60 ; lim = 1,49 x 28,284 = 42,14 ; chi = 0,9
    # sigma_el = (1,31 x 42,14 / 60)^2 fy = 0,8466 fy
    # raiz(sigma_el / (chi fy)) = raiz(0,8466 / 0,9) = 0,9699
    # bef = b (1 - 0,18 x 0,9699) x 0,9699 = 0,8006 b
    lim = 1.49 * RE
    bef = C._largura_efetiva(0.600, 0.010, lim, C.C_AA, 0.9, FY)
    raiz = math.sqrt((1.31 * lim / 60.0) ** 2 / 0.9)
    assert bef == pytest.approx(0.600 * (1 - 0.18 * raiz) * raiz)
    assert bef / 0.600 == pytest.approx(0.8006, abs=0.0005)


def test_quanto_menor_o_chi_menos_reducao():
    # a tensao que o elemento ve e' chi.fy: barra esbelta nao chega a flambar a alma
    lim = 1.49 * RE
    assert C._largura_efetiva(0.5, 0.01, lim, C.C_AA, 0.3, FY) == 0.5
    assert C._largura_efetiva(0.5, 0.01, lim, C.C_AA, 1.0, FY) < 0.5


def test_perfil_compacto_tem_area_efetiva_igual_a_bruta():
    s = perfis.PERFIS["HEA200"]
    aef, mesa, alma = C.area_efetiva(s, FY, 1.0)
    assert (aef, mesa, alma) == (s["A"], 1.0, 1.0)


def test_ipe500_so_a_alma_reduz():
    s = perfis.PERFIS["IPE500"]
    aef, mesa, alma = C.area_efetiva(s, FY, 1.0)
    h = s["d"] - 2 * s["tf"]
    assert mesa == 1.0 and alma < 1.0
    assert aef == pytest.approx(s["A"] - h * (1 - alma) * s["tw"])


def test_forca_resistente_e_chi_aef_fy():
    s = perfis.PERFIS["IPE500"]
    r = C.verifica(s, FY, L=8.0, Nsd=130.0, Msd=0.0, Vsd=0.0, Lb=2.0)
    assert r["lambda0"] == pytest.approx(math.sqrt(s["A"] * FY / r["Ne"]))
    assert r["Nc_Rd"] == pytest.approx(r["chi"] * r["Aef"] * FY / 1.10)
    assert r["Ne"] == min(r["Nex"], r["Ney"], r["Nez"])


def test_torcao_a_mao_e_governa_quando_y_esta_travado():
    s = perfis.PERFIS["IPE500"]
    Cw, J = C._cw_j(s)
    r = C.verifica(s, FY, L=3.0, Nsd=100.0, Msd=0.0, Vsd=0.0, Lb=3.0)
    r0_2 = (s["Ix"] + s["Iy"]) / s["A"]
    assert r["Nez"] == pytest.approx((math.pi ** 2 * 200e6 * Cw / 9.0 + 77e6 * J) / r0_2)
    # travamento so' a flexao em y (Ky pequeno nao vale para a torcao no modelo):
    # com os mesmos comprimentos, a torcao do IPE500 fica entre Ney e Nex
    assert r["Ney"] < r["Nez"] < r["Nex"]
