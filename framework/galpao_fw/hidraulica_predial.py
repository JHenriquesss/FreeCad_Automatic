# ============================================================================
# hidraulica_predial.py - O QUE ESTE SCRIPT CALCULA
# DIMENSIONAMENTO HIDRAULICO PREDIAL (modulo de calculo stateless, CI), lido
# LITERALMENTE dos PDFs no NotebookLM (regra AR300 - nunca de memoria):
#
#   AGUA FRIA (ABNT NBR 5626:2020 + metodo dos pesos de 1998) - DOIS metodos de vazao,
#   ambos aceitos pela 2020 Sec.6.14.2 ("metodo reconhecido ou devidamente fundamentado,
#   seja ele empirico ou probabilistico"); o projetista escolhe e justifica:
#     - "soma": soma das vazoes de projeto Tab.B.4 (conservador, sem simultaneidade). A 2020
#       tirou a tabela de pesos do texto (migrou p/ norma de DESEMPENHO: vazao do fabricante
#       Q=K*raiz(P) Sec.6.9.2 + perda de carga pela eq. universal Sec.6.14.4);
#     - "pesos": pesos relativos da NBR 5626:1998 (Anexo A + Tab.A.1), Q=0,3*raiz(SP), com a
#       demanda simultanea provavel embutida (menor, economico).
#     Em ambos o diametro sai da velocidade <= 3 m/s (2020 Sec.6.8.3 NOTA); pressoes (Sec.6.9):
#     dinamica min 10 kPa no ponto / 5 kPa em qq ponto; estatica max 400 kPa.
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
# AUDITADO S41 (AR300, contra os PDFs no NLM): os valores estaveis conferem. NOTA de
# PROVENIENCIA sobre bacia_caixa=0,96: vem desta Tab.B.4 (8160, adaptada); a NBR
# 5626:1998 Tabela 1 da 0,15 L/s p/ caixa de descarga (abastecimento). Adotado o 0,96
# por ser MAIS CONSERVADOR (tubo maior) - decisao de projeto CONFIRMADA pelo usuario
# (S41); nao rebaixar sem novo criterio. (mictorio com/sem sifao troca entre edicoes.)
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

# --- DOIS METODOS DE VAZAO DE AGUA (ambos aceitos pela NBR 5626:2020 Sec.6.14.2:
#     "metodo reconhecido ou devidamente fundamentado, seja ele empirico ou probabilistico"):
#  - "soma": soma das vazoes de projeto (Tab.B.4), conservador, SEM simultaneidade;
#  - "pesos": metodo dos pesos relativos da NBR 5626:1998 (Anexo A + Tab.A.1) -> Q=0,3*raiz(SP),
#             com a demanda simultanea provavel embutida (menor, economico).
# Em ambos, o DIAMETRO sai da velocidade <= 3 m/s (2020 Sec.6.8.3).
C_PESOS = 0.3                # coeficiente da formula Q = C*raiz(SP) (NBR 5626:1998 Anexo A)
# Tab.A.1 (NBR 5626:1998): peso relativo P por aparelho/peca de utilizacao. cited_text:
# "Bacia sanitaria Caixa de descarga 0,15 0,3 / Valvula de descarga 1,70 32 / Banheira 0,30 1,0
# / Bebedouro 0,10 0,1 / Bide 0,10 0,1 / Chuveiro ou ducha 0,20 0,4 / Chuveiro eletrico 0,10 0,1
# / Lavadora de pratos ou de roupas 0,30 1,0 / Lavatorio 0,15 0,3 / Mictorio c/ sifao 0,15 0,3 /
# Mictorio s/ sifao (valvula) 0,50 2,8 / Mictorio calha 0,15/m 0,3 / Pia 0,25 0,7 / Pia
# torneira eletrica 0,10 0,1 / Tanque 0,25 0,7 / Torneira jardim/lavagem 0,20 0,4".
PESO_RELATIVO = {
    "bacia_caixa": 0.3, "bacia_valvula": 32.0, "banheira": 1.0, "bebedouro": 0.1,
    "bide": 0.1, "chuveiro": 0.4, "chuveiro_eletrico": 0.1, "maquina_lavar": 1.0,
    "lavatorio": 0.3, "mictorio_sifao": 0.3, "mictorio": 2.8, "mictorio_calha": 0.3,
    "pia": 0.7, "pia_eletrica": 0.1, "tanque": 0.7, "torneira_jardim": 0.4,
}
METODOS_AGUA = ("soma", "pesos")


