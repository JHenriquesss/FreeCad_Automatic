# Memoria de Calculo - Scripts + Resultados (Galpao 20x10)

CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL.
Cada script abaixo vem seguido do seu resultado de execucao, para conferencia
matematica manual. Codigo em ingles; saidas em portugues.

---

## frame2d.py
_Solver de portico 2D (metodo da rigidez direta) - com auto-teste_

```python
"""2D frame solver (direct stiffness method) - transparent and auditable.

For the transverse portal frame of the galpao. 3 DOF per node (u, v, rotation).
Beam-column elements with axial + bending (Euler-Bernoulli). Supports nodal
loads, member uniformly distributed loads given in GLOBAL components (wx, wy per
unit length), and pinned/fixed/roller supports.

This is a standard matrix structural analysis. It COMPUTES; it does not certify.
The responsible engineer must review the method and the results. Validated below
against closed-form cases (run `python frame2d.py`).

References: any structural analysis text (e.g. matrix stiffness method); member
capacity checks per ABNT NBR 8800 are done in a separate module, not here.
"""

from __future__ import annotations

import math

import numpy as np


class Frame2D:
    def __init__(self):
        self.nodes = []          # list of (x, y)
        self.elements = []       # list of dict: i, j, E, A, I
        self.supports = {}       # node -> (fix_u, fix_v, fix_rot) booleans
        self.nodal_loads = {}    # node -> (Fx, Fy, M)
        self.member_udl = {}     # elem index -> (wx, wy) global per unit length

    def add_node(self, x, y):
        self.nodes.append((float(x), float(y)))
        return len(self.nodes) - 1

    def add_element(self, i, j, E, A, I):
        self.elements.append({"i": i, "j": j, "E": E, "A": A, "I": I})
        return len(self.elements) - 1

    def add_support(self, node, u=False, v=False, rot=False):
        self.supports[node] = (u, v, rot)

    def add_nodal_load(self, node, Fx=0.0, Fy=0.0, M=0.0):
        fx, fy, m = self.nodal_loads.get(node, (0, 0, 0))
        self.nodal_loads[node] = (fx + Fx, fy + Fy, m + M)

    def add_member_udl(self, elem, wx=0.0, wy=0.0):
        gx, gy = self.member_udl.get(elem, (0, 0))
        self.member_udl[elem] = (gx + wx, gy + wy)

    # --- element helpers -----------------------------------------------------
    def _geom(self, e):
        (xi, yi), (xj, yj) = self.nodes[e["i"]], self.nodes[e["j"]]
        dx, dy = xj - xi, yj - yi
        L = math.hypot(dx, dy)
        return L, dx / L, dy / L   # length, cos, sin

    def _k_local(self, e, L):
        E, A, I = e["E"], e["A"], e["I"]
        EA_L = E * A / L
        EI = E * I
        k = np.zeros((6, 6))
        k[0, 0] = k[3, 3] = EA_L
        k[0, 3] = k[3, 0] = -EA_L
        a = 12 * EI / L**3
        b = 6 * EI / L**2
        c = 4 * EI / L
        d = 2 * EI / L
        k[1, 1] = k[4, 4] = a
        k[1, 4] = k[4, 1] = -a
        k[1, 2] = k[2, 1] = b
        k[1, 5] = k[5, 1] = b
        k[2, 4] = k[4, 2] = -b
        k[4, 5] = k[5, 4] = -b
        k[2, 2] = k[5, 5] = c
        k[2, 5] = k[5, 2] = d
        return k

    def _T(self, cs, sn):
        T = np.zeros((6, 6))
        R = np.array([[cs, sn, 0], [-sn, cs, 0], [0, 0, 1.0]])
        T[0:3, 0:3] = R
        T[3:6, 3:6] = R
        return T

    def _fef_local(self, e, L, cs, sn):
        """Fixed-end forces (local) from a global UDL (wx, wy)."""
        wx, wy = self.member_udl.get(self._eidx(e), (0.0, 0.0))
        if wx == 0 and wy == 0:
            return np.zeros(6)
        # rotate global load into local axes
        w_ax = wx * cs + wy * sn        # along member
        w_pp = -wx * sn + wy * cs       # perpendicular
        f = np.zeros(6)
        f[0] = f[3] = w_ax * L / 2.0
        f[1] = f[4] = w_pp * L / 2.0
        f[2] = w_pp * L**2 / 12.0
        f[5] = -w_pp * L**2 / 12.0
        return f

    def _eidx(self, e):
        return self.elements.index(e)

    # --- solve ---------------------------------------------------------------
    def solve(self):
        n = len(self.nodes)
        ndof = 3 * n
        K = np.zeros((ndof, ndof))
        F = np.zeros(ndof)

        # nodal loads
        for nd, (fx, fy, m) in self.nodal_loads.items():
            F[3 * nd:3 * nd + 3] += [fx, fy, m]

        fef_store = {}
        for e in self.elements:
            L, cs, sn = self._geom(e)
            k_loc = self._k_local(e, L)
            T = self._T(cs, sn)
            k_glob = T.T @ k_loc @ T
            dofs = [3 * e["i"], 3 * e["i"] + 1, 3 * e["i"] + 2,
                    3 * e["j"], 3 * e["j"] + 1, 3 * e["j"] + 2]
            for a in range(6):
                for b in range(6):
                    K[dofs[a], dofs[b]] += k_glob[a, b]
            # equivalent nodal loads from member UDL
            fef = self._fef_local(e, L, cs, sn)
            fef_store[self._eidx(e)] = (fef, T, k_loc, dofs)
            F_eq_global = T.T @ fef
            for a in range(6):
                F[dofs[a]] -= F_eq_global[a]

        # boundary conditions
        fixed = []
        for nd, (u, v, r) in self.supports.items():
            if u:
                fixed.append(3 * nd)
            if v:
                fixed.append(3 * nd + 1)
            if r:
                fixed.append(3 * nd + 2)
        free = [d for d in range(ndof) if d not in fixed]

        d = np.zeros(ndof)
        Kff = K[np.ix_(free, free)]
        Ff = F[free]
        d[free] = np.linalg.solve(Kff, Ff)

        # member end forces (local): f = k_loc*T*d + fef
        member_forces = {}
        for idx, (fef, T, k_loc, dofs) in fef_store.items():
            d_e = d[dofs]
            f_loc = k_loc @ (T @ d_e) + fef
            # local: [N_i, V_i, M_i, N_j, V_j, M_j]
            member_forces[idx] = f_loc
        return d, member_forces


# ---------------------------------------------------------------------------
# Validation against closed-form solutions
# ---------------------------------------------------------------------------
def _selftest():
    E = 200e6  # kPa (200 GPa) - consistent units: kN, m
    # 1) Cantilever, length L, tip point load P -> tip defl = P L^3 / 3EI
    L, I, A, P = 3.0, 1e-4, 1e-2, 10.0
    f = Frame2D()
    n0 = f.add_node(0, 0)
    n1 = f.add_node(L, 0)
    f.add_element(n0, n1, E, A, I)
    f.add_support(n0, True, True, True)
    f.add_nodal_load(n1, Fy=-P)
    d, mf = f.solve()
    tip = d[3 * n1 + 1]
    exact = -P * L**3 / (3 * E * I)
    assert abs(tip - exact) / abs(exact) < 1e-6, (tip, exact)
    base_M = mf[0][2]
    exact_baseM = P * L
    assert abs(abs(base_M) - exact_baseM) / exact_baseM < 1e-6, (base_M, exact_baseM)

    # 2) Simply supported beam, UDL w -> midspan M = w L^2 / 8
    L, w = 4.0, 5.0
    f = Frame2D()
    a = f.add_node(0, 0)
    mid = f.add_node(L / 2, 0)
    b = f.add_node(L, 0)
    e0 = f.add_element(a, mid, E, A, I)
    e1 = f.add_element(mid, b, E, A, I)
    f.add_support(a, True, True, False)
    f.add_support(b, False, True, False)
    f.add_member_udl(e0, wy=-w)
    f.add_member_udl(e1, wy=-w)
    d, mf = f.solve()
    m_mid = abs(mf[0][5])  # moment at 'mid' end of element 0
    exact_m = w * L**2 / 8.0
    assert abs(m_mid - exact_m) / exact_m < 1e-3, (m_mid, exact_m)
    print("frame2d self-test PASSED")
    print(f"  cantilever tip: {tip:.6e} m (exact {exact:.6e})")
    print(f"  cantilever base M: {abs(base_M):.4f} kN.m (exact {exact_baseM:.4f})")
    print(f"  SS beam mid M: {m_mid:.4f} kN.m (exact {exact_m:.4f})")


if __name__ == "__main__":
    _selftest()
```

