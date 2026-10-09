# ============================================================================
# test_circuitos_planta.py - PONTOS, DIVISAO EM CIRCUITOS E QUADRO DE CARGAS
# (plano de 2026-10-08, Fase 5, segundo passo). Cobra: os pontos somam a
# previsao do motor ambiente a ambiente; iluminacao, tomadas e tomadas dos
# locais de 9.5.3.2 nunca se misturam; o limite declarado corta o circuito no
# ponto certo; cada ponto cai em um unico circuito; equipamento tem circuito
# proprio com a exigencia de 9.5.3.1 dita dos dois lados de 10 A; criterio
# ausente nao vira circuito.
# ============================================================================
"""Ambientes -> pontos -> circuitos -> quadro de cargas."""

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import arquitetura_residencial as AR
import circuitos_planta as CP

_AMBIENTES = [
    {"nome": "quarto", "tipo": "quarto", "area_m2": 12.0, "perimetro_m": 14.0},   # 160 + 3x100
    {"nome": "cozinha", "tipo": "cozinha", "area_m2": 9.0, "perimetro_m": 12.0},  # 100 + 1900
    {"nome": "banho", "tipo": "banheiro", "area_m2": 3.0, "perimetro_m": 7.0},    # 100 + 600
    {"nome": "servico", "tipo": "area_servico", "area_m2": 7.5, "perimetro_m": 13.0}]  # 100 + 1900

_CRITERIOS = {"tensao_v": 127.0, "n_fases": 2,
              "limite_va": {"iluminacao": 1000.0, "tomadas": 1500.0,
                            "tomadas_exclusivas": 2000.0},
              "equipamentos": []}


def _previsao():
    return AR.rodar({"ambientes": copy.deepcopy(_AMBIENTES)})


def _criterios(**troca):
    c = copy.deepcopy(_CRITERIOS)
    c.update(troca)
    return c


def test_pontos_somam_a_previsao_do_motor_por_ambiente():
    prev = _previsao()
    pontos = [p for _c, p in CP.pontos_dos_ambientes(prev, 127.0)]
    for amb in prev["ambientes"]:
        do_amb = [p for p in pontos if p["room"] == amb["nome"]]
        luz = [p["power_va"] for p in do_amb if p["kind"] == "lighting"]
        tug = [p["power_va"] for p in do_amb if p["kind"] == "tug"]
        assert luz == [amb["carga_iluminacao_va"]]
        assert len(tug) == amb["n_tomadas_min"] and sum(tug) == amb["carga_tomadas_va"]
    cozinha = [p["power_va"] for p in pontos if p["room"] == "cozinha" and p["kind"] == "tug"]
    assert cozinha == [600.0, 600.0, 600.0, 100.0]
    assert [p["power_va"] for p in pontos if p["room"] == "quarto" and p["kind"] == "tug"] \
        == [100.0, 100.0, 100.0]
    assert {p["voltage_v"] for p in pontos} == {127.0}


def test_classes_nao_se_misturam_e_cada_ponto_tem_um_circuito():
    res = CP.dividir(_previsao(), _criterios())
    assert res["ATENDE"] is True and res["erros"] == []
    por_id = {p["id"]: p for p in res["pontos"]}
    usados = [pid for c in res["circuitos"] for pid in c["point_ids"]]
    assert sorted(usados) == sorted(por_id)                       # todos, uma vez so
    for c in res["circuitos"]:
        tipos = {por_id[pid]["kind"] for pid in c["point_ids"]}
        assert len(tipos) == 1
        assert (c["use"] == "iluminacao") == (tipos == {"lighting"})
    exclusivos = [c for c in res["circuitos"] if c["classe"] == "tomadas_exclusivas"]
    gerais = [c for c in res["circuitos"] if c["classe"] == "tomadas"]
    assert {a for c in exclusivos for a in c["ambientes"]} == {"cozinha", "servico"}
    assert {a for c in gerais for a in c["ambientes"]} == {"quarto", "banho"}


