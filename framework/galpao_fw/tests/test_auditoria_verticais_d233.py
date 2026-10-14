# ============================================================================
# test_auditoria_verticais_d233.py - AUDITORIA DOS MOTORES CONTRA AS FONTES DO
# ACERVO, 6a parte (D233): os METODOS dos verticais fora do galpao de aco -
# pilar de concreto (flexao composta), protensao, laje macica, telhado de
# madeira, luminotecnica, estacas e o vento em telhados multiplos. Cada numero
# de referencia sai do texto da norma (NBR 6118:2014 no PDF local F016, NBR
# 7190-1:2022, NBR 8681:2025, NBR 6122:2022, NBR ISO/CIE 8995-1:2013, NBR
# 6123:2023), nao da saida anterior do motor.
# ============================================================================
"""Conferencias do D233 contra o texto das normas."""

import copy
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import estaca_profunda as ep
import laje_concreto as lc
import luminotecnica_nbr8995 as lt
import pilar_concreto as pc
import telhado_casa_madeira as tmad
import vento_nbr6123 as vi
import viga_protendida as vp


# ---- pilar de concreto (NBR 6118:2014 15.8.3.3.2 e Figura 17.1) --------------
def _pilar(le, Ma, Mc=None, tipo="balanco"):
    md = {"tipo": tipo, "Ma": Ma}
    if Mc is not None:
        md["Mc"] = Mc
    return pc.dimensiona_pilar({"b": 0.40, "h": 0.40, "Nk": 500.0, "le_x": le,
                                "le_y": le, "fck": 30e3, "fyk": 500e3,
                                "M1d_x": md})


def test_pilar_sem_segunda_ordem_dimensiona_com_M1dA_inteiro():
    """lambda <= lambda1: a extremidade leva M1d,A; alpha_b so' reduz a secao
    intermediaria. Antes o motor usava alpha_b.M1d,A (balanco: 0,9.M1d,A)."""
    r = _pilar(3.0, 150.0, 75.0)["dir"]["x"]
    assert r["alpha_b"] == pytest.approx(0.90)
    assert not r["considera_2a"]
    assert r["Md_tot"] == pytest.approx(150.0)


def test_pilar_com_segunda_ordem_nunca_abaixo_de_M1dA():
    """15.8.3.3.2: Md,tot = alpha_b.M1d,A + Nd.le2/10.1/r >= M1d,A."""
    for le in (4.0, 5.0, 6.0, 8.0):
        r = _pilar(le, 200.0, 0.0)["dir"]["x"]
        if r["considera_2a"]:
            esperado = max(r["alpha_b"] * 200.0 + r["M2d"],
                           r["M1d_min"] + r["M2d"], 200.0)
            assert r["Md_tot"] == pytest.approx(esperado, abs=0.02)
            assert r["Md_tot"] >= 200.0 - 1e-9


def test_pilar_alpha_b_unitario_abaixo_do_momento_minimo():
    """15.8.2 d): momento de 1a ordem menor que o minimo -> alpha_b = 1,0."""
    r = _pilar(6.0, 1.0, 0.0)["dir"]["x"]
    assert r["alpha_b"] == pytest.approx(1.0)


def test_pivo_C_do_dominio_5_acima_de_C50():
    """Figura 17.1: pivo C a (eps_cu - eps_c2).h/eps_cu. Em x = h a reta do
    dominio 5 tem de encontrar a do 4a (antes, em C70, 4,2 por mil > eps_cu)."""
    h, d = 0.40, 0.36
    for fck in (30e3, 50e3, 70e3, 90e3):
        ecu = pc.eps_cu(fck / 1e3)
        ec2 = pc.eps_c2(fck / 1e3)
        assert pc._eps_fibra(0.0, h * (1 + 1e-9), d, h, fck) == pytest.approx(ecu, rel=1e-6)
        zc = (ecu - ec2) * h / ecu
        assert pc._eps_fibra(zc, 3.0 * h, d, h, fck) == pytest.approx(ec2, rel=1e-9)


# ---- protensao (NBR 6118:2014 9.6.1.2 e 17.3.1) ------------------------------
def test_estiramento_pre_tracao_aco_RB():
    """9.6.1.2.1-a (2014): RB -> 0,77 fptk e 0,85 fpyk ; 9.6.1.2.2 -> 0,74 fptk
    e 0,82 fpyk ao termino da operacao."""
    fptk = 1900e3
    fpyk = 0.9 * fptk
    assert vp.SIGMA_PI_MAX == pytest.approx(min(0.77 * fptk, 0.85 * fpyk))
    assert vp.SIGMA_P0_MAX == pytest.approx(min(0.74 * fptk, 0.82 * fpyk))
    r = vp.verifica_viga_protendida({"vao": 16.0, "b": 0.30, "h": 0.80,
                                     "fck": 40e3, "q": 5.0, "n_cordoalhas": 8})
    assert "sigma_p0_ok" in r
    assert r["sigma_p0_ok"] == (r["sigma_p0_MPa"] * 1e3 <= vp.SIGMA_P0_MAX + 1e3)


