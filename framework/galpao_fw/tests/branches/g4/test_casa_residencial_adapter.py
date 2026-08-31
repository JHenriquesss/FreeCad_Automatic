"""Adaptador residencial REAL: tres disciplinas calculadas + a conferencia
NBR 5410 9.5.2 entre a planta e a instalacao declarada (branch G4)."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import arquitetura_residencial as ar
import casa_residencial as cr
import desenho_casa_residencial as dcr
from builtin_adapters import register_builtin_adapters
from project_loop import describe_adapters, normalize_spec, run_project, verify_project_run


ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = ROOT.parents[1]
SPEC_PERSISTIDO = REPO_ROOT / "projects" / "casa-residencial" / "project-spec.json"


@pytest.fixture(scope="module")
def spec():
    return json.loads(SPEC_PERSISTIDO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module", autouse=True)
def _adaptadores():
    register_builtin_adapters()


@pytest.fixture(scope="module")
def execucao(spec, tmp_path_factory):
    destino = tmp_path_factory.mktemp("casa-residencial") / "run"
    manifesto = run_project(spec, destino, {"generate_2d": True})
    return manifesto, destino


# --- contrato do adaptador -------------------------------------------------

DISCIPLINAS = {"arquitetura", "estrutura", "eletrico", "hidraulica"}


def test_adaptador_declara_as_quatro_disciplinas():
    """G13: 'estrutura' entrou. Era a disciplina que faltava - a casa tinha
    instalacoes e nao tinha laje, viga, pilar nem fundacao."""
    capacidades = {item["name"]: item for item in describe_adapters()}
    assert "casa-residencial" in capacidades
    real = capacidades["casa-residencial"]
    assert real["project_types"] == ["residencial"]
    assert set(real["disciplines"]) == DISCIPLINAS
    assert "drawings" in real["deliverables"]


def test_a_fixture_sintetica_continua_registrada():
    """O caso de contrato do nucleo nao foi apagado: sao dois adaptadores."""
    nomes = {item["name"] for item in describe_adapters()}
    assert {"casa-residencial", "casa-residencial-sintetica"} <= nomes


def test_o_adaptador_real_nao_se_declara_fixture(spec):
    normalizado = normalize_spec(spec)
    resultado, _ = cr.run_casa_residencial(normalizado, None)
    assert resultado["synthetic_fixture"] is False
    assert resultado["schema"] == "freecad-automatic/residential-house-result"


def test_nao_importa_o_turnkey_do_galpao():
    """Criterio 4 do desenho de generalizacao. Conferido no AST: mencionar o
    galpao num comentario e' legitimo, importa-lo nao."""
    import ast

    arvore = ast.parse(Path(cr.__file__).read_text(encoding="utf-8"))
    importados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module)
    assert not any(nome.startswith("galpao") for nome in importados), importados


# --- as quatro disciplinas calculam de verdade -----------------------------

def test_as_quatro_disciplinas_produzem_numero(execucao):
    manifesto, _ = execucao
    disciplinas = manifesto["disciplines"]
    assert set(disciplinas) == DISCIPLINAS
    for registro in disciplinas.values():
        assert registro["status"] == "needs_review", registro.get("errors")
        assert registro["gates"], "disciplina sem gate nao calculou nada"
    assert disciplinas["arquitetura"]["gates"]["previsao_carga"][
        "carga_iluminacao_va"] > 0
    assert disciplinas["hidraulica"]["gates"]["agua_velocidade"]["DN_mm"] > 0
    # a estrutura so calculou de verdade se a carga chegou ao chao: o gate da
    # fundacao existe e nomeia o tipo dimensionado
    assert disciplinas["estrutura"]["gates"]["fundacao"]["n_pilares"] > 0


def test_nenhuma_disciplina_e_marcada_passed(execucao):
    """Aprovacao para obra e' decisao de responsavel tecnico."""
    manifesto, _ = execucao
    assert all(registro["status"] != "passed"
               for registro in manifesto["disciplines"].values())


def test_gate_de_fixture_sintetica_nao_existe_mais(execucao):
    manifesto, _ = execucao
    for registro in manifesto["disciplines"].values():
        assert "synthetic_fixture" not in registro["gates"]


def test_manifesto_verifica_os_artefatos(execucao):
    manifesto, destino = execucao
    verificacao = verify_project_run(destino)
    assert verificacao["ok"] is True, verificacao["errors"]


