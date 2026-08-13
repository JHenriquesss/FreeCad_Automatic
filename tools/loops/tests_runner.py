"""Test execution, pytest result parsing, and promotion gates."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
import sys

from .commands import CommandRunner
from .models import CommandResult


TARGETED = (sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q")
REGRESSION = (sys.executable, "tools/run_tests.py")
BUILD = ("powershell", "-ExecutionPolicy", "Bypass", "-File", "tools/run_build_suite.ps1")

_COUNT_RE = re.compile(r"(?<!\w)(\d+)\s+(passed|failed|skipped|errors?|xfailed|xpassed)\b", re.IGNORECASE)
_DURATION_RE = re.compile(r"\bin\s+([0-9]+(?:\.[0-9]+)?)s\b", re.IGNORECASE)


@dataclass(frozen=True)
class TestSnapshot:
    kind: str
    command: tuple[str, ...] = ()
    cwd: str = ""
    returncode: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    timed_out: bool = False
    stdout: str = ""
    stderr: str = ""
    failed_tests: tuple[str, ...] = ()
    error_tests: tuple[str, ...] = ()
    target_paths: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "command", tuple(str(item) for item in self.command))
        object.__setattr__(self, "failed_tests", tuple(self.failed_tests))
        object.__setattr__(self, "error_tests", tuple(self.error_tests))
        object.__setattr__(self, "target_paths", tuple(str(item) for item in self.target_paths))
        object.__setattr__(self, "artifacts", tuple(str(item) for item in self.artifacts))

    @property
    def successful(self) -> bool:
        return (
            self.returncode == 0
            and not self.timed_out
            and self.failed == 0
            and self.errors == 0
            and not (self.kind == "targeted" and self.target_paths and self.skipped > 0)
        )

    @property
    def failure_ids(self) -> tuple[str, ...]:
        return self.failed_tests

    @property
    def duration(self) -> float:
        return self.duration_seconds

    @property
    def error_ids(self) -> tuple[str, ...]:
        return self.error_tests

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "command": list(self.command),
            "cwd": self.cwd,
            "returncode": self.returncode,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "timed_out": self.timed_out,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "failed_tests": list(self.failed_tests),
            "error_tests": list(self.error_tests),
            "target_paths": list(self.target_paths),
            "artifacts": list(self.artifacts),
        }


@dataclass(frozen=True)
class TestDelta:
    baseline: TestSnapshot
    current: TestSnapshot
    preexisting_failures: tuple[str, ...] = ()
    new_failures: tuple[str, ...] = ()
    resolved_failures: tuple[str, ...] = ()
    preexisting_errors: tuple[str, ...] = ()
    new_errors: tuple[str, ...] = ()
    resolved_errors: tuple[str, ...] = ()
    promotion_allowed: bool = False

    @property
    def has_new_failure(self) -> bool:
        return bool(self.new_failures)

    @property
    def has_new_error(self) -> bool:
        return bool(self.new_errors)

    @property
    def can_promote(self) -> bool:
        return self.promotion_allowed

    def to_dict(self) -> dict:
        return {
            "baseline": self.baseline.to_dict(),
            "current": self.current.to_dict(),
            "preexisting_failures": list(self.preexisting_failures),
            "new_failures": list(self.new_failures),
            "resolved_failures": list(self.resolved_failures),
            "preexisting_errors": list(self.preexisting_errors),
            "new_errors": list(self.new_errors),
            "resolved_errors": list(self.resolved_errors),
            "promotion_allowed": self.promotion_allowed,
        }


def parse_test_result(
    result: CommandResult,
    *,
    kind: str,
    command=None,
    cwd=None,
    target_paths=(),
    artifacts=(),
) -> TestSnapshot:
    """Parse stable counts and test identifiers from a pytest command result."""
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    combined = f"{stdout}\n{stderr}"
    summary = _last_summary(combined)
    counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    duration = result.duration_seconds
    if summary:
        summary_text, summary_duration = summary
        duration = summary_duration
        for count, label in _COUNT_RE.findall(summary_text):
            name = label.casefold()
            if name in {"error", "errors"}:
                name = "errors"
            if name in counts:
                counts[name] = int(count)

    failed_tests = _status_ids(combined, "FAILED")
    error_tests = _status_ids(combined, "ERROR")
    counts["failed"] = max(counts["failed"], len(failed_tests))
    counts["errors"] = max(counts["errors"], len(error_tests))
    return TestSnapshot(
        kind=kind,
        command=tuple(command if command is not None else result.argv),
        cwd=str(cwd if cwd is not None else result.cwd),
        returncode=result.returncode,
        duration_seconds=float(duration),
        timed_out=getattr(result, "timed_out", False),
        stdout=stdout,
        stderr=stderr,
        failed_tests=failed_tests,
        error_tests=error_tests,
        target_paths=tuple(target_paths),
        artifacts=tuple(artifacts),
        **counts,
    )


class TestRunner:
    """Run the loop's targeted, regression, and optional build gates."""

    def __init__(
        self,
        project_root,
        *,
        command_runner: CommandRunner | None = None,
        artifact_dir=None,
        command_timeout_seconds: int = 900,
        build_timeout_seconds: int = 1800,
    ):
        self.project_root = Path(project_root).expanduser().resolve()
        self.framework_root = self.project_root / "framework" / "galpao_fw"
        self.command_runner = command_runner or CommandRunner()
        self.artifact_dir = (
            Path(artifact_dir).expanduser().resolve()
            if artifact_dir is not None
            else self.project_root / ".loop-runtime" / "test-results"
        )
        self.command_timeout_seconds = command_timeout_seconds
        self.build_timeout_seconds = build_timeout_seconds

    def baseline(self) -> TestSnapshot:
        return self._run(REGRESSION, self.framework_root, "baseline", self.command_timeout_seconds)

    def targeted(self, test_paths) -> TestSnapshot:
        paths = tuple(str(path) for path in test_paths)
        command = TARGETED + tuple(self._target_argument(path) for path in paths)
        return self._run(
            command,
            self.framework_root,
            "targeted",
            self.command_timeout_seconds,
            target_paths=paths,
        )

    def regression(self) -> TestSnapshot:
        return self._run(REGRESSION, self.framework_root, "regression", self.command_timeout_seconds)

    def build(self) -> TestSnapshot:
        return self._run(BUILD, self.project_root, "build", self.build_timeout_seconds)

    def _run(self, command, cwd, kind, timeout_seconds, *, target_paths=()):
        result = self.command_runner.run(command, cwd, timeout_seconds)
        artifacts = self._save_output(kind, result)
        return parse_test_result(
            result,
            kind=kind,
            command=command,
            cwd=cwd,
            target_paths=target_paths,
            artifacts=artifacts,
        )

    def _target_argument(self, value: str) -> str:
        path = Path(value)
        if path.is_absolute():
            try:
                return path.resolve().relative_to(self.framework_root).as_posix()
            except ValueError:
                return str(path)
        project_relative = self.project_root / path
        try:
            return project_relative.resolve().relative_to(self.framework_root).as_posix()
        except ValueError:
            pass
        return path.as_posix()

    def _save_output(self, kind: str, result: CommandResult) -> tuple[str, ...]:
        if self.artifact_dir is None:
            return ()
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = self.artifact_dir / f"{kind}.stdout.txt"
        stderr_path = self.artifact_dir / f"{kind}.stderr.txt"
        stdout_path.write_text(result.stdout or "", encoding="utf-8")
        stderr_path.write_text(result.stderr or "", encoding="utf-8")
        return (str(stdout_path), str(stderr_path))


