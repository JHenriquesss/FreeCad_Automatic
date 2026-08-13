# Validador FV de Strings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax for tracking.

**Goal:** Transformar a evidência auditada da NBR 16690/NBR 16149 em um validador puro de compatibilidade elétrica de strings FV e em uma unidade atômica do loop.

**Architecture:** fotovoltaico.py receberá uma função pura que calcula limites CC e devolve falhas estruturadas; as fórmulas existentes de área e geração permanecerão intactas. discovery.py criará uma tarefa FV com source_paths explícitos, mantendo a pendência ampla de ANEEL/distribuidora separada.

**Tech Stack:** Python 3.12, math.isfinite, pytest, NotebookLM CLI e scheduler existente.

## Global Constraints

- Usar somente citações auditáveis da ABNT NBR 16690:2019 (source ID 1d06923f-04d7-4b39-afbd-da6ab91567a9) e da ABNT NBR 16149:2013 (source ID 7f85f8f0-9ff2-492a-9188-bf345529f2b6).
- Não inventar fator de temperatura, catálogo de módulo/inversor, HSP, regra de distribuidora ou valor da ANEEL.
- Toda entrada numérica deve ser finita; bool não é número válido.
- A função não lança exceções para entrada de projeto inválida: retorna ok=False e falhas estáveis.
- Não alterar dimensiona_fv, as fórmulas de geração existentes ou fontes locais.
- O estado operacional do scheduler permanece em .loop-runtime.

---

## Phase 19 plan

### Scope

Entregar validar_compatibilidade_arranjo_fv(caso) em
framework/galpao_fw/fotovoltaico.py, testes unitários reais no módulo FV e uma
unidade de descoberta com as duas fontes normativas locais.

### Entry condition

- NotebookLM autenticado com nlm login --check.
- Fontes NBR 16690 e NBR 16149 presentes nos caminhos declarados.
- Suíte FV existente verde antes da alteração.
- Especificação da fase revisada.

### Exit condition

- A função valida tensão, corrente, componentes, proteção de arranjo, proteção de séries e conectores conforme o contrato.
- A descoberta produz o candidato FV atômico antes da pendência ampla e declara exatamente as duas fontes.
- Testes focados, suíte de loops, suíte FV, compilação e git diff --check passam.
- Um ciclo supervisionado real registra evidência ou estaciona de forma auditável.
- Revisão do diff aprovada e sessão registrada.

### Must-exist checklist

- [x] Descoberta confirma tópico, disciplina, prioridade, testes e os dois source_paths.
- [x] Caso positivo confirma VOC_ARRANJO, V_MAX_ARRANJO, ISC_ARRANJO, corrente mínima e componentes.
- [x] Casos negativos cobrem entradas ausentes, não finitas, tensão/corrente insuficientes e componente não CC.
- [x] Proteção de arranjo, proteção individual e proteção agrupada são testadas com desigualdades estritas.
- [x] Conectores iguais passam e fabricante/tipo diferentes falham.
- [x] Retorno contém ok, falhas, avisos, valores_calculados e referencias.
- [x] A pendência ampla de vigência continua descoberta separadamente.

### Must-not-exist checklist

- [x] Nenhuma regra de seccionamento, aterramento, anti-ilhamento ou distribuidora é implementada.
- [x] Nenhum fator de correção ou valor de catálogo é criado por default.
- [x] Nenhuma exceção ValueError, KeyError, TypeError, NaN ou inf escapa do validador.
- [x] Nenhum teste é marcado como skip ou depende de mock do validador.
- [x] Nenhuma fonte remota é baixada, substituída ou apagada.
- [x] A tarefa ampla sem source_paths não é promovida pelo candidato FV atômico.

### Test plan

#### Positive

- Caso de uma série com fator_correcao_tensao=1.10 e componente CC compatível retorna ok=True.
- Caso equivalente com v_max_arranjo_v direto produz os mesmos valores.
- Proteção individual válida é aceita.
- Proteção agrupada válida é aceita.
- Conectores do mesmo fabricante e tipo são aceitos.

