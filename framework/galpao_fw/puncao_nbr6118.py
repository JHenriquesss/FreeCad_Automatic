# ============================================================================
# puncao_nbr6118.py - O QUE ESTE SCRIPT FAZ / CALCULA
# PUNCAO (cisalhamento em duas direcoes) da ABNT NBR 6118:2014, item 19.5 -
# completo o suficiente para LAJE LISA / LAJE-COGUMELO, que e o que faltava:
# a sapata (fundacao_sapata) ja cobria o pilar INTERNO com o contorno C' a 2d,
# mas nao a borda, o canto, a armadura de puncao, o contorno C'', as aberturas,
# a armadura obrigatoria de 19.5.3.5 nem o colapso progressivo de 19.5.4.
#
# REUSO POR PRIMITIVA (licao da Fase 6B: uma so implementacao): as tensoes
# resistentes tau_Rd1/tau_Rd2 e o coeficiente K da Tabela 19.2 moram AQUI, e
# fundacao_sapata passa a importa-los deste modulo.
#
# GEOMETRIA POR CONSTRUCAO, NAO POR FORMULA FECHADA: o contorno critico e gerado
# como poligonal (retangulo do pilar dilatado de 'a', com os cantos em arco de
# raio 'a'), e dele saem u, o centroide e o modulo plastico Wp = integral|e|dl,
# que e a PROPRIA definicao da norma. A formula fechada do pilar interno
# (Wp = C1^2/2 + C1*C2 + 4*C2*d + 16*d^2 + 2*pi*d*C1) e usada apenas como
# CONFERENCIA no teste - assim borda, canto, C'' e contorno com abertura saem da
# mesma implementacao, sem transcrever mais formulas.
#
# AFERICAO - LIMITE DECLARADO: nao ha exemplo resolvido de puncao pela NBR 6118
# no acervo (Carvalho cap.7 so trata laje sobre vigas; o Vol.4 do Araujo esta
# digitalizado so ate a p.168; Nilson/MacGregor resolvem pelo ACI 318, que e
# outro modelo). Portanto NAO ha aqui afericao contra exemplo de livro, como ha
# em laje_concreto (Carvalho Ex.1) ou na sapata (Alonso). O que existe:
#   (1) cada expressao transcrita LITERALMENTE da norma, com o item ao lado;
#   (2) a geometria conferida contra a formula fechada da propria norma;
#   (3) cross-check numerico contra fundacao_sapata.puncao_sapata (pilar interno).
# Um exemplo resolvido de laje lisa continua sendo item A CONFIRMAR do acervo.
# Unidades: m, kN (fck em kN/m2), momentos em kN.m.
# ============================================================================
"""Puncao da NBR 6118:2014 (19.5) para laje lisa: contornos criticos C, C' e C''
de pilar interno, de borda e de canto, tensoes resistentes com e sem armadura de
puncao, aberturas proximas, armadura obrigatoria (19.5.3.5) e protecao contra
colapso progressivo (19.5.4)."""

from __future__ import annotations

import math
import re

# ---------------------------------------------------------------------------
# Tabela 19.2 - coeficiente K (parcela de M_Sd transmitida por cisalhamento).
# ---------------------------------------------------------------------------
K_TAB_19_2 = ((0.5, 0.45), (1.0, 0.60), (2.0, 0.70), (3.0, 0.80))
K_CIRCULAR = 0.60          # pilar circular interno (19.5.2.2)

# 19.5.3.3 / 20.4 - tensao de calculo maxima da armadura de puncao.
FYWD_LIM = {"stud": 300e3, "estribo": 250e3}    # kN/m2
SR_MAX_FATOR = 0.75        # s_r <= 0,75 d
S0_MAX_FATOR = 0.50        # 1a linha de conectores a no maximo 0,5 d da face
DIST_ABERTURA = 8.0        # aberturas a menos de 8d do contorno C (19.5.1)
FRACAO_MIN_19_5_3_5 = 0.50  # armadura para no minimo 50% de F_Sd
FATOR_COLAPSO = 1.5        # fyd*As,ccp >= 1,5*F_Sd (19.5.4)
GF_COLAPSO = 1.2           # 19.5.4 permite calcular F_Sd com gamma_f = 1,2

