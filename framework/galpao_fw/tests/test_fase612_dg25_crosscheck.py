# ============================================================================
# test_fase612_dg25_crosscheck.py - RED tests da Fase 6.12.
# Cross-check (VALIDACAO) da FLT de misula: momento de FLT elastico M_eLTB pelo
# AISC Design Guide 25 (5.4.3, Eq. 5.4-10=F4-5, secao do MEIO do trecho) vs o Mcr
# do NBR 8800 Anexo J (secao de MAIOR altura, J.4.2). INFORMATIVO - nao altera o
# dimensionamento (que segue a NBR). Base verbatim do DG25 pg 60-61 (imagens).
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


# ==================== me-1: nucleo DG25 ==================================
def test_rt_formula():
    import dg25_ltb as dg
    s = _sec(0.60)
    # rt = bfc / sqrt(12*(ho/d + (1/6)*aw*h^2/(ho*d)))  (5.4-11, F4-10)
    d, bf, tf, tw = s["d"], s["bf"], s["tf"], s["tw"]
    hc = d - 2 * tf; ho = d - tf
    aw = hc * tw / (bf * tf)
    rt_ref = bf / math.sqrt(12.0 * (ho / d + (1.0 / 6.0) * aw * hc ** 2 / (ho * d)))
    assert dg.rt(s) == pytest.approx(rt_ref, rel=1e-9)


def test_J_dg_compacta_positiva():
    import dg25_ltb as dg
    s = _sec(0.60)                                   # alma compacta -> J>0
    assert dg.J_dg(s, FY) > 0.0


def test_J_dg_slender_zero():
    import dg25_ltb as dg
    s = _sec(0.95, tw=0.004)                          # alma esbelta -> J=0 (5.4-12)
    hc = s["d"] - 2 * s["tf"]
    assert hc / s["tw"] > 5.70 * math.sqrt(dg.E / FY), "fixture deve ter alma esbelta"
    assert dg.J_dg(s, FY) == 0.0


def test_m_eltb_positivo_e_decresce_com_Lb():
    import dg25_ltb as dg
    s = _sec(0.60)
    m_curto = dg.m_eltb(s, FY, Lb=3.0, Cb=1.0)
    m_longo = dg.m_eltb(s, FY, Lb=6.0, Cb=1.0)
    assert m_curto > m_longo > 0.0, "M_eLTB cresce quando Lb diminui"


def test_selftest_roda():
    import dg25_ltb as dg
    dg._selftest()


# ==================== me-2: cross_check_flt ==============================
def _segs(h1, h2, nseg=8, bf=0.25, tw=0.008, tf=0.016):
    import alma_variavel as av
    xs = [i / (nseg - 1) for i in range(nseg)]
    return [{"props": av.props_I(h1 + (h2 - h1) * x, bf, tw, tf),
             "h_m": h1 + (h2 - h1) * x} for x in xs]


def test_prismatico_converge():
    # h1==h2: DG25 (meio) e NBR (funda) usam ~mesma secao -> razao ~1, CONVERGE.
    import dg25_ltb as dg
    r = dg.cross_check_flt(_segs(0.60, 0.60), FY, Lb=4.0)
    assert r["converge"] is True
    assert abs(r["razao"] - 1.0) <= r["tol"] + 1e-9


def test_razao_independe_de_cb():
    import dg25_ltb as dg
    r1 = dg.cross_check_flt(_segs(0.90, 0.45), FY, Lb=4.0, Cb=1.0)
    r2 = dg.cross_check_flt(_segs(0.90, 0.45), FY, Lb=4.0, Cb=2.3)
    assert r1["razao"] == pytest.approx(r2["razao"], rel=1e-9), \
        "Cb cancela na razao DG25/NBR"


def test_taper_forte_sinaliza_sem_excecao():
    # taper forte: secao meio << secao funda -> razao se afasta de 1; deve
    # SINALIZAR (converge pode ser False) sem lancar excecao. razao finita.
    import dg25_ltb as dg
    r = dg.cross_check_flt(_segs(1.20, 0.35), FY, Lb=4.0, tol=0.05)
    assert math.isfinite(r["razao"]) and r["razao"] > 0
    assert isinstance(r["converge"], bool)
    assert r["sec_meio"] != r["sec_funda"]           # secoes de referencia distintas


# ==================== me-3: integracao (informativa) =====================
def test_integra_reporta_razao_sem_mudar_util(tmp_path):
    import rodar_projeto as RP
    from test_fase6b_alma_variavel import _spec
    s = _spec(tipo="alma_variavel",
              tapered={"h_joelho": 0.90, "h_cumeeira": 0.45, "h_col_base": 0.35,
                       "bf": 0.22, "tw": 0.006, "tf": 0.014})
    r = RP.calcular(s, str(tmp_path))
    av = r.get("alma_variavel", {})
    assert "dg25_razao_raf" in av, "res deve reportar a razao do cross-check DG25 (rafter)"
    assert math.isfinite(av["dg25_razao_raf"]) and av["dg25_razao_raf"] > 0
    # cross-check e INFORMATIVO: a utilizacao da FLT continua presente e valida.
    assert av.get("util_flt_trecho") is not None
