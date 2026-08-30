"""Vento por pavimento, desaprumo e gamma_z do edificio multipavimento.

Fecha os tres primeiros itens abertos da secao 10 do REVISAO-G3: ate aqui a
descida de cargas era GRAVITACIONAL e nada alimentava o gamma_z com uma analise
de multiplos pavimentos.

Clausulas conferidas no acervo (NBR 6118:2014 + Emenda 1:2026 e NBR 6123:1988),
nao de memoria:
  11.3.3.4.1  theta_1 = 1/(100 raiz(H)), theta_1min = 1/300, theta_1max = 1/200,
              theta_a = theta_1 raiz((1 + 1/n)/2); lajes lisas -> theta_a = theta_1;
              regra a/b/c dos 30 % entre vento e desaprumo;
  15.5.3      gamma_z = 1/(1 - dMtot,d/M1tot,d), valido para >= 4 andares,
              nos fixos se gamma_z <= 1,1;
  15.7.2      majoracao 0,95 gamma_z, SO valida para gamma_z <= 1,3;
  15.7.3      (EI)sec: 0,8 Ec Ic pilares, 0,4 Ec Ic vigas (As' != As);
  15.5.1      Ec = 1,10 Ecs na analise global.
"""

import math

import pytest

import estabilidade_edificio as ee


PE = 2.90
VAOS_X = [5.0, 4.0, 5.0]
VAOS_Y = [4.5, 4.5]
N_PAV = 9
H_TOTAL = N_PAV * PE          # 26,10 m


