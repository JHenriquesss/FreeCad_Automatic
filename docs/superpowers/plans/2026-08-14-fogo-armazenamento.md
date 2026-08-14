# Phase 33: fogo_armazenamento

## Scope

Adicionar o gate puro da NBR 16981:2021 para armazenamento e integrá-lo ao vertical de segurança contra incêndio do galpão. A fase cobre somente os requisitos explicitamente citados na fonte autorizada; não altera o cálculo histórico da NBR 10897.

## Entry condition

- A fonte local `fontes/09_INCENDIO/INCENDIO__NBR__NBR-16981-2021__sprinklers-areas-armazenamento.pdf` existe e está pronta no notebook `a7e4b5d9-4e07-401b-970e-e973bae3aada`.
- O adaptador de pesquisa está no commit `a7a8b32` e converte a resposta JSON aninhada em citações auditáveis.
- A suíte `tools/loops/tests` está verde antes da mudança da fase.

## Exit condition

- A candidata `fogo_armazenamento` é descoberta com caminho de fonte explícito e prompt restrito ao source ID `ce183de0-750c-4330-bf4d-a5a67a15f012`.
- O gate puro atende aos casos completos, reprova violações e marca dados/lacunas ausentes como inconclusivos.
- `galpao_seguranca_incendio.rodar()` publica o gate somente quando o bloco de armazenamento é fornecido e inclui seu resultado em `ATENDE`.
- O loop executa targeted, regressão, revisão e registro; nenhuma fonte remota é alterada.

## Must-exist checklist

- [ ] `framework/galpao_fw/armazenamento_nbr16981.py` com `verifica_armazenamento_nbr16981(caso)` e retorno estável.
- [ ] `framework/galpao_fw/tests/test_armazenamento_nbr16981.py` cobre completo, ausente, densidade/área, encapsulado, ESFR, intraprateleiras, papel e lacuna tissue.
- [ ] `framework/galpao_fw/galpao_seguranca_incendio.py` publica `gates["armazenamento_nbr16981"]` sem alterar a saída quando o bloco não existe.
- [ ] `framework/galpao_fw/tests/test_seguranca_incendio.py` cobre integração do gate e preservação do contrato antigo.
- [ ] `tools/loops/discovery.py` e seus testes expõem a candidata com o source path canônico.
- [ ] `tools/loops/__main__.py` e seus testes geram pergunta e retry somente para NBR 16981.
- [ ] EvidenceBundle contém exclusivamente o source ID autorizado, seção e `cited_text`.
- [ ] `git diff --check`, `py_compile`, targeted, regressão e revisão passam conforme os gates do loop.

## Must-not-exist checklist

- [ ] Nenhum default de altura, classe de mercadoria, densidade, área ou vazão no gate de produção.
- [ ] Nenhuma citação de NBR 10897, NBR 13792, IT estadual ou fabricante usada para decidir o gate.
- [ ] Nenhum cálculo novo de bomba, RTI, hidrante ou tabela completa ESFR nesta fase.
- [ ] Nenhuma resposta com `sources_used` vazio ou `cited_text` ausente promovida a evidência.
- [ ] Nenhum upload, remoção, merge ou push remoto executado pelo loop.

## Test plan

### Positive

- [ ] Caso completo com altura até 3,7 m passa sem exigir os requisitos condicionais de armazenamento alto.
- [ ] Caso acima de 3,7 m com densidade 6,1, área 186 e não interpolação passa.
- [ ] Caso encapsulado com densidade de projeto igual a 1,25 vezes a base passa.
- [ ] Caso ESFR com 12 chuveiros, 3 ramais e ausência de extração/barreira passa.
- [ ] Caso intraprateleiras dentro de 3.700 m² passa sem inventar limite de vazão ausente.
- [ ] Caso de bobinas de papel com chuveiro de alta temperatura e área por chuveiro entre 6,5 m² e 9,3 m² passa.

### Negative

- [ ] Configuração vazia ou campo condicional ausente retorna `OK=False`, `inconclusivo=True`.
- [ ] Densidade abaixo de 6,1 L/min/m² ou área abaixo de 186 m² reprova.
- [ ] Encapsulamento sem aumento de 25%, interpolação verdadeira ou ESFR com quantidade/ramais incompatíveis reprova.
- [ ] Área intraprateleiras acima de 3.700 m² reprova; a vazão de 115 L/min permanece lacuna não decisória.
- [ ] Bobina de papel alta sem chuveiro de alta temperatura reprova.
- [ ] Tissue acima de 6,1 m marca lacuna inconclusiva, sem inventar critério.
- [ ] Integração sem o bloco de armazenamento preserva os gates históricos; integração com bloco vazio reprova por inconclusividade.

## Test tree integration

- Trunk touch point: jornada E2E do galpão na etapa de segurança contra incêndio, antes da emissão de SVG/IFC e depois da entrada explícita de geometria e sistemas.
- New branches added: `test_armazenamento_nbr16981.py` para o gate puro; `test_seguranca_incendio.py` para integração; discovery/CLI para a cadeia fonte → pesquisa.

## Next phase seed

Após a promoção, iniciar a NBR 14323 quando o PDF for carregado, ou separar reservatórios/ bombas hidráulicos com fontes próprias.

