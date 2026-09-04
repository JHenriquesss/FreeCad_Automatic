# ============================================================================
# varredura_descoberta.py - G40/G43/G48: A VARREDURA PRECISA DESCOBRIR,
# NAO CONFERIR.
# SCRIPT AVULSO: ferramenta de descoberta rodada a mao/CI (python
# varredura_descoberta.py) e pelos testes-guardas
# tests/test_varredura_descoberta_g40.py (estrutural),
# tests/test_varredura_descoberta_g43.py (demais disciplinas) e
# tests/test_varredura_descoberta_g48.py (lente ampliada aos calculos).
# Nao e importada por nenhum orquestrador do Loop - e declarada em
# SCRIPTS_AVULSOS no tests/test_alcancabilidade.py, no mesmo molde de
# validacao/verificar_amostra.
#
# Motivacao (G40): varredura_nao_verificados.NAO_VERIFICADOS e lista curada;
# o AST valida cada item declarado e confirma que as vigas fecharam. Util -
# o guarda trava nos dois sentidos - mas nao e o que o G6 fez. O fecho de
# alcancabilidade achou 21 ilhas que ninguem suspeitava; a lista curada so
# acha o par que alguem ja escreveu. Prova: G39 veio de raciocinio humano,
# G38 estava estacionado numa nota de cabecalho fora da guarda ("omissao
# de caminho de carga, nao esforco calculado sem cheque").
#
# Detector de verdade: percorre os orquestradores (rodar()) procurando valor
# calculado que nunca alcanca uma funcao de verificacao. Mecanismo:
#   - fontes: nomes atribuidos em rodar() com cara de esforco/carga
#     (M_/V_/N_/W_/R_/... , r_escada/stair, w_/q_).
#   - sumidouros: chamadas a funcoes de verificacao/dimensionamento
#     (verifica|dimensiona|vrd|flt|cross_check|ist_req|a_max|...).
#   - fluxo: grafo de dependencias (Assign, For, mutacao via metodo
#     obj.setdefault/update/append e via _descer_escada(desc, stair)).
#     Uma fonte ALCANCA verificacao se ela propria ou qualquer variavel a
#     jusante aparece nos argumentos de um sumidouro.
#   - orfao: fonte que nao alcanca nenhum sumidouro e nao esta em
#     PERMITIDOS_TERMINAIS (saidas terminais de verificacao e totais de
#     reporte, documentados abaixo - nao ilhas estruturais).
#
# No espirito do G21, o detector e provado vermelho injetando um caso
# conhecido em cada linguagem (ver test_varredura_descoberta_g40.py para o
# estrutural e test_varredura_descoberta_g43.py para as demais disciplinas:
# um zero so vale depois do vermelho injetado naquela linguagem).
#
# G48 - A LENTE SO ENXERGAVA rodar(): nas disciplinas nao estruturais quase
# todo o calculo mora um nivel abaixo, nos modulos chamados
# (hidraulica_residencial.rodar(): 12 atribuicoes, 0 candidatos; incendio:
# 22 e 1; contra 45 e 8 no eletrico, o unico que calcula no rodar).
# A descoberta agora alcanca as funcoes de calculo chamaveis a partir de
# cada rodar() - mesmo arquivo ou outro modulo do GALPAO resolvido via
# import - em transicao com TETO (PROFUNDIDADE_MAX): rodar(0) -> chamados
# diretos(1) -> chamados-dos-chamados(2). Cada funcao e analisada com o
# mesmo vocabulario (ESFORCO_RE) e os mesmos sumidouros (VERIF_RE), mas o
# RETORNO da funcao e FRONTEIRA: valor calculado que alcanca o return
# atravessou para o chamador (vira responsabilidade dele) e nao e orfao
# na funcao. Idem a CONFERENCIA INLINE COM VEREDITO: candidata testada num
# `if` cujo ramo registra veredito (violacoes/faltantes/erros/avisos.append,
# raise, atribuicao a OK/violacoes) esta conferida - e o idioma das funcoes
# verificadoras (verifica_extintores, verifica_armazenamento,
# verifica_agua_quente_seguranca, corrige_fator_potencia). Triagem G48 de
# tudo que a lente ampliada achou: "vira verificacao" (retorno/veredito,
# sem tocar producao e sem allowlist) ou "vira ilha declarada" (baseline
# pinada, nunca silenciada). O vermelho injetado agora mora num MODULO
# CHAMADO, nao no orquestrador (ver test_varredura_descoberta_g48.py).
# ============================================================================
"""Varredura G40: descoberta generica de valor calculado sem verificacao."""

