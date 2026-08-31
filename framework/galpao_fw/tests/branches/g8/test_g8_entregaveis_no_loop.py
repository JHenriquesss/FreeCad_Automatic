"""G8 no Project Loop: as duas tipologias novas DECLARAM e ENTREGAM o BIM.

Capacidade declarada que nao produz artefato e' pior que capacidade ausente - o
manifesto passa a mentir. Estes testes rodam os dois projetos persistidos de
ponta a ponta pelo Loop e conferem o par: o adaptador declara `ifc`/`model_3d`, e
a rodada devolve status honesto para cada um (gerado com artefato registrado, ou
indisponivel com o motivo escrito).
"""

import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
GALPAO = HERE.parents[3]
sys.path.insert(0, str(GALPAO))

from builtin_adapters import register_builtin_adapters
from project_loop import describe_adapters, run_project, verify_project_run

PROJETOS = GALPAO.parents[1] / "projects"


@pytest.fixture(scope="module", autouse=True)
def _adaptadores():
    register_builtin_adapters()


def _spec(slug):
    return json.loads((PROJETOS / slug / "project-spec.json").read_text(
        encoding="utf-8"))


@pytest.fixture(scope="module")
def rodada_edificio(tmp_path_factory):
    destino = tmp_path_factory.mktemp("ed") / "run"
    manifesto = run_project(_spec("edificio-multipavimento"), destino,
                            {"generate_2d": False, "generate_ifc": True,
                             "generate_3d": False})
    return manifesto, destino


@pytest.fixture(scope="module")
def rodada_casa(tmp_path_factory):
    destino = tmp_path_factory.mktemp("casa") / "run"
    manifesto = run_project(_spec("casa-residencial"), destino,
                            {"generate_2d": False, "generate_ifc": True,
                             "generate_3d": False})
    return manifesto, destino


# ----------------------------- capacidade declarada -------------------------

@pytest.mark.parametrize("adaptador", ["edificio-multipavimento", "casa-residencial"])
def test_a_tipologia_declara_bim_e_3d(adaptador):
    capacidades = {item["name"]: item for item in describe_adapters()}
    entregaveis = capacidades[adaptador]["deliverables"]
    assert "ifc" in entregaveis and "model_3d" in entregaveis


def test_o_galpao_continua_declarando_o_que_declarava():
    """A tipologia nova nao pode encolher a que ja existia."""
    capacidades = {item["name"]: item for item in describe_adapters()}
    galpao = capacidades["galpao"]["deliverables"]
    assert {"ifc", "model_3d", "drawings"} <= set(galpao)


# ------------------------------- edificio -----------------------------------

def test_o_edificio_entrega_o_ifc_com_o_artefato_registrado(rodada_edificio):
    manifesto, destino = rodada_edificio
    entregavel = manifesto["deliverables"]["ifc"]
    assert entregavel["status"] == "generated", entregavel
    assert entregavel["conferencia_modelo"]["ok"]
    assert entregavel["interferencias"] == []
    for relativo in entregavel["artifacts"]:
        assert (Path(destino) / relativo).is_file()
    assert verify_project_run(destino)["ok"] is True


def test_o_ifc_do_edificio_esta_no_manifesto_de_artefatos(rodada_edificio):
    manifesto, _ = rodada_edificio
    registrados = [a for a in manifesto["artifacts"] if a["kind"] == "ifc"]
    assert registrados and registrados[0]["path"].endswith(".ifc")
    assert registrados[0].get("discipline") == "estrutura"


def test_o_3d_nao_pedido_nao_e_dado_como_gerado(rodada_edificio):
    manifesto, _ = rodada_edificio
    assert manifesto["deliverables"]["model_3d"]["status"] == "not_requested"


def test_estrutura_ausente_bloqueia_o_bim_em_vez_de_gerar(tmp_path):
    """Sem estrutura declarada a rodada e' bloqueada, e o BIM vai junto: nunca
    um IFC vazio publicado como se fosse o modelo do predio."""
    spec = copy.deepcopy(_spec("edificio-multipavimento"))
    spec["turnkey"].pop("estrutura")
    manifesto = run_project(spec, tmp_path / "run",
                            {"generate_2d": False, "generate_ifc": True})
    assert manifesto["status"] == "blocked"
    assert manifesto["deliverables"]["ifc"]["status"] == "blocked"
    assert not [a for a in manifesto["artifacts"] if a["kind"] == "ifc"]


def test_o_hook_sem_estrutura_calculada_diz_o_motivo(tmp_path):
    """O hook em si (fora do curto-circuito do Loop) tem de recusar com motivo
    escrito, nao estourar nem devolver 'generated' de um modelo vazio."""
    import edificio_adapter as ea
    from project_loop import ProjectLoopOptions

    manifesto = {"deliverables": {}, "artifacts": []}
    ea._emitir_ifc(manifesto, tmp_path, {"turnkey_spec": {}},
                   ProjectLoopOptions(generate_ifc=True), {"estrutura": None})
    entregavel = manifesto["deliverables"]["ifc"]
    assert entregavel["status"] == "not_available"
    assert "estrutura" in entregavel["detail"]


