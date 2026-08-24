# Loop de Generalização do Framework Implementation Plan

**Status:** fase implementada e verificada em 2026-08-24; evidência e commits
registrados na seção `Execution record` ao final deste documento.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separar a implementação nativa do galpão do núcleo do Loop, registrar uma casa residencial sintética como adaptador independente e provar que as duas tipologias percorrem o mesmo contrato auditável.

**Architecture:** `project_loop.py` permanecerá responsável por normalização, preflight, estados, manifestos, artefatos e iterações. Um carregador de adaptadores registrará o adaptador do galpão e o adaptador residencial sintético; cada módulo de tipologia conterá seu runner e hooks, sem ramificações de tipologia no núcleo. O segundo projeto será um fixture declarativo e determinístico, explicitamente não apto para obra.

**Tech Stack:** Python 3, `pytest`, JSON versionado, subprocesso Python para o teste de isolamento de importação, filesystem local e os contratos já expostos por `project_loop.py`.

## Global Constraints

- O galpão continua sendo o caso de integração realista e seus 419 clashes abertos não serão resolvidos nesta fase.
- Nenhum dado ou regra específica do galpão será adicionado ao núcleo universal.
- O `ProjectSpec` é declarativo; nenhum adaptador inventará cargas, dimensões, normas ou decisões de engenharia.
- A casa residencial sintética deve ser marcada como fixture de teste e não pode alegar prontidão para obra.
- Hooks ausentes devem permanecer como `not_available` ou `not_requested`, sem arquivos falsos.
- O núcleo não consulta implicitamente NotebookLM; fontes entram somente por `source_refs` ou catálogo versionado.
- Não introduzir dependências novas para executar o Loop ou os testes focados.
- Preservar mudanças não relacionadas já existentes no worktree; não usar `git reset`, `git checkout` ou limpeza destrutiva.

---

# Phase 4: Loop de generalização

## Scope

Extrair a tipologia galpão para um módulo de adaptador, registrar uma casa
residencial sintética independente e validar os contratos de entrada,
capacidades, disciplinas, entregáveis, coordenação e verificação de artefatos.
Esta fase entrega uma prova de generalização do framework, não cálculos
residenciais de engenharia.

## Entry condition

- `docs/superpowers/specs/2026-08-15-generalizacao-framework-design.md` está aprovado.
- O registro de adaptadores, os hooks e o manifesto persistente existentes continuam disponíveis.
- A jornada trunk do galpão e os testes focados de `project_loop` estão presentes.
- O worktree pode conter alterações anteriores; os arquivos fora do escopo devem ser preservados.

## Exit condition

- `project_loop.py` não contém implementação ou import direto de `galpao_turnkey`; o núcleo apenas despacha para adaptadores.
- `galpao` e `casa-residencial-sintetica` aparecem em `describe_adapters()` com capacidades JSON-safe.
- O spec residencial salvo executa sem importar ou chamar `galpao_turnkey`.
- A execução residencial gera manifesto verificável, relatório genérico e estados honestos para hooks ausentes.
- A jornada trunk do galpão permanece verde e continua gerando seus artefatos de integração.
- Testes positivos e negativos da fase passam, e não há artefato residencial fictício de IFC, 3D ou desenhos.

## Must-exist checklist

- [x] `framework/galpao_fw/galpao_adapter.py` contém o runner e hooks específicos do galpão.
- [x] `framework/galpao_fw/casa_residencial_sintetica.py` contém somente o adaptador sintético e não importa `galpao_turnkey`.
- [x] `framework/galpao_fw/builtin_adapters.py` registra os adaptadores nativos sem colocar lógica de tipologia no núcleo.
- [x] `projects/casa-residencial-sintetica/project-spec.json` é um envelope UTF-8 válido, versionado e determinístico.
- [x] `framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py` cobre registro, execução, isolamento e contrato comum.
- [x] `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py` executa também o spec residencial depois da jornada do galpão.
- [x] O manifesto residencial contém `adapter_capabilities`, `disciplines`, `deliverables`, `coordination`, `artifacts` e `verification`.
- [x] `verify_project_run()` valida a execução residencial sem erro.
- [x] A jornada `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py` continua verde.
- [x] `framework/galpao_fw/COMO-RODAR.md` documenta a execução do fixture residencial como validação de contrato, não como projeto para obra.

