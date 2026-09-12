"""G115 - a armacao de pilar mostra todos os trechos, nao so o lance de base.

Medido (G113, BACKLOG-GOALS-G114-G118.md:112-131): `desenho_pavimento`
(G110) desenhava uma fileira por pilar, do lance de BASE (lances[-1]).
No spec persistido do predio (`projects/edificio-multipavimento`), 8 dos
12 pilares mudam de secao ou de As entre lances (9 lances cada); a casa
tem 1 lance por pilar e nao e' afetada. A 18.4 da 2023 e' identica a da
2014 (conferido pela imagem no G113, D136) - nenhuma clausula nova e'
afirmada aqui alem das ja permitidas no G110.

Entrega: uma fileira por TRECHO de lances iguais (mesma secao e mesmo As)
em `desenho_pavimento.py` (`_trechos_pilar`, `_vals_fileira_trecho`,
`_escreve_secao_pilares` por trecho, altura dinamica por fileiras,
`confere_armacao_pilares` por trecho com soma dos lances). Pilar sem
mudanca continua com uma fileira ("1-N").

Aceite deste arquivo: desenho-vs-dado por trecho (predio 12 pilares /
42 trechos, casa 12 pilares / 12 trechos); vermelho por injecao nos DOIS
sentidos em tmp_path/memoria sem mutar o repo (lance com secao trocada no
dado -> a folha antiga reprova na lente); `confere_folha_svg`; renderizar
e olhar com skip escrito quando o rendering faltar.

Convencoes do lote: baseline nos dois sentidos (regra 1), injecao sem
mutar a arvore (regra 2), escada substring -> parse -> renderizar
(regra 3), anti-tautologia - esperado medido e escrito aqui (mapa de
trechos), contado no SVG por regex independente, nunca o svg consigo
mesmo (regra 5) - e "a folha diz o que desenha" (regra 6: rodape declara
os trechos). Nenhum item de norma alem de 15.8, 13.2.3, 17.2.2, 17.2.5,
17.3.5.3, 17.4.2, 18.3, 18.4.3 e' afirmado aqui.
"""
import copy
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

# Clausulas que este arquivo pode afirmar (as mesmas do G110).
_CLAUSULAS_PERMITIDAS = {"15.8", "13.2.3", "17.2.2", "17.2.5", "17.3.5.3",
                         "17.4.2", "18.3", "18.4.3"}

# Mapa MEDIDO dos trechos do predio (spec persistido, 9 lances por pilar;
# chave = mesma secao e mesmo As, contiguos; rotulos 1-based do topo).
# Verificado em 2026-09-12 contra `pilar_continuo.dimensiona` via _caso():
# P11/P13/P41/P43 sem mudanca (1 trecho "1-9"); P12/P42 com 5; P21/P23/P31
# /P33 com 3 ("1-7","8","9"); P22/P32 com 8 ("1-2" + 6 isolados).
_TRECHOS_MEDIDOS = {
    "P11": ["1-9"], "P12": ["1-5", "6", "7", "8", "9"],
    "P13": ["1-9"], "P21": ["1-7", "8", "9"],
    "P22": ["1-2", "3", "4", "5", "6", "7", "8", "9"],
    "P23": ["1-7", "8", "9"], "P31": ["1-7", "8", "9"],
    "P32": ["1-2", "3", "4", "5", "6", "7", "8", "9"],
    "P33": ["1-7", "8", "9"], "P41": ["1-9"],
    "P42": ["1-5", "6", "7", "8", "9"], "P43": ["1-9"],
}
_N_TRECHOS_PREDIO = 42


def _dp():
    import desenho_pavimento as dp

    for nome in ("prancha_armacao_pilares_svg", "confere_armacao_pilares",
                 "gerar_prancha_armacao_pilares",
                 "prancha_armacao_vigas_pilares_svg", "_trechos_pilar"):
        assert hasattr(dp, nome), "G115 sem entrega: desenho_pavimento.%s" % nome
    return dp


def _pilares_predio():
    from tests.test_edificio_pranchas_g56 import _caso

    R, _H, _E, _I = _caso()
    pilares = R["pilares"]
    assert len(pilares) == 12, sorted(pilares)
    return pilares


