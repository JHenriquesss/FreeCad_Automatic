# ============================================================================
# galpao_portico.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Cria e analisa o PORTICO 2D do galpao de aco pelo metodo da rigidez direta
# (frame2d). Pode ser de 1 ou MULTIPLOS vaos (geminado). Para N vaos, cria
# N+1 colunas e N cumeeiras; todas as colunas na mesma altura EAVE, as cumeeiras
# em RIDGE. Os carregamentos sao aplicados por funcoes de caso.
#
# METODO extraido das normas (pesquisa/aco/) - nunca de memoria.
# CONCEITUAL - pendente revisao e ART do engenheiro responsavel.
# Unidades: m, kN ; fck/fyk em kN/m2 ; E=200 GPa.
# ============================================================================
"""Cria e analisa o portico 2D. Parametrico para 1 ou N vaos."""

from __future__ import annotations

import math
import re
import frame2d as f2d

# ---- parametros globais (modificados por configurar) -------------------------
SPANS = [10.0]                     # largura de cada vao [m]
EAVE  = 6.0                         # altura do beiral (coluna) [m]
RIDGE = 6.5                         # altura da cumeeira [m]
BAY   = 5.0                         # espacamento entre porticos [m]
THETA = math.atan((RIDGE - EAVE) / (SPANS[0] / 2.0))  # inclinacao (1a agua)
COS   = math.cos(THETA)
SIN   = math.sin(THETA)
NSEG  = 8                            # numero de sub-elementos por membro
E     = 200e6                         # modulo de elasticidade [kPa] (200 GPa)
N_VAOS = 1                           # numero de vaos (deduzido de SPANS)

# Secoes (preenchidas por configurar)
A_COL = 53.8e-4                      # area da secao da coluna [m2] (HEA200)
I_COL = 3692e-8                      # I da coluna [m4]
A_RAF = 45.3e-4                      # area da secao da viga [m2]  (HEA180)
I_RAF = 2510e-8                      # I da viga [m4]

# Secoes POR COLUNA (multi-vao com perfis distintos). None = todas as colunas
# usam A_COL/I_COL (default, retrocompativel). Lista de dicts {"A","I"} com um
# item por coluna (indice 0..N_VAOS). Preenchida por redimensionamento._aplica
# para que a analise 2D e o B2 (P-Delta) enxerguem a rigidez REAL de cada coluna
# (nao so o B1 local). Bug 8.21 (residuo). So o ramo prismatico a honra.
SEC_COLS_PORTICO = None

BASE_FIXED = False                   # base engastada? (True=engaste, False=rotula)

# Cargas (preenchidas por configurar)
G_ROOF = 0.27                        # carga perm. na cobertura [kN/m2 de telhado]
RAFTER_SELF = 0.35                   # peso proprio da viga [kN/m]
Q_ROOF = 0.25                        # sobrecarga [kN/m2 de projecao horizontal]
ABERTURA_DOMINANTE = "portao_oitao"  # config de abertura p/ Cpi (NBR 6123 6.2.5);
                                     # 'vedada' usa Cpi pequeno em vez do de portao.
AGUAS = 2                            # nº de aguas do telhado: 2 (simetrico) ou 1
                                     # (shed/uma agua: colunas de alturas diferentes,
                                     # 1 rafter, sem cumeeira). Shed so p/ 1 vao.
W_WALL_COL = 0.0                     # peso do fechamento de parede como UDL vertical
                                     # [kN/m] em CADA coluna externa (paredes
                                     # longitudinais descarregam nos beirais de
                                     # extremidade). Aplicado como UDL axial (mesmo
                                     # caminho/convencao da carga de cobertura) - NAO
                                     # usar carga nodal (frame2d tem sinal de reacao
                                     # diferente p/ nodal x UDL: mistura corrompe o G).

# Cargas opcionais (None = ausente)
PONTE = None                         # dict de reacao da ponte rolante
SISMO = None                         # dict {E: kN} forca sismica total no portico


def reset():
    """Reseta estado mutavel entre projetos."""
    global PONTE, SISMO, BASE_FIXED, SEC_COLS_PORTICO, W_WALL_COL, ABERTURA_DOMINANTE, AGUAS, TAPERED
    PONTE = None; SISMO = None; BASE_FIXED = False; SEC_COLS_PORTICO = None
    W_WALL_COL = 0.0
    ABERTURA_DOMINANTE = "portao_oitao"
    AGUAS = 2
    TAPERED = None


# Alma variavel (tapered): None = rafter prismatico (default). dict = misula
# {h_joelho, h_cumeeira, bf, tw, tf} (m) -> rafter com secao variando por segmento
# (secao_tapered de alma_variavel). Fundo no joelho, raso na cumeeira.
TAPERED = None
_UNSET = object()      # sentinela: tapered=None RESETA para prismatico; omitido mantem


