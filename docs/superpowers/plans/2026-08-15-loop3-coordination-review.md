# Loop 3 - Revisão, resolução e emissão final: plano de implementação

> **Para agentes de execução:** seguir o ciclo TDD vermelho → verde → integração → verificação em cada tarefa. Manter a alteração isolada do Loop 2 e executar a jornada dourada após cada marco verde.

**Objetivo:** transformar a coordenação do Loop 2 em uma revisão auditável que classifica pendências `CLH-*`, aplica somente decisões aprovadas pelo responsável técnico, reexecuta o projeto sem sobrescrever o pai, reconcilia conflitos por GUID estável e só marca a revisão como aprovada quando os entregáveis solicitados e os hashes estiverem íntegros.

**Arquitetura:** adicionar um módulo puro para validação/classificação/reconciliação; expor `review_project()` no orquestrador existente; persistir plano e relatório como artefatos do filho; adicionar uma rota CLI específica; anexar a jornada dourada e testes de limites ao test tree.

**Stack:** Python 3, pytest, JSON versionado, `project_loop.iterate_project()`, adaptador turnkey já existente e verificação SHA-256 já existente.

## Fase 6: Loop 3 de revisão de coordenação

### Escopo

- Ler `coordination/pendencias.json` do manifesto pai e indexar as pendências por `id` e `guid`.
- Classificar automaticamente somente o que já é evidência auditada: `esperado=true` vira `expected`; o restante começa como `inconclusive`.
- Validar plano JSON com `schema`, `schema_version`, `parent_run_id`, `project_id`, IDs existentes e decisões únicas.
- Aplicar atualizações apenas em decisões `approved` que contenham `approved_by` e `approved_at`.
- Reutilizar `iterate_project()` para criar a rodada filha e herdar a política do pai.
- Persistir o plano, o relatório de reconciliação e os hashes no filho.
- Reconciliar por GUID em estados `accepted_expected`, `resolved`, `reopened`, `inconclusive_open` e `new_open`.
- Expor a operação na CLI e registrar o vínculo pai/filho, disciplinas afetadas e disciplinas efetivamente reexecutadas.

### Condições de entrada

- O pai contém `project-run.json`, artefatos declarados e hashes verificáveis.
- O pai contém `coordination/pendencias.json` gerado pelo Loop 2.
- O projeto continua sendo executável conforme os gates nativos já registrados no manifesto.

### Condições de saída

- Toda execução de revisão produz um manifesto filho não destrutivo, ou falha antes de criar saída parcial quando o plano é inválido.
- O plano e o relatório de revisão são artefatos com SHA-256 no filho.
- `verify_project_run(filho)` retorna `ok=true` para uma execução válida.
- `coordination.review_status` é `approved` somente sem conflito real persistente, sem estado inconclusivo/novo/reaberto, com entregáveis pedidos gerados e gates nativos preservados.
- Uma revisão não aprovada permanece `needs_review` ou `failed` e explica as pendências no relatório.

### Deve existir

- Contrato JSON versionado e validação sem efeitos colaterais.
- Atualização rejeitada quando pendente, rejeitada, textual ou sem responsável/data.
- Caminho de spec ausente, issue desconhecida, ID duplicado, pai divergente e pai adulterado rejeitados.
- Reconciliação determinística por `guid`.
- Regra explícita para disciplinas afetadas e reexecutadas.
- CLI com `--review-from` e `--resolution-plan`.
- Teste de jornada ponta a ponta com plano, filho, artefatos e relatório final.

### Não deve existir

- Alteração no `project-run.json` ou nos artefatos do pai.
- Aprovação automática de conflito não esperado como `real`.
- Fechamento por `note`, `status` textual ou `approval_status` sem alteração aplicável.
- Sobrescrita silenciosa de atualizações conflitantes para o mesmo caminho.
- Aprovação de coordenação mascarando disciplina bloqueada/reprovada, preflight bloqueado ou entregável ausente.
- Consulta normativa nova ou solução automática de engenharia dentro deste loop.

### Teste positivo

1. Um plano aprovado com update existente cria a iteração filha, preserva o pai, reexecuta o escopo, registra a decisão, grava o relatório e mantém hashes válidos.
2. Um conflito esperado persistente vira `accepted_expected` sem exigir alteração.
3. Um conflito real que desaparece vira `resolved`; um que permanece vira `reopened`.
4. Uma pendência inconclusiva permanece `inconclusive_open`; uma pendência surgida somente no filho vira `new_open`.
5. A jornada dourada lê a API/CLI do Loop 3 e verifica os artefatos finais.

### Teste negativo

1. Plano sem `schema`, versão incompatível, pai divergente, projeto divergente, ID inexistente ou ID repetido falha antes de criar o filho.
2. Update em decisão `pending`/`rejected` ou decisão aprovada sem responsável/data não é aplicado.
3. Dois valores diferentes para o mesmo caminho aprovado são rejeitados.
4. Pai adulterado não é usado para iniciar a revisão.
5. Entregável solicitado ausente, hash inválido, disciplina falha ou conflito real persiste impede `review_status=approved`.

## Tarefas de implementação

### Tarefa 1 — Contrato puro e reconciliação (TDD)

**Arquivos:** criar `framework/galpao_fw/coordination_review.py`; criar `framework/galpao_fw/tests/branches/project_loop/test_project_loop_review_contract.py`.

**Interface:** implementar `load_resolution_plan()`, `validate_resolution_plan()`, `classify_pendencias()`, `collect_approved_updates()`, `derive_affected_disciplines()`, `reconcile_pendencias()` e `build_review_report()`.

**Passos:**

