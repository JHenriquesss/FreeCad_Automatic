# ============================================================================
# test_vento_lateral_d224.py - O VENTO LATERAL NO PORTICO E OS COEFICIENTES PELA
# PROPORCAO DO GALPAO (D224). Ate' o D224 a forca das paredes entrava sem o vao
# entre porticos e com a parede de sotavento freando; nenhum teste media a
# reacao horizontal do portico.
# ============================================================================
"""Vento a 90 graus: equilibrio horizontal do portico e Tabelas 6 e 7 da NBR 6123:2023."""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import galpao_portico as gp
import vento_nbr6123 as vi


@pytest.fixture
def portico():
    gp.reset()
    vi.reset()
    gp.configurar(span=20.0, eave=8.0, ridge=9.5, bay=5.7, base_fixed=True,
                  A_col=0.0116, I_col=4.82e-4, A_raf=0.0116, I_raf=4.82e-4,
                  comprimento=28.5)
    yield
    gp.reset()
    vi.reset()


def _reacao_horizontal(cpi_key):
    apply, wr = gp._wind(cpi_key)
    _d, _mf, ix, fr = gp._run(apply)
    R = fr.reactions()
    return sum(R[3 * b] for b in ix["nBases"]), sum(R[3 * b + 1] for b in ix["nBases"]), wr


@pytest.mark.parametrize("cpi_key", ["portao_barlavento", "portao_sotavento"])
def test_reacao_horizontal_e_o_arrasto_das_paredes_mais_o_do_telhado(portico, cpi_key):
    rx, _ry, wr = _reacao_horizontal(cpi_key)
    q = wr["q_kN_m2"]
    # h/b = 8/20 = 0,40 ; a/b = 28,5/20 = 1,425 -> Tabela 6: A = +0,7 ; B = -0,4
    assert wr["cpe"]["parede_barlavento"] == 0.7 and wr["cpe"]["parede_sotavento"] == -0.4
    paredes = (0.7 - (-0.4)) * q * 5.7 * 8.0
    # telhado: agua de barlavento puxa para tras, a de sotavento para a frente
    agua = math.hypot(10.0, 1.5)
    seno = 1.5 / agua
    telhado = (wr["cpe"]["cobertura_barlavento"] - wr["cpe"]["cobertura_sotavento"]) \
        * q * 5.7 * agua * seno
    assert -rx == pytest.approx(paredes + telhado, rel=1e-6)
    # o arrasto nao depende da pressao interna: ela empurra as duas paredes igual
    assert -rx == pytest.approx(-_reacao_horizontal("portao_barlavento")[0], rel=1e-9)


def test_reacao_vertical_e_a_succao_do_telhado(portico):
    _rx, ry, wr = _reacao_horizontal("portao_barlavento")
    q, cpi = wr["q_kN_m2"], wr["cpi_cases"]["portao_barlavento"]
    liquido = (wr["cpe"]["cobertura_barlavento"] - cpi) + (wr["cpe"]["cobertura_sotavento"] - cpi)
    # cada agua cobre 10 m de projecao horizontal
    assert ry == pytest.approx(liquido * q * 5.7 * 10.0, rel=1e-6)
    assert ry < 0                                   # arrancamento: reacao para baixo


def test_sem_geometria_vale_o_bloco_antigo():
    assert vi.cpe_paredes() == {"parede_barlavento": 0.7, "parede_sotavento": -0.6}
    # 1/2 < h/b <= 3/2: 5 graus -0,9 e 10 graus -1,1 -> 5,71 graus: -0,93
    assert vi.cpe_telhado(5.71) == {"cobertura_barlavento": -0.93, "cobertura_sotavento": -0.6}
    assert vi.cpe_telhado_longitudinal(5.0) == {"cobertura_long_EG": -0.9,
                                                "cobertura_long_FH": -0.6}


@pytest.mark.parametrize("h_b, a_b, barl, sot", [
    (0.40, 1.425, 0.7, -0.4), (0.40, 2.5, 0.7, -0.5), (0.60, 1.2, 0.7, -0.5),
    (0.60, 3.0, 0.7, -0.6), (2.0, 1.0, 0.8, -0.6), (2.0, 4.0, 0.8, -0.6),
    (0.40, 1.75, 0.7, -0.45),      # Nota 2: interpola entre 3/2 e 2
    (0.60, 6.0, 0.7, -0.6),        # acima de 4: ultima linha, com aviso no memorial
])
def test_paredes_pela_tabela_6(h_b, a_b, barl, sot):
    c = vi.cpe_paredes(h_b, a_b)
    assert (c["parede_barlavento"], c["parede_sotavento"]) == (barl, pytest.approx(sot))


@pytest.mark.parametrize("theta, h_b, efi, ghj, eg, fh", [
    (5.0, 0.4, -0.9, -0.4, -0.8, -0.4), (10.0, 0.4, -1.2, -0.4, -0.8, -0.6),
    (7.5, 0.4, -1.05, -0.4, -0.8, -0.5), (20.0, 0.4, -0.4, -0.4, -0.7, -0.6),
    (10.0, 1.0, -1.1, -0.6, -0.8, -0.6), (30.0, 1.0, -0.2, -0.5, -0.8, -0.8),
    (5.0, 2.0, -0.8, -0.6, -0.8, -0.8), (40.0, 2.0, -0.2, -0.5, -0.8, -0.7),
])
def test_telhado_pela_tabela_7(theta, h_b, efi, ghj, eg, fh):
    t = vi.cpe_telhado(theta, h_b)
    l = vi.cpe_telhado_longitudinal(theta, h_b)
    assert (t["cobertura_barlavento"], t["cobertura_sotavento"]) == (efi, ghj)
    assert (l["cobertura_long_EG"], l["cobertura_long_FH"]) == (eg, fh)


def test_fora_das_tabelas_reprova():
    with pytest.raises(ValueError, match="Tabela 7"):
        vi.cpe_telhado(65.0, 0.4)
    with pytest.raises(ValueError, match="limite 6"):
        vi.cpe_paredes(7.0, 2.0)
    with pytest.raises(ValueError, match="MAIOR dimensao"):
        vi.cpe_paredes(0.4, 0.8)


def test_proporcoes_usam_a_menor_dimensao_em_planta():
    assert vi.proporcoes(20.0, 8.0, 28.5) == pytest.approx((0.4, 1.425))
    assert vi.proporcoes(20.0, 8.0, 10.0) == pytest.approx((0.8, 2.0))


def test_memorial_cita_a_edicao_e_a_proporcao_real():
    txt = vi.relatorio_pt(vi.compute(larg_b=20.0, alt_h=8.0, comp_a=28.5, theta=8.53))
    assert "NBR 6123:2023" in txt and "h/b = 0.40" in txt and "a/b = 1.43" in txt
    assert "grupo 4: SEM ocupacao humana" in txt       # S3 = 0,95 do padrao do motor
    longo = vi.relatorio_pt(vi.compute(larg_b=20.0, alt_h=8.0, comp_a=100.0, theta=8.53))
    assert "FORA da Tabela 6" in longo and "FORA da Tabela 6" not in txt
