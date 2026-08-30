# Plano de implementação: Development Loop

> **Para agentes de execução:** use a skill subagent-driven-development (recomendada) ou executing-plans para executar este plano tarefa por tarefa. Os passos usam checkboxes para acompanhar o progresso.

**Objetivo:** Construir um loop de desenvolvimento supervisionado que descubra lacunas do framework, consulte somente evidências rastreáveis do NotebookLM, transforme uma lacuna em uma tarefa pequena, implemente em worktree isolada, execute testes, faça revisão independente e registre o resultado para a próxima sessão.

**Arquitetura:** Um supervisor Python em tools/loops/ coordenará uma máquina de estados persistida. Adaptadores separados encapsularão NotebookLM, agentes de código, execução de testes, revisão e worktrees Git. O loop escreverá apenas artefatos em .loop-runtime/ e na worktree temporária; a promoção para o branch do usuário será explícita.

**Stack:** Python 3.12 da biblioteca padrão; pytest e o executor já usado pelo projeto; nlm CLI; codex exec ou claude -p; Git worktree; PowerShell somente para a suíte FreeCAD.

## Restrições globais

- A primeira execução será dry-run e a operação padrão será supervised.
- A configuração local será a fonte de quais notebooks, fontes locais e comandos estão disponíveis.
- O adaptador NotebookLM aceitará somente fontes com status 2, registrará notebook, IDs, pergunta, resposta, citações e timestamp, e nunca tratará memória do agente como evidência.
- Fonte ausente, conflito entre fontes ou resposta sem citação válida produzirá um pedido manual e estacionará a tarefa.
- Cada iteração tratará exatamente uma tarefa candidata.
- O branch raiz não será editado pelo agente; a implementação ocorrerá em .loop-runtime/worktrees/<loop_id>.
- O loop não fará push, merge automático, deleção ampla, alteração de fontes remotas nem repetição infinita.
- Toda mudança de fase será persistida no ledger; falhas serão classificadas com motivo, comando e artefatos.
- A comparação de testes registrará baseline e delta, sem aceitar como sucesso uma suíte que apenas repete uma falha conhecida.
- Nenhuma dependência nova será adicionada ao runtime do framework.
- Testes build que exigem FreeCAD permanecerão em uma etapa separada e com timeout próprio.
- Logs podem conter saídas de ferramentas, mas não podem registrar tokens, cookies ou credenciais.

## Mapa de arquivos

Criar:

- tools/loops/__init__.py
- tools/loops/__main__.py
- tools/loops/models.py
- tools/loops/config.py
- tools/loops/ledger.py
- tools/loops/discovery.py
- tools/loops/research_nlm.py
- tools/loops/commands.py
- tools/loops/tests_runner.py
- tools/loops/agents.py
- tools/loops/reviewer.py
- tools/loops/worktrees.py
- tools/loops/supervisor.py
- tools/loops/prompts/implementation.md
- tools/loops/prompts/review.md
- tools/loops/schema/development-loop.schema.json
- tools/loops/tests/test_ledger.py
- tools/loops/tests/test_config_worktrees.py
- tools/loops/tests/test_research_nlm.py
- tools/loops/tests/test_discovery.py
- tools/loops/tests/test_commands_and_tests.py
- tools/loops/tests/test_agents_and_reviewer.py
- tools/loops/tests/test_supervisor.py
- tools/loops/tests/test_cli.py
- tools/loops/tests/test_integration.py

Modificar:

- .gitignore, adicionando .loop-runtime/
- tools/README.md, documentando configuração, modos, comandos e recuperação manual

Artefatos gerados, fora do código rastreado:

- .loop-runtime/ledger.json
- .loop-runtime/runs/<loop_id>/task.json
- .loop-runtime/runs/<loop_id>/evidence.json
- .loop-runtime/runs/<loop_id>/plan.md
- .loop-runtime/runs/<loop_id>/commands/
- .loop-runtime/runs/<loop_id>/tests/
- .loop-runtime/runs/<loop_id>/review.md
- .loop-runtime/runs/<loop_id>/outcome.json
- .loop-runtime/runs/<loop_id>/session-summary.md
- .loop-runtime/runs/<loop_id>/manual-source-requests.md
- .loop-runtime/worktrees/<loop_id>/

