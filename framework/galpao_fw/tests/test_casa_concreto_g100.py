"""G100 - as folhas de concreto da casa: o predio ja tem os tres emissores.

Medido (G98): a casa declara PE-CO-02/03/04 como "sem emissor nesta
rodada" com a estrutura calculada (G13), e o predio emite os equivalentes
(`armacao-vigas-pavimento-tipo.svg` via `desenho_pavimento`, e
`fundacao-locacao-formas.svg` via `desenho_fundacao_edificio` do G80).
Medido no G100: a casa de concreto produz os mesmos contratos (vigas
verificadas tramo a tramo desde o G34, laje de `dimensiona_laje`,
fundacao por pilar de `fundacao_edificio.dimensiona) - reuso por
primitivas, sem copia: tres wrappers em `desenho_casa_residencial` que
delegam as funcoes do predio, ligados em `gerar_desenhos_casa`. Os tres
ramos de motivo sumiram (nome morto apos o fato, como no G99).

Armadilha medida: na casa em alvenaria portante as vigas saem vazias
(por_linha == [], G61) e a fundacao sai por linha (sapata corrida, sem
por_pilar) - a ausencia sai nomeada, nunca folha vazia (o bug irmao do
G62 e da saturacao no piso da Fase 6B).

Convencoes do BACKLOG: baseline nos dois sentidos (o caso bom emite, o
injetado volta a faltar - test_03), injecao em tmp_path sem mutar a
arvore viva, parse XML + `confere_folha_svg` (nunca substring), fonte
independente (o spec persistido) e os dois aceites ("a folha esta certa"
e "a folha sai": drawing-vs-data + arquivo no disco e no manifesto).
"""
import copy
import json
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
REPO = os.path.dirname(os.path.dirname(GALPAO))

import desenho_svg_base as sb
import varredura_indice_disco as lente

TRES = ("armacao-vigas-pilares-casa.svg", "detalhes-concreto-casa.svg",
        "fundacao-locacao-formas-casa.svg")
MAPA_CO = {"PE-CO-02": "armacao-vigas-pilares-casa.svg",
           "PE-CO-03": "detalhes-concreto-casa.svg",
           "PE-CO-04": "fundacao-locacao-formas-casa.svg"}


def _estrutura_concreto():
    """Estrutura real da casa de concreto (spec persistido, fonte
    independente)."""
    import casa_residencial as cres
    from builtin_adapters import register_builtin_adapters
    from project_loop import normalize_spec

    register_builtin_adapters()
    spec = json.load(open(os.path.join(
        REPO, "projects", "casa-residencial", "project-spec.json"),
        encoding="utf-8"))
    resultado, _reg = cres.run_casa_residencial(normalize_spec(spec), None)
    return resultado["estrutura"]


def _estrutura_alvenaria():
    """Estrutura real da casa em alvenaria portante (vigas vazias,
    fundacao por linha)."""
    import estrutura_casa as ec
    from tests.test_alvenaria_bim_pranchas_g62 import BASE

    return ec.rodar(copy.deepcopy(BASE))


def _opt():
    return type("O", (), {"generate_2d": True, "generate_caderno": False})()


def _hook(tmp_path, estrutura, nome="run"):
    """Roda o hook da casa sobre uma casa minima com estrutura real."""
    import casa_residencial as casa

    destino = str(tmp_path / nome)
    manifesto = {"artifacts": [], "deliverables": {}}
    resultado = {"arquitetura": None, "estrutura": estrutura,
                 "hidraulica": None, "eletrico": None}
    casa._emitir_desenhos(manifesto, destino, {}, _opt(),
                          copy.deepcopy(resultado))
    return manifesto, destino


