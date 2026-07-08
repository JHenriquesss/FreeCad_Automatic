# ============================================================================
# viga_baldrame.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Dimensiona a VIGA DE BALDRAME / AMARRACAO entre as sapatas (concreto armado,
# ABNT NBR 6118:2014). Dois papeis:
#   1) BALDRAME: viga sob a parede de fechamento (alvenaria) vencendo o vao entre
#      sapatas -> flexao (17.2) + armadura minima (rho_min, Tab.17.3).
#   2) AMARRACAO: absorve a reacao HORIZONTAL da base do pilar (empuxo do portico)
#      como tracao axial -> As = Nd/fyd, aliviando o solo/atrito da sapata.
#   Detalhamento: b_min=12 cm (13.2.2), estribo s_max=0,6d<=300 mm (18.3.3.2).
# REUSA as rotinas de concreto ja validadas em fundacao_sapata (_armadura_flexao,
# rho_min, detalha_barras). A carga da parede, o vao e a forca de amarracao sao
# DADOS DO PROJETO (o vao e a reacao vem do proprio modelo; a parede, do gate).
# ============================================================================
"""Viga de baldrame / amarracao entre sapatas (NBR 6118:2014). Flexao sob a parede
+ tracao de amarracao (reacao horizontal da base). Reaproveita o concreto armado
de fundacao_sapata. Saidas em portugues. Unidades: m, kN ; fck/fyk em kN/m2."""

from __future__ import annotations

import math
import fundacao_sapata as fs

GAMMA_C_CONC = 25.0        # peso especifico do concreto armado (kN/m3) - NBR 6118
GF = 1.4                   # coef. de ponderacao das acoes (ELU, combinacao normal)
B_MIN = 0.12               # largura minima de viga (NBR 6118 13.2.2)

# Coeficiente de momento por continuidade (biapoiada entre sapatas / continua).
_COEF_M = {"simples": 1.0 / 8.0, "continua": 1.0 / 10.0}

# Armadura construtiva superior (porta-estribos, face comprimida): 2 phi 6.3 mm.
AS_CONSTRUTIVA_SUP = 2.0 * math.pi * (0.0063 ** 2) / 4.0


def _verifica_cortante(Vd, b, d, fck, fyk):
    """Verifica cisalhamento de viga (Modelo I, θ=45°, NBR 6118 17.4.2).
    Retorna dict com VRd2 (biela) e VRd3_min (estribo minimo) em kN,
    e utilizacoes. Vd ja majorado (ELU)."""
    fck_MPa = fck / 1000.0
    fcd = fck / 1.4
    fywd = fyk / 1.15
    alpha_v2 = 1.0 - fck_MPa / 250.0
    VRd2 = 0.27 * alpha_v2 * fcd * b * d
    fctm_MPa = 0.3 * fck_MPa ** (2.0 / 3.0)
    fctd_MPa = 0.7 * fctm_MPa / 1.4
    Vc = 0.6 * fctd_MPa * 1000.0 * b * d
    fywk_MPa = fyk / 1000.0
    rho_sw_min = 0.2 * fctm_MPa / fywk_MPa if fywk_MPa > 0 else 0.0
    asw_min = rho_sw_min * b
    Vsw_min = asw_min * 0.9 * d * fywd
    VRd3_min = Vc + Vsw_min
    return {"VRd2": VRd2, "VRd3_min": VRd3_min, "Vc": Vc, "Vsw_min": Vsw_min,
            "rho_sw_min": rho_sw_min,
            "u_biela": Vd / VRd2 if VRd2 > 0 else float("inf"),
            "u_cort": Vd / VRd3_min if VRd3_min > 0 else float("inf"),
            "ok_biela": Vd <= VRd2 + 1e-9, "ok_min": Vd <= VRd3_min + 1e-9}


