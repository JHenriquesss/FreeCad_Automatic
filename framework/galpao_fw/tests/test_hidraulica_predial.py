"""Dimensionamento hidraulico predial (modulo de calculo): agua fria (NBR 5626:2020),
esgoto (NBR 8160) e aguas pluviais (NBR 10844). Valores aferidos contra as tabelas
LITERAIS das normas (lidas do PDF - regra AR300)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import hidraulica_predial as hp


def test_selftest():
    hp._selftest()


# ------------------------------ AGUA FRIA (NBR 5626:2020) --------------------
def test_vazao_agua_soma_projeto():
    # 2020 removeu o metodo dos pesos -> soma das vazoes de projeto (Tab.B.4)
    q = hp.vazao_agua({"bacia_caixa": 1, "lavatorio": 1, "chuveiro": 1})
    assert abs(q - (0.96 + 0.15 + 0.20)) < 1e-9


def test_diametro_agua_por_velocidade_3ms():
    a = hp.diametro_agua({"bacia_valvula": 1})     # 1,70 L/s
    # D = raiz(4*0,0017/(pi*3)) = 26,9 mm -> DN32; v_real <= 3 m/s (Sec.6.8.3)
    assert a["DN_mm"] == 32 and a["v_real_ms"] <= 3.0 and a["OK"]
    assert a["p_est_max_kPa"] == 400.0             # Sec.6.9.5


def test_agua_aparelho_invalido_e_vazio():
    with pytest.raises(ValueError):
        hp.vazao_agua({"foo": 1})
    with pytest.raises(ValueError):
        hp.diametro_agua({})


# ------------------------------ ESGOTO (NBR 8160) ---------------------------
def test_uhc_e_dn_descarga():
    uhc, dn = hp.uhc_de_aparelhos({"bacia": 1, "chuveiro": 1})
    assert uhc == 6 + 2 and dn == 100              # bacia: 6 UHC, ramal descarga DN100


def test_tabelas_esgoto():
    assert hp.diametro_ramal_esgoto(6) == 50       # Tab.5: DN50 cobre 6 UHC
    assert hp.diametro_ramal_esgoto(6, dn_min_descarga=100) == 100   # descarga forca DN100
    assert hp.diametro_tubo_queda(24, pavimentos=3) == 75           # Tab.6 <=3pav: 30>=24
    assert hp.diametro_tubo_queda(24, pavimentos=5) == 50           # Tab.6 >3pav: 24>=24
    assert hp.diametro_coletor(180, declividade_pct=1.0) == 100     # Tab.7 1%: 180>=180
    assert hp.diametro_coletor(181, declividade_pct=1.0) == 150     # >180 -> proximo DN
    assert hp.diametro_coletor(5, declividade_pct=1.0) == 100       # minimo coletor DN100


def test_esgoto_declividade_nao_tabelada_usa_inferior():
    # 1,5% nao esta na tabela -> usa 1% (mais conservador)
    assert hp.diametro_coletor(180, declividade_pct=1.5) == 100
    assert hp.diametro_coletor(181, declividade_pct=1.5) == 150


# ------------------------------ PLUVIAL (NBR 10844) -------------------------
def test_vazao_pluvial_formula():
    assert abs(hp.vazao_pluvial(120.0, 150.0) - 300.0) < 1e-9       # 150*120/60


def test_diametro_pluvial_tab4():
    p = hp.diametro_pluvial(100.0, 150.0, declividade_pct=1.0)      # Q=250 L/min
    assert p["DN_mm"] == 100 and p["Q_Lmin"] == 250.0              # Tab.4 1%: 287>=250
    p2 = hp.diametro_pluvial(800.0, 150.0, declividade_pct=1.0)     # Q=2000 L/min
    assert p2["DN_mm"] == 250                                       # 1820<2000<=3310


def test_area_contribuicao_inclinacao():
    # (b + h/2)*a  (Sec.5.2.1) + paredes
    assert abs(hp.area_contribuicao(10.0, 20.0, altura_incl_m=2.0, parede_m2=5.0)
               - ((10 + 1) * 20 + 5)) < 1e-9


def test_pluvial_i_default_flagado():
    p = hp.diametro_pluvial(100.0)         # i default -> dado de sitio flagado
    assert p["i_default"] is True
    p2 = hp.diametro_pluvial(100.0, i_mm_h=200.0)
    assert p2["i_default"] is False


def test_pluvial_entrada_degenerada():
    for bad in (lambda: hp.vazao_pluvial(0, 150), lambda: hp.vazao_pluvial(100, 0),
                lambda: hp.area_contribuicao(0, 20)):
        with pytest.raises(ValueError):
            bad()
