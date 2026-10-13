# ============================================================================
# vento_nbr6123.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Calcula a acao do vento pela ABNT NBR 6123:2023 (tabelas conferidas no D224;
# as da edicao de 1988 tem os mesmos valores com outra numeracao).
#   Calcula: fator de rugosidade S2 (Tabela 1), velocidade caracteristica Vk,
#            pressao dinamica q = 0,613*Vk^2, coeficientes de forma externos Cpe
#            (paredes Tabela 6, telhado Tabela 7) e coeficiente de pressao interna
#            Cpi (item 6.3.2.1-c, portao como abertura dominante), e a pressao
#            liquida (Cpe - Cpi)*q por superficie.
# NAO analisa a estrutura - so fornece as pressoes de vento.
# ============================================================================
"""Wind loads per ABNT NBR 6123/1988 for the galpao transverse frame.

Coefficients are the ACTUAL table values (Tabela 1, 4, 5 and item 6.2), read from
the standard, with clause references. Transparent and auditable. The zone/alpha
mapping and the dominant-opening area ratio are flagged for engineer confirmation.
Outputs in Portuguese. Computes only; pending engineer review. Units: m, kN.

Building: a=20 (length), b=10 (span/width), h=6 (eave). h/b=0.6 ; a/b=2.
Transverse frame = wind perpendicular to the ridge (hits the long 20 m walls).
"""

from __future__ import annotations


# Defaults de sitio (do gate). configurar() troca; compute() usa quando o arg e None.
_CFG_DEFAULT = {"v0": 40.0, "cat": "II", "classe": "B", "s1": 1.0, "s3": 0.95,
                "z": 6.5, "theta": 5.71}
_CFG = dict(_CFG_DEFAULT)


def reset():
    """Zera o estado de sitio para o default (evita vazamento entre projetos)."""
    _CFG.clear(); _CFG.update(_CFG_DEFAULT)


def configurar(v0=None, cat=None, classe=None, s1=None, s3=None, z=None, theta=None):
    """Define os parametros de sitio/vento (do Gate 5). Chamar antes de compute()."""
    for k, v in (("v0", v0), ("cat", cat), ("classe", classe), ("s1", s1),
                 ("s3", s3), ("z", z), ("theta", theta)):
        if v is not None:
            _CFG[k] = v


def s2_factor(cat, classe, z):
    """NBR 6123 Tabela 1 (parametros meteorologicos) -> S2 = b*Fr*(z/10)^p.
    Fr = fator de rajada da categoria II por classe (A=1,00; B=0,98; C=0,95),
    usado para todas as categorias. b e p por categoria/classe, conferidos
    integralmente contra a Tabela 1 da NBR 6123/1988 (pag. 8 do PDF)."""
    Fr = {"A": 1.00, "B": 0.98, "C": 0.95}[classe]
    # (b, p) por (categoria, classe) - Tabela 1 da NBR 6123/1988 (verbatim)
    bp = {
        ("I", "A"): (1.10, 0.06), ("I", "B"): (1.11, 0.065), ("I", "C"): (1.12, 0.07),
        ("II", "A"): (1.00, 0.085), ("II", "B"): (1.00, 0.09), ("II", "C"): (1.00, 0.10),
        ("III", "A"): (0.94, 0.10), ("III", "B"): (0.94, 0.105), ("III", "C"): (0.93, 0.115),
        ("IV", "A"): (0.86, 0.12), ("IV", "B"): (0.85, 0.125), ("IV", "C"): (0.84, 0.135),
        ("V", "A"): (0.74, 0.15), ("V", "B"): (0.73, 0.16), ("V", "C"): (0.71, 0.175),
    }
    if (cat, classe) not in bp:
        raise ValueError(f"categoria/classe de vento invalida: {cat}/{classe} "
                         "(NBR 6123 Tabela 1: categorias I-V, classes A/B/C)")
    b, p = bp[(cat, classe)]
    return b, Fr, p, b * Fr * (z / 10.0) ** p


def _interp(x, x0, x1, y0, y1):
    return y0 + (x - x0) / (x1 - x0) * (y1 - y0)


