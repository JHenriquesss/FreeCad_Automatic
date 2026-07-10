# ============================================================================
# console_ponte.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica a LIGACAO DO CONSOLE da ponte rolante a coluna (a chapa/solda que
# recebe a viga de rolamento excentrica). So existe quando ha ponte. Nao
# reinventa a resistencia da solda: reusa `ligacoes.fw_rd_filete` (metal da
# solda 6.2.5) e `ligacoes.solda_filete_minimo` (perna minima Tab.9); as cargas
# vem de `ponte_rolante` (reacao vertical do trilho + forca transversal).
# Metodo do GRUPO DE SOLDA = analise ELASTICA (vetorial) da linha de solda:
#   demanda por comprimento f = sqrt(f_v^2 + f_h^2 + f_b^2), com
#   f_v = Rv/L (cisalhamento vertical), f_h = Ht/L (transversal),
#   f_b = 6*M/L^2 (flexao, modulo da linha Sw=L^2/6), M = Rv*ecc.
# Este metodo elastico do grupo de solda e MECANICA/AISC (nao e item da NBR) -
# documentado como FLAG, analogo ao T-stub (EN 1993) ja aceito no joelho.
# Tambem verifica o cisalhamento da chapa (0,6*fy escoamento, 5.4). Saidas em
# portugues. Unidades SI: m, kN.
# ============================================================================
"""Verificacao da ligacao do console da ponte rolante (compoe ligacoes.py)."""

from __future__ import annotations

import math

import ligacoes as LG
from check_nbr8800 import GA1

GA2 = LG.GA2


def verifica_console(caso):
    """Verifica a ligacao console->coluna. `caso` (SI, m/kN):
      Rv     - reacao vertical no console (kN) = reacao maxima do trilho
      Ht     - forca horizontal transversal no console (kN)
      ecc    - excentricidade do trilho a face da coluna (m)
      t      - espessura da chapa do console (m)
      L      - comprimento da linha de solda console->coluna (m)
      fy, fu - aco da chapa (kN/m2)
      fw     - resistencia do metal da solda (kN/m2; E70XX ~ 485e3)
      perna  - perna do filete (m); default = minimo Tab.9
    Retorna dict com util da solda (grupo elastico) + cisalhamento da chapa."""
    Rv, Ht = abs(caso["Rv"]), abs(caso.get("Ht", 0.0))
    ecc, t, L = caso["ecc"], caso["t"], caso["L"]
    fy, fu = caso["fy"], caso["fu"]
    fw = caso.get("fw", 485e3)

    M = Rv * ecc
    # grupo de solda elastico (linha vertical de comprimento L, dois cordoes)
    f_v = Rv / L
    f_h = Ht / L
    f_b = 6.0 * M / (L ** 2)                     # Sw = L^2/6 (modulo da linha)
    f_dem = math.sqrt(f_v ** 2 + f_h ** 2 + f_b ** 2)
    # DIMENSIONA a perna do filete: menor perna-padrao (>= minimo Tab.9) cuja
    # capacidade por comprimento cubra a demanda do grupo (first-fit). Se nem
    # 12 mm bastar, adota 12 e sinaliza (requer solda de penetracao/redesenho).
    p_min = LG.solda_filete_minimo(t * 1000.0)
    pernas = [p for p in (6.0, 8.0, 10.0, 12.0) if p >= p_min] or [p_min]
    perna = caso.get("perna") and caso["perna"] * 1000.0
    if perna is None:
        perna = pernas[-1]
        for p in pernas:
            if LG.fw_rd_filete(p / 1000.0, 1.0, fw)[0] >= f_dem:
                perna = p
                break
    perna = perna / 1000.0
    f_cap = LG.fw_rd_filete(perna, 1.0, fw)[0]   # capacidade por comprimento (kN/m)
    u_solda = f_dem / f_cap if f_cap else float("inf")

    # cisalhamento da chapa do console (escoamento 5.4): V_Rd = 0,6*fy*Aw/ga1
    Aw = t * L
    V_pl_Rd = 0.6 * fy * Aw / GA1
    u_chapa = Rv / V_pl_Rd if V_pl_Rd else float("inf")

    res = {
        "M": M, "perna_mm": round(perna * 1000.0, 1), "L_mm": round(L * 1000.0, 1),
        "solda": {"f_dem": f_dem, "f_cap": f_cap, "u": u_solda, "OK": u_solda <= 1.0,
                  "f_v": f_v, "f_h": f_h, "f_b": f_b},
        "chapa_cisalhamento": {"V_Rd": V_pl_Rd, "u": u_chapa, "OK": u_chapa <= 1.0},
    }
    us = {"solda": u_solda, "chapa": u_chapa}
    res["u_max"] = max(us.values())
    res["governa"] = max(us, key=us.get)
    res["OK"] = res["solda"]["OK"] and res["chapa_cisalhamento"]["OK"]
    res["adotado"] = {"t_mm": round(t * 1000.0, 1), "perna_solda_mm": res["perna_mm"]}
    return res