# --- conferencia NBR 5410 9.5.2 (a costura que faltava) --------------------

def _arquitetura(nomes_e_tipos):
    return ar.rodar({"ambientes": [
        {"nome": nome, "tipo": tipo, "largura_m": largura,
         "comprimento_m": comprimento}
        for nome, tipo, largura, comprimento in nomes_e_tipos]})


def test_projeto_persistido_atende_a_previsao(execucao):
    manifesto, destino = execucao
    resultado = json.loads(
        (destino / "reports" / "adapter-result.json").read_text(encoding="utf-8"))
    conferencia = resultado["eletrico"]["conferencia_nbr5410"]
    assert conferencia["ok"] is True
    assert conferencia["totais"]["tomadas_declaradas"] == conferencia[
        "totais"]["tomadas_minimo"]
    assert conferencia["totais"]["pontos_orfaos"] == 0
    assert manifesto["disciplines"]["eletrico"]["gates"][
        "previsao_nbr5410_atendida"] is True


def test_tomada_faltando_reprova_o_eletrico():
    """Sala de 4x5 exige 4 TUG (9.5.2.2.1-d). Declarar 2 nao pode passar."""
    arquitetura = _arquitetura([("Sala", "sala", 4.0, 5.0)])
    circuitos = {"points": [
        {"id": "L1", "room": "Sala", "kind": "lighting", "power_va": 280.0},
        {"id": "T1", "room": "Sala", "kind": "tug", "power_va": 100.0},
        {"id": "T2", "room": "Sala", "kind": "tug", "power_va": 100.0},
    ]}
    conferencia = cr.conferir_previsao_nbr5410(arquitetura, circuitos)
    assert conferencia["ok"] is False
    erro = next(e for e in conferencia["erros"]
                if e["code"] == "tomadas_abaixo_do_minimo_nbr5410")
    assert (erro["minimo"], erro["declarado"]) == (4, 2)


def test_comodo_sem_ponto_de_luz_reprova():
    arquitetura = _arquitetura([("Sala", "sala", 4.0, 5.0)])
    circuitos = {"points": [
        {"id": "T%d" % i, "room": "Sala", "kind": "tug", "power_va": 100.0}
        for i in range(4)]}
    conferencia = cr.conferir_previsao_nbr5410(arquitetura, circuitos)
    assert "ponto_de_luz_ausente_nbr5410" in [e["code"] for e in conferencia["erros"]]


def test_potencia_abaixo_do_minimo_reprova_mesmo_com_o_numero_certo():
    """Cozinha com 4 TUG mas 100 VA cada: 9.5.2.2.2 exige 3x600 + 100."""
    arquitetura = _arquitetura([("Cozinha", "cozinha", 2.5, 3.6)])
    circuitos = {"points": [
        {"id": "L1", "room": "Cozinha", "kind": "lighting", "power_va": 100.0}
    ] + [{"id": "T%d" % i, "room": "Cozinha", "kind": "tug", "power_va": 100.0}
         for i in range(4)]}
    conferencia = cr.conferir_previsao_nbr5410(arquitetura, circuitos)
    erro = next(e for e in conferencia["erros"]
                if e["code"] == "carga_de_tomadas_abaixo_do_minimo_nbr5410")
    assert erro["minimo_va"] == 1900.0
    assert erro["declarado_va"] == 400.0


def test_ponto_em_ambiente_inexistente_nao_some_em_silencio():
    """Filtro de nome morto: o ponto que nao casa com nenhum ambiente teria
    sumido da contagem sem que ninguem soubesse."""
    arquitetura = _arquitetura([("Sala", "sala", 4.0, 5.0)])
    circuitos = {"points": [
        {"id": "L1", "room": "Sala", "kind": "lighting", "power_va": 280.0},
        {"id": "T9", "room": "Suite master", "kind": "tug", "power_va": 100.0},
    ]}
    conferencia = cr.conferir_previsao_nbr5410(arquitetura, circuitos)
    erro = next(e for e in conferencia["erros"]
                if e["code"] == "ambiente_desconhecido_no_circuito")
    assert erro["points"] == ["T9"]
    assert conferencia["totais"]["pontos_orfaos"] == 1


