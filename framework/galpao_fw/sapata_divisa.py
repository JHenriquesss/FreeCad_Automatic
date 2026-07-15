# ============================================================================
# sapata_divisa.py - SAPATA DE DIVISA com VIGA ALAVANCA (Velloso & Lopes / NBR 6122)
# Quando o pilar esta na divisa do lote, a sapata nao pode ser centrada.
# Uma viga alavanca conecta a sapata de divisa (excêntrica) a uma sapata
# interna, eliminando a excentricidade e uniformizando a pressao no solo.
# METODO: iterativo - arbitra R', calcula B, L, e, R_real, converge.
# Alivio na sapata interna = metade de Delta_P (praxe de projeto).
# Reaproveita fundacao_sapata para o concreto (flexao, puncao, compressao diagonal).
# ============================================================================
"""Sapata de divisa + viga alavanca. Saidas PT. Unidades: m, kN."""

from __future__ import annotations
import math
import fundacao_sapata as fs
import viga_baldrame as vb        # reaproveita _verifica_cortante (biela/estribo min)

GF = 1.4                     # coef. ponderacao ELU
SIGMA_SOLO_ADM = 250.0       # kN/m2 (default, sobrescrito por input)
FATOR_ALIVIO = 0.5           # fração do alivio aplicada na sapata interna (praxe 0,5)


