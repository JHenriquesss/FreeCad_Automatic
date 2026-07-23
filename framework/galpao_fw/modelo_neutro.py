# ============================================================================
# modelo_neutro.py - MODELO NEUTRO (puro, SEM FreeCAD) do portico primario do
# galpao: a "receita" da estrutura como DADOS (barras com perfil + extremidades +
# secao), nao como chamadas de API do FreeCAD. E a camada de intercambio entre o
# CALCULO e os EMISSORES (FreeCAD, IFC, ...). Item 2 do roteiro de
# interoperabilidade: com o modelo neutro, o FreeCAD deixa de ser obrigatorio para
# o entregavel BIM (ver ifc_emit.py, emissor IFC puro-Python).
#
# Escopo desta 1a versao: estrutura PRIMARIA (colunas + rafters/meias-aguas). Os
# secundarios, chapas e ligacoes seguem no modelo do FreeCAD (build_galpao) ate
# serem migrados. Coordenadas em MILIMETROS (padrao do IFC de galpao). O eixo do
# galpao: X = comprimento (linha de porticos), Y = vao(s) transversal(is), Z =
# altura. As secoes (d, bf, tw, tf) chegam em METROS (catalogo perfis) e o membro
# guarda-as como estao; o emissor converte p/ mm.
# ============================================================================
"""Modelo neutro (puro) do portico primario: barras com perfil + extremidades."""

from __future__ import annotations

MM = 1000.0


def _n_porticos(comprimento, bay):
    return int(round(comprimento / bay)) + 1 if bay > 0 else 1


def frame_primario(geometria, secoes):
    """Monta o modelo neutro das barras PRIMARIAS (colunas + rafters).
    geometria: {span|spans, comprimento, eave, ridge, bay} em METROS.
    secoes: {"col": {nome, d, bf, tw, tf}, "raf": {nome, d, bf, tw, tf}} em METROS.
    Retorna lista de membros; cada um:
      {marca, perfil, tipo ("Column"/"Beam"), p1 (mm), p2 (mm), secao (m)}."""
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    comp = float(geometria["comprimento"])
    bay = float(geometria["bay"])
    eave = float(geometria["eave"])
    ridge = float(geometria.get("ridge", eave))
    np_ = _n_porticos(comp, bay)
    xs = [comp * i / (np_ - 1) for i in range(np_)] if np_ > 1 else [0.0]
    cols_y = [0.0]                                   # linhas de coluna em Y
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    col, raf = secoes["col"], secoes["raf"]
    membros = []
    for x in xs:
        # COLUNAS: uma por linha de vao, da base (Z=0) ao beiral (Z=eave)
        for y in cols_y:
            membros.append({"marca": "C1", "perfil": col["nome"], "tipo": "Column",
                            "p1": (x * MM, y * MM, 0.0),
                            "p2": (x * MM, y * MM, eave * MM), "secao": col})
        # RAFTERS: 2 meias-aguas por vao (do beiral a cumeeira, subindo)
        for j in range(len(spans)):
            yr = (cols_y[j] + cols_y[j + 1]) / 2.0
            for ya in (cols_y[j], cols_y[j + 1]):
                membros.append({"marca": "V%d" % (j + 1), "perfil": raf["nome"],
                                "tipo": "Beam",
                                "p1": (x * MM, ya * MM, eave * MM),
                                "p2": (x * MM, yr * MM, ridge * MM), "secao": raf})
    return membros


def frame_primario_tapered(geometria, tapered):
    """Pórtico de ALMA VARIÁVEL (tapered): colunas + rafters como I de ALTURA
    VARIÁVEL (loft entre 2 seções I de mesma mesa, alturas diferentes nas pontas).
    Espelha tapered_column/tapered_rafter do build_galpao:
      - rafter: funda no joelho (h_joelho, no beiral) -> rasa na cumeeira (h_cumeeira);
      - coluna: h_col_base (base) -> h_joelho (joelho, no beiral). Sem h_col_base a
        coluna é PRISMÁTICA na altura do joelho (o build usa COL_SEC prismático ali).
    tapered {h_joelho, h_cumeeira, bf, tw, tf, h_col_base?} em METROS. Membro tapered
    carrega `secao` (início) + `secao2` (fim); prismático carrega só `secao`. O eixo
    forte (altura d) fica no plano do pórtico (mesma orientação do frame_primario)."""
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    comp = float(geometria["comprimento"])
    bay = float(geometria["bay"])
    eave = float(geometria["eave"])
    ridge = float(geometria.get("ridge", eave))
    np_ = _n_porticos(comp, bay)
    xs = [comp * i / (np_ - 1) for i in range(np_)] if np_ > 1 else [0.0]
    cols_y = [0.0]
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    hj = float(tapered["h_joelho"])
    hc = float(tapered["h_cumeeira"])
    bf = float(tapered.get("bf", 0.20))
    tw = float(tapered.get("tw", 0.008))
    tf = float(tapered.get("tf", 0.0125))
    hcb = tapered.get("h_col_base")
    hcb = float(hcb) if hcb is not None else None

    def _I(h):
        return {"nome": "I%d" % int(round(h * 1000)), "forma": "I",
                "d": float(h), "bf": bf, "tw": tw, "tf": tf}

    membros = []
    for x in xs:
        for y in cols_y:
            col = {"marca": "C1", "perfil": "COL-VAR", "tipo": "Column",
                   "p1": (x * MM, y * MM, 0.0), "p2": (x * MM, y * MM, eave * MM),
                   "secao": _I(hcb if hcb is not None else hj)}
            if hcb is not None:                       # coluna afina: base -> joelho
                col["secao2"] = _I(hj)
            membros.append(col)
        for j in range(len(spans)):                   # rafters: joelho -> cumeeira
            yr = (cols_y[j] + cols_y[j + 1]) / 2.0
            for ya in (cols_y[j], cols_y[j + 1]):
                membros.append({"marca": "V%d" % (j + 1), "perfil": "RAF-VAR",
                                "tipo": "Beam",
                                "p1": (x * MM, ya * MM, eave * MM),
                                "p2": (x * MM, yr * MM, ridge * MM),
                                "secao": _I(hj), "secao2": _I(hc)})
    return membros


