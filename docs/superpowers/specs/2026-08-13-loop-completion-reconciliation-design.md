# Fase 21a: reconciliação de conclusões do loop

## Objetivo

Impedir que o scheduler suprima uma candidata porque existe um registro antigo
de promoção cujo commit não pertence ao histórico que ainda representa a
promoção. O registro continuará preservado para diagnóstico, mas só bloqueará
uma candidata quando o commit promovido estiver alcançável a partir do `HEAD`
raiz ou da branch de promoção registrada.

## Contrato

`DevelopmentSupervisor._completed_task_ids()` continuará retornando um conjunto
de IDs de tarefas, mas deverá aplicar estas regras:

1. Ler `completed-tasks.json` como objeto com `tasks` do tipo dicionário.
2. Considerar concluído somente o registro cujo campo
   `promoted_commit` seja uma string não vazia e cujo commit seja ancestral do
   `HEAD` no repositório do projeto ou de `refs/heads/loop/<loop_id>`, quando o
   `loop_id` registrado for válido.
3. Ignorar, sem apagar, registros com commit ausente, inválido ou não ancestral.
4. Consultar Git com argumentos separados, sem shell, e tratar qualquer falha
   de `git merge-base --is-ancestor` como registro não concluído. A consulta da
   branch usará somente o `loop_id` do próprio registro; não haverá busca por
   qualquer branch que por acaso contenha o commit.
5. Manter o comportamento atual para uma tarefa promovida no branch corrente e
   para a opção `--retry-blocked`.

O filtro não inferirá conclusão pelo título, tópico, caminho de fonte ou pela
existência de arquivos. Isso evita esconder uma implementação que existe apenas
parcialmente ou em outro branch. A branch `loop/<loop_id>` é a exceção explícita
porque é o artefato criado pelo próprio fluxo de promoção.

## Diagnóstico e documentação

O arquivo de runtime não será reescrito durante a descoberta. A documentação do
loop explicará que registros não ancestrais são históricos e deixam a candidata
elegível novamente. A reconciliação de tarefas FV já concluídas nesta sessão será
feita no registro runtime depois da mudança, usando os commits reais que estão
no branch, sem inventar uma regra de descoberta.

## Testes

- registro com commit `HEAD` ou commit ancestral continua bloqueando a tarefa;
- promoção real na worktree/branch `loop/<loop_id>` bloqueia a mesma tarefa na
  descoberta seguinte, mesmo antes de um merge manual na raiz;
- registro com commit válido de uma linha paralela não bloqueia;
- registro com commit inválido ou ausente não bloqueia;
- `retry_blocked=True` não ultrapassa o filtro de conclusão válido;
- a suíte completa de `tools/loops/tests` permanece verde.

## Fora do escopo

- não remover registros históricos;
- não mudar a geração de IDs das candidatas;
- não alterar a pesquisa NotebookLM, a criação de worktrees ou a promoção Git;
- não marcar automaticamente tarefas pela presença de módulos ou testes.
