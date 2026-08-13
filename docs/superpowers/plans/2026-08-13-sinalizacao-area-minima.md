# Validação da Área Mínima de Placas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validar a área informada de placas de emergência contra a ABNT NBR 16820:2020 e registrar a unidade no loop supervisionado.

**Architecture:** O módulo puro `sinalizacao_nbr16820.py` continua sendo a única fronteira de cálculo. A validação opcional é incorporada ao retorno existente, o orquestrador apenas repassa a entrada já suportada, e `discovery.py` registra uma unidade atômica com uma fonte normativa única.

**Tech Stack:** Python 3.12, `math`, `pytest`, NotebookLM via `nlm` e máquina de estados em `tools/loops`.

## Global Constraints

- A evidência normativa é somente o source ID `3510e0c9-f90d-41b5-87ca-42446212c710` do NotebookLM `09_INCENDIO`.
- A relação da NBR 16820:2020 é estrita: `A > L²/2000`, válida somente para `L < 50 m`, com distância mínima considerada de `4 m`.
- A ausência de `area_placa_m2` preserva `area_atende=None` e não reprova o gate por área.
- Distância explícita `L >= 50 m`, área negativa ou não finita deve falhar explicitamente; distância `>=50 m` derivada da geometria deve reprovar com segurança sem quebrar o pipeline.
- Não alterar espaçamentos, lados padronizados, SVG, BIM ou APIs existentes além dos campos novos do retorno.
- Toda produção nova deve ter um teste RED observado antes do código GREEN.

---

### Task 1: Especificação e unidade descoberta

**Files:**
- Create: `docs/superpowers/specs/2026-08-13-sinalizacao-area-minima-design.md`
- Create: `docs/superpowers/plans/2026-08-13-sinalizacao-area-minima.md`
- Modify: `framework/galpao_fw/wiki/06-open-threads.md`

**Interfaces:**
- Produces: evidência, contrato e thread T42 usada pelo descobridor.

- [ ] **Step 1: Registrar a especificação e o plano**

  Manter no spec o NotebookLM, o source ID, as seções 5.1.1, 5.1.1.1 e
  5.1.1.2 e a distinção entre distância explícita inválida e saturação derivada.

- [ ] **Step 2: Abrir a thread T42**

  Adicionar à wiki uma pendência objetiva para validar a área mínima real de
  placas NBR 16820. A linha deve ser checkbox aberto e conter `NBR 16820` e
  `área mínima`, para gerar uma tarefa observável.

- [ ] **Step 3: Commitar somente os documentos da fase**

  Run: `git add docs/superpowers/specs/2026-08-13-sinalizacao-area-minima-design.md docs/superpowers/plans/2026-08-13-sinalizacao-area-minima.md framework/galpao_fw/wiki/06-open-threads.md; git commit -m "docs: plan emergency sign area validation"`

  Expected: commit criado sem incluir alterações pré-existentes do usuário.

### Task 2: RED do contrato do dimensionador

**Files:**
- Create: `framework/galpao_fw/tests/test_sinalizacao_nbr16820.py`

**Interfaces:**
- Consumes: `sinalizacao_nbr16820.area_minima_placa` e
  `sinalizacao_nbr16820.dimensiona_sinalizacao`.
- Produces: testes de comportamento que falham antes da implementação.

- [ ] **Step 1: Escrever os testes focais**

  Cobrir, com código executável, os seguintes casos:

  ```python
  def test_area_informada_obedece_inequacao_estrita():
      assert not dimensiona_sinalizacao({"C": 20, "L": 20,
                                         "dist_visualizacao_m": 10,
                                         "area_placa_m2": 0.05})["area_atende"]
      assert dimensiona_sinalizacao({"C": 20, "L": 20,
                                     "dist_visualizacao_m": 10,
                                     "area_placa_m2": 0.051})["area_atende"]

  def test_distancia_minima_de_quatro_metros_e_aplicada():
      r = dimensiona_sinalizacao({"C": 20, "L": 20,
                                  "dist_visualizacao_m": 3,
                                  "area_placa_m2": 0.009})
      assert r["distancia_calculo_m"] == 4.0
      assert r["area_minima_m2"] == 0.008
      assert r["area_atende"] is True

  def test_sem_area_preserva_modo_legado():
      r = dimensiona_sinalizacao({"C": 40, "L": 20})
      assert r["area_placa_m2"] is None and r["area_atende"] is None and r["OK"]
  ```

  Adicionar parâmetros para área `-0.1`, `nan`, `inf`, `-inf`, `True` e texto,
  e para distância explícita `50`, `nan` e `inf`, exigindo `ValueError`.
  Também cobrir o galpão derivado `100 x 60`, que deve retornar `OK=False` e
  `limite_normativo_excedido=True` sem levantar exceção.

- [ ] **Step 2: Rodar RED**

  Run: `python -m pytest framework/galpao_fw/tests/test_sinalizacao_nbr16820.py -q`

  Expected: falha por campos ausentes e por validações ainda não implementadas;
  não editar produção antes de observar essa falha.

- [ ] **Step 3: Commitar o RED**

  Run: `git add framework/galpao_fw/tests/test_sinalizacao_nbr16820.py; git commit -m "test: specify emergency sign area gate"`

### Task 3: Implementação GREEN do módulo

**Files:**
- Modify: `framework/galpao_fw/sinalizacao_nbr16820.py`
- Test: `framework/galpao_fw/tests/test_sinalizacao_nbr16820.py`

