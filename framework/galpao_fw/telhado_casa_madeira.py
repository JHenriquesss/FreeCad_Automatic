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
# VENTO/SUCCAO/UPLIFT (G71): com spec["vento"] declarado o modulo monta a
# pressao liquida (cpe - cpi).q da Tabela 5 da NBR 6123 (duas aguas,
# bloco pelo h/b, lida na p.15 do PDF) e roda a combinacao com permanente
# favoravel ao lado da gravitacional 1,4.(G+Q): cada barra guarda o par
# (Ngravidade, Nuplift) e e' verificada nos dois; a ancoragem e' verificada
# contra o arrancamento; a terca e' verificada sob momento invertido com o
# L1 da borda inferior. Sem vento declarado a cadeia segue gravitacional
# (compativel G66). Cap. 9 da 6123 (dinamico) e +2 aguas seguem fora do
# lote, nomeados em escopo() com motivo.
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
ligacoes em chapa de aco (7.3) ou madeira-madeira (7.2, por declaracao)
e reacoes para a descida."""

from __future__ import annotations

import math

import madeira_nbr7190 as mad

GF = 1.4  # ELU gravitacional (mesma convencao dos modulos de concreto)
# G71 - combinacao com permanente favoravel (uplift). Fontes lidas na pagina
# (NBR 8681:2025, fontes/04_ACOES_EQUIPAMENTOS/...8681-2025...pdf):
# - 5.1.3.1 (p.12): em casos especificos consideram-se DOIS conjuntos de
#   combinacoes - permanente desfavoravel e permanente favoravel;
# - Tab.1/Tab.2 (p.14): permanente favoravel = 1,0 na normal. Adota-se 0,9
#   (extremo estrito, conservador para uplift: menos estabilizante = mais
#   arrancamento), DECLARADO no resultado como G_FAV;
# - 5.1.4.2 (p.15): acao variavel favoravel NAO entra na combinacao
#   (Q = 0 no uplift) e Tab.4 (p.15): vento = 1,4.
G_FAV = 0.9
GAMA_VENTO = 1.4
# 9.2.1: banzo de trelica e' "barra longitudinal" = peca principal
# isolada; diagonal, montante e terca sao secundarias.
PAPEL_921 = {"banzo": "principal_isolada", "secundaria": "secundaria_isolada"}
TOL_FECHAMENTO = 0.02  # mesma tolerancia do baldrame/alvenaria
G_M_S2 = 9.81


# --- vento: Tabela 5 da NBR 6123 (G71) ---------------------------------------
# Transcrita da p.15 do PDF (ACOES__NBR__NBR-6123-1988__forcas-vento-
# edificacoes.pdf): telhado duas aguas simetrico, planta retangular.
# (theta_graus: EF, GH) para vento perpendicular a cumeeira (alfa = 90) e
# (EG, FH) para vento paralelo (alfa = 0, uplift simetrico nas duas aguas).
# Tres blocos de altura relativa; o galpao usa o bloco do meio (h/b = 0,6:
# 5 graus EF -0,90 GH -0,60; 10 graus EF -1,10 GH -0,60 - confere com
# vento_nbr6123.cpe_telhado). A casa terrea cai em geral no bloco <= 1/2,
# onde GH = -0,40 (nao -0,60): fixar o bloco do galpao seria outro numero
# de memoria. Por isso o bloco entra pelo h/b declarado.
TAB5_CPE = {
    "h<=1/2": {
        "alfa90": [(0.0, -0.8, -0.4), (5.0, -0.9, -0.4),
                   (10.0, -1.2, -0.4), (15.0, -1.0, -0.4),
                   (20.0, -0.4, -0.4), (30.0, 0.0, -0.4),
                   (45.0, +0.3, -0.5), (60.0, +0.7, -0.6)],
        "alfa0": [(0.0, -0.8, -0.4), (5.0, -0.8, -0.4),
                  (10.0, -0.8, -0.6), (15.0, -0.8, -0.6),
                  (20.0, -0.7, -0.6), (30.0, -0.7, -0.6)],
    },
    "1/2-3/2": {
        "alfa90": [(0.0, -0.8, -0.6), (5.0, -0.9, -0.6),
                   (10.0, -1.1, -0.6), (15.0, -1.0, -0.6),
                   (20.0, -0.7, -0.5), (30.0, -0.2, -0.5),
                   (45.0, +0.2, -0.5), (60.0, +0.6, -0.5)],
        "alfa0": [(0.0, -1.0, -0.6), (5.0, -0.9, -0.6),
                  (10.0, -0.8, -0.6), (15.0, -0.8, -0.6),
                  (20.0, -0.8, -0.6), (30.0, -0.8, -0.8)],
    },
    "3/2-6": {
        "alfa90": [(0.0, -0.8, -0.6), (5.0, -0.8, -0.6),
                   (10.0, -0.8, -0.6), (15.0, -0.8, -0.6),
                   (20.0, -0.8, -0.6), (30.0, -1.0, -0.5),
                   (40.0, -0.2, -0.5), (50.0, +0.2, -0.5),
                   (60.0, +0.5, -0.5)],
        "alfa0": [(0.0, -0.9, -0.7), (5.0, -0.8, -0.8),
                  (10.0, -0.8, -0.8), (15.0, -0.8, -0.8),
                  (20.0, -0.8, -0.8), (30.0, -0.8, -0.7)],
    },
}
FONTE_TAB5 = ("NBR 6123:1988 Tab.5 p.15 "
              "(fontes/04_ACOES_EQUIPAMENTOS)")


def _interp_tab(theta, pontos):
    """Interpolacao linear em theta, clampada ao dominio tabelado."""
    t = min(max(float(theta), pontos[0][0]), pontos[-1][0])
    for k in range(len(pontos) - 1):
        t0, t1 = pontos[k][0], pontos[k + 1][0]
        if t <= t1 + 1e-9:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return (pontos[k][1] + f * (pontos[k + 1][1] - pontos[k][1]),
                    pontos[k][2] + f * (pontos[k + 1][2] - pontos[k][2]))
    return pontos[-1][1], pontos[-1][2]


def bloco_tab5(h_sobre_b):
    """Bloco de altura relativa da Tab.5 pelo h/b (h = altura no beiral,
    b = vao perpendicular a cumeeira)."""
    r = float(h_sobre_b)
    if not r > 0:
        raise EntradaTelhado("h/b deve ser > 0 (recebido %s)" % r)
    if r <= 0.5:
        return "h<=1/2"
    if r <= 1.5:
        return "1/2-3/2"
    if r <= 6.0:
        return "3/2-6"
    raise EntradaTelhado(
        "h/b = %.2f fora da Tab.5 (limite 6): telhado fora do campo da "
        "tabela" % r)


def cpe_telhado_2aguas(theta_graus, h_sobre_b):
    """cpe do telhado de duas aguas pela NBR 6123 Tab.5 (lida na p.15).

    Devolve {"bloco", "alfa90": (EF, GH), "alfa0": (EG, FH), "fonte"}.
    alfa90 = vento perpendicular a cumeeira (uma agua de cada lado);
    alfa0 = vento paralelo (as duas aguas na mesma zona: EG governa o
    uplift simetrico e e' envelopado junto)."""
    bloco = bloco_tab5(h_sobre_b)
    ef, gh = _interp_tab(theta_graus, TAB5_CPE[bloco]["alfa90"])
    eg, fh = _interp_tab(theta_graus, TAB5_CPE[bloco]["alfa0"])
    return {"bloco": bloco,
            "alfa90": (round(ef, 3), round(gh, 3)),
            "alfa0": (round(eg, 3), round(fh, 3)),
            "fonte": FONTE_TAB5}


def _valida_vento(vspec, inclinacao_graus, vao):
    """Valida spec["vento"] e devolve os parametros conferidos.

    cpi e' DECLARADO com a origem (6.2.5-a/b/c, 6.2.6 ou 6.2.7, pp.12-13):
    sem origem o numero e' memoria. Faixa aceita [-0,9, +0,8] (a envoltoria
    dos valores que esses itens entregam). S2 sai da Tab.1 (5.3.3, p.9),
    a mesma que vento_nbr6123.s2_factor transcreve para o galpao."""
    for chave in ("v0", "categoria", "classe", "s1", "s3",
                  "h_edificacao_m", "cpi", "cpi_origem"):
        if vspec.get(chave) is None:
            raise EntradaTelhado(
                "vento.%s deve ser declarado (sem default): sem sitio e "
                "sem cpi nao ha succao" % chave)
    v0 = float(vspec["v0"])
    if not v0 > 0:
        raise EntradaTelhado("vento.v0 deve ser > 0")
    s1, s3 = float(vspec["s1"]), float(vspec["s3"])
    if not (s1 > 0 and s3 > 0):
        raise EntradaTelhado("vento.s1/s3 devem ser > 0")
    h_ed = float(vspec["h_edificacao_m"])
    if not h_ed > 0:
        raise EntradaTelhado("vento.h_edificacao_m deve ser > 0")
    cpi = float(vspec["cpi"])
    if not -0.9 - 1e-9 <= cpi <= 0.8 + 1e-9:
        raise EntradaTelhado(
            "vento.cpi = %.2f fora da envoltoria da 6.2.5/6.2.6 "
            "([-0,9, +0,8]): declare a origem (abertura dominante, "
            "permeabilidade ou 6.2.7)" % cpi)
    if not str(vspec["cpi_origem"]).strip():
        raise EntradaTelhado("vento.cpi_origem deve nomear o item da "
                             "6.2 (a, b, c, 6.2.6 ou 6.2.7, pp.12-13)")
    import vento_nbr6123 as _vi
    try:
        _b, _fr, _p, s2 = _vi.s2_factor(
            str(vspec["categoria"]), str(vspec["classe"]),
            float(vspec.get("z_m", h_ed)))
    except (ValueError, KeyError) as exc:
        raise EntradaTelhado("vento S2 (Tab.1, 5.3.3 p.9): %s" % exc)
    z = float(vspec.get("z_m", h_ed))
    vk = v0 * s1 * s2 * s3
    q = 0.613 * vk ** 2 / 1000.0  # kN/m2
    h_sobre_b = h_ed / float(vao)
    cpe = cpe_telhado_2aguas(float(inclinacao_graus), h_sobre_b)
    return {"v0": v0, "categoria": str(vspec["categoria"]),
            "classe": str(vspec["classe"]), "s1": s1, "s3": s3,
            "s2": round(s2, 3), "z_m": z, "vk": round(vk, 2),
            "q_kNm2": round(q, 4), "h_edificacao_m": h_ed,
            "h_sobre_b": round(h_sobre_b, 3), "cpe": cpe,
            "cpi": cpi, "cpi_origem": str(vspec["cpi_origem"]).strip()}


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
    if spec.get("travamento_borda_inferior_m") is not None and not float(
            spec["travamento_borda_inferior_m"]) >= 0:
        raise EntradaTelhado("travamento_borda_inferior_m deve ser >= 0")
    if spec.get("vento") is not None and not isinstance(
            spec.get("vento"), dict):
        raise EntradaTelhado("vento deve ser um objeto (v0, categoria, "
                             "classe, s1, s3, h_edificacao_m, cpi, "
                             "cpi_origem)")
    anc = spec.get("ancoragem")
    if anc is not None:
        if not isinstance(anc, dict):
            raise EntradaTelhado("ancoragem deve ser um objeto (tipo, "
                                 "resistencia_arrancamento_kN, origem)")
        for chave in ("tipo", "resistencia_arrancamento_kN", "origem"):
            if anc.get(chave) is None:
                raise EntradaTelhado(
                    "ancoragem.%s deve ser declarado: sem capacidade "
                    "declarada (ensaio/catalogo) nao ha numero" % chave)
        if not float(anc["resistencia_arrancamento_kN"]) > 0:
            raise EntradaTelhado(
                "ancoragem.resistencia_arrancamento_kN deve ser > 0")
        if not str(anc["origem"]).strip():
            raise EntradaTelhado("ancoragem.origem deve dizer de onde vem "
                                 "a capacidade (ensaio/catalogo)")
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
    sis = lig.get("sistema")
    if sis is None:
        sis = ("chapa_aco" if lig.get("config_73") is not None
               else ("madeira_madeira" if lig.get("n_cortes") is not None
                     else None))
    if sis not in ("chapa_aco", "madeira_madeira"):
        raise EntradaTelhado(
            "ligacao.sistema deve ser declarado ('chapa_aco' com "
            "config_73 + t_chapa_mm, ou 'madeira_madeira' com n_cortes "
            "+ d0_mm, 7.2): sem no verificado a tesoura e' um desenho")
    if sis == "chapa_aco":
        for chave in ("tipo_pino", "d_mm", "fu_MPa", "n_pinos",
                      "config_73", "espacamentos", "he_mm",
                      "t_chapa_mm"):
            if lig.get(chave) is None:
                raise EntradaTelhado(
                    "ligacao.%s deve ser declarado: sem no verificado "
                    "a tesoura e' um desenho" % chave)
    else:
        for chave in ("tipo_pino", "d_mm", "d0_mm", "fu_MPa", "n_pinos",
                      "n_cortes", "espacamentos", "he_mm"):
            if lig.get(chave) is None:
                raise EntradaTelhado(
                    "ligacao.%s deve ser declarado: o no madeira-madeira "
                    "(7.2) exige pre-furacao Tab.16 e n_cortes" % chave)
        try:
            nc = int(lig["n_cortes"])
        except (TypeError, ValueError):
            raise EntradaTelhado(
                "ligacao.n_cortes deve ser 1 ou 2 (7.2: corte simples "
                "ou duplo, Figs.19-21)") from None
        if nc not in (1, 2):
            raise EntradaTelhado(
                "ligacao.n_cortes = %r fora da 7.2 (1|corte simples, "
                "2|corte duplo, Figs.19-21)" % (lig["n_cortes"],))
        if lig.get("config_73") is not None \
                or lig.get("t_chapa_mm") is not None:
            raise EntradaTelhado(
                "ligacao madeira-madeira (7.2) nao leva config_73 nem "
                "t_chapa_mm: o no e' madeira-madeira por declaracao, "
                "a chapa continua disponivel via sistema='chapa_aco'")
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


def _checa_barra_axial(n1, n2, grupo, L, Nd, sec, res, prop,
                       d_pino_mm, trav_inf, vao):
    """Verifica UMA barra sob UM Nd (ELU): tracao (6.3.2, area liquida) ou
    compressao com estabilidade (6.3.3+6.5, lambda <= 140, kc) + 9.2.1/9.3.
    O chamador roda nos dois sinais do par (gravidade, uplift): barra que
    passa de tracao para compressao ganha a estabilidade automaticamente,
    e o banzo inferior sem contraventamento flamba o vao inteiro."""
    b, h = float(sec["b"]), float(sec["h"])
    A = b * h
    Ix = b * h ** 3 / 12.0  # flexao no plano (h = altura no plano)
    Iy = h * b ** 3 / 12.0
    if Nd >= 0:
        A_liq = (b - float(d_pino_mm) / 1000.0) * h
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
    papel = (PAPEL_921["banzo"] if grupo.startswith("banzo")
             else PAPEL_921["secundaria"])
    r921 = mad.verifica_dimensoes_minimas_921(b, h, papel)
    solic = "tracionada" if Nd >= 0 else "comprimida"
    L0_921 = L if (Nd >= 0 or grupo != "banzo_inf" or trav_inf) else vao
    r93 = mad.verifica_esbeltez_geometrica_93(L0_921, min(b, h), solic)
    construtivas = []
    if not r921["OK"] or not r93["OK"]:
        construtivas.append(
            "%s-%s (%s): %s" % (n1, n2, grupo,
                                "; ".join(r921["falhas"]
                                          + ([r93["motivo"]]
                                             if r93["motivo"] else []))))
    r = dict(r, barra="%s-%s" % (n1, n2), grupo=grupo,
             L_m=round(L, 3), Nd_kN=round(Nd, 2), b_m=b, h_m=h,
             dimensoes_9_2_1=r921, esbeltez_9_3=r93)
    return r, construtivas


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

    # --- uplift G71: G, Q e W separados, combinados depois (linearidade) ----
    # A trelica e' linear: N(0,9.G + 1,4.W) = 0,9.N(G) + 1,4.N(W). Por isso
    # tres analises caracteristicas (G so, Q so, W so por caso de vento) e
    # as combinacoes 1,4.(G+Q) e 0,9.G+1,4.W saem por superposicao - a
    # reacao de uplift NAO e' a gravitacional com sinal trocado a mao (foi
    # exatamente o bug _wind_unico do galpao: succao sem sinal dando "um
    # numero plausivel").
    beiral_L = min(nos, key=lambda nid: nos[nid][0])
    beiral_R = max(nos, key=lambda nid: nos[nid][0])
    cargas_G = {nid: (0.0, -c[2]) for nid, c in cargas.items()}
    cargas_Q = {nid: (0.0, -c[3]) for nid, c in cargas.items()}
    analise_G = analisa_trelica(nos, barras, cargas_G, beiral_L, beiral_R)
    analise_Q = analisa_trelica(nos, barras, cargas_Q, beiral_L, beiral_R)
    vento_info = None
    casos_W = {}  # caso -> {esforcos_Nk, RyL, RyR, RxL, p_aguas, W_tot_kN}
    if spec.get("vento") is not None:
        vento_info = _valida_vento(spec["vento"], inc, vao)
        _q = vento_info["q_kNm2"]
        _cpi = vento_info["cpi"]
        _ef, _gh = vento_info["cpe"]["alfa90"]
        _eg, _fh = vento_info["cpe"]["alfa0"]
        # pressao liquida (cpe - cpi).q por agua (kN/m2, normal ao plano;
        # negativa = succao para fora). Transversal: cada agua na sua zona;
        # longitudinal: as duas aguas na mesma zona (EG governa o uplift
        # simetrico - o caso que o refino do galpao quase removeu).
        p_trans = {"L": (_ef - _cpi) * _q, "R": (_gh - _cpi) * _q}
        p_long = (_eg - _cpi) * _q
        sin_t, cos_t2 = math.sin(math.radians(inc)), math.cos(
            math.radians(inc))
        for caso, pL, pR in (("transversal_90", p_trans["L"],
                              p_trans["R"]),
                             ("longitudinal_0", p_long, p_long)):
            cargas_W = {}
            for nid in sup_ids:
                x = nos[nid][0]
                area = trib[nid] * esp
                if abs(x) < 1e-9:
                    p = (pL + pR) / 2.0  # cumeeira: media das aguas
                    cargas_W[nid] = (0.0, -p * area)
                elif x < 0:
                    p = pL  # agua esquerda: normal (-sin, cos)
                    cargas_W[nid] = (p * area * sin_t, -p * area * cos_t2)
                else:
                    p = pR  # agua direita: normal (+sin, cos)
                    cargas_W[nid] = (-p * area * sin_t, -p * area * cos_t2)
            an_W = analisa_trelica(nos, barras, cargas_W,
                                   beiral_L, beiral_R)
            W_tot = sum(f[1] for f in cargas_W.values())
            casos_W[caso] = dict(an_W, p_agua_L=round(pL, 4),
                                 p_agua_R=round(pR, 4),
                                 W_tot_kN=round(W_tot, 3))

    # verificacao barra a barra: o PAR (gravidade, uplift).
    trav_inf = bool(spec["contraventamento_banzo_inf"])
    ver_barras = []
    reprovadas = []
    construtivas = []  # 9.2.1 e 9.3, por grupo (uma vez cada)
    d_pino = float(spec["ligacao"]["d_mm"])
    for bar in barras:
        n1, n2, grupo = bar
        L = comp[bar]
        Nk_g = analise_G["esforcos_Nk"][bar]
        Nk_q = analise_Q["esforcos_Nk"][bar]
        Nd_grav = GF * (Nk_g + Nk_q)
        r_grav, c_grav = _checa_barra_axial(
            n1, n2, grupo, L, Nd_grav, secoes[grupo], res, prop,
            d_pino, trav_inf, vao)
        construtivas.extend(c for c in c_grav
                            if c not in construtivas)
        # uplift: um Nd por caso de vento; governa o pior modulo.
        Nd_up, caso_up, r_up = None, None, None
        if casos_W:
            cands = {}
            for caso, an_W in casos_W.items():
                Nk_w = an_W["esforcos_Nk"][bar]
                cands[caso] = (G_FAV * Nk_g + GAMA_VENTO * Nk_w, Nk_w)
            caso_up = max(cands, key=lambda c: abs(cands[c][0]))
            Nd_up, Nk_w_up = cands[caso_up]
            r_up, c_up = _checa_barra_axial(
                n1, n2, grupo, L, Nd_up, secoes[grupo], res, prop,
                d_pino, trav_inf, vao)
            construtivas.extend(c for c in c_up
                                if c not in construtivas)
        r = dict(r_grav, Nk_kN=round(Nk_g + Nk_q, 2),
                 Nk_G_kN=round(Nk_g, 2), Nk_Q_kN=round(Nk_q, 2),
                 Nd_kN=round(Nd_grav, 2), Nd_grav_kN=round(Nd_grav, 2),
                 Nd_uplift_kN=(None if Nd_up is None
                               else round(Nd_up, 2)),
                 uplift_caso=caso_up)
        ok_bar = bool(r_grav["OK"] and (r_up is None or r_up["OK"]))
        r = dict(r, OK=ok_bar,
                 util_grav=r_grav.get("util"),
                 util_uplift=(None if r_up is None
                              else r_up.get("util")))
        ver_barras.append(r)
        if not r_grav["OK"]:
            reprovadas.append("%s-%s (%s): util %.2f" %
                             (n1, n2, grupo, r_grav.get("util", 9.9)))
        if r_up is not None and not r_up["OK"]:
            reprovadas.append("%s-%s (%s) [uplift %s]: util %.2f" %
                             (n1, n2, grupo, caso_up,
                              r_up.get("util", 9.9)))

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
    # terca sob momento invertido (G71): sob succao quem comprime e' a
    # borda INFERIOR - normalmente sem travamento algum -, entao o L1 da
    # borda superior deixa de valer. Sem L1 inferior declarado e com o
    # momento invertido, a terca reprova nomeando o que falta.
    terca_up = {"ativo": False, "inverte": False, "OK": True,
                "motivo": "sem vento declarado"}
    if casos_W:
        p_pior = min([casos_W[c]["p_agua_L"] for c in casos_W]
                     + [casos_W[c]["p_agua_R"] for c in casos_W])
        w_W = p_pior * painel_inc  # kN/m (negativo = para cima)
        w_d = G_FAV * g_lin + GAMA_VENTO * w_W
        terca_up = dict(terca_up, ativo=True, p_pior_kNm2=round(p_pior, 4),
                        w_W_kNm=round(w_W, 3), w_d_kNm=round(w_d, 3))
        if w_d < 0:
            Md_up = w_d * esp ** 2 / 8.0
            Vd_up = w_d * esp / 2.0
            L1_inf = spec.get("travamento_borda_inferior_m")
            if L1_inf is None:
                terca_up = dict(
                    terca_up, inverte=True, OK=False, Md_kNm=round(Md_up, 3),
                    motivo=("momento invertido (%.3f kNm) sem "
                            "travamento_borda_inferior_m declarado: a 6.5.6 "
                            "tem de ser reavaliada com o comprimento livre "
                            "da borda inferior" % Md_up))
            else:
                r_est_inf = mad.dispensa_estabilidade_lateral_656(
                    bt, ht, float(L1_inf), prop["E0m"], res["fmd"],
                    km["kmod"], rotacao_apoio_impedida=True)
                r_flex_up = mad.verifica_flexao(Md_up, Wt, res["fmd"],
                                               r_est_inf)
                r_cis_up = mad.verifica_cisalhamento(abs(Vd_up), At,
                                                    res["fv0d"])
                ok_up = bool(r_flex_up["OK"] and r_cis_up["OK"])
                terca_up = dict(
                    terca_up, inverte=True, OK=ok_up, Md_kNm=round(Md_up, 3),
                    Vd_kN=round(Vd_up, 3), L1_inf_m=float(L1_inf),
                    estabilidade_borda_inferior=r_est_inf,
                    flexao_invertida=r_flex_up,
                    cisalhamento_invertido=r_cis_up,
                    motivo=(None if ok_up else
                            "; ".join(m for m in [
                                r_flex_up.get("motivo"),
                                (None if r_cis_up["OK"] else
                                 "cisalhamento excedido")]
                                if m)))
        else:
            terca_up = dict(terca_up,
                            motivo="sem inversao (w_d >= 0: o peso segura)")
    terca = {"OK": bool(r_flex["OK"] and r_cis["OK"] and r_els["OK"]
                         and r_apoio_terca["OK"] and r921_terca["OK"]
                         and terca_up["OK"]),
             "dimensoes_9_2_1": r921_terca,
             "estabilidade_lateral": r_estab,
             "Md_kNm": round(Md, 3), "Vd_kN": round(Vd, 3),
              "flexao": r_flex, "cisalhamento": r_cis, "els": r_els,
              "apoio": r_apoio_terca, "w_g_kNm": round(g_lin, 3),
              "w_q_kNm": round(q_lin, 3), "uplift": terca_up}

    # ligacoes: apoio (reacao max) + no interno critico (max |N|).
    # O sistema e' DECLARADO: 'chapa_aco' (7.3, default compativel) ou
    # 'madeira_madeira' (7.2, Tab.18/19 + Tab.16). A chapa continua
    # disponivel - nada muda nela.
    lig = spec["ligacao"]
    sistema = lig.get("sistema") or (
        "chapa_aco" if lig.get("config_73") is not None
        else "madeira_madeira")
    d_mm = float(lig["d_mm"])
    fe_apoio = mad.embutimento_fek(d_mm, prop["rhok"], conifera,
                                   True, 0.0)
    fe_no = mad.embutimento_fek(d_mm, prop["rhok"], conifera, True,
                                float(inc))
    R_apoio_kN = max(abs(analise["RyL"]), abs(analise["RyR"]))

    def _demanda_barra(r):
        vals = [abs(r["Nd_grav_kN"])]
        if r["Nd_uplift_kN"] is not None:
            vals.append(abs(r["Nd_uplift_kN"]))
        return max(vals)

    bar_crit = max(ver_barras, key=_demanda_barra)
    sec_c = secoes[bar_crit["grupo"]]
    if sistema == "chapa_aco":
        base_lig = {"t_chapa_mm": float(lig["t_chapa_mm"]),
                    "tipo_pino": lig["tipo_pino"], "d_mm": d_mm,
                    "fu_MPa": float(lig["fu_MPa"]),
                    "n_pinos": int(lig["n_pinos"]),
                    "espacamentos": lig["espacamentos"],
                    "alpha_graus": 0.0,
                    "t_madeira_mm": float(secoes["banzo_inf"]["b"])
                    * 1000.0,
                    "penetracao_mm": float(secoes["banzo_inf"]["b"])
                    * 1000.0,
                    "kmod1": km["kmod1"], "kmod2": km["kmod2"]}
        cfg_apoio = dict(
            base_lig, config_73=lig["config_73"],
            t1_mm=float(secoes["banzo_inf"]["h"]) * 1000.0,
            t2_mm=float(secoes["banzo_inf"]["h"]) * 1000.0,
            fe1_Nmm2=fe_apoio["fe_k_Nmm2"],
            fe2_Nmm2=fe_apoio["fe_k_Nmm2"],
            n_planos=2 if "dupla" in lig["config_73"] else 1)
        r_lig_apoio = mad.verifica_ligacao(GF * R_apoio_kN, cfg_apoio)
        cfg_no = dict(
            base_lig, config_73=lig["config_73"],
            t1_mm=float(sec_c["h"]) * 1000.0,
            t2_mm=float(sec_c["h"]) * 1000.0,
            fe1_Nmm2=fe_no["fe_k_Nmm2"],
            fe2_Nmm2=fe_no["fe_k_Nmm2"],
            alpha_graus=float(inc),
            t_madeira_mm=float(sec_c["b"]) * 1000.0,
            penetracao_mm=float(sec_c["b"]) * 1000.0,
            n_planos=2 if "dupla" in lig["config_73"] else 1)
        r_lig_no = mad.verifica_ligacao(_demanda_barra(bar_crit),
                                        cfg_no)
    else:
        base_mm = {"tipo_pino": lig["tipo_pino"], "d_mm": d_mm,
                   "d0_mm": float(lig["d0_mm"]),
                   "conifera": conifera,
                   "fu_MPa": float(lig["fu_MPa"]),
                   "n_pinos": int(lig["n_pinos"]),
                   "n_cortes": int(lig["n_cortes"]),
                   "espacamentos": lig["espacamentos"],
                   "alpha_graus": 0.0,
                   "t_madeira_mm": float(secoes["banzo_inf"]["b"])
                   * 1000.0,
                   "penetracao_mm": float(secoes["banzo_inf"]["b"])
                   * 1000.0,
                   "kmod1": km["kmod1"], "kmod2": km["kmod2"]}
        cfg_apoio = dict(
            base_mm,
            t1_mm=float(secoes["banzo_inf"]["h"]) * 1000.0,
            t2_mm=float(secoes["banzo_inf"]["h"]) * 1000.0,
            fe1_Nmm2=fe_apoio["fe_k_Nmm2"],
            fe2_Nmm2=fe_apoio["fe_k_Nmm2"])
        r_lig_apoio = mad.verifica_ligacao_madeira_madeira(
            GF * R_apoio_kN, cfg_apoio)
        cfg_no = dict(
            base_mm,
            t1_mm=float(sec_c["h"]) * 1000.0,
            t2_mm=float(sec_c["h"]) * 1000.0,
            fe1_Nmm2=fe_no["fe_k_Nmm2"],
            fe2_Nmm2=fe_no["fe_k_Nmm2"],
            alpha_graus=float(inc),
            t_madeira_mm=float(sec_c["b"]) * 1000.0,
            penetracao_mm=float(sec_c["b"]) * 1000.0)
        r_lig_no = mad.verifica_ligacao_madeira_madeira(
            _demanda_barra(bar_crit), cfg_no)
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
                "sistema": sistema, "apoio": r_lig_apoio,
                "no_critico": r_lig_no,
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

    # ancoragem no apoio (G71): sob succao a reacao pode trocar de sinal -
    # e ai quem trabalha e' a ancoragem, nao o embutimento por compressao.
    # "A gravidade segura" nao e' verificacao: com arrancamento e sem peca
    # declarada, o telhado reprova nomeando a peca que falta.
    arranc_L = arranc_R = 0.0
    arr_caso = None
    if casos_W:
        for caso, an_W in casos_W.items():
            for lado, Ry_g in (("L", analise_G["RyL"]),
                               ("R", analise_G["RyR"])):
                Ry_w = an_W["RyL"] if lado == "L" else an_W["RyR"]
                Rd = G_FAV * Ry_g + GAMA_VENTO * Ry_w
                arr = max(0.0, -Rd)
                if lado == "L" and arr >= arranc_L:
                    arranc_L, arr_caso = arr, caso
                if lado == "R" and arr >= arranc_R:
                    arranc_R, arr_caso = arr, caso
    arranc_max = max(arranc_L, arranc_R)
    if not casos_W:
        ancoragem = {"OK": True, "aplicavel": False,
                     "motivo": "sem vento declarado: sem caso de alivio"}
    elif arranc_max <= 1e-9:
        ancoragem = {"OK": True, "aplicavel": True,
                     "arrancamento_L_kN": round(arranc_L, 3),
                     "arrancamento_R_kN": round(arranc_R, 3),
                     "motivo": "sem arrancamento (reacao segue p/ baixo)"}
    elif spec.get("ancoragem") is None:
        ancoragem = {"OK": False, "aplicavel": True,
                     "arrancamento_L_kN": round(arranc_L, 3),
                     "arrancamento_R_kN": round(arranc_R, 3),
                     "caso": arr_caso,
                     "motivo": ("arrancamento de %.2f kN no apoio sem "
                                "ancoragem declarada: declare ancoragem "
                                "(tipo, resistencia_arrancamento_kN, origem)"
                                % arranc_max)}
    else:
        cap = float(spec["ancoragem"]["resistencia_arrancamento_kN"])
        util = arranc_max / cap if cap > 0 else float("inf")
        ancoragem = {"OK": bool(util <= 1.0), "aplicavel": True,
                     "tipo": spec["ancoragem"]["tipo"],
                     "origem": spec["ancoragem"]["origem"],
                     "arrancamento_L_kN": round(arranc_L, 3),
                     "arrancamento_R_kN": round(arranc_R, 3),
                     "caso": arr_caso,
                     "resistencia_kN": cap, "util": round(util, 3),
                     "motivo": (None if util <= 1.0 else
                                "arrancamento %.2f kN acima de %.2f kN "
                                "(%s)" % (arranc_max, cap,
                                          spec["ancoragem"]["tipo"]))}

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
               "apoio": spec["apoio"],
               # G71: a parcela de succao realimenta a casa com o caso de
               # alivio - a parede e a fundacao precisam saber que ele
               # existe (chaves novas; as gravitacionais seguem intactas).
               "vento_ativo": bool(casos_W),
               "W_total_W_por_caso_kN": (
                   {c: round(casos_W[c]["W_tot_kN"] * n_tesouras, 2)
                    for c in casos_W} if casos_W else {}),
               "arrancamento_por_tesoura_kN": {
                   "L_kN": round(arranc_L, 2),
                   "R_kN": round(arranc_R, 2)},
               "arrancamento_total_kN": round(
                   (arranc_L + arranc_R) * n_tesouras, 2)}

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
        "vento": {"OK": True,
                  "ativo": bool(casos_W),
                  "q_kNm2": (vento_info["q_kNm2"] if vento_info else None),
                  "cpe": (vento_info["cpe"] if vento_info else None),
                  "cpi": (vento_info["cpi"] if vento_info else None)},
        "ancoragem_uplift": {"OK": ancoragem["OK"],
                             "motivo": ancoragem.get("motivo")},
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
        "vento_ativo": bool(casos_W), "vento": vento_info,
        "casos_W": casos_W, "ancoragem": ancoragem,
        "combinacoes": {
            "gravidade": "1,4.(G+Q) (NBR 8681, permanente desfavoravel)",
            "uplift": ("0,9.G+1,4.W por caso de vento (NBR 8681 5.1.3.1 "
                       "conjunto favoravel; 5.1.4.2: Q favoravel = 0; "
                       "Tab.4: vento 1,4; G_FAV 0,9 = extremo estrito "
                       "declarado ante o 1,0 da Tab.1/Tab.2 p.14)")
            if casos_W else None},
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
        # G71: a succao/uplift sai de not_available (a capacidade existe
        # quando o vento e' declarado; sem vento a cadeia segue
        # gravitacional por declaracao). O Cap. 9 da 6123 e +2 aguas
        # seguem fora, nomeados com motivo em motivos_escopo().
        "vento_succao_uplift": "implemented",
        "combinacao_permanente_favoravel": "implemented",
        "ancoragem_uplift": "implemented",
        "terca_borda_inferior_656": "implemented",
        "vento_dinamico_cap9_6123": "not_available",
        "vento_mais_de_2_aguas": "not_available",
        # G72: o telhado entra no BIM (IfcMember/IfcBeam via
        # bim_telhado_madeira, federado + clash) - a ilha de entrega fecha.
        "bim_ifc": "implemented",
    })
    return base


