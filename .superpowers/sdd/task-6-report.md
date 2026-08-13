# Task 6 - Adaptadores de agente e revisor

## Entrega

- Criado `tools/loops/agents.py` com `AgentRequest`, `AgentResult`, adaptadores
  Codex/Claude, prompts delimitados, argv sanitizado e artefato de saida.
- Criado `tools/loops/reviewer.py` com `ReviewerRequest`, `ReviewResult` e gates
  locais de evidencia/citacao, targeted, regressao, escopo e fontes remotas.
- Criados os prompts versionados em `tools/loops/prompts/`.
- Criados fakes e testes em `tools/loops/tests/test_agents_and_reviewer.py`.

## Politicas verificadas

- Codex usa `workspace-write`, aprovacao `never`, worktree explicita, artefato
  `--output-last-message` e stdin; Claude usa modo print, `acceptEdits`, JSON,
  sem persistencia de sessao e `--add-dir` na worktree.
- Nao ha bypass destrutivo, push, merge, reset ou remocao ampla.
- O prompt exige source IDs/citacoes, RED antes da correcao, mudanca minima,
  escopo e registro de incerteza.
- O revisor rejeita citacao ausente/invalida, alvo ausente/falho, nova regressao,
  arquivo fora do escopo e alteracao em `fontes/`/sources.
- Saidas completas e arquivos tocados sao registrados; argv e sanitizado para
  tokens, cookies, senhas e chaves.

## TDD e verificacao

- RED: coleta inicial falhou por ausencia de `tools.loops.agents`.
- GREEN focado: `python -B -m pytest -p no:cacheprovider tools/loops/tests/test_agents_and_reviewer.py -q` -> 7 passed.
- GREEN completo: `python -B -m pytest -p no:cacheprovider tools/loops -q` -> 82 passed.
- Warning de coleta por `TestSnapshot` importado foi eliminado no teste.
- Compilacao dos adaptadores e testes passou.
- Nenhum Codex/Claude/rede foi invocado durante os testes.
- A revisao delegada permaneceu inconclusiva por timeout; foi feita auditoria
  local adicional e a suite independente permaneceu verde.
