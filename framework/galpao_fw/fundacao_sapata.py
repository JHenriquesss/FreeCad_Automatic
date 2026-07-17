# ============================================================================
# fundacao_sapata.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Dimensiona/verifica a SAPATA ISOLADA sob a reacao de base do pilar (N, V, M).
# Dividido em duas partes, por rigor de metodo:
#
#   PARTE A - GEOTECNIA / ESTABILIDADE (estatica pura - defensavel sem norma
#   de concreto). Verifica:
#     - tensao no solo sob N+M (flexao composta): nucleo (e<=L/6, trapezio) ou
#       borda (e>L/6, diagrama triangular, comprimento de contato 3*(L/2-e));
#       criterio sigma_max <= sigma_solo,adm (INPUT do engenheiro/sondagem - NAO
#       inventado aqui);
#     - FS ao TOMBAMENTO   = M_estabilizante / M_tombante  >= FS_tomb;
#     - FS ao DESLIZAMENTO = (N*mu + c*A) / V              >= FS_desl.
#     Inclui peso proprio da sapata + reaterro no N estabilizante.
#     Pre-dimensiona a planta B x L pela escada ate passar.
#
#   PARTE B - CONCRETO ARMADO (NBR 6118:2014): rigidez (22.6.1), armadura de
#   flexao nas 2 direcoes (22.6.3 modelo de flexao + 17.2.2 bloco retangular) e
#   compressao diagonal no perimetro do pilar (19.5.3.1). Sapata RIGIDA nao tem
#   puncao (22.6.2.2). METODO EXTRAIDO DA NBR 6118 (pesquisa/aco/nbr-6118-2014
#   ...pdf) - nao de memoria. Detalhamento/ancoragem = executivo (FLAG).
#
# Ask, Do Not Invent: sigma_solo,adm, mu, coesao, fck, fyk, cobrimento e os
# fatores de seguranca sao INPUTS do caso (a skill pergunta). Saidas em PT.
# Calcula apenas; CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# Unidades SI: m, kN (fck/fyk/sigma em kN/m2).
# ============================================================================
"""Sapata isolada: Parte A (geotecnia/estabilidade) + Parte B (concreto NBR 6118)."""

from __future__ import annotations

import math
import re

# Fatores de seguranca USUAIS (o caso pode sobrescrever). Convencao de projeto -
# o engenheiro confirma. FLAG no relatorio.
FS_TOMB_MIN = 1.5          # tombamento (pratica usual p/ ELU geotecnico)
FS_DESL_MIN = 1.5          # deslizamento
GAMMA_C_CONCRETO = 25.0    # peso especifico concreto armado (kN/m3) - NBR 6120
GAMMA_SOLO = 18.0          # reaterro (kN/m3) - INPUT (sondagem); default flag


# ---- PARTE A: GEOTECNIA / ESTABILIDADE -------------------------------------
def tensoes_solo(N, M, B, L):
    """Tensao no solo sob carga axial N (>0 compressao) + momento M, flexao em
    torno do eixo de comprimento L. Retorna (sigma_max, sigma_min, regime,
    comprimento_contato). N ja deve incluir peso proprio da sapata + reaterro.
    Convencao: momento no plano do portico (dimensao L)."""
    A = B * L
    if N <= 0:
        return None, None, "sem compressao (N<=0)", 0.0
    e = abs(M) / N
    if e <= L / 6.0 + 1e-12:                       # dentro do nucleo: contato total
        sig_max = N / A * (1.0 + 6.0 * e / L)
        sig_min = N / A * (1.0 - 6.0 * e / L)
        return sig_max, sig_min, "nucleo (contato total)", L
    # fora do nucleo: parte da sapata levanta, diagrama triangular.
    # comprimento de contato x = 3*(L/2 - e); sigma_max = 2N/(B*x).
    x = 3.0 * (L / 2.0 - e)
    if x <= 0:
        return None, 0.0, "instavel (resultante fora da base)", 0.0
    sig_max = 2.0 * N / (B * x)
    return sig_max, 0.0, "borda (levantamento parcial)", x


def peso_proprio(B, L, h, h_reaterro=0.0, d_ped=0.0, b_ped=0.0, h_ped=0.0):
    """Peso da sapata (bloco B x L x h) + pedestal + reaterro sobre as abas.
    Retorna (peso_total_kN, detalhe). h_reaterro = altura de solo sobre a sapata.
    d_ped/b_ped/h_ped = pedestal (m); reaterro sobre area (B*L - area_pedestal)."""
    p_sapata = B * L * h * GAMMA_C_CONCRETO
    a_ped = (d_ped * b_ped) if (d_ped and b_ped) else 0.0
    p_ped = a_ped * h_ped * GAMMA_C_CONCRETO
    p_solo = max(B * L - a_ped, 0.0) * h_reaterro * GAMMA_SOLO
    return p_sapata + p_ped + p_solo, {"sapata": p_sapata, "pedestal": p_ped,
                                       "reaterro": p_solo}


def estabilidade(N, V, M, B, L, h, mu, coesao=0.0, h_reaterro=0.0,
                 d_ped=0.0, b_ped=0.0, h_ped=0.0):
    """FS ao tombamento e ao deslizamento, com N estabilizante = reacao +
    peso proprio. M_tombante = V*h_total + M (momento na base da sapata)."""
    Pp, det = peso_proprio(B, L, h, h_reaterro, d_ped, b_ped, h_ped)
    N_tot = N + Pp
    h_tot = h + h_ped                              # altura ate o topo do pedestal
    M_tomb = abs(V) * h_tot + abs(M)
    M_est = N_tot * L / 2.0
    fs_tomb = (M_est / M_tomb) if M_tomb > 0 else float("inf")
    # atrito ~ N_tot (independe da area); ADESAO (coesao) atua so sob a area de
    # contato efetiva: sob levantamento (e>L/6) so B*x toca o solo, nao B*L.
    e = abs(M) / N_tot if N_tot > 0 else 0.0
    x_cont = L if e <= L / 6.0 else max(3.0 * (L / 2.0 - e), 0.0)
    A_ef = B * min(x_cont, L)                       # = B*L com contato total
    resist = N_tot * mu + coesao * A_ef
    fs_desl = (resist / abs(V)) if abs(V) > 0 else float("inf")
    return {"N_tot": N_tot, "Pp": Pp, "Pp_det": det, "M_tomb": M_tomb, "A_ef": A_ef,
            "M_est": M_est, "fs_tomb": fs_tomb, "fs_desl": fs_desl, "h_tot": h_tot}


# Fator de forma Iw (Perloff 1975, meio de espessura infinita; via Veloso & Lopes
# Tab. 5.1) - RIGIDO. Lido do PDF (nao de memoria): circulo 0,79 ; quadrado 0,88.
# Retangulo cresce com L/B - o valor exato sai da Tab. 5.1 pela relacao L/B (o
# engenheiro confirma / passa Iw). Default = 0,88 (quadrado rigido).
_IW_RIGIDO = {1.0: 0.88}                             # circulo -> usar 0,79 (caso.Iw)


def recalque_elastico(q_liq, B, Es, nu=0.30, Iw=0.88):
    """Recalque IMEDIATO/elastico de sapata pela Teoria da Elasticidade
    (Veloso & Lopes; NBR 6122 remete a metodos geotecnicos):

        rho = q_liq * B * (1 - nu^2) * Iw / Es

    q_liq = pressao LIQUIDA de servico (kN/m2) ; B = menor dimensao (m) ; Es =
    modulo de deformabilidade do solo (kN/m2, INPUT sondagem) ; nu = coef. de
    Poisson do solo ; Iw = fator de forma/rigidez (Tab. 5.1 Perloff). Retorna rho
    em metros. Es e nu sao dados geotecnicos - Ask, Do Not Invent."""
    if Es <= 0:
        return None
    return q_liq * B * (1.0 - nu ** 2) * Iw / Es