def _valida_aparelhos(aparelhos, tabela, rotulo):
    """Valida o dict {tipo: qtd} contra a tabela do metodo (nao vazio, tipo conhecido,
    qtd >= 0). Levanta ValueError com mensagem clara."""
    if not aparelhos:
        raise ValueError("[A CONFIRMAR] informe os aparelhos de agua fria (dict tipo->qtd).")
    for tipo, n in aparelhos.items():
        if tipo not in tabela:
            raise ValueError("aparelho de agua desconhecido p/ %s: %r (validos: %s)."
                             % (rotulo, tipo, sorted(tabela)))
        if n < 0:
            raise ValueError("quantidade negativa para %r." % tipo)


def vazao_agua(aparelhos, simultaneidade=1.0):
    """Vazao de projeto (L/s) pela SOMA das vazoes de projeto (Tab.B.4), conservador
    (sem simultaneidade por padrao). aparelhos: dict {tipo: quantidade}. Um fator de
    simultaneidade < 1 so deve ser usado com criterio de projeto justificado."""
    if not (0 < simultaneidade <= 1.0):
        raise ValueError("simultaneidade deve estar em (0, 1]; recebido %s." % simultaneidade)
    _valida_aparelhos(aparelhos, VAZAO_PROJETO_LS, "metodo soma")
    q = sum(VAZAO_PROJETO_LS[tipo] * n for tipo, n in aparelhos.items())
    return q * simultaneidade


def soma_pesos(aparelhos):
    """Somatorio dos pesos relativos SP (NBR 5626:1998 Tab.A.1). aparelhos: {tipo: qtd}."""
    _valida_aparelhos(aparelhos, PESO_RELATIVO, "metodo pesos")
    return sum(PESO_RELATIVO[tipo] * n for tipo, n in aparelhos.items())


def vazao_agua_pesos(aparelhos):
    """Vazao ESTIMADA (demanda simultanea provavel, L/s) pelo METODO DOS PESOS
    RELATIVOS (NBR 5626:1998 Anexo A): Q = 0,3 * raiz(SP)."""
    return C_PESOS * math.sqrt(soma_pesos(aparelhos))


def diametro_agua(aparelhos, v_max=V_MAX_AGUA_MS, simultaneidade=1.0, metodo="soma"):
    """Dimensiona o tubo de agua fria por velocidade (NBR 5626:2020 Sec.6.8.3):
    D_calc = raiz(4Q/(pi*v)); adota o proximo DN comercial >= D_calc. A VAZAO Q vem
    do metodo escolhido (ambos aceitos pela 2020 Sec.6.14.2):
      - metodo="soma"  : soma das vazoes de projeto (Tab.B.4), conservador (default);
      - metodo="pesos" : metodo dos pesos NBR 5626:1998 (Q=0,3*raiz(SP), simultaneo).
    Retorna {metodo, Q_Ls, [soma_P], D_calc_mm, DN_mm, v_real_ms, v_max_ms, OK, pressoes}."""
    if v_max <= 0:
        raise ValueError("v_max deve ser > 0; recebido %s." % v_max)
    if metodo not in METODOS_AGUA:
        raise ValueError("metodo de agua invalido: %r (validos: %s)." % (metodo, METODOS_AGUA))
    extra = {}
    if metodo == "pesos":
        sp = soma_pesos(aparelhos)
        q_ls = C_PESOS * math.sqrt(sp)
        extra["soma_P"] = round(sp, 2)
    else:
        q_ls = vazao_agua(aparelhos, simultaneidade)
    q_m3s = q_ls / 1000.0
    d_calc_m = math.sqrt(4.0 * q_m3s / (math.pi * v_max)) if q_m3s > 0 else 0.0
    d_calc_mm = d_calc_m * 1000.0
    dn = next((d for d in DN_AGUA_MM if d >= d_calc_mm), DN_AGUA_MM[-1])
    v_real = q_m3s / (math.pi * (dn / 1000.0) ** 2 / 4.0) if dn > 0 else 0.0
    return {
        "metodo": metodo, "Q_Ls": round(q_ls, 3), "D_calc_mm": round(d_calc_mm, 1),
        "DN_mm": dn, "v_real_ms": round(v_real, 2), "v_max_ms": v_max,
        "p_din_min_ponto_kPa": P_DIN_MIN_PONTO_KPA, "p_est_max_kPa": P_EST_MAX_KPA,
        "OK": v_real <= v_max + 1e-9, **extra,
    }


