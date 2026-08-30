# Loop de Desenvolvimento — Especificação de Design

**Data:** 2026-08-12
**Status:** aprovado para planejamento da implementação
**Escopo:** primeira versão do loop de desenvolvimento do FreeCAD Automatic

## Objetivo

Criar um loop persistente e auditável que percorra, para uma tarefa técnica pequena,
as etapas de descobrir uma lacuna, consultar as fontes normativas do NotebookLM,
especificar a mudança, implementar, testar, revisar e registrar o resultado.

O loop deve permitir execução prolongada, mas nunca transformar repetição em autonomia
sem limites. Uma tarefa que não possui fonte pronta, dado de engenharia ou diagnóstico
suficiente deve ser estacionada com evidência, não resolvida por invenção.

## Contexto atual

- `fontes/catalogo.csv` é o catálogo local e
  `fontes/notebooklm-mapa.md` contém os IDs e as regras de consulta dos notebooks.
- O caminho de pesquisa já verificado é `nlm login --check`, `nlm list sources` e
  `nlm notebook query ... --source-ids ...`.
- O Claude Code possui `notebooklm-mcp` conectado nesta máquina; o Codex CLI não
  possui MCP configurado. O loop, portanto, não pode acoplar pesquisa e executor a
  um único agente.
- Os orquestradores de engenharia são stateless e recebem `spec`, especialmente
  `galpao_turnkey.rodar(spec)` e `rodar_projeto.rodar_tudo(...)`.
- A suíte possui testes rápidos e testes marcados `build`; o baseline precisa ser
  medido em cada execução porque o estado do ambiente pode variar.
- O framework segue a regra `Ask, Do Not Invent`: campos não confirmados são
  `A CONFIRMAR`/bloqueio, não defaults silenciosos.

## Não objetivos da primeira versão

- Não gerar projetos automaticamente sem um `spec` validado.
- Não substituir a revisão e a responsabilidade do engenheiro.
- Não fazer `git push`, merge, publicação externa ou exclusão remota de fontes.
- Não tentar reenviar indefinidamente uma fonte que exige upload manual.
- Não pesquisar a web como substituto silencioso das fontes do NotebookLM.
- Não modificar duas disciplinas independentes na mesma iteração.

## Arquitetura

O sistema será um supervisor Python orientado por estados, com adaptadores substituíveis:

```text
Ledger do loop
      │
      ├── Descoberta: backlog, revisões, testes e threads abertas
      ├── Pesquisa: NotebookLM → EvidenceBundle
      ├── Planejamento: fase pequena + testes positivos/negativos
      ├── Executor: Codex ou Claude em worktree isolado
      ├── Verificação: testes alvo, regressão e build quando aplicável
      ├── Revisor: diff + evidências + anti-invenção
      └── Registro: artefatos, sessão, commit local ou tarefa estacionada
```

O supervisor controla a ordem e as políticas; os agentes não escolhem por conta
própria a fonte normativa, o limite de tentativas ou o momento de concluir uma tarefa.

### Adaptadores

`ResearchAdapter` recebe disciplina, pergunta e candidatos de fonte; retorna um
`EvidenceBundle` com notebook ID, source IDs, títulos, status, pergunta, resposta,
conversation ID, citações e hashes locais quando houver correspondência no catálogo.

A primeira implementação usará o CLI `nlm`, por ser o caminho já validado e fácil de
registrar. Um adaptador MCP poderá usar o `notebooklm-mcp` do Claude sem alterar o
contrato. Se nenhum source ID com status `2` atender à pergunta, o adaptador cria uma
pendência manual com notebook, arquivo, status e ação esperada.

`AgentAdapter` recebe um pacote de tarefa, evidências e plano; trabalha somente no
worktree da iteração e retorna resumo, arquivos alterados, comandos e sessão do agente.
As implementações iniciais podem ser `codex exec` e `claude -p`.

