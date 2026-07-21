# ============================================================================
# test_terca_trib_real.py - a TERCA tem que ser verificada com a largura de
# influencia REAL (= espacamento entre tercas), nao com a do galpao de referencia.
#
# BUG: `ti.configurar(..., trib=params["terca"]["trib"])` roda no inicio do
# `rodar()` e usava o PARAMS_REF, cujo 1,675 m e o espacamento do galpao de
# REFERENCIA (vao 10 m -> agua hypot(5;0,5)=5,025 m, n=3 -> 1,675). Dois motivos
# para nao servir ao projeto real:
#   1. a agua tem outro comprimento (amostra: 10,112 m);
#   2. o `n_terca` e AUTO-DIMENSIONADO mais adiante (sobe ate a telha passar) -
#      ou seja, o valor certo nem existe ainda quando o configurar roda.
# Na amostra: trib usado 1,675 contra 2,022 real -> a terca era verificada com
# **21% menos carga** do que recebe. Contra-seguranca.
#
# Medido apos o fix: interacao 0,51 -> 0,62 (razao 2,022/1,675 = 1,21) e flecha
# 9,1 -> 11,0 mm. O perfil adotado nao mudou na amostra, mas mudaria num projeto
# mais carregado.
#
# E a contrapartida do PR #29 (n_terca): la o CALCULO nao chegava ao modelo; aqui
# a GEOMETRIA nao chegava de volta ao calculo.
# ============================================================================
import ast
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

SRC = os.path.join(GALPAO, "rodar_galpao.py")


@pytest.fixture(scope="module")
def src():
    return open(SRC, encoding="utf-8").read()


def test_trib_e_derivado_da_geometria(src):
    assert '_trib_real = _w_agua_t / max(n_terca, 1)' in src
    assert 'ti.configurar(trib=_trib_real)' in src


def test_reconfigura_DEPOIS_de_fixar_o_n_terca(src):
    """O bug era de ORDEM: o configurar original roda antes da auto-dimensao do
    n_terca. A reconfiguracao TEM que vir depois, senao volta a usar valor velho."""
    arv = ast.parse(src)
    ln_final = None      # onde n_terca recebe o valor auto-dimensionado
    ln_reconf = None     # onde trib e reconfigurado
    for n in ast.walk(arv):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                # SO a auto-dimensao (`n_terca = min(_need, 12)`). Ha outra
                # atribuicao bem mais abaixo que apenas RELE params["terca"]
                # (para o Lb do rafter) e ja pega o valor atualizado - ancorar
                # nela daria falso negativo.
                if isinstance(t, ast.Name) and t.id == "n_terca" \
                        and isinstance(n.value, ast.Call) \
                        and getattr(n.value.func, "id", "") == "min":
                    ln_final = max(ln_final or 0, n.lineno)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "configurar" \
                and any(k.arg == "trib" and isinstance(k.value, ast.Name)
                        for k in n.keywords):
            ln_reconf = n.lineno
    assert ln_final and ln_reconf, "nao localizei as duas ancoras"
    assert ln_reconf > ln_final, (
        "reconfiguracao do trib (linha %d) vem ANTES da auto-dimensao do n_terca "
        "(linha %d) - usaria o valor velho" % (ln_reconf, ln_final))


def test_o_1675_do_params_ref_e_mesmo_o_de_referencia():
    """Documenta a origem do numero: galpao de referencia (vao 10, ridge-eave
    0,5, n=3). Se PARAMS_REF mudar, este teste avisa que o comentario envelheceu."""
    import rodar_galpao as RG
    assert RG.PARAMS_REF["terca"]["trib"] == 1.675
    g = RG.PARAMS_REF["geometria"]
    agua = math.hypot(g["span"] / 2.0, g["ridge"] - g["eave"])
    assert round(agua / RG.PARAMS_REF["terca"]["n_por_agua"], 3) == 1.675


def test_aritmetica_da_amostra():
    """Amostra: vao 20, eave 8, ridge 9,5, n_terca=5 -> trib 2,022 (nao 1,675)."""
    agua = math.hypot(20 / 2.0, 9.5 - 8.0)
    assert round(agua / 5, 3) == 2.022
    assert round(2.022 / 1.675, 2) == 1.21      # 21% de carga a mais