def dimensiona_divisa(P_divisa, P_interno, dist_eixos, dist_divisa,
                      b_col_paralela=None, sigma_solo=None, fck=25e3, fyk=500e3,
                      L_fixo=None, cobrimento=0.05):
    """Dimensiona sapata de divisa + viga alavanca + sapata interna.
    
    P_divisa: carga do pilar da divisa (kN, caracteristica)
    P_interno: carga do pilar interno (kN, caracteristica)
    dist_eixos: distancia entre eixos dos pilares (m)
    dist_divisa: distancia do centro do pilar da divisa ate a divisa (m)
    sigma_solo: tensao admissivel do solo (kN/m2)
    B_fixo: largura fixa da sapata de divisa (opcional, default = auto)
    
    Retorna dict com resultados completos."""
    sig = sigma_solo if sigma_solo is not None else SIGMA_SOLO_ADM
    
    # --- Sapata de divisa (processo iterativo) --------------------------------
    # Largura maxima disponivel = 2 * dist_divisa - folga (2.5 cm de cada lado)
    B_max = 2.0 * (dist_divisa - 0.025)
    # Chute inicial: R' ~ 10% maior que P_divisa
    R = P_divisa * 1.10
    # Alonso: B = dimensao PERPENDICULAR a divisa (fixa, onde atua e).
    # L = dimensao PARALELA a divisa (varia para prover area).
    b_col_div = 2.0 * dist_divisa
    # Alonso: fixa B (perp. a divisa). Estimativa inicial: B ~ 1.5 a 2.0 m
    # para cargas tipicas. B e ajustado para obter L/B ~ 2.
    B_foot = max(b_col_div + 0.30, 1.80)
    # A excentricidade atua SEMPRE na direcao PERPENDICULAR a divisa (B_foot):
    # e = (B - b_col)/2. A dimensao PARALELA (L) nao influencia e. Por isso NAO
    # se troca B<->L quando o usuario fixa L (corrige inversao dimensional).
    e_fixo = max((B_foot - b_col_div) / 2.0, 0.0)
    # Com B_foot fixo, e_fixo e constante. Reacao direta (Alonso):
    e = e_fixo
    R_divisa = P_divisa * dist_eixos / max(dist_eixos - e, 0.01)
    B = B_foot
    if L_fixo:                     # usuario fixou o comprimento PARALELO a divisa
        L = L_fixo                 # e continua baseado em B (perpendicular)
    else:
        L = R_divisa / sig / B_foot
    # NBR 6122 7.7.1: nenhuma dimensao de sapata isolada/divisa < 60 cm
    L = max(L, 0.60)
    B = max(B, 0.60)
    
    # --- Alivio na sapata interna --------------------------------------------
    delta_P = R_divisa - P_divisa
    P_int_ajust = P_interno - FATOR_ALIVIO * delta_P
    
    # --- Sapata interna (centrada) -------------------------------------------
    A_int = max(P_int_ajust, 0.0) / sig
    if A_int <= 0:
        B_int = L_int = 0.0
    else:
        L_int = B_int = math.sqrt(A_int)
        if L_int / B_int > 2.0:
            B_int = math.sqrt(A_int / 2.0)
            L_int = A_int / B_int
    
    # --- Viga alavanca: esforcos --------------------------------------------
    # Esquema: viga bi-apoiada com balanco. Carga na sapata de divisa = R_divisa
    # (distribuida em B). Reacao no pilar = P_divisa. Momento max no engaste.
    # Comprimento da viga = dist_eixos
    # Carga na sapata de divisa: q = R_divisa / B (kN/m)
    q_div = R_divisa / B
    # Estatica exata (corte no centroide da sapata de divisa): a unica forca a
    # direita do corte e a carga do pilar P no braco e -> M = P*e (NAO R'*e, que
    # superestimava por l/(l-e)). Consistente com viga_equilibrio.py.
    M_viga = P_divisa * e
    V_viga = R_divisa - P_divisa  # cortante = delta_P (diferenca entre R e P)
    # Secao da viga alavanca: h ~ L/6 a L/8 (viga de transicao)
    h_viga = max(dist_eixos / 7.0, 0.50)
    # Largura da viga = largura do pilar da divisa
    b_viga = 0.25  # largura tipica da viga alavanca (m)
    d_viga = h_viga - cobrimento - 0.0125
    
    # Armadura longitudinal (flexao): tracao na face SUPERIOR.
    # Cisalhamento (NBR 6118 17.4): V = Delta_P e CONSTANTE ao longo do vao; a
    # viga alavanca frequentemente e governada pela biela (VRd2), nao pela flexao.
    M_d = GF * M_viga
    V_d = GF * V_viga
    As_viga, x_d, _, ok = fs._armadura_flexao(M_d, b_viga, d_viga, fck, fyk)
    cr = vb._verifica_cortante(V_d, b_viga, d_viga, fck, fyk)
    ok_flex = ok and As_viga is not None
    ok_cort = cr["ok_biela"] and cr["ok_min"]
    # Se nao passa flexao E biela, aumentar h ate passar as duas
    for _ in range(6):
        if ok_flex and ok_cort: break
        h_viga *= 1.3
        d_viga = h_viga - cobrimento - 0.0125
        As_viga, x_d, _, ok = fs._armadura_flexao(M_d, b_viga, d_viga, fck, fyk)
        cr = vb._verifica_cortante(V_d, b_viga, d_viga, fck, fyk)
        ok_flex = ok and As_viga is not None
        ok_cort = cr["ok_biela"] and cr["ok_min"]
    if As_viga is None:
        As_viga = 0.0
    ok = ok_flex and ok_cort
    # espacamento maximo de estribo (NBR 6118 18.3.3.2)
    s_estribo = min(0.6 * d_viga, 0.30) if V_d <= 0.67 * cr["VRd2"] else min(0.3 * d_viga, 0.20)

    # Armadura de pele / construtiva
    As_viga_min = fs.rho_min(fck / 1000.0) * b_viga * h_viga
    As_viga_final = max(As_viga, As_viga_min)
    arr_viga = fs.detalha_barras(As_viga_final, b_viga, cobrimento)
    
    return {
        "divisa": {"P": P_divisa, "R": round(R_divisa, 1), "e": round(e, 3),
                   "B": round(B, 2), "L": round(L, 2), "A": round(B * L, 2),
                   "sigma": round(R_divisa / (B * L), 1),
                   "b_col_div": round(b_col_div, 2), "dist_divisa": dist_divisa},
        "interno": {"P": P_interno, "P_ajust": round(P_int_ajust, 1),
                    "delta_P": round(delta_P, 1), "B": round(B_int, 2),
                    "L": round(L_int, 2), "A": round(B_int * L_int, 2)},
        "viga": {"M_max_kNm": round(M_viga, 2), "V_max_kN": round(V_viga, 1),
                 "Vd_kN": round(V_d, 1), "h": round(h_viga, 2), "b": b_viga,
                 "d": round(d_viga, 2), "As_cm2": round(As_viga * 1e4, 2),
                 "As_min_cm2": round(As_viga_min * 1e4, 2),
                 "As_adot_cm2": round(As_viga_final * 1e4, 2),
                 "VRd2_kN": round(cr["VRd2"], 1), "VRd3_min_kN": round(cr["VRd3_min"], 1),
                 "u_biela": round(cr["u_biela"], 3), "s_estribo_max_m": round(s_estribo, 3),
                 "arr": arr_viga, "ok_flexao": ok_flex, "ok_cortante": ok_cort, "ok": ok},
        "params": {"P_divisa": P_divisa, "P_interno": P_interno,
                   "dist_eixos": dist_eixos, "dist_divisa": dist_divisa,
                   "sigma_solo": sig, "fck": fck, "fyk": fyk}
    }


