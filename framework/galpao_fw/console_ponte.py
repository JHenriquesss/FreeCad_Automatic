# ============================================================================
# console_ponte.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica a LIGACAO DO CONSOLE da ponte rolante a coluna (a chapa/solda que
# recebe a viga de rolamento excentrica). So existe quando ha ponte. Nao
# reinventa a resistencia da solda: reusa `ligacoes.fw_rd_filete` (metal da
# solda 6.2.5) e `ligacoes.solda_filete_minimo` (perna minima Tab.9); as cargas
# vem de `ponte_rolante` (reacao vertical do trilho + forca transversal).
# Metodo do GRUPO DE SOLDA = analise ELASTICA (vetorial) da linha de solda,
# DOIS cordoes verticais (um de cada lado da chapa) -> A_w = 2L, Sw = L^2/3.
# Direcoes (chapa no plano de carga; z vertical=direcao do cordao; x horizontal):
#   f_v  = Rv/(2L)              cisalhamento vertical direto (eixo z, // cordao)
#   f_h  = Ht/(2L)              cisalhamento horizontal direto (eixo x)
#   f_bV = 3*M/L^2   ; M = Rv*ecc            flexao no plano -> eixo x
#   f_bH = 3*Mz/L^2  ; Mz = Ht*(L/2+h_trilho) flexao por excentricidade de Ht (x)
# f_h, f_bV, f_bH sao COLINEARES (todas no eixo x horizontal) -> somam
# ALGEBRICAMENTE; so entao compoem com f_v (ortogonal, eixo z):
#   f_dem = sqrt(f_v^2 + (f_h + f_bV + f_bH)^2)
# (o SRSS de 3 termos da versao anterior era NAO-CONSERVADOR: subestima a
#  resultante de componentes colineares. Correcao do parecer senior 2026-07.)
# Este metodo elastico do grupo de solda e MECANICA/AISC (nao e item da NBR) -
# documentado como FLAG, analogo ao T-stub (EN 1993) ja aceito no joelho.
# Verifica a chapa do console como VIGA EM BALANCO: cisalhamento (5.4) E flexao
# na raiz COM FLT da chapa retangular macica (NBR 8800 Anexo G / Tab. G.1: o bordo
# comprimido tomba antes de plastificar). Saidas em portugues. Unidades SI: m, kN.
# ============================================================================
"""Verificacao da ligacao do console da ponte rolante (compoe ligacoes.py)."""

from __future__ import annotations

import math

import ligacoes as LG
from check_nbr8800 import GA1, E

GA2 = LG.GA2


def mrd_flt_chapa(t, L, ecc, fy, Cb=1.0):
    """Momento fletor resistente da CHAPA RETANGULAR MACICA do console por FLT
    (flambagem lateral com torcao) - NBR 8800:2008 Anexo G, Tabela G.1, linha
    "secoes solidas retangulares fletidas em relacao ao eixo de maior momento de
    inercia". Seccao macica NAO tem flambagem LOCAL (nao ha elementos esbeltos,
    G.1.2) -> o unico estado-limite e a FLT: o bordo comprimido "tomba" (gira
    lateralmente) antes de plastificar. Fecha o FLAG de flambagem do bordo.

    Chapa: espessura t, altura (eixo forte, no plano de carga) L, em balanco de
    projecao `ecc`. Extremidade livre nao contida -> Lb = 2*ecc (K=2); balanco ->
    Cb = 1 (conservador). Propriedades da seccao t x L:
      A=t*L ; W=t*L^2/6 ; Z=t*L^2/4 ; ry=t/sqrt(12) ; Cw~0 ;
      J = L*t^3/3 * (1 - 0,63*t/L)  (Saint-Venant c/ correcao de placa).
    Tabela G.1 (secao solida retangular, FLT):
      lambda   = Lb/ry
      lambda_p = 0,13*E*sqrt(J*A)/Mpl     (Mpl = Z*fy)
      lambda_r = 2,00*E*sqrt(J*A)/Mr      (Mr  = W*fy ; solido: sem sigma_r)
      Mcr      = 2,00*Cb*E*sqrt(J*A)/lambda
    e G.2.2: Mrd = Mpl/ga1 (l<=lp) ; interpola (lp<l<=lr) ; Mcr/ga1 (l>lr); teto Mpl.
    Validado contra o exemplo resolvido (Pfeil) via NotebookLM. Tudo SI (m, kN)."""
    A = t * L
    W = t * L ** 2 / 6.0
    Z = t * L ** 2 / 4.0
    ry = t / math.sqrt(12.0)                       # sqrt(Iy/A), Iy = L*t^3/12
    J = (L * t ** 3 / 3.0) * (1.0 - 0.63 * t / L)  # Saint-Venant (correcao de placa)
    Lb = 2.0 * max(ecc, 0.0)                       # balanco livre -> Lb = 2x projecao
    Mpl = Z * fy
    Mr = W * fy                                    # secao solida: sem reducao por sigma_r
    raizJA = math.sqrt(J * A)
    lam = Lb / ry if ry > 0 else 0.0
    lam_p = 0.13 * E * raizJA / Mpl if Mpl else float("inf")
    lam_r = 2.00 * E * raizJA / Mr if Mr else float("inf")
    if lam <= lam_p:
        Mn, regime = Mpl, "plastificacao"
    elif lam <= lam_r:
        Mn = Cb * (Mpl - (Mpl - Mr) * (lam - lam_p) / (lam_r - lam_p))
        Mn, regime = min(Mn, Mpl), "inelastico (FLT)"
    else:
        Mcr = 2.00 * Cb * E * raizJA / lam
        Mn, regime = min(Mcr, Mpl), "elastico (FLT)"
    return {"Mrd": Mn / GA1, "Mn": Mn, "Mpl": Mpl, "Mr": Mr, "W": W, "Z": Z,
            "lam": lam, "lam_p": lam_p, "lam_r": lam_r, "Lb": Lb, "J": J,
            "regime": regime}