def configurar(span=None, spans=None, eave=None, ridge=None, bay=None,
               base_fixed=None,
               A_col=None, I_col=None, A_raf=None, I_raf=None,
               G_roof=None, rafter_self=None, Q_roof=None,
               ponte=None, sismo=None, tapered=_UNSET, w_wall_col=None,
               abertura_dominante=None, aguas=None):
    """Configura a geometria/secoes/cargas do portico. Aceita tanto 'span'
    (1 vao, retrocompativel) quanto 'spans' (lista p/ N vaos)."""
    global SPANS, N_VAOS, EAVE, RIDGE, BAY, THETA, COS, SIN
    global A_COL, I_COL, A_RAF, I_RAF
    global BASE_FIXED, G_ROOF, RAFTER_SELF, Q_ROOF, PONTE, SISMO, TAPERED, W_WALL_COL
    global ABERTURA_DOMINANTE, AGUAS
    if tapered is not _UNSET:
        TAPERED = dict(tapered) if tapered else None
    if spans is not None:
        SPANS = list(spans)
    elif span is not None:
        SPANS = [span]
    N_VAOS = len(SPANS)
    if eave is not None:
        EAVE = eave
    if ridge is not None:
        RIDGE = ridge
    if bay is not None:
        BAY = bay
    THETA = math.atan((RIDGE - EAVE) / (SPANS[0] / 2.0))
    COS = math.cos(THETA); SIN = math.sin(THETA)
    if A_col is not None: A_COL = A_col
    if I_col is not None: I_COL = I_col
    if A_raf is not None: A_RAF = A_raf
    if I_raf is not None: I_RAF = I_raf
    if base_fixed is not None: BASE_FIXED = base_fixed
    if G_roof is not None: G_ROOF = G_roof
    if rafter_self is not None: RAFTER_SELF = rafter_self
    if Q_roof is not None: Q_ROOF = Q_roof
    if ponte is not None: PONTE = ponte if ponte else None
    if sismo is not None: SISMO = sismo if sismo else None
    if w_wall_col is not None: W_WALL_COL = w_wall_col
    if abertura_dominante is not None: ABERTURA_DOMINANTE = abertura_dominante
    if aguas is not None: AGUAS = int(aguas)


def _chain(fr, na, nb, Asec, Isec, nseg):
    """Cria nseg elementos entre nos na e nb. Retorna lista de indices.
    O no intermediario do segmento i serve como no inicial do segmento i+1."""
    xa, ya = fr.nodes[na]; xb, yb = fr.nodes[nb]
    elems = []; prev = na
    for i in range(nseg):
        t1 = (i + 1) / nseg
        xj = xa + (xb - xa) * t1; yj = ya + (yb - ya) * t1
        nxt = fr.add_node(xj, yj) if i < nseg - 1 else nb
        e = fr.add_element(prev, nxt, E, Asec, Isec)
        elems.append(e)
        prev = nxt
    return elems


def _chain_var(fr, na, nb, secoes):
    """Como _chain, mas cada segmento recebe a SUA secao (A,I) da lista `secoes`
    (len == nseg). Usado no rafter de alma variavel: I varia ao longo do vao."""
    import alma_variavel as av  # noqa: F401 (import p/ manter dependencia explicita)
    nseg = len(secoes)
    xa, ya = fr.nodes[na]; xb, yb = fr.nodes[nb]
    elems = []; prev = na
    for i in range(nseg):
        t1 = (i + 1) / nseg
        xj = xa + (xb - xa) * t1; yj = ya + (yb - ya) * t1
        nxt = fr.add_node(xj, yj) if i < nseg - 1 else nb
        e = fr.add_element(prev, nxt, E, secoes[i]["A_m2"], secoes[i]["I_m4"])
        elems.append(e)
        prev = nxt
    return elems


def _secoes_rafter(sentido):
    """Secoes por segmento do rafter tapered (NSEG). sentido='eave2ridge' (fundo
    no inicio) ou 'ridge2eave' (raso no inicio). Usa alma_variavel.secao_tapered."""
    import alma_variavel as av
    t = TAPERED
    if sentido == "eave2ridge":
        h1, h2 = t["h_joelho"], t["h_cumeeira"]
    else:
        h1, h2 = t["h_cumeeira"], t["h_joelho"]
    return av.secao_tapered(h1, h2, t.get("bf", 0.20), t.get("tw", 0.008),
                            t.get("tf", 0.0125), nseg=NSEG)


def _coluna_tapered():
    """True se a coluna deve ser tapered (rasa na base -> funda no joelho).
    Requer TAPERED com h_col_base (m). Sem esse campo -> coluna prismatica."""
    return bool(TAPERED) and TAPERED.get("h_col_base") is not None


def _secoes_coluna():
    """Secoes por segmento da coluna tapered (NSEG), da BASE (h_col_base, rasa)
    ao JOELHO (h_joelho, funda; casa a base do rafter). Usa secao_tapered."""
    import alma_variavel as av
    t = TAPERED
    return av.secao_tapered(t["h_col_base"], t["h_joelho"], t.get("bf", 0.20),
                            t.get("tw", 0.008), t.get("tf", 0.0125), nseg=NSEG)


def _posicoes():
    """Retorna (x_cols, x_ridges) com as posicoes X das colunas e cumeeiras."""
    n = len(SPANS)
    x_cols = [sum(SPANS[:i]) for i in range(n + 1)]
    x_ridges = [sum(SPANS[:i]) + SPANS[i] / 2.0 for i in range(n)]
    return x_cols, x_ridges


def _ridge_h(i):
    """Altura da cumeeira do vao i mantendo a INCLINACAO constante (a do 1o vao,
    embutida em RIDGE/THETA). Vaos IGUAIS -> = RIDGE (retrocompativel, sem mudanca
    no caminho do wizard). Vaos DESIGUAIS -> cumeeira mais ALTA no vao mais largo,
    consistente com o 3D (build_galpao mantem a inclinacao) - antes o 2D usava
    RIDGE unico e ACHATAVA os vaos maiores (wiki 07 item I)."""
    if not SPANS or SPANS[0] <= 0:
        return RIDGE
    return EAVE + (RIDGE - EAVE) * (SPANS[i] / SPANS[0])


def _sec_coluna(i):
    """(A, I) da coluna i. Usa SEC_COLS_PORTICO[i] se preenchida (multi-perfil),
    senao a secao unica A_COL/I_COL (retrocompativel). Bug 8.21."""
    sp = SEC_COLS_PORTICO
    if sp is not None and i < len(sp) and sp[i] is not None:
        s = sp[i]
        return s.get("A", A_COL), s.get("I", I_COL)
    return A_COL, I_COL


