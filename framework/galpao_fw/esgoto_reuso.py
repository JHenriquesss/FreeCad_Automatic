# ============================================================================
# esgoto_reuso.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Duas frentes de saneamento do lote quando NAO ha rede publica / para
# sustentabilidade:
#   (1) TRATAMENTO DE ESGOTO no proprio terreno - FOSSA SEPTICA (NBR 7229) + pos-
#       tratamento/sumidouro. Volume util da fossa pela formula da NBR 7229:
#         V = 1000 + N.(C.T + K.Lf)   [litros]
#       onde N=contribuintes, C=contribuicao de esgoto (L/pessoa.dia), T=periodo de
#       detencao (dias), K=taxa de acumulacao de lodo (dias), Lf=contribuicao de
#       lodo fresco (L/pessoa.dia). ATENCAO (AR300): C, T, K e Lf sao valores
#       TABELADOS da NBR 7229 (Tabelas 1/3/4) - este modulo NAO os inventa: sao
#       ENTRADA obrigatoria (o projetista le da norma vigente). Sumidouro/vala de
#       infiltracao dimensionado pela taxa de infiltracao do solo (ensaio).
#   (2) REUSO DE AGUA DE CHUVA - dimensiona a CISTERNA pelo METODO DE RIPPL (balanco
#       de massa, NBR 15527 Anexo): volume = maior deficit acumulado (demanda -
#       oferta) ao longo dos meses. Oferta = precipitacao . area de captacao .
#       coeficiente de escoamento (runoff). E' ALGORITMO (nao ha coeficiente de
#       norma escondido); o runoff (~0,8 telha metalica) e o consumo sao dados de
#       projeto. A precipitacao mensal e' DADO DE SITIO (A CONFIRMAR: estacao/INMET).
# STATELESS. Unidades: litros, m2, mm/mes, m3.
# ============================================================================
"""Saneamento do lote sem rede: fossa septica (formula NBR 7229, coeficientes de
ENTRADA) + reuso de agua de chuva (cisterna por Rippl / balanco de massa).
STATELESS. Precipitacao/coeficientes tabelados = A CONFIRMAR."""

from __future__ import annotations

RUNOFF_TELHA_METALICA = 0.80    # coef. de escoamento superficial tipico (A CONFIRMAR)
V_MIN_FOSSA_L = 1000.0          # volume util minimo da fossa septica (NBR 7229)


def volume_fossa_septica(N, C, T, K, Lf):
    """Volume util da fossa septica (NBR 7229): V = 1000 + N.(C.T + K.Lf) [L].
    TODOS os coeficientes sao ENTRADA (valores tabelados da NBR 7229 - Tabela 1 p/
    C e Lf por ocupacao; Tabela 3 p/ T pela contribuicao diaria; Tabela 4 p/ K pela
    temperatura e intervalo de limpeza). O modulo aplica a formula e o minimo de
    1000 L; nao inventa os coeficientes. Retorna dict."""
    for nome, val in (("N", N), ("C", C), ("T", T), ("K", K), ("Lf", Lf)):
        if val is None or val < 0:
            raise ValueError("[A CONFIRMAR NBR 7229] coeficiente %s ausente/invalido: %r"
                             % (nome, val))
    V = 1000.0 + N * (C * T + K * Lf)
    V = max(V, V_MIN_FOSSA_L)
    contrib_diaria = N * C
    return {"volume_util_L": round(V, 0), "volume_util_m3": round(V / 1000.0, 2),
            "contribuicao_diaria_L": round(contrib_diaria, 0),
            "N": N, "C": C, "T": T, "K": K, "Lf": Lf,
            "fonte": "NBR 7229 (V = 1000 + N(C.T + K.Lf)); coeficientes das Tab.1/3/4 "
                     "da norma (ENTRADA - A CONFIRMAR na norma vigente)"}


def area_sumidouro(contribuicao_diaria_L, taxa_infiltracao_L_m2_dia):
    """Area de infiltracao do sumidouro/vala: A = Q_diaria / taxa_infiltracao.
    A taxa de infiltracao vem do ENSAIO de infiltracao do solo (NBR 7229/13969) -
    ENTRADA (A CONFIRMAR). Retorna m2 (area lateral+fundo a prover)."""
    if not taxa_infiltracao_L_m2_dia or taxa_infiltracao_L_m2_dia <= 0:
        raise ValueError("[A CONFIRMAR] taxa de infiltracao do solo (ensaio) ausente")
    return round(contribuicao_diaria_L / taxa_infiltracao_L_m2_dia, 1)


def dimensiona_esgoto(caso):
    """Sistema de esgoto no lote. caso: {N, C, T, K, Lf, taxa_infiltracao_L_m2_dia?}.
    Devolve fossa + sumidouro (se a taxa for dada). Coeficientes NBR 7229 = ENTRADA."""
    f = volume_fossa_septica(caso["N"], caso["C"], caso["T"], caso["K"], caso["Lf"])
    out = {"fossa": f}
    taxa = caso.get("taxa_infiltracao_L_m2_dia")
    if taxa:
        out["sumidouro_area_m2"] = area_sumidouro(f["contribuicao_diaria_L"], taxa)
    else:
        out["sumidouro_nota"] = ("informar taxa de infiltracao (ensaio) p/ dimensionar "
                                 "o sumidouro/vala - A CONFIRMAR")
    return out


def oferta_chuva_mensal(precip_mm_mes, area_captacao_m2, runoff=RUNOFF_TELHA_METALICA):
    """Volume captado num mes (litros): V = precip(mm) . area(m2) . runoff.
    (1 mm sobre 1 m2 = 1 litro.)"""
    return [p * area_captacao_m2 * runoff for p in precip_mm_mes]


