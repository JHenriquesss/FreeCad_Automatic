# Elétrica residencial BT/Enel — Implementation Plan

> **Status final (2026-08-16):** concluído. A vertical foi implementada,
> endurecida e verificada em checkout limpo. O resultado operacional permanece
> `needs_review` por desenho: dimensionamento executivo, desenhos 2D/BIM e
> aprovação da concessionária continuam fora desta fase.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** adicionar ao framework uma primeira vertical elétrica residencial BT/Enel, determinística e auditável, sem acoplar o núcleo a regras do galpão.

**Architecture:** dois calculadores puros (`demanda_residencial_enel.py` e `entrada_enel_bt.py`) recebem apenas JSON e devolvem resultados estruturados com erros, avisos e referências. Um runner `residencial_eletrica.py` valida o contrato de circuitos, exige as fontes normativas mínimas e compõe o relatório da disciplina; o registro do adaptador e a fixture persistida usam o mesmo `run_project_file()` universal já usado pelo galpão.

**Tech Stack:** Python 3.12, pytest, JSON versionado, `project_loop.py`, `project_io.py`, `project_source_gate.py`, fontes locais e snapshot do NotebookLM elétrico.

## Global Constraints

- Não importar `galpao_eletrico`, `galpao_hidraulica`, `galpao_turnkey` ou qualquer geometria industrial na vertical residencial.
- Não consultar o NotebookLM dentro do cálculo; a revalidação viva permanece no `project_source_gate.py`/readiness.
- Não inventar fator de localização, tensão, tipo de fornecimento, carga instalada, pontos ou parâmetros de dimensionamento.
- `loads.installed_load_kw` é obrigatório para selecionar a linha Enel; não substituir esse valor pela demanda calculada.
- Cada ponto de circuito deve declarar `id`, `room`, `kind`, `power_va` e `voltage_v`.
- O resultado residencial desta fase nunca emite `passed`; o máximo é `needs_review` com premissas explícitas.
- Não gerar IFC, FCStd, PDF, SVG ou DXF nesta fase.
- Manter intactos arquivos modificados ou não rastreados que não pertençam a esta vertical; adicionar arquivos e fazer commits somente dos caminhos da tarefa corrente.
- Fontes mínimas do cálculo: NBR 5410 `d213019d-6e5c-4f18-8151-bf5a74c11b5d`, Enel BT R02/2025 `5129118d-2ff6-4187-a9d2-d1828d61afdf` e WKI demanda BT `5bc6c2f1-c8b8-4a04-8b82-be0e937b4749`; PRODIST `4c71daf6-ff91-44d1-a5e7-d7f881ab66f8` é contexto e pode acompanhar o spec.
- O notebook elétrico de referência é `78cd2efd-0652-484e-b312-c5c5a7648962`, com no máximo 50 fontes.

## Mapa de arquivos

- Criar `framework/galpao_fw/demanda_residencial_enel.py`: módulos de cômodos, fatores, aquecimento, iluminação especial e composição `a + maior(b,c,d) + 0,70 * restantes`.
- Criar `framework/galpao_fw/entrada_enel_bt.py`: tabelas dos Anexos A e C da Enel Rio e seleção por tensão, tipo e carga instalada.
- Criar `framework/galpao_fw/residencial_eletrica.py`: runner da disciplina elétrica, fontes obrigatórias, validação de circuitos e relatório JSON.
- Modificar `framework/galpao_fw/builtin_adapters.py`: registrar `casa-residencial-eletrica` depois dos adaptadores existentes, sem alterar o adaptador sintético.
- Criar `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_demand.py`.
- Criar `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py`.
- Criar `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py`.
- Criar `projects/casa-residencial-eletrica-sintetica/project-spec.json` e `projects/casa-residencial-eletrica-sintetica/README.md`.
- Modificar `framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py` somente para cobrir a fixture real elétrica, se a extensão não puder ficar no novo teste.
- Modificar `framework/galpao_fw/COMO-RODAR.md` com o comando de readiness e execução da fixture.
- Atualizar `.superpowers/sdd/progress.md` e `sessions/2026-08-15.md` a cada marco concluído.

---

### Task 1: Especificar os contratos puros em testes RED

**Files:**
- Create: `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_demand.py`
- Create: `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py`
- Create: `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py`

