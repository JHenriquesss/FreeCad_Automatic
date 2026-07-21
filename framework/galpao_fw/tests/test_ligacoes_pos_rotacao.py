# ============================================================================
# test_ligacoes_pos_rotacao.py - as pecas que se referenciam a COLUNA tem que usar
# a dimensao certa depois que a coluna passou a ter a alma no plano do portico.
#
# REGRESSAO QUE EU MESMO INTRODUZI no PR #35 (roll=90 nas colunas): varios pontos
# usavam COL_SEC[1]/2 (bf/2) para deslocamento em Y, o que era CORRETO enquanto a
# coluna estava girada errada (ocupava bf em Y). Com a alma no plano do portico a
# coluna passa a ocupar d em Y, e esses pontos ficaram 150 mm fora do lugar:
#     NERVURA_BASE  85% ENTERRADA na coluna     -> 0%
#     CLIPE_GIRT    38% enterrado                -> 11%
#     girt (GOFF)   DENTRO do envelope da coluna -> encostada na face
#     ENRIJ joelho  (d, bf) trocados             -> (bf, d)
#     DOUBLER       deslocado em Y, mas a alma agora esta no plano Y-Z -> em X
#
# POR QUE PASSOU: peca de CONEXAO e EXCLUIDA do `checa_interferencia`. Eu validei o
# PR #35 pela paridade de interferencias (84=84) - uma metrica CEGA justamente para
# a classe que quebrei. So apareceu medindo VOLUME DE INTERPENETRACAO peca a peca.
#
# Efeito colateral bom: ao afastar a calha para livrar a girt, os condutores sairam
# de cima das placas de base -> o par CONDUTOR x PLACA (6 no baseline) sumiu.
# Interferencias do run: 6 -> 0.
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


def test_nervura_parte_da_face_em_d(src):
    assert "ftip = COL_SEC[0] / 2.0" in src
    assert "ftip = COL_SEC[1] / 2.0" not in src


def test_girt_encosta_na_face_em_d(src):
    assert "GOFF = COL_SEC[0] / 2.0 + UPE_LONG[0] / 2.0" in src


def test_enrijecedor_do_joelho_com_x_bf_e_y_d(src):
    """Preenche a secao entre as mesas: X = bf (largura), Y = d (altura)."""
    assert "COL_SEC[1], COL_SEC[0], 12.0," in src
    assert "COL_SEC[0], COL_SEC[1], 12.0," not in src


def test_doubler_desloca_em_X(src):
    """A alma do pilar esta no plano Y-Z: as duas chapas ficam uma de cada lado
    dela, deslocadas em X, com a extensao 'dentro da alma' em Y."""
    assert "offx = sx * (tw_col / 2.0 + t_lado / 2.0)" in src
    assert "wy = COL_SEC[0] * 0.7" in src
    assert "offy = sy * (tw_col" not in src


def test_calha_livra_a_girt_nao_so_a_coluna(src):
    """A peca mais externa da parede e a GIRT (e os tirantes nela), nao a coluna."""
    assert "GUT_Y = COL_SEC[0] / 2.0 + UPE_LONG[0] + CALHA_SEC[0] / 2.0" in src


def test_nenhum_offset_em_Y_usa_bf(src):
    """Guarda GERAL da familia: com a alma no plano do portico, qualquer meia-
    extensao da coluna em Y e COL_SEC[0]/2. Um COL_SEC[1]/2 sobrando e suspeito.
    (COL_SEC[1] sozinho continua valido como LARGURA em X - ex.: o enrijecedor.)"""
    assert not re.search(r"COL_SEC\[1\]\s*/\s*2\.0", src), (
        "sobrou meia-largura de mesa usada como extensao em Y")


def test_fonte_compila(src):
    ast.parse(src)
