"""Piso industrial: placa de concreto sobre solo de Winkler, espessura por
tensao de Westergaard (interior/borda/canto), resistencia a tracao na flexao
NBR 6118 8.2.5, juntas e reforco. Camada PURA (roda toda em CI)."""
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import piso_industrial as pi


def test_selftest():
    assert pi._selftest() is True


def test_resistencia_flexao_maior_que_axial():
    """NBR 6118 8.2.5: tracao na flexao = tracao axial / 0,7 (~1,43x maior)."""
    fck = 30.0
    fctm = 0.3 * fck ** (2 / 3)
    axial_d = 0.7 * fctm / 1.4
    flexao_d = pi.resistencia_flexao_projeto(fck)
    assert flexao_d > axial_d
    assert abs(flexao_d - fctm / 1.4) < 1e-9            # fct,f,k,inf = fct,m


def test_rigidez_e_raio_relativo():
    """D = E t^3/12(1-nu^2) (Veloso&Lopes 4.76); l = (D/k)^0,25."""
    D = pi.rigidez_flexao_placa(30000.0, 200.0)
    assert abs(D - 30000.0 * 200.0 ** 3 / (12 * (1 - 0.15 ** 2))) < 1e-3
    l = pi.raio_rigidez_relativa(D, 40.0)
    assert abs(l - (D / (40.0 * 1e-3)) ** 0.25) < 1e-6
    assert 600.0 < l < 1500.0                           # ordem de grandeza (mm)


def test_westergaard_borda_e_canto_severos():
    """Para a mesma carga: borda e canto (livre) sao mais severos que o interior
    (a ordem relativa entre borda x canto depende da area de contato)."""
    E, h, k, a = 30000.0, 180.0, 40.0, 100.0
    D = pi.rigidez_flexao_placa(E, h)
    l = pi.raio_rigidez_relativa(D, k)
    b = pi.raio_contato_equivalente(a, h)
    si = pi.tensao_westergaard(30e3, h, l, b, a, "interior")
    se = pi.tensao_westergaard(30e3, h, l, b, a, "borda")
    sc = pi.tensao_westergaard(30e3, h, l, b, a, "canto")
    assert 0 < si < se and si < sc


def test_raio_contato_equivalente_dois_ramos():
    """Westergaard: p/ a<1,724h usa a formula corrigida (que espalha pela espessura
    e pode dar b>a p/ carga pequena); p/ a>=1,724h, b=a (sem correcao)."""
    h = 200.0
    a_peq = 50.0
    b = pi.raio_contato_equivalente(a_peq, h)
    assert abs(b - (math.sqrt(1.6 * a_peq ** 2 + h ** 2) - 0.675 * h)) < 1e-9
    assert pi.raio_contato_equivalente(400.0, h) == 400.0  # a >= 1,724h -> b=a


def test_espessura_cresce_com_a_carga():
    """A espessura adotada nunca diminui quando a carga aumenta (mesma posicao)."""
    def h_para(P):
        r = pi.verifica_piso({"L": 30, "W": 20, "fck_MPa": 30, "k_MN_m3": 50,
                              "cargas": [{"P_kN": P, "area_contato_cm2": 300,
                                          "posicoes": ["interior"]}]})
        return r["h_mm"] if r["OK"] else 10 ** 9
    assert h_para(20) <= h_para(35) <= h_para(60)


def test_subleito_mais_rigido_reduz_espessura():
    """k maior (subleito melhor) -> placa mais fina p/ a mesma carga."""
    caso = {"L": 30, "W": 20, "fck_MPa": 30,
            "cargas": [{"P_kN": 45, "area_contato_cm2": 200}]}
    fraco = pi.verifica_piso(dict(caso, k_MN_m3=20))
    forte = pi.verifica_piso(dict(caso, k_MN_m3=90))
    assert forte["h_mm"] <= fraco["h_mm"]


def test_sem_cargas_a_confirmar():
    """Sem cargas de operacao a espessura NAO e' inventada (A CONFIRMAR)."""
    r = pi.verifica_piso({"L": 10, "W": 10})
    assert r["OK"] is False and "A CONFIRMAR" in r["motivo"]


def test_geometria_invalida_levanta():
    with pytest.raises(ValueError):
        pi.verifica_piso({"L": 0, "W": 10, "cargas": [{"P_kN": 30, "area_contato_cm2": 300}]})


def test_juntas_regra_24h_teto_6m():
    assert pi.juntas_serragem(150) == round(min(6.0, 24 * 0.150), 2)  # 3,6 m
    assert pi.juntas_serragem(300) == 6.0                              # teto


def test_malha_de_juntas_cobre_o_piso():
    r = pi.verifica_piso({"L": 40, "W": 20, "fck_MPa": 30, "k_MN_m3": 60,
                          "cargas": [{"P_kN": 30, "area_contato_cm2": 300,
                                      "posicoes": ["interior"]}]})
    j = r["juntas"]
    assert j["paineis_x"] * j["painel_m"][0] >= 40 - 1e-6
    assert j["paineis_y"] * j["painel_m"][1] >= 20 - 1e-6


def test_udl_verifica_contra_solo():
    """A carga distribuida + peso da placa nao pode passar do sigma_solo_adm."""
    r = pi.verifica_piso({"L": 30, "W": 20, "fck_MPa": 30, "k_MN_m3": 60,
                          "cargas": [{"P_kN": 30, "area_contato_cm2": 300,
                                      "posicoes": ["interior"]}],
                          "udl_kN_m2": 300.0, "sigma_solo_adm_kN_m2": 150.0})
    assert r["udl"]["OK"] is False        # 300+peso > 150 -> reprova a UDL
    assert r["OK"] is False


def test_k_por_cbr_monotono():
    assert pi.k_por_cbr(2) < pi.k_por_cbr(10) < pi.k_por_cbr(20)


def test_desenho_planta_juntas_xml_valido():
    """A planta de juntas e' SVG XML valido (parse, nao substring) - lição do bug
    'SVG nao e' XML-parseado'."""
    import desenho_piso as dp
    assert dp._selftest() is True


def test_volume_e_area_coerentes():
    r = pi.verifica_piso({"L": 40, "W": 20, "fck_MPa": 30, "k_MN_m3": 60,
                          "cargas": [{"P_kN": 30, "area_contato_cm2": 300,
                                      "posicoes": ["interior"]}]})
    assert abs(r["area_m2"] - 800.0) < 1e-6
    assert abs(r["volume_concreto_m3"] - 800.0 * r["h_mm"] / 1000.0) < 1e-6
