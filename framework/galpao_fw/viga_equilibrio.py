# ============================================================================
# viga_equilibrio.py - BLOCO SOBRE ESTACAS NA DIVISA + VIGA DE EQUILIBRIO
# Variante PROFUNDA (estaca) da fundacao de divisa. Quando o pilar esta na divisa
# do lote E a fundacao e profunda, o grupo de estacas nao pode ser centrado sob o
# pilar (a divisa impede); o bloco fica EXCENTRICO. Uma VIGA DE EQUILIBRIO (viga
# alavanca) liga o bloco de divisa a um bloco interno, absorvendo o momento da
# excentricidade e transferindo a reacao amplificada.
#
# MECANICA (corpo rigido, identica a sapata_divisa - ja validada contra o exemplo
# Velloso & Lopes / Alonso): a reacao no bloco de divisa e AMPLIFICADA pelo braco
#   R' = P_divisa . l / (l - e)                (l = vao da viga; e = excentricidade
#                                               eixo do pilar -> centroide do grupo)
# O acrescimo Delta_P = R' - P_divisa ALIVIA o pilar interno (praxe: 50%).
# ESFORCOS NA VIGA (parecer item 48 - estatica de corpo rigido, corte no centroide
# do grupo): a unica forca a direita do corte e P_divisa no braco e, logo
#   M_viga = P_divisa . e     (NAO R'.e! provado: Delta_P.(l-e) = P.e)
#   V_viga = Delta_P          (cortante CONSTANTE ao longo do vao l-e)
# A viga e RC tracionada na FACE SUPERIOR: dimensiona flexao (_armadura_flexao) E
# CISALHAMENTO obrigatorio (NBR 6118 17.4: biela VRd2 + estribos, via viga_baldrame).
# Peso proprio do bloco+viga (praxe ~5% de R') entra na contagem de estacas.
# Reaproveita estaca_profunda (n_estacas, bloco), fundacao_sapata (_armadura_flexao)
# e viga_baldrame (_verifica_cortante).
# Ask-Do-Not-Invent: capacidade da estaca (P_adm) vem da SONDAGEM (estaca_profunda);
# a excentricidade depende do arranjo/diametro (default geometrico, A CONFIRMAR).
# Unidades SI: m, kN.
# ============================================================================
"""Bloco de divisa sobre estacas + viga de equilibrio. Saidas PT. m, kN."""

from __future__ import annotations
import math
import fundacao_sapata as fs
import estaca_profunda as ep
import viga_baldrame as vb

GF = 1.4                     # coef. ponderacao ELU
FATOR_ALIVIO = 0.5           # fracao do alivio aplicada no bloco interno (praxe 0,5)
FATOR_PP = 1.05              # majoracao p/ peso proprio bloco+viga na contagem de estacas (praxe Alonso ~5%)


def excentricidade_estimada(dist_divisa, D_estaca, espacamento=None, folga_borda=0.15):
    """Excentricidade geometrica (eixo do pilar -> centroide do grupo) para um bloco
    de divisa com 2 estacas perpendiculares a divisa. A estaca mais proxima da divisa
    fica a (D/2 + folga_borda); a segunda, a +espacamento. Centroide do par ->
    excentricidade e = (D/2 + folga + s/2) - dist_divisa. ARRANJO A CONFIRMAR."""
    s = espacamento if espacamento is not None else 3.0 * D_estaca
    x_centroide = D_estaca / 2.0 + folga_borda + s / 2.0
    return max(x_centroide - dist_divisa, 0.10)