### Resultado (execucao de `frame2d.py`)

```
frame2d self-test PASSED
  cantilever tip: -4.500000e-03 m (exact -4.500000e-03)
  cantilever base M: 30.0000 kN.m (exact 30.0000)
  SS beam mid M: 10.0000 kN.m (exact 10.0000)
```

---

## vento_nbr6123.py
_Vento NBR 6123 (coeficientes das tabelas reais)_

```python
"""Wind loads per ABNT NBR 6123/1988 for the galpao transverse frame.

Coefficients are the ACTUAL table values (Tabela 1, 4, 5 and item 6.2), read from
the standard, with clause references. Transparent and auditable. The zone/alpha
mapping and the dominant-opening area ratio are flagged for engineer confirmation.
Outputs in Portuguese. Computes only; pending engineer review. Units: m, kN.

Building: a=20 (length), b=10 (span/width), h=6 (eave). h/b=0.6 ; a/b=2.
Transverse frame = wind perpendicular to the ridge (hits the long 20 m walls).
"""

from __future__ import annotations


def s2_factor(cat, classe, z):
    """NBR 6123 Tabela 1 (categoria II)."""
    tbl = {
        ("II", "A"): (1.00, 1.00, 0.085),
        ("II", "B"): (1.00, 0.98, 0.09),
        ("II", "C"): (1.00, 0.95, 0.10),
    }
    b, Fr, p = tbl[(cat, classe)]
    return b, Fr, p, b * Fr * (z / 10.0) ** p


def _interp(x, x0, x1, y0, y1):
    return y0 + (x - x0) / (x1 - x0) * (y1 - y0)


def cpe_paredes():
    """NBR 6123 Tabela 4, paredes. Vento transversal atinge as paredes longas
    (a=20). Bloco 1/2<h/b<=3/2, linha 2<=a/b<=4, incidencia alpha=90 (faces A,B).
    A = barlavento, B = sotavento."""
    return {"parede_barlavento": +0.70, "parede_sotavento": -0.60}


def cpe_telhado(theta_graus=5.71):
    """NBR 6123 Tabela 5, telhado duas aguas. Bloco 1/2<h/b<=3/2, alpha=0
    (vento perpendicular a cumeeira). Colunas EG (agua barlavento) e FH (agua
    sotavento). Interpola theta entre 5 e 10 graus.
    5 graus:  EG=-0,9  FH=-0,6 ; 10 graus: EG=-0,8  FH=-0,6."""
    eg = _interp(theta_graus, 5.0, 10.0, -0.9, -0.8)
    fh = _interp(theta_graus, 5.0, 10.0, -0.6, -0.6)
    return {"cobertura_barlavento": round(eg, 2), "cobertura_sotavento": round(fh, 2)}


def cpi_cases():
    """NBR 6123 item 6.2.5-c: PORTAO = abertura dominante no oitao.
    - Portao a barlavento (vento no oitao): Cpi = +0,1 a +0,8 conforme a razao
      (area do portao / area das demais aberturas sob succao). Adotado +0,8
      (conservador, razao >=6) - A CONFIRMAR com a razao real das aberturas.
    - Portao a sotavento: Cpi = Cpe da face de sotavento (Tabela 4) = -0,6.
    Consideram-se ambos; o engenheiro escolhe/refina."""
    return {"portao_barlavento": +0.80, "portao_sotavento": -0.60}


def compute(v0=40.0, cat="II", classe="B", s1=1.0, s3=0.95, z=6.5, theta=5.71):
    b, Fr, p, s2 = s2_factor(cat, classe, z)
    vk = v0 * s1 * s2 * s3
    q = 0.613 * vk ** 2 / 1000.0
    cpe = {**cpe_paredes(), **cpe_telhado(theta)}
    cpi = cpi_cases()
    net = {}
    for cname, cpiv in cpi.items():
        net[cname] = {s: round(cpe[s] - cpiv, 2) for s in cpe}
    return {"v0": v0, "cat": cat, "classe": classe, "s1": s1, "s2": round(s2, 3),
            "s3": s3, "Fr": Fr, "p": p, "z": z, "theta": theta,
            "vk": round(vk, 2), "q_kN_m2": round(q, 3),
            "cpe": cpe, "cpi_cases": cpi, "net": net}


def relatorio_pt(r):
    L = []
    L.append("VENTO (ABNT NBR 6123/1988)")
    L.append(f"  V0 = {r['v0']:.0f} m/s ; Categoria {r['cat']} ; Classe {r['classe']}")
    L.append(f"  S1 = {r['s1']:.2f} (topografia plana) ; S3 = {r['s3']:.2f} (galpao deposito)")
    L.append(f"  S2 = 1,00*{r['Fr']:.2f}*({r['z']:.1f}/10)^{r['p']:.3f} = {r['s2']:.3f}")
    L.append(f"  Vk = {r['vk']:.2f} m/s ; q = 0,613*Vk^2 = {r['q_kN_m2']:.3f} kN/m2")
    L.append(f"  Telhado theta = {r['theta']:.2f} graus (10%) ; h/b=0,6 ; a/b=2")
    L.append("  Cpe (Tabela 4 paredes alpha=90 ; Tabela 5 telhado alpha=0):")
    for s, v in r["cpe"].items():
        L.append(f"    {s.replace('_',' ')}: {v:+.2f}")
    L.append("  Cpi (item 6.2.5-c, PORTAO como abertura dominante):")
    for k, v in r["cpi_cases"].items():
        L.append(f"    {k.replace('_',' ')}: {v:+.2f}")
    L.append("  Cp liquido = Cpe - Cpi e pressao (kN/m2):")
    for caso, d in r["net"].items():
        L.append(f"    caso {caso.replace('_',' ')}:")
        for s, v in d.items():
            L.append(f"      {s.replace('_',' ')}: {v:+.2f}  ({v*r['q_kN_m2']:+.3f} kN/m2)")
    L.append("  [A CONFIRMAR: classe (20 m), S3=0,95, mapeamento de zonas/alpha e")
    L.append("   razao de areas das aberturas para o Cpi do portao (6.2.5-c).]")
    return "\n".join(L)


if __name__ == "__main__":
    print(relatorio_pt(compute()))
```