def test_limite_declarado_corta_o_circuito_no_ponto_certo():
    res = CP.dividir(_previsao(), _criterios())
    achado = {c["id"]: (c["potencia_va"], c["point_ids"]) for c in res["circuitos"]}
    assert achado == {
        "IL1": (460.0, ["L01", "L02", "L03", "L04"]),
        "TG1": (900.0, ["T01.1", "T01.2", "T01.3", "T03.1"]),
        # cozinha 1900 cabe em 2000; o primeiro ponto do servico (600) nao cabe mais
        "TE1": (1900.0, ["T02.1", "T02.2", "T02.3", "T02.4"]),
        "TE2": (1900.0, ["T04.1", "T04.2", "T04.3", "T04.4"])}
    # limite menor: a cozinha sozinha ja se parte, e o resto do circuito segue enchendo
    apertado = CP.dividir(_previsao(), _criterios(limite_va={
        "iluminacao": 300.0, "tomadas": 1500.0, "tomadas_exclusivas": 1300.0}))
    te = [(c["id"], c["potencia_va"], c["point_ids"]) for c in apertado["circuitos"]
          if c["classe"] == "tomadas_exclusivas"]
    assert te == [("TE1", 1200.0, ["T02.1", "T02.2"]),
                  ("TE2", 1300.0, ["T02.3", "T02.4", "T04.1"]),
                  ("TE3", 1300.0, ["T04.2", "T04.3", "T04.4"])]
    il = [(c["potencia_va"], c["point_ids"]) for c in apertado["circuitos"]
          if c["classe"] == "iluminacao"]
    assert il == [(260.0, ["L01", "L02"]), (200.0, ["L03", "L04"])]
    for c in apertado["circuitos"]:
        assert c["potencia_va"] <= apertado["criterios"]["limite_va"][c["classe"]]


def test_quadro_fecha_com_a_previsao_e_com_as_fases():
    prev = _previsao()
    res = CP.dividir(prev, _criterios())
    q = res["quadro"]
    esperado = prev["totais"]["carga_iluminacao_va"] + prev["totais"]["carga_tomadas_va"]
    assert q["carga_instalada_va"] == esperado == 5160.0
    assert q["n_pontos"] == prev["totais"]["n_pontos_luz_min"] + prev["totais"]["n_tomadas_min"]
    # 1900, 1900, 900, 460 em duas fases, maior primeiro na menos carregada
    # (empate vai para a primeira letra): A = 1900 + 900, B = 1900 + 460
    assert q["carga_por_fase_va"] == {"A": 2800.0, "B": 2360.0}
    assert sum(q["carga_por_fase_va"].values()) == q["carga_instalada_va"]
    assert q["desequilibrio_pct"] == pytest.approx(100.0 * 440.0 / 2800.0)
    fases = {c["id"]: c["fases"] for c in res["circuitos"]}
    assert fases == {"TE1": ["A"], "TE2": ["B"], "TG1": ["A"], "IL1": ["B"]}
    for c in res["circuitos"]:
        assert c["corrente_a"] == pytest.approx(c["potencia_va"] / 127.0)
    uma = CP.dividir(prev, _criterios(n_fases=1))["quadro"]
    assert uma["carga_por_fase_va"] == {"A": 5160.0} and uma["desequilibrio_pct"] == 0.0