def verifica_sapata_A(caso):
    """PARTE A completa: tensao no solo + estabilidade. Retorna dict de resultados."""
    N, V, M = caso["N"], caso["V"], caso["M"]
    B, L, h = caso["B"], caso["L"], caso["h"]
    mu = caso.get("mu", 0.5)
    coesao = caso.get("coesao", 0.0)
    est = estabilidade(N, V, M, B, L, h, mu, coesao,
                       caso.get("h_reaterro", 0.0),
                       caso.get("d_ped", 0.0), caso.get("b_ped", 0.0),
                       caso.get("h_ped", 0.0))
    sig_max, sig_min, regime, xcont = tensoes_solo(est["N_tot"], M, B, L)
    sig_adm = caso["sigma_solo_adm"]
    r = {"nome": caso.get("nome", "sapata"), "B": B, "L": L, "h": h,
         "sigma_max": sig_max, "sigma_min": sig_min, "regime": regime,
         "x_contato": xcont, "sigma_adm": sig_adm, **est}
    r["u_solo"] = (sig_max / sig_adm) if (sig_max and sig_adm) else float("inf")
    r["fs_tomb_min"] = caso.get("fs_tomb_min", FS_TOMB_MIN)
    r["fs_desl_min"] = caso.get("fs_desl_min", FS_DESL_MIN)
    r["ok_solo"] = (sig_max is not None and sig_max <= sig_adm + 1e-9)
    r["ok_tomb"] = est["fs_tomb"] >= r["fs_tomb_min"]
    r["ok_desl"] = est["fs_desl"] >= r["fs_desl_min"]
    # levantamento: em sapata isolada de galpao aceita-se contato parcial, mas a
    # resultante deve cair no terco medio para nao ter borda descolando demais.
    r["ok_contato"] = xcont >= L / 3.0

    # RECALQUE (ELS geotecnico, NBR 6122 - teoria da elasticidade). So calcula se
    # Es_solo (deformabilidade, sondagem) for dado. Pressao LIQUIDA de SERVICO:
    # usa N_serv se dado, senao N (o envelope passa ELU -> conservador; o eng.
    # informa a combinacao de servico). Informativo; gateia OK_A so se exceder.
    Es = caso.get("Es_solo")
    if Es:
        N_serv = caso.get("N_serv", N)
        q_liq = max(N_serv / (B * L) - caso.get("q_sobrecarga", 0.0), 0.0)
        Bmin = min(B, L)                             # menor dimensao (recalque)
        rho = recalque_elastico(q_liq, Bmin, Es, caso.get("nu_solo", 0.30),
                                caso.get("Iw", 0.88))
        r["recalque_mm"] = rho * 1000.0
        r["recalque_adm_mm"] = caso.get("recalque_adm_mm", 25.0)
        r["ok_recalque"] = r["recalque_mm"] <= r["recalque_adm_mm"] + 1e-9
    else:
        r["recalque_mm"] = None
        r["recalque_adm_mm"] = caso.get("recalque_adm_mm", 25.0)
        r["ok_recalque"] = None                      # sem Es: nao verifica (FLAG)

    r["OK_A"] = (r["ok_solo"] and r["ok_tomb"] and r["ok_desl"] and r["ok_contato"]
                 and (r["ok_recalque"] is not False))
    return r


# Escada de sapatas (B, L, h) em m - da menor para a maior. Quadrada/retangular
# conforme o momento. h cresce junto (rigidez + altura util p/ Parte B).
ESCADA_SAPATA = [
    (1.20, 1.20, 0.35),
    (1.50, 1.50, 0.40),
    (1.50, 2.00, 0.45),
    (2.00, 2.00, 0.50),
    (2.00, 2.50, 0.55),
    (2.50, 2.50, 0.60),
    (2.50, 3.00, 0.65),
    (3.00, 3.00, 0.70),
]


def dimensiona_sapata(caso, escada=None):
    """Escolhe a sapata MAIS LEVE (menor area) que passa Parte A (solo +
    estabilidade) sob a reacao real. Retorna {aprovado:(B,L,h,r,caso)|None,
    linhas, tabela}. A Parte B (concreto) roda depois, sobre a adotada."""
    escada = escada or ESCADA_SAPATA
    linhas, aprovado = [], None
    for (B, L, h) in escada:
        c = dict(caso); c.update(B=B, L=L, h=h)
        r = verifica_sapata_A(c)
        linhas.append(r)
        if r["OK_A"] and aprovado is None:
            aprovado = (B, L, h, r, c)
    rB = None
    if aprovado:                                   # Parte B sobre a adotada
        B, L, h, rA, cA = aprovado
        # RIGIDEZ (22.6.1): sobe h ate rigida (aumentar h so ajuda a Parte A).
        ap_L = caso.get("d_ped") or caso.get("ap_L") or 0.30
        ap_B = caso.get("b_ped") or caso.get("ap_B") or 0.30
        h_rig = max(L - ap_L, B - ap_B) / 3.0
        if h < h_rig:
            h = math.ceil(h_rig / 0.05) * 0.05     # arredonda p/ 5 cm
            cA = dict(cA); cA.update(h=h)
            rA = verifica_sapata_A(cA)
            aprovado = (B, L, h, rA, cA)
        rB = dimensiona_sapata_B(caso, rA)
    return {"aprovado": aprovado, "parte_B": rB, "linhas": linhas,
            "tabela": _tabela_sapata(linhas, aprovado, caso, rB)}


def dimensiona_sapata_env(caso_base, casos, escada=None):
    """Dimensiona a sapata pelo ENVELOPE de combinacoes: adota a MENOR geometria
    que passa (Parte A + Parte B) em TODAS as combinacoes. Fecha o gap de usar so
    a combinacao que governa a placa de base - aqui o bearing pega o N MAXIMO
    gravitacional, o tombamento pega o N minimo com M maximo, etc.

    caso_base: dict com os parametros do solo/concreto (sigma_solo_adm, mu, fck,
               fyk, pedestal...); N,V,M sao ignorados (vem de 'casos').
    casos:     lista de (nome, N, V, M) - uma por combinacao ELU.
    Retorna {aprovado:(B,L,h,rA,c)|None, parte_B, linhas, tabela, governantes}."""
    escada = escada or ESCADA_SAPATA
    ap_L = caso_base.get("d_ped") or caso_base.get("ap_L") or 0.30
    ap_B = caso_base.get("b_ped") or caso_base.get("ap_B") or 0.30
    linhas, aprovado, rB_ad, gov = [], None, None, {}
    for (B, L, h0) in escada:
        h = max(h0, math.ceil(max(L - ap_L, B - ap_B) / 3.0 / 0.05) * 0.05)  # rigida
        piorA, todosA = None, True
        # pior u_solo / menor FS entre as combinacoes (Parte A)
        u_solo = fs_tomb = fs_desl = None
        for (nm, N, V, M) in casos:
            c = dict(caso_base); c.update(N=N, V=V, M=M, B=B, L=L, h=h)
            rA = verifica_sapata_A(c)
            todosA = todosA and rA["OK_A"]
            if u_solo is None or rA["u_solo"] > u_solo:
                u_solo = rA["u_solo"]; gov["solo"] = (nm, rA["u_solo"])
                piorA = (rA, c)
            if fs_tomb is None or rA["fs_tomb"] < fs_tomb:
                fs_tomb = rA["fs_tomb"]; gov["tomb"] = (nm, rA["fs_tomb"])
            if fs_desl is None or rA["fs_desl"] < fs_desl:
                fs_desl = rA["fs_desl"]; gov["desl"] = (nm, rA["fs_desl"])
        # Parte B: pior utilizacao e MAIOR As entre as combinacoes
        rB_pior, As_L, As_B, okB = None, 0.0, 0.0, True
        u_cd = None
        for (nm, N, V, M) in casos:
            c = dict(caso_base); c.update(N=N, V=V, M=M)
            rB = dimensiona_sapata_B(c, {"B": B, "L": L, "h": h})
            okB = okB and rB["OK_B"]
            As_L = max(As_L, rB["flexao_L"]["As_adot"])
            As_B = max(As_B, rB["flexao_B"]["As_adot"])
            if u_cd is None or rB["compr_diag"]["u_cd"] > u_cd:
                u_cd = rB["compr_diag"]["u_cd"]; gov["compr"] = (nm, u_cd); rB_pior = rB
        linha = {"B": B, "L": L, "h": h, "u_solo": u_solo, "fs_tomb": fs_tomb,
                 "fs_desl": fs_desl, "u_cd": u_cd, "As_L": As_L, "As_B": As_B,
                 "okA": todosA, "okB": okB, "OK": todosA and okB}
        linhas.append(linha)
        if linha["OK"] and aprovado is None:
            rA_ad, c_ad = piorA
            cob = caso_base.get("cobrimento", 0.05)
            rB_ad = dict(rB_pior)
            rB_ad["flexao_L"] = dict(rB_ad["flexao_L"])
            rB_ad["flexao_L"]["As_adot"] = As_L
            rB_ad["flexao_L"]["barras"] = detalha_barras(As_L, B, cob)
            rB_ad["flexao_B"] = dict(rB_ad["flexao_B"])
            rB_ad["flexao_B"]["As_adot"] = As_B
            rB_ad["flexao_B"]["barras"] = detalha_barras(As_B, L, cob)
            aprovado = (B, L, h, rA_ad, c_ad)
    return {"aprovado": aprovado, "parte_B": rB_ad, "linhas": linhas,
            "governantes": gov,
            "tabela": _tabela_env(linhas, aprovado, casos, gov, rB_ad, caso_base)}


