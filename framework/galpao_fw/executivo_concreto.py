# ============================================================================
# executivo_concreto.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Produz o EXECUTIVO do galpao de concreto: (1) o QUADRO DE ACO / lista de
# dobramento (a "ferragem" quantitativa que os desenhos de armacao anotam) e
# (2) o MEMORIAL de calculo completo. Reaproveita:
#   - fundacao_sapata.comprimento_ancoragem (NBR 6118 9.4) p/ o gancho/ancoragem;
#   - fundacao_sapata.quadro_dobramento (peso = n*L*0,00617*phi^2);
#   - os relatorio_pt de vento/viga/pilar/sapata para o memorial.
# Escopo P5: os DADOS de fabricacao (barras, estribos, comprimentos, pesos, resumo
# de consumo kg/m2 e kg/m3). O desenho grafico de FORMAS+ARMACAO (TechDraw) e a
# camada de renderizacao (equivalente as pranchas PE do aco) e segue como proximo
# passo, sobre estes dados. Unidades: m, kN. Saidas em portugues.
# ============================================================================
"""Executivo do galpao de concreto: quadro de aco (lista de dobramento) + memorial.
Reaproveita ancoragem/peso da fundacao e os relatorios dos modulos de calculo."""

from __future__ import annotations

import math

import fundacao_sapata as fs

_BITOLAS_LONG = [10.0, 12.5, 16.0, 20.0, 25.0]      # bitolas longitudinais (mm)
PESO_ML = 0.00617                                   # kg/m por mm^2 de bitola (7850 kg/m3)


def _peso(phi_mm, n, L_m):
    return round(n * L_m * PESO_ML * phi_mm ** 2, 2)


def _barras_para_As(As_cm2, n_min=4, par=True):
    """Escolhe (phi, n) tal que n*area >= As, n>=n_min (e par, p/ pilar). Prefere a
    MENOR bitola que resolve com n razoavel (<= 12)."""
    if As_cm2 <= 0:
        return _BITOLAS_LONG[0], n_min
    for phi in _BITOLAS_LONG:
        a1 = math.pi * (phi / 10.0) ** 2 / 4.0      # cm2 por barra
        n = max(n_min, math.ceil(As_cm2 / a1))
        if par and n % 2:
            n += 1
        if n <= 12:
            return phi, n
    phi = _BITOLAS_LONG[-1]
    a1 = math.pi * (phi / 10.0) ** 2 / 4.0
    n = max(n_min, math.ceil(As_cm2 / a1))
    return phi, n + (n % 2 if par else 0)


def _estribo_comprimento(b, h, cob, phi_est_mm):
    """Comprimento de UM estribo fechado retangular (m): perimetro interno + 2 ganchos
    (10*phi). NBR 6118 18.3.3."""
    perim = 2.0 * ((b - 2 * cob) + (h - 2 * cob))
    ganchos = 2.0 * 10.0 * phi_est_mm / 1000.0
    return round(perim + ganchos, 3)