def test_equipamento_tem_circuito_proprio_e_a_exigencia_dos_dois_lados_de_10_a():
    eqs = [{"nome": "chuveiro", "ambiente": "banho", "potencia_va": 5500.0,
            "tensao_v": 220.0, "n_fases": 2},                              # 25 A
           {"nome": "exaustor", "ambiente": "cozinha", "potencia_va": 1270.0,
            "tensao_v": 127.0, "n_fases": 1},                              # 10 A exatos
           {"nome": "forno", "ambiente": "cozinha", "potencia_va": 1271.0,
            "tensao_v": 127.0, "n_fases": 1}]                              # logo acima
    res = CP.dividir(_previsao(), _criterios(equipamentos=eqs))
    assert res["ATENDE"] is True
    eq = {c["equipamento"]: c for c in res["circuitos"] if c["classe"] == "equipamento"}
    assert [eq[n]["point_ids"] for n in ("chuveiro", "exaustor", "forno")] \
        == [["E01"], ["E02"], ["E03"]]
    assert eq["chuveiro"]["corrente_a"] == pytest.approx(25.0)
    assert eq["chuveiro"]["independente_exigido_9_5_3_1"] is True
    assert eq["chuveiro"]["fases"] == ["A", "B"]
    assert eq["exaustor"]["corrente_a"] == pytest.approx(10.0)
    assert eq["exaustor"]["independente_exigido_9_5_3_1"] is False        # "superior a 10 A"
    assert eq["forno"]["independente_exigido_9_5_3_1"] is True
    assert res["quadro"]["carga_instalada_va"] == 5160.0 + 5500.0 + 1270.0 + 1271.0
    assert sum(res["quadro"]["carga_por_fase_va"].values()) \
        == pytest.approx(res["quadro"]["carga_instalada_va"])
    tri = CP.dividir(_previsao(), _criterios(n_fases=3, equipamentos=[
        {"nome": "bomba", "ambiente": "servico", "potencia_va": 3810.0,
         "tensao_v": 220.0, "n_fases": 3}]))
    bomba = [c for c in tri["circuitos"] if c["classe"] == "equipamento"][0]
    assert bomba["corrente_a"] == pytest.approx(3810.0 / (3 ** 0.5 * 220.0))
    assert bomba["fases"] == ["A", "B", "C"]


@pytest.mark.parametrize("apaga, campo", [
    ("tensao_v", "tensao_v"), ("n_fases", "n_fases"), ("equipamentos", "equipamentos"),
    ("limite_va", "limite_va.iluminacao")])
def test_criterio_ausente_nao_vira_circuito(apaga, campo):
    criterios = _criterios()
    del criterios[apaga]
    res = CP.dividir(_previsao(), criterios)
    assert res["ATENDE"] is False and res["circuitos"] == [] and res["quadro"] is None
    assert campo in [e["campo"] for e in res["erros"]]
    assert "DIVISAO NAO FEITA" in CP.relatorio_pt(res)


def test_limite_de_uma_classe_so_faltando_e_nomeado():
    criterios = _criterios(limite_va={"iluminacao": 1000.0, "tomadas": 1500.0})
    res = CP.dividir(_previsao(), criterios)
    assert [e["campo"] for e in res["erros"]] == ["limite_va.tomadas_exclusivas"]


def test_ponto_maior_que_o_limite_e_equipamento_mal_declarado_reprovam():
    res = CP.dividir(_previsao(), _criterios(limite_va={
        "iluminacao": 1000.0, "tomadas": 1500.0, "tomadas_exclusivas": 500.0}))
    assert res["ATENDE"] is False
    grandes = [e["ponto"] for e in res["erros"] if e["code"] == "ponto_maior_que_limite"]
    assert grandes == ["T02.1", "T02.2", "T02.3", "T04.1", "T04.2", "T04.3"]
    ruim = CP.dividir(_previsao(), _criterios(equipamentos=[
        {"nome": "chuveiro", "ambiente": "suite", "potencia_va": 5500.0,
         "tensao_v": 220.0, "n_fases": 2},
        {"nome": "forno", "ambiente": "cozinha", "potencia_va": 3000.0},
        {"nome": "bomba", "ambiente": "servico", "potencia_va": 3000.0,
         "tensao_v": 220.0, "n_fases": 3}]))
    assert ruim["ATENDE"] is False
    assert sorted(e["code"] for e in ruim["erros"]) == [
        "equipamento_em_ambiente_desconhecido", "equipamento_incompleto",
        "equipamento_invalido"]
    assert [c for c in ruim["circuitos"] if c["classe"] == "equipamento"] == []


def test_previsao_reprovada_derruba_o_veredito_da_divisao():
    prev = _previsao()
    prev["ATENDE"] = False
    res = CP.dividir(prev, _criterios())
    assert res["circuitos"] and res["ATENDE"] is False


