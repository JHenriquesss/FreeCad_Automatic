from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class LoopPhase(StrEnum):
    PREFLIGHT = "preflight"
    DISCOVER = "discover"
    RESEARCH = "research"
    PLAN = "plan"
    RED = "red"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    REVIEW = "review"
    RECORD = "record"
    PROMOTE = "promote"
    PARK = "park"


VALID_TRANSITIONS = {
    "preflight": {"discover", "park"},
    "discover": {"research", "park"},
    "research": {"plan", "park"},
    "plan": {"red", "park"},
    "red": {"implement", "park"},
    "implement": {"verify", "park"},
    "verify": {"review", "park"},
    "review": {"record", "park"},
    "record": {"promote", "park"},
    "promote": set(),
    "park": {"discover", "research"},
}


@dataclass(frozen=True)
class TaskCandidate:
    id: str
    title: str
    discipline: str
    origin: str
    priority: int
    evidence_paths: tuple[str, ...]
    suggested_tests: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "discipline": self.discipline,
                "origin": self.origin, "priority": self.priority,
                "evidence_paths": list(self.evidence_paths) if isinstance(self.evidence_paths, tuple) else self.evidence_paths,
                "suggested_tests": list(self.suggested_tests) if isinstance(self.suggested_tests, tuple) else self.suggested_tests}

    @classmethod
    def from_dict(cls, value):
        return cls(**{**value, "evidence_paths": tuple(value["evidence_paths"]),
                      "suggested_tests": tuple(value["suggested_tests"])})


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    title: str
    status: int
    notebook_id: str
    local_path: str | None = None
    local_hash: str | None = None

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, value):
        return cls(**value)


@dataclass(frozen=True)
class Citation:
    number: str
    source_id: str
    cited_text: str

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, value):
        return cls(**value)


@dataclass(frozen=True)
class EvidenceBundle:
    notebook_id: str
    source_ids: tuple[str, ...]
    sources: tuple[SourceRecord, ...]
    question: str
    answer: str
    conversation_id: str | None
    citations: tuple[Citation, ...]
    retrieved_at: str
    manual_request: str | None = None

    def to_dict(self):
        return {"notebook_id": self.notebook_id, "source_ids": list(self.source_ids),
                "sources": [item.to_dict() for item in self.sources],
                "question": self.question, "answer": self.answer,
                "conversation_id": self.conversation_id,
                "citations": [item.to_dict() for item in self.citations],
                "retrieved_at": self.retrieved_at, "manual_request": self.manual_request}

    @classmethod
    def from_dict(cls, value):
        return cls(**{**value, "source_ids": tuple(value["source_ids"]),
                      "sources": tuple(SourceRecord.from_dict(item) for item in value["sources"]),
                      "citations": tuple(Citation.from_dict(item) for item in value["citations"])})


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    cwd: str
    returncode: int
    duration_seconds: float
    stdout: str
    stderr: str

    def to_dict(self):
        return {**self.__dict__, "argv": list(self.argv)}

    @classmethod
    def from_dict(cls, value):
        return cls(**{**value, "argv": tuple(value["argv"])})


@dataclass(frozen=True)
class FailureRecord:
    reason: str
    command: tuple[str, ...] | None
    artifacts: tuple[str, ...]
    detail: str | None = None

    def to_dict(self):
        return {
            "reason": self.reason,
            "command": list(self.command) if isinstance(self.command, tuple) else self.command,
            "artifacts": list(self.artifacts) if isinstance(self.artifacts, tuple) else self.artifacts,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, value):
        return cls(
            **{
                **value,
                "command": tuple(value["command"]) if value["command"] is not None else None,
                "artifacts": tuple(value["artifacts"]),
            }
        )


@dataclass
class LoopState:
    schema_version: int
    loop_id: str
    mode: str
    iteration: int
    phase: LoopPhase
    task: TaskCandidate | None
    base_commit: str
    worktree: str | None
    evidence: EvidenceBundle | None
    attempts: dict[str, int]
    artifacts: dict[str, str]
    outcome: str | None
    last_error: str | None
    failure: FailureRecord | None = None

    def to_dict(self):
        phase = self.phase.value if isinstance(self.phase, LoopPhase) else self.phase
        return {"schema_version": self.schema_version, "loop_id": self.loop_id,
                "mode": self.mode, "iteration": self.iteration,
                "phase": phase,
                "task": self.task.to_dict() if isinstance(self.task, TaskCandidate) else self.task,
                "base_commit": self.base_commit, "worktree": self.worktree,
                "evidence": self.evidence.to_dict() if isinstance(self.evidence, EvidenceBundle) else self.evidence,
                "attempts": dict(self.attempts) if isinstance(self.attempts, dict) else self.attempts,
                "artifacts": dict(self.artifacts) if isinstance(self.artifacts, dict) else self.artifacts,
                "outcome": self.outcome, "last_error": self.last_error,
                "failure": self.failure.to_dict() if isinstance(self.failure, FailureRecord) else self.failure}

    @classmethod
    def from_dict(cls, value):
        return cls(**{**value, "phase": LoopPhase(value["phase"]),
                      "task": TaskCandidate.from_dict(value["task"]) if value["task"] else None,
                      "evidence": EvidenceBundle.from_dict(value["evidence"]) if value["evidence"] else None,
                      "failure": FailureRecord.from_dict(value["failure"]) if value["failure"] else None})
