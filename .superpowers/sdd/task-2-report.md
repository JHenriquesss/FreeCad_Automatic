# Task 2 — configuração e worktrees isoladas

## Status

Implementação concluída em escopo local, com TDD RED/GREEN, self-review e validação da suíte de `tools/loops`.

## Implementação

- `tools/loops/config.py` implementa `load_config(path, project_root)` com JSON, caminhos absolutos ancorados no projeto e defaults seguros:
  - modo `supervised`;
  - executor `codex`;
  - uma iteração;
  - três tentativas por fase;
  - timeout de comando de 900 segundos;
  - timeout de build de 1800 segundos.
- `tools/loops/worktrees.py` implementa `WorktreeManager`:
  - cria `git worktree add -b loop/<loop_id> <runtime>/worktrees/<loop_id> <base_commit>`;
  - rejeita IDs vazios, com separadores, traversal ou caracteres inseguros;
  - detecta alteração do HEAD do root e levanta `ExternalChangeError`;
  - remove somente um caminho registrado pelo Git e confinado ao runtime.
- `tools/loops/models.py` recebeu o `LoopConfig` declarado no contrato da Task 1, que não estava presente no arquivo existente.
- `.gitignore` recebeu somente `.loop-runtime/`; as regras preexistentes de `sessions/` e `/fontes/` foram preservadas.
- Não foram adicionadas dependências runtime nem alterada a lógica de engenharia.

## Arquivos

- `.gitignore`
- `tools/loops/models.py`
- `tools/loops/config.py`
- `tools/loops/worktrees.py`
- `tools/loops/tests/test_config_worktrees.py`
- `.superpowers/sdd/task-2-report.md`

## TDD e testes

### RED

Antes da produção, foi executado:

```powershell
python -m pytest tools/loops/tests/test_config_worktrees.py -q
```

Resultado: falha na coleta com `ModuleNotFoundError: No module named 'tools.loops.config'`.

### GREEN

Após a implementação mínima:

- `python -m pytest tools/loops/tests/test_config_worktrees.py -q` — `12 passed`.
- `python -m pytest tools/loops -q` — `37 passed`.
- Baseline anterior da Task 2: `python -m pytest tools/loops/tests/test_ledger.py -q` — `25 passed`.
- `git diff --check` — sem erros de whitespace nos arquivos versionados alterados.

Os testes focados usam repositórios Git temporários reais e verificam resolução de configuração, commit-base exato, imutabilidade do root, detecção de alteração externa, confinamento de remoção e rejeição de IDs inseguros.

## Self-review

- Os caminhos relativos de configuração e runtime são resolvidos a partir de `project_root`.
- A criação usa o commit recebido, não o estado implícito do branch atual.
- A criação não modifica o HEAD nem os arquivos rastreados do root.
- A remoção consulta os worktrees registrados pelo Git e valida o caminho absoluto antes de remover.
- O nome da branch criada é `loop/<loop_id>`.
- Alterações não relacionadas em `.gitignore`, `docs/`, `.omo/` e diretórios de saída permaneceram fora do escopo do commit.

## Commit

Mensagem solicitada: `feat: isolate development loop worktrees`

## Correção dos findings do revisor

### Findings

1. `WorktreeManager.assert_base_unchanged` comparava o HEAD completo diretamente com o texto de `base_commit`, rejeitando abreviações válidas.
2. `_validate_loop_id` aceitava `a..b` e `a.`, embora as branches `loop/a..b` e `loop/a.` fossem inválidas no Git; a falha posterior ocorria depois de criar o diretório de runtime.

### RED

- Foi adicionado `test_assert_base_unchanged_accepts_abbreviated_commit`; sua execução isolada falhou com `ExternalChangeError` porque o HEAD completo era comparado a `13e0ab77`.
- Foi adicionado `test_git_invalid_loop_id_is_rejected_before_runtime_creation`, parametrizado para `a..b` e `a.`; a execução isolada falhou duas vezes com `CalledProcessError` do Git, confirmando que a validação anterior era insuficiente.

### GREEN

- `assert_base_unchanged` agora normaliza o argumento com `git rev-parse <base_commit>^{commit}` antes de comparar.
- `_validate_loop_id` agora rejeita IDs contendo `..` ou terminados em `.`, antes de `mkdir`.
- `python -m pytest tools/loops/tests/test_config_worktrees.py -q` — `15 passed`.
- `python -m pytest tools/loops -q` — `40 passed`.

### Self-review

- O commit abreviado é resolvido pelo Git e continua sendo comparado ao HEAD completo.
- `a..b` e `a.` geram `ValueError` e não criam `.loop-runtime` nem `worktrees` parcial.
- A alteração mantém o alfabeto seguro existente e não adiciona dependências.
- Nenhuma lógica de engenharia, regra de `.gitignore`, documentação, `.omo` ou saída não relacionada foi alterada nesta correção.
