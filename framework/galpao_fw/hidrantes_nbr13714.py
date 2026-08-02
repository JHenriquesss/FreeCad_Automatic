# ============================================================================
# hidrantes_nbr13714.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Sistema de HIDRANTES E MANGOTINHOS de combate a incendio do galpao (ABNT NBR
# 13714:2000), 5o modulo do vertical de seguranca contra incendio (protecao ATIVA
# por agua, operada por pessoas):
#   1) TIPO DE SISTEMA (Tabela 1): 1 = mangotinho (mangueira semi-rigida 25/32 mm,
#      esguicho regulavel, 1 saida, 80/100 L/min); 2 = hidrante (mangueira 40 mm,
#      jato compacto 16 mm, 2 saidas, 300 L/min); 3 = hidrante (mangueira 65 mm,
#      jato compacto 25 mm, 2 saidas, 900 L/min). Mangueira <= 30 m (lances de 15 m).
#   2) APLICABILIDADE (Anexo D, Tab.D.1): exige sistema se area > 750 m2 e/ou altura
#      > 12 m. GALPAO/INDUSTRIA = Grupo I: I-1 (<=300 MJ/m2) e I-2 (300-1200, depositos)
#      -> Tipo 2 ; I-3 (>1200 MJ/m2 ou perigosos) -> Tipo 3.
#   3) DIMENSIONAMENTO (5.3): 2 jatos mais desfavoraveis simultaneos (qualquer tipo);
#      qualquer ponto alcancado por 1 (tipo 1) ou 2 (tipos 2/3) esguichos pelo trajeto
#      REAL da mangueira (desconsidera o alcance do jato). Alcance do jato compacto
#      >= 8 m (4.4.1). Pressao entre esguichos <= 2x a do mais desfavoravel; maxima de
#      trabalho <= 1000 kPa (100 mca).
#   4) RESERVA DE INCENDIO (5.4.2): V = Q * t ; Q = vazao de DUAS saidas (Tab.1) ;
#      t = 60 min (tipos 1 e 2) / 30 min (tipo 3). V em litros.
# Valores LIDOS do PDF da NBR 13714:2000 via NotebookLM - NAO de memoria.
# Unidades: area em m2; comprimento/altura em m; vazao em L/min; reserva em L/m3;
# pressao em kPa; diametros em mm.
# ============================================================================
"""Hidrantes e mangotinhos do galpao (NBR 13714:2000): tipo de sistema por ocupacao,
vazao por saida, 2 jatos simultaneos, numero de hidrantes e reserva V=Q*t."""

from __future__ import annotations

import math

# Tabela 1 - tipos de sistema. vazao_Lmin = por SAIDA (esguicho); tempo_min = 5.4.2.
TIPO_SISTEMA = {
    1: {"nome": "mangotinho", "esguicho": "regulavel", "mangueira_mm": (25, 32),
        "comp_max_m": 30, "saidas": 1, "vazao_Lmin": 100, "orificio_mm": None,
        "tempo_min": 60},
    2: {"nome": "hidrante", "esguicho": "jato compacto 16 mm ou regulavel",
        "mangueira_mm": (40,), "comp_max_m": 30, "saidas": 2, "vazao_Lmin": 300,
        "orificio_mm": 16, "tempo_min": 60},
    3: {"nome": "hidrante", "esguicho": "jato compacto 25 mm ou regulavel",
        "mangueira_mm": (65,), "comp_max_m": 30, "saidas": 2, "vazao_Lmin": 900,
        "orificio_mm": 25, "tempo_min": 30},
}

# Anexo D - tipo de sistema exigido por ocupacao (foco no galpao = Grupo I). Cada
# entrada: (tipo, vazao_saida_Lmin ou None p/ usar a da Tabela 1).
OCUPACAO_TIPO = {
    "residencial_A": (1, 80),                 # D.2
    "geral_B_D_E_H_F1a5": (1, 100),           # D.3 (comercio/servico/escola/hospital)
    "reuniao_C_F6a8": (2, None),              # D.4 (saidas duplas 40 mm)
    "industrial_I1": (2, None),               # baixo risco (<= 300 MJ/m2)
    "industrial_I2": (2, None),               # medio risco (300-1200) / depositos
    "industrial_I3": (3, None),               # alto risco (> 1200 MJ/m2 ou perigosos)
}

AREA_MIN_EXIGE_M2 = 750.0        # D.1: > 750 m2 e/ou > 12 m -> exige sistema
ALTURA_MIN_EXIGE_M = 12.0
ALCANCE_JATO_MIN_M = 8.0         # 4.4.1
PRESSAO_MAX_TRABALHO_KPA = 1000.0   # 100 mca (5.3.7, recomendado)
N_JATOS_SIMULTANEOS = 2          # 5.3.3 (dois jatos mais desfavoraveis, qualquer tipo)
DIST_TOMADA_PORTA_MAX_M = 5.0    # 5.2.1 a) proximo das portas/acessos
ALTURA_TOMADA_M = (1.0, 1.5)     # 5.2.1 d) 1,0 a 1,5 m do piso


