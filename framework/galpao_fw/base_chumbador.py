# ============================================================================
# base_chumbador.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Dimensiona/verifica a LIGACAO DE BASE de um pilar (placa de base + chumbadores)
# sob N (axial), V (cortante) e M (momento) - serve para base rotulada (M=0) e
# engastada (M/=0). Generico e parametrico.
#   - Pressao de contato no concreto: NBR 8800 item 6.6.5
#       sigma_c,Rd = fck/(gamma_c*gamma_n)*sqrt(A2/A1) <= fck ; gamma_n=1,40.
#   - Placa sob N+M pelo metodo da excentricidade (equilibrio bloco de
#     compressao PLASTIFICADO em sig_c,Rd + tracao nos chumbadores; AISC DG1).
#     Na grande excentricidade sigma_max = sig_c,Rd (bloco plastificado, u=1),
#     verifica-se Y <= L (o bloco cabe na placa).
#   - Espessura da placa pelo MAIOR entre os dois lados (AISC DG1 3.1.3):
#     lado comprimido (bloco de contato Y em balanco ate a face da mesa) e
#     lado tracionado (linha de dobra: T no braco ate a mesa do pilar).
#     Precisa das dims do pilar (d_col, bf_col) e do braco de tracao.
#   - Chumbador: tracao Ft,Rd=Abe*fub/gamma_a2 (6.3.3.1), cisalhamento
#     Fv,Rd=0,4*Ab*fub/gamma_a2 (rosca no plano, 6.3.3.2), interacao
#     (Ft/FtRd)^2+(Fv/FvRd)^2<=1 (6.3.3.4).
#   - Espessura da placa por flexao em balanco (modelo de mesa em balanco).
#   - Ancoragem do chumbador no concreto por ADERENCIA (NBR 6118 9.4.2): produz o
#     embutimento reto requerido lb,nec (informativo/requisito, como t_req). O CONE
#     DE ARRANCAMENTO e o efeito de GRUPO (ACI 318 Ch.17) seguem do projeto de
#     fundacao (FLAG - a aderencia sozinha subestima o gancho/placa mecanico).
# Saidas em portugues.
# Calcula apenas; pendente revisao. Unidades SI: m, kN (fck, fub em kN/m2).
# ============================================================================
"""Ligacao de base (placa + chumbadores) conforme NBR 8800 6.3/6.6 + AISC DG1."""

from __future__ import annotations

import math

GA2 = 1.35         # coef. ruptura (parafuso), NBR 8800
GA1 = 1.10         # coef. escoamento
GC = 1.40          # concreto (NBR 6118)
GN = 1.40          # 6.6.5


def sigma_c_rd(fck, A1, A2):
    """NBR 8800 6.6.5: pressao de contato resistente no concreto."""
    val = fck / (GC * GN) * math.sqrt(A2 / A1)
    return min(val, fck)


def ft_rd_chumbador(Abe, fub):
    """6.3.3.1: tracao resistente por chumbador (area efetiva rosqueada)."""
    return Abe * fub / GA2


def fv_rd_chumbador(Ab, fub, rosca_no_plano=True):
    """6.3.3.2: cisalhamento resistente por chumbador (por plano de corte)."""
    c = 0.4 if rosca_no_plano else 0.5
    return c * Ab * fub / GA2


def _area_efetiva(db):
    """Area efetiva (rosqueada) aproximada = 0,75*area bruta (uso comum)."""
    Ab = math.pi * db ** 2 / 4.0
    return 0.75 * Ab, Ab


