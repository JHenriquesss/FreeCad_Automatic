import json
from dataclasses import replace
from pathlib import Path

import pytest

import tools.loops.ledger as ledger_module
from tools.loops.ledger import Ledger
from tools.loops.models import (
    Citation,
    EvidenceBundle,
    FailureRecord,
    LoopPhase,
    LoopState,
    SourceRecord,
    TaskCandidate,
    VALID_TRANSITIONS,
)


def make_state(phase=LoopPhase.PREFLIGHT, *, evidence=None, failure=None):
    return LoopState(
        schema_version=1,
        loop_id="2026-08-12T0000Z",
        mode="supervised",
        iteration=1,
        phase=phase,
        task=TaskCandidate(
            id="T-0001",
            title="ledger",
            discipline="geral",
            origin="brief",
            priority=0,
            evidence_paths=(),
            suggested_tests=(),
        ),
        base_commit="abc123",
        worktree=None,
        evidence=evidence,
        attempts={},
        artifacts={},
        outcome=None,
        last_error=None,
        failure=failure,
    )


def make_evidence():
    return EvidenceBundle(
        notebook_id="nb-1",
        source_ids=("src-1",),
        sources=(
            SourceRecord(
                source_id="src-1",
                title="Norma teste",
                status=2,
                notebook_id="nb-1",
                local_path="fontes/norma.pdf",
                local_hash="sha256:abc",
            ),
        ),
        question="Qual requisito deve ser verificado?",
        answer="O requisito de teste deve ser verificado.",
        conversation_id="conv-1",
        citations=(Citation("1", "src-1", "trecho curto"),),
        retrieved_at="2026-08-12T00:00:00Z",
        manual_request=None,
    )


def assert_essential_schema(document):
    assert document["schema_version"] == 1
    assert set(document) == {
        "schema_version", "loop_id", "mode", "iteration", "phase", "task",
        "base_commit", "worktree", "evidence", "attempts", "artifacts",
        "outcome", "last_error", "failure",
    }
    assert document["phase"] in {phase.value for phase in LoopPhase}
    assert document["mode"] in {"dry-run", "supervised", "autonomous"}
    assert isinstance(document["attempts"], dict)
    assert isinstance(document["artifacts"], dict)


def test_state_round_trip_preserves_enum_and_empty_collections(tmp_path):
    state = make_state(evidence=make_evidence())
    restored = LoopState.from_dict(LoopState.from_dict(state.to_dict()).to_dict())

    assert restored == state
    assert restored.phase is LoopPhase.PREFLIGHT
    assert restored.task.evidence_paths == ()
    assert restored.task.suggested_tests == ()
    assert restored.attempts == {}
    assert restored.artifacts == {}
    assert restored.evidence.sources[0].local_hash == "sha256:abc"
    assert restored.failure is None


def test_ledger_transition_requires_expected_phase(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, make_state())
    ledger.save()

    with pytest.raises(ValueError, match="expected phase"):
        ledger.transition(LoopPhase.DISCOVER, LoopPhase.RESEARCH)

    assert Ledger.load(path).state.phase is LoopPhase.PREFLIGHT


def test_ledger_save_is_valid_json_after_replacement(tmp_path):
    path = tmp_path / "ledger.json"
    Ledger(path, make_state()).save()

    document = json.loads(path.read_text(encoding="utf-8"))
    assert_essential_schema(document)
    assert not list(tmp_path.glob("*.tmp"))


def test_invalid_iteration_is_rejected_on_load_and_save(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, make_state())
    ledger.save()
    invalid_document = ledger.state.to_dict()
    invalid_document["iteration"] = 0
    path.write_text(json.dumps(invalid_document), encoding="utf-8")

    with pytest.raises(ValueError, match="schema"):
        Ledger.load(path)

    candidate = make_state()
    candidate.iteration = 0
    with pytest.raises(ValueError, match="schema"):
        ledger.save(candidate)
    assert ledger.state.iteration == 1


@pytest.mark.parametrize("invalid_attempts", [{"red": -1}, {"red": "1"}, {"red": True}, []])
def test_invalid_attempts_are_rejected_on_load_and_save(tmp_path, invalid_attempts):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, make_state())
    ledger.save()
    invalid_document = ledger.state.to_dict()
    invalid_document["attempts"] = invalid_attempts
    path.write_text(json.dumps(invalid_document), encoding="utf-8")

    with pytest.raises(ValueError, match="schema"):
        Ledger.load(path)

    candidate = make_state()
    candidate.attempts = invalid_attempts
    with pytest.raises(ValueError, match="schema"):
        ledger.save(candidate)
    assert ledger.state.attempts == {}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("loop_id", 7),
        ("mode", 7),
        ("phase", 7),
        ("base_commit", 7),
        ("worktree", 7),
        ("artifacts", {"log": 7}),
        ("outcome", 7),
        ("last_error", 7),
    ],
)
def test_invalid_top_level_types_are_rejected_on_load_and_save(tmp_path, field, value):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, make_state())
    ledger.save()
    invalid_document = ledger.state.to_dict()
    invalid_document[field] = value
    path.write_text(json.dumps(invalid_document), encoding="utf-8")

    with pytest.raises(ValueError, match="schema"):
        Ledger.load(path)

    candidate = make_state()
    setattr(candidate, field, value)
    with pytest.raises(ValueError, match="schema"):
        ledger.save(candidate)
    assert ledger.state.to_dict() == make_state().to_dict()