def test_acento_e_caixa_nao_criam_ambiente_diferente():
    arquitetura = _arquitetura([("Área de serviço", "area_servico", 2.0, 3.0)])
    circuitos = {"points": [
        {"id": "L1", "room": "AREA DE SERVICO", "kind": "lighting",
         "power_va": 100.0}] + [
        {"id": "T%d" % i, "room": "area de servico", "kind": "tug",
         "power_va": 600.0} for i in range(3)]}
    conferencia = cr.conferir_previsao_nbr5410(arquitetura, circuitos)
    assert conferencia["totais"]["pontos_orfaos"] == 0
    assert conferencia["ok"] is True


def test_tue_nao_conta_como_tomada_de_uso_geral():
    """9.5.3.1: ponto dedicado e' circuito independente, nao substitui a TUG."""
    arquitetura = _arquitetura([("Banheiro", "banheiro", 1.5, 2.4)])
    circuitos = {"points": [
        {"id": "L1", "room": "Banheiro", "kind": "lighting", "power_va": 100.0},
        {"id": "TUE", "room": "Banheiro", "kind": "tue", "power_va": 5400.0},
    ]}
    conferencia = cr.conferir_previsao_nbr5410(arquitetura, circuitos)
    assert "tomadas_abaixo_do_minimo_nbr5410" in [
        e["code"] for e in conferencia["erros"]]


def test_deficit_bloqueia_a_disciplina_no_loop(spec, tmp_path):
    """O caminho completo: tirar tomadas do spec tem que bloquear o eletrico."""
    reduzido = json.loads(json.dumps(spec))
    circuitos = reduzido["turnkey"]["eletrico"]["circuits"]
    removidos = {p["id"] for p in circuitos["points"]
                 if p["kind"] == "tug" and p["room"] == "Sala"}
    circuitos["points"] = [p for p in circuitos["points"]
                           if p["id"] not in removidos]
    circuitos["layout"]["points"] = [p for p in circuitos["layout"]["points"]
                                     if p["id"] not in removidos]
    for design in circuitos["designs"]:
        design["point_ids"] = [i for i in design["point_ids"]
                               if i not in removidos]
    circuitos["designs"] = [d for d in circuitos["designs"] if d["point_ids"]]
    manifesto = run_project(reduzido, tmp_path / "run-deficit", {"generate_2d": True})
    eletrico = manifesto["disciplines"]["eletrico"]
    assert eletrico["status"] == "blocked"
    assert "tomadas_abaixo_do_minimo_nbr5410" in [
        e["code"] for e in eletrico["errors"]]
    assert manifesto["status"] == "blocked"


def test_sem_arquitetura_a_conferencia_e_declarada_ausente(spec, tmp_path):
    """Sem programa, a conferencia nao acontece - e isso e' dito em voz alta."""
    sem_arquitetura = json.loads(json.dumps(spec))
    sem_arquitetura["turnkey"].pop("arquitetura")
    manifesto = run_project(sem_arquitetura, tmp_path / "run-sem-arq")
    eletrico = manifesto["disciplines"]["eletrico"]
    assert "conferencia_nbr5410_nao_executada" in [
        w["code"] for w in eletrico["warnings"]]
    assert "arquitetura" not in manifesto["disciplines"]


# --- entradas ausentes ficam explicitas ------------------------------------

def test_disciplina_sem_payload_fica_bloqueada():
    normalizado = normalize_spec({
        "schema": "freecad-automatic/project-spec", "schema_version": 1,
        "adapter": "casa-residencial",
        "project": {"slug": "x", "type": "residencial"},
        "turnkey": {"geometria": {"comprimento": 8.0, "vao": 6.0,
                                  "pe_direito": 2.7}},
    })
    normalizado["requested_disciplines"] = ["arquitetura", "hidraulica"]
    _resultado, registros = cr.run_casa_residencial(normalizado, None)
    assert registros["arquitetura"]["status"] == "blocked"
    assert registros["hidraulica"]["status"] == "blocked"
    assert "missing_architecture_input" in [
        e["code"] for e in registros["arquitetura"]["errors"]]


def test_arquitetura_invalida_bloqueia_sem_derrubar_a_execucao():
    normalizado = normalize_spec({
        "schema": "freecad-automatic/project-spec", "schema_version": 1,
        "adapter": "casa-residencial",
        "project": {"slug": "x", "type": "residencial"},
        "turnkey": {"geometria": {"comprimento": 8.0, "vao": 6.0,
                                  "pe_direito": 2.7},
                    "arquitetura": {"ambientes": "nao e uma lista"}},
    })
    normalizado["requested_disciplines"] = ["arquitetura"]
    _resultado, registros = cr.run_casa_residencial(normalizado, None)
    assert registros["arquitetura"]["status"] == "blocked"
    assert "architecture_calculation_failed" in [
        e["code"] for e in registros["arquitetura"]["errors"]]


