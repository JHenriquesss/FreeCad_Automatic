# ============================================================================
# pilar_concreto.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Dimensiona a armadura longitudinal de um PILAR de concreto armado submetido a
# FLEXAO COMPOSTA (flexo-compressao), ABNT NBR 6118:2014. Cobre o que faltava no
# vertical de concreto (o baldrame/fundacao ja tratavam flexao simples, cortante,
# ancoragem e flecha):
#   1) ESBELTEZ (15.8.2): lambda = raiz(12)*le/h ; esbeltez limite lambda1 =
#      (25 + 12,5*e1/h)/alpha_b, com 35 <= lambda1 <= 90 ; alpha_b por vinculacao.
#   2) 2a ORDEM - metodo do PILAR-PADRAO com CURVATURA APROXIMADA (15.8.3.3.2):
#      1/r = 0,005/[h*(nu+0,5)] <= 0,005/h ; e2 = le^2/10 * 1/r ;
#      Md,tot = alpha_b*M1d,A + Nd*e2 >= M1d,A, por direcao.
#   3) MOMENTO MINIMO de 1a ordem (11.3.3.4.3): M1d,min = Nd*(0,015 + 0,03*h) [h em m].
#   4) COEF. DE SECAO PEQUENA gamma_n (13.2.3, Tab.13.1): b<19 cm -> 1,95 - 0,05*b.
#   5) RESISTENCIA da secao (17.2.2): solver de flexao composta reta por
#      compatibilidade de deformacoes (dominios 2-5, pivos 10/3,5/2 por mil), bloco
#      retangular 0,8x/0,85fcd. As/2 em cada face perpendicular a excentricidade.
#   6) ARMADURA MINIMA/MAXIMA (17.3.5.3): As,min = max(0,15*Nd/fyd ; 0,004*Ac) ;
#      As,max = 0,08*Ac (0,04*Ac por lance, considerando emenda).
# Valores da norma conferidos LITERALMENTE (NotebookLM: NBR 6118 15.8/11.3/17.3) e
# o solver aferido contra 3 exemplos resolvidos de Bastos (UNESP) - NAO de memoria.
# Unidades: m, kN ; fck/fyk em kN/m2. Saidas em portugues.
# ============================================================================
"""Pilar de concreto armado em flexao composta (NBR 6118:2014): esbeltez, 2a ordem
pelo pilar-padrao (curvatura aproximada), momento minimo, gamma_n de secao pequena e
armadura por compatibilidade de deformacoes. Unidades: m, kN, fck/fyk em kN/m2."""

from __future__ import annotations

import math

# --- coeficientes de ponderacao (ELU, combinacao normal) --------------------
GAMMA_C = 1.4
GAMMA_S = 1.15
GAMMA_F = 1.4

# --- diagrama de deformacoes (fck <= 50 MPa), NBR 6118 8.2.10 / 17.2.2 -------
EPS_CU = 0.0035        # encurtamento ultimo do concreto (3,5 por mil)
EPS_C2 = 0.0020        # deformacao no pivo C / dominio 5 (2 por mil)
EPS_SU = 0.0100        # alongamento maximo do aco (10 por mil), 17.2.2
ES_ACO = 210e6         # modulo de elasticidade do aco (kN/m2), 8.3.6
LAMBDA_BLOCO = 0.80    # altura do bloco retangular de tensoes, 17.2.2 (fck<=50)
ALPHA_C = 0.85         # tensao do bloco = 0,85*fcd, 17.2.2 (fck<=50)


def esbeltez(le, h):
    """Indice de esbeltez de secao retangular (15.8.2): lambda = le/i, i = h/raiz(12)
    -> lambda = raiz(12)*le/h. le e h na MESMA direcao (m)."""
    return math.sqrt(12.0) * le / h


