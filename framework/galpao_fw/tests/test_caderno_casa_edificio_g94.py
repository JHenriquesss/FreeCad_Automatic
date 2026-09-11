"""G94 - caderno executivo em PDF para a casa e para o predio.

Cobre `caderno_casa_edificio`: svg_para_png(), montar_caderno_svg() (pura),
emitir_caderno_casa() e emitir_caderno_edificio() (hooks do project_loop).

Sobre as fixtures SVG: as folhas minimas abaixo sao CRAFTADAS (nao saem dos
emissores reais desenho_pavimento/desenho_concreto, que exigem estruturas
calculadas - pesado demais para um portao unitario). Cada uma passa por
`desenho_svg_base.confere_folha_svg` via parse XML (`ET.fromstring`), nunca
por substring (convencao 3: substring nao ve geometria). O Edge headless
continua sendo o renderizador do repo; aqui o fitz e' so a ponte SVG->PNG de
CI, e os testes conferem via fitz (texto + imagens por pagina).

Fonte independente (anti-tautologia, convencao 5): as contagens esperadas
vêm de `pacote_legal.indice_de_pranchas(disciplinas_pacote(...))`, nunca da
saida do proprio caderno. BASELINE_G94 congela os dois sentidos: o caso bom
fecha verde com contagens exatas; o defeito injetado (SVG apagado numa copia
em `tmp_path`, nunca na arvore viva - convencao 2) fica vermelho nomeando o
codigo. Cada teste coleta todos os lados e falha uma vez so (G97: nunca
asserts em sequencia onde o primeiro esconde os demais).
"""
import copy
import os
import sys
import xml.etree.ElementTree as ET

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import caderno_casa_edificio as caderno

fitz = pytest.importorskip("fitz")

# Resultado sintetico que promete o pacote sem telhado e sem alvenaria:
# casa -> arquitetura + concreto + hidraulica + eletrico = 14 codigos
# (3 AR + 4 CO + 3 HI + 4 EL); predio -> concreto + hidraulica + eletrico +
# coordenacao = 12 codigos (4 CO + 3 HI + 4 EL + 1 CD).
RESULTADO_CASA = {
    "arquitetura": {"totais": {"area_util_m2": 60.0}},
    "estrutura": {"fundacao": {"ok": True}},
    "hidraulica": {"ok": True},
    "eletrico": {"circuits": {"layout_validation": {}}},
}
RESULTADO_EDIFICIO = {
    "estrutura": {"fundacao": {"ok": True}},
    "instalacoes": {"eletrico": {"ok": True}, "hidraulica": {"ok": True}},
}

# Arquivos emitidos no caso bom (basenames do mapa real). Na casa o
# esquema-hidraulico.svg cobre PE-HI-01/02/03 (N:1, contrato G82): 8 arquivos
# viram 10 pranchas; 4 codigos viram declaracao. No predio 1:1: 9 arquivos,
# 9 pranchas, 3 declaracoes.
CASA_EMITIDOS = ("implantacao.svg", "planta-baixa.svg", "planta-formas.svg",
                 "armacao-vigas-pilares-casa.svg", "esquema-hidraulico.svg",
                 "unifilar.svg", "planta-eletrica.svg", "quadro-cargas.svg")
CASA_DECLARADOS = {
    "cortes-fachadas.svg":
        "not_available: niveis nao declarados (cota de soleira/terreno)",
    "detalhes-concreto-casa.svg":
        "not_available: sem emissor de detalhes de concreto nesta rodada",
    "fundacao-locacao-formas-casa.svg":
        "not_available: estrutura.fundacao sem folha de locacao emitida",
    "eletrica-infra-aterramento-casa.svg":
        "not_available: malha de aterramento e SPDA nao declarados",
}
ED_EMITIDOS = ("planta-formas-pavimento-tipo.svg",
               "armacao-vigas-pavimento-tipo.svg",
               "planta-laje-pavimento-tipo.svg",
               "fundacao-locacao-formas.svg",
               "hidraulica-agua-fria.svg", "hidraulica-esgoto-ventilacao.svg",
               "eletrica-unifilar-prumada.svg",
               "eletrica-planta-pavimento-tipo.svg",
               "coordenacao-federado.svg")
