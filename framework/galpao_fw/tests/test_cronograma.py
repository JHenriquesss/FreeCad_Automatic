"""Cronograma fisico-financeiro 4D: rede CPM (caminho critico) + curva S. CI puro."""
import os
import sys

from xml.dom.minidom import parseString

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import cronograma as cr


def test_selftest():
    assert cr._selftest() is True


def test_cpm_serie():
    ats = [{"id": "A", "nome": "A", "dur": 5, "pred": []},
           {"id": "B", "nome": "B", "dur": 3, "pred": ["A"]},
           {"id": "C", "nome": "C", "dur": 2, "pred": ["B"]}]
    c = cr.cronograma(ats)
    assert c["duracao_total_dias"] == 10
    assert c["caminho_critico"] == ["A", "B", "C"]


def test_cpm_paralelo_folga():
    ats = [{"id": "A", "nome": "A", "dur": 5, "pred": []},
           {"id": "B", "nome": "B", "dur": 2, "pred": []},
           {"id": "C", "nome": "C", "dur": 4, "pred": ["A", "B"]}]
    c = cr.cronograma(ats)
    folgas = {a["id"]: a["folga"] for a in c["atividades"]}
    assert c["duracao_total_dias"] == 9
    assert folgas["A"] == 0 and folgas["B"] == 3 and folgas["C"] == 0


def test_ciclo_e_precedencia_invalida():
    with pytest.raises(ValueError):
        cr.cronograma([{"id": "X", "nome": "X", "dur": 1, "pred": ["Y"]},
                       {"id": "Y", "nome": "Y", "dur": 1, "pred": ["X"]}])
    with pytest.raises(ValueError):
        cr.cronograma([{"id": "A", "nome": "A", "dur": 1, "pred": ["Z"]}])


def test_ids_duplicados():
    with pytest.raises(ValueError):
        cr.cronograma([{"id": "A", "nome": "A", "dur": 1, "pred": []},
                       {"id": "A", "nome": "A2", "dur": 1, "pred": []}])


def test_curva_s_monotona_e_100():
    ats = cr.aplica_custos(
        [{"id": "A", "nome": "A", "dur": 5, "pred": []},
         {"id": "B", "nome": "B", "dur": 3, "pred": ["A"]}],
        {"A": 700.0, "B": 300.0})
    c = cr.cronograma(ats)
    cs = cr.curva_s(c)
    pcts = [p["avanco_fisico_pct"] for p in cs["periodos"]]
    assert pcts == sorted(pcts)
    assert abs(pcts[-1] - 100.0) < 1e-6
    assert abs(cs["periodos"][-1]["desembolso_acum"] - 1000.0) < 1e-6


def test_aplica_custos():
    ats = cr.aplica_custos([{"id": "A", "nome": "A", "dur": 1, "pred": []}],
                           {"A": 123.0})
    assert ats[0]["custo"] == 123.0


def test_wbs_default_galpao():
    c = cr.cronograma()
    assert c["duracao_total_dias"] > 0
    assert "estr" in c["caminho_critico"]        # a estrutura esta no caminho critico


def test_curva_s_svg_xml_valido():
    c = cr.cronograma(cr.aplica_custos(cr._WBS_GALPAO,
                                       {"estr": 400000, "fund": 90000}))
    svg = cr.curva_s_svg(c)
    assert svg.startswith("<svg") and "CURVA S" in svg
    parseString(svg.encode("utf-8"))
