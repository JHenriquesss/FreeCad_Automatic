# Fase 6A hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir os achados da revisão ampla da Fase 6A antes de declarar o dimensionamento residencial confiável dentro do escopo aprovado.

**Architecture:** O calculador residencial continuará sendo uma camada de contrato sobre as tabelas genéricas. A fronteira residencial rejeitará domínios que as tabelas atuais não cobrem, capturará falhas de domínio como erros estruturados e devolverá o envelope completo documentado; o Loop será apenas alinhado aos resultados.

**Source decision:** A consulta NotebookLM ao notebook elétrico `78cd2efd-0652-484e-b312-c5c5a7648962`, fonte NBR 5410 `d213019d-6e5c-4f18-8151-bf5a74c11b5d`, confirmou que `power_va` representa potência aparente `S` e que `IB=S/V` (monofásico) ou `IB=S/(sqrt(3)*V)` (trifásico). `fp` não será aplicado novamente à corrente.

## Global Constraints

- `power_va` é potência aparente; a fórmula da corrente não divide novamente por `power_factor`.
- Só serão aceitos `grouping_count` presentes nas colunas cobertas pelas tabelas genéricas: `1, 2, 3, 4, 6, 9`.
- Só serão aceitos fatores de potência com coluna de queda coberta explicitamente: `0.8`, `0.95` e `1.0`; para `1.0`, o resultado registra a coluna de referência `0.95` usada pela tabela existente.
- Lista, dicionário ou outro valor não-hashable em campos enumerados deve retornar erro estruturado, nunca `TypeError`.
- Exceção de domínio levantada pelas tabelas genéricas deve ser convertida em erro estruturado no calculador público.
- `short_circuit_evaluation` só será `implemented` quando todos os designs calculados tiverem curto completo e avaliado; cenário misto permanece `not_evaluated` com aviso.
- A rastreabilidade NBR 5410 será baseada no `source_id` autoritativo, não no título textual.
- A API pública retornará `points` e `routes`, além de `ok/errors/warnings/designs/scope`.
- A jornada anterior `casa-residencial-sintetica` permanecerá no trunk; o fixture elétrico será anexado, não substituirá a cobertura existente.

## Task 5A: contrato e calculador

**Files:**
- Modify: `framework/galpao_fw/dimensionamento_eletrico_residencial.py`
- Test: `framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py`

- [ ] Escrever testes RED para VA/fp, grouping/fp fora de domínio, tipos não-hashable, comprimento extremo, curto completo/misto, fonte sem título e envelope `points/routes`.
- [ ] Rodar o teste focal e registrar as falhas esperadas.
- [ ] Corrigir o calculador com validação explícita, fórmula VA, captura por design, escopo agregado por `all`, rastreabilidade por ID e envelope completo.
- [ ] Rodar a branch inteira e garantir GREEN.
- [ ] Commitar `feat/fix: harden residential electrical contract` com relatório TDD.

## Task 5B: fixture, trunk e documentação

**Files:**
- Modify: `framework/galpao_fw/residencial_eletrica.py`
- Modify: `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py`
- Modify: `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`
- Modify: `projects/casa-residencial-eletrica-sintetica/project-spec.json`
- Modify: `projects/casa-residencial-eletrica-sintetica/README.md`
- Modify: `docs/superpowers/specs/2026-08-16-fase-6a-dimensionamento-eletrico-residencial.md`
- Modify: `docs/superpowers/plans/2026-08-16-dimensionamento-eletrico-residencial.md`

- [ ] Atualizar fixtures de `power_factor` para o domínio explicitamente coberto e manter `power_va` como VA.
- [ ] Alinhar docstring, README, spec e plan à fórmula e ao resultado coordenado.
- [ ] Restaurar a execução do fixture `casa-residencial-sintetica` no trunk e manter o fixture elétrico adicional.
- [ ] Adicionar teste de integração para o curto misto e a rastreabilidade persistida.
- [ ] Rodar branch, trunk, regressões do adaptador, `compileall` e `git diff --check`.
- [ ] Commitar `fix: align residential fixtures and golden journey` com relatório.

## Exit condition

Todos os achados Critical/Important da revisão ampla estão cobertos por teste ou corrigidos com evidência, e a revisão ampla seguinte não encontra bloqueios.

## Execution record

- Task 5B implementation is complete; independent review is still pending and
  this record does not mark the phase as approved.
- Task 5A was implemented in `e107283` and completed with the explicit
  three-phase apparent-power test in `6e718e6`.
- Task 5B keeps the prior `casa-residencial-sintetica` golden journey,
  appends the persisted residential electrical journey, and aligns the
  integration fixture with the 6000 VA / 220 V coordinated case.
- The wrapper contract remains deliberately bounded: supported grouping
  columns are `1, 2, 3, 4, 6, 9`; supported power factors are `0.8`, `0.95`
  and `1.0`, with `0.95` as the voltage-drop reference for `1.0`.
- No generic table module was changed, and the phase still does not claim
  Enel approval, construction readiness, short-circuit evaluation without
  complete inputs, or IFC/2D executive deliverables.
