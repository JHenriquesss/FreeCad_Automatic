"""G128 - a declaracao da edicao chega as tres tipologias.

Medido (G125): o G123 fiou a chave `norma_6118_edicao` so no galpao - casa e
predio carimbavam o parametro ausente; as tres tipologias chamavam
`gerar_pendencias` sem `edicao`; o caderno escrevia "NBR 6118" sem edicao
(4x na casa, 4x no predio).

Entregue:
  1. CARIMBO casa/predio: desenho_pavimento + desenho_fundacao_edificio +
     desenho_concreto (laje) ganham `edicao=None` (ausente = hoje, 2014
     declarado); os hooks passam a declarada (fonte unica, sem literal).
  2. COMPAT x3: os 3 adapters passam a declarada a `gerar_pendencias`, que
     carimba `edicao_6118` em cada pendencia; o galpao repassa ainda ao
     calculo do concreto (o normalize nao a carregava ao turnkey).
  3. CADERNO: gerar_caderno/markdown/caderno_de_turnkey ganham `edicao`
     (a "NBR 6118" sai com a da conta + secao de declaracao, sempre);
     pacote de casa/predio recebe o spec (o do galpao, o projeto declarado).
  4. PORTAO (test_01/02/03): rodada real das 3 tipologias x 2 chaves.
  5. INJECAO (test_04/05, tmp_path, nunca o repo): folha 2014 com chave
     2023+Em1 reprova no confronto; o furo 125 so muda com a chave.
  6. BASELINE (test_06, nos dois sentidos): defaults byte-identicos, 19
     usos, 2 pontos intactos (8.2.5 fora, G123).

O que este goal NAO faz: virar a chave em projeto nenhum do repo (a
injecao e em copia na memoria + tmp_path); migrar a 8.2.5 (segue 2014
declarado, G123); implementar verificacoes novas.
"""
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, HERE)

import edicao_nbr6118_g123 as lente


def _rodada(nome, tmp_path, edicao=None, opcoes=None):
    """Roda a tipologia de verdade (spec persistido, inalterado) em tmp_path.

    `edicao`: None (chave ausente, hoje) ou '2023+Em1' (injetada NA COPIA
    em memoria, nunca no repo). Devolve (manifesto, destino)."""
    import test_indice_disco_rodada_g102 as g102
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    spec = g102._spec(nome)
    assert "norma_6118_edicao" not in spec, \
        "o repo nao declara a chave (Nao fazer do G128)"
    if edicao is not None:
        spec["norma_6118_edicao"] = edicao
    destino = str(tmp_path / ("run-%s-%s" % (nome, edicao or "ausente")))
    opcoes = dict(opcoes) if opcoes is not None \
        else dict(g102._OPCOES[nome])
    return run_project(spec, destino, opcoes), destino


def _confronto_folha_edicao(texto, edicao_esperada):
    """A folha declara a edicao que a conta usou? (portao do aceite).

    OK so quando ha declaracao e ela e a esperada ('ambas' = citacao
    obsoleta junto do carimbo, reprova). Sem declaracao reprova nomeando
    (o mesmo molde do confere_peca do G123)."""
    c = lente.contem_declaracao(texto)
    if not c["tem"]:
        return {"OK": False,
                "motivo": "folha sem declaracao da edicao (exigido G128)"}
    if c["edicao"] != edicao_esperada:
        return {"OK": False,
                "motivo": "folha declara %s com o projeto em %s"
                          % (c["edicao"], edicao_esperada)}
    return {"OK": True, "motivo": ""}