**Interfaces:**
- `calculate_residential_demand(payload: dict) -> dict` deve devolver `ok`, `errors`, `warnings` e `calculation`.
- `select_enel_bt_entry(*, voltage_system: str, supply_type: str, installed_load_kw: float) -> dict` deve devolver `ok`, `errors`, `warnings` e `entry`.
- `run_residential_electrical(normalized: dict, run_dir: pathlib.Path, preflight: dict | None = None) -> tuple[dict, dict]` deve seguir o contrato do `register_adapter`.

- [ ] **Step 1: Escrever os testes de demanda antes dos módulos de produção**

Adicionar estes comportamentos ao arquivo de demanda:

```python
import pytest

from demanda_residencial_enel import calculate_residential_demand


def _payload(**overrides):
    value = {
        "network": {"location_factor": 1.0},
        "rooms": {
            "quarto": 2, "sala": 1, "banheiro": 1,
            "cozinha": 1, "area_servico": 1, "outros": 0,
        },
        "loads": {"installed_load_kw": 7.5, "heating": [],
                  "motors": [], "special_lighting": []},
    }
    value.update(overrides)
    return value


def test_room_modules_use_kitchen_one_for_up_to_two_bedrooms():
    result = calculate_residential_demand(_payload())
    assert result["ok"] is True
    assert result["calculation"]["rooms"]["kitchen_module"] == 1.50
    assert result["calculation"]["rooms"]["subtotal_kva"] == pytest.approx(10.30)
    assert result["calculation"]["rooms"]["diversity_divisor"] == pytest.approx(1.20)
    assert result["calculation"]["demand"]["rooms_kva"] == pytest.approx(10.30 / 1.20)


def test_three_bedrooms_use_kitchen_two():
    payload = _payload()
    payload["rooms"]["quarto"] = 3
    result = calculate_residential_demand(payload)
    assert result["ok"] is True
    assert result["calculation"]["rooms"]["kitchen_module"] == 2.10


def test_one_bedroom_uses_divisor_1_4():
    payload = _payload()
    payload["rooms"]["quarto"] = 1
    result = calculate_residential_demand(payload)
    assert result["calculation"]["rooms"]["diversity_divisor"] == pytest.approx(1.40)


def test_location_factor_is_applied_and_never_defaulted():
    payload = _payload()
    payload["network"]["location_factor"] = 0.88
    result = calculate_residential_demand(payload)
    assert result["calculation"]["location_factor"] == pytest.approx(0.88)
    assert result["calculation"]["demand"]["final_kva"] == pytest.approx(
        (10.30 / 1.20) * 0.88
    )

    missing = _payload()
    del missing["network"]["location_factor"]
    blocked = calculate_residential_demand(missing)
    assert blocked["ok"] is False
    assert any(error["code"] == "missing_location_factor"
               for error in blocked["errors"])


def test_heating_table_uses_power_band_and_quantity():
    payload = _payload()
    payload["loads"]["heating"] = [{"quantity": 2, "power_kw": 4.0}]
    result = calculate_residential_demand(payload)
    heating = result["calculation"]["heating"]
    assert heating["items"][0]["factor_percent"] == pytest.approx(65.0)
    assert heating["demand_kw"] == pytest.approx(2 * 4.0 * 0.65)


def test_final_demand_combines_a_major_group_and_remaining_groups():
    payload = _payload()
    payload["loads"]["special_lighting"] = [{"power_kw": 4.0, "factor": 1.0}]
    payload["loads"]["heating"] = [{"quantity": 2, "power_kw": 4.0}]
    payload["loads"]["motors"] = [{"quantity": 1, "power_cv": 1.0,
                                      "connection": "trifasica"}]
    result = calculate_residential_demand(payload)
    demand = result["calculation"]["demand"]
    assert demand["a"] == pytest.approx(10.30 / 1.20)
    assert demand["final_kva"] == pytest.approx(
        demand["a"] + max(demand["b"], demand["c"], demand["d"])
        + 0.70 * (sum((demand["b"], demand["c"], demand["d"]))
                  - max(demand["b"], demand["c"], demand["d"]))
    )


def test_unknown_room_count_and_out_of_table_motor_are_blocked():
    payload = _payload()
    payload["rooms"]["varanda"] = 1
    invalid_room = calculate_residential_demand(payload)
    assert invalid_room["ok"] is False
    assert any(error["code"] == "unknown_room"
               for error in invalid_room["errors"])

    motor_payload = _payload()
    motor_payload["loads"]["motors"] = [{"quantity": 1, "power_cv": 999,
                                           "connection": "trifasica"}]
    invalid_motor = calculate_residential_demand(motor_payload)
    assert invalid_motor["ok"] is False
    assert any(error["code"] == "motor_outside_table"
               for error in invalid_motor["errors"])
```