## Must-not-exist checklist

- [x] `project_loop.py` não contém `import galpao_turnkey`, `from galpao_turnkey` ou chamadas a `galpao_turnkey`.
- [x] `project_loop.py` não conhece o caminho específico `reports/turnkey.txt`; o hook do galpão registra esse artefato.
- [x] `casa_residencial_sintetica.py` não importa `galpao_turnkey`, `galpao_concreto`, `galpao_eletrico`, `galpao_hidraulica` ou `galpao_turnkey` por import dinâmico.
- [x] O spec sintético não contém `__PENDENTE__`, números apresentados como dimensionamento normativo ou claims de aprovação.
- [x] A execução residencial não cria IFC, modelo 3D, desenhos ou caderno quando o adaptador não fornece os hooks.
- [x] Nenhuma condição `if galpao` ou equivalente é adicionada ao caminho universal de execução.
- [x] O adaptador residencial não reutiliza `turnkey_fixture` nem copia o runner do galpão.
- [x] Nenhuma decisão técnica é criada para os 419 clashes do galpão nesta fase.
- [x] Nenhum teste usa mock para fingir que um artefato inexistente foi gerado.

## Test plan

### Positive

- [x] O registro lista `casa-residencial-sintetica` com tipo `residencial` e disciplinas `arquitetura`, `eletrico` e `hidraulica`.
- [x] O spec residencial passa por `run_project_file()` e produz `reports/adapter-result.json` e `reports/disciplinas.json`.
- [x] O resultado residencial preserva o `ProjectSpec`, as capacidades e os estados no manifesto.
- [x] O resultado residencial é `needs_review` por ser fixture sintético e por não fornecer coordenação/entregáveis opcionais, sem ser apresentado como `passed` para obra.
- [x] `verify_project_run()` confirma todos os artefatos declarados da execução residencial.
- [x] Um subprocesso que proíbe a importação de `galpao_turnkey` consegue importar o Loop e executar a casa.
- [x] Galpão e casa expõem as mesmas chaves estruturais de manifesto, sem exigir os mesmos números ou disciplinas.
- [x] A jornada trunk do galpão mantém coordenação, iteração, revisão e artefatos relativos.

### Negative

- [x] Tipo `industrial` no adaptador residencial é bloqueado com `unsupported_project_type` antes do runner.
- [x] Geometria comum ausente ou inválida é bloqueada pelo preflight.
- [x] Solicitar IFC, 3D ou desenhos à casa sem hooks resulta em `not_available`, não em arquivo vazio ou status `generated`.
- [x] Um adaptador desconhecido continua listando os adaptadores registrados e não executa disciplinas.
- [x] Um artefato residencial adulterado faz `verify_project_run()` falhar por hash.

## Test tree integration

- **Trunk touch point:** `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`, depois da execução inicial e antes da iteração/revisão; a jornada do galpão continua sendo a integração de referência.
- **New branches added:**
  - `test_project_loop_generalization.py::test_residential_adapter_is_registered_with_declared_capabilities`
  - `test_project_loop_generalization.py::test_residential_spec_runs_with_honest_optional_states`
  - `test_project_loop_generalization.py::test_residential_missing_hooks_are_not_available_when_requested`
  - `test_project_loop_generalization.py::test_residential_execution_does_not_import_galpao_turnkey`
  - `test_project_loop_generalization.py::test_residential_manifest_matches_universal_contract`
  - `test_project_loop_generalization.py::test_residential_type_mismatch_is_blocked`
  - `test_project_loop_generalization.py::test_residential_missing_geometry_is_blocked`
  - `test_project_loop_generalization.py::test_residential_artifact_tampering_is_detected`

## Next phase seed

Usar os contratos comprovados por galpão e casa para adicionar calculadores reais por disciplina, começando por uma disciplina residencial escolhida explicitamente e com fontes normativas versionadas.

---

## File map and interfaces

### Core boundary

**Modify:** `framework/galpao_fw/project_loop.py`

Keep these universal symbols in the core:

