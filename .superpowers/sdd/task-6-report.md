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

## Correcao Task 6 strict JSON (2026-08-16)

### Defeito corrigido

- Raiz: `_json_safe` mantinha `float("nan")` como `float`, e `_write_json` usava o encoder padrao do Python, que persiste `NaN` nao padrao.
- Correcao: `_json_safe` converte floats nao finitos para marcador textual JSON-safe e `_write_json` agora usa `allow_nan=False` como guarda centralizada.
- O bloqueio de preflight nao foi mascarado: a execucao continua com `status=blocked` e erro `invalid_coordination_policy`.

### RED evidence

```powershell
python -m pytest framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py::test_non_finite_coordination_policy_is_persisted_as_strict_json -q
```

```text
F                                                                        [100%]
FAILED framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py::test_non_finite_coordination_policy_is_persisted_as_strict_json
ValueError: non-finite JSON constant: NaN
1 failed in 0.47s
```

### GREEN evidence

Foco:

```powershell
python -m pytest framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py::test_non_finite_coordination_policy_is_persisted_as_strict_json -q
```

```text
.                                                                        [100%]
1 passed in 0.24s
```

Verificacao direta de persistencia estrita e bloqueio:

```text
status=blocked
reports/preflight.json:strict=ok
preflight.ok=False
preflight.error.value='nan'
project-run.json:strict=ok
manifest.status=blocked
manifest.input.folga_mm='nan'
manifest.error.code=invalid_coordination_policy
input/spec.json:strict=ok
```

Arquivo de generalizacao:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py
```

```text
..............                                                           [100%]
14 passed in 3.75s
```

Suite de branches `project_loop`:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop
```

```text
........................................................................ [ 33%]
........................................................................ [ 67%]
....................................................................     [100%]
212 passed in 63.62s (0:01:03)
```

### Self-review

- A protecao ficou centralizada no caminho de serializacao usado pelos artefatos auditaveis.
- Valores numericos finitos continuam sendo persistidos como numeros.
- Valores nao finitos rejeitados continuam visiveis como marcador textual, sem se tornarem parametro valido.
- `allow_nan=False` impede regressao silenciosa caso outro caminho deixe passar float nao finito.
- Nenhuma regra de engenharia ou resolucao automatica foi adicionada.

### Preocupacoes

- O worktree ja estava amplamente sujo antes da correcao; o commit deve ser seletivo para `project_loop.py`, o teste RED e este relatorio.
