# ============================================================================
# viga_continua.py - O QUE ESTE SCRIPT FAZ / CALCULA
# VIGA CONTINUA de varios tramos do pavimento-tipo (ABNT NBR 6118:2014, item
# 14.6.6.1). Ate aqui o framework so tinha viga de UM vao: `viga_concreto` usa
# coeficientes fixos (M = qL^2/8 simples, qL^2/10 continua), o que nao serve para
# um pavimento de edificio, onde os vaos sao desiguais e o momento negativo de
# apoio depende da relacao entre eles.
#
#   1) ANALISE: solver proprio de viga continua pelo metodo dos DESLOCAMENTOS
#      (slope-deflection / rigidez direta em rotacoes nodais), com EI por tramo,
#      carga uniforme e cargas concentradas. Modelo classico de 14.6.6.1: viga
#      simplesmente apoiada nos pilares.
#   2) CORRECOES OBRIGATORIAS de 14.6.6.1, que o modelo classico NAO da sozinho:
#      a) momento POSITIVO de cada tramo nao pode ser menor que o de engastamento
#         perfeito (w*L^2/24 para carga uniforme);
#      b) momento NEGATIVO em apoio intermediario solidario ao pilar, com largura
#         de apoio > h_pilar/4, nao pode ser menor em modulo que o de engastamento
#         perfeito (w*L^2/12);
#      c) nos apoios EXTREMOS, momento de engastamento parcial = momento de
#         engastamento perfeito x r_inf+r_sup / (r_vig+r_inf+r_sup), com r_i = I_i/l_i
#         e l_sup/2, l_inf/2 (Figura 14.8). Os momentos que sobram vao para os
#         tramos superior e inferior do PILAR - devolvidos aqui para o pilar usar.
#   3) ALTERNANCIA DE CARGAS (14.6.6.3): a dispensa vale so se a carga variavel for
#      <= 5 kN/m2 E <= 50% da carga total. Fora disso a envoltoria e montada com os
#      tramos carregados em xadrez. NAO ha saturacao silenciosa aqui: se a dispensa
#      nao valer e a alternancia estiver desligada, o resultado sai REPROVADO.
#
# ATENCAO a uma divergencia de fonte, resolvida a favor da norma: uma apostila
# didatica do acervo escreve os coeficientes de 14.6.6.1-c com fatores 3 e 4
# (3r/(4r_vig+3r_inf+3r_sup)), forma que vem de considerar a viga com a extremidade
# oposta rotulada. O TEXTO DA NBR 6118:2014 nao tem esses fatores. Implementado como
# esta na norma; a variante esta em coef_engastamento_parcial(variante='apostila')
# apenas para comparacao, nunca como default.
#
# Unidades: m, kN. Convencao de momento: SAGGING POSITIVO (tracao na face inferior),
# de modo que momento de apoio sai NEGATIVO. Saidas em portugues.
# ============================================================================
"""Viga continua de concreto armado (NBR 6118:2014 item 14.6.6): analise por
deslocamentos, correcoes obrigatorias de 14.6.6.1, engastamento parcial nos apoios
extremos e alternancia de cargas de 14.6.6.3."""

from __future__ import annotations

import math

# limites de 14.6.6.3 para DISPENSAR a alternancia de cargas
Q_MAX_DISPENSA_ALTERNANCIA = 5.0      # kN/m2
FRACAO_MAX_DISPENSA = 0.50            # q <= 50% da carga total


# ---------------------------------------------------------------------------
# Algebra: sistema linear pequeno (n+1 rotacoes nodais), eliminacao de Gauss
# ---------------------------------------------------------------------------
def _resolve(A, b):
    """Gauss com pivotamento parcial. A: lista de listas (n x n); b: lista (n)."""
    n = len(b)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-14:
            raise ValueError("sistema singular na analise da viga continua "
                             "(vao nulo ou rigidez nula?)")
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        for r in range(n):
            if r == c:
                continue
            f = M[r][c] / piv
            if f:
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