## Contratos centrais

Os contratos devem ser definidos antes dos adaptadores concretos para que testes unitários não dependam de NotebookLM, Codex, Claude ou FreeCAD.

~~~python
class LoopPhase(StrEnum):
    PREFLIGHT = "preflight"
    DISCOVER = "discover"
    RESEARCH = "research"
    PLAN = "plan"
    RED = "red"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    REVIEW = "review"
    RECORD = "record"
    PROMOTE = "promote"
    PARK = "park"


@dataclass(frozen=True)
class TaskCandidate:
    id: str
    title: str
    discipline: str
    origin: str
    priority: int
    evidence_paths: tuple[str, ...]
    suggested_tests: tuple[str, ...]


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    title: str
    status: int
    notebook_id: str
    local_path: str | None = None
    local_hash: str | None = None


@dataclass(frozen=True)
class Citation:
    number: str
    source_id: str
    cited_text: str


@dataclass(frozen=True)
class EvidenceBundle:
    notebook_id: str
    source_ids: tuple[str, ...]
    sources: tuple[SourceRecord, ...]
    question: str
    answer: str
    conversation_id: str | None
    citations: tuple[Citation, ...]
    retrieved_at: str
    manual_request: str | None = None


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    cwd: str
    returncode: int
    duration_seconds: float
    stdout: str
    stderr: str


@dataclass(frozen=True)
class FailureRecord:
    reason: str
    command: tuple[str, ...] | None
    artifacts: tuple[str, ...]
    detail: str | None = None


@dataclass
class LoopState:
    schema_version: int
    loop_id: str
    mode: str
    iteration: int
    phase: LoopPhase
    task: TaskCandidate | None
    base_commit: str
    worktree: str | None
    evidence: EvidenceBundle | None
    attempts: dict[str, int]
    artifacts: dict[str, str]
    outcome: str | None
    last_error: str | None
    failure: FailureRecord | None


@dataclass(frozen=True)
class LoopConfig:
    project_root: str
    runtime_dir: str
    mode: str
    max_iterations: int
    max_attempts_per_phase: int
    command_timeout_seconds: int
    build_timeout_seconds: int
    executor: str
~~~

A transição permitida será explícita:

~~~python
VALID_TRANSITIONS = {
    "preflight": {"discover", "park"},
    "discover": {"research", "park"},
    "research": {"plan", "park"},
    "plan": {"red", "park"},
    "red": {"implement", "park"},
    "implement": {"verify", "park"},
    "verify": {"review", "park"},
    "review": {"record", "park"},
    "record": {"promote", "park"},
    "promote": set(),
    "park": {"discover", "research"},
}
~~~

## Task 1: contrato de estado, schema e ledger

- [x] Concluir a tarefa 1 e validar o ledger isoladamente.

Arquivos:

- Criar tools/loops/models.py.
- Criar tools/loops/ledger.py.
- Criar tools/loops/schema/development-loop.schema.json.
- Criar tools/loops/tests/test_ledger.py.

Implementação:

1. Definir os dataclasses e a enumeração acima, com serialização explícita para JSON.
2. Validar o conjunto de fases e as transições antes de persistir.
3. Implementar Ledger.load, Ledger.save e Ledger.transition.
4. Implementar Ledger.record_failure(reason, command, artifacts, detail) para registrar falhas operacionais classificadas sem avançar a fase; uma chamada inválida de transition continua sem mutar o ledger.
5. Escrever o JSON primeiro em arquivo temporário exclusivo no mesmo diretório e substituir o ledger com os.replace; só atualizar self.state após a substituição bem-sucedida.
6. Rejeitar mudança de fase quando a fase atual não for a esperada.
7. Validar o documento contra o schema na entrada e na saída usando apenas a biblioteca padrão; o teste deverá verificar tipos, limites e estruturas aninhadas do contrato, sem introduzir um validador externo.

Testes que devem falhar antes da implementação:

