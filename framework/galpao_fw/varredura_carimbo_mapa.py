# ============================================================================
# varredura_carimbo_mapa.py - G112: O CARIMBO USA UM CODIGO, O INDICE OUTRO.
# SCRIPT AVULSO: ferramenta permanente rodada a mao/CI (python
# varredura_carimbo_mapa.py) e pelo teste-guarda
# tests/test_carimbo_mapa_g112.py. Nao e importada por nenhum
# orquestrador do Loop - declarada em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de varredura_asserts_sequencia.
#
# O que foi MEDIDO (G106, 2026-09-11; enderecos verificados na entrega G112):
#   - o carimbo das pranchas do galpao diz PE-HID-01/02, PE-INC-01/02/03
#     (G138: +PE-INC-03 em techdraw_incendio._pr_detalhes), PE-CLI-01/02
#     (techdraw_hidraulica.py:30,47-48,
#     techdraw_incendio.py:46,68,84, techdraw_climatizacao.py:25,41-42, e a
#     rota SVG do G104 em prancha_svg_direta.PRANCHAS, :50-54);
#   - o indice (pacote_legal._PRANCHAS, :46,47-49,54) promete PE-HI-01..03,
#     PE-IN-01..03, PE-CL-01. Nao e so o prefixo: PE-HI-02 no indice e
#     "Esgoto/ventilacao", e PE-HID-02 no carimbo e o quadro de
#     dimensionamento - o mesmo numero designa folhas diferentes;
#   - o NAO-medido do G106, medido na entrega G112 via AST (ast.parse, nunca
#     substring): aco (techdraw_exec.py:662,695,740,807,861,933,1109,1434,
#     1518,1669,1737 - _nova_prancha "PE01_COBERTURA".."PE16_MONTAGEM" com
#     carimbo "PE-01".."PE-16"; PE15_DET_BLOCO, :1008, carimba "-" e nao
#     conta) contra PE-ES-01..03 do indice; concreto do galpao
#     (techdraw_concreto.py - "PE01_FORMAS"/"PE02_PORTICO"/
#     "PE03_QUADROS"/"PE04_LOCACAO_FUNDACAO" com carimbo
#     "PE-01"/"PE-02"/"PE-03"/"PE-04"; G140: a locacao ganha emissor
#     ligado); mezanino (techdraw_mezanino.py - "MZ01_MEZANINO" com
#     carimbo "MZ-01"; G146: formas + armacao via desenho_pavimento
#     adaptado, cobertura 1:1 na tabela); eletrico
#     (techdraw_eletrico.py:46,66,88,110 - "PE01_UNIFILAR".."PE04_QUADROS"
#     com carimbo "PE-EL-01".."PE-EL-04"); coordenacao
#     (techdraw_coordenacao.py:43,60 - "COORD01_PLANTA"/"COORD02_CLASH" com
#     carimbo "PE-COORD-01"/"PE-COORD-02"). Arquivo emitido = nome da pagina
#     + ".pdf". Cada par esta escrito no cabecalho do teste-guarda.
#
# Maquina: funcao pura, sem AST e sem FreeCAD. Recebe o mapa da tipologia
# ({codigo do indice: arquivo}) e os carimbos por arquivo emitido
# ({basename do arquivo: [codigos no carimbo daquela folha]}), inverte o
# mapa para arquivo->{codigos} e cobra que todo carimbo de um arquivo
# pertenca ao conjunto que o mapa atribui aquele arquivo. O teste-guarda
# aplica a funcao as tres tipologias com os mapas vivos
# (galpao_adapter._PRANCHA_ARQUIVO_GALPAO, casa_residencial.
# _PRANCHA_ARQUIVO_CASA, edificio_adapter._PRANCHA_ARQUIVO) e os carimbos
# extraidos vivos (AST sobre os techdraw_* + PRANCHAS/ARQUIVOS de
# prancha_svg_direta).
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - conteudo da folha (geometria, legibilidade): e de confere_folha_svg
#     e do censo do G77, nao desta lente (codigo no carimbo nao e desenho);
#   - arquivos sem literal de carimbo extraivel (ex. INC04_ESCADA no mapa
#     do galpao; todas as .svg da casa
#     e do predio, cujos emissores desenho_* nao publicam literal de
#     carimbo): saem em `sem_carimbo_informativo` e NAO afetam o OK -
#     ausencia declarada, nunca default silencioso (nao-coverture
#     declarada, nao passe livre). G138: INC03_DETALHES tem literal
#     extraivel (techdraw_incendio._pr_detalhes) e cobertura 1:1 na tabela,
#     logo nao cai aqui; G140: PE04_LOCACAO_FUNDACAO tem literal
#     extraivel (techdraw_concreto._pr_locacao) e cobertura 1:1 na tabela,
#     logo nao cai aqui; G146: MZ01_MEZANINO tem literal extraivel
#     (techdraw_mezanino._pr_mezanino) e cobertura 1:1 na tabela, logo
#     nao cai aqui;
#   - indice x disco (arquivo emitido ou nao): e da lente do G91/G102,
#     nao desta (carimbo x mapa, nao promessa x arquivo).
#
# Veredito G112 (segundo ramo do goal: numeracao propria + tabela): os
# carimbos ficam como estao - o executivo numera as folhas por arquivo de
# producao (PE-HID/PE-INC/PE-CLI para esquema+quadro; PE-01..PE-16 na
# sequencia do aco; PE-01..PE-04 na sequencia do concreto; PE-COORD na
# coordenacao) enquanto o indice numera por disciplina
# (PE-HI/PE-IN/PE-CL/PE-ES/PE-CO/PE-EL/PE-CD). As numeracoes diferem porque
# (a) um arquivo de esquema cobre N codigos do indice (HID01_ESQUEMA.pdf
# cobre PE-HI-01/02/03; INC01_PLANTA.pdf cobre PE-IN-01 (PE-IN-02 sai em
# INC03_DETALHES.pdf, G138; PE-IN-03 sem emissor); (b) as folhas de quadro
# (HID02_QUADRO.pdf com PE-HID-02, INC02_RESUMO.pdf, CLI02_QUADRO.pdf)
# nao tem codigo proprio no indice - PE-HID-02 colide em numero
# com PE-HI-02 "Esgoto/ventilacao" mas e outra folha; (c) o aco emite 17
# folhas contra 3 codigos PE-ES e o carimbo PE-01 esta em dois arquivos
# distintos (PE01_FORMAS.pdf do concreto e PE01_COBERTURA.pdf do aco);
# (d) a coordenacao emite 2 folhas contra 1 codigo PE-CD. Carimbar um unico
# codigo do indice nessas folhas afirmaria uma cobertura que a folha nao tem
# (convencao 6: a folha diz o que desenha) - por isso a numeracao propria
# permanece, e a CORRESPONDENCIA_G112 abaixo diz ao cliente que folha do
# executivo responde por que codigo(s) do indice. G137: o aco passa a 17
# codigos PE-ES (1:1 com as pranchas emitidas); o carimbo de producao
# (PE-01..PE-16) segue distinto do codigo do indice (PE-ES-..), logo a
# tabela e as isencoes permanecem. A tabela viaja no
# pacote-legal.md do galpao (pacote_legal.markdown com correspondencia, via
# entregaveis_projeto.emitir_pacote_legal); o portao fica verde COM as
# isencoes escritas (ISENCOES_CARIMBO_MAPA), nunca enfraquecendo a lente.
# ============================================================================
"""Varredura G112: codigo do carimbo <-> conjunto de codigos do mapa, funcao pura."""

