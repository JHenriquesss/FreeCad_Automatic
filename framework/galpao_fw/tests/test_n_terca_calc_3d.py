# ============================================================================
# test_n_terca_calc_3d.py - o 3D tem que construir com o MESMO n de tercas que a
# memoria de calculo certificou.
#
# BUG QUE ISTO TRAVA: `n_terca` era HARDCODED em build_galpao (`n_terca = 3`),
# enquanto o gate 7 auto-dimensiona (sobe ate esp_terca <= vao_max da telha, NBR
# 14762). Na amostra o calc adotou 5/agua (esp 2,02 m, vao_max 2,14 m) e o modelo
# saiu com 3 (esp 3,37 m = +57% do vao_max). Resultado: memoria diz "telha
# APROVADA", mas o 3D, as pranchas e o TAKEOFF (lista de compra) mostram 6 linhas
# de terca em vez de 10 - o montador instala a telha vencendo 3,37 m.
#
# POR QUE ESTE TESTE NAO IMPORTA build_galpao: ele faz `import FreeCAD` no topo,
# entao qualquer teste que o importe vira 'build' e e DESELECIONADO sem o bridge -
# o mesmo ponto cego que deixou PE04/PE07 passarem. Aqui interceptamos o XMLRPC e
# inspecionamos o codigo que SERIA enviado ao FreeCAD: roda sempre, no CI.
# ============================================================================
import ast
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import rodar_projeto as RP

SPEC_JSON = os.path.join(GALPAO, "spec_amostra_engenheiro.json")
BUILD_SRC = os.path.join(GALPAO, "build_galpao.py")


@pytest.fixture
def spec():
    with open(SPEC_JSON, encoding="utf-8") as fh:
        return json.load(fh)


class _FakeSrv:
    """Captura o codigo enviado em vez de falar com o FreeCAD."""
    enviado = None

    def __init__(self, host):
        pass

    def execute(self, src):
        _FakeSrv.enviado = src
        return {"success": True, "result": {"elementos": 0}}


def _capta(monkeypatch, spec, **kw):
    import xmlrpc.client
    _FakeSrv.enviado = None
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _FakeSrv)
    RP.montar_modelo(spec, GALPAO, "t", **kw)
    return _FakeSrv.enviado


def test_n_terca_do_calc_chega_ao_build(monkeypatch, spec):
    """O valor auto-dimensionado tem que aparecer no configurar() enviado."""
    src = _capta(monkeypatch, spec, n_terca=5)
    assert "'n_terca': 5" in src, "n_terca do calc nao foi propagado ao build 3D"


def test_sem_n_terca_nao_injeta_chave(monkeypatch, spec):
    """Back-compat: quem nao passa n_terca deixa o build no seu default."""
    src = _capta(monkeypatch, spec, n_terca=None)
    assert "'n_terca'" not in src


@pytest.mark.parametrize("n", [1, 4, 7, 12])
def test_varios_valores_propagam(monkeypatch, spec, n):
    src = _capta(monkeypatch, spec, n_terca=n)
    assert "'n_terca': %d" % n in src


def test_build_nao_tem_mais_n_terca_hardcoded():
    """Guarda de REGRESSAO na fonte: o build nao pode voltar a fixar o valor.
    (Nao da p/ importar o modulo sem FreeCAD, entao lemos a AST.)"""
    arv = ast.parse(open(BUILD_SRC, encoding="utf-8").read())
    globais = {t.id for n in arv.body if isinstance(n, ast.Assign)
               for t in n.targets if isinstance(t, ast.Name)}
    assert "N_TERCA" in globais, "N_TERCA deve ser global (configuravel pelo calc)"
    # dentro das funcoes, n_terca so pode receber N_TERCA - nunca um literal
    for no in ast.walk(arv):
        if isinstance(no, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "n_terca" for t in no.targets):
            assert isinstance(no.value, ast.Name) and no.value.id == "N_TERCA", (
                "n_terca atribuido com valor fixo na linha %d - deve vir de N_TERCA"
                % no.lineno)


def test_configurar_aceita_n_terca():
    """A assinatura de configurar() precisa expor o parametro."""
    arv = ast.parse(open(BUILD_SRC, encoding="utf-8").read())
    cfg = next(n for n in arv.body
               if isinstance(n, ast.FunctionDef) and n.name == "configurar")
    nomes = [a.arg for a in cfg.args.args] + [a.arg for a in cfg.args.kwonlyargs]
    assert "n_terca" in nomes


def test_espacamento_do_calc_respeita_vao_max_da_telha():
    """COERENCIA FISICA (o que o bug violava): com o n_terca do calc o vao da
    telha cabe no vao_max; com o 3 hardcoded, NAO cabe. Numeros da amostra."""
    import math
    span, eave, ridge = 20.0, 8.0, 9.5
    w_agua = math.hypot(span / 2.0, ridge - eave)
    vao_max = 2.142                      # gate7-telha.txt da amostra
    assert w_agua / 5 <= vao_max         # n_terca do calc: passa
    assert w_agua / 3 > vao_max          # o antigo hardcoded: NAO passa
