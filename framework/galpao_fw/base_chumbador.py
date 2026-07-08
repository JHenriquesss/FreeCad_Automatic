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
#     embutimento reto requerido lb,nec (informativo/requisito, como t_req).
#   - CONE DE ARRANCAMENTO do concreto e efeito de GRUPO (ACI 318 Ch.17, metodo CCD
#     via Nilson cap.21): breakout Ncbg + pullout Npn + side-face Nsb do grupo
#     tracionado (opt-in via cone_geom - a geometria do bloco de fundacao e do
#     projeto de fundacao). Informativo; gateia so se gate_cone=True.
#   - TRANSFERENCIA DE CORTANTE (Fakury cap.11 - NBR 8800): triagem automatica
#     ATRITO (Vat,Rd=min(0,7 mu Nc; 0,2 fck Y B), mu=0,55) -> se sobrar, CHUMBADOR
#     (Vca,Sd=VSd-Vat) e/ou dimensiona a CHAVETA (barra de cisalhamento: hbc, tbc,
#     sigma_bc<=sig_c,Rd). Informativo (credita atrito so se atrito_cortante=True).
#   - EDGE BREAKOUT no cisalhamento (ACI 318 Ch.17 / Nilson cap.21): quando o V vai
#     aos chumbadores perto da borda -> Vcbg (21.7/8) + pryout Vcp (21.14). Opt-in
#     (cone_geom com ca1/ca2/h_bloco); informativo.
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


# ---- ACI 318 Ch.17 (metodo CCD) - cone de arrancamento do concreto -----------
# Fonte: Nilson, "Design of Concrete Structures" 15th ed., Cap.21 (reproduz o ACI
# 318 Ch.17), lido do PDF em pesquisa/aco/ (NAO de memoria). O ACI e escrito em
# unidades US (lb, in, psi); para preservar as CONSTANTES EXATAS das equacoes
# (kc=24, ANco=9hef^2, Np=8Abrg fc', Nsb=160..., 1.9 fya) a rotina converte a
# ENTRADA SI (m, kN, kN/m2) -> US no contorno, calcula, e devolve kN.
_IN_PER_M = 39.37007874          # 1 m  -> in
_PSI_PER_KPA = 0.14503773773     # 1 kN/m2 (=kPa) -> psi
_KN_PER_LB = 0.004448221615      # 1 lb -> kN