# ---------------------------------------------------------------------------
# Momentos de engastamento perfeito (FEM), convencao CLOCKWISE-POSITIVA
# ---------------------------------------------------------------------------
def _fem(L, w, cargas_p):
    """Momentos de engastamento perfeito do tramo: (FEM_ij no no esquerdo,
    FEM_ji no no direito), convencao horaria positiva.
    w: carga uniforme (kN/m); cargas_p: [(P, a)] com a medido do no esquerdo."""
    fem_i = -w * L ** 2 / 12.0
    fem_j = +w * L ** 2 / 12.0
    for P, a in cargas_p:
        b = L - a
        fem_i += -P * a * b ** 2 / L ** 2
        fem_j += +P * a ** 2 * b / L ** 2
    return fem_i, fem_j


def _momento_no_tramo(x, L, w, cargas_p, MA, MB):
    """Momento fletor (sagging positivo) na abscissa x do tramo, dados os momentos
    de extremidade MA e MB (tambem sagging positivo, portanto negativos em apoio)."""
    M = MA * (1.0 - x / L) + MB * (x / L) + w * x * (L - x) / 2.0
    for P, a in cargas_p:
        # viga biapoiada equivalente: reacao esquerda = P*(L-a)/L
        M += P * (L - a) / L * x if x <= a else P * a / L * (L - x)
    return M


def _cortante_no_tramo(x, L, w, cargas_p, MA, MB):
    """Cortante na abscissa x (derivada do momento)."""
    V = (MB - MA) / L + w * (L / 2.0 - x)
    for P, a in cargas_p:
        V += P * (L - a) / L if x < a else -P * a / L
    return V


# ---------------------------------------------------------------------------
# Solver de um caso de carga
# ---------------------------------------------------------------------------
def _analisa_caso(tramos, cargas_w, cargas_pontuais, n_pontos=41):
    """Resolve a viga continua para UM caso de carga.
    tramos: [{'L','EI'}]; cargas_w: [w por tramo]; cargas_pontuais: [[(P,a)]].
    Retorna {'M_apoios', 'M_x', 'V_x', 'reacoes', 'M_extremos'}."""
    n = len(tramos)
    nn = n + 1
    K = [[0.0] * nn for _ in range(nn)]
    F = [0.0] * nn
    fems = []
    for i, tr in enumerate(tramos):
        L, EI = tr["L"], tr["EI"]
        k = 2.0 * EI / L
        K[i][i] += 2.0 * k
        K[i][i + 1] += k
        K[i + 1][i + 1] += 2.0 * k
        K[i + 1][i] += k
        fi, fj = _fem(L, cargas_w[i], cargas_pontuais[i])
        fems.append((fi, fj))
        F[i] -= fi
        F[i + 1] -= fj
    theta = _resolve(K, F)

    # momentos de extremidade de cada tramo, convertidos para SAGGING POSITIVO:
    # MA = M_ij (horario) ; MB = -M_ji
    M_ext = []
    for i, tr in enumerate(tramos):
        L, EI = tr["L"], tr["EI"]
        k = 2.0 * EI / L
        m_ij = k * (2.0 * theta[i] + theta[i + 1]) + fems[i][0]
        m_ji = k * (2.0 * theta[i + 1] + theta[i]) + fems[i][1]
        M_ext.append((m_ij, -m_ji))

    M_x, V_x = [], []
    for i, tr in enumerate(tramos):
        L = tr["L"]
        MA, MB = M_ext[i]
        xs = [L * j / (n_pontos - 1) for j in range(n_pontos)]
        M_x.append([_momento_no_tramo(x, L, cargas_w[i], cargas_pontuais[i], MA, MB)
                    for x in xs])
        V_x.append([_cortante_no_tramo(x, L, cargas_w[i], cargas_pontuais[i], MA, MB)
                    for x in xs])

    # reacoes de apoio
    reacoes = [0.0] * nn
    for i, tr in enumerate(tramos):
        L = tr["L"]
        MA, MB = M_ext[i]
        reacoes[i] += _cortante_no_tramo(0.0, L, cargas_w[i], cargas_pontuais[i], MA, MB)
        reacoes[i + 1] -= _cortante_no_tramo(L, L, cargas_w[i], cargas_pontuais[i], MA, MB)

    # momento sobre cada apoio (sagging positivo -> negativo em apoio)
    M_apoios = [M_ext[0][0]]
    for i in range(1, n):
        M_apoios.append(0.5 * (M_ext[i - 1][1] + M_ext[i][0]))
    M_apoios.append(M_ext[-1][1])

    return {"M_apoios": M_apoios, "M_x": M_x, "V_x": V_x, "reacoes": reacoes,
            "M_extremos": M_ext, "theta": theta}


