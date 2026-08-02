# ============================================================================
# condutores_nbr5410.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Dimensiona a SECAO de um condutor de baixa tensao pelos TRES criterios da ABNT
# NBR 5410:2004, 2a etapa do projeto eletrico:
#   1) CAPACIDADE DE CONDUCAO DE CORRENTE (ampacidade), 6.2.5: corrigir a corrente
#      de projeto pelos fatores de temperatura (FCT, Tab.40) e agrupamento (FCA,
#      Tab.42) -> IC = IB/(FCT*FCA); escolher a menor secao com Iz >= IC nas
#      Tabelas 36/38 (PVC 70C) ou 37/39 (EPR/XLPE 90C), pelo metodo de referencia.
#   2) LIMITE DE QUEDA DE TENSAO, 6.2.7: metodo da queda unitaria
#      dV% = dVu*IB*L*100/V (L em km) <= limite (5% rede publica; 7% SE propria;
#      terminal <= 4%). dVu (V/A.km) das tabelas de Cotrim/Creder por secao e fp.
#   3) SECAO MINIMA DE CURTO (5.3.5 / 6.3.4.3): S >= IC_cc*raiz(t)/k, k da Tab.30
#      (Cu/PVC=115, Cu/EPR=143). E a SECAO MINIMA absoluta da Tab.47 (iluminacao
#      1,5mm2; forca 2,5mm2). A secao final e o MAIOR entre os quatro criterios.
#   4) CONDUTORES EM PARALELO (6.2.5.7): se IC excede o Iz da maior secao tabelada
#      (300mm2), usa N condutores IGUAIS por fase (mesma secao/material/comprimento);
#      corrente e queda por condutor caem p/ 1/N. Tabela estendida ate 300 mm2.
# Todas as tabelas (36/37/38/39, 40, 42, 47, 30 e queda unitaria) LIDAS do PDF da
# NBR 5410 e de Cotrim/Creder via NotebookLM - NAO de memoria. Solver aferido
# contra o exercicio resolvido do chuveiro 6000W/220V (Creder/pratico) -> 6 mm2.
# Unidades: corrente em A; comprimento em km; tensao em V; secao em mm2.
# ============================================================================
"""Dimensionamento de condutor BT pelos 3 criterios da NBR 5410 (ampacidade +
queda de tensao + curto) com secao minima. Tabelas lidas via NotebookLM."""

from __future__ import annotations

import math

# secoes nominais comerciais cobertas pelas tabelas (mm2)
SECOES = [2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]

# --- Ampacidade (A): AMPACIDADE[isol][metodo][n_cond] = {secao: Iz} -----------
# Cobre. PVC 70C: Tab.36 (B1) / Tab.38 (F). EPR/XLPE 90C: Tab.37 (B1) / Tab.39 (F).
# secoes grandes (150-300 mm2) so p/ 3 condutores carregados (trifasico) e p/ B1 2cond
# (Tab.36-39; valores lidos via NotebookLM). F 2cond grande nao tabelado aqui.
AMPACIDADE = {
    "PVC": {
        "B1": {2: {2.5: 24, 4: 32, 6: 41, 10: 57, 16: 76, 25: 101, 35: 125,
                   50: 151, 70: 192, 95: 232, 120: 269, 150: 309, 185: 353, 240: 415},
               3: {2.5: 21, 4: 28, 6: 36, 10: 50, 16: 68, 25: 89, 35: 110,
                   50: 134, 70: 171, 95: 207, 120: 239, 150: 275, 185: 314, 240: 370,
                   300: 426}},
        "F":  {2: {2.5: 31, 4: 41, 6: 53, 10: 73, 16: 99, 25: 131, 35: 162,
                   50: 196, 70: 251, 95: 304, 120: 352},
               3: {2.5: 24, 4: 33, 6: 43, 10: 60, 16: 82, 25: 110, 35: 137,
                   50: 167, 70: 216, 95: 264, 120: 308, 150: 356, 185: 409, 240: 485,
                   300: 561}},
    },
    "EPR": {
        "B1": {2: {2.5: 31, 4: 42, 6: 54, 10: 75, 16: 100, 25: 133, 35: 164,
                   50: 198, 70: 253, 95: 306, 120: 354, 150: 407, 185: 464, 240: 546},
               3: {2.5: 28, 4: 37, 6: 48, 10: 66, 16: 88, 25: 117, 35: 144,
                   50: 175, 70: 222, 95: 269, 120: 312, 150: 358, 185: 408, 240: 481,
                   300: 553}},
        "F":  {2: {2.5: 37, 4: 50, 6: 65, 10: 90, 16: 121, 25: 161, 35: 200,
                   50: 242, 70: 310, 95: 377, 120: 437},
               3: {2.5: 29, 4: 40, 6: 53, 10: 74, 16: 101, 25: 135, 35: 169,
                   50: 207, 70: 268, 95: 328, 120: 383, 150: 469, 185: 538, 240: 637,
                   300: 736}},
    },
}
# XLPE compartilha a tabela do EPR (mesma temperatura de 90C)
AMPACIDADE["XLPE"] = AMPACIDADE["EPR"]