- [ ] **Step 2: Executar apenas os testes de demanda para confirmar RED**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_demand.py`

Expected: FAIL por `ModuleNotFoundError: demanda_residencial_enel`, sem erro de sintaxe no arquivo de teste.

- [ ] **Step 3: Escrever os testes RED da tabela Enel**

Adicionar ao arquivo de entrada:

```python
import pytest

from entrada_enel_bt import select_enel_bt_entry


def test_annex_a_selects_b1_for_127_220_and_7_5_kw():
    result = select_enel_bt_entry(
        voltage_system="127/220", supply_type="B", installed_load_kw=7.5
    )
    assert result["ok"] is True
    assert result["entry"]["row"] == "B1"
    assert result["entry"]["breaker_a"] == 50
    assert result["entry"]["reference"]["page"] == 72


def test_annex_a_requires_type_when_ranges_overlap():
    result = select_enel_bt_entry(
        voltage_system="127/220", supply_type=None, installed_load_kw=7.5
    )
    assert result["ok"] is False
    assert any(error["code"] == "missing_supply_type"
               for error in result["errors"])


def test_annex_a_selects_c3_without_silently_changing_type():
    result = select_enel_bt_entry(
        voltage_system="127/220", supply_type="C", installed_load_kw=20.0
    )
    assert result["ok"] is True
    assert result["entry"]["row"] == "C3"
    assert result["entry"]["point_of_connection"] == "poste"


def test_annex_c_selects_b1_for_120_240():
    result = select_enel_bt_entry(
        voltage_system="120/240", supply_type="B", installed_load_kw=10.0
    )
    assert result["ok"] is True
    assert result["entry"]["row"] == "B1"
    assert result["entry"]["breaker_a"] == 50
    assert result["entry"]["reference"]["page"] == 77


@pytest.mark.parametrize("voltage", ["220/380", "127", "120/208"])
def test_unsupported_voltage_is_blocked(voltage):
    result = select_enel_bt_entry(
        voltage_system=voltage, supply_type="B", installed_load_kw=7.5
    )
    assert result["ok"] is False
    assert any(error["code"] == "unsupported_voltage_system"
               for error in result["errors"])


def test_load_without_matching_row_is_blocked():
    result = select_enel_bt_entry(
        voltage_system="120/240", supply_type="B", installed_load_kw=20.0
    )
    assert result["ok"] is False
    assert any(error["code"] == "no_entry_table_row"
               for error in result["errors"])
```

- [ ] **Step 4: Executar os testes da tabela para confirmar RED**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py`

Expected: FAIL por `ModuleNotFoundError: entrada_enel_bt`.

- [ ] **Step 5: Escrever os testes RED do runner e do isolamento**

O arquivo de adapter deve usar um spec em memória com `schema_version=1`, geometria universal positiva e `turnkey.eletrico` contendo o payload aprovado. Deve verificar:

```python
def test_real_residential_adapter_is_registered_with_only_electrical_capability():
    capabilities = [item for item in describe_adapters()
                    if item["name"] == "casa-residencial-eletrica"]
    assert capabilities
    assert capabilities[0]["project_types"] == ["residencial"]
    assert capabilities[0]["disciplines"] == ["eletrico"]
    assert capabilities[0]["deliverables"] == ["report"]


def test_residential_electrical_run_is_needs_review_and_traceable(tmp_path):
    result = run_project(_spec(), tmp_path, options={
        "generate_ifc": False, "require_source_refs": True,
    })
    assert result["adapter"] == "casa-residencial-eletrica"
    assert result["status"] == "needs_review"
    record = result["disciplines"]["eletrico"]
    assert record["status"] == "needs_review"
    assert record["calculation"]["demand"]["final_kva"] > 0
    assert record["service_entry"]["entry"]["row"] == "B1"
    assert (tmp_path / "reports" / "adapter-result.json").is_file()


def test_missing_required_electrical_source_blocks_discipline(tmp_path):
    spec = _spec()
    spec["source_refs"]["eletrico"] = [
        ref for ref in spec["source_refs"]["eletrico"]
        if ref["source_id"] != "5129118d-2ff6-4187-a9d2-d1828d61afdf"
    ]
    result = run_project(spec, tmp_path, options={"generate_ifc": False})
    assert result["status"] == "blocked"
    assert any(error["code"] == "missing_required_source"
               for error in result["disciplines"]["eletrico"]["errors"])


def test_invalid_circuit_point_blocks_without_heuristic_repair(tmp_path):
    spec = _spec()
    del spec["turnkey"]["eletrico"]["circuits"]["points"][0]["voltage_v"]
    result = run_project(spec, tmp_path, options={"generate_ifc": False})
    assert result["status"] == "blocked"
    assert any(error["code"] == "missing_circuit_voltage"
               for error in result["disciplines"]["eletrico"]["errors"])


def test_residential_electrical_path_does_not_import_galpao_modules(tmp_path):
    script = r'''
import builtins, json, sys
from pathlib import Path
root, spec_path, out_path = map(Path, sys.argv[1:])
sys.path.insert(0, str(root))
real_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name.split(".", 1)[0] in {
        "galpao_eletrico", "galpao_hidraulica", "galpao_turnkey",
    }:
        raise AssertionError(name)
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
from project_io import run_project_file
run_project_file(spec_path, out_path, options={"generate_ifc": False})
'''
    completed = subprocess.run(
        [sys.executable, "-c", script, str(ROOT), str(SPEC), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
```

