# ============================================================================
# test_fase616_dg25_envelope.py - RED tests da Fase 6.16.
# DG25 envelope de estados-limite de flexao (§5.4.4 FLB / §5.4.5 TFY /
# §5.4.6 ruptura / §5.4.7 razao). Mn nominal = MENOR entre CFY/LTB/FLB/TFY/TFR.
# Base verbatim AISC Design Guide 25 pgs 62-64 (imagens). INFORMATIVO.
# ============================================================================
import os
import sys
import math
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import dg25_ltb as dg
import props_I_mono as pm
import alma_variavel as av

FY = 250e3
FU = 400e3


def test_flb_mesa_compacta_nao_aplica():
    s = av.props_I(0.60, 0.25, 0.008, 0.016)     # bf/2tf=7.8 < 0.38 sqrt(E/Fy)~10.8
    r = dg.mn_flb(s, FY)
    assert r["regiao"] == "a" and r["aplica"] is False
    assert abs(r["Mn"] - dg.m_cfy(s, FY)) < 1e-6   # teto CFY (sem reducao)


def test_flb_mesa_esbelta_regiao_c():
    s = av.props_I(0.60, 0.30, 0.008, 0.006)     # bf/2tf=25 -> esbelta
    r = dg.mn_flb(s, FY)
    assert r["regiao"] == "c" and r["aplica"] is True
    assert r["Mn"] < dg.m_cfy(s, FY)              # FLB reduz


def test_kc_usa_h_livre_da_alma_nao_hc():
    # parecer item 46 F1: kc (5.4-24) = 4/sqrt(h/tw), h = altura LIVRE da alma (hw),
    # NAO hc. Verbatim DG25 pag 63. Numa secao mono hc != hw discrimina.
    m = pm.props_I_mono(0.70, 0.35, 0.010, 0.18, 0.012, 0.006)
    hw, hc, tw = m["hw"], m["hc"], m["tw"]
    assert abs(hc - hw) > 0.05 * hw                  # geometria discrimina
    kc_hw = min(max(4.0 / math.sqrt(hw / tw), 0.35), 0.76)
    kc_hc = min(max(4.0 / math.sqrt(hc / tw), 0.35), 0.76)
    assert abs(dg.kc_flb(m) - kc_hw) < 1e-9          # usa hw
    assert abs(dg.kc_flb(m) - kc_hc) > 1e-4          # e NAO hc


def test_kc_duplo_sim_inalterado():
    # hc == hw no duplo-sim -> kc identico ao calculo por hc
    s = av.props_I(0.60, 0.25, 0.008, 0.009)
    hw = s["d"] - 2 * s["tf"]
    assert abs(dg.kc_flb(s) - min(max(4.0 / math.sqrt(hw / s["tw"]), 0.35), 0.76)) < 1e-12


def test_flb_mesa_nao_compacta_regiao_b():
    s = av.props_I(0.60, 0.25, 0.008, 0.009)     # bf/2tf=13.9 -> intermediaria
    r = dg.mn_flb(s, FY)
    assert r["regiao"] == "b" and r["aplica"] is True
    assert r["Mn"] <= dg.m_cfy(s, FY) + 1e-6


def test_tfy_duplo_sim_nao_aplica():
    s = av.props_I(0.60, 0.25, 0.008, 0.016)
    assert dg.mn_tfy(s, FY)["aplica"] is False   # Sxt==Sxc


def test_tfy_mono_mesa_tracionada_menor_aplica():
    m = pm.props_I_mono(0.60, 0.28, 0.019, 0.12, 0.0095, 0.008)
    r = dg.mn_tfy(m, FY)
    assert r["aplica"] is True                    # Sxt<Sxc
    assert abs(r["Mn"] - r["Rpt"] * FY * m["Wxt"]) < 1e-6


def test_tfr_sem_furos_nao_aplica():
    m = pm.props_I_mono(0.60, 0.28, 0.019, 0.12, 0.0095, 0.008)
    assert dg.mn_tfr(m, FY, FU, n_furos=0, dh=0.0)["aplica"] is False


def test_tfr_com_furos_reduz():
    m = pm.props_I_mono(0.60, 0.28, 0.019, 0.12, 0.0095, 0.008)
    r = dg.mn_tfr(m, FY, FU, n_furos=2, dh=0.026)
    assert r["aplica"] is True
    assert r["Afn"] < r["Afg"] and r["Yt"] == 1.0
    assert r["Mn"] < FY * m["Wxt"]                # ruptura abaixo do escoamento


def test_envelope_governa_menor_estado():
    s = av.props_I(0.60, 0.25, 0.008, 0.016)
    e = dg.mn_envelope(s, FY, Lb=6.0, Cb=1.0)
    assert e["Mn"] == min(e["estados"].values())
    assert e["governa"] in e["estados"]
    assert "TFY" not in e["estados"]              # duplo-sim
    assert e["Mn"] <= e["estados"]["CFY"] + 1e-6  # CFY e o teto


def test_envelope_mono_com_furos_inclui_todos():
    m = pm.props_I_mono(0.60, 0.30, 0.006, 0.12, 0.0095, 0.008)  # mesa comp esbelta
    e = dg.mn_envelope(m, FY, Lb=5.0, Cb=1.0, fu=FU, n_furos=2, dh=0.026)
    assert "FLB" in e["estados"] and "TFY" in e["estados"] and "TFR" in e["estados"]
    assert e["Mn"] == min(e["estados"].values())
    assert e["Mn"] > 0


def test_envelope_prismatico_curto_lb_cfy_ou_ltb():
    # Lb curto + mesa compacta -> FLB neutro; governa CFY ou LTB
    s = av.props_I(0.60, 0.25, 0.008, 0.016)
    e = dg.mn_envelope(s, FY, Lb=1.5, Cb=1.0)
    assert e["governa"] in ("CFY", "LTB", "FLB")