def test_da_planta_dxf_ao_quadro(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")
    import ambientes_dxf as AD

    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    for x0, y0, w, h, texto in [(0, 0, 4000, 3000, "quarto; quarto"),
                                (4000, 0, 3000, 3000, "cozinha; cozinha"),
                                (0, 3000, 2000, 1500, "banho; banheiro"),
                                (2000, 3000, 5000, 1500, "servico; area de servico")]:
        msp.add_lwpolyline([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)],
                           close=True, dxfattribs={"layer": "AMBIENTES"})
        msp.add_text(texto, dxfattribs={"layer": "AMBIENTES",
                                        "insert": (x0 + w / 2.0, y0 + h / 2.0)})
    caminho = str(tmp_path / "planta.dxf")
    doc.saveas(caminho)
    da_planta = CP.dividir(AD.previsao_de_cargas(caminho), _criterios())
    a_mao = CP.dividir(_previsao(), _criterios())
    assert da_planta["circuitos"] == a_mao["circuitos"]
    assert da_planta["quadro"] == a_mao["quadro"] and da_planta["ATENDE"] is True
    texto = CP.relatorio_pt(da_planta)
    assert "TE2" in texto and "total 5160 VA em 4 circuitos" in texto


# ---------------------------------------------------------------------------
# terceiro passo: comprimento, dimensionamento pelo motor e desenhos
# ---------------------------------------------------------------------------
_GEOMETRIA = {"quarto": [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]],
              "cozinha": [[4.0, 0.0], [7.0, 0.0], [7.0, 3.0], [4.0, 3.0]],
              "banho": [[0.0, 3.0], [2.0, 3.0], [2.0, 4.5], [0.0, 4.5]],
              "servico": [[2.0, 3.0], [7.0, 3.0], [7.0, 4.5], [2.0, 4.5]]}
_TRACADO = {"fator": 1.2, "acrescimo_vertical_m": 2.5}
_INSTALACAO = {"isolacao": "PVC", "metodo_referencia": "B1", "temperatura_ambiente_c": 30.0,
               "circuitos_agrupados": 3, "queda_tensao_max_pct": 4.0,
               "exposicao_dps": "quadro",
               "fator_potencia": {"iluminacao": 1.0, "tomadas": 0.8,
                                  "tomadas_exclusivas": 0.8, "equipamento": 1.0}}


def _comprimentos(valor=10.0, **troca):
    div = CP.dividir(_previsao(), _criterios())
    comp = {c["id"]: {"comprimento_m": valor, "origem": "declarado"} for c in div["circuitos"]}
    for cid, v in troca.items():
        comp[cid] = {"comprimento_m": v, "origem": "declarado"}
    return div, comp


def test_comprimento_estimado_e_a_distancia_ortogonal_ao_vertice_mais_distante():
    div = CP.dividir(_previsao(), _criterios())
    est = CP.comprimentos_pela_planta(div, _GEOMETRIA, [2.0, 3.0], _TRACADO)
    assert est["erros"] == []
    achado = {cid: (d["distancia_ortogonal_m"], d["ambiente_mais_distante"],
                    d["comprimento_m"], d["origem"]) for cid, d in est["comprimentos"].items()}
    assert achado == {
        "IL1": (8.0, "cozinha", pytest.approx(12.1), "estimado_pela_planta"),   # (7; 0)
        "TG1": (5.0, "quarto", pytest.approx(8.5), "estimado_pela_planta"),     # (0; 0)
        "TE1": (8.0, "cozinha", pytest.approx(12.1), "estimado_pela_planta"),
        "TE2": (6.5, "servico", pytest.approx(10.3), "estimado_pela_planta")}   # (7; 4,5)
    # o quadro anda so em y e depois so em x: o comprimento acompanha cada eixo
    em_y = CP.comprimentos_pela_planta(div, _GEOMETRIA, [2.0, 0.0], _TRACADO)["comprimentos"]
    em_x = CP.comprimentos_pela_planta(div, _GEOMETRIA, [0.0, 3.0], _TRACADO)["comprimentos"]
    assert em_y["TE2"]["distancia_ortogonal_m"] == 9.5      # 5 + 4,5
    assert em_x["TE2"]["distancia_ortogonal_m"] == 8.5      # 7 + 1,5
    assert em_y["TE2"]["comprimento_m"] == pytest.approx(1.2 * 9.5 + 2.5)