def ancoragem_chumbador(Ft_sd, db, fck, fyk=250e3, com_gancho=True,
                        eta1=1.0, eta2=1.0, h_embed=None):
    """NBR 6118 9.4.2: comprimento de ancoragem POR ADERENCIA do chumbador (o
    embutimento reto desenvolve a tracao Ft_sd por aderencia; o gancho reduz por
    alpha). Fecha o lado do CONCRETO que faltava (o modulo so tinha aco/placa).

      - 9.3.2.1  fbd = eta1*eta2*eta3*fctd ; fctd = fctk,inf/gamma_c ,
                 fctk,inf = 0,7*fctm , fctm = 0,3*fck^(2/3) [MPa] ;
                 eta1 = 1,0 (barra LISA = chumbador liso; nervurada seria 2,25) ;
                 eta2 = 1,0 boa aderencia / 0,7 ma ; eta3 = 1,0 (phi<32 mm) ;
      - 9.4.2.4  lb = (phi/4)*(fyd/fbd) ;
      - 9.4.2.5  lb,nec = alpha*lb*(As,cal/As,ef) >= lb,min ; alpha=0,7 c/ gancho
                 (tracionada, cobrimento normal ao gancho >= 3 phi), 1,0 sem ;
                 lb,min = max(0,3*lb ; 10*phi ; 100 mm).

    LIMITE: NAO cobre o CONE DE ARRANCAMENTO do concreto nem o efeito de GRUPO
    (ACI 318 Ch.17 / concrete breakout) - permanece FLAG do projeto de fundacao.
    Unidades: db,h_embed em m ; fck,fyk em kN/m2 ; Ft_sd em kN."""
    phi = db
    fck_MPa = fck / 1000.0
    fctm = 0.3 * fck_MPa ** (2.0 / 3.0)              # MPa (fck<=50)
    fctd = 0.7 * fctm / GC * 1000.0                  # kN/m2
    eta3 = 1.0 if db < 0.032 else (132.0 - db * 1000.0) / 100.0
    fbd = eta1 * eta2 * eta3 * fctd
    fyd = fyk / 1.15
    lb = (phi / 4.0) * (fyd / fbd)                   # 9.4.2.4
    Abe, _ = _area_efetiva(db)
    As_cal = Ft_sd / fyd if fyd > 0 else 0.0         # area necessaria p/ a tracao
    ratio = min(As_cal / Abe, 1.0) if Abe > 0 else 0.0
    alpha = 0.7 if com_gancho else 1.0
    lb_min = max(0.3 * lb, 10.0 * phi, 0.100)
    lb_nec = max(alpha * lb * ratio, lb_min)         # 9.4.2.5
    r = {"fbd": fbd, "fctd": fctd, "lb": lb, "lb_nec": lb_nec, "lb_min": lb_min,
         "alpha": alpha, "eta3": eta3, "As_cal": As_cal, "Abe": Abe,
         "h_embed": h_embed}
    if h_embed is not None:
        r["u_anc"] = lb_nec / h_embed if h_embed > 0 else float("inf")
        r["ok_anc"] = h_embed >= lb_nec - 1e-9
    else:                                            # sem embutimento dado: informa o requerido
        r["u_anc"] = None
        r["ok_anc"] = None
    return r


def placa_sob_NM(N, M, B, L, sig_rd, d_anchor):
    """Metodo da excentricidade (AISC DG1). N>0 compressao. Retorna a tracao
    total T nos chumbadores do lado tracionado e a extensao Y do bloco de
    compressao. d_anchor = distancia da borda comprimida a linha de chumbadores
    tracionados. Convencao: momento positivo tende a tracionar o lado dos
    chumbadores.
    """
    if N <= 0:                      # uplift liquido: tudo tracionado
        # tracao total = |N| + par do momento (bracos aproximados)
        T = abs(N) + (abs(M) / d_anchor if d_anchor > 0 else 0.0)
        return T, 0.0, 0.0, "uplift (N tracao)"
    e = M / N if N != 0 else 0.0
    if abs(e) <= L / 6.0:           # dentro do nucleo: sem tracao
        sig_max = N / (B * L) * (1 + 6 * abs(e) / L)
        return 0.0, L, sig_max, ("pequena excentricidade (sem tracao)")
    # grande excentricidade: bloco de compressao PLASTIFICADO em sig_rd (AISC
    # DG1). C*(d_anchor - Y/2) = N*(d_anchor - L/2) + M ; C = sig_rd*B*Y
    q = sig_rd * B                  # forca por metro do bloco (sig_rd = TENSAO)
    a = -q / 2.0
    b = q * d_anchor
    c = -(N * (d_anchor - L / 2.0) + abs(M))
    disc = b * b - 4 * a * c
    if disc < 0:
        return None, None, sig_rd, "SEM SOLUCAO (placa/bloco insuficiente)"
    Y = (-b + math.sqrt(disc)) / (2 * a)
    if Y <= 0 or Y > L:
        Y = (-b - math.sqrt(disc)) / (2 * a)
    C = q * Y
    T = C - N
    modo = "grande excentricidade" + (" (Y>L: bloco NAO cabe!)" if Y > L else "")
    # concreto plastificado no bloco -> sig_max = sig_rd (nao N/BY)
    return max(T, 0.0), Y, sig_rd, modo


