import json
import subprocess
import sys
from pathlib import Path

import pytest

from project_io import run_project_file
from project_loop import describe_adapters, normalize_spec, run_project, verify_project_run
from residencial_eletrica import run_residential_electrical


ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = ROOT.parents[1]
PERSISTED_SPEC = (REPO_ROOT / "projects" / "casa-residencial-eletrica-sintetica"
                  / "project-spec.json")
PERSISTED_README = PERSISTED_SPEC.with_name("README.md")


SOURCE_REFS = [
    {
        "source_id": "d213019d-6e5c-4f18-8151-bf5a74c11b5d",
        "notebook_id": "78cd2efd-0652-484e-b312-c5c5a7648962",
        "title": "ABNT NBR 5410:2004",
        "edition": "2004",
        "status": 2,
        "is_stale": False,
    },
    {
        "source_id": "5129118d-2ff6-4187-a9d2-d1828d61afdf",
        "notebook_id": "78cd2efd-0652-484e-b312-c5c5a7648962",
        "title": "Enel Brasil CNC-NDBR-DBR-24-1569-EDBR-R02",
        "edition": "R02",
        "status": 2,
        "is_stale": False,
    },
    {
        "source_id": "5bc6c2f1-c8b8-4a04-8b82-be0e937b4749",
        "notebook_id": "78cd2efd-0652-484e-b312-c5c5a7648962",
        "title": "Enel Rio WKI-OMBR-MAT-18-0263-INBR-R01",
        "edition": "R01",
        "status": 2,
        "is_stale": False,
    },
    {
        "source_id": "4c71daf6-ff91-44d1-a5e7-d7f881ab66f8",
        "notebook_id": "78cd2efd-0652-484e-b312-c5c5a7648962",
        "title": "PRODIST Modulo 3",
        "edition": "vigente",
        "status": 2,
        "is_stale": False,
    },
]


def _synthetic_designs():
    return [
        {
            "id": "C-L-01",
            "point_ids": ["L-01"],
            "length_m": 10.0,
            "system": "monofasico",
            "conductors_loaded": 2,
            "insulation": "PVC",
            "reference_method": "B1",
            "ambient_temperature_C": 30.0,
            "grouping_count": 3,
            "power_factor": 1.0,
            "voltage_drop_limit_pct": 4.0,
            "use": "iluminacao",
            "protection": {"location": "seco", "exposure": "quadro"},
        },
        {
            "id": "C-T-01",
            "point_ids": ["T-01"],
            "length_m": 12.0,
            "system": "monofasico",
            "conductors_loaded": 2,
            "insulation": "PVC",
            "reference_method": "B1",
            "ambient_temperature_C": 30.0,
            "grouping_count": 3,
            "power_factor": 0.8,
            "voltage_drop_limit_pct": 4.0,
            "use": "forca",
            "protection": {"location": "cozinha", "exposure": "quadro"},
        },
        {
            "id": "C-TUE-01",
            "point_ids": ["TUE-01"],
            "length_m": 18.0,
            "system": "monofasico",
            "conductors_loaded": 2,
            "insulation": "PVC",
            "reference_method": "B1",
            "ambient_temperature_C": 30.0,
            "grouping_count": 3,
            "power_factor": 1.0,
            "voltage_drop_limit_pct": 4.0,
            "use": "forca",
            "protection": {"location": "banheiro", "exposure": "quadro"},
        },
    ]


