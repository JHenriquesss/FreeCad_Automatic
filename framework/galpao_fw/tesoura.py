# ============================================================================
# tesoura.py - TRELIÇA DE COBERTURA (tesoura)
# Banzo superior PARABOLICO. Isostatico: b + r = 2j.
# Warren: nos inferiores defasados, sem montantes.
# Pratt: nos inferiores alinhados, montantes + 1 diagonal/painel interno.
# ============================================================================
"""Tesoura (trelica de cobertura). Saidas PT. Unidades: m."""

from __future__ import annotations
import math


def gera_trelica(L, h, n_paineis=8, tipo="warren"):
    """Gera trelica isostatica. L (m), h (m) no centro."""
    dx = L / n_paineis
    nos = []
    # Banzo superior: n_paineis+1 nos (parabola)
    for i in range(n_paineis + 1):
        x = i * dx
        y = 4.0 * h * x * (L - x) / (L * L) if L > 0 else 0.0
        nos.append((x, y))
    
    if tipo == "warren":
        # N inferiores defasados (meio do painel), sem conexao direta aos apoios
        for i in range(n_paineis):
            x = (i + 0.5) * dx
            nos.append((x, 0.0))
        n_sup = n_paineis + 1
        n_inf = len(nos)
        banzos_sup = [(i, i + 1) for i in range(n_paineis)]
        # Banzo inferior: 7 barras entre os 8 nos internos (sem ir ate os apoios)
        banzos_inf = [(n_sup + i, n_sup + i + 1) for i in range(n_paineis - 1)]
        # Diagonais: cada no inferior conecta aos 2 nos superiores adjacentes
        diagonais = []
        for i in range(n_paineis):
            inf = n_sup + i
            diagonais.append((inf, i))      # diagonal esquerda
            diagonais.append((inf, i + 1))  # diagonal direita
        montantes = []
    else:  # pratt
        # N inferiores alinhados (exceto extremos, que sao os apoios)
        for i in range(1, n_paineis):
            x = i * dx
            nos.append((x, 0.0))
        n_sup = n_paineis + 1
        n_inf = len(nos)
        banzos_sup = [(i, i + 1) for i in range(n_paineis)]
        # Banzo inferior: 8 barras (apoio 0 -> inf[0] -> ... -> inf[6] -> apoio n)
        banzos_inf = [(0, n_sup)]
        for i in range(n_sup, n_inf - 1):
            banzos_inf.append((i, i + 1))
        banzos_inf.append((n_inf - 1, n_paineis))
        # Montantes: 7 (apenas nos nos internos)
        montantes = [(i, n_sup + i - 1) for i in range(1, n_paineis)]
        # Diagonais: 6 (apenas nos paineis internos 2..n-1, evitando sobreposicao)
        # Primeiro e ultimo painel ja sao triangulados pelo banzo convergente
        diagonais = []
        for i in range(1, n_paineis - 1):
            if i < n_paineis / 2:
                diagonais.append((i + 1, n_sup + i - 1))  # convergente ao centro
            else:
                diagonais.append((i, n_sup + i))          # divergente do centro
    
    return {"nos": nos, "banzo_sup": banzos_sup, "banzo_inf": banzos_inf,
            "diagonais": diagonais, "montantes": montantes,
            "n_nos": n_inf, "n_paineis": n_paineis, "L": L, "h": h,
            "tipo": tipo}


def _selftest():
    t = gera_trelica(20.0, 2.5, 8, "warren")
    b = sum(len(v) for v in [t['banzo_sup'], t['banzo_inf'], t['diagonais'], t['montantes']])
    assert b == 31 and b + 3 == 2 * t["n_nos"], f"warren: {t['n_nos']}nos {b}barras b+3={b+3} 2j={2*t['n_nos']}"
    assert len(t["diagonais"]) == 16
    assert len(t["montantes"]) == 0
    
    t2 = gera_trelica(20.0, 2.5, 8, "pratt")
    b2 = sum(len(v) for v in [t2['banzo_sup'], t2['banzo_inf'], t2['diagonais'], t2['montantes']])
    assert b2 == 29 and b2 + 3 == 2 * t2["n_nos"], f"pratt: {t2['n_nos']}nos {b2}barras b+3={b2+3} 2j={2*t2['n_nos']}"
    assert len(t2["diagonais"]) == 6
    assert len(t2["montantes"]) == 7
    
    print(f"tesoura self-test PASSED: Warren {t['n_nos']}nos/{b}barras isostatico; "
          f"Pratt {t2['n_nos']}nos/{b2}barras isostatico")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        for tp in ("warren", "pratt"):
            t = gera_trelica(20.0, 2.5, 8, tp)
            b = sum(len(v) for v in [t['banzo_sup'], t['banzo_inf'], t['diagonais'], t['montantes']])
            print(f"{tp.upper()}: {t['n_nos']} nos, {b} barras -> b+3={b+3}, 2j={2*t['n_nos']}")
