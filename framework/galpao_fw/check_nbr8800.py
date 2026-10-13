# ============================================================================
# check_nbr8800.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica um perfil I/H laminado pela ABNT NBR 8800 dados os esforcos
# solicitantes (Nsd, Msd, Vsd).
#   Compressao: NBR 8800:2024/Er1:2025, 5.3 (lida no MCP_Fontes em 2026-10-13,
#     D226): Nc,Rd = chi.Aef.fy/ga1; chi de 5.3.3 com lambda0 = raiz(Ag.fy/Ne);
#     Ne = menor entre flexao em x, flexao em y e torcao (5.3.5.1); Aef pelas
#     larguras efetivas de 5.3.4.2 (Tabelas 4 e 5). A edicao de 2008 fazia a
#     flambagem local pelo fator Q do Anexo F (`fator_Q`, mantido para a tesoura).
#   Flexao e cortante: formulas da edicao de 2008 (Anexo G e 5.4.3), AINDA NAO
#     conferidas contra a edicao de 2024.
#   Flexao (5.4 / Anexo G, Tabela G.1): estados-limite FLT, FLM e FLA com as
#     formulas exatas (Mr = 0,7 fy W ; Lr, Mcr com Cw e J calculados da geometria;
#     Mn = menor dos tres). Cw = Iy(d-tf)^2/4 ; J = soma(b t^3)/3.
#   Cortante (5.4.3): com verificacao de esbeltez da alma.
#   Interacao flexo-compressao (5.5.1.2).
# ATENCAO: os esforcos de entrada Nsd/Msd ja devem vir amplificados pela analise
# de 2a ordem (B1/B2). Este script verifica a SECAO, nao a estabilidade global.
# NAO calcula esforcos (vem do galpao_portico). Calcula apenas; pendente revisao.
# ============================================================================
"""Verificacao de perfil metalico conforme ABNT NBR 8800:2008 (Anexos F e G)."""

from __future__ import annotations

import math

E = 200e6          # kN/m2 (200 GPa) - NBR 8800:2024, 4.6.2.9 a)
G_ACO = 77e6       # kN/m2 (77 GPa)  - NBR 8800:2024, 4.6.2.9 c)
GA1 = 1.10
# NBR 8800:2024, Tabela 5 - fatores (c1, c2) da largura efetiva
C_AA, C_AL = (0.18, 1.31), (0.22, 1.49)


def chi_compressao(lambda0):
    """NBR 8800 5.3.3 / Tabela 4."""
    if lambda0 <= 1.5:
        return 0.658 ** (lambda0 ** 2)
    return 0.877 / lambda0 ** 2


def _largura_efetiva(b, t, lim, c, chi, fy):
    """NBR 8800:2024, 5.3.4.2: largura efetiva do elemento de largura b e
    espessura t, com (b/t)lim da Tabela 4 e (c1, c2) da Tabela 5."""
    bt = b / t
    if bt <= lim / math.sqrt(chi):
        return b
    sigma_el = (c[1] * lim / bt) ** 2 * fy
    raiz = math.sqrt(sigma_el / (chi * fy))
    return b * (1.0 - c[0] * raiz) * raiz


def area_efetiva(sec, fy, chi):
    """NBR 8800:2024, 5.3.4: area efetiva do perfil I/H laminado na compressao.
    Mesas: 4 abas AL do grupo 4, (b/t)lim = 0,56.raiz(E/fy), b = bf/2. Alma: AA
    do grupo 2, (b/t)lim = 1,49.raiz(E/fy), b = d - 2.tf (sem o raio de
    concordancia: alma um pouco mais esbelta que a real). Devolve (Aef, razao
    bef/b da mesa, razao bef/b da alma)."""
    bf, tf, d, tw = sec["bf"], sec["tf"], sec["d"], sec["tw"]
    h = d - 2 * tf
    rE = math.sqrt(E / fy)
    b_mesa = bf / 2.0
    ef_mesa = _largura_efetiva(b_mesa, tf, 0.56 * rE, C_AL, chi, fy)
    ef_alma = _largura_efetiva(h, tw, 1.49 * rE, C_AA, chi, fy)
    aef = sec["A"] - 4.0 * (b_mesa - ef_mesa) * tf - (h - ef_alma) * tw
    return aef, ef_mesa / b_mesa, ef_alma / h


