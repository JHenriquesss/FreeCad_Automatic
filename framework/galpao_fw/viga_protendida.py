# ============================================================================
# viga_protendida.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica/dimensiona uma VIGA DE COBERTURA PRE-TRACIONADA (concreto protendido,
# ABNT NBR 6118:2014) - a solucao para os vaos que a viga de concreto armado nao
# vence (> ~12 m). Cobre o que a NBR exige para pre-tracao com aderencia:
#   1) ATO DA PROTENSAO (17.2.4.3.2): com gamma_p=1,1 e so o peso proprio, a tensao
#      de compressao <= 0,7*fckj e a de tracao <= 1,2*fctm,j (estadio I);
#   2) SERVICO por nivel de protensao (Tab.13.4): pre-tracao CAA II = nivel 2
#      (LIMITADA) -> ELS-F (formacao de fissuras, comb. frequente: tracao <= fct,f)
#      e ELS-D (descompressao, comb. quase-permanente: sem tracao);
#   3) ELU a FLEXAO: Mrd (cordoalha a fpyd + bloco de concreto) >= Md.
# Cordoalha CP-190 RB (NBR 7483): fptk=1900 MPa, fpyk=0,9 fptk, Ep=200 GPa; areas
# Ø12,7=1,01 cm2, Ø15,2=1,40 cm2. Tensao de estiramento (9.6.1.2.1, pre-tracao):
# sigma_pi <= min(0,77 fptk ; 0,90 fpyk). PERDAS por 9.6.3 (processo aproximado
# permitido, 9.6.3.4.3) - estimadas por um fator, marcado A CONFIRMAR.
# Convencao de tensao: COMPRESSAO NEGATIVA. A aritmetica de tensoes de borda foi
# aferida contra o exemplo resolvido de Bastos ("Fundamentos do Concreto Protendido",
# Cap.1, laje 30x30) - NAO de memoria. Unidades: m, kN ; fck em kN/m2.
# ============================================================================
"""Viga de cobertura pre-tracionada (NBR 6118:2014): ato da protensao, ELS-F/ELS-D
por nivel (Tab.13.4) e ELU a flexao. Cordoalha CP-190 RB. Aferido contra Bastos."""

from __future__ import annotations

import math

# --- aco de protensao CP-190 RB (NBR 7483) ---------------------------------
FPTK_CP190 = 1900e3                # resistencia a tracao (kN/m2) = 1900 MPa
FPYK_CP190 = 0.9 * FPTK_CP190      # escoamento convencional (RB): 0,9 fptk
EP_ACO = 200e6                     # modulo de elasticidade (kN/m2) = 200 GPa
AP_CORDOALHA = {12.7: 1.01e-4, 15.2: 1.40e-4}   # area nominal (m2), NBR 7483
GAMMA_S = 1.15
GAMMA_P_ATO = 1.1                  # ponderacao da protensao no ato (17.2.4.3.2)

# tensao maxima de estiramento na pre-tracao (9.6.1.2.1): min(0,77 fptk ; 0,90 fpyk)
SIGMA_PI_MAX = min(0.77 * FPTK_CP190, 0.90 * FPYK_CP190)

# fatores de combinacao (NBR 8681) para a cobertura
PSI1_SOBRECARGA = 0.5              # frequente (sobrecarga de cobertura)
PSI2_SOBRECARGA = 0.3             # quase-permanente


def props_retangular(b, h):
    """Propriedades geometricas da secao retangular. Retorna dict (m, m2, m4)."""
    Ac = b * h
    I = b * h ** 3 / 12.0
    yt = yb = h / 2.0
    return {"Ac": Ac, "I": I, "yt": yt, "yb": yb, "Wt": I / yt, "Wb": I / yb}


def tensoes_borda(P, ep, M, b, h):
    """Tensoes normais nas bordas (COMPRESSAO NEGATIVA), estadio I:
        sigma_topo = -P/Ac + P*ep*yt/I - M*yt/I
        sigma_base = -P/Ac - P*ep*yb/I + M*yb/I
    P = forca de protensao (kN, >0) ; ep = excentricidade do cabo ABAIXO do CG (m,
    >0) ; M = momento de servico (kN.m, sagging>0 -> tracao na base). Convencao
    aferida contra Bastos (laje 30x30: axial P=1125, ep=0, M=56,26 -> base=0)."""
    s = props_retangular(b, h)
    Ac, I, yt, yb = s["Ac"], s["I"], s["yt"], s["yb"]
    s_topo = -P / Ac + P * ep * yt / I - M * yt / I
    s_base = -P / Ac - P * ep * yb / I + M * yb / I
    return s_topo, s_base


