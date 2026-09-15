"""G112 - o carimbo do galpao usa um codigo e o indice usa outro.

Medido (G106): o carimbo das pranchas do galpao
(techdraw_hidraulica.py:32,49, techdraw_incendio.py:48,65,
techdraw_climatizacao.py:27,43, e a rota SVG do G104 em
prancha_svg_direta.PRANCHAS) diz PE-HID-01/02, PE-INC-01/02, PE-CLI-01/02,
enquanto o indice (pacote_legal._PRANCHAS) promete PE-HI-01..03,
PE-IN-01..03, PE-CL-01. Nao e so o prefixo: PE-HI-02 no indice e
"Esgoto/ventilacao", e PE-HID-02 no carimbo e o quadro de
dimensionamento. O mesmo numero designa folhas diferentes.

O que foi MEDIDO nesta entrega (G112, via AST - ast.parse, nunca
substring; arquivo emitido = nome da pagina + ".pdf"):
  aco (techdraw_exec.py): PE01_COBERTURA/PE-01 (:662-663),
    PE02_FUNDACOES/PE-02 (:689-690,:695-696), PE03_ELEVACOES/PE-03
    (:740-741), PE04_PORTICO/PE-04 (:807-808),
    PE05_CONTRAVENTAMENTO/PE-05 (:846-847,:861-862),
    PE06_DET_BASE/PE-06 (:895-896,:933-934), PE07_DET_JOELHO/PE-07
    (:1100-1101,:1109-1110), PE08_FECHAMENTO/PE-08 (:1423-1424,:1434-1435),
    PE09_QUADROS/PE-09 (:1518-1519), PE14_CROQUIS/PE-14 (:1669-1670),
    PE16_MONTAGEM/PE-16 (:1737-1738). PE15_DET_BLOCO (:1008-1009) carimba
    "-" (sem literal de carimbo) e a chamada generica (:1341, page_name
    variavel) nao contam;
   concreto do galpao (techdraw_concreto.py:84-168): PE01_FORMAS/PE-01
     (:84-85), PE02_PORTICO/PE-02 (:116-117), PE03_QUADROS/PE-03
     (:138-139), PE04_LOCACAO_FUNDACAO/PE-04 do G140 (:167-169, via AST
     de techdraw_concreto);
   mezanino do galpao (techdraw_mezanino.py): MZ01_MEZANINO/MZ-01 do G146
     (via AST de techdraw_mezanino);
  eletrico (techdraw_eletrico.py): PE01_UNIFILAR/PE-EL-01 (:46),
    PE02_PLANTA_INST/PE-EL-02 (:66), PE03_PLANTA_INFRA/PE-EL-03 (:88),
    PE04_QUADROS/PE-EL-04 (:110);
  coordenacao (techdraw_coordenacao.py): COORD01_PLANTA/PE-COORD-01
    (:43-44), COORD02_CLASH/PE-COORD-02 (:60-61);
  hidraulica/incendio/climatizacao (rota SVG viva,
    prancha_svg_direta.ARQUIVOS :44-48 + PRANCHAS :50-54, mesmos basenames
    das paginas FreeCAD techdraw_hidraulica.py:30-31,47-48,
    techdraw_incendio.py:46-47,63-64 + INC03_DETALHES/PE-INC-03 do G138
    (:84-86, via AST de techdraw_incendio),
    techdraw_climatizacao.py:25-26,41-42):
    HID01_ESQUEMA/PE-HID-01, HID02_QUADRO/PE-HID-02,
    INC01_PLANTA/PE-INC-01, INC02_RESUMO/PE-INC-02,
    INC03_DETALHES/PE-INC-03 (G138),
    CLI01_ESQUEMA/PE-CLI-01, CLI02_QUADRO/PE-CLI-02.

Entregue:
  1. LENTE (varredura_carimbo_mapa.py, funcao pura): inverte o mapa para
     arquivo->{codigos} e cobra que todo carimbo de um arquivo pertenca
     ao conjunto do mapa. Nao reescreve confere_folha_svg nem o censo do
     G77 (codigo no carimbo, nao conteudo).
  2. PORTAO (test_01): a lente sobre as TRES tipologias com os mapas vivos,
     os carimbos extraidos vivos e as isencoes escritas do galpao, um
     assert so (receita do G97) - verde COM triagem, nunca com a lente
     enfraquecida (sem isencoes o galpao reprova como antes).
  3. BASELINE (test_02, nos dois sentidos): a lista de isentas congelada -
     cura muda o baseline junto; gap novo ou isencao que some sem triagem
     = vermelho.
  4. INJECAO (test_03, tmp_path, nunca mutando o repo): carimbo trocado
     sem isencao e isencao de motivo apagado deixam a suite vermelha; o
     caso bom fica verde.
  5. TABELA (test_06): cada gap cru tem entrada na CORRESPONDENCIA_G112 e
     vice-versa; a secao do cliente sai no .md com correspondencia e some
     por default (byte-identico); o emissor do pacote passa a fonte unica
     (pacote_legal.CORRESPONDENCIA_NUMERACAO_GALPAO, G113 - era um espelho).

O que a lente NAO cobre (molde DIVIDA-LENTE do G51): conteudo/geometria
da folha (confere_folha_svg + censo do G77, nao esta lente); arquivos sem
literal de carimbo extraivel saem em sem_carimbo_informativo e NAO afetam
o OK (nao-coverture declarada).

Veredito G112 (segundo ramo do goal: numeracao propria + tabela): os
carimbos ficam - o executivo numera por arquivo de producao e o indice por
disciplina (razao verbatim em
varredura_carimbo_mapa.RAZAO_NUMERACAO_PROPRIA_G112); a tabela viaja no
pacote-legal.md do galpao e o portao e verde com as isencoes escritas.
"""
import ast
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import varredura_carimbo_mapa as lente


