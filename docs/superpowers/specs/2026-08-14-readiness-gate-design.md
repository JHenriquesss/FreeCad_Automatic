# Gate de prontidão antes do Loop de projeto

## Contexto

O `project_loop` já normaliza o spec e executa um preflight, mas a chamada
normal continua para os calculadores quando não há erro. O framework precisa de
uma etapa explícita entre o Loop de desenvolvimento e o Loop de projeto para
homologar entrada, fontes e capacidades sem produzir entregáveis.

## Decisão

Adicionar um modo `preflight-only` que reutiliza exatamente a normalização e o
preflight existentes e grava um manifesto separado:

- schema: `freecad-automatic/project-readiness`;
- `schema_version`: `1`;
- status: `ready`, `needs_review` ou `blocked`;
- `can_start_project_loop`: verdadeiro somente quando o status é `ready`;
- preflight completo, capacidades do adaptador, local, fontes e disciplinas
  solicitadas preservados para auditoria.

O modo não chama runner de disciplina, coordenação, IFC, FreeCAD ou
`iterate_project`. Ele pode gravar `input/spec.json`,
`reports/preflight.json` e `project-readiness.json`, mas nunca grava
`project-run.json`.

### Classificação

- Qualquer erro do preflight: `blocked`.
- Sem erros e com avisos, incluindo fonte marcada como obsoleta:
  `needs_review`.
- Sem erros nem avisos: `ready`.

`needs_review` é deliberadamente diferente de bloqueio: o relatório pode ser
inspecionado, mas `can_start_project_loop` permanece falso até a revisão.
Chamadores de produção devem usar `--require-source-refs` para transformar
ausência de referências normativas em bloqueio.

Quando `--require-source-refs` está ativo, cada referência deve conter
`source_id` (ou `id`) e um localizador de origem (`notebook_id`, `catalog_id`,
`path`, `uri` ou `url`). Referências malformadas e payloads de disciplina que
não sejam objetos JSON são erros de preflight. Uma pasta que já contém
`project-run.json` é recusada para evitar misturar uma execução antiga com um
readiness novo.

## Interface

No Python:

```python
preflight_project(spec, out_dir=None, options=None) -> dict
preflight_project_file(spec_path, out_dir, options=None) -> dict
```

No CLI, `--preflight-only` usa o mesmo `--spec`, `--out-dir` e opções de fontes
do Loop de projeto. Seu código de saída é `0` para `ready`, `1` para
`needs_review`, `2` para `blocked` e `4` para erro de entrada.

O caminho normal sem `--preflight-only` permanece compatível e continua
executando o Loop de projeto depois do preflight.

## Critérios de aceitação

1. Um spec pronto gera manifesto `ready` sem chamar runner nem criar
   `project-run.json`.
2. O template SJB/ENEL incompleto gera `blocked`, registra caminhos das
   pendências e não executa calculadores.
3. Uma fonte marcada como obsoleta gera `needs_review` e
   `can_start_project_loop=false`.
4. O CLI persiste o manifesto e retorna os códigos definidos; erro semântico de
   transporte retorna `4` sem traceback.
5. A jornada existente do Loop de projeto e sua regressão permanecem verdes.