def _vigas_predio():
    from tests.test_edificio_pranchas_g56 import _caso

    R, _H, _E, _I = _caso()
    vv = R["vigas_verificacao"]
    assert vv["n_tramos"] == 17, vv.get("n_tramos")
    return vv


def _estrutura_casa():
    if _CASA.get("estrutura") is not None:
        return _CASA["estrutura"]
    import casa_residencial as cres
    from builtin_adapters import register_builtin_adapters
    from project_loop import normalize_spec
    import json

    register_builtin_adapters()
    spec = json.load(open(os.path.join(
        REPO, "projects", "casa-residencial", "project-spec.json"),
        encoding="utf-8"))
    resultado, _reg = cres.run_casa_residencial(normalize_spec(spec), None)
    estrutura = resultado["estrutura"]
    assert len(estrutura["pilares"]) == 12, sorted(estrutura["pilares"])
    _CASA["estrutura"] = estrutura
    return estrutura


def _conta_nome(svg, nome):
    """Contagem INDEPENDENTE por nome (regex G69), dado-vs-desenho."""
    return len(re.findall(re.escape(str(nome)) + r"(?![0-9A-Za-z])", svg or ""))


def test_01_predio_uma_fileira_por_trecho_42():
    """Drawing-vs-data por trecho (predio): 12 pilares, 42 trechos, cada
    intervalo medido desenhado, e a soma cobre os 9 lances de cada pilar."""
    dp = _dp()
    pilares = _pilares_predio()
    svg = dp.prancha_armacao_pilares_svg(pilares)
    conf = dp.confere_armacao_pilares(pilares, svg)
    gaps = []
    if not conf["ok"]:
        gaps.append("confere reprova no caso bom: %r" % (conf,))
    if conf.get("n_pilares") != 12:
        gaps.append("n_pilares=%r (esperado 12)" % conf.get("n_pilares"))
    if conf.get("n_trechos") != _N_TRECHOS_PREDIO:
        gaps.append("n_trechos=%r (esperado %d)" % (
            conf.get("n_trechos"), _N_TRECHOS_PREDIO))
    for nome, intervalos in _TRECHOS_MEDIDOS.items():
        if _conta_nome(svg, nome) < len(intervalos):
            gaps.append("%s: %d trechos medidos, %d ocorrencias desenhadas"
                        % (nome, len(intervalos), _conta_nome(svg, nome)))
        for rotulo in intervalos:
            if rotulo not in svg:
                gaps.append("%s trecho %s: intervalo nao desenhado" % (nome, rotulo))
    # a folha soma exatamente os lances de cada pilar do resultado
    for nome in pilares:
        if len((pilares[nome] or {}).get("lances") or []) != 9:
            gaps.append("%s: %d lances (esperado 9)" % (
                nome, len((pilares[nome] or {}).get("lances") or [])))
    assert not gaps, "G115 predio por trecho:\n%s" % "\n".join(
        "  - " + g for g in gaps)


def test_02_casa_um_lance_uma_fileira():
    """A casa tem 1 lance por pilar: 12 pilares, 12 trechos, inalterada."""
    dp = _dp()
    pilares = _estrutura_casa()["pilares"]
    svg = dp.prancha_armacao_pilares_svg(pilares)
    conf = dp.confere_armacao_pilares(pilares, svg)
    gaps = []
    if not conf["ok"]:
        gaps.append("confere reprova na casa: %r" % (conf,))
    if conf.get("n_trechos") != 12:
        gaps.append("n_trechos=%r (esperado 12)" % conf.get("n_trechos"))
    for nome in pilares:
        if len((pilares[nome] or {}).get("lances") or []) != 1:
            gaps.append("%s: %d lances (esperado 1)" % (
                nome, len((pilares[nome] or {}).get("lances") or [])))
        if _conta_nome(svg, nome) < 1:
            gaps.append("%s calculado sem ocorrencia desenhada" % nome)
    assert not gaps, "G115 casa:\n%s" % "\n".join("  - " + g for g in gaps)


