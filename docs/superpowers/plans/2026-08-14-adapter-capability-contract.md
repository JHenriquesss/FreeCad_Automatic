# Adapter capability contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer com que adaptadores de outros tipos de obra possam executar disciplinas próprias sem atravessar caminhos específicos do galpão, declarando capacidades e hooks opcionais.

**Architecture:** O registry manterá runners, metadados e hooks em mapas separados para preservar compatibilidade. O Loop consultará hooks do adaptador antes de chamar qualquer helper turnkey; o adaptador nativo registrará os hooks existentes e o comportamento atual permanecerá inalterado.

**Tech Stack:** Python 3.11+, dataclasses/JSON existentes, pytest, `project_loop`.

## Global Constraints

- Não inventar calculadores de arquitetura, casas ou edifícios nesta fase.
- Não alterar o contrato antigo `register_adapter(name, runner)`.
- Adaptador externo sem hook deve resultar em `not_available`/`needs_review`, nunca em sucesso silencioso.
- `galpao_turnkey` só pode ser chamado pelo adaptador `galpao`.
- Capacidades persistidas devem ser JSON-safe e não conter callables.
- Preservar specs, manifestos e testes existentes; não usar reset/checkout/commit abrangente.

---

### Task 1: Registry de capacidades e preflight extensível

**Files:**
- Modify: `framework/galpao_fw/project_loop.py`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py`

**Interfaces:**
- `register_adapter(name, runner, *, project_types=(), disciplines=(), deliverables=(), hooks=None)` mantém o runner antigo.
- `describe_adapters(name=None) -> list[dict]` retorna metadados sem funções.
- `adapter_capabilities` entra no preflight e no manifesto.

- [ ] **Step 1: Escrever testes RED para capacidades e disciplina externa**

```python
def test_registered_external_adapter_accepts_its_discipline_without_galpao_calls(tmp_path):
    def runner(normalized, run_dir):
        return {"disciplinas": {"arquitetura": {"rodou": True}}}, {
            "arquitetura": {"status": "passed", "native_atende": True,
                             "reprovados": [], "gates": {}, "warnings": [],
                             "errors": [], "artifacts": []},
        }
    register_adapter("teste-arquitetura", runner,
                     project_types=("residencial",),
                     disciplines=("arquitetura",),
                     deliverables=("ifc",))
    result = run_project(
        {"adapter": "teste-arquitetura",
         "project": {"slug": "casa-teste"},
         "geometria": {"comprimento": 10, "vao": 8, "pe_direito": 3},
         "arquitetura": {"programa": "pendente"}},
        tmp_path, options={"generate_ifc": False},
    )
    assert result["status"] == "needs_review"
    assert result["disciplines"]["arquitetura"]["status"] == "passed"
    assert result["preflight"]["adapter_capabilities"]["disciplines"] == ["arquitetura"]
    assert result["coordination"]["status"] == "not_available"


def test_unknown_adapter_lists_registered_capabilities(tmp_path):
    result = run_project({"adapter": "nao-existe",
                          "geometria": {"comprimento": 10, "vao": 8,
                                         "pe_direito": 3}}, tmp_path)
    error = next(item for item in result["preflight"]["errors"]
                 if item["code"] == "unsupported_adapter")
    assert "galpao" in error["supported_adapters"]
```

- [ ] **Step 2: Executar e confirmar RED**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py`

Expected: API de capacidades ausente ou adaptador externo bloqueado como desconhecido.

- [ ] **Step 3: Implementar registry/metadados e preflight**

Adicionar mapas privados para capacidades/hooks, normalizar sequências de strings, incluir disciplinas declaradas do adaptador no conjunto permitido e persistir `adapter_capabilities`. Não expor os hooks em JSON.

- [ ] **Step 4: Executar testes focados**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py`

Expected: testes de capacidades passam.

### Task 2: Hooks de execução e estados honestos

**Files:**
- Modify: `framework/galpao_fw/project_loop.py`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py`

**Interfaces:**
- Hooks recebem `(manifest, run_dir, normalized, options, adapter_result)`.
- Sem hook, relatório genérico vira `reports/adapter-result.json`; coordenação e entregáveis solicitados viram `not_available`.

- [ ] **Step 1: Acrescentar asserções RED ao teste externo**

Verificar `reports/adapter-result.json`, `deliverables.ifc.status == "not_requested"` quando `generate_ifc=False`, ausência de artefatos turnkey e `coordination.status == "not_available"`.

- [ ] **Step 2: Executar o teste e confirmar a falha**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py::test_registered_external_adapter_accepts_its_discipline_without_galpao_calls`

Expected: o pipeline atual tenta relatório/coordenação turnkey e não registra o estado externo.

- [ ] **Step 3: Encaminhar somente pelos hooks registrados**

Registrar os hooks atuais do `galpao`; no executor, usar hook quando presente e marcar ausência explicitamente quando não houver. Incluir `reports/adapter-result.json` no ledger padrão.

- [ ] **Step 4: Executar testes focados**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py`

Expected: adaptador externo passa com `needs_review` honesto.

### Task 3: Integrar o adaptador galpão, documentação e regressão

**Files:**
- Modify: `framework/galpao_fw/project_loop.py`
- Modify: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_contract.py`
- Modify: `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`
- Modify: `framework/galpao_fw/COMO-RODAR.md`
- Modify: `docs/superpowers/specs/2026-08-14-project-loop-design.md`

**Interfaces:**
- `describe_adapters()` lista `galpao` com tipos `galpao`/`industrial`, seis disciplinas e entregáveis existentes.
- A jornada trunk mantém IFC/coordenação/iteração sem mudança de comportamento.

- [ ] **Step 1: Verificar registro nativo e documentação**

Adicionar asserções de capacidades do galpão e documentar como registrar um novo adaptador sem prometer cálculo ainda inexistente.

- [ ] **Step 2: Executar jornada e regressão afetada**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`

Run: `python -m pytest -q framework/galpao_fw/tests/test_turnkey.py framework/galpao_fw/tests/test_turnkey_bim.py framework/galpao_fw/tests/test_turnkey_clash.py framework/galpao_fw/tests/test_caderno_turnkey.py framework/galpao_fw/tests/test_pipeline_bim.py framework/galpao_fw/tests/test_validacao.py framework/galpao_fw/tests/test_relatorio_x_calculo.py -m "not build"`

- [ ] **Step 3: Verificar sintaxe e higiene**

Run: `python -m compileall -q framework/galpao_fw/project_loop.py` e `git diff --check`.

Expected: adaptador galpão permanece verde; extensão externa é explicitamente auditável.

## Plan self-review

- O plano não cria calculador novo; cobre apenas registry, dispatch e estados.
- Compatibilidade antiga é mantida por argumentos opcionais.
- O teste externo usa um runner registrado e verifica o manifesto final, não funções privadas de coordenação.

## Evidência executada

- Adapter contract: 5 testes aprovados.
- Branches do Loop + trunk após integração: 28 testes aprovados.
- Regressão turnkey/BIM/clash/validação: 76 aprovados, 1 desmarcado.
- `compileall` e `git diff --check`: aprovados.
