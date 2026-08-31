# ============================================================================
# test_gestao_edificio.py - G14: A GESTAO DO EDIFICIO.
#
# O edificio saia da rodada com estrutura, fundacao, instalacoes, BIM e
# pranchas - e sem orcamento, cronograma, caderno de encargos ou pacote legal.
# O mecanismo (`entregaveis_projeto`) ja existia; faltava a DERIVACAO de
# quantitativos de um predio de concreto.
#
# O criterio destes testes e' o MANIFESTO (o que sai da rodada do Loop), e o
# alvo principal e' o defeito n.3 do G7: orcamento PARCIAL se apresentando como
# fechado. Por isso quase todo teste aqui pergunta a mesma coisa por angulos
# diferentes: o que o numero NAO cobre esta dito ao lado do numero?
# ============================================================================
"""Entregaveis de gestao do edificio multipavimento, via run_project."""

import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import cronograma as cr
import edificio_adapter as ea
import gestao_edificio as ge
import project_loop
from builtin_adapters import register_builtin_adapters
from project_loop import normalize_spec, run_project

REPO = os.path.dirname(os.path.dirname(GALPAO))
SPEC_PERSISTIDO = os.path.join(REPO, "projects", "edificio-multipavimento",
                               "project-spec.json")

COM_DESENHO = {"generate_ifc": False, "generate_2d": True}


@pytest.fixture(scope="module", autouse=True)
def _adaptadores():
    register_builtin_adapters()


@pytest.fixture(scope="module")
def spec():
    with open(SPEC_PERSISTIDO, encoding="utf-8") as arquivo:
        return json.load(arquivo)


@pytest.fixture(scope="module")
def rodada(spec, tmp_path_factory):
    destino = tmp_path_factory.mktemp("g14")
    return run_project(copy.deepcopy(spec), destino, COM_DESENHO), str(destino)


@pytest.fixture(scope="module")
def manifesto(rodada):
    return rodada[0]


@pytest.fixture(scope="module")
def derivado(spec):
    resultado, _registros = ea.run_edificio(
        normalize_spec(copy.deepcopy(spec)), None)
    return ge.derivacao(resultado), resultado


# --------------------------- contrato do adaptador ---------------------------
def test_os_quatro_entregaveis_de_gestao_estao_declarados():
    edificio = project_loop.describe_adapters(ea.ADAPTER_NAME)[0]
    for nome in ("orcamento", "cronograma", "caderno_encargos", "pacote_legal"):
        assert nome in edificio["deliverables"], nome


def test_orcamento_roda_antes_do_cronograma():
    # a ordem declarada e a ordem de execucao: sem a planilha gravada, a curva S
    # do edificio sairia sem custo nenhum.
    extras = project_loop._PROJECT_EXTRA_DELIVERABLES[ea.ADAPTER_NAME]
    assert extras.index("orcamento") < extras.index("cronograma")


def test_os_quatro_saem_generated_na_rodada(manifesto):
    for nome in ("orcamento", "cronograma", "caderno_encargos", "pacote_legal"):
        assert manifesto["deliverables"][nome]["status"] == "generated", nome


def test_todo_artefato_de_gestao_entra_no_manifesto_com_hash(manifesto):
    kinds = {"budget-sheet", "budget-abc", "schedule-cpm", "schedule-scurve-svg",
             "specification-book", "legal-package"}
    achados = [item for item in manifesto["artifacts"] if item["kind"] in kinds]
    assert {item["kind"] for item in achados} == kinds
    for item in achados:
        assert item["sha256"] and item["size"] > 0, item


# ------------------------------- quantitativos -------------------------------
def test_concreto_e_a_soma_dos_elementos_medidos_sem_sobreposicao(derivado):
    """A conta refeita por fora: laje cheia, alma da viga e pilar entre vigas.

    Se um dia a convencao mudar num lado so (viga medida com a altura total, ou
    pilar de piso a piso), o volume cresce sem que nenhum gate reclame - o
    orcamento e' o unico lugar onde esse erro aparece, e em dinheiro.
    """
    dados, resultado = derivado
    est = resultado["estrutura"]
    pav = est["pavimento"]
    n = est["n_pavimentos"]
    comp = (sum(sum(v["vaos"]) for v in pav["vigas_x"])
            + sum(sum(v["vaos"]) for v in pav["vigas_y"]))
    laje = pav["area_m2"] * est["h_laje_adotada"] * n
    viga = pav["b_viga"] * (pav["h_viga"] - est["h_laje_adotada"]) * comp * n
    pilar = sum(lance["b"] * lance["h"]
                * (lance["pe_direito"] - lance["h_viga"])
                for p in est["pilares"].values() for lance in p["lances"])

    composicao = dados["composicao"]
    assert composicao["laje_m3"] == pytest.approx(laje, rel=1e-3)
    assert composicao["viga_m3"] == pytest.approx(viga, rel=1e-3)
    assert composicao["pilar_m3"] == pytest.approx(pilar, rel=1e-3)
    total = dados["quantitativos"]["concreto_estrut"]
    assert total == pytest.approx(laje + viga + pilar + composicao["escada_m3"],
                                  rel=1e-3)
    # e a espessura que ENTROU e a ADOTADA pela laje, nao a declarada no spec
    assert est["h_laje_adotada"] > est["h_laje_declarada"]


