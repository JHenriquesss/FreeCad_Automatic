"""A estrutura da casa no Project Loop (G13): disciplina, costura e BIM.

Tres camadas, porque a barra verde de uma nao cobre a outra:

  1. ADAPTADOR - 'estrutura' virou disciplina do adaptador residencial e o escopo
     deixou de dizer `not_available`. Disciplina que ninguem declara continua
     ausente: capacidade nao declarada e' capacidade que nao existe.
  2. COSTURA arquitetura x estrutura - as duas descrevem a MESMA casa. Programa
     maior que a malha, pe-direito divergente ou comodo fora do retangulo da
     malha REPROVAM, em vez de o Loop desenhar uma planta e calcular outra.
  3. IFC REAL - o arquivo e' aberto de volta e a geometria MEDIDA. Ler a string
     do perfil nao pega uma viga deitada de lado nem um baldrame flutuando acima
     do terreno; so medir o retangulo e as cotas pega.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
GALPAO = HERE.parents[3]
sys.path.insert(0, str(GALPAO))

import bim_edificio as be
import casa_residencial as cr
import estrutura_casa as ec
from builtin_adapters import register_builtin_adapters
from project_loop import run_project

SPEC = GALPAO.parents[1] / "projects" / "casa-residencial" / "project-spec.json"
MM = be.MM


@pytest.fixture(scope="module")
def spec():
    return json.loads(SPEC.read_text(encoding="utf-8"))


@pytest.fixture(scope="module", autouse=True)
def _adaptadores():
    register_builtin_adapters()


@pytest.fixture(scope="module")
def execucao(spec, tmp_path_factory):
    destino = tmp_path_factory.mktemp("casa-g13") / "run"
    manifesto = run_project(spec, destino,
                            {"generate_2d": True, "generate_ifc": True})
    return manifesto, destino


@pytest.fixture(scope="module")
def estrutura(spec):
    """O resultado do CALCULO da estrutura, direto do spec persistido."""
    return ec.rodar(copy.deepcopy(spec["turnkey"]["estrutura"]))


# --------------------------------------------------------------- 1. adaptador

def test_o_spec_persistido_declara_estrutura(spec):
    """A casa de referencia do repositorio passa a ter estrutura declarada; sem
    isso a disciplina existiria so nos testes."""
    estrutura = spec["turnkey"]["estrutura"]
    assert estrutura["geometria"]["vaos_x"] and estrutura["geometria"]["vaos_y"]
    assert estrutura["fundacao"]["perfil_spt"]
    assert "A CONFIRMAR" in estrutura["fundacao"]["perfil_spt_proveniencia"]


def test_a_malha_cobre_o_envelope_do_projeto(spec):
    """A geometria comum do Loop e os vaos da estrutura sao o MESMO envelope."""
    geometria = spec["geometry"]
    estrutura = spec["turnkey"]["estrutura"]["geometria"]
    assert sum(estrutura["vaos_x"]) == pytest.approx(geometria["comprimento"])
    assert sum(estrutura["vaos_y"]) == pytest.approx(geometria["vao"])
    assert estrutura["pe_direito"] == pytest.approx(geometria["pe_direito"])


def test_estrutura_entra_no_manifesto_com_gate(execucao):
    manifesto, _ = execucao
    registro = manifesto["disciplines"]["estrutura"]
    assert registro["status"] == "needs_review", registro.get("errors")
    assert registro["gates"]["fundacao"]["OK"]
    assert registro["gates"]["viga_baldrame"]["OK"]
    assert registro["gates"]["pilares"]["n"] == 12
    # nenhuma disciplina e' marcada 'passed': aprovacao e' decisao de RT
    assert registro["status"] != "passed"


def test_o_escopo_deixou_de_dizer_estrutura_not_available(execucao, tmp_path):
    manifesto, destino = execucao
    resultado = json.loads(
        (destino / "reports" / "adapter-result.json").read_text(encoding="utf-8"))
    escopo = resultado["scope"]
    assert escopo["estrutura"] == "implemented"
    assert escopo["fundacao"] == "implemented"
    assert escopo["viga_baldrame"] == "implemented"
    # e o que NAO e' calculado continua dito em voz alta
    assert escopo["acao_horizontal"] == "not_available"


def test_sem_estrutura_declarada_a_disciplina_nao_e_inventada(spec):
    """Capacidade nao declarada e' capacidade que nao existe: o spec sem
    `turnkey.estrutura` nao ganha uma estrutura deduzida do envelope."""
    normalizado = {"project_id": "sem-estrutura",
                   "turnkey_spec": {k: v for k, v in spec["turnkey"].items()
                                    if k != "estrutura"},
                   "requested_disciplines": ["arquitetura", "estrutura"]}
    resultado, registros = cr.run_casa_residencial(normalizado, None, None)
    assert registros["estrutura"]["status"] == "blocked"
    assert registros["estrutura"]["errors"][0]["code"] == "missing_structure_input"
    assert resultado["estrutura"] is None
    assert resultado["scope"]["estrutura"] == "not_available"


# ------------------------------------------- 2. costura arquitetura x estrutura

def _arquitetura(spec):
    import arquitetura_residencial as ar

    return ar.rodar(copy.deepcopy(spec["turnkey"]["arquitetura"]))


def test_a_casa_de_referencia_passa_na_costura(spec):
    conferencia = cr.conferir_arquitetura_estrutura(
        _arquitetura(spec), spec["turnkey"]["estrutura"],
        spec["turnkey"]["eletrico"]["circuits"]["layout"])
    assert conferencia["ok"], conferencia["erros"]
    assert conferencia["area_programa_m2"] <= conferencia["area_malha_m2"]
    assert conferencia["layout_conferido"] is True


def test_o_layout_chega_ate_a_estrutura_na_rodada_real(spec):
    """`comodos_fora_da_malha == []` tem dois significados possiveis: nenhum
    comodo fora, ou a conferencia geometrica nao rodou. `layout_conferido`
    separa os dois - sem ele, um layout que nunca chegou ate aqui passaria por
    aprovado."""
    from project_loop import normalize_spec

    normalizado = normalize_spec(copy.deepcopy(spec))
    _resultado, registros = cr.run_casa_residencial(normalizado, None, None)
    conferencia = registros["estrutura"]["conferencia_arquitetura"]
    assert conferencia["layout_conferido"] is True
    assert not any(a["code"] == "conferencia_geometrica_nao_executada"
                   for a in registros["estrutura"]["warnings"])


def test_sem_layout_a_conferencia_geometrica_se_declara_ausente(spec):
    conferencia = cr.conferir_arquitetura_estrutura(
        _arquitetura(spec), spec["turnkey"]["estrutura"], None)
    assert conferencia["layout_conferido"] is False
    assert any(a["code"] == "conferencia_geometrica_nao_executada"
               for a in conferencia["avisos"])
    # a conferencia de AREA continua valendo mesmo sem layout
    assert conferencia["ok"] is True
    assert conferencia["area_malha_m2"] > 0


def test_malha_menor_que_a_casa_bloqueia_a_estrutura_na_rodada_real(spec):
    """A perturbacao que exercita a costura de ponta a ponta: o layout continua
    valido para o eletrico, mas nao cabe mais na malha declarada."""
    from project_loop import normalize_spec

    mau = copy.deepcopy(spec)
    mau["turnkey"]["estrutura"]["geometria"]["vaos_x"] = [3.0, 3.0]
    _resultado, registros = cr.run_casa_residencial(
        normalize_spec(mau), None, None)
    registro = registros["estrutura"]
    assert registro["status"] == "blocked"
    codigos = {e["code"] for e in registro["errors"]}
    assert "comodo_fora_da_malha_estrutural" in codigos
    assert "programa_maior_que_a_malha_estrutural" in codigos


def test_programa_maior_que_a_malha_reprova(spec):
    """Area util acima da coberta pela malha = metros quadrados de casa sem
    laje, viga nem pilar em cima."""
    estrutura = copy.deepcopy(spec["turnkey"]["estrutura"])
    estrutura["geometria"]["vaos_x"] = [2.0]
    estrutura["geometria"]["vaos_y"] = [2.0]
    conferencia = cr.conferir_arquitetura_estrutura(_arquitetura(spec), estrutura)
    assert conferencia["ok"] is False
    assert conferencia["erros"][0]["code"] == "programa_maior_que_a_malha_estrutural"


def test_pe_direito_divergente_reprova(spec):
    estrutura = copy.deepcopy(spec["turnkey"]["estrutura"])
    estrutura["geometria"]["pe_direito"] += 0.30
    conferencia = cr.conferir_arquitetura_estrutura(_arquitetura(spec), estrutura)
    assert conferencia["ok"] is False
    assert any(e["code"] == "pe_direito_diverge" for e in conferencia["erros"])


def test_comodo_fora_da_malha_reprova(spec):
    """A area pode fechar com um quarto pendurado para fora da estrutura; so a
    conferencia GEOMETRICA pega isso."""
    layout = copy.deepcopy(spec["turnkey"]["eletrico"]["circuits"]["layout"])
    layout["rooms"][0]["x_m"] = 9.0          # empurra a sala para fora da malha
    conferencia = cr.conferir_arquitetura_estrutura(
        _arquitetura(spec), spec["turnkey"]["estrutura"], layout)
    assert conferencia["ok"] is False
    erro = next(e for e in conferencia["erros"]
                if e["code"] == "comodo_fora_da_malha_estrutural")
    assert erro["comodos"][0]["ambiente"] == "Sala"


def test_a_costura_reprovada_bloqueia_a_disciplina(spec):
    estrutura = copy.deepcopy(spec["turnkey"]["estrutura"])
    estrutura["geometria"]["pe_direito"] += 0.30
    registro, resultado = cr._registro_estrutura(estrutura, _arquitetura(spec))
    assert registro["status"] == "blocked"
    assert registro["native_atende"] is False
    assert "conferencia_arquitetura" in registro["reprovados"]
    # o calculo ainda rodou: a costura nao apaga os numeros, ela os contesta
    assert resultado is not None and resultado["gates"]["pilares"]["OK"]


# ------------------------------------------------------- 3. modelo neutro/IFC

def test_o_modelo_neutro_reproduz_o_calculo(estrutura):
    membros = be.membros_bim(estrutura)
    conferencia = be.confere_modelo(estrutura, membros)
    assert conferencia["ok"], conferencia
    assert conferencia["por_tipo"]["Footing"] == 12
    assert be.confere_empilhamento(membros)["OK"]


def test_o_baldrame_entra_no_modelo_uma_vez_por_tramo(estrutura):
    """Contagem: linhas de contorno x tramos. Um baldrame que sumisse do modelo
    abriria normalmente no visualizador sem denunciar nada."""
    membros = be.membros_bim(estrutura)
    baldrames = [m for m in membros if m["marca"].startswith(("BX-", "BY-"))]
    assert len(baldrames) == be.n_baldrames(estrutura)
    assert len(baldrames) == 10            # 2 linhas X x 3 + 2 linhas Y x 2
    assert {m["pavimento"] for m in baldrames} == {"Fundacao"}


def test_baldrame_que_invade_a_sapata_e_recusado(estrutura):
    """Geometria impossivel nao e' acomodada com folga inventada."""
    invadindo = copy.deepcopy(estrutura)
    invadindo["baldrame"]["secao"]["h"] = 1.5      # cota de apoio e' 1,0 m
    with pytest.raises(be.GeometriaIncoerente) as erro:
        be.membros_bim(invadindo)
    assert "cota de apoio" in str(erro.value)