_N_ARCO = 24               # discretizacao de cada arco de canto do contorno


def _pt(txt):
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", txt)


# ---------------------------------------------------------------------------
# 1. PRIMITIVAS DE RESISTENCIA (19.5.3)
# ---------------------------------------------------------------------------

def K_puncao(c1_c2):
    """Coeficiente K da Tabela 19.2, interpolado em C1/C2 e limitado a faixa
    tabelada (0,45 em C1/C2 <= 0,5 ; 0,80 em C1/C2 >= 3)."""
    if c1_c2 <= K_TAB_19_2[0][0]:
        return K_TAB_19_2[0][1]
    if c1_c2 >= K_TAB_19_2[-1][0]:
        return K_TAB_19_2[-1][1]
    for (r0, k0), (r1, k1) in zip(K_TAB_19_2, K_TAB_19_2[1:]):
        if r0 <= c1_c2 <= r1:
            return k0 + (k1 - k0) * (c1_c2 - r0) / (r1 - r0)
    return K_TAB_19_2[-1][1]


def tau_rd2(fck):
    """Compressao diagonal do concreto na superficie critica C (19.5.3.1):
    tau_Rd2 = 0,27 * alpha_v * fcd, com alpha_v = (1 - fck/250), fck em MPa."""
    fck_MPa = fck / 1000.0
    return 0.27 * (1.0 - fck_MPa / 250.0) * (fck / 1.4)


def tau_rd1(d, rho, fck, sigma_cp=0.0):
    """Tensao resistente na superficie C' SEM armadura de puncao (19.5.3.2):
    tau_Rd1 = 0,13*(1 + raiz(20/d))*(100*rho*fck)^(1/3) + 0,10*sigma_cp,
    com d em CENTIMETROS na parcela (1 + raiz(20/d)) e fck em MPa.
    rho = raiz(rho_x*rho_y) nas duas direcoes ortogonais."""
    if d <= 0:
        raise ValueError("altura util d deve ser positiva (d=%r)" % (d,))
    d_cm = d * 100.0
    fck_MPa = fck / 1000.0
    base = 0.13 * (1.0 + math.sqrt(20.0 / d_cm)) \
        * (100.0 * max(rho, 0.0) * fck_MPa) ** (1.0 / 3.0) * 1000.0
    return base + 0.10 * sigma_cp


def tau_rd3(d, rho, fck, Asw, fywd, sr, u, alpha_graus=90.0, sigma_cp=0.0):
    """Tensao resistente na superficie C' COM armadura de puncao (19.5.3.3):
    tau_Rd3 = 0,10*(1 + raiz(20/d))*(100*rho*fck)^(1/3) + 0,10*sigma_cp
              + 1,5*(d/s_r)*Asw*fywd*sen(alpha)/(u*d).
    Asw e a area total de UM contorno completo paralelo a C'."""
    d_cm = d * 100.0
    fck_MPa = fck / 1000.0
    concreto = 0.10 * (1.0 + math.sqrt(20.0 / d_cm)) \
        * (100.0 * max(rho, 0.0) * fck_MPa) ** (1.0 / 3.0) * 1000.0
    aco = 0.0
    if Asw > 0 and sr > 0 and u > 0:
        aco = 1.5 * (d / sr) * Asw * fywd * math.sin(math.radians(alpha_graus)) / (u * d)
    return concreto + 0.10 * sigma_cp + aco


def fywd_de_projeto(fyk, tipo="stud"):
    """fywd da armadura de puncao com o TETO de 19.5.3.3 (300 MPa para conector
    tipo pino/stud, 250 MPa para estribo). Devolve tambem 'saturou': se o teto
    cortou o valor, a armadura NAO rende o que fyk/1,15 sugeriria - deixar isso
    calado e exatamente o padrao de saturacao silenciosa."""
    if tipo not in FYWD_LIM:
        raise ValueError("tipo de armadura de puncao invalido: %r (use %s)"
                         % (tipo, sorted(FYWD_LIM)))
    livre = fyk / 1.15
    teto = FYWD_LIM[tipo]
    return {"fywd": min(livre, teto), "teto": teto, "fywd_livre": livre,
            "saturou": livre > teto, "tipo": tipo}


