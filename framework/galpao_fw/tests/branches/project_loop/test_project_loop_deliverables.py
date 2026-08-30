import json
import os

import ifc_emit

from project_loop import (_relative_runtime_paths, run_project,
                          verify_project_run)


def test_coordination_artifacts_are_real_and_manifest_paths_relative(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    result = run_project(turnkey_fixture_with_hvac_and_hydraulic, tmp_path,
                         options={"generate_ifc": False})
    assert (tmp_path / "coordination" / "clash.json").exists()
    assert (tmp_path / "coordination" / "pendencias.bcf.json").exists()
    assert result["coordination"]["n_revisar"] >= 1
    for artifact in result["artifacts"]:
        assert not os.path.isabs(artifact["path"])
        assert len(artifact["sha256"]) == 64


def test_ifc_dependency_is_explicit_instead_of_false_success(tmp_path, turnkey_fixture):
    result = run_project(turnkey_fixture(), tmp_path,
                         options={"generate_ifc": True})
    if ifc_emit.disponivel():
        assert result["deliverables"]["ifc"]["status"] == "generated"
        assert any(a["path"].endswith("turnkey_federado.ifc")
                   for a in result["artifacts"])
        assert all(not a["path"].startswith("bim/bim/")
                   for a in result["artifacts"])
        assert any(a["path"] == "bim/turnkey_federado.ifc"
                   for a in result["artifacts"])
    else:
        assert result["deliverables"]["ifc"]["status"] == "not_available"
        assert result["status"] == "needs_review"


def test_optional_deliverable_metadata_paths_are_relative(tmp_path):
    drawing = tmp_path / "drawings" / "CADERNO.pdf"
    drawing.parent.mkdir()
    drawing.write_bytes(b"pdf")
    raw = {
        "path": str(drawing),
        "status": {"incendio": {
            "arquivos": [str(drawing)], "fcstd": str(drawing)}},
    }

    normalized = _relative_runtime_paths(raw, tmp_path)

    assert normalized == {
        "path": "drawings/CADERNO.pdf",
        "status": {"incendio": {
            "arquivos": ["drawings/CADERNO.pdf"],
            "fcstd": "drawings/CADERNO.pdf",
        }},
    }
    assert all(not os.path.isabs(value)
               for value in (normalized["path"],
                             normalized["status"]["incendio"]["fcstd"],
                             normalized["status"]["incendio"]["arquivos"][0]))


def test_verify_project_run_accepts_intact_manifest_and_artifacts(
        tmp_path, turnkey_fixture):
    result = run_project(turnkey_fixture(), tmp_path,
                         options={"generate_ifc": False})

    verification = verify_project_run(tmp_path)

    assert verification["ok"] is True
    assert verification["run_id"] == result["run_id"]
    assert verification["checked_artifacts"] == len(result["artifacts"])
    assert verification["valid_artifacts"] == verification["checked_artifacts"]
    assert verification["errors"] == []


def test_project_manifest_persists_post_run_verification(tmp_path,
                                                          turnkey_fixture):
    result = run_project(turnkey_fixture(), tmp_path,
                         options={"generate_ifc": False})

    persisted = json.loads(
        (tmp_path / "project-run.json").read_text(encoding="utf-8"))

    assert result["verification"]["ok"] is True
    assert persisted["verification"]["ok"] is True
    assert persisted["verification"]["valid_artifacts"] == len(
        persisted["artifacts"])
    assert "run_dir" not in persisted["verification"]


def test_verify_project_run_detects_changed_artifact_hash(tmp_path,
                                                           turnkey_fixture):
    run_project(turnkey_fixture(), tmp_path,
                options={"generate_ifc": False})
    artifact = next(item for item in json.loads(
        (tmp_path / "project-run.json").read_text(encoding="utf-8"))["artifacts"]
                     if item["sha256"])
    (tmp_path / artifact["path"]).write_text("adulterado", encoding="utf-8")

    verification = verify_project_run(tmp_path)

    assert verification["ok"] is False
    assert any(item["code"] == "artifact_hash_mismatch"
               and item["path"] == artifact["path"]
               for item in verification["errors"])
