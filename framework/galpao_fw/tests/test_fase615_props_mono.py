# ============================================================================
# test_fase615_props_mono.py - RED tests da Fase 6.15.
# props_I_mono: propriedades de perfil I MONOSSIMETRICO (mesas diferentes) e o
# ramo monossimetrico real do DG25 (F_L 5.4-15 via Sxt/Sxc, rt 5.4-11 via bfc).
# Criterio de aceite: reducao EXATA ao duplo-simetrico (alma_variavel.props_I).
# ============================================================================
import os
import sys
import math
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import props_I_mono as pm
import alma_variavel as av
import dg25_ltb as dg

FY = 345e3


def test_reduz_ao_duplo_simetrico():
    d, bf, tw, tf = 0.60, 0.25, 0.008, 0.016
    m = pm.props_I_mono(d, bf, tf, bf, tf, tw)
    s = av.props_I(d, bf, tw, tf)
    for k in ("A", "Ix", "Iy", "Wx", "Zx", "rx", "ry", "Av"):
        assert abs(m[k] - s[k]) < 1e-9, f"{k}: mono={m[k]} dupl={s[k]}"


def test_simetrico_Wxc_igual_Wxt():
    m = pm.props_I_mono(0.60, 0.25, 0.016, 0.25, 0.016, 0.008)
    assert abs(m["Wxc"] - m["Wxt"]) < 1e-12
    assert abs(m["hc"] - (0.60 - 2 * 0.016)) < 1e-9
    assert abs(m["ho"] - (0.60 - 0.016)) < 1e-12
    assert abs(m["Iyc_Iy"] - 0.5) < 1e-3


def test_mesa_comprimida_maior_centroide_sobe():
    m = pm.props_I_mono(0.60, 0.30, 0.019, 0.20, 0.0125, 0.008)
    assert m["cc"] < m["ct"]                    # centroide mais perto do topo
    assert m["Wxc"] > m["Wxt"]                  # Sxc>Sxt (fibra comp. mais perto)
    assert m["Iyc_Iy"] > 0.5                    # mesa comp. domina Iy
    assert m["hc"] > 0 and m["hp"] > 0 and m["ho"] > 0


def test_zx_maior_que_modulo_elastico_minimo():
    # plastico Zx >= modulo elastico da fibra critica (S_min = Ix/c_max). O outro
    # modulo (fibra menos solicitada) pode superar Zx em secao muito assimetrica.
    m = pm.props_I_mono(0.70, 0.28, 0.016, 0.18, 0.012, 0.008)
    assert m["Zx"] > min(m["Wxc"], m["Wxt"]) > 0


def test_cw_reduz_a_Iy_ho2_sobre_4():
    # Cw mono (Iyc*Iyt/(Iyc+Iyt)) reduz a Iy*ho^2/4 a menos do termo tw^3 da alma
    d, bf, tf, tw = 0.60, 0.25, 0.016, 0.008
    m = pm.props_I_mono(d, bf, tf, bf, tf, tw)
    ho = d - tf
    assert abs(m["Cw"] - m["Iy"] * ho ** 2 / 4.0) / (m["Iy"] * ho ** 2 / 4.0) < 1e-3


def test_dg25_rt_usa_bfc():
    # rt deve escalar com a mesa comprimida (bfc), nao a tracionada
    m1 = pm.props_I_mono(0.60, 0.30, 0.016, 0.15, 0.012, 0.008)
    m2 = pm.props_I_mono(0.60, 0.20, 0.016, 0.15, 0.012, 0.008)
    assert dg.rt(m1) > dg.rt(m2)                # bfc maior -> rt maior
    assert abs(dg.rt(m1) - m1["rt"]) < 1e-12    # dg25 usa o rt pronto


def test_rt_usa_h_livre_da_alma_nao_hc():
    # parecer item 45 F2: em 5.4-11 o termo ao quadrado e h = ALTURA LIVRE da alma
    # (hw), NAO hc. Numa secao mono forte hc<<hw; rt tem de bater com a formula em hw.
    m = pm.props_I_mono(0.60, 0.30, 0.019, 0.15, 0.0095, 0.008)
    hw, hc, ho, d, tw = m["hw"], m["hc"], m["ho"], m["d"], m["tw"]
    assert hc < 0.9 * hw                                  # geometria discrimina hw x hc
    aw = hc * tw / (0.30 * 0.019)                         # aw usa hc (correto)
    rt_hw = 0.30 / math.sqrt(12.0 * (ho / d + (1.0 / 6.0) * aw * hw ** 2 / (ho * d)))
    rt_hc = 0.30 / math.sqrt(12.0 * (ho / d + (1.0 / 6.0) * aw * hc ** 2 / (ho * d)))
    assert abs(m["rt"] - rt_hw) < 1e-12                   # usa hw
    assert abs(m["rt"] - rt_hc) > 1e-4                    # e NAO hc


def test_dg25_FL_clampa_em_meia_fy():
    # mesa tracionada pequena -> Sxt/Sxc<0.5 -> F_L = 0.5 Fy (limite inferior 5.4-15)
    m = pm.props_I_mono(0.60, 0.28, 0.019, 0.12, 0.0095, 0.008)
    assert m["Wxt"] / m["Wxc"] < 0.5
    assert abs(dg.f_L(m, FY) - 0.5 * FY) < 1e-3


def test_dg25_FL_rampa_monossimetrica():
    # procura uma geometria com 0.5<Sxt/Sxc<0.7 -> F_L = Fy*Sxt/Sxc (5.4-15 rampa)
    achou = False
    for bft in (0.17, 0.18, 0.19, 0.20, 0.21):
        m = pm.props_I_mono(0.60, 0.26, 0.016, bft, 0.011, 0.008)
        r = m["Wxt"] / m["Wxc"]
        if 0.5 < r < 0.7:
            assert abs(dg.f_L(m, FY) - FY * r) < 1e-3
            achou = True
    assert achou, "nenhuma geometria caiu na faixa da rampa 5.4-15"


def test_dg25_mn_roda_em_secao_mono():
    m = pm.props_I_mono(0.60, 0.28, 0.019, 0.12, 0.0095, 0.008)
    mn = dg.mn_ltb_dg(m, FY, Lb=4.0, Cb=1.0)
    assert mn["Mn"] > 0 and mn["regiao"] in ("a", "b", "c")
    assert mn["Mn"] <= mn["M_cfy"] + 1e-6


def test_dg25_duplo_sim_inalterado_via_mono():
    # secao duplo-sim montada por props_I_mono deve dar o mesmo Mn que por props_I
    d, bf, tw, tf = 0.60, 0.25, 0.008, 0.016
    a = dg.mn_ltb_dg(av.props_I(d, bf, tw, tf), FY, 4.0, 1.0)["Mn"]
    b = dg.mn_ltb_dg(pm.props_I_mono(d, bf, tf, bf, tf, tw), FY, 4.0, 1.0)["Mn"]
    assert abs(a - b) / a < 1e-3
