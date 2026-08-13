# Loop Completion Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o scheduler distinguir conclusões promovidas no branch atual de registros históricos de outros branches.

**Architecture:** O supervisor continuará sendo a fonte do filtro, mas delegará a validação de cada `promoted_commit` a uma consulta Git segura e limitada ao repositório do projeto. Registros inválidos permanecem no JSON e apenas deixam de bloquear a descoberta.

**Tech Stack:** Python 3.12, `subprocess`, `pytest`, Git e o runtime JSON existente em `.loop-runtime/`.

## Global Constraints

- `completed-tasks.json` continua sendo estado de runtime e não deve ser editado pelo código de descoberta.
- Só um commit ancestral de `HEAD` pode bloquear uma candidata.
- A consulta Git usa argv sem shell e falha fechada para o registro, não para o scheduler.
- Testes do loop usam repositórios temporários reais, sem mockar a semântica de ancestralidade.

---

### Task 1: filtro de conclusões por ancestralidade Git

**Files:**
- Modify: `tools/loops/tests/test_supervisor.py`
- Modify: `tools/loops/supervisor.py:457-464`
- Modify: `tools/README.md` na seção de estado do loop

**Interfaces:**
- Consumes: `TaskCandidate.id`, `completed-tasks.json`, `self.project_root` e `git merge-base --is-ancestor`.
- Produces: `_completed_task_ids() -> frozenset[str]` filtrado por commits alcançáveis.

- [ ] **Step 1: Write the failing tests**

Adicionar ao teste do supervisor casos que gravem um registro com o commit-base
real e outro com um commit válido criado em uma branch paralela. O primeiro deve
retornar `no_candidate`; o segundo deve selecionar `task-1`. Adicionar também um
registro com `promoted_commit` ausente e outro com valor inválido; ambos devem
deixar a candidata elegível.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tools/loops/tests/test_supervisor.py -q`

Expected: os casos com commit paralelo, ausente ou inválido falham porque o
filtro atual considera qualquer chave do registro como concluída.

- [ ] **Step 3: Write minimal implementation**

Substituir o retorno direto de `frozenset(tasks)` por uma filtragem que:

```python
return frozenset(
    task_id
    for task_id, record in tasks.items()
    if isinstance(record, dict)
    and self._commit_is_ancestor(record.get("promoted_commit"))
)
```

Adicionar `_commit_is_ancestor(self, commit) -> bool`, executando:

```python
subprocess.run(
    ["git", "-C", str(self.project_root), "merge-base", "--is-ancestor", commit, "HEAD"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    check=False,
)
```

Retornar `False` para tipo não string, string vazia, `OSError` ou código de
retorno diferente de zero.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tools/loops/tests/test_supervisor.py -q`

Expected: todos os testes do arquivo passam.

- [ ] **Step 5: Update documentation and commit**

Documentar em `tools/README.md` que um registro de promoção só vale enquanto o
commit for ancestral do `HEAD`; registros históricos permanecem no arquivo e
voltam à fila. Rodar `git diff --check` e criar commit:

```powershell
git add tools/loops/supervisor.py tools/loops/tests/test_supervisor.py tools/README.md
git commit -m "fix: reconcile completed loop tasks with git history"
```

### Task 2: verificação do scheduler real

**Files:**
- Modify: `.loop-runtime/completed-tasks.json` somente como estado runtime local, se necessário
- Test: `.loop-runtime/scheduler-last.json`

**Interfaces:**
- Consumes: commits reais `05f529d`, `03e9f80`, `8e500d6` e registros históricos existentes.
- Produces: dry-run que não repete uma tarefa cujo commit está no branch e torna elegível a próxima tarefa cujo commit não está.

- [ ] **Step 1: Reconciliar somente registros comprovados**

Adicionar ao `completed-tasks.json` as tarefas FV já promovidas apenas com seus
IDs descobertos e commits ancestrais reais; não alterar registros de tarefas
cujos commits não pertencem ao branch.

- [ ] **Step 2: Rodar descoberta e dry-run**

Run: `python -m tools.loops --mode dry-run --max-iterations 1 --command-timeout 180 --build-timeout 300`

Expected: `scheduler-last.json` e `ledger.json` mostram uma candidata não
concluída; o validador FV não volta a ser selecionado quando seu registro tem
commit ancestral.

- [ ] **Step 3: Verificar regressão**

Run: `python -m pytest tools/loops/tests -q`

Expected: todos os testes do loop passam.
