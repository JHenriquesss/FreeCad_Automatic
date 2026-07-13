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
    """Duas vezes a distancia do centroide a face interna da mesa comprimida.
    I duplo-simetrico: hc = altura livre da alma hw = d-2tf. Secao monossimetrica:
    hc ja vem calculado em props_I_mono (sec['hc']) - usa se presente."""
    return sec.get("hc", sec["d"] - 2.0 * sec["tf"])


def ho(sec):
    """Distancia entre os centroides das mesas. I duplo-simetrico: d-tf.
    Monossimetrico: props_I_mono fornece sec['ho']."""
    return sec.get("ho", sec["d"] - sec["tf"])


def aw(sec):
    """aw = hc tw / (bfc tfc) (para rt, sem o limite de 10). bfc/tfc = mesa
    COMPRIMIDA (sec['bfc']/['tfc'] no monossim.; = bf/tf no duplo-sim)."""
    bfc = sec.get("bfc", sec["bf"]); tfc = sec.get("tfc", sec["tf"])
    return hc(sec) * sec["tw"] / (bfc * tfc)


def rt(sec):
    """Raio de giracao efetivo rt (5.4-11 / Spec. F4-10).
    ATENCAO (parecer item 45 F2): o 'h' que vai ao QUADRADO e a ALTURA LIVRE DA ALMA
    (hw = d-tfc-tft; = d-2tf no duplo-sim), NAO hc nem a altura total d. hc entra so
    no aw. O d aparece so em ho/d e /(ho*d). bf = mesa COMPRIMIDA (bfc). props_I_mono
    ja entrega rt pronto (sec['rt']) - usa se presente (evita divergencia numerica)."""
    if "rt" in sec:
        return sec["rt"]
    d = sec["d"]; bf = sec.get("bfc", sec["bf"])
    h = sec.get("hw", sec["d"] - 2.0 * sec["tf"])      # altura LIVRE da alma, NAO hc/d
    ho_ = ho(sec); aw_ = aw(sec)
    return bf / math.sqrt(12.0 * (ho_ / d + (1.0 / 6.0) * aw_ * h ** 2 / (ho_ * d)))


def e_alma_esbelta(sec, fy):
    """hc/tw > 5.70 sqrt(E/Fy) (para o ramo J=0 do DG25)."""
    return hc(sec) / sec["tw"] > 5.70 * math.sqrt(E / fy)


def J_dg(sec, fy):
    """Constante de torcao J do DG25 (5.4-12). Se a alma e esbelta OU Iyc/Iy<=0.23,
    J=0; senao, forma completa com o desconto (1-0.63 t/b) por mesa. I duplo-sim:
    Iyc/Iy = 0.5 -> so a alma esbelta zera J. Monossimetrico: usa as duas mesas
    (bfc/tfc, bft/tft) e Iyc/Iy real de props_I_mono, e a altura livre hw (NAO hc)."""
    tw = sec["tw"]
    Iyc_sobre_Iy = sec.get("Iyc_Iy", 0.5)
    if e_alma_esbelta(sec, fy) or Iyc_sobre_Iy <= 0.23:
        return 0.0
    bfc = sec.get("bfc", sec["bf"]); tfc = sec.get("tfc", sec["tf"])
    bft = sec.get("bft", sec["bf"]); tft = sec.get("tft", sec["tf"])
    hw = sec.get("hw", sec["d"] - 2.0 * sec["tf"])    # altura livre da alma (NAO hc)
    termo_c = bfc * tfc ** 3 / 3.0 * (1.0 - 0.63 * tfc / bfc)
    termo_t = bft * tft ** 3 / 3.0 * (1.0 - 0.63 * tft / bft)
    return hw * tw ** 3 / 3.0 + termo_c + termo_t


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


# ============================================================================
# DG25 FULL (fase 6.14) - momento nominal de FLT completo (nao so o Mcr elastico).
# Base verbatim DG25 pgs 58-62 (imagens das paginas):
#   §5.4.1 Cb (5.4-1/5.4-2), §5.4.2 CFY (5.4-8/9), §5.4.3 LTB (5.4-13..5.4-21),
#   Rpc (5.4-4/5), Rpg (5.4-6/7), F_L (5.4-14/15).
# CHAVE ALGEBRICA: gamma_eLTB = F_eLTB/f_r (5.4-13), logo gamma_eLTB * f_r = F_eLTB.
# O f_r (tensao de compressao no ponto) CANCELA nas eqs 5.4-16..18: o Mn nominal
# depende so de F_eLTB, F_L, Fy, Rpc, Rpg. Por isso o Cb (dentro de F_eLTB) NAO
# cancela na razao do cross-check de CAPACIDADE (entra nao-linearmente pelas 3
# regioes) - ao contrario do cross-check ELASTICO (cross_check_flt), onde cancela.
# ============================================================================
LAM_LTB = math.pi ** 2 / 1.1 ** 2                     # = 8.16 ~ 8.2 (limite (a))