```python
register_adapter(name, runner, *, project_types=(), disciplines=(),
                 deliverables=(), hooks=None)
describe_adapters(name=None)
normalize_spec(spec) -> dict
preflight_project(spec, out_dir=None, options=None) -> dict
run_project(spec, out_dir, options=None, *, iteration=1,
            parent_run_id=None, changes=None, resolutions=None) -> dict
verify_project_run(manifest_or_path) -> dict
```

Remove the native galpão runner, its hooks and its registration from this
file. The universal executor continues to call `_PROJECT_ADAPTERS` and
`_PROJECT_HOOKS`, but does not know which adapter performs the work.

### Native adapter loader

**Create:** `framework/galpao_fw/builtin_adapters.py`

Expose one idempotent loader:

```python
def register_builtin_adapters() -> None:
    from galpao_adapter import register_galpao_adapter
    from casa_residencial_sintetica import register_residential_adapter

    register_galpao_adapter()
    register_residential_adapter()
```

Call it once at the end of `project_loop.py`, after all universal functions
needed by the adapter modules have been defined. The loader must not import
`galpao_turnkey` itself.

### Galpão adapter

**Create:** `framework/galpao_fw/galpao_adapter.py`

Move, without semantic changes, the existing galpão-specific symbols:

```python
_write_coordination
_emit_ifc
_freecad_executable
_register_tree
_optional_status
_emit_model_3d
_emit_drawings
_basic_classify
_review_signals
_preflight_blocked_names
_run_turnkey
_write_turnkey_report
```

Import only universal helpers from `project_loop`:

```python
from project_loop import (
    _add_artifact, _empty_discipline, _json_safe,
    _relative_runtime_paths, _selected_turnkey_spec, _write_json,
    register_adapter,
)
```

Expose:

```python
def register_galpao_adapter() -> None:
    register_adapter(
        "galpao", _run_turnkey,
        project_types=("galpao", "industrial"),
        disciplines=KNOWN_DISCIPLINES,
        deliverables=("ifc", "model_3d", "drawings", "coordination", "iteration"),
        hooks={
            "report": _write_turnkey_report,
            "coordination": _write_coordination,
            "ifc": _emit_ifc,
            "model_3d": _emit_model_3d,
            "drawings": _emit_drawings,
        },
    )
```

`KNOWN_DISCIPLINES` remains a universal list for legacy preflight compatibility;
the adapter imports that constant rather than redefining a second list. All
imports of `galpao_turnkey` stay inside galpão functions, so loading the
registry does not execute the galpão engine for another adapter. The
`_write_turnkey_report` hook must call `_add_artifact()` for
`reports/turnkey.txt`; the universal `_record_standard_artifacts()` list must
not contain that path.

### Residential synthetic adapter

**Create:** `framework/galpao_fw/casa_residencial_sintetica.py`

The module must not import any galpão module. Its runner has the exact public
shape below and returns only deterministic contract data:

```python
ADAPTER_NAME = "casa-residencial-sintetica"
DISCIPLINES = ("arquitetura", "eletrico", "hidraulica")


def _run_residential_synthetic(normalized, run_dir):
    records = {}
    result_disciplines = {}
    for name in normalized["requested_disciplines"]:
        payload = normalized["turnkey_spec"].get(name)
        present = isinstance(payload, dict)
        warning = {
            "code": "synthetic_fixture",
            "detail": "resultado de contrato; não é dimensionamento para obra",
        }
        if not present:
            records[name] = {
                "status": "blocked",
                "native_atende": None,
                "reprovados": [],
                "gates": {},
                "warnings": [warning],
                "errors": [{"code": "missing_synthetic_input"}],
                "artifacts": [],
            }
        else:
            records[name] = {
                "status": "needs_review",
                "native_atende": None,
                "reprovados": [],
                "gates": {"synthetic_fixture": True},
                "warnings": [warning],
                "errors": [],
                "artifacts": [],
            }
        result_disciplines[name] = {"input_present": present}
    return {
        "schema": "freecad-automatic/synthetic-adapter-result",
        "schema_version": 1,
        "adapter": ADAPTER_NAME,
        "synthetic_fixture": True,
        "project_id": normalized["project_id"],
        "disciplines": result_disciplines,
    }, records


def register_residential_adapter():
    register_adapter(
        ADAPTER_NAME,
        _run_residential_synthetic,
        project_types=("residencial",),
        disciplines=DISCIPLINES,
        deliverables=("report",),
    )
```

