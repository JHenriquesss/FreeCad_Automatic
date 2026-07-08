# ============================================================================
# ligacoes.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica LIGACOES de estrutura de aco (parafusadas e soldadas) pela ABNT
# NBR 8800:2008. Generico e parametrico (qualquer ligacao: joelho viga-coluna,
# emenda, ligacao de contravento, chapa de terca, etc.).
#   - Parafusos (6.3.3): cisalhamento Fv,Rd=0,4*Ab*fub/ga2 (rosca no plano) ou
#     0,5 (fora); tracao Ft,Rd=Abe*fub/ga2 ; pressao de contato/esmagamento
#     Fc,Rd=min(1,2*lf*t*fu ; 2,4*db*t*fu)/ga2 ; interacao tracao+corte
#     (Ft/FtRd)^2+(Fv/FvRd)^2<=1 (6.3.3.4).
#   - Solda de filete (6.2.5): metal da solda Fw,Rd=0,60*fw*Aw/gw2
#     (Aw=0,707*perna*comprimento). Metal-base (Tabela 8 -> 6.5.5): menor entre
#     escoamento 0,60*fy*AMB/ga1 e ruptura 0,60*fu*AMB/ga2.
#   - Forca minima de ligacao 45 kN (6.1.5.2), com as excecoes da norma
#     (tirantes redondos, travessas, TERCAS de cobertura, travejamento).
#   - Detalhamento dos furos (6.3.9/6.3.10/6.3.11): espacamento >= 2,7 db (pref
#     3 db), distancia livre entre furos >= db, espacamento max <= min(24t; 300);
#     lf (do esmagamento 6.3.3.3) DERIVADO da geometria (e_borda/s_furos). A
#     Tabela 14 (furo-borda) fica FLAG (resistencia governada por 6.3.3.3).
# NAO cobre estados-limites da chapa (rasgamento em bloco/flexao) alem do
# esmagamento - FLAG onde aplicavel. Saidas em portugues. Unidades SI: m, kN.
# ============================================================================
"""Verificacao de ligacoes parafusadas e soldadas conforme ABNT NBR 8800:2008."""

from __future__ import annotations

import math

GA2 = 1.35         # ruptura (parafuso/solda de ruptura)
GA1 = 1.10         # escoamento (metal-base)
GW2 = 1.35         # solda (Nota k, Tabela 8)
FORCA_MIN = 45.0   # kN (6.1.5.2)


# ---- parafusos -------------------------------------------------------------
def _area(db):
    Ab = math.pi * db ** 2 / 4.0
    return Ab, 0.75 * Ab            # bruta, efetiva (rosqueada)


def fv_rd(db, fub, rosca_no_plano=True, n_planos=1):
    Ab, _ = _area(db)
    c = 0.4 if rosca_no_plano else 0.5
    return c * Ab * fub / GA2 * n_planos


def ft_rd(db, fub):
    _, Abe = _area(db)
    return Abe * fub / GA2


def fc_rd(db, t, fu, lf):
    """Esmagamento/rasgamento (deformacao limitante, 6.3.3.3)."""
    return min(1.2 * lf * t * fu, 2.4 * db * t * fu) / GA2


def _diam_furo(db):
    """Diametro do furo-padrao (Tabela 12): db + 1,5 mm (db<=24) / db + 1,5 mm
    (>=30 usa +1,5 tambem, conservador para lf). Unidades m."""
    return db + 0.0015


# Tabela 14 (NBR 8800) - distancia minima do centro de furo-padrao a borda [mm],
# por diametro db [mm]: (borda cortada com serra/tesoura ; borda laminada ou cortada
# a macarico). Linhas em pol convertidas p/ mm nominal. LIDO do PDF (pg.94).
_TAB14 = [(12.7, 22.0, 19.0), (16.0, 29.0, 22.0), (19.05, 32.0, 26.0),
          (20.0, 35.0, 27.0), (22.0, 38.0, 29.0), (24.0, 42.0, 31.0),
          (25.4, 44.0, 32.0), (27.0, 50.0, 38.0), (30.0, 53.0, 39.0),
          (31.75, 57.0, 42.0), (36.0, 64.0, 46.0)]