BETA_MIN_BLOCO = 60.0      # NBR 6122:2022 item 7.8.2: angulo minimo do bloco (graus)


def dimensiona_bloco_env(caso_base, casos):
    """BLOCO DE FUNDACAO (NBR 6122:2022 item 7.8.2) pelo ENVELOPE de combinacoes.
    Fundacao rasa de CONCRETO SIMPLES (sem armadura de flexao) - difere da sapata.
    - Base B x L: atende a tensao no solo + estabilidade (Parte A, = sapata).
    - Altura h: do angulo beta >= 60 graus -> h >= tan(60)*(dim_bloco - dim_pilar)/2
      nas duas direcoes (o maior balanco governa). Garante que a tracao no concreto
      e resistida sem armadura (biela de compressao).
    - Informa sigma_t,adm ~ fck/25 <= 0,8 MPa (Alonso; Velloso&Lopes) como FLAG.
    NAO ha Parte B armada (nenhuma As): eis a diferenca essencial p/ a sapata."""
    ap_L = caso_base.get("d_ped") or caso_base.get("ap_L") or 0.30
    ap_B = caso_base.get("b_ped") or caso_base.get("ap_B") or 0.30
    fck = caso_base.get("fck", 20e3)                       # kN/m2
    sigma_t_adm = min(fck / 25.0, 800.0)                  # 0,8 MPa = 800 kN/m2
    tan_beta = math.tan(math.radians(BETA_MIN_BLOCO))
    linhas, aprovado, gov = [], None, {}
    for (B, L, _h0) in ESCADA_SAPATA:
        bal = max((B - ap_B) / 2.0, (L - ap_L) / 2.0)     # maior balanco (m)
        h = math.ceil(tan_beta * bal / 0.05) * 0.05 if bal > 1e-9 else 0.30
        beta = math.degrees(math.atan(h / bal)) if bal > 1e-9 else 90.0
        u_solo = fs_tomb = fs_desl = None
        todosA = True
        for (nm, N, V, M) in casos:
            c = dict(caso_base); c.update(N=N, V=V, M=M, B=B, L=L, h=h)
            rA = verifica_sapata_A(c)
            todosA = todosA and rA["OK_A"]
            if u_solo is None or rA["u_solo"] > u_solo:
                u_solo = rA["u_solo"]; gov["solo"] = (nm, rA["u_solo"])
            if fs_tomb is None or rA["fs_tomb"] < fs_tomb:
                fs_tomb = rA["fs_tomb"]; gov["tomb"] = (nm, rA["fs_tomb"])
            if fs_desl is None or rA["fs_desl"] < fs_desl:
                fs_desl = rA["fs_desl"]; gov["desl"] = (nm, rA["fs_desl"])
        okbeta = beta >= BETA_MIN_BLOCO - 1e-6
        linha = {"B": B, "L": L, "h": h, "u_solo": u_solo, "fs_tomb": fs_tomb,
                 "fs_desl": fs_desl, "beta": beta, "OK": todosA and okbeta}
        linhas.append(linha)
        if linha["OK"] and aprovado is None:
            aprovado = (B, L, h, beta)
    return {"aprovado": aprovado, "linhas": linhas, "governantes": gov,
            "sigma_t_adm": sigma_t_adm, "beta_min": BETA_MIN_BLOCO,
            "tabela": _tabela_bloco(linhas, aprovado, casos, gov, caso_base, sigma_t_adm)}


def _tabela_bloco(linhas, aprovado, casos, gov, caso_base, sigma_t_adm):
    L = ["=" * 82, "DIMENSIONAMENTO DO BLOCO DE FUNDACAO - CONCRETO SIMPLES (NBR 6122 7.8.2)",
         "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL", "=" * 82, "",
         f"sigma_solo,adm = {caso_base['sigma_solo_adm']:.0f} kN/m2  [INPUT sondagem - A CONFIRMAR]",
         f"angulo minimo beta = {BETA_MIN_BLOCO:.0f} graus (dispensa armadura de tracao)",
         f"sigma_t,adm concreto ~ fck/25 = {sigma_t_adm:.0f} kN/m2 (<= 0,8 MPa)  [FLAG]",
         f"Combinacoes ELU consideradas: {len(casos)}", "",
         f"{'BxLxh (m)':>16} | {'u_solo':>6} {'FS_tmb':>6} {'FS_dsl':>6} {'beta(o)':>7} | res",
         "-" * 82]
    for r in linhas:
        tag = "PASSA" if r["OK"] else "nao"
        L.append(f"{r['B']:.2f}x{r['L']:.2f}x{r['h']:.2f} | {r['u_solo']:6.2f} "
                 f"{r['fs_tomb']:6.2f} {r['fs_desl']:6.2f} {r['beta']:7.1f} | {tag}")
    L += ["-" * 82, ""]
    if aprovado:
        B, Lm, h, beta = aprovado
        L += [f"ADOTADO (menor bloco que passa): {B:.2f} x {Lm:.2f} x {h:.2f} m (beta={beta:.1f} graus)",
              "  Concreto SIMPLES (sem armadura de flexao) - biela de compressao.",
              f"  Governantes: solo={gov.get('solo',('-',0))[0]} (u={gov.get('solo',('-',0))[1]:.2f}) ;"
              f" tombamento={gov.get('tomb',('-',0))[0]} (FS={gov.get('tomb',('-',0))[1]:.2f})"]
    else:
        L += ["NENHUM bloco da escada passou - ampliar a escada / usar estaca."]
    L += ["", "[FLAG] sigma_solo,adm e parametros do solo: sondagem (geotecnia).",
          "[FLAG] Concreto simples: confirmar fck e a tensao de tracao (Alonso)."]
    return _pt("\n".join(L))