def verifica_agua_quente_seguranca(config, vazao_calculada_Ls,
                                   pressao_dinamica_ponto_kPa):
    """Verifica o contrato explícito de segurança da água quente.

    A NBR 5626:2020 exige que as condições da rede quente, temperaturas,
    pressões, dilatação/perdas térmicas e dispositivos de segurança sejam
    declarados no projeto. Ausência de dado é ``inconclusivo``; uma condição
    declarada e incompatível é uma violação efetiva. A função não cria valores
    default de projeto.
    """
    faltantes = []
    violacoes = []
    cfg = config if isinstance(config, dict) else {}
    if config is not None and not isinstance(config, dict):
        faltantes.append("hidraulica.agua_quente_seguranca deve ser um dicionario")

    def _numero(chave, descricao, minimo=None):
        if chave not in cfg or cfg[chave] is None:
            faltantes.append(chave)
            return None
        valor = cfg[chave]
        if (isinstance(valor, bool) or not isinstance(valor, (int, float))
                or not math.isfinite(valor)):
            violacoes.append("%s deve ser numerico" % descricao)
            return None
        if minimo is not None and valor < minimo:
            violacoes.append("%s deve ser >= %s" % (descricao, minimo))
            return None
        return float(valor)

    def _booleano(chave, descricao):
        if chave not in cfg or cfg[chave] is None:
            faltantes.append(chave)
            return None
        valor = cfg[chave]
        if not isinstance(valor, bool):
            violacoes.append("%s deve ser booleano" % descricao)
            return None
        return valor

    q_normal = _numero("vazao_normal_Ls", "vazao normal", 0.0)
    q_maxima = _numero("vazao_maxima_Ls", "vazao maxima", 0.0)
    p_estatica = _numero("pressao_estatica_kPa", "pressao estatica", 0.0)
    temperatura = _numero("temperatura_max_C", "temperatura maxima", 0.0)
    q_calculada = vazao_calculada_Ls
    if q_calculada is None:
        faltantes.append("vazao_calculada_Ls")
    elif (isinstance(q_calculada, bool) or not isinstance(q_calculada, (int, float))
          or not math.isfinite(q_calculada) or q_calculada < 0.0):
        violacoes.append("vazao calculada deve ser numerica e nao negativa")
        q_calculada = None
    p_dinamica = pressao_dinamica_ponto_kPa
    if p_dinamica is None:
        faltantes.append("pressao_dinamica_ponto_kPa")
    elif (isinstance(p_dinamica, bool) or not isinstance(p_dinamica, (int, float))
          or not math.isfinite(p_dinamica)):
        violacoes.append("pressao dinamica no ponto deve ser numerica")
        p_dinamica = None

    compatibilidade = _booleano(
        "pressao_fria_quente_compativel", "compatibilidade entre pressoes fria e quente")
    misturadores = _booleano("misturadores_sanitarios", "misturadores sanitarios")
    uso_corporal = _booleano("uso_corporal", "uso corporal")
    limitador_45 = _booleano(
        "limitador_automatico_45C", "limitador automatico de 45 C")
    superf_protegidas = _booleano("superficies_protegidas", "protecao das superficies")
    reducao_perdas = _booleano(
        "reducao_perdas_termicas", "reducao de perdas termicas")
    perdas_estimadas = _booleano(
        "perdas_termicas_estimadas", "estimativa de perdas termicas")
    dilatacao = _booleano("dilatacao_considerada", "dilatacao")
    movimentacoes = _booleano("movimentacoes_absorvidas", "absorção de movimentacoes")
    acumulacao = _booleano("aquecedor_acumulacao", "aquecedor de acumulacao")

    if q_normal is not None and q_maxima is not None and q_maxima < q_normal:
        violacoes.append("vazao maxima deve ser >= vazao normal")
    if q_calculada is not None and q_maxima is not None and q_calculada > q_maxima + 1e-12:
        violacoes.append("vazao calculada excede a vazao maxima declarada")
    if p_estatica is not None and p_estatica > P_EST_MAX_KPA + 1e-12:
        violacoes.append("pressao estatica excede 400 kPa")
    if p_dinamica is not None and p_dinamica < P_DIN_MIN_PONTO_KPA - 1e-12:
        violacoes.append("pressao dinamica no ponto abaixo do minimo de 10 kPa")
    if compatibilidade is False:
        violacoes.append("pressao fria e quente declaradas como incompativeis")
    if (misturadores is True and temperatura is not None
            and temperatura > 70.0 + 1e-12):
        violacoes.append("temperatura maxima excede 70 C em ambiente com misturadores")
    if (uso_corporal is True and temperatura is not None and temperatura > 45.0 + 1e-12
            and limitador_45 is False):
        violacoes.append("uso corporal acima de 45 C exige limitador automatico")
    if superf_protegidas is False:
        violacoes.append("superficies expostas da rede quente nao estao protegidas")
    if reducao_perdas is False or perdas_estimadas is False:
        violacoes.append("perdas termicas nao foram reduzidas e estimadas")
    if dilatacao is False or movimentacoes is False:
        violacoes.append("dilatacao e movimentacoes da rede nao foram consideradas")

    if acumulacao is True:
        for chave, descricao in (
                ("limitador_automatico_temperatura",
                 "limitador automatico de temperatura"),
                ("valvula_seguranca_temperatura",
                 "valvula de seguranca de temperatura"),
                ("limitador_automatico_pressao",
                 "limitador automatico de pressao")):
            valor = _booleano(chave, descricao)
            if valor is False:
                violacoes.append("aquecedor de acumulacao exige %s" % descricao)

    return {
        "OK": not faltantes and not violacoes,
        "inconclusivo": bool(faltantes) and not violacoes,
        "faltantes": faltantes,
        "violacoes": violacoes,
        "vazao_calculada_Ls": q_calculada,
        "pressao_dinamica_ponto_kPa": p_dinamica,
    }


