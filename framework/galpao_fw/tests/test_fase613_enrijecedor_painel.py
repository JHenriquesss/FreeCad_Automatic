# ============================================================================
# test_fase613_enrijecedor_painel.py - RED tests da Fase 6.13.
# Enrijecedores transversais da alma do joelho (NBR 8800 §5.4.3.1): kv = 5+5/(a/h)^2
# eleva V_Rd; requisitos §5.4.3.1.3 (b/t, I_st>=a tw^3 j, j=[2,5/(a/h)^2]-2>=0,5);
# relaxa o cap h/tw<=260 do Anexo H quando a/h<=3. Base verbatim nbr8800 pgs 59-60.
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


def _sec(h, bf=0.25, tw=0.004, tf=0.016):
    import alma_variavel as av
    return av.props_I(h, bf, tw, tf)


# ==================== me-1: kv por a/h ==================================
def test_kv_sem_enrijecedor():
    import enrijecedor_painel as enp
    assert enp.kv(_sec(0.95), a=None) == 5.0


def test_kv_a_igual_h():
    import enrijecedor_painel as enp
    s = _sec(0.95)
    h = s["d"] - 2 * s["tf"]
    assert enp.kv(s, a=h) == pytest.approx(10.0)        # 5 + 5/1^2


def test_kv_a_h_maior_que_3_cai_para_5():
    import enrijecedor_painel as enp
    s = _sec(0.95)
    h = s["d"] - 2 * s["tf"]
    assert enp.kv(s, a=4.0 * h) == 5.0                   # a/h>3 -> sem enrijecedor


def test_kv_a_h_acima_do_limite_260():
    import enrijecedor_painel as enp
    s = _sec(0.95)
    h = s["d"] - 2 * s["tf"]
    lim = (260.0 / (h / s["tw"])) ** 2
    a = (lim + 0.5) * h                                  # a/h > (260/(h/tw))^2
    assert enp.kv(s, a=a) == 5.0


# ==================== me-2: V_Rd com kv ================================
def test_vrd_sobe_com_enrijecedor():
    import enrijecedor_painel as enp
    s = _sec(0.95)                                       # alma esbelta
    v0 = enp.vrd(s, FY, None)["Vrd"]
    v1 = enp.vrd(s, FY, a=s["d"] - 2 * s["tf"])["Vrd"]
    assert v1 > v0 > 0.0


def test_vrd_a_none_reproduz_kv5():
    import enrijecedor_painel as enp
    import check_nbr8800 as ck
    s = _sec(0.95)
    # replica o cortante de check_nbr8800 (kv=5, tres dominios) com Aw=d*tw
    h = s["d"] - 2 * s["tf"]; lam = h / s["tw"]
    lamp = 1.10 * math.sqrt(5.0 * ck.E / FY)
    lamr = 1.37 * math.sqrt(5.0 * ck.E / FY)
    Vpl = 0.6 * s["d"] * s["tw"] * FY
    if lam <= lamp:
        Vn = Vpl
    elif lam <= lamr:
        Vn = Vpl * (lamp / lam)
    else:
        Vn = Vpl * 1.24 * (lamp / lam) ** 2
    assert enp.vrd(s, FY, None)["Vrd"] == pytest.approx(Vn / ck.GA1, rel=1e-9)


# ==================== me-3: requisitos §5.4.3.1.3 ======================
def test_j_rigidez():
    import enrijecedor_painel as enp
    assert enp.j_rigidez(1.0) == pytest.approx(0.5)      # 2.5-2 = 0.5
    assert enp.j_rigidez(0.5) == pytest.approx(2.5 / 0.25 - 2.0)  # 8.0
    assert enp.j_rigidez(3.0) == 0.5                     # piso 0.5


def test_ist_req_formula():
    import enrijecedor_painel as enp
    s = _sec(0.95)
    a = s["d"] - 2 * s["tf"]
    j = enp.j_rigidez(a / (s["d"] - 2 * s["tf"]))
    assert enp.ist_req(s, a) == pytest.approx(a * s["tw"] ** 3 * j, rel=1e-9)


