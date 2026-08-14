"""Local, read-only review gates for an agent result."""

from __future__ import annotations

from dataclasses import dataclass
import re


_NEW_CODE_ROOTS = ("framework/galpao_fw/", "tools/")


@dataclass(frozen=True)
class ReviewerRequest:
    task: object
    evidence: object
    test_delta: object
    diff: str
    worktree: str
    allowed_paths: tuple[str, ...] = ()
    files_touched: tuple[str, ...] = ()
    test_paths: tuple[str, ...] = ()
    targeted: object | None = None
    regression: object | None = None

    def __post_init__(self):
        object.__setattr__(self, "allowed_paths", tuple(str(path).replace("\\", "/") for path in self.allowed_paths))
        object.__setattr__(self, "files_touched", tuple(str(path).replace("\\", "/") for path in self.files_touched))
        object.__setattr__(self, "test_paths", tuple(str(path).replace("\\", "/") for path in self.test_paths))


@dataclass(frozen=True)
class ReviewResult:
    approved: bool
    reasons: tuple[str, ...] = ()
    scope_ok: bool = False
    evidence_ok: bool = False
    targeted_ok: bool = False
    regression_ok: bool = False
    remote_sources_ok: bool = False

    @property
    def accepted(self) -> bool:
        return self.approved

    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "reasons": list(self.reasons),
            "scope_ok": self.scope_ok,
            "evidence_ok": self.evidence_ok,
            "targeted_ok": self.targeted_ok,
            "regression_ok": self.regression_ok,
            "remote_sources_ok": self.remote_sources_ok,
        }


class ReviewAdapter:
    """Evaluate objective gates without invoking an external reviewer."""

    def review(self, request: ReviewerRequest) -> ReviewResult:
        reasons = []
        evidence_ok = self._evidence_ok(request.evidence)
        if not evidence_ok:
            reasons.append("evidence/citation ausente ou invalida")

        scope_ok = self._scope_ok(request)
        if not scope_ok:
            reasons.append("arquivo fora do escopo ou fonte remota alterada")

        targeted_ok = self._targeted_ok(request)
        if not targeted_ok:
            reasons.append("teste alvo ausente, falho ou nao executado")

        regression_ok = bool(getattr(request.test_delta, "promotion_allowed", False))
        if not regression_ok:
            reasons.append("nova regressao, erro, timeout ou falha de execucao")

        remote_sources_ok = not _remote_source_change(request.diff, request.files_touched)
        if not remote_sources_ok and not any("fonte remota" in reason for reason in reasons):
            reasons.append("mudanca em fonte remota proibida")

        return ReviewResult(
            approved=not reasons,
            reasons=tuple(reasons),
            scope_ok=scope_ok,
            evidence_ok=evidence_ok,
            targeted_ok=targeted_ok,
            regression_ok=regression_ok,
            remote_sources_ok=remote_sources_ok,
        )

    @staticmethod
    def _evidence_ok(evidence) -> bool:
        source_ids = tuple(getattr(evidence, "source_ids", ()))
        sources = tuple(getattr(evidence, "sources", ()))
        citations = tuple(getattr(evidence, "citations", ()))
        if not source_ids or not sources or not citations:
            return False
        requested_ids = set(source_ids)
        source_map = {source.source_id: source for source in sources}
        return all(
            citation.source_id in requested_ids
            and citation.source_id in source_map
            and type(source_map[citation.source_id].status) is int
            and source_map[citation.source_id].status == 2
            and citation.cited_text.strip()
            for citation in citations
        )

    @staticmethod
    def _targeted_ok(request: ReviewerRequest) -> bool:
        snapshot = request.targeted
        if snapshot is None:
            snapshot = getattr(request.test_delta, "current", None)
            if getattr(snapshot, "kind", None) != "targeted":
                return False
        expected = tuple(getattr(request, "test_paths", ())) or tuple(
            getattr(request.task, "suggested_tests", ())
        )
        actual = tuple(getattr(snapshot, "target_paths", ()))
        if not actual:
            return False
        if expected and not any(_same_path(expected_path, actual_path) for expected_path in expected for actual_path in actual):
            return False
        return bool(getattr(snapshot, "successful", False))

    @staticmethod
    def _scope_ok(request: ReviewerRequest) -> bool:
        paths = set(request.files_touched) or _diff_paths(request.diff)
        allowed = set(request.allowed_paths)
        if not paths:
            return False
        if not allowed:
            return False
        return all(path in allowed or _is_new_code_path(path) for path in paths)


def _diff_paths(diff: str) -> tuple[str, ...]:
    paths = []
    for line in diff.splitlines():
        match = re.match(r"(?:diff --git a/([^ ]+) b/[^ ]+|\+\+\+ b/(\S+)|--- a/(\S+))", line)
        if match:
            path = next((value for value in match.groups() if value and value != "/dev/null"), None)
            if path and path not in paths:
                paths.append(path)
    return tuple(paths)


def _remote_source_change(diff: str, files_touched=()) -> bool:
    paths = set(_diff_paths(diff)) | set(files_touched)
    return any(path.casefold().startswith(("fontes/", "sources/", "source/")) for path in paths)


def _is_new_code_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return normalized.endswith(".py") and normalized.startswith(_NEW_CODE_ROOTS)


def _same_path(expected: str, actual: str) -> bool:
    return expected.replace("\\", "/").lstrip("./") == actual.replace("\\", "/").lstrip("./")
