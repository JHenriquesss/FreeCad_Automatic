"""Iluminacao externa/de vias do galpao (NBR 5101:2024 / Mamede Cap.2): classes,
niveis, espacamento de postes e metodo dos lumens para vias. Puro -> CI."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import iluminacao_externa_nbr5101 as ix


def test_selftest():
    ix._selftest()


def test_niveis_e_classes():
    assert ix.nivel_externo("estacionamento") == 50.0
    assert ix.nivel_externo("patio_manobra") == 150.0
    assert ix.CLASSE_M["M1"]["L_cd_m2"] == 2.00
    assert ix.CLASSE_C["C0"] == 50.0 and ix.CLASSE_P["P1"] == (20.0, 4.0, 6.0)


def test_nivel_desconhecido_nao_inventa():
    import pytest
    with pytest.raises(ValueError):
        ix.nivel_externo("inexistente")


def test_espacamento_e_disposicao():
    assert ix.espacamento_postes(10.0) == 40.0            # 4*H
    assert ix.espacamento_postes(10.0, 6.0) == 50.0       # limita a 5*H
    assert ix.espacamento_postes(10.0, 2.0) == 30.0       # limita a 3*H
    assert ix.disposicao_postes(10.0, 10.0) == "unilateral"
    assert ix.disposicao_postes(14.0, 10.0) == "bilateral_alternada"
    assert ix.disposicao_postes(16.0, 10.0) == "bilateral_oposta"


def test_metodo_dos_lumens_mamede():
    # Mamede 2.7.2: Em = 12600*0,36/(10*30) = 15,12 lux
    assert abs(ix.iluminancia_media(12600.0, 1, 0.36, 1.0, 10.0, 30.0) - 15.12) < 0.01
    assert abs(ix.espacamento_para_iluminancia(12600.0, 1, 0.36, 1.0, 15.12, 10.0) - 30.0) < 0.01


def test_projeto_via_interna():
    r = ix.dimensiona_iluminacao_externa({"comprimento_m": 100.0, "Lp": 8.0, "H": 10.0,
                                          "area_tipo": "estacionamento",
                                          "luminaria": {"fluxo_lm": 15000.0, "P_W": 100.0}})
    assert r["Em_lux"] == 50.0 and r["disposicao"] == "unilateral"
    assert r["S_m"] <= r["S_max_m"] and r["N_postes"] >= 2 and r["OK"]
    assert r["P_total_kW"] > 0
