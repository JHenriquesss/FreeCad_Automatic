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
EPS_CU = 0.0035        # encurtamento ultimo do concreto (3,5 por mil, C50)
EPS_C2 = 0.0020        # deformacao no pivo C / dominio 5 (2 por mil, C50)
EPS_SU = 0.0100        # alongamento maximo do aco (10 por mil), 17.2.2
ES_ACO = 210e6         # modulo de elasticidade do aco (kN/m2), 8.3.6
LAMBDA_BLOCO = 0.80    # altura do bloco retangular de tensoes, 17.2.2 (fck<=50)
ALPHA_C = 0.85         # tensao do bloco = 0,85*fcd, 17.2.2 (fck<=50)


def eps_cu(fck_MPa=None):
    """Encurtamento ultimo (NBR 6118 8.2.10.1 Fig.8.2, G50).
    C50: 3,5 por mil ; C55-C90: 2,6+35*[(90-fck)/100]^4 por mil."""
    if fck_MPa is None or fck_MPa <= 50.0:
        return EPS_CU
    return (2.6 + 35.0 * ((90.0 - fck_MPa) / 100.0) ** 4) / 1000.0


def eps_c2(fck_MPa=None):
    """Deformacao do pivo C (NBR 6118 8.2.10.1 Fig.8.2, G50).
    C50: 2,0 por mil ; C55-C90: 2,0+0,085*(fck-50)^0,53 por mil."""
    if fck_MPa is None or fck_MPa <= 50.0:
        return EPS_C2
    return (2.0 + 0.085 * (fck_MPa - 50.0) ** 0.53) / 1000.0


def expoente_n(fck_MPa=None):
    """Expoente n do parabola-retangulo (NBR 6118 8.2.10.1 Fig.8.2, G50).
    C50: 2,0 ; C55-C90: 1,4+23,4*[(90-fck)/100]^4."""
    if fck_MPa is None or fck_MPa <= 50.0:
        return 2.0
    return 1.4 + 23.4 * ((90.0 - fck_MPa) / 100.0) ** 4


def alpha_c_pilar(fck_MPa=None):
    """Tensao do bloco parabola-retangulo (NBR 6118 17.2.2, G50).
    C50: 0,85 ; C55-C90: 0,85*[1-(fck-50)/200]."""
    if fck_MPa is None or fck_MPa <= 50.0:
        return ALPHA_C
    return 0.85 * (1.0 - (fck_MPa - 50.0) / 200.0)


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


# --- limites de esbeltez (15.8.1 / 15.8.3.2 / 15.8.3.3.2 / 15.8.4) ----------
# Conferidos LITERALMENTE no texto da NBR 6118:2014 (NotebookLM, citacao do texto
# bruto). Sao FAIXAS DE VALIDADE, nao utilizacoes: nao aparecem como razao
# solicitante/resistente e por isso "passam" caladas se nao houver gate proprio.
LAMBDA_MAX = 200.0              # 15.8.1: "os pilares devem ter lambda <= 200"
LAMBDA_CURVATURA_APROX = 90.0   # 15.8.3.3.2: "pode ser empregado apenas ... lambda <= 90"
LAMBDA_METODO_GERAL = 140.0     # 15.8.3.2: "o metodo geral e obrigatorio para lambda > 140"
LAMBDA_FLUENCIA = 90.0          # 15.8.4: fluencia obrigatoria para lambda > 90
NU_POUCO_COMPRIMIDO = 0.10      # 15.8.1: ressalva de N_d < 0,10 fcd Ac


def gamma_n1(lam):
    """Coeficiente adicional para pilares com lambda > 140 (15.8.1):
    gamma_n1 = 1 + [0,01*(lambda - 140)/1,4]. Abaixo de 140 vale 1,0."""
    if lam <= LAMBDA_METODO_GERAL:
        return 1.0
    return 1.0 + 0.01 * (lam - LAMBDA_METODO_GERAL) / 1.4