# --- Tab.40: fator de correcao de temperatura (linhas nao-subterraneas) -------
# {temp_ambiente_C: (FCT_PVC, FCT_EPR)}. Interpolacao linear entre pontos.
_FCT = {10: (1.22, 1.15), 15: (1.17, 1.12), 20: (1.12, 1.08), 25: (1.06, 1.04),
        30: (1.00, 1.00), 35: (0.94, 0.96), 40: (0.87, 0.91), 45: (0.79, 0.87),
        50: (0.71, 0.82), 55: (0.61, 0.76), 60: (0.50, 0.71)}

# --- Tab.42: fator de correcao por agrupamento (feixe/camada unica) -----------
_FCA = {1: 1.00, 2: 0.80, 3: 0.70, 4: 0.65, 6: 0.57, 9: 0.50}

# --- Tab.47: secao minima do condutor de fase (cobre), por uso ----------------
SECAO_MINIMA = {"iluminacao": 1.5, "forca": 2.5, "sinalizacao": 0.5}

# --- Tab.30: constante k para secao minima de curto (cobre, S<=300mm2) ---------
K_CURTO = {"PVC": 115, "EPR": 143, "XLPE": 143}

# --- Queda de tensao unitaria dVu (V/A.km), cobre, eletroduto/calha nao-magn. -
# QUEDA_UNITARIA[sistema][fp] = {secao: dVu}. FP=0,80 completo (ate 120mm2);
# FP=0,95 parcial (fonte cita ate 35mm2) - usado p/ cargas de alto fp (resistivas).
QUEDA_UNITARIA = {
    "trifasico": {
        0.80: {2.5: 12.4, 4: 7.79, 6: 5.25, 10: 3.17, 16: 2.03, 25: 1.33,
               35: 0.98, 50: 0.76, 70: 0.55, 95: 0.43, 120: 0.36,
               150: 0.31, 185: 0.27, 240: 0.23, 300: 0.21},
        0.95: {2.5: 14.7, 4: 9.15, 6: 6.14, 10: 3.67, 16: 2.33, 25: 1.49, 35: 1.09},
    },
    "monofasico": {
        0.80: {2.5: 14.3, 4: 8.96, 6: 6.03, 10: 3.63, 16: 2.32, 25: 1.51,
               35: 1.12, 50: 0.86, 70: 0.62, 95: 0.48, 120: 0.40,
               150: 0.35, 185: 0.30, 240: 0.26},
        0.95: {2.5: 16.9, 4: 10.6, 6: 7.07, 10: 4.23, 16: 2.68, 25: 1.71, 35: 1.25},
    },
}

# limites de queda de tensao (6.2.7), por origem do suprimento (%)
DV_LIMITE = {"rede_publica": 5.0, "subestacao_propria": 7.0, "gerador_proprio": 7.0}
DV_TERMINAL_MAX = 4.0     # queda no ramal terminal (quadro -> equipamento)


def fct(temp_amb, isolacao):
    """Fator de correcao de temperatura (Tab.40), interpolado linearmente.
    isolacao 'PVC' -> indice 0; 'EPR'/'XLPE' -> indice 1."""
    idx = 0 if isolacao == "PVC" else 1
    temps = sorted(_FCT)
    if temp_amb <= temps[0]:
        return _FCT[temps[0]][idx]
    if temp_amb >= temps[-1]:
        return _FCT[temps[-1]][idx]
    if temp_amb in _FCT:
        return _FCT[temp_amb][idx]
    lo = max(t for t in temps if t < temp_amb)
    hi = min(t for t in temps if t > temp_amb)
    f = (temp_amb - lo) / (hi - lo)
    return _FCT[lo][idx] + f * (_FCT[hi][idx] - _FCT[lo][idx])


def fca(n_agrupados):
    """Fator de correcao por agrupamento (Tab.42). Para n nao tabelado usa o
    proximo n MAIOR tabelado (mais conservador) - nao inventa valor intermediario."""
    n = int(n_agrupados)
    if n <= 1:
        return 1.0
    if n in _FCA:
        return _FCA[n]
    maiores = [k for k in _FCA if k >= n]
    if maiores:
        return _FCA[min(maiores)]
    return _FCA[max(_FCA)]


def _fp_coluna(fp):
    """Coluna de queda unitaria: 0,95 para cargas de alto fp; 0,80 caso contrario."""
    return 0.95 if fp >= 0.90 else 0.80