- test_state_round_trip_preserves_enum_and_empty_collections
- test_ledger_transition_requires_expected_phase
- test_ledger_save_is_valid_json_after_replacement
- test_invalid_transition_is_reported_without_mutating_state
- test_invalid_iteration_is_rejected
- test_record_failure_persists_reason_command_and_artifacts

Verificação:

~~~powershell
python -m pytest tools/loops/tests/test_ledger.py -q
~~~

Resultado esperado após a tarefa: todos os testes da tarefa passam e uma tentativa inválida não altera o arquivo persistido.

Commit da tarefa: feat: add development loop state contract

## Task 2: configuração e worktrees isoladas

- [x] Concluir a tarefa 2 e validar worktrees isoladas.

Arquivos:

- Criar tools/loops/config.py.
- Criar tools/loops/worktrees.py.
- Criar tools/loops/tests/test_config_worktrees.py.
- Modificar .gitignore adicionando .loop-runtime/.

Interfaces:

- load_config(path, project_root) -> LoopConfig
- WorktreeManager.create(loop_id, base_commit) -> str
- WorktreeManager.assert_base_unchanged(base_commit) -> None
- WorktreeManager.remove(loop_id) -> None

Implementação:

1. Usar valores seguros para modo supervised, executor codex, uma iteração, três tentativas por fase, timeout de comando de 900 segundos e timeout build de 1800 segundos.
2. Resolver todos os caminhos a partir de project_root.
3. Criar a worktree com:
   git worktree add -b loop/<loop_id> <runtime>/worktrees/<loop_id> <base_commit>
4. Recusar loop_id com separador de caminho ou nome que não seja seguro.
5. Verificar que o HEAD do project_root continua sendo base_commit antes da promoção.
6. Remover somente uma worktree registrada dentro de runtime_dir/worktrees, depois de confirmar o caminho absoluto.
7. Adicionar .loop-runtime/ a .gitignore sem alterar as regras existentes de sessions/ ou fontes/.

Testes que devem falhar antes da implementação:

- test_load_config_uses_project_root_for_relative_paths
- test_worktree_creation_is_based_on_exact_commit
- test_root_head_change_raises_external_change
- test_remove_rejects_path_outside_runtime
- test_invalid_loop_id_is_rejected

O teste criará um repositório Git temporário, fará um commit inicial, criará a worktree e confirmará que o arquivo do repositório raiz não foi modificado.

Verificação:

~~~powershell
python -m pytest tools/loops/tests/test_config_worktrees.py -q
~~~

Commit da tarefa: feat: isolate development loop worktrees

## Task 3: adaptador NotebookLM e fila de fontes manuais

- [x] Concluir a tarefa 3 e validar consulta, citações e fila manual.

Arquivos:

- Criar tools/loops/research_nlm.py.
- Criar tools/loops/tests/test_research_nlm.py.

Interfaces:

- NotebookMap.load(path) -> NotebookMap
- CatalogIndex.load(path) -> CatalogIndex
- NlmCliAdapter.list_ready_sources(notebook_id) -> tuple[SourceRecord, ...]
- NlmCliAdapter.query(notebook_id, question, source_ids) -> EvidenceBundle
- ManualSourceRequest.write(path) -> None

Implementação:

1. Ler fontes locais e a divisão por notebook do mapa existente em fontes/notebooklm-mapa.md e no catálogo versionado da pasta fontes.
2. Aceitar a saída JSON do nlm tanto como lista quanto como objeto contendo uma lista de fontes.
3. Filtrar exclusivamente fontes com status numérico 2.
4. Executar a consulta neste formato:
   nlm notebook query <notebook_id> <question> --source-ids id1,id2 --timeout 120 --json
5. Não incluir uma fonte não pronta na consulta; se a fonte necessária não estiver pronta, criar manual-source-requests.md com notebook, título, caminho local, motivo e comando manual sugerido.
6. Validar que cada citação retornada aponta para um source_id solicitado.
7. Preservar a resposta original como artefato sem armazenar credenciais.
8. Usar um runner injetável para que os testes não chamem a rede nem o NotebookLM real.