# ---------------------------------------------------------------------------
# 14.6.6.3 - alternancia de cargas
# ---------------------------------------------------------------------------
def dispensa_alternancia(q_variavel, carga_total):
    """14.6.6.3: a analise pode ser feita SEM alternancia de cargas se a carga
    variavel for <= 5 kN/m2 E <= 50% da carga total. As duas condicoes sao
    cumulativas ('e que seja no maximo igual a 50%').

    Devolve (dispensa: bool, motivo: str). Este e um requisito que NAO aparece como
    razao solicitante/resistente: uma viga de biblioteca ou de garagem passa em todos
    os gates de flexao e cortante e ainda assim esta subdimensionada se a alternancia
    for ignorada."""
    if carga_total <= 0:
        raise ValueError("carga total deve ser > 0")
    frac = q_variavel / carga_total
    if q_variavel > Q_MAX_DISPENSA_ALTERNANCIA + 1e-9:
        return False, ("carga variavel de %.2f kN/m2 > 5 kN/m2: a dispensa de "
                       "14.6.6.3 NAO se aplica; alternancia obrigatoria" % q_variavel)
    if frac > FRACAO_MAX_DISPENSA + 1e-9:
        return False, ("carga variavel e %.0f%% da carga total (> 50%%): a dispensa de "
                       "14.6.6.3 NAO se aplica; alternancia obrigatoria" % (100 * frac))
    return True, ("carga variavel %.2f kN/m2 <= 5 kN/m2 e %.0f%% <= 50%% da total: "
                  "dispensada a alternancia (14.6.6.3)" % (q_variavel, 100 * frac))


def _padroes_alternancia(n):
    """Padroes de tramos carregados com a carga VARIAVEL, para a envoltoria:
      - todos carregados;
      - xadrez par e xadrez impar (maximiza M+ nos tramos carregados);
      - para cada apoio interno, os dois tramos adjacentes carregados (maximiza M-).
    Devolve lista de tuplas de booleanos, uma por tramo."""
    pads = [tuple([True] * n)]
    if n >= 2:
        pads.append(tuple(i % 2 == 0 for i in range(n)))
        pads.append(tuple(i % 2 == 1 for i in range(n)))
        for k in range(1, n):
            pads.append(tuple(i in (k - 1, k) for i in range(n)))
    return list(dict.fromkeys(pads))


# ---------------------------------------------------------------------------
# 14.6.6.1-c - engastamento parcial nos apoios extremos
# ---------------------------------------------------------------------------
def coef_engastamento_parcial(r_vig, r_inf, r_sup, variante="norma"):
    """Coeficientes de reparticao do momento de engastamento perfeito no apoio
    EXTREMO (14.6.6.1-c). r_i = I_i / l_i, com l_sup/2 e l_inf/2 (Figura 14.8) e
    l_vig = o vao da viga.

    variante='norma' (default) usa o texto literal da NBR 6118:2014:
        viga = (r_inf + r_sup)/(r_vig + r_inf + r_sup)
        sup  =  r_sup /(r_vig + r_inf + r_sup)
        inf  =  r_inf /(r_vig + r_inf + r_sup)
    variante='apostila' reproduz a forma com fatores 3 e 4 que aparece em material
    didatico do acervo (viga com a extremidade oposta rotulada). NAO e o texto da
    norma - existe so para comparacao, e nunca deve ser o default.

    Nas duas variantes, viga + sup + inf = 1 (o momento se reparte integralmente)."""
    if min(r_vig, r_inf, r_sup) < 0:
        raise ValueError("rigidezes r_i devem ser >= 0")
    if variante == "norma":
        den = r_vig + r_inf + r_sup
        if den <= 0:
            raise ValueError("soma das rigidezes nula no no do apoio extremo")
        return {"viga": (r_inf + r_sup) / den, "sup": r_sup / den, "inf": r_inf / den,
                "fonte": "NBR 6118:2014, 14.6.6.1-c (texto literal)"}
    if variante == "apostila":
        den = 4.0 * r_vig + 3.0 * r_inf + 3.0 * r_sup
        if den <= 0:
            raise ValueError("soma das rigidezes nula no no do apoio extremo")
        return {"viga": (3.0 * r_inf + 3.0 * r_sup) / den, "sup": 3.0 * r_sup / den,
                "inf": 3.0 * r_inf / den,
                "fonte": "variante didatica com fatores 3/4 - NAO e o texto da norma"}
    raise ValueError("variante deve ser 'norma' ou 'apostila'")


