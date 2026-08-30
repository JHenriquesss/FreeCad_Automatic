"""Hidraulica da casa: agua fria, esgoto/ventilacao e pluvial (branch G4).

Os valores de tabela conferidos aqui sao os de hidraulica_predial (NBR
5626:2020 Tab.B.4 / NBR 8160 Tab.3, 5, 6, 7, 8, D.1 / NBR 10844 Tab.3, 4),
ja aferidos contra os PDFs. O que este arquivo cobre e' a COMPOSICAO
residencial e as flags de saturacao.
"""

import copy

import pytest

import hidraulica_predial as hp
import hidraulica_residencial as hr


def _casa():
    return {
        "aparelhos_agua": {"bacia_caixa": 1, "chuveiro": 1, "lavatorio": 1,
                           "pia": 1, "tanque": 1},
        "aparelhos_esgoto": {"bacia": 1, "chuveiro": 1, "lavatorio": 1,
                             "pia": 1, "tanque": 1},
        "agua": {"L_real_m": 18.0, "p_alim_kPa": 120.0,
                 "conexoes": {"cotovelo_90": 6, "te_direta": 2}},
        "cobertura": {"area_m2": 90.0, "n_condutores": 2, "i_mm_h": 150.0},
    }


# --- agua fria -------------------------------------------------------------

def test_agua_fria_soma_das_vazoes_de_projeto():
    """Tab.B.4: 0,96 + 0,20 + 0,15 + 0,25 + 0,25 = 1,81 L/s."""
    r = hr.rodar(_casa())
    agua = r["redes"]["agua_fria"]
    assert agua["Q_Ls"] == pytest.approx(1.81)
    assert agua["v_real_ms"] <= agua["v_max_ms"]
    assert r["gates"]["agua_velocidade"]["OK"] is True


def test_metodo_dos_pesos_da_diametro_menor_que_a_soma():
    casa = _casa()
    soma = hr.rodar(casa)["redes"]["agua_fria"]
    casa["metodo_agua"] = "pesos"
    pesos = hr.rodar(casa)["redes"]["agua_fria"]
    assert pesos["Q_Ls"] < soma["Q_Ls"]
    assert pesos["DN_mm"] <= soma["DN_mm"]
    assert pesos["metodo"] == "pesos"


def test_pressao_com_p_alim_assumida_e_gate_informativo():
    casa = _casa()
    casa["agua"].pop("p_alim_kPa")
    r = hr.rodar(casa)
    assert r["gates"]["agua_pressao"]["p_alim_assumida"] is True
    assert "p_alim_assumida" in [a["code"] for a in r["avisos"]]


def test_pressao_insuficiente_reprova_quando_p_alim_e_declarada():
    casa = _casa()
    casa["agua"]["p_alim_kPa"] = 12.0        # rede fraca declarada pelo projeto
    casa["agua"]["L_real_m"] = 40.0
    r = hr.rodar(casa)
    assert r["gates"]["agua_pressao"]["OK"] is False
    assert "agua_pressao" in r["reprovados"]


def test_percurso_de_agua_nao_e_inventado():
    casa = _casa()
    casa["agua"].pop("L_real_m")
    r = hr.rodar(casa)
    assert "comprimento_agua_ausente" in [e["code"] for e in r["erros"]]
    assert r["ATENDE"] is False


def test_valvula_de_descarga_eleva_a_pressao_minima_exigida():
    casa = _casa()
    casa["aparelhos_agua"] = {"bacia_valvula": 1, "lavatorio": 1}
    r = hr.rodar(casa)
    assert r["redes"]["agua_fria"]["pressao"]["tipo_ponto"] == "valvula_descarga"
    assert r["redes"]["agua_fria"]["pressao"]["p_min_kPa"] == 15.0


# --- esgoto e ventilacao ---------------------------------------------------

