# ============================================================================
# fotovoltaico.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Dimensiona o SISTEMA FOTOVOLTAICO na cobertura do galpao (geracao distribuida,
# on-grid): a cobertura e' a usina natural. Da AREA de telhado disponivel deriva a
# POTENCIA instalavel, a GERACAO de energia e o quanto do CONSUMO ela compensa, com
# o numero de modulos e inversores.
#   - potencia_instalavel: P_kWp = area_util . densidade_kWp_m2 (modulos modernos
#     ~0,18 kWp/m2 de area de modulo; aproveitamento do telhado desconta sombras/
#     caminhos/orientacao).
#   - geracao: E = P_kWp . HSP . PR . dias  (metodo consagrado, CRESESB). HSP =
#     horas de sol pico do SITIO (irradiacao diaria media, kWh/m2/dia) - DADO DE
#     SITIO (A CONFIRMAR: CRESESB/INPE p/ a cidade). PR = performance ratio (~0,78,
#     perdas de temperatura/cabeamento/inversor).
#   - n_modulos / n_inversores: por potencia de modulo (Wp) e do inversor (kW), com
#     FDI (fator de dimensionamento do inversor) tipico 0,75-1,0.
#   - dimensiona_fv: limita a potencia pelo MENOR entre o alvo (compensar o consumo)
#     e o teto de area; devolve geracao, cobertura do consumo (%), area usada.
# Refs: NBR 16690 (instalacoes eletricas de arranjos FV) e ANEEL REN 1000/2023
# (geracao distribuida / compensacao). Specs de modulo/inversor = CATALOGO
# (A CONFIRMAR). STATELESS. Unidades: m2, kWp, kWh, V.
# ============================================================================
"""Sistema fotovoltaico na cobertura (on-grid): area -> potencia -> geracao ->
compensacao do consumo. HSP e catalogo A CONFIRMAR. STATELESS."""

from __future__ import annotations

import math

DENS_KWP_M2 = 0.18              # densidade de potencia (kWp por m2 de modulo, ~550 Wp)
APROVEITAMENTO = 0.70          # fracao util do telhado (sombra/caminhos/orientacao)
PR_PADRAO = 0.78               # performance ratio tipico (perdas do sistema)
P_MODULO_WP = 550.0            # potencia do modulo (Wp) - CATALOGO (A CONFIRMAR)
AREA_MODULO_M2 = 2.6           # area de um modulo de ~550 Wp (~2,3 x 1,13 m)
FDI = 0.85                     # fator de dimensionamento do inversor (Pinv/Pfv)
DIAS_MES = 30.4                # dias medios por mes


def potencia_instalavel(area_m2, aproveitamento=APROVEITAMENTO, densidade=DENS_KWP_M2):
    """Potencia FV instalavel (kWp) numa area de telhado. area_util = area x
    aproveitamento; P = area_util x densidade."""
    if area_m2 <= 0:
        raise ValueError("area de cobertura invalida: %r" % area_m2)
    area_util = area_m2 * aproveitamento
    return area_util * densidade


def geracao(P_kWp, HSP, PR=PR_PADRAO):
    """Energia gerada (metodo CRESESB): E = P.HSP.PR.dias. HSP = horas de sol pico
    (kWh/m2/dia) do sitio. Retorna dict com diaria/mensal/anual (kWh)."""
    if HSP <= 0:
        raise ValueError("[A CONFIRMAR] HSP (irradiacao) do sitio nao informado")
    e_dia = P_kWp * HSP * PR
    return {"kwh_dia": e_dia, "kwh_mes": e_dia * DIAS_MES, "kwh_ano": e_dia * 365.0,
            "HSP": HSP, "PR": PR}


def n_modulos(P_kWp, P_modulo_Wp=P_MODULO_WP):
    """Numero de modulos = teto(P_kWp*1000 / P_modulo_Wp)."""
    return int(math.ceil(P_kWp * 1000.0 / P_modulo_Wp))


def n_inversores(P_kWp, P_inversor_kW, fdi=FDI):
    """Numero de inversores: a potencia total dos inversores >= P_kWp*fdi
    (subdimensionamento controlado do inversor). teto(P_kWp*fdi / P_inv)."""
    if P_inversor_kW <= 0:
        raise ValueError("potencia do inversor invalida")
    return max(1, int(math.ceil(P_kWp * fdi / P_inversor_kW)))


