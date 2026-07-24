# ============================================================================
# perdas_protensao_nbr6118.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Perdas de protensao de uma peca PRE-TRACIONADA (NBR 6118:2014, item 9.6.3),
# substituindo a estimativa unica de 20% por um calculo com procedencia:
#   - PERDA IMEDIATA por encurtamento elastico do concreto (9.6.3.3.1, pre-tracao):
#       Dsigma_enc = alpha_p * sigma_cp , alpha_p = Ep/Eci
#     (na pre-tracao a liberacao e simultanea -> perda integral, sem o fator
#     (n-1)/2n que e exclusivo da POS-tracao 9.6.3.3.2.1);
#   - PERDAS PROGRESSIVAS pelo processo APROXIMADO (9.6.3.4.3), aco de relaxacao
#     BAIXA (RB), em porcentagem de sigma_p0:
#       Dsigma_p/sigma_p0 [%] = 7,4 + (alpha_p/18,7) * phi^1,07 * (3 + sigma_c,p0g)
#     com sigma_c,p0g em MPa (compressao positiva) e phi = coef. de fluencia.
# Valores tipicos (Tab.A.1, ao ar livre ~70% UR): phi 1,5..2,5 ; retracao
# -3,8e-4..-6,2e-4. Relaxacao ja embutida no 7,4 (RB). Lido do PDF NBR 6118
# (NotebookLM), nao de memoria. Unidades: m, kN (tensoes em kN/m2).
# ============================================================================
"""Perdas de protensao (pre-tracao) da NBR 6118:2014 9.6.3: encurtamento elastico
imediato + processo aproximado 9.6.3.4.3 (relaxacao baixa)."""

from __future__ import annotations

import math

EP_ACO = 200e6                 # modulo do aco de protensao (kN/m2), 8.4.7

# fluencia/retracao tipicos (Tab.A.1 NBR 6118, ao ar livre ~70% UR)
PHI_FLUENCIA_PADRAO = 2.0      # abatimento 5-9 cm, ao ar livre
EPS_CS_PADRAO = -5.0e-4        # retracao correspondente


def _eci(fckj):
    """Modulo tangente inicial na data da protensao. fckj em kN/m2 -> kN/m2."""
    return 5600.0 * math.sqrt(fckj / 1000.0) * 1000.0


def perdas_pretracao(sigma_pi, Ap, ep, Mg, b, h, fckj, phi=PHI_FLUENCIA_PADRAO):
    """Perdas de uma peca pre-tracionada retangular.
    sigma_pi = tensao de estiramento (kN/m2) ; Ap = area de cordoalha (m2) ;
    ep = excentricidade abaixo do CG (m) ; Mg = momento de peso proprio (kN.m) ;
    b,h = secao (m) ; fckj = fck na data da protensao (kN/m2) ; phi = coef. fluencia.
    Retorna dict com as parcelas e a FRACAO total de perda."""
    Ac = b * h
    Ic = b * h ** 3 / 12.0
    Eci = _eci(fckj)
    alpha_p = EP_ACO / Eci

    # tensao no concreto ao nivel do cabo (compressao positiva), forca inicial
    P_ini = sigma_pi * Ap
    sigma_cp = P_ini / Ac + P_ini * ep ** 2 / Ic - Mg * ep / Ic     # kN/m2

    # 1) perda imediata por encurtamento elastico (pre-tracao)
    dsig_enc = alpha_p * sigma_cp                                   # kN/m2
    sigma_p0 = sigma_pi - dsig_enc                                  # apos perda imediata

    # 2) perda progressiva (9.6.3.4.3, RB) em % de sigma_p0
    sigma_cp0g_MPa = sigma_cp / 1000.0
    prog_pct = 7.4 + (alpha_p / 18.7) * (phi ** 1.07) * (3.0 + sigma_cp0g_MPa)
    dsig_prog = prog_pct / 100.0 * sigma_p0                         # kN/m2

    perda_total = (dsig_enc + dsig_prog) / sigma_pi
    return {"alpha_p": round(alpha_p, 2), "sigma_cp_MPa": round(sigma_cp / 1000.0, 2),
            "dsig_enc_MPa": round(dsig_enc / 1000.0, 1),
            "perda_imediata_pct": round(dsig_enc / sigma_pi * 100.0, 1),
            "prog_pct": round(prog_pct, 1),
            "dsig_prog_MPa": round(dsig_prog / 1000.0, 1),
            "perda_total_frac": round(perda_total, 3),
            "perda_total_pct": round(perda_total * 100.0, 1), "phi": phi}


def _selftest():
    # viga 20x60, C40, 6 cordoalhas Ø12,7 (Ap=6,06 cm2), ep~0,25 m
    sigma_pi = 0.74 * 1900e3                       # ~ estiramento tipico
    Ap = 6 * 1.01e-4
    Mg = 25.0 * 0.20 * 0.60 * 15.0 ** 2 / 8.0      # peso proprio, vao 15 m
    r = perdas_pretracao(sigma_pi, Ap, 0.25, Mg, 0.20, 0.60, 40e3, phi=2.0)
    # perda total tipica de pre-tracao: ~10 a 25%
    assert 0.08 < r["perda_total_frac"] < 0.30, r
    assert r["perda_imediata_pct"] > 0 and r["prog_pct"] > 7.4
    # mais fluencia -> mais perda progressiva
    r_alto = perdas_pretracao(sigma_pi, Ap, 0.25, Mg, 0.20, 0.60, 40e3, phi=2.5)
    assert r_alto["perda_total_frac"] > r["perda_total_frac"]
    # concreto mais novo (fckj menor) -> Eci menor -> alpha_p maior -> mais perda
    r_novo = perdas_pretracao(sigma_pi, Ap, 0.25, Mg, 0.20, 0.60, 25e3, phi=2.0)
    assert r_novo["perda_total_frac"] > r["perda_total_frac"]
    print("perdas_protensao_nbr6118 self-test PASSED:",
          f"perda total {r['perda_total_pct']:.1f}% "
          f"(imediata {r['perda_imediata_pct']:.1f}% + prog {r['prog_pct']:.1f}%)")


if __name__ == "__main__":
    _selftest()
