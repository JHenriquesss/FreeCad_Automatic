# ============================================================================
# tercas_nbr14762.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica uma TERCA de cobertura em perfil formado a frio (secao U enrijecido,
# Ue) pela ABNT NBR 14762:2010. Generico: recebe qualquer perfil (dimensoes +
# propriedades de catalogo) e a configuracao (vao, linha de corrente, largura
# de influencia, inclinacao, CARGAS CARACTERISTICAS G/Q/W) e verifica:
#   - Momento resistente por escoamento da secao efetiva (9.8.2.1, MSE) -> caso
#     GRAVIDADE (mesa comprimida travada pela telha, sem FLT).
#   - Momento resistente sob SUCCAO (mesa comprimida livre): Anexo F -> R*Wef.
#   - Flambagem distorcional (9.8.2.3): dispensa (Tab.14) ou, se informado o
#     Mdist (analise de estabilidade elastica), entra no menor MRd.
#   - Cortante (9.8.3).
#   - Flexao obliqua: DECOMPOE SO A GRAVIDADE (vertical) em qx=G*cos e qy=G*sin;
#     o VENTO ja atua NORMAL ao telhado (so qx, sem qy). A linha de corrente
#     reduz o vao do eixo fraco. Interacao Msx/Mrdx + Msy/Mrdy.
#   - Eixo fraco: Wef,y (reducao por flambagem local da mesa comprimida) - NAO
#     usa o modulo bruto (que seria contra a seguranca sob sucao). APROXIMADO.
#   - Flecha (ELS): L/180 (gravidade) e L/120 (vento de sucao). Usa Ief do
#     catalogo (perfil["Ief"], rigoroso) OU o fallback conservador Ix*(Wef/W)
#     (subestima a rigidez -> flecha maior -> a favor da seguranca).
#   - Modelo estatico: a flag "continua" AUTO-seleciona os coeficientes -
#     BIAPOIADO (1/8, 1/2, 5/384) ou CONTINUO >=3 vaos iguais (1/10, 0,6,
#     2,6/384); ambos ainda sobrescrevveis por coef_momento/cortante/flecha.
# gamma_g FAVORAVEL: adotado 0,90 (conservador p/ uplift, NBR 8681 / criterio do
#   RT). A NBR 8800 Tabela 1 permite 1,00; configuravel via cfg["gamma"].
# Wef pelo MSE usa Wx (catalogo) + kl (Tabela 13, das dimensoes) -> baixo erro.
# ATENCAO: propriedades do perfil = do catalogo do fornecedor (A CONFIRMAR).
# Saidas em portugues. Calcula apenas; pendente revisao. Unidades SI: m, kN.
# ============================================================================
"""Verificacao de terca (Ue) conforme ABNT NBR 14762:2010 (9.8 + Anexo F)."""

from __future__ import annotations

import math

E = 200e6          # kN/m2 (modulo de elasticidade)
NU = 0.3           # coeficiente de Poisson
G_ACO = 77e6       # kN/m2 (modulo transversal)
GA = 1.10          # gamma para flexao/cortante (NBR 14762 9.8)

# Tabela 13 (NBR 14762) - kl da secao COMPLETA, flexao no eixo de maior inercia,
# Caso b (U enrijecido). Colunas: mu<=0,2 ; mu=0,25 ; mu=0,30 (mu = D/bw).
_TAB13 = {
    0.2: (32.0, 25.8, 21.2), 0.3: (29.3, 23.8, 19.7), 0.4: (24.8, 20.7, 18.2),
    0.5: (18.7, 17.6, 16.0), 0.6: (13.6, 13.3, 13.0), 0.7: (10.2, 10.1, 10.1),
    0.8: (7.9, 7.9, 7.9), 0.9: (6.2, 6.3, 6.3), 1.0: (5.1, 5.1, 5.1),
}


def _interp(x, x0, x1, y0, y1):
    if x1 == x0:
        return y0
    return y0 + (x - x0) / (x1 - x0) * (y1 - y0)


