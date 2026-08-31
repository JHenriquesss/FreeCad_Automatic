"""Estrutura da casa residencial (G13): a carga chega ao chao.

Ate aqui a casa tinha instalacoes e nao tinha estrutura - o escopo dizia
`estrutura: not_available` e nenhuma laje, viga, pilar ou fundacao era
calculada. Estes testes cobrem a cadeia nova e, sobretudo, as tres coisas que
poderiam dar errado EM SILENCIO:

  1. o peso da alvenaria do TERREO sumir entre o pavimento e a fundacao (ele nao
     passa pelos pilares: desce pelo baldrame);
  2. a viga continua ser ANALISADA e nunca VERIFICADA - a secao declarada nunca
     conferida a flexao, cortante, flecha e fissura;
  3. o momento negativo da envoltoria ser trocado, na armadura superior, pelo
     w*L^2/10 de tabela, que e' MENOR num apoio interno de dois vaos.

E a fronteira da tipologia: esta cadeia nao calcula estabilidade horizontal, e
por isso RECUSA um predio em vez de aprova-lo sem gamma_z.
"""

import copy
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
GALPAO = HERE.parents[3]
sys.path.insert(0, str(GALPAO))

import estrutura_casa as ec
import viga_concreto as vgc

PAREDE = {"tipo": "bloco_ceramico_furo_horizontal", "espessura_cm": 14,
          "altura": 2.7, "revestimento_cm": 2.0}

TERREA = {
    "geometria": {"vaos_x": [3.5, 3.5, 3.4], "vaos_y": [4.0, 4.0],
                  "pe_direito": 2.7},
    "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"}],
    "laje": {"h": 0.10, "revestimento_kN_m2": 1.0},
    "viga": {"b": 0.20, "h": 0.45},
    "materiais": {"fck": 25e3, "fyk": 500e3},
    "parede_sobre_vigas": dict(PAREDE),
    "baldrame": {"b": 0.15, "h": 0.40, "parede": dict(PAREDE)},
    "fundacao": {"perfil_spt": [{"tipo": "argila_arenosa", "N": 8, "dz": 2.0},
                                {"tipo": "areia_siltosa", "N": 16, "dz": 3.0},
                                {"tipo": "areia", "N": 25, "dz": 4.0}],
                 "cota_apoio_m": 1.0, "mu_solo": 0.5, "h_pedestal_m": 0.4},
}


def _spec(**mudancas):
    spec = copy.deepcopy(TERREA)
    spec.update(copy.deepcopy(mudancas))
    return spec


@pytest.fixture(scope="module")
def terrea():
    return ec.rodar(copy.deepcopy(TERREA))


# --------------------------------------------------- a cadeia inteira roda

def test_a_casa_terrea_entrega_a_cadeia_completa(terrea):
    """Laje, viga, pilar, baldrame e fundacao - cada um com o seu gate."""
    assert terrea["ATENDE"], terrea["reprovados"]
    assert set(terrea["gates"]) >= {"laje", "vigas", "pilares", "viga_baldrame",
                                    "fundacao", "fechamento_carga"}
    assert terrea["tipologia"] == "terrea"
    assert terrea["fundacao"]["gate"]["n_pilares"] == 12
    for registro in terrea["fundacao"]["por_pilar"].values():
        assert registro["geometria"]["B_m"] > 0


def test_o_sobrado_tambem_roda():
    spec = _spec(pavimentos=[{"nome": "Cobertura", "uso": "cobertura_manutencao"},
                             {"nome": "Terreo", "uso": "residencial_dormitorio"}])
    resultado = ec.rodar(spec)
    assert resultado["tipologia"] == "sobrado"
    assert resultado["n_pavimentos"] == 2
    # dois pavimentos carregam MAIS que um: se a descida nao empilhasse, a
    # fundacao do sobrado sairia igual a da terrea
    assert resultado["N_base_max_k"] > ec.rodar(copy.deepcopy(TERREA))[
        "N_base_max_k"]


# ------------------------------------------- a fronteira tem guarda, nao fe

def test_predio_e_recusado_em_vez_de_aprovado_sem_estabilidade():
    """Esta cadeia nao calcula gamma_z, desaprumo nem ELS lateral. Deixar um
    predio de cinco andares passar por aqui entregaria todos os gates dizendo
    ATENDE sobre uma estrutura cuja estabilidade global ninguem verificou."""
    spec = _spec(pavimentos=[{"nome": "Pav %d" % k,
                              "uso": "residencial_dormitorio"}
                             for k in range(5)])
    with pytest.raises(ec.EntradaEstrutura) as erro:
        ec.rodar(spec)
    assert "edificio" in str(erro.value)


