"""G102 - o portao do G91 mede indice x MAPA; este mede indice x DISCO.

Medido (G98): em tests/test_indice_disco_g91.py os tres quadros montam
"disco" como sorted(mapa.values()) — o lado do disco deriva do proprio
mapa, entao `faltando` nunca pode disparar. Aquele portao mede indice x
mapa (sem_mapa e sobrando sao reais e uteis), nao o que o nome promete.
A divisao que o G102 pede, sem renomear o arquivo (o nome esta travado
pela lista PORTOES_G97 em test_asserts_sequencia_g97.py): o G91 fica como
portao indice x mapa, e ESTE arquivo e o portao indice x disco sobre
rodada de verdade.

Entregue:
  1. rodada real das tres tipologias (specs de projects/, generate_ifc
     desligado) confrontada com o MANIFESTO da rodada — prometidos do
     resultado vivo, disco de deliverables.drawings.artifacts, motivos de
     skipped — via a lente do G91 estendida com o quarto lado;
  2. o quarto lado na lente: `extra_no_disco` — arquivo emitido que nenhum
     codigo reivindica. Cada extra sai isento com motivo escrito
     (ISENCOES_EXTRA, folha de conferencia interna e legitima) ou e gap;
  3. "a folha sai" (convencao 6): cada artefato dito emitido existe no
     disco e tem entrada em manifest["artifacts"]; ausencia de desenhos
     (galpao sem freecad.exe) so passa declarada (status + detalhe), nunca
     em silencio.

CUSTO_MEDIDO (2026-09-11, maquina de desenvolvimento Windows, sem
freecad.exe no PATH da rodada): casa=1.9s predio=34.8s galpao=38.5s
total=75.2s. O galpao roda com generate_2d/caderno desligados (a via
TechDraw exige freecad.exe com GUI e custa ~15min): a ausencia de
pranchas sai declarada no manifesto e o um-por-um sem FreeCAD e do laco
G93. Total abaixo do teto de 1800s: roda no CI.

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em diretorio temporario (nunca mutando o repo),
parse do manifesto (existencia, nao geometria), saturacao silenciosa (um
por um, nao numero contra numero) e fonte independente (o spec persistido
e `_PRANCHAS`, nao o resultado).
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
REPO = os.path.dirname(os.path.dirname(GALPAO))

# Quarto lado: arquivo no disco que nenhum codigo reivindica. Folha de
# conferencia interna e legitima, mas so com isencao escrita — e a isencao
# diz que nao ha codigo ("sem codigo no indice"), nunca "nao disponivel"
# generico. Entrada nova aqui = folha nova sem triagem; chave sumindo com
# o arquivo ainda no disco = gap de volta (baseline nos dois sentidos, no
# test_01: isencao nao usada vira gap).
ISENCOES_EXTRA = {
    "quadro-ambientes.svg":
        "folha de conferencia interna da casa (programa de arquitetura), "
        "sem codigo no indice",
    "conferencia-nbr5410.svg":
        "folha de conferencia interna da casa (NBR 5410), "
        "sem codigo no indice",
}

# Custo medido e escrito (aceite do G102): segundos por tipologia na
# maquina de desenvolvimento, generate_ifc desligado. O test_01 imprime o
# custo de cada rodada; o test_05 trava este registro. Se o portao ficar
# mais lento que o teto, ele reprova em vez de apodrecer em silencio.
CUSTO_MEDIDO_SEG = {"casa": 1.9, "predio": 34.8, "galpao": 38.5}
CUSTO_MEDIDO_EM = "2026-09-11"
CUSTO_TETO_SEG = 1800

TIPOLOGIAS = ("casa", "predio", "galpao")

_SPECS = {
    "casa": ("casa-residencial", "project-spec.json"),
    "predio": ("edificio-multipavimento", "project-spec.json"),
    "galpao": ("galpao-tp-g95", "project-spec.json"),
}

_OPCOES = {
    "casa": {"generate_ifc": False, "generate_2d": True},
    "predio": {"generate_ifc": False, "generate_2d": True},
    "galpao": {"generate_ifc": False, "generate_2d": False,
               "generate_caderno": False},
}


def _spec(nome):
    pasta, arquivo = _SPECS[nome]
    with open(os.path.join(REPO, "projects", pasta, arquivo),
              encoding="utf-8") as fh:
        return json.load(fh)


def _rodada(nome, tmp_path):
    """Roda a tipologia de verdade no spec persistido (fonte independente).

    Devolve (manifesto, resultado, destino, segundos). O resultado e o
    adapter-result.json quando o adaptador o escreve; para o galpao (hook
    de relatorio proprio) e None e os executados saem do manifesto.
    """
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    destino = str(tmp_path / ("run-" + nome))
    inicio = time.perf_counter()
    manifesto = run_project(_spec(nome), destino, dict(_OPCOES[nome]))
    segundos = time.perf_counter() - inicio
    caminho = os.path.join(destino, "reports", "adapter-result.json")
    resultado = None
    if os.path.isfile(caminho):
        with open(caminho, encoding="utf-8") as fh:
            resultado = json.load(fh)
    return manifesto, resultado, destino, segundos


def _prometidos(nome, manifesto, resultado):
    """Codigos prometidos e disciplinas que os prometem, da fonte viva.

    A mesma fonte que o pacote usa (G92/G93): o laco da rodada so confronta
    o que a rodada promete. Devolve (codigos, disciplinas)."""
    import pacote_legal as pl

    if nome == "casa":
        import gestao_casa as gcasa

        discos = gcasa.disciplinas_pacote(resultado)
        return (sorted(f["codigo"] for f in pl.indice_de_pranchas(discos)),
                list(discos))
    if nome == "predio":
        import gestao_edificio as gedif

        discos = gedif.disciplinas_pacote(resultado) + ["coordenacao"]
        return (sorted(f["codigo"] for f in pl.indice_de_pranchas(discos)),
                list(discos))
    import galpao_turnkey as tk

    executadas = [n for n, rec in (manifesto.get("disciplines") or {}).items()
                  if isinstance(rec, dict) and rec.get("status") != "blocked"]
    discos = [d for d in tk.DISCIPLINAS
              if d in pl._PRANCHAS and d in executadas] + ["coordenacao"]
    return (sorted(f["codigo"] for f in pl.indice_de_pranchas(discos)),
            list(discos))


def _disciplina_do_codigo(codigo):
    """Disciplina dona do codigo pelo prefixo de _PRANCHAS; None se ignota."""
    import pacote_legal as pl

    for disciplina, (prefixo, _titulos) in pl._PRANCHAS.items():
        if codigo.startswith(prefixo + "-"):
            return disciplina
    return None


def _mapa(nome):
    if nome == "casa":
        import casa_residencial as casa

        return dict(casa._PRANCHA_ARQUIVO_CASA)
    if nome == "predio":
        import edificio_adapter as predio

        return dict(predio._PRANCHA_ARQUIVO)
    import galpao_adapter as ga

    return dict(ga._PRANCHA_ARQUIVO_GALPAO)


def _confronta(nome, manifesto, destino, desenhos):
    """Indice x manifesto de verdade. Devolve gaps, lens, disco, mapa."""
    import varredura_indice_disco as lente

    artefatos = list(desenhos.get("artifacts") or [])
    pulados = desenhos.get("skipped") or {}
    caminho = os.path.join(destino, "reports", "adapter-result.json")
    resultado = None
    if os.path.isfile(caminho):
        with open(caminho, encoding="utf-8") as fh:
            resultado = json.load(fh)
    prometidos, disciplinas = _prometidos(nome, manifesto, resultado)
    mapa = _mapa(nome)
    no_disco = [a.split("/", 1)[1] if "/" in a else a for a in artefatos]
    res = lente.conferir_indice_disco(
        prometidos, mapa, no_disco, pulados, ISENCOES_EXTRA)
    gaps = []
    for codigo in res["sem_mapa"]:
        gaps.append("sem_mapa %s (prometido sem entrada no mapa)" % codigo)
    # O mapa e da UNIAO (G92: a casa sem alvenaria promete 15 dos 17): o
    # sobrando de disciplina que a rodada nao prometeu e higiene do portao
    # G91, nao desta rodada. Nome morto de disciplina prometida e gap.
    for codigo in res["sobrando"]:
        dona = _disciplina_do_codigo(codigo)
        if dona is None or dona in disciplinas:
            gaps.append("sobrando %s (nome morto no mapa -> %s)"
                        % (codigo, mapa.get(codigo)))
    # Faltando sem motivo so passa com a ausencia declarada no manifesto:
    # o galpao sem freecad.exe nao emite prancha nenhuma, e isso sai como
    # status (not_available/not_requested), nunca como buraco silencioso.
    declarado = (desenhos.get("status") in ("not_available", "not_requested")
                 and (desenhos.get("detail") or desenhos.get("status")))
    for codigo in res["faltando"]:
        if declarado:
            continue
        gaps.append("faltando %s (-> %s sem arquivo e sem motivo)"
                    % (codigo, mapa.get(codigo)))
    for extra in res["extra_no_disco"]:
        gaps.append("extra_no_disco %s (emitido, sem codigo e sem isencao)"
                    % extra)
    registrados = {a.get("path") for a in manifesto.get("artifacts") or []}
    for artefato in artefatos:
        if not os.path.isfile(os.path.join(destino, artefato)):
            gaps.append("manifesto mente %s (dito emitido, sem arquivo)"
                        % artefato)
        elif artefato not in registrados:
            gaps.append("fora do manifesto %s (emitido sem entrada em "
                        "manifest[artifacts])" % artefato)
    return gaps, res, no_disco, mapa, prometidos, disciplinas


def test_01_portao_rodada_real_falha_unica(tmp_path):
    """As tres tipologias de verdade, todos os lados, um assert so.

    O disco vem do manifesto da rodada (nao do mapa): desligar o emissor
    faz o codigo voltar a faltando, e planta um arquivo fantasma faz o
    extra disparar (provado por injecao no test_03/test_04 sobre a mesma
    lente). O custo de cada rodada sai na mensagem (aceite do G102)."""
    import varredura_indice_disco as lente

    gaps = []
    custos = {}
    resultados = {}
    mapas = {}
    prometidos_por = {}
    vistos = set()
    for nome in TIPOLOGIAS:
        manifesto, _resultado, destino, segundos = _rodada(nome, tmp_path)
        custos[nome] = segundos
        desenhos = (manifesto.get("deliverables") or {}).get("drawings")
        if not desenhos:
            gaps.append("%s: deliverable drawings ausente no manifesto "
                        "(nem emitido nem declarado)" % nome)
            continue
        lado, res, no_disco, mapa, prometidos, _discs = _confronta(
            nome, manifesto, destino, desenhos)
        gaps.extend("[%s] %s" % (nome, g) for g in lado)
        resultados[nome] = res
        mapas[nome] = mapa
        prometidos_por[nome] = prometidos
        vistos.update(n.split("/")[-1] for n in no_disco)
    for chave in sorted(ISENCOES_EXTRA):
        if chave not in vistos:
            gaps.append("isencao morta %s (isenta sem arquivo no disco em "
                        "nenhuma rodada)" % chave)
    total = sum(custos.values())
    print("CUSTO_G102 " + " ".join("%s=%.1fs" % (n, custos[n])
                                   for n in TIPOLOGIAS)
          + " total=%.1fs" % total)
    # G106: o teto cobra o tempo MEDIDO nesta rodada. O test_05 so conferia
    # a constante escrita a mao - portao que nunca mede nao reprova nada.
    if total > CUSTO_TETO_SEG:
        gaps.append("custo medido %.1fs estoura o teto %ss (CI)"
                    % (total, CUSTO_TETO_SEG))
    assert not gaps, (
        "G102: indice x disco reprova em rodada real:\n%s\n%s"
        % ("\n".join("  - " + g for g in gaps),
           lente.relatorio_pt(resultados, mapas, prometidos_por)))


def test_02_baseline_extras_isentos_nos_dois_sentidos():
    """Isencao sem motivo reprova; motivo generico reprova; chave nova sem
    triagem reprova (o test_01 so aceita o que esta aqui)."""
    import varredura_indice_disco as lente

    lados = []
    if set(ISENCOES_EXTRA) != {"quadro-ambientes.svg",
                               "conferencia-nbr5410.svg"}:
        lados.append("ISENCOES_EXTRA mudou sem triagem G102: %r"
                     % (sorted(ISENCOES_EXTRA),))
    for chave, motivo in sorted(ISENCOES_EXTRA.items()):
        if "sem codigo no indice" not in motivo:
            lados.append("isencao %r sem dizer que nao ha codigo: %r"
                         % (chave, motivo))
    # Fonte independente: os dois arquivos saem do mesmo emissor
    # (gerar_desenhos_casa), nao do mapa — a isencao nao deriva do
    # proprio resultado que ela libera.
    import ast

    arvore = ast.parse(open(os.path.join(
        GALPAO, "desenho_casa_residencial.py"),
        encoding="utf-8").read())
    texto = ast.dump(arvore)
    for chave in ISENCOES_EXTRA:
        if chave not in texto:
            lados.append("isencao %r sem emissor na arvore (nome morto)"
                         % chave)
    # A lente com as isencoes congela o caso bom; sem elas, o extra volta.
    bom = lente.conferir_indice_disco(
        ["PE-AR-01"], {"PE-AR-01": "a.svg"},
        ["a.svg"] + sorted(ISENCOES_EXTRA), {}, ISENCOES_EXTRA)
    if not bom["OK"]:
        lados.append("caso bom com isencoes reprova: %r" % (bom,))
    sem_isencao = lente.conferir_indice_disco(
        ["PE-AR-01"], {"PE-AR-01": "a.svg"},
        ["a.svg"] + sorted(ISENCOES_EXTRA), {})
    if sem_isencao["extra_no_disco"] != sorted(ISENCOES_EXTRA):
        lados.append("sem isencao o extra nao volta: %r" % (sem_isencao,))
    assert not lados, "baseline de extras G102 reprova:\n" + "\n".join(lados)


def test_03_vermelho_por_injecao_faltando_via_tmp_path(tmp_path):
    """Tirar um arquivo do disco faz o codigo voltar a faltando; o caso
    bom fica verde. A copia mora em tmp_path (convencao 2: o repo vivo
    nunca e mutado)."""
    import json

    import varredura_indice_disco as lente

    mapa = _mapa("predio")
    prometidos = sorted(mapa)
    caminho = tmp_path / "disco_predio.json"
    caminho.write_text(json.dumps(sorted(set(mapa.values()))),
                       encoding="utf-8")
    disco_bom = list(json.loads(caminho.read_text(encoding="utf-8")))
    bom = lente.conferir_indice_disco(prometidos, mapa, disco_bom, {})
    assert bom["OK"], bom
    furado = [n for n in disco_bom if n != "fundacao-locacao-formas.svg"]
    quebrado = lente.conferir_indice_disco(prometidos, mapa, furado, {})
    assert quebrado["faltando"] == ["PE-CO-04"] \
        and not quebrado["OK"], quebrado


def test_04_vermelho_por_injecao_extra_via_tmp_path(tmp_path):
    """Plantar um arquivo que nenhum codigo reivindica faz o quarto lado
    disparar; isencao escrita libera, motivo em branco nao. Tudo em
    tmp_path (convencao 2)."""
    import json

    import varredura_indice_disco as lente

    mapa = _mapa("predio")
    prometidos = sorted(mapa)
    caminho = tmp_path / "disco_predio.json"
    caminho.write_text(json.dumps(sorted(set(mapa.values()))),
                       encoding="utf-8")
    plantado = list(json.loads(caminho.read_text(encoding="utf-8")))
    plantado.append("folha-fantasma.svg")
    fantasma = lente.conferir_indice_disco(prometidos, mapa, plantado, {})
    assert fantasma["extra_no_disco"] == ["folha-fantasma.svg"] \
        and not fantasma["OK"], fantasma
    apagada = lente.conferir_indice_disco(
        prometidos, mapa, plantado, {}, {"folha-fantasma.svg": "   "})
    assert apagada["extra_no_disco"] == ["folha-fantasma.svg"] \
        and not apagada["OK"], apagada
    isenta = lente.conferir_indice_disco(
        prometidos, mapa, plantado, {},
        {"folha-fantasma.svg": "folha de conferencia interna, "
                               "sem codigo no indice"})
    assert isenta["OK"], isenta


def test_06_vermelho_por_injecao_sobre_rodada_real(tmp_path):
    """G106: test_03/test_04 injetam sobre um disco derivado do mapa - a
    mesma forma do G91. Aqui a injecao e sobre uma RODADA REAL da casa
    (a mais barata, ~2 s), no tmp_path: apagar um arquivo dito emitido faz
    o manifesto mentir; registrar um artefato sem codigo faz o quarto lado
    disparar. O caso bom da mesma rodada fica verde.

    Nota medida: `faltando` nao dispara em rodada real de casa/predio - o
    laco do proprio adaptador nomeia todo arquivo ausente. O lado do disco
    que so a rodada real mede e este: manifesto x arquivo, e extra."""
    manifesto, _resultado, destino, _s = _rodada("casa", tmp_path)
    desenhos = manifesto["deliverables"]["drawings"]
    bom, _res, _d, _m, _p, _di = _confronta("casa", manifesto, destino,
                                             desenhos)
    assert not bom, bom
    alvo = "drawings/unifilar.svg"
    assert alvo in desenhos["artifacts"], desenhos["artifacts"]
    os.remove(os.path.join(destino, alvo))
    apagado, _res, _d, _m, _p, _di = _confronta("casa", manifesto, destino,
                                                 desenhos)
    assert any("manifesto mente " + alvo in g for g in apagado), apagado
    plantado = dict(desenhos)
    plantado["artifacts"] = list(desenhos["artifacts"]) + [
        "drawings/folha-fantasma.svg"]
    extra, _res, _d, _m, _p, _di = _confronta("casa", manifesto, destino,
                                               plantado)
    assert any("extra_no_disco folha-fantasma.svg" in g for g in extra), extra


def test_05_custo_medido_e_escrito():
    """O aceite do G102: o custo existe e esta escrito, dentro do teto.

    Os segundos saem do test_01 (rodada real, generate_ifc desligado) e
    sao transcritos para CUSTO_MEDIDO_SEG/CUSTO_MEDIDO_EM. Portao que
    estoura o teto reprova em vez de apodrecer em silencio."""
    lados = []
    if CUSTO_MEDIDO_EM is None:
        lados.append("custo ainda nao medido: rode o test_01 e transcreva "
                     "os segundos para CUSTO_MEDIDO_SEG/CUSTO_MEDIDO_EM")
    for nome in TIPOLOGIAS:
        valor = CUSTO_MEDIDO_SEG.get(nome)
        if not isinstance(valor, (int, float)) or valor <= 0:
            lados.append("custo de %r nao escrito: %r" % (nome, valor))
        elif valor > CUSTO_TETO_SEG:
            lados.append("custo de %r estoura o teto (%s > %s): roda no CI "
                         "ou so a mao?" % (nome, valor, CUSTO_TETO_SEG))
    assert not lados, "custo G102 reprova:\n" + "\n".join(lados)
