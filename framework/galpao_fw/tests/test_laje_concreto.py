"""Laje macica (NBR 6118) - AFERICAO contra exemplo resolvido + gates.

Fonte da afericao: Carvalho, R. C. & Figueiredo Filho, J. R., "Calculo e
Detalhamento de Estruturas Usuais de Concreto Armado segundo a NBR 6118:2014",
4a ed., EdUFSCar, 2014, Cap.7 "Pavimentos de edificios com lajes macicas",
Exemplo 1 (p.358-368): pavimento de escritorio com as lajes L1, L2 e L3,
C20, CA-50, h = 12 cm, d = 8 cm, cobrimento 2,5 cm.
  L1: caso 4, 6,00 x 6,00 (lambda 1,00)
  L2: caso 4, 4,00 x 6,00 (lambda 1,50)
  L3: caso 3, 5,00 x 10,00 (lambda 2,00)
  g = 3,00 (p.proprio) + 0,36 (contrapiso) + 0,20 (piso) = 3,56 kN/m2
  q = 2,00 kN/m2 (sala para escritorio) -> p = 5,56 kN/m2
Nada aqui foi escrito de memoria: os coeficientes, os momentos, as areas de aco
e as flechas sao os impressos no livro (ver o quadro das p.363/364 e o das
flechas da p.359).
"""

import re

import pytest

import laje_concreto as lj

FCK, FYK = 20e3, 500e3
P = 5.56          # carga total de calculo de servico do exemplo (kN/m2)
P_QP = 5.36       # combinacao quase permanente do exemplo (h = 16 cm, g+0,4q)
D = 0.08          # altura util adotada no livro
H = 0.12

# (caso, lx, ly, mu esperados, momentos esperados m_x, x_x, m_y, x_y)
LAJES = {
    "L1": dict(caso=4, lx=6.0, ly=6.0, mu=(2.81, 6.99, 2.81, 6.99),
               m=(5.62, 14.00, 5.62, 14.00)),
    "L2": dict(caso=4, lx=4.0, ly=6.0, mu=(4.81, 10.62, 2.47, 8.06),
               m=(4.28, 9.45, 2.20, 7.17)),
    "L3": dict(caso=3, lx=5.0, ly=10.0, mu=(6.51, 12.34, 1.48, 0.0),
               m=(9.05, 17.15, 2.06, 0.0)),
}


# ---------------------------------------------------------------------------
# 1. Coeficientes e momentos: batem com o livro
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nome", sorted(LAJES))
def test_coeficientes_de_bares_do_exemplo(nome):
    L = LAJES[nome]
    c = lj.coeficientes_bares(L["caso"], L["ly"] / L["lx"])
    assert (c["mu_x"], c["mu_x_neg"], c["mu_y"], c["mu_y_neg"]) == L["mu"]
    assert c["saturou"] is False


@pytest.mark.parametrize("nome", sorted(LAJES))
def test_momentos_batem_com_o_livro(nome):
    L = LAJES[nome]
    M = lj.momentos_bares(L["caso"], L["lx"], L["ly"], P)
    esperado = dict(zip(("m_x", "x_x", "m_y", "x_y"), L["m"]))
    for chave, valor in esperado.items():
        # o livro arredonda p*lx^2 (89 em vez de 88,96); 1,5% cobre o
        # arredondamento sem deixar passar erro de coeficiente
        assert M[chave] == pytest.approx(valor, rel=0.015), (nome, chave)


def test_lambda_e_troca_de_vaos():
    """lx e SEMPRE o menor vao: passar invertido nao pode mudar o resultado."""
    a = lj.momentos_bares(4, 4.0, 6.0, P)
    b = lj.momentos_bares(4, 6.0, 4.0, P)
    assert a["m_x"] == pytest.approx(b["m_x"]) and a["lambda"] == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# 2. Armadura de flexao: bate com o quadro de As do livro (p.364)
# ---------------------------------------------------------------------------

