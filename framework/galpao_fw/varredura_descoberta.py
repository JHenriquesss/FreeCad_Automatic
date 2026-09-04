# ============================================================================
# varredura_descoberta.py - G40/G43: A VARREDURA PRECISA DESCOBRIR, NAO CONFERIR.
# SCRIPT AVULSO: ferramenta de descoberta rodada a mao/CI (python
# varredura_descoberta.py) e pelos testes-guardas
# tests/test_varredura_descoberta_g40.py (estrutural) e
# tests/test_varredura_descoberta_g43.py (demais disciplinas).
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


def descobrir_no_arquivo(caminho):
    """Orfaos de UM orquestrador: [{arquivo, variavel, linha, detalhe}]."""
    caminho = pathlib.Path(caminho)
    try:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    no = _rodar_no(arvore)
    if no is None:
        return []
    edges, defined = _dependencias(no)
    sumidouros, _ = _sumidouros(no)
    orfaos = []
    for var, linha in sorted(defined.items()):
        if not ESFORCO_RE.match(var):
            continue
        if (caminho.name, var) in PERMITIDOS_TERMINAIS:
            continue
        if _alcancca(var, edges, sumidouros):
            continue
        jusante = sorted(edges.get(var, ()))[:4]
        orfaos.append({
            "arquivo": caminho.name,
            "variavel": var,
            "linha": linha,
            "detalhe": ("calculado em rodar() e nunca alcanca verificacao; "
                        "jusante=%r" % (jusante,)),
        })
    return orfaos


def descobrir_texto(nome_arquivo, fonte):
    """Variante para prova isolada (G21 espirito): analisa fonte em memoria."""
    try:
        arvore = ast.parse(fonte)
    except SyntaxError:
        return []
    no = _rodar_no(arvore)
    if no is None:
        return []
    edges, defined = _dependencias(no)
    sumidouros, _ = _sumidouros(no)
    orfaos = []
    for var, linha in sorted(defined.items()):
        if not ESFORCO_RE.match(var):
            continue
        if _alcancca(var, edges, sumidouros):
            continue
        orfaos.append({"arquivo": nome_arquivo, "variavel": var,
                       "linha": linha, "detalhe": "orfao em fonte sintetica"})
    return orfaos


def varredura():
    """Todos os orfaos descobertos nos orquestradores (ordem estavel)."""
    achados = []
    for _tip, arquivos in TIPOLOGIAS.items():
        for arq in arquivos:
            achados.extend(descobrir_no_arquivo(GALPAO / arq))
    achados.sort(key=lambda d: (d["arquivo"], d["variavel"]))
    return achados


def chaves_varridas():
    return sorted((d["arquivo"], d["variavel"]) for d in varredura())


def relatorio_pt():
    linhas = ["VARREDURA G40/G43 - DESCOBERTA GENERICA DE ORFAOS",
               "arquivo | variavel @linha -> motivo"]
    for d in varredura():
        linhas.append("  %-26s | %-14s @%d" % (d["arquivo"], d["variavel"],
                                               d["linha"]))
    if not varredura():
        linhas.append("  (nenhum orfao: tudo calculado alcanca verificacao)")
    return "\n".join(linhas)


if __name__ == "__main__":
    print(relatorio_pt())
    print()
    for ilha in varredura():
        print("  ORFAO: %(arquivo)s/%(variavel)s L%(linha)s" % ilha)