def verifica_console(caso):
    """Verifica a ligacao console->coluna. `caso` (SI, m/kN):
      Rv       - reacao vertical no console (kN) = reacao maxima do trilho
      Ht       - forca horizontal transversal no console (kN)
      ecc      - excentricidade do trilho a face da coluna (m)
      h_trilho - altura do topo do trilho acima do TOPO da solda (m; default 0);
                 braco de Ht ao centroide da solda = L/2 + h_trilho
      t        - espessura da chapa do console (m)
      L        - comprimento (vertical) FISICO de CADA cordao console->coluna (m)
      fy, fu   - aco da chapa (kN/m2)
      fw       - resistencia do metal da solda (kN/m2; E70XX ~ 485e3)
      perna    - perna do filete (m); default = minimo Tab.9
    Dois cordoes de comprimento EFETIVO L_ef=L-2*perna (desconta crateras):
    A_w=2*L_ef, Sw=L_ef^2/3. Retorna dict: solda (grupo elastico) + chapa em
    balanco (cisalhamento 5.4 E flexao na raiz, na secao t x L fisico)."""
    Rv, Ht = abs(caso["Rv"]), abs(caso.get("Ht", 0.0))
    ecc, t, L = caso["ecc"], caso["t"], caso["L"]
    h_trilho = caso.get("h_trilho", 0.0)
    fy, fu = caso["fy"], caso["fu"]
    fw = caso.get("fw", 485e3)

    M = Rv * ecc                                 # flexao no plano (Rv excentrico)
    Mz = Ht * (L / 2.0 + h_trilho)               # flexao por excentricidade de Ht

    def _grupo_solda(Lw):
        """Grupo de solda elastico, DOIS cordoes de comprimento EFETIVO Lw:
        A_w=2*Lw, Sw=Lw^2/3. M e Mz vem da geometria FISICA (fixos). Retorna
        (f_dem, componentes). Colineares em x somam; x ortogonal a z (f_v)."""
        f_v = Rv / (2.0 * Lw)                    # vertical direto (z, // cordao)
        f_h = Ht / (2.0 * Lw)                    # horizontal direto (x)
        f_bV = 3.0 * M / (Lw ** 2)               # flexao Rv*ecc (x)
        f_bH = 3.0 * Mz / (Lw ** 2)              # flexao Ht*braco (x)
        f_horiz = f_h + f_bV + f_bH              # COLINEARES no eixo x -> soma
        return math.sqrt(f_v ** 2 + f_horiz ** 2), f_v, f_h, f_bV, f_bH, f_horiz

    # comprimento EFETIVO de cada cordao: desconta crateras de inicio/fim
    # (2*perna), pratica de rigor recomendada p/ filetes. Depende da perna,
    # entao entra no proprio laco de dimensionamento.
    def _L_ef(perna_m):
        return max(L - 2.0 * perna_m, 1e-6)

    # FADIGA da solda (NBR 8800 Anexo K, Tab.K.1 item 8.2 = categoria F, cisalha-
    # mento na garganta do filete). A ponte passa e a reacao vai de ~0 a Rv -> a
    # faixa de variacao de tensao na garganta e tau_SR = f_dem_servico/garganta.
    # f_dem vem das cargas de SERVICO (Rv/Ht sao a reacao sem impacto). garganta =
    # 0,707*perna. So verifica se N informado (n_ciclos do regime, NBR 8400).
    N = caso.get("n_ciclos")
    sig_rd_F = None
    if N:
        from ponte_rolante import faixa_admissivel_fadiga
        sig_rd_F = faixa_admissivel_fadiga("F", N)   # MPa (piso sigma_TH=55)

    def _tau_sr(perna_m):
        """Faixa de variacao de tensao na garganta (MPa) p/ uma perna dada."""
        fd = _grupo_solda(_L_ef(perna_m))[0]
        return (fd / (0.707 * perna_m)) / 1000.0     # kN/m2 -> MPa

    # DIMENSIONA a perna do filete: menor perna-padrao (>= minimo Tab.9) que
    # satisfaz ESTATICA (capacidade do grupo >= demanda) E FADIGA (tau_SR <=
    # faixa cat.F) simultaneamente. A fadiga costuma governar em ponte pesada e
    # exige perna maior. Se nem 12 mm bastar, adota 12 e sinaliza (redesenho).
    p_min = LG.solda_filete_minimo(t * 1000.0)
    pernas = [p for p in (6.0, 8.0, 10.0, 12.0) if p >= p_min] or [p_min]
    perna = caso.get("perna") and caso["perna"] * 1000.0
    if perna is None:
        perna = pernas[-1]
        for p in pernas:
            fdem_p = _grupo_solda(_L_ef(p / 1000.0))[0]
            estatica_ok = LG.fw_rd_filete(p / 1000.0, 1.0, fw)[0] >= fdem_p
            fadiga_ok = (sig_rd_F is None) or (_tau_sr(p / 1000.0) <= sig_rd_F + 1e-9)
            if estatica_ok and fadiga_ok:
                perna = p
                break
    perna = perna / 1000.0
    L_ef = _L_ef(perna)
    f_dem, f_v, f_h, f_bV, f_bH, f_horiz = _grupo_solda(L_ef)
    f_cap = LG.fw_rd_filete(perna, 1.0, fw)[0]   # capacidade por comprimento (kN/m)
    u_solda = f_dem / f_cap if f_cap else float("inf")

    fad = None
    if N:
        tau_sr = _tau_sr(perna)                      # com a perna adotada
        fad = {"cat": "F", "N": N, "tau_sr": tau_sr, "sigma_rd": sig_rd_F,
               "u": tau_sr / sig_rd_F if sig_rd_F else float("inf"),
               "OK": tau_sr <= sig_rd_F + 1e-9}

    # chapa do console como VIGA EM BALANCO (secao t x L na raiz, junto a coluna):
    # (a) cisalhamento (escoamento 5.4): V_Rd = 0,6*fy*Aw/ga1 ; Aw = t*L
    Aw = t * L
    V_pl_Rd = 0.6 * fy * Aw / GA1
    u_cis = (Rv / V_pl_Rd) if V_pl_Rd else float("inf")
    # (b) flexao na raiz COM FLT da chapa retangular macica (NBR 8800 Anexo G,
    #     Tabela G.1). M_Sd = |M| + |Mz|: M=Rv*ecc e Mz=Ht*(L/2+h_trilho) fletem a
    #     chapa em torno do MESMO eixo forte -> tensoes normais colineares que SOMAM.
    #     O M_Rd NAO e mais W*fy elastico: o bordo comprimido pode TOMBAR (FLT) antes
    #     de plastificar -> Mrd pela curva do Anexo G (Lb=2*ecc, Cb=1). Fecha o FLAG
    #     de flambagem do bordo comprimido (era so flagado antes).
    M_Sd_chapa = abs(M) + abs(Mz)
    flt = mrd_flt_chapa(t, L, ecc, fy)
    M_Rd = flt["Mrd"]
    W = flt["W"]
    u_flex = (M_Sd_chapa / M_Rd) if M_Rd else float("inf")

    res = {
        "M": M, "Mz": Mz, "perna_mm": round(perna * 1000.0, 1),
        "L_mm": round(L * 1000.0, 1), "L_ef_mm": round(L_ef * 1000.0, 1),
        "solda": {"f_dem": f_dem, "f_cap": f_cap, "u": u_solda, "OK": u_solda <= 1.0,
                  "f_v": f_v, "f_horiz": f_horiz, "f_h": f_h, "f_bV": f_bV,
                  "f_bH": f_bH, "L_ef": L_ef},
        "chapa_cisalhamento": {"V_Rd": V_pl_Rd, "u": u_cis, "OK": u_cis <= 1.0},
        "chapa_flexao": {"M_Sd": M_Sd_chapa, "M": M, "Mz": Mz, "M_Rd": M_Rd,
                         "W": W, "u": u_flex, "OK": u_flex <= 1.0,
                         "flt_regime": flt["regime"], "lam": flt["lam"],
                         "lam_p": flt["lam_p"], "lam_r": flt["lam_r"],
                         "Mpl": flt["Mpl"], "Lb": flt["Lb"]},
        "fadiga": fad,
    }
    us = {"solda": u_solda, "chapa_cis": u_cis, "chapa_flex": u_flex}
    if fad:
        us["fadiga"] = fad["u"]
    res["u_max"] = max(us.values())
    res["governa"] = max(us, key=us.get)
    res["OK"] = all(v["OK"] for v in (res["solda"], res["chapa_cisalhamento"],
                                      res["chapa_flexao"])) and (fad is None or fad["OK"])
    res["adotado"] = {"t_mm": round(t * 1000.0, 1), "perna_solda_mm": res["perna_mm"]}
    return res


