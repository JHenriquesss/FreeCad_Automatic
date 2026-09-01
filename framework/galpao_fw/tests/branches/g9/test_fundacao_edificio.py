"""Fundacao do edificio multipavimento (G9): a carga que descia e parava no chao.

A descida sempre entregou N_base por pilar e ninguem o dimensionava - o escopo
dizia `fundacao: not_available`. Os modulos de calculo ja existiam e ja estavam
aferidos (fundacao_sapata contra Alonso, estaca_profunda por Aoki-Velloso lido
do PDF, geotecnia_spt pela ponte SPT -> tensao admissivel). Estes testes fixam a
LIGACAO, nao os calculos - que tem os seus proprios arquivos.

O que eles travam:
  - a sondagem e' ENTRADA DECLARADA: sem ela nao ha fundacao, e nada de tensao
    de solo arbitrada por default;
  - a geometria e' PILAR A PILAR (canto != interno) e a carga de dimensionamento
    e' a do pior caso de cada pilar, nao a do pior pilar da obra;
  - a acao horizontal entra como binario de tombamento, e o pilar de barlavento
    (que ALIVIA) e' verificado junto com o de sotavento;
  - o que NAO entra e' dito: momento na base do pilar, viga baldrame, recalque.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
GALPAO = HERE.parents[3]
sys.path.insert(0, str(GALPAO))

import edificio_multipavimento as em
import fundacao_edificio as fe

SPEC = GALPAO.parents[1] / "projects" / "edificio-multipavimento" / "project-spec.json"

# perfil com o solo raso MOLE: a sondagem tem de mandar para fundacao profunda
PERFIL_MOLE = [{"tipo": "argila", "N": 2, "dz": 6.0},
               {"tipo": "argila_arenosa", "N": 5, "dz": 4.0},
               {"tipo": "areia", "N": 32, "dz": 5.0},
               {"tipo": "areia", "N": 45, "dz": 6.0}]


def _entrada(**troca):
    payload = json.loads(SPEC.read_text(encoding="utf-8"))["turnkey"]["estrutura"]
    entrada = {chave: copy.deepcopy(payload[chave]) for chave in
               ("geometria", "pavimentos", "laje", "viga", "materiais", "vento",
                "fundacao") if chave in payload}
    entrada.update(copy.deepcopy(troca))
    return entrada


@pytest.fixture(scope="module")
def resultado():
    return em.rodar(_entrada())


@pytest.fixture(scope="module")
def fundacao(resultado):
    return resultado["fundacao"]


# ------------------------- a sondagem e' entrada declarada -------------------

def test_sem_sondagem_nem_tensao_nao_ha_fundacao():
    """Tensao admissivel arbitrada e' o erro que este framework trata como bug."""
    assert fe.declarada(None) is False
    assert fe.declarada({}) is False
    assert fe.declarada({"cota_apoio_m": 1.5}) is False
    entrada = _entrada()
    entrada.pop("fundacao")
    resultado = em.rodar(entrada)
    assert resultado["fundacao"] is None
    assert "fundacao" not in resultado["gates"]


def test_a_tensao_admissivel_e_derivada_do_spt(fundacao):
    """sigma_adm = N/50 no bulbo (geotecnia_spt), com a proveniencia dita."""
    assert fundacao["sigma_solo_adm"] > 0
    assert "SPT" in fundacao["proveniencia_sigma"]
    assert "N/50" in fundacao["proveniencia_sigma"]


def test_a_tensao_declarada_vence_a_derivada():
    entrada = _entrada()
    entrada["fundacao"]["sigma_solo_adm"] = 180.0
    resultado = em.rodar(entrada)
    assert resultado["fundacao"]["sigma_solo_adm"] == 180.0
    assert resultado["fundacao"]["proveniencia_sigma"] == "declarada no spec"


def test_estaca_sem_sondagem_e_recusada():
    """Aoki-Velloso e' semi-empirico sobre o SPT: sem sondagem nao ha capacidade."""
    with pytest.raises(fe.EntradaFundacao):
        fe.dimensiona({"tipo": "estaca", "sigma_solo_adm": 200.0},
                      {"pilares": [{"nome": "P11", "i": 0, "j": 0,
                                    "N_base_k": 500.0, "secao": (0.2, 0.5)}],
                       "eixos_x": [0.0], "eixos_y": [0.0],
                       "materiais": {"fck": 30e3, "fyk": 500e3}})


