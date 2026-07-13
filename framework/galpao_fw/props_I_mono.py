# ============================================================================
# props_I_mono.py - PROPRIEDADES DE PERFIL I MONOSSIMETRICO (mesas diferentes)
# Perfil I soldado com mesa COMPRIMIDA (bfc x tfc, no TOPO) diferente da mesa
# TRACIONADA (bft x tft, na BASE) e alma tw. Eixo forte x (flexao no plano da alma).
#
# Habilita o ramo monossimetrico real do AISC Design Guide 25 (F_L 5.4-15 via
# Sxt/Sxc, rt 5.4-11 via bfc, Rpc/Rpg via hc real) - ver dg25_ltb.py. Tambem serve
# a qualquer verificacao que precise de Wxc/Wxt distintos.
#
# Convencoes (todas verificadas por reducao ao caso duplo-simetrico bfc=bft,tfc=tft,
# que reproduz alma_variavel.props_I - ver _selftest e tests):
#   - y medido da FIBRA TRACIONADA extrema (base, y=0) para cima.
#   - ho = distancia entre centroides das mesas.
#   - hc = 2 x (centroide -> face interna da mesa comprimida)  [AISC: 2x alma comp.]
#   - hp = 2 x (LNP -> face interna da mesa comprimida)         [AISC: plastico]
#   - Cw (empenamento, I monossim.) = ho^2 * Iyc*Iyt/(Iyc+Iyt)  [reduz a Iy ho^2/4].
#   - J (Saint-Venant, secao aberta) = Sum b t^3/3 (1-0,63 t/b) mesas + hw tw^3/3.
# Unidades SI: m, kN (consistente com o resto do framework).
# ============================================================================
"""Propriedades de perfil I monossimetrico (mesas diferentes). Unidades m, kN."""

from __future__ import annotations
import math


def _integra_retangulos(rects):
    """rects = [(y_lo, y_hi, largura)]. Retorna (A, ybar, Ix) sobre o eixo
    centroidal, com ybar medido da origem (base)."""
    A = sum(w * (b - a) for (a, b, w) in rects)
    Q = sum(w * (b - a) * (a + b) / 2.0 for (a, b, w) in rects)   # 1o momento / origem
    ybar = Q / A
    Ix = 0.0
    for (a, b, w) in rects:
        h = b - a
        mid = (a + b) / 2.0
        Ix += w * h ** 3 / 12.0 + w * h * (mid - ybar) ** 2
    return A, ybar, Ix


def _zx_sobre(rects, yp):
    """Modulo plastico Zx = integral de largura*|y-yp| dy (exato p/ retangulos)."""
    Zx = 0.0
    for (a, b, w) in rects:
        if yp <= a or yp >= b:
            Zx += w * (b - a) * abs((a + b) / 2.0 - yp)
        else:                                         # LNP dentro do retangulo -> divide
            Zx += w * ((yp - a) ** 2 / 2.0 + (b - yp) ** 2 / 2.0)
    return Zx


def _lnp(rects, A):
    """Linha neutra plastica: y (da base) que divide a area ao meio."""
    alvo = A / 2.0
    acc = 0.0
    for (a, b, w) in rects:
        area = w * (b - a)
        if acc + area >= alvo:
            return a + (alvo - acc) / w                # dentro deste retangulo
        acc += area
    return rects[-1][1]                                # fallback (nao deve ocorrer)