def _tabela_env(linhas, aprovado, casos, gov, rB, caso_base):
    L = ["=" * 82, "DIMENSIONAMENTO DA SAPATA - ENVELOPE DE COMBINACOES (NBR 6118)",
         "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL", "=" * 82, "",
         f"sigma_solo,adm = {caso_base['sigma_solo_adm']:.0f} kN/m2  [INPUT sondagem - A CONFIRMAR]",
         f"Combinacoes ELU consideradas: {len(casos)}", ""]
    for (nm, N, V, M) in casos:
        L.append(f"    {nm:<20} N={N:+8.1f}  V={V:+7.1f}  M={M:+8.1f} kN,kN.m")
    L += ["", f"{'BxLxh (m)':>16} | {'u_solo':>6} {'FS_tmb':>6} {'FS_dsl':>6} {'u_cd':>5}"
          f" {'As_L':>6} {'As_B':>6} | res", "-" * 82]
    for r in linhas:
        tag = "PASSA" if r["OK"] else "nao"
        L.append(f"{r['B']:.2f}x{r['L']:.2f}x{r['h']:.2f} | {r['u_solo']:6.2f} "
                 f"{r['fs_tomb']:6.2f} {r['fs_desl']:6.2f} {r['u_cd']:5.2f} "
                 f"{r['As_L']*1e4:5.1f}c {r['As_B']*1e4:5.1f}c | {tag}")
    L += ["-" * 82, ""]
    if aprovado:
        B, Lm, h, rA, _ = aprovado
        L += [f"ADOTADA (menor que passa o envelope): {B:.2f} x {Lm:.2f} x {h:.2f} m",
              f"  Governantes: solo={gov.get('solo',('-',0))[0]} (u={gov.get('solo',('-',0))[1]:.2f}) ;"
              f" tombamento={gov.get('tomb',('-',0))[0]} (FS={gov.get('tomb',('-',0))[1]:.2f}) ;",
              f"               deslizamento={gov.get('desl',('-',0))[0]} (FS={gov.get('desl',('-',0))[1]:.2f}) ;"
              f" compr.diagonal={gov.get('compr',('-',0))[0]} (u={gov.get('compr',('-',0))[1]:.2f})"]
        if rB:
            L += ["", relatorio_sapata_B(rB, dict(caso_base))]
    else:
        L += ["NENHUMA sapata da escada passou o envelope - ampliar escada/revisar."]
    L += ["", "[FLAG] sigma_solo,adm e parametros do solo: sondagem (geotecnia).",
          "[FLAG] Detalhamento/ancoragem da armadura (22.6.4): projeto executivo."]
    return _pt("\n".join(L))


RHO_ACO = 7850.0           # massa especifica do aco (kg/m3)


def quantitativo(rA, rB, n_sapatas=1, h_ped=0.5):
    """Quantitativo de UMA sapata x n_sapatas: volume de concreto (m3) e consumo
    de aco da armadura de flexao (kg). Aproximacao: barras na direcao L com
    comprimento ~ B e vice-versa; As e area total por largura (ja integra a
    quantidade de barras). Retorna dict por sapata e total."""
    B, L, h = rA["B"], rA["L"], rA["h"]
    ap_L = rB.get("ap_L", 0.30); ap_B = rB.get("ap_B", 0.30)
    vol_sapata = B * L * h
    vol_ped = ap_L * ap_B * h_ped
    vol_conc = vol_sapata + vol_ped
    As_L = rB["flexao_L"]["As_adot"]           # m2 (por largura B)
    As_B = rB["flexao_B"]["As_adot"]           # m2 (por largura L)
    # volume de aco = As * comprimento das barras (barras // L tem comprimento ~B)
    vol_aco = As_L * (B - 0.10) + As_B * (L - 0.10)
    massa_aco = vol_aco * RHO_ACO
    taxa = massa_aco / vol_conc if vol_conc else 0.0    # kg/m3 (indicador)
    return {"n": n_sapatas,
            "vol_conc_un": vol_conc, "massa_aco_un": massa_aco, "taxa_aco": taxa,
            "vol_conc_tot": vol_conc * n_sapatas, "massa_aco_tot": massa_aco * n_sapatas}


def _pt(s):
    """Ponto decimal -> virgula (fora de numeros de item tipo 6.118)."""
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", s)


def _tabela_sapata(linhas, aprovado, caso, rB=None):
    L = ["=" * 78, "DIMENSIONAMENTO DA SAPATA ISOLADA - PARTE A (GEOTECNIA/ESTABILIDADE)",
         "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL", "=" * 78, "",
         f"Reacao de base: N={caso['N']:+.1f} kN ; V={caso['V']:.1f} kN ; M={caso['M']:.1f} kN.m",
         f"sigma_solo,adm = {caso['sigma_solo_adm']:.0f} kN/m2 (= {caso['sigma_solo_adm']/1000:.2f} MPa)"
         f"  [INPUT sondagem - A CONFIRMAR]",
         f"mu(solo-concreto) = {caso.get('mu', 0.5):.2f} ; FS_tomb>={caso.get('fs_tomb_min', FS_TOMB_MIN):.1f}"
         f" ; FS_desl>={caso.get('fs_desl_min', FS_DESL_MIN):.1f}", "",
         f"{'BxLxh (m)':>16} | {'sig_max':>8} {'u_solo':>6} | {'FS_tomb':>7} {'FS_desl':>7}"
         f" {'contato':>7} | resultado", "-" * 78]
    for r in linhas:
        tag = "PASSA" if r["OK_A"] else "nao passa"
        sm = f"{r['sigma_max']:.0f}" if r['sigma_max'] else "---"
        L.append(f"{r['B']:.2f}x{r['L']:.2f}x{r['h']:.2f} | {sm:>8} {r['u_solo']:6.2f} |"
                 f" {r['fs_tomb']:7.2f} {r['fs_desl']:7.2f} {r['x_contato']/r['L']*100:6.0f}%"
                 f" | {tag}")
    L += ["-" * 78, ""]
    if aprovado:
        B, Lm, h, r, _ = aprovado
        L += [f"ADOTADA (menor que passa): {B:.2f} x {Lm:.2f} x {h:.2f} m",
              f"  sigma_max={r['sigma_max']:.0f} kN/m2 <= {r['sigma_adm']:.0f} (u={r['u_solo']:.2f}) ;"
              f" FS_tomb={r['fs_tomb']:.2f} ; FS_desl={r['fs_desl']:.2f}",
              f"  peso proprio+reaterro={r['Pp']:.1f} kN ; regime solo: {r['regime']}"]
        if r.get("recalque_mm") is not None:
            L += [f"  Recalque (ELS, teoria da elasticidade): rho={r['recalque_mm']:.1f} mm "
                  f"<= adm {r['recalque_adm_mm']:.0f} mm -> "
                  f"{'OK' if r['ok_recalque'] else 'NAO PASSA'}"]
        else:
            L += ["  Recalque: [informe Es_solo (deformabilidade, sondagem) para "
                  "verificar - NBR 6122]"]
    else:
        L += ["NENHUMA sapata da escada passou - ampliar a escada, reduzir sigma pela",
              "geometria, ou revisar (M/V alto: aumentar sapata, tirante, ou base rotulada)."]
    if rB is not None:
        L += ["", "-" * 78, "PARTE B - CONCRETO ARMADO (NBR 6118:2014):", "",
              relatorio_sapata_B(rB, caso)]
    L += ["", "[FLAG] sigma_solo,adm e parametros do solo: relatorio de sondagem (geotecnia).",
          "[FLAG] A reacao (N,V,M) e a combinacao que governa a PLACA DE BASE (em",
          "       galpao leve, o vento/uplift). A PRESSAO NO SOLO deve ainda ser",
          "       confirmada para a combinacao de N MAXIMO gravitacional (pior caso",
          "       de bearing) - PENDENTE envelope de combinacoes por elemento."]
    return _pt("\n".join(L))


# ==== DETALHAMENTO EXECUTIVO DE ARMADURA ====================================