def alpha_b(caso_dir):
    """Coeficiente alpha_b (15.8.2), por vinculacao/diagrama de M1 na direcao:
      - 'balanco'  (pilar em balanco): 0,80 + 0,20*Mc/Ma, com 0,85 <= alpha_b <= 1,0;
      - 'biapoiado' sem cargas transversais: 0,60 + 0,40*Mb/Ma, com 0,40 <= alpha_b <= 1,0
        (Ma>=|Mb|; Mb/Ma NEGATIVO se tracionar faces opostas -> curvatura reversa);
      - sem momento de 1a ordem (pilar intermediario) ou com carga transversal: 1,0.
    caso_dir: {'tipo', 'Ma', 'Mb' ou 'Mc'}. Retorna alpha_b."""
    tipo = caso_dir.get("tipo", "biapoiado")
    Ma = abs(caso_dir.get("Ma", 0.0))
    if Ma <= 0.0:
        return 1.0
    if caso_dir.get("carga_transversal", False):
        return 1.0
    if tipo == "balanco":
        Mc = caso_dir.get("Mc", 0.0)
        ab = 0.80 + 0.20 * Mc / Ma
        return min(max(ab, 0.85), 1.0)
    # biapoiado sem cargas transversais
    Mb = caso_dir.get("Mb", 0.0)             # sinal: + mesma curvatura, - reversa
    ab = 0.60 + 0.40 * Mb / Ma
    return min(max(ab, 0.40), 1.0)


def gamma_n(b_cm):
    """Coeficiente adicional gamma_n para secao pequena (13.2.3 / Tab.13.1): majora
    TODOS os esforcos quando 14 <= b < 19 cm ; gamma_n = 1,95 - 0,05*b (b em cm).
    Secao minima absoluta 360 cm2 e dimensao minima 14 cm (fora disso -> erro)."""
    if b_cm >= 19.0:
        return 1.0
    if b_cm < 14.0 - 1e-9:
        raise ValueError("dimensao < 14 cm nao permitida (NBR 6118 13.2.3)")
    return 1.95 - 0.05 * b_cm


def lambda_1(e1, h, ab):
    """Esbeltez limite lambda1 (15.8.2): (25 + 12,5*e1/h)/alpha_b, com 35<=lambda1<=90.
    e1 e h na mesma direcao (m). e1 = excentricidade de 1a ordem (M1d,A/Nd)."""
    l1 = (25.0 + 12.5 * e1 / h) / ab
    return min(max(l1, 35.0), 90.0)


def momento_minimo(Nd, h):
    """Momento fletor minimo de 1a ordem (11.3.3.4.3): M1d,min = Nd*(0,015 + 0,03*h),
    h em METROS na direcao considerada. Retorna kN.m."""
    return Nd * (0.015 + 0.03 * h)


def curvatura(h, nu):
    """Curvatura aproximada na secao critica (15.8.3.3.2): 1/r = 0,005/[h*(nu+0,5)]
    <= 0,005/h. nu = Nd/(Ac*fcd) (forca normal adimensional). h em m -> 1/r em 1/m."""
    inv_r = 0.005 / (h * (nu + 0.5))
    return min(inv_r, 0.005 / h)


# ---------------------------------------------------------------------------
# Solver de resistencia: FLEXAO COMPOSTA RETA por compatibilidade de deformacoes
# ---------------------------------------------------------------------------
def _eps_fibra(z, x, d, h):
    """Deformacao (COMPRESSAO POSITIVA) na fibra a distancia z da face mais
    comprimida, para linha neutra a profundidade x. Pivos da NBR 6118 (17.2.2):
      - x <= 0,259d  -> dominio 2: pivo no aco tracionado (EPS_SU em z=d);
      - 0,259d < x <= h -> dominios 3/4: pivo no concreto (EPS_CU na face z=0);
      - x > h -> dominio 5: pivo C (EPS_C2 na fibra z=3h/7)."""
    x23 = d * EPS_CU / (EPS_CU + EPS_SU)          # 0,259d (fronteira dom.2/3)
    if x <= x23:
        k = EPS_SU / (d - x) if d > x else EPS_CU / max(x, 1e-12)
    elif x <= h:
        k = EPS_CU / x
    else:
        k = EPS_C2 / (x - 3.0 * h / 7.0)
    return k * (x - z)


