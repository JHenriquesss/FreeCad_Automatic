"""Escada multi-lance com patamar de descanso (fecha o gap C5 da auditoria).

Antes, escada.dimensiona ABORTAVA (ok:False) para desnivel > 3,2 m. Como galpao
tem pe-direito > 6 m, qualquer escada de acesso a plataforma/mezanino era reprovada
e nao gerada. Agora divide em N lances (cada <= limite_lance) com (N-1) patamares.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import escada as E


def test_lance_unico_inalterado():
    # desnivel <= 3,2 m: continua single-flight (sem 'multi')
    r = E.dimensiona(3.0, 4.5, 1.20)
    assert r.get("ok") and not r.get("multi")


def test_desnivel_alto_gera_patamar_nao_aborta():
    # 4,0 m > 3,2 m: 2 lances de 2,0 m + 1 patamar (nao aborta mais)
    r = E.dimensiona(4.0, 8.0, 1.20)
    assert r.get("ok") and r.get("multi")
    assert r["n_lances"] == 2 and r["n_patamares"] == 1
    assert abs(r["desnivel_por_lance_m"] - 2.0) < 1e-9
    assert r["desnivel_por_lance_m"] <= r["limite_lance_m"] + 1e-9
    assert r["perfil"]


def test_cada_lance_respeita_blondel():
    # a projecao do lance e DERIVADA de Blondel -> 62 <= 2e+p <= 64
    r = E.dimensiona(6.0, 20.0, 1.20)
    assert 62.0 <= r["lance"]["blondel_cm"] <= 64.0


def test_numero_de_lances_escala_com_desnivel():
    assert E.dimensiona(3.5, 20.0)["n_lances"] == 2     # 3,5/3,2 -> 2
    assert E.dimensiona(7.0, 30.0)["n_lances"] == 3     # 7/3,2 -> 3
    assert E.dimensiona(10.0, 40.0)["n_lances"] == 4    # 10/3,2 -> 4


def test_limite_lance_parametrizavel_nr18():
    # NR-18 pode exigir 2,90 m: um desnivel de 3,0 m passa a exigir patamar
    r = E.dimensiona(3.0, 8.0, 1.20, limite_lance=2.90)
    assert r.get("multi") and r["n_lances"] == 2


def test_espaco_insuficiente_sinaliza_nao_cabe():
    # geometria valida, mas nao cabe na projecao disponivel -> flag (nao inventa)
    r = E.dimensiona(6.5, 1.0, 1.20)
    assert r.get("ok") and r["espaco_suficiente"] is False
    assert r["projecao_necessaria_m"] > r["projecao_disponivel_m"]


def test_espaco_suficiente_cabe():
    r = E.dimensiona(6.5, 25.0, 1.20)
    assert r["espaco_suficiente"] is True


def test_patamar_default_igual_largura():
    r = E.dimensiona(5.0, 20.0, largura=1.50)
    assert abs(r["patamar_comprimento_m"] - 1.50) < 1e-9   # >= largura (pratica)


def test_relatorio_multi_cita_patamar_e_a_confirmar():
    txt = E.relatorio_pt(E.dimensiona(5.0, 20.0, 1.20))
    assert "PATAMAR" in txt.upper() and "A CONFIRMAR" in txt


def test_selftest_modulo():
    E._selftest()
