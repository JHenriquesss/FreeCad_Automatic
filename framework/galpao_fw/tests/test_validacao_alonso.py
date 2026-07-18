# ============================================================================
# test_validacao_alonso.py - VALIDACAO DE SISTEMA contra exemplos RESOLVIDOS do
# livro "Exercicios de Fundacoes" (Urbano R. Alonso). Confirma o modulo de sapata
# contra numeros de referencia reais (nao so equilibrio interno). Tambem cobre a
# cadeia do fix de sinal: N>0 (compressao) -> sigma correto.
#   Caso 1 (18o Exercicio, cap.1): pilar 20x150, N=1200 kN, M=+/-200 kN.m,
#     sigma_adm=0,3 MPa -> livro: sapata 1,0 x 4,0 m, sig_max~377, sig_min~224.
#   Caso 2 (cap.9): pilar 45x45, P=1700 kN, sigma_adm=0,3 MPa -> livro: 2,50x2,50.
# ============================================================================
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import fundacao_sapata as fs


def test_alonso_caso1_tensao_no_solo_com_momento():
    # tensoes_solo(N, M, B, L). N>0 = compressao (convencao correta).
    sig_max, sig_min, regime, x = fs.tensoes_solo(1200.0, 200.0, 1.0, 4.0)
    assert sig_max == pytest.approx(377.0, rel=0.01)     # livro 377 kN/m2 (<1%)
    assert sig_min == pytest.approx(224.0, rel=0.01)     # livro 224 kN/m2
    assert "nucleo" in regime                            # e < L/6 -> contato total
    # media das tensoes = sigma_adm (equilibrio da resultante) - checagem do livro
    assert (sig_max + sig_min) / 2.0 == pytest.approx(300.0, rel=0.01)


def test_alonso_caso2_dimensionamento_por_bearing():
    caso = {"sigma_solo_adm": 300.0, "mu": 0.5, "fck": 15e3, "fyk": 500e3,
            "cobrimento": 0.05, "b_ped": 0.45, "d_ped": 0.45}
    casos = [("P", 1700.0, 0.0, 0.0)]                    # carga vertical, sem momento
    dims = fs.dimensiona_sapata_env(caso, casos)
    assert dims["aprovado"] is not None
    B, L, h, _, _ = dims["aprovado"]
    # B x L bate EXATO com o livro (2,50 x 2,50 m)
    assert B == pytest.approx(2.50) and L == pytest.approx(2.50)
    # altura: criterio de sapata RIGIDA (NBR 22.6.1) da ~0,70 (livro 0,60 por ACI
    # cortante); ambos validos, o nosso mais conservador. So garante que e rigida.
    assert h >= (L - 0.45) / 3.0 - 1e-9


def test_alonso_bloco_altura_beta_60():
    # Bloco (Alonso, 1o Exercicio cap.1): pilar 35x60, base 1,80x1,90 m ->
    # h pela regra beta>=60 (NBR 6122 7.8.2) = 1,25 m ; sigma_t = fck/25 = 0,6 MPa.
    import math
    B, L, ap_B, ap_L = 1.80, 1.90, 0.35, 0.60
    bal = max((B - ap_B) / 2.0, (L - ap_L) / 2.0)
    h = math.tan(math.radians(60.0)) * bal
    assert h == pytest.approx(1.25, abs=0.02)             # livro h = 1,25 m
    assert math.degrees(math.atan(h / bal)) == pytest.approx(60.0)
    # tensao admissivel a tracao do concreto = fck/25 <= 0,8 MPa (livro 0,6 MPa)
    assert min(15e3 / 25.0, 800.0) == pytest.approx(600.0)
    # o dimensionador aplica a MESMA regra (beta>=60) na altura adotada
    caso = {"sigma_solo_adm": 400.0, "mu": 0.5, "fck": 15e3, "b_ped": 0.35, "d_ped": 0.60}
    d = fs.dimensiona_bloco_env(caso, [("P", 1700.0, 0.0, 0.0)])
    assert d["aprovado"] is not None
    assert d["aprovado"][3] >= 60.0 - 1e-6                # beta >= 60
    assert d["sigma_t_adm"] == pytest.approx(600.0)


def test_alonso_sinal_gravidade_e_compressao():
    # regressao da cadeia do fix de sinal: carga vertical positiva (gravidade) DEVE
    # produzir compressao no solo (sigma_max > 0), nao "sem compressao".
    sig_max, _, regime, _ = fs.tensoes_solo(1000.0, 0.0, 2.0, 2.0)
    assert sig_max is not None and sig_max > 0
    assert "sem compressao" not in regime


def test_bellei_a6_pilar_compressao_nbr8800():
    # Bellei "Edificios de Multiplos Andares em Aco", Ex. A.6: pilar W360x122,
    # A572 Gr50, L=6m rotulado, lambda0y=1,26 -> chi=0,514, N_Rd=2503 kN.
    import check_nbr8800 as ck, math
    lam = 1.0 * 600 / (6.29 * math.pi) * math.sqrt(34.5 / 20000)   # lambda0y
    assert lam == pytest.approx(1.26, abs=0.01)
    chi = ck.chi_compressao(1.26)
    assert chi == pytest.approx(0.514, abs=0.005)                  # livro 0,514
    Nrd = chi * 1.0 * 155.3e-4 * 345e3 / 1.10                      # chi*Ag*fy/gamma
    assert Nrd == pytest.approx(2503.0, rel=0.005)                 # livro 2503 kN (<0,5%)


def test_vento_nbr6123_q_dinamica():
    # NBR 6123: galpao 20x10, V0=40, Cat II, Classe B, z=6,5 -> S2=0,943,
    # Vk=35,82 m/s, q=0,613*Vk^2=0,787 kN/m2.
    import vento_nbr6123 as v
    wr = v.compute(larg_b=10.0, alt_h=6.0, comp_a=20.0, theta=5.71, v0=40.0,
                   cat="II", classe="B", s1=1.0, s3=0.95, z=6.5)
    assert wr["q_kN_m2"] == pytest.approx(0.787, abs=0.005)        # livro 0,787
