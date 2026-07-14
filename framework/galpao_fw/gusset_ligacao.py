# ============================================================================
# gusset_ligacao.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica a CHAPA DE GUSSET dos contraventamentos (nós onde as barras
# diagonais tracionadas se ligam ao pórtico/coluna). NÃO reinventa fórmula:
# COMPÕE os primitivos já homologados de `ligacoes.py` (block shear 6.5.6,
# solda de filete 6.2.5, esmagamento/espaçamento 6.3) + a compressão
# 5.3.3 de `check_nbr8800.chi_compressao`. Estados-limite (ABNT NBR 8800:2008):
#   - Tração na LARGURA EFETIVA DE WHITMORE (escoamento 5.2.2 Nt,Rd=Ag*fy/ga1;
#     ruptura 5.2.3 na seção líquida se parafusada). Whitmore = espalhamento de
#     30° a partir da 1ª fixação (CONVENÇÃO AISC/Thornton — não é item da NBR;
#     documentada como premissa, análogo ao T-stub EN 1993 já aceito no joelho).
#   - Flambagem por compressão da faixa de Whitmore (5.3): só governa se a barra
#     puder comprimir; contraventamento de barra redonda pré-tensionada é
#     TRAÇÃO-ONLY -> incluída flagada para completude.
#   - Solda de filete gusset->estrutura (reusa `ligacoes.solda`; perna mínima
#     `solda_filete_minimo`).
#   - Rasgamento em bloco 6.5.6 (reusa `ligacoes.block_shear_linha`) quando a
#     ligação da barra ao gusset for PARAFUSADA.
# FLAGs: ângulo de Whitmore (30°), comprimento de flambagem (Kl), percurso do
# bloco de falha - o engenheiro responsável confirma p/ arranjos fora do padrão.
# Saídas em português. Unidades SI: m, kN.
# ============================================================================
"""Verificação da chapa de gusset de contraventamento (compõe ligacoes.py)."""

from __future__ import annotations

import math

import ligacoes as LG
from check_nbr8800 import chi_compressao, E, GA1

GA2 = LG.GA2                       # 1,35 (ruptura)
K_DUAS_BORDAS = 0.65              # gusset apoiado em 2 bordas (no de canto) - AISC DG29
K_UMA_BORDA = 1.2                 # gusset em bandeira (1 borda) - AISC DG29


def largura_whitmore(w0, Lc, ang_graus=30.0):
    """Largura efetiva de Whitmore (m): bw = w0 + 2*Lc*tan(ang).
    w0 = largura do elemento ligado (0 p/ barra redonda); Lc = comprimento da
    ligação ao longo da força. CONVENÇÃO AISC (30°) - FLAG, não é item NBR."""
    return w0 + 2.0 * Lc * math.tan(math.radians(ang_graus))


def _tracao_whitmore(N, bw, t, fy):
    """Escoamento à tração na seção de Whitmore (NBR 8800 5.2.2)."""
    Ag = bw * t
    Nt_Rd = Ag * fy / GA1
    return {"Ag": Ag, "Nt_Rd": Nt_Rd, "u": N / Nt_Rd if Nt_Rd else float("inf"),
            "OK": N <= Nt_Rd}


def _compressao_whitmore(N, bw, t, Kl, fy):
    """Flambagem da faixa de Whitmore como coluna curta (NBR 8800 5.3.3).
    r = t/sqrt(12) (raio de giração da chapa); lambda0 = (Kl/r)/pi*sqrt(fy/E).
    Kl = K * L_livre (metodo Thornton/AISC): L_livre = distancia LIVRE da ultima
    fixacao ate a face do apoio, NAO o comprimento da ligacao Lc."""
    r = t / math.sqrt(12.0)
    if r <= 0:
        return {"Nc_Rd": 0.0, "u": float("inf"), "OK": False}
    lam = (Kl / r) / math.pi * math.sqrt(fy / E)
    chi = chi_compressao(lam)
    Ag = bw * t
    Nc_Rd = chi * Ag * fy / GA1
    return {"lambda0": lam, "chi": chi, "Ag": Ag, "Nc_Rd": Nc_Rd, "Kl": Kl,
            "u": N / Nc_Rd if Nc_Rd else float("inf"), "OK": N <= Nc_Rd}