def myc(sec, fy):
    """M_yc = Fy Sxc (5.4-4 'where'). Sxc = Wx (I duplo-sim)."""
    return fy * sec["Wx"]


def mp_dg(sec, fy):
    """M_p = Fy Zx <= 1,6 Fy Sxc (5.4-9 / 'where' de 5.4-4)."""
    return min(fy * sec["Zx"], 1.6 * fy * sec["Wx"])


def _lam_pw(fy):
    """lambda_pw = 3,76 sqrt(E/Fy) (Spec Tab. B4.1, secao duplo-simetrica)."""
    return 3.76 * math.sqrt(E / fy)


def _lam_rw(fy):
    """lambda_rw = 5,70 sqrt(E/Fy) (Spec Tab. B4.1)."""
    return 5.70 * math.sqrt(E / fy)


def rpc(sec, fy):
    """Fator de plastificacao da alma - compressao (5.4-4/5.4-5, Spec F4-9a/b).
    I duplo-sim: Iyc/Iy=0.5 (>0.23). lambda = hc/tw."""
    lam = hc(sec) / sec["tw"]
    lpw = _lam_pw(fy); lrw = _lam_rw(fy)
    mp_myc = mp_dg(sec, fy) / myc(sec, fy)
    if lam <= lpw:
        return mp_myc                                    # 5.4-4
    if lam < lrw:
        return min(mp_myc - (mp_myc - 1.0) * (lam - lpw) / (lrw - lpw), mp_myc)  # 5.4-5
    return 1.0                                           # hc/tw >= lrw (ou Iyc/Iy<=0.23)


def rpg(sec, fy):
    """Fator de flambagem por flexao da alma - bend buckling (5.4-6/5.4-7, Spec F5-6).
    aw limitado a 10 (5.4-7). Rpg=1 se alma nao esbelta."""
    lam = hc(sec) / sec["tw"]; lrw = _lam_rw(fy)
    if lam <= lrw:
        return 1.0
    aw_ = min(aw(sec), 10.0)
    val = 1.0 - aw_ / (1200.0 + 300.0 * aw_) * (lam - 5.70 * math.sqrt(E / fy))
    return min(val, 1.0)


def f_L(sec, fy):
    """Tensao F_L (5.4-14/5.4-15). I duplo-sim: Sxt/Sxc = 1 >= 0,7 -> F_L = 0,7 Fy.
    Caso geral (monossimetrico) tratado para robustez."""
    Sxt = sec.get("Wxt", sec["Wx"]); Sxc = sec["Wx"]
    if Sxt / Sxc >= 0.7:
        return 0.7 * fy                                  # 5.4-14
    return max(fy * Sxt / Sxc, 0.5 * fy)                 # 5.4-15


def m_cfy(sec, fy):
    """§5.4.2 - momento nominal por escoamento da mesa comprimida (5.4-8):
    Mn = Rpc Rpg Myc = Rpc Rpg Fy Sxc. Teto superior do estado de FLT."""
    return rpc(sec, fy) * rpg(sec, fy) * myc(sec, fy)


def mn_ltb_dg(sec, fy, Lb, Cb=1.0):
    """§5.4.3 - momento nominal de FLT do DG25 (metodo geral completo), 3 regioes.
    Usa F_eLTB (que contem Cb); f_r cancela (gamma*f_r=F_eLTB). Retorna dict com Mn
    nominal (kN.m), regiao (a/b/c), Rpc, Rpg, F_L, F_eLTB, razao F_eLTB/Fy."""
    Feltb = f_eltb(sec, fy, Lb, Cb)
    Rpc = rpc(sec, fy); Rpg = rpg(sec, fy); FL = f_L(sec, fy)
    Sxc = sec["Wx"]; Mcfy = Rpc * Rpg * myc(sec, fy)
    ratio = Feltb / fy                                   # = gamma_eLTB*f_r/Fy
    esbelta = e_alma_esbelta(sec, fy)
    if ratio >= LAM_LTB:                                 # (a) FLT nao se aplica
        Mn, reg = Mcfy, "a"
    elif Feltb > FL:                                     # (b) inelastica (5.4-16)
        num = math.pi * math.sqrt(fy / Feltb) - 1.1
        den = math.pi * math.sqrt(fy / FL) - 1.1
        Mn = Rpg * Rpc * myc(sec, fy) * \
            (1.0 - (1.0 - FL / (Rpc * fy)) * (num / den))
        Mn = min(Mn, Mcfy); reg = "b"
    else:                                                # (c) elastica (5.4-17/18)
        Mn = (Rpg * Feltb * Sxc) if esbelta else (Feltb * Sxc)
        Mn = min(Mn, Mcfy); reg = "c"
    return {"Mn": Mn, "M_cfy": Mcfy, "regiao": reg, "Rpc": Rpc, "Rpg": Rpg,
            "F_L": FL, "F_eLTB": Feltb, "ratio_FeFy": ratio, "esbelta": esbelta}


