# ============================================================================
# proteccao_sprinklers_nbr10897.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Sistema de PROTECAO POR CHUVEIROS AUTOMATICOS (sprinklers) do galpao (ABNT NBR
# 10897:2014), 4o modulo do vertical de seguranca contra incendio (protecao ATIVA
# por agua):
#   1) CLASSIFICACAO DE RISCO (Secao 4): leve; ordinario I (estoque <= 2,4 m) / II
#      (<= 3,7 m); extra I/II. Galpao de producao/estoque <= 3,7 m -> ordinario II.
#      Estoque > 3,7 m -> areas de armazenamento (NBR 13792, fora do escopo).
#   2) AREA DE COBERTURA por chuveiro (Tab.10) e ESPACAMENTO por risco (parede =
#      metade; minima 100 mm; teto absoluto 21 m2).
#   3) CURVA DENSIDADE x AREA DE OPERACAO (Fig.43): densidade de aplicacao (mm/min =
#      L/min.m2) x area de operacao (m2). Area minima 140 m2 (leve/ord) / 230 m2 (extra).
#   4) VAZAO Q = K*raiz(P) (K em L/min/bar^0,5, P em bar; K=80 padrao DN15); pressao
#      minima de operacao 48 kPa (0,48 bar).
#   5) DURACAO (Tab.24): leve 30 / ordinario 60 / extra 90 min; demanda de hidrantes a
#      somar (380/950/1900 L/min). RESERVA = (Q_chuveiros + Q_hidrantes) * duracao.
# Valores LIDOS do PDF da NBR 10897:2014 via NotebookLM - NAO de memoria.
# Unidades: area em m2; densidade em mm/min (=L/min.m2); vazao em L/min; pressao em
# bar; reserva em L; duracao em min.
# ============================================================================
"""Protecao por chuveiros automaticos do galpao (NBR 10897:2014): risco, cobertura,
curva densidade x area, vazao Q=K*raiz(P) e reserva de incendio."""

from __future__ import annotations

import math

# classe de risco: cobertura (m2), espacamento (m), curva densidade (mm/min) e area
# de operacao (m2) nos extremos, duracao (min), demanda de hidrantes (L/min), area
# minima de operacao (m2). Cobertura de extra = 9,3 (densidade >= 10,2), conservador.
RISCO = {
    "leve":        {"h_max_m": None, "cobertura_m2": 18.6, "espacamento_m": 4.6,
                    "densidade": (2.25, 4.1), "area": (280.0, 140.0),
                    "duracao_min": 30, "hidrantes_Lmin": 380, "area_min_m2": 140.0},
    "ordinario_I": {"h_max_m": 2.4, "cobertura_m2": 12.1, "espacamento_m": 4.6,
                    "densidade": (4.1, 6.1), "area": (370.0, 140.0),
                    "duracao_min": 60, "hidrantes_Lmin": 950, "area_min_m2": 140.0},
    "ordinario_II": {"h_max_m": 3.7, "cobertura_m2": 12.1, "espacamento_m": 4.6,
                     "densidade": (6.1, 8.1), "area": (370.0, 140.0),
                     "duracao_min": 60, "hidrantes_Lmin": 950, "area_min_m2": 140.0},
    "extra_I":     {"h_max_m": None, "cobertura_m2": 9.3, "espacamento_m": 3.7,
                    "densidade": (8.1, 12.2), "area": (465.0, 230.0),
                    "duracao_min": 90, "hidrantes_Lmin": 1900, "area_min_m2": 230.0},
    "extra_II":    {"h_max_m": None, "cobertura_m2": 9.3, "espacamento_m": 3.7,
                    "densidade": (12.2, 16.3), "area": (465.0, 230.0),
                    "duracao_min": 90, "hidrantes_Lmin": 1900, "area_min_m2": 230.0},
}
COBERTURA_MAX_ABS_M2 = 21.0      # limite absoluto por chuveiro padrao (7.6.2.1)
PAREDE_MIN_MM = 100.0            # distancia minima a parede (7.7.3)
K_PADRAO = 80.0                  # DN15, L/min/bar^0,5 (Tab.1)
PRESSAO_MIN_BAR = 0.48          # 48 kPa (9.4.4.10)


def classifica_risco(altura_estoque_m, tipo="producao"):
    """Classe de risco por altura de estocagem (Secao 4). tipo 'extra' forca extra.
    Estoque > 3,7 m -> armazenamento (NBR 13792, fora do escopo -> ValueError)."""
    if tipo in ("extra", "extra_I", "extra_II"):
        return "extra_I" if tipo in ("extra", "extra_I") else "extra_II"
    if tipo == "leve":
        return "leve"
    h = altura_estoque_m
    if h <= 2.4:
        return "ordinario_I"
    if h <= 3.7:
        return "ordinario_II"
    raise ValueError("[A CONFIRMAR] estoque > 3,7 m -> area de armazenamento "
                     "(NBR 13792, fora do escopo da NBR 10897).")


