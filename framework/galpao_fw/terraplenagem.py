# ============================================================================
# terraplenagem.py - O QUE ESTE SCRIPT FAZ / CALCULA
# TERRAPLENAGEM e DRENAGEM DO TERRENO (movimento de terra do lote - o que vem ANTES
# da fundacao). Duas frentes:
#   (1) CORTE/ATERRO por GRADE: dada a malha de cotas do terreno natural e a cota da
#       PLATAFORMA (greide), calcula os volumes de corte (terreno acima do greide) e
#       aterro (abaixo), pelo metodo da grade (volume = soma das celulas . area).
#       greide_equilibrio: acha por bisseccao a cota que EQUILIBRA corte e aterro
#       considerando o EMPOLAMENTO (bulking) - o corte "incha" ao ser escavado e o
#       aterro exige mais material solto p/ compactar. movimento_terra: importar ou
#       exportar terra (bota-fora / emprestimo).
#   (2) DRENAGEM SUPERFICIAL do lote pelo METODO RACIONAL: Q = C.i.A/360 (Q em m3/s,
#       C=coef. de escoamento, i=intensidade da chuva mm/h, A=area em ha) - metodo
#       consagrado (DNIT/manuais). Canaleta dimensionada por MANNING
#       (Q = (1/n).A.Rh^(2/3).S^(1/2)) - hidraulica de canal, secao retangular.
# Tudo e' ALGORITMO/mecanica (grade, bisseccao, Manning, racional) - nao ha tabela
# de norma escondida. Fatores de empolamento/compactacao e coef. de escoamento sao
# propriedades do material/solo (ENTRADA, A CONFIRMAR ensaio). Intensidade da chuva
# (curva IDF) e' DADO DE SITIO (A CONFIRMAR). STATELESS. Unidades: m, m2, m3, m3/s.
# ============================================================================
"""Terraplenagem (corte/aterro por grade + greide de equilibrio) e drenagem
superficial (metodo racional + Manning). STATELESS. Empolamento/IDF = A CONFIRMAR."""

from __future__ import annotations


def volumes_corte_aterro(grid_terreno, cota_plataforma, area_celula_m2):
    """Volumes de corte e aterro pelo metodo da grade. grid_terreno: matriz (lista de
    listas) de cotas do terreno natural (m); cota_plataforma: cota do greide (m);
    area_celula_m2: area de influencia de cada no da grade. Corte = terreno ACIMA do
    greide; aterro = ABAIXO. Retorna dict (m3)."""
    corte = aterro = 0.0
    n = 0
    for linha in grid_terreno:
        for cota in linha:
            dh = cota - cota_plataforma
            if dh > 0:
                corte += dh * area_celula_m2
            else:
                aterro += (-dh) * area_celula_m2
            n += 1
    return {"corte_m3": round(corte, 1), "aterro_m3": round(aterro, 1),
            "n_celulas": n, "cota_plataforma": cota_plataforma}


def greide_equilibrio(grid_terreno, area_celula_m2, empolamento=1.0, tol=1e-3,
                      max_iter=100):
    """Acha por bisseccao a cota de plataforma que EQUILIBRA corte e aterro. O corte
    escavado rende corte/empolamento de volume compactado util p/ o aterro (o solo
    incha ao ser solto e volta a densificar). Equilibrio: corte_compactado = aterro.
    empolamento >= 1 (fator de conversao volume solto/compactado). Retorna dict."""
    cotas = [c for linha in grid_terreno for c in linha]
    lo, hi = min(cotas), max(cotas)
    meio = (lo + hi) / 2.0
    for _ in range(max_iter):
        meio = (lo + hi) / 2.0
        v = volumes_corte_aterro(grid_terreno, meio, area_celula_m2)
        # corte disponivel p/ aterro apos empolamento/compactacao
        corte_util = v["corte_m3"] / empolamento
        dif = corte_util - v["aterro_m3"]
        if abs(dif) < tol * max(1.0, v["aterro_m3"]):
            break
        # corte_util cresce quando a plataforma BAIXA (mais terreno acima)
        if dif > 0:                 # sobra corte -> subir a plataforma (menos corte)
            lo = meio
        else:                       # falta corte -> descer a plataforma
            hi = meio
    v = volumes_corte_aterro(grid_terreno, meio, area_celula_m2)
    return {"cota_equilibrio": round(meio, 3), "corte_m3": v["corte_m3"],
            "aterro_m3": v["aterro_m3"], "empolamento": empolamento,
            "corte_util_m3": round(v["corte_m3"] / empolamento, 1)}


