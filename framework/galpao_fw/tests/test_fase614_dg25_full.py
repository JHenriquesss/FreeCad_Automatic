# ============================================================================
# test_fase614_dg25_full.py - RED tests da Fase 6.14.
# DG25 FULL: momento nominal de FLT completo (Rpc/Rpg/3 regioes, 5.4-8..5.4-21),
# Cb tapered por tensoes (5.4-1/5.4-2), cross-check de CAPACIDADE (Cb NAO cancela).
# Base verbatim AISC Design Guide 25 pgs 58-62 (imagens). INFORMATIVO - nao dimensiona.
# ============================================================================
import os
import sys
import math
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, HERE)

FY = 250e3


def _sec(h, bf=0.25, tw=0.008, tf=0.016):
    import alma_variavel as av
    return av.props_I(h, bf, tw, tf)


# ==================== Rpc (5.4-4/5.4-5) =================================
def test_rpc_compacta_igual_mp_myc():
    import dg25_ltb as dg
    s = _sec(0.40, tw=0.012)                             # alma compacta hc/tw<=lpw
    lpw = 3.76 * math.sqrt(dg.E / FY)
    assert dg.hc(s) / s["tw"] <= lpw
    assert dg.rpc(s, FY) == pytest.approx(dg.mp_dg(s, FY) / dg.myc(s, FY), rel=1e-9)


def test_rpc_slender_um():
    import dg25_ltb as dg
    s = _sec(0.95, tw=0.004)                             # alma esbelta -> Rpc=1
    assert dg.hc(s) / s["tw"] >= 5.70 * math.sqrt(dg.E / FY)
    assert dg.rpc(s, FY) == pytest.approx(1.0)


def test_rpc_noncompact_interpola():
    import dg25_ltb as dg
    # alma nao-compacta (entre lpw e lrw): Rpc entre 1 e Mp/Myc
    s = _sec(0.70, tw=0.007)
    lam = dg.hc(s) / s["tw"]
    lpw = 3.76 * math.sqrt(dg.E / FY); lrw = 5.70 * math.sqrt(dg.E / FY)
    if lpw < lam < lrw:
        r = dg.rpc(s, FY)
        assert 1.0 <= r <= dg.mp_dg(s, FY) / dg.myc(s, FY) + 1e-9


# ==================== Rpg (5.4-6/5.4-7) =================================
def test_rpg_nao_esbelta_um():
    import dg25_ltb as dg
    s = _sec(0.40, tw=0.012)
    assert dg.rpg(s, FY) == pytest.approx(1.0)


def test_rpg_slender_menor_que_um():
    import dg25_ltb as dg
    s = _sec(0.95, tw=0.004)
    r = dg.rpg(s, FY)
    assert 0.0 < r < 1.0
    # verbatim 5.4-6 com aw capado a 10
    aw = min(dg.aw(s), 10.0)
    lam = dg.hc(s) / s["tw"]
    ref = 1.0 - aw / (1200.0 + 300.0 * aw) * (lam - 5.70 * math.sqrt(dg.E / FY))
    assert r == pytest.approx(min(ref, 1.0), rel=1e-9)


# ==================== F_L (5.4-14/5.4-15) ==============================
def test_fL_duplo_simetrico():
    import dg25_ltb as dg
    s = _sec(0.60)
    assert dg.f_L(s, FY) == pytest.approx(0.7 * FY)      # Sxt/Sxc=1 -> 0.7Fy


# ==================== Mn full (5.4-8..5.4-21) ==========================
def test_mn_positivo_e_bounded_por_cfy():
    import dg25_ltb as dg
    s = _sec(0.60)
    m = dg.mn_ltb_dg(s, FY, Lb=4.0, Cb=1.0)
    assert m["Mn"] > 0
    assert m["Mn"] <= m["M_cfy"] + 1e-6
    assert m["regiao"] in ("a", "b", "c")


def test_mn_cresce_quando_Lb_diminui():
    import dg25_ltb as dg
    s = _sec(0.60)
    m_curto = dg.mn_ltb_dg(s, FY, Lb=2.0, Cb=1.0)["Mn"]
    m_longo = dg.mn_ltb_dg(s, FY, Lb=8.0, Cb=1.0)["Mn"]
    assert m_curto >= m_longo > 0


