# ============================================================================
# test_entregaveis_projeto.py - A CAMADA DE ENTREGA TEM QUE SER ALCANCAVEL.
# Os modulos de orcamento/cronograma/caderno/pacote/sitio/FV calculavam certo e
# ninguem os chamava: do ponto de vista de quem usa o framework eles NAO
# EXISTIAM. Estes testes travam o contrato pelo lado do USUARIO - o que sai numa
# rodada do Loop - e nao pelo lado da funcao pura (isso os testes de cada modulo
# ja fazem). O criterio e o manifesto: entregavel com status e artefato com hash.
# ============================================================================
"""Entregaveis de gestao/sitio/desenho do adaptador de galpao, via run_project."""

import os
import sys
import xml.dom.minidom as md

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import galpao_adapter  # noqa: F401  (registra o adaptador)
import project_loop
from project_loop import register_adapter, run_project

SEM_IFC = {"generate_ifc": False}


def _spec(**extras):
    valor = {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "concreto": {"vao": 20.0, "comprimento": 40.0, "n_porticos": 7,
                     "v0": 40.0, "cat": "IV", "classe": "B", "s1": 1.0, "s3": 1.0,
                     "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
                     "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"},
    }
    valor.update(extras)
    return valor


def _artefatos(resultado, kind):
    return [item for item in resultado["artifacts"] if item["kind"] == kind]


@pytest.fixture(scope="module")
def rodada(tmp_path_factory):
    """(manifesto, run_dir): o manifesto nao carrega o run_dir, e sem ele os
    testes de conteudo do artefato passariam sem abrir arquivo nenhum."""
    destino = tmp_path_factory.mktemp("basica")
    return run_project(_spec(), destino, SEM_IFC), str(destino)


@pytest.fixture(scope="module")
def rodada_basica(rodada):
    return rodada[0]


# --------------------------- contrato do adaptador ---------------------------
def test_entregaveis_de_gestao_estao_declarados_no_adaptador():
    galpao = project_loop.describe_adapters("galpao")[0]
    for nome in ("orcamento", "cronograma", "caderno_encargos", "pacote_legal",
                 "obras_sitio", "fotovoltaico", "desenhos_concreto"):
        assert nome in galpao["deliverables"], nome


def test_hook_fora_do_nucleo_exige_deliverable_homonimo():
    # sem declarar o entregavel, o hook e recusado: nao existe entregavel que o
    # manifesto nao anuncie.
    with pytest.raises(ValueError, match="hooks desconhecidos"):
        register_adapter("teste-hook-nao-declarado", lambda n, r: ({}, {}),
                         deliverables=("ifc",),
                         hooks={"orcamento": lambda *a: None})


def test_orcamento_roda_antes_do_cronograma():
    # a ordem declarada e a ordem de execucao: o cronograma le a planilha que o
    # orcamento acabou de gravar.
    extras = project_loop._PROJECT_EXTRA_DELIVERABLES["galpao"]
    assert extras.index("orcamento") < extras.index("cronograma")


# ------------------------------ gestao (sempre) ------------------------------
def test_orcamento_sai_da_rodada_com_planilha_e_curva_abc(rodada_basica):
    entregavel = rodada_basica["deliverables"]["orcamento"]
    assert entregavel["status"] == "generated"
    assert entregavel["custo_direto"] > 0
    assert entregavel["preco_venda"] > entregavel["custo_direto"]   # BDI aplicado
    # o preco de referencia nao pode passar por cotacao
    assert any("SINAPI" in aviso for aviso in entregavel["a_confirmar"])
    assert _artefatos(rodada_basica, "budget-sheet")
    assert _artefatos(rodada_basica, "budget-abc")


def test_todo_artefato_novo_entra_no_manifesto_com_hash(rodada_basica):
    kinds = {"budget-sheet", "schedule-cpm", "specification-book", "legal-package"}
    achados = [item for item in rodada_basica["artifacts"] if item["kind"] in kinds]
    assert {item["kind"] for item in achados} == kinds
    for item in achados:
        assert item["sha256"] and item["size"] > 0, item


def test_cronograma_usa_o_custo_do_orcamento_e_declara_a_cobertura(rodada_basica):
    entregavel = rodada_basica["deliverables"]["cronograma"]
    assert entregavel["status"] == "generated"
    assert entregavel["duracao_total_dias"] > 0
    assert entregavel["caminho_critico"]
    assert entregavel["custeado_pelo_orcamento"] is True
    assert entregavel["custo_total"] > 0
    # curva S custeada em parte das atividades satura antes do fim da obra: isso
    # e declarado, nunca mascarado.
    if entregavel["atividades_custeadas"] < entregavel["atividades_totais"]:
        assert any("curva S custeada" in aviso
                   for aviso in entregavel["a_confirmar"])


def test_curva_s_sai_como_svg_bem_formado(rodada):
    resultado, raiz = rodada
    caminho = _artefatos(resultado, "schedule-scurve-svg")[0]["path"]
    dom = md.parse(os.path.join(raiz, *caminho.split("/")))
    assert dom.documentElement.tagName == "svg"


def test_pranchas_do_concreto_sao_svg_parseavel(rodada):
    # substring nao prova render: o SVG tem que ABRIR como XML.
    resultado, raiz = rodada
    caminhos = [item["path"] for item in _artefatos(resultado, "drawing-svg")]
    assert caminhos
    for caminho in caminhos:
        dom = md.parse(os.path.join(raiz, *caminho.split("/")))
        assert dom.documentElement.tagName == "svg"