`TestAdapter` executa comandos permitidos e retorna exit code, duração, stdout/stderr
resumidos, testes passantes, falhos, ignorados e artefatos. O baseline é coletado antes
da alteração; a validação exige que a mudança não introduza regressões além das falhas
já conhecidas.

`ReviewAdapter` recebe o diff, o plano, o `EvidenceBundle` e os resultados dos testes.
Ele deve verificar escopo, cobertura, citações, uso de parâmetros normativos, ausência
de defaults inventados e coerência com a API existente. O implementador não deve ser
o único revisor.

## Máquina de estados

Cada iteração executa no máximo uma tarefa e percorre estes estados:

1. `preflight` — verifica worktree, versão, dependências, autenticação, estado do
   NotebookLM e baseline de testes.
2. `discover` — reúne candidatos de `wiki/06-open-threads.md`, `REVISAO-*.md`, testes
   falhos, gaps documentados e módulos sem cobertura; escolhe um candidato pequeno.
3. `research` — resolve o notebook pela disciplina, filtra fontes prontas, consulta
   apenas IDs registrados e salva o `EvidenceBundle`.
4. `plan` — cria o plano de fase com escopo, entry/exit, must-exist, must-not-exist e
   testes positivos/negativos.
5. `red` — adiciona ou confirma o teste que reproduz a lacuna; o teste deve falhar
   pela razão esperada antes da implementação.
6. `implement` — o agente modifica código e testes no worktree isolado, usando somente
   a evidência e o escopo da tarefa.
7. `verify` — roda teste alvo, regressão não-build e, para tarefas geométricas, a suíte
   build conforme a política. Também executa `git diff --check`.
8. `review` — revisor independente examina diff, evidência e resultados.
9. `record` — grava artefatos, sessão, decisão e métricas; cria commit local se todos
   os gates passarem.
10. `promote` ou `park` — `promote` deixa o commit na branch da tarefa para revisão
    humana; `park` retorna o motivo e a próxima ação sem fingir conclusão.

Uma chamada inválida à API de transição deve falhar sem modificar o estado persistido.
Erros operacionais do loop devem deixar o ledger em um estado recuperável, com uma
falha classificada contendo motivo, comando e referências aos artefatos. O supervisor
usará essa informação para estacionar e retomar a partir da última fase persistida.

## Estado persistente

O ledger deve conter, no mínimo:

```json
{
  "schema_version": 1,
  "loop_id": "2026-08-12T0000Z",
  "mode": "dry-run|supervised|autonomous",
  "iteration": 1,
  "state": "research",
  "task": {
    "id": "T-0001",
    "title": "descrição curta",
    "discipline": "eletrica",
    "origin": "arquivo e linha",
    "priority": 0
  },
  "worktree": {"path": "...", "branch": "loop/T-0001", "base_commit": "..."},
  "evidence": [],
  "attempts": {"research": 0, "red": 0, "implement": 0, "verify": 0, "review": 0},
  "tests": {"baseline": {}, "targeted": {}, "regression": {}, "build": {}},
  "artifacts": [],
  "outcome": null,
  "failure": null,
  "updated_at": "..."
}
```

Os componentes versionados ficarão em `tools/loops/` (código, esquema e prompts). O
estado operacional ficará em `.loop-runtime/`, ignorado pelo Git, com o ledger em
`.loop-runtime/ledger.json`, os artefatos em `.loop-runtime/runs/<loop_id>/` e os
worktrees descartáveis em `.loop-runtime/worktrees/<loop_id>/`. Cada rodada também
produzirá um resumo legível em `sessions/` e, quando necessário, a fila manual em
`.loop-runtime/runs/<loop_id>/manual-source-requests.md`.

## Descoberta e seleção de tarefas

O descobridor deve dar prioridade, nesta ordem:

1. regressão ou falha reproduzível que pode comprometer segurança;
2. parecer ou thread aberta com impacto de contra-segurança;
3. gap documentado sem teste;
4. cobertura de uma integração existente;
5. nova capacidade solicitada explicitamente.

