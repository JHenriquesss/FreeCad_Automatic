# ============================================================================
# galpao_climatizacao.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Vertical de CLIMATIZACAO (HVAC) do galpao: eleva o modulo de calculo
# climatizacao_nbr16401 (carga termica + capacidade TR/kW) a uma disciplina do
# turnkey, com ROTA DE DUTOS e membros_bim -> os dutos entram no MODELO FEDERADO e
# no CLASH. Dutos de ar sao a fonte classica de interferencia de obra (cruzam vigas/
# tercas/eletrocalhas), entao a coordenacao passa a achar conflitos REAIS a revisar.
#   - rodar(spec) -> capacidade (climatizacao_nbr16401) + vazao de insuflamento +
#     secao do duto principal (dimensiona_duto) + gates.
#   - membros_bim(r) -> duto TRONCO ao longo do comprimento (no forro), RAMAIS
#     transversais e a UTA (unidade de tratamento de ar). Frame comum do turnkey
#     (X=comprimento, Y=largura, Z=altura; mm). Secao de BARRA em metros.
# A capacidade e as vazoes vem da NBR 16401 (modulo de calculo aferido). A GEOMETRIA
# do duto e' de COORDENACAO (rota/interferencia), com dT de insuflamento e velocidade
# [A CONFIRMAR] contra a NBR 16401-1 - ver climatizacao_nbr16401.
# ============================================================================
"""Vertical de climatizacao (HVAC) do galpao: capacidade (NBR 16401) + rota de dutos
+ membros_bim (tronco/ramais/UTA) para o modelo federado e o clash do turnkey."""

from __future__ import annotations

import climatizacao_nbr16401 as cl

N_RAMAIS_PADRAO = 4               # ramais transversais ao longo do comprimento
RECUO_DUTO_TETO_MM = 400.0        # duto abaixo do forro/beiral (onde cruza a estrutura)


def rodar(spec):
    """Dimensiona a climatizacao e a rota de dutos do galpao.
    spec: {geometria{L,W,H} (m), tipo(='galpao'), metodo, n_pessoas, dT_ins(opc),
           vel_duto(opc), n_ramais(opc), ...componentes de carga}.
    Retorna {geometria, climatizacao, duto, V_insuflamento_m3h, gates, reprovados, ATENDE}."""
    geo = spec.get("geometria") or {}
    if not all(k in geo for k in ("L", "W", "H")):
        raise ValueError("[A CONFIRMAR] geometria {L,W,H} (m) obrigatoria p/ climatizacao.")
    L = float(geo["L"]); W = float(geo["W"]); H = float(geo["H"])
    if L <= 0 or W <= 0 or H <= 0:
        raise ValueError("[A CONFIRMAR] geometria do galpao invalida (L,W,H > 0); "
                         "recebido L=%s W=%s H=%s." % (L, W, H))
    area = L * W

    caso = {"area_m2": area, "tipo": spec.get("tipo", "galpao"),
            "metodo": spec.get("metodo", "estimativa")}
    for k in ("n_pessoas", "atividade", "COP", "envoltoria",
              "P_iluminacao_W", "P_equipamentos_W", "dT_ar_ext"):
        if spec.get(k) is not None:
            caso[k] = spec[k]
    clm = cl.dimensiona_climatizacao(caso)

    V_ins = cl.vazao_insuflamento(clm["capacidade_kW"] * 1000.0,
                                  float(spec.get("dT_ins", cl.DT_INSUFLAMENTO_K)))
    duto = cl.dimensiona_duto(V_ins, float(spec.get("vel_duto", cl.VEL_DUTO_PRINCIPAL_MS)),
                              classe_pa=int(spec.get("classe_pressao_pa",
                                                     cl.CLASSE_PRESSAO_PADRAO_PA)))

    gates = {
        "capacidade": {"TR": clm["capacidade_TR"], "kW": clm["capacidade_kW"],
                       "BTU_h": clm["capacidade_BTU_h"], "OK": clm["OK"]},
        "duto_principal": {"largura_m": duto["largura_m"], "altura_m": duto["altura_m"],
                           "vel_ms": duto["vel_ms"], "vel_max_ms": duto["vel_max_ms"],
                           "classe_pa": duto["classe_pa"], "vazao_m3h": round(V_ins, 1),
                           # OK: secao valida E velocidade <= max da classe (NBR 16401-1 Tab.1)
                           "OK": duto["area_m2"] > 0 and duto["vel_OK"]},
    }
    r = {"geometria": {"L": L, "W": W, "H": H}, "climatizacao": clm, "duto": duto,
         "V_insuflamento_m3h": round(V_ins, 1), "n_ramais": int(spec.get("n_ramais",
                                                                         N_RAMAIS_PADRAO)),
         "gates": gates}
    r["reprovados"] = [k for k, g in gates.items() if not g["OK"]]
    r["ATENDE"] = len(r["reprovados"]) == 0
    return r