---

# Fogo armazenamento Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use the existing development loop supervisor to execute the tasks in this plan, with RED/GREEN and review gates.

**Goal:** Validar requisitos explícitos de armazenamento da NBR 16981:2021 e publicar um gate auditável no vertical de incêndio.

**Architecture:** Um módulo puro concentra a validação condicional e retorna `OK`, `inconclusivo`, faltantes e violações. O orquestrador chama esse módulo somente quando `spec["armazenamento_nbr16981"]` existe; a descoberta e o adaptador carregam a mesma fonte por caminho/source ID explícitos.

**Tech Stack:** Python 3.12, pytest, NotebookLM CLI, JSON EvidenceBundle, módulos puros existentes do `framework/galpao_fw`.

## Global Constraints

- Fonte autorizada: source ID `ce183de0-750c-4330-bf4d-a5a67a15f012`.
- Limites normativos usados: 3,7 m; 6,1 L/min/m²; 186 m²; 25%; 12 chuveiros; 3 ramais; 3.700 m²; 4,6 m; 6,5–9,3 m²; 6,1 m para a lacuna tissue. O alegado limite de 115 L/min acima de 7,6 m não foi determinado pela fonte e fica fora do gate.
- Nenhum valor ausente recebe default.
- A NBR 10897 existente continua inalterada.

### Task 1: Discover and research contract

**Files:**
- Modify: `tools/loops/discovery.py`
- Modify: `tools/loops/__main__.py`
- Test: `tools/loops/tests/test_discovery.py`
- Test: `tools/loops/tests/test_cli.py`

**Interfaces:**
- Produces task ID derived from `fontes/pendencias-atualizacao.md`, topic `fogo_armazenamento`, source path `09_INCENDIO/INCENDIO__NBR__NBR-16981-2021__sprinklers-areas-armazenamento.pdf`.
- Produces research prompts requiring source ID `ce183de0-750c-4330-bf4d-a5a67a15f012`, sections 4, 5, 6, 8, 9, B and 12, with explicit no-invention/lacuna wording.

- [ ] Write failing discovery and prompt assertions for the exact topic, path, source ID and suggested tests.
- [ ] Run `python -m pytest -q tools/loops/tests/test_discovery.py tools/loops/tests/test_cli.py -k armazenamento`; expected failure because the candidate/prompt branches do not exist.
- [ ] Add the narrow source constant and topic branches, preserving all existing candidates.
- [ ] Run the focused tests; expected result is green with no changes to remote sources.
- [ ] Run `git diff --check` and commit the discovery contract.

### Task 2: Pure NBR 16981 validator

**Files:**
- Create: `framework/galpao_fw/armazenamento_nbr16981.py`
- Test: `framework/galpao_fw/tests/test_armazenamento_nbr16981.py`

**Interfaces:**
- Consumes: explicit `caso: dict` fields named in the spec.
- Produces: `dict` with boolean `OK`, boolean `inconclusivo`, lists `faltantes`, `violacoes`, and `requisitos_aplicados`.

- [ ] Write the RED tests listed in the phase plan using real calls to `verifica_armazenamento_nbr16981`.
- [ ] Run `python -m pytest -q framework/galpao_fw/tests/test_armazenamento_nbr16981.py`; expected failures must be missing-function/API failures.
- [ ] Implement numeric/boolean validation, conditional requirements and only the cited limits from the spec.
- [ ] Run the focused test file; expected result is green.
- [ ] Run `python -m py_compile framework/galpao_fw/armazenamento_nbr16981.py` and commit the pure validator.

### Task 3: Integrate the gate

**Files:**
- Modify: `framework/galpao_fw/galpao_seguranca_incendio.py`
- Test: `framework/galpao_fw/tests/test_seguranca_incendio.py`

**Interfaces:**
- Consumes: `armazenamento_nbr16981.verifica_armazenamento_nbr16981` and optional `spec["armazenamento_nbr16981"]`.
- Produces: `result["gates"]["armazenamento_nbr16981"]` and `reprovados/ATENDE` updates only when the block is present.

- [ ] Add RED integration assertions for complete, empty and absent storage blocks.
- [ ] Run the focused integration tests and observe the missing gate/API failure.
- [ ] Import the pure module, call it conditionally, add the gate, and preserve the no-block output.
- [ ] Run `python -m pytest -q framework/galpao_fw/tests/test_seguranca_incendio.py`; expected result is green.
- [ ] Run `python -m pytest -q framework/galpao_fw/tests/test_seguranca_incendio.py framework/galpao_fw/tests/test_incendio_robustez.py framework/galpao_fw/tests/test_incendio_bim.py` and commit the integration.

### Task 4: Execute the supervised loop

**Files:**
- Read: `.loop-runtime/ledger.json`, `.loop-runtime/runs/<loop-id>/evidence.json`, `.loop-runtime/runs/<loop-id>/test-delta.json`.
- Update: `sessions/2026-08-13.md` through the session-log workflow.

- [ ] Run `nlm login --check` before the scoped research.
- [ ] Run the supervised loop with source scope and bounded timeouts.
- [ ] Confirm targeted tests, regression delta, local review, and promoted commit.
- [ ] Record source ID, conversation ID, tests, preexisting failures and next seed.
