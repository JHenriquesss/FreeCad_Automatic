# ============================================================================
# iluminacao_externa_nbr5101.py - O QUE ESTE SCRIPT FAZ / CALCULA
# ILUMINACAO EXTERNA / DE VIAS do galpao - patio de manobra, estacionamento, vias de
# circulacao e area de carga/descarga (ABNT NBR 5101:2024 + Mamede Cap.2):
#   1) CLASSES de iluminacao: M (luminancia cd/m2, trafego motorizado, Tab.2), C
#      (iluminancia lux, area de conflito, Tab.4), P (pedestres, Tab.7). Niveis
#      recomendados p/ areas externas industriais (Mamede Tab.2.17).
#   2) ESPACAMENTO entre postes S = k*H (3H <= S <= 5H; pratico ~4H); disposicao por
#      Lp/H: unilateral (Lp<=H), bilateral alternada (Lp<=1,5H), oposta (Lp>1,5H).
#   3) METODO DOS LUMENS p/ vias (Mamede 2.7.2): Em = fluxo*N*Fu*Fm/(Lp*S) ->
#      S = fluxo*N*Fu*Fm/(Em*Lp). Fu 0,20-0,45 (curva da luminaria); Fm 0,70-0,80 LED.
# Valores LIDOS do PDF da NBR 5101:2024 / Mamede via NotebookLM - NAO de memoria.
# Unidades: iluminancia em lux; luminancia em cd/m2; comprimentos em m; fluxo em lm;
# potencia em W.
# ============================================================================
"""Iluminacao externa/de vias do galpao (NBR 5101:2024 / Mamede Cap.2): classes,
niveis, espacamento de postes e metodo dos lumens para vias (Em = fluxo*N*Fu*Fm/(Lp*S))."""

from __future__ import annotations

import math

# niveis recomendados p/ areas externas industriais (lux) - Mamede Tab.2.17 / NBR 5413
NIVEL_EXTERNO = {
    "deposito_ar_livre": 20.0,      # 10-20 lx
    "estacionamento": 50.0,
    "via_trafego": 70.0,            # 50-70 lx
    "patio_manobra": 150.0,         # 100-150 lx (caminhoes)
    "carga_descarga": 150.0,        # 100-150 lx
}

# Classe M - luminancia media mantida (cd/m2) + uniformidades (Tab.2)
CLASSE_M = {
    "M1": {"L_cd_m2": 2.00, "U0": 0.40, "UL": 0.65},
    "M2": {"L_cd_m2": 1.50, "U0": 0.40, "UL": 0.65},
    "M3": {"L_cd_m2": 1.00, "U0": 0.40, "UL": 0.60},
    "M4": {"L_cd_m2": 0.75, "U0": 0.40, "UL": 0.60},
    "M5": {"L_cd_m2": 0.50, "U0": 0.35, "UL": 0.35},
    "M6": {"L_cd_m2": 0.30, "U0": 0.35, "UL": 0.35},
}
# Classe C - iluminancia media mantida (lux) area de conflito (Tab.4)
CLASSE_C = {"C0": 50.0, "C1": 30.0, "C2": 20.0, "C3": 15.0, "C4": 10.0, "C5": 7.5}
# Classe P - pedestres: (E_med, E_min, E_vert) lux (Tab.7)
CLASSE_P = {"P1": (20.0, 4.0, 6.0), "P2": (15.0, 3.0, 5.0), "P3": (10.0, 2.0, 3.0),
            "P4": (7.5, 1.5, 2.5), "P5": (5.0, 1.0, 1.5), "P6": (3.0, 0.6, 1.0)}

K_ESP_MIN = 3.0                  # S >= 3*H
K_ESP_MAX = 5.0                  # S <= 5*H
K_ESP_PRATICO = 4.0             # ~ 3,5 a 4,0 * H p/ uniformidade
FU_DEFAULT = 0.36               # fator de utilizacao (curva da luminaria), A CONFIRMAR
FM_DEFAULT = 0.75               # fator de manutencao LED selada (0,70-0,80)


def nivel_externo(area_tipo):
    """Iluminancia recomendada (lux) p/ area externa industrial (Mamede Tab.2.17)."""
    try:
        return NIVEL_EXTERNO[area_tipo]
    except KeyError:
        raise ValueError("[A CONFIRMAR] area externa '%s' sem nivel tabelado." % area_tipo)


def espacamento_postes(H, k=K_ESP_PRATICO):
    """Espacamento entre postes S = k*H (m), limitado a [3H, 5H]."""
    k = max(K_ESP_MIN, min(K_ESP_MAX, k))
    return k * H


def disposicao_postes(Lp, H):
    """Disposicao dos postes por relacao largura/altura Lp/H (Creder/Mamede)."""
    if Lp <= H:
        return "unilateral"
    if Lp <= 1.5 * H:
        return "bilateral_alternada"
    return "bilateral_oposta"


