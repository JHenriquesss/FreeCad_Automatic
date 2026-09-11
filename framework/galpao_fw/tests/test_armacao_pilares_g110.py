"""G110 - a folha diz o que desenha: PE-CO-02 promete "Armacao pilares/vigas".

Medido (G106, BACKLOG-GOALS-G107-G112.md:174-200): `pacote_legal._PRANCHAS`
promete "Armacao pilares/vigas" em PE-CO-02 nas duas tipologias de concreto,
mas casa (G100) e predio mapeiam PE-CO-02 para a folha de VIGAS
(`desenho_pavimento.prancha_armacao_vigas_svg`); nenhum emissor de armacao
de pilar existe na arvore. O dado EXISTE: `pilar_continuo.dimensiona`
publica por lance `b`, `h`, `As_cm2`, `taxa_pct`, `Nd`, e o `detalhe` de
`pilar_concreto` traz o estribo adotado (phi, s, ramos) e o
`s_limite_governante` da 18.4.3 (D84). Amostra real medida: predio base
{"b": 0.19, "h": 0.3, "Nd": 408.8, "As_cm2": 2.28, "taxa_pct": 0.4} com
detalhe {"phi_estribo_mm": 5.0, "s_estribo": 0.15, "n_ramos_estribo": 2,
"s_limite_governante": "18.3 (viga)"}; casa base {"b": 0.14, "h": 0.3,
"Nd": 73.6, "As_cm2": 1.68}, governante "18.4.3 menor dimensao". A bitola
longitudinal NAO e' calculada: so entra se `phi_long_mm` for declarado
(`pilar_concreto.py:683`) - nenhum produtor a declara.

Entrega (agente paralelo): em `desenho_pavimento.py` a primitiva
`prancha_armacao_pilares_svg(pilares, titulo=None)` (quadro por pilar/lance:
secao, As, taxa, estribo, limite governante, tudo lido do resultado; o
arranjo sai DECLARADO onde nao houver bitola), `confere_armacao_pilares`
(drawing-vs-data por contagem independente via regex por nome, padrao G69),
`gerar_prancha_armacao_pilares` e `prancha_armacao_vigas_pilares_svg`
(combinada vigas+pilares); o wrapper
`desenho_casa_residencial.armacao_vigas_pilares_casa_svg(estrutura)` passa
a emitir a combinada.

Aceite deste arquivo: drawing-vs-data isolada (predio e casa, 12 pilares
cada) e combinada (17 tramos + 12 pilares); declaracao normativa
(NBR 6118:2014 + ausencia de phi_long_mm declarada, nunca default
silencioso); parse XML + `confere_folha_svg`; vermelho por injecao nos
DOIS sentidos em tmp_path/memoria sem mutar o repo; renderizar-e-olhar
com skip escrito quando o rendering faltar.

Decisao N:1: a folha de pilares entra N:1 com a de vigas (combinada
vigas+pilares sob o PE-CO-02 ja mapeado), como decidido pelo agente
produtor e registrado aqui na entrega.

Convencoes do lote: baseline nos dois sentidos (regra 1), injecao sem
mutar a arvore (regra 2), escada substring -> parse -> renderizar
(regra 3), anti-tautologia - comparacao sempre dado-vs-desenho por
contagem independente, nunca svg consigo mesmo (regra 5) - e "a folha
diz o que desenha" (regra 6). Nenhum item de norma alem de 15.8, 13.2.3,
17.2.2, 17.2.5, 17.3.5.3, 17.4.2, 18.3, 18.4.3 e' afirmado aqui.

Se a primitiva G110 ainda nao existir quando este arquivo rodar, os
testes marcam SKIP aguardando a entrega (sem inventar a string que a
primitiva vai emitir).
"""
import copy
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
REPO = os.path.dirname(os.path.dirname(GALPAO))

import desenho_svg_base as sb

_CASA = {}

# Clausulas que este arquivo pode afirmar (MUST NOT DO do goal).
_CLAUSULAS_PERMITIDAS = {"15.8", "13.2.3", "17.2.2", "17.2.5", "17.3.5.3",
                         "17.4.2", "18.3", "18.4.3"}


