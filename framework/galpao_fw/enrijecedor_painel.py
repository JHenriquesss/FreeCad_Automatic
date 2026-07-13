# ============================================================================
# enrijecedor_painel.py - Enrijecedores transversais da ALMA (painel do joelho).
# NBR 8800:2008 §5.4.3.1. A alma esbelta do joelho de portico tapered pode ter a
# forca cortante resistente AUMENTADA por enrijecedores transversais espacados de
# "a": o coeficiente de flambagem por cisalhamento sobe de kv=5 (sem enrijecedores)
# para kv = 5 + 5/(a/h)^2, elevando lambda_p / lambda_r e portanto V_Rd.
#
# Base normativa (lida verbatim de pesquisa/aço/nbr8800_2008_1.pdf, pags 59-60):
#   §5.4.3.1.1  V_Rd em 3 dominios de lambda = h/tw:
#       lambda <= lambda_p:      V_Rd = Vpl / gamma_a1
#       lambda_p < l <= lambda_r:V_Rd = (lambda_p/lambda) Vpl / gamma_a1
#       lambda > lambda_r:       V_Rd = 1,24 (lambda_p/lambda)^2 Vpl / gamma_a1
#     lambda_p = 1,10 sqrt(kv E/fy) ; lambda_r = 1,37 sqrt(kv E/fy)
#     kv = 5,0                          para almas SEM enrijecedores transversais,
#                                       para a/h > 3 ou a/h > [260/(h/tw)]^2
#     kv = 5 + 5/(a/h)^2                para todos os outros casos
#   §5.4.3.1.2  Vpl = 0,60 Aw fy ; Aw = d tw (altura TOTAL d).
#   §5.4.3.1.3  requisitos do enrijecedor (quando necessario):
#     a) soldado a alma e mesas; interrupcao do lado tracionado entre 4tw e 6tw;
#     b) (largura/espessura) do enrijecedor <= 0,56 sqrt(E/fy);
#     c) I_st >= a tw^3 j , com j = [2,5/(a/h)^2] - 2 >= 0,5 ; I_st = inercia da
#        secao de um enrijecedor singelo (ou par, um de cada lado) em relacao ao
#        eixo no plano medio da alma.
#   h = distancia entre faces internas das mesas (perfil soldado) = d - 2 tf.
# Premissa: perfil I soldado duplamente simetrico. Unidades SI: m, kN (fy kN/m2).
# ============================================================================
"""Enrijecedores transversais da alma (NBR 8800 §5.4.3.1). Unidades m, kN."""

from __future__ import annotations
import math
import check_nbr8800 as ck

E = ck.E
GA1 = ck.GA1


def _h(sec):
    """Altura da alma (perfil soldado) = d - 2 tf (faces internas das mesas)."""
    return sec["d"] - 2.0 * sec["tf"]


def kv(sec, a):
    """§5.4.3.1.1 - coeficiente de flambagem por cisalhamento.
    a = espacamento entre enrijecedores transversais adjacentes (m); a=None => sem
    enrijecedores. kv=5,0 se sem enrijecedores OU a/h>3 OU a/h>[260/(h/tw)]^2;
    caso contrario kv = 5 + 5/(a/h)^2 (>5)."""
    h = _h(sec); tw = sec["tw"]
    if a is None:
        return 5.0
    a_h = a / h
    lim = (260.0 / (h / tw)) ** 2
    if a_h > 3.0 or a_h > lim:
        return 5.0
    return 5.0 + 5.0 / a_h ** 2


def vpl(sec, fy):
    """§5.4.3.1.2 - Vpl = 0,60 Aw fy ; Aw = d tw (altura TOTAL da secao)."""
    return 0.60 * sec["d"] * sec["tw"] * fy


def vrd(sec, fy, a=None):
    """§5.4.3.1.1 - forca cortante resistente de calculo V_Rd com kv por a/h.
    a=None => kv=5 (identico ao cortante de check_nbr8800). Retorna dict com V_Rd,
    kv, lambda/lambda_p/lambda_r e o dominio governante."""
    kvv = kv(sec, a)
    lam = _h(sec) / sec["tw"]
    lamp = 1.10 * math.sqrt(kvv * E / fy)
    lamr = 1.37 * math.sqrt(kvv * E / fy)
    Vpl = vpl(sec, fy)
    if lam <= lamp:
        Vn = Vpl; dom = "plastificacao"
    elif lam <= lamr:
        Vn = (lamp / lam) * Vpl; dom = "inelastica"
    else:
        Vn = 1.24 * (lamp / lam) ** 2 * Vpl; dom = "elastica"
    return {"Vrd": Vn / GA1, "Vn": Vn, "Vpl": Vpl, "kv": kvv,
            "lam": lam, "lamp": lamp, "lamr": lamr, "dominio": dom, "a": a}


def j_rigidez(a_h):
    """§5.4.3.1.3c - fator de rigidez j = [2,5/(a/h)^2] - 2 >= 0,5."""
    return max(2.5 / a_h ** 2 - 2.0, 0.5)


