# ============================================================================
# forcas_localizadas.py - MESAS E ALMAS DE PERFIS I/H SOB FORCAS TRANSVERSAIS
# LOCALIZADAS + ENRIJECEDOR DE APOIO (NBR 8800:2008 Secao 5.7).
# METODO extraido VERBATIM do PDF (pesquisa/aco/nbr8800_2008_1.pdf, pgs 57-62,
# lidas do texto e das imagens das equacoes - zero-erro-de-metodo). Estados-limite:
#   5.7.2 Flexao local da mesa          F_Rd = 6,25 tf^2 fy / ga1
#   5.7.3 Escoamento local da alma      1,10 (5k+ln) fy tw / ga1  (int.)
#                                       1,10 (2,5k+ln) fy tw / ga1 (extremidade)
#   5.7.4 Enrugamento da alma           0,66/0,33 tw^2 [...] sqrt(E fy tf/tw) / ga1
#   5.7.5 Flambagem lateral da alma     Cr tw^3 tf/(ga1 h^2)[0,94+0,37 (.)^3]
#   5.7.6 Flambagem da alma (compressao) 24 tw^3 sqrt(E fy)/(h ga1)
#   5.7.8 Apoios sem restricao a rotacao -> exige enrijecedor transversal
#   5.7.9 Projeto do enrijecedor (5.7.9.4 barra comprimida Lb=0,75h, secao =
#         enrijecedores + faixa de alma 12tw extremidade / 25tw interna;
#         5.7.9.5 largura b_st+tw/2 >= b_ref/3 ; t_st >= tf/2 e >= b_st/15).
# Unidades SI: m, kN. F_Rd = forca resistente de calculo (kN).
# ============================================================================
"""Forcas transversais localizadas e enrijecedor de apoio (NBR 8800 5.7). m, kN."""

from __future__ import annotations
import math
import check_nbr8800 as ck
import enrijecedor_painel as enp

E = ck.E
GA1 = ck.GA1


def _h(sec):
    """Distancia entre faces internas das mesas (perfil soldado) = d - 2 tf."""
    return sec["d"] - 2.0 * sec["tf"]


# ----- 5.7.2 Flexao local da mesa -------------------------------------------
def flexao_local_mesa(sec, fy, l_carga=None, dist_extremidade=None):
    """5.7.2.2: F_Rd = 6,25 tf^2 fy / ga1. Nao precisa verificar se o comprimento
    de atuacao (perpendicular a barra) < 0,15 bf (5.7.2.1). Reduz a metade se a
    forca atua a menos de 10 tf da extremidade (5.7.2.3). Retorna dict."""
    tf, bf = sec["tf"], sec["bf"]
    if l_carga is not None and l_carga < 0.15 * bf:
        return {"F_Rd": None, "aplica": False, "motivo": "l_carga<0,15 bf (5.7.2.1)"}
    F_Rd = 6.25 * tf ** 2 * fy / GA1
    if dist_extremidade is not None and dist_extremidade < 10.0 * tf:
        F_Rd *= 0.5                                     # 5.7.2.3
    return {"F_Rd": F_Rd, "aplica": True}


# ----- 5.7.3 Escoamento local da alma ---------------------------------------
def escoamento_local_alma(sec, fy, ln, k, na_extremidade=False):
    """5.7.3.2: F_Rd = 1,10 (5k+ln) fy tw / ga1 (dist>d, interior) ou
    1,10 (2,5k+ln) fy tw / ga1 (dist<=d, extremidade). ln = comprimento de atuacao
    longitudinal; k = tf + perna do filete (soldado) ou tf + raio (laminado)."""
    tw = sec["tw"]
    c = 2.5 if na_extremidade else 5.0
    F_Rd = 1.10 * (c * k + ln) * fy * tw / GA1
    return {"F_Rd": F_Rd, "aplica": True, "ramo": "extremidade" if na_extremidade
            else "interior"}