# ============================================================================
# ENVELOPE DE ESTADOS-LIMITE DE FLEXAO (fase 6.16) - DG25 §5.4.4/5/6/7
# (verbatim DG25 pgs 62-64, imagens). Momento nominal = MENOR entre:
#   CFY  §5.4.2  escoamento da mesa comprimida (m_cfy = Rpc Rpg Myc) - teto
#   LTB  §5.4.3  flambagem lateral com torcao (mn_ltb_dg)
#   FLB  §5.4.4  flambagem local da mesa comprimida (3 regioes, 5.4-14..24)
#   TFY  §5.4.5  escoamento da mesa tracionada (so se Sxt<Sxc; 5.4-25..29)
#   TFR  §5.4.6  ruptura da mesa tracionada com furos (5.4-30; F13.1)
# lambda_pf=0,38 sqrt(E/Fy); lambda_rf=0,95 sqrt(kc E/FL); kc=4/sqrt(hc/tw) em
# [0,35;0,76] (5.4-24). Rpt (fator de plastificacao p/ tracao) espelha Rpc mas
# em Myt=Fy Sxt. INFORMATIVO/verificacao - nao dimensiona (dimensionamento = NBR).
# ============================================================================
def _lam_pf(fy):
    """lambda_pf = 0,38 sqrt(E/Fy) (mesa compacta, Spec Tab. B4.1b)."""
    return 0.38 * math.sqrt(E / fy)


def kc_flb(sec):
    """kc = 4/sqrt(hc/tw), limitado a [0,35 ; 0,76] (5.4-24)."""
    return min(max(4.0 / math.sqrt(hc(sec) / sec["tw"]), 0.35), 0.76)


def _lam_rf(sec, fy):
    """lambda_rf = 0,95 sqrt(kc E/FL) (mesa nao-compacta, 5.4-22 denom)."""
    return 0.95 * math.sqrt(kc_flb(sec) * E / f_L(sec, fy))


def mn_flb(sec, fy):
    """§5.4.4 - flambagem local da mesa comprimida (FLB), 3 regioes por
    lambda=bfc/(2 tfc). (a) compacta: nao aplica -> retorna o teto CFY. (b) nao-
    compacta: interpola 5.4-22. (c) esbelta: 5.4-23. Retorna {Mn, regiao, aplica}."""
    bf = sec.get("bfc", sec["bf"]); tf = sec.get("tfc", sec["tf"])
    lam = bf / (2.0 * tf)
    lpf = _lam_pf(fy); lrf = _lam_rf(sec, fy)
    Rpc = rpc(sec, fy); Rpg = rpg(sec, fy); FL = f_L(sec, fy)
    Sxc = sec["Wx"]; Myc = myc(sec, fy); Mcfy = Rpc * Rpg * Myc
    if lam <= lpf:                                       # (a) compacta: FLB nao aplica
        return {"Mn": Mcfy, "regiao": "a", "aplica": False}
    if lam < lrf:                                        # (b) nao-compacta (5.4-22)
        Mn = Rpg * (Rpc * Myc - (Rpc * Myc - FL * Sxc) * (lam - lpf) / (lrf - lpf))
        return {"Mn": min(Mn, Mcfy), "regiao": "b", "aplica": True}
    kc = kc_flb(sec)                                     # (c) esbelta (5.4-23)
    Mn = Rpg * 0.9 * E * kc * Sxc / lam ** 2
    return {"Mn": min(Mn, Mcfy), "regiao": "c", "aplica": True}