# ---------------------------------------------------------------------------
# 2. GEOMETRIA DOS CONTORNOS CRITICOS (19.5.1 / 19.5.2)
# ---------------------------------------------------------------------------

def contorno(c1, c2, a, tipo="interno", d=None, n_arco=_N_ARCO):
    """Poligonal do contorno afastado de 'a' da face de um pilar retangular
    C1 x C2 (C1 na direcao x, C2 na direcao y; pilar centrado na origem).
    a = 0 da o proprio contorno C (perimetro do pilar); a = 2d da C';
    a = 2d + n*s_r da os contornos intermediarios e C''.

    tipo:
      'interno' - contorno fechado (retangulo dilatado com cantos em arco);
      'borda'   - ha uma borda livre em x = +C1/2 (a face do pilar esta rente a
                  borda). O contorno so existe no lado interno e e INTERROMPIDO
                  perpendicularmente a borda livre a uma distancia da face do
                  pilar igual a min(1,5d ; 0,5*C1) - item 19.5.2.3;
      'canto'   - duas bordas livres (x = +C1/2 e y = +C2/2), cada uma com a
                  mesma interrupcao - item 19.5.2.4.
    A geometria de borda/canto segue o texto do 19.5.2.3/19.5.2.4; a Figura 19.3
    nao esta disponivel em texto no acervo, entao a POSICAO do corte fica
    marcada A CONFIRMAR (o modulo devolve u* e e* explicitos justamente para
    permitir a conferencia)."""
    if c1 <= 0 or c2 <= 0 or a < 0:
        raise ValueError("geometria invalida: c1=%r c2=%r a=%r" % (c1, c2, a))
    if tipo not in ("interno", "borda", "canto"):
        raise ValueError("tipo de pilar invalido: %r" % (tipo,))
    x0, y0 = c1 / 2.0, c2 / 2.0
    pts = []
    if a == 0:
        pts = [(x0, -y0), (x0, y0), (-x0, y0), (-x0, -y0), (x0, -y0)]
    else:
        pts = [(x0 + a, -y0)]
        for cx, cy, ang0 in ((x0, y0, 0.0), (-x0, y0, math.pi / 2),
                             (-x0, -y0, math.pi), (x0, -y0, 3 * math.pi / 2)):
            pts.append((cx + a * math.cos(ang0), cy + a * math.sin(ang0)))
            for k in range(1, n_arco + 1):
                t = ang0 + (math.pi / 2) * k / n_arco
                pts.append((cx + a * math.cos(t), cy + a * math.sin(t)))
    if tipo == "interno":
        return _segmentos(pts, fechado=True)
    corte = min(1.5 * (d if d else a / 2.0), 0.5 * c1)
    lim_x = x0 + corte
    segs = _segmentos(pts, fechado=True)
    segs = [s for s in segs if _meio(s)[0] <= lim_x + 1e-12]
    if tipo == "canto":
        corte_y = min(1.5 * (d if d else a / 2.0), 0.5 * c2)
        lim_y = y0 + corte_y
        segs = [s for s in segs if _meio(s)[1] <= lim_y + 1e-12]
    return segs


def _segmentos(pts, fechado=True):
    seq = list(pts)
    if fechado and seq[0] != seq[-1]:
        seq.append(seq[0])
    return [(seq[i], seq[i + 1]) for i in range(len(seq) - 1)
            if seq[i] != seq[i + 1]]


def _meio(seg):
    (xa, ya), (xb, yb) = seg
    return ((xa + xb) / 2.0, (ya + yb) / 2.0)


def _comp(seg):
    (xa, ya), (xb, yb) = seg
    return math.hypot(xb - xa, yb - ya)


