# ============================================================================
# test_resultados_planta.py - O CONTRATO TIPADO DAS SAIDAS DO ELETRICO SOBRE
# PLANTA (plano de 2026-10-08, Fase 1 e Fase 5). As saidas sao as que o motor
# devolve de verdade para a casa de teste (com e sem erro): o contrato tem de
# le-las todas e devolve-las iguais; chave que falta ou que sobra reprova.
# ============================================================================
"""Saidas de circuitos_planta lidas como estruturas imutaveis."""

import copy
import dataclasses
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import circuitos_planta as CP
import resultados_planta as RP
import test_circuitos_planta as TCP        # a mesma casa e os mesmos criterios

_SEM_PLANTA = {"geometria": None, "quadro_m": None}


def _cadeia(sem=None):
    """(divisao, dimensionamento, entrada) do motor; `sem` tira um criterio."""
    previsao, criterios, _ent = TCP._entrada()
    if sem:
        criterios = {k: v for k, v in criterios.items() if k != sem}
    div = CP.dividir(previsao, criterios)
    declarados = dict(criterios, comprimentos_m={c["id"]: 12.0 for c in div["circuitos"]})
    dim = CP.dimensionar_da_planta(div, _SEM_PLANTA, declarados)
    return div, dim, CP.demanda_e_entrada(previsao, div, criterios)


def test_saidas_do_motor_voltam_iguais_depois_de_lidas():
    div, dim, ent = _cadeia()
    assert div["ATENDE"] and dim["ATENDE"] and ent["ATENDE"]
    lida = RP.divisao(copy.deepcopy(div))
    assert lida.para_dict() == div and list(lida.para_dict()) == list(div)
    assert RP.dimensionamento(copy.deepcopy(dim)).para_dict() == dim
    assert RP.entrada(copy.deepcopy(ent)).para_dict() == ent
    # os campos tem o que o dicionario tinha
    assert [c.id for c in lida.circuitos] == [c["id"] for c in div["circuitos"]]
    assert lida.quadro.n_circuitos == len(lida.circuitos) and lida.atende is True
    eq = [c for c in lida.circuitos if c.equipamento is not None]
    assert [c.equipamento for c in eq] == ["chuveiro"]
    assert all("equipamento" not in c.para_dict() for c in lida.circuitos if c not in eq)


def test_saidas_com_erro_tambem_cabem_no_contrato():
    div, dim, ent = _cadeia(sem="tensao_v")
    assert not div["ATENDE"] and div["quadro"] is None and "criterios" not in div
    lida = RP.divisao(div)
    assert lida.quadro is None and lida.criterios is None and lida.para_dict() == div
    assert not dim["ATENDE"] and RP.dimensionamento(dim).para_dict() == dim
    assert not ent["ATENDE"] and RP.entrada(ent).para_dict() == ent
    _d, _m, sem_rede = _cadeia(sem="rede")
    assert not sem_rede["ATENDE"] and sem_rede["rooms"] is None
    assert RP.entrada(sem_rede).para_dict() == sem_rede


def test_as_estruturas_sao_imutaveis():
    div, dim, _ent = _cadeia()
    lida = RP.divisao(div)
    with pytest.raises(dataclasses.FrozenInstanceError):
        lida.circuitos[0].potencia_va = 0.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        RP.dimensionamento(dim).resumo[0].secao_mm2 = 1.5
    assert isinstance(lida.circuitos[0].point_ids, tuple)


@pytest.mark.parametrize("mexe, trecho", [
    (lambda d: d.pop("ATENDE"), "divisao: faltam ['ATENDE']"),
    (lambda d: d.update(atende=True), "fora do contrato ['atende']"),
    (lambda d: d["circuitos"][0].pop("corrente_a"), "divisao.circuitos[1]: faltam ['corrente_a']"),
    (lambda d: d["circuitos"][1].update(secao=2.5), "divisao.circuitos[2]"),
    (lambda d: d["pontos"][0].update(potencia_va=100.0), "divisao.pontos[1]"),
    (lambda d: d["quadro"].pop("escopo"), "divisao.quadro: faltam ['escopo']"),
    (lambda d: d.update(pontos=None), "divisao.pontos: esperada uma lista"),
])
def test_divisao_fora_do_contrato_reprova_dizendo_onde(mexe, trecho):
    div, _dim, _ent = _cadeia()
    mexe(div)
    with pytest.raises(RP.SaidaForaDoContrato) as ex:
        RP.divisao(div)
    assert trecho in str(ex.value)


def test_dimensionamento_e_entrada_fora_do_contrato_reprovam():
    _div, dim, ent = _cadeia()
    torto = copy.deepcopy(dim)
    torto["resumo"][0]["secao"] = torto["resumo"][0].pop("secao_mm2")
    with pytest.raises(RP.SaidaForaDoContrato, match=r"resumo\[1\].*secao_mm2.*secao"):
        RP.dimensionamento(torto)
    torto = copy.deepcopy(dim)
    del torto["comprimentos"]["IL1"]["origem"]
    with pytest.raises(RP.SaidaForaDoContrato, match="comprimentos.IL1"):
        RP.dimensionamento(torto)
    torto = copy.deepcopy(ent)
    del torto["service_entry"]
    with pytest.raises(RP.SaidaForaDoContrato, match="service_entry"):
        RP.entrada(torto)
    with pytest.raises(RP.SaidaForaDoContrato, match="esperado um objeto"):
        RP.entrada(None)