def valida_esbeltez(lam, nu):
    """Faixa de validade do metodo implementado (pilar-padrao com CURVATURA
    APROXIMADA) e limites absolutos da norma, para UMA direcao.

    lam: indice de esbeltez naquela direcao. nu: N_d/(Ac*fcd) (forca normal
    adimensional de CALCULO, como pede a Emenda 1 da 15.8.1).

    Devolve {'ok', 'avisos', 'exige_metodo_geral', 'exige_fluencia', 'gamma_n1'}.
    ok=False significa que o resultado do metodo aproximado NAO pode ser usado -
    nao que a secao esteja "quase passando". Sem este gate o modulo devolve um As
    perfeitamente calculado para um pilar que a norma nem admite."""
    avisos = []
    ok = True
    if lam > LAMBDA_MAX:
        if nu < NU_POUCO_COMPRIMIDO:
            avisos.append(
                "lambda = %.1f > 200, admitido apenas porque o elemento e pouco "
                "comprimido (nu = %.3f < 0,10), ressalva de 15.8.1" % (lam, nu))
        else:
            ok = False
            avisos.append(
                "REPROVA (15.8.1): lambda = %.1f > 200 e o elemento NAO e pouco "
                "comprimido (nu = %.3f >= 0,10). A norma nao admite este pilar."
                % (lam, nu))
    if lam > LAMBDA_CURVATURA_APROX:
        ok = False
        avisos.append(
            "REPROVA (15.8.3.3.2): lambda = %.1f > 90. O metodo do pilar-padrao com "
            "curvatura aproximada, que este modulo implementa, 'pode ser empregado "
            "apenas no calculo de pilares com lambda <= 90'. O resultado abaixo esta "
            "FORA da faixa de validade do metodo - use o metodo geral (obrigatorio "
            "acima de 140) ou o pilar-padrao acoplado a diagramas M,N,1/r." % lam)
    if lam > LAMBDA_FLUENCIA:
        avisos.append(
            "15.8.4: lambda = %.1f > 90 -> a consideracao da FLUENCIA e obrigatoria "
            "(excentricidade adicional e_cc), e nao esta implementada aqui." % lam)
    if lam > LAMBDA_METODO_GERAL:
        avisos.append(
            "15.8.1: lambda = %.1f > 140 -> os esforcos finais de calculo teriam de "
            "ser majorados por gamma_n1 = %.3f, alem de exigir o metodo geral."
            % (lam, gamma_n1(lam)))
    return {"ok": ok, "avisos": avisos,
            "exige_metodo_geral": lam > LAMBDA_METODO_GERAL,
            "exige_fluencia": lam > LAMBDA_FLUENCIA,
            "gamma_n1": round(gamma_n1(lam), 4)}


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
def _eps_fibra(z, x, d, h, fck=None):
    """Deformacao (COMPRESSAO POSITIVA) na fibra a distancia z da face mais
    comprimida, para linha neutra a profundidade x. Pivos da NBR 6118 (17.2.2
    + 8.2.10.1 Fig.8.2, G50): fck em kN/m2 (None = C50 legado).
      - x <= x23  -> dominio 2: pivo no aco tracionado (EPS_SU em z=d);
      - x23 < x <= h -> dominios 3/4: pivo no concreto (eps_cu na face z=0);
      - x > h -> dominio 5: pivo C (eps_c2 na fibra z=3h/7)."""
    fck_MPa = fck / 1000.0 if fck is not None else None
    ecu = eps_cu(fck_MPa)
    ec2 = eps_c2(fck_MPa)
    x23 = d * ecu / (ecu + EPS_SU)          # 0,259d em C50 (fronteira dom.2/3)
    if x <= x23:
        k = EPS_SU / (d - x) if d > x else ecu / max(x, 1e-12)
    elif x <= h:
        k = ecu / x
    else:
        k = ec2 / (x - 3.0 * h / 7.0)
    return k * (x - z)


def _sigma_s(eps, fyd):
    """Tensao no aco (elastoplastico perfeito), compressao positiva. kN/m2."""
    return max(-fyd, min(fyd, ES_ACO * eps))


def _sigma_c(eps, fcd, fck=None):
    """Tensao do concreto pelo diagrama PARABOLA-RETANGULO (17.2.2 + 8.2.10.1
    Fig.8.2, G50): alpha_c*fcd*[1-(1-eps/eps_c2)^n] p/ 0<=eps<eps_c2 ;
    alpha_c*fcd p/ eps_c2<=eps<=eps_cu. fck em kN/m2 (None = C50 legado:
    0,85fcd*[1-(1-eps/0,002)^2]).
    Compressao positiva; tracao -> 0. kN/m2. (Diagrama de referencia dos abacos de
    pilar; o bloco retangular equivalente fica na viga/sapata em flexao simples.)"""
    fck_MPa = fck / 1000.0 if fck is not None else None
    ec2 = eps_c2(fck_MPa)
    nn = expoente_n(fck_MPa)
    ac = alpha_c_pilar(fck_MPa)
    if eps <= 0.0:
        return 0.0
    if eps >= ec2:
        return ac * fcd
    return ac * fcd * (1.0 - (1.0 - eps / ec2) ** nn)


