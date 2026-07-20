# ============================================================================
# test_aco_classe.py - a CLASSE DE ACO e escolha do projeto e tem que chegar
# inteira (fy E fu) ao calculo, ao carimbo e ao wizard.
#
# CONTEXTO: `fy` vinha de PARAMS_REF["fy"]=250e3 e `fu` estava LITERAL (400e3) no
# rodar_galpao -> TODO projeto era dimensionado em MR250, sem o engenheiro poder
# pedir alta resistencia (encarece a estrutura; e o A572 G50 e o aco do exemplo
# CBCA que o proprio validacao.py reproduz).
#
# POR QUE (fy, fu) E NAO SO fy: fu entra na ruptura da secao liquida, no block
# shear e na pressao de contato das LIGACOES. Um aco AR350 com o fu do MR250
# daria ligacao inconsistente com o perfil.
#
# Valores conferidos no PDF (pesquisa/aço/Pfeil, Cap.1, pag 33 do PDF), NAO de
# memoria - a 1a versao desta tabela tinha um "AR300" que nao existe.
# ============================================================================
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import acos
import projeto_spec as PS
import techdraw_exec as TD

SPEC_JSON = os.path.join(GALPAO, "spec_amostra_engenheiro.json")


@pytest.fixture
def spec():
    with open(SPEC_JSON, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.parametrize("nome,fy,fu", [
    ("MR250", 250e3, 400e3),          # Pfeil: media resistencia (= ASTM A36)
    ("A572-G50", 345e3, 450e3),       # Tabela 1.1, baixa liga
    ("AR350", 350e3, 450e3),          # Pfeil: alta resistencia (ABNT)
    ("AR-COR415", 415e3, 520e3),      # Pfeil: resistente a corrosao
])
def test_propriedades_conferem_com_a_fonte(nome, fy, fu):
    assert acos.propriedades(nome) == (fy, fu)


@pytest.mark.parametrize("escrito", ["ar 350", "AR-350", "a572 g50", "A36", "mr250"])
def test_aceita_variacao_de_escrita(escrito):
    assert acos.normaliza(escrito) is not None


def test_ar300_nao_existe():
    """Guarda contra o erro que eu ja cometi: 'AR300' nao e classe ABNT."""
    assert acos.normaliza("AR300") is None
    with pytest.raises(ValueError):
        acos.propriedades("AR300")


def test_classe_desconhecida_falha_alto():
    """Nao adivinha: um aco errado muda a resistencia de TODA a estrutura."""
    with pytest.raises(ValueError):
        acos.propriedades("ACO_QUALQUER")


def test_mapper_leva_fy_e_fu(spec):
    s = copy.deepcopy(spec)
    s.setdefault("estrutura", {})["aco"] = "AR350"
    p = PS.to_rodar_params(s)
    assert p["fy"] == 350e3
    assert p["fu"] == 450e3          # o par inteiro, nao so fy


def test_default_mantem_comportamento_historico(spec):
    """Spec sem o campo (todos os projetos existentes) continua MR250."""
    s = copy.deepcopy(spec)
    s.get("estrutura", {}).pop("aco", None)
    p = PS.to_rodar_params(s)
    assert (p["fy"], p["fu"]) == (250e3, 400e3)


def test_validar_bloqueia_classe_desconhecida(spec):
    s = copy.deepcopy(spec)
    s.setdefault("estrutura", {})["aco"] = "AR300"
    campos = [f[0] for f in PS.validar(s)["faltando"]]
    assert "estrutura.aco" in campos


def test_carimbo_declara_o_aco_escolhido(spec):
    s = copy.deepcopy(spec)
    s.setdefault("estrutura", {})["aco"] = "A572-G50"
    cfg = TD.config_de_spec(s, "x", "y")
    car = TD._carimbo(cfg, "T", "PE-01", "1:50", "01/13")
    assert "A572-G50" in car["part_material"]
    assert cfg["materiais"]["fy_MPa"] == 345


def test_wizard_pergunta_o_aco():
    import wizard as WZ
    chaves = [q[0] for q in WZ.PERGUNTAS]
    assert "aco" in chaves


def test_wizard_guarda_valor_cru_para_o_validar_bloquear():
    """Typo tem que ser BLOQUEADO, nao cair calado no default."""
    import wizard as WZ
    r = {"area_lote_m2": 5000, "span": 20, "comprimento": 28.5, "eave": 8,
         "v0": 45, "sigma_solo": 200, "aco": "AR300"}
    s = WZ.construir_spec(r, "t")
    assert s["estrutura"]["aco"] == "AR300"
    assert "estrutura.aco" in [f[0] for f in PS.validar(s)["faltando"]]
