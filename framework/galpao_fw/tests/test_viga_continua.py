"""Testes da viga continua (NBR 6118:2014, item 14.6.6).

Aferição do solver: contra as solucoes FECHADAS classicas de viga continua de
vaos iguais sob carga uniforme (momentos de apoio, reacoes e momentos positivos),
que sao independentes do codigo. Depois, cada correcao obrigatoria de 14.6.6.1 e
verificada pelo efeito que ela produz - nao pela sua existencia no fonte.
"""

import pytest

import viga_continua as vc

W = 10.0        # kN/m
L = 5.0         # m
EI = 1.0e5      # kN.m2


def _tramos(n, L_=L):
    return [{"L": L_, "EI": EI} for _ in range(n)]


def _caso(n, w=W, L_=L):
    return vc._analisa_caso(_tramos(n, L_), [w] * n, [[] for _ in range(n)],
                            n_pontos=1001)


# ---------------------------------------------------------------------------
# Aferição do solver contra solucoes fechadas
# ---------------------------------------------------------------------------
def test_um_vao_reproduz_biapoiada():
    r = _caso(1)
    assert max(r["M_x"][0]) == pytest.approx(W * L ** 2 / 8, rel=1e-6)
    assert r["M_apoios"][0] == pytest.approx(0.0, abs=1e-9)
    assert r["M_apoios"][1] == pytest.approx(0.0, abs=1e-9)


def test_dois_vaos_iguais_valores_fechados():
    """Viga de 2 vaos iguais sob carga uniforme: M_apoio = -wL^2/8,
    R_extremo = 3wL/8, R_central = 10wL/8, M+ = 9wL^2/128."""
    r = _caso(2)
    assert r["M_apoios"][1] == pytest.approx(-W * L ** 2 / 8, rel=1e-6)
    assert r["reacoes"][0] == pytest.approx(3 * W * L / 8, rel=1e-6)
    assert r["reacoes"][1] == pytest.approx(10 * W * L / 8, rel=1e-6)
    assert max(r["M_x"][0]) == pytest.approx(9 * W * L ** 2 / 128, rel=1e-4)


def test_tres_vaos_iguais_valores_fechados():
    """3 vaos iguais: M_apoio = -0,10wL^2 ; R_ext = 0,40wL ; R_int = 1,10wL ;
    M+ = 0,080wL^2 no tramo externo e 0,025wL^2 no central."""
    r = _caso(3)
    assert r["M_apoios"][1] == pytest.approx(-0.100 * W * L ** 2, rel=1e-5)
    assert r["M_apoios"][2] == pytest.approx(-0.100 * W * L ** 2, rel=1e-5)
    assert r["reacoes"][0] == pytest.approx(0.400 * W * L, rel=1e-5)
    assert r["reacoes"][1] == pytest.approx(1.100 * W * L, rel=1e-5)
    assert max(r["M_x"][0]) == pytest.approx(0.080 * W * L ** 2, rel=1e-4)
    assert max(r["M_x"][1]) == pytest.approx(0.025 * W * L ** 2, rel=1e-4)


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_equilibrio_global_soma_das_reacoes(n):
    r = _caso(n)
    assert sum(r["reacoes"]) == pytest.approx(n * W * L, rel=1e-9)


def test_vaos_desiguais_o_vao_maior_puxa_o_momento():
    """O ponto de ter um solver em vez do coeficiente fixo qL^2/10: com vaos
    desiguais o momento de apoio nao e simetrico nem previsivel por coeficiente."""
    tr = [{"L": 4.0, "EI": EI}, {"L": 7.0, "EI": EI}]
    r = vc._analisa_caso(tr, [W, W], [[], []], n_pontos=401)
    # o coeficiente fixo de viga_concreto daria wL^2/10 com um unico L; aqui o
    # momento de apoio e maior em modulo que o do menor vao isolado
    assert r["M_apoios"][1] < -W * 4.0 ** 2 / 10.0
    assert max(r["M_x"][1]) > max(r["M_x"][0])