ED_DECLARADOS = {
    "hidraulica-pluvial.svg":
        "not_available: rede pluvial nao dimensionada nesta rodada",
    "eletrica-infra-aterramento.svg":
        "not_available: malha de aterramento nao declarada",
    "eletrica-qdc-quadros.svg":
        "not_available: quadro de cargas nao emitido nesta rodada",
}

BASELINE_G94 = {
    "casa_n_indice": 14, "casa_n_pranchas": 10, "casa_n_declaradas": 4,
    "ed_n_indice": 12, "ed_n_pranchas": 9, "ed_n_declaradas": 3,
}


def _folha_svg(codigo):
    """Folha SVG minima que passa em confere_folha_svg (parse, nao substring)."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1188" height="840"'
        ' viewBox="0 0 1188 840">'
        '<rect x="20" y="20" width="1148" height="800" fill="none"'
        ' stroke="black" stroke-width="2"/>'
        '<line x1="20" y1="120" x2="1168" y2="120" stroke="black"/>'
        '<text x="40" y="80" font-size="48">%s</text>'
        '<rect x="60" y="160" width="400" height="300" fill="none"'
        ' stroke="black"/>'
        '<circle cx="800" cy="400" r="120" fill="none" stroke="black"/>'
        '</svg>' % codigo)


def _escrever_desenhos(destino, arquivos_por_codigo):
    """Escreve os SVGs no diretorio drawings/ e devolve {basename: path}."""
    pasta = os.path.join(destino, "drawings")
    os.makedirs(pasta, exist_ok=True)
    saida = {}
    for base, codigo in sorted(arquivos_por_codigo.items()):
        texto = _folha_svg(codigo)
        ET.fromstring(texto)
        caminho = os.path.join(pasta, base)
        with open(caminho, "w", encoding="utf-8") as fh:
            fh.write(texto)
        saida[base] = caminho
    return saida


def _manifesto_desenhos(tipologia, destino, emitidos, declarados):
    """Manifesto no formato que o hook de drawings grava (casa: skipped dict;
    edificio: skipped lista de {prancha, motivo})."""
    import casa_residencial as casa_mod
    import edificio_adapter as ed_mod

    if tipologia == "casa":
        mapa = dict(casa_mod._PRANCHA_ARQUIVO_CASA)
    else:
        mapa = dict(ed_mod._PRANCHA_ARQUIVO)
    por_codigo = {}
    for codigo, base in mapa.items():
        if base in emitidos and base not in por_codigo.values():
            por_codigo[base] = codigo
    escritos = _escrever_desenhos(destino, por_codigo)
    artefatos = ["drawings/" + b for b in sorted(escritos)]
    if tipologia == "casa":
        skipped = dict(declarados)
    else:
        skipped = [{"prancha": k, "motivo": v}
                   for k, v in sorted(declarados.items())]
    return {"artifacts": [], "deliverables": {
        "drawings": {"status": "generated", "artifacts": artefatos,
                     "skipped": skipped}}}


def _indice_independente(tipologia, resultado):
    """Indice pela MESMA fonte do pacote legal (nunca pela saida do caderno)."""
    import pacote_legal as pl

    if tipologia == "casa":
        import gestao_casa as gg

        return pl.indice_de_pranchas(gg.disciplinas_pacote(resultado))
    import gestao_edificio as ge

    return pl.indice_de_pranchas(
        ge.disciplinas_pacote(resultado) + ["coordenacao"])


def _conferir_caderno(tipologia, resultado, manifesto, destino, baseline):
    """Coleta TODOS os lados do aceite G94 de uma vez (G97)."""
    import desenho_svg_base as base

    gaps = []
    cad = (manifesto.get("deliverables") or {}).get("caderno") or {}
    if cad.get("status") != "generated":
        return ["caderno status=%r detail=%r (esperado generated)"
                % (cad.get("status"), cad.get("detail"))]
    indice = _indice_independente(tipologia, resultado)
    if cad.get("n_indice") != len(indice):
        gaps.append("n_indice %r != len(indice independente) %d"
                    % (cad.get("n_indice"), len(indice)))
    soma = (cad.get("n_pranchas") or 0) + (cad.get("n_declaradas") or 0)
    if soma != len(indice):
        gaps.append("n_pranchas(%r)+n_declaradas(%r)=%d != len(indice) %d"
                    % (cad.get("n_pranchas"), cad.get("n_declaradas"), soma,
                       len(indice)))
    for chave in ("n_indice", "n_pranchas", "n_declaradas"):
        esperado = baseline[chave]
        if cad.get(chave) != esperado:
            gaps.append("%s %r != BASELINE_G94 %r"
                        % (chave, cad.get(chave), esperado))
    if cad.get("faltando"):
        gaps.append("faltando nao vazio no caso bom: %r" % (cad["faltando"],))
    if cad.get("OK") is not True:
        gaps.append("OK=%r no caso bom (esperado True)" % (cad.get("OK"),))
    artefatos = [a for a in (manifesto.get("artifacts") or [])
                 if a.get("kind") == "executive-dossier"]
    if not artefatos:
        gaps.append("nenhum artifact kind=executive-dossier no manifesto")
    pdf_nome = (cad.get("artifacts") or [None])[0]
    pdf = os.path.join(destino, pdf_nome) if pdf_nome else None
    if not pdf or not os.path.isfile(pdf):
        gaps.append("PDF %r nao saiu no disco (regra 6)" % (pdf,))
        return gaps
    try:
        with fitz.open(pdf) as doc:
            n_pag = doc.page_count
            textos = [p.get_text() for p in doc]
            imagens = [len(p.get_images()) for p in doc]
    except Exception as exc:
        return gaps + ["PDF nao reabre no fitz: %s" % exc]
    if cad.get("n_paginas") != n_pag:
        gaps.append("n_paginas %r != paginas reais %d"
                    % (cad.get("n_paginas"), n_pag))
    if n_pag < 3:
        gaps.append("PDF com %d paginas (esperado capa+indice+folhas)" % n_pag)
    corpo = textos[2:]
    n_img = imagens[2:]
    for folha in indice:
        codigo = folha["codigo"]
        pag = [t for t in corpo if codigo in t]
        if not pag:
            gaps.append("codigo %s sem pagina no PDF (evaporou)" % codigo)
    # carimbo + conteudo por pagina de prancha; motivo verbatim na declaracao
    for folha in indice:
        codigo = folha["codigo"]
        for t in corpo:
            if codigo not in t:
                continue
            for campo in (codigo, folha["titulo"], folha["disciplina"]):
                if campo not in t:
                    gaps.append("pagina %s sem carimbo %r" % (codigo, campo))
            break
    for base_nome, motivo in (CASA_DECLARADOS.items()
                              if tipologia == "casa"
                              else ED_DECLARADOS.items()):
        alvos = [t for t in corpo if motivo in t]
        if not alvos:
            gaps.append("declaracao de %s sem o motivo verbatim" % base_nome)
    # N:1 da casa: um arquivo, tres paginas de prancha com imagem
    if tipologia == "casa":
        n_hi = sum(1 for t, ni in zip(corpo, n_img)
                   if "PE-HI-" in t and ni > 0)
        if n_hi != 3:
            gaps.append("N:1 quebrado: %d paginas PE-HI-* com imagem "
                        "(esperado 3 de 1 arquivo)" % n_hi)
    # cada SVG escrito passa na guarda de folha (parse, convencao 3)
    for nome in sorted(os.listdir(os.path.join(destino, "drawings"))):
        with open(os.path.join(destino, "drawings", nome),
                  encoding="utf-8") as fh:
            rep = base.confere_folha_svg(fh.read())
        if not rep.get("ok"):
            gaps.append("guarda de folha reprova %s: %s"
                        % (nome, rep.get("motivo")))
    return gaps


def test_01_caderno_casa_verde_contagens_congeladas(tmp_path):
    destino = str(tmp_path / "run-casa")
    os.makedirs(destino, exist_ok=True)
    manifesto = _manifesto_desenhos("casa", destino, CASA_EMITIDOS,
                                    CASA_DECLARADOS)
    resultado = copy.deepcopy(RESULTADO_CASA)
    caderno.emitir_caderno_casa(manifesto, destino, {"slug": "casa-g94"},
                                None, resultado)
    gaps = _conferir_caderno(
        "casa", resultado, manifesto, destino,
        {"n_indice": BASELINE_G94["casa_n_indice"],
         "n_pranchas": BASELINE_G94["casa_n_pranchas"],
         "n_declaradas": BASELINE_G94["casa_n_declaradas"]})
    assert not gaps, ("G94 casa verde:\n%s"
                      % "\n".join("  - " + g for g in gaps))


def test_02_caderno_edificio_verde_contagens_congeladas(tmp_path):
    destino = str(tmp_path / "run-ed")
    os.makedirs(destino, exist_ok=True)
    manifesto = _manifesto_desenhos("edificio", destino, ED_EMITIDOS,
                                    ED_DECLARADOS)
    resultado = copy.deepcopy(RESULTADO_EDIFICIO)
    caderno.emitir_caderno_edificio(manifesto, destino,
                                    {"slug": "edificio-g94"}, None, resultado)
    gaps = _conferir_caderno(
        "edificio", resultado, manifesto, destino,
        {"n_indice": BASELINE_G94["ed_n_indice"],
         "n_pranchas": BASELINE_G94["ed_n_pranchas"],
         "n_declaradas": BASELINE_G94["ed_n_declaradas"]})
    assert not gaps, ("G94 edificio verde:\n%s"
                      % "\n".join("  - " + g for g in gaps))


def test_03_vermelho_por_injecao_folha_sem_arquivo_nem_motivo(tmp_path):
    """Defeito injetado em copia tmp_path: SVG apagado vira faltando com o
    codigo nomeado e OK=False; o caso bom ao lado continua verde."""
    destino = str(tmp_path / "run-inj")
    os.makedirs(destino, exist_ok=True)
    manifesto = _manifesto_desenhos("casa", destino, CASA_EMITIDOS,
                                    CASA_DECLARADOS)
    resultado = copy.deepcopy(RESULTADO_CASA)
    # injeta o defeito: apaga UM svg da copia (nunca a arvore viva) e tira o
    # artifact correspondente, sem escrever motivo (nem arquivo, nem triagem)
    vitima = os.path.join(destino, "drawings", "planta-baixa.svg")
    os.remove(vitima)
    d = manifesto["deliverables"]["drawings"]
    d["artifacts"] = [a for a in d["artifacts"]
                      if not a.endswith("planta-baixa.svg")]
    caderno.emitir_caderno_casa(manifesto, destino, {"slug": "casa-g94"},
                                None, copy.deepcopy(resultado))
    cad = manifesto["deliverables"]["caderno"]
    gaps = []
    if cad.get("OK") is not False:
        gaps.append("OK=%r com folha sem arquivo nem motivo (esperado False)"
                    % (cad.get("OK"),))
    if cad.get("faltando") != ["PE-AR-02"]:
        gaps.append("faltando=%r (esperado ['PE-AR-02'], o codigo vitima)"
                    % (cad.get("faltando"),))
    soma = (cad.get("n_pranchas") or 0) + (cad.get("n_declaradas") or 0)
    if soma + len(cad.get("faltando") or []) != cad.get("n_indice"):
        gaps.append("pranchas(%r)+declaradas(%r)+faltando(%r) != n_indice(%r)"
                    % (cad.get("n_pranchas"), cad.get("n_declaradas"),
                       cad.get("faltando"), cad.get("n_indice")))
    # caso bom puro continua verde ao lado (baseline nos dois sentidos)
    folhas_boas = [{"codigo": "PE-AR-01", "titulo": "Planta de implantacao",
                    "disciplina": "arquitetura",
                    "svg": os.path.join(destino, "drawings",
                                        "implantacao.svg"),
                    "motivo": None}]
    res_bom = caderno.montar_caderno_svg(
        folhas_boas, os.path.join(destino, "BOM.pdf"), "T", "P")
    if res_bom["OK"] is not True or res_bom["faltando"]:
        gaps.append("caso bom acusou faltando: %r" % (res_bom,))
    # folha com svg=None E motivo=None reprova direto na pura
    res_ruim = caderno.montar_caderno_svg(
        [{"codigo": "PE-XX-99", "titulo": "Folha fantasma",
          "disciplina": "aco", "svg": None, "motivo": None}],
        os.path.join(destino, "RUIM.pdf"), "T", "P")
    if res_ruim["OK"] is not False or res_ruim["faltando"] != ["PE-XX-99"]:
        gaps.append("folha sem svg nem motivo devia reprovar com o codigo: "
                    "%r" % (res_ruim,))
    assert not gaps, ("G94 vermelho por injecao:\n%s"
                      % "\n".join("  - " + g for g in gaps))


def test_04_hook_degrada_sem_drawings_e_fiacao_no_loop(tmp_path):
    """Sem drawings o caderno sai not_available nomeando o detalhe (nunca
    derruba a rodada); e a fiacao declara caderno por ultimo nos dois
    adaptadores, com hook proprio aceito pelo project_loop."""
    import project_loop as ploop

    gaps = []
    for fn, tipologia, resultado in (
            (caderno.emitir_caderno_casa, "casa",
             copy.deepcopy(RESULTADO_CASA)),
            (caderno.emitir_caderno_edificio, "edificio",
             copy.deepcopy(RESULTADO_EDIFICIO))):
        destino = str(tmp_path / ("run-sem-%s" % tipologia))
        os.makedirs(destino, exist_ok=True)
        manifesto = {"artifacts": [], "deliverables": {}}
        try:
            fn(manifesto, destino, {}, None, resultado)
        except Exception as exc:
            gaps.append("%s levantou sem drawings: %s" % (tipologia, exc))
            continue
        cad = (manifesto.get("deliverables") or {}).get("caderno") or {}
        if cad.get("status") != "not_available":
            gaps.append("%s sem drawings: status=%r (esperado "
                        "not_available)" % (tipologia, cad.get("status")))
        elif "drawings" not in str(cad.get("detail", "")):
            gaps.append("%s sem drawings: detalhe nao nomeia drawings: %r"
                        % (tipologia, cad.get("detail")))
    import casa_residencial as casa_mod
    import edificio_adapter as ed_mod
    from builtin_adapters import register_builtin_adapters

    register_builtin_adapters()          # levanta se hook fora do nucleo
    for mod, nome in ((casa_mod, "casa-residencial"),
                      (ed_mod, "edificio-multipavimento")):
        if mod.DELIVERABLES[-1] != "caderno":
            gaps.append("%s: caderno nao e o ultimo DELIVERABLES: %r"
                        % (nome, mod.DELIVERABLES))
        hooks = ploop._PROJECT_HOOKS.get(nome) or {}
        if "caderno" not in hooks:
            gaps.append("%s: hook caderno ausente: %s"
                        % (nome, sorted(hooks)))
        extras = ploop._PROJECT_EXTRA_DELIVERABLES.get(nome) or []
        if not extras or extras[-1] != "caderno":
            gaps.append("%s: caderno nao roda por ultimo nos extras: %r"
                        % (nome, extras))
    assert not gaps, ("G94 degradacao + fiacao:\n%s"
                      % "\n".join("  - " + g for g in gaps))
