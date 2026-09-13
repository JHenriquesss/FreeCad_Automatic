# ============================================================================
# exigencias_nao_verificadas_g130.py - G130: AS 39 DIVIDAS QUE O CLIENTE NAO VE.
# MODULO DE PRODUCAO (fonte unica da aplicabilidade): o que o cliente recebe
# mora aqui; a lente e o teste importam daqui. (Uma fonte so - regra do lote.)
# A CLAUSULA e o MOTIVO moram em varredura_constantes_orfas.ORFAS_TRIADAS
# (fonte unica do G124); este modulo NAO os copia - os LE de la. O que mora
# aqui e so a APLICABILIDADE por tipologia (casa/predio/galpao), com o motivo
# escrito para cada nao-aplicacao. Rodado a mao/CI (python
# exigencias_nao_verificadas_g130.py) e pelo teste-guarda
# tests/test_exigencias_nao_verificadas_g130.py. IMPORTADO pela producao
# (pacote_legal) - por isso NAO e script avulso (ver test_alcancabilidade).
#
# O que foi MEDIDO (G125): ORFAS_TRIADAS tem 39 DIVIDAS com clausula -
# exigencias de norma escritas e nao verificadas; zero mencoes (nome,
# clausula ou "nao verificado") nos documentos entregues de rodada real de
# casa e predio (documentos/*.md). Nao medido: o galpao; quais se aplicam a
# cada tipologia (e o que este modulo declara).
#
# Maquina: TIPOLOGIAS (casa/predio/galpao; "edificio" e alias de "predio") +
# APLICABILIDADE (para cada chave de ORFAS_TRIADAS: o conjunto das
# tipologias onde a exigencia vale + o motivo escrito onde ela nao vale) +
# exigencias_para_tipologia / nao_aplicaveis_para_tipologia (leem
# ORFAS_TRIADAS ao vivo: divida nova sem triagem vira sem_triagem, nunca
# some em silencio) + linhas_markdown / markdown_secao (o que o pacote
# carimba) + contem_exigencia / confere_documento (portao por substring:
# nome da constante + endereco/clausula da fonte unica) +
# confere_aplicabilidade (baseline nos dois sentidos) +
# arquivos_que_importam_exigencias / confere_uso_exigencias (ninguem le por
# conta propria fora do esperado).
#
# Nao fazer do goal: implementar as verificacoes (cada uma e um goal
# proprio) nem ligar constante em conta para tira-la da lista. Este modulo
# so PUBLICA a divida; nenhuma conta o importa para calcular.
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - o CONTEUDO da clausula (mora em ORFAS_TRIADAS; aqui so a chave);
#   - dispensa condicional fina (ex.: guarda-corpo so onde houver
#     guarda-corpo, explosivo so onde houver area classificada): a linha do
#     pacote diz "quando houver", e a ausencia do sistema na tipologia vai
#     como nao-aplicacao com motivo - o refinamento por projeto e goal
#     proprio;
#   - o PDF do memorial (a declaracao mora no pacote-legal.md em texto,
#     que o portao confere).
# ============================================================================
"""Exigencias nao verificadas pelo framework (G130): aplicabilidade por tipologia."""

from __future__ import annotations

import ast
import pathlib

try:
    from varredura_constantes_orfas import ORFAS_TRIADAS as _ORFAS
except ImportError:  # uso isolado fora do pacote
    _ORFAS = {}

GALPAO = pathlib.Path(__file__).resolve().parent

# Tipologias do framework. "predio" e o nome vivo no repo (specs de
# projects/, _OPCOES do G102, _spec do G128); "edificio" e alias aceito na
# porta, nunca gravado.
TIPOLOGIAS = ("casa", "predio", "galpao")

_ALIAS = {"casa": "casa", "predio": "predio", "edificio": "predio",
          "galpao": "galpao"}

# Marca que o portao confere por substring (nunca regex sobre o markdown:
# a secao e texto corrido, mesmo molde do G123/G126).
MARCA_SECAO = "Exigências não verificadas pelo framework (G130)"
MARCA_ITEM = "não verificada pelo framework"

# Arquivos de producao que podem importar esta fonte unica (baseline nos
# dois sentidos: import novo sem triagem = leitura por conta propria;
# import que some = nome morto). So raiz *.py (nao tests/): teste que
# importa a lente nao e conta de producao. O pacote_legal e o unico leitor:
# gestao_casa/gestao_edificio/entregaveis_projeto so passam a string da
# tipologia (dito aqui para a ausencia nao parecer esquecimento).
LEITORES_ESPERADOS = frozenset({
    "exigencias_nao_verificadas_g130.py",
    "pacote_legal.py",
})