def k_local(bf, bw, D):
    """kl da Tabela 13 (Ue) por interpolacao dupla em zeta=bf/bw e mu=D/bw."""
    zeta = min(max(bf / bw, 0.2), 1.0)
    mu = min(max(D / bw, 0.0), 0.3)
    zs = sorted(_TAB13)
    z0 = max([z for z in zs if z <= zeta], default=zs[0])
    z1 = min([z for z in zs if z >= zeta], default=zs[-1])
    # interpola em mu (0,2 ; 0,25 ; 0,3) para cada zeta vizinho
    def _kmu(row):
        if mu <= 0.2:
            return row[0]
        if mu <= 0.25:
            return _interp(mu, 0.2, 0.25, row[0], row[1])
        return _interp(mu, 0.25, 0.3, row[1], row[2])
    k0, k1 = _kmu(_TAB13[z0]), _kmu(_TAB13[z1])
    return _interp(zeta, z0, z1, k0, k1)


def Wef_MSE(W, Wc, kl, bw, t, fy):
    """Modulo resistente da secao efetiva (9.8.2.1, MSE)."""
    Ml = kl * math.pi ** 2 * E / (12 * (1 - NU ** 2)) * (t / bw) ** 2 * Wc
    lp = math.sqrt(W * fy / Ml)
    Wef = W if lp <= 0.673 else W * (1 - 0.22 / lp) / lp
    return Wef, Ml, lp


def fator_R_anexoF(bw_mm, secao="U", continua=False):
    """Tabela F.1: fator R para mesa comprimida livre (sucao)."""
    if continua:
        if bw_mm > 292:
            return None                            # fora do escopo do Anexo F (F.1-b)
        return 0.70 if secao == "Z" else 0.60      # bw <= 292
    if bw_mm <= 165:
        return 0.70
    if bw_mm <= 216:
        return 0.65
    if bw_mm <= 292:
        return 0.50 if secao == "Z" else 0.40
    return None                                     # fora do escopo do Anexo F


# Tabela 14: D/bw minimo para DISPENSAR distorcional (flexao, Ue). bw/t nas
# colunas (250,200,125,100,50) ; bf/bw nas linhas.
_TAB14_BWT = [250, 200, 125, 100, 50]
_TAB14 = {
    0.4: [0.05, 0.06, 0.10, 0.12, 0.25], 0.6: [0.05, 0.06, 0.10, 0.12, 0.25],
    0.8: [0.05, 0.06, 0.09, 0.12, 0.22], 1.0: [0.05, 0.06, 0.09, 0.11, 0.22],
    1.2: [0.05, 0.06, 0.09, 0.11, 0.20], 1.4: [0.05, 0.06, 0.09, 0.10, 0.20],
    1.6: [0.05, 0.06, 0.09, 0.10, 0.20], 1.8: [0.05, 0.06, 0.09, 0.10, 0.19],
    2.0: [0.05, 0.06, 0.09, 0.10, 0.19],
}


def dispensa_distorcional(bw, bf, D, t):
    """True se D/bw >= limite da Tabela 14 (dispensa a verificacao)."""
    bwt = bw / t
    ratio = bf / bw            # bf/bw (a tabela usa bf/bw)
    rs = sorted(_TAB14)
    r0 = max([r for r in rs if r <= ratio], default=rs[0])
    # coluna por bw/t (interpola nas colunas)
    cols = _TAB14_BWT
    def _colval(row):
        if bwt >= cols[0]:
            return row[0]
        if bwt <= cols[-1]:
            return row[-1]
        for a, b in zip(cols, cols[1:]):
            if b <= bwt <= a:
                return _interp(bwt, a, b, row[cols.index(a)], row[cols.index(b)])
        return row[-1]
    lim = _colval(_TAB14[r0])
    return (D / bw) >= lim, lim


def cortante_Vrd(h, t, fy, kv=5.0):
    """9.8.3: forca cortante resistente (kv=5 sem enrijecedores)."""
    lam = h / t
    lp = 1.08 * math.sqrt(E * kv / fy)
    lr = 1.40 * math.sqrt(E * kv / fy)
    if lam <= lp:
        return 0.6 * fy * h * t / GA
    if lam <= lr:
        return 0.65 * t ** 2 * math.sqrt(kv * fy * E) / GA
    return (0.905 * E * kv * t ** 3 / h) / GA