1. Escrever testes de classificação, validação de IDs, aprovação, caminhos, conflitos de update e reconciliação por GUID.
2. Rodar somente o novo arquivo e confirmar falhas vermelhas claras por ausência do módulo/API.
3. Implementar o mínimo sem importar FreeCAD nem executar adaptador.
4. Rodar o novo arquivo e depois toda a suíte de branches `project_loop`.

**Critério:** funções determinísticas, entradas JSON-safe, sem mutar pendências/plano recebidos e com mensagens de erro úteis.

### Tarefa 2 — API de revisão no orquestrador

**Arquivos:** alterar `framework/galpao_fw/project_loop.py`; criar `framework/galpao_fw/tests/branches/project_loop/test_project_loop_review_execution.py`.

**Interface:** adicionar `review_project(previous_run, resolution_plan, out_dir=None, options=None)` e exportá-la em `__all__`.

**Passos:**

1. Escrever teste de jornada com um pai real gerado pelo adaptador turnkey e um plano aprovado.
2. Confirmar vermelho para a API ausente.
3. Verificar pai/hashes antes de validar e executar o plano.
4. Ler pendências do pai, validar o plano, chamar `iterate_project()` somente com updates aprovados e preservar a herança de opções.
5. Anexar `coordination/resolution-plan.json` e `coordination/review-report.json`, atualizar o manifesto e recalcular a verificação/hash dos artefatos.
6. Registrar `affected_disciplines`, `rerun_disciplines`, `applied_updates` e o vínculo pai/filho.
7. Rodar testes de execução, branches existentes e jornada dourada.

**Critério:** nenhuma saída criada para plano inválido; pai intacto; filho verificável; decisões textuais não mudam spec nem encerram clash.

### Tarefa 3 — Regra de emissão e proteção dos gates

**Arquivos:** alterar `framework/galpao_fw/coordination_review.py` e `framework/galpao_fw/project_loop.py`; ampliar `test_project_loop_review_execution.py`.

**Passos:**

1. Escrever testes para `approved` e `needs_review` com todas as combinações de conflito/entregável/hash.
2. Implementar a decisão final sem alterar `status`, `atende`, preflight ou estados nativos de disciplina quando houver bloqueio.
3. Exigir os entregáveis que estavam pedidos no pai e verificar o manifesto filho com `verify_project_run()`.
4. Rodar a suíte completa após o marco verde.

**Critério:** `coordination.review_status=approved` é impossível quando há `real` persistente, inconclusivo, novo, reaberto, artefato ausente, hash inválido ou gate nativo não aprovado.

### Tarefa 4 — CLI e jornada dourada

**Arquivos:** alterar `framework/galpao_fw/project_loop_cli.py`; alterar `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`; criar/alterar testes de CLI em `framework/galpao_fw/tests/branches/project_loop/test_project_loop_spec_file_input.py`.

**Interface:** aceitar `--review-from`, `--resolution-plan`, `--out-dir` e as opções de geração herdadas; rejeitar combinações ambíguas com `--iterate-from`, `--iteration-plan`, `--update` e `--resolution`.

**Passos:**

1. Escrever teste CLI que gera o pai, grava plano e executa a revisão pelo caminho de arquivo.
2. Confirmar vermelho.
3. Implementar parsing, carga segura, códigos de saída e resumo JSON.
4. Integrar a etapa de revisão à jornada dourada sem mocks do orquestrador.
5. Rodar a jornada e a suíte completa.

**Critério:** CLI retorna código 0 apenas para resultado operacional válido (`passed` ou `needs_review` conforme a política existente), 2 para bloqueio, 3 para falha e 4 para entrada inválida; imprime manifesto filho.

### Tarefa 5 — Documentação, smoke e auditoria

**Arquivos:** alterar `COMO-RODAR.md` se existente ou documentar em `README.md`; atualizar `docs/superpowers/specs/2026-08-15-loop3-coordination-review-design.md`; criar/atualizar `sessions/2026-08-14.md`.

**Passos:**

1. Documentar formato do plano, comando CLI e significado de cada estado.
2. Executar smoke sintético com conflito corrigido e verificar pai, filho, plano, relatório, entregáveis e hashes.
3. Executar `compileall`, suíte completa e `git diff --check`.
4. Registrar limitações atuais: o spec real SJB/ENEL continua bloqueado por pendências geométricas e não será falsamente emitido.

**Critério:** evidência reproduzível dos comandos e nenhum claim de conclusão sem saída verificável.

## Integração no test tree

- **Tronco:** `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py` passa por execução inicial, leitura de coordenação, criação de plano de revisão, geração do filho e validação de hashes.
- **Branch de contrato:** cobre funções puras e negativas de segurança.
- **Branch de execução:** cobre pai/filho, atualizações aprovadas e política de emissão.
- **Branch de CLI:** cobre entrada por arquivo e códigos de saída.
- **Folhas:** pai adulterado, issue desconhecida, update não aprovado, conflito persistente e entregável ausente.

## Próximo marco após esta fase

Com o Loop 3 estabilizado, iniciar o Loop 4 de homologação do projeto real: resolver as pendências de geometria/readiness do galpão de São João da Barra, registrar premissas técnicas e somente então executar a cadeia completa com fontes ENEL e notebooks por disciplina.

## Verificação do plano

- Todos os critérios do design estão mapeados para tarefas, testes positivos/negativos ou documentação.
- Não há caminhos de implementação indefinidos, placeholders ou tarefas vagas.
- As interfaces propostas são compatíveis com `iterate_project()`, `verify_project_run()` e o formato real de `pendencias.json`.
- A implementação não exige FreeCAD real para o contrato puro, mas a jornada usa o adaptador turnkey real e verifica artefatos persistidos.