def _pecas_concreto(nome, destino):
    """{arquivo: texto} das folhas PE-CO emitidas na rodada."""
    if nome == "casa":
        import casa_residencial as adaptador
        mapa = dict(adaptador._PRANCHA_ARQUIVO_CASA)
    elif nome == "predio":
        import edificio_adapter as adaptador
        mapa = dict(adaptador._PRANCHA_ARQUIVO)
    else:
        mapa = {}
    pecas = {}
    faltando = []
    for codigo, arquivo in sorted(mapa.items()):
        if not codigo.startswith("PE-CO-"):
            continue
        caminho = os.path.join(destino, "drawings", arquivo)
        if not os.path.isfile(caminho):
            faltando.append("%s (%s) nao saiu" % (codigo, arquivo))
            continue
        with open(caminho, encoding="utf-8") as fh:
            pecas[arquivo] = fh.read()
    return pecas, faltando


def _confere_rodada(nome, destino, edicao_esperada, com_desenhos=True):
    """Um assert so por rodada: folhas + pacote + caderno + pendencias."""
    quebras = []
    if com_desenhos:
        pecas, faltando = _pecas_concreto(nome, destino)
        quebras.extend(faltando)
        if nome == "casa" and len(pecas) != 4:
            quebras.append("folhas PE-CO da casa=%d, esperado 4" % len(pecas))
        if nome == "predio" and len(pecas) != 4:
            quebras.append("folhas PE-CO do predio=%d, esperado 4"
                           % len(pecas))
        for arquivo, texto in sorted(pecas.items()):
            r = _confronto_folha_edicao(texto, edicao_esperada)
            if not r["OK"]:
                quebras.append("%s: %s" % (arquivo, r["motivo"]))
    for doc in ("pacote-legal.md", "caderno-encargos.md"):
        caminho = os.path.join(destino, "documentos", doc)
        if not os.path.isfile(caminho):
            quebras.append("%s nao saiu" % doc)
            continue
        with open(caminho, encoding="utf-8") as fh:
            texto = fh.read()
        r = _confronto_folha_edicao(texto, edicao_esperada)
        if not r["OK"]:
            quebras.append("%s: %s" % (doc, r["motivo"]))
        if edicao_esperada == "2014" and "nao declarada" not in texto:
            quebras.append("%s esconde a ausencia (sem 'nao declarada')"
                           % doc)
    caminho = os.path.join(destino, "coordination", "pendencias.json")
    if os.path.isfile(caminho):
        with open(caminho, encoding="utf-8") as fh:
            pends = json.load(fh)
        outras = sorted({p.get("edicao_6118") for p in pends
                         if p.get("edicao_6118") != edicao_esperada})
        if outras:
            quebras.append("pendencias com edicao %r (esperado %s)"
                           % (outras, edicao_esperada))
    return quebras


def test_01_rodada_casa_ausente_e_2023(tmp_path):
    """Casa de verdade x 2 chaves: toda peca de concreto declara a da conta."""
    quebras = []
    for chave, esperada in ((None, "2014"), ("2023+Em1", "2023+Em1")):
        _man, destino = _rodada("casa", tmp_path, edicao=chave)
        quebras.extend("[casa %s] %s" % (chave or "ausente", q)
                       for q in _confere_rodada("casa", destino, esperada))
    assert not quebras, "G128 casa:\n" + "\n".join(quebras)


def test_02_rodada_predio_ausente_e_2023(tmp_path):
    """Predio de verdade x 2 chaves: toda peca de concreto declara a da conta."""
    quebras = []
    for chave, esperada in ((None, "2014"), ("2023+Em1", "2023+Em1")):
        _man, destino = _rodada("predio", tmp_path, edicao=chave)
        quebras.extend("[predio %s] %s" % (chave or "ausente", q)
                       for q in _confere_rodada("predio", destino, esperada))
    assert not quebras, "G128 predio:\n" + "\n".join(quebras)


