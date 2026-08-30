"""Relatorio formal de compatibilizacao: clash federado -> pendencias rastreaveis
(BCF-like) + matriz de coordenacao. Camada PURA (CI)."""
import os
import sys

from xml.dom.minidom import parseString

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import compatibilizacao as cp


def _rep():
    return {"por_par": {"concretoxeletrico": 2, "concretoxhidraulica": 1},
            "clashes": [
                {"a": "C-P1E", "b": "E-CALHA", "disciplinas": "concretoxeletrico",
                 "tipos": "ColumnxCableCarrier", "vol_mm3": 8.0e6, "esperado": False},
                {"a": "C-V1", "b": "H-TUBO", "disciplinas": "concretoxhidraulica",
                 "tipos": "BeamxPipe", "vol_mm3": 6.0e5, "esperado": False},
                {"a": "C-P2D", "b": "E-DESC", "disciplinas": "concretoxeletrico",
                 "tipos": "ColumnxCable", "vol_mm3": 3.0e5, "esperado": True}]}


def test_selftest():
    assert cp._selftest() is True


def test_ids_sequenciais_revisar_antes_do_esperado():
    pend = cp.gerar_pendencias(_rep())
    assert [p["id"] for p in pend] == ["CLH-001", "CLH-002", "CLH-003"]
    # a revisar (por volume desc) antes do esperado
    assert not pend[0]["esperado"] and not pend[1]["esperado"]
    assert pend[2]["esperado"]


def test_severidade_por_volume():
    pend = cp.gerar_pendencias(_rep())
    assert pend[0]["severidade"] == "Alta"          # 8e6 > 5e6
    assert pend[1]["severidade"] == "Media"         # 6e5 > 5e5
    assert pend[2]["severidade"] == "Informativa"   # esperado


def test_status_e_responsavel():
    pend = cp.gerar_pendencias(_rep())
    assert pend[0]["status"] == cp.STATUS_ABERTO
    assert pend[2]["status"] == cp.STATUS_APROVADO   # montagem intencional
    # estrutura x eletrica -> a eletrica se adequa
    assert pend[0]["responsavel"] == "eletrico"


def test_guid_estavel():
    """Mesmo conflito -> mesmo GUID entre execucoes (rastreabilidade)."""
    a = cp.gerar_pendencias(_rep())[0]["guid"]
    b = cp.gerar_pendencias(_rep())[0]["guid"]
    assert a == b and len(a) > 20


def test_guid_unico_para_clashes_identicos_e_estavel():
    rep = _rep()
    repetido = dict(rep["clashes"][0])
    rep["clashes"] = [repetido, dict(repetido)]

    primeira = cp.gerar_pendencias(rep)
    segunda = cp.gerar_pendencias(rep)

    assert [item["guid"] for item in primeira] == [
        item["guid"] for item in segunda]
    assert len({item["guid"] for item in primeira}) == 2
    assert primeira[0]["guid"] != primeira[1]["guid"]


def test_resumo():
    pend = cp.gerar_pendencias(_rep())
    r = cp.resumo(pend)
    assert r["total"] == 3 and r["abertas"] == 2
    assert r["por_severidade"]["Alta"] == 1


def test_matriz_coordenacao_simetrica():
    mat = cp.matriz_coordenacao(_rep())
    assert mat["matriz"]["concreto"]["eletrico"] == 2
    assert mat["matriz"]["eletrico"]["concreto"] == 2


def test_bcf_topics():
    pend = cp.gerar_pendencias(_rep())
    bcf = cp.bcf_topics(pend)
    assert bcf["n"] == 3 and bcf["bcf_version"].startswith("2.1")
    assert bcf["topics"][0]["topic_status"] == "Open"
    assert bcf["topics"][0]["priority"] == "High"      # severidade Alta
    assert bcf["topics"][2]["topic_status"] == "Closed"  # esperado


def test_matriz_svg_xml_valido():
    svg = cp.matriz_svg(_rep())
    assert svg.startswith("<svg") and "MATRIZ DE COMPATIBILIZACAO" in svg
    parseString(svg.encode("utf-8"))                    # parse, nao substring


def test_sem_conflitos():
    assert cp.gerar_pendencias({"clashes": []}) == []
    parseString(cp.matriz_svg({"por_par": {}, "clashes": []}).encode("utf-8"))
    assert "Nenhum conflito" in cp.relatorio_pt([])