def remove_abertura(segs, abertura, d, dist_max=DIST_ABERTURA):
    """19.5.1: quando ha abertura a menos de 8d do contorno C, o trecho do
    contorno critico entre as duas retas que passam pelo centro do pilar e
    tangenciam os vertices da abertura NAO e considerado.
    abertura: (x_min, x_max, y_min, y_max), no mesmo referencial do pilar."""
    xmin, xmax, ymin, ymax = abertura
    vert = ((xmin, ymin), (xmin, ymax), (xmax, ymin), (xmax, ymax))
    dist = min(math.hypot(x, y) for x, y in vert)
    if dist > dist_max * d:
        return segs, False
    angs = sorted(math.atan2(y, x) for x, y in vert)
    a0, a1 = angs[0], angs[-1]
    if a1 - a0 > math.pi:                       # setor cruzando +-pi
        a0, a1 = a1, a0 + 2 * math.pi

    def dentro(seg):
        x, y = _meio(seg)
        t = math.atan2(y, x)
        if a1 >= a0:
            return a0 - 1e-12 <= t <= a1 + 1e-12
        return t >= a0 - 1e-12 or t <= a1 - 2 * math.pi + 1e-12
    return [s for s in segs if not dentro(s)], True


def _integral_abs(ea, eb, comp):
    """Integral de |e| ao longo de um segmento reto em que e varia linearmente de
    ea a eb. Tomar |e| no ponto MEDIO zera os trechos que cruzam o eixo (foi
    exatamente esse erro que a conferencia contra a formula fechada da norma
    pegou: Wp saia 8% baixo)."""
    if ea * eb >= 0:
        return comp * (abs(ea) + abs(eb)) / 2.0
    return comp * (ea ** 2 + eb ** 2) / (2.0 * abs(eb - ea))


def propriedades(segs):
    """u (perimetro), centroide e modulo plastico Wp = integral |e| dl em cada
    direcao (19.5.2.2), com e medido a partir do CENTROIDE do contorno - o que
    importa nos contornos reduzidos u* de borda e de canto."""
    u = sum(_comp(s) for s in segs)
    if u <= 0:
        return {"u": 0.0, "xc": 0.0, "yc": 0.0, "Wp_x": 0.0, "Wp_y": 0.0}
    xc = sum(_meio(s)[0] * _comp(s) for s in segs) / u
    yc = sum(_meio(s)[1] * _comp(s) for s in segs) / u
    Wp_x = sum(_integral_abs(s[0][0] - xc, s[1][0] - xc, _comp(s)) for s in segs)
    Wp_y = sum(_integral_abs(s[0][1] - yc, s[1][1] - yc, _comp(s)) for s in segs)
    return {"u": u, "xc": xc, "yc": yc, "Wp_x": Wp_x, "Wp_y": Wp_y}


def Wp_interno_formula(c1, c2, d):
    """Formula fechada da norma para o contorno C' de pilar retangular interno:
    Wp = C1^2/2 + C1*C2 + 4*C2*d + 16*d^2 + 2*pi*d*C1 (19.5.2.2). Usada como
    CONFERENCIA da geometria construida (ver tests/test_puncao_nbr6118.py)."""
    return (c1 ** 2 / 2.0 + c1 * c2 + 4.0 * c2 * d + 16.0 * d ** 2
            + 2.0 * math.pi * d * c1)


# ---------------------------------------------------------------------------
# 3. ORQUESTRADOR (19.5 completo)
# ---------------------------------------------------------------------------

def _tensao(F_sd, prop, d, K1, M1, K2=0.0, M2=0.0):
    """tau_Sd = F_Sd/(u*d) + K1*M_Sd1/(Wp1*d) + K2*M_Sd2/(Wp2*d) (19.5.2)."""
    u = prop["u"]
    if u <= 0 or d <= 0:
        return float("inf")
    t = F_sd / (u * d)
    if M1 and prop["Wp_x"] > 0:
        t += K1 * abs(M1) / (prop["Wp_x"] * d)
    if M2 and prop["Wp_y"] > 0:
        t += K2 * abs(M2) / (prop["Wp_y"] * d)
    return t