def quadro_de_aco(r):
    """Monta o quadro de aco do galpao (r = galpao_concreto.rodar()). Retorna lista
    de posicoes {elemento, pos, phi_mm, n, comprimento_m, peso_kg} agregadas pela
    QUANTIDADE de elementos iguais (n_pilares, n_vigas, n_sapatas)."""
    sp = r["spec"]
    n_port = sp["n_porticos"]; H = sp["H"]; vao = sp["vao"]
    fckM = sp["fck_MPa"]; fyk = 500.0
    n_pilares = n_port * 2
    n_vigas = n_port
    n_sapatas = n_port * 2
    q = []

    # -------- PILAR (longitudinal + estribos) --------
    pil = r["pilar"]; hx = pil["hx"]; hy = pil["hy"]; cob = 0.03
    phi_l, n_l = _barras_para_As(pil["As_cm2"], n_min=4, par=True)
    anc = fs.comprimento_ancoragem(phi_l, fckM, fyk, gancho=True)
    L_arr = anc["lb_nec_mm"] / 1000.0               # ancoragem na sapata
    L_bar = H + L_arr + 0.6                          # H + ancoragem + arranque calice
    q.append({"elemento": "Pilar", "pos": "N1 (long.)", "phi_mm": phi_l,
              "n": n_l * n_pilares, "comprimento_m": round(L_bar, 2),
              "peso_kg": _peso(phi_l, n_l * n_pilares, L_bar)})
    phi_e = pil.get("phi_estribo_mm", 5.0)
    s_e = 0.15                                        # estribo c/15 cm (usual pilar)
    n_e = (math.ceil(H / s_e) + 1)
    Le = _estribo_comprimento(hy, hx, cob, phi_e)
    q.append({"elemento": "Pilar", "pos": "N2 (estribo)", "phi_mm": phi_e,
              "n": n_e * n_pilares, "comprimento_m": Le,
              "peso_kg": _peso(phi_e, n_e * n_pilares, Le)})

    # -------- VIGA DE COBERTURA (inf + sup + estribos) --------
    vg = r["viga"]; b = vg["b"]; h = vg["h"]
    for pos, arr in (("N3 (inf.)", vg["arr_inf"]), ("N4 (sup.)", vg["arr_sup"])):
        if arr and arr.get("n"):
            phi = arr["phi"]; n = arr["n"]
            Lb = vao + 2 * (fs.comprimento_ancoragem(phi, fckM, fyk)["lb_nec_mm"] / 1000.0)
            q.append({"elemento": "Viga cob.", "pos": pos, "phi_mm": phi,
                      "n": n * n_vigas, "comprimento_m": round(Lb, 2),
                      "peso_kg": _peso(phi, n * n_vigas, Lb)})
    phi_ev = vg.get("phi_estribo_mm", 5.0)
    s_ev = min(vg.get("s_estribo_max", 0.2), 0.2)
    n_ev = math.ceil(vao / s_ev) + 1
    Lev = _estribo_comprimento(b, h, 0.03, phi_ev)
    q.append({"elemento": "Viga cob.", "pos": "N5 (estribo)", "phi_mm": phi_ev,
              "n": n_ev * n_vigas, "comprimento_m": Lev,
              "peso_kg": _peso(phi_ev, n_ev * n_vigas, Lev)})

    # -------- SAPATA (malha inferior 2 direcoes) --------
    sap = r["sapata"]
    rB = sap.get("parte_B")
    if sap["aprovado"] and rB:
        B, L, hf = sap["aprovado"][0], sap["aprovado"][1], sap["aprovado"][2]
        # armadura de flexao da sapata nas 2 direcoes (dimensiona_sapata_B):
        # flexao_L -> barras ao longo de L ; flexao_B -> barras ao longo de B.
        for pos, flex, comp in (("N6 (malha // L)", rB.get("flexao_L"), L),
                                ("N7 (malha // B)", rB.get("flexao_B"), B)):
            arr = (flex or {}).get("barras")
            if arr and arr.get("n"):
                phi = arr["phi"]; n = arr["n"]
                Lb = comp - 2 * 0.04 + 0.30          # cobre a dimensao - cob + dobras
                q.append({"elemento": "Sapata", "pos": pos, "phi_mm": phi,
                          "n": n * n_sapatas, "comprimento_m": round(Lb, 2),
                          "peso_kg": _peso(phi, n * n_sapatas, Lb)})
    return q


def resumo_aco(r, quadro=None):
    """Resumo de consumo de aco: peso total, peso por bitola e taxas kg/m2 (area
    construida) e kg/m3 (volume de concreto estimado)."""
    q = quadro if quadro is not None else quadro_de_aco(r)
    sp = r["spec"]
    total = round(sum(x["peso_kg"] for x in q), 1)
    por_bitola = {}
    for x in q:
        por_bitola[x["phi_mm"]] = round(por_bitola.get(x["phi_mm"], 0.0) + x["peso_kg"], 1)
    area = sp["vao"] * sp["comprimento"]
    # volume de concreto aproximado: pilares + vigas + sapatas
    n_port = sp["n_porticos"]; H = sp["H"]
    pil = r["pilar"]; vg = r["viga"]
    vol_pil = pil["hx"] * pil["hy"] * H * n_port * 2
    vol_vig = vg["b"] * vg["h"] * sp["vao"] * n_port
    vol_sap = 0.0
    if r["sapata"]["aprovado"]:
        B, L, hf = r["sapata"]["aprovado"][:3]
        vol_sap = B * L * hf * n_port * 2
    vol = vol_pil + vol_vig + vol_sap
    return {"peso_total_kg": total, "por_bitola_kg": por_bitola,
            "area_m2": round(area, 1), "volume_concreto_m3": round(vol, 2),
            "taxa_kg_m2": round(total / area, 1) if area else 0.0,
            "consumo_kg_m3": round(total / vol, 1) if vol else 0.0}