def exige_sistema(area_m2, altura_m):
    """Exige sistema de hidrantes/mangotinhos? (D.1: area > 750 m2 e/ou altura > 12 m)."""
    return area_m2 > AREA_MIN_EXIGE_M2 or altura_m > ALTURA_MIN_EXIGE_M


def tipo_por_ocupacao(ocupacao):
    """Tipo de sistema exigido pela ocupacao (Anexo D). Retorna (tipo, vazao_ou_None)."""
    try:
        return OCUPACAO_TIPO[ocupacao]
    except KeyError:
        raise ValueError("[A CONFIRMAR] ocupacao '%s' sem tipo de sistema na Tab.D.1 "
                         "(NBR 13714 Anexo D)." % ocupacao)


def vazao_saida(tipo, vazao_override=None):
    """Vazao por saida (L/min) do tipo (Tabela 1), com override da Tab.D.1 (ex. 80)."""
    if vazao_override is not None:
        return float(vazao_override)
    return float(TIPO_SISTEMA[tipo]["vazao_Lmin"])


def reserva_incendio(tipo, vazao_override=None):
    """Reserva de incendio (5.4.2): V = Q * t ; Q = vazao de DUAS saidas ; t = 60 min
    (tipos 1 e 2) / 30 min (tipo 3). Retorna (V_litros, Q_Lmin, t_min)."""
    q1 = vazao_saida(tipo, vazao_override)
    Q = 2.0 * q1                                   # sempre duas saidas (5.4.2)
    t = TIPO_SISTEMA[tipo]["tempo_min"]
    return Q * t, Q, t


def jatos_por_ponto(tipo):
    """Nº de esguichos que devem alcancar CADA ponto da area (5.3.2): 1 (tipo 1) ou
    2 (tipos 2 e 3). E' o nº de saidas do tipo (Tabela 1)."""
    return 1 if int(tipo) == 1 else 2


def numero_hidrantes(C, L, tipo):
    """Numero de hidrantes/mangotinhos p/ cobrir o galpao C x L (m). Regra 5.3.2:
    "qualquer ponto da area a ser protegida seja alcancado por UM (tipo 1) ou DOIS
    (tipos 2 e 3) esguichos, considerando-se o comprimento da(s) mangueira(s) e seu
    TRAJETO REAL e DESCONSIDERANDO-SE o alcance do jato de agua". Portanto o passo da
    malha e' o comprimento da mangueira (Tabela 1 = 30 m), NAO o alcance do jato (8 m,
    4.4.1 - excluido de proposito). ESTIMATIVA por MALHA retangular: uma tomada por
    celula R x R (ceil(C/R) x ceil(L/R)) cobre cada ponto com UM jato; tipos 2/3
    exigem DOIS jatos por ponto -> multiplica a malha por 2. R e' o alcance em linha
    reta (limite superior do trajeto real, que serpenteia): confirmar o leiaute real
    (portas <=5 m, obstaculos, 5.2.1) - a malha pode subir. Minimo = nº de saidas."""
    R = float(TIPO_SISTEMA[tipo]["comp_max_m"])
    n_jatos = jatos_por_ponto(tipo)
    celulas = math.ceil(C / R) * math.ceil(L / R)        # malha, nao o maior lado
    n = celulas * n_jatos                                 # 2 jatos por ponto nos tipos 2/3
    minimo = TIPO_SISTEMA[tipo]["saidas"]
    return max(minimo, n)


def dimensiona_hidrantes(caso):
    """Projeta o sistema de hidrantes/mangotinhos do galpao (NBR 13714).
    caso: {C, L, altura_m(=pe_direito), ocupacao(='industrial_I2'), tipo(opc override)}.
    Retorna tipo, vazao, reserva, n_hidrantes, mangueira/esguicho e a exigencia."""
    C = float(caso["C"]); L = float(caso["L"])
    A = C * L
    h = float(caso.get("altura_m", caso.get("pe_direito", 6.0)))
    ocup = caso.get("ocupacao", "industrial_I2")
    if caso.get("tipo") is not None:
        tipo, vaz_over = int(caso["tipo"]), caso.get("vazao_saida")
        if tipo not in TIPO_SISTEMA:
            raise ValueError("[A CONFIRMAR] tipo de sistema '%s' inexistente na NBR 13714 "
                             "(use 1, 2 ou 3)." % tipo)
    else:
        tipo, vaz_over = tipo_por_ocupacao(ocup)
    ts = TIPO_SISTEMA[tipo]

    V_L, Q, t = reserva_incendio(tipo, vaz_over)
    n_hid = numero_hidrantes(C, L, tipo)
    exige = exige_sistema(A, h)
    return {"ocupacao": ocup, "tipo": tipo, "sistema": ts["nome"],
            "exige_sistema": exige, "area_m2": A,
            "vazao_saida_Lmin": vazao_saida(tipo, vaz_over),
            "n_jatos_simultaneos": N_JATOS_SIMULTANEOS,
            "vazao_total_Lmin": Q, "tempo_min": t,
            "reserva_incendio_L": round(V_L, 0), "reserva_incendio_m3": round(V_L / 1000.0, 1),
            "N_hidrantes": n_hid, "mangueira_mm": ts["mangueira_mm"],
            "comprimento_mangueira_m": ts["comp_max_m"], "esguicho": ts["esguicho"],
            "orificio_esguicho_mm": ts["orificio_mm"], "alcance_jato_min_m": ALCANCE_JATO_MIN_M,
            "pressao_max_kPa": PRESSAO_MAX_TRABALHO_KPA,
            "dist_max_tomada_porta_m": DIST_TOMADA_PORTA_MAX_M,
            "altura_tomada_m": ALTURA_TOMADA_M,
            "OK": n_hid >= 1 and V_L > 0}


