# ============================================================================
# premoldado_nbr9062.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Fecha o gap "pre-moldado" do vertical de concreto: as verificacoes que a NBR
# 6118 nao cobre e que a NBR 9062:2017 exige de um galpao PRE-MOLDADO de verdade:
#   (A) LIGACAO PILAR-FUNDACAO por CALICE (colarinho): comprimento de embutimento
#       (Tabela 15), forca horizontal na parede frontal Hsfd (modelo de Leonhardt
#       modificado por El Debs, 7.7.3.1 / Figura 26), forca normal de fundo Nbd,
#       verificacao da compressao na parede (<= 0,4 fcd, 7.7.3.6) e as armaduras
#       horizontal/vertical do colarinho. gamma_n = 1,2 (7.7.1.2, sistema de
#       pilares engastados e vigas articuladas - exatamente o nosso galpao).
#   (B) SITUACOES TRANSITORIAS (5.3.2): saque da forma, manuseio, transporte,
#       icamento e montagem. Carga estatica equivalente g_eq,d = gamma_f*beta_a*gk
#       (gamma_f = 1,30 ; beta_a tabelado em 5.3.2.2). Verificacao do icamento do
#       PILAR pre-moldado (momento de peso proprio nos pontos de pega, tensao na
#       armadura longitudinal <= 0,50 fyk, obrigatorio por 5.3.2.2).
#   (C) RESISTENCIA DO CONCRETO NA IDADE DO SAQUE fckj (NBR 6118 12.3.3):
#       fckj = beta1*fck, beta1 = exp{s[1-(28/t)^0.5]}.
# TODOS os coeficientes lidos da NBR 9062:2017 / NBR 6118:2014 no NotebookLM
# (nao de memoria). Unidades: m, kN ; fck/fyk em kN/m2.
# ============================================================================
"""Verificacoes de concreto PRE-MOLDADO da NBR 9062:2017: calice de fundacao
(colarinho), situacoes transitorias (icamento/transporte/montagem) e fckj."""

from __future__ import annotations

import math

# --- coeficientes de ponderacao (NBR 6118) ---------------------------------
GAMMA_C = 1.4
GAMMA_S = 1.15

# --- NBR 9062:2017 ----------------------------------------------------------
GAMMA_F_TRANS = 1.30       # coef. de ponderacao de acoes, analise transitoria (5.3.2.1)
GAMMA_N_CALICE = 1.20      # ajustamento p/ colarinho, pilar engastado+viga artic. (7.7.1.2)
MU_LISA = 0.30             # atrito max, interface lisa (7.7.3.2)
MU_RUGOSA = 0.60           # atrito max, interface rugosa (7.7.3.2)
LEMB_MIN = 0.40            # embutimento minimo absoluto (7.7.2.4)
ESP_PAREDE_MIN = 0.15      # espessura minima da parede do colarinho (7.7.5.1)
ESP_FUNDO_MIN = 0.20       # espessura minima do fundo sob o pilar (7.7.5.1)

# beta_a minimos (5.3.2.2) - coeficiente de amplificacao dinamica
BETA_A = {
    "saque": 1.3, "manuseio": 1.3, "montagem": 1.3,   # 1,4 em circunstancias desfavoraveis
    "transporte": 1.3,                                  # 0,8 se p.proprio em situacao favoravel
    "icamento_pilar": 1.3,                              # obrig. limitar sigma_s a 0,50 fyk
    "dispositivo": 3.0,                                 # projeto das alcas/ancoragens de icamento
}
BETA_A_DESFAVORAVEL = 1.4  # saque/manuseio/montagem sob circunstancias desfavoraveis
BETA_A_TRANSP_FAVOR = 0.8  # transporte com carga permanente em situacao favoravel
SIGMA_S_ICAMENTO = 0.50    # tensao da armadura longitudinal limitada a 0,50 fyk (5.3.2.2)

# fator "s" do cimento p/ evolucao da resistencia (NBR 6118 12.3.3)
S_CIMENTO = {"CPIII": 0.38, "CPIV": 0.38, "CPI": 0.25, "CPII": 0.25, "CPV": 0.20, "CPV-ARI": 0.20}


# ---------------------------------------------------------------- (C) fckj
def fckj_idade(fck, t_dias, cimento="CPII"):
    """Resistencia caracteristica do concreto na idade t (NBR 6118 12.3.3):
    fckj = beta1*fck, beta1 = exp{s[1 - (28/t)^0.5]}. fck em kN/m2, t em dias."""
    s = S_CIMENTO.get(str(cimento).upper(), 0.25)
    if t_dias >= 28:
        return fck
    beta1 = math.exp(s * (1.0 - math.sqrt(28.0 / t_dias)))
    return beta1 * fck


