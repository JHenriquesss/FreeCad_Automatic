# Solver de portico 2D - frame2d.py

Arquivo: `framework/galpao_fw/frame2d.py`  
Gerado: 2026-07-05  
Status: validado (auto-teste contra solucao fechada). Metodo da rigidez
direta. Inclui reactions() para a decomposicao nt/lt do metodo B1/B2.

## Codigo completo

```python
# ============================================================================
# frame2d.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Resolve um portico plano 2D pelo metodo da rigidez direta.
#   Entra: geometria (nos e barras), secoes (E, A, I), apoios e cargas (nodais e
#          distribuidas).
#   Calcula: deslocamentos dos nos e esforcos nas barras (N normal, V cortante,
#            M momento fletor).
#   Auto-teste valida contra solucao fechada (cantilever PL^3/3EI e M=PL;
#   viga biapoiada M=wL^2/8).
# NAO dimensiona nem verifica perfil - apenas calcula esforcos e deslocamentos.
# ============================================================================
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

        # store for reactions(): R = K*d - F (nonzero at supported DOFs)
        self._K, self._F, self._d = K, F, d

        # member end forces (local): f = k_loc*T*d + fef
        # Convention: [N_i, V_i, M_i, N_j, V_j, M_j], forces the ELEMENT exerts on
        # its end nodes. To plot internal-force diagrams (traction positive), flip
        # the sign of the i-end (N_i, V_i, M_i).
        member_forces = {}
        for idx, (fef, T, k_loc, dofs) in fef_store.items():
            d_e = d[dofs]
            f_loc = k_loc @ (T @ d_e) + fef
            member_forces[idx] = f_loc
        return d, member_forces

    def reactions(self):
        """Reacoes de apoio: R = K*d - F (por GDL global; nao-nulo nos apoios).
        Chamar apos solve(). No no n: horizontal=R[3n], vertical=R[3n+1],
        momento=R[3n+2]. Inclui as reacoes de contencoes ficticias (usadas na
        decomposicao nt/lt do metodo B1-B2)."""
        return self._K @ self._d - self._F


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

## Resultado da execucao (auto-teste)

```
frame2d self-test PASSED
  cantilever tip: -4.500000e-03 m (exact -4.500000e-03)
  cantilever base M: 30.0000 kN.m (exact 30.0000)
  SS beam mid M: 10.0000 kN.m (exact 10.0000)
```
