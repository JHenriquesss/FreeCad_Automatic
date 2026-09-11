# ============================================================================
# varredura_indice_disco.py - G91: O INDICE PROMETE, O DISCO ENTREGA.
# FERRAMENTA PERMANENTE rodada a mao/CI (python
# varredura_indice_disco.py), pelo teste-guarda
# tests/test_indice_disco_g91.py E importada pelos lacos da casa
# (casa_residencial, G92) e do galpao (galpao_adapter, G93) — graduou de
# avulsa a biblioteca quando os lacos passaram a reusar conferir +
# registro_laco_quebrado em vez de reimplementar (por isso NAO esta em
# SCRIPTS_AVULSOS em tests/test_alcancabilidade.py: avulso e script que
# ninguem importa, e esta e importada).
#
# Motivacao (G91): tres implementacoes do mesmo contrato e nenhuma delas
# E o contrato. O predio confronta o indice de todas as disciplinas do
# pacote + coordenacao contra _PRANCHA_ARQUIVO (edificio_adapter, 15/15);
# a casa confronta so ["arquitetura"] (3/3, recorte do proprio escopo);
# o galpao nao tem mapa nenhum (conta numero contra numero em
# pacote_no_manifesto). O buraco da casa (13 codigos evaporando no
# continue do indice) passava com a suite verde.
#
# Maquina: funcao pura, sem AST e sem FreeCAD. Recebe os quatro lados e
# devolve os tres gaps + OK. O teste-guarda aplica a funcao aos mapas
# reais das tres tipologias.
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - conteudo da folha (geometria, legibilidade): e de confere_folha_svg
#     e do censo do G77, nao desta lente (existencia nao e conteudo);
#   - motivo generico vs motivo com o dado nomeado: a PRESENCA do motivo
#     libera aqui; a QUALIDADE do motivo e do G92, nao desta lente;
#   - N:1 (um arquivo cobrindo varios codigos, ex. hidraulica do galpao):
#     cada codigo com entrada no mapa e avaliado pela sua entrada; dois
#     codigos apontando para o mesmo arquivo nao e "sobrando".
# ============================================================================
"""Varredura G91: indice de pranchas <-> arquivos no disco, funcao pura."""

from __future__ import annotations

import pathlib

GALPAO = pathlib.Path(__file__).resolve().parent


def _base(nome):
    """Ultimo segmento do caminho: "drawings/folha.svg" e "folha.svg" casam.

    Os lacos dos adaptadores guardam "drawings/<nome>" no manifesto e so o
    nome base no mapa; sem normalizar, toda folha emitida viraria
    "faltando"."""
    texto = str(nome or "").replace("\\", "/")
    return texto.split("/")[-1].strip()


def _motivos_validos(motivos):
    """Nomes com motivo escrito, normalizados por _base.

    Aceita os tres formatos que os adaptadores usam para puladas:
      - dict {arquivo: motivo}: so conta com texto nao vazio (motivo
        apagado e silencio, nao triagem);
      - lista de dicts {"prancha": nome, "motivo": texto} (predio);
      - iteravel de nomes (casa: dict nome->motivo chega como dict; uma
        lista de nomes conta como registro escrito da triagem).
    Entrada vazia/None = ninguem nomeado, nunca erro."""
    if not motivos:
        return set()
    if isinstance(motivos, dict):
        return {_base(chave) for chave, texto in motivos.items()
                if _base(chave) and str(texto or "").strip()}
    saida = set()
    for item in motivos:
        if isinstance(item, dict):
            nome = item.get("prancha", item.get("folha", ""))
            texto = item.get("motivo", "")
            if _base(nome) and str(texto or "").strip():
                saida.add(_base(nome))
        elif _base(item):
            saida.add(_base(item))
    return saida


def conferir_indice_disco(codigos_prometidos, mapa_codigo_arquivo,
                          nomes_no_disco, motivos_escritos):
    """Confronta o indice prometido com o disco, via o mapa codigo->arquivo.

    codigos_prometidos: os codigos do indice (pacote_legal).
    mapa_codigo_arquivo: {codigo: arquivo em drawings/} (o mapa da tipologia).
    nomes_no_disco: arquivos emitidos nesta rodada (com ou sem "drawings/").
    motivos_escritos: pulados com motivo (ver _motivos_validos).

    Devolve {"OK", "faltando", "sobrando", "sem_mapa"}:
      - faltando: codigo COM entrada no mapa cujo arquivo nem saiu nem foi
        nomeado com motivo;
      - sobrando: entrada no mapa que o indice nao promete (nome morto);
      - sem_mapa: codigo prometido que nem entrada no mapa tem;
      - OK: os tres vazios.
    Entrada malformada (None onde se espera lista/mapa) levanta TypeError:
    lente que devolve OK sobre lixo e saturacao silenciosa. Quem chama em
    adaptador captura e registra via registro_laco_quebrado (o "(indice)"
    do laco do predio), nunca engole."""
    if codigos_prometidos is None:
        raise TypeError("codigos_prometidos nao pode ser None")
    if mapa_codigo_arquivo is None:
        raise TypeError("mapa_codigo_arquivo nao pode ser None")
    if not isinstance(mapa_codigo_arquivo, dict):
        raise TypeError("mapa_codigo_arquivo tem de ser dict codigo->arquivo")
    prometidos = sorted({str(codigo) for codigo in codigos_prometidos})
    tem = set(prometidos)
    no_disco = {_base(n) for n in (nomes_no_disco or []) if _base(n)}
    nomeados = _motivos_validos(motivos_escritos)
    sem_mapa = sorted(c for c in prometidos if c not in mapa_codigo_arquivo)
    faltando = sorted(c for c in prometidos
                      if c in mapa_codigo_arquivo
                      and _base(mapa_codigo_arquivo[c]) not in no_disco
                      and _base(mapa_codigo_arquivo[c]) not in nomeados)
    sobrando = sorted(c for c in mapa_codigo_arquivo if c not in tem)
    return {"OK": not (faltando or sobrando or sem_mapa),
            "faltando": faltando, "sobrando": sobrando,
            "sem_mapa": sem_mapa}


