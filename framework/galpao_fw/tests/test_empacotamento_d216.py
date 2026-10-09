# ============================================================================
# test_empacotamento_d216.py - O PACOTE PLANO DO MOTOR LISTA TODOS OS MODULOS
# (plano de 2026-10-08, Fase 1; D216). O pyproject nao sabe varrer a pasta: a
# lista de modulos e' escrita, e modulo novo fora dela seria instalado pela
# metade sem ninguem ver. Aqui a lista e' conferida nos dois sentidos.
# Construir e instalar a roda nao e' feito aqui (baixa dependencias); foi
# medido a mao e esta no verbete D216.
# ============================================================================
"""A lista de modulos do pyproject e' a pasta, nem mais nem menos."""

import os
import pathlib
import tomllib

GALPAO = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _pyproject():
    with open(GALPAO / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def test_lista_de_modulos_e_a_pasta_nos_dois_sentidos():
    declarados = _pyproject()["tool"]["setuptools"]["py-modules"]
    na_pasta = sorted(p.stem for p in GALPAO.glob("*.py"))
    assert sorted(set(declarados)) == declarados, "lista com repeticao ou fora de ordem"
    faltam = sorted(set(na_pasta) - set(declarados))
    sobram = sorted(set(declarados) - set(na_pasta))
    assert not faltam and not sobram, (
        "pyproject.toml fora de passo com a pasta: faltam %r, sobram %r" % (faltam, sobram))


def test_dependencias_vem_do_requirements_e_nao_de_uma_segunda_lista():
    cfg = _pyproject()
    assert cfg["project"]["dynamic"] == ["dependencies"]
    assert "dependencies" not in cfg["project"]
    arquivos = cfg["tool"]["setuptools"]["dynamic"]["dependencies"]["file"]
    assert arquivos == ["requirements.txt"] and (GALPAO / "requirements.txt").is_file()


def test_pasta_de_teste_e_de_ferramenta_nao_entram_no_pacote():
    cfg = _pyproject()["tool"]["setuptools"]
    assert "packages" not in cfg
    assert not [m for m in cfg["py-modules"] if m.startswith("test_") or m == "conftest"]
