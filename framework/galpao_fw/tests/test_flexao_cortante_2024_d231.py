# ============================================================================
# test_flexao_cortante_2024_d231.py - FLEXAO E CORTANTE DO PERFIL PELA
# NBR 8800:2024 (auditoria contra o acervo, D231). O que mudou do motor:
#   - FLT (Anexo D, D.2.1 e D.2.8-a): Cb entra em lambda_r e em Mcr; a reta do
#     trecho inelastico nao leva Cb. O motor multiplicava a reta por Cb (edicao
#     de 2008) e dava ate' 22 % a mais de momento resistente com Cb > 1.
#   - teto de 5.4.2.2: M_Rd <= 1,50.W.fy/ga1.
#   - cortante (5.4.3.1.1): kv = 5,34 para alma sem enrijecedor (era 5,0).
# As referencias sao contas refeitas aqui por outro caminho (bissecao, formula
# escrita de novo), nao a saida anterior do motor.
# ============================================================================
"""Flexao e cortante de perfil I/H pela NBR 8800:2024 (Anexo D e 5.4.3)."""

import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import check_nbr8800 as ck
import perfis

FY = 345e3


def _mcr(sec, Lb, Cb):
    """D.2.8-a, escrita na forma da norma: Cb.pi2.E.Iy/Lb2 . raiz(Cw/Iy.(1 + 0,039.J.Lb2/Cw))."""
    Cw, J = ck._cw_j(sec)
    return (Cb * math.pi ** 2 * ck.E * sec["Iy"] / Lb ** 2
            * math.sqrt(Cw / sec["Iy"] * (1.0 + 0.039 * J * Lb ** 2 / Cw)))


def _lr_por_bissecao(sec, fy, Cb):
    """lambda_r e' onde a flambagem elastica alcanca Mr: Mcr(Lr) = (fy - 0,3 fy).W."""
    mr = 0.7 * fy * sec["Wx"]
    a, b = 0.1, 200.0
    for _ in range(200):
        m = 0.5 * (a + b)
        if _mcr(sec, m, Cb) > mr:
            a = m
        else:
            b = m
    return 0.5 * (a + b)


@pytest.mark.parametrize("nome", ["IPE300", "IPE450", "HEB280"])
@pytest.mark.parametrize("Cb", [1.0, 1.3, 1.75, 2.3])
def test_lambda_r_da_flt_leva_cb_e_fecha_com_mcr(nome, Cb):
    sec = perfis.PERFIS[nome]
    _mn, _gov, det = ck.momento_resistente(sec, FY, Lb=3.0, Cb=Cb)
    assert det["Lr_flt"] == pytest.approx(_lr_por_bissecao(sec, FY, Cb), rel=2e-3)
    # logo acima de Lr o momento e' o elastico, e ele vale Mr em Lr (continuidade)
    Lr = det["Lr_flt"]
    mr = 0.7 * FY * sec["Wx"]
    abaixo = ck.momento_resistente(sec, FY, Lb=Lr * 0.999, Cb=Cb)[2]["Mn_flt"]
    acima = ck.momento_resistente(sec, FY, Lb=Lr * 1.001, Cb=Cb)[2]["Mn_flt"]
    assert abaixo == pytest.approx(mr, rel=5e-3) and acima == pytest.approx(mr, rel=5e-3)


@pytest.mark.parametrize("Cb", [1.0, 1.75, 2.3])
def test_trecho_inelastico_e_a_reta_entre_mpl_e_mr_sem_cb(Cb):
    sec = perfis.PERFIS["IPE450"]
    det0 = ck.momento_resistente(sec, FY, Lb=1.0, Cb=Cb)[2]
    Lp, Lr = det0["Lp"], det0["Lr_flt"]
    mpl, mr = sec["Zx"] * FY, 0.7 * FY * sec["Wx"]
    for fracao in (0.25, 0.5, 0.75):
        Lb = Lp + fracao * (Lr - Lp)
        mn = ck.momento_resistente(sec, FY, Lb=Lb, Cb=Cb)[2]["Mn_flt"]
        assert mn == pytest.approx(mpl - (mpl - mr) * fracao, rel=1e-9)


def test_cb_maior_que_um_sobe_o_momento_mas_nao_devolve_o_plastico():
    """O defeito: com Cb = 1,75 o motor devolvia Mpl inteiro no trecho inelastico."""
    sec = perfis.PERFIS["IPE450"]
    mpl = sec["Zx"] * FY
    m1 = ck.momento_resistente(sec, FY, Lb=5.0, Cb=1.0)[0]
    m175 = ck.momento_resistente(sec, FY, Lb=5.0, Cb=1.75)[0]
    assert m1 < m175 < 0.85 * mpl
    # a forma da edicao de 2008 (reta com lambda_r de Cb = 1, vezes Cb, ate' Mpl)
    det1 = ck.momento_resistente(sec, FY, Lb=5.0, Cb=1.0)[2]
    assert min(1.75 * det1["Mn_flt"], mpl) == pytest.approx(mpl)
    assert m175 < 0.80 * min(1.75 * det1["Mn_flt"], mpl)


def test_com_cb_igual_a_um_nada_muda():
    """Referencia a mao, IPE450 a 345 MPa: Lp = 1,76.ry.raiz(E/fy)."""
    sec = perfis.PERFIS["IPE450"]
    mn, gov, det = ck.momento_resistente(sec, FY, Lb=1.0, Cb=1.0)
    assert det["Lp"] == pytest.approx(1.76 * sec["ry"] * math.sqrt(ck.E / FY), rel=1e-12)
    assert mn == pytest.approx(sec["Zx"] * FY) and det["anexo"] == "D"
    assert gov in ("FLT", "FLM", "FLA")