# ---------------------------------------------------------------------------
# COEFICIENTES DE FORMA EXTERNOS - NBR 6123:2023, Tabelas 6 e 7, lidas na imagem
# da pagina no MCP_Fontes em 2026-10-13 (D224). Sao as Tabelas 4 e 5 da edicao
# de 1988, com os mesmos valores nas celulas que o motor ja usava.
#
# Ate' o D224 o motor usava SEMPRE o bloco 1/2 < h/b <= 3/2 com 2 <= a/b <= 4,
# qualquer que fosse a proporcao do galpao. A escolha agora e' pela geometria.
# Sem geometria (h_b / a_b = None) vale o bloco antigo: so' para o chamador que
# nao a tem (memorial avulso, selftest).
#
# Tabela 6 (paredes), por bloco de h/b e de a/b:
#   alpha = 0  (vento na face menor b): A1B1, A2B2, C (barlavento), D (sotavento)
#   alpha = 90 (vento na face maior a): A (barlavento), B (sotavento), C1D1, C2D2
_CE_PAREDE = {
    "<=1/2":   {"1-3/2": (-0.8, -0.5, +0.7, -0.4, +0.7, -0.4, -0.8, -0.4),
                "2-4":   (-0.8, -0.4, +0.7, -0.3, +0.7, -0.5, -0.9, -0.5)},
    "1/2-3/2": {"1-3/2": (-0.9, -0.5, +0.7, -0.5, +0.7, -0.5, -0.9, -0.5),
                "2-4":   (-0.9, -0.4, +0.7, -0.3, +0.7, -0.6, -0.9, -0.5)},
    "3/2-6":   {"1-3/2": (-1.0, -0.6, +0.8, -0.6, +0.8, -0.6, -1.0, -0.6),
                "2-4":   (-1.0, -0.5, +0.8, -0.3, +0.8, -0.6, -1.0, -0.6)},
}
# Tabela 7 (telhado de duas aguas), por bloco de h/b:
#   theta -> (EFI, GHJ) para alpha = 90 e (EG, FH) para alpha = 0
_CE_TELHADO = {
    "<=1/2": [(0, (-0.8, -0.4, -0.8, -0.4)), (5, (-0.9, -0.4, -0.8, -0.4)),
              (10, (-1.2, -0.4, -0.8, -0.6)), (15, (-1.0, -0.4, -0.8, -0.6)),
              (20, (-0.4, -0.4, -0.7, -0.6)), (30, (0.0, -0.4, -0.7, -0.6)),
              (45, (+0.3, -0.5, -0.7, -0.6)), (60, (+0.7, -0.6, -0.7, -0.6))],
    "1/2-3/2": [(0, (-0.8, -0.6, -1.0, -0.6)), (5, (-0.9, -0.6, -0.9, -0.6)),
                (10, (-1.1, -0.6, -0.8, -0.6)), (15, (-1.0, -0.6, -0.8, -0.6)),
                (20, (-0.7, -0.5, -0.8, -0.6)), (30, (-0.2, -0.5, -0.8, -0.8)),
                (45, (+0.2, -0.5, -0.8, -0.8)), (60, (+0.6, -0.5, -0.8, -0.8))],
    "3/2-6": [(0, (-0.8, -0.6, -0.9, -0.7)), (5, (-0.8, -0.6, -0.8, -0.8)),
              (10, (-0.8, -0.6, -0.8, -0.8)), (15, (-0.8, -0.6, -0.8, -0.8)),
              (20, (-0.8, -0.6, -0.8, -0.8)), (30, (-1.0, -0.5, -0.8, -0.7)),
              (40, (-0.2, -0.5, -0.8, -0.7)), (50, (+0.2, -0.5, -0.8, -0.7)),
              (60, (+0.5, -0.5, -0.8, -0.7))],
}
_BLOCO_ANTIGO = "1/2-3/2"


def _bloco_de(h_b):
    if h_b is None:
        return _BLOCO_ANTIGO
    if h_b <= 0.5:
        return "<=1/2"
    if h_b <= 1.5:
        return "1/2-3/2"
    if h_b <= 6.0:
        return "3/2-6"
    raise ValueError(f"h/b={h_b:.2f} fora das Tabelas 6 e 7 (limite 6)")


def _linha_parede(h_b, a_b):
    """Linha da Tabela 6 para (h/b, a/b); entre 3/2 e 2 interpola (Nota 2)."""
    bloco = _CE_PAREDE[_bloco_de(h_b)]
    if a_b is None:
        return bloco["2-4"]
    if a_b < 1.0:
        raise ValueError(f"a/b={a_b:.2f}: a e' a MAIOR dimensao em planta (a/b >= 1)")
    # acima de a/b = 4 a Tabela 6 nao tem linha: vale a ultima (2 <= a/b <= 4) e
    # o memorial avisa (relatorio_pt)
    if a_b <= 1.5:
        return bloco["1-3/2"]
    if a_b >= 2.0:
        return bloco["2-4"]
    return tuple(_interp(a_b, 1.5, 2.0, y0, y1)
                 for y0, y1 in zip(bloco["1-3/2"], bloco["2-4"]))


def _linha_telhado(theta_graus, h_b):
    """Linha da Tabela 7 para theta, interpolada entre os angulos tabelados."""
    linhas = _CE_TELHADO[_bloco_de(h_b)]
    if not linhas[0][0] <= theta_graus <= linhas[-1][0]:
        raise ValueError(f"theta={theta_graus:.1f} graus fora da Tabela 7 (0 a 60)")
    for (t0, v0), (t1, v1) in zip(linhas, linhas[1:]):
        if t0 <= theta_graus <= t1:
            return tuple(_interp(theta_graus, t0, t1, y0, y1) for y0, y1 in zip(v0, v1))
    return linhas[-1][1]


def cpe_paredes(h_b=None, a_b=None):
    """NBR 6123:2023 Tabela 6, paredes, vento a 90 graus (na face maior): A =
    barlavento, B = sotavento. h_b = altura do beiral / menor dimensao em planta;
    a_b = maior / menor dimensao em planta."""
    ln = _linha_parede(h_b, a_b)
    return {"parede_barlavento": round(ln[4], 3), "parede_sotavento": round(ln[5], 3)}


def cpe_telhado(theta_graus=5.71, h_b=None):
    """NBR 6123:2023 Tabela 7, telhado de duas aguas, vento PERPENDICULAR a
    cumeeira (alpha = 90): EFI = agua de barlavento, GHJ = agua de sotavento.
    (As colunas EG/FH sao do vento a 0 grau e nao se misturam com as paredes de
    alpha = 90.)"""
    ln = _linha_telhado(theta_graus, h_b)
    return {"cobertura_barlavento": round(ln[0], 2), "cobertura_sotavento": round(ln[1], 2)}


