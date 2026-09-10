"""G78: a casa promete 3 folhas de arquitetura e nao emitia nenhuma.

Medido: `pacote_legal._PRANCHAS["arquitetura"]` promete PE-AR-01/02/03; o
censo achava 32 folhas e nenhuma de arquitetura; `desenho_casa_residencial`
pulava a planta baixa com `posicoes_dos_ambientes_nao_declaradas` - motivo
falso para o spec persistido, que declara os 7 comodos com x/y/width/depth
sob `turnkey.eletrico.circuits.layout.rooms`.

Entregue:
  1. o layout mora canonicamente em `turnkey.arquitetura.layout` (a
     arquitetura declara, a eletrica le); o espelho eletrico que diverge
     recusa com o endereco do canonico (molde do G74);
  2. `planta_baixa_svg` de verdade (PE-AR-02): comodos posicionados, nomes,
     areas, cotas gerais - sem inventar parede, porta ou janela;
  3. PE-AR-01/PE-AR-03 triadas: `not_available` com o dado que falta nomeado;
  4. guarda de cross-check area do programa x area do layout, com tolerancia
     declarada e vermelho por injecao;
  5. a folha nova registrada em `FOLHAS` de `test_folhas_g77` (o portao do
     censo fica vermelho ate isso ser feito - e' de proposito).

Cada teste segue as 5 convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em diretorio temporario (nunca mutando o repo),
substring -> parse -> renderizar, saturacao silenciosa (drawing-vs-data) e
sem assercao tautologica (fonte independente: os numeros do spec).
"""
import copy
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

import pytest

GALPAO = pathlib.Path(__file__).resolve().parents[1]
if str(GALPAO) not in sys.path:
    sys.path.insert(0, str(GALPAO))
REPO = GALPAO.parents[1]

import casa_residencial as cr
import desenho_casa_residencial as dcr
import desenho_svg_base as sb
import layout_ambientes as la


def _spec():
    return json.loads((REPO / "projects" / "casa-residencial" /
                       "project-spec.json").read_text(encoding="utf-8"))


def _programa_e_layout():
    """Programa calculado + layout canonico do spec persistido (reais)."""
    import arquitetura_residencial as ar

    spec = _spec()
    programa = ar.rodar(spec["turnkey"]["arquitetura"])
    layout = copy.deepcopy(spec["turnkey"]["arquitetura"]["layout"])
    return programa, layout


# ---------------------------------------------------------------------------
# 1. a tolerancia e' UMA so, nas tres disciplinas que fazem a mesma pergunta
# ---------------------------------------------------------------------------

def test_tolerancia_do_crosscheck_e_unica_e_declarada():
    """`arquitetura_residencial` (area x LxC), `bim_casa_residencial` (rotulo
    x geometria) e `layout_ambientes` (programa x layout) conferem a mesma
    coisa: duas tolerancias que envelhecem e passam a discordar em silencio
    e' o anti-padrao que este goal fecha."""
    import bim_casa_residencial as bim

    assert la.TOL_AREA_REL == pytest.approx(1e-3)
    assert bim.TOL_REL == pytest.approx(la.TOL_AREA_REL)


# ---------------------------------------------------------------------------
# 2. cross-check programa x layout: baseline nos dois sentidos
# ---------------------------------------------------------------------------

def test_crosscheck_passa_no_caso_bom_e_acusa_a_injecao():
    programa, layout = _programa_e_layout()
    bom = la.conferir_areas_programa_layout(programa["ambientes"],
                                            layout["rooms"])
    assert bom["ok"] is True, bom["erros"]
    # o detalhamento entregue: um registro por ambiente, com os dois numeros
    assert len(bom["por_ambiente"]) == 7
    for registro in bom["por_ambiente"]:
        assert registro["area_programa_m2"] == pytest.approx(
            registro["area_layout_m2"], rel=la.TOL_AREA_REL)

    # injecao: um comodo 20 cm mais largo - a suite tem de acusar, nomeando
    # o ambiente e os dois numeros (vermelho, sem mutar o repo: tudo em copia)
    ruim = copy.deepcopy(layout)
    ruim["rooms"][0]["width_m"] += 0.20
    acusacao = la.conferir_areas_programa_layout(programa["ambientes"],
                                                 ruim["rooms"])
    assert acusacao["ok"] is False
    erro = acusacao["erros"][0]
    assert erro["code"] == "area_do_layout_diverge_do_programa"
    assert erro["ambiente"] == "Sala"
    assert erro["area_programa_m2"] == pytest.approx(20.0)
    assert erro["area_layout_m2"] == pytest.approx(20.8)


def test_crosscheck_acusa_ambiente_sem_retangulo():
    programa, layout = _programa_e_layout()
    sem_um = copy.deepcopy(layout)
    sem_um["rooms"] = [c for c in sem_um["rooms"] if c["id"] != "Cozinha"]
    conf = la.conferir_areas_programa_layout(programa["ambientes"],
                                             sem_um["rooms"])
    assert conf["ok"] is False
    assert {e["code"] for e in conf["erros"]} == {"ambiente_ausente_no_layout"}