def test_03_rodada_galpao_ausente_e_2023(tmp_path):
    """Galpao de verdade x 2 chaves: calculo + compat + caderno + pacote.

    Sem 2D (o emissor de desenho do galpao e do G123, ja coberto la com
    2D; aqui valem as pranchas SVG puro-Python + os documentos). A chave
    chega ao calculo do concreto (o normalize nao a carregava ao turnkey):
    com 2023+Em1 as folhas do calculo declaram 2023+Em1."""
    quebras = []
    for chave, esperada in ((None, "2014"), ("2023+Em1", "2023+Em1")):
        _man, destino = _rodada("galpao", tmp_path, edicao=chave,
                                opcoes={"generate_ifc": False,
                                        "generate_2d": False})
        for arquivo in ("concreto-armacao.svg", "concreto-formas.svg"):
            caminho = os.path.join(destino, "drawings-svg", arquivo)
            if not os.path.isfile(caminho):
                quebras.append("[galpao %s] %s nao saiu"
                               % (chave or "ausente", arquivo))
                continue
            with open(caminho, encoding="utf-8") as fh:
                r = _confronto_folha_edicao(fh.read(), esperada)
            if not r["OK"]:
                quebras.append("[galpao %s] %s: %s"
                               % (chave or "ausente", arquivo, r["motivo"]))
        quebras.extend("[galpao %s] %s" % (chave or "ausente", q)
                       for q in _confere_rodada("galpao", destino, esperada,
                                                com_desenhos=False))
    assert not quebras, "G128 galpao:\n" + "\n".join(quebras)


def _clash_furo_125(forma):
    hint = {"direcao": "transversal", "d_furo_mm": 125.0,
            "h_viga_mm": 600.0, "dist_apoio_mm": 1300.0,
            "zona_tracao": True, "dist_face_mm": 60.0,
            "cobrimento_mm": 25.0, "furo_unico": True,
            "armadura_seccionada": False}
    if forma is not None:
        hint["forma_furo"] = forma
    clash = {"a": "V1", "b": "T1",
             "disciplinas": "concretoxhidraulica", "tipos": "BeamxPipe",
             "vol_mm3": 1e5, "esperado": False}
    return {"clashes": [clash]}, {("V1", "T1", "BeamxPipe"): hint}


def test_04_furo_125_muda_so_com_a_chave():
    """O circular de 125 mm muda de veredito com a chave, e so com ela."""
    import compatibilizacao as cp

    quebras = []
    rep, hints = _clash_furo_125("circular")
    sem = cp.gerar_pendencias(rep, cruzamentos=hints)[0]
    com = cp.gerar_pendencias(rep, cruzamentos=hints,
                              edicao="2023+Em1")[0]
    if sem["veredito"] != "a_confirmar":
        quebras.append("circular 125 sem chave=%r, esperado a_confirmar"
                       % (sem["veredito"],))
    if com["veredito"] != "admissivel":
        quebras.append("circular 125 com 2023+Em1=%r, esperado admissivel"
                       % (com["veredito"],))
    if sem["edicao_6118"] != "2014" or com["edicao_6118"] != "2023+Em1":
        quebras.append("carimbo da pendencia: %r/%r"
                       % (sem["edicao_6118"], com["edicao_6118"]))
    # So com ela: retangular e sem-forma ficam em 12 cm mesmo virada.
    for forma in ("retangular", None):
        rep_f, hints_f = _clash_furo_125(forma)
        r = cp.gerar_pendencias(rep_f, cruzamentos=hints_f,
                                edicao="2023+Em1")[0]
        if r["veredito"] != "a_confirmar":
            quebras.append("forma %r com 2023+Em1=%r, esperado a_confirmar"
                           % (forma, r["veredito"]))
    # Sem hint nao ha furo (o tipo de peca nao classifica): segue conflito.
    rep_s = {"clashes": [{"a": "V1", "b": "T1",
                          "disciplinas": "concretoxhidraulica",
                          "tipos": "BeamxPipe", "vol_mm3": 1e5,
                          "esperado": False}]}
    r_s = cp.gerar_pendencias(rep_s, edicao="2023+Em1")[0]
    if r_s["categoria"] != "conflito":
        quebras.append("sem hint virou %r, esperado conflito"
                       % (r_s["categoria"],))
    assert not quebras, "G128 furo 125:\n" + "\n".join(quebras)


