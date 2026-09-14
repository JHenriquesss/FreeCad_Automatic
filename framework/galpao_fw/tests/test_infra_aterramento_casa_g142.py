"""G142 - PE-EL-03 infraestrutura e aterramento da casa.

Medido (2026-09-14, antes de mudar):
- Casa real: PE-EL-03 sai pulada ("not_available: sem emissor de
  infraestrutura/aterramento nesta rodada (PE-EL-03 Infraestrutura/
  aterramento); malha de aterramento e SPDA nao declarados e sem folha
  emitida"). O predio emite com `desenho_eletrico.infra_aterramento_
  edificio_svg` (`desenho_eletrico.py:439`), chamado so por
  `edificio_adapter.py:1114`.
- O que o calculo eletrico da casa produz (fonte viva:
  `residencial_eletrica.run_residential_electrical` + fixture fase 6B):
  padrao de entrada (ramal, eletroduto, disjuntor geral, condutor de
  aterramento do padrao), QD + circuitos dimensionados (secao/protecao)
  e layout validado (comodos/pontos/quadro). Nao produz: pavimentos
  servidos, prumada, rotas de eletrodutos (`circuits.routes == []`),
  malha de aterramento (solo/resistividade/arranjo) nem SPDA (NP/
  descidas). Remeça no test_01.
- O emissor do predio exige `ele.pavimentos_servidos >= 1` (senao
  ValueError "nada a desenhar") e le `prumada.secao_mm2`: casa terreo
  sem shaft/prumada nao tem o que alimentar. Desenhar eletroduto sem
  rota declarada ou malha/SPDA sem dado seria invencao (regra do lote:
  ausencia se declara, nunca default silencioso).

Entregue (segundo ramo do goal): nada da folha e desenhável sem os
dados, entao a folha segue pulada com o motivo atual e o goal registra
a medicao neste guarda + verbete D171. Nenhuma linha de producao
mudada; predio byte-identico; sem dimensionar SPDA/malha.

Cada teste segue as convencoes: baseline nos dois sentidos, injecao em
tmp_path (nunca mutando o repo), substring -> parse -> renderizar (o
PNG e olhado no verbete D171), lente parte de onde o dado e PRODUZIDO
(a conta, o emissor) e o resumo da suite se le inteiro antes de fechar.
"""
import copy
import inspect
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)


def _eletrica():
    """Resultado eletrico real da casa (fase 6B), com layout valido."""
    from tests.branches.phase6b.test_residential_electrical_deliverables \
        import _result
    return _result()


def _opt():
    return type("O", (), {"generate_2d": True, "generate_caderno": False})()


def _hook(tmp_path, eletrico, nome="run"):
    import casa_residencial as casa

    destino = str(tmp_path / nome)
    manifesto = {"artifacts": [], "deliverables": {}}
    resultado = {"arquitetura": None, "estrutura": None,
                 "hidraulica": None, "eletrico": eletrico}
    casa._emitir_desenhos(manifesto, destino, {}, _opt(),
                          copy.deepcopy(resultado))
    return manifesto, destino


def test_01_remessa_conta_da_casa_contra_emissor_do_predio():
    """O que a conta produz vs o que o emissor do predio consome (fontes
    vivas, nunca o proprio mapa)."""
    import desenho_eletrico as de

    ele = _eletrica()
    gaps = []
    # a conta produz infraestrutura parcial (padrao + QD + circuitos)
    entry = ((ele.get("service_entry") or {}).get("entry") or {})
    for campo in ("breaker_a", "entry_conductors", "grounding_conductor_mm2",
                  "conduit_mm", "row"):
        if entry.get(campo) is None:
            gaps.append("conta sem %r no padrao: %r" % (campo, entry))
    circuits = ele.get("circuits") or {}
    if not isinstance(circuits.get("designs"), list) or not circuits["designs"]:
        gaps.append("conta sem designs dimensionados: %r" % (circuits.keys(),))
    lv = circuits.get("layout_validation") or {}
    if not lv.get("ok") or not isinstance((lv.get("layout") or {}).get("board"), dict):
        gaps.append("conta sem layout validado com quadro: %r" % (lv,))
    # e NAO produz nada do que a infra do predio exige
    for ausente in ("pavimentos_servidos", "prumada"):
        if ausente in ele:
            gaps.append("conta nao devia ter %r" % ausente)
    if (circuits.get("routes") or []) != []:
        gaps.append("rotas de eletrodutos deviam ser [] (nao geradas): %r"
                    % (circuits.get("routes"),))
    blob = str(ele)
    for termo in ("malha", "spda", "resistividade", "eletrodo"):
        if termo in blob.lower():
            gaps.append("conta nao devia citar %r" % termo)
    # o emissor do predio exige o que a casa nao tem (fonte viva: o fonte)
    src = inspect.getsource(de.infra_aterramento_edificio_svg)
    if "pavimentos_servidos" not in src or "prumada" not in src:
        gaps.append("emissor do predio mudou de forma: sem pavimentos/prumada")
    try:
        de.infra_aterramento_edificio_svg({}, {})
        gaps.append("emissor sem pavimentos devia levantar nada-a-desenhar")
    except ValueError as exc:
        if "nada a desenhar" not in str(exc):
            gaps.append("erro do emissor fora do contrato: %r" % (exc,))
    # com shape de predio minimo, emite (o caminho do predio existe)
    svg_predio = de.infra_aterramento_edificio_svg(
        {"pavimentos_servidos": 2, "prumada": {"secao_mm2": 50}}, {})
    if "PRUMADA 50 mm2" not in svg_predio:
        gaps.append("emissor do predio nao desenha prumada do calculo")
    assert not gaps, ("G142 remessa:\n%s" % "\n".join("  - " + g for g in gaps))