@pytest.mark.parametrize("quadro, tracado, campo", [
    (None, _TRACADO, "quadro"),
    ([2.0, 3.0], {"acrescimo_vertical_m": 2.5}, "tracado.fator"),
    ([2.0, 3.0], {"fator": 0.9, "acrescimo_vertical_m": 2.5}, "tracado.fator"),
    ([2.0, 3.0], {"fator": 1.2}, "tracado.acrescimo_vertical_m"),
    ([2.0, 3.0], None, "tracado.fator")])
def test_sem_quadro_ou_sem_criterio_de_tracado_nao_ha_comprimento(quadro, tracado, campo):
    div = CP.dividir(_previsao(), _criterios())
    est = CP.comprimentos_pela_planta(div, _GEOMETRIA, quadro, tracado)
    assert est["comprimentos"] == {} and campo in [e["campo"] for e in est["erros"]]
    criterios = _criterios(instalacao=_INSTALACAO)
    if tracado is not None:
        criterios["tracado"] = tracado
    dim = CP.dimensionar_da_planta(div, {"geometria": _GEOMETRIA, "quadro_m": quadro}, criterios)
    assert dim["ATENDE"] is False and dim["circuits"] is None and dim["resumo"] == []
    codigos = [e["code"] for e in dim["erros"]]
    assert "comprimento_ausente" in codigos
    assert CP.desenhos(dim, "nao_usada")["files"] == []


def test_dimensionamento_e_o_do_motor_para_o_mesmo_circuito():
    import dimensionamento_eletrico_residencial as DR

    div, comp = _comprimentos(TE1=20.0)
    dim = CP.dimensionar(div, _INSTALACAO, comp)
    assert dim["ATENDE"] is True and dim["erros"] == []
    assert [r["id"] for r in dim["resumo"]] == ["IL1", "TG1", "TE1", "TE2"]
    a_mao = DR.calculate_residential_circuit_designs({
        "points": [{"id": "p", "room": "cozinha", "kind": "tug", "power_va": 1900.0,
                    "voltage_v": 127.0}],
        "designs": [{"id": "X", "point_ids": ["p"], "length_m": 20.0, "system": "monofasico",
                     "conductors_loaded": 2, "insulation": "PVC", "reference_method": "B1",
                     "ambient_temperature_C": 30.0, "grouping_count": 3, "power_factor": 0.8,
                     "voltage_drop_limit_pct": 4.0, "use": "forca",
                     "protection": {"location": "molhado", "exposure": "quadro"}}]}, [])
    esperado = a_mao["designs"][0]
    te1 = [r for r in dim["resumo"] if r["id"] == "TE1"][0]
    assert te1["secao_mm2"] == esperado["conductor"]["secao_mm2"]
    assert te1["disjuntor_a"] == esperado["protection"]["disjuntor"]["IN"]
    assert te1["queda_pct"] == esperado["conductor"]["dv_pct"]
    assert te1["corrente_a"] == pytest.approx(1900.0 / 127.0) and te1["comprimento_m"] == 20.0
    # a protecao nunca fica abaixo da corrente nem acima do que o condutor leva
    for d in dim["circuits"]["designs"]:
        assert d["load"]["current_a"] <= d["protection"]["disjuntor"]["IN"] <= d["conductor"]["Iz"]
        assert d["conductor"]["dv_pct"] <= 4.0


def test_comprimento_maior_engrossa_o_condutor_e_o_absurdo_reprova():
    def _te1(metros):
        div, comp = _comprimentos(TE1=metros)
        return CP.dimensionar(div, _INSTALACAO, comp)

    curto, longo = _te1(20.0), _te1(60.0)
    secao = lambda dim: [r["secao_mm2"] for r in dim["resumo"] if r["id"] == "TE1"][0]
    assert secao(curto) < secao(longo) and longo["ATENDE"] is True
    absurdo = _te1(5000.0)
    assert absurdo["ATENDE"] is False
    assert "TE1" not in [r["id"] for r in absurdo["resumo"]]
    assert [e["design_id"] for e in absurdo["erros"]] == ["TE1"]