def _ruptura_whitmore(N, bw, t, fu, n_furos_transv, db, Ct):
    """Ruptura da secao liquida na faixa de Whitmore (NBR 8800 5.2.2b/5.2.3).
    So quando a barra e PARAFUSADA ao gusset. An = (bw - n_furos_transv*dh)*t;
    Ae = Ct*An; Nt,Rd = Ae*fu/GA2. dh = furo-padrao (Tabela 12, reusa ligacoes)."""
    dh = LG._diam_furo(db)
    An = max(bw - n_furos_transv * dh, 0.0) * t
    Ae = Ct * An
    Nt_Rd = Ae * fu / GA2
    return {"dh": dh, "An": An, "Ae": Ae, "Nt_Rd": Nt_Rd,
            "u": N / Nt_Rd if Nt_Rd else float("inf"), "OK": N <= Nt_Rd}


def verifica_gusset(caso):
    """Verifica um gusset de contraventamento. `caso` (SI, m/kN):
      N       - esforço da diagonal (kN, tração > 0)
      t       - espessura do gusset (m)
      w0      - largura do elemento ligado (m; 0 p/ barra redonda)
      Lc      - comprimento da LIGAÇÃO ao longo da força (m; define o espraiamento 30°)
      fy, fu  - do aço do gusset (kN/m2)
      d_barra - diâmetro da barra redonda ranhurada/soldada (m); vira w0 se w0 omitido
      w0      - largura inicial de distribuição (m); default d_barra (0 só se plano)
      Lsolda  - comprimento total de solda gusset->estrutura (m)
      perna   - perna do filete (m); default = mínimo por Tab.9 (solda_filete_minimo)
      L_livre - distância LIVRE da última fixação à face de apoio (m; flambagem);
                default = Lc (conservador; NÃO é o Lc por definição - Thornton)
      K       - fator de flambagem; default 0.65 (2 bordas). 1.2 se em bandeira.
      tracao_only - True p/ barra redonda pré-tensionada (dispensa compressão)
      # opcionais p/ ligação PARAFUSADA da barra ao gusset:
      n, db, s_furos, e_long, e_transv, Cts, n_furos_transv (ruptura líquida)
    Retorna dict com util por estado, governante e o gusset adotado."""
    N = abs(caso["N"])
    t = caso["t"]
    fy, fu = caso["fy"], caso["fu"]
    # barra redonda ranhurada/soldada -> largura inicial = diametro (nao 0):
    # transfere carga em 2 soldas laterais, nao num ponto (evita singularidade).
    w0 = caso.get("w0")
    if w0 is None:
        w0 = caso.get("d_barra", 0.0)
    Lc = caso["Lc"]
    bw = largura_whitmore(w0, Lc, caso.get("ang_whitmore", 30.0))

    res = {"bw": bw, "t": t, "w0": w0, "estados": {}}
    tr = _tracao_whitmore(N, bw, t, fy)
    res["estados"]["tracao_whitmore"] = tr

    if not caso.get("tracao_only", True):
        K = caso.get("K", K_DUAS_BORDAS)
        L_livre = caso.get("L_livre", Lc)
        Kl = caso.get("Kl", K * L_livre)
        res["estados"]["compressao_whitmore"] = _compressao_whitmore(N, bw, t, Kl, fy)

    # solda gusset -> estrutura (filete)
    if caso.get("Lsolda"):
        perna = caso.get("perna") or LG.solda_filete_minimo(t * 1000.0) / 1000.0
        sd = LG.solda({"perna": perna, "Lw": caso["Lsolda"], "fw": caso.get("fw", 485e3),
                       "t_base": t, "fy_base": fy, "fu_base": fu, "F": N})
        sd["perna"] = perna
        res["estados"]["solda"] = sd

    # rasgamento em bloco + ruptura da secao liquida se a barra for PARAFUSADA
    if caso.get("n") and caso.get("db"):
        bs = LG.block_shear_linha(caso["n"], caso["s_furos"], caso["e_long"],
                                  caso["e_transv"], caso["db"], t, fy, fu,
                                  caso.get("Cts", 1.0))
        bs["u"] = N / bs["Frd"] if bs["Frd"] else float("inf")
        bs["OK"] = N <= bs["Frd"]
        res["estados"]["block_shear"] = bs
        # ruptura da secao liquida na largura de Whitmore (5.2.2b/5.2.3)
        res["estados"]["ruptura_whitmore"] = _ruptura_whitmore(
            N, bw, t, fu, caso.get("n_furos_transv", 1), caso["db"],
            caso.get("Cts", 1.0))

    us = {k: v["u"] for k, v in res["estados"].items() if "u" in v}
    res["u_max"] = max(us.values()) if us else float("inf")
    res["governa"] = max(us, key=us.get) if us else None
    res["OK"] = all(v.get("OK", True) for v in res["estados"].values())
    res["adotado"] = {"t_mm": round(t * 1000.0, 1), "bw_mm": round(bw * 1000.0, 1)}
    return res


