# ============================================================================
# zona_painel.py - ZONA DE PAINEL do no rigido viga-coluna (joelho).
# NBR 8800:2008. Verifica o painel de alma do PILAR num no rigido e os estados
# locais sob as mesas da viga, decidindo chapa de reforco (doubler) e/ou
# enrijecedores transversais.
#
# Base normativa (lida verbatim de pesquisa/aço/nbr8800_2008_1.pdf):
#   5.7.7.1  Cisalhamento do painel de alma. Chapa de reforco/enrijecedor diagonal
#            exigidos quando FSd (forca cortante transmitida pelas mesas da viga)
#            exceder F_Rd:
#              - N_Sd <= 0,4 Npl :  F_Rd = V_Rd
#              - N_Sd >  0,4 Npl :  F_Rd = V_Rd (1,4 - N_Sd/Npl)
#            V_Rd = cortante resistente do painel (5.4.3, Aw = dc*tw do pilar);
#            Npl = Ag fy (escoamento da secao do pilar).
#   5.4.3.1.2  Vpl = 0,60 fy Aw ;  Aw = d tw.
#   5.7.2.2  Flexao local da mesa:  F_Rd = 6,25 tf^2 fy / gamma_a1.
#   5.7.3.2  Escoamento local da alma:
#              interior (dist > d):  F_Rd = 1,10 (5k + ln) fy tw / gamma_a1
#              extremidade (<= d) :  F_Rd = 1,10 (2,5k + ln) fy tw / gamma_a1
#            k = tf da mesa carregada + raio/perna de solda ; ln = compr. de atuacao.
#   5.7.6.2  Flambagem da alma por compressao (par de forcas opostas nas 2 mesas):
#              F_Rd = 24 tw^3 sqrt(E fy) / (h gamma_a1).
#            5.7.6.3: se o par estiver a menos de d/2 da extremidade -> metade.
#   5.7.7.2  Doubler: chapas nos DOIS lados da alma, dimensionadas por 5.4 para
#            absorver a parcela da cortante; estende +150 mm alem do painel.
#
# Demanda FSd = M_Sd / dm (binario das mesas da viga; dm = d_viga - tf_viga,
# centro-a-centro das mesas) - MECANICA (Bellei, Edificios Industriais em Aco),
# nao coeficiente de norma.
# Unidades SI: m, kN (fy em kN/m2).
# ============================================================================
"""Zona de painel do joelho (NBR 8800 5.7). Unidades m, kN."""

from __future__ import annotations
import math
import check_nbr8800 as ck

GA1 = ck.GA1
E = ck.E


def forca_das_mesas(M_Sd, d_viga, tf_viga):
    """FSd transmitida pelas mesas da viga ao painel = binario M/dm, com
    dm = d_viga - tf_viga (distancia entre centros geometricos das mesas)."""
    dm = max(d_viga - tf_viga, 1e-6)
    return abs(M_Sd) / dm


def _Vrd_painel(dc, tw_col, fy):
    """Cortante resistente do painel de alma do pilar (5.4.3.1.2 + 5.4.3.1.1).
    Aw = dc*tw. Aplica a reducao por esbeltez da alma (kv=5,0 sem enrijecedores)."""
    Aw = dc * tw_col
    Vpl = 0.6 * fy * Aw
    # esbeltez da alma (5.4.3.1.1) com kv=5,0 (painel sem enrijecedores transversais)
    kv = 5.0
    lam = dc / tw_col
    lam_p = 1.10 * math.sqrt(kv * E / fy)
    lam_r = 1.37 * math.sqrt(kv * E / fy)
    if lam <= lam_p:
        Vn = Vpl
    elif lam <= lam_r:
        Vn = Vpl * (lam_p / lam)
    else:
        Vn = Vpl * 1.24 * (lam_p / lam) ** 2
    return Vn / GA1, Vpl


def cisalhamento_painel(caso):
    """5.7.7.1 - cisalhamento do painel de alma do pilar no no rigido.
    caso: M_Sd, N_Sd (axial no pilar), dc, tw_col, Ag_col, d_viga, tf_viga, fy.
    Retorna FSd, V_Rd, F_Rd, Npl, u_painel, reduz_axial."""
    fy = caso["fy"]
    FSd = forca_das_mesas(caso["M_Sd"], caso["d_viga"], caso["tf_viga"])
    V_Rd, Vpl = _Vrd_painel(caso["dc"], caso["tw_col"], fy)
    Npl = caso["Ag_col"] * fy
    N_Sd = abs(caso.get("N_Sd", 0.0))
    reduz = N_Sd > 0.4 * Npl
    F_Rd = V_Rd * (1.4 - N_Sd / Npl) if reduz else V_Rd
    F_Rd = max(F_Rd, 0.0)
    return {"FSd": FSd, "V_Rd": V_Rd, "Vpl": Vpl, "Npl": Npl, "N_Sd": N_Sd,
            "F_Rd": F_Rd, "reduz_axial": reduz,
            "u_painel": FSd / F_Rd if F_Rd > 0 else float("inf")}


