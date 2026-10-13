# ============================================================================
# test_solda_perfil_chapa.py - SOLDA DE FILETE DO PERFIL I NA CHAPA (D223).
# Valores esperados sao contas a mao sobre um W 310 x 38,7 de chapas retas; o
# caminho ate' o pset do IFC e' conferido no emissor.
# ============================================================================
"""Solda do pilar na placa de base e da viga nas chapas de topo."""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ifc_emit
import solda_perfil_chapa as S

W310 = {"d": 0.310, "bf": 0.165, "tw": 0.0058, "tf": 0.0097}
FY, FU = 250e3, 400e3


def test_selftest_do_modulo():
    S._selftest()


@pytest.mark.parametrize("t, perna", [(4.75, 3.0), (6.3, 3.0), (6.35, 5.0), (12.5, 5.0),
                                      (12.6, 6.0), (19.0, 6.0), (19.1, 8.0), (50.0, 8.0)])
def test_perna_minima_da_tabela_11(t, perna):
    assert S.perna_minima(t) == perna


def test_secao_a_mao():
    # A = 2 x 165 x 9,7 + 290,6 x 5,8 = 4886,5 mm2
    # Ix = (165 x 310^3 - 159,2 x 290,6^3) / 12 = 84,04e6 mm4
    s = S.secao(W310)
    assert s["A"] * 1e6 == pytest.approx(4886.48, abs=0.01)
    assert s["Ix"] * 1e12 == pytest.approx((165 * 310 ** 3 - 159.2 * 290.6 ** 3) / 12, rel=1e-9)


def test_momento_puro_a_mao():
    # sigma na mesa = 60 x 0,155 / Ix ; cada cordao da mesa leva sigma x tf / 2
    s = S.secao(W310)
    sigma = 60.0 * 0.155 / s["Ix"]
    r = S.verifica(W310, 6.0, 0.0, 0.0, 60.0, FY, FU)
    mesa = r["pontos"][0]
    assert mesa["f_sd"] == pytest.approx(sigma * 0.0097 / 2)
    assert mesa["f_sd"] == pytest.approx(536.7, abs=0.5)
    # filete de 6 mm: 0,6 x 485e3 x 0,707 x 0,006 / 1,35 = 914,4 kN/m
    assert mesa["f_rd"] == pytest.approx(914.4, abs=0.1)
    assert mesa["u_base"] == pytest.approx(sigma / (FY / 1.10))


def test_os_cordoes_devolvem_o_momento_aplicado():
    # equilibrio: a soma das forcas dos cordoes vezes o braco e' o momento
    s = S.secao(W310)
    m = 60.0
    sigma = lambda y: m * y / s["Ix"]
    mesas = 2 * sigma(0.155 - 0.0097 / 2) * 0.165 * 0.0097 * (0.155 - 0.0097 / 2)
    alma = sigma(1.0) * 0.0058 * s["hw"] ** 3 / 12
    assert mesas + alma == pytest.approx(m, rel=2e-3)


def test_dimensiona_sobe_a_perna_ate_atender():
    d = S.dimensiona(W310, 16.0, 0.0, 50.0, 60.0, FY, FU)
    # alma de 5,8 mm: minima de 3 mm, que nao atende; a de 4 mm atende
    assert d["OK"] and d["perna_minima_mm"] == 3.0 and d["perna_mm"] == 4.0
    d = S.dimensiona(W310, 16.0, 0.0, 50.0, 100.0, FY, FU)
    assert d["OK"] and d["perna_mm"] > d["perna_minima_mm"]
    anterior = S.verifica(W310, d["tentativas"][-2]["perna_mm"], 0.0, 50.0, 100.0, FY, FU)
    assert not anterior["OK"]


def test_perfil_que_nao_resiste_reprova_pelo_metal_base():
    d = S.dimensiona(W310, 16.0, 0.0, 50.0, 400.0, FY, FU)
    assert d["OK"] is False and d["governa"] == "metal-base"
    assert "tensao no perfil" in S.relatorio_pt([d])


def test_metal_da_solda_esgotado_pede_penetracao():
    # mesa grossa e aco de alta resistencia: o perfil aguenta, o filete de 16 mm nao
    grosso = {"d": 0.310, "bf": 0.165, "tw": 0.030, "tf": 0.060}
    d = S.dimensiona(grosso, 50.0, 0.0, 0.0, 1150.0, 690e3, 760e3)
    assert d["OK"] is False and d["governa"] == "metal da solda"
    assert d["perna_mm"] == S.PERNAS_MM[-1]
    assert "penetracao" in S.relatorio_pt([d])


def test_esforco_com_sinal_trocado_da_a_mesma_solda():
    a = S.dimensiona(W310, 16.0, 80.0, 50.0, 90.0, FY, FU)
    b = S.dimensiona(W310, 16.0, -80.0, -50.0, -90.0, FY, FU)
    assert a["perna_mm"] == b["perna_mm"] and a["u"] == pytest.approx(b["u"])


def _membros():
    return [{"marca": "PB1", "perfil": "PlacaBase", "tipo": "Plate"},
            {"marca": "CJ1", "perfil": "ChapaTopoJoelho", "tipo": "Plate"},
            {"marca": "CC1", "perfil": "ChapaTopoCumeeira", "tipo": "Plate"}]


def _spec(**soldas):
    est = {"base_adotada": {"B": 0.6, "L": 0.8, "t": 0.05, "n": 4, "db": 0.032}}
    est.update(soldas)
    return {"estrutura": est}


def test_perna_da_solda_chega_ao_pset_de_cada_chapa():
    ms = _membros()
    ifc_emit._anotar_calculo(ms, _spec(solda_base={"perna_mm": 6.0, "u": 0.9, "ok": True},
                                       solda_joelho={"perna_mm": 10.0, "u": 0.9, "ok": True},
                                       solda_cumeeira={"perna_mm": 8.0, "u": 0.9, "ok": True}))
    pernas = {m["marca"]: m["propriedades"][ifc_emit.PSET_CALCULO]["SoldaFiletePerna_mm"]
              for m in ms}
    assert pernas == {"PB1": 6.0, "CJ1": 10.0, "CC1": 8.0}


def test_sem_solda_no_calculo_o_pset_nao_ganha_a_propriedade():
    ms = _membros()
    ifc_emit._anotar_calculo(ms, _spec())
    assert "SoldaFiletePerna_mm" not in ms[0]["propriedades"][ifc_emit.PSET_CALCULO]
    assert "propriedades" not in ms[1] and "propriedades" not in ms[2]