def cpe_telhado_longitudinal(theta_graus=5.71, h_b=None):
    """NBR 6123:2023 Tabela 7, vento PARALELO a cumeeira (alpha = 0): o telhado se
    divide ao longo do comprimento nas zonas EG (barlavento) e FH (sotavento); as
    duas aguas de um mesmo portico ficam na mesma zona -> carga simetrica. EG e'
    a zona critica do uplift simetrico."""
    ln = _linha_telhado(theta_graus, h_b)
    return {"cobertura_long_EG": round(ln[2], 2), "cobertura_long_FH": round(ln[3], 2)}


def proporcoes(larg_b, alt_h, comp_a):
    """(h/b, a/b) das Tabelas 6 e 7 a partir do vao, da altura do beiral e do
    comprimento: b e' a MENOR dimensao em planta e a, a maior."""
    menor, maior = min(larg_b, comp_a), max(larg_b, comp_a)
    return alt_h / menor, maior / menor


def cpi_cases(abertura_dominante="portao_oitao"):
    """Cpi (NBR 6123 item 6.2.5) conforme a abertura dominante do galpao. Delega
    a cpi_por_abertura para que o MEMORIAL de vento use a MESMA premissa da analise
    do portico (antes fixava sempre portao +0,80/-0,60, ignorando a escolha do
    usuario -> memorial e analise divergiam quando o galpao era 'vedada')."""
    return cpi_por_abertura(abertura_dominante)


def cpe_telhado_1agua(theta_graus=5.71):
    """NBR 6123 Tabela 6 - telhado de UMA AGUA (shed), h/b < 2. Coef. de FORMA Ce
    (para o portico principal) por metade do telhado: H (metade BAIXA) e L (metade
    ALTA), nas duas direcoes de vento perpendicular a cumeeira:
      'vento90'  = vento sobe (atinge a fachada BAIXA): H barlavento, L sotavento;
      'vento_90' = vento desce (atinge a fachada ALTA): L barlavento, H sotavento.
    Todos os valores sao de SUCCAO (negativos) -> uplift. Interpola theta em
    5/10/15 graus (valores lidos da Tabela 6). Barlavento sempre -0,9 a -1,0."""
    pts = [5.0, 10.0, 15.0]
    H90 = [-1.0, -1.0, -0.9]; L90 = [-0.5, -0.5, -0.5]      # vento 90 (sobe)
    Hm90 = [-0.5, -0.4, -0.3]; Lm90 = [-1.0, -1.0, -1.0]    # vento -90 (desce)

    def _ip(ys):
        t = min(max(theta_graus, pts[0]), pts[-1])
        for k in range(len(pts) - 1):
            if t <= pts[k + 1] + 1e-9:
                f = (t - pts[k]) / (pts[k + 1] - pts[k])
                return round(ys[k] + (ys[k + 1] - ys[k]) * f, 3)
        return ys[-1]
    return {"vento90": {"H": _ip(H90), "L": _ip(L90)},
            "vento_90": {"H": _ip(Hm90), "L": _ip(Lm90)}}


def cpi_por_abertura(abertura_dominante="portao_oitao"):
    """Cpi (NBR 6123 item 6.2.5) conforme a configuracao de abertura. Retorna os
    DOIS casos usados no envelope de vento (mesma chave de cpi_cases):
      - 'portao_oitao' / 'portao_lateral' -> ABERTURA DOMINANTE (6.2.5-c):
        +0,80 (portao a barlavento) / -0,60 (portao a sotavento).
      - 'vedada' -> SEM abertura dominante, permeabilidade baixa/uniforme
        (6.2.5-a/b): +0,20 / -0,30 (conservador; A CONFIRMAR com a permeabilidade
        real do galpao - reboco, esquadrias, telha com costura).
    Antes o Cpi era SEMPRE o de portao (+0,80/-0,60), ignorando a escolha do
    usuario -> galpao vedado ficava com pressao interna de portao (superestimava
    o uplift). Ver wizard 'abertura_dominante'."""
    a = (abertura_dominante or "portao_oitao").strip().lower()
    if a in ("vedada", "vedado", "sem", "sem_abertura"):
        return {"portao_barlavento": +0.20, "portao_sotavento": -0.30}
    return {"portao_barlavento": +0.80, "portao_sotavento": -0.60}


# ============================================================================
# Cpe MEDIO / LOCAL (alta succao de borda e canto) - Tabelas 4 e 5, coluna
# "cpe medio" (zonas hachuradas). NAO governa o portico (que usa o Cpe global
# acima); governa a TELHA, a TERCA e seus FIXADORES nas faixas de borda/canto,
# onde a succao e muito maior. Valores lidos VERBATIM do PDF (pags. 14-15).
# ============================================================================

# Tabela 4 (paredes) - coluna "cpe medio", faixa de barlavento das paredes
# paralelas ao vento, largura = min(0,2b ; h) [nota c]. Chave: (bloco h/b, bloco a/b).
_CPE_MEDIO_PAREDE = {
    ("<=1/2", "1-3"): -0.9, ("<=1/2", "2-4"): -1.0,
    ("1/2-3/2", "1-3"): -1.1, ("1/2-3/2", "2-4"): -1.1,
    ("3/2-6", "1-3"): -1.2, ("3/2-6", "2-4"): -1.2,
}

