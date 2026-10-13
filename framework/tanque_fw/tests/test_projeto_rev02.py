# ============================================================================
# test_projeto_rev02.py - DIMENSIONAMENTO DA REV.02 DO TANQUE-BASE.
# Os valores esperados sao contas a mao sobre as dimensoes de SPEC_REV02, e
# cada verificacao tem um teste que a faz reprovar quando a peca e' enfraquecida.
# ============================================================================
"""Tanque-base integral: projeto da REV.02."""

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import projeto_rev02 as P


def _ver(res, trecho):
    achados = [v for v in res["verificacoes"] if trecho in v["nome"]]
    assert len(achados) == 1, trecho
    return achados[0]


def test_geometria_fecha_dentro_do_skid():
    g = P.geometria(P.SPEC_REV02)
    # 6058 - 2x100 (testeiras) - 50 (folga) - 400 (baia) ; 2438 - 2x(100 + 50)
    # altura: 690 - 15 - 50 (travessa superior) - 100 (travessa inferior)
    assert g["tanque_ext"] == pytest.approx((5408.0, 2138.0, 525.0))
    # tampa: 690 - 15 (folga sob o conteiner) - 50 (travessa superior)
    assert g["z_tampa"] == pytest.approx(625.0)
    assert g["interno"][2] == pytest.approx(525.0 - 6.35 - 4.75)
    # a gaiola fica abaixo do plano dos cantos mais que os 6 mm da ISO 1496-1 5.3.4
    assert P.SPEC_REV02["skid"]["alt"] - g["z_topo_gaiola"] > 6.0
    assert g["passo"] <= P.SPEC_REV02["passo_travessa_max"]
    assert g["passo"] == pytest.approx(5408.0 / 11)


def test_capacidade():
    cap = P.capacidade(P.SPEC_REV02)
    assert cap["volume_m3"] == pytest.approx(5.3985 * 2.1285 * 0.5139, rel=1e-9)
    assert cap["niveis"]["alarme_alto"]["volume_m3"] == pytest.approx(4.72, abs=0.01)
    assert cap["turnos_ate_alarme_alto"] == pytest.approx(4.724 / 1.57, abs=0.01)


def test_tensao_na_tampa_a_mao():
    # M = 0,005 x 491,64^2 / 8 = 151,07 N.mm/mm ; t = 4,75 - 1,0 = 3,75 mm
    # sigma = 1,5 x 6 x 151,07 / 3,75^2 = 96,7 MPa ; resistente 250 / 1,10
    v = _ver(P.calcular(), "Tampa")
    assert v["sd"] == pytest.approx(1.5 * 6 * (0.005 * (5408 / 11) ** 2 / 8) / 3.75 ** 2)
    assert v["sd"] == pytest.approx(96.7, abs=0.1)
    assert v["rd"] == pytest.approx(227.27, abs=0.01)


def test_projeto_aprovado_e_apoio_central_obrigatorio():
    res = P.calcular()
    assert res["aprovado"] is True
    so4 = _ver(res, "so' 4 cantos")
    assert so4["ok"] is False and so4["informativo"] is True
    assert _ver(res, "6 apoios")["ok"] is True


@pytest.mark.parametrize("caminho, valor, trecho", [
    (("chapas", "tampa"), 3.0, "Tampa"),
    (("chapas", "lateral"), 3.0, "Lateral"),
    (("chapas", "fundo"), 3.0, "Fundo"),
    (("adotado", "pressao_projeto_kPa"), 12.0, "Travessa superior"),
    (("adotado", "fator_dinamico_icamento"), 3.0, "Icamento vazio pelos 4 cantos"),
    (("adotado", "carga_canto_kN"), 250.0, "Montante de canto: carga da placa"),
    (("adotado", "vazao_ar_caminhao_m3h"), 2000.0, "Respiro"),
    (("tubo_travessa_inf", "t"), 1.0, "Travessa inferior: flexao"),
    (("perna_solda",), 3.0, "Perna minima"),
    (("detalhes", "olhal", "borda"), 2.0, "Olhal: rasgamento"),
    (("detalhes", "olhal", "t"), 4.0, "Olhal: flexao fora do plano"),
    (("solda_chapa", "passo"), 60000.0, "Solda intermitente"),
    (("detalhes", "chapa_topo", "t"), 9.5, "Chapa de topo"),
    (("local", "v0"), 400.0, "vento lateral"),
    (("adotado", "massa_conteiner_minima_kg"), 0.0, "Tombamento"),
    (("detalhes", "poco", "prof"), 95.0, "Poco do pescador: profundidade"),
    (("adotado", "angulo_cabo_icamento_graus"), 1.0, "compressao na longarina superior"),
])
def test_peca_enfraquecida_reprova(caminho, valor, trecho):
    spec = copy.deepcopy(P.SPEC_REV02)
    alvo = spec
    for k in caminho[:-1]:
        alvo = alvo[k]
    alvo[caminho[-1]] = valor
    res = P.calcular(spec)
    assert _ver(res, trecho)["ok"] is False
    assert res["aprovado"] is False