### Resultado (execucao de `vento_nbr6123.py`)

```
VENTO (ABNT NBR 6123/1988)
  V0 = 40 m/s ; Categoria II ; Classe B
  S1 = 1.00 (topografia plana) ; S3 = 0.95 (galpao deposito)
  S2 = 1,00*0.98*(6.5/10)^0.090 = 0.943
  Vk = 35.82 m/s ; q = 0,613*Vk^2 = 0.787 kN/m2
  Telhado theta = 5.71 graus (10%) ; h/b=0,6 ; a/b=2
  Cpe (Tabela 4 paredes alpha=90 ; Tabela 5 telhado alpha=0):
    parede barlavento: +0.70
    parede sotavento: -0.60
    cobertura barlavento: -0.89
    cobertura sotavento: -0.60
  Cpi (item 6.2.5-c, PORTAO como abertura dominante):
    portao barlavento: +0.80
    portao sotavento: -0.60
  Cp liquido = Cpe - Cpi e pressao (kN/m2):
    caso portao barlavento:
      parede barlavento: -0.10  (-0.079 kN/m2)
      parede sotavento: -1.40  (-1.102 kN/m2)
      cobertura barlavento: -1.69  (-1.330 kN/m2)
      cobertura sotavento: -1.40  (-1.102 kN/m2)
    caso portao sotavento:
      parede barlavento: +1.30  (+1.023 kN/m2)
      parede sotavento: +0.00  (+0.000 kN/m2)
      cobertura barlavento: -0.29  (-0.228 kN/m2)
      cobertura sotavento: +0.00  (+0.000 kN/m2)
  [A CONFIRMAR: classe (20 m), S3=0,95, mapeamento de zonas/alpha e
   razao de areas das aberturas para o Cpi do portao (6.2.5-c).]
```

