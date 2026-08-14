# Segurança da água quente — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar gates auditáveis de segurança da rede de água quente usando somente a ABNT NBR 5626:2020 já catalogada.

**Architecture:** O descobridor cria uma candidata atômica com escopo para a fonte local da NBR 5626:2020. A camada pura `hidraulica_predial` valida dados explícitos e a vertical `galpao_hidraulica` expõe o resultado como rede/gate; dados ausentes são inconclusivos e não aprovam o dimensionamento completo.

**Tech Stack:** Python 3.12, pytest, NotebookLM CLI existente, worktree supervisionada pelo loop.

## Global Constraints

- Consultar apenas `07_HIDRAULICA/HIDRAULICA__NBR__NBR-5626-2020__agua-fria-quente.pdf`.
- Usar somente citações textuais do source ID `88bbe8c0-cab9-44e4-bfe6-8b895d8d6fc2`.
- Não inventar limite numérico para pressão “próxima”, isolamento ou dilatação.
- Não alterar fontes, notebooks, redes fria/esgoto/pluvial ou itens de reservatório/bomba.
- Produção sem bloco de segurança completo deve ficar `OK=False`/inconclusiva, nunca aprovada silenciosamente.

---

### Task 1: Contratos RED da descoberta, pesquisa e cálculo

**Files:**
- Modify: `tools/loops/tests/test_discovery.py`
- Modify: `tools/loops/tests/test_cli.py`
- Create: `framework/galpao_fw/tests/test_agua_quente_seguranca.py`

**Interfaces:**
- Consumes: `discover_candidates`, `_research_question`, `_research_retry_question` e o módulo hidráulico real.
- Produces: candidata `agua_quente_segura`, prompts específicos e testes de comportamento normativo.

- [ ] **Step 1: Add failing discovery and prompt tests**

Criar uma pendência temporária com o texto de água quente e afirmar que a
candidata tem `topic="agua_quente_segura"`, disciplina `hidraulica`, origem
terminada em `:agua-quente-segura` e exatamente o caminho NBR 5626. A candidata
ampla deve continuar com `source_paths=()`.

Criar teste do prompt normal/retry exigindo `5626`, `6.7`, `6.9`, `6.10`,
`6.11`, `6.12`, `6.13`, o source ID e “citações textuais” no retry.

- [ ] **Step 2: Add failing engineering tests**

Criar testes para: ausência de configuração retornar `OK=False` e
`inconclusivo=True`; configuração completa retornar `OK=True`; temperatura
corporal acima de 45 °C sem limitador reprovar; pressão estática acima de 400
kPa reprovar; e integração da vertical publicar
`gates["seguranca_agua_quente"]`.

- [ ] **Step 3: Run RED**

```powershell
python -m pytest -q framework/galpao_fw/tests/test_agua_quente_seguranca.py tools/loops/tests/test_discovery.py -k "agua_quente or hot_water"
python -m pytest -q tools/loops/tests/test_cli.py -k agua_quente
```

Esperado: falhas porque a candidata/prompt/função ainda não existem.

### Task 2: Descoberta e consulta auditável

**Files:**
- Modify: `tools/loops/discovery.py`
- Modify: `tools/loops/__main__.py`

- [ ] **Step 1: Add the canonical source constant and discovery branch**

Adicionar a tupla com o caminho exato e decompor somente o item de expansão
hidráulica, mantendo a candidata ampla.

- [ ] **Step 2: Add topic-specific prompt and retry**

Exigir requisitos verificáveis, seção/condição, source ID exato, trechos
textuais e lacunas sem parâmetros universais; proibir preenchimento por outras
fontes.

- [ ] **Step 3: Run focused GREEN**

```powershell
python -m pytest -q tools/loops/tests/test_discovery.py -k agua_quente
python -m pytest -q tools/loops/tests/test_cli.py -k agua_quente
```

### Task 3: Implementação mínima guiada pelo RED

**Files:**
- Modify: `framework/galpao_fw/hidraulica_predial.py`
- Modify: `framework/galpao_fw/galpao_hidraulica.py`
- Modify: `framework/galpao_fw/tests/test_galpao_hidraulica.py` somente se a API existente precisar receber o bloco explícito.

- [ ] **Step 1: Implement `verifica_agua_quente_seguranca`**

Validar tipos/valores, produzir razões por requisito, reprovar violações
explícitas e marcar dados ausentes como inconclusivos. Não criar valores
default.

- [ ] **Step 2: Integrate the gate**

Passar a vazão calculada e a pressão dinâmica residual da rede quente; publicar
o resultado em `redes.agua_quente.seguranca` e `gates.seguranca_agua_quente`;
incluir o gate no dimensionamento completo/`ATENDE`.

- [ ] **Step 3: Run GREEN and hydraulic regression**

```powershell
python -m pytest -q framework/galpao_fw/tests/test_agua_quente_seguranca.py framework/galpao_fw/tests/test_hidraulica_predial.py framework/galpao_fw/tests/test_galpao_hidraulica.py
```

### Task 4: Verificação do loop e revisão

**Files:**
- Modify: `fontes/pendencias-atualizacao.md` somente para registrar a unidade e preservar a pendência ampla.
- Modify: `sessions/2026-08-13.md`.

- [ ] **Step 1: Run full loop suite and project hydraulic tests**

```powershell
python -m pytest -q tools/loops/tests
python -m pytest -q framework/galpao_fw/tests/test_hidraulica_predial.py framework/galpao_fw/tests/test_galpao_hidraulica.py framework/galpao_fw/tests/test_agua_quente_seguranca.py
git diff --check
```

- [ ] **Step 2: Revalidate NotebookLM and run bounded supervised loop**

```powershell
nlm login --check
python -m tools.loops --mode supervised --max-iterations 1 --command-timeout 180
```

Esperado: a candidata atômica é pesquisada com a fonte autorizada; se o
executor ou os gates falharem, preservar o ledger e registrar a causa.

- [ ] **Step 3: Review, record and commit only phase files**

Conferir source IDs, diff permitido, RED/GREEN, targeted, regressão e revisão.
Atualizar o log com evidências e não tocar nos arquivos de usuário fora da
fase.

## Next phase seed

Separar a pendência residual de reservatórios/bombas/recirculação e obter fontes
específicas antes de implementar geração ou armazenamento de água quente.
