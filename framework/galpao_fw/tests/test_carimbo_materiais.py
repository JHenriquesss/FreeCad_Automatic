# ============================================================================
# test_carimbo_materiais.py - a PRANCHA nao pode declarar material diferente do
# que o projeto especificou. O desenho vai para a OBRA.
#
# BUG: `_carimbo` imprimia "ACO MR250 / CONCRETO fck 25 MPa" LITERAL nas 13
# pranchas, e a nota tecnica 4 dizia "Concreto fck 25 MPa. Cobrimento 5 cm"
# LITERAL. fck e cobrimento SAO campos do spec (validar exige > 0) e alimentam o
# calculo da fundacao. Um projeto com fck 40 / cobrimento 7,5 cm (classe de
# agressividade mais severa, NBR 6118) recebia prancha mandando executar 25 MPa e
# 5 cm - contra-seguranca de DURABILIDADE, e o cfg nem carregava os valores.
#
# Terceira superficie do mesmo padrao (calc decide -> entregavel nao ve):
# n_terca (3D), calha/condutor (3D), materiais (2D).
# ============================================================================
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import techdraw_exec as TD

SPEC_JSON = os.path.join(GALPAO, "spec_amostra_engenheiro.json")


@pytest.fixture
def spec():
    with open(SPEC_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def _carimbo_de(spec):
    cfg = TD.config_de_spec(spec, "x", "y")
    return TD._carimbo(cfg, "T", "PE-01", "1:50", "01/13"), cfg


def test_carimbo_segue_o_fck_do_projeto(spec):
    s = copy.deepcopy(spec)
    s["fundacao"]["fck"] = 40e3
    car, _ = _carimbo_de(s)
    assert "40 MPa" in car["part_material"]
    assert "25 MPa" not in car["part_material"]


def test_carimbo_da_amostra_intacto(spec):
    """O caso base (fck 25) continua escrevendo o mesmo texto de antes."""
    car, _ = _carimbo_de(spec)
    assert car["part_material"] == "ACO MR250 / CONCRETO fck 25 MPa"


@pytest.mark.parametrize("fy,nome", [(250, "MR250"), (345, "A572 G50"),
                                     (300, "AR300")])
def test_nome_do_aco_por_fy(fy, nome):
    assert TD._ACO_POR_FY[fy] == nome


def test_aco_fora_da_tabela_nao_inventa_designacao():
    """fy sem nome comercial conhecido -> declara o valor, nao um nome errado."""
    mat = TD._materiais_de_spec({"estrutura": {"aco_fy": 420e3}, "fundacao": {}})
    assert mat["aco"] == "fy=420 MPa"


def test_cobrimento_do_projeto_vai_para_a_nota(spec):
    """Cobrimento e DURABILIDADE: a nota nao pode fixar 5 cm."""
    s = copy.deepcopy(spec)
    s["fundacao"]["cobrimento"] = 0.075
    mat = TD._materiais_de_spec(s)
    assert mat["cobrimento_cm"] == 7.5


def test_armadura_segue_o_fyk(spec):
    s = copy.deepcopy(spec)
    s["fundacao"]["fyk"] = 600e3
    mat = TD._materiais_de_spec(s)
    assert mat["fyk_MPa"] == 600          # -> "CA-60" na nota 3


def test_sem_fck_a_nota_remete_ao_memorial_em_vez_de_mentir():
    """Sem o dado, omitir e correto; imprimir 25 MPa fixo nao e."""
    mat = TD._materiais_de_spec({"fundacao": {}})
    assert mat["fck_MPa"] is None
    assert "fck" not in TD._txt_material(mat)


def test_cfg_carrega_materiais(spec):
    _, cfg = _carimbo_de(spec)
    assert cfg["materiais"]["fck_MPa"] == 25
    assert cfg["materiais"]["cobrimento_cm"] == 5.0