def _frame_shed():
    """Portico de UMA AGUA (shed): coluna BAIXA (x=0, z=EAVE) + coluna ALTA
    (x=SPAN, z=EAVE+slope*SPAN) + 1 rafter unico, sem cumeeira. So 1 vao,
    prismatico. Retorna (fr, ix) compativel com case_G/Q/analyse (rafts[0]=
    [rafter, []]; cols=[baixa, alta])."""
    fr = f2d.Frame2D()
    S = SPANS[0]
    slope = math.tan(THETA)                 # inclinacao (= (RIDGE-EAVE)/(SPAN/2))
    h_high = EAVE + slope * S               # topo da coluna alta
    b0 = fr.add_node(0.0, 0.0); b1 = fr.add_node(S, 0.0)
    e_low = fr.add_node(0.0, EAVE); e_high = fr.add_node(S, h_high)
    Ac0, Ic0 = _sec_coluna(0); Ac1, Ic1 = _sec_coluna(1)
    col_low = _chain(fr, b0, e_low, Ac0, Ic0, NSEG)
    col_high = _chain(fr, b1, e_high, Ac1, Ic1, NSEG)
    rafter = _chain(fr, e_low, e_high, A_RAF, I_RAF, NSEG)   # a unica agua
    for b in (b0, b1):
        fr.add_support(b, u=True, v=True, rot=BASE_FIXED)
    ix = {"nBases": [b0, b1], "nEaves": [e_low, e_high], "nRidges": [],
          "nCons": [None, None], "cols": [col_low, col_high],
          "rafts": [[rafter, []]], "n_nodes": len(fr.nodes), "shed": True,
          "nBaseL": b0, "nBaseR": b1, "nEaveL": e_low, "nEaveR": e_high,
          "nRidge": e_high, "nConsL": None, "colL": col_low, "colR": col_high,
          "rafL": rafter, "rafR": []}
    return fr, ix