def cisterna_rippl(precip_mm_mes, area_captacao_m2, demanda_L_mes,
                   runoff=RUNOFF_TELHA_METALICA):
    """Dimensiona a cisterna de reuso pelo METODO DE RIPPL (balanco de massa, NBR
    15527). precip_mm_mes: 12 valores (mm/mes) do sitio [A CONFIRMAR]. demanda_L_mes:
    consumo mensal a atender (escalar ou 12 valores). Volume = maior deficit
    acumulado (sum de demanda-oferta enquanto positivo). Retorna dict."""
    if len(precip_mm_mes) != 12:
        raise ValueError("precip_mm_mes deve ter 12 valores (mm/mes)")
    if isinstance(demanda_L_mes, (int, float)):
        demanda = [float(demanda_L_mes)] * 12
    else:
        demanda = list(demanda_L_mes)
        if len(demanda) != 12:
            raise ValueError("demanda_L_mes escalar ou 12 valores")
    oferta = oferta_chuva_mensal(precip_mm_mes, area_captacao_m2, runoff)
    # Rippl: acumula (demanda - oferta); o maior acumulado positivo (roda 2 ciclos
    # p/ captar o ano hidrologico que cruza dez->jan) e' o volume necessario.
    acum = 0.0; vol_nec = 0.0
    total_ofer = total_dem = 0.0
    for ciclo in range(2):
        for m in range(12):
            if ciclo == 0:
                total_ofer += oferta[m]; total_dem += demanda[m]
            acum += demanda[m] - oferta[m]
            if acum < 0:
                acum = 0.0                          # reservatorio cheio, transborda
            vol_nec = max(vol_nec, acum)
    atendimento = min(1.0, total_ofer / total_dem) if total_dem else 0.0
    return {"volume_cisterna_L": round(vol_nec, 0),
            "volume_cisterna_m3": round(vol_nec / 1000.0, 2),
            "oferta_anual_L": round(total_ofer, 0),
            "demanda_anual_L": round(total_dem, 0),
            "atendimento_pct": round(100.0 * atendimento, 1),
            "runoff": runoff, "area_captacao_m2": area_captacao_m2,
            "metodo": "Rippl (balanco de massa) - NBR 15527; precipitacao do sitio "
                      "A CONFIRMAR (INMET/estacao)"}


# ----------------------------------- selftest --------------------------------
def _selftest():
    # 1) fossa NBR 7229 - formula exata + minimo 1000 L
    # exemplo: N=50, C=160, T=0,75, K=65, Lf=1  -> V=1000+50(160.0,75+65.1)=1000+50.185=10250
    f = volume_fossa_septica(50, 160.0, 0.75, 65.0, 1.0)
    assert abs(f["volume_util_L"] - (1000 + 50 * (160 * 0.75 + 65 * 1))) < 1e-6
    assert f["volume_util_L"] == 10250.0
    # minimo 1000 L p/ contribuicao minuscula
    assert volume_fossa_septica(1, 0.0, 0.0, 0.0, 0.0)["volume_util_L"] == 1000.0
    # coeficiente ausente -> A CONFIRMAR (nao inventa)
    try:
        volume_fossa_septica(10, None, 0.75, 65, 1); assert False
    except ValueError:
        pass

    # 2) sumidouro: A = Q/taxa
    a = area_sumidouro(8000.0, 40.0)
    assert abs(a - 200.0) < 1e-6
    try:
        area_sumidouro(8000.0, 0); assert False
    except ValueError:
        pass

    # 3) oferta de chuva: 100 mm sobre 800 m2 x 0,8 = 64000 L
    of = oferta_chuva_mensal([100.0], 800.0, 0.8)
    assert abs(of[0] - 64000.0) < 1e-6

    # 4) Rippl: chuva farta o ano todo -> cisterna pequena; seca -> maior
    chuva_regular = [120] * 12
    r1 = cisterna_rippl(chuva_regular, 800.0, 50000.0)
    chuva_sazonal = [200, 200, 200, 50, 10, 5, 5, 10, 30, 80, 150, 200]
    r2 = cisterna_rippl(chuva_sazonal, 800.0, 50000.0)
    assert r2["volume_cisterna_L"] >= r1["volume_cisterna_L"]
    assert 0.0 <= r1["atendimento_pct"] <= 100.0
    # demanda por lista de 12 tambem funciona
    r3 = cisterna_rippl(chuva_sazonal, 800.0, [40000] * 12)
    assert r3["volume_cisterna_L"] >= 0
    try:
        cisterna_rippl([100] * 11, 800.0, 50000.0); assert False
    except ValueError:
        pass

    # 5) orquestrador
    d = dimensiona_esgoto({"N": 50, "C": 160.0, "T": 0.75, "K": 65.0, "Lf": 1.0,
                           "taxa_infiltracao_L_m2_dia": 40.0})
    assert d["fossa"]["volume_util_L"] == 10250.0 and d["sumidouro_area_m2"] > 0
    return True


if __name__ == "__main__":
    _selftest()
    import json
    print(json.dumps(dimensiona_esgoto({"N": 50, "C": 160.0, "T": 0.75, "K": 65.0,
                                         "Lf": 1.0, "taxa_infiltracao_L_m2_dia": 40.0}),
                     indent=2, ensure_ascii=False))
    print(json.dumps(cisterna_rippl([190, 170, 150, 80, 40, 20, 15, 25, 60, 110, 150, 180],
                                    800.0, 45000.0), indent=2, ensure_ascii=False))
    print("selftest OK")