The test helper `_spec()` must declare the four source records with the exact IDs listed in `Global Constraints`, `status: 2`, `is_stale: False`, `title` and `edition`, and use `supply_type="B"`, `installed_load_kw=7.5`.

- [ ] **Step 6: Executar o arquivo de adapter para confirmar RED**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py`

Expected: FAIL por ausência do runner/registro, sem modificar arquivos de produção.

- [ ] **Step 7: Registrar o ciclo RED**

Run: `git diff --check`.

Commit only the three new test files:

```text
test: definir contrato red da eletrica residencial
```

Record in `sessions/2026-08-15.md`: red count, expected missing modules/runner, and the next implementation task.

---

### Task 2: Implementar a demanda residencial Enel

**Files:**
- Create: `framework/galpao_fw/demanda_residencial_enel.py`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_demand.py`

**Interfaces:**
- Input: `turnkey.eletrico` with `network`, `rooms` and `loads`.
- Output: `{"ok": bool, "errors": list, "warnings": list, "calculation": dict}`.
- No import of `project_loop`, FreeCAD or any `galpao_*` module.

- [ ] **Step 1: Implementar somente os dados normativos e validadores exigidos pelos testes**

Use these exact constants and rules:

```python
ROOM_MODULES_KVA = {
    "quarto": 1.50,
    "sala": 1.60,
    "banheiro": 2.30,
    "cozinha_1": 1.50,
    "cozinha_2": 2.10,
    "area_servico": 1.90,
    "outros": 0.35,
}
LOCATION_FACTORS = (1.00, 0.88, 0.75, 0.55)

def calculate_residential_demand(payload):
    errors = _validate_payload(payload)
    if errors:
        return {"ok": False, "errors": errors, "warnings": [],
                "calculation": {}}
    rooms = _calculate_rooms(payload["rooms"],
                              payload["network"]["location_factor"])
    heating = _calculate_heating(payload["loads"]["heating"])
    motors = _calculate_motors(payload["loads"]["motors"])
    special = _calculate_special_lighting(payload["loads"]["special_lighting"])
    errors = motors.pop("errors", [])
    return _compose_result(rooms, heating, motors, special, errors)
```

The implementation must return the complete structure below for a valid payload:

```python
{
    "ok": True,
    "errors": [],
    "warnings": [],
    "calculation": {
        "location_factor": 1.0,
        "rooms": {
            "modules_kva": {"quarto": 3.0, "sala": 1.6,
                             "banheiro": 2.3, "cozinha": 1.5,
                             "area_servico": 1.9, "outros": 0.0},
            "kitchen_module": 1.5,
            "subtotal_kva": 10.3,
            "diversity_divisor": 1.2,
            "demand_kva": 8.583333333333334,
        },
        "heating": {"items": [], "installed_kw": 0.0, "demand_kw": 0.0},
        "special_lighting": {"items": [], "demand_kw": 0.0},
        "motors": {"items": [], "installed_kw": 0.0, "demand_kw": 0.0},
        "demand": {"a": 8.583333333333334, "b": 0.0, "c": 0.0,
                   "d": 0.0, "final_kva": 8.583333333333334},
    },
}
```