def _sigma_s(eps, fyd):
    """Tensao no aco (elastoplastico perfeito), compressao positiva. kN/m2."""
    return max(-fyd, min(fyd, ES_ACO * eps))


def _sigma_c(eps, fcd):
    """Tensao do concreto pelo diagrama PARABOLA-RETANGULO (17.2.2, fck<=50, n=2):
    0,85fcd*[1-(1-eps/0,002)^2] p/ 0<=eps<0,002 ; 0,85fcd p/ 0,002<=eps<=0,0035.
    Compressao positiva; tracao -> 0. kN/m2. (Diagrama de referencia dos abacos de
    pilar; o bloco retangular equivalente fica na viga/sapata em flexao simples.)"""
    if eps <= 0.0:
        return 0.0
    if eps >= EPS_C2:
        return ALPHA_C * fcd
    return ALPHA_C * fcd * (1.0 - (1.0 - eps / EPS_C2) ** 2)


def _resultante_concreto(x, b, h, d, fck, n=60):
    """Integra o diagrama parabola-retangulo na zona comprimida (regra do ponto
    medio, n faixas): retorna (Rcc [kN], Mcc [kN.m] em relacao ao CG)."""
    fcd = fck / GAMMA_C
    dz = h / n
    Rcc = 0.0
    Mcc = 0.0
    for i in range(n):
        z = (i + 0.5) * dz
        s = _sigma_c(_eps_fibra(z, x, d, h), fcd)
        f = s * b * dz
        Rcc += f
        Mcc += f * (h / 2.0 - z)
    return Rcc, Mcc


def _N_M_resistente(x, As, b, h, dl, fck, fyk):
    """Esforcos resistentes (NRd, MRd em relacao ao CG) da secao retangular b*h com
    As/2 em cada face (a dl das bordas), para linha neutra x. Concreto pelo diagrama
    parabola-retangulo. Compressao positiva. As em m2 ; retorna (NRd [kN], MRd [kN.m])."""
    fcd = fck / GAMMA_C
    fyd = fyk / GAMMA_S
    d = h - dl                                    # aco tracionado (face oposta)
    Rcc, Mcc = _resultante_concreto(x, b, h, d, fck)
    eps_c = _eps_fibra(dl, x, d, h)               # aco junto a face comprimida
    eps_t = _eps_fibra(d, x, d, h)                # aco junto a face tracionada
    # desconta o concreto DESLOCADO pelo aco comprimido (tensao real na fibra)
    sig_c = _sigma_s(eps_c, fyd) - _sigma_c(eps_c, fcd)
    sig_t = _sigma_s(eps_t, fyd)
    Rs_c = (As / 2.0) * sig_c
    Rs_t = (As / 2.0) * sig_t
    NRd = Rcc + Rs_c + Rs_t
    MRd = Mcc + Rs_c * (h / 2.0 - dl) + Rs_t * (-(h / 2.0 - dl))
    return NRd, MRd


def _x_para_Nd(Nd, As, b, h, dl, fck, fyk):
    """Acha a profundidade x da linha neutra que equilibra a forca normal Nd
    (NRd(x)=Nd) por bisseccao. NRd e monotona crescente em x."""
    lo, hi = 1e-5, 20.0 * h                        # x pode passar de h (dominio 5)
    N_lo, _ = _N_M_resistente(lo, As, b, h, dl, fck, fyk)
    N_hi, _ = _N_M_resistente(hi, As, b, h, dl, fck, fyk)
    if Nd <= N_lo:
        return lo
    if Nd >= N_hi:
        return hi
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        Nm, _ = _N_M_resistente(mid, As, b, h, dl, fck, fyk)
        if Nm < Nd:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def MRd_para_Nd(Nd, As, b, h, dl, fck, fyk):
    """Momento resistente MRd para a forca normal Nd atuante e armadura As total
    (m2). Acha x tal que NRd(x)=Nd e devolve o MRd correspondente (kN.m, >=0)."""
    x = _x_para_Nd(Nd, As, b, h, dl, fck, fyk)
    _, MRd = _N_M_resistente(x, As, b, h, dl, fck, fyk)
    return abs(MRd)


