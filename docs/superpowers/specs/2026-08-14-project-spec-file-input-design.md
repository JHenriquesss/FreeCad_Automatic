# Entrada de spec de projeto por arquivo

**Data:** 2026-08-14  
**Status:** aprovado para implementação  
**Escopo:** primeira entrada operacional do Loop de projeto

## Problema

O `project_loop` já recebe dicionários Python, executa o adaptador de galpão,
persiste manifestos e permite iterações. Para uso real, o engenheiro precisa
preencher um arquivo de projeto e executar o mesmo caminho sem escrever um
script auxiliar. Também é necessário que o template inicial seja seguro:
campos desconhecidos não podem virar defaults silenciosos.

## Decisão

Adicionar uma camada pequena de entrada de arquivo, sem duplicar o motor:

- `project_io.load_project_spec(path)` lê JSON UTF-8, exige objeto na raiz e
  valida `schema`/`schema_version` quando o envelope versionado está presente;
  specs legados continuam aceitos explicitamente.
- `project_io.run_project_file(path, out_dir, options=None, ...)` carrega o
  arquivo e delega integralmente a `project_loop.run_project`.
- `project_loop` reexporta essas duas funções para manter uma API única.
- `project_loop_cli.py` oferece `spec -> project-run.json`, opções de geração e
  códigos de saída: 0 para `passed`/`needs_review`, 2 para `blocked`, 3 para
  `failed` e 4 para erro de entrada.
- `projects/galpao-sjb/project-spec.template.json` contém somente o local
  fornecido pelo usuário (São João da Barra/RJ/ENEL); entradas de engenharia
  usam `__PENDENTE__`. Textos de descrição no template são apenas orientação
  para preenchimento e não são valores de cálculo.

## Gate de pendências

O preflight percorrerá cada sub-spec solicitado e registrará
`pending_discipline_input` quando encontrar o marcador exato `__PENDENTE__`.
Isso não substitui os validadores dos calculadores: apenas impede que um
template incompleto chegue a eles. O marcador na geometria continua sendo um
erro comum (`invalid_common_geometry`), bloqueando a execução inteira.

## Fluxo

```text
JSON UTF-8
  -> load_project_spec
  -> normalize/preflight existente
  -> run_project
  -> project-run.json + entregáveis + coordenação
```

Não haverá consulta ao NotebookLM/web, preenchimento de campos, conversão para
YAML ou banco de dados nesta fase. A iteração continua usando
`iterate_project` sobre o manifesto anterior e permanece explicitamente
dirigida por alterações do usuário.

## Aceitação

1. Um JSON versionado preenchido passa pela mesma jornada trunk e grava hash do
   input.
2. O template SJB/ENEL termina `blocked`, lista geometria e disciplinas
   pendentes e não gera cálculo aprovado.
3. JSON inválido, schema desconhecido, versão não suportada e arquivo ausente
   produzem diagnóstico de entrada sem criar execução parcial.
4. A CLI devolve o estado do gate e mantém os artefatos do manifesto relativos.
5. Os testes existentes do Loop e a regressão afetada permanecem verdes.

## Gate de prontidão independente

O modo `--preflight-only` reutiliza a mesma entrada e normalização, mas grava
`project-readiness.json` e encerra antes de chamar qualquer runner. Isso
permite que o Loop 1.5 homologue o spec real antes que o Loop de projeto gere
disciplinas, IFC, desenhos ou coordenação.