def test_reacoes_somam_o_total():
    r = P.reacoes(P.SPEC_REV02)
    assert 4 * r["canto_kN"] + 2 * r["meio_kN"] == pytest.approx(r["total_kN"], rel=1e-9)


def test_respiro_limite_devolve_a_pressao_de_projeto():
    spec = copy.deepcopy(P.SPEC_REV02)
    spec["adotado"]["vazao_ar_caminhao_m3h"] = P.respiro(spec)["vazao_limite_m3h"]
    assert P.respiro(spec)["depressao_kPa"] == pytest.approx(5.0, rel=1e-9)


def test_travessa_inferior_em_pe_limita_a_flecha():
    v = _ver(P.calcular(), "Travessa inferior: flexao")
    # tanque cheio em operacao normal: melhor que vao/500
    assert 2238.0 / v["flecha_normal_mm"] > 500
    deitada = copy.deepcopy(P.SPEC_REV02)
    deitada["tubo_travessa_inf"] = {"h": 50.0, "b": 100.0, "t": 4.75}
    vd = _ver(P.calcular(deitada), "Travessa inferior: flexao")
    assert 2238.0 / vd["flecha_normal_mm"] < 250


def test_espessura_de_calculo_do_tubo_e_a_minima_da_nbr_8261():
    prop = P.tubo_de_calculo(P.SPEC_REV02, "tubo_quadro")
    assert prop["t_calculo_mm"] == pytest.approx(6.35 * 0.875)
    nominal = P.TB.tubo_retangular(P.SPEC_REV02["tubo_quadro"])
    assert prop["Wx_mm3"] < nominal["Wx_mm3"]
    assert prop["raio_externo_mm"] == pytest.approx(nominal["raio_externo_mm"])
    assert prop["massa_kg_m"] == pytest.approx(nominal["massa_kg_m"])   # peso: parede nominal


def test_cortante_da_travessa_a_mao():
    # h plano = 100 - 2 x 3 x 4,75 = 71,5 ; tw = 4,75 x 0,875 ; Aw = 2.h.tw
    v = _ver(P.calcular(), "Travessa inferior: cortante")
    assert v["rd"] == pytest.approx(0.6 * 2 * 71.5 * 4.75 * 0.875 * 317 / 1.10 / 1000, rel=1e-9)


def test_flechas_em_servico_dentro_do_limite_de_viga_de_piso():
    res = P.calcular()
    assert _ver(res, "Travessa inferior: flecha")["rd"] == pytest.approx(2238.0 / 350)
    assert _ver(res, "Longarina inferior: flecha")["ok"]


def test_tabela_de_soldas_cobre_o_tanque_e_a_gaiola():
    juntas = P.juntas_soldadas(P.SPEC_REV02)
    nomes = " | ".join(j[0] for j in juntas)
    for trecho in ("Longarina", "Travessa na longarina", "Fundo", "Tampa", "Poco", "Olhal",
                   "Chapa de topo", "Bocais"):
        assert trecho in nomes
    # 12 barras do quadro x 2 pontas ; 24 travessas x 2 pontas
    por_nome = {j[0]: j for j in juntas}
    assert por_nome["Longarina e testeira no montante"][3] == 24
    assert por_nome["Travessa na longarina"][3] == 48
    # o perimetro do tanque: 2 x (5408 + 2138)
    assert por_nome["Tampa nas laterais e testas (fechamento)"][4] == pytest.approx(15092.0)
    # toda solda do envelope molhado e' continua
    for j in juntas:
        if j[0].startswith(("Fundo", "Lateral", "Tampa", "Poco", "Bocais")):
            assert "ESTANQUE" in j[1]