`a` is the room demand. `b`, `c` and `d` are, in order, heating, motors and special lighting; the output must preserve the mapping so a reviewer can audit the combination. For heating use the WKI Table 1 percentages by quantity and the `<= 3.5 kW`/`> 3.5 kW` bands. For a special lighting item require numeric `power_kw` and `factor`; for a motor require an exact supported `connection`, `power_cv` and quantity combination, otherwise append `motor_outside_table`.

- [ ] **Step 2: Run the focused demand tests GREEN**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_demand.py`

Expected: all demand tests pass.

- [ ] **Step 3: Run compile and whitespace checks**

Run: `python -m py_compile framework/galpao_fw/demanda_residencial_enel.py`

Run: `git diff --check`.

- [ ] **Step 4: Commit the demand slice**

```text
feat: calcular demanda residencial enel
```

Record the RED/GREEN counts and the WKI rules implemented in `sessions/2026-08-15.md`.

---

### Task 3: Implementar a seleção do padrão Enel BT

**Files:**
- Create: `framework/galpao_fw/entrada_enel_bt.py`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py`

**Interfaces:**
- `select_enel_bt_entry(*, voltage_system, supply_type, installed_load_kw) -> dict`.
- Return valid rows with `row`, `voltage_system`, `supply_type`, `load_range_kw`, `breaker_a`, conductor fields, `point_of_connection`, `metering`, and `reference`.
- Reject unsupported voltage, missing/invalid type, non-positive load, and a load with no row; never select a row from another type.

- [ ] **Step 1: Confirm the table tests are still RED after Task 2**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py`.

Expected: FAIL only because `entrada_enel_bt` is not present.

- [ ] **Step 2: Implementar as linhas dos Anexos A e C reproduzidas da fonte local**

Use a private immutable row table with these ranges and minimum fields:

```python
ANNEX_A_127_220 = (
    ("A1", "A", None, 5.0, 40, "1x10 (10)", "10 (10)", 10, 50, "medidor"),
    ("A2", "A", 5.0, 8.0, 63, "1x16 (10)", "16 (10)", 16, 50, "medidor"),
    ("B1", "B", 0.0, 11.0, 50, "2x10 (10)", "10 (10)", 10, 50, "medidor"),
    ("B2", "B", 11.0, 14.0, 63, "2x16 (10)", "16 (10)", 16, 60, "medidor"),
    ("C1", "C", 10.0, 15.0, 40, "3x10 (10)", "10 (10)", 10, 50, "medidor"),
    ("C2", "C", 15.0, 19.1, 50, "3x10 (10)", "10 (10)", None, 50, "medidor"),
    ("C3", "C", 19.1, 24.0, 63, "3x16 (16)", "25 (25)", 16, 60, "medidor"),
    ("C4", "C", 24.0, 30.0, 80, "3x35 (54.6)", None, None, 40, "poste"),
    ("C5", "C", 30.0, 38.0, 100, "3x35 (54.6)", "35 (25)", None, 40, "poste"),
    ("C6", "C", 38.0, 48.0, 125, "3x35 (54.6)", "50 (25)", 25, 50, "poste"),
    ("C7", "C", 48.0, 57.1, 150, "3x50 (54.6)", "70 (35)", 35, None, "poste"),
    ("C8", "C", 57.1, 67.0, 175, "3x50 (54.6)", "95 (50)", 50, None, "poste"),
    ("C9", "C", 67.0, 75.0, 200, "3x95 (54.6)", "95 (50)", 25, None, "poste"),
)

ANNEX_C_120_240 = (
    ("A1", "A", None, 5.0, 40, "1x10 (10)", "10 (10)", 10, 50, "medidor"),
    ("A2", "A", 5.0, 6.0, 50, "1x16 (16)", "16 (16)", 16, 50, "medidor"),
    ("B1", "B", 6.0, 12.0, 50, "2x16 (16)", "16 (16)", 16, 60, "medidor"),
)
```

Use strict lower/upper boundary semantics matching the source (`C <= max`, and the next range begins above the previous maximum). The public return must include `reference: {"document": "CNC-NDBR-DBR-24-1569-EDBR", "edition": "R02/2025", "annex": "A" or "C", "page": 72 or 77}`. `None` fields are preserved as `not_transcribed` warnings and are never fabricated.

- [ ] **Step 3: Run entry tests GREEN**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py`.

Expected: all table tests pass.

