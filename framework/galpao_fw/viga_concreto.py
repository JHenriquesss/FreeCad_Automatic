# ============================================================================
# viga_concreto.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Dimensiona uma VIGA de concreto armado retangular (ABNT NBR 6118:2014) a flexao
# simples + cisalhamento + ELS de flecha + detalhamento. Generaliza o que o
# viga_baldrame ja fazia (que e um caso particular: viga sob parede) para a viga de
# cobertura / travessa e vigas em geral do galpao de concreto. REUSA as rotinas ja
# aferidas:
#   - flexao (17.2.2, bloco retangular): fundacao_sapata._armadura_flexao
#     (aferida contra Alonso e contra Araujo/Carvalho: As 2,98 e 1,46 cm2);
#   - cortante (Modelo I, 17.4.2): viga_baldrame._verifica_cortante;
#   - flecha (17.3.2 Branson + fluencia): viga_baldrame._flecha_alvenaria;
#   - detalhamento (barras/ancoragem/rho_min): fundacao_sapata.
# ELS (Tabela 13.3): viga visivel -> L/250 (deslocamento total); viga que suporta
# alvenaria -> L/500 ou 10 mm (so a fluencia pos-parede, como no baldrame).
# Unidades: m, kN ; fck/fyk em kN/m2. Saidas em portugues.
# ============================================================================
"""Viga de concreto armado retangular (NBR 6118:2014): flexao + cortante + ELS de
flecha + detalhamento, reaproveitando as rotinas ja aferidas de sapata e baldrame.
A viga de cobertura do galpao de concreto e o caso de uso principal."""

from __future__ import annotations

import math

import fundacao_sapata as fs
import viga_baldrame as vb

GAMMA_C_CONC = 25.0                 # peso especifico do concreto armado (kN/m3)
GF = 1.4                            # ponderacao das acoes (ELU normal)
B_MIN = 0.12                        # largura minima de viga (13.2.2)
_COEF_M = {"simples": 1.0 / 8.0, "continua": 1.0 / 10.0}

# ELS - Tabela 13.3 (deslocamentos limites):
LIM_VISUAL = 250.0                  # aceitabilidade sensorial (deslocamentos visiveis): L/250


def dimensiona_viga(cfg, alturas=(0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70, 0.80)):
    """Adota a MENOR altura h (a partir da pedida) que atende ELU + ELS."""
    h0 = cfg.get("h", 0.30)
    r = None
    for h in [a for a in alturas if a >= h0 - 1e-9] or [h0]:
        r = verifica_viga(dict(cfg, h=h))
        if r["OK"]:
            return r
    return r