def normaliza_tipologia(tipologia):
    """Canoniza a tipologia (aceita "edificio" como alias de "predio").

    Desconhecida LEVANTA ValueError com a lista das validas (nunca vira
    outra tipologia em silencio). None nunca chega aqui (ver
    exigencias_para_tipologia): sem tipologia o pacote publica a uniao.
    """
    if not isinstance(tipologia, str):
        raise ValueError("tipologia deve ser uma de %s (recebido %r)"
                         % (", ".join(TIPOLOGIAS), tipologia))
    t = tipologia.strip().lower()
    if t not in _ALIAS:
        raise ValueError("tipologia desconhecida %r (use uma de: %s)"
                         % (tipologia, ", ".join(TIPOLOGIAS)))
    return _ALIAS[t]


# APLICABILIDADE (G130). Para cada chave de ORFAS_TRIADAS: onde a exigencia
# vale + por que nao vale onde nao vale. A clausula/motivo NAO sao copiados
# (moram em ORFAS_TRIADAS, fonte unica do G124). Chave nova em ORFAS sem
# entrada aqui vira sem_triagem (o portao reprova); entrada aqui sem chave
# em ORFAS vira morta (nome morto, licao do G98).
#
# Criterio (engenharia, nao execucao da rodada): a exigencia vale onde o
# SISTEMA existe na tipologia. Condicional fina ("quando houver
# guarda-corpo/area classificada") continua listada, com o "quando houver"
# na linha do pacote - sumir por refinamento de projeto e goal proprio.
APLICABILIDADE = {
    ("alvenaria_estrutural.py", "FVK_ARMADA_COEF"): (
        frozenset({"casa"}),
        {"predio": "edificio calculado e portico de concreto (alvenaria e vedacao, sem parede portante)",
         "galpao": "fechamento metalico (sem alvenaria portante)"}),
    ("alvenaria_estrutural.py", "FVK_ARMADA_RHO_TETO"): (
        frozenset({"casa"}),
        {"predio": "edificio calculado e portico de concreto (alvenaria e vedacao, sem parede portante)",
         "galpao": "fechamento metalico (sem alvenaria portante)"}),
    ("alvenaria_estrutural.py", "FVK_ARMADA_TAU0_MP"): (
        frozenset({"casa"}),
        {"predio": "edificio calculado e portico de concreto (alvenaria e vedacao, sem parede portante)",
         "galpao": "fechamento metalico (sem alvenaria portante)"}),
    ("alvenaria_estrutural.py", "FVK_ARMADA_TETO_MP"): (
        frozenset({"casa"}),
        {"predio": "edificio calculado e portico de concreto (alvenaria e vedacao, sem parede portante)",
         "galpao": "fechamento metalico (sem alvenaria portante)"}),
    ("aterramento_nbr15749.py", "R_MAX_EXPLOSIVO"): (
        frozenset({"casa", "predio", "galpao"}),
        {}),
    ("cargas_nbr6120.py", "Q_BORDA_GUARDA_CORPO"): (
        frozenset({"casa", "predio"}),
        {"galpao": "cobertura industrial sem borda habitacional com guarda-corpo (carga de cobertura e manutencao)"}),
    ("cargas_nbr6120.py", "Q_ELEMENTO_ISOLADO_COBERTURA"): (
        frozenset({"casa", "predio", "galpao"}),
        {}),
    ("condutores_nbr5410.py", "DV_TERMINAL_MAX"): (
        frozenset({"casa", "predio", "galpao"}),
        {}),
    ("desempenho_nbr15575.py", "COMB_FACHADA"): (
        frozenset({"casa", "predio"}),
        {"galpao": "NBR 15575 e desempenho de edificacao habitacional (galpao industrial nao e habitacional)"}),
    ("desempenho_nbr15575.py", "NOTA_B_TAB2"): (
        frozenset({"casa", "predio"}),
        {"galpao": "NBR 15575 e desempenho de edificacao habitacional (galpao industrial nao e habitacional)"}),
    ("deteccao_alarme_nbr17240.py", "AFASTAMENTO_PAREDE_MIN_M"): (
        frozenset({"predio", "galpao"}),
        {"casa": "casa unifamiliar do escopo sem sistema central de deteccao/alarme exigido"}),
    ("deteccao_alarme_nbr17240.py", "LINEAR_PAREDE_MAX_M"): (
        frozenset({"predio", "galpao"}),
        {"casa": "casa unifamiliar do escopo sem sistema central de deteccao/alarme exigido"}),
    ("deteccao_alarme_nbr17240.py", "RAIO_DETECTOR_M"): (
        frozenset({"predio", "galpao"}),
        {"casa": "casa unifamiliar do escopo sem sistema central de deteccao/alarme exigido"}),
    ("escada.py", "Q_CONCENTRADA"): (
        frozenset({"galpao"}),
        {"casa": "escada residencial de concreto/madeira (nao escada industrial em aco)",
         "predio": "escada de emergencia de concreto (nao escada industrial em aco)"}),
    ("fissuracao_nbr6118.py", "ETA1_ENTALHADA"): (
        frozenset({"casa", "predio", "galpao"}),
        {}),
    ("fissuracao_nbr6118.py", "ETA1_LISA"): (
        frozenset({"casa", "predio", "galpao"}),
        {}),
    ("fronteiras.py", "UNIDADE_TIPO_ENUM"): (
        frozenset({"casa", "predio", "galpao"}),
        {}),
    ("galpao_concreto.py", "PSI0_SOBRECARGA"): (
        frozenset({"galpao"}),
        {"casa": "combinacao do dimensiona_pilar_secao do galpao de concreto (casa usa estrutura_casa)",
         "predio": "combinacao do dimensiona_pilar_secao do galpao de concreto (predio usa fundacao_edificio/pavimento_tipo)"}),
    ("gusset_ligacao.py", "K_UMA_BORDA"): (
        frozenset({"galpao"}),
        {"casa": "sem ligacao gusset em bandeira (sem estrutura metalica com gusset)",
         "predio": "sem ligacao gusset em bandeira (estrutura de concreto)"}),
    ("hidraulica_edificio.py", "SOBREPRESSAO_TRANSIENTE_MAX_KPA"): (
        frozenset({"casa", "predio", "galpao"}),
        {}),
    ("hidraulica_predial.py", "P_DIN_MIN_REDE_KPA"): (
        frozenset({"casa", "predio", "galpao"}),
        {}),
    ("iluminacao_emergencia_nbr10898.py", "ESPACO_ALTO_MAX_M"): (
        frozenset({"predio", "galpao"}),
        {"casa": "casa unifamiliar do escopo sem sistema central de iluminacao de emergencia exigido"}),
    ("iluminacao_emergencia_nbr10898.py", "FLUXO_MIN_BALIZ_DUPLO_LM"): (
        frozenset({"predio", "galpao"}),
        {"casa": "casa unifamiliar do escopo sem sistema central de iluminacao de emergencia exigido"}),
    ("iluminacao_emergencia_nbr10898.py", "FLUXO_MIN_BALIZ_EXCLUSIVO_LM"): (
        frozenset({"predio", "galpao"}),
        {"casa": "casa unifamiliar do escopo sem sistema central de iluminacao de emergencia exigido"}),
    ("laje_concreto.py", "THETA_APOIO_LIM"): (
        frozenset({"casa", "predio"}),
        {"galpao": "galpao de portico sem laje de concreto (sem apoio com rotacao limite)"}),
    ("luminotecnica_nbr8995.py", "REFLETANCIA_PAREDE"): (
        frozenset({"galpao"}),
        {"casa": "modulo e projeto luminotecnico de galpao pelo metodo dos lumens (casa sem esse calculo)",
         "predio": "modulo e projeto luminotecnico de galpao pelo metodo dos lumens (predio sem esse calculo)"}),
    ("luminotecnica_nbr8995.py", "REFLETANCIA_PISO"): (
        frozenset({"galpao"}),
        {"casa": "modulo e projeto luminotecnico de galpao pelo metodo dos lumens (casa sem esse calculo)",
         "predio": "modulo e projeto luminotecnico de galpao pelo metodo dos lumens (predio sem esse calculo)"}),
    ("luminotecnica_nbr8995.py", "REFLETANCIA_TETO"): (
        frozenset({"galpao"}),
        {"casa": "modulo e projeto luminotecnico de galpao pelo metodo dos lumens (casa sem esse calculo)",
         "predio": "modulo e projeto luminotecnico de galpao pelo metodo dos lumens (predio sem esse calculo)"}),
    ("madeira_nbr7190.py", "GAMMA_W_ELS"): (
        frozenset({"casa"}),
        {"predio": "sem estrutura de madeira (edificio de concreto)",
         "galpao": "sem estrutura de madeira (estrutura metalica)"}),
    ("perdas_protensao_nbr6118.py", "EPS_CS_PADRAO"): (
        frozenset({"galpao"}),
        {"casa": "sem protensao (concreto moldado in-loco, sem viga protendida)",
         "predio": "sem protensao (concreto moldado in-loco, sem viga protendida)"}),
    ("plataforma.py", "PESO_ACO"): (
        frozenset({"galpao"}),
        {"casa": "sem plataforma/passarela industrial em aco",
         "predio": "sem plataforma/passarela industrial em aco"}),
    ("plataforma.py", "Q_CONCENTRADA"): (
        frozenset({"galpao"}),
        {"casa": "sem plataforma/passarela industrial em aco",
         "predio": "sem plataforma/passarela industrial em aco"}),
    ("premoldado_nbr9062.py", "ESP_FUNDO_MIN"): (
        frozenset({"galpao"}),
        {"casa": "sem calice pre-moldado (fundacao em sapata, sem pilar pre-moldado)",
         "predio": "sem calice pre-moldado (fundacao em sapata/bloco, sem pilar pre-moldado)"}),
    ("proteccao_sprinklers_nbr10897.py", "PAREDE_MIN_MM"): (
        frozenset({"predio", "galpao"}),
        {"casa": "casa unifamiliar do escopo sem sprinklers exigidos"}),
    ("sinalizacao_nbr16820.py", "NIVEL_INFERIOR_M"): (
        frozenset({"predio", "galpao"}),
        {"casa": "casa unifamiliar do escopo sem sinalizacao de emergencia central exigida"}),
    ("sinalizacao_nbr16820.py", "NIVEL_INTERMEDIARIO_M"): (
        frozenset({"predio", "galpao"}),
        {"casa": "casa unifamiliar do escopo sem sinalizacao de emergencia central exigida"}),
    ("sismo_nbr15421.py", "_CUP"): (
        frozenset({"casa", "predio", "galpao"}),
        {}),
    ("spda_nbr5419.py", "CD_LOCALIZACAO"): (
        frozenset({"predio", "galpao"}),
        {"casa": "casa do escopo sem SPDA avaliado (sem Ng/Cd declarados; quando houver, vale a clausula)"}),
    ("spda_nbr5419.py", "RT_R3"): (
        frozenset({"predio", "galpao"}),
        {"casa": "casa do escopo sem SPDA avaliado (sem risco R3 declarado; quando houver, vale a clausula)"}),
}


