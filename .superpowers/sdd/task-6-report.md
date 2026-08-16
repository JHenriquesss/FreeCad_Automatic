# Task 6: Expose the project coordination policy

## Status

DONE

## Commit de implementação

- `a77ecce feat: expose project coordination policy`

## Escopo entregue

- O core do Loop aceita `coordination_policy` opcional no ProjectSpec.
- O preflight resolve e persiste a política efetiva no formato:
  - `enabled`
  - `folga_mm`
  - `vol_min_mm3`
  - `resolution_mode`
- `folga_mm` e `vol_min_mm3` declarados no projeto sobrescrevem os defaults de execução de `ProjectLoopOptions`.
- `enabled` omisso vira `true`; `resolution_mode` omisso vira `manual_approval`.
- O preflight bloqueia políticas inválidas com `invalid_coordination_policy` antes do runner do adaptador.
- O manifesto persistido inclui `coordination_policy` no topo e `coordination.policy`.
- O hook de coordenação do galpão usa a política efetiva para `folga_mm`/`vol_min_mm3`.
- Quando `enabled=false`, o hook persiste `coordination.status = disabled`, inclui a política efetiva e não cria artefatos em `coordination/`.
- O status geral fica `needs_review` quando a coordenação é desativada, evitando declarar passagem de coordenação.
- O core permanece sem imports de `galpao_turnkey`.

## Arquivos alterados

- `framework/galpao_fw/project_loop.py`
- `framework/galpao_fw/galpao_adapter.py`
- `framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py`
- `.superpowers/sdd/task-6-report.md`

## RED evidence

Comando inicial do brief:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py -k "coordination_policy"
```

Resultado antes da implementação:

```text
FF                                                                       [100%]
FAILED test_project_coordination_policy_overrides_execution_defaults
FAILED test_invalid_project_coordination_policy_is_blocked_before_runner
2 failed, 10 deselected in 1.58s
```

Após adicionar a cobertura `enabled=false`, o RED focado ficou:

```text
FFF                                                                      [100%]
FAILED test_project_coordination_policy_overrides_execution_defaults
FAILED test_invalid_project_coordination_policy_is_blocked_before_runner
FAILED test_disabled_project_coordination_policy_skips_clash_artifacts
3 failed, 10 deselected in 2.55s
```

## GREEN evidence

Política focada:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py -k "coordination_policy"
```

```text
...                                                                      [100%]
3 passed, 10 deselected in 1.87s
```

Generalização completa:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py
```

```text
.............                                                            [100%]
13 passed in 3.48s
```

Regressão branch do Loop:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop
```

```text
........................................................................ [ 34%]
........................................................................ [ 68%]
...................................................................      [100%]
211 passed in 62.16s (0:01:02)
```

Golden trunk:

```powershell
python -m pytest -q framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py
```

```text
.                                                                        [100%]
1 passed in 3.10s
```

Diff/whitespace:

```powershell
git diff --check -- framework/galpao_fw/project_loop.py framework/galpao_fw/galpao_adapter.py framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py
```

```text
exit 0; apenas warnings de normalização LF/CRLF do Git
```

## Self-review

- A validação da política fica em `project_loop.py`, no preflight universal.
- O adaptador galpão consome a política já resolvida pelo manifesto; não há import de motor galpão no core.
- O caminho `enabled=false` retorna antes dos imports e antes de criar `coordination/`.
- `manual_approval` continua sendo o único modo aceito; nenhuma resolução técnica automática foi introduzida.
- Políticas inválidas geram erro de preflight sem disciplina, então `can_execute` fica falso e o runner não executa.
- Specs sem `coordination_policy` preservam defaults de execução.

## Preocupações

- O worktree já tinha muitas alterações sujas não relacionadas antes do início; foram preservadas.
- O commit de implementação inclui os dois testes RED pré-existentes no arquivo de generalização, porque eles estavam no escopo do Task 6 e ainda não estavam commitados.
- O Git emitiu avisos LF/CRLF ao checar/stagear os arquivos tocados; `git diff --check` não encontrou erro de whitespace.
