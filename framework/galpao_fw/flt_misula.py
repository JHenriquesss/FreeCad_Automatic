# ============================================================================
# flt_misula.py - FLT de barras de secao variavel (misula) por NBR 8800 Anexo J.
#
# Substitui o metodo conservador (secao mais funda + Cb=1,0 + M_max cego) pelo
# metodo NORMATIVO do Anexo J. IMPORTANTE: a NBR 8800 NAO usa "fator gamma de
# misula" (isso e AISC Design Guide 25) - o caminho da norma e o Anexo J.
#
# Base normativa (lida verbatim de pesquisa/aço/nbr8800_2008_1.pdf):
#   J.1  Aplica-se a secoes I/H/caixao com 2 eixos de simetria; mesas de secao
#        constante entre secoes contidas; altura da alma variando linearmente.
#   J.4.2  Na determinacao de lambda, lambda_p, lambda_r (qualquer estado-limite),
#          adotar as propriedades da secao de MAIOR altura.
#   J.4.1  FLT (5.4): M_Rd,FLT >= M_Sd na secao de MAIOR tensao de compressao nas
#          mesas. Cb por analise racional (ou 1,0, conservador).
#   5.4.2.3a  Cb = 12,5 Mmax / (2,5 Mmax + 3 MA + 4 MB + 3 MC) * Rm  <= 3,0.
#          MA/MB/MC = |M| a 1/4, 1/2, 3/4 de Lb ; Rm=1,0 (secao duplo-simetrica).
#   5.4.2.3b  Trecho em balanco (uma extremidade livre): Cb = 1,0.
#   5.4.2.2  Teto: M_Rd <= 1,50 W fy / gamma_a1 (ja imposto em check_nbr8800).
#
# Nota: gamma AISC DG25 fica como alternativa NAO adotada (nao normativa na NBR).
# Unidades SI: m, kN (fy em kN/m2).
# ============================================================================
"""FLT de misula por NBR 8800 Anexo J. Unidades m, kN."""

from __future__ import annotations
import check_nbr8800 as ck

GA1 = ck.GA1


def cb_momento(Ms, balanco=False):
    """Fator Cb (5.4.2.3a) para o diagrama de momento no comprimento destravado.
    Ms = lista de |M| ao longo de Lb (>=1 valor). Usa Mmax e os pontos a 1/4, 1/2,
    3/4 por interpolacao linear na lista. Rm=1,0 (secao duplo-simetrica). Teto 3,0.
    balanco=True (trecho em balanco, 5.4.2.3b) -> Cb=1,0."""
    if balanco:
        return 1.0
    vals = [abs(m) for m in Ms]
    if len(vals) == 1:
        return 1.0

    def _interp(frac):
        x = frac * (len(vals) - 1)
        i = int(x)
        if i >= len(vals) - 1:
            return vals[-1]
        return vals[i] + (vals[i + 1] - vals[i]) * (x - i)

    Mmax = max(vals)
    MA, MB, MC = _interp(0.25), _interp(0.50), _interp(0.75)
    denom = 2.5 * Mmax + 3.0 * MA + 4.0 * MB + 3.0 * MC
    if denom <= 0:
        return 1.0
    cb = 12.5 * Mmax / denom            # Rm = 1,0
    return min(cb, 3.0)


def flt_misula(segmentos, fy, Lb, cb=None, balanco=False):
    """FLT de trecho de misula por Anexo J. segmentos = lista de dicts com M (kN.m),
    props (dict de check_nbr8800), h_m (altura, m), ORDENADOS ao longo do trecho.
      - lambda da secao de MAIOR altura (J.4.2);
      - Cb racional (5.4.2.3a) do diagrama de M do trecho, salvo cb explicito;
      - demanda M_Sd na secao de MAIOR tensao M/Wx (J.4.1).
    Retorna util, Cb, M_Rd (kN.m), secao_critica (indice), h_secao_flt (m)."""
    segs = [s for s in segmentos if s.get("props")]
    if not segs:
        return {"util": 0.0, "Cb": 1.0, "M_Rd": 0.0, "secao_critica": None,
                "h_secao_flt": None}
    # J.4.2 - secao de MAIOR altura governa a esbeltez da FLT
    deep = max(segs, key=lambda s: s.get("h_m") or s["props"]["d"])
    # Cb - analise racional (5.4.2.3a) a partir do diagrama de M do trecho
    Cb = cb_momento([s["M"] for s in segs], balanco=balanco) if cb is None else cb
    _mn, _gov, det = ck.momento_resistente(dict(deep["props"]), fy, Lb, Cb=Cb)
    M_Rd = det["Mn_flt"] / GA1
    # J.4.1 - demanda na secao de MAIOR tensao de compressao nas mesas (max M/Wx).
    # A capacidade M_Rd e referida a secao mais funda (maior W); a demanda
    # equivalente nessa referencia = (max sigma) * Wx_deep = max(M/Wx) * Wx_deep.
    sig = [abs(s["M"]) / s["props"]["Wx"] for s in segs]
    k_crit = sig.index(max(sig))
    Wx_deep = deep["props"]["Wx"]
    M_dem = sig[k_crit] * Wx_deep
    return {"util": M_dem / M_Rd if M_Rd > 0 else float("inf"),
            "Cb": Cb, "M_Rd": M_Rd, "secao_critica": k_crit,
            "h_secao_flt": deep.get("h_m") or deep["props"]["d"],
            "M_dem": M_dem}


def _selftest():
    import alma_variavel as av
    # Cb: momento uniforme -> 1,0 ; gradiente -> >1 ; teto 3,0
    assert abs(cb_momento([100.0] * 5) - 1.0) < 1e-6
    assert cb_momento([100.0, 75.0, 50.0, 25.0, 0.0]) > 1.3
    assert cb_momento([100.0, 5.0, 2.0, 5.0, 3.0]) <= 3.0 + 1e-9
    assert cb_momento([100.0, 50.0], balanco=True) == 1.0
    # flt_misula: secao maior altura + Cb reduz util
    secs = av.secao_tapered(0.60, 0.30, 0.20, 0.008, 0.0125, nseg=8)
    Ms = [180.0, 150.0, 125.0, 105.0, 88.0, 74.0, 62.0, 52.0]
    segs = [{"M": Ms[i], "props": s["props"], "h_m": s["h_m"]}
            for i, s in enumerate(secs)]
    r = flt_misula(segs, 250e3, 4.0)
    rc = flt_misula(segs, 250e3, 4.0, cb=1.0)
    assert abs(r["h_secao_flt"] - 0.60) < 0.02          # secao mais funda (J.4.2)
    assert r["Cb"] > 1.0 and r["util"] < rc["util"]     # Cb racional afrouxa
    assert r["M_Rd"] > rc["M_Rd"]
    print("flt_misula self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