def movimento_terra(corte_m3, aterro_m3, empolamento=1.0):
    """Balanco de terra: corte util (apos empolamento) - aterro. Positivo -> SOBRA
    (bota-fora); negativo -> FALTA (emprestimo/importacao). Volumes em m3 (solto p/
    o transporte usa o corte com empolamento)."""
    corte_util = corte_m3 / empolamento
    saldo = corte_util - aterro_m3
    return {"corte_util_m3": round(corte_util, 1), "aterro_m3": round(aterro_m3, 1),
            "saldo_m3": round(saldo, 1),
            "acao": "bota-fora (exportar)" if saldo > 0 else
                    ("emprestimo (importar)" if saldo < 0 else "equilibrado"),
            "volume_transporte_solto_m3": round(abs(saldo) * empolamento, 1)}


def vazao_racional(C, i_mm_h, A_ha):
    """Vazao de pico pelo METODO RACIONAL: Q = C.i.A/360 [m3/s] (C adimensional,
    i em mm/h, A em ha). C e i (curva IDF) = dados de projeto/sitio (A CONFIRMAR)."""
    if not (0 < C <= 1) or i_mm_h <= 0 or A_ha <= 0:
        raise ValueError("[A CONFIRMAR] C (0-1), i (mm/h) e A (ha) devem ser > 0")
    return C * i_mm_h * A_ha / 360.0


def canaleta_manning(Q_m3s, largura_m, declividade, n_manning=0.015,
                     altura_max_m=1.0):
    """Dimensiona a lamina d'agua de uma canaleta RETANGULAR por MANNING:
    Q = (1/n).A.Rh^(2/3).S^(1/2), A=b.y, Rh=A/(b+2y). Resolve y (bisseccao) p/ a
    vazao Q. n=rugosidade (0,015 concreto). Retorna a altura d'agua e a verificacao."""
    if Q_m3s <= 0 or largura_m <= 0 or declividade <= 0:
        raise ValueError("Q, largura e declividade devem ser > 0")

    def _Q(y):
        A = largura_m * y
        Rh = A / (largura_m + 2 * y)
        return (1.0 / n_manning) * A * Rh ** (2.0 / 3.0) * declividade ** 0.5

    lo, hi = 1e-4, altura_max_m
    if _Q(hi) < Q_m3s:                          # nem cheia a canaleta vence -> alertar
        return {"y_m": round(hi, 3), "capacidade_m3s": round(_Q(hi), 4),
                "OK": False, "nota": "canaleta insuficiente na altura max - alargar "
                "ou aumentar declividade", "largura_m": largura_m}
    for _ in range(100):
        y = (lo + hi) / 2.0
        if _Q(y) < Q_m3s:
            lo = y
        else:
            hi = y
    y = (lo + hi) / 2.0
    return {"y_m": round(y, 3), "largura_m": largura_m, "declividade": declividade,
            "vazao_m3s": round(Q_m3s, 4), "borda_livre_m": round(altura_max_m - y, 3),
            "OK": True, "capacidade_m3s": round(_Q(y), 4)}


def dimensiona_drenagem(caso):
    """Drenagem superficial do lote. caso: {C, i_mm_h, area_ha, largura_canaleta_m,
    declividade, n_manning?}. Q pelo racional -> canaleta por Manning."""
    Q = vazao_racional(caso["C"], caso["i_mm_h"], caso["area_ha"])
    can = canaleta_manning(Q, caso["largura_canaleta_m"], caso["declividade"],
                           caso.get("n_manning", 0.015),
                           caso.get("altura_max_m", 1.0))
    return {"vazao_m3s": round(Q, 4), "canaleta": can,
            "metodo": "Racional Q=C.i.A/360 (DNIT) + Manning; C e IDF A CONFIRMAR"}