def queda_unitaria(secao, sistema, fp):
    """dVu (V/A.km) para a secao. Se a secao faltar na coluna do fp (0,95 e
    parcial), cai para a coluna 0,80 (mais completa)."""
    col = _fp_coluna(fp)
    tab = QUEDA_UNITARIA[sistema]
    if secao in tab[col]:
        return tab[col][secao]
    return tab[0.80][secao]


def queda_pct(secao, IB, L_km, V, sistema, fp):
    """Queda de tensao percentual pelo metodo da queda unitaria (Creder 16.3.3)."""
    return queda_unitaria(secao, sistema, fp) * IB * L_km * 100.0 / V


def secao_por_ampacidade(IC, isolacao, metodo, n_cond):
    """Menor secao cujo Iz >= IC (corrente corrigida). Retorna (secao, Iz) ou
    (None, None) se nenhuma secao tabelada atende."""
    tab = AMPACIDADE[isolacao][metodo][n_cond]
    for s in SECOES:
        if s in tab and tab[s] >= IC:
            return s, tab[s]
    return None, None


def secao_por_queda(IB, L_km, V, sistema, fp, dv_max, s_inicial=None):
    """Menor secao com dV% <= dv_max. Retorna (secao, dV%)."""
    for s in SECOES:
        if s_inicial is not None and s < s_inicial:
            continue
        dv = queda_pct(s, IB, L_km, V, sistema, fp)
        if dv <= dv_max:
            return s, dv
    return None, None


def secao_por_curto(Icc, t_s, isolacao):
    """Secao minima de curto: S >= Icc*raiz(t)/k (Tab.30). Retorna a menor secao
    comercial >= ao valor calculado."""
    k = K_CURTO[isolacao]
    s_min = Icc * math.sqrt(t_s) / k
    for s in SECOES:
        if s >= s_min:
            return s, s_min
    return SECOES[-1], s_min


def dimensiona_condutor(circ):
    """Dimensiona a secao de fase pelos 3 criterios + secao minima.
    circ: {IB, V, L_km, sistema('trifasico'|'monofasico'), n_cond(2|3),
           isolacao('PVC'|'EPR'|'XLPE'), metodo('B1'|'F'), fp(=0,8),
           temp_amb(=30), n_agrupados(=1), uso('forca'|'iluminacao'),
           dv_max(ou origem), Icc(opcional), t_curto_s(opcional)}.
    Retorna dict com a secao final e o detalhe de cada criterio."""
    IB = float(circ["IB"])
    V = float(circ["V"])
    L = float(circ["L_km"])
    sistema = circ.get("sistema", "trifasico")
    n_cond = int(circ.get("n_cond", 3))
    isol = circ.get("isolacao", "PVC")
    metodo = circ.get("metodo", "B1")
    fp = float(circ.get("fp", 0.80))
    temp = float(circ.get("temp_amb", 30.0))
    n_agr = int(circ.get("n_agrupados", 1))
    uso = circ.get("uso", "forca")
    if "dv_max" in circ:
        dv_max = float(circ["dv_max"])
    else:
        dv_max = DV_LIMITE.get(circ.get("origem", "rede_publica"), 5.0)

    _fct = fct(temp, isol)
    _fca = fca(n_agr)
    IC = IB / (_fct * _fca)

    s_amp, Iz = secao_por_ampacidade(IC, isol, metodo, n_cond)
    # CONDUTORES EM PARALELO (NBR 5410 6.2.5.7): se IC excede o Iz da MAIOR secao
    # tabelada, usa N condutores iguais por fase (mesma secao/material/comprimento).
    n_par = 1
    if s_amp is None:
        tab = AMPACIDADE[isol][metodo][n_cond]
        s_max = max(tab)                              # maior secao com Iz nesta tabela
        iz_max = tab[s_max]
        n_par = max(2, math.ceil(IC / iz_max))
        s_amp = s_max
        Iz = iz_max * n_par                           # capacidade equivalente do grupo

    s_min = SECAO_MINIMA.get(uso, 2.5)
    s_min = s_min if s_min in SECOES else min(SECOES)   # ampacidade comeca em 2,5
    # queda: com N condutores em paralelo a corrente por condutor cai p/ IB/N,
    # entao a queda tambem cai p/ 1/N (resistencia equivalente /N).
    s_qda, dv = secao_por_queda(IB / n_par, L, V, sistema, fp, dv_max)
    s_cc, s_cc_calc = (None, None)
    if circ.get("Icc") and circ.get("t_curto_s"):
        s_cc, s_cc_calc = secao_por_curto(float(circ["Icc"]) / n_par,
                                          float(circ["t_curto_s"]), isol)

    candidatas = [c for c in (s_amp, s_min, s_qda, s_cc) if c is not None]
    secao = max(candidatas) if candidatas else None
    gov = "ampacidade" if secao == s_amp else ("queda" if secao == s_qda else
          ("curto" if secao == s_cc else "secao_minima"))

    dv_final = queda_pct(secao, IB / n_par, L, V, sistema, fp) if secao else None
    Iz_final = (AMPACIDADE[isol][metodo][n_cond].get(secao) or 0) * n_par if secao else None
    ok = (secao is not None
          and (dv_final is not None and dv_final <= dv_max))
    return {"IB": IB, "IC": IC, "FCT": _fct, "FCA": _fca,
            "secao_mm2": secao, "n_paralelo": n_par, "governante": gov,
            "secao_ampacidade": s_amp, "Iz": Iz_final, "Iz_ampacidade": Iz,
            "secao_minima": s_min, "secao_queda": s_qda, "dv_pct": dv_final,
            "dv_max": dv_max, "secao_curto": s_cc, "s_curto_calc_mm2": s_cc_calc,
            "isolacao": isol, "metodo": metodo, "n_cond": n_cond, "OK": ok}