- [ ] **Step 4: Verify exact boundary and source trace**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py -vv`.

Confirm the output distinguishes A1/A2/B1 overlaps by `supply_type` and exposes Annex/page instead of only a breaker value.

- [ ] **Step 5: Commit the entry slice**

```text
feat: selecionar padrao de entrada enel bt
```

Record the table pages and the intentionally preserved `None` fields in the session log.

---

### Task 4: Integrar circuitos explícitos e runner da disciplina

**Files:**
- Create: `framework/galpao_fw/residencial_eletrica.py`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py`

**Interfaces:**
- `validate_circuit_points(circuits: dict) -> dict` returns `ok`, `errors`, `warnings`, `points`.
- `run_residential_electrical(normalized, run_dir, preflight=None) -> (turnkey_result, discipline_records)`.
- `register_residential_electrical_adapter() -> None` registers name `casa-residencial-eletrica`, type `residencial`, discipline `eletrico`, deliverable `report`.

- [ ] **Step 1: Confirm the adapter tests are RED**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py`.

Expected: failure because the real adapter and runner do not exist.

- [ ] **Step 2: Implementar validação sem heurística de pontos**

`validate_circuit_points` must require `circuits.points` to be a list. Each point must be an object with non-empty string `id` and `room`, one of `lighting`, `tug`, `tue` in `kind`, finite numeric `power_va > 0`, and finite numeric `voltage_v > 0`. Duplicate IDs produce `duplicate_circuit_id`; missing values produce `missing_circuit_power` or `missing_circuit_voltage`; invalid kinds produce `unsupported_circuit_kind`. An empty list returns `ok=False` with `missing_circuit_points`. `routes` is accepted only as a list and is not generated.

The returned `points` must be a deep copy containing only the validated explicit input; no room or point may be created from the room counts.

- [ ] **Step 3: Implementar composição do runner**

The runner must:

1. Read `normalized["turnkey_spec"]["eletrico"]` and `source_refs` for discipline `eletrico`.
2. Check the three required source IDs. Missing required IDs return a blocked record with `missing_required_source`; a status other than 2 or `is_stale=True` is already reported by generic preflight and must remain visible in the record.
3. Validate the payload shape, network fields and circuits.
4. Call `calculate_residential_demand` and `select_enel_bt_entry` only after their required input sections exist.
5. Return a turnkey result with `schema: "freecad-automatic/residential-electrical-result"`, `schema_version: 1`, `adapter`, `project_id`, `source_refs`, `calculation`, `service_entry`, `circuits`, and `scope`.
6. Return one discipline record under `eletrico` with `native_atende: None`, `errors`, `warnings`, `gates`, `calculation`, `service_entry`, `circuits`, and status `needs_review` only when all required calculations are valid; any validation/calculation error yields `blocked`.
7. Set warnings for `source_snapshot_requires_readiness`, `executive_deliverables_not_implemented`, and any untranscribed table fields. The record must not claim Enel approval or construction readiness.

Use this record shape:

```python
{
    "status": "needs_review",
    "native_atende": None,
    "reprovados": [],
    "warnings": [
        {"code": "source_snapshot_requires_readiness"},
        {"code": "executive_deliverables_not_implemented"},
    ],
    "errors": [],
    "gates": {
        "required_sources_declared": True,
        "explicit_network_inputs": True,
        "explicit_circuit_points": True,
    },
    "calculation": calculation,
    "service_entry": service_entry,
    "circuits": circuit_result,
    "artifacts": [],
}
```

No runner code may import `condutores_nbr5410` or `protecao_nbr5410` until a circuit supplies the explicit parameters those APIs require; this phase records the validated circuit contract and leaves conductor/protection dimensioning as a later vertical slice.

- [ ] **Step 4: Run the adapter tests GREEN in isolation**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py`.

Expected: the pure adapter tests pass except the registration test, because registration is the next step.

- [ ] **Step 5: Commit the runner slice**

```text
feat: integrar disciplina eletrica residencial
```

Record the explicit-point contract and the intentional absence of conductor/protection sizing in the session log.

---

### Task 5: Registrar o adaptador e persistir a fixture residencial elétrica