def Wef_y_mesa(bf, t, Wy, fy, k=4.0):
    """Wef do EIXO FRACO (conservador): aplica a reducao de flambagem local da
    MESA comprimida (elemento AA entre alma e enrijecedor, k=4) ao modulo Wy.
    9.2.2 (MLE): lambda_p=(b/t)/(0,95*sqrt(kE/fy)) ; rho=(1-0,22/lp)/lp.
    Evita usar Wy bruto, que superestima a resistencia sob sucao."""
    b = (bf - 2 * t) / 1000.0
    tm = t / 1000.0
    lp = (b / tm) / (0.95 * math.sqrt(k * E / fy))
    rho = 1.0 if lp <= 0.673 else (1 - 0.22 / lp) / lp
    return rho * Wy, rho, lp


def flecha_biapoiada(q, L, I):
    """Flecha no meio do vao de viga biapoiada sob carga uniforme (5qL^4/384EI)."""
    return 5.0 * abs(q) * L ** 4 / (384.0 * E * I)


def chi_distorcional(W, fy, Mdist):
    """9.8.2.3: fator de reducao distorcional a partir do Mdist (elastico)."""
    lam = math.sqrt(W * fy / Mdist)
    chi = 1.0 if lam <= 0.673 else (1 - 0.22 / lam) / lam
    return chi, lam