def relatorio_pt(res, titulo="CONSOLE DA PONTE ROLANTE"):
    def _pt(x):
        return ("%.2f" % x).replace(".", ",")
    s, c, f = res["solda"], res["chapa_cisalhamento"], res["chapa_flexao"]
    return "\n".join([
        "=" * 74, "%s - CONCEITUAL, PENDENTE REVISAO E ART DO ENG." % titulo,
        "Grupo de solda ELASTICO 2 cordoes (mecanica/AISC, FLAG) + chapa em balanco",
        "=" * 74, "",
        "Chapa t = %s mm ; solda perna %s mm x L %s mm (L_ef %s ; 2 cordoes) ; M = Rv*ecc = %s kN.m"
        % (_pt(res["adotado"]["t_mm"]), _pt(res["perna_mm"]), _pt(res["L_mm"]),
           _pt(res["L_ef_mm"]), _pt(res["M"])), "",
        "  Solda (grupo elastico)   dem = %s kN/m  cap = %s kN/m  util = %s %s"
        % (_pt(s["f_dem"]), _pt(s["f_cap"]), _pt(s["u"]),
           "OK" if s["OK"] else "*** NAO ATENDE ***"),
        "    (f_v=%s ; f_horiz=f_h+f_bV+f_bH=%s kN/m)"
        % (_pt(s["f_v"]), _pt(s["f_horiz"])),
        "  Chapa cisalhamento 5.4   V_Rd = %s kN            util = %s %s"
        % (_pt(c["V_Rd"]), _pt(c["u"]), "OK" if c["OK"] else "*** NAO ATENDE ***"),
        "  Chapa flexao+FLT (Anexo G) M_Rd = %s kN.m  util = %s %s   [%s]"
        % (_pt(f["M_Rd"]), _pt(f["u"]), "OK" if f["OK"] else "*** NAO ATENDE ***",
           f.get("flt_regime", "-")),
    ] + ([
        "  Fadiga solda (Anexo K, cat.F, N=%.0e)  tau_SR = %s <= %s MPa  util = %s %s"
        % (res["fadiga"]["N"], _pt(res["fadiga"]["tau_sr"]), _pt(res["fadiga"]["sigma_rd"]),
           _pt(res["fadiga"]["u"]), "OK" if res["fadiga"]["OK"] else "*** NAO ATENDE ***")
    ] if res.get("fadiga") else []) + [
        "", "Governa: %s (util = %s)" % (res["governa"], _pt(res["u_max"])),
        "RESULTADO: %s" % ("ATENDE" if res["OK"] else "NAO ATENDE"), ""])