def _confere_folhas(no_disco, destino, gaps, exigir=()):
    """Parse XML + guarda da folha para cada arquivo exigido no disco."""
    for nome in exigir:
        caminho = os.path.join(destino, "drawings", nome)
        if not os.path.isfile(caminho):
            gaps.append("%s dito emitido sem arquivo no disco" % nome)
            continue
        try:
            svg = open(caminho, encoding="utf-8").read()
            ET.fromstring(svg)
        except ET.ParseError as exc:
            gaps.append("%s malformado: %s" % (nome, exc))
            continue
        conf = sb.confere_folha_svg(svg)
        if not conf["ok"]:
            gaps.append("%s reprova confere_folha_svg: %s"
                        % (nome, conf["motivo"]))
    return gaps


def test_01_hook_emite_as_tres_folhas_no_caminho_de_concreto(tmp_path):
    """Com estrutura de concreto, as tres saem no disco e no manifesto,
    passam no parse, na guarda e no drawing-vs-data, e o G91 fecha do
    lado do disco para os tres codigos."""
    import casa_residencial as casa
    import desenho_fundacao_edificio as dfe
    import desenho_pavimento as dp

    estrutura = _estrutura_concreto()
    manifesto, destino = _hook(tmp_path, estrutura)
    desenhos = manifesto["deliverables"]["drawings"]
    artefatos = list(desenhos.get("artifacts") or [])
    no_disco = sorted(a.split("/", 1)[1] for a in artefatos)
    pulados = dict(desenhos.get("skipped") or {})
    gaps = []
    for nome in TRES:
        if "drawings/" + nome not in artefatos:
            gaps.append("%s fora do manifesto: %r" % (nome, artefatos))
        if nome in pulados:
            gaps.append("%s emitido e triado ao mesmo tempo: %r"
                        % (nome, pulados.get(nome)))
    _confere_folhas(no_disco, destino, gaps, exigir=TRES)
    # Os dois aceites: a folha esta certa (drawing-vs-data contra o
    # calculado, nunca contra o proprio SVG) e a folha sai.
    svg_vigas = open(os.path.join(
        destino, "drawings", TRES[0]), encoding="utf-8").read()
    conf_v = dp.confere_armacao_vigas(estrutura["vigas"], svg_vigas)
    if not conf_v["ok"]:
        gaps.append("drawing-vs-data das vigas reprova: %r" % (conf_v,))
    svg_fund = open(os.path.join(
        destino, "drawings", TRES[2]), encoding="utf-8").read()
    conf_f = dfe.confere_desenho_fundacao(estrutura["fundacao"], svg_fund)
    if not conf_f["ok"]:
        gaps.append("drawing-vs-data da fundacao reprova: %r" % (conf_f,))
    res = lente.conferir_indice_disco(
        sorted(MAPA_CO), dict(MAPA_CO), no_disco, pulados)
    if res["faltando"]:
        gaps.append("G91 acusa faltando com as folhas no disco: %r" % (res,))
    # G100: os ramos PE-CO-02/03/04 sumiram do motivo (nome morto apos o
    # fato, como no G99); o que resta e' o generico do laco.
    for codigo in ("PE-CO-02", "PE-CO-03", "PE-CO-04"):
        motivo = casa._motivo_folha_casa_nao_emitida(codigo, "titulo")
        if ("sem emissor de armacao" in motivo
                or "sem emissor de detalhes" in motivo
                or "sem emissor de locacao" in motivo):
            gaps.append("%s ainda tem ramo de motivo morto: %r"
                        % (codigo, motivo))
    assert not gaps, (
        "G100 caminho de concreto:\n%s" % "\n".join("  - " + g for g in gaps))


