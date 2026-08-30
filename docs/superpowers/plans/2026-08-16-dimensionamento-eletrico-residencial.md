# Dimensionamento elétrico residencial — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar ao adaptador residencial o dimensionamento auditável de condutores e proteções para designs de circuitos explicitamente declarados.

**Architecture:** Um módulo residencial fino validará o contrato e mapeará os dados para os calculadores normativos genéricos já existentes. O runner continuará responsável por fontes, demanda, status e persistência; a fase não cria entregáveis CAD/BIM.

**Tech Stack:** Python 3.12, pytest, JSON, `condutores_nbr5410.py`, `protecao_nbr5410.py` e o Loop universal existente.

## Global Constraints

- Não haverá defaults para comprimento, método, isolação, temperatura, agrupamento, fator de potência, limite de queda, uso, local, exposição ou curto.
- A NBR 5410:2004 será consultada pelo NotebookLM `78cd2efd-0652-484e-b312-c5c5a7648962`, fonte `d213019d-6e5c-4f18-8151-bf5a74c11b5d`; tabelas normativas não serão duplicadas no adaptador.
- Circuito sem `short_circuit` completo permanecerá `needs_review` com `short_circuit_evaluation: not_evaluated`.
- A fase não emitirá IFC, FCStd, DXF, SVG, PDF, unifilar ou prancha 2D.
- O núcleo universal não conterá dados hardcoded de galpão, casa, município ou concessionária.
- Nenhum teste usará mock do calculador sob teste; o teste de processo poderá usar somente filesystem temporário e o fixture persistido.

## Mapa de arquivos

- Criar `framework/galpao_fw/dimensionamento_eletrico_residencial.py`: contrato, validação, corrente, mapeamento e composição condutor/proteção.
- Criar `framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py`: testes de contrato, cálculo e falhas.
- Modificar `framework/galpao_fw/residencial_eletrica.py`: chamar o calculador e expor o novo escopo.
- Modificar `projects/casa-residencial-eletrica-sintetica/project-spec.json`: declarar designs explícitos, mantendo o fixture sintético.
- Modificar `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py`: enriquecer a fábrica de spec com designs para preservar os testes da vertical.
- Modificar `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`: anexar o fixture elétrico ao percurso universal.
- Atualizar `projects/casa-residencial-eletrica-sintetica/README.md`: registrar a nova entrada e o status ainda não executivo.

### Task 1: Escrever os testes vermelhos do contrato e do dimensionamento

**Files:**
- Create: `framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py`

**Interfaces:**
- O módulo sob teste exporá `calculate_residential_circuit_designs(circuits, source_refs)`.
- O teste chamará a API real com dicionários Python e conferirá o envelope final, não funções privadas.

- [ ] **Step 1: Write the failing tests**

Criar uma fábrica local de pontos e designs e incluir estes casos, sem `pytest.skip`:

```python
def test_chuveiro_residencial_dimensiona_resultado_final_coordenado():
    result = calculate_residential_circuit_designs(_circuits(
        point={"id": "TUE-01", "room": "banheiro", "kind": "tue",
               "power_va": 6000, "voltage_v": 220},
        design=_design(point_id="TUE-01", length_m=18.0, use="forca",
                        location="banheiro", power_factor=1.0)), SOURCE_REFS)
    item = result["designs"][0]
    assert item["load"]["current_a"] == pytest.approx(6000 / 220)
    assert item["base_conductor"]["secao_mm2"] == 6
    assert item["conductor"]["secao_mm2"] == 10
    assert item["protection"]["disjuntor"]["IN"] == 32
    assert item["protection"]["OK"] is True


def test_queda_de_tensao_pode_ser_o_criterio_governante():
    result = calculate_residential_circuit_designs(_circuits(
        point={"id": "TUG-01", "room": "sala", "kind": "tug",
               "power_va": 2000, "voltage_v": 127},
        design=_design(point_id="TUG-01", length_m=80.0, use="forca",
                        location="seco", power_factor=0.8)), SOURCE_REFS)
    assert result["designs"][0]["conductor"]["governante"] == "queda"


def test_sem_curto_explica_revisao_sem_inventar_icc():
    result = calculate_residential_circuit_designs(_circuits(
        point={"id": "L-01", "room": "sala", "kind": "lighting",
               "power_va": 100, "voltage_v": 127},
        design=_design(point_id="L-01", length_m=10.0, use="iluminacao",
                        location="seco")), SOURCE_REFS)
    assert result["ok"] is True
    assert result["designs"][0]["short_circuit"]["status"] == "not_evaluated"
    assert result["scope"]["short_circuit_evaluation"] == "not_evaluated"


@pytest.mark.parametrize("mutator, code", [
    (lambda c: c.pop("designs"), "missing_circuit_designs"),
    (lambda c: c["designs"][0].pop("length_m"), "missing_design_field"),
    (lambda c: c["designs"][0].update({"point_ids": ["UNKNOWN"]}),
     "unknown_design_point"),
    (lambda c: c["designs"].append(copy.deepcopy(c["designs"][0])),
     "duplicate_design_id"),
    (lambda c: c["designs"][0].update({"short_circuit": {"Icc_A": 5000}}),
     "invalid_short_circuit"),
])
def test_contrato_invalido_bloqueia_sem_heuristica(mutator, code):
    circuits = _circuits()
    mutator(circuits)
    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)
    assert result["ok"] is False
    assert any(error["code"] == code for error in result["errors"])
```