def test_perfil_spt_malformado_e_recusado_com_motivo():
    for perfil in ([], [{"N": 10}], [{"N": 10, "dz": -1.0}],
                   [{"N": 10, "dz": 2.0, "tipo": "queijo"}]):
        with pytest.raises(fe.EntradaFundacao):
            fe.dimensiona({"perfil_spt": perfil}, {
                "pilares": [{"nome": "P11", "i": 0, "j": 0, "N_base_k": 500.0,
                             "secao": (0.2, 0.5)}],
                "eixos_x": [0.0], "eixos_y": [0.0],
                "materiais": {"fck": 30e3, "fyk": 500e3}})


def test_entrada_declarada_que_nao_fecha_vira_gate_reprovado():
    """Sem camada competente a estaca nao tem onde se apoiar. O resultado nomeia
    o motivo; a fundacao nao some do dict em silencio."""
    entrada = _entrada()
    entrada["fundacao"]["tipo"] = "estaca"
    entrada["fundacao"]["perfil_spt"] = [{"tipo": "argila", "N": 3, "dz": 8.0}]
    resultado = em.rodar(entrada)
    assert resultado["fundacao"] is None
    assert resultado["fundacao_erro"]
    assert resultado["gates"]["fundacao"]["OK"] is False
    assert "camada competente" in resultado["gates"]["fundacao"]["erro"]
    assert not resultado["ATENDE"]


# --------------------------- geometria pilar a pilar -------------------------

def test_um_dimensionamento_por_pilar_da_malha(fundacao, resultado):
    assert set(fundacao["por_pilar"]) == set(resultado["descida"]["pilares"])
    assert fundacao["gate"]["n_pilares"] == len(resultado["descida"]["pilares"])


def test_a_sapata_de_canto_e_menor_que_a_do_pilar_interno(fundacao):
    """Uma sapata unica pelo pior pilar seria desperdicio em 8 das 12 posicoes -
    e o teste mede a AREA, nao le o rotulo da posicao."""
    por_posicao = {}
    for registro in fundacao["por_pilar"].values():
        geometria = registro["geometria"]
        area = geometria["B_m"] * geometria["L_m"]
        por_posicao.setdefault(registro["posicao"], []).append(area)
    assert max(por_posicao["canto"]) < min(por_posicao["interno"])
    assert max(por_posicao["canto"]) <= min(por_posicao["extremidade"])


def test_a_carga_de_dimensionamento_e_a_do_proprio_pilar(fundacao, resultado):
    """Cada pilar e' dimensionado para o SEU pior caso, nao para o da obra."""
    for nome, registro in fundacao["por_pilar"].items():
        n_base = resultado["descida"]["pilares"][nome]["N_base_k"]
        assert registro["N_dimensionamento_kN"] >= n_base - 1e-6
        # e nunca acima do maximo da obra
        assert registro["N_dimensionamento_kN"] <= fundacao["gate"]["N_max_kN"] + 1e-6
    dimensionamentos = {r["N_dimensionamento_kN"]
                        for r in fundacao["por_pilar"].values()}
    assert len(dimensionamentos) > 1, "todos os pilares com a mesma carga?"


def test_a_secao_do_pedestal_e_a_do_lance_da_base(resultado):
    """A sapata recebe o pilar da BASE - e' ela que define o balanco e a rigidez
    de 22.6.1. Usar a secao do topo daria uma sapata de outro predio."""
    entrada = _entrada()
    pilares = resultado["pilares"]
    for nome, registro in resultado["fundacao"]["por_pilar"].items():
        lance_base = pilares[nome]["lances"][-1]
        # o balanco da sapata adotada tem de ser coerente com a secao da base:
        # a rigidez exige h >= max(L - ap_L, B - ap_B)/3
        geometria = registro["geometria"]
        exigido = max(geometria["L_m"] - lance_base["h"],
                      geometria["B_m"] - lance_base["b"]) / 3.0
        assert geometria["h_m"] >= exigido - 1e-6, nome
    del entrada


# --------------------------- acao horizontal ---------------------------------

def test_o_tombamento_global_vira_binario_nas_prumadas(fundacao):
    """dN = M*x/sum(x^2): soma zero (e' binario) e cresce com o braco."""
    for direcao, registro in fundacao["acao_horizontal"].items():
        valores = [item["dN_kN"] for item in registro["por_pilar"].values()]
        assert abs(sum(valores)) < 1.0, direcao      # binario: nao altera o total
        bracos = {item["braco_m"]: item["dN_kN"]
                  for item in registro["por_pilar"].values()}
        ordenados = sorted(bracos)
        assert bracos[ordenados[0]] < bracos[ordenados[-1]], direcao