def _resultante_concreto(x, b, h, d, fck, n=60):
    """Integra o diagrama parabola-retangulo na zona comprimida (regra do ponto
    medio, n faixas): retorna (Rcc [kN], Mcc [kN.m] em relacao ao CG).
    Diagrama 8.2.10.1/17.2.2 por fck (G50)."""
    fcd = fck / GAMMA_C
    dz = h / n
    Rcc = 0.0
    Mcc = 0.0
    for i in range(n):
        z = (i + 0.5) * dz
        s = _sigma_c(_eps_fibra(z, x, d, h, fck), fcd, fck)
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
    eps_c = _eps_fibra(dl, x, d, h, fck)               # aco junto a face comprimida
    eps_t = _eps_fibra(d, x, d, h, fck)                # aco junto a face tracionada
    # desconta o concreto DESLOCADO pelo aco comprimido (tensao real na fibra)
    sig_c = _sigma_s(eps_c, fyd) - _sigma_c(eps_c, fcd, fck)
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
# Flexao composta OBLIQUA (biaxial) - NBR 6118 17.2.5 / 15.8.3.3.5
# ---------------------------------------------------------------------------
ALPHA_BIAXIAL_RECT = 1.2   # expoente da interacao (17.2.5, secao retangular); 1,0 geral


def verifica_biaxial(Nd, Mx, My, hy, hx, dl, fck, fyk, As, alpha=ALPHA_BIAXIAL_RECT):
    """Verificacao de flexao composta OBLIQUA (NBR 6118 17.2.5):
        (Mx/Mrd,xx)^alpha + (My/Mrd,yy)^alpha <= 1
    Mrd,xx e Mrd,yy = momentos resistentes UNIAXIAIS (flexao composta normal) em cada
    eixo, para o MESMO Nd, calculados com a armadura em estudo. Mx = momento na dir x
    (profundidade hx); My = dir y (profundidade hy). Armadura nos 4 CANTOS -> cada
    capacidade uniaxial usa o As TOTAL (As/2 por face perpendicular ao eixo, exatamente
    o solver aferido). Retorna dict com util e ok."""
    Mrd_xx = MRd_para_Nd(Nd, As, hy, hx, dl, fck, fyk)   # dir x: profundidade hx, largura hy
    Mrd_yy = MRd_para_Nd(Nd, As, hx, hy, dl, fck, fyk)   # dir y: profundidade hy, largura hx
    ix = (Mx / Mrd_xx) ** alpha if Mrd_xx > 1e-9 else float("inf")
    iy = (My / Mrd_yy) ** alpha if Mrd_yy > 1e-9 else float("inf")
    util = ix + iy
    return {"Mrd_xx": Mrd_xx, "Mrd_yy": Mrd_yy, "util": util, "alpha": alpha,
            "ok": util <= 1.0 + 1e-6}


def armadura_biaxial(Nd, Mx, My, hy, hx, dl, fck, fyk, As_max, alpha=ALPHA_BIAXIAL_RECT):
    """Menor As total (armadura nos 4 cantos) que satisfaz a interacao obliqua (17.2.5)
    <= 1. util e monotona decrescente em As -> bisseccao. Retorna (As, ok)."""
    def _u(As):
        return verifica_biaxial(Nd, Mx, My, hy, hx, dl, fck, fyk, As, alpha)["util"]
    if _u(0.0) <= 1.0:
        return 0.0, True
    if _u(As_max) > 1.0:
        return As_max, False
    lo, hi = 0.0, As_max
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _u(mid) > 1.0:
            lo = mid
        else:
            hi = mid
    return hi, True