def motivos_escopo():
    """Motivo e endereco de cada fora do lote deste modulo."""
    base = dict(mad.motivos_escopo())
    base["vento_succao_uplift"] = (
        "sem spec['vento'] declarado a cadeia e' gravitacional por "
        "declaracao (compativel G66); com vento, cpe Tab.5 + cpi "
        "declarado + 0,9.G+1,4.W")
    base["vento_dinamico_cap9_6123"] = (
        "efeitos dinamicos do vento (Cap. 9 da NBR 6123) fora do lote: "
        "casa terrea rigida, metodo estatico")
    base["vento_mais_de_2_aguas"] = (
        "vento em telhado de mais de duas aguas fora do lote: Tab.5 "
        "cobre duas aguas; multiplos sao Tab.7/7.3 do galpao")
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
          "  TERCAS: %s ; LIGACOES %s (apoio + no critico %s): %s ; "
          "APOIO: %s" % (
              "ATENDE" if r["gates"]["tercas"]["OK"] else "REPROVA",
              r["ligacoes"].get("sistema", "chapa_aco"),
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
          "contraflecha e contraventamento longitudinal fora do lote.]"
          if not r.get("vento_ativo") else
          "  [VENTO G71: q=%.3f kN/m2 cpe(EF,GH)=%s cpi=%.2f (%s); "
          "uplift %s; arrancamento L/R %.2f/%.2f kN por tesoura; "
          "ancoragem: %s]"
          % (r["vento"]["q_kNm2"], r["vento"]["cpe"]["alfa90"],
             r["vento"]["cpi"], r["vento"]["cpi_origem"],
             r["descida"]["W_total_W_por_caso_kN"],
             r["descida"]["arrancamento_por_tesoura_kN"]["L_kN"],
             r["descida"]["arrancamento_por_tesoura_kN"]["R_kN"],
             ("ATENDE" if r["gates"]["ancoragem_uplift"]["OK"]
              else "REPROVA")),
          ]
    if r["telha_perfil"].get("ilustrativo"):
        L.append("  [A CONFIRMAR: Wef/Ief do perfil '%s' sao ilustrativos; "
                 "o PESO (%.3f kN/m2) e' declarado e e' o que carrega a "
                 "tesoura]" % (r["telha_perfil"].get("tipo"),
                                r["telha_peso_kNm2"]))
    return "\n".join(L)
