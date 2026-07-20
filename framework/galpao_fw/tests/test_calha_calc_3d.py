# ============================================================================
# test_calha_calc_3d.py - a DRENAGEM desenhada tem que ser a dimensionada.
#
# MESMA FAMILIA do n_terca (test_n_terca_calc_3d): valor decidido pelo calc em
# runtime que nunca chegava ao 3D. `calhas.dimensiona` sobe uma escada de secoes
# ate drenar a vazao (+ borda livre 25% + regra de Bellei) e escolhe o diametro do
# condutor por vazao (NBR 10844), mas o build tinha CALHA_SEC=(200,300,5,5) e
# d=100 FIXOS. Na amostra: memoria diz calha 200x150, modelo/prancha/takeoff
# desenhavam 200x300 (o dobro da altura, "U300x200x5" na lista de material).
#
# Nao importa build_galpao (import FreeCAD no topo -> viraria teste 'build',
# deselecionado sem bridge). Intercepta o XMLRPC + AST, como no n_terca.
# ============================================================================
import ast
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


def test_mapper_leva_calha_dimensionada(spec):
    """O que o calc gravou em estrutura.calha_adotada tem que virar kwarg."""
    spec.setdefault("estrutura", {})["calha_adotada"] = {
        "B_mm": 200.0, "H_mm": 150.0, "condutor_mm": 100}
    bk = PS.to_build_kwargs(spec)
    assert bk["calha"] == [200.0, 150.0]
    assert bk["condutor_d"] == 100


def test_sem_calha_adotada_fica_none(spec):
    """Back-compat: sem o gate de calha, o build usa o proprio default."""
    spec.get("estrutura", {}).pop("calha_adotada", None)
    bk = PS.to_build_kwargs(spec)
    assert bk["calha"] is None and bk["condutor_d"] is None


def test_calha_chega_ao_build_3d(monkeypatch, spec):
    import xmlrpc.client
    spec.setdefault("estrutura", {})["calha_adotada"] = {
        "B_mm": 250.0, "H_mm": 200.0, "condutor_mm": 125}
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _FakeSrv)
    RP.montar_modelo(spec, GALPAO, "t")
    src = _FakeSrv.enviado
    assert "'calha': [250.0, 200.0]" in src
    assert "'condutor_d': 125" in src


def test_build_nao_tem_mais_drenagem_hardcoded():
    """REGRESSAO na fonte: condutor e bocal nao podem voltar a ser literais."""
    txt = open(BUILD_SRC, encoding="utf-8").read()
    assert "CONDUTOR_D" in txt
    # o colar do bocal tem que ser DERIVADO do condutor (um 130 fixo ficaria
    # menor que um condutor de 150 -> colar nao abraca o tubo)
    assert "CONDUTOR_D + 30.0" in txt
    arv = ast.parse(txt)
    globais = {t.id for n in arv.body if isinstance(n, ast.Assign)
               for t in n.targets if isinstance(t, ast.Name)}
    assert {"CALHA_SEC", "CONDUTOR_D"} <= globais


def test_configurar_e_reset_cobrem_a_drenagem():
    """reset() TEM que restaurar: sem isso um 2o projeto na mesma sessao do
    FreeCAD herda a calha do 1o (a armadilha do _CFG global do vento)."""
    arv = ast.parse(open(BUILD_SRC, encoding="utf-8").read())
    fn = {n.name: n for n in arv.body if isinstance(n, ast.FunctionDef)}
    cfg_args = [a.arg for a in fn["configurar"].args.args]
    assert "calha" in cfg_args and "condutor_d" in cfg_args
    for alvo in ("configurar", "reset"):
        decl = {nome for n in ast.walk(fn[alvo]) if isinstance(n, ast.Global)
                for nome in n.names}
        assert {"CALHA_SEC", "CONDUTOR_D"} <= decl, (
            "%s nao declara CALHA_SEC/CONDUTOR_D" % alvo)
    # e o reset precisa REATRIBUIR (nao so declarar global)
    atrib = {t.id for n in ast.walk(fn["reset"]) if isinstance(n, ast.Assign)
             for t in n.targets if isinstance(t, ast.Name)}
    assert {"CALHA_SEC", "CONDUTOR_D", "N_TERCA"} <= atrib


def test_altura_da_calha_e_o_indice_1():
    """Trava a ORIENTACAO: a calha e rolada 90 graus, entao CALHA_SEC[1] e a
    ALTURA. Trocar B com H aqui passaria despercebido no desenho de topo."""
    txt = open(BUILD_SRC, encoding="utf-8").read()
    assert "GUT_BOTTOM = EAVE_H - CALHA_SEC[1] / 2.0" in txt