Testes que devem falhar antes da implementação:

- test_list_ready_sources_filters_status_two
- test_query_passes_only_requested_source_ids
- test_query_parses_list_and_object_json_shapes
- test_query_rejects_citation_from_unrequested_source
- test_missing_source_writes_manual_request

Fixtures do teste:

~~~python
def ready_evidence():
    return EvidenceBundle(
        notebook_id="nb-1",
        source_ids=("src-ok",),
        sources=(
            SourceRecord(
                source_id="src-ok",
                title="Norma teste",
                status=2,
                notebook_id="nb-1",
            ),
        ),
        question="Qual requisito deve ser verificado?",
        answer="A resposta de teste exige verificação.",
        conversation_id="conv-1",
        citations=(
            Citation("1", "src-ok", "trecho curto de teste"),
        ),
        retrieved_at="2026-08-12T00:00:00Z",
    )
~~~

Verificações:

~~~powershell
python -m pytest tools/loops/tests/test_research_nlm.py -q
nlm login --check
~~~

A segunda verificação é um smoke manual da autenticação salva, não deve ser executada nos testes unitários.

Commit da tarefa: feat: add NotebookLM research adapter

## Task 4: descoberta e priorização determinísticas

- [x] Concluir a tarefa 4 e validar candidatos determinísticos.

Arquivos:

- Criar tools/loops/discovery.py.
- Criar tools/loops/tests/test_discovery.py.

Interfaces:

- discover_candidates(project_root) -> tuple[TaskCandidate, ...]
- rank_candidates(candidates) -> tuple[TaskCandidate, ...]

Implementação:

1. Ler threads abertas da wiki, pendências de fontes, documentação REVISAO e nomes de testes que indiquem robustez ou integração.
2. Transformar cada item em uma tarefa pequena e verificável, com disciplina, origem e testes sugeridos.
3. Ignorar títulos que contenham RESOLVIDO, MERGED, FECHADO ou HOMOLOGADO quando não houver marcador de pendência no mesmo item.
4. Gerar ID estável com sha1(origin + newline + title)[:12].
5. Dar prioridade maior a segurança estrutural, validações de entrada, regressões e lacunas explicitamente abertas; priorizar depois elétrica, hidráulica, esgoto, estrutura, BIM/IFC, 2D e documentação.
6. Ordenar de forma determinística por prioridade, disciplina, origem e ID.
7. Não inventar tarefa a partir de uma norma sem uma lacuna observável no código, testes ou documentação.
8. Delimitar cada item por heading, parágrafo, bullet, checkbox ou linha de tabela; não concatenar uma tabela ou seção histórica inteira em uma única candidata.
9. Ler como pendência de fonte apenas arquivos explícitos de pendências/recomendações; não interpretar prosa normativa bruta em TXT como tarefa.
10. Reconhecer checkboxes abertos e marcadores atuais de pendência, ignorando itens com RESOLVIDO, MERGED, FECHADO, HOMOLOGADO, APROVADO ou equivalente quando não houver uma pendência atual no mesmo item.

Testes que devem falhar antes da implementação:

- test_discovery_finds_unverified_fuzz_item
- test_discovery_ignores_resolved_item
- test_rank_prioritizes_structural_safety_over_documentation
- test_candidate_id_is_stable
- test_same_repository_state_has_same_order
- test_resolved_status_markers_are_ignored
- test_open_source_checkbox_is_discovered
- test_normative_prose_is_not_discovered
- test_candidate_id_matches_required_formula

Verificação:

~~~powershell
python -m pytest tools/loops/tests/test_discovery.py -q
~~~

Commit da tarefa: feat: add deterministic loop discovery

## Task 5: execução de comandos e políticas de teste

- [x] Concluir a tarefa 5 e validar gates, timeouts e delta de testes.

Arquivos:

- Criar tools/loops/commands.py.
- Criar tools/loops/tests_runner.py.
- Criar tools/loops/tests/test_commands_and_tests.py.

Interfaces:

