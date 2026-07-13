# ============================================================================
# tesoura.py - TRELIÇA DE COBERTURA (tesoura)
# Banzo superior RETO em DUAS AGUAS (segue a inclinacao do telhado ate a cumeeira),
# nao parabolico (bowstring): assim as tercas apoiam NOS NOS do banzo (carga so
# nodal -> metodo dos nos valido; parecer Q5). Isostatico: b + r = 2j.
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
    """Gera trelica isostatica. L (m), h (m) no centro. n_paineis deve ser PAR:
    a cumeeira (x=L/2) precisa cair num NO do banzo superior; se impar, o apice
    fica no meio de uma barra e reintroduz flexao (invalida o metodo dos nos)."""
    if n_paineis % 2 != 0:
        raise ValueError(
            "n_paineis deve ser PAR (cumeeira em no; impar poe o apice no meio da "
            "barra e reintroduz flexao). Recebido: %s" % n_paineis)
    dx = L / n_paineis
    nos = []
    # Banzo superior RETO em DUAS AGUAS: sobe do beiral (y=0) ate a cumeeira (y=h no
    # centro) pela inclinacao do telhado (slope = 2h/L), simetrico. Assim os nos do
    # banzo ficam SOBRE o plano do telhado -> as tercas apoiam nos nos (parecer Q5).
    for i in range(n_paineis + 1):
        x = i * dx
        y = (2.0 * h / L) * (x if x <= L / 2.0 else (L - x)) if L > 0 else 0.0
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


# ---- carregamento nodal do banzo superior -----------------------------------
def _trib_sup(t):
    """Comprimento tributario INCLINADO de cada no do banzo superior (0..n_p):
    metade do segmento de banzo de cada lado (nas pontas, so um lado)."""
    nos = t["nos"]; n_p = t["n_paineis"]
    seg = [math.hypot(nos[i + 1][0] - nos[i][0], nos[i + 1][1] - nos[i][1])
           for i in range(n_p)]
    trib = [0.0] * (n_p + 1)
    for i in range(n_p + 1):
        esq = seg[i - 1] if i > 0 else 0.0
        dir_ = seg[i] if i < n_p else 0.0
        trib[i] = (esq + dir_) / 2.0
    return trib, seg


def _gamma_g_dead(wv):
    """gamma_g do peso permanente (NBR 8681) conforme o SENTIDO do vento no no:
    - vento de SUCCAO (wv<=0, uplift): peso e FAVORAVEL (opoe o arranque) -> 0,9;
    - vento de PRESSAO (wv>0, p/ baixo): peso e DESFAVORAVEL (soma) -> 1,4.
    (parecer item 41, pt.3: nao usar 0,9 hardcoded se o vento vira pressao.)"""
    return 0.9 if wv <= 0.0 else 1.4


def _P_vento_zonas(t, trib, w_barl, w_sot, w_dead, direction=1):
    """Cargas nodais da combinacao com vento POR AGUA (zona). Cada metade do banzo
    superior recebe o Cpe da sua agua (NBR 6123 Tabela 5, barlavento EF / sotavento
    GH), atuando SIMULTANEAMENTE. w_barl/w_sot: vento por m de banzo (kN/m, <0 =
    uplift/succao, >0 = pressao). direction=+1: agua ESQUERDA=barlavento, DIREITA=
    sotavento; -1: espelhado.
    Combinacao (NBR 8681): 1,4 w_vento(agua) + gamma_g w_dead, com gamma_g=0,9
    (succao, peso favoravel) ou 1,4 (pressao, peso desfavoravel).
    Cumeeira (x=L/2): area tributaria = metade barlavento + metade sotavento -> carga
    da MEDIA (w_barl+w_sot)/2 (fiel a fisica; parecer item 41 pt.1).
    Convencao: w>0 -> carga p/ BAIXO (Fy=-w.trib)."""
    nos = t["nos"]; n_p = t["n_paineis"]; L = t["L"]
    P = {}
    for i in range(n_p + 1):
        x = nos[i][0]
        if abs(x - L / 2.0) < 1e-9:
            wv = (w_barl + w_sot) / 2.0                   # cumeeira: media das aguas
        else:
            esq = x < L / 2.0
            barlavento = esq if direction >= 0 else (not esq)
            wv = w_barl if barlavento else w_sot
        w_no = 1.4 * wv + _gamma_g_dead(wv) * w_dead
        P[i] = (0.0, -w_no * trib[i])
    return P


