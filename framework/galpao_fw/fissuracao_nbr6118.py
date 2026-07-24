# ============================================================================
# fissuracao_nbr6118.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Estado-limite de ABERTURA DE FISSURAS (ELS-W) da NBR 6118:2014, item 17.3.3.2.
# A durabilidade de uma peca de concreto armado depende de a fissura de tracao
# ficar abaixo do limite da classe de agressividade (Tabela 13.4). Este modulo:
#   1. calcula a tensao na armadura no ESTADIO II (secao fissurada) sob o momento
#      de servico -> sigma_s;
#   2. aplica as DUAS expressoes de wk da norma e toma o MENOR:
#        wk = (phi/(12,5 eta1))*(sigma_si/Es)*(3 sigma_si/fctm)
#        wk = (phi/(12,5 eta1))*(sigma_si/Es)*(4/rho_ri + 45)
#      eta1 = 2,25 (barra nervurada, 9.3.2.1); rho_ri = As/Acri (area de envolvimento,
#      retangulo a no maximo 7,5 phi do eixo da barra, Fig.17.3);
#   3. compara com o limite por CAA: I 0,4 ; II/III 0,3 ; IV 0,2 mm (Tab.13.4).
# Valores lidos do PDF NBR 6118:2014 (NotebookLM), nao de memoria.
# Unidades internas: m, kN (fck em kN/m2) ; phi em mm ; wk em mm.
# ============================================================================
"""Controle da fissuracao (ELS-W) da NBR 6118:2014 17.3.3.2: abertura de fissura
wk no estadio II e verificacao contra o limite da classe de agressividade."""

from __future__ import annotations

import math

ETA1_NERVURADA = 2.25          # coef. de conformacao superficial, barra nervurada (9.3.2.1)
ETA1_LISA = 1.0
ETA1_ENTALHADA = 1.4
ES_ACO = 210e6                 # modulo do aco (kN/m2), 8.3.6

# Tabela 13.4 - limite de wk (mm) por CAA, concreto armado, combinacao frequente
WK_LIM_MM = {"I": 0.4, "II": 0.3, "III": 0.3, "IV": 0.2}


def modulo_secante(fck, alpha_e=1.0):
    """Ecs (modulo secante) da NBR 6118 8.2.8. fck em kN/m2 -> Ecs em kN/m2.
    Eci = alpha_e*5600*sqrt(fck[MPa]); Ecs = alpha_i*Eci, alpha_i=0,8+0,2 fck/80<=1."""
    fck_MPa = fck / 1000.0
    Eci = alpha_e * 5600.0 * math.sqrt(fck_MPa)          # MPa
    alpha_i = min(0.8 + 0.2 * fck_MPa / 80.0, 1.0)
    return alpha_i * Eci * 1000.0                          # kN/m2


def fctm(fck):
    """Resistencia media a tracao (8.2.5). fck em kN/m2 -> kN/m2."""
    fck_MPa = fck / 1000.0
    v = 0.3 * fck_MPa ** (2.0 / 3.0) if fck_MPa <= 50.0 else 2.12 * math.log(1 + 0.11 * fck_MPa)
    return v * 1000.0


def sigma_s_estadio2(Ms, b, d, As, fck):
    """Tensao de tracao na armadura no estadio II (secao fissurada, linha neutra
    por homogeneizacao). Ms em kN.m ; b,d em m ; As em m2 ; fck em kN/m2 -> kN/m2."""
    Ecs = modulo_secante(fck)
    ae = ES_ACO / Ecs                                     # razao modular
    rho = As / (b * d)
    xi = -ae * rho + math.sqrt((ae * rho) ** 2 + 2.0 * ae * rho)   # x/d
    x = xi * d
    I_II = b * x ** 3 / 3.0 + ae * As * (d - x) ** 2       # inercia fissurada homog.
    sigma_s = ae * Ms * (d - x) / I_II                     # kN/m2
    return sigma_s, x, I_II


def area_envolvimento(b, h, d, phi_mm):
    """Area de envolvimento Acri (Fig.17.3): retangulo cujos lados nao distam mais
    de 7,5 phi do eixo da barra tracionada. Faixa de altura 2*min(h-d ; 7,5 phi)
    pela largura b. Retorna (Acri_m2, rho_nao) - rho calculado fora com As."""
    a_face = h - d                                         # face tracionada -> eixo da barra
    meia_faixa = min(a_face, 7.5 * phi_mm / 1000.0)
    Acri = b * (2.0 * meia_faixa)
    return Acri


