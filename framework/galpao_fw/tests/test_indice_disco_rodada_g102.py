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
freecad.exe no PATH da rodada): casa=2.7s predio=35.7s galpao=923.0s
total=961.4s. G107: o galpao passa a rodar com generate_2d=True (as tres
de esquema saem pela rota SVG e PE-HI/PE-IN/PE-CL sao confrontados com o
disco de verdade); o custo do galpao sobe pelos dois `tk.rodar` (turnkey
+ caderno, o segundo do montar_caderno) sobre o spec 44x90 de dois vaos.
Total abaixo do teto de 1800s: roda no CI.
G114 (2026-09-12): `montar_caderno(..., R=turnkey_result)` reusa o turnkey
do adaptador e nao recalcula — um `tk.rodar` so, contado por injecao em
`tests/test_caderno_reuso_turnkey_g114.py` (com R: zero chamadas; sem R:
uma; mesmo `n_pranchas`/`disciplinas`/`ATENDE`).
G121 (2026-09-12): remedicao integral com a maquina livre em corrida
isolada com -s (8 GB, ~2,5 GB livres, sem orfao): casa=2.4s predio=28.9s
galpao=1048.3s total=1079.5s, 6 passed. O galpao segue acima dos 923 s de
antes do reuso (variacao de maquina/rodada, nao regressao do reuso: o
total 1079,5 s fica abaixo dos 1230 s da corrida limpa pos-G114 do G119).
Pico de memoria junto (MedidorPico): casa=107,0 predio=143,6
galpao=1988,8 MB (pytest 174,4 + freecad.exe 1819,7, um por vez) - o teto
de 2500 MB por rodada mora no CUSTO_TETO_MEM_MB com o motivo escrito.

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
    # G107: o galpao sem freecad.exe emite as tres de esquema pela rota
    # SVG-direta (G104), duas folhas cada (esquema + quadro). A primeira
    # cobre os codigos do indice (N:1 no mapa); a segunda e folha legitima
    # da disciplina, sem codigo proprio no indice.
    "HID02_QUADRO.pdf":
        "segunda folha da hidraulica do galpao (quadro de "
        "dimensionamento e memorial, rota SVG G104), "
        "sem codigo proprio no indice",
    "INC02_RESUMO.pdf":
        "segunda folha do incendio do galpao (quadro-resumo e memorial, "
        "rota SVG G104), sem codigo proprio no indice",
    "CLI02_QUADRO.pdf":
        "segunda folha da climatizacao do galpao (quadro de capacidade "
        "e memorial, rota SVG G104), sem codigo proprio no indice",
}

# Custo medido e escrito (aceite do G102): segundos por tipologia na
# maquina de desenvolvimento, generate_ifc desligado. O test_01 imprime o
# custo de cada rodada; o test_05 trava este registro. Se o portao ficar
# mais lento que o teto, ele reprova em vez de apodrecer em silencio.
CUSTO_MEDIDO_SEG = {"casa": 2.4, "predio": 28.9, "galpao": 1048.3}
CUSTO_MEDIDO_EM = "2026-09-12"
CUSTO_TETO_SEG = 1800

# G121: o teto do portao media so tempo, e o que matava era memoria (G113:
# quatro mortes sem o tempo chegar perto do teto; D145). O portao agora
# mede tambem o PICO DE MEMORIA residente de cada rodada - o processo
# pytest/Python mais a soma dos freecad.exe visiveis - via o medidor da
# producao (medicao_memoria.MedidorPico, fonte unica, stdlib-only). O
# test_01 imprime o pico junto com os segundos; o test_05 trava o registro;
# o test_07 prova o vermelho por injecao. Medido em 2026-09-12 em corrida
# isolada com -s (maquina de 8 GB, ~2,5 GB livres, sem processo orfao):
# o galpao mora no freecad.exe (1819,7 de 1988,8 MB); casa/predio nao
# sobem freecad.exe (rota SVG pura).
CUSTO_MEDIDO_MEM_MB = {"casa": 107.0, "predio": 143.6, "galpao": 1988.8}
CUSTO_MEDIDO_MEM_EM = "2026-09-12"
# Teto de memoria: 2500 MB por rodada (pico medido 1988,8 + ~25 % de
# folga). Motivo, como o teto de tempo tem: a maquina tem 8 GB e o SO +
# fundo comem ~2 GB; o teto deixa a rodada respirar e ainda reprova
# vazamento, freecad orfao concorrente ou disciplina nova que suba outro
# freecad junto (n_freecad_max sai no print para auditar). Picos nao se
# somam entre tipologias (cada rodada e um processo proprio): o teto vale
# por rodada, nao no total.
CUSTO_TETO_MEM_MB = 2500
# G125 (auditoria do G121): quantos freecad.exe cada rodada sobe, medido na
# mesma corrida oficial (n_freecad_max). A rodada que ve MENOS que isto nao
# mediu o processo que carrega o pico (acesso negado, nome trocado) - e o
# pico "cabe no teto" por nao ter visto o freecad. Mais que isto o teto ja
# pega (freecad orfao concorrente).
CUSTO_MEDIDO_N_FREECAD = {"casa": 0, "predio": 0, "galpao": 1}