def area_operacao(risco, densidade=None):
    """Area de operacao (m2) para uma densidade na curva densidade x area (Fig.43),
    interpolada linearmente entre os extremos. Sem densidade -> extremo de menor
    densidade (maior area, mais conservador p/ a reserva). Respeita a area minima."""
    r = RISCO[risco]
    d_min, d_max = r["densidade"]
    a_max, a_min = r["area"]                          # a_max no d_min ; a_min no d_max
    if densidade is None:
        densidade = d_min
    d = max(d_min, min(d_max, densidade))
    frac = 0.0 if d_max == d_min else (d - d_min) / (d_max - d_min)
    A = a_max + frac * (a_min - a_max)
    return max(A, r["area_min_m2"]), d


def vazao_chuveiro(K, P_bar):
    """Vazao de um chuveiro: Q = K*raiz(P) [L/min]."""
    return K * math.sqrt(P_bar)


def pressao_de_vazao(Q, K):
    """Pressao (bar) necessaria p/ a vazao Q num chuveiro de fator K: P = (Q/K)^2."""
    return (Q / K) ** 2


def dimensiona_sprinklers(caso):
    """Projeta o sistema de chuveiros automaticos do galpao.
    caso: {C, L, altura_estoque_m(=3.0), tipo(='producao'), risco(opc), densidade(opc),
           K(=80)}.
    Retorna risco, cobertura, N de chuveiros (operacao e total), vazoes, pressao e a
    reserva de incendio."""
    C = float(caso["C"]); L = float(caso["L"])
    A_total = C * L
    risco = caso.get("risco") or classifica_risco(float(caso.get("altura_estoque_m", 3.0)),
                                                  caso.get("tipo", "producao"))
    r = RISCO[risco]
    cob = min(r["cobertura_m2"], COBERTURA_MAX_ABS_M2)
    A_oper, dens = area_operacao(risco, caso.get("densidade"))
    K = float(caso.get("K", K_PADRAO))

    n_oper = max(1, math.ceil(A_oper / cob))          # chuveiros na area de operacao
    n_total = max(1, math.ceil(A_total / cob))        # chuveiros no galpao todo
    Q_chuveiros = dens * A_oper                        # L/min (densidade * area)
    Q_por_chuveiro = Q_chuveiros / n_oper
    P = max(pressao_de_vazao(Q_por_chuveiro, K), PRESSAO_MIN_BAR)
    Q_hidr = r["hidrantes_Lmin"]
    duracao = r["duracao_min"]
    reserva_L = (Q_chuveiros + Q_hidr) * duracao
    return {"risco": risco, "cobertura_m2": cob, "espacamento_max_m": r["espacamento_m"],
            "densidade_mm_min": dens, "area_operacao_m2": round(A_oper, 1),
            "N_chuveiros_operacao": n_oper, "N_chuveiros_total": n_total,
            "Q_chuveiros_Lmin": round(Q_chuveiros, 1),
            "Q_por_chuveiro_Lmin": round(Q_por_chuveiro, 1), "K": K,
            "pressao_bar": round(P, 3), "Q_hidrantes_Lmin": Q_hidr,
            "duracao_min": duracao, "reserva_incendio_L": round(reserva_L, 0),
            "reserva_incendio_m3": round(reserva_L / 1000.0, 1),
            "OK": P >= PRESSAO_MIN_BAR and cob <= COBERTURA_MAX_ABS_M2}


def _selftest():
    """Afere contra a NBR 10897:2014 (Secao 4, Tab.10, Fig.43, Tab.24)."""
    # classificacao: galpao producao estoque 3 m -> ordinario II
    assert classifica_risco(3.0, "producao") == "ordinario_II"
    assert classifica_risco(2.0) == "ordinario_I"
    import pytest
    with pytest.raises(ValueError):
        classifica_risco(5.0)                          # > 3,7 m -> NBR 13792
    # cobertura e espacamento (Tab.10)
    assert RISCO["ordinario_II"]["cobertura_m2"] == 12.1
    assert RISCO["leve"]["espacamento_m"] == 4.6
    # curva densidade x area: ord II no extremo d_min=6,1 -> area 370
    A, d = area_operacao("ordinario_II")
    assert d == 6.1 and A == 370.0
    # vazao: K=80, P=1 bar -> Q=80 L/min ; P de 113 L/min -> (113/80)^2=1,996 bar
    assert vazao_chuveiro(80.0, 1.0) == 80.0
    assert abs(pressao_de_vazao(113.0, 80.0) - 1.9954) < 0.001
    # projeto do galpao 40x20, estoque 3 m (ord II):
    r = dimensiona_sprinklers({"C": 40.0, "L": 20.0, "altura_estoque_m": 3.0})
    assert r["risco"] == "ordinario_II" and r["cobertura_m2"] == 12.1
    assert r["N_chuveiros_operacao"] == 31            # ceil(370/12,1)
    assert r["N_chuveiros_total"] == 67               # ceil(800/12,1)
    # Q = 6,1 * 370 = 2257 L/min ; reserva = (2257 + 950) * 60 = 192420 L = 192,4 m3
    assert abs(r["Q_chuveiros_Lmin"] - 2257.0) < 1.0
    assert abs(r["reserva_incendio_m3"] - 192.4) < 0.5
    assert r["duracao_min"] == 60 and r["Q_hidrantes_Lmin"] == 950 and r["OK"]
    print("proteccao_sprinklers_nbr10897 self-test PASSED (NBR 10897:2014)")


if __name__ == "__main__":
    _selftest()