def test_02_alvenaria_nomeia_nunca_emite_vazia(tmp_path):
    """Sem viga de concreto (por_linha vazio, G61) e sem fundacao por
    pilar (sapata corrida), as folhas saem nomeadas - nunca vazias. A
    laje existe nos dois caminhos e continua saindo."""
    manifesto, destino = _hook(tmp_path, _estrutura_alvenaria(),
                               nome="run-alvenaria")
    desenhos = manifesto["deliverables"]["drawings"]
    artefatos = list(desenhos.get("artifacts") or [])
    pulados = dict(desenhos.get("skipped") or {})
    gaps = []
    for nome in ("armacao-vigas-pilares-casa.svg",
                 "fundacao-locacao-formas-casa.svg"):
        if os.path.isfile(os.path.join(destino, "drawings", nome)):
            gaps.append("%s sem dado devia nao sair no disco (folha vazia)"
                        % nome)
        motivo = pulados.get(nome)
        if not motivo:
            gaps.append("%s sem dado devia sair nomeado: %r"
                        % (nome, sorted(pulados)))
        elif "nao calculad" not in motivo and "sem emissor" not in motivo \
                and "not_available" not in motivo:
            gaps.append("%s sem o dado nomeado: %r" % (nome, motivo))
    if "drawings/detalhes-concreto-casa.svg" not in artefatos:
        gaps.append("detalhes (laje) devia sair no caminho de alvenaria: %r"
                    % (artefatos,))
    _confere_folhas(
        [a.split("/", 1)[1] for a in artefatos], destino, gaps,
        exigir=("detalhes-concreto-casa.svg",))
    assert not gaps, (
        "G100 caminho de alvenaria:\n%s" % "\n".join("  - " + g for g in gaps))


def test_03_vermelho_por_injecao_desligar_a_chamada(tmp_path, monkeypatch):
    """Desligar a chamada faz os tres voltarem a faltar: o caso bom emite
    (verde) e, sem arquivo e sem motivo, a lente acusa `faltando` (o
    vermelho que provaria a regressao se a ligacao sumisse em silencio).
    O defeito mora numa copia em `tmp_path`, nunca na arvore viva."""
    import desenho_casa_residencial as dcr

    estrutura = _estrutura_concreto()
    manifesto, _destino = _hook(tmp_path, estrutura, nome="run-bom")
    desenhos = manifesto["deliverables"]["drawings"]
    bom = sorted(a.split("/", 1)[1]
                 for a in desenhos.get("artifacts") or [])
    pulados = dict(desenhos.get("skipped") or {})
    caminho = tmp_path / "mapa_casa_pe_co.json"
    caminho.write_text(json.dumps(dict(MAPA_CO)), encoding="utf-8")
    mapa = dict(json.loads(caminho.read_text(encoding="utf-8")))
    gaps = []
    res_bom = lente.conferir_indice_disco(sorted(mapa), mapa, bom, pulados)
    # O hook minimo emite planta-formas/telhado fora deste recorte de 3
    # codigos (extra_no_disco do recorte, nao da rodada): o que vale aqui
    # e' faltando/sem_mapa, como no test_01 do G92.
    if res_bom["faltando"] or res_bom["sem_mapa"]:
        gaps.append("caso bom devia fechar 3/3 no disco: %r" % (res_bom,))
    for _nome in ("armacao_vigas_pilares_casa_svg",
                  "detalhes_concreto_casa_svg",
                  "fundacao_locacao_formas_casa_svg"):
        monkeypatch.setattr(
            dcr, _nome,
            lambda estrutura, titulo=None: (_ for _ in ()).throw(
                ValueError("injetado: chamada desligada")))
    manifesto2, destino2 = _hook(tmp_path, estrutura, nome="run-injetado")
    desenhos2 = manifesto2["deliverables"]["drawings"]
    mal = sorted(a.split("/", 1)[1]
                 for a in desenhos2.get("artifacts") or [])
    if any(n in mal for n in TRES):
        gaps.append("injetado ainda emite: %r" % (mal,))
    for nome in TRES:
        if os.path.isfile(os.path.join(destino2, "drawings", nome)):
            gaps.append("injetado com arquivo no disco: %s" % nome)
    # Sem arquivo e sem motivo a lente vai a vermelho nos tres codigos;
    # com o motivo do laco, a ausencia sai declarada (nunca silenciosa).
    vermelho = lente.conferir_indice_disco(sorted(mapa), mapa, mal, {})
    if vermelho["faltando"] != sorted(mapa):
        gaps.append("injetado sem motivo devia acusar faltando %r: %r"
                    % (sorted(mapa), vermelho))
    assert not gaps, (
        "G100 injecao:\n%s" % "\n".join("  - " + g for g in gaps))
