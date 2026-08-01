# ============================================================================
# spda_nbr5419.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Projeto do SPDA (Sistema de Protecao contra Descargas Atmosfericas) do galpao,
# ABNT NBR 5419 (partes 1 a 4, ed. 2026). Cobre:
#   1) GERENCIAMENTO DE RISCO (parte 2, Anexo A): area de exposicao equivalente
#      Ad = L*W + 2*(3H)*(L+W) + pi*(3H)^2 ; numero de eventos perigosos por
#      descarga direta Nd = Ng*Ad*Cd*1e-6 (Ng densidade de raios/km2.ano, Cd fator
#      de localizacao, Tab.A.1). Protecao necessaria se R1 > RT = 1e-5.
#   2) NIVEL DE PROTECAO (NP I..IV, parte 1 Tab.4): corrente de pico minima e raio
#      da esfera rolante (20/30/45/60 m); eficiencia estimada (98/95/90/80%).
#   3) CAPTACAO (parte 3 Tab.2): modulo da malha (5/10/15/20 m) por NP.
#   4) DESCIDAS (parte 3 Tab.5): espacamento medio (10/10/15/20 m) por NP; numero
#      minimo = perimetro/espacamento.
#   5) SECOES MINIMAS (parte 3 Tab.7/8, cobre): captor 35, descida <=20m 16 / >20m
#      35, eletrodo de aterramento 50 mm2.
# Todos os valores LIDOS do PDF da NBR 5419-1/2/3 via NotebookLM - NAO de memoria.
# Unidades: L,W,H,a,b em m; Ad em m2; Ng em 1/km2.ano; seccoes em mm2.
# ============================================================================
"""SPDA do galpao (NBR 5419-1/2/3/4): gerenciamento de risco (Nd, RT=1e-5), nivel
de protecao, esfera rolante/malha, descidas e secoes minimas. Valores via NotebookLM."""

from __future__ import annotations

import math

RT_R1 = 1e-5              # risco tolerable de perda de vida humana (parte 2, Tab.4)
RT_R3 = 1e-4              # risco tolerable de perda de patrimonio cultural

# Tabela por nivel de protecao (NP): parte 1 Tab.4 + parte 3 Tab.2/Tab.5.
# {NP: {Ipico_kA, esfera_m, malha_m, descida_m, eficiencia}}
NIVEL_PROTECAO = {
    "I":   {"Ipico_kA": 3,  "esfera_m": 20, "malha_m": 5,  "descida_m": 10, "eficiencia": 0.98},
    "II":  {"Ipico_kA": 5,  "esfera_m": 30, "malha_m": 10, "descida_m": 10, "eficiencia": 0.95},
    "III": {"Ipico_kA": 10, "esfera_m": 45, "malha_m": 15, "descida_m": 15, "eficiencia": 0.90},
    "IV":  {"Ipico_kA": 16, "esfera_m": 60, "malha_m": 20, "descida_m": 20, "eficiencia": 0.80},
}

# Secoes minimas de cobre (parte 3, Tab.7/8), mm2
SECAO_CAPTOR_MM2 = 35
SECAO_DESCIDA_ATE20M_MM2 = 16
SECAO_DESCIDA_ACIMA20M_MM2 = 35
SECAO_ELETRODO_MM2 = 50

# Fator de localizacao Cd (parte 2, Tab.A.1)
CD_LOCALIZACAO = {
    "cercada_mais_altos": 0.25,
    "cercada_mesma_altura": 0.5,
    "isolada": 1.0,
    "topo_colina": 2.0,
}


def area_exposicao(L, W, H):
    """Area de exposicao equivalente de estrutura retangular isolada (parte 2, A.1):
    Ad = L*W + 2*(3H)*(L+W) + pi*(3H)^2. L,W,H em m -> m2."""
    return L * W + 2.0 * (3.0 * H) * (L + W) + math.pi * (3.0 * H) ** 2


def frequencia_descargas(Ng, Ad, Cd=1.0):
    """Numero de eventos perigosos por descarga direta (parte 2, A.3):
    Nd = Ng*Ad*Cd*1e-6. Ng em 1/km2.ano, Ad em m2 -> eventos/ano."""
    return Ng * Ad * Cd * 1e-6


def protecao_necessaria(R1, RT=RT_R1):
    """Regra de decisao (parte 1, 6.2.3): protecao necessaria se R1 > RT."""
    return R1 > RT