# --------------------------------- casa -------------------------------------

# Desde o G13 a casa emite DOIS modelos - arquitetura e estrutura - e o
# entregavel `ifc`/`model_3d` agrega os dois em `partes`. O que estes testes
# guardam continua sendo a honestidade da parte de ARQUITETURA (proveniencia do
# layout, escopo do que nao foi declarado, recusa com motivo escrito); o que
# mudou e' onde ela mora no manifesto.

def _parte(entregavel, nome):
    return entregavel["partes"][nome]


def test_a_casa_entrega_o_ifc_e_diz_de_onde_veio_o_layout(rodada_casa):
    """A proveniencia viaja: um layout que a arquitetura nao declarou nao pode
    ser lido no manifesto como se ela o tivesse declarado."""
    manifesto, destino = rodada_casa
    entregavel = manifesto["deliverables"]["ifc"]
    assert entregavel["status"] == "generated", entregavel
    arquitetura = _parte(entregavel, "arquitetura")
    assert arquitetura["status"] == "generated", arquitetura
    assert arquitetura["layout_origem"] == "eletrico.circuits.layout"
    assert arquitetura["conferencia_areas"]["ok"]
    for relativo in entregavel["artifacts"]:
        assert (Path(destino) / relativo).is_file()
    assert verify_project_run(destino)["ok"] is True


def test_a_casa_entrega_tambem_o_ifc_da_estrutura(rodada_casa):
    """G13: o IFC da casa deixou de ser so arquitetura."""
    manifesto, destino = rodada_casa
    entregavel = manifesto["deliverables"]["ifc"]
    assert "bim/estrutura-residencial.ifc" in entregavel["artifacts"]
    estrutura = _parte(entregavel, "estrutura")
    assert estrutura["status"] == "generated", estrutura
    assert estrutura["conferencia_modelo"]["por_tipo"]["Footing"] > 0
    assert (Path(destino) / "bim" / "estrutura-residencial.ifc").is_file()


def test_o_escopo_publica_o_que_o_layout_nao_declarou(rodada_casa):
    manifesto, _ = rodada_casa
    escopo = _parte(manifesto["deliverables"]["ifc"], "arquitetura")["escopo"]
    assert escopo["ambientes"] == "implemented"
    assert escopo["paredes"] == "not_declared"
    assert escopo["esquadrias"] == "not_declared"


def test_sem_layout_nenhum_a_arquitetura_declara_indisponivel(tmp_path):
    """Sem posicao declarada nao ha modelo de ambientes honesto a emitir. A
    ESTRUTURA nao depende do layout (a malha e' declarada) e continua saindo -
    por isso a indisponibilidade agora e' da parte, nao do entregavel."""
    spec = copy.deepcopy(_spec("casa-residencial"))
    spec["turnkey"]["eletrico"]["circuits"].pop("layout")
    manifesto = run_project(spec, tmp_path / "run",
                            {"generate_2d": False, "generate_ifc": True})
    entregavel = manifesto["deliverables"]["ifc"]
    arquitetura = _parte(entregavel, "arquitetura")
    assert arquitetura["status"] == "not_available"
    assert "layout" in arquitetura["detail"]
    assert "bim/arquitetura-residencial.ifc" not in entregavel["artifacts"]


def test_layout_que_nao_bate_com_o_programa_bloqueia(tmp_path):
    """Modelo e calculo nao podem descrever casas diferentes."""
    spec = copy.deepcopy(_spec("casa-residencial"))
    spec["turnkey"]["arquitetura"]["layout"] = {
        "units": "m",
        "rooms": [{"id": a["nome"], "name": a["nome"], "x_m": 0.0,
                   "y_m": 3.0 * i, "width_m": 1.0, "depth_m": 1.0}
                  for i, a in enumerate(spec["turnkey"]["arquitetura"]["ambientes"])],
    }
    manifesto = run_project(spec, tmp_path / "run",
                            {"generate_2d": False, "generate_ifc": True})
    arquitetura = _parte(manifesto["deliverables"]["ifc"], "arquitetura")
    assert arquitetura["status"] == "blocked"
    assert arquitetura["layout_origem"] == "arquitetura.layout"
    assert "layout_area_mismatch" in {e["code"] for e in arquitetura["errors"]}
    # nenhum IFC de arquitetura foi publicado a partir do layout recusado
    assert "bim/arquitetura-residencial.ifc" not in manifesto[
        "deliverables"]["ifc"]["artifacts"]


def test_o_3d_da_arquitetura_sem_solido_declarado_e_indisponivel(tmp_path):
    """So ambientes declarados: nao ha peca construida de ARQUITETURA a montar.
    A estrutura tem solidos proprios e monta o seu modelo em separado."""
    manifesto = run_project(_spec("casa-residencial"), tmp_path / "run",
                            {"generate_2d": False, "generate_ifc": False,
                             "generate_3d": True})
    entregavel = manifesto["deliverables"]["model_3d"]
    arquitetura = _parte(entregavel, "arquitetura")
    assert arquitetura["status"] == "not_available"
    assert "solido" in arquitetura["detail"]