**Files:**
- Modify: `framework/galpao_fw/builtin_adapters.py`
- Create: `projects/casa-residencial-eletrica-sintetica/project-spec.json`
- Create: `projects/casa-residencial-eletrica-sintetica/README.md`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py`

**Interfaces:**
- Existing adapters retain their registration order and behavior.
- New adapter is discoverable by `describe_adapters()` and selected only by `adapter: "casa-residencial-eletrica"`.
- The persisted fixture must run through `run_project_file()` without a special path.

- [ ] **Step 1: Add the registration test before editing the loader**

Run the existing registration test and confirm it fails only because `casa-residencial-eletrica` is absent.

- [ ] **Step 2: Register the real residential electrical adapter**

In `register_builtin_adapters()`, import `register_residential_electrical_adapter` from `residencial_eletrica` alongside the synthetic registration and call it in both loader branches. Do not add a direct import of `galpao_turnkey` to the new module.

- [ ] **Step 3: Create the persisted project spec**

Use this complete envelope, with the source titles/editions copied into each reference:

```json
{
  "schema": "freecad-automatic/project-spec",
  "schema_version": 1,
  "adapter": "casa-residencial-eletrica",
  "project": {
    "slug": "casa-residencial-eletrica-sintetica",
    "type": "residencial",
    "date": "2026-08-15"
  },
  "geometry": {"comprimento": 10.0, "vao": 8.0, "pe_direito": 3.0},
  "turnkey": {
    "eletrico": {
      "network": {
        "voltage_system": "127/220",
        "supply_type": "B",
        "network_kind": "aerea",
        "location_factor": 1.0
      },
      "rooms": {
        "quarto": 2, "sala": 1, "banheiro": 1,
        "cozinha": 1, "area_servico": 1, "outros": 0
      },
      "loads": {
        "installed_load_kw": 7.5,
        "heating": [], "motors": [], "special_lighting": []
      },
      "circuits": {
        "points": [
          {"id": "L-01", "room": "sala", "kind": "lighting",
           "power_va": 100, "voltage_v": 127},
          {"id": "T-01", "room": "cozinha", "kind": "tug",
           "power_va": 600, "voltage_v": 127},
          {"id": "TUE-01", "room": "banheiro", "kind": "tue",
           "power_va": 4400, "voltage_v": 220}
        ],
        "routes": []
      }
    }
  },
  "source_refs": {
    "eletrico": [
      {
        "notebook_id": "78cd2efd-0652-484e-b312-c5c5a7648962",
        "source_id": "d213019d-6e5c-4f18-8151-bf5a74c11b5d",
        "title": "ABNT NBR 5410:2004",
        "edition": "2004", "status": 2, "is_stale": false
      },
      {
        "notebook_id": "78cd2efd-0652-484e-b312-c5c5a7648962",
        "source_id": "5129118d-2ff6-4187-a9d2-d1828d61afdf",
        "title": "Enel BT individual",
        "edition": "R02/2025", "status": 2, "is_stale": false
      },
      {
        "notebook_id": "78cd2efd-0652-484e-b312-c5c5a7648962",
        "source_id": "5bc6c2f1-c8b8-4a04-8b82-be0e937b4749",
        "title": "Enel Rio WKI cálculo de demanda BT",
        "edition": "R01/2018", "status": 2, "is_stale": false
      },
      {
        "notebook_id": "78cd2efd-0652-484e-b312-c5c5a7648962",
        "source_id": "4c71daf6-ff91-44d1-a5e7-d7f881ab66f8",
        "title": "ANEEL PRODIST Módulo 3",
        "edition": "vigente no snapshot", "status": 2, "is_stale": false
      }
    ]
  }
}
```

- [ ] **Step 4: Run the persisted fixture through the universal loop**

Run:

```powershell
python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('framework/galpao_fw').resolve())); from project_io import run_project_file; print(run_project_file(Path('projects/casa-residencial-eletrica-sintetica/project-spec.json'), Path('saida_residencial_eletrica'), options={'generate_ifc': False}))"
```

Expected: result `status` equal to `needs_review`, discipline `eletrico` equal to `needs_review`, service-entry row `B1`, and only generic JSON artifacts.

- [ ] **Step 5: Add the README with safe execution and readiness commands**

Document the exact workflow:

```powershell
nlm login
python -m framework.galpao_fw.project_loop_cli --spec projects/casa-residencial-eletrica-sintetica/project-spec.json --out-dir projects/casa-residencial-eletrica-sintetica/readiness --preflight-only --require-source-refs
python -m framework.galpao_fw.project_loop_cli --spec projects/casa-residencial-eletrica-sintetica/project-spec.json --out-dir projects/casa-residencial-eletrica-sintetica/run --readiness projects/casa-residencial-eletrica-sintetica/readiness --require-source-refs --no-ifc
```

State that the local `status: 2` values are a snapshot and that the first command after `nlm login` is the live source gate; no approval Enel/ART is implied.

- [ ] **Step 6: Run focused and generalization tests**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_adapter.py framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py -m "not build"`.