def _spec():
    return {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "adapter": "casa-residencial-eletrica",
        "project": {"slug": "casa-residencial-eletrica", "type": "residencial"},
        "geometria": {"comprimento": 10.0, "vao": 8.0, "pe_direito": 3.0},
        "turnkey": {
            "geometria": {"comprimento": 10.0, "vao": 8.0, "pe_direito": 3.0},
            "eletrico": {
                "network": {
                    "voltage_system": "127/220",
                    "supply_type": "B",
                    "network_kind": "aerea",
                    "location_factor": 1.0,
                },
                "rooms": {
                    "quarto": 2, "sala": 1, "banheiro": 1,
                    "cozinha": 1, "area_servico": 1, "outros": 0,
                },
                "loads": {
                    "installed_load_kw": 7.5,
                    "heating": [], "motors": [], "special_lighting": [],
                },
                "circuits": {
                    "points": [
                        {"id": "L-01", "room": "sala", "kind": "lighting",
                         "power_va": 100, "voltage_v": 127},
                        {"id": "T-01", "room": "cozinha", "kind": "tug",
                         "power_va": 600, "voltage_v": 127},
                        {"id": "TUE-01", "room": "banheiro", "kind": "tue",
                         "power_va": 6000, "voltage_v": 220},
                    ],
                    "routes": [],
                    "designs": _synthetic_designs(),
                },
            },
        },
        "source_refs": {"eletrico": [dict(ref) for ref in SOURCE_REFS]},
    }


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
    assert record["scope"]["conductor_sizing"] == "implemented"
    assert record["scope"]["protection_sizing"] == "implemented"
    assert record["scope"]["short_circuit_evaluation"] == "not_evaluated"
    adapter_result = json.loads(
        (tmp_path / "reports" / "adapter-result.json").read_text(encoding="utf-8"))
    assert adapter_result["scope"] == record["scope"]
    circuits = record["circuits"]
    assert set(circuits) >= {
        "points", "routes", "designs", "errors", "warnings", "ok", "scope",
    }
    assert circuits["ok"] is True
    assert circuits["scope"]["short_circuit_evaluation"] == "not_evaluated"
    assert [item["id"] for item in circuits["designs"]] == [
        "C-L-01", "C-T-01", "C-TUE-01",
    ]
    tue_design = next(item for item in circuits["designs"]
                      if item["id"] == "C-TUE-01")
    assert tue_design["load"]["power_va"] == pytest.approx(6000.0)
    assert tue_design["base_conductor"]["secao_mm2"] == 6
    assert tue_design["conductor"]["secao_mm2"] == 10
    assert tue_design["protection"]["disjuntor"]["IN"] == 32
    assert tue_design["traceability"]["source_ids"] == [
        "d213019d-6e5c-4f18-8151-bf5a74c11b5d",
    ]
    assert all(item["short_circuit"] == {"status": "not_evaluated"}
               for item in circuits["designs"])
    assert all(item["conductor"]["secao_mm2"] > 0 for item in circuits["designs"])
    assert all(item["protection"]["disjuntor"]["IN"] > 0
               for item in circuits["designs"])
    assert (tmp_path / "reports" / "adapter-result.json").is_file()


def test_persisted_residential_electrical_fixture_runs_through_universal_loop(tmp_path):
    result = run_project_file(PERSISTED_SPEC, tmp_path, options={
        "generate_ifc": False, "require_source_refs": True,
    })
    assert result["status"] == "needs_review"
    assert result["disciplines"]["eletrico"]["status"] == "needs_review"
    assert result["disciplines"]["eletrico"]["service_entry"]["entry"]["row"] == "B1"
    circuits = result["disciplines"]["eletrico"]["circuits"]
    assert [item["id"] for item in circuits["designs"]] == [
        "C-L-01", "C-T-01", "C-TUE-01",
    ]
    tue_design = next(item for item in circuits["designs"]
                      if item["id"] == "C-TUE-01")
    assert tue_design["load"]["power_va"] == pytest.approx(6000.0)
    assert tue_design["base_conductor"]["secao_mm2"] == 6
    assert tue_design["conductor"]["secao_mm2"] == 10
    assert tue_design["protection"]["disjuntor"]["IN"] == 32
    persisted_adapter = json.loads(
        (tmp_path / "reports" / "adapter-result.json").read_text(
            encoding="utf-8"))
    persisted_tue = next(
        item for item in persisted_adapter["circuits"]["designs"]
        if item["id"] == "C-TUE-01")
    assert persisted_tue["base_conductor"]["secao_mm2"] == 6
    assert persisted_tue["conductor"]["secao_mm2"] == 10
    assert persisted_tue["protection"]["disjuntor"]["IN"] == 32
    assert persisted_tue["traceability"]["source_ids"] == [
        "d213019d-6e5c-4f18-8151-bf5a74c11b5d",
    ]
    assert circuits["scope"]["short_circuit_evaluation"] == "not_evaluated"
    verification = verify_project_run(result)
    assert verification["ok"] is True
    artifacts = result["artifacts"]
    assert artifacts
    assert all(artifact["path"].endswith(".json") for artifact in artifacts)
    assert all(len(artifact.get("sha256", "")) == 64 for artifact in artifacts)
    assert {artifact["path"] for artifact in artifacts} == {
        "input/spec.json", "reports/adapter-result.json",
        "reports/disciplinas.json", "reports/preflight.json",
    }