def dimensiona_viga_equilibrio(P_divisa, P_interno, dist_eixos, dist_divisa,
                               P_estaca_adm, a_pilar, D_estaca=0.30, e=None,
                               espacamento=None, fck=25e3, fyk=500e3,
                               cobrimento=0.05, b_viga=None):
    """Dimensiona bloco de divisa sobre estacas + viga de equilibrio + bloco interno.
    P_divisa/P_interno: cargas caracteristicas dos pilares (kN).
    dist_eixos: vao da viga de equilibrio (entre eixos dos pilares, m).
    dist_divisa: distancia do eixo do pilar da divisa a divisa (m).
    P_estaca_adm: capacidade admissivel de UMA estaca (kN) - da sondagem.
    a_pilar: lado do pilar (m). D_estaca: diametro da estaca (m).
    e: excentricidade (m); se None, estimada geometricamente (A CONFIRMAR)."""
    s = espacamento if espacamento is not None else 3.0 * D_estaca
    if e is None:
        e = excentricidade_estimada(dist_divisa, D_estaca, s)
    # --- reacao amplificada no bloco de divisa (braco de alavanca) --------------
    R_divisa = P_divisa * dist_eixos / max(dist_eixos - e, 0.01)
    # peso proprio bloco+viga (praxe ~5% da reacao) majora a contagem de estacas
    n_est_div = ep.n_estacas(R_divisa, P_estaca_adm, peso_bloco=(FATOR_PP - 1.0) * R_divisa)["n"]
    # --- alivio no pilar interno -----------------------------------------------
    delta_P = R_divisa - P_divisa
    P_int_ajust = P_interno - FATOR_ALIVIO * delta_P
    n_est_int = ep.n_estacas(max(P_int_ajust, 0.0), P_estaca_adm,
                             peso_bloco=(FATOR_PP - 1.0) * max(P_int_ajust, 0.0))["n"]
    # --- viga de equilibrio: esforcos (tracao na face SUPERIOR) ----------------
    # M_max no centroide do grupo: forcas a direita do corte = so P_divisa @ braco e.
    # (parecer item 48: M = P.e, NAO R'.e; V = Delta_P constante ao longo do vao.)
    M_viga = P_divisa * e                              # momento fletor (estatica exata)
    V_viga = delta_P                                   # cortante = acrescimo de carga
    h_viga = max(dist_eixos / 7.0, 0.50)               # viga de transicao (l/7 a l/8)
    b_v = b_viga if b_viga is not None else max(a_pilar, 0.30)
    M_d = GF * M_viga
    V_d = GF * V_viga
    d_viga = h_viga - cobrimento - 0.0125
    As_viga, x_d, _, ok = fs._armadura_flexao(M_d, b_v, d_viga, fck, fyk)
    cr = vb._verifica_cortante(V_d, b_v, d_viga, fck, fyk)
    ok_flex = ok and As_viga is not None
    ok_cort = cr["ok_biela"] and cr["ok_min"]
    for _ in range(6):                                 # aumenta h ate passar flexao E biela
        if ok_flex and ok_cort:
            break
        h_viga *= 1.3
        d_viga = h_viga - cobrimento - 0.0125
        As_viga, x_d, _, ok = fs._armadura_flexao(M_d, b_v, d_viga, fck, fyk)
        cr = vb._verifica_cortante(V_d, b_v, d_viga, fck, fyk)
        ok_flex = ok and As_viga is not None
        ok_cort = cr["ok_biela"] and cr["ok_min"]
    if As_viga is None:
        As_viga = 0.0
    ok = ok_flex and ok_cort
    # espacamento de estribo (NBR 6118 18.3.3.2)
    s_estribo = min(0.6 * d_viga, 0.30) if V_d <= 0.67 * cr["VRd2"] else min(0.3 * d_viga, 0.20)
    As_min = fs.rho_min(fck / 1000.0) * b_v * h_viga
    As_final = max(As_viga, As_min)
    arr = fs.detalha_barras(As_final, b_v, cobrimento)
    return {
        "divisa": {"P": P_divisa, "R": round(R_divisa, 1), "e": round(e, 3),
                   "n_estacas": n_est_div, "espacamento": round(s, 2),
                   "carga_estaca": round(R_divisa / n_est_div, 1),
                   "P_estaca_adm": P_estaca_adm, "dist_divisa": dist_divisa},
        "interno": {"P": P_interno, "P_ajust": round(P_int_ajust, 1),
                    "delta_P": round(delta_P, 1), "n_estacas": n_est_int,
                    "carga_estaca": round(max(P_int_ajust, 0.0) / max(n_est_int, 1), 1)},
        "viga": {"M_max_kNm": round(M_viga, 2), "V_max_kN": round(V_viga, 1),
                 "h": round(h_viga, 2), "b": round(b_v, 2), "d": round(d_viga, 2),
                 "As_cm2": round(As_viga * 1e4, 2), "As_min_cm2": round(As_min * 1e4, 2),
                 "As_adot_cm2": round(As_final * 1e4, 2), "arr": arr,
                 "V_d_kN": round(V_d, 1), "VRd2_kN": round(cr["VRd2"], 1),
                 "VRd3_min_kN": round(cr["VRd3_min"], 1), "u_biela": round(cr["u_biela"], 3),
                 "s_estribo_cm": round(s_estribo * 100.0, 1),
                 "ok_flexao": ok_flex, "ok_cortante": ok_cort, "ok": ok},
        "params": {"P_divisa": P_divisa, "P_interno": P_interno,
                   "dist_eixos": dist_eixos, "dist_divisa": dist_divisa,
                   "P_estaca_adm": P_estaca_adm, "D_estaca": D_estaca,
                   "fck": fck, "fyk": fyk},
    }


