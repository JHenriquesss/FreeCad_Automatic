"""Programa de ambientes + previsao de carga NBR 5410 9.5.2 (branch G4).

Os numeros conferidos aqui vieram da transcricao literal da NBR 5410:2004
(notebook 78cd2efd, fonte d213019d) registrada no design
docs/superpowers/specs/2026-08-29-g4-adaptador-casa-residencial-real.md.
"""

import copy
import math

import pytest

import arquitetura_residencial as ar


def _casa():
    return {
        "ambientes": [
            {"nome": "Sala", "tipo": "sala", "largura_m": 4.0, "comprimento_m": 5.0},
            {"nome": "Dormitorio 1", "tipo": "dormitorio",
             "largura_m": 3.0, "comprimento_m": 3.5},
            {"nome": "Cozinha", "tipo": "cozinha", "largura_m": 2.5,
             "comprimento_m": 3.6},
            {"nome": "Banheiro", "tipo": "banheiro", "largura_m": 1.5,
             "comprimento_m": 2.4},
            {"nome": "Circulacao", "tipo": "circulacao", "largura_m": 1.0,
             "comprimento_m": 2.0},
        ],
        "pe_direito_m": 2.7,
    }


# --- 9.5.2.1.2 carga de iluminacao ----------------------------------------

@pytest.mark.parametrize("area,esperado", [
    (2.0, 100.0),      # a) area <= 6 m2 -> 100 VA
    (6.0, 100.0),      # a) limite inclusivo
    (6.5, 100.0),      # b) so ha 0,5 m2 excedente: nenhum bloco de 4 m2 inteiro
    (10.0, 160.0),     # b) 6 + 4 -> 100 + 60
    (13.9, 160.0),     # b) 7,9 excedentes -> ainda 1 bloco inteiro
    (14.0, 220.0),     # b) 8 excedentes -> 2 blocos
    (20.0, 280.0),     # b) 14 excedentes -> 3 blocos
])
def test_carga_iluminacao_951212(area, esperado):
    assert ar.carga_iluminacao_va(area) == esperado


def test_todo_ambiente_tem_ponto_de_luz_no_teto():
    """9.5.2.1.1: pelo menos um ponto de luz fixo no teto por comodo."""
    r = ar.rodar(_casa())
    assert all(a["n_pontos_luz_min"] >= 1 for a in r["ambientes"])


# --- 9.5.2.2.1 numero de pontos de tomada ---------------------------------

def test_cozinha_usa_perimetro_de_3_5_m():
    """b) 1 ponto/3,5 m ou fracao. 2,5x3,6 -> perimetro 12,2 -> ceil(12,2/3,5)=4."""
    r = ar.rodar(_casa())
    cozinha = next(a for a in r["ambientes"] if a["tipo"] == "cozinha")
    assert cozinha["perimetro_m"] == pytest.approx(12.2)
    assert cozinha["criterio_tomadas"] == "9.5.2.2.1-b"
    assert cozinha["n_tomadas_min"] == 4


def test_sala_e_dormitorio_usam_perimetro_de_5_m():
    """d) 1 ponto/5 m ou fracao. Sala 4x5 -> 18 m -> ceil(18/5)=4;
    dormitorio 3x3,5 -> 13 m -> ceil(13/5)=3."""
    r = ar.rodar(_casa())
    sala = next(a for a in r["ambientes"] if a["tipo"] == "sala")
    dorm = next(a for a in r["ambientes"] if a["tipo"] == "dormitorio")
    assert (sala["criterio_tomadas"], sala["n_tomadas_min"]) == ("9.5.2.2.1-d", 4)
    assert (dorm["criterio_tomadas"], dorm["n_tomadas_min"]) == ("9.5.2.2.1-d", 3)


def test_banheiro_tem_um_ponto_junto_ao_lavatorio():
    r = ar.rodar(_casa())
    banho = next(a for a in r["ambientes"] if a["tipo"] == "banheiro")
    assert banho["criterio_tomadas"] == "9.5.2.2.1-a"
    assert banho["n_tomadas_min"] == 1
    assert any("9.1" in nota for nota in banho["notas"])


def test_varanda_tem_pelo_menos_um_ponto():
    r = ar.rodar({"ambientes": [
        {"nome": "Varanda", "tipo": "varanda", "largura_m": 1.2,
         "comprimento_m": 6.0}]})
    varanda = r["ambientes"][0]
    assert (varanda["criterio_tomadas"], varanda["n_tomadas_min"]) == ("9.5.2.2.1-c", 1)


