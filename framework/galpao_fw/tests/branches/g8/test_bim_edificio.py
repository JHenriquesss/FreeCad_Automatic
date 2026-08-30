"""BIM do edificio multipavimento (G8): o modelo tem de ser o predio CALCULADO.

Duas camadas, como o resto do projeto (a barra verde do calculo nao cobre o
modelo):

  1. MODELO NEUTRO, sem ifcopenshell: contagem de pecas por tipo contra a malha
     calculada, empilhamento vertical sem interpenetracao, e a costura com o
     caminho FreeCAD (build_concreto.caixas) - as duas descricoes da mesma
     estrutura tem de dar a mesma caixa.
  2. IFC REAL, com ifcopenshell: o arquivo e' aberto de volta e a geometria e'
     MEDIDA (bbox mundial de cada peca). Ler a string do perfil nao pega uma
     viga deitada de lado nem um pilar com o eixo forte fora do plano - so medir
     o retangulo pega, e o historico deste projeto tem os dois casos.
"""

import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
GALPAO = HERE.parents[3]
sys.path.insert(0, str(GALPAO))

import bim_edificio as be
import build_concreto as bc
import edificio_multipavimento as em

SPEC = GALPAO.parents[1] / "projects" / "edificio-multipavimento" / "project-spec.json"


@pytest.fixture(scope="module")
def estrutura():
    payload = json.loads(SPEC.read_text(encoding="utf-8"))["turnkey"]["estrutura"]
    entrada = {chave: payload[chave] for chave in
               ("geometria", "pavimentos", "laje", "viga", "materiais", "vento")
               if chave in payload}
    return em.rodar(entrada)


@pytest.fixture(scope="module")
def membros(estrutura):
    return be.membros_bim(estrutura)


# --------------------------- camada 1: modelo neutro -----------------------

def test_o_modelo_tem_uma_peca_por_peca_calculada(estrutura, membros):
    """Contagem por tipo x malha calculada. Peca que sumiu no caminho abre
    normalmente no visualizador e nao denuncia nada - so a contagem denuncia."""
    conferencia = be.confere_modelo(estrutura, membros)
    assert conferencia["ok"], conferencia
    assert conferencia["por_tipo"] == conferencia["esperado"]


def test_um_pavimento_do_modelo_por_pavimento_do_calculo(estrutura, membros):
    nomes = {m["pavimento"] for m in membros}
    assert nomes == {p["nome"] for p in estrutura["descida"]["pavimentos"]}


def test_nenhuma_peca_ocupa_o_volume_de_outra(membros):
    """Laje sobre nervura sobre pilar: compartilham FACE, nunca volume."""
    resultado = be.confere_empilhamento(membros)
    assert resultado["OK"], resultado["conflitos"][:5]


def test_a_viga_em_y_e_recuada_para_nao_cruzar_a_viga_em_x(estrutura, membros):
    """Sem o recuo de b/2 as duas vigas se cruzariam no no' e o mesmo concreto
    seria contado duas vezes no quantitativo."""
    pav = estrutura["pavimento"]
    b_viga = pav["b_viga"]
    vy = [m for m in membros if m["marca"].startswith("VY-")]
    assert vy
    for membro in vy:
        comprimento = abs(membro["p2"][1] - membro["p1"][1]) / be.MM
        vao = pav["vaos_y"][int(membro["marca"].split("-")[2]) - 1]
        assert comprimento == pytest.approx(vao - b_viga, abs=1e-6)


def test_o_pilar_engrossa_ao_descer(estrutura, membros):
    """A secao adotada por lance vai para o modelo; nao a da base repetida."""
    pav = estrutura["pavimento"]
    niveis = [n["nome"] for n in be.niveis(estrutura, pav_pe(estrutura))]
    colunas = {m["marca"]: m for m in membros if m["tipo"] == "Column"}
    areas = []
    for nome in niveis:
        membro = colunas["P11-%s" % nome]
        areas.append(membro["secao"]["bf"] * membro["secao"]["d"])
    # da base para o topo a area nunca cresce (o pilar continuo nao encolhe ao descer)
    assert all(a >= b - 1e-12 for a, b in zip(areas, areas[1:])), areas


def pav_pe(estrutura):
    return be._pe_direito(estrutura["pilares"])


