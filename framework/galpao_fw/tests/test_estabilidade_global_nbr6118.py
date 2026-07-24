"""Estabilidade global NBR 6118:2014 15.5 (estabilidade_global_nbr6118.py).

Formulas e limites conferidos no PDF NBR 6118:2014 (NotebookLM), nao de memoria:
- alpha = Htot*sqrt(Nk/(Ecs*Ic)) ; nos fixos se alpha <= alpha1 (15.5.2).
- alpha1 = 0,2+0,1n (n<=3) ; 0,6 (n>=4). Pilar em balanco n=1 -> 0,3.
- gamma_z = 1/(1 - dMtot,d/M1,tot,d) (15.5.3), valido so p/ >= 4 andares.
- majoracao 0,95 gamma_z p/ 1,1 < gamma_z <= 1,3 (15.7.2).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import estabilidade_global_nbr6118 as eg


def test_alpha1_por_andares():
    assert abs(eg.alpha_limite(1) - 0.3) < 1e-9       # 0,2+0,1
    assert abs(eg.alpha_limite(2) - 0.4) < 1e-9
    assert abs(eg.alpha_limite(3) - 0.5) < 1e-9
    assert eg.alpha_limite(4, "portico") == 0.5
    assert eg.alpha_limite(4, "pilar_parede") == 0.7
    assert eg.alpha_limite(4, "associado") == 0.6


def test_parametro_alpha_formula():
    # alpha = H*sqrt(Nk/(1,1 Ecs Ic)) com majoracao de 10% do Ecs
    Ecs = eg.fis.modulo_secante(30e3)
    Ic = eg.inercia_retangular(0.20, 0.40) * 2
    a = eg.parametro_alpha(6.0, 80.0, Ecs, Ic)
    import math
    assert abs(a - 6.0 * math.sqrt(80.0 / (1.1 * Ecs * Ic))) < 1e-9


def test_galpao_leve_nos_fixos():
    r = eg.verifica_estabilidade_galpao(6.0, 80.0, 0.20, 0.40, 2, 30e3)
    assert r["alpha1"] == 0.3 and r["nos"] == "fixos" and r["OK"]
    assert not r["gamma_z_aplicavel"]                 # 1 andar


def test_carga_alta_vira_nos_moveis():
    r = eg.verifica_estabilidade_galpao(9.0, 8000.0, 0.20, 0.40, 2, 30e3)
    assert r["nos"] == "moveis" and not r["OK"]


def test_gamma_z_e_majoracao():
    gz = eg.gamma_z(100.0, 1000.0)
    assert abs(gz - 1.0 / 0.9) < 1e-9
    assert eg.majoracao_horizontal(1.05)[0] == 1.0    # <=1,1 dispensa
    assert abs(eg.majoracao_horizontal(1.2)[0] - 0.95 * 1.2) < 1e-9
    assert eg.majoracao_horizontal(1.4)[0] is None    # >1,3 exige P-Delta


def test_selftest_roda():
    eg._selftest()