# momento (kN.m/m) -> As do livro (cm2/m), com d = 8 cm, b = 1 m, C20, CA-50
AS_LIVRO = [(5.62, 2.388), (14.00, 6.613), (4.28, 1.794), (2.20, 0.907),
            (9.45, 4.204), (7.17, 3.102), (9.05, 3.966), (2.06, 0.850),
            (17.15, 8.561)]


@pytest.mark.parametrize("m,As_livro", AS_LIVRO)
def test_armadura_de_flexao_bate_com_o_livro(m, As_livro):
    """1% cobre a diferenca entre o KMD/KZ tabelado do livro e a forma fechada do
    bloco retangular (o livro resolve a mesma equacao do 2o grau)."""
    r = lj.dimensiona_seccao(1.4 * m, 1.0, D, H, FCK, FYK, "negativa")
    assert r["As"] * 1e4 == pytest.approx(As_livro, rel=0.01)
    assert r["secao_ok"]


def test_ductilidade_pega_o_atalho_de_d_do_proprio_livro():
    """O livro calcula TODAS as armaduras com d = 8 cm "a favor da seguranca",
    inclusive a negativa de L3 (17,15 kN.m/m), cujo d real e 9 cm. Com d = 8 cm
    a secao vai a x/d = 0,48, ACIMA do limite de ductilidade de 0,45 (14.6.4.3);
    com o d real de 9 cm ela volta para dentro. O gate tem de acusar os dois."""
    com_8 = lj.dimensiona_seccao(1.4 * 17.15, 1.0, 0.08, H, FCK, FYK, "negativa")
    com_9 = lj.dimensiona_seccao(1.4 * 17.15, 1.0, 0.09, H, FCK, FYK, "negativa")
    assert com_8["x_d"] > 0.45 and com_8["ok_dominio"] is False
    assert com_9["x_d"] <= 0.45 and com_9["ok_dominio"] is True


def test_armadura_minima_do_livro_e_a_da_tabela_19_1():
    """C20: rho_min = 0,15% -> As,min = 0,15%*100*12 = 1,80 cm2/m (livro, item g3).
    A Tabela 19.1 reduz para 0,67 rho_min a positiva de laje armada em 2 direcoes."""
    assert lj.armadura_minima(FCK, H, "negativa") * 1e4 == pytest.approx(1.80, rel=1e-3)
    assert lj.armadura_minima(FCK, H, "positiva_2d") * 1e4 == pytest.approx(1.206, rel=1e-3)
    assert lj.armadura_minima(FCK, H, "secundaria") * 1e4 == pytest.approx(0.90, rel=1e-3)


def test_minimo_governa_onde_o_livro_diz_que_governa():
    """No livro, L2 m_x (1,794), L2 m_y (0,907) e L3 m_y (0,850) sao substituidos
    pela armadura minima de 1,80 cm2/m."""
    for m in (4.28, 2.20, 2.06):
        r = lj.dimensiona_seccao(1.4 * m, 1.0, D, H, FCK, FYK, "negativa")
        assert r["governa_minimo"]
        assert r["As_adotada"] * 1e4 == pytest.approx(1.80, rel=1e-3)


def test_detalhamento_da_malha_respeita_20_1():
    """phi <= h/8 e s <= min(2h ; 20 cm) na principal; 33 cm na secundaria.
    Para o As positivo de L1 (2,388 cm2/m) o livro detalha phi 6,3 c/ 12,5 cm."""
    m = lj.detalha_malha(2.388e-4, H)
    assert (m["phi_mm"], round(m["s"], 4)) == (6.3, 0.125)
    assert m["phi_mm"] <= H / 8 * 1000 and m["s"] <= min(2 * H, 0.20) + 1e-9
    assert lj.detalha_malha(1.0e-4, H, principal=False)["s_max"] == 0.33
    assert lj.detalha_malha(1.0e-4, 0.08)["s_max"] == 0.16   # 2h < 20 cm


def test_As_efetiva_nunca_fica_abaixo_do_requerido():
    """O espacamento comercial e arredondado PARA BAIXO: a malha entregue tem de
    cobrir o As pedido (o livro aceita 3% de deficit; aqui nao se aceita)."""
    for As in (0.9e-4, 2.0e-4, 3.5e-4, 6.6e-4, 8.6e-4):
        m = lj.detalha_malha(As, H)
        assert m["As_ef"] >= As - 1e-12, m