def _pares_nova_prancha_carimbo(nome_modulo):
    """Extrai {pagina.pdf: carimbo} de um techdraw_* via AST (nunca substring).

    Para cada chamada `_nova_prancha(doc, "NOME", _carimbo*(cfg, titulo,
    "NUMERO", ...))`, o arquivo emitido e NOME + ".pdf" e o carimbo e o
    terceiro argumento posicional do _carimbo* (assinatura cfg, titulo,
    numero, escala, folha em techdraw_exec.py:622, techdraw_concreto.py:41,
    techdraw_eletrico.py:26, techdraw_coordenacao.py:25). Pagina variavel
    (Name, nao Constant) e numero "-" / vazio nao contam: sem literal de
    carimbo extraivel."""
    caminho = os.path.join(GALPAO, nome_modulo + ".py")
    with open(caminho, encoding="utf-8") as f:
        arvore = ast.parse(f.read())
    pares = {}
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        fn = getattr(no.func, "attr", None) or getattr(no.func, "id", None)
        if fn != "_nova_prancha" or len(no.args) < 3:
            continue
        pagina = no.args[1]
        if not (isinstance(pagina, ast.Constant)
                and isinstance(pagina.value, str) and pagina.value.strip()):
            continue
        carimbo = no.args[2]
        if not (isinstance(carimbo, ast.Call) and len(carimbo.args) >= 3):
            continue
        cfn = getattr(carimbo.func, "attr", None) \
            or getattr(carimbo.func, "id", None)
        if not (isinstance(cfn, str) and cfn.startswith("_carimbo")):
            continue
        numero = carimbo.args[2]
        if not (isinstance(numero, ast.Constant)
                and isinstance(numero.value, str)):
            continue
        codigo = numero.value.strip()
        if not codigo or codigo == "-":
            continue
        pares.setdefault(pagina.value.strip() + ".pdf", set()).add(codigo)
    return {arquivo: sorted(codigos) for arquivo, codigos in pares.items()}


def _mapa_galpao():
    """O mapa vivo do galpao (fonte viva: galpao_adapter)."""
    import galpao_adapter as ga

    return dict(ga._PRANCHA_ARQUIVO_GALPAO)


def _mapa_casa():
    """O mapa vivo da casa (fonte viva: casa_residencial)."""
    import casa_residencial as casa

    return dict(casa._PRANCHA_ARQUIVO_CASA)


def _mapa_predio():
    """O mapa vivo do predio (fonte viva: edificio_adapter)."""
    import edificio_adapter as ed

    return dict(ed._PRANCHA_ARQUIVO)


