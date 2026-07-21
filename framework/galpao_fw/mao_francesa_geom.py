# ============================================================================
# mao_francesa_geom.py - GEOMETRIA (pura, sem FreeCAD) das maos-francesas.
# A mao-francesa (flange brace) CONTEM LATERALMENTE a mesa inferior do rafter,
# comprimida sob succao de vento. Bellei (Fig. 8.16/8.17) e NBR 8800 (Anexo G):
# ela liga a MESA INFERIOR a uma TERCA (que corre no sentido LONGITUDINAL do
# galpao, X) e restringe a translacao lateral da mesa PARA FORA do plano do
# portico - o proprio movimento da flambagem lateral com torcao (FLT).
#
# => Cada braco DEVE ter componente LONGITUDINAL (X): fica no plano X-Z (secao
#    transversal do rafter, Y constante), NAO no plano do portico (Y-Z).
#
# BUG HISTORICO (corrigido): o desenho colocava o braco em X CONSTANTE (plano do
# portico) apontando para baixo, sem tocar a terca -> nao travava a mesa inferior
# fora do plano (nao cumpria funcao nenhuma). Guardado por test_mao_francesa_geom.
#
# O ESPACAMENTO (quantos bracos, o stride) vem do calculo em mao_francesa.py
# (inversao da interacao flexo-compressao); AQUI so a colocacao geometrica 3D.
# ============================================================================
"""Endpoints 3D das maos-francesas (mesa inferior -> terca, com offset longitudinal)."""

from __future__ import annotations

import math


def segmentos(axes, cols_y, ridges_y, n_terca, brace_k, raf_h, poff, rafter_z,
              theta=0.0):
    """Lista de (p1, p2, nome) - uma mao-francesa por (portico x, terca travada).

    Eixos: rafter corre em Y (no plano do portico, X do frame); tercas correm em X
    (longitudinal), acima do rafter (z = rafter_z(y) + poff). A mesa inferior fica
    em z = rafter_z(y) - raf_h/2*cos(theta).

    Geometria CORRETA:
      p1 = mesa inferior          (x,             y, z_bot)
      p2 = terca (deslocada em X)  (x + sgn*off_x, y, z_terca)   [Y constante]
    off_x = (z_terca - z_bot) da ~45 graus e, sendo != 0, garante o travamento da
    mesa FORA do plano do portico. sgn alterna o lado longitudinal por agua.

    Parametros: axes (X dos porticos), cols_y (Y das colunas), ridges_y (Y das
    cumeeiras por vao), n_terca (tercas por agua), brace_k (indices de terca que
    recebem braco), raf_h (altura do perfil do rafter), poff (offset da terca acima
    do eixo do rafter), rafter_z(y)->z do eixo do rafter, theta (inclinacao, rad).
    """
    segs = []
    nv = len(cols_y) - 1
    ct = math.cos(theta)
    # Dominio LONGITUDINAL onde existe terca para o braco alcancar. As tercas
    # correm de ponta a ponta do galpao, ou seja, de axes[0] ate axes[-1].
    x_min, x_max = min(axes), max(axes)
    for x in axes:
        c = 0
        for j in range(nv):
            y0, y1 = cols_y[j], cols_y[j + 1]
            yrj = ridges_y[j]
            for k in brace_k:
                # posicoes de terca nas duas aguas do vao j (mesma conta do desenho
                # das tercas em build_galpao); sgn = lado longitudinal do braco.
                for y, sgn in ((y0 + (yrj - y0) * k / n_terca, +1.0),
                               (y1 - (y1 - yrj) * k / n_terca, -1.0)):
                    c += 1
                    za = rafter_z(y)
                    z_bot = za - (raf_h / 2.0) * ct       # mesa inferior do rafter
                    z_ter = za + poff                      # terca (corre em X, acima)
                    off_x = z_ter - z_bot                  # componente LONGITUDINAL
                    # Nos porticos de EXTREMIDADE o braco so pode apontar para
                    # DENTRO: fora deles nao existe terca para travar. Com o sgn
                    # alternado CEGO, o braco da agua D no portico x=0 mirava
                    # x=-665 (fora do galpao) e nao tocava terca nenhuma - medido
                    # no modelo: 4 de 24 bracos a 361,83 mm da terca mais proxima,
                    # sempre nas duas pontas, justamente os porticos mais
                    # solicitados por vento.
                    s = sgn
                    if not (x_min <= x + s * off_x <= x_max):
                        if x_min <= x - s * off_x <= x_max:
                            s = -s                         # o outro lado alcanca
                    p1 = (x, y, z_bot)
                    p2 = (x + s * off_x, y, z_ter)
                    segs.append((p1, p2,
                                 "MAO_FRANCESA_S%02d_%02d_%02d" % (j, int(x) // 1000, c)))
    return segs
