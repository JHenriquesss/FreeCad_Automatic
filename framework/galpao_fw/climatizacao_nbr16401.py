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

# coeficiente de desempenho (entrada eletrica = capacidade termica / COP). Aferido
# contra Creder Tab.3.5 (24000 BTU/h = 7,03 kW term / 1990 W elet -> COP ~ 3,5).
COP_PADRAO = 3.5

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
    cop = float(caso.get("COP", COP_PADRAO))
    if cop <= 0.0:
        raise ValueError("[A CONFIRMAR] COP deve ser > 0 (entrada eletrica = "
                         "capacidade / COP); recebido COP=%s." % cop)
    P_eletrica_kW = cap["kW"] / cop                   # entrada eletrica do equipamento
    return {"area_m2": area, "tipo": tipo, "metodo": metodo, "n_pessoas": n,
            "capacidade_TR": cap["TR"], "capacidade_kW": cap["kW"],
            "capacidade_BTU_h": cap["BTU_h"], "COP": cop,
            "potencia_eletrica_kW": round(P_eletrica_kW, 2),
            "vazao_ar_exterior_m3h": round(V_ar, 1),
            "t_interna_C": T_INTERNA_VERAO_C, "UR_pct": UR_CONFORTO_PCT,
            "vel_ar_max_ms": VEL_AR_MAX_MS, "detalhe": cap,
            "OK": cap["TR"] > 0}


# --- DUTOS (secao p/ o modelo de coordenacao) ---
# A vazao de insuflamento sai da fisica do ar (CP_AR_SENSIVEL, ja no modulo): V = Q/(
# 0,335*dT). A VELOCIDADE tem limite de NORMA: NBR 16401-1:2024, Secao 10.4.1.2 + Tabela 1
# (Classes de pressao) - velocidade MAXIMA do ar no duto por classe de pressao estatica.
# LIDO do PDF via NotebookLM (c5934f22) - NAO de memoria. A norma NAO especifica velocidade
# de projeto, so o MAXIMO; adota-se um valor de projeto ABAIXO do maximo.
# O dT de insuflamento NBR 16401-1 NAO fixa (Secao 6.3.4, depende de psicrometria/vazao) ->
# fica como parametro de PROJETO (nao ha valor de norma a citar; default tipico).
VEL_MAX_CLASSE_PA = {125: 10.0, 250: 12.5, 500: 12.5, 750: 20.0, 1000: 20.0}  # Tab.1, m/s
CLASSE_PRESSAO_PADRAO_PA = 250    # NBR 16401-1: na ausencia de projeto, assumir classe 250
DT_INSUFLAMENTO_K = 10.0          # parametro de PROJETO (NBR 16401-1 6.3.4 nao fixa - psicro)
VEL_DUTO_PRINCIPAL_MS = 6.0       # velocidade de projeto (< max 12,5 da classe 250, Tab.1)


def velocidade_max_duto(classe_pa=CLASSE_PRESSAO_PADRAO_PA):
    """Velocidade MAXIMA do ar no duto (m/s) pela classe de pressao (NBR 16401-1 Tab.1).
    classe_pa fora da tabela -> erro (nao inventar)."""
    try:
        return VEL_MAX_CLASSE_PA[classe_pa]
    except KeyError:
        raise ValueError("[A CONFIRMAR] classe de pressao %s Pa fora da Tab.1 da NBR "
                         "16401-1 (use 125/250/500/750/1000)." % (classe_pa,))


def vazao_insuflamento(carga_W, dT_ins=DT_INSUFLAMENTO_K):
    """Vazao de ar de insuflamento (m3/h) para remover a carga: V = Q/(0,335*dT_ins).
    Usa a carga TOTAL como limite superior (conservador p/ duto maior). dT_ins e'
    parametro de projeto (a NBR 16401-1 6.3.4 nao fixa - depende de psicrometria)."""
    if dT_ins <= 0:
        raise ValueError("[A CONFIRMAR] dT_ins deve ser > 0 (recebido %s)." % (dT_ins,))
    return carga_W / (CP_AR_SENSIVEL * dT_ins)