def rpt(sec, fy):
    """Fator de plastificacao da alma p/ mesa TRACIONADA (5.4-26/27/28). Espelha
    Rpc mas referido a Myt=Fy Sxt. Iyc/Iy<=0,23 OU alma esbelta -> Rpt=1,0."""
    lam = hc(sec) / sec["tw"]; lpw = _lam_pw(fy); lrw = _lam_rw(fy)
    Iyc_Iy = sec.get("Iyc_Iy", 0.5)
    Sxt = sec.get("Wxt", sec["Wx"])
    Mp = min(fy * sec["Zx"], 1.6 * fy * Sxt)             # 5.4-28
    Myt = fy * Sxt                                       # 5.4-29
    mp_myt = Mp / Myt
    if lam > lrw or Iyc_Iy <= 0.23:
        return 1.0                                       # 5.4-28 (clausula)
    if lam <= lpw:
        return mp_myt                                    # 5.4-26
    return min(mp_myt - (mp_myt - 1.0) * (lam - lpw) / (lrw - lpw), mp_myt)  # 5.4-27


def mn_tfy(sec, fy):
    """§5.4.5 - escoamento da mesa tracionada (TFY). So aplica se Sxt<Sxc (mesa
    tracionada menor). Mn = Rpt Fy Sxt (5.4-25). Retorna {Mn, aplica, Rpt}."""
    Sxt = sec.get("Wxt", sec["Wx"]); Sxc = sec["Wx"]
    if Sxt >= Sxc:
        return {"Mn": None, "aplica": False}
    Rpt = rpt(sec, fy)
    return {"Mn": Rpt * fy * Sxt, "Rpt": Rpt, "aplica": True}


def mn_tfr(sec, fy, fu, n_furos=0, dh=0.0):
    """§5.4.6 - ruptura da mesa tracionada com furos (5.4-30, Spec F13.1). So com
    furos (n_furos>0, dh>0). Yt=1,0 se Fy/Fu<=0,8 senao 1,1. Nao aplica se
    Fu Afn >= Yt Fy Afg. Mn=(Fu Afn/Afg) Sxt. dh em m (furo bruto)."""
    Sxt = sec.get("Wxt", sec["Wx"])
    bft = sec.get("bft", sec["bf"]); tft = sec.get("tft", sec["tf"])
    if n_furos <= 0 or dh <= 0:
        return {"Mn": None, "aplica": False}
    Afg = bft * tft; Afn = Afg - n_furos * dh * tft
    Yt = 1.0 if fy / fu <= 0.8 else 1.1
    if fu * Afn >= Yt * fy * Afg:
        return {"Mn": None, "aplica": False, "Yt": Yt}
    return {"Mn": (fu * Afn / Afg) * Sxt, "aplica": True, "Yt": Yt,
            "Afn": Afn, "Afg": Afg}


def mn_envelope(sec, fy, Lb, Cb=1.0, fu=None, n_furos=0, dh=0.0):
    """§5.4.7 - momento nominal de flexao = MENOR entre CFY/LTB/FLB/TFY/TFR.
    Retorna {Mn, governa, estados{}, ltb_regiao, flb_regiao}. INFORMATIVO."""
    cfy = m_cfy(sec, fy)
    ltb = mn_ltb_dg(sec, fy, Lb, Cb)
    flb = mn_flb(sec, fy)
    tfy = mn_tfy(sec, fy)
    tfr = mn_tfr(sec, fy, fu, n_furos, dh) if fu else {"Mn": None, "aplica": False}
    estados = {"CFY": cfy, "LTB": ltb["Mn"], "FLB": flb["Mn"]}
    if tfy["aplica"]:
        estados["TFY"] = tfy["Mn"]
    if tfr["aplica"]:
        estados["TFR"] = tfr["Mn"]
    gov = min(estados, key=lambda k: estados[k])
    return {"Mn": estados[gov], "governa": gov, "estados": estados,
            "ltb_regiao": ltb["regiao"], "flb_regiao": flb["regiao"]}


def cb_tapered(f0, fmid, f2):
    """Cb do DG25 por TENSOES na mesa (5.4-1/5.4-2), metodo Yura-Helwig/AASHTO.
    f2 = |maior tensao de compressao| numa extremidade (compressao +, tracao -);
    fmid = tensao na mesa no meio do Lb; f0 = tensao na extremidade oposta a f2.
    Se fmid/f2>=1 ou f2==0 -> Cb=1. Senao Cb=1,75-1,05(f1/f2)+0,3(f1/f2)^2 <=2,3,
    com f1 por 5.4-2: se |fmid|<|(f0+f2)/2| -> f1=f0 ; senao f1=2 fmid-f2 (>=f0).
    PREMISSA DO CHAMADOR (parecer item 44, pt 2): os sinais das tensoes sao
    RESPONSABILIDADE de quem chama - o metodo Yura-Helwig e sensivel a sinal
    (compressao +, tracao -). f2 deve ser o MODULO da MAIOR compressao numa
    extremidade; se a fibra critica reverte para tracao nas outras estacoes, f0/fmid
    devem vir NEGATIVOS. Um erro de sinal aqui inverte a parabola do limite de Cb."""
    if f2 == 0 or (fmid / f2) >= 1.0:
        return 1.0
    if abs(fmid) < abs((f0 + f2) / 2.0):
        f1 = f0                                          # 5.4-2 (topo)
    else:
        f1 = max(2.0 * fmid - f2, f0)                    # 5.4-2 (base)
    r = f1 / f2
    return min(1.75 - 1.05 * r + 0.3 * r ** 2, 2.3)