def _triadas(triadas=None):
    return _ORFAS if triadas is None else triadas


def _aplic(aplic=None):
    return APLICABILIDADE if aplic is None else aplic


def exigencias_para_tipologia(tipologia=None, triadas=None, aplic=None):
    """Dividas aplicaveis a tipologia, vindas de ORFAS_TRIADAS ao vivo.

    `tipologia`: "casa"/"predio"/"galpao" ("edificio" e alias); None = a
    uniao das tres (para chamadas sem tipologia: o pacote nunca esconde
    divida por falta de rotulo). Cada item: {arquivo, nome, motivo,
    endereco, tipologias}. Ordem estavel por (arquivo, nome). Divida nova
    em ORFAS sem entrada em APLICABILIDADE NAO some: ela nao sai em
    nenhuma tipologia e aparece em sem_triagem no confere (vermelho por
    injecao). Nao implementa verificacao nenhuma: so publica.
    """
    tri = _triadas(triadas)
    ap = _aplic(aplic)
    if tipologia is None:
        chaves = sorted(tri.keys())
    else:
        tip = normaliza_tipologia(tipologia)
        chaves = sorted(k for k in tri.keys()
                        if tip in (ap.get(k, (frozenset(), {}))[0] or frozenset()))
    out = []
    for arquivo, nome in chaves:
        if (arquivo, nome) not in tri:
            continue
        _dest, motivo, endereco = tri[(arquivo, nome)]
        tips = sorted(ap.get((arquivo, nome), (frozenset(), {}))[0] or frozenset())
        out.append({"arquivo": arquivo, "nome": nome, "motivo": motivo,
                    "endereco": endereco, "tipologias": tips})
    return out