# ---------------------------------------------------------------------------
# 3. ELS: flecha elastica e fluencia batem com o livro (p.359)
# ---------------------------------------------------------------------------

def test_modulo_secante_do_exemplo():
    """Ecs = 4760*raiz(fck) = 21287 MPa para C20 (item d2 do exemplo)."""
    assert lj.fis.modulo_secante(FCK) / 1000.0 == pytest.approx(21287, rel=2e-4)


def test_fluencia_alpha_f_do_exemplo():
    """t0 = 14/30 = 0,47 mes -> xi(t0) = 0,53 ; xi(inf) = 2 ; alpha_f = 1,47."""
    assert lj.xi_fluencia(0.47) == pytest.approx(0.53, abs=0.005)
    assert lj.xi_fluencia(70.0) == 2.0
    assert lj.alpha_f(70.0, 0.47) == pytest.approx(1.47, abs=0.005)


@pytest.mark.parametrize("nome,alpha,f_im_cm", [("L1", 2.42, 0.19), ("L2", 4.38, 0.06),
                                                ("L3", 5.66, 0.22)])
def test_flecha_elastica_bate_com_o_livro(nome, alpha, f_im_cm):
    """Quadro de flechas do exemplo (calculado ainda com h = 16 cm)."""
    L = LAJES[nome]
    f = lj.flecha_laje(L["caso"], L["lx"], L["ly"], P_QP, 0.16, FCK,
                       considerar_fissuracao=False)
    assert f["alpha"] == pytest.approx(alpha, rel=1e-3)
    assert f["f_elastica"] * 100 == pytest.approx(f_im_cm, abs=0.01)
    # o livro multiplica a flecha JA ARREDONDADA por (1 + alpha_f) = 2,47
    assert f["f_total"] == pytest.approx(f["f_elastica"] * 2.47, rel=0.005)


def test_limites_de_flecha_do_exemplo():
    """O livro atribui a laje 2/3 do limite total: l/250*2/3 = l/375 (quase
    permanente) e l/350*2/3 = l/525 (so carga acidental)."""
    assert lj.limite_flecha("visual", 6.0) * 2 / 3 == pytest.approx(0.0160, abs=1e-5)
    assert lj.limite_flecha("vibracao", 6.0) * 2 / 3 == pytest.approx(0.0114, abs=1e-4)
    assert lj.limite_flecha("alvenaria", 6.0) == 0.010      # teto absoluto de 10 mm
    assert lj.limite_flecha("divisorias_leves", 3.0) == pytest.approx(0.012)


def test_fissuracao_reduz_a_rigidez_e_aumenta_a_flecha():
    """A flecha com Branson (Ic/Ieq) nunca pode ser MENOR que a elastica."""
    f_el = lj.flecha_laje(4, 6.0, 6.0, P_QP, H, FCK, considerar_fissuracao=False)
    f_fis = lj.flecha_laje(4, 6.0, 6.0, P_QP, H, FCK, As_tracao=2.4e-4,
                           M_servico=14.0, d=D)
    assert f_fis["fissurou"] and f_fis["fator_fissuracao"] > 1.0
    assert f_fis["f_imediata"] > f_el["f_elastica"]


# ---------------------------------------------------------------------------
# 4. Reacoes nas vigas: batem com os Quadros 7.8/7.9 (q = k*p*lx/10)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("caso,lam,k_esperado", [
    (1, 1.00, {"x0": 2.50, "x1": 2.50, "y0": 2.50, "y1": 2.50}),
    (1, 1.50, {"x0": 3.33, "x1": 3.33, "y0": 2.50, "y1": 2.50}),
    (2, 1.00, {"x0": 1.83, "x1": 1.83, "y0": 4.02, "y1": 2.32}),
    (4, 1.00, {"x0": 3.17, "x1": 1.83, "y0": 3.17, "y1": 1.83}),
    (9, 1.00, {"x0": 2.50, "x1": 2.50, "y0": 2.50, "y1": 2.50}),
])
def test_reacoes_batem_com_os_quadros_de_k(caso, lam, k_esperado):
    lx = 4.0
    r = lj.reacoes_apoios(caso, lx, lx * lam, 10.0)
    for b, k in k_esperado.items():
        assert r[b]["k"] == pytest.approx(k, abs=0.02), (caso, lam, b)