def test_caderno_e_pacote_saem_com_conteudo_e_nao_so_cabecalho(rodada):
    resultado, raiz = rodada
    for kind, marca in (("specification-book", "Material:"),
                        ("legal-package", "ART")):
        caminho = _artefatos(resultado, kind)[0]["path"]
        texto = open(os.path.join(raiz, *caminho.split("/")),
                     encoding="utf-8").read()
        assert marca in texto and len(texto) > 500, kind


def test_caderno_de_encargos_cobre_as_disciplinas_executadas(rodada_basica):
    entregavel = rodada_basica["deliverables"]["caderno_encargos"]
    assert entregavel["status"] == "generated"
    assert "concreto" in entregavel["disciplinas"]
    assert entregavel["n_clausulas"] > 0
    assert entregavel["normas_referenciadas"]


def test_pacote_legal_nao_inventa_o_responsavel_tecnico(rodada_basica):
    entregavel = rodada_basica["deliverables"]["pacote_legal"]
    assert entregavel["status"] == "generated"
    assert entregavel["n_pranchas"] > 0 and entregavel["n_art"] > 0
    assert any("ART" in aviso for aviso in entregavel["a_confirmar"])


def test_desenhos_do_concreto_saem_como_svg_valido(rodada_basica, tmp_path):
    entregavel = rodada_basica["deliverables"]["desenhos_concreto"]
    assert entregavel["status"] == "generated"
    assert "concreto-armacao.svg" in entregavel["pranchas"]
    assert "concreto-formas.svg" in entregavel["pranchas"]


# ------------------------- sitio: so com dado do sitio ------------------------
def test_sem_dado_de_sitio_o_entregavel_e_not_requested_e_nao_um_default(
        rodada_basica):
    for nome in ("obras_sitio", "fotovoltaico"):
        entregavel = rodada_basica["deliverables"][nome]
        assert entregavel["status"] == "not_requested"
        assert entregavel["detail"]


def test_terraplenagem_e_saneamento_saem_quando_o_sitio_e_declarado(tmp_path):
    site = {"terraplenagem": {"grid_terreno": [[101.0, 100.5], [99.5, 99.0]],
                              "cota_plataforma": 100.0, "area_celula_m2": 400.0,
                              "empolamento": 1.25, "greide_equilibrio": True,
                              "drenagem": {"C": 0.8, "i_mm_h": 120.0,
                                           "area_ha": 0.8,
                                           "largura_canaleta_m": 0.6,
                                           "declividade": 0.005}},
            "saneamento": {"esgoto": {"N": 20, "C": 50.0, "T": 1.0, "K": 65.0,
                                      "Lf": 1.0,
                                      "taxa_infiltracao_L_m2_dia": 40.0}}}
    resultado = run_project(_spec(site=site), tmp_path, SEM_IFC)
    entregavel = resultado["deliverables"]["obras_sitio"]
    assert entregavel["status"] == "generated"
    assert entregavel["frentes"] == ["saneamento", "terraplenagem"]
    assert _artefatos(resultado, "site-works")


def test_fotovoltaico_sem_hsp_nao_finge_dimensionar(tmp_path):
    resultado = run_project(
        _spec(site={"fotovoltaico": {"consumo_kwh_mes": 30000.0}}),
        tmp_path, SEM_IFC)
    entregavel = resultado["deliverables"]["fotovoltaico"]
    assert entregavel["status"] == "not_available"
    assert "A CONFIRMAR" in (entregavel["detail"] or "")
    assert entregavel["potencia_kWp"] is None


def test_fotovoltaico_dimensiona_com_hsp_e_area_da_cobertura(tmp_path):
    resultado = run_project(
        _spec(site={"fotovoltaico": {"HSP": 5.2, "consumo_kwh_mes": 30000.0}}),
        tmp_path, SEM_IFC)
    entregavel = resultado["deliverables"]["fotovoltaico"]
    assert entregavel["status"] == "generated"
    assert entregavel["potencia_kWp"] > 0
    # sem evidencia de campo nao se ATESTA comissionamento: sai o checklist
    assert "checklist" in entregavel["comissionamento"]
    assert _artefatos(resultado, "pv-design")


# ------------------------------ isolamento de falha ---------------------------
def test_falha_de_um_entregavel_nao_derruba_os_outros(tmp_path):
    resultado = run_project(
        _spec(**{"gestao": {"cronograma": {"atividades": "isto nao e uma lista"}}}),
        tmp_path, SEM_IFC)
    assert resultado["deliverables"]["cronograma"]["status"] == "failed"
    assert "TypeError" in resultado["deliverables"]["cronograma"]["detail"]
    assert resultado["deliverables"]["orcamento"]["status"] == "generated"
    assert resultado["deliverables"]["pacote_legal"]["status"] == "generated"


def test_precos_do_usuario_substituem_a_tabela_de_referencia(tmp_path):
    gestao = {"orcamento": {
        "quantitativos": {"aco_estrutural": 1000.0},
        "precos": {"aco_estrutural": ("Aco (cotacao da obra)", "kg", 20.0)},
        "bdi_pct": 18.0}}
    resultado = run_project(_spec(gestao=gestao), tmp_path, SEM_IFC)
    entregavel = resultado["deliverables"]["orcamento"]
    assert entregavel["bdi_pct"] == 18.0
    assert "aco_estrutural" in entregavel["codigos"]
    # com preco e BDI declarados, nao sobra ressalva de COTACAO...
    assert not [r for r in entregavel["a_confirmar"] if "SINAPI" in r or "BDI" in r]
    # ...mas o orcamento continua PARCIAL e tem que dizer isso (G7): declarar so o
    # aco nao torna a planilha um orcamento da obra.
    assert "piso_industrial" in entregavel["sem_quantidade"]
    assert any("PARCIAL" in r for r in entregavel["a_confirmar"])