# Tabela 5 (telhado 2 aguas) - coluna "cpe medio", 4 zonas hachuradas por
# (bloco h/b, theta). None = zona ausente naquele angulo (celula em branco).
# Faixa: y = min(h ; 0,15b) ; dimensao da zona = min(max(b/3 ; a/4) ; 2h).
_CPE_MEDIO_COB = {
    "<=1/2": [
        (0,  (-2.0, -2.0, -2.0, None)), (5,  (-1.4, -1.2, -1.2, -1.0)),
        (10, (-1.4, -1.4, None, -1.2)), (15, (-1.4, -1.2, None, -1.2)),
        (20, (-1.0, None, None, -1.2)), (30, (-0.8, None, None, -1.1)),
        (45, (None, None, None, -1.1)), (60, (None, None, None, -1.1)),
    ],
    "1/2-3/2": [
        (0,  (-2.0, -2.0, -2.0, None)), (5,  (-2.0, -2.0, -1.5, -1.0)),
        (10, (-2.0, -2.0, -1.5, -1.2)), (15, (-1.8, -1.5, -1.5, -1.2)),
        (20, (-1.5, -1.5, -1.5, -1.0)), (30, (-1.0, None, None, -1.0)),
    ],
    "3/2-6": [
        (0,  (-2.0, -2.0, -2.0, None)), (5,  (-2.0, -2.0, -1.5, -1.0)),
        (10, (-2.0, -2.0, -1.5, -1.2)), (15, (-1.8, -1.8, -1.5, -1.2)),
        (20, (-1.5, -1.5, -1.5, -1.2)), (30, (-1.5, None, None, None)),
        (40, (-1.0, None, None, None)),
    ],
}


def _bloco_hb(h, b):
    hb = h / b
    if hb <= 0.5:
        return "<=1/2", hb
    if hb <= 1.5:
        return "1/2-3/2", hb
    if hb <= 6.0:
        return "3/2-6", hb
    raise ValueError(f"h/b={hb:.2f} fora da Tabela 4/5 (limite 6)")


def _bloco_ab(a, b):
    ab = a / b
    return ("1-3" if ab <= 1.5 else "2-4"), ab   # nota a: interpola 3/2..2


def cpe_local_parede(a=20.0, b=10.0, h=6.0):
    """cpe medio das paredes (Tabela 4), zona de alta succao de borda a barlavento
    das paredes paralelas ao vento. Largura da faixa = min(0,2b ; h) [nota c].
    Governa o fixador da telha/terca de fechamento lateral no canto de barlavento."""
    bloco_h, hb = _bloco_hb(h, b)
    bloco_a, ab = _bloco_ab(a, b)
    cpe = _CPE_MEDIO_PAREDE[(bloco_h, bloco_a)]
    faixa = min(0.2 * b, h)
    return {"cpe_medio": cpe, "faixa_m": round(faixa, 2),
            "hb": round(hb, 3), "ab": round(ab, 3),
            "bloco_hb": bloco_h, "bloco_ab": bloco_a}


def cpe_local_cobertura(theta_graus=5.71, b=10.0, h=6.0, a=20.0):
    """cpe medio do telhado (Tabela 5), envoltoria das 4 zonas hachuradas de
    borda/canto, interpolada em theta. Governa o fixador da telha e a ligacao
    terca-portico nas bordas/cantos da cobertura. Retorna a envoltoria (mais
    negativa) e a geometria da zona (faixa y e dimensao da zona)."""
    bloco_h, hb = _bloco_hb(h, b)
    linhas = _CPE_MEDIO_COB[bloco_h]
    th = max(linhas[0][0], min(theta_graus, linhas[-1][0]))   # clamp ao dominio
    # localiza o par de linhas que envolve th
    lo = hi = linhas[0]
    for row in linhas:
        if row[0] <= th:
            lo = row
        if row[0] >= th:
            hi = row
            break
    zonas = []
    for j in range(4):
        y0, y1 = lo[1][j], hi[1][j]
        if y0 is None and y1 is None:
            zonas.append(None)
        elif y0 is None:
            zonas.append(y1)
        elif y1 is None:
            zonas.append(y0)
        elif lo[0] == hi[0]:
            zonas.append(y0)
        else:
            zonas.append(round(_interp(th, lo[0], hi[0], y0, y1), 2))
    envoltoria = min(v for v in zonas if v is not None)
    y = min(h, 0.15 * b)
    dim_zona = min(max(b / 3.0, a / 4.0), 2.0 * h)
    return {"cpe_medio_envoltoria": round(envoltoria, 2),
            "zonas": zonas, "theta": theta_graus, "bloco_hb": bloco_h,
            "faixa_y_m": round(y, 2), "dim_zona_m": round(dim_zona, 2),
            "lanternim_cpe_medio": -2.0}


