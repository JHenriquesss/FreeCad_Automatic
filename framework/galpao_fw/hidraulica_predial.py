# ============================================================================
# hidraulica_predial.py - O QUE ESTE SCRIPT CALCULA
# DIMENSIONAMENTO HIDRAULICO PREDIAL (modulo de calculo stateless, CI), lido
# LITERALMENTE dos PDFs no NotebookLM (regra AR300 - nunca de memoria):
#
#   AGUA FRIA (ABNT NBR 5626:2020):
#     - vazao de projeto por aparelho = Tab.B.4 (vazoes unitarias; a 5626:2020
#       REMOVEU o metodo dos pesos Q=0,3*raiz(SP), entao NAO se usa a tabela de
#       pesos de 1998 - somam-se as vazoes de projeto, conservador, sem simultaneidade);
#     - diametro por velocidade: D = raiz(4Q/(pi*v)), v_max = 3 m/s (Sec.6.8.3 NOTA:
#       "limite maximo de velocidade media da agua de 3 m/s");
#     - pressoes (Sec.6.9): dinamica minima 10 kPa no ponto / 5 kPa em qq ponto;
#       estatica maxima 400 kPa.
#
#   ESGOTO SANITARIO (ABNT NBR 8160:1999) - Unidades Hunter de Contribuicao (UHC):
#     - Tab.3 UHC + DN minimo do ramal de descarga por aparelho;
#     - Tab.5 ramais de esgoto (DN -> UHC max); Tab.6 tubos de queda (<=3 / >3 pav);
#     - Tab.7 subcoletor/coletor predial (DN -> UHC max por declividade); coletor >= DN100;
#     - declividades minimas: 2% (DN<=75), 1% (DN>=100).
#
#   AGUAS PLUVIAIS (ABNT NBR 10844:1989):
#     - Sec.5.3.1 vazao de projeto Q = i*A/60 (Q L/min, i mm/h, A m2);
#     - Sec.5.2.1 area de contribuicao com incremento de inclinacao e paredes;
#     - Tab.4 capacidade de condutores (DN -> vazao por rugosidade n e declividade);
#     - Tab.5 chuvas intensas por cidade (intensidade i e' DADO DE SITIO -> [A CONFIRMAR]).
#     - condutor VERTICAL usa abaco (Fig.3, grafico, exige H da calha e L): nao ha
#       formula fechada na norma -> aqui o DN e' selecionado pela Tab.4 (tabulada).
#
# Cada tabela abaixo traz, no comentario, a clausula e o trecho literal citado.
# ============================================================================
"""Dimensionamento hidraulico predial: agua fria (NBR 5626:2020), esgoto (NBR 8160)
e aguas pluviais (NBR 10844). Modulo de calculo stateless (CI), aferido no _selftest."""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# AGUA FRIA - NBR 5626:2020
# ---------------------------------------------------------------------------
# Tab.B.4 (vazoes unitarias de projeto, L/s), reproduzida na NBR 8160 Anexo B
# "adaptado da NBR 5626". cited_text: "Bacia sanitaria Caixa de descarga 0,96 /
# Valvula de descarga 1,70 / Banheira Misturador 0,90 / Bide 0,40 / Chuveiro ou
# ducha 0,20 / Lavatorio 0,15 / Maquina de lavar roupas ou pratos 0,30 / Mictorio
# com sifao integrado 0,50 / Mictorio sem sifao 0,15 / Pia 0,25 / Tanque 0,25".
VAZAO_PROJETO_LS = {
    "bacia_caixa": 0.96, "bacia_valvula": 1.70, "banheira": 0.90, "bide": 0.40,
    "chuveiro": 0.20, "lavatorio": 0.15, "maquina_lavar": 0.30,
    "mictorio_sifao": 0.50, "mictorio": 0.15, "pia": 0.25, "tanque": 0.25,
}
V_MAX_AGUA_MS = 3.0          # NBR 5626:2020 Sec.6.8.3 NOTA (velocidade media max)
P_DIN_MIN_PONTO_KPA = 10.0   # Sec.6.9.2 (pressao dinamica minima no ponto)
P_DIN_MIN_REDE_KPA = 5.0     # Sec.6.9.4 (pressao dinamica minima em qq ponto)
P_EST_MAX_KPA = 400.0        # Sec.6.9.5 (pressao estatica maxima)
# serie comercial de DN de agua (mm) - PVC soldavel
DN_AGUA_MM = [20, 25, 32, 40, 50, 60, 75, 85, 110]


