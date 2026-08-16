import json
import subprocess
import sys
from pathlib import Path

from project_loop import (__file__ as PROJECT_LOOP_FILE, describe_adapters,
                          run_project, run_project_file, verify_project_run)


ROOT = Path(__file__).resolve().parents[3]
SPEC = (ROOT.parent.parent / "projects" / "casa-residencial-sintetica"
        / "project-spec.json")
GENERIC_ARTIFACT_PATHS = {
    "input/spec.json",
    "reports/preflight.json",
    "reports/disciplinas.json",
    "reports/adapter-result.json",
}
FORBIDDEN_ARTIFACT_MARKERS = (".ifc", ".fcstd", ".pdf", ".svg", ".dxf",
                              "freecad")
DISCIPLINE_STATUSES = {
    "passed", "needs_review", "blocked", "failed", "not_requested",
    "not_available",
}
DELIVERABLE_STATUSES = {
    "generated", "not_requested", "not_available", "blocked", "failed",
}
COORDINATION_STATUSES = {
    "generated", "not_run", "not_available", "blocked", "failed",
}


def test_universal_core_has_no_direct_galpao_engine_import():
    source = Path(PROJECT_LOOP_FILE).read_text(encoding="utf-8")
    assert "import galpao_turnkey" not in source
    assert "from galpao_turnkey" not in source
    assert "reports/turnkey.txt" not in source


def test_galpao_adapter_is_directly_importable_in_a_fresh_process():
    script = r'''
import sys

sys.path.insert(0, sys.argv[1])
import galpao_adapter

assert callable(galpao_adapter.register_galpao_adapter)
'''
    completed = subprocess.run(
        [sys.executable, "-c", script, str(ROOT)],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_residential_adapter_is_registered_with_declared_capabilities():
    capabilities = [item for item in describe_adapters()
                    if item["name"] == "casa-residencial-sintetica"]
    assert capabilities, (
        "adaptador casa-residencial-sintetica nao registrado; "
        "adaptadores registrados: %r"
        % [item.get("name") for item in describe_adapters()]
    )
    capability = capabilities[0]
    assert capability["project_types"] == ["residencial"]
    assert capability["disciplines"] == ["arquitetura", "eletrico", "hidraulica"]
    assert capability["deliverables"] == ["report"]


def test_residential_spec_runs_with_honest_optional_states(tmp_path):
    result = run_project_file(SPEC, tmp_path,
                              options={"generate_ifc": False})
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
    paths = {item["path"] for item in result["artifacts"]}
    assert paths <= GENERIC_ARTIFACT_PATHS, (
        "hooks ausentes nao podem produzir artefatos fora do conjunto "
        "generico esperado: %r" % sorted(paths - GENERIC_ARTIFACT_PATHS)
    )
    assert all(
        not any(marker in path.casefold()
                for marker in FORBIDDEN_ARTIFACT_MARKERS)
        for path in paths
    ), "artefato de IFC/FreeCAD/PDF/SVG/DXF encontrado: %r" % sorted(paths)


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


def test_residential_manifest_matches_universal_contract(
        tmp_path, turnkey_fixture):
    house_dir = tmp_path / "house"
    house = run_project_file(SPEC, house_dir,
                             options={"generate_ifc": False})
    galpao_dir = tmp_path / "galpao"
    galpao_spec = {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "galpao-fixture", "type": "galpao"},
        "turnkey": turnkey_fixture(),
    }
    galpao = run_project(galpao_spec, galpao_dir,
                         options={"generate_ifc": False})
    _assert_universal_manifest_contract(house)
    _assert_universal_manifest_contract(galpao)
    assert verify_project_run(house_dir)["ok"] is True
    assert verify_project_run(galpao_dir)["ok"] is True


def test_residential_artifact_tampering_is_detected(tmp_path):
    result = run_project_file(SPEC, tmp_path,
                              options={"generate_ifc": False})
    matching = [item for item in result["artifacts"]
                if item["path"] == "reports/adapter-result.json"]
    assert matching, (
        "artefato de resultado do adaptador nao foi registrado; artefatos: %r"
        % result["artifacts"]
    )
    artifact = matching[0]
    (tmp_path / artifact["path"]).write_text("adulterado", encoding="utf-8")
    verification = verify_project_run(tmp_path)
    assert verification["ok"] is False
    assert any(item["code"] == "artifact_hash_mismatch"
               and item["path"] == artifact["path"]
               for item in verification["errors"])


def _assert_universal_manifest_contract(manifest):
    expected = {"schema", "adapter", "adapter_capabilities", "disciplines",
                "deliverables", "coordination", "artifacts", "verification"}
    assert expected <= manifest.keys()
    assert isinstance(manifest["schema"], str)
    assert isinstance(manifest["adapter"], str)
    assert isinstance(manifest["project_type"], str)

    capabilities = manifest["adapter_capabilities"]
    assert isinstance(capabilities, dict)
    assert isinstance(capabilities["project_types"], list)
    assert isinstance(capabilities["disciplines"], list)
    assert isinstance(capabilities["deliverables"], list)

    disciplines = manifest["disciplines"]
    assert isinstance(disciplines, dict)
    assert all(isinstance(name, str) for name in disciplines)
    assert all(isinstance(record, dict) for record in disciplines.values())
    assert all(record["status"] in DISCIPLINE_STATUSES
               for record in disciplines.values())

    deliverables = manifest["deliverables"]
    assert isinstance(deliverables, dict)
    assert all(isinstance(name, str) for name in deliverables)
    assert all(isinstance(record, dict) for record in deliverables.values())
    assert all(record["status"] in DELIVERABLE_STATUSES
               for record in deliverables.values())

    coordination = manifest["coordination"]
    assert isinstance(coordination, dict)
    assert coordination["status"] in COORDINATION_STATUSES

    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    assert all(isinstance(record, dict) for record in artifacts)
    assert all(isinstance(record["path"], str)
               and not Path(record["path"]).is_absolute()
               for record in artifacts)

    verification = manifest["verification"]
    assert isinstance(verification, dict)
    assert isinstance(verification["ok"], bool)
    assert isinstance(verification["errors"], list)
