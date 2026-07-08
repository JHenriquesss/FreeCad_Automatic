# ============================================================================
# neve.py - CARGA DE NEVE EM COBERTURAS (EN 1991-1-3)
# Para telhados de 2 aguas SIMETRICOS (alpha_esq = alpha_dir).
# Inclui casos simetrico e assimetrico (vento varrendo neve, Secao 5.3.3)
# e restricao de deslizamento impedido (Secao 5.3.3).
# ============================================================================
"""Carga de neve em coberturas simetricas. Saidas PT. Unidades: kN/m2."""

from __future__ import annotations
import math


def carga_neve(sk_kN_m2=0.0, theta_graus=5.71, Ce=1.0, Ct=1.0,
               deslizamento_livre=True):
    """Carga de neve na cobertura (EN 1991-1-3). Para aguas SIMETRICAS.
    Retorna 3 cenarios, cada um como tupla (agua_E, agua_D) em kN/m2.
    
    sk = carga de neve no solo (kN/m2) — INPUT regional.
    theta = inclinacao do telhado (graus, mesma para ambas as aguas).
    Ce = coeficiente de exposicao (1.0 normal).
    Ct = coeficiente termico (1.0 normal; reducao apenas com justificativa
         termodinamica, EN Secao 5.2.8).
    deslizamento_livre = True (neve escorrega livremente, reducao permitida
         para theta>30). Se False (platibanda/retentores), mu nunca reduz
         abaixo de 0.8 (Secao 5.3.3)."""
    th = min(theta_graus, 90.0)
    if th <= 30.0:
        mu = 0.8
    elif th < 60.0:
        mu = 0.8 * (60.0 - th) / 30.0 if deslizamento_livre else 0.8
    else:
        mu = 0.0 if deslizamento_livre else 0.8
    s_base = sk_kN_m2 * Ce * Ct
    # 3 cenarios: cada um como (agua_E, agua_D)
    simetrico = (round(s_base * mu, 4), round(s_base * mu, 4))
    assim1 = (round(s_base * 0.5 * mu, 4), round(s_base * mu, 4))
    assim2 = (round(s_base * mu, 4), round(s_base * 0.5 * mu, 4))
    return {"sk_kN_m2": sk_kN_m2, "theta_graus": th,
            "mu": round(mu, 3), "Ce": Ce, "Ct": Ct,
            "deslizamento_livre": deslizamento_livre,
            "simetrico_kN_m2": simetrico,
            "assimetrico_1_kN_m2": assim1,
            "assimetrico_2_kN_m2": assim2,
            "obs": "So relevante para regioes serranas do Sul (SC/RS)"}


def relatorio_pt(r):
    def _fmt(t):
        return f"({t[0]:.4f}, {t[1]:.4f})"
    L = ["CARGA DE NEVE NA COBERTURA (EN 1991-1-3) - aguas simetricas",
         f"  Carga no solo sk = {r['sk_kN_m2']:.2f} kN/m2",
         f"  Inclinacao = {r['theta_graus']:.1f} deg ; mu = {r['mu']:.3f}",
         f"  Deslizamento livre: {r['deslizamento_livre']}",
         f"  SIMETRICO:          {_fmt(r['simetrico_kN_m2'])}",
         f"  ASSIMETRICO 1:      {_fmt(r['assimetrico_1_kN_m2'])}",
         f"  ASSIMETRICO 2:      {_fmt(r['assimetrico_2_kN_m2'])}"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    r = carga_neve(1.0, 20, 1.0, 1.0)
    assert r["simetrico_kN_m2"] == (0.8, 0.8)
    assert r["assimetrico_1_kN_m2"] == (0.4, 0.8)
    assert r["assimetrico_2_kN_m2"] == (0.8, 0.4)
    # deslizamento impedido: mu trava em 0.8 mesmo para theta > 30
    r2 = carga_neve(1.0, 45, 1.0, 1.0, deslizamento_livre=False)
    assert r2["mu"] == 0.8, f"mu travado = {r2['mu']}"
    assert r2["simetrico_kN_m2"] == (0.8, 0.8)
    r3 = carga_neve(0.0)
    assert r3["simetrico_kN_m2"] == (0.0, 0.0)
    print("neve self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(carga_neve(0.5, 25)))