def relatorio_pt(res, titulo="CONSOLE DA PONTE ROLANTE"):
    def _pt(x):
        return ("%.2f" % x).replace(".", ",")
    s, c = res["solda"], res["chapa_cisalhamento"]
    return "\n".join([
        "=" * 74, "%s - CONCEITUAL, PENDENTE REVISAO E ART DO ENG." % titulo,
        "Grupo de solda ELASTICO (mecanica/AISC, FLAG) + cisalhamento da chapa",
        "=" * 74, "",
        "Chapa t = %s mm ; solda perna %s mm x L %s mm ; M = Rv*ecc = %s kN.m"
        % (_pt(res["adotado"]["t_mm"]), _pt(res["perna_mm"]), _pt(res["L_mm"]),
           _pt(res["M"])), "",
        "  Solda (grupo elastico)   dem = %s kN/m  cap = %s kN/m  util = %s %s"
        % (_pt(s["f_dem"]), _pt(s["f_cap"]), _pt(s["u"]),
           "OK" if s["OK"] else "*** NAO ATENDE ***"),
        "  Chapa (cisalhamento 5.4) V_Rd = %s kN            util = %s %s"
        % (_pt(c["V_Rd"]), _pt(c["u"]), "OK" if c["OK"] else "*** NAO ATENDE ***"),
        "", "Governa: %s (util = %s)" % (res["governa"], _pt(res["u_max"])),
        "RESULTADO: %s" % ("ATENDE" if res["OK"] else "NAO ATENDE"), ""])


def _selftest():
    # caso bem-proporcionado (solda ao longo da mísula, L=0,45 m): grupo elastico
    # f_dem = sqrt((Rv/L)^2 + (Ht/L)^2 + (6*Rv*ecc/L^2)^2)
    r = verifica_console({"Rv": 120.0, "Ht": 12.0, "ecc": 0.15, "t": 0.016,
                          "L": 0.45, "fy": 250e3, "fu": 400e3})
    M = 120.0 * 0.15
    f_v, f_h, f_b = 120.0 / 0.45, 12.0 / 0.45, 6.0 * M / 0.45 ** 2
    assert abs(r["solda"]["f_dem"] - math.sqrt(f_v**2 + f_h**2 + f_b**2)) < 1e-6
    # DIMENSIONA: adota a menor perna-padrao (>= min Tab.9=6mm) cuja cap >= dem
    cand = [p for p in (6.0, 8.0, 10.0, 12.0)
            if LG.fw_rd_filete(p / 1000.0, 1.0, 485e3)[0] >= r["solda"]["f_dem"]]
    assert abs(r["perna_mm"] - cand[0]) < 1e-9, (r["perna_mm"], cand)
    assert abs(r["solda"]["f_cap"] - LG.fw_rd_filete(r["perna_mm"] / 1000.0, 1.0, 485e3)[0]) < 1e-6
    assert r["solda"]["OK"]                                   # cap>=dem por construcao
    # cisalhamento da chapa: V_Rd = 0,6*fy*t*L/ga1
    assert abs(r["chapa_cisalhamento"]["V_Rd"] - 0.6 * 250e3 * 0.016 * 0.45 / GA1) < 1e-6
    # console curto/fino sob carga enorme: nem 12mm basta -> adota 12 e NAO ATENDE
    r2 = verifica_console({"Rv": 3000.0, "Ht": 300.0, "ecc": 0.60, "t": 0.006,
                           "L": 0.12, "fy": 250e3, "fu": 400e3})
    assert r2["perna_mm"] == 12.0 and not r2["OK"]
    # sem excentricidade -> f_b = 0
    r3 = verifica_console({"Rv": 100.0, "Ht": 0.0, "ecc": 0.0, "t": 0.016,
                           "L": 0.45, "fy": 250e3, "fu": 400e3})
    assert abs(r3["solda"]["f_b"]) < 1e-12
    print("console_ponte _selftest PASSED")


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(verifica_console({"Rv": 120.0, "Ht": 12.0, "ecc": 0.30,
                                        "t": 0.016, "L": 0.24, "fy": 250e3,
                                        "fu": 400e3})))
