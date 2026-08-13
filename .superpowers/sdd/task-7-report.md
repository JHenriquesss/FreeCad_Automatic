# Task 7 - Supervisor da maquina de estados

## Entrega

- Criado `tools/loops/supervisor.py` com `SupervisorDeps`, `RunOutcome`,
  `DevelopmentSupervisor.run_once()` e `.resume(loop_id)`.
- Criado `tools/loops/tests/test_supervisor.py` com 13 cenarios fake.
- O supervisor persiste task/evidence/plan/baseline/targeted/regression/delta,
  review, resumo e promocao no run; o ledger e salvo antes/depois das transicoes.

## Politicas verificadas

- Dry-run descobre, pesquisa e planeja, mas nao cria worktree nem chama red,
  agente, testes ou revisor.
- Fonte ausente, red falho, targeted falho, regressao nova, build falho,
  timeout, revisao rejeitada e HEAD externo estacionam sem apagar worktree.
- Targeted, regression e build respeitam seus gates; build so e exigido pela
  dependencia `build_required` ou por tarefa explicitamente marcada.
- Retomada reidrata snapshots, delta e resultado do agente de artefatos
  persistidos; ledger ativo nao pode ser sobrescrito por uma nova rodada.
- Tentativas sao limitadas por fase; `command_timeout` e separado de falha
  funcional; a promocao inicial e commit local na worktree.
- Caminhos de teste relativos a raiz sao normalizados para o cwd do framework.

## TDD e verificacao

- RED: coleta inicial falhou por ausencia de `tools.loops.supervisor`.
- GREEN supervisor: `python -B -m pytest -p no:cacheprovider tools/loops/tests/test_supervisor.py -q` -> 13 passed.
- GREEN completo: `python -B -m pytest -p no:cacheprovider tools/loops -q` -> 100 passed.
- Compilacao do supervisor passou; nenhum serviço externo ou NotebookLM foi
  chamado nos testes.
- Revisao delegada nao retornou dentro do limite operacional; foi feita
  auditoria local adicional e os testes cobriram as falhas de integração.
