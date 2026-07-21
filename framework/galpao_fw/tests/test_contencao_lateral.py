# ============================================================================
# test_contencao_lateral.py - verificacao da PECA da mao-francesa
# (NBR 8800 4.11.3.4 + 5.3.2 + 5.3.4.1).
#
# CONTEXTO: `mao_francesa.py` calcula so o ESPACAMENTO (inverte a interacao
# flexo-compressao -> Lb_max -> stride). Decide ONDE por o braco e nunca O QUE
# por: nao computa Fbr,Sd nem Sbr,Sd e nao verifica secao nenhuma. O modelo
# desenhava barra redonda D16, que so trabalha a TRACAO.
#
# A norma exige os DOIS sentidos (Fakury, Cap. 5, Fig. 5.22, literal): "a forca
# axial solicitante nas contencoes laterais [...] deve ser considerada [...] COMO
# DE TRACAO E DE COMPRESSAO, pois o movimento lateral desses elementos pode se
# dar para um lado ou para o lado oposto".
#
# ARMADILHA GUARDADA AQUI: o item VIZINHO 4.11.3.3 (contencoes RELATIVAS) usa
# 0,008 e 4; o 4.11.3.4 (NODAIS) usa 0,02 e 10. A mao-francesa trava um PONTO ->
# e NODAL. Trocar os itens subdimensiona por 2,5x.
# ============================================================================
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import contencao_lateral as CL


# ---- 4.11.3.4: os coeficientes -------------------------------------------
def test_coeficientes_do_item_nodal():
    """Fbr = 0,02.Msd.Cd/h0 ; Sbr = 10.Msd.Cd.gamma_r/(Lbb.h0)."""
    F, S = CL.requisitos_nodal(Msd=100.0, h0=0.5, Lbb=4.0)
    assert F == pytest.approx(0.02 * 100.0 / 0.5)
    assert S == pytest.approx(10.0 * 100.0 * 1.35 / (4.0 * 0.5))


def test_nao_confundir_com_a_contencao_relativa():
    """4.11.3.3 usa 0,008 e 4 - exatamente 2,5x menor nos dois. Usar o item
    errado subdimensiona a contencao."""
    n = CL.requisitos_nodal(100.0, 0.5, 4.0)
    r = CL.requisitos_relativa(100.0, 0.5, 4.0)
    assert n[0] / r[0] == pytest.approx(2.5)
    assert n[1] / r[1] == pytest.approx(2.5)


def test_gamma_r_da_norma():
    """4.11.3.3: 'gamma_r e um coeficiente de ponderacao da rigidez, igual a 1,35'."""
    assert CL.GAMMA_R == 1.35


def test_Cd_dobra_os_requisitos():
    """Cd=2,00 nas vizinhancas do ponto de inflexao (curvatura reversa)."""
    a = CL.requisitos_nodal(100.0, 0.5, 4.0, Cd=1.0)
    b = CL.requisitos_nodal(100.0, 0.5, 4.0, Cd=2.0)
    assert b[0] == pytest.approx(2 * a[0])
    assert b[1] == pytest.approx(2 * a[1])


def test_h0_e_Lbb_invalidos():
    for kw in ({"h0": 0.0}, {"Lbb": 0.0}, {"h0": -1.0}):
        p = {"Msd": 100.0, "h0": 0.5, "Lbb": 4.0}
        p.update(kw)
        with pytest.raises(ValueError):
            CL.requisitos_nodal(**p)


# ---- secao / esbeltez -----------------------------------------------------
def test_barra_redonda_raio_de_giracao():
    """Secao cheia: I = pi.d^4/64 e A = pi.d^2/4 -> r = d/4."""
    s = CL.secao_barra_redonda(0.016)
    assert s["r"] == pytest.approx(0.004)
    assert s["A"] == pytest.approx(math.pi * 0.016 ** 2 / 4)
    assert s["Q"] == 1.0        # sem elemento de chapa a que o Anexo F se aplique


def test_limite_de_esbeltez_da_norma():
    """5.3.4.1: 'nao deve ser superior a 200' (barras COMPRIMIDAS)."""
    assert CL.ESBELTEZ_MAX == 200.0


# ---- o caso real: a barra D16 que o modelo desenhava -----------------------
def _caso_d16():
    """L do braco MEDIDO no modelo da amostra: dX=dZ=670,6 mm -> 948,4 mm a 45."""
    return CL.verifica_braco(Msd=61.3, h0=0.1615, Lbb=3.35, L_braco=0.9484,
                             ang_graus=45.0, sec=CL.secao_barra_redonda(0.016),
                             fy=250e3)


def test_d16_reprova_por_esbeltez():
    r = _caso_d16()
    assert r["esbeltez"] == pytest.approx(0.9484 / 0.004, rel=1e-6)
    assert r["esbeltez"] > 200
    assert not r["ok_esbeltez"]


def test_d16_reprova_tambem_por_resistencia():
    """Nao e so a esbeltez: a barra resiste a METADE da forca solicitante."""
    r = _caso_d16()
    assert not r["ok_resistencia"]
    assert r["N_braco"] > 1.5 * r["Nc_Rd"]


def test_d16_reprova_no_total_e_diz_por_que():
    r = _caso_d16()
    assert not r["ok"]
    assert "5.3.4.1" in r["motivo"] and "5.3.2" in r["motivo"]


def test_forca_do_braco_corrigida_pelo_angulo():
    """Fakury: 'Se uma contencao formar um angulo diferente de 90 graus com o
    elemento travado, sua forca solicitante precisa ser ajustada para o angulo'."""
    r = _caso_d16()
    assert r["N_braco"] == pytest.approx(r["Fbr_Sd"] / math.cos(math.radians(45.0)))


def test_rigidez_util_cai_com_o_cosseno_ao_quadrado():
    r = _caso_d16()
    esperado = (CL.E * r_area(0.016) / 0.9484) * math.cos(math.radians(45.0)) ** 2
    assert r["S_braco"] == pytest.approx(esperado)


def r_area(d):
    return math.pi * d ** 2 / 4.0


def test_braco_perpendicular_a_forca_nao_contem():
    with pytest.raises(ValueError):
        CL.verifica_braco(61.3, 0.1615, 3.35, 0.9484, 90.0,
                          CL.secao_barra_redonda(0.016), 250e3)


def test_secao_generosa_atende():
    """Contraprova: com area e raio de giracao suficientes o veredito vira ATENDE
    - o modulo nao esta simplesmente reprovando tudo."""
    sec = {"A": 20e-4, "r": 0.020, "Q": 1.0, "nome": "generosa"}
    r = CL.verifica_braco(61.3, 0.1615, 3.35, 0.9484, 45.0, sec, 250e3)
    assert r["ok"], r["motivo"]


def test_relatorio_declara_reforco_exigido():
    """Regra do projeto: quando falta capacidade o veredito e NAO ATENDE +
    reforco exigido - nunca 'atende com reforco'."""
    txt = CL.relatorio_pt(_caso_d16())
    assert "NAO ATENDE" in txt and "REFORCO EXIGIDO" in txt
    assert "atende com reforco" not in txt.lower()


def test_selftest_do_modulo():
    CL._selftest()