def test_uhc_e_diametros_do_esgoto():
    """Tab.3: bacia 6 + chuveiro 2 + lavatorio 1 + pia 3 + tanque 3 = 15 UHC.
    Tab.5 daria DN75, mas o DN minimo de descarga da bacia (Tab.3) e' 100."""
    r = hr.rodar(_casa())
    esgoto = r["redes"]["esgoto"]
    assert esgoto["uhc"] == 15
    assert esgoto["dn_ramal_descarga_min_mm"] == 100
    assert esgoto["ramal_DN_mm"] == 100
    assert esgoto["coletor_DN_mm"] == 100        # Tab.7: coletor predial >= DN100


def test_ventilacao_usa_a_coluna_com_bacias():
    """Tab.8 com bacias: ate 17 UHC -> DN50. A coluna 'sem bacias' e' menos
    exigente (ate 12 UHC -> DN40): as duas colunas tem que sair diferentes."""
    com = hp.diametro_ramal_ventilacao_sat(10, com_bacia=True)
    sem = hp.diametro_ramal_ventilacao_sat(10, com_bacia=False)
    assert (com["DN_mm"], sem["DN_mm"]) == (50, 40)
    r = hr.rodar(_casa())
    assert r["redes"]["esgoto"]["com_bacia"] is True
    assert r["redes"]["esgoto"]["ventilacao_ramal_DN_mm"] == 50
    assert r["redes"]["esgoto"]["ventilacao_coluna_DN_mm"] == 50   # Tab.D.1


def test_casa_terrea_nao_tem_tubo_de_queda():
    r = hr.rodar(_casa())
    assert "tubo_queda_DN_mm" not in r["redes"]["esgoto"]


def test_sobrado_dimensiona_tubo_de_queda():
    casa = _casa()
    casa["pavimentos"] = 2
    r = hr.rodar(casa)
    assert r["redes"]["esgoto"]["tubo_queda_DN_mm"] == 75    # Tab.6: 15 UHC <= 30


def test_declividade_abaixo_do_minimo_do_coletor_reprova():
    casa = _casa()
    casa["decl_esgoto_pct"] = 0.5      # DN>=100 exige 1 % (Sec.4.2.3.2)
    r = hr.rodar(casa)
    assert "declividade_esgoto_invalida" in [e["code"] for e in r["erros"]]
    assert r["ATENDE"] is False


# --- saturacao silenciosa --------------------------------------------------

def test_ventilacao_saturada_nao_passa_em_silencio():
    """Tab.8 termina em DN75 (60 UHC com bacias). Antes o DN75 saia igual para
    60 e para 600 UHC, com OK=True."""
    casa = _casa()
    casa["aparelhos_esgoto"] = {"bacia": 20, "pia": 10}   # 120 + 30 = 150 UHC
    r = hr.rodar(casa)
    assert r["redes"]["esgoto"]["ventilacao_saturada"] is True
    assert r["gates"]["esgoto_saturacao"]["OK"] is False
    assert "esgoto_saturacao" in r["reprovados"]
    assert r["ATENDE"] is False
    assert "SATURADO" in r["dimensionamento"]


def test_ramal_de_esgoto_saturado_e_sinalizado():
    """Tab.5 termina em 160 UHC (DN100)."""
    saturado = hp.diametro_ramal_esgoto_sat(200, 40)
    assert (saturado["DN_mm"], saturado["saturado"]) == (100, True)
    assert hp.diametro_ramal_esgoto_sat(160, 40)["saturado"] is False


def test_coletor_saturado_e_sinalizado():
    """Tab.7 a 1 %: a maior linha e' DN400 com 8300 UHC."""
    assert hp.diametro_coletor_sat(8300, 1.0)["saturado"] is False
    estourado = hp.diametro_coletor_sat(9000, 1.0)
    assert (estourado["DN_mm"], estourado["saturado"]) == (400, True)


def test_api_antiga_de_diametro_continua_devolvendo_o_dn():
    """As funcoes originais seguem existindo para o galpao (compatibilidade)."""
    assert hp.diametro_coletor(15, 1.0) == 100
    assert hp.diametro_ramal_esgoto(15, 100) == 100
    assert hp.diametro_ramal_ventilacao(15, com_bacia=True) == 50
    assert hp.diametro_tubo_queda(15, 3) == 75


