# ============================================================================
# test_mao_francesa_geom.py - GARANTE que a mao-francesa NUNCA volte a ser
# desenhada no plano do portico. A funcao dela e travar a mesa inferior do rafter
# LATERALMENTE (fora do plano) sob succao de vento (Bellei 8.16/8.17, NBR 8800
# Anexo G). Bug corrigido na caca sessao 14: o braco ficava em X constante (plano
# do portico) e nao travava nada. Este teste e a rede de seguranca permanente.
# ============================================================================
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import mao_francesa_geom as MFG


# geometria de referencia: 1 vao 15 m, beiral 6 m, cumeeira no meio, 2 porticos,
# rafter HEA300 (raf_h=290), terca ~90 mm acima; braco na 2a terca (de 4).
SLOPE = 0.10
RAF_H = 290.0
POFF = 190.0


def _rafter_z(y):
    # telhado simetrico: sobe do beiral (y=0 e y=15000) ate a cumeeira (y=7500)
    return 6000.0 + SLOPE * min(y, 15000.0 - y)


def _segs():
    return MFG.segmentos(axes=[0.0, 5000.0], cols_y=[0.0, 15000.0],
                         ridges_y=[7500.0], n_terca=4, brace_k=[2],
                         raf_h=RAF_H, poff=POFF, rafter_z=_rafter_z,
                         theta=math.atan(SLOPE))


def test_gera_bracos():
    segs = _segs()
    # 2 porticos x 1 vao x 1 terca travada x 2 aguas = 4 bracos
    assert len(segs) == 4, len(segs)


def test_tem_componente_fora_do_plano():
    # A GUARDA CENTRAL: cada braco PRECISA variar em X (longitudinal). Sem isso
    # ele fica no plano do portico e NAO trava a mesa inferior (bug historico).
    for p1, p2, nm in _segs():
        dx = abs(p2[0] - p1[0])
        assert dx > 1e-6, (nm, "mao-francesa no plano do portico (dx=0) - nao trava a FLT")


def test_liga_mesa_inferior_a_terca():
    for p1, p2, nm in _segs():
        y = p1[1]
        za = _rafter_z(y)
        z_bot_esperado = za - (RAF_H / 2.0) * math.cos(math.atan(SLOPE))
        z_ter_esperado = za + POFF
        # p1 na mesa inferior, p2 na terca (acima)
        assert abs(p1[2] - z_bot_esperado) < 1e-6, nm
        assert abs(p2[2] - z_ter_esperado) < 1e-6, nm
        assert p2[2] > p1[2], (nm, "braco deve subir da mesa inferior ate a terca")


def test_fica_na_linha_da_terca_Y_constante():
    # o braco fica na SECAO transversal (Y constante = linha da terca); o
    # travamento e no plano X-Z, nao Y-Z.
    for p1, p2, nm in _segs():
        assert abs(p2[1] - p1[1]) < 1e-6, (nm, "Y deveria ser constante")


def test_offset_x_da_inclinacao_razoavel():
    # off_x ~ rise -> ~45 graus; nao pode degenerar (0) nem estourar o vao.
    for p1, p2, nm in _segs():
        dx = abs(p2[0] - p1[0]); dz = abs(p2[2] - p1[2])
        assert 100.0 < dx < 2000.0, (nm, dx)
        ang = math.degrees(math.atan2(dz, dx))
        assert 20.0 < ang < 70.0, (nm, ang)