def vazao_agua(aparelhos, simultaneidade=1.0):
    """Vazao de projeto (L/s) de um conjunto de aparelhos de agua fria.
    aparelhos: dict {tipo: quantidade} (tipos em VAZAO_PROJETO_LS).
    A NBR 5626:2020 removeu o metodo dos pesos; por padrao soma-se a vazao de
    projeto de todos os aparelhos (simultaneidade=1,0, conservador). Um fator < 1
    so deve ser usado com criterio de projeto justificado."""
    if not aparelhos:
        raise ValueError("[A CONFIRMAR] informe os aparelhos de agua fria (dict tipo->qtd).")
    if not (0 < simultaneidade <= 1.0):
        raise ValueError("simultaneidade deve estar em (0, 1]; recebido %s." % simultaneidade)
    q = 0.0
    for tipo, n in aparelhos.items():
        if tipo not in VAZAO_PROJETO_LS:
            raise ValueError("aparelho de agua desconhecido: %r (validos: %s)."
                             % (tipo, sorted(VAZAO_PROJETO_LS)))
        if n < 0:
            raise ValueError("quantidade negativa para %r." % tipo)
        q += VAZAO_PROJETO_LS[tipo] * n
    return q * simultaneidade


def diametro_agua(aparelhos, v_max=V_MAX_AGUA_MS, simultaneidade=1.0):
    """Dimensiona o tubo de agua fria por velocidade (NBR 5626:2020 Sec.6.8.3).
    D_calc = raiz(4Q/(pi*v)); adota o proximo DN comercial >= D_calc.
    Retorna {Q_Ls, D_calc_mm, DN_mm, v_real_ms, v_max_ms, OK, pressoes...}."""
    if v_max <= 0:
        raise ValueError("v_max deve ser > 0; recebido %s." % v_max)
    q_ls = vazao_agua(aparelhos, simultaneidade)
    q_m3s = q_ls / 1000.0
    d_calc_m = math.sqrt(4.0 * q_m3s / (math.pi * v_max)) if q_m3s > 0 else 0.0
    d_calc_mm = d_calc_m * 1000.0
    dn = next((d for d in DN_AGUA_MM if d >= d_calc_mm), DN_AGUA_MM[-1])
    v_real = q_m3s / (math.pi * (dn / 1000.0) ** 2 / 4.0) if dn > 0 else 0.0
    return {
        "Q_Ls": round(q_ls, 3), "D_calc_mm": round(d_calc_mm, 1), "DN_mm": dn,
        "v_real_ms": round(v_real, 2), "v_max_ms": v_max,
        "p_din_min_ponto_kPa": P_DIN_MIN_PONTO_KPA, "p_est_max_kPa": P_EST_MAX_KPA,
        "OK": v_real <= v_max + 1e-9,
    }


# ---------------------------------------------------------------------------
# ESGOTO SANITARIO - NBR 8160:1999 (Unidades Hunter de Contribuicao)
# ---------------------------------------------------------------------------
# Tab.3 (UHC e DN minimo do ramal de descarga). cited_text: "Bacia sanitaria 6 100 /
# Banheira de residencia 2 40 / Bebedouro 0,5 40 / Bide 1 40 / Chuveiro residencia 2 40
# coletivo 4 40 / Lavatorio residencia 1 40 uso geral 2 40 / Mictorio valvula 6 75
# caixa 5 50 automatica 2 40 calha 2 50 / Pia cozinha residencial 3 50 industrial
# preparacao 3 50 lavagem de panelas 4 50 / Tanque de lavar roupas 3 40 / Maquina de
# lavar loucas 2 50 / Maquina de lavar roupas 3 50".
UHC_APARELHO = {   # tipo: (UHC, DN_min_ramal_descarga_mm)
    "bacia": (6, 100), "banheira": (2, 40), "bebedouro": (0.5, 40), "bide": (1, 40),
    "chuveiro": (2, 40), "chuveiro_coletivo": (4, 40),
    "lavatorio": (1, 40), "lavatorio_geral": (2, 40),
    "mictorio_valvula": (6, 75), "mictorio_caixa": (5, 50),
    "mictorio_automatico": (2, 40),
    "pia": (3, 50), "pia_industrial": (3, 50), "tanque": (3, 40),
    "maquina_loucas": (2, 50), "maquina_roupas": (3, 50),
}
# Tab.5 (ramais de esgoto: DN -> UHC max). cited_text: "40 3 / 50 6 / 75 20 / 100 160".
_TAB5_RAMAL = [(40, 3), (50, 6), (75, 20), (100, 160)]
# Tab.6 (tubos de queda: DN -> UHC max, [<=3 pav, >3 pav]). cited_text: "40 4 8 / 50 10 24
# / 75 30 70 / 100 240 500 / 150 960 1900 / 200 2200 3600 / 250 3800 5600 / 300 6000 8400".
_TAB6_QUEDA = [(40, 4, 8), (50, 10, 24), (75, 30, 70), (100, 240, 500),
               (150, 960, 1900), (200, 2200, 3600), (250, 3800, 5600), (300, 6000, 8400)]
