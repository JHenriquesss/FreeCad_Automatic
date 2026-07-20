# ============================================================================
# test_takeoff_rotulos.py - o TAKEOFF (lista de material) descreve a peca que foi
# desenhada, nao um texto fixo.
#
# ACHADO: a coluna "perfil" do takeoff tinha strings LITERAIS. Depois do PR #30
# (calha/condutor parametrizados) a GEOMETRIA saiu certa mas a lista de compra
# continuou dizendo o antigo:
#     desenhado            takeoff dizia
#     calha 200 x 150      "U300x200x5"     (o dobro da altura)
#     condutor d150        "tubo-100x3"     (33% menor - NBR 10844 pede 150)
#     bocal d180           "tubo-130x3"
#     chumbador d32        "porca-M20"      (porca que nao entra no chumbador)
# Passou batido porque eu validei o #30 MEDINDO O MODELO, nao a lista.
#
# Nao da p/ importar build_galpao (import FreeCAD no topo -> teste 'build',
# deselecionado sem bridge). Guarda na FONTE, via AST/texto.
# ============================================================================
import ast
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

BUILD_SRC = os.path.join(GALPAO, "build_galpao.py")


@pytest.fixture(scope="module")
def src():
    return open(BUILD_SRC, encoding="utf-8").read()


@pytest.mark.parametrize("literal", [
    '"U300x200x5"',        # calha: era a secao fixa antiga
    '"tubo-100x3"',        # condutor
    '"tubo-130x3"',        # bocal
    '"porca-M20"',         # porca (o chumbador ja vinha do BASE_PLATE["db"])
    '"VS500"',             # viga de rolamento
])
def test_rotulo_nao_e_mais_literal(src, literal):
    assert literal not in src, (
        "rotulo do takeoff voltou a ser fixo (%s): a lista de compra passa a "
        "descrever peca diferente da desenhada" % literal)


@pytest.mark.parametrize("global_usado", [
    "CALHA_SEC[1]",        # altura da calha (rolada 90 -> indice 1)
    "CONDUTOR_D",
    'BASE_PLATE["db"]',
    "VR_SEC[0]",
])
def test_rotulo_deriva_do_parametro(src, global_usado):
    assert global_usado in src


def test_bocal_acompanha_o_condutor(src):
    """O colar e condutor+30 na GEOMETRIA; o rotulo tem que usar a mesma conta."""
    assert "CONDUTOR_D + 30.0" in src
    # aparece 2x: uma no desenho do tubo, outra no rotulo do takeoff
    assert src.count("CONDUTOR_D + 30.0") >= 2


def test_porca_casa_com_o_chumbador(src):
    """Chumbador e porca tem que sair do MESMO db - era o caso mais visivel
    (barra-32 com porca-M20 na mesma lista)."""
    chumb = re.search(r'"Chumbadores", "barra-%\.0f" % BASE_PLATE\["db"\]', src)
    porca = re.search(r'"Porcas", "porca-M%\.0f" % BASE_PLATE\["db"\]', src)
    nivel = re.search(r'"Porcas de nivel", "porca-M%\.0f" % BASE_PLATE\["db"\]', src)
    assert chumb and porca and nivel


def test_fonte_compila(src):
    ast.parse(src)
