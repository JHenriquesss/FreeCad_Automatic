# ============================================================================
# solda_perfil_chapa.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Solda de FILETE de um perfil I numa chapa (pilar na placa de base, viga na
# chapa de topo do joelho e da cumeeira), sob N, V e M no plano da alma.
#
# METODO: a solda transmite o que o elemento do perfil traz. As tensoes saem da
# secao do perfil em regime elastico (sigma = N/A + M.y/I na mesa e na ponta da
# alma; tau = V/(hw.tw) na alma); a forca por comprimento de cada elemento
# (tensao x espessura) e' dividida pelos dois cordoes, um de cada face. A
# resultante vetorial por comprimento de cordao e' comparada com a resistencia
# do filete. A secao e' a de chapas retas (sem o raio de concordancia), o que
# da' tensao um pouco maior que a real.
#
# NORMA (ABNT NBR 8800:2024/Er1:2025, lida no MCP_Fontes em 2026-10-13):
#   Tabela 9, linha "Filete": a solicitacao e' a RESULTANTE VETORIAL das forcas
#     na junta; metal da solda 0,6.Aw.fw/gw2; metal-base deve atender a 6.5
#     (aqui: escoamento e ruptura do elemento do perfil junto ao cordao).
#     Nota i: gw2 = 1,35 (combinacoes normais).
#   6.2.2.2 a) e b): area efetiva = comprimento x garganta (0,707 da perna).
#   6.2.5.2 (acrescimo pela direcao da forca): NAO usado, a favor da seguranca.
#   Tabela 11: perna minima pela parte MENOS espessa da junta.
#   Tabela A.4: fw = 485 MPa para eletrodo de classe 70.
#
# O QUE NAO FAZ: nao confere a chapa nem os parafusos (ligacoes.py,
# base_chumbador.py); nao conta com contato na compressao (a normal de
# compressao entra como se fosse tracao); nao cobre perfil que nao seja I.
# Unidades do motor: m, kN, kPa. A perna sai em mm.
# ============================================================================
"""Solda de filete de perfil I em chapa, pelas tensoes da secao do perfil."""

import math

import ligacoes as LG

FW_E70 = 485e3                       # kPa - Tabela A.4, classe 70
# pernas de filete oferecidas (mm); acima da ultima a junta pede penetracao
PERNAS_MM = (3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0)


def perna_minima(t_menor_mm):
    """Tabela 11: perna minima (mm) pela MENOR espessura do metal-base na junta."""
    return LG.solda_filete_minimo(t_menor_mm)


def secao(perfil):
    """Area, inercia e alma da secao I de chapas retas (m2, m4, m)."""
    d, bf, tw, tf = perfil["d"], perfil["bf"], perfil["tw"], perfil["tf"]
    hw = d - 2.0 * tf
    return {"A": 2.0 * bf * tf + hw * tw,
            "Ix": (bf * d ** 3 - (bf - tw) * hw ** 3) / 12.0, "hw": hw}


def verifica(perfil, perna_mm, N, V, M, fy, fu, fw=FW_E70):
    """Forca por comprimento de cordao (kN/m) contra a resistencia do filete.

    `u_base` e' a tensao no elemento do perfil junto a solda contra o escoamento
    ou a ruptura (6.5): nao depende da perna - se passar de 1, e' o perfil que
    nao resiste ao esforco, e nenhuma solda resolve."""
    s = secao(perfil)
    n, v, m = abs(N), abs(V), abs(M)
    metal, _aw = LG.fw_rd_filete(perna_mm / 1000.0, 1.0, fw)
    limite = min(fy / LG.GA1, fu / LG.GA2)
    pontos = []
    for nome, sigma, tau, t in (
            ("mesa", n / s["A"] + m * (perfil["d"] / 2.0) / s["Ix"], 0.0, perfil["tf"]),
            ("alma", n / s["A"] + m * (s["hw"] / 2.0) / s["Ix"], v / (s["hw"] * perfil["tw"]),
             perfil["tw"])):
        f_sd = math.hypot(sigma, tau) * t / 2.0
        u_metal = f_sd / metal
        u_base = math.hypot(sigma / limite, tau / (0.60 * limite))
        pontos.append({"onde": nome, "sigma": sigma, "tau": tau, "f_sd": f_sd, "f_rd": metal,
                       "u_metal": u_metal, "u_base": u_base, "u": max(u_metal, u_base),
                       "governa": "metal-base" if u_base > u_metal else "metal da solda"})
    pior = max(pontos, key=lambda p: p["u"])
    return {"perna_mm": perna_mm, "pontos": pontos, "u": pior["u"], "onde": pior["onde"],
            "governa": pior["governa"], "OK": pior["u"] <= 1.0}


