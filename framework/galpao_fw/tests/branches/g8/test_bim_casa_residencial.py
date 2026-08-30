"""BIM da arquitetura residencial (G8): modelo so onde ha posicao DECLARADA.

`desenho_casa_residencial` diz, na sua abertura, que nao ha planta baixa porque
"o programa declara area e perimetro, nao posicoes". O BIM herda exatamente a
mesma regra: com layout declarado ha modelo; sem ele, ausencia explicita - nunca
comodos em posicoes arbitradas.

Estes testes fixam as duas metades disso: o que o modulo RECUSA (layout que nao
reproduz o programa, comodo sobrando, parede obliqua) e o que ele EMITE (areas
medidas no IFC de volta, parede em pe e nao deitada).
"""

import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
GALPAO = HERE.parents[3]
sys.path.insert(0, str(GALPAO))

import arquitetura_residencial as arq
import bim_casa_residencial as bim

SPEC = GALPAO.parents[1] / "projects" / "casa-residencial" / "project-spec.json"


@pytest.fixture(scope="module")
def turnkey():
    return json.loads(SPEC.read_text(encoding="utf-8"))["turnkey"]


@pytest.fixture(scope="module")
def programa(turnkey):
    return arq.rodar(turnkey["arquitetura"])


@pytest.fixture(scope="module")
def layout_declarado(turnkey):
    """Os retangulos que o spec ja declara (na secao do projeto eletrico)."""
    eletrico = turnkey["eletrico"]["circuits"]["layout"]
    return {"units": eletrico["units"], "rooms": copy.deepcopy(eletrico["rooms"])}


@pytest.fixture(scope="module")
def layout(programa, layout_declarado):
    validacao = bim.validar_layout(layout_declarado, programa)
    assert validacao["ok"], validacao["errors"]
    return validacao["layout"]


# ------------------------------- o que recusa -------------------------------

def test_sem_layout_nao_ha_modelo(programa):
    """Ausencia de posicao e' ausencia de dado, nao um modelo vazio."""
    validacao = bim.validar_layout(None, programa)
    assert validacao == {"declared": False, "ok": False, "errors": [],
                         "layout": None}
    assert bim.membros_bim(programa, None) == []


def test_retangulo_que_nao_reproduz_a_area_do_programa_e_recusado(
        programa, layout_declarado):
    """A previsao de carga da NBR 5410 9.5.2 foi feita sobre area e perimetro;
    um retangulo diferente descreve outra casa com o mesmo nome."""
    quebrado = copy.deepcopy(layout_declarado)
    quebrado["rooms"][0]["width_m"] = quebrado["rooms"][0]["width_m"] + 1.0
    validacao = bim.validar_layout(quebrado, programa)
    assert not validacao["ok"]
    codigos = {e["code"] for e in validacao["errors"]}
    assert "layout_area_mismatch" in codigos


def test_ambiente_do_programa_sem_retangulo_e_recusado(programa, layout_declarado):
    quebrado = copy.deepcopy(layout_declarado)
    quebrado["rooms"].pop()
    validacao = bim.validar_layout(quebrado, programa)
    assert not validacao["ok"]
    assert "missing_layout_room" in {e["code"] for e in validacao["errors"]}


def test_comodo_que_o_programa_nao_tem_e_recusado(programa, layout_declarado):
    quebrado = copy.deepcopy(layout_declarado)
    extra = copy.deepcopy(quebrado["rooms"][0])
    extra.update({"id": "Adega", "name": "Adega", "x_m": 100.0, "y_m": 100.0})
    quebrado["rooms"].append(extra)
    validacao = bim.validar_layout(quebrado, programa)
    assert not validacao["ok"]
    assert "layout_room_not_in_programme" in {e["code"] for e in validacao["errors"]}


def test_comodos_sobrepostos_sao_recusados(programa, layout_declarado):
    """A regra vem da primitiva compartilhada com a eletrica; aqui so se prova
    que a arquitetura tambem a aplica."""
    quebrado = copy.deepcopy(layout_declarado)
    quebrado["rooms"][1]["x_m"] = quebrado["rooms"][0]["x_m"]
    quebrado["rooms"][1]["y_m"] = quebrado["rooms"][0]["y_m"]
    validacao = bim.validar_layout(quebrado, programa)
    assert not validacao["ok"]
    assert "overlapping_layout_rooms" in {e["code"] for e in validacao["errors"]}


