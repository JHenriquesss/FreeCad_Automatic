# ============================================================================
# varredura_asserts_sequencia.py - G97: O PORTAO QUE ESCONDE O PORTAO.
# SCRIPT AVULSO: ferramenta permanente rodada a mao/CI (python
# varredura_asserts_sequencia.py) e pelo teste-guarda
# tests/test_asserts_sequencia_g97.py. Nao e importada por nenhum
# orquestrador do Loop - declarada em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de varredura_descoberta.
#
# Motivacao (G97): test_09_cobertura_todo_py_varrido_ou_isento tinha quatro
# asserts independentes em sequencia (faltando, sobrando, sem_motivo,
# ausentes); o primeiro que estourava impedia a avaliacao dos outros tres.
# O portao do G77 ficou vermelho desde o proprio commit fb53107 e ninguem
# viu: o sobrando (isencao de desenho_svg_base.py que virou nome morto,
# porque a prosa da linha 229 passou a casar com a VALIDADE_RE) estava
# escondido atras do faltando. Cada conserto revelava um achado que ja
# estava la havia commits. O padrao se repete em test_guardas_d86_g69.py,
# test_folhas_g77.py, test_defaults_veredito_g75.py e no G91.
#
# Maquina: AST por funcao de teste (mesma familia do G48/G51/G75/G83, sem
# vocabulario de faixa). Para cada `def test_*` em tests/**/test_*.py que
# seja portao de censo/cobertura (nome com censo|cobertura|baseline|portao|
# indice_disco, ou corpo que chama confere_cobertura|censo_de_folhas|
# chaves_desguardadas|arquivos_sem_chave|conferir_indice_disco), a lente
# mede runs de `assert` consecutivos no mesmo bloco. Um run de >= 2 asserts
# INDEPENDENTES e o defeito (o segundo nunca e avaliado quando o primeiro
# estoura). Um run onde cada passo DEPENDE do anterior (guard clause:
# `assert r is not None` antes de `assert r["x"] == 3`) e correto e entra
# em ISENTAS_SEQUENCIA com o motivo escrito - isencao sem motivo e
# silencio, nao triagem (mesma regra das outras lentes).
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - asserts separados por outra instrucao (ex. `r = f()` entre eles):
#     nao sao "em sequencia" no sentido do AST e nao entram; o mascaramento
#     parcial que resta e triado como conteudo, nao como sequencia.
#   - asserts dentro de `for`/`while` (um por iteracao): o mascaramento ali
#     e por iteracao, nao por lado; a receita (coletar e falhar uma vez)
#     vale igual, mas a lente nao os acusa para nao virar ruido.
#   - funcoes que nao sao portao (nome fora do vocabulario e sem chamada
#     de censo): podem ter N asserts sequenciais por desenho (prova de
#     vermelho por injecao, passo a passo); a lente as ignora e o
#     teste-guarda as declara em ISENTAS_SEQUENCIA quando preciso.
#   - arquivos fora de tests/: a lente mira a suite, nao a arvore.
# ============================================================================
"""Varredura G97: asserts independentes em sequencia num mesmo portao."""

from __future__ import annotations

import ast
import pathlib
import re

GALPAO = pathlib.Path(__file__).resolve().parent
TESTS = GALPAO / "tests"

_PORTAO_NOME_RE = re.compile(
    r"censo|varrido_ou_isento|coberta_ou_isenta|baseline|"
    r"portao_.*tipologia|indice_disco|toda_folha",
    re.IGNORECASE,
)

_CHAMADAS_CENSO = (
    "confere_cobertura",
    "censo_de_folhas",
    "chaves_desguardadas",
    "arquivos_sem_chave",
    "conferir_indice_disco",
    "arquivos_varridos",
)

_BASELINE_NOMES = (
    "BASELINE_G",
    "TRIADAS_G69",
    "SEM_FAIXA_DECLARADA",
    "ISENTAS",
)


def _e_portao(nome_func, seg, func_no=None):
    """True se a funcao e portao de censo/cobertura (nome ou chamada).

    Provas de vermelho por injecao (nome com `vermelho` ou arg `tmp_path`)
    sao passos intencionais, nao portao: ficam de fora.
    """
    if "vermelho" in (nome_func or "").lower():
        return False
    if func_no is not None:
        args = [a.arg for a in getattr(func_no.args, "args", [])]
        if "tmp_path" in args:
            return False
    if _PORTAO_NOME_RE.search(nome_func or ""):
        return True
    texto = seg or ""
    for marca in _CHAMADAS_CENSO:
        if marca in texto:
            return True
    for marca in _BASELINE_NOMES:
        if marca in texto:
            return True
    return False


def _nomes(test):
    return {n.id for n in ast.walk(test) if isinstance(n, ast.Name)}