def cone_arrancamento_aci(Ft_sd_por_ancora, n_tracao, db, hef, fck,
                          s_x, s_y, n_x, n_y, ca1, ca2,
                          fyk=250e3, fissurado=True, com_reforco=False,
                          gancho=True, eh=None, A_brg=None, lam_a=1.0):
    """Verificacao do CONE DE ARRANCAMENTO do concreto (ACI 318 Ch.17, metodo CCD)
    para o GRUPO de chumbadores tracionados de uma base. Fecha o modo de ruptura do
    concreto que a ancoragem por aderencia (NBR 6118) NAO cobre.

    Modos de ruptura na TRACAO (o menor governa; NBR 8800 ja cobre o aco):
      - Breakout do grupo (Ncbg)  Eq.21.6:
          Nb   = kc*lam_a*sqrt(fc')*hef^1.5   (kc=24 cast-in)          [21.1]
          ANco = 9*hef^2 ; ANc = area projetada do grupo (limitada por 1.5hef/borda)
          psi_ec,N = 1/(1+2 e'N/(3 hef)) <= 1                          [Tab.21.6]
          psi_ed,N = 1 se ca,min>=1.5hef senao 0,7+0,3*ca,min/(1.5hef) [Tab.21.5]
          psi_c,N  = 1,0 fissurado / 1,25 nao-fissurado cast-in        [Tab.21.4]
          psi_cp,N = 1,0 (cast-in)
          Ncbg = (ANc/ANco)*psi_ec*psi_ed*psi_c*psi_cp*Nb
      - Pullout (Npn)  Eq.21.9/21.10/21.11:
          headed: Np = 8*Abrg*fc' ; hooked (gancho J/L): Np = 0,9*fc'*eh*da
          psi_c,p = 1,0 fissurado / 1,4 nao-fissurado ; Npn = psi_c,p*Np (por ancora)
      - Side-face blowout (Nsb)  Eq.21.12: 160*ca1*sqrt(Abrg)*lam_a*sqrt(fc')
          so quando hef > 2,5*ca1 (embutimento profundo perto da borda).

    phi (Tab.21.1): aco ductil 0,75 ; breakout cast-in Cond.B (SEM armadura
    suplementar) 0,70 e Cond.A (COM) 0,75 ; pullout/side-face sempre 0,70.
    Demanda: N_ua = Ft_sd_por_ancora * n_tracao (tracao fatorada do lado tracionado).

    Convencao de grupo: n_x*n_y chumbadores tracionados, espacamentos s_x/s_y (m),
    distancias de borda ca1 (mais proxima) e ca2 (m). e'N = 0 (default, carga
    centrada no grupo tracionado). Unidades SI: db,hef,s_x,s_y,ca1,ca2,eh,A_brg em
    m/m2 ; fck,fyk em kN/m2 ; Ft_sd_por_ancora em kN. Devolve capacidades em kN.

    INFORMATIVO por padrao (nao gateia OK): a geometria do bloco de fundacao
    (borda/altura) e do detalhe da cabeca/gancho e do projeto de fundacao; o
    responsavel confirma ca1/ca2/hef/reforco. Devolve ok=None sem geometria."""
    # ---- SI -> US -----------------------------------------------------------
    hef_in = hef * _IN_PER_M
    da_in = db * _IN_PER_M
    fc_psi = fck * _PSI_PER_KPA
    s1_in = s_x * _IN_PER_M                       # espacamento em x
    s2_in = s_y * _IN_PER_M                       # espacamento em y
    ca1_in = ca1 * _IN_PER_M
    ca2_in = ca2 * _IN_PER_M
    sqfc = math.sqrt(fc_psi)
    kc = 24.0                                     # cast-in (chumbador embutido)

    # ---- Breakout (tracao) --------------------------------------------------
    # Nb basico (21.1); alternativa profunda (21.2) para 11<=hef<=25 in.
    Nb = kc * lam_a * sqfc * hef_in ** 1.5
    if 11.0 <= hef_in <= 25.0:
        Nb = max(Nb, 16.0 * lam_a * sqfc * hef_in ** (5.0 / 3.0))
    ANco = 9.0 * hef_in ** 2
    # Area projetada do grupo: expande o retangulo dos ancoras por min(1.5hef,borda)
    # em cada face. sx_tot/sy_tot = extensao total do grupo tracionado.
    infl = 1.5 * hef_in
    sx_tot = (n_x - 1) * s1_in
    sy_tot = (n_y - 1) * s2_in
    largura = min(infl, ca1_in) + sx_tot + infl          # borda so no lado ca1 (x)
    profund = min(infl, ca2_in) + sy_tot + infl          # borda so no lado ca2 (y)
    ANc = largura * profund
    ca_min = min(ca1_in, ca2_in)
    psi_ed = 1.0 if ca_min >= infl else (0.7 + 0.3 * ca_min / infl)
    psi_c = 1.0 if fissurado else 1.25                   # cast-in
    psi_cp = 1.0                                         # cast-in
    psi_ec = 1.0                                         # e'N=0 (carga centrada)
    Ncbg_lb = (ANc / ANco) * psi_ec * psi_ed * psi_c * psi_cp * Nb

    # ---- Pullout (por ancora) ----------------------------------------------
    if gancho:
        eh_in = (eh * _IN_PER_M) if eh else 3.0 * da_in  # 3da<=eh<4.5da; 3da conserv.
        Np_lb = 0.9 * fc_psi * eh_in * da_in             # 21.11 hooked
        Abrg_in2 = None
    else:
        if A_brg:
            Abrg_in2 = A_brg * _IN_PER_M ** 2
        else:                                            # cabeca de porca sextavada ~1,7db
            d_head = 1.7 * da_in
            Abrg_in2 = math.pi * (d_head ** 2 - da_in ** 2) / 4.0
        Np_lb = 8.0 * Abrg_in2 * fc_psi                  # 21.10 headed
    psi_cp_pull = 1.0 if fissurado else 1.4
    Npn_lb = psi_cp_pull * Np_lb
    Npng_lb = Npn_lb * (n_x * n_y)                       # grupo (soma das ancoras)

    # ---- Side-face blowout (so hef > 2,5 ca1) -------------------------------
    if hef_in > 2.5 * ca1_in and Abrg_in2 is not None:
        Nsb_lb = 160.0 * ca1_in * math.sqrt(Abrg_in2) * lam_a * sqfc
        if ca2_in < 3.0 * ca1_in:                        # modificador de canto
            Nsb_lb *= (1.0 + max(min(ca2_in / ca1_in, 3.0), 1.0)) / 4.0
    else:
        Nsb_lb = float("inf")                            # nao governa (raso/longe da borda)

    # ---- phi + governante ---------------------------------------------------
    phi_brk = 0.75 if com_reforco else 0.70              # Cond.A / Cond.B (Tab.21.1)
    phi_pull = 0.70                                      # pullout sempre Cond.B
    cap_breakout = phi_brk * Ncbg_lb * _KN_PER_LB
    cap_pullout = phi_pull * Npng_lb * _KN_PER_LB
    cap_sideface = (phi_pull * Nsb_lb * _KN_PER_LB) if Nsb_lb != float("inf") else float("inf")
    cap_conc = min(cap_breakout, cap_pullout, cap_sideface)
    modo = min((("breakout", cap_breakout), ("pullout", cap_pullout),
                ("side-face", cap_sideface)), key=lambda t: t[1])[0]
    demanda = Ft_sd_por_ancora * n_tracao
    r = {"Nb_kN": Nb * _KN_PER_LB, "ANc_ANco": ANc / ANco,
         "psi_ed": psi_ed, "psi_c": psi_c,
         "cap_breakout_kN": cap_breakout, "cap_pullout_kN": cap_pullout,
         "cap_sideface_kN": cap_sideface, "cap_concreto_kN": cap_conc,
         "modo_governante": modo, "demanda_kN": demanda, "hef_m": hef}
    r["u_cone"] = demanda / cap_conc if cap_conc > 0 else float("inf")
    r["ok_cone"] = cap_conc >= demanda - 1e-9
    return r