# ---------------------------------------------------------------------------
# 3. o canonico e' da arquitetura; o espelho que diverge recusa (molde G74)
# ---------------------------------------------------------------------------

def _resultado_eletrico_com_layout(rooms):
    return {"circuits": {"layout_validation": {
        "declared": True, "ok": True, "errors": [],
        "layout": {"units": "m", "rooms": rooms}}}}


def test_espelho_igual_ao_canonico_passa_com_proveniencia_canonica():
    spec = _spec()
    turnkey = spec["turnkey"]
    conf = cr.conferencia_layout_canonico(
        turnkey, {"ambientes": []},
        _resultado_eletrico_com_layout(
            copy.deepcopy(turnkey["eletrico"]["circuits"]["layout"]["rooms"])))
    assert conf["canonico_declarado"] is True
    assert conf["espelho_declarado"] is True
    assert conf["ok"] is True, conf["erros"]
    assert conf["proveniencia"] == "arquitetura.layout"


def test_espelho_divergente_recusa_com_o_endereco_do_canonico():
    spec = _spec()
    turnkey = copy.deepcopy(spec["turnkey"])
    espelho = copy.deepcopy(turnkey["eletrico"]["circuits"]["layout"]["rooms"])
    espelho[1]["width_m"] += 0.50  # a eletrica desenha outra cozinha
    conf = cr.conferencia_layout_canonico(
        turnkey, {"ambientes": []}, _resultado_eletrico_com_layout(espelho))
    assert conf["ok"] is False
    erro = next(e for e in conf["erros"]
                if e["code"] == "layout_eletrico_diverge_do_canonico")
    assert erro["room"] == "Cozinha"
    # a chave antiga recusa COM ENDERECO (molde do G74): vale o canonico
    assert cr.LAYOUT_CANONICO in erro["detail"]
    assert erro["canonico"] == cr.LAYOUT_CANONICO


def test_sem_canonico_o_fallback_eletrico_vale_com_proveniencia_dita():
    spec = _spec()
    turnkey = copy.deepcopy(spec["turnkey"])
    del turnkey["arquitetura"]["layout"]
    conf = cr.conferencia_layout_canonico(
        turnkey, {"ambientes": []},
        _resultado_eletrico_com_layout(
            copy.deepcopy(turnkey["eletrico"]["circuits"]["layout"]["rooms"])))
    assert conf["canonico_declarado"] is False
    assert conf["ok"] is True
    assert conf["proveniencia"] == "eletrico.circuits.layout"


def test_divergencia_do_espelho_bloqueia_o_eletrico_no_loop(tmp_path):
    """O caminho completo: espelho divergente bloqueia, com o codigo nomeado."""
    from builtin_adapters import register_builtin_adapters
    from project_loop import normalize_spec

    register_builtin_adapters()
    spec = _spec()
    # injecao que NAO quebra a validacao eletrica (sem sobreposicao, pontos
    # seguem dentro: Sala 5,0 -> 4,5 m, T-SALA-04 em x=4,15 continua dentro):
    # o espelho passa na eletrica e cai SO na conferencia canonica
    spec["turnkey"]["eletrico"]["circuits"]["layout"]["rooms"][0][
        "width_m"] -= 0.50
    resultado, registros = cr.run_casa_residencial(normalize_spec(spec), None)
    assert registros["eletrico"]["status"] == "blocked"
    assert "layout_eletrico_diverge_do_canonico" in [
        e["code"] for e in registros["eletrico"]["errors"]]
    assert resultado["status"] == "blocked"
    _ = tmp_path  # o vermelho mora na copia em memoria, nunca no repo


# ---------------------------------------------------------------------------
# 4. a planta baixa: parse + guarda + drawing-vs-data (fonte independente)
# ---------------------------------------------------------------------------

def _svg_bom():
    programa, layout = _programa_e_layout()
    return programa, layout, dcr.planta_baixa_svg(programa, layout)


def test_planta_passa_na_guarda_generica():
    _, _, svg = _svg_bom()
    ET.fromstring(svg)
    conf = sb.confere_folha_svg(svg)
    assert conf["ok"], conf["motivo"]


def test_planta_desenha_um_retangulo_por_comodo_com_os_numeros_do_spec():
    """Drawing-vs-data: a contagem desenhada == a do programa, e as dimensoes
    escritas sao as do spec (fonte independente - lidas do JSON aqui, nao do
    SVG). Nenhum par sobreposto: a primitiva ja garante, o teste reconfere."""
    programa, layout, svg = _svg_bom()
    raiz = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    desenhados = [el for el in list(raiz.iter(ns + "rect"))
                  + list(raiz.iter("rect"))
                  if (el.get("fill") or "").lower() == dcr.COR_FUNDO_COMODO]
    assert len(desenhados) == 7 == len(programa["ambientes"])

    textos = [(el.text or "") for el in list(raiz.iter(ns + "text"))
              + list(raiz.iter("text"))]
    spec = _spec()
    for ambiente in spec["turnkey"]["arquitetura"]["ambientes"]:
        assert ambiente["nome"] in textos
    for comodo in layout["rooms"]:
        assert ("%.2f x %.2f m" % (comodo["width_m"], comodo["depth_m"])
                ) in textos
    # cotas gerais do envelope, calculadas AQUI do spec (nao lidas da folha)
    xs = [c["x_m"] + c["width_m"] for c in layout["rooms"]]
    ys = [c["y_m"] + c["depth_m"] for c in layout["rooms"]]
    assert ("%.2f m" % max(xs)) in textos
    assert ("%.2f m" % max(ys)) in textos
    # o que NAO foi declarado e' dito na folha, nao desenhado
    assert any("fora do escopo" in t for t in textos)


