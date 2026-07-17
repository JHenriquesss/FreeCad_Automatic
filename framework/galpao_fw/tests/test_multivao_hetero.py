# ============================================================================
# test_multivao_hetero.py - multi-vao HETEROGENEO (vaos desiguais). O 2D usava
# uma cumeeira UNICA (RIDGE) p/ todos os vaos, achatando os vaos mais largos e
# divergindo do 3D (que mantem a inclinacao). Agora a altura da cumeeira e por
# vao, com inclinacao constante. Ver wiki 07 item I.
# ============================================================================
import os
import sys
import math

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_portico as gp


def test_cumeeira_por_vao_inclinacao_constante():
    # spans 10 e 20, inclinacao 10% (do 1o vao): cumeeira do vao largo e mais alta
    gp.configurar(spans=[10, 20], eave=6, ridge=6.5, bay=6)   # slope=(6.5-6)/5=0.10
    assert gp._ridge_h(0) == pytest.approx(6.5)
    assert gp._ridge_h(1) == pytest.approx(7.0)               # 6 + 0.10*(20/2)
    # a inclinacao (angulo) e a MESMA nas duas aguas
    ang0 = math.atan((gp._ridge_h(0) - 6) / (10 / 2.0))
    ang1 = math.atan((gp._ridge_h(1) - 6) / (20 / 2.0))
    assert ang0 == pytest.approx(ang1)
    # os nos de cumeeira no frame ficam nas alturas certas
    fr, ix = gp._frame()
    zs = [fr.nodes[r][1] for r in ix["nRidges"]]
    assert zs == pytest.approx([6.5, 7.0])


def test_vaos_iguais_sem_regressao():
    # vaos IGUAIS: cumeeira por vao == RIDGE (identico ao comportamento anterior)
    gp.configurar(spans=[15, 15], eave=6, ridge=6.75, bay=6)
    assert gp._ridge_h(0) == gp._ridge_h(1) == pytest.approx(6.75)


def test_hetero_em_equilibrio():
    gp.configurar(spans=[10, 20], eave=6, ridge=6.5, bay=6)
    fr, ix = gp._frame(); gp.case_G(fr, ix); fr.solve(); R = fr.reactions()
    av = sum(fy for _, (fx, fy, m) in fr.nodal_loads.items())
    for e, (wx, wy) in fr.member_udl.items():
        xi, yi = fr.nodes[fr.elements[e]["i"]]; xj, yj = fr.nodes[fr.elements[e]["j"]]
        av += wy * math.hypot(xj - xi, yj - yi)
    rv = sum(R[3 * b + 1] for b in ix["nBases"])
    assert abs(av + rv) < 1e-6
