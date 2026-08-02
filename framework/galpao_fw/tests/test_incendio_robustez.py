"""Harness de ROBUSTEZ dos verticais novos: SEGURANCA CONTRA INCENDIO (NBR 10898/
16820/17240/10897) e os complementares ILUMINACAO EXTERNA (NBR 5101) e CLIMATIZACAO
(NBR 16401). Varredura adversarial de galpoes variados (minusculo, gigante, teto
alto, viga profunda, risco extra, sem leiaute) + invariantes (gate booleano, sem
crash, contagens nao-negativas, monotonicidade, reserva cresce com o risco) + entrada
invalida vira ValueError limpo (nao ZeroDivisionError). Tudo PURO -> CI."""
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_seguranca_incendio as gsi
import iluminacao_externa_nbr5101 as ie
import climatizacao_nbr16401 as cl
import deteccao_alarme_nbr17240 as da
import iluminacao_emergencia_nbr10898 as iem
import proteccao_sprinklers_nbr10897 as sp


# --------------------------------------------------------------------------
#  1) VERTICAL DE INCENDIO - varredura de galpoes
# --------------------------------------------------------------------------
def _incendio(C, L, H, **kw):
    spec = {"geometria": {"L": C, "W": L, "H": H},
            "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
            "deteccao": {"viga_m": kw.get("viga_m", 0.0)}}
    if kw.get("sprinklers"):
        spec["sprinklers"] = kw["sprinklers"]
    return gsi.rodar(spec)


_CENARIOS_INCENDIO = [
    ("minusculo",    6.0, 5.0, 3.0, {}),
    ("tipico",       40.0, 20.0, 6.0, {"sprinklers": {"altura_estoque_m": 3.0}}),
    ("gigante",      120.0, 60.0, 9.0, {"sprinklers": {"altura_estoque_m": 3.5}}),
    ("teto_alto",    50.0, 30.0, 12.0, {}),                 # -> detector linear
    ("viga_profunda", 40.0, 20.0, 6.0, {"viga_m": 0.70}),   # cobertura 40,5 m2
    ("comprido",     200.0, 12.0, 7.0, {}),
    ("risco_extra",  40.0, 20.0, 6.0, {"sprinklers": {"tipo": "extra"}}),
]


@pytest.mark.parametrize("nome,C,L,H,kw", _CENARIOS_INCENDIO)
def test_incendio_nao_quebra_e_invariantes(nome, C, L, H, kw):
    r = _incendio(C, L, H, **kw)
    # todo gate tem OK booleano e ATENDE booleano
    for k, g in r["gates"].items():
        assert isinstance(g.get("OK"), bool), (nome, k, g)
    assert isinstance(r["ATENDE"], bool), nome
    g = r["gates"]
    # contagens fisicas nunca negativas
    assert g["iluminacao_emergencia"]["N_aclaramento"] >= 1
    assert g["sinalizacao"]["N_placas"] >= 1
    assert g["deteccao_alarme"]["N_detectores"] >= 1
    # autonomias/comutacao dentro da norma (2 h ; <= 2 s bloco)
    assert g["iluminacao_emergencia"]["autonomia_h"] == 2.0
    assert g["iluminacao_emergencia"]["comutacao_max_s"] <= 5.0
    assert g["deteccao_alarme"]["tensao_Vcc"] == 24.0


def test_teto_alto_vira_detector_linear():
    r = _incendio(50.0, 30.0, 12.0)
    assert r["gates"]["deteccao_alarme"]["tipo_detector"] == "linear"
    r2 = _incendio(50.0, 30.0, 6.0)
    assert r2["gates"]["deteccao_alarme"]["tipo_detector"] == "pontual"


def test_detectores_monotonicos_na_area():
    # dobrar a area nao pode reduzir o numero de detectores pontuais
    n1 = da.numero_detectores_pontuais(400.0, 6.0)
    n2 = da.numero_detectores_pontuais(800.0, 6.0)
    assert n2 >= n1
    # viga mais profunda -> cobertura menor -> mais detectores
    assert da.numero_detectores_pontuais(800.0, 6.0, 0.70) >= da.numero_detectores_pontuais(800.0, 6.0)


def test_reserva_cresce_com_o_risco():
    base = {"C": 40.0, "L": 20.0}
    leve = sp.dimensiona_sprinklers(dict(base, tipo="leve"))
    ordII = sp.dimensiona_sprinklers(dict(base, altura_estoque_m=3.0))
    extra = sp.dimensiona_sprinklers(dict(base, tipo="extra"))
    assert leve["reserva_incendio_m3"] <= ordII["reserva_incendio_m3"] <= extra["reserva_incendio_m3"]


def test_sprinklers_estoque_alto_recusa_sem_inventar():
    # estoque > 3,7 m -> area de armazenamento (NBR 13792, fora do escopo) -> ValueError
    with pytest.raises(ValueError):
        sp.dimensiona_sprinklers({"C": 40.0, "L": 20.0, "altura_estoque_m": 6.0})