def verifica_terca(perfil, cfg):
    """perfil: dict com dims (mm) e propriedades de catalogo (SI).
    cfg: config com CARGAS CARACTERISTICAS G, Q, W (kN/m2 ; W<0 = sucao)."""
    bw, bf, D, t = perfil["bw"], perfil["bf"], perfil["D"], perfil["t"]  # mm
    bw_m, t_m = bw / 1000.0, t / 1000.0
    h = perfil.get("h_alma_plana", bw - 2 * (t + perfil.get("r", 0))) / 1000.0
    fy = cfg["fy"]
    W = perfil["Wx"]                     # modulo elastico bruto (SI)
    Wc = perfil.get("Wxc", W)            # comp. (U simetrico no eixo x: = W)
    Wy = perfil["Wy"]                    # eixo fraco (bruto)
    Ix = perfil["Ix"]

    kl = k_local(bf, bw, D)
    Wef, Ml, lp = Wef_MSE(W, Wc, kl, bw_m, t_m, fy)

    # ---- eixo forte: momentos resistentes ---------------------------------
    Mrd_local = Wef * fy / GA                                  # 9.8.2.1
    R = fator_R_anexoF(bw, perfil.get("secao", "U"), cfg.get("continua", False))
    Mrd_succ_local = (R * Wef * fy / GA) if R else None        # Anexo F
    # distorcional (9.8.2.3): dispensa (Tab.14) ou Mdist informado
    disp, lim14 = dispensa_distorcional(bw, bf, D, t)
    Mdist = cfg.get("Mdist")
    Mrd_dist = chi = lam_d = None
    dist_inconclusivo = False
    if not disp:
        if Mdist:
            chi, lam_d = chi_distorcional(W, fy, Mdist)
            Mrd_dist = chi * W * fy / GA
        else:
            dist_inconclusivo = True         # nao dispensada e sem Mdist
    # MRd finais (menor entre local/Anexo F e distorcional, se houver)
    def _min_dist(m):
        return min(m, Mrd_dist) if (m and Mrd_dist) else m
    Mrd_grav = _min_dist(Mrd_local)
    Mrd_succ = _min_dist(Mrd_succ_local)

    # ---- eixo fraco: Wef,y (flambagem local da mesa; NAO usa bruto) --------
    if perfil.get("Wefy"):                     # rigoroso, do catalogo/software
        Wefy = perfil["Wefy"]
        rho_y = Wefy / Wy
    else:                                      # aproximado (rho da mesa)
        Wefy, rho_y, _ = Wef_y_mesa(bf, t, Wy, fy)
    Mrdy = Wefy * fy / GA

    Vrd = cortante_Vrd(h, t_m, fy)

    theta = cfg["theta"]
    L = cfg["vao"]
    Ly = cfg.get("vao_fraco", L)
    trib = cfg["larg_influencia"]
    ct, st = math.cos(theta), math.sin(theta)
    Gk, Qk, Wk = cfg.get("G", 0.0), cfg.get("Q", 0.0), cfg.get("W", 0.0)
    # gamma_g FAVORAVEL = 0,90 (conservador para uplift; NBR 8681 / criterio do
    # RT). NBR 8800 Tabela 1 permite 1,00 - sobrescrever via cfg["gamma"].
    g = cfg.get("gamma", {"G": 1.25, "Q": 1.50, "W": 1.40, "G_fav": 0.90})
    # modelo estatico: a flag "continua" AUTO-seleciona os coeficientes.
    continua = cfg.get("continua", False)
    if continua:                              # viga continua (>=3 vaos iguais)
        cM = cfg.get("coef_momento", 1.0 / 10.0)
        cV = cfg.get("coef_cortante", 0.60)
        cD = cfg.get("coef_flecha", 2.6 / 384.0)
        aviso_estatico = ("modelo CONTINUO (>=3 vaos iguais: M=qL2/10, V=0,6qL, "
                          "flecha=2,6qL4/384EI). Para 2 vaos use continua=False.")
    else:                                     # biapoiada (isostatica)
        cM = cfg.get("coef_momento", 1.0 / 8.0)
        cV = cfg.get("coef_cortante", 1.0 / 2.0)
        cD = cfg.get("coef_flecha", 5.0 / 384.0)
        aviso_estatico = "modelo BIAPOIADO (M=qL2/8, V=qL/2, flecha=5qL4/384EI)."
    # inercia efetiva (ELS): catalogo (rigoroso) OU fallback conservador Ix*Wef/W
    Ief = perfil.get("Ief")
    Ief_fonte = "catalogo/servico" if Ief else "aprox. Ix*(Wef/W)"
    if not Ief:
        Ief = Ix * (Wef / W)
    aviso_y = ("Mrd,y por metodo APROXIMADO (rho da mesa sobre Wy, k=4 uniforme; "
               "rigor pede a flexao com gradiente de tensoes e centroide efetivo "
               "no eixo y). Sobrescrever com perfil['Wefy'] se disponivel.")

    res = {"perfil": perfil.get("nome", "Ue"), "kl": kl, "Wef": Wef, "Ml": Ml,
           "lp": lp, "Mrd_local": Mrd_local, "Mrd_grav": Mrd_grav,
           "Mrd_succ": Mrd_succ, "R": R, "Mrdy": Mrdy, "Wefy": Wefy,
           "rho_y": rho_y, "Vrd": Vrd, "dispensa_dist": disp, "lim_tab14": lim14,
           "Mrd_dist": Mrd_dist, "dist_inconclusivo": dist_inconclusivo,
           "Ief": Ief, "Ief_fonte": Ief_fonte, "aviso_eixo_fraco": aviso_y,
           "aviso_estatico": aviso_estatico, "casos": {}, "els": {}}

    # ---- ELU: combos (vento NORMAL ao telhado -> so qx ; gravidade decompoe)
    # carga por metro de terca (kN/m): gravidade vertical ; vento normal
    def _combo(nome, vG, vQ, vW):
        vert = (vG * Gk + vQ * Qk) * trib          # vertical (kN/m), para baixo>0
        wn = vW * Wk * trib                         # vento normal (W<0 = sucao)
        qx = vert * ct + wn                         # eixo forte (perp. telhado)
        qy = vert * st                              # eixo fraco (so gravidade)
        Msx = cM * abs(qx) * L ** 2
        Msy = cM * abs(qy) * Ly ** 2
        Vsx = cV * abs(qx) * L
        uplift = qx < 0                             # mesa comprimida livre
        Mrdx = Mrd_succ if (uplift and Mrd_succ) else Mrd_grav
        inter = (Msx / Mrdx + Msy / Mrdy) if Mrdx else float("inf")
        okv = Vsx / Vrd
        # 9.8.4 M+V combinados, alma SEM enrijecedores transversais (terca):
        # (Msd/Mrd)^2 + (Vsd/Vrd)^2 <= 1,0 . Usa a utilizacao de flexao biaxial
        # (inter) como termo de momento (conservador na flexao obliqua).
        mv = inter ** 2 + okv ** 2
        ok = (inter <= 1.0 and okv <= 1.0 and mv <= 1.0
              and not (uplift and dist_inconclusivo))
        res["casos"][nome] = {"qx": qx, "qy": qy, "Msx": Msx, "Msy": Msy,
                              "Vsx": Vsx, "Mrdx": Mrdx, "uplift": uplift,
                              "interacao": inter, "uV": okv, "mv": mv, "OK": ok}

    gf = g.get("G_fav", 0.90)
    _combo("gravidade 1,25G+1,5Q", g["G"], g["Q"], 0.0)
    _combo(f"sucao {gf:.2g}G+1,4W".replace(".", ","), gf, 0.0, g["W"])

    # ---- ELS: flecha (cargas caracteristicas, sem majoracao) --------------
    # gravidade (mesmo sentido G): limite L/180 ; vento sucao (oposto): L/120
    # flecha com Ief (nao Ix bruto) e coeficiente cD (default biapoiado)
    qx_grav = (Gk + Qk) * trib * ct
    d_grav = cD * abs(qx_grav) * L ** 4 / (E * Ief)
    qx_vento = (Gk * trib * ct) + (Wk * trib)      # G para baixo + W sucao
    d_vento = cD * abs(qx_vento) * L ** 4 / (E * Ief)
    res["els"] = {"d_grav": d_grav, "lim_grav": L / 180.0,
                  "ok_grav": d_grav <= L / 180.0,
                  "d_vento": d_vento, "lim_vento": L / 120.0,
                  "ok_vento": d_vento <= L / 120.0}
    return res