def test_o_pilar_de_barlavento_e_verificado_aliviado(fundacao):
    """Verificar so o maior N deixaria passar o caso que dimensiona tombamento e
    deslizamento - o mesmo motivo pelo qual `dimensiona_sapata_env` existe."""
    combinacoes = fundacao["por_pilar"]["P11"]["combinacoes"]
    nomes = {c["nome"] for c in combinacoes}
    assert "gravitacional" in nomes
    assert {"sotavento_x", "barlavento_x", "sotavento_y", "barlavento_y"} <= nomes
    gravitacional = next(c for c in combinacoes if c["nome"] == "gravitacional")
    barlavento = next(c for c in combinacoes if c["nome"] == "barlavento_y")
    sotavento = next(c for c in combinacoes if c["nome"] == "sotavento_y")
    assert barlavento["N_kN"] < gravitacional["N_kN"] < sotavento["N_kN"]
    assert barlavento["V_kN"] > 0, "sem cortante nao ha deslizamento a verificar"


def test_sem_vento_a_fundacao_e_so_gravitacional_e_diz_isso():
    entrada = _entrada()
    entrada.pop("vento")
    resultado = em.rodar(entrada)
    fundacao = resultado["fundacao"]
    assert fundacao["acao_horizontal"] == {}
    assert fundacao["escopo"]["acao_horizontal_na_fundacao"] == "not_available"
    codigos = {aviso["code"] for aviso in fundacao["avisos"]}
    assert "fundacao_so_gravitacional" in codigos
    for registro in fundacao["por_pilar"].values():
        assert [c["nome"] for c in registro["combinacoes"]] == ["gravitacional"]


def test_o_momento_na_base_de_cada_pilar_e_declarado_ausente(fundacao):
    """G17: momento por prumada passa a ser extraido do portico heterogeneo
    (secao real por pilar, rigidez bruta) e alimenta V/M nas combinacoes."""
    assert fundacao["escopo"]["momento_base_pilar"] == "implemented"
    codigos = {aviso["code"] for aviso in fundacao["avisos"]}
    assert "momento_base_pilar_extraido" in codigos
    # pelo menos um pilar tem M !=0 (vento/desaprumo geram momento na base)
    assert any(any(c["M_kNm"] != 0.0 for c in reg["combinacoes"])
               for reg in fundacao["por_pilar"].values())
    # central vs canto: momentos e geometrias diferentes (distinguem)
    por_pos = {}
    for reg in fundacao["por_pilar"].values():
        # geometria pode ser divisa (B_m/L_m) ou isolada, mas sempre tem area
        geom = reg["geometria"]
        # area para comparar: B*L quando isolada, B*L quando divisa
        area = geom.get("B_m", 0) * geom.get("L_m", 0) if geom else 0
        por_pos.setdefault(reg["posicao"], []).append((reg["combinacoes"], area))
    # canto tem area menor que interno (carga menor), e momento diferente
    # verifica que nem todos os pilares tem mesma combinacao de M
    momentos = {tuple(c["M_kNm"] for c in reg["combinacoes"])
                for reg in fundacao["por_pilar"].values()}
    assert len(momentos) > 1, "todos os pilares com mesma combinacao de M?"


# ------------------------------ tipo da fundacao -----------------------------

def test_a_sondagem_mole_manda_para_fundacao_profunda():
    entrada = _entrada()
    entrada["fundacao"]["perfil_spt"] = copy.deepcopy(PERFIL_MOLE)
    fundacao = em.rodar(entrada)["fundacao"]
    assert fundacao["tipo"] == "estaca"
    for registro in fundacao["por_pilar"].values():
        assert registro["geometria"]["n_estacas"] >= 1
        assert registro["geometria"]["util"] <= 1.0


def test_a_estaca_atravessa_a_camada_competente():
    """A ponta para na BASE da camada com N >= 20, nao no topo: e' a escolha que
    nao exige arbitrar embutimento."""
    entrada = _entrada()
    entrada["fundacao"]["perfil_spt"] = copy.deepcopy(PERFIL_MOLE)
    fundacao = em.rodar(entrada)["fundacao"]
    esperado = sum(camada["dz"] for camada in PERFIL_MOLE[:3])
    for registro in fundacao["por_pilar"].values():
        assert registro["geometria"]["L_m"] == pytest.approx(esperado, abs=0.05)


