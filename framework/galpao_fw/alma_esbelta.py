# ============================================================================
# alma_esbelta.py - Momento fletor resistente de vigas de ALMA ESBELTA.
# NBR 8800:2008 Anexo H. Aplica-se quando o parametro de esbeltez da alma
# lambda = h/tw supera 5,70 sqrt(E/fy) (H.1.2). Substitui o Anexo G (baseado em
# Zx/plastificacao) pelo dimensionamento baseado em Wxc/Wxt + fator kpg.
#
# Base normativa (lida verbatim de pesquisa/aço/nbr8800_2008_1.pdf, pags 147-149 e 136):
#   H.1.2  alma esbelta: lambda = h/tw > 5,70 sqrt(E/fy).
#   H.1.3  validade: Aw/Afc <= 10 ; h/tw <= 260.
#   H.2.1  escoamento da mesa tracionada:  M_Rd = Wxt fy / gamma_a1.
#   H.2.2  FLT:  M_Rd = kpg [.] / gamma_a1 ; lambda = Lb/ryT ;
#          lambda_p = 1,10 sqrt(E/fy) ; lambda_r = pi sqrt(E/(0,7 fy)) ;
#            plato:      kpg Wxc fy
#            inelastico: kpg Cb (1 - 0,3 (lambda-lambda_p)/(lambda_r-lambda_p)) Wxc fy <= plato
#            elastico:   kpg Cb pi^2 E Wxc / lambda^2 <= plato
#          ryT = raio de giracao (eixo fraco) da MESA COMPRIMIDA + 1/3 da ALMA COMPRIMIDA.
#   H.2.3  FLM:  M_Rd = kpg [.] / gamma_a1 ; lambda = bf/(2 tf) ;
#          lambda_p = 0,38 sqrt(E/fy) ; lambda_r = 0,95 sqrt(kc E/(0,7 fy)) ;
#            elastico:   0,90 kpg E kc Wxc / lambda^2.
#   kpg = 1 - ar/(1200 + 300 ar) (hc/tw - 5,70 sqrt(E/fy))  <= 1,0
#          ar = Aw/Afc (<=10) ; hc = 2 x (CG -> face interna da mesa comprimida).
#   F.2   kc = 4 / sqrt(h/tw) , 0,35 <= kc <= 0,76.
#   M_Rd = min(H.2.1, H.2.2, H.2.3).
# Premissa: perfil I duplamente simetrico (mesas iguais) -> Wxc=Wxt=Wx, hc=hw.
# Unidades SI: m, kN (fy em kN/m2).
# ============================================================================
"""Momento resistente de alma esbelta (NBR 8800 Anexo H). Unidades m, kN."""

from __future__ import annotations
import math
import check_nbr8800 as ck

E = ck.E
GA1 = ck.GA1


def _lam_alma(sec):
    h = sec["d"] - 2.0 * sec["tf"]
    return h / sec["tw"]


def e_esbelta(sec, fy):
    """H.1.2 - alma esbelta se h/tw > 5,70 sqrt(E/fy)."""
    return _lam_alma(sec) > 5.70 * math.sqrt(E / fy)


def kc(sec):
    """F.2 - kc = 4/sqrt(h/tw), limitado a [0,35 ; 0,76]."""
    val = 4.0 / math.sqrt(_lam_alma(sec))
    return min(0.76, max(0.35, val))


def kpg(sec, fy):
    """Fator de reducao por flambagem da alma por flexao (Anexo H):
    kpg = 1 - ar/(1200+300 ar)(hc/tw - 5,70 sqrt(E/fy)) <= 1,0.
    ar = Aw/Afc (<=10) ; hc = hw (I duplamente simetrico)."""
    tf, tw, bf = sec["tf"], sec["tw"], sec["bf"]
    hw = sec["d"] - 2.0 * tf
    Aw = hw * tw
    Afc = bf * tf
    ar = min(Aw / Afc, 10.0)                       # limitado a 10 (H.2.2 / H.1.3)
    hc = hw                                         # duplo eixo de simetria
    val = 1.0 - ar / (1200.0 + 300.0 * ar) * (hc / tw - 5.70 * math.sqrt(E / fy))
    return min(val, 1.0)


def ryt(sec):
    """Raio de giracao (eixo fraco) da secao formada pela MESA COMPRIMIDA + 1/3 da
    ALMA COMPRIMIDA (H.2.2). I duplo-simetrico: mesa comprimida = bf x tf; alma
    comprimida = metade superior (hw/2); 1/3 dela = hw/6 de altura de alma."""
    tf, tw, bf = sec["tf"], sec["tw"], sec["bf"]
    hw = sec["d"] - 2.0 * tf
    A_mesa = bf * tf
    A_web13 = (hw / 6.0) * tw                       # 1/3 da alma comprimida (hw/2 /3)
    Iy = tf * bf ** 3 / 12.0 + (hw / 6.0) * tw ** 3 / 12.0
    A = A_mesa + A_web13
    return math.sqrt(Iy / A)


