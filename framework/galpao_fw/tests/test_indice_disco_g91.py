"""G91 - uma lente de indice<->disco para as tres tipologias.

Contexto: tres implementacoes do mesmo contrato, nenhuma delas E o
contrato. O predio confronta o indice de todas as disciplinas do pacote
+ coordenacao contra _PRANCHA_ARQUIVO (15/15); a casa confronta so
["arquitetura"] (3/3, recorte do proprio escopo); o galpao nao tem mapa
nenhum (numero contra numero em pacote_no_manifesto).

Este portao ENTROU VERMELHO DE PROPOSITO na arvore viva: casa (13 sem
mapa) e galpao (19 sem mapa) reprovavam no minuto em que a lente existiu.
O G92 fechou a casa (mapa de 17 + laco na fonte unica do pacote) e o G93
fechou o galpao (mapa de 19 + laco no hook, ver
tests/test_galpao_indice_g93.py). Os tres lados verdes provam que a lente
nao acusa tudo.

1. FERRAMENTA (varredura_indice_disco.py, funcao pura): recebe os quatro
   lados e devolve faltando/sobrando/sem_mapa/OK. Nao reescreve
   confere_folha_svg nem o censo do G77 (conteudo, nao existencia).
2. PORTAO (test_01): aplica a lente aos MAPAS REAIS das tres
   tipologias e falha UMA vez so, com todos os lados na mensagem (a
   receita do G97: coletar tudo, relatar tudo, um assert).
3. BASELINE (test_02, nos dois sentidos): o estado conhecido congelado -
   predio verde, casa 13 sem mapa, galpao 19 sem mapa. Mudanca some sem
   triagem = vermelho; gap novo some no meio do conhecido = vermelho.
4. INJECAO (test_03..05, tmp_path, nunca mutando o repo): apagar uma
   entrada do mapa, plantar um nome morto, tirar um arquivo do disco e
   apagar um motivo deixam a suite vermelha; o caso bom fica verde.

Nao fazer (regra do goal): arbitrar geometria ou dado de projeto para
"fazer a folha sair". A ausencia se declara - e aqui ela aparece como
sem_mapa, um gap nomeado por codigo, nunca um default silencioso.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import varredura_indice_disco as lente


def _codigos(disciplinas):
    import pacote_legal as pl

    return sorted(f["codigo"] for f in pl.indice_de_pranchas(disciplinas))


def _quadro_casa():
    """A casa completa: uniao das disciplinas, 17 prometidos, 17 mapeados.

    A fonte das disciplinas e a MESMA que o pacote usa
    (gestao_casa.disciplinas_pacote) - ligada no laco da casa pelo G92.
    Fixture com alvenaria E telhado (a uniao): sem telhado nao ha PE-MD,
    sem alvenaria nao ha PE-AL - o laco da casa so confronta o que a
    rodada promete, e este quadro trava a uniao (nenhum codigo da uniao
    sem entrada no mapa, nenhuma entrada morta). A rodada real sem
    alvenaria promete 15 e o laco ignora as entradas extras do mapa."""

    import casa_residencial as casa
    import gestao_casa as gcasa

    resultado = {
        "arquitetura": {"totais": {}},
        "estrutura": {"fundacao": {"ok": True}, "alvenaria": {"ok": True},
                      "telhado": {"geometria_nos": {"N1": [0.0, 0.0]}}},
        "hidraulica": {"ok": True},
        "eletrico": {"circuits": {"layout_validation": {}}},
    }
    discos = gcasa.disciplinas_pacote(resultado)
    prometidos = _codigos(discos)
    mapa = dict(casa._PRANCHA_ARQUIVO_CASA)
    return {"prometidos": prometidos, "mapa": mapa,
            "disco": sorted(mapa.values()), "motivos": {}}


def _quadro_predio():
    """O predio completo: 15 prometidos, 15 mapeados, lado verde."""
    import edificio_adapter as predio
    import gestao_edificio as gedif

    resultado = {
        "estrutura": {"fundacao": {"ok": True}},
        "instalacoes": {"eletrico": {"ok": True},
                        "hidraulica": {"ok": True},
                        "incendio": {"ok": True}},
    }
    discos = gedif.disciplinas_pacote(resultado) + ["coordenacao"]
    prometidos = _codigos(discos)
    mapa = dict(predio._PRANCHA_ARQUIVO)
    return {"prometidos": prometidos, "mapa": mapa,
            "disco": sorted(mapa.values()), "motivos": {}}


def _quadro_galpao():
    """O galpao: mapa real do G93, 19 prometidos, 19 mapeados, lado verde.

    Prometidos = DISCIPLINAS que o turnkey executa (fonte viva,
    galpao_turnkey) filtradas ao vocabulario do indice + coordenacao.
    "mezanino" evapora no continue do indice (D89) - achado registrado,
    nao consertado (o pacote faz o mesmo; o laco do G93 confronta a mesma
    fonte). O disco do quadro e o caso bom (tudo emitido); a rodada real
    sem uma disciplina marca os codigos dela como pulados nomeados, nunca
    como buraco - ver tests/test_galpao_indice_g93.py."""
    import galpao_adapter as ga
    import galpao_turnkey as tk
    import pacote_legal as pl

    discos = [d for d in tk.DISCIPLINAS if d in pl._PRANCHAS]
    prometidos = _codigos(discos + ["coordenacao"])
    mapa = dict(ga._PRANCHA_ARQUIVO_GALPAO)
    return {"prometidos": prometidos, "mapa": mapa,
            "disco": sorted(set(mapa.values())), "motivos": {}}


def _quadros():
    return {"casa": _quadro_casa(), "galpao": _quadro_galpao(),
            "predio": _quadro_predio()}


def _resultados(quadros=None):
    quadros = quadros if quadros is not None else _quadros()
    return {nome: lente.conferir_indice_disco(
        q["prometidos"], q["mapa"], q["disco"], q["motivos"])
        for nome, q in quadros.items()}


# BASELINE_G91 (medido 2026-09-10, commit 72a210e; curado na casa pelo
# G92 e no galpao pelo G93 em 2026-09-10): as tres tipologias fecham
# (predio 15/15, casa 17/17, galpao 19/19). Entrada nova aqui = cura de um
# lado (o baseline MUDA junto, nunca em silencio); gap novo que coincida
# com estes e o defeito voltando.
BASELINE_G91 = {
    "casa": {"faltando": [], "sobrando": [], "sem_mapa": []},
    "galpao": {"faltando": [], "sobrando": [], "sem_mapa": []},
    "predio": {"faltando": [], "sobrando": [], "sem_mapa": []},
}


def test_01_portao_tres_tipologias_falha_unica():
    """O portao: as tres tipologias, todos os lados, um assert so.

    VERDE nas tres desde o G93 (a casa foi fechada pelo G92, o galpao pelo
    G93, o predio sempre fechou). A mensagem nomeia os tres lados de cada
    tipologia numa rodada so (receita do G97) - nao um assert por vez,
    que esconderia os seguintes."""
    quadros = _quadros()
    resultados = _resultados(quadros)
    maus = sorted(n for n, r in resultados.items() if not r["OK"])
    assert not maus, (
        "indice<->disco reprova %r (G91: o gap nomeado; G92/G93 fecham).\n%s"
        % (maus, lente.relatorio_pt(
            resultados,
            {n: q["mapa"] for n, q in quadros.items()},
            {n: q["prometidos"] for n, q in quadros.items()})))


def test_02_baseline_g91_nos_dois_sentidos():
    """Sem baseline congelado nos dois sentidos a lente e relatorio, nao
    portao: gap novo cairia no meio do conhecido com a suite verde."""
    agora = {n: {k: r[k] for k in ("faltando", "sobrando", "sem_mapa")}
             for n, r in _resultados().items()}
    # G97: um assert so, com tipologia nova e gaps por tipologia na mesma
    # mensagem. O assert de tipologia escondia os gaps seguintes.
    lados = []
    if set(agora) != set(BASELINE_G91):
        lados.append("tipologia nova sem triagem G91: %r"
                     % (sorted(set(agora) ^ set(BASELINE_G91)),))
    for nome in sorted(set(agora) | set(BASELINE_G91)):
        if agora.get(nome) != BASELINE_G91.get(nome):
            lados.append("G91 mudou em %r: conhecido %r, agora %r. Cura "
                         "(G92/G93) muda o baseline junto; gap novo nao some "
                         "no conhecido."
                         % (nome, BASELINE_G91.get(nome), agora.get(nome)))
    assert not lados, "baseline G91 reprova:\n" + "\n".join(lados)


def test_03_vermelho_por_injecao_no_mapa_via_tmp_path(tmp_path):
    """Apagar uma entrada de _PRANCHA_ARQUIVO deixa a suite vermelha; o
    caso bom fica verde. A copia mora em tmp_path (convenção 2: o repo
    vivo nunca e mutado)."""
    quadros = _quadros()
    caminho = tmp_path / "mapa_predio.json"
    caminho.write_text(json.dumps(quadros["predio"]["mapa"]),
                       encoding="utf-8")
    copia = dict(json.loads(caminho.read_text(encoding="utf-8")))
    # caso bom: a copia fiel fecha 15/15
    bom = lente.conferir_indice_disco(
        quadros["predio"]["prometidos"], copia,
        quadros["predio"]["disco"], {})
    assert bom["OK"], bom
    # injecao 1: sem a entrada, o codigo vira sem_mapa
    del copia["PE-CO-04"]
    quebrado = lente.conferir_indice_disco(
        quadros["predio"]["prometidos"], copia,
        quadros["predio"]["disco"], {})
    assert quebrado["sem_mapa"] == ["PE-CO-04"] and not quebrado["OK"], \
        quebrado
    # injecao 2 (outro sentido): nome morto no mapa vira sobrando
    copia2 = dict(json.loads(caminho.read_text(encoding="utf-8")))
    copia2["PE-XX-99"] = "folha-morta.svg"
    morto = lente.conferir_indice_disco(
        quadros["predio"]["prometidos"], copia2,
        quadros["predio"]["disco"], {})
    assert morto["sobrando"] == ["PE-XX-99"] and not morto["OK"], morto


def test_04_faltando_precisa_de_arquivo_ou_motivo(tmp_path):
    """Codigo mapeado sem arquivo e sem motivo = faltando; com motivo
    escrito = nomeado (ok). Motivo apagado e silencio, nao triagem."""
    quadros = _quadros()
    prom = quadros["predio"]["prometidos"]
    mapa = quadros["predio"]["mapa"]
    disco_furado = [n for n in quadros["predio"]["disco"]
                    if n != "fundacao-locacao-formas.svg"]
    furado = lente.conferir_indice_disco(prom, mapa, disco_furado, {})
    assert furado["faltando"] == ["PE-CO-04"] and not furado["OK"], furado
    # motivo escrito (dict da casa / lista de dicts do predio) nomeia
    nomeado = lente.conferir_indice_disco(
        prom, mapa, disco_furado,
        [{"prancha": "fundacao-locacao-formas.svg",
          "motivo": "sondagem nao declarada"}])
    assert nomeado["OK"], nomeado
    apagado = lente.conferir_indice_disco(
        prom, mapa, disco_furado, {"fundacao-locacao-formas.svg": "   "})
    assert apagado["faltando"] == ["PE-CO-04"] and not apagado["OK"], \
        apagado
    # o laco do predio guarda "drawings/<nome>": o prefixo nao vira gap
    prefixado = lente.conferir_indice_disco(
        ["PE-CO-04"], {"PE-CO-04": "fundacao-locacao-formas.svg"},
        ["drawings/fundacao-locacao-formas.svg"], {})
    assert prefixado["OK"], prefixado
    assert tmp_path.is_dir()


def test_05_entrada_malformada_grita_e_laco_quebrado_e_nomeado():
    """Lente que devolve OK sobre lixo e saturacao silenciosa: None
    levanta. E a garantia que cai (a propria conferencia falhando) sai
    como "(indice)" com o erro nomeado - o comportamento do laco do
    predio, preservado na lente para G92/G93 reusarem."""
    try:
        lente.conferir_indice_disco(None, {}, [], {})
        raise AssertionError("prometidos None devia levantar")
    except TypeError:
        pass
    try:
        lente.conferir_indice_disco([], None, [], {})
        raise AssertionError("mapa None devia levantar")
    except TypeError:
        pass
    reg = lente.registro_laco_quebrado(RuntimeError("boom-g91"))
    # G97: um assert so, com prancha e motivo na mesma mensagem.
    lados = []
    if reg["prancha"] != "(indice)":
        lados.append("prancha=%r (esperado '(indice)')" % (reg["prancha"],))
    if not ("boom-g91" in reg["motivo"] and "RuntimeError" in reg["motivo"]):
        lados.append("motivo sem erro nomeado: %r" % (reg["motivo"],))
    assert not lados, "registro de laco quebrado reprova:\n" + "\n".join(lados)


def test_06_fontes_independentes_dos_prometidos():
    """Assercao nao-tautologica (convenção 5): os prometidos que os
    fixtures derivam das funcoes vivas sao comparados com a conta feita
    a mao a partir de pacote_legal._PRANCHAS (titulos por disciplina).

    Se disciplinas_pacote encolher em silencio, este teste acusa mesmo
    com a lente verde."""
    import pacote_legal as pl

    def conta(discos):
        return sum(len(pl._PRANCHAS[d][1]) for d in discos)

    quadros = _quadros()
    assert len(quadros["casa"]["prometidos"]) == conta(
        ["arquitetura", "concreto", "alvenaria_estrutural", "hidraulica",
         "eletrico", "madeira"]) == 17
    assert set(quadros["casa"]["prometidos"]) == {
        "PE-AR-%02d" % i for i in (1, 2, 3)} | {
        "PE-CO-%02d" % i for i in (1, 2, 3, 4)} | {
        "PE-AL-%02d" % i for i in (1, 2)} | {
        "PE-HI-%02d" % i for i in (1, 2, 3)} | {
        "PE-EL-%02d" % i for i in (1, 2, 3, 4)} | {"PE-MD-01"}
    assert len(quadros["predio"]["prometidos"]) == conta(
        ["concreto", "eletrico", "hidraulica", "incendio",
         "coordenacao"]) == 15
    assert len(quadros["galpao"]["prometidos"]) == conta(
        ["concreto", "aco", "eletrico", "hidraulica", "incendio",
         "climatizacao", "coordenacao"]) == 19
    # "mezanino" o turnkey executa e o indice nao promete: evapora no
    # continue (D89). Registrado para o G93; este assert trava o fato.
    import galpao_turnkey as tk

    assert "mezanino" in tk.DISCIPLINAS
    assert "mezanino" not in pl._PRANCHAS
