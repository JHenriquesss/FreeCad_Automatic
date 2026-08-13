# Calhas Declividade Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validar entradas hidráulicas de calhas contra a NBR 10844:1989 e eliminar crash/NaN causado por declividade inválida.

**Architecture:** `calhas.py` mantém suas funções puras e sua API, centralizando apenas validações internas reutilizáveis na fronteira. Os testes existentes de robustez permanecem o contrato de regressão, com casos explícitos para a fronteira normativa e valores não finitos.

**Tech Stack:** Python 3.12, `math`, `pytest` e os módulos hidráulicos existentes.

## Global Constraints

- A declividade mínima é exatamente `0.005 m/m`.
- O erro deve ocorrer antes de `i ** 0.5` para nunca produzir número complexo.
- A fórmula de Manning e o formato de retorno não serão alterados.
- Toda entrada pública nova deve ter teste RED/GREEN e nenhuma regra normativa pode ficar sem o source ID documentado na especificação.

---

### Task 1: contrato RED de entradas hidráulicas

**Files:**
- Modify: `framework/galpao_fw/tests/test_calhas_robustez.py`

**Interfaces:**
- Consumes: `calhas.secao_calha`, `calhas.dimensiona`, `calhas.area_contribuicao`, `calhas.vazao_projeto` e `calhas.diametro_condutor`.
- Produces: testes que falham antes da implementação e cobrem a fronteira normativa.

- [ ] **Step 1: Add failing tests**

Manter o parâmetro existente de `inclinacao` e adicionar casos explícitos para
entradas não finitas/negativas nas outras funções, por exemplo:

```python
@pytest.mark.parametrize("inclinacao", [0.0, 0.004, -0.01, float("nan"), float("inf")])
def test_declividade_calha_nbr_10844_falha_explicitamente(inclinacao):
    with pytest.raises(ValueError, match="declividade"):
        calhas.secao_calha(500.0, B_base=0.40, i=inclinacao, H_max=0.30)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_entradas_nao_finitas_falham_sem_crash(bad):
    chamadas = (
        lambda: calhas.vazao_projeto(bad),
        lambda: calhas.secao_calha(100.0, B_base=bad),
        lambda: calhas.diametro_condutor(100.0, n_condutores=bad),
    )
    for chamada in chamadas:
        with pytest.raises(ValueError):
            chamada()
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest framework/galpao_fw/tests/test_calhas_robustez.py -q`

Expected: falha nos casos de declividade e nos novos casos de entradas não
finitas, sem editar produção antes dessa confirmação.

### Task 2: validação mínima na implementação

**Files:**
- Modify: `framework/galpao_fw/calhas.py`
- Test: `framework/galpao_fw/tests/test_calhas_robustez.py`

**Interfaces:**
- Consumes: os valores de entrada das funções públicas existentes.
- Produces: `ValueError` precoce para entradas inválidas e resultados finitos para entradas válidas.

- [ ] **Step 1: Implement helpers internos**

Adicionar `_exigir_finito`, `_exigir_nao_negativo` e `_exigir_positivo` usando
`math.isfinite` com tratamento de `TypeError`, `ValueError` e `OverflowError`.

- [ ] **Step 2: Apply the helpers**

Aplicar as guardas em `area_contribuicao`, `vazao_projeto`, `secao_calha`,
`diametro_condutor` e `dimensiona`. Em `secao_calha`, validar primeiro:

```python
i = _exigir_finito("declividade", i)
if i < 0.005:
    raise ValueError("declividade da calha deve ser >= 0,005 m/m")
```

Validar também `Q_calc`, área total da seção, volume e peso derivados antes de
retorná-los.

- [ ] **Step 3: Run GREEN**

Run: `python -m pytest framework/galpao_fw/tests/test_calhas_robustez.py -q`

Expected: todos os testes de robustez passam.

### Task 3: regressão hidráulica e revisão

**Files:**
- Modify: `sessions/2026-08-13.md`
- Modify: `.superpowers/sdd/progress.md`

- [ ] **Step 1: Run focused regression**

```powershell
python -m pytest framework/galpao_fw/tests/test_calhas_robustez.py framework/galpao_fw/tests/test_hidraulica_predial.py -q
python -m pytest framework/galpao_fw/tests/test_calha_calc_3d.py framework/galpao_fw/tests/test_fase6a_calha_divisa.py -q
python -m py_compile framework/galpao_fw/calhas.py
git diff --check
```

- [ ] **Step 2: Record evidence**

Registrar contagens reais, a fonte NBR 10844 e qualquer falha fora do escopo;
não marcar a fase como fechada sem os comandos acima passarem.

- [ ] **Step 3: Commit**

```powershell
git add framework/galpao_fw/calhas.py framework/galpao_fw/tests/test_calhas_robustez.py
git commit -m "fix: validate gutter slope inputs"
```