def rigidez(I, l):
    """r_i = I_i / l_i (14.6.6.1-c). Para os tramos de pilar, l ja deve vir dividido
    por 2 conforme a Figura 14.8."""
    if l <= 0:
        raise ValueError("comprimento l deve ser > 0")
    return I / l


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------
def analisa(cfg):
    """Analisa uma viga continua e devolve a ENVOLTORIA de esforcos ja com as
    correcoes de 14.6.6.1.

    cfg: {
      'tramos': [{'L': vao (m), 'b','h': secao (m), 'EI': opcional (kN.m2)}],
      'g'     : carga permanente por tramo (kN/m) - escalar ou lista,
      'q'     : carga variavel por tramo (kN/m)  - escalar ou lista,
      'cargas_pontuais': opcional, [[(P, a)]] por tramo (kN, m do no esquerdo),
      'q_area_kN_m2'   : opcional, carga variavel por AREA do pavimento, usada so
                         para o teste de dispensa de 14.6.6.3,
      'g_area_kN_m2'   : idem para a permanente,
      'alternancia'    : 'auto' (default) | True | False,
      'apoios_extremos': opcional, dict por indice de apoio extremo (0 e n) com
                         {'r_vig','r_inf','r_sup'} para 14.6.6.1-c,
      'apoios_solidarios': opcional, dict por indice de apoio INTERNO com
                         {'largura_apoio': m, 'h_pilar': m} para 14.6.6.1-b,
      'fck': opcional (kN/m2), usado para estimar EI se nao vier explicito.
    }"""
    tramos_in = cfg["tramos"]
    n = len(tramos_in)
    if n < 1:
        raise ValueError("a viga precisa de pelo menos um tramo")

    def _por_tramo(v):
        if isinstance(v, (list, tuple)):
            if len(v) != n:
                raise ValueError("lista com %d valores para %d tramos" % (len(v), n))
            return [float(x) for x in v]
        return [float(v)] * n

    g = _por_tramo(cfg.get("g", 0.0))
    q = _por_tramo(cfg.get("q", 0.0))
    pontuais = cfg.get("cargas_pontuais") or [[] for _ in range(n)]
    fck = cfg.get("fck", 25e3)
    # Ecs estimado (8.2.8) so para a rigidez RELATIVA entre tramos; a analise linear
    # de viga continua so depende das relacoes EI/L, nao do valor absoluto.
    Ecs = 0.85 * 5600.0 * math.sqrt(fck / 1000.0) * 1000.0

    tramos = []
    for tr in tramos_in:
        if "EI" in tr:
            EI = tr["EI"]
        else:
            b, h = tr["b"], tr["h"]
            EI = Ecs * b * h ** 3 / 12.0
        tramos.append({"L": tr["L"], "EI": EI, "b": tr.get("b"), "h": tr.get("h")})

    # --- 14.6.6.3: precisa alternar? -------------------------------------
    q_area = cfg.get("q_area_kN_m2")
    g_area = cfg.get("g_area_kN_m2")
    if q_area is not None and g_area is not None:
        disp, motivo_alt = dispensa_alternancia(q_area, q_area + g_area)
    else:
        # sem as cargas por area, usa as lineares como proxy da FRACAO e nao aplica
        # o limite absoluto de 5 kN/m2 (que e por area) - declarado no aviso
        tot = sum(g) + sum(q)
        frac = (sum(q) / tot) if tot > 0 else 0.0
        disp = frac <= FRACAO_MAX_DISPENSA + 1e-9
        motivo_alt = ("sem 'q_area_kN_m2'/'g_area_kN_m2': o criterio de 14.6.6.3 foi "
                      "avaliado so pela fracao da carga LINEAR (%.0f%% da total); o "
                      "limite absoluto de 5 kN/m2 nao pode ser verificado" % (100 * frac))

    modo = cfg.get("alternancia", "auto")
    if modo == "auto":
        alternar = not disp
    else:
        alternar = bool(modo)

    reprovado_alt = (not disp) and (not alternar)

    # --- casos de carga ---------------------------------------------------
    casos = []
    if alternar and n >= 2:
        for pad in _padroes_alternancia(n):
            w = [g[i] + (q[i] if pad[i] else 0.0) for i in range(n)]
            casos.append((pad, _analisa_caso(tramos, w, pontuais)))
    else:
        w = [g[i] + q[i] for i in range(n)]
        casos.append((tuple([True] * n), _analisa_caso(tramos, w, pontuais)))

    # --- envoltoria -------------------------------------------------------
    n_pontos = len(casos[0][1]["M_x"][0])
    M_max = [[-1e18] * n_pontos for _ in range(n)]
    M_min = [[+1e18] * n_pontos for _ in range(n)]
    V_max = [0.0] * n
    for _pad, r in casos:
        for i in range(n):
            for j in range(n_pontos):
                M_max[i][j] = max(M_max[i][j], r["M_x"][i][j])
                M_min[i][j] = min(M_min[i][j], r["M_x"][i][j])
            V_max[i] = max(V_max[i], max(abs(v) for v in r["V_x"][i]))
    M_apoios = [min(r["M_apoios"][k] for _p, r in casos) for k in range(n + 1)]
    reacoes = [max(r["reacoes"][k] for _p, r in casos) for k in range(n + 1)]
    reacoes_min = [min(r["reacoes"][k] for _p, r in casos) for k in range(n + 1)]

    M_pos = [max(M_max[i]) for i in range(n)]
    avisos = []
    correcoes = []

    # --- 14.6.6.1-a: M+ >= engastamento perfeito --------------------------
    for i in range(n):
        w_tot = g[i] + q[i]
        M_eng_pos = w_tot * tramos[i]["L"] ** 2 / 24.0
        if M_pos[i] < M_eng_pos - 1e-9:
            correcoes.append(
                "tramo %d: M+ elevado de %.2f para %.2f kN.m (14.6.6.1-a: nao pode ser "
                "menor que o de engastamento perfeito, w*L^2/24)"
                % (i + 1, M_pos[i], M_eng_pos))
            M_pos[i] = M_eng_pos

    # --- 14.6.6.1-b: M- em apoio interno solidario ao pilar ---------------
    solidarios = cfg.get("apoios_solidarios") or {}
    for k_str, dados in solidarios.items():
        k = int(k_str)
        if k <= 0 or k >= n:
            raise ValueError("14.6.6.1-b vale para apoio INTERNO (1..%d); recebido %d"
                             % (n - 1, k))
        larg = dados["largura_apoio"]
        h_pil = dados["h_pilar"]
        if larg > h_pil / 4.0 + 1e-12:
            # Engastamento perfeito NESSE APOIO: cada tramo adjacente contribui com
            # w*L^2/12; adota-se o MAIOR dos dois (leitura conservadora). E um PISO
            # sobre o modulo, nao uma atribuicao: quando a analise elastica ja da um
            # momento maior em modulo (o caso usual de vaos iguais, que converge para
            # w*L^2/12), nada muda.
            cand = []
            for i in (k - 1, k):
                cand.append((g[i] + q[i]) * tramos[i]["L"] ** 2 / 12.0)
            M_eng_neg = -max(cand)
            if M_apoios[k] > M_eng_neg + 1e-9:
                correcoes.append(
                    "apoio %d: |M-| elevado de %.2f para %.2f kN.m (14.6.6.1-b: viga "
                    "solidaria ao pilar e largura de apoio %.2f m > h_pilar/4 = %.2f m, "
                    "logo |M-| >= engastamento perfeito w*L^2/12)"
                    % (k, M_apoios[k], M_eng_neg, larg, h_pil / 4.0))
                M_apoios[k] = M_eng_neg
        else:
            avisos.append("apoio %d: largura de apoio %.2f m <= h_pilar/4 = %.2f m -> a "
                          "correcao de 14.6.6.1-b nao se aplica"
                          % (k, larg, h_pil / 4.0))

    # --- 14.6.6.1-c: engastamento parcial nos apoios extremos -------------
    momentos_pilar = {}
    extremos = cfg.get("apoios_extremos") or {}
    for k_str, dados in extremos.items():
        k = int(k_str)
        if k not in (0, n):
            raise ValueError("14.6.6.1-c vale para os apoios EXTREMOS (0 e %d); "
                             "recebido %d" % (n, k))
        i = 0 if k == 0 else n - 1
        w_tot = g[i] + q[i]
        M_eng = w_tot * tramos[i]["L"] ** 2 / 12.0        # engastamento perfeito
        c = coef_engastamento_parcial(dados["r_vig"], dados["r_inf"], dados["r_sup"],
                                      dados.get("variante", "norma"))
        M_viga = -c["viga"] * M_eng                        # negativo (traciona em cima)
        momentos_pilar[k] = {"M_sup": c["sup"] * M_eng, "M_inf": c["inf"] * M_eng,
                             "coeficientes": c, "M_engastamento_perfeito": M_eng}
        if M_apoios[k] > M_viga + 1e-9:
            correcoes.append(
                "apoio extremo %d: M- de %.2f para %.2f kN.m (14.6.6.1-c: engastamento "
                "parcial, coef. viga = %.3f)" % (k, M_apoios[k], M_viga, c["viga"]))
            M_apoios[k] = M_viga

    ok = not reprovado_alt
    if reprovado_alt:
        avisos.append(
            "REPROVADO: a dispensa de alternancia de cargas de 14.6.6.3 nao se aplica "
            "(%s) e a alternancia foi desligada explicitamente. Os esforcos abaixo "
            "SUBESTIMAM a viga - nao use este resultado." % motivo_alt)

    return {
        "OK": ok,
        "n_tramos": n,
        "vaos": [tr["L"] for tr in tramos],
        "M_positivo": [round(v, 3) for v in M_pos],
        "M_apoios": [round(v, 3) for v in M_apoios],
        "V_max": [round(v, 3) for v in V_max],
        "reacoes": [round(v, 3) for v in reacoes],
        "reacoes_min": [round(v, 3) for v in reacoes_min],
        "M_envoltoria_max": M_max, "M_envoltoria_min": M_min,
        "alternancia_aplicada": bool(alternar and n >= 2),
        "alternancia_dispensada": bool(disp),
        "alternancia_motivo": motivo_alt,
        "n_casos_de_carga": len(casos),
        "correcoes_14661": correcoes,
        "momentos_no_pilar": momentos_pilar,
        "avisos": avisos,
    }


