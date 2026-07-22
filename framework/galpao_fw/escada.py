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


def _dimensiona_multi(desnivel, projecao_horizontal, largura, q_acidental, fy,
                      limite_lance, patamar_comp=None):
    """Escada de VARIOS LANCES com patamar(es) de descanso (desnivel > limite_lance).
    Divide o desnivel em N lances iguais (cada um <= limite_lance) separados por
    (N-1) patamares. Comprimento do patamar = largura do lance (pratica; NBR
    9050/9077 NAO consta na base de normas -> A CONFIRMAR, sobrescrivivel por
    patamar_comp). Cada lance e dimensionado pelo nucleo de lance unico (h<=3,2 m,
    sem recursao). O patamar consome parte da projecao em planta."""
    n_lances = max(2, math.ceil(desnivel / limite_lance))
    p_len = patamar_comp if patamar_comp else largura
    h_lance = desnivel / n_lances
    # Projecao do lance DERIVADA de Blondel (nao fatiada da entrada): dado o espelho
    # (<=18 cm), o piso segue de 2e + p = 63 cm (centro de [62;64]). Fatiar uma
    # projecao fixa quebraria o Blondel de cada lance.
    n_esp = max(2, math.ceil(h_lance / 0.18))
    espelho_cm = (h_lance / n_esp) * 100.0
    piso_cm = 63.0 - 2.0 * espelho_cm                 # Blondel alvo 63
    if not (24.0 <= piso_cm <= 32.0):                 # piso fora da faixa ergonomica
        return {"ok": False, "erro": f"Lance {h_lance:.2f}m: piso Blondel {piso_cm:.1f}cm "
                f"fora de [24;32] (revisar limite_lance/geometria)"}
    proj_lance = (n_esp - 1) * (piso_cm / 100.0)
    lance = dimensiona(h_lance, proj_lance, largura, q_acidental, fy, limite_lance)
    if not lance.get("ok"):
        return {"ok": False, "erro": f"Lance ({h_lance:.2f}m x {proj_lance:.2f}m): "
                f"{lance.get('erro')}"}
    # projecao TOTAL necessaria em planta = N lances + (N-1) patamares; a entrada
    # `projecao_horizontal` e o espaco DISPONIVEL (informa se cabe).
    proj_necessaria = n_lances * proj_lance + (n_lances - 1) * p_len
    L_total = n_lances * lance["L"] + (n_lances - 1) * p_len   # desenvolvimento total
    espaco_ok = (projecao_horizontal <= 0) or (proj_necessaria <= projecao_horizontal + 1e-9)
    return {
        "ok": True, "multi": True,
        "n_lances": n_lances, "n_patamares": n_lances - 1,
        "desnivel_total_m": round(desnivel, 3),
        "desnivel_por_lance_m": round(h_lance, 3),
        "projecao_necessaria_m": round(proj_necessaria, 3),
        "projecao_disponivel_m": round(projecao_horizontal, 3),
        "espaco_suficiente": bool(espaco_ok),
        "patamar_comprimento_m": round(p_len, 3), "patamar_largura_m": largura,
        "limite_lance_m": limite_lance,
        "perfil": lance["perfil"],              # mesmo perfil em todos (lances iguais)
        "L_desenvolvimento_m": round(L_total, 2),
        "lance": lance,
        "obs_patamar": "Comprimento do patamar = largura do lance (pratica de "
                       "engenharia; a dimensao exata NBR 9050/9077 NAO consta na "
                       "base de normas -> A CONFIRMAR). Patamar como plataforma: "
                       "vigas/piso pelo modulo de plataforma.",
    }