# ---------------------------------------------------------------------------
# 14.6.6.1-a : M+ nao pode ser menor que o de engastamento perfeito
# ---------------------------------------------------------------------------
def test_correcao_a_eleva_o_momento_positivo_do_tramo_central():
    """No tramo central de 3 vaos iguais o modelo classico da 0,025wL^2, MENOR que o
    engastamento perfeito wL^2/24 = 0,0417wL^2. A alinea 'a' obriga a subir. Sem essa
    correcao o tramo central sai com 60% da armadura positiva devida."""
    r = vc.analisa({"tramos": [{"L": L, "b": 0.20, "h": 0.50} for _ in range(3)],
                    "g": W, "q": 0.0})
    M_eng = W * L ** 2 / 24.0
    assert r["M_positivo"][1] == pytest.approx(M_eng, rel=1e-4)
    assert r["M_positivo"][1] > 0.025 * W * L ** 2 * 1.5
    assert any("14.6.6.1-a" in c for c in r["correcoes_14661"])


def test_correcao_a_nao_mexe_onde_nao_precisa():
    """No tramo externo (0,08wL^2 > wL^2/24) a correcao nao se aplica."""
    r = vc.analisa({"tramos": [{"L": L, "b": 0.20, "h": 0.50} for _ in range(3)],
                    "g": W, "q": 0.0})
    assert r["M_positivo"][0] == pytest.approx(0.080 * W * L ** 2, rel=1e-3)


# ---------------------------------------------------------------------------
# 14.6.6.1-b : M- em apoio interno solidario ao pilar
# ---------------------------------------------------------------------------
def test_correcao_b_e_um_piso_sobre_o_modulo_nao_uma_atribuicao():
    """Em vaos iguais a analise elastica ja da |M-| = 0,10wL^2, MAIOR que o
    engastamento perfeito wL^2/12 = 0,083wL^2 (a viga continua infinita converge
    justamente para w*L^2/12). A alinea 'b' e um piso: nesse caso ela nao mexe em
    nada. Um codigo que ATRIBUISSE w*L^2/12 estaria reduzindo o momento de apoio em
    17% e subarmando a viga."""
    r = vc.analisa({"tramos": [{"L": L, "b": 0.20, "h": 0.50} for _ in range(3)],
                    "g": W, "q": 0.0,
                    "apoios_solidarios": {1: {"largura_apoio": 0.20, "h_pilar": 0.60}}})
    assert r["M_apoios"][1] == pytest.approx(-0.100 * W * L ** 2, rel=1e-4)
    assert not any("14.6.6.1-b" in c for c in r["correcoes_14661"])


def test_correcao_b_morde_quando_o_vao_extremo_e_curto():
    """Vaos [2; 6; 2]: os tramos extremos curtos aliviam o apoio, e a analise elastica
    da |M-| = 25,4 kN.m, ABAIXO do engastamento perfeito do vao de 6 m (30 kN.m). Aqui
    a alinea 'b' morde e eleva o momento negativo."""
    vaos = [2.0, 6.0, 2.0]
    base = {"tramos": [{"L": v, "b": 0.20, "h": 0.50} for v in vaos], "g": W, "q": 0.0}
    ref = -W * 6.0 ** 2 / 12.0
    sem = vc.analisa(base)
    assert sem["M_apoios"][1] > ref            # elastico e menor em modulo
    com = vc.analisa(dict(base, apoios_solidarios={1: {"largura_apoio": 0.20,
                                                       "h_pilar": 0.60}}))
    assert com["M_apoios"][1] == pytest.approx(ref, rel=1e-6)
    assert any("14.6.6.1-b" in c for c in com["correcoes_14661"])


def test_correcao_b_nao_se_aplica_com_largura_de_apoio_pequena():
    """A alinea 'b' so vale se a largura do apoio for maior que h_pilar/4."""
    vaos = [2.0, 6.0, 2.0]
    base = {"tramos": [{"L": v, "b": 0.20, "h": 0.50} for v in vaos], "g": W, "q": 0.0}
    r = vc.analisa(dict(base, apoios_solidarios={1: {"largura_apoio": 0.10,
                                                     "h_pilar": 0.60}}))
    assert r["M_apoios"][1] > -W * 6.0 ** 2 / 12.0
    assert any("nao se aplica" in a for a in r["avisos"])


def test_correcao_b_recusa_apoio_extremo():
    base = {"tramos": [{"L": L, "b": 0.20, "h": 0.50} for _ in range(3)], "g": W}
    with pytest.raises(ValueError, match="apoio INTERNO"):
        vc.analisa(dict(base, apoios_solidarios={0: {"largura_apoio": 0.2,
                                                     "h_pilar": 0.6}}))