---

## galpao_portico.py
_Analise do portico + combinacoes NBR 8800 + memoria_

```python
"""Transverse portal-frame analysis of the galpao + Portuguese calc memory.

Uses the validated frame2d solver and the NBR 6123 wind module. Linear-elastic,
first-order (note: the engineer must confirm whether 2nd-order/sway effects
govern - NBR 8800). Load cases are combined by superposition. Output memory is in
Portuguese for direct review. Computes only; pending engineer review.

Frame plane: horizontal = building span Y, vertical = Z. Pinned bases.
Units: m, kN.
"""

from __future__ import annotations

import math
import os

import frame2d as f2d
import vento_nbr6123 as vento

# ---- geometry (transverse frame) -------------------------------------------
SPAN = 10.0
EAVE = 6.0
RIDGE = 6.5
BAY = 5.0                     # tributary width (internal frame)
THETA = (RIDGE - EAVE) / (SPAN / 2)   # slope of rafter (rise/run) = 0.1
COS = 1.0 / math.hypot(1.0, THETA)    # cos of rafter angle

E = 200e6                     # kN/m2 (200 GPa)
# placeholder sections (NOT verified): HEA200 columns, HEA180 rafters
A_COL, I_COL = 53.8e-4, 3692e-8       # m2, m4  (HEA200)
A_RAF, I_RAF = 45.3e-4, 2510e-8       # m2, m4  (HEA180)

# ---- loads (kN/m2 areal, and member self weight kN/m) ----------------------
G_ROOF = 0.27                 # cladding + purlins + suspended (areal)
RAFTER_SELF = 0.35            # HEA180 ~35.5 kg/m
Q_ROOF = 0.25                 # roof live / maintenance


def _frame():
    fr = f2d.Frame2D()
    n0 = fr.add_node(0.0, 0.0)          # left base
    n1 = fr.add_node(0.0, EAVE)         # left eave
    n2 = fr.add_node(SPAN / 2, RIDGE)   # ridge
    n3 = fr.add_node(SPAN, EAVE)        # right eave
    n4 = fr.add_node(SPAN, 0.0)         # right base
    eColL = fr.add_element(n0, n1, E, A_COL, I_COL)
    eRafL = fr.add_element(n1, n2, E, A_RAF, I_RAF)
    eRafR = fr.add_element(n2, n3, E, A_RAF, I_RAF)
    eColR = fr.add_element(n3, n4, E, A_COL, I_COL)
    fr.add_support(n0, u=True, v=True)  # pinned
    fr.add_support(n4, u=True, v=True)
    return fr, dict(n1=n1, n2=n2, colL=eColL, rafL=eRafL, rafR=eRafR, colR=eColR)


def _run(load_fn):
    fr, ix = _frame()
    load_fn(fr, ix)
    d, mf = fr.solve()
    return d, mf, ix


def case_G(fr, ix):
    wy = -(G_ROOF * BAY * COS + RAFTER_SELF)   # vertical UDL on rafters (down)
    fr.add_member_udl(ix["rafL"], wy=wy)
    fr.add_member_udl(ix["rafR"], wy=wy)


def case_Q(fr, ix):
    wy = -(Q_ROOF * BAY * COS)
    fr.add_member_udl(ix["rafL"], wy=wy)
    fr.add_member_udl(ix["rafR"], wy=wy)


def _wind_case(cpi_key):
    """Return a load function for a wind sub-case (internal pressure sign)."""
    r = vento.compute()
    q = r["q_kN_m2"]
    net = r["net"][cpi_key]

    def apply(fr, ix):
        # Walls: net pressure (Cpe-Cpi) acts INWARD on each wall. Inward is +Y for
        # the left (windward) wall and -Y for the right (leeward) wall, so the
        # leeward term is negated. Both windward pressure and leeward suction push
        # the frame in the wind direction (+Y).
        fr.add_member_udl(ix["colL"], wx=+net["parede_barlavento"] * q * BAY)
        fr.add_member_udl(ix["colR"], wx=-net["parede_sotavento"] * q * BAY)
        # Roof: net suction acts outward (up); low slope -> ~vertical uplift.
        up_bar = -net["cobertura_barlavento"] * q * BAY * COS   # +y up
        up_lee = -net["cobertura_sotavento"] * q * BAY * COS
        fr.add_member_udl(ix["rafL"], wy=up_bar)
        fr.add_member_udl(ix["rafR"], wy=up_lee)
    return apply, r


def _member_MN(mf, eid):
    f = mf[eid]  # [N_i, V_i, M_i, N_j, V_j, M_j]
    M = max(abs(f[2]), abs(f[5]))
    N = max(abs(f[0]), abs(f[3]))
    V = max(abs(f[1]), abs(f[4]))
    return M, N, V


def analyse():
    # per-case results (superposition)
    dG, mfG, ix = _run(case_G)
    dQ, mfQ, _ = _run(case_Q)
    (w1fn, wr) = _wind_case("portao_barlavento")   # Cpi +0.8 -> max uplift
    dW1, mfW1, _ = _run(w1fn)
    (w2fn, _) = _wind_case("portao_sotavento")     # Cpi -0.6 -> max wall push
    dW2, mfW2, _ = _run(w2fn)

    def combo_mf(coeffs):
        # coeffs: dict case->factor ; returns combined member forces
        import numpy as np
        keys = list(mfG.keys())
        out = {}
        for k in keys:
            v = np.zeros(6)
            for case, fac in coeffs.items():
                v = v + fac * {"G": mfG, "Q": mfQ, "W1": mfW1, "W2": mfW2}[case][k]
            out[k] = v
        return out

    def combo_disp(coeffs):
        import numpy as np
        v = np.zeros_like(dG)
        for case, fac in coeffs.items():
            v = v + fac * {"G": dG, "Q": dQ, "W1": dW1, "W2": dW2}[case]
        return v

    # ULS combinations (NBR 8800 Tabelas 1 e 2). gamma_g=1.25/1.0, gamma_q,vento=
    # 1.4, gamma_q,sobrecarga=1.5; psi0: sobrecarga cobertura=0.8, vento=0.6.
    # Combos flagged for engineer confirmation.
    C1 = {"G": 1.25, "Q": 1.50, "W2": 0.6 * 1.40}     # gravidade principal (+vento sec.)
    C2 = {"G": 1.00, "W1": 1.40}                       # vento uplift princ. (Q favoravel omitida)
    C3 = {"G": 1.00, "W2": 1.40, "Q": 0.8 * 1.50}     # vento pressao princ. (+sobrecarga sec.)

    combos = {"C1_gravidade": C1, "C2_vento_succao": C2, "C3_vento_pressao": C3}
    results = {}
    for name, c in combos.items():
        cmf = combo_mf(c)
        col = max(_member_MN(cmf, ix["colL"]), _member_MN(cmf, ix["colR"]))
        raf = max(_member_MN(cmf, ix["rafL"]), _member_MN(cmf, ix["rafR"]))
        results[name] = {"coluna": col, "viga": raf}

    # ELS drift (characteristic wind, worst push case W2)
    dser = combo_disp({"W2": 1.0})
    drift = abs(dser[3 * ix["n1"]])           # eave horizontal (frame x)
    drift_lim = EAVE / 300.0
    # ELS vertical deflection at ridge (G+Q)
    dvert = combo_disp({"G": 1.0, "Q": 1.0})
    ridge_v = abs(dvert[3 * ix["n2"] + 1])

    return {"wind": wr, "results": results, "drift": drift, "drift_lim": drift_lim,
            "ridge_v": ridge_v}


def memoria_pt(a):
    L = []
    L.append("=" * 70)
    L.append("MEMORIA DE CALCULO - GALPAO 20x10 m (portico transversal)")
    L.append("CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL")
    L.append("=" * 70)
    L.append("")
    L.append("1. DADOS")
    L.append(f"   Vao 10,0 m ; pe-direito 6,0 m ; cumeeira 6,5 m ; inclinacao 10%")
    L.append(f"   Espacamento de porticos (largura de influencia) = {BAY:.1f} m")
    L.append(f"   Bases rotuladas. Perfis PLACEHOLDER: colunas HEA200, vigas HEA180.")
    L.append(f"   Analise linear elastica de 1a ordem (2a ordem/deslocabilidade a")
    L.append(f"   confirmar pelo engenheiro - NBR 8800).")
    L.append("")
    L.append("2. ACOES")
    L.append(f"   2.1 Permanente (G): cobertura {G_ROOF:.2f} kN/m2 (telha+tercas+suspensas)")
    L.append(f"       + peso proprio da viga {RAFTER_SELF:.2f} kN/m")
    L.append(f"   2.2 Sobrecarga (Q): {Q_ROOF:.2f} kN/m2 (manutencao, NBR 8800)")
    L.append(f"   2.3 " + vento.relatorio_pt(a["wind"]).replace("\n", "\n   "))
    L.append("")
    L.append("3. COMBINACOES (NBR 8800, ELU) [a confirmar pelo engenheiro]")
    L.append("   psi0: sobrecarga cobertura = 0,8 ; vento = 0,6 (Tabela 2)")
    L.append("   C1 gravidade:  1,25 G + 1,50 Q + 0,84 W   (Q principal)")
    L.append("   C2 uplift:     1,00 G + 1,40 W(press. int.)   (Q favoravel omitida)")
    L.append("   C3 pressao:    1,00 G + 1,40 W(succ. int.) + 1,20 Q")
    L.append("")
    L.append("4. ESFORCOS (envoltoria por combinacao) [M kN.m, N kN, V kN]")
    for name, r in a["results"].items():
        cM, cN, cV = r["coluna"]
        vM, vN, vV = r["viga"]
        L.append(f"   {name}:")
        L.append(f"     Coluna: M={cM:6.1f}  N={cN:6.1f}  V={cV:6.1f}")
        L.append(f"     Viga:   M={vM:6.1f}  N={vN:6.1f}  V={vV:6.1f}")
    L.append("")
    L.append("5. DESLOCAMENTOS (ELS)")
    L.append(f"   Deslocamento lateral no beiral (vento caract.): {a['drift']*1000:.1f} mm")
    L.append(f"     Limite H/300 = {a['drift_lim']*1000:.1f} mm  -> "
             f"{'OK' if a['drift'] <= a['drift_lim'] else 'NAO ATENDE'}")
    L.append(f"   Flecha vertical na cumeeira (G+Q): {a['ridge_v']*1000:.1f} mm (verificar L/200)")
    L.append("")
    L.append("6. OBSERVACOES / PENDENCIAS (engenheiro)")
    L.append("   - Coeficientes de vento (Cpe/Cpi) a confirmar; portao = abertura")
    L.append("     dominante (pressao interna pode chegar a +0,7 com vento no oitao).")
    L.append("   - Confirmar necessidade de analise de 2a ordem e reducao de rigidez.")
    L.append("   - Dimensionar/verificar perfis (flexo-compressao, FLT, flambagem)")
    L.append("     e ligacoes (esforco minimo 45 kN) - proxima etapa.")
    L.append("   - Verificar tercas, contraventamento e bases separadamente.")
    import re
    return re.sub(r"(\d)\.(\d)", r"\1,\2", "\n".join(L))


if __name__ == "__main__":
    a = analyse()
    txt = memoria_pt(a)
    print(txt)
    out = "D:/dev/FreeCad_Automatic/projects/galpao/exports"
    os.makedirs(out + "/memoria", exist_ok=True)
    with open(out + "/memoria/memoria-calculo-galpao.txt", "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print("\n[gravado] exports/memoria/memoria-calculo-galpao.txt")
```