def dist_min_borda(db, borda_cortada=True, baixa_solicitacao=False):
    """Distancia minima do centro do furo a borda (NBR 8800 Tabela 14). db em m.
    borda_cortada=True -> coluna serra/tesoura ; False -> laminada/macarico.
    baixa_solicitacao (nota b): so p/ borda laminada, reduz 3 mm quando Fsd <= 25%
    da forca resistente. Para db > 36 mm: 1,75 db (cortada) / 1,25 db (laminada).
    Retorna a distancia minima em m."""
    dbmm = db * 1000.0
    if dbmm > 36.0 + 1e-9:
        e_mm = 1.75 * dbmm if borda_cortada else 1.25 * dbmm
    else:
        row = next((r for r in _TAB14 if r[0] >= dbmm - 1e-6), _TAB14[-1])
        e_mm = row[1] if borda_cortada else row[2]
        if (not borda_cortada) and baixa_solicitacao:
            e_mm -= 3.0                              # nota b
    return e_mm / 1000.0


def block_shear(Agv, Anv, Ant, fy, fu, Cts=1.0):
    """Colapso por RASGAMENTO EM BLOCO (NBR 8800 6.5.6). Soma da resistencia ao
    cisalhamento de linha(s) de falha + tracao no segmento perpendicular:

      F_r,Rd = (0,60*fu*Anv + Cts*fu*Ant)/ga2  <=  (0,60*fy*Agv + Cts*fu*Ant)/ga2

    Agv = area BRUTA ao cisalhamento ; Anv = area LIQUIDA ao cisalhamento ;
    Ant = area LIQUIDA a tracao ; Cts = 1,0 (tracao uniforme na area liquida) ou
    0,5 (nao-uniforme). Areas em m2, fy/fu em kN/m2. Retorna dict (Frd em kN).
    As AREAS vem da geometria do bloco de falha (o responsavel define o percurso)."""
    r_rup = (0.60 * fu * Anv + Cts * fu * Ant) / GA2      # ruptura ao cisalhamento
    r_esc = (0.60 * fy * Agv + Cts * fu * Ant) / GA2      # escoamento ao cisalhamento
    Frd = min(r_rup, r_esc)
    return {"Frd": Frd, "r_ruptura": r_rup, "r_escoamento": r_esc,
            "governa": "ruptura ao cisalhamento" if r_rup <= r_esc else "escoamento ao cisalhamento",
            "Agv": Agv, "Anv": Anv, "Ant": Ant, "Cts": Cts}


def block_shear_linha(n, s_furos, e_long, e_transv, db, t, fy, fu, Cts=1.0):
    """Rasgamento em bloco para o caso comum: 1 LINHA de n parafusos tracionada
    (chapa de no / barra tracionada), com UM plano de cisalhamento (ao longo da
    linha) + tracao no segmento transversal na extremidade. Percurso assumido
    (FLAG - o responsavel confirma para outros arranjos):
      - comprimento ao cisalhamento Lgv = e_long + (n-1)*s_furos (borda -> ultimo furo)
      - furos no plano de cisalhamento = n (subtrai n*dh na area liquida)
      - tracao transversal Lnt = e_transv (subtrai 1/2 furo)
    e_long = distancia do 1o furo a borda na direcao da forca ; e_transv = distancia
    do furo a borda transversal. Unidades m. Retorna o dict de block_shear."""
    dh = _diam_furo(db)
    Lgv = e_long + (n - 1) * s_furos
    Agv = Lgv * t
    Anv = (Lgv - n * dh) * t
    Ant = max(e_transv - 0.5 * dh, 0.0) * t
    r = block_shear(Agv, max(Anv, 0.0), Ant, fy, fu, Cts)
    r.update(Lgv=Lgv, dh=dh, n=n)
    return r