If the existing `_empty_discipline()` shape is preferable during
implementation, use it without changing the public statuses or adding a
calculation claim. The important invariant is that an input-bearing synthetic
discipline is `needs_review`, while a missing required payload is `blocked`.

### Persisted fixture

**Create:** `projects/casa-residencial-sintetica/project-spec.json`

Use this exact semantic envelope (values are test data, not normative
assumptions):

```json
{
  "schema": "freecad-automatic/project-spec",
  "schema_version": 1,
  "adapter": "casa-residencial-sintetica",
  "project": {
    "slug": "casa-residencial-sintetica",
    "type": "residencial",
    "description": "fixture de contrato; não é projeto para obra"
  },
  "site": {
    "synthetic_fixture": true,
    "city": "São João da Barra",
    "state": "RJ",
    "utility": "ENEL"
  },
  "source_refs": {
    "arquitetura": [],
    "eletrico": [],
    "hidraulica": []
  },
  "turnkey": {
    "geometria": {
      "comprimento": 10.0,
      "vao": 8.0,
      "pe_direito": 3.0
    },
    "arquitetura": {
      "synthetic_fixture": true,
      "ambientes": ["sala", "cozinha", "banheiro", "quarto"]
    },
    "eletrico": {
      "synthetic_fixture": true,
      "tensao_V": 220.0,
      "pontos": 8
    },
    "hidraulica": {
      "synthetic_fixture": true,
      "pontos_consumo": 4,
      "pontos_esgoto": 3
    }
  }
}
```

**Create:** `projects/casa-residencial-sintetica/README.md` with the warning
that the file exercises the framework contract only and deliberately has no
normative source approval or construction deliverables.

### Tests

**Create:** `framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py`

Start with these red tests before creating the adapter modules:

```python
import json
import subprocess
import sys
from pathlib import Path

import pytest

from project_loop import describe_adapters, run_project, run_project_file


ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT.parent.parent / "projects" / "casa-residencial-sintetica" / "project-spec.json"


def test_residential_adapter_is_registered_with_declared_capabilities():
    capability = next(item for item in describe_adapters()
                      if item["name"] == "casa-residencial-sintetica")
    assert capability["project_types"] == ["residencial"]
    assert capability["disciplines"] == ["arquitetura", "eletrico", "hidraulica"]
    assert capability["deliverables"] == ["report"]


def test_residential_spec_runs_with_honest_optional_states(tmp_path):
    result = run_project_file(SPEC, tmp_path, options={"generate_ifc": False})
    assert result["adapter"] == "casa-residencial-sintetica"
    assert result["project_type"] == "residencial"
    assert result["status"] == "needs_review"
    assert set(result["disciplines"]) == {"arquitetura", "eletrico", "hidraulica"}
    assert all(item["status"] == "needs_review"
               for item in result["disciplines"].values())
    assert result["coordination"]["status"] == "not_available"
    assert result["deliverables"]["ifc"]["status"] == "not_requested"
    assert result["deliverables"]["model_3d"]["status"] == "not_requested"
    assert result["deliverables"]["drawings"]["status"] == "not_requested"
    assert (tmp_path / "reports" / "adapter-result.json").is_file()


def test_residential_execution_does_not_import_galpao_turnkey(tmp_path):
    script = r'''
import builtins
import sys
from pathlib import Path

root = Path(sys.argv[1])
spec = Path(sys.argv[2])
out = Path(sys.argv[3])
sys.path.insert(0, str(root))
real_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name.split(".", 1)[0] == "galpao_turnkey":
        raise AssertionError("galpao_turnkey importado pela casa")
    return real_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from project_loop import run_project_file, verify_project_run
result = run_project_file(spec, out, options={"generate_ifc": False})
assert result["adapter"] == "casa-residencial-sintetica"
assert verify_project_run(out)["ok"] is True
'''
    completed = subprocess.run(
        [sys.executable, "-c", script, str(ROOT), str(SPEC), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_residential_missing_hooks_are_not_available_when_requested(tmp_path):
    result = run_project_file(
        SPEC, tmp_path,
        options={"generate_ifc": True, "generate_3d": True,
                 "generate_2d": True},
    )
    assert result["deliverables"]["ifc"]["status"] == "not_available"
    assert result["deliverables"]["model_3d"]["status"] == "not_available"
    assert result["deliverables"]["drawings"]["status"] == "not_available"
    assert all(not item["path"].startswith(("bim/", "model/", "drawings/"))
               for item in result["artifacts"])


def test_residential_type_mismatch_is_blocked(tmp_path):
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    spec["project"]["type"] = "industrial"
    result = run_project(spec, tmp_path, options={"generate_ifc": False})
    assert result["status"] == "blocked"
    assert any(item["code"] == "unsupported_project_type"
               for item in result["preflight"]["errors"])


def test_residential_missing_geometry_is_blocked(tmp_path):
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    del spec["turnkey"]["geometria"]["vao"]
    result = run_project(spec, tmp_path, options={"generate_ifc": False})
    assert result["status"] == "blocked"
    assert any(item["code"] == "invalid_common_geometry"
               and item["path"] == "vao"
               for item in result["preflight"]["errors"])
```