@pytest.mark.parametrize("largura,comprimento,esperado", [
    (1.0, 2.0, 1),      # e) area 2,0 <= 2,25 m2 -> 1 ponto
    (1.5, 3.0, 1),      # e) 2,25 < 4,5 <= 6 m2 -> 1 ponto
    (2.5, 4.0, 3),      # e) area 10 > 6 -> perimetro 13 -> ceil(13/5) = 3
])
def test_demais_comodos_seguem_alinea_e(largura, comprimento, esperado):
    r = ar.rodar({"ambientes": [
        {"nome": "Escritorio", "tipo": "escritorio", "largura_m": largura,
         "comprimento_m": comprimento}]})
    comodo = r["ambientes"][0]
    assert comodo["criterio_tomadas"].startswith("9.5.2.2.1-e")
    assert comodo["n_tomadas_min"] == esperado


# --- 9.5.2.2.2 potencias atribuiveis --------------------------------------

def test_ambiente_molhado_600_va_ate_tres_pontos():
    """a) 600 VA ate tres pontos, 100 VA para os excedentes. Cozinha com 4
    pontos -> 3*600 + 1*100 = 1900 VA."""
    r = ar.rodar(_casa())
    cozinha = next(a for a in r["ambientes"] if a["tipo"] == "cozinha")
    assert cozinha["carga_tomadas_va"] == 1900.0


def test_alternativa_de_dois_pontos_nao_e_adotada_em_silencio():
    """A regra dos dois pontos e' uma PERMISSAO (quando o conjunto molhado
    passa de seis pontos). O calculo padrao continua sendo o de tres pontos;
    a alternativa aparece como campo separado e sinalizado."""
    casa = _casa()
    casa["ambientes"].append({"nome": "Area de servico", "tipo": "area_servico",
                              "largura_m": 2.0, "comprimento_m": 3.0})
    r = ar.rodar(casa)
    cozinha = next(a for a in r["ambientes"] if a["tipo"] == "cozinha")
    assert r["totais"]["pontos_molhados"] > 6
    assert r["totais"]["alternativa_9_5_2_2_2_disponivel"] is True
    assert cozinha["carga_tomadas_va"] == 1900.0                  # criterio padrao
    assert cozinha["carga_tomadas_va_alternativa"] == 1400.0      # 2*600 + 2*100
    assert (r["totais"]["carga_tomadas_va_alternativa"]
            < r["totais"]["carga_tomadas_va"])


def test_ambiente_seco_100_va_por_ponto():
    r = ar.rodar(_casa())
    sala = next(a for a in r["ambientes"] if a["tipo"] == "sala")
    assert sala["carga_tomadas_va"] == 400.0     # 4 pontos x 100 VA


def test_totais_fecham_com_a_soma_dos_ambientes():
    r = ar.rodar(_casa())
    assert r["totais"]["carga_iluminacao_va"] == pytest.approx(
        sum(a["carga_iluminacao_va"] for a in r["ambientes"]))
    assert r["totais"]["carga_tomadas_va"] == pytest.approx(
        sum(a["carga_tomadas_va"] for a in r["ambientes"]))
    assert r["totais"]["area_util_m2"] == pytest.approx(
        sum(a["area_m2"] for a in r["ambientes"]))


# --- rotulo x geometria ----------------------------------------------------

def test_perimetro_declarado_menor_que_o_isoperimetrico_e_reprovado():
    """Um comodo de 12 m2 nao pode ter 10 m de perimetro: o minimo geometrico
    e' o do quadrado, 4*raiz(12) = 13,86 m. Sem esta checagem o numero de
    tomadas sairia de uma planta que nao existe."""
    r = ar.rodar({"ambientes": [
        {"nome": "Impossivel", "tipo": "sala", "area_m2": 12.0,
         "perimetro_m": 10.0}]})
    assert r["ATENDE"] is False
    assert "geometria" in r["reprovados"]
    codigos = [e["code"] for e in r["erros"]]
    assert "perimetro_incompativel_com_area" in codigos


def test_perimetro_igual_ao_quadrado_e_aceito():
    lado = 3.0
    r = ar.rodar({"ambientes": [
        {"nome": "Quadrado", "tipo": "sala", "area_m2": lado * lado,
         "perimetro_m": 4 * lado}]})
    assert r["ATENDE"] is True


def test_area_e_perimetro_declarados_conferem_com_largura_e_comprimento():
    r = ar.rodar({"ambientes": [
        {"nome": "Divergente", "tipo": "sala", "largura_m": 3.0,
         "comprimento_m": 4.0, "area_m2": 20.0}]})
    assert r["ATENDE"] is False
    assert "area_declarada_diverge_da_geometria" in [e["code"] for e in r["erros"]]


@pytest.mark.parametrize("campo,valor", [
    ("largura_m", 0.0), ("largura_m", -1.0), ("comprimento_m", 0.0),
    ("largura_m", float("nan")), ("comprimento_m", float("inf")),
])
def test_geometria_degenerada_reprova(campo, valor):
    amb = {"nome": "X", "tipo": "sala", "largura_m": 3.0, "comprimento_m": 4.0}
    amb[campo] = valor
    r = ar.rodar({"ambientes": [amb]})
    assert r["ATENDE"] is False