def test_taxas_de_concreto_e_forma_ficam_na_ordem_de_grandeza_de_um_predio(derivado):
    """Guarda de ordem de grandeza: 1 m2 de pavimento gasta ~0,2 m3 e ~2 m2.

    Nao e' aferimento de norma - e' a rede que pega uma unidade trocada (o erro
    de dimensao em mm x m que o G8 achou na sapata) antes de ela virar preco.
    """
    dados, resultado = derivado
    est = resultado["estrutura"]
    area_total = est["pavimento"]["area_m2"] * est["n_pavimentos"]
    q = dados["quantitativos"]
    assert 0.12 <= q["concreto_estrut"] / area_total <= 0.30
    assert 1.5 <= q["forma"] / area_total <= 2.6


def test_armadura_e_publicada_por_ELEMENTO_e_a_da_viga_nunca_e_derivada(derivado):
    """O buraco tem de ter nome proprio.

    Nao existe As dimensionada para as vigas do edificio (elas sao analisadas e
    nunca verificadas). Se a armadura fosse UM codigo so, o peso da laje mais o
    do pilar sairiam com cara de armadura completa - 30-40% abaixo do real.
    """
    dados, _resultado = derivado
    q = dados["quantitativos"]
    assert q["armadura_laje"] > 0 and q["armadura_pilar"] > 0
    assert "armadura_viga" not in q
    assert "armadura" not in q                       # o codigo generico nao e usado
    motivos = {item["item"]: item["motivo"] for item in dados["nao_derivados"]}
    assert "armadura_viga" in motivos
    assert "VERIFICADAS" in motivos["armadura_viga"]


def test_armadura_da_laje_sai_do_quadro_de_ferros_e_nao_de_taxa_inventada(derivado):
    import laje_concreto as lj

    dados, resultado = derivado
    laje = resultado["estrutura"]["laje"]
    peso_painel = lj.peso_total_aco(lj.quadro_de_ferros(laje))
    taxa = peso_painel / (laje["lx"] * laje["ly"])
    area_total = (resultado["estrutura"]["pavimento"]["area_m2"]
                  * resultado["estrutura"]["n_pavimentos"])
    assert dados["quantitativos"]["armadura_laje"] == pytest.approx(
        taxa * area_total, rel=1e-4)


def test_taxa_de_armadura_do_pilar_e_plausivel(derivado):
    dados, _resultado = derivado
    taxa = (dados["quantitativos"]["armadura_pilar"]
            / dados["composicao"]["pilar_m3"])
    assert 40.0 <= taxa <= 200.0                     # kg/m3 de pilar de edificio


def test_fundacao_medida_da_geometria_aprovada_de_cada_pilar(derivado):
    dados, resultado = derivado
    fund = resultado["estrutura"]["fundacao"]
    volume = sum(r["geometria"]["B_m"] * r["geometria"]["L_m"]
                 * r["geometria"]["h_m"] for r in fund["por_pilar"].values())
    assert dados["quantitativos"]["fundacao_concreto"] == pytest.approx(
        volume, abs=0.01)
    assert dados["quantitativos"]["armadura_fundacao"] > 0


def test_pontos_eletricos_e_hidraulicos_vem_das_instalacoes(derivado):
    dados, resultado = derivado
    elet = resultado["instalacoes"]["eletrico"]
    ambientes = elet["carga_por_unidade"]["ambientes"]
    esperado = ((sum(a["n_tomadas"] for a in ambientes) + len(ambientes))
                * elet["unidades_por_pavimento"] * elet["pavimentos_servidos"])
    assert dados["quantitativos"]["eletrica_ponto"] == esperado
    aparelhos = resultado["instalacoes"]["hidraulica"]["coluna"]["aparelhos_totais"]
    assert dados["quantitativos"]["hidraulica_ponto"] == sum(aparelhos.values())