def _dp():
    """Primitivas G110, ou SKIP escrito se a entrega ainda nao pousou."""
    import desenho_pavimento as dp

    for nome in ("prancha_armacao_pilares_svg", "confere_armacao_pilares",
                 "gerar_prancha_armacao_pilares",
                 "prancha_armacao_vigas_pilares_svg"):
        if not hasattr(dp, nome):
            pytest.skip("G110 aguardando entrega: desenho_pavimento.%s "
                        "ainda nao existe" % nome)
    return dp


def _pilares_predio():
    """12 pilares reais do predio (fonte independente, nunca a mao)."""
    from tests.test_edificio_pranchas_g56 import _caso

    R, _H, _E, _I = _caso()
    pilares = R["pilares"]
    assert len(pilares) == 12, sorted(pilares)
    return pilares


def _vigas_predio():
    """7 linhas / 17 tramos reais do predio (G34)."""
    from tests.test_edificio_pranchas_g56 import _caso

    R, _H, _E, _I = _caso()
    vv = R["vigas_verificacao"]
    assert vv["n_tramos"] == 17, vv.get("n_tramos")
    return vv


def _estrutura_casa():
    """Estrutura real da casa (spec persistido, fonte independente)."""
    if _CASA.get("estrutura") is not None:
        return _CASA["estrutura"]
    import casa_residencial as cres
    from builtin_adapters import register_builtin_adapters
    from project_loop import normalize_spec

    register_builtin_adapters()
    spec = json.load(open(os.path.join(
        REPO, "projects", "casa-residencial", "project-spec.json"),
        encoding="utf-8"))
    resultado, _reg = cres.run_casa_residencial(normalize_spec(spec), None)
    estrutura = resultado["estrutura"]
    assert len(estrutura["pilares"]) == 12, sorted(estrutura["pilares"])
    assert estrutura["vigas"]["n_tramos"] == 17, \
        estrutura["vigas"].get("n_tramos")
    _CASA["estrutura"] = estrutura
    return estrutura


def _conta_nome(svg, nome):
    """Contagem INDEPENDENTE por nome (regex G69), dado-vs-desenho."""
    return len(re.findall(re.escape(str(nome)) + r"(?![0-9])", svg or ""))


def test_01_isolada_predio_lista_os_12_pilares_do_resultado():
    """Drawing-vs-data isolada (predio): a folha lista exatamente os 12
    pilares de R["pilares"], contados por regex independente."""
    dp = _dp()
    pilares = _pilares_predio()
    svg = dp.prancha_armacao_pilares_svg(pilares)
    conf = dp.confere_armacao_pilares(pilares, svg)
    gaps = []
    if not conf["ok"]:
        gaps.append("confere reprova no caso bom: %r" % (conf,))
    if conf.get("n_pilares") != len(pilares) != 12:
        gaps.append("n_pilares=%r, len=%d (esperado 12)" % (
            conf.get("n_pilares"), len(pilares)))
    for nome in pilares:
        if _conta_nome(svg, nome) < 1:
            gaps.append("%s calculado sem ocorrencia desenhada" % nome)
    assert not gaps, "G110 isolada predio:\n%s" % "\n".join(
        "  - " + g for g in gaps)


def test_02_isolada_casa_p11_a_p43_do_calculo():
    """Drawing-vs-data isolada (casa): os 12 pilares P11..P43 da estrutura
    real, contados por regex independente."""
    dp = _dp()
    pilares = _estrutura_casa()["pilares"]
    svg = dp.prancha_armacao_pilares_svg(pilares)
    conf = dp.confere_armacao_pilares(pilares, svg)
    gaps = []
    if not conf["ok"]:
        gaps.append("confere reprova no caso bom: %r" % (conf,))
    if conf.get("n_pilares") != len(pilares) != 12:
        gaps.append("n_pilares=%r, len=%d (esperado 12)" % (
            conf.get("n_pilares"), len(pilares)))
    for nome in pilares:
        if _conta_nome(svg, nome) < 1:
            gaps.append("%s calculado sem ocorrencia desenhada" % nome)
    assert not gaps, "G110 isolada casa:\n%s" % "\n".join(
        "  - " + g for g in gaps)