def verifica_viga(cfg):
    """Dimensiona/verifica uma viga retangular de concreto armado.

    cfg: {
      'vao'      : vao teorico (m).
      'b','h'    : secao (m). 'cobrimento' (m, default 0,03).
      'fck','fyk': resistencias (kN/m2). 'phi_estribo_mm' (default 5), 'phi_barra_mm' (default 16).
      'q'        : carga CARACTERISTICA uniforme (kN/m) - inclui peso proprio? Nao:
                   o p.proprio da viga e somado internamente. (Alternativa: 'M_d','V_d'.)
      'continuidade' : 'simples' (default) | 'continua'.
      'suporta_alvenaria' : bool ; 'q_alvenaria' (kN/m) da parede apoiada (ELS Tab 13.3).
      'gamma_f'  : default 1,4.
    }
    Retorna dict com ELU (flexao+cortante), ELS (flecha) e detalhamento."""
    L = cfg["vao"]
    b = cfg.get("b", 0.20)
    h = cfg.get("h", 0.40)
    fck = cfg["fck"]; fyk = cfg["fyk"]
    cob = cfg.get("cobrimento", 0.03)
    phi_est = cfg.get("phi_estribo_mm", 5.0) / 1000.0
    phi_bar = cfg.get("phi_barra_mm", 16.0) / 1000.0
    d = h - cob - phi_est - phi_bar / 2.0          # altura util
    gf = cfg.get("gamma_f", GF)
    continua = cfg.get("continuidade", "simples") == "continua"
    cM = _COEF_M["continua" if continua else "simples"]

    # ---- carga (peso proprio somado) --------------------------------------
    w_self = GAMMA_C_CONC * b * h
    w = cfg.get("q", 0.0) + w_self                 # caracteristica (kN/m)

    # ---- FLEXAO (17.2.2) --------------------------------------------------
    M_d = cfg.get("M_d", gf * cM * w * L ** 2)
    As_flex, x_d, z, ok_dom = fs._armadura_flexao(M_d, b, d, fck, fyk)
    sec_ok = As_flex is not None
    As_flex = As_flex or 0.0
    rho = fs.rho_min(fck / 1000.0)
    As_min = rho * b * h
    As_inf = max(As_flex, As_min)

    # momento negativo no apoio (viga continua) -> face superior
    M_d_neg = gf * (1.0 / 10.0) * w * L ** 2 if continua else 0.0
    As_neg = 0.0; ok_dom_neg = True; sec_ok_neg = True
    if continua:
        As_neg, _xn, _zn, ok_dom_neg = fs._armadura_flexao(M_d_neg, b, d, fck, fyk)
        sec_ok_neg = As_neg is not None
        As_neg = As_neg or 0.0
    As_sup = max(As_neg, As_min if continua else vb.AS_CONSTRUTIVA_SUP)

    # ---- CORTANTE (17.4.2, Modelo I) --------------------------------------
    V_d = cfg.get("V_d", gf * w * L / 2.0)
    cr = vb._verifica_cortante(V_d, b, d, fck, fyk)
    cort_ok = cr["ok_biela"] and cr["ok_min"]
    if V_d <= 0.67 * cr["VRd2"]:
        s_estribo = min(0.6 * d, 0.30)
    else:
        s_estribo = min(0.3 * d, 0.20)

    # ---- ELS: flecha (17.3.2 Branson + fluencia; Tab 13.3) ----------------
    # viga visivel -> L/250 (deslocamento TOTAL) ; viga que suporta alvenaria ->
    # L/500 ou 10 mm (so a fluencia pos-parede, como no baldrame).
    suporta_alv = cfg.get("suporta_alvenaria", False)
    w_els = w + (cfg.get("q_alvenaria", 0.0) if suporta_alv else 0.0)
    fl = vb._flecha_alvenaria(b, h, d, L, w_els, fck, As_inf, continua)
    if suporta_alv:
        d_comp_mm = fl["d_pos_parede_mm"]; lim_mm = fl["lim_mm"]
    else:
        d_comp_mm = fl["d_total_mm"]; lim_mm = round(L / LIM_VISUAL * 1000, 2)
    els_ok = d_comp_mm <= lim_mm + 1e-9
    els = {"d_total_mm": fl["d_total_mm"], "d_comparado_mm": d_comp_mm,
           "lim_mm": lim_mm, "fissura": fl["fissura"],
           "criterio": "alvenaria (L/500;10mm, pos-parede)" if suporta_alv
                       else "visual (L/250, total)", "ok": els_ok}

    # ---- detalhamento -----------------------------------------------------
    arr_inf = fs.detalha_barras(As_inf, b, cob)
    arr_sup = fs.detalha_barras(As_sup, b, cob)
    anc = fs.comprimento_ancoragem(cfg.get("phi_barra_mm", 16.0),
                                   fck / 1000.0, fyk / 1000.0, gancho=True)
    b_ok = b >= B_MIN - 1e-9

    OK = (sec_ok and ok_dom and b_ok and cort_ok and sec_ok_neg and ok_dom_neg
          and els_ok)
    return {"vao": L, "b": b, "h": h, "d": round(d, 3), "w": round(w, 3),
            "w_self": round(w_self, 3), "M_d": round(M_d, 2),
            "As_flex_cm2": round(As_flex * 1e4, 2), "As_min_cm2": round(As_min * 1e4, 2),
            "As_inf_cm2": round(As_inf * 1e4, 2), "As_sup_cm2": round(As_sup * 1e4, 2),
            "x_d": round(x_d, 3), "z": round(z, 3),
            "continua": continua, "M_d_neg": round(M_d_neg, 2),
            "As_neg_cm2": round(As_neg * 1e4, 2), "sec_ok_neg": sec_ok_neg,
            "ok_dominio_neg": ok_dom_neg,
            "V_d": round(V_d, 2), "VRd2": round(cr["VRd2"], 1),
            "VRd3_min": round(cr["VRd3_min"], 1), "u_biela": round(cr["u_biela"], 3),
            "u_cort": round(cr["u_cort"], 3), "s_estribo_max": round(s_estribo, 3),
            "phi_estribo_mm": cfg.get("phi_estribo_mm", 5.0),
            "arr_inf": arr_inf, "arr_sup": arr_sup, "ancoragem": anc,
            "els": els, "els_ok": els_ok,
            "ok_dominio": ok_dom, "sec_ok": sec_ok, "b_ok": b_ok, "cort_ok": cort_ok,
            "OK": OK}