def verifica_cortante_pilar(Vd, bw, d, fck, fyk):
    """Verifica E DIMENSIONA o cortante do fuste (NBR 6118 17.4.2, Modelo I, theta=45°).

    Mesma mecanica de viga_baldrame._verifica_cortante, aplicada a secao do
    pilar: bw = largura ortogonal ao plano do cortante, d = altura util na
    direcao do cortante. Vc sem bonus de compressao axial (conservador:
    flexo-compressao resiste pelo menos o Vc0 da flexao simples).
    Vd ja majorado (ELU, kN).

    G44: alem de verificar a biela e o minimo (G39, fail-closed), DIMENSIONA o
    estribo quando o minimo nao basta: Asw/s_req = max(Vd-Vc,0)/(0,9*d*fywd)
    (Vsw = (Asw/s)*0,9*d*fywd, estribo vertical). Com isso, todo Vd <= VRd2 e
    atendivel por Asw — o gate passa a ser a biela (cort_ok = ok_biela); a
    biela esmagada (Vd > VRd2) continua reprovando (so aumenta a secao).

    Retorna dict com VRd2 (biela), VRd3_min (estribo minimo, legado), VRd3
    (com o Asw adotado), Asw/s req/min/adotado (m2/m), utilizacoes e
    ok_biela/ok_min (legado) + ok (dimensionado = biela)."""

    fck_MPa = fck / 1000.0
    fcd = fck / GAMMA_C
    fywd = fyk / GAMMA_S
    alpha_v2 = 1.0 - fck_MPa / 250.0
    VRd2 = 0.27 * alpha_v2 * fcd * bw * d
    if fck_MPa <= 50.0:
        fctm_MPa = 0.3 * fck_MPa ** (2.0 / 3.0)       # 8.2.5 ate C50
    else:
        fctm_MPa = 2.12 * math.log(1.0 + 0.11 * fck_MPa)  # 8.2.5 C55-C90 (G49)
    fctd_MPa = 0.7 * fctm_MPa / 1.4
    Vc = 0.6 * fctd_MPa * 1000.0 * bw * d
    fywk_MPa = fyk / 1000.0
    rho_sw_min = 0.2 * fctm_MPa / fywk_MPa if fywk_MPa > 0 else 0.0
    asw_min = rho_sw_min * bw
    Vsw_min = asw_min * 0.9 * d * fywd
    VRd3_min = Vc + Vsw_min
    # G44: Asw necessario (Modelo I) e adotado (maximo entre req e minimo)
    denom = 0.9 * d * fywd
    asw_req = max(Vd - Vc, 0.0) / denom if denom > 0 else 0.0
    asw = max(asw_req, asw_min)
    Vsw = asw * 0.9 * d * fywd
    VRd3 = Vc + Vsw
    ok_biela = Vd <= VRd2 + 1e-9
    ok_min = Vd <= VRd3_min + 1e-9
    return {"VRd2": VRd2, "VRd3_min": VRd3_min, "VRd3": VRd3, "Vc": Vc,
            "Vsw_min": Vsw_min, "Vsw": Vsw,
            "rho_sw_min": rho_sw_min, "asw_min": asw_min,
            "asw_req": asw_req, "asw": asw,
            "u_biela": Vd / VRd2 if VRd2 > 0 else float("inf"),
            "u_cort": Vd / VRd3_min if VRd3_min > 0 else float("inf"),
            "u_cort_min": Vd / VRd3_min if VRd3_min > 0 else float("inf"),
            "ok_biela": ok_biela, "ok_min": ok_min, "ok": ok_biela}


# Bitolas de estribo do fuste (mm) e ramos do estribo.
# G47: a lista de bitolas fica CONGELADA em phi <= 10 (a armadilha era
# acrescentar phi 12,5 e empurrar o teto de 2 ramos de 31,4 para 49,1 cm2/m
# sem detalhar nada). O ganho de capacidade vem de RAMOS (2 -> 4 -> 6),
# com a regra do acervo (NBR 6118:2014 lida no PDF local, texto extraivel):
#   - 18.3.3.2, p.149: st,max = d (<=800 mm) se Vd <= 0,20 VRd2, senao
#     st,max = 0,6 d (<=350 mm); s,max longitudinal 0,6d/0,3d (<=300/200 mm);
#   - 18.4.3, p.151-152: o pilar usa estribos + grampos suplementares "quando
#     for o caso", em toda a altura (inclusive cruzamento com vigas/lajes), e
#     havendo cortante compara com os limites de 18.3, valendo o menor;
#   - 18.2.4, p.145-146: o estribo poligonal protege os cantos e as barras a
#     ate 20*phi_t do canto (max. 2 barras nesse trecho, sem contar o canto);
#     acima disso ou com barra fora do trecho, ha estribos suplementares.
# Tentativa de NotebookLM registrada: `nlm login --check` em 2026-09-04
# retornou autenticacao expirada (sem rede/credencial), sem condicao de
# reconsultar; como o PDF tem texto extraivel (256/256 pags, 555 mil chars,
# regra de st em texto, nao em imagem), nao ha caso de "tabela-imagem" que
# exigisse parar - a regra acima e literal do acervo, nao deduzida.
_BITOLAS_ESTRIBO_PILAR = (5.0, 6.3, 8.0, 10.0)
_N_RAMOS_OPCOES = (2, 4, 6)        # fechado simples, +1 grampo, +2 grampos
_COB_ESTRIBO = 0.03                # cobrimento para o st entre ramos (m)
_S_MIN_ESTRIBO = 0.05              # espacamento minimo pratico (montagem)


def st_max_transversal(Vd, VRd2, d):
    """Espacamento transversal maximo entre ramos (NBR 6118:2014, 18.3.3.2):
    Vd <= 0,20 VRd2 -> min(d, 0,80 m); senao -> min(0,6*d, 0,35 m)."""
    if Vd <= 0.20 * VRd2:
        return min(d, 0.80)
    return min(0.6 * d, 0.35)