Também incluir testes de tensão inconsistente, ponto duplicado entre designs, método/isolação inválidos, `NaN`/infinito e nenhum disjuntor coordenável.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py -q
```

Expected: FAIL during collection because `dimensionamento_eletrico_residencial` ainda não existe, ou falha equivalente do contrato ausente. Não corrigir escrevendo produção nesta tarefa.

- [ ] **Step 3: Commit**

```powershell
git add framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py
git commit -m "test: add red contract for residential circuit sizing"
```

### Task 2: Implementar o calculador residencial mínimo

**Files:**
- Create: `framework/galpao_fw/dimensionamento_eletrico_residencial.py`
- Test: `framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py`

**Interfaces:**
- Produz `calculate_residential_circuit_designs(circuits: dict, source_refs: list[dict]) -> dict`.
- Usa `dimensiona_condutor` e `dimensiona_protecao` somente depois da validação completa.

- [ ] **Step 1: Implementar somente o contrato e o cálculo coberto**

O mapa para as APIs existentes deve ser equivalente a:

```python
conductor_input = {
    "IB": current_a,
    "V": voltage_v,
    "L_km": length_m / 1000.0,
    "sistema": design["system"],
    "n_cond": design["conductors_loaded"],
    "isolacao": design["insulation"],
    "metodo": design["reference_method"],
    "fp": design["power_factor"],
    "temp_amb": design["ambient_temperature_C"],
    "n_agrupados": design["grouping_count"],
    "uso": design["use"],
    "dv_max": design["voltage_drop_limit_pct"],
}
```

Somar `power_va`, calcular a corrente monofásica ou trifásica conforme a especificação, selecionar a proteção, repetir o condutor com `I_protecao`, e retornar os campos de rastreabilidade e status. Erros devem ser dados estruturados e não exceções de entrada.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
pytest framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py -q
```

Expected: all tests da API nova passam.

- [ ] **Step 3: Commit**

```powershell
git add framework/galpao_fw/dimensionamento_eletrico_residencial.py framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py
git commit -m "feat: dimension residential electrical circuits"
```

### Task 3: Integrar no adaptador e no fixture persistido

**Files:**
- Modify: `framework/galpao_fw/residencial_eletrica.py`
- Modify: `projects/casa-residencial-eletrica-sintetica/project-spec.json`
- Modify: `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py`
- Test: `framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py`

**Interfaces:**
- `run_residential_electrical` chama o calculador com `payload["circuits"]` e as referências elétricas.
- O registro `disciplines.eletrico["circuits"]` preserva `points`, `routes`, `designs`, `errors` e `warnings`.

- [ ] **Step 1: Escrever/estender o teste de integração antes da alteração**

Adicionar ao branch e ao fixture a expectativa de que `run_project_file` devolve `needs_review`, contém três designs calculados, `conductor_sizing == implemented`, `protection_sizing == implemented`, e continua com todos os artefatos JSON hashados.

- [ ] **Step 2: Executar o teste vermelho de integração**

```powershell
pytest framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py -q
```

Expected: falha porque o runner ainda não chama o módulo novo e o fixture ainda não tem `designs`.

- [ ] **Step 3: Integrar sem mudar o núcleo universal**

No runner, combinar os erros do novo calculador com os erros existentes, preservar os warnings de readiness e substituir os campos de escopo `not_implemented` por `implemented` apenas para condutor/proteção. Não emitir artefato de engenharia novo nesta fase.

- [ ] **Step 4: Executar o teste verde e a regressão da vertical**

```powershell
pytest framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py -q
```

Expected: PASS sem exceções e com o status deliberadamente `needs_review`.

- [ ] **Step 5: Commit**

```powershell
git add framework/galpao_fw/residencial_eletrica.py projects/casa-residencial-eletrica-sintetica/project-spec.json framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py framework/galpao_fw/tests/branches/phase6a/test_residential_circuit_sizing.py
git commit -m "feat: integrate residential circuit sizing in loop"
```

### Task 4: Conectar o golden journey, documentação e verificação final