def props_I_mono(d, bfc, tfc, bft, tft, tw):
    """Propriedades completas de um perfil I MONOSSIMETRICO de altura total d (m).
    Mesa comprimida (topo): bfc x tfc. Mesa tracionada (base): bft x tft. Alma tw.
    Retorna dict compativel com o consumido por check_nbr8800 e dg25_ltb, com:
      A, Ix, Iy, Wx(=Wxc, mesa comprimida), Wxc, Wxt, Zx, Wy, Zy, rx, ry, rt,
      d, bf(=bfc), tf(=tfc), tw, Av, bfc, tfc, bft, tft, hw, hc, hp, ho,
      Iyc, Iyt, Iyc_Iy, J, Cw, ybar, cc, ct.
    Reduz EXATAMENTE a alma_variavel.props_I quando bfc==bft e tfc==tft."""
    hw = d - tfc - tft                                 # altura livre da alma
    if hw <= 0:
        raise ValueError(f"Altura {d}m menor que tfc+tft={tfc+tft}m (inconsistente)")
    # retangulos da base (y=0) ao topo: mesa tracionada, alma, mesa comprimida
    rects = [(0.0, tft, bft),
             (tft, tft + hw, tw),
             (d - tfc, d, bfc)]
    A, ybar, Ix = _integra_retangulos(rects)
    ct = ybar                                          # base = fibra tracionada extrema
    cc = d - ybar                                      # topo = fibra comprimida extrema
    Wxt = Ix / ct
    Wxc = Ix / cc
    # eixo fraco
    Iyc = tfc * bfc ** 3 / 12.0
    Iyt = tft * bft ** 3 / 12.0
    Iy = Iyc + Iyt + hw * tw ** 3 / 12.0
    bf_max = max(bfc, bft)
    Wy = 2.0 * Iy / bf_max
    # modulo plastico eixo forte (LNP) e eixo fraco
    yp = _lnp(rects, A)
    Zx = _zx_sobre(rects, yp)
    Zy = tfc * bfc ** 2 / 4.0 + tft * bft ** 2 / 4.0 + hw * tw ** 2 / 4.0
    # geometria de flambagem
    ho = (d - tfc / 2.0) - (tft / 2.0)                 # entre centroides das mesas
    hc = 2.0 * ((d - tfc) - ybar)                      # 2x alma comprimida (elastico)
    hp = 2.0 * ((d - tfc) - yp)                        # 2x alma comprimida (plastico)
    Iyc_Iy = Iyc / Iy
    # J (Saint-Venant) e Cw (empenamento monossimetrico)
    J = (bfc * tfc ** 3 / 3.0 * (1.0 - 0.63 * tfc / bfc)
         + bft * tft ** 3 / 3.0 * (1.0 - 0.63 * tft / bft)
         + hw * tw ** 3 / 3.0)
    Cw = ho ** 2 * Iyc * Iyt / (Iyc + Iyt)
    # rt (DG25 5.4-11) usa a mesa COMPRIMIDA e a alma comprimida hc
    aw = hc * tw / (bfc * tfc)
    rt = bfc / math.sqrt(12.0 * (ho / d + (1.0 / 6.0) * aw * hc ** 2 / (ho * d)))
    return {"A": A, "Ix": Ix, "Iy": Iy, "Wx": Wxc, "Wxc": Wxc, "Wxt": Wxt,
            "Zx": Zx, "Wy": Wy, "Zy": Zy, "rx": math.sqrt(Ix / A),
            "ry": math.sqrt(Iy / A), "rt": rt, "d": d, "bf": bfc, "tf": tfc,
            "tw": tw, "Av": hw * tw, "bfc": bfc, "tfc": tfc, "bft": bft, "tft": tft,
            "hw": hw, "hc": hc, "hp": hp, "ho": ho, "Iyc": Iyc, "Iyt": Iyt,
            "Iyc_Iy": Iyc_Iy, "J": J, "Cw": Cw, "ybar": ybar, "cc": cc, "ct": ct}


def _selftest():
    import alma_variavel as av
    # reducao ao duplo-simetrico: bfc=bft, tfc=tft -> bate com props_I
    d, bf, tw, tf = 0.60, 0.25, 0.008, 0.016
    m = props_I_mono(d, bf, tf, bf, tf, tw)
    s = av.props_I(d, bf, tw, tf)
    for k in ("A", "Ix", "Iy", "Wx", "Zx"):
        assert abs(m[k] - s[k]) < 1e-9, f"{k}: mono {m[k]} != dupl {s[k]}"
    assert abs(m["Wxc"] - m["Wxt"]) < 1e-12                 # simetrico
    assert abs(m["Iyc_Iy"] - 0.5) < 1e-3          # ~0.4997 (termo tw^3 da alma no Iy)
    assert abs(m["ho"] - (d - tf)) < 1e-12
    assert abs(m["hc"] - (d - 2 * tf)) < 1e-9
    # monossimetrico: mesa comprimida MAIOR -> centroide sobe -> cc<ct -> Wxc>Wxt
    mm = props_I_mono(0.60, 0.30, 0.019, 0.20, 0.0125, 0.008)
    assert mm["cc"] < mm["ct"] and mm["Wxc"] > mm["Wxt"]
    assert mm["Iyc_Iy"] > 0.5                               # mesa comp. domina Iy
    assert 0 < mm["hc"] and 0 < mm["hp"] and mm["ho"] > 0
    # dg25 F_L monossimetrico (mesa tracionada menor -> Sxt/Sxc<0.7 -> rampa 5.4-15)
    import dg25_ltb as dg
    fy = 345e3
    # (i) mesa tracionada bem menor -> Sxt/Sxc<0.5 -> F_L clampado em 0.5 Fy (5.4-15)
    mt = props_I_mono(0.60, 0.28, 0.019, 0.12, 0.0095, 0.008)
    razao = mt["Wxt"] / mt["Wxc"]
    FL = dg.f_L(mt, fy)
    assert razao < 0.7 and abs(FL - max(fy * razao, 0.5 * fy)) < 1e-3
    assert abs(FL - 0.5 * fy) < 1e-3                        # clampado (razao<0.5)
    # (ii) razao na faixa (0.5,0.7) -> rampa ativa F_L = Fy*Sxt/Sxc
    mr = props_I_mono(0.60, 0.26, 0.016, 0.19, 0.011, 0.008)
    rr = mr["Wxt"] / mr["Wxc"]
    if 0.5 < rr < 0.7:
        assert abs(dg.f_L(mr, fy) - fy * rr) < 1e-3, f"rampa: {dg.f_L(mr,fy)} vs {fy*rr}"
    mn = dg.mn_ltb_dg(mt, fy, Lb=4.0, Cb=1.0)
    assert mn["Mn"] > 0 and mn["regiao"] in ("a", "b", "c")
    print(f"props_I_mono self-test PASSED (Wxc/Wxt={mm['Wxc']/mm['Wxt']:.3f}, "
          f"Iyc/Iy={mm['Iyc_Iy']:.3f}, F_L/Fy={FL/fy:.3f})")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