def test_persisted_fixture_readme_documents_live_source_verification():
    readme = PERSISTED_README.read_text(encoding="utf-8")
    assert "python framework/galpao_fw/project_loop_cli.py" in readme
    assert "--verify-source-refs --preflight-only --require-source-refs" in readme
    assert "python -m framework.galpao_fw.project_loop_cli" not in readme


def test_builtin_loader_registers_residential_adapters_after_early_galpao_import():
    script = r'''
import sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
import galpao_adapter
from project_loop import describe_adapters
names = {item["name"] for item in describe_adapters()}
assert {"galpao", "casa-residencial-sintetica", "casa-residencial-eletrica"} <= names, names
'''
    completed = subprocess.run(
        [sys.executable, "-c", script, str(ROOT)],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


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


def test_required_electrical_source_must_match_notebook_id(tmp_path):
    spec = _spec()
    spec["source_refs"]["eletrico"][0]["notebook_id"] = "wrong-notebook"
    result = run_project(spec, tmp_path, options={"generate_ifc": False})
    errors = result["disciplines"]["eletrico"]["errors"]
    assert result["status"] == "blocked"
    assert any(
        error["code"] == "missing_required_source"
        and error.get("context", {}).get("source_id")
            == "d213019d-6e5c-4f18-8151-bf5a74c11b5d"
        and error.get("context", {}).get("notebook_id")
            == "78cd2efd-0652-484e-b312-c5c5a7648962"
        for error in errors
    )


def test_malformed_required_source_id_blocks_without_exception(tmp_path):
    spec = _spec()
    spec["source_refs"]["eletrico"][0]["source_id"] = []

    _, records = run_residential_electrical(normalize_spec(spec), tmp_path)

    record = records["eletrico"]
    assert record["status"] == "blocked"
    assert any(error["code"] == "missing_required_source"
               for error in record["errors"])


def test_malformed_required_notebook_id_blocks_without_exception(tmp_path):
    spec = _spec()
    spec["source_refs"]["eletrico"][0]["notebook_id"] = {}

    _, records = run_residential_electrical(normalize_spec(spec), tmp_path)

    record = records["eletrico"]
    assert record["status"] == "blocked"
    assert any(error["code"] == "missing_required_source"
               for error in record["errors"])


def test_direct_residential_electrical_import_works_in_fresh_process():
    script = r'''
import sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
import residencial_eletrica
assert callable(residencial_eletrica.run_residential_electrical)
assert callable(residencial_eletrica.register_residential_electrical_adapter)
'''
    completed = subprocess.run(
        [sys.executable, "-c", script, str(ROOT)],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_runner_exposes_limited_motor_table_scope_and_kva_field(tmp_path):
    result, records = run_residential_electrical(normalize_spec(_spec()), tmp_path)
    coverage = result["scope"]["motor_table_coverage"]
    assert coverage["status"] == "limited"
    assert coverage["supported"] == [{
        "connection": "trifasica",
        "power_cv": 1.0,
        "quantity": 1,
    }]
    assert coverage["demand_field"] == "demand_kva"
    assert records["eletrico"]["calculation"]["motors"]["demand_kva"] == 0.0


def test_invalid_circuit_point_blocks_without_heuristic_repair(tmp_path):
    spec = _spec()
    del spec["turnkey"]["eletrico"]["circuits"]["points"][0]["voltage_v"]
    result = run_project(spec, tmp_path, options={"generate_ifc": False})
    assert result["status"] == "blocked"
    assert any(error["code"] == "missing_circuit_voltage"
               for error in result["disciplines"]["eletrico"]["errors"])


@pytest.mark.parametrize("mutator, code", [
    (lambda circuits: circuits.pop("designs"), "missing_circuit_designs"),
    (lambda circuits: circuits["designs"][0].update({"power_factor": 0}),
     "invalid_design_value"),
])
def test_invalid_or_missing_design_blocks_runner_with_structured_error(
        mutator, code, tmp_path):
    spec = _spec()
    circuits = spec["turnkey"]["eletrico"]["circuits"]
    mutator(circuits)

    result = run_project(spec, tmp_path, options={"generate_ifc": False})

    record = result["disciplines"]["eletrico"]
    assert result["status"] == "blocked"
    assert record["status"] == "blocked"
    assert any(error["code"] == code for error in record["errors"])
    assert any(error["code"] == code for error in record["circuits"]["errors"])


def test_subterranean_network_blocks_aerial_enel_entry_selection(tmp_path):
    spec = _spec()
    spec["turnkey"]["eletrico"]["network"]["network_kind"] = "subterranea"
    _, records = run_residential_electrical(normalize_spec(spec), tmp_path)
    record = records["eletrico"]
    assert record["status"] == "blocked"
    assert any(error["code"] == "unsupported_network_kind_for_entry"
               for error in record["errors"])


def test_malformed_turnkey_spec_blocks_runner_without_exception(tmp_path):
    normalized = normalize_spec(_spec())
    normalized["turnkey_spec"] = None
    _, records = run_residential_electrical(normalized, tmp_path)
    record = records["eletrico"]
    assert record["status"] == "blocked"
    assert any(error["code"] == "invalid_electrical_payload"
               for error in record["errors"])


def test_preflight_with_non_list_errors_blocks_runner_without_exception(tmp_path):
    result, records = run_residential_electrical(
        normalize_spec(_spec()), tmp_path, preflight={"errors": None})

    record = records["eletrico"]
    assert record["status"] == "blocked"
    assert any(error["code"] == "invalid_preflight_errors"
               for error in record["errors"])


@pytest.mark.parametrize("normalized", [None, [], "invalid"])
def test_non_object_normalized_input_returns_blocked_envelope_without_exception(
        normalized, tmp_path):
    result, records = run_residential_electrical(normalized, tmp_path)

    record = records["eletrico"]
    assert result["status"] == "blocked"
    assert record["status"] == "blocked"
    assert any(error["code"] == "invalid_normalized_spec"
               for error in record["errors"])


def test_list_network_kind_blocks_runner_without_exception(tmp_path):
    spec = _spec()
    spec["turnkey"]["eletrico"]["network"]["network_kind"] = []

    _, records = run_residential_electrical(normalize_spec(spec), tmp_path)

    record = records["eletrico"]
    assert record["status"] == "blocked"
    assert any(error["code"] == "invalid_network_kind"
               for error in record["errors"])


def test_object_circuit_kind_blocks_runner_without_exception(tmp_path):
    spec = _spec()
    spec["turnkey"]["eletrico"]["circuits"]["points"][0]["kind"] = {}

    _, records = run_residential_electrical(normalize_spec(spec), tmp_path)

    record = records["eletrico"]
    assert record["status"] == "blocked"
    assert any(error["code"] == "unsupported_circuit_kind"
               for error in record["errors"])


def test_residential_electrical_path_does_not_import_galpao_modules(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_spec()), encoding="utf-8")
    script = r'''
import builtins, sys
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
result = run_project_file(spec_path, out_path, options={"generate_ifc": False})
assert result["adapter"] == "casa-residencial-eletrica"
assert result["status"] == "needs_review"
assert result["disciplines"]["eletrico"]["status"] == "needs_review"
assert (out_path / "reports" / "adapter-result.json").is_file()
'''
    completed = subprocess.run(
        [sys.executable, "-c", script, str(ROOT), str(spec_path), str(tmp_path / "run")],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
