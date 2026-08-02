# ============================================================================
# iluminacao_emergencia_nbr10898.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Sistema de ILUMINACAO DE EMERGENCIA do galpao (ABNT NBR 10898:2023), 1o modulo do
# vertical de SEGURANCA CONTRA INCENDIO:
#   1) NIVEL MINIMO de iluminancia (aclaramento): 3 lx (areas planas s/ obstaculo),
#      5 lx (obstaculos/escadas), area de circulacao aberta 1 lx (horiz.)/3 lx (vert.),
#      alto risco >= 15 lx. Uniformidade maxima 20:1 (5.1/5.4/5.5/11.2).
#   2) AUTONOMIA minima 2 h; TEMPO DE COMUTACAO <= 2 s (bloco autonomo/UPS) ou <= 5 s
#      (motogerador); disparo com a rede em 60% da tensao nominal (4.9/6.x).
#   3) ESPACAMENTO dos pontos de ACLARAMENTO: pe-direito <= 3,75 m -> dist. max = 4*h
#      entre pontos e 2*h a parede; pe-direito > 3,75 m -> 15 m (ideal), 20 m (max).
#      BALIZAMENTO: <= 15 m entre pontos; em grandes ambientes (galpao) rente ao piso
#      <= 4 m (14.18 / A).
#   4) FLUXO minimo por bloco: aclaramento >= 300 lm; balizamento 30 lm (exclusivo) ou
#      400 lm (dupla funcao). Fumaca: instalar >= 0,5 m abaixo do teto ou >= 15 lx piso.
# Valores LIDOS do PDF da NBR 10898:2023 via NotebookLM - NAO de memoria.
# Unidades: comprimentos em m; iluminancia em lux; fluxo em lm; tempo em s/h.
# ============================================================================
"""Iluminacao de emergencia do galpao (NBR 10898:2023): nivel minimo, autonomia,
espacamento de aclaramento/balizamento e numero de blocos autonomos."""

from __future__ import annotations

import math

# --- niveis minimos de iluminancia (lux) por tipo de area (Secao 5) ----------
E_MIN = {"plano": 3.0, "obstaculo": 5.0, "escada": 5.0,
         "aberta_horizontal": 1.0, "aberta_vertical": 3.0, "alto_risco": 15.0}
UNIFORMIDADE_MAX = 20.0            # relacao max:min (11.2)

AUTONOMIA_MIN_H = 2.0             # h (4.9)
COMUTACAO_MAX_BLOCO_S = 2.0      # s, bloco autonomo/UPS (6.1/6.2)
COMUTACAO_MAX_GERADOR_S = 5.0   # s, grupo motogerador (6.4)
TENSAO_DISPARO_PCT = 60.0        # % da tensao nominal p/ comutar (6.x)

FLUXO_MIN_ACLARAMENTO_LM = 300.0   # lm por bloco (6.1.2.4)
FLUXO_MIN_BALIZ_EXCLUSIVO_LM = 30.0   # lm (5.2.3)
FLUXO_MIN_BALIZ_DUPLO_LM = 400.0     # lm (5.2.4)
E_MIN_SEM_FUMACA_LX = 15.0       # lx no piso se o ponto ficar acima do colchao de fumaca
FOLGA_TETO_FUMACA_M = 0.5        # instalar >= 0,5 m abaixo do teto (13)

# espacamento de balizamento (m)
BALIZ_GERAL_M = 15.0
BALIZ_GRANDE_AMBIENTE_M = 4.0    # rente ao piso, galpao/grande ambiente (14.18 NOTA 2)
PE_DIREITO_LIMITE_M = 3.75       # divisor do criterio de espacamento (A NOTA 3/4)
ESPACO_ALTO_IDEAL_M = 15.0
ESPACO_ALTO_MAX_M = 20.0


def iluminancia_minima(tipo_area):
    """Iluminancia minima de aclaramento (lux) por tipo de area (NBR 10898 Secao 5)."""
    try:
        return E_MIN[tipo_area]
    except KeyError:
        raise ValueError("[A CONFIRMAR] tipo de area '%s' sem nivel tabelado." % tipo_area)


def espacamento_aclaramento(pe_direito, h_inst=None):
    """Distancia maxima entre pontos de aclaramento (m). h_inst = altura de instalacao
    (default = pe_direito). pd <= 3,75 m -> 4*h; pd > 3,75 m -> 15 m (max 20)."""
    h = pe_direito if h_inst is None else h_inst
    if pe_direito <= PE_DIREITO_LIMITE_M:
        return 4.0 * h
    return ESPACO_ALTO_IDEAL_M          # ideal 15 m (limite absoluto 20 m)


def numero_pontos_grade(C, L, dist_max):
    """Numero de pontos numa grade cobrindo o retangulo C x L com espacamento <=
    dist_max (e <= dist_max/2 ate a parede). N = ceil(C/d) x ceil(L/d)."""
    n_c = max(1, math.ceil(C / dist_max))
    n_l = max(1, math.ceil(L / dist_max))
    return n_c * n_l, (n_c, n_l)


