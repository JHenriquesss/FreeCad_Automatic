"""G129 - censo de colisao de rotulo sobre toda folha que o manifesto entrega.

Medido (G125, remedido no G129): 6 de 27 folhas de casa+predio com colisao
(48 pares); o galpao nao tinha sido medido (14 pares em 8 fontes SVG, via
o turnkey real do spec persistido). Cada par triado olhando o PNG: 19
colisoes reais viraram correcao na folha (F1/F2 em
desenho_eletrico_residencial, CORRIGIDOS_G129) e 43 viraram isencao com
motivo (ISENCOES_G129, todas com o PNG conferido).

Entregue:
  1. PORTAO (test_01): o censo vivo das tres tipologias contra o baseline
     nos dois sentidos (par novo = vermelho; par que some sem triagem =
     vermelho), e todo par vivo com motivo escrito - falha UMA vez so,
     com todos os lados na mensagem (a receita do G97).
  2. BASELINE (test_02, nos dois sentidos): universo de 35 folhas + 43
     pares + triagem completa congelados; cura (F1/F2) muda o baseline
     junto com o registro em CORRIGIDOS_G129, nunca em silencio.
  3. INJECAO (test_03/test_04, tmp_path, nunca mutando o repo): rotulo
     empurrado sobre outro, motivo apagado, isencao morta e par sumido
     deixam a suite vermelha; o caso bom fica verde.
  4. FONTES (test_05/test_06): entrada malformada levanta, o instrumento
     acusa SVG malformado, e o universo e ancorado em fontes independentes
     (mapas vivos + emissores que alimentam os PDFs).

Nao fazer (regra do lote): arbitrar valor normativo, inventar dado de
projeto, ou transformar ausencia de dado em default silencioso. Folha do
galpao que o manifesto entrega em PDF e medida na fonte SVG que o
`config_de_spec` rasteriza (dito na lente, nunca fingido que o PDF foi
parseado como SVG).
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
REPO = os.path.dirname(os.path.dirname(GALPAO))

import varredura_colisoes_g129 as lente

_CACHE = {}


def _spec(tipologia):
    pastas = {"casa": ("casa-residencial", "project-spec.json"),
              "predio": ("edificio-multipavimento", "project-spec.json"),
              "galpao": ("galpao-tp-g95", "project-spec.json")}
    pasta, arquivo = pastas[tipologia]
    with open(os.path.join(REPO, "projects", pasta, arquivo),
              encoding="utf-8") as fh:
        return json.load(fh)


def _censo():
    """O censo vivo das 35 folhas (cache por sessao, rodadas deterministicas).

    casa+predio: rodada real no spec persistido (`generate_2d`), artefatos
    SVG do manifesto. galpao: turnkey real do spec persistido (calculo
    puro, sem freecad.exe) + emissores SVG que alimentam os PDFs do
    manifesto (a fonte, convencao 9).
    """
    if "censo" in _CACHE:
        return _CACHE["censo"]
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    censo = {}
    for tipologia in ("casa", "predio"):
        destino = os.path.join(tempfile.mkdtemp(prefix="g129-"), tipologia)
        manifesto = run_project(_spec(tipologia), destino,
                                {"generate_ifc": False, "generate_2d": True})
        desenhos = (manifesto.get("deliverables") or {}).get("drawings") or {}
        for artefato in sorted(desenhos.get("artifacts") or []):
            if not artefato.lower().endswith(".svg"):
                continue
            with open(os.path.join(destino, artefato),
                      encoding="utf-8") as fh:
                censo["%s/%s" % (tipologia, artefato)] = \
                    lente.pares_de_svg(fh.read())
    import galpao_turnkey as tk
    import desenho_hidraulica as dh
    import desenho_incendio as di
    import desenho_eletrico as de
    import desenho_concreto as dco
    import desenho_climatizacao as dcl

    saida = tempfile.mkdtemp(prefix="g129-tk-")
    resultado = tk.rodar(_spec("galpao")["turnkey"], saida)
    disciplinas = resultado["disciplinas"]
    fontes = {
        "galpao/esquema-hidraulica.svg":
            dh.esquema_hidraulica_svg(disciplinas["hidraulica"]["raw"]),
        "galpao/planta-seguranca.svg":
            di.planta_seguranca_svg(disciplinas["incendio"]["raw"]),
        "galpao/esquema-climatizacao.svg":
            dcl.esquema_climatizacao_svg(disciplinas["climatizacao"]["raw"]),
        "galpao/diagrama-unifilar.svg":
            de.diagrama_unifilar_svg(disciplinas["eletrico"]["raw"]),
        "galpao/quadro-cargas.svg":
            de.quadro_cargas_svg(disciplinas["eletrico"]["raw"]),
        "galpao/planta-eletrica.svg":
            de.planta_eletrica_svg(disciplinas["eletrico"]["raw"]),
        "galpao/prancha-armacao.svg":
            dco.prancha_armacao_svg(disciplinas["concreto"]["raw"]),
        "galpao/planta-formas.svg":
            dco.planta_formas_svg(disciplinas["concreto"]["raw"]),
    }
    for chave, svg in fontes.items():
        censo[chave] = lente.pares_de_svg(svg)
    _CACHE["censo"] = censo
    return censo


def test_01_portao_censo_vivo_falha_unica():
    """O portao: as 35 folhas vivas contra o baseline, todos os lados."""
    res = lente.confere_censo(_censo())
    assert res["OK"], ("G129: censo de colisoes reprova:\n%s"
                       % lente.relatorio_pt(res))


def test_02_baseline_universo_e_triagem_nos_dois_sentidos():
    """Universo, baseline e triagem congelados; cura muda junto, gap nao."""
    censo = _censo()
    res = lente.confere_censo(censo)
    universo = set(lente.chaves_do_censo())
    pares_vivos = sum(len(v) for v in censo.values())
    # G97: um assert so, com universo, baseline, triagem e contagens.
    lados = []
    if set(censo) != universo:
        lados.append("universo mudou sem triagem G129: novas=%r sumidas=%r"
                     % (sorted(set(censo) - universo),
                        sorted(universo - set(censo))))
    if len(censo) != 35:
        lados.append("universo com %d folhas (esperado 35: casa 12 + "
                     "predio 15 + galpao 8)" % len(censo))
    if pares_vivos != 43:
        lados.append("censo com %d pares vivos (esperado 43 pos-correcao "
                     "F1/F2)" % pares_vivos)
    for rotulo in ("pares_novos", "pares_sumidos", "sem_triagem",
                   "isencoes_mortas", "folhas_novas", "folhas_sumidas"):
        bloco = res.get(rotulo) or {}
        total = (sum(len(v) for v in bloco.values())
                 if isinstance(bloco, dict) else len(bloco))
        if total:
            lados.append("%s com %s: %r" % (rotulo, total, bloco))
    for folha, pares in sorted(lente.BASELINE_G129.items()):
        for par in pares:
            motivo = (lente.ISENCOES_G129.get(folha) or {}).get(tuple(par))
            if not (str(motivo or "").strip()
                    and "png" in str(motivo).lower()):
                lados.append("par sem PNG conferido %s %r" % (folha, par))
    for folha, motivos in sorted(lente.ISENCOES_G129.items()):
        for par in motivos:
            if list(par) not in [list(p) for p in
                                 censo.get(folha, [])]:
                lados.append("isencao morta %s %r (par fora do vivo)"
                             % (folha, par))
    for entrada in lente.CORRIGIDOS_G129:
        if not (str(entrada.get("folha") or "").strip()
                and entrada.get("pares")
                and str(entrada.get("correcao") or "").strip()
                and "png" in str(entrada.get("png") or "").lower()):
            lados.append("corrigido sem folha/pares/correcao/PNG: %r"
                         % (entrada,))
            continue
        vivos = censo.get(entrada["folha"], [])
        voltaram = [p for p in entrada["pares"]
                    if list(p) in [list(v) for v in vivos]]
        if voltaram:
            lados.append("correcao perdeu o efeito em %s: %r de volta"
                         % (entrada["folha"], voltaram))
    assert not lados, "baseline G129 reprova:\n" + "\n".join(lados)


def _svg_duas_linhas(desloca_segunda=0):
    """Folha minima com dois rotulos; desloca_segunda empurra um sobre o outro."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" '
        'viewBox="0 0 400 200">'
        '<text x="100" y="100" font-size="12" text-anchor="middle">rotulo A</text>'
        '<text x="%d" y="100" font-size="12" text-anchor="middle">rotulo B</text>'
        "</svg>" % (300 + desloca_segunda))