def test_mn_regiao_a_quando_muito_curto():
    import dg25_ltb as dg
    s = _sec(0.60)
    # Lb muito pequeno -> F_eLTB/Fy >= 8.2 -> regiao (a), Mn = CFY
    m = dg.mn_ltb_dg(s, FY, Lb=0.3, Cb=1.0)
    assert m["regiao"] == "a"
    assert m["Mn"] == pytest.approx(m["M_cfy"], rel=1e-9)


def test_mn_regiao_c_quando_muito_longo():
    import dg25_ltb as dg
    s = _sec(0.60)
    m = dg.mn_ltb_dg(s, FY, Lb=15.0, Cb=1.0)
    assert m["regiao"] == "c"


# ==================== Cb tapered (5.4-1/5.4-2) =========================
def test_cb_uniforme_um():
    import dg25_ltb as dg
    assert dg.cb_tapered(f0=100.0, fmid=100.0, f2=100.0) == 1.0  # fmid/f2>=1
    assert dg.cb_tapered(f0=0.0, fmid=0.0, f2=0.0) == 1.0        # f2=0


def test_cb_gradiente_maior_que_um_limitado_23():
    import dg25_ltb as dg
    cb = dg.cb_tapered(f0=-40.0, fmid=30.0, f2=100.0)
    assert 1.0 <= cb <= 2.3


def test_cb_formula_verbatim():
    import dg25_ltb as dg
    f0, fmid, f2 = 20.0, 55.0, 100.0
    # |fmid|>=|(f0+f2)/2|? (20+100)/2=60 ; |55|<60 -> f1=f0=20
    f1 = f0
    r = f1 / f2
    assert dg.cb_tapered(f0, fmid, f2) == pytest.approx(
        min(1.75 - 1.05 * r + 0.3 * r ** 2, 2.3), rel=1e-9)


# ==================== cross_check_capacidade ===========================
def _segs(h1, h2, nseg=8, bf=0.22, tw=0.006, tf=0.014):
    import alma_variavel as av
    xs = [i / (nseg - 1) for i in range(nseg)]
    return [{"props": av.props_I(h1 + (h2 - h1) * x, bf, tw, tf),
             "h_m": h1 + (h2 - h1) * x} for x in xs]


def test_capacidade_cb_nao_cancela():
    import dg25_ltb as dg
    r1 = dg.cross_check_capacidade(_segs(0.90, 0.45), FY, 4.0, Cb=1.0)["razao"]
    r2 = dg.cross_check_capacidade(_segs(0.90, 0.45), FY, 4.0, Cb=1.6)["razao"]
    assert abs(r1 - r2) > 1e-6, "no cross-check de CAPACIDADE o Cb deve alterar a razao"


def test_capacidade_prismatico_finito():
    import dg25_ltb as dg
    r = dg.cross_check_capacidade(_segs(0.60, 0.60), FY, 4.0, Cb=1.0)
    assert math.isfinite(r["razao"]) and r["razao"] > 0
    assert r["regiao_dg"] in ("a", "b", "c")
    assert isinstance(r["converge"], bool)


def test_selftest_roda():
    import dg25_ltb as dg
    dg._selftest()


# ==================== integracao informativa ===========================
def test_integra_reporta_capacidade(tmp_path):
    import rodar_projeto as RP
    from test_fase6b_alma_variavel import _spec
    s = _spec(tipo="alma_variavel",
              tapered={"h_joelho": 0.90, "h_cumeeira": 0.45, "h_col_base": 0.35,
                       "bf": 0.22, "tw": 0.006, "tf": 0.014})
    r = RP.calcular(s, str(tmp_path))
    av = r.get("alma_variavel", {})
    assert "dg25_cap_razao_raf" in av
    assert math.isfinite(av["dg25_cap_razao_raf"]) and av["dg25_cap_razao_raf"] > 0
    assert av["dg25_cap_regiao_raf"] in ("a", "b", "c")