def cargas_vento_zonas(cfg, w_barl, w_sot, direction=1):
    """Wrapper testavel: monta a trelica de cfg e devolve as cargas nodais de vento
    por zona (ver _P_vento_zonas)."""
    t = gera_trelica(cfg["L"], cfg["h"], cfg.get("n_paineis", 8),
                     cfg.get("tipo", "warren"))
    trib, _ = _trib_sup(t)
    w_dead = cfg.get("w_dead_kN_m", cfg["w_grav_kN_m"])
    return _P_vento_zonas(t, trib, w_barl, w_sot, w_dead, direction)


# ---- verificacao das barras (reusa check_nbr8800) ---------------------------
def _props_I(sec):
    """A, rx (raio de giracao forte), ry (fraco) de um I duplamente simetrico
    (h,b,tw,tf) m. rx = no plano da trelica ; ry = fora do plano (banzo comprimido)."""
    h, bf, tw, tf = sec
    A = 2.0 * bf * tf + (h - 2.0 * tf) * tw
    Ix = (bf * h ** 3 - (bf - tw) * (h - 2.0 * tf) ** 3) / 12.0
    Iy = (2.0 * tf * bf ** 3 + (h - 2.0 * tf) * tw ** 3) / 12.0
    rx = math.sqrt(Ix / A) if A > 0 else 1e-6
    ry = math.sqrt(Iy / A) if A > 0 else 1e-6
    return A, rx, ry


def _nc_rd(sec, fy, L_plano, L_fora):
    """COMPRESSAO (kN): flambagem chi*Q*A*fy/ga1. Verifica os DOIS eixos (parecer):
    - no plano da trelica: esbeltez L_plano/rx (comprimento da barra entre nos);
    - FORA do plano: L_fora/ry (distancia entre pontos TRAVADOS - tercas/contravento,
      nem sempre = comprimento da barra). Governa o MAIOR indice de esbeltez (menor chi)."""
    import check_nbr8800 as ck
    A, rx, ry = _props_I(sec)
    lam_x = (L_plano / rx) / math.pi * math.sqrt(fy / ck.E)
    lam_y = (L_fora / ry) / math.pi * math.sqrt(fy / ck.E)
    chi = min(ck.chi_compressao(lam_x), ck.chi_compressao(lam_y))
    try:
        Q = ck.fator_Q(sec, fy)
    except Exception:
        Q = 1.0
    return chi * Q * A * fy / ck.GA1


def _nt_rd(sec, fy, fu, Ct=1.0, area_furos=0.0):
    """TRACAO (kN): MENOR entre escoamento da secao BRUTA (5.2.2 A*fy/ga1) e RUPTURA
    da secao LIQUIDA (5.2.3 Ae*fu/ga2), Ae = Ct*(A - area_furos). Ct = coef. de
    reducao por shear lag (ligacao parcial/parafusada); area_furos = area dos furos
    na secao critica (parafusada). Parecer: a ruptura liquida costuma governar o
    banzo tracionado parafusado."""
    import check_nbr8800 as ck
    GA2 = getattr(ck, "GA2", 1.35)                    # NBR 8800: ruptura (1,35)
    A, _, _ = _props_I(sec)
    N_esc = A * fy / ck.GA1
    An = max(A - area_furos, 0.0)
    N_rup = Ct * An * fu / GA2
    return min(N_esc, N_rup)