def verifica_espacamento(db, s_furos, e_borda, t=None, borda_cortada=True):
    """Detalhamento geometrico dos furos (NBR 8800 6.3.9/6.3.10/6.3.11) e a
    distancia livre 'lf' DERIVADA da geometria (alimenta o esmagamento 6.3.3.3).

      - 6.3.9  espacamento entre centros >= 2,7 db (pref. 3 db) ; distancia LIVRE
               entre bordas de furos consecutivos >= db ;
      - 6.3.10 espacamento maximo (chapa pintada) <= min(24 t ; 300 mm) ;
      - lf (para 6.3.3.3): min(e_borda - dh/2 ; s_furos - dh) (distancia livre do
               furo a borda / ao furo vizinho, na direcao da forca), dh do furo.

    db, s_furos (centro a centro), e_borda (centro-borda), t em m. borda_cortada:
    True = serra/tesoura ; False = laminada/macarico (Tabela 14). A distancia minima
    furo-borda (6.3.11 / Tabela 14) AGORA e verificada; o estado-limite de resistencia
    segue o esmagamento 6.3.3.3 (nota a). Retorna dict."""
    dh = _diam_furo(db)
    s_min = 2.7 * db                                 # 6.3.9 (pref 3 db)
    livre_furos = s_furos - dh                       # distancia livre entre furos
    lf_borda = e_borda - dh / 2.0                    # livre furo-extremidade
    lf_inter = s_furos - dh                          # livre furo-furo
    lf = max(min(lf_borda, lf_inter), 0.0)
    e_min_borda = dist_min_borda(db, borda_cortada)  # 6.3.11 / Tabela 14
    r = {"dh": dh, "s_min_2p7db": s_min, "s_furos": s_furos, "e_borda": e_borda,
         "livre_furos": livre_furos, "lf": lf,
         "e_min_borda": e_min_borda, "ok_borda_t14": e_borda >= e_min_borda - 1e-9,
         "ok_espac": s_furos >= s_min - 1e-9,
         "ok_livre": livre_furos >= db - 1e-9,       # distancia livre >= db
         "ok_borda_livre": lf_borda >= 0.0}
    if t:
        s_max = min(24.0 * t, 0.300)                 # 6.3.10 a) pintado
        r["s_max"] = s_max
        r["ok_s_max"] = s_furos <= s_max + 1e-9
        e_max = min(12.0 * t, 0.150)                 # 6.3.12 distancia MAXIMA a borda
        r["e_max_borda"] = e_max
        r["ok_e_max"] = e_borda <= e_max + 1e-9
    r["OK"] = r["ok_espac"] and r["ok_livre"] and r["ok_borda_livre"] and \
        r["ok_borda_t14"] and r.get("ok_s_max", True) and r.get("ok_e_max", True)
    return r


def parafusos(caso):
    n = caso["n"]
    db, fub = caso["db"], caso["fub"]
    t, fu = caso["t_chapa"], caso["fu_chapa"]
    # lf: se a geometria (s_furos + e_borda) for dada, DERIVA lf dela (consistente);
    # senao usa o lf explicito (retrocompativel).
    esp = None
    if caso.get("s_furos") and caso.get("e_borda"):
        esp = verifica_espacamento(db, caso["s_furos"], caso["e_borda"], t,
                                   caso.get("borda_cortada", True))
        lf = esp["lf"]
    else:
        lf = caso["lf"]
    Fvrd = fv_rd(db, fub, caso.get("rosca_no_plano", True), caso.get("n_planos", 1))
    Ftrd = ft_rd(db, fub)
    Fcrd = fc_rd(db, t, fu, lf)
    Vsd = caso.get("V", 0.0) / n
    Nsd = caso.get("N", 0.0) / n           # tracao por parafuso (se houver)
    # resistencia ao corte por parafuso = min(corte, esmagamento)
    Fv_lim = min(Fvrd, Fcrd)
    inter = (Nsd / Ftrd) ** 2 + (Vsd / Fvrd) ** 2 if Nsd > 0 else Vsd / Fv_lim
    ok_esp = (esp["OK"] if esp else True)
    return {"tipo": "parafusos", "n": n, "Fv_Rd": Fvrd, "Ft_Rd": Ftrd,
            "Fc_Rd": Fcrd, "Fv_lim": Fv_lim, "Vsd": Vsd, "Nsd": Nsd, "lf": lf,
            "u_corte": Vsd / Fv_lim, "u_tracao": (Nsd / Ftrd) if Nsd else 0.0,
            "espacamento": esp,
            "interacao": inter, "OK": inter <= 1.0 and (Vsd / Fv_lim) <= 1.0
            and ok_esp}


# ---- solda de filete -------------------------------------------------------
def fw_rd_filete(perna, Lw, fw):
    """Metal da solda (6.2.5): garganta = 0,707*perna."""
    Aw = 0.707 * perna * Lw
    return 0.60 * fw * Aw / GW2, Aw


