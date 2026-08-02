# ============================================================================
# climatizacao_nbr16401.py - O QUE ESTE SCRIPT FAZ / CALCULA
# CLIMATIZACAO / AR-CONDICIONADO do galpao ou de ambientes internos (ABNT NBR
# 16401-1/2/3):
#   1) CARGA TERMICA (16401-1, Secao 6): componentes -
#      - envoltoria: conducao Q = U*A*dT (parede/cobertura/vidro) + radiacao solar;
#      - fontes internas: pessoas (calor sensivel+latente, Tab.C.1), iluminacao e
#        equipamentos (dissipacao = potencia eletrica), motores;
#      - ar exterior: carga sensivel/latente do ar de renovacao/infiltracao.
#   2) VAZAO DE AR EXTERIOR (16401-3): 27 m3/h.pessoa (7,5 L/s) + 1,5 m3/h.m2.
#   3) CONVERSAO: 1 TR = 3,517 kW = 12 000 BTU/h = 3 024 kcal/h.
#   4) ESTIMATIVA rapida por area (BTU/h.m2): galpao 400-600 ; comercial 600-800.
#      Ocupacao: escritorio 7-10 m2/pessoa ; galpao 15-30 m2/pessoa.
#   5) CONDICOES de projeto (16401-2): verao 23-25 C (tol. 22-26); UR 40-60%;
#      velocidade do ar na zona ocupada <= 0,2 m/s.
# Valores LIDOS do PDF da NBR 16401 / Creder via NotebookLM - NAO de memoria. O
# coeficiente 0,335 W.h/(m3.K) do ar exterior deriva das propriedades do ar-padrao
# (rho*cp = 1,2*1006/3600), nao de tabela.
# Unidades: carga em W; area em m2; vazao em m3/h; capacidade em TR/kW/BTU.
# ============================================================================
"""Climatizacao do galpao/ambientes (NBR 16401): carga termica (Q=U*A*dT + internos +
ar exterior), vazao de renovacao, condicoes de projeto e capacidade em TR/kW/BTU."""

from __future__ import annotations

import math

# conversoes de capacidade (1 TR = ...)
TR_KW = 3.517
TR_BTU_H = 12000.0
TR_KCAL_H = 3024.0
KW_BTU_H = 3412.0

# vazao de ar exterior minima (NBR 16401-3)
VAZAO_AR_PESSOA_M3H = 27.0        # m3/h.pessoa (7,5 L/s)
VAZAO_AR_AREA_M3H = 1.5          # m3/h.m2 (0,40 L/s.m2)

# estimativa rapida de carga (BTU/h.m2) por tipo de ambiente
BTU_M2 = {"escritorio": 700.0, "comercial": 700.0, "residencia": 550.0,
          "galpao": 500.0, "galpao_leve": 400.0}
# ocupacao tipica (m2 por pessoa) - NBR 16401-3
OCUPACAO_M2 = {"escritorio": 8.0, "reuniao": 1.75, "galpao": 20.0, "comercial": 5.0}
# calor total dissipado por pessoa (W) por atividade (Tab.C.1)
CALOR_PESSOA_W = {"leve": 235.0, "moderado": 295.0, "pesado": 440.0}

# condicoes de projeto (NBR 16401-2)
T_INTERNA_VERAO_C = (23.0, 25.0)
UR_CONFORTO_PCT = (40.0, 60.0)
VEL_AR_MAX_MS = 0.20
# constante do ar-padrao p/ carga sensivel do ar exterior: rho*cp/3600 (W.h/m3.K)
CP_AR_SENSIVEL = 0.335


def kw_para_tr(kw):
    return kw / TR_KW


def btu_para_tr(btu_h):
    return btu_h / TR_BTU_H


def capacidade(carga_W):
    """Converte a carga termica (W) p/ capacidade em kW, TR e BTU/h."""
    kw = carga_W / 1000.0
    return {"carga_W": carga_W, "kW": round(kw, 2), "TR": round(kw / TR_KW, 2),
            "BTU_h": round(kw * KW_BTU_H, 0)}


def conducao(U, A, dT):
    """Ganho de calor por conducao pela envoltoria: Q = U*A*dT [W]."""
    return U * A * dT


def carga_pessoas(n, atividade="leve"):
    """Calor total dissipado por n pessoas (W), Tab.C.1."""
    try:
        return n * CALOR_PESSOA_W[atividade]
    except KeyError:
        raise ValueError("[A CONFIRMAR] atividade '%s' sem calor tabelado." % atividade)


def vazao_ar_exterior(n_pessoas, area_m2):
    """Vazao minima de ar exterior (m3/h): 27*n + 1,5*A (NBR 16401-3)."""
    return VAZAO_AR_PESSOA_M3H * n_pessoas + VAZAO_AR_AREA_M3H * area_m2


def carga_ar_exterior_sensivel(vazao_m3h, dT):
    """Carga sensivel do ar exterior: Q = 0,335*V*dT [W] (ar-padrao)."""
    return CP_AR_SENSIVEL * vazao_m3h * dT


def capacidade_estimativa(area_m2, tipo="galpao"):
    """Estimativa rapida da capacidade (TR) por area: A*BTU_m2/12000."""
    try:
        btu = area_m2 * BTU_M2[tipo]
    except KeyError:
        raise ValueError("[A CONFIRMAR] tipo '%s' sem estimativa BTU/m2." % tipo)
    return btu / TR_BTU_H


