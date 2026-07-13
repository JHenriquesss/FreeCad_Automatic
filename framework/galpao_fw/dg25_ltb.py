# ============================================================================
# dg25_ltb.py - CROSS-CHECK (validacao) da FLT de misula pelo AISC Design Guide 25.
# Calcula o momento de flambagem lateral com torcao ELASTICO, M_eLTB, de um trecho
# de barra linearmente afunilada, e COMPARA com o Mcr do NBR 8800 Anexo J. E uma
# CONFERENCIA INDEPENDENTE - INFORMATIVA. NAO altera o dimensionamento, que segue a
# NBR 8800 (Anexo J, item 36 homologado).
#
# Base (AISC Design Guide 25, "Frame Design Using Web-Tapered Members", pg 60-61,
# lida verbatim das imagens das paginas):
#   5.4.3 General Procedure - LTB:
#   1) Tensao de FLT elastica pela AISC Spec. Eq. F4-5, com as propriedades da secao
#      no MEIO do comprimento destravado e Cb:
#        F_eLTB = Cb pi^2 E / (Lb/rt)^2 * sqrt(1 + 0.078 (J/(Sxc ho)) (Lb/rt)^2)
#                                                             (5.4-10, Spec. F4-5)
#        rt = bfc / sqrt(12 (ho/d + (1/6) aw h^2/(ho d)))     (5.4-11, Spec. F4-10)
#        ho = distancia entre centroides das mesas (= d - tf, I duplo-sim)
#        aw = hc tw / (bfc tfc)   (para rt, o limite <=10 NAO se aplica)
#        hc = 2 x (centroide -> face interna da mesa comprimida) = hw (I duplo-sim)
#        Se a alma e esbelta (hc/tw > 5.70 sqrt(E/Fy)) OU Iyc/Iy <= 0.23 -> J = 0;
#        senao  J = h tw^3/3 + bft tft^3/3 (1-0.63 tft/bft)
#                            + bfc tfc^3/3 (1-0.63 tfc/bfc)   (5.4-12)
#   2) M_eLTB = F_eLTB * Sxc (Sxc = Wx). (gamma_eLTB = F_eLTB/fr, 5.4-13, e a razao
#      de resistencia; aqui o cross-check usa o MOMENTO M_eLTB = F_eLTB Sxc.)
#
# Diferenca-chave do cross-check: o DG25 usa a secao do MEIO do trecho; o NBR 8800
# Anexo J (J.4.2) usa a secao de MAIOR altura. A razao M_eLTB(DG25)/Mcr(NBR) revela
# se o Anexo J e conservador ou liberal relativamente ao DG25.
# Premissa: perfil I duplamente simetrico (mesas iguais). Unidades SI (m, kN).
# ============================================================================
"""Cross-check DG25 da FLT elastica de misula vs NBR 8800 Anexo J. Unidades m, kN."""

from __future__ import annotations
import math
import check_nbr8800 as ck

E = ck.E
GA1 = ck.GA1


def hc(sec):
    """Duas vezes a distancia do centroide a face interna da mesa comprimida
    (I duplo-simetrico) = altura livre da alma hw."""
    return sec["d"] - 2.0 * sec["tf"]


def ho(sec):
    """Distancia entre os centroides das mesas = d - tf (I duplo-simetrico)."""
    return sec["d"] - sec["tf"]


def aw(sec):
    """aw = hc tw / (bfc tfc) (para rt, sem o limite de 10)."""
    return hc(sec) * sec["tw"] / (sec["bf"] * sec["tf"])


def rt(sec):
    """Raio de giracao efetivo rt (5.4-11 / Spec. F4-10), I duplo-simetrico.
    ATENCAO (parecer item 42 F2): o 'h' que vai ao QUADRADO e a ALTURA LIVRE DA ALMA
    (hc = hw = d-2tf), NAO a altura total d. O d aparece so em ho/d e /(ho*d)."""
    d, bf = sec["d"], sec["bf"]
    h = hc(sec)                                        # altura livre da alma (hw), NAO d
    ho_ = ho(sec); aw_ = aw(sec)
    return bf / math.sqrt(12.0 * (ho_ / d + (1.0 / 6.0) * aw_ * h ** 2 / (ho_ * d)))


def e_alma_esbelta(sec, fy):
    """hc/tw > 5.70 sqrt(E/Fy) (para o ramo J=0 do DG25)."""
    return hc(sec) / sec["tw"] > 5.70 * math.sqrt(E / fy)


def J_dg(sec, fy):
    """Constante de torcao J do DG25 (5.4-12). Se a alma e esbelta OU Iyc/Iy<=0.23,
    J=0; senao, forma completa com o desconto (1-0.63 t/b) por mesa. I duplo-sim:
    Iyc/Iy = 0.5 -> so a alma esbelta zera J."""
    bf, tf, tw = sec["bf"], sec["tf"], sec["tw"]
    Iyc_sobre_Iy = 0.5                                # duplo-simetrico
    if e_alma_esbelta(sec, fy) or Iyc_sobre_Iy <= 0.23:
        return 0.0
    h = hc(sec)
    termo_mesa = bf * tf ** 3 / 3.0 * (1.0 - 0.63 * tf / bf)
    return h * tw ** 3 / 3.0 + 2.0 * termo_mesa       # 2 mesas iguais