from __future__ import annotations

import pathlib

GALPAO = pathlib.Path(__file__).resolve().parent


# RAZAO_NUMERACAO_PROPRIA_G112 e CORRESPONDENCIA_G112: a razao e a tabela que
# o cliente recebe. UMA fonte so, na producao
# (pacote_legal.CORRESPONDENCIA_NUMERACAO_GALPAO). Ate a auditoria G113 a
# tabela vivia AQUI e entregaveis_projeto carregava uma copia de ~150 linhas
# guardada por teste de igualdade: duas listas para divergir, com a canonica
# no lugar que o cliente nao le. Script avulso pode importar a producao; o
# contrario e que nao pode (tests/test_alcancabilidade.py).
from pacote_legal import CORRESPONDENCIA_NUMERACAO_GALPAO as _PACOTE_G112

RAZAO_NUMERACAO_PROPRIA_G112 = _PACOTE_G112["intro"]
CORRESPONDENCIA_G112 = _PACOTE_G112["entradas"]


# ISENCOES_CARIMBO_MAPA: os 23 arquivos da tabela, com o motivo escrito
# (molde G103 de varredura_disciplina_prancha.ISENCOES_DISCIPLINA_PRANCHA:
# {arquivo: motivo}; motivo vazio/em branco e silencio, nao triagem).
# Derivada da tabela - uma fonte so, nunca duas listas para divergir.
ISENCOES_CARIMBO_MAPA = {e["arquivo"]: e["motivo"]
                         for e in CORRESPONDENCIA_G112}