def test_03_combinada_tem_17_tramos_e_12_pilares():
    """A combinada contem os 17 tramos (confere_armacao_vigas ok) E os 12
    pilares (confere_armacao_pilares ok) - N:1 sob o PE-CO-02."""
    dp = _dp()
    import desenho_casa_residencial as dcr

    estrutura = _estrutura_casa()
    svg = dcr.armacao_vigas_pilares_casa_svg(estrutura)
    conf_v = dp.confere_armacao_vigas(estrutura["vigas"], svg)
    conf_p = dp.confere_armacao_pilares(estrutura["pilares"], svg)
    gaps = []
    if not conf_v["ok"]:
        gaps.append("vigas na combinada reprovam: %r" % (conf_v,))
    if conf_v.get("n_tramos") != 17:
        gaps.append("n_tramos=%r (esperado 17)" % conf_v.get("n_tramos"))
    if not conf_p["ok"]:
        gaps.append("pilares na combinada reprovam: %r" % (conf_p,))
    if conf_p.get("n_pilares") != 12:
        gaps.append("n_pilares=%r (esperado 12)" % conf_p.get("n_pilares"))
    # Contagem independente dos dois lados, nunca o svg consigo mesmo.
    for nome in estrutura["pilares"]:
        if _conta_nome(svg, nome) < 1:
            gaps.append("pilar %s sem ocorrencia na combinada" % nome)
    for linha in estrutura["vigas"]["por_linha"]:
        viga = linha["nome"]
        esperado = len(linha.get("tramos") or [])
        achados = _conta_nome(svg, viga)
        if achados < esperado:
            gaps.append("%s: %d tramos calculados, %d desenhados"
                        % (viga, esperado, achados))
    assert not gaps, "G110 combinada:\n%s" % "\n".join(
        "  - " + g for g in gaps)


def test_04_norma_parse_e_guarda_da_folha():
    """A folha diz que calcula pela NBR 6118:2014, declara a ausencia de
    phi_long_mm (sem inventar bitola), parseia como XML e passa na guarda
    da folha. Nenhuma clausula alem das permitidas e' afirmada."""
    dp = _dp()
    pilares = _pilares_predio()
    svg = dp.prancha_armacao_pilares_svg(pilares)
    gaps = []
    if "NBR 6118:2014" not in svg:
        gaps.append("folha sem declarar NBR 6118:2014")
    # Sem inventar a frase exata da primitiva: o que vale e' a ausencia
    # sair NOMEADA (o dado phi_long_mm dito nao declarado).
    if "phi_long_mm" not in svg:
        gaps.append("folha omite o dado ausente (phi_long_mm nao nomeado)")
    if "NAO DETALHADO" not in svg.upper():
        gaps.append("arranjo sem declaracao de nao-detalhado")
    for numero in re.findall(r"(?<!\d)(\d{2}\.\d(?:\.\d+)?)(?![\d.])", svg):
        if numero not in _CLAUSULAS_PERMITIDAS:
            gaps.append("clausula %s fora do rol permitido" % numero)
    try:
        ET.fromstring(svg)
    except ET.ParseError as exc:
        gaps.append("SVG malformado: %s" % exc)
    else:
        conf = sb.confere_folha_svg(svg)
        if not conf["ok"]:
            gaps.append("confere_folha_svg reprova: %s" % conf.get("motivo"))
    assert not gaps, "G110 norma/guarda:\n%s" % "\n".join(
        "  - " + g for g in gaps)