# ---------------------------------------------------------------------------
# 14.6.6.1-c : engastamento parcial nos apoios extremos
# ---------------------------------------------------------------------------
def test_coeficientes_satisfazem_o_equilibrio_do_no():
    """Os tres coeficientes de 14.6.6.1-c NAO somam 1 - eles reparticionam o momento
    de engastamento perfeito entre as tres barras que chegam ao no, e o que tem de
    valer e o EQUILIBRIO: o momento que fica na viga e igual a soma dos que vao para
    os tramos superior e inferior do pilar."""
    c = vc.coef_engastamento_parcial(r_vig=0.001, r_inf=0.002, r_sup=0.0015)
    assert c["viga"] == pytest.approx(c["sup"] + c["inf"], rel=1e-12)
    assert c["viga"] <= 1.0
    a = vc.coef_engastamento_parcial(0.001, 0.002, 0.0015, variante="apostila")
    assert a["viga"] == pytest.approx(a["sup"] + a["inf"], rel=1e-12)


def test_coeficiente_da_viga_e_o_texto_literal_da_norma():
    """A NBR 6118 14.6.6.1-c escreve (r_inf + r_sup)/(r_vig + r_inf + r_sup), SEM os
    fatores 3 e 4 que aparecem em material didatico. A variante didatica existe so
    para comparacao e da resultado diferente - nao pode ser o default."""
    r_vig, r_inf, r_sup = 0.0020, 0.0015, 0.0015
    norma = vc.coef_engastamento_parcial(r_vig, r_inf, r_sup)
    assert norma["viga"] == pytest.approx((r_inf + r_sup) / (r_vig + r_inf + r_sup),
                                          rel=1e-12)
    apost = vc.coef_engastamento_parcial(r_vig, r_inf, r_sup, variante="apostila")
    assert apost["viga"] != pytest.approx(norma["viga"], rel=1e-6)
    assert "NAO e o texto da norma" in apost["fonte"]


def test_pilar_muito_rigido_engasta_a_viga():
    """Com os pilares muito mais rigidos que a viga, o coeficiente da viga tende a 1
    (engastamento quase perfeito); com pilares flexiveis, tende a 0 (rotula)."""
    rigido = vc.coef_engastamento_parcial(r_vig=0.001, r_inf=1.0, r_sup=1.0)
    flexivel = vc.coef_engastamento_parcial(r_vig=1.0, r_inf=1e-6, r_sup=1e-6)
    assert rigido["viga"] > 0.99
    assert flexivel["viga"] < 0.01


def test_apoio_extremo_recebe_momento_negativo_e_devolve_momento_ao_pilar():
    """No modelo classico o apoio extremo tem M = 0. A alinea 'c' introduz o momento
    de engastamento parcial - e a parcela que sobra vai para os tramos do PILAR, que e
    justamente o momento de 1a ordem no topo do pilar de extremidade."""
    r = vc.analisa({
        "tramos": [{"L": L, "b": 0.20, "h": 0.50} for _ in range(2)],
        "g": W, "q": 0.0,
        "apoios_extremos": {0: {"r_vig": 0.0010, "r_inf": 0.0008, "r_sup": 0.0008}},
    })
    assert r["M_apoios"][0] < 0.0
    d = r["momentos_no_pilar"][0]
    assert d["M_sup"] > 0.0 and d["M_inf"] > 0.0
    # o momento total repartido e o de engastamento perfeito
    M_eng = W * L ** 2 / 12.0
    assert d["M_engastamento_perfeito"] == pytest.approx(M_eng, rel=1e-9)
    # equilibrio do no: o que fica na viga = o que vai para os dois tramos do pilar
    assert abs(r["M_apoios"][0]) == pytest.approx(d["M_sup"] + d["M_inf"], rel=1e-4)
    assert abs(r["M_apoios"][0]) == pytest.approx(
        d["coeficientes"]["viga"] * M_eng, rel=1e-4)


# ---------------------------------------------------------------------------
# 14.6.6.3 : alternancia de cargas
# ---------------------------------------------------------------------------
def test_dispensa_de_alternancia_exige_as_DUAS_condicoes():
    """"carga variavel de ate 5 kN/m2 E que seja no maximo igual a 50% da carga
    total" - as duas condicoes sao cumulativas."""
    ok, _ = vc.dispensa_alternancia(2.0, 8.0)          # 2 <= 5 e 25% <= 50%
    assert ok is True
    nao1, m1 = vc.dispensa_alternancia(6.0, 20.0)      # 30% mas 6 > 5 kN/m2
    assert nao1 is False and "5 kN/m2" in m1
    nao2, m2 = vc.dispensa_alternancia(4.0, 6.0)       # 4 <= 5 mas 67% > 50%
    assert nao2 is False and "50%" in m2


