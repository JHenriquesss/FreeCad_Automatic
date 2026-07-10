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
    r = t/sqrt(12) (raio de giração da chapa); lambda0 = (Kl/r)/pi*sqrt(fy/E)."""
    r = t / math.sqrt(12.0)
    if r <= 0:
        return {"Nc_Rd": 0.0, "u": float("inf"), "OK": False}
    lam = (Kl / r) / math.pi * math.sqrt(fy / E)
    chi = chi_compressao(lam)
    Ag = bw * t
    Nc_Rd = chi * Ag * fy / GA1
    return {"lambda0": lam, "chi": chi, "Ag": Ag, "Nc_Rd": Nc_Rd,
            "u": N / Nc_Rd if Nc_Rd else float("inf"), "OK": N <= Nc_Rd}


def verifica_gusset(caso):
    """Verifica um gusset de contraventamento. `caso` (SI, m/kN):
      N       - esforço da diagonal (kN, tração > 0)
      t       - espessura do gusset (m)
      w0      - largura do elemento ligado (m; 0 p/ barra redonda)
      Lc      - comprimento da ligação ao longo da força (m)
      fy, fu  - do aço do gusset (kN/m2)
      Lsolda  - comprimento total de solda gusset->estrutura (m)
      perna   - perna do filete (m); default = mínimo por Tab.9 (solda_filete_minimo)
      Kl      - comprimento de flambagem da faixa (m); default 0.6*Lc
      tracao_only - True p/ barra redonda pré-tensionada (dispensa compressão)
      # opcionais p/ ligação PARAFUSADA da barra ao gusset:
      n, db, s_furos, e_long, e_transv, Cts
    Retorna dict com util por estado, governante e o gusset adotado."""
    N = abs(caso["N"])
    t = caso["t"]
    fy, fu = caso["fy"], caso["fu"]
    w0 = caso.get("w0", 0.0)
    Lc = caso["Lc"]
    bw = largura_whitmore(w0, Lc, caso.get("ang_whitmore", 30.0))

    res = {"bw": bw, "t": t, "estados": {}}
    tr = _tracao_whitmore(N, bw, t, fy)
    res["estados"]["tracao_whitmore"] = tr

    if not caso.get("tracao_only", True):
        Kl = caso.get("Kl", 0.6 * Lc)
        res["estados"]["compressao_whitmore"] = _compressao_whitmore(N, bw, t, Kl, fy)

    # solda gusset -> estrutura (filete)
    if caso.get("Lsolda"):
        perna = caso.get("perna") or LG.solda_filete_minimo(t * 1000.0) / 1000.0
        sd = LG.solda({"perna": perna, "Lw": caso["Lsolda"], "fw": caso.get("fw", 485e3),
                       "t_base": t, "fy_base": fy, "fu_base": fu, "F": N})
        sd["perna"] = perna
        res["estados"]["solda"] = sd

    # rasgamento em bloco se a barra for PARAFUSADA ao gusset
    if caso.get("n") and caso.get("db"):
        bs = LG.block_shear_linha(caso["n"], caso["s_furos"], caso["e_long"],
                                  caso["e_transv"], caso["db"], t, fy, fu,
                                  caso.get("Cts", 1.0))
        bs["u"] = N / bs["Frd"] if bs["Frd"] else float("inf")
        bs["OK"] = N <= bs["Frd"]
        res["estados"]["block_shear"] = bs

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
    nomes = {"tracao_whitmore": "Tracao (Whitmore) 5.2.2",
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
    # compressao habilitada quando nao tracao_only
    r2 = verifica_gusset({"N": 50.0, "t": 0.012, "w0": 0.0, "Lc": 0.100,
                          "fy": 250e3, "fu": 400e3, "tracao_only": False})
    assert "compressao_whitmore" in r2["estados"]
    cw = r2["estados"]["compressao_whitmore"]
    assert 0.0 < cw["chi"] <= 1.0
    # block shear entra se parafusado; reusa ligacoes.block_shear_linha
    r3 = verifica_gusset({"N": 50.0, "t": 0.012, "w0": 0.0, "Lc": 0.100,
                          "fy": 250e3, "fu": 400e3, "n": 2, "db": 0.020,
                          "s_furos": 0.060, "e_long": 0.035, "e_transv": 0.035})
    bs = r3["estados"]["block_shear"]
    ref_bs = LG.block_shear_linha(2, 0.060, 0.035, 0.035, 0.020, 0.012, 250e3, 400e3)
    assert abs(bs["Frd"] - ref_bs["Frd"]) < 1e-9
    # gusset fino demais reprova a tracao
    r4 = verifica_gusset({"N": 5000.0, "t": 0.003, "w0": 0.0, "Lc": 0.050,
                          "fy": 250e3, "fu": 400e3})
    assert not r4["OK"]
    print("gusset_ligacao _selftest PASSED")


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(verifica_gusset({"N": 50.0, "t": 0.012, "w0": 0.0,
                                        "Lc": 0.100, "fy": 250e3, "fu": 400e3,
                                        "Lsolda": 0.30})))