def _fctm(fck):
    """fctm (kN/m2) = 0,3*fck^(2/3) [fck<=50]."""
    fck_MPa = fck / 1000.0
    return 0.3 * fck_MPa ** (2.0 / 3.0) * 1000.0


def verifica_ato(P0, ep, Mg, b, h, fckj):
    """ATO DA PROTENSAO (17.2.4.3.2): esforcos com gamma_p=1,1 e peso proprio
    (gamma_f=1,0). Compressao <= 0,7 fckj ; tracao <= 1,2 fctm,j. Verifica as duas
    bordas (o topo pode tracionar na regiao de M pequeno). Retorna dict."""
    st, sb = tensoes_borda(GAMMA_P_ATO * P0, ep, Mg, b, h)
    lim_comp = -0.70 * fckj                       # negativo (compressao)
    lim_trac = 1.20 * _fctm(fckj)                 # positivo (tracao)
    comp_ok = min(st, sb) >= lim_comp - 1e-6      # compressao nao passa do limite
    trac_ok = max(st, sb) <= lim_trac + 1e-6
    return {"s_topo": st, "s_base": sb, "lim_comp": lim_comp, "lim_trac": lim_trac,
            "comp_ok": comp_ok, "trac_ok": trac_ok, "ok": comp_ok and trac_ok}


def verifica_servico(Pinf, ep, Mg, Mq, b, h, fck, nivel=2):
    """SERVICO por nivel de protensao (Tab.13.4). Nivel 2 (LIMITADA, pre-tracao CAA
    II): ELS-F (comb. FREQUENTE, tracao <= fct,f) + ELS-D (comb. QUASE-PERMANENTE,
    sem tracao). fct,f = 1,5*fctm (modulo de ruptura, secao retangular). Retorna dict."""
    fctf = 1.5 * _fctm(fck)                        # limite de formacao de fissuras
    # combinacao FREQUENTE: g + psi1*q
    M_freq = Mg + PSI1_SOBRECARGA * Mq
    stf, sbf = tensoes_borda(Pinf, ep, M_freq, b, h)
    els_f_ok = max(stf, sbf) <= fctf + 1e-6        # nao forma fissura
    # combinacao QUASE-PERMANENTE: g + psi2*q
    M_qp = Mg + PSI2_SOBRECARGA * Mq
    stq, sbq = tensoes_borda(Pinf, ep, M_qp, b, h)
    els_d_ok = max(stq, sbq) <= 1e-6               # descompressao: sem tracao
    return {"fct_f": fctf, "M_freq": M_freq, "s_base_freq": sbf, "els_f_ok": els_f_ok,
            "M_qp": M_qp, "s_base_qp": sbq, "els_d_ok": els_d_ok,
            "ok": els_f_ok and els_d_ok}


def verifica_elu_flexao(Ap, dp, Mg, Mq, b, h, fck, gamma_f=1.4):
    """ELU a flexao (simplificado): a cordoalha atinge fpyd e equilibra o bloco de
    concreto 0,8x/0,85fcd. Mrd = Ap*fpyd*(dp - 0,4x). Md = gamma_f*(Mg+Mq)."""
    fcd = fck / 1.4
    fpyd = FPYK_CP190 / GAMMA_S
    Rp = Ap * fpyd                                 # forca da cordoalha (kN)
    x = Rp / (0.85 * fcd * b * 0.8)                # 0,85fcd*b*0,8x = Rp
    z = dp - 0.4 * x
    Mrd = Rp * z
    Md = gamma_f * (Mg + Mq)
    return {"Mrd": Mrd, "Md": Md, "x": x, "z": z, "dp": dp,
            "u": Md / Mrd if Mrd > 0 else float("inf"), "ok": Md <= Mrd + 1e-6}