def verifica_puncao(cfg):
    """Verificacao completa de puncao de uma ligacao laje-pilar (19.5).
    cfg: {
      'tipo'   : 'interno' | 'borda' | 'canto' (posicao do pilar na laje).
      'c1','c2': lados do pilar (m). C1 e o lado PARALELO a excentricidade /
                 PERPENDICULAR a borda livre; C2 o outro.
      'd'      : altura util media da laje (m) = (dx+dy)/2.
      'fck','fyk' : (kN/m2).
      'F_sd'   : forca de puncao de calculo (kN).
      'M_sd_x' : momento de calculo no plano perpendicular a borda livre (kN.m).
      'M_sd_y' : momento no plano paralelo a borda livre (kN.m).
      'rho_x','rho_y' : taxas de armadura de flexao na faixa do pilar + 3d para
                 cada lado (ou 'As_x','As_y' em m2/m, convertidas por As/d).
      'sigma_cp' : tensao normal media de protensao (kN/m2, default 0).
      'armadura' : None ou {'Asw' (m2 por contorno), 'sr' (m), 's0' (m),
                 'tipo' ('stud'|'estribo'), 'alpha_graus', 'n_contornos'}.
      'estabilidade_depende_laje' : bool (19.5.3.5).
      'As_ccp' : soma das areas das barras inferiores que cruzam cada face do
                 pilar (m2), para o colapso progressivo (19.5.4).
      'aberturas' : lista de (x_min, x_max, y_min, y_max) no referencial do pilar.
    }"""
    tipo = cfg.get("tipo", "interno")
    c1, c2 = float(cfg["c1"]), float(cfg["c2"])
    d = float(cfg["d"])
    fck, fyk = cfg["fck"], cfg.get("fyk", 500e3)
    F_sd = float(cfg["F_sd"])
    M1 = float(cfg.get("M_sd_x", 0.0))
    M2 = float(cfg.get("M_sd_y", 0.0))
    sigma_cp = cfg.get("sigma_cp", 0.0)
    if "rho_x" in cfg or "rho_y" in cfg:
        rho_x, rho_y = cfg.get("rho_x", 0.0), cfg.get("rho_y", 0.0)
    else:
        rho_x = cfg.get("As_x", 0.0) / d if d > 0 else 0.0
        rho_y = cfg.get("As_y", 0.0) / d if d > 0 else 0.0
    rho = math.sqrt(max(rho_x, 0.0) * max(rho_y, 0.0))
    avisos = []
    if F_sd <= 0 or d <= 0 or c1 <= 0 or c2 <= 0:
        raise ValueError("entrada degenerada: F_sd=%r d=%r c1=%r c2=%r"
                         % (F_sd, d, c1, c2))
    if rho <= 0:
        avisos.append("rho = 0: sem armadura de flexao declarada, tau_Rd1 vai a zero"
                      " (informe As_x/As_y ou rho_x/rho_y na faixa c + 3d)")

    K1 = K_CIRCULAR if cfg.get("circular") else K_puncao(c1 / c2 if c2 > 0 else 1.0)
    K2 = K_puncao(c2 / (2.0 * c1)) if c1 > 0 else 0.0     # 19.5.2.3-b

    # --- contorno C (perimetro do pilar): compressao diagonal 19.5.3.1 -----
    prop0 = propriedades(contorno(c1, c2, 0.0, tipo, d=d))
    tau_sd0 = _tensao(F_sd, prop0, d, K1, M1, K2, M2)
    t_rd2 = tau_rd2(fck)
    ok_biela = tau_sd0 <= t_rd2 + 1e-9
    if not ok_biela:
        avisos.append("compressao diagonal do concreto esgotada no contorno C"
                      " (19.5.3.1): armadura de puncao NAO resolve, e preciso"
                      " aumentar h, fck ou a secao do pilar")

    # --- contorno C' a 2d (com desconto de aberturas, 19.5.1) --------------
    segs = contorno(c1, c2, 2.0 * d, tipo, d=d)
    aberturas_ativas = 0
    for ab in cfg.get("aberturas", ()):
        segs, cortou = remove_abertura(segs, ab, d)
        aberturas_ativas += 1 if cortou else 0
    if aberturas_ativas:
        avisos.append("%d abertura(s) a menos de %.0fd do contorno C: trecho radial"
                      " descontado de C' (19.5.1)" % (aberturas_ativas, DIST_ABERTURA))
    prop = propriedades(segs)
    e_estrela = math.hypot(prop["xc"], prop["yc"])
    # 19.5.2.3: M_Sd1 = (M_Sd - F_Sd*e*) >= 0 no contorno reduzido
    M1_ef = max(abs(M1) - F_sd * abs(prop["xc"]), 0.0) if tipo != "interno" else abs(M1)
    M2_ef = max(abs(M2) - F_sd * abs(prop["yc"]), 0.0) if tipo == "canto" else abs(M2)
    tau_sd = _tensao(F_sd, prop, d, K1, M1_ef, K2, M2_ef)
    t_rd1 = tau_rd1(d, rho, fck, sigma_cp)
    dispensa_armadura = tau_sd <= t_rd1 + 1e-9

    # --- armadura de puncao (19.5.3.3) e contorno C'' (19.5.3.4) -----------
    arm = cfg.get("armadura")
    res_arm = None
    ok_armadura = True
    ok_c2linha = True
    if arm:
        f = fywd_de_projeto(fyk, arm.get("tipo", "stud"))
        sr = float(arm["sr"])
        s0 = float(arm.get("s0", 0.5 * d))
        n_cont = int(arm.get("n_contornos", 1))
        Asw = float(arm["Asw"])
        alpha = float(arm.get("alpha_graus", 90.0))
        t_rd3 = tau_rd3(d, rho, fck, Asw, f["fywd"], sr, prop["u"], alpha, sigma_cp)
        ok_sr = sr <= SR_MAX_FATOR * d + 1e-9
        ok_s0 = s0 <= S0_MAX_FATOR * d + 1e-9
        if f["saturou"]:
            avisos.append("fywd limitado a %.0f MPa pelo teto de 19.5.3.3 (%s):"
                          " o aco NAO rende fyk/1,15 = %.0f MPa"
                          % (f["teto"] / 1000, f["tipo"], f["fywd_livre"] / 1000))
        if not ok_sr:
            avisos.append("s_r = %.3f m > 0,75d = %.3f m (19.5.3.3)"
                          % (sr, SR_MAX_FATOR * d))
        if not ok_s0:
            avisos.append("1a linha de conectores a %.3f m > 0,5d = %.3f m (20.4)"
                          % (s0, S0_MAX_FATOR * d))
        # C'': 2d alem da ultima linha de armadura, onde volta a valer tau_Rd1
        a_2linha = 2.0 * d + s0 + max(n_cont - 1, 0) * sr + 2.0 * d
        prop2 = propriedades(contorno(c1, c2, a_2linha, tipo, d=d))
        tau_sd2 = _tensao(F_sd, prop2, d, K1, M1_ef, K2, M2_ef)
        ok_c2linha = tau_sd2 <= t_rd1 + 1e-9
        if not ok_c2linha:
            avisos.append("no contorno C'' (2d alem da ultima linha) tau_Sd = %.0f >"
                          " tau_Rd1 = %.0f kN/m2: estenda as linhas de armadura"
                          " (19.5.3.4)" % (tau_sd2, t_rd1))
        ok_armadura = (tau_sd <= t_rd3 + 1e-9) and ok_sr and ok_s0
        res_arm = {"tau_rd3": t_rd3, "fywd": f, "sr": sr, "s0": s0, "Asw": Asw,
                   "n_contornos": n_cont, "u_c2linha": prop2["u"],
                   "tau_sd_c2linha": tau_sd2, "a_c2linha": a_2linha,
                   "ok_sr": ok_sr, "ok_s0": ok_s0, "ok_c2linha": ok_c2linha,
                   "u_arm": tau_sd / t_rd3 if t_rd3 > 0 else float("inf")}
        if tau_sd > t_rd3 + 1e-9:
            avisos.append("tau_Sd = %.0f > tau_Rd3 = %.0f kN/m2: a armadura de"
                          " puncao declarada nao basta (19.5.3.3)" % (tau_sd, t_rd3))
    elif not dispensa_armadura:
        ok_armadura = False
        avisos.append("tau_Sd = %.0f > tau_Rd1 = %.0f kN/m2 e NAO ha armadura de"
                      " puncao declarada (19.5.3.3)" % (tau_sd, t_rd1))

    # --- 19.5.3.5: armadura obrigatoria mesmo com tau_Sd <= tau_Rd1 --------
    # GATE anti-saturacao silenciosa: este requisito NAO aparece como razao
    # tau_Sd/tau_Rd; sem gate proprio a ligacao "passa" sem a armadura exigida.
    exige_19_5_3_5 = bool(cfg.get("estabilidade_depende_laje"))
    ok_19_5_3_5 = True
    equilibrado = 0.0
    if exige_19_5_3_5:
        if arm:
            f = fywd_de_projeto(fyk, arm.get("tipo", "stud"))
            equilibrado = (float(arm["Asw"]) * f["fywd"]
                           * math.sin(math.radians(float(arm.get("alpha_graus", 90.0)))))
        ok_19_5_3_5 = equilibrado >= FRACAO_MIN_19_5_3_5 * F_sd - 1e-9
        if not ok_19_5_3_5:
            avisos.append("19.5.3.5: a estabilidade global depende da laje, entao a"
                          " armadura de puncao e OBRIGATORIA e deve equilibrar >= 50%%"
                          " de F_Sd (%.0f kN); a declarada equilibra %.0f kN"
                          % (FRACAO_MIN_19_5_3_5 * F_sd, equilibrado))

    # --- 19.5.4: colapso progressivo --------------------------------------
    As_ccp = cfg.get("As_ccp")
    fyd = fyk / 1.15
    F_colapso = F_sd * (GF_COLAPSO / 1.4) if cfg.get("usar_gf_1_2") else F_sd
    As_ccp_min = FATOR_COLAPSO * F_colapso / fyd
    ok_colapso = As_ccp is not None and As_ccp >= As_ccp_min - 1e-12
    if not ok_colapso:
        avisos.append("19.5.4 (colapso progressivo): exige fyd*As,ccp >= 1,5*F_Sd,"
                      " ou seja As,ccp >= %.2f cm2 de armadura INFERIOR cruzando"
                      " cada face do pilar, ancorada alem de C'/C''; declarado: %s"
                      % (As_ccp_min * 1e4,
                         "nada" if As_ccp is None else "%.2f cm2" % (As_ccp * 1e4)))

    OK = bool(ok_biela and (dispensa_armadura or ok_armadura) and ok_c2linha
              and ok_19_5_3_5 and ok_colapso)
    return {"tipo": tipo, "c1": c1, "c2": c2, "d": d, "rho": rho, "K1": K1, "K2": K2,
            "F_sd": F_sd, "M_sd_x": M1, "M_sd_y": M2, "M_sd1_efetivo": M1_ef,
            "M_sd2_efetivo": M2_ef, "e_estrela": e_estrela,
            "u0": prop0["u"], "tau_sd_C": tau_sd0, "tau_rd2": t_rd2,
            "u": prop["u"], "Wp_x": prop["Wp_x"], "Wp_y": prop["Wp_y"],
            "tau_sd": tau_sd, "tau_rd1": t_rd1,
            "u_biela": tau_sd0 / t_rd2 if t_rd2 > 0 else float("inf"),
            "u_puncao": tau_sd / t_rd1 if t_rd1 > 0 else float("inf"),
            "dispensa_armadura": dispensa_armadura, "armadura": res_arm,
            "aberturas_ativas": aberturas_ativas,
            "exige_19_5_3_5": exige_19_5_3_5, "ok_19_5_3_5": ok_19_5_3_5,
            "As_ccp_min": As_ccp_min, "As_ccp": As_ccp, "ok_colapso": ok_colapso,
            "ok_biela": ok_biela, "ok_armadura": ok_armadura,
            "avisos": avisos, "OK": OK}