def test_reacoes_fecham_a_carga_total():
    """Invariante de equilibrio: a soma das reacoes e a carga do painel."""
    for caso in range(1, 10):
        lx, ly, p = 4.0, 6.0, 8.0
        r = lj.reacoes_apoios(caso, lx, ly, p)
        total = sum(v["v"] * (ly if b in ("x0", "x1") else lx) for b, v in r.items())
        assert total == pytest.approx(p * lx * ly, rel=1e-3), caso


# ---------------------------------------------------------------------------
# 5. GATES DE SATURACAO (o calculo nao pode saturar e devolver OK=True)
# ---------------------------------------------------------------------------

def test_tabela_de_placa_satura_em_lambda_2_e_sinaliza():
    """Acima de lambda = 2 a tabela devolve a ultima linha - o que SUBESTIMA o
    momento. O flag 'saturou' tem de acompanhar o valor saturado."""
    c2 = lj.coeficientes_bares(1, 2.00)
    c3 = lj.coeficientes_bares(1, 3.00)
    assert c3["mu_x"] == c2["mu_x"]          # saturou mesmo
    assert c3["saturou"] is True and c2["saturou"] is False


def test_lambda_maior_que_2_vira_laje_armada_em_uma_direcao():
    """Sem forcar, o orquestrador troca de modelo (14.7.6.2) em vez de saturar."""
    r = lj.verifica_laje(dict(lx=2.0, ly=6.0, h=0.10, fck=FCK, fyk=FYK, caso=1,
                              g=1.0, q=2.0))
    assert r["duas_direcoes"] is False and r["saturou_tabela"] is False
    assert r["momentos"]["m_x"] == pytest.approx(r["p_d"] * 2.0 ** 2 / 8.0)
    assert any("UMA direcao" in a for a in r["avisos"])
    assert r["armaduras"]["m_y"]["papel"] == "secundaria"


def test_forcar_tabela_fora_da_faixa_reprova_em_vez_de_passar_calado():
    """GATE: laje 2 x 8 m forcada na tabela de placa - o momento sai subestimado,
    entao NAO pode sair OK=True (padrao da saturacao silenciosa)."""
    r = lj.verifica_laje(dict(lx=2.0, ly=8.0, h=0.12, fck=FCK, fyk=FYK, caso=1,
                              g=1.0, q=2.0, forcar_bares=True))
    assert r["saturou_tabela"] is True
    assert r["OK"] is False
    assert any("SATURACAO" in a for a in r["avisos"])
    # e o momento saturado e mesmo MENOR que o correto de faixa unitaria
    correto = lj.momentos_uma_direcao("apoiada", 2.0, r["p_d"])["m_x"]
    assert r["momentos"]["m_x"] < correto


def test_malha_saturada_reprova():
    """GATE: se nem a maior bitola no menor espacamento cobre o As exigido, o
    detalhamento nao pode ser dado como atendido."""
    m = lj.detalha_malha(60e-4, 0.08)
    assert m["saturou"] is True and m["As_ef"] < 60e-4


def test_laje_impossivel_nao_volta_OK():
    """Vao grande, laje fina e carga alta: qualquer que seja o gate que pegue
    (dominio, secao, malha, flecha), o resultado nao pode ser ATENDE."""
    r = lj.verifica_laje(dict(lx=7.0, ly=7.0, h=0.08, fck=FCK, fyk=FYK, caso=1,
                              g=2.0, q=8.0))
    assert r["OK"] is False and r["avisos"]