from __future__ import annotations

import ast
import collections
import pathlib
import re

GALPAO = pathlib.Path(__file__).resolve().parent

# Orquestradores varridos, por tipologia (G40: estruturais, mesma cobertura
# da G33; G43: +5 verticais nunca examinados por esta lente).
TIPOLOGIAS = {
    "galpao": ["rodar_galpao.py", "galpao_concreto.py"],
    "casa": ["estrutura_casa.py"],
    "edificio": ["edificio_multipavimento.py"],
    "mezanino": ["galpao_mezanino.py"],
    "eletrico": ["galpao_eletrico.py"],
    "hidraulica": ["galpao_hidraulica.py", "hidraulica_residencial.py"],
    "incendio": ["galpao_seguranca_incendio.py"],
    "climatizacao": ["galpao_climatizacao.py"],
    "residencial": ["arquitetura_residencial.py"],
}

# Nome com cara de grandeza calculada no orquestrador, por disciplina.
# CASE-SENSITIVE de proposito (G43): o re.I antigo casava N_ com n_cond
# (n. de condutores pluviais), n_tomadas (n. de tomadas) e n_port/n_col
# (contagens de porticos/pilares) - dois deles viraram falsos positivos
# assim que a lente alcançou as outras disciplinas. As formas minusculas
# legitimas ja estao listadas (r_escada, w_, q_, n_terca, uhc...); o re.I
# era redundante para elas e caçava contadores.
ESFORCO_RE = re.compile(
    # estrutural (G40, inalterado menos a caixa)
    r"^(M_|V_|N_|Q_|W_|R_|F_|Vd|Nd|Md|Vsd|Msd|Nsd|V_w|M_w|N_w|W_g|W_q|"
    r"M_positivo|M_apoios|V_max|N_total|N_acum|N_aplicado|g_kN|q_kN|R_beam|"
    r"Msd_|Vsd_|Nsd_|M_k|N_k|V_k|M_base|M_max|V_base|N_pilar|N_cinta|N_comp|"
    r"N_tr|r_escada|stair|r_laje|r_vigas|w_|q_|n_terca|"
    # eletrico (G43: Icc na barra, queda dU, S_/P_ aparentes/ativas,
    # fp resultante, Iz/IB/IN do alimentador)
    r"Icc|dU|dv_|S_|P_|fp|IZ|Iz|IB|IN_|D_kW|D_kVA|P_inst|"
    # hidraulica (G43: vazao Q_, velocidade v_, perda J_, DN, UHC)
    r"v_|J_|DN|UHC|uhc|soma_P|"
    # incendio (G43: carga de incendio, populacao, vazao de hidrante)
    r"carga_|pop_|vazao|N_detectores|N_hidrantes|N_chuveiros|N_acionadores|"
    r"N_placas|reserva_|"
    # climatizacao (G43: vazao de insuflamento, TR, capacidade)
    r"V_ins|TR_|capacidade|vazao_ins|"
    # residencial/arquitetura (G43: geometria que governa a NBR 5410 9.5.2)
    r"area|perimetro|carga_iluminacao|carga_tomadas|n_pontos_luz)",
)

# Chamada que VERIFICA ou DIMENSIONA (sumidouro). Inclui nomes curtos do
# dominio (vrd, flt, cross_check, ist_req, a_max) que nao contem "verifica",
# mais os verbos de calculo de cada disciplina (G43) que produzem ou
# consomem as grandezas acima sem dizer "verifica"/"dimensiona".
VERIF_RE = re.compile(
    r"verifica|dimensiona|vrd|flt|cross_check|ist_req|a_max|forcas_local|"
    r"empocamento|chec|valid|confer|fecha|"
    r"diametro|uhc_|vazao|quadro_de_cargas|icc|corrige|"
    r"projeto_luminotecnico|criterio_tomadas|carga_",
    re.I,
)

