"""Viga de concreto armado retangular (NBR 6118) - viga_concreto.py.

Reaproveita as rotinas aferidas de sapata/baldrame. A flexao e ancorada em 2
exemplos RESOLVIDOS externos (lidos das fontes, nao de memoria):
  - Araujo (Curso de Concreto Armado 2, Ex.1): 15x40, d=36, C20, Md=42 -> As=2,98 cm2
  - Carvalho & Figueiredo (Ex.1): bw=12, d=29, C20, Md=17,08 -> x=5,45 cm (dom.2), As=1,46
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import viga_concreto as vc


def test_flexao_afere_araujo():
    # viga 15x40 (d=36), C20, Md=42 kN.m -> As=2,98 cm2, x=9 cm
    r = vc.verifica_viga({"vao": 4.0, "b": 0.15, "h": 0.40, "fck": 20e3, "fyk": 500e3,
                          "cobrimento": 0.04, "phi_estribo_mm": 0.0, "phi_barra_mm": 0.0,
                          "M_d": 42.0})
    assert abs(r["d"] - 0.36) < 1e-9
    assert abs(r["As_flex_cm2"] - 2.98) < 0.03
    assert abs(r["x_d"] * r["d"] * 100 - 9.0) < 0.2   # x = 9 cm


def test_cortante_reprova_biela_secao_fina():
    # cortante muito alto numa alma fina -> reprova a biela (VRd2)
    r = vc.verifica_viga({"vao": 6.0, "b": 0.12, "h": 0.40, "fck": 25e3, "fyk": 500e3,
                          "V_d": 500.0})
    assert r["u_biela"] > 1.0 and not r["cort_ok"] and not r["OK"]


def test_els_visual_limite_L250():
    r = vc.verifica_viga({"vao": 5.0, "b": 0.20, "h": 0.50, "fck": 25e3, "fyk": 500e3,
                          "q": 6.0})
    assert abs(r["els"]["lim_mm"] - 5.0 / 250.0 * 1000) < 1e-6   # L/250 = 20 mm
    assert "visual" in r["els"]["criterio"]


def test_els_governa_e_dimensiona_sobe_altura():
    # viga esbelta: a semente (h=0,30) estoura a flecha L/250 -> dimensiona sobe h
    cfg = {"vao": 6.0, "b": 0.20, "h": 0.30, "fck": 25e3, "fyk": 500e3, "q": 14.0}
    r = vc.verifica_viga(cfg)
    rd = vc.dimensiona_viga(cfg)
    assert not r["els_ok"] and not r["OK"]         # a semente reprova no ELS
    assert rd["h"] > 0.30 and rd["OK"] and rd["els_ok"]   # subiu ate atender


def test_suporta_alvenaria_usa_criterio_L500():
    r = vc.verifica_viga({"vao": 5.0, "b": 0.20, "h": 0.60, "fck": 25e3, "fyk": 500e3,
                          "q": 5.0, "suporta_alvenaria": True, "q_alvenaria": 8.0})
    assert "alvenaria" in r["els"]["criterio"]
    # limite = min(L/500, 10 mm) ; L=5 -> L/500 = 10 mm
    assert abs(r["els"]["lim_mm"] - 10.0) < 1e-6


def test_continua_gera_armadura_negativa():
    r = vc.verifica_viga({"vao": 6.0, "b": 0.20, "h": 0.55, "fck": 25e3, "fyk": 500e3,
                          "q": 12.0, "continuidade": "continua"})
    assert r["continua"] and r["M_d_neg"] > 0 and r["As_sup_cm2"] > 0


def test_as_min_governa_carga_baixa():
    r = vc.verifica_viga({"vao": 3.0, "b": 0.20, "h": 0.50, "fck": 25e3, "fyk": 500e3,
                          "M_d": 1.0})
    assert r["As_inf_cm2"] >= r["As_min_cm2"] - 1e-9


def test_selftest_roda():
    vc._selftest()
