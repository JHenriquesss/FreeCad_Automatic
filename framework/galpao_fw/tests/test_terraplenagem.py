"""Terraplenagem (corte/aterro por grade + greide de equilibrio) e drenagem
superficial (metodo racional + Manning). Camada PURA (CI)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import terraplenagem as tp


def test_selftest():
    assert tp._selftest() is True


def test_corte_puro_e_aterro_puro():
    grade = [[10.0, 10.0], [10.0, 10.0]]
    assert tp.volumes_corte_aterro(grade, 8.0, 100.0)["corte_m3"] == 800.0
    assert tp.volumes_corte_aterro(grade, 8.0, 100.0)["aterro_m3"] == 0.0
    assert tp.volumes_corte_aterro(grade, 12.0, 100.0)["aterro_m3"] == 800.0


def test_greide_equilibrio_media():
    rampa = [[6.0, 8.0], [10.0, 12.0]]           # media 9
    g = tp.greide_equilibrio(rampa, 100.0, empolamento=1.0)
    assert abs(g["cota_equilibrio"] - 9.0) < 0.1
    assert abs(g["corte_m3"] - g["aterro_m3"]) < 1.0


def test_greide_empolamento_baixa_a_plataforma():
    """Empolamento > 1 exige mais corte -> plataforma mais baixa (mais volume de corte)."""
    rampa = [[6.0, 8.0], [10.0, 12.0]]
    g1 = tp.greide_equilibrio(rampa, 100.0, empolamento=1.0)
    g2 = tp.greide_equilibrio(rampa, 100.0, empolamento=1.3)
    assert g2["cota_equilibrio"] < g1["cota_equilibrio"]


def test_movimento_terra_saldo():
    assert tp.movimento_terra(1000.0, 600.0)["saldo_m3"] == 400.0
    assert "bota-fora" in tp.movimento_terra(1000.0, 600.0)["acao"]
    assert "emprestimo" in tp.movimento_terra(500.0, 900.0)["acao"]


def test_movimento_terra_empolamento_reduz_corte_util():
    a = tp.movimento_terra(1000.0, 600.0, empolamento=1.0)
    b = tp.movimento_terra(1000.0, 600.0, empolamento=1.25)
    assert b["corte_util_m3"] < a["corte_util_m3"]


def test_racional():
    Q = tp.vazao_racional(0.7, 100.0, 1.0)
    assert abs(Q - 0.7 * 100 * 1 / 360.0) < 1e-9
    with pytest.raises(ValueError):
        tp.vazao_racional(1.5, 100, 1)           # C > 1
    with pytest.raises(ValueError):
        tp.vazao_racional(0.7, 0, 1)             # i = 0


def test_manning_lamina_cresce_com_vazao():
    c1 = tp.canaleta_manning(0.2, 0.5, 0.01)
    c2 = tp.canaleta_manning(0.5, 0.5, 0.01)
    assert c2["y_m"] > c1["y_m"] and c1["OK"]
    # a capacidade calculada bate a vazao pedida
    assert abs(c1["capacidade_m3s"] - 0.2) < 5e-3


def test_manning_canaleta_insuficiente():
    r = tp.canaleta_manning(50.0, 0.3, 0.005, altura_max_m=0.5)
    assert r["OK"] is False and "insuficiente" in r["nota"]


def test_dimensiona_drenagem():
    d = tp.dimensiona_drenagem({"C": 0.7, "i_mm_h": 120.0, "area_ha": 0.8,
                                "largura_canaleta_m": 0.4, "declividade": 0.01})
    assert d["vazao_m3s"] > 0 and d["canaleta"]["y_m"] > 0 and d["canaleta"]["OK"]