Add the universal-manifest comparison and tamper test after the first red/green
cycle:

```python
from project_loop import verify_project_run


def test_residential_manifest_matches_universal_contract(
        tmp_path, turnkey_fixture):
    house_dir = tmp_path / "house"
    house = run_project_file(SPEC, house_dir,
                             options={"generate_ifc": False})
    galpao_dir = tmp_path / "galpao"
    galpao = run_project(turnkey_fixture(), galpao_dir,
                         options={"generate_ifc": False})
    universal = {"schema", "adapter", "adapter_capabilities", "disciplines",
                 "deliverables", "coordination", "artifacts", "verification"}
    assert universal <= house.keys()
    assert universal <= galpao.keys()
    assert verify_project_run(house_dir)["ok"] is True
    assert verify_project_run(galpao_dir)["ok"] is True


def test_residential_artifact_tampering_is_detected(tmp_path):
    result = run_project_file(SPEC, tmp_path,
                              options={"generate_ifc": False})
    artifact = next(item for item in result["artifacts"]
                    if item["path"] == "reports/adapter-result.json")
    (tmp_path / artifact["path"]).write_text("adulterado", encoding="utf-8")
    verification = verify_project_run(tmp_path)
    assert verification["ok"] is False
    assert any(item["code"] == "artifact_hash_mismatch"
               and item["path"] == artifact["path"]
               for item in verification["errors"])
```

The final test module may import `run_project_file` from `project_loop` or
`project_io`; use the existing project-loop convention consistently. If the
repository's actual test path calculation differs, correct only the path
expression and retain the same behavior assertions.

### Documentation

**Modify:** `framework/galpao_fw/COMO-RODAR.md`

Add a short section with the exact commands:

```powershell
python framework/galpao_fw/project_loop_cli.py `
  --spec projects/casa-residencial-sintetica/project-spec.json `
  --out-dir .loop-runtime/project-loop/casa-residencial-sintetica `
  --no-ifc

python framework/galpao_fw/project_loop_cli.py `
  --verify-run .loop-runtime/project-loop/casa-residencial-sintetica
```

Document the expected meaning: the run is a contract fixture and may be
`needs_review`; verification `ok: true` proves artifact integrity, not
engineering approval.

**Modify:** `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`

Extend the existing golden journey after its galpão review assertions. Add
`from pathlib import Path` and execute the persisted house spec through the
same file-input API:

```python
house_spec = (Path(__file__).resolve().parents[3].parent.parent
              / "projects" / "casa-residencial-sintetica" / "project-spec.json")
house = run_project_file(
    house_spec, tmp_path / "residencial",
    options={"generate_ifc": False},
)
assert house["adapter"] == "casa-residencial-sintetica"
assert house["status"] == "needs_review"
assert verify_project_run(tmp_path / "residencial")["ok"] is True
```

This keeps the trunk as one end-to-end journey that exercises both the
integration fixture and the independent typology; it does not compare
engineering numbers between them.

---

## Task 1: Write the failing generalization tests

**Files:**
- Create: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py`
- Read-only reference: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py`
- Read-only reference: `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`