def dimensiona_fv(caso):
    """Dimensiona o sistema FV. caso:
      'area_cobertura_m2' : area de telhado disponivel (m2). OBRIGATORIO.
      'HSP'               : horas de sol pico do sitio (kWh/m2/dia) [A CONFIRMAR].
      'consumo_kwh_mes'   : consumo a compensar (opc). Alternativa: 'demanda_kW' +
                            'horas_dia' -> consumo estimado.
      'aproveitamento','PR','P_modulo_Wp','P_inversor_kW','densidade' : opcionais.
    Limita a potencia pelo MENOR entre (alvo p/ compensar o consumo) e (teto de
    area). Retorna potencia, geracao, cobertura do consumo, modulos e inversores."""
    area = caso.get("area_cobertura_m2")
    if not area or area <= 0:
        raise ValueError("[A CONFIRMAR] area_cobertura_m2 nao informada")
    HSP = caso.get("HSP")
    apr = caso.get("aproveitamento", APROVEITAMENTO)
    PR = caso.get("PR", PR_PADRAO)
    dens = caso.get("densidade", DENS_KWP_M2)
    P_mod = caso.get("P_modulo_Wp", P_MODULO_WP)
    P_inv = caso.get("P_inversor_kW", 75.0)

    P_teto_area = potencia_instalavel(area, apr, dens)

    # consumo alvo (kWh/mes): direto ou por demanda x horas
    consumo = caso.get("consumo_kwh_mes")
    if consumo is None and caso.get("demanda_kW"):
        horas = caso.get("horas_dia", 8.0)
        consumo = caso["demanda_kW"] * horas * DIAS_MES

    if HSP is None:
        return {"OK": False, "motivo": "[A CONFIRMAR] HSP (irradiacao do sitio) - "
                "obter no CRESESB/INPE para a cidade.",
                "potencia_teto_area_kWp": round(P_teto_area, 1)}

    # potencia p/ compensar 100% do consumo (se dado): P = consumo_mes/(HSP.PR.dias)
    P_alvo = None
    if consumo:
        P_alvo = consumo / (HSP * PR * DIAS_MES)

    P_kWp = P_teto_area if P_alvo is None else min(P_teto_area, P_alvo)
    limitado_por = ("area (telhado nao comporta 100% do consumo)"
                    if (P_alvo is not None and P_teto_area < P_alvo) else
                    ("consumo (alvo)" if P_alvo is not None else "area (sem consumo alvo)"))

    ger = geracao(P_kWp, HSP, PR)
    nmod = n_modulos(P_kWp, P_mod)
    ninv = n_inversores(P_kWp, P_inv)
    area_usada = nmod * (caso.get("area_modulo_m2", AREA_MODULO_M2))
    cobertura = (100.0 * ger["kwh_mes"] / consumo) if consumo else None

    return {"OK": True, "potencia_kWp": round(P_kWp, 1),
            "potencia_teto_area_kWp": round(P_teto_area, 1),
            "limitado_por": limitado_por,
            "geracao": {"kwh_dia": round(ger["kwh_dia"], 1),
                        "kwh_mes": round(ger["kwh_mes"], 1),
                        "kwh_ano": round(ger["kwh_ano"], 1),
                        "HSP": HSP, "PR": PR},
            "consumo_kwh_mes": round(consumo, 1) if consumo else None,
            "cobertura_consumo_pct": round(cobertura, 1) if cobertura else None,
            "n_modulos": nmod, "P_modulo_Wp": P_mod,
            "n_inversores": ninv, "P_inversor_kW": P_inv,
            "area_modulos_m2": round(area_usada, 1),
            "area_cobertura_m2": area, "aproveitamento": apr,
            # fator de emissao medio do SIN ~0,0817 tCO2/MWh (A CONFIRMAR ano-base MCTI)
            "co2_evitado_ton_ano": round(ger["kwh_ano"] / 1000.0 * 0.0817, 2),
            "norma": "Geracao: E=P.HSP.PR (CRESESB); NBR 16690 (arranjo FV); ANEEL "
                     "REN 1000/2023 (GD/compensacao). HSP e catalogo A CONFIRMAR."}


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def grafico_svg(r):
    """Grafico do sistema FV: barras geracao x consumo (kWh/mes) + resumo. SVG puro,
    XML-valido (parse). r = saida de dimensiona_fv."""
    W, H = 900, 560

    def _t(x, y, s, size=13, anchor="middle", weight="normal", color="#111"):
        return (f'<text x="{x:.0f}" y="{y:.0f}" font-family="Arial" font-size="{size}"'
                f' text-anchor="{anchor}" font-weight="{weight}" fill="{color}">'
                f'{_esc(s)}</text>')

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Arial">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           _t(W / 2, 42, "SISTEMA FOTOVOLTAICO NA COBERTURA", 21, weight="bold")]
    if not r.get("OK"):
        out.append(_t(W / 2, H / 2, r.get("motivo", "FV nao dimensionado"), 14,
                      color="#b00"))
        out.append("</svg>"); return "\n".join(out)

    ger = r["geracao"]["kwh_mes"]; cons = r.get("consumo_kwh_mes") or ger
    base = max(ger, cons) or 1.0
    bx, by, bw, bh = 130, 120, 150, 300
    for i, (lbl, val, cor) in enumerate([("Geracao FV", ger, "#f39c12"),
                                         ("Consumo", cons, "#3498db")]):
        x = bx + i * 220
        hh = bh * val / base
        out.append(f'<rect x="{x}" y="{by + bh - hh:.0f}" width="{bw}" height="{hh:.0f}" '
                   f'fill="{cor}"/>')
        out.append(_t(x + bw / 2, by + bh - hh - 10, "%.0f kWh/mes" % val, 13, weight="bold"))
        out.append(_t(x + bw / 2, by + bh + 24, lbl, 14))
    out.append(f'<line x1="{bx-20}" y1="{by+bh}" x2="{bx+2*220}" y2="{by+bh}" '
               f'stroke="#111" stroke-width="1.5"/>')

    # resumo (direita)
    qx = 590
    linhas = [("Potencia instalada", "%.1f kWp" % r["potencia_kWp"]),
              ("Modulos", "%d x %.0f Wp" % (r["n_modulos"], r["P_modulo_Wp"])),
              ("Inversores", "%d x %.0f kW" % (r["n_inversores"], r["P_inversor_kW"])),
              ("Geracao anual", "%.0f kWh/ano" % r["geracao"]["kwh_ano"]),
              ("Cobertura do consumo", ("%.0f%%" % r["cobertura_consumo_pct"]
                                        if r.get("cobertura_consumo_pct") else "-")),
              ("Limitado por", r["limitado_por"][:22]),
              ("Area de modulos", "%.0f m2 / %.0f m2" % (r["area_modulos_m2"],
                                                         r["area_cobertura_m2"])),
              ("HSP (sitio)", "%.1f kWh/m2.dia" % r["geracao"]["HSP"]),
              ("CO2 evitado", "%.1f t/ano" % r["co2_evitado_ton_ano"])]
    out.append(f'<rect x="{qx}" y="110" width="270" height="{28*len(linhas)+40}" '
               f'fill="#fafafa" stroke="#111" stroke-width="1.2"/>')
    out.append(_t(qx + 135, 136, "RESUMO DO SISTEMA", 14, weight="bold"))
    for i, (k, v) in enumerate(linhas):
        yy = 162 + i * 28
        out.append(_t(qx + 12, yy, k, 12, anchor="start", color="#333"))
        out.append(_t(qx + 258, yy, v, 12, anchor="end", weight="bold"))
    out.append(_t(W / 2, H - 20, "E = P.HSP.PR (CRESESB) | NBR 16690 / ANEEL REN "
                  "1000 | HSP e catalogo A CONFIRMAR", 11, color="#666"))
    out.append("</svg>")
    return "\n".join(out)


