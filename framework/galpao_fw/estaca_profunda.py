# ============================================================================
# estaca_profunda.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Fundacao PROFUNDA: capacidade de carga da ESTACA pelo metodo semi-empirico de
# AOKI-VELLOSO (1975) a partir do SPT, e o BLOCO DE COROAMENTO em concreto armado.
#   - capacidade_aoki_velloso: R_ult = R_ponta + R_lateral ; P_adm = R_ult/FS
#     (NBR 6122, FS=2,0 semi-empirico sem prova de carga).
#       R_ponta   = (K*N_p/F1) * A_ponta
#       R_lateral = sum_camadas (alpha*K*N_l/F2) * U * dL
#     K, alpha (Tab.12.6) e F1, F2 (Tab.12.7) LIDOS do PDF (Veloso & Lopes 2012 /
#     Aoki-Velloso 1975), nao de memoria.
#   - n_estacas: numero de estacas = teto(N_pilar / P_adm).
#   - bloco_coroamento: tirante do bloco RIGIDO por bielas-e-tirantes (equilibrio,
#     modelo de Blevot), As = T/f_yd ; concreto reaproveitado de fundacao_sapata.
# O perfil de SPT (tipo de solo + N por camada), o tipo e a geometria da estaca
# sao DADOS DO PROJETO/SONDAGEM (Ask, Do Not Invent). Saidas em portugues.
# Unidades: m, kN ; K em kPa ; fck/fyk em kN/m2.
# ============================================================================
"""Fundacao profunda: capacidade da estaca (Aoki-Velloso, SPT) + bloco de
coroamento (bielas-e-tirantes, NBR 6118). Metodo e tabelas lidos dos PDFs."""

from __future__ import annotations

import math
import fundacao_sapata as fs

# --- Tabela 12.6 (Aoki-Velloso, 1975) - K [kPa] e alpha [%] por tipo de solo ---
# K em kPa = valor em kgf/cm2 x 100 (convencao de Cintra & Aoki 2010). LIDO do PDF.
_K_ALPHA = {
    "areia":               (1000.0, 1.4),
    "areia_siltosa":       (800.0, 2.0),
    "areia_siltoargilosa": (700.0, 2.4),
    "areia_argilossiltosa":(500.0, 2.8),
    "areia_argilosa":      (600.0, 3.0),
    "silte_arenoso":       (550.0, 2.2),
    "silte_arenoargiloso": (450.0, 2.8),
    "silte":               (400.0, 3.0),
    "silte_argiloarenoso": (250.0, 3.0),
    "silte_argiloso":      (230.0, 3.4),
    "argila_arenosa":      (350.0, 2.4),
    "argila_arenossiltosa":(300.0, 2.8),
    "argila_siltoarenosa": (330.0, 3.0),
    "argila_siltosa":      (220.0, 4.0),
    "argila":              (200.0, 6.0),
}

# --- Tabela 12.7 (Aoki-Velloso, 1975) - F1, F2 por tipo de estaca --------------
_F1_F2 = {
    "franki":       (2.5, 5.0),
    "metalica":     (1.75, 3.5),
    "pre_moldada":  (1.75, 3.5),
    "escavada":     (3.0, 6.0),
    "raiz":         (2.0, 4.0),     # raiz/helice/omega (Veloso et al.; final de curso UFRJ)
    "helice":       (2.0, 4.0),
    "omega":        (2.0, 4.0),
}

N_LIMITE = 50.0        # valor limite de N adotado no metodo (Veloso & Lopes p.279)
FS_GLOBAL = 2.0        # NBR 6122: fator de seguranca global (semi-empirico s/ prova de carga)


def capacidade_aoki_velloso(perfil, D, L, tipo_estaca="pre_moldada",
                            N_ponta=None, fs_global=FS_GLOBAL):
    """Capacidade de carga da estaca (Aoki-Velloso 1975).
    perfil: lista de camadas [{tipo, N, dz}] do topo ate a ponta (dz em m; a soma
      das dz ate a profundidade da estaca = L). N = SPT medio da camada.
    D = diametro (m) ; L = comprimento/embutimento (m) ; tipo_estaca = chave de _F1_F2.
    N_ponta = SPT na ponta (default: N da ultima camada). Retorna dict (kN)."""
    if tipo_estaca not in _F1_F2:
        raise ValueError(f"tipo de estaca invalido: {tipo_estaca} ({list(_F1_F2)})")
    F1, F2 = _F1_F2[tipo_estaca]
    A_ponta = math.pi * D ** 2 / 4.0
    U = math.pi * D                                  # perimetro do fuste
    # resistencia de ponta
    Np = N_ponta if N_ponta is not None else perfil[-1]["N"]
    Np = min(Np, N_LIMITE)
    K_p, _ = _solo(perfil[-1]["tipo"])
    R_ponta = (K_p * Np / F1) * A_ponta
    # atrito lateral (soma das camadas ao longo do fuste, ate L)
    R_lat = 0.0; z = 0.0; detalhe = []
    for cam in perfil:
        if z >= L - 1e-9:
            break
        dz = min(cam["dz"], L - z)
        K, alpha = _solo(cam["tipo"])
        N = min(cam["N"], N_LIMITE)
        r_l = (alpha / 100.0) * K * N / F2           # atrito lateral unitario (kPa)
        dR = r_l * U * dz
        R_lat += dR
        detalhe.append({"tipo": cam["tipo"], "N": cam["N"], "dz": round(dz, 2),
                        "rl_kPa": round(r_l, 1), "dR_kN": round(dR, 1)})
        z += dz
    R_ult = R_ponta + R_lat
    P_adm = R_ult / fs_global
    return {"tipo_estaca": tipo_estaca, "D": D, "L": L, "F1": F1, "F2": F2,
            "A_ponta": A_ponta, "U": U, "N_ponta": Np, "K_ponta": K_p,
            "R_ponta_kN": round(R_ponta, 1), "R_lateral_kN": round(R_lat, 1),
            "R_ult_kN": round(R_ult, 1), "FS": fs_global, "P_adm_kN": round(P_adm, 1),
            "camadas": detalhe}


