# ============================================================================
# test_calhas_robustez.py - achados do FUZZ INTERNO dos motores (sessao 16).
#
# O fuzz mutou cada argumento de cada funcao publica de 7 modulos. Quase tudo o
# que acusou foi NaN-entra/NaN-sai em formula-folha, cuja entrada o `validar()`
# ja bloqueia -> nao acionavel. Sobraram DOIS defeitos reais no calhas:
#   1. secao_calha materializava uma LISTA de int(0,75*H_max*1000) elementos ->
#      H_max absurdo (erro de unidade) TRAVAVA o processo em vez de acusar.
#   2. area_contribuicao aceitava dimensao negativa -> vazao negativa -> a calha
#      saia com ok=True (numero sem sentido apresentado como aprovado).
# ============================================================================
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import calhas


def test_h_max_absurdo_falha_alto_e_rapido():
    """Antes: range(5, 7.5e14) -> lista gigante -> processo travado/memoria.
    Agora: ValueError imediato. O teste passar JA prova que nao trava."""
    with pytest.raises(ValueError):
        calhas.secao_calha(Q_req=500.0, H_max=1e12)


@pytest.mark.parametrize("h", [0.0, -0.5, float("inf"), float("nan")])
def test_h_max_invalido_falha_alto(h):
    with pytest.raises(ValueError):
        calhas.secao_calha(Q_req=500.0, H_max=h)


def test_h_max_em_metros_continua_funcionando():
    """A guarda nao pode estreitar a faixa util (a escada do pipeline vai ate 0,30)."""
    r = calhas.secao_calha(Q_req=500.0, B_base=0.40, H_max=0.30)
    assert r["ok"] is True
    assert 0 < r["h_agua_m"] <= 0.75 * 0.30


@pytest.mark.parametrize("comp,larg", [(-10.0, 20.0), (30.0, -20.0)])
def test_dimensao_negativa_falha_alto(comp, larg):
    """Antes devolvia area negativa com ok=True (contra-seguranca)."""
    with pytest.raises(ValueError):
        calhas.area_contribuicao(comp, larg)
    with pytest.raises(ValueError):
        calhas.dimensiona(comp, larg)


def test_caso_valido_intacto():
    """O caso do pipeline (amostra) nao muda com as guardas."""
    r = calhas.dimensiona(28.5, 10.0, I_mm_h=150.0, B_base=0.40, H_calha=0.30)
    assert r["area_contrib_m2"] == pytest.approx(285.0, rel=1e-6)
    assert r["vazao_Lmin"] > 0
    assert r["ok"] in (True, False)      # veredito existe e e booleano
