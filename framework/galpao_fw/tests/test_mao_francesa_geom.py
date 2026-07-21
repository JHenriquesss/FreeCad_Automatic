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


# ---------------------------------------------------------------------------
# BRACO APONTANDO PARA FORA DO GALPAO (medido no modelo em 2026-07-21)
# Das 24 maos-francesas da amostra, 4 ficavam a 361,83 mm da terca mais proxima -
# nao tocavam terca NENHUMA, logo nao travavam a mesa inferior contra FLT.
# Sempre nos porticos de EXTREMIDADE: MAO_FRANCESA_S00_00_02 ia de X=-665,0 a
# X=+5,7, ou seja, para FORA do galpao (que comeca em X=0). Causa: `sgn`
# alternava o lado longitudinal por agua sem olhar ONDE o portico estava.
# Agrava: os porticos de ponta sao os mais solicitados por vento.
# ---------------------------------------------------------------------------
def _segs_3_porticos():
    """3 porticos: 0 e 10000 sao extremidades, 5000 e interior."""
    return MFG.segmentos(axes=[0.0, 5000.0, 10000.0], cols_y=[0.0, 15000.0],
                         ridges_y=[7500.0], n_terca=4, brace_k=[2],
                         raf_h=RAF_H, poff=POFF, rafter_z=_rafter_z,
                         theta=math.atan(SLOPE))


def test_nenhum_braco_aponta_para_fora_do_galpao():
    """A GUARDA: fora de [axes[0], axes[-1]] nao existe terca para travar."""
    for axes, segs in (([0.0, 5000.0], _segs()),
                       ([0.0, 5000.0, 10000.0], _segs_3_porticos())):
        lo, hi = min(axes), max(axes)
        for p1, p2, nm in segs:
            assert lo - 1e-6 <= p2[0] <= hi + 1e-6, (
                nm, "braco mira x=%.1f, fora de [%.1f, %.1f] - nao toca terca"
                % (p2[0], lo, hi))


def test_portico_de_ponta_aponta_para_dentro():
    """No primeiro portico os dois bracos vao para +X; no ultimo, para -X."""
    segs = _segs_3_porticos()
    prim = [s for s in segs if abs(s[0][0] - 0.0) < 1e-6]
    ult = [s for s in segs if abs(s[0][0] - 10000.0) < 1e-6]
    assert prim and ult
    for p1, p2, nm in prim:
        assert p2[0] > p1[0], (nm, "braco do primeiro portico deveria ir para +X")
    for p1, p2, nm in ult:
        assert p2[0] < p1[0], (nm, "braco do ultimo portico deveria ir para -X")


def test_portico_interior_mantem_a_alternancia():
    """A inversao vale SO nas pontas - no meio o lado continua alternando por
    agua (distribui o travamento em vez de enviesar tudo para um lado)."""
    meio = [s for s in _segs_3_porticos() if abs(s[0][0] - 5000.0) < 1e-6]
    assert len(meio) == 2, len(meio)
    lados = sorted(1 if p2[0] > p1[0] else -1 for p1, p2, _ in meio)
    assert lados == [-1, 1], "portico interior deveria ter um braco de cada lado"


# ---------------------------------------------------------------------------
# GEOMETRIA COMPARTILHADA calc <-> build. `comprimento_braco` existe para o gate
# 4.11.3.4 (contencao_lateral) verificar EXATAMENTE a peca que o 3D desenha.
#
# ARMADILHA QUE ME CUSTOU UMA ENTREGA PARCIAL: comparei o comprimento do EIXO
# (derivado, 659,3 mm) com o BOUNDING BOX medido no modelo (670,6 mm), concluí
# que havia 11,3 mm inexplicados e me RECUSEI a ligar o gate por isso. Nao havia
# discrepancia: o braco e um CILINDRO de diametro 16, e o bbox mede
# off_x + d.sen(45) = 659,3 + 11,31 = 670,6. Residuo real: 0,016 mm.
# ---------------------------------------------------------------------------
def test_comprimento_braco_bate_com_segmentos():
    """A formula fechada e os endpoints desenhados tem que dar o MESMO valor."""
    RAF_H, RAF_BF, UE_H = 500.0, 200.0, 300.0
    th = math.atan(0.15)
    L, offx = MFG.comprimento_braco(RAF_H, RAF_BF, UE_H, th)
    poff = MFG.offset_terca(RAF_H, RAF_BF, UE_H, th)

    def rz(y):
        return 8000.0 + 0.15 * min(y, 20000.0 - y)

    segs = MFG.segmentos(axes=[5700.0], cols_y=[0.0, 20000.0], ridges_y=[10000.0],
                         n_terca=5, brace_k=[2], raf_h=RAF_H, poff=poff,
                         rafter_z=rz, theta=th)
    p1, p2, _ = segs[0]
    assert abs(math.dist(p1, p2) - L) < 1e-9
    assert abs(abs(p2[0] - p1[0]) - offx) < 1e-9


def test_bbox_do_cilindro_explica_os_11mm():
    """REGRESSAO DO MEU ERRO: bbox = eixo + d.sen(45). Conferir contra o modelo
    exige somar isso, senao 'sobra' um residuo que nao existe."""
    RAF_H, RAF_BF, UE_H = 500.0, 200.0, 300.0
    _, offx = MFG.comprimento_braco(RAF_H, RAF_BF, UE_H, math.atan(0.15))
    bbox_previsto = offx + MFG.DIAM_BRACO * math.sin(math.radians(45.0))
    assert abs(bbox_previsto - 670.60) < 0.05, bbox_previsto   # MEDIDO no modelo


def test_diametro_e_constante_compartilhada():
    """O build desenha com MFG.DIAM_BRACO e o gate verifica com o mesmo valor -
    se divergirem, o calculo aprova/reprova uma peca que nao e a desenhada."""
    src = open(os.path.join(GALPAO, "build_galpao.py"), encoding="utf-8").read()
    assert "mfg.DIAM_BRACO" in src
    assert "rod(doc, p1, p2, 16, nm)" not in src


def test_comprimento_do_braco_nao_muda_ao_inverter():
    """Inverter o lado nao pode encurtar o braco (a peca e a mesma, so espelhada)."""
    esperado = None
    for p1, p2, nm in _segs_3_porticos():
        L = math.dist(p1, p2)
        if esperado is None:
            esperado = L
        assert abs(L - esperado) < 1e-6, (nm, L, esperado)
