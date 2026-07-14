# ============================================================================
# check_nbr8800.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica um perfil I/H laminado pela ABNT NBR 8800:2008 dados os esforcos
# solicitantes (Nsd, Msd, Vsd). Formulas extraidas da norma (Anexos F e G).
#   Compressao (5.3): flambagem global (chi, Tabela 4) + flambagem local
#     (fator Q = Qs*Qa, Anexo F / Tabela F.1) - NAO assume Q=1, calcula.
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

E = 200e6          # kN/m2 (200 GPa)
GA1 = 1.10


def chi_compressao(lambda0):
    """NBR 8800 5.3.3 / Tabela 4."""
    if lambda0 <= 1.5:
        return 0.658 ** (lambda0 ** 2)
    return 0.877 / lambda0 ** 2


def fator_Q(sec, fy):
    """Anexo F: Q = Qs (mesa, Grupo 4) * Qa (alma, Grupo 2)."""
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

    # Compressao (5.3): global + local (Q)
    Q, Qs, Qa, btf, btw = fator_Q(sec, fy)
    Ne = min(math.pi ** 2 * E * Ix / (Kx * L) ** 2,
             math.pi ** 2 * E * Iy / (Ky * Lb) ** 2)
    lambda0 = math.sqrt(Q * A * fy / Ne)
    chi = chi_compressao(lambda0)
    Nc_Rd = chi * Q * A * fy / GA1
    r.update(Q=Q, Qs=Qs, Qa=Qa, Ne=Ne, lambda0=lambda0, chi=chi, Nc_Rd=Nc_Rd)

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
    n, m = Nsd / Nc_Rd, Msd / Mrd
    if n >= 0.2:
        inter, eq = n + (8.0 / 9.0) * m, "N/Nrd + 8/9*(M/Mrd)"
    else:
        inter, eq = n / 2.0 + m, "N/(2Nrd) + M/Mrd"
    r.update(interacao=inter, eq_interacao=eq)
    r["OK"] = inter <= 1.0 and r["u_V"] <= 1.0
    return r


def relatorio_pt(rs, fy):
    L = ["VERIFICACAO DE PERFIS (ABNT NBR 8800:2008 - Anexos F e G)",
         f"  fy = {fy/1000:.0f} MPa ; gamma_a1 = {GA1:.2f}",
         "  ATENCAO: Nsd/Msd devem vir amplificados por B1/B2 (2a ordem)."]
    for r in rs:
        L += ["",
              f"  --- {r['nome']} ---",
              f"  Flambagem local: Qs={r['Qs']:.3f} ; Qa={r['Qa']:.3f} ; Q={r['Q']:.3f}",
              f"  Compressao: Ne={r['Ne']:.0f} kN ; lambda0={r['lambda0']:.3f} ; "
              f"chi={r['chi']:.3f} ; Nc,Rd={r['Nc_Rd']:.1f} kN",
              f"  Flexao: Mpl={r['Mpl']:.1f} ; Lp={r['Lp']:.2f} m ; Lr(FLT)={r['Lr_flt']:.2f} m ; "
              f"Cw={r['Cw']:.3e} ; J={r['J']:.3e}",
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
