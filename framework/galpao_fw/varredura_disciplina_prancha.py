# ============================================================================
# varredura_disciplina_prancha.py - G103: DISCIPLINA EXECUTADA TEM PRANCHA OU MOTIVO.
# SCRIPT AVULSO: ferramenta permanente rodada a mao/CI (python
# varredura_disciplina_prancha.py) e pelo teste-guarda
# tests/test_disciplina_prancha_g103.py. Nao e importada por nenhum
# orquestrador do Loop - declarada em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de varredura_asserts_sequencia.
#
# Motivacao (G103): "mezanino" estava em galpao_turnkey.DISCIPLINAS e nao em
# pacote_legal._PRANCHAS - a disciplina era calculada e evaporava no `continue`
# do indice (travado por assert em tests/test_indice_disco_g91.py:304-305,
# achado registrado e nao consertado). Era o D89 espelhado: o D89 conhecido
# e codigo prometido sem arquivo; este era disciplina entregue sem codigo.
# Nenhuma lente olhava esse lado. G141 curou o gap (PE-MZ-01 em _PRANCHAS,
# ausencia declarada por codigo no laco); a motivacao fica como registro.
#
# Maquina: funcao pura, sem AST e sem FreeCAD. Recebe as disciplinas
# executadas (fonte viva da tipologia), o mapa de pranchas
# (pacote_legal._PRANCHAS) e as isencoes escritas, e devolve o gap
# `sem_prancha` + OK. O teste-guarda aplica a funcao as tres tipologias
# com as tres fontes vivas (galpao_turnkey.DISCIPLINAS,
# gestao_casa.disciplinas_pacote, gestao_edificio.disciplinas_pacote).
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - conteudo da folha (geometria, legibilidade): e de confere_folha_svg
#     e do censo do G77, nao desta lente (existencia nao e conteudo);
#   - motivo generico vs motivo com o dado nomeado: a PRESENCA do motivo
#     libera aqui; a QUALIDADE do motivo e do G92, nao desta lente;
#   - indice x disco (arquivo emitido ou nao): e da lente do G91/G102,
#     nao desta (promessa x execucao, nao promessa x arquivo).
# ============================================================================
"""Varredura G103: disciplina executada <-> entrada em _PRANCHAS, funcao pura."""

from __future__ import annotations

import pathlib

GALPAO = pathlib.Path(__file__).resolve().parent


# G141: o mezanino do galpao ganhou entrada em pacote_legal._PRANCHAS
# (PE-MZ-01, ausencia declarada por codigo sem emissor ligado). A isencao
# morreu com a cura - disciplina executada agora tem prancha (ou motivo
# por codigo no laco), e isencao sem gap viraria silencio. Dict vazio =
# ninguem isento, nunca erro.
ISENCOES_DISCIPLINA_PRANCHA = {
}


# Coberturas declaradas: disciplina executada cujo detalhamento sai na
# folha de outra disciplina. Espelha FUNDACAO_COBERTA_POR de gestao_casa e
# gestao_edificio ("fundacao" coberta pelo "concreto", PE-CO-01 "Formas e
# fundacoes") - dito em voz alta para nao evaporar no `continue` (D89).
COBERTA_POR = {
    "fundacao": "concreto",
}


def _isencoes_validas(isencoes):
    """Disciplinas com motivo escrito (texto nao vazio apos strip).

    Motivo apagado/em branco e silencio, nao triagem. Entrada vazia/None
    = ninguem isento, nunca erro."""
    if not isencoes:
        return set()
    if not isinstance(isencoes, dict):
        raise TypeError("isencoes tem de ser dict disciplina->motivo")
    return {str(d) for d, texto in isencoes.items()
            if str(d or "").strip() and str(texto or "").strip()}