def verifica_baldrame(cfg):
    """Dimensiona a viga de baldrame/amarracao.
    cfg: {vao [m], b [m], h [m], fck, fyk [kN/m2], cobrimento [m],
          q_parede [kN/m] (carga da alvenaria de fechamento; 0 se so telha),
          N_amarracao [kN] (reacao horizontal da base = tracao de amarracao),
          continuidade ('simples'|'continua'), phi_estribo_mm}. 1 viga."""
    L = cfg["vao"]
    b = cfg.get("b", 0.20)
    h = cfg.get("h", 0.40)
    fck = cfg["fck"]; fyk = cfg["fyk"]
    cob = cfg.get("cobrimento", 0.05)
    phi_est = cfg.get("phi_estribo_mm", 5.0) / 1000.0
    d = h - cob - phi_est - 0.010          # altura util (estimativa: barra ~20 mm)
    cM = _COEF_M.get(cfg.get("continuidade", "simples"), 1.0 / 8.0)

    # ---- 1) BALDRAME: flexao sob a parede + peso proprio -------------------
    w_self = GAMMA_C_CONC * b * h
    w = cfg.get("q_parede", 0.0) + w_self          # carga caracteristica (kN/m)
    M_d = GF * cM * w * L ** 2                      # momento de calculo (kN.m)
    As_flex, x_d, z, ok_dom = fs._armadura_flexao(M_d, b, d, fck, fyk)
    sec_ok = As_flex is not None                   # secao suficiente a flexao?

    # ---- 2) AMARRACAO: tracao axial (reacao horizontal da base) ------------
    N_tie = abs(cfg.get("N_amarracao", 0.0))
    Nd_tie = GF * N_tie
    fyd = fyk / 1.15
    As_tie = Nd_tie / fyd if fyd > 0 else 0.0      # tracao -> dividida nas 2 faces

    # ---- cortante (cisalhamento) - obrigatorio NBR 6118 17.4 --------------
    Vd = GF * w * L / 2.0
    cr = _verifica_cortante(Vd, b, d, fck, fyk)
    cort_ok = cr["ok_biela"] and cr["ok_min"]

    # ---- minimos e composicao ---------------------------------------------
    rho = fs.rho_min(fck / 1000.0)                 # Tabela 17.3 (piso 0,15%)
    As_min = rho * b * h
    As_flex = As_flex or 0.0
    As_inf = max(As_flex + As_tie / 2.0, As_min)   # face tracionada por flexao + amarracao
    As_sup = max(As_tie / 2.0, AS_CONSTRUTIVA_SUP) # face comprimida: amarracao + porta-estribos
    arr_inf = fs.detalha_barras(As_inf, b, cob)
    arr_sup = fs.detalha_barras(As_sup, b, cob)

    # ---- detalhamento (NBR 6118 13.2.2 / 18.3.3.2) ------------------------
    if Vd <= 0.67 * cr["VRd2"]:
        s_estribo = min(0.6 * d, 0.30)
    else:
        s_estribo = min(0.3 * d, 0.20)
    b_ok = b >= B_MIN - 1e-9

    OK = sec_ok and ok_dom and b_ok and cort_ok
    return {"vao": L, "b": b, "h": h, "d": round(d, 3), "M_d": round(M_d, 2),
            "w": round(w, 3), "w_self": round(w_self, 3), "N_tie": N_tie,
            "Vd": round(Vd, 2),
            "VRd2": round(cr["VRd2"], 1), "VRd3_min": round(cr["VRd3_min"], 1),
            "u_biela": round(cr["u_biela"], 3), "u_cort": round(cr["u_cort"], 3),
            "As_flex_cm2": round(As_flex * 1e4, 2), "As_tie_cm2": round(As_tie * 1e4, 2),
            "As_min_cm2": round(As_min * 1e4, 2),
            "As_inf_cm2": round(As_inf * 1e4, 2), "As_sup_cm2": round(As_sup * 1e4, 2),
            "As_construtiva_cm2": round(AS_CONSTRUTIVA_SUP * 1e4, 3),
            "arr_inf": arr_inf, "arr_sup": arr_sup, "x_d": round(x_d, 3),
            "ok_dominio": ok_dom, "sec_ok": sec_ok, "b_ok": b_ok, "cort_ok": cort_ok,
            "s_estribo_max": round(s_estribo, 3), "phi_estribo_mm": cfg.get("phi_estribo_mm", 5.0),
            "OK": OK}