def dimensiona_duto(vazao_m3h, vel_ms=VEL_DUTO_PRINCIPAL_MS, aspecto=2.0,
                    classe_pa=CLASSE_PRESSAO_PADRAO_PA):
    """Secao do duto RETANGULAR pela vazao: A = V/(3600*v); lados na razao `aspecto`
    (largura/altura). VERIFICA a velocidade contra o MAXIMO da classe de pressao (NBR
    16401-1 Tab.1). Retorna {area_m2, largura_m, altura_m, vel_ms, vel_max_ms,
    classe_pa, vel_OK}. vel_OK=False -> velocidade acima do maximo da classe (duto
    subdimensionado / classe de pressao maior)."""
    if vel_ms <= 0 or aspecto <= 0:
        raise ValueError("[A CONFIRMAR] velocidade e aspecto do duto devem ser > 0 "
                         "(recebido vel=%s, aspecto=%s)." % (vel_ms, aspecto))
    vmax = velocidade_max_duto(classe_pa)
    A = vazao_m3h / 3600.0 / vel_ms                    # m2
    h = math.sqrt(A / aspecto)
    w = aspecto * h
    return {"area_m2": round(A, 4), "largura_m": round(w, 3), "altura_m": round(h, 3),
            "vel_ms": vel_ms, "vel_max_ms": vmax, "classe_pa": classe_pa,
            "vel_OK": vel_ms <= vmax}


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
    # potencia eletrica = capacidade / COP (33,33 TR = 117,2 kW term / 3,5 = 33,5 kW elet)
    assert abs(r["potencia_eletrica_kW"] - r["capacidade_kW"] / 3.5) < 0.01
    assert r["potencia_eletrica_kW"] < r["capacidade_kW"]
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
    # DUTOS (coordenacao): V = Q/(0,335*dT). 117200 W / (0,335*10) = 34985 m3/h
    Vi = vazao_insuflamento(117200.0, 10.0)
    assert abs(Vi - 34985.07) < 1.0, Vi
    # secao a 6 m/s: A = 34985/3600/6 = 1,62 m2 ; aspecto 2 -> h=0,90 w=1,80
    du = dimensiona_duto(Vi, 6.0, aspecto=2.0)
    assert abs(du["area_m2"] - 1.62) < 0.02, du["area_m2"]
    assert abs(du["largura_m"] / du["altura_m"] - 2.0) < 1e-6      # razao de aspecto
    assert abs(du["largura_m"] * du["altura_m"] - du["area_m2"]) < 1e-3
    # VELOCIDADE x NORMA (NBR 16401-1 Tab.1): classe 250 Pa -> max 12,5 m/s
    assert velocidade_max_duto(250) == 12.5 and velocidade_max_duto(125) == 10.0
    assert du["vel_max_ms"] == 12.5 and du["classe_pa"] == 250 and du["vel_OK"]  # 6 < 12,5
    # velocidade acima do maximo da classe -> vel_OK False (nao levanta; e' aviso)
    assert dimensiona_duto(Vi, 15.0)["vel_OK"] is False            # 15 > 12,5 (classe 250)
    assert dimensiona_duto(Vi, 15.0, classe_pa=750)["vel_OK"]      # 15 < 20 (classe 750)
    import pytest
    with pytest.raises(ValueError):
        vazao_insuflamento(1000.0, 0.0)                            # dT <= 0
    with pytest.raises(ValueError):
        dimensiona_duto(1000.0, 0.0)                              # vel <= 0
    with pytest.raises(ValueError):
        velocidade_max_duto(300)                                  # classe fora da Tab.1
    print("climatizacao_nbr16401 self-test PASSED (NBR 16401 Tab.1 velocidade + dutos)")


if __name__ == "__main__":
    _selftest()