def conferir_disciplina_prancha(executadas, pranchas, isencoes=None):
    """Confronta as disciplinas executadas com o vocabulario do indice.

    executadas: disciplinas que a tipologia executa (fonte viva: tupla do
      turnkey ou disciplinas_pacote(resultado) da casa/predio).
    pranchas: mapa disciplina->(prefixo, titulos) (pacote_legal._PRANCHAS).
    isencoes: {disciplina: motivo} para executada sem prancha propria;
      motivo vazio/em branco nao isenta.

    Devolve {"OK", "sem_prancha", "isentas"}:
      - sem_prancha: executada SEM entrada em pranchas, SEM cobertura
        declarada e SEM isencao com motivo escrito;
      - isentas: executadas cobertas por isencao com motivo escrito
        (excecao nomeada, nao gap);
      - OK: sem_prancha vazio.
    Entrada malformada (None onde se espera lista/mapa) levanta
    TypeError: lente que devolve OK sobre lixo e saturacao silenciosa."""
    if executadas is None:
        raise TypeError("executadas nao pode ser None")
    if pranchas is None:
        raise TypeError("pranchas nao pode ser None")
    if not isinstance(pranchas, dict):
        raise TypeError("pranchas tem de ser dict disciplina->(prefixo, titulos)")
    vistas = _isencoes_validas(isencoes)
    sem_prancha = []
    isentas = []
    for nome in list(executadas or []):
        chave = str(nome)
        if chave in pranchas:
            continue
        cobertura = COBERTA_POR.get(chave)
        if cobertura is not None and cobertura in pranchas:
            continue
        if chave in vistas:
            isentas.append(chave)
        else:
            sem_prancha.append(chave)
    return {"OK": not sem_prancha,
            "sem_prancha": sorted(sem_prancha),
            "isentas": sorted(isentas)}


def relatorio_pt(por_tipologia):
    """Uma mensagem so com todas as tipologias (receita do G97).

    por_tipologia: {nome: resultado de conferir_disciplina_prancha}."""
    linhas = ["VARREDURA G103 - DISCIPLINA EXECUTADA <-> PRANCHA"]
    for nome in sorted(por_tipologia):
        res = por_tipologia[nome]
        linhas.append("  [%s] OK=%s sem_prancha=%d isentas=%d" % (
            nome, res["OK"], len(res.get("sem_prancha") or []),
            len(res.get("isentas") or [])))
        for disciplina in res.get("sem_prancha") or []:
            linhas.append("    %-14s %s" % ("sem_prancha", disciplina))
        for disciplina in res.get("isentas") or []:
            linhas.append("    %-14s %s (isenta com motivo)"
                         % ("isenta", disciplina))
    return "\n".join(linhas)


def _selftest():
    pranchas = {"concreto": ("PE-CO", ["Formas"]), "aco": ("PE-ES", ["Portico"])}
    bom = conferir_disciplina_prancha(
        ["concreto", "aco"], pranchas, {})
    assert bom["OK"] and bom["sem_prancha"] == [] and bom["isentas"] == []
    gap = conferir_disciplina_prancha(
        ["concreto", "mezanino"], pranchas, {})
    assert gap["sem_prancha"] == ["mezanino"] and not gap["OK"], gap
    isento = conferir_disciplina_prancha(
        ["concreto", "mezanino"], pranchas,
        {"mezanino": "parte da estrutura, sem folha propria"})
    assert isento["OK"] and isento["isentas"] == ["mezanino"], isento
    apagada = conferir_disciplina_prancha(
        ["concreto", "mezanino"], pranchas, {"mezanino": "   "})
    assert apagada["sem_prancha"] == ["mezanino"] and not apagada["OK"], \
        apagada
    coberta = conferir_disciplina_prancha(["fundacao"], pranchas, {})
    assert coberta["OK"] and coberta["sem_prancha"] == [], coberta
    try:
        conferir_disciplina_prancha(None, {}, {})
        raise AssertionError("executadas None devia levantar")
    except TypeError:
        pass
    try:
        conferir_disciplina_prancha([], None, {})
        raise AssertionError("pranchas None devia levantar")
    except TypeError:
        pass
    return True


if __name__ == "__main__":
    _selftest()
    demo = conferir_disciplina_prancha(
        ["concreto", "aco", "mezanino"],
        {"concreto": ("PE-CO", ["Formas"]), "aco": ("PE-ES", ["Portico"])},
        ISENCOES_DISCIPLINA_PRANCHA)
    print(relatorio_pt({"demo": demo}))
    print("selftest OK")