def test_a_laje_carrega_armadura_so_no_painel_que_foi_dimensionado(membros):
    """O calculo dimensionou UM painel (o de maior area). Copiar essa armadura
    para os demais publicaria um numero que ninguem calculou naquela posicao."""
    lajes = [m for m in membros if m["tipo"] == "Slab"]
    com_armadura = [m for m in lajes if "armadura" in m]
    assert com_armadura
    n_niveis = len({m["pavimento"] for m in lajes})
    assert len(com_armadura) == n_niveis        # um painel critico por pavimento
    assert len(com_armadura) < len(lajes)


def test_geometria_impossivel_e_recusada(estrutura):
    """Viga mais rasa que a laje descreve um predio que nao existe."""
    import copy
    quebrado = copy.deepcopy(estrutura)
    quebrado["pavimento"]["h_viga"] = 0.05
    quebrado["pavimento"]["peso_viga_kN_m"] = round(
        25.0 * quebrado["pavimento"]["b_viga"] * 0.05, 3)
    with pytest.raises(be.GeometriaIncoerente):
        be.membros_bim(quebrado)


def test_secao_da_viga_incoerente_com_o_peso_da_analise_e_recusada(estrutura):
    """A secao publicada tem de reproduzir o peso proprio que ENTROU na analise:
    divergir e' desenhar uma viga que nao e' a calculada."""
    import copy
    quebrado = copy.deepcopy(estrutura)
    quebrado["pavimento"]["h_viga"] = 0.80        # peso_viga_kN_m fica o antigo
    with pytest.raises(be.GeometriaIncoerente):
        be.membros_bim(quebrado)


# ------------- camada 1b: cross-check com o caminho FreeCAD ----------------

def test_o_modelo_puro_e_o_do_freecad_descrevem_a_mesma_caixa(membros):
    """`build_concreto.caixas` (o que o FreeCAD monta) x o modelo neutro (o que
    vira IFC). Duas descricoes da mesma estrutura por caminhos independentes:
    e' a costura que impede uma delas de envelhecer sozinha."""
    caixas = bc.caixas(membros)
    assert len(caixas) == len(membros)
    por_nome = {c["name"]: c for c in caixas}
    for membro in membros:
        caixa = por_nome[membro["marca"]]
        x0, x1, y0, y1, z0, z1 = be._aabb(membro)
        assert caixa["origem"] == pytest.approx((x0, y0, z0), abs=1e-6), membro["marca"]
        assert caixa["dims"] == pytest.approx(
            (x1 - x0, y1 - y0, z1 - z0), abs=1e-6), membro["marca"]


def test_o_volume_de_concreto_bate_nos_dois_caminhos(membros):
    puro = be.quantitativo(membros)["vol_concreto_m3"]
    freecad = bc._takeoff(bc.caixas(membros))["vol_concreto_m3"]
    assert abs(puro - freecad) <= 0.001


# ----------------------------- camada 2: IFC real ---------------------------

ifcopenshell = pytest.importorskip("ifcopenshell")


@pytest.fixture(scope="module")
def modelo_ifc(estrutura, tmp_path_factory):
    destino = tmp_path_factory.mktemp("bim") / "edificio.ifc"
    be.emitir_bim(estrutura, str(destino))
    return ifcopenshell.open(str(destino))


def _caixa_mundial(entidade):
    """bbox da peca em COORDENADAS DO MUNDO (m): a geometria que o visualizador
    mostra, nao a do perfil local."""
    import ifcopenshell.geom as geom
    import ifcopenshell.util.shape as shape

    ajustes = geom.settings()
    ajustes.set("use-world-coords", True)
    forma = geom.create_shape(ajustes, entidade)
    minimo, maximo = shape.get_bbox(shape.get_vertices(forma.geometry))
    return minimo, maximo


def _por_nome(modelo, nome):
    return next(e for e in modelo.by_type("IfcProduct") if e.Name == nome)


def test_ifc4_com_um_pavimento_por_pavimento(modelo_ifc, estrutura):
    assert modelo_ifc.schema == "IFC4"
    andares = modelo_ifc.by_type("IfcBuildingStorey")
    assert len(andares) == len(estrutura["descida"]["pavimentos"])
    pe = pav_pe(estrutura)
    for andar in andares:
        assert andar.Elevation is not None
    elevacoes = sorted(a.Elevation for a in andares)
    assert elevacoes[0] == pytest.approx(pe * 1000.0)