def _solo(tipo):
    if tipo not in _K_ALPHA:
        raise ValueError(f"tipo de solo invalido: {tipo} ({list(_K_ALPHA)})")
    return _K_ALPHA[tipo]


# --- Decourt-Quaresma (1978) - Tab.12.12 C [tf/m2] por grupo de solo ------------
# LIDO do PDF (Veloso & Lopes 2012, pag.281). q_ponta = C*N (tf/m2); em kPa = x10.
_C_DECOURT = {"argila": 12.0, "silte_argiloso": 20.0, "silte_arenoso": 25.0,
              "areia": 40.0}
_TF_KPA = 10.0         # convencao Decourt: 1 tf/m2 ~ 10 kPa


def _grupo_decourt(tipo):
    """Mapeia os 15 solos de Aoki nos 4 grupos de Decourt (Tab.12.12)."""
    if tipo.startswith("areia"):
        return "areia"
    if tipo.startswith("silte"):
        return "silte_arenoso" if "aren" in tipo else "silte_argiloso"
    return "argila"                                  # argila* (e demais finos)


def capacidade_decourt_quaresma(perfil, D, L, N_ponta=None, fs_global=FS_GLOBAL):
    """Capacidade da estaca por Decourt-Quaresma (1978, versao inicial). Usado como
    CROSS-CHECK do Aoki-Velloso. q_ponta = C*N_p ; atrito r_l = N/3+1 (tf/m2, 3<=N<=50,
    independe do solo, Tab.12.13); R_l usa a MEDIA de N ao longo do fuste embutido.
    P_adm = R_ult/FS. Unidades: kN. (A 2a versao 1996 com alpha/beta e FLAG futuro.)"""
    A_ponta = math.pi * D ** 2 / 4.0
    U = math.pi * D
    Np = N_ponta if N_ponta is not None else perfil[-1]["N"]
    Np = max(3.0, min(Np, N_LIMITE))
    C = _C_DECOURT[_grupo_decourt(perfil[-1]["tipo"])]
    q_p = C * Np * _TF_KPA                            # kPa
    R_ponta = q_p * A_ponta
    # media de N ao longo do fuste embutido (ponderada por dz)
    somaNz = 0.0; somaz = 0.0; z = 0.0
    for cam in perfil:
        if z >= L - 1e-9:
            break
        dz = min(cam["dz"], L - z)
        somaNz += cam["N"] * dz; somaz += dz; z += dz
    N_med = somaNz / somaz if somaz > 0 else 0.0
    N_med = max(3.0, min(N_med, N_LIMITE))
    r_l = (N_med / 3.0 + 1.0) * _TF_KPA              # kPa (Tab.12.13 / Eq.12.60)
    R_lat = r_l * U * L
    R_ult = R_ponta + R_lat
    # admissivel de Decourt-Quaresma com FS PARTIDO (Veloso & Lopes pg.288):
    #   FS_lateral = 1,1*1,0*1,0*1,2 = 1,32 ~ 1,3 ; FS_ponta = 1,35*1,0*2,5*1,2 ~ 4,0
    #   Q_adm = R_lateral/1,3 + R_ponta/4,0  (mais racional que o FS global)
    P_adm_partic = R_lat / 1.3 + R_ponta / 4.0
    return {"metodo": "decourt_quaresma", "C": C, "N_ponta": Np, "N_med_fuste": round(N_med, 1),
            "r_l_kPa": round(r_l, 1), "R_ponta_kN": round(R_ponta, 1),
            "R_lateral_kN": round(R_lat, 1), "R_ult_kN": round(R_ult, 1),
            "FS": fs_global, "P_adm_kN": round(R_ult / fs_global, 1),
            "FS_lateral": 1.3, "FS_ponta": 4.0, "P_adm_partic_kN": round(P_adm_partic, 1)}


# --- Teixeira (1996) - Tab.12.16 alpha [tf/m2] por solo x tipo de estaca ---------
# Tipos: I=pre-moldada/perfil metalico ; II=Franki ; III=escavada a ceu aberto ;
# IV=raiz. LIDO do PDF (Veloso & Lopes pg.290, Tab.12.16 / rodape).
_TEIX_ALPHA = {   # (I, II, III, IV) em tf/m2
    "argila_siltosa": (11, 10, 10, 10), "silte_argiloso": (16, 13, 11, 11),
    "argila_arenosa": (21, 18, 13, 14), "silte_arenoso": (26, 21, 16, 16),
    "areia_argilosa": (30, 24, 20, 19), "areia_siltosa": (36, 30, 24, 22),
    "areia": (40, 34, 27, 26), "areia_pedregulho": (44, 38, 31, 29),
}
_TEIX_BETA = {"I": 0.4, "II": 0.5, "III": 0.4, "IV": 0.6}    # tf/m2 (rodape Tab.12.16)
# mapa: tipo de estaca de _F1_F2 -> coluna de Teixeira
_TEIX_TIPO = {"pre_moldada": "I", "metalica": "I", "franki": "II",
              "escavada": "III", "raiz": "IV", "helice": "IV", "omega": "IV"}


def _grupo_teixeira(tipo):
    """Mapeia os 15 solos de Aoki nos 8 grupos de Teixeira (Tab.12.16)."""
    if tipo == "areia":
        return "areia"
    if tipo.startswith("areia"):
        return "areia_siltosa" if "silt" in tipo else "areia_argilosa"
    if tipo.startswith("silte"):
        return "silte_arenoso" if "aren" in tipo else "silte_argiloso"
    if tipo.startswith("argila"):
        return "argila_arenosa" if "aren" in tipo else "argila_siltosa"
    return "argila_siltosa"


