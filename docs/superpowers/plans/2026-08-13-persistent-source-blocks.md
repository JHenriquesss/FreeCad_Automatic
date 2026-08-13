# Persistent Source Blocks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persistir bloqueios documentais do loop, reabrindo tarefas somente após mudança observável das fontes ou `--retry-blocked`.

**Architecture:** `DevelopmentSupervisor` será o dono do registro JSON em `.loop-runtime`; a descoberta calcula uma assinatura local determinística e filtra somente registros com assinatura igual. `LoopConfig` carregará a flag booleana do CLI, enquanto o ledger continuará sendo a fonte do resultado da execução.

**Tech Stack:** Python 3, `dataclasses`, `hashlib`, `json`, `pytest`, CLI argparse.

## Global Constraints

- Somente evidência auditável do NotebookLM pode liberar implementação.
- O estado operacional deve permanecer dentro de `.loop-runtime`.
- Não consultar a web nem alterar fontes durante a descoberta.
- Todo comportamento novo deve ter teste RED observado antes do código de produção.

---

### Task 1: Configuração e contrato do retry

**Files:**
- Modify: `tools/loops/models.py` — adicionar `retry_blocked: bool = False` ao `LoopConfig`.
- Modify: `tools/loops/config.py` — aceitar, validar e propagar `retry_blocked`.
- Modify: `tools/loops/__main__.py` — adicionar `--retry-blocked` e propagar a flag ao `LoopConfig` carregado por arquivo ou CLI.
- Test: `tools/loops/tests/test_config.py` e `tools/loops/tests/test_cli.py`.

**Interfaces:**
- Consumes: `LoopConfig` existente e `build_parser()`.
- Produces: `config.retry_blocked`, sempre booleano, default `False`.

- [x] **Step 1: Write the failing test**

```python
def test_cli_exposes_retry_blocked():
    args = build_parser().parse_args(["--retry-blocked"])
    assert args.retry_blocked is True

def test_config_rejects_non_boolean_retry_blocked(tmp_path):
    path = tmp_path / "loop.json"
    path.write_text('{"retry_blocked": "yes"}', encoding="utf-8")
    with pytest.raises(ValueError, match="retry_blocked"):
        load_config(path, tmp_path)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tools/loops/tests/test_cli.py::test_cli_exposes_retry_blocked tools/loops/tests/test_config.py::test_config_rejects_non_boolean_retry_blocked -q`

Expected: FAIL because the parser and `LoopConfig` do not expose the option.

- [x] **Step 3: Write minimal implementation**

Adicionar o campo default ao dataclass, `parser.add_argument("--retry-blocked", action="store_true")`, validação `type(value) is bool` e propagação nos dois construtores de configuração.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tools/loops/tests/test_cli.py::test_cli_exposes_retry_blocked tools/loops/tests/test_config.py::test_config_rejects_non_boolean_retry_blocked -q`

Expected: PASS.

- [x] **Step 5: Commit**

```powershell
git add tools/loops/models.py tools/loops/config.py tools/loops/__main__.py tools/loops/tests/test_cli.py tools/loops/tests/test_config.py
git commit -m "feat: expose persistent source retry option"
```

### Task 2: Registro e assinatura dos bloqueios

**Files:**
- Modify: `tools/loops/supervisor.py` — registrar, ler, assinar e limpar bloqueios.
- Test: `tools/loops/tests/test_supervisor.py`.

**Interfaces:**
- Consumes: `TaskCandidate`, `project_root`, `runtime_dir` e `retry_blocked`.
- Produces: `.loop-runtime/blocked-tasks.json`, `_source_signature(candidate)` e `_blocked_task_ids(candidates)` internos ao supervisor.

- [x] **Step 1: Write the failing test**

```python
def test_missing_source_persists_block_and_same_signature_is_skipped(tmp_path):
    h, cfg = harness(tmp_path)
    h.research.error = MissingSourceRequired("NBR ausente")
    first = make_supervisor(h, cfg).run_once()
    assert first.outcome == "manual_source_required"
    block_path = Path(cfg.runtime_dir) / "blocked-tasks.json"
    document = json.loads(block_path.read_text(encoding="utf-8"))
    assert document["tasks"]["task-1"]["reason"] == "missing_source"

    second = make_supervisor(h, cfg).run_once()
    assert second.outcome == "no_candidate"
    assert h.research.calls == 1
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tools/loops/tests/test_supervisor.py::test_missing_source_persists_block_and_same_signature_is_skipped -q`

Expected: FAIL because no persistent registry is written or read.

- [x] **Step 3: Write minimal implementation**

Implementar leitura validada do documento, fingerprint seguro de arquivos sob `fontes/`, SHA-256 determinístico, filtro em `_discover()`, gravação em `_park_manual_source()` e limpeza quando o candidato é selecionado ou promovido.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tools/loops/tests/test_supervisor.py::test_missing_source_persists_block_and_same_signature_is_skipped -q`

