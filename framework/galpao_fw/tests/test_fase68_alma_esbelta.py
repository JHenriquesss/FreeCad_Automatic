# ============================================================================
# test_fase68_alma_esbelta.py - RED tests da Fase 6.8.
# Momento fletor resistente de vigas de ALMA ESBELTA (NBR 8800 Anexo H): quando
# h/tw > 5,70 sqrt(E/fy), o dimensionamento usa Wxc/Wxt + fator kpg, em vez de
# abortar com ValueError. Alma compacta/semicompacta segue Anexo G (inalterado).
# ============================================================================
import os
import sys
import math
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)


def _sec_esbelta():
    # perfil I soldado alto e de alma FINA -> h/tw esbelto. h=0.90 m, tw=3 mm.
    import alma_variavel as av
    return av.props_I(0.90, 0.25, 0.003, 0.016)


def _sec_compacta():
    import alma_variavel as av
    return av.props_I(0.40, 0.20, 0.010, 0.0125)   # h/tw = ~37, compacta


# ==================== me-1: modulo alma_esbelta ============================
def test_web_esbelta_detectada():
    import check_nbr8800 as ck
    s = _sec_esbelta()
    lam = (s["d"] - 2 * s["tf"]) / s["tw"]
    lamr = 5.70 * math.sqrt(ck.E / 250e3)
    assert lam > lamr, "fixture deve ter alma esbelta (h/tw > 5,70 sqrt(E/fy))"


def test_kc_dentro_limites():
    import alma_esbelta as ae
    kc = ae.kc(_sec_esbelta())
    assert 0.35 <= kc <= 0.76, "kc = 4/sqrt(h/tw) deve ficar em [0,35; 0,76]"


def test_kpg_nao_maior_que_1():
    import alma_esbelta as ae
    kpg = ae.kpg(_sec_esbelta(), 250e3)
    assert kpg <= 1.0 and kpg > 0.0, "kpg <= 1 (fator de reducao da alma esbelta)"


def test_mrd_reduzido_por_kpg():
    import alma_esbelta as ae
    s = _sec_esbelta()
    r = ae.mrd_alma_esbelta(s, 250e3, Lb=2.0, Cb=1.0)
    # M_Rd < Wxc*fy/GA1 (reducao por kpg + FLT/FLM)
    import check_nbr8800 as ck
    teto = s["Wx"] * 250e3 / ck.GA1
    assert 0 < r["M_Rd"] < teto, "M_Rd deve ser reduzido em relacao a Wxc*fy/GA1"
    assert r["gov"] in ("FLT", "FLM", "escoamento_mesa")


def test_guard_validade_aw_afc():
    import alma_esbelta as ae
    import alma_variavel as av
    # Aw/Afc > 10: alma enorme, mesa minuscula
    s = av.props_I(1.20, 0.08, 0.006, 0.006)
    r = ae.mrd_alma_esbelta(s, 250e3, Lb=2.0, Cb=1.0)
    assert r.get("fora_validade"), "Aw/Afc>10 deve sinalizar fora de validade (H.1.3)"


def test_selftest_roda():
    import alma_esbelta as ae
    ae._selftest()


def test_cb_nao_excede_plato():
    # parecer 38 ponto 2: no regime inelastico da FLT, Cb alto (2,5) NAO pode gerar
    # Mn > plato = kpg Wxc fy. A trava min(..., plato) deve segurar.
    import alma_esbelta as ae
    s = _sec_esbelta()
    # Lb=3,0 coloca a FLT no regime inelastico (lamp_t < lam_t < lamr_t)
    r = ae.mrd_alma_esbelta(s, 250e3, Lb=3.0, Cb=2.5)
    plato = r["kpg"] * s["Wx"] * 250e3
    assert r["M_flt"] <= plato + 1e-6, "Cb nao pode levar M_flt acima do plato kpg Wxc fy"
    assert r["Mn"] <= plato + 1e-6, "Mn (min) nunca supera o plato"
    # confirma que a trava REALMENTE engatou (Cb 2,5 empurraria acima sem o clamp)
    assert abs(r["M_flt"] - plato) < 1e-6, "com Cb=2,5 no inelastico a FLT deve travar no plato"


def test_flm_inelastico_presente():
    # parecer 38 ponto 1: o regime inelastico da FLM (lamp < lam <= lamr) existe e
    # NAO usa Cb. Secao com mesa semicompacta -> FLM inelastico entre plato e elastico.
    import alma_esbelta as ae
    import alma_variavel as av
    # mesa semicompacta: bf/2tf entre 0,38 e 0,95 sqrt(kc E / 0,7 fy)
    s = av.props_I(0.90, 0.30, 0.003, 0.010)   # bf/2tf = 15 -> inelastico p/ MR250
    r = ae.mrd_alma_esbelta(s, 250e3, Lb=1.0, Cb=1.0)
    plato = r["kpg"] * s["Wx"] * 250e3
    # se a mesa cai no ramo inelastico, M_flm fica ESTRITAMENTE entre elastico e plato
    assert 0 < r["M_flm"] <= plato + 1e-6


# ==================== me-2: momento_resistente despacha ====================
def test_momento_resistente_nao_aborta_esbelta():
    import check_nbr8800 as ck
    s = _sec_esbelta()
    # antes: ValueError; agora: despacha Anexo H
    Mn, gov, det = ck.momento_resistente(s, 250e3, Lb=2.0, Cb=1.0)
    assert Mn > 0, "momento_resistente deve calcular (Anexo H), nao abortar"
    assert det.get("anexo") == "H", "deve marcar que usou o Anexo H"


def test_compacta_usa_anexo_g_inalterado():
    # mne-2: alma compacta -> Anexo G, resultado identico ao atual
    import check_nbr8800 as ck
    s = _sec_compacta()
    Mn, gov, det = ck.momento_resistente(s, 250e3, Lb=2.0, Cb=1.0)
    assert det.get("anexo", "G") == "G", "compacta deve seguir Anexo G"
    # Mpl > 0 (Anexo G usa Zx)
    assert det["Mpl"] == pytest.approx(s["Zx"] * 250e3)


# ==================== me-3: integracao (rodar, sem abortar) ================
def test_misula_alma_fina_calcula():
    import flt_misula as fm
    import alma_variavel as av
    # misula alta 950->500 com alma 4 mm -> joelho esbelto
    secs = av.secao_tapered(0.95, 0.50, 0.22, 0.004, 0.014, nseg=8)
    segs = [{"M": 220.0 - 18 * i, "props": s["props"], "h_m": s["h_m"]}
            for i, s in enumerate(secs)]
    r = fm.flt_misula(segs, 250e3, Lb=3.0)      # nao pode abortar
    assert r["util"] >= 0 and r["M_Rd"] > 0