def test_teto_de_150_w_fy():
    """5.4.2.2: secao com Zx > 1,5.Wx (nao e' o caso de I laminado) para no teto."""
    sec = dict(perfis.PERFIS["IPE300"])
    sec["Zx"] = 1.8 * sec["Wx"]
    mn, gov, det = ck.momento_resistente(sec, FY, Lb=0.5, Cb=1.0)
    assert gov == "5.4.2.2" and mn == pytest.approx(1.5 * sec["Wx"] * FY)
    assert det["Mn_teto"] == pytest.approx(mn)
    # I laminado de catalogo fica abaixo do teto
    for nome in ("IPE300", "IPE500", "HEB280"):
        s = perfis.PERFIS[nome]
        assert s["Zx"] < 1.5 * s["Wx"]


def _vrd_a_mao(sec, fy, kv):
    h = sec["d"] - 2 * sec["tf"]
    lam = h / sec["tw"]
    lp, lr = 1.10 * math.sqrt(kv * ck.E / fy), 1.37 * math.sqrt(kv * ck.E / fy)
    vpl = 0.60 * sec["d"] * sec["tw"] * fy
    if lam <= lp:
        return vpl / 1.10
    if lam <= lr:
        return (lp / lam) * vpl / 1.10
    return 1.24 * (lp / lam) ** 2 * vpl / 1.10


def test_cortante_usa_kv_534_nos_tres_dominios():
    import alma_variavel as av
    assert ck.KV_SEM_ENRIJECEDOR == 5.34
    # almas de 6 mm com h/tw crescente: plastificacao, inelastica e elastica
    dominios = set()
    for d in (0.30, 0.42, 0.44, 0.60, 0.90):
        sec = av.props_I(d, 0.20, 0.006, 0.0125)
        lam = (sec["d"] - 2 * sec["tf"]) / sec["tw"]
        lp, lr = 1.10 * math.sqrt(5.34 * ck.E / FY), 1.37 * math.sqrt(5.34 * ck.E / FY)
        dominios.add("p" if lam <= lp else "i" if lam <= lr else "e")
        r = ck.verifica(sec, FY, 4.0, 10.0, 10.0, 10.0, Lb=1.0)
        assert r["Vrd"] == pytest.approx(_vrd_a_mao(sec, FY, 5.34), rel=1e-9)
        assert r["alma_compacta_cisalhamento"] is (lam <= lp)
    assert dominios == {"p", "i", "e"}


def test_alma_entre_o_limite_de_2008_e_o_de_2024_plastifica():
    """h/tw entre 1,10.raiz(5,0 E/fy) e 1,10.raiz(5,34 E/fy): com kv = 5,0 o motor
    reduzia o cortante; pela edicao de 2024 a alma plastifica."""
    import alma_variavel as av
    lp_2008 = 1.10 * math.sqrt(5.0 * ck.E / FY)
    lp_2024 = 1.10 * math.sqrt(5.34 * ck.E / FY)
    tw = 0.006
    h = 0.5 * (lp_2008 + lp_2024) * tw
    sec = av.props_I(h + 2 * 0.0125, 0.20, tw, 0.0125)
    lam = (sec["d"] - 2 * sec["tf"]) / sec["tw"]
    assert lp_2008 < lam < lp_2024
    r = ck.verifica(sec, FY, 4.0, 10.0, 10.0, 10.0, Lb=1.0)
    assert r["Vrd"] == pytest.approx(0.60 * sec["d"] * tw * FY / 1.10, rel=1e-9)
    assert r["Vrd"] > _vrd_a_mao(sec, FY, 5.0)


def test_perfil_u_da_terca_segue_a_mesma_flt():
    import secundarios_nbr8800 as S
    sec = next(s for s in vars(S).values()
               if isinstance(s, dict) and {"Cw", "J", "Zx", "Wx", "bf"} <= set(s))
    mpl = sec["Zx"] * FY
    m1, _g, d1 = S._mrd_eixo_forte_U(sec, FY, d1_lb := 2.5, Cb=1.0)
    m2, _g, d2 = S._mrd_eixo_forte_U(sec, FY, d1_lb, Cb=1.75)
    assert d2["Lr"] > d1["Lr"]                       # Cb alarga o trecho inelastico
    assert d1["Mn_flt"] <= d2["Mn_flt"] <= mpl
    if d1["Lp"] < d1_lb < d2["Lr"]:                  # no trecho inelastico de Cb = 1,75
        mr = 0.7 * FY * sec["Wx"]
        esperado = mpl - (mpl - mr) * (d1_lb - d1["Lp"]) / (d2["Lr"] - d1["Lp"])
        assert d2["Mn_flt"] == pytest.approx(esperado, rel=1e-9)


def test_relatorio_cita_a_edicao_de_2024():
    sec = perfis.PERFIS["IPE450"]
    r = ck.verifica(sec, FY, 6.0, 50.0, 100.0, 40.0, Lb=2.0, nome="Viga")
    txt = ck.relatorio_pt([r], FY)
    assert "NBR 8800:2024" in txt and "Anexo D" in txt and "5.4.3" in txt
    assert "2008" not in txt and "Anexo G" not in txt