- CommandRunner.run(argv, cwd, timeout_seconds) -> CommandResult
- TestRunner.baseline() -> TestSnapshot
- TestRunner.targeted(test_paths) -> TestSnapshot
- TestRunner.regression() -> TestSnapshot
- TestRunner.build() -> TestSnapshot
- compare_snapshots(baseline, current) -> TestDelta

Comandos padrão:

~~~python
TARGETED = [
    sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q"
]
REGRESSION = [
    sys.executable, "tools/run_tests.py"
]
BUILD = [
    "powershell", "-ExecutionPolicy", "Bypass", "-File",
    "tools/run_build_suite.ps1"
]
~~~

Implementação:

1. Executar com subprocess.Popen e communicate(timeout=).
2. Em timeout, terminar o processo, registrar returncode -1, stdout, stderr e a marcação de timeout.
3. Executar targeted e regression com cwd framework/galpao_fw; executar build a partir da raiz do projeto.
4. Extrair um resumo estável de passed, failed, skipped, errors, duration e timed_out; preservar a saída completa em arquivo.
5. Calcular delta em relação ao baseline, distinguindo falha preexistente de nova falha.
6. Impedir promoção se houver nova falha, erro, timeout ou teste alvo que não passou.
7. Permitir que build seja obrigatório somente quando a tarefa for marcada como build.

Testes que devem falhar antes da implementação:

- test_command_runner_captures_stdout_and_stderr
- test_command_runner_marks_timeout
- test_snapshot_parser_handles_pytest_summary
- test_delta_distinguishes_new_failure_from_baseline_failure
- test_build_policy_is_separate_from_unit_regression
- test_targeted_failure_blocks_promotion

Verificação:

~~~powershell
python -m pytest tools/loops/tests/test_commands_and_tests.py -q
~~~

Commit da tarefa: feat: add loop test gates

## Task 6: adaptadores de agente e revisor

- [x] Concluir a tarefa 6 e validar comandos delimitados e revisão.

Arquivos:

- Criar tools/loops/agents.py.
- Criar tools/loops/reviewer.py.
- Criar tools/loops/prompts/implementation.md.
- Criar tools/loops/prompts/review.md.
- Criar tools/loops/tests/test_agents_and_reviewer.py.

Interfaces:

- AgentRequest(task, evidence, plan, worktree, test_paths) -> AgentResult
- CodexExecAdapter.run(request) -> AgentResult
- ClaudePrintAdapter.run(request) -> AgentResult
- ReviewerRequest(task, evidence, test_delta, diff, worktree) -> ReviewResult
- ReviewAdapter.review(request) -> ReviewResult

Implementação:

1. CodexExecAdapter deverá montar:
   codex exec --cd <worktree> --sandbox workspace-write --ask-for-approval never --output-last-message <artifact> -
   e enviar o prompt pela entrada padrão.
2. ClaudePrintAdapter deverá montar:
   claude -p --add-dir <worktree> --permission-mode acceptEdits --output-format json --no-session-persistence <prompt>
3. Não usar bypass de sandbox, skip de permissões, push, merge, reset destrutivo ou remoção ampla.
4. O prompt de implementação deverá exigir consulta às citações fornecidas, teste vermelho antes da correção, mudança mínima, preservação do escopo e registro da incerteza.
5. O revisor deverá ser somente leitura e validar diff, teste alvo, regressão, evidência e limites da tarefa.
6. A política local deverá rejeitar automaticamente falta de evidência, teste alvo ausente, teste alvo falho, nova regressão, arquivos fora do escopo ou mudança em fonte remota.
7. O resultado do agente deverá registrar argv sanitizado, duração, arquivos tocados e saída em artefato.

Testes que devem falhar antes da implementação:

- test_codex_command_uses_workspace_write_and_no_permission_bypass
- test_claude_command_is_noninteractive_and_scoped
- test_implementation_prompt_requires_citations_and_red_test
- test_reviewer_rejects_missing_citation
- test_reviewer_rejects_new_regression
- test_reviewer_accepts_verified_in_scope_change

Verificação:

~~~powershell
python -m pytest tools/loops/tests/test_agents_and_reviewer.py -q
~~~