def test_local_do_circuito_e_o_mais_restritivo_dos_ambientes():
    locais = {c["id"]: c["local"] for c in CP.dividir(_previsao(), _criterios())["circuitos"]}
    assert locais == {"IL1": "banheiro", "TG1": "banheiro", "TE1": "molhado", "TE2": "molhado"}
    secos = AR.rodar({"ambientes": [
        {"nome": "quarto", "tipo": "quarto", "area_m2": 12.0, "perimetro_m": 14.0},
        {"nome": "sala", "tipo": "sala", "area_m2": 16.0, "perimetro_m": 16.0}]})
    assert {c["local"] for c in CP.dividir(secos, _criterios())["circuitos"]} == {"seco"}
    varanda = AR.rodar({"ambientes": [
        {"nome": "quarto", "tipo": "quarto", "area_m2": 12.0, "perimetro_m": 14.0},
        {"nome": "varanda", "tipo": "varanda", "area_m2": 4.0, "perimetro_m": 8.0}]})
    assert {c["local"] for c in CP.dividir(varanda, _criterios())["circuitos"]} == {"externo"}
    # iluminacao em local seco nao leva o diferencial; com banheiro no circuito, leva
    def _dr_da_iluminacao(previsao):
        div = CP.dividir(previsao, _criterios())
        comp = {c["id"]: {"comprimento_m": 10.0, "origem": "declarado"}
                for c in div["circuitos"]}
        return [r["dr"] for r in CP.dimensionar(div, _INSTALACAO, comp)["resumo"]
                if r["classe"] == "iluminacao"]
    assert _dr_da_iluminacao(secos) == [False]
    assert _dr_da_iluminacao(_previsao()) == [True]


def test_comprimento_declarado_vence_o_estimado_e_a_origem_fica_dita():
    div = CP.dividir(_previsao(), _criterios())
    criterios = _criterios(instalacao=_INSTALACAO, tracado=_TRACADO,
                           comprimentos_m={"TE1": 31.0})
    dim = CP.dimensionar_da_planta(div, {"geometria": _GEOMETRIA, "quadro_m": [2.0, 3.0]},
                                   criterios)
    assert dim["ATENDE"] is True
    origem = {r["id"]: (r["origem_comprimento"], r["comprimento_m"]) for r in dim["resumo"]}
    assert origem["TE1"] == ("declarado", 31.0)
    assert origem["TE2"] == ("estimado_pela_planta", pytest.approx(10.3))
    texto = CP.relatorio_dimensionamento_pt(dim)
    assert "declarado" in texto and "estimado" in texto and "ATENDE: True" in texto
    # tudo declarado: nem o quadro nem o criterio de tracado fazem falta
    tudo = _criterios(instalacao=_INSTALACAO,
                      comprimentos_m={c["id"]: 12.0 for c in div["circuitos"]})
    so_declarado = CP.dimensionar_da_planta(div, {"geometria": {}, "quadro_m": None}, tudo)
    assert so_declarado["ATENDE"] is True and so_declarado["erros"] == []


@pytest.mark.parametrize("campo", ["isolacao", "metodo_referencia", "temperatura_ambiente_c",
                                   "circuitos_agrupados", "queda_tensao_max_pct",
                                   "exposicao_dps", "fator_potencia"])
def test_dado_de_instalacao_ausente_nao_e_suposto(campo):
    div, comp = _comprimentos()
    instalacao = copy.deepcopy(_INSTALACAO)
    del instalacao[campo]
    dim = CP.dimensionar(div, instalacao, comp)
    assert dim["ATENDE"] is False and dim["circuits"] is None
    assert any(e["campo"].startswith("instalacao.%s" % campo) for e in dim["erros"])


def test_fator_de_potencia_de_uma_classe_so_faltando_e_nomeado():
    div, comp = _comprimentos()
    instalacao = copy.deepcopy(_INSTALACAO)
    del instalacao["fator_potencia"]["tomadas"]
    dim = CP.dimensionar(div, instalacao, comp)
    assert [e["campo"] for e in dim["erros"]] == ["instalacao.fator_potencia.tomadas"]