### Resultado (execucao de `galpao_portico.py`)

```
======================================================================
MEMORIA DE CALCULO - GALPAO 20x10 m (portico transversal)
CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL
======================================================================

1. DADOS
   Vao 10,0 m ; pe-direito 6,0 m ; cumeeira 6,5 m ; inclinacao 10%
   Espacamento de porticos (largura de influencia) = 5,0 m
   Bases rotuladas. Perfis PLACEHOLDER: colunas HEA200, vigas HEA180.
   Analise linear elastica de 1a ordem (2a ordem/deslocabilidade a
   confirmar pelo engenheiro - NBR 8800).

2. ACOES
   2,1 Permanente (G): cobertura 0,27 kN/m2 (telha+tercas+suspensas)
       + peso proprio da viga 0,35 kN/m
   2,2 Sobrecarga (Q): 0,25 kN/m2 (manutencao, NBR 8800)
   2,3 VENTO (ABNT NBR 6123/1988)
     V0 = 40 m/s ; Categoria II ; Classe B
     S1 = 1,00 (topografia plana) ; S3 = 0,95 (galpao deposito)
     S2 = 1,00*0,98*(6,5/10)^0,090 = 0,943
     Vk = 35,82 m/s ; q = 0,613*Vk^2 = 0,787 kN/m2
     Telhado theta = 5,71 graus (10%) ; h/b=0,6 ; a/b=2
     Cpe (Tabela 4 paredes alpha=90 ; Tabela 5 telhado alpha=0):
       parede barlavento: +0,70
       parede sotavento: -0,60
       cobertura barlavento: -0,89
       cobertura sotavento: -0,60
     Cpi (item 6,2.5-c, PORTAO como abertura dominante):
       portao barlavento: +0,80
       portao sotavento: -0,60
     Cp liquido = Cpe - Cpi e pressao (kN/m2):
       caso portao barlavento:
         parede barlavento: -0,10  (-0,079 kN/m2)
         parede sotavento: -1,40  (-1,102 kN/m2)
         cobertura barlavento: -1,69  (-1,330 kN/m2)
         cobertura sotavento: -1,40  (-1,102 kN/m2)
       caso portao sotavento:
         parede barlavento: +1,30  (+1,023 kN/m2)
         parede sotavento: +0,00  (+0,000 kN/m2)
         cobertura barlavento: -0,29  (-0,228 kN/m2)
         cobertura sotavento: +0,00  (+0,000 kN/m2)
     [A CONFIRMAR: classe (20 m), S3=0,95, mapeamento de zonas/alpha e
      razao de areas das aberturas para o Cpi do portao (6,2.5-c).]

3. COMBINACOES (NBR 8800, ELU) [a confirmar pelo engenheiro]
   psi0: sobrecarga cobertura = 0,8 ; vento = 0,6 (Tabela 2)
   C1 gravidade:  1,25 G + 1,50 Q + 0,84 W   (Q principal)
   C2 uplift:     1,00 G + 1,40 W(press. int.)   (Q favoravel omitida)
   C3 pressao:    1,00 G + 1,40 W(succ. int.) + 1,20 Q

4. ESFORCOS (envoltoria por combinacao) [M kN.m, N kN, V kN]
   C1_gravidade:
     Coluna: M=  62,1  N=  26,5  V=  10,4
     Viga:   M=  62,1  N=  12,9  V=  25,4
   C2_vento_succao:
     Coluna: M= 109,8  N=  48,9  V=  19,9
     Viga:   M= 109,8  N=  24,7  V=  46,7
   C3_vento_pressao:
     Coluna: M=  81,1  N=  26,9  V=  13,5
     Viga:   M=  81,1  N=  16,1  V=  25,4

5. DESLOCAMENTOS (ELS)
   Deslocamento lateral no beiral (vento caract.): 183,6 mm
     Limite H/300 = 20,0 mm  -> NAO ATENDE
   Flecha vertical na cumeeira (G+Q): 26,6 mm (verificar L/200)

6. OBSERVACOES / PENDENCIAS (engenheiro)
   - Coeficientes de vento (Cpe/Cpi) a confirmar; portao = abertura
     dominante (pressao interna pode chegar a +0,7 com vento no oitao).
   - Confirmar necessidade de analise de 2a ordem e reducao de rigidez.
   - Dimensionar/verificar perfis (flexo-compressao, FLT, flambagem)
     e ligacoes (esforco minimo 45 kN) - proxima etapa.
   - Verificar tercas, contraventamento e bases separadamente.

[gravado] exports/memoria/memoria-calculo-galpao.txt
```

