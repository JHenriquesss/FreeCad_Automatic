import copy
import json

import pytest

from coordination_review import (
    build_review_report,
    classify_pendencias,
    collect_approved_updates,
    derive_affected_disciplines,
    reconcile_pendencias,
    validate_resolution_plan,
)


def _parent_manifest():
    return {
        "run_id": "parent-001",
        "project_id": "review-fixture",
        "input": {
            "turnkey": {
                "geometria": {"pe_direito": 6.0},
                "eletrico": {"cargas": {"iluminacao_kW": 20.0}},
                "aco": {"perfil": {"serie": "W"}},
            },
        },
        "options": {"required_disciplines": ["eletrico", "aco"]},
    }


def _pendencias():
    return [
        {
            "id": "CLH-001",
            "guid": "guid-expected",
            "esperado": True,
            "disciplina_a": "concreto",
            "disciplina_b": "eletrico",
        },
        {
            "id": "CLH-002",
            "guid": "guid-real",
            "esperado": False,
            "disciplina_a": "aco",
            "disciplina_b": "eletrico",
        },
        {
            "id": "CLH-003",
            "guid": "guid-inconclusive",
            "esperado": False,
            "disciplina_a": "hidraulica",
            "disciplina_b": "concreto",
        },
    ]


def _approved_plan(*decisions):
    return {
        "schema": "freecad-automatic/coordination-resolution-plan",
        "schema_version": 1,
        "parent_run_id": "parent-001",
        "project_id": "review-fixture",
        "decisions": list(decisions),
    }


def _decision(issue_id, classification, *, approval_status="approved",
              updates=None, approved=True):
    value = {
        "issue_id": issue_id,
        "classification": classification,
        "approval_status": approval_status,
        "updates": updates or {},
        "note": "decisão registrada",
    }
    if approved:
        value.update({
            "approved_by": "engenheiro-responsavel",
            "approved_at": "2026-08-15T12:00:00Z",
        })
    return value


def test_classification_is_audit_safe_and_does_not_mutate_source():
    source = _pendencias()
    classified = classify_pendencias(source)

    assert [item["classification"] for item in classified] == [
        "expected", "inconclusive", "inconclusive"]
    assert all("classification" not in item for item in source)


def test_validation_and_updates_accept_only_approved_existing_paths():
    plan = _approved_plan(
        _decision("CLH-001", "expected"),
        _decision(
            "CLH-002", "real",
            updates={"turnkey.eletrico.cargas.iluminacao_kW": 21.0}),
    )

    normalized = validate_resolution_plan(
        plan, _pendencias(), _parent_manifest())

    assert normalized["schema_version"] == 1
    assert collect_approved_updates(normalized) == {
        "turnkey.eletrico.cargas.iluminacao_kW": 21.0}
    assert derive_affected_disciplines(
        normalized, ["eletrico", "aco"]) == ["eletrico"]


@pytest.mark.parametrize("approval_status", ["pending", "rejected"])
def test_unapproved_update_is_rejected_before_execution(approval_status):
    plan = _approved_plan(_decision(
        "CLH-002", "real", approval_status=approval_status,
        updates={"turnkey.eletrico.cargas.iluminacao_kW": 21.0},
        approved=False,
    ))

    with pytest.raises(ValueError, match="approved"):
        validate_resolution_plan(plan, _pendencias(), _parent_manifest())


def test_approved_real_requires_engineer_and_applicable_update():
    missing_approval = _approved_plan(_decision(
        "CLH-002", "real", updates={
            "turnkey.eletrico.cargas.iluminacao_kW": 21.0}, approved=False))
    no_update = _approved_plan(_decision("CLH-002", "real", updates={}))

    with pytest.raises(ValueError, match="approved_by"):
        validate_resolution_plan(
            missing_approval, _pendencias(), _parent_manifest())
    with pytest.raises(ValueError, match="update"):
        validate_resolution_plan(no_update, _pendencias(), _parent_manifest())


@pytest.mark.parametrize("field,value", [
    ("parent_run_id", "other-parent"),
    ("project_id", "other-project"),
])
def test_plan_must_match_parent(field, value):
    plan = _approved_plan()
    plan[field] = value

    with pytest.raises(ValueError, match="corresponde"):
        validate_resolution_plan(plan, _pendencias(), _parent_manifest())


def test_unknown_and_duplicate_issue_ids_are_rejected():
    unknown = _approved_plan(_decision("CLH-999", "expected"))
    duplicate = _approved_plan(
        _decision("CLH-001", "expected"),
        _decision("CLH-001", "expected"),
    )

    with pytest.raises(ValueError, match="issue_id"):
        validate_resolution_plan(unknown, _pendencias(), _parent_manifest())
    with pytest.raises(ValueError, match="duplicad"):
        validate_resolution_plan(duplicate, _pendencias(), _parent_manifest())