def test_unifilar_e_quadro_saem_com_todos_os_circuitos(tmp_path):
    import xml.dom.minidom

    div = CP.dividir(_previsao(), _criterios(equipamentos=[
        {"nome": "chuveiro", "ambiente": "banho", "potencia_va": 5500.0,
         "tensao_v": 220.0, "n_fases": 2}]))
    comp = {c["id"]: {"comprimento_m": 12.0, "origem": "declarado"} for c in div["circuitos"]}
    dim = CP.dimensionar(div, _INSTALACAO, comp)
    assert dim["ATENDE"] is True
    emitido = CP.desenhos(dim, str(tmp_path))
    assert emitido["files"] == ["unifilar.svg", "quadro-cargas.svg"]
    for nome in emitido["files"]:
        svg = (tmp_path / nome).read_text(encoding="utf-8")
        xml.dom.minidom.parseString(svg)                 # e' XML de verdade
        for c in div["circuitos"]:
            assert ">%s<" % c["id"] in svg, (nome, c["id"])
    quadro = (tmp_path / "quadro-cargas.svg").read_text(encoding="utf-8")
    eq = [r for r in dim["resumo"] if r["id"] == "EQ1"][0]
    assert "%d A" % eq["disjuntor_a"] in quadro and "5500 VA" in quadro


def test_da_planta_com_quadro_marcado_ao_dimensionamento(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")
    import ambientes_dxf as AD

    def _planta(nome, quadros):
        doc = ezdxf.new("R2018")
        doc.header["$INSUNITS"] = 4
        msp = doc.modelspace()
        for x0, y0, w, h, texto in [(0, 0, 4000, 3000, "quarto; quarto"),
                                    (4000, 0, 3000, 3000, "cozinha; cozinha"),
                                    (0, 3000, 2000, 1500, "banho; banheiro"),
                                    (2000, 3000, 5000, 1500, "servico; area de servico")]:
            msp.add_lwpolyline([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)],
                               close=True, dxfattribs={"layer": "AMBIENTES"})
            msp.add_text(texto, dxfattribs={"layer": "AMBIENTES",
                                            "insert": (x0 + w / 2.0, y0 + h / 2.0)})
        for q in quadros:
            msp.add_point(q, dxfattribs={"layer": "QUADRO"})
        caminho = str(tmp_path / nome)
        doc.saveas(caminho)
        return caminho

    criterios = _criterios(instalacao=_INSTALACAO, tracado=_TRACADO)
    prev = AD.previsao_de_cargas(_planta("um.dxf", [(2000, 3000)]))
    assert prev["leitura_dxf"]["quadro_m"] == [2.0, 3.0]
    assert prev["leitura_dxf"]["geometria"] == _GEOMETRIA
    dim = CP.dimensionar_da_planta(CP.dividir(prev, criterios), prev["leitura_dxf"], criterios)
    assert dim["ATENDE"] is True
    assert {r["id"]: r["comprimento_m"] for r in dim["resumo"]} == {
        "IL1": pytest.approx(12.1), "TG1": pytest.approx(8.5),
        "TE1": pytest.approx(12.1), "TE2": pytest.approx(10.3)}
    # dois quadros marcados: erro nomeado, posicao nao escolhida, veredito cai
    dois = AD.previsao_de_cargas(_planta("dois.dxf", [(2000, 3000), (6000, 1000)]))
    assert dois["leitura_dxf"]["quadro_m"] is None and dois["ATENDE"] is False
    assert [e["code"] for e in dois["leitura_dxf"]["erros"]] == ["varios_quadros"]
    # nenhum quadro marcado nao e' erro de leitura: so impede o comprimento estimado
    nenhum = AD.previsao_de_cargas(_planta("nenhum.dxf", []))
    assert nenhum["leitura_dxf"]["quadro_m"] is None and nenhum["ATENDE"] is True
    sem = CP.dimensionar_da_planta(CP.dividir(nenhum, criterios), nenhum["leitura_dxf"],
                                   criterios)
    assert sem["ATENDE"] is False and "quadro_nao_marcado" in [e["code"] for e in sem["erros"]]