def _valida(sec, a=None):
    """H.1.3 - limites de validade: Aw/Afc <= 10 ; h/tw <= 260.
    O limite 260 de h/tw vale para almas SEM enrijecedores transversais. Com
    enrijecedores no painel (comum no joelho tapered), a NBR 8800 §5.4.3.1.1 admite
    almas mais esbeltas desde que a/h <= 3 (kv = 5 + 5/(a/h)^2 > 5): nesse caso o
    cap de 260 e substituido pelo provimento dos enrijecedores (ver
    enrijecedor_painel.requisitos_enrijecedor). Aw/Afc <= 10 continua valendo.
    a = espacamento dos enrijecedores (m) ou None (sem enrijecedores)."""
    hw = sec["d"] - 2.0 * sec["tf"]
    Aw = hw * sec["tw"]; Afc = sec["bf"] * sec["tf"]
    if a is not None and (a / hw) <= 3.0:
        return Aw / Afc <= 10.0                          # enrijecido: cap 260 dispensado
    return (Aw / Afc <= 10.0) and (_lam_alma(sec) <= 260.0)


def mrd_alma_esbelta(sec, fy, Lb, Cb=1.0, a=None):
    """M_Rd de viga de alma esbelta (Anexo H) = min(H.2.1, H.2.2 FLT, H.2.3 FLM).
    a = espacamento de enrijecedores transversais (m); relaxa o cap h/tw<=260 da
    validade (§5.4.3.1.1). Retorna dict: M_Rd (kN.m), gov, fora_validade, kpg, kc,
    ryT + parcelas."""
    Wx = sec["Wx"]
    kp = kpg(sec, fy)
    rE = math.sqrt(E / fy)
    plato = kp * Wx * fy                             # teto comum (kpg Wxc fy)

    # H.2.1 - escoamento da mesa tracionada
    M_esc = Wx * fy

    # H.2.2 - FLT
    lam_t = Lb / ryt(sec)
    lamp_t = 1.10 * rE
    lamr_t = math.pi * math.sqrt(E / (0.7 * fy))
    if lam_t <= lamp_t:
        M_flt = plato
    elif lam_t <= lamr_t:
        M_flt = min(kp * Cb * (1.0 - 0.3 * (lam_t - lamp_t) / (lamr_t - lamp_t)) * Wx * fy,
                    plato)
    else:
        M_flt = min(kp * Cb * math.pi ** 2 * E * Wx / lam_t ** 2, plato)

    # H.2.3 - FLM (mesa comprimida)
    kcf = kc(sec)
    lam_m = (sec["bf"] / 2.0) / sec["tf"]
    lamp_m = 0.38 * rE
    lamr_m = 0.95 * math.sqrt(kcf * E / (0.7 * fy))
    if lam_m <= lamp_m:
        M_flm = plato
    elif lam_m <= lamr_m:
        M_flm = kp * (1.0 - 0.3 * (lam_m - lamp_m) / (lamr_m - lamp_m)) * Wx * fy
    else:
        M_flm = 0.90 * kp * E * kcf * Wx / lam_m ** 2

    Mn = min(M_esc, M_flt, M_flm)
    gov = {M_esc: "escoamento_mesa", M_flt: "FLT", M_flm: "FLM"}[Mn]
    return {"M_Rd": Mn / GA1, "Mn": Mn, "gov": gov,
            "fora_validade": not _valida(sec, a),
            "kpg": kp, "kc": kcf, "ryT": ryt(sec),
            "M_esc": M_esc, "M_flt": M_flt, "M_flm": M_flm, "anexo": "H"}


def _selftest():
    import alma_variavel as av
    s = av.props_I(0.90, 0.25, 0.003, 0.016)        # alma esbelta
    assert e_esbelta(s, 250e3)
    assert 0.35 <= kc(s) <= 0.76
    kp = kpg(s, 250e3)
    assert 0.0 < kp <= 1.0
    r = mrd_alma_esbelta(s, 250e3, Lb=2.0, Cb=1.0)
    teto = s["Wx"] * 250e3 / GA1
    assert 0 < r["M_Rd"] < teto                      # reduzido por kpg/FLT/FLM
    assert r["gov"] in ("FLT", "FLM", "escoamento_mesa")
    # secao compacta NAO e esbelta
    assert not e_esbelta(av.props_I(0.40, 0.20, 0.010, 0.0125), 250e3)
    # fora de validade: Aw/Afc > 10
    s2 = av.props_I(1.20, 0.08, 0.006, 0.006)
    assert mrd_alma_esbelta(s2, 250e3, 2.0)["fora_validade"]
    print("alma_esbelta self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
