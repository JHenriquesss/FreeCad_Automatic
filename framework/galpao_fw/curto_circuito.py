# ============================================================================
# curto_circuito.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Corrente de CURTO-CIRCUITO presumida no secundario do transformador de entrada,
# base para especificar a capacidade de interrupcao (Icu) dos disjuntores e a
# secao minima de curto dos condutores. Base: Mamede Filho, "Instalacoes
# Eletricas Industriais", Cap.5 (5.5.3):
#   - corrente nominal secundaria: In = Sn/(raiz(3)*Vn)  [Sn em kVA, Vn em kV -> A]
#   - corrente de curto simetrica trifasica: Ik3 = In*100/z%  (z% do trafo)
#   - corrente assimetrica: Ica = Fa*Ics, com o fator de assimetria
#     Fa = raiz(1 + 2*e^(-2*t/Ct)) e Ct = X/(377*R) (60 Hz); t = 1/4 ciclo = 0,00416 s.
# Formulas e o exemplo (300 kVA, 380 V, z=4,5% -> In=455,8 A ; Ik3=10,13 kA) LIDOS
# do PDF de Mamede/Manual de Equipamentos via NotebookLM - NAO de memoria.
# Unidades: Sn em kVA; Vn em kV (linha); Icc em A. Saidas em portugues.
# ============================================================================
"""Corrente de curto-circuito no secundario do trafo (Mamede Cap.5): In, Ik3
simetrica e Ica assimetrica. Sn em kVA, Vn em kV, correntes em A."""

from __future__ import annotations

import math

OMEGA_60HZ = 377.0        # 2*pi*60, rad/s
T_QUARTO_CICLO = 1.0 / 240.0   # 1/4 de ciclo em 60 Hz = 0,004166... s


def corrente_nominal(Sn_kVA, Vn_kV):
    """Corrente nominal (linha): In = Sn/(raiz(3)*Vn). Sn kVA, Vn kV -> A."""
    return Sn_kVA / (math.sqrt(3.0) * Vn_kV)


def icc_simetrica(Sn_kVA, Vn_kV, z_pct):
    """Corrente de curto-circuito simetrica trifasica presumida no secundario:
    Ik3 = In*100/z%. Retorna dict {In, Ik3, Sn, Vn, z_pct}."""
    In = corrente_nominal(Sn_kVA, Vn_kV)
    Ik3 = In * 100.0 / z_pct
    return {"In": In, "Ik3": Ik3, "Sn_kVA": Sn_kVA, "Vn_kV": Vn_kV, "z_pct": z_pct}


def fator_assimetria(x_sobre_r, t_s=T_QUARTO_CICLO):
    """Fator de assimetria Fa = raiz(1 + 2*e^(-2*t/Ct)), Ct = (X/R)/377 (Mamede
    5.5.3.8). x_sobre_r = X/R do ponto. Tende a raiz(3) quando X/R -> inf."""
    Ct = x_sobre_r / OMEGA_60HZ
    return math.sqrt(1.0 + 2.0 * math.exp(-2.0 * t_s / Ct))


def icc_assimetrica(Ics, x_sobre_r, t_s=T_QUARTO_CICLO):
    """Corrente eficaz assimetrica: Ica = Fa*Ics."""
    Fa = fator_assimetria(x_sobre_r, t_s)
    return {"Ica": Fa * Ics, "Fa": Fa, "Ics": Ics}


def _selftest():
    """Afere contra o exemplo de Mamede/Manual: trafo 300 kVA, 380 V, z=4,5%."""
    r = icc_simetrica(300.0, 0.38, 4.5)
    assert abs(r["In"] - 455.80) < 0.1, r["In"]
    assert abs(r["Ik3"] - 10128.9) < 2.0, r["Ik3"]        # 10,13 kA
    r5 = icc_simetrica(300.0, 0.38, 5.0)
    assert abs(r5["Ik3"] - 9116.0) < 2.0, r5["Ik3"]       # z=5,0% -> 9,12 kA
    # fator de assimetria: limite superior raiz(3) para X/R muito grande
    assert fator_assimetria(1e6) < math.sqrt(3.0) + 1e-6
    assert fator_assimetria(1e6) > 1.70                   # ~raiz(3)=1,732
    assert fator_assimetria(0.5) < fator_assimetria(50.0) # mais indutivo -> mais assimetria
    print("curto_circuito self-test PASSED (Mamede 300 kVA -> 10,13 kA)")


if __name__ == "__main__":
    _selftest()