# ---------------------------------------------------------------------------
# AGUA FRIA - VERIFICACAO DE PRESSAO / PERDA DE CARGA (NBR 5626:1998 Anexo A.2)
# ---------------------------------------------------------------------------
# Fair-Whipple-Hsiao (A.2.1): perda de carga unitaria J (kPa/m). cited_text:
# "Para tubos rugosos (aco-carbono, galvanizado): J = 20,2 x 106 x Q^1,88 x d^-4,88 /
#  Para tubos lisos (plastico, cobre): J = 8,69 x 106 x Q^1,75 x d^-4,75 / J perda de
#  carga unitaria kPa/m; Q vazao L/s; d diametro interno mm".
_FWH = {"liso": (8.69e6, 1.75, -4.75), "rugoso": (20.2e6, 1.88, -4.88)}
# Tab.A.3: comprimento equivalente (m) de conexoes p/ tubo LISO, por DN. cited_text:
# "Cotovelo 90 45 / Curva 90 45 / Te passagem direta lateral: 15 1,1 0,4 0,4 0,2 0,7 2,3 /
#  20 1,2 0,5 0,5 0,3 0,8 2,4 / 25 1,5 0,7 0,6 0,4 0,9 3,1 / 32 2,0 1,0 0,7 0,5 1,5 4,6 /
#  40 3,2 1,0 1,2 0,6 2,2 7,3 / 50 3,4 1,3 1,3 0,7 2,3 7,6 / 65 3,7 1,7 1,4 0,8 2,4 7,8 /
#  80 3,9 1,8 1,5 0,9 2,5 8,0 / 100 4,3 1,9 1,6 1,0 2,6 8,3 / 125 4,9 2,4 1,9 1,1 3,3 10,0 /
#  150 5,4 2,6 2,1 1,2 3,8 11,1". Colunas: cotovelo_90/cotovelo_45/curva_90/curva_45/te_direta/te_lateral.
_CONEXOES = ("cotovelo_90", "cotovelo_45", "curva_90", "curva_45", "te_direta", "te_lateral")
COMPRIMENTO_EQUIV_M = {
    15: (1.1, 0.4, 0.4, 0.2, 0.7, 2.3), 20: (1.2, 0.5, 0.5, 0.3, 0.8, 2.4),
    25: (1.5, 0.7, 0.6, 0.4, 0.9, 3.1), 32: (2.0, 1.0, 0.7, 0.5, 1.5, 4.6),
    40: (3.2, 1.0, 1.2, 0.6, 2.2, 7.3), 50: (3.4, 1.3, 1.3, 0.7, 2.3, 7.6),
    65: (3.7, 1.7, 1.4, 0.8, 2.4, 7.8), 80: (3.9, 1.8, 1.5, 0.9, 2.5, 8.0),
    100: (4.3, 1.9, 1.6, 1.0, 2.6, 8.3), 125: (4.9, 2.4, 1.9, 1.1, 3.3, 10.0),
    150: (5.4, 2.6, 2.1, 1.2, 3.8, 11.1),
}
# Pressao dinamica minima no ponto (NBR 5626:1998 Sec.5.3.5.1): 10 kPa geral; 5 kPa na
# caixa de descarga; 15 kPa na valvula de descarga p/ bacia sanitaria.
P_MIN_PONTO_KPA = {"geral": 10.0, "caixa_descarga": 5.0, "valvula_descarga": 15.0}
PESO_ESPEC_AGUA_KPA_M = 10.0    # peso especifico da agua (10 kN/m3 = 10 kPa/m) - A.4.2