def capacidade_teixeira(perfil, D, L, tipo_estaca="pre_moldada", N_ponta=None):
    """Capacidade da estaca por Teixeira (1996) - 3o metodo (cross-check).
      q_ponta = alpha*N_p ; r_lateral = beta*N_med (tf/m2, x10 -> kPa)
      alpha por solo x tipo de estaca (Tab.12.16) ; beta por tipo de estaca.
    FS: tipos I,II,IV -> global 2,0 ; tipo III (escavada) -> ponta 4,0 / lateral 1,3
    (recomendacao de Teixeira, lida do PDF). N em [4;40] p/ a ponta. Retorna dict."""
    col = _TEIX_TIPO.get(tipo_estaca, "I")
    A_ponta = math.pi * D ** 2 / 4.0
    U = math.pi * D
    Np = N_ponta if N_ponta is not None else perfil[-1]["N"]
    Np = max(4.0, min(Np, 40.0))
    idx = {"I": 0, "II": 1, "III": 2, "IV": 3}[col]
    alpha = _TEIX_ALPHA[_grupo_teixeira(perfil[-1]["tipo"])][idx]
    beta = _TEIX_BETA[col]
    R_ponta = alpha * Np * _TF_KPA * A_ponta
    # N medio ao longo do fuste
    somaNz = somaz = z = 0.0
    for cam in perfil:
        if z >= L - 1e-9:
            break
        dz = min(cam["dz"], L - z); somaNz += cam["N"] * dz; somaz += dz; z += dz
    N_med = somaNz / somaz if somaz > 0 else 0.0
    r_l = beta * N_med * _TF_KPA                      # kPa
    R_lat = r_l * U * L
    R_ult = R_ponta + R_lat
    if col == "III":                                 # escavada: FS partido 4,0/1,3
        P_adm = R_lat / 1.3 + R_ponta / 4.0
        fs_txt = "escavada: R_lat/1,3 + R_ponta/4,0"
    else:
        P_adm = R_ult / 2.0
        fs_txt = "global 2,0"
    return {"metodo": "teixeira", "alpha": alpha, "beta": beta, "col_estaca": col,
            "N_ponta": Np, "N_med_fuste": round(N_med, 1), "r_l_kPa": round(r_l, 1),
            "R_ponta_kN": round(R_ponta, 1), "R_lateral_kN": round(R_lat, 1),
            "R_ult_kN": round(R_ult, 1), "P_adm_kN": round(P_adm, 1), "fs": fs_txt}


def capacidade_tracao(cap_compressao, fs_tracao=2.0):
    """Capacidade a TRACAO (arranque/uplift): so o atrito lateral resiste (a ponta
    nao trabalha). NBR 6122. R_lat,trac = R_lateral ; P_adm,trac = R_lat/FS_tracao.
    Recebe o dict de capacidade_aoki_velloso (usa seu R_lateral)."""
    R_lat = cap_compressao["R_lateral_kN"]
    return {"R_lateral_kN": R_lat, "FS_tracao": fs_tracao,
            "P_adm_tracao_kN": round(R_lat / fs_tracao, 1)}


def n_estacas(N_pilar, P_adm, peso_bloco=0.0):
    """Numero de estacas = teto((N_pilar + peso_bloco) / P_adm), minimo 1."""
    N_tot = N_pilar + peso_bloco
    n = max(1, math.ceil(N_tot / P_adm)) if P_adm > 0 else float("inf")
    return {"n": n, "N_por_estaca_kN": round(N_tot / n, 1) if n else None,
            "util": round(N_tot / (n * P_adm), 3) if (n and P_adm > 0) else None}


def eficiencia_grupo(m, n, s, D):
    """Eficiencia do GRUPO de estacas por Converse-Labarre. m x n estacas em malha,
    espacamento s, diametro D. eta = 1 - (theta/90)*[(m-1)*n + (n-1)*m]/(m*n), com
    theta = atan(D/s) em graus. R_grupo = eta * (m*n) * R_estaca_isolada. Grupos com
    s >= 3D tem eta ~1 (pouca interacao); solos arenosos podem ter eta>1 (nao usado,
    a favor da seguranca). Retorna dict."""
    if m < 1 or n < 1:
        raise ValueError("m, n >= 1")
    theta = math.degrees(math.atan(D / s)) if s > 0 else 90.0
    N = m * n
    if N <= 1:
        eta = 1.0
    else:
        eta = 1.0 - (theta / 90.0) * ((m - 1) * n + (n - 1) * m) / (m * n)
    return {"m": m, "n": n, "N_estacas": N, "s": s, "D": D,
            "theta_graus": round(theta, 2), "eficiencia": round(eta, 3)}


def atrito_negativo(D, camadas_neg):
    """Atrito NEGATIVO (downdrag): em solo em adensamento/aterro recente, o solo
    desce em relacao a estaca e o atrito lateral INVERTE de sinal, virando CARGA
    (soma-se a solicitacao, nao resiste). N_neg = U * sum(f_neg * dz).
    camadas_neg: lista [{f_neg [kPa], dz [m]}] das camadas que adensam. f_neg (atrito
    negativo unitario) = beta*sigma_v' (metodo beta) OU medido - e DADO GEOTECNICO.
    Retorna a forca de arrasto (kN, positiva = carga adicional na estaca)."""
    U = math.pi * D
    N_neg = sum(c["f_neg"] * c["dz"] for c in camadas_neg) * U
    return {"N_negativo_kN": round(N_neg, 1), "U": U,
            "camadas": [{"f_neg": c["f_neg"], "dz": c["dz"]} for c in camadas_neg]}


