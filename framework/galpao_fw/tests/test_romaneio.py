"""Romaneio preliminar com marcas de peca (a partir do calculo)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import romaneio as R

_SEC = {"col": {"nome": "HEA200", "A": 0.005383},
        "raf": {"nome": "HEA180", "A": 0.004525}}


def test_massa_por_metro():
    assert abs(R.massa_por_metro(0.005383) - 0.005383 * 7850) < 1e-6


def test_n_porticos_e_contagem_colunas():
    r = R.romaneio_primario(
        {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}, _SEC)
    assert r["n_porticos"] == 9                       # 40/5 + 1
    col = [i for i in r["itens"] if i["marca"] == "C1"][0]
    assert col["qtd"] == 2 * 9                         # (1 vao -> 2 col) x 9 porticos


def test_peso_coluna_confere():
    r = R.romaneio_primario(
        {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}, _SEC)
    col = [i for i in r["itens"] if i["marca"] == "C1"][0]
    assert abs(col["peso_unit_kg"] - 0.005383 * 7850 * 6.0) < 0.1


def test_rafter_meia_agua_comprimento_e_qtd():
    r = R.romaneio_primario(
        {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}, _SEC)
    v1 = [i for i in r["itens"] if i["marca"] == "V1"][0]
    assert abs(v1["comprimento_m"] - math.hypot(10.0, 1.0)) < 1e-2
    assert v1["qtd"] == 2 * 1 * 9                      # 2 meias-aguas x 1 vao x 9 porticos


def test_multivao_heterogeneo_gera_marcas_distintas():
    r = R.romaneio_primario(
        {"spans": [10.0, 30.0], "comprimento": 30.0, "eave": 6.0, "ridge": 7.5, "bay": 6.0},
        _SEC)
    marcas = {i["marca"] for i in r["itens"]}
    assert {"C1", "V1", "V2"} <= marcas               # 2 larguras -> V1 e V2
    assert [i for i in r["itens"] if i["marca"] == "C1"][0]["qtd"] == 3 * 6


def test_peso_total_soma_itens():
    r = R.romaneio_primario(
        {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}, _SEC)
    assert abs(r["peso_total_kg"] - sum(i["peso_total_kg"] for i in r["itens"])) < 0.5


def test_relatorio_tem_cabecalho_e_marcas():
    r = R.romaneio_primario(
        {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}, _SEC)
    txt = R.relatorio_pt(r)
    assert "MARCA" in txt and "C1" in txt and "V1" in txt and "PESO PRIMARIO TOTAL" in txt