def tercas(geometria, n_terca, terca_sec):
    """Terças (purlins) LONGITUDINAIS do modelo neutro: barras X=0->comprimento na
    altura do rafter, `n_terca-1` posicoes INTERMEDIARIAS por agua (eave e cumeeira
    ficam com as tercas de beiral/cumeeira, fora deste conjunto), nas duas aguas de
    cada vao. Replica a convencao do build_galpao (loop das tercas, k=1..n_terca-1,
    yl interpolado eave->ridge; ver terca_ys la) - guardado por cross-check de
    contagem em test_modelo_neutro. terca_sec: {nome, h/d, bf, t, lip} (m), forma C.
    Assenta no TOPO do rafter (z = rafter + meia-alma do rafter + meia-alma da terca)."""
    if not n_terca or n_terca < 2 or not terca_sec:
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    comp = float(geometria["comprimento"])
    eave = float(geometria["eave"])
    ridge = float(geometria.get("ridge", eave))
    raf_d = float(geometria.get("raf_d", 0.0))       # altura do rafter (m), p/ o assento
    t_h = float(terca_sec.get("d") or terca_sec.get("h") or 0.0)
    off = (raf_d / 2.0 + t_h / 2.0)                  # terca no topo do rafter
    cols_y = [0.0]
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    nome = terca_sec.get("nome", "Terca")

    def _terca(yl, zl):
        ms.append({"marca": "T1", "perfil": nome, "tipo": "Member",
                   "p1": (0.0, yl * MM, zl * MM),
                   "p2": (comp * MM, yl * MM, zl * MM), "secao": terca_sec})

    ms = []
    for j in range(len(spans)):
        y0, y1 = cols_y[j], cols_y[j + 1]
        yr = (y0 + y1) / 2.0                          # cumeeira do vao
        for k in range(1, int(n_terca)):
            for (ya, yb) in ((y0, yr), (y1, yr)):     # agua E (sobe ate cumeeira) e D
                yl = ya + (yb - ya) * k / n_terca
                zl = eave + (ridge - eave) * (yl - ya) / (yb - ya) + off
                _terca(yl, zl)
    # tercas de BEIRAL: uma em cada lado externo do galpao (cols_y[0] e cols_y[-1]),
    # na cota do beiral (mesma convencao do build_galpao, TERCA_BEIRAL_E/D).
    _terca(cols_y[0], eave + off)
    _terca(cols_y[-1], eave + off)
    return ms


GIRT_Z_MM = (2000.0, 4000.0)                          # niveis dos girts (mm) - espelha o build


def girts(geometria, girt_sec, col_d=0.0):
    """Girts de parede (longarinas): U LONGITUDINAIS em 2 niveis (GIRT_Z_MM), nas 2
    paredes longitudinais (y = -GOFF e y = SPAN + GOFF, GOFF = col_d/2 + girt_d/2 =
    girt contra a mesa do pilar). Perfil U (UPE). Espelha o build_galpao
    (TERCA_PAREDE), caso comum sem porta lateral (que segmentaria a parede). Niveis
    acima do beiral sao descartados. col_d e a altura do pilar (m)."""
    if not girt_sec:
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    comp = float(geometria["comprimento"])
    eave = float(geometria["eave"])
    span_tot = sum(spans)
    girt_d = float(girt_sec.get("d") or girt_sec.get("h") or 0.0)
    goff = col_d / 2.0 + girt_d / 2.0
    nome = girt_sec.get("nome", "Girt")
    ms = []
    for z_mm in GIRT_Z_MM:
        if z_mm > eave * MM:                          # girt acima do beiral -> nao existe
            continue
        for y in (-goff, span_tot + goff):
            ms.append({"marca": "G1", "perfil": nome, "tipo": "Member",
                       "p1": (0.0, y * MM, z_mm), "p2": (comp * MM, y * MM, z_mm),
                       "secao": girt_sec})
    return ms


def _xs(geometria):
    """Posicoes X dos porticos (m)."""
    comp = float(geometria["comprimento"])
    bay = float(geometria["bay"])
    np_ = _n_porticos(comp, bay)
    return [comp * i / (np_ - 1) for i in range(np_)] if np_ > 1 else [0.0]


def tirantes_parede(geometria, n_tirante, d_mm, col_d=0.0, girt_d=0.0):
    """Tirantes de parede: barras redondas VERTICAIS (Z0->beiral), n_tirante por vao
    (xk = x0 + bay*k/(n+1)), nas 2 paredes (y=-GOFF e SPAN+GOFF). Espelha o
    build_galpao (TIRANTE_PAREDE). d_mm = diametro (mm)."""
    if not n_tirante or n_tirante < 1:
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    span_tot = sum(float(s) for s in spans if s)
    eave = float(geometria["eave"])
    goff = col_d / 2.0 + girt_d / 2.0
    xs = _xs(geometria)
    sec = {"nome": "R%.0f" % d_mm, "forma": "round", "D": d_mm / 1000.0}
    ms = []
    for b in range(len(xs) - 1):
        bay = xs[b + 1] - xs[b]
        for k in range(1, int(n_tirante) + 1):
            xk = xs[b] + bay * k / (n_tirante + 1)
            for y in (-goff, span_tot + goff):
                ms.append({"marca": "TR1", "perfil": sec["nome"], "tipo": "Member",
                           "p1": (xk * MM, y * MM, 0.0),
                           "p2": (xk * MM, y * MM, eave * MM), "secao": sec})
    return ms


def contrav_cobertura(geometria, d_mm=20.0):
    """Contraventamento de cobertura: 2 diagonais cruzadas (so-tracao) no plano do
    beiral, nos vaos de EXTREMIDADE (1o e ultimo). Espelha o build_galpao
    (CONTRAV_COBERTURA). Barras redondas d_mm."""
    spans = geometria.get("spans") or [geometria.get("span")]
    span_tot = sum(float(s) for s in spans if s)
    eave = float(geometria["eave"])
    xs = _xs(geometria)
    if len(xs) < 2:
        return []
    pares = [(xs[0], xs[1])]
    if len(xs) >= 3:
        pares.append((xs[-2], xs[-1]))
    sec = {"nome": "R%.0f" % d_mm, "forma": "round", "D": d_mm / 1000.0}
    ms = []
    for (x0, x1) in pares:
        for (xa, xb) in ((x0, x1), (x1, x0)):         # A e B (cruzadas)
            ms.append({"marca": "CV1", "perfil": sec["nome"], "tipo": "Member",
                       "p1": (xa * MM, 0.0, eave * MM),
                       "p2": (xb * MM, span_tot * MM, eave * MM), "secao": sec})
    return ms