def membros_bim(r):
    """Modelo neutro dos dutos de HVAC (frame comum do turnkey; mm; secao de barra em m).
    Duto TRONCO no forro ao longo do comprimento (cruza as vigas/tercas), RAMAIS
    transversais e a UTA (caixa). Lista vazia sem geometria."""
    geo = r.get("geometria") or {}
    if not all(k in geo for k in ("L", "W", "H")):
        return []
    L = geo["L"] * 1000.0; W = geo["W"] * 1000.0; H = geo["H"] * 1000.0     # mm
    du = r["duto"]
    bf = du["largura_m"]; d = du["altura_m"]                                # secao (m)
    ze = H - RECUO_DUTO_TETO_MM                                             # cota do tronco
    sec_tronco = {"forma": "RECT", "bf": bf, "d": d}
    M = []
    # TRONCO: ao longo do comprimento, no eixo central (Y = W/2)
    M.append({"tipo": "Duct", "perfil": "Tronco %.2fx%.2f m" % (bf, d), "marca": "DUTO-T",
              "secao": sec_tronco, "p1": [0.0, W / 2.0, ze], "p2": [L, W / 2.0, ze],
              "material": "Aco galvanizado"})
    # RAMAIS transversais (metade da secao do tronco), distribuidos no comprimento
    n = max(0, int(r.get("n_ramais", N_RAMAIS_PADRAO)))
    bf_r, d_r = bf / 2.0, d
    zr = ze - (d * 1000.0)                                                  # logo abaixo do tronco
    for i in range(n):
        x = (i + 0.5) * L / n
        M.append({"tipo": "Duct", "perfil": "Ramal", "marca": "DUTO-R%d" % (i + 1),
                  "secao": {"forma": "RECT", "bf": bf_r, "d": d_r},
                  "p1": [x, 0.0, zr], "p2": [x, W, zr], "material": "Aco galvanizado"})
    # UTA (unidade de tratamento de ar): caixa junto a uma empena, no piso
    M.append({"tipo": "AirHandler", "perfil": "UTA", "marca": "UTA1",
              "dims": [2000.0, 1500.0, 1800.0], "centro": [-1500.0, W / 2.0, 900.0],
              "material": "Aco"})
    return M


def emitir_bim(r, path, nome="GalpaoClimatizacao"):
    """Emite o IFC4 dos dutos de HVAC (via ifc_emit puro). None sem geometria/ifcopenshell."""
    import ifc_emit
    if not ifc_emit.disponivel():
        return None
    membros = membros_bim(r)
    if not membros:
        return None
    return ifc_emit.emitir_ifc(membros, path, nome=nome, secao_em_metros=True)


def relatorio_pt(r):
    g = r["gates"]
    cap = g["capacidade"]; dp = g["duto_principal"]
    L = ["CLIMATIZACAO - GALPAO (NBR 16401)",
         "  Capacidade: %.1f TR (%.1f kW ; %.0f BTU/h)" % (cap["TR"], cap["kW"],
                                                           cap["BTU_h"]),
         "  Vazao de insuflamento: %.0f m3/h" % dp["vazao_m3h"],
         "  Duto principal: %.2f x %.2f m @ %.1f m/s (max %.1f m/s classe %d Pa, "
         "NBR 16401-1 Tab.1) ; %d ramais" % (dp["largura_m"], dp["altura_m"],
         dp["vel_ms"], dp["vel_max_ms"], dp["classe_pa"], r.get("n_ramais",
                                                                N_RAMAIS_PADRAO)),
         "  RESULTADO: %s" % ("ATENDE" if r["ATENDE"] else "REPROVA -> "
                              + ", ".join(r["reprovados"]))]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    r = rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "tipo": "galpao"})
    # galpao 800 m2 -> ~33,3 TR (estimativa) ; duto principal dimensionado
    assert abs(r["gates"]["capacidade"]["TR"] - 33.33) < 0.1
    assert r["duto"]["largura_m"] > 0 and r["duto"]["altura_m"] > 0
    assert r["gates"]["duto_principal"]["largura_m"] == r["duto"]["largura_m"]
    assert r["ATENDE"] is True
    mb = membros_bim(r)
    tipos = {}
    for m in mb:
        tipos[m["tipo"]] = tipos.get(m["tipo"], 0) + 1
    assert tipos["Duct"] == 1 + r["n_ramais"] and tipos["AirHandler"] == 1
    # tronco corre no comprimento (40 m -> 40000 mm), secao em metros
    tronco = next(m for m in mb if m["marca"] == "DUTO-T")
    assert tronco["p2"][0] == 40000.0 and tronco["secao"]["bf"] == r["duto"]["largura_m"]
    # geometria invalida -> ValueError limpo
    import pytest
    with pytest.raises(ValueError):
        rodar({"geometria": {"L": 0, "W": 20, "H": 6}})
    print(relatorio_pt(r))
    print("galpao_climatizacao self-test PASSED")


if __name__ == "__main__":
    _selftest()