def edge_breakout_cisalhamento_aci(V_sd, n_borda, db, hef, fck, ca1, ca2, ha,
                                   s_par=0.0, n_par=1, fissurado=True,
                                   com_reforco=False, le=None, ncbg_kN=None,
                                   paralelo=False, lam_a=1.0):
    """Concrete Edge Breakout no CISALHAMENTO (ACI 318 Ch.17 / Nilson cap.21).
    Complementa o cone de tracao: quando o cortante e resistido pelos chumbadores
    perto da borda do pedestal, o concreto pode 'estourar' a borda empurrado pela
    ancora. Mesmo isolamento de unidades (US interno <- SI no contorno).

    Modos (o menor governa):
      - Edge breakout Vcbg (21.7/21.8):
          Vb = (7*(le/da)^0,2*sqrt(da))*lam*sqrt(fc')*ca1^1,5  <= 9*lam*sqrt(fc')*ca1^1,5
               (le = comprimento de apoio ao cisalhamento = hef, <= 8*da)   [21.3/21.4]
          AVco = 4,5*ca1^2 ; AVc = area projetada na face livre (largura x altura,
                 altura = min(1,5ca1, ha))                                   [Fig.21.10]
          psi_ed,V = 1 se ca2>=1,5ca1 senao 0,7+0,3*ca2/(1,5ca1)            [Tab.21.5]
          psi_c,V  = 1,0 fissurado / 1,4 nao-fissurado cast-in              [Tab.21.4]
          psi_h,V  = sqrt(1,5ca1/ha) >= 1 (ha < 1,5ca1)                     [21.4d]
          Vcbg = (AVc/AVco)*psi_ed*psi_c*psi_h*Vb ; cortante PARALELO a borda = 2x.
      - Pryout Vcpg = kcp*Ncbg (21.14/15): kcp = 1 (hef<2,5in) / 2 (>=2,5in). So
        calculado se ncbg_kN (breakout de TRACAO do grupo) for passado.

    phi (Tab.21.1): breakout cast-in Cond.B 0,70 / Cond.A 0,75 ; pryout 0,70.
    V_sd = cortante de calculo no grupo junto a borda (kN). Unidades SI: m/kN/kN-m2.
    INFORMATIVO/opt-in (geometria do bloco = projeto de fundacao)."""
    da_in = db * _IN_PER_M
    hef_in = hef * _IN_PER_M
    ca1_in = ca1 * _IN_PER_M
    ca2_in = ca2 * _IN_PER_M
    ha_in = ha * _IN_PER_M
    s_in = s_par * _IN_PER_M
    fc_psi = fck * _PSI_PER_KPA
    sqfc = math.sqrt(fc_psi)
    le_in = (le * _IN_PER_M) if le else min(hef_in, 8.0 * da_in)

    Vb = (7.0 * (le_in / da_in) ** 0.2 * math.sqrt(da_in)) * lam_a * sqfc * ca1_in ** 1.5
    Vb = min(Vb, 9.0 * lam_a * sqfc * ca1_in ** 1.5)          # teto 21.4
    AVco = 4.5 * ca1_in ** 2
    altura = min(1.5 * ca1_in, ha_in)
    largura = min(1.5 * ca1_in, ca2_in) + (n_par - 1) * s_in + 1.5 * ca1_in
    AVc = largura * altura
    infl = 1.5 * ca1_in
    psi_ed = 1.0 if ca2_in >= infl else (0.7 + 0.3 * ca2_in / infl)
    psi_c = 1.0 if fissurado else 1.4
    psi_h = math.sqrt(infl / ha_in) if ha_in < infl else 1.0
    Vcbg_lb = (AVc / AVco) * psi_ed * psi_c * psi_h * Vb
    if paralelo:
        Vcbg_lb *= 2.0                                       # 17.5.2.1
    phi_brk = 0.75 if com_reforco else 0.70
    cap_breakout = phi_brk * Vcbg_lb * _KN_PER_LB

    # pryout (precisa do Ncbg de tracao)
    if ncbg_kN is not None:
        kcp = 2.0 if hef_in >= 2.5 else 1.0
        cap_pryout = 0.70 * kcp * ncbg_kN                    # ncbg ja em kN nominal
    else:
        cap_pryout = float("inf")
    cap = min(cap_breakout, cap_pryout)
    modo = "edge-breakout" if cap_breakout <= cap_pryout else "pryout"
    r = {"Vb_kN": Vb * _KN_PER_LB, "AVc_AVco": AVc / AVco, "psi_ed": psi_ed,
         "psi_c": psi_c, "psi_h": psi_h, "cap_breakout_kN": cap_breakout,
         "cap_pryout_kN": cap_pryout, "cap_cisalhamento_kN": cap,
         "modo": modo, "demanda_kN": V_sd, "paralelo": paralelo}
    r["u_edge"] = V_sd / cap if cap > 0 else float("inf")
    r["ok_edge"] = cap >= V_sd - 1e-9
    # ACI 17.5.2.9: se o breakout sem armadura nao passa (u>1), a borda estoura ->
    # o projeto de fundacao pode desenvolver a carga com ARMADURA DE ANCORAGEM em
    # laco (hairpin/estribo) transversal, atravessando a superficie de ruptura.
    r["armadura_ancoragem"] = not r["ok_edge"]
    return r