def perda_carga_unitaria(Q_ls, d_mm, material="liso"):
    """Perda de carga unitaria J (kPa/m) por Fair-Whipple-Hsiao (NBR 5626:1998 A.2.1).
    material: 'liso' (plastico/cobre) ou 'rugoso' (aco). Q em L/s, d interno em mm."""
    if material not in _FWH:
        raise ValueError("material invalido: %r (validos: %s)." % (material, tuple(_FWH)))
    if Q_ls < 0 or d_mm <= 0:
        raise ValueError("Q >= 0 e d > 0; recebido Q=%s d=%s." % (Q_ls, d_mm))
    k, eq, ed = _FWH[material]
    return k * (Q_ls ** eq) * (d_mm ** ed) if Q_ls > 0 else 0.0


def _dn_equiv(dn_mm):
    """DN tabelado (Tab.A.3) mais proximo do dn dado (a serie comercial de agua tem
    DN 60/85/110 que nao constam na tabela -> usa o tabelado mais proximo)."""
    return min(COMPRIMENTO_EQUIV_M, key=lambda d: abs(d - dn_mm))


def comprimento_equivalente(dn_mm, conexoes):
    """Somatorio dos comprimentos equivalentes (m) das conexoes (NBR 5626:1998 Tab.A.3).
    conexoes: dict {tipo: quantidade} (tipos em _CONEXOES). Registros de passagem plena
    tem perda desprezivel (A.2.3) e nao entram na tabela."""
    tab = COMPRIMENTO_EQUIV_M[_dn_equiv(dn_mm)]
    leq = 0.0
    for tipo, n in (conexoes or {}).items():
        if tipo not in _CONEXOES:
            raise ValueError("conexao desconhecida: %r (validas: %s)." % (tipo, _CONEXOES))
        if n < 0:
            raise ValueError("quantidade negativa para %r." % tipo)
        leq += tab[_CONEXOES.index(tipo)] * n
    return leq


def verifica_pressao(Q_ls, d_mm, L_real_m, p_entrada_kPa, conexoes=None, dcota_m=0.0,
                     material="liso", tipo_ponto="geral", perda_singular_kPa=0.0):
    """Verifica a pressao no ponto de utilizacao (NBR 5626:1998 Anexo A.2/A.4 + Sec.5.3.5.1).
    p_disponivel = p_entrada + dcota*10 (dcota>0 = ponto ABAIXO da entrada -> ganho);
    p_residual = p_disponivel - J*(L_real+Leq) - perdas singulares. OK se p_residual >=
    minimo do ponto (10 geral / 5 caixa / 15 valvula). Retorna o balanco completo."""
    if tipo_ponto not in P_MIN_PONTO_KPA:
        raise ValueError("tipo_ponto invalido: %r (validos: %s)."
                         % (tipo_ponto, tuple(P_MIN_PONTO_KPA)))
    if L_real_m < 0:
        raise ValueError("comprimento real deve ser >= 0.")
    J = perda_carga_unitaria(Q_ls, d_mm, material)
    leq = comprimento_equivalente(d_mm, conexoes)
    perda = J * (L_real_m + leq) + perda_singular_kPa
    p_disp = p_entrada_kPa + dcota_m * PESO_ESPEC_AGUA_KPA_M
    p_res = p_disp - perda
    p_min = P_MIN_PONTO_KPA[tipo_ponto]
    return {"J_kPa_m": round(J, 4), "Leq_m": round(leq, 2),
            "L_total_m": round(L_real_m + leq, 2), "perda_kPa": round(perda, 2),
            "p_disponivel_kPa": round(p_disp, 2), "p_residual_kPa": round(p_res, 2),
            "p_min_kPa": p_min, "tipo_ponto": tipo_ponto, "OK": p_res >= p_min - 1e-9}


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
    return _menor_dn_sat(tabela_dn_cap, uhc)[0]


def _menor_dn_sat(tabela_dn_cap, q):
    """(dn, saturado): menor DN cuja capacidade >= q; se NENHUM atende, satura no maior
    DN da tabela e marca saturado=True (a vazao excede a maior secao tabelada -> a peca
    NAO comporta o fluxo, precisa de mais pontos/declividade). Nunca silencioso."""
    for dn, cap in tabela_dn_cap:
        if cap is not None and cap >= q:
            return dn, False
    return tabela_dn_cap[-1][0], True


