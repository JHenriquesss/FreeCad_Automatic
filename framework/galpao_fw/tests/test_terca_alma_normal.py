# ============================================================================
# test_terca_alma_normal.py - a TERCA de cobertura tem que ter a alma
# PERPENDICULAR AO PLANO DO TELHADO, nao vertical.
#
# POR QUE: o gate `tercas_nbr14762` decompoe a gravidade em
#     qx = G*cos(theta)  (normal ao telhado -> eixo FORTE)
#     qy = G*sin(theta)  (paralela ao telhado -> eixo fraco)
# e trata o VENTO como ja normal ao telhado (so qx). Essa decomposicao SO vale se
# os eixos principais da terca estiverem alinhados com o plano do telhado, ou
# seja, alma perpendicular a ele. O modelo desenhava a alma VERTICAL (medido:
# dY=85 / dZ=300 exatos, sem inclinacao) - contradizia a memoria e ainda fazia a
# terca apoiar DE CANTO na mesa inclinada do rafter.
#
# Mesma familia do eixo forte da coluna (test_coluna_orientacao), so que aqui o
# desalinhamento e de theta (8,53 graus na amostra) em vez de 90.
#
# Validado ao vivo pela NORMAL DA FACE SUPERIOR (onde a telha assenta):
#     lado E -> (0, -0.148, 0.989)   lado D -> (0, +0.148, 0.989)
# que e exatamente a normal do telhado a 8,53 graus, espelhada por agua.
# bbox foi de (dY,dZ)=(85,300) para (129,309), como previsto por
#     dY = 300*sin(t) + 85*cos(t)   dZ = 300*cos(t) + 85*sin(t)
# Interferencias seguem em 6 (= baseline do main).
#
# build_galpao nao importa sem FreeCAD -> guarda na FONTE (AST).
# ============================================================================
import ast
import math
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


def _ue_calls(src):
    arv = ast.parse(src)
    out = []
    for n in ast.walk(arv):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "ue_member":
            lit = "".join(v.value for a in n.args if isinstance(a, ast.JoinedStr)
                          for v in a.values if isinstance(v, ast.Constant))
            roll = {k.arg: k.value for k in n.keywords}.get("roll")
            out.append((lit, roll))
    return out


def test_tilt_derivado_da_inclinacao(src):
    """O angulo tem que sair do SLOPE, nao ser numero fixo."""
    assert "_terca_tilt = math.degrees(math.atan(SLOPE))" in src


def test_tercas_de_cobertura_usam_o_tilt(src):
    """As duas aguas usam o tilt, e com SINAIS OPOSTOS (normais espelhadas)."""
    achou = {}
    for lit, roll in _ue_calls(src):
        m = re.search(r"_(E|D)_$", lit) or re.search(r"_(E|D)_", lit)
        if not lit.startswith("TERCA_S") and "_E_" not in lit and "_D_" not in lit:
            continue
        if roll is None:
            continue
        achou[m.group(1) if m else lit] = ast.dump(roll)
    assert "E" in achou and "D" in achou, "nao achei as tercas dos dois lados"
    assert "_terca_tilt" in achou["E"] and "_terca_tilt" in achou["D"]
    # lado D e a rotacao NEGATIVA (espelhada); lado E soma ao flip de 180
    assert "USub" in achou["D"], "lado D precisa do tilt NEGATIVO (agua oposta)"
    assert "180" in achou["E"], "lado E mantem o flip de 180 do perfil Ue"


def test_terca_de_beiral_fica_sem_tilt(src):
    """ESCOPO DELIBERADO: a terca de BEIRAL apoia no TOPO DO PILAR (superficie
    horizontal), nao na mesa inclinada do rafter - por isso o build a posiciona
    sem `_assenta`. Ela mantem so o flip do perfil Ue (roll 180/0), sem o tilt.
    Se um dia o detalhe de beiral exigir a alma normal ao telhado, e mudanca
    consciente - este teste obriga a passar por aqui."""
    for lit, roll in _ue_calls(src):
        if lit.startswith("TERCA_BEIRAL"):
            assert roll is not None
            assert "_terca_tilt" not in ast.dump(roll)


def test_geometria_esperada_do_tilt():
    """Confere a aritmetica que a medicao ao vivo confirmou (Ue 300x85, 15%)."""
    t = math.atan(0.15)
    dY = 300 * math.sin(t) + 85 * math.cos(t)
    dZ = 300 * math.cos(t) + 85 * math.sin(t)
    assert round(dY) == 129
    assert round(dZ) == 309
    assert round(math.sin(t), 3) == 0.148     # normal medida da face superior


def test_fonte_compila(src):
    ast.parse(src)
