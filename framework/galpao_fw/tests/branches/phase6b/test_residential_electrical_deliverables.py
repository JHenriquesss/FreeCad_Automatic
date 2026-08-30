"""Fase 6B: entregáveis (desenho + BIM) da elétrica residencial.

Regra desta suíte: SVG é XML. Todo desenho é PARSEADO com ElementTree e as
asserções olham nós/atributos, nunca substring — foi exatamente a checagem por
substring que deixou passar o unifilar XML-malformado do 'R <= 10 ohm' (S41).
"""

import copy
import json
from pathlib import Path
from xml.etree import ElementTree

import pytest

import bim_eletrico_residencial as bim
import desenho_eletrico_residencial as der
import layout_eletrico_residencial as lay
from project_io import run_project_file
from project_loop import describe_adapters, run_project, verify_project_run
from residencial_eletrica import run_residential_electrical


SVG_NS = "{http://www.w3.org/2000/svg}"
REPO_ROOT = Path(__file__).resolve().parents[3].parents[1]
PERSISTED_SPEC = (REPO_ROOT / "projects" / "casa-residencial-eletrica-sintetica"
                  / "project-spec.json")


def _spec():
    return json.loads(PERSISTED_SPEC.read_text(encoding="utf-8"))


def _circuits(spec=None):
    return (spec or _spec())["turnkey"]["eletrico"]["circuits"]


def _loop_spec(spec=None):
    spec = spec or _spec()
    turnkey = copy.deepcopy(spec["turnkey"])
    turnkey["geometria"] = spec["geometry"]
    return {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "adapter": "casa-residencial-eletrica",
        "project": {"slug": "casa-fase6b", "type": "residencial"},
        "geometria": spec["geometry"],
        "turnkey": turnkey,
        "source_refs": spec["source_refs"],
    }


def _result(spec=None):
    result, _ = run_residential_electrical(
        {"project_id": "casa-fase6b",
         "turnkey_spec": (spec or _spec())["turnkey"],
         "source_refs": (spec or _spec())["source_refs"]["eletrico"],
         "requested_disciplines": ["eletrico"]},
        None)
    return result


def _parse(svg):
    """Parseia o SVG como XML e devolve a raiz. Falha aqui = SVG quebrado."""
    root = ElementTree.fromstring(svg)
    assert root.tag == SVG_NS + "svg"
    return root


def _textos(root):
    return [(node.text or "") for node in root.iter(SVG_NS + "text")]


# --------------------------------------------------------------------------
# SVG é XML
# --------------------------------------------------------------------------

def test_os_tres_desenhos_sao_xml_bem_formado():
    result = _result()
    for svg in (der.unifilar_residencial_svg(result),
                der.quadro_cargas_residencial_svg(result),
                der.planta_eletrica_residencial_svg(result)):
        _parse(svg)


def test_caractere_reservado_no_dado_nao_quebra_o_svg():
    """O bug S41: um '<' ou '&' cru vindo do dado invalidava o XML inteiro."""
    spec = _spec()
    circuits = _circuits(spec)
    for room in circuits["layout"]["rooms"]:
        if room["id"] == "sala":
            room["name"] = "Sala <estar> & jantar"
    result = _result(spec)
    root = _parse(der.planta_eletrica_residencial_svg(result))
    assert "Sala <estar> & jantar" in _textos(root)