def diametro_ramal_esgoto_sat(uhc, dn_min_descarga=40):
    """{DN_mm, saturado} do ramal de esgoto (NBR 8160 Tab.5), nunca menor que o
    DN minimo de descarga do aparelho mais exigente (Tab.3).

    saturado=True quando a UHC excede a maior linha da Tab.5 (160 UHC em DN100):
    a tabela nao cobre o trecho, que precisa ser subdividido. A flag NUNCA e'
    descartada (saturacao silenciosa)."""
    if uhc < 0:
        raise ValueError("UHC nao pode ser negativo.")
    dn, saturado = _menor_dn_sat(_TAB5_RAMAL, uhc)
    return {"DN_mm": max(dn, dn_min_descarga), "saturado": saturado,
            "uhc": uhc, "tabela": "NBR 8160 Tab.5"}


def diametro_ramal_esgoto(uhc, dn_min_descarga=40):
    """DN do ramal de esgoto (NBR 8160 Tab.5), nunca menor que o DN minimo de
    descarga do aparelho mais exigente (Tab.3). Use ``diametro_ramal_esgoto_sat``
    quando precisar saber se a tabela saturou."""
    return diametro_ramal_esgoto_sat(uhc, dn_min_descarga)["DN_mm"]


def diametro_tubo_queda_sat(uhc, pavimentos=3):
    """{DN_mm, saturado} do tubo de queda (NBR 8160 Tab.6). Coluna <=3 pav ou
    >3 pav. saturado=True quando a UHC excede a maior linha da coluna."""
    if uhc < 0:
        raise ValueError("UHC nao pode ser negativo.")
    idx = 1 if pavimentos <= 3 else 2
    dn, saturado = _menor_dn_sat([(row[0], row[idx]) for row in _TAB6_QUEDA], uhc)
    return {"DN_mm": dn, "saturado": saturado, "uhc": uhc,
            "tabela": "NBR 8160 Tab.6"}


def diametro_tubo_queda(uhc, pavimentos=3):
    """DN do tubo de queda (NBR 8160 Tab.6). Coluna <=3 pav ou >3 pav.
    Use ``diametro_tubo_queda_sat`` para saber se a tabela saturou."""
    return diametro_tubo_queda_sat(uhc, pavimentos)["DN_mm"]


def declividade_minima_pct(dn_mm):
    """Declividade minima de trecho horizontal de esgoto (NBR 8160 Sec.4.2.3.2):
    2 % p/ DN <= 75, 1 % p/ DN >= 100."""
    return 2.0 if dn_mm <= 75 else 1.0