# --- desenhos (renderizar-e-olhar) -----------------------------------------

def test_pranchas_sao_xml_valido(execucao):
    _manifesto, destino = execucao
    svgs = sorted((destino / "drawings").glob("*.svg"))
    assert [s.name for s in svgs] == [
        "conferencia-nbr5410.svg", "esquema-hidraulico.svg",
        "planta-formas.svg", "quadro-ambientes.svg"]
    for svg in svgs:
        raiz = ET.fromstring(svg.read_text(encoding="utf-8"))
        assert raiz.tag.endswith("svg")


def test_prancha_ausente_traz_o_motivo(execucao):
    manifesto, _ = execucao
    desenhos = manifesto["deliverables"]["drawings"]
    assert desenhos["status"] == "generated"
    assert desenhos["skipped"]["planta-baixa.svg"] == (
        "posicoes_dos_ambientes_nao_declaradas")


def test_o_quadro_mostra_todos_os_ambientes(execucao, spec):
    _manifesto, destino = execucao
    texto = (destino / "drawings" / "quadro-ambientes.svg").read_text(
        encoding="utf-8")
    for ambiente in spec["turnkey"]["arquitetura"]["ambientes"]:
        assert ambiente["nome"] in texto


def test_nome_com_caractere_xml_nao_quebra_a_prancha():
    """SVG e' XML: um '<' cru no nome do ambiente quebraria o arquivo inteiro."""
    arquitetura = ar.rodar({"ambientes": [
        {"nome": "Sala <estar & jantar>", "tipo": "sala", "largura_m": 4.0,
         "comprimento_m": 5.0}]})
    raiz = ET.fromstring(dcr.quadro_ambientes_svg(arquitetura))
    textos = [no.text for no in raiz.iter() if no.tag.endswith("text")]
    assert "Sala <estar & jantar>" in textos


def test_deficit_aparece_na_prancha_de_conferencia():
    arquitetura = _arquitetura([("Sala", "sala", 4.0, 5.0)])
    conferencia = cr.conferir_previsao_nbr5410(arquitetura, {"points": [
        {"id": "L1", "room": "Sala", "kind": "lighting", "power_va": 280.0},
        {"id": "T1", "room": "Sala", "kind": "tug", "power_va": 100.0}]})
    raiz = ET.fromstring(dcr.conferencia_svg(conferencia))
    textos = [no.text for no in raiz.iter() if no.tag.endswith("text")]
    assert "FALTAM 3 TUG" in textos
    assert any("NAO atendida" in (t or "") for t in textos)


def test_esquema_hidraulico_sem_rede_nao_finge_conteudo():
    raiz = ET.fromstring(dcr.esquema_hidraulico_svg({"redes": {}}))
    textos = [no.text or "" for no in raiz.iter() if no.tag.endswith("text")]
    assert any("nenhuma rede dimensionada" in t for t in textos)


def test_saturacao_do_esgoto_aparece_no_esquema():
    import hidraulica_residencial as hr
    hidraulica = hr.rodar({
        "aparelhos_agua": {"pia": 1}, "agua": {"L_real_m": 10.0},
        "aparelhos_esgoto": {"bacia": 20, "pia": 10},
        "cobertura": {"area_m2": 80.0, "i_mm_h": 150.0}})
    raiz = ET.fromstring(dcr.esquema_hidraulico_svg(hidraulica))
    textos = [no.text or "" for no in raiz.iter() if no.tag.endswith("text")]
    assert any("TABELA SATURADA" in t for t in textos)


# --- rotulo x geometria entre disciplinas ----------------------------------

def test_layout_com_area_diferente_do_programa_reprova():
    """O programa diz 20 m2, o layout eletrico desenha 12 m2: o numero de
    tomadas saiu de uma planta e foi conferido contra outra."""
    arquitetura = _arquitetura([("Sala", "sala", 4.0, 5.0)])
    circuitos = {
        "points": [],
        "layout": {"units": "m", "rooms": [
            {"id": "Sala", "name": "Sala", "x_m": 0.0, "y_m": 0.0,
             "width_m": 4.0, "depth_m": 3.0}]},
    }
    geometria = cr.conferir_geometria_layout(arquitetura, circuitos)
    assert geometria["ok"] is False
    erro = next(e for e in geometria["erros"]
                if e["code"] == "area_do_layout_diverge_do_programa")
    assert (erro["area_programa_m2"], erro["area_layout_m2"]) == (20.0, 12.0)