def fator_Q(sec, fy):
    """NBR 8800:2008, Anexo F: Q = Qs (mesa, Grupo 4) * Qa (alma, Grupo 2).
    Metodo da edicao anterior; `verifica` usa a area efetiva de 2024."""
    bf, tf, d, tw = sec["bf"], sec["tf"], sec["d"], sec["tw"]
    h = d - 2 * tf
    rE = math.sqrt(E / fy)
    # Qs - mesa (elemento AL, Grupo 4)
    bt_f = (bf / 2.0) / tf
    lim1, lim2 = 0.56 * rE, 1.03 * rE
    if bt_f <= lim1:
        Qs = 1.0
    elif bt_f < lim2:
        Qs = 1.415 - 0.74 * bt_f * math.sqrt(fy / E)
    else:
        Qs = 0.69 * E / (fy * bt_f ** 2)
    # Qa - alma (elemento AA, Grupo 2)
    bt_w = h / tw
    limw = 1.49 * rE
    if bt_w <= limw:
        Qa = 1.0
    else:
        # F.3.2 largura efetiva (ca=0,34), sigma=fy (conservador)
        t = tw
        bef = 1.92 * t * rE * (1 - 0.34 / bt_w * rE)
        bef = min(bef, h)
        Aef = sec["A"] - (h - bef) * tw
        Qa = Aef / sec["A"]
    return Qs * Qa, Qs, Qa, bt_f, bt_w


def _cw_j(sec):
    """Cw = Iy(d-tf)^2/4 ; J = (2 bf tf^3 + (d-2tf) tw^3)/3."""
    bf, tf, d, tw, Iy = sec["bf"], sec["tf"], sec["d"], sec["tw"], sec["Iy"]
    Cw = Iy * (d - tf) ** 2 / 4.0
    J = (2 * bf * tf ** 3 + (d - 2 * tf) * tw ** 3) / 3.0
    return Cw, J


def _interp_M(lam, lamp, lamr, Mpl, Mr, Mcr, Cb=1.0):
    """G.2.1: Mn plastificacao / inelastico (interp) / elastico."""
    if lam <= lamp:
        return Mpl
    if lam <= lamr:
        return min(Cb * (Mpl - (Mpl - Mr) * (lam - lamp) / (lamr - lamp)), Mpl)
    return min(Mcr, Mpl)


def momento_resistente(sec, fy, Lb, Cb=1.0):
    """Menor Mn entre FLT, FLM, FLA (Tabela G.1, I duplo eixo, eixo forte).
    Se a alma for ESBELTA (h/tw > 5,70 sqrt(E/fy)), despacha para o Anexo H
    (viga de alma esbelta: Wxc/Wxt + kpg), em vez de abortar."""
    Zx, Wx, ry, bf, tf, d, tw = (sec["Zx"], sec["Wx"], sec["ry"], sec["bf"],
                                 sec["tf"], sec["d"], sec["tw"])
    Iy = sec["Iy"]
    h = d - 2 * tf
    # despacho para o Anexo H quando a alma e esbelta (h/tw > 5,70 sqrt(E/fy)).
    if h / tw > 5.70 * math.sqrt(E / fy):
        import alma_esbelta as ae
        rh = ae.mrd_alma_esbelta(sec, fy, Lb, Cb)
        Mn = rh["Mn"]
        det = {"Mpl": None, "Lp": None, "Lr_flt": None,
               "Mn_flt": rh["M_flt"], "Mn_flm": rh["M_flm"], "Mn_fla": rh["M_esc"],
               "kpg": rh["kpg"], "kc": rh["kc"], "ryT": rh["ryT"],
               "fora_validade": rh["fora_validade"], "anexo": "H"}
        return Mn, rh["gov"], det
    Mpl = Zx * fy
    sr = 0.3 * fy                     # tensao residual
    rE = math.sqrt(E / fy)
    Cw, J = _cw_j(sec)

    # FLT
    lam = Lb / ry
    lamp = 1.76 * rE
    Mr_flt = (fy - sr) * Wx
    b1 = (fy - sr) * Wx / (E * J)
    lamr_flt = (1.38 * math.sqrt(Iy * J)) / (ry * J * b1) * \
        math.sqrt(1 + math.sqrt(1 + 27 * Cw * b1 ** 2 / Iy))
    Mcr_flt = (Cb * math.pi ** 2 * E * Iy / Lb ** 2) * \
        math.sqrt(Cw / Iy + 0.039 * J * Lb ** 2 / Iy)
    Mn_flt = _interp_M(lam, lamp, lamr_flt, Mpl, Mr_flt, Mcr_flt, Cb)

    # FLM (mesa, laminado)
    lam_m = (bf / 2.0) / tf
    lamp_m = 0.38 * rE
    lamr_m = 0.83 * math.sqrt(E / (fy - sr))
    Mr_m = (fy - sr) * Wx
    Mcr_m = 0.69 * E * Wx / lam_m ** 2
    Mn_flm = _interp_M(lam_m, lamp_m, lamr_m, Mpl, Mr_m, Mcr_m)

    # FLA (alma)
    lam_a = h / tw
    lamp_a = 3.76 * rE
    lamr_a = 5.70 * rE
    if lam_a > lamr_a:                 # alma esbelta: fora do escopo (Tabela G.1)
        raise ValueError(
            f"{sec.get('nome', 'perfil')}: esbeltez da alma h/tw={lam_a:.1f} > "
            f"lamr={lamr_a:.1f}. Alma esbelta -> dimensionar como viga de alma "
            f"cheia (NBR 8800 Anexo H); fora do escopo deste verificador.")
    Mr_a = fy * Wx
    Mn_fla = _interp_M(lam_a, lamp_a, lamr_a, Mpl, Mr_a, Mpl)  # alma nao-esbelta

    Mn = min(Mn_flt, Mn_flm, Mn_fla)
    gov = ["FLT", "FLM", "FLA"][[Mn_flt, Mn_flm, Mn_fla].index(Mn)]
    return Mn, gov, {"Mpl": Mpl, "Lp": lamp * ry, "Lr_flt": lamr_flt * ry,
                     "Mn_flt": Mn_flt, "Mn_flm": Mn_flm, "Mn_fla": Mn_fla,
                     "Cw": Cw, "J": J, "anexo": "G"}