def relatorio_pt(r):
    def _arr(a):
        return (f"{a['n']} phi {a['phi']:.1f} mm (As_ef={a['As_ef']*1e4:.2f} cm2)"
                if a and a.get("n") else "(detalhar)")
    L = ["VIGA DE CONCRETO ARMADO (ABNT NBR 6118:2014)",
         f"  Vao = {r['vao']:.2f} m ; secao {r['b']*100:.0f}x{r['h']*100:.0f} cm "
         f"(d={r['d']*100:.0f} cm) ; b_min 12 cm {'OK' if r['b_ok'] else 'REPROVA'}",
         f"  FLEXAO: w = {r['w']:.3f} kN/m (+p.proprio {r['w_self']:.3f}) ; "
         f"M_d = {r['M_d']:.2f} kN.m ; x/d = {r['x_d']:.3f} "
         f"{'OK' if r['ok_dominio'] else 'FORA DO DOMINIO'}"
         + ('' if r['sec_ok'] else ' ; SECAO INSUFICIENTE'),
         f"    As,inf = {r['As_inf_cm2']:.2f} cm2 (min {r['As_min_cm2']:.2f}) -> {_arr(r['arr_inf'])}",
         *( [f"  APOIO (M-, continua): M_d- = {r['M_d_neg']:.2f} kN.m ; "
            f"As,sup = {r['As_sup_cm2']:.2f} cm2 -> {_arr(r['arr_sup'])}"]
            if r['continua'] else
            [f"  As,sup construtiva = {r['As_sup_cm2']:.2f} cm2 -> {_arr(r['arr_sup'])}"] ),
         f"  CORTANTE (17.4): V_d = {r['V_d']:.2f} kN ; VRd2 = {r['VRd2']:.1f} (u={r['u_biela']:.3f}) ; "
         f"VRd3_min = {r['VRd3_min']:.1f} (u={r['u_cort']:.3f}) ; "
         f"{'OK' if r['cort_ok'] else 'REPROVA'}",
         f"    estribos phi {r['phi_estribo_mm']:.1f} mm s_max {r['s_estribo_max']*1000:.0f} mm ; "
         f"lb,nec = {r['ancoragem']['lb_nec_mm']:.0f} mm",
         f"  FLECHA (ELS, {r['els']['criterio']}): {r['els']['d_comparado_mm']:.1f} mm <= "
         f"{r['els']['lim_mm']:.1f} mm ; {'OK' if r['els']['ok'] else 'REPROVA (aumentar h)'}"
         + (' ; secao fissurada' if r['els']['fissura'] else ''),
         f"  RESULTADO: {'APROVADA' if r['OK'] else 'REPROVADA'}",
         "  [A CONFIRMAR: carga da viga (cobertura/parede) e vao do modelo.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # Afericao da FLEXAO contra Araujo (Curso de Concreto Armado 2, Ex.1):
    # viga 15x40, d=36, C20, Md=42 kN.m -> As=2,98 cm2, x=9 cm. Aqui damos M_d direto.
    r = verifica_viga({"vao": 4.0, "b": 0.15, "h": 0.40, "fck": 20e3, "fyk": 500e3,
                       "cobrimento": 0.04, "phi_estribo_mm": 0.0, "phi_barra_mm": 0.0,
                       "M_d": 42.0})
    assert abs(r["d"] - 0.36) < 1e-9, r["d"]
    assert abs(r["As_flex_cm2"] - 2.98) < 0.03, r["As_flex_cm2"]
    assert abs(r["x_d"] * r["d"] * 100 - 9.0) < 0.2, r["x_d"]
    # cortante: VRd2 > 0 e utilizacao coerente
    assert r["cort_ok"], (r["u_biela"], r["u_cort"])
    # ELS de viga visivel: limite L/250
    assert abs(r["els"]["lim_mm"] - 4.0 / 250.0 * 1000) < 1e-6, r["els"]
    # viga esbelta sob carga alta reprova ELS ou ELU e a escada sobe h
    ruim = {"vao": 8.0, "b": 0.15, "h": 0.30, "fck": 25e3, "fyk": 500e3, "q": 30.0}
    rr = verifica_viga(ruim)
    rd = dimensiona_viga(ruim)
    assert rd["h"] >= rr["h"], (rr["h"], rd["h"])
    # viga que suporta alvenaria usa o criterio L/500;10mm
    ralv = verifica_viga({"vao": 5.0, "b": 0.20, "h": 0.50, "fck": 25e3, "fyk": 500e3,
                          "q": 5.0, "suporta_alvenaria": True, "q_alvenaria": 8.0})
    assert "alvenaria" in ralv["els"]["criterio"], ralv["els"]
    print("viga_concreto self-test PASSED (flexao aferida vs Araujo)")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(verifica_viga({"vao": 6.0, "b": 0.20, "h": 0.50,
              "fck": 25e3, "fyk": 500e3, "q": 12.0})))