def comprimento_ancoragem(phi_mm, fck_MPa=25, fyk_MPa=500, gancho=True,
                           boa_aderencia=True):
    """Comprimento de ancoragem basico (lb) e necessario (lb,nec) (NBR 6118 9.4).
    Retorna lb, lb_nec, lb_min em mm, fbd em MPa."""
    fctd = 0.7 * 0.3 * fck_MPa ** (2.0 / 3.0) / 1.4
    fbd = 2.25 * (1.0 if boa_aderencia else 0.7) * 1.0 * fctd
    fyd = fyk_MPa / 1.15
    lb = (phi_mm / 4.0) * (fyd / fbd)
    alpha = 0.7 if gancho else 1.0
    lb_min = max(0.3 * lb, 10.0 * phi_mm, 100.0)
    lb_nec = max(alpha * lb, lb_min)
    return {"lb_mm": round(lb), "lb_nec_mm": round(lb_nec),
            "lb_min_mm": round(lb_min), "fbd_MPa": round(fbd, 2),
            "gancho": gancho, "phi_mm": phi_mm}


def quadro_dobramento(barras):
    """Gera quadro de dobramento simplificado (phi, n, comprimento, peso).
    barras: lista de dicts com phi_mm, n, comprimento_total_mm."""
    return [{"phi": b["phi_mm"], "n": b["n"],
             "L_total_m": round(b["comprimento_total_mm"] / 1000.0, 2),
             "peso_kg": round(b["n"] * (b["comprimento_total_mm"] / 1000.0)
                              * 0.00617 * b["phi_mm"] ** 2, 2)}
            for b in barras]


# ---- PARTE B: CONCRETO ARMADO (NBR 6118) -----------------------------------
# Metodo extraido da NBR 6118:2014 (pesquisa/aco/nbr-6118-2014...pdf):
#   - 22.6.1  : sapata RIGIDA se h >= (a - ap)/3 nas duas direcoes (a=dim sapata,
#               ap=dim pilar); rigida admite distribuicao plana de tensoes.
#   - 22.6.2.2: rigida trabalha a FLEXAO (2 direcoes, tracao uniforme na largura)
#               e ao cisalhamento por COMPRESSAO DIAGONAL conforme 19.5.3.1; fica
#               dentro do cone -> NAO ha puncao (so a flexivel, 22.6.4.1.3).
#   - 22.6.3  : permite modelo de FLEXAO (alem de biela-tirante 3D).
#   - 17.2.2  : bloco retangular de tensoes; fck<=50 MPa -> lambda=0,8 ; alpha_c=0,85.
#   - 19.5.3.1: tau_Sd <= tau_Rd2 = 0,27*alpha_v*fcd ; alpha_v=(1-fck/250) [MPa];
#               tau_Sd = Fd/(u0*d) [+ K*Md/(Wp0*d)] no perimetro do pilar u0
#               (K da Tabela 19.2 em funcao de C1/C2).
LAMBDA_BLOCO = 0.80        # 17.2.2 (fck<=50 MPa)
ALPHA_C = 0.85             # 17.2.2 (fck<=50 MPa)
XD_LIM = 0.45              # 14.6.4.3 limite de ductilidade x/d (fck<=50)
RHO_MIN = 0.0015           # piso absoluto 0,15% (17.3.5.2.1); rho_min(fck) p/ fck>30

# Tabela 17.3 (NBR 6118:2014) - taxa minima de armadura de flexao, secao
# retangular, CA-50, gamma_c=1,4, d/h=0,8. Piso absoluto 0,15% (17.3.5.2.1); sobe
# para fck>30. Valores conferidos contra a norma (Carvalho & Figueiredo, Quadro
# 4.2 = Tabela 17.3) - nao de memoria. Adotado o valor de VIGA (mais exigente que
# o de laje 2-direcoes 0,67*rho_min, 19.3.3.2/Tab.19.1): remove o canto nao-
# conservador qualquer que seja a classificacao da sapata pelo revisor.
_RHO_MIN_TAB = {20: 0.00150, 25: 0.00150, 30: 0.00150, 35: 0.00164,
                40: 0.00179, 45: 0.00194, 50: 0.00208}


def rho_min(fck_MPa):
    """Taxa minima de armadura de flexao (Tabela 17.3, secao retangular CA-50).
    Piso 0,15% ate fck 30; interpola linearmente entre pontos tabelados p/ fck>30
    (a favor da seguranca). fck em MPa. Ex.: 25->0,00150 ; 40->0,00179."""
    pts = sorted(_RHO_MIN_TAB.items())
    if fck_MPa <= pts[0][0]:
        return pts[0][1]
    if fck_MPa >= pts[-1][0]:
        return pts[-1][1]
    for (f0, r0), (f1, r1) in zip(pts, pts[1:]):
        if f0 <= fck_MPa <= f1:
            return r0 + (r1 - r0) * (fck_MPa - f0) / (f1 - f0)
    return pts[-1][1]

# Tabela 19.2 - coeficiente K (parcela de M transmitida por cisalhamento).
_K_TAB = [(0.5, 0.45), (1.0, 0.60), (2.0, 0.70), (3.0, 0.80)]


def _K_puncao(c1_c2):
    """Interpola/limita K da Tabela 19.2 pela relacao C1/C2."""
    if c1_c2 <= _K_TAB[0][0]:
        return _K_TAB[0][1]
    if c1_c2 >= _K_TAB[-1][0]:
        return _K_TAB[-1][1]
    for (r0, k0), (r1, k1) in zip(_K_TAB, _K_TAB[1:]):
        if r0 <= c1_c2 <= r1:
            return k0 + (k1 - k0) * (c1_c2 - r0) / (r1 - r0)
    return _K_TAB[-1][1]


def _armadura_flexao(M_d, b, d, fck, fyk):
    """Armadura de flexao por bloco retangular (17.2.2). Retorna
    (As, x_d, z, ok_dominio). M_d em kN.m ; b,d em m ; fck,fyk em kN/m2."""
    fcd = fck / 1.4
    fyd = fyk / 1.15
    if M_d <= 0:
        return 0.0, 0.0, d, True
    mu = M_d / (b * d * d * ALPHA_C * fcd)
    disc = 1.0 - 2.0 * mu
    if disc < 0:                                  # secao insuficiente a flexao
        return None, 1.0 / LAMBDA_BLOCO, 0.0, False
    x_d = (1.0 - math.sqrt(disc)) / LAMBDA_BLOCO
    z = d * (1.0 - 0.5 * LAMBDA_BLOCO * x_d)
    As = M_d / (fyd * z)
    return As, x_d, z, (x_d <= XD_LIM + 1e-9)