def _selftest():
    # caso bem-proporcionado (mísula L=0,45 m), 2 cordoes: Sw=L^2/3, A_w=2L.
    # f_dem = sqrt(f_v^2 + (f_h + f_bV + f_bH)^2), colineares no eixo x.
    Rv, Ht, ecc, L = 120.0, 12.0, 0.15, 0.45
    r = verifica_console({"Rv": Rv, "Ht": Ht, "ecc": ecc, "t": 0.016, "L": L,
                          "fy": 250e3, "fu": 400e3})
    M = Rv * ecc                                            # 18 kN.m
    Mz = Ht * (L / 2.0 + 0.0)                               # h_trilho default 0
    # grupo com comprimento EFETIVO L_ef = L - 2*perna adotada (crateras)
    L_ef = L - 2 * r["perna_mm"] / 1000.0
    assert abs(r["solda"]["L_ef"] - L_ef) < 1e-9
    f_v = Rv / (2 * L_ef)
    f_horiz = Ht / (2 * L_ef) + 3 * M / L_ef**2 + 3 * Mz / L_ef**2
    assert abs(r["solda"]["f_dem"] - math.sqrt(f_v**2 + f_horiz**2)) < 1e-6
    assert abs(r["solda"]["f_horiz"] - f_horiz) < 1e-9      # colineares somados
    # componentes horizontais NAO sao SRSS entre si (seria nao-conservador):
    srss3 = math.sqrt(f_v**2 + (Ht/(2*L_ef))**2 + (3*M/L_ef**2)**2 + (3*Mz/L_ef**2)**2)
    assert r["solda"]["f_dem"] > srss3                      # soma algebrica > SRSS
    # DIMENSIONA: menor perna-padrao (>= min Tab.9=6mm) cuja cap(1 cordao) >= dem
    cand = [p for p in (6.0, 8.0, 10.0, 12.0)
            if LG.fw_rd_filete(p / 1000.0, 1.0, 485e3)[0] >= r["solda"]["f_dem"]]
    assert abs(r["perna_mm"] - cand[0]) < 1e-9, (r["perna_mm"], cand)
    assert abs(r["solda"]["f_cap"] - LG.fw_rd_filete(r["perna_mm"] / 1000.0, 1.0, 485e3)[0]) < 1e-6
    assert r["solda"]["OK"]
    # h_trilho aumenta o braco de Ht -> f_dem maior
    rh = verifica_console({"Rv": Rv, "Ht": Ht, "ecc": ecc, "t": 0.016, "L": L,
                           "fy": 250e3, "fu": 400e3, "h_trilho": 0.10})
    assert rh["solda"]["f_dem"] > r["solda"]["f_dem"]
    # chapa em balanco: cisalhamento V_Rd=0,6*fy*t*L/ga1 ; flexao M_Rd=W*fy/ga1
    assert abs(r["chapa_cisalhamento"]["V_Rd"] - 0.6 * 250e3 * 0.016 * L / GA1) < 1e-6
    # flexao COM FLT (Anexo G, Tab. G.1): M_Rd = Mrd da chapa retangular macica,
    # nunca superior ao PLASTICO Mpl/ga1 (teto G.2.2). Para chapa robusta a FLT
    # entrega a reserva plastica (Mpl = 1,5*W*fy > elastico); para chapa esbelta,
    # REDUZ abaixo disso (FLT governa) - o que fecha o FLAG.
    flt_b = mrd_flt_chapa(0.016, L, ecc, 250e3)
    assert abs(r["chapa_flexao"]["M_Rd"] - flt_b["Mrd"]) < 1e-12
    assert flt_b["Mrd"] <= flt_b["Mpl"] / GA1 + 1e-9
    # M_Sd da chapa = |M| + |Mz| (flexao reta aditiva, mesmo eixo forte)
    assert abs(r["chapa_flexao"]["M_Sd"] - (abs(M) + abs(Mz))) < 1e-9
    # console curto/fino sob carga enorme: nem 12mm basta -> adota 12 e NAO ATENDE
    r2 = verifica_console({"Rv": 3000.0, "Ht": 300.0, "ecc": 0.60, "t": 0.006,
                           "L": 0.12, "fy": 250e3, "fu": 400e3})
    assert r2["perna_mm"] == 12.0 and not r2["OK"]
    # sem excentricidade e sem Ht -> f_horiz = 0 (so cisalhamento vertical)
    r3 = verifica_console({"Rv": 100.0, "Ht": 0.0, "ecc": 0.0, "t": 0.016,
                           "L": 0.45, "fy": 250e3, "fu": 400e3})
    assert abs(r3["solda"]["f_horiz"]) < 1e-12
    # FADIGA da solda (Anexo K cat.F): sem n_ciclos -> nao verifica (None)
    assert r["fadiga"] is None
    # com n_ciclos: tau_SR = f_dem/garganta vs faixa admissivel K.4b (cat.F).
    from ponte_rolante import faixa_admissivel_fadiga
    rf = verifica_console({"Rv": Rv, "Ht": Ht, "ecc": ecc, "t": 0.016, "L": L,
                           "fy": 250e3, "fu": 400e3, "n_ciclos": 2.0e6})
    fd = rf["fadiga"]
    garg = 0.707 * rf["perna_mm"] / 1000.0
    assert abs(fd["tau_sr"] - (rf["solda"]["f_dem"] / garg) / 1000.0) < 1e-6
    assert abs(fd["sigma_rd"] - faixa_admissivel_fadiga("F", 2.0e6)) < 1e-9
    # K.4b (cat.F): crossover em ~6e6 ciclos. N=2e6 (ponte B7) -> parte inclinada
    # governa (>55); N>=~6e6 (B9/B10) -> piso sigma_TH=55 MPa. Monotona decrescente.
    assert faixa_admissivel_fadiga("F", 2.0e6) > 55.0
    assert abs(faixa_admissivel_fadiga("F", 8.0e6) - 55.0) < 1e-9
    assert faixa_admissivel_fadiga("F", 2.0e6) > faixa_admissivel_fadiga("F", 4.0e6)
    assert fd["OK"] and rf["OK"]                     # console bem-proporcionado passa
    # console curtissimo sob carga enorme e muitos ciclos -> fadiga REPROVA e OK=False
    rf2 = verifica_console({"Rv": 800.0, "Ht": 80.0, "ecc": 0.40, "t": 0.016,
                            "L": 0.15, "fy": 250e3, "fu": 400e3, "n_ciclos": 2.0e6})
    assert rf2["fadiga"]["u"] > 1.0 and not rf2["fadiga"]["OK"] and not rf2["OK"]

    # ---- FLT da chapa retangular macica (NBR 8800 Anexo G, Tab. G.1) ----------
    # Reproduz o exemplo resolvido (Pfeil, via NotebookLM): chapa t=12,5mm x
    # L=270mm, balanco ecc=145mm, fy=250 MPa. Regime INELASTICO (lp<lam<lr);
    # Md=15,95 kN.m << Mrd -> ATENDE.
    ex = mrd_flt_chapa(0.0125, 0.27, 0.145, 250e3)
    assert ex["regime"] == "inelastico (FLT)"
    assert abs(ex["lam_p"] - 10.96) < 0.2 and abs(ex["lam_r"] - 252.9) < 2.0
    assert abs(ex["lam"] - 80.4) < 0.5
    assert 44.0 < ex["Mrd"] < 49.0                     # ~46,8 kN.m (com ga1)
    assert ex["Mrd"] < ex["Mpl"] / GA1                 # FLT reduz abaixo de Mpl/ga1
    # balanco CURTO -> lam<=lp -> plastificacao (Mrd = Mpl/ga1, sem reducao FLT)
    curto = mrd_flt_chapa(0.0125, 0.27, 0.002, 250e3)
    assert curto["regime"] == "plastificacao"
    assert abs(curto["Mrd"] - curto["Mpl"] / GA1) < 1e-9
    # balanco LONGO e chapa fina -> regime ELASTICO (lam>lr), Mrd cai bastante
    longo = mrd_flt_chapa(0.008, 0.30, 1.20, 250e3)
    assert longo["regime"] == "elastico (FLT)"
    assert longo["Mrd"] < longo["Mpl"] / GA1
    # monotonia: quanto maior o balanco, menor o Mrd (mais FLT)
    a1 = mrd_flt_chapa(0.016, 0.45, 0.15, 250e3)["Mrd"]
    a2 = mrd_flt_chapa(0.016, 0.45, 0.60, 250e3)["Mrd"]
    assert a2 < a1
    # o console (verifica_console) usa a FLT: chapa DEEP fina em balanco longo
    # reprova por flexao (FLT), nao passaria pelo elastico ingenuo.
    rflt = verifica_console({"Rv": 200.0, "Ht": 0.0, "ecc": 0.9, "t": 0.008,
                             "L": 0.30, "fy": 250e3, "fu": 400e3})
    assert rflt["chapa_flexao"]["flt_regime"] in ("inelastico (FLT)", "elastico (FLT)")
    print("console_ponte _selftest PASSED")


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(verifica_console({"Rv": 120.0, "Ht": 12.0, "ecc": 0.15,
                                        "t": 0.016, "L": 0.45, "fy": 250e3,
                                        "fu": 400e3})))
