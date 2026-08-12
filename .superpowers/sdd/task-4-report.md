# Task 4 — Relatório de descoberta determinística

## Entrega

- Criado `tools/loops/discovery.py` com `discover_candidates(project_root)` e
  `rank_candidates(candidates)`.
- Criado `tools/loops/tests/test_discovery.py` com os cinco comportamentos
  exigidos pelo brief.
- A descoberta lê somente arquivos locais: threads abertas, documentos
  `REVISAO-*`, pendências textuais em `fontes/` e nomes de testes de robustez
  ou integração. Não chama NotebookLM.

## Regras verificadas

- Cada candidato é respaldado por um item que declara pendência, bloqueio,
  lacuna, fuzz não feito ou item não re-verificado.
- Itens exclusivamente resolvidos não entram; uma pendência explícita no mesmo
  item permanece elegível.
- O ID é `sha1(origin + "\\n" + title)[:12]`.
- A ordem é determinística por prioridade observada, disciplina, origem e ID.
- A priorização favorece segurança estrutural, validação, regressão, fuzz e
  lacunas abertas; depois aplica a ordem de disciplinas definida no brief.

## TDD

- RED inicial: `ModuleNotFoundError` para `tools.loops.discovery`.
- GREEN: os cinco testes passaram após a implementação mínima.
- RED adicional: pendência multiline com texto resolvido no mesmo item era
  descartada.
- GREEN adicional: o leitor passou a acumular parágrafos e itens Markdown
  antes de classificá-los.

## Self-review

- Estado atual: 61 candidatos, IDs únicos e ordem repetível.
- Confirmado: candidato `Fuzz interno dos motores` presente.
- Confirmado: thread resolvida de dupla-conversão de janela ausente.
- `git diff --check` sem erros para os arquivos da Task 4.

## Testes

~~~text
python -m pytest tools/loops/tests/test_discovery.py -q  -> 5 passed
python -m pytest tools/loops -q                         -> 60 passed
~~~