def relatorio(r):
    """Memoria de calculo da viga continua."""
    L = ["VIGA CONTINUA - ABNT NBR 6118:2014, item 14.6.6",
         "Tramos: %d ; vaos: %s m" % (r["n_tramos"],
                                      ", ".join("%.2f" % v for v in r["vaos"])),
         "",
         "%-8s %14s %14s %12s" % ("TRAMO", "M+ (kN.m)", "V max (kN)", "VAO (m)")]
    for i in range(r["n_tramos"]):
        L.append("%-8d %14.2f %14.2f %12.2f"
                 % (i + 1, r["M_positivo"][i], r["V_max"][i], r["vaos"][i]))
    L += ["", "%-8s %14s %14s" % ("APOIO", "M- (kN.m)", "REACAO (kN)")]
    for k in range(r["n_tramos"] + 1):
        L.append("%-8d %14.2f %14.2f" % (k, r["M_apoios"][k], r["reacoes"][k]))
    L += ["", "Alternancia de cargas (14.6.6.3): %s"
          % ("APLICADA (%d casos de carga)" % r["n_casos_de_carga"]
             if r["alternancia_aplicada"] else "nao aplicada"),
          "  %s" % r["alternancia_motivo"]]
    if r["correcoes_14661"]:
        L += ["", "Correcoes obrigatorias de 14.6.6.1:"]
        L += ["  - " + c for c in r["correcoes_14661"]]
    if r["momentos_no_pilar"]:
        L += ["", "Engastamento parcial nos apoios extremos (14.6.6.1-c) - momentos "
              "transmitidos ao pilar:"]
        for k, d in sorted(r["momentos_no_pilar"].items()):
            L.append("  apoio %d: M_sup = %.2f kN.m ; M_inf = %.2f kN.m "
                     "(M_engastamento perfeito = %.2f)"
                     % (k, d["M_sup"], d["M_inf"], d["M_engastamento_perfeito"]))
    if r["avisos"]:
        L += ["", "Avisos:"] + ["  ! " + a for a in r["avisos"]]
    L += ["", "RESULTADO: %s" % ("OK" if r["OK"] else "REPROVADO")]
    return "\n".join(L)
