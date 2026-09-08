# ============================================================================
# telhado_casa_madeira.py - TESOURA DE MADEIRA DA CASA (G66)
#
# A casa tinha laje, viga, pilar, fundacao e agora parede portante - e nao
# tinha telhado: estrutura_casa.escopo()["telhado_madeira"] = "not_available".
# Este modulo e' a estrutura que apoia a telha: tesoura triangulada Howe
# (banzos, diagonais, montantes) + tercas, dimensionada pela NBR 7190-1
# (madeira_nbr7190), com a carga DESCENDO de verdade - a reacao da tesoura
# realimenta a descida (o remedio da escada do G42/G38: carga que nao
# realimenta e' saturacao silenciosa entre modulos).
#
# CARGA (reuso, nao invencao): o peso da telha e' o contrato do galpao -
# cobertura.telha_peso com o tipo amarrado ao perfil (gate 7), via
# telha_cobertura.catalogo_por_tipo. Aqui peso E tipo sao declarados; sem
# peso a carga e' indefinida e a entrada e' RECUSADA (regra do SPT do G9).
# Vento/succao/uplift fora do lote (cadeia gravitacional, como a casa).
#
# GEOMETRIA: vao entre apoios + inclinacao -> cumeeira h = (vao/2).tan.
# n_paineis por agua; nos e barras da trelica Howe simetrica; terca em
# cada no do banzo superior. O apoio e' o que a casa ja tem: 'parede' no
# caminho portante (carga linear nas linhas do beiral) ou 'viga' no de
# concreto (carga nos pilares do topo).
#
# Unidades: m, kN. STATELESS, puro (so math).
# CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# ============================================================================
"""Tesoura Howe de madeira + tercas (NBR 7190-1): geometria do vao e da
inclinacao, esforcos por equilibrio nos nos, verificacao barra a barra,
ligacoes em chapa de aco (7.3) e reacoes para a descida."""

from __future__ import annotations

import math

import madeira_nbr7190 as mad

GF = 1.4  # ELU gravitacional (mesma convencao dos modulos de concreto)
# 9.2.1: banzo de trelica e' "barra longitudinal" = peca principal
# isolada; diagonal, montante e terca sao secundarias.
PAPEL_921 = {"banzo": "principal_isolada", "secundaria": "secundaria_isolada"}
TOL_FECHAMENTO = 0.02  # mesma tolerancia do baldrame/alvenaria
G_M_S2 = 9.81


class EntradaTelhado(ValueError):
    """A entrada declarada nao descreve um telhado que caiba neste lote."""


def _num(cfg, chave, minimo=None, texto=None):
    try:
        v = float(cfg[chave])
    except (KeyError, TypeError, ValueError):
        raise EntradaTelhado(
            "%s deve ser declarado numerico%s" % (
                chave, (": " + texto) if texto else "")) from None
    if minimo is not None and not v > minimo:
        raise EntradaTelhado("%s deve ser > %s (recebido %s)"
                             % (chave, minimo, v))
    return v


# --- geometria ----------------------------------------------------------------
def geometria(vao, inclinacao_graus, n_paineis):
    """Nos e barras da Howe simetrica. Devolve nos {id: (x, y)}, barras
    [(n1, n2, grupo)] e a altura da cumeeira."""
    L = float(vao)
    if not L > 0:
        raise EntradaTelhado("vao deve ser > 0")
    t = float(inclinacao_graus)
    if not 0 < t < 60:
        raise EntradaTelhado("inclinacao_graus deve estar em (0, 60)")
    n = int(n_paineis)
    if n < 1:
        raise EntradaTelhado("n_paineis deve ser >= 1")
    a = L / 2.0
    h = a * math.tan(math.radians(t))
    nos = {}
    # banzo inferior: 2n+1 nos (beirais + cumeeira-baixa).
    for i in range(2 * n + 1):
        nos["B%d" % i] = (-a + i * (L / (2 * n)), 0.0)
    # banzo superior: n-1 interiores por agua + cumeeira.
    for i in range(1, n):
        x = -a + i * (a / n)
        nos["TL%d" % i] = (x, (x + a) * math.tan(math.radians(t)))
    for i in range(1, n):
        x = a - i * (a / n)
        nos["TR%d" % i] = (x, (a - x) * math.tan(math.radians(t)))
    nos["C"] = (0.0, h)
    beiral_L, beiral_R = "B0", "B%d" % (2 * n)
    nos[beiral_L] = (-a, 0.0)
    nos[beiral_R] = (a, 0.0)
    barras = []
    # banzo inferior.
    for i in range(2 * n):
        barras.append(("B%d" % i, "B%d" % (i + 1), "banzo_inf"))
    # banzo superior esquerdo + direito.
    seq_L = [beiral_L] + ["TL%d" % i for i in range(1, n)] + ["C"]
    seq_R = ["C"] + ["TR%d" % i for i in range(1, n)] + [beiral_R]
    for s1, s2 in zip(seq_L, seq_L[1:]):
        barras.append((s1, s2, "banzo_sup"))
    for s1, s2 in zip(seq_R, seq_R[1:]):
        barras.append((s1, s2, "banzo_sup"))
    # montantes: cada no inferior interior tem vertical ate o superior.
    # mapa x -> no superior (beiral/cumeeira/interiores).
    sup = {}
    for nid, (x, y) in nos.items():
        if y > 1e-9:
            sup[round(x, 9)] = nid
    sup[round(-a, 9)] = beiral_L
    sup[round(a, 9)] = beiral_R
    for i in range(1, 2 * n):
        x = -a + i * (L / (2 * n))
        nid_sup = sup.get(round(x, 9))
        if nid_sup is not None and nid_sup != "B%d" % i:
            barras.append(("B%d" % i, nid_sup, "montante"))
    # diagonais Howe: do no superior ao inferior vizinho em direcao ao
    # centro (trabalham comprimidas sob gravidade). A cumeeira nao tem
    # diagonal (o montante central ja a pendura).
    for i in range(1, n):
        barras.append(("TL%d" % i, "B%d" % (i + 1), "diagonal"))
    for j in range(1, n):
        barras.append(("TR%d" % j, "B%d" % (2 * n - j - 1), "diagonal"))
    # remove duplicadas (cumeeira/beiral podem coincidir em n = 1).
    unicas = []
    vistos = set()
    for n1, n2, g in barras:
        chave = (min(n1, n2), max(n1, n2), g)
        if chave not in vistos and n1 != n2:
            vistos.add(chave)
            unicas.append((n1, n2, g))
    return {"nos": nos, "barras": unicas, "h_cumeeira": h,
            "meio_vao": a, "n_paineis": n}