def _spec(**kw):
    base = {
        "geometria": {"vaos_x": list(VAOS_X), "vaos_y": list(VAOS_Y),
                      "pe_direito": PE},
        "n_pavimentos": N_PAV,
        "materiais": {"fck": 30e3},
        "secoes": {"pilar": {"b": 0.20, "h": 0.50},
                   "viga": {"b": 0.20, "h": 0.50}},
        # carga vertical CARACTERISTICA por pavimento (kN), da descida
        "cargas_verticais_kN": [1200.0] * N_PAV,
        "vento": {"v0": 40.0, "cat": "IV", "classe": "B", "s1": 1.0, "s3": 1.0,
                  # Ca e' ABACO (NBR 6123 Fig.4): entrada declarada, nao derivada
                  "ca": {"x": 1.15, "y": 1.30}},
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# desaprumo (11.3.3.4.1)
# ---------------------------------------------------------------------------
def test_theta1_e_o_inverso_de_cem_vezes_a_raiz_de_H():
    """H = 6,25 m cai entre os dois limites: 1/(100*2,5) = 1/250."""
    r = ee.desaprumo(H=6.25, n_prumadas=4)
    assert r["theta_1"] == pytest.approx(1.0 / 250.0, rel=1e-9)


def test_theta1_satura_no_maximo_de_um_duzentos_avos():
    """H < 4 m -> 1/(100 raiz(H)) > 1/200. Tem de PARAR em 1/200 e DIZER."""
    r = ee.desaprumo(H=2.25, n_prumadas=4)
    assert r["theta_1"] == pytest.approx(1.0 / 200.0, rel=1e-9)
    assert r["saturou"] == "theta_1max"


def test_theta1_satura_no_minimo_de_um_trezentos_avos():
    """H > 9 m -> 1/(100 raiz(H)) < 1/300. O predio de 26,10 m cai aqui."""
    r = ee.desaprumo(H=H_TOTAL, n_prumadas=4)
    assert r["theta_1"] == pytest.approx(1.0 / 300.0, rel=1e-9)
    assert r["saturou"] == "theta_1min"


def test_a_saturacao_nao_e_silenciosa():
    """Padrao recorrente do framework: saturar e devolver OK e' bug."""
    livre = ee.desaprumo(H=6.25, n_prumadas=4)
    assert livre["saturou"] is None


def test_theta_a_reduz_theta_1_pelo_numero_de_prumadas():
    r = ee.desaprumo(H=6.25, n_prumadas=4)
    esperado = (1.0 / 250.0) * math.sqrt((1.0 + 1.0 / 4.0) / 2.0)
    assert r["theta_a"] == pytest.approx(esperado, rel=1e-9)


def test_laje_lisa_usa_theta_a_igual_a_theta_1():
    """'Para edificios com predominancia de lajes lisas ou cogumelo, theta_a = theta_1'."""
    r = ee.desaprumo(H=6.25, n_prumadas=4, lajes_lisas=True)
    assert r["theta_a"] == pytest.approx(r["theta_1"], rel=1e-9)


def test_a_comparacao_com_o_vento_usa_theta_a_sem_theta_1min():
    """'...com desaprumo calculado com theta_a, SEM a consideracao do theta_1min'."""
    r = ee.desaprumo(H=H_TOTAL, n_prumadas=4)
    assert r["theta_a_comparacao"] < r["theta_a"]
    bruto = 1.0 / (100.0 * math.sqrt(H_TOTAL))
    assert r["theta_a_comparacao"] == pytest.approx(
        bruto * math.sqrt((1.0 + 1.0 / 4.0) / 2.0), rel=1e-9)


def test_a_forca_de_desaprumo_e_theta_a_vezes_a_carga_do_pavimento():
    r = ee.desaprumo(H=H_TOTAL, n_prumadas=4, cargas_kN=[1000.0, 800.0])
    assert r["forcas_kN"][0] == pytest.approx(r["theta_a"] * 1000.0, rel=1e-9)
    assert r["forcas_kN"][1] == pytest.approx(r["theta_a"] * 800.0, rel=1e-9)


# ---------------------------------------------------------------------------
# vento por pavimento (NBR 6123)
# ---------------------------------------------------------------------------
def test_a_pressao_cresce_com_a_altura():
    """S2 cresce com z, entao q cresce monotonicamente do 1o ao ultimo piso."""
    r = ee.vento_por_pavimento(_spec(), direcao="x")
    q = [p["q_kN_m2"] for p in r["pavimentos"]]
    assert q == sorted(q) and q[-1] > q[0]
    assert all(p["Fa_kN"] > 0 for p in r["pavimentos"])


def test_a_forca_por_m2_cresce_mas_a_do_topo_cai_pela_meia_faixa():
    """O ultimo pavimento tem metade da altura tributaria: a forca dele e' MENOR
    que a do primeiro apesar da pressao maior. Conferir a forca crua aqui
    esconderia um erro de area atras de um erro de pressao."""
    r = ee.vento_por_pavimento(_spec(), direcao="x")
    prim, ult = r["pavimentos"][0], r["pavimentos"][-1]
    assert ult["Fa_kN"] / ult["Ae_m2"] > prim["Fa_kN"] / prim["Ae_m2"]
    assert ult["h_trib_m"] == pytest.approx(PE / 2.0)
    assert ult["Fa_kN"] < prim["Fa_kN"]


def test_a_area_frontal_total_desconta_o_meio_pe_direito_da_base():
    """A meia-altura inferior vai direto para a fundacao, nao para um pavimento."""
    r = ee.vento_por_pavimento(_spec(), direcao="x")
    total = sum(p["Ae_m2"] for p in r["pavimentos"])
    l1 = sum(VAOS_Y)
    assert total == pytest.approx(l1 * (H_TOTAL - PE / 2.0), rel=1e-9)


def test_a_largura_frontal_troca_com_a_direcao_do_vento():
    """l1 e' a dimensao PERPENDICULAR ao vento (NBR 6123 2.2)."""
    rx = ee.vento_por_pavimento(_spec(), direcao="x")
    ry = ee.vento_por_pavimento(_spec(), direcao="y")
    assert rx["l1_m"] == pytest.approx(sum(VAOS_Y))
    assert ry["l1_m"] == pytest.approx(sum(VAOS_X))


def test_o_ca_e_entrada_declarada_e_nao_derivada_de_abaco():
    """NBR 6123 Fig.4 e' GRAFICO. Sem ca declarado, REPROVA - nao chuta."""
    spec = _spec()
    del spec["vento"]["ca"]
    with pytest.raises(ValueError, match="ca"):
        ee.vento_por_pavimento(spec, direcao="x")


def test_a_proveniencia_do_ca_fica_registrada():
    r = ee.vento_por_pavimento(_spec(), direcao="x")
    assert r["ca_proveniencia"] == "declarado"
    assert "Figura 4" in r["ca_fonte"]


# ---------------------------------------------------------------------------
# regra a/b/c dos 30 % (11.3.3.4.1)
# ---------------------------------------------------------------------------
def test_vento_dominante_dispensa_o_desaprumo():
    """a) 30 % do vento > desaprumo -> so vento."""
    r = ee.combina_vento_desaprumo(M_vento=1000.0, M_desaprumo=100.0)
    assert r["caso"] == "a"
    assert r["usar"] == "vento"
    assert r["M_kNm"] == pytest.approx(1000.0)


def test_desaprumo_dominante_dispensa_o_vento():
    """b) vento < 30 % do desaprumo -> so desaprumo, COM theta_1min."""
    r = ee.combina_vento_desaprumo(M_vento=20.0, M_desaprumo=1000.0)
    assert r["caso"] == "b"
    assert r["usar"] == "desaprumo"
    assert r["aplica_theta_1min"] is True


def test_no_caso_intermediario_as_duas_acoes_se_somam():
    """c) combina, SEM theta_1min."""
    r = ee.combina_vento_desaprumo(M_vento=300.0, M_desaprumo=500.0)
    assert r["caso"] == "c"
    assert r["usar"] == "combinado"
    assert r["aplica_theta_1min"] is False
    assert r["M_kNm"] == pytest.approx(800.0)


def test_a_fronteira_dos_trinta_por_cento_e_estrita():
    """30 % do vento IGUAL ao desaprumo nao e' 'maior que' -> cai no caso c."""
    r = ee.combina_vento_desaprumo(M_vento=1000.0, M_desaprumo=300.0)
    assert r["caso"] == "c"


# ---------------------------------------------------------------------------
# gamma_z (15.5.3 / 15.7.2 / 15.7.3)
# ---------------------------------------------------------------------------
def test_gamma_z_sai_de_uma_analise_de_portico_de_verdade():
    r = ee.verifica(_spec())
    gz = r["gamma_z"]
    assert 1.0 < gz["gamma_z"] < 1.3, gz
    assert gz["dM_tot_d_kNm"] > 0 and gz["M1_tot_d_kNm"] > 0
    assert gz["deslocamento_topo_m"] > 0


def test_a_rigidez_usa_os_coeficientes_de_15_7_3():
    r = ee.verifica(_spec())
    rig = r["gamma_z"]["rigidez"]
    assert rig["pilar"] == pytest.approx(0.8)
    assert rig["viga"] == pytest.approx(0.4)
    assert rig["majoracao_Ecs"] == pytest.approx(1.10)


def test_gamma_z_exige_quatro_andares():
    """15.5.3: 'valido para estruturas reticuladas de no minimo quatro andares'."""
    r = ee.verifica(_spec(n_pavimentos=3, cargas_verticais_kN=[1200.0] * 3))
    assert r["gamma_z"]["aplicavel"] is False
    assert "quatro" in r["gamma_z"]["motivo"]


def test_acima_de_um_virgula_tres_o_processo_simplificado_REPROVA():
    """15.7.2 so vale para gamma_z <= 1,3. Passar disso nao pode virar OK."""
    r = ee.classifica_gamma_z(1.45)
    assert r["OK"] is False
    assert r["majorador"] is None
    assert "P-Delta" in r["motivo"] or "1,3" in r["motivo"]


def test_ate_um_virgula_um_a_estrutura_e_de_nos_fixos():
    r = ee.classifica_gamma_z(1.05)
    assert r["nos"] == "fixos"
    assert r["majorador"] == pytest.approx(1.0)


def test_entre_um_virgula_um_e_um_virgula_tres_majora_por_095_gamma_z():
    r = ee.classifica_gamma_z(1.20)
    assert r["nos"] == "moveis"
    assert r["majorador"] == pytest.approx(0.95 * 1.20)


# ---------------------------------------------------------------------------
# gate consolidado
# ---------------------------------------------------------------------------
def test_o_gate_cobre_as_duas_direcoes():
    r = ee.verifica(_spec())
    assert set(r["direcoes"]) == {"x", "y"}
    for d in ("x", "y"):
        assert r["por_direcao"][d]["gamma_z"] > 1.0


def test_o_gate_reprova_entrada_degenerada():
    with pytest.raises(ValueError):
        ee.verifica(_spec(cargas_verticais_kN=[0.0] * N_PAV))


# ---------------------------------------------------------------------------
# ELS - movimento lateral (13.3 / Tabela 13.3)
# ---------------------------------------------------------------------------
def test_o_els_usa_secao_bruta_e_nao_a_rigidez_reduzida_do_elu():
    """15.7.3 e' EXCLUSIVA da 2a ordem no ELU; o ELS usa Ecs com secao bruta
    (14.6.4.1). Usar 0,4/0,8 aqui dobraria o deslocamento sem amparo."""
    r = ee.verifica(_spec())
    els = r["por_direcao"]["y"]["els"]
    assert els["secao"] == "bruta"
    assert els["Ecs_kN_m2"] == pytest.approx(
        r["por_direcao"]["y"]["detalhe_gamma_z"]["Ecs_kN_m2"])
    # o ELU majora Ecs em 10 %; o ELS nao
    assert els["Ecs_kN_m2"] < r["por_direcao"]["y"]["detalhe_gamma_z"]["Ec_kN_m2"]


def test_o_els_usa_a_combinacao_frequente_com_psi1_de_030():
    r = ee.verifica(_spec())
    assert r["por_direcao"]["x"]["els"]["psi_1"] == pytest.approx(0.30)


def test_os_limites_sao_H_por_1700_e_Hi_por_850():
    r = ee.verifica(_spec())
    els = r["por_direcao"]["x"]["els"]
    assert els["limite_topo_m"] == pytest.approx(H_TOTAL / 1700.0)
    assert els["limite_entre_m"] == pytest.approx(PE / 850.0)


def test_o_drift_entre_pavimentos_soma_o_deslocamento_do_topo():
    """Conferencia de fechamento: a soma dos drifts tem de dar o topo."""
    r = ee.verifica(_spec())
    els = r["por_direcao"]["y"]["els"]
    assert sum(els["drift_entre_pavimentos_m"]) == pytest.approx(
        els["u_topo_m"], rel=1e-9)


def test_o_els_entra_no_gate_consolidado():
    """Sem isto o gamma_z sozinho declararia OK um predio que balanca demais -
    foi assim que a longarina passou sem ELS."""
    r = ee.verifica(_spec())
    assert "els_OK" in r
    assert r["OK"] == (r["gamma_z"]["majorador"] is not None and r["els_OK"])