def cpe_telhado_multiplo(n_vaos, theta_graus=5.71):
    """Cpe para telhados MULTIPLOS simetricos de tramos IGUAIS (NBR 6123 Tab.7).
    Retorna uma lista de dicts, um por tramo (vao). Cada dict tem:
      {"barlavento": float, "sotavento": float}  (face E e D de cada vao)
    Para vento a 0° (perpendicular as cumeeiras): o 1o tramo recebe mais carga,
    os intermediarios e o ultimo recebem menos (sombreamento aerodinamico).
    Para vento a 90° (paralelo) os valores sao constantes ao longo do telhado:
      faixa b1 (h): -0,8 ; b2 (h): -0,6 ; b3: -0,2 (Tab.7, α=90°).
    Interpolacao linear entre 5° e 10°. h/b e a/b definem as faixas (nao os
    coeficientes nominais, que dependem so de θ)."""
    th = max(5.0, min(theta_graus, 10.0))
    f = (th - 5.0) / (10.0 - 5.0)
    # Tramo 1 (barlavento): face a (barlavento), face b (sotavento)
    a = -0.9 + f * (-1.1 + 0.9)     # -0.9 (5°) a -1.1 (10°)
    b = -0.6                         # constante
    # Tramo 2 (1o intermediario): faces c (barl) e d (sot)
    c = -0.4; d = -0.3              # constante
    # Demais intermediarios: m (barl) e n (sot)
    m = -0.3; n = -0.3
    # Ultimo tramo (sotavento): x (barl) e z (sot)
    x = -0.3
    z = -0.3 + f * (-0.4 + 0.3)     # -0.3 (5°) a -0.4 (10°)
    tramos = []
    if n_vaos == 1:
        tramos.append({"barlavento": a, "sotavento": b if th < 7.5 else z})
    elif n_vaos == 2:
        tramos.append({"barlavento": a, "sotavento": b})
        tramos.append({"barlavento": x, "sotavento": z})
    else:
        tramos.append({"barlavento": a, "sotavento": b})
        for _ in range(n_vaos - 2):
            tramos.append({"barlavento": m, "sotavento": n})
        tramos.append({"barlavento": x, "sotavento": z})
    # Vento a 90°: valores por faixa longitudinal (nao por tramo)
    # Retorna tambem os valores para α=90°
    return tramos


def sucao_local_fixacao(q_kN_m2, cpe_medio, cpi=+0.80):
    """Succao liquida LOCAL para dimensionar telha/terca e FIXADORES na borda/canto.
    p = (cpe_medio - cpi)*q. Usa o Cpi mais desfavoravel (portao a barlavento,
    +0,8, empurra de dentro e soma na succao externa). kN/m2 (negativo = arranque)."""
    return round((cpe_medio - cpi) * q_kN_m2, 3)


def compute(v0=None, cat=None, classe=None, s1=None, s3=None, z=None, theta=None,
            larg_b=10.0, alt_h=6.0, comp_a=20.0, abertura_dominante="portao_oitao"):
    v0 = _CFG["v0"] if v0 is None else v0
    cat = _CFG["cat"] if cat is None else cat
    classe = _CFG["classe"] if classe is None else classe
    s1 = _CFG["s1"] if s1 is None else s1
    s3 = _CFG["s3"] if s3 is None else s3
    z = _CFG["z"] if z is None else z
    theta = _CFG["theta"] if theta is None else theta
    b, Fr, p, s2 = s2_factor(cat, classe, z)     # b = coef. da Tabela 1 (NAO a largura)
    vk = v0 * s1 * s2 * s3
    q = 0.613 * vk ** 2 / 1000.0     # 0,613*Vk^2 [N/m2] -> /1000 -> kN/m2
    h_b, a_b = proporcoes(larg_b, alt_h, comp_a)
    cpe = {**cpe_paredes(h_b, a_b), **cpe_telhado(theta, h_b)}
    cpi = cpi_cases(abertura_dominante)
    net = {}
    for cname, cpiv in cpi.items():
        net[cname] = {s: round(cpe[s] - cpiv, 2) for s in cpe}
    # Cpe medio / local (borda-canto) para telha/terca/fixador
    loc_cob = cpe_local_cobertura(theta, larg_b, alt_h, comp_a)
    loc_par = cpe_local_parede(comp_a, larg_b, alt_h)
    cpi_arr = max(cpi.values())     # Cpi mais desfavoravel para arranque
    local = {"cobertura": loc_cob, "parede": loc_par, "cpi_arranque": cpi_arr,
             "p_local_cob_kN_m2": sucao_local_fixacao(q, loc_cob["cpe_medio_envoltoria"], cpi_arr),
             "p_local_par_kN_m2": sucao_local_fixacao(q, loc_par["cpe_medio"], cpi_arr)}
    return {"v0": v0, "cat": cat, "classe": classe, "s1": s1, "s2": round(s2, 3),
            "s3": s3, "b": b, "Fr": Fr, "p": p, "z": z, "theta": theta,
            "vk": round(vk, 2), "q_kN_m2": round(q, 3),
            "abertura_dominante": abertura_dominante, "h_b": h_b, "a_b": a_b,
            "cpe": cpe, "cpi_cases": cpi, "net": net, "local": local}


def grupo_s3(s3):
    """Grupo da Tabela 4 da NBR 6123:2023 a que o valor de S3 corresponde."""
    grupos = {1.11: "grupo 1: socorro e seguranca apos tempestade",
              1.06: "grupo 2: aglomeracao de pessoas",
              1.00: "grupo 3: residencia, hotel, comercio, industria",
              0.95: "grupo 4: SEM ocupacao humana (deposito, silo) e sem pessoas no entorno",
              0.83: "grupo 5: temporaria nao reutilizavel"}
    for valor, nome in grupos.items():
        if abs(s3 - valor) < 0.005:
            return nome
    return "valor fora dos minimos da Tabela 4"