def test_o_edificio_continua_sem_baldrame_no_modelo():
    """O emissor e' um so, mas peca que o calculo nao produziu nao aparece: o
    multipavimento nao dimensiona baldrame e nao ganha nenhum."""
    assert be.n_baldrames({"pavimento": {}, "fundacao": None}) == 0
    assert be.membros_baldrame({"baldrame": None}, [0.0], [0.0], "Concreto") == []


def test_o_ifc_da_estrutura_e_publicado(execucao):
    manifesto, destino = execucao
    entregavel = manifesto["deliverables"]["ifc"]
    assert entregavel["status"] == "generated", entregavel.get("detail")
    assert "bim/estrutura-residencial.ifc" in entregavel["artifacts"]
    assert (destino / "bim" / "estrutura-residencial.ifc").is_file()
    parte = entregavel["partes"]["estrutura"]
    assert parte["conferencia_modelo"]["ok"]
    assert parte["quantitativo"]["vol_concreto_m3"] > 0


# ---------- IFC medido de volta (ifcopenshell) ----------

ifcopenshell = pytest.importorskip("ifcopenshell")


@pytest.fixture(scope="module")
def modelo_ifc(estrutura, tmp_path_factory):
    destino = tmp_path_factory.mktemp("bim-g13") / "casa.ifc"
    be.emitir_bim(estrutura, str(destino), nome="CasaResidencial")
    return ifcopenshell.open(str(destino))


