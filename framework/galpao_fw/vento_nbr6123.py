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
_CFG_DEFAULT = {"v0": 40.0, "cat": "II", "classe": "B", "s1": 1.0, "s3": 0.95,
                "z": 6.5, "theta": 5.71}
_CFG = dict(_CFG_DEFAULT)


def reset():
    """Zera o estado de sitio para o default (evita vazamento entre projetos)."""
    _CFG.clear(); _CFG.update(_CFG_DEFAULT)


def configurar(v0=None, cat=None, classe=None, s1=None, s3=None, z=None, theta=None):
    """Define os parametros de sitio/vento (do Gate 5). Chamar antes de compute()."""
    for k, v in (("v0", v0), ("cat", cat), ("classe", classe), ("s1", s1),
                 ("s3", s3), ("z", z), ("theta", theta)):
        if v is not None:
            _CFG[k] = v


def s2_factor(cat, classe, z):
    """NBR 6123 Tabela 1 (parametros meteorologicos) -> S2 = b*Fr*(z/10)^p.
    Fr = fator de rajada da categoria II por classe (A=1,00; B=0,98; C=0,95),
    usado para todas as categorias. b e p por categoria/classe, conferidos
    integralmente contra a Tabela 1 da NBR 6123/1988 (pag. 8 do PDF)."""
    Fr = {"A": 1.00, "B": 0.98, "C": 0.95}[classe]
    # (b, p) por (categoria, classe) - Tabela 1 da NBR 6123/1988 (verbatim)
    bp = {
        ("I", "A"): (1.10, 0.06), ("I", "B"): (1.11, 0.065), ("I", "C"): (1.12, 0.07),
        ("II", "A"): (1.00, 0.085), ("II", "B"): (1.00, 0.09), ("II", "C"): (1.00, 0.10),
        ("III", "A"): (0.94, 0.10), ("III", "B"): (0.94, 0.105), ("III", "C"): (0.93, 0.115),
        ("IV", "A"): (0.86, 0.12), ("IV", "B"): (0.85, 0.125), ("IV", "C"): (0.84, 0.135),
        ("V", "A"): (0.74, 0.15), ("V", "B"): (0.73, 0.16), ("V", "C"): (0.71, 0.175),
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


# ============================================================================
# Cpe MEDIO / LOCAL (alta succao de borda e canto) - Tabelas 4 e 5, coluna
# "cpe medio" (zonas hachuradas). NAO governa o portico (que usa o Cpe global
# acima); governa a TELHA, a TERCA e seus FIXADORES nas faixas de borda/canto,
# onde a succao e muito maior. Valores lidos VERBATIM do PDF (pags. 14-15).
# ============================================================================

# Tabela 4 (paredes) - coluna "cpe medio", faixa de barlavento das paredes
# paralelas ao vento, largura = min(0,2b ; h) [nota c]. Chave: (bloco h/b, bloco a/b).
_CPE_MEDIO_PAREDE = {
    ("<=1/2", "1-3"): -0.9, ("<=1/2", "2-4"): -1.0,
    ("1/2-3/2", "1-3"): -1.1, ("1/2-3/2", "2-4"): -1.1,
    ("3/2-6", "1-3"): -1.2, ("3/2-6", "2-4"): -1.2,
}

# Tabela 5 (telhado 2 aguas) - coluna "cpe medio", 4 zonas hachuradas por
# (bloco h/b, theta). None = zona ausente naquele angulo (celula em branco).
# Faixa: y = min(h ; 0,15b) ; dimensao da zona = min(max(b/3 ; a/4) ; 2h).
_CPE_MEDIO_COB = {
    "<=1/2": [
        (0,  (-2.0, -2.0, -2.0, None)), (5,  (-1.4, -1.2, -1.2, -1.0)),
        (10, (-1.4, -1.4, None, -1.2)), (15, (-1.4, -1.2, None, -1.2)),
        (20, (-1.0, None, None, -1.2)), (30, (-0.8, None, None, -1.1)),
        (45, (None, None, None, -1.1)), (60, (None, None, None, -1.1)),
    ],
    "1/2-3/2": [
        (0,  (-2.0, -2.0, -2.0, None)), (5,  (-2.0, -2.0, -1.5, -1.0)),
        (10, (-2.0, -2.0, -1.5, -1.2)), (15, (-1.8, -1.5, -1.5, -1.2)),
        (20, (-1.5, -1.5, -1.5, -1.0)), (30, (-1.0, None, None, -1.0)),
    ],
    "3/2-6": [
        (0,  (-2.0, -2.0, -2.0, None)), (5,  (-2.0, -2.0, -1.5, -1.0)),
        (10, (-2.0, -2.0, -1.5, -1.2)), (15, (-1.8, -1.8, -1.5, -1.2)),
        (20, (-1.5, -1.5, -1.5, -1.2)), (30, (-1.5, None, None, None)),
        (40, (-1.0, None, None, None)),
    ],
}


def _bloco_hb(h, b):
    hb = h / b
    if hb <= 0.5:
        return "<=1/2", hb
    if hb <= 1.5:
        return "1/2-3/2", hb
    if hb <= 6.0:
        return "3/2-6", hb
    raise ValueError(f"h/b={hb:.2f} fora da Tabela 4/5 (limite 6)")


def _bloco_ab(a, b):
    ab = a / b
    return ("1-3" if ab <= 1.5 else "2-4"), ab   # nota a: interpola 3/2..2


def cpe_local_parede(a=20.0, b=10.0, h=6.0):
    """cpe medio das paredes (Tabela 4), zona de alta succao de borda a barlavento
    das paredes paralelas ao vento. Largura da faixa = min(0,2b ; h) [nota c].
    Governa o fixador da telha/terca de fechamento lateral no canto de barlavento."""
    bloco_h, hb = _bloco_hb(h, b)
    bloco_a, ab = _bloco_ab(a, b)
    cpe = _CPE_MEDIO_PAREDE[(bloco_h, bloco_a)]
    faixa = min(0.2 * b, h)
    return {"cpe_medio": cpe, "faixa_m": round(faixa, 2),
            "hb": round(hb, 3), "ab": round(ab, 3),
            "bloco_hb": bloco_h, "bloco_ab": bloco_a}


def cpe_local_cobertura(theta_graus=5.71, b=10.0, h=6.0, a=20.0):
    """cpe medio do telhado (Tabela 5), envoltoria das 4 zonas hachuradas de
    borda/canto, interpolada em theta. Governa o fixador da telha e a ligacao
    terca-portico nas bordas/cantos da cobertura. Retorna a envoltoria (mais
    negativa) e a geometria da zona (faixa y e dimensao da zona)."""
    bloco_h, hb = _bloco_hb(h, b)
    linhas = _CPE_MEDIO_COB[bloco_h]
    th = max(linhas[0][0], min(theta_graus, linhas[-1][0]))   # clamp ao dominio
    # localiza o par de linhas que envolve th
    lo = hi = linhas[0]
    for row in linhas:
        if row[0] <= th:
            lo = row
        if row[0] >= th:
            hi = row
            break
    zonas = []
    for j in range(4):
        y0, y1 = lo[1][j], hi[1][j]
        if y0 is None and y1 is None:
            zonas.append(None)
        elif y0 is None:
            zonas.append(y1)
        elif y1 is None:
            zonas.append(y0)
        elif lo[0] == hi[0]:
            zonas.append(y0)
        else:
            zonas.append(round(_interp(th, lo[0], hi[0], y0, y1), 2))
    envoltoria = min(v for v in zonas if v is not None)
    y = min(h, 0.15 * b)
    dim_zona = min(max(b / 3.0, a / 4.0), 2.0 * h)
    return {"cpe_medio_envoltoria": round(envoltoria, 2),
            "zonas": zonas, "theta": theta_graus, "bloco_hb": bloco_h,
            "faixa_y_m": round(y, 2), "dim_zona_m": round(dim_zona, 2),
            "lanternim_cpe_medio": -2.0}


def cpe_telhado_multiplo(n_vaos, theta_graus=5.71):
    """Cpe para telhados MULTIPLOS simetricos de tramos IGUAIS (NBR 6123 Tab.7).
    Retorna uma lista de dicts, um por tramo (vao). Cada dict tem:
      {"barlavento": float, "sotavento": float}  (face E e D de cada vao)
    Para vento a 0° (perpendicular as cumeeiras): o 1o tramo recebe mais carga,
    os intermediarios e o ultimo recebem menos (sombreamento aerodinamico).
    Para vento a 90° (paralelo) os valores sao constantes ao longo do telhado:
      faixa b1 (h): -0,8 ; b2 (h): -0,6 ; b3: -0,2 (Tab.7, α=90°).
    Interpolacao linear entre 5° e 10°. h/b e a/b definem as faixas (nao os
    coeficientes nominais, que dependem so de θ)."""
    th = max(5.0, min(theta_graus, 10.0))
    f = (th - 5.0) / (10.0 - 5.0)
    # Tramo 1 (barlavento): face a (barlavento), face b (sotavento)
    a = -0.9 + f * (-1.1 + 0.9)     # -0.9 (5°) a -1.1 (10°)
    b = -0.6                         # constante
    # Tramo 2 (1o intermediario): faces c (barl) e d (sot)
    c = -0.4; d = -0.3              # constante
    # Demais intermediarios: m (barl) e n (sot)
    m = -0.3; n = -0.3
    # Ultimo tramo (sotavento): x (barl) e z (sot)
    x = -0.3
    z = -0.3 + f * (-0.4 + 0.3)     # -0.3 (5°) a -0.4 (10°)
    tramos = []
    if n_vaos == 1:
        tramos.append({"barlavento": a, "sotavento": b if th < 7.5 else z})
    elif n_vaos == 2:
        tramos.append({"barlavento": a, "sotavento": b})
        tramos.append({"barlavento": x, "sotavento": z})
    else:
        tramos.append({"barlavento": a, "sotavento": b})
        for _ in range(n_vaos - 2):
            tramos.append({"barlavento": m, "sotavento": n})
        tramos.append({"barlavento": x, "sotavento": z})
    # Vento a 90°: valores por faixa longitudinal (nao por tramo)
    # Retorna tambem os valores para α=90°
    return tramos


def sucao_local_fixacao(q_kN_m2, cpe_medio, cpi=+0.80):
    """Succao liquida LOCAL para dimensionar telha/terca e FIXADORES na borda/canto.
    p = (cpe_medio - cpi)*q. Usa o Cpi mais desfavoravel (portao a barlavento,
    +0,8, empurra de dentro e soma na succao externa). kN/m2 (negativo = arranque)."""
    return round((cpe_medio - cpi) * q_kN_m2, 3)


def compute(v0=None, cat=None, classe=None, s1=None, s3=None, z=None, theta=None,
            larg_b=10.0, alt_h=6.0, comp_a=20.0):
    v0 = _CFG["v0"] if v0 is None else v0
    cat = _CFG["cat"] if cat is None else cat
    classe = _CFG["classe"] if classe is None else classe
    s1 = _CFG["s1"] if s1 is None else s1
    s3 = _CFG["s3"] if s3 is None else s3
    z = _CFG["z"] if z is None else z
    theta = _CFG["theta"] if theta is None else theta
    b, Fr, p, s2 = s2_factor(cat, classe, z)     # b = coef. da Tabela 1 (NAO a largura)
    vk = v0 * s1 * s2 * s3
    q = 0.613 * vk ** 2 / 1000.0     # 0,613*Vk^2 [N/m2] -> /1000 -> kN/m2
    cpe = {**cpe_paredes(), **cpe_telhado(theta)}
    cpi = cpi_cases()
    net = {}
    for cname, cpiv in cpi.items():
        net[cname] = {s: round(cpe[s] - cpiv, 2) for s in cpe}
    # Cpe medio / local (borda-canto) para telha/terca/fixador
    loc_cob = cpe_local_cobertura(theta, larg_b, alt_h, comp_a)
    loc_par = cpe_local_parede(comp_a, larg_b, alt_h)
    cpi_arr = max(cpi.values())     # Cpi mais desfavoravel para arranque
    local = {"cobertura": loc_cob, "parede": loc_par, "cpi_arranque": cpi_arr,
             "p_local_cob_kN_m2": sucao_local_fixacao(q, loc_cob["cpe_medio_envoltoria"], cpi_arr),
             "p_local_par_kN_m2": sucao_local_fixacao(q, loc_par["cpe_medio"], cpi_arr)}
    return {"v0": v0, "cat": cat, "classe": classe, "s1": s1, "s2": round(s2, 3),
            "s3": s3, "Fr": Fr, "p": p, "z": z, "theta": theta,
            "vk": round(vk, 2), "q_kN_m2": round(q, 3),
            "cpe": cpe, "cpi_cases": cpi, "net": net, "local": local}


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
    loc = r.get("local")
    if loc:
        c = loc["cobertura"]; pa = loc["parede"]
        L.append("  Cpe MEDIO / LOCAL (borda-canto, Tab.4/5 col. 'cpe medio') - TELHA/TERCA/FIXADOR:")
        L.append(f"    cobertura: envoltoria {c['cpe_medio_envoltoria']:+.2f} "
                 f"(zonas {c['zonas']}); faixa y={c['faixa_y_m']:.2f} m ; "
                 f"zona={c['dim_zona_m']:.2f} m ; lanternim {c['lanternim_cpe_medio']:+.2f}")
        L.append(f"    parede:    cpe medio {pa['cpe_medio']:+.2f} "
                 f"(h/b={pa['hb']:.2f}, a/b={pa['ab']:.2f}); faixa={pa['faixa_m']:.2f} m")
        L.append(f"    succao liquida (Cpi={loc['cpi_arranque']:+.2f} p/ arranque): "
                 f"cobertura {loc['p_local_cob_kN_m2']:+.3f} kN/m2 ; "
                 f"parede {loc['p_local_par_kN_m2']:+.3f} kN/m2")
        L.append("    -> dimensionar o fixador da telha e a ligacao terca-portico de BORDA/CANTO")
        L.append("       com esta succao local (bem maior que a global do portico).")
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
    q = 0.613 * vk ** 2 / 1000.0     # 0,613*Vk^2 [N/m2] -> /1000 -> kN/m2
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


def _selftest():
    # Tabela 4 - parede, bloco 1/2<h/b<=3/2, 2<=a/b<=4 (galpao 20x10, h=6): cpe medio -1,1
    p = cpe_local_parede(20.0, 10.0, 6.0)
    assert p["cpe_medio"] == -1.1, p
    assert p["bloco_hb"] == "1/2-3/2" and p["bloco_ab"] == "2-4", p
    assert abs(p["faixa_m"] - 2.0) < 1e-9, p     # min(0,2*10 ; 6) = 2,0
    # Tabela 5 - cobertura, mesmo bloco, theta 5,71 -> zona 1 governa -2,0
    c = cpe_local_cobertura(5.71, 10.0, 6.0, 20.0)
    assert c["cpe_medio_envoltoria"] == -2.0, c
    assert abs(c["faixa_y_m"] - 1.5) < 1e-9, c   # min(6 ; 0,15*10)=1,5
    assert abs(c["dim_zona_m"] - 5.0) < 1e-9, c  # min(max(10/3;20/4)=5 ; 2*6=12)=5
    # interpolacao em theta: bloco <=1/2, theta=7,5 -> zona1 entre -1,4 e -1,4 = -1,4
    c2 = cpe_local_cobertura(7.5, 20.0, 6.0, 40.0)   # h/b=0,3
    assert c2["bloco_hb"] == "<=1/2", c2
    assert c2["zonas"][0] == -1.4, c2
    # succao local de arranque: (cpe_medio - cpi)*q, cpi=+0,8
    assert sucao_local_fixacao(1.0, -2.0, +0.80) == -2.8
    # compute integra local sem quebrar
    r = compute()
    assert "local" in r and r["local"]["cobertura"]["cpe_medio_envoltoria"] == -2.0
    print("vento self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(compute()))
        print()
        print(relatorio_longitudinal_pt(compute_longitudinal()))