Commit da tarefa: feat: add agent and review adapters

## Task 7: supervisor da máquina de estados

- [x] Concluir a tarefa 7 e validar retomada, estacionamento e promoção.

Arquivos:

- Criar tools/loops/supervisor.py.
- Criar tools/loops/tests/test_supervisor.py.

Interfaces:

- SupervisorDeps, contendo discover, research, planner, red, agent, tests, reviewer, worktrees e ledger.
- DevelopmentSupervisor.run_once() -> RunOutcome
- DevelopmentSupervisor.resume(loop_id) -> RunOutcome

Implementação:

1. Executar preflight, capturar base_commit e validar configuração.
2. Descobrir uma única candidata e persistir task.json.
3. Consultar NotebookLM antes do plano; persistir evidence.json.
4. Se faltar fonte pronta, escrever manual-source-requests.md, registrar park e terminar a iteração com outcome manual_source_required.
5. No modo dry-run, produzir candidato e consulta planejada, mas não executar red, agente, teste ou revisão.
6. No modo supervised, exigir red, implementação, targeted, regression e revisão antes de promover.
7. Persistir o ledger após cada transição e também antes de executar comando externo.
8. Em falha, estacionar com uma razão enumerada: invalid_config, missing_source, source_conflict, research_error, red_failed, implementation_error, targeted_failed, regression_failed, build_failed, review_rejected, external_change ou command_timeout.
9. Retomar somente a partir de uma fase persistida e repetível; não repetir uma fase além de max_attempts_per_phase.
10. Antes de promover, confirmar que HEAD raiz continua base_commit e que todos os gates passaram.
11. A promoção inicial será somente commit local na branch da worktree e geração do resultado; a integração no branch do usuário ficará fora do supervisor.

Testes que devem falhar antes da implementação:

- test_dry_run_stops_before_external_mutation
- test_missing_source_parks_and_writes_manual_request
- test_targeted_failure_parks_loop
- test_regression_failure_parks_loop
- test_resume_restarts_from_persisted_phase
- test_external_head_change_prevents_promotion
- test_every_transition_is_persisted
- test_attempt_limit_prevents_infinite_retry

O teste usará fakes para todos os adaptadores e verificará que o supervisor pode completar um ciclo sem chamar serviços externos.

Verificação:

~~~powershell
python -m pytest tools/loops/tests/test_supervisor.py -q
~~~

Commit da tarefa: feat: orchestrate supervised development loop

## Task 8: CLI, documentação e integração local

- [x] Concluir a tarefa 8 e validar CLI e ciclo fake completo.

Arquivos:

- Criar tools/loops/__init__.py.
- Criar tools/loops/__main__.py.
- Criar tools/loops/tests/test_cli.py.
- Criar tools/loops/tests/test_integration.py.
- Modificar tools/README.md.
- Modificar .gitignore se a documentação identificar outro artefato local.

Interface CLI:

~~~text
python -m tools.loops --mode dry-run --max-iterations 1
python -m tools.loops --mode supervised --executor codex --max-iterations 1
python -m tools.loops --mode supervised --executor claude --resume <loop_id>
~~~

Opções obrigatórias:

- --mode com dry-run, supervised ou autonomous
- --max-iterations inteiro positivo
- --executor com codex ou claude
- --project-root opcional, padrão na raiz detectada
- --resume opcional para um loop persistido

Códigos de saída:

- 0 para ciclo controladamente estacionado ou promovido
- 2 para configuração inválida
- 1 para erro inesperado registrado no ledger

Implementação:

1. Encadear CLI, configuração, supervisor e artefatos sem importações circulares.
2. Documentar pré-requisitos, nlm login --check, mapa de notebooks, modos, timeouts, recuperação manual e comandos de verificação.
3. Criar teste de integração com fakes que percorra preflight, discover, research, plan, red, implement, verify, review, record e promote.
4. Criar teste negativo que percorra missing_source até park.
5. Confirmar que nenhuma integração chama rede durante os testes.
6. Registrar session-summary.md com tarefa, evidência, comandos, delta, revisão e próximo passo.