# ----- 5.7.4 Enrugamento da alma --------------------------------------------
def enrugamento_alma(sec, fy, ln, na_extremidade=False):
    """5.7.4.2. Compressao na mesa. (a) dist>=d/2 (interior): 0,66; (b) dist<d/2
    (extremidade): 0,33, com dois sub-ramos por ln/d. sqrt(E fy tf/tw)."""
    tw, tf, d = sec["tw"], sec["tf"], sec["d"]
    raiz = math.sqrt(E * fy * tf / tw)
    r = (tw / tf) ** 1.5
    ld = ln / d
    if not na_extremidade:                              # (a) dist >= d/2
        col = 0.66 * tw ** 2 / GA1 * (1.0 + 3.0 * ld * r) * raiz
        ramo = "a (>=d/2)"
    else:                                               # (b) dist < d/2
        if ld <= 0.2:
            col = 0.33 * tw ** 2 / GA1 * (1.0 + 3.0 * ld * r) * raiz
            ramo = "b (<d/2, ln/d<=0,2)"
        else:
            col = 0.33 * tw ** 2 / GA1 * (1.0 + (4.0 * ld - 0.2) * r) * raiz
            ramo = "b (<d/2, ln/d>0,2)"
    return {"F_Rd": col, "aplica": True, "ramo": ramo}


# ----- 5.7.5 Flambagem lateral da alma --------------------------------------
def flambagem_lateral_alma(sec, fy, Lb, Msd, Mr, rot_impedida=True):
    """5.7.5.2. So se o deslocamento lateral relativo entre mesas nao esta impedido
    no ponto da forca (5.7.5.1). Cr=32E se Msd<Mr, 16E se Msd>=Mr. (a) rotacao
    impedida, (h/tw)/(l/bf)<=2,30: [0,94+0,37(.)^3]; (b) rotacao livre,
    ...<=1,70: [0,37(.)^3]. Acima do limite (5.7.5.3): nao ocorre -> aplica=False."""
    tw, tf, bf = sec["tw"], sec["tf"], sec["bf"]
    h = _h(sec)
    razao = (h / tw) / (Lb / bf)
    lim = 2.30 if rot_impedida else 1.70
    if razao > lim:
        return {"F_Rd": None, "aplica": False, "motivo": f"(h/tw)/(l/bf)={razao:.2f}"
                f">{lim} (5.7.5.3): nao ocorre"}
    Cr = 32.0 * E if Msd < Mr else 16.0 * E
    base = Cr * tw ** 3 * tf / (GA1 * h ** 2)
    bracket = (0.94 + 0.37 * razao ** 3) if rot_impedida else (0.37 * razao ** 3)
    return {"F_Rd": base * bracket, "aplica": True, "Cr": Cr, "razao": razao}


# ----- 5.7.6 Flambagem da alma por compressao (par de forcas) ----------------
def flambagem_alma_compressao(sec, fy, na_extremidade=False):
    """5.7.6.2: par de forcas opostas nas duas mesas. F_Rd = 24 tw^3 sqrt(E fy)/
    (h ga1). Reduz a metade se o par esta a menos de d/2 da extremidade (5.7.6.3)."""
    tw = sec["tw"]; h = _h(sec)
    F_Rd = 24.0 * tw ** 3 * math.sqrt(E * fy) / (h * GA1)
    if na_extremidade:
        F_Rd *= 0.5
    return {"F_Rd": F_Rd, "aplica": True}