def recalque_grupo(N_grupo, B_grupo, L_grupo, L_estaca, Es, nu=0.30, Iw=0.88,
                   ponta_apoiada=False):
    """Recalque do GRUPO de estacas pelo metodo do RADIER EQUIVALENTE (Terzaghi-Peck
    / Veloso & Lopes): substitui o grupo por uma sapata ficticia na profundidade
      z = 2/3 * L_estaca  (estacas de atrito)  ou  z = L_estaca (ponta apoiada),
    com a carga espalhada 1:4 (talude 1H:4V) ate esse nivel. Recalque elastico da
    sapata equivalente (reusa fundacao_sapata.recalque_elastico).
    N_grupo = carga total (kN) ; B_grupo x L_grupo = dimensoes em planta do grupo (m) ;
    Es = modulo do solo abaixo da ponta (kN/m2, sondagem). Retorna dict (rho em m)."""
    z = (L_estaca if ponta_apoiada else (2.0 / 3.0) * L_estaca)
    # espalhamento 1:4 da carga ate a profundidade z do radier equivalente
    B_eq = B_grupo + 2.0 * (z / 4.0)
    L_eq = L_grupo + 2.0 * (z / 4.0)
    q_liq = N_grupo / (B_eq * L_eq)
    rho = fs.recalque_elastico(q_liq, min(B_eq, L_eq), Es, nu, Iw)
    return {"z_radier_m": round(z, 2), "B_eq_m": round(B_eq, 2), "L_eq_m": round(L_eq, 2),
            "q_liq_kPa": round(q_liq, 1), "recalque_mm": round(rho * 1000.0, 1) if rho else None,
            "Es": Es}


def ancoragem_tirante(phi, fck, fyk, boa_aderencia=True, gancho=False,
                      As_calc=None, As_ef=None):
    """Comprimento de ancoragem do tirante (NBR 6118 9.3.2/9.4.2). phi em m.
      fctm = 0,3*fck^(2/3) (<=C50) ; fctd = 0,7*fctm/1,4 ; fbd = eta1*eta2*eta3*fctd
      eta1=2,25 (nervurada CA-50) ; eta2=1,0 boa / 0,7 ma aderencia ; eta3=1,0 (phi<32mm)
      lb = (phi/4)*(fyd/fbd) ; lb_nec = alpha*lb*(As_calc/As_ef) >= lb_min
      lb_min = max(0,3 lb ; 10 phi ; 100 mm) ; alpha = 0,7 (gancho) / 1,0 (reta).
    fck, fyk em kN/m2. Retorna dict (comprimentos em m)."""
    fck_MPa = fck / 1000.0
    fctm = 0.3 * fck_MPa ** (2.0 / 3.0)              # MPa (<= C50)
    fctd = 0.7 * fctm / 1.4                          # MPa
    phi_mm = phi * 1000.0
    eta1 = 2.25                                      # barra nervurada (CA-50)
    eta2 = 1.0 if boa_aderencia else 0.7
    eta3 = 1.0 if phi_mm < 32.0 else (132.0 - phi_mm) / 100.0
    fbd = eta1 * eta2 * eta3 * fctd                  # MPa
    fyd = (fyk / 1000.0) / 1.15                      # MPa
    lb = (phi / 4.0) * (fyd / fbd)                   # m
    alpha = 0.7 if gancho else 1.0
    rel = (As_calc / As_ef) if (As_calc and As_ef and As_ef > 0) else 1.0
    lb_min = max(0.3 * lb, 10.0 * phi, 0.10)
    lb_nec = max(alpha * lb * rel, lb_min)
    return {"phi_mm": phi_mm, "fctm_MPa": round(fctm, 2), "fbd_MPa": round(fbd, 2),
            "lb_m": round(lb, 3), "lb_min_m": round(lb_min, 3),
            "lb_nec_m": round(lb_nec, 3), "gancho": gancho, "boa_aderencia": boa_aderencia}