def dimensiona_doubler(FSd, F_Rd, dc, fy):
    """5.7.7.2 - chapa(s) de reforco da alma. Dimensiona a espessura TOTAL de
    reforco (dois lados) que cobre o excesso de cortante (FSd - F_Rd), por 5.4:
    0,6 fy dc t_dob / gamma_a1 >= FSd - F_Rd. Retorna t_dob em mm (0 se nao precisa)."""
    excesso = FSd - F_Rd
    if excesso <= 0:
        return 0.0
    t = excesso * GA1 / (0.6 * fy * dc)          # m
    return math.ceil(t * 1000.0)                  # mm, arredonda p/ cima


def estados_locais(caso):
    """Estados-limites locais sob as mesas da viga (forcas concentradas na mesa
    do pilar). Retorna dict por estado + precisa_enrijecedor.
      5.7.2.2 flexao local da mesa (tracao)    : 6,25 tf^2 fy / GA1
      5.7.3.2 escoamento local da alma          : 1,10 (a*k + ln) fy tw / GA1
      5.7.6.2 flambagem da alma por compressao  : 24 tw^3 sqrt(E fy) / (h GA1)
    A forca concentrada = FSd (mesma das mesas da viga)."""
    fy = caso["fy"]
    tf_c, tw_c = caso["tf_col"], caso["tw_col"]
    dc = caso["dc"]
    FSd = forca_das_mesas(caso["M_Sd"], caso["d_viga"], caso["tf_viga"])
    # k = espessura da mesa carregada + perna de solda (~ mesa); ln = espessura da
    # mesa da viga (comprimento de atuacao da forca na direcao longitudinal).
    k = tf_c + 0.008
    ln = caso.get("tf_viga", 0.0095)
    a_k = 2.5 if caso.get("extremidade") else 5.0
    h = max(dc - 2.0 * tf_c, 1e-6)                # altura livre da alma do pilar
    Ff_flex = 6.25 * tf_c ** 2 * fy / GA1                       # 5.7.2.2
    if caso.get("extremidade"):
        Ff_flex *= 0.5                                         # 5.7.2.3
    Ff_esc = 1.10 * (a_k * k + ln) * fy * tw_c / GA1           # 5.7.3.2
    Ff_flamb = 24.0 * tw_c ** 3 * math.sqrt(E * fy) / (h * GA1)  # 5.7.6.2
    if caso.get("extremidade"):
        Ff_flamb *= 0.5                                        # 5.7.6.3
    estados = {"flexao_local_mesa": Ff_flex, "escoamento_local_alma": Ff_esc,
               "flambagem_alma_compressao": Ff_flamb}
    governa = min(estados, key=estados.get)
    F_min = estados[governa]
    return {"FSd": FSd, "estados": estados, "governa": governa,
            "F_Rd_min": F_min, "u_local": FSd / F_min if F_min > 0 else float("inf"),
            "precisa_enrijecedor": FSd > F_min}


def verifica_painel(caso):
    """Verificacao consolidada da zona de painel do joelho. Junta o cisalhamento
    do painel (5.7.7) e os estados locais sob as mesas (5.7.2/5.7.3/5.7.6),
    decidindo doubler e/ou enrijecedores."""
    cis = cisalhamento_painel(caso)
    loc = estados_locais(caso)
    precisa_reforco = cis["u_painel"] > 1.0
    t_dob = dimensiona_doubler(cis["FSd"], cis["F_Rd"], caso["dc"], caso["fy"]) \
        if precisa_reforco else 0.0
    u_max = max(cis["u_painel"], loc["u_local"])
    return {**cis, "local": loc,
            "precisa_reforco": precisa_reforco, "t_doubler_mm": t_dob,
            "precisa_enrijecedor": loc["precisa_enrijecedor"],
            "u_local": loc["u_local"], "u_max": u_max}