def test_pluvial_saturado_reprova():
    casa = _casa()
    casa["cobertura"] = {"area_m2": 100000.0, "n_condutores": 1, "i_mm_h": 150.0}
    r = hr.rodar(casa)
    assert r["gates"]["pluvial_saturacao"]["OK"] is False
    assert r["ATENDE"] is False


# --- pluvial ---------------------------------------------------------------

def test_pluvial_divide_a_cobertura_pelos_pontos_de_descida():
    casa = _casa()
    r_dois = hr.rodar(casa)
    casa["cobertura"]["n_condutores"] = 1
    r_um = hr.rodar(casa)
    assert (r_dois["redes"]["pluvial"]["area_por_ponto_m2"] * 2
            == pytest.approx(r_dois["redes"]["pluvial"]["area_m2"]))
    assert r_um["redes"]["pluvial"]["Q_Lmin"] > r_dois["redes"]["pluvial"]["Q_Lmin"]


def test_intensidade_declarada_nao_e_marcada_como_assumida():
    """i=150 mm/h CONFIRMADO pelo projeto nao pode virar [A CONFIRMAR] so por
    coincidir com o valor padrao."""
    r = hr.rodar(_casa())
    assert r["redes"]["pluvial"]["i_default"] is False
    assert "intensidade_pluvial_assumida" not in [a["code"] for a in r["avisos"]]


def test_intensidade_ausente_e_flagada():
    casa = _casa()
    casa["cobertura"].pop("i_mm_h")
    r = hr.rodar(casa)
    assert r["redes"]["pluvial"]["i_default"] is True
    assert "intensidade_pluvial_assumida" in [a["code"] for a in r["avisos"]]
    assert "A CONFIRMAR" in r["dimensionamento"]


def test_cobertura_ausente_bloqueia():
    casa = _casa()
    casa.pop("cobertura")
    r = hr.rodar(casa)
    assert "area_cobertura_ausente" in [e["code"] for e in r["erros"]]
    assert r["ATENDE"] is False


# --- honestidade -----------------------------------------------------------

def test_sem_aparelhos_nao_ha_diametro_default():
    """Diferenca deliberada em relacao ao galpao: uma casa sem aparelhos fica
    bloqueada, nunca com um DN comercial que parece dimensionado."""
    r = hr.rodar({"cobertura": {"area_m2": 90.0}})
    codigos = [e["code"] for e in r["erros"]]
    assert "aparelhos_agua_ausentes" in codigos
    assert "aparelhos_esgoto_ausentes" in codigos
    assert "agua_fria" not in r["redes"]
    assert "esgoto" not in r["redes"]
    assert r["ATENDE"] is False


def test_aparelho_desconhecido_nao_e_ignorado():
    casa = _casa()
    casa["aparelhos_esgoto"]["jacuzzi_espacial"] = 1
    r = hr.rodar(casa)
    assert "aparelhos_esgoto_invalidos" in [e["code"] for e in r["erros"]]
    assert r["ATENDE"] is False


def test_ambiente_molhado_sem_aparelho_e_lacuna():
    r = hr.rodar({
        "ambientes": [{"nome": "Banheiro", "tipo": "banheiro"},
                      {"nome": "Sala", "tipo": "sala"}],
        "cobertura": {"area_m2": 90.0, "i_mm_h": 150.0},
    })
    codigos = [e["code"] for e in r["erros"]]
    assert "ambientes_molhados_sem_aparelho" in codigos


def test_escopo_nao_reivindica_aprovacao():
    r = hr.rodar(_casa())
    assert r["escopo"]["aprovacao_concessionaria"] == "not_claimed"
    assert r["escopo"]["construction_readiness"] == "not_claimed"


def test_casa_bem_formada_atende():
    r = hr.rodar(_casa())
    assert r["ATENDE"] is True, r["reprovados"]
    assert r["erros"] == []


def test_stateless_nao_muta_a_entrada():
    casa = _casa()
    antes = copy.deepcopy(casa)
    hr.rodar(casa)
    assert casa == antes