def test_05_vermelho_por_injecao_em_tmp_path(tmp_path):
    """tmp_path, nunca o repo: 2014 com chave 2023 reprova; sem declaracao
    reprova; edicao invalida levanta em toda porta nova."""
    quebras = []
    # Folha 2023+Em1 adulterada para 2014: o confronto acusa nomeando.
    boa = lente.carimbo_edicao("2023+Em1")
    adulterada = boa.replace(lente.DECLARACAO_2023_EM1,
                             lente.DECLARACAO_2014)
    r = _confronto_folha_edicao(adulterada, "2023+Em1")
    if r["OK"]:
        quebras.append("folha 2014 com chave 2023 devia reprovar")
    elif "2014" not in r["motivo"] or "2023+Em1" not in r["motivo"]:
        quebras.append("motivo nao nomeia os dois lados: %r" % (r["motivo"],))
    # A intacta passa; a sem declaracao reprova.
    if not _confronto_folha_edicao(boa, "2023+Em1")["OK"]:
        quebras.append("folha intacta devia passar")
    if _confronto_folha_edicao("concreto sem norma", "2014")["OK"]:
        quebras.append("folha sem declaracao devia reprovar")
    # "NBR 6118" sem edicao no caderno reprova (a ausencia que o G128 achou).
    if lente.contem_declaracao("**Normas:** NBR 6118, NBR 9062")["tem"]:
        quebras.append("caderno sem edicao devia reprovar no portao")
    # Invalida levanta em toda porta nova (nunca vira edicao em silencio).
    import compatibilizacao as cp
    import caderno_encargos as ce
    import desenho_pavimento as dp

    rep = {"clashes": []}
    for fn in (lambda: lente.edicao_de_normalized(
                   {"raw_spec": {"norma_6118_edicao": "2015"}}),
               lambda: cp.gerar_pendencias(rep, edicao="2015"),
               lambda: ce.gerar_caderno(["concreto"], edicao="2015"),
               lambda: dp.prancha_armacao_pilares_svg({}, edicao="2015")):
        try:
            fn()
            quebras.append("edicao invalida devia levantar: %r" % (fn,))
        except ValueError:
            pass
    if not tmp_path.is_dir():
        quebras.append("tmp_path sumiu")
    assert not quebras, "G128 injecao:\n" + "\n".join(quebras)


