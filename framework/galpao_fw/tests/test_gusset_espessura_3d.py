# ============================================================================
# test_gusset_espessura_3d.py - a chapa de GUSSET desenhada tem que ter a
# espessura DIMENSIONADA.
#
# Mesma familia dos PRs #29/#30/#31/#32/#33: o calc decide
# `gusset_adotado.t_mm` (Whitmore / escoamento / bloco de cisalhamento),
# rodar_projeto ja gravava no spec, mas `to_build_kwargs` nao levava -> o build
# usava o default `thick=12.0` do `_gusset_tri`. Na amostra da 12,0 e COINCIDE;
# em qualquer projeto com contravento mais carregado o modelo, a prancha e o
# takeoff mostrariam chapa mais fina que a calculada.
#
# O bracket do CONSOLE tambem usa _gusset_tri, mas de proposito NAO recebe
# GUSSET_T: e chapa de outra peca, com espessura propria (console_adotado).
# ============================================================================
import ast
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS
import rodar_projeto as RP

SPEC_JSON = os.path.join(GALPAO, "spec_amostra_engenheiro.json")
BUILD_SRC = os.path.join(GALPAO, "build_galpao.py")


@pytest.fixture
def spec():
    with open(SPEC_JSON, encoding="utf-8") as fh:
        return json.load(fh)


class _FakeSrv:
    enviado = None

    def __init__(self, host):
        pass

    def execute(self, src):
        _FakeSrv.enviado = src
        return {"success": True, "result": {"elementos": 0}}


def test_mapper_leva_espessura_dimensionada(spec):
    spec.setdefault("estrutura", {})["gusset_adotado"] = {"t_mm": 19.0,
                                                          "perna_solda_mm": 6.0}
    assert PS.to_build_kwargs(spec)["gusset_t"] == 19.0


def test_sem_gusset_adotado_fica_none(spec):
    spec.get("estrutura", {}).pop("gusset_adotado", None)
    assert PS.to_build_kwargs(spec)["gusset_t"] is None


def test_espessura_chega_ao_build(monkeypatch, spec):
    """Valor DIFERENTE de 12: com 12 o teste passaria mesmo sem o fix."""
    import xmlrpc.client
    spec.setdefault("estrutura", {})["gusset_adotado"] = {"t_mm": 19.0}
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _FakeSrv)
    RP.montar_modelo(spec, GALPAO, "t")
    assert "'gusset_t': 19.0" in _FakeSrv.enviado


def test_gussets_de_contravento_usam_o_global():
    """Os dois gussets de contravento (cobertura e parede) passam thick=GUSSET_T."""
    txt = open(BUILD_SRC, encoding="utf-8").read()
    assert txt.count("thick=GUSSET_T") == 2


def test_bracket_do_console_nao_usa_o_gusset():
    """O bracket do console e chapa de OUTRA peca - nao pode herdar a espessura
    do gusset de contravento (semantica diferente)."""
    arv = ast.parse(open(BUILD_SRC, encoding="utf-8").read())
    for no in ast.walk(arv):
        if (isinstance(no, ast.Call) and getattr(no.func, "id", "") == "_gusset_tri"
                and any(isinstance(a, ast.Constant) and "CONSOLE" in str(a.value)
                        for a in no.args)):
            kw = {k.arg for k in no.keywords}
            assert "thick" not in kw


def test_rotulo_do_takeoff_deriva():
    txt = open(BUILD_SRC, encoding="utf-8").read()
    assert '"chapa-%.0f" % GUSSET_T' in txt
    assert '"Chapas gusset (contravento)", "chapa-12"' not in txt


def test_global_em_configurar_e_reset():
    """Sem reset, um 2o projeto na mesma sessao herda a chapa do 1o."""
    arv = ast.parse(open(BUILD_SRC, encoding="utf-8").read())
    fn = {n.name: n for n in arv.body if isinstance(n, ast.FunctionDef)}
    for alvo in ("configurar", "reset"):
        decl = {nome for n in ast.walk(fn[alvo]) if isinstance(n, ast.Global)
                for nome in n.names}
        assert "GUSSET_T" in decl, "%s nao declara GUSSET_T" % alvo
    atrib = {t.id for n in ast.walk(fn["reset"]) if isinstance(n, ast.Assign)
             for t in n.targets if isinstance(t, ast.Name)}
    assert "GUSSET_T" in atrib
