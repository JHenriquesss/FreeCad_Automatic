"""G92 - a casa confronta o indice que ela promete, nao so o PE-AR.

Medido: `casa_residencial._emitir_desenhos` lia
`pl.indice_de_pranchas(["arquitetura"])` - 3 codigos, 3 mapeados, verde -
mas `gestao_casa.disciplinas_pacote` promete o pacote inteiro (16 sem
telhado, 15 sem alvenaria, 17 na uniao). Os demais evaporavam no
`continue` do indice com a suite verde (saturacao silenciosa, regra 4).

Entregue:
  1. o laco le a MESMA fonte do pacote (`gc.disciplinas_pacote`), nunca um
     recorte;
  2. `_PRANCHA_ARQUIVO_CASA` com os 17 codigos da uniao (o que ja sai
     noutro emissor do mesmo hook so ganha a entrada; HI e N:1 num esquema
     so, como o contrato G82 do galpao);
  3. cada folha sem emissor sai pulada com o dado que falta nomeado
     (`_motivo_folha_casa_nao_emitida`), nunca "nao disponivel" generico.

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em diretorio temporario (nunca mutando o repo),
parse do manifesto (existencia, nao geometria), saturacao silenciosa (um
por um, nao numero contra numero) e fonte independente (o spec persistido
e `_PRANCHAS`, nao o resultado).
"""
import copy
import json
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
REPO = os.path.dirname(os.path.dirname(GALPAO))

# Motivo sem o dado nomeado e silencio, nao triagem. Cada valor pulado tem
# de dizer O QUE falta (dado do spec/resultado) ou QUE nao ha emissor para
# aquela folha - nunca so "nao emitida". A mensagem generica antiga ("folha
# X nao emitida nesta rodada") nao tem nenhum destes marcadores e reprova.
AUSENCIA_NOMEADA = ("nao declarado", "nao declarados", "nao declarada",
                    "nao calculad", "nao dimensionada", "sem emissor",
                    "ausente", "not_available")

GENERicos = {"nao disponivel", "não disponível", "not available",
             "not_available", "indisponivel", "indisponível", "n/a",
             "sem dados", "ausente", "nao emitido", "nao emitida"}


def _norm(texto):
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", str(texto or ""))
        if not unicodedata.combining(c))
    return " ".join(sem_acento.replace("_", " ").strip().casefold().split())


def _spec():
    return json.loads(open(os.path.join(
        REPO, "projects", "casa-residencial", "project-spec.json"),
        encoding="utf-8").read())


def _rodada(tmp_path):
    """Roda a casa de verdade no spec persistido (fonte independente)."""
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    destino = str(tmp_path / "run")
    manifesto = run_project(_spec(), destino, {"generate_2d": True})
    resultado = json.loads(open(os.path.join(
        destino, "reports", "adapter-result.json"), encoding="utf-8").read())
    return manifesto, resultado, destino


def test_01_laco_cobre_o_pacote_inteiro_um_por_um(tmp_path):
    """Cada codigo prometido sai no disco ou sai nomeado - um por um.

    Numero contra numero (a conta de `pacote_no_manifesto`) fecharia com
    qualquer desenho a mais; aqui cada codigo tem arquivo no disco ou
    motivo escrito, e cada arquivo dito emitido existe de verdade (a
    sexta regra: "a folha esta certa" e "a folha sai" sao dois aceites).
    """
    import gestao_casa as gcasa
    import pacote_legal as pl
    import varredura_indice_disco as lente

    manifesto, resultado, destino = _rodada(tmp_path)
    desenhos = manifesto["deliverables"]["drawings"]
    prometidos = sorted(
        f["codigo"] for f in pl.indice_de_pranchas(
            gcasa.disciplinas_pacote(resultado)))
    artefatos = list(desenhos.get("artifacts") or [])
    no_disco = sorted(a.split("/", 1)[1] for a in artefatos)
    pulados = dict(desenhos.get("skipped") or {})
    gaps = []
    for codigo in prometidos:
        import casa_residencial as casa

        esperado = casa._PRANCHA_ARQUIVO_CASA.get(codigo)
        if not esperado:
            gaps.append("sem_mapa %s (laco sem entrada no mapa)" % codigo)
        elif esperado not in set(no_disco) | set(pulados):
            gaps.append("evaporou %s (-> %s sem arquivo e sem motivo)"
                        % (codigo, esperado))
        elif esperado in no_disco and not os.path.isfile(
                os.path.join(destino, "drawings", esperado)):
            gaps.append("manifesto mente %s (dito emitido, sem arquivo)"
                        % codigo)
    res = lente.conferir_indice_disco(
        prometidos, __import__("casa_residencial")._PRANCHA_ARQUIVO_CASA,
        no_disco, pulados)
    # Na rodada, o que vale e faltando/sem_mapa: o `sobrando` de disciplina
    # opcional (ex. PE-AL sem parede calculada) e higiene do portao G91 na
    # uniao, nao da rodada - o laco so confronta o que foi prometido.
    if res["faltando"] or res["sem_mapa"]:
        gaps.append("lente G91 acusa %r" % (res,))
    assert not gaps, (
        "G92: %d codigo(s) do pacote sem folha e sem triagem:\n%s"
        % (len(gaps), "\n".join("  - " + g for g in gaps)))