def f_eltb(sec, fy, Lb, Cb=1.0):
    """Tensao de FLT elastica F_eLTB (5.4-10 / Spec. F4-5)."""
    Sxc = sec["Wx"]; ho_ = ho(sec); rt_ = rt(sec); J = J_dg(sec, fy)
    lam = Lb / rt_
    return (Cb * math.pi ** 2 * E / lam ** 2) * \
        math.sqrt(1.0 + 0.078 * (J / (Sxc * ho_)) * lam ** 2)


def m_eltb(sec, fy, Lb, Cb=1.0):
    """Momento de FLT elastico do DG25: M_eLTB = F_eLTB * Sxc (kN.m)."""
    return f_eltb(sec, fy, Lb, Cb) * sec["Wx"]


def nbr_mcr(sec, fy, Lb, Cb=1.0):
    """Mcr da FLT elastica pelo NBR 8800 (mesma forma do check_nbr8800, Anexo G/F2):
    Mcr = Cb pi^2 E Iy/Lb^2 sqrt(Cw/Iy + 0.039 J Lb^2/Iy)."""
    Iy = sec["Iy"]
    Cw, J = ck._cw_j(sec)
    return (Cb * math.pi ** 2 * E * Iy / Lb ** 2) * \
        math.sqrt(Cw / Iy + 0.039 * J * Lb ** 2 / Iy)


def cross_check_flt(segs, fy, Lb, Cb=1.0, tol=0.20):
    """Compara o momento de FLT elastico do DG25 (secao do MEIO do trecho, 5.4.3)
    com o Mcr do NBR 8800 Anexo J (secao de MAIOR altura, J.4.2). segs = lista de
    {'props': sec, 'h_m': altura}. O MESMO Cb (escalar) multiplica os dois lados ->
    cancela na razao POR CONSTRUCAO do teste (nao e propriedade intrinseca: em tapered
    o Cb do DG25 5.4-2 difere do Cb do Anexo J; aqui isola-se so a diferenca da secao
    de referencia). Retorna dict com a razao e o veredito CONVERGE (|razao-1|<=tol).
    INFORMATIVO - nao altera dimensionamento."""
    valid = [s for s in segs if s.get("props")]
    if not valid:
        return {"M_dg": 0.0, "M_nbr": 0.0, "razao": float("nan"),
                "converge": False, "tol": tol, "sec_meio": None, "sec_funda": None}
    sec_meio = valid[len(valid) // 2]                 # meio do comprimento destravado
    sec_funda = max(valid, key=lambda s: s["h_m"])    # maior altura (J.4.2)
    M_dg = m_eltb(sec_meio["props"], fy, Lb, Cb)
    M_nbr = nbr_mcr(sec_funda["props"], fy, Lb, Cb)
    razao = M_dg / M_nbr if M_nbr > 0 else float("inf")
    return {"M_dg": M_dg, "M_nbr": M_nbr, "razao": razao,
            "converge": abs(razao - 1.0) <= tol, "tol": tol,
            "sec_meio": round(sec_meio["h_m"] * 1000, 1),
            "sec_funda": round(sec_funda["h_m"] * 1000, 1)}


def _selftest():
    import alma_variavel as av
    s = av.props_I(0.60, 0.25, 0.008, 0.016)
    assert rt(s) > 0 and aw(s) > 0
    assert J_dg(s, 250e3) > 0
    # alma esbelta zera J
    s_sl = av.props_I(0.95, 0.25, 0.004, 0.016)
    assert e_alma_esbelta(s_sl, 250e3) and J_dg(s_sl, 250e3) == 0.0
    # M_eLTB cresce com Lb menor
    assert m_eltb(s, 250e3, 3.0) > m_eltb(s, 250e3, 6.0) > 0
    # prismatico converge (DG25 meio ~ NBR funda mesma secao)
    segs = [{"props": av.props_I(0.60, 0.25, 0.008, 0.016), "h_m": 0.60}
            for _ in range(8)]
    r = cross_check_flt(segs, 250e3, Lb=4.0)
    assert r["converge"], f"prismatico deveria convergir (razao={r['razao']:.3f})"
    # Cb cancela na razao
    a = cross_check_flt(segs, 250e3, 4.0, Cb=1.0)["razao"]
    b = cross_check_flt(segs, 250e3, 4.0, Cb=2.3)["razao"]
    assert abs(a - b) < 1e-9
    print("dg25_ltb self-test PASSED "
          f"(prismatico razao DG25/NBR = {r['razao']:.3f}, CONVERGE)")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