def _caixa_mundial(entidade):
    import ifcopenshell.geom as geom
    import ifcopenshell.util.shape as shape

    ajustes = geom.settings()
    ajustes.set("use-world-coords", True)
    forma = geom.create_shape(ajustes, entidade)
    return shape.get_bbox(shape.get_vertices(forma.geometry))


def _por_nome(modelo, nome):
    return next(e for e in modelo.by_type("IfcProduct") if e.Name == nome)


def test_o_ifc_tem_os_elementos_estruturais_e_nao_so_arquitetura(modelo_ifc):
    """O criterio de aceite do G13, medido no arquivo emitido."""
    assert modelo_ifc.schema == "IFC4"
    for tipo, minimo in (("IfcColumn", 12), ("IfcBeam", 27), ("IfcSlab", 6),
                         ("IfcFooting", 12)):
        assert len(modelo_ifc.by_type(tipo)) == minimo, tipo


def test_nenhum_elemento_estrutural_fica_fora_da_arvore(modelo_ifc):
    contidos = set()
    for relacao in modelo_ifc.by_type("IfcRelContainedInSpatialStructure"):
        contidos.update(e.id() for e in relacao.RelatedElements)
    produtos = [e for e in modelo_ifc.by_type("IfcProduct")
                if e.is_a() in ("IfcColumn", "IfcBeam", "IfcSlab", "IfcFooting")]
    assert produtos
    assert [e.Name for e in produtos if e.id() not in contidos] == []


