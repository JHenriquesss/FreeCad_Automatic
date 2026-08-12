# Task 3 — adaptador NotebookLM e fila de fontes manuais

## Escopo entregue

- Criado tools/loops/research_nlm.py com:
  - NotebookMap.load(path) para o mapa Markdown de notebooks;
  - CatalogIndex.load(path) para o catálogo CSV local;
  - NlmCliAdapter com runner injetável;
  - filtro estrito de fontes cujo status é o inteiro 2;
  - consulta nlm notebook query <notebook_id> <question> --source-ids id1,id2 --timeout 120 --json;
  - validação de que toda citação pertence aos IDs efetivamente consultados;
  - ManualSourceRequest.write(path) para fontes ausentes ou não prontas;
  - artefato JSON da resposta, sanitizado para não persistir campos de credenciais.
- Criado tools/loops/tests/test_research_nlm.py.
- LoopConfig e WorktreeManager não foram alterados.
- Não foram adicionadas dependências runtime.

## Findings corrigidos

1. A sanitização agora percorre dicionários e listas aninhados e substitui por `[REDACTED]` valores em chaves de token, secret, password, credential, authorization, cookie, api-key, csrf, bearer, client-secret, id-token e refresh-token, inclusive com hífen ou underscore. O `EvidenceBundle` é extraído do documento já sanitizado.
2. `query` aceita `source_metadata` opcional para IDs ausentes da listagem. `ManualSourceRequest` preserva `local_hash` e o escreve como `Hash local` na fila Markdown quando fornecido; sem metadados, informa explicitamente que título e caminho local devem ser fornecidos e inclui o `source_id`. Fontes existentes mas não prontas mantêm os metadados obtidos do catálogo.
3. O caminho padrão de pedidos manuais é `.loop-runtime/manual-source-requests.md`; o supervisor ainda pode sobrescrevê-lo por execução.
4. `NotebookMap.notebook_id_for_path` seleciona o prefixo de pasta mais específico, incluindo `fontes/_NOTEBOOKLM_COMPLEMENTAR/01_CONCRETO_DIGITALIZADO`.
5. `_run` rejeita `CommandResult` e `CompletedProcess` com `returncode` não zero, incluindo o `stderr` no erro antes de qualquer parse JSON.
6. O runner padrão usa `subprocess.run(check=False)` e retorna o `CompletedProcess` completo, permitindo que `_run` produza erro explícito com código de retorno e `stderr`, sem deixar `CalledProcessError` escapar.

## TDD

1. RED da correção final: o baseline era `13 passed`; após adicionar a asserção de `local_hash` via `source_metadata` e o teste real com processo não zero, `python -m pytest tools/loops/tests/test_research_nlm.py -q` retornou `2 failed, 12 passed`, reproduzindo os dois findings.
2. GREEN: a implementação mínima adicionou o hash à estrutura e ao Markdown e fez o runner padrão retornar `CompletedProcess`; o teste focal passou com `14 passed`, preservando status estrito `int` igual a `2`, o comando exato de consulta, citações validadas e suporte injetável.
3. GREEN final:
   - `python -m pytest tools/loops/tests/test_research_nlm.py -q` → `14 passed`;
   - `python -m pytest tools/loops -q` → `55 passed`.

## Cobertura dos requisitos

- test_list_ready_sources_filters_status_two: aceita somente status inteiro 2.
- test_query_passes_only_requested_source_ids: restringe a chamada a --source-ids, fixa --timeout 120 e grava resposta sem token.
- test_query_parses_list_and_object_json_shapes: cobre lista e objeto com sources.
- test_query_rejects_citation_from_unrequested_source: rejeita citação fora do conjunto consultado.
- test_missing_source_writes_manual_request: registra notebook, título, caminho local, motivo e comando manual, sem enviar a fonte pendente.
- test_query_redacts_nested_secret_key_patterns_from_artifact_and_evidence: cobre os padrões de segredo em estruturas aninhadas e confirma que nem artefato nem evidência retêm os valores.
- test_missing_source_writes_complete_manual_request_from_local_metadata: cobre `source_metadata` completo para fonte remota ausente.
- test_missing_source_without_metadata_requests_title_and_path: impede título ou caminho inventados.
- test_manual_request_default_is_inside_loop_runtime: garante o default seguro dentro de `.loop-runtime`.
- test_notebook_map_prefers_the_most_specific_real_path_prefix: cobre a entrada complementar real e o prefixo aninhado.
- test_run_rejects_nonzero_command_results_and_preserves_stderr: cobre `CommandResult` e `CompletedProcess` não zero.
- test_default_runner_surfaces_stderr_for_nonzero_process: cobre o runner padrão com processo real não zero, incluindo código de retorno e `stderr`.

## Smoke NotebookLM

Executado separadamente, fora dos testes:

nlm login --check

Resultado: passou para o perfil `default`; a CLI encontrou 64 notebooks. Nenhuma consulta NotebookLM foi executada; os testes permaneceram offline por meio do runner injetável.

## Self-review

- Confirmado: nenhuma alteração em Tasks 1/2, `fontes/` ou dependências.
- Confirmado: `.gitignore` não foi alterado nesta correção.
- Confirmado: o comando de consulta segue exatamente `nlm notebook query <notebook_id> <question> --source-ids <ids> --timeout 120 --json`.
- Confirmado: fontes não prontas não entram no `--source-ids`; citações continuam limitadas aos IDs efetivamente consultados.
- Confirmado: todos os valores secretos exercitados pelos testes são redigidos recursivamente com marcador seguro, inclusive antes da extração da evidência.
- Confirmado: o hash de `source_metadata` aparece na fila manual e falhas reais do subprocesso não escapam como `CalledProcessError` sem diagnóstico.