def relatorio_quadro_pt(r):
    q = quadro_de_aco(r); res = resumo_aco(r, q)
    L = ["QUADRO DE ACO - GALPAO DE CONCRETO (NBR 6118)",
         "  Elemento    | Pos          | phi(mm) |   n  | comp(m) | peso(kg)",
         "  " + "-" * 62]
    for x in q:
        L.append(f"  {x['elemento']:<11} | {x['pos']:<12} | {x['phi_mm']:>6.1f}  | "
                 f"{x['n']:>4} | {x['comprimento_m']:>6.2f}  | {x['peso_kg']:>7.1f}")
    L += ["  " + "-" * 62,
          f"  ACO TOTAL: {res['peso_total_kg']:.1f} kg ; area {res['area_m2']:.0f} m2 ; "
          f"volume concreto {res['volume_concreto_m3']:.1f} m3",
          f"  TAXAS: {res['taxa_kg_m2']:.1f} kg/m2 (area) ; "
          f"consumo {res['consumo_kg_m3']:.1f} kg/m3 de concreto",
          "  [A CONFIRMAR: comprimentos de emenda/arranque conforme detalhamento final.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def memorial(r):
    """Memorial de calculo completo do galpao de concreto: compoe os relatorios de
    cada disciplina (vento, viga, pilar, sapata) + o quadro de aco."""
    import vento_nbr6123 as vento
    import viga_concreto as vc
    import pilar_concreto as pc
    import galpao_concreto as gc
    # a viga pode ser CA ou PROTENDIDA (vao grande) - usa o relatorio correspondente
    if r.get("viga_prot"):
        import viga_protendida as vp
        viga_rel = vp.relatorio_pt(r["viga_prot"])
    else:
        viga_rel = vc.relatorio_pt(r["viga"])
    partes = ["=" * 66,
              "MEMORIAL DE CALCULO - GALPAO DE CONCRETO PRE-MOLDADO",
              "=" * 66, "",
              gc.relatorio_pt(r), "",
              "-- VENTO " + "-" * 57, vento.relatorio_pt(r["vento"]), "",
              "-- VIGA DE COBERTURA " + "-" * 45, viga_rel, "",
              "-- PILAR " + "-" * 57, pc.relatorio_pt(r["pilar"]), "",
              "-- QUADRO DE ACO " + "-" * 49, relatorio_quadro_pt(r)]
    return "\n".join(partes)


def _selftest():
    import galpao_concreto as gc
    r = gc.rodar({"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
                  "v0": 40.0, "cat": "IV", "classe": "B", "G_roof": 0.30, "Q_roof": 0.25,
                  "fck": 30e3, "sigma_solo_adm": 250.0})
    q = quadro_de_aco(r)
    assert any(x["elemento"] == "Pilar" for x in q)
    assert any(x["elemento"] == "Viga cob." for x in q)
    assert all(x["peso_kg"] > 0 and x["n"] > 0 for x in q), q
    res = resumo_aco(r, q)
    assert res["peso_total_kg"] > 0 and res["taxa_kg_m2"] > 0
    # consumo de aco de galpao de concreto: tipicamente 60-140 kg/m3 (ordem de grandeza)
    assert 20.0 < res["consumo_kg_m3"] < 300.0, res["consumo_kg_m3"]
    txt = memorial(r)
    assert "MEMORIAL DE CALCULO" in txt and "QUADRO DE ACO" in txt
    print("executivo_concreto self-test PASSED ; aco total %.0f kg (%.1f kg/m2, %.0f kg/m3)"
          % (res["peso_total_kg"], res["taxa_kg_m2"], res["consumo_kg_m3"]))


if __name__ == "__main__":
    import sys
    import galpao_concreto as gc
    r = gc.rodar({"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
                  "v0": 40.0, "cat": "IV", "classe": "B", "G_roof": 0.30, "Q_roof": 0.25,
                  "fck": 30e3, "sigma_solo_adm": 250.0})
    if "--selftest" in sys.argv:
        _selftest()
    elif "--memorial" in sys.argv:
        print(memorial(r))
    else:
        print(relatorio_quadro_pt(r))
