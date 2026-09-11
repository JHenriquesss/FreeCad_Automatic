"""G99 - a casa liga o eletrico que ela ja calcula.

Medido (G98): `casa_residencial._motivo_folha_casa_nao_emitida` declarava
PE-EL-01/02/04 como "sem emissor ligado ao hook da casa", e o emissor
existe (`desenho_eletrico_residencial.gerar_desenhos_residenciais`) -
chamado so pelo adaptador da fixture sintetica. Entregue: a chamada no
hook da casa, com os arquivos no manifesto e as triagens proprias do
emissor preservadas; os tres ramos de motivo sumiram (PE-EL-03 continua
declarado: sem emissor, malha nao declarada).

Convencoes do BACKLOG: baseline nos dois sentidos (o caso bom emite, o
injetado volta a faltar - test_04), injecao em tmp_path sem mutar a
arvore viva, parse XML + `confere_folha_svg` (nunca substring), e os dois
aceites ("a folha esta certa" e "a folha sai": parse + arquivo no disco
e no manifesto).
"""
import copy
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import desenho_svg_base as sb
import varredura_indice_disco as lente

TRES = ("unifilar.svg", "quadro-cargas.svg", "planta-eletrica.svg")
MAPA_EL = {"PE-EL-01": "unifilar.svg",
           "PE-EL-02": "planta-eletrica.svg",
           "PE-EL-04": "quadro-cargas.svg"}


def _eletrica():
    """Resultado eletrico real (fase 6B), com layout declarado e valido."""
    from tests.branches.phase6b.test_residential_electrical_deliverables \
        import _result
    return _result()


def _opt():
    return type("O", (), {"generate_2d": True, "generate_caderno": False})()


def _hook(tmp_path, eletrico, nome="run"):
    """Roda o hook da casa sobre uma casa minima com eletrico real."""
    import casa_residencial as casa

    destino = str(tmp_path / nome)
    manifesto = {"artifacts": [], "deliverables": {}}
    resultado = {"arquitetura": None, "estrutura": None,
                 "hidraulica": None, "eletrico": eletrico}
    casa._emitir_desenhos(manifesto, destino, {}, _opt(),
                          copy.deepcopy(resultado))
    return manifesto, destino


def _confere_folhas(no_disco, pulados, destino, gaps, exigir=()):
    """Parse XML + guarda da folha para cada arquivo no disco."""
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


def test_01_hook_emite_as_tres_folhas_com_layout_valido(tmp_path):
    """Com layout valido, unifilar + quadro + planta saem no disco e no
    manifesto, passam no parse e na guarda, e o G91 fecha do lado do
    disco para os tres codigos."""
    import casa_residencial as casa

    manifesto, destino = _hook(tmp_path, _eletrica())
    desenhos = manifesto["deliverables"]["drawings"]
    artefatos = list(desenhos.get("artifacts") or [])
    no_disco = sorted(a.split("/", 1)[1] for a in artefatos)
    pulados = dict(desenhos.get("skipped") or {})
    gaps = []
    for nome in TRES:
        if "drawings/" + nome not in artefatos:
            gaps.append("%s fora do manifesto: %r" % (nome, artefatos))
    _confere_folhas(no_disco, pulados, destino, gaps, exigir=TRES)
    res = lente.conferir_indice_disco(
        sorted(MAPA_EL), dict(MAPA_EL), no_disco, pulados)
    if res["faltando"]:
        gaps.append("G91 acusa faltando com as folhas no disco: %r" % (res,))
    if "eletrica-infra-aterramento-casa.svg" not in pulados:
        gaps.append("PE-EL-03 devia continuar declarado: %r"
                    % (sorted(pulados),))
    # G99: os ramos PE-EL-01/02/04 sumiram do motivo (nome morto apos o
    # fato); PE-EL-03 continua com ramo proprio.
    for codigo in ("PE-EL-01", "PE-EL-02", "PE-EL-04"):
        motivo = casa._motivo_folha_casa_nao_emitida(codigo, "titulo")
        if "sem emissor" in motivo and "ligado ao hook" in motivo:
            gaps.append("%s ainda tem ramo de motivo morto: %r"
                        % (codigo, motivo))
    motivo03 = casa._motivo_folha_casa_nao_emitida("PE-EL-03", "titulo")
    if "PE-EL-03" not in motivo03 or "sem emissor" not in motivo03:
        gaps.append("PE-EL-03 perdeu o ramo proprio: %r" % (motivo03,))
    assert not gaps, (
        "G99 com layout valido:\n%s" % "\n".join("  - " + g for g in gaps))


def test_02_sem_layout_planta_nomeada_nunca_vazia(tmp_path):
    """Sem layout declarado, unifilar + quadro saem e a planta sai
    nomeada (`layout_not_declared`) - nunca folha vazia."""
    eletrico = _eletrica()
    (eletrico.get("circuits") or {}).pop("layout_validation", None)
    manifesto, destino = _hook(tmp_path, eletrico, nome="run-sem-layout")
    desenhos = manifesto["deliverables"]["drawings"]
    artefatos = list(desenhos.get("artifacts") or [])
    no_disco = sorted(a.split("/", 1)[1] for a in artefatos)
    pulados = dict(desenhos.get("skipped") or {})
    gaps = []
    _confere_folhas(no_disco, pulados, destino, gaps,
                    exigir=("unifilar.svg", "quadro-cargas.svg"))
    if os.path.isfile(os.path.join(destino, "drawings",
                                   "planta-eletrica.svg")):
        gaps.append("planta sem layout devia nao sair no disco")
    if pulados.get("planta-eletrica.svg") != "layout_not_declared":
        gaps.append("planta sem layout devia sair nomeada "
                    "layout_not_declared: %r" % (pulados,))
    res = lente.conferir_indice_disco(
        ["PE-EL-01", "PE-EL-02", "PE-EL-04"], dict(MAPA_EL),
        no_disco, pulados)
    if res["faltando"]:
        gaps.append("G91 acusa faltando com a planta nomeada: %r" % (res,))
    assert not gaps, (
        "G99 sem layout:\n%s" % "\n".join("  - " + g for g in gaps))