def _universo_vazio():
    return {chave: [] for chave in lente.chaves_do_censo()}


_FOLHA_FIXA = "casa/drawings/unifilar.svg"


def test_03_vermelho_por_injecao_rotulo_empurrado_via_tmp_path(tmp_path):
    """Rotulo empurrado sobre outro vira par novo; o caso bom fica verde."""
    caminho = tmp_path / "folha.json"
    caminho.write_text(json.dumps({"bom": _svg_duas_linhas(0)}),
                       encoding="utf-8")
    base = dict(json.loads(caminho.read_text(encoding="utf-8")))
    universo = _universo_vazio()
    bom = lente.confere_censo(dict(universo), dict(universo), {})
    # G97: um assert so, com o bom e o injetado na mesma mensagem.
    lados = []
    if not (bom["OK"] and bom["pares_novos"] == {}):
        lados.append("caso bom devia fechar: %r" % (bom,))
    injetado = dict(universo)
    injetado[_FOLHA_FIXA] = lente.pares_de_svg(_svg_duas_linhas(-160))
    ruim = lente.confere_censo(injetado, dict(universo), {})
    if ruim["pares_novos"] != {_FOLHA_FIXA: [("rotulo A", "rotulo B")]} \
            or ruim["OK"]:
        lados.append("injecao devia acusar par novo: %r" % (ruim,))
    assert not lados, "injecao G129 reprova:\n" + "\n".join(lados)