def _fctm(fck):
    """Resistencia media a tracao (NBR 6118 8.2.5). fck em kN/m2 -> retorna kN/m2."""
    fck_MPa = fck / 1000.0
    if fck_MPa <= 50.0:
        fctm_MPa = 0.3 * fck_MPa ** (2.0 / 3.0)
    else:
        fctm_MPa = 2.12 * math.log(1.0 + 0.11 * fck_MPa)
    return fctm_MPa * 1000.0


# ------------------------------------------------------- (A) CALICE / COLARINHO
def embutimento(Nd, Md, h, interface="rugosa", tracao=False):
    """Comprimento minimo de embutimento do pilar no calice (Tabela 15, 7.7.2).
    h = dimensao do pilar // ao plano do momento (m). interface: 'lisa'|'rugosa'|'chaves'.
    Interpola linearmente a relacao Md/(Nd*h) entre 0,15 e 2,0. >= 40 cm (7.7.2.4).
    Pilar tracionado (7.7.2.2): Lemb = 2,0h e interface nao pode ser lisa."""
    if tracao:
        if interface == "lisa":
            raise ValueError("NBR 9062 7.7.2.2: pilar tracionado nao admite interface lisa")
        return max(2.0 * h, LEMB_MIN)
    r = abs(Md) / (Nd * h) if Nd > 0 else 2.0
    if interface == "chaves":
        lo, hi = 1.2, 1.6
    else:                                   # lisa ou rugosa
        lo, hi = 1.5, 2.0
    if r <= 0.15:
        k = lo
    elif r >= 2.0:
        k = hi
    else:
        k = lo + (hi - lo) * (r - 0.15) / (2.0 - 0.15)
    return max(k * h, LEMB_MIN)


def _mu(interface):
    return {"lisa": MU_LISA, "rugosa": MU_RUGOSA}.get(interface, 0.0)


def forca_horizontal_calice(Nd, Md, Vd, h, Lemb, interface="rugosa"):
    """Forca horizontal solicitante Hsfd na parede frontal do colarinho e forca
    normal de fundo Nbd - modelo de Leonhardt modificado por El Debs (NBR 9062
    7.7.3.1, Figura 26). Interfaces lisas/rugosas. Grande excentricidade usa a
    resultante a 0,1*Lemb do topo/fundo (braco 0,8*Lemb); pequena (Md/(Nd h)<=0,15)
    usa a = Lemb/6 e enb = 0. mu por 7.7.3.2. Retorna (Hsfd, Nbd)."""
    mu = _mu(interface)
    r = abs(Md) / (Nd * h) if Nd > 0 else 2.0
    if r <= 0.15:                            # pequena excentricidade (7.7.3.3)
        a = Lemb / 6.0
        enb = 0.0
    else:                                    # grande excentricidade (7.7.3.1)
        a = 0.10 * Lemb
        enb = 0.25 * h
    y = (a - 0.75 * mu * h) / (1.0 + mu * mu)
    braco = (Lemb - 2.0 * a) + mu * h
    Hsfd = (abs(Md) - Nd * (enb + mu * y) + abs(Vd) * (Lemb - y)) / braco
    Nbd = (Nd - mu * abs(Vd)) / (1.0 + mu * mu)
    return Hsfd, Nbd