def bloco_coroamento(N_pilar, n_est, espacamento, a_pilar, d, fck, fyk, D_estaca=0.30):
    """Bloco RIGIDO de coroamento por BIELAS-E-TIRANTES (modelo de Blevot; NBR 6118
    22.3). Equilibrio: a biela vai do quarto do pilar (no a a_pilar/4 do eixo) ate a
    estaca (a espacamento/2 do eixo); o componente horizontal e o tirante (As=T/f_yd,
    22.3.3). Verifica a BIELA comprimida (22.3.2): tensao junto ao pilar <= fcd1 e
    junto a estaca <= fcd3. So blocos SIMETRICOS 2 ou 4 estacas. d = altura util (m)."""
    if d <= 0:
        raise ValueError("altura util d do bloco deve ser > 0")
    if n_est not in (2, 4):
        raise ValueError("bloco_coroamento: implementado p/ 2 ou 4 estacas")
    fyd = fyk / 1.15
    P_est = N_pilar / n_est                          # carga por estaca (biela)
    braco = espacamento / 2.0 - a_pilar / 4.0        # braco horizontal da biela
    T = P_est * braco / d
    n_tirantes = 1 if n_est == 2 else 2
    As = T / fyd
    As_min = fs.rho_min(fck / 1000.0) * a_pilar * (d + 0.05)   # referencia p/ minimo
    As_req = max(As, As_min)
    arr = fs.detalha_barras(As_req, a_pilar)         # bitola do tirante
    phi_tir = (arr["phi"] / 1000.0) if arr else 0.0125
    anc = ancoragem_tirante(phi_tir, fck, fyk, boa_aderencia=True, gancho=True,
                            As_calc=As_req, As_ef=(arr["As_ef"] if arr else As_req))

    # ---- biela comprimida (NBR 6118 22.3.2) -------------------------------
    tan_theta = d / braco if braco > 0 else float("inf")
    sin2 = tan_theta ** 2 / (1.0 + tan_theta ** 2)   # sen^2(theta)
    fck_MPa = fck / 1000.0
    alpha_v2 = 1.0 - fck_MPa / 250.0
    fcd = fck / 1.4
    fcd1 = 0.85 * alpha_v2 * fcd                      # no CCC (junto ao pilar)
    fcd3 = 0.72 * alpha_v2 * fcd                      # no CCT (junto a estaca, c/ tirante)
    A_pilar = a_pilar ** 2                            # pilar quadrado (contato no topo)
    A_estaca = math.pi * D_estaca ** 2 / 4.0
    sig_pilar = N_pilar / (A_pilar * sin2)           # tensao da biela junto ao pilar
    sig_estaca = P_est / (A_estaca * sin2)           # tensao da biela junto a estaca
    ok_ang = 0.57 <= tan_theta <= 2.0                # 22.3.1 (0,57 <= tan(theta) <= 2)
    ok_biela = sig_pilar <= fcd1 and sig_estaca <= fcd3
    # bloco rigido (tan>=0,57) dispensa puncao (trabalha por bielas); senao verifica
    rigido = tan_theta >= 0.57
    punc = None
    if not rigido:
        # puncao (NBR 6118 19.5) no bloco flexivel, contorno critico C' a 2d, carga
        # TOTAL (sem alivio de solo, conservador). Verifica DOIS contornos: (a) o
        # pilar puncionando p/ baixo ; (b) cada ESTACA puncionando p/ cima (CEB/Blevot).
        d_cm = d * 100.0
        rho_fl = As / (a_pilar * d) if (a_pilar * d) > 0 else 0.0
        tau_rd1 = 0.13 * (1.0 + math.sqrt(20.0 / d_cm)) * (100.0 * rho_fl * fck_MPa) ** (1.0 / 3.0) * 1000.0
        u_pil = 2.0 * (a_pilar + a_pilar) + 2.0 * math.pi * (2.0 * d)   # contorno do pilar
        tau_pil = N_pilar / (u_pil * d)
        u_est = math.pi * D_estaca + 2.0 * math.pi * (2.0 * d)          # contorno da estaca
        tau_est = P_est / (u_est * d)
        ok_pil = tau_pil <= tau_rd1
        ok_est = tau_est <= tau_rd1
        punc = {"tau_rd1_MPa": round(tau_rd1 / 1000.0, 3),
                "tau_pilar_MPa": round(tau_pil / 1000.0, 3), "ok_pilar": ok_pil,
                "tau_estaca_MPa": round(tau_est / 1000.0, 3), "ok_estaca": ok_est,
                "ok_puncao": ok_pil and ok_est}

    return {"n_est": n_est, "P_estaca_kN": round(P_est, 1), "braco_m": round(braco, 3),
            "T_kN": round(T, 1), "As_tirante_cm2": round(As * 1e4, 2),
            "n_tirantes": n_tirantes, "As_min_cm2": round(As_min * 1e4, 2), "d": d,
            "tan_theta": round(tan_theta, 3), "ok_angulo": ok_ang,
            "sig_pilar_MPa": round(sig_pilar / 1000.0, 2), "fcd1_MPa": round(fcd1 / 1000.0, 2),
            "sig_estaca_MPa": round(sig_estaca / 1000.0, 2), "fcd3_MPa": round(fcd3 / 1000.0, 2),
            "ok_biela": ok_biela, "rigido": rigido, "phi_tirante_mm": phi_tir * 1000.0,
            "lb_nec_tirante_m": anc["lb_nec_m"], "ancoragem": anc, "puncao": punc,
            "OK": braco > 0 and ok_biela and ok_ang and (punc is None or punc["ok_puncao"])}


def verifica_estaca(cfg):
    """Orquestra: capacidade -> n estacas -> bloco. cfg com perfil, D, L, tipo,
    N_pilar, e (opcional) bloco {espacamento, a_pilar, h, fck, fyk, cobrimento}."""
    cap = capacidade_aoki_velloso(cfg["perfil"], cfg["D"], cfg["L"],
                                  cfg.get("tipo_estaca", "pre_moldada"),
                                  N_ponta=cfg.get("N_ponta"),
                                  fs_global=cfg.get("FS", FS_GLOBAL))
    dq = capacidade_decourt_quaresma(cfg["perfil"], cfg["D"], cfg["L"],
                                     N_ponta=cfg.get("N_ponta"),
                                     fs_global=cfg.get("FS", FS_GLOBAL))
    tx = capacidade_teixeira(cfg["perfil"], cfg["D"], cfg["L"],
                             cfg.get("tipo_estaca", "pre_moldada"), N_ponta=cfg.get("N_ponta"))
    nn = n_estacas(cfg["N_pilar"], cap["P_adm_kN"], cfg.get("peso_bloco", 0.0))
    out = {"capacidade": cap, "decourt": dq, "teixeira": tx, "grupo": nn,
           "N_pilar": cfg["N_pilar"]}
    # Tracao (uplift): se o pilar arranca (N_uplift > 0), verifica pelo atrito lateral
    N_up = abs(cfg.get("N_uplift", 0.0))
    if N_up > 0:
        trac = capacidade_tracao(cap, cfg.get("FS_tracao", 2.0))
        trac["N_uplift_kN"] = round(N_up, 1)
        trac["N_por_estaca_kN"] = round(N_up / nn["n"], 1)
        trac["util"] = round((N_up / nn["n"]) / trac["P_adm_tracao_kN"], 3) \
            if trac["P_adm_tracao_kN"] > 0 else float("inf")
        trac["OK"] = trac["util"] <= 1.0
        out["tracao"] = trac
    # efeito de grupo (Converse-Labarre) - se a malha for informada
    gr = cfg.get("grupo")
    if gr:
        ge = eficiencia_grupo(gr["m"], gr["n"], gr.get("s", 3.0 * cfg["D"]), cfg["D"])
        ge["R_grupo_kN"] = round(ge["eficiencia"] * ge["N_estacas"] * cap["P_adm_kN"], 1)
        out["grupo_estacas"] = ge
    # atrito negativo (downdrag) - se houver camadas em adensamento
    if cfg.get("camadas_neg"):
        out["atrito_negativo"] = atrito_negativo(cfg["D"], cfg["camadas_neg"])
    # recalque do grupo (radier equivalente) - se Es do solo for informado
    rg = cfg.get("recalque_grupo")
    if rg:
        out["recalque_grupo"] = recalque_grupo(
            cfg["N_pilar"], rg["B_grupo"], rg["L_grupo"], cfg["L"], rg["Es"],
            nu=rg.get("nu", 0.30), Iw=rg.get("Iw", 0.88),
            ponta_apoiada=rg.get("ponta_apoiada", False))
    bl = cfg.get("bloco")
    if bl and nn["n"] in (2, 4):
        h = bl.get("h", max(0.4, 1.2 * cfg["D"]))
        d = h - bl.get("cobrimento", 0.05) - 0.02
        out["bloco"] = bloco_coroamento(
            cfg["N_pilar"], nn["n"], bl.get("espacamento", 3.0 * cfg["D"]),
            bl.get("a_pilar", 0.30), d, bl.get("fck", 25e3), bl.get("fyk", 500e3),
            D_estaca=cfg["D"])
        out["bloco"]["h"] = h
    return out


