# ============================================================================
# test_auditoria_acervo_d232.py - AUDITORIA DOS MOTORES CONTRA AS FONTES DO
# ACERVO, 5a parte (D232): tesoura, ligacoes parafusadas, base de pilar,
# tercas de chapa dobrada e aco em incendio. Cada referencia e' refeita aqui
# pelo texto da norma (NBR 8800:2024, NBR 14762:2010, NBR 14323:2013), nao pela
# saida anterior do motor.
# ============================================================================
"""Conferencias do D232 contra o texto das normas lido no MCP_Fontes."""

import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import base_chumbador as bc
import check_nbr8800 as ck
import fogo_nbr14323 as fogo
import ligacoes as lg
import tercas_nbr14762 as tc
import tesoura as tes


# ---- tesoura -----------------------------------------------------------------
def test_tesoura_compressao_desconta_flambagem_local():
    """Chapa esbelta: a area efetiva de 5.3.4 reduz Nc,Rd. Antes o fator Q de
    2008 recebia a tupla, falhava e o `except` devolvia Q = 1."""
    esbelta = (0.30, 0.20, 0.004, 0.006)            # mesa b/t = 16,7 ; alma h/t = 72
    A, rx, ry = tes._props_I(esbelta)
    lam_x = 2.6 / rx / math.pi * math.sqrt(250e3 / ck.E)
    lam_y = 2.6 / ry / math.pi * math.sqrt(250e3 / ck.E)
    sem_local = min(ck.chi_compressao(lam_x), ck.chi_compressao(lam_y)) * A * 250e3 / 1.10
    assert tes._nc_rd(esbelta, 250e3, 2.6, 2.6) < 0.95 * sem_local
    compacta = (0.20, 0.10, 0.006, 0.008)
    assert tes._nc_rd(compacta, 250e3, 2.6, 2.6) == pytest.approx(
        ck.compressao(tes._sec_dict(compacta), 250e3, 2.6, 2.6)["Nc_Rd"])


def test_tesoura_gravidade_e_125G_mais_150Q():
    perfil = (0.20, 0.10, 0.006, 0.008)
    base = {"L": 20.0, "h": 2.5, "n_paineis": 8, "tipo": "warren", "fy": 250e3,
            "fu": 400e3, "perfil_banzo": perfil, "perfil_diagonal": perfil,
            "w_vento_kN_m": 0.0}
    r = tes.verifica_tesoura(dict(base, w_grav_kN_m=3.0, w_dead_kN_m=1.0))
    # mesma trelica com carga unica igual a 1,25.G + 1,50.Q = 1,25 + 3,0 = 4,25
    r_ref = tes.verifica_tesoura(dict(base, w_grav_kN_m=4.25 / 1.5))
    assert r["N_banzo_sup_max"] == pytest.approx(r_ref["N_banzo_sup_max"], rel=1e-9)
    assert r["esbeltez_compressao_max"] > 0 and r["esbeltez_tracao_max"] > 0


# ---- ligacoes parafusadas -------------------------------------------------------
def test_parafuso_corte_045_e_056():
    Ab = math.pi * 0.020 ** 2 / 4
    assert lg.fv_rd(0.020, 825e3) == pytest.approx(0.45 * Ab * 825e3 / 1.35)
    assert lg.fv_rd(0.020, 825e3, rosca_no_plano=False) == pytest.approx(0.56 * Ab * 825e3 / 1.35)


@pytest.mark.parametrize("db, furo, borda", [(16, 18, 22), (20, 22, 26), (22, 24, 28),
                                             (24, 27, 30), (27, 30, 34), (30, 33, 38),
                                             (36, 39, 45)])
def test_furo_padrao_e_borda_minima_tabelas_14_e_16(db, furo, borda):
    assert lg._diam_furo(db / 1000.0) * 1000 == pytest.approx(furo)
    assert lg.dist_min_borda(db / 1000.0) * 1000 == pytest.approx(borda)


def test_area_liquida_soma_2_mm_ao_furo():
    assert lg.largura_furo_area_liquida(0.020) == pytest.approx(0.024)
    assert lg.largura_furo_area_liquida(0.020, broca=True) == pytest.approx(0.022)


# ---- base de pilar ------------------------------------------------------------
def test_base_pressao_no_concreto_6_6_5():
    assert bc.sigma_c_rd(25e3, 1.0, 1.0) == pytest.approx(0.85 * 25e3 / 1.4)
    assert bc.sigma_c_rd(25e3, 1.0, 9.0) == pytest.approx(1.7 * 25e3 / 1.4)