def _carimbos_galpao():
    """Os carimbos vivos do galpao: AST sobre os techdraw_* + rota SVG viva.

    Nunca copia hard-code: cada lado vem do dict vivo do modulo. A rota
    SVG (prancha_svg_direta.ARQUIVOS + PRANCHAS) usa os mesmos basenames
    das paginas FreeCAD e carimba os mesmos codigos onde se sobrepoe
    (HID01/INC01/CLI01) - a fusao une os conjuntos."""
    import prancha_svg_direta as direta

    saida = {}
    for modulo in ("techdraw_exec", "techdraw_concreto", "techdraw_eletrico",
                   "techdraw_incendio", "techdraw_coordenacao",
                   "techdraw_mezanino"):
        for arquivo, codigos in _pares_nova_prancha_carimbo(modulo).items():
            saida.setdefault(arquivo, set()).update(codigos)
    for disciplina in direta.DISCIPLINAS:
        for base, codigo in zip(direta.ARQUIVOS[disciplina],
                                direta.PRANCHAS[disciplina]):
            saida.setdefault(base + ".pdf", set()).add(codigo)
    return {arquivo: sorted(codigos) for arquivo, codigos in saida.items()}


def _carimbos_casa():
    """A casa emite .svg cujos emissores desenho_* nao publicam literal de
    carimbo extraivel (medido G112: so desenho_hidraulica.py:143-146 tem
    literais PE-HI-*, e e cobertura N:1 do galpao, nao carimbo de folha).
    Nao-coverture declarada: dict vazio, tudo cai em
    sem_carimbo_informativo sem afetar o OK."""
    return {}


def _carimbos_predio():
    """O predio emite .svg sem literal de carimbo extraivel (mesma medida
    da casa). Nao-coverture declarada."""
    return {}


def _quadros():
    return {"casa": {"mapa": _mapa_casa(), "carimbos": _carimbos_casa(),
                     "isencoes": {}},
            "galpao": {"mapa": _mapa_galpao(),
                       "carimbos": _carimbos_galpao(),
                       "isencoes": dict(lente.ISENCOES_CARIMBO_MAPA)},
            "predio": {"mapa": _mapa_predio(),
                       "carimbos": _carimbos_predio(),
                       "isencoes": {}}}


def _resultados(quadros=None, sem_isencoes=False):
    """Aplica a lente as tres tipologias. Com sem_isencoes=True a lente crua
    (prova de que o verde do portao vem da triagem escrita, nunca da lente
    enfraquecida)."""
    quadros = quadros if quadros is not None else _quadros()
    return {nome: lente.conferir_carimbo_mapa(
        q["mapa"], q["carimbos"],
        None if sem_isencoes else q.get("isencoes"))
        for nome, q in quadros.items()}


