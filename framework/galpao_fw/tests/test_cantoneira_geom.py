# ============================================================================
# test_cantoneira_geom.py - propriedades da cantoneira de abas iguais.
#
# POR QUE DERIVAR EM VEZ DE TABELAR: nao ha tabela de perfis L nas fontes do
# projeto (o Apendice A do Fakury lista os NOMES das variaveis e o trecho e
# cortado antes dos valores). Escrever bitolas de catalogo DE MEMORIA foi
# exatamente o erro do "AR300" - inventei uma classe de aco inexistente e ainda
# criei um teste que cristalizava o erro. Aqui nao ha esse risco: as propriedades
# de uma cantoneira de abas iguais tem FORMA FECHADA a partir de b e t.
#
# COMO ESTE TESTE VALIDA: por INTEGRACAO EXATA DE POLIGONO (Green/shoelace) -
# rota deliberadamente diferente da soma de dois retangulos com translacao de
# eixos usada em perfis.cantoneira. Sem dado externo e sem discretizacao: as duas
# rotas batem a 1e-9. NENHUM numero de catalogo aparece neste arquivo.
#
# FILLET DESPREZADO: o raio de concordancia ACRESCENTA area e inercia, entao
# desprezar da A e I MENORES que o catalogo -> conservador para resistencia.
# ============================================================================
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import perfis


def _malha(b_mm, t_mm):
    """Momentos da secao em L por INTEGRACAO EXATA DE POLIGONO (Green/shoelace).

    Metodo deliberadamente DIFERENTE do usado em perfis.cantoneira (que soma dois
    retangulos com translacao de eixos). Aqui a secao entra como UM poligono e os
    momentos saem de somatorios sobre as arestas - se as duas rotas concordam, a
    algebra da decomposicao esta certa. E EXATO: sem malha, sem erro de
    discretizacao (a primeira versao deste teste usava celulas quadradas e
    acusava 0,24% de "erro" que era so o contorno y=t caindo entre celulas).
    """
    b, t = b_mm * 1e-3, t_mm * 1e-3
    P = [(0.0, 0.0), (b, 0.0), (b, t), (t, t), (t, b), (0.0, b)]
    A = Cx = Cy = Ixx0 = Ixy0 = 0.0
    for i in range(len(P)):
        x0, y0 = P[i]
        x1, y1 = P[(i + 1) % len(P)]
        cr = x0 * y1 - x1 * y0
        A += cr
        Cx += (x0 + x1) * cr
        Cy += (y0 + y1) * cr
        Ixx0 += (y0 * y0 + y0 * y1 + y1 * y1) * cr
        Ixy0 += (x0 * y1 + 2.0 * x0 * y0 + 2.0 * x1 * y1 + x1 * y0) * cr
    A *= 0.5
    Cx /= (6.0 * A)
    Cy /= (6.0 * A)
    Ixx0 /= 12.0
    Ixy0 /= 24.0
    Ix = Ixx0 - A * Cy * Cy                      # transporte para o centroide
    Ixy = Ixy0 - A * Cx * Cy
    return A, Cx, Cy, Ix, Ixy


@pytest.mark.parametrize("b,t", [(50, 5), (63, 6), (76, 8), (102, 9.5)])
def test_forma_fechada_bate_com_integracao_numerica(b, t):
    c = perfis.cantoneira(b, t)
    A, cgx, cgy, Ix, Ixy = _malha(b, t)
    assert c["A"] == pytest.approx(A, rel=1e-9)
    assert c["cg"] == pytest.approx(cgy, rel=1e-9)
    assert c["Ix"] == pytest.approx(Ix, rel=1e-9)
    assert abs(c["Ixy"]) == pytest.approx(abs(Ixy), rel=1e-9)


@pytest.mark.parametrize("b,t", [(50, 5), (63, 6), (76, 8), (102, 9.5)])
def test_r_min_bate_com_integracao(b, t):
    """r_min governa a flambagem da cantoneira simples - e o valor que o gate
    4.11.3.4 usa contra o limite de esbeltez 200."""
    c = perfis.cantoneira(b, t)
    A, _, _, Ix, Ixy = _malha(b, t)
    r_min_num = math.sqrt((Ix - abs(Ixy)) / A)
    assert c["r_min"] == pytest.approx(r_min_num, rel=1e-9)


def test_area_e_a_formula_elementar():
    """A = t(2b - t): dois retangulos menos a sobreposicao do canto."""
    c = perfis.cantoneira(50, 5)
    assert c["A"] == pytest.approx(5e-3 * (2 * 50e-3 - 5e-3))


def test_abas_iguais_tem_Ix_igual_a_Iy():
    """Simetria em relacao a diagonal de 45 graus."""
    c = perfis.cantoneira(63, 6)
    assert c["Ix"] == c["Iy"]


def test_eixos_principais_a_45_graus():
    """Para abas iguais, I_max/I_min = Ix +/- |Ixy| (eixos principais a 45)."""
    c = perfis.cantoneira(76, 8)
    assert c["I_max"] == pytest.approx(c["Ix"] + abs(c["Ixy"]))
    assert c["I_min"] == pytest.approx(c["Ix"] - abs(c["Ixy"]))
    assert c["I_min"] < c["Ix"] < c["I_max"]


@pytest.mark.parametrize("b,t", [(50, 5), (63, 6), (76, 8), (102, 9.5), (127, 12.7)])
def test_razao_r_min_sobre_b_e_estavel(b, t):
    """Propriedade geometrica conhecida da cantoneira de abas iguais: r_min/b fica
    em torno de 0,195-0,197 para as espessuras usuais. Serve de sanidade: se a
    algebra quebrar, essa razao foge."""
    c = perfis.cantoneira(b, t)
    assert 0.19 < c["r_min"] / c["b"] < 0.20


def test_geometria_invalida_levanta():
    for b, t in ((50, 50), (50, 60), (50, 0), (50, -5)):
        with pytest.raises(ValueError):
            perfis.cantoneira(b, t)


def test_nome_do_perfil():
    assert perfis.cantoneira(63, 6)["nome"] == "L63x63x6"