def relatorio_pt(r):
    """Relatorio textual da verificacao de puncao."""
    L = ["PUNCAO DA LIGACAO LAJE-PILAR (NBR 6118 item 19-5)",
         "  Pilar %s %.0f x %.0f cm ; d %.1f cm ; rho %.4f ; F_Sd %.0f kN"
         % (r["tipo"], r["c1"] * 100, r["c2"] * 100, r["d"] * 100, r["rho"],
            r["F_sd"]),
         "  Contorno C  : u0 %.2f m ; tau_Sd %.0f <= tau_Rd2 %.0f kN/m2 (u %.2f) -> %s"
         % (r["u0"], r["tau_sd_C"], r["tau_rd2"], r["u_biela"],
            "ATENDE" if r["ok_biela"] else "REPROVA"),
         "  Contorno C' : u %.2f m ; Wp_x %.3f m2 ; e* %.3f m"
         % (r["u"], r["Wp_x"], r["e_estrela"]),
         "                tau_Sd %.0f x tau_Rd1 %.0f kN/m2 (u %.2f) -> %s"
         % (r["tau_sd"], r["tau_rd1"], r["u_puncao"],
            "dispensa armadura" if r["dispensa_armadura"] else "EXIGE armadura")]
    a = r["armadura"]
    if a:
        L.append("  Armadura    : Asw %.2f cm2/contorno ; s_r %.0f cm ; fywd %.0f MPa"
                 " ; tau_Rd3 %.0f kN/m2 (u %.2f)"
                 % (a["Asw"] * 1e4, a["sr"] * 100, a["fywd"]["fywd"] / 1000,
                    a["tau_rd3"], a["u_arm"]))
        L.append("  Contorno C'': a %.2f m ; tau_Sd %.0f x tau_Rd1 %.0f kN/m2 -> %s"
                 % (a["a_c2linha"], a["tau_sd_c2linha"], r["tau_rd1"],
                    "ATENDE" if a["ok_c2linha"] else "REPROVA"))
    if r["exige_19_5_3_5"]:
        L.append("  19-5-3-5    : armadura obrigatoria (estabilidade depende da laje)"
                 " -> %s" % ("ATENDE" if r["ok_19_5_3_5"] else "REPROVA"))
    L.append("  19-5-4      : As,ccp >= %.2f cm2 (colapso progressivo) -> %s"
             % (r["As_ccp_min"] * 1e4, "ATENDE" if r["ok_colapso"] else "REPROVA"))
    for av in r["avisos"]:
        L.append("  [AVISO] " + av)
    L.append("  RESULTADO: " + ("ATENDE" if r["OK"] else "NAO ATENDE"))
    return _pt("\n".join(L))


