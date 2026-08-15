import json
import subprocess
import sys
from pathlib import Path

from project_loop import (describe_adapters, run_project, run_project_file,
                          verify_project_run)


ROOT = Path(__file__).resolve().parents[3]
SPEC = (ROOT.parent.parent / "projects" / "casa-residencial-sintetica"
        / "project-spec.json")


def test_residential_adapter_is_registered_with_declared_capabilities():
    capability = next(item for item in describe_adapters()
                      if item["name"] == "casa-residencial-sintetica")
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
