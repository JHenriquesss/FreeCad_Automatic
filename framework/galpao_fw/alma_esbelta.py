# ============================================================================
# alma_esbelta.py - Momento fletor resistente de vigas de ALMA ESBELTA.
# NBR 8800:2024/Er1:2025, Anexo E (na edicao de 2008 era o Anexo H). Aplica-se
# quando o parametro de esbeltez da alma lambda = h/tw supera 5,70 sqrt(E/fy).
# Substitui o Anexo D (baseado em Zx/plastificacao) pelo dimensionamento
# baseado em Wxc/Wxt + fator kpg.
#
# Base normativa (paginas 148 a 150 da edicao de 2024, lidas na imagem pelo
# MCP_Fontes em 2026-10-13, D231; a extracao de texto numera as secoes do
# anexo como E.5/E.6 - os numeros abaixo sao os da extracao):
#   E.5.2  alma esbelta: lambda = h/tw > 5,70 sqrt(E/fy).
#   E.5.3 b) h/tw nao pode exceder 260 nem 11,7 sqrt(E/fy) (a/h <= 1,5) nem
#          0,42 E/fy (a/h > 1,5; e' o caso da alma sem enrijecedor).
#   E.6.1  escoamento da mesa tracionada:  M_Rd = Wxt fy / gamma_a1.
#   E.6.2  FLT:  lambda = Lb/ryc ; lambda_y = 1,10 sqrt(E/fy) ;
#          lambda_r = pi sqrt(E Cb/(fy - sigma_r)) ; My = kpg fy Wxc ;
#          Mr = kpg (fy - sigma_r) Wxc ; Mcr = Cb kpg pi^2 E Wxc / lambda^2 ;
#            lambda <= lambda_y:  My
#            ate' lambda_r:       My - (My - Mr)(lambda-lambda_y)/(lambda_r-lambda_y)
#            acima:               Mcr
#          Cb DENTRO de lambda_r e de Mcr; a reta nao leva Cb (a edicao de 2008
#          multiplicava o trecho inelastico por Cb, com lambda_r sem Cb).
#          ryc = raio de giracao (eixo fraco) da MESA COMPRIMIDA + 1/3 da ALMA COMPRIMIDA.
#   E.6.3  FLM:  lambda = bf/(2 tf) ; lambda_y = 0,38 sqrt(E/fy) ;
#          lambda_r = 0,95 sqrt(kc E/(fy - sigma_r)) ;
#            elastico:   0,90 kpg E kc Wxc / lambda^2.
#   kpg = 1 - ar/(1200 + 300 ar) (hc/tw - 5,70 sqrt(E/fy))  <= 1,0
#          ar = hc tw/Afc (<=10) ; hc = 2 x (CG -> face interna da mesa comprimida).
#   kc = 4 / sqrt(h/tw) , 0,35 <= kc <= 0,76 (Tabela 4, nota a; conferida na
#   imagem da pagina 47 no D232).
#   sigma_r = 0,3 fy (D.2.8-e).
#   M_Rd = min(E.6.1, E.6.2, E.6.3).
# Premissa: perfil I duplamente simetrico (mesas iguais) -> Wxc=Wxt=Wx, hc=hw.
# Unidades SI: m, kN (fy em kN/m2).
# ============================================================================
"""Momento resistente de alma esbelta (NBR 8800:2024 Anexo E). Unidades m, kN."""

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
    """NBR 8800:2024, Tabela 4, nota a: kc = 4/raiz(h/tw), com 0,35 <= kc <= 0,76."""
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


def limite_esbeltez_alma(sec, fy, a=None):
    """NBR 8800:2024, E.5.3 b): h/tw nao pode exceder 260 nem 11,7 sqrt(E/fy)
    (a/h <= 1,5) nem 0,42 E/fy (a/h > 1,5). `a` = espacamento dos enrijecedores
    transversais (m); None = sem enrijecedor (a/h > 1,5)."""
    hw = sec["d"] - 2.0 * sec["tf"]
    if a is not None and (a / hw) <= 1.5:
        return min(260.0, 11.7 * math.sqrt(E / fy))
    return min(260.0, 0.42 * E / fy)


def _valida(sec, a=None, fy=None):
    """Limites de validade do Anexo E: hc tw/Afc <= 10 e h/tw dentro de E.5.3 b)
    (`limite_esbeltez_alma`). Enrijecedor transversal NAO dispensa o teto de 260:
    a norma diz "nao pode exceder 260 nem ..." (ate' o D231 o motor dispensava o
    260 quando a/h <= 3). Sem `fy` so' o 260 e' conferido."""
    hw = sec["d"] - 2.0 * sec["tf"]
    Aw = hw * sec["tw"]; Afc = sec["bf"] * sec["tf"]
    teto = 260.0 if fy is None else limite_esbeltez_alma(sec, fy, a)
    return (Aw / Afc <= 10.0) and (_lam_alma(sec) <= teto)


def mrd_alma_esbelta(sec, fy, Lb, Cb=1.0, a=None):
    """M_Rd de viga de alma esbelta (NBR 8800:2024, Anexo E) = min(escoamento
    da mesa tracionada, FLT, FLM).

    a = espacamento de enrijecedores transversais (m); muda o teto de h/tw de
    E.5.3 b). Retorna dict: M_Rd (kN.m), gov, fora_validade, kpg, kc, ryT + parcelas."""
    Wx = sec["Wx"]
    kp = kpg(sec, fy)
    rE = math.sqrt(E / fy)
    plato = kp * Wx * fy                             # teto comum (kpg Wxc fy)

    # E.6.1 - escoamento da mesa tracionada
    M_esc = Wx * fy
    # E.6.2 - FLT: Cb em lambda_r e em Mcr; a reta do trecho inelastico nao leva Cb
    lam_t = Lb / ryt(sec)
    lamp_t = 1.10 * rE
    lamr_t = max(math.pi * math.sqrt(E * Cb / (0.7 * fy)), lamp_t)
    if lam_t <= lamp_t:
        M_flt = plato
    elif lam_t <= lamr_t:
        M_flt = kp * (1.0 - 0.3 * (lam_t - lamp_t) / (lamr_t - lamp_t)) * Wx * fy
    else:
        M_flt = min(kp * Cb * math.pi ** 2 * E * Wx / lam_t ** 2, plato)
    # E.6.3 - FLM (mesa comprimida)
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
            "fora_validade": not _valida(sec, a, fy),
            "kpg": kp, "kc": kcf, "ryT": ryt(sec),
            "M_esc": M_esc, "M_flt": M_flt, "M_flm": M_flm, "anexo": "E"}


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