def relatorio_pt(r):
    def _arr(a):
        return (f"{a['n']} phi {a['phi']:.1f} mm (s={a['s']*1000:.0f} mm, "
                f"As_ef={a['As_ef']*1e4:.2f} cm2)"
                if a and a.get("n") else "(detalhar)")
    L = ["VIGA DE BALDRAME / AMARRACAO (ABNT NBR 6118:2014)",
         f"  Vao entre sapatas = {r['vao']:.2f} m ; secao {r['b']*100:.0f}x{r['h']*100:.0f} cm "
         f"(d={r['d']*100:.0f} cm) ; b_min 12 cm {'OK' if r['b_ok'] else 'REPROVA'}",
         f"  BALDRAME (flexao): w = {r['w']:.3f} kN/m (parede + p.proprio {r['w_self']:.3f}) ; "
         f"M_d = {r['M_d']:.2f} kN.m",
         f"    As,flexao = {r['As_flex_cm2']:.2f} cm2 ; x/d = {r['x_d']:.3f} "
         f"{'OK' if r['ok_dominio'] else 'FORA DO DOMINIO (aumentar secao)'}"
         + ('' if r['sec_ok'] else ' ; SECAO INSUFICIENTE'),
         f"  AMARRACAO (tracao): N_tie = {r['N_tie']:.1f} kN (reacao horiz. da base) ; "
         f"As,amarracao = {r['As_tie_cm2']:.2f} cm2",
         f"  As,min (rho_min*b*h) = {r['As_min_cm2']:.2f} cm2",
         f"  Armadura inferior: As = {r['As_inf_cm2']:.2f} cm2 -> {_arr(r['arr_inf'])}",
         f"  Armadura superior: As = {r['As_sup_cm2']:.2f} cm2 -> {_arr(r['arr_sup'])} "
         f"(construtiva 2 phi 6,3 = {r['As_construtiva_cm2']:.3f} cm2)",
         f"  CORTANTE (17.4): Vd = {r['Vd']:.2f} kN ; VRd2 (biela) = {r['VRd2']:.1f} kN "
         f"(u={r['u_biela']:.3f}) ; VRd3_min (estribo min) = {r['VRd3_min']:.1f} kN "
         f"(u={r['u_cort']:.3f}) ; {'OK' if r['cort_ok'] else 'REPROVA'}",
         f"  Estribos: phi {r['phi_estribo_mm']:.1f} mm ; s_max = "
         f"{r['s_estribo_max']*1000:.0f} mm (18.3.3.2)",
         f"  RESULTADO: {'APROVADA' if r['OK'] else 'REPROVADA'}",
         "  [A CONFIRMAR: carga da parede de fechamento (tipo/altura da alvenaria);",
         "   forca de amarracao (reacao horizontal da base do envelope); secao b x h.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # baldrame 5 m, alvenaria 2,5 m x 2,4 kN/m2/m = 6 kN/m ; secao 20x40 ; C25 CA50
    cfg = {"vao": 5.0, "b": 0.20, "h": 0.40, "fck": 25e3, "fyk": 500e3,
           "cobrimento": 0.05, "q_parede": 6.0, "N_amarracao": 30.0}
    r = verifica_baldrame(cfg)
    # M_d = 1,4 * (6 + 25*0,2*0,4)*5^2/8 = 1,4*(6+2)*25/8 = 1,4*25 = 35 kN.m
    w = 6.0 + 25.0 * 0.2 * 0.4
    assert abs(r["w"] - w) < 1e-9, r
    assert abs(r["M_d"] - 1.4 * w * 25.0 / 8.0) < 1e-6, r["M_d"]
    # amarracao: As = 1,4*30/(500e3/1,15) = 42/434782,6 m2 = 0,966 cm2
    assert abs(r["As_tie_cm2"] - 1.4 * 30.0 / (500e3 / 1.15) * 1e4) < 1e-2, r
    # dominio ok e secao suficiente
    assert r["ok_dominio"] and r["sec_ok"] and r["b_ok"] and r["cort_ok"] and r["OK"], r
    # As_inf >= As_min e >= As_flex + As_tie/2
    assert r["As_inf_cm2"] >= r["As_min_cm2"] - 1e-9
    assert r["As_inf_cm2"] >= r["As_flex_cm2"] + r["As_tie_cm2"] / 2.0 - 0.02
    # As_sup NAO governada por As_min (face comprimida -> construtiva)
    assert r["As_sup_cm2"] < r["As_min_cm2"] - 0.1, \
        f"As_sup {r['As_sup_cm2']} >= As_min {r['As_min_cm2']} (antieconomico)"
    assert abs(r["As_sup_cm2"] - r["As_construtiva_cm2"]) < 0.01, \
        f"As_sup {r['As_sup_cm2']} != construtiva {r['As_construtiva_cm2']}"
    # Vd cortante esperado
    Vd_esp = 1.4 * w * 5.0 / 2.0
    assert abs(r["Vd"] - Vd_esp) < 1e-9, r
    assert r["cort_ok"], f"cortante reprova: u_biela={r['u_biela']} u_cort={r['u_cort']}"
    # b < 12 cm reprova
    r2 = verifica_baldrame({**cfg, "b": 0.10})
    assert not r2["b_ok"] and not r2["OK"], r2
    # secao pequena (10x15) sob M grande -> fora do dominio ou insuficiente
    r3 = verifica_baldrame({**cfg, "b": 0.12, "h": 0.15, "q_parede": 40.0})
    assert not r3["OK"], r3
    print("viga_baldrame self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        cfg = {"vao": 5.0, "b": 0.20, "h": 0.40, "fck": 25e3, "fyk": 500e3,
               "cobrimento": 0.05, "q_parede": 6.0, "N_amarracao": 30.0}
        print(relatorio_pt(verifica_baldrame(cfg)))