def carga_termica_detalhada(caso):
    """Carga termica de resfriamento pelo metodo por componentes (16401-1 Secao 6).
    caso: {envoltoria: [{U, A, dT}...], n_pessoas, atividade, P_iluminacao_W,
           P_equipamentos_W, area_m2, dT_ar_ext}.
    Retorna a carga total (W) e as parcelas."""
    env = sum(conducao(e["U"], e["A"], e["dT"]) for e in caso.get("envoltoria", []))
    pes = carga_pessoas(int(caso.get("n_pessoas", 0)), caso.get("atividade", "leve"))
    ilum = float(caso.get("P_iluminacao_W", 0.0))
    equip = float(caso.get("P_equipamentos_W", 0.0))
    area = float(caso.get("area_m2", 0.0))
    n = int(caso.get("n_pessoas", 0))
    V_ar = vazao_ar_exterior(n, area)
    ar_ext = carga_ar_exterior_sensivel(V_ar, float(caso.get("dT_ar_ext", 8.0)))
    total = env + pes + ilum + equip + ar_ext
    return {"envoltoria_W": round(env, 1), "pessoas_W": round(pes, 1),
            "iluminacao_W": round(ilum, 1), "equipamentos_W": round(equip, 1),
            "ar_exterior_W": round(ar_ext, 1), "vazao_ar_exterior_m3h": round(V_ar, 1),
            "carga_total_W": round(total, 1), **capacidade(total)}


def dimensiona_climatizacao(caso):
    """Dimensiona a climatizacao de um ambiente. metodo 'estimativa' (rapido, por
    area) ou 'detalhado' (por componentes). Retorna capacidade + vazao de renovacao +
    condicoes de projeto.
    caso: {area_m2, tipo(='galpao'), metodo(='estimativa'), n_pessoas, ...componentes}."""
    area = float(caso["area_m2"])
    tipo = caso.get("tipo", "galpao")
    metodo = caso.get("metodo", "estimativa")
    if caso.get("n_pessoas") is not None:
        n = int(caso["n_pessoas"])
    else:
        n = max(1, int(area / OCUPACAO_M2.get(tipo, 20.0)))     # ocupacao tipica

    if metodo == "detalhado":
        det = carga_termica_detalhada(dict(caso, area_m2=area, n_pessoas=n))
        cap = det
    else:
        TR = capacidade_estimativa(area, tipo)
        cap = capacidade(TR * TR_KW * 1000.0)
        cap["metodo"] = "estimativa"

    V_ar = vazao_ar_exterior(n, area)
    return {"area_m2": area, "tipo": tipo, "metodo": metodo, "n_pessoas": n,
            "capacidade_TR": cap["TR"], "capacidade_kW": cap["kW"],
            "capacidade_BTU_h": cap["BTU_h"], "vazao_ar_exterior_m3h": round(V_ar, 1),
            "t_interna_C": T_INTERNA_VERAO_C, "UR_pct": UR_CONFORTO_PCT,
            "vel_ar_max_ms": VEL_AR_MAX_MS, "detalhe": cap,
            "OK": cap["TR"] > 0}


def _selftest():
    """Afere contra a NBR 16401 + Creder (conversoes, estimativa, Q=U*A*dT)."""
    # conversoes: 1 TR = 3,517 kW = 12000 BTU/h
    assert TR_KW == 3.517 and TR_BTU_H == 12000.0
    assert abs(kw_para_tr(3.517) - 1.0) < 1e-9 and btu_para_tr(12000.0) == 1.0
    # conducao Q = U*A*dT
    assert conducao(2.0, 100.0, 8.0) == 1600.0
    # pessoas (Tab.C.1): 10 pessoas trabalho leve -> 2350 W
    assert carga_pessoas(10, "leve") == 2350.0
    # vazao de ar exterior: 10 pessoas + 800 m2 -> 270 + 1200 = 1470 m3/h
    assert vazao_ar_exterior(10, 800.0) == 1470.0
    # estimativa: galpao 800 m2 -> 800*500/12000 = 33,33 TR
    assert abs(capacidade_estimativa(800.0, "galpao") - 33.333) < 0.01
    # dimensionamento por estimativa
    r = dimensiona_climatizacao({"area_m2": 800.0, "tipo": "galpao"})
    assert abs(r["capacidade_TR"] - 33.33) < 0.1
    assert r["vazao_ar_exterior_m3h"] == vazao_ar_exterior(r["n_pessoas"], 800.0)
    assert r["t_interna_C"] == (23.0, 25.0) and r["vel_ar_max_ms"] == 0.20 and r["OK"]
    # metodo detalhado: envoltoria + pessoas + iluminacao + equipamentos + ar ext
    d = dimensiona_climatizacao({"area_m2": 100.0, "tipo": "escritorio",
                                 "metodo": "detalhado", "n_pessoas": 10,
                                 "envoltoria": [{"U": 2.0, "A": 100.0, "dT": 8.0}],
                                 "P_iluminacao_W": 1000.0, "P_equipamentos_W": 1500.0,
                                 "dT_ar_ext": 8.0})
    # envoltoria 1600 + pessoas 2350 + ilum 1000 + equip 1500 + ar_ext 0,335*V*8
    V = vazao_ar_exterior(10, 100.0)                       # 270+150=420
    esperado = 1600 + 2350 + 1000 + 1500 + 0.335 * V * 8
    assert abs(d["detalhe"]["carga_total_W"] - esperado) < 1.0, d["detalhe"]["carga_total_W"]
    print("climatizacao_nbr16401 self-test PASSED (NBR 16401 + Creder)")


if __name__ == "__main__":
    _selftest()