# BASELINE_G112 (medido 2026-09-11, enderecos no cabecalho acima; G137 em
# 2026-09-14 move 8 do aco de arquivo_sem_mapa para fora_do_mapa — ganharam
# codigo PE-ES-04..09,14,15 no mapa, mas o carimbo de producao PE-02..PE-16
# segue distinto do codigo do indice, logo a numeracao propria permanece e
# a tabela/isencoes seguem com 22 entradas, so com o cobre atualizado
# (G138: 23, +INC03_DETALHES com cobre [PE-IN-02]);
# G139 move COORD02_CLASH de arquivo_sem_mapa para fora_do_mapa — ganhou o
# codigo PE-CD-02 no mapa, mas o carimbo de producao PE-COORD-02 segue
# distinto do codigo do indice (cada folha emitida tem codigo, mesma regra
# do G137); G138 move INC03_DETALHES para fora_do_mapa com esperado
# [PE-IN-02] — ganhou emissor ligado (techdraw_incendio._pr_detalhes) e
# cobertura 1:1 na tabela; isentas 22 -> 23):
# G140 move PE04_LOCACAO_FUNDACAO para fora_do_mapa com esperado
# [PE-CO-04] — ganhou emissor ligado (techdraw_concreto._pr_locacao) e
# cobertura 1:1 na tabela, mesma regra do G137/G138/G139; isentas 23
# -> 24):
# G146 move MZ01_MEZANINO para fora_do_mapa com esperado [PE-MZ-01] —
# ganhou emissor ligado (techdraw_mezanino._pr_mezanino, formas + armacao
# via desenho_pavimento adaptado) e cobertura 1:1 na tabela, mesma regra;
# o carimbo de producao (MZ-01) segue distinto do codigo do indice
# (PE-MZ-01); isentas 24 -> 25):
#   fora_do_mapa (22): os 21 de antes + MZ01_MEZANINO/MZ-01
#     ({PE-MZ-01}; G146: o mezanino calculado ganha folha ligada);
#   fora_do_mapa (21): os 20 de antes + PE04_LOCACAO_FUNDACAO/PE-04
#     ({PE-CO-04}; G140: a locacao da fundacao do galpao ganha emissor
#     ligado e cobertura 1:1 na tabela, mesma regra do G137/G139);
#   arquivo_sem_mapa (3): CLI02_QUADRO, HID02_QUADRO,
#     INC02_RESUMO (quadros sem codigo proprio, como antes);
# casa e predio: sem literal de carimbo extraivel, gaps vazios. Entrada
# nova aqui = cura de um lado (a tabela MUDA junto, nunca em silencio);
# gap novo que coincida com estes e o defeito voltando. Nenhum carimbo foi
# corrigido nesta entrega (segundo ramo do goal: numeracao propria + tabela
# que o cliente recebe).
BASELINE_G112 = {
    "casa": {"fora_do_mapa": [], "arquivo_sem_mapa": []},
    "galpao": {
        "fora_do_mapa": [
            ["CLI01_ESQUEMA.pdf", "PE-CLI-01", ["PE-CL-01"]],
            ["COORD01_PLANTA.pdf", "PE-COORD-01", ["PE-CD-01"]],
            ["COORD02_CLASH.pdf", "PE-COORD-02", ["PE-CD-02"]],
            ["HID01_ESQUEMA.pdf", "PE-HID-01",
             ["PE-HI-01", "PE-HI-02", "PE-HI-03"]],
            ["INC01_PLANTA.pdf", "PE-INC-01", ["PE-IN-01"]],
            ["INC03_DETALHES.pdf", "PE-INC-03", ["PE-IN-02"]],
            ["MZ01_MEZANINO.pdf", "MZ-01", ["PE-MZ-01"]],
            ["PE01_COBERTURA.pdf", "PE-01", ["PE-ES-03"]],
            ["PE01_FORMAS.pdf", "PE-01", ["PE-CO-01"]],
            ["PE02_FUNDACOES.pdf", "PE-02", ["PE-ES-04"]],
            ["PE02_PORTICO.pdf", "PE-02", ["PE-CO-02"]],
            ["PE03_ELEVACOES.pdf", "PE-03", ["PE-ES-05"]],
            ["PE03_QUADROS.pdf", "PE-03", ["PE-CO-03"]],
            ["PE04_LOCACAO_FUNDACAO.pdf", "PE-04", ["PE-CO-04"]],
            ["PE04_PORTICO.pdf", "PE-04", ["PE-ES-01"]],
            ["PE05_CONTRAVENTAMENTO.pdf", "PE-05", ["PE-ES-06"]],
            ["PE06_DET_BASE.pdf", "PE-06", ["PE-ES-07"]],
            ["PE07_DET_JOELHO.pdf", "PE-07", ["PE-ES-02"]],
            ["PE08_FECHAMENTO.pdf", "PE-08", ["PE-ES-08"]],
            ["PE09_QUADROS.pdf", "PE-09", ["PE-ES-09"]],
            ["PE14_CROQUIS.pdf", "PE-14", ["PE-ES-14"]],
            ["PE16_MONTAGEM.pdf", "PE-16", ["PE-ES-15"]],
        ],
        "arquivo_sem_mapa": [
            "CLI02_QUADRO.pdf",
            "HID02_QUADRO.pdf",
            "INC02_RESUMO.pdf",
        ],
    },
    "predio": {"fora_do_mapa": [], "arquivo_sem_mapa": []},
}


# BASELINE_ISENTAS_G112: as isentas congeladas - o galpao tria os 25
# arquivos da tabela com motivo escrito (G138: +INC03_DETALHES; G140:
# +PE04_LOCACAO_FUNDACAO; G146: +MZ01_MEZANINO); casa e
# triar: sem literal de carimbo extraivel). Cura muda o baseline junto;
# isencao que some sem triagem = vermelho (o gap cru reaparece no test_01).
BASELINE_ISENTAS_G112 = {
    "casa": [],
    "galpao": [
        "CLI01_ESQUEMA.pdf",
        "CLI02_QUADRO.pdf",
        "COORD01_PLANTA.pdf",
        "COORD02_CLASH.pdf",
        "HID01_ESQUEMA.pdf",
        "HID02_QUADRO.pdf",
        "INC01_PLANTA.pdf",
        "INC02_RESUMO.pdf",
        "INC03_DETALHES.pdf",
        "MZ01_MEZANINO.pdf",
        "PE01_COBERTURA.pdf",
        "PE01_FORMAS.pdf",
        "PE02_FUNDACOES.pdf",
        "PE02_PORTICO.pdf",
        "PE03_ELEVACOES.pdf",
        "PE03_QUADROS.pdf",
        "PE04_LOCACAO_FUNDACAO.pdf",
        "PE04_PORTICO.pdf",
        "PE05_CONTRAVENTAMENTO.pdf",
        "PE06_DET_BASE.pdf",
        "PE07_DET_JOELHO.pdf",
        "PE08_FECHAMENTO.pdf",
        "PE09_QUADROS.pdf",
        "PE14_CROQUIS.pdf",
        "PE16_MONTAGEM.pdf",
    ],
    "predio": [],
}