def compare_snapshots(baseline: TestSnapshot, current: TestSnapshot) -> TestDelta:
    baseline_failures = _stable_ids(baseline.failed_tests, baseline.failed, "failure")
    current_failures = _stable_ids(current.failed_tests, current.failed, "failure")
    baseline_errors = _stable_ids(baseline.error_tests, baseline.errors, "error")
    current_errors = _stable_ids(current.error_tests, current.errors, "error")

    new_failures = tuple(sorted(current_failures - baseline_failures))
    preexisting_failures = tuple(sorted(current_failures & baseline_failures))
    resolved_failures = tuple(sorted(baseline_failures - current_failures))
    new_errors = tuple(sorted(current_errors - baseline_errors))
    preexisting_errors = tuple(sorted(current_errors & baseline_errors))
    resolved_errors = tuple(sorted(baseline_errors - current_errors))

    unparsed_execution_failure = (
        current.returncode != 0
        and not current.timed_out
        and current.failed == 0
        and current.errors == 0
    )
    targeted_failure = current.kind == "targeted" and not current.successful
    allowed = not (
        current.timed_out
        or new_failures
        or new_errors
        or targeted_failure
        or unparsed_execution_failure
    )
    return TestDelta(
        baseline=baseline,
        current=current,
        preexisting_failures=preexisting_failures,
        new_failures=new_failures,
        resolved_failures=resolved_failures,
        preexisting_errors=preexisting_errors,
        new_errors=new_errors,
        resolved_errors=resolved_errors,
        promotion_allowed=allowed,
    )


def promotion_allowed(
    *,
    baseline: TestSnapshot | None = None,
    targeted: TestSnapshot | None = None,
    regression: TestSnapshot | None = None,
    build: TestSnapshot | None = None,
    build_required: bool = False,
) -> bool:
    """Return whether all supplied gates permit local promotion."""
    baseline = baseline or TestSnapshot(kind="baseline")
    if targeted is not None and not targeted.successful:
        return False
    if regression is not None and not compare_snapshots(baseline, regression).promotion_allowed:
        return False
    if build_required and (build is None or not build.successful):
        return False
    return True


def _last_summary(output: str):
    matches = []
    for line in output.splitlines():
        duration_match = _DURATION_RE.search(line)
        if duration_match and _COUNT_RE.search(line):
            matches.append((line, float(duration_match.group(1))))
    return matches[-1] if matches else None


def _status_ids(output: str, status: str) -> tuple[str, ...]:
    found = []
    prefix = status.casefold()
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped.casefold().startswith(prefix + " "):
            continue
        value = stripped.split(None, 1)[1].strip()
        value = value.split(" - ", 1)[0].strip()
        if value and value not in found:
            found.append(value)
    return tuple(found)


def _stable_ids(ids, count: int, label: str) -> set[str]:
    values = list(ids)
    index = 0
    while len(values) < count:
        synthetic = f"__{label}_{index}"
        if synthetic not in values:
            values.append(synthetic)
        index += 1
    return set(values)