def abertura_wk(phi_mm, sigma_s, fck, rho_ri, eta1=ETA1_NERVURADA):
    """Abertura caracteristica de fissura wk (17.3.3.2), MENOR das duas expressoes.
    sigma_s, fck em kN/m2 ; phi em mm ; rho_ri = As/Acri. Retorna (wk, wk1, wk2) em mm."""
    fct = fctm(fck)
    base = phi_mm / (12.5 * eta1) * (sigma_s / ES_ACO)     # phi[mm] * strain -> mm
    wk1 = base * (3.0 * sigma_s / fct)
    wk2 = base * (4.0 / rho_ri + 45.0)
    return min(wk1, wk2), wk1, wk2


def verifica_fissuracao(caso):
    """Verifica o ELS-W de uma secao retangular fletida de concreto armado.
    caso: {
      'Ms' : momento de SERVICO (kN.m, combinacao frequente).
      'b','h','d' : secao e altura util (m). 'As' : armadura tracionada (m2).
      'fck': (kN/m2). 'phi_mm': diametro da barra. 'CAA': 'I'|'II'|'III'|'IV' (default 'II').
      'eta1' (default 2,25 nervurada).
    }"""
    b = caso["b"]; h = caso["h"]; d = caso["d"]; As = caso["As"]
    fck = caso["fck"]; phi = caso["phi_mm"]; Ms = caso["Ms"]
    CAA = caso.get("CAA", "II"); eta1 = caso.get("eta1", ETA1_NERVURADA)
    sigma_s, x, I_II = sigma_s_estadio2(Ms, b, d, As, fck)
    Acri = area_envolvimento(b, h, d, phi)
    rho_ri = As / Acri
    wk, wk1, wk2 = abertura_wk(phi, sigma_s, fck, rho_ri, eta1)
    lim = WK_LIM_MM[CAA]
    return {"CAA": CAA, "Ms": round(Ms, 2), "sigma_s_MPa": round(sigma_s / 1000.0, 1),
            "x_m": round(x, 4), "rho_ri": round(rho_ri, 4),
            "wk_mm": round(wk, 3), "wk1_mm": round(wk1, 3), "wk2_mm": round(wk2, 3),
            "wk_lim_mm": lim, "OK": wk <= lim + 1e-9}


def relatorio_pt(r):
    L = ["CONTROLE DA FISSURACAO ELS-W (NBR 6118 17.3.3.2)",
         f"  CAA {r['CAA']} ; Ms {r['Ms']:.1f} kN.m ; sigma_s {r['sigma_s_MPa']:.0f} MPa "
         f"(estadio II) ; rho_ri {r['rho_ri']:.4f}",
         f"  wk = min({r['wk1_mm']:.3f} ; {r['wk2_mm']:.3f}) = {r['wk_mm']:.3f} mm "
         f"<= {r['wk_lim_mm']:.1f} mm -> {'ATENDE' if r['OK'] else 'REPROVA'}"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # viga 20x50, d=0,45, As=8 cm2, C30, Ms=80 kN.m, phi 16, CAA II
    r = verifica_fissuracao({"Ms": 80.0, "b": 0.20, "h": 0.50, "d": 0.45,
                             "As": 8e-4, "fck": 30e3, "phi_mm": 16.0, "CAA": "II"})
    assert 100 < r["sigma_s_MPa"] < 400, r          # tensao de servico plausivel
    assert r["wk_mm"] == min(r["wk1_mm"], r["wk2_mm"])
    assert 0.0 < r["wk_mm"] < 1.0
    # CAA IV e mais restritivo que CAA I
    r1 = verifica_fissuracao({"Ms": 80.0, "b": 0.20, "h": 0.50, "d": 0.45, "As": 8e-4,
                              "fck": 30e3, "phi_mm": 16.0, "CAA": "I"})
    r4 = verifica_fissuracao({"Ms": 80.0, "b": 0.20, "h": 0.50, "d": 0.45, "As": 8e-4,
                              "fck": 30e3, "phi_mm": 16.0, "CAA": "IV"})
    assert r1["wk_lim_mm"] == 0.4 and r4["wk_lim_mm"] == 0.2
    # mais armadura (menor tensao) -> menor fissura
    r_mais = verifica_fissuracao({"Ms": 80.0, "b": 0.20, "h": 0.50, "d": 0.45,
                                  "As": 16e-4, "fck": 30e3, "phi_mm": 16.0})
    assert r_mais["wk_mm"] < r["wk_mm"]
    # eta1 exato da norma
    assert ETA1_NERVURADA == 2.25 and WK_LIM_MM["II"] == 0.3
    print("fissuracao_nbr6118 self-test PASSED")
    print(relatorio_pt(r))


if __name__ == "__main__":
    _selftest()