def test_01_portao_tres_tipologias_falha_unica():
    """O portao: as tres tipologias, todos os lados, um assert so.

    Verde COM as isencoes escritas (a tabela que o cliente recebe): as tres
    tipologias OK e as isentas do galpao iguais as congeladas. A prova de
    que o verde vem da triagem - e nao da lente enfraquecida - e que a lente
    crua (sem isencoes) reprova o galpao exatamente no baseline cru
    (receita do G97: coletar tudo, relatar tudo, um assert)."""
    quadros = _quadros()
    resultados = _resultados(quadros)
    crus = _resultados(quadros, sem_isencoes=True)
    cru_galpao = {"fora_do_mapa": [list(t)
                                   for t in crus["galpao"]["fora_do_mapa"]],
                  "arquivo_sem_mapa": list(
                      crus["galpao"]["arquivo_sem_mapa"])}
    lados = []
    for nome in sorted(resultados):
        r = resultados[nome]
        if not r["OK"]:
            lados.append("tipologia %r nao OK (G112)" % (nome,))
        if list(r.get("isentas") or []) != BASELINE_ISENTAS_G112[nome]:
            lados.append("isentas de %r mudaram: conhecido %r, agora %r"
                         % (nome, BASELINE_ISENTAS_G112[nome],
                            list(r.get("isentas") or [])))
    if cru_galpao != BASELINE_G112["galpao"]:
        lados.append("lente crua mudou: a triagem esconderia o novo estado; "
                     "conhecido %r, agora %r"
                     % (BASELINE_G112["galpao"], cru_galpao))
    assert not lados, ("portao G112 reprova:\n%s\n%s"
                       % ("\n".join(lados),
                          lente.relatorio_pt(resultados)))


def test_02_baseline_g112_nos_dois_sentidos():
    """Sem baseline congelado nos dois sentidos a lente e relatorio, nao
    portao: isencao que sumisse sem triagem faria o gap cru sumir junto com
    a suite verde."""
    agora = {n: list(r.get("isentas") or [])
             for n, r in _resultados().items()}
    # G97: um assert so, com tipologia nova e isentas por tipologia na mesma
    # mensagem. O assert de tipologia escondia os gaps seguintes.
    lados = []
    if set(agora) != set(BASELINE_ISENTAS_G112):
        lados.append("tipologia nova sem triagem G112: %r"
                     % (sorted(set(agora) ^ set(BASELINE_ISENTAS_G112)),))
    for nome in sorted(set(agora) | set(BASELINE_ISENTAS_G112)):
        if agora.get(nome) != BASELINE_ISENTAS_G112.get(nome):
            lados.append("G112 mudou em %r: conhecido %r, agora %r. Cura "
                         "muda o baseline junto; isencao nova nao some "
                         "no conhecido."
                         % (nome, BASELINE_ISENTAS_G112.get(nome),
                            agora.get(nome)))
    assert not lados, "baseline G112 reprova:\n" + "\n".join(lados)