**Files:**
- Modify: `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`
- Modify: `projects/casa-residencial-eletrica-sintetica/README.md`
- Modify: `docs/superpowers/specs/2026-08-16-fase-6a-dimensionamento-eletrico-residencial.md`
- Modify: `docs/superpowers/plans/2026-08-16-dimensionamento-eletrico-residencial.md`

- [ ] **Step 1: Anexar o branch ao trunk**

O golden journey deve carregar `projects/casa-residencial-eletrica-sintetica/project-spec.json`, executar o Loop com `--no-ifc` equivalente, verificar `needs_review`, `verify_project_run(...)["ok"] is True`, três designs e os campos de escopo.

- [ ] **Step 2: Atualizar o README do fixture**

Documentar que `circuits.designs` é obrigatório para o cálculo, que
`short_circuit` ausente significa `not_evaluated`, que o caso coordenado sob
agrupamento 3 publica base 6 mm² / final 10 mm² sem perder a primeira
passagem, e que não há entrega CAD/BIM nesta fase.

- [ ] **Step 3: Rodar a verificação completa**

```powershell
pytest framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py framework/galpao_fw/tests/branches/phase6a -q
python -m compileall -q framework/galpao_fw
```

Expected: todos os testes selecionados passam, o trunk passa e o compileall termina com código 0.

- [ ] **Step 4: Commit**

```powershell
git add framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py projects/casa-residencial-eletrica-sintetica/README.md docs/superpowers/specs/2026-08-16-fase-6a-dimensionamento-eletrico-residencial.md docs/superpowers/plans/2026-08-16-dimensionamento-eletrico-residencial.md
git commit -m "docs: close phase 6a residential electrical scope"
```

## Self-review do plano

- Cobertura: contrato, cálculo genérico, proteção, curto ausente, integração, fixture persistido, trunk e regressão estão distribuídos nas quatro tarefas.
- Antiobjetivos: IFC/CAD, aprovação Enel e defaults aparecem explicitamente como proibidos.
- Consistência: o nome público é `calculate_residential_circuit_designs`; `circuits.designs` é a única nova entrada; `scope` usa os seis estados definidos na especificação.
- Próxima fase: Fase 6B começa a partir dos resultados JSON validados para unifilar, 2D e IFC, sem misturar geração gráfica ao cálculo.

## Fase 6B — FECHADA (2026-08-29)

Entregue em `docs/superpowers/specs/2026-08-29-fase-6b-entregaveis-eletrica-residencial.md`:
o adaptador passou a declarar `deliverables=("report", "drawings", "ifc")` e emite
unifilar, quadro de cargas, planta 2D e IFC4 a partir do mesmo JSON já validado.
A geração gráfica não calcula nada. A geometria entra por `circuits.layout`
(opcional, sem default); sem ela o escopo fica `schematic_only` e a planta/IFC
não são inventados.

### Achado do render-and-look sobre a prancha entregue (2026-08-29)

Abrir o quadro de cargas renderizado — não a barra verde — mostrou a coluna
`GOVERN.` dizendo **ampacidade** para o circuito de iluminação de 0,79 A em
2,5 mm² (Iz = 24 A). Rótulo × cálculo: ampacidade não governa nada ali.

Causa em `condutores_nbr5410.py`: a `SECAO_MINIMA` da NBR 5410 Tab.47 para
iluminação é 1,5 mm², mas a tabela de ampacidade deste projeto começa em
2,5 mm²; o mínimo normativo era substituído em silêncio pelo piso da tabela
(`s_min if s_min in SECOES else min(SECOES)`) e o resultado ainda se rotulava
`ampacidade`. É o espelho da saturação silenciosa: em vez de saturar no maior
valor tabelado, satura no **menor** — e o `OK=True` esconde os dois números.

Fechado: o resultado passa a expor `secao_minima_norma` (o valor da norma) e
`piso_tabela`; `governante` vira `piso_tabela` quando a seção adotada é o piso
e nenhum critério real pediu mais, ou `secao_minima` quando o mínimo da norma é
representável na tabela (força, 2,5 mm²). A prancha escreve
"piso da tabela (norma 1,5 mm²)" e "seção mínima (Tab.47)".

Aberto (dado, não código): a tabela de ampacidade não tem a linha de 1,5 mm²
das Tab.36-39. Enquanto não for lida da norma, circuitos de iluminação saem em
2,5 mm² — conservador, e agora declarado como tal em vez de disfarçado.

Um segundo defeito só visível no render: o rótulo novo transbordava a coluna e
colidia com a coluna DR. Colisão de texto não é XML malformado — o parser
aceita. A suíte ganhou um teste geométrico que compara a largura estimada de
cada texto com o início da coluna seguinte.