def _isencoes_validas(isencoes):
    """Arquivos com motivo escrito (texto nao vazio apos strip).

    Motivo apagado/em branco e silencio, nao triagem - a mesma regra que
    derrubou o G77 (molde de _motivos_validos do G91 e _isencoes_validas do
    G103). Entrada vazia/None = ninguem isento, nunca erro; nao-dict
    levanta TypeError."""
    if not isencoes:
        return set()
    if not isinstance(isencoes, dict):
        raise TypeError("isencoes tem de ser dict arquivo->motivo")
    return {str(a or "").replace("\\", "/").split("/")[-1].strip()
            for a, texto in isencoes.items()
            if str(a or "").replace("\\", "/").split("/")[-1].strip()
            and str(texto or "").strip()}


def conferir_carimbo_mapa(mapa_codigo_arquivo, carimbos_por_arquivo,
                          isencoes=None):
    """Confronta o carimbo de cada folha emitida com o mapa codigo->arquivo.

    mapa_codigo_arquivo: {codigo do indice: arquivo} (o mapa vivo da
      tipologia).
    carimbos_por_arquivo: {basename do arquivo emitido: [codigos no
      carimbo daquela folha]} (extracao viva: AST sobre os techdraw_* +
      PRANCHAS/ARQUIVOS de prancha_svg_direta; arquivo emitido = nome da
      pagina + ".pdf").
    isencoes: {arquivo: motivo} para numeracao propria triada (a tabela
      que o cliente recebe); motivo vazio/em branco nao isenta.

    Devolve {"OK", "fora_do_mapa", "arquivo_sem_mapa",
      "sem_carimbo_informativo", "isentas"}:
      - fora_do_mapa: [(arquivo, carimbo, esperados-ordenados)] para cada
        carimbo que nao pertence ao conjunto que o mapa atribui aquele
        arquivo (cada gap nomeia o dado: codigo + arquivo + conjunto
        esperado);
      - arquivo_sem_mapa: arquivos com carimbo que nao tem entrada entre
        os valores do mapa (ordenados);
      - sem_carimbo_informativo: arquivos do mapa sem literal de carimbo
        extraivel (ordenados) - nao-coverture declarada, NAO afeta o OK;
      - isentas: arquivos com carimbo cobertos por isencao com motivo
        escrito (excecao nomeada, nao gap);
      - OK: fora_do_mapa e arquivo_sem_mapa vazios (a lente nao
        enfraquece: sem isencoes o galpao reprova como antes).
    Entrada malformada (None ou nao-dict) levanta TypeError: lente que
    devolve OK sobre lixo e saturacao silenciosa."""
    if mapa_codigo_arquivo is None:
        raise TypeError("mapa_codigo_arquivo nao pode ser None")
    if not isinstance(mapa_codigo_arquivo, dict):
        raise TypeError("mapa_codigo_arquivo tem de ser dict codigo->arquivo")
    if carimbos_por_arquivo is None:
        raise TypeError("carimbos_por_arquivo nao pode ser None")
    if not isinstance(carimbos_por_arquivo, dict):
        raise TypeError("carimbos_por_arquivo tem de ser dict arquivo->[carimbos]")
    por_arquivo = {}
    for codigo, arquivo in mapa_codigo_arquivo.items():
        nome = str(arquivo or "").replace("\\", "/").split("/")[-1].strip()
        if nome:
            por_arquivo.setdefault(nome, set()).add(str(codigo))
    isentos = _isencoes_validas(isencoes)
    fora_do_mapa = []
    arquivo_sem_mapa = []
    isentas = []
    com_carimbo = set()
    for arquivo, carimbos in carimbos_por_arquivo.items():
        nome = str(arquivo or "").replace("\\", "/").split("/")[-1].strip()
        vistos = sorted({str(c).strip() for c in (carimbos or [])
                         if str(c or "").strip()})
        if not nome or not vistos:
            continue
        com_carimbo.add(nome)
        if nome in isentos:
            isentas.append(nome)
            continue
        esperados = por_arquivo.get(nome)
        if esperados is None:
            arquivo_sem_mapa.append(nome)
            continue
        for carimbo in vistos:
            if carimbo not in esperados:
                fora_do_mapa.append((nome, carimbo, sorted(esperados)))
    fora_do_mapa.sort()
    arquivo_sem_mapa.sort()
    isentas.sort()
    sem_carimbo = sorted(n for n in por_arquivo if n not in com_carimbo)
    return {"OK": not (fora_do_mapa or arquivo_sem_mapa),
            "fora_do_mapa": fora_do_mapa,
            "arquivo_sem_mapa": arquivo_sem_mapa,
            "sem_carimbo_informativo": sem_carimbo,
            "isentas": isentas}