**Interfaces:**
- Consumes: existing `describe_adapters`, `run_project`, `run_project_file` and `verify_project_run`.
- Produces: red assertions that define the residential adapter boundary, honest statuses, import isolation, type/geometry gates and universal manifest.

- [x] **Step 1: Add the registration and execution tests**

Use the concrete test code in the **Tests** section above. Keep the fixture
path anchored at the repository root and use a temporary output directory for
every run.

- [x] **Step 2: Run the new branch and verify the failure is meaningful**

Run:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py
```

Expected: FAIL because the persisted spec and
`casa-residencial-sintetica` registration do not exist yet. No test should
fail because of a syntax error or a wrong fixture path; fix only such test
setup errors before proceeding.

## Task 2: Extract the galpão adapter from the universal core

**Files:**
- Create: `framework/galpao_fw/galpao_adapter.py`
- Create: `framework/galpao_fw/builtin_adapters.py`
- Modify: `framework/galpao_fw/project_loop.py`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py`
- Regression: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py`

**Interfaces:**
- Consumes: the existing galpão hook bodies and universal helper functions.
- Produces: `register_galpao_adapter()` and `register_builtin_adapters()`; all current galpão capabilities and hook behavior remain unchanged.

- [x] **Step 1: Add a failing core-boundary assertion**

Add this test before moving implementation:

```python
from project_loop import __file__ as PROJECT_LOOP_FILE


def test_universal_core_has_no_direct_galpao_engine_import():
    source = Path(PROJECT_LOOP_FILE).read_text(encoding="utf-8")
    assert "import galpao_turnkey" not in source
    assert "from galpao_turnkey" not in source
```

Run the focused test and confirm it fails against the current implementation.

- [x] **Step 2: Move the galpão-only functions without changing behavior**

Move the symbols listed in **Galpão adapter** above as a single mechanical
extraction. Preserve their existing function signatures and JSON output. In
the new module, import universal helpers from `project_loop`; do not duplicate
artifact hashing, path normalization, preflight or manifest logic.

- [x] **Step 3: Add the built-in loader and remove native registration from the core**

Replace the old registration block at the bottom of `project_loop.py` with:

```python
from builtin_adapters import register_builtin_adapters

register_builtin_adapters()
```

The call must happen after `run_project` and all universal helper definitions,
so the adapter modules can import their stable helper interfaces.

- [x] **Step 4: Run the extraction regression**

Run:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py
```

Expected: all existing adapter-contract and golden-journey tests pass and the
core-boundary test passes after the extraction. If it fails, the extraction
left a direct galpão import or the core still names a galpão-only artifact.

- [x] **Step 5: Remove the last direct core references and run the test again**

Use `rg` to find remaining direct galpão imports in the core, move any missed
hook-local reference to `galpao_adapter.py`, then run:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py::test_universal_core_has_no_direct_galpao_engine_import framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py
```

Expected: PASS with no change to galpão manifest semantics.

## Task 3: Implement and register the residential synthetic adapter

**Files:**
- Create: `framework/galpao_fw/casa_residencial_sintetica.py`
- Modify: `framework/galpao_fw/builtin_adapters.py`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py`

**Interfaces:**
- Consumes: normalized spec and `run_dir` through `_run_residential_synthetic(normalized, run_dir)`.
- Produces: `(adapter_result, discipline_records)` with `needs_review` for present synthetic inputs and `blocked` for missing requested payloads.

- [x] **Step 1: Implement only the minimum runner described above**

Create the module with `ADAPTER_NAME`, `DISCIPLINES`,
`_run_residential_synthetic` and `register_residential_adapter`. The runner
must not write IFC, model, drawing or caderno files and must not import any
galpão module. Use only the input-presence check and the explicit
`synthetic_fixture` warning; do not add engineering calculations.

- [x] **Step 2: Register the adapter through the loader**

Add `register_residential_adapter()` to `register_builtin_adapters()` after
the galpão registration. Re-importing the module should simply overwrite the
same registry key through the existing `register_adapter` behavior.

- [x] **Step 3: Run the focused tests and confirm green**