def test_o_escopo_nomeia_o_que_nao_e_calculado(terrea):
    escopo = terrea["escopo"]
    assert escopo["acao_horizontal"] == "not_available"
    assert escopo["estabilidade_global"] == "not_available"
    assert escopo["desaprumo"] == "not_available"
    assert escopo["laje"] == escopo["viga"] == escopo["pilar"] == "implemented"


# ---------------------------------- o peso da alvenaria terrea nao pode sumir

def test_a_carga_do_baldrame_chega_a_fundacao(terrea):
    """A alvenaria do terreo NAO passa por pilar nenhum: ela nasce no baldrame e
    desce direto para a sapata. Sem esta soma, o peso de todas as paredes da
    casa desapareceria entre o pavimento e a fundacao, com o fechamento de carga
    do pavimento fechando certinho."""
    reacoes = terrea["reacoes_baldrame_k"]
    assert reacoes and any(v > 0 for v in reacoes.values())
    for nome, N_fund in terrea["N_fundacao_k"].items():
        N_pilar = terrea["descida"]["pilares"][nome]["N_base_k"]
        assert N_fund == pytest.approx(N_pilar + reacoes.get(nome, 0.0), abs=0.02)
    # e a fundacao recebeu de fato o numero somado, nao o do pilar
    for nome, registro in terrea["fundacao"]["por_pilar"].items():
        assert registro["N_dimensionamento_kN"] == pytest.approx(
            terrea["N_fundacao_k"][nome], abs=0.1)


def test_sem_baldrame_as_sapatas_sao_menores_e_isso_e_dito():
    """A comparacao que prova que a parcela existe: a mesma casa sem baldrame
    declarado carrega MENOS a fundacao. O resultado nomeia a ausencia."""
    spec = _spec()
    spec.pop("baldrame")
    sem = ec.rodar(spec)
    com = ec.rodar(copy.deepcopy(TERREA))
    assert sem["baldrame"] is None
    assert sem["escopo"]["viga_baldrame"] == "not_available"
    assert "viga_baldrame" not in sem["gates"]
    # a comparacao e' na SOMA, nao no maximo: o baldrame do contorno nao chega
    # ao pilar interno, que continua sendo o mais carregado nos dois casos
    assert sum(sem["N_fundacao_k"].values()) < sum(com["N_fundacao_k"].values())
    assert sem["N_fundacao_k"]["P11"] < com["N_fundacao_k"]["P11"]


def test_o_baldrame_fecha_a_carga_que_lancou(terrea):
    """Uma linha de baldrame cujo peso nao foi lancado em pilar nenhum some sem
    que nada reclame - a mesma armadilha do fechamento do pavimento."""
    fechamento = terrea["baldrame"]["fechamento"]
    assert fechamento["ok"]
    assert fechamento["N_pilares_kN"] == pytest.approx(
        fechamento["carga_esperada_kN"], rel=0.02)
    esperado = terrea["baldrame"]["w_kN_m"] * fechamento["comprimento_m"]
    assert fechamento["carga_esperada_kN"] == pytest.approx(esperado, abs=0.01)


def test_baldrame_sem_a_parede_declarada_reprova_com_o_motivo():
    """Nao ha default de alvenaria: um baldrame que so carrega o proprio peso
    nao e' o baldrame desta casa. A entrada recusada vira gate REPROVADO com o
    motivo - falha ISOLADA, que nao impede o resto da casa de ser calculado e
    nao deixa a fundacao passar como se o baldrame nao existisse."""
    spec = _spec(baldrame={"b": 0.15, "h": 0.40})
    resultado = ec.rodar(spec)
    assert resultado["baldrame"] is None
    assert "parede" in resultado["baldrame_erro"]
    assert resultado["gates"]["viga_baldrame"]["OK"] is False
    assert "viga_baldrame" in resultado["reprovados"]
    assert resultado["gates"]["pilares"]["OK"]      # o resto seguiu calculado


def test_o_baldrame_adota_a_altura_que_atende_e_ela_pesa():
    """`dimensiona_baldrame` sobe a altura quando a declarada nao atende a
    flecha sob alvenaria. A carga que desce tem de usar a altura ADOTADA - senao
    a fundacao recebe o peso proprio de um baldrame que nao vai ser construido."""
    spec = _spec()
    spec["baldrame"] = dict(spec["baldrame"], h=0.40)
    resultado = ec.rodar(spec)
    baldrame = resultado["baldrame"]
    h = baldrame["secao"]["h"]
    esperado = baldrame["q_parede_kN_m"] + ec.GAMMA_C_CONC * baldrame["secao"]["b"] * h
    assert baldrame["w_kN_m"] == pytest.approx(esperado, rel=1e-6)
    assert h >= baldrame["secao"]["h_declarada"]


# ----------------------------------- a viga e VERIFICADA, nao so analisada

