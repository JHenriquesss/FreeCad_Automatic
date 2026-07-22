"""Empocamento progressivo (NBR 8800 9.3) - gate de declividade."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import empocamento_nbr8800 as emp


def test_declividade_maior_igual_3pct_dispensa():
    for pct in (3.0, 5.0, 10.0, 17.6):
        r = emp.verifica_empocamento(pct)
        assert r["dispensado"] and r["OK"], (pct, r)


def test_declividade_menor_3pct_nao_atende():
    r = emp.verifica_empocamento(2.0)
    assert not r["dispensado"] and not r["OK"]
    assert "NAO ATENDE" in r["flag"] and "9.3" in r["flag"]


def test_limite_exato_3pct_inclusivo():
    assert emp.verifica_empocamento(3.0)["OK"]
    assert not emp.verifica_empocamento(2.999)["OK"]


def test_incl_pct_de_theta():
    # 5 graus -> 8,75% ; ~1,72 graus -> 3,0%
    assert abs(emp.incl_pct_de_theta(math.radians(5.0)) - 8.749) < 0.01
    assert abs(emp.incl_pct_de_theta(math.atan(0.03)) - 3.0) < 1e-6


def test_relatorio_contem_veredito():
    assert "NAO ATENDE" in emp.relatorio_pt(emp.verifica_empocamento(1.0))
    assert "DISPENSADO" in emp.relatorio_pt(emp.verifica_empocamento(5.0))