O candidato só entra na iteração se puder ser descrito por uma única fase curta, tiver
um ponto de teste localizável e não exigir decisão de engenharia ausente. Candidatos
independentes são colocados na fila, não fundidos em uma tarefa gigante.

## Regras de pesquisa normativa

- O mapa local escolhe o notebook; o catálogo escolhe o nome/edição/hash da fonte.
- Apenas fontes remotas com status `2` podem sustentar uma decisão de implementação.
- Cada consulta deve declarar a pergunta técnica, o contexto do módulo e os source IDs.
- A resposta não é suficiente sem registrar as citações retornadas.
- Conflito entre edições, ausência de edição completa ou arquivo não carregado estaciona
  a tarefa e gera solicitação manual.
- O agente deve distinguir norma principal, suplemento, referência histórica e fonte
  auxiliar; uma emenda não substitui silenciosamente a norma-base.
- O texto de uma fonte não deve ser copiado integralmente para o repositório; registram-se
  metadados, trechos curtos necessários, citações e caminho local.

## Testes e gates

Cada tarefa deve provar o caminho completo: teste vermelho antes, teste verde depois,
regressão e revisão. O loop não exige que o baseline global seja perfeito para começar,
mas exige registrar as falhas preexistentes e não aumentar seu conjunto sem justificativa.

- Módulo puro: teste unitário/selftest + integração do orquestrador afetado.
- Vertical: teste `rodar(spec)` + BIM neutro/IFC quando aplicável + veredito/gates.
- Saída 2D: SVG/XML, contagens e configuração + build TechDraw quando aplicável.
- Geometria 3D: testes puros de camada + teste marcado `build` em janela própria.
- Turnkey: trunk de `rodar_tudo`/`galpao_turnkey`, federação, clash e caderno quando
  a mudança alcançá-los.

O build periódico continua sendo uma guarda separada; uma tarefa que o exige não pode
ser declarada plenamente verificada enquanto o build correspondente não for executado.

## Falhas, limites e segurança

- Falha de fonte: registrar em
  `.loop-runtime/runs/<loop_id>/manual-source-requests.md`, estacionar somente tarefas
  que dependem dela e continuar com outra tarefa independente.
- Falha de teste: permitir no máximo duas tentativas de diagnóstico na mesma iteração;
  a terceira ocorrência sem progresso estaciona a tarefa.
- Timeout: registrar comando, duração e processo; não matar processos FreeCAD do usuário
  fora do worktree/job iniciado pelo loop.
- Worktree principal sujo: criar o worktree da iteração a partir do `HEAD` atual e nunca
  editar a raiz; se o `HEAD` mudar durante a rodada, interromper antes de promover.
- Evidência conflitante ou parâmetro `A CONFIRMAR`: estacionar e pedir decisão humana.
- Nunca executar `git push`, merge, exclusão remota ou remoção de arquivos fora do
  worktree como ação automática da primeira versão.
- Cada rodada possui limite de tempo, limite de tentativas e limite de alterações.

## Modos de execução

- `dry-run`: descobre, pesquisa e monta o plano; não edita código.
- `supervised`: pode criar teste, implementar, testar e fazer commit local; exige revisão
  humana antes de merge/push. Este é o modo inicial.
- `autonomous`: pode encadear tarefas independentes dentro dos limites configurados,
  mas mantém todas as proibições de rede, merge, push e exclusão.

## Critério de sucesso da primeira fase

A Fase 1 está concluída quando uma execução reproduzível em modo `dry-run` e uma em modo
`supervised` conseguem: selecionar uma tarefa, encontrar o notebook, produzir evidência
com source IDs, criar/confirmar o teste, executar o agente em worktree, rodar os gates,
gerar revisão e salvar o ledger/resumo. Uma falha deliberadamente induzida também deve
ser estacionada com motivo e retomável.

## Próxima fase

Implementar o contrato do ledger, os adaptadores `nlm`/testes, o supervisor em modo
`dry-run` e os prompts de descoberta, implementação e revisão. Só depois habilitar edição
supervisionada no primeiro ciclo real.