# Funcoes cujo primeiro argumento e MUTADO pelos demais (carga que desce).
# _descer_escada(desc, stair) e o caso do G38: stair -> desc.
MUTATE_RE = re.compile(
    r"descer|desce|soma|aplica|distribui|atualiza|acumula|propaga|realimenta",
    re.I,
)

# Saidas que NAO precisam alcancar outro sumidouro, com motivo declarado.
# Sao resultados TERMINAIS de verificacao ou totais de reporte derivados de
# descida ja verificada - nao esforco orfao. Tudo o mais que o detector achar
# e ILHA DESCOBERTA (nao curada): entra no relatorio, nao aqui.
PERMITIDOS_TERMINAIS = {
    # (arquivo, variavel): motivo
    ("estrutura_casa.py", "r_vigas"):
        "saida terminal de verifica_vigas: E a verificacao, nao precisa de outra",
    ("estrutura_casa.py", "N_base"):
        "total de reporte p/ retorno (derivado de desc ja verificada)",
    ("edificio_multipavimento.py", "r_vigas"):
        "saida terminal de verifica_vigas por tramo (G34): E a verificacao",
    ("edificio_multipavimento.py", "N_desc_total"):
        "total de reporte p/ fechamento_carga (comparacao inline, nao sumidouro)",
    ("estrutura_casa.py", "N_desc_total"):
        "total de reporte p/ fechamento_carga G42 (comparacao inline, nao sumidouro)",
}


def _rodar_no(arvore, nome="rodar"):
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == nome:
            return no
    return None


# G48: teto da lente ampliada. rodar()=0, chamados diretos=1,
# chamados-dos-chamados=2. Mais fundo que isso e outro goal (a lente
# declara o teto em vez de varrer o mundo em silencio).
PROFUNDIDADE_MAX = 2
MAX_FUNCOES_POR_ORQUESTRADOR = 32

# Ramo que registra veredito: a candidata testada no `if` esta conferida.
# (violacoes/faltantes/erros/avisos.append|extend, raise, atribuicao a
# OK/violacoes/faltantes - o idioma das verificadoras.)
_VEREDITO_NOME_RE = re.compile(r"violac|faltante|erros?|avisos?", re.I)
_VEREDITO_ATRIB_RE = re.compile(r"^(OK|violac|faltante|reprovad|precisa_)", re.I)


def _funcoes_da_arvore(arvore):
    return {n.name: n for n in ast.walk(arvore)
            if isinstance(n, ast.FunctionDef)}


def _imports_para_modulo(arvore):
    """Nome local -> modulo de origem (parte alta, arquivos irmaos no GALPAO)."""
    mapa = {}
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for a in no.names:
                mapa[(a.asname or a.name).split(".")[0]] = \
                    a.name.split(".")[0]
        elif isinstance(no, ast.ImportFrom) and no.module:
            for a in no.names:
                mapa[a.asname or a.name] = no.module.split(".")[0]
    return mapa


def _chamadas_de(no_func):
    """Pares (base_ou_None, nome) chamados no corpo da funcao."""
    achadas = []
    for no in ast.walk(no_func):
        if isinstance(no, ast.Call):
            fn = no.func
            if isinstance(fn, ast.Name):
                achadas.append((None, fn.id))
            elif (isinstance(fn, ast.Attribute)
                    and isinstance(fn.value, ast.Name)):
                achadas.append((fn.value.id, fn.attr))
    return achadas


def _retornos(no_func):
    """Nomes que escapam pelo return: a fronteira da funcao (G48)."""
    nomes = set()
    for no in ast.walk(no_func):
        if isinstance(no, ast.Return) and no.value is not None:
            for n in ast.walk(no.value):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                    nomes.add(n.id)
    return nomes