def relatorio_pt(por_tipologia):
    """Uma mensagem so com todas as tipologias (receita do G97).

    por_tipologia: {nome: resultado de conferir_carimbo_mapa}."""
    linhas = ["VARREDURA G112 - CARIMBO <-> MAPA"]
    for nome in sorted(por_tipologia):
        res = por_tipologia[nome]
        linhas.append("  [%s] OK=%s fora_do_mapa=%d arquivo_sem_mapa=%d "
                       "sem_carimbo_informativo=%d isentas=%d" % (
                           nome, res["OK"],
                           len(res.get("fora_do_mapa") or []),
                           len(res.get("arquivo_sem_mapa") or []),
                           len(res.get("sem_carimbo_informativo") or []),
                           len(res.get("isentas") or [])))
        for arquivo, carimbo, esperados in res.get("fora_do_mapa") or []:
            linhas.append("    %-14s %-22s carimbo=%-12s esperados=%s" % (
                "fora_do_mapa", arquivo, carimbo, esperados))
        for arquivo in res.get("arquivo_sem_mapa") or []:
            linhas.append("    %-14s %s" % ("arquivo_sem_mapa", arquivo))
        for arquivo in res.get("sem_carimbo_informativo") or []:
            linhas.append("    %-14s %s (sem literal de carimbo)"
                           % ("sem_carimbo", arquivo))
        for arquivo in res.get("isentas") or []:
            linhas.append("    %-14s %s (isenta com motivo)"
                           % ("isenta", arquivo))
    return "\n".join(linhas)


def correspondencia_markdown(tabela=None, razao=None):
    """Renderiza a secao da tabela que o cliente recebe (G112).

    tabela: lista de {arquivo, carimbo, cobre, motivo} (default
      CORRESPONDENCIA_G112); razao: o porque escrito (default
      RAZAO_NUMERACAO_PROPRIA_G112, verbatim do cabecalho). Cada entrada
      sai verbatim: carimbo, arquivo, codigos cobertos, motivo. Pura, sem
      AST e sem FreeCAD."""
    tabela = CORRESPONDENCIA_G112 if tabela is None else tabela
    razao = RAZAO_NUMERACAO_PROPRIA_G112 if razao is None else razao
    linhas = ["## Correspondencia de numeracao do executivo (G112)", "",
               str(razao), ""]
    for e in tabela or []:
        carimbo = e.get("carimbo") or "(sem carimbo extraivel)"
        cobre = list(e.get("cobre") or [])
        cobertura = (", ".join(cobre)
                     if cobre else "(sem codigo proprio no indice)")
        linhas.append("- %s — carimbo %s — cobre %s — %s"
                       % (e.get("arquivo"), carimbo, cobertura,
                          e.get("motivo")))
    return "\n".join(linhas)


