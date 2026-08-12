import json
import os
from pathlib import Path

from .models import LoopPhase, LoopState, VALID_TRANSITIONS


class Ledger:
    def __init__(self, path, state):
        self.path = Path(path)
        self.state = state
        self._validate(self.state.to_dict())

    @classmethod
    def load(cls, path):
        ledger_path = Path(path)
        document = json.loads(ledger_path.read_text(encoding="utf-8"))
        cls._validate(document)
        return cls(ledger_path, LoopState.from_dict(document))

    def save(self, state=None):
        if state is not None:
            self._validate(state.to_dict())
            self.state = state
        document = self.state.to_dict()
        self._validate(document)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.tmp")
        try:
            temporary.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def transition(self, expected_phase, next_phase):
        expected = LoopPhase(expected_phase)
        target = LoopPhase(next_phase)
        if self.state.phase is not expected:
            raise ValueError(f"expected phase {expected.value}, got {self.state.phase.value}")
        if target.value not in VALID_TRANSITIONS[expected.value]:
            raise ValueError(f"invalid transition {expected.value} -> {target.value}")
        self.state.phase = target
        self.save()

    @staticmethod
    def _validate(document):
        required = {"schema_version", "loop_id", "mode", "iteration", "phase", "task",
                    "base_commit", "worktree", "evidence", "attempts", "artifacts",
                    "outcome", "last_error"}
        if not isinstance(document, dict) or set(document) != required:
            raise ValueError("ledger document does not match schema")
        if document["schema_version"] != 1 or document["mode"] not in {"dry-run", "supervised", "autonomous"}:
            raise ValueError("ledger document does not match schema")
        if document["phase"] not in {phase.value for phase in LoopPhase}:
            raise ValueError("ledger document does not match schema")
        if not isinstance(document["attempts"], dict) or not isinstance(document["artifacts"], dict):
            raise ValueError("ledger document does not match schema")