def st_entre_ramos(n_ramos, bw, cob=_COB_ESTRIBO):
    """Distancia transversal entre ramos sucessivos (m): (bw - 2*cob)/(n-1),
    com bw = largura ortogonal ao cortante e cob = cobrimento."""
    if n_ramos < 2:
        raise ValueError("n_ramos >= 2")
    return max((bw - 2.0 * cob) / (n_ramos - 1), 0.0)


def precisa_suplementar_flambagem(n_barras_no_trecho, barra_fora_do_trecho=False):
    """Regra literal de 18.2.4: ha estribo suplementar quando houver mais de
    2 barras no trecho de 20*phi_t a partir do canto (sem contar a do canto)
    ou barra longitudinal fora desse trecho."""
    return bool(barra_fora_do_trecho or n_barras_no_trecho > 2)


def detalha_estribo_pilar(asw, s_max, bw=None, d=None, Vd=None, VRd2=None,
                          n_barras_trecho=1, phi_min=5.0):
    """Escolhe (phi_mm, s, n_ramos) tal que A_prov = n_ramos*A_phi/s >= asw
    (m2/m), com s <= s_max e s >= 5 cm, E com o espacamento transversal
    entre ramos st = (bw-2*cob)/(n-1) <= st,max (18.3.3.2 via 18.4.3).

    Prefere MENOS ramos e, dentro do ramo, a MENOR bitola com espacamento
    praticavel (>= 5 cm); o espacamento e arredondado PARA BAIXO ao cm
    (a favor da seguranca). n_barras_trecho = barras longitudinais no
    trecho de 20*phi_t a partir do canto (sem contar a do canto, 18.2.4):
    > 2 impoe n_ramos >= 4 (o fuste dimensionado aqui usa 4 cantos ->
    default 1, e o cortante/st governa).
    Retorna (phi_mm, s, Asw_prov_m2m, n_ramos, st_m, st_max_m). asw em
    m2/m ; s/st em m. Sem geometria (bw/d/Vd/VRd2 ausentes) o st nao e
    exigido (compatibilidade) e vale 0,0/inf.

    G44b: a tabela TEM TETO e o chamador compara prov x req e REPROVA
    (fail-closed, nunca satura em silencio). G47 elevou o teto com ramos:
    2R phi10 c/5 = 31,4 ; 4R = 62,8 ; 6R = 94,2 cm2/m (bitolas congeladas
    em phi <= 10). Acima do teto de 6R, devolve o teto e o chamador reprova.
    """
    import math
    s_max = max(min(float(s_max), 0.40), _S_MIN_ESTRIBO)
    if bw is not None and d is not None and Vd is not None and VRd2 is not None:
        st_lim = st_max_transversal(Vd, VRd2, d)
    else:
        st_lim = float("inf")
    n_min = 4 if precisa_suplementar_flambagem(n_barras_trecho) else 2
    for n_ramos in _N_RAMOS_OPCOES:
        if n_ramos < n_min:
            continue
        st = st_entre_ramos(n_ramos, bw) if bw is not None else 0.0
        if bw is not None and st > st_lim + 1e-9:
            continue                               # st estoura: mais ramos
        for phi in _BITOLAS_ESTRIBO_PILAR:
            if phi < phi_min - 1e-9:
                continue                           # 18.4.3: phi_t >= phi_long/4
            a_phi = math.pi * (phi / 1000.0) ** 2 / 4.0
            a_tot = n_ramos * a_phi
            s_req = a_tot / asw if asw > 0 else s_max
            s_lim = min(s_req, s_max)
            s = math.floor(s_lim * 100.0 + 1e-9) / 100.0   # cm cheio, p/ baixo
            if s >= _S_MIN_ESTRIBO - 1e-9:
                return (phi, round(s, 3), round(a_tot / s, 6), n_ramos,
                        round(st, 4), round(st_lim, 4) if st_lim != float("inf") else st_lim)
    # Teto da tabela (6R phi 10 c/5 = 94,2 cm2/m). O chamador confere
    # Asw_prov >= Asw_req e reprova se nao cobrir.
    phi = _BITOLAS_ESTRIBO_PILAR[-1]
    n_ramos = _N_RAMOS_OPCOES[-1]
    a_tot = n_ramos * math.pi * (phi / 1000.0) ** 2 / 4.0
    st = st_entre_ramos(n_ramos, bw) if bw is not None else 0.0
    return (phi, _S_MIN_ESTRIBO, round(a_tot / _S_MIN_ESTRIBO, 6), n_ramos,
            round(st, 4), round(st_lim, 4) if st_lim != float("inf") else st_lim)


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
      'Vd'            : (opcional) cortante de CALCULO no fuste (kN, ELU, >=0).
                        Aceita os apelidos 'Vsd', 'V_d', 'V'. Se ausente, aceita
                        'Vk' (caracteristico, majorado por gamma_n*gamma_f).
                        Ausente tudo -> Vd = 0 (compat.: pilar sem vento declarado).
                        Verificado a cortante pelo Modelo I (17.4.2) via
                        verifica_cortante_pilar; entra no gate OK.
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
    mtot = {}                                     # Md,tot por direcao
    m1real = {}                                   # momento de 1a ordem REAL (pre-minimo)
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
        val = valida_esbeltez(lam, nu)
        res["dir"][dirn] = {
            "esbeltez_valida": val["ok"], "avisos_esbeltez": val["avisos"],
            "exige_metodo_geral": val["exige_metodo_geral"],
            "exige_fluencia": val["exige_fluencia"], "gamma_n1": val["gamma_n1"],
            "le": le, "lambda": round(lam, 1), "lambda1": round(l1, 1),
            "alpha_b": round(ab, 3), "e1_cm": round(e1 * 100, 2),
            "M1d_min": round(M1min, 2), "M1d_A": round(M1dA, 2),
            "considera_2a": lam > l1, "e2_cm": round(e2 * 100, 2),
            "M2d": round(M2, 2), "Md_tot": round(Mtot, 2),
        }
        mtot[dirn] = Mtot
        m1real[dirn] = M1dA
        if Mtot > Md_gov:
            Md_gov = Mtot
            dep_gov, wid_gov = hcol, houtro       # profundidade/largura desta direcao

    # BIAXIAL (flexao composta obliqua, 17.2.5) quando ha momento de 1a ordem REAL nas
    # DUAS direcoes (pilar de canto) ou forcado; senao, uniaxial pela direcao critica
    # (pilar intermediario/extremidade - preserva a pratica de Bastos p/ retangular).
    As_max = 0.08 * Ac
    biaxial = caso.get("forcar_biaxial", False) or (m1real["x"] > 1e-9 and m1real["y"] > 1e-9)
    bx = None
    if biaxial:
        As, ok_res = armadura_biaxial(Nd, mtot["x"], mtot["y"], hy, hx, dl, fck, fyk, As_max)
        modo = "biaxial"
    else:
        As, ok_res = armadura_flexao_composta(Nd, Md_gov, wid_gov, dep_gov, dl,
                                              fck, fyk, As_max=As_max)
        modo = "uniaxial"
    As_min = max(0.15 * Nd / fyd, 0.004 * Ac)
    As_ad = max(As, As_min)
    taxa = As_ad / Ac
    # teto por lance (emenda dobra a armadura -> 4% por lance, 17.3.5.3.2)
    ok_max = As_ad <= 0.04 * Ac + 1e-12
    # faixa de validade do metodo (15.8.1/15.8.3.3.2): REPROVA, nao satura
    esb_ok = all(res["dir"][d]["esbeltez_valida"] for d in res["dir"])
    avisos_esb = [a for d in res["dir"] for a in res["dir"][d]["avisos_esbeltez"]]

    # CORTANTE do fuste (NBR 6118 17.4.2, Modelo I): o vento do galpao chega
    # aqui como Vd de CALCULO (o calice e a sapata ja o recebiam; o fuste nao).
    # Direcao do vento = plano do portico (x): bw = hy, d = hx - dl.
    if caso.get("Vd") is not None:
        Vd = abs(float(caso["Vd"]))
    elif caso.get("Vsd") is not None:
        Vd = abs(float(caso["Vsd"]))
    elif caso.get("V_d") is not None:
        Vd = abs(float(caso["V_d"]))
    elif caso.get("V") is not None:
        Vd = abs(float(caso["V"]))
    elif caso.get("Vk") is not None:
        Vd = abs(float(caso["Vk"])) * gn * gf
    else:
        Vd = 0.0
    bw_cort = hy
    d_cort = max(hx - dl, 0.5 * hx)
    cr = verifica_cortante_pilar(Vd, bw_cort, d_cort, fck, fyk)
    # G44: o estribo e DIMENSIONADO (Asw/s) quando o minimo nao basta; o gate
    # deixa de ser o VRd3,min (G39) e passa a ser a biela MAIS o detalhamento.
    # ok_min/u_cort seguem expostos como diagnostico do minimo (G39).
    if Vd <= 0.67 * cr["VRd2"]:
        s_18_3 = min(0.6 * d_cort, 0.30)
    else:
        s_18_3 = min(0.3 * d_cort, 0.20)
    # G47b: o s LONGITUDINAL de PILAR nao e' o de viga. A 18.4.3 impoe limites
    # PROPRIOS - "o menor dos seguintes valores: 200 mm; menor dimensao da
    # secao; 24 phi para CA-25, 12 phi para CA-50" - e so DEPOIS manda comparar
    # com os de 18.3 "adotando-se o menor dos limites" (p.152, lido no PDF do
    # acervo). O modulo aplicava so o lado de viga desde o G39: varredura de
    # 775 casos achou 87 em que o s ADOTADO passa do teto da 18.4.3 - o pior,
    # 14x50 com s = 270 mm contra 140 mm permitidos, quase o dobro, e num pilar
    # esbelto, onde o espacamento do estribo e' justamente o que impede a
    # flambagem da barra longitudinal. Nao era regressao do G47; era o G47 que
    # leu a 18.4.3 e implementou so a metade que restringe o st.
    #
    # 200 mm e "menor dimensao" saem da geometria. O 12*phi so e' aplicavel se
    # a bitola longitudinal for DECLARADA ('phi_long_mm'): sem ela, nao ha como
    # saber, e arbitrar uma bitola para apertar (ou afrouxar) o limite seria
    # inventar dado. Fica registrado em 's_limite_governante' qual mandou.
    limites_s = {"18.3 (viga)": s_18_3, "18.4.3 200mm": 0.200,
                 "18.4.3 menor dimensao": min(hx, hy)}
    phi_long = caso.get("phi_long_mm")
    if phi_long is not None:
        limites_s["18.4.3 12.phi_long"] = 12.0 * float(phi_long) / 1000.0
    s_estribo_max = min(limites_s.values())
    s_limite_governante = min(limites_s, key=lambda k: limites_s[k])
    # G49/NOTA 18.4.3 C55-C90: "recomenda-se" espacamentos maximos reduzidos em
    # 50% e ganchos a 135 graus. Decisao registrada (D85/G49): APLICAR o 50%
    # (conservador, fail-closed) e EXIGIR o gancho 135 como campo de
    # detalhamento. Nao ignorar em silencio.
    fck_MPa_pilar = fck / 1000.0
    nota_duct_C55_C90 = bool(fck_MPa_pilar > 50.0)
    gancho_135_exigido = bool(nota_duct_C55_C90)
    if nota_duct_C55_C90:
        s_estribo_max = 0.5 * s_estribo_max
        s_limite_governante = "18.4.3 NOTA C55-C90 50% (G49)"
    # 18.4.3: phi_t >= 5 mm e >= phi_long/4 (so verificavel com phi_long dado).
    phi_t_min = max(5.0, float(phi_long) / 4.0) if phi_long is not None else 5.0
    # G47: o detalhamento recebe a geometria do cortante para exigir o st
    # entre ramos (18.3.3.2 via 18.4.3) e abrir 4R/6R com grampo suplementar.
    phi_est, s_est, asw_prov, n_ramos_est, st_est, st_lim = detalha_estribo_pilar(
        cr["asw"], s_estribo_max, bw=bw_cort, d=d_cort, Vd=Vd, VRd2=cr["VRd2"],
        phi_min=phi_t_min)
    # G44b: a tabela de estribo TEM TETO (G47: 6R phi 10 c/5 = 94,2 cm2/m).
    # Sem esta conferencia o modulo devolvia o teto e dizia OK - ex. G44:
    # 40x40 fck30 com Vd = 700 kN pede 40,8 cm2/m, recebia 31,4 (23% a menos)
    # e passava. Comparar prov x req e a diferenca entre dimensionar e saturar.
    asw_atendido = asw_prov >= cr["asw"] - 1e-9
    st_ok = bool(st_est <= st_lim + 1e-9)
    cort_ok = bool(cr["ok"] and asw_atendido and st_ok)

    OK = (ok_res and ok_max and esb_ok and cort_ok
          and min(hx, hy) >= 0.14 - 1e-9 and Ac >= 0.036 - 1e-9)

    # verificacao da interacao obliqua com o As ADOTADO (para o relatorio/gate)
    if biaxial:
        bx = verifica_biaxial(Nd, mtot["x"], mtot["y"], hy, hx, dl, fck, fyk, As_ad)
        res["biaxial"] = {"util": round(bx["util"], 3), "alpha": bx["alpha"],
                          "Mrd_xx": round(bx["Mrd_xx"], 1), "Mrd_yy": round(bx["Mrd_yy"], 1),
                          "Md_x": round(mtot["x"], 1), "Md_y": round(mtot["y"], 1),
                          "ok": bx["ok"]}

    res.update({
        "modo": modo,
        "Md_gov": round(Md_gov, 2), "As_calc_cm2": round(As * 1e4, 2),
        "As_min_cm2": round(As_min * 1e4, 2), "As_cm2": round(As_ad * 1e4, 2),
        "taxa_pct": round(taxa * 100, 2), "As_max_cm2": round(0.04 * Ac * 1e4, 2),
        "resiste": ok_res, "ok_taxa_max": ok_max, "OK": OK,
        "esbeltez_valida": esb_ok, "avisos_esbeltez": avisos_esb,
        "Vd": round(Vd, 2), "VRd2": round(cr["VRd2"], 1),
        "VRd3_min": round(cr["VRd3_min"], 1),
        "VRd3": round(cr["VRd3"], 1),
        "Asw_s_req_cm2_m": round(cr["asw_req"] * 1e4, 2),
        "Asw_s_min_cm2_m": round(cr["asw_min"] * 1e4, 2),
        "Asw_s_cm2_m": round(cr["asw"] * 1e4, 2),
        "u_biela": round(cr["u_biela"], 3), "u_cort": round(cr["u_cort"], 3),
        "u_cort_min": round(cr["u_cort_min"], 3),
        "ok_biela": bool(cr["ok_biela"]), "ok_min": bool(cr["ok_min"]),
        "cort_ok": cort_ok, "s_estribo_max": round(s_estribo_max, 3),
        "phi_estribo_mm": phi_est, "s_estribo": round(s_est, 3),
        "Asw_prov_cm2_m": round(asw_prov * 1e4, 2),
        "Asw_atendido": bool(asw_atendido),
        "n_ramos_estribo": int(n_ramos_est),
        "s_t": round(st_est, 4), "s_t_max": round(st_lim, 4),
        "st_ok": bool(st_ok),
        "s_limite_governante": s_limite_governante,
        "phi_t_min_mm": round(phi_t_min, 2),
        "limites_s_m": {k: round(v, 4) for k, v in limites_s.items()},
        "nota_ductilidade_C55_C90": bool(nota_duct_C55_C90),
        "gancho_135_exigido": bool(gancho_135_exigido),
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
    if r.get("biaxial"):
        b = r["biaxial"]
        L.append(f"  FLEXAO OBLIQUA (17.2.5, alpha={b['alpha']:.1f}): "
                 f"(Mx/Mrd,xx)^a + (My/Mrd,yy)^a = ({b['Md_x']:.1f}/{b['Mrd_xx']:.1f})^a"
                 f" + ({b['Md_y']:.1f}/{b['Mrd_yy']:.1f})^a = {b['util']:.3f} "
                 f"{'<= 1 OK' if b['ok'] else '> 1 REPROVA'} (armadura nos 4 cantos)")
    L += [f"  Direcao critica: Md,tot = {r['Md_gov']:.1f} kN.m ({r.get('modo','uniaxial')})",
          f"  As (flexo-compressao) = {r['As_calc_cm2']:.2f} cm2 ; "
          f"As,min = {r['As_min_cm2']:.2f} cm2 -> As adotado = {r['As_cm2']:.2f} cm2 "
          f"(taxa {r['taxa_pct']:.2f} %) "
          + ("" if r["resiste"] else "; SECAO NAO RESISTE (aumentar) ")
          + ("" if r["ok_taxa_max"] else "; TAXA > 4% por lance (aumentar secao)"),
          f"  CORTANTE (17.4.2, Modelo I): Vd = {r.get('Vd', 0.0):.1f} kN ; "
          f"VRd2 = {r.get('VRd2', 0.0):.1f} (u={r.get('u_biela', 0.0):.3f}) ; "
          f"VRd3,min = {r.get('VRd3_min', 0.0):.1f} (u={r.get('u_cort', 0.0):.3f}) ; "
          f"Asw/s = {r.get('Asw_s_cm2_m', 0.0):.2f} cm2/m "
          f"(min {r.get('Asw_s_min_cm2_m', 0.0):.2f}) -> "
          f"phi {r.get('phi_estribo_mm', 5.0):.1f} c/{r.get('s_estribo', r.get('s_estribo_max', 0.0))*1000:.0f} "
          f"{r.get('n_ramos_estribo', 2)}R (s_max {r.get('s_estribo_max', 0.0)*1000:.0f} mm ; "
          f"s_t {r.get('s_t', 0.0)*1000:.0f} <= {r.get('s_t_max', 0.0)*1000:.0f} mm) -> "
          f"{'OK' if r.get('cort_ok', True) else ('REPROVA (biela)' if not r.get('ok_biela', True) else ('REPROVA (st)' if not r.get('st_ok', True) else 'REPROVA (Asw excede o estribo detalhavel (2/4/6R ate phi 10 c/5): %.2f > %.2f cm2/m)' % (r.get('Asw_s_cm2_m', 0.0), r.get('Asw_prov_cm2_m', 0.0))))}",
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
