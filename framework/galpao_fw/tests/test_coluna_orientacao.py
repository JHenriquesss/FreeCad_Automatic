# ============================================================================
# test_coluna_orientacao.py - a COLUNA do portico tem que ter o EIXO FORTE no
# PLANO DO PORTICO.
#
# BUG (o mais grave da sessao 16): as colunas eram criadas com roll=0. O `_sweep`
# desenha a secao no plano local (y=largura b, z=altura h), extruda em +X e gira
# pela rotacao MINIMA que leva X a direcao da peca. Para uma coluna VERTICAL isso
# manda a altura h para o X GLOBAL (o comprimento do galpao) -> o eixo FRACO fica
# no plano do portico, enquanto o calculo 2D dimensiona com Ix (eixo forte).
# Os RAFTERS ja saiam certos (eixo no plano Y-Z) - a assimetria denunciava.
#
# Medido na amostra: coluna IPE500 saia dX=500/dY=200 (altura ao longo do
# comprimento). Ix/Iy = 22,5x: quem montasse pelo desenho teria 2.142 cm4 no
# plano do portico onde a memoria dimensionou 48.200 cm4.
#
# FONTE (NotebookLM sobre os livros do usuario): Fakury, "Dimensionamento de
# Elementos Estruturais de Aco e Mistos de Aco e Concreto", Cap. 9 secao 9.1 e
# Fig. 9.1a: "pilares de porticos rigidos planos [...] submetidos a flexao em
# RELACAO AO EIXO DE MAIOR MOMENTO DE INERCIA e a forca axial". O eixo fraco
# aponta para o comprimento, onde a estabilidade vem do CONTRAVENTAMENTO em X.
#
# build_galpao nao e importavel sem FreeCAD -> guarda na FONTE (AST).
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


def _chamadas(src, func):
    arv = ast.parse(src)
    return [n for n in ast.walk(arv)
            if isinstance(n, ast.Call) and getattr(n.func, "id", "") == func]


def _literais(call):
    """Partes literais das f-strings dos argumentos (o nome da peca)."""
    return [v.value for a in call.args if isinstance(a, ast.JoinedStr)
            for v in a.values if isinstance(v, ast.Constant)]


def test_coluna_prismatica_tem_roll_90(src):
    """i_member da coluna (nome ..._C{j}) precisa de roll=90."""
    achou = False
    for c in _chamadas(src, "i_member"):
        lit = "".join(_literais(c))
        if not re.fullmatch(r"_C\d*", lit):   # nao casar _CUMEEIRA_S etc
            continue
        achou = True
        roll = {k.arg: k.value for k in c.keywords}.get("roll")
        assert roll is not None and getattr(roll, "value", None) == 90.0, \
            "coluna prismatica sem roll=90 -> eixo fraco no plano do portico"
    assert achou, "nao encontrei a chamada que cria a coluna prismatica"


def test_coluna_tapered_tem_roll_90(src):
    achou = False
    for c in _chamadas(src, "tapered_column"):
        achou = True
        roll = {k.arg: k.value for k in c.keywords}.get("roll")
        assert roll is not None and getattr(roll, "value", None) == 90.0
    assert achou


def test_rafter_continua_sem_roll(src):
    """O rafter JA estava certo (eixo dele esta no plano Y-Z): nao pode ganhar
    roll=90 'por simetria' - isso o giraria para fora do plano."""
    for c in _chamadas(src, "i_member"):
        lit = "".join(_literais(c))
        if not re.fullmatch(r"_V\d*", lit):
            continue
        roll = {k.arg: k.value for k in c.keywords}.get("roll")
        assert roll is None or getattr(roll, "value", None) in (0, 0.0)


def test_calha_afastada_por_derivacao(src):
    """Com o eixo forte no plano, a coluna ocupa d/2 em Y (era bf/2). O GUT_Y
    fixo de 340 fazia a calha invadir a coluna. Tem que ser DERIVADO, senao volta
    a colidir no proximo perfil mais alto.

    NOTA: a formula ficou mais completa depois (a calha precisa livrar a GIRT, que
    e a peca mais externa da parede - ver test_ligacoes_pos_rotacao). Este teste
    guarda a INTENCAO (derivado da coluna, sem numero magico); a formula exata e
    verificada la, para nao travar duas vezes a mesma linha."""
    assert "GUT_Y = 340.0" not in src
    # DERIVADO da coluna (sem numero magico). O afastamento passou a usar a
    # meia-altura MAIS FUNDA no beiral (_col_d_beiral = max(COL_SEC[0], h_joelho
    # do tapered) - ver o fix de interferencia do bloco tapered).
    assert "_col_d_beiral = COL_SEC[0]" in src
    assert "GUT_Y = _col_d_beiral / 2.0" in src


def test_fonte_compila(src):
    ast.parse(src)
