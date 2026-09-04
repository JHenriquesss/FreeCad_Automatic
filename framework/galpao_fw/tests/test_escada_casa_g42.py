# ============================================================================
# test_escada_casa_g42.py - G42: A ESCADA DA CASA DESCE AOS PILARES.
# Gemeo do G38 no edificio: estrutura_casa.py dimensionava a escada DEPOIS da
# descida (linhas 505-512), dava o gate na 590, devolvia na 602, e a reacao nao
# chegava a pilar nenhum. O verifica_fechamento da casa tambem nao pegava, pelo
# mesmo motivo - fechava o que foi incluido. Mesmo remedio: dimensionar antes,
# realimentar a descida, e o fechamento conferir contra a carga declarada.
# Trava a transicao nos dois sentidos: sem descida o N_base nao pode subir, e
# sem largura a carga e INDEFINIDA (reprova), nunca zero.
# ============================================================================
"""Guarda G42: escada da casa desce aos pilares e fechamento pega."""

import copy
import os
import pathlib
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = pathlib.Path(os.path.dirname(HERE))
if str(GALPAO) not in sys.path:
    sys.path.insert(0, str(GALPAO))

import estrutura_casa as ec
import varredura_descoberta as vd


def _spec(**kw):
    base = {
        "geometria": {"vaos_x": [3.5, 3.5, 3.4], "vaos_y": [4.0, 4.0],
                      "pe_direito": 2.7},
        "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"},
                       {"nome": "Terreo", "uso": "residencial_dormitorio"}],
        "laje": {"h": 0.10, "revestimento_kN_m2": 1.0},
        "viga": {"b": 0.20, "h": 0.45},
        "materiais": {"fck": 25e3, "fyk": 500e3},
    }
    base.update(copy.deepcopy(kw))
    return base


def _escada():
    return {"desnivel": 1.35, "largura": 1.20,
            "uso": "escada_residencial_comum", "h_laje": 0.08}


def test_escada_desce_aos_pilares():
    """A carga que some: com escada o N_base tem de SUBIR exatamente o peso dela."""
    sem = ec.rodar(_spec())
    com = ec.rodar(_spec(escada=_escada()))
    g = com["gates"]["escada"]
    assert g["desceu_aos_pilares"] is True, g
    assert com["escada_descida"] is not None
    total = g["W_g_por_pav_kN"] + g["W_q_por_pav_kN"]
    assert total > 0
    esperado_total = com["n_pavimentos"] * total
    assert com["gates"]["fechamento_carga"]["escada_total_kN"] == pytest.approx(
        esperado_total, abs=0.01)
    soma_sem = sum(sem["N_fundacao_k"].values())
    soma_com = sum(com["N_fundacao_k"].values())
    assert soma_com == pytest.approx(soma_sem + esperado_total, abs=0.1), \
        "escada %.2f kN nao chegou a fundacao (%.2f -> %.2f)" % (
            esperado_total, soma_sem, soma_com)
    assert com["N_base_max_k"] > sem["N_base_max_k"]
    # e a fundacao recebeu o numero somado (pilar + escada + baldrame=0 aqui)
    for nome in com["descida"]["pilares"]:
        assert com["N_fundacao_k"][nome] == pytest.approx(
            com["descida"]["pilares"][nome]["N_base_k"], abs=0.02)


def test_fechamento_confere_contra_carga_declarada():
    """O fechamento antigo fechava o que foi incluido; agora confere a base bruta
    contra a carga declarada + escada."""
    com = ec.rodar(_spec(escada=_escada()))
    f = com["gates"]["fechamento_carga"]
    assert f["OK"] and f["escada_erro"] is None
    assert f["erro_total"] <= 0.02
    assert f["N_desc_total_k"] == pytest.approx(f["esperado_total_k"], rel=0.02)
    # 2 pavimentos de usos distintos: o esperado total empilha ambos + escada,
    # logo e' MAIOR que o 'esperado' de um so pavimento-tipo (o gate antigo).
    assert f["esperado_total_k"] > f["esperado"]
    assert f["esperado_total_k"] == pytest.approx(
        f["N_desc_total_k"], abs=0.05)
    # e o acrescimo sobre a casa sem escada e' exatamente o peso da escada.
    sem = ec.rodar(_spec())
    f_sem = sem["gates"]["fechamento_carga"]
    assert f["esperado_total_k"] == pytest.approx(
        f_sem["esperado_total_k"] + f["escada_total_kN"], abs=0.5)


def test_escada_sem_largura_reprova_em_vez_de_zerar():
    """Sem largura a reacao e INDEFINIDA, nao zero: reprova o fechamento e o ATENDE."""
    spec = _spec(escada={"desnivel": 1.35, "uso": "escada_residencial_comum",
                         "h_laje": 0.08})
    r = ec.rodar(spec)
    assert r["gates"]["escada"]["desceu_aos_pilares"] is False
    assert "largura" in (r["gates"]["escada"]["erro"] or "")
    assert r["gates"]["fechamento_carga"]["OK"] is False
    assert "fechamento_carga" in r["reprovados"]
    assert r["ATENDE"] is False


def test_apoios_declarados_concentram_nos_pilares_nomeados():
    """Com 'apoios', so os pilares nomeados recebem a escada; os demais nao mexem."""
    apoios = ["P11", "P41"]
    sem = ec.rodar(_spec())
    com = ec.rodar(_spec(escada=dict(_escada(), apoios=apoios)))
    assert com["gates"]["escada"]["distribuicao"].startswith("apoios declarados")
    assert sorted(com["escada_descida"]["pilares"]) == sorted(apoios)
    for nome in sem["descida"]["pilares"]:
        d_sem = sem["descida"]["pilares"][nome]["N_base_k"]
        d_com = com["descida"]["pilares"][nome]["N_base_k"]
        if nome in apoios:
            assert d_com > d_sem, nome
        else:
            assert d_com == pytest.approx(d_sem, abs=1e-9), nome


def test_varredura_casa_limpa_e_baseline_zerada():
    """A casa saiu da baseline do G40: r_escada/stair alcancam verificacao."""
    casa = vd.descobrir_no_arquivo(GALPAO / "estrutura_casa.py")
    assert not any(d["variavel"] in ("r_escada", "stair") for d in casa), \
        "G42 reabriu em silencio: %r" % (casa,)
    assert vd.chaves_varridas() == [], \
        "baseline deveria estar zerada apos o G42: %r" % (vd.chaves_varridas(),)
