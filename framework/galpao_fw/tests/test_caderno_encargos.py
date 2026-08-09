"""Caderno de encargos / especificacoes tecnicas por disciplina (material +
execucao + controle + normas). Camada PURA (CI)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import caderno_encargos as ce


def test_selftest():
    assert ce._selftest() is True


def test_todas_disciplinas_tem_clausulas_completas():
    cad = ce.gerar_caderno()
    assert cad["n_secoes"] == len(ce.disciplinas_disponiveis())
    for s in cad["secoes"]:
        assert s["clausulas"]
        for c in s["clausulas"]:
            assert c["material"] and c["execucao"] and c["controle"]
            assert c["normas"]                       # normas de referencia nao vazias


def test_ordem_canonica():
    ordem = [s["disciplina"] for s in ce.gerar_caderno()["secoes"]]
    assert ordem.index("terraplenagem") < ordem.index("fundacao")
    assert ordem.index("fundacao") < ordem.index("concreto")


def test_subconjunto():
    sub = ce.gerar_caderno(["eletrico", "hidraulica"])
    assert {s["disciplina"] for s in sub["secoes"]} == {"eletrico", "hidraulica"}


def test_disciplina_invalida():
    with pytest.raises(ValueError):
        ce.gerar_caderno(["inexistente"])


def test_markdown():
    md = ce.markdown(ce.gerar_caderno())
    assert md.startswith("# CADERNO DE ENCARGOS")
    assert "**Material:**" in md and "**Controle/aceitacao:**" in md
    assert "NBR 8800" in md and "NBR 5410" in md


def test_normas_referenciadas_ordenadas_unicas():
    normas = ce.gerar_caderno()["normas_referenciadas"]
    assert normas == sorted(set(normas))


def test_caderno_de_turnkey_acrescenta_fundacao_piso():
    R = {"executadas": ["concreto", "eletrico"]}
    discs = {s["disciplina"] for s in ce.caderno_de_turnkey(R)["secoes"]}
    assert {"concreto", "fundacao", "piso", "eletrico"} <= discs


def test_caderno_de_turnkey_vazio_cai_no_completo():
    ct = ce.caderno_de_turnkey({"executadas": []})
    assert ct["n_secoes"] == len(ce.disciplinas_disponiveis())