# ----- 5.7.9 Enrijecedor de apoio (barra comprimida) ------------------------
def checa_geometria_enrijecedor(sec, b_st, t_st, b_ref=None):
    """5.7.9.5: (a) b_st + tw/2 >= b_ref/3 ; (b) t_st >= tf/2 e t_st >= b_st/15.
    b_ref = largura da mesa/chapa que recebe a forca (default = bf da barra)."""
    tw, tf, bf = sec["tw"], sec["tf"], sec["bf"]
    b_ref = bf if b_ref is None else b_ref
    ok_a = (b_st + tw / 2.0) >= b_ref / 3.0
    ok_b1 = t_st >= tf / 2.0
    ok_b2 = t_st >= b_st / 15.0
    return {"ok": ok_a and ok_b1 and ok_b2, "ok_largura": ok_a,
            "ok_espessura_mesa": ok_b1, "ok_espessura_largura": ok_b2,
            "b_min_a": b_ref / 3.0 - tw / 2.0, "t_min_b": max(tf / 2.0, b_st / 15.0)}


def enrijecedor_apoio(sec, fy, b_st, t_st, n_st=2, extremidade=True, F_sd=None,
                      b_ref=None):
    """5.7.9.4: enrijecedor de apoio dimensionado como BARRA COMPRIMIDA (5.3),
    flambagem por flexao em eixo no PLANO MEDIO DA ALMA. Secao = enrijecedores +
    faixa de alma 12tw (extremidade) ou 25tw (interna). Lb = 0,75 h.
    Retorna N_Rd (kN), esbeltez, chi, geometria e (se F_sd dado) atende."""
    tw = sec["tw"]; h = _h(sec)
    geo = checa_geometria_enrijecedor(sec, b_st, t_st, b_ref)
    faixa = (12.0 if extremidade else 25.0) * tw        # 5.7.9.4
    A_eff = n_st * b_st * t_st + faixa * tw
    # inercia do par de enrijecedores no plano medio da alma (= ist_par, 6.13)
    I = enp.ist_par(sec, b_st, t_st) if n_st == 2 else t_st * (b_st + tw / 2.0) ** 3 / 3.0
    r = math.sqrt(I / A_eff)
    KL = 0.75 * h                                       # 5.7.9.4
    Ne = math.pi ** 2 * E * I / KL ** 2                 # carga critica de Euler
    lam0 = math.sqrt(A_eff * fy / Ne)                   # Q=1 (enrijecedor robusto)
    chi = ck.chi_compressao(lam0)
    N_Rd = chi * A_eff * fy / GA1
    out = {"N_Rd": N_Rd, "A_eff": A_eff, "I": I, "r": r, "Lb": KL,
           "lambda0": lam0, "chi": chi, "faixa_alma": faixa, "geometria": geo}
    if F_sd is not None:
        out["F_sd"] = F_sd
        out["atende"] = N_Rd >= F_sd
    return out


def dimensiona_enrijecedor_apoio(sec, fy, F_sd, extremidade=True, b_ref=None,
                                 t_lista=None):
    """Menor enrijecedor de apoio (b_st, t_st) que atende F_sd E a geometria
    5.7.9.5. Varre chapas comerciais. Retorna o dict de enrijecedor_apoio + escolha."""
    tw, tf, bf = sec["tw"], sec["tf"], sec["bf"]
    t_lista = t_lista or [0.00635, 0.008, 0.0095, 0.0125, 0.016, 0.019, 0.0222, 0.025]
    b_ref = bf if b_ref is None else b_ref
    b_min = max(b_ref / 3.0 - tw / 2.0, 0.0)            # 5.7.9.5a
    for t_st in t_lista:
        # largura minima que satisfaz 5.7.9.5a e b (b_st<=15 t_st)
        b0 = max(b_min, tf / 2.0 * 0.0)                 # (a) domina a largura minima
        for b_st in [round(b0 + 0.005 * i, 4) for i in range(0, 40)]:
            if b_st < b_min or b_st > 15.0 * t_st or t_st < tf / 2.0:
                continue
            if b_st > (bf - tw) / 2.0 + 1e-9:           # nao ultrapassa a mesa
                break
            res = enrijecedor_apoio(sec, fy, b_st, t_st, extremidade=extremidade,
                                    F_sd=F_sd, b_ref=b_ref)
            if res["geometria"]["ok"] and res["atende"]:
                res["escolha"] = {"b_st": b_st, "t_st": t_st}
                return res
    return {"N_Rd": None, "atende": False, "escolha": None,
            "motivo": "nenhuma chapa da lista atende F_sd + geometria"}


