# Research Scope Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Impedir consultas amplas do NotebookLM quando uma candidata não declarar fontes normativas locais exatas.

**Architecture:** O CLI de pesquisa valida `TaskCandidate.source_paths` antes de resolver fontes. O supervisor classifica a mensagem como lacuna manual e registra o bloqueio; candidatos atômicos continuam no caminho existente de seleção por caminho e hash.

**Tech Stack:** Python 3.12, pytest, `tools/loops`, NotebookLM CLI somente para verificação real.

## Global Constraints

- Uma candidata sem `source_paths` nunca chama `list_ready_sources()` nem `nlm notebook query`.
- A fonte normativa deve ser indicada por caminho relativo à pasta `fontes/`.
- Não inferir fontes por título, não consultar web e não alterar fontes remotas.
- A alteração deve passar por RED observado antes do código de produção.

---

### Task 1: Guardar o contrato de pesquisa

**Files:**
- Modify: `tools/loops/__main__.py`
- Modify: `tools/loops/supervisor.py`
- Test: `tools/loops/tests/test_cli.py`
- Test: `tools/loops/tests/test_supervisor.py`

**Interfaces:**
- Consumes: `TaskCandidate.source_paths`.
- Produces: `ValueError("candidate source scope is required ...")` antes da seleção de fontes para candidatas sem escopo; classificação como `manual_source_required` no supervisor.

- [x] **Step 1: Escrever o teste RED do CLI**

```python
def test_research_candidate_rejects_empty_source_scope_before_notebook_query():
    class Adapter:
        notebook_map = NotebookMap({"09_INCENDIO": "nb-incendio"})

        def list_ready_sources(self, notebook_id):
            raise AssertionError("broad source listing must not run")

    candidate = TaskCandidate(
        "id", "Pendência ampla", "seguranca", "wiki:T1", 1,
        ("wiki.md",), (), topic="geral", source_paths=(),
    )

    with pytest.raises(ValueError, match="source_paths"):
        _research_candidate(Adapter(), candidate)
```

- [x] **Step 2: Rodar RED**

Run: `python -m pytest tools/loops/tests/test_cli.py::test_research_candidate_rejects_empty_source_scope_before_notebook_query -q`

Expected: falha porque o código atual chama `list_ready_sources()` para escopo vazio.

- [x] **Step 3: Implementar o gate e a classificação do supervisor**

```python
# tools/loops/__main__.py::_research_candidate
if not candidate.source_paths:
    raise ValueError(
        "candidate source scope is required; declare source_paths before querying NotebookLM"
    )

# tools/loops/supervisor.py::_looks_like_missing_source
if "source scope" in message or "source_paths" in message:
    return True
```

- [x] **Step 4: Escrever e rodar o teste RED/GREEN do supervisor**

O teste deve fornecer uma candidata sem escopo e uma pesquisa fake que levanta
`ValueError("candidate source scope is required")`; o resultado esperado é
`manual_source_required`, com `blocked-tasks.json` contendo `source_paths: []` e
sem criação de worktree.

Run: `python -m pytest tools/loops/tests/test_cli.py tools/loops/tests/test_supervisor.py -q`

Expected: todos passam após a guarda.

- [x] **Step 5: Commit**

```powershell
git add tools/loops/__main__.py tools/loops/supervisor.py tools/loops/tests/test_cli.py tools/loops/tests/test_supervisor.py
git commit -m "fix: reject unscoped NotebookLM research"
```

### Task 2: Documentar a política e verificar o diagnóstico real

**Files:**
- Modify: `tools/README.md`
- Modify: `sessions/2026-08-13.md`
- Modify: `.superpowers/sdd/progress.md`
- Runtime: `.loop-runtime/runs/<loop_id>/`, `.loop-runtime/blocked-tasks.json`

**Interfaces:**
- Consumes: o timeout `loop-20260813T214243716844Z` e a nova guarda.
- Produces: política documentada, bloqueio auditável da candidata ampla e uma
  execução posterior que não chama o NotebookLM para escopo vazio.

- [x] **Step 1: Atualizar o README**

Acrescentar que `source_paths=()` é uma falha de escopo: o loop estaciona e pede
decomposição atômica; nunca significa “todas as fontes do notebook”.

- [x] **Step 2: Rodar a suíte completa do loop**

Run: `python -m pytest tools/loops/tests -q`

Expected: todos os testes passam, incluindo a regressão do timeout.

- [x] **Step 3: Reautenticar e executar dry-run controlado**

Run: `nlm login --check` e
`python -m tools.loops --mode dry-run --max-iterations 1 --executor codex --command-timeout 120`.

Expected: a candidata ampla estaciona como `manual_source_required` rapidamente,
sem `evidence.json` e sem `nlm notebook query`; o ledger preserva o timeout anterior
como diagnóstico histórico.

- [x] **Step 4: Verificar e registrar**

Run: `python -m py_compile tools/loops/__main__.py tools/loops/supervisor.py; git diff --check`.
Registrar source scope, timeout histórico, outcome novo, testes e carry-over.

- [x] **Step 5: Commit de documentação**

```powershell
git add tools/README.md sessions/2026-08-13.md .superpowers/sdd/progress.md
git commit -m "docs: record NotebookLM scope guard"
```

## Phase checklist

### Must exist

- [x] Gate test-first para candidatas sem escopo.
- [x] Bloqueio manual no supervisor sem chamada ampla ao NLM.
- [x] Regressão dos candidatos atômicos com fontes declaradas.
- [x] Registro do timeout histórico e da correção.

### Must not exist

- [x] `list_ready_sources()` como fallback em `_research_candidate`.
- [x] Consulta `nlm notebook query` para `source_paths=()`.
- [x] Inferência silenciosa de fonte ou edição.

## Next phase seed

Após a guarda, reexecutar a triagem; decompor a próxima pendência com fonte pronta ou registrar solicitação manual específica.