def test_04_vermelho_sumido_morto_e_sem_motivo_via_tmp_path(tmp_path):
    """Par sumido, isencao morta e motivo apagado viram vermelho; bom verde."""
    caminho = tmp_path / "censo.json"
    caminho.write_text(json.dumps({"f": [["a", "b"]]}), encoding="utf-8")
    par = [tuple(p) for p in
           json.loads(caminho.read_text(encoding="utf-8"))["f"]]
    universo = _universo_vazio()
    base = dict(universo)
    base[_FOLHA_FIXA] = par
    bom = lente.confere_censo(dict(base), dict(base),
                              {_FOLHA_FIXA: {("a", "b"): "visto no PNG x.png"}})
    # G97: um assert so, com os quatro lados na mesma mensagem.
    lados = []
    if not bom["OK"]:
        lados.append("caso bom devia fechar: %r" % (bom,))
    sumido = lente.confere_censo(dict(universo), dict(base),
                                 {_FOLHA_FIXA: {("a", "b"): "visto no PNG x.png"}})
    if sumido["pares_sumidos"] != {_FOLHA_FIXA: [("a", "b")]} \
            or sumido["isencoes_mortas"] != {_FOLHA_FIXA: [("a", "b")]} \
            or sumido["OK"]:
        lados.append("sumido devia acusar nos dois sentidos: %r" % (sumido,))
    apagada = lente.confere_censo(dict(base), dict(base),
                                  {_FOLHA_FIXA: {("a", "b"): "   "}})
    if apagada["sem_triagem"] != {_FOLHA_FIXA: [("a", "b")]} \
            or apagada["OK"]:
        lados.append("motivo em branco e silencio, nao triagem: %r"
                     % (apagada,))
    sem = lente.confere_censo(dict(base), dict(base), {})
    if sem["sem_triagem"] != {_FOLHA_FIXA: [("a", "b")]} or sem["OK"]:
        lados.append("par vivo sem motivo devia acusar: %r" % (sem,))
    assert not lados, "injecao G129 reprova:\n" + "\n".join(lados)