def test_els_f_usa_fctk_inf():
    """17.3.1: formacao de fissuras com fctk,inf = 0,7 fctm (alfa 1,5)."""
    s = vp.verifica_servico(800.0, 0.25, 100.0, 50.0, 0.30, 0.80, 40e3)
    fctm = 0.3 * 40.0 ** (2.0 / 3.0) * 1e3
    assert s["fct_f"] == pytest.approx(1.5 * 0.7 * fctm, rel=1e-6)


def test_elu_protendida_reprova_secao_superarmada():
    """14.6.4.3: x/d <= 0,45 (fck <= 50); acima disso a cordoalha pode nao
    escoar e o Mrd simplificado nao vale."""
    r = vp.verifica_elu_flexao(Ap=20 * 1.01e-4, dp=0.35, Mg=10.0, Mq=10.0,
                               b=0.15, h=0.40, fck=30e3)
    assert r["x_d"] > 0.45 and not r["dutilidade_ok"] and not r["ok"]


# ---- laje macica (NBR 6118:2014 19.4.1 + 17.4.2.2) -------------------------
def test_biela_da_laje_pela_17422():
    c = lc.cortante_laje(10.0, 1.0, 0.09, 25e3, 3e-4)
    assert c["V_rd2"] == pytest.approx(0.27 * (1 - 25 / 250) * 25e3 / 1.4 * 1.0 * 0.09)


# ---- telhado de madeira (NBR 8681:2025 Tab.2/4/6) ---------------------------
def test_combinacoes_do_telhado_de_madeira():
    out = dict(tmad.combinacoes_desfavoraveis(1.0, 1.0, {"w": 1.0}))
    assert out["1,35G+1,5Q"] == pytest.approx(2.85)
    assert out["1,35G+1,5Q+0,84W[w]"] == pytest.approx(1.35 + 1.5 + 1.4 * 0.6)
    assert out["1,35G+1,4W[w]+1,2Q"] == pytest.approx(1.35 + 1.4 + 1.5 * 0.8)
    assert out["1,35G+1,4W[w]"] == pytest.approx(2.75)


def test_pressao_do_vento_entra_na_terca_e_na_trelica():
    """Telhado a 45 graus com cpi -0,3: a agua de barlavento fica em PRESSAO.
    Antes so' o uplift 0,9.G+1,4.W era combinado e a terca via 1,4.(g+q)."""
    import test_telhado_madeira_g71 as T
    tel = T._telhado_vento(inclinacao_graus=45.0)
    tel["vento"] = dict(tel["vento"], cpi=-0.3,
                        cpi_origem="6.2.5-b quatro faces igualmente permeaveis")
    r = tmad.rodar(tel)
    t = r["terca"]
    grav = 1.35 * t["w_g_kNm"] + 1.5 * t["w_q_kNm"]
    assert "W[pressao]" in t["comb_governante"]
    assert t["w_d_kNm"] > 1.3 * grav
    assert any("W[" in b["comb_governante"] for b in r["barras"])
    # o apoio da terca e' verificado com a reacao de CALCULO
    assert t["apoio"]["R_kN"] == pytest.approx(t["w_d_kNm"] * tel["espacamento"], rel=1e-3)


# ---- luminotecnica (NBR ISO/CIE 8995-1:2013 Tabela 5) -----------------------
def test_iluminancias_da_tabela_5():
    assert lt.iluminancia_recomendada("circulacao") == 100
    assert lt.iluminancia_recomendada("armazem_geral") == 100
    assert lt.iluminancia_recomendada("deposito") == 200        # continuamente ocupado
    assert lt.iluminancia_recomendada("usinagem_grosseira") == 300
    assert lt.iluminancia_recomendada("montagem_media") == 500
    assert lt.iluminancia_recomendada("montagem_fina") == 750
    assert lt.iluminancia_recomendada("montagem_precisao") == 1000


# ---- estacas (NBR 6122:2022 8.2.1.2) ----------------------------------------
PERFIL = [{"tipo": "argila", "N": 4, "dz": 6.0}, {"tipo": "areia", "N": 40, "dz": 6.0}]


@pytest.mark.parametrize("tipo", ["helice", "escavada"])
def test_ponta_limitada_ao_atrito(tipo):
    c = ep.capacidade_aoki_velloso(PERFIL, 0.40, 10.0, tipo, fs_global=2.0)
    assert c["ponta_limitada_8212"]
    assert c["R_ponta_kN"] > c["R_lateral_kN"]          # o caso que a regra pega
    assert c["P_adm_kN"] == pytest.approx(2.0 * c["R_lateral_kN"] / 2.0, abs=0.1)


def test_pre_moldada_sem_limite_de_ponta():
    c = ep.capacidade_aoki_velloso(PERFIL, 0.40, 10.0, "pre_moldada", fs_global=2.0)
    assert not c["ponta_limitada_8212"]
    assert c["P_adm_kN"] == pytest.approx(c["R_ult_kN"] / 2.0, abs=0.1)