def test_ambiente_do_programa_ausente_no_layout_reprova():
    arquitetura = _arquitetura([("Sala", "sala", 4.0, 5.0),
                                ("Despensa", "despensa", 1.0, 2.0)])
    circuitos = {"points": [], "layout": {"units": "m", "rooms": [
        {"id": "Sala", "name": "Sala", "x_m": 0.0, "y_m": 0.0,
         "width_m": 5.0, "depth_m": 4.0}]}}
    geometria = cr.conferir_geometria_layout(arquitetura, circuitos)
    assert "ambiente_ausente_no_layout" in [e["code"] for e in geometria["erros"]]


def test_sem_layout_a_conferencia_geometrica_nao_inventa_veredito():
    arquitetura = _arquitetura([("Sala", "sala", 4.0, 5.0)])
    geometria = cr.conferir_geometria_layout(arquitetura, {"points": []})
    assert geometria == {"declarado": False, "ok": None, "erros": [],
                         "por_ambiente": []}


def test_projeto_persistido_tem_layout_coerente_com_o_programa(execucao):
    _manifesto, destino = execucao
    resultado = json.loads(
        (destino / "reports" / "adapter-result.json").read_text(encoding="utf-8"))
    geometria = resultado["eletrico"]["conferencia_nbr5410"]["geometria_layout"]
    assert geometria["declarado"] is True
    assert geometria["ok"] is True, geometria["erros"]
    assert len(geometria["por_ambiente"]) == 7


# --- geometria do texto na prancha -----------------------------------------

def test_nome_longo_nao_invade_a_coluna_vizinha():
    """Teste GEOMETRICO (nao substring): o texto de cada celula tem que caber
    na largura da sua coluna, senao a prancha sai ilegivel."""
    longo = "Sala de estar e jantar integrada com varanda gourmet"
    arquitetura = ar.rodar({"ambientes": [
        {"nome": longo, "tipo": "sala", "largura_m": 4.0, "comprimento_m": 5.0}]})
    raiz = ET.fromstring(dcr.quadro_ambientes_svg(arquitetura))
    largura_coluna_ambiente = 190
    celulas = [no.text or "" for no in raiz.iter() if no.tag.endswith("text")]
    nome_desenhado = next(t for t in celulas if t.startswith("Sala de estar"))
    assert nome_desenhado != longo, "nome longo tinha que ser truncado"
    assert nome_desenhado.endswith("...")
    assert dcr.largura_texto_px(nome_desenhado, 12) <= (
        largura_coluna_ambiente - dcr.FOLGA_CELULA_PX)


def test_nome_que_cabe_nao_e_truncado():
    arquitetura = ar.rodar({"ambientes": [
        {"nome": "Area de servico", "tipo": "area_servico", "largura_m": 2.0,
         "comprimento_m": 3.0}]})
    raiz = ET.fromstring(dcr.quadro_ambientes_svg(arquitetura))
    celulas = [no.text or "" for no in raiz.iter() if no.tag.endswith("text")]
    assert "Area de servico" in celulas


def test_toda_celula_das_tres_pranchas_cabe_na_coluna(execucao):
    """Varre as pranchas do projeto persistido e checa cada celula da tabela."""
    _manifesto, destino = execucao
    for nome in ("quadro-ambientes.svg", "conferencia-nbr5410.svg"):
        raiz = ET.fromstring(
            (destino / "drawings" / nome).read_text(encoding="utf-8"))
        largura_svg = float(raiz.get("width"))
        for no in raiz.iter():
            if not no.tag.endswith("text"):
                continue
            ancora = no.get("text-anchor")
            corpo = float(no.get("font-size"))
            comprimento = dcr.largura_texto_px(no.text or "", corpo)
            x = float(no.get("x"))
            esquerda = x if ancora == "start" else (
                x - comprimento if ancora == "end" else x - comprimento / 2)
            assert esquerda >= -1.0, (nome, no.text)
            assert esquerda + comprimento <= largura_svg + 1.0, (nome, no.text)