def relatorio_pt(r):
    d = r["divisa"]; i = r["interno"]; v = r["viga"]; p = r["params"]

    def _arr(a):
        if a and a.get("n"):
            return f'{a["n"]} phi {a["phi"]:.1f} mm (s={a["s"]*1000:.0f} mm)'
        return "(detalhar)"
    L = ["BLOCO DE DIVISA SOBRE ESTACAS + VIGA DE EQUILIBRIO (NBR 6122 / Alonso)",
         "", "1. BLOCO DE DIVISA (excentrico):",
         f"   Pilar P_divisa = {d['P']:.0f} kN ; dist. a divisa = {d['dist_divisa']:.2f} m ; e = {d['e']:.3f} m",
         f"   Reacao amplificada R = P.l/(l-e) = {d['R']:.1f} kN (l={p['dist_eixos']:.2f} m)",
         f"   Estacas: {d['n_estacas']} x (P_adm={d['P_estaca_adm']:.0f} kN) ; carga/estaca = {d['carga_estaca']:.1f} kN",
         "", "2. VIGA DE EQUILIBRIO (tracao na face SUPERIOR):",
         f"   M_max = P.e = {v['M_max_kNm']:.2f} kN.m ; V = Delta_P = {v['V_max_kN']:.1f} kN (constante)",
         f"   Secao: {v['b']*100:.0f} x {v['h']*100:.0f} cm (d={v['d']*100:.0f} cm)",
         f"   FLEXAO: As = {v['As_cm2']:.2f} cm2 ; As,min = {v['As_min_cm2']:.2f} cm2",
         f"   Armadura adotada: {v['As_adot_cm2']:.2f} cm2 -> {_arr(v['arr'])}",
         f"   CORTANTE (NBR 6118 17.4): Vd = {v['V_d_kN']:.1f} kN ; VRd2 (biela) = {v['VRd2_kN']:.1f} kN "
         f"(u={v['u_biela']:.2f}) ; estribos s <= {v['s_estribo_cm']:.0f} cm",
         "", "3. BLOCO INTERNO (com alivio):",
         f"   Pilar interno P = {i['P']:.0f} kN ; Delta_P = R - P = {i['delta_P']:.1f} kN",
         f"   Alivio {FATOR_ALIVIO*100:.0f}% -> P_ajust = {i['P_ajust']:.1f} kN ; Estacas: {i['n_estacas']}",
         "", "   [A CONFIRMAR: carga real dos pilares (envelope do portico); capacidade",
         "    da estaca P_adm (sondagem); arranjo/excentricidade do grupo na divisa.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # P_div=1400, P_int=1900, l=5,5 m, dist_divisa=0,20 m, estaca D=0,40 P_adm=700 kN
    r = dimensiona_viga_equilibrio(1400.0, 1900.0, dist_eixos=5.5, dist_divisa=0.20,
                                   P_estaca_adm=700.0, a_pilar=0.40, D_estaca=0.40)
    d = r["divisa"]; i = r["interno"]; v = r["viga"]
    # braco de alavanca amplifica (R>P) e a formula bate
    R_esp = 1400.0 * 5.5 / (5.5 - d["e"])
    assert abs(d["R"] - R_esp) < 1.0, f"R={d['R']} vs {R_esp}"
    assert d["R"] > 1400.0
    # numero de estacas coerente com a capacidade
    assert d["n_estacas"] >= math.ceil(d["R"] / 700.0)
    # alivio reduz o pilar interno
    assert i["P_ajust"] < 1900.0 and i["delta_P"] > 0
    # momento fletor = P.e (estatica exata), NAO R.e
    assert abs(v["M_max_kNm"] - 1400.0 * d["e"]) < 0.01, f"M={v['M_max_kNm']} vs P.e={1400.0*d['e']:.2f}"
    assert v["M_max_kNm"] < d["R"] * d["e"]            # menor que a formula antiga R.e
    # viga passa a flexao E cortante (biela + estribo)
    assert v["ok_flexao"] and v["ok_cortante"] and v["ok"] and v["As_adot_cm2"] > 0
    assert v["VRd2_kN"] > v["V_d_kN"]                  # biela nao esmaga
    print(f"viga_equilibrio self-test PASSED (e={d['e']:.3f} R={d['R']:.0f} kN, M=P.e={v['M_max_kNm']:.0f} kNm, "
          f"{d['n_estacas']} estacas divisa / {i['n_estacas']} interno, "
          f"viga {v['b']*100:.0f}x{v['h']*100:.0f} As={v['As_adot_cm2']:.1f} cm2 Vd={v['V_d_kN']:.0f} kN)")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(dimensiona_viga_equilibrio(
            1400.0, 1900.0, 5.5, 0.20, 700.0, 0.40, 0.40)))