def relatorio_pt(r, caso):
    """Relatorio PT da zona de painel do joelho."""
    L = ["=" * 66, "ZONA DE PAINEL DO JOELHO (no rigido viga-coluna) - NBR 8800 5.7",
         "=" * 66,
         "  Pilar: dc=%.0f mm ; tw=%.1f mm ; tf=%.1f mm ; bf=%.0f mm" % (
             caso["dc"] * 1000, caso["tw_col"] * 1000, caso["tf_col"] * 1000,
             caso["bf_col"] * 1000),
         "  Viga : d=%.0f mm ; tf=%.1f mm" % (
             caso["d_viga"] * 1000, caso["tf_viga"] * 1000),
         "  M_Sd=%.1f kN.m ; N_Sd=%.1f kN ; fy=%.0f MPa" % (
             caso["M_Sd"], caso.get("N_Sd", 0.0), caso["fy"] / 1000),
         "",
         "  CISALHAMENTO DO PAINEL (5.7.7):",
         "    FSd (mesas da viga) = M/dm = %.1f kN" % r["FSd"],
         "    V_Rd (painel, 5.4.3) = %.1f kN" % r["V_Rd"],
         "    Npl = Ag.fy = %.1f kN ; N_Sd/0,4Npl -> %s" % (
             r["Npl"], "reduz F_Rd" if r["reduz_axial"] else "sem reducao"),
         "    F_Rd = %.1f kN ; u_painel = %.2f" % (r["F_Rd"], r["u_painel"])]
    if r["precisa_reforco"]:
        L.append("    >> EXIGE chapa de reforco (doubler): t_total = %.0f mm "
                 "(dois lados, +150 mm alem do painel)" % r["t_doubler_mm"])
    else:
        L.append("    >> painel OK sem reforco.")
    loc = r["local"]
    L += ["", "  ESTADOS LOCAIS SOB AS MESAS (forca concentrada = FSd):",
          "    flexao local da mesa (5.7.2)      = %.1f kN" % loc["estados"]["flexao_local_mesa"],
          "    escoamento local da alma (5.7.3)  = %.1f kN" % loc["estados"]["escoamento_local_alma"],
          "    flambagem da alma compr. (5.7.6)  = %.1f kN" % loc["estados"]["flambagem_alma_compressao"],
          "    governante = %s ; u_local = %.2f" % (loc["governa"], loc["u_local"])]
    if loc["precisa_enrijecedor"]:
        L.append("    >> EXIGE enrijecedores transversais (ambos os lados da alma, 5.7.9).")
    else:
        L.append("    >> estados locais OK sem enrijecedor.")
    L += ["", "  >> UTILIZACAO MAX DO NO = %.2f" % r["u_max"], "=" * 66]
    return "\n".join(L)


def _selftest():
    caso = {"M_Sd": 180.0, "N_Sd": 120.0, "V_col": 40.0,
            "dc": 0.19, "tw_col": 0.0065, "bf_col": 0.20, "tf_col": 0.010,
            "Ag_col": 0.005383, "d_viga": 0.36, "tf_viga": 0.0095,
            "fy": 250e3, "extremidade": False}
    # FSd = M/dm
    assert abs(forca_das_mesas(180.0, 0.36, 0.0095) - 180.0 / 0.3505) < 1e-6
    # sem axial: F_Rd = V_Rd
    r0 = cisalhamento_painel({**caso, "N_Sd": 0.0})
    assert abs(r0["F_Rd"] - r0["V_Rd"]) < 1e-6
    # axial alto reduz
    Npl = caso["Ag_col"] * caso["fy"]
    r1 = cisalhamento_painel({**caso, "N_Sd": 0.6 * Npl})
    assert r1["F_Rd"] < r1["V_Rd"]
    assert abs(r1["F_Rd"] - r1["V_Rd"] * (1.4 - 0.6)) / r1["V_Rd"] < 1e-6
    # alma fina exige doubler que cobre o excesso
    rr = verifica_painel({**caso, "tw_col": 0.004, "M_Sd": 260.0, "N_Sd": 80.0})
    assert rr["precisa_reforco"] and rr["t_doubler_mm"] > 0
    add = 0.6 * caso["fy"] * caso["dc"] * (rr["t_doubler_mm"] / 1000.0) / GA1
    assert add >= (rr["FSd"] - rr["F_Rd"]) - 1e-6
    # alma espessa passa
    assert not verifica_painel({**caso, "tw_col": 0.020, "M_Sd": 120.0})["precisa_reforco"]
    print("zona_painel self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        c = {"M_Sd": 180.0, "N_Sd": 120.0, "V_col": 40.0,
             "dc": 0.19, "tw_col": 0.0065, "bf_col": 0.20, "tf_col": 0.010,
             "Ag_col": 0.005383, "d_viga": 0.36, "tf_viga": 0.0095,
             "fy": 250e3, "extremidade": False}
        print(relatorio_pt(verifica_painel(c), c))