def test_ambiente_sem_geometria_reprova_sem_inventar_numero():
    r = ar.rodar({"ambientes": [{"nome": "Sem medida", "tipo": "sala"}]})
    assert r["ATENDE"] is False
    assert "geometria_ausente" in [e["code"] for e in r["erros"]]
    assert r["ambientes"][0]["n_tomadas_min"] is None
    assert r["ambientes"][0]["carga_iluminacao_va"] is None


def test_programa_vazio_reprova():
    r = ar.rodar({"ambientes": []})
    assert r["ATENDE"] is False
    assert "programa_vazio" in [e["code"] for e in r["erros"]]


# --- honestidade -----------------------------------------------------------

def test_tipo_desconhecido_cai_na_alinea_e_com_aviso_explicito():
    r = ar.rodar({"ambientes": [
        {"nome": "Atelie", "tipo": "atelie", "largura_m": 3.0,
         "comprimento_m": 4.0}]})
    assert r["ambientes"][0]["criterio_tomadas"].startswith("9.5.2.2.1-e")
    assert "tipo_ambiente_nao_mapeado" in [w["code"] for w in r["avisos"]]


def test_escopo_nao_reivindica_aprovacao_legal():
    r = ar.rodar(_casa())
    assert r["escopo"]["codigo_de_obras"] == "not_evaluated"
    assert r["escopo"]["desempenho_nbr15575"] == "not_evaluated"
    assert r["escopo"]["aprovacao_legal"] == "not_claimed"


def test_casa_bem_formada_atende():
    r = ar.rodar(_casa())
    assert r["ATENDE"] is True
    assert r["reprovados"] == []


def test_stateless_nao_muta_a_entrada():
    casa = _casa()
    antes = copy.deepcopy(casa)
    ar.rodar(casa)
    assert casa == antes


def test_isoperimetrico_limite_exato_nao_reprova_por_arredondamento():
    area = 7.3
    r = ar.rodar({"ambientes": [
        {"nome": "Limite", "tipo": "sala", "area_m2": area,
         "perimetro_m": 4 * math.sqrt(area)}]})
    assert r["ATENDE"] is True


# --- "ou fracao": as bordas exatas ----------------------------------------

@pytest.mark.parametrize("perimetro,passo,esperado", [
    (15.0, 5.0, 3),        # multiplo exato: 3 pontos, nao 4
    (15.001, 5.0, 4),      # qualquer fracao acima ja exige mais um
    (14.999, 5.0, 3),
    (5.0, 5.0, 1),
    (0.5, 5.0, 1),         # minimo de um ponto
    (10.5, 3.5, 3),        # multiplo exato do passo molhado
    (10.51, 3.5, 4),
])
def test_pontos_por_perimetro_na_borda_do_multiplo(perimetro, passo, esperado):
    assert ar._pontos_por_perimetro(perimetro, passo) == esperado


def test_comodo_de_seis_metros_quadrados_fica_na_alinea_a_da_iluminacao():
    """O limite de 9.5.2.1.2 e' inclusivo ('igual ou inferior a 6 m2')."""
    assert ar.carga_iluminacao_va(6.0) == 100.0
    assert ar.carga_iluminacao_va(6.0000001) == 100.0


def test_comodo_de_2_25_m2_fica_no_primeiro_degrau_da_alinea_e():
    """9.5.2.2.1-e: 'igual ou inferior a 2,25 m2' e' o primeiro degrau."""
    no_limite = ar.rodar({"ambientes": [
        {"nome": "Closet", "tipo": "closet", "area_m2": 2.25,
         "perimetro_m": 6.1}]})
    assert no_limite["ambientes"][0]["criterio_tomadas"] == "9.5.2.2.1-e-1"
    acima = ar.rodar({"ambientes": [
        {"nome": "Closet", "tipo": "closet", "area_m2": 2.30,
         "perimetro_m": 6.2}]})
    assert acima["ambientes"][0]["criterio_tomadas"] == "9.5.2.2.1-e-2"


def test_geometria_contestada_nao_publica_numero_derivado():
    """Se a area declarada diverge de largura x comprimento, o ambiente fica sem
    previsao: publicar um numero tirado de uma planta em disputa e' pior que
    dizer que nao da para calcular."""
    r = ar.rodar({"ambientes": [
        {"nome": "Divergente", "tipo": "sala", "largura_m": 3.0,
         "comprimento_m": 4.0, "area_m2": 20.0}]})
    ambiente = r["ambientes"][0]
    assert ambiente["geometria_ok"] is False
    assert ambiente["area_m2"] is None
    assert ambiente["n_tomadas_min"] is None
    assert ambiente["carga_tomadas_va"] is None
    assert r["totais"]["carga_tomadas_va"] == 0
    assert "ambientes_sem_previsao_de_carga" in [a["code"] for a in r["avisos"]]
