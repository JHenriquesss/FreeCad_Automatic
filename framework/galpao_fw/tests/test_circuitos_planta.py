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