# ------------------- o orcamento nao pode se dizer fechado --------------------
def test_orcamento_parcial_e_declarado_com_os_insumos_que_faltam(manifesto):
    orcamento = manifesto["deliverables"]["orcamento"]
    assert "armadura_viga" in orcamento["sem_quantidade"]
    assert any("orcamento PARCIAL" in aviso for aviso in orcamento["a_confirmar"])
    assert 0 < orcamento["cobertura_pct"] < 100


def test_insumo_que_a_obra_nao_tem_nao_conta_como_falta(manifesto):
    """`nao_aplicaveis` x `sem_quantidade` - a distincao que separa ruido de furo.

    Um predio de concreto nao tem aco estrutural nem telha metalica: lista-los
    como 'sem quantitativo' encheria o aviso de itens irrelevantes e esconderia
    a armadura de viga, que e' a falta que importa.
    """
    orcamento = manifesto["deliverables"]["orcamento"]
    for codigo in ("aco_estrutural", "telha_cobertura", "piso_industrial"):
        assert codigo in orcamento["nao_aplicaveis"]
        assert codigo not in orcamento["sem_quantidade"]
    # fundacao RASA: metro de estaca nao e' insumo desta obra
    assert "estaca" in orcamento["nao_aplicaveis"]
    assert "estaca" not in orcamento["sem_quantidade"]


def test_insumos_fora_da_tabela_de_precos_sao_nomeados(manifesto):
    # revestimento, esquadria, elevador e a instalacao de incendio nao tem preco
    # na tabela: o preco de venda NAO e o preco da obra, e isso e' dito.
    avisos = " ".join(manifesto["deliverables"]["orcamento"]["a_confirmar"])
    assert "elevador" in avisos and "incendio" in avisos


def test_fachada_nao_declarada_nao_vira_area_de_alvenaria(manifesto):
    orcamento = manifesto["deliverables"]["orcamento"]
    assert "fechamento_lateral" in orcamento["sem_quantidade"]
    motivos = {item["item"]: item["motivo"]
               for item in orcamento["nao_derivados"]}
    assert "parede_sobre_vigas" in motivos["fechamento_lateral"]


def test_fachada_declarada_vira_area_de_alvenaria(spec):
    """O outro lado da mesma regra: declarada a parede, ela e' orcada."""
    com_parede = copy.deepcopy(spec)
    com_parede["turnkey"]["estrutura"]["parede_sobre_vigas"] = {
        "tipo": "bloco_ceramico_furo_horizontal", "espessura_cm": 14.0,
        "revestimento_cm": 2.0}
    resultado, _registros = ea.run_edificio(normalize_spec(com_parede), None)
    dados = ge.derivacao(resultado)
    assert dados["quantitativos"]["fechamento_lateral"] > 0
    assert any("sem desconto de vaos" in nota.lower()
               for nota in dados["a_confirmar"])


def test_fundacao_em_estacas_troca_o_insumo_e_nomeia_o_bloco(spec):
    """O escopo segue o TIPO de fundacao, e o que a obra tem nunca some dele.

    Sobre estacas nao ha volume de sapata - mas ha bloco de coroamento, e a
    geometria publicada so traz a altura dele. Entao `fundacao_concreto`
    continua NO ESCOPO (aparece como falta, com motivo), enquanto `estaca` sai
    do escopo quando a fundacao e' rasa.
    """
    profunda = copy.deepcopy(spec)
    profunda["turnkey"]["estrutura"]["fundacao"]["tipo"] = "estaca"
    resultado, _registros = ea.run_edificio(normalize_spec(profunda), None)
    dados = ge.derivacao(resultado)
    assert dados["quantitativos"]["estaca"] > 0
    assert "fundacao_concreto" not in dados["quantitativos"]
    assert "fundacao_concreto" in dados["aplicaveis"]
    motivos = {item["item"] for item in dados["nao_derivados"]}
    assert "bloco de coroamento" in motivos


def test_sem_estrutura_calculada_nao_ha_orcamento_inventado():
    dados = ge.derivacao({"estrutura": None, "instalacoes": {}})
    assert dados["quantitativos"] == {}
    assert dados["nao_derivados"][0]["item"] == "estrutura"