def diametro_coletor_sat(uhc, declividade_pct=1.0):
    """{DN_mm, saturado} do subcoletor/coletor predial (NBR 8160 Tab.7) p/ a declividade
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
    dn, saturado = _menor_dn_sat(tabela, uhc)
    return {"DN_mm": max(dn, 100),          # coletor predial >= DN100
            "saturado": saturado, "uhc": uhc, "declividade_pct": declividade_pct,
            "tabela": "NBR 8160 Tab.7"}


def diametro_coletor(uhc, declividade_pct=1.0):
    """DN do subcoletor/coletor predial (NBR 8160 Tab.7). Use
    ``diametro_coletor_sat`` para saber se a tabela saturou."""
    return diametro_coletor_sat(uhc, declividade_pct)["DN_mm"]


# --- VENTILACAO do esgoto (NBR 8160 Sec.5.2.2) ---
# Tab.8 (ramal de ventilacao por UHC): (limite_UHC, DN). cited_text: "sem bacias: Ate 12 40
# / 13 a 18 50 / 19 a 36 75 ; com bacias: Ate 17 50 / 18 a 60 75".
_TAB8_VENT_SEM = [(12, 40), (18, 50), (36, 75)]
_TAB8_VENT_COM = [(17, 50), (60, 75)]
# Tab.D.1 (ramal/coluna de ventilacao pelo DN do ramal de descarga/esgoto). cited_text:
# "DN 40 -> 40 / DN 50 -> 40 / DN 75 -> 50 / DN 100 -> 50".
_TABD1_VENT = {40: 40, 50: 40, 75: 50, 100: 50}


def diametro_ramal_ventilacao_sat(uhc, com_bacia=True):
    """{DN_mm, saturado} do ramal de ventilacao (NBR 8160 Tab.8) por UHC ventilada.

    com_bacia=True usa a coluna 'com bacias sanitarias'. A Tab.8 termina em DN75
    (60 UHC com bacias, 36 sem): acima disso a norma NAO cobre o ramal e a peca
    precisa ser subdividida -> saturado=True. Antes esta saturacao era silenciosa
    (o DN75 saia igual para 60 e para 600 UHC)."""
    if uhc < 0:
        raise ValueError("UHC nao pode ser negativo.")
    tab = _TAB8_VENT_COM if com_bacia else _TAB8_VENT_SEM
    for lim, dn in tab:
        if uhc <= lim:
            return {"DN_mm": dn, "saturado": False, "uhc": uhc,
                    "limite_uhc": lim, "tabela": "NBR 8160 Tab.8"}
    return {"DN_mm": tab[-1][1], "saturado": True, "uhc": uhc,
            "limite_uhc": tab[-1][0], "tabela": "NBR 8160 Tab.8"}


def diametro_ramal_ventilacao(uhc, com_bacia=True):
    """DN do ramal de ventilacao (NBR 8160 Tab.8) por UHC ventilada. Use
    ``diametro_ramal_ventilacao_sat`` para saber se a tabela saturou."""
    return diametro_ramal_ventilacao_sat(uhc, com_bacia)["DN_mm"]


def diametro_coluna_ventilacao(dn_esgoto_mm):
    """DN da coluna/ramal de ventilacao pelo DN do ramal de esgoto (NBR 8160 Tab.D.1).
    Alternativa simples ao metodo por UHC+comprimento (Tab.2)."""
    dn = min(_TABD1_VENT, key=lambda d: abs(d - dn_esgoto_mm))   # DN tabelado mais proximo
    return _TABD1_VENT[dn]


# --- CALHAS pluviais (NBR 10844 Tab.3, semicirculares n=0,011) ---
# Tab.3 (capacidade de calhas semicirculares, L/min) por DN e declividade 0,5/1/2 %.
# cited_text: "100 130 183 256 / 125 236 333 466 / 150 384 541 757".
_DECLIV_CALHA = [0.5, 1.0, 2.0]
_TAB3_CALHA_N011 = {100: [130, 183, 256], 125: [236, 333, 466], 150: [384, 541, 757]}


def diametro_calha(area_m2, i_mm_h=None, declividade_pct=0.5):
    """DN da calha semicircular (NBR 10844 Tab.3). Q = i*A/60 (Sec.5.3.1); adota a menor
    calha cuja capacidade >= Q na declividade dada (0,5/1/2 %). declividade minima de
    calha/condutor horizontal = 0,5 % (Sec.5.7.1)."""
    i = I_PLUVIAL_PADRAO_MM_H if i_mm_h is None else i_mm_h
    q = vazao_pluvial(area_m2, i)
    if declividade_pct not in _DECLIV_CALHA:
        menores = [d for d in _DECLIV_CALHA if d <= declividade_pct]
        if not menores:
            raise ValueError("declividade de calha %s%% < minima 0,5%% (Sec.5.7.1)."
                             % declividade_pct)
        declividade_pct = max(menores)
    col = _DECLIV_CALHA.index(declividade_pct)
    tabela = [(dn, caps[col]) for dn, caps in sorted(_TAB3_CALHA_N011.items())]
    dn, sat = _menor_dn_sat(tabela, q)
    return {"Q_Lmin": round(q, 1), "DN_mm": dn, "declividade_pct": declividade_pct,
            "i_mm_h": i, "i_default": i == I_PLUVIAL_PADRAO_MM_H, "saturado": sat}


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
    dn0, sat = _menor_dn_sat(tabela, q)
    dn = max(dn0, DN_MIN_PLUVIAL_MM)                       # Sec.5.6.3: DN vertical >= 75
    return {"Q_Lmin": round(q, 1), "DN_mm": dn, "i_mm_h": i_mm_h, "saturado": sat,
            "declividade_pct": declividade_pct, "i_default": i_mm_h == I_PLUVIAL_PADRAO_MM_H}


def _selftest():
    import pytest
    # --- AGUA FRIA metodo "soma" (NBR 5626:2020): banheiro simples ---
    # bacia c/ caixa 0,96 + lavatorio 0,15 + chuveiro 0,20 = 1,31 L/s
    banheiro = {"bacia_caixa": 1, "lavatorio": 1, "chuveiro": 1}
    a = diametro_agua(banheiro)
    assert a["metodo"] == "soma" and abs(a["Q_Ls"] - 1.31) < 1e-6, a
    # D_calc = raiz(4*0,00131/(pi*3)) = 23,6 mm -> DN25
    assert 23.0 < a["D_calc_mm"] < 24.0 and a["DN_mm"] == 25, a
    # --- AGUA FRIA metodo "pesos" (NBR 5626:1998 Anexo A): mesmo banheiro ---
    # P: bacia caixa 0,3 + lavatorio 0,3 + chuveiro 0,4 = SP=1,0 -> Q=0,3*raiz(1)=0,30 L/s
    assert abs(soma_pesos(banheiro) - 1.0) < 1e-9
    ap = diametro_agua(banheiro, metodo="pesos")
    assert ap["metodo"] == "pesos" and ap["soma_P"] == 1.0
    assert abs(ap["Q_Ls"] - 0.30) < 1e-6, ap        # simultaneo << soma (1,31)
    assert ap["Q_Ls"] < a["Q_Ls"] and ap["DN_mm"] <= a["DN_mm"]
    assert abs(vazao_agua_pesos(banheiro) - 0.30) < 1e-6
    # bacia com VALVULA de descarga domina (P=32): SP=32 -> Q=0,3*raiz(32)=1,70 L/s
    assert abs(vazao_agua_pesos({"bacia_valvula": 1}) - 1.697) < 1e-3
    with pytest.raises(ValueError):
        diametro_agua(banheiro, metodo="xyz")
    # --- VERIFICACAO DE PRESSAO (NBR 5626:1998 Anexo A.2, Fair-Whipple-Hsiao) ---
    # J = 8,69e6 * Q^1,75 * d^-4,75. Q=0,30 L/s, d=25 mm -> J ~ 0,24 kPa/m
    J = perda_carga_unitaria(0.30, 25.0, "liso")
    assert abs(J - 0.241) < 0.01, J
    assert perda_carga_unitaria(0.30, 25.0, "rugoso") > J     # aco perde mais que plastico
    # Leq (Tab.A.3, DN25): 2 cotovelos 90 (1,5) + 1 te direta (0,9) = 3,9 m
    assert abs(comprimento_equivalente(25.0, {"cotovelo_90": 2, "te_direta": 1}) - 3.9) < 1e-6
    # trecho: L=20 m, Leq=3,9 -> perda=0,241*23,9=5,76 kPa; p_ent=100, ponto 3 m ABAIXO
    # (ganho +30) -> disp=130; residual=124,2 kPa >= 10 -> OK
    vp = verifica_pressao(0.30, 25.0, 20.0, 100.0,
                          conexoes={"cotovelo_90": 2, "te_direta": 1},
                          dcota_m=3.0, tipo_ponto="geral")
    assert abs(vp["Leq_m"] - 3.9) < 1e-6 and abs(vp["perda_kPa"] - 5.76) < 0.05, vp
    assert abs(vp["p_disponivel_kPa"] - 130.0) < 1e-6 and vp["OK"], vp
    # pressao insuficiente -> reprova; valvula de descarga exige >= 15 kPa
    ruim = verifica_pressao(0.30, 25.0, 5.0, 12.0, tipo_ponto="valvula_descarga")
    assert ruim["p_min_kPa"] == 15.0 and not ruim["OK"]
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
    # --- VENTILACAO (NBR 8160 Tab.8 / Tab.D.1) ---
    assert diametro_ramal_ventilacao(9, com_bacia=True) == 50    # com bacia, ate 17 UHC -> DN50
    assert diametro_ramal_ventilacao(9, com_bacia=False) == 40   # sem bacia, ate 12 UHC -> DN40
    assert diametro_ramal_ventilacao(40, com_bacia=True) == 75   # 18 a 60 -> DN75
    assert diametro_coluna_ventilacao(100) == 50                 # Tab.D.1: esgoto DN100 -> vent DN50
    # --- PLUVIAL (NBR 10844): telhado 100 m2, i=150 mm/h ---
    q = vazao_pluvial(100.0, 150.0)
    assert abs(q - 250.0) < 1e-9, q                             # 150*100/60 = 250 L/min
    p = diametro_pluvial(100.0, 150.0, declividade_pct=1.0)
    assert p["Q_Lmin"] == 250.0 and p["DN_mm"] == 100, p        # Tab.4 1%: 287>=250 -> DN100
    assert p["i_default"] is True                               # i default -> flag de sitio
    # area pequena: Tab.4 daria DN50, mas o condutor vertical tem DN minimo 75 (Sec.5.6.3)
    assert diametro_pluvial(5.0, 150.0, declividade_pct=1.0)["DN_mm"] == 75
    # CALHA (Tab.3): area 100 m2, i=150 -> Q=250 L/min. 0,5%: DN150 (384>=250); 1%: DN125 (333>=250)
    assert diametro_calha(100.0, 150.0, declividade_pct=0.5)["DN_mm"] == 150
    assert diametro_calha(100.0, 150.0, declividade_pct=1.0)["DN_mm"] == 125
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