def relatorio_pt(res, titulo="GUSSET DE CONTRAVENTAMENTO"):
    def _pt(x):
        return ("%.2f" % x).replace(".", ",")
    L = ["=" * 74, "%s - CONCEITUAL, PENDENTE REVISAO E ART DO ENG." % titulo,
         "NBR 8800 (estados-limite) + largura de Whitmore (AISC, FLAG 30 graus)",
         "=" * 74, "",
         "Gusset: t = %s mm ; largura de Whitmore bw = %s mm"
         % (_pt(res["t"] * 1000.0), _pt(res["bw"] * 1000.0)), ""]
    nomes = {"tracao_whitmore": "Tracao escoam. (Whitmore) 5.2.2",
             "ruptura_whitmore": "Tracao ruptura liq. (Whitmore) 5.2.3",
             "compressao_whitmore": "Compressao (faixa Whitmore) 5.3.3",
             "solda": "Solda de filete 6.2.5", "block_shear": "Rasgamento bloco 6.5.6"}
    for k, v in res["estados"].items():
        rd = v.get("Nt_Rd") or v.get("Nc_Rd") or v.get("Fw_Rd") or v.get("Frd")
        L.append("  %-34s Rd = %8s kN   util = %s %s"
                 % (nomes.get(k, k), _pt(rd), _pt(v["u"]),
                    "OK" if v.get("OK") else "*** NAO ATENDE ***"))
    L += ["", "Governa: %s (util = %s)" % (res["governa"], _pt(res["u_max"])),
          "RESULTADO: %s" % ("ATENDE" if res["OK"] else "NAO ATENDE"), ""]
    return "\n".join(L)