def test_requisitos_ok_e_reprova():
    import enrijecedor_painel as enp
    s = _sec(0.95)
    a = s["d"] - 2 * s["tf"]
    ok = enp.requisitos_enrijecedor(s, a, FY, b_st=0.075, t_st=0.008)
    assert ok["OK"] and ok["bt_ok"] and ok["Ist_ok"]
    bad = enp.requisitos_enrijecedor(s, a, FY, b_st=0.10, t_st=0.004)  # b/t alto
    assert not bad["bt_ok"] and not bad["OK"]


def test_bt_limite_verbatim():
    import enrijecedor_painel as enp
    import check_nbr8800 as ck
    s = _sec(0.95)
    r = enp.requisitos_enrijecedor(s, s["d"] - 2 * s["tf"], FY, 0.075, 0.008)
    assert r["bt_lim"] == pytest.approx(0.56 * math.sqrt(ck.E / FY), rel=1e-9)


# ==================== me-4: Anexo H relaxa cap 260 =====================
def test_anexo_h_cap_260_relaxado_com_enrijecedor():
    import alma_esbelta as ae
    import alma_variavel as av
    # alma muito esbelta: h/tw > 260 -> fora de validade SEM enrijecedor
    sec = av.props_I(1.10, 0.25, 0.004, 0.014)           # h/tw ~ 267 > 260
    assert (sec["d"] - 2 * sec["tf"]) / sec["tw"] > 260.0
    r_sem = ae.mrd_alma_esbelta(sec, FY, Lb=2.0, a=None)
    assert r_sem["fora_validade"] is True
    # com enrijecedor a/h<=3 -> cap 260 dispensado (Aw/Afc ainda <=10)
    a = 1.5 * (sec["d"] - 2 * sec["tf"])
    r_com = ae.mrd_alma_esbelta(sec, FY, Lb=2.0, a=a)
    assert r_com["fora_validade"] is False


def test_aw_afc_ainda_limita():
    import alma_esbelta as ae
    import alma_variavel as av
    # Aw/Afc > 10: enrijecedor NAO salva (limite independe de a)
    sec = av.props_I(1.20, 0.08, 0.006, 0.006)
    assert ae.mrd_alma_esbelta(sec, FY, 2.0, a=0.5)["fora_validade"] is True


# ==================== me-5: a_min_para_vsd + selftest ==================
def test_a_min_para_vsd():
    import enrijecedor_painel as enp
    s = _sec(0.95)
    v0 = enp.vrd(s, FY, None)["Vrd"]
    alvo = 0.5 * (v0 + enp.vrd(s, FY, 0.05)["Vrd"])
    a = enp.a_min_para_vsd(s, FY, alvo)
    assert a is not None and enp.vrd(s, FY, a)["Vrd"] >= alvo * 0.999


def test_selftest_roda():
    import enrijecedor_painel as enp
    enp._selftest()


# ==================== me-5b: integracao informativa ====================
def test_integra_reporta_enrijecedor_quando_esbelto(tmp_path):
    import rodar_projeto as RP
    from test_fase6b_alma_variavel import _spec
    # joelho fundo com alma fina -> esbelto; V de pico pode exceder V_Rd(kv=5)
    s = _spec(tipo="alma_variavel",
              tapered={"h_joelho": 1.05, "h_cumeeira": 0.45, "h_col_base": 0.35,
                       "bf": 0.22, "tw": 0.005, "tf": 0.012})
    r = RP.calcular(s, str(tmp_path))
    zp = r.get("zona_painel", {})
    # a chave so aparece quando o joelho pede enrijecedor; se aparecer, coerente
    if "enrij_a_sug_mm" in zp:
        assert zp["enrij_Vrd_kN"] >= zp["enrij_Vrd_sem_kN"]
        assert zp["enrij_kv"] >= 5.0
        assert zp["enrij_Ist_req_cm4"] > 0