def test_base_tracionada_casos_T1_T2_T3():
    L, B, sig, d_anchor = 0.40, 0.30, 15000.0, 0.35         # a = 0,15
    T, Y, _s, m = bc.placa_sob_NM(-120.0, 0.0, B, L, sig, d_anchor)
    assert T == pytest.approx(60.0) and "T1" in m
    T, Y, _s, m = bc.placa_sob_NM(-120.0, 9.0, B, L, sig, d_anchor)
    assert T == pytest.approx(60.0 + 9.0 / 0.30) and Y == 0.0 and "T2" in m
    T, Y, _s, m = bc.placa_sob_NM(-120.0, 40.0, B, L, sig, d_anchor)
    # 6.7.2.2 f): lc = (lx/2 + a) - raiz[(lx/2 + a)2 - 2.N.(e - a)/(sigma.ly)]
    e = 40.0 / 120.0
    D = 0.20 + 0.15
    lc = D - math.sqrt(D ** 2 - 2 * 120.0 * (e - 0.15) / (sig * B))
    assert "T3" in m and Y == pytest.approx(lc) and T == pytest.approx(sig * lc * B + 120.0)


def test_base_cortante_no_chumbador_6_7_2_5():
    Fv, Ft, db, tp, ta = 40.0, 20.0, 0.025, 0.025, 0.008
    alfa = 1.45 * (tp + 0.5 * ta) / db * (400e3 / 250e3) * (1.10 / 1.35)
    v = (math.sqrt((1 + alfa ** 2) * Fv ** 2 - (0.533 * Ft) ** 2) - alfa * 0.533 * Ft) / (1 + alfa ** 2)
    got, a = bc.vrd_chumbador_arruela(Fv, Ft, db, tp, ta, 400e3, 250e3, 1e9)
    assert a == pytest.approx(alfa) and got == pytest.approx(v)
    assert got < 0.5 * Fv                                  # bem abaixo de 6.3.3.2
    # teto 5.db2.sigma_c,Rd
    assert bc.vrd_chumbador_arruela(Fv, 0.0, db, 0.001, 0.0, 400e3, 250e3, 100.0)[0] == \
        pytest.approx(5 * db ** 2 * 100.0)


def test_base_tabela_18_e_escada_da_norma():
    assert bc.tabela18(0.025)["a1"] == 50 and bc.tabela18(0.025)["h1"] == 465
    assert bc.tabela18(0.020)["db"] == 22 and bc.tabela18(0.060) is None
    for ly, lx, db, nb, a1 in bc.escada_norma(0.280, 0.280):
        assert lx == pytest.approx(0.280 + 4 * a1)
        assert ly >= 0.280 + 0.025 - 1e-9


def test_base_passa_em_todas_as_combinacoes_e_exige_a_placa_de_cisalhamento():
    caso = dict(bc.CASO_EXEMPLO_ENGASTE)
    caso.pop("cone_geom")
    so_um = bc.dimensiona_base(caso)
    # arrancamento com cortante alto: sem contato nao ha' atrito e o chumbador
    # (6.7.2.5) nao leva -> placa de cisalhamento obrigatoria
    env = bc.dimensiona_base(caso, esforcos=[("grav", 49.0, 26.0, 60.0),
                                             ("arranc", -60.0, 400.0, 5.0)])
    assert env["aprovado"] and env["chaveta"] is not None
    assert "PLACA DE CISALHAMENTO OBRIGATORIA" in env["tabela"]
    assert so_um["chaveta"] is None


def test_base_sem_placa_de_cisalhamento_declarada_nao_passa():
    caso = dict(bc.CASO_EXEMPLO_ENGASTE, N=-60.0, V=90.0, M=5.0)
    caso.pop("cone_geom")
    r = bc.verifica_base(caso)
    assert r["chaveta_necessaria"] and not r["OK"]
    assert bc.verifica_base(dict(caso, chaveta=True))["chaveta_adotada"]


# ---- tercas -------------------------------------------------------------------
def test_tercas_condicoes_do_anexo_F():
    assert tc.condicoes_anexoF(250, 85, 3.0, 5.0, 250e3) == []
    fora = tc.condicoes_anexoF(200, 75, 2.0, 5.0, 250e3)
    assert len(fora) == 1 and "bw/bf" in fora[0]
    assert any("10 m" in f for f in tc.condicoes_anexoF(250, 85, 3.0, 10.0, 250e3))
    assert any("410" in f for f in tc.condicoes_anexoF(250, 85, 3.0, 5.0, 450e3))


