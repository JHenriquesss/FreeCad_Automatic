# ============================================================================
# test_validacao_coerencia.py - o caminho SPEC-DIRETO (carregar_spec/JSON editado)
# nao pode CERTIFICAR geometria/fisica degenerada. Antes da guarda de coerencia
# em projeto_spec.validar(), specs com span<0, ridge<=eave, slope<=0, V0=0,
# aguas invalido ou abertura > fachada passavam e o motor dava atende_global=True
# (ou crashava em eave=0). Ver cacada de bugs sessao 14.
# ============================================================================
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS


def _base():
    """Spec de amostra COMPLETO e valido (fundacao=bloco). validar() -> ok."""
    p = os.path.join(GALPAO, "spec_amostra_engenheiro.json")
    return json.load(open(p, encoding="utf-8"))


def _bloqueado_em(spec, path_prefixo):
    """True se validar() reprova (ok=False) por causa de um item cujo path
    comeca com path_prefixo."""
    r = PS.validar(spec)
    if r["ok"]:
        return False
    return any(p == path_prefixo or p.startswith(path_prefixo) for p, _ in r["faltando"])


def test_amostra_valida_passa():
    """Sanidade: o spec de amostra (valido) NAO e barrado pela guarda."""
    r = PS.validar(_base())
    assert r["ok"], ("amostra valida bloqueada: %s" % r["faltando"])


def test_span_negativo_bloqueia():
    s = _base(); s["geometria"]["span"] = -20.0
    assert _bloqueado_em(s, "geometria.span")


def test_dimensoes_nao_positivas_bloqueiam():
    for campo in ("comprimento", "eave", "bay"):
        s = _base(); s["geometria"][campo] = 0.0
        assert _bloqueado_em(s, "geometria." + campo), campo


def test_ridge_menor_igual_eave_bloqueia():
    # invertido
    s = _base(); s["geometria"]["ridge"] = s["geometria"]["eave"] - 1.0
    assert _bloqueado_em(s, "geometria.ridge")
    # plano (ridge == eave)
    s = _base(); s["geometria"]["ridge"] = s["geometria"]["eave"]
    assert _bloqueado_em(s, "geometria.ridge")


def test_slope_nao_positivo_bloqueia():
    for sl in (0.0, -0.1):
        s = _base(); s["cobertura"]["slope"] = sl
        assert _bloqueado_em(s, "cobertura.slope"), sl


def test_aguas_invalido_bloqueia():
    s = _base(); s["cobertura"]["aguas"] = 3
    assert _bloqueado_em(s, "cobertura.aguas")


def test_v0_abaixo_do_mapa_bloqueia():
    s = _base(); s["vento"]["v0"] = 0.0
    assert _bloqueado_em(s, "vento.v0")
    s = _base(); s["vento"]["v0"] = 25.0
    assert _bloqueado_em(s, "vento.v0")


def test_v0_no_limite_passa():
    s = _base(); s["vento"]["v0"] = 30.0
    r = PS.validar(s)
    assert r["ok"], r["faltando"]


def test_abertura_maior_que_fachada_bloqueia():
    # portao 50 x 40 m num galpao 28,5 x 20 m
    s = _base(); s["aberturas"]["portao_frente"] = [50000.0, 40000.0]
    assert _bloqueado_em(s, "aberturas.portao_frente")


def test_spans_multivao_nao_positivo_bloqueia():
    s = _base(); s["geometria"]["spans"] = [20.0, -5.0]
    assert _bloqueado_em(s, "geometria.spans")


def test_abertura_normal_nao_bloqueia():
    # a amostra ja tem portao 4,5x2,5 e janela 3,0x1,0 - devem passar
    r = PS.validar(_base())
    assert not any(p.startswith("aberturas.") for p, _ in r["faltando"])