def fundacoes(geometria, fund_sec):
    """Fundacoes rasas (sapata/bloco): uma CAIXA B x L x h por base de coluna, com o
    TOPO no nivel do solo (Z0=0) descendo -h. Espelha SAPATA_ do build (o bloco raso
    tambem sai como caixa). fund_sec {B,L,h} em m. Membro tipo 'Footing' definido por
    CENTRO + dims (nao por eixo)."""
    if not fund_sec or not all(k in fund_sec for k in ("B", "L", "h")):
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    B, L, h = float(fund_sec["B"]), float(fund_sec["L"]), float(fund_sec["h"])
    cols_y = [0.0]
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    nome = "Bloco" if str(fund_sec.get("tipo")) == "bloco" else "Sapata"
    ms = []
    for x in _xs(geometria):
        for y in cols_y:
            ms.append({"marca": nome[:3].upper() + "1", "perfil": nome, "tipo": "Footing",
                       "centro": (x * MM, y * MM, -h / 2.0 * MM),
                       "dims": (B * MM, L * MM, h * MM), "secao": fund_sec})
    return ms


def placas_base(geometria, base_sec, z0_mm=30.0):
    """Placas de base das colunas: uma CAIXA B x L x t por base, com o TOPO no nível
    do grout (Z0) descendo -t. Espelha PLACA_BASE_ do build (plate B x L x t centrada
    em Z0-t/2). base_sec {B, L, t} em m (do base_adotada). Membro tipo 'Plate' (chapa)
    definido por CENTRO + dims -> IfcPlate. Uma por base de coluna."""
    if not base_sec or not all(k in base_sec for k in ("B", "L", "t")):
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    B, L, t = float(base_sec["B"]), float(base_sec["L"]), float(base_sec["t"])
    Z0 = float(z0_mm)
    cols_y = [0.0]
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    ms = []
    for x in _xs(geometria):
        for y in cols_y:
            ms.append({"marca": "PB1", "perfil": "PlacaBase", "tipo": "Plate",
                       "centro": (x * MM, y * MM, Z0 - t * MM / 2.0),
                       "dims": (B * MM, L * MM, t * MM), "secao": base_sec})
    return ms


def gussets_contrav(geometria, gusset_t=12.0, esc_d=0.152, L=150.0, z0_mm=30.0):
    """Gussets (chapas triangulares) dos cantos dos painéis de contraventamento, nos
    vãos de EXTREMIDADE. Cobertura: 4 cantos/vão (plano X-Y no beiral). Parede: 4/vão
    por parede (plano X-Z), o superior nasce sob a escora (z=eave-esc_d/2). Espelha
    CONEX_GUSSET_COB_/CONEX_GUSSET_PAR_ do build (_gusset_tri: nó + d1,d2 x L). gusset_t
    (mm), esc_d = altura da escora (m). Poligono triangular tipo 'Plate' -> IfcPlate."""
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    EAVE = float(geometria["eave"]) * MM
    SPAN = sum(spans) * MM
    Z0 = float(z0_mm)
    z_top = EAVE - float(esc_d) * MM / 2.0
    xs = [x * MM for x in _xs(geometria)]
    if len(xs) < 2:
        return []
    end_bays = [(xs[0], xs[1]), (xs[-2], xs[-1])]
    ms = []

    def _tri(node, d1, d2):
        A = node
        B = (A[0] + d1[0] * L, A[1] + d1[1] * L, A[2] + d1[2] * L)
        C = (A[0] + d2[0] * L, A[1] + d2[1] * L, A[2] + d2[2] * L)
        ms.append({"marca": "GC1", "perfil": "GussetContrav", "tipo": "Plate",
                   "poligono": [A, B, C], "esp": float(gusset_t), "aberturas": [],
                   "secao": {"forma": "poly"}})

    for (x0, x1) in end_bays:
        for (nx, ny, d1, d2) in ((x0, 0.0, (1, 0, 0), (0, 1, 0)),
                                 (x1, 0.0, (-1, 0, 0), (0, 1, 0)),
                                 (x0, SPAN, (1, 0, 0), (0, -1, 0)),
                                 (x1, SPAN, (-1, 0, 0), (0, -1, 0))):
            _tri((nx, ny, EAVE), d1, d2)
        for yw in (0.0, SPAN):
            for (nx, nz, d1, d2) in ((x0, Z0, (1, 0, 0), (0, 0, 1)),
                                     (x1, Z0, (-1, 0, 0), (0, 0, 1)),
                                     (x0, z_top, (1, 0, 0), (0, 0, -1)),
                                     (x1, z_top, (-1, 0, 0), (0, 0, -1))):
                _tri((nx, yw, nz), d1, d2)
    return ms


def conectores_base(geometria, base_full, z0_mm=30.0):
    """Conectores da base: por ancoragem, chumbador (barra) + gancho + arruela (chapa)
    + porca + porca de nível. Espelha CHUMBADOR_/PORCA_/ARRUELA_ do build. base_full
    {B, L, t, db, n} em m (base_adotada). Tipo 'Fastener' -> IfcMechanicalFastener.
    Ancoragens: malha (-gx,gx) x (ys), ys = [-gy,0,gy] se n>=6 senão [-gy,gy]."""
    if not base_full or not all(k in base_full for k in ("B", "L", "t", "db", "n")):
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    Bp, Lp = float(base_full["B"]) * MM, float(base_full["L"]) * MM
    tp, dbp, npc = float(base_full["t"]) * MM, float(base_full["db"]) * MM, int(base_full["n"])
    Z0 = float(z0_mm)
    ptop, pbot = Z0, Z0 - tp
    edge = 60.0
    gx, gy = Bp / 2.0 - edge, Lp / 2.0 - edge
    ys = [-gy, 0.0, gy] if npc >= 6 else [-gy, gy]
    ancoras = [(dx, dy) for dx in (-gx, gx) for dy in ys]
    wsz, wt, pod = 2.0 * dbp + 40.0, float(T_ARRUELA), 1.7 * dbp + 8.0
    cols_y = [0.0]
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    rb = {"nome": "Ø%g" % dbp, "forma": "round", "D": dbp / MM}    # chumbador
    rp = {"nome": "Ø%gp" % pod, "forma": "round", "D": pod / MM}   # porca
    ms = []
    for x in _xs(geometria):
        for y in cols_y:
            xm, ym = x * MM, y * MM
            for (dx, dy) in ancoras:
                ax, ay = xm + dx, ym + dy
                ms.append({"marca": "CB1", "perfil": rb["nome"], "tipo": "Fastener",
                           "p1": (ax, ay, -300.0), "p2": (ax, ay, ptop + 55.0), "secao": rb})
                ms.append({"marca": "CG1", "perfil": rb["nome"], "tipo": "Fastener",
                           "p1": (ax, ay, -300.0), "p2": (ax, ay - 60.0, -300.0), "secao": rb})
                ms.append({"marca": "AR1", "perfil": "Arruela", "tipo": "Fastener",
                           "centro": (ax, ay, ptop + wt / 2.0),
                           "dims": (wsz, wsz, wt), "secao": {"forma": "box"}})
                ms.append({"marca": "PC1", "perfil": rp["nome"], "tipo": "Fastener",
                           "p1": (ax, ay, ptop + 12.0), "p2": (ax, ay, ptop + 30.0), "secao": rp})
                ms.append({"marca": "PN1", "perfil": rp["nome"], "tipo": "Fastener",
                           "p1": (ax, ay, pbot - 28.0), "p2": (ax, ay, pbot), "secao": rp})
    return ms


