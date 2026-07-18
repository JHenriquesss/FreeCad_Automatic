# ============================================================================
# test_frame2d_sinal.py - trava o SINAL da resposta a carga distribuida (UDL).
# Bug historico: a carga nodal equivalente da UDL era SUBTRAIDA no vetor de forcas
# (deveria somar), invertendo deslocamento e reacao de toda carga distribuida. So
# batia em MAGNITUDE (asserts em valor absoluto), entao a gravidade chegava na
# fundacao como se fosse UPLIFT -> footings superdimensionadas. Ver memoria
# bug-sinal-reacao-fundacao.
# ============================================================================
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import frame2d as f2

E, A, I = 200e6, 1e-2, 1e-4


def _ss():
    fr = f2.Frame2D()
    a = fr.add_node(0, 0); m = fr.add_node(2, 0); b = fr.add_node(4, 0)
    e0 = fr.add_element(a, m, E, A, I); e1 = fr.add_element(m, b, E, A, I)
    fr.add_support(a, True, True, False); fr.add_support(b, False, True, False)
    return fr, a, m, b, e0, e1


def test_udl_para_baixo_desloca_para_baixo():
    fr, a, m, b, e0, e1 = _ss()
    fr.add_member_udl(e0, wy=-5); fr.add_member_udl(e1, wy=-5)   # 20 kN p/ baixo
    d, mf = fr.solve()
    assert d[3 * m + 1] < 0, "UDL p/ baixo tem de deslocar p/ BAIXO (sinal, nao so magnitude)"


def test_udl_reacao_e_compressao_para_cima():
    fr, a, m, b, e0, e1 = _ss()
    fr.add_member_udl(e0, wy=-5); fr.add_member_udl(e1, wy=-5)
    fr.solve(); R = fr.reactions()
    # reacao verdadeira de carga p/ baixo = p/ CIMA (positiva) = +10 em cada apoio
    assert R[3 * a + 1] == pytest.approx(10.0)
    assert R[3 * b + 1] == pytest.approx(10.0)


def test_udl_e_nodal_equivalente_dao_mesma_reacao():
    # 20 kN como UDL vs como carga nodal no meio -> MESMA reacao total (consistencia
    # de sinal entre os dois caminhos; a inconsistencia era a raiz do bug).
    fr, a, m, b, e0, e1 = _ss()
    fr.add_member_udl(e0, wy=-5); fr.add_member_udl(e1, wy=-5)
    fr.solve(); Rudl = fr.reactions()
    fr2, a2, m2, b2, _, _ = _ss()
    fr2.add_nodal_load(m2, Fy=-20)
    fr2.solve(); Rnod = fr2.reactions()
    assert (Rudl[3 * a + 1] + Rudl[3 * b + 1]) == pytest.approx(20.0)
    assert (Rnod[3 * a2 + 1] + Rnod[3 * b2 + 1]) == pytest.approx(20.0)


def test_gravidade_no_portico_comprime_a_base():
    # no portico de referencia, a gravidade (case_G, UDL) tem de dar reacao de base
    # de COMPRESSAO (para cima) - antes vinha negativa (uplift) por causa do bug.
    import galpao_portico as gp
    gp.configurar(span=10, eave=6, ridge=7, bay=6); gp.W_WALL_COL = 0.0
    fr, ix = gp._frame(); gp.case_G(fr, ix); fr.solve(); R = fr.reactions()
    Rv = sum(R[3 * b + 1] for b in ix["nBases"])
    assert Rv > 0, "gravidade tem de comprimir a base (reacao vertical > 0)"