def dimensiona_calice(caso):
    """Dimensiona o calice de fundacao (colarinho) de um pilar pre-moldado.
    caso: {
      'Nd','Md','Vd' : esforcos de calculo na base do pilar (kN, kN.m).
      'h'  : dimensao do pilar // ao momento (m).  'b' : dimensao perpendicular (m).
      'fck': do MENOR entre bloco/pilar/graute (kN/m2). 'fyk': aco do colarinho.
      'interface' : 'lisa'|'rugosa'|'chaves' (default 'rugosa').
      'esp_parede' : espessura da parede (m, default 0,15). 'aplicar_gamma_n' (default True).
    }
    Aplica gamma_n = 1,2 (7.7.1.2). Verifica compressao <= 0,4 fcd (7.7.3.6) numa
    faixa de 0,2*Lemb pela largura do pilar. Devolve embutimento, Hsfd, Nbd,
    tensao/compressao, armaduras e OK."""
    Nd = caso["Nd"]; Md = caso["Md"]; Vd = caso.get("Vd", 0.0)
    h = caso["h"]; b = caso["b"]
    fck = caso.get("fck", 30e3); fyk = caso.get("fyk", 500e3)
    interface = caso.get("interface", "rugosa")
    esp_parede = caso.get("esp_parede", ESP_PAREDE_MIN)
    gn = GAMMA_N_CALICE if caso.get("aplicar_gamma_n", True) else 1.0

    # esforcos majorados pelo ajustamento do colarinho (7.7.1.2)
    Ndc, Mdc, Vdc = Nd * gn, Md * gn, Vd * gn

    Lemb = embutimento(Ndc, Mdc, h, interface, tracao=caso.get("tracao", False))
    fcd = fck / GAMMA_C
    fyd = fyk / GAMMA_S

    if interface == "chaves":
        # 7.7.4: transferencia por chaves. Momento na base do colarinho e o alivio
        # da normal no fundo (0,2 Nd). Armadura vertical por flexo-compressao.
        Mbd = Mdc + abs(Vdc) * Lemb
        N_base = 0.2 * Ndc
        Hsfd = Nbd = None
        # armadura vertical do colarinho (secao vazada) - simplificacao pelo braco 0,8h_col
        As_v = Mbd / (0.85 * h * fyd) * 1e4     # cm2 (aprox., z ~ 0,85 h)
        As_h = As_v * 0.5                         # secundaria (>= 0,5 principal)
        sigma_c = N_base / (0.2 * Lemb * b)
        comp_ok = sigma_c <= 0.4 * fcd
        return {"interface": interface, "Lemb": round(Lemb, 3), "Mbd": round(Mbd, 1),
                "N_base": round(N_base, 1), "sigma_c_kN_m2": round(sigma_c, 1),
                "lim_comp": round(0.4 * fcd, 1), "compressao_ok": comp_ok,
                "As_vertical_cm2": round(As_v, 2), "As_horizontal_cm2": round(As_h, 2),
                "esp_parede": esp_parede, "esp_parede_ok": esp_parede >= ESP_PAREDE_MIN,
                "gamma_n": gn, "OK": comp_ok and esp_parede >= ESP_PAREDE_MIN and Lemb <= 1.80}

    # interfaces lisas ou rugosas (7.7.3)
    Hsfd, Nbd = forca_horizontal_calice(Ndc, Mdc, Vdc, h, Lemb, interface)
    # compressao na parede frontal: Hsfd numa faixa de 0,2 Lemb pela largura b (7.7.3.6)
    sigma_c = Hsfd / (0.2 * Lemb * b)
    comp_ok = sigma_c <= 0.4 * fcd
    # armaduras (7.7.3.5 / Figura 27): horizontal resiste Hsfd (topo); vertical
    # suspende a mesma resultante ate a fundacao (modelo El Debs, conservador).
    As_h = Hsfd / fyd * 1e4                       # cm2 (horizontal principal, no topo)
    As_v = Hsfd / fyd * 1e4                       # cm2 (vertical principal, paredes long.)
    Lemb_ok = Lemb <= 1.80                         # > 1,80 m exige estudo especial (7.7.2.5)
    parede_ok = esp_parede >= ESP_PAREDE_MIN
    return {"interface": interface, "Lemb": round(Lemb, 3), "Hsfd": round(Hsfd, 1),
            "Nbd": round(Nbd, 1), "sigma_c_kN_m2": round(sigma_c, 1),
            "lim_comp": round(0.4 * fcd, 1), "compressao_ok": comp_ok,
            "As_horizontal_cm2": round(As_h, 2), "As_vertical_cm2": round(As_v, 2),
            "esp_parede": esp_parede, "esp_parede_ok": parede_ok, "gamma_n": gn,
            "OK": comp_ok and parede_ok and Lemb_ok}


# --------------------------------------------- (B) SITUACOES TRANSITORIAS 5.3.2
def beta_a(situacao, desfavoravel=False, favoravel=False):
    """Coeficiente de amplificacao dinamica minimo (5.3.2.2)."""
    if situacao in ("saque", "manuseio", "montagem") and desfavoravel:
        return BETA_A_DESFAVORAVEL
    if situacao == "transporte" and favoravel:
        return BETA_A_TRANSP_FAVOR
    if situacao not in BETA_A:
        raise ValueError(f"situacao transitoria desconhecida: {situacao}")
    return BETA_A[situacao]


