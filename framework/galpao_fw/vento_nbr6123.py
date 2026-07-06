# ============================================================================
# vento_nbr6123.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Calcula a acao do vento pela ABNT NBR 6123/1988.
#   Calcula: fator de rugosidade S2 (Tabela 1), velocidade caracteristica Vk,
#            pressao dinamica q = 0,613*Vk^2, coeficientes de forma externos Cpe
#            (paredes Tabela 4, telhado Tabela 5) e coeficiente de pressao interna
#            Cpi (item 6.2.5-c, portao como abertura dominante), e a pressao
#            liquida (Cpe - Cpi)*q por superficie.
# NAO analisa a estrutura - so fornece as pressoes de vento.
# ============================================================================
"""Wind loads per ABNT NBR 6123/1988 for the galpao transverse frame.

Coefficients are the ACTUAL table values (Tabela 1, 4, 5 and item 6.2), read from
the standard, with clause references. Transparent and auditable. The zone/alpha
mapping and the dominant-opening area ratio are flagged for engineer confirmation.
Outputs in Portuguese. Computes only; pending engineer review. Units: m, kN.

Building: a=20 (length), b=10 (span/width), h=6 (eave). h/b=0.6 ; a/b=2.
Transverse frame = wind perpendicular to the ridge (hits the long 20 m walls).
"""

from __future__ import annotations


# Defaults de sitio (do gate). configurar() troca; compute() usa quando o arg e None.
_CFG = {"v0": 40.0, "cat": "II", "classe": "B", "s1": 1.0, "s3": 0.95,
        "z": 6.5, "theta": 5.71}


def configurar(v0=None, cat=None, classe=None, s1=None, s3=None, z=None, theta=None):
    """Define os parametros de sitio/vento (do Gate 5). Chamar antes de compute()."""
    for k, v in (("v0", v0), ("cat", cat), ("classe", classe), ("s1", s1),
                 ("s3", s3), ("z", z), ("theta", theta)):
        if v is not None:
            _CFG[k] = v


def s2_factor(cat, classe, z):
    """NBR 6123 Tabela 1 (parametros meteorologicos) -> S2 = b*Fr*(z/10)^p.
    Fr = fator de rajada da categoria II por classe (A=1,00; B=0,98; C=0,95),
    usado para todas as categorias. b e p por categoria/classe. Cat II conferida
    contra a referencia; demais categorias A CONFIRMAR contra a Tabela 1 do PDF."""
    Fr = {"A": 1.00, "B": 0.98, "C": 0.95}[classe]
    # (b, p) por (categoria, classe) - Tabela 1 da NBR 6123/1988
    bp = {
        ("I", "A"): (1.10, 0.06), ("I", "B"): (1.10, 0.065), ("I", "C"): (1.10, 0.07),
        ("II", "A"): (1.00, 0.085), ("II", "B"): (1.00, 0.09), ("II", "C"): (1.00, 0.10),
        ("III", "A"): (0.94, 0.10), ("III", "B"): (0.94, 0.105), ("III", "C"): (0.94, 0.115),
        ("IV", "A"): (0.86, 0.12), ("IV", "B"): (0.86, 0.125), ("IV", "C"): (0.86, 0.135),
        ("V", "A"): (0.74, 0.15), ("V", "B"): (0.74, 0.16), ("V", "C"): (0.74, 0.175),
    }
    if (cat, classe) not in bp:
        raise ValueError(f"categoria/classe de vento invalida: {cat}/{classe} "
                         "(NBR 6123 Tabela 1: categorias I-V, classes A/B/C)")
    b, p = bp[(cat, classe)]
    return b, Fr, p, b * Fr * (z / 10.0) ** p


def _interp(x, x0, x1, y0, y1):
    return y0 + (x - x0) / (x1 - x0) * (y1 - y0)


def cpe_paredes():
    """NBR 6123 Tabela 4, paredes. Vento transversal atinge as paredes longas
    (a=20). Bloco 1/2<h/b<=3/2, linha 2<=a/b<=4, incidencia alpha=90 (faces A,B).
    A = barlavento, B = sotavento."""
    return {"parede_barlavento": +0.70, "parede_sotavento": -0.60}


def cpe_telhado(theta_graus=5.71):
    """NBR 6123 Tabela 5, telhado duas aguas. MESMA incidencia das paredes:
    vento perpendicular a cumeeira = alpha=90 graus -> colunas EF (agua
    barlavento) e GH (agua sotavento). Bloco 1/2<h/b<=3/2 (h/b=0,6). Interpola
    theta entre 5 e 10 graus:
      5 graus:  EF=-0,90  GH=-0,60 ; 10 graus: EF=-1,10  GH=-0,60.
    (As colunas EG/FH da Tabela 5 sao para alpha=0 - vento LONGITUDINAL - e NAO
    podem ser misturadas com as paredes de alpha=90.)"""
    ef = _interp(theta_graus, 5.0, 10.0, -0.90, -1.10)
    gh = _interp(theta_graus, 5.0, 10.0, -0.60, -0.60)
    return {"cobertura_barlavento": round(ef, 2), "cobertura_sotavento": round(gh, 2)}


def cpi_cases():
    """NBR 6123 item 6.2.5-c: PORTAO = abertura dominante no oitao.
    - Portao a barlavento (vento no oitao): Cpi = +0,1 a +0,8 conforme a razao
      (area do portao / area das demais aberturas sob succao). Adotado +0,8
      (conservador, razao >=6) - A CONFIRMAR com a razao real das aberturas.
    - Portao a sotavento: Cpi = Cpe da face de sotavento (Tabela 4) = -0,6.
    Consideram-se ambos; o engenheiro escolhe/refina."""
    return {"portao_barlavento": +0.80, "portao_sotavento": -0.60}