def test_06_baseline_nos_dois_sentidos():
    """Defaults byte-identicos; 19 usos; 2 pontos intactos (8.2.5 fora)."""
    import caderno_encargos as ce
    import compatibilizacao as cp
    import desenho_fundacao_edificio as dfe
    import desenho_pavimento as dp

    quebras = []
    # Sem o parametro, o comportamento e o de hoje...
    if dp._sufixo_edicao() != dp._sufixo_edicao(None) != " (NBR 6118:2014)":
        quebras.append("sufixo default mudou: %r" % (dp._sufixo_edicao(),))
    if dfe._sufixo_edicao() != " (NBR 6118:2014)":
        quebras.append("sufixo fundacao mudou: %r" % (dfe._sufixo_edicao(),))
    if dp._subtitulo_pilares() != dp._SUBTITULO_PILARES:
        quebras.append("subtitulo default mudou")
    if "NBR 6118:2023 + Emenda 1:2026" not in dp._subtitulo_pilares(
            "2023+Em1"):
        quebras.append("subtitulo 2023 sem Emenda 1")
    if [n for n in ce.gerar_caderno()["normas_referenciadas"]
            if n == "NBR 6118"]:
        quebras.append("caderno default ainda tem NBR 6118 sem edicao")
    md = ce.markdown(ce.gerar_caderno(["concreto", "fundacao", "piso"]))
    if [l for l in md.splitlines()
            if "NBR 6118" in l and "NBR 6118:" not in l]:
        quebras.append("caderno default com 6118 sem edicao no markdown")
    p = cp.gerar_pendencias({"clashes": []})
    if p != []:
        quebras.append("pendencias vazias mudaram: %r" % (p,))
    # ...e a peca diz qual e: 19 usos, 2 pontos, 2 edicoes.
    esp = {"edicao_nbr6118_g123.py", "premoldado_nbr9062.py",
           "compatibilizacao.py", "desenho_concreto.py",
           "techdraw_concreto.py", "pacote_legal.py", "relatorio_calculo.py",
           "executivo_concreto.py", "projeto_spec.py", "galpao_concreto.py",
           "rodar_galpao.py", "entregaveis_projeto.py",
           "desenho_pavimento.py", "desenho_fundacao_edificio.py",
           "casa_residencial.py", "edificio_adapter.py",
           "galpao_adapter.py", "desenho_casa_residencial.py",
           "caderno_encargos.py"}
    if set(lente.USO_ESPERADO) != esp:
        quebras.append("USO_ESPERADO mudou: so no conhecido %r, so no vivo %r"
                       % (sorted(esp - set(lente.USO_ESPERADO)),
                          sorted(set(lente.USO_ESPERADO) - esp)))
    uso = lente.confere_uso_edicao()
    if not uso["OK"]:
        quebras.append("uso real fora do baseline: %r" % (uso,))
    if tuple(lente.MODULOS_COM_TROCA) != (("premoldado_nbr9062", "12.3.3"),
                                          ("compatibilizacao", "13.2.5.1")):
        quebras.append("MODULOS_COM_TROCA mudou: %r"
                       % (lente.MODULOS_COM_TROCA,))
    if tuple(lente.EDICOES_VALIDAS) != ("2014", "2023+Em1"):
        quebras.append("EDICOES_VALIDAS mudou: %r" % (lente.EDICOES_VALIDAS,))
    assert not quebras, "G128 baseline:\n" + "\n".join(quebras)


def test_07_pacote_e_caderno_lem_spec():
    """O spec declarado chega ao pacote (3 tipologias) e ao caderno."""
    import pacote_legal as pl

    quebras = []
    pac = pl.gerar_pacote(["concreto"],
                          spec={"norma_6118_edicao": "2023+Em1"})
    if pac["edicao_6118"] != "2023+Em1":
        quebras.append("pacote com spec 2023: %r" % (pac["edicao_6118"],))
    md = pl.markdown(pac)
    if "NBR 6118:2023 + Emenda 1:2026" not in md:
        quebras.append("pacote 2023 sem carimbo no markdown")
    pac0 = pl.gerar_pacote(["concreto"], spec={})
    if "nao declarada" not in pl.markdown(pac0):
        quebras.append("pacote sem chave esconde a ausencia")
    try:
        pl.gerar_pacote(["concreto"], spec={"norma_6118_edicao": "2015"})
        quebras.append("pacote com spec invalido devia levantar")
    except ValueError:
        pass
    # edicao_de_normalized: raw vence turnkey; ausente = None; lixo = None.
    if lente.edicao_de_normalized(
            {"raw_spec": {"norma_6118_edicao": "2023+Em1"},
             "turnkey_spec": {}}) != "2023+Em1":
        quebras.append("normalized nao resolveu do raw_spec")
    if lente.edicao_de_normalized(
            {"raw_spec": {}, "turnkey_spec": {"edicao_6118": "2014"}}) \
            != "2014":
        quebras.append("normalized nao caiu no turnkey_spec")
    if lente.edicao_de_normalized({}) is not None:
        quebras.append("normalized vazio devia dar None")
    if lente.edicao_de_normalized(None) is not None:
        quebras.append("normalized None devia dar None")
    # O caderno via camada de entrega resolve do normalized.
    import caderno_encargos as ce
    cad = ce.caderno_de_turnkey({"executadas": ["concreto"],
                                 "disciplinas": {
                                     "concreto": {"raw": {}}}},
                                edicao="2023+Em1")
    if "NBR 6118:2023 + Emenda 1:2026" not in ce.markdown(cad):
        quebras.append("caderno_de_turnkey 2023 sem carimbo")
    assert not quebras, "G128 pacote/caderno:\n" + "\n".join(quebras)