def _selftest():
    """Conferencia rapida: geometria contra a formula fechada da norma e os dois
    gates que nao aparecem como razao de tensao (19.5.3.5 e 19.5.4)."""
    c1, c2, d = 0.40, 0.20, 0.15
    pr = propriedades(contorno(c1, c2, 2 * d, "interno"))
    assert abs(pr["u"] - (2 * (c1 + c2) + 4 * math.pi * d)) < 5e-3, pr["u"]
    assert abs(pr["Wp_x"] - Wp_interno_formula(c1, c2, d)) < 5e-3, pr["Wp_x"]
    base = {"tipo": "interno", "c1": 0.40, "c2": 0.40, "d": 0.16, "fck": 30e3,
            "fyk": 500e3, "F_sd": 250.0, "As_x": 12e-4, "As_y": 12e-4,
            "As_ccp": 20e-4}
    r = verifica_puncao(dict(base))
    assert r["OK"] and r["dispensa_armadura"]
    r2 = verifica_puncao(dict(base, estabilidade_depende_laje=True))
    assert r2["dispensa_armadura"] and not r2["OK"]          # 19.5.3.5
    r3 = verifica_puncao(dict(base, As_ccp=1e-4))
    assert r3["dispensa_armadura"] and not r3["OK"]          # 19.5.4
    print("puncao_nbr6118 self-test PASSED")
    print(relatorio_pt(r))


if __name__ == "__main__":
    _selftest()
