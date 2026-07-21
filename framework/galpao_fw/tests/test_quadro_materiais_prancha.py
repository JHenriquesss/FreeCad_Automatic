# ============================================================================
# test_quadro_materiais_prancha.py - o QUADRO DE MATERIAIS da PE09 nao pode
# sumir em silencio.
#
# ACHADO (verificacao VISUAL da prancha, 2026-07-21): a PE09 saiu com METADE DA
# FOLHA EM BRANCO. O quadro de verificacoes estava la (com "Mao-francesa (peca)
# 3,39 REVER" na ultima linha), as notas tecnicas tambem - e o QUADRO DE
# MATERIAIS, que e o que o fabricante usa para comprar aco, simplesmente nao
# existia. A prancha se chama "QUADROS E NOTAS TECNICAS", no plural.
#
# CAUSA: `cfg["takeoff"]` vem de spec["estrutura"]["takeoff"], que SO o
# `montar_modelo` grava. Mas `rodar_executivo` e projetado para rodar SOZINHO
# sobre um FCStd ja salvo (a propria docstring diz isso) - e nesse caminho o
# quadro sumia sem nenhum sinal: `ok=True`, 13 pranchas, ZERO avisos.
#
# POR QUE A GUARDA EXISTENTE NAO PEGOU: `_cobertura` verifica se cada TIPO DE
# SOLIDO aparece em alguma prancha; um quadro de TEXTO ausente nao e solido
# nenhum. E `_aviso_prancha` so e chamado onde alguem lembrou de chamar.
#
# So apareceu porque eu ABRI o PNG e olhei. Nenhuma verificacao automatica -
# minha ou pre-existente - tinha como pegar meia folha vazia.
# ============================================================================
import ast
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import techdraw_exec as TD

SRC = os.path.join(GALPAO, "techdraw_exec.py")


@pytest.fixture(scope="module")
def src():
    return open(SRC, encoding="utf-8").read()


def _fonte_de(src, nome):
    arv = ast.parse(src)
    for n in ast.walk(arv):
        if isinstance(n, ast.FunctionDef) and n.name == nome:
            return ast.get_source_segment(src, n)
    raise AssertionError("funcao %s nao encontrada" % nome)


def test_takeoff_vazio_gera_aviso(src):
    """Silencio era o problema: ok=True e 0 avisos com meia prancha em branco."""
    fn = _fonte_de(src, "_pr_quadros")
    assert "if not tk:" in fn
    assert '_aviso_prancha("PE09_QUADROS"' in fn


def test_takeoff_vazio_imprime_o_motivo_na_prancha(src):
    """Quem recebe o PDF tem que saber que falta - nao ficar com area vazia."""
    fn = _fonte_de(src, "_pr_quadros")
    assert "NAO DISPONIVEL NESTA EXECUCAO" in fn


def test_aviso_diz_como_resolver(src):
    fn = _fonte_de(src, "_pr_quadros")
    assert "montar_modelo" in fn and "rodar_tudo" in fn


def test_o_quadro_continua_saindo_quando_ha_takeoff(src):
    """A correcao nao pode ter trocado o caminho normal pelo aviso."""
    fn = _fonte_de(src, "_pr_quadros")
    assert "if tk:" in fn
    assert '_tabela(doc, page, "Q09M"' in fn


def test_lista_de_avisos_e_exposta():
    """O aviso precisa chegar ao chamador (rodar_executivo -> avisos_prancha),
    senao continua invisivel para quem automatiza."""
    assert isinstance(TD.AVISOS_PRANCHA, list)
    assert callable(TD._aviso_prancha)


def test_fonte_compila(src):
    ast.parse(src)
