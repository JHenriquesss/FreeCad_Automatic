"""FLT da chapa retangular macica do console da ponte (NBR 8800 Anexo G / Tab. G.1).

Fecha o gap A3 da auditoria: o console e uma chapa em balanco cujo bordo comprimido
pode TOMBAR (flambagem lateral com torcao) antes de plastificar. Seccao macica NAO
tem flambagem local (G.1.2) -> o estado-limite e a FLT (Tabela G.1, linha "secoes
solidas retangulares fletidas em relacao ao eixo de maior momento de inercia").
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import console_ponte as CP
from check_nbr8800 import GA1, E


def test_reproduz_exemplo_pfeil():
    # Exemplo resolvido (via NotebookLM): chapa t=12,5mm x L=270mm, balanco
    # ecc=145mm, fy=250 MPa. Lb=2*ecc=290mm; regime INELASTICO.
    r = CP.mrd_flt_chapa(0.0125, 0.27, 0.145, 250e3)
    assert abs(r["Lb"] - 0.29) < 1e-9
    assert r["regime"] == "inelastico (FLT)"
    assert abs(r["lam"] - 80.4) < 0.5
    assert abs(r["lam_p"] - 10.96) < 0.2
    assert abs(r["lam_r"] - 252.9) < 2.0
    # Md do exemplo = 15,95 kN.m < Mrd (~46,8) -> ATENDE com folga
    assert 44.0 < r["Mrd"] < 49.0
    assert 15.95 < r["Mrd"]


def test_propriedades_da_secao_retangular():
    t, L = 0.0125, 0.27
    r = CP.mrd_flt_chapa(t, L, 0.145, 250e3)
    assert abs(r["W"] - t * L ** 2 / 6.0) < 1e-12          # elastico
    assert abs(r["Z"] - t * L ** 2 / 4.0) < 1e-12          # plastico
    assert abs(r["J"] - (L * t ** 3 / 3.0) * (1 - 0.63 * t / L)) < 1e-15


def test_balanco_curto_plastifica():
    # lam <= lam_p -> Mrd = Mpl/ga1 (sem reducao por FLT)
    r = CP.mrd_flt_chapa(0.0125, 0.27, 0.002, 250e3)
    assert r["regime"] == "plastificacao"
    assert abs(r["Mrd"] - r["Mpl"] / GA1) < 1e-12


def test_balanco_longo_esbelto_regime_elastico():
    # chapa fina, balanco longo -> lam > lam_r -> Mrd = Mcr/ga1 (FLT elastica)
    r = CP.mrd_flt_chapa(0.008, 0.30, 1.20, 250e3)
    assert r["regime"] == "elastico (FLT)"
    assert r["Mrd"] < r["Mpl"] / GA1


def test_flt_monotona_com_o_balanco():
    # quanto maior o balanco (Lb), menor o Mrd
    ms = [CP.mrd_flt_chapa(0.016, 0.45, e, 250e3)["Mrd"]
          for e in (0.10, 0.30, 0.60, 1.00)]
    assert all(ms[i] >= ms[i + 1] for i in range(len(ms) - 1))


def test_flt_nunca_supera_o_plastico():
    for e in (0.01, 0.1, 0.3, 1.0, 2.0):
        r = CP.mrd_flt_chapa(0.012, 0.35, e, 250e3)
        assert r["Mrd"] <= r["Mpl"] / GA1 + 1e-12


def test_verifica_console_usa_flt_e_pode_reprovar_por_flambagem():
    # chapa DEEP fina em balanco longo: a FLT governa a flexao (o check elastico
    # ingenuo NAO pegaria). Regime nao-plastico e util de flexao alta.
    r = CP.verifica_console({"Rv": 250.0, "Ht": 0.0, "ecc": 0.9, "t": 0.008,
                             "L": 0.30, "fy": 250e3, "fu": 400e3})
    cf = r["chapa_flexao"]
    assert cf["flt_regime"] in ("inelastico (FLT)", "elastico (FLT)")
    # a FLT reduz o M_Rd abaixo do plastico Mpl/ga1
    assert cf["M_Rd"] < cf["Mpl"] / GA1


def test_selftest_do_modulo():
    CP._selftest()
