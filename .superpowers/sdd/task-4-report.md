# Task 4 - Relatorio de descoberta deterministica

## Entrega

- Atualizado `tools/loops/discovery.py` com `discover_candidates(project_root)` e
  `rank_candidates(candidates)`.
- Ampliado `tools/loops/tests/test_discovery.py` para cobrir status resolvidos,
  historico explicito, checkboxes, tabelas, fontes normativas e o ID exato.
- A descoberta le somente arquivos locais: a wiki, documentos `REVISAO-*` (com
  o indice excluido), os arquivos explicitos de pendencias em `fontes/` e nomes
  de testes de robustez ou integracao. Nao chama NotebookLM.

## Regras verificadas

- Itens sao delimitados por heading, paragrafo, lista, checkbox ou linha de tabela.
- `RESOLVIDO`, `MERGED`, `FECHADO`, `HOMOLOGADO`, `APROVADO`, `ATENDE`,
  `CORRIGIDO`, `ACATADO` e `JA IMPLEMENTADO` nao geram tarefa sem uma pendencia
  atual explicita.
- `(hist.)` e outros prefixos historicos explicitos sao ignorados.
- `[ ]` entra; `[x]` nao entra; TXT normativo bruto nao e varrido.
- O ID e `sha1(origin + "\\n" + title)[:12]` e a ordem e deterministica por
  prioridade, disciplina, origem e ID.
- Fuzz e itens `nao re-verificados` continuam elegiveis quando representam
  pendencia atual, incluindo T16.

## TDD e verificacao

- RED: os testes novos reproduziram T21 resolvido, tabela historica, prosa TXT,
  checkbox ausente, historico `(hist.)` e estados concluidos.
- GREEN: `python -B -m pytest -p no:cacheprovider tools/loops/tests/test_discovery.py -q`
  -> 12 passed.
- GREEN completo: `python -B -m pytest -p no:cacheprovider tools/loops -q`
  -> 67 passed.
- A execucao real nao produziu T21, `REVISAO-INDICE.md`, `retilineidade`, PNG
  historico ou origens `.txt`; T16 fuzz e multi-vao foram preservados.
- `git diff --check` sem erros nos arquivos da tarefa.