Expected: PASS.

- [x] **Step 5: Commit**

```powershell
git add tools/loops/supervisor.py tools/loops/tests/test_supervisor.py
git commit -m "feat: persist manual source blocks"
```

### Task 3: Reabertura por mudança, retry e limpeza

**Files:**
- Modify: `tools/loops/supervisor.py` — respeitar `retry_blocked` e remover registros em promoção.
- Test: `tools/loops/tests/test_supervisor.py`, `tools/loops/tests/test_cli.py`.

**Interfaces:**
- Consumes: registro da Task 2 e `LoopConfig.retry_blocked`.
- Produces: reabertura determinística sem alterar o filtro de tarefas concluídas.

- [x] **Step 1: Write the failing tests**

```python
def test_changed_declared_source_reopens_blocked_task(tmp_path):
    h, cfg = harness(tmp_path)
    source = h.root / "fontes" / "02_ACO" / "norma.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"versao-1")
    h.discover.candidates = (replace(task(), source_paths=("02_ACO/norma.pdf",)),)
    h.research.error = MissingSourceRequired("sem OCR")
    assert make_supervisor(h, cfg).run_once().outcome == "manual_source_required"
    source.write_bytes(b"versao-2")
    h.research.error = None
    assert make_supervisor(h, replace(cfg, mode="dry-run")).run_once().outcome == "dry_run"

def test_retry_blocked_reopens_without_source_change(tmp_path):
    h, cfg = harness(tmp_path)
    h.research.error = MissingSourceRequired("fonte ausente")
    assert make_supervisor(h, cfg).run_once().outcome == "manual_source_required"
    retry_cfg = replace(cfg, retry_blocked=True, mode="dry-run")
    h.research.error = None
    assert make_supervisor(h, retry_cfg).run_once().outcome == "dry_run"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tools/loops/tests/test_supervisor.py -k "changed_declared_source or retry_blocked" -q`

Expected: FAIL because the persistent record still filters the candidate.

- [x] **Step 3: Write minimal implementation**

Ignorar registros persistidos somente quando `config.retry_blocked` for verdadeiro; após promoção, remover a tarefa do registro e manter o registro vazio válido.

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tools/loops/tests/test_supervisor.py -k "changed_declared_source or retry_blocked" -q`

Expected: PASS.

- [x] **Step 5: Commit**

```powershell
git add tools/loops/supervisor.py tools/loops/tests/test_supervisor.py tools/loops/tests/test_cli.py
git commit -m "feat: reopen blocked tasks after source changes"
```

### Task 4: Documentar, rodar suíte e auditar estado

**Files:**
- Modify: `tools/README.md` — documentar arquivo e flag.
- Modify: `sessions/2026-08-13.md` — registrar RED, GREEN e fechamento.
- Test: `tools/loops/tests/` — suíte completa.

**Interfaces:**
- Consumes: comportamento das Tasks 1–3.
- Produces: documentação operacional e evidência de verificação.

- [x] **Step 1: Write the failing test**

Não há novo comportamento nesta tarefa; os testes das Tasks 1–3 são o contrato.

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tools/loops/tests -q`

Expected: nenhum teste novo falha após as Tasks 1–3.

- [x] **Step 3: Write minimal implementation**

Adicionar à documentação o fluxo: bloqueio → assinatura → reabertura por mudança ou `--retry-blocked`, sem mencionar upload automático.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tools/loops/tests -q; python -m py_compile tools/loops/*.py`

Expected: todos os testes passam e a compilação termina sem erro.

- [x] **Step 5: Commit**

```powershell
git add tools/README.md sessions/2026-08-13.md
git commit -m "docs: record persistent source block workflow"
```
