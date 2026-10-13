# ============================================================================
# test_tanque_base.py - GEOMETRIA, CAPACIDADE E MASSAS DO TANQUE-BASE.
# Os valores esperados sao contas feitas a mao a partir das dimensoes do PDF
# REV.01, nao a saida do modulo copiada.
# ============================================================================
"""Tanque-base integral para conteiner 20 pes: primeira fatia."""

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tanque_base as TB


def test_volume_bruto_e_niveis():
    cap = TB.capacidade(TB.SPEC_REV01)
    # 5540,5 x 2270,5 x 538,9 mm
    assert cap["volume_bruto_m3"] == pytest.approx(5.5405 * 2.2705 * 0.5389, rel=1e-9)
    assert cap["volume_bruto_m3"] == pytest.approx(6.779, abs=0.001)
    n = cap["niveis"]["alarme_alto"]
    assert n["volume_m3"] == pytest.approx(5.423, abs=0.001)
    assert n["lamina_mm"] == pytest.approx(431.12, abs=0.01)


def test_pdf_declara_volume_menor_que_o_bruto():
    # o PDF fala em 6,4 a 6,6 m3 "liquidos": o bruto tem de ficar acima disso
    assert TB.capacidade(TB.SPEC_REV01)["volume_bruto_m3"] > 6.6


def test_quadro_do_pdf_nao_cabe_ao_lado_do_tanque():
    enc = TB.encaixe(TB.SPEC_REV01)
    # (2438 - 2280)/2 = 79 mm por lado, para um tubo de 100 mm de largura
    assert enc["folgas"]["lateral_por_lado_mm"] == pytest.approx(-21.0)
    # 6058 - 5550 - 400 = 108 mm para dois tubos de 100 mm
    assert enc["folgas"]["longitudinal_total_mm"] == pytest.approx(-92.0)
    # 600 - 550 = 50 mm, menos os 6 mm de flecha da base (ISO 1496-1, 5.3.4)
    assert enc["folgas"]["altura_mm"] == pytest.approx(44.0)
    assert enc["cabe"] is False


def test_encaixe_aprova_quando_ha_espaco():
    spec = copy.deepcopy(TB.SPEC_REV01)
    spec["tanque"]["larg"] = 2200.0
    spec["tanque"]["comp"] = 5400.0
    enc = TB.encaixe(spec)
    assert enc["folgas"]["lateral_por_lado_mm"] == pytest.approx(19.0)
    assert enc["cabe"] is True


def test_massas():
    m = TB.massas(TB.SPEC_REV01)
    # fundo: 5,55 x 2,28 x 0,00635 m3 x 7850
    assert m["chapas"]["fundo"] == pytest.approx(5.55 * 2.28 * 0.00635 * 7850, rel=1e-9)
    assert m["chapas"]["fundo"] == pytest.approx(630.8, abs=0.1)
    # perimetro de 16,992 m de tubo 150x100x6,35
    kg_m = TB.tubo_retangular(TB.SPEC_REV01["quadro"])["massa_kg_m"]
    assert m["tubos"]["quadro"] == pytest.approx(kg_m * 16.992, rel=1e-9)
    assert m["n_travessas"] == 9
    assert m["efluente"]["cheio"] == pytest.approx(6779, abs=1)
    assert m["efluente"]["alarme_alto"] == pytest.approx(5423, abs=1)
    assert "conteiner" in m["nao_incluido"]


def test_relatorio_lista_as_fontes_ausentes():
    r = TB.relatorio()
    assert "NAO CABE" in r
    for f in TB.FONTES_AUSENTES:
        assert f in r


def test_tubo_de_canto_vivo_bate_com_a_conta_a_mao():
    t = TB.tubo_retangular({"h": 150.0, "b": 100.0, "t": 6.35}, raio_sobre_t=0)
    # 2 x 6,35 x (250 - 12,7) = 3013,71 mm2
    assert t["A_mm2"] == pytest.approx(3013.71, abs=0.01)
    assert t["Ix_mm4"] == pytest.approx((100 * 150 ** 3 - 87.3 * 137.3 ** 3) / 12, rel=1e-12)
    assert t["Iy_mm4"] == pytest.approx((150 * 100 ** 3 - 137.3 * 87.3 ** 3) / 12, rel=1e-12)


def test_tubo_arredondado_bate_com_integracao_numerica():
    # confere a formula fechada contando celulas de uma malha de 0,05 mm
    np = pytest.importorskip("numpy")
    h, b, t = 150.0, 100.0, 6.35
    re_, ri = 3 * t, 2 * t
    passo = 0.05
    x = np.arange(-b / 2 + passo / 2, b / 2, passo)
    y = np.arange(-h / 2 + passo / 2, h / 2, passo)
    X, Y = np.meshgrid(np.abs(x), np.abs(y))

    def dentro(hh, bb, r):
        dx, dy = X - (bb / 2 - r), Y - (hh / 2 - r)
        canto = (dx > 0) & (dy > 0)
        return (X <= bb / 2) & (Y <= hh / 2) & (~canto | (dx * dx + dy * dy <= r * r))

    parede = dentro(h, b, re_) & ~dentro(h - 2 * t, b - 2 * t, ri)
    dA = passo * passo
    tubo = TB.tubo_retangular({"h": h, "b": b, "t": t})
    assert tubo["A_mm2"] == pytest.approx(parede.sum() * dA, rel=2e-3)
    assert tubo["Ix_mm4"] == pytest.approx((parede * Y * Y).sum() * dA, rel=2e-3)
    assert tubo["Iy_mm4"] == pytest.approx((parede * X * X).sum() * dA, rel=2e-3)
    # cantos arredondados tiram area: menos que o tubo de canto vivo
    assert tubo["A_mm2"] < 3013.71


def test_escoamento_do_tubo_retangular_por_grau():
    # NBR 8261:2019, Tabela 4, coluna "secao quadrada e retangular"
    assert TB.FY_TUBO_RETANGULAR == {"A": 269.0, "B": 317.0, "C": 345.0}