def fw_rd_base(t_base, Lw, fy, fu=None):
    """Metal-base ao cisalhamento (Tabela 8 filete -> 6.5.5): menor entre
    escoamento 0,60*fy*Ag/ga1 e ruptura 0,60*fu*Anv/ga2. Ao longo da solda nao
    ha furos -> Anv=Ag=AMB. Sem fu -> so escoamento (retrocompativel)."""
    AMB = t_base * Lw
    Fesc = 0.60 * fy * AMB / GA1
    if fu is None:
        return Fesc
    Frup = 0.60 * fu * AMB / GA2
    return min(Fesc, Frup)


def solda(caso):
    perna, Lw, fw = caso["perna"], caso["Lw"], caso["fw"]
    Fw, Aw = fw_rd_filete(perna, Lw, fw)
    Fb = fw_rd_base(caso["t_base"], Lw, caso["fy_base"], caso.get("fu_base"))
    Frd = min(Fw, Fb)
    Fsd = caso["F"]
    return {"tipo": "solda", "Aw": Aw, "Fw_metal": Fw, "Fw_base": Fb,
            "Fw_Rd": Frd, "Fsd": Fsd, "u": Fsd / Frd, "OK": Fsd <= Frd,
            "governa": "metal-base" if Fb < Fw else "metal da solda"}


# ---- forca minima 6.1.5.2 --------------------------------------------------
def forca_minima(Fsd, excecao=False):
    """Retorna a forca de dimensionamento (>=45 kN) e se foi governada pelo
    minimo. excecao=True para tirantes redondos, travessas, TERCAS, travejamento."""
    if excecao:
        return Fsd, False
    if abs(Fsd) < FORCA_MIN:
        return FORCA_MIN, True
    return Fsd, False


def verifica_ligacao(caso):
    Fsd_orig = caso.get("F", caso.get("V", 0.0))
    Fdim, governou = forca_minima(Fsd_orig, caso.get("excecao_terca", False))
    caso = dict(caso)
    # aplica a forca de dimensionamento minima ao esforco principal
    if governou:
        if "F" in caso:
            caso["F"] = Fdim
        else:
            caso["V"] = Fdim
    r = solda(caso) if caso["tipo"] == "solda" else parafusos(caso)
    r["nome"] = caso.get("nome", "ligacao")
    r["forca_dim"] = Fdim
    r["min_governou"] = governou
    return r


# Escada da ligacao de momento do joelho (n parafusos, db, t_chapa) em m.
ESCADA_JOELHO = [
    (4, 0.020, 0.0125),
    (4, 0.024, 0.0160),        # referencia
    (6, 0.024, 0.0190),
    (6, 0.027, 0.0220),
    (8, 0.027, 0.0250),
    (8, 0.030, 0.0315),
]


def dimensiona_ligacao(caso, escada=None):
    """Escolhe a ligacao de momento (n parafusos, db, t_chapa) MAIS LEVE que passa
    (interacao<=1) sob o esforco do caso (N tracao da mesa, V). Parte do seed.
    Retorna {aprovado:(n,db,t,r,caso)|None, linhas, tabela}."""
    escada = escada or ESCADA_JOELHO
    seed = (int(caso["n"]), round(caso["db"], 3), round(caso["t_chapa"], 4))
    cand = list(escada)
    if seed not in cand:
        cand = [seed] + cand
    linhas, aprovado = [], None
    for (n, db, t) in cand:
        c = dict(caso)
        c.update(n=n, db=db, t_chapa=t, lf=caso.get("lf", 1.5 * db))
        r = parafusos(c)
        linhas.append((n, db, t, r))
        if r["OK"] and aprovado is None:
            aprovado = (n, db, t, r, c)
    return {"aprovado": aprovado, "linhas": linhas,
            "tabela": _tabela_ligacao(linhas, aprovado, caso)}


