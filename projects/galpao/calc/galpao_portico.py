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