def test_03_vermelho_por_injecao_via_tmp_path(tmp_path):
    """Carimbo trocado sem isencao e isencao de motivo apagado deixam a
    suite vermelha; o caso bom fica verde. A copia mora em tmp_path
    (convenção 2: o repo vivo nunca e mutado)."""
    quadros = _quadros()
    mapa_el = {c: quadros["galpao"]["mapa"][c]
               for c in ("PE-EL-01", "PE-EL-02", "PE-EL-03", "PE-EL-04")}
    carimbos_el = {a: quadros["galpao"]["carimbos"][a]
                   for a in ("PE01_UNIFILAR.pdf", "PE02_PLANTA_INST.pdf",
                             "PE03_PLANTA_INFRA.pdf", "PE04_QUADROS.pdf")}
    caminho = tmp_path / "carimbos_eletrico.json"
    caminho.write_text(json.dumps(carimbos_el, sort_keys=True),
                       encoding="utf-8")
    copia = {a: list(c) for a, c
             in json.loads(caminho.read_text(encoding="utf-8")).items()}
    # G97: um assert so, com os tres lados na mesma mensagem.
    lados = []
    # caso bom: o recorte eletrico 1:1 fecha verde
    bom = lente.conferir_carimbo_mapa(mapa_el, copia)
    if not bom["OK"] or bom["fora_do_mapa"] != []:
        lados.append("caso bom devia fechar verde: %r" % (bom,))
    # injecao 1: carimbo trocado de arquivo vira fora_do_mapa
    copia["PE01_UNIFILAR.pdf"] = ["PE-EL-02"]
    quebrado = lente.conferir_carimbo_mapa(mapa_el, copia)
    if quebrado["fora_do_mapa"] != [
            ("PE01_UNIFILAR.pdf", "PE-EL-02", ["PE-EL-01"])] \
            or quebrado["OK"]:
        lados.append("carimbo trocado devia reprovar: %r" % (quebrado,))
    # injecao 2 (outro sentido): isencao de motivo apagado e silencio, nao
    # triagem - o trocado continua fora_do_mapa e some das isentas
    apagado = lente.conferir_carimbo_mapa(
        mapa_el, copia, {"PE01_UNIFILAR.pdf": "   "})
    if apagado["fora_do_mapa"] != [
            ("PE01_UNIFILAR.pdf", "PE-EL-02", ["PE-EL-01"])] \
            or apagado["isentas"] != [] or apagado["OK"]:
        lados.append("motivo apagado devia reprovar: %r" % (apagado,))
    if not tmp_path.is_dir():
        lados.append("tmp_path sumiu")
    assert not lados, "injecao G112 reprova:\n" + "\n".join(lados)


def test_04_informativo_sem_motivo_e_malformada_grita():
    """Arquivo sem literal de carimbo e ausencia declarada (informativo,
    sem forjar OK nem gap); entrada malformada (None/nao-dict) levanta:
    lente que devolve OK sobre lixo e saturacao silenciosa."""
    # G97: um assert so, com os quatro lados na mesma mensagem.
    lados = []
    vazio = lente.conferir_carimbo_mapa({"PE-EL-01": "a.pdf"},
                                        {"a.pdf": []})
    if not vazio["OK"] or vazio["sem_carimbo_informativo"] != ["a.pdf"] \
            or vazio["fora_do_mapa"] or vazio["arquivo_sem_mapa"]:
        lados.append("lista vazia devia ser informativo sem afetar OK: %r"
                     % (vazio,))
    try:
        lente.conferir_carimbo_mapa(None, {})
        lados.append("mapa None devia levantar TypeError")
    except TypeError:
        pass
    try:
        lente.conferir_carimbo_mapa({}, None)
        lados.append("carimbos None devia levantar TypeError")
    except TypeError:
        pass
    try:
        lente.conferir_carimbo_mapa(["PE-EL-01"], {})
        lados.append("mapa nao-dict devia levantar TypeError")
    except TypeError:
        pass
    assert not lados, "informativo/malformada reprova:\n" + "\n".join(lados)