def verifica_viga_protendida(cfg):
    """Verifica uma viga de cobertura pre-tracionada retangular.
    cfg: {vao, b, h, fck [kN/m2], q [kN/m sobrecarga+perm exceto p.proprio],
          n_cordoalhas, phi_cord (12.7|15.2), cobrimento (m), fckj (default fck),
          perdas (fracao, default 0,20), nivel (default 2)}."""
    L = cfg["vao"]; b = cfg["b"]; h = cfg["h"]; fck = cfg["fck"]
    cob = cfg.get("cobrimento", 0.05)
    phi = cfg.get("phi_cord", 12.7)
    ncord = cfg["n_cordoalhas"]
    Ap = ncord * AP_CORDOALHA[phi]
    dp = h - cob                                   # cordoalha junto a face tracionada
    ep = dp - h / 2.0                              # excentricidade abaixo do CG
    fckj = cfg.get("fckj", fck)
    sigma_pi = SIGMA_PI_MAX                        # estiramento no limite (9.6.1.2.1)

    # cargas: peso proprio + sobrecarga/permanente adicional
    g = 25.0 * b * h                               # p.proprio (kN/m)
    Mg = g * L ** 2 / 8.0
    Mq = cfg.get("q", 0.0) * L ** 2 / 8.0

    # PERDAS (9.6.3): calculadas por procedencia (encurtamento elastico + processo
    # aproximado 9.6.3.4.3 RB). Se cfg["perdas"] for dado explicito, usa a estimativa.
    perdas_in = cfg.get("perdas")
    if perdas_in is None:
        import perdas_protensao_nbr6118 as pp
        pr = pp.perdas_pretracao(sigma_pi, Ap, ep, Mg, b, h, fckj,
                                 cfg.get("phi_fluencia", pp.PHI_FLUENCIA_PADRAO))
        perdas = pr["perda_total_frac"]
        sigma_p0 = sigma_pi * (1.0 - pr["perda_imediata_pct"] / 100.0)  # apos perda imediata
        perdas_info = pr
    else:
        perdas = perdas_in
        sigma_p0 = sigma_pi * (1.0 - 0.5 * perdas)   # aprox.: metade das perdas no ato
        perdas_info = {"perda_total_frac": perdas, "estimativa": True}
    P0 = Ap * sigma_p0                              # no ato (apos perda imediata)
    Pinf = Ap * sigma_pi * (1.0 - perdas)          # em servico (perdas totais)

    ato = verifica_ato(P0, ep, Mg, b, h, fckj)
    serv = verifica_servico(Pinf, ep, Mg, Mq, b, h, fck, cfg.get("nivel", 2))
    elu = verifica_elu_flexao(Ap, dp, Mg, Mq, b, h, fck)
    OK = ato["ok"] and serv["ok"] and elu["ok"]
    return {"vao": L, "b": b, "h": h, "n_cordoalhas": ncord, "phi_cord": phi,
            "Ap_cm2": round(Ap * 1e4, 2), "ep_cm": round(ep * 100, 1),
            "P0": round(P0, 1), "Pinf": round(Pinf, 1), "sigma_pi_MPa": round(sigma_pi / 1000, 0),
            "Mg": round(Mg, 1), "Mq": round(Mq, 1), "g": round(g, 2),
            "ato": ato, "servico": serv, "elu": elu, "perdas": perdas,
            "perdas_info": perdas_info, "OK": OK}


def dimensiona_viga_protendida(cfg, secoes=None, max_cord=24):
    """Adota a MENOR secao + numero de cordoalhas que atende (ato + servico + ELU).
    secoes: lista de (b,h). Retorna o 1o que passa (ou o ultimo tentado)."""
    secoes = secoes or [(0.20, 0.60), (0.25, 0.70), (0.30, 0.80), (0.30, 1.00),
                        (0.35, 1.10), (0.40, 1.20)]
    r = None
    for (b, h) in secoes:
        for n in range(2, max_cord + 1, 2):
            r = verifica_viga_protendida(dict(cfg, b=b, h=h, n_cordoalhas=n))
            if r["OK"]:
                return r
    return r