Run:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py -k "residential_adapter_is_registered_with_declared_capabilities or galpao_adapter_is_directly_importable_in_a_fresh_process"
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py
```

Expected: the two registration/import tests and the galpao regressions pass.
The other residential branch tests may still fail because the persisted spec
is intentionally created only in Task 4; do not weaken those assertions.

## Task 4: Add the persisted fixture and documentation

**Files:**
- Create: `projects/casa-residencial-sintetica/project-spec.json`
- Create: `projects/casa-residencial-sintetica/README.md`
- Modify: `framework/galpao_fw/COMO-RODAR.md`
- Modify: `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py`

**Interfaces:**
- Consumes: the residential adapter name and schema version from Tasks 2–3.
- Produces: a reproducible file-input journey and operator instructions.

- [x] **Step 1: Create the exact JSON fixture**

Write the envelope from the **Persisted fixture** section as UTF-8 with
`ensure_ascii=False` semantics. Keep `synthetic_fixture: true` in site and
discipline payloads. Do not add `source_refs` that claim live normative
validation.

- [x] **Step 2: Add the fixture warning README**

State that this file exists to test contracts, manifests and dispatch, not to
issue a residential design. State that empty source references are deliberate
and that discipline results are `needs_review`.

- [x] **Step 3: Add the CLI commands to the operator guide**

Copy the commands from the **Documentation** section and explain the expected
`needs_review`/`verify ok` combination.

- [x] **Step 4: Run the file-input journey**

Run:

```powershell
$out = '.loop-runtime/project-loop/casa-residencial-sintetica-plan'
python framework/galpao_fw/project_loop_cli.py --spec projects/casa-residencial-sintetica/project-spec.json --out-dir $out --no-ifc
python framework/galpao_fw/project_loop_cli.py --verify-run $out
```

Expected: the first command reports the residential adapter and
`needs_review`; the second command exits successfully with `ok: true`.

- [x] **Step 5: Integrate the residential run into the trunk**

Apply the exact trunk extension from the **Documentation** section and run:

```powershell
python -m pytest -q framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py
```

Expected: the original galpão project-to-review journey and the appended
residential contract run pass in the same test execution.

## Task 5: Run phase regression and inspect the boundary

**Files:**
- Verify: `framework/galpao_fw/project_loop.py`
- Verify: `framework/galpao_fw/galpao_adapter.py`
- Verify: `framework/galpao_fw/casa_residencial_sintetica.py`
- Verify: `projects/casa-residencial-sintetica/project-spec.json`
- Verify: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py`

**Interfaces:**
- Consumes: all outputs from Tasks 1–4.
- Produces: evidence that both typologies use the same universal contract and that no prohibited scope leaked into the phase.