T_ARRUELA = 12.0                                      # espessura da arruela (mm), = build


def nervuras_base(geometria, col_d, base_L, z0_mm=30.0, esp_mm=12.0):
    """Nervuras (enrijecedores) da placa de base: 2 chapas triangulares por base, no
    plano do pórtico (Y-Z, X constante), uma p/ cada lado da coluna (+Y e -Y). Espelha
    NERVURA_BASE_ do build (triangulo V1-V2-V3, extrudado 12mm em X, centrado). col_d =
    altura do perfil da coluna (m); base_L = comprimento da placa (m). Membro poligonal
    tipo 'Plate' -> IfcPlate. Uma nervura sobe do topo do grout (Z0) 300mm."""
    if not col_d or not base_L:
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    Z0 = float(z0_mm)
    ftip = float(col_d) * MM / 2.0                     # face da coluna em Y = d/2
    yb2 = min(ftip + 140.0, float(base_L) * MM / 2.0)  # base da nervura sobre a placa
    cols_y = [0.0]
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    ms = []
    for x in _xs(geometria):
        xm = x * MM
        for y in cols_y:
            ym = y * MM
            for sgn in (1.0, -1.0):
                poly = [(xm, ym + sgn * ftip, Z0),
                        (xm, ym + sgn * yb2, Z0),
                        (xm, ym + sgn * ftip, Z0 + 300.0)]
                ms.append({"marca": "NB1", "perfil": "NervuraBase", "tipo": "Plate",
                           "poligono": poly, "esp": float(esp_mm),
                           "aberturas": [], "secao": {"forma": "poly"}})
    return ms


def _rafz_mm(geometria):
    """Fábrica de rafter_z(y_mm)->z_mm a partir de eave/ridge (m). Cume no meio do vão,
    linear eave->ridge->eave; multi-vão por span."""
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    eave = float(geometria["eave"]); ridge = float(geometria.get("ridge", eave))
    cols = [0.0]
    for s in spans:
        cols.append(cols[-1] + s)
    cols = [c * MM for c in cols]
    rid = [(cols[i] + cols[i + 1]) / 2.0 for i in range(len(spans))]
    E = eave * MM; dR = (ridge - eave) * MM

    def _f(y):
        for i in range(len(spans)):
            c0, c1 = cols[i], cols[i + 1]
            if c0 - 1e-6 <= y <= c1 + 1e-6:
                ym = rid[i]
                return E + dR * ((y - c0) / (ym - c0) if y <= ym else (c1 - y) / (c1 - ym))
        return E
    return _f, cols, rid