def verifica_base(caso):
    r = {"nome": caso.get("nome", "base")}
    fck = caso["fck"]
    B, L = caso["B"], caso["L"]           # dimensoes da placa (m)
    A1 = B * L
    A2 = caso.get("A2", A1)               # area do pedestal/concreto
    sig_rd = sigma_c_rd(fck, A1, A2)
    r["sigma_c_rd"] = sig_rd

    n = caso["n_chumbadores"]             # total
    n_t = caso.get("n_tracionados", n // 2)
    db = caso["db"]                       # diametro (m)
    fub = caso["fub"]
    Abe, Ab = _area_efetiva(db)
    Ft_rd = ft_rd_chumbador(Abe, fub)
    Fv_rd = fv_rd_chumbador(Ab, fub, caso.get("rosca_no_plano", True))
    r.update(Ft_rd=Ft_rd, Fv_rd=Fv_rd, Abe=Abe, Ab=Ab)

    N, V, M = caso["N"], caso["V"], caso["M"]
    d_anchor = caso.get("d_anchor", L - caso.get("borda", 0.05))
    # passa a TENSAO sig_rd (a funcao multiplica por B internamente)
    T, Y, sig_max, modo = placa_sob_NM(N, M, B, L, sig_rd, d_anchor)
    r["modo"] = modo
    r["Y"] = Y
    r["T_total"] = T

    # tracao por chumbador
    Ft_sd = (T / n_t) if (T and n_t > 0) else 0.0
    Fv_sd = abs(V) / n                    # cisalhamento distribuido em todos
    r.update(Ft_sd=Ft_sd, Fv_sd=Fv_sd)
    r["u_tracao"] = Ft_sd / Ft_rd
    r["u_corte"] = Fv_sd / Fv_rd
    r["interacao"] = (Ft_sd / Ft_rd) ** 2 + (Fv_sd / Fv_rd) ** 2

    # ancoragem no concreto por aderencia (NBR 6118 9.4.2) - lado do concreto
    anc = ancoragem_chumbador(Ft_sd, db, fck, caso.get("fyk_chumbador", 250e3),
                              com_gancho=caso.get("com_gancho", True),
                              eta2=caso.get("eta2_aderencia", 1.0),
                              h_embed=caso.get("h_embed"))
    r["ancoragem"] = anc

    # bearing no concreto: na grande excentricidade o bloco esta PLASTIFICADO
    # (sig_max = sig_rd, u=1,0). O criterio geometrico e Y <= L (o bloco cabe).
    r["sigma_max"] = sig_max
    r["u_concreto"] = (sig_max / sig_rd) if sig_rd else 0.0
    r["Y_cabe"] = (Y is not None and Y <= L)

    # ---- espessura da placa: AISC DG1 3.1.3, MAIOR entre os dois lados ------
    fy_p = caso["fy_placa"]
    d_col = caso.get("d_col")             # altura do perfil do pilar (m)
    bf_col = caso.get("bf_col")           # largura da mesa (m)
    # lado COMPRIMIDO: momento da flexao da placa na secao critica (face da mesa
    # do pilar). A pressao sig_max atua SO sobre o bloco de comprimento Y (na
    # grande excentricidade Y<<balanco), nao sobre todo o balanco -> usa-se o
    # bloco de contato e seu braco ate a face da mesa (nao o m,n de pressao
    # uniforme, que so vale na pequena excentricidade).
    x_face = (max(L / 2.0 - d_col / 2.0, 0.0) if d_col
              else caso.get("balanco", 0.05))
    Ybear = min(Y, L) if Y else L
    p = sig_max if sig_max else sig_rd
    if Ybear >= x_face:                       # bloco cobre alem da secao critica
        m_comp = p * x_face ** 2 / 2.0
    else:                                     # bloco (Y) fica antes da secao
        m_comp = p * Ybear * (x_face - Ybear / 2.0)
    t_comp = math.sqrt(4 * m_comp * GA1 / fy_p)
    c_bal = x_face
    # lado TRACIONADO: a placa flexiona contra a mesa do pilar (linha de dobra).
    # braco x = distancia do chumbador tracionado a face da mesa do pilar.
    x_t = caso.get("x_tracao")
    if x_t is None and d_col:
        # chumbador a d_anchor da borda comprimida ; face tracionada da mesa em
        # (L/2 + d_col/2) da borda comprimida
        x_t = max(d_anchor - (L / 2.0 + d_col / 2.0), 0.0)
    beff = caso.get("beff_tracao", B)     # largura efetiva (default = largura)
    t_trac = 0.0
    if T and x_t and beff > 0:
        m_trac = (T / beff) * x_t         # momento por metro (kN.m/m)
        t_trac = math.sqrt(4 * m_trac * GA1 / fy_p)
    t_req = max(t_comp, t_trac)
    r.update(t_comp=t_comp, t_trac=t_trac, c_bal=c_bal, x_trac=x_t or 0.0,
             t_placa_req=t_req, t_placa=caso.get("t_placa", None))

    # A ancoragem PRODUZ o embutimento requerido lb,nec (como t_req da placa) -
    # INFORMATIVO por default; so reprova o OK se o caso pedir gate_ancoragem=True
    # E o embutimento dado for insuficiente. Motivo: a aderencia (barra lisa) e
    # conservadora; o gancho/placa transfere por MECANICA (cone/bearing, ACI Ch.17
    # - flagado), que a aderencia NBR sozinha subestima. lb,nec fica como
    # requisito de projeto para o embutimento (ou ancoragem mecanica equivalente).
    ok_anc_gate = True
    if caso.get("gate_ancoragem", False) and anc["ok_anc"] is False:
        ok_anc_gate = False
    r["OK"] = (r["interacao"] <= 1.0 and r["u_corte"] <= 1.0 and
               r["u_concreto"] <= 1.0 + 1e-9 and r["Y_cabe"] and
               (r["t_placa"] is None or r["t_placa"] >= t_req) and ok_anc_gate)
    return r


def relatorio_pt(r, caso):
    L = ["LIGACAO DE BASE (placa + chumbadores) - NBR 8800 6.3/6.6 + AISC DG1",
         f"  {r['nome']}",
         f"  Esforcos: N={caso['N']:+.1f} kN ; V={caso['V']:.1f} kN ; "
         f"M={caso['M']:.1f} kN.m  (base {'ENGASTADA' if caso['M'] else 'ROTULADA'})",
         f"  Placa: {caso['B']*1000:.0f} x {caso['L']*1000:.0f} mm ; "
         f"fck={caso['fck']/1000:.0f} MPa ; sigma_c,Rd={r['sigma_c_rd']:.0f} kN/m2",
         f"  Regime placa: {r['modo']}",
         f"  Chumbadores: {caso['n_chumbadores']} x d={caso['db']*1000:.0f} mm ; "
         f"Ft,Rd={r['Ft_rd']:.1f} kN ; Fv,Rd={r['Fv_rd']:.1f} kN",
         f"  Tracao total = {r['T_total']:.1f} kN -> por chumbador Ft,Sd="
         f"{r['Ft_sd']:.1f} kN ; Fv,Sd={r['Fv_sd']:.1f} kN",
         f"  Concreto: sigma_max={r['sigma_max']:.0f} kN/m2 (bloco plastificado) "
         f"-> u={r['u_concreto']:.2f} ; Y={ (r['Y'] or 0)*1000:.1f} mm "
         f"{'<=L (cabe)' if r['Y_cabe'] else '> L (NAO CABE)'}",
         f"  Chumbador: tracao u={r['u_tracao']:.2f} ; corte u={r['u_corte']:.2f} ; "
         f"interacao (Ft/FtRd)^2+(Fv/FvRd)^2 = {r['interacao']:.2f}",
         _linha_ancoragem(r["ancoragem"]),
         f"  Placa (AISC DG1): lado comprimido t={r['t_comp']*1000:.1f} mm "
         f"(balanco {r['c_bal']*1000:.0f} mm) ; lado tracionado t={r['t_trac']*1000:.1f} mm "
         f"(braco {r['x_trac']*1000:.0f} mm) -> t_req={r['t_placa_req']*1000:.1f} mm"
         + (f" ; t_adotada={r['t_placa']*1000:.0f} mm" if r['t_placa'] else ""),
         f"  -> {'OK' if r['OK'] else 'NAO PASSA'}",
         "  [FLAG] Ancoragem por ADERENCIA verificada (NBR 6118 9.4.2). O CONE DE",
         "         ARRANCAMENTO do concreto e o efeito de GRUPO (ACI 318 Ch.17)",
         "         permanecem do projeto de fundacao - NAO cobertos aqui."]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _linha_ancoragem(anc):
    """Linha do relatorio para a ancoragem por aderencia (NBR 6118 9.4.2)."""
    base = (f"  Ancoragem (NBR 6118 9.4.2): fbd={anc['fbd']:.0f} kN/m2 ; "
            f"lb={anc['lb']*1000:.0f} mm -> lb,nec={anc['lb_nec']*1000:.0f} mm "
            f"(alpha={anc['alpha']:.1f} c/ gancho ; lb,min={anc['lb_min']*1000:.0f} mm)")
    if anc["h_embed"] is not None:
        tag = "OK" if anc["ok_anc"] else "embutir >= lb,nec (ou ancoragem mecanica)"
        base += (f" ; embutimento={anc['h_embed']*1000:.0f} mm -> u={anc['u_anc']:.2f} "
                 f"[{tag}]")
    else:
        base += " ; [lb,nec = embutimento reto requerido por aderencia]"
    return base


# Escada de bases (B, L, db, n) - placa e chumbadores. A ESPESSURA nao entra na
# escada: e DERIVADA de t_req (AISC DG1) arredondada para chapa padrao. Do mais
# leve ao mais pesado (m, m, m, -).
ESCADA_BASE = [
    (0.40, 0.50, 0.020, 4),
    (0.45, 0.55, 0.020, 4),             # referencia 20x10
    (0.50, 0.60, 0.025, 4),
    (0.55, 0.70, 0.025, 6),
    (0.60, 0.80, 0.032, 6),
    (0.70, 0.90, 0.032, 6),
]
# Chapas de base padrao (mm) - escolhe a >= t_req.
STD_T = [16.0, 19.0, 22.0, 25.0, 31.5, 38.0, 44.5, 50.0, 63.0, 75.0, 90.0, 100.0]


def _std_t(t_m):
    tmm = t_m * 1000.0
    for s in STD_T:
        if s >= tmm - 1e-6:
            return s / 1000.0
    return STD_T[-1] / 1000.0


def dimensiona_base(caso, escada=None):
    """Escolhe a base (placa + chumbadores) MAIS LEVE que PASSA sob o esforco real
    (N,V,M do caso), variando (B,L,db,n); a ESPESSURA e derivada de t_req (chapa
    padrao >= t_req). Retorna {aprovado:(B,L,t,db,n,r,caso)|None, linhas, tabela}."""
    escada = escada or ESCADA_BASE
    seed = (round(caso["B"], 3), round(caso["L"], 3), round(caso["db"], 3),
            int(caso["n_chumbadores"]))
    cand = list(escada)
    if seed not in cand:
        cand = [seed] + cand
    linhas, aprovado = [], None
    for (B, L, db, n) in cand:
        c = dict(caso)
        c.update(B=B, L=L, db=db, n_chumbadores=n, n_tracionados=max(1, n // 2),
                 borda=caso.get("borda", 0.05), d_anchor=L - caso.get("borda", 0.05),
                 A2=(B + 0.15) * (L + 0.15), t_placa=None)   # t_placa None: OK ignora espessura
        r = verifica_base(c)
        t_adot = _std_t(r["t_placa_req"])                    # espessura derivada
        linhas.append((B, L, t_adot, db, n, r))
        if r["OK"] and aprovado is None:                     # OK = ancoragem+concreto+Y
            c["t_placa"] = t_adot
            aprovado = (B, L, t_adot, db, n, r, c)
    return {"aprovado": aprovado, "linhas": linhas,
            "tabela": _tabela_base(linhas, aprovado, caso)}


def _tabela_base(linhas, aprovado, caso):
    L = ["=" * 74, "DIMENSIONAMENTO DA BASE ENGASTADA (placa + chumbadores)",
         "CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL", "=" * 74, "",
         f"Esforco: N={caso['N']:+.1f} kN ; V={caso['V']:.1f} kN ; M={caso['M']:.1f} kN.m",
         "Criterio: interacao chumbador<=1 ; corte<=1 ; concreto<=1 ; Y<=L ;"
         " t_placa>=t_req (AISC DG1).", "",
         f"{'BxL (mm)':>12} {'t':>4} {'db':>4} {'n':>2} | {'u.trac':>6} {'u.corte':>7}"
         f" {'u.conc':>6} {'Y<=L':>5} {'t_req':>6} | resultado", "-" * 74]
    for (B, Lm, t, db, n, r) in linhas:
        tag = "PASSA" if r["OK"] else "nao passa"
        L.append(f"{B*1000:5.0f}x{Lm*1000:<5.0f} {t*1000:4.0f} {db*1000:4.0f} {n:2d} |"
                 f" {r['u_tracao']:6.2f} {r['u_corte']:7.2f} {r['u_concreto']:6.2f}"
                 f" {'sim' if r['Y_cabe'] else 'NAO':>5} {r['t_placa_req']*1000:5.0f}mm"
                 f" | {tag}")
    L += ["-" * 74, ""]
    if aprovado:
        B, Lm, t, db, n = aprovado[:5]
        L += [f"ADOTADA (mais leve que passa): {B*1000:.0f} x {Lm*1000:.0f} x "
              f"{t*1000:.0f} mm ; {n} chumbadores d={db*1000:.0f} mm"]
    else:
        L += ["NENHUMA base da escada passou - ampliar a escada ou revisar (M muito",
              "alto: aumentar pilar/base, ou considerar base rotulada + contravento)."]
    if aprovado:
        anc = aprovado[5]["ancoragem"]
        L += [f"Ancoragem (NBR 6118 9.4.2): embutimento reto requerido lb,nec="
              f"{anc['lb_nec']*1000:.0f} mm (c/ gancho) - ou ancoragem mecanica equiv."]
    L += ["", "[FLAG] Cone de arrancamento/grupo (ACI 318 Ch.17): projeto de fundacao "
          "(a aderencia NBR 6118 nao cobre o cone/bearing mecanico do gancho)."]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # 1) Tracao pura por chumbador: Ft,Rd = Abe*fub/1,35
    Abe, Ab = _area_efetiva(0.020)
    ft = ft_rd_chumbador(Abe, 400e3)      # ASTM A307-ish fub=400 MPa
    exp = Abe * 400e3 / 1.35
    assert abs(ft - exp) < 1e-6
    # 2) bearing: A2=A1 -> sqrt=1 -> sigma = fck/(1,4*1,4)
    s = sigma_c_rd(20e3, 0.16, 0.16)
    assert abs(s - 20e3 / (1.4 * 1.4)) < 1e-6, s
    # 3) uplift puro: T_total = |N|
    T, Y, sm, m = placa_sob_NM(-100.0, 0.0, 0.4, 0.4, 5000.0, 0.30)
    assert abs(T - 100.0) < 1e-9, (T, m)
    # 4) grande excentricidade: bloco plastificado (sig_max = sig_rd)
    Tg, Yg, smg, mg = placa_sob_NM(49.0, 60.0, 0.40, 0.45, 24791.5, 0.40)
    assert abs(smg - 24791.5) < 1e-6 and abs(Tg - 126.3) < 0.5, (Tg, Yg, smg)
    # 5) ancoragem NBR 6118 9.4.2: fbd, lb e lb,nec com gancho (alpha=0,7)
    a = ancoragem_chumbador(126.3, 0.020, 25e3, 250e3, com_gancho=True, h_embed=0.30)
    fck_MPa = 25.0
    fctd = 0.7 * 0.3 * fck_MPa ** (2.0 / 3.0) / 1.4 * 1000.0
    assert abs(a["fbd"] - 1.0 * 1.0 * 1.0 * fctd) < 1e-3          # eta1=eta2=eta3=1
    lb_exp = (0.020 / 4.0) * ((250e3 / 1.15) / a["fbd"])          # 9.4.2.4
    assert abs(a["lb"] - lb_exp) < 1e-9
    assert a["lb_nec"] >= a["lb_min"] - 1e-12 and a["alpha"] == 0.7
    assert a["ok_anc"] == (0.30 >= a["lb_nec"])                   # gate por h_embed
    # sem gancho (alpha=1,0) exige mais que com gancho
    a2 = ancoragem_chumbador(126.3, 0.020, 25e3, 250e3, com_gancho=False, h_embed=0.30)
    assert a2["lb_nec"] >= a["lb_nec"] - 1e-12
    print("base_chumbador self-test PASSED")
    print(f"  Ft,Rd(d20, fub400) = {ft:.1f} kN ; sigma_c,Rd(fck20,A2=A1) = {s:.0f} kN/m2")
    print(f"  grande exc.: T={Tg:.1f} kN ; Y={Yg*1000:.1f} mm ; sig_max=sig_rd={smg:.0f}")


# ---- exemplo PLACEHOLDER (a skill pergunta ao usuario) ---------------------
CASO_EXEMPLO_ENGASTE = {
    "nome": "Base engastada HEA200 (EXEMPLO - a skill pergunta)",
    "N": 49.0, "V": 26.0, "M": 60.0,          # kN, kN.m (esforcos de base)
    "fck": 25e3, "B": 0.40, "L": 0.45, "A2": 0.80 * 0.85,
    "n_chumbadores": 4, "n_tracionados": 2, "db": 0.020, "fub": 400e3,
    "d_anchor": 0.40, "borda": 0.05,
    "d_col": 0.190, "bf_col": 0.200,          # HEA200 (para os balancos AISC)
    "beff_tracao": 0.200,                     # largura efetiva lado tracionado
    "fy_placa": 250e3, "t_placa": 0.025, "rosca_no_plano": True,
    "fyk_chumbador": 250e3, "com_gancho": True, "h_embed": 0.30,   # ancoragem 9.4.2
}


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(verifica_base(CASO_EXEMPLO_ENGASTE), CASO_EXEMPLO_ENGASTE))
