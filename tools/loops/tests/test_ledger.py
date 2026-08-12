import json
from dataclasses import fields
from pathlib import Path

import pytest

from tools.loops.ledger import Ledger
from tools.loops.models import (
    Citation,
    EvidenceBundle,
    LoopPhase,
    LoopState,
    SourceRecord,
    TaskCandidate,
    VALID_TRANSITIONS,
)


def make_state(phase=LoopPhase.PREFLIGHT):
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
        evidence=None,
        attempts={},
        artifacts={},
        outcome=None,
        last_error=None,
    )


def assert_essential_schema(document):
    assert document["schema_version"] == 1
    assert set(document) == {
        "schema_version", "loop_id", "mode", "iteration", "phase", "task",
        "base_commit", "worktree", "evidence", "attempts", "artifacts",
        "outcome", "last_error",
    }
    assert document["phase"] in {phase.value for phase in LoopPhase}
    assert document["mode"] in {"dry-run", "supervised", "autonomous"}
    assert isinstance(document["attempts"], dict)
    assert isinstance(document["artifacts"], dict)


def test_state_round_trip_preserves_enum_and_empty_collections(tmp_path):
    state = make_state()
    restored = LoopState.from_dict(LoopState.from_dict(state.to_dict()).to_dict())

    assert restored == state
    assert restored.phase is LoopPhase.PREFLIGHT
    assert restored.task.evidence_paths == ()
    assert restored.task.suggested_tests == ()
    assert restored.attempts == {}
    assert restored.artifacts == {}


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


def test_invalid_transition_is_reported_without_mutating_state(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, make_state())
    ledger.save()
    before = path.read_bytes()

    with pytest.raises(ValueError, match="invalid transition"):
        ledger.transition(LoopPhase.PREFLIGHT, LoopPhase.REVIEW)

    assert path.read_bytes() == before
    assert ledger.state.phase is LoopPhase.PREFLIGHT
