# ============================================================================
# test_criterios_planta.py - OS CRITERIOS DE PROJETO LIDOS COMO ESTRUTURA
# TIPADA (plano de 2026-10-08, Fase 1 e Fase 5). O que se cobra: chave com o
# nome errado reprova em vez de sumir, o que e' lido volta igual ao dicionario
# que o motor consome, e nada e' preenchido por conta propria.
# ============================================================================
"""Leitura tipada dos criterios de projeto do eletrico sobre planta."""

import copy
import dataclasses
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import arquitetura_residencial as AR
import circuitos_planta as CP
import criterios_planta as CR
import test_circuitos_planta as TCP        # os mesmos dados de instalacao e de rede

_MINIMO = {"tensao_v": 127.0, "n_fases": 2,
           "limite_va": {"iluminacao": 1000.0, "tomadas": 1500.0, "tomadas_exclusivas": 2000.0},
           "equipamentos": []}
_COMPLETO = dict(
    _MINIMO,
    equipamentos=[{"nome": "chuveiro", "ambiente": "banho", "potencia_va": 5500.0,
                   "tensao_v": 220.0, "n_fases": 2, "grupo_demanda": "aquecimento"},
                  {"nome": "forno", "ambiente": "cozinha", "potencia_va": 3000.0,
                   "tensao_v": 220.0, "n_fases": 2}],
    instalacao=copy.deepcopy(TCP._INSTALACAO),
    tracado={"fator": 1.2, "acrescimo_vertical_m": 3.0},
    comprimentos_m={"IL1": 18.0},
    rede=dict(TCP._REDE),
    demanda={"motores": [], "iluminacao_especial": [{"power_kw": 1.2, "kind": "incandescent"}],
             "modulo_por_tipo": {"area_servico": "servico"}})


def _com(**troca):
    c = copy.deepcopy(_COMPLETO)
    c.update(troca)
    return c


@pytest.mark.parametrize("criterios", [_MINIMO, _COMPLETO])
def test_o_que_e_lido_volta_igual_ao_dicionario_que_o_motor_consome(criterios):
    lidos, erros = CR.ler(copy.deepcopy(criterios))
    assert erros == [] and isinstance(lidos, CR.Criterios)
    assert lidos.para_dict() == criterios


def test_bloco_opcional_ausente_fica_none_e_nao_volta_preenchido():
    lidos, _erros = CR.ler(copy.deepcopy(_MINIMO))
    for nome in ("instalacao", "tracado", "comprimentos_m", "rede", "demanda"):
        assert getattr(lidos, nome) is None and nome not in lidos.para_dict()
    forno = CR.ler(_com())[0].equipamentos[1]
    assert forno.grupo_demanda is None and "grupo_demanda" not in forno.para_dict()


def test_os_criterios_lidos_sao_imutaveis():
    lidos, _erros = CR.ler(_com())
    with pytest.raises(dataclasses.FrozenInstanceError):
        lidos.tensao_v = 220.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        lidos.equipamentos[0].potencia_va = 1.0


@pytest.mark.parametrize("troca, campo, parecida", [
    ({"comprimento_m": {"IL1": 18.0}}, "comprimento_m", "comprimentos_m"),
    ({"limites_va": {}}, "limites_va", "limite_va"),
    ({"tracado": {"fator": 1.2, "acrescimo_vertical": 3.0}},
     "tracado.acrescimo_vertical", "acrescimo_vertical_m"),
    ({"rede": dict(_COMPLETO["rede"], tipo_de_rede="aerea")}, "rede.tipo_de_rede", None),
    ({"demanda": dict(_COMPLETO["demanda"], motor=[])}, "demanda.motor", "motores"),
    ({"equipamentos": [dict(_COMPLETO["equipamentos"][0], potencia_w=5500.0)]},
     "equipamentos[1].potencia_w", "potencia_va"),
    ({"limite_va": dict(_MINIMO["limite_va"], tomada=1.0)}, "limite_va.tomada", "tomadas"),
])
def test_chave_com_nome_errado_reprova_e_diz_a_parecida(troca, campo, parecida):
    lidos, erros = CR.ler(_com(**troca))
    assert lidos is None
    achados = [e for e in erros if e["code"] == "criterio_desconhecido"]
    assert [(e["campo"], e["parecida"]) for e in achados] == [(campo, parecida)]
    assert campo in CR.relatorio_pt(erros)