def dimensiona(desnivel, projecao_horizontal, largura=1.20,
               q_acidental=Q_ESCADA, fy=250e3, limite_lance=3.20):
    """Dimensiona longarina de escada reta.
    desnivel: altura a vencer (m)
    projecao_horizontal: comprimento em planta (m)
    largura: largura util da escada (m)
    limite_lance: desnivel maximo de um lance CONTINUO (m); acima disso a escada e
                  dividida em lances com PATAMAR intermediario (NBR 9050/bombeiros
                  3,20 m; NR-18 pode exigir 2,90 m -> parametrizavel).
    Retorna dict com resultados (single-flight) OU, se desnivel > limite_lance,
    dict COMPOSTO (multi=True) com N lances + (N-1) patamares."""
    # Desnivel alto -> divide em lances com patamar de descanso (nao mais aborta).
    if desnivel > limite_lance:
        return _dimensiona_multi(desnivel, projecao_horizontal, largura,
                                 q_acidental, fy, limite_lance)
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
    if r.get("multi"):
        lc = r["lance"]
        L = ["ESCADA INDUSTRIAL METALICA (MULTI-LANCE com PATAMAR)",
             f"  Desnivel total: {r['desnivel_total_m']:.2f} m em {r['n_lances']} "
             f"lances de {r['desnivel_por_lance_m']:.2f} m (limite {r['limite_lance_m']:.2f} m/lance)",
             f"  Patamares: {r['n_patamares']} x {r['patamar_comprimento_m']:.2f} m "
             f"(comprimento) x {r['patamar_largura_m']:.2f} m (largura)",
             f"  Projecao necessaria: {r['projecao_necessaria_m']:.1f} m "
             f"(disponivel {r['projecao_disponivel_m']:.1f} m -> "
             f"{'CABE' if r['espaco_suficiente'] else '*** NAO CABE no espaco ***'})",
             f"  Desenvolvimento total ~ {r['L_desenvolvimento_m']:.1f} m",
             f"  Longarina (por lance): {lc['perfil']} (L={lc['L']:.2f} m)",
             f"  Por lance: {lc['n_espelhos']} espelhos x {lc['espelho_mm']:.0f} mm ; "
             f"{lc['n_pisos']} pisos x {lc['piso_mm']:.0f} mm ; Blondel {lc['blondel_cm']:.1f} cm",
             f"  M_max = {lc['M_max']:.1f} kN.m ; V_max = {lc['V_max']:.1f} kN ; "
             f"interacao {lc['interacao']:.3f} ; flecha {lc['delta_mm']:.1f} mm",
             f"  [{r['obs_patamar']}]"]
        import re
        return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))
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
    # MULTI-LANCE: desnivel 4,0 m > 3,2 m -> 2 lances de 2,0 m + 1 patamar (nao aborta)
    rm = dimensiona(desnivel=4.0, projecao_horizontal=6.0, largura=1.20)
    assert rm.get("ok") and rm.get("multi"), f"multi falhou: {rm.get('erro')}"
    assert rm["n_lances"] == 2 and rm["n_patamares"] == 1
    assert abs(rm["desnivel_por_lance_m"] - 2.0) < 1e-9
    assert abs(rm["desnivel_total_m"] - 4.0) < 1e-9
    assert rm["perfil"]                                  # dimensionou a longarina do lance
    # cada lance <= limite_lance
    assert rm["desnivel_por_lance_m"] <= 3.20 + 1e-9
    # desnivel altissimo -> mais lances (7 m -> 3 lances)
    r7 = dimensiona(desnivel=7.0, projecao_horizontal=12.0, largura=1.20)
    assert r7.get("ok") and r7["n_lances"] == 3 and r7["n_patamares"] == 2
    # a geometria e valida (Blondel derivado), mas o espaco em planta e curto ->
    # dimensiona a escada e sinaliza que NAO CABE (nao inventa que cabe).
    rbad = dimensiona(desnivel=6.5, projecao_horizontal=1.0, largura=1.20)
    assert rbad.get("ok") and rbad.get("multi")
    assert rbad["espaco_suficiente"] is False
    assert rbad["projecao_necessaria_m"] > rbad["projecao_disponivel_m"]
    # com espaco folgado -> cabe
    rok = dimensiona(desnivel=6.5, projecao_horizontal=20.0, largura=1.20)
    assert rok["espaco_suficiente"] is True
    # limite_lance parametrizavel (NR-18 2,90 m): desnivel 3,0 m passa a exigir patamar
    r29 = dimensiona(desnivel=3.0, projecao_horizontal=6.0, largura=1.20, limite_lance=2.90)
    assert r29.get("multi") and r29["n_lances"] == 2
    print(f"escada self-test PASSED: {r['n_espelhos']} espelhos, "
          f"espelho={r['espelho_mm']:.0f}mm, piso={r['piso_mm']:.0f}mm, "
          f"Blondel={r['blondel_cm']:.1f}cm, perfil={r['perfil']} ; "
          f"multi: {rm['n_lances']} lances + {rm['n_patamares']} patamar OK")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(dimensiona(3.0, 4.5, 1.20)))