# ----------------------------------- selftest --------------------------------
def _selftest():
    # 1) corte/aterro: grade plana em cota 10, plataforma 8 -> so corte (2 m . area)
    grade = [[10.0, 10.0], [10.0, 10.0]]
    v = volumes_corte_aterro(grade, 8.0, 100.0)
    assert v["corte_m3"] == 2.0 * 100.0 * 4 and v["aterro_m3"] == 0.0
    # plataforma 12 -> so aterro
    v2 = volumes_corte_aterro(grade, 12.0, 100.0)
    assert v2["aterro_m3"] == 2.0 * 100.0 * 4 and v2["corte_m3"] == 0.0

    # 2) greide de equilibrio: terreno inclinado -> cota ~ media (empolamento 1)
    rampa = [[6.0, 8.0], [10.0, 12.0]]           # media 9
    g = greide_equilibrio(rampa, 100.0, empolamento=1.0)
    assert abs(g["cota_equilibrio"] - 9.0) < 0.1
    assert abs(g["corte_m3"] - g["aterro_m3"]) < 1.0    # equilibrado
    # empolamento > 1 -> precisa de MAIS corte -> plataforma mais baixa que a media
    g2 = greide_equilibrio(rampa, 100.0, empolamento=1.3)
    assert g2["cota_equilibrio"] < g["cota_equilibrio"]

    # 3) movimento de terra: saldo e acao
    m = movimento_terra(1000.0, 600.0, empolamento=1.0)
    assert m["saldo_m3"] == 400.0 and "bota-fora" in m["acao"]
    m2 = movimento_terra(500.0, 900.0)
    assert m2["saldo_m3"] == -400.0 and "emprestimo" in m2["acao"]

    # 4) racional: C=0,7 i=100 A=1 ha -> Q = 0,7.100.1/360 = 0,1944 m3/s
    Q = vazao_racional(0.7, 100.0, 1.0)
    assert abs(Q - 0.7 * 100 * 1 / 360.0) < 1e-9
    try:
        vazao_racional(1.5, 100, 1); assert False
    except ValueError:
        pass

    # 5) Manning: a lamina cresce com a vazao ; verifica a capacidade calculada
    c1 = canaleta_manning(0.2, 0.5, 0.01)
    c2 = canaleta_manning(0.5, 0.5, 0.01)
    assert c2["y_m"] > c1["y_m"] and c1["OK"]
    assert abs(c1["capacidade_m3s"] - 0.2) < 5e-3         # bate a vazao pedida
    # vazao absurda p/ a canaleta -> nao OK
    assert canaleta_manning(50.0, 0.3, 0.005, altura_max_m=0.5)["OK"] is False

    # 6) orquestrador de drenagem
    d = dimensiona_drenagem({"C": 0.7, "i_mm_h": 120.0, "area_ha": 0.8,
                             "largura_canaleta_m": 0.4, "declividade": 0.01})
    assert d["vazao_m3s"] > 0 and d["canaleta"]["y_m"] > 0
    return True


if __name__ == "__main__":
    _selftest()
    import json
    terreno = [[102.3, 101.8, 101.2], [101.5, 101.0, 100.4], [100.6, 100.1, 99.5]]
    g = greide_equilibrio(terreno, 400.0, empolamento=1.25)
    print("GREIDE DE EQUILIBRIO:", json.dumps(g, ensure_ascii=False))
    print("MOV. TERRA:", json.dumps(movimento_terra(g["corte_m3"], g["aterro_m3"], 1.25),
                                    ensure_ascii=False))
    print("DRENAGEM:", json.dumps(dimensiona_drenagem(
        {"C": 0.75, "i_mm_h": 130.0, "area_ha": 1.2, "largura_canaleta_m": 0.4,
         "declividade": 0.008}), ensure_ascii=False))
    print("selftest OK")
