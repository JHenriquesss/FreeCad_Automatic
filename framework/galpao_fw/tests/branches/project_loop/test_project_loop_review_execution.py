import json
from pathlib import Path

import pytest

from project_loop import review_project, run_project, verify_project_run


def _plan_for_expected(first):
    coordination_dir = Path(first["_runtime_run_dir"])
    issues = json.loads((coordination_dir / "coordination" /
                         "pendencias.json").read_text(encoding="utf-8"))
    expected = next(item for item in issues if item.get("esperado") is True)
    return {
        "schema": "freecad-automatic/coordination-resolution-plan",
        "schema_version": 1,
        "parent_run_id": first["run_id"],
        "project_id": first["project_id"],
        "decisions": [{
            "issue_id": expected["id"],
            "classification": "expected",
            "approval_status": "approved",
            "approved_by": "engenheiro-responsavel",
            "approved_at": "2026-08-15T12:00:00Z",
            "affected_disciplines": [],
            "updates": {},
            "note": "montagem intencional documentada",
        }],
    }


def test_review_creates_auditable_child_and_keeps_parent_intact(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    first_dir = tmp_path / "loop-2"
    first = run_project(
        turnkey_fixture_with_hvac_and_hydraulic, first_dir,
        options={"generate_ifc": False},
    )
    plan = _plan_for_expected(first)
    child_dir = tmp_path / "loop-3"

    second = review_project(
        first, plan, out_dir=child_dir,
        options={"generate_ifc": False},
    )

    assert second["iteration"] == first["iteration"] + 1
    assert second["parent_run_id"] == first["run_id"]
    assert second["changes"] == {}
    assert second["coordination"]["review_status"] == "needs_review"
    assert (child_dir / "coordination" / "resolution-plan.json").exists()
    assert (child_dir / "coordination" / "review-report.json").exists()
    assert not (first_dir / "coordination" / "review-report.json").exists()
    assert verify_project_run(child_dir)["ok"] is True

    persisted = json.loads(
        (child_dir / "coordination" / "review-report.json").read_text(
            encoding="utf-8"))
    assert persisted["decision_count"] == 1
    assert persisted["affected_disciplines"] == []


def test_invalid_review_plan_does_not_create_child(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    first = run_project(
        turnkey_fixture_with_hvac_and_hydraulic, tmp_path / "loop-2",
        options={"generate_ifc": False},
    )
    plan = _plan_for_expected(first)
    plan["decisions"][0]["issue_id"] = "CLH-999"
    child_dir = tmp_path / "loop-3-invalid"

    with pytest.raises(ValueError, match="issue_id inexistente"):
        review_project(first, plan, out_dir=child_dir,
                       options={"generate_ifc": False})

    assert not child_dir.exists()


def test_review_applies_only_the_approved_update_to_the_child(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    spec = {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "review-update"},
        "turnkey": turnkey_fixture_with_hvac_and_hydraulic,
    }
    first = run_project(spec, tmp_path / "loop-2", options={"generate_ifc": False})
    issues = json.loads(
        (tmp_path / "loop-2" / "coordination" / "pendencias.json").read_text(
            encoding="utf-8"))
    issue = issues[0]
    plan = {
        "schema": "freecad-automatic/coordination-resolution-plan",
        "schema_version": 1,
        "parent_run_id": first["run_id"],
        "project_id": first["project_id"],
        "decisions": [{
            "issue_id": issue["id"],
            "classification": "inconclusive",
            "approval_status": "approved",
            "approved_by": "engenheiro-responsavel",
            "approved_at": "2026-08-15T12:00:00Z",
            "updates": {
                "turnkey.incendio.iluminacao_emergencia.fluxo_bloco_lm": 400,
            },
        }],
    }

    second = review_project(
        first, plan, out_dir=tmp_path / "loop-3",
        options={"generate_ifc": False},
    )

    assert second["changes"] == {
        "turnkey.incendio.iluminacao_emergencia.fluxo_bloco_lm": 400}
    assert second["input"]["turnkey"]["incendio"][
        "iluminacao_emergencia"]["fluxo_bloco_lm"] == 400
    assert first["input"]["turnkey"]["incendio"][
        "iluminacao_emergencia"]["fluxo_bloco_lm"] == 350.0


def test_review_includes_explicitly_affected_discipline_in_child_scope(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    first = run_project(
        turnkey_fixture_with_hvac_and_hydraulic, tmp_path / "loop-2",
        options={"required_disciplines": ["concreto", "eletrico"],
                 "generate_ifc": False},
    )
    issues = json.loads(
        (tmp_path / "loop-2" / "coordination" / "pendencias.json").read_text(
            encoding="utf-8"))
    issue = issues[0]
    plan = {
        "schema": "freecad-automatic/coordination-resolution-plan",
        "schema_version": 1,
        "parent_run_id": first["run_id"],
        "project_id": first["project_id"],
        "decisions": [{
            "issue_id": issue["id"],
            "classification": "expected",
            "approval_status": "approved",
            "approved_by": "engenheiro-responsavel",
            "approved_at": "2026-08-15T12:00:00Z",
            "affected_disciplines": ["aco"],
            "updates": {},
        }],
    }

    second = review_project(
        first, plan, out_dir=tmp_path / "loop-3",
        options={"generate_ifc": False},
    )

    assert "aco" in second["options"]["required_disciplines"]
    assert "aco" in second["coordination"]["affected_disciplines"]
    assert "aco" in second["coordination"]["rerun_disciplines"]
