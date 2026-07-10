# ============================================================================
# tesoura.py - TRELIÇA DE COBERTURA (tesoura)
# Banzo superior PARABOLICO. Isostatico: b + r = 2j.
# Warren: nos inferiores defasados, sem montantes.
# Pratt: nos inferiores alinhados, montantes + 1 diagonal/painel interno.
# ============================================================================
"""Tesoura (trelica de cobertura). Saidas PT. Unidades: m."""

from __future__ import annotations
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# numpy e check_nbr8800 sao importados SOB DEMANDA (solver/verificacao) para que
# gera_trelica (so geometria, math puro) seja importavel no build (freecadcmd, que
# pode nao ter numpy). Ver resolve_trelica / verifica_tesoura.


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


# ---- solver de esforcos (metodo dos nos, trelica plana isostatica) ----------
def _barras(t):
    """Lista unica de barras (i, j, grupo) na ordem banzo_sup, banzo_inf,
    diagonais, montantes (mesma ordem dos indices retornados por resolve_trelica)."""
    bars = []
    for grp in ("banzo_sup", "banzo_inf", "diagonais", "montantes"):
        for (i, j) in t[grp]:
            bars.append((i, j, grp))
    return bars


def resolve_trelica(t, P_nos):
    """Esforcos axiais da trelica plana ISOSTATICA pelo metodo dos nos (equilibrio
    nodal). P_nos: dict no->(Fx, Fy) em kN. Apoios: no 0 = pino (Rx, Ry) ; no
    n_paineis = rolete (Ry). N>0 = TRACAO. Retorna esforcos por barra + reacoes.
    Sistema quadrado 2j x (b+3) (b + r = 2j, isostatico)."""
    nos = t["nos"]; j = len(nos)
    bars = _barras(t); b = len(bars)
    import numpy as np
    n_ap0, n_apN = 0, t["n_paineis"]
    nx = b + 3
    if 2 * j != nx:
        raise ValueError(f"trelica nao isostatica: 2j={2*j} != b+3={nx}")
    A = np.zeros((2 * j, nx)); f = np.zeros(2 * j)
    for bi, (i, jj, grp) in enumerate(bars):
        (xi, yi), (xj, yj) = nos[i], nos[jj]
        dx, dy = xj - xi, yj - yi
        Lb = math.hypot(dx, dy)
        ex, ey = dx / Lb, dy / Lb
        A[2 * i, bi] += ex; A[2 * i + 1, bi] += ey        # no i: +N e_ij
        A[2 * jj, bi] -= ex; A[2 * jj + 1, bi] -= ey       # no j: -N e_ij
    A[2 * n_ap0, b + 0] = 1.0                              # R0x
    A[2 * n_ap0 + 1, b + 1] = 1.0                          # R0y
    A[2 * n_apN + 1, b + 2] = 1.0                          # RNy
    for no, (Fx, Fy) in P_nos.items():
        f[2 * no] -= Fx; f[2 * no + 1] -= Fy
    x = np.linalg.solve(A, f)
    N = [float(v) for v in x[:b]]
    reac = {n_ap0: (float(x[b + 0]), float(x[b + 1])),
            n_apN: (0.0, float(x[b + 2]))}
    idx = {"idx_banzo_sup": [], "idx_banzo_inf": [], "idx_diagonais": [],
           "idx_montantes": []}
    comp = []
    for bi, (i, jj, grp) in enumerate(bars):
        idx["idx_" + grp].append(bi)
        comp.append(math.hypot(nos[jj][0] - nos[i][0], nos[jj][1] - nos[i][1]))
    return {"N_barras": N, "reacoes": reac, "barras": bars,
            "comprimentos": comp, **idx}


# ---- verificacao das barras (reusa check_nbr8800) ---------------------------
def _props_I(sec):
    """A, r_min (raio de giracao fraco) de um I duplamente simetrico (h,b,tw,tf) m."""
    h, bf, tw, tf = sec
    A = 2.0 * bf * tf + (h - 2.0 * tf) * tw
    Iy = (2.0 * tf * bf ** 3 + (h - 2.0 * tf) * tw ** 3) / 12.0
    r = math.sqrt(Iy / A) if A > 0 else 1e-6
    return A, r


