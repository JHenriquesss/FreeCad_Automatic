# ============================================================================
# test_takeoff_x_modelo.py - o ROTULO do takeoff tem que descrever a peca que o
# 3D realmente desenha.
#
# O takeoff calcula massa = Shape.Volume x densidade, entao a QUANTIDADE nunca
# diverge do modelo. O que diverge e o ROTULO (o perfil declarado) - e quando o
# rotulo mente, quem compra o material compra a peca errada.
#
# ACHADO 1 - MISULA MACICA (o caro): a misula do joelho era um TRIANGULO
# EXTRUDADO 180 mm, ou seja, um BLOCO MACICO, rotulado "chapa-9.5". Como a massa
# sai do volume:
#     254,3 kg por misula  ->  3.052,1 kg no total  =  6,2% de TODO o aco
# A misula real e FABRICADA EM CHAPAS SOLDADAS: alma (triangulo) + MESA INFERIOR
# propria ao longo da aresta inclinada. A mesa inferior nao e detalhe estetico -
# e o elemento COMPRIMIDO sob momento negativo no joelho, o que governa a FLT ali
# (fonte: "no 'joelho tapered', a mesa inferior e inclinada por um angulo theta").
# O proprio caminho `alma_variavel` deste framework ja modelava o joelho como I
# duplamente simetrico; so o caminho PRISMATICO estava fora de passo.
#     depois: 37,5 kg por misula -> 449,6 kg no total
#     aco total: 49.140,3 -> 46.537,9 kg (-2.602,4 kg, -5,3%)
#     a diferenca bate EXATAMENTE com a reducao das misulas: nada mais mudou.
#
# ACHADO 2 - ARRUELA: rotulada "chapa-10" e desenhada com 12 mm.
#
# CONFERIDOS E CORRETOS (o rotulo ja derivava): placa de base chapa-100,
# chumbador barra-32, gusset chapa-12, nervura chapa-12, clipe chapa-8,
# enrijecedor do joelho chapa-12.
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


# ---- misula: chapas soldadas, nao bloco macico ----------------------------
def test_misula_nao_e_mais_bloco_macico(src):
    """O extrude de 180 mm criava um prisma triangular SOLIDO."""
    assert "App.Vector(180.0, 0, 0))" not in src
    assert "sol.translate(App.Vector(-90.0, 0, 0))" not in src


def test_misula_tem_alma_na_espessura_do_rafter(src):
    assert "_bf, _tw, _tf = RAF_SEC[1], RAF_SEC[2], RAF_SEC[3]" in src
    assert "alma.translate(App.Vector(-_tw / 2.0, 0, 0))" in src


def test_misula_tem_mesa_inferior_propria(src):
    """A mesa inclinada e o elemento comprimido no joelho - sem ela a peca nao
    representa o que resiste ao momento negativo."""
    assert "_box = Part.makeBox(_bf, _Lf, _tf)" in src
    assert "sol = alma.fuse(_box)" in src


def test_mesa_vai_para_fora_do_triangulo(src):
    """Se a mesa cair para DENTRO do triangulo ela some dentro da alma e a massa
    volta a ficar errada (agora para menos)."""
    assert "if _Av.sub(_Bv).dot(_n) > 0.0:" in src
    assert "_n = _n.negative()" in src


def test_rotulo_da_misula_deriva_do_rafter(src):
    codigo = [l for l in src.splitlines() if not l.lstrip().startswith("#")]
    assert not [l for l in codigo if '"chapa-9.5"' in l]
    assert '"alma-%.1f/mesa-%.0f" % (RAF_SEC[2], RAF_SEC[3])' in src


def test_rotulo_sem_virgula(src):
    """O takeoff e CSV: uma virgula no rotulo desloca todas as colunas."""
    arv = ast.parse(src)
    fn = next(n for n in arv.body
              if isinstance(n, ast.FunctionDef) and n.name == "_classifica")
    for no in ast.walk(fn):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            assert "," not in no.value, "rotulo com virgula quebra o CSV: %r" % no.value


# ---- arruela --------------------------------------------------------------
def test_arruela_rotulo_bate_com_a_espessura(src):
    assert re.search(r"^T_ARRUELA = 12\.0", src, re.M)
    assert '"chapa-%.0f" % T_ARRUELA' in src
    assert '"Arruelas", "chapa-10"' not in src


def test_arruela_desenhada_com_a_constante(src):
    assert "wsz, wsz, wt," in src
    assert "wsz, wsz, 12," not in src


# ---- guarda geral ---------------------------------------------------------
def test_espessuras_de_chapa_declaradas_sao_constantes_nomeadas(src):
    """Cada 'chapa-N' do takeoff tem que sair de uma constante/parametro, nunca de
    um literal - foi assim que 'chapa-10' e 'chapa-9.5' passaram a mentir."""
    arv = ast.parse(src)
    fn = next(n for n in arv.body
              if isinstance(n, ast.FunctionDef) and n.name == "_classifica")
    literais = []
    for no in ast.walk(fn):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            if re.fullmatch(r"chapa-[\d.]+", no.value):
                literais.append(no.value)
    # Sobram 5 literais, todos de pecas cuja espessura NAO vem do calculo:
    #   nervura da base (12) e enrijecedor do joelho (12) - conferidos contra a
    #   geometria, batem; console da ponte: chapa (16), trilho (12), bracket (12).
    # O teto existe para a lista nao CRESCER: espessura nova tem que entrar como
    # constante nomeada, como T_CLIPE / T_ARRUELA / GUSSET_T.
    assert len(literais) <= 5, "novas espessuras cravadas no takeoff: %s" % literais


def test_fonte_compila(src):
    ast.parse(src)