# ----- Agregador: reacao de apoio -------------------------------------------
def reacao_apoio(sec, fy, F_sd, ln, k, desloc_lateral_impedido=True,
                 Msd=0.0, Mr=None, Lb=None, rot_impedida=True):
    """Verifica a reacao de apoio F_sd contra os estados-limite aplicaveis a uma
    EXTREMIDADE de viga: escoamento local da alma (5.7.3, ramo extremidade),
    enrugamento (5.7.4, ramo extremidade), e - se o deslocamento lateral NAO estiver
    impedido - flambagem lateral da alma (5.7.5). Retorna dict com cada F_Rd, o
    MENOR governante e se precisa de enrijecedor de apoio (5.7.8/5.7.9)."""
    esc = escoamento_local_alma(sec, fy, ln, k, na_extremidade=True)
    enr = enrugamento_alma(sec, fy, ln, na_extremidade=True)
    estados = {"escoamento_alma": esc["F_Rd"], "enrugamento_alma": enr["F_Rd"]}
    if not desloc_lateral_impedido and Lb is not None and Mr is not None:
        fla = flambagem_lateral_alma(sec, fy, Lb, Msd, Mr, rot_impedida)
        if fla["aplica"]:
            estados["flambagem_lateral_alma"] = fla["F_Rd"]
    gov = min(estados, key=lambda kk: estados[kk])
    F_Rd_min = estados[gov]
    return {"estados": estados, "governa": gov, "F_Rd_min": F_Rd_min, "F_sd": F_sd,
            "atende": F_sd <= F_Rd_min, "precisa_enrijecedor": F_sd > F_Rd_min}


def _selftest():
    import alma_variavel as av
    sec = av.props_I(0.60, 0.25, 0.008, 0.016)
    fy = 345e3
    assert flexao_local_mesa(sec, fy)["F_Rd"] > 0
    # extremidade < interior (escoamento e enrugamento)
    esc_i = escoamento_local_alma(sec, fy, 0.10, 0.02, False)["F_Rd"]
    esc_e = escoamento_local_alma(sec, fy, 0.10, 0.02, True)["F_Rd"]
    assert esc_e < esc_i
    enr_i = enrugamento_alma(sec, fy, 0.10, False)["F_Rd"]
    enr_e = enrugamento_alma(sec, fy, 0.10, True)["F_Rd"]
    assert enr_e < enr_i
    # flambagem por compressao reduz a metade na extremidade
    fc = flambagem_alma_compressao(sec, fy, False)["F_Rd"]
    assert abs(flambagem_alma_compressao(sec, fy, True)["F_Rd"] - fc / 2.0) < 1e-6
    # enrijecedor de apoio: N_Rd cresce com b_st
    n1 = enrijecedor_apoio(sec, fy, 0.10, 0.0125)["N_Rd"]
    n2 = enrijecedor_apoio(sec, fy, 0.06, 0.0125)["N_Rd"]
    assert n1 > n2 > 0
    # dimensionamento acha uma chapa
    F_sd = reacao_apoio(sec, fy, 800.0, 0.10, 0.02)["F_Rd_min"] * 1.5
    dim = dimensiona_enrijecedor_apoio(sec, fy, F_sd)
    assert dim["atende"] and dim["escolha"], "deveria achar enrijecedor"
    print(f"forcas_localizadas self-test PASSED (esc_e={esc_e:.0f} enr_e={enr_e:.0f} "
          f"fc={fc:.0f} kN; enrij b={dim['escolha']['b_st']*1000:.0f} "
          f"t={dim['escolha']['t_st']*1000:.1f} N_Rd={dim['N_Rd']:.0f} kN)")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