def test_balizamento_galpao_usa_4m():
    r = _incendio(40.0, 20.0, 6.0)
    assert r["gates"]["iluminacao_emergencia"]["N_balizamento"] >= 2
    # grande ambiente -> espacamento 4 m (mais pontos que 15 m)
    assert iem.numero_balizamento(120.0, True) > iem.numero_balizamento(120.0, False)


# --------------------------------------------------------------------------
#  2) ILUMINACAO EXTERNA (NBR 5101) - varredura
# --------------------------------------------------------------------------
_LUMINARIA = {"fluxo_lm": 15000.0, "P_W": 100.0}
_CENARIOS_EXT = [
    ("estac_estreita", 100.0, 6.0, 8.0, "estacionamento"),
    ("patio_largo",    80.0, 40.0, 12.0, "patio_manobra"),
    ("via_longa",      500.0, 8.0, 10.0, "via_trafego"),
    ("deposito",       60.0, 30.0, 8.0, "deposito_ar_livre"),
]


@pytest.mark.parametrize("nome,comp,Lp,H,tipo", _CENARIOS_EXT)
def test_iluminacao_externa_nao_quebra(nome, comp, Lp, H, tipo):
    r = ie.dimensiona_iluminacao_externa({"comprimento_m": comp, "Lp": Lp, "H": H,
                                          "area_tipo": tipo, "luminaria": _LUMINARIA})
    assert isinstance(r["OK"], bool)
    assert r["N_postes"] >= 2 and r["S_m"] > 0
    assert r["S_m"] <= r["S_max_m"] + 1e-9              # nunca ultrapassa 5*H
    assert r["Em_real_lux"] >= r["Em_lux"] - 1e-6 or not r["OK"]   # atende o alvo (ou reprova)


def test_iluminacao_externa_area_desconhecida_e_Lp_zero():
    with pytest.raises(ValueError):
        ie.dimensiona_iluminacao_externa({"comprimento_m": 100.0, "Lp": 8.0, "H": 10.0,
                                          "area_tipo": "inexistente"})
    # Lp <= 0 -> ValueError limpo (nao ZeroDivisionError)
    with pytest.raises(ValueError):
        ie.dimensiona_iluminacao_externa({"comprimento_m": 100.0, "Lp": 0.0, "H": 10.0,
                                          "area_tipo": "estacionamento"})


def test_espacamento_postes_respeita_faixa_3H_5H():
    for H in (4.0, 8.0, 12.0):
        S = ie.espacamento_postes(H)
        assert 3.0 * H <= S <= 5.0 * H


# --------------------------------------------------------------------------
#  3) CLIMATIZACAO (NBR 16401) - varredura
# --------------------------------------------------------------------------
_CENARIOS_CLIMA = [
    ("galpao_peq",   {"area_m2": 200.0, "tipo": "galpao"}),
    ("galpao_grande", {"area_m2": 5000.0, "tipo": "galpao"}),
    ("escritorio",   {"area_m2": 100.0, "tipo": "escritorio"}),
    ("detalhado",    {"area_m2": 300.0, "tipo": "galpao", "metodo": "detalhado",
                      "n_pessoas": 20, "envoltoria": [{"U": 2.5, "A": 500.0, "dT": 8.0}],
                      "P_iluminacao_W": 3000.0, "P_equipamentos_W": 5000.0}),
]


@pytest.mark.parametrize("nome,caso", _CENARIOS_CLIMA)
def test_climatizacao_nao_quebra(nome, caso):
    r = cl.dimensiona_climatizacao(caso)
    assert isinstance(r["OK"], bool)
    assert r["capacidade_TR"] > 0 and r["capacidade_kW"] > 0
    # potencia eletrica < capacidade termica (COP > 1) e coerente com o COP
    assert r["potencia_eletrica_kW"] < r["capacidade_kW"]
    assert abs(r["potencia_eletrica_kW"] - r["capacidade_kW"] / r["COP"]) < 0.01
    assert r["vazao_ar_exterior_m3h"] > 0


def test_climatizacao_capacidade_cresce_com_area():
    a = cl.dimensiona_climatizacao({"area_m2": 200.0, "tipo": "galpao"})
    b = cl.dimensiona_climatizacao({"area_m2": 2000.0, "tipo": "galpao"})
    assert b["capacidade_TR"] > a["capacidade_TR"]


def test_climatizacao_COP_invalido_e_tipo_desconhecido():
    # COP <= 0 -> ValueError limpo (nao ZeroDivisionError)
    with pytest.raises(ValueError):
        cl.dimensiona_climatizacao({"area_m2": 800.0, "tipo": "galpao", "COP": 0.0})
    # tipo sem estimativa tabelada -> ValueError
    with pytest.raises(ValueError):
        cl.dimensiona_climatizacao({"area_m2": 800.0, "tipo": "inexistente"})


def test_selftests_modulos():
    gsi._selftest()
    ie._selftest()
    cl._selftest()
    da._selftest()
    iem._selftest()
    sp._selftest()