def _selftest():
    """Afere contra o exercicio resolvido do chuveiro 6000W/220V (Creder 16.6):
    B1, PVC, agrupamento 3 circuitos (FCA=0,70), 30C, L=18m -> secao 6 mm2 pela
    ampacidade; dV% = 1,58% no condutor de 6 mm2."""
    IB = 6000.0 / 220.0                                   # 27,27 A
    r = dimensiona_condutor({"IB": IB, "V": 220.0, "L_km": 0.018,
                             "sistema": "monofasico", "n_cond": 2,
                             "isolacao": "PVC", "metodo": "B1", "fp": 1.0,
                             "temp_amb": 30.0, "n_agrupados": 3, "uso": "forca",
                             "dv_max": 4.0})
    assert abs(IB - 27.27) < 0.01
    assert abs(r["IC"] - 38.96) < 0.05, r["IC"]           # IB/0,70
    assert r["secao_ampacidade"] == 6, r["secao_ampacidade"]
    assert r["Iz"] == 53 or r["Iz_ampacidade"] == 41      # 6mm2 F=53 / B1=41
    assert r["Iz_ampacidade"] == 41, r["Iz_ampacidade"]
    assert r["secao_mm2"] == 6, r                          # ampacidade governa
    assert r["governante"] == "ampacidade"
    assert abs(r["dv_pct"] - 1.58) < 0.05, r["dv_pct"]     # 7,07*27,27*0,018*100/220
    assert r["OK"]
    # criterio de curto isolado: Icc=5000A, t=0,1s, PVC (k=115) -> S>=13,7 -> 16mm2
    s_cc, s_calc = secao_por_curto(5000.0, 0.1, "PVC")
    assert abs(s_calc - 13.75) < 0.1, s_calc
    assert s_cc == 16, s_cc
    # fatores de correcao pontuais
    assert fct(40, "PVC") == 0.87 and fct(40, "EPR") == 0.91
    assert abs(fct(37, "PVC") - (0.94 + 0.4 * (0.87 - 0.94))) < 1e-9   # interpola
    assert fca(3) == 0.70 and fca(1) == 1.0
    assert fca(5) == 0.57                                  # n=5 -> usa coluna 6 (conserv.)
    # CONDUTORES EM PARALELO: alimentador de 900 A (EPR F 3cond, Iz max 300mm2=736A)
    # -> IC=900 excede 736 -> 2 condutores de 300mm2 por fase.
    rp = dimensiona_condutor({"IB": 900.0, "V": 380.0, "L_km": 0.05,
                              "sistema": "trifasico", "n_cond": 3, "isolacao": "EPR",
                              "metodo": "F", "fp": 0.85, "temp_amb": 30.0,
                              "n_agrupados": 1, "uso": "forca", "dv_max": 7.0})
    assert rp["n_paralelo"] == 2 and rp["secao_mm2"] == 300, (rp["n_paralelo"], rp["secao_mm2"])
    assert rp["Iz"] == 736 * 2 and rp["OK"]
    # secao unica ainda vale p/ 300 A (nao vira paralelo)
    r300 = dimensiona_condutor({"IB": 300.0, "V": 380.0, "L_km": 0.05,
                                "sistema": "trifasico", "n_cond": 3, "isolacao": "EPR",
                                "metodo": "F", "fp": 0.85, "dv_max": 7.0})
    assert r300["n_paralelo"] == 1 and r300["secao_mm2"] == 95, r300["secao_mm2"]
    print("condutores_nbr5410 self-test PASSED (Creder 6mm2 + curto/FCT/FCA + paralelo)")


if __name__ == "__main__":
    _selftest()