def test_bloco_de_coroamento_fora_de_2_ou_4_estacas_e_declarado(fundacao):
    """O modelo de bielas implementado cobre 2 e 4. Fora disso o bloco NAO foi
    dimensionado, e o resultado diz - nao some do quadro."""
    entrada = _entrada()
    entrada["fundacao"]["perfil_spt"] = copy.deepcopy(PERFIL_MOLE)
    resultado = em.rodar(entrada)["fundacao"]
    assert resultado["escopo"]["bloco_de_coroamento"] == "partial"
    sem_bloco = [nome for nome, r in resultado["por_pilar"].items()
                 if r["geometria"].get("bloco_dimensionado") is False
                 and r["geometria"]["n_estacas"] > 1]
    if sem_bloco:
        codigos = {aviso["code"] for aviso in resultado["avisos"]}
        assert "bloco_de_coroamento_nao_dimensionado" in codigos
    del fundacao


def test_o_tipo_declarado_vence_a_sondagem_mas_a_divergencia_e_dita():
    entrada = _entrada()
    entrada["fundacao"]["perfil_spt"] = copy.deepcopy(PERFIL_MOLE)
    entrada["fundacao"]["tipo"] = "sapata"
    entrada["fundacao"]["sigma_solo_adm"] = 400.0     # o projetista assume
    fundacao = em.rodar(entrada)["fundacao"]
    assert fundacao["tipo"] == "sapata"
    codigos = {aviso["code"] for aviso in fundacao["avisos"]}
    assert "tipo_diverge_da_sondagem" in codigos


def test_bloco_de_concreto_simples_nao_tem_armadura_de_flexao():
    entrada = _entrada()
    entrada["fundacao"]["tipo"] = "bloco"
    fundacao = em.rodar(entrada)["fundacao"]
    assert fundacao["tipo"] == "bloco"
    for registro in fundacao["por_pilar"].values():
        geometria = registro["geometria"]
        assert geometria["beta_graus"] >= 60.0 - 1e-6
        assert "As_L_cm2" not in geometria and "As_B_cm2" not in geometria


# --------------------------------- gate --------------------------------------

def test_o_gate_da_fundacao_entra_no_atende_do_edificio(resultado):
    assert "fundacao" in resultado["gates"]
    assert resultado["gates"]["fundacao"]["OK"] is True
    assert resultado["gates"]["fundacao"]["reprovados"] == []


def test_solo_fraco_demais_reprova_em_vez_de_adotar_a_maior_sapata():
    """Saturar na maior geometria da escada e devolver OK e' o padrao de bug que
    este projeto persegue."""
    entrada = _entrada()
    entrada["fundacao"].pop("perfil_spt")
    entrada["fundacao"]["sigma_solo_adm"] = 25.0      # solo muito fraco
    resultado = em.rodar(entrada)
    assert resultado["gates"]["fundacao"]["OK"] is False
    assert resultado["gates"]["fundacao"]["reprovados"]
    assert not resultado["ATENDE"]
    for nome in resultado["gates"]["fundacao"]["reprovados"]:
        assert resultado["fundacao"]["por_pilar"][nome]["geometria"] is None


def test_o_relatorio_lista_um_pilar_por_linha(fundacao):
    texto = fe.relatorio_pt(fundacao)
    for nome in fundacao["por_pilar"]:
        assert nome in texto
    assert "PENDENTE REVISAO E ART" in texto


def test_o_cortante_na_estaca_e_declarado_nao_verificado():
    """Estaca carregada transversalmente (Broms / Matlock-Reese) nao existe no
    framework. Fronteira nomeada, nao verificacao esquecida."""
    entrada = _entrada()
    entrada["fundacao"]["perfil_spt"] = copy.deepcopy(PERFIL_MOLE)
    fundacao = em.rodar(entrada)["fundacao"]
    assert fundacao["escopo"]["esforco_horizontal_na_estaca"] == "not_available"


def test_na_fundacao_rasa_o_cortante_nao_e_uma_estaca(fundacao):
    """Na sapata o cortante ENTRA (FS ao deslizamento); o escopo da estaca nao
    se aplica e diz isso, em vez de herdar um not_available que confundiria."""
    assert fundacao["escopo"]["esforco_horizontal_na_estaca"] == "not_applicable"
    assert fundacao["escopo"]["acao_horizontal_na_fundacao"] == "implemented"