def nao_aplicaveis_para_tipologia(tipologia, triadas=None, aplic=None):
    """Dividas que NAO se aplicam a tipologia, cada uma com o porquê.

    Devolve [{arquivo, nome, por_que_nao_aplica}]. A que nao se aplica diz
    por que, no codigo (exigencia do goal): motivo vazio reprova no
    confere. Ordem estavel por (arquivo, nome).
    """
    tip = normaliza_tipologia(tipologia)
    tri = _triadas(triadas)
    ap = _aplic(aplic)
    out = []
    for chave in sorted(tri.keys()):
        tips, nao = ap.get(chave, (None, None))
        if tips is None:
            continue  # sem triagem: e sem_triagem, nao "nao aplicavel"
        if tip in tips:
            continue
        arquivo, nome = chave
        motivo = (nao or {}).get(tip, "")
        out.append({"arquivo": arquivo, "nome": nome,
                    "por_que_nao_aplica": motivo})
    return out


def confere_aplicabilidade(triadas=None, aplic=None):
    """Portao da triagem nos dois sentidos (molde G124/G69).

    Devolve {"OK", "sem_triagem", "mortas", "sem_motivo_nao_aplica",
    "tipologia_invalida"}:
      - sem_triagem: orfa DIVIDA sem entrada em APLICABILIDADE (divida
        nova que nao chega ao pacote: o vermelho por injecao do goal);
      - mortas: entrada em APLICABILIDADE sem chave em ORFAS (nome morto,
        licao do G98);
      - sem_motivo_nao_aplica: tipologia fora do conjunto sem motivo
        escrito (a que nao se aplica diz por que);
      - tipologia_invalida: conjunto com nome fora de TIPOLOGIAS.
    """
    tri = _triadas(triadas)
    ap = _aplic(aplic)
    sem = sorted(k for k in tri.keys() if k not in (ap or {}))
    mortas = sorted(k for k in (ap or {}).keys() if k not in tri)
    sem_motivo = []
    invalida = []
    for chave, valor in (ap or {}).items():
        try:
            tips, nao = valor
        except (TypeError, ValueError):
            sem_motivo.append(chave)
            continue
        tips = set(tips or set())
        nao = dict(nao or {})
        for t in tips:
            if t not in TIPOLOGIAS:
                invalida.append(chave)
                break
        for t in TIPOLOGIAS:
            if t not in tips and not (nao.get(t) or "").strip():
                sem_motivo.append(chave)
                break
    sem_motivo = sorted(set(sem_motivo))
    invalida = sorted(set(invalida))
    return {"OK": not (sem or mortas or sem_motivo or invalida),
            "sem_triagem": sem, "mortas": mortas,
            "sem_motivo_nao_aplica": sem_motivo,
            "tipologia_invalida": invalida}