Verificações:

~~~powershell
python -m pytest tools/loops/tests -q
python -m tools.loops --mode dry-run --max-iterations 1
~~~

Commit da tarefa: feat: add development loop CLI

## Task 9: primeira execução real supervisionada

- [ ] Concluir a tarefa 9 somente após a aprovação das tarefas 1 a 8.

Esta tarefa só começa depois de todas as tarefas anteriores passarem.

Baseline obrigatório:

~~~powershell
nlm login --check
python -m pytest tools/loops/tests -q
Push-Location framework\galpao_fw
python tools\run_tests.py -q
Pop-Location
~~~

Procedimento:

1. Rodar dry-run e inspecionar a candidata, a pergunta NotebookLM e os source_ids.
2. Confirmar que o loop não escolheu conteúdo resolvido.
3. Priorizar a nota T16 de fuzz somente depois de dividi-la em uma tarefa de módulo único, começando pelo módulo com teste e critério de segurança mais claros.
4. Rodar uma iteração supervised com Codex ou Claude, conforme o executor escolhido na configuração.
5. Verificar diff, arquivos modificados, targeted, regression e o ledger.
6. Confirmar que a raiz não mudou e que a worktree está isolada.
7. Se houver fonte ausente, entregar o arquivo manual-source-requests.md com notebook, título, caminho local e ação manual; não inventar conteúdo.
8. Se houver falha, manter a worktree e o ledger para retomada; não apagar automaticamente.
9. Registrar o resumo da sessão e o próximo candidato.
10. Não fazer merge ou push automático.

Verificações de encerramento da primeira iteração:

~~~powershell
git status --short
Get-Content .loop-runtime\ledger.json
Get-ChildItem .loop-runtime\runs -Recurse
~~~

## Árvore de testes da fase

Tronco dourado existente:

- ProjetoSpec -> validar -> calcular -> 3D -> executivo.

Ramos do loop:

- Contrato: round-trip, transições inválidas e persistência atômica.
- Segurança: worktree fora do root, HEAD externo, source_id não citado, ausência de fonte e timeout.
- Pesquisa: filtro de status 2, mapa por notebook e pedido manual.
- Descoberta: item aberto, item resolvido, ranking e ID estável.
- Execução: red falho, targeted falho, regressão nova, build separado.
- Integração: ciclo fake completo e ciclo estacionado.
- Recuperação: resume da fase persistida e limite de tentativas.

A suíte própria do loop será executada fora de framework/galpao_fw para não alterar a contagem atual da engenharia. Depois que o loop estiver estável, uma tarefa futura poderá adicionar testes específicos ao trunk do framework.

## Critérios de aceite da implementação

- Um dry-run produz uma candidata determinística e não edita o projeto.
- Uma fonte pronta é consultada pelo notebook e as citações apontam para source_ids solicitados.
- Uma fonte ausente produz uma fila manual acionável.
- Um ciclo supervisionado executa em worktree isolada e registra cada fase.
- Falha nova de targeted, regressão, build obrigatório ou revisão bloqueia promoção.
- O root HEAD alterado por processo externo bloqueia promoção.
- O processo pode ser encerrado e retomado sem perder o ledger.
- O revisor confirma evidência, teste e escopo antes do commit local.
- Todos os testes de tools/loops passam e a suíte existente é medida por baseline/delta.
- Nenhuma credencial é escrita nos artefatos.
- O caminho para execução contínua existe, mas a ativação autônoma só será considerada depois de várias iterações supervisionadas sem falha de segurança.

## Forma de execução

Após a aprovação deste plano:

1. Executar as tarefas 1, 2 e 3.
2. Rodar seus testes e o smoke nlm login --check.
3. Parar para revisão do contrato e do adaptador de fontes.
4. Executar as tarefas 4 a 8.
5. Rodar a suíte própria, dry-run e revisão manual dos artefatos.
6. Executar a tarefa 9 como primeiro ciclo real.

A estratégia recomendada é subagent-driven-development com revisão após cada tarefa; executing-plans é a alternativa para execução linear no mesmo contexto.