def _tem_veredito(ramos):
    """Ha registro de veredito nos corpos do if (body/orelse)?"""
    for corpo in ramos:
        for no in ast.walk(ast.Module(body=corpo, type_ignores=[])):
            if isinstance(no, ast.Raise):
                return True
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute):
                base = no.func.value
                if (isinstance(base, ast.Name)
                        and _VEREDITO_NOME_RE.search(base.id)
                        and no.func.attr in ("append", "extend", "add",
                                             "update", "setdefault")):
                    return True
            if isinstance(no, (ast.Assign, ast.AnnAssign)):
                alvos = (no.targets if isinstance(no, ast.Assign)
                         else [no.target])
                for t in alvos:
                    for n in ast.walk(t):
                        if (isinstance(n, ast.Name)
                                and isinstance(n.ctx, ast.Store)
                                and _VEREDITO_ATRIB_RE.match(n.id)):
                            return True
    return False


def _conferidas_inline(no_func):
    """Candidatas testadas em `if` cujo ramo registra veredito (G48).

    E a conferencia inline das verificadoras: `if area_operacao < MIN:
    violacoes.append(...)`, `if not 0 < fp <= 1: raise`, etc. So vale com
    veredito no ramo - um `if x is not None: pass` sozinho nao confere."""
    conferidas = set()
    for no in ast.walk(no_func):
        if not isinstance(no, ast.If):
            continue
        teste = {n.id for n in ast.walk(no.test)
                 if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        if teste and _tem_veredito((no.body, no.orelse)):
            conferidas.update(teste)
    return conferidas


def _dependencias(no_rodar):
    """Grafo dep -> {definidos} e mapa definido -> linha."""
    edges = collections.defaultdict(set)
    defined = {}

    def add(dep, dst):
        if dep != dst:
            edges[dep].add(dst)

    for no in ast.walk(no_rodar):
        if isinstance(no, (ast.Assign, ast.AnnAssign)):
            targets = no.targets if isinstance(no, ast.Assign) else [no.target]
            val = no.value
            rhs = {n.id for n in ast.walk(val)
                   if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            fname = ""
            if isinstance(val, ast.Call):
                fn = val.func
                fname = (fn.attr if isinstance(fn, ast.Attribute)
                         else (fn.id if isinstance(fn, ast.Name) else ""))
            for t in targets:
                lhs = set()
                for n in ast.walk(t):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                        lhs.add(n.id)
                if isinstance(t, ast.Subscript):
                    v = t.value
                    while isinstance(v, ast.Subscript):
                        v = v.value
                    if isinstance(v, ast.Name):
                        lhs.add(v.id)
                    elif (isinstance(v, ast.Attribute)
                          and isinstance(v.value, ast.Name)):
                        lhs.add(v.value.id)
                for d in lhs:
                    defined.setdefault(d, getattr(no, "lineno", 0))
                    for r in rhs:
                        add(r, d)
            # mutacao via construtor: detalhe = _descer_escada(desc, stair)
            # (Assign, nao Expr): stair -> desc quando a funcao sugere mutacao.
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name):
                if MUTATE_RE.search(val.func.id) or \
                        val.func.id.startswith("_descer"):
                    if val.args:
                        fset = {n.id for n in ast.walk(val.args[0])
                                if isinstance(n, ast.Name)}
                        allargs = {n.id for n in ast.walk(val)
                                   if isinstance(n, ast.Name)
                                   and isinstance(n.ctx, ast.Load)}
                        for f in fset:
                            for r in allargs:
                                if r != f:
                                    add(r, f)
        elif isinstance(no, ast.For):
            it = {n.id for n in ast.walk(no.iter)
                  if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            tg = {n.id for n in ast.walk(no.target)
                  if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
            for d in tg:
                defined.setdefault(d, getattr(no, "lineno", 0))
                for r in it:
                    add(r, d)
        elif isinstance(no, ast.Expr) and isinstance(no.value, ast.Call):
            c = no.value
            fn = c.func
            allargs = {n.id for n in ast.walk(c)
                       if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
                obj = fn.value.id
                for r in allargs:
                    if r != obj:
                        add(r, obj)
            elif isinstance(fn, ast.Name):
                if MUTATE_RE.search(fn.id) or fn.id.startswith("_descer"):
                    if c.args:
                        fset = {n.id for n in ast.walk(c.args[0])
                                if isinstance(n, ast.Name)}
                        for f in fset:
                            for r in allargs:
                                if r != f:
                                    add(r, f)
    return edges, defined


def _sumidouros(no_rodar):
    """Nomes que aparecem como argumento de funcao verificadora."""
    nomes = set()
    n_chamadas = 0
    for no in ast.walk(no_rodar):
        if isinstance(no, ast.Call):
            fn = no.func
            fname = (fn.attr if isinstance(fn, ast.Attribute)
                     else (fn.id if isinstance(fn, ast.Name) else ""))
            if VERIF_RE.search(fname):
                n_chamadas += 1
                for n in ast.walk(no):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                        nomes.add(n.id)
    return nomes, n_chamadas


def _alcancca(var, edges, sumidouros):
    vistos = {var}
    fila = [var]
    while fila:
        cur = fila.pop()
        if cur in sumidouros:
            return True
        for nxt in edges.get(cur, ()):
            if nxt not in vistos:
                vistos.add(nxt)
                fila.append(nxt)
    return False


def _orfaos_em_funcao(nome_arquivo, nome_funcao, no_func, profundidade):
    """Orfaos de UMA funcao: mesma lente do rodar, com duas fronteiras a
    mais (G48): o return (valor atravessou para o chamador) e a conferencia
    inline com veredito (idioma das verificadoras)."""
    edges, defined = _dependencias(no_func)
    sumidouros, _ = _sumidouros(no_func)
    fronteira = set(sumidouros) | _retornos(no_func)
    conferidas = _conferidas_inline(no_func)
    orfaos = []
    for var, linha in sorted(defined.items()):
        if not ESFORCO_RE.match(var):
            continue
        if nome_funcao == "rodar" and \
                (nome_arquivo, var) in PERMITIDOS_TERMINAIS:
            continue
        if _alcancca(var, edges, fronteira):
            continue
        if var in conferidas:
            continue
        jusante = sorted(edges.get(var, ()))[:4]
        onde = ("rodar()" if nome_funcao == "rodar"
                else "%s() a %d salto(s) de rodar()"
                % (nome_funcao, profundidade))
        orfaos.append({
            "arquivo": nome_arquivo,
            "funcao": nome_funcao,
            "variavel": var,
            "linha": linha,
            "detalhe": ("calculado em %s e nunca alcanca verificacao, "
                        "retorno ou veredito-inline; jusante=%r"
                        % (onde, jusante)),
        })
    return orfaos


def _alcancaveis(arvore, nome_arquivo, resolver_imports=True,
                 cache=None, profundidade_max=PROFUNDIDADE_MAX):
    """Fecho rodar() -> calculos: [(arquivo, funcao, no, profundidade)].

    Mesmo arquivo via chamadas diretas; outros modulos do GALPAO via
    `modulo.funcao` resolvido pelo import (alias inclusive). Transitivo
    com TETO: alem de profundidade_max a lente declara que nao ve - nao
    finge que viu."""
    if cache is None:
        cache = {}
    funcoes = _funcoes_da_arvore(arvore)
    no_rodar = funcoes.get("rodar")
    if no_rodar is None:
        return []
    importados = _imports_para_modulo(arvore) if resolver_imports else {}
    vistos = set()
    fila = [(nome_arquivo, "rodar", no_rodar, 0)]
    ordem = []
    while fila and len(ordem) < MAX_FUNCOES_POR_ORQUESTRADOR:
        arq, fname, no, prof = fila.pop(0)
        if (arq, fname) in vistos:
            continue
        vistos.add((arq, fname))
        ordem.append((arq, fname, no, prof))
        if prof >= profundidade_max:
            continue
        for base, attr in _chamadas_de(no):
            if base is None:
                alvo = funcoes.get(attr) if arq == nome_arquivo else None
                if alvo is None and arq != nome_arquivo:
                    outra = cache.get(arq)
                    if outra is not None:
                        alvo = _funcoes_da_arvore(outra).get(attr)
                if alvo is not None and (arq, attr) not in vistos:
                    fila.append((arq, attr, alvo, prof + 1))
            elif resolver_imports and base in importados:
                modulo = importados[base]
                if modulo not in cache:
                    palvo = GALPAO / (modulo + ".py")
                    try:
                        cache[modulo] = (
                            ast.parse(palvo.read_text(encoding="utf-8"))
                            if palvo.is_file() else None)
                    except (OSError, SyntaxError):
                        cache[modulo] = None
                outra = cache[modulo]
                if outra is None:
                    continue
                alvo = _funcoes_da_arvore(outra).get(attr)
                if alvo is not None and \
                        (modulo + ".py", attr) not in vistos:
                    fila.append((modulo + ".py", attr, alvo, prof + 1))
    return ordem


def _estado_escrito(no_func):
    """Globais que a funcao PUBLICA: declarados em `global` e armazenados.

    E a fronteira de estado (G48): configurar()/reset() publicam N_VAOS,
    Q_ROOF, W_WALL_COL e o solver/rodar consomem via estado do modulo. O
    fluxo intra-funcao nao ve essa publicacao - o fecho ve (ver abaixo)."""
    declarados = set()
    for no in ast.walk(no_func):
        if isinstance(no, ast.Global):
            declarados.update(no.names)
    if not declarados:
        return set()
    armazenados = {n.id for n in ast.walk(no_func)
                   if isinstance(n, ast.Name)
                   and isinstance(n.ctx, ast.Store)}
    return declarados & armazenados


def _nomes_lidos(no_func):
    return {n.id for n in ast.walk(no_func)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def _descobrir_em_alcance(alcance):
    """Orfaos do fecho rodar()->calculos, com fluxo de estado (G48).

    Primeiro a prova intra-funcao (_orfaos_em_funcao). O que sobrar como
    orfao MAS for estado publicado (global) ganha a segunda chance honesta:
    o grafo combinado do fecho, com arestas escritor->leitor no mesmo
    modulo. So cobre se, no leitor, o nome alcanca sumidouro, retorno ou
    veredito - o mesmo barao da prova intra, fim a fim. Referencia passada
    como callback, mutacao de objeto via parametro e leitura cross-modulo
    (`gp.N_VAOS`) seguem FORA do alcance declarado (limite documentado,
    nao silencio: o que ficar de fora aparece como ilha declarada)."""
    por_func = {}
    for arq, fname, no, prof in alcance:
        edges, defined = _dependencias(no)
        sumidouros, _ = _sumidouros(no)
        por_func[(arq, fname)] = {
            "no": no, "prof": prof, "edges": edges, "defined": defined,
            "sumidouros": sumidouros, "retornos": _retornos(no),
            "conferidas": _conferidas_inline(no),
            "escritos": _estado_escrito(no),
            "lidos": _nomes_lidos(no),
        }
    # Grafo combinado com nos qualificados (funcao, variavel).
    comb_edges = collections.defaultdict(set)
    comb_alvos = set()
    for (arq, fname), info in por_func.items():
        for dep, dsts in info["edges"].items():
            for dst in dsts:
                comb_edges[(fname, dep)].add((fname, dst))
        for s in (info["sumidouros"] | info["retornos"]):
            comb_alvos.add((fname, s))
    for (arq_w, fname_w), info_w in por_func.items():
        for var in info_w["escritos"]:
            for (arq_r, fname_r), info_r in por_func.items():
                if arq_r != arq_w or fname_r == fname_w:
                    continue
                if var in info_r["lidos"]:
                    comb_edges[(fname_w, var)].add((fname_r, var))
    orfaos = []
    for (arq, fname), info in por_func.items():
        for var, linha in sorted(info["defined"].items()):
            if not ESFORCO_RE.match(var):
                continue
            if fname == "rodar" and (arq, var) in PERMITIDOS_TERMINAIS:
                continue
            if _alcancca(var, info["edges"],
                         info["sumidouros"] | info["retornos"]):
                continue
            if var in info["conferidas"]:
                continue
            if var in info["escritos"] and _alcancca(
                    (fname, var), comb_edges, comb_alvos):
                continue
            jusante = sorted(info["edges"].get(var, ()))[:4]
            onde = ("rodar()" if fname == "rodar"
                    else "%s() a %d salto(s) de rodar()"
                    % (fname, info["prof"]))
            orfaos.append({
                "arquivo": arq,
                "funcao": fname,
                "variavel": var,
                "linha": linha,
                "detalhe": ("calculado em %s e nunca alcanca verificacao, "
                            "retorno, veredito-inline ou leitor de estado; "
                            "jusante=%r" % (onde, jusante)),
            })
    return orfaos


def descobrir_no_arquivo(caminho, profundidade=PROFUNDIDADE_MAX):
    """Orfaos de UM orquestrador e seus calculos (G48).

    [{arquivo, funcao, variavel, linha, detalhe}]. Com profundidade=0 a
    lente volta a enxergar so o rodar() (comportamento G40/G43)."""
    caminho = pathlib.Path(caminho)
    try:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    return _descobrir_em_alcance(_alcancaveis(
        arvore, caminho.name, profundidade_max=profundidade))


def descobrir_texto(nome_arquivo, fonte, profundidade=PROFUNDIDADE_MAX):
    """Variante para prova isolada (G21 espirito): analisa fonte em memoria,
    agora com as chamadas internas (G48: o vermelho mora no modulo chamado)."""
    try:
        arvore = ast.parse(fonte)
    except SyntaxError:
        return []
    orfaos = _descobrir_em_alcance(_alcancaveis(
        arvore, nome_arquivo, resolver_imports=False,
        profundidade_max=profundidade))
    for d in orfaos:
        d["arquivo"] = nome_arquivo
    return orfaos


def permitido_ainda_valido(arq, var, profundidade=PROFUNDIDADE_MAX):
    """Guarda anti-allowlist de nome morto na lente AMPLIADA (G48).

    O permitido vale enquanto nomear variavel viva no rodar() OU em
    qualquer calculo alcancavel - com a lista maior a guarda continua
    valendo; se o orquestrador for renomeado ou a variavel sair de todos
    os alcances, morre em voz alta em vez de virar salvo-conduto vazio."""
    caminho = GALPAO / arq
    if not caminho.is_file():
        return False
    try:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    if _rodar_no(arvore) is None:
        return False
    for _a, _f, no, _p in _alcancaveis(arvore, arq,
                                       profundidade_max=profundidade):
        nomes = {n.id for n in ast.walk(no) if isinstance(n, ast.Name)}
        if var in nomes:
            return True
    return False


def varredura():
    """Todos os orfaos descobertos nos orquestradores (ordem estavel).

    G48: o mesmo calculo pode ser alcancado por dois orquestradores
    (multiplicadores_pavimentos via casa e via edificio) - a chave
    (arquivo, funcao, variavel) sai uma vez so."""
    achados = []
    vistas = set()
    for _tip, arquivos in TIPOLOGIAS.items():
        for arq in arquivos:
            for d in descobrir_no_arquivo(GALPAO / arq):
                chave = (d["arquivo"], d["funcao"], d["variavel"])
                if chave not in vistas:
                    vistas.add(chave)
                    achados.append(d)
    achados.sort(key=lambda d: (d["arquivo"], d["funcao"], d["variavel"]))
    return achados


def chaves_varridas():
    # G48: a chave ganhou a funcao - a mesma variavel pode viver no rodar()
    # e num calculo com destinos diferentes.
    return sorted((d["arquivo"], d["funcao"], d["variavel"])
                  for d in varredura())


def relatorio_pt():
    linhas = ["VARREDURA G40/G43/G48 - DESCOBERTA GENERICA DE ORFAOS",
               "arquivo/funcao | variavel @linha -> motivo"]
    for d in varredura():
        linhas.append("  %-26s/%-28s | %-20s @%d" % (
            d["arquivo"], d["funcao"], d["variavel"], d["linha"]))
    if not varredura():
        linhas.append("  (nenhum orfao: tudo calculado alcanca verificacao, "
                       "retorno ou veredito-inline)")
    return "\n".join(linhas)


if __name__ == "__main__":
    print(relatorio_pt())
    print()
    for ilha in varredura():
        print("  ORFAO: %(arquivo)s/%(funcao)s/%(variavel)s L%(linha)s" % ilha)