def relatorio_pt(res, cfg):
    e = res["els"]
    L = ["VERIFICACAO DE TERCA (ABNT NBR 14762:2010 - 9.8 + Anexo F)",
         f"  Perfil: {res['perfil']}  (propriedades A CONFIRMAR no catalogo)",
         f"  fy = {cfg['fy']/1000:.0f} MPa ; vao = {cfg['vao']:.2f} m ; "
         f"vao eixo fraco = {cfg.get('vao_fraco', cfg['vao']):.2f} m (linha de corrente)",
         f"  Largura de influencia = {cfg['larg_influencia']:.3f} m ; "
         f"inclinacao = {math.degrees(cfg['theta']):.2f} graus",
         f"  Cargas caracteristicas: G={cfg.get('G',0):.3f} Q={cfg.get('Q',0):.3f} "
         f"W={cfg.get('W',0):+.3f} kN/m2",
         f"  Flambagem local: kl = {res['kl']:.2f} ; Ml = {res['Ml']:.2f} kN.m ; "
         f"lambda_p = {res['lp']:.3f}",
         f"  Wef = {res['Wef']*1e6:.2f} cm3 ; Mrd(local) = {res['Mrd_local']:.2f} kN.m",
         (f"  Anexo F: R = {res['R']} ; Mrd(succao) = {res['Mrd_succ']:.2f} kN.m"
          if res['Mrd_succ'] else "  Anexo F: fora do escopo (bw>292)"),
         f"  Eixo fraco: rho_y = {res['rho_y']:.3f} -> Wef,y = {res['Wefy']*1e6:.2f} cm3 "
         f"; Mrd,y = {res['Mrdy']:.2f} kN.m (NAO usa Wy bruto)",
         f"  [AVISO] {res['aviso_eixo_fraco']}",
         f"  Vrd = {res['Vrd']:.2f} kN ; Ief (ELS) = {res['Ief']*1e8:.0f} cm4 "
         f"({res['Ief_fonte']})",
         f"  Modelo estatico: {res['aviso_estatico']}"]
    if res["dispensa_dist"]:
        L.append(f"  Distorcional: DISPENSADA (D/bw >= {res['lim_tab14']:.3f}, Tab.14)")
    elif res["Mrd_dist"]:
        L.append(f"  Distorcional: Mrd,dist = {res['Mrd_dist']:.2f} kN.m "
                 f"(entra no menor MRd)")
    else:
        L.append(f"  Distorcional: NAO DISPENSADA e SEM Mdist informado -> "
                 f"INCONCLUSIVO sob sucao (exige analise de estabilidade elastica).")
    L += [f"  Mrd,x final: gravidade = {res['Mrd_grav']:.2f} ; "
          f"succao = {res['Mrd_succ']:.2f} kN.m" if res['Mrd_succ'] else
          f"  Mrd,x gravidade = {res['Mrd_grav']:.2f} kN.m", ""]
    for nome, c in res["casos"].items():
        L += [f"  --- ELU {nome} ({'SUCCAO/mesa livre' if c['uplift'] else 'gravidade'}) ---",
              f"    qx={c['qx']:+.3f} qy={c['qy']:+.3f} kN/m ; "
              f"Msx={c['Msx']:.2f} Msy={c['Msy']:.2f} kN.m ; Vsx={c['Vsx']:.2f} kN",
              f"    Interacao Msx/Mrdx + Msy/Mrdy = {c['Msx']:.2f}/{c['Mrdx']:.2f} + "
              f"{c['Msy']:.2f}/{res['Mrdy']:.2f} = {c['interacao']:.2f} ; "
              f"V/Vrd={c['uV']:.2f}",
              f"    9.8.4 M+V (alma s/ enrijec.): (M/Mrd)^2+(V/Vrd)^2 = "
              f"{c['mv']:.2f}  -> {'OK' if c['OK'] else 'NAO PASSA'}"]
    L += ["", "  --- ELS (flecha, cargas caracteristicas) ---",
          f"    Gravidade: {e['d_grav']*1000:.1f} mm ; limite L/180 = "
          f"{e['lim_grav']*1000:.1f} mm -> {'OK' if e['ok_grav'] else 'NAO ATENDE'}",
          f"    Vento (sucao): {e['d_vento']*1000:.1f} mm ; limite L/120 = "
          f"{e['lim_vento']*1000:.1f} mm -> {'OK' if e['ok_vento'] else 'NAO ATENDE'}"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


# ---- auto-teste ------------------------------------------------------------
def _selftest():
    assert abs(k_local(0.5 * 100, 100, 0.2 * 100) - 18.7) < 1e-6
    assert abs(k_local(1.0 * 100, 100, 0.0) - 5.1) < 1e-6
    W = 50e-6
    Wef, Ml, lp = Wef_MSE(W, W, 20.0, 0.100, 0.003, 250e3)
    assert lp <= 0.673 and abs(Wef - W) < 1e-12, (lp, Wef)
    # flecha biapoiada: 5qL^4/384EI (q=1 kN/m, L=1 m, I=1e-6 m4)
    d = flecha_biapoiada(1.0, 1.0, 1e-6)
    assert abs(d - 5.0 / (384 * 200e6 * 1e-6)) < 1e-12
    # Wef,y reduz (rho<1) para mesa esbelta
    Wefy, rho, lpy = Wef_y_mesa(75.0, 2.0, 12e-6, 250e3)
    assert rho <= 1.0
    print("tercas_nbr14762 self-test PASSED")
    print(f"  k_local(zeta=0,5; mu=0,2) = {k_local(50,100,20):.2f} (Tab.13=18,7)")
    print(f"  Wef(compacta)=W ; lambda_p={lp:.3f} ; rho_y(mesa 75x2)={rho:.3f}")


# ---- exemplo PLACEHOLDER (a skill pergunta ao usuario) ---------------------
PERFIL_EXEMPLO = {
    "nome": "Ue 200x75x25x2.65 (EXEMPLO - confirmar catalogo)",
    "bw": 200.0, "bf": 75.0, "D": 25.0, "t": 2.65, "r": 3.0, "secao": "U",
    "A": 8.03e-4, "Ix": 480e-8, "Iy": 63e-8, "Wx": 48.0e-6, "Wy": 12.0e-6,
}
CFG_EXEMPLO = {
    "fy": 250e3, "theta": math.atan(0.5 / 5.0), "vao": 5.0, "vao_fraco": 2.5,
    "larg_influencia": 1.675, "continua": False,
    "G": 0.15, "Q": 0.25, "W": -0.90,      # cargas CARACTERISTICAS (kN/m2)
    "Mdist": None,                          # informar se distorcional nao dispensa
}


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(verifica_terca(PERFIL_EXEMPLO, CFG_EXEMPLO), CFG_EXEMPLO))