# ---- Transferencia de cortante na base (Fakury cap.11 - NBR 8800) ------------
# Fonte: "Dimensionamento de elementos estruturais de aco e mistos de aco e
# concreto" (Fakury/Silva/Caldas), cap.11 "Bases de pilar", lido do PDF em
# pesquisa/aco/ (NAO de memoria). Triade de transferencia de cisalhamento:
#   1) ATRITO placa-concreto (11.21): Vat,Rd = min(0,7*mu*Nc,Sd ; 0,2*fck*Y*Bpb),
#      mu=0,55 (face inferior SEM pintura). So com compressao na base.
#   2) BARRA DE CISALHAMENTO / chaveta (11.22-25,28): Vbc,Sd = VSd - Vat,Rd ;
#      hbc >= 2*har ; sigma_bc,Sd = Vbc/(bbc*(hbc-har)) <= sigma_c,Rd ;
#      Mbc,Sd = Vbc*cbc , cbc = har + (hbc-har)/2 -> flexao da chapa da chaveta.
#   3) CHUMBADORES (11.26): Vca,Sd = VSd - Vat,Rd (exige arruela especial soldada).
MU_ACO_CONCRETO = 0.55          # coef. atrito placa de aco x concreto (sem pintura)


def transferencia_cortante_base(V_sd, N_comp, fck, B, Y, sig_c_rd, n_ch, Fv_rd,
                                mu=MU_ACO_CONCRETO, har=0.030, b_chaveta=None,
                                fy_chaveta=250e3):
    """Triagem automatica do cortante da base (Fakury cap.11). Ordem de prioridade:
    ATRITO -> se sobrar, CHUMBADOR (aco) e/ou CHAVETA (barra de cisalhamento).

    V_sd = cortante de calculo (kN) ; N_comp = forca NORMAL de COMPRESSAO na mesma
    combinacao (kN, 0 se tracao/uplift -> sem atrito) ; Y = comprimento comprimido
    do concreto (m, de placa_sob_NM) ; sig_c_rd = tensao resistente de contato
    (kN/m2, 6.6.5) ; b_chaveta = largura da chaveta (m, default = B) ; har = altura
    da argamassa/graute (m). Unidades SI. Dimensiona a chaveta requerida (hbc, tbc).

    Retorna o mecanismo que RESOLVE o cortante e o dimensionamento da chaveta caso
    o atrito nao baste. INFORMATIVO (nao gateia): creditar o atrito exige que a
    COMPRESSAO atue na MESMA combinacao do cortante - decisao do projetista."""
    # 1) ATRITO (11.21): so com compressao. Cap por esmagamento do contato.
    if N_comp and N_comp > 0:
        Vat_rd = min(0.7 * mu * N_comp, 0.2 * fck * max(Y, 0.0) * B)
    else:
        Vat_rd = 0.0
    V_resid = max(V_sd - Vat_rd, 0.0)
    r = {"Vat_rd": Vat_rd, "V_resid": V_resid, "mu": mu}
    if V_resid <= 1e-9:
        r["mecanismo"] = "atrito"
        r["ok"] = True
        return r
    # 2) CHUMBADORES (11.26): cortante residual distribuido nos n chumbadores.
    Fv_sd_liq = V_resid / n_ch if n_ch > 0 else float("inf")
    r["Vca_sd"] = V_resid
    r["Fv_sd_liq"] = Fv_sd_liq
    r["u_chumbador"] = Fv_sd_liq / Fv_rd if Fv_rd > 0 else float("inf")
    r["ok_chumbador"] = Fv_sd_liq <= Fv_rd + 1e-9
    # 3) CHAVETA (barra de cisalhamento): dimensiona hbc e tbc para o residual.
    bbc = b_chaveta if b_chaveta else B
    Vbc_sd = V_resid
    # (hbc-har) requerido p/ nao esmagar o concreto: sigma_bc <= sig_c_rd (11.25/28)
    h_util_req = Vbc_sd / (bbc * sig_c_rd) if (bbc > 0 and sig_c_rd > 0) else float("inf")
    hbc_req = max(2.0 * har, har + h_util_req)          # hbc >= 2*har (11 recomenda)
    h_util = hbc_req - har
    sigma_bc = Vbc_sd / (bbc * h_util) if h_util > 0 else float("inf")
    cbc = har + h_util / 2.0                            # (11.24)
    Mbc_sd = Vbc_sd * cbc                               # (11.23)
    # flexao da chapa da chaveta (secao bbc x tbc, plastificacao): tbc requerido
    tbc_req = math.sqrt(4.0 * Mbc_sd * GA1 / (bbc * fy_chaveta)) if bbc > 0 else float("inf")
    r["chaveta"] = {"bbc": bbc, "hbc_req": hbc_req, "h_util": h_util,
                    "sigma_bc": sigma_bc, "sig_c_rd": sig_c_rd, "cbc": cbc,
                    "Mbc_sd": Mbc_sd, "tbc_req": tbc_req, "har": har}
    # mecanismo recomendado: chumbador se aguentar o aco, senao chaveta.
    r["mecanismo"] = "chumbador" if r["ok_chumbador"] else "chaveta"
    r["ok"] = True                                     # a chaveta sempre pode ser dimensionada
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

    # cone de arrancamento (ACI 318 Ch.17) - opt-in: so quando o caso traz a
    # geometria do bloco de fundacao (borda/altura/espacamento), que e do projeto
    # de fundacao. Informativo; gateia OK so se caso["gate_cone"]=True.
    cone = None
    if caso.get("cone_geom"):
        g = caso["cone_geom"]
        cone = cone_arrancamento_aci(
            Ft_sd, g.get("n_tracao", n_t), db,
            g.get("hef", caso.get("h_embed", 0.30)), fck,
            s_x=g["s_x"], s_y=g["s_y"], n_x=g["n_x"], n_y=g["n_y"],
            ca1=g["ca1"], ca2=g["ca2"],
            fissurado=g.get("fissurado", True),
            com_reforco=g.get("com_reforco", False),
            gancho=caso.get("com_gancho", True), eh=g.get("eh"),
            A_brg=g.get("A_brg"))
    r["cone"] = cone

    # transferencia de cortante (Fakury cap.11): atrito -> chumbador/chaveta.
    # N>0 = compressao (convencao placa_sob_NM). So credita atrito se o caso pedir
    # (a compressao tem de atuar na MESMA combinacao do cortante) - default: sem
    # credito (conservador, todo V nos chumbadores, como antes).
    N_comp = N if (N and N > 0 and caso.get("atrito_cortante", False)) else 0.0
    cv = transferencia_cortante_base(
        abs(V), N_comp, fck, B, (Y if Y else 0.0), sig_rd, n, Fv_rd,
        har=caso.get("h_graute", 0.030), b_chaveta=caso.get("b_chaveta"),
        fy_chaveta=caso.get("fy_chaveta", caso.get("fy_placa", 250e3)))
    # edge breakout no cisalhamento (ACI Ch.17): so quando o V residual vai aos
    # CHUMBADORES e ha geometria de bloco (cone_geom + h_bloco). Informativo.
    if caso.get("cone_geom") and cv.get("mecanismo") == "chumbador":
        g = caso["cone_geom"]
        ncbg_nom = (cone["cap_breakout_kN"] / 0.70) if cone else None
        cv["edge"] = edge_breakout_cisalhamento_aci(
            cv["V_resid"], g.get("n_tracao", n_t), db,
            g.get("hef", caso.get("h_embed", 0.30)), fck,
            ca1=g["ca1"], ca2=g["ca2"], ha=g.get("h_bloco", g.get("hef", 0.40)),
            s_par=g.get("s_x", 0.0), n_par=g.get("n_x", 1),
            fissurado=g.get("fissurado", True),
            com_reforco=g.get("com_reforco", False), ncbg_kN=ncbg_nom,
            paralelo=caso.get("cortante_paralelo_borda", False))
    r["cortante"] = cv

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
    # cone: informativo por default; gateia so se gate_cone=True e reprovar.
    ok_cone_gate = True
    if caso.get("gate_cone", False) and cone is not None and cone["ok_cone"] is False:
        ok_cone_gate = False
    r["OK"] = (r["interacao"] <= 1.0 and r["u_corte"] <= 1.0 and
               r["u_concreto"] <= 1.0 + 1e-9 and r["Y_cabe"] and
               (r["t_placa"] is None or r["t_placa"] >= t_req) and ok_anc_gate and
               ok_cone_gate)
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
         f"  -> {'OK' if r['OK'] else 'NAO PASSA'}"]
    c = r.get("cone")
    if c is not None:
        tag = ("OK" if c["ok_cone"] else
               "REPROVA - aumentar hef/borda/n, cabeca/gancho (pullout) ou reforco de ancoragem")
        L += [f"  Cone de arrancamento (ACI 318 Ch.17): governa {c['modo_governante']} ; "
              f"cap.concreto={c['cap_concreto_kN']:.0f} kN vs demanda={c['demanda_kN']:.0f} "
              f"kN -> u={c['u_cone']:.2f} [{tag}]",
              f"         (breakout={c['cap_breakout_kN']:.0f} ; pullout={c['cap_pullout_kN']:.0f}"
              + ("" if c['cap_sideface_kN'] == float('inf') else f" ; side-face={c['cap_sideface_kN']:.0f}")
              + f" kN ; ANc/ANco={c['ANc_ANco']:.2f} ; psi_ed={c['psi_ed']:.2f})"]
    else:
        L += ["  [FLAG] Ancoragem por ADERENCIA verificada (NBR 6118 9.4.2). O CONE DE",
              "         ARRANCAMENTO do concreto e o efeito de GRUPO (ACI 318 Ch.17)",
              "         seguem do projeto de fundacao (passar cone_geom para calcular)."]
    cv = r.get("cortante")
    if cv is not None:
        if cv["mecanismo"] == "atrito":
            L += [f"  Cortante (Fakury cap.11): atrito Vat,Rd={cv['Vat_rd']:.0f} kN >= "
                  f"V={caso['V']:.0f} kN -> RESOLVIDO por atrito (chumbadores so a tracao)."]
        else:
            ch = cv["chaveta"]
            L += [f"  Cortante (Fakury cap.11): atrito Vat,Rd={cv['Vat_rd']:.0f} kN ; "
                  f"residual Vbc,Sd={cv['V_resid']:.0f} kN -> "
                  f"chumbador u={cv['u_chumbador']:.2f}"
                  + (" OK" if cv["ok_chumbador"] else " NAO PASSA (aco) -> usar CHAVETA"),
                  f"         Chaveta requerida: bbc={ch['bbc']*1000:.0f} mm ; "
                  f"hbc>={ch['hbc_req']*1000:.0f} mm (h_util={ch['h_util']*1000:.0f}) ; "
                  f"tbc>={ch['tbc_req']*1000:.1f} mm ; sigma_bc={ch['sigma_bc']:.0f}<="
                  f"sig_c,Rd={ch['sig_c_rd']:.0f} kN/m2"]
            eg = cv.get("edge")
            if eg is not None:
                tage = "OK" if eg["ok_edge"] else "REPROVA - afastar da borda/aumentar ca1,hef ou usar chaveta"
                L += [f"         Edge breakout no cortante (ACI Ch.17): governa "
                      f"{eg['modo']} ; cap={eg['cap_cisalhamento_kN']:.0f} kN vs "
                      f"V={eg['demanda_kN']:.0f} kN -> u={eg['u_edge']:.2f} [{tage}]"]
                if eg.get("armadura_ancoragem"):
                    L += ["         [WARNING] u>1 SEM armadura: borda estoura. Projeto de "
                          "fundacao deve detalhar ARMADURA DE ANCORAGEM em laco "
                          "(hairpin/estribo) atravessando a ruptura (ACI 17.5.2.9)."]
            else:
                L += ["         [FLAG] Edge breakout no cortante (ACI Ch.17): passar "
                      "cone_geom (ca1,ca2,h_bloco) p/ calcular quando V vai aos chumbadores."]
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
    # 6) Cone ACI 318 Ch.17 - reproduz Nilson Ex.21.3 (breakout) e 21.6 (pullout)
    #    via ENTRADA SI, provando o isolamento de unidades (US interno).
    #    Ex.21.3: 6 studs 1/2", hef=4", s1=5", s2=4.5", ca1=ca2=8" (>1.5hef), fc=5000
    #    psi, fissurado -> Ncbg nominal = 33,7 kips = 149,7 kN (Nb=13,58 kip, ANc/ANco
    #    =357/144=2,479). Ex.21.6: Abrg=0,589 in^2 -> Npng = 141,4 kips = 628,9 kN.
    IN = 0.0254
    fc_si = 5000.0 / _PSI_PER_KPA                     # 5000 psi -> kN/m2
    c = cone_arrancamento_aci(50.0, 6, 0.5 * IN, 4.0 * IN, fc_si,
                              s_x=5.0 * IN, s_y=4.5 * IN, n_x=2, n_y=3,
                              ca1=8.0 * IN, ca2=8.0 * IN, fissurado=True,
                              com_reforco=False,             # Cond.B -> phi=0,70
                              gancho=False, A_brg=0.589 * IN ** 2)
    assert abs(c["Nb_kN"] - 60.4) < 1.0, c["Nb_kN"]   # 13.576 lb -> 60,4 kN
    assert abs(c["ANc_ANco"] - 2.479) < 1e-2, c["ANc_ANco"]
    Ncbg_nom = c["cap_breakout_kN"] / 0.70            # remove phi -> nominal
    assert abs(Ncbg_nom - 149.7) < 1.5, Ncbg_nom      # 33,7 kips
    Npng_nom = c["cap_pullout_kN"] / 0.70
    assert abs(Npng_nom - 628.9) < 3.0, Npng_nom      # 141,4 kips
    assert c["psi_ed"] == 1.0 and c["psi_c"] == 1.0   # ca>1,5hef ; fissurado
    # 7) Transferencia de cortante (Fakury cap.11): atrito, chumbador, chaveta.
    #    (a) atrito resolve: V baixo + compressao alta -> mecanismo="atrito".
    sig = sigma_c_rd(25e3, 0.4 * 0.45, 0.4 * 0.45)
    t1 = transferencia_cortante_base(V_sd=26.0, N_comp=200.0, fck=25e3, B=0.40,
                                     Y=0.10, sig_c_rd=sig, n_ch=4, Fv_rd=37.2)
    Vat_exp = min(0.7 * 0.55 * 200.0, 0.2 * 25e3 * 0.10 * 0.40)   # 77 vs 200 -> 77
    assert abs(t1["Vat_rd"] - Vat_exp) < 1e-6 and t1["mecanismo"] == "atrito", t1
    #    (b) uplift (sem compressao) -> atrito=0, cortante vai p/ chumbador/chaveta.
    t2 = transferencia_cortante_base(V_sd=120.0, N_comp=0.0, fck=25e3, B=0.40,
                                     Y=0.0, sig_c_rd=sig, n_ch=4, Fv_rd=37.2)
    assert t2["Vat_rd"] == 0.0 and abs(t2["V_resid"] - 120.0) < 1e-9
    assert t2["chaveta"]["hbc_req"] >= 2.0 * 0.030 - 1e-12         # hbc>=2 har
    assert t2["chaveta"]["sigma_bc"] <= sig + 1e-6                 # chaveta nao esmaga
    # cortante alto sozinho nos 4 chumbadores estoura o aco -> recomenda chaveta
    assert t2["mecanismo"] in ("chaveta", "chumbador")
    # 8) Edge breakout no cisalhamento (ACI Ch.17) - Vb do Nilson Ex.21.5
    #    (da=0,75", hef=4", ca1=8", fc=5000 psi) -> Vb=13,56 kip=60,3 kN ; AVco=4,5ca1^2.
    e = edge_breakout_cisalhamento_aci(50.0, 1, 0.75 * IN, 4.0 * IN, fc_si,
                                       ca1=8.0 * IN, ca2=20.0 * IN, ha=16.0 * IN,
                                       s_par=0.0, n_par=1, fissurado=True)
    assert abs(e["Vb_kN"] - 60.3) < 0.6, e["Vb_kN"]         # 13,56 kip
    assert e["psi_ed"] == 1.0 and e["psi_h"] == 1.0         # ca2>=1,5ca1 ; ha>=1,5ca1
    assert e["cap_pryout_kN"] == float("inf")               # sem Ncbg -> so breakout
    # ca2 < 1,5ca1 reduz o breakout (psi_ed = 0,7+0,3*ca2/(1,5ca1))
    ered = edge_breakout_cisalhamento_aci(50.0, 1, 0.75 * IN, 4.0 * IN, fc_si,
                                          ca1=8.0 * IN, ca2=8.0 * IN, ha=16.0 * IN)
    assert abs(ered["psi_ed"] - (0.7 + 0.3 * 8.0 / 12.0)) < 1e-9   # = 0,90
    # com Ncbg de tracao -> pryout kcp=2 (hef=4in>2,5)
    e2 = edge_breakout_cisalhamento_aci(50.0, 1, 0.75 * IN, 4.0 * IN, fc_si,
                                        ca1=8.0 * IN, ca2=20.0 * IN, ha=16.0 * IN,
                                        ncbg_kN=150.0)
    assert abs(e2["cap_pryout_kN"] - 0.70 * 2.0 * 150.0) < 1e-9
    # u>1 sem armadura -> aciona o warning de armadura de ancoragem (hairpin)
    ehi = edge_breakout_cisalhamento_aci(500.0, 1, 0.020, 0.30, fc_si,
                                         ca1=0.10, ca2=0.10, ha=0.40)
    assert ehi["u_edge"] > 1.0 and ehi["armadura_ancoragem"] is True
    # caso folgado (V pequeno, borda larga) passa e nao aciona armadura
    elow = edge_breakout_cisalhamento_aci(5.0, 1, 0.020, 0.30, fc_si,
                                          ca1=0.30, ca2=0.30, ha=0.60)
    assert elow["ok_edge"] and elow["armadura_ancoragem"] is False
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
    # cone ACI 318 Ch.17 (EXEMPLO - geometria do bloco de fundacao; a skill pergunta):
    # 2 chumbadores tracionados lado a lado (n_x=2, s_x=0,30), 1 fila (n_y=1);
    # bloco/pedestal dando borda ca1=ca2=0,15 m ; hef=embutimento=0,30 m ; fissurado.
    "cone_geom": {"n_tracao": 2, "hef": 0.30, "n_x": 2, "n_y": 1,
                  "s_x": 0.30, "s_y": 0.0, "ca1": 0.15, "ca2": 0.15,
                  "h_bloco": 0.60, "fissurado": True, "com_reforco": False},
}


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(verifica_base(CASO_EXEMPLO_ENGASTE), CASO_EXEMPLO_ENGASTE))