#### Negative

- Fator e tensão máxima simultâneos, ou ambos ausentes, retornam TENSAO_MAXIMA_AMBIGUA.
- Campos numéricos ausentes, booleanos, infinitos, NaN, zero ou negativos retornam falhas sem exceção.
- Tensão ou corrente nominal abaixo do limite retorna código específico.
- Componente não CC, proteção ausente, tipo não autorizado e faixas inválidas retornam códigos específicos.
- Conectores de fabricante ou tipo diferentes falham.

### Test tree integration

- Trunk touch point: fluxo existente de dimensionamento FV em framework/galpao_fw/tests/test_fotovoltaico.py.
- New branches: descoberta do candidato; limites CC; proteção de séries; conectores; entradas inválidas.

### Next phase seed

Fase 20 deve tratar seccionamento/isolação da UCP ou documentação/comissionamento pela NBR 16274, após nova consulta auditável.

---

### Task 1: Candidato FV atômico na descoberta

**Files:**
- Modify: tools/loops/discovery.py
- Test: tools/loops/tests/test_discovery.py

**Interfaces:**
- Consumes: item amplo de fontes/pendencias-atualizacao.md sobre vigência FV.
- Produces: TaskCandidate com topic=fotovoltaico, discipline=eletrica, dois caminhos de fonte e teste FV.

- [x] Step 1: Write the failing test

Adicionar testes que localizem topic == fotovoltaico, confirmem os dois caminhos
exatos, test_fotovoltaico.py nos testes e posição anterior ao candidato amplo.

- [x] Step 2: Run test to verify it fails

    python -m pytest tools/loops/tests/test_discovery.py -k fotovoltaico -q

Expected: FAIL porque a descoberta atual só produz a pendência ampla sem tópico FV.

- [x] Step 3: Write minimal implementation

Adicionar constante de caminhos FV e ramo específico em _candidates_for_item()
para gerar o candidato atômico e preservar o candidato amplo. Adicionar termos
de teste para selecionar test_fotovoltaico.py.

- [x] Step 4: Run test to verify it passes

    python -m pytest tools/loops/tests/test_discovery.py -k fotovoltaico -q

- [x] Step 5: Commit

    git add tools/loops/discovery.py tools/loops/tests/test_discovery.py
    git commit -m "feat: discover atomic photovoltaic validation task"

### Task 2: Limites de tensão, corrente e componentes

**Files:**
- Modify: framework/galpao_fw/fotovoltaico.py
- Test: framework/galpao_fw/tests/test_fotovoltaico.py

**Interfaces:**
- Consumes: voc_modulo_v, modulos_serie, isc_modulo_a, series_paralelo, fator ou tensão máxima direta e componentes_cc.
- Produces: validar_compatibilidade_arranjo_fv(caso) -> dict com cálculos e falhas.

- [x] Step 1: Write the failing test

Adicionar caso-base:

    caso = {
        "voc_modulo_v": 49.5,
        "modulos_serie": 20,
        "isc_modulo_a": 13.2,
        "series_paralelo": 1,
        "fator_correcao_tensao": 1.10,
        "componentes_cc": [{
            "nome": "inversor",
            "tensao_nominal_v": 1200.0,
            "corrente_nominal_a": 20.0,
            "adequado_cc": True,
        }],
        "usa_conectores": False,
    }
    resultado = fv.validar_compatibilidade_arranjo_fv(caso)
    assert resultado["ok"] is True
    assert resultado["valores_calculados"]["voc_arranjo_v"] == 990.0
    assert resultado["valores_calculados"]["v_max_arranjo_v"] == 1089.0
    assert resultado["valores_calculados"]["isc_arranjo_a"] == 13.2
    assert resultado["valores_calculados"]["corrente_minima_arranjo_a"] == 16.5

Adicionar casos de tensão direta equivalente, componente CC inadequado, tensão
insuficiente, corrente insuficiente, número não finito e tensão máxima ambígua.

- [x] Step 2: Run test to verify it fails

    python -m pytest framework/galpao_fw/tests/test_fotovoltaico.py -k compatibilidade -q