def compute(v0=None, cat=None, classe=None, s1=None, s3=None, z=None, theta=None):
    v0 = _CFG["v0"] if v0 is None else v0
    cat = _CFG["cat"] if cat is None else cat
    classe = _CFG["classe"] if classe is None else classe
    s1 = _CFG["s1"] if s1 is None else s1
    s3 = _CFG["s3"] if s3 is None else s3
    z = _CFG["z"] if z is None else z
    theta = _CFG["theta"] if theta is None else theta
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
    L.append("  Cpe (MESMA incidencia alpha=90: paredes Tab.4 A/B ; telhado Tab.5 EF/GH):")
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


# ============================================================================
# VENTO LONGITUDINAL (incidencia alpha=0, atinge o OITAO / empena de 10 m)
# Fornece: (a) Cpe das paredes na incidencia 0 (Tabela 4) para o MONTANTE DE
# OITAO; (b) a FORCA DE ARRASTO global Fa = Ca*q*Ae (item 6.3), que os
# contraventamentos longitudinais e as escoras de beiral resistem. Ca vem da
# Figura 4 (grafico, vento de baixa turbulencia) - NAO e tabela: entra como
# parametro marcado "A CONFIRMAR (ler Figura 4)". O metodo Fa=Ca*q*Ae e exato.
# ============================================================================


def cpe_paredes_longitudinal():
    """NBR 6123 Tabela 4, incidencia alpha=0 (vento no oitao). a/b = 2.
    Barlavento (empena atingida) C = +0,7 ; sotavento D = -0,3 (a/b=2) ;
    paredes laterais (paralelas ao vento) A/B = -0,8 / -0,5."""
    return {"oitao_barlavento": +0.70, "oitao_sotavento": -0.30,
            "parede_lateral_A": -0.80, "parede_lateral_B": -0.50}


def forca_arrasto(q, area_frontal, ca):
    """Item 6.3: Fa = Ca * q * Ae (kN). Ae = area frontal (empena) projetada."""
    return ca * q * area_frontal


def compute_longitudinal(v0=None, cat=None, classe=None, s1=None, s3=None, z=None,
                         b=10.0, eave=6.0, ridge=6.5, ca=1.2):
    """Vento longitudinal (alpha=0). q reaproveitado (independe da direcao).
    b = largura do oitao ; area frontal = retangulo + triangulo da empena.
    ca = coeficiente de arrasto (Figura 4, baixa turbulencia) - A CONFIRMAR."""
    v0 = _CFG["v0"] if v0 is None else v0
    cat = _CFG["cat"] if cat is None else cat
    classe = _CFG["classe"] if classe is None else classe
    s1 = _CFG["s1"] if s1 is None else s1
    s3 = _CFG["s3"] if s3 is None else s3
    z = _CFG["z"] if z is None else z
    b_, Fr, p, s2 = s2_factor(cat, classe, z)
    vk = v0 * s1 * s2 * s3
    q = 0.613 * vk ** 2 / 1000.0
    area = b * eave + b * (ridge - eave) / 2.0     # empena: retangulo + triangulo
    cpe = cpe_paredes_longitudinal()
    cpi = cpi_cases()
    net = {c: {s: round(cpe[s] - civ, 2) for s in cpe} for c, civ in cpi.items()}
    Fa = forca_arrasto(q, area, ca)
    return {"v0": v0, "vk": round(vk, 2), "q_kN_m2": round(q, 3), "b": b,
            "eave": eave, "ridge": ridge, "area_frontal": round(area, 2),
            "ca": ca, "Fa_kN": round(Fa, 1), "Fa_por_lado_kN": round(Fa / 2.0, 1),
            "cpe": cpe, "cpi_cases": cpi, "net": net}


def relatorio_longitudinal_pt(r):
    L = ["VENTO LONGITUDINAL (ABNT NBR 6123/1988 - incidencia alpha=0, oitao)",
         f"  Vk = {r['vk']:.2f} m/s ; q = {r['q_kN_m2']:.3f} kN/m2",
         f"  Area frontal (empena {r['b']:.0f} m) = {r['area_frontal']:.2f} m2",
         f"  Cpe paredes (Tab.4, alpha=0):"]
    for s, v in r["cpe"].items():
        L.append(f"    {s.replace('_',' ')}: {v:+.2f}")
    L.append("  Cp liquido (Cpe - Cpi) por caso de portao:")
    for caso, d in r["net"].items():
        L.append(f"    {caso.replace('_',' ')}: " +
                 " ; ".join(f"{s.split('_')[-1]}={v:+.2f}" for s, v in d.items()))
    L += [f"  Forca de arrasto Fa = Ca*q*Ae = {r['ca']:.2f}*{r['q_kN_m2']:.3f}*"
          f"{r['area_frontal']:.2f} = {r['Fa_kN']:.1f} kN",
          f"  Fa por lado (2 paineis de contraventamento) = {r['Fa_por_lado_kN']:.1f} kN",
          "  [A CONFIRMAR: Ca da Figura 4 (baixa turbulencia); area frontal da",
          "   empena; fracao de Fa por escora conforme o arranjo do contraventamento.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


if __name__ == "__main__":
    print(relatorio_pt(compute()))
    print()
    print(relatorio_longitudinal_pt(compute_longitudinal()))