def test_toda_viga_e_verificada_tramo_a_tramo(terrea):
    """`pavimento_tipo` devolve a envoltoria de esforcos e NAO confere se a
    secao resiste. Aqui cada tramo passa por viga_concreto."""
    vigas = terrea["vigas"]
    assert vigas["n_tramos"] == sum(len(l["tramos"]) for l in vigas["por_linha"])
    assert vigas["n_tramos"] == 17          # 3 linhas X x 3 tramos + 4 Y x 2
    for linha in vigas["por_linha"]:
        for tramo in linha["tramos"]:
            assert tramo["As_inf_cm2"] > 0
            assert tramo["V_d_kN"] > 0


def test_viga_esbelta_demais_reprova_com_o_tramo_nomeado():
    """Nao ha saturacao: a secao que nao cabe sai REPROVADA dizendo qual tramo e
    por que, nunca dada por boa."""
    spec = _spec(viga={"b": 0.12, "h": 0.30})
    resultado = ec.rodar(spec)
    assert not resultado["gates"]["vigas"]["OK"]
    reprovadas = resultado["gates"]["vigas"]["reprovadas"]
    assert reprovadas
    assert all("tramo" in motivo for motivo in reprovadas)
    assert "vigas" in resultado["reprovados"]
    # reprovado SEM dizer por que e' quase tao ruim quanto aprovado em silencio
    for linha in resultado["vigas"]["por_linha"]:
        for tramo in linha["tramos"]:
            if not tramo["OK"]:
                assert tramo["motivos"], (linha["nome"], tramo["tramo"])


def test_o_momento_negativo_da_envoltoria_chega_ao_dimensionamento(terrea):
    """Guarda do repasse. Se `M_d_neg` deixar de ser passado, viga_concreto volta
    ao w*L^2/10 de tabela - MENOR que o w*L^2/8 de um apoio interno de dois vaos
    - e a armadura superior fica abaixo do esforco sem nenhum gate reclamar."""
    achou_continua = False
    for linha in terrea["vigas"]["por_linha"]:
        for tramo in linha["tramos"]:
            assert tramo["momento_negativo_coberto"], (linha["nome"], tramo)
            if tramo["M_d_neg_envoltoria_kNm"] > 0:
                achou_continua = True
                assert tramo["M_d_neg_dimensionado_kNm"] == pytest.approx(
                    tramo["M_d_neg_envoltoria_kNm"], abs=0.01)
    assert achou_continua


def test_passar_o_momento_negativo_muda_a_armadura_superior():
    """A prova de que o repasse tem efeito: sem `M_d_neg` a face superior sai com
    OUTRO numero. Um parametro que nao muda nada seria um repasse decorativo."""
    base = {"vao": 4.0, "b": 0.20, "h": 0.45, "fck": 25e3, "fyk": 500e3,
            "q": 20.0, "continuidade": "continua"}
    tabela = vgc.verifica_viga(dict(base))
    envoltoria = vgc.verifica_viga(dict(base, M_d_neg=2.0 * tabela["M_d_neg"]))
    assert envoltoria["M_d_neg"] == pytest.approx(2.0 * tabela["M_d_neg"])
    assert envoltoria["As_sup_cm2"] > tabela["As_sup_cm2"]


# ------------------------------------------------------------- laje e solo

def test_a_espessura_adotada_da_laje_realimenta_a_carga():
    """A laje ENGROSSA quando a declarada nao atende; a carga permanente que
    desceu tem de ser a da espessura adotada, nao a da declarada."""
    spec = _spec(laje={"h": 0.08, "revestimento_kN_m2": 1.0})
    resultado = ec.rodar(spec)
    gate = resultado["gates"]["laje_compatibilizada"]
    assert gate["OK"]
    assert gate["h_na_carga_cm"] == pytest.approx(gate["h_adotada_cm"])
    assert resultado["pavimento"]["h_laje_usada"] == pytest.approx(
        resultado["laje"]["h"])


def test_sem_sondagem_declarada_nao_ha_fundacao_inventada():
    """A tensao admissivel do solo nao tem default neste framework."""
    spec = _spec()
    spec.pop("fundacao")
    resultado = ec.rodar(spec)
    assert resultado["fundacao"] is None
    assert resultado["escopo"]["fundacao"] == "not_available"
    assert "fundacao" not in resultado["gates"]
    # e a superestrutura continua calculada: a fundacao ausente nao derruba tudo
    assert resultado["gates"]["pilares"]["OK"]


def test_relatorio_diz_o_que_ficou_de_fora(terrea):
    texto = ec.relatorio_pt(terrea)
    assert "ACAO HORIZONTAL NAO AVALIADA" in texto
    assert "VIGA BALDRAME" in texto
    assert "PENDENTE REVISAO E ART" in texto
