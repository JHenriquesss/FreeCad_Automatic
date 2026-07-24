"""Controle da fissuracao ELS-W - NBR 6118:2014 17.3.3.2 (fissuracao_nbr6118.py).

Formula e limites conferidos no PDF NBR 6118:2014 (NotebookLM), nao de memoria:
- wk = MENOR entre (phi/(12,5 eta1))(sigma_s/Es)(3 sigma_s/fctm) e
  (phi/(12,5 eta1))(sigma_s/Es)(4/rho_ri + 45).
- eta1 = 2,25 barra nervurada (9.3.2.1).
- limites (Tab.13.4, concreto armado): CAA I 0,4 ; II/III 0,3 ; IV 0,2 mm.
- Acri: retangulo a no maximo 7,5 phi do eixo da barra (Fig.17.3).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fissuracao_nbr6118 as fis


def _caso(**kw):
    base = {"Ms": 80.0, "b": 0.20, "h": 0.50, "d": 0.45, "As": 8e-4,
            "fck": 30e3, "phi_mm": 16.0, "CAA": "II"}
    base.update(kw)
    return base


def test_wk_e_o_menor_das_duas():
    r = fis.verifica_fissuracao(_caso())
    assert r["wk_mm"] == min(r["wk1_mm"], r["wk2_mm"])
    assert 0.0 < r["wk_mm"] < 1.0


def test_limites_por_caa_tabela134():
    assert fis.WK_LIM_MM["I"] == 0.4
    assert fis.WK_LIM_MM["II"] == 0.3 and fis.WK_LIM_MM["III"] == 0.3
    assert fis.WK_LIM_MM["IV"] == 0.2
    assert fis.verifica_fissuracao(_caso(CAA="I"))["wk_lim_mm"] == 0.4
    assert fis.verifica_fissuracao(_caso(CAA="IV"))["wk_lim_mm"] == 0.2


def test_eta1_nervurada_225():
    assert fis.ETA1_NERVURADA == 2.25
    # eta1 maior (melhor aderencia) -> fissura menor
    r_nerv = fis.abertura_wk(16.0, 200e3, 30e3, 0.03, eta1=2.25)[0]
    r_lisa = fis.abertura_wk(16.0, 200e3, 30e3, 0.03, eta1=1.0)[0]
    assert r_nerv < r_lisa


def test_mais_armadura_reduz_fissura():
    r = fis.verifica_fissuracao(_caso(As=8e-4))
    r_mais = fis.verifica_fissuracao(_caso(As=16e-4))
    assert r_mais["wk_mm"] < r["wk_mm"]
    assert r_mais["sigma_s_MPa"] < r["sigma_s_MPa"]   # menos tensao no aco


def test_barra_mais_fina_reduz_fissura():
    # mesmo As, phi menor -> menor abertura (a fissura escala com phi)
    r16 = fis.verifica_fissuracao(_caso(phi_mm=16.0))
    r10 = fis.verifica_fissuracao(_caso(phi_mm=10.0))
    assert r10["wk_mm"] < r16["wk_mm"]


def test_sigma_s_estadio2_plausivel():
    sigma_s, x, I = fis.sigma_s_estadio2(80.0, 0.20, 0.45, 8e-4, 30e3)
    assert 0.0 < x < 0.45                     # linha neutra dentro da secao
    assert 100e3 < sigma_s < 400e3            # kN/m2 (100..400 MPa)


def test_modulo_secante_e_fctm_c30():
    # C30: Ecs ~ 27 GPa ; fctm ~ 2,9 MPa
    assert 25e6 < fis.modulo_secante(30e3) < 30e6
    assert 2.5e3 < fis.fctm(30e3) < 3.2e3


def test_selftest_roda():
    fis._selftest()
