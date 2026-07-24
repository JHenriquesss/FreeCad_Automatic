"""Perdas de protensao (pre-tracao) - NBR 6118:2014 9.6.3 (perdas_protensao_nbr6118.py).

Formulas conferidas no PDF NBR 6118:2014 (NotebookLM), nao de memoria:
- encurtamento elastico (pre-tracao 9.6.3.3.1): Dsigma = alpha_p * sigma_cp, sem o
  fator (n-1)/2n (que e da pos-tracao 9.6.3.3.2.1);
- progressivas aproximadas (9.6.3.4.3, RB): Dsigma/sigma_p0 [%] =
  7,4 + (alpha_p/18,7) phi^1,07 (3 + sigma_c,p0g[MPa]).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import perdas_protensao_nbr6118 as pp


def _r(**kw):
    base = {"sigma_pi": 0.74 * 1900e3, "Ap": 6 * 1.01e-4, "ep": 0.25,
            "Mg": 25.0 * 0.20 * 0.60 * 15.0 ** 2 / 8.0, "b": 0.20, "h": 0.60,
            "fckj": 40e3, "phi": 2.0}
    base.update(kw)
    return pp.perdas_pretracao(**base)


def test_perda_total_faixa_realista():
    r = _r()
    assert 0.08 < r["perda_total_frac"] < 0.30       # pre-tracao tipica 10..25%
    assert r["perda_imediata_pct"] > 0
    assert r["prog_pct"] > 7.4                         # constante base RB


def test_formula_progressiva_rb_literal():
    r = _r(phi=2.0)
    ap = r["alpha_p"]; scp = r["sigma_cp_MPa"]
    esperado = 7.4 + (ap / 18.7) * (2.0 ** 1.07) * (3.0 + scp)
    assert abs(r["prog_pct"] - round(esperado, 1)) < 0.2


def test_mais_fluencia_mais_perda():
    assert _r(phi=2.5)["perda_total_frac"] > _r(phi=1.5)["perda_total_frac"]


def test_concreto_mais_novo_mais_perda():
    # fckj menor -> Eci menor -> alpha_p maior -> mais encurtamento e progressiva
    assert _r(fckj=25e3)["perda_total_frac"] > _r(fckj=40e3)["perda_total_frac"]
    assert _r(fckj=25e3)["alpha_p"] > _r(fckj=40e3)["alpha_p"]


def test_encurtamento_pretracao_sem_fator_pos():
    # alpha_p = Ep/Eci ; Dsigma_enc = alpha_p*sigma_cp (sem (n-1)/2n)
    r = _r()
    import math
    Eci = 5600.0 * math.sqrt(40.0) * 1000.0
    assert abs(r["alpha_p"] - round(200e6 / Eci, 2)) < 0.01


def test_selftest_roda():
    pp._selftest()