def drenagem(geometria, calha_bh, condutor_d, col_d, girt_h, base_L, z0_mm=30.0):
    """Drenagem: 2 calhas longitudinais (perfil U, no beiral) + condutores verticais
    e bocais em 3 posições (extremos + meio) x 2 paredes. Espelha CALHA_/CONDUTOR_/
    BOCAL_ do build. calha_bh=(B_mm,H_mm); condutor_d (mm); col_d/girt_h/base_L (m).
    Tipo 'Member' -> IfcMember (drenagem, linear). Coords em mm."""
    if not calha_bh or not condutor_d:
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    comp = float(geometria["comprimento"]) * MM
    eave = float(geometria["eave"])
    EAVE = eave * MM
    SPAN = sum(spans) * MM
    B, H = float(calha_bh[0]), float(calha_bh[1])
    cd = float(col_d) * MM
    gh = float(girt_h) * MM
    bL = float(base_L) * MM
    GUT_Y = cd / 2.0 + gh + B / 2.0 + 30.0
    DOWN_Y = max(GUT_Y, bL / 2.0 + condutor_d / 2.0 + 40.0)
    GUT_BOTTOM = EAVE - H / 2.0
    csec = {"nome": "Calha%gx%g" % (B, H), "forma": "U",
            "d": H / MM, "bf": B / MM, "tw": 0.005, "tf": 0.005}
    dsec = {"nome": "Cond%g" % condutor_d, "forma": "round", "D": float(condutor_d) / MM}
    bsec = {"nome": "Bocal%g" % (condutor_d + 30.0), "forma": "round",
            "D": (float(condutor_d) + 30.0) / MM}
    xs = [x * MM for x in _xs(geometria)]
    ms = []
    for y in (-GUT_Y, SPAN + GUT_Y):                  # calhas
        ms.append({"marca": "CL1", "perfil": csec["nome"], "tipo": "Member",
                   "p1": (0.0, y, EAVE), "p2": (comp, y, EAVE), "secao": csec})
    xd = [xs[0], xs[len(xs) // 2], xs[-1]]            # condutores/bocais: 3 posições
    for x in xd:
        for y in (-DOWN_Y, SPAN + DOWN_Y):
            ms.append({"marca": "BO1", "perfil": bsec["nome"], "tipo": "Member",
                       "p1": (x, y, GUT_BOTTOM), "p2": (x, y, GUT_BOTTOM - 120.0),
                       "secao": bsec})
            ms.append({"marca": "CD1", "perfil": dsec["nome"], "tipo": "Member",
                       "p1": (x, y, GUT_BOTTOM), "p2": (x, y, 0.0), "secao": dsec})
    return ms


def tirantes_cobertura(geometria, n_terca, d_mm=16.0):
    """Tirantes de cobertura (barras redondas): uma linha por vão/água a meio-vão
    entre pórticos (X), SEGMENTADA em cada terça (fecha na cumeeira). Espelha
    TIRANTE_S do build (pts entre y0/y1 e a cumeeira, cortados nas terças). Tipo
    'Member' -> IfcMember (barra redonda). Coords em mm."""
    if not n_terca or int(n_terca) < 2:
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    rafz, cols, rid = _rafz_mm(geometria)
    xs = [x * MM for x in _xs(geometria)]
    sec = {"nome": "Ø%g" % d_mm, "forma": "round", "D": float(d_mm) / MM}
    ms = []

    def _rod(xm, ya, yb):
        ms.append({"marca": "TC1", "perfil": sec["nome"], "tipo": "Member",
                   "p1": (xm, ya, rafz(ya)), "p2": (xm, yb, rafz(yb)), "secao": sec})

    for b in range(len(xs) - 1):
        xm = (xs[b] + xs[b + 1]) / 2.0
        for j in range(len(spans)):
            y0, y1, yrj = cols[j], cols[j + 1], rid[j]
            tys = []
            for k in range(1, int(n_terca)):
                tys.append(y0 + (yrj - y0) * k / n_terca)      # água E
                tys.append(y1 - (y1 - yrj) * k / n_terca)      # água D
            pts_e = [y0] + [p for p in sorted(y for y in tys if y0 <= y < yrj) if p != y0] + [yrj]
            for s in range(len(pts_e) - 1):
                _rod(xm, pts_e[s], pts_e[s + 1])
            pts_d = [y1] + [p for p in sorted((y for y in tys if yrj < y <= y1), reverse=True) if p != y1] + [yrj]
            for s in range(len(pts_d) - 1):
                _rod(xm, pts_d[s], pts_d[s + 1])
    return ms


def escoras_cumeeiras(geometria, esc_sec):
    """Escoras de beiral + vigas de cumeeira: barras LONGITUDINAIS (X) entre pórticos
    adjacentes. Escora de beiral: 2 por vão (paredes y=cols[0] e cols[-1], no beiral).
    Cumeeira: 1 por vão por água (y=cumeeira). Espelha ESCORA_BEIRAL_/CUMEEIRA_S do
    build (perfil_escora). Tipo 'Beam' -> IfcBeam. Coords em mm."""
    if not esc_sec:
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    rafz, cols, rid = _rafz_mm(geometria)
    xs = [x * MM for x in _xs(geometria)]
    ms = []
    for b in range(len(xs) - 1):
        x0, x1 = xs[b], xs[b + 1]
        for y in (cols[0], cols[-1]):                  # escoras de beiral (2 paredes)
            z = rafz(y)
            ms.append({"marca": "EB1", "perfil": esc_sec["nome"], "tipo": "Beam",
                       "p1": (x0, y, z), "p2": (x1, y, z), "secao": esc_sec})
        for yr in rid:                                 # cumeeiras (1 por água)
            z = rafz(yr)
            ms.append({"marca": "CM1", "perfil": esc_sec["nome"], "tipo": "Beam",
                       "p1": (x0, yr, z), "p2": (x1, yr, z), "secao": esc_sec})
    return ms


def montantes_oitao(geometria, esc_sec, aberturas=None, z0_mm=30.0):
    """Montantes de oitão: colunetas VERTICAIS nas empenas (pórticos de extremidade).
    Se há portão no oitão, ficam nos batentes; senão, nos terços do vão. Espelha
    MONTANTE_OITAO_ do build (perfil_escora, do Z0 até rafter_z(y)-95). 2 por oitão x
    2 oitões = 4. Tipo 'Member' -> IfcMember. Coords em mm."""
    if not esc_sec:
        return []
    ab = aberturas or {}
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    rafz, cols, _rid = _rafz_mm(geometria)
    SPAN = cols[-1]
    Z0 = float(z0_mm)
    xs = [x * MM for x in _xs(geometria)]

    def _ys(portao):
        if portao:
            gw = float(portao[0]) if isinstance(portao, (list, tuple)) else float(portao)
            return (SPAN / 2.0 - gw / 2.0, SPAN / 2.0 + gw / 2.0)
        return (SPAN / 3.0, 2.0 * SPAN / 3.0)

    ms = []
    for x, lbl in ((xs[0], "frente"), (xs[-1], "fundo")):
        for yg in _ys(ab.get("portao_%s" % lbl)):
            ms.append({"marca": "MO1", "perfil": esc_sec["nome"], "tipo": "Member",
                       "p1": (x, yg, Z0), "p2": (x, yg, rafz(yg) - 95.0),
                       "secao": esc_sec})
    return ms


def maos_francesas(geometria, n_terca, mf_stride, raf_d, raf_bf, ue_h, mf_sec=None):
    """Mãos-francesas (flange brace): trava lateral da mesa inferior do rafter (FLT
    sob sucção). REUSA o módulo PURO mao_francesa_geom (mfg.segmentos) - exatamente a
    geometria do build. raf_d/raf_bf = altura/mesa do rafter (m); ue_h = altura da
    terça (m); mf_stride = 1 braço a cada N terças; mf_sec (b_mm, t_mm) -> cantoneira
    (perfil L); sem mf_sec -> barra redonda DIAM_BRACO. Tipo 'Member' -> IfcMember."""
    import math
    import mao_francesa_geom as mfg
    if not n_terca or int(n_terca) < 2 or not mf_stride:
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    eave = float(geometria["eave"])
    ridge = float(geometria.get("ridge", eave))
    cols_y = [0.0]
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    cols_y_mm = [c * MM for c in cols_y]
    ridges_mm = [(cols_y_mm[i] + cols_y_mm[i + 1]) / 2.0 for i in range(len(spans))]
    slope = (ridge - eave) / (spans[0] / 2.0) if spans else 0.0
    theta = math.atan(slope)
    raf_h = float(raf_d) * MM
    poff = mfg.offset_terca(raf_h, float(raf_bf) * MM, float(ue_h) * MM, theta)
    EAVE = eave * MM

    def _rafz(y):
        for i in range(len(spans)):
            c0, c1 = cols_y_mm[i], cols_y_mm[i + 1]
            if c0 - 1e-6 <= y <= c1 + 1e-6:
                ym = ridges_mm[i]
                if y <= ym:
                    return EAVE + (ridge - eave) * MM * (y - c0) / (ym - c0)
                return EAVE + (ridge - eave) * MM * (c1 - y) / (c1 - ym)
        return EAVE

    xs_mm = [x * MM for x in _xs(geometria)]
    brace_k = [k for k in range(1, int(n_terca)) if k % int(mf_stride) == 0]
    if mf_sec:
        b, t = float(mf_sec[0]), float(mf_sec[1])
        sec = {"nome": "L%gx%g" % (b, t), "forma": "L",
               "d": b / MM, "bf": b / MM, "t": t / MM}
    else:
        sec = {"nome": "Ø%g" % mfg.DIAM_BRACO, "forma": "round", "D": mfg.DIAM_BRACO / MM}
    ms = []
    for (p1, p2, _nm) in mfg.segmentos(xs_mm, cols_y_mm, ridges_mm, int(n_terca),
                                       brace_k, raf_h, poff, _rafz, theta=theta):
        ms.append({"marca": "MF1", "perfil": sec["nome"], "tipo": "Member",
                   "p1": p1, "p2": p2, "secao": sec})
    return ms


def clipes_terca(geometria, n_terca, terca_sec, t_mm=8.0):
    """Clipes de apoio da terça: uma chapa de assento em cada cruzamento
    PÓRTICO x LINHA DE TERÇA (sob a terça, na mesa da viga). Espelha CLIPE_TERCA_ do
    build (plate 90x120xT por axis x terça_seat). Caixa 90x120xT tipo 'Plate' ->
    IfcPlate. Contagem = n_porticos x n_linhas_de_terça."""
    ts = tercas(geometria, n_terca, terca_sec)
    if not ts:
        return []
    t = float(t_mm)
    ms = []
    for x in _xs(geometria):
        xm = x * MM
        for tm in ts:
            yl, zl = tm["p1"][1], tm["p1"][2]
            ms.append({"marca": "CT1", "perfil": "ClipeTerca", "tipo": "Plate",
                       "centro": (xm, yl, zl - t / 2.0),
                       "dims": (90.0, 120.0, t), "secao": {"forma": "box"}})
    return ms


def clipes_girt(geometria, t_mm=8.0):
    """Clipes da longarina (girt) no pilar: uma chapa contra a face da mesa em cada
    cruzamento PÓRTICO x NÍVEL DE GIRT, nas 2 paredes. Espelha CLIPE_GIRT_E/D_ do
    build (plate 90xTx120 em y=∓(100+T/2)). Caixa tipo 'Plate' -> IfcPlate.
    Contagem = n_porticos x n_niveis(2) x 2 paredes."""
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    SPAN = sum(spans) * MM
    t = float(t_mm)
    ms = []
    for x in _xs(geometria):
        xm = x * MM
        for z in GIRT_Z_MM:
            for y in (-100.0 - t / 2.0, SPAN + 100.0 + t / 2.0):
                ms.append({"marca": "CG1", "perfil": "ClipeGirt", "tipo": "Plate",
                           "centro": (xm, y, z), "dims": (90.0, t, 120.0),
                           "secao": {"forma": "box"}})
    return ms


def telhas(geometria, telha_t=0.0007):
    """Telhas de cobertura: 2 paineis por vao (aguas E e D), do beiral a cumeeira,
    ao longo de todo o comprimento. Espelha TELHA_S do build. Cada painel = laje
    retangular (largura = comprimento do galpao, comprimida na inclinacao),
    representada como 'Covering' de perfil retangular (bf=comprimento, d=espessura)
    extrudado ao longo da INCLINACAO (beiral->cumeeira). telha_t = espessura (m)."""
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    comp = float(geometria["comprimento"])
    eave = float(geometria["eave"])
    ridge = float(geometria.get("ridge", eave))
    cols_y = [0.0]
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    sec = {"forma": "rect", "bf": comp, "d": telha_t}
    xm = comp / 2.0
    ms = []
    for j in range(len(spans)):
        y0, y1 = cols_y[j], cols_y[j + 1]
        yr = (y0 + y1) / 2.0
        for ya in (y0, y1):                            # agua E (do beiral y0) e D (y1)
            ms.append({"marca": "TL1", "perfil": "Telha", "tipo": "Covering",
                       "p1": (xm * MM, ya * MM, eave * MM),
                       "p2": (xm * MM, yr * MM, ridge * MM), "secao": sec})
    return ms


def tapamentos(geometria, fechamento=None, aberturas=None, z0_mm=30.0, tcl_mm=0.65):
    """Tapamento (fechamento de PAREDE) do modelo neutro: 2 paineis laterais (longos)
    + 2 oitoes (empenas), cada um um POLIGONO com espessura fina (pele metalica), com
    ABERTURAS (portas/janelas/portoes) recortadas. Espelha TAPAMENTO_LATERAL_/_OITAO_
    do build_galpao (yw=195, Z0=grout, recorte por caixa). Painel != barra: e definido
    por `poligono` (cantos 3D, mm) + `esp` (mm) + `aberturas` (caixas 3D a recortar);
    o emissor IFC extruda o perfil-com-vazios pela espessura. Tipo 'Cladding'
    (IfcCovering CLADDING). fechamento {tipo, altura_alvenaria}; tipo 'aberto' -> [].

    Contagem guardada por cross-check contra o build (TAPAMENTO_*)."""
    fech = fechamento or {}
    ftipo = fech.get("tipo", "telha")
    if ftipo == "aberto":
        return []
    ab = aberturas or {}
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    comp = float(geometria["comprimento"])
    eave = float(geometria["eave"])
    ridge = float(geometria.get("ridge", eave))
    L = comp * MM
    EAVE = eave * MM
    yw = 195.0
    Z0 = float(z0_mm)
    h_alv = float(fech.get("altura_alvenaria") or 0.0) * MM
    cols_y = [0.0]
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    cols_y = [c * MM for c in cols_y]
    ridges_y = [(cols_y[i] + cols_y[i + 1]) / 2.0 for i in range(len(spans))]
    SPAN = cols_y[-1]

    def _rafz(y):
        for i in range(len(spans)):
            c0, c1 = cols_y[i], cols_y[i + 1]
            if c0 - 1e-6 <= y <= c1 + 1e-6:
                ym = ridges_y[i]
                if y <= ym:
                    return EAVE + (ridge - eave) * MM * (y - c0) / (ym - c0)
                return EAVE + (ridge - eave) * MM * (c1 - y) / (c1 - ym)
        return EAVE

    PORTA_PESSOA = (900.0, 2130.0)
    ms = []

    def _painel(nome, poligono, esp, ops):
        ms.append({"marca": "TP1", "perfil": "Tapamento", "tipo": "Cladding",
                   "poligono": [tuple(float(v) for v in p) for p in poligono],
                   "esp": float(esp), "aberturas": [tuple(map(tuple, o)) for o in ops],
                   "secao": {"forma": "poly"}})

    # --- aberturas das paredes laterais (espelha build: janelas centrais + porta) ---
    lat_ops = {"E": [], "D": []}
    pl = ab.get("porta_lateral")
    if pl:
        lat_ops["E"].append(((pl[0], pl[1]), (-yw - 60, -yw + 60),
                             (Z0, Z0 + PORTA_PESSOA[1])))
    jl = ab.get("janelas_laterais")
    if jl:
        win_x = (float(geometria.get("bay", 0.0)) * MM, L - float(geometria.get("bay", 0.0)) * MM)
        lat_ops["E"].append((win_x, (-yw - 60, -yw + 60), (jl[0], jl[1])))
        lat_ops["D"].append((win_x, (SPAN + yw - 60, SPAN + yw + 60), (jl[0], jl[1])))

    def _parede_lateral(y, nome, ops):
        if ftipo == "alvenaria_telha" and h_alv > Z0:
            # meia-parede de alvenaria (caixa) + tapamento acima
            _painel(nome + "_ALVENARIA",
                    [(0, y - 95, Z0), (L, y - 95, Z0), (L, y - 95, h_alv), (0, y - 95, h_alv)],
                    190.0, [])
            zb = h_alv
            ops_sup = [o for o in ops if o[2][1] > zb]
        else:
            zb, ops_sup = Z0, ops
        _painel(nome, [(0, y, zb), (L, y, zb), (L, y, EAVE), (0, y, EAVE)],
                tcl_mm, ops_sup)

    _parede_lateral(-yw, "TAPAMENTO_LATERAL_E", lat_ops["E"])
    _parede_lateral(SPAN + yw, "TAPAMENTO_LATERAL_D", lat_ops["D"])

    # --- oitoes (empenas): poligono seguindo a linha do telhado + portao/porta ---
    for xc, lbl in ((-yw, "FRENTE"), (L + yw, "FUNDO")):
        ops = []
        portao = ab.get("portao_%s" % lbl.lower())
        porta = ab.get("porta_%s" % lbl.lower())
        if portao:
            gw, gh = portao
            yr = (SPAN / 2.0 - gw / 2.0 + 80.0, SPAN / 2.0 + gw / 2.0 - 80.0)
            ops.append(((xc - 300, xc + 300), yr, (Z0, Z0 + gh)))
        if porta:
            pw, ph = porta
            yr = (SPAN / 2.0 - pw / 2.0, SPAN / 2.0 + pw / 2.0)
            ops.append(((xc - 300, xc + 300), yr, (Z0, Z0 + ph)))
        pts = [(xc, cols_y[0], Z0), (xc, cols_y[-1], Z0), (xc, cols_y[-1], EAVE)]
        for j in range(len(spans) - 1, -1, -1):
            pts.append((xc, ridges_y[j], _rafz(ridges_y[j])))
            if j > 0:
                pts.append((xc, cols_y[j], EAVE))
        pts.append((xc, cols_y[0], EAVE))
        _painel("TAPAMENTO_OITAO_%s" % lbl, pts, tcl_mm, ops)
    return ms


def frame_completo(geometria, secoes, n_terca=None, terca_sec=None,
                   girt_sec=None, col_d=None, n_tirante_parede=None,
                   d_tirante_mm=16.0, contrav=False, d_contrav_mm=20.0,
                   fund_sec=None, telha=False, telha_t=0.0007,
                   fechamento=None, aberturas=None, tapered=None, base_sec=None,
                   nervura_base=False, esp_nervura_mm=12.0, clipes=False,
                   mao_francesa=None, esc_sec=None, montante_ab=None,
                   tirante_cob=False, d_tirante_cob_mm=16.0, base_full=None,
                   drenagem_cfg=None, gusset_contrav=None):
    """Modelo neutro fisico = primario (colunas + rafters, PRISMÁTICO ou tapered) +
    terças/girts/tirantes/contrav + fundações + placas de base + telha + tapamento.
    `tapered` (dict, m) -> primário de alma variável (secoes pode ser None nesse caso)."""
    if tapered:
        ms = frame_primario_tapered(geometria, tapered)
        raf_d = float(tapered.get("h_joelho", 0.0))   # seção mais funda (beiral)
        cd = col_d if col_d is not None else float(tapered.get("h_joelho", 0.0))
    else:
        cd = col_d if col_d is not None else (secoes.get("col") or {}).get("d", 0.0)
        ms = frame_primario(geometria, secoes)
        raf_d = (secoes.get("raf") or {}).get("d", 0.0) if secoes else 0.0
    geo = dict(geometria)                             # altura do rafter -> assento
    geo.setdefault("raf_d", raf_d)
    if n_terca and terca_sec:
        ms += tercas(geo, n_terca, terca_sec)
    girt_d = (girt_sec or {}).get("d", 0.0) if girt_sec else 0.0
    if girt_sec:
        ms += girts(geometria, girt_sec, cd)
    if clipes:                                        # chapas de assento/ligação
        if n_terca and terca_sec:
            ms += clipes_terca(geo, n_terca, terca_sec)
        if girt_sec:
            ms += clipes_girt(geometria)
    if mao_francesa and n_terca:                      # travas da mesa inferior (FLT)
        ms += maos_francesas(geometria, n_terca, mao_francesa.get("mf_stride"),
                             mao_francesa.get("raf_d"), mao_francesa.get("raf_bf"),
                             mao_francesa.get("ue_h"), mao_francesa.get("mf_sec"))
    if esc_sec:                                        # escoras/cumeeiras + montantes
        ms += escoras_cumeeiras(geometria, esc_sec)
        ms += montantes_oitao(geometria, esc_sec, aberturas=montante_ab)
    if tirante_cob and n_terca:                        # tirantes de cobertura segmentados
        ms += tirantes_cobertura(geometria, n_terca, d_tirante_cob_mm)
    if drenagem_cfg:                                   # calhas + condutores + bocais
        dc = drenagem_cfg
        ms += drenagem(geometria, dc.get("calha_bh"), dc.get("condutor_d"),
                       dc.get("col_d"), dc.get("girt_h"), dc.get("base_L"))
    if n_tirante_parede:
        ms += tirantes_parede(geometria, n_tirante_parede, d_tirante_mm, cd, girt_d)
    if contrav:
        ms += contrav_cobertura(geometria, d_contrav_mm)
    if gusset_contrav:                                 # chapas dos cantos do contravento
        ms += gussets_contrav(geometria, gusset_contrav.get("t", 12.0),
                              gusset_contrav.get("esc_d", 0.152))
    if fund_sec:
        ms += fundacoes(geometria, fund_sec)
    if base_sec:
        ms += placas_base(geometria, base_sec)
    if nervura_base and base_sec:
        ms += nervuras_base(geometria, cd, base_sec.get("L"), esp_mm=esp_nervura_mm)
    if base_full:
        ms += conectores_base(geometria, base_full)
    if telha:
        ms += telhas(geometria, telha_t)
    if fechamento is not None or aberturas is not None:
        ms += tapamentos(geometria, fechamento=fechamento, aberturas=aberturas)
    return ms


def analitico_do_spec(spec):
    """Modelo ANALITICO 2D do portico a partir do CALCULO (spec): nos + barras (com
    secao A/I) + apoios. Configura o galpao_portico com a geometria + secoes
    adotadas e extrai (nivel de membro). Retorna dict {nos, barras, apoios,
    unidade, n_porticos} ou None (perfil nao-laminado). E o intercambio ANALITICO -
    o mais rico p/ ferramenta de calculo (alimenta IFC-structural / SAF / outro
    software estrutural). Puro (sem FreeCAD)."""
    import galpao_portico as gp
    import perfis
    g = spec["geometria"]
    est = spec.get("estrutura", {}) or {}
    tap = (est.get("tapered") if est.get("tipo_portico") == "alma_variavel"
           and isinstance(est.get("tapered"), dict) else None)
    secao_var = None                                  # por grupo: (d_i, d_j, props_i, props_j)
    if tap:
        # ALMA VARIÁVEL: A/I das seções SOLDADAS (av.props_I). A topologia (nós/barras)
        # é section-agnostic; a barra recebe a seção REPRESENTATIVA do joelho (a mais
        # funda) + as duas seções de ponta anexadas p/ o downstream saber que varia.
        import alma_variavel as av
        hj = float(tap["h_joelho"]); hc = float(tap["h_cumeeira"])
        bf = float(tap.get("bf", 0.20)); tw = float(tap.get("tw", 0.008))
        tf = float(tap.get("tf", 0.0125))
        hcb = float(tap["h_col_base"]) if tap.get("h_col_base") is not None else hj
        pj = av.props_I(hj, bf, tw, tf)               # joelho: representa coluna e rafter
        acol = araf = pj["A"]; icol = iraf = pj["Ix"]
        secao_var = {"coluna": (hcb, hj, av.props_I(hcb, bf, tw, tf), pj),
                     "rafter": (hj, hc, pj, av.props_I(hc, bf, tw, tf))}
        sec_nomes = {"coluna": "VAR %d-%d" % (round(hcb * 1000), round(hj * 1000)),
                     "rafter": "VAR %d-%d" % (round(hj * 1000), round(hc * 1000))}
    else:
        pc = perfis.PERFIS.get(est.get("perfil_col_adotado"))
        pr = perfis.PERFIS.get(est.get("perfil_raf_adotado"))
        if not pc or not pr:
            return None                               # tesoura/prismático sem A/I -> None
        acol, icol = pc["A"], pc.get("Ix", pc.get("I"))
        araf, iraf = pr["A"], pr.get("Ix", pr.get("I"))
        sec_nomes = {"coluna": est.get("perfil_col_adotado"),
                     "rafter": est.get("perfil_raf_adotado")}
    gp.reset()                                        # limpa estado (SEC_COLS_PORTICO etc.)
    gp.configurar(span=g.get("span"), spans=g.get("spans"), eave=g["eave"],
                  ridge=g.get("ridge", g["eave"]), bay=g["bay"],
                  base_fixed=bool(g.get("base_fixed", False)),
                  A_col=acol, I_col=icol, A_raf=araf, I_raf=iraf)
    m = gp.modelo_analitico()
    comp, bay = g.get("comprimento"), g.get("bay")
    m["n_porticos"] = int(round(comp / bay)) + 1 if (comp and bay) else None
    m["secoes"] = sec_nomes
    # esforcos de PROJETO (2a ordem, do calculo) por grupo -> anexa a cada barra.
    # Fonte unica: rodar_galpao capturou o envelope do mesmo a["combos"] da verificacao.
    esf = {"coluna": est.get("esf_coluna"), "rafter": est.get("esf_rafter")}
    for bar in m["barras"]:
        e = esf.get(bar["grupo"])
        if e:
            bar["esforcos"] = dict(e)
        if secao_var and bar["grupo"] in secao_var:   # barra de alma variável
            di, dj, pi, pj_ = secao_var[bar["grupo"]]
            bar["secao_var"] = {"d_i": di, "d_j": dj, "A_i": pi["A"], "I_i": pi["Ix"],
                                "A_j": pj_["A"], "I_j": pj_["Ix"]}
    return m


def analitico_json(modelo, path):
    """Grava o modelo analitico em JSON (intercambio neutro, sempre disponivel)."""
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(modelo, f, ensure_ascii=False, indent=2)
    return path


def resumo(membros):
    """Contagem por tipo (p/ testes/relatorio)."""
    from collections import Counter
    return dict(Counter(m["tipo"] for m in membros))


def _selftest():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    sec = {"col": {"nome": "HEA200", "d": 0.190, "bf": 0.200, "tw": 0.0065, "tf": 0.010},
           "raf": {"nome": "HEA180", "d": 0.171, "bf": 0.180, "tw": 0.006, "tf": 0.0095}}
    M = frame_primario(geo, sec)
    # 40/5=8 -> 9 porticos ; 1 vao -> 2 colunas/portico = 18 colunas ; 2 rafters/portico = 18
    r = resumo(M)
    assert r["Column"] == 18 and r["Beam"] == 18, r
    # coluna da base ao beiral, vertical (so Z varia)
    c = [m for m in M if m["tipo"] == "Column"][0]
    assert c["p1"][2] == 0.0 and abs(c["p2"][2] - 6000.0) < 1e-6
    assert c["p1"][0] == c["p2"][0] and c["p1"][1] == c["p2"][1]
    # rafter sobe do beiral (Z=6000) a cumeeira (Z=7000) e caminha em Y ate o meio
    v = [m for m in M if m["tipo"] == "Beam"][0]
    assert abs(v["p1"][2] - 6000.0) < 1e-6 and abs(v["p2"][2] - 7000.0) < 1e-6
    assert abs(v["p2"][1] - 10000.0) < 1e-6         # cumeeira no meio do vao 20 m
    # multi-vao: 2 vaos -> 3 colunas/portico + 4 rafters/portico
    M2 = frame_primario({"spans": [10.0, 12.0], "comprimento": 30.0, "eave": 6.0,
                         "ridge": 7.5, "bay": 6.0}, sec)
    r2 = resumo(M2)
    # 30/6=5 -> 6 porticos ; 3 colunas -> 18 ; 4 rafters -> 24
    assert r2["Column"] == 18 and r2["Beam"] == 24, r2
    # marcas V1 (1o vao) e V2 (2o vao) distintas
    marcas = {m["marca"] for m in M2 if m["tipo"] == "Beam"}
    assert marcas == {"V1", "V2"}, marcas
    print("modelo_neutro _selftest PASSED")


if __name__ == "__main__":
    _selftest()