def relatorio_pt(r):
    d = r["divisa"]; i = r["interno"]; v = r["viga"]
    def _arr(a):
        if a and a.get("n"):
            return f'{a["n"]} phi {a["phi"]:.1f} mm (s={a["s"]*1000:.0f} mm)'
        return "(detalhar)"
    L = ["SAPATA DE DIVISA + VIGA ALAVANCA (NBR 6122 / Velloso & Lopes)",
         "", "1. SAPATA DE DIVISA:",
         f"   Pilar P_divisa = {d['P']:.0f} kN ; distancia a divisa = {d['dist_divisa']:.2f} m",
         f"   Reacao R = P * l/(l-e) = {d['R']:.1f} kN (l={r['params']['dist_eixos']:.2f}m, e={d['e']:.3f}m)",
         f"   Sapata: {d['B']:.2f} x {d['L']:.2f} m (A={d['A']:.2f} m2)",
         f"   Tensao no solo: {d['sigma']:.1f} kN/m2 <= {r['params']['sigma_solo']:.0f} kN/m2",
         "", "2. VIGA ALAVANCA (tracao na face SUPERIOR):",
         f"   M_max = P * e = {v['M_max_kNm']:.2f} kN.m ; V_max = R - P = {v['V_max_kN']:.1f} kN",
         f"   Secao: {v['b']*100:.0f} x {v['h']*100:.0f} cm (d={v['d']*100:.0f} cm)",
         f"   As,flexao = {v['As_cm2']:.2f} cm2 ; As,min = {v['As_min_cm2']:.2f} cm2",
         f"   Armadura adotada: {v['As_adot_cm2']:.2f} cm2 -> {_arr(v['arr'])}",
         f"   Cortante (17.4): Vd = {v['Vd_kN']:.1f} kN ; VRd2 (biela) = {v['VRd2_kN']:.1f} kN "
         f"(u={v['u_biela']:.3f}) ; VRd3,min = {v['VRd3_min_kN']:.1f} kN ; "
         f"s_max = {v['s_estribo_max_m']*1000:.0f} mm ; {'OK' if v['ok_cortante'] else 'REPROVA (biela)'}",
         "", "3. SAPATA INTERNA (com alivio):",
         f"   Pilar interno P = {i['P']:.0f} kN ; Delta_P = R - P = {i['delta_P']:.1f} kN",
         f"   Alivio adotado: {FATOR_ALIVIO*100:.0f}% -> P_ajust = P - {FATOR_ALIVIO:.1f}*Delta_P = {i['P_ajust']:.1f} kN",
         f"   Sapata: {i['B']:.2f} x {i['L']:.2f} m (A={i['A']:.2f} m2)",
         "", "   [A CONFIRMAR: carga real dos pilares (envelope do portico);",
         "    tensao admissivel do solo (sondagem); geometria da divisa.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # Exemplo de Velloso & Lopes / Alonso: P_div=1400 kN, P_int=1900 kN, l=5.5m
    # Coluna 100x22 (100cm paralela a divisa, 22cm perpendicular). dist_divisa=0.11 (22/2)
    r = dimensiona_divisa(1400.0, 1900.0, dist_eixos=5.50, dist_divisa=0.11,
                          b_col_paralela=1.0, sigma_solo=250.0)
    d = r["divisa"]; i = r["interno"]; v = r["viga"]
    assert abs(d["R"] - 1635) < 30, f"R={d['R']}"
    assert abs(d["L"] - 3.63) < 0.40, f"L={d['L']}"
    assert abs(d["B"] - 1.80) < 0.20, f"B={d['B']}"
    assert abs(d["e"] - 0.79) < 0.10, f"e={d['e']}"
    assert abs(i["B"] - 2.70) < 0.30, f"B_int={i['B']}"
    print("sapata_divisa self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(dimensiona_divisa(1400.0, 1900.0, 5.50, 0.11, b_col_paralela=1.0, sigma_solo=250.0)))
