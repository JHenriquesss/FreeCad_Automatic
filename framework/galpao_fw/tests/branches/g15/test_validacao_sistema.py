"""Testes G15 - validacao de sistema contra projeto real.

Cobre: vento, Cpe, parede, equilibrio, secoes, armadura, quantitativos,
eletrica (IB/secao/quedas/demanda), hidraulica (DN/pressao), estrutura
(pilar/sapata) e o guard d*sen45. Cada teste chama o check correspondente
de validacao_sistema_g15 e assere PASS dentro da tolerancia de engenharia.

A validacao de sistema nao substitui a de nucleo (validacao.py); ela a
complementa aferindo o SISTEMA (spec->calculo->quantitativo) contra
handcalc/memo publicado, com a mesma grandeza dos dois lados.
"""
import math
import pytest
import validacao_sistema_g15 as G15


@pytest.mark.parametrize("fn", G15.CHECKS)
def test_g15_checks_pass(fn):
    nome, ok, err, det = fn()
    assert ok, f"{nome} falhou (err={err:.2%}) :: {det}"


def test_g15_todos_passam():
    ok, resultados = G15.rodar(verbose=False)
    assert ok, "Nem todos os 19 checks G15 passaram"
    assert len(resultados) == 19


def test_g15_sem_falsa_divergencia_d_sen45():
    """Guard: d vs d*sen45 sao grandezas diferentes; nunca comparar direto."""
    d = 400.0
    d_proj = d * math.sin(math.radians(45.0))
    # \"divergencia\" falsa se comparar sem converter:
    falso_err = abs(d - d_proj) / d  # 29.3%
    assert falso_err > 0.25, "Guard: d vs d*sen45 devia dar ~29% de falsa divergencia"
    # O check de G15 deve passar (ele nao compara grandezas diferentes)
    nome, ok, err, det = G15.check_armadilha_d_sen45()
    assert ok


def test_g15_quantitativo_aco_grandeza_inclinada():
    """Quantitativo usa L_rafter inclinado, nao projecao."""
    nome, ok, err, det = G15.check_quantitativo_aco_amostra()
    assert ok
    assert "INCLINADO" in det
    assert "10.112" in det  # L correto
    assert "10.0" in det    # projecao mencionada como armadilha


def test_g15_vento_define_z_cumeeira():
    nome, ok, err, det = G15.check_vento_amostra()
    assert ok
    assert "cumeeira" in det  # z=9.5 explicitado


def test_g15_carga_parede_no_baldrame():
    nome, ok, err, det = G15.check_carga_parede_amostra()
    assert ok
    assert "BALDRAME" in det
    assert "NAO carrega coluna" in det


def test_g15_eletrica_ib_monofasico():
    nome, ok, err, det = G15.check_eletrica_casa_ib()
    assert ok
    assert "S/V monofasico" in det


def test_g15_cbca_regressao_bate():
    """CBCA ja homologado: nao pode regredir."""
    nome, ok, err, det = G15.check_vento_cbca_referencia()
    assert ok, det
    assert err < 0.05  # vertical 5% / H/M 15%
