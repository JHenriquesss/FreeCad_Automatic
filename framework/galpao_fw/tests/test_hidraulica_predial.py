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


# ------------------------------ AGUA FRIA metodo dos pesos (NBR 5626:1998) ---
def test_pesos_tabela_A1():
    # Tab.A.1 (valores literais): bacia caixa 0,3 ; bacia valvula 32 ; chuveiro 0,4 ;
    # lavatorio 0,3 ; pia 0,7 ; tanque 0,7 ; mictorio s/ sifao 2,8
    assert hp.PESO_RELATIVO["bacia_caixa"] == 0.3
    assert hp.PESO_RELATIVO["bacia_valvula"] == 32.0
    assert hp.PESO_RELATIVO["mictorio"] == 2.8
    assert hp.soma_pesos({"bacia_caixa": 1, "lavatorio": 1, "chuveiro": 1}) == 1.0


def test_vazao_pesos_formula():
    # Q = 0,3*raiz(SP). SP=1,0 -> 0,30 L/s ; SP=32 (bacia valvula) -> 0,3*raiz(32)=1,697 L/s
    assert abs(hp.vazao_agua_pesos({"bacia_caixa": 1, "lavatorio": 1, "chuveiro": 1})
               - 0.30) < 1e-6
    assert abs(hp.vazao_agua_pesos({"bacia_valvula": 1}) - 1.697) < 1e-3


def test_pesos_menor_que_soma():
    # o metodo dos pesos (simultaneo) da vazao MENOR que a soma (conservador)
    banheiro = {"bacia_caixa": 1, "lavatorio": 1, "chuveiro": 1}
    soma = hp.diametro_agua(banheiro, metodo="soma")
    pesos = hp.diametro_agua(banheiro, metodo="pesos")
    assert pesos["metodo"] == "pesos" and pesos["soma_P"] == 1.0
    assert pesos["Q_Ls"] < soma["Q_Ls"] and pesos["DN_mm"] <= soma["DN_mm"]
    assert pesos["v_real_ms"] <= 3.0 and pesos["OK"]


def test_metodo_agua_invalido():
    with pytest.raises(ValueError):
        hp.diametro_agua({"bacia_caixa": 1}, metodo="xyz")
    with pytest.raises(ValueError):
        hp.soma_pesos({"desconhecido": 1})


# ------------------------------ VERIFICACAO DE PRESSAO (NBR 5626:1998 A.2) ---
def test_fair_whipple_hsiao():
    # J = 8,69e6 * Q^1,75 * d^-4,75 (lisos). Q=0,30 L/s, d=25 mm -> ~0,241 kPa/m
    assert abs(hp.perda_carga_unitaria(0.30, 25.0, "liso") - 0.241) < 0.01
    # aco (rugoso) perde mais que plastico (liso) no mesmo Q/d
    assert hp.perda_carga_unitaria(0.30, 25.0, "rugoso") > hp.perda_carga_unitaria(0.30, 25.0)
    assert hp.perda_carga_unitaria(0.0, 25.0) == 0.0            # sem vazao, sem perda
    with pytest.raises(ValueError):
        hp.perda_carga_unitaria(0.3, 0.0)


def test_comprimento_equivalente_tabela_A3():
    # DN25: cotovelo 90 = 1,5 ; te direta = 0,9 -> 2*1,5 + 0,9 = 3,9 m
    assert abs(hp.comprimento_equivalente(25.0, {"cotovelo_90": 2, "te_direta": 1}) - 3.9) < 1e-9
    # DN comercial 60 (fora da Tab.A.3) -> usa o tabelado mais proximo (65)
    assert hp.comprimento_equivalente(60.0, {"cotovelo_90": 1}) == hp.COMPRIMENTO_EQUIV_M[65][0]
    with pytest.raises(ValueError):
        hp.comprimento_equivalente(25.0, {"gambiarra": 1})


def test_verifica_pressao_balanco():
    # trecho: Q=0,30, d=25, L=20 m, 2 cotovelos + te (Leq 3,9) -> perda ~5,76 kPa
    # p_ent=100, ponto 3 m ABAIXO (ganho +30) -> disp=130 ; residual ~124 kPa >= 10 -> OK
    vp = hp.verifica_pressao(0.30, 25.0, 20.0, 100.0,
                             conexoes={"cotovelo_90": 2, "te_direta": 1},
                             dcota_m=3.0, tipo_ponto="geral")
    assert abs(vp["p_disponivel_kPa"] - 130.0) < 1e-6
    assert abs(vp["perda_kPa"] - 5.76) < 0.05 and vp["OK"] and vp["p_min_kPa"] == 10.0


def test_verifica_pressao_reprova_e_tipos_de_ponto():
    # pressao baixa -> reprova ; valvula de descarga exige 15 kPa, caixa aceita 5 kPa
    assert not hp.verifica_pressao(0.30, 25.0, 5.0, 12.0, tipo_ponto="valvula_descarga")["OK"]
    assert hp.P_MIN_PONTO_KPA["caixa_descarga"] == 5.0
    assert hp.P_MIN_PONTO_KPA["valvula_descarga"] == 15.0
    with pytest.raises(ValueError):
        hp.verifica_pressao(0.30, 25.0, 5.0, 100.0, tipo_ponto="inexistente")


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


def test_esgoto_declividade_minima_obrigatoria():
    # NBR 8160 Sec.4.2.3.2: DN>=100 exige >= 1% -> 0,5% e' violacao
    assert hp.declividade_minima_pct(75) == 2.0 and hp.declividade_minima_pct(100) == 1.0
    with pytest.raises(ValueError):
        hp.diametro_coletor(200, declividade_pct=0.5)


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


def test_pluvial_dn_minimo_vertical():
    # NBR 10844 Sec.5.6.3: condutor vertical DN interno minimo 70 mm -> DN75 comercial.
    # area pequena (Q baixo) que a Tab.4 dimensionaria como DN50 sobe p/ DN75.
    p = hp.diametro_pluvial(5.0, 150.0, declividade_pct=1.0)
    assert p["Q_Lmin"] == 12.5 and p["DN_mm"] == 75


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
