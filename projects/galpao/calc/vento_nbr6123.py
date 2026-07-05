"""Wind loads per ABNT NBR 6123 for the galpao transverse frame.

Transparent and auditable: every factor is a named variable with the clause it
comes from, so the reviewing engineer checks the method, not a black box. The
coefficient VALUES are standard NBR 6123 table entries for a simple rectangular
building; they are flagged for engineer confirmation. Outputs (report text) are
in Portuguese.

Computes only; not certified. Units: m, kN, kN/m2.
"""

from __future__ import annotations


def s2_factor(cat, classe, z):
    """NBR 6123 Table 1: S2 = b * Fr * (z/10)^p."""
    # (b, Fr, p) for terrain category II, building classes A/B/C
    tbl = {
        ("II", "A"): (1.00, 1.00, 0.06),
        ("II", "B"): (1.00, 0.98, 0.06),
        ("II", "C"): (1.00, 0.95, 0.06),
    }
    # p differs by class; NBR 6123 Table 1 (Cat II): pA=0.085? use standard set.
    # Using the commonly tabulated Cat II values:
    tbl = {
        ("II", "A"): (1.00, 1.00, 0.085),
        ("II", "B"): (1.00, 0.98, 0.09),
        ("II", "C"): (1.00, 0.95, 0.10),
    }
    b, Fr, p = tbl[(cat, classe)]
    return b, Fr, p, b * Fr * (z / 10.0) ** p


def compute(v0=40.0, cat="II", classe="B", s1=1.0, s3=1.0, z=6.5):
    """Return the wind result dict for the transverse case."""
    b, Fr, p, s2 = s2_factor(cat, classe, z)
    vk = v0 * s1 * s2 * s3
    q = 0.613 * vk ** 2 / 1000.0   # kN/m2 (0.613 in N/m2 with V in m/s)

    # External pressure coefficients Cpe (NBR 6123 Tables 4-6), transverse wind
    # (perpendicular to the 20 m length, hitting the 10 m-span long walls).
    # Governing values for a low building, roof slope ~5.7deg -> treated low.
    cpe = {
        "parede_barlavento": 0.70,    # windward wall (pressure)
        "parede_sotavento": -0.40,    # leeward wall (suction)
        "cobertura_barlavento": -0.80,  # windward roof (suction)
        "cobertura_sotavento": -0.40,   # leeward roof (suction)
    }
    # Internal pressure coefficient Cpi (NBR 6123 6.2). Gate is a dominant opening
    # on the FRONT gable; for transverse wind it is a side face -> use +/-0.30
    # from permeability. Consider both signs; the engineer confirms.
    cpi_cases = {"pressao_interna": +0.30, "succao_interna": -0.30}

    # Net pressure coefficient per surface for each Cpi case: Cp = Cpe - Cpi
    net = {}
    for cname, cpi in cpi_cases.items():
        net[cname] = {s: round(cpe[s] - cpi, 2) for s in cpe}

    return {
        "v0": v0, "cat": cat, "classe": classe, "s1": s1, "s2": round(s2, 3),
        "s3": s3, "Fr": Fr, "p": p, "z": z, "vk": round(vk, 2), "q_kN_m2": round(q, 3),
        "cpe": cpe, "cpi_cases": cpi_cases, "net": net,
    }


def relatorio_pt(r):
    """Portuguese text block for the calc memory."""
    L = []
    L.append("VENTO (ABNT NBR 6123)")
    L.append(f"  V0 = {r['v0']:.0f} m/s ; Categoria {r['cat']} ; Classe {r['classe']}")
    L.append(f"  S1 = {r['s1']:.2f} (topografia plana) ; S3 = {r['s3']:.2f}")
    L.append(f"  S2 = b*Fr*(z/10)^p = 1,00*{r['Fr']:.2f}*({r['z']:.1f}/10)^{r['p']:.3f} "
             f"= {r['s2']:.3f}  (z = {r['z']:.1f} m, altura da cumeeira)")
    L.append(f"  Vk = V0*S1*S2*S3 = {r['vk']:.2f} m/s")
    L.append(f"  q = 0,613*Vk^2 = {r['q_kN_m2']:.3f} kN/m2")
    L.append("  Coeficientes de forma externos Cpe (NBR 6123):")
    for s, v in r["cpe"].items():
        L.append(f"    {s.replace('_',' ')}: {v:+.2f}")
    L.append("  Coeficiente de pressao interna Cpi (portao = abertura dominante):")
    for k, v in r["cpi_cases"].items():
        L.append(f"    {k.replace('_',' ')}: {v:+.2f}")
    L.append("  Coeficiente liquido Cp = Cpe - Cpi (governante por superficie):")
    for caso, d in r["net"].items():
        L.append(f"    caso {caso.replace('_',' ')}:")
        for s, v in d.items():
            L.append(f"      {s.replace('_',' ')}: {v:+.2f}  (pressao {v*r['q_kN_m2']:+.3f} kN/m2)")
    L.append("  [VALORES DE COEFICIENTE A CONFIRMAR PELO ENGENHEIRO RESPONSAVEL]")
    return "\n".join(L)


if __name__ == "__main__":
    r = compute()
    print(relatorio_pt(r))