def test_05_fontes_independentes_dos_carimbos():
    """Assercao nao-tautologica (convenção 5): as fontes vivas sao
    confrontadas com literais escritos a mao a partir do codigo-fonte.

    Se uma fonte viva encolher em silencio, este teste acusa mesmo com a
    lente verde."""
    import galpao_adapter as ga
    import casa_residencial as casa
    import edificio_adapter as ed
    import pacote_legal as pl
    import prancha_svg_direta as direta

    # G97: um assert so, com todos os lados na mesma mensagem.
    lados = []
    if dict(direta.PRANCHAS) != {
            "hidraulica": ("PE-HID-01", "PE-HID-02"),
            "incendio": ("PE-INC-01", "PE-INC-02"),
            "climatizacao": ("PE-CLI-01", "PE-CLI-02")}:
        lados.append("PRANCHAS da rota SVG mudou: %r" % (direta.PRANCHAS,))
    if dict(direta.ARQUIVOS) != {
            "hidraulica": ("HID01_ESQUEMA", "HID02_QUADRO"),
            "incendio": ("INC01_PLANTA", "INC02_RESUMO"),
            "climatizacao": ("CLI01_ESQUEMA", "CLI02_QUADRO")}:
        lados.append("ARQUIVOS da rota SVG mudou: %r" % (direta.ARQUIVOS,))
    if [pl._PRANCHAS[d][0] for d in
            ("hidraulica", "incendio", "climatizacao", "aco", "concreto",
             "eletrico", "coordenacao")] != [
            "PE-HI", "PE-IN", "PE-CL", "PE-ES", "PE-CO", "PE-EL", "PE-CD"]:
        lados.append("prefixos do indice mudaram: %r"
                     % ({d: pl._PRANCHAS[d][0] for d in pl._PRANCHAS},))
    if len(ga._PRANCHA_ARQUIVO_GALPAO) != 35:
        lados.append("mapa do galpao encolheu/cresceu: %d entradas (G141: 35)"
                     % (len(ga._PRANCHA_ARQUIVO_GALPAO),))
    if len(casa._PRANCHA_ARQUIVO_CASA) != 17:
        lados.append("mapa da casa encolheu/cresceu: %d entradas"
                     % (len(casa._PRANCHA_ARQUIVO_CASA),))
    if len(ed._PRANCHA_ARQUIVO) != 15:
        lados.append("mapa do predio encolheu/cresceu: %d entradas"
                     % (len(ed._PRANCHA_ARQUIVO),))
    pares_aco = _pares_nova_prancha_carimbo("techdraw_exec")
    if len(pares_aco) != 11:
        lados.append("paginas de aco com carimbo mudaram: %r" % (pares_aco,))
    if pares_aco.get("PE04_PORTICO.pdf") != ["PE-04"]:
        lados.append("carimbo do portico de aco mudou: %r" % (pares_aco,))
    pares_conc = _pares_nova_prancha_carimbo("techdraw_concreto")
    if pares_conc != {"PE01_FORMAS.pdf": ["PE-01"],
                      "PE02_PORTICO.pdf": ["PE-02"],
                      "PE03_QUADROS.pdf": ["PE-03"],
                      # G140: a locacao ganha emissor ligado
                      "PE04_LOCACAO_FUNDACAO.pdf": ["PE-04"]}:
        lados.append("carimbos do concreto mudaram: %r" % (pares_conc,))
    pares_ele = _pares_nova_prancha_carimbo("techdraw_eletrico")
    if pares_ele != {"PE01_UNIFILAR.pdf": ["PE-EL-01"],
                     "PE02_PLANTA_INST.pdf": ["PE-EL-02"],
                     "PE03_PLANTA_INFRA.pdf": ["PE-EL-03"],
                     "PE04_QUADROS.pdf": ["PE-EL-04"]}:
        lados.append("carimbos do eletrico mudaram: %r" % (pares_ele,))
    pares_coord = _pares_nova_prancha_carimbo("techdraw_coordenacao")
    if pares_coord != {"COORD01_PLANTA.pdf": ["PE-COORD-01"],
                       "COORD02_CLASH.pdf": ["PE-COORD-02"]}:
        lados.append("carimbos da coordenacao mudaram: %r" % (pares_coord,))
    pares_inc = _pares_nova_prancha_carimbo("techdraw_incendio")
    if pares_inc != {"INC01_PLANTA.pdf": ["PE-INC-01"],
                     "INC02_RESUMO.pdf": ["PE-INC-02"],
                     "INC03_DETALHES.pdf": ["PE-INC-03"]}:
        lados.append("carimbos do incendio mudaram: %r" % (pares_inc,))
    pares_mz = _pares_nova_prancha_carimbo("techdraw_mezanino")
    if pares_mz != {"MZ01_MEZANINO.pdf": ["MZ-01"]}:
        lados.append("carimbos do mezanino mudaram: %r" % (pares_mz,))
    codigos = [p["codigo"] for p in
               pl.indice_de_pranchas(["hidraulica", "incendio",
                                      "climatizacao"])]
    if codigos != ["PE-HI-01", "PE-HI-02", "PE-HI-03", "PE-IN-01",
                   "PE-IN-02", "PE-IN-03", "PE-CL-01"]:
        lados.append("indice hid/inc/cli mudou: %r" % (codigos,))
    if len(lente.CORRESPONDENCIA_G112) != 25:
        lados.append("tabela G112 encolheu/cresceu: %d entradas (G146: 25)"
                     % (len(lente.CORRESPONDENCIA_G112),))
    if set(lente.ISENCOES_CARIMBO_MAPA) != set(
            BASELINE_ISENTAS_G112["galpao"]):
        lados.append("isencoes do galpao divergem da tabela: %r"
                     % (sorted(lente.ISENCOES_CARIMBO_MAPA),))
    for frase in ("PE-HID-02 colide em numero com PE-HI-02",
                  "convencao 6",
                  "PE01_FORMAS.pdf do concreto e PE01_COBERTURA.pdf do aco"):
        if frase not in lente.RAZAO_NUMERACAO_PROPRIA_G112:
            lados.append("razao G112 perdeu a frase %r" % (frase,))
    assert not lados, "fontes independentes reprovam:\n" + "\n".join(lados)