def puncao_sapata(N_d, B, L, ap_L, ap_B, d, fck, As_L, As_B):
    """PUNCAO da sapata FLEXIVEL (NBR 6118 19.5), no contorno critico C' distante
    2d do pilar. So faz sentido quando a sapata NAO e rigida (a rigida fica dentro
    do cone e dispensa punção por 22.6.2.2). Modelo de sapata: a reacao do solo
    DENTRO de C' alivia a forca de punção (nao atravessa a superficie critica).

      - 19.5.2.1: tau_Sd = F_Sd,ef / (u * d) ; u = perimetro de C' (2d do pilar);
      - 19.5.3.2: tau_Rd1 = 0,13*(1+raiz(20/d[cm]))*(100*rho*fck[MPa])^(1/3)
                  (sigma_cp=0: sem protensao/normal na sapata -> conservador);
      - rho = raiz(rho_x*rho_y), taxa geometrica de armadura de flexao aderente.
    Unidades: N em kN, dims em m, fck em kN/m2. Retorna dict com tau e utilizacao."""
    C1, C2 = ap_L, ap_B
    u = 2.0 * (C1 + C2) + 2.0 * math.pi * (2.0 * d)      # contorno C' a 2d (cantos arredondados)
    # area em planta dentro de C' = soma de Minkowski do pilar com disco de raio 2d
    A_cp = C1 * C2 + 2.0 * (C1 + C2) * (2.0 * d) + math.pi * (2.0 * d) ** 2
    sig = N_d / (B * L)                                  # pressao media (equilibrio)
    F_ef = max(N_d - sig * min(A_cp, B * L), 0.0)        # alivio da reacao dentro de C'
    tau_sd = F_ef / (u * d) if (u * d) > 0 else float("inf")
    fck_MPa = fck / 1000.0
    d_cm = d * 100.0
    rho_x = As_L / (B * d) if (B * d) > 0 else 0.0       # As_L distribuido na largura B
    rho_y = As_B / (L * d) if (L * d) > 0 else 0.0
    rho = math.sqrt(max(rho_x, 0.0) * max(rho_y, 0.0))
    tau_rd1 = 0.13 * (1.0 + math.sqrt(20.0 / d_cm)) * (100.0 * rho * fck_MPa) ** (1.0 / 3.0) * 1000.0
    return {"tau_sd": tau_sd, "tau_rd1": tau_rd1, "u": u, "A_cp": A_cp, "F_ef": F_ef,
            "rho": rho, "u_punc": (tau_sd / tau_rd1 if tau_rd1 > 0 else float("inf")),
            "ok": tau_sd <= tau_rd1 + 1e-9}


# Bitolas comerciais (mm) e area da barra (m2). CA-50.
_BITOLAS = [6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0]
S_MIN = 0.10        # espacamento min pratico entre barras (m) - A CONFIRMAR (18.3.2.2)
S_MAX = 0.20        # espacamento max pratico p/ armadura de flexao (m) - A CONFIRMAR


def _area_barra(phi_mm):
    return math.pi * (phi_mm / 1000.0) ** 2 / 4.0


def detalha_barras(As_req, largura, cobrimento=0.05):
    """Traduz As requerido (m2, por largura) num arranjo de barras: escolhe a
    bitola comercial cujo espacamento resultante cai na faixa pratica
    [S_MIN, S_MAX]; entre as validas, prefere a de MENOR bitola (mais barras,
    fissuracao melhor). n = ceil(As_req/A_barra) (>=2). Retorna dict ou None.
    Espacamentos-limite marcados A CONFIRMAR (detalhamento NBR 6118)."""
    b_util = max(largura - 2 * cobrimento, 0.0)
    if As_req <= 0 or b_util <= 0:
        return None
    melhor = None
    for phi in _BITOLAS:
        A1 = _area_barra(phi)
        n = max(2, math.ceil(As_req / A1))
        s = b_util / (n - 1)                       # espacamento entre eixos
        As_ef = n * A1
        cand = {"phi": phi, "n": n, "s": s, "As_ef": As_ef,
                "na_faixa": (S_MIN - 1e-9) <= s <= (S_MAX + 1e-9)}
        if cand["na_faixa"]:
            if melhor is None or phi < melhor["phi"]:
                melhor = cand
    if melhor:
        return melhor
    # nenhuma na faixa: adota a que da o MAIOR espacamento <= S_MAX (mais barras)
    # ou, se todas muito juntas, a menor bitola; devolve a mais proxima da faixa.
    fallback = None
    for phi in _BITOLAS:
        A1 = _area_barra(phi)
        n = max(2, math.ceil(As_req / A1))
        s = b_util / (n - 1)
        if s <= S_MAX + 1e-9:                      # cabe (pode estar < S_MIN)
            fallback = {"phi": phi, "n": n, "s": s, "As_ef": n * A1,
                        "na_faixa": False}
            break
    return fallback


def dimensiona_sapata_B(caso, r_A):
    """PARTE B - concreto da sapata (NBR 6118) sobre a geometria adotada na
    Parte A: rigidez (22.6.1), armadura de flexao nas 2 direcoes (22.6.3 modelo
    de flexao + 17.2.2), compressao diagonal no perimetro do pilar (19.5.3.1) e
    As,min (17.3.5.2). Convencao: L // eixo do momento do portico ; pedestal
    d_ped // L, b_ped // B. Esforcos majorados por gamma_f."""
    B, L, h = r_A["B"], r_A["L"], r_A["h"]
    ap_L = caso.get("d_ped") or caso.get("ap_L") or 0.30    # pilar // L
    ap_B = caso.get("b_ped") or caso.get("ap_B") or 0.30    # pilar // B
    fck, fyk = caso["fck"], caso["fyk"]
    fck_MPa = fck / 1000.0
    cob = caso.get("cobrimento", 0.05)             # contato c/ solo: >= 5 cm (7.4)
    phi = caso.get("phi_barra", 0.0125)
    gf = caso.get("gamma_f", 1.4)
    d = h - cob - phi                              # altura util (2 camadas ort.)
    r = {"B": B, "L": L, "h": h, "d": d, "ap_L": ap_L, "ap_B": ap_B}

    # 1) RIGIDEZ (22.6.1): h >= (a - ap)/3 nas duas direcoes
    rig_L = h >= (L - ap_L) / 3.0 - 1e-9
    rig_B = h >= (B - ap_B) / 3.0 - 1e-9
    r["rigida"] = rig_L and rig_B
    r["rig_L"], r["rig_B"] = rig_L, rig_B

    # esforcos de calculo (ELU); pressao de flexao = so a reacao do pilar (o peso
    # proprio da sapata nao flexiona a propria sapata). Conservador: sigma_max.
    N_d, V_d, M_d0 = gf * caso["N"], gf * caso["V"], gf * caso["M"]
    sig_max_d, _, _, _ = tensoes_solo(N_d, M_d0, B, L)
    if sig_max_d is None:
        sig_max_d = N_d / (B * L)
    r["sigma_d"] = sig_max_d

    # 2) FLEXAO (22.6.3 modelo de flexao + 17.2.2): balanco a partir da face do
    #    pilar, pressao (conservadora) sig_max_d uniforme sobre o balanco.
    c_L = max((L - ap_L) / 2.0, 0.0)               # balanco na direcao L
    c_B = max((B - ap_B) / 2.0, 0.0)               # balanco na direcao B
    M_dL = sig_max_d * B * c_L ** 2 / 2.0          # momento (barras // L), largura B
    M_dB = sig_max_d * L * c_B ** 2 / 2.0          # momento (barras // B), largura L
    As_L, xdL, zL, okL = _armadura_flexao(M_dL, B, d, fck, fyk)
    As_B, xdB, zB, okB = _armadura_flexao(M_dB, L, d, fck, fyk)
    rho = rho_min(fck_MPa)                          # Tabela 17.3 (sobe p/ fck>30)
    As_min_L = rho * B * h                          # As,min por largura (17.3.5.2)
    As_min_B = rho * L * h
    As_ad_L = max(As_L or 0.0, As_min_L)
    As_ad_B = max(As_B or 0.0, As_min_B)
    r["flexao_L"] = {"M_d": M_dL, "As": As_L, "As_min": As_min_L, "x_d": xdL,
                     "As_adot": As_ad_L, "ok_dom": okL, "balanco": c_L,
                     "barras": detalha_barras(As_ad_L, B, cob)}      # barras // L (largura B)
    r["flexao_B"] = {"M_d": M_dB, "As": As_B, "As_min": As_min_B, "x_d": xdB,
                     "As_adot": As_ad_B, "ok_dom": okB, "balanco": c_B,
                     "barras": detalha_barras(As_ad_B, L, cob)}      # barras // B (largura L)

    # 3) COMPRESSAO DIAGONAL no perimetro do pilar (19.5.3.1)
    fcd = fck / 1.4
    alpha_v = 1.0 - fck_MPa / 250.0
    tau_rd2 = 0.27 * alpha_v * fcd
    u0 = 2.0 * (ap_L + ap_B)                        # perimetro do pilar
    # parcela de momento (19.5.2.2): C1 // excentricidade (= ap_L, plano do M) ;
    # Wp0 = modulo plastico do contorno do pilar (termos com d anulam em u0).
    C1, C2 = ap_L, ap_B
    K = _K_puncao(C1 / C2 if C2 > 0 else 1.0)
    Wp0 = C1 ** 2 / 2.0 + C1 * C2                   # 19.5.2.3 reduzido ao perim. u0
    tau_sd = N_d / (u0 * d) + (K * abs(M_d0) / (Wp0 * d) if Wp0 > 0 else 0.0)
    r["compr_diag"] = {"tau_sd": tau_sd, "tau_rd2": tau_rd2, "u0": u0,
                       "alpha_v": alpha_v, "K": K, "u_cd": tau_sd / tau_rd2}

    r["ok_flexao"] = okL and okB
    r["ok_compr_diag"] = tau_sd <= tau_rd2 + 1e-9

    # 4) PUNCAO (19.5): so a sapata FLEXIVEL. A rigida fica dentro do cone e
    #    dispensa punção (22.6.2.2) - a compressao diagonal (item 3) ja a cobre.
    if r["rigida"]:
        r["OK_B"] = r["ok_flexao"] and r["ok_compr_diag"]
    else:
        pc = puncao_sapata(N_d, B, L, ap_L, ap_B, d, fck, As_ad_L, As_ad_B)
        r["puncao"] = pc
        r["ok_puncao"] = pc["ok"]
        r["OK_B"] = r["ok_flexao"] and r["ok_compr_diag"] and r["ok_puncao"]
        r["flag_flexivel"] = ("Sapata FLEXIVEL (h < (a-ap)/3): PUNCAO verificada "
                              "(19.5) no contorno C' a 2d -> u_punc=%.2f (%s). Flexao "
                              "nao-uniforme (22.6.4.1.3) mantida simplificada "
                              "(conservador). Alternativa: aumentar h -> rigida."
                              % (pc["u_punc"], "OK" if pc["ok"] else "NAO PASSA"))
    return r