def test_dimensiona_laje_nao_devolve_OK_por_esgotar_a_lista():
    """GATE: quando NENHUMA espessura da lista atende, sai OK=False com aviso -
    nunca a ultima tentada dada como boa."""
    r = lj.dimensiona_laje(dict(lx=9.0, ly=9.0, fck=FCK, fyk=FYK, caso=1,
                                g=3.0, q=10.0), espessuras=(0.08, 0.10, 0.12))
    assert r["OK"] is False
    assert any("nenhuma espessura" in a for a in r["avisos"])
    assert r["h"] == 0.12


def test_dimensiona_laje_adota_a_menor_espessura_que_atende():
    r = lj.dimensiona_laje(dict(lx=4.0, ly=5.0, fck=FCK, fyk=FYK, caso=1,
                                g=1.0, q=2.0))
    assert r["OK"] is True
    menor = lj.verifica_laje(dict(lx=4.0, ly=5.0, h=r["h"] - 0.01, fck=FCK,
                                  fyk=FYK, caso=1, g=1.0, q=2.0))
    assert menor["OK"] is False or r["h"] == 0.08


# ---------------------------------------------------------------------------
# 6. Minimos geometricos, cortante, nervurada e entradas invalidas
# ---------------------------------------------------------------------------

def test_espessura_minima_tabela_13_2():
    assert lj.h_minima("cobertura") == 0.07
    assert lj.h_minima("piso") == 0.08
    assert lj.h_minima("balanco") == 0.10
    assert lj.h_minima("lisa") == 0.16
    assert lj.h_minima("cogumelo") == 0.14
    with pytest.raises(ValueError):
        lj.h_minima("laje_de_marte")


def test_h_abaixo_do_minimo_reprova():
    r = lj.verifica_laje(dict(lx=2.0, ly=2.0, h=0.07, fck=FCK, fyk=FYK, caso=1,
                              g=0.5, q=1.5, tipo="piso"))
    assert r["ok_h"] is False and r["OK"] is False


def test_gamma_n_de_balanco():
    """h < 19 cm em balanco: gamma_n = 1,95 - 0,05h[cm] (Tabela 13.2)."""
    assert lj.gamma_n_balanco(0.10) == pytest.approx(1.45)
    assert lj.gamma_n_balanco(0.19) == 1.0
    assert lj.gamma_n_balanco(0.25) == 1.0
    r = lj.verifica_laje(dict(lx=1.5, ly=1.5, h=0.12, fck=FCK, fyk=FYK, caso=1,
                              g=1.0, q=2.0, tipo="balanco"))
    assert r["gamma_n"] == pytest.approx(1.35)
    assert r["p_d"] == pytest.approx(1.4 * 1.35 * r["p_k"])


def test_cortante_de_laje_19_4_1():
    """V_Rd1 = [0,25*fctd*k*(1,2+40*rho1)]*bw*d, k = |1,6-d| >= 1."""
    d, As = 0.10, 5e-4
    r = lj.cortante_laje(10.0, 1.0, d, 25e3, As)
    fctd = 0.7 * 0.3 * 25 ** (2.0 / 3.0) / 1.4 * 1000.0
    esperado = 0.25 * fctd * (1.6 - d) * (1.2 + 40 * As / d) * 1.0 * d
    assert r["V_rd1"] == pytest.approx(esperado, rel=1e-9)
    assert r["k"] == pytest.approx(1.5)
    assert lj.cortante_laje(10.0, 1.0, 0.8, 25e3, As)["k"] == 1.0   # |1,6-0,8| < 1 -> 1
    assert lj.cortante_laje(1e6, 1.0, d, 25e3, As)["exige_armadura"] is True


def test_rho1_do_cortante_e_limitado_a_2_por_cento():
    r = lj.cortante_laje(10.0, 1.0, 0.10, 25e3, 0.10)     # As absurdo
    assert r["rho1"] == pytest.approx(0.02)


