# ============================================================================
# test_viga_rolamento_3d.py - a VIGA DE ROLAMENTO desenhada tem que ser a
# verificada pelo calculo.
#
# ULTIMO caso da varredura "o calc decide, o 3D nao ve" (n_terca #29, calha #30,
# materiais no carimbo #31). `VR_SEC = (500,250,8,16)` era FIXO no build_galpao -
# espelho do VS500 de REFERENCIA do ponte_rolante.py. O spec pode informar
# `ponte.perfil_viga` (catalogo do fabricante) e o calculo verifica ESSA viga
# (`analisa` -> verifica_viga_rolamento com fadiga Anexo K + flecha), mas o
# modelo, a prancha e o takeoff mostravam sempre a viga de referencia.
#
# A amostra nao tem ponte, entao o caminho da ponte nao tinha cobertura no 3D:
# este arquivo tambem serve de fixture do caso COM ponte.
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

# Viga de catalogo DIFERENTE da VS500 de referencia (d 600 x bf 300 x tw 10 x tf 19)
# - proposital: com a de referencia o teste passaria mesmo sem o fix.
VIGA_CAT = {"A": 120e-4, "Ix": 60000e-8, "Iy": 2600e-8, "ry": 0.047,
            "Zx": 2300e-6, "Wx": 2050e-6, "Zy": 360e-6, "Wy": 240e-6,
            "d": 0.600, "bf": 0.300, "tf": 0.019, "tw": 0.010,
            "_fonte": "A CONFIRMAR (catalogo do fabricante)"}

# Dados do FABRICANTE (Ask-Do-Not-Invent) - valores de exemplo, A CONFIRMAR.
PONTE = {"Q": 100.0, "peso_ponte": 60.0, "peso_trole": 15.0, "vao_ponte": 19.0,
         "aprox_min": 1.0, "n_rodas_lado": 2, "n_rodas_motoras": 1, "phi": 1.10,
         "frac_lateral": 0.10, "frac_long": 0.10, "vao_viga": 5.7,
         "d_rodas": 3.0, "Hvr": 6.0}


@pytest.fixture
def spec_ponte():
    with open(SPEC_JSON, encoding="utf-8") as fh:
        s = json.load(fh)
    s["ponte"] = copy.deepcopy(PONTE)
    return s


class _FakeSrv:
    enviado = None

    def __init__(self, host):
        pass

    def execute(self, src):
        _FakeSrv.enviado = src
        return {"success": True, "result": {"elementos": 0}}


def test_spec_com_ponte_valida(spec_ponte):
    """Fixture do caminho COM ponte (a amostra nao tem)."""
    assert PS.validar(spec_ponte)["ok"] is True


def test_mapper_leva_o_perfil_do_catalogo(spec_ponte):
    spec_ponte["ponte"]["perfil_viga"] = VIGA_CAT
    bk = PS.to_build_kwargs(spec_ponte)
    assert bk["ponte_modelo"]["perfil_viga"] == [600.0, 300.0, 10.0, 19.0]


def test_sem_perfil_no_spec_nao_injeta(spec_ponte):
    """Back-compat: sem perfil informado o build fica no VS500 de referencia."""
    bk = PS.to_build_kwargs(spec_ponte)
    assert "perfil_viga" not in bk["ponte_modelo"]


def test_perfil_incompleto_e_ignorado(spec_ponte):
    """Dict sem d/bf/tw/tf nao pode virar uma secao com None (lixo no sweep)."""
    spec_ponte["ponte"]["perfil_viga"] = {"d": 0.6, "bf": 0.3}
    bk = PS.to_build_kwargs(spec_ponte)
    assert "perfil_viga" not in bk["ponte_modelo"]


def test_sem_ponte_nao_ha_ponte_modelo(spec_ponte):
    spec_ponte["ponte"] = None
    assert PS.to_build_kwargs(spec_ponte)["ponte_modelo"] is None


def test_perfil_chega_ao_build_3d(monkeypatch, spec_ponte):
    import xmlrpc.client
    spec_ponte["ponte"]["perfil_viga"] = VIGA_CAT
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", _FakeSrv)
    RP.montar_modelo(spec_ponte, GALPAO, "t")
    assert "'perfil_viga': [600.0, 300.0, 10.0, 19.0]" in _FakeSrv.enviado


def test_vr_sec_configuravel_e_resetado():
    """VR_SEC tem que ser global de configurar E de reset - sem o reset, um 2o
    projeto na mesma sessao do FreeCAD herda a viga do 1o (armadilha do _CFG)."""
    arv = ast.parse(open(BUILD_SRC, encoding="utf-8").read())
    fn = {n.name: n for n in arv.body if isinstance(n, ast.FunctionDef)}
    for alvo in ("configurar", "reset"):
        decl = {nome for n in ast.walk(fn[alvo]) if isinstance(n, ast.Global)
                for nome in n.names}
        assert "VR_SEC" in decl, "%s nao declara VR_SEC" % alvo
    atrib = {t.id for n in ast.walk(fn["reset"]) if isinstance(n, ast.Assign)
             for t in n.targets if isinstance(t, ast.Name)}
    assert "VR_SEC" in atrib, "reset() nao restaura VR_SEC"