def test_parede_obliqua_e_recusada_em_vez_de_sair_torta(programa, layout_declarado):
    quebrado = copy.deepcopy(layout_declarado)
    quebrado["paredes"] = [{"id": "P1", "x0_m": 0.0, "y0_m": 0.0,
                            "x1_m": 3.0, "y1_m": 3.0,
                            "espessura_m": 0.15, "altura_m": 2.7}]
    validacao = bim.validar_layout(quebrado, programa)
    assert not validacao["ok"]
    assert "oblique_wall" in {e["code"] for e in validacao["errors"]}


def test_piso_so_existe_se_a_espessura_for_declarada(programa, layout):
    """Sem `piso_espessura_m` nao ha piso - e nao um piso de espessura default."""
    assert layout["piso_espessura_m"] is None
    membros = bim.membros_bim(programa, layout)
    assert not [m for m in membros if m["tipo"] == "Slab"]


# ------------------------------- o que emite --------------------------------

def test_um_ambiente_por_ambiente_do_programa(programa, layout):
    membros = bim.membros_bim(programa, layout)
    espacos = [m for m in membros if m["tipo"] == "Space"]
    assert len(espacos) == len(programa["ambientes"])
    assert {m["marca"] for m in espacos} == {a["nome"] for a in programa["ambientes"]}


def test_a_area_emitida_reproduz_o_programa(programa, layout):
    conferencia = bim.confere_areas(programa, bim.membros_bim(programa, layout))
    assert conferencia["ok"], conferencia


def test_o_ambiente_tem_a_altura_do_pe_direito(programa, layout):
    membros = [m for m in bim.membros_bim(programa, layout) if m["tipo"] == "Space"]
    for membro in membros:
        assert membro["dims"][2] / bim.MM == pytest.approx(
            programa["pe_direito_m"], abs=1e-9)


def test_sem_pe_direito_declarado_nao_ha_volume_a_emitir(programa, layout):
    sem_pe = dict(programa, pe_direito_m=None)
    assert bim.membros_bim(sem_pe, layout) == []


# ------------------------------ IFC real ------------------------------------

ifcopenshell = pytest.importorskip("ifcopenshell")


def _caixa_mundial(entidade):
    import ifcopenshell.geom as geom
    import ifcopenshell.util.shape as shape

    ajustes = geom.settings()
    ajustes.set("use-world-coords", True)
    forma = geom.create_shape(ajustes, entidade)
    return shape.get_bbox(shape.get_vertices(forma.geometry))


def test_ifc4_com_um_ifcspace_por_ambiente(programa, layout, tmp_path):
    destino = tmp_path / "casa.ifc"
    assert bim.emitir_bim(programa, layout, str(destino))
    modelo = ifcopenshell.open(str(destino))
    assert modelo.schema == "IFC4"
    assert len(modelo.by_type("IfcSpace")) == len(programa["ambientes"])


def test_o_ambiente_entra_por_agregacao_no_pavimento(programa, layout, tmp_path):
    """IfcSpace e' estrutura ESPACIAL: entra por IfcRelAggregates. Contido como
    produto, ele aparece no 3D mas nao na arvore de ambientes do visualizador."""
    destino = tmp_path / "casa.ifc"
    bim.emitir_bim(programa, layout, str(destino))
    modelo = ifcopenshell.open(str(destino))
    agregados = set()
    for relacao in modelo.by_type("IfcRelAggregates"):
        agregados.update(o.id() for o in relacao.RelatedObjects)
    assert all(e.id() in agregados for e in modelo.by_type("IfcSpace"))