def test_so_a_boca_de_inspecao_e_aparafusada():
    textos = " ".join(e for _i, e, _q in P.componentes(P.SPEC_REV02))
    assert textos.count("aparafusad") == 1
    assert any("Tudo soldado" in n for n in P.notas_gerais(P.SPEC_REV02))


def test_vento_a_mao():
    # NBR 6123:2023: Vk = 35 x 1,0 x 0,94 x 1,0 = 32,9 m/s ; q = 0,613 x 32,9^2 = 663,5 N/m2
    # altura = 0,690 + 2,591 = 3,281 m ; h/b = 3,281 / 2,438 = 1,35 ; a/b = 2,48
    # Tabela 6: barlavento +0,7 e sotavento -0,6 -> 1,3 x 663,5 = 862,6 N/m2
    v = P.vento(P.SPEC_REV02)
    assert v["vk_m_s"] == pytest.approx(32.9)
    assert v["q_kPa"] == pytest.approx(0.6635, abs=0.0001)
    assert (v["ce_barlavento"], v["ce_sotavento"]) == (0.7, -0.6)
    assert v["h_b"] == pytest.approx(3.281 / 2.438) and v["a_b"] == pytest.approx(6.058 / 2.438)
    assert v["forca_total_kN"] == pytest.approx(0.86255 * 6.058 * 3.281, rel=1e-4)
    assert v["forca_conteiner_kN"] == pytest.approx(0.86255 * 6.058 * 2.591, rel=1e-4)
    assert v["fora_da_tabela"] is False


@pytest.mark.parametrize("cat, classe, bm, fr, p", [
    ("II", "A", 1.00, 1.00, 0.085), ("IV", "B", 0.85, 0.98, 0.125), ("I", "C", 1.12, 0.95, 0.07),
])
def test_s2_da_tabela_3_bate_com_a_formula(cat, classe, bm, fr, p):
    # Tabelas 1 e 2 da NBR 6123:2023, z = 5 m
    assert P.S2_ATE_5M[cat][classe] == pytest.approx(bm * fr * 0.5 ** p, abs=0.006)


def test_vento_recusa_conjunto_acima_de_5_m():
    spec = copy.deepcopy(P.SPEC_REV02)
    spec["skid"]["alt"] = 2500.0
    with pytest.raises(ValueError, match="z <= 5 m"):
        P.vento(spec)


def test_tombamento_a_mao():
    # H_sd = 1,4 x 17,145 = 24,00 kN a 3,281 / 2 ; braco = (2438 - 100) / 2 = 1169 mm
    e = P.estabilidade(P.SPEC_REV02)
    assert e["tombamento"]["sd"] == pytest.approx(24.003 * 1.6405, abs=0.01)
    assert e["tombamento"]["rd"] == pytest.approx(0.9 * e["peso_minimo_kN"] * 1.169)
    assert e["atrito_necessario"] == pytest.approx(24.003 / (0.9 * e["peso_minimo_kN"]), abs=1e-3)
    # sem conteiner em cima a base vazia nao segura o vento de um conteiner
    assert e["atrito_necessario"] > 0.4


def test_apoio_sem_tensao_declarada_nao_dimensiona():
    a = P.apoios(P.SPEC_REV02)
    assert a["lado_mm"] is None and a["tensao_admissivel_kPa"] is None
    r = P.reacoes(P.SPEC_REV02)
    assert a["carga_max_kN"] == pytest.approx(r["canto_placa_kN"] + a["vento_canto_kN"])
    assert a["pressao_calco_MPa"] == pytest.approx(a["carga_max_kN"] * 1000 / (250.0 * 200.0))


def test_apoio_com_tensao_declarada():
    spec = copy.deepcopy(P.SPEC_REV02)
    spec["apoio"]["tensao_admissivel_kPa"] = 100.0
    a = P.apoios(spec)
    # raiz(1,05 x 54,15 / 100) = 0,754 m -> 800 mm
    assert a["lado_mm"] == 800.0
    spec["apoio"]["tensao_admissivel_kPa"] = 1000.0
    assert P.apoios(spec)["lado_mm"] == P.LADO_MIN_SAPATA      # NBR 6122 7.7.1


