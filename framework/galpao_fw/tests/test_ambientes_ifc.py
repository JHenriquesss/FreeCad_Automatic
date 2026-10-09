# ============================================================================
# test_ambientes_ifc.py - AMBIENTES LIDOS DOS IfcSpace DE UM MODELO (plano de
# 2026-10-08, Fase 5, quinto passo). O modelo e' escrito aqui com o
# ifcopenshell (unidade em mm ou em m, ambientes fora da origem, um em L); o
# que se cobra e' que area, perimetro e poligono saiam da GEOMETRIA em metros
# nos dois eixos, que a previsao e a divisao sejam as mesmas da planta DXF
# equivalente, e que modelo mal formado reprove com o motivo nomeado.
# ============================================================================
"""IfcSpace de um IFC -> ambientes -> previsao de carga pelo motor."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ifcopenshell = pytest.importorskip("ifcopenshell")
np = pytest.importorskip("numpy")

import ifcopenshell.api as api

import ambientes_dxf as AD
import ambientes_ifc as AI
import arquitetura_residencial as AR
import circuitos_planta as CP

_RET = lambda w, h: [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]
# (Name, LongName, contorno local em m, origem em m)
_CASA = [("quarto", "Quarto", _RET(4.0, 3.0), (10.0, 20.0)),
         ("cozinha", "Cozinha", _RET(3.0, 3.0), (14.0, 20.0)),
         ("banho", "Banheiro", _RET(2.0, 1.5), (10.0, 23.0)),
         ("servico", "Área de Serviço", _RET(5.0, 1.5), (12.0, 23.0))]


class _Modelo:
    def __init__(self, unidade="MILLIMETERS"):
        self.f = 1000.0 if unidade == "MILLIMETERS" else 1.0
        m = self.m = api.run("project.create_file", version="IFC4")
        proj = api.run("root.create_entity", m, ifc_class="IfcProject", name="P")
        if unidade == "MILLIMETERS":
            api.run("unit.assign_unit", m, length={"is_metric": True, "raw": "MILLIMETERS"})
        else:
            api.run("unit.assign_unit", m, length={"is_metric": True, "raw": "METERS"})
        ctx = api.run("context.add_context", m, context_type="Model")
        self.body = api.run("context.add_context", m, context_type="Model",
                            context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
        site = api.run("root.create_entity", m, ifc_class="IfcSite", name="S")
        self.predio = api.run("root.create_entity", m, ifc_class="IfcBuilding", name="B")
        api.run("aggregate.assign_object", m, relating_object=proj, products=[site])
        api.run("aggregate.assign_object", m, relating_object=site, products=[self.predio])
        self.andares = {}

    def andar(self, nome):
        if nome not in self.andares:
            self.andares[nome] = api.run("root.create_entity", self.m,
                                         ifc_class="IfcBuildingStorey", name=nome)
            api.run("aggregate.assign_object", self.m, relating_object=self.predio,
                    products=[self.andares[nome]])
        return self.andares[nome]

    def espaco(self, nome, longo, contorno_m, origem_m, andar="Terreo", tipo=None,
               com_geometria=True, area_escrita_m2=None):
        m, f = self.m, self.f
        e = api.run("root.create_entity", m, ifc_class="IfcSpace", name=nome)
        e.LongName = longo
        e.ObjectType = tipo
        if com_geometria:
            pontos = [m.create_entity("IfcCartesianPoint", Coordinates=(x * f, y * f))
                      for x, y in contorno_m + [contorno_m[0]]]
            perfil = m.create_entity("IfcArbitraryClosedProfileDef", ProfileType="AREA",
                                     OuterCurve=m.create_entity("IfcPolyline", Points=pontos))
            rep = api.run("geometry.add_profile_representation", m, context=self.body,
                          profile=perfil, depth=2.7)
            api.run("geometry.assign_representation", m, product=e, representation=rep)
        mat = np.eye(4)
        mat[:3, 3] = [origem_m[0], origem_m[1], 0.0]
        api.run("geometry.edit_object_placement", m, product=e, matrix=mat)
        api.run("aggregate.assign_object", m, relating_object=self.andar(andar), products=[e])
        if area_escrita_m2 is not None:
            qto = api.run("pset.add_qto", m, product=e, name="Qto_SpaceBaseQuantities")
            api.run("pset.edit_qto", m, qto=qto,
                    properties={"NetFloorArea": area_escrita_m2 * f * f})
        return e

    def quadro(self, x_m, y_m):
        q = api.run("root.create_entity", self.m, ifc_class="IfcElectricDistributionBoard",
                    name="QD")
        mat = np.eye(4)
        mat[:3, 3] = [x_m, y_m, 1.5]
        api.run("geometry.edit_object_placement", self.m, product=q, matrix=mat)

    def grava(self, tmp_path, nome="casa.ifc"):
        caminho = str(tmp_path / nome)
        self.m.write(caminho)
        return caminho


def _casa(tmp_path, unidade="MILLIMETERS", quadro=(12.0, 23.0), nome="casa.ifc"):
    modelo = _Modelo(unidade)
    for linha in _CASA:
        modelo.espaco(*linha)
    if quadro is not None:
        modelo.quadro(*quadro)
    return modelo.grava(tmp_path, nome)


@pytest.mark.parametrize("unidade", ["MILLIMETERS", "METERS"])
def test_area_perimetro_e_poligono_saem_da_geometria_em_metros(tmp_path, unidade):
    lido = AI.ler_ambientes(_casa(tmp_path, unidade), AD.normaliza_tipo)
    assert lido["erros"] == [] and lido["pavimentos"] == ["Terreo"]
    achado = {a["nome"]: (a["tipo"], a["area_m2"], a["perimetro_m"]) for a in lido["ambientes"]}
    assert achado == {"quarto": ("quarto", 12.0, 14.0), "cozinha": ("cozinha", 9.0, 12.0),
                      "banho": ("banheiro", 3.0, 7.0), "servico": ("area_servico", 7.5, 13.0)}
    # o poligono vem na posicao do modelo, nos dois eixos
    assert sorted(map(tuple, lido["geometria"]["servico"])) == [
        (12.0, 23.0), (12.0, 24.5), (17.0, 23.0), (17.0, 24.5)]
    assert sorted(map(tuple, lido["geometria"]["quarto"])) == [
        (10.0, 20.0), (10.0, 23.0), (14.0, 20.0), (14.0, 23.0)]
    assert lido["quadro_m"] == [12.0, 23.0]


def test_ambiente_em_l_e_tipo_pelo_object_type(tmp_path):
    modelo = _Modelo()
    ele = [(0.0, 0.0), (5.0, 0.0), (5.0, 2.0), (2.0, 2.0), (2.0, 4.0), (0.0, 4.0)]
    modelo.espaco("101", "Estar e jantar", ele, (3.0, 7.0), tipo="Sala de Estar")
    lido = AI.ler_ambientes(modelo.grava(tmp_path), AD.normaliza_tipo)
    assert lido["erros"] == [] and lido["quadro_m"] is None
    amb = lido["ambientes"][0]
    assert (amb["nome"], amb["tipo"]) == ("101", "sala_estar")
    assert (amb["area_m2"], amb["perimetro_m"]) == (14.0, 18.0)
    assert sorted(map(tuple, lido["geometria"]["101"])) == sorted(
        (3.0 + x, 7.0 + y) for x, y in ele)


def test_previsao_e_divisao_iguais_as_dos_mesmos_ambientes_digitados(tmp_path):
    criterios = {"tensao_v": 127.0, "n_fases": 2,
                 "limite_va": {"iluminacao": 1000.0, "tomadas": 1500.0,
                               "tomadas_exclusivas": 2000.0},
                 "equipamentos": [],
                 "instalacao": {"isolacao": "PVC", "metodo_referencia": "B1",
                                "temperatura_ambiente_c": 30.0, "circuitos_agrupados": 3,
                                "queda_tensao_max_pct": 4.0, "exposicao_dps": "quadro",
                                "fator_potencia": {"iluminacao": 1.0, "tomadas": 0.8,
                                                   "tomadas_exclusivas": 0.8,
                                                   "equipamento": 1.0}},
                 "tracado": {"fator": 1.2, "acrescimo_vertical_m": 2.5}}
    prev = AI.previsao_de_cargas(_casa(tmp_path), AD.normaliza_tipo)
    a_mao = AR.rodar({"ambientes": [
        {"nome": "quarto", "tipo": "quarto", "area_m2": 12.0, "perimetro_m": 14.0},
        {"nome": "cozinha", "tipo": "cozinha", "area_m2": 9.0, "perimetro_m": 12.0},
        {"nome": "banho", "tipo": "banheiro", "area_m2": 3.0, "perimetro_m": 7.0},
        {"nome": "servico", "tipo": "area_servico", "area_m2": 7.5, "perimetro_m": 13.0}]})
    assert prev["ATENDE"] is True and prev["totais"] == a_mao["totais"]
    div = CP.dividir(prev, criterios)
    assert div["circuitos"] == CP.dividir(a_mao, criterios)["circuitos"]
    # o quadro do modelo e os poligonos alimentam o comprimento estimado: a casa
    # e' a do teste da planta DXF deslocada de (10; 20), e os metros sao os mesmos
    dim = CP.dimensionar_da_planta(div, prev["leitura_dxf"], criterios)
    assert dim["ATENDE"] is True
    assert {r["id"]: r["comprimento_m"] for r in dim["resumo"]} == {
        "IL1": pytest.approx(12.1), "TG1": pytest.approx(8.5),
        "TE1": pytest.approx(12.1), "TE2": pytest.approx(10.3)}


def test_quantidade_de_area_que_diverge_da_geometria_reprova(tmp_path):
    modelo = _Modelo()
    modelo.espaco("quarto", "Quarto", _RET(4.0, 3.0), (0.0, 0.0), area_escrita_m2=12.05)
    modelo.espaco("sala", "Sala", _RET(5.0, 4.0), (4.0, 0.0), area_escrita_m2=25.0)
    prev = AI.previsao_de_cargas(modelo.grava(tmp_path), AD.normaliza_tipo)
    erros = prev["leitura_dxf"]["erros"]
    assert [(e["code"], e["ambiente"]) for e in erros] == [("area_diverge_da_quantidade", "sala")]
    assert (erros[0]["area_geometria_m2"], erros[0]["area_escrita_m2"]) == (20.0, 25.0)
    # dentro da tolerancia o ambiente entra, com a area da GEOMETRIA
    assert [(a["nome"], a["area_m2"]) for a in prev["ambientes"]] == [("quarto", 12.0)]
    assert prev["ATENDE"] is False


def test_modelo_mal_formado_reprova_com_o_motivo(tmp_path):
    modelo = _Modelo()
    modelo.espaco("quarto", "Quarto", _RET(4.0, 3.0), (0.0, 0.0))
    modelo.espaco("vazio", "Sala", _RET(4.0, 3.0), (4.0, 0.0), com_geometria=False)
    modelo.espaco(None, None, _RET(2.0, 2.0), (8.0, 0.0))
    modelo.quadro(1.0, 1.0)
    modelo.quadro(2.0, 2.0)
    prev = AI.previsao_de_cargas(modelo.grava(tmp_path), AD.normaliza_tipo)
    assert sorted(e["code"] for e in prev["leitura_dxf"]["erros"]) == [
        "ambiente_sem_geometria", "ambiente_sem_nome", "varios_quadros"]
    assert [a["nome"] for a in prev["ambientes"]] == ["quarto"]
    assert prev["leitura_dxf"]["quadro_m"] is None and prev["ATENDE"] is False


def test_dois_pavimentos_exigem_a_escolha(tmp_path):
    modelo = _Modelo()
    modelo.espaco("quarto", "Quarto", _RET(4.0, 3.0), (0.0, 0.0), andar="Terreo")
    modelo.espaco("suite", "Suite", _RET(5.0, 3.0), (0.0, 0.0), andar="Superior")
    caminho = modelo.grava(tmp_path)
    sem = AI.ler_ambientes(caminho, AD.normaliza_tipo)
    assert sem["ambientes"] == [] and [e["code"] for e in sem["erros"]] == ["varios_pavimentos"]
    assert sem["erros"][0]["pavimentos"] == ["Superior", "Terreo"]
    cima = AI.ler_ambientes(caminho, AD.normaliza_tipo, pavimento="Superior")
    assert cima["erros"] == [] and [(a["nome"], a["area_m2"]) for a in cima["ambientes"]] \
        == [("suite", 15.0)]
    outro = AI.ler_ambientes(caminho, AD.normaliza_tipo, pavimento="Cobertura")
    assert outro["ambientes"] == [] and [e["code"] for e in outro["erros"]] \
        == ["pavimento_desconhecido"]


def test_pegada_com_vazio_tem_dois_contornos():
    # anel quadrado triangulado a mao: contorno de fora e contorno do furo
    fora = [(0, 0), (4, 0), (4, 4), (0, 4)]
    furo = [(1, 1), (3, 1), (3, 3), (1, 3)]
    verts = [(x, y, 0.0) for x, y in fora + furo] + [(x, y, 2.7) for x, y in fora + furo]
    faces = []
    for k in range(4):
        a, b, c, d = k, (k + 1) % 4, 4 + (k + 1) % 4, 4 + k
        faces += [(a, b, c), (a, c, d)]
    contornos = AI._pegada(verts, faces)
    assert sorted(len(c) for c in contornos) == [4, 4]
    assert sorted(sorted(c) for c in contornos) == sorted([sorted(map(lambda p: (float(p[0]), float(p[1])), fora)),
                                                          sorted(map(lambda p: (float(p[0]), float(p[1])), furo))])