def _selftest():
    mapa = {"PE-EL-01": "PE01_UNIFILAR.pdf", "PE-EL-02": "PE02_PLANTA_INST.pdf"}
    bom = conferir_carimbo_mapa(
        mapa, {"PE01_UNIFILAR.pdf": ["PE-EL-01"],
               "PE02_PLANTA_INST.pdf": ["PE-EL-02"]})
    assert bom["OK"] and bom["fora_do_mapa"] == [] \
        and bom["arquivo_sem_mapa"] == [], bom
    trocado = conferir_carimbo_mapa(
        mapa, {"PE01_UNIFILAR.pdf": ["PE-EL-02"]})
    assert trocado["fora_do_mapa"] == [
        ("PE01_UNIFILAR.pdf", "PE-EL-02", ["PE-EL-01"])] \
        and not trocado["OK"], trocado
    sem_mapa = conferir_carimbo_mapa(mapa, {"FANTASMA.pdf": ["PE-XX-01"]})
    assert sem_mapa["arquivo_sem_mapa"] == ["FANTASMA.pdf"] \
        and not sem_mapa["OK"], sem_mapa
    informativo = conferir_carimbo_mapa(mapa, {})
    assert informativo["OK"] and informativo["sem_carimbo_informativo"] == [
        "PE01_UNIFILAR.pdf", "PE02_PLANTA_INST.pdf"], informativo
    vazio = conferir_carimbo_mapa(mapa, {"PE01_UNIFILAR.pdf": []})
    assert vazio["OK"] and vazio["sem_carimbo_informativo"] == [
        "PE01_UNIFILAR.pdf", "PE02_PLANTA_INST.pdf"], vazio
    # isencoes: arquivo triado sai em isentas e some dos gaps; motivo em
    # branco e silencio, nao triagem; o OK com isencao exige motivo escrito.
    isento = conferir_carimbo_mapa(
        mapa, {"PE01_UNIFILAR.pdf": ["PE-XX-01"]},
        {"PE01_UNIFILAR.pdf": "numeracao propria triada na tabela G112"})
    assert isento["OK"] and isento["isentas"] == ["PE01_UNIFILAR.pdf"] \
        and not isento["fora_do_mapa"], isento
    apagada = conferir_carimbo_mapa(
        mapa, {"PE01_UNIFILAR.pdf": ["PE-XX-01"]},
        {"PE01_UNIFILAR.pdf": "   "})
    assert apagada["fora_do_mapa"] == [
        ("PE01_UNIFILAR.pdf", "PE-XX-01", ["PE-EL-01"])] \
        and apagada["isentas"] == [] and not apagada["OK"], apagada
    try:
        conferir_carimbo_mapa(None, {})
        raise AssertionError("mapa None devia levantar")
    except TypeError:
        pass
    try:
        conferir_carimbo_mapa({}, None)
        raise AssertionError("carimbos None devia levantar")
    except TypeError:
        pass
    try:
        conferir_carimbo_mapa(["PE-EL-01"], {})
        raise AssertionError("mapa nao-dict devia levantar")
    except TypeError:
        pass
    try:
        conferir_carimbo_mapa({}, {}, isencoes=["PE01_UNIFILAR.pdf"])
        raise AssertionError("isencoes nao-dict devia levantar")
    except TypeError:
        pass
    # tabela: 25 entradas (22 + INC03_DETALHES do G138 +
    # PE04_LOCACAO_FUNDACAO do G140 + MZ01_MEZANINO do G146), cada uma com
    # arquivo/carimbo/cobre/motivo; isencoes derivadas 1:1; o renderer conta
    # cada arquivo na secao do cliente.
    assert len(CORRESPONDENCIA_G112) == 25, len(CORRESPONDENCIA_G112)
    assert set(ISENCOES_CARIMBO_MAPA) == {e["arquivo"]
                                          for e in CORRESPONDENCIA_G112}
    assert all(str(v or "").strip() for e in CORRESPONDENCIA_G112
               for v in (e["arquivo"], e["motivo"]))
    sec = correspondencia_markdown()
    assert sec.startswith("## Correspondencia de numeracao do executivo "
                           "(G112)")
    assert RAZAO_NUMERACAO_PROPRIA_G112 in sec
    assert all(e["arquivo"] in sec for e in CORRESPONDENCIA_G112), sec
    return True


if __name__ == "__main__":
    _selftest()
    demo = conferir_carimbo_mapa(
        {"PE-HI-01": "HID01_ESQUEMA.pdf", "PE-HI-02": "HID01_ESQUEMA.pdf"},
        {"HID01_ESQUEMA.pdf": ["PE-HID-01"]})
    print(relatorio_pt({"demo": demo}))
    print("selftest OK")
