# ============================================================================
# tensao_ponto.py - Verificacao por TENSOES da teoria da elasticidade.
# NBR 8800:2008 secao 5.5.2.3 (pag 57): "Secoes quaisquer submetidas a momento de
# torcao, forca axial, momentos fletores e forcas cortantes". A tensao resistente
# de calculo deve ser >= a solicitante, com sigma e tau da teoria da elasticidade.
# Aplica-se ao JOELHO tapered de alma esbelta, onde M e V picam juntos e a
# interacao no ponto (juncao mesa-alma) pode governar - o que as checagens
# separadas de flexao (5.4/Anexo G/H) e cortante (5.4.3) nao capturam.
#
# Base normativa (lida verbatim de pesquisa/aço/nbr8800_2008_1.pdf, pag 57):
#   5.5.2.3  A tensao resistente de calculo para os ELU a seguir deve ser >=
#            a solicitante, expressa em sigma_Sd ou tau_Sd (teoria da elasticidade):
#     a) escoamento sob tensao normal:        sigma_Sd <= fy / gama_a1
#     b) escoamento sob cisalhamento:          tau_Sd  <= 0,60 fy / gama_a1
#     c) instabilidade sob tensao normal:      sigma_Sd <= chi   fy / gama_a1
#     d) instabilidade sob cisalhamento:       tau_Sd  <= 0,60 chi fy / gama_a1
#   (chi = fator de reducao 5.3.3; para a) e c) chi_n com lambda0=sqrt(fy/sigma_e);
#    para b) e d) chi_v com lambda0=sqrt(0,60 fy/tau_e). Aqui chi_n, chi_v sao
#    INPUT - o consumidor passa a esbeltez ao cisalhamento da alma esbelta.)
#
# NOTA - von Mises: sqrt(sigma^2 + 3 tau^2) <= fy/gama_a1 NAO e equacao explicita
# da NBR 8800; entra como check SUPLEMENTAR conservador (teoria da elasticidade,
# criterio de energia de distorcao). Sempre >= max(sigma, sqrt(3) tau) e
# <= sigma + sqrt(3) tau. Sinalizado em base_vm.
#
# Pontos avaliados (I duplo-simetrico):
#   - fibra extrema (y = d/2):  sigma = N/A + M/Wx ; tau ~ 0.
#   - juncao mesa-alma (y = d/2 - tf): sigma = N/A + M (d/2-tf)/Ix ;
#     tau = V Qf/(Ix tw), Qf = bf tf (d-tf)/2 (momento estatico da mesa).
#   A juncao concentra sigma alto E tau alto -> ponto critico para 5.5.2.3.
# Unidades SI: m, kN (fy em kN/m2, tensao em kN/m2).
# ============================================================================
"""Verificacao por tensoes NBR 8800 5.5.2.3 (juncao mesa-alma). Unidades m, kN."""

from __future__ import annotations
import math
import check_nbr8800 as ck

GA1 = ck.GA1
SQRT3 = math.sqrt(3.0)


def sigma_tau(sec, Nsd, Msd, Vsd):
    """Tensoes normais/cisalhantes (teoria da elasticidade) na fibra extrema e na
    juncao mesa-alma. Retorna dict {'fibra':{...}, 'juncao':{...}}.
    Convencao: sinais absolutos irrelevantes p/ os ELU (checa modulo)."""
    A, Ix, Wx, tw, d, bf, tf = (sec["A"], sec["Ix"], sec["Wx"], sec["tw"],
                                sec["d"], sec["bf"], sec["tf"])
    # fibra extrema
    sig_fibra = Nsd / A + Msd / Wx
    # juncao mesa-alma
    yj = d / 2.0 - tf
    sig_j = Nsd / A + Msd * yj / Ix
    Qf = bf * tf * (d - tf) / 2.0                  # momento estatico da mesa
    tau_j = Vsd * Qf / (Ix * tw)
    return {"fibra": {"sigma": sig_fibra, "tau": 0.0},
            "juncao": {"sigma": sig_j, "tau": tau_j, "Qf": Qf}}