def verifica_tesoura(cfg):
    """Dimensiona/verifica a tesoura sob a carga de cobertura. cfg: {L, h,
    n_paineis, tipo, w_grav_kN_m (permanente+sobrecarga por m de banzo, >0),
    w_vento_kN_m (sucção, <0), fy, fu, perfil_banzo (h,b,tw,tf m), perfil_diagonal,
    Lb_y_sup (m; travamento FORA do plano do banzo superior - terças; default =
    painel inclinado, i.e. cada no travado), Ct (shear lag, default 1.0),
    area_furos (m2, secao critica parafusada, default 0)}.
    Combinacoes (NBR 8681): gravidade 1,4.w_grav ; vento (uplift) 1,4.w_vento +
    0,9.w_dead, onde w_dead = carga PERMANENTE estabilizante (>0, p/ baixo) e
    w_vento e a succao (<0, p/ cima) - vetores OPOSTOS. A sobrecarga Q NAO estabiliza
    o uplift (carga variavel pode estar ausente): w_dead exclui Q (default = w_grav
    p/ retrocompatibilidade se w_dead_kN_m nao for informado).
    Convencao do solver (_cargas): w>0 -> carga p/ BAIXO (Fy = -w.trib).
    N>0 tracao. Carga distribuida -> NODAL por trib. inclinada (metodo dos nos).
    Retorna util maxima, barra governante e esforcos por banzo."""
    t = gera_trelica(cfg["L"], cfg["h"], cfg.get("n_paineis", 8),
                     cfg.get("tipo", "warren"))
    n_p = t["n_paineis"]
    fy = cfg.get("fy", 250e3); fu = cfg.get("fu", 400e3)
    Ct = cfg.get("Ct", 1.0); area_furos = cfg.get("area_furos", 0.0)
    sb, sd = cfg["perfil_banzo"], cfg["perfil_diagonal"]
    nos = t["nos"]
    trib, seg = _trib_sup(t)
    # travamento fora do plano do banzo superior (default: cada no travado ->
    # maior segmento inclinado adjacente)
    Lby_sup = cfg.get("Lb_y_sup", max(seg))

    def _cargas(w):
        return {i: (0.0, -w * trib[i]) for i in range(n_p + 1)}   # w>0 p/ baixo

    # w_dead = permanente estabilizante (exclui Q); default = w_grav (retrocompat).
    w_dead = cfg.get("w_dead_kN_m", cfg["w_grav_kN_m"])
    # Combinacoes (NBR 8681): gravidade + uplift. O uplift pode vir POR ZONA (agua):
    # cfg["w_vento_zonas"]=(w_barl,w_sot) -> NBR 6123 Tabela 5 por agua, ENVELOPE das
    # 2 direcoes de vento. Ausente -> escalar w_vento_kN_m uniforme (back-compat).
    load_cases = [("gravidade", _cargas(1.4 * cfg["w_grav_kN_m"]))]
    zonas = cfg.get("w_vento_zonas")
    if zonas is not None:
        wb, ws = zonas
        load_cases.append(("vento(barl.esq)", _P_vento_zonas(t, trib, wb, ws, w_dead, +1)))
        load_cases.append(("vento(barl.dir)", _P_vento_zonas(t, trib, wb, ws, w_dead, -1)))
    else:
        load_cases.append(("vento", _cargas(1.4 * cfg.get("w_vento_kN_m", 0.0)
                                            + 0.9 * w_dead)))
    bars = _barras(t)
    sol0 = resolve_trelica(t, _cargas(1.0))
    diag_idx = set(sol0["idx_diagonais"] + sol0["idx_montantes"])
    sup_idx = set(sol0["idx_banzo_sup"])
    u_max = 0.0; gov = None; Nsup = 0.0; Ninf = 0.0
    for nome, P in load_cases:
        sol = resolve_trelica(t, P)
        for bi, N in enumerate(sol["N_barras"]):
            sec = sd if bi in diag_idx else sb
            Lbar = sol["comprimentos"][bi]
            if N < 0:                                        # COMPRESSAO (2 eixos)
                Lfora = Lby_sup if bi in sup_idx else Lbar   # so o banzo sup usa Lby
                Nrd = _nc_rd(sec, fy, Lbar, Lfora)
            else:                                            # TRACAO (escoam + ruptura)
                Nrd = _nt_rd(sec, fy, fu, Ct, area_furos)
            u = abs(N) / Nrd if Nrd > 0 else float("inf")
            if u > u_max:
                u_max = u; gov = {"combo": nome, "barra": bars[bi],
                                  "N_kN": round(N, 1), "u": round(u, 3),
                                  "grupo": bars[bi][2],
                                  "estado": "compressao" if N < 0 else "tracao"}
        Nsup = max(Nsup, max(abs(sol["N_barras"][k]) for k in sol["idx_banzo_sup"]))
        Ninf = max(Ninf, max(abs(sol["N_barras"][k]) for k in sol["idx_banzo_inf"]))
    return {"tipo": t["tipo"], "n_paineis": n_p, "h_m": cfg["h"], "L_m": cfg["L"],
            "u_max": round(u_max, 3), "barra_governante": gov,
            "N_banzo_sup_max": round(Nsup, 1), "N_banzo_inf_max": round(Ninf, 1),
            "Lb_y_sup_m": round(Lby_sup, 3), "OK": u_max <= 1.0, "trelica": t}


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
         f"({g.get('estado')}, combo {g.get('combo')}, u={g.get('u')})",
         f"  Travamento fora do plano do banzo sup Lb_y = {r.get('Lb_y_sup_m')} m",
         "  Banzo sup RETO em duas aguas (tercas apoiam nos nos); metodo dos nos",
         "  (isostatica). Tracao = escoam.(bruta)+ruptura(liquida); compressao = 2 eixos.",
         "  Perfis, Ct(shear lag), area de furos e Lb_y = A CONFIRMAR (gate).", "=" * 66]
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

    # n_paineis IMPAR bloqueia (cumeeira cairia no meio da barra -> flexao)
    try:
        gera_trelica(20.0, 2.5, 7, "warren"); raise AssertionError("impar deveria falhar")
    except ValueError:
        pass

    # GEOMETRIA duas-aguas RETA (parecer Q5): banzo sup sobe linear ate a cumeeira
    # (no central, y=h) e desce; nao parabola. Inclinacao constante em cada agua.
    nos = t["nos"]
    assert abs(nos[4][1] - 2.5) < 1e-9, "cumeeira (no central) deve ter y=h"
    s1 = (nos[1][1] - nos[0][1]) / (nos[1][0] - nos[0][0])
    s2 = (nos[2][1] - nos[1][1]) / (nos[2][0] - nos[1][0])
    assert abs(s1 - s2) < 1e-9, "agua esquerda deve ser RETA (inclinacao constante)"
    assert abs(s1 - 2 * 2.5 / 20.0) < 1e-9, "inclinacao = 2h/L (telhado)"

    # EQUILIBRIO GLOBAL (metodo dos nos): soma das reacoes = carga aplicada.
    import numpy as np  # noqa
    P = {i: (0.0, -10.0) for i in range(t["n_paineis"] + 1)}   # 10 kN/no p/ baixo
    sol = resolve_trelica(t, P)
    Rx = sum(r[0] for r in sol["reacoes"].values())
    Ry = sum(r[1] for r in sol["reacoes"].values())
    Wtot = 10.0 * (t["n_paineis"] + 1)
    assert abs(Rx) < 1e-6, f"SFx: reacao horizontal residual {Rx}"
    assert abs(Ry - Wtot) < 1e-6, f"SFy: {Ry} != carga {Wtot}"
    # simetria -> reacoes verticais iguais nos 2 apoios
    assert abs(sol["reacoes"][0][1] - sol["reacoes"][t["n_paineis"]][1]) < 1e-6
    # banzo inferior TRACIONA, banzo superior COMPRIME sob gravidade
    assert min(sol["N_barras"][k] for k in sol["idx_banzo_sup"]) < 0
    assert max(sol["N_barras"][k] for k in sol["idx_banzo_inf"]) > 0

    # VERIFICACAO NBR: tracao (escoam+ruptura liquida) e compressao (2 eixos)
    perfil = (0.20, 0.10, 0.006, 0.008)      # I: h,b,tw,tf (m)
    r = verifica_tesoura({"L": 20.0, "h": 2.5, "n_paineis": 8, "tipo": "warren",
                          "w_grav_kN_m": 3.0, "w_vento_kN_m": -2.0, "fy": 250e3,
                          "fu": 400e3, "perfil_banzo": perfil, "perfil_diagonal": perfil})
    assert 0 < r["u_max"] and r["barra_governante"]["estado"] in ("tracao", "compressao")
    # ruptura liquida (parafusado) reduz N_t,Rd -> util maior que so escoamento
    r2 = verifica_tesoura({"L": 20.0, "h": 2.5, "n_paineis": 8, "tipo": "warren",
                           "w_grav_kN_m": 3.0, "w_vento_kN_m": -2.0, "fy": 250e3,
                           "fu": 400e3, "perfil_banzo": perfil, "perfil_diagonal": perfil,
                           "Ct": 0.85, "area_furos": 4e-4})
    assert r2["u_max"] >= r["u_max"] - 1e-9
    # Lb_y_sup maior (menos travamento) -> compressao do banzo sup mais penalizada
    r3 = verifica_tesoura({"L": 20.0, "h": 2.5, "n_paineis": 8, "tipo": "warren",
                           "w_grav_kN_m": 3.0, "w_vento_kN_m": -2.0, "fy": 250e3,
                           "fu": 400e3, "perfil_banzo": perfil, "perfil_diagonal": perfil,
                           "Lb_y_sup": 6.0})
    assert r3["u_max"] >= r["u_max"] - 1e-9

    print(f"tesoura self-test PASSED: Warren {t['n_nos']}nos/{b}barras isostatico; "
          f"Pratt {t2['n_nos']}nos/{b2}barras isostatico; equilibrio global OK; "
          f"duas-aguas reta; NBR tracao(ruptura)+compressao(2 eixos) OK")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        for tp in ("warren", "pratt"):
            t = gera_trelica(20.0, 2.5, 8, tp)
            b = sum(len(v) for v in [t['banzo_sup'], t['banzo_inf'], t['diagonais'], t['montantes']])
            print(f"{tp.upper()}: {t['n_nos']} nos, {b} barras -> b+3={b+3}, 2j={2*t['n_nos']}")