Expected: all focused tests pass and the existing galpão/residential synthetic contract remains green.

- [ ] **Step 7: Commit only loader, fixture, README and focused test changes**

```text
feat: registrar fixture eletrica residencial
```

Update `.superpowers/sdd/progress.md` with Task 1–5 completion and the focused test count.

---

### Task 6: Validar fonte viva, manifesto e regressões do galpão

**Files:**
- Modify: `framework/galpao_fw/COMO-RODAR.md` if command details need correction.
- Modify: `.superpowers/sdd/progress.md`.
- Modify: `sessions/2026-08-15.md`.
- Test: existing project-loop and electrical suites.

- [ ] **Step 1: Reautenticar e verificar as 39 fontes elétricas**

Run:

```powershell
nlm login
nlm list sources 78cd2efd-0652-484e-b312-c5c5a7648962 --json --full
```

Expected: the command succeeds, the notebook remains under 50 sources, the three required source IDs exist, and each has `status: 2` and `is_stale: false`. If the CLI reports a changed source ID/title, stop the run and update only the fixture source snapshot after recording the difference.

- [ ] **Step 2: Execute the live source gate for the persisted fixture**

Run the documented readiness command with `nlm login` already successful. Expected: `project-readiness.json` is `ready` for the source gate and records a SHA-256; the project itself remains `needs_review` after execution because executive deliverables are intentionally absent.

- [ ] **Step 3: Verify persisted artifacts**

Run:

```powershell
python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('framework/galpao_fw').resolve())); from project_loop import verify_project_run; print(verify_project_run(Path('projects/casa-residencial-eletrica-sintetica/run')))"
```

Expected: `ok: True`, all generated JSON artifact hashes valid, no absolute path and no forbidden artifact extension.

- [ ] **Step 4: Run the electrical and framework regression suites**

Run:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop framework/galpao_fw/tests/test_eletrico_bt.py framework/galpao_fw/tests/test_eletrico_robustez.py framework/galpao_fw/tests/test_eletrico_bim.py framework/galpao_fw/tests/test_executivo_eletrico.py -m "not build"
```

Expected: all tests pass; any failure in a pre-existing galpão test is investigated before the task is marked complete.

- [ ] **Step 5: Audit isolation and placeholders**

Run:

```powershell
rg -n "galpao_eletrico|galpao_hidraulica|galpao_turnkey|__PENDENTE__" framework/galpao_fw/residencial_eletrica.py framework/galpao_fw/demanda_residencial_enel.py framework/galpao_fw/entrada_enel_bt.py projects/casa-residencial-eletrica-sintetica
git diff --check
```

Expected: no galpão import, no pending marker, no placeholder, and no whitespace errors. The generic core may retain its deliberate `PENDING_MARKER`; this audit is restricted to the new vertical and fixture.

- [ ] **Step 6: Request the broad review before claiming completion**

Review the complete diff for spec compliance, source traceability, status honesty, table boundary behavior, and preservation of unrelated worktree changes. Do not mark the phase complete until verification output exists and the broad review has no unresolved finding.

- [ ] **Step 7: Close the phase record**

Append a structured session entry with focused/trunk counts, live source result, artifact verification, and carry-over: conductor/protection sizing, 2D/unifilar, BIM/IFC and other disciplines remain future phases. Update `.superpowers/sdd/progress.md` with the final evidence.

## Self-review checklist

- Spec coverage: demand rules are Task 2; Enel tables are Task 3; explicit circuits/statuses/source refs are Task 4; registration and persisted universal run are Task 5; live source evidence and regression are Task 6.
- No production code is written before the corresponding RED test exists and has been observed failing.
- Every public function has a focused test and every persisted path has a verification test.
- No placeholder marker is introduced in the plan, new source modules or fixture.
- The sample contract is internally consistent: `supply_type=B`, `127/220`, `installed_load_kw=7.5` selects Anexo A row B1, and every circuit point has `voltage_v`.
- A missing location factor, source, voltage, supply type, installed-load row or circuit value produces a structured blocked result rather than a guessed value.
- A successful calculation remains `needs_review` and never claims concessionaire approval or construction readiness.
