# ============================================================================
# perfis.py - O QUE ESTE ARQUIVO FORNECE
# Biblioteca de propriedades geometricas de perfis I laminados (serie europeia
# IPE / HEA / HEB), para alimentar o portico (A, Ix) e a verificacao NBR 8800
# (A, Ix, Iy, ry, Wx, Zx, d, bf, tf, tw). Valores em SI (m, m2, m4, m3).
# ATENCAO: propriedades tabeladas do catalogo europeu - A CONFIRMAR com o
# catalogo do fornecedor nacional (Gerdau/CBCA) antes do projeto executivo.
# NAO calcula nada - so tabela de dados de entrada.
# ============================================================================
"""Tabela de perfis I. Entradas do catalogo em (cm2, cm4, cm3, cm, mm)."""

from __future__ import annotations


def _mk(A_cm2, Ix_cm4, Iy_cm4, Wx_cm3, Zx_cm3, ry_cm, d_mm, bf_mm, tf_mm, tw_mm):
    """Converte propriedades de catalogo para SI (m)."""
    return {"A": A_cm2 * 1e-4, "Ix": Ix_cm4 * 1e-8, "Iy": Iy_cm4 * 1e-8,
            "Wx": Wx_cm3 * 1e-6, "Zx": Zx_cm3 * 1e-6, "ry": ry_cm * 1e-2,
            "d": d_mm * 1e-3, "bf": bf_mm * 1e-3, "tf": tf_mm * 1e-3,
            "tw": tw_mm * 1e-3}


#        nome      A     Ix     Iy    Wx    Zx    ry    d    bf   tf   tw
PERFIS = {
    "HEA180": _mk(45.25, 2510, 924.6, 293.6, 324.9, 4.52, 171, 180, 9.5, 6.0),
    "HEA200": _mk(53.83, 3692, 1336, 388.6, 429.5, 4.98, 190, 200, 10.0, 6.5),
    "HEA220": _mk(64.34, 5410, 1955, 515.2, 568.5, 5.51, 210, 220, 11.0, 7.0),
    "HEA240": _mk(76.84, 7763, 2769, 675.1, 744.6, 6.00, 230, 240, 12.0, 7.5),
    "IPE300": _mk(53.81, 8356, 604.0, 557.1, 628.4, 3.35, 300, 150, 10.7, 7.1),
    "IPE330": _mk(62.61, 11770, 788.1, 713.1, 804.3, 3.55, 330, 160, 11.5, 7.5),
    "IPE360": _mk(72.73, 16270, 1043, 903.6, 1019, 3.79, 360, 170, 12.7, 8.0),
    "IPE400": _mk(84.46, 23130, 1318, 1156, 1307, 3.95, 400, 180, 13.5, 8.6),
    "HEB200": _mk(78.08, 5696, 2003, 569.6, 642.5, 5.07, 200, 200, 15.0, 9.0),
    "HEB220": _mk(91.04, 8091, 2843, 735.5, 827.0, 5.59, 220, 220, 16.0, 9.5),
    "HEB240": _mk(106.0, 11260, 3923, 938.3, 1053, 6.08, 240, 240, 17.0, 10.0),
    "HEB260": _mk(118.4, 14920, 5135, 1148, 1283, 6.58, 260, 260, 17.5, 10.0),
    "HEB280": _mk(131.4, 19270, 6595, 1376, 1534, 7.09, 280, 280, 18.0, 10.5),
    "HEB300": _mk(149.1, 25170, 8563, 1678, 1869, 7.58, 300, 300, 19.0, 11.0),
    "IPE450": _mk(98.82, 33740, 1676, 1500, 1702, 4.12, 450, 190, 14.6, 9.4),
    "IPE500": _mk(115.5, 48200, 2142, 1928, 2194, 4.31, 500, 200, 16.0, 10.2),
    "IPE550": _mk(134.4, 67120, 2668, 2441, 2787, 4.45, 550, 210, 17.2, 11.1),
}