def carga_equivalente(gk, situacao, desfavoravel=False, favoravel=False):
    """Carga estatica equivalente de calculo g_eq,d = gamma_f*beta_a*gk (5.3.2.1).
    gamma_f = 1,30. Retorna (g_eq_d, beta_a_usado)."""
    ba = beta_a(situacao, desfavoravel, favoravel)
    return GAMMA_F_TRANS * ba * gk, ba


def _momento_icamento(q, L, a):
    """Momento maximo (valor absoluto) de uma barra sob peso proprio q (kN/m),
    comprimento L, icada em 2 pontos simetricos a distancia 'a' de cada ponta
    (viga biapoiada com 2 balancos). Retorna (M_apoio, M_vao, M_max)."""
    vao = L - 2.0 * a
    M_apoio = q * a * a / 2.0                       # momento negativo sobre a pega
    M_vao = q * vao * vao / 8.0 - M_apoio           # momento positivo no meio
    return M_apoio, M_vao, max(M_apoio, abs(M_vao))


def a_otimo_icamento(L):
    """Distancia de pega que iguala momento de apoio e de vao (minimiza |M|):
    a = (sqrt(2)-1)/... ~ 0,207 L (2 balancos simetricos, viga sob peso proprio)."""
    return (math.sqrt(2.0) - 1.0) / 2.0 * L         # ~0,2071 L


def verifica_icamento_pilar(caso):
    """Verifica o ICAMENTO de um pilar pre-moldado (peso proprio, 2 pontos de pega).
    Momento de calculo com gamma_f*beta_a (icamento_pilar, beta_a=1,3), tensao na
    armadura longitudinal limitada a 0,50 fyk (5.3.2.2, OBRIGATORIO). Resistencia
    do concreto na idade do saque (fckj). caso: {
      'L': comprimento do pilar (m). 'b','h': secao (m). 'As': armadura long. TRACIONADA (cm2).
      'fck': (kN/m2). 'fyk'. 't_dias' (idade do saque, default 3). 'cimento' (default 'CPV').
      'a_pega' (m, default a_otimo). 'dl' (cobrimento+.., m, default 0,04).
    }"""
    L = caso["L"]; b = caso["b"]; h = caso["h"]
    As = caso["As"] * 1e-4                          # cm2 -> m2
    fck = caso.get("fck", 30e3); fyk = caso.get("fyk", 500e3)
    t = caso.get("t_dias", 3); cim = caso.get("cimento", "CPV")
    dl = caso.get("dl", 0.04)
    a = caso.get("a_pega", a_otimo_icamento(L))
    GAMMA_CONC = 25.0                               # kN/m3

    gk = GAMMA_CONC * b * h                         # peso proprio (kN/m)
    q_eq, ba = carga_equivalente(gk, "icamento_pilar")
    _, _, Mk_max = _momento_icamento(gk, L, a)
    Md = q_eq / gk * Mk_max                         # aplica gamma_f*beta_a ao momento

    d = h - dl                                       # altura util (flexao no plano de h)
    fckj = fckj_idade(fck, t, cim)
    # momento resistente com tensao do aco limitada a 0,50 fyk (z ~ 0,9 d, conservador)
    sigma_lim = SIGMA_S_ICAMENTO * fyk
    Mr_05 = As * sigma_lim * 0.9 * d                # kN.m
    # fissuracao do concreto na idade (informativo): Mr,fiss = fctm,j * W
    W = b * h * h / 6.0
    Mr_fiss = _fctm(fckj) * W
    ok = Md <= Mr_05
    return {"gk_kN_m": round(gk, 2), "beta_a": ba, "a_pega": round(a, 3),
            "a_otimo": round(a_otimo_icamento(L), 3), "Md_kN_m": round(Md, 2),
            "Mr_0.5fyk_kN_m": round(Mr_05, 2), "sigma_s_util": round(Md / Mr_05, 2) if Mr_05 else None,
            "fckj_MPa": round(fckj / 1000.0, 1), "t_dias": t,
            "Mr_fissuracao_kN_m": round(Mr_fiss, 2), "fissura": Md > Mr_fiss, "OK": ok}


