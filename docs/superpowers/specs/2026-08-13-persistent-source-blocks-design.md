# Bloqueio persistente de fontes — especificação

## Objetivo

O loop deve continuar trabalhando em outras tarefas quando uma tarefa exige uma
fonte ausente ou não auditável, sem voltar a consultar a mesma tarefa em toda
execução. A tarefa ficará estacionada somente enquanto o estado local das fontes
que a sustentam permanecer igual.

## Escopo

Esta fase altera apenas o scheduler e seu estado operacional. Ela não interpreta
normas, não faz upload/remover fontes no NotebookLM e não muda o critério de que
uma implementação exige citações auditáveis. O próximo módulo elétrico será uma
fase separada.

## Estado persistido

O arquivo `.loop-runtime/blocked-tasks.json` terá o formato:

```json
{
  "schema_version": 1,
  "tasks": {
    "<task-id>": {
      "task_id": "<task-id>",
      "title": "<title>",
      "topic": "<topic>",
      "reason": "missing_source",
      "detail": "<manual request>",
      "signature": "<sha256>",
      "source_paths": ["<relative path>"],
      "updated_at": "<UTC ISO-8601>"
    }
  }
}
```

O arquivo é estado local ignorado pelo Git. Registros inválidos não serão
ignorados silenciosamente: a leitura levanta `ValueError` para impedir uma
execução com seleção de tarefas desconhecida.

## Assinatura e elegibilidade

Para cada candidato, o supervisor calcula SHA-256 de um JSON determinístico que
contém:

1. a representação serializada do candidato;
2. para cada `source_path` declarado, caminho normalizado, existência, tipo,
   tamanho e hash SHA-256 do arquivo quando ele existir;
3. o estado hash do catálogo local e do mapa NotebookLM.

O caminho de fonte é resolvido dentro de `fontes/`; caminhos que escapem dessa
raiz são marcados como inválidos, nunca lidos fora dela. Candidatos sem
`source_paths` recebem a assinatura do próprio candidato mais catálogo/mapa;
assim, uma alteração documental local ou `--retry-blocked` é necessária para
reabrir uma investigação ampla cujo estado remoto não pode ser inferido na
descoberta.

Na descoberta, um registro cujo `signature` seja igual à assinatura atual exclui
o candidato. Assinatura diferente torna-o elegível. A opção `--retry-blocked`
ignora os registros persistidos apenas naquela invocação; se a pesquisa falhar
novamente, o registro é recriado com a assinatura atual.

## Ciclo de vida

- `manual_source_required`: grava ou atualiza o registro depois de estacionar o
  ledger.
- seleção de candidato elegível: remove o registro antigo daquela tarefa antes
  da pesquisa, evitando que uma falha posterior de implementação fique marcada
  como falha documental.
- `promoted`: remove o registro como limpeza defensiva.
- demais resultados: não criam bloqueio persistente.

O scheduler continua usando `excluded_task_ids` apenas para adiamento temporário
dentro da invocação; os dois mecanismos são independentes.

## Interface de configuração

`LoopConfig.retry_blocked: bool = False` será exposto pelo CLI como
`--retry-blocked`. Configuração inválida deve falhar antes de iniciar o loop.

## Testes e critérios de aceite

- bloqueio grava todos os campos e a assinatura;
- nova execução com assinatura igual termina em `no_candidate` sem chamar
  pesquisa;
- alterar um arquivo fonte declarado libera a tarefa;
- `--retry-blocked` libera a tarefa sem alteração;
- promoção remove o registro;
- tarefa concluída continua filtrada mesmo com retry;
- JSON inválido falha explicitamente;
- suíte completa de `tools/loops` e compilação dos módulos alterados passam.

## Fora do escopo

- consultar o NotebookLM durante a descoberta para verificar status remoto;
- reautenticar ou fazer upload automático de fontes;
- alterar a lista de fontes, o catálogo ou as normas;
- implementar o validador fotovoltaico.