def iluminancia_media(fluxo_lm, n_lamp, Fu, Fm, Lp, S):
    """Iluminancia media na via: Em = fluxo*N*Fu*Fm/(Lp*S) [lux] (Mamede 2.7.2)."""
    return fluxo_lm * n_lamp * Fu * Fm / (Lp * S)


def espacamento_para_iluminancia(fluxo_lm, n_lamp, Fu, Fm, Em, Lp):
    """Espacamento entre postes p/ atender Em: S = fluxo*N*Fu*Fm/(Em*Lp) [m]."""
    return fluxo_lm * n_lamp * Fu * Fm / (Em * Lp)


def dimensiona_iluminacao_externa(caso):
    """Projeta a iluminacao externa de uma via/patio do galpao.
    caso: {comprimento_m, Lp(largura), H(altura poste=8), area_tipo(->Em) ou Em,
           luminaria(nome->fluxo/P ou dict), Fu(=0,36), Fm(=0,75)}.
    Retorna Em, S (limitado a 5H), disposicao, N de postes e potencia."""
    comp = float(caso["comprimento_m"]); Lp = float(caso["Lp"])
    H = float(caso.get("H", 8.0))
    if Lp <= 0.0 or H <= 0.0:
        raise ValueError("[A CONFIRMAR] largura da via Lp (%s) e altura do poste H "
                         "(%s) devem ser > 0." % (Lp, H))
    Em = float(caso["Em"]) if caso.get("Em") is not None else nivel_externo(caso["area_tipo"])
    Fu = float(caso.get("Fu", FU_DEFAULT)); Fm = float(caso.get("Fm", FM_DEFAULT))
    lum = caso.get("luminaria", {"fluxo_lm": 15000.0, "P_W": 100.0, "n_lampadas": 1})
    fluxo = lum["fluxo_lm"]; n = lum.get("n_lampadas", 1); P = lum["P_W"]

    S_ideal = espacamento_para_iluminancia(fluxo, n, Fu, Fm, Em, Lp)
    S = min(S_ideal, K_ESP_MAX * H)                   # limita a 5*H (uniformidade)
    disp = disposicao_postes(Lp, H)
    lados = 2 if disp in ("bilateral_alternada", "bilateral_oposta") else 1
    n_postes = lados * (max(1, math.ceil(comp / S)) + 1)
    Em_real = iluminancia_media(fluxo, n * lados, Fu, Fm, Lp, S)
    P_total_kW = n_postes * P * n / 1000.0
    return {"Em_lux": Em, "Em_real_lux": round(Em_real, 1), "S_m": round(S, 2),
            "S_ideal_m": round(S_ideal, 2), "S_max_m": K_ESP_MAX * H,
            "disposicao": disp, "N_postes": n_postes, "H_m": H,
            "P_total_kW": round(P_total_kW, 2), "Fu": Fu, "Fm": Fm,
            "OK": Em_real >= Em and S <= K_ESP_MAX * H}


def _selftest():
    """Afere contra a NBR 5101:2024 (Tab.2/4/7) + o metodo de Mamede 2.7.2."""
    # niveis externos (Mamede Tab.2.17)
    assert nivel_externo("estacionamento") == 50.0
    assert nivel_externo("patio_manobra") == 150.0
    # classes (Tab.2/4/7)
    assert CLASSE_M["M1"]["L_cd_m2"] == 2.00 and CLASSE_C["C0"] == 50.0
    assert CLASSE_P["P1"] == (20.0, 4.0, 6.0)
    # espacamento: H=10 -> S pratico 4*10=40 ; limitado a [30,50]
    assert espacamento_postes(10.0) == 40.0 and espacamento_postes(10.0, 6.0) == 50.0
    # disposicao: Lp=10, H=10 -> unilateral ; Lp=16,H=10 -> oposta
    assert disposicao_postes(10.0, 10.0) == "unilateral"
    assert disposicao_postes(16.0, 10.0) == "bilateral_oposta"
    # metodo dos lumens (Mamede): Em = 12600*1*0,36*1,0/(10*30) = 15,12 lux
    assert abs(iluminancia_media(12600.0, 1, 0.36, 1.0, 10.0, 30.0) - 15.12) < 0.01
    assert abs(espacamento_para_iluminancia(12600.0, 1, 0.36, 1.0, 15.12, 10.0) - 30.0) < 0.01
    # projeto de uma via interna 100 m, Lp=8 m, H=10 m, estacionamento 50 lx
    r = dimensiona_iluminacao_externa({"comprimento_m": 100.0, "Lp": 8.0, "H": 10.0,
                                       "area_tipo": "estacionamento",
                                       "luminaria": {"fluxo_lm": 15000.0, "P_W": 100.0}})
    assert r["Em_lux"] == 50.0 and r["disposicao"] == "unilateral"
    assert r["S_m"] <= 50.0 and r["N_postes"] >= 2 and r["OK"]
    print("iluminacao_externa_nbr5101 self-test PASSED (NBR 5101:2024 + Mamede 2.7.2)")


if __name__ == "__main__":
    _selftest()