def test_a_area_do_ifcspace_medida_bate_com_o_programa(programa, layout, tmp_path):
    """Mede o solido emitido, nao a string do nome."""
    destino = tmp_path / "casa.ifc"
    bim.emitir_bim(programa, layout, str(destino))
    modelo = ifcopenshell.open(str(destino))
    por_nome = {a["nome"]: a for a in programa["ambientes"]}
    for espaco in modelo.by_type("IfcSpace"):
        minimo, maximo = _caixa_mundial(espaco)
        dims = maximo - minimo
        area = float(dims[0]) * float(dims[1])
        assert area == pytest.approx(por_nome[espaco.Name]["area_m2"], rel=1e-3)
        assert float(dims[2]) == pytest.approx(programa["pe_direito_m"], abs=1e-4)


def test_a_parede_declarada_sai_em_pe_e_com_a_espessura_declarada(
        programa, layout_declarado, tmp_path):
    """Espessura no plano horizontal e altura em Z - a parede deitada de lado e'
    a mesma familia de defeito da viga deitada."""
    com_paredes = copy.deepcopy(layout_declarado)
    com_paredes["paredes"] = [
        {"id": "PAR-X", "x0_m": 0.0, "y0_m": 0.0, "x1_m": 5.0, "y1_m": 0.0,
         "espessura_m": 0.15, "altura_m": 2.7},
        {"id": "PAR-Y", "x0_m": 0.0, "y0_m": 0.0, "x1_m": 0.0, "y1_m": 4.0,
         "espessura_m": 0.15, "altura_m": 2.7}]
    validacao = bim.validar_layout(com_paredes, programa)
    assert validacao["ok"], validacao["errors"]
    destino = tmp_path / "casa-paredes.ifc"
    bim.emitir_bim(programa, validacao["layout"], str(destino))
    modelo = ifcopenshell.open(str(destino))
    paredes = {p.Name: p for p in modelo.by_type("IfcWall")}
    assert set(paredes) == {"PAR-X", "PAR-Y"}
    for nome, eixo in (("PAR-X", 0), ("PAR-Y", 1)):
        minimo, maximo = _caixa_mundial(paredes[nome])
        dims = maximo - minimo
        assert float(dims[1 - eixo]) == pytest.approx(0.15, abs=1e-4), nome
        assert float(dims[2]) == pytest.approx(2.7, abs=1e-4), nome
        assert float(minimo[2]) == pytest.approx(0.0, abs=1e-4), nome


def test_paredes_declaradas_que_se_cruzam_reprovam_o_modelo(programa, layout_declarado):
    """Duas paredes ocupando o mesmo canto e' dado do projetista, nao erro do
    emissor - mas modelo com solido dentro de solido nao e' entregavel, entao as
    pecas sao NOMEADAS em vez de o conflito ficar calado."""
    com_cruzamento = copy.deepcopy(layout_declarado)
    com_cruzamento["paredes"] = [
        {"id": "PAR-N", "x0_m": 0.0, "y0_m": 0.0, "x1_m": 5.0, "y1_m": 0.0,
         "espessura_m": 0.15, "altura_m": 2.7},
        {"id": "PAR-O", "x0_m": 0.0, "y0_m": 0.0, "x1_m": 0.0, "y1_m": 4.0,
         "espessura_m": 0.15, "altura_m": 2.7}]
    validacao = bim.validar_layout(com_cruzamento, programa)
    assert validacao["ok"], validacao["errors"]
    resultado = bim.confere_solidos(bim.membros_bim(programa, validacao["layout"]))
    assert not resultado["OK"]
    assert {resultado["conflitos"][0]["a"], resultado["conflitos"][0]["b"]} == {
        "PAR-N", "PAR-O"}


def test_o_ambiente_nao_conta_como_solido_na_varredura(programa, layout_declarado):
    """IfcSpace e' volume de uso: o piso e as paredes que o delimitam o tocam
    legitimamente, e conta-lo faria toda casa parecer um amontoado de conflitos."""
    com_piso = copy.deepcopy(layout_declarado)
    com_piso["piso_espessura_m"] = 0.08
    validacao = bim.validar_layout(com_piso, programa)
    assert validacao["ok"], validacao["errors"]
    membros = bim.membros_bim(programa, validacao["layout"])
    assert [m for m in membros if m["tipo"] == "Slab"]
    assert bim.confere_solidos(membros)["OK"]