def verifica(sec, fy, L, Nsd, Msd, Vsd, Kx=1.0, Ky=1.0, Lb=None, Cb=1.0, nome=""):
    A, Ix, Iy = sec["A"], sec["Ix"], sec["Iy"]
    d, tw, tf = sec["d"], sec["tw"], sec["tf"]
    Aw = d * tw                       # area de cisalhamento (laminado): d*tw
    if Lb is None:
        Lb = L
    r = {"nome": nome}

    # Compressao (NBR 8800:2024, 5.3): Ne de 5.3.5.1 (flexao em x, em y e torcao,
    # esta com o mesmo comprimento destravado de y), chi de 5.3.3 e Aef de 5.3.4
    Cw, J = _cw_j(sec)
    Nex = math.pi ** 2 * E * Ix / (Kx * L) ** 2
    Ney = math.pi ** 2 * E * Iy / (Ky * Lb) ** 2
    Nez = (math.pi ** 2 * E * Cw / (Ky * Lb) ** 2 + G_ACO * J) / ((Ix + Iy) / A)
    Ne = min(Nex, Ney, Nez)
    lambda0 = math.sqrt(A * fy / Ne)
    chi = chi_compressao(lambda0)
    Aef, Qs, Qa = area_efetiva(sec, fy, chi)
    Q = Aef / A
    Nc_Rd = chi * Aef * fy / GA1
    r.update(Q=Q, Qs=Qs, Qa=Qa, Aef=Aef, Ne=Ne, Nex=Nex, Ney=Ney, Nez=Nez,
             lambda0=lambda0, chi=chi, Nc_Rd=Nc_Rd)

    # Flexao (Anexo G)
    Mn, gov, det = momento_resistente(sec, fy, Lb, Cb)
    Mrd = Mn / GA1
    r.update(Mrd=Mrd, M_gov=gov, **det)

    # Cortante (5.4.3.1.1): tres dominios, kv=5 (alma sem enrijecedores)
    h = d - 2 * tf
    lamw = h / tw
    lamw_p = 1.10 * math.sqrt(5.0 * E / fy)   # escoamento (plastificacao)
    lamw_r = 1.37 * math.sqrt(5.0 * E / fy)   # flambagem elastica
    Vpl = 0.6 * Aw * fy
    if lamw <= lamw_p:
        Vn = Vpl                                   # plastificacao da alma
    elif lamw <= lamw_r:
        Vn = Vpl * (lamw_p / lamw)                 # flambagem inelastica
    else:
        Vn = Vpl * 1.24 * (lamw_p / lamw) ** 2     # flambagem elastica
    Vrd = Vn / GA1
    r["Vrd"] = Vrd
    r["alma_compacta_cisalhamento"] = lamw <= lamw_p

    # Utilizacao + interacao (5.5.1.2)
    r["u_N"] = Nsd / Nc_Rd
    r["u_M"] = Msd / Mrd
    r["u_V"] = Vsd / Vrd
    # NBR 8800 5.5.1.2 aplica-se a forca axial de tracao OU compressao: a interacao
    # SOMA os modulos das utilizacoes. Usar abs() impede que a tracao (Nsd<0) subtraia
    # da flexao (flexo-tracao) e mascare a solicitacao acumulada na mesa tracionada.
    n, m = abs(Nsd) / Nc_Rd, abs(Msd) / Mrd
    if n >= 0.2:
        inter, eq = n + (8.0 / 9.0) * m, "N/Nrd + 8/9*(M/Mrd)"
    else:
        inter, eq = n / 2.0 + m, "N/(2Nrd) + M/Mrd"
    r.update(interacao=inter, eq_interacao=eq)
    r["OK"] = inter <= 1.0 and r["u_V"] <= 1.0
    return r