def relatorio_pt(r):
    a = r["ato"]; s = r["servico"]; e = r["elu"]
    L = ["VIGA DE COBERTURA PRE-TRACIONADA (ABNT NBR 6118:2014 ; CP-190 RB)",
         f"  Vao {r['vao']:.1f} m ; secao {r['b']*100:.0f}x{r['h']*100:.0f} cm ; "
         f"{r['n_cordoalhas']} cordoalhas Ø{r['phi_cord']} (Ap={r['Ap_cm2']:.2f} cm2, "
         f"ep={r['ep_cm']:.1f} cm)",
         f"  Protensao: sigma_pi={r['sigma_pi_MPa']:.0f} MPa ; P0={r['P0']:.0f} kN ; "
         f"Pinf={r['Pinf']:.0f} kN (perdas {r['perdas']*100:.0f}%"
         + (f": imediata {r['perdas_info']['perda_imediata_pct']:.1f}% + "
            f"progressiva {r['perdas_info']['prog_pct']:.1f}%, phi={r['perdas_info']['phi']:.1f}"
            if not r['perdas_info'].get('estimativa') else " estimativa") + ")",
         f"  ATO (17.2.4.3.2): topo {a['s_topo']/1000:.2f} , base {a['s_base']/1000:.2f} MPa ; "
         f"comp<={-a['lim_comp']/1000:.1f} {'OK' if a['comp_ok'] else 'REPROVA'} ; "
         f"trac<={a['lim_trac']/1000:.2f} {'OK' if a['trac_ok'] else 'REPROVA'}",
         f"  SERVICO nivel 2 (Tab.13.4): ELS-F base {s['s_base_freq']/1000:.2f} <= "
         f"{s['fct_f']/1000:.2f} MPa {'OK' if s['els_f_ok'] else 'REPROVA'} ; "
         f"ELS-D base {s['s_base_qp']/1000:.2f} <= 0 {'OK' if s['els_d_ok'] else 'REPROVA'}",
         f"  ELU flexao: Md={e['Md']:.0f} <= Mrd={e['Mrd']:.0f} kN.m (u={e['u']:.2f}) "
         f"{'OK' if e['ok'] else 'REPROVA'}",
         f"  RESULTADO: {'APROVADA' if r['OK'] else 'REPROVADA'}",
         "  [A CONFIRMAR: fckj na idade da protensao, perdas (9.6.3), classe de agressividade.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # Afericao da ARITMETICA DE TENSOES contra Bastos ("Fundamentos do Concreto
    # Protendido", Cap.1, laje b=30 h=30 cm ; Mg=Mq=2813 kN.cm=28,13 kN.m):
    b, h = 0.30, 0.30
    Mtot = 2.0 * 28.13                             # g+q (kN.m)
    # protensao AXIAL (ep=0) que anula a base: P=1125 kN -> base ~ 0
    st, sb = tensoes_borda(1125.0, 0.0, Mtot, b, h)
    assert abs(sb) < 5.0, sb / 1000.0             # base ~ 0 (kN/m2)
    # so a carga: base = +12,5 MPa (tracao), topo = -12,5 MPa
    st0, sb0 = tensoes_borda(0.0, 0.0, Mtot, b, h)
    assert abs(sb0 / 1000.0 - 12.5) < 0.1 and abs(st0 / 1000.0 + 12.5) < 0.1, (st0, sb0)
    # protensao no limite do nucleo (ep=h/6=0,05): topo da PROTENSAO ~ 0
    stp, sbp = tensoes_borda(562.5, 0.05, 0.0, b, h)
    assert abs(stp) < 5.0, stp                    # topo da protensao ~ 0 (nucleo central)
    assert abs(sbp / 1000.0 + 12.5) < 0.2, sbp    # base da protensao = -2P/Ac = -12,5 MPa
    # ep maximo (0,10): topo da protensao = +P/Ac (tracao). P=375 -> +4,17 MPa
    stm, sbm = tensoes_borda(375.0, 0.10, 0.0, b, h)
    assert abs(stm / 1000.0 - 4.17) < 0.1, stm / 1000.0
    # dimensionamento: um vao de 16 m (que o CA nao vence) fecha com protensao
    r = dimensiona_viga_protendida({"vao": 16.0, "fck": 40e3, "q": 5.0})
    assert r["OK"], relatorio_pt(r)
    print("viga_protendida self-test PASSED (tensoes aferidas vs Bastos ; vao 16 m OK)")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(dimensiona_viga_protendida({"vao": 16.0, "fck": 40e3, "q": 5.0})))