def _resolve_sistema(A, b):
    """Eliminacao de Gauss com pivoteamento parcial (puro, sem numpy)."""
    n = len(b)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            raise EntradaTelhado("tesoura hipostatica: equilibrio sem "
                                 "solucao unica (geometria invalida)")
        M[col], M[piv] = M[piv], M[col]
        for r in range(col + 1, n):
            f = M[r][col] / M[col][col]
            for c in range(col, n + 1):
                M[r][c] -= f * M[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / M[i][i]
    return x


def analisa_trelica(nos, barras, cargas, apoio_L, apoio_R):
    """Equilibrio no a no: barras (tracao +) + reacoes (apoio_L pino,
    apoio_R rolete). `cargas`: {no: (Fx, Fy)} em kN. Devolve {barra:
    Nk, reacoes}."""
    ids = list(nos)
    idx = {nid: k for k, nid in enumerate(ids)}
    nb = len(barras)
    # incognitas: nb barras + RxL, RyL, RyR.
    n = 2 * len(ids)
    if nb + 3 != n:
        raise EntradaTelhado("trelica fora do padrao 2j-3 (j=%d, b=%d)"
                             % (len(ids), nb))
    A = [[0.0] * n for _ in range(n)]
    b = [0.0] * n
    for nid, (fx, fy) in cargas.items():
        k = idx[nid]
        b[2 * k] = -fx
        b[2 * k + 1] = -fy
    for j, (n1, n2, _g) in enumerate(barras):
        x1, y1 = nos[n1]
        x2, y2 = nos[n2]
        comp = math.hypot(x2 - x1, y2 - y1)
        cx, cy = (x2 - x1) / comp, (y2 - y1) / comp
        A[2 * idx[n1]][j] = cx
        A[2 * idx[n1] + 1][j] = cy
        A[2 * idx[n2]][j] = -cx
        A[2 * idx[n2] + 1][j] = -cy
    A[2 * idx[apoio_L]][nb] = 1.0
    A[2 * idx[apoio_L] + 1][nb + 1] = 1.0
    A[2 * idx[apoio_R] + 1][nb + 2] = 1.0
    x = _resolve_sistema(A, b)
    esforcos = {(n1, n2, g): x[j] for j, (n1, n2, g) in enumerate(barras)}
    return {"esforcos_Nk": esforcos, "RxL": x[nb], "RyL": x[nb + 1],
            "RyR": x[nb + 2]}


def _valida(spec):
    for chave in ("telha", "sobrecarga_kNm2", "madeira", "secoes", "apoio",
                  "ligacao", "travamento_borda_comprimida_m",
                  "contraventamento_banzo_inf", "apoio_comprimento_m"):
        if spec.get(chave) is None:
            raise EntradaTelhado("%s deve ser declarado" % chave)
    if spec.get("travado_borda_comprimida") is not None:
        raise EntradaTelhado(
            "travado_borda_comprimida saiu do contrato: a 6.5.6 dispensa "
            "pelo NUMERO (L1 entre travamentos da borda comprimida) e nao "
            "por declaracao 'sim'; use travamento_borda_comprimida_m")
    if not float(spec["travamento_borda_comprimida_m"]) >= 0:
        raise EntradaTelhado("travamento_borda_comprimida_m deve ser >= 0")
    telha = spec["telha"]
    if telha.get("tipo") is None or telha.get("peso") is None:
        raise EntradaTelhado("telha precisa de 'tipo' e 'peso' (kN/m2 de "
                             "telhado): sem peso a carga e' indefinida")
    if not float(telha["peso"]) > 0:
        raise EntradaTelhado("telha.peso deve ser > 0")
    mad_spec = spec["madeira"]
    for chave in ("classe", "carregamento", "umidade", "categoria"):
        if mad_spec.get(chave) is None:
            raise EntradaTelhado("madeira.%s deve ser declarado (sem "
                                 "default)" % chave)
    for grupo in ("banzo_sup", "banzo_inf", "diagonal", "montante",
                  "terca"):
        sec = (spec["secoes"] or {}).get(grupo)
        if not isinstance(sec, dict) or not sec.get("b") or not sec.get("h"):
            raise EntradaTelhado("secoes.%s precisa de b/h (m)" % grupo)
    if spec["apoio"] not in ("parede", "viga"):
        raise EntradaTelhado("apoio deve ser 'parede' (caminho portante) "
                             "ou 'viga' (caminho de concreto)")
    lig = spec["ligacao"]
    for chave in ("tipo_pino", "d_mm", "fu_MPa", "n_pinos", "config_73",
                  "espacamentos", "he_mm", "t_chapa_mm"):
        if lig.get(chave) is None:
            raise EntradaTelhado("ligacao.%s deve ser declarado: sem no "
                                 "verificado a tesoura e' um desenho" % chave)
    h_sup = float((spec["secoes"] or {}).get("banzo_sup", {}).get("h", 0))
    if not 0 < float(lig["he_mm"]) / 1000.0 < h_sup:
        raise EntradaTelhado(
            "ligacao.he_mm deve estar em (0, h_banzo_sup): detalhe "
            "inconsistente com a secao (he=%.0f mm, h=%.0f mm)"
            % (float(lig["he_mm"]), h_sup * 1000.0))


def comprimentos(geo):
    """Comprimento de cada barra (m)."""
    nos = geo["nos"]
    comp = {}
    for n1, n2, g in geo["barras"]:
        x1, y1 = nos[n1]
        x2, y2 = nos[n2]
        comp[(n1, n2, g)] = math.hypot(x2 - x1, y2 - y1)
    return comp


def confere_fechamento_area(G_lancado_kN, Q_lancado_kN, g_total_kN_m2,
                            sobrecarga_kN_m2, vao_m, espacamento_m,
                            cos_inclinacao, tol=TOL_FECHAMENTO):
    """Carga lancada nos nos x O TELHADO QUE ELA COBRE (G66, pos-revisao).

    O gate irmao (fechamento_carga: reacao x lancado) fecha por
    CONSTRUCAO - a reacao sai do equilibrio da mesma carga -, logo nao
    enxerga tributario errado: e' a assercao tautologica do D86. Este
    tem origem independente, a area de telhado da faixa da tesoura, e
    foi ele que pegou o no de beiral levando painel INTEIRO (a tesoura
    carregava N/(N-1) telhados: +25 % com 4 paineis, com o quantitativo
    comprando um telhado so).

    As duas areas sao diferentes de proposito: telha e peso proprio
    cobrem o plano INCLINADO; a sobrecarga de manutencao e' projetada na
    horizontal."""
    area_incl = 2.0 * (float(vao_m) / 2.0 / float(cos_inclinacao))         * float(espacamento_m)
    area_proj = float(vao_m) * float(espacamento_m)
    G_esp = float(g_total_kN_m2) * area_incl
    Q_esp = float(sobrecarga_kN_m2) * area_proj
    e_G = abs(float(G_lancado_kN) - G_esp) / G_esp if G_esp > 0 else 0.0
    e_Q = abs(float(Q_lancado_kN) - Q_esp) / Q_esp if Q_esp > 0 else 0.0
    erro = max(e_G, e_Q)
    return {"ok": bool(erro <= tol),
            "area_inclinada_m2": round(area_incl, 3),
            "area_projetada_m2": round(area_proj, 3),
            "G_esperado_kN": round(G_esp, 3),
            "Q_esperado_kN": round(Q_esp, 3),
            "G_lancado_kN": round(float(G_lancado_kN), 3),
            "Q_lancado_kN": round(float(Q_lancado_kN), 3),
            "erro_rel": round(erro, 5)}


def rodar(spec):
    """Dimensiona a tesoura + tercas e devolve verificacao, reacoes e
    quantitativos. `spec` conforme _valida()."""
    _valida(spec)
    vao = _num(spec, "vao", 0, "entre apoios")
    inc = _num(spec, "inclinacao_graus", 0, "do telhado")
    ext = _num(spec, "extensao", 0, "comprimento do telhado")
    esp = _num(spec, "espacamento", 0, "entre tesouras")
    n_pain = int(spec.get("n_paineis", 2))
    sobre_q = _num(spec, "sobrecarga_kNm2", 0, "manutencao (projetada)")
    comp_apoio = _num(spec, "apoio_comprimento_m", 0, "apoio da tesoura")

    prop = mad.propriedades_classe(spec["madeira"]["classe"])
    km = mad.kmod(spec["madeira"]["carregamento"],
                  spec["madeira"]["umidade"],
                  spec["madeira"].get("categoria", "serrada"))
    res = mad.resistencias_calculo(prop, km["kmod"])
    conifera = prop["conifera"]

    import telha_cobertura as _tlh
    perfil = _tlh.catalogo_por_tipo(spec["telha"]["tipo"],
                                   peso_override=float(
                                       spec["telha"]["peso"]))
    g_telha = float(perfil["peso"])  # kN/m2 de telhado inclinado

    geo = geometria(vao, inc, n_pain)
    nos, barras = geo["nos"], geo["barras"]
    comp = comprimentos(geo)
    cos_t = math.cos(math.radians(inc))

    # nos do banzo superior (recebem telha): beirais + interiores + cumeeira.
    sup_ids = sorted({n1 for n1, _n2, g in barras if g == "banzo_sup"} |
                     {n2 for _n1, n2, g in barras if g == "banzo_sup"},
                     key=lambda nid: nos[nid][0])
    # tributario inclinado por no (metade do painel vizinho).
    # O no interior pega meio painel de cada lado; o de BEIRAL so tem
    # painel de um lado. Espelhar o vizinho (2.x0 - x1) dava painel
    # inteiro tambem na ponta e a tesoura passava a carregar (N/(N-1))
    # telhados - 25 % a mais com 4 paineis. Sem beiral declarado, a
    # borda termina no apoio.
    trib = {}
    xs = [nos[nid][0] for nid in sup_ids]
    for k, nid in enumerate(sup_ids):
        x0 = xs[k - 1] if k > 0 else xs[0]
        x1 = xs[k + 1] if k < len(xs) - 1 else xs[-1]
        trib[nid] = (x1 - x0) / 2.0 / cos_t  # m inclinados por tesoura

    rho = prop["rhom"]  # kg/m3 (medio, a favor do peso)
    secoes = spec["secoes"]

    def _area(grupo):
        s = secoes[grupo]
        return float(s["b"]) * float(s["h"])

    # ponto fixo do peso proprio (molde da laje do G8): a madeira pesa e
    # o peso realimenta a carga ate parar de crescer (3 iteracoes).
    pp_kNm2 = 0.0  # por m2 inclinado
    analise = None
    for _it in range(3):
        cargas = {}
        for nid in sup_ids:
            trib_h = trib[nid] * cos_t  # projecao p/ a sobrecarga
            G = (g_telha + pp_kNm2) * trib[nid] * esp
            Q = sobre_q * trib_h * esp
            cargas[nid] = (0.0, -(G + Q))
            cargas[nid] = (0.0, -(G + Q), G, Q)
        beiral_L = min(nos, key=lambda nid: nos[nid][0])
        beiral_R = max(nos, key=lambda nid: nos[nid][0])
        cargas_nos = {nid: (c[0], c[1]) for nid, c in cargas.items()}
        analise = analisa_trelica(nos, barras, cargas_nos,
                                  beiral_L, beiral_R)
        # volume -> novo pp.
        vol = sum(comp[bar] * _area(bar[2]) for bar in barras)
        vol += _volume_tercas(geo, secoes, esp, ext)
        area_por_tesoura = 2.0 * (vao / 2.0 / cos_t) * esp
        pp_novo = vol * rho * G_M_S2 / 1000.0 / area_por_tesoura
        if abs(pp_novo - pp_kNm2) < 1e-6:
            pp_kNm2 = pp_novo
            break
        pp_kNm2 = pp_novo

    # fechamento: reacoes x carga lancada (irmao do baldrame).
    G_tot = sum(c[2] for c in cargas.values())
    Q_tot = sum(c[3] for c in cargas.values())
    R_tot = analise["RyL"] + analise["RyR"]
    erro = (abs(R_tot - (G_tot + Q_tot)) / (G_tot + Q_tot)
            if (G_tot + Q_tot) > 0 else 0.0)
    # ... e a carga lancada x O TELHADO QUE ELA COBRE. So o primeiro
    # fecha por construcao (a reacao SAI do equilibrio da carga: e' a
    # assercao tautologica do D86). O segundo tem origem independente -
    # a area de telhado da faixa da tesoura - e e' o unico dos dois que
    # enxerga tributario errado. As duas areas sao diferentes de
    # proposito: a telha e o peso proprio cobrem o plano INCLINADO; a
    # sobrecarga de manutencao e' projetada na horizontal.
    fechamento_area = confere_fechamento_area(
        G_tot, Q_tot, g_telha + pp_kNm2, sobre_q, vao, esp, cos_t)
    fechamento = {"ok": bool(erro <= TOL_FECHAMENTO),
                  "R_kN": round(R_tot, 2),
                  "lancado_kN": round(G_tot + Q_tot, 2),
                  "G_kN": round(G_tot, 2), "Q_kN": round(Q_tot, 2),
                  "erro_rel": round(erro, 5)}

    # verificacao barra a barra (ELU 1,4).
    trav_inf = bool(spec["contraventamento_banzo_inf"])
    ver_barras = []
    reprovadas = []
    construtivas = []  # 9.2.1 e 9.3, por grupo (uma vez cada)
    for bar in barras:
        n1, n2, grupo = bar
        L = comp[bar]
        Nk = analise["esforcos_Nk"][bar]
        Nd = GF * Nk
        sec = secoes[grupo]
        b, h = float(sec["b"]), float(sec["h"])
        A = b * h
        Ix = b * h ** 3 / 12.0  # flexao no plano (h = altura no plano)
        Iy = h * b ** 3 / 12.0
        if Nk >= 0:
            A_liq = (b - float(spec["ligacao"]["d_mm"]) / 1000.0) * h
            r = mad.verifica_tracao(Nd, max(A_liq, 1e-9), res["ft0d"])
            r = dict(r, lambda_=None, kc=None)
        else:
            L0_in = L
            if grupo == "banzo_inf" and not trav_inf:
                L0_out = vao  # sem contraventamento, flamba o vao inteiro
            else:
                L0_out = L
            lam = max(mad.esbeltez(L0_in, Ix, A),
                      mad.esbeltez(L0_out, Iy, A))
            r = mad.verifica_compressao(Nd, A, res["fc0d"], lam,
                                        prop["fc0k_d0"], prop["E005"])
        # 9.2.1 (secao minima) e 9.3 (L0 <= 40x a dimensao comprimida,
        # 50x na tracionada): limites CONSTRUTIVOS proprios, ao lado do
        # lambda <= 140. Sem eles a peca podia sair legal na conta e
        # proibida na norma.
        papel = (PAPEL_921["banzo"] if grupo.startswith("banzo")
                 else PAPEL_921["secundaria"])
        r921 = mad.verifica_dimensoes_minimas_921(b, h, papel)
        solic = "tracionada" if Nk >= 0 else "comprimida"
        L0_921 = L if (Nk >= 0 or grupo != "banzo_inf" or trav_inf) else vao
        r93 = mad.verifica_esbeltez_geometrica_93(L0_921, min(b, h), solic)
        if not r921["OK"] or not r93["OK"]:
            construtivas.append(
                "%s-%s (%s): %s" % (n1, n2, grupo,
                                    "; ".join(r921["falhas"]
                                              + ([r93["motivo"]]
                                                 if r93["motivo"] else []))))
        r = dict(r, barra="%s-%s" % (n1, n2), grupo=grupo,
                 L_m=round(L, 3), Nk_kN=round(Nk, 2),
                 Nd_kN=round(Nd, 2), b_m=b, h_m=h,
                 dimensoes_9_2_1=r921, esbeltez_9_3=r93)
        ver_barras.append(r)
        if not r["OK"]:
            reprovadas.append("%s-%s (%s): util %.2f" %
                             (n1, n2, grupo, r.get("util", 9.9)))

    # tercas: biapoiadas no espacamento, faixa = painel inclinado.
    painel_inc = (vao / 2.0 / n_pain) / cos_t
    sec_t = secoes["terca"]
    bt, ht = float(sec_t["b"]), float(sec_t["h"])
    At = bt * ht
    Wt = bt * ht ** 2 / 6.0
    It = bt * ht ** 3 / 12.0
    trib_h_terca = painel_inc * cos_t
    g_lin = (g_telha + pp_kNm2) * painel_inc  # kN/m por terca interior
    q_lin = sobre_q * trib_h_terca
    Md = GF * (g_lin + q_lin) * esp ** 2 / 8.0
    Vd = GF * (g_lin + q_lin) * esp / 2.0
    L1 = float(spec["travamento_borda_comprimida_m"])
    r_estab = mad.dispensa_estabilidade_lateral_656(
        bt, ht, L1, prop["E0m"], res["fmd"], km["kmod"],
        rotacao_apoio_impedida=True)
    r_flex = mad.verifica_flexao(Md, Wt, res["fmd"], r_estab)
    r_cis = mad.verifica_cisalhamento(Vd, At, res["fv0d"])
    r_els = mad.verifica_els_terca(g_lin, q_lin, esp, prop["E0m"],
                                   It, int(spec["madeira"]["umidade"]),
                                   bool(spec.get("forro_fragil", False)),
                                   float(spec.get("contraflecha_m", 0.0)),
                                   spec.get("limites_flecha"))
    # Apoio da terca: a terca corre a extensao INTEIRA sobre varias
    # tesouras, entao a tesoura INTERIOR recebe as duas meias-cargas dos
    # tramos vizinhos (R = w.esp no modelo biapoiado por tramo que a
    # flexao ja adota), e nao meio tramo. E as duas pontas recebem meio
    # tramo, porem na EXTREMIDADE da peca, onde a 6.2.4 manda alfa_n = 1.
    # Os dois casos sao verificados e governa o pior: usar so R = w.esp/2
    # com o alfa_n da Tab.6 subestimava o apoio interior em 2x.
    w_terca = g_lin + q_lin
    A_apoio_terca = bt * float(secoes["banzo_sup"]["b"])
    ext_apoio_cm = float(secoes["banzo_sup"]["b"]) * 100.0
    tem_interior = ext > esp + 1e-9
    casos_apoio = [("extremidade", w_terca * esp / 2.0, None)]
    if tem_interior:
        casos_apoio.append(("interior", w_terca * esp, esp * 100.0))
    r_apoio_terca = None
    for nome, R, dist in casos_apoio:
        r = mad.verifica_apoio(R, A_apoio_terca, res["fc0d"],
                               ext_apoio_cm, dist_extremidade_cm=dist)
        r = dict(r, apoio=nome, R_kN=round(R, 3))
        if r_apoio_terca is None or r["util"] > r_apoio_terca["util"]:
            r_apoio_terca = r
    r921_terca = mad.verifica_dimensoes_minimas_921(
        bt, ht, PAPEL_921["secundaria"])
    if not r921_terca["OK"]:
        construtivas.append("terca: " + "; ".join(r921_terca["falhas"]))
    terca = {"OK": bool(r_flex["OK"] and r_cis["OK"] and r_els["OK"]
                         and r_apoio_terca["OK"] and r921_terca["OK"]),
             "dimensoes_9_2_1": r921_terca,
             "estabilidade_lateral": r_estab,
             "Md_kNm": round(Md, 3), "Vd_kN": round(Vd, 3),
             "flexao": r_flex, "cisalhamento": r_cis, "els": r_els,
             "apoio": r_apoio_terca, "w_g_kNm": round(g_lin, 3),
             "w_q_kNm": round(q_lin, 3)}

    # ligacoes: apoio (reacao max) + no interno critico (max |N|).
    lig = spec["ligacao"]
    d_mm = float(lig["d_mm"])
    fe_apoio = mad.embutimento_fek(d_mm, prop["rhok"], conifera,
                                   True, 0.0)
    fe_no = mad.embutimento_fek(d_mm, prop["rhok"], conifera, True,
                                float(inc))
    base_lig = {"t_chapa_mm": float(lig["t_chapa_mm"]),
                "tipo_pino": lig["tipo_pino"], "d_mm": d_mm,
                "fu_MPa": float(lig["fu_MPa"]),
                "n_pinos": int(lig["n_pinos"]),
                "espacamentos": lig["espacamentos"],
                "alpha_graus": 0.0,
                "t_madeira_mm": float(secoes["banzo_inf"]["b"]) * 1000.0,
                "penetracao_mm": float(secoes["banzo_inf"]["b"]) * 1000.0,
                "kmod1": km["kmod1"], "kmod2": km["kmod2"]}
    R_apoio_kN = max(abs(analise["RyL"]), abs(analise["RyR"]))
    cfg_apoio = dict(base_lig, config_73=lig["config_73"],
                     t1_mm=float(secoes["banzo_inf"]["h"]) * 1000.0,
                     t2_mm=float(secoes["banzo_inf"]["h"]) * 1000.0,
                     fe1_Nmm2=fe_apoio["fe_k_Nmm2"],
                     fe2_Nmm2=fe_apoio["fe_k_Nmm2"],
                     n_planos=2 if "dupla" in lig["config_73"] else 1)
    r_lig_apoio = mad.verifica_ligacao(GF * R_apoio_kN, cfg_apoio)
    bar_crit = max(ver_barras, key=lambda r: abs(r["Nd_kN"]))
    sec_c = secoes[bar_crit["grupo"]]
    cfg_no = dict(base_lig,
                  config_73=lig["config_73"],
                  t1_mm=float(sec_c["h"]) * 1000.0,
                  t2_mm=float(sec_c["h"]) * 1000.0,
                  fe1_Nmm2=fe_no["fe_k_Nmm2"],
                  fe2_Nmm2=fe_no["fe_k_Nmm2"],
                  alpha_graus=float(inc),
                  t_madeira_mm=float(sec_c["b"]) * 1000.0,
                  penetracao_mm=float(sec_c["b"]) * 1000.0,
                  n_planos=2 if "dupla" in lig["config_73"] else 1)
    r_lig_no = mad.verifica_ligacao(abs(bar_crit["Nd_kN"]), cfg_no)
    # tracao perpendicular no beiral (componente da banzo superior).
    N_sup_beiral = max((abs(analise["esforcos_Nk"][bar])
                        for bar in barras if bar[2] == "banzo_sup"),
                       default=0.0)
    Fv_beiral = N_sup_beiral * math.sin(math.radians(inc))
    r_f90 = mad.verifica_tracao_perp_no(
        GF * Fv_beiral, float(secoes["banzo_sup"]["b"]) * 1000.0,
        float(secoes["banzo_sup"]["h"]) * 1000.0,
        float(lig["he_mm"]), km["kmod"])
    ligacoes = {"OK": bool(r_lig_apoio["OK"] and r_lig_no["OK"]
                           and r_f90["OK"]),
                "apoio": r_lig_apoio, "no_critico": r_lig_no,
                "tracao_perp_beiral": r_f90,
                "barra_critica": bar_crit["barra"]}

    # apoio da tesoura na casa (compressao perpendicular).
    sec_inf = secoes["banzo_inf"]
    # a tesoura pousa na EXTREMIDADE do banzo inferior: a 6.2.4 manda
    # alfa_n = 1 quando a forca chega a menos de 7,5 cm da ponta, e e'
    # esse o caso (dist_extremidade nao declarada => piso).
    r_apoio = mad.verifica_apoio(
        R_apoio_kN, float(sec_inf["b"]) * comp_apoio, res["fc0d"],
        comp_apoio * 100.0)

    # quantitativos: volume por grupo + area de telha + tesouras.
    n_tesouras = int(round(ext / esp)) + 1
    if n_tesouras < 2:
        raise EntradaTelhado("extensao comporta menos de 2 tesouras: "
                             "declare espacamento <= extensao")
    pecas = []
    for grupo in ("banzo_sup", "banzo_inf", "diagonal", "montante"):
        Ltot = sum(comp[bar] for bar in barras if bar[2] == grupo)
        n = sum(1 for bar in barras if bar[2] == grupo)
        sec = secoes[grupo]
        pecas.append({"grupo": grupo, "b_m": float(sec["b"]),
                      "h_m": float(sec["h"]), "L_por_tesoura_m": round(Ltot, 3),
                      "n_por_tesoura": n,
                      "vol_por_tesoura_m3": round(Ltot * _area(grupo), 4)})
    # tercas: uma por no superior, vencendo a extensao em tramos de `esp`.
    n_tercas = len(sup_ids)
    L_terca = ext
    pecas.append({"grupo": "terca", "b_m": bt, "h_m": ht,
                  "L_por_tesoura_m": round(L_terca * n_tercas / n_tesouras, 3),
                  "n_por_tesoura": round(n_tercas / n_tesouras, 3),
                  "vol_por_tesoura_m3": round(
                      n_tercas * L_terca * At / n_tesouras, 4)})
    vol_total = round(sum(p["vol_por_tesoura_m3"] for p in pecas)
                      * n_tesouras, 3)
    area_telha = 2.0 * (vao / 2.0 / cos_t) * ext

    # descida: reacao por tesoura -> apoio que a casa ja tem.
    R_por_tesoura = {"G_kN": round(G_tot, 2), "Q_kN": round(Q_tot, 2),
                     "R_kN": round(G_tot + Q_tot, 2)}
    W_tot_G = G_tot * n_tesouras
    W_tot_Q = Q_tot * n_tesouras
    descida = {"n_tesouras": n_tesouras,
               "reacao_por_tesoura_kN": R_por_tesoura,
               "W_total_G_kN": round(W_tot_G, 2),
               "W_total_Q_kN": round(W_tot_Q, 2),
               "W_total_kN": round(W_tot_G + W_tot_Q, 2),
               "apoio": spec["apoio"]}

    gates = {
        "geometria": {"OK": True, "h_cumeeira_m": round(geo["h_cumeeira"], 3),
                      "n_barras": len(barras), "n_nos": len(nos)},
        "fechamento_carga": {"OK": fechamento["ok"],
                             "erro_rel": fechamento["erro_rel"],
                             "R_kN": fechamento["R_kN"],
                             "lancado_kN": fechamento["lancado_kN"]},
        "fechamento_area": dict(fechamento_area,
                                OK=fechamento_area["ok"]),
        "barras": {"OK": not reprovadas, "n": len(ver_barras),
                   "reprovadas": reprovadas},
        "tercas": {"OK": terca["OK"]},
        "ligacoes": {"OK": ligacoes["OK"]},
        "apoio_madeira": {"OK": r_apoio["OK"], "util": r_apoio["util"]},
        "construtivas_9": {"OK": not construtivas,
                           "fora_do_minimo": construtivas},
    }
    reprovados = [k for k, g in gates.items() if not g["OK"]]
    return {
        "ATENDE": not reprovados, "reprovados": reprovados, "gates": gates,
        "vao_m": vao, "inclinacao_graus": inc, "extensao_m": ext,
        "espacamento_m": esp, "n_paineis": n_pain,
        "h_cumeeira_m": round(geo["h_cumeeira"], 3),
        "telha_perfil": perfil, "telha_peso_kNm2": g_telha,
        "sobrecarga_kNm2": sobre_q,
        "pp_madeira_kNm2": round(pp_kNm2, 4),
        "rho_madeira_kgm3": rho,
        "madeira": {"classe": prop["classe"], "kmod": km["kmod"],
                    "kmod1": km["kmod1"], "kmod2": km["kmod2"],
                    "ft0d": res["ft0d"], "fc0d": res["fc0d"],
                    "fmd": res["fmd"], "fv0d": res["fv0d"]},
        "barras": ver_barras, "terca": terca, "ligacoes": ligacoes,
        "apoio_verificacao": r_apoio,
        "reacoes_caracteristicas": {"RyL_kN": round(analise["RyL"], 2),
                                    "RyR_kN": round(analise["RyR"], 2),
                                    "RxL_kN": round(analise["RxL"], 2)},
        "pecas": pecas, "vol_madeira_m3": vol_total,
        "area_telha_m2": round(area_telha, 2),
        "n_tesouras": n_tesouras, "descida": descida,
        "geometria_nos": {k: (round(v[0], 3), round(v[1], 3))
                          for k, v in nos.items()},
        "escopo": escopo(),
    }


def _volume_tercas(geo, secoes, espacamento, extensao):
    """Volume das tercas por tesoura (rateio do total)."""
    sup_ids = {n1 for n1, _n2, g in geo["barras"] if g == "banzo_sup"} | \
        {n2 for _n1, n2, g in geo["barras"] if g == "banzo_sup"}
    n_tercas = len(sup_ids)
    n_tes = int(round(extensao / espacamento)) + 1
    sec = secoes["terca"]
    return n_tercas * extensao * float(sec["b"]) * float(sec["h"]) / n_tes


def escopo():
    """O que este modulo cobre, dito em voz alta."""
    base = mad.escopo()
    base.update({
        "tesoura_howe": "implemented",
        "tercas": "implemented",
        "descida_telhado": "implemented",
        "telha_peso_tipo_gate7": "implemented",
    })
    return base


def relatorio_pt(r):
    """Quadro-resumo do telhado de madeira."""
    L = ["TELHADO DE MADEIRA (NBR 7190-1, tesoura Howe) - quadro-resumo",
         "  vao %.2f m ; inclinacao %.1f graus ; cumeeira %.2f m ; %d "
         "tesoura(s) a cada %.2f m" % (
             r["vao_m"], r["inclinacao_graus"], r["h_cumeeira_m"],
             r["n_tesouras"], r["espacamento_m"]),
         "  telha %s (%.3f kN/m2) ; sobrecarga %.2f kN/m2 ; pp madeira "
         "%.3f kN/m2" % (
             r["telha_perfil"].get("nome", r["telha_perfil"].get("tipo")),
             r["telha_peso_kNm2"], r["sobrecarga_kNm2"],
             r["pp_madeira_kNm2"]),
         "  madeira %s kmod=%.3f (ft0,d=%.0f fc0,d=%.0f fm,d=%.0f "
         "fv0,d=%.0f kN/m2)" % (
             r["madeira"]["classe"], r["madeira"]["kmod"],
             r["madeira"]["ft0d"], r["madeira"]["fc0d"],
             r["madeira"]["fmd"], r["madeira"]["fv0d"]),
         "  BARRAS: %d verificadas -> %s" % (
             r["gates"]["barras"]["n"],
             "ATENDE" if r["gates"]["barras"]["OK"] else "REPROVA"),
         "  TERCAS: %s ; LIGACOES (apoio + no critico %s): %s ; "
         "APOIO: %s" % (
             "ATENDE" if r["gates"]["tercas"]["OK"] else "REPROVA",
             r["ligacoes"]["barra_critica"],
             "ATENDE" if r["gates"]["ligacoes"]["OK"] else "REPROVA",
             "ATENDE" if r["gates"]["apoio_madeira"]["OK"] else "REPROVA"),
         "  REACAO por tesoura: G=%.2f Q=%.2f kN ; total G=%.1f Q=%.1f kN "
         "-> apoio '%s'" % (
             r["descida"]["reacao_por_tesoura_kN"]["G_kN"],
             r["descida"]["reacao_por_tesoura_kN"]["Q_kN"],
             r["descida"]["W_total_G_kN"], r["descida"]["W_total_Q_kN"],
             r["descida"]["apoio"]),
         "  MADEIRA: %.3f m3 em %d tesouras ; TELHA: %.1f m2 inclinados"
         % (r["vol_madeira_m3"], r["n_tesouras"], r["area_telha_m2"]),
         "  RESULTADO GLOBAL: %s" % (
             "ATENDE" if r["ATENDE"]
             else "REPROVA -> " + ", ".join(r["reprovados"])),
         "  [TELHADO GRAVITACIONAL: vento/succao fora do lote; "
         "contraflecha e contraventamento longitudinal fora do lote.]",
         ]
    if r["telha_perfil"].get("ilustrativo"):
        L.append("  [A CONFIRMAR: Wef/Ief do perfil '%s' sao ilustrativos; "
                 "o PESO (%.3f kN/m2) e' declarado e e' o que carrega a "
                 "tesoura]" % (r["telha_perfil"].get("tipo"),
                                r["telha_peso_kNm2"]))
    return "\n".join(L)