def _frame():
    """Cria o modelo do portico 2D. Retorna (fr, ix). Para 1 vao, mantem
    as chaves antigas (nBaseL/R, nEaveL/R, nRidge, colL/R, rafL/R)."""
    if AGUAS == 1 and len(SPANS) == 1:
        return _frame_shed()
    fr = f2d.Frame2D()
    xc, xr = _posicoes(); n = len(SPANS)
    # --- nos ---
    bases = [fr.add_node(x, 0.0) for x in xc]          # N+1 bases
    eaves = [fr.add_node(x, EAVE) for x in xc]          # N+1 beirais
    cons  = [None] * (n + 1)                             # consoles (opcional)
    ridges = [fr.add_node(xr[i], _ridge_h(i)) for i in range(n)]  # N cumeeiras (h por vao)
    # console da ponte (so na 1a coluna por enquanto)
    if PONTE:
        cons[0] = fr.add_node(xc[0], PONTE.get("Hvr", EAVE))
    # --- elementos ---
    cols = []
    col_tap = _coluna_tapered()
    for i in range(n + 1):
        topo = cons[i] if cons[i] is not None else eaves[i]
        if col_tap:                                 # alma variavel na coluna
            # secoes base->joelho; se ha console, a parte console->beiral usa a
            # secao do topo (joelho) ja que acima do console a coluna nao afina.
            secs_col = _secoes_coluna()
            c = _chain_var(fr, bases[i], topo, secs_col)
            if cons[i] is not None:
                sj = secs_col[-1]
                c += _chain(fr, cons[i], eaves[i], sj["A_m2"], sj["I_m4"], NSEG // 2)
        else:                                       # prismatica (ref)
            Ac, Ic = _sec_coluna(i)                 # per-coluna se disponivel
            c = _chain(fr, bases[i], topo, Ac, Ic, NSEG)
            if cons[i] is not None:
                c += _chain(fr, cons[i], eaves[i], Ac, Ic, NSEG // 2)
        cols.append(c)
    rafts = []  # rafts[s] = [left_raft_elements, right_raft_elements]
    for i in range(n):
        if TAPERED:                                 # alma variavel: secao por segmento
            rl = _chain_var(fr, eaves[i], ridges[i], _secoes_rafter("eave2ridge"))
            rr = _chain_var(fr, ridges[i], eaves[i + 1], _secoes_rafter("ridge2eave"))
        else:                                       # prismatico (ref)
            rl = _chain(fr, eaves[i], ridges[i], A_RAF, I_RAF, NSEG)
            rr = _chain(fr, ridges[i], eaves[i + 1], A_RAF, I_RAF, NSEG)
        rafts.append([rl, rr])
    # --- apoios ---
    rot = BASE_FIXED
    for b in bases:
        fr.add_support(b, u=True, v=True, rot=rot)
    # --- indice ---
    ix = {"nBases": bases, "nEaves": eaves, "nRidges": ridges,
          "nCons": cons, "cols": cols, "rafts": rafts,
          "n_nodes": len(fr.nodes)}
    # retrocompatibilidade 1 vao
    if n == 1:
        ix["nBaseL"] = bases[0]; ix["nBaseR"] = bases[1]
        ix["nEaveL"] = eaves[0]; ix["nEaveR"] = eaves[1]
        ix["nRidge"] = ridges[0]
        ix["nConsL"] = cons[0]
        ix["colL"] = cols[0]; ix["colR"] = cols[1]
        ix["rafL"] = rafts[0][0]; ix["rafR"] = rafts[0][1]
    return fr, ix


def modelo_analitico():
    """Extrai o MODELO ANALITICO 2D do portico (nivel de MEMBRO, nao os NSEG
    sub-elementos) a partir do frame ja configurado (chamar apos configurar()).
    Retorna {nos, barras, apoios, unidade} - o modelo estrutural como DADOS, base
    do intercambio analitico (IFC-structural / SAF) e do modelo_neutro. Item 2:
    esse e o intercambio mais rico p/ uma ferramenta de calculo (nos+barras+
    apoios+secoes, nao so geometria). Coordenadas 2D no plano do portico (x
    transversal, y vertical), em metros."""
    fr, ix = _frame()
    bases, eaves, ridges = ix["nBases"], ix["nEaves"], ix["nRidges"]
    nos = []
    _vistos = set()

    def _no(idx, papel):
        if idx is None or idx in _vistos:
            return
        _vistos.add(idx)
        x, y = fr.nodes[idx]
        nos.append({"id": idx, "x": round(x, 4), "y": round(y, 4), "papel": papel})

    for b in bases:
        _no(b, "base")
    for e in eaves:
        _no(e, "beiral")
    for r in ridges:
        _no(r, "cumeeira")

    def _AI(elem_idx):
        el = fr.elements[elem_idx]
        return el["A"], el["I"]

    barras = []
    for i in range(len(bases)):                       # colunas: base -> beiral
        A, I = _AI(ix["cols"][i][0])
        barras.append({"no_i": bases[i], "no_j": eaves[i], "grupo": "coluna",
                       "A": A, "I": I})
    for s in range(len(ridges)):                      # rafters: beiral->cumeeira->beiral
        A, I = _AI(ix["rafts"][s][0][0])
        barras.append({"no_i": eaves[s], "no_j": ridges[s], "grupo": "rafter", "A": A, "I": I})
        A, I = _AI(ix["rafts"][s][1][0])
        barras.append({"no_i": ridges[s], "no_j": eaves[s + 1], "grupo": "rafter", "A": A, "I": I})

    apoios = []
    for b in bases:
        if b in fr.supports:
            u, v, rot = fr.supports[b]
            apoios.append({"no": b, "u": bool(u), "v": bool(v), "rot": bool(rot),
                           "tipo": "engaste" if rot else "rotula"})
    return {"nos": nos, "barras": barras, "apoios": apoios, "unidade": "m",
            "n_porticos": None}


def _run(load_fn):
    """Constroi o frame, aplica o caso de carga, resolve."""
    fr, ix = _frame()
    load_fn(fr, ix)
    d, mf = fr.solve()
    R = fr.reactions()
    return d, mf, ix, fr


def _carrega_udl(fr, ix, wy):
    """Aplica UDL gravitacional (wy) em todas as vigas do portico."""
    for i in range(N_VAOS):
        for elems in ix["rafts"][i]:
            for e in elems:
                fr.add_member_udl(e, wy=wy)


def _carrega_udl_spans(fr, ix, wy, spans):
    """Aplica UDL gravitacional (wy) so nas vigas dos VAOS em `spans` (indices).
    Usado no pattern loading (carga em xadrez, NBR 8681) para maximizar o momento
    de desequilibrio nas colunas internas de porticos multi-vao."""
    for i in spans:
        for elems in ix["rafts"][i]:
            for e in elems:
                fr.add_member_udl(e, wy=wy)


def case_G(fr, ix):
    """Carga permanente na cobertura (G) + peso da parede de fechamento."""
    _carrega_udl(fr, ix, wy=-(G_ROOF * BAY + RAFTER_SELF))
    # Peso da parede de fechamento (telha/painel/alvenaria) como UDL vertical AXIAL
    # nas DUAS colunas externas (as paredes longitudinais descarregam nos pilares de
    # extremidade). UDL (nao nodal) para casar a convencao de sinal da reacao com a
    # carga de cobertura - assim o esforco chega correto na coluna E na fundacao.
    if W_WALL_COL:
        cols = ix["cols"]
        for c in (cols[0], cols[-1]):
            for e in c:
                fr.add_member_udl(e, wy=-W_WALL_COL)


def case_Q(fr, ix):
    """Sobrecarga (Q)."""
    _carrega_udl(fr, ix, wy=-(Q_ROOF * BAY * COS))


def case_ponte(fr, ix):
    """Reacao da ponte rolante: carga maxima na 1a coluna (console),
    carga minima na 2a coluna (beiral, sem console). Ponte atua no 1o vao."""
    if not PONTE:
        return
    # Coluna 1 (mais carregada): console com R_vert + M_exc + H_transv
    if ix["nCons"][0] is not None:
        fr.add_nodal_load(ix["nCons"][0], Fx=PONTE.get("H_transv", 0.0),
                          Fy=-PONTE.get("R_vert", 0.0),
                          M=PONTE.get("M_exc", 0.0))
    # Coluna 2 (menos carregada): R_vert_min no beiral
    if len(ix["nEaves"]) > 1:
        fr.add_nodal_load(ix["nEaves"][1], Fy=-PONTE.get("R_vert_min", PONTE.get("R_vert", 0.0)))


def case_sismo(fr, ix):
    """Forca sismica equivalente nos beirais."""
    if not SISMO:
        return
    E_h = SISMO["E"]
    n_eave = len(ix["nEaves"])
    for ne in ix["nEaves"]:
        fr.add_nodal_load(ne, Fx=E_h / n_eave)


def _wind_multi(cpi_key, fr=None, ix=None):
    """Aplica vento para portico de N vaos. Usa NBR 6123 Tabela 7 para
    telhados multiplos simetricos."""
    import vento_nbr6123 as vi
    xc, _ = _posicoes()
    n = N_VAOS
    wr = vi.compute(larg_b=SPANS[0], alt_h=EAVE,
                    comp_a=max(xc) - min(xc), theta=math.degrees(THETA))
    cpi = vi.cpi_por_abertura(ABERTURA_DOMINANTE)[cpi_key]
    q = wr["q_kN_m2"]
    # Coeficientes Cpe por tramo (Tabela 7)
    tramos = vi.cpe_telhado_multiplo(n, math.degrees(THETA))
    def apply(fr, ix):
        F_wall = q * EAVE / 2.0
        cpe_barl = 0.7; cpe_sotav = -0.5
        F_bar = (cpe_barl - cpi) * F_wall
        F_sot = (cpe_sotav - cpi) * F_wall
        fr.add_nodal_load(ix["nEaves"][0], Fx=F_bar)
        fr.add_nodal_load(ix["nEaves"][-1], Fx=F_sot)
        for i in range(n):
            tc = tramos[i]
            # Vento na face barlavento do tramo i (lado esquerdo de cada agua)
            p_b = (tc["barlavento"] - cpi) * q
            # Vento na face sotavento do tramo i (lado direito de cada agua)
            p_s = (tc["sotavento"] - cpi) * q
            # Aplica nas duas vigas do tramo: E (barl->cumeeira) e D (cumeeira->sot)
            for e in ix["rafts"][i][0]:
                fr.add_member_udl(e, wx=-p_b * BAY * SIN, wy=-p_b * BAY * COS)
            for e in ix["rafts"][i][1]:
                fr.add_member_udl(e, wx=p_s * BAY * SIN, wy=-p_s * BAY * COS)
    if fr is not None and ix is not None:
        apply(fr, ix)
        return wr
    return apply, wr


def _wind_shed(cpi_key):
    """Vento no telhado de UMA AGUA (NBR 6123 Tabela 6). Pressao liquida
    (Ce - Cpi)*q por metade do rafter (H baixa, L alta) + paredes (Tabela 4).
    cpi_key W1 -> vento sobe (fachada baixa a barlavento); W2 -> vento desce."""
    import vento_nbr6123 as vi
    wr = vi.compute(larg_b=SPANS[0], alt_h=EAVE, comp_a=SPANS[0] * 2,
                    theta=math.degrees(THETA))
    q = wr["q_kN_m2"]
    cpi = vi.cpi_por_abertura(ABERTURA_DOMINANTE)[cpi_key]
    cw = vi.cpe_paredes()
    ct = vi.cpe_telhado_1agua(math.degrees(THETA))
    caso = ct["vento90"] if cpi_key == "portao_barlavento" else ct["vento_90"]

    def apply(fr, ix):
        raft = ix["rafts"][0][0]
        nlow = len(raft) // 2                      # metade BAIXA (H) x metade ALTA (L)
        for j, e in enumerate(raft):
            Ce = caso["H"] if j < nlow else caso["L"]
            p = (Ce - cpi) * q                     # succao (p<0) -> wy>0 (uplift)
            fr.add_member_udl(e, wx=-p * BAY * SIN, wy=-p * BAY * COS)
        # paredes: baixa (x=0) e alta (x=SPAN); forca horizontal liquida no beiral,
        # proporcional a altura de cada coluna.
        z_low = fr.nodes[ix["nEaves"][0]][1]; z_high = fr.nodes[ix["nEaves"][1]][1]
        fr.add_nodal_load(ix["nEaves"][0], Fx=(cw["parede_barlavento"] - cpi) * q * z_low / 2.0)
        fr.add_nodal_load(ix["nEaves"][1], Fx=(cw["parede_sotavento"] - cpi) * q * z_high / 2.0)
    return apply, wr


def _wind(cpi_key):
    """Vento para 1 vao (retrocompativel). Usa os coeficientes tabulados."""
    if AGUAS == 1 and N_VAOS == 1:
        return _wind_shed(cpi_key)
    return _wind_unico(cpi_key) if N_VAOS == 1 else _wind_multi(cpi_key)


def _wind_unico(cpi_key):
    """Vento para 1 vao (NBR 6123). Pressao LIQUIDA (Cpe - Cpi)*q por superficie:
    paredes Tabela 4, telhado Tabela 5. O telhado a baixa inclinacao e SUCCAO nas
    duas aguas -> uplift. (Corrige o modelo antigo, que aplicava q p/ BAIXO sem o
    Cpe de telhado e anulava o arrancamento - wiki 07 §2A; mesmo modelo do
    _wind_multi.)"""
    import vento_nbr6123 as vi
    wr = vi.compute(larg_b=SPANS[0], alt_h=EAVE,
                    comp_a=SPANS[0] * 2,  # comprimento aproximado
                    theta=math.degrees(THETA))
    cpi = vi.cpi_por_abertura(ABERTURA_DOMINANTE)[cpi_key]
    q = wr["q_kN_m2"]
    cw = vi.cpe_paredes()                 # Tabela 4 (barlavento +0,70 / sotavento -0,60)
    ct = vi.cpe_telhado(math.degrees(THETA))   # Tabela 5 (sucao nas duas aguas)
    def apply(fr, ix):
        # Paredes: forca horizontal liquida (cpe - cpi) concentrada no beiral.
        F_wall = q * EAVE / 2.0
        fr.add_nodal_load(ix["nEaveL"], Fx=(cw["parede_barlavento"] - cpi) * F_wall)
        fr.add_nodal_load(ix["nEaveR"], Fx=(cw["parede_sotavento"] - cpi) * F_wall)
        # Telhado: pressao liquida normal a agua, componentes (wx, wy). Sucao
        # (cpe<0) com cpi>0 -> p<0 -> wy>0 (para CIMA) = arrancamento.
        p_b = (ct["cobertura_barlavento"] - cpi) * q     # agua barlavento (rafL)
        p_s = (ct["cobertura_sotavento"] - cpi) * q      # agua sotavento (rafR)
        for e in ix["rafL"]:
            fr.add_member_udl(e, wx=-p_b * BAY * SIN, wy=-p_b * BAY * COS)
        for e in ix["rafR"]:
            fr.add_member_udl(e, wx=p_s * BAY * SIN, wy=-p_s * BAY * COS)
    return apply, wr


def _combos_elu(ponte=None, sismo=None):
    """Combinacoes ELU (NBR 8681 / 8800). Cruza cada hipotese de G+Q com
    W1 (portao barlavento) e W2 (portao sotavento). Retorna dict
    {'C1_Grav_W1': {"G":1.25,"Q":1.50,"W1":0.84}, ...}.
    Opcionais: ponte (adiciona C4/C5) e sismo (adiciona C6)."""
    base = {"G": 1.0, "Q": 1.0}
    combos = {}
    # wf = fator de combinacao ELU do vento: PRIMARIO 1,40 ; SECUNDARIO (combo de
    # gravidade, Q predomina) = gamma_f * psi0 = 1,40 * 0,60 = 0,84 (NBR 8681).
    # Gfav: G FAVORAVEL (gamma_g=1,0) com vento principal (uplift). A sobrecarga Q
    # (variavel gravitacional) NAO pode estabilizar o arrancamento -> gamma_q=0
    # (NBR 8681: acoes variaveis favoraveis nao entram na combinacao). qf=0,80 seria
    # nao-conservativo (subdimensiona chumbadores/blocos/estacas sob tracao).
    for tag, gf, qf, wf in [("grav", 1.25, 1.50, 0.6 * 1.40),
                             ("uplift", 1.00, 0.00, 1.40),
                             ("Gdesf", 1.25, 0.80, 1.40),
                             ("Gfav", 1.00, 0.00, 1.40)]:
        for wsuf, wkey in (("W1", "W1"), ("W2", "W2")):
            c = {"G": gf}
            if qf > 0: c["Q"] = qf
            c[wkey] = wf
            combos[f"C1_{tag}_{wsuf}"] = c
    if ponte:
        combos["C4_ponteW"] = {"G": 1.25, "PONTE": 1.50, "W1": 0.6 * 1.40}
        combos["C5_ventoP"] = {"G": 1.25, "W1": 1.40, "PONTE": 0.7 * 1.50}
    if sismo:
        for sgn, tag in ((1.0, "P"), (-1.0, "N")):
            combos[f"C6_sismo_Gdesf_{tag}"] = {"G": 1.20, "SISMO": sgn}
            combos[f"C6_sismo_Gfav_{tag}"] = {"G": 1.00, "SISMO": sgn}
    # PATTERN LOADING / carga em xadrez (NBR 8681): em portico multi-vao a
    # sobrecarga alternada (vaos pares x impares) maximiza o momento de deseque-
    # librio nas COLUNAS INTERNAS - carregar todos os vaos por igual o mascara.
    # Gravidade pura (G desfavoravel + Q em subconjunto de vaos), sem vento.
    # Qa = vaos de indice par ; Qb = vaos de indice impar (ver analyse()).
    if N_VAOS >= 2:
        combos["C2_xadrez_A"] = {"G": 1.25, "Qa": 1.50}
        combos["C2_xadrez_B"] = {"G": 1.25, "Qb": 1.50}
    return combos


def _grupo_MNV(mf_comb, elems):
    """Retorna (M_max, N_max, V_max) para um grupo de elementos."""
    M, N, V = 0.0, 0.0, 0.0
    for e in elems:
        fe = mf_comb[e]
        for k in (0, 3): N = max(N, abs(fe[k]))
        for k in (1, 4): V = max(V, abs(fe[k]))
        for k in (2, 5): M = max(M, abs(fe[k]))
    return M, N, V


def analyse():
    """Analisa o portico. Retorna dict com esforcos por grupo, drift, etc.
    Para N>1, 'colunas' e 'vigas' sao listas (um resultado por grupo)."""
    # --- casos base ---
    dG, mfG, ix, _ = _run(case_G)
    dQ, mfQ, _, _ = _run(case_Q)
    # casos de PATTERN LOADING (xadrez): sobrecarga so nos vaos pares (Qa) e so
    # nos impares (Qb). So faz sentido em multi-vao; alimenta os combos C2_xadrez.
    cases_pattern = {}
    if N_VAOS >= 2:
        wyQ = -(Q_ROOF * BAY * COS)
        spans_a = [i for i in range(N_VAOS) if i % 2 == 0]
        spans_b = [i for i in range(N_VAOS) if i % 2 == 1]
        dQa, mfQa, _, _ = _run(lambda f, i: _carrega_udl_spans(f, i, wyQ, spans_a))
        dQb, mfQb, _, _ = _run(lambda f, i: _carrega_udl_spans(f, i, wyQ, spans_b))
        cases_pattern = {"Qa": (dQa, mfQa), "Qb": (dQb, mfQb)}
    # vento
    def run_wind(key):
        apply_fn, wr = _wind(key)
        d, mf, _, _ = _run(lambda f, i: apply_fn(f, i))
        return d, mf, wr
    dW1, mfW1, wr1 = run_wind("portao_barlavento")
    dW2, mfW2, wr2 = run_wind("portao_sotavento")
    cases_d = {"G": dG, "Q": dQ, "W1": dW1, "W2": dW2}
    cases_mf = {"G": mfG, "Q": mfQ, "W1": mfW1, "W2": mfW2}
    for k, (dk, mfk) in cases_pattern.items():         # Qa/Qb (pattern loading)
        cases_d[k] = dk; cases_mf[k] = mfk
    wind_result = wr1  # wind data p/ relatorio (W1)
    # opcionais
    if PONTE:
        dP, mfP, _, _ = _run(case_ponte)
        cases_d["PONTE"] = dP; cases_mf["PONTE"] = mfP
    if SISMO:
        dS, mfS, _, _ = _run(case_sismo)
        cases_d["SISMO"] = dS; cases_mf["SISMO"] = mfS
    # --- combinacoes ---
    combos = _combos_elu(PONTE, SISMO)
    def combo_mf(c):
        return {e: sum(cases_mf[cs].get(e, cases_mf[cs][list(cases_mf[cs])[0]]) * fac
                       for cs, fac in c.items()
                       for _ in [()]) for e in list(cases_mf[list(cases_mf.keys())[0]].keys())}
    # Hmm, o combo acima e problematico. Vou usar abordagem direta:
    # Combinacao = soma ponderada dos member forces de cada caso
    # Para simplificar, vamos iterar por elemento indexado como (caso, elem)
    # Melhor: criar um dict combinado
    all_elems = set()
    for mfd in cases_mf.values():
        all_elems.update(mfd.keys())
    results = {}
    # envelope por SEGMENTO do rafter (para a verificacao segmento-a-segmento do
    # tapered - a secao do joelho NAO governa necessariamente): por elemento do
    # rafter, guarda o maior |M| (e o N/V concomitantes) e a combinacao governante.
    raft_seg_env = {}
    for i in range(N_VAOS):
        for side in (0, 1):
            for e in ix["rafts"][i][side]:
                raft_seg_env[e] = {"M": 0.0, "N": 0.0, "V": 0.0, "gov": None}
    # envelope por SEGMENTO da coluna tapered (so os NSEG elementos base->joelho de
    # cada coluna; console/beiral fica de fora). A base NAO governa necessariamente.
    col_tap = _coluna_tapered()
    col_seg_env = {}
    if col_tap:
        for i in range(N_VAOS + 1):
            for e in ix["cols"][i][:NSEG]:
                col_seg_env[e] = {"M": 0.0, "N": 0.0, "V": 0.0, "gov": None}
    for cname, c in combos.items():
        mf_c = {}
        for e in all_elems:
            mf_c[e] = sum(cases_mf[cs].get(e, [0]*6) * fac for cs, fac in c.items())
        for e, se in raft_seg_env.items():
            fe = mf_c[e]
            M = max(abs(fe[2]), abs(fe[5]))
            N = max(abs(fe[0]), abs(fe[3])); V = max(abs(fe[1]), abs(fe[4]))
            if M > se["M"]:
                se["M"] = M; se["gov"] = cname
            se["N"] = max(se["N"], N); se["V"] = max(se["V"], V)
        for e, se in col_seg_env.items():
            fe = mf_c[e]
            M = max(abs(fe[2]), abs(fe[5]))
            N = max(abs(fe[0]), abs(fe[3])); V = max(abs(fe[1]), abs(fe[4]))
            if M > se["M"]:
                se["M"] = M; se["gov"] = cname
            se["N"] = max(se["N"], N); se["V"] = max(se["V"], V)
        # resultados por grupo
        cols_r = []
        for i in range(N_VAOS + 1):
            M, N, V = _grupo_MNV(mf_c, ix["cols"][i])
            cols_r.append({"M": round(M, 2), "N": round(N, 2), "V": round(V, 2)})
        vigas_r = []
        for i in range(N_VAOS):
            Mr, Nr, Vr = 0.0, 0.0, 0.0
            for side in (0, 1):
                M, N, V = _grupo_MNV(mf_c, ix["rafts"][i][side])
                Mr = max(Mr, M); Nr = max(Nr, N); Vr = max(Vr, V)
            vigas_r.append({"M": round(Mr, 2), "N": round(Nr, 2), "V": round(Vr, 2)})
        resp = {"colunas": cols_r, "vigas": vigas_r}
        if N_VAOS == 1:
            resp["coluna"] = cols_r[0] if cols_r[0]["M"] >= cols_r[1]["M"] else cols_r[1]
            resp["viga"] = vigas_r[0]
        # pior coluna e pior viga (maior M)
        pior_col = max(cols_r, key=lambda x: x["M"])
        pior_viga = max(vigas_r, key=lambda x: x["M"])
        resp["coluna_pior"] = pior_col
        resp["viga_pior"] = pior_viga
        results[cname] = resp
    # --- drift lateral (ELS) ---
    # Flecha no beiral sob vento caracteristico (G=1.0, W=1.0)
    def eave_drift(d):
        return max(abs(d[3 * ne]) for ne in ix["nEaves"]) if d is not None else 0.0
    drift = max(eave_drift(dW1), eave_drift(dW2))
    drift_sismo = eave_drift(cases_d.get("SISMO")) if SISMO else 0.0
    # flecha vertical na cumeeira (G+Q caracteristico). Shed (1 agua) nao tem
    # cumeeira -> usa o beiral ALTO (default=0 evita max() de sequencia vazia).
    _vnodes = ix["nRidges"] if ix["nRidges"] else ([ix["nEaves"][-1]] if ix.get("shed") else [])
    ridge_v = max((abs(dG[3 * rn + 1] + dQ[3 * rn + 1]) for rn in _vnodes), default=0.0) \
        if "SISMO" not in cases_d else 0.0
    # lista ordenada dos segmentos do rafter com esforco enveloped + secao (tapered)
    rafter_segmentos = []
    for i in range(N_VAOS):
        for side in (0, 1):
            secs = (_secoes_rafter("eave2ridge" if side == 0 else "ridge2eave")
                    if TAPERED else None)
            elems = ix["rafts"][i][side]
            L_raft = math.hypot(SPANS[i] / 2.0, _ridge_h(i) - EAVE)   # meia-agua (m) por vao
            Lseg = L_raft / len(elems) if elems else None
            for k, e in enumerate(elems):
                se = raft_seg_env[e]
                rafter_segmentos.append({
                    "vao": i, "lado": side, "seg": k,
                    "M": round(se["M"], 2), "N": round(se["N"], 2),
                    "V": round(se["V"], 2), "gov": se["gov"],
                    "L_seg": Lseg, "h_m": (secs[k]["h_m"] if secs else None),
                    "sec_props": (secs[k]["props"] if secs else None)})
    # lista ordenada dos segmentos da coluna tapered (base->joelho) com esforco
    # enveloped + secao. Vazio quando a coluna e prismatica.
    coluna_segmentos = []
    if col_tap:
        for i in range(N_VAOS + 1):
            secs = _secoes_coluna()
            elems = ix["cols"][i][:NSEG]
            Lseg = EAVE / len(elems) if elems else None
            for k, e in enumerate(elems):
                se = col_seg_env[e]
                coluna_segmentos.append({
                    "coluna": i, "seg": k,
                    "M": round(se["M"], 2), "N": round(se["N"], 2),
                    "V": round(se["V"], 2), "gov": se["gov"],
                    "L_seg": Lseg, "h_m": secs[k]["h_m"],
                    "sec_props": secs[k]["props"]})
    return {"results": results, "drift": drift, "drift_sismo": drift_sismo,
            "ridge_v": ridge_v, "drift_lims": {"H/300": EAVE / 300.0,
               "H/250": EAVE / 250.0, "H/200": EAVE / 200.0, "H/150": EAVE / 150.0},
            "drift_ref": "H/300", "ix": ix, "N_VAOS": N_VAOS,
            "rafter_segmentos": rafter_segmentos, "tapered": bool(TAPERED),
            "coluna_segmentos": coluna_segmentos,
            "coluna_tapered": col_tap}


def memoria_pt(a):
    """Relatorio PT do portico."""
    L = [
        "=" * 70,
        f"PORTICO 2D ({N_VAOS} vao(s)) - ANALISE DE 1a ORDEM",
        "CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL",
        "=" * 70, "",
        f"Geometria: {N_VAOS} vao(s) {SPANS} m ; beiral {EAVE:.1f} m ; "
        f"cumeeira {RIDGE:.1f} m ; inclinacao {math.degrees(THETA):.2f} deg",
        f"Colunas: {N_VAOS + 1} (A={A_COL*1e4:.1f} cm2, Ix={I_COL*1e8:.0f} cm4)",
        f"Vigas: {2 * N_VAOS} (A={A_RAF*1e4:.1f} cm2, Ix={I_RAF*1e8:.0f} cm4)",
        f"Base: {'engastada' if BASE_FIXED else 'rotulada'}",
        "", "COMBINACOES - esforcos de 1a ordem por grupo:",
        f"{'Combo':>22} {'Col(s)':>8} {'Mcol':>8} {'Ncol':>8} {'Vcol':>6}"
        f" {'Mvig':>8} {'Nvig':>8} {'Vvig':>6}",
        "-" * 70
    ]
    for cname, r in sorted(a["results"].items()):
        pc = r["coluna_pior"]; pv = r["viga_pior"]
        L.append(f"{cname:>22} {N_VAOS + 1:>3} un  {pc['M']:>7.1f} "
                 f"{pc['N']:>7.1f} {pc['V']:>6.1f} {pv['M']:>7.1f} "
                 f"{pv['N']:>7.1f} {pv['V']:>6.1f}")
    L += ["-" * 70, "",
          f"ELS: drift lateral max = {a['drift']*1000:.1f} mm (beiral) ; "
          f"limites: H/300={a['drift_lims']['H/300']*1000:.1f} mm"]
    if a.get("drift_sismo"):
        L.append(f"  drift sismico = {a['drift_sismo']*1000:.1f} mm")
    L.append(f"  flecha vertical cumeeira = {a['ridge_v']*1000:.1f} mm (G+Q carac.)")
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # 1 vao 20m (retrocompatibilidade)
    configurar(span=20.0, eave=6.0, ridge=6.5, bay=5.0, base_fixed=True,
               A_col=53.8e-4, I_col=3692e-8, A_raf=45.3e-4, I_raf=2510e-8)
    a = analyse()
    assert "C1_grav_W1" in a["results"], a["results"].keys()
    r = a["results"]["C1_grav_W1"]
    assert "coluna" in r and "viga" in r, r.keys()
    assert r["coluna"]["M"] > 0 and r["viga"]["M"] > 0, r
    assert a["drift"] >= 0
    # 2 vaos
    configurar(spans=[20.0, 20.0], eave=6.0, ridge=6.5, bay=5.0)
    a2 = analyse()
    assert a2["N_VAOS"] == 2
    r2 = a2["results"]["C1_grav_W1"]
    assert len(r2["colunas"]) == 3, len(r2["colunas"])
    assert len(r2["vigas"]) == 2, len(r2["vigas"])
    assert a2["drift"] >= 0
    # Bug 8.21: o frame deve honrar secoes POR-COLUNA (SEC_COLS_PORTICO). Coluna
    # central mais rigida atrai mais momento -> reacoes de base mudam.
    def _mbase():
        fr, ix = _frame()
        fr.add_nodal_load(ix["nEaves"][0], Fx=50.0)
        fr.solve(); R = fr.reactions()
        return [R[3 * b + 2] for b in ix["nBases"]]
    global SEC_COLS_PORTICO
    SEC_COLS_PORTICO = None
    m_unif = _mbase()
    SEC_COLS_PORTICO = [{"A": A_COL, "I": I_COL},
                        {"A": A_COL * 2.0, "I": I_COL * 3.0},
                        {"A": A_COL, "I": I_COL}]
    m_pc = _mbase()
    assert any(abs(a - b) > 1e-6 for a, b in zip(m_unif, m_pc)), \
        "frame ignora SEC_COLS_PORTICO (bug 8.21)"
    assert abs(m_pc[1]) > abs(m_unif[1]), \
        "coluna central rigida deveria atrair mais momento"
    reset()  # limpa SEC_COLS_PORTICO (nao vazar estado)
    assert SEC_COLS_PORTICO is None
    print("galpao_portico self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        configurar(span=20.0, eave=6.0, ridge=6.5, bay=5.0, base_fixed=True)
        a = analyse()
        print(memoria_pt(a))