def _bases_deref(test):
    """Bases de Subscript/Attribute/Call no teste (r em r["x"], r.ok)."""
    bases = set()
    for no in ast.walk(test):
        if isinstance(no, ast.Subscript):
            v = no.value
            while isinstance(v, ast.Subscript):
                v = v.value
            if isinstance(v, ast.Name):
                bases.add(v.id)
            elif isinstance(v, ast.Attribute):
                cur = v
                while isinstance(cur, ast.Attribute):
                    cur = cur.value
                if isinstance(cur, ast.Name):
                    bases.add(cur.id)
        elif isinstance(no, ast.Attribute):
            cur = no
            while isinstance(cur, ast.Attribute):
                cur = cur.value
            if isinstance(cur, ast.Name):
                bases.add(cur.id)
    return bases


def _e_guard(anterior, posterior):
    """True se o posterior DEPENDE do anterior (guard clause legitima).

    Forma canonica: `assert r is not None` (ou `assert r`) antes de
    `assert r["x"] == ...`. Sem o primeiro, o segundo levantaria TypeError
    em vez de falhar como assercao - a ordem e dependencia, nao
    mascaramento de lados independentes.

    `assert not r["faltando"]` antes de `assert not r["sobrando"]` NAO e
    guard: ambos dereferenciam chaves do mesmo dict (lados independentes).
    Guard exige que o anterior cheque o OBJETO (sem Subscript/Attribute),
    nao uma chave dele.
    """
    teste_a = anterior.test
    # Lado checado nao e guard: `assert not r["k"]`, `assert r["k"] == v`,
    # `assert len(r["k"]) == 0` - o anterior ja e um lado, nao a guarda.
    for no in ast.walk(teste_a):
        if isinstance(no, (ast.Subscript, ast.Attribute)):
            return False
    teste_a = anterior.test
    e_guard_simples = False
    if isinstance(teste_a, ast.Name):
        e_guard_simples = True
    elif isinstance(teste_a, ast.UnaryOp) and isinstance(teste_a.op, ast.Not):
        e_guard_simples = True
    elif isinstance(teste_a, ast.Compare) and any(
        isinstance(op, (ast.Is, ast.IsNot)) for op in teste_a.ops
    ):
        e_guard_simples = True
    if not e_guard_simples:
        return False
    nomes_a = _nomes(teste_a)
    bases_b = _bases_deref(posterior.test)
    return bool(nomes_a & bases_b)


def _runs_de_asserts(stmts):
    """Runs de Assert consecutivos na mesma lista de instrucoes."""
    runs = []
    atual = []
    for st in stmts:
        if isinstance(st, ast.Assert):
            atual.append(st)
        else:
            if len(atual) >= 2:
                runs.append(list(atual))
            atual = []
    if len(atual) >= 2:
        runs.append(list(atual))
    return runs


def _listas_de_bloco(func_no):
    """Todas as listas de instrucoes do corpo (recursivo, sem entrar em def)."""
    listas = []

    def _visita(stmts):
        listas.append(stmts)
        for st in stmts:
            for campo in ("body", "orelse", "finalbody"):
                sub = getattr(st, campo, None)
                if isinstance(sub, list) and sub and all(
                    isinstance(x, ast.stmt) for x in sub
                ):
                    _visita(sub)
            if isinstance(st, ast.Try):
                for h in getattr(st, "handlers", []):
                    if isinstance(getattr(h, "body", None), list) and h.body:
                        _visita(h.body)

    _visita(list(func_no.body))
    return listas


def _asserts_da_funcao(func_no):
    """Todos os `assert` do corpo (inclusive em for/if/try), sem nested def."""
    saida = []

    def _visita(stmts):
        for st in stmts:
            if isinstance(st, ast.Assert):
                saida.append(st)
            elif isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                continue
            else:
                for campo in ("body", "orelse", "finalbody"):
                    sub = getattr(st, campo, None)
                    if isinstance(sub, list) and sub and all(
                        isinstance(x, ast.stmt) for x in sub
                    ):
                        _visita(sub)
                if isinstance(st, ast.Try):
                    for h in getattr(st, "handlers", []):
                        if isinstance(getattr(h, "body", None), list) \
                                and h.body:
                            _visita(h.body)

    _visita(list(func_no.body))
    return saida


def _classes_de_funcao(func_no):
    """[] | ["ASSERTS_SEQUENCIA"] | ["GUARD_CLAUSE"] por funcao-portao."""
    try:
        seg = ast.get_source_segment(_TEXTO_ATUAL, func_no) or ""
    except Exception:
        seg = ""
    if not _e_portao(func_no.name, seg, func_no):
        return []
    asserts = _asserts_da_funcao(func_no)
    if len(asserts) < 2:
        return []
    # Guard legitima: todo assert apos o primeiro depende de algum anterior
    # (`assert r is not None` ... `assert r["x"] == 3`). Qualquer lado
    # independente sem guardiao e o defeito do G97.
    todos_guard = True
    for j in range(1, len(asserts)):
        if not any(_e_guard(asserts[i], asserts[j]) for i in range(j)):
            todos_guard = False
            break
    if todos_guard:
        return ["GUARD_CLAUSE"]
    return ["ASSERTS_SEQUENCIA"]


_TEXTO_ATUAL = ""