def test_desenhos_gravados_pelo_loop_continuam_xml_no_disco(tmp_path):
    manifest = run_project(_loop_spec(), tmp_path, options={
        "generate_ifc": False, "generate_2d": True, "require_source_refs": True})
    assert manifest["deliverables"]["drawings"]["status"] == "generated"
    for nome in manifest["deliverables"]["drawings"]["artifacts"]:
        _parse((tmp_path / nome).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Rótulo × geometria
# --------------------------------------------------------------------------

def test_retangulo_do_comodo_mede_o_que_o_rotulo_declara():
    """O cômodo desenhado tem a proporção da geometria declarada, não outra."""
    result = _result()
    root = _parse(der.planta_eletrica_residencial_svg(result))
    layout = result["circuits"]["layout_validation"]["layout"]
    declarados = {room["id"]: room for room in layout["rooms"]}
    medidos = []
    for node in root.iter(SVG_NS + "rect"):
        largura = float(node.attrib["width"])
        altura = float(node.attrib["height"])
        if node.attrib.get("fill") == "#fafafa":
            medidos.append((float(node.attrib["x"]), float(node.attrib["y"]),
                            largura, altura))
    sala = declarados["sala"]
    banheiro = declarados["banheiro"]
    esperado = ((sala["width_m"] * sala["depth_m"])
                / (banheiro["width_m"] * banheiro["depth_m"]))
    areas = sorted(largura * altura for _, _, largura, altura in medidos)
    assert areas, "nenhum cômodo desenhado"
    assert max(areas) / min(areas) == pytest.approx(esperado, rel=1e-3)


def test_planta_desenha_uma_ligacao_por_ponto_de_circuito():
    result = _result()
    root = _parse(der.planta_eletrica_residencial_svg(result))
    tracejadas = [node for node in root.iter(SVG_NS + "line")
                  if node.attrib.get("stroke-dasharray") == "5,4"]
    pontos = sum(len(design["point_ids"])
                 for design in result["circuits"]["designs"])
    assert len(tracejadas) == pontos + 1        # +1 = amostra da legenda


def test_comprimento_declarado_menor_que_a_distancia_do_layout_vira_aviso():
    """O ramal não pode ser mais curto que a reta quadro→ponto do layout."""
    spec = _spec()
    for design in _circuits(spec)["designs"]:
        if design["id"] == "C-L-01":
            design["length_m"] = 1.0
    avisos = bim.verificar_comprimentos(_result(spec))
    assert [item["code"] for item in avisos] == [
        "declared_length_shorter_than_layout_distance"]
    assert avisos[0]["design_id"] == "C-L-01"
    assert avisos[0]["layout_distance_m"] > avisos[0]["declared_length_m"]


def test_layout_coerente_nao_gera_aviso_de_comprimento():
    assert bim.verificar_comprimentos(_result()) == []


# --------------------------------------------------------------------------
# Saturação silenciosa
# --------------------------------------------------------------------------

def test_quadro_de_cargas_escreve_reprova_quando_o_calculo_reprova():
    """Prancha não pode mostrar 'atende' sobre condutor/proteção com OK falso."""
    result = _result()
    result["circuits"]["designs"][0]["protection"]["OK"] = False
    root = _parse(der.quadro_cargas_residencial_svg(result))
    assert "REPROVA" in _textos(root)
    vermelhos = [node.attrib.get("fill") for node in root.iter(SVG_NS + "text")
                 if node.text == "REPROVA"]
    assert vermelhos == ["#a00"]


def test_unifilar_marca_o_circuito_reprovado():
    result = _result()
    result["circuits"]["designs"][2]["conductor"]["OK"] = False
    root = _parse(der.unifilar_residencial_svg(result))
    assert _textos(root).count("REPROVA") == 1


def test_circuito_rejeitado_nao_some_em_silencio_do_desenho():
    """Circuito que falhou o dimensionamento não entra em `designs`.

    Sem o bloco de ausentes ele sumiria da prancha e o desenho pareceria
    completo faltando circuito — o padrão do quadro de materiais que
    desapareceu sem aviso.
    """
    spec = _spec()
    # carga fora do alcance de um ramal terminal: nenhuma seção única atende,
    # o condutor iria a paralelo e o design vira erro em vez de resultado.
    _circuits(spec)["points"][2]["power_va"] = 200000
    result = _result(spec)
    rejeitados = der.circuitos_nao_dimensionados(result)
    assert [item["design_id"] for item in rejeitados] == ["C-TUE-01"]
    assert len(result["circuits"]["designs"]) == 2

    for svg in (der.unifilar_residencial_svg(result),
                der.quadro_cargas_residencial_svg(result)):
        textos = " ".join(_textos(_parse(svg)))
        assert "C-TUE-01" in textos
        assert rejeitados[0]["code"] in textos


def test_curto_nao_avaliado_aparece_no_desenho_em_vez_de_sumir():
    result = _result()
    for svg in (der.unifilar_residencial_svg(result),
                der.quadro_cargas_residencial_svg(result)):
        textos = " ".join(_textos(_parse(svg)))
        assert "não avaliado" in textos


@pytest.mark.parametrize("campo, valor", [
    ("ambient_temperature_C", 75.0),     # acima da Tab.40 (satura em 60 °C)
    ("grouping_count", 12),              # acima da Tab.42 (satura em 9)
])
def test_dominio_fora_da_tabela_e_recusado_em_vez_de_saturado(campo, valor):
    spec = _spec()
    _circuits(spec)["designs"][0][campo] = valor
    result = _result(spec)
    assert result["status"] == "blocked"
    codigos = {item["code"] for item in result["errors"]}
    assert codigos & {"invalid_design_value", "unsupported_design_domain"}


# --------------------------------------------------------------------------
# Contrato do layout
# --------------------------------------------------------------------------

def test_sem_layout_a_planta_nao_e_inventada(tmp_path):
    spec = _spec()
    del _circuits(spec)["layout"]
    result = _result(spec)
    assert result["circuits"]["layout_validation"]["declared"] is False
    with pytest.raises(der.LayoutIndisponivel):
        der.planta_eletrica_residencial_svg(result)
    emitido = der.gerar_desenhos_residenciais(result, tmp_path)
    assert emitido["files"] == ["unifilar.svg", "quadro-cargas.svg"]
    assert emitido["skipped"] == {"planta-eletrica.svg": "layout_not_declared"}
    assert bim.membros_bim(result) == []


def test_sem_layout_o_escopo_diz_schematic_only():
    spec = _spec()
    del _circuits(spec)["layout"]
    result = _result(spec)
    assert result["scope"]["executive_deliverables"] == "schematic_only"
    assert result["status"] == "needs_review"
    assert any(item["code"] == "layout_not_declared"
               for item in result["warnings"])


def test_com_layout_valido_o_escopo_diz_implemented():
    assert _result()["scope"]["executive_deliverables"] == "implemented"


@pytest.mark.parametrize("mutator, code", [
    (lambda layout: layout["points"].pop(), "missing_layout_point"),
    (lambda layout: layout["points"].append(
        {"id": "X-99", "x_m": 1.0, "y_m": 1.0, "z_m": 1.0}),
     "unknown_layout_point"),
    (lambda layout: layout["points"][0].update({"x_m": 9.9, "y_m": 7.9}),
     "point_outside_declared_room"),
    (lambda layout: layout["rooms"].append(copy.deepcopy(layout["rooms"][0])),
     "duplicate_layout_room"),
    (lambda layout: layout["rooms"][1].update({"x_m": 0.0}),
     "overlapping_layout_rooms"),
    (lambda layout: layout["board"].update({"x_m": 99.0, "y_m": 99.0}),
     "board_outside_declared_rooms"),
    (lambda layout: layout["rooms"][0].pop("depth_m"), "missing_layout_field"),
    (lambda layout: layout["rooms"][0].update({"width_m": 0.0}),
     "invalid_layout_value"),
    (lambda layout: layout.update({"units": "cm"}), "invalid_layout_value"),
    (lambda layout: layout["board"].update({"z_m": 0.0}), "invalid_layout_value"),
])
def test_layout_incoerente_bloqueia_com_codigo(mutator, code):
    spec = _spec()
    circuits = _circuits(spec)
    mutator(circuits["layout"])
    validacao = lay.validate_electrical_layout(circuits)
    assert validacao["ok"] is False
    assert validacao["layout"] is None
    assert any(item["code"] == code for item in validacao["errors"]), \
        [item["code"] for item in validacao["errors"]]


def test_layout_invalido_bloqueia_a_execucao(tmp_path):
    spec = _spec()
    _circuits(spec)["layout"]["points"][0].update({"x_m": 9.9, "y_m": 7.9})
    manifest = run_project(_loop_spec(spec), tmp_path, options={
        "generate_ifc": True, "generate_2d": True, "require_source_refs": True})
    assert manifest["status"] == "blocked"
    assert any(item["code"] == "point_outside_declared_room"
               for item in manifest["disciplines"]["eletrico"]["errors"])


# --------------------------------------------------------------------------
# BIM
# --------------------------------------------------------------------------

def test_membros_bim_posicionam_o_que_o_layout_declara():
    result = _result()
    membros = bim.membros_bim(result)
    por_marca = {membro["marca"]: membro for membro in membros}
    layout = result["circuits"]["layout_validation"]["layout"]
    posicoes = {item["id"]: item for item in layout["points"]}
    assert por_marca["QD-01"]["tipo"] == "Board"
    assert por_marca["L-01"]["tipo"] == "Luminaire"
    assert por_marca["T-01"]["tipo"] == "Outlet"
    assert por_marca["TUE-01"]["tipo"] == "Outlet"
    for point_id, posicao in posicoes.items():
        assert por_marca[point_id]["centro"] == [
            posicao["x_m"] * 1000.0, posicao["y_m"] * 1000.0,
            posicao["z_m"] * 1000.0]
    cabos = [membro for membro in membros if membro["tipo"] == "Cable"]
    assert len(cabos) == sum(len(design["point_ids"])
                             for design in result["circuits"]["designs"])


def test_diametro_do_cabo_corresponde_a_secao_calculada():
    """Rótulo × geometria: o cilindro do IFC tem a área da seção dimensionada."""
    import math
    result = _result()
    membros = {membro["marca"]: membro for membro in bim.membros_bim(result)
               if membro["tipo"] == "Cable"}
    for design in result["circuits"]["designs"]:
        membro = membros[design["id"] + "-1"]
        diametro_m = membro["secao"]["D"]
        area_mm2 = math.pi * (diametro_m * 1000.0 / 2.0) ** 2
        assert area_mm2 == pytest.approx(design["conductor"]["secao_mm2"], rel=1e-9)


def test_loop_emite_ifc_e_desenhos_com_hash(tmp_path):
    ifc_emit = pytest.importorskip("ifc_emit")
    if not ifc_emit.disponivel():
        pytest.skip("ifcopenshell ausente")
    manifest = run_project_file(PERSISTED_SPEC, tmp_path, options={
        "generate_ifc": True, "generate_2d": True, "require_source_refs": True})
    assert manifest["status"] == "needs_review"
    assert manifest["deliverables"]["drawings"]["status"] == "generated"
    assert manifest["deliverables"]["ifc"]["status"] == "generated"
    assert manifest["deliverables"]["ifc"]["warnings"] == []
    caminhos = {item["path"]: item for item in manifest["artifacts"]}
    for esperado in ("drawings/unifilar.svg", "drawings/quadro-cargas.svg",
                     "drawings/planta-eletrica.svg",
                     "bim/eletrico-residencial.ifc"):
        assert esperado in caminhos, sorted(caminhos)
        assert caminhos[esperado]["sha256"]
        assert caminhos[esperado]["size"] > 0
    assert verify_project_run(tmp_path)["ok"] is True


def test_ifc_contem_as_classes_eletricas_esperadas(tmp_path):
    ifcopenshell = pytest.importorskip("ifcopenshell")
    destino = tmp_path / "residencial.ifc"
    assert bim.emitir_bim(_result(), str(destino)) is not None
    modelo = ifcopenshell.open(str(destino))
    assert len(modelo.by_type("IfcElectricDistributionBoard")) == 1
    assert len(modelo.by_type("IfcLightFixture")) == 1
    assert len(modelo.by_type("IfcOutlet")) == 2
    assert len(modelo.by_type("IfcCableSegment")) == 3


def test_ifc_indisponivel_sem_layout(tmp_path):
    spec = _spec()
    del _circuits(spec)["layout"]
    manifest = run_project(_loop_spec(spec), tmp_path, options={
        "generate_ifc": True, "generate_2d": True, "require_source_refs": True})
    assert manifest["status"] == "needs_review"
    assert manifest["deliverables"]["ifc"]["status"] == "not_available"
    assert manifest["deliverables"]["drawings"]["status"] == "generated"
    assert manifest["deliverables"]["drawings"]["skipped"] == {
        "planta-eletrica.svg": "layout_not_declared"}


def test_desenhos_nao_pedidos_ficam_not_requested(tmp_path):
    manifest = run_project(_loop_spec(), tmp_path, options={
        "generate_ifc": False, "generate_2d": False, "require_source_refs": True})
    assert manifest["deliverables"]["drawings"]["status"] == "not_requested"
    assert manifest["deliverables"]["ifc"]["status"] == "not_requested"


def test_capacidades_declaram_os_novos_entregaveis():
    capacidades = [item for item in describe_adapters()
                   if item["name"] == "casa-residencial-eletrica"]
    assert capacidades[0]["deliverables"] == ["report", "drawings", "ifc"]


def test_quadro_nomeia_o_piso_da_tabela_em_vez_de_dizer_ampacidade():
    """Rótulo × cálculo na prancha: o circuito de luz é de 0,79 A.

    Dizer 'ampacidade' na coluna GOVERN. faz o revisor procurar folga térmica
    onde não há critério nenhum — quem manda é o piso da tabela de ampacidade
    (2,5 mm²), acima do mínimo de 1,5 mm² da NBR 5410 Tab.47. A prancha tem de
    dizer o piso E o mínimo da norma.
    """
    result = _result()
    luz = [d for d in result["circuits"]["designs"]
           if d["conductor"]["piso_tabela"]]
    assert luz, "o caso do piso sumiu da fixture"

    root = _parse(der.quadro_cargas_residencial_svg(result))
    textos = _textos(root)

    assert "piso da tabela (norma 1,5 mm²)" in textos
    # 'ampacidade' só pode sobrar nas linhas em que a ampacidade de fato governa
    esperado = sum(1 for d in result["circuits"]["designs"]
                   if d["conductor"]["governante"] == "ampacidade")
    assert textos.count("ampacidade") == esperado
    assert all(not d["conductor"]["piso_tabela"] for d in
               result["circuits"]["designs"]
               if d["conductor"]["governante"] == "ampacidade")


def _largura_estimada(node):
    """Largura conservadora do texto em Arial: ~0,55 em por caractere."""
    fator = 0.60 if node.get("font-weight") == "bold" else 0.55
    return len(node.text or "") * float(node.get("font-size")) * fator


def test_nenhum_texto_do_quadro_invade_a_coluna_seguinte():
    """Colisão de texto não é XML malformado: o parser aceita, o revisor não.

    Foi assim que 'piso da tabela (norma 1,5 mm²)' entrou por cima do 'não' da
    coluna DR — verde na suíte, ilegível na prancha.
    """
    root = _parse(der.quadro_cargas_residencial_svg(_result()))
    largura_svg = float(root.get("width"))

    linhas = {}
    for node in root.iter(SVG_NS + "text"):
        if node.get("text-anchor") != "start":
            continue
        linhas.setdefault(node.get("y"), []).append(node)

    for y, nodes in linhas.items():
        nodes.sort(key=lambda n: float(n.get("x")))
        for atual, seguinte in zip(nodes, nodes[1:]):
            fim = float(atual.get("x")) + _largura_estimada(atual)
            assert fim <= float(seguinte.get("x")), (
                "'%s' invade '%s' na linha y=%s" % (atual.text, seguinte.text, y))
        ultimo = nodes[-1]
        assert float(ultimo.get("x")) + _largura_estimada(ultimo) <= largura_svg, (
            "'%s' passa da borda do desenho" % ultimo.text)