def test_nervurada_13_2_4_2():
    ok = lj.verifica_nervurada({"hf": 0.05, "bw": 0.09, "l0": 0.50, "e_nerv": 0.59})
    assert ok["OK"] and "LAJE" in ok["regime"]
    fina = lj.verifica_nervurada({"hf": 0.03, "bw": 0.04, "l0": 0.50, "e_nerv": 0.59})
    assert fina["OK"] is False and len(fina["avisos"]) >= 2
    # mesa minima l0/15 quando o vao livre manda
    grande = lj.verifica_nervurada({"hf": 0.04, "bw": 0.10, "l0": 0.90, "e_nerv": 1.00})
    assert grande["hf_min"] == pytest.approx(0.06) and grande["OK"] is False
    # nervura fina nao pode ter armadura de compressao
    comp = lj.verifica_nervurada({"hf": 0.05, "bw": 0.06, "l0": 0.50,
                                  "e_nerv": 0.56, "armadura_compressao": True})
    assert comp["ok_armadura_compressao"] is False and comp["OK"] is False
    # espacamento entre eixos acima de 110 cm: mesa vira laje macica
    larga = lj.verifica_nervurada({"hf": 0.08, "bw": 0.12, "l0": 1.10, "e_nerv": 1.22})
    assert "LAJE MACICA" in larga["regime"] and larga["OK"] is False


def test_compatibilizacao_de_momentos_negativos():
    """Criterio corrente: o maior entre a media e 80% do maior."""
    c = lj.compatibiliza_momentos_negativos(14.00, 9.45)
    assert c["X"] == pytest.approx(11.725)                 # media governa
    c2 = lj.compatibiliza_momentos_negativos(17.15, 7.17)
    assert c2["X"] == pytest.approx(0.80 * 17.15)          # 80% do maior governa
    assert lj.compatibiliza_momentos_negativos(17.15, 7.17, "maior")["X"] == 17.15
    with pytest.raises(ValueError):
        lj.compatibiliza_momentos_negativos(1.0, 2.0, "chute")


def test_entradas_invalidas_levantam_erro():
    with pytest.raises(ValueError):
        lj.momentos_bares(4, 0.0, 6.0, 5.0)
    with pytest.raises(ValueError):
        lj.momentos_bares(99, 4.0, 6.0, 5.0)
    with pytest.raises(ValueError):
        lj.coeficientes_bares(1, 0.90)          # lambda < 1: vaos trocados
    with pytest.raises(ValueError):
        lj.momentos_uma_direcao("flutuante", 4.0, 5.0)
    with pytest.raises(ValueError):
        lj.armadura_minima(FCK, 0.12, "papel_inexistente")
    with pytest.raises(ValueError):
        lj.limite_flecha("conforto_espiritual", 4.0)


# ---------------------------------------------------------------------------
# 7. Orquestrador ponta a ponta
# ---------------------------------------------------------------------------

def test_laje_do_exemplo_atende_e_reproduz_os_momentos():
    """L1 do livro pelo orquestrador (d proprio, dai o As nao ser o do livro)."""
    r = lj.verifica_laje(dict(lx=6.0, ly=6.0, h=0.12, fck=FCK, fyk=FYK, caso=4,
                              g=0.56, q=2.0, cobrimento=0.025, phi_mm=8.0,
                              lim_flecha="visual"))
    assert r["p_k"] == pytest.approx(5.56)
    assert r["momentos"]["m_x"] / 1.4 == pytest.approx(5.62, rel=0.01)
    assert r["momentos"]["x_x"] / 1.4 == pytest.approx(14.00, rel=0.01)
    assert r["OK"] is True
    assert r["fissuracao"]["OK"] and r["cortante"]["ok"]
    assert set(r["ancoragem"]) and all(a["lb_nec_mm"] > 0 for a in r["ancoragem"].values())


def test_relatorio_sai_em_portugues_com_virgula_decimal():
    r = lj.verifica_laje(dict(lx=4.0, ly=5.0, h=0.12, fck=FCK, fyk=FYK, caso=1,
                              g=1.0, q=2.0))
    txt = lj.relatorio_pt(r)
    assert "LAJE MACICA" in txt and "RESULTADO" in txt
    assert "cm2/m" in txt and re.search(r"\d,\d", txt)