def test_o_desenho_recusa_divisao_fora_do_contrato_antes_de_abrir_a_planta(tmp_path):
    pytest.importorskip("ezdxf")
    import planta_eletrica_dxf as PE
    div, _dim, _ent = _cadeia()
    del div["circuitos"][0]["point_ids"]
    with pytest.raises(RP.SaidaForaDoContrato, match="point_ids"):
        PE.desenhar(str(tmp_path / "nao-existe.dxf"), str(tmp_path / "saida.dxf"), {}, div)
    assert not (tmp_path / "saida.dxf").exists()


def test_comprimento_estimado_pela_planta_traz_os_campos_a_mais_e_volta_igual():
    previsao, criterios, _ent = TCP._entrada()
    div = CP.dividir(previsao, criterios)
    nomes = sorted({a for c in div["circuitos"] for a in c["ambientes"]})
    leitura = {"geometria": {n: [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]] for n in nomes},
               "quadro_m": [0.0, 0.0]}
    dim = CP.dimensionar_da_planta(div, leitura, dict(
        criterios, tracado={"fator": 1.2, "acrescimo_vertical_m": 3.0}))
    lido = RP.dimensionamento(copy.deepcopy(dim))
    assert lido.para_dict() == dim
    um = lido.comprimentos[div["circuitos"][0]["id"]]
    assert um.origem != "declarado" and um.distancia_ortogonal_m == 7.0
    assert um.ambiente_mais_distante in nomes
    # no comprimento declarado os campos a mais nao existem e nao sao inventados
    dec = CP.dimensionar_da_planta(div, _SEM_PLANTA, dict(
        criterios, comprimentos_m={c["id"]: 12.0 for c in div["circuitos"]}))
    for c in RP.dimensionamento(dec).comprimentos.values():
        assert c.distancia_ortogonal_m is None and "distancia_ortogonal_m" not in c.para_dict()


def _leituras(tmp_path):
    """As leituras reais dos dois leitores: planta DXF e modelo IFC."""
    pytest.importorskip("ezdxf")
    pytest.importorskip("ifcopenshell")
    import ambientes_dxf as AD
    import ambientes_ifc as AI
    import test_ambientes_dxf as TAD
    import test_ambientes_ifc as TAI
    planta = TAD._planta(tmp_path, TAD._CASA_MM)
    modelo = TAI._casa(tmp_path)
    return {"dxf": (AD.ler_ambientes(planta), AD.previsao_de_cargas(planta)),
            "ifc": (AI.ler_ambientes(modelo, AD.normaliza_tipo),
                    AI.previsao_de_cargas(modelo, AD.normaliza_tipo))}


def test_leitura_dos_dois_leitores_cabe_no_mesmo_contrato(tmp_path):
    lidas = _leituras(tmp_path)
    for origem, (lido, previsao) in lidas.items():
        tipada = RP.leitura(lido)
        assert tipada.para_dict(list(lido)) == lido, origem
        assert [a.nome for a in tipada.ambientes] == [a["nome"] for a in lido["ambientes"]]
        assert sorted(tipada.geometria) == sorted(a.nome for a in tipada.ambientes)
        bloco = RP.leitura_da_previsao(previsao["leitura_dxf"])
        assert bloco.arquivo == previsao["leitura_dxf"]["arquivo"]
    # o que so uma origem traz fica None na outra, sem valor inventado
    dxf, ifc = RP.leitura(lidas["dxf"][0]), RP.leitura(lidas["ifc"][0])
    assert dxf.camada == "AMBIENTES" and dxf.pavimentos is None
    assert ifc.camada is None and isinstance(ifc.pavimentos, tuple)
    assert dxf.quadro_m is None and ifc.quadro_m == (12.0, 23.0)
    assert RP.leitura_da_previsao(lidas["ifc"][1]["leitura_dxf"]).origem == "ifc"
    assert RP.leitura_da_previsao(lidas["dxf"][1]["leitura_dxf"]).origem is None


@pytest.mark.parametrize("mexe, trecho", [
    (lambda d: d.pop("quadro_m"), "leitura: faltam ['quadro_m']"),
    (lambda d: d.update(quadro=[1.0, 2.0]), "fora do contrato ['quadro']"),
    (lambda d: d["ambientes"][0].pop("perimetro_m"), "leitura.ambientes[1]"),
    (lambda d: d["ambientes"][0].update(area=1.0), "leitura.ambientes[1]"),
    (lambda d: d.update(quadro_m=[1.0, 2.0, 3.0]), "leitura.quadro_m"),
    (lambda d: d["geometria"].pop(d["ambientes"][0]["nome"]), "nao sao os ambientes lidos"),
    (lambda d: d["geometria"].update(fantasma=[[0, 0], [1, 0], [1, 1]]),
     "nao sao os ambientes lidos"),
    (lambda d: d["geometria"].update({d["ambientes"][0]["nome"]: [[0, 0], [1, 0]]}),
     "esperados 3 ou mais pontos"),
])
def test_leitura_fora_do_contrato_reprova_dizendo_onde(tmp_path, mexe, trecho):
    lido = copy.deepcopy(_leituras(tmp_path)["dxf"][0])
    mexe(lido)
    with pytest.raises(RP.SaidaForaDoContrato) as ex:
        RP.leitura(lido)
    assert trecho in str(ex.value)


def test_leitura_com_erro_do_leitor_tambem_cabe_no_contrato(tmp_path):
    pytest.importorskip("ezdxf")
    import ambientes_dxf as AD
    import test_ambientes_dxf as TAD
    lido = AD.ler_ambientes(TAD._planta(tmp_path, [(0, 0, 4000, 3000, None)]))
    assert lido["erros"]
    tipada = RP.leitura(lido)
    assert tipada.para_dict(list(lido)) == lido and len(tipada.erros) == len(lido["erros"])