TIPOLOGIAS = ("casa", "predio", "galpao")

_SPECS = {
    "casa": ("casa-residencial", "project-spec.json"),
    "predio": ("edificio-multipavimento", "project-spec.json"),
    "galpao": ("galpao-tp-g95", "project-spec.json"),
}

_OPCOES = {
    "casa": {"generate_ifc": False, "generate_2d": True},
    "predio": {"generate_ifc": False, "generate_2d": True},
    # G107: o galpao roda com generate_2d=True — as tres de esquema saem
    # pela rota SVG sem freecad.exe e PE-HI/PE-IN/PE-CL sao confrontados
    # com o disco de verdade (antes, generate_2d=False media so indice x
    # mapa no galpao, D130).
    "galpao": {"generate_ifc": False, "generate_2d": True},
}


def _spec(nome):
    pasta, arquivo = _SPECS[nome]
    with open(os.path.join(REPO, "projects", pasta, arquivo),
              encoding="utf-8") as fh:
        return json.load(fh)


def _rodada(nome, tmp_path):
    """Roda a tipologia de verdade no spec persistido (fonte independente).

    Devolve (manifesto, resultado, destino, segundos, pico_mem). O resultado
    e o adapter-result.json quando o adaptador o escreve; para o galpao
    (hook de relatorio proprio) e None e os executados saem do manifesto.
    O pico_mem e o resumo do medicao_memoria.MedidorPico amostrado durante
    o run_project (G121: processo + freecad.exe na mesma amostra).
    """
    import medicao_memoria as _mm
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    destino = str(tmp_path / ("run-" + nome))
    medidor = _mm.MedidorPico(intervalo_s=1.0)
    inicio = time.perf_counter()
    medidor.start()
    try:
        manifesto = run_project(_spec(nome), destino, dict(_OPCOES[nome]))
    finally:
        segundos = time.perf_counter() - inicio
        pico_mem = medidor.stop()
    caminho = os.path.join(destino, "reports", "adapter-result.json")
    resultado = None
    if os.path.isfile(caminho):
        with open(caminho, encoding="utf-8") as fh:
            resultado = json.load(fh)
    return manifesto, resultado, destino, segundos, pico_mem


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
    import galpao_adapter as ga

    executadas = [n for n, rec in (manifesto.get("disciplines") or {}).items()
                  if isinstance(rec, dict) and rec.get("status") != "blocked"]
    discos = [d for d in tk.DISCIPLINAS
              if d in pl._PRANCHAS and d in executadas] + ["coordenacao"]
    # A promessa e a MESMA fonte do laco do adaptador (G93 + fronteira da
    # escada G101): sem escada declarada PE-IN-03 sai dispensada, nao
    # prometida. Cobrar o codigo aqui seria o portao brigando com o laco.
    indice, _dispensadas = ga._indice_galpao_com_fronteira(
        discos, {"raw_spec": _spec("galpao"),
                 "turnkey_spec": _spec("galpao").get("turnkey", {})})
    return (sorted(f["codigo"] for f in indice), list(discos))


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
    # G91, nao desta rodada. Nome morto de disciplina prometida e gap —
    # salvo quando a fronteira da tipologia dispensou o codigo por escrito
    # (G101: PE-IN-03 sem escada sai dispensada, nao prometida; o mapa
    # continua cobrindo o caso com escada).
    dispensados = {d.get("codigo")
                   for d in (desenhos.get("dispensadas") or [])
                   if isinstance(d, dict)}
    for codigo in res["sobrando"]:
        if codigo in dispensados:
            continue
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
    import medicao_memoria as mm
    import varredura_indice_disco as lente

    gaps = []
    custos = {}
    picos = {}
    resultados = {}
    mapas = {}
    prometidos_por = {}
    vistos = set()
    for nome in TIPOLOGIAS:
        manifesto, _resultado, destino, segundos, pico = _rodada(nome, tmp_path)
        custos[nome] = segundos
        picos[nome] = pico
        desenhos = (manifesto.get("deliverables") or {}).get("drawings")
        if not desenhos:
            gaps.append("%s: deliverable drawings ausente no manifesto "
                        "(nem emitido nem declarado)" % nome)
            continue
        lado, res, no_disco, mapa, prometidos, _discs = _confronta(
            nome, manifesto, destino, desenhos)
        gaps.extend("[%s] %s" % (nome, g) for g in lado)
        if nome == "galpao" and "PE-IN-03" not in prometidos:
            disp = [d.get("codigo")
                    for d in (desenhos.get("dispensadas") or [])]
            if "PE-IN-03" not in disp:
                gaps.append("[galpao] PE-IN-03 fora do indice sem dispensa "
                            "escrita (fronteira G101): %r"
                            % (desenhos.get("dispensadas"),))
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
    # G121: o pico de memoria sai no print junto com os segundos (aceite).
    # pico_total = max por amostra de (processo + freecad) - nao a soma dos
    # picos. Sem -s o pytest engole este print: a rodada oficial que congela
    # o registro roda com -s em corrida isolada.
    print("MEM_G102 " + " ".join(
        "%s=%.1fMB(proc=%.1f,fc=%.1f,n=%d)" % (
            n, picos[n]["pico_total_mb"], picos[n]["pico_processo_mb"],
            picos[n]["pico_freecad_mb"], picos[n]["n_freecad_max"])
        for n in TIPOLOGIAS))
    # G106: o teto cobra o tempo MEDIDO nesta rodada. O test_05 so conferia
    # a constante escrita a mao - portao que nunca mede nao reprova nada.
    if total > CUSTO_TETO_SEG:
        gaps.append("custo medido %.1fs estoura o teto %ss (CI)"
                    % (total, CUSTO_TETO_SEG))
    # G121: o teto de memoria cobra o pico MEDIDO nesta rodada, por
    # tipologia (cada rodada e um processo proprio; picos nao se somam).
    # Pico None/nao mensuravel nao vira gap - a ausencia se declara no
    # print acima, nunca vira aprovacao silenciosa nem teto inventado.
    if CUSTO_TETO_MEM_MB is not None:
        for nome in TIPOLOGIAS:
            if picos[nome]["falhou"] or picos[nome]["n_amostras"] == 0:
                gaps.append("[%s] medidor de memoria falhou: pico nao "
                            "mensuravel, sem numero para cobrar (G121)"
                            % nome)
                continue
            if not picos[nome].get("freecad_mensuravel", False):
                gaps.append("[%s] freecad.exe nao mensuravel em %d de %d "
                            "amostras: o pico nao inclui o processo que "
                            "carrega a rodada (G125)" % (
                                nome, picos[nome]["n_amostras_sem_freecad"],
                                picos[nome]["n_amostras"]))
                continue
            if picos[nome]["n_freecad_max"] < CUSTO_MEDIDO_N_FREECAD[nome]:
                gaps.append("[%s] a rodada viu %d freecad.exe, a medida "
                            "oficial viu %d: o pico nao inclui o processo "
                            "que carrega a rodada (G125)" % (
                                nome, picos[nome]["n_freecad_max"],
                                CUSTO_MEDIDO_N_FREECAD[nome]))
            falha = mm.veredito_memoria(picos[nome]["pico_total_mb"],
                                        CUSTO_TETO_MEM_MB)
            if falha is not None:
                gaps.append("[%s] %s" % (nome, falha))
    else:
        print("MEM_G102 teto de memoria ainda nao congelado (G121)")
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
                               "conferencia-nbr5410.svg",
                               "HID02_QUADRO.pdf", "INC02_RESUMO.pdf",
                               "CLI02_QUADRO.pdf"}:
        lados.append("ISENCOES_EXTRA mudou sem triagem G102: %r"
                     % (sorted(ISENCOES_EXTRA),))
    for chave, motivo in sorted(ISENCOES_EXTRA.items()):
        if "sem codigo" not in motivo or "no indice" not in motivo:
            lados.append("isencao %r sem dizer que nao ha codigo: %r"
                         % (chave, motivo))
    # Fonte independente: as duas da casa saem do mesmo emissor
    # (gerar_desenhos_casa), nao do mapa; as tres do galpao saem da rota
    # SVG-direta (prancha_svg_direta.ARQUIVOS), nao do mapa — a isencao
    # nao deriva do proprio resultado que ela libera.
    import ast

    arvore = ast.parse(open(os.path.join(
        GALPAO, "desenho_casa_residencial.py"),
        encoding="utf-8").read())
    texto = ast.dump(arvore)
    import prancha_svg_direta as psd

    arquivos_svg = {base + ".pdf"
                    for par in psd.ARQUIVOS.values() for base in par}
    for chave in ISENCOES_EXTRA:
        if chave not in texto and chave not in arquivos_svg:
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
    manifesto, _resultado, destino, _s, _pico = _rodada("casa", tmp_path)
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
    estoura o teto reprova em vez de apodrecer em silencio. G121: o mesmo
    vale para o pico de memoria (CUSTO_MEDIDO_MEM_MB/CUSTO_TETO_MEM_MB)
    quando congelado; enquanto None, a ausencia segue declarada no
    test_01 e aqui nao cobra (o vermelho por injecao mora no test_07)."""
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
    if CUSTO_MEDIDO_MEM_MB is not None and CUSTO_TETO_MEM_MB is not None:
        for nome in TIPOLOGIAS:
            pico = CUSTO_MEDIDO_MEM_MB.get(nome)
            if not isinstance(pico, (int, float)) or pico <= 0:
                lados.append("pico de memoria de %r nao escrito: %r"
                             % (nome, pico))
            elif pico > CUSTO_TETO_MEM_MB:
                lados.append("pico de memoria de %r estoura o teto "
                             "(%s > %s)" % (nome, pico, CUSTO_TETO_MEM_MB))
    assert not lados, "custo G102 reprova:\n" + "\n".join(lados)


def test_07_memoria_teto_acusa_em_tmp_path(tmp_path):
    """G121: o teto de memoria consegue acusar (convencao 7 do lote).

    Roda a casa de verdade em tmp_path com o medidor ligado (a mais
    barata, ~3 s): o sampler tem de ter medido de verdade (amostras e pico
    do processo > 0 - medidor que diz zero por ser incapaz de acusar e o
    defeito do G117/D145). Sobre esse pico real, teto artificialmente baixo
    reprova e teto folgado passa - nos dois sentidos, sem mutar o repo."""
    import medicao_memoria as mm

    _manifesto, _resultado, _destino, _seg, pico = _rodada("casa", tmp_path)
    assert pico["n_amostras"] >= 2, pico
    assert not pico["falhou"], pico
    assert pico["pico_processo_mb"] > 0, pico
    assert pico["pico_total_mb"] >= pico["pico_processo_mb"], pico
    medido = pico["pico_total_mb"]
    baixo = mm.veredito_memoria(medido, 0.01)
    assert baixo is not None and "estoura o teto" in baixo, (medido, baixo)
    alto = mm.veredito_memoria(medido, medido + 10000.0)
    assert alto is None, (medido, alto)
    assert mm.veredito_memoria(None, 0.01) is None


def test_08_medidor_acusa_freecad_nao_mensuravel(monkeypatch):
    """G125 (auditoria do G121): o lado freecad do medidor consegue acusar.

    Antes, `memoria_freecad_mb` devolvendo (None, 0) virava 0,0 MB com
    `falhou` falso - o teto do galpao passava sem ter medido o freecad.exe
    (medido: pico 14,7 MB, falhou False). Injecao por monkeypatch (nunca
    mutando o repo): sem o freecad, `freecad_mensuravel` apaga; intacto, acende."""
    import medicao_memoria as mm

    intacto = mm.MedidorPico(intervalo_s=0.2)
    intacto.start()
    time.sleep(0.5)
    bom = intacto.stop()
    monkeypatch.setattr(mm, "memoria_freecad_mb", lambda: (None, 0))
    cego = mm.MedidorPico(intervalo_s=0.2)
    cego.start()
    time.sleep(0.5)
    ruim = cego.stop()
    quebras = []
    if not bom["freecad_mensuravel"]:
        quebras.append("medidor intacto nao mediu o freecad: %r" % bom)
    if ruim["freecad_mensuravel"] or ruim["n_amostras_sem_freecad"] < 2:
        quebras.append("freecad cego nao acusou: %r" % ruim)
    if ruim["falhou"] or ruim["pico_processo_mb"] <= 0:
        quebras.append("o lado do processo devia seguir medindo: %r" % ruim)
    if CUSTO_MEDIDO_N_FREECAD != {"casa": 0, "predio": 0, "galpao": 1}:
        quebras.append("registro de freecad por rodada mudou sem triagem: %r"
                       % CUSTO_MEDIDO_N_FREECAD)
    assert not quebras, "G125:\n" + "\n".join(quebras)
