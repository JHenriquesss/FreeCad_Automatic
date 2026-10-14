# ============================================================================
# test_migracao_6118_2023_d236.py - MIGRACAO DA NBR 6118 PARA A 2023 + EMENDA 1
# (decisao do usuario em 2026-10-14), FASE 1: os dois numeros do pilar de
# concreto que o D233 achou mudando. Cada valor vem da imagem da pagina:
# 2014 no PDF local F016 (p.108 e p.26), 2023 no MCP_Fontes (p.108 e p.26).
# A chave continua DESLIGADA por padrao (2014) ate' a fase 3.
# ============================================================================
"""D236: alpha_b do balanco (15.8.2 c) e eta_c (8.2.10.1) lendo a chave."""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import edicao_nbr6118_g123 as ed
import pilar_concreto as pc


def test_alpha_b_balanco_nas_duas_edicoes():
    # 2014: 0,80 + 0,20.Mc/Ma entre 0,85 e 1,0
    assert ed.alpha_b_balanco("2014", 50.0, 100.0) == pytest.approx(0.90)
    assert ed.alpha_b_balanco("2014", 0.0, 100.0) == pytest.approx(0.85)
    assert ed.alpha_b_balanco("2014", -100.0, 100.0) == pytest.approx(0.85)
    # 2023: 1,0 em qualquer caso
    assert ed.alpha_b_balanco("2023+Em1", 0.0, 100.0) == 1.0
    assert ed.alpha_b_balanco("2023+Em1", 50.0, 100.0) == 1.0


def test_eta_c_nas_duas_edicoes():
    assert ed.eta_c("2014", 70.0) == 1.0
    assert ed.eta_c("2014", 90.0) == 1.0
    assert ed.eta_c("2023+Em1", 40.0) == 1.0
    assert ed.eta_c("2023+Em1", 50.0) == pytest.approx((40.0 / 50.0) ** (1 / 3))
    assert ed.eta_c("2023+Em1", 90.0) == pytest.approx((40.0 / 90.0) ** (1 / 3))


def test_pico_do_parabola_retangulo_por_edicao():
    # 2014 (motor): 0,85 ate' C50 e 0,85.[1 - (fck-50)/200] acima (D85)
    assert pc.alpha_c_pilar(45.0, "2014") == pytest.approx(0.85)
    assert pc.alpha_c_pilar(70.0, "2014") == pytest.approx(0.85 * 0.90)
    # 2023: 0,85.eta_c
    assert pc.alpha_c_pilar(45.0, "2023+Em1") == pytest.approx(0.85 * (40 / 45) ** (1 / 3))
    assert pc.alpha_c_pilar(70.0, "2023+Em1") == pytest.approx(0.85 * (40 / 70) ** (1 / 3))
    assert pc.alpha_c_pilar(30.0, "2023+Em1") == pytest.approx(0.85)


def _pilar_balanco(fck, edicao=None, Mc=75.0, Nk=900.0, Ma=150.0):
    caso = {"b": 0.40, "h": 0.40, "Nk": Nk, "le_x": 6.0, "le_y": 6.0,
            "fck": fck, "fyk": 500e3,
            "M1d_x": {"tipo": "balanco", "Ma": Ma, "Mc": Mc}}
    if edicao:
        caso["edicao"] = edicao
    return pc.dimensiona_pilar(caso)


def test_pilar_declara_a_edicao_da_conta():
    assert _pilar_balanco(30e3, "2014")["edicao_6118"] == "2014"
    assert _pilar_balanco(30e3, "2023+Em1")["edicao_6118"] == "2023+Em1"
    # fase 3: sem chave = padrao 2023 + Em1
    assert _pilar_balanco(30e3)["edicao_6118"] == "2023+Em1"


def test_pilar_em_balanco_pela_2023_pede_mais_aco():
    """alpha_b 0,90 -> 1,0 e (acima de C40) eta_c < 1: a 2023 pede mais."""
    r14 = _pilar_balanco(30e3, "2014")
    r23 = _pilar_balanco(30e3, "2023+Em1")
    assert r14["dir"]["x"]["alpha_b"] == pytest.approx(0.90)
    assert r23["dir"]["x"]["alpha_b"] == 1.0
    assert r23["dir"]["x"]["Md_tot"] > r14["dir"]["x"]["Md_tot"]
    assert r23["As_cm2"] >= r14["As_cm2"]
    # C70 governado pela resistencia (medido: 56,4 -> 70,1 cm2, a 2023 reprova)
    c14 = _pilar_balanco(70e3, "2014", Nk=3000.0, Ma=300.0, Mc=150.0)
    c23 = _pilar_balanco(70e3, "2023+Em1", Nk=3000.0, Ma=300.0, Mc=150.0)
    assert c23["As_cm2"] > 1.15 * c14["As_cm2"]


def test_sem_chave_byte_igual_a_2023():
    """Fase 3 (D236): chave ausente = padrao 2023 + Em1."""
    assert ed.EDICAO_PADRAO == "2023+Em1"
    a = _pilar_balanco(70e3)
    b = _pilar_balanco(70e3, "2023+Em1")
    assert a["As_cm2"] == b["As_cm2"] and a["dir"] == b["dir"]


def test_edicao_do_projeto_vale_na_rodada():
    """A 2014 declarada no projeto chega aos pontos que nao recebem parametro
    (fct,m, bloco, tau_Rd, protensao) pelo contexto das entradas (D236)."""
    import fctm_nbr6118_g127 as fm
    assert fm.fctm_MPa(60.0) == pytest.approx(2.12 * __import__("math").log(1 + 0.1 * 68))
    with ed.edicao_do_projeto("2014"):
        assert fm.fctm_MPa(60.0) == pytest.approx(4.300, abs=0.005)
        assert not ed.eh_2023()
    assert ed.eh_2023()

    @ed.com_edicao_do_projeto("spec")
    def entrada(spec):
        return ed.eh_2023()
    assert entrada({"norma_6118_edicao": "2014"}) is False
    assert entrada({}) is True