def test_03_layout_invalido_planta_nomeada_invalid_layout(tmp_path):
    """Com layout declarado mas invalido, a triagem propria do emissor
    (`invalid_layout`) viaja intacta ate o manifesto."""
    eletrico = _eletrica()
    (eletrico.get("circuits") or {})["layout_validation"] = {
        "declared": True, "ok": False, "errors": ["sala sem retangulo"],
        "layout": None}
    manifesto, destino = _hook(tmp_path, eletrico, nome="run-invalido")
    desenhos = manifesto["deliverables"]["drawings"]
    artefatos = list(desenhos.get("artifacts") or [])
    no_disco = sorted(a.split("/", 1)[1] for a in artefatos)
    pulados = dict(desenhos.get("skipped") or {})
    gaps = []
    _confere_folhas(no_disco, pulados, destino, gaps,
                    exigir=("unifilar.svg", "quadro-cargas.svg"))
    if pulados.get("planta-eletrica.svg") != "invalid_layout":
        gaps.append("planta invalida devia sair nomeada invalid_layout: %r"
                    % (pulados,))
    assert not gaps, (
        "G99 layout invalido:\n%s" % "\n".join("  - " + g for g in gaps))


def test_04_vermelho_por_injecao_desligar_a_chamada(tmp_path, monkeypatch):
    """Desligar a chamada faz as tres voltarem a faltar: o caso bom emite
    (verde) e o injetado declara ausencia via o laco (o vermelho que
    provaria a regressao se a ligacao sumisse)."""
    manifesto, destino = _hook(tmp_path, _eletrica(), nome="bom")
    bom = sorted(a.split("/", 1)[1]
                 for a in manifesto["deliverables"]["drawings"]
                 .get("artifacts") or [])
    import desenho_eletrico_residencial as der

    monkeypatch.setattr(
        der, "gerar_desenhos_residenciais",
        lambda resultado, saida: {"files": [], "skipped": {}})
    manifesto2, destino2 = _hook(tmp_path, _eletrica(), nome="injetado")
    desenhos2 = manifesto2["deliverables"]["drawings"]
    mal = sorted(a.split("/", 1)[1]
                 for a in desenhos2.get("artifacts") or [])
    pulados2 = dict(desenhos2.get("skipped") or {})
    gaps = []
    if any(n not in bom for n in TRES):
        gaps.append("caso bom devia emitir as tres: %r" % (bom,))
    if any(n in mal for n in TRES):
        gaps.append("injetado ainda emite: %r" % (mal,))
    if any(n not in pulados2 for n in TRES):
        gaps.append("injetado devia nomear as tres via o laco: %r"
                    % (sorted(pulados2),))
    res = lente.conferir_indice_disco(
        sorted(MAPA_EL), dict(MAPA_EL), mal, pulados2)
    if res["faltando"]:
        gaps.append("injetado devia sair nomeado, nao faltando: %r" % (res,))
    for nome in TRES:
        caminho = os.path.join(destino2, "drawings", nome)
        if os.path.isfile(caminho):
            gaps.append("injetado com arquivo no disco: %s" % nome)
    assert not gaps, (
        "G99 injecao:\n%s" % "\n".join("  - " + g for g in gaps))


def test_05_falha_do_emissor_e_eletrico_ausente_saem_nomeados(
        tmp_path, monkeypatch):
    """G106: o except do hook devolvia listas vazias e apagava a excecao;
    o laco caia no motivo generico "sem emissor ligado" - falso depois do
    G99. A falha tem de viajar com a excecao, e a ausencia de
    `eletrico.circuits` tem de dizer ESSE dado."""
    import desenho_eletrico_residencial as der

    gaps = []
    manifesto, _ = _hook(tmp_path, None, nome="sem-eletrico")
    pulados = dict(manifesto["deliverables"]["drawings"].get("skipped") or {})
    # sem eletrico calculado o indice nem promete PE-EL: nada a nomear

    def _explode(resultado, saida):
        raise RuntimeError("circuito C-99 sem condutor")

    monkeypatch.setattr(der, "gerar_desenhos_residenciais", _explode)
    manifesto2, _ = _hook(tmp_path, _eletrica(), nome="explode")
    pulados2 = dict(manifesto2["deliverables"]["drawings"].get("skipped") or {})
    for nome in TRES:
        motivo = str(pulados2.get(nome) or "")
        if "C-99 sem condutor" not in motivo:
            gaps.append("%s devia carregar a excecao do emissor: %r"
                        % (nome, motivo))
        if "sem emissor ligado" in motivo:
            gaps.append("%s com o motivo generico falso: %r" % (nome, motivo))
    import casa_residencial as casa

    for codigo in MAPA_EL:
        motivo = casa._motivo_folha_casa_nao_emitida(codigo, "t")
        if "eletrico.circuits" not in motivo:
            gaps.append("%s sem o dado nomeado: %r" % (codigo, motivo))
    if any(n in pulados for n in TRES):
        gaps.append("sem eletrico o laco nomeou PE-EL: %r" % (pulados,))
    assert not gaps, (
        "G99 falha/ausencia:\n%s" % "\n".join("  - " + g for g in gaps))