def _selftest():
    """Afere contra a NBR 13714:2000 (Tabela 1, Anexo D, 5.3.3, 5.4.2)."""
    # Tabela 1: vazoes por saida
    assert TIPO_SISTEMA[2]["vazao_Lmin"] == 300 and TIPO_SISTEMA[3]["vazao_Lmin"] == 900
    assert TIPO_SISTEMA[1]["mangueira_mm"] == (25, 32) and TIPO_SISTEMA[3]["mangueira_mm"] == (65,)
    assert TIPO_SISTEMA[2]["orificio_mm"] == 16 and TIPO_SISTEMA[3]["orificio_mm"] == 25
    # Anexo D: galpao industrial -> I-2 = Tipo 2 ; I-3 = Tipo 3
    assert tipo_por_ocupacao("industrial_I2") == (2, None)
    assert tipo_por_ocupacao("industrial_I3") == (3, None)
    assert tipo_por_ocupacao("residencial_A") == (1, 80)
    import pytest
    with pytest.raises(ValueError):
        tipo_por_ocupacao("inexistente")
    # exigencia D.1: > 750 m2 e/ou > 12 m
    assert exige_sistema(800.0, 6.0) and exige_sistema(500.0, 15.0)
    assert not exige_sistema(500.0, 6.0)
    # reserva 5.4.2: V = 2*vazao*t
    #  Tipo 2: 2*300*60 = 36 000 L = 36 m3
    V, Q, t = reserva_incendio(2)
    assert V == 36000.0 and Q == 600.0 and t == 60
    #  Tipo 3: 2*900*30 = 54 000 L = 54 m3
    V3, Q3, t3 = reserva_incendio(3)
    assert V3 == 54000.0 and Q3 == 1800.0 and t3 == 30
    #  Tipo 1 (grupo A, 80 L/min): 2*80*60 = 9 600 L
    assert reserva_incendio(1, 80)[0] == 9600.0
    # cobertura 5.3.2 por MALHA (passo = mangueira 30 m; jato de 8 m NAO conta):
    #  - tipo 1 (1 jato/ponto): malha ceil(C/30)*ceil(L/30), sem duplicar
    assert jatos_por_ponto(1) == 1 and jatos_por_ponto(2) == 2 and jatos_por_ponto(3) == 2
    assert numero_hidrantes(40.0, 20.0, 1) == 2      # ceil(40/30)*ceil(20/30)=2*1
    #  - tipo 2/3 (2 jatos/ponto): DOBRA a malha -> 40x20 = 2*1*2 = 4
    assert numero_hidrantes(40.0, 20.0, 2) == 4 and numero_hidrantes(40.0, 20.0, 3) == 4
    #  - galpao ALONGADO 200x12 (o caso que a heuristica de maior-lado subdimensionava):
    #    malha ceil(200/30)*ceil(12/30)=7*1=7 ; tipo 2 dobra -> 14 (antes: max(7,..)=7)
    assert numero_hidrantes(200.0, 12.0, 2) == 14
    #  - quadrado grande 60x60 tipo 2: malha 2*2=4, dobra -> 8 (o "max de lado" daria 2)
    assert numero_hidrantes(60.0, 60.0, 2) == 8
    # galpao 40x20 industrial medio -> Tipo 2, reserva 36 m3, 4 hidrantes (2 jatos/malha)
    r = dimensiona_hidrantes({"C": 40.0, "L": 20.0, "altura_m": 6.0})
    assert r["tipo"] == 2 and r["sistema"] == "hidrante"
    assert r["reserva_incendio_m3"] == 36.0 and r["vazao_total_Lmin"] == 600.0
    assert r["N_hidrantes"] == 4 and r["esguicho"].startswith("jato compacto 16")
    assert r["exige_sistema"] and r["n_jatos_simultaneos"] == 2 and r["OK"]
    # alto risco (I-3) -> Tipo 3, mangueira 65 mm, reserva 54 m3
    r3 = dimensiona_hidrantes({"C": 40.0, "L": 20.0, "altura_m": 6.0,
                               "ocupacao": "industrial_I3"})
    assert r3["tipo"] == 3 and r3["mangueira_mm"] == (65,) and r3["reserva_incendio_m3"] == 54.0
    print("hidrantes_nbr13714 self-test PASSED (NBR 13714:2000)")


if __name__ == "__main__":
    _selftest()