def relatorio_pt(r):
    L = []
    L.append("VENTO (ABNT NBR 6123:2023)")
    L.append(f"  V0 = {r['v0']:.0f} m/s ; Categoria {r['cat']} ; Classe {r['classe']}")
    L.append(f"  S1 = {r['s1']:.2f} (topografia plana) ; S3 = {r['s3']:.2f} "
             f"({grupo_s3(r['s3'])})")
    L.append(f"  S2 = {r['b']:.2f}*{r['Fr']:.2f}*({r['z']:.1f}/10)^{r['p']:.3f} = {r['s2']:.3f}")
    L.append(f"  Vk = {r['vk']:.2f} m/s ; q = 0,613*Vk^2 = {r['q_kN_m2']:.3f} kN/m2")
    L.append(f"  Telhado theta = {r['theta']:.2f} graus ; h/b = {r['h_b']:.2f} ; "
             f"a/b = {r['a_b']:.2f}")
    if r["a_b"] > 4.0:
        L.append("  AVISO: a/b > 4 esta' FORA da Tabela 6; usada a linha 2 <= a/b <= 4.")
    L.append("  Cpe (MESMA incidencia alpha=90: paredes Tabela 6 A/B ; telhado Tabela 7 EFI/GHJ):")
    for s, v in r["cpe"].items():
        L.append(f"    {s.replace('_',' ')}: {v:+.2f}")
    _ad = str(r.get("abertura_dominante", "portao_oitao")).lower()
    _lbl = ("VEDADA (sem abertura dominante, item 6.3.2.1-a/b)"
            if _ad.startswith("veda") else "PORTAO como abertura dominante, item 6.3.2.1-c")
    L.append("  Cpi (%s):" % _lbl)
    for k, v in r["cpi_cases"].items():
        L.append(f"    {k.replace('_',' ')}: {v:+.2f}")
    L.append("  Cp liquido = Cpe - Cpi e pressao (kN/m2):")
    for caso, d in r["net"].items():
        L.append(f"    caso {caso.replace('_',' ')}:")
        for s, v in d.items():
            L.append(f"      {s.replace('_',' ')}: {v:+.2f}  ({v*r['q_kN_m2']:+.3f} kN/m2)")
    loc = r.get("local")
    if loc:
        c = loc["cobertura"]; pa = loc["parede"]
        L.append("  Cpe MEDIO / LOCAL (borda-canto, Tabelas 6 e 7, col. 'cpe medio') - TELHA/TERCA/FIXADOR:")
        L.append(f"    cobertura: envoltoria {c['cpe_medio_envoltoria']:+.2f} "
                 f"(zonas {c['zonas']}); faixa y={c['faixa_y_m']:.2f} m ; "
                 f"zona={c['dim_zona_m']:.2f} m ; lanternim {c['lanternim_cpe_medio']:+.2f}")
        L.append(f"    parede:    cpe medio {pa['cpe_medio']:+.2f} "
                 f"(h/b={pa['hb']:.2f}, a/b={pa['ab']:.2f}); faixa={pa['faixa_m']:.2f} m")
        L.append(f"    succao liquida (Cpi={loc['cpi_arranque']:+.2f} p/ arranque): "
                 f"cobertura {loc['p_local_cob_kN_m2']:+.3f} kN/m2 ; "
                 f"parede {loc['p_local_par_kN_m2']:+.3f} kN/m2")
        L.append("    -> dimensionar o fixador da telha e a ligacao terca-portico de BORDA/CANTO")
        L.append("       com esta succao local (bem maior que a global do portico).")
    L.append("  [A CONFIRMAR: classe (20 m), grupo do S3 (Tabela 4), e a razao de areas")
    L.append("   das aberturas para o Cpi do portao (6.3.2.1-c): com o portao em face")
    L.append("   paralela ao vento a norma manda o Ce do local da abertura (Tabela 6);")
    L.append("   o -0,60 adotado e' um valor intermediario.]")
    return "\n".join(L)


# ============================================================================
# VENTO LONGITUDINAL (incidencia alpha=0, atinge o OITAO / empena de 10 m)
# Fornece: (a) Cpe das paredes na incidencia 0 (Tabela 4) para o MONTANTE DE
# OITAO; (b) a FORCA DE ARRASTO global Fa = Ca*q*Ae (item 6.3), que os
# contraventamentos longitudinais e as escoras de beiral resistem. Ca vem da
# Figura 4 (grafico, vento de baixa turbulencia) - NAO e tabela: entra como
# parametro marcado "A CONFIRMAR (ler Figura 4)". O metodo Fa=Ca*q*Ae e exato.
# ============================================================================


def cpe_paredes_longitudinal(h_b=None, a_b=None):
    """NBR 6123:2023 Tabela 6, vento a 0 grau (no oitao): C = empena de
    barlavento, D = empena de sotavento, A1B1 / A2B2 = paredes laterais. Sem
    geometria vale o caso antigo do motor (h/b <= 1/2, a/b = 2)."""
    ln = _linha_parede(0.5 if h_b is None else h_b, 2.0 if a_b is None else a_b)
    return {"oitao_barlavento": round(ln[2], 3), "oitao_sotavento": round(ln[3], 3),
            "parede_lateral_A": round(ln[0], 3), "parede_lateral_B": round(ln[1], 3)}


def forca_arrasto(q, area_frontal, ca):
    """Item 6.3: Fa = Ca * q * Ae (kN). Ae = area frontal (empena) projetada."""
    return ca * q * area_frontal


