"""G58: a casa nivela ao predio - cinco entregaveis, quantitativos proprios.

Cada teste abre o artefato no disco (G52), nao so o status do manifesto. O
vermelho-por-injecao garante que cada guarda falha quando o defeito volta.
"""

import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import gestao_casa as gc
from builtin_adapters import register_builtin_adapters
from project_loop import describe_adapters, run_project, verify_project_run

ROOT = Path(__file__).resolve().parents[3]
SPEC_PERSISTIDO = ROOT / "projects" / "casa-residencial" / "project-spec.json"


@pytest.fixture(scope="module")
def spec():
    return json.loads(SPEC_PERSISTIDO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module", autouse=True)
def _adaptadores():
    register_builtin_adapters()


@pytest.fixture(scope="module")
def execucao(spec, tmp_path_factory):
    destino = tmp_path_factory.mktemp("casa-g58") / "run"
    manifesto = run_project(
        spec, destino,
        {"generate_2d": True, "generate_ifc": True, "generate_3d": False})
    return manifesto, destino


def _manifestodisco(destino):
    return json.loads((destino / "project-run.json").read_text(encoding="utf-8"))


# --- contrato: nove entregaveis, cinco hooks novos ---------------------------

NOVE = {"report", "drawings", "ifc", "model_3d", "coordination", "orcamento",
        "cronograma", "caderno_encargos", "pacote_legal"}


def test_adaptador_declara_os_nove_entregaveis():
    capacidades = {item["name"]: item for item in describe_adapters()}
    assert set(capacidades["casa-residencial"]["deliverables"]) == NOVE


def test_cronograma_roda_depois_do_orcamento():
    capacidades = {item["name"]: item for item in describe_adapters()}
    entregaveis = capacidades["casa-residencial"]["deliverables"]
    assert entregaveis.index("orcamento") < entregaveis.index("cronograma")


# --- orcamento cheio: telha dentro, estaca fora, nada faltando ---------------

def test_orcamento_cheio_cobre_telha_e_exclui_estaca(execucao):
    manifesto, _ = execucao
    orcamento = manifesto["deliverables"]["orcamento"]
    assert orcamento["status"] == "generated"
    assert "telha_cobertura" in orcamento["codigos"]
    assert orcamento["sem_quantidade"] == []
    assert orcamento["cobertura_pct"] == 100.0
    # sapata, nao estaca: cobrar metro de estaca seria o ruido da guarda 2
    assert "estaca" in orcamento["nao_aplicaveis"]
    assert "aco_estrutural" in orcamento["nao_aplicaveis"]
    assert "piso_industrial" in orcamento["nao_aplicaveis"]


def test_relatorio_do_orcamento_nomeia_a_telha(execucao):
    _, destino = execucao
    texto = (destino / "orcamento" / "relatorio.txt").read_text(encoding="utf-8")
    assert "telha_cobertura" in texto or "telha" in texto.lower()
    assert "ORCAMENTO PARCIAL" not in texto


# --- guarda G14, primeira vez fora do predio ---------------------------------

def test_guarda_g14_sem_estrutura_concreto_e_falta_aco_e_ruido():
    """Sem estrutura calculada: concreto vira falta, aco segue nao-aplicavel."""
    import orcamento as orc

    resultado = {"estrutura": None,
                 "eletrico": {"circuits": {"points": [{"kind": "lighting"}]}},
                 "hidraulica": {}, "arquitetura": {}}
    dados = gc.derivacao(
        resultado,
        {"aparelhos_agua": {"pia": 1}, "aparelhos_esgoto": {"bacia": 1},
         "cobertura": {"area_m2": 80.0}})
    # eletrica/hidraulica/telha continuam - so o concreto some
    assert dados["quantitativos"]["eletrica_ponto"] == 1
    assert dados["quantitativos"]["telha_cobertura"] == 80.0
    composto = orc.compor_orcamento(
        dados["quantitativos"], dict(gc.PRECOS_CASA), 25.0,
        aplicaveis=dados["aplicaveis"])
    assert "concreto_estrut" in composto["sem_quantidade"]
    assert "aco_estrutural" in composto["nao_aplicaveis"]


def test_telhado_sem_area_vira_falta_nomeada_nunca_zero():
    """Sem cobertura declarada: telha em sem_quantidade, nao zerada."""
    import orcamento as orc

    resultado = {"estrutura": None,
                 "eletrico": {"circuits": {"points": [{"kind": "tug"}]}},
                 "hidraulica": {}, "arquitetura": {}}
    dados = gc.derivacao(
        resultado,
        {"aparelhos_agua": {"pia": 1}, "aparelhos_esgoto": {"bacia": 1}})
    assert "telha_cobertura" not in dados["quantitativos"]
    assert any(item["item"] == "telha_cobertura"
               for item in dados["nao_derivados"])
    composto = orc.compor_orcamento(
        dados["quantitativos"], dict(gc.PRECOS_CASA), 25.0,
        aplicaveis=dados["aplicaveis"])
    assert "telha_cobertura" in composto["sem_quantidade"]


def test_orcamento_parcial_se_declara_parcial_no_disco(spec, tmp_path):
    """Casa sem estrutura: o .txt diz PARCIAL com os insumos nomeados."""
    reduzido = copy.deepcopy(spec)
    reduzido["turnkey"].pop("estrutura")
    destino = tmp_path / "run-sem-estrutura"
    manifesto = run_project(reduzido, destino, {"generate_2d": False})
    orcamento = manifesto["deliverables"]["orcamento"]
    assert orcamento["status"] == "generated"
    assert "concreto_estrut" in orcamento["sem_quantidade"]
    texto = (destino / "orcamento" / "relatorio.txt").read_text(encoding="utf-8")
    assert "ORCAMENTO PARCIAL" in texto
    assert "concreto_estrut" in texto


# --- coordenacao: geometria antes do hook ------------------------------------

def test_coordenacao_tem_as_tres_disciplinas(execucao):
    manifesto, _ = execucao
    coordenacao = manifesto["coordination"]
    assert coordenacao["status"] == "generated"
    assert set(coordenacao["disciplinas"]) == {"estrutura", "eletrico",
                                              "hidraulica"}


def test_clash_aponta_furos_reais_no_disco(execucao):
    _, destino = execucao
    clash = json.loads(
        (destino / "coordination" / "clash.json").read_text(encoding="utf-8"))
    assert clash["n_clashes"] > 0
    assert "hidraulica" in (clash["por_par"] and ";".join(clash["por_par"]) or "")
    tipos = {c["tipos"] for c in clash["clashes"]}
    assert any("Pipe" in t for t in tipos)
    relatorio = (destino / "coordination" / "relatorio.txt").read_text(
        encoding="utf-8")
    assert "FEDERADO DA CASA" in relatorio
    matriz = (destino / "coordination" / "matriz.svg").read_text(encoding="utf-8")
    assert "<svg" in matriz


def test_luminaria_hospedada_nao_vira_furo(execucao):
    """Ponto de luz no teto toca a laje por montagem, nao e' furacao."""
    _, destino = execucao
    clash = json.loads(
        (destino / "coordination" / "clash.json").read_text(encoding="utf-8"))
    pares = {(c["tipos"]) for c in clash["clashes"]}
    assert not any(set(p.split("x")) == {"Slab", "Luminaire"} for p in pares)


def test_sem_instalacao_coordenacao_fica_indisponivel_com_motivo(spec, tmp_path):
    reduzido = copy.deepcopy(spec)
    reduzido["turnkey"].pop("eletrico")
    reduzido["turnkey"].pop("hidraulica")
    manifesto = run_project(reduzido, tmp_path / "run-sem-inst")
    coordenacao = manifesto["coordination"]
    assert coordenacao["status"] == "not_available"
    assert "instalacao" in (coordenacao.get("detail") or "")


# --- fronteira G13 atravessa os entregaveis novos -----------------------------

def test_tres_pavimentos_bloqueiam_estrutura_e_os_cinco_respeitam(spec, tmp_path):
    """Acima de 2 pav a casa e' recusada; nada novo contorna a fronteira."""
    alto = copy.deepcopy(spec)
    alto["turnkey"]["estrutura"]["pavimentos"] = [
        {"nome": "P%d" % i, "uso": "dormitorio"} for i in range(1, 4)]
    destino = tmp_path / "run-3pav"
    manifesto = run_project(alto, destino, {"generate_2d": True})
    assert manifesto["disciplines"]["estrutura"]["status"] == "blocked"
    for nome in ("orcamento", "cronograma"):
        entregavel = manifesto["deliverables"][nome]
        assert entregavel["status"] == "not_available", nome
        assert "G13" in (entregavel.get("detail") or ""), nome
    assert manifesto["coordination"]["status"] == "not_available"


# --- cronograma, caderno, pacote ----------------------------------------------

def test_cronograma_tem_cobertura_e_sai_custeado(execucao):
    manifesto, destino = execucao
    cronograma = manifesto["deliverables"]["cronograma"]
    assert cronograma["status"] == "generated"
    assert cronograma["duracao_total_dias"] > 0
    cpm = json.loads(
        (destino / "cronograma" / "cpm.json").read_text(encoding="utf-8"))
    ids = {a["id"] for a in cpm["atividades"]}
    assert "cob" in ids
    assert cronograma["custeado_pelo_orcamento"] is True


def test_wbs_da_casa_tem_cobertura_propria():
    ids = [a["id"] for a in gc.wbs(1)]
    assert "cob" in ids
    assert gc.CUSTO_POR_ATIVIDADE["telha_cobertura"] == "cob"


def test_caderno_so_disciplinas_com_clausula(execucao):
    manifesto, _ = execucao
    caderno = manifesto["deliverables"]["caderno_encargos"]
    assert caderno["status"] == "generated"
    assert "arquitetura" not in caderno["disciplinas"]
    assert {"concreto", "eletrico", "hidraulica"} <= set(caderno["disciplinas"])


def test_pacote_lista_arquitetura_e_avisa_o_indice(execucao):
    manifesto, destino = execucao
    pacote = manifesto["deliverables"]["pacote_legal"]
    assert pacote["status"] == "generated"
    dados = json.loads(
        (destino / "documentos" / "pacote-legal.json").read_text(encoding="utf-8"))
    disciplinas = {p["disciplina"] for p in dados["indice_pranchas"]}
    assert "arquitetura" in disciplinas
    assert pacote["pranchas_emitidas_na_rodada"] < pacote["n_pranchas"]
    texto = (destino / "documentos" / "pacote-legal.md").read_text(encoding="utf-8")
    assert "AVISO" in texto


def test_sobrado_dois_pavimentos_dentro_da_fronteira(spec, tmp_path):
    """2 pav e' casa (sobrado), nao predio: estrutura calcula e a WBS escala."""
    sobrado = copy.deepcopy(spec)
    sobrado["turnkey"]["estrutura"]["pavimentos"] = [
        {"nome": "Terreo", "uso": "residencial_dormitorio"},
        {"nome": "Cobertura", "uso": "cobertura_manutencao"}]
    sobrado["turnkey"]["hidraulica"]["pavimentos"] = 2
    destino = tmp_path / "run-sobrado"
    manifesto = run_project(sobrado, destino, {})
    assert manifesto["disciplines"]["estrutura"]["status"] == "needs_review"
    resultado = json.loads(
        (destino / "reports" / "adapter-result.json").read_text(encoding="utf-8"))
    assert resultado["estrutura"]["tipologia"] == "sobrado"
    assert resultado["estrutura"]["n_pavimentos"] == 2
    orcamento = manifesto["deliverables"]["orcamento"]
    assert orcamento["status"] == "generated"
    assert orcamento["sem_quantidade"] == []
    assert manifesto["coordination"]["status"] == "generated"
    assert gc.wbs(2)[2]["dur"] > gc.wbs(1)[2]["dur"]


# --- laco manifesto <-> disco (G52) --------------------------------------------

def test_todo_artefato_do_manifesto_existe_no_disco(execucao):
    manifesto, destino = execucao
    faltando = []
    for artefato in manifesto.get("artifacts", []):
        if not (destino / artefato["path"]).is_file():
            faltando.append(artefato["path"])
    assert faltando == []
    verificacao = verify_project_run(destino)
    assert verificacao["ok"] is True, verificacao["errors"]


def test_cada_entregavel_novo_abre_no_disco(execucao):
    _, destino = execucao
    planilha = json.loads(
        (destino / "orcamento" / "planilha.json").read_text(encoding="utf-8"))
    assert planilha["preco_venda"] > 0
    assert len(planilha["linhas"]) == 11
    cpm = json.loads(
        (destino / "cronograma" / "cpm.json").read_text(encoding="utf-8"))
    assert cpm["duracao_total_dias"] > 0
    caderno = (destino / "documentos" / "caderno-encargos.md").read_text(
        encoding="utf-8")
    assert "CADERNO DE ENCARGOS" in caderno
    pacote = (destino / "documentos" / "pacote-legal.md").read_text(encoding="utf-8")
    assert "Indice de pranchas" in pacote