def test_nenhum_elemento_fica_fora_da_arvore_espacial(modelo_ifc):
    """Elemento sem container nao aparece no navegador do visualizador."""
    contidos = set()
    for relacao in modelo_ifc.by_type("IfcRelContainedInSpatialStructure"):
        contidos.update(e.id() for e in relacao.RelatedElements)
    produtos = [e for e in modelo_ifc.by_type("IfcProduct")
                if e.is_a() in ("IfcColumn", "IfcBeam", "IfcSlab")]
    assert produtos
    assert [e.Name for e in produtos if e.id() not in contidos] == []


def test_o_pilar_nao_esta_girado_90_graus(modelo_ifc, estrutura):
    """MEDE o retangulo emitido. 'h' e' a dimensao na direcao X (a convencao com
    que `pilar_continuo` calculou a esbeltez); trocado com 'b', o pilar entra no
    BIM com o eixo forte fora da direcao dimensionada."""
    nome_base = be.niveis(estrutura, pav_pe(estrutura))[0]["nome"]
    lance = list(estrutura["pilares"]["P11"]["lances"])[-1]     # lance da base
    minimo, maximo = _caixa_mundial(_por_nome(modelo_ifc, "P11-%s" % nome_base))
    dims = maximo - minimo
    assert dims[0] == pytest.approx(lance["h"], abs=1e-4)
    assert dims[1] == pytest.approx(lance["b"], abs=1e-4)


def test_a_viga_nao_esta_deitada_de_lado(modelo_ifc, estrutura):
    """A nervura tem de estar EM PE: largura no plano horizontal, altura em Z."""
    pav = estrutura["pavimento"]
    nivel = be.niveis(estrutura, pav_pe(estrutura))[0]["nome"]
    altura = pav["h_viga"] - estrutura["laje"]["h"]
    for marca, eixo_do_vao in (("VX-0-1-%s" % nivel, 0), ("VY-0-1-%s" % nivel, 1)):
        minimo, maximo = _caixa_mundial(_por_nome(modelo_ifc, marca))
        dims = maximo - minimo
        transversal = 1 - eixo_do_vao
        assert dims[transversal] == pytest.approx(pav["b_viga"], abs=1e-4), marca
        assert dims[2] == pytest.approx(altura, abs=1e-4), marca


def test_a_cadeia_vertical_fecha_sem_folga_e_sem_embutir(modelo_ifc, estrutura):
    """pilar -> nervura -> laje: topo de um = fundo do seguinte. Meia viga
    embutida no pilar foi um defeito real do galpao de concreto, e so aparece
    medindo as cotas do arquivo emitido."""
    pe = pav_pe(estrutura)
    nivel = be.niveis(estrutura, pe)[0]["nome"]
    _, topo_pilar = _caixa_mundial(_por_nome(modelo_ifc, "P11-%s" % nivel))
    base_viga, topo_viga = _caixa_mundial(_por_nome(modelo_ifc, "VX-0-1-%s" % nivel))
    base_laje, topo_laje = _caixa_mundial(_por_nome(modelo_ifc, "L11-%s" % nivel))
    assert base_viga[2] == pytest.approx(topo_pilar[2], abs=1e-4)
    assert base_laje[2] == pytest.approx(topo_viga[2], abs=1e-4)
    assert topo_laje[2] == pytest.approx(pe, abs=1e-4)


def test_a_armadura_calculada_viaja_no_pset(modelo_ifc):
    psets = [p for p in modelo_ifc.by_type("IfcPropertySet")
             if p.Name == "Pset_Armadura"]
    assert psets
    nomes = {prop.Name for prop in psets[0].HasProperties}
    assert "As_long_cm2" in nomes or "As_x_cm2_m" in nomes


def test_pavimentos_com_o_mesmo_nome_sao_recusados(estrutura):
    """O nome do pavimento e' a chave do IfcBuildingStorey e o sufixo da marca.
    Repetido, dois andares viram um so e as pecas de um somem dentro do outro."""
    import copy
    quebrado = copy.deepcopy(estrutura)
    pavimentos = quebrado["descida"]["pavimentos"]
    pavimentos[1]["nome"] = pavimentos[0]["nome"]
    with pytest.raises(be.GeometriaIncoerente):
        be.membros_bim(quebrado)


def test_pilar_da_malha_sem_dimensionamento_e_recusado(estrutura):
    """Pular em silencio deixaria um furo na malha, e o modelo mostraria uma
    laje sem apoio."""
    import copy
    quebrado = copy.deepcopy(estrutura)
    quebrado["pilares"].pop(sorted(quebrado["pilares"])[0])
    with pytest.raises(be.GeometriaIncoerente):
        be.membros_bim(quebrado)
