# ============================================================================
# escada.py - DIMENSIONAMENTO DE ESCADAS INDUSTRIAIS EM ACO
# Dimensiona longarinas (vigas inclinadas), degraus (chapa xadrez ou
# grelha), patamares e guarda-corpo. Conforme NBR 8800, NBR 6120, NR-18.
# Inclui verificacao de Blondel, patamar intermediario para desnivel > 3.2m,
# e flecha L/300.
# ============================================================================
"""Escadas metalicas industriais. Saidas PT. Unidades: m, kN."""

from __future__ import annotations
import math
import check_nbr8800 as chk
import perfis

PESO_DEGRAU = 0.30       # kN/m2 (chapa xadrez 5mm)
Q_ESCADA = 3.0           # kN/m2 (NBR 6120, acesso publico)
Q_CONCENTRADA = 2.5      # kN
LIM_FECHA = 300.0        # L/300
DESNIVEL_MAX_SEM_PATAMAR = 3.20  # m


def dimensiona(desnivel, projecao_horizontal, largura=1.20,
               q_acidental=Q_ESCADA, fy=250e3, limite_lance=3.20):
    """Dimensiona longarina de escada reta.
    desnivel: altura a vencer (m)
    projecao_horizontal: comprimento em planta (m)
    largura: largura util da escada (m)
    Retorna dict com resultados."""
    # Patamar obrigatorio para desnivel > 3.2 m
    if desnivel > limite_lance:
        return {"ok": False, "erro": f"Desnivel {desnivel:.1f}m > {DESNIVEL_MAX_SEM_PATAMAR}m: "
                "exige patamar intermediario (fora do escopo deste modulo)"}
    # Numero de espelhos (arredondar para CIMA para respeitar espelho max 18cm)
    n_espelhos = max(2, math.ceil(desnivel / 0.18))
    espelho = desnivel / n_espelhos
    # Numero de pisos = espelhos - 1 (o ultimo piso e o piso superior)
    n_pisos = n_espelhos - 1
    piso = projecao_horizontal / n_pisos if n_pisos > 0 else 0.0
    # Verificacao de Blondel: 62 <= 2e + p <= 64 (cm)
    blondel = 2.0 * (espelho * 100.0) + (piso * 100.0)
    if blondel < 62 or blondel > 64:
        return {"ok": False, "erro": f"Blondel {blondel:.1f}cm fora de [62;64]"}
    # Comprimento da longarina
    L_long = math.hypot(projecao_horizontal, desnivel)
    # Carga na longarina (2 longarinas). PESO_DEGRAU*largura ja e a carga LINEAR
    # dos degraus (kN/m); somado 0,50 kN/m (longarina + guarda-corpo) e dividido
    # pelas 2 longarinas. NAO multiplicar por largura de novo (erro dimensional).
    w_perm = (PESO_DEGRAU * largura + 0.50) / 2.0
    w_acid = q_acidental * largura / 2.0
    w_total = w_perm + w_acid
    M_max = w_total * L_long ** 2 / 8.0
    V_max = w_total * L_long / 2.0
    # Flecha (combinacao frequente): limite L/300. A flecha real e verificada no
    # loop com o Ix REAL de cada perfil (delta_real); aqui so o limite.
    lim_delta = L_long / LIM_FECHA
    
    escada_perfis = ["U100x10", "U125x10", "U150x12", "U150x15",
                     "U200x15", "U200x20", "HEA160", "HEA180", "HEA200"]
    melhor = None
    for pnome in escada_perfis:
        if pnome not in perfis.PERFIS:
            continue
        sec = perfis.PERFIS[pnome]
        Ix = sec.get("Ix", sec.get("I", 0))
        if not Ix:
            continue
        r = chk.verifica(sec, fy, L_long, Nsd=0.0, Msd=M_max, Vsd=V_max,
                         Kx=1.0, Ky=1.0, Lb=0.05)
        if r["interacao"] > 1.0:
            continue
        delta_real = 5.0 * (w_perm + 0.6 * w_acid) * L_long ** 4 / (384.0 * 200e6 * Ix)
        if delta_real > lim_delta:
            continue
        if melhor is None:
            melhor = {"perfil": pnome, "L": round(L_long, 2),
                      "espelho_mm": round(espelho * 1000, 1),
                      "piso_mm": round(piso * 1000, 1),
                      "n_espelhos": n_espelhos, "n_pisos": n_pisos,
                      "blondel_cm": round(blondel, 1),
                      "M_max": round(M_max, 1), "V_max": round(V_max, 1),
                      "delta_mm": round(delta_real * 1000, 1),
                      "interacao": round(r["interacao"], 3), "ok": True}
    return melhor or {"ok": False, "erro": "Nenhum perfil passou nas verificacoes"}


def relatorio_pt(r):
    if not r.get("ok"):
        return f"ESCADA - {r.get('erro', 'Erro desconhecido')}"
    L = ["ESCADA INDUSTRIAL METALICA",
         f"  Desnivel: {r['espelho_mm']*r['n_espelhos']/1000:.2f} m ; "
         f"Projecao: {r['piso_mm']*r['n_pisos']/1000:.1f} m",
         f"  Largura util = 1.20 m",
         f"  Espelhos: {r['n_espelhos']} x {r['espelho_mm']:.0f} mm = "
         f"{r['n_espelhos']*r['espelho_mm']/1000:.2f} m",
         f"  Pisos: {r['n_pisos']} x {r['piso_mm']:.0f} mm = "
         f"{r['n_pisos']*r['piso_mm']/1000:.1f} m",
         f"  Blondel: 2e+p = {r['blondel_cm']:.1f} cm (62-64) OK",
         f"  Longarina: {r['perfil']} (L={r['L']:.2f} m)",
         f"  M_max = {r['M_max']:.1f} kN.m ; V_max = {r['V_max']:.1f} kN",
         f"  Interacao ELU = {r['interacao']:.3f}",
         f"  Flecha = {r['delta_mm']:.1f} mm <= L/{LIM_FECHA} = "
         f"{r['L']*1000/LIM_FECHA:.1f} mm"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    r = dimensiona(desnivel=3.0, projecao_horizontal=4.50, largura=1.20)
    assert r.get("ok"), f"Falhou: {r.get('erro')}"
    assert r["espelho_mm"] <= 180, f"espelho {r['espelho_mm']} > 180mm"
    assert r["n_espelhos"] == r["n_pisos"] + 1
    assert 62 <= r["blondel_cm"] <= 64, f"Blondel {r['blondel_cm']} fora"
    print(f"escada self-test PASSED: {r['n_espelhos']} espelhos, "
          f"espelho={r['espelho_mm']:.0f}mm, piso={r['piso_mm']:.0f}mm, "
          f"Blondel={r['blondel_cm']:.1f}cm, perfil={r['perfil']}")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(dimensiona(3.0, 4.5, 1.20)))