# --------------------------------- cronograma --------------------------------
def test_a_estrutura_do_cronograma_escala_com_os_pavimentos():
    quatro = {a["id"]: a for a in ge.wbs(4)}["estr"]["dur"]
    doze = {a["id"]: a for a in ge.wbs(12)}["estr"]["dur"]
    assert doze == 3 * quatro
    assert quatro == 4 * ge.CICLO_ESTRUTURA_DIAS_POR_PAVIMENTO


def test_cronograma_do_edificio_e_o_do_predio_desta_rodada(manifesto, derivado):
    dados, resultado = derivado
    crono = manifesto["deliverables"]["cronograma"]
    assert crono["duracao_total_dias"] > 0
    assert crono["custeado_pelo_orcamento"] is True
    esperado = cr.cronograma(ge.wbs(resultado["estrutura"]["n_pavimentos"]))
    assert crono["duracao_total_dias"] == esperado["duracao_total_dias"]
    # a rede do galpao (que nao sobe pavimentos) nao pode ter sido usada
    assert crono["duracao_total_dias"] != cr.cronograma(cr._WBS_GALPAO)[
        "duracao_total_dias"]


def test_curva_s_parcialmente_custeada_e_declarada(manifesto):
    crono = manifesto["deliverables"]["cronograma"]
    if crono["atividades_custeadas"] < crono["atividades_totais"]:
        assert any("curva S custeada" in aviso for aviso in crono["a_confirmar"])


# ---------------------------- caderno e pacote legal --------------------------
def test_caderno_so_especifica_as_disciplinas_executadas(manifesto):
    disciplinas = manifesto["deliverables"]["caderno_encargos"]["disciplinas"]
    assert set(disciplinas) == {"fundacao", "concreto", "eletrico", "hidraulica",
                                "incendio"}
    # o predio nao tem estrutura metalica nem piso industrial: especifica-los
    # seria o caderno prometendo o que o projeto nao entrega
    assert "aco" not in disciplinas and "piso" not in disciplinas


def test_disciplina_nao_executada_fica_fora_do_caderno(spec):
    sem_hidraulica = copy.deepcopy(spec)
    del sem_hidraulica["turnkey"]["hidraulica"]
    resultado, _registros = ea.run_edificio(
        normalize_spec(sem_hidraulica), None)
    assert "hidraulica" not in ge.disciplinas(resultado)


def test_memorial_do_pacote_traz_o_veredito_de_cada_disciplina(derivado, rodada):
    _dados, resultado = derivado
    memorial = ge.memorial(resultado)
    nomes = {item["disciplina"] for item in memorial["disciplinas"]}
    assert {"estrutura", "eletrico", "hidraulica", "incendio"} <= nomes
    assert memorial["geometria"]["pavimentos"] == resultado["estrutura"][
        "n_pavimentos"]
    # o texto entregue tem de conter o memorial, nao so o dict
    manifesto, raiz = rodada
    caminho = [item["path"] for item in manifesto["artifacts"]
               if item["kind"] == "legal-package"][0]
    with open(os.path.join(raiz, *caminho.split("/")), encoding="utf-8") as arq:
        texto = arq.read()
    assert "Memorial descritivo consolidado" in texto
    assert "PE-CO-01" in texto


def test_indice_de_pranchas_nao_passa_por_pasta_de_pranchas(manifesto):
    """O indice lista o executivo INTEIRO; a rodada desenhou duas folhas.

    Sem confrontar os dois, o pacote legal listaria treze pranchas ao lado de
    uma pasta com duas e passaria por completo - o orcamento parcial na forma
    de prancha.
    """
    pacote = manifesto["deliverables"]["pacote_legal"]
    emitidas = pacote["pranchas_emitidas_na_rodada"]
    assert 0 < emitidas < pacote["n_pranchas"]
    assert any("o indice lista" in aviso for aviso in pacote["a_confirmar"])
    assert any("responsavel tecnico" in aviso for aviso in pacote["a_confirmar"])


# ------------------------- o galpao nao foi alterado --------------------------
def test_o_galpao_continua_com_a_sua_propria_derivacao():
    """A camada virou generica; o galpao nao pode ter herdado o escopo do predio."""
    galpao = project_loop.describe_adapters("galpao")[0]
    for nome in ("orcamento", "cronograma", "caderno_encargos", "pacote_legal",
                 "obras_sitio", "fotovoltaico"):
        assert nome in galpao["deliverables"], nome
    assert "obras_sitio" not in project_loop.describe_adapters(
        ea.ADAPTER_NAME)[0]["deliverables"]