def von_mises(sigma, tau):
    """Tensao equivalente de von Mises: sqrt(sigma^2 + 3 tau^2)."""
    return math.sqrt(sigma ** 2 + 3.0 * tau ** 2)


def verifica_5523(sec, fy, Nsd, Msd, Vsd, chi_n=1.0, chi_v=1.0):
    """Verificacao por tensoes 5.5.2.3 no ponto critico (juncao mesa-alma).
    Aplica a)-d) SEPARADOS + von Mises suplementar. chi_n/chi_v = fatores de
    reducao (5.3.3) por instabilidade normal/cisalhamento (INPUT).
    Retorna utilizacoes u_* (>1 reprova), governante e OK global."""
    st = sigma_tau(sec, Nsd, Msd, Vsd)
    # ponto critico para a interacao = juncao (sigma alto + tau alto).
    # a fibra extrema (tau=0) ja e coberta por a)/c) com o sigma maior; toma-se o
    # sigma da fibra para a) e c) (maior tensao normal) e o tau da juncao para b)/d).
    sig = max(abs(st["fibra"]["sigma"]), abs(st["juncao"]["sigma"]))
    tau = abs(st["juncao"]["tau"])
    sig_j = abs(st["juncao"]["sigma"])              # sigma no MESMO ponto do tau

    lim_a = fy / GA1                                 # a) escoamento normal
    lim_b = 0.60 * fy / GA1                          # b) escoamento cisalhamento
    lim_c = chi_n * fy / GA1                         # c) instabilidade normal
    lim_d = 0.60 * chi_v * fy / GA1                  # d) instabilidade cisalhamento
    lim_vm = fy / GA1                                # von Mises (suplementar)

    u_sigma_a = sig / lim_a
    u_tau_b = tau / lim_b
    u_sigma_c = sig / lim_c
    u_tau_d = tau / lim_d
    # von Mises avaliado no ponto critico (juncao: sigma_j + tau_j juntos)
    vm = von_mises(sig_j, tau)
    u_vm = vm / lim_vm

    us = {"a_sigma": u_sigma_a, "b_tau": u_tau_b, "c_sigma": u_sigma_c,
          "d_tau": u_tau_d, "vm": u_vm}
    gov = max(us, key=us.get)
    OK = all(u <= 1.0 for u in us.values())
    return {"u_sigma_a": u_sigma_a, "u_tau_b": u_tau_b, "u_sigma_c": u_sigma_c,
            "u_tau_d": u_tau_d, "u_vm": u_vm, "vm": vm, "sigma": sig_j, "tau": tau,
            "gov": gov, "OK": OK,
            "base_vm": "suplementar (teoria da elasticidade / energia de "
                       "distorcao); NAO e equacao explicita da NBR 8800 5.5.2.3"}


def _selftest():
    import alma_variavel as av
    s = av.props_I(0.90, 0.25, 0.003, 0.016)         # alma esbelta
    st = sigma_tau(s, 200.0, 300.0, 150.0)
    assert st["fibra"]["tau"] == 0.0
    assert st["juncao"]["tau"] > 0.0
    # von Mises no envelope
    sig = abs(st["juncao"]["sigma"]); tau = abs(st["juncao"]["tau"])
    vm = von_mises(sig, tau)
    assert max(sig, SQRT3 * tau) - 1e-9 <= vm <= sig + SQRT3 * tau + 1e-9
    r = verifica_5523(s, 250e3, 200.0, 300.0, 150.0, chi_v=0.7)
    assert set(("u_sigma_a", "u_tau_b", "u_sigma_c", "u_tau_d", "u_vm")) <= set(r)
    # d) mais severa que b) quando chi_v<1
    r2 = verifica_5523(s, 250e3, 0.0, 0.0, 150.0, chi_v=0.6)
    assert r2["u_tau_d"] > r2["u_tau_b"]
    # sigma isolado reprova
    r3 = verifica_5523(s, 250e3, 0.0, 2.0 * s["Wx"] * 250e3, 0.0)
    assert r3["u_sigma_a"] > 1.0 and not r3["OK"]
    print("tensao_ponto self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