def linha_exigencia(item):
    """Uma linha do pacote para a divida (vem da fonte unica, nunca literal).

    Contem o nome da constante, o arquivo, o endereco/clausula e a marca
    "não verificada pelo framework" que o portao confere por substring.
    """
    return ("- %s (%s): %s — %s [não verificada pelo framework]"
            % (item["nome"], item["arquivo"], item["motivo"],
               item["endereco"]))


def linhas_markdown(tipologia=None, triadas=None, aplic=None):
    """Linhas da secao G130 para a tipologia (ou a uniao, sem tipologia)."""
    return [linha_exigencia(it)
            for it in exigencias_para_tipologia(tipologia, triadas, aplic)]


def markdown_secao(tipologia=None, triadas=None, aplic=None):
    """Bloco markdown da secao G130 (o que o pacote carimba)."""
    if tipologia is None:
        rotulo = "todas as tipologias (sem filtro de tipologia)"
    else:
        rotulo = normaliza_tipologia(tipologia)
    linhas = ["## %s" % MARCA_SECAO, "",
               "Tipologia: %s." % rotulo,
               "Cada item abaixo e exigencia de norma escrita e nao "
               "verificada pelo framework (fonte: "
               "varredura_constantes_orfas.ORFAS_TRIADAS).", ""]
    linhas.extend(linhas_markdown(tipologia, triadas, aplic))
    return "\n".join(linhas)


def contem_exigencia(texto, arquivo, nome, endereco):
    """O documento cita a divida? (portao por substring, nunca so contagem).

    True quando o texto contem o nome da constante E o endereco/clausula
    da fonte unica. O instrumento acusa por parte (convencao 7 do lote):
    cada divida aplicavel tem de chegar ao veredito.
    """
    t = str(texto or "")
    return (nome in t) and (endereco in t)


