"""Efeito de diafragma da cobertura (NBR 15421 8.3.2 + distribuicao)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import diafragma as D


def test_classifica_flexivel_criterio_2_1():
    # 8.3.2: flexivel se deflexao no plano > 2x drift medio
    assert D.classifica_diafragma(30.0, 10.0)["classe"] == "flexivel"   # 30 > 20
    assert D.classifica_diafragma(21.0, 10.0)["classe"] == "flexivel"   # 21 > 20
    assert D.classifica_diafragma(19.0, 10.0)["classe"] == "rigido"     # 19 <= 20


def test_laje_concreto_vao_prof_menor_3_rigido():
    assert D.classifica_diafragma(15.0, 10.0, concreto_vao_prof=2.0)["classe"] == "rigido"


def test_drift_nulo_indefinido():
    assert D.classifica_diafragma(0.0, 0.0)["classe"] == "indefinido"


def test_flexivel_distribui_por_tributaria():
    ff = D.distribui_flexivel(90.0, [5.0, 5.0, 5.0])
    assert all(abs(f - 30.0) < 1e-9 for f in ff)
    fb = D.distribui_flexivel(100.0, [2.5, 5.0, 2.5])
    assert abs(fb[0] - 25.0) < 1e-9 and abs(fb[1] - 50.0) < 1e-9


def test_rigido_distribui_por_rigidez():
    fk = D.distribui_rigido(100.0, [3.0, 1.0])
    assert abs(fk[0] - 75.0) < 1e-9 and abs(fk[1] - 25.0) < 1e-9


def test_rigido_iguais_equivale_uniforme():
    fr = D.distribui_rigido(90.0, [1.0, 1.0, 1.0])
    assert all(abs(f - 30.0) < 1e-9 for f in fr)


def test_rigido_torcao_carrega_a_ponta_e_equilibra():
    fe = D.distribui_rigido(90.0, [1.0, 1.0, 1.0], posicoes=[0.0, 5.0, 10.0], exc=2.0)
    assert fe[2] > fe[1] > fe[0]                       # torcao puxa a ponta afastada
    assert abs(sum(fe) - 90.0) < 1e-6                   # equilibrio


def test_relatorio_cita_nbr15421():
    txt = D.relatorio_pt(D.classifica_diafragma(30.0, 10.0))
    assert "15421" in txt and "FLEXIVEL" in txt.upper()