def relatorio_pt(cal, ica=None):
    L = ["LIGACAO PILAR-FUNDACAO POR CALICE (NBR 9062:2017 7.7)",
         f"  Interface: {cal['interface']} ; embutimento Lemb = {cal['Lemb']:.3f} m ; "
         f"gamma_n = {cal['gamma_n']:.2f}"]
    if cal["interface"] == "chaves":
        L.append(f"  Mbd = {cal['Mbd']:.1f} kN.m ; N_base = {cal['N_base']:.1f} kN "
                 f"(alivio 0,2 Nd)")
    else:
        L.append(f"  Hsfd = {cal['Hsfd']:.1f} kN ; Nbd = {cal['Nbd']:.1f} kN")
    L.append(f"  Compressao parede: {cal['sigma_c_kN_m2']:.0f} <= {cal['lim_comp']:.0f} kN/m2 "
             f"(0,4 fcd) -> {'OK' if cal['compressao_ok'] else 'REPROVA'}")
    L.append(f"  Armaduras: horizontal {cal['As_horizontal_cm2']:.2f} cm2 ; "
             f"vertical {cal['As_vertical_cm2']:.2f} cm2")
    L.append(f"  CALICE -> {'ATENDE' if cal['OK'] else 'REPROVA'}")
    if ica:
        L += ["SITUACAO TRANSITORIA - ICAMENTO DO PILAR (NBR 9062 5.3.2)",
              f"  Peso proprio {ica['gk_kN_m']:.2f} kN/m ; beta_a = {ica['beta_a']:.1f} ; "
              f"pega a {ica['a_pega']:.2f} m das pontas (otimo {ica['a_otimo']:.2f} m)",
              f"  Md = {ica['Md_kN_m']:.1f} kN.m <= Mr(0,5 fyk) = {ica['Mr_0.5fyk_kN_m']:.1f} kN.m "
              f"-> {'OK' if ica['OK'] else 'REPROVA'} (fckj = {ica['fckj_MPa']:.1f} MPa aos {ica['t_dias']} d)"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # calice de um pilar 40x40 sob N=800 kN e M=200 kN.m (grande excentricidade)
    cal = dimensiona_calice({"Nd": 800.0, "Md": 200.0, "Vd": 40.0, "h": 0.40, "b": 0.40,
                             "fck": 30e3, "fyk": 500e3, "interface": "rugosa"})
    assert cal["Lemb"] >= 0.40
    # grande excentricidade (M/(N h) = 200/(800*0,4) = 0,625 -> interpola p/ ~1,74h).
    # gamma_n majora Md e Nd juntos -> a relacao r nao muda, so o Lemb final (round 3).
    assert abs(cal["Lemb"] - round(embutimento(800, 200, 0.40, "rugosa"), 3)) < 1e-6
    assert cal["Hsfd"] > 0
    assert "OK" in cal
    # embutimento: limites exatos da Tabela 15
    assert abs(embutimento(1000, 10, 0.4, "rugosa") - 1.5 * 0.4) < 1e-9      # r<=0,15 -> 1,5h
    assert abs(embutimento(1000, 1000, 0.4, "rugosa") - 2.0 * 0.4) < 1e-9    # r>=2 -> 2,0h
    assert abs(embutimento(1000, 10, 0.4, "chaves") - 1.2 * 0.4) < 1e-9      # chaves -> 1,2h
    assert abs(embutimento(100, 1000, 0.2, "lisa") - LEMB_MIN) < 1e-9         # piso 40 cm
    # situacoes transitorias: beta_a e gamma_f exatos (5.3.2)
    assert beta_a("montagem") == 1.3 and beta_a("montagem", desfavoravel=True) == 1.4
    assert beta_a("transporte", favoravel=True) == 0.8
    assert beta_a("dispositivo") == 3.0
    g, ba = carga_equivalente(10.0, "icamento_pilar")
    assert abs(g - 1.30 * 1.3 * 10.0) < 1e-9 and ba == 1.3
    # fckj: aos 28 d = fck ; mais novo, menor
    assert abs(fckj_idade(30e3, 28) - 30e3) < 1e-6
    assert fckj_idade(30e3, 3, "CPV") < 30e3
    # icamento de um pilar 40x40, 8 m
    ica = verifica_icamento_pilar({"L": 8.0, "b": 0.40, "h": 0.40, "As": 12.0,
                                   "fck": 30e3, "fyk": 500e3, "t_dias": 3})
    assert ica["Md_kN_m"] > 0 and "OK" in ica
    assert abs(ica["a_otimo"] - 0.2071 * 8.0) < 0.01
    print("premoldado_nbr9062 self-test PASSED")
    print(relatorio_pt(cal, ica))


if __name__ == "__main__":
    _selftest()