def test_fator_de_potencia_com_classe_errada_reprova_pelos_dois_lados():
    inst = copy.deepcopy(_COMPLETO["instalacao"])
    inst["fator_potencia"]["equipamentos"] = inst["fator_potencia"].pop("equipamento")
    _lidos, erros = CR.ler(_com(instalacao=inst))
    assert {(e["code"], e["campo"]) for e in erros} == {
        ("criterio_desconhecido", "instalacao.fator_potencia.equipamentos"),
        ("criterio_ausente", "instalacao.fator_potencia.equipamento")}


def test_sem_a_leitura_tipada_o_comprimento_declarado_com_nome_errado_some_em_silencio():
    """O defeito que a leitura fecha: o motor aceita o dicionario com a chave
    errada e dimensiona pelo comprimento estimado, sem erro nenhum."""
    previsao = AR.rodar({"ambientes": [
        {"nome": "sala", "tipo": "sala", "area_m2": 16.0, "perimetro_m": 16.0}]})
    leitura = {"geometria": {"sala": [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]},
               "quadro_m": [0.0, 0.0]}
    certo = _com(equipamentos=[], comprimentos_m={"IL1": 40.0})
    torto = _com(equipamentos=[], comprimento_m={"IL1": 40.0})
    del torto["comprimentos_m"]
    res = {}
    for nome, crit in (("certo", certo), ("torto", torto)):
        div = CP.dividir(previsao, crit)
        res[nome] = CP.dimensionar_da_planta(div, leitura, crit)
    assert res["certo"]["comprimentos"]["IL1"] == {"comprimento_m": 40.0, "origem": "declarado"}
    assert res["torto"]["erros"] == [] and res["torto"]["comprimentos"]["IL1"]["origem"] != "declarado"
    assert res["torto"]["comprimentos"]["IL1"]["comprimento_m"] != 40.0
    # a leitura tipada reprova o mesmo arquivo antes de qualquer conta
    assert CR.ler(torto)[0] is None and CR.ler(certo)[1] == []


def test_o_que_falta_continua_dito_pelo_validador_do_motor():
    sem_tensao = copy.deepcopy(_MINIMO)
    del sem_tensao["tensao_v"]
    lidos, erros = CR.ler(sem_tensao)
    assert lidos is None and erros == CP._erros_dos_criterios(sem_tensao)
    _l, erros = CR.ler(_com(rede={"location_factor": 1.0}))
    assert sorted(e["campo"] for e in erros) == [
        "rede.network_kind", "rede.supply_type", "rede.voltage_system"]
    _l, erros = CR.ler(_com(equipamentos=[{"nome": "x"}]))
    assert [e["code"] for e in erros] == ["equipamento_incompleto"]
    assert CR.ler([1, 2])[0] is None and CR.ler(None)[1]


def _linha_de_comando(tmp_path, criterios):
    import json
    import subprocess
    import test_ambientes_dxf as TAD
    planta = TAD._planta(tmp_path, TAD._CASA_MM)
    arq = tmp_path / "criterios.json"
    arq.write_text(json.dumps(criterios), encoding="utf-8")
    galpao = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return subprocess.run(
        [sys.executable, os.path.join(galpao, "ambientes_dxf.py"), planta,
         "criterios=%s" % arq],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=dict(os.environ, PYTHONUTF8="1"), cwd=str(tmp_path))


def test_linha_de_comando_para_no_arquivo_de_criterios_com_chave_errada(tmp_path):
    pytest.importorskip("ezdxf")
    torto = copy.deepcopy(_MINIMO)
    torto["limite_va"]["tomada"] = torto["limite_va"].pop("tomadas")
    r = _linha_de_comando(tmp_path, torto)
    assert r.returncode == 1
    assert "ERROS NO ARQUIVO DE CRITERIOS" in r.stdout and "limite_va.tomada" in r.stdout
    assert "QUADRO" not in r.stdout.split("ERROS NO ARQUIVO DE CRITERIOS")[1]
    certo = _linha_de_comando(tmp_path, copy.deepcopy(_MINIMO))
    assert certo.returncode == 0 and "ERROS NO ARQUIVO DE CRITERIOS" not in certo.stdout
