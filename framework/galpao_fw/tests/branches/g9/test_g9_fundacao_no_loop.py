"""G9 no Project Loop e no BIM: a fundacao sai de not_available e vira peca.

Capacidade nao declarada e' capacidade que nao existe - mas capacidade declarada
que nao produz nada e' pior, porque o manifesto passa a mentir. Estes testes
prendem os dois lados: o escopo do adaptador so diz `implemented` quando a
sondagem esta declarada, e quando diz, a peca aparece no IFC com a cota certa.
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
import edificio_multipavimento as em
from builtin_adapters import register_builtin_adapters
from project_loop import run_project

PROJETOS = GALPAO.parents[1] / "projects"
SPEC = PROJETOS / "edificio-multipavimento" / "project-spec.json"


@pytest.fixture(scope="module", autouse=True)
def _adaptadores():
    register_builtin_adapters()


def _spec():
    return json.loads(SPEC.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rodada(tmp_path_factory):
    destino = tmp_path_factory.mktemp("g9") / "run"
    manifesto = run_project(_spec(), destino,
                            {"generate_2d": False, "generate_ifc": True,
                             "generate_3d": False})
    return manifesto, destino


def _resultado_adaptador(destino):
    return json.loads((Path(destino) / "reports" / "adapter-result.json")
                      .read_text(encoding="utf-8"))


# ------------------------------- escopo --------------------------------------

def test_a_fundacao_saiu_de_not_available(rodada):
    """O aceite do G9, medido onde ele importa: o escopo publicado da rodada."""
    _manifesto, destino = rodada
    escopo = _resultado_adaptador(destino)["scope"]
    assert escopo["fundacao"] == "implemented"


def test_sem_sondagem_o_escopo_volta_a_dizer_not_available(tmp_path):
    """Sem o dado, a capacidade some do escopo - e nao vira uma sapata assentada
    numa tensao de solo arbitrada."""
    spec = _spec()
    spec["turnkey"]["estrutura"].pop("fundacao")
    destino = tmp_path / "run"
    run_project(spec, destino, {"generate_2d": False, "generate_ifc": False})
    resultado = _resultado_adaptador(destino)
    assert resultado["scope"]["fundacao"] == "not_available"
    registro = json.loads(
        (destino / "reports" / "disciplinas.json").read_text(encoding="utf-8"))
    codigos = {aviso["code"]
               for aviso in registro["estrutura"]["warnings"]}
    assert "fundacao_nao_declarada" in codigos


def test_o_que_a_fundacao_nao_cobre_continua_publicado(rodada):
    """G17 levantou o momento na base; o resto da lista continua publicado.

    Este teste guardava `momento_base_pilar` como ausente, que era a verdade
    ate o G17 extrair os esforcos de extremidade do Frame2D por prumada. A
    assercao passa a cobrir a REGRA (com momento, a excentricidade alcanca a
    sapata de divisa e a viga de equilibrio) em vez do valor congelado.
    """
    _manifesto, destino = rodada
    escopo = _resultado_adaptador(destino)["scope"]
    assert escopo["momento_base_pilar"] == "implemented"
    assert escopo["sapata_divisa"] == "implemented"
    assert escopo["viga_equilibrio"] == "implemented"
    # Estes seguem abertos: sao o escopo do G18, nao do G17.
    assert escopo["viga_baldrame"] == "not_available"
    assert escopo["recalque_diferencial"] == "not_available"


def test_o_registro_da_disciplina_traz_a_fundacao_por_pilar(rodada):
    _manifesto, destino = rodada
    registro = json.loads(
        (destino / "reports" / "disciplinas.json").read_text(encoding="utf-8"))
    fundacao = registro["estrutura"]["foundation"]
    assert fundacao["tipo"] == "sapata"
    assert fundacao["sigma_solo_adm_kNm2"] > 0
    assert "SPT" in fundacao["proveniencia_sigma"]
    assert len(fundacao["por_pilar"]) == 12
    assert all(item["OK"] for item in fundacao["por_pilar"].values())


def test_entrada_de_fundacao_rejeitada_bloqueia_a_disciplina(tmp_path):
    spec = _spec()
    spec["turnkey"]["estrutura"]["fundacao"]["tipo"] = "estaca"
    spec["turnkey"]["estrutura"]["fundacao"]["perfil_spt"] = [
        {"tipo": "argila", "N": 3, "dz": 8.0}]
    destino = tmp_path / "run"
    manifesto = run_project(spec, destino,
                            {"generate_2d": False, "generate_ifc": False})
    assert manifesto["status"] == "blocked"
    registro = json.loads(
        (destino / "reports" / "disciplinas.json").read_text(encoding="utf-8"))
    codigos = {erro["code"] for erro in registro["estrutura"]["errors"]}
    assert "foundation_input_rejected" in codigos


def test_fundacao_malformada_e_recusada_na_entrada(tmp_path):
    spec = _spec()
    spec["turnkey"]["estrutura"]["fundacao"] = "argila"
    destino = tmp_path / "run"
    manifesto = run_project(spec, destino,
                            {"generate_2d": False, "generate_ifc": False})
    assert manifesto["status"] == "blocked"


# --------------------------------- BIM ---------------------------------------

@pytest.fixture(scope="module")
def estrutura():
    payload = _spec()["turnkey"]["estrutura"]
    return em.rodar({chave: copy.deepcopy(payload[chave]) for chave in
                     ("geometria", "pavimentos", "laje", "viga", "materiais",
                      "vento", "fundacao") if chave in payload})


def test_uma_sapata_por_pilar_no_modelo(estrutura):
    membros = be.membros_bim(estrutura)
    sapatas = [m for m in membros if m["tipo"] == "Footing"]
    assert len(sapatas) == len(estrutura["fundacao"]["por_pilar"])
    conferencia = be.confere_modelo(estrutura, membros)
    assert conferencia["ok"], conferencia


def test_a_fundacao_nao_interpenetra_o_resto(estrutura):
    resultado = be.confere_empilhamento(be.membros_bim(estrutura))
    assert resultado["OK"], resultado["conflitos"][:5]


def test_sem_fundacao_calculada_nenhuma_peca_de_fundacao_e_emitida(estrutura):
    """Peca que ninguem calculou nao aparece no modelo."""
    sem = copy.deepcopy(estrutura)
    sem["fundacao"] = None
    membros = be.membros_bim(sem)
    assert not [m for m in membros if m["tipo"] in ("Footing", "Pile")]
    assert be.confere_modelo(sem, membros)["ok"]


ifcopenshell = pytest.importorskip("ifcopenshell")


def _caixa_mundial(entidade):
    import ifcopenshell.geom as geom
    import ifcopenshell.util.shape as shape

    ajustes = geom.settings()
    ajustes.set("use-world-coords", True)
    forma = geom.create_shape(ajustes, entidade)
    return shape.get_bbox(shape.get_vertices(forma.geometry))


@pytest.fixture(scope="module")
def modelo_ifc(estrutura, tmp_path_factory):
    destino = tmp_path_factory.mktemp("g9bim") / "edificio.ifc"
    be.emitir_bim(estrutura, str(destino))
    return ifcopenshell.open(str(destino))


def test_a_sapata_sai_como_ifcfooting_no_andar_de_fundacao(modelo_ifc, estrutura):
    sapatas = modelo_ifc.by_type("IfcFooting")
    assert len(sapatas) == len(estrutura["fundacao"]["por_pilar"])
    andares = {a.Name: a for a in modelo_ifc.by_type("IfcBuildingStorey")}
    assert "Fundacao" in andares
    cota = estrutura["fundacao"]["cota_apoio_m"]
    assert andares["Fundacao"].Elevation == pytest.approx(-cota * 1000.0)


def test_a_sapata_esta_enterrada_com_o_topo_na_cota_de_apoio(modelo_ifc,
                                                             estrutura):
    """Medido no arquivo emitido: sapata na cota zero seria fundacao a ceu aberto."""
    cota = estrutura["fundacao"]["cota_apoio_m"]
    registro = estrutura["fundacao"]["por_pilar"]["P22"]
    geometria = registro["geometria"]
    entidade = next(e for e in modelo_ifc.by_type("IfcFooting")
                    if e.Name == "SAP-P22")
    minimo, maximo = _caixa_mundial(entidade)
    assert float(maximo[2]) == pytest.approx(-cota, abs=1e-4)
    assert float(minimo[2]) == pytest.approx(-cota - geometria["h_m"], abs=1e-4)
    dims = maximo - minimo
    assert float(dims[0]) == pytest.approx(geometria["B_m"], abs=1e-4)
    assert float(dims[1]) == pytest.approx(geometria["L_m"], abs=1e-4)


def test_a_sapata_fica_sob_o_pilar_que_ela_recebe(modelo_ifc, estrutura):
    """Rotulo x geometria: a sapata SAP-Pij tem de estar no eixo do pilar Pij."""
    for nome, registro in estrutura["fundacao"]["por_pilar"].items():
        sapata = next(e for e in modelo_ifc.by_type("IfcFooting")
                      if e.Name == "SAP-%s" % nome)
        pilar = next(e for e in modelo_ifc.by_type("IfcColumn")
                     if e.Name.startswith("%s-" % nome))
        min_s, max_s = _caixa_mundial(sapata)
        min_p, max_p = _caixa_mundial(pilar)
        centro_s = ((min_s[0] + max_s[0]) / 2, (min_s[1] + max_s[1]) / 2)
        centro_p = ((min_p[0] + max_p[0]) / 2, (min_p[1] + max_p[1]) / 2)
        assert centro_s[0] == pytest.approx(centro_p[0], abs=1e-3), nome
        assert centro_s[1] == pytest.approx(centro_p[1], abs=1e-3), nome
        del registro


def test_a_armadura_da_sapata_viaja_no_pset(modelo_ifc):
    psets = [p for p in modelo_ifc.by_type("IfcPropertySet")
             if p.Name == "Pset_Armadura"]
    nomes = set()
    for pset in psets:
        nomes.update(prop.Name for prop in pset.HasProperties)
    assert "N_dimensionamento_kN" in nomes
    assert "As_L_cm2" in nomes or "As_B_cm2" in nomes


def test_a_estaca_sai_como_ifcpile_cilindrica(tmp_path):
    """Prisma DxD daria 27 % a mais de concreto; o perfil tem de ser circular."""
    payload = _spec()["turnkey"]["estrutura"]
    entrada = {chave: copy.deepcopy(payload[chave]) for chave in
               ("geometria", "pavimentos", "laje", "viga", "materiais", "vento",
                "fundacao") if chave in payload}
    entrada["fundacao"]["perfil_spt"] = [
        {"tipo": "argila", "N": 2, "dz": 6.0},
        {"tipo": "argila_arenosa", "N": 5, "dz": 4.0},
        {"tipo": "areia", "N": 32, "dz": 5.0},
        {"tipo": "areia", "N": 45, "dz": 6.0}]
    resultado = em.rodar(entrada)
    assert resultado["fundacao"]["tipo"] == "estaca"
    destino = tmp_path / "estacas.ifc"
    be.emitir_bim(resultado, str(destino))
    modelo = ifcopenshell.open(str(destino))
    estacas = modelo.by_type("IfcPile")
    assert estacas
    D = resultado["fundacao"]["por_pilar"]["P11"]["geometria"]["D_m"]
    L = resultado["fundacao"]["por_pilar"]["P11"]["geometria"]["L_m"]
    entidade = next(e for e in estacas if e.Name == "EST-P11-1")
    minimo, maximo = _caixa_mundial(entidade)
    dims = maximo - minimo
    assert float(dims[0]) == pytest.approx(D, abs=1e-3)
    assert float(dims[1]) == pytest.approx(D, abs=1e-3)
    assert float(dims[2]) == pytest.approx(L, abs=1e-3)
    # volume de UM cilindro, nao de um prisma: pi*D^2/4*L
    import geometria_membros as gm
    membro = next(m for m in be.membros_bim(resultado)
                  if m.get("marca") == "EST-P11-1")
    import math
    assert gm.volume(membro) == pytest.approx(
        math.pi * D ** 2 / 4.0 * L, rel=1e-6)