def armadura_flexao_composta(Nd, Md, b, h, dl, fck, fyk, As_max=None):
    """Armadura TOTAL As (m2) de flexao composta reta: menor As tal que
    MRd_para_Nd(Nd, As) >= |Md|. Bisseccao em As (MRd e monotona crescente em As).
    Retorna (As, ok) ; ok=False se nem As_max resiste."""
    Md = abs(Md)
    if As_max is None:
        As_max = 0.08 * b * h                      # teto absoluto 8% (17.3.5.3.2)
    if MRd_para_Nd(Nd, 0.0, b, h, dl, fck, fyk) >= Md:
        return 0.0, True                           # so concreto ja resiste
    if MRd_para_Nd(Nd, As_max, b, h, dl, fck, fyk) < Md:
        return As_max, False                       # nem no teto resiste
    lo, hi = 0.0, As_max
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if MRd_para_Nd(Nd, mid, b, h, dl, fck, fyk) < Md:
            lo = mid
        else:
            hi = mid
    return hi, True


# ---------------------------------------------------------------------------
# Orquestrador: dimensionamento completo do pilar
# ---------------------------------------------------------------------------
def dimensiona_pilar(caso):
    """Dimensiona a armadura longitudinal de um pilar retangular em flexo-compressao.

    caso: {
      'b', 'h'        : dimensoes da secao (m). Convencao: 'x' // h ('hx'), 'y' // b ('hy').
      'Nk'            : forca normal caracteristica de compressao (kN, >0).
      'le_x','le_y'   : comprimentos de flambagem em cada direcao (m).
      'fck','fyk'     : resistencias (kN/m2). 'dl' = d' (m, default 0,04).
      'M1d_x','M1d_y' : (opcional) dict {'tipo','Ma','Mb'/'Mc','carga_transversal'} com
                        os momentos de 1a ordem de CALCULO (kN.m) em cada direcao;
                        ausente -> pilar intermediario (M1=0).
      'gamma_f'       : default 1,4.
    }
    hx = dimensao na direcao x (=h) ; hy = dimensao na direcao y (=b). Retorna dict."""
    hx = caso["h"]; hy = caso["b"]
    fck = caso["fck"]; fyk = caso["fyk"]
    dl = caso.get("dl", 0.04)
    Ac = hx * hy
    fcd = fck / GAMMA_C
    fyd = fyk / GAMMA_S
    gf = caso.get("gamma_f", GAMMA_F)
    gn = gamma_n(min(hx, hy) * 100.0)             # secao pequena majora TUDO
    Nd = gn * gf * caso["Nk"]
    nu = Nd / (Ac * fcd)                          # forca normal adimensional

    res = {"hx": hx, "hy": hy, "Ac_cm2": round(Ac * 1e4, 1), "Nd": round(Nd, 1),
           "gamma_n": round(gn, 3), "nu": round(nu, 3), "dir": {}}

    Md_gov = 0.0
    dep_gov, wid_gov = hx, hy                     # geometria do solver na dir. critica
    # Para flexao na direcao d, a PROFUNDIDADE da secao (onde varia a deformacao) e a
    # dimensao NAQUELA direcao (hcol) e a LARGURA e a dimensao ortogonal (houtro); o
    # aco vai nas duas faces perpendiculares a excentricidade.
    for dirn, hcol, houtro, le_key, m_key in (("x", hx, hy, "le_x", "M1d_x"),
                                              ("y", hy, hx, "le_y", "M1d_y")):
        le = caso.get(le_key, caso.get("le", 0.0))
        lam = esbeltez(le, hcol)
        md = caso.get(m_key) or {}
        # Ma/Mb: momentos de 1a ordem de CALCULO M1d (gamma_f e gamma_n ja embutidos,
        # como saem da envoltoria do modelo). alpha_b usa a RAZAO Mb/Ma (invariante).
        M1dA = abs(md.get("Ma", 0.0))
        ab = alpha_b(md)
        e1 = M1dA / Nd if Nd > 0 else 0.0
        l1 = lambda_1(e1, hcol, ab)
        M1min = momento_minimo(Nd, hcol)
        # base de 1a ordem: alpha_b*M1d,A, com piso no momento minimo (11.3.3.4.3):
        # a norma (15.8.3.3.2) exige alpha_b*M1d,A >= M1d,min.
        M1d_base = max(ab * M1dA, M1min)
        if lam <= l1:                            # dispensa 2a ordem nesta direcao
            e2 = 0.0; M2 = 0.0
            Mtot = M1d_base
        else:
            inv_r = curvatura(hcol, nu)
            e2 = le ** 2 / 10.0 * inv_r
            M2 = Nd * e2                          # M2 SOMA-SE a base de 1a ordem
            Mtot = M1d_base + M2
        res["dir"][dirn] = {
            "le": le, "lambda": round(lam, 1), "lambda1": round(l1, 1),
            "alpha_b": round(ab, 3), "e1_cm": round(e1 * 100, 2),
            "M1d_min": round(M1min, 2), "M1d_A": round(M1dA, 2),
            "considera_2a": lam > l1, "e2_cm": round(e2 * 100, 2),
            "M2d": round(M2, 2), "Md_tot": round(Mtot, 2),
        }
        if Mtot > Md_gov:
            Md_gov = Mtot
            dep_gov, wid_gov = hcol, houtro       # profundidade/largura desta direcao

    # armadura pela direcao critica (maior Md_tot) - secao retangular, aco nas duas
    # faces perpendiculares a excentricidade (pratica de Bastos p/ pilar retangular).
    As_max = 0.08 * Ac
    As, ok_res = armadura_flexao_composta(Nd, Md_gov, wid_gov, dep_gov, dl,
                                          fck, fyk, As_max=As_max)
    As_min = max(0.15 * Nd / fyd, 0.004 * Ac)
    As_ad = max(As, As_min)
    taxa = As_ad / Ac
    # teto por lance (emenda dobra a armadura -> 4% por lance, 17.3.5.3.2)
    ok_max = As_ad <= 0.04 * Ac + 1e-12
    OK = ok_res and ok_max and min(hx, hy) >= 0.14 - 1e-9 and Ac >= 0.036 - 1e-9

    res.update({
        "Md_gov": round(Md_gov, 2), "As_calc_cm2": round(As * 1e4, 2),
        "As_min_cm2": round(As_min * 1e4, 2), "As_cm2": round(As_ad * 1e4, 2),
        "taxa_pct": round(taxa * 100, 2), "As_max_cm2": round(0.04 * Ac * 1e4, 2),
        "resiste": ok_res, "ok_taxa_max": ok_max, "OK": OK,
    })
    return res