def test_08_nenhum_projeto_do_repo_virou_a_chave():
    """Nao fazer do goal: nenhum project-spec.json declara a chave."""
    import glob as _glob

    quebras = []
    for caminho in _glob.glob(os.path.join(
            GALPAO, "..", "..", "projects", "*", "project-spec.json")):
        with open(caminho, encoding="utf-8") as fh:
            spec = json.load(fh)
        for chave in ("norma_6118_edicao", "edicao_6118", "edicao"):
            if spec.get(chave) not in (None, ""):
                quebras.append("%s declara %s=%r" % (
                    caminho, chave, spec.get(chave)))
    # Nem o material de apoio: a 2023 nao entra em spec de teste do repo.
    if not quebras and not _glob.glob(os.path.join(
            GALPAO, "..", "..", "projects", "*", "project-spec.json")):
        quebras.append("nenhum project-spec.json achado (caminho errado?)")
    assert not quebras, "G128 chave virada no repo:\n" + "\n".join(quebras)


def test_09_topo_x_payload_divergentes_falham_com_motivo(tmp_path):
    """G131 (auditoria do G128), medido em rodada real do galpao: com
    2023+Em1 no topo do project-spec e 2014 no payload concreto, o payload
    vencia em silencio - pacote, caderno e pendencias diziam 2023+Em1, a
    conta e as 2 folhas do calculo diziam 2014. Um assert so: a divergencia
    falha a rodada com o motivo escrito e sem pacote; a MESMA edicao nos dois
    lugares nao e conflito (o pacote sai)."""
    import copy

    import test_indice_disco_rodada_g102 as g102
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    nl = chr(10)
    quebras = []
    spec = copy.deepcopy(g102._spec("galpao"))
    spec["norma_6118_edicao"] = "2023+Em1"
    spec["turnkey"]["concreto"]["norma_6118_edicao"] = "2014"
    destino = str(tmp_path / "galpao-edicao-conflito")
    run_project(spec, destino, {"generate_ifc": False, "generate_2d": False})
    with open(os.path.join(destino, "project-run.json"), encoding="utf-8") as fh:
        registro = fh.read()
    if "diverge do payload concreto" not in registro:
        quebras.append("conflito de edicao nao ficou escrito no registro")
    if os.path.isfile(os.path.join(destino, "documentos", "pacote-legal.md")):
        quebras.append("conflito de edicao ainda emitiu pacote")
    spec = copy.deepcopy(g102._spec("galpao"))
    spec["norma_6118_edicao"] = "2023+Em1"
    spec["turnkey"]["concreto"]["edicao"] = "2023+Em1"
    destino = str(tmp_path / "galpao-edicao-igual")
    run_project(spec, destino, {"generate_ifc": False, "generate_2d": False})
    with open(os.path.join(destino, "project-run.json"), encoding="utf-8") as fh:
        registro = fh.read()
    if "diverge do payload concreto" in registro:
        quebras.append("mesma edicao nos dois lugares virou conflito")
    caminho = os.path.join(destino, "documentos", "pacote-legal.md")
    if not os.path.isfile(caminho):
        quebras.append("mesma edicao nos dois lugares nao emitiu pacote")
    else:
        with open(caminho, encoding="utf-8") as fh:
            r = _confronto_folha_edicao(fh.read(), "2023+Em1")
        if not r["OK"]:
            quebras.append("pacote com a mesma edicao: %s" % r["motivo"])
    assert not quebras, "G131 edicao topo x payload:" + nl + nl.join(quebras)