def sitios_do_arquivo(caminho):
    """Achados de um arquivo de teste: {arquivo, funcao, linha, classes}."""
    global _TEXTO_ATUAL
    caminho = pathlib.Path(caminho)
    try:
        texto = caminho.read_text(encoding="utf-8-sig", errors="replace")
        arvore = ast.parse(texto, filename=str(caminho))
    except (SyntaxError, UnicodeDecodeError):
        return []
    try:
        rel = caminho.relative_to(TESTS).as_posix()
    except ValueError:
        rel = caminho.name
    _TEXTO_ATUAL = texto
    try:
        achados = []
        for no in ast.walk(arvore):
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not no.name.startswith("test_"):
                continue
            classes = _classes_de_funcao(no)
            if classes:
                achados.append({"arquivo": rel,
                                "funcao": no.name,
                                "linha": int(getattr(no, "lineno", 0) or 0),
                                "classes": sorted(classes)})
        return achados
    finally:
        _TEXTO_ATUAL = ""


def varredura(raiz=None):
    """Um item por (funcao, classe): {arquivo, funcao, linha, classe}."""
    base = pathlib.Path(raiz) if raiz is not None else TESTS
    achados = []
    for arq in sorted(base.rglob("test_*.py")):
        for sitio in sitios_do_arquivo(arq):
            for classe in sitio["classes"]:
                achados.append({"arquivo": sitio["arquivo"],
                                "funcao": sitio["funcao"],
                                "linha": sitio["linha"],
                                "classe": classe})
    return achados


# ---------------------------------------------------------------------------
# ISENTAS_SEQUENCIA (G97). Guard clauses legitimas e provas de vermelho que
# mantem asserts em sequencia POR DESENHO, com o motivo medido pelo qual
# NAO sao o defeito. Chave (arquivo, funcao); motivo vazio reprova
# (sem_motivo); entrada que nao produz mais classe reprova como nome morto
# (sobrando); funcao que some do disco reprova como ausente.
# Vazio hoje: os portoes foram convertidos a mensagem unica e as provas de
# vermelho por injecao usam um assert por direcao com relatorio completo.
# ---------------------------------------------------------------------------
ISENTAS_SEQUENCIA = {}


def confere(raiz=None, isentos=None):
    """Guarda D87 em forma chamavel: sequencias nao triadas vs isencoes.

    Devolve {"OK", "sequencias", "sobrando", "sem_motivo", "ausentes"}:
      - sequencias: portoes com ASSERTS_SEQUENCIA fora da lista;
      - sobrando: isento que nao produz mais classe (nome morto);
      - sem_motivo: isencao com motivo apagado/vazio;
      - ausentes: isento cujo arquivo sumiu do disco.
    GUARD_CLAUSE nunca e defeito sozinha: so entra aqui se estiver sem
    motivo (para a triagem ficar escrita) ou se virar nome morto.
    """
    iso = ISENTAS_SEQUENCIA if isentos is None else isentos
    achados = varredura(raiz=raiz)
    seq = sorted({(d["arquivo"], d["funcao"])
                  for d in achados if d["classe"] == "ASSERTS_SEQUENCIA"})
    guard = {(d["arquivo"], d["funcao"]) for d in achados
             if d["classe"] == "GUARD_CLAUSE"}
    tem_classe = set(seq) | guard
    sequencias = sorted(s for s in seq if s not in (iso or {}))
    base = pathlib.Path(raiz) if raiz is not None else TESTS
    no_disco = set()
    for arq in base.rglob("test_*.py"):
        try:
            no_disco.add(arq.relative_to(base).as_posix())
        except ValueError:
            no_disco.add(arq.name)
    # sobrando, preciso: isento que nao e mais sequencia nem guard
    sobrando = sorted(k for k in (iso or {}) if k not in tem_classe
                      and k[0] in no_disco)
    sem_motivo = sorted(k for k, m in (iso or {}).items()
                        if not (m or "").strip())
    ausentes = sorted(k for k in (iso or {}) if k[0] not in no_disco)
    return {"OK": not (sequencias or sobrando or sem_motivo or ausentes),
            "sequencias": sequencias, "sobrando": sobrando,
            "sem_motivo": sem_motivo, "ausentes": ausentes}


def relatorio_pt(res):
    """Uma mensagem so com todos os lados (receita do G97)."""
    linhas = ["VARREDURA G97 - ASSERTS EM SEQUENCIA"]
    for lado in ("sequencias", "sobrando", "sem_motivo", "ausentes"):
        linhas.append("  [%s] %d" % (lado, len(res.get(lado) or [])))
        for arquivo, funcao in (res.get(lado) or []):
            linhas.append("    %-9s %s::%s" % (lado, arquivo, funcao))
    return "\n".join(linhas)


def _selftest():
    linhas = varredura()
    assert isinstance(linhas, list)
    assert all(set(d) == {"arquivo", "funcao", "linha", "classe"}
               for d in linhas)
    assert {d["classe"] for d in linhas} <= {"ASSERTS_SEQUENCIA",
                                            "GUARD_CLAUSE"}
    return {"n_sitios": len(linhas)}


if __name__ == "__main__":
    for item in varredura():
        print("%s::%s:%s [%s]" % (item["arquivo"], item["funcao"],
                                  item["linha"], item["classe"]))
