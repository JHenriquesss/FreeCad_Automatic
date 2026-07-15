# ============================================================================
# plataforma.py - PLATAFORMAS E PASSARELAS INDUSTRIAIS EM ACO
# Dimensiona vigas secundarias (perfil I ou U), piso (grelha/chapa),
# guarda-corpo (NR-18) e verifica flecha L/350 e frequencia natural > 3 Hz.
# Reaproveita check_nbr8800 para verificacao de perfis.
# ============================================================================
"""Plataformas e passarelas. Saidas PT. Unidades: m, kN."""

from __future__ import annotations
import math
import check_nbr8800 as chk
import perfis

Q_UTILIZACAO = 3.0        # kN/m2 (carga acidental tipica)
Q_CONCENTRADA = 2.0       # kN (carga concentrada p/ verificacao local)
LIM_FLECHA = 350.0        # L/350 (combinacao frequente)
FREQ_MIN = 3.0            # Hz (frequencia natural minima)
PESO_ACO = 77.0           # kN/m3


def viga_secundaria(L, b_trib, q_perm, q_acidental=Q_UTILIZACAO,
                    fy=250e3, contida=True, perfil_tipo="I"):
    """Dimensiona viga secundaria de plataforma.
    L = vao (m), b_trib = largura tributaria (m).
    Retorna o perfil mais leve que passa."""
    w_perm = q_perm * b_trib
    w_acid = q_acidental * b_trib
    w_total = w_perm + w_acid
    M_max = w_total * L ** 2 / 8.0
    V_max = w_total * L / 2.0
    
    escada = ["HEA160", "HEA180", "HEA200", "HEA220", "HEA240",
              "IPE300", "IPE330", "IPE360", "IPE400", "IPE450",
              "IPE500", "IPE550", "HEB200", "HEB220", "HEB240",
              "HEB260", "HEB280", "HEB300"]
    Lb_para_flt = 0.05 if contida else L  # se contida, Lb~0 -> usa 0.05
    melhor = None
    for pnome in escada:
        if pnome not in perfis.PERFIS:
            continue
        sec = perfis.PERFIS[pnome]
        r = chk.verifica(sec, fy, L, Nsd=0.0, Msd=M_max, Vsd=V_max,
                         Kx=1.0, Ky=1.0, Lb=Lb_para_flt)
        if r["interacao"] > 1.0:
            continue
        # Flecha
        Ix = sec.get("Ix", sec.get("I", 0))
        delta = 5.0 * (w_perm + 0.6 * w_acid) * L ** 4 / (384.0 * 200e6 * Ix)
        if delta > L / LIM_FLECHA:
            continue
        # Frequencia natural
        w_total_serv = (w_perm + 0.2 * w_acid) * L
        try:
            freq = math.sqrt(980.665 * 200e6 * Ix / (w_total_serv * L ** 3)) / (2 * math.pi)
        except Exception:
            freq = 0
        # NBR 8800 Anexo L.1.2: "em nenhum caso a frequencia natural pode ser
        # inferior a 3 Hz" - sem isencao por vao. Vao curto ja tende a freq alta
        # (f ~ 1/L^1.5), mas o criterio e verificado SEMPRE (sem bypass L>4,0).
        if freq < FREQ_MIN:
            continue
        if melhor is None:
            melhor = {"perfil": pnome, "sec": sec, "L": L, "M_max": M_max,
                      "V_max": V_max, "delta_mm": round(delta * 1000, 1),
                      "interacao": round(r["interacao"], 3),
                      "freq_Hz": round(freq, 2), "ok": True}
    return melhor or {"ok": False, "L": L, "M_max": M_max}


def guarda_corpo(altura=1.20, carga_horizontal=0.9):
    """Dimensiona guarda-corpo (NR-18). Retorna esforcos no montante."""
    M_base = carga_horizontal * altura  # kN.m/m
    return {"altura_m": altura, "carga_kN_m": carga_horizontal,
            "M_base_kN_m_m": round(M_base, 2)}


def relatorio_pt(r):
    L = ["PLATAFORMA / PASSARELA INDUSTRIAL"]
    if r.get("ok"):
        L += [f"  Perfil adotado: {r['perfil']} (L={r['L']:.2f} m)",
              f"  M_max = {r['M_max']:.1f} kN.m ; V_max = {r['V_max']:.1f} kN",
              f"  Interacao ELU = {r['interacao']:.3f}",
              f"  Flecha (freq) = {r['delta_mm']:.1f} mm <= L/{LIM_FLECHA}",
              f"  Frequencia natural = {r['freq_Hz']:.2f} Hz (min {FREQ_MIN} Hz)"]
    else:
        L.append("  Nenhum perfil da escada passou.")
    L += ["  [A CONFIRMAR: carga de utilizacao (NBR 6120); carga de guarda-corpo",
          "   (NR-18); geometria da plataforma.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    r = viga_secundaria(L=6.0, b_trib=1.5, q_perm=2.0, q_acidental=3.0)
    assert r.get("ok"), "nenhum perfil passou"
    assert r["delta_mm"] < 6000 / 350.0
    print(f"plataforma self-test PASSED: {r['perfil']} delta={r['delta_mm']}mm freq={r['freq_Hz']}Hz")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(viga_secundaria(L=6.0, b_trib=1.5, q_perm=2.0, q_acidental=3.0)))
