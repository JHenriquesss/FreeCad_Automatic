# ============================================================================
# deteccao_alarme_nbr17240.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Sistema de DETECCAO E ALARME DE INCENDIO do galpao (ABNT NBR 17240:2010), 3o
# modulo do vertical de seguranca contra incendio:
#   1) DETECTOR PONTUAL DE FUMACA (5.4.1): area maxima de cobertura 81 m2 (teto <= 8 m,
#      plano ou viga <= 0,20 m), quadrado 9x9 m inscrito em circulo r = 6,30 m.
#      Viga 0,21-0,60 m -> cobertura 2/3 (54 m2); viga > 0,61 m -> 1/2 (40,5 m2).
#   2) TETO > 8 m: usar DETECTOR LINEAR de fumaca (feixe optico): feixes <= 15 m entre
#      si, <= 7,5 m das paredes, alcance <= 100 m (5.4.4).
#   3) ACIONADORES MANUAIS (5.5.3): distancia maxima a percorrer <= 30 m; >= 1 por
#      pavimento. Altura 0,90-1,40 m.
#   4) CENTRAL / ALIMENTACAO (5.3 / Anexo B): 24 Vcc; cabo do sistema >= 50 cm de
#      condutores de energia; autonomia em SUPERVISAO >= 24 h + ALARME >= 15 min;
#      resposta do acionador na central <= 15 s.
# Valores LIDOS do PDF da NBR 17240:2010 via NotebookLM - NAO de memoria.
# Unidades: area em m2; distancia/altura em m; tensao em Vcc; tempo em h/min/s.
# ============================================================================
"""Deteccao e alarme de incendio do galpao (NBR 17240:2010): detectores pontuais/
lineares de fumaca, acionadores manuais e requisitos da central."""

from __future__ import annotations

import math

COBERTURA_DETECTOR_M2 = 81.0     # teto <= 8 m, plano/viga <= 0,20 m (5.4.1.1)
RAIO_DETECTOR_M = 6.30           # raio de cobertura (quadrado 9x9)
ALTURA_MAX_PONTUAL_M = 8.0       # acima disso -> detector linear (5.4.1.17)
AFASTAMENTO_PAREDE_MIN_M = 0.15  # do teto a parede/viga (5.4.1.2)

# detector linear de fumaca (feixe optico) - 5.4.4
LINEAR_ENTRE_FEIXES_MAX_M = 15.0
LINEAR_PAREDE_MAX_M = 7.5
LINEAR_ALCANCE_MAX_M = 100.0

ACIONADOR_DIST_MAX_M = 30.0      # caminhada max ate o acionador (5.5.3)
ACIONADOR_ALTURA_M = (0.90, 1.35)   # altura de instalacao do piso acabado (5.5.2)

TENSAO_SISTEMA_VCC = 24.0        # 24 Vcc (escopo)
AFASTAMENTO_CABO_ENERGIA_M = 0.50   # 50 cm de 127/220 Vca (6.8.17)
AUTONOMIA_SUPERVISAO_H = 24.0    # Anexo B
AUTONOMIA_ALARME_MIN = 15.0     # min, apos as 24 h
RESPOSTA_ACIONADOR_S = 15.0     # central sinaliza em <= 15 s (8.1.4)


def cobertura_detector(altura_teto, viga_m=0.0):
    """Area de cobertura (m2) de um detector pontual de fumaca por altura de viga.
    Retorna None se altura_teto > 8 m (usar detector LINEAR)."""
    if altura_teto > ALTURA_MAX_PONTUAL_M:
        return None
    if viga_m > 0.60:
        return COBERTURA_DETECTOR_M2 / 2.0          # 40,5 m2
    if viga_m >= 0.21:
        return COBERTURA_DETECTOR_M2 * 2.0 / 3.0    # 54 m2
    return COBERTURA_DETECTOR_M2                     # 81 m2


def numero_detectores_pontuais(area, altura_teto, viga_m=0.0):
    """Numero de detectores pontuais p/ cobrir `area` (m2). None se teto > 8 m."""
    cob = cobertura_detector(altura_teto, viga_m)
    if cob is None:
        return None
    return max(1, math.ceil(area / cob))


def numero_detectores_lineares(C, L):
    """Numero de detectores lineares (feixes) p/ teto alto: feixes <= 15 m entre si,
    <= 7,5 m das paredes, alcance <= 100 m. C = comprimento (feixe), L = largura.
    N_feixes cobre a largura; se C > 100 m, subdivide o comprimento."""
    n_feixes = max(1, math.ceil(L / LINEAR_ENTRE_FEIXES_MAX_M))
    n_trechos = max(1, math.ceil(C / LINEAR_ALCANCE_MAX_M))
    return n_feixes * n_trechos