def test_05_malformada_grita_e_instrumento_acusa():
    """None levanta; SVG malformado acusa em vez de passar."""
    # G97: um assert so, com os quatro lados na mesma mensagem.
    lados = []
    for rotulo, fn in (("atual-None",
                        lambda: lente.confere_censo(None)),
                       ("svg-None",
                        lambda: lente.pares_de_svg(None)),
                       ("par-unitario",
                        lambda: lente.confere_censo({"f": [("a",)]})),
                       ("baseline-lista",
                        lambda: lente.confere_censo({}, []))):
        try:
            fn()
            lados.append("%s devia levantar TypeError" % rotulo)
        except TypeError:
            pass
    mal = lente.pares_de_svg("<svg><text")
    if mal != [("svg-malformado", "")]:
        lados.append("malformado devia acusar: %r" % (mal,))
    ver = lente.confere_censo({"f": mal}, {"f": []}, {})
    if ver["pares_novos"] != {"f": [("svg-malformado", "")]} or ver["OK"]:
        lados.append("malformado devia ser par novo: %r" % (ver,))
    assert not lados, "malformada G129 reprova:\n" + "\n".join(lados)


def test_06_universo_ancorado_em_fontes_independentes():
    """O universo deriva das fontes vivas, nao do proprio resultado.

    casa+predio: chaves == artefatos SVG do manifesto da MESMA rodada que
    o G102 confronta (mapas _PRANCHA_ARQUIVO_* como vocabulario); galpao:
    cada fonte e o emissor que o config_de_spec da disciplina rasteriza
    (o modulo existe e expoe a funcao). Contagens literais travam o fato.
    """
    censo = _censo()
    import casa_residencial as casa
    import edificio_adapter as predio

    # G97: um assert so, com os cinco lados na mesma mensagem.
    lados = []
    chaves_casa = sorted(k for k in censo if k.startswith("casa/"))
    chaves_predio = sorted(k for k in censo if k.startswith("predio/"))
    chaves_galpao = sorted(k for k in censo if k.startswith("galpao/"))
    if len(chaves_casa) != 12:
        lados.append("casa com %d folhas (esperado 12 do manifesto): %r"
                     % (len(chaves_casa), chaves_casa))
    if len(chaves_predio) != 15:
        lados.append("predio com %d folhas (esperado 15 do manifesto): %r"
                     % (len(chaves_predio), chaves_predio))
    if len(chaves_galpao) != 8:
        lados.append("galpao com %d fontes (esperado 8): %r"
                     % (len(chaves_galpao), chaves_galpao))
    mapa_casa = set(casa._PRANCHA_ARQUIVO_CASA.values())
    mapa_predio = set(predio._PRANCHA_ARQUIVO.values())
    for chave in chaves_casa:
        nome = chave.split("/", 1)[1].split("/", 1)[1]
        if nome not in mapa_casa and nome not in (
                "quadro-ambientes.svg", "conferencia-nbr5410.svg"):
            lados.append("casa %r sem lastro no mapa nem em extra triado "
                         "(G102)" % chave)
    for chave in chaves_predio:
        nome = chave.split("/", 1)[1].split("/", 1)[1]
        if nome not in mapa_predio:
            lados.append("predio %r sem lastro no mapa" % chave)
    import desenho_hidraulica as dh
    import desenho_incendio as di
    import desenho_eletrico as de
    import desenho_concreto as dco
    import desenho_climatizacao as dcl

    esperadas = {"galpao/esquema-hidraulica.svg": (dh,
                                                  "esquema_hidraulica_svg"),
                 "galpao/planta-seguranca.svg": (di,
                                                 "planta_seguranca_svg"),
                 "galpao/esquema-climatizacao.svg": (
                     dcl, "esquema_climatizacao_svg"),
                 "galpao/diagrama-unifilar.svg": (de,
                                                  "diagrama_unifilar_svg"),
                 "galpao/quadro-cargas.svg": (de, "quadro_cargas_svg"),
                 "galpao/planta-eletrica.svg": (de, "planta_eletrica_svg"),
                 "galpao/prancha-armacao.svg": (dco, "prancha_armacao_svg"),
                 "galpao/planta-formas.svg": (dco, "planta_formas_svg")}
    if set(chaves_galpao) != set(esperadas):
        lados.append("fontes do galpao mudaram: %r"
                     % (sorted(set(chaves_galpao) ^ set(esperadas)),))
    for chave, (modulo, funcao) in sorted(esperadas.items()):
        if not callable(getattr(modulo, funcao, None)):
            lados.append("emissor sumiu: %s.%s (fonte de %s)"
                         % (modulo.__name__, funcao, chave))
    assert not lados, "fontes G129 reprovam:\n" + "\n".join(lados)