def ist_req(sec, a):
    """§5.4.3.1.3c - inercia minima do enrijecedor: I_st >= a tw^3 j (m^4)."""
    return a * sec["tw"] ** 3 * j_rigidez(a / _h(sec))


def ist_par(sec, b_st, t_st):
    """Inercia de um PAR de enrijecedores (um de cada lado da alma), retangulos de
    largura b_st e espessura t_st, em relacao ao eixo no plano medio da alma. O par
    equivale a uma chapa de largura (2 b_st + tw) e espessura t_st: I = t_st (2 b_st
    + tw)^3 / 12. Conservador (nao credita a alma)."""
    return t_st * (2.0 * b_st + sec["tw"]) ** 3 / 12.0


def requisitos_enrijecedor(sec, a, fy, b_st, t_st, Ist=None):
    """§5.4.3.1.3 - verifica os requisitos do enrijecedor transversal.
      (a) faixa de interrupcao da solda: 4tw a 6tw (informativo);
      (b) b/t do enrijecedor <= 0,56 sqrt(E/fy);
      (c) I_st fornecido (ou estimado como par) >= a tw^3 j.
    Retorna dict com utilizacoes e OK global."""
    tw = sec["tw"]
    bt = b_st / t_st
    bt_lim = 0.56 * math.sqrt(E / fy)
    Ist_val = Ist if Ist is not None else ist_par(sec, b_st, t_st)
    Ireq = ist_req(sec, a)
    return {"bt": bt, "bt_lim": bt_lim, "bt_ok": bt <= bt_lim,
            "j": j_rigidez(a / _h(sec)), "Ist": Ist_val, "Ist_req": Ireq,
            "u_ist": Ireq / Ist_val if Ist_val > 0 else float("inf"),
            "Ist_ok": Ist_val >= Ireq,
            "solda_min": 4.0 * tw, "solda_max": 6.0 * tw,
            "OK": (bt <= bt_lim) and (Ist_val >= Ireq)}


def a_min_para_vsd(sec, fy, Vsd, a_lo=0.05, a_hi=None, tol=1e-4):
    """Menor espacamento a (mais enrijecedores) que faz V_Rd(a) >= Vsd, se possivel.
    Retorna a (m) ou None se nem a->0 atende (busca por bisseccao decrescente).
    V_Rd cresce quando a diminui (kv sobe). a_hi default = 3 h (limite a/h<=3)."""
    h = _h(sec)
    if a_hi is None:
        a_hi = 3.0 * h
    if vrd(sec, fy, a_lo)["Vrd"] < Vsd:
        return None                                    # nem no espacamento minimo
    if vrd(sec, fy, a_hi)["Vrd"] >= Vsd:
        return a_hi                                    # ja atende com a maximo
    lo, hi = a_lo, a_hi
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if vrd(sec, fy, mid)["Vrd"] >= Vsd:
            lo = mid
        else:
            hi = mid
    return lo


def _selftest():
    import alma_variavel as av
    fy = 250e3
    s = av.props_I(0.95, 0.25, 0.004, 0.016)           # alma esbelta (h/tw ~ 230)
    assert kv(s, None) == 5.0                           # sem enrijecedor
    h = _h(s)
    assert abs(kv(s, a=h) - 10.0) < 1e-9                # a/h=1 -> 5+5=10
    assert kv(s, a=4.0 * h) == 5.0                      # a/h>3 -> 5
    # V_Rd sobe com enrijecedores (kv maior) em alma esbelta
    v0 = vrd(s, fy, None)["Vrd"]
    v1 = vrd(s, fy, a=h)["Vrd"]
    assert v1 > v0 > 0, "enrijecedores devem elevar V_Rd na alma esbelta"
    # a=None reproduz kv=5 do check_nbr8800
    assert abs(vrd(s, fy, None)["kv"] - 5.0) < 1e-12
    # j: a/h=1 -> 0,5 ; a/h pequeno -> cresce
    assert abs(j_rigidez(1.0) - 0.5) < 1e-9
    assert j_rigidez(0.5) > 0.5
    # requisitos: b/t e I_st
    r = requisitos_enrijecedor(s, a=h, fy=fy, b_st=0.075, t_st=0.008)
    assert r["bt_ok"] and r["Ist_ok"] and r["OK"]
    r_bad = requisitos_enrijecedor(s, a=h, fy=fy, b_st=0.10, t_st=0.004)  # b/t alto
    assert not r_bad["bt_ok"] and not r_bad["OK"]
    # a_min_para_vsd: alvo entre v0 e o V_Rd de a pequeno
    alvo = 0.5 * (v0 + vrd(s, fy, 0.05)["Vrd"])
    a_ok = a_min_para_vsd(s, fy, alvo)
    assert a_ok is not None and vrd(s, fy, a_ok)["Vrd"] >= alvo * 0.999
    print("enrijecedor_painel self-test PASSED "
          f"(kv(a=h)={kv(s, h):.1f}, V_Rd {v0:.0f}->{v1:.0f} kN)")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