def relatorio_pt(r):
    L = ["PILAR DE CONCRETO ARMADO - FLEXAO COMPOSTA (ABNT NBR 6118:2014)",
         f"  Secao hx x hy = {r['hx']*100:.0f} x {r['hy']*100:.0f} cm "
         f"(Ac = {r['Ac_cm2']:.0f} cm2) ; Nd = {r['Nd']:.0f} kN "
         f"(gamma_n = {r['gamma_n']:.2f}) ; nu = {r['nu']:.2f}"]
    for dn in ("x", "y"):
        d = r["dir"][dn]
        L.append(f"  Direcao {dn}: lambda = {d['lambda']:.1f} ; lambda1 = {d['lambda1']:.1f} "
                 f"(alpha_b = {d['alpha_b']:.2f}) -> "
                 + ("considera 2a ordem" if d["considera_2a"] else "dispensa 2a ordem"))
        L.append(f"     M1d,min = {d['M1d_min']:.1f} ; M1d,A = {d['M1d_A']:.1f} ; "
                 f"e2 = {d['e2_cm']:.2f} cm ; M2d = {d['M2d']:.1f} ; "
                 f"Md,tot = {d['Md_tot']:.1f} kN.m")
    L += [f"  Direcao critica: Md,tot = {r['Md_gov']:.1f} kN.m",
          f"  As (flexo-compressao) = {r['As_calc_cm2']:.2f} cm2 ; "
          f"As,min = {r['As_min_cm2']:.2f} cm2 -> As adotado = {r['As_cm2']:.2f} cm2 "
          f"(taxa {r['taxa_pct']:.2f} %) "
          + ("" if r["resiste"] else "; SECAO NAO RESISTE (aumentar) ")
          + ("" if r["ok_taxa_max"] else "; TAXA > 4% por lance (aumentar secao)"),
          f"  RESULTADO: {'APROVADO' if r['OK'] else 'REPROVADO'}",
          "  [A CONFIRMAR: esforcos (Nk, M1d) e comprimentos de flambagem do modelo.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    """Afere o solver e o pilar-padrao contra 3 exemplos resolvidos de Bastos (UNESP,
    'Pilares de Concreto Armado'), C30/CA-50 - NAO de memoria."""
    # Ex.1: pilar intermediario 20x50, Nk=1000, le=280 -> As=10,84 cm2 (abaco A-4)
    r1 = dimensiona_pilar({"b": 0.20, "h": 0.50, "Nk": 1000.0, "le_x": 2.80,
                           "le_y": 2.80, "fck": 30e3, "fyk": 500e3, "dl": 0.04})
    assert abs(r1["dir"]["y"]["lambda"] - 48.4) < 0.3, r1["dir"]["y"]
    assert r1["dir"]["y"]["lambda1"] == 35.0
    assert abs(r1["nu"] - 0.65) < 0.01
    assert abs(r1["dir"]["y"]["e2_cm"] - 1.70) < 0.05
    assert abs(r1["Md_gov"] - 53.2) < 0.3, r1["Md_gov"]           # 5320 kN.cm
    assert abs(r1["As_cm2"] - 10.84) < 0.6, r1["As_cm2"]          # abaco ~+-5%
    # Ex.2: idem, le=480 -> As=31,03 cm2
    r2 = dimensiona_pilar({"b": 0.20, "h": 0.50, "Nk": 1000.0, "le_x": 4.80,
                           "le_y": 4.80, "fck": 30e3, "fyk": 500e3, "dl": 0.04})
    assert abs(r2["dir"]["y"]["e2_cm"] - 5.00) < 0.1
    assert abs(r2["Md_gov"] - 99.4) < 0.5, r2["Md_gov"]
    assert abs(r2["As_cm2"] - 31.03) < 2.0, r2["As_cm2"]
    # Ex.5: pilar de extremidade 15x40, Nk=500, M1d,A,x=35, M1d,B,x=20 -> alpha_b, gamma_n
    r5 = dimensiona_pilar({"b": 0.40, "h": 0.15, "Nk": 500.0, "le_x": 2.80,
                           "le_y": 2.80, "fck": 30e3, "fyk": 500e3, "dl": 0.03,
                           "M1d_x": {"tipo": "biapoiado", "Ma": 35.0, "Mb": 20.0}})
    assert abs(r5["Nd"] - 840.0) < 1.0, r5["Nd"]                  # gamma_n=1,20
    assert abs(r5["gamma_n"] - 1.20) < 1e-6
    assert abs(r5["dir"]["x"]["alpha_b"] - 0.83) < 0.01
    assert abs(r5["dir"]["x"]["e1_cm"] - 4.17) < 0.05
    assert abs(r5["dir"]["x"]["Md_tot"] - 48.0) < 0.5, r5["dir"]["x"]["Md_tot"]
    print("pilar_concreto self-test PASSED (Bastos Ex.1/2/5)")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        # Bastos Exemplo 1: 20x50, C30, Nk=1000, le=280 -> As ~ 10,84 cm2
        caso = {"b": 0.20, "h": 0.50, "Nk": 1000.0, "le_x": 2.80, "le_y": 2.80,
                "fck": 30e3, "fyk": 500e3, "dl": 0.04, "gamma_f": 1.4}
        print(relatorio_pt(dimensiona_pilar(caso)))
