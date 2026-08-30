"""Orcamento 5D: quantitativos -> planilha orcamentaria + curva ABC + BDI.
Precos de REFERENCIA (A CONFIRMAR). Camada PURA (CI)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import orcamento as orc


def test_selftest():
    assert orc._selftest() is True


def test_planilha_custo_e_bdi():
    itens = [{"codigo": "a", "descricao": "A", "unidade": "kg", "quantidade": 100,
              "preco_unitario": 10.0}]
    p = orc.planilha(itens, bdi_pct=25.0)
    assert p["custo_direto"] == 1000.0
    assert p["bdi_valor"] == 250.0 and p["preco_venda"] == 1250.0
    assert p["linhas"][0]["custo"] == 1000.0


def test_planilha_rejeita_negativo():
    with pytest.raises(ValueError):
        orc.planilha([{"codigo": "x", "quantidade": -1, "preco_unitario": 5}])


def test_curva_abc_ordena_e_acumula():
    itens = [{"codigo": "p", "descricao": "peq", "unidade": "un", "quantidade": 1,
              "preco_unitario": 100.0},
             {"codigo": "g", "descricao": "grande", "unidade": "un", "quantidade": 1,
              "preco_unitario": 900.0}]
    abc = orc.curva_abc(orc.planilha(itens))
    # ordenado por custo decrescente
    assert abc["itens"][0]["codigo"] == "g"
    # acumulado do ultimo = 100%
    assert abs(abc["itens"][-1]["pct_acumulado"] - 100.0) < 1e-6


def test_curva_abc_item_dominante_e_classe_a():
    """Um item que sozinho passa do corte ainda e' classe A (lidera a curva)."""
    itens = [{"codigo": "dom", "descricao": "dominante", "unidade": "un",
              "quantidade": 1, "preco_unitario": 950.0}]
    itens += [{"codigo": "t%d" % i, "descricao": "cauda", "unidade": "un",
               "quantidade": 1, "preco_unitario": 5.0} for i in range(9)]
    abc = orc.curva_abc(orc.planilha(itens))
    assert abc["itens"][0]["codigo"] == "dom" and abc["itens"][0]["classe"] == "A"
    assert abc["resumo"]["C"]["n"] >= 1


def test_compor_orcamento_referencia_e_sem_preco():
    res = orc.compor_orcamento({"aco_estrutural": 40000, "concreto_estrut": 150,
                                "inexistente": 3, "piso_industrial": 0})
    # codigo sem preco vai p/ sem_preco; quantidade 0 e' ignorada
    assert "inexistente" in res["sem_preco"]
    assert all(l["codigo"] != "piso_industrial" for l in res["planilha"]["linhas"])
    # aco (40 t x 18 = 720k) domina -> classe A
    assert res["abc"]["itens"][0]["codigo"] == "aco_estrutural"
    assert res["abc"]["itens"][0]["classe"] == "A"


def test_override_preco_usuario_vence():
    res = orc.compor_orcamento({"aco_estrutural": 1000},
                               precos={"aco_estrutural": ("Aco", "kg", 30.0)})
    assert res["planilha"]["linhas"][0]["preco_unitario"] == 30.0


def test_vol_membros_concreto():
    """Volume de concreto de barras RECT (bf.d.comp) + caixas (dims)."""
    membros = [
        {"tipo": "Column", "secao": {"bf": 0.3, "d": 0.4},
         "p1": [0, 0, 0], "p2": [0, 0, 6000]},        # 0,3x0,4x6 = 0,72 m3
        # caixa em MILIMETROS, a convencao unica do modelo neutro: 2 x 2 x 0,5 m
        {"tipo": "Footing", "dims": [2000.0, 2000.0, 500.0]},   # 2 m3
    ]
    v = orc._vol_membros_concreto(membros)
    assert abs(v - (0.72 + 2.0)) < 1e-6


def test_quantitativos_de_turnkey_extrai_piso():
    """Extrai a area de piso do resultado; guardado (nao quebra sem membros)."""
    R = {"disciplinas": {"concreto": {"rodou": True,
         "raw": {"piso": {"OK": True, "area_m2": 800.0}}}}}
    q = orc.quantitativos_de_turnkey(R)
    assert q.get("piso_industrial") == 800.0


def test_quantitativos_de_turnkey_vazio_sem_disciplinas():
    assert orc.quantitativos_de_turnkey({"disciplinas": {}}) == {}


def test_relatorio_texto():
    res = orc.compor_orcamento({"aco_estrutural": 10000, "piso_industrial": 400})
    txt = orc.relatorio_pt(res)
    assert "CURVA ABC" in txt and "PRECO DE VENDA" in txt and "A CONFIRMAR" in txt