def test_invalid_task_and_evidence_structures_are_rejected_on_load_and_save(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, make_state(evidence=make_evidence()))
    ledger.save()
    valid_document = ledger.state.to_dict()
    invalid_documents = []

    invalid_task = json.loads(json.dumps(valid_document))
    invalid_task["task"]["evidence_paths"] = [7]
    invalid_documents.append(invalid_task)

    invalid_evidence = json.loads(json.dumps(valid_document))
    invalid_evidence["evidence"]["sources"][0]["status"] = "2"
    invalid_documents.append(invalid_evidence)

    invalid_citation = json.loads(json.dumps(valid_document))
    invalid_citation["evidence"]["citations"][0]["cited_text"] = 7
    invalid_documents.append(invalid_citation)

    for invalid_document in invalid_documents:
        path.write_text(json.dumps(invalid_document), encoding="utf-8")
        with pytest.raises(ValueError, match="schema"):
            Ledger.load(path)

    bad_task = make_state(evidence=make_evidence())
    bad_task.task = replace(bad_task.task, evidence_paths=(7,))
    with pytest.raises(ValueError, match="schema"):
        ledger.save(bad_task)

    bad_evidence = make_state(evidence=make_evidence())
    bad_source = replace(bad_evidence.evidence.sources[0], status="2")
    bad_evidence.evidence = replace(bad_evidence.evidence, sources=(bad_source,))
    with pytest.raises(ValueError, match="schema"):
        ledger.save(bad_evidence)


def test_record_failure_persists_reason_command_and_artifacts(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, make_state())
    ledger.save()

    ledger.record_failure(
        "command_timeout",
        ("python", "-m", "pytest"),
        ("artifacts/stdout.txt", "artifacts/stderr.txt"),
        "pytest exceeded the command timeout",
    )

    assert ledger.state.phase is LoopPhase.PREFLIGHT
    assert ledger.state.failure == FailureRecord(
        reason="command_timeout",
        command=("python", "-m", "pytest"),
        artifacts=("artifacts/stdout.txt", "artifacts/stderr.txt"),
        detail="pytest exceeded the command timeout",
    )
    restored = Ledger.load(path)
    assert restored.state.failure == ledger.state.failure
    assert restored.state.phase is LoopPhase.PREFLIGHT


@pytest.mark.parametrize(
    ("command", "artifacts"),
    [
        ("python -m pytest", ("artifacts/stdout.txt",)),
        (("python", "-m", "pytest"), "artifacts/stdout.txt"),
    ],
)
def test_record_failure_rejects_scalar_collections_without_mutating_ledger(
    tmp_path, command, artifacts
):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, make_state())
    ledger.save()
    before = path.read_bytes()

    with pytest.raises(ValueError, match="must be an array"):
        ledger.record_failure("command_timeout", command, artifacts)

    assert ledger.state.failure is None
    assert ledger.state.phase is LoopPhase.PREFLIGHT
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "failure",
    [
        {"reason": 7, "command": None, "artifacts": [], "detail": None},
        {
            "reason": "command_timeout",
            "command": ["python", 7],
            "artifacts": [],
            "detail": None,
        },
        {
            "reason": "command_timeout",
            "command": None,
            "artifacts": [7],
            "detail": None,
        },
    ],
)
def test_invalid_failure_structure_is_rejected_on_load_and_save(tmp_path, failure):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, make_state())
    ledger.save()
    invalid_document = ledger.state.to_dict()
    invalid_document["failure"] = failure
    path.write_text(json.dumps(invalid_document), encoding="utf-8")

    with pytest.raises(ValueError, match="schema"):
        Ledger.load(path)

    candidate = make_state(failure=failure)
    with pytest.raises(ValueError, match="schema"):
        ledger.save(candidate)
    assert ledger.state.failure is None


def test_save_updates_state_only_after_atomic_replacement(tmp_path, monkeypatch):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, make_state())
    ledger.save()
    before = path.read_bytes()
    candidate = replace(ledger.state, phase=LoopPhase.DISCOVER)

    def fail_replace(source, destination):
        raise OSError("replacement failed")

    monkeypatch.setattr(ledger_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replacement failed"):
        ledger.save(candidate)

    assert ledger.state.phase is LoopPhase.PREFLIGHT
    assert path.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))


def test_invalid_transition_is_reported_without_mutating_state(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, make_state())
    ledger.save()
    before = path.read_bytes()

    with pytest.raises(ValueError, match="invalid transition"):
        ledger.transition(LoopPhase.PREFLIGHT, LoopPhase.REVIEW)

    assert path.read_bytes() == before
    assert ledger.state.phase is LoopPhase.PREFLIGHT