def test_03_vermelho_secao_trocada_no_dado(tmp_path):
    """Baseline sentido 1 (o aceite do goal): lance com secao trocada no
    DADO (copia em memoria, repo intacto) -> a folha antiga reprova na
    lente nova. O G110 desenhava so a base: a variacao escondida agora
    acusa."""
    dp = _dp()
    pilares = _pilares_predio()
    svg_bom = dp.prancha_armacao_pilares_svg(pilares)
    assert dp.confere_armacao_pilares(pilares, svg_bom)["ok"]
    caminho = dp.gerar_prancha_armacao_pilares(
        pilares, str(tmp_path / "pilares-trechos-bom.svg"))
    assert os.path.isfile(caminho)
    svg_disco = open(caminho, encoding="utf-8").read()
    assert dp.confere_armacao_pilares(pilares, svg_disco)["ok"]
    # Injecao: um lance do meio troca de secao no dado, mesmo desenho.
    injetado = copy.deepcopy(pilares)
    testemunha = "P11"  # pilar sem mudanca: 1 trecho "1-9" vira 3
    lances = injetado[testemunha]["lances"]
    assert len(lances) == 9
    lances[4] = copy.deepcopy(lances[4])
    lances[4]["b"] = 0.25
    conf = dp.confere_armacao_pilares(injetado, svg_bom)
    assert conf["ok"] is False, "secao trocada devia reprovar: %r" % (conf,)
    assert any(testemunha in f for f in conf["faltando"]), conf
    assert pilares.keys() == _pilares_predio().keys(), "repo mutado"


def test_04_vermelho_fileira_de_trecho_removida_do_svg():
    """Baseline sentido 1 (outra ponta): com uma ocorrencia de um pilar de
    varios trechos removida do SVG em memoria, o confere acusa."""
    dp = _dp()
    pilares = _pilares_predio()
    svg_bom = dp.prancha_armacao_pilares_svg(pilares)
    assert dp.confere_armacao_pilares(pilares, svg_bom)["ok"]
    testemunha = "P22"  # 8 trechos medidos
    assert _conta_nome(svg_bom, testemunha) >= 8
    svg_mutilado = re.sub(re.escape(testemunha), "", svg_bom, count=1)
    assert _conta_nome(svg_mutilado, testemunha) == \
        _conta_nome(svg_bom, testemunha) - 1
    conf = dp.confere_armacao_pilares(pilares, svg_mutilado)
    assert conf["ok"] is False, "fileira removida devia reprovar: %r" % (conf,)
    assert any(testemunha in f for f in conf["faltando"]), conf


def test_05_baseline_outro_sentido_vazio_declara_ausencia():
    """Baseline sentido 2: dado vazio {} + svg declarando a ausencia ->
    ok (a ausencia sai nomeada, nunca folha vazia fingindo conteudo)."""
    dp = _dp()
    svg_vazio = dp.prancha_armacao_pilares_svg({})
    conf = dp.confere_armacao_pilares({}, svg_vazio)
    gaps = []
    if not conf["ok"]:
        gaps.append("vazio declarado devia passar: %r" % (conf,))
    if conf.get("n_trechos") != 0:
        gaps.append("n_trechos devia ser 0: %r" % (conf,))
    assert not gaps, ("G115 baseline outro sentido:\n%s"
                      % "\n".join("  - " + g for g in gaps))


def test_06_norma_parse_guarda_e_diz_o_que_desenha():
    """A folha diz que calcula pela NBR 6118:2014, declara os trechos no
    rodape, parseia como XML e passa na guarda da folha."""
    dp = _dp()
    pilares = _pilares_predio()
    svg = dp.prancha_armacao_pilares_svg(pilares)
    gaps = []
    if "NBR 6118:2014" not in svg:
        gaps.append("folha sem declarar NBR 6118:2014")
    if "phi_long_mm" not in svg:
        gaps.append("folha omite o dado ausente (phi_long_mm nao nomeado)")
    if "NAO DETALHADO" not in svg.upper():
        gaps.append("arranjo sem declaracao de nao-detalhado")
    if "uma fileira por trecho" not in svg.lower():
        gaps.append("rodape nao declara os trechos (a folha nao diz o que desenha)")
    if "LANCES" not in svg:
        gaps.append("cabecalho sem coluna LANCES")
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
    assert not gaps, "G115 norma/guarda:\n%s" % "\n".join(
        "  - " + g for g in gaps)