# ---- vento: telhados multiplos (NBR 6123:2023 Tabela 10) --------------------
def test_tabela_10_linhas_e_tramos():
    t = vi.cpe_telhado_multiplo(4, 5.0)
    assert [(x["barlavento"], x["sotavento"]) for x in t] == [
        (-0.9, -0.6), (-0.4, -0.3), (-0.3, -0.3), (-0.3, -0.3)]
    t20 = vi.cpe_telhado_multiplo(3, 20.0)
    assert t20[0] == {"barlavento": -0.7, "sotavento": -0.6}
    assert t20[1] == {"barlavento": -0.4, "sotavento": -0.3}
    assert t20[-1] == {"barlavento": -0.3, "sotavento": -0.5}
    t45 = vi.cpe_telhado_multiplo(2, 45.0)
    assert t45[0]["barlavento"] == pytest.approx(0.3)         # pressao
    with pytest.raises(ValueError):
        vi.cpe_telhado_multiplo(2, 50.0)


def test_tabela_8_uma_agua_celulas():
    """NBR 6123:2023 Tabela 8 (imagem da p.22), colunas 90 e -90 graus, 5 a 30."""
    linhas = ((5, -1.0, -0.5, -0.5, -1.0), (10, -1.0, -0.5, -0.4, -1.0),
              (15, -0.9, -0.5, -0.3, -1.0), (20, -0.8, -0.5, -0.2, -1.0),
              (25, -0.7, -0.5, -0.1, -0.9), (30, -0.5, -0.5, 0.0, -0.6))
    for th, H90, L90, Hm90, Lm90 in linhas:
        c = vi.cpe_telhado_1agua(th)
        assert c["vento90"] == {"H": H90, "L": L90}
        assert c["vento_90"] == {"H": Hm90, "L": Lm90}
    with pytest.raises(ValueError):
        vi.cpe_telhado_1agua(35.0)


def test_tabela_10_todas_as_celulas():
    """NBR 6123:2023 Tabela 10, alfa = 0 (imagem da p.24): as 40 celulas
    (theta 5/10/20/30/45 x a*, b*, c*, d*, m*, n*, x*, z*), uma a uma."""
    imagem = {
        5:  (-0.9, -0.6, -0.4, -0.3, -0.3, -0.3, -0.3, -0.3),
        10: (-1.1, -0.6, -0.4, -0.3, -0.3, -0.3, -0.3, -0.4),
        20: (-0.7, -0.6, -0.4, -0.3, -0.3, -0.3, -0.3, -0.5),
        30: (-0.2, -0.6, -0.4, -0.3, -0.2, -0.3, -0.2, -0.5),
        45: (+0.3, -0.6, -0.6, -0.4, -0.2, -0.4, -0.2, -0.5),
    }
    for th, cel in imagem.items():
        assert vi._linha_tab10(float(th)) == pytest.approx(cel)
        t = vi.cpe_telhado_multiplo(4, float(th))
        a, b, c, d, m, n, x, z = cel
        assert [(v["barlavento"], v["sotavento"]) for v in t] == pytest.approx(
            [(a, b), (c, d), (m, n), (x, z)])


# ---- base unica conferida em cada pilar (D235) -------------------------------
def test_base_conferida_com_as_medidas_de_cada_pilar():
    """A mesma placa num pilar mais estreito tem balanco maior: confere_base
    recalcula a espessura exigida com as medidas do pilar (D235)."""
    import base_chumbador as bc
    import perfis
    base = {"fck": 25e3, "B": 0.32, "L": 0.60, "A2": 0.47 * 0.75, "n_chumbadores": 4,
            "n_tracionados": 2, "db": 0.038, "fub": 400e3, "borda": 0.06,
            "fy_placa": 250e3, "t_placa": None, "rosca_no_plano": True,
            "d_anchor": 0.54, "N": 0.0, "V": 0.0, "M": 0.0}
    esf = [("c1", 120.0, 25.0, 90.0), ("c2", -20.0, 30.0, 40.0)]
    r = {}
    for pn in ("HEB280", "HEB240"):
        p = perfis.PERFIS[pn]
        c = dict(base, d_col=p["d"], bf_col=p["bf"], beff_tracao=p["bf"])
        r[pn] = bc.confere_base(c, 0.32, 0.60, 0.038, 4, 0.06, None, esf)
        assert r[pn]["n_comb"] == 2 and r[pn]["t_placa_req"] > 0
    assert r["HEB240"]["t_placa_req"] != pytest.approx(r["HEB280"]["t_placa_req"])
    # com a espessura dada, o OK passa a exigir t_placa >= t_req
    p = perfis.PERFIS["HEB240"]
    c = dict(base, d_col=p["d"], bf_col=p["bf"], beff_tracao=p["bf"])
    fino = bc.confere_base(c, 0.32, 0.60, 0.038, 4, 0.06, 0.005, esf)
    assert not fino["OK"]