# ---------------------------------------------------------------------------
# calculo parametrico: outros conteineres da serie 1 (ISO 668)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n_vaos, m, r_ext, r_int, flecha", [
    (1, 1 / 8, 0.5, 0.0, 5 / 384),            # biapoiada
    (2, 1 / 8, 0.375, 1.25, 1 / 185),         # dois vaos
    (3, 0.100, 0.400, 1.100, 0.00688),        # tres vaos
    (4, 0.1071, 0.3929, 1.1428, 0.00646),     # quatro vaos (tabela: 0,0065)
])
def test_viga_continua_bate_com_os_coeficientes_de_tabela(n_vaos, m, r_ext, r_int, flecha):
    v = P.viga_continua(n_vaos, 1.0, 1.0)
    assert v["M_max"] == pytest.approx(m, abs=2e-4)
    assert v["R_extremo"] == pytest.approx(r_ext, abs=2e-4)
    assert v["R_interno_max"] == pytest.approx(r_int, abs=2e-4)
    assert v["flecha_EI"] == pytest.approx(flecha, abs=3e-5)
    assert sum(v["reacoes"]) == pytest.approx(n_vaos)


def test_tabela_iso_668():
    c = P.CONTEINER_ISO
    assert (c["1CC"]["comp"], c["1CC"]["alt"], c["1CC"]["S"], c["1CC"]["R"]) == (
        6058.0, 2591.0, 5853.0, 36000.0)
    assert (c["1AA"]["comp"], c["1AA"]["S"]) == (12192.0, 11985.0)
    assert (c["1D"]["comp"], c["1D"]["S"], c["1D"]["R"]) == (2991.0, 2787.0, 10160.0)
    assert c["1CCC"]["alt"] == 2896.0 and "1DD" not in c


def test_novo_spec_do_proprio_1cc_e_a_rev02():
    spec = P.novo_spec("1CC", documento=P.SPEC_REV02["documento"])
    assert spec == P.SPEC_REV02


@pytest.mark.parametrize("tipo, lados", [("1D", 2), ("1CC", 3), ("1BB", 5), ("1AA", 6)])
def test_novo_spec_reparte_os_apoios_sem_passar_do_vao_da_rev02(tipo, lados):
    spec = P.novo_spec(tipo)
    g = P.geometria(spec)
    assert spec["apoios_por_lado"] == lados
    assert g["vao_longarina"] <= 2954.0 + 1e-6
    r = P.reacoes(spec)
    assert 4 * r["canto_kN"] + 2 * sum(r["meios_kN"]) == pytest.approx(r["total_kN"], rel=1e-9)


@pytest.mark.parametrize("tipo", ["1D", "1C", "1CCC", "1BB", "1AA"])
def test_outros_conteineres_calculam_ate_o_veredito(tipo):
    res = P.calcular(P.novo_spec(tipo))
    assert isinstance(res["aprovado"], bool)
    assert res["capacidade"]["volume_m3"] > 0 and res["vento"]["forca_total_kN"] > 0


def test_conteiner_de_40_pes_fica_fora_da_tabela_de_vento_e_avisa():
    v = P.vento(P.novo_spec("1AA"))
    assert v["a_b"] == pytest.approx(12192.0 / 2438.0) and v["fora_da_tabela"] is True


def test_novo_spec_recusa_entrada_invalida():
    with pytest.raises(ValueError, match="fora da serie 1"):
        P.novo_spec("1DD")
    with pytest.raises(ValueError, match="400 a 1200"):
        P.novo_spec("1CC", alt_base=200.0)
    with pytest.raises(ValueError, match="inteiro"):
        P.novo_spec("1CC", apoios_por_lado=1)


def test_documentos_da_rev02_recusam_outro_conteiner(tmp_path):
    import entrega_rev02 as E
    with pytest.raises(ValueError, match="20 pes"):
        E.gerar(str(tmp_path), P.novo_spec("1AA"))


def test_modelo_3d_recusa_outro_numero_de_apoios(tmp_path):
    import ifc_tanque
    with pytest.raises(NotImplementedError, match="3 apoios por lado"):
        ifc_tanque.emitir(str(tmp_path / "x.ifc"), P.novo_spec("1AA"))
