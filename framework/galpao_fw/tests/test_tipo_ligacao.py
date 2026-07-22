"""Tipo de ligacao (soldada/parafusada): wizard pergunta, spec valida e propaga."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import wizard as W
import projeto_spec as PS


def _respostas_min(**over):
    r = {"area_lote_m2": 1000.0, "span": 20.0, "comprimento": 40.0, "eave": 6.0,
         "v0": 40.0, "sigma_solo": 300.0}
    r.update(over)
    return r


def test_wizard_pergunta_tipo_ligacao_existe():
    chaves = [k for k, *_ in W.PERGUNTAS]
    assert "tipo_ligacao" in chaves


def test_default_soldada():
    s = W.construir_spec(_respostas_min())
    assert s["estrutura"]["tipo_ligacao"] == "soldada"


def test_normaliza_maiuscula_espaco():
    s = W.construir_spec(_respostas_min(tipo_ligacao="  Parafusada "))
    assert s["estrutura"]["tipo_ligacao"] == "parafusada"


def test_validacao_rejeita_valor_invalido():
    s = W.construir_spec(_respostas_min())
    s["estrutura"]["tipo_ligacao"] = "solda"          # erro de digitacao
    chaves = [c for c, _ in PS.validar(s)["faltando"]]
    assert "estrutura.tipo_ligacao" in chaves


def test_validacao_aceita_soldada_e_parafusada():
    for v in ("soldada", "parafusada"):
        s = W.construir_spec(_respostas_min(tipo_ligacao=v))
        chaves = [c for c, _ in PS.validar(s)["faltando"]]
        assert "estrutura.tipo_ligacao" not in chaves


def test_propaga_para_rodar_params():
    s = W.construir_spec(_respostas_min(tipo_ligacao="parafusada"))
    p = PS.to_rodar_params(s)
    assert p["tipo_ligacao"] == "parafusada"