def _n_rd(sec, fy, L, comprimido):
    """Esforco axial resistente (kN) de uma barra: TRACAO = escoamento A*fy/ga1;
    COMPRESSAO = flambagem chi*Q*A*fy/ga1 (K=1). Reusa ck.chi_compressao/fator_Q."""
    import check_nbr8800 as ck
    A, r = _props_I(sec)
    if not comprimido:
        return A * fy / ck.GA1
    lam0 = (1.0 * L / r) / math.pi * math.sqrt(fy / ck.E)
    chi = ck.chi_compressao(lam0)
    try:
        Q = ck.fator_Q(sec, fy)
    except Exception:
        Q = 1.0
    return chi * Q * A * fy / ck.GA1


def verifica_tesoura(cfg):
    """Dimensiona/verifica a tesoura sob a carga de cobertura. cfg: {L, h,
    n_paineis, tipo, w_grav_kN_m (permanente+sobrecarga por m de banzo, >0),
    w_vento_kN_m (sucção, <0), fy, perfil_banzo (h,b,tw,tf m), perfil_diagonal}.
    Combinacoes: gravidade 1,4.w_grav ; vento 1,4.w_vento + 0,9.(-w_grav) (uplift).
    N>0 tracao. Retorna util maxima, barra governante e esforcos por banzo."""
    t = gera_trelica(cfg["L"], cfg["h"], cfg.get("n_paineis", 8),
                     cfg.get("tipo", "warren"))
    n_p = t["n_paineis"]; dx = cfg["L"] / n_p
    fy = cfg.get("fy", 250e3)
    sb, sd = cfg["perfil_banzo"], cfg["perfil_diagonal"]

    def _cargas(w):
        P = {}
        for i in range(n_p + 1):
            trib = dx if 0 < i < n_p else dx / 2.0
            P[i] = (0.0, -w * trib)               # w>0 gravidade (para baixo)
        return P

    combos = [("gravidade", 1.4 * cfg["w_grav_kN_m"]),
              ("vento", 1.4 * cfg.get("w_vento_kN_m", 0.0) + 0.9 * (-cfg["w_grav_kN_m"]))]
    bars = _barras(t)
    sol0 = resolve_trelica(t, _cargas(1.0))
    diag_idx = set(sol0["idx_diagonais"] + sol0["idx_montantes"])
    u_max = 0.0; gov = None; Nsup = 0.0; Ninf = 0.0
    for nome, w in combos:
        sol = resolve_trelica(t, _cargas(w))
        for bi, N in enumerate(sol["N_barras"]):
            sec = sd if bi in diag_idx else sb
            comprimido = N < 0
            Nrd = _n_rd(sec, fy, sol["comprimentos"][bi], comprimido)
            u = abs(N) / Nrd if Nrd > 0 else float("inf")
            if u > u_max:
                u_max = u; gov = {"combo": nome, "barra": bars[bi],
                                  "N_kN": round(N, 1), "u": round(u, 3),
                                  "grupo": bars[bi][2]}
        Nsup = max(Nsup, max(abs(sol["N_barras"][k]) for k in sol["idx_banzo_sup"]))
        Ninf = max(Ninf, max(abs(sol["N_barras"][k]) for k in sol["idx_banzo_inf"]))
    return {"tipo": t["tipo"], "n_paineis": n_p, "h_m": cfg["h"], "L_m": cfg["L"],
            "u_max": round(u_max, 3), "barra_governante": gov,
            "N_banzo_sup_max": round(Nsup, 1), "N_banzo_inf_max": round(Ninf, 1),
            "OK": u_max <= 1.0, "trelica": t}


def relatorio_tesoura_pt(r):
    g = r.get("barra_governante") or {}
    L = ["=" * 66, "PORTICO TRELICADO (TESOURA) - esforcos e verificacao",
         "=" * 66,
         f"  Tipo: {r['tipo']} ; L = {r['L_m']:.1f} m ; h = {r['h_m']:.2f} m ; "
         f"{r['n_paineis']} paineis",
         f"  Banzo superior N_max = {r['N_banzo_sup_max']:.1f} kN (compressao)",
         f"  Banzo inferior N_max = {r['N_banzo_inf_max']:.1f} kN (tracao)",
         f"  Utilizacao maxima = {r['u_max']:.2f} -> "
         f"{'OK' if r['OK'] else 'NAO PASSA'}",
         f"  Barra governante: {g.get('grupo')} N={g.get('N_kN')} kN "
         f"(combo {g.get('combo')}, u={g.get('u')})",
         "  Metodo dos nos (isostatica); barras verificadas por check_nbr8800.",
         "  Perfis de banzo/diagonal = A CONFIRMAR (gate).", "=" * 66]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


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
