# ============================================================================
# test_tesoura_lby_inf.py - o banzo INFERIOR da tesoura COMPRIME sob uplift e so
# e travado fora do plano onde ha mao-francesa (Bellei Fig 5.9). O default assume
# travamento a cada no (otimista); Lb_y_inf permite o espacamento real (conservador).
# Caca sessao 14: exposto p/ o eng. nao subestimar a flambagem do banzo inferior.
# ============================================================================
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import tesoura as T

_PERFIL = (0.20, 0.10, 0.006, 0.008)
_BASE = dict(L=20.0, h=2.5, n_paineis=8, tipo="warren", w_grav_kN_m=3.0,
             w_vento_kN_m=-4.0, fy=250e3, fu=400e3,
             perfil_banzo=_PERFIL, perfil_diagonal=_PERFIL)


def test_default_backcompat():
    # sem Lb_y_inf: comportamento antigo (cada no travado) - Lb_y_inf_m = None
    r = T.verifica_tesoura(dict(_BASE))
    assert r["Lb_y_inf_m"] is None
    assert r["u_max"] > 0


def test_lby_inf_conservador_nao_reduz_util():
    r0 = T.verifica_tesoura(dict(_BASE))
    r1 = T.verifica_tesoura(dict(_BASE, Lb_y_inf=8.0))
    # travar so a cada 8 m (em vez de cada no) PENALIZA o banzo inferior comprimido
    assert r1["u_max"] >= r0["u_max"] - 1e-9
    assert r1["Lb_y_inf_m"] == 8.0


def test_lby_inf_grande_reprova_quando_default_passava():
    # demonstra o risco real: com travamento esparso o banzo inferior pode reprovar
    r0 = T.verifica_tesoura(dict(_BASE))
    r1 = T.verifica_tesoura(dict(_BASE, Lb_y_inf=10.0))
    assert r0["u_max"] < 1.0 and r1["u_max"] > r0["u_max"]
