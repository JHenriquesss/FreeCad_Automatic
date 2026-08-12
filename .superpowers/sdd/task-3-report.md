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

## TDD

1. RED: python -m pytest tools/loops/tests/test_research_nlm.py -q falhou na coleta com ModuleNotFoundError: tools.loops.research_nlm.
2. GREEN: foi implementado o mínimo para os cinco comportamentos requeridos. Uma fixture do teste foi corrigida após a investigação mostrar que ela escrevia \n literal, impedindo o parsing do Markdown real.
3. GREEN final:
   - python -m pytest tools/loops/tests/test_research_nlm.py -q → 6 passed;
   - python -m pytest tools/loops -q → 47 passed.

## Cobertura dos requisitos

- test_list_ready_sources_filters_status_two: aceita somente status inteiro 2.
- test_query_passes_only_requested_source_ids: restringe a chamada a --source-ids, fixa --timeout 120 e grava resposta sem token.
- test_query_parses_list_and_object_json_shapes: cobre lista e objeto com sources.
- test_query_rejects_citation_from_unrequested_source: rejeita citação fora do conjunto consultado.
- test_missing_source_writes_manual_request: registra notebook, título, caminho local, motivo e comando manual, sem enviar a fonte pendente.

## Smoke NotebookLM

Executado separadamente, fora dos testes:

nlm login --check

Resultado: falhou com network_error: ClientAuthenticationError (Could not reach NotebookLM). Nenhuma consulta remota foi executada; os testes permaneceram offline por meio do runner injetável.