def numero_balizamento(comprimento_rota, grande_ambiente=False):
    """Numero de pontos de balizamento ao longo de uma rota (m). Espacamento 15 m,
    ou 4 m rente ao piso em grande ambiente (galpao)."""
    esp = BALIZ_GRANDE_AMBIENTE_M if grande_ambiente else BALIZ_GERAL_M
    return max(2, math.ceil(comprimento_rota / esp) + 1)


def dimensiona_iluminacao_emergencia(caso):
    """Projeta a iluminacao de emergencia do galpao.
    caso: {C, L, (pe_direito | h_inst), tipo_area(=plano), fluxo_bloco_lm(=300),
           rota_fuga_m(opc; default perimetro), tipo_fonte('bloco'|'gerador'),
           fumaca(bool)}.
    Retorna niveis, N de aclaramento/balizamento, autonomia, comutacao e OK."""
    C = float(caso["C"]); L = float(caso["L"])
    pd = float(caso.get("pe_direito", caso.get("h_inst", 3.0)))
    tipo_area = caso.get("tipo_area", "plano")
    E_req = float(caso["E_min"]) if caso.get("E_min") is not None else iluminancia_minima(tipo_area)
    if caso.get("fumaca") and pd > (caso.get("h_inst", pd) + FOLGA_TETO_FUMACA_M):
        E_req = max(E_req, E_MIN_SEM_FUMACA_LX)     # acima do colchao de fumaca -> 15 lx

    d = espacamento_aclaramento(pd, caso.get("h_inst"))
    n_acl, grade = numero_pontos_grade(C, L, d)
    grande = C * L >= 500.0 or max(C, L) > 30.0     # galpao = grande ambiente
    rota = float(caso.get("rota_fuga_m", 2.0 * (C + L)))
    n_bal = numero_balizamento(rota, grande_ambiente=grande)

    fluxo_bloco = float(caso.get("fluxo_bloco_lm", FLUXO_MIN_ACLARAMENTO_LM))
    tipo_fonte = caso.get("tipo_fonte", "bloco")
    comut_max = COMUTACAO_MAX_GERADOR_S if tipo_fonte == "gerador" else COMUTACAO_MAX_BLOCO_S
    ok_fluxo = fluxo_bloco >= FLUXO_MIN_ACLARAMENTO_LM

    return {"E_min_lux": E_req, "uniformidade_max": UNIFORMIDADE_MAX,
            "espacamento_max_m": d, "grade": grade, "N_aclaramento": n_acl,
            "N_balizamento": n_bal, "baliz_espacamento_m": BALIZ_GRANDE_AMBIENTE_M if grande else BALIZ_GERAL_M,
            "autonomia_h": AUTONOMIA_MIN_H, "comutacao_max_s": comut_max,
            "tensao_disparo_pct": TENSAO_DISPARO_PCT, "fluxo_bloco_lm": fluxo_bloco,
            "tipo_fonte": tipo_fonte, "N_blocos_total": n_acl + n_bal,
            "OK": ok_fluxo and n_acl >= 1}


def _selftest():
    """Afere contra os valores da NBR 10898:2023 + geometria de um galpao 40x20x6."""
    assert iluminancia_minima("plano") == 3.0 and iluminancia_minima("obstaculo") == 5.0
    assert iluminancia_minima("alto_risco") == 15.0
    # pe-direito 6 m (>3,75) -> espacamento 15 m
    assert espacamento_aclaramento(6.0) == 15.0
    # pe-direito 3 m (<=3,75), h=3 -> 4*3 = 12 m
    assert espacamento_aclaramento(3.0, 3.0) == 12.0
    # galpao 40x20, d=15 -> grade 3x2 = 6 pontos de aclaramento
    n, grade = numero_pontos_grade(40.0, 20.0, 15.0)
    assert n == 6 and grade == (3, 2), (n, grade)
    # balizamento em grande ambiente (galpao): perimetro 120 m, 4 m -> 31 pontos
    assert numero_balizamento(120.0, grande_ambiente=True) == 31
    assert numero_balizamento(120.0, grande_ambiente=False) == 9   # 15 m -> 8+1
    # projeto completo
    r = dimensiona_iluminacao_emergencia({"C": 40.0, "L": 20.0, "pe_direito": 6.0,
                                          "tipo_area": "plano", "fluxo_bloco_lm": 350.0})
    assert r["E_min_lux"] == 3.0 and r["N_aclaramento"] == 6
    assert r["autonomia_h"] == 2.0 and r["comutacao_max_s"] == 2.0
    assert r["baliz_espacamento_m"] == 4.0 and r["OK"]           # galpao -> baliz 4 m
    # bloco abaixo do minimo de fluxo -> reprova
    r2 = dimensiona_iluminacao_emergencia({"C": 40.0, "L": 20.0, "pe_direito": 6.0,
                                           "fluxo_bloco_lm": 250.0})
    assert not r2["OK"]
    print("iluminacao_emergencia_nbr10898 self-test PASSED (NBR 10898:2023)")


if __name__ == "__main__":
    _selftest()