def test_02_folha_segue_pulada_com_motivo_e_tres_emitidas():
    """Com eletrico calculado, PE-EL-01/02/04 saem e PE-EL-03 segue pulada
    com malha e SPDA nomeados; nada inventado no disco."""
    import casa_residencial as casa
    import varredura_indice_disco as lente

    # o essencial e o motivo vivo (fonte: a funcao, nao o manifesto).
    gaps = []
    motivo = casa._motivo_folha_casa_nao_emitida("PE-EL-03", "Infraestrutura/aterramento")
    if "PE-EL-03" not in motivo:
        gaps.append("motivo sem codigo: %r" % (motivo,))
    for termo in ("malha", "SPDA"):
        if termo not in motivo:
            gaps.append("motivo sem %r: %r" % (termo, motivo))
    if casa._PRANCHA_ARQUIVO_CASA.get("PE-EL-03") != "eletrica-infra-aterramento-casa.svg":
        gaps.append("mapa da casa sem PE-EL-03: %r"
                    % (casa._PRANCHA_ARQUIVO_CASA.get("PE-EL-03"),))
    # a lente fecha com a pulada nomeada (nao e faltando nem sem_mapa)
    res = lente.conferir_indice_disco(
        ["PE-EL-03"], dict(casa._PRANCHA_ARQUIVO_CASA), [],
        {"eletrica-infra-aterramento-casa.svg": motivo})
    if res["faltando"] or res["sem_mapa"]:
        gaps.append("lente acusa com a pulada nomeada: %r" % (res,))
    assert not gaps, ("G142 motivo:\n%s" % "\n".join("  - " + g for g in gaps))


def test_03_tres_aceites_olhando_o_png(tmp_path):
    """Substring -> parse -> renderizar nas 3 folhas eletricas da casa.
    O que os tres aceites olham no verbete D171: unifilar, planta e quadro
    passam na guarda, rasterizam com bytes e dizem o que desenham sem
    inventar malha/SPDA."""
    import desenho_svg_base as sb
    from caderno_casa_edificio import svg_para_png

    manifesto, destino = _hook(tmp_path, _eletrica())
    desenhos = manifesto["deliverables"]["drawings"]
    artefatos = list(desenhos.get("artifacts") or [])
    pulados = dict(desenhos.get("skipped") or {})
    gaps = []
    # PE-EL-03 segue pulada; as 3 emitidas estao no manifesto e no disco
    if "eletrica-infra-aterramento-casa.svg" not in pulados:
        gaps.append("PE-EL-03 devia seguir pulada: %r" % (sorted(pulados),))
    for nome in ("unifilar.svg", "planta-eletrica.svg", "quadro-cargas.svg"):
        if "drawings/" + nome not in artefatos:
            gaps.append("%s fora do manifesto: %r" % (nome, artefatos))
        caminho = os.path.join(destino, "drawings", nome)
        if not os.path.isfile(caminho):
            gaps.append("%s dito emitido sem arquivo" % nome)
            continue
        svg = open(caminho, encoding="utf-8").read()
        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            gaps.append("%s malformado: %s" % (nome, exc))
            continue
        conf = sb.confere_folha_svg(svg)
        if not conf["ok"]:
            gaps.append("%s reprova a guarda: %s" % (nome, conf["motivo"]))
        p_png = os.path.join(destino, nome + ".png")
        if not svg_para_png(caminho, p_png) or not os.path.getsize(p_png):
            gaps.append("%s nao rasterizou para o aceite visual" % nome)
        # diz o que desenha, sem inventar o que falta
        for termo in ("malha de aterramento", "SPDA NP", "PRUMADA"):
            if termo in svg:
                gaps.append("%s inventa %r" % (nome, termo))
    # a infra que existe ja e declarada onde e devida (sem duplicar folha)
    uni = open(os.path.join(destino, "drawings", "unifilar.svg"),
               encoding="utf-8").read()
    if "ATERRAMENTO" not in uni:
        gaps.append("unifilar sem o condutor de aterramento do calculo")
    assert not gaps, ("G142 PNG:\n%s" % "\n".join("  - " + g for g in gaps))