def forca_atrito(q, l1, l2, h, cf_telhado=0.04, cf_parede=0.04):
    """FORCA DE ATRITO do vento (NBR 6123 item 6.4.2), na direcao do vento,
    sobre as superficies PARALELAS ao fluxo (telhado + 2 paredes longitudinais).
    So se aplica a edificacao COMPRIDA: l2/h > 4 OU l2/l1 > 4 (senao F'=0).
      l1 = dimensao horizontal PERPENDICULAR ao vento (largura/vao do galpao)
      l2 = dimensao PARALELA ao vento (comprimento do galpao)
      h  = altura (parede/beiral)
    Formula (6.4.2), descontando a 1a faixa (escoamento descolado):
      se h <= l1:  F' = Cf'*q*l1*(l2-4h)  +  Cf'*q*2h*(l2-4h)
      se h  > l1:  F' = Cf'*q*l1*(l2-4l1) +  Cf'*q*2h*(l2-4l1)
      1o termo = telhado (area l1 x Lef) ; 2o termo = 2 paredes (2h x Lef).
    Cf' (6.4.3): 0,01 liso ; 0,02 nervura arredondada ; 0,04 nervura retangular
    (telha trapezoidal transversal). Default 0,04 = mais conservador (A CONFIRMAR
    o perfil da telha/tapamento e sua orientacao vs. o vento longitudinal).
    Retorna dict com F_telhado, F_parede, F_at (kN) e o Lef adotado."""
    aplica = (l2 / h > 4.0) or (l2 / l1 > 4.0) if (h > 0 and l1 > 0) else False
    if not aplica:
        return {"aplica": False, "Lef": 0.0, "F_telhado": 0.0, "F_parede": 0.0,
                "F_at": 0.0, "l1": l1, "l2": l2, "h": h}
    Lef = max(l2 - 4.0 * h, 0.0) if h <= l1 else max(l2 - 4.0 * l1, 0.0)
    F_telhado = cf_telhado * q * l1 * Lef          # telhado (superficie superior)
    F_parede = cf_parede * q * 2.0 * h * Lef       # 2 paredes longitudinais
    return {"aplica": True, "Lef": Lef, "F_telhado": F_telhado, "F_parede": F_parede,
            "F_at": F_telhado + F_parede, "l1": l1, "l2": l2, "h": h,
            "cf_telhado": cf_telhado, "cf_parede": cf_parede}


def compute_longitudinal(v0=None, cat=None, classe=None, s1=None, s3=None, z=None,
                         b=10.0, eave=6.0, ridge=6.5, ca=1.2, comp=None,
                         cf_atrito=0.04):
    """Vento longitudinal (alpha=0). q reaproveitado (independe da direcao).
    b = largura do oitao ; area frontal = retangulo + triangulo da empena.
    ca = coeficiente de arrasto (Figura 4, baixa turbulencia) - A CONFIRMAR.
    comp = comprimento do galpao (m) -> ativa a FORCA DE ATRITO (6.4) no telhado
    e nas 2 paredes longitudinais, que se SOMA ao arrasto no contraventamento
    longitudinal. cf_atrito = Cf' (6.4.3; 0,04 = telha trapezoidal, conservador)."""
    v0 = _CFG["v0"] if v0 is None else v0
    cat = _CFG["cat"] if cat is None else cat
    classe = _CFG["classe"] if classe is None else classe
    s1 = _CFG["s1"] if s1 is None else s1
    s3 = _CFG["s3"] if s3 is None else s3
    z = _CFG["z"] if z is None else z
    b_, Fr, p, s2 = s2_factor(cat, classe, z)
    vk = v0 * s1 * s2 * s3
    q = 0.613 * vk ** 2 / 1000.0     # 0,613*Vk^2 [N/m2] -> /1000 -> kN/m2
    area = b * eave + b * (ridge - eave) / 2.0     # empena: retangulo + triangulo
    cpe = (cpe_paredes_longitudinal(*proporcoes(b, eave, comp)) if comp
           else cpe_paredes_longitudinal())
    cpi = cpi_cases()
    net = {c: {s: round(cpe[s] - civ, 2) for s in cpe} for c, civ in cpi.items()}
    Fa = forca_arrasto(q, area, ca)
    # Forca de ATRITO (6.4): l1=vao (perp. ao vento long.), l2=comprimento, h=beiral.
    atr = (forca_atrito(q, l1=b, l2=comp, h=eave, cf_telhado=cf_atrito,
                        cf_parede=cf_atrito) if comp else
           {"aplica": False, "F_at": 0.0, "F_telhado": 0.0, "F_parede": 0.0, "Lef": 0.0})
    F_at = atr["F_at"]
    Ftot = Fa + F_at                               # o contraventamento resiste a soma
    return {"v0": v0, "vk": round(vk, 2), "q_kN_m2": round(q, 3), "b": b,
            "eave": eave, "ridge": ridge, "area_frontal": round(area, 2),
            "ca": ca, "Fa_kN": round(Fa, 1), "atrito": atr,
            "F_atrito_kN": round(F_at, 1), "Ftot_long_kN": round(Ftot, 1),
            "Fa_por_lado_kN": round(Ftot / 2.0, 1),   # arrasto + atrito, por painel
            "Fa_arrasto_por_lado_kN": round(Fa / 2.0, 1),
            "cpe": cpe, "cpi_cases": cpi, "net": net}