def test_o_baldrame_esta_em_pe_e_enterrado(modelo_ifc, estrutura):
    """MEDE o retangulo e as cotas: largura no plano horizontal, altura em Z, e
    o TOPO na cota zero. Um baldrame deitado, ou boiando acima do terreno, passa
    despercebido em qualquer teste que so leia a string do perfil."""
    secao = estrutura["baldrame"]["secao"]
    for marca, eixo_do_vao in (("BX-0-1", 0), ("BY-0-1", 1)):
        minimo, maximo = _caixa_mundial(_por_nome(modelo_ifc, marca))
        dims = maximo - minimo
        transversal = 1 - eixo_do_vao
        assert dims[transversal] == pytest.approx(secao["b"], abs=1e-4), marca
        assert dims[2] == pytest.approx(secao["h"], abs=1e-4), marca
        assert maximo[2] == pytest.approx(0.0, abs=1e-4), marca
        assert minimo[2] == pytest.approx(-secao["h"], abs=1e-4), marca


def test_o_baldrame_nao_ocupa_o_volume_da_sapata(modelo_ifc, estrutura):
    cota = estrutura["fundacao"]["cota_apoio_m"]
    _minimo, maximo = _caixa_mundial(_por_nome(modelo_ifc, "SAP-P11"))
    assert maximo[2] == pytest.approx(-cota, abs=1e-4)
    minimo_b, _maximo_b = _caixa_mundial(_por_nome(modelo_ifc, "BX-0-1"))
    assert minimo_b[2] > maximo[2] + 1e-6


def test_o_pilar_da_casa_nao_esta_girado_90_graus(modelo_ifc, estrutura):
    """'h' e' a dimensao na direcao X - a convencao com que a esbeltez foi
    calculada. Trocado com 'b', o pilar entra no BIM com o eixo forte fora da
    direcao dimensionada; ja aconteceu duas vezes neste repositorio."""
    pe = list(estrutura["pilares"]["P11"]["lances"])[-1]["pe_direito"]
    nivel = be.niveis(estrutura, pe)[0]["nome"]
    lance = list(estrutura["pilares"]["P11"]["lances"])[-1]
    minimo, maximo = _caixa_mundial(_por_nome(modelo_ifc, "P11-%s" % nivel))
    dims = maximo - minimo
    assert dims[0] == pytest.approx(lance["h"], abs=1e-4)
    assert dims[1] == pytest.approx(lance["b"], abs=1e-4)