def test_05_vermelho_pilar_fantasma_no_dado(tmp_path):
    """Baseline sentido 1: o caso bom e' verde; com um pilar fantasma a
    mais no DADO (copia em memoria, repo intacto) o confere acusa."""
    dp = _dp()
    pilares = _pilares_predio()
    svg_bom = dp.prancha_armacao_pilares_svg(pilares)
    assert dp.confere_armacao_pilares(pilares, svg_bom)["ok"]
    # Gerar-em-disco tambem e' verde no caso bom (a folha sai).
    caminho = dp.gerar_prancha_armacao_pilares(
        pilares, str(tmp_path / "pilares-bom.svg"))
    assert os.path.isfile(caminho)
    svg_disco = open(caminho, encoding="utf-8").read()
    assert dp.confere_armacao_pilares(pilares, svg_disco)["ok"]
    # Injecao: um pilar a mais no dado, mesmo desenho.
    injetado = copy.deepcopy(pilares)
    testemunha = next(iter(pilares))
    injetado["PX-FANTASMA"] = copy.deepcopy(pilares[testemunha])
    conf = dp.confere_armacao_pilares(injetado, svg_bom)
    assert conf["ok"] is False, "fantasma no dado devia reprovar: %r" % (conf,)
    assert any("PX-FANTASMA" in f for f in conf["faltando"]), conf
    assert pilares.keys() == _pilares_predio().keys(), "repo mutado"


def test_06_vermelho_linha_de_pilar_removida_do_svg():
    """Baseline sentido 1 (outra ponta): com a linha de um pilar removida
    do SVG em memoria, o confere acusa (verde no desenho intacto)."""
    dp = _dp()
    pilares = _pilares_predio()
    svg_bom = dp.prancha_armacao_pilares_svg(pilares)
    assert dp.confere_armacao_pilares(pilares, svg_bom)["ok"]
    testemunha = sorted(pilares)[0]
    assert _conta_nome(svg_bom, testemunha) >= 1
    svg_mutilado = re.sub(re.escape(testemunha), "", svg_bom, count=1)
    assert _conta_nome(svg_mutilado, testemunha) == \
        _conta_nome(svg_bom, testemunha) - 1
    conf = dp.confere_armacao_pilares(pilares, svg_mutilado)
    assert conf["ok"] is False, "linha removida devia reprovar: %r" % (conf,)
    assert any(testemunha in f for f in conf["faltando"]), conf


def test_07_baseline_outro_sentido_vazio_declara_ausencia():
    """Baseline sentido 2: dado vazio {} + svg declarando a ausencia ->
    ok (a ausencia sai nomeada, nunca folha vazia fingindo conteudo)."""
    dp = _dp()
    svg_vazio = dp.prancha_armacao_pilares_svg({})
    conf = dp.confere_armacao_pilares({}, svg_vazio)
    gaps = []
    if not conf["ok"]:
        gaps.append("vazio declarado devia passar: %r" % (conf,))
    if conf.get("n_pilares") != 0:
        gaps.append("n_pilares devia ser 0: %r" % (conf,))
    if not ("NAO" in svg_vazio.upper() or "sem " in svg_vazio.lower()
            or "ausente" in svg_vazio.lower() or "0" in svg_vazio):
        gaps.append("ausencia sem declaracao no svg vazio")
    assert not gaps, ("G110 baseline outro sentido:\n%s"
                      % "\n".join("  - " + g for g in gaps))


def test_08_renderizar_e_olhar_combinada(tmp_path):
    """Renderizar-e-olhar (regra 3): a combinada rasteriza via
    caderno_casa_edificio.svg_para_png; sem fitz, SKIP escrito."""
    dp = _dp()
    import desenho_casa_residencial as dcr

    _ = dp
    estrutura = _estrutura_casa()
    svg = dcr.armacao_vigas_pilares_casa_svg(estrutura)
    svg_path = str(tmp_path / "combinada-g110.svg")
    png_path = str(tmp_path / "combinada-g110.png")
    open(svg_path, "w", encoding="utf-8").write(svg)
    try:
        import fitz  # noqa: F401
    except ImportError:
        pytest.skip("rendering indisponivel: fitz ausente - "
                    "svg_para_png nao pode rasterizar")
    import caderno_casa_edificio as caderno

    ok = caderno.svg_para_png(svg_path, png_path)
    if not ok:
        pytest.skip("rendering indisponivel: svg_para_png devolveu False "
                    "neste ambiente (nao falhar, nao silenciar)")
    assert os.path.isfile(png_path)
    assert os.path.getsize(png_path) > 0