---

## check_nbr8800.py
_Verificacao de perfil NBR 8800 (flexo-compressao, FLT)_

```python
"""Verificacao de perfil metalico conforme ABNT NBR 8800:2008.

Recebe propriedades da secao + esforcos solicitantes (Nsd, Msd, Vsd) e calcula as
resistencias de calculo e as razoes de utilizacao. Transparente e auditavel, com
as clausulas citadas. Calcula apenas; pendente revisao do engenheiro.

Verifica: tracao (5.2), compressao com flambagem global (5.3, chi da Tabela 4),
flexao com FLT (5.4/Anexo G, simplificado), cortante (5.4.3) e a interacao
flexo-compressao (5.5.1.2). Flambagem local: Q=1 assumido (secao compacta) - a
confirmar. Unidades internas: kN, m, kN/m2.
"""

from __future__ import annotations

import math

E = 200e6          # kN/m2 (200 GPa)
GA1 = 1.10         # coef. de resistencia ao escoamento/flambagem
GA2 = 1.35         # coef. de resistencia a ruptura


def chi_compressao(lambda0):
    """NBR 8800 5.3.3 / Tabela 4: fator de reducao chi."""
    if lambda0 <= 1.5:
        return 0.658 ** (lambda0 ** 2)
    return 0.877 / lambda0 ** 2


def verifica(sec, fy, L, Nsd, Msd, Vsd, Kx=1.0, Ky=1.0, Lb=None, Q=1.0, Cb=1.0,
             nome=""):
    """sec: dict com A, Ix, Iy, ry, Zx, Wx, Aw (SI: m2, m4, m, m3).
    fy em kN/m2. L, Lb em m. Retorna dict de resultados."""
    A, Ix, Iy = sec["A"], sec["Ix"], sec["Iy"]
    ry, Zx, Wx, Aw = sec["ry"], sec["Zx"], sec["Wx"], sec["Aw"]
    if Lb is None:
        Lb = L
    r = {"nome": nome}

    # --- Tracao (5.2): escoamento da secao bruta ---
    Nt_Rd = A * fy / GA1
    r["Nt_Rd"] = Nt_Rd

    # --- Compressao (5.3): flambagem global, dois eixos ---
    Ne_x = math.pi ** 2 * E * Ix / (Kx * L) ** 2
    Ne_y = math.pi ** 2 * E * Iy / (Ky * Lb) ** 2
    Ne = min(Ne_x, Ne_y)
    lambda0 = math.sqrt(Q * A * fy / Ne)
    chi = chi_compressao(lambda0)
    Nc_Rd = chi * Q * A * fy / GA1
    r.update(Ne=Ne, lambda0=lambda0, chi=chi, Nc_Rd=Nc_Rd)

    # --- Flexao com FLT (5.4 / Anexo G), eixo forte, simplificado ---
    Mpl = Zx * fy
    Lp = 1.76 * ry * math.sqrt(E / fy)
    if Lb <= Lp:
        Mn = Mpl
        flt = "sem FLT (Lb<=Lp): Mn=Mpl"
    else:
        # Mr = fy*Wx (inicio do regime inelastico, conservador sem residual);
        # Lr aproximado por pi*ry*sqrt(E/(0.7fy)) (limite elastico simplificado).
        Mr = fy * Wx
        Lr = math.pi * ry * math.sqrt(E / (0.7 * fy))
        if Lb <= Lr:
            Mn = min(Cb * (Mpl - (Mpl - Mr) * (Lb - Lp) / (Lr - Lp)), Mpl)
            flt = "FLT inelastica (Lp<Lb<=Lr) - VERIFICAR Anexo G detalhado"
        else:
            Mcr = Cb * math.pi ** 2 * E * Iy / Lb ** 2  # simplificado (só termo empenamento omitido)
            Mn = min(Mcr, Mpl)
            flt = "FLT elastica (Lb>Lr) - VERIFICAR Anexo G detalhado"
    Mrd = Mn / GA1
    r.update(Mpl=Mpl, Lp=Lp, Lb=Lb, Mn=Mn, Mrd=Mrd, flt=flt)

    # --- Cortante (5.4.3), alma compacta ---
    Vpl = 0.6 * Aw * fy
    Vrd = Vpl / GA1
    r["Vrd"] = Vrd

    # --- Razoes de utilizacao ---
    r["u_N_trac"] = Nsd / Nt_Rd if Nsd > 0 else 0.0
    r["u_N_comp"] = Nsd / Nc_Rd
    r["u_M"] = Msd / Mrd
    r["u_V"] = Vsd / Vrd

    # --- Interacao flexo-compressao (5.5.1.2) ---
    n = Nsd / Nc_Rd
    m = Msd / Mrd
    if n >= 0.2:
        inter = n + (8.0 / 9.0) * m
        eq = "N/Nrd + 8/9*(M/Mrd)"
    else:
        inter = n / 2.0 + m
        eq = "N/(2Nrd) + M/Mrd"
    r.update(interacao=inter, eq_interacao=eq)
    r["OK"] = (inter <= 1.0 and r["u_V"] <= 1.0)
    return r


def relatorio_pt(rs, fy):
    L = []
    L.append("VERIFICACAO DE PERFIS (ABNT NBR 8800:2008)")
    L.append(f"  fy = {fy/1000:.0f} MPa ; gamma_a1 = {GA1:.2f} ; Q = 1,0 (compacta, a confirmar)")
    for r in rs:
        L.append("")
        L.append(f"  --- {r['nome']} ---")
        L.append(f"  Compressao: Ne={r['Ne']:.0f} kN ; lambda0={r['lambda0']:.3f} ; "
                 f"chi={r['chi']:.3f} ; Nc,Rd={r['Nc_Rd']:.1f} kN")
        L.append(f"  Flexao: Mpl={r['Mpl']:.1f} ; Lp={r['Lp']:.2f} m ; Lb={r['Lb']:.2f} m ; "
                 f"Mrd={r['Mrd']:.1f} kN.m ({r['flt']})")
        L.append(f"  Cortante: Vrd={r['Vrd']:.1f} kN")
        L.append(f"  Utilizacao: N/Nc={r['u_N_comp']:.2f} ; M/Mrd={r['u_M']:.2f} ; "
                 f"V/Vrd={r['u_V']:.2f}")
        L.append(f"  Interacao ({r['eq_interacao']}) = {r['interacao']:.2f}  -> "
                 f"{'OK' if r['OK'] else 'NAO PASSA'}")
    import re
    return re.sub(r"(\d)\.(\d)", r"\1,\2", "\n".join(L))


# ---- secoes (SI: m2, m4, m, m3) --------------------------------------------
HEA200 = {"A": 53.83e-4, "Ix": 3692e-8, "Iy": 1336e-8, "ry": 0.0498,
          "Zx": 429.5e-6, "Wx": 388.6e-6, "Aw": 0.190 * 0.0065}
HEA180 = {"A": 45.25e-4, "Ix": 2510e-8, "Iy": 924.6e-8, "ry": 0.0452,
          "Zx": 324.9e-6, "Wx": 293.6e-6, "Aw": 0.171 * 0.006}


if __name__ == "__main__":
    fy = 250e3  # kN/m2 (aco MR250 / ASTM A36)
    # Esforcos da combinacao governante C2 (galpao_portico): coluna e viga.
    col = verifica(HEA200, fy, L=6.0, Nsd=48.9, Msd=109.8, Vsd=19.9,
                   Kx=2.0, Ky=1.0, Lb=2.0, nome="Coluna HEA200 (K x=2 sway; Lb=2 m girts)")
    raf = verifica(HEA180, fy, L=5.03, Nsd=24.7, Msd=109.8, Vsd=46.7,
                   Kx=1.0, Ky=1.0, Lb=1.67, nome="Viga HEA180 (Lb=1,67 m tercas)")
    print(relatorio_pt([col, raf], fy))
```