def dimensiona(perfil, t_chapa_mm, N, V, M, fy, fu, fw=FW_E70, nome=""):
    """Menor perna da escada que atende, a partir da minima da Tabela 11.

    Se nenhuma atende, devolve OK=False: com o metal da solda governando, a
    junta pede solda de penetracao, que este modulo nao dimensiona."""
    t_menor = min(t_chapa_mm, perfil["tw"] * 1000.0)
    minima = perna_minima(t_menor)
    linhas, adotada = [], None
    for perna in PERNAS_MM:
        if perna < minima:
            continue
        r = verifica(perfil, perna, N, V, M, fy, fu, fw)
        linhas.append(r)
        if r["OK"]:
            adotada = r
            break
    r = adotada or linhas[-1]
    u_base = max(p["u_base"] for p in r["pontos"])
    if not r["OK"] and u_base > 1.0:
        # a tensao no perfil nao muda com a perna: o aviso e' do perfil, nao da solda
        r = dict(r, u=u_base, governa="metal-base")
    return {"nome": nome, "N": abs(N), "V": abs(V), "M": abs(M), "t_menor_mm": t_menor,
            "perna_minima_mm": minima, "perna_mm": r["perna_mm"], "u": r["u"],
            "onde": r["onde"], "governa": r["governa"], "OK": r["OK"], "tentativas": linhas}


def relatorio_pt(rs):
    L = ["SOLDA DE FILETE DO PERFIL NA CHAPA (NBR 8800:2024, Tabela 9 e Tabela 11)",
         "Tensoes da secao do perfil; resultante vetorial por comprimento de cordao.", ""]
    for r in rs:
        L.append("%s" % r["nome"])
        L.append("  N = %.1f kN   V = %.1f kN   M = %.1f kN.m" % (r["N"], r["V"], r["M"]))
        L.append("  menor espessura na junta %.1f mm -> perna minima %.0f mm"
                 % (r["t_menor_mm"], r["perna_minima_mm"]))
        for t in r["tentativas"]:
            for p in t["pontos"]:
                L.append("    perna %2.0f mm  %-4s  f_sd = %7.1f kN/m  solda %.2f  metal-base %.2f"
                         % (t["perna_mm"], p["onde"], p["f_sd"], p["u_metal"], p["u_base"]))
        if r["OK"]:
            situacao = "OK"
        elif r["governa"] == "metal-base":
            situacao = "*** NAO ATENDE: a tensao no perfil junto a chapa passa do limite ***"
        else:
            situacao = "*** NAO ATENDE: usar solda de penetracao ***"
        L.append("  ADOTADA: filete de %.0f mm em todo o contorno  (u = %.2f)  %s"
                 % (r["perna_mm"], r["u"], situacao))
        L.append("")
    return "\n".join(L).replace(".", ",")


def _selftest():
    # W 310 x 38,7 a mao: d 310, bf 165, tw 5,8, tf 9,7 (mm)
    p = {"d": 0.310, "bf": 0.165, "tw": 0.0058, "tf": 0.0097}
    s = secao(p)
    assert abs(s["hw"] - 0.2906) < 1e-9
    assert abs(s["A"] - (2 * 0.165 * 0.0097 + 0.2906 * 0.0058)) < 1e-12
    # so' cortante: tau = 100 / (0,2906 x 0,0058) kPa; cada cordao leva tau.tw/2
    r = verifica(p, 5.0, 0.0, 100.0, 0.0, 250e3, 400e3)
    assert abs(r["pontos"][1]["f_sd"] - 100.0 / (2 * 0.2906)) < 1e-6
    assert r["pontos"][0]["f_sd"] == 0.0
    # so' normal: os cordoes somados devolvem a forca (contorno = 2 por elemento)
    r = verifica(p, 5.0, 200.0, 0.0, 0.0, 250e3, 400e3)
    total = 2 * (2 * 0.165 * r["pontos"][0]["f_sd"]) + 2 * 0.2906 * r["pontos"][1]["f_sd"]
    assert abs(total - 200.0) < 1e-6
    # metal da solda de 5 mm: 0,6 x 485e3 x 0,707 x 0,005 / 1,35 = 762,0 kN/m
    metal, _ = LG.fw_rd_filete(0.005, 1.0, FW_E70)
    assert abs(metal - 762.0) < 0.1
    assert perna_minima(6.3) == 3.0 and perna_minima(6.35) == 5.0 and perna_minima(25.0) == 8.0
    d = dimensiona(p, 16.0, 0.0, 50.0, 60.0, 250e3, 400e3)
    assert d["OK"] and d["perna_mm"] >= d["perna_minima_mm"]
    # momento acima da resistencia do proprio perfil: nenhuma perna resolve
    assert not dimensiona(p, 16.0, 0.0, 50.0, 400.0, 250e3, 400e3)["OK"]
    print("solda_perfil_chapa: selftest OK")


if __name__ == "__main__":
    _selftest()
