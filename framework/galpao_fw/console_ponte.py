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
# na raiz (M_Sd=Rv*ecc; W=t*L^2/6). Saidas em portugues. Unidades SI: m, kN.
# ============================================================================
"""Verificacao da ligacao do console da ponte rolante (compoe ligacoes.py)."""

from __future__ import annotations

import math

import ligacoes as LG
from check_nbr8800 import GA1

GA2 = LG.GA2


def verifica_console(caso):
    """Verifica a ligacao console->coluna. `caso` (SI, m/kN):
      Rv       - reacao vertical no console (kN) = reacao maxima do trilho
      Ht       - forca horizontal transversal no console (kN)
      ecc      - excentricidade do trilho a face da coluna (m)
      h_trilho - altura do topo do trilho acima do TOPO da solda (m; default 0);
                 braco de Ht ao centroide da solda = L/2 + h_trilho
      t        - espessura da chapa do console (m)
      L        - comprimento (vertical) de CADA cordao console->coluna (m)
      fy, fu   - aco da chapa (kN/m2)
      fw       - resistencia do metal da solda (kN/m2; E70XX ~ 485e3)
      perna    - perna do filete (m); default = minimo Tab.9
    Dois cordoes (A_w=2L, Sw=L^2/3). Retorna dict: solda (grupo elastico) +
    chapa em balanco (cisalhamento 5.4 E flexao na raiz)."""
    Rv, Ht = abs(caso["Rv"]), abs(caso.get("Ht", 0.0))
    ecc, t, L = caso["ecc"], caso["t"], caso["L"]
    h_trilho = caso.get("h_trilho", 0.0)
    fy, fu = caso["fy"], caso["fu"]
    fw = caso.get("fw", 485e3)

    M = Rv * ecc                                 # flexao no plano (Rv excentrico)
    Mz = Ht * (L / 2.0 + h_trilho)               # flexao por excentricidade de Ht
    # grupo de solda elastico, DOIS cordoes: A_w=2L, Sw=2*(L^2/6)=L^2/3
    f_v = Rv / (2.0 * L)                          # vertical direto (z, // cordao)
    f_h = Ht / (2.0 * L)                          # horizontal direto (x)
    f_bV = 3.0 * M / (L ** 2)                     # flexao Rv*ecc (x)
    f_bH = 3.0 * Mz / (L ** 2)                    # flexao Ht*braco (x)
    f_horiz = f_h + f_bV + f_bH                   # COLINEARES no eixo x -> soma
    f_dem = math.sqrt(f_v ** 2 + f_horiz ** 2)    # x ortogonal a z (f_v)
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

    # chapa do console como VIGA EM BALANCO (secao t x L na raiz, junto a coluna):
    # (a) cisalhamento (escoamento 5.4): V_Rd = 0,6*fy*Aw/ga1 ; Aw = t*L
    Aw = t * L
    V_pl_Rd = 0.6 * fy * Aw / GA1
    u_cis = (Rv / V_pl_Rd) if V_pl_Rd else float("inf")
    # (b) flexao na raiz (elastico, conservador): W = t*L^2/6 ; M_Rd = W*fy/ga1.
    #     M_Sd = Rv*ecc (mesma flexao que gera f_bV na solda). Z=t*L^2/4 disponivel
    #     mas fica flagado (flambagem local do bordo comprimido - ver FLAG).
    W = t * (L ** 2) / 6.0
    M_Rd = W * fy / GA1
    u_flex = (M / M_Rd) if M_Rd else float("inf")

    res = {
        "M": M, "Mz": Mz, "perna_mm": round(perna * 1000.0, 1),
        "L_mm": round(L * 1000.0, 1),
        "solda": {"f_dem": f_dem, "f_cap": f_cap, "u": u_solda, "OK": u_solda <= 1.0,
                  "f_v": f_v, "f_horiz": f_horiz, "f_h": f_h, "f_bV": f_bV,
                  "f_bH": f_bH},
        "chapa_cisalhamento": {"V_Rd": V_pl_Rd, "u": u_cis, "OK": u_cis <= 1.0},
        "chapa_flexao": {"M_Sd": M, "M_Rd": M_Rd, "W": W, "u": u_flex,
                         "OK": u_flex <= 1.0},
    }
    us = {"solda": u_solda, "chapa_cis": u_cis, "chapa_flex": u_flex}
    res["u_max"] = max(us.values())
    res["governa"] = max(us, key=us.get)
    res["OK"] = all(v["OK"] for v in (res["solda"], res["chapa_cisalhamento"],
                                      res["chapa_flexao"]))
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
        "Chapa t = %s mm ; solda perna %s mm x L %s mm (2 cordoes) ; M = Rv*ecc = %s kN.m"
        % (_pt(res["adotado"]["t_mm"]), _pt(res["perna_mm"]), _pt(res["L_mm"]),
           _pt(res["M"])), "",
        "  Solda (grupo elastico)   dem = %s kN/m  cap = %s kN/m  util = %s %s"
        % (_pt(s["f_dem"]), _pt(s["f_cap"]), _pt(s["u"]),
           "OK" if s["OK"] else "*** NAO ATENDE ***"),
        "    (f_v=%s ; f_horiz=f_h+f_bV+f_bH=%s kN/m)"
        % (_pt(s["f_v"]), _pt(s["f_horiz"])),
        "  Chapa cisalhamento 5.4   V_Rd = %s kN            util = %s %s"
        % (_pt(c["V_Rd"]), _pt(c["u"]), "OK" if c["OK"] else "*** NAO ATENDE ***"),
        "  Chapa flexao (balanco)   M_Rd = %s kN.m          util = %s %s"
        % (_pt(f["M_Rd"]), _pt(f["u"]), "OK" if f["OK"] else "*** NAO ATENDE ***"),
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
    f_v = Rv / (2 * L)
    f_horiz = Ht / (2 * L) + 3 * M / L**2 + 3 * Mz / L**2
    assert abs(r["solda"]["f_dem"] - math.sqrt(f_v**2 + f_horiz**2)) < 1e-6
    assert abs(r["solda"]["f_horiz"] - f_horiz) < 1e-9      # colineares somados
    # componentes horizontais NAO sao SRSS entre si (seria nao-conservador):
    srss3 = math.sqrt(f_v**2 + (Ht/(2*L))**2 + (3*M/L**2)**2 + (3*Mz/L**2)**2)
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
    W = 0.016 * L**2 / 6.0
    assert abs(r["chapa_flexao"]["M_Rd"] - W * 250e3 / GA1) < 1e-6
    assert abs(r["chapa_flexao"]["M_Sd"] - M) < 1e-9
    # console curto/fino sob carga enorme: nem 12mm basta -> adota 12 e NAO ATENDE
    r2 = verifica_console({"Rv": 3000.0, "Ht": 300.0, "ecc": 0.60, "t": 0.006,
                           "L": 0.12, "fy": 250e3, "fu": 400e3})
    assert r2["perna_mm"] == 12.0 and not r2["OK"]
    # sem excentricidade e sem Ht -> f_horiz = 0 (so cisalhamento vertical)
    r3 = verifica_console({"Rv": 100.0, "Ht": 0.0, "ecc": 0.0, "t": 0.016,
                           "L": 0.45, "fy": 250e3, "fu": 400e3})
    assert abs(r3["solda"]["f_horiz"]) < 1e-12
    print("console_ponte _selftest PASSED")


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(verifica_console({"Rv": 120.0, "Ht": 12.0, "ecc": 0.15,
                                        "t": 0.016, "L": 0.45, "fy": 250e3,
                                        "fu": 400e3})))