- [x] **Step 1: Run all project-loop branch tests and the trunk**

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py
```

Expected: PASS. The existing 103 branch tests and golden journey must remain
green; count differences are acceptable only when the command output itself
shows no failures.

- [x] **Step 2: Run the targeted turnkey regression**

```powershell
python -m pytest -q framework/galpao_fw/tests/test_turnkey.py framework/galpao_fw/tests/test_turnkey_bim.py framework/galpao_fw/tests/test_turnkey_clash.py framework/galpao_fw/tests/test_pipeline_bim.py framework/galpao_fw/tests/test_validacao.py framework/galpao_fw/tests/test_relatorio_x_calculo.py -m "not build"
```

Expected: PASS with no new failure caused by adapter extraction.

- [x] **Step 3: Check import and placeholder invariants**

```powershell
rg -n "import galpao_turnkey|from galpao_turnkey|__PENDENTE__|TODO|TBD" framework/galpao_fw/project_loop.py framework/galpao_fw/casa_residencial_sintetica.py projects/casa-residencial-sintetica
git diff --check
```

Expected: no forbidden galpão import in the core or residential module, no
pending marker/TODO/TBD in the synthetic fixture, and no whitespace errors.

- [x] **Step 4: Verify both persisted runs independently**

Run the CLI verification for the residential output and the known completed
galpão Loop 3 output:

```powershell
python framework/galpao_fw/project_loop_cli.py --verify-run .loop-runtime/project-loop/casa-residencial-sintetica-plan
python framework/galpao_fw/project_loop_cli.py --verify-run .loop-runtime/project-loop/loop3-coordination-framework-teste-3600-20260815
```

Expected: both return `ok: true`; the galpão result remains `needs_review`
because of coordination, not because of this phase.

## Task 6: Expose the project coordination policy

The approved design requires coordination policy to be configurable by the
project, while the universal core only classifies, reconciles and records
decisions. Close the audit gap with the smallest versioned contract:

- accept an optional `coordination_policy` object in the ProjectSpec;
- persist its effective values in preflight and the project manifest;
- use project `folga_mm` and `vol_min_mm3` in the galpao coordination hook,
  overriding execution defaults when declared;
- default `enabled` to true and `resolution_mode` to `manual_approval`;
- reject malformed or negative numeric policy values during preflight before
  any adapter runner executes;
- allow `enabled: false` to produce an explicit `disabled` coordination state,
  without creating clash artifacts or claiming technical resolution;
- keep manual approval as the only resolution mode; the core must not invent
  technical clash corrections;
- add focused tests for override, invalid input and disabled behavior;
- preserve legacy specs that omit `coordination_policy` by deriving the
  effective tolerances from `ProjectLoopOptions`.

The effective policy shape is:

```json
{
  "enabled": true,
  "folga_mm": 1.0,
  "vol_min_mm3": 1000.0,
  "resolution_mode": "manual_approval"
}
```

**Status:** complete. Commits `a77ecce`, `2411518` and `8f77c22` implement
the contract; the task review is approved and the branch, trunk, turnkey and
CLI verification evidence is recorded in the session log.

## Self-review against the approved specification

- **Separate core and adapters:** Task 2 moves all native galpão execution and hooks out of `project_loop.py`; Task 3 keeps residential logic in its own module.
- **ProjectSpec contract:** Task 4 persists the versioned envelope and Task 5 exercises file input and the manifest.
- **Discipline and deliverable contracts:** Task 3 returns explicit discipline states; the universal executor records absent hooks as `not_available`/`not_requested`.
- **Clash identity/policy:** no new technical clash decisions are fabricated; the existing galpão coordination hook remains isolated, and the residential adapter has no coordination hook.
- **Second project:** Task 4 creates the committed synthetic house fixture.
- **Galpão integration:** Task 4 extends the trunk with the residential run while preserving the original galpão project-to-review journey; Task 5 runs the trunk and targeted turnkey regression.
- **No construction claim:** the synthetic warning, README and `needs_review` assertions enforce this boundary.

## Placeholder and type review

The plan contains no `TODO`, `TBD`, or unspecified implementation step. The
only new public signatures are `register_galpao_adapter()`,
`register_residential_adapter()`, and `_run_residential_synthetic(normalized,
run_dir)`. The existing `register_adapter` and `run_project` signatures are
unchanged. Every test command names an exact path and an expected outcome.

## Execution record — 2026-08-24

- A implementação foi concluída nos commits `79d8025`, `e4a5dac`, `d274204`,
  `b6c35b8`, `c35b72e` e `03415ef`, com revisões independentes registradas
  nos relatórios ignorados `.superpowers/sdd/task-1*` a `task-4*`.
- O núcleo universal não importa `galpao_turnkey`; o runner e os hooks do
  galpão vivem em `galpao_adapter.py`, e o fixture residencial usa
  `casa_residencial_sintetica.py`.
- O spec `projects/casa-residencial-sintetica/project-spec.json` é executado
  pelo mesmo `run_project_file`, retorna `needs_review`, não gera artefatos
  técnicos e passa pelo verificador de hashes.
- Verificação fresca em 2026-08-24:
  `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py`
  — **14 passed**; branch do Loop + trunk — **215 passed**.
- `compileall` dos módulos universais/adaptadores e `git diff --check` dos
  arquivos da fase terminaram com código 0.
- O galpão continua sendo integração realista; seus clashes permanecem sob a
  política do projeto e não foram tecnicamente resolvidos nesta fase.

**Status da fase:** completa dentro do escopo aprovado. A próxima fase deve
escolher uma disciplina real e um contrato de entregável, usando a casa como
fixture de integração e sem converter essa fixture em projeto para obra.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-15-loop-generalizacao.md`.
Implementation must use `subagent-driven-development` or `executing-plans`,
follow the red-green-refactor order, and stop at the verification checkpoint
before claiming the phase complete.