# Tab.7 (subcoletor/coletor predial: DN -> UHC max por declividade 0,5/1/2/4 %).
# cited_text: "100 - 180 216 250 / 150 - 700 840 1000 / 200 1400 1600 1920 2300 /
# 250 2500 2900 3500 4200 / 300 3900 4600 5600 6700 / 400 7000 8300 10000 12000".
_DECLIV_COL = [0.5, 1.0, 2.0, 4.0]
_TAB7_COLETOR = {
    100: [None, 180, 216, 250], 150: [None, 700, 840, 1000],
    200: [1400, 1600, 1920, 2300], 250: [2500, 2900, 3500, 4200],
    300: [3900, 4600, 5600, 6700], 400: [7000, 8300, 10000, 12000],
}


def uhc_de_aparelhos(aparelhos):
    """Somatorio de UHC (NBR 8160 Tab.3) e o maior DN minimo de ramal de descarga exigido.
    aparelhos: dict {tipo: quantidade}. Retorna (uhc_total, dn_min_ramal_mm)."""
    if not aparelhos:
        raise ValueError("[A CONFIRMAR] informe os aparelhos de esgoto (dict tipo->qtd).")
    uhc = 0.0
    dn_min = 0
    for tipo, n in aparelhos.items():
        if tipo not in UHC_APARELHO:
            raise ValueError("aparelho de esgoto desconhecido: %r (validos: %s)."
                             % (tipo, sorted(UHC_APARELHO)))
        if n < 0:
            raise ValueError("quantidade negativa para %r." % tipo)
        u, dn = UHC_APARELHO[tipo]
        uhc += u * n
        if n > 0:
            dn_min = max(dn_min, dn)
    return uhc, dn_min


def _menor_dn(tabela_dn_cap, uhc):
    """Menor DN de uma lista [(DN, cap), ...] cuja capacidade >= uhc (ordenada)."""
    for dn, cap in tabela_dn_cap:
        if cap is not None and cap >= uhc:
            return dn
    return tabela_dn_cap[-1][0]   # satura no maior DN da tabela


def diametro_ramal_esgoto(uhc, dn_min_descarga=40):
    """DN do ramal de esgoto (NBR 8160 Tab.5), nunca menor que o DN minimo de
    descarga do aparelho mais exigente (Tab.3)."""
    if uhc < 0:
        raise ValueError("UHC nao pode ser negativo.")
    dn = _menor_dn(_TAB5_RAMAL, uhc)
    return max(dn, dn_min_descarga)


def diametro_tubo_queda(uhc, pavimentos=3):
    """DN do tubo de queda (NBR 8160 Tab.6). Coluna <=3 pav ou >3 pav."""
    if uhc < 0:
        raise ValueError("UHC nao pode ser negativo.")
    idx = 1 if pavimentos <= 3 else 2
    return _menor_dn([(row[0], row[idx]) for row in _TAB6_QUEDA], uhc)


def declividade_minima_pct(dn_mm):
    """Declividade minima de trecho horizontal de esgoto (NBR 8160 Sec.4.2.3.2):
    2 % p/ DN <= 75, 1 % p/ DN >= 100."""
    return 2.0 if dn_mm <= 75 else 1.0