def test_alternancia_aumenta_o_momento_positivo():
    """O ponto da alternancia: carregar os tramos em xadrez aumenta o M+ do tramo
    carregado em relacao ao carregamento total. Se o codigo nunca alternasse, o M+
    sairia menor e nada reprovaria."""
    cfg = {"tramos": [{"L": L, "b": 0.20, "h": 0.50} for _ in range(3)],
           "g": 4.0, "q": 8.0}
    sem = vc.analisa(dict(cfg, alternancia=False))
    com = vc.analisa(dict(cfg, alternancia=True))
    assert com["n_casos_de_carga"] > sem["n_casos_de_carga"]
    assert com["M_positivo"][0] > sem["M_positivo"][0]


def test_saturacao_silenciosa_alternancia_obrigatoria_desligada_reprova():
    """SATURACAO SILENCIOSA: a alternancia nao aparece como razao solicitante/
    resistente. Uma viga de biblioteca (q = 6 kN/m2 > 5) analisada sem alternancia
    passa em flexao e cortante e ainda assim esta subdimensionada. Aqui o resultado
    sai OK=False, com o motivo."""
    r = vc.analisa({
        "tramos": [{"L": L, "b": 0.20, "h": 0.50} for _ in range(3)],
        "g": 12.0, "q": 18.0,
        "g_area_kN_m2": 4.0, "q_area_kN_m2": 6.0,
        "alternancia": False,
    })
    assert r["OK"] is False
    assert any("REPROVADO" in a for a in r["avisos"])
    assert r["alternancia_dispensada"] is False


def test_modo_auto_liga_a_alternancia_quando_a_dispensa_nao_vale():
    r = vc.analisa({
        "tramos": [{"L": L, "b": 0.20, "h": 0.50} for _ in range(3)],
        "g": 12.0, "q": 18.0,
        "g_area_kN_m2": 4.0, "q_area_kN_m2": 6.0,
    })
    assert r["OK"] is True
    assert r["alternancia_dispensada"] is False
    assert r["alternancia_aplicada"] is True


def test_modo_auto_dispensa_quando_a_carga_e_leve():
    r = vc.analisa({
        "tramos": [{"L": L, "b": 0.20, "h": 0.50} for _ in range(3)],
        "g": 15.0, "q": 4.5,
        "g_area_kN_m2": 5.0, "q_area_kN_m2": 1.5,
    })
    assert r["alternancia_dispensada"] is True
    assert r["alternancia_aplicada"] is False


def test_sem_cargas_por_area_o_criterio_absoluto_nao_pode_ser_verificado():
    """Honestidade do aviso: sem q por AREA, o limite de 5 kN/m2 (que e por area) nao
    tem como ser checado, e isso tem de estar dito - nao silenciosamente assumido."""
    r = vc.analisa({"tramos": [{"L": L, "b": 0.20, "h": 0.50} for _ in range(2)],
                    "g": 15.0, "q": 5.0})
    assert "nao pode ser verificado" in r["alternancia_motivo"]


# ---------------------------------------------------------------------------
# robustez de entrada
# ---------------------------------------------------------------------------
def test_lista_de_cargas_com_tamanho_errado_levanta():
    with pytest.raises(ValueError, match="tramos"):
        vc.analisa({"tramos": [{"L": L, "b": 0.2, "h": 0.5} for _ in range(3)],
                    "g": [1.0, 2.0]})


def test_viga_sem_tramos_levanta():
    with pytest.raises(ValueError, match="pelo menos um tramo"):
        vc.analisa({"tramos": [], "g": 1.0})


def test_carga_pontual_no_meio_do_vao_biapoiado():
    r = vc._analisa_caso([{"L": L, "EI": EI}], [0.0], [[(40.0, L / 2)]], n_pontos=1001)
    assert max(r["M_x"][0]) == pytest.approx(40.0 * L / 4.0, rel=1e-3)
    assert sum(r["reacoes"]) == pytest.approx(40.0, rel=1e-9)


def test_relatorio_traz_os_itens_normativos():
    r = vc.analisa({"tramos": [{"L": L, "b": 0.20, "h": 0.50} for _ in range(3)],
                    "g": W, "q": 2.0,
                    "apoios_extremos": {0: {"r_vig": 1e-3, "r_inf": 8e-4,
                                            "r_sup": 8e-4}}})
    txt = vc.relatorio(r)
    assert "14.6.6" in txt
    assert "Alternancia de cargas" in txt
    assert "Engastamento parcial" in txt