def confere_documento(texto, tipologia=None, triadas=None, aplic=None):
    """Portao do documento: OK quando TODA divida aplicavel esta no texto.

    OK global so com todas citadas (contra a saturacao silenciosa do
    G113). 'faltando' e o acumulador que o teste faz disparar (convencao
    7). 'sem_triagem' propaga a divida nova que nao chega ao pacote.
    """
    if tipologia is None:
        esperadas = exigencias_para_tipologia(None, triadas, aplic)
    else:
        normaliza_tipologia(tipologia)  # invalida levanta, nunca vira outra
        esperadas = exigencias_para_tipologia(tipologia, triadas, aplic)
    por_item = {}
    faltando = []
    for it in esperadas:
        ok = contem_exigencia(texto, it["arquivo"], it["nome"],
                              it["endereco"])
        if ok:
            por_item["%s::%s" % (it["arquivo"], it["nome"])] = {
                "OK": True, "motivo": ""}
        else:
            por_item["%s::%s" % (it["arquivo"], it["nome"])] = {
                "OK": False,
                "motivo": "exigencia aplicavel sem citacao no documento "
                          "(exigido G130: nome + clausula da fonte unica)"}
            faltando.append((it["arquivo"], it["nome"]))
    faltando.sort()
    base = confere_aplicabilidade(triadas, aplic)
    return {"por_item": por_item, "faltando": faltando,
            "sem_triagem": list(base["sem_triagem"]),
            "OK": (not faltando) and base["OK"]}


def arquivos_que_importam_exigencias(raiz=None):
    """Arquivos *.py da raiz que importam esta fonte unica (por AST, nunca
    substring: o nome em string de mensagem de erro nao e dependencia).

    Le por ast.parse (nunca substring): `import
    exigencias_nao_verificadas_g130` ou `from
    exigencias_nao_verificadas_g130 import ...`, em qualquer nivel. O
    proprio modulo conta (fonte unica). So raiz (nao tests/): teste que
    importa a lente nao e conta de producao.
    """
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = set()
    for caminho in sorted(base.glob("*.py")):
        if caminho.name == "exigencias_nao_verificadas_g130.py":
            achados.add(caminho.name)
            continue
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            arvore = ast.parse(texto, filename=str(caminho))
        except SyntaxError:
            continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                if any((a.name or "").split(".")[0] == "exigencias_nao_verificadas_g130"
                       for a in no.names):
                    achados.add(caminho.name)
                    break
            elif isinstance(no, ast.ImportFrom):
                if (no.module or "").split(".")[0] == "exigencias_nao_verificadas_g130":
                    achados.add(caminho.name)
                    break
    return achados


def confere_uso_exigencias(raiz=None, esperado=None):
    """Portao 'ninguem le por conta propria' (lado dos imports).

    Compara quem importa a fonte unica com o baseline LEITORES_ESPERADOS
    nos dois sentidos: extra (import novo sem triagem) e faltando (nome
    morto) = vermelho. 'extras'/'faltando' sao os acumuladores que o teste
    faz disparar.
    """
    esp = set(LEITORES_ESPERADOS) if esperado is None else set(esperado)
    tem = set(arquivos_que_importam_exigencias(raiz))
    extras = sorted(tem - esp)
    faltando = sorted(esp - tem)
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    try:
        no_disco = {p.name for p in base.glob("*.py")}
    except OSError:
        no_disco = set(tem) | esp
    ausentes = sorted(a for a in esp if a not in no_disco)
    faltando = sorted(a for a in faltando if a not in ausentes)
    return {"OK": not (extras or faltando or ausentes),
            "extras": extras, "faltando": faltando, "ausentes": ausentes,
            "tem": sorted(tem)}


def main() -> int:
    from varredura_constantes_orfas import ORFAS_TRIADAS as _t
    ap = confere_aplicabilidade(_t)
    print("dividas=%d tipologias=%s" % (len(_t), list(TIPOLOGIAS)))
    for tip in TIPOLOGIAS:
        n = len(exigencias_para_tipologia(tip, _t))
        m = len(nao_aplicaveis_para_tipologia(tip, _t))
        print("  %s: aplicaveis=%d nao_aplicaveis=%d" % (tip, n, m))
    print("aplicabilidade OK=%s sem_triagem=%r mortas=%r sem_motivo=%r "
          "invalida=%r" % (ap["OK"], ap["sem_triagem"], ap["mortas"],
                            ap["sem_motivo_nao_aplica"],
                            ap["tipologia_invalida"]))
    u = confere_uso_exigencias()
    print("uso OK=%s extras=%r faltando=%r" % (u["OK"], u["extras"],
                                               u["faltando"]))
    return 0 if (ap["OK"] and u["OK"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