def relatorio_longitudinal_pt(r):
    L = ["VENTO LONGITUDINAL (ABNT NBR 6123:2023 - incidencia alpha=0, oitao)",
         f"  Vk = {r['vk']:.2f} m/s ; q = {r['q_kN_m2']:.3f} kN/m2",
         f"  Area frontal (empena {r['b']:.0f} m) = {r['area_frontal']:.2f} m2",
         f"  Cpe paredes (Tabela 6, alpha=0):"]
    for s, v in r["cpe"].items():
        L.append(f"    {s.replace('_',' ')}: {v:+.2f}")
    L.append("  Cp liquido (Cpe - Cpi) por caso de portao:")
    for caso, d in r["net"].items():
        L.append(f"    {caso.replace('_',' ')}: " +
                 " ; ".join(f"{s.split('_')[-1]}={v:+.2f}" for s, v in d.items()))
    L += [f"  Forca de arrasto Fa = Ca*q*Ae = {r['ca']:.2f}*{r['q_kN_m2']:.3f}*"
          f"{r['area_frontal']:.2f} = {r['Fa_kN']:.1f} kN"]
    atr = r.get("atrito", {})
    if atr.get("aplica"):
        L += [f"  Forca de atrito F' (6.4, l2/h>4 ou l2/l1>4): Lef={atr['Lef']:.1f} m",
              f"    telhado = {atr['F_telhado']:.1f} kN ; 2 paredes = {atr['F_parede']:.1f} kN"
              f"  ->  F' = {r['F_atrito_kN']:.1f} kN (Cf'={atr.get('cf_telhado',0):.2f})",
              f"  TOTAL longitudinal = Fa + F' = {r['Ftot_long_kN']:.1f} kN"]
    else:
        L += ["  Forca de atrito F' (6.4): NAO se aplica (l2/h<=4 e l2/l1<=4) ou comprimento nao informado"]
    L += [f"  Por lado (2 paineis de contraventamento) = {r['Fa_por_lado_kN']:.1f} kN",
          "  [A CONFIRMAR: Ca da Figura 4 (baixa turbulencia); area frontal da empena;",
          "   Cf' conforme perfil/orientacao da telha (6.4.3); fracao por escora.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # Tabela 4 - parede, bloco 1/2<h/b<=3/2, 2<=a/b<=4 (galpao 20x10, h=6): cpe medio -1,1
    p = cpe_local_parede(20.0, 10.0, 6.0)
    assert p["cpe_medio"] == -1.1, p
    assert p["bloco_hb"] == "1/2-3/2" and p["bloco_ab"] == "2-4", p
    assert abs(p["faixa_m"] - 2.0) < 1e-9, p     # min(0,2*10 ; 6) = 2,0
    # Tabela 5 - cobertura, mesmo bloco, theta 5,71 -> zona 1 governa -2,0
    c = cpe_local_cobertura(5.71, 10.0, 6.0, 20.0)
    assert c["cpe_medio_envoltoria"] == -2.0, c
    assert abs(c["faixa_y_m"] - 1.5) < 1e-9, c   # min(6 ; 0,15*10)=1,5
    assert abs(c["dim_zona_m"] - 5.0) < 1e-9, c  # min(max(10/3;20/4)=5 ; 2*6=12)=5
    # interpolacao em theta: bloco <=1/2, theta=7,5 -> zona1 entre -1,4 e -1,4 = -1,4
    c2 = cpe_local_cobertura(7.5, 20.0, 6.0, 40.0)   # h/b=0,3
    assert c2["bloco_hb"] == "<=1/2", c2
    assert c2["zonas"][0] == -1.4, c2
    # succao local de arranque: (cpe_medio - cpi)*q, cpi=+0,8
    assert sucao_local_fixacao(1.0, -2.0, +0.80) == -2.8
    # compute integra local sem quebrar
    r = compute()
    assert "local" in r and r["local"]["cobertura"]["cpe_medio_envoltoria"] == -2.0
    # FORCA DE ATRITO (6.4.2): galpao comprido 20x60, h=6 -> l2/h=10>4 aplica.
    # h(6) <= l1(20) -> Lef = l2-4h = 60-24 = 36. F_telh=Cf'*q*l1*Lef ;
    # F_par=Cf'*q*2h*Lef. Total = Cf'*q*Lef*(l1+2h).
    qv = 0.613 * (compute_longitudinal(comp=60.0)["vk"]) ** 2 / 1000.0
    fa = forca_atrito(qv, l1=20.0, l2=60.0, h=6.0, cf_telhado=0.04, cf_parede=0.04)
    assert fa["aplica"] and abs(fa["Lef"] - 36.0) < 1e-9
    assert abs(fa["F_telhado"] - 0.04 * qv * 20.0 * 36.0) < 1e-9
    assert abs(fa["F_parede"] - 0.04 * qv * 2 * 6.0 * 36.0) < 1e-9
    assert abs(fa["F_at"] - 0.04 * qv * 36.0 * (20.0 + 12.0)) < 1e-9
    # galpao curto (l2/h<=4 e l2/l1<=4): NAO aplica -> F'=0
    fc = forca_atrito(qv, l1=20.0, l2=20.0, h=6.0)
    assert not fc["aplica"] and fc["F_at"] == 0.0
    # h > l1 (torre alta e estreita): desconta 4*l1
    ft = forca_atrito(qv, l1=4.0, l2=30.0, h=10.0)
    assert abs(ft["Lef"] - (30.0 - 4.0 * 4.0)) < 1e-9
    # compute_longitudinal com comp: Fa_por_lado inclui o atrito (Ftot/2)
    rl = compute_longitudinal(b=20.0, eave=6.0, ridge=7.0, comp=60.0)
    assert rl["F_atrito_kN"] > 0 and abs(rl["Ftot_long_kN"] - (rl["Fa_kN"] + rl["F_atrito_kN"])) < 0.11
    assert abs(rl["Fa_por_lado_kN"] - rl["Ftot_long_kN"] / 2.0) < 0.06
    # sem comp: atrito nao entra (compat. retro) -> Fa_por_lado = Fa/2
    rl0 = compute_longitudinal(b=20.0, eave=6.0, ridge=7.0)
    assert rl0["F_atrito_kN"] == 0.0 and abs(rl0["Fa_por_lado_kN"] - rl0["Fa_kN"] / 2.0) < 0.06
    print("vento self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(compute()))
        print()
        print(relatorio_longitudinal_pt(compute_longitudinal()))