def relatorio_sapata_B(rB, caso):
    def cm2(As):
        return (As or 0.0) * 1e4       # m2 -> cm2 (por largura da sapata)
    L = ["SAPATA - PARTE B (CONCRETO ARMADO) - NBR 6118:2014",
         f"  Geometria: {rB['B']:.2f} x {rB['L']:.2f} x {rB['h']:.2f} m ; "
         f"d(util)={rB['d']*100:.1f} cm ; pilar {rB['ap_B']*100:.0f}x{rB['ap_L']*100:.0f} cm",
         f"  RIGIDEZ (22.6.1): h>= (a-ap)/3 -> dir.L {'OK' if rB['rig_L'] else 'NAO'} ; "
         f"dir.B {'OK' if rB['rig_B'] else 'NAO'} -> "
         f"{'RIGIDA (sem puncao)' if rB['rigida'] else 'FLEXIVEL (ver flag)'}",
         f"  fck={caso['fck']/1000:.0f} MPa ; fyk={caso['fyk']/1000:.0f} MPa ; "
         f"cobrimento={caso.get('cobrimento',0.05)*100:.0f} cm ; gamma_f={caso.get('gamma_f',1.4):.1f}",
         f"  Pressao de calculo (flexao) sigma_d={rB['sigma_d']:.0f} kN/m2"]
    for tag, f in (("L (barras // L)", rB["flexao_L"]), ("B (barras // B)", rB["flexao_B"])):
        dom = "OK" if f["ok_dom"] else "x/d>lim (aumentar h/fck!)"
        L.append(f"  Flexao dir.{tag}: balanco={f['balanco']*100:.0f} cm ; "
                 f"M_d={f['M_d']:.1f} kN.m ; x/d={f['x_d']:.2f} ({dom}) ; "
                 f"As={cm2(f['As']):.1f} cm2 ; As,min={cm2(f['As_min']):.1f} -> "
                 f"As,adot={cm2(f['As_adot']):.1f} cm2")
        bb = f.get("barras")
        if bb:
            aviso = "" if bb["na_faixa"] else "  [!] espacamento fora de [10;20]cm - revisar"
            L.append(f"      -> {bb['n']} barras phi {bb['phi']:.1f} mm c/ "
                     f"{bb['s']*100:.0f} cm (As,ef={cm2(bb['As_ef']):.1f} cm2){aviso}")
    cd = rB["compr_diag"]
    L.append(f"  Compressao diagonal (19.5.3.1): tau_Sd={cd['tau_sd']:.0f} <= "
             f"tau_Rd2={cd['tau_rd2']:.0f} kN/m2 (alpha_v={cd['alpha_v']:.2f} ; "
             f"K={cd['K']:.2f}) -> u={cd['u_cd']:.2f} "
             f"{'OK' if rB['ok_compr_diag'] else 'NAO PASSA'}")
    if not rB["rigida"] and rB.get("puncao"):
        pc = rB["puncao"]
        L.append(f"  Puncao (19.5, sapata flexivel): tau_Sd={pc['tau_sd']:.0f} <= "
                 f"tau_Rd1={pc['tau_rd1']:.0f} kN/m2 no contorno C' a 2d "
                 f"(u={pc['u']*100:.0f} cm ; rho={pc['rho']*100:.3f}%) -> "
                 f"u_punc={pc['u_punc']:.2f} {'OK' if pc['ok'] else 'NAO PASSA'}")
    L.append(f"  -> PARTE B {'OK' if rB['OK_B'] else 'NAO PASSA'}")
    if not rB["rigida"]:
        L.append("  [FLAG] " + rB["flag_flexivel"])
    L += ["  [FLAG] As,min=0,15% (17.3.5.2) - confirmar p/ fck adotado.",
          "  [FLAG] Ancoragem da armadura de arranque (22.6.4.1.2) e detalhamento",
          "         (gancho de face a face, 22.6.4.1.1): projeto executivo."]
    return _pt("\n".join(L))


# ---- exemplo PLACEHOLDER (a skill pergunta ao usuario) ---------------------
CASO_EXEMPLO = {
    "nome": "Sapata pilar de galpao (EXEMPLO - a skill pergunta)",
    "N": 49.0, "V": 26.0, "M": 60.0,             # reacao de base (kN, kN.m)
    "sigma_solo_adm": 200.0,                     # kN/m2 = 0,20 MPa (sondagem!)
    "mu": 0.5, "coesao": 0.0,
    "h_reaterro": 0.5, "d_ped": 0.30, "b_ped": 0.30, "h_ped": 0.50,
    "fck": 25e3, "fyk": 500e3, "cobrimento": 0.04,
    "B": 1.5, "L": 1.5, "h": 0.40,
}