def numero_acionadores(C, L):
    """Numero de acionadores manuais: distancia a percorrer <= 30 m de qualquer ponto
    (5.5.3). A cobertura por AREA (circulo de raio 30 m) sozinha SUBcontava em galpao
    ALONGADO (ex.: 200 x 12 m -> area/pi*30^2 = 1, mas a ponta fica a ~100 m do centro).
    Corrigido com um PISO por dimensao: ao longo de cada lado os acionadores distam
    <= 2*30 m entre si (cada um alcanca 30 m p/ cada lado) -> ceil(lado / 60). Toma-se
    o MAX (nunca reduz a contagem; so eleva o piso p/ vencer o comprimento). O valor
    de norma (30 m) e' o mesmo ja citado - muda so a geometria de aplicacao."""
    area = C * L
    cob = math.pi * ACIONADOR_DIST_MAX_M ** 2
    por_area = math.ceil(area / cob)
    passo = 2.0 * ACIONADOR_DIST_MAX_M                 # 60 m entre acionadores num eixo
    por_comprimento = math.ceil(C / passo)
    por_largura = math.ceil(L / passo)
    return max(1, por_area, por_comprimento, por_largura)


def dimensiona_deteccao_alarme(caso):
    """Projeta a deteccao e alarme do galpao.
    caso: {C, L, altura_teto(=pe_direito), viga_m(=0)}.
    Retorna detectores (pontuais ou lineares), acionadores, tensao e autonomias."""
    C = float(caso["C"]); L = float(caso["L"])
    A = C * L
    h = float(caso.get("altura_teto", caso.get("pe_direito", 6.0)))
    viga = float(caso.get("viga_m", 0.0))
    n_pont = numero_detectores_pontuais(A, h, viga)
    if n_pont is not None:
        tipo_det, n_det, cob = "pontual", n_pont, cobertura_detector(h, viga)
    else:
        tipo_det, n_det, cob = "linear", numero_detectores_lineares(C, L), None
    n_acion = numero_acionadores(C, L)
    return {"area_m2": A, "tipo_detector": tipo_det, "N_detectores": n_det,
            "cobertura_m2": cob, "N_acionadores": n_acion,
            "tensao_Vcc": TENSAO_SISTEMA_VCC,
            "autonomia_supervisao_h": AUTONOMIA_SUPERVISAO_H,
            "autonomia_alarme_min": AUTONOMIA_ALARME_MIN,
            "resposta_max_s": RESPOSTA_ACIONADOR_S,
            "afastamento_cabo_energia_m": AFASTAMENTO_CABO_ENERGIA_M,
            "OK": n_det >= 1 and n_acion >= 1}


def _selftest():
    """Afere contra a NBR 17240:2010 (5.4 + 5.5 + Anexo B)."""
    # cobertura por viga
    assert cobertura_detector(6.0, 0.0) == 81.0
    assert abs(cobertura_detector(6.0, 0.30) - 54.0) < 1e-9
    assert cobertura_detector(6.0, 0.70) == 40.5
    assert cobertura_detector(9.0) is None            # teto > 8 m -> linear
    # exemplo NBR: 12 x 23 m -> area 276 m2 -> 4 detectores (81 m2)
    assert numero_detectores_pontuais(12.0 * 23.0, 6.0) == 4, numero_detectores_pontuais(276.0, 6.0)
    # galpao 40x20=800 m2, teto 6 m -> ceil(800/81) = 10 detectores
    assert numero_detectores_pontuais(800.0, 6.0) == 10
    # com viga > 0,6 -> 40,5 m2 -> 20 detectores
    assert numero_detectores_pontuais(800.0, 6.0, 0.70) == 20
    # teto alto 12 m: linear -> feixes 20/15=2 x trechos 40/100=1 = 2
    d = dimensiona_deteccao_alarme({"C": 40.0, "L": 20.0, "altura_teto": 12.0})
    assert d["tipo_detector"] == "linear" and d["N_detectores"] == 2
    # acionadores: 800 m2 / (pi*30^2=2827) -> 1 (40x20 curto: 1 basta, <= 30 m)
    assert numero_acionadores(40.0, 20.0) == 1
    assert numero_acionadores(200.0, 60.0) >= 2       # galpao grande -> mais de 1
    # PISO por comprimento: galpao ALONGADO 200 x 12 m -> a area sozinha daria 1, mas
    # ceil(200/60) = 4 (a ponta a 100 m do centro violaria os 30 m). Correcao contra-seguranca.
    assert numero_acionadores(200.0, 12.0) == 4, numero_acionadores(200.0, 12.0)
    assert numero_acionadores(12.0, 200.0) == 4       # simetrico (largura longa)
    # central: 24 Vcc, autonomia 24h + 15min
    dd = dimensiona_deteccao_alarme({"C": 40.0, "L": 20.0, "altura_teto": 6.0})
    assert dd["tensao_Vcc"] == 24.0 and dd["autonomia_supervisao_h"] == 24.0
    assert dd["autonomia_alarme_min"] == 15.0 and dd["N_detectores"] == 10 and dd["OK"]
    print("deteccao_alarme_nbr17240 self-test PASSED (NBR 17240:2010)")


if __name__ == "__main__":
    _selftest()