**Interfaces:**
- Consumes: `C`, `L`, `dist_visualizacao_m` opcional e `area_placa_m2` opcional.
- Produces: campos `distancia_calculo_m`, `area_minima_m2`, `area_placa_m2`,
  `area_atende` e `limite_normativo_excedido`, mantendo o retorno antigo.

- [ ] **Step 1: Adicionar guardas finitas mínimas**

  Criar helpers internos para rejeitar booleanos, tipos não numéricos,
  `NaN`, infinitos e valores não positivos nos campos de distância/geometria;
  aceitar zero apenas como área informada, que será reprovada pela desigualdade.

- [ ] **Step 2: Implementar a comparação normativa**

  Calcular `L_calc = max(L_vis, DIST_MIN_PROJETO_M)` somente no domínio
  `0 < L_calc < 50`, comparar `area_placa_m2 > area_minima_m2` sem arredondar e
  preservar `placa_area_min_m2` arredondado para compatibilidade.

- [ ] **Step 3: Preservar saturação derivada**

  Para distância padrão derivada `>=50 m`, manter a placa máxima e `OK=False`,
  registrar `limite_normativo_excedido=True` e evitar apresentar uma área como
  cálculo normativo. Para distância explícita no mesmo domínio, levantar
  `ValueError` antes de calcular.

- [ ] **Step 4: Rodar GREEN focal**

  Run: `python -m pytest framework/galpao_fw/tests/test_sinalizacao_nbr16820.py -q`

  Expected: todos os testes focais passam sem warnings novos.

- [ ] **Step 5: Commitar a implementação**

  Run: `git add framework/galpao_fw/sinalizacao_nbr16820.py framework/galpao_fw/tests/test_sinalizacao_nbr16820.py; git commit -m "fix: validate emergency sign area"`

### Task 4: Registrar a unidade no loop

**Files:**
- Modify: `tools/loops/discovery.py`
- Modify: `tools/loops/tests/test_discovery.py`
- Modify: `framework/galpao_fw/wiki/06-open-threads.md`

**Interfaces:**
- Consumes: thread T42 e caminho local da NBR 16820.
- Produces: candidato `sinalizacao-area-minima`, tópico `sinalizacao`,
  disciplina `seguranca`, prioridade 75 e exatamente uma fonte.

- [ ] **Step 1: Escrever RED da descoberta**

  Exigir origem com suffix `:sinalizacao-area-minima`, título atômico, tópico,
  disciplina, prioridade, caminho
  `09_INCENDIO/INCENDIO__NBR__NBR-16820-2020__sinalizacao-emergencia.pdf` e
  sugestão do teste focal.

- [ ] **Step 2: Rodar RED da descoberta**

  Run: `python -m pytest tools/loops/tests/test_discovery.py -q`

  Expected: falha apenas porque a decomposição atômica ainda não existe.

- [ ] **Step 3: Implementar o candidato atômico**

  Adicionar a constante de fonte, a ramificação T42 em `_candidates_for_item`
  e termos específicos de `sinalizacao` em `_tests_for_candidate`, sem alterar
  as prioridades ou fontes dos candidatos fotovoltaicos/T16.

- [ ] **Step 4: Fechar a thread e rodar GREEN**

  Após a implementação, marcar T42 como resolvida com referência ao módulo e
  testes. Rodar:

  `python -m pytest tools/loops/tests/test_discovery.py -q`

  Expected: descoberta determinística, candidato atômico presente no estado
  aberto testado e thread fechada não redescoberta.

- [ ] **Step 5: Commitar a integração**

  Run: `git add tools/loops/discovery.py tools/loops/tests/test_discovery.py framework/galpao_fw/wiki/06-open-threads.md; git commit -m "feat: discover emergency sign validation unit"`

### Task 5: Regressão, revisão e evidência do loop

**Files:**
- Modify: `sessions/2026-08-13.md`
- Modify: `.superpowers/sdd/progress.md`

- [ ] **Step 1: Rodar regressões focais**

  ```powershell
  python -m pytest framework/galpao_fw/tests/test_sinalizacao_nbr16820.py framework/galpao_fw/tests/test_seguranca_incendio.py framework/galpao_fw/tests/test_incendio_robustez.py framework/galpao_fw/tests/test_saturacao_verdito.py -q
  python -m pytest tools/loops/tests -q
  python -m py_compile framework/galpao_fw/sinalizacao_nbr16820.py tools/loops/discovery.py
  git diff --check
  ```

- [ ] **Step 2: Revisar o diff contra o spec**

  Confirmar que cada regra nova aponta para o source ID da NBR 16820, que a
  comparação não usa valor arredondado e que nenhuma chamada antiga perdeu
  campos ou passou a falhar no cenário gigante já coberto.

- [ ] **Step 3: Reautenticar e executar dry-run**

  Run: `nlm login --check` e depois
  `python -m tools.loops --mode dry-run --max-iterations 1 --executor codex`.

  Registrar o outcome, tarefa escolhida e eventual bloqueio de fonte em
  `.loop-runtime/scheduler-last.json`; não transformar bloqueio de outra tarefa
  em falsa conclusão desta fase.

- [ ] **Step 4: Registrar fatos**

  Acrescentar no log da sessão contagens reais RED/GREEN, regressão, suíte do
  loop, compilação, dry-run e revisão. Atualizar `.superpowers/sdd/progress.md`
  somente depois de todos os critérios observados.