def test_04_vermelho_por_injecao_nos_dois_sentidos(tmp_path, monkeypatch):
    """Com o emissor as 3 fecham; sem ele voltam a faltar/nomear; sem o
    motivo a PE-EL-03 vira faltando; sem o mapa vira sem_mapa. Tudo em
    tmp_path."""
    import casa_residencial as casa
    import varredura_indice_disco as lente

    manifesto, _dest = _hook(tmp_path, _eletrica(), nome="bom")
    bom = sorted(a.split("/", 1)[1]
                 for a in manifesto["deliverables"]["drawings"]
                 .get("artifacts") or [])
    import desenho_eletrico_residencial as der

    monkeypatch.setattr(der, "gerar_desenhos_residenciais",
                        lambda resultado, saida: {"files": [], "skipped": {}})
    manifesto2, _d2 = _hook(tmp_path, _eletrica(), nome="injetado")
    mal = sorted(a.split("/", 1)[1]
                 for a in manifesto2["deliverables"]["drawings"]
                 .get("artifacts") or [])
    pulados2 = dict(manifesto2["deliverables"]["drawings"].get("skipped") or {})
    gaps = []
    for nome in ("unifilar.svg", "quadro-cargas.svg", "planta-eletrica.svg"):
        if nome not in bom:
            gaps.append("caso bom devia emitir %s: %r" % (nome, bom))
        if nome in mal:
            gaps.append("injetado ainda emite %s: %r" % (nome, mal))
    # o motivo da PE-EL-03 e vivo: sem ele, a lente acusa faltando
    motivo = casa._motivo_folha_casa_nao_emitida("PE-EL-03", "t")
    vazio = lente.conferir_indice_disco(["PE-EL-03"],
                                        dict(casa._PRANCHA_ARQUIVO_CASA), [], {})
    if vazio["OK"] or vazio["faltando"] != ["PE-EL-03"]:
        gaps.append("sem motivo PE-EL-03 devia faltar: %r" % (vazio,))
    cheio = lente.conferir_indice_disco(
        ["PE-EL-03"], dict(casa._PRANCHA_ARQUIVO_CASA), [],
        {"eletrica-infra-aterramento-casa.svg": motivo})
    if cheio["faltando"] or cheio["sem_mapa"]:
        gaps.append("com motivo nao devia faltar: %r" % (cheio,))
    # outro sentido: sem a entrada no mapa, vira sem_mapa
    mapa = dict(casa._PRANCHA_ARQUIVO_CASA)
    del mapa["PE-EL-03"]
    sem_mapa = lente.conferir_indice_disco(["PE-EL-03"], mapa, [], {})
    if sem_mapa["OK"] or sem_mapa["sem_mapa"] != ["PE-EL-03"]:
        gaps.append("sem mapa devia acusar sem_mapa: %r" % (sem_mapa,))
    assert not gaps, ("G142 injecao:\n%s" % "\n".join("  - " + g for g in gaps))


def test_05_predio_byte_identico_e_sem_dimensionar(tmp_path, monkeypatch):
    """A casa nunca chama o emissor do predio; o predio emite igual antes
    e depois; nada dimensiona malha/SPDA."""
    import desenho_eletrico as de

    # a casa nao chama o emissor do predio: se chamasse, explodiria aqui
    def _explode(*a, **k):
        raise AssertionError("casa chamou o emissor do predio")

    monkeypatch.setattr(de, "infra_aterramento_edificio_svg", _explode)
    monkeypatch.setattr(de, "gerar_infra_edificio", _explode)
    gaps = []
    try:
        _hook(tmp_path, _eletrica(), nome="sem-predio")
    except AssertionError as exc:
        gaps.append(str(exc))
    monkeypatch.undo()
    # o predio emite deterministico (byte-identico na mesma entrada)
    a = de.infra_aterramento_edificio_svg(
        {"pavimentos_servidos": 2, "prumada": {"secao_mm2": 50}}, {})
    b = de.infra_aterramento_edificio_svg(
        {"pavimentos_servidos": 2, "prumada": {"secao_mm2": 50}}, {})
    if a != b:
        gaps.append("emissor do predio nao deterministico")
    if "A CONFIRMAR" not in a:
        gaps.append("folha do predio sem o aterramento a confirmar: %r" % (a[:200],))
    # a casa nao dimensiona: nenhum simbolo novo de malha/SPDA no disco
    import pathlib

    _m, dest = _hook(tmp_path, _eletrica(), nome="sem-dim")
    for nome in ("unifilar.svg", "planta-eletrica.svg", "quadro-cargas.svg"):
        svg = pathlib.Path(dest, "drawings", nome).read_text(encoding="utf-8")
        for termo in ("resistencia de malha", "Sverak", "NBR 5419",
                      "SPDA NP", "descidas"):
            if termo in svg and nome != "quadro-cargas.svg":
                # o unifilar/planta nao citam SPDA/malha; o quadro cita a
                # norma de secao/protecao, nunca SPDA/malha dimensionados
                if termo in ("SPDA NP", "Sverak", "resistencia de malha"):
                    gaps.append("%s dimensiona %r" % (nome, termo))
    assert not gaps, ("G142 predio:\n%s" % "\n".join("  - " + g for g in gaps))