def test_02_nenhum_motivo_generico(tmp_path):
    """Motivo sem o dado nomeado e silencio, nao triagem.

    Cada pulado diz o que falta (dado do spec/resultado) ou que nao ha
    emissor ligado para aquela folha. A mensagem generica do laco antigo
    ("folha X nao emitida nesta rodada") reprova aqui: nomeia o titulo,
    mas nao o dado que falta.
    """
    manifesto, _resultado, _destino = _rodada(tmp_path)
    pulados = dict(manifesto["deliverables"]["drawings"].get("skipped") or {})
    gaps = []
    assert pulados, "rodada sem nenhum pulado: esperado PE-AR-01/03 e as sem emissor"
    for nome, motivo in sorted(pulados.items()):
        texto = _norm(motivo)
        if not texto:
            gaps.append("%s com motivo vazio (silencio)" % nome)
        elif texto in GENERicos:
            gaps.append("%s com motivo generico %r" % (nome, motivo))
        elif not any(m in texto for m in AUSENCIA_NOMEADA):
            gaps.append("%s sem o dado nomeado: %r" % (nome, motivo))
    assert not gaps, (
        "G92: %d motivo(s) generico(s):\n%s"
        % (len(gaps), "\n".join("  - " + g for g in gaps)))


def test_03_vermelho_por_injecao_via_tmp_path(tmp_path):
    """Estreitar de volta para ["arquitetura"] (ou podar o mapa) acusa.

    O defeito mora numa copia em `tmp_path` (convencao 2: o repo vivo
    nunca e mutado). Nos dois sentidos: prometidos estreitos com mapa
    cheio viram `sobrando`; mapa podado com prometidos cheios vira
    `sem_mapa`. O caso bom (cheio com cheio) fica verde.
    """
    import casa_residencial as casa
    import gestao_casa as gcasa
    import pacote_legal as pl
    import varredura_indice_disco as lente

    resultado = {
        "arquitetura": {"totais": {}},
        "estrutura": {"fundacao": {"ok": True}, "alvenaria": {"ok": True},
                      "telhado": {"geometria_nos": {"N1": [0.0, 0.0]}}},
        "hidraulica": {"ok": True},
        "eletrico": {"circuits": {"layout_validation": {}}},
    }
    cheios = sorted(f["codigo"] for f in pl.indice_de_pranchas(
        gcasa.disciplinas_pacote(resultado)))
    mapa = dict(casa._PRANCHA_ARQUIVO_CASA)
    disco = sorted(set(mapa.values()))
    gaps = []
    bom = lente.conferir_indice_disco(cheios, mapa, disco, {})
    if not bom["OK"]:
        gaps.append("caso bom devia fechar 17/17: %r" % (bom,))
    estreitos = sorted(
        f["codigo"] for f in pl.indice_de_pranchas(["arquitetura"]))
    recorte = lente.conferir_indice_disco(estreitos, mapa, disco, {})
    if recorte["OK"] or len(recorte["sobrando"]) != len(mapa) - 3:
        gaps.append("recorte ['arquitetura'] devia acusar %d sobrando: %r"
                    % (len(mapa) - 3, recorte))
    caminho = tmp_path / "mapa_casa.json"
    caminho.write_text(json.dumps(mapa), encoding="utf-8")
    podado = dict(json.loads(caminho.read_text(encoding="utf-8")))
    for codigo in list(podado):
        if not codigo.startswith("PE-AR-"):
            del podado[codigo]
    furado = lente.conferir_indice_disco(cheios, podado, disco, {})
    esperados = sorted(c for c in cheios if not c.startswith("PE-AR-"))
    if furado["OK"] or furado["sem_mapa"] != esperados:
        gaps.append("mapa podado devia acusar sem_mapa %r: %r"
                    % (esperados, furado))
    assert not gaps, (
        "G92 injecao:\n%s" % "\n".join("  - " + g for g in gaps))


def test_04_promessa_segue_o_resultado_fonte_unica(tmp_path):
    """A promessa segue `disciplinas_pacote(result)`: sem eletrico
    calculado, PE-EL nao e prometido e o laco nao o tria; com ele, tria.

    Prova comportamental da fonte unica (anti-tautologia: o laco e
    confrontado com uma variacao do resultado, nao com ele mesmo).
    """
    import casa_residencial as casa

    opt = type("O", (), {"generate_2d": True, "generate_caderno": False})()
    sem_ele = {"arquitetura": None, "estrutura": None, "hidraulica": None,
               "eletrico": None}
    manifesto = {"artifacts": [], "deliverables": {}}
    casa._emitir_desenhos(manifesto, str(tmp_path / "a"), {}, opt,
                          copy.deepcopy(sem_ele))
    pulados_sem = dict(
        manifesto["deliverables"]["drawings"].get("skipped") or {})
    com_ele = {"arquitetura": None, "estrutura": None, "hidraulica": None,
               "eletrico": {"circuits": {"layout_validation": {}}}}
    manifesto2 = {"artifacts": [], "deliverables": {}}
    casa._emitir_desenhos(manifesto2, str(tmp_path / "b"), {}, opt,
                          copy.deepcopy(com_ele))
    pulados_com = dict(
        manifesto2["deliverables"]["drawings"].get("skipped") or {})
    tem_el = [casa._PRANCHA_ARQUIVO_CASA[c] for c in
              ("PE-EL-01", "PE-EL-02", "PE-EL-03", "PE-EL-04")]
    gaps = []
    if any(n in pulados_sem for n in tem_el):
        gaps.append("sem eletrico calculado o laco triou PE-EL: %r"
                    % (sorted(set(tem_el) & set(pulados_sem)),))
    if any(n not in pulados_com for n in tem_el):
        gaps.append("com eletrico calculado falta triagem PE-EL: %r"
                    % (sorted(set(tem_el) - set(pulados_com)),))
    assert not gaps, (
        "G92 fonte unica:\n%s" % "\n".join("  - " + g for g in gaps))