def nivel_por_eficiencia(E):
    """Menor NP (mais eficiente) cuja eficiencia estimada atende E requerida.
    E < 0,80 -> nenhum nivel isolado atende (combinar metodos)."""
    for np_ in ("IV", "III", "II", "I"):        # do menos ao mais exigente
        if NIVEL_PROTECAO[np_]["eficiencia"] >= E:
            return np_
    return None if E > 0.98 else "I"


def numero_descidas(perimetro, NP):
    """Numero minimo de descidas = perimetro / espacamento medio (Tab.5),
    arredondado p/ cima; minimo de 2 (parte 3, 5.4.3)."""
    espac = NIVEL_PROTECAO[NP]["descida_m"]
    return max(2, math.ceil(perimetro / espac))


def secao_descida(H):
    """Secao minima do condutor de descida (cobre) por altura da estrutura."""
    return SECAO_DESCIDA_ATE20M_MM2 if H <= 20.0 else SECAO_DESCIDA_ACIMA20M_MM2


def dimensiona_spda(caso):
    """Projeta o SPDA de um galpao retangular.
    caso: {L, W, H, NP(ou requerer via R1), Ng(opc), Cd(opc), R1(opc)}.
    Se R1 e Ng dados, avalia a necessidade; NP pode vir explicito ou por eficiencia.
    Retorna dict com Ad, Nd, NP, esfera, malha, descidas e secoes."""
    L = float(caso["L"]); W = float(caso["W"]); H = float(caso["H"])
    Ad = area_exposicao(L, W, H)
    Cd = float(caso.get("Cd", 1.0))
    Nd = frequencia_descargas(caso["Ng"], Ad, Cd) if caso.get("Ng") is not None else None

    R1 = caso.get("R1")
    necessario = protecao_necessaria(R1) if R1 is not None else None
    NP = caso.get("NP")
    if NP is None and R1 is not None and necessario:
        E_req = 1.0 - RT_R1 / R1           # eficiencia requerida p/ reduzir R1 a RT
        NP = nivel_por_eficiencia(E_req)
    NP = NP or "III"                        # default conservador se nao especificado

    npd = NIVEL_PROTECAO[NP]
    perimetro = 2.0 * (L + W)
    return {"Ad_m2": Ad, "Nd_ano": Nd, "R1": R1, "protecao_necessaria": necessario,
            "NP": NP, "esfera_m": npd["esfera_m"], "malha_m": npd["malha_m"],
            "eficiencia": npd["eficiencia"], "Ipico_kA": npd["Ipico_kA"],
            "perimetro_m": perimetro, "n_descidas": numero_descidas(perimetro, NP),
            "secao_captor_mm2": SECAO_CAPTOR_MM2, "secao_descida_mm2": secao_descida(H),
            "secao_eletrodo_mm2": SECAO_ELETRODO_MM2,
            "OK": (necessario is not True) or NP is not None}


def _selftest():
    """Afere as formulas contra valores calculados a mao (galpao 40x20x6 m)."""
    Ad = area_exposicao(40.0, 20.0, 6.0)
    # 800 + 2*18*60 + pi*18^2 = 800 + 2160 + 1017,88 = 3977,88
    assert abs(Ad - 3977.88) < 0.1, Ad
    Nd = frequencia_descargas(5.0, Ad, 1.0)
    assert abs(Nd - 0.0198894) < 1e-6, Nd
    assert protecao_necessaria(2e-5) and not protecao_necessaria(5e-6)
    # tabelas por nivel
    assert NIVEL_PROTECAO["I"]["esfera_m"] == 20 and NIVEL_PROTECAO["IV"]["malha_m"] == 20
    assert NIVEL_PROTECAO["III"]["descida_m"] == 15
    # descidas: perimetro 120 m, NP III (espac 15) -> 8
    assert numero_descidas(120.0, "III") == 8
    assert numero_descidas(10.0, "I") == 2                 # minimo 2
    # secoes: descida 16mm2 (H<=20), eletrodo 50, captor 35
    r = dimensiona_spda({"L": 40.0, "W": 20.0, "H": 6.0, "NP": "III", "Ng": 5.0,
                         "R1": 2e-5})
    assert r["secao_descida_mm2"] == 16 and r["secao_eletrodo_mm2"] == 50
    assert r["n_descidas"] == 8 and r["esfera_m"] == 45
    assert r["protecao_necessaria"] is True
    # selecao de NP por eficiencia
    assert nivel_por_eficiencia(0.90) == "III"
    assert nivel_por_eficiencia(0.96) == "I"               # >0,95 -> so NP I (0,98) atende
    print("spda_nbr5419 self-test PASSED (Ad=3977,9 m2 galpao 40x20x6 + tabelas NP)")


if __name__ == "__main__":
    _selftest()