# ----------------------------------- selftest --------------------------------
def _selftest():
    # potencia instalavel: 1000 m2 x 0,7 x 0,18 = 126 kWp
    assert abs(potencia_instalavel(1000.0) - 126.0) < 1e-9

    # geracao: 100 kWp x 5 HSP x 0,78 = 390 kWh/dia
    g = geracao(100.0, 5.0)
    assert abs(g["kwh_dia"] - 390.0) < 1e-9
    assert abs(g["kwh_ano"] - 390.0 * 365) < 1e-6

    # n modulos: 100 kWp / 550 Wp = 182 modulos (teto)
    assert n_modulos(100.0) == math.ceil(100000.0 / 550.0)
    # n inversores: 100 kWp x 0,85 / 75 kW = 2 (teto)
    assert n_inversores(100.0, 75.0) == 2

    # dimensiona limitado por AREA (telhado pequeno, consumo alto)
    r = dimensiona_fv({"area_cobertura_m2": 500.0, "HSP": 5.0,
                       "consumo_kwh_mes": 100000.0})
    assert r["OK"] and r["limitado_por"].startswith("area")
    assert r["potencia_kWp"] == r["potencia_teto_area_kWp"]
    assert r["cobertura_consumo_pct"] < 100.0        # nao compensa 100%

    # dimensiona limitado por CONSUMO (telhado grande, consumo modesto)
    r2 = dimensiona_fv({"area_cobertura_m2": 2000.0, "HSP": 5.5,
                        "consumo_kwh_mes": 20000.0})
    assert r2["limitado_por"].startswith("consumo")
    assert abs(r2["cobertura_consumo_pct"] - 100.0) < 2.0   # ~compensa 100%
    assert r2["potencia_kWp"] < r2["potencia_teto_area_kWp"]

    # sem HSP -> A CONFIRMAR (nao inventa)
    assert dimensiona_fv({"area_cobertura_m2": 800.0}).get("OK") is False

    # consumo por demanda x horas
    r3 = dimensiona_fv({"area_cobertura_m2": 2000.0, "HSP": 5.0,
                        "demanda_kW": 50.0, "horas_dia": 8.0})
    assert r3["consumo_kwh_mes"] == round(50.0 * 8.0 * DIAS_MES, 1)

    # area invalida levanta
    try:
        dimensiona_fv({"area_cobertura_m2": 0, "HSP": 5.0}); assert False
    except ValueError:
        pass

    # grafico SVG e' XML valido (parse)
    from xml.dom.minidom import parseString
    svg = grafico_svg(r2)
    assert svg.startswith("<svg") and "SISTEMA FOTOVOLTAICO" in svg
    parseString(svg.encode("utf-8"))
    parseString(grafico_svg({"OK": False, "motivo": "x"}).encode("utf-8"))
    return True


if __name__ == "__main__":
    _selftest()
    import json
    demo = dimensiona_fv({"area_cobertura_m2": 800.0, "HSP": 5.2,
                          "consumo_kwh_mes": 18000.0, "P_inversor_kW": 75.0})
    print(json.dumps(demo, indent=2, ensure_ascii=False))
    print("selftest OK")