def registro_laco_quebrado(exc):
    """O registro "(indice)" do laco do predio, em forma chamavel.

    A garantia (todo codigo do indice sai ou sai nomeado) nao pode cair em
    silencio quando a propria conferencia falha: o manifesto diz que ela
    nao aconteceu, com o erro nomeado. G92/G93 reusam em vez de
    reimplementar o except."""
    return {"prancha": "(indice)",
            "motivo": "laco indice<->disco nao pode ser conferido: %s: %s"
                      % (type(exc).__name__, exc)}


def relatorio_pt(por_tipologia, mapas=None, prometidos=None):
    """Uma mensagem so com todos os lados (receita do G97).

    por_tipologia: {nome: resultado de conferir_indice_disco}.
    mapas: {nome: mapa usado} opcional, para mostrar o arquivo esperado.
    prometidos: {nome: lista de codigos} opcional, para a contagem."""
    mapas = mapas or {}
    prometidos = prometidos or {}
    linhas = ["VARREDURA G91 - INDICE <-> DISCO"]
    for nome in sorted(por_tipologia):
        res = por_tipologia[nome]
        mapa = mapas.get(nome) or {}
        linhas.append("  [%s] OK=%s prometidos=%d faltando=%d sobrando=%d "
                       "sem_mapa=%d" % (
                           nome, res["OK"], len(prometidos.get(nome) or []),
                           len(res["faltando"]), len(res["sobrando"]),
                           len(res["sem_mapa"])))
        for lado in ("sem_mapa", "faltando", "sobrando"):
            for codigo in res[lado]:
                esperado = mapa.get(codigo, "-")
                linhas.append("    %-9s %-10s -> %s" % (lado, codigo, esperado))
    return "\n".join(linhas)


def _selftest():
    bom = conferir_indice_disco(
        ["PE-AR-01", "PE-AR-02"],
        {"PE-AR-01": "a.svg", "PE-AR-02": "b.svg"},
        ["drawings/a.svg", "b.svg"], {})
    assert bom["OK"] and not bom["faltando"]
    sem_arquivo = conferir_indice_disco(
        ["PE-AR-01"], {"PE-AR-01": "a.svg"}, [], {})
    assert sem_arquivo["faltando"] == ["PE-AR-01"] and not sem_arquivo["OK"]
    com_motivo = conferir_indice_disco(
        ["PE-AR-01"], {"PE-AR-01": "a.svg"}, [],
        {"a.svg": "dado X nao declarado"})
    assert com_motivo["OK"]
    motivo_apagado = conferir_indice_disco(
        ["PE-AR-01"], {"PE-AR-01": "a.svg"}, [], {"a.svg": "   "})
    assert motivo_apagado["faltando"] == ["PE-AR-01"]
    sem_entrada = conferir_indice_disco(["PE-AR-09"], {}, [], {})
    assert sem_entrada["sem_mapa"] == ["PE-AR-09"]
    morto = conferir_indice_disco(
        [], {"PE-XX-01": "morta.svg"}, [], {})
    assert morto["sobrando"] == ["PE-XX-01"]
    try:
        conferir_indice_disco(None, {}, [], {})
        raise AssertionError("None devia levantar")
    except TypeError:
        pass
    reg = registro_laco_quebrado(ValueError("boom"))
    assert reg["prancha"] == "(indice)" and "boom" in reg["motivo"]
    return True


if __name__ == "__main__":
    _selftest()
    demo = conferir_indice_disco(
        ["PE-AR-01", "PE-AR-02", "PE-CO-01"],
        {"PE-AR-01": "a.svg", "PE-AR-02": "b.svg"},
        ["a.svg"], {})
    print(relatorio_pt({"demo": demo},
                       {"demo": {"PE-AR-01": "a.svg",
                                 "PE-AR-02": "b.svg"}},
                       {"demo": ["PE-AR-01", "PE-AR-02", "PE-CO-01"]}))
    print("selftest OK")