def _selftest():
    # 1) nucleo: e<=L/6 -> contato total, sigma = N/A*(1 +- 6e/L)
    sm, sn, reg, x = tensoes_solo(300.0, 30.0, 2.0, 2.0)   # e=0,1 ; L/6=0,333
    A = 4.0
    assert abs(sm - 300.0 / A * (1 + 6 * 0.1 / 2.0)) < 1e-6, sm
    assert "nucleo" in reg and abs(x - 2.0) < 1e-9
    # 2) borda: e>L/6 -> triangular, x=3*(L/2-e), sig_max=2N/(B*x)
    sm2, sn2, reg2, x2 = tensoes_solo(100.0, 60.0, 1.5, 1.5)   # e=0,6 ; L/6=0,25
    xexp = 3.0 * (0.75 - 0.6)
    assert abs(x2 - xexp) < 1e-9 and abs(sm2 - 2 * 100.0 / (1.5 * xexp)) < 1e-6
    assert sn2 == 0.0 and "borda" in reg2
    # 3) estabilidade: FS_tomb = M_est/M_tomb com peso proprio
    e = estabilidade(100.0, 20.0, 40.0, 1.5, 1.5, 0.4, 0.5)
    Pp = 1.5 * 1.5 * 0.4 * GAMMA_C_CONCRETO
    assert abs(e["Pp"] - Pp) < 1e-6
    assert abs(e["M_tomb"] - (20.0 * 0.4 + 40.0)) < 1e-9
    assert abs(e["M_est"] - (100.0 + Pp) * 0.75) < 1e-6
    assert abs(e["fs_desl"] - ((100.0 + Pp) * 0.5) / 20.0) < 1e-6
    # 3b) coesao atua so na area efetiva: sob uplift (e>L/6) A_ef = B*x < B*L
    ec = estabilidade(100.0, 20.0, 80.0, 1.5, 1.5, 0.4, 0.5, coesao=10.0)
    Ntc = 100.0 + Pp                               # e=80/Ntc > L/6=0,25 -> uplift
    xc = 3.0 * (0.75 - 80.0 / Ntc)
    assert abs(ec["A_ef"] - 1.5 * xc) < 1e-6 and ec["A_ef"] < 1.5 * 1.5   # < B*L
    assert abs(ec["fs_desl"] - (Ntc * 0.5 + 10.0 * 1.5 * xc) / 20.0) < 1e-6
    e2 = estabilidade(300.0, 20.0, 10.0, 1.5, 1.5, 0.4, 0.5, coesao=10.0)  # contato total
    assert abs(e2["A_ef"] - 1.5 * 1.5) < 1e-9      # e<L/6 -> A_ef = B*L (nao regride)
    # 4) dimensiona: escolhe a menor que passa + roda Parte B
    d = dimensiona_sapata(CASO_EXEMPLO)
    assert d["aprovado"] is not None, "exemplo deveria passar em alguma sapata"
    B, Lm, h, r, _ = d["aprovado"]
    # 5) Parte B: bloco retangular reversivel (As -> M de volta)
    As, xd, z, ok = _armadura_flexao(100.0, 1.0, 0.5, 25e3, 500e3)
    fyd = 500e3 / 1.15
    assert abs(As * fyd * z - 100.0) < 1e-6 and ok, (As, xd, z)
    # 6) compressao diagonal: alpha_v e tau_rd2 conforme 19.5.3.1
    rB = d["parte_B"]
    assert rB is not None and abs(rB["compr_diag"]["alpha_v"] - (1 - 25.0 / 250.0)) < 1e-9
    assert abs(rB["compr_diag"]["tau_rd2"] - 0.27 * (1 - 25.0 / 250.0) * 25e3 / 1.4) < 1e-3
    # 7) rigidez 22.6.1
    assert rB["rigida"] == (h >= (Lm - CASO_EXEMPLO["d_ped"]) / 3.0 - 1e-9 and
                            h >= (B - CASO_EXEMPLO["b_ped"]) / 3.0 - 1e-9)
    # 8) ENVELOPE: bearing pega N max, tombamento pega N min + M
    casos = [("C1_grav", 300.0, 10.0, 20.0),      # N alto -> governa solo
             ("C2_uplift", 5.0, 30.0, 70.0)]      # N baixo + M -> governa tombamento
    de = dimensiona_sapata_env(dict(CASO_EXEMPLO), casos)
    assert de["aprovado"] is not None
    assert de["governantes"]["solo"][0] == "C1_grav"       # N maximo governa bearing
    assert de["governantes"]["tomb"][0] == "C2_uplift"     # uplift governa tombamento
    # 9) detalhamento: As_ef >= As_req e espacamento coerente
    bb = detalha_barras(18e-4, 2.0, 0.05)          # 18 cm2 em 2 m
    assert bb and bb["As_ef"] >= 18e-4 - 1e-9 and bb["n"] >= 2
    assert bb["s"] > 0
    # 10) rho_min (Tabela 17.3): piso 0,15% ate fck 30 ; sobe p/ fck>30
    assert rho_min(20) == 0.0015 and rho_min(25) == 0.0015 and rho_min(30) == 0.0015
    assert abs(rho_min(35) - 0.00164) < 1e-9 and abs(rho_min(50) - 0.00208) < 1e-9
    assert rho_min(15) == 0.0015 and rho_min(90) == 0.00208     # fora da faixa: extremos
    assert 0.00164 < rho_min(37.5) < 0.00179                    # interpola 35..40
    # 11) PUNCAO (19.5): sapata flexivel verifica C' a 2d; formulas conferidas
    pc = puncao_sapata(300.0, 2.0, 2.0, 0.30, 0.30, 0.25, 25e3, 8e-4, 8e-4)
    d_ = 0.25; C1 = C2 = 0.30
    u_exp = 2.0 * (C1 + C2) + 2.0 * math.pi * (2.0 * d_)
    assert abs(pc["u"] - u_exp) < 1e-9                           # contorno C' a 2d
    rho_exp = math.sqrt((8e-4 / (2.0 * d_)) ** 2)               # rho_x=rho_y aqui
    trd1 = 0.13 * (1.0 + math.sqrt(20.0 / (d_ * 100.0))) * (100.0 * rho_exp * 25.0) ** (1.0 / 3.0) * 1000.0
    assert abs(pc["tau_rd1"] - trd1) < 1e-3                      # 19.5.3.2
    assert pc["F_ef"] < 300.0 and pc["F_ef"] > 0.0              # alivio da reacao do solo
    assert "u_punc" in pc and pc["u_punc"] >= 0.0
    # sapata deliberadamente FLEXIVEL (h pequeno) -> Parte B roda puncao, nao so flag
    cf = dict(CASO_EXEMPLO)
    rBf = dimensiona_sapata_B(cf, {"B": 2.5, "L": 2.5, "h": 0.30})   # h<(2,5-0,3)/3=0,73
    assert not rBf["rigida"] and "puncao" in rBf and "ok_puncao" in rBf
    # 12) RECALQUE elastico (NBR 6122 / teoria da elasticidade)
    rho = recalque_elastico(200.0, 2.0, 20e3, 0.30, 0.88)          # q200,B2,Es20MPa
    assert abs(rho - 200.0 * 2.0 * (1 - 0.30 ** 2) * 0.88 / 20e3) < 1e-12
    assert recalque_elastico(200.0, 2.0, 0.0) is None              # Es=0 -> None
    # sem Es -> nao verifica (informativo); com Es -> entra no OK_A
    cse = dict(CASO_EXEMPLO); cse.update(B=2.0, L=2.0, h=0.60)
    r_sem = verifica_sapata_A(cse)
    assert r_sem["recalque_mm"] is None and r_sem["ok_recalque"] is None
    cse2 = dict(cse); cse2.update(Es_solo=20e3, nu_solo=0.30, recalque_adm_mm=25.0)
    r_com = verifica_sapata_A(cse2)
    assert r_com["recalque_mm"] is not None and r_com["ok_recalque"] in (True, False)
    print("fundacao_sapata self-test PASSED")
    print(f"  exemplo -> sapata {B:.2f}x{Lm:.2f}x{h:.2f} m ; sig_max={r['sigma_max']:.0f}"
          f" kN/m2 (u={r['u_solo']:.2f}) ; FS_tomb={r['fs_tomb']:.2f} ; FS_desl={r['fs_desl']:.2f}")
    fL, fB = rB["flexao_L"], rB["flexao_B"]
    print(f"  Parte B -> {'RIGIDA' if rB['rigida'] else 'FLEXIVEL'} ; d={rB['d']*100:.0f} cm ; "
          f"As_L={fL['As_adot']*1e4:.1f} cm2 ; As_B={fB['As_adot']*1e4:.1f} cm2 ; "
          f"compr.diag u={rB['compr_diag']['u_cd']:.2f}")


if __name__ == "__main__":
    _selftest()
    print()
    d = dimensiona_sapata(CASO_EXEMPLO)
    print(d["tabela"])