def test_planta_nao_desenha_casa_divergente(tmp_path):
    """Layout que diverge do programa: a folha nao sai, e o motivo viaja em
    `skipped` com o codigo da guarda (desenhar seria publicar uma casa e
    calcular outra). Tudo em diretorio temporario."""
    programa, layout = _programa_e_layout()
    turnkey = {"arquitetura": {"layout": layout}}
    turnkey["arquitetura"]["layout"] = copy.deepcopy(layout)
    turnkey["arquitetura"]["layout"]["rooms"][2]["depth_m"] += 0.30
    resultado = {"arquitetura": programa,
                 "eletrico": {"circuits": {"layout_validation": {
                     "declared": False, "ok": False, "errors": [],
                     "layout": None}}}}
    out = dcr.gerar_desenhos_casa(resultado, tmp_path / "d", turnkey)
    assert "planta-baixa.svg" not in out["files"]
    assert out["skipped"]["planta-baixa.svg"] in (
        "layout_area_mismatch", "layout_perimeter_mismatch")
    assert not (tmp_path / "d" / "planta-baixa.svg").exists()


def test_sem_layout_a_planta_traz_o_motivo_antigo(tmp_path):
    """Baseline no outro sentido: sem posicao declarada nao ha planta honesta,
    e o motivo continua sendo o de antes (nada inventado)."""
    programa, _ = _programa_e_layout()
    resultado = {"arquitetura": programa, "eletrico": {}, "hidraulica": {}}
    out = dcr.gerar_desenhos_casa(resultado, tmp_path / "d")
    assert out["skipped"]["planta-baixa.svg"] == \
        "posicoes_dos_ambientes_nao_declaradas"


# ---------------------------------------------------------------------------
# 5. triagem PE-AR-01/PE-AR-03: not_available com o dado nomeado, sem arbitrar
# ---------------------------------------------------------------------------

def test_triagem_nomeia_o_dado_que_falta():
    spec = _spec()
    motivos = dcr.motivos_arquitetura_faltante(spec["turnkey"], spec["site"])
    assert set(motivos) == {"implantacao.svg", "cortes-fachadas.svg"}
    for motivo in motivos.values():
        assert motivo.startswith("not_available")
    assert "site.lote" in motivos["implantacao.svg"]
    assert "soleira" in motivos["cortes-fachadas.svg"]


def test_triagem_com_dado_declarado_mantem_not_available_sem_fingir_falta():
    """Outro sentido: com lote e niveis declarados, a ausencia e' so de
    emissor - o motivo nao pode continuar acusando dado que existe."""
    turnkey = copy.deepcopy(_spec()["turnkey"])
    site = {"lote": {"dimensoes_m": [12.0, 25.0],
                     "recuos_m": {"frente": 3.0},
                     "orientacao": "norte na testada"}}
    turnkey["niveis"] = {"soleira_m": 0.20}
    motivos = dcr.motivos_arquitetura_faltante(turnkey, site)
    assert all(m.startswith("not_available") for m in motivos.values())
    assert "nao declarado" not in motivos["implantacao.svg"]
    assert "nao declarados" not in motivos["cortes-fachadas.svg"]


# ---------------------------------------------------------------------------
# 6. o laco indice<->disco da casa fecha para a arquitetura
# ---------------------------------------------------------------------------

def test_laco_indice_disco_da_arquitetura(tmp_path):
    """Nenhuma PE-AR prometida sem arquivo ou sem motivo escrito."""
    import pacote_legal as pl
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    destino = tmp_path / "run"
    manifesto = run_project(_spec(), destino, {"generate_2d": True})
    desenhos = manifesto["deliverables"]["drawings"]
    indice = pl.indice_de_pranchas(["arquitetura"])
    assert [p["codigo"] for p in indice] == ["PE-AR-01", "PE-AR-02", "PE-AR-03"]
    assert "drawings/planta-baixa.svg" in desenhos["artifacts"]
    assert (destino / "drawings" / "planta-baixa.svg").is_file()
    assert desenhos["skipped"]["implantacao.svg"].startswith("not_available")
    assert desenhos["skipped"]["cortes-fachadas.svg"].startswith(
        "not_available")
    cobertas = {a.split("/", 1)[1] for a in desenhos["artifacts"]}
    cobertas.update(desenhos["skipped"])
    for folha in indice:
        assert cr._PRANCHA_ARQUIVO_CASA[folha["codigo"]] in cobertas