def diametro_coletor(uhc, declividade_pct=1.0):
    """DN do subcoletor/coletor predial (NBR 8160 Tab.7) para a declividade dada
    (0,5/1/2/4 %). Coletor predial tem DN minimo 100 (Sec.5.1.4.1) e, por ser DN >= 100,
    exige declividade minima de 1 % (Sec.4.2.3.2)."""
    if uhc < 0:
        raise ValueError("UHC nao pode ser negativo.")
    # coletor predial e' sempre >= DN100 -> declividade minima obrigatoria 1 % (Sec.4.2.3.2)
    if declividade_pct < 1.0:
        raise ValueError("declividade %s%% < minima 1%% para coletor DN>=100 "
                         "(NBR 8160 Sec.4.2.3.2)." % declividade_pct)
    if declividade_pct not in _DECLIV_COL:
        # adota a declividade tabelada imediatamente inferior (mais conservadora)
        menores = [d for d in _DECLIV_COL if d <= declividade_pct]
        if not menores:
            raise ValueError("declividade %s%% abaixo do minimo tabelado (0,5%%)."
                             % declividade_pct)
        declividade_pct = max(menores)
    col = _DECLIV_COL.index(declividade_pct)
    tabela = [(dn, caps[col]) for dn, caps in sorted(_TAB7_COLETOR.items())]
    return max(_menor_dn(tabela, uhc), 100)   # coletor predial >= DN100


# ---------------------------------------------------------------------------
# AGUAS PLUVIAIS - NBR 10844:1989
# ---------------------------------------------------------------------------
# Tab.4 (capacidade de condutores, L/min) por rugosidade n e declividade %.
# cited_text: "50 32 45 64 90 ... / 75 95 133 188 267 / 100 204 287 405 575 /
# 125 370 521 735 1040 / 150 602 847 1190 1690 / 200 1300 1820 2570 3650 /
# 250 2350 3310 4660 6620 / 300 3820 5380 7590 10800" (colunas n=0,011: 0,5/1/2/4 %).
_DECLIV_PLUV = [0.5, 1.0, 2.0, 4.0]
_TAB4_CONDUTOR_N011 = {   # n = 0,011 ; DN -> [0,5%, 1%, 2%, 4%]  (L/min)
    50: [32, 45, 64, 90], 75: [95, 133, 188, 267], 100: [204, 287, 405, 575],
    125: [370, 521, 735, 1040], 150: [602, 847, 1190, 1690],
    200: [1300, 1820, 2570, 3650], 250: [2350, 3310, 4660, 6620],
    300: [3820, 5380, 7590, 10800],
}
I_PLUVIAL_PADRAO_MM_H = 150.0   # [A CONFIRMAR] intensidade de projeto (DADO DE SITIO;
#                                 NBR 10844 Tab.5 lista i por cidade/periodo de retorno).
DN_MIN_PLUVIAL_MM = 75          # NBR 10844 Sec.5.6.3: diametro INTERNO minimo 70 mm do
#                                 condutor vertical -> DN75 comercial (interno >= 70 mm).


def vazao_pluvial(area_m2, i_mm_h=I_PLUVIAL_PADRAO_MM_H):
    """Vazao de projeto pluvial (L/min) - NBR 10844 Sec.5.3.1: Q = i * A / 60.
    area_m2 = area de contribuicao (Sec.5.2.1: incluir incremento de inclinacao/paredes)."""
    if area_m2 <= 0:
        raise ValueError("area de contribuicao deve ser > 0; recebido %s." % area_m2)
    if i_mm_h <= 0:
        raise ValueError("intensidade pluviometrica deve ser > 0; recebido %s." % i_mm_h)
    return i_mm_h * area_m2 / 60.0


def area_contribuicao(largura_m, comprimento_m, altura_incl_m=0.0, parede_m2=0.0):
    """Area de contribuicao (m2) - NBR 10844 Sec.5.2.1. Para telhado inclinado, a
    projecao horizontal acrescida de metade da altura da inclinacao (a+h/2)*b, mais
    a contribuicao de paredes que interceptam a chuva."""
    if largura_m <= 0 or comprimento_m <= 0:
        raise ValueError("dimensoes do telhado devem ser > 0.")
    return (largura_m + altura_incl_m / 2.0) * comprimento_m + parede_m2