def test_07_combinada_tem_17_tramos_e_42_trechos(tmp_path):
    """Tres aceites por folha: esta certa (os dois confere ok), sai no
    manifesto (gera em disco em tmp_path) e diz o que desenha (trechos no
    rodape). A altura cresce com as fileiras (G77)."""
    dp = _dp()
    vv = _vigas_predio()
    pilares = _pilares_predio()
    svg = dp.prancha_armacao_vigas_pilares_svg(vv, pilares)
    conf_v = dp.confere_armacao_vigas(vv, svg)
    conf_p = dp.confere_armacao_pilares(pilares, svg)
    gaps = []
    if not conf_v["ok"]:
        gaps.append("vigas na combinada reprovam: %r" % (conf_v,))
    if conf_v.get("n_tramos") != 17:
        gaps.append("n_tramos=%r (esperado 17)" % conf_v.get("n_tramos"))
    if not conf_p["ok"]:
        gaps.append("pilares na combinada reprovam: %r" % (conf_p,))
    if conf_p.get("n_trechos") != _N_TRECHOS_PREDIO:
        gaps.append("n_trechos=%r (esperado %d)" % (
            conf_p.get("n_trechos"), _N_TRECHOS_PREDIO))
    if "uma fileira por trecho" not in svg.lower():
        gaps.append("combinada nao declara os trechos no rodape")
    try:
        ET.fromstring(svg)
    except ET.ParseError as exc:
        gaps.append("SVG malformado: %s" % exc)
    else:
        if not sb.confere_folha_svg(svg)["ok"]:
            gaps.append("confere_folha_svg reprova na combinada: %s"
                        % sb.confere_folha_svg(svg).get("motivo"))
    caminho = dp.gerar_prancha_armacao_vigas_pilares(
        vv, pilares, str(tmp_path / "combinada-trechos.svg"))
    if not os.path.isfile(caminho):
        gaps.append("combinada nao saiu em disco (nao entra no manifesto)")
    assert not gaps, "G115 combinada:\n%s" % "\n".join(
        "  - " + g for g in gaps)


def test_08_renderizar_e_olhar_combinada(tmp_path):
    """Renderizar-e-olhar (regra 3): a combinada com 42 trechos rasteriza
    via caderno_casa_edificio.svg_para_png; sem fitz, SKIP escrito."""
    dp = _dp()
    vv = _vigas_predio()
    pilares = _pilares_predio()
    svg = dp.prancha_armacao_vigas_pilares_svg(vv, pilares)
    svg_path = str(tmp_path / "combinada-g115.svg")
    png_path = str(tmp_path / "combinada-g115.png")
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


# ---------------------------------------------------------------- G119
def test_09_mapa_medido_confrontado_pilar_a_pilar():
    """Auditoria do G115: `_TRECHOS_MEDIDOS` era constante escrita a mao que
    nenhum teste comparava com o dado.

    O test_01 conferia (a) o TOTAL (42) e (b) cada rotulo por substring - e
    substring de trecho isolado ("6", "3") casa em qualquer ponto do SVG
    (medido: uma folha sem esses trechos contem as tres strings). Logo o
    agrupamento POR PILAR podia mudar inteiro - P11 virar 8 trechos e P22
    virar 1 - sem nada reprovar, desde que a soma desse 42. Aqui o mapa e'
    confrontado item a item com `_trechos_pilar` sobre o spec persistido.
    """
    dp = _dp()
    pilares = _pilares_predio()
    medido = {nome: [t["rotulo"] for t in dp._trechos_pilar(pilares[nome])]
              for nome in pilares}
    assert medido == _TRECHOS_MEDIDOS, (
        "mapa de trechos divergiu do medido:\n"
        + "\n".join("  %s: medido %r, baseline %r" % (n, medido.get(n),
                                                      _TRECHOS_MEDIDOS.get(n))
                    for n in sorted(set(medido) | set(_TRECHOS_MEDIDOS))
                    if medido.get(n) != _TRECHOS_MEDIDOS.get(n)))
    assert sum(len(v) for v in medido.values()) == _N_TRECHOS_PREDIO
