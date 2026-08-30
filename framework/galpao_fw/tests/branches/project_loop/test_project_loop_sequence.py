import json

import pytest

from project_loop import run_project_sequence


def test_project_sequence_runs_explicit_steps_and_persists_lineage(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    root = tmp_path / "sequence"
    result = run_project_sequence(
        turnkey_fixture_with_hvac_and_hydraulic,
        root,
        steps=[{
            "updates": {
                "incendio.iluminacao_emergencia.fluxo_bloco_lm": 400.0,
            },
            "resolutions": [{"issue_id": "CLH-001", "status": "reviewed"}],
        }],
        options={"generate_ifc": False},
    )

    report = result["sequence"]
    persisted = json.loads(
        (root / "project-sequence.json").read_text(encoding="utf-8"))

    assert len(result["runs"]) == 2
    assert report["completed_iterations"] == 2
    assert report["status"] == "needs_review"
    assert [item["path"] for item in report["iterations"]] == [
        "iteration-001", "iteration-002"]
    assert report["iterations"][1]["parent_run_id"] == \
        report["iterations"][0]["run_id"]
    assert result["runs"][1]["changes"] == {
        "incendio.iluminacao_emergencia.fluxo_bloco_lm": 400.0}
    assert result["runs"][1]["verification"]["ok"] is True
    assert persisted["schema"] == "freecad-automatic/project-sequence"
    assert persisted["errors"] == []


def test_project_sequence_rejects_invalid_plan_before_creating_output(
        tmp_path, turnkey_fixture):
    root = tmp_path / "invalid-sequence"

    with pytest.raises(ValueError, match="updates deve ser um objeto"):
        run_project_sequence(
            turnkey_fixture(), root,
            steps=[{"updates": ["nao-e-mapa"]}],
            options={"generate_ifc": False},
        )

    assert not root.exists()
