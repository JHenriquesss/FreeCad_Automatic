# ============================================================================
# test_fase69_tensao_ponto.py - RED tests da Fase 6.9.
# Verificacao por TENSOES da teoria da elasticidade (NBR 8800 secao 5.5.2.3,
# pag 57): checa sigma_Sd e tau_Sd no ponto critico (juncao mesa-alma), onde M e
# V do joelho picam juntos na alma esbelta. A NBR da checagens SEPARADAS:
#   a) sigma_Sd <= fy/gama_a1            (escoamento sob tensao normal)
#   b) tau_Sd   <= 0,60 fy/gama_a1       (escoamento sob cisalhamento)
#   c) sigma_Sd <= chi_n fy/gama_a1      (instabilidade sob tensao normal)
#   d) tau_Sd   <= 0,60 chi_v fy/gama_a1 (instabilidade sob cisalhamento)
# von Mises sqrt(sigma^2+3 tau^2) <= fy/gama_a1 entra como SUPLEMENTAR conservador
# (NAO e equacao explicita da NBR -> flag).
# ============================================================================
import os
import sys
import math
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

FY = 250e3   # kN/m2 (MR250)


def _sec_esbelta():
    import alma_variavel as av
    return av.props_I(0.90, 0.25, 0.003, 0.016)   # alma fina (joelho esbelto)


def _sig_tau_ref(sec, Nsd, Msd, Vsd):
    """Tensoes de referencia na JUNCAO mesa-alma, formula fechada."""
    A, Ix, tw, d, bf, tf = (sec["A"], sec["Ix"], sec["tw"], sec["d"],
                            sec["bf"], sec["tf"])
    yj = d / 2.0 - tf                             # juncao (face interna da mesa)
    sig = Nsd / A + Msd * yj / Ix
    Qf = bf * tf * (d - tf) / 2.0                 # momento estatico da mesa
    tau = Vsd * Qf / (Ix * tw)
    return sig, tau, Qf


# ==================== me-1: sigma/tau nos pontos ==========================
def test_sigma_juncao_formula():
    import tensao_ponto as tp
    s = _sec_esbelta()
    st = tp.sigma_tau(s, Nsd=200.0, Msd=300.0, Vsd=150.0)
    sig_ref, _, _ = _sig_tau_ref(s, 200.0, 300.0, 150.0)
    assert st["juncao"]["sigma"] == pytest.approx(sig_ref, rel=1e-9)


def test_tau_juncao_usa_Qf_real():
    # mne-5: tau na juncao usa Q estatico da mesa, NAO V/Aw uniforme.
    import tensao_ponto as tp
    s = _sec_esbelta()
    st = tp.sigma_tau(s, Nsd=0.0, Msd=0.0, Vsd=150.0)
    _, tau_ref, _ = _sig_tau_ref(s, 0.0, 0.0, 150.0)
    tau_uniforme = 150.0 / s["Av"]
    assert st["juncao"]["tau"] == pytest.approx(tau_ref, rel=1e-9)
    assert abs(st["juncao"]["tau"] - tau_uniforme) > 1e-6, \
        "tau da juncao nao pode ser a simplificacao V/Aw uniforme"


def test_fibra_extrema_tau_zero():
    import tensao_ponto as tp
    s = _sec_esbelta()
    st = tp.sigma_tau(s, Nsd=100.0, Msd=300.0, Vsd=150.0)
    # fibra extrema: sigma = N/A + M/Wx ; tau ~ 0
    sig_fibra = 100.0 / s["A"] + 300.0 / s["Wx"]
    assert st["fibra"]["sigma"] == pytest.approx(sig_fibra, rel=1e-9)
    assert abs(st["fibra"]["tau"]) < 1e-9


# ==================== me-2: verifica_5523 =================================
def test_5523_retorna_quatro_checks():
    import tensao_ponto as tp
    s = _sec_esbelta()
    r = tp.verifica_5523(s, FY, Nsd=200.0, Msd=300.0, Vsd=150.0)
    for k in ("u_sigma_a", "u_tau_b", "u_sigma_c", "u_tau_d", "u_vm", "gov", "OK"):
        assert k in r, f"faltou {k} no retorno de verifica_5523"


def test_von_mises_envelope():
    # von Mises entre max(sigma, sqrt(3) tau) e (sigma + sqrt(3) tau)
    import tensao_ponto as tp
    s = _sec_esbelta()
    st = tp.sigma_tau(s, Nsd=200.0, Msd=300.0, Vsd=150.0)
    sig = abs(st["juncao"]["sigma"]); tau = abs(st["juncao"]["tau"])
    vm = tp.von_mises(sig, tau)
    assert max(sig, math.sqrt(3) * tau) - 1e-9 <= vm <= sig + math.sqrt(3) * tau + 1e-9


def test_von_mises_flag_nao_normativo():
    import tensao_ponto as tp
    s = _sec_esbelta()
    r = tp.verifica_5523(s, FY, Nsd=200.0, Msd=300.0, Vsd=150.0)
    assert "elasticidade" in r.get("base_vm", "").lower(), \
        "von Mises deve ser marcado como suplementar (teoria da elasticidade), nao NBR explicito"


def test_check_d_reduz_com_chi_v():
    # d) usa 0,60 chi_v fy: chi_v<1 aperta o limite -> u_tau_d > u_tau_b
    import tensao_ponto as tp
    s = _sec_esbelta()
    r = tp.verifica_5523(s, FY, Nsd=0.0, Msd=0.0, Vsd=150.0,
                         chi_n=1.0, chi_v=0.6)
    assert r["u_tau_d"] > r["u_tau_b"] + 1e-9, \
        "chi_v<1 deve tornar a checagem d) mais severa que b)"


def test_sigma_isolado_reprova():
    # sigma > fy/gama isolado -> OK False, mesmo com tau nulo
    import tensao_ponto as tp
    s = _sec_esbelta()
    Mgrande = 2.0 * s["Wx"] * FY   # forca sigma bem acima de fy
    r = tp.verifica_5523(s, FY, Nsd=0.0, Msd=Mgrande, Vsd=0.0)
    assert r["u_sigma_a"] > 1.0 and not r["OK"]


def test_tau_governa_com_V_alto():
    # V alto, M~0 -> governa cisalhamento (b ou d), nao normal (a/c)
    import tensao_ponto as tp
    s = _sec_esbelta()
    r = tp.verifica_5523(s, FY, Nsd=0.0, Msd=1.0, Vsd=800.0, chi_v=0.7)
    assert r["gov"] in ("b_tau", "d_tau"), f"esperava cisalhamento governar, veio {r['gov']}"


def test_selftest_roda():
    import tensao_ponto as tp
    tp._selftest()


# ==================== me-3: integracao (joelho esbelto) ===================
def test_joelho_esbelto_integra():
    import tensao_ponto as tp
    import alma_esbelta as ae
    import alma_variavel as av
    s = av.props_I(0.95, 0.22, 0.004, 0.014)     # joelho tapered esbelto
    assert ae.e_esbelta(s, FY), "fixture deve ter alma esbelta"
    r = tp.verifica_5523(s, FY, Nsd=180.0, Msd=260.0, Vsd=140.0, chi_v=0.7)
    assert math.isfinite(r["u_vm"]) and r["u_vm"] > 0, \
        "verificacao no joelho esbelto deve retornar utilizacao finita, sem abortar"