def diametro_pluvial(area_m2, i_mm_h=I_PLUVIAL_PADRAO_MM_H, declividade_pct=1.0):
    """Dimensiona o condutor pluvial (NBR 10844). Q = i*A/60 (Sec.5.3.1); adota o
    menor DN da Tab.4 (n=0,011) cuja capacidade >= Q na declividade dada.
    O condutor VERTICAL usa abaco (Fig.3) - aqui usa-se a Tab.4 (tabulada, capacidade
    de condutor) como criterio de selecao do DN."""
    q = vazao_pluvial(area_m2, i_mm_h)
    if declividade_pct not in _DECLIV_PLUV:
        menores = [d for d in _DECLIV_PLUV if d <= declividade_pct]
        if not menores:
            raise ValueError("declividade %s%% abaixo do minimo tabelado." % declividade_pct)
        declividade_pct = max(menores)
    col = _DECLIV_PLUV.index(declividade_pct)
    tabela = [(dn, caps[col]) for dn, caps in sorted(_TAB4_CONDUTOR_N011.items())]
    dn = max(_menor_dn(tabela, q), DN_MIN_PLUVIAL_MM)      # Sec.5.6.3: DN vertical >= 75
    return {"Q_Lmin": round(q, 1), "DN_mm": dn, "i_mm_h": i_mm_h,
            "declividade_pct": declividade_pct, "i_default": i_mm_h == I_PLUVIAL_PADRAO_MM_H}


def _selftest():
    import pytest
    # --- AGUA FRIA (NBR 5626:2020): banheiro simples ---
    # bacia c/ caixa 0,96 + lavatorio 0,15 + chuveiro 0,20 = 1,31 L/s
    a = diametro_agua({"bacia_caixa": 1, "lavatorio": 1, "chuveiro": 1})
    assert abs(a["Q_Ls"] - 1.31) < 1e-6, a
    # D_calc = raiz(4*0,00131/(pi*3)) = 23,6 mm -> DN25
    assert 23.0 < a["D_calc_mm"] < 24.0 and a["DN_mm"] == 25, a
    assert a["v_real_ms"] <= 3.0 and a["OK"], a
    # --- ESGOTO (NBR 8160): mesmo banheiro ---
    uhc, dn_desc = uhc_de_aparelhos({"bacia": 1, "lavatorio": 1, "chuveiro": 1})
    assert uhc == 6 + 1 + 2 and dn_desc == 100, (uhc, dn_desc)   # bacia forca DN100 na descarga
    assert diametro_ramal_esgoto(uhc, dn_desc) == 100            # Tab.5 DN75>=20>=9, mas descarga>=100
    assert diametro_tubo_queda(9, pavimentos=3) == 50           # Tab.6 <=3pav: DN50 cobre ate 10 UHC
    assert diametro_tubo_queda(300, pavimentos=3) == 150        # 300 UHC -> DN150 (240<300<=960)
    assert diametro_coletor(9, declividade_pct=1.0) == 100      # Tab.7 + minimo coletor DN100
    assert diametro_coletor(900, declividade_pct=2.0) == 200    # 840<900<=1920 -> DN200
    assert declividade_minima_pct(75) == 2.0 and declividade_minima_pct(100) == 1.0
    # --- PLUVIAL (NBR 10844): telhado 100 m2, i=150 mm/h ---
    q = vazao_pluvial(100.0, 150.0)
    assert abs(q - 250.0) < 1e-9, q                             # 150*100/60 = 250 L/min
    p = diametro_pluvial(100.0, 150.0, declividade_pct=1.0)
    assert p["Q_Lmin"] == 250.0 and p["DN_mm"] == 100, p        # Tab.4 1%: 287>=250 -> DN100
    assert p["i_default"] is True                               # i default -> flag de sitio
    # area pequena: Tab.4 daria DN50, mas o condutor vertical tem DN minimo 75 (Sec.5.6.3)
    assert diametro_pluvial(5.0, 150.0, declividade_pct=1.0)["DN_mm"] == 75
    # coletor com declividade < 1% (DN>=100) e' violacao (Sec.4.2.3.2)
    with pytest.raises(ValueError):
        diametro_coletor(180, declividade_pct=0.5)
    # area de contribuicao com inclinacao
    assert abs(area_contribuicao(10.0, 20.0, altura_incl_m=2.0) - (10 + 1) * 20) < 1e-9
    # guardas de entrada degenerada
    for bad in (lambda: vazao_pluvial(0, 150), lambda: diametro_agua({}),
                lambda: uhc_de_aparelhos({}), lambda: vazao_pluvial(100, 0)):
        with pytest.raises(ValueError):
            bad()
    print("hidraulica_predial self-test PASSED (NBR 5626:2020 / 8160 / 10844)")


if __name__ == "__main__":
    _selftest()
