"""G103 - disciplina executada que o indice nao promete: o D89 do lado da promessa.

Medido (G98): "mezanino" esta em galpao_turnkey.DISCIPLINAS e nao em
pacote_legal._PRANCHAS (travado por assert em
tests/test_indice_disco_g91.py:304-305, achado registrado e nao
consertado). A disciplina e calculada e evapora no `continue` do indice.
E o D89 espelhado: o D89 conhecido e codigo prometido sem arquivo; este
e disciplina entregue sem codigo. Nenhuma lente olhava esse lado.

Entregue:
  1. FERRAMENTA (varredura_disciplina_prancha.py, funcao pura): recebe as
     disciplinas executadas, o mapa de pranchas e as isencoes escritas, e
     devolve sem_prancha/isentas/OK. Nao reescreve confere_folha_svg nem
     o censo do G77 (existencia de promessa, nao conteudo).
  2. PORTAO (test_01): aplica a lente as TRES tipologias com as tres
     fontes vivas (galpao_turnkey.DISCIPLINAS,
     gestao_casa.disciplinas_pacote, gestao_edificio.disciplinas_pacote)
     e falha UMA vez so, com todos os lados na mensagem (a receita do
     G97: coletar tudo, relatar tudo, um assert).
  3. BASELINE (test_02, nos dois sentidos): o estado conhecido congelado -
     galpao isenta "mezanino" com motivo escrito; casa e predio sem gap.
     Disciplina nova sem prancha = vermelho; gap conhecido que some sem
     triagem = vermelho.
  4. INJECAO (test_03, tmp_path, nunca mutando o repo): disciplina nova
     sem prancha, motivo apagado e cobertura sumida deixam a suite
     vermelha; o caso bom fica verde.

Nao fazer (regra do lote): arbitrar valor normativo, inventar dado de
projeto, ou transformar ausencia de dado em default silencioso. O
mezanino segue sem prancha propria com a excecao nomeada - ausencia
declarada continua sendo entrega valida.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import varredura_disciplina_prancha as lente


def _pranchas():
    import pacote_legal as pl

    return pl._PRANCHAS


def _executadas_galpao():
    """O galpao: todas as disciplinas que o turnkey executa (fonte viva)."""
    import galpao_turnkey as tk

    return list(tk.DISCIPLINAS)


def _executadas_casa():
    """A casa completa: a uniao das disciplinas no vocabulario do indice.

    Fixture com arquitetura + fundacao + alvenaria + telhado (a uniao):
    sem telhado nao ha madeira, sem alvenaria nao ha alvenaria_estrutural.
    A fonte e a MESMA que o pacote usa (gestao_casa.disciplinas_pacote)."""
    import gestao_casa as gcasa

    resultado = {
        "arquitetura": {"totais": {}},
        "estrutura": {"fundacao": {"ok": True}, "alvenaria": {"ok": True},
                      "telhado": {"geometria_nos": {"N1": [0.0, 0.0]}}},
        "hidraulica": {"ok": True},
        "eletrico": {"circuits": {"layout_validation": {}}},
    }
    return list(gcasa.disciplinas_pacote(resultado))


def _executadas_predio():
    """O predio completo: a uniao das disciplinas no vocabulario do indice.

    A fonte e a MESMA que o pacote usa
    (gestao_edificio.disciplinas_pacote)."""
    import gestao_edificio as gedif

    resultado = {
        "estrutura": {"fundacao": {"ok": True}},
        "instalacoes": {"eletrico": {"ok": True},
                        "hidraulica": {"ok": True},
                        "incendio": {"ok": True}},
    }
    return list(gedif.disciplinas_pacote(resultado))


def _quadros():
    pranchas = _pranchas()
    return {"casa": {"executadas": _executadas_casa(),
                     "pranchas": pranchas},
            "galpao": {"executadas": _executadas_galpao(),
                       "pranchas": pranchas},
            "predio": {"executadas": _executadas_predio(),
                       "pranchas": pranchas}}


def _resultados(quadros=None):
    quadros = quadros if quadros is not None else _quadros()
    return {nome: lente.conferir_disciplina_prancha(
        q["executadas"], q["pranchas"], lente.ISENCOES_DISCIPLINA_PRANCHA)
        for nome, q in quadros.items()}


# BASELINE_G103 (medido 2026-09-11): o galpao executa 7 disciplinas e isenta
# 1 ("mezanino", parte da estrutura sem prancha propria, motivo escrito);
# casa (6 na uniao) e predio (4) fecham sem gap. Entrada nova aqui = cura
# de um lado (o baseline MUDA junto, nunca em silencio); gap novo que
# coincida com estes e o defeito voltando.
BASELINE_G103 = {
    "casa": {"sem_prancha": [], "isentas": []},
    "galpao": {"sem_prancha": [], "isentas": ["mezanino"]},
    "predio": {"sem_prancha": [], "isentas": []},
}


def test_01_portao_tres_tipologias_falha_unica():
    """O portao: as tres tipologias, todos os lados, um assert so.

    A mensagem nomeia as tres tipologias numa rodada so (receita do G97)
    - nao um assert por vez, que esconderia as seguintes."""
    quadros = _quadros()
    resultados = _resultados(quadros)
    maus = sorted(n for n, r in resultados.items() if not r["OK"])
    assert not maus, (
        "disciplina executada sem prancha %r (G103).\n%s"
        % (maus, lente.relatorio_pt(resultados)))


def test_02_baseline_g103_nos_dois_sentidos():
    """Sem baseline congelado nos dois sentidos a lente e relatorio, nao
    portao: gap novo cairia no meio do conhecido com a suite verde."""
    agora = {n: {k: r[k] for k in ("sem_prancha", "isentas")}
             for n, r in _resultados().items()}
    # G97: um assert so, com tipologia nova e gaps por tipologia na mesma
    # mensagem. O assert de tipologia escondia os gaps seguintes.
    lados = []
    if set(agora) != set(BASELINE_G103):
        lados.append("tipologia nova sem triagem G103: %r"
                     % (sorted(set(agora) ^ set(BASELINE_G103)),))
    for nome in sorted(set(agora) | set(BASELINE_G103)):
        if agora.get(nome) != BASELINE_G103.get(nome):
            lados.append("G103 mudou em %r: conhecido %r, agora %r. Cura "
                         "muda o baseline junto; gap novo nao some "
                         "no conhecido."
                         % (nome, BASELINE_G103.get(nome), agora.get(nome)))
    assert not lados, "baseline G103 reprova:\n" + "\n".join(lados)


def test_03_vermelho_por_injecao_via_tmp_path(tmp_path):
    """Disciplina nova sem prancha deixa a suite vermelha; o caso bom fica
    verde. A copia mora em tmp_path (convenção 2: o repo vivo nunca e
    mutado)."""
    quadros = _quadros()
    caminho = tmp_path / "executadas_galpao.json"
    caminho.write_text(json.dumps(quadros["galpao"]["executadas"]),
                       encoding="utf-8")
    copia = list(json.loads(caminho.read_text(encoding="utf-8")))
    pranchas = dict(quadros["galpao"]["pranchas"])
    # caso bom: as executadas vivas fecham com a isencao escrita
    bom = lente.conferir_disciplina_prancha(
        copia, pranchas, lente.ISENCOES_DISCIPLINA_PRANCHA)
    assert bom["OK"] and bom["isentas"] == ["mezanino"], bom
    # injecao 1: disciplina nova sem prancha vira sem_prancha
    copia.append("ancoragem_orbital")
    quebrado = lente.conferir_disciplina_prancha(
        copia, pranchas, lente.ISENCOES_DISCIPLINA_PRANCHA)
    assert quebrado["sem_prancha"] == ["ancoragem_orbital"] \
        and not quebrado["OK"], quebrado
    # injecao 2 (outro sentido): motivo apagado e silencio, nao triagem -
    # o mezanino volta a sem_prancha
    apagado = lente.conferir_disciplina_prancha(
        quadros["galpao"]["executadas"], pranchas, {"mezanino": "   "})
    assert apagado["sem_prancha"] == ["mezanino"] \
        and not apagado["OK"], apagado
    # injecao 3 (outro sentido): cobertura sumida - a fundacao sem o
    # concreto que a cobre vira sem_prancha
    sem_cobertura = {d: v for d, v in pranchas.items() if d != "concreto"}
    descoberta = lente.conferir_disciplina_prancha(["fundacao"],
                                                   sem_cobertura, {})
    assert descoberta["sem_prancha"] == ["fundacao"] \
        and not descoberta["OK"], descoberta
    assert tmp_path.is_dir()


def test_04_isencao_sem_motivo_reprova_e_malformada_grita():
    """Isencao sem motivo e silencio, nao triagem (a regra que derrubou o
    G77, e a unica que impede a lista de isentos de virar silencio).
    Entrada malformada (None) levanta: lente que devolve OK sobre lixo e
    saturacao silenciosa."""
    # G97: um assert so, com os tres lados na mesma mensagem.
    lados = []
    vazia = lente.conferir_disciplina_prancha(
        ["mezanino"], _pranchas(), {"mezanino": ""})
    if vazia["sem_prancha"] != ["mezanino"] or vazia["OK"]:
        lados.append("isencao vazia devia reprovar: %r" % (vazia,))
    try:
        lente.conferir_disciplina_prancha(None, {}, {})
        lados.append("executadas None devia levantar TypeError")
    except TypeError:
        pass
    try:
        lente.conferir_disciplina_prancha([], None, {})
        lados.append("pranchas None devia levantar TypeError")
    except TypeError:
        pass
    assert not lados, "isencao/malformada reprova:\n" + "\n".join(lados)


def test_05_fontes_independentes_das_executadas():
    """Assercao nao-tautologica (convenção 5): as executadas que as funcoes
    vivas devolvem sao comparadas com a conta feita a mao a partir do
    codigo-fonte (DISCIPLINAS, _DISCIPLINAS_DO_EDIFICIO, _PRANCHAS).

    Se uma fonte viva encolher em silencio, este teste acusa mesmo com a
    lente verde."""
    import galpao_turnkey as tk
    import pacote_legal as pl

    # G97: um assert so, com os quatro lados na mesma mensagem.
    lados = []
    if list(tk.DISCIPLINAS) != ["concreto", "aco", "eletrico", "incendio",
                                "climatizacao", "hidraulica", "mezanino"]:
        lados.append("DISCIPLINAS do turnkey mudou: %r" % (list(tk.DISCIPLINAS),))
    if set(_executadas_galpao()) != set(tk.DISCIPLINAS):
        lados.append("executadas do galpao derivam de outra fonte: %r"
                     % (_executadas_galpao(),))
    if set(_executadas_casa()) != {"arquitetura", "concreto",
                                   "alvenaria_estrutural", "hidraulica",
                                   "eletrico", "madeira"}:
        lados.append("executadas da casa (uniao) mudou: %r"
                     % (_executadas_casa(),))
    if set(_executadas_predio()) != {"concreto", "incendio", "hidraulica",
                                     "eletrico"}:
        lados.append("executadas do predio (uniao) mudou: %r"
                     % (_executadas_predio(),))
    for d in list(_executadas_galpao()) + _executadas_casa() \
            + _executadas_predio():
        if d not in pl._PRANCHAS \
                and d not in lente.ISENCOES_DISCIPLINA_PRANCHA \
                and d not in lente.COBERTA_POR:
            lados.append("executada %r sem prancha, sem isencao e sem "
                         "cobertura: %r" % (d, sorted(pl._PRANCHAS)))
    if not str(lente.ISENCOES_DISCIPLINA_PRANCHA.get("mezanino") or ""
               ).strip():
        lados.append("isencao do mezanino sem motivo escrito")
    assert not lados, "fontes independentes reprovam:\n" + "\n".join(lados)
