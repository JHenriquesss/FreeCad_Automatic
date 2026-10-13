# ============================================================================
# test_combinacoes_elu_d225.py - COMBINACOES ULTIMAS DO PORTICO (D225).
# NBR 8800:2024, Tabelas 1 e 2 e 4.8.7.2.1. Ate' o D225 nao havia combinacao
# de gravidade sem vento (a succao aliviava sempre) e a sobrecarga secundaria
# entrava com psi0 sem gama_q.
# ============================================================================
"""Combinacoes ELU do portico: gravidade sem vento e sobrecarga secundaria."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import galpao_portico as gp
import vento_nbr6123 as vi


@pytest.fixture
def portico():
    gp.reset()
    vi.reset()
    gp.configurar(span=20.0, eave=8.0, ridge=9.5, bay=5.7, base_fixed=True,
                  A_col=0.0116, I_col=4.82e-4, A_raf=0.0116, I_raf=4.82e-4,
                  G_roof=0.27, rafter_self=0.9, Q_roof=0.25, comprimento=28.5)
    yield
    gp.reset()
    vi.reset()


def test_gravidade_sem_vento_existe():
    assert gp._combos_elu()["C0_grav"] == {"G": 1.25, "Q": 1.50}


def test_sobrecarga_secundaria_leva_gama_q_e_psi0_de_cobertura():
    c = gp._combos_elu()
    # 1,50 x 0,8 (Tabela 2: coberturas) com o vento principal
    assert c["C1_Gdesf_W1"] == {"G": 1.25, "Q": pytest.approx(1.20), "W1": 1.40}
    # 1,40 x 0,6 (Tabela 2: vento) com a sobrecarga principal
    assert c["C1_grav_W2"] == {"G": 1.25, "Q": 1.50, "W2": pytest.approx(0.84)}


def test_arrancamento_sem_sobrecarga_e_com_g_favoravel():
    c = gp._combos_elu()
    for nome in ("C1_uplift_W1", "C1_uplift_W2", "C1_Gfav_W1", "C1_Gfav_W2"):
        assert "Q" not in c[nome] and c[nome]["G"] == 1.00


def test_succao_do_vento_aliviava_a_gravidade(portico):
    """O defeito medido: com o vento de succao dentro, o momento de gravidade na
    viga sai menor que sem ele. A combinacao sem vento tem de governar a gravidade."""
    r = gp.analyse()["results"]
    sem_vento = r["C0_grav"]["viga_pior"]["M"]
    com_succao = r["C1_grav_W1"]["viga_pior"]["M"]
    assert sem_vento > com_succao