def test_06_tabela_baseline_markdown_espelho():
    """A tabela que o cliente recebe cobre exatamente os gaps crus (cada gap
    cru tem entrada e vice-versa); a secao sai no .md com correspondencia e
    some por default (byte-identico); o espelho de producao e igual a
    canonica (o packager nao pode importar a lente: SCRIPT AVULSO)."""
    import pacote_legal as pl
    import entregaveis_projeto as ep

    # G97: um assert so, com os quatro lados na mesma mensagem.
    lados = []
    crus = _resultados(sem_isencoes=True)["galpao"]
    # fora_do_mapa: (arquivo, carimbo); arquivo_sem_mapa: (arquivo, carimbo
    # do extrato vivo) - a comparacao usa o carimbo medido nos dois lados.
    carimbos = _quadros()["galpao"]["carimbos"]
    esperados_tabela = set()
    for e in lente.CORRESPONDENCIA_G112:
        medidos = carimbos.get(e["arquivo"], [])
        esperados_tabela.add((e["arquivo"], medidos[0] if medidos else None))
    crus_com_carimbo = set()
    for a, c, _ in crus["fora_do_mapa"]:
        crus_com_carimbo.add((a, c))
    for a in crus["arquivo_sem_mapa"]:
        medidos = carimbos.get(a, [])
        crus_com_carimbo.add((a, medidos[0] if medidos else None))
    if crus_com_carimbo != esperados_tabela:
        lados.append("tabela<>baseline divergem: so no cru %r, so na tabela "
                     "%r" % (sorted(crus_com_carimbo - esperados_tabela),
                             sorted(esperados_tabela - crus_com_carimbo)))
    for e in lente.CORRESPONDENCIA_G112:
        if not str(e.get("motivo") or "").strip():
            lados.append("entrada sem motivo escrito: %r" % (e,))
        if e["arquivo"] not in carimbos:
            lados.append("entrada sem carimbo medido no extrato: %r" % (e,))
    if set(lente.ISENCOES_CARIMBO_MAPA) != {e["arquivo"]
                                            for e in
                                            lente.CORRESPONDENCIA_G112}:
        lados.append("isencoes divergem da tabela")
    pac = pl.gerar_pacote(["eletrico"])
    md_sem = pl.markdown(pac)
    md_padrao = pl.markdown(pac, correspondencia=None)
    if md_sem != md_padrao:
        lados.append("default correspondencia=None mudou a saida")
    # G113: fonte unica em pacote_legal; a lente a importa e o emissor do
    # pacote a passa ao markdown - conferir que o emissor usa ESSA fonte.
    import inspect
    if "pl.CORRESPONDENCIA_NUMERACAO_GALPAO" not in inspect.getsource(
            ep.emitir_pacote_legal):
        lados.append("emitir_pacote_legal nao passa a fonte unica")
    espelho = pl.CORRESPONDENCIA_NUMERACAO_GALPAO
    canonica = {"intro": lente.RAZAO_NUMERACAO_PROPRIA_G112,
                "entradas": lente.CORRESPONDENCIA_G112}
    if espelho != canonica:
        lados.append("espelho de producao diverge da canonica")
    md_com = pl.markdown(pac, correspondencia=espelho)
    if "## Correspondencia de numeracao do executivo (G112)" not in md_com:
        lados.append("secao G112 ausente no .md com correspondencia")
    for e in lente.CORRESPONDENCIA_G112:
        if e["arquivo"] not in md_com or (e.get("carimbo") or "") not in md_com:
            lados.append("entrada fora do .md do cliente: %r" % (e,))
    if lente.RAZAO_NUMERACAO_PROPRIA_G112 not in md_com:
        lados.append("razao G112 ausente no .md do cliente")
    if "## Correspondencia" in md_sem:
        lados.append("secao G112 vazou no default sem correspondencia")
    assert not lados, "tabela/markdown/espelho reprovam:\n" + "\n".join(lados)
