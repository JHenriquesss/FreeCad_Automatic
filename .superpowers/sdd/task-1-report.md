# Task 1 — contrato de estado, schema e ledger

## Implementação

- Criado `tools/loops/models.py` com `LoopPhase`, `VALID_TRANSITIONS` e os dataclasses do contrato (`TaskCandidate`, `SourceRecord`, `Citation`, `EvidenceBundle`, `CommandResult`, `LoopState`).
- Implementada serialização explícita `to_dict`/`from_dict`, preservando enums e coleções vazias.
- Criado `tools/loops/ledger.py` com `Ledger.load`, `Ledger.save` e `Ledger.transition`.
- O ledger valida campos essenciais, modos e fases na entrada e na saída, sem dependências runtime novas.
- A persistência escreve em temporário no mesmo diretório e usa `os.replace`; transições inválidas são rejeitadas antes da persistência.
- Criado `tools/loops/schema/development-loop.schema.json` com campos obrigatórios, enumeração de modos/fases e tipos essenciais.

## Arquivos

- `tools/loops/models.py`
- `tools/loops/ledger.py`
- `tools/loops/schema/development-loop.schema.json`
- `tools/loops/tests/test_ledger.py`

## Comandos e resultados

- `python -m pytest tools/loops/tests/test_ledger.py -q` antes da produção: RED na coleta, `ModuleNotFoundError: No module named 'tools.loops.ledger'`.
- `python -m pytest tools/loops/tests/test_ledger.py -q` depois da produção: `4 passed in 0.07s`.
- `python -m pytest tools/loops -q`: `4 passed in 0.09s`.
- `git diff --check`: sem erros de whitespace nos arquivos versionados já rastreados; os arquivos novos foram revisados no diff final.

## Evidência RED/GREEN

Os quatro testes exigidos foram escritos antes da produção. A execução inicial falhou durante a coleta pela ausência do módulo de ledger. Após a implementação mínima, os quatro testes passaram, cobrindo round-trip, fase esperada, JSON válido após replacement e não mutação em transição inválida.

## Self-review

- Escopo limitado aos artefatos da Task 1 e ao relatório solicitado; alterações existentes em `.gitignore`, `.omo/`, `docs/` e saídas foram preservadas fora do commit.
- Não foram adicionadas dependências runtime.
- A transição verifica fase esperada e whitelist antes de salvar.
- `save` remove o temporário remanescente em caso de erro; `os.replace` mantém a substituição atômica no mesmo diretório.
- Testes exercitam o objeto real e validam regras essenciais do schema com `json`/stdlib.

## Preocupações

- A validação implementada cobre as regras essenciais usadas nesta fatia; validação genérica de JSON Schema e contratos dos adaptadores ficam para tarefas posteriores.
- A suíte global do repositório não foi executada porque esta task delimita a validação ao ledger isolado; a suíte própria `tools/loops` foi executada integralmente e está verde.