def relatorio_pt(r):
    c = r["capacidade"]; g = r["grupo"]
    L = ["FUNDACAO PROFUNDA - ESTACA (Aoki-Velloso 1975 / NBR 6122)",
         f"  Estaca {c['tipo_estaca']} D={c['D']*100:.0f} cm L={c['L']:.1f} m "
         f"(F1={c['F1']}, F2={c['F2']})",
         f"  R_ponta   = K*N/F1*A = {c['R_ponta_kN']:.1f} kN "
         f"(K={c['K_ponta']:.0f} kPa, N={c['N_ponta']:.0f})",
         f"  R_lateral = sum(alpha*K*N/F2)*U*dz = {c['R_lateral_kN']:.1f} kN",
         f"  R_ult = {c['R_ult_kN']:.1f} kN ; P_adm = R_ult/{c['FS']:.1f} = {c['P_adm_kN']:.1f} kN",
         f"  Pilar N = {r['N_pilar']:.1f} kN -> n estacas = {g['n']} "
         f"(N/estaca = {g['N_por_estaca_kN']:.1f} kN ; util {g['util']:.2f})"]
    dq = r.get("decourt")
    if dq:
        dif = 100.0 * (dq["R_ult_kN"] - c["R_ult_kN"]) / c["R_ult_kN"] if c["R_ult_kN"] else 0.0
        L.append(f"  [cross-check Decourt-Quaresma] R_ult={dq['R_ult_kN']:.1f} kN "
                 f"(P_adm global={dq['P_adm_kN']:.1f} ; P_adm FS partido "
                 f"R_lat/1,3+R_p/4,0={dq['P_adm_partic_kN']:.1f}) ; C={dq['C']:.0f} tf/m2 "
                 f"; dif R_ult vs Aoki {dif:+.0f}%")
    tx = r.get("teixeira")
    if tx:
        dift = 100.0 * (tx["R_ult_kN"] - c["R_ult_kN"]) / c["R_ult_kN"] if c["R_ult_kN"] else 0.0
        L.append(f"  [cross-check Teixeira 1996] R_ult={tx['R_ult_kN']:.1f} kN "
                 f"(P_adm={tx['P_adm_kN']:.1f}, FS {tx['fs']}) ; alpha={tx['alpha']} beta={tx['beta']} "
                 f"tf/m2 (estaca tipo {tx['col_estaca']}) ; dif R_ult vs Aoki {dift:+.0f}%")
    if "tracao" in r:
        t = r["tracao"]
        L.append(f"  TRACAO (uplift): N_up={t['N_uplift_kN']:.1f} kN "
                 f"({t['N_por_estaca_kN']:.1f}/estaca) ; P_adm,trac=R_lat/{t['FS_tracao']:.1f}="
                 f"{t['P_adm_tracao_kN']:.1f} kN ; util {t['util']:.2f} "
                 f"{'OK' if t['OK'] else 'REPROVA (aumentar L/atrito)'}")
    if "bloco" in r:
        b = r["bloco"]
        L += [f"  BLOCO DE COROAMENTO ({b['n_est']} estacas, bielas-e-tirantes):",
              f"    h={b['h']*100:.0f} cm (d={b['d']*100:.0f} cm) ; carga/estaca={b['P_estaca_kN']:.1f} kN ; "
              f"braco={b['braco_m']:.3f} m ; tan(theta)={b['tan_theta']:.2f} "
              f"{'OK' if b['ok_angulo'] else 'FORA de [0,57;2]'}",
              f"    Tirante T = {b['T_kN']:.1f} kN -> As = {b['As_tirante_cm2']:.2f} cm2 "
              f"(x{b['n_tirantes']} direcao(oes)) ; As_min ref {b['As_min_cm2']:.2f} cm2",
              f"    Biela (22.3.2): pilar {b['sig_pilar_MPa']:.2f}<={b['fcd1_MPa']:.2f} MPa ; "
              f"estaca {b['sig_estaca_MPa']:.2f}<={b['fcd3_MPa']:.2f} MPa "
              f"{'OK' if b['ok_biela'] else 'REPROVA (aumentar bloco/fck)'}",
              f"    Bloco {'RIGIDO -> puncao dispensada (trabalha por bielas)' if b['rigido'] else 'FLEXIVEL'}"
              + ("" if b["rigido"] or not b.get("puncao") else
                 f" -> puncao C' 2d (tau_rd1={b['puncao']['tau_rd1_MPa']:.3f} MPa): "
                 f"pilar {b['puncao']['tau_pilar_MPa']:.3f} {'OK' if b['puncao']['ok_pilar'] else 'REPROVA'} ; "
                 f"estaca {b['puncao']['tau_estaca_MPa']:.3f} {'OK' if b['puncao']['ok_estaca'] else 'REPROVA'}"),
              f"    Ancoragem do tirante (9.4.2): phi={b['phi_tirante_mm']:.1f} mm -> "
              f"lb,nec={b['lb_nec_tirante_m']*100:.0f} cm (com gancho)"]
    if "grupo_estacas" in r:
        ge = r["grupo_estacas"]
        L.append(f"  EFEITO DE GRUPO (Converse-Labarre {ge['m']}x{ge['n']}): "
                 f"eta={ge['eficiencia']:.3f} -> R_grupo={ge['R_grupo_kN']:.1f} kN")
    if "atrito_negativo" in r:
        an = r["atrito_negativo"]
        L.append(f"  ATRITO NEGATIVO (downdrag): N_neg={an['N_negativo_kN']:.1f} kN "
                 f"(carga adicional na estaca)")
    if "recalque_grupo" in r:
        rg = r["recalque_grupo"]
        L.append(f"  RECALQUE DO GRUPO (radier equivalente z={rg['z_radier_m']:.1f} m, "
                 f"{rg['B_eq_m']:.1f}x{rg['L_eq_m']:.1f} m): "
                 f"{rg['recalque_mm']:.1f} mm (q={rg['q_liq_kPa']:.0f} kPa)")
    L += ["  [A CONFIRMAR: perfil de SPT (tipo de solo + N por camada) da SONDAGEM;",
          "   tipo/geometria da estaca; FS da NBR 6122 (2,0 semi-empirico s/ prova);",
          "   puncao do bloco flexivel = projeto do bloco.]",
          "  [3 metodos de capacidade (Aoki-Velloso, Decourt-Quaresma, Teixeira) +",
          "   tracao, grupo, atrito negativo, recalque, bloco (biela+ancoragem+puncao).]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # perfil: 3 m argila (N=5), 4 m areia siltosa (N=15), ponta em areia (N=25)
    perfil = [{"tipo": "argila", "N": 5, "dz": 3.0},
              {"tipo": "areia_siltosa", "N": 15, "dz": 4.0},
              {"tipo": "areia", "N": 25, "dz": 3.0}]
    D, L = 0.30, 10.0
    cap = capacidade_aoki_velloso(perfil, D, L, "pre_moldada")
    # R_ponta = K*N/F1*A = 1000*25/1,75 * (pi*0,3^2/4)
    Ap = math.pi * 0.3 ** 2 / 4.0
    assert abs(cap["R_ponta_kN"] - 1000.0 * 25 / 1.75 * Ap) < 0.2, cap
    # atrito camada argila: (6/100)*200*5/3,5 * (pi*0,3) * 3
    U = math.pi * 0.3
    rl_arg = (6.0 / 100.0) * 200.0 * 5 / 3.5
    dR_arg = rl_arg * U * 3.0
    assert abs(cap["camadas"][0]["dR_kN"] - round(dR_arg, 1)) < 0.2, cap["camadas"][0]
    assert abs(cap["P_adm_kN"] - cap["R_ult_kN"] / 2.0) < 0.1, cap
    # N limite 50: ponta N=80 -> usa 50
    cap2 = capacidade_aoki_velloso(perfil, D, L, "pre_moldada", N_ponta=80)
    assert abs(cap2["N_ponta"] - 50.0) < 1e-9, cap2
    # grupo: pilar 900 kN
    g = n_estacas(900.0, cap["P_adm_kN"])
    assert g["n"] == math.ceil(900.0 / cap["P_adm_kN"]) and g["util"] <= 1.0 + 1e-9, g
    # bloco 2 estacas
    b = bloco_coroamento(900.0, 2, 0.9, 0.30, 0.55, 25e3, 500e3, D_estaca=0.30)
    # T = (900/2) * (0,9/2 - 0,30/4) / 0,55
    brc = 0.9 / 2.0 - 0.30 / 4.0
    assert abs(b["T_kN"] - 450.0 * brc / 0.55) < 0.2, b
    assert abs(b["As_tirante_cm2"] - (450.0 * brc / 0.55) / (500e3 / 1.15) * 1e4) < 0.1, b
    # biela (22.3.2): fcd1=0,85*(1-25/250)*25/1,4 ; fcd3=0,72*...
    fcd = 25e3 / 1.4; av2 = 1.0 - 25.0 / 250.0
    assert abs(b["fcd1_MPa"] - 0.85 * av2 * fcd / 1000.0) < 0.01, b
    assert abs(b["fcd3_MPa"] - 0.72 * av2 * fcd / 1000.0) < 0.01, b
    tan = 0.55 / brc; sin2 = tan ** 2 / (1 + tan ** 2)
    assert abs(b["sig_estaca_MPa"] - (450.0 / (math.pi * 0.3 ** 2 / 4.0 * sin2)) / 1000.0) < 0.02, b
    assert b["ok_angulo"] == (0.57 <= tan <= 2.0) and "ok_biela" in b
    # ancoragem do tirante (9.3.2): fctm=0,3*25^(2/3) ; fbd=2,25*1*1*0,7*fctm/1,4
    anc = ancoragem_tirante(0.0125, 25e3, 500e3, boa_aderencia=True, gancho=False)
    fctm = 0.3 * 25.0 ** (2.0 / 3.0); fbd = 2.25 * 0.7 * fctm / 1.4
    lb = (0.0125 / 4.0) * ((500.0 / 1.15) / fbd)
    assert abs(anc["lb_m"] - round(lb, 3)) < 1e-3, anc
    # efeito de grupo Converse-Labarre 2x2, s=3D
    ge = eficiencia_grupo(2, 2, 0.9, 0.30)
    th = math.degrees(math.atan(0.30 / 0.9))
    eta = 1.0 - (th / 90.0) * ((2 - 1) * 2 + (2 - 1) * 2) / 4.0
    assert abs(ge["eficiencia"] - round(eta, 3)) < 1e-3, ge
    # atrito negativo: U*sum(f*dz)
    an = atrito_negativo(0.30, [{"f_neg": 20.0, "dz": 3.0}, {"f_neg": 30.0, "dz": 2.0}])
    assert abs(an["N_negativo_kN"] - (20 * 3 + 30 * 2) * math.pi * 0.30) < 0.1, an
    # recalque de grupo (radier equivalente): z=2/3 L ; espalhamento 1:4
    rg = recalque_grupo(2000.0, 2.0, 2.0, 12.0, Es=20000.0)
    z = 2.0 / 3.0 * 12.0
    Beq = 2.0 + 2.0 * (z / 4.0)
    assert abs(rg["B_eq_m"] - Beq) < 1e-9 and rg["recalque_mm"] > 0, rg
    # bloco flexivel -> puncao verificada (tan<0,57): d pequeno, braco grande
    bf = bloco_coroamento(500.0, 2, 1.5, 0.30, 0.20, 25e3, 500e3, D_estaca=0.30)
    assert not bf["rigido"] and bf["puncao"] is not None
    assert "ok_pilar" in bf["puncao"] and "ok_estaca" in bf["puncao"]
    # Decourt-Quaresma: ponta areia C=40 tf/m2, q_p=40*25*10=10000 kPa
    dq = capacidade_decourt_quaresma(perfil, D, L)
    assert dq["C"] == 40.0, dq
    assert abs(dq["R_ponta_kN"] - 40.0 * 25 * 10.0 * Ap) < 0.2, dq
    # r_l = (N_med/3+1)*10 ; N_med = (5*3+15*4+25*3)/10 = 15,0
    Nmed = (5 * 3 + 15 * 4 + 25 * 3) / 10.0
    assert abs(dq["N_med_fuste"] - Nmed) < 1e-6, dq
    rl = (Nmed / 3.0 + 1.0) * 10.0
    assert abs(dq["R_lateral_kN"] - rl * U * L) < 0.2, dq
    # FS partido (Veloso & Lopes pg.288): R_lat/1,3 + R_ponta/4,0
    assert abs(dq["P_adm_partic_kN"] - (dq["R_lateral_kN"] / 1.3 + dq["R_ponta_kN"] / 4.0)) < 0.1, dq
    # Teixeira 1996: ponta areia col I alpha=40 ; q_p=40*25*10 ; beta I=0,4
    tx = capacidade_teixeira(perfil, D, L, "pre_moldada")
    assert tx["alpha"] == 40 and tx["beta"] == 0.4 and tx["col_estaca"] == "I", tx
    assert abs(tx["R_ponta_kN"] - 40 * 25 * 10.0 * Ap) < 0.2, tx
    Nmed_t = (5 * 3 + 15 * 4 + 25 * 3) / 10.0
    assert abs(tx["R_lateral_kN"] - 0.4 * Nmed_t * 10.0 * U * L) < 0.2, tx
    # escavada -> FS partido 4,0/1,3
    txe = capacidade_teixeira(perfil, D, L, "escavada")
    assert txe["col_estaca"] == "III"
    assert abs(txe["P_adm_kN"] - (txe["R_lateral_kN"] / 1.3 + txe["R_ponta_kN"] / 4.0)) < 0.1, txe
    # grupo decourt: silte arenoso -> silte_arenoso (25) ; argila -> argila (12)
    assert _grupo_decourt("areia_siltosa") == "areia"        # comeca com areia
    assert _grupo_decourt("silte_arenoso") == "silte_arenoso"
    assert _grupo_decourt("silte_argiloso") == "silte_argiloso"
    assert _grupo_decourt("argila_arenosa") == "argila"
    # tracao: so atrito lateral / FS
    tr = capacidade_tracao(cap, 2.0)
    assert abs(tr["P_adm_tracao_kN"] - cap["R_lateral_kN"] / 2.0) < 0.1, tr
    # verifica_estaca integra (com uplift)
    r = verifica_estaca({"perfil": perfil, "D": D, "L": L, "tipo_estaca": "pre_moldada",
                         "N_pilar": 600.0, "N_uplift": 200.0,
                         "bloco": {"espacamento": 0.9, "a_pilar": 0.30, "h": 0.55}})
    assert r["grupo"]["n"] >= 1 and "capacidade" in r and "decourt" in r and "tracao" in r
    assert r["tracao"]["OK"] in (True, False)
    print("estaca_profunda self-test PASSED")
    print(f"  D30 L10 pre-moldada: R_ult={cap['R_ult_kN']:.0f} kN, "
          f"P_adm={cap['P_adm_kN']:.0f} kN")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        perfil = [{"tipo": "argila", "N": 5, "dz": 3.0},
                  {"tipo": "areia_siltosa", "N": 15, "dz": 4.0},
                  {"tipo": "areia", "N": 25, "dz": 3.0}]
        print(relatorio_pt(verifica_estaca({
            "perfil": perfil, "D": 0.30, "L": 10.0, "tipo_estaca": "pre_moldada",
            "N_pilar": 1500.0, "N_uplift": 300.0,
            "grupo": {"m": 2, "n": 1, "s": 0.9},
            "camadas_neg": [{"f_neg": 15.0, "dz": 3.0}],
            "recalque_grupo": {"B_grupo": 1.2, "L_grupo": 0.6, "Es": 20000.0},
            "bloco": {"espacamento": 0.9, "a_pilar": 0.30, "h": 0.55}})))