def _tabela_ligacao(linhas, aprovado, caso):
    L = ["=" * 68, "DIMENSIONAMENTO DA LIGACAO DE MOMENTO (JOELHO)",
         "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL", "=" * 68, "",
         f"Esforco: N(tracao mesa)={caso.get('N',0):.1f} kN ; V={caso.get('V',0):.1f} kN",
         "Criterio: interacao (Nsd/Ft,Rd)^2+(Vsd/Fv,Rd)^2 <= 1 ; corte<=1.", "",
         f"{'n':>2} {'db(mm)':>6} {'t(mm)':>5} | {'u.trac':>6} {'u.corte':>7}"
         f" {'inter':>6} | resultado", "-" * 68]
    for (n, db, t, r) in linhas:
        tag = "PASSA" if r["OK"] else "nao passa"
        L.append(f"{n:>2} {db*1000:6.0f} {t*1000:5.1f} | {r['u_tracao']:6.2f}"
                 f" {r['u_corte']:7.2f} {r['interacao']:6.2f} | {tag}")
    L += ["-" * 68, ""]
    if aprovado:
        n, db, t = aprovado[:3]
        L += [f"ADOTADA: {n} parafusos d{db*1000:.0f} mm ; chapa de topo {t*1000:.0f} mm"]
    else:
        L += ["NENHUMA ligacao da escada passou - ampliar a escada ou rever o no."]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def relatorio_pt(rs):
    L = ["VERIFICACAO DE LIGACOES (ABNT NBR 8800:2008 - 6.2 / 6.3 / 6.1.5)"]
    for r in rs:
        L += ["", f"  --- {r['nome']} ({r['tipo']}) ---"]
        if r["min_governou"]:
            L.append(f"    Forca de dimensionamento = 45,0 kN (minimo 6.1.5.2)")
        if r["tipo"] == "parafusos":
            L += [f"    n={r['n']} parafusos ; Fv,Rd={r['Fv_Rd']:.1f} ; "
                  f"Ft,Rd={r['Ft_Rd']:.1f} ; Fc,Rd(esmag.)={r['Fc_Rd']:.1f} kN",
                  f"    por parafuso: V={r['Vsd']:.1f} ; N={r['Nsd']:.1f} kN ; "
                  f"corte/min(Fv,Fc)={r['u_corte']:.2f} ; tracao={r['u_tracao']:.2f}",
                  f"    interacao/util = {r['interacao']:.2f}  -> "
                  f"{'OK' if r['OK'] else 'NAO PASSA'}"]
            esp = r.get("espacamento")
            if esp is not None:
                L += [f"    Detalhamento (6.3.9/10/11): s={esp['s_furos']*1000:.0f} mm "
                      f"(>=2,7db={esp['s_min_2p7db']*1000:.0f}: {'OK' if esp['ok_espac'] else 'NAO'}) ; "
                      f"livre entre furos={esp['livre_furos']*1000:.0f} mm "
                      f"(>=db: {'OK' if esp['ok_livre'] else 'NAO'}) ; lf={esp['lf']*1000:.0f} mm",
                      "    [FLAG] distancia furo-borda pela Tabela 14 (borda cortada x "
                      "laminada) = confirmar; resistencia governada por 6.3.3.3 (esmag.)."]
        else:
            L += [f"    Aw={r['Aw']*1e4:.2f} cm2 ; metal solda={r['Fw_metal']:.1f} ; "
                  f"metal-base={r['Fw_base']:.1f} -> Fw,Rd={r['Fw_Rd']:.1f} kN "
                  f"(governa {r['governa']})",
                  f"    Fsd={r['Fsd']:.1f} kN ; util={r['u']:.2f}  -> "
                  f"{'OK' if r['OK'] else 'NAO PASSA'}"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # parafuso: Fv,Rd = 0,4*Ab*fub/1,35
    Ab, _ = _area(0.016)
    assert abs(fv_rd(0.016, 800e3) - 0.4 * Ab * 800e3 / 1.35) < 1e-6
    # solda: Fw = 0,60*fw*0,707*perna*L/1,35
    Fw, Aw = fw_rd_filete(0.006, 0.200, 485e3)
    assert abs(Fw - 0.60 * 485e3 * Aw / 1.35) < 1e-6
    # metal-base filete (6.5.5): menor entre escoamento e ruptura
    AMB = 0.008 * 0.200
    esc, rup = 0.60 * 250e3 * AMB / 1.10, 0.60 * 400e3 * AMB / 1.35
    assert abs(fw_rd_base(0.008, 0.200, 250e3, 400e3) - min(esc, rup)) < 1e-6
    assert abs(fw_rd_base(0.008, 0.200, 250e3) - esc) < 1e-6   # sem fu -> escoamento
    # forca minima
    assert forca_minima(30.0)[0] == 45.0 and forca_minima(30.0, excecao=True)[0] == 30.0
    # espacamento (6.3.9/10/11) + lf derivado da geometria. db=20, dh=21,5.
    esp = verifica_espacamento(0.020, s_furos=0.060, e_borda=0.035, t=0.0125)
    assert abs(esp["dh"] - 0.0215) < 1e-9
    assert esp["ok_espac"]                          # 60 >= 2,7*20=54 mm
    assert esp["ok_livre"]                          # 60-21,5=38,5 >= 20 mm
    assert abs(esp["lf"] - min(0.035 - 0.0215 / 2, 0.060 - 0.0215)) < 1e-9
    # Tabela 14 (6.3.11): db=20 borda cortada -> e_min=35 mm ; e_borda=35 -> OK
    assert abs(dist_min_borda(0.020, borda_cortada=True) - 0.035) < 1e-9
    assert abs(dist_min_borda(0.020, borda_cortada=False) - 0.027) < 1e-9
    assert abs(dist_min_borda(0.040, borda_cortada=True) - 1.75 * 0.040) < 1e-9  # >36mm
    assert esp["ok_borda_t14"] and esp["OK"]
    # e_borda insuficiente pela Tabela 14 reprova (db24 cortada precisa 42 mm)
    esp3 = verifica_espacamento(0.024, s_furos=0.070, e_borda=0.035, t=0.0125)
    assert not esp3["ok_borda_t14"] and not esp3["OK"]      # 35 < 42 mm
    # espacamento apertado reprova (s < 2,7 db)
    esp2 = verifica_espacamento(0.020, s_furos=0.045, e_borda=0.030)
    assert not esp2["ok_espac"] and not esp2["OK"]  # 45 < 54 mm
    # parafusos deriva lf da geometria quando s_furos/e_borda dados
    p = parafusos({"n": 4, "db": 0.020, "fub": 825e3, "t_chapa": 0.0125,
                   "fu_chapa": 400e3, "V": 200.0, "s_furos": 0.060, "e_borda": 0.035})
    assert p["espacamento"] is not None and abs(p["lf"] - esp["lf"]) < 1e-9
    # rasgamento em bloco (6.5.6): F_r,Rd = min(0,6fu*Anv+Cts*fu*Ant ; 0,6fy*Agv+Cts*fu*Ant)/ga2
    bs = block_shear(Agv=6e-4, Anv=4e-4, Ant=2e-4, fy=250e3, fu=400e3, Cts=1.0)
    rup = (0.60 * 400e3 * 4e-4 + 1.0 * 400e3 * 2e-4) / 1.35
    esc = (0.60 * 250e3 * 6e-4 + 1.0 * 400e3 * 2e-4) / 1.35
    assert abs(bs["Frd"] - min(rup, esc)) < 1e-6, bs
    assert bs["governa"] in ("ruptura ao cisalhamento", "escoamento ao cisalhamento")
    # helper de linha: 3 furos db20, s=60, e_long=35, e_transv=40, t=12,5
    bl = block_shear_linha(3, 0.060, 0.035, 0.040, 0.020, 0.0125, 250e3, 400e3)
    Lgv = 0.035 + 2 * 0.060
    assert abs(bl["Lgv"] - Lgv) < 1e-9 and bl["Frd"] > 0
    print("ligacoes self-test PASSED")
    print(f"  Fv,Rd(d16, fub800) = {fv_rd(0.016,800e3):.1f} kN")
    print(f"  Fw,Rd filete 6mm x 200mm (fw=485) metal = {Fw:.1f} kN")


# ---- exemplos PLACEHOLDER (a skill pergunta ao usuario) --------------------
EXEMPLOS = [
    {"nome": "Joelho viga-coluna (parafusos M20 A325)", "tipo": "parafusos",
     "n": 6, "db": 0.020, "fub": 825e3, "t_chapa": 0.0125, "fu_chapa": 400e3,
     "s_furos": 0.060, "e_borda": 0.035, "V": 130.0, "N": 90.0, "rosca_no_plano": True},
    {"nome": "Chapa de terca (parafusos M12) - excecao terca", "tipo": "parafusos",
     "n": 2, "db": 0.012, "fub": 400e3, "t_chapa": 0.006, "fu_chapa": 400e3,
     "lf": 0.025, "V": 8.0, "excecao_terca": True},
    {"nome": "Ligacao de contravento (solda filete)", "tipo": "solda",
     "perna": 0.006, "Lw": 0.240, "fw": 485e3, "t_base": 0.008, "fy_base": 250e3,
     "fu_base": 400e3, "F": 45.0},
]


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt([verifica_ligacao(c) for c in EXEMPLOS]))