def test_reconciliation_uses_guid_and_distinguishes_open_states():
    parent = _pendencias()
    child = [
        copy.deepcopy(parent[0]),
        {
            "id": "CLH-004",
            "guid": "guid-new",
            "esperado": False,
            "disciplina_a": "incendio",
            "disciplina_b": "eletrico",
        },
    ]
    plan = _approved_plan(
        _decision("CLH-001", "expected"),
        _decision("CLH-002", "real", updates={
            "turnkey.eletrico.cargas.iluminacao_kW": 21.0}),
    )

    reconciliation = reconcile_pendencias(parent, child, plan)
    states = {item["guid"]: item["state"]
              for item in reconciliation["items"]}

    assert states == {
        "guid-expected": "accepted_expected",
        "guid-real": "resolved",
        "guid-inconclusive": "inconclusive_open",
        "guid-new": "new_open",
    }
    assert reconciliation["open_issue_ids"] == ["CLH-003", "CLH-004"]


def test_reconciliation_accepts_legacy_duplicate_guids_by_occurrence():
    parent = [
        {
            "id": "CLH-001",
            "guid": "legacy-guid",
            "esperado": True,
            "disciplina_a": "concreto",
            "disciplina_b": "eletrico",
        },
        {
            "id": "CLH-002",
            "guid": "legacy-guid",
            "esperado": False,
            "disciplina_a": "aco",
            "disciplina_b": "eletrico",
        },
    ]
    child = copy.deepcopy(parent)
    plan = _approved_plan(
        _decision("CLH-001", "expected"),
        _decision("CLH-002", "real", updates={
            "turnkey.eletrico.cargas.iluminacao_kW": 21.0}),
    )

    reconciliation = reconcile_pendencias(parent, child, plan)

    assert [item["state"] for item in reconciliation["items"]] == [
        "accepted_expected", "reopened"]
    assert reconciliation["open_issue_ids"] == ["CLH-002"]


def test_persistent_real_is_reopened_and_blocks_approval():
    parent = _pendencias()[:2]
    child = copy.deepcopy(parent)
    plan = _approved_plan(_decision(
        "CLH-002", "real", updates={
            "turnkey.eletrico.cargas.iluminacao_kW": 21.0}))
    manifest = {
        "status": "passed",
        "preflight": {"ok": True, "can_execute": True},
        "disciplines": {
            "eletrico": {"status": "passed"},
            "aco": {"status": "passed"},
        },
        "options": {
            "generate_ifc": False,
            "generate_3d": False,
            "generate_2d": False,
            "generate_caderno": False,
        },
        "deliverables": {},
    }

    report = build_review_report(
        parent, child, plan, manifest=manifest,
        verification={"ok": True},
        affected_disciplines=["eletrico"],
        rerun_disciplines=["eletrico", "aco"],
        applied_updates={"turnkey.eletrico.cargas.iluminacao_kW": 21.0},
    )

    assert report["review_status"] == "needs_review"
    assert "CLH-002" in report["open_issue_ids"]
    assert report["reconciliation"]["counts"]["reopened"] == 1


def test_review_is_approved_only_after_coordination_and_requested_outputs_pass():
    parent = _pendencias()[:1]
    child = copy.deepcopy(parent)
    plan = _approved_plan(_decision("CLH-001", "expected"))
    manifest = {
        "status": "passed",
        "preflight": {"ok": True, "can_execute": True},
        "disciplines": {
            "concreto": {"status": "passed"},
            "eletrico": {"status": "passed"},
        },
        "options": {
            "generate_ifc": True,
            "generate_3d": True,
            "generate_2d": True,
            "generate_caderno": True,
        },
        "deliverables": {
            "ifc": {"status": "generated"},
            "model_3d": {"status": "generated"},
            "drawings": {"status": "generated"},
        },
    }

    report = build_review_report(
        parent, child, plan, manifest=manifest,
        verification={"ok": True, "artifact_count": 10,
                       "valid_artifacts": 10},
        affected_disciplines=[], rerun_disciplines=["concreto", "eletrico"],
    )

    assert report["review_status"] == "approved"
    assert report["reasons"] == []
    assert report["reconciliation"]["open_issue_ids"] == []


def test_missing_requested_deliverable_blocks_review_approval():
    parent = _pendencias()[:1]
    plan = _approved_plan(_decision("CLH-001", "expected"))
    manifest = {
        "status": "passed",
        "preflight": {"ok": True, "can_execute": True},
        "disciplines": {"concreto": {"status": "passed"}},
        "options": {"generate_ifc": True},
        "deliverables": {"ifc": {"status": "partial"}},
    }

    report = build_review_report(
        parent, parent, plan, manifest=manifest,
        verification={"ok": True},
    )

    assert report["review_status"] == "needs_review"
    assert report["missing_deliverables"] == ["ifc"]


def test_failed_child_status_cannot_be_masked_by_coordination_approval():
    parent = _pendencias()[:1]
    plan = _approved_plan(_decision("CLH-001", "expected"))
    manifest = {
        "status": "failed",
        "preflight": {"ok": True, "can_execute": True},
        "disciplines": {"concreto": {"status": "passed"}},
        "options": {},
        "deliverables": {},
    }

    report = build_review_report(
        parent, parent, plan, manifest=manifest,
        verification={"ok": True},
    )

    assert report["review_status"] == "needs_review"
    assert report["native_statuses"] == {"concreto": "passed"}