def _selftest():
    # Whitmore: w0=0, Lc=100mm, 30deg -> bw = 2*0,1*tan30 = 0,11547 m
    bw = largura_whitmore(0.0, 0.100, 30.0)
    assert abs(bw - 2 * 0.100 * math.tan(math.radians(30.0))) < 1e-9
    # tracao 5.2.2: Nt_Rd = bw*t*fy/ga1
    tr = _tracao_whitmore(50.0, bw, 0.012, 250e3)
    assert abs(tr["Nt_Rd"] - bw * 0.012 * 250e3 / GA1) < 1e-6
    # gusset tracao-only com barra Ø20: esforço pequeno passa
    r = verifica_gusset({"N": 50.0, "t": 0.012, "w0": 0.0, "Lc": 0.100,
                         "fy": 250e3, "fu": 400e3, "Lsolda": 0.30})
    assert "tracao_whitmore" in r["estados"] and "solda" in r["estados"]
    assert "compressao_whitmore" not in r["estados"]      # tracao_only default
    assert r["OK"], r
    # solda: reusa ligacoes.solda -> mesmo Fw_Rd
    sd = r["estados"]["solda"]
    perna = LG.solda_filete_minimo(12.0) / 1000.0         # t=12mm -> 5mm
    assert abs(sd["perna"] - perna) < 1e-9
    ref = LG.solda({"perna": perna, "Lw": 0.30, "fw": 485e3, "t_base": 0.012,
                    "fy_base": 250e3, "fu_base": 400e3, "F": 50.0})
    assert abs(sd["Fw_Rd"] - ref["Fw_Rd"]) < 1e-9
    # d_barra vira w0 quando w0 omitido (barra redonda ranhurada, nao ponto)
    rb = verifica_gusset({"N": 50.0, "t": 0.012, "d_barra": 0.020, "Lc": 0.100,
                          "fy": 250e3, "fu": 400e3})
    assert abs(rb["w0"] - 0.020) < 1e-9
    assert abs(rb["bw"] - largura_whitmore(0.020, 0.100)) < 1e-9
    # compressao habilitada quando nao tracao_only; K default = 0.65 (2 bordas)
    r2 = verifica_gusset({"N": 50.0, "t": 0.012, "w0": 0.0, "Lc": 0.100,
                          "fy": 250e3, "fu": 400e3, "tracao_only": False})
    assert "compressao_whitmore" in r2["estados"]
    cw = r2["estados"]["compressao_whitmore"]
    assert 0.0 < cw["chi"] <= 1.0
    assert abs(cw["Kl"] - K_DUAS_BORDAS * 0.100) < 1e-9   # Kl = K*L_livre, L_livre=Lc
    # L_livre desacoplado de Lc: distancia livre maior -> Kl maior -> chi menor
    r2b = verifica_gusset({"N": 50.0, "t": 0.012, "w0": 0.0, "Lc": 0.100,
                           "fy": 250e3, "fu": 400e3, "tracao_only": False,
                           "L_livre": 0.300})
    assert r2b["estados"]["compressao_whitmore"]["chi"] < cw["chi"]
    # block shear + ruptura liquida entram se parafusado
    r3 = verifica_gusset({"N": 50.0, "t": 0.012, "w0": 0.0, "Lc": 0.100,
                          "fy": 250e3, "fu": 400e3, "n": 2, "db": 0.020,
                          "s_furos": 0.060, "e_long": 0.035, "e_transv": 0.035})
    bs = r3["estados"]["block_shear"]
    ref_bs = LG.block_shear_linha(2, 0.060, 0.035, 0.035, 0.020, 0.012, 250e3, 400e3)
    assert abs(bs["Frd"] - ref_bs["Frd"]) < 1e-9
    # ruptura liquida: An = (bw - n_furos_transv*dh)*t ; Nt_Rd = Ae*fu/GA2
    rup = r3["estados"]["ruptura_whitmore"]
    dh = LG._diam_furo(0.020)
    An_ref = (r3["bw"] - 1 * dh) * 0.012
    assert abs(rup["An"] - An_ref) < 1e-12
    assert abs(rup["Nt_Rd"] - An_ref * 400e3 / GA2) < 1e-6   # Ct=1
    # gusset fino demais reprova a tracao
    r4 = verifica_gusset({"N": 5000.0, "t": 0.003, "w0": 0.0, "Lc": 0.050,
                          "fy": 250e3, "fu": 400e3})
    assert not r4["OK"]
    print("gusset_ligacao _selftest PASSED")


if __name__ == "__main__":
    _selftest()
    print()
    # caso REAL: barra redonda Ø20 soldada -> w0 = d_barra = 20 mm (nao ponto)
    print(relatorio_pt(verifica_gusset({"N": 50.0, "t": 0.012, "d_barra": 0.020,
                                        "Lc": 0.100, "fy": 250e3, "fu": 400e3,
                                        "Lsolda": 0.30})))
