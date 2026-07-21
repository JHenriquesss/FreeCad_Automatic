# ============================================================================
# test_terca_assento_3d.py - a terca senta SOBRE a chapa de assento, e a chapa
# senta sobre a mesa da viga. Nenhuma das duas dentro da outra.
#
# ACHADO PRINCIPAL (o filtro morto): `vigas` era coletado com
#     [o for o in doc.Objects if "_VIGA_" in o.Name]
# mas as vigas do portico chamam-se PORTICO_xx_Vyy_E/D. O filtro NUNCA casava:
# `vigas` saia VAZIA e TODO `_assenta(terca, vigas)` era no-op. O comentario no
# codigo prometia um "assentamento MEDIDO robusto a inclinacao" que jamais rodou -
# as tercas ficavam na estimativa POFF, penetrando a mesa da viga.
#
# MEDIDO no modelo da amostra (60 clipes, 6 porticos x 10 tercas):
#   ANTES  cj=01..08 (intermediarias) 60,1% do volume do clipe DENTRO da viga
#          cj=09..10 (beiral)         23,3% .. 60,2% dentro do pilar/escora/gusset
#   DEPOIS todos os 60                 0,0%
#
# Eram DUAS falhas com a mesma raiz - valor AFIRMADO em vez de MEDIDO:
#  A) beiral: `terca_seats.append((y, EAVE_H))` afirmava que a face inferior da
#     terca de beiral era EAVE_H. Medido: EAVE_H + 262 mm - quem apoia a terca de
#     beiral e a VIGA (que passa por cima do pilar), nao a cota do pilar. O clipe
#     ficava 262 mm abaixo da terca, enterrado na cabeca do pilar, apoiando NADA.
#  B) intermediarias: o clipe encostava certo na terca, mas ocupava 8 mm de viga
#     macica - ninguem abria espaco para a chapa.
#
# A chapa segue a INCLINACAO da terca (mesa da viga e terca sao paralelas ao plano
# do telhado; chapa horizontal entre as duas cunharia ~12 mm em 120 mm de largura).
# ============================================================================
import ast
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

BUILD_SRC = os.path.join(GALPAO, "build_galpao.py")


@pytest.fixture(scope="module")
def src():
    return open(BUILD_SRC, encoding="utf-8").read()


def test_filtro_de_vigas_casa_com_o_nome_real(src):
    """REGRESSAO DO ACHADO: "_VIGA_" nao existe em nome nenhum do modelo. As vigas
    sao PORTICO_xx_Vyy[_E|_D] (ver i_member/tapered_rafter)."""
    codigo = [l for l in src.splitlines() if not l.lstrip().startswith("#")]
    assert not [l for l in codigo if '"_VIGA_" in o.Name' in l], (
        "o filtro morto voltou ao codigo")
    assert r'PORTICO_\d+_V\d+' in src


def test_nomes_de_viga_conferem_com_o_filtro(src):
    """O padrao do filtro tem que casar com os nomes que o proprio build gera."""
    pat = re.compile(r"^PORTICO_\d+_V\d+")
    gerados = ["PORTICO_01_V00", "PORTICO_01_V00_E", "PORTICO_12_V03_D"]
    for n in gerados:
        assert pat.match(n), "filtro nao pega %s" % n
    for n in ("VIGA_ROLAMENTO_01", "PORTICO_01_C00", "TERCA_S00_E_01"):
        assert not pat.match(n), "filtro pega %s indevidamente" % n


def test_beiral_nao_afirma_EAVE_H(src):
    """A cota da face inferior da terca de beiral e MEDIDA (_assenta), nunca o
    EAVE_H afirmado - que errava 262 mm."""
    assert "terca_seats.append((y, EAVE_H))" not in src
    assert "_assenta(_ob, _ap_beiral)" in src


def test_beiral_apoia_na_viga_e_na_escora(src):
    """Quem sustenta a terca de beiral e a viga (passa por cima do pilar) + escora."""
    assert "_ap_beiral = vigas + [o for o in doc.Objects" in src
    assert '"ESCORA_BEIRAL" in o.Name' in src


def test_chapa_segue_a_inclinacao_da_terca(src):
    """plate_basis com a base do plano do telhado - nao plate() horizontal."""
    assert "cl = plate_basis(doc," in src
    assert "(0.0, _c, _s), (0.0, -_s, _c)" in src


def test_agua_E_e_D_tem_sinais_opostos(src):
    """A face inferior sobe na agua E (+theta) e desce na D (-theta)."""
    assert "_terca_angs.append(_theta)" in src
    assert "_terca_angs.append(-_theta)" in src


def test_terca_sobe_depois_que_a_chapa_existe(src):
    """ORDEM: assenta a chapa na viga -> so entao assenta a terca nas chapas. O
    inverso deixaria a chapa 60% enterrada (era exatamente o estado anterior)."""
    i_chapa = src.index("_assenta(cl, apoios)")
    i_terca = src.index("st[1] = _assenta(st[2], st[5])")
    assert i_chapa < i_terca


def test_espessura_da_chapa_e_unica(src):
    """T_CLIPE serve o assento da terca, o clipe de girt E o rotulo do takeoff."""
    assert re.search(r"^T_CLIPE = 8\.0", src, re.M)
    assert '"chapa-%.0f" % T_CLIPE' in src
    assert '"Clipes de apoio (conexao)", "chapa-8"' not in src
    assert "90.0, 120.0, T_CLIPE" in src          # assento da terca
    assert "90.0, T_CLIPE, 120.0" in src          # clipe de girt


def test_telha_le_a_cota_medida(src):
    """A telha se apoia no topo da terca MEDIDO (st[1]), nao na estimativa."""
    assert "max((st[1] + UE_SEC[0] - rafter_z(st[0])) for st in terca_seats)" in src


def test_fonte_compila(src):
    ast.parse(src)