def cross_check_capacidade(segs, fy, Lb, Cb=1.0, tol=0.20):
    """Cross-check de CAPACIDADE (fase 6.14): Mn nominal de FLT do DG25 completo
    (secao do MEIO, Rpc/Rpg/3 regioes) vs Mn nominal do NBR 8800 Anexo G/J (secao
    de MAIOR altura, momento_resistente). Diferente do cross_check_flt (elastico),
    aqui o Cb NAO cancela (entra nao-linearmente). INFORMATIVO - nao dimensiona."""
    import check_nbr8800 as ck
    valid = [s for s in segs if s.get("props")]
    if not valid:
        return {"Mn_dg": 0.0, "Mn_nbr": 0.0, "razao": float("nan"),
                "converge": False, "tol": tol, "sec_meio": None, "sec_funda": None,
                "regiao_dg": None}
    sec_meio = valid[len(valid) // 2]
    sec_funda = max(valid, key=lambda s: s["h_m"])
    dg = mn_ltb_dg(sec_meio["props"], fy, Lb, Cb)
    Mn_nbr = ck.momento_resistente(sec_funda["props"], fy, Lb, Cb)[0]
    razao = dg["Mn"] / Mn_nbr if Mn_nbr > 0 else float("inf")
    return {"Mn_dg": dg["Mn"], "Mn_nbr": Mn_nbr, "razao": razao,
            "converge": abs(razao - 1.0) <= tol, "tol": tol,
            "regiao_dg": dg["regiao"], "Rpc": dg["Rpc"], "Rpg": dg["Rpg"],
            "sec_meio": round(sec_meio["h_m"] * 1000, 1),
            "sec_funda": round(sec_funda["h_m"] * 1000, 1)}


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
    # --- DG25 FULL (fase 6.14) ---
    sc = av.props_I(0.60, 0.25, 0.008, 0.016)            # alma compacta
    assert rpc(sc, 250e3) >= 1.0                          # compacta: Rpc = Mp/Myc >1
    assert abs(rpg(sc, 250e3) - 1.0) < 1e-12             # nao esbelta: Rpg=1
    assert abs(f_L(sc, 250e3) - 0.7 * 250e3) < 1e-6      # duplo-sim: F_L=0.7Fy
    ss = av.props_I(0.95, 0.25, 0.004, 0.016)            # alma esbelta
    assert rpg(ss, 250e3) < 1.0 and abs(rpc(ss, 250e3) - 1.0) < 1e-12
    mn = mn_ltb_dg(sc, 250e3, 4.0, Cb=1.0)
    assert mn["Mn"] > 0 and mn["regiao"] in ("a", "b", "c")
    assert mn["Mn"] <= mn["M_cfy"] + 1e-6                # teto CFY
    # Cb NAO cancela no cross-check de capacidade (entra nao-linear)
    segt = [{"props": av.props_I(0.90 - 0.45 * i / 7, 0.22, 0.006, 0.014),
             "h_m": 0.90 - 0.45 * i / 7} for i in range(8)]
    c1 = cross_check_capacidade(segt, 250e3, 4.0, Cb=1.0)["razao"]
    c2 = cross_check_capacidade(segt, 250e3, 4.0, Cb=1.6)["razao"]
    assert abs(c1 - c2) > 1e-6, "Cb deve alterar a razao no cross-check de capacidade"
    # cb_tapered: gradiente uniforme -> ~1; f2=0 -> 1
    assert cb_tapered(f0=100.0, fmid=100.0, f2=100.0) == 1.0
    assert cb_tapered(f0=0.0, fmid=0.0, f2=0.0) == 1.0
    assert 1.0 <= cb_tapered(f0=-40.0, fmid=60.0, f2=100.0) <= 2.3
    print("dg25_ltb self-test PASSED "
          f"(prismatico razao DG25/NBR = {r['razao']:.3f}, CONVERGE ; "
          f"full Mn regiao {mn['regiao']}, Rpc={mn['Rpc']:.3f})")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