def relatorio_pt(rs, fy):
    L = ["VERIFICACAO DE PERFIS (ABNT NBR 8800: compressao pela edicao de 2024, 5.3;",
         "  flexao e cortante pelas formulas da edicao de 2008, Anexo G e 5.4.3)",
         f"  fy = {fy/1000:.0f} MPa ; gamma_a1 = {GA1:.2f}",
         "  ATENCAO: Nsd/Msd devem vir amplificados por B1/B2 (2a ordem)."]
    for r in rs:
        # Alma esbelta (Anexo H): Mpl/Lp/Lr_flt = None e nao ha Cw/J no dict.
        if r.get("anexo") == "H":
            flexao = (f"  Flexao (Anexo H, alma esbelta): kpg={r['kpg']:.3f} ; "
                      f"kc={r['kc']:.3f} ; ryT={r['ryT']:.4f} m")
        else:
            flexao = (f"  Flexao: Mpl={r['Mpl']:.1f} ; Lp={r['Lp']:.2f} m ; "
                      f"Lr(FLT)={r['Lr_flt']:.2f} m ; Cw={r['Cw']:.3e} ; J={r['J']:.3e}")
        L += ["",
              f"  --- {r['nome']} ---",
              f"  Largura efetiva (5.3.4): mesa bef/b={r['Qs']:.3f} ; alma bef/b={r['Qa']:.3f} ; "
              f"Aef/Ag={r['Q']:.3f}",
              f"  Compressao: Ne={r['Ne']:.0f} kN ; lambda0={r['lambda0']:.3f} ; "
              f"chi={r['chi']:.3f} ; Nc,Rd={r['Nc_Rd']:.1f} kN",
              flexao,
              f"    Mn_FLT={r['Mn_flt']:.1f} ; Mn_FLM={r['Mn_flm']:.1f} ; Mn_FLA={r['Mn_fla']:.1f} "
              f"-> governa {r['M_gov']} ; Mrd={r['Mrd']:.1f} kN.m",
              f"  Cortante: Vrd={r['Vrd']:.1f} kN (alma compacta: {r['alma_compacta_cisalhamento']})",
              f"  Utilizacao: N/Nc={r['u_N']:.2f} ; M/Mrd={r['u_M']:.2f} ; V/Vrd={r['u_V']:.2f}",
              f"  Interacao ({r['eq_interacao']}) = {r['interacao']:.2f}  -> "
              f"{'OK' if r['OK'] else 'NAO PASSA'}"]
    import re
    # virgula decimal (PT) sem mastigar numeros de clausula pontilhada.
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


# ---- secoes (SI: m, m2, m4, m3). Inclui d, bf, tf, tw para Q, Cw, J ---------
HEA200 = {"A": 53.83e-4, "Ix": 3692e-8, "Iy": 1336e-8, "ry": 0.0498,
          "Zx": 429.5e-6, "Wx": 388.6e-6, "d": 0.190, "bf": 0.200,
          "tf": 0.010, "tw": 0.0065}
HEA180 = {"A": 45.25e-4, "Ix": 2510e-8, "Iy": 924.6e-8, "ry": 0.0452,
          "Zx": 324.9e-6, "Wx": 293.6e-6, "d": 0.171, "bf": 0.180,
          "tf": 0.0095, "tw": 0.006}


if __name__ == "__main__":
    # Esforcos AMPLIFICADOS de 2a ordem (estabilidade_b1b2, MAES + rigidez 0,8
    # + forca nocional). Com o MAES, usa-se K=1,0 (4.9.6.2): a flambagem por
    # translacao de nos ja esta coberta pelo B2. Verifica TODAS as combinacoes
    # e reporta a pior interacao por peca.
    import estabilidade_b1b2 as est
    fy = 250e3  # kN/m2 (aco MR250 / ASTM A36)
    a = est.analyse()
    # (perfil, comprimento real da barra, Lb travamento lateral) por peca
    pecas = {"coluna": (HEA200, est.SEC["coluna"]["L"], 2.0),
             "viga":   (HEA180, est.SEC["viga"]["L"], 1.67)}
    finais = []
    for g, (sec, Lreal, Lb) in pecas.items():
        cands = []
        for r in a["combos"]:
            d = r[g]
            cands.append(verifica(sec, fy, L=Lreal, Nsd=d["Nsd"], Msd=d["Msd"],
                                  Vsd=d["Vsd"], Kx=1.0, Ky=1.0, Lb=Lb,
                                  nome=f"{g.capitalize()} (K=1; gov {r['nome']})"))
        finais.append(max(cands, key=lambda x: x["interacao"]))
    print(relatorio_pt(finais, fy))
