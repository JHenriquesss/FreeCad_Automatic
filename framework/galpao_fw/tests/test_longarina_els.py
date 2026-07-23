"""ELS (flecha) da longarina de parede - NBR 8800 Anexo C, Tabela C.1.

A verificacao antes so fazia ELU (interacao biaxial); a norma tambem limita o
DESLOCAMENTO da travessa de fechamento: L/120 perpendicular (vento) e L/180
paralelo (peso, entre tirantes). Achado na auditoria de fechamento.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import secundarios_nbr8800 as sec


def _cfg(vao, qv, **kw):
    base = {"vao": vao, "q_vento": qv, "trib": 1.5, "g_tapamento": 0.1,
            "peso_proprio": 0.08, "n_tirantes": 3, "continua": False,
            "mesa_interna_travada": True, "n_maos_francesas": 5}
    base.update(kw)
    return base


def test_longarina_tem_verificacao_de_flecha():
    r = sec.verifica_longarina(sec.UPE140, 250e3, _cfg(5.7, 0.8))
    # a resposta agora carrega os dois limites da Tab C.1
    assert "els_ok" in r and "flecha_vento_mm" in r and "flecha_peso_mm" in r
    # limites: perp = vao/120 ; paral = Ly/180 (Ly = vao/(n_mf+1) com mesa travada)
    assert abs(r["lim_vento_mm"] - 5.7 / 120.0 * 1000) < 1e-6


def test_els_governa_reprova_mesmo_com_elu_ok():
    # UPE140 em vao de 12 m sob vento leve: ELU passa (inter<1) mas a flecha de
    # vento estoura vao/120 -> a peca NAO atende. Sem o ELS, OK seria True (bug).
    r = sec.verifica_longarina(sec.UPE140, 250e3, _cfg(12.0, 0.3))
    assert r["inter"] <= 1.0                        # ELU passa
    assert r["els_ok"] is False                     # ELS reprova
    assert r["OK"] is False                         # OK reflete ELU E ELS
    assert r["flecha_vento_mm"] > r["lim_vento_mm"]


def test_amostra_girt_atende_els():
    # o girt da amostra (UPE140, vao 5,7) passa folgado no ELS
    r = sec.verifica_longarina(sec.UPE140, 250e3, _cfg(5.7, 0.8))
    assert r["els_ok"] is True and r["OK"] is True
    assert r["flecha_vento_mm"] < r["lim_vento_mm"]


def test_passa_reflete_els():
    # _passa (usado pela escada de perfis do dimensiona_secundarios) agora reprova
    # quando o ELS falha, mesmo com ELU ok -> a escada sobe o perfil pela flecha.
    r_ruim = sec.verifica_longarina(sec.UPE140, 250e3, _cfg(12.0, 0.3))
    assert sec._passa(r_ruim) is False
    r_bom = sec.verifica_longarina(sec.UPE140, 250e3, _cfg(5.7, 0.8))
    assert sec._passa(r_bom) is True