Expected: FAIL porque a função ainda não existe.

- [x] Step 3: Write minimal implementation

Implementar somente contrato de entrada, cálculos e validação de componentes_cc.
Usar math.isfinite, rejeitar bool, acumular falhas e retornar o dicionário estável
sem alterar as funções existentes.

- [x] Step 4: Run test to verify it passes

    python -m pytest framework/galpao_fw/tests/test_fotovoltaico.py -k compatibilidade -q

- [x] Step 5: Commit

    git add framework/galpao_fw/fotovoltaico.py framework/galpao_fw/tests/test_fotovoltaico.py
    git commit -m "feat: validate photovoltaic dc limits"

### Task 3: Proteções e conectores

**Files:**
- Modify: framework/galpao_fw/fotovoltaico.py
- Test: framework/galpao_fw/tests/test_fotovoltaico.py

**Interfaces:**
- Consumes: cálculos da Task 2 e protecao_arranjo, imod_max_ocpr_a, protecao_series e conectores.
- Produces: validação normativa de proteção e compatibilidade de conectores.

- [x] Step 1: Write the failing test

Adicionar casos com series_paralelo=3, isc_modulo_a=13.2 e
imod_max_ocpr_a=25.0. Sem proteção de séries deve falhar porque
(3 - 1) × 13.2 > 25. Proteção individual válida deve satisfazer
1,5 × Isc < In < 2,4 × Isc e In <= ImodMaxOCPR. Proteção agrupada deve
ser validada pelas duas desigualdades de grupo. Adicionar tipo não autorizado,
proteção ausente, conectores iguais, fabricante diferente, tipo diferente e
par macho/fêmea ausente.

- [x] Step 2: Run test to verify it fails

    python -m pytest framework/galpao_fw/tests/test_fotovoltaico.py -k protecao -q

Expected: FAIL porque a função ainda não trata proteção nem conectores.

- [x] Step 3: Write minimal implementation

Implementar as desigualdades estritas de 5.3.9/5.3.11.1, validar tipos
autorizados, separar protecao_arranjo de protecao_series, usar a proteção do
arranjo como referência da Tabela 5 e validar fabricante/tipo dos conectores.
Não implementar seccionamento ou interface CA.

- [x] Step 4: Run test to verify it passes

    python -m pytest framework/galpao_fw/tests/test_fotovoltaico.py -k protecao -q

- [x] Step 5: Commit

    git add framework/galpao_fw/fotovoltaico.py framework/galpao_fw/tests/test_fotovoltaico.py
    git commit -m "feat: validate photovoltaic protection and connectors"

### Task 4: Verificação, documentação operacional e ciclo real

**Files:**
- Modify: tools/README.md only if an operator note is needed.
- Modify: .superpowers/sdd/progress.md and sessions/2026-08-13.md.
- Test: tools/loops/tests and framework/galpao_fw/tests/test_fotovoltaico.py.

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: evidência de suíte, compilação, consulta NotebookLM e execução supervisionada.

- [x] Step 1: Write the failing test

Não há novo comportamento; os testes das Tasks 1–3 são o contrato executável.

- [x] Step 2: Run test to verify it passes

    python -m pytest tools/loops/tests -q
    python -m pytest framework/galpao_fw/tests/test_fotovoltaico.py -q

- [x] Step 3: Write minimal implementation

Adicionar somente documentação operacional necessária e registrar IDs das fontes,
resultado RED/GREEN, revisão e qualquer estacionamento do scheduler.

- [x] Step 4: Run test to verify it passes

    python -m pytest tools/loops/tests -q
    python -m pytest framework/galpao_fw/tests/test_fotovoltaico.py -q
    python -m py_compile tools/loops/*.py
    git diff --check
    nlm login --check

No Windows, enumerar os arquivos Python para compilação em vez de depender da
expansão de glob do PowerShell.

- [x] Step 5: Commit

    git add tools/README.md
    git commit -m "docs: record photovoltaic validation cycle"