### Resultado (execucao de `check_nbr8800.py`)

```
VERIFICACAO DE PERFIS (ABNT NBR 8800:2008)
  fy = 250 MPa ; gamma_a1 = 1,10 ; Q = 1,0 (compacta, a confirmar)

  --- Coluna HEA200 (K x=2 sway; Lb=2 m girts) ---
  Compressao: Ne=506 kN ; lambda0=1,631 ; chi=0,330 ; Nc,Rd=403,5 kN
  Flexao: Mpl=107,4 ; Lp=2,48 m ; Lb=2,00 m ; Mrd=97,6 kN.m (sem FLT (Lb<=Lp): Mn=Mpl)
  Cortante: Vrd=168,4 kN
  Utilizacao: N/Nc=0,12 ; M/Mrd=1,12 ; V/Vrd=0,12
  Interacao (N/(2Nrd) + M/Mrd) = 1,19  -> NAO PASSA

  --- Viga HEA180 (Lb=1,67 m tercas) ---
  Compressao: Ne=1958 kN ; lambda0=0,760 ; chi=0,785 ; Nc,Rd=807,5 kN
  Flexao: Mpl=81,2 ; Lp=2,25 m ; Lb=1,67 m ; Mrd=73,8 kN.m (sem FLT (Lb<=Lp): Mn=Mpl)
  Cortante: Vrd=139,9 kN
  Utilizacao: N/Nc=0,03 ; M/Mrd=1,49 ; V/Vrd=0,33
  Interacao (N/(2Nrd) + M/Mrd) = 1,50  -> NAO PASSA
```