def test_torcao_do_U_simples_confere_a_formula_fechada():
    h, b, t = 200.0, 75.0, 2.0
    r = tc.torcao_secao_aberta([(b, h / 2), (0, h / 2), (0, -h / 2), (b, -h / 2)],
                               [(0, 1, t), (1, 2, t), (2, 3, t)])
    assert r["Cw"] == pytest.approx(t * b ** 3 * h ** 2 * (3 * b + 2 * h) / (12 * (6 * b + h)))
    assert r["xs"] + r["xc"] == pytest.approx(-3 * b ** 2 / (6 * b + h))   # do lado oposto da alma
    assert r["J"] == pytest.approx((2 * b + h) * t ** 3 / 3)


def test_succao_fora_do_anexo_F_nao_usa_a_resistencia_da_mesa_travada():
    import tercas_iteracao as ti
    p = ti._props_ue(200.0, 75.0, 20.0, 2.0)
    r = tc.verifica_terca(p, dict(tc.CFG_EXEMPLO))
    assert r["R"] is None and r["flt"] is not None
    assert r["Mrd_succ"] < 0.6 * r["Mrd_grav"]
    sem_torcao = {k: v for k, v in p.items() if k not in ("J", "Cw", "x0")}
    r2 = tc.verifica_terca(sem_torcao, dict(tc.CFG_EXEMPLO))
    caso = [c for c in r2["casos"].values() if c["uplift"]][0]
    assert caso["OK"] is False and r2["Mrd_succ"] is None


def test_chi_flt_9_8_2_2():
    assert tc.chi_flt(0.5) == 1.0
    assert tc.chi_flt(1.0) == pytest.approx(1.11 * (1 - 0.278))
    assert tc.chi_flt(2.0) == pytest.approx(0.25)


# ---- aco em incendio ------------------------------------------------------------
def test_fogo_aco_sem_revestimento_8_5_1_1():
    """Passo de 1 s refeito aqui, eps = 0,7, alfa_c = 25, ca = 600."""
    ua, theta = 120.0, 20.0
    for i in range(30 * 60):
        tg = 20.0 + 345.0 * math.log10(8.0 * i / 60.0 + 1.0)
        phi = 25.0 * (tg - theta) + 5.67e-8 * 0.7 * ((tg + 273) ** 4 - (theta + 273) ** 4)
        theta += ua / (600.0 * 7850.0) * phi
    assert fogo.temp_aco_nao_protegido(30, ua) == pytest.approx(theta, abs=3.0)


def test_fogo_tabela_1_sem_linha_inventada():
    assert fogo.k_y(550.0) == pytest.approx((0.78 + 0.47) / 2)
    assert fogo.k_E(1100.0) == pytest.approx(0.023)


def test_fogo_revestido_usa_a_forma_da_nbr():
    """Um passo de 30 s refeito pela equacao de 8.5.1.2.2."""
    ua, tp, lam, cp, rp = 150.0, 0.015, 0.20, 1100.0, 300.0
    xi = cp * rp / (600.0 * 7850.0) * tp * ua
    tg1 = 20.0 + 345.0 * math.log10(8.0 * 0.5 + 1.0)
    d = (lam * ua / (tp * 7850.0 * 600.0) * (tg1 - 20.0) * 30.0 / (1 + xi / 4)
         - (tg1 - 20.0) / (4 / xi + 1))
    esperado = 20.0 + max(d, 0.0)
    got = fogo._temp_com_protecao(0.5, ua, "spray", 15.0)
    assert got == pytest.approx(min(esperado, tg1), abs=0.11)


# ---- verticais (amostra) -----------------------------------------------------
def test_agrupamento_de_circuitos_tabela_42_linha_inteira():
    import condutores_nbr5410 as cd
    esperado = {1: 1.00, 2: 0.80, 3: 0.70, 4: 0.65, 5: 0.60, 6: 0.57, 7: 0.54,
                8: 0.52, 9: 0.50, 11: 0.50, 12: 0.45, 15: 0.45, 16: 0.41, 19: 0.41,
                20: 0.38, 40: 0.38}
    for n, f in esperado.items():
        assert cd.fca(n) == pytest.approx(f), n


def test_pressao_minima_no_ponto_nbr5626_2020():
    import hidraulica_predial as hp
    assert hp.P_MIN_PONTO_KPA["caixa_descarga"] >= 10.0
    assert min(hp.P_MIN_PONTO_KPA.values()) >= 10.0
