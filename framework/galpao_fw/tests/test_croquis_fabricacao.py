"""Prancha de CROQUIS DE FABRICACAO (PE14) - shop drawings por peca (marca)."""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "techdraw_exec.py")


def _fonte():
    return open(SRC, encoding="utf-8").read()


def _fn(src, nome):
    arv = ast.parse(src)
    for n in ast.walk(arv):
        if isinstance(n, ast.FunctionDef) and n.name == nome:
            return ast.get_source_segment(src, n)
    raise AssertionError("funcao %s nao encontrada" % nome)


def test_pr_croquis_existe():
    _fn(_fonte(), "_pr_croquis")


def test_croquis_registrada_nos_construtores():
    src = _fonte()
    exe = _fn(src, "gerar_executivo")
    assert "_pr_croquis" in exe                        # registrada no pipeline
    # recebe (doc, cfg, objs, todos) - grupo das miudezas
    assert "_pr_croquis)" in exe or "_pr_croquis]" in exe


def test_croquis_usa_marca_do_modelo():
    fn = _fn(_fonte(), "_pr_croquis")
    assert 'getattr(o, "Marca"' in fn                  # localiza a peca pela Marca
    assert "PE14_CROQUIS" in fn
    assert "_vista(" in fn                              # projeta a peca


def test_croquis_rotula_marcas_principais():
    fn = _fn(_fonte(), "_pr_croquis")
    assert '"C1"' in fn and '"V1"' in fn and '"MI1"' in fn
    assert "SOLDADA" in fn                              # nota de solda p/ misula


def test_fonte_compila():
    ast.parse(_fonte())
