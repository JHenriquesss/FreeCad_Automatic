"""Persisted state-machine orchestration for one development-loop iteration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import subprocess

from .agents import AgentRequest, AgentResult
from .ledger import Ledger
from .models import LoopPhase, LoopState
from .research_nlm import NlmCommandTimeout, NlmEvidenceRequired
from .reviewer import ReviewerRequest
from .tests_runner import compare_snapshots


class MissingSourceRequired(RuntimeError):
    """Research cannot continue until the user supplies or fixes a source."""


@dataclass(frozen=True)
class SupervisorDeps:
    discover: object
    research: object
    planner: object
    red: object
    agent: object
    tests: object
    reviewer: object
    worktrees: object
    tests_factory: object | None = None
    promote: object | None = None
    allowed_paths: tuple[str, ...] = ()
    build_required: bool = False


@dataclass(frozen=True)
class RunOutcome:
    loop_id: str
    outcome: str
    phase: LoopPhase
    state: LoopState
    transition_count: int = 0


_FAILURE_PHASES = {
    "missing_source": LoopPhase.RESEARCH,
    "source_conflict": LoopPhase.RESEARCH,
    "research_error": LoopPhase.RESEARCH,
    "red_failed": LoopPhase.RED,
    "implementation_error": LoopPhase.IMPLEMENT,
    "implementation_no_change": LoopPhase.IMPLEMENT,
    "targeted_failed": LoopPhase.VERIFY,
    "regression_failed": LoopPhase.VERIFY,
    "build_failed": LoopPhase.VERIFY,
    "review_rejected": LoopPhase.REVIEW,
    "command_timeout": LoopPhase.VERIFY,
    "external_change": LoopPhase.REVIEW,
}


class DevelopmentSupervisor:
    def __init__(self, config, deps: SupervisorDeps):
        self.config = config
        self.deps = deps
        self.project_root = Path(config.project_root).expanduser().resolve()
        self.runtime_dir = Path(config.runtime_dir).expanduser().resolve()
        self.ledger_path = self.runtime_dir / "ledger.json"
        self.completed_tasks_path = self.runtime_dir / "completed-tasks.json"
        self.transition_count = 0
        self.run_dir: Path | None = None
        self.ledger: Ledger | None = None

    def run_once(self) -> RunOutcome:
        self._validate_config()
        if self.ledger_path.exists():
            existing = Ledger.load(self.ledger_path).state
            if existing.phase not in {LoopPhase.PARK, LoopPhase.PROMOTE}:
                raise RuntimeError("an active loop already exists; resume it before starting another")
            if existing.phase is LoopPhase.PROMOTE and existing.outcome == "promoted":
                self._record_completion(existing, existing.artifacts.get("promoted_commit"))
        loop_id = self._new_loop_id()
        base_commit = self._root_head()
        state = LoopState(
            schema_version=1,
            loop_id=loop_id,
            mode=self.config.mode,
            iteration=1,
            phase=LoopPhase.PREFLIGHT,
            task=None,
            base_commit=base_commit,
            worktree=None,
            evidence=None,
            attempts={},
            artifacts={},
            outcome=None,
            last_error=None,
            failure=None,
        )
        self._start(state, overwrite=True)
        return self._advance()

    def resume(self, loop_id) -> RunOutcome:
        if not self.ledger_path.exists():
            raise FileNotFoundError(self.ledger_path)
        self._start(Ledger.load(self.ledger_path).state)
        if self.ledger.state.loop_id != loop_id:
            raise ValueError("requested loop_id does not match persisted ledger")
        state = self.ledger.state
        if state.phase is LoopPhase.PARK and state.failure is not None:
            phase = self._resume_phase(state)
            if phase is None:
                return self._set_outcome("attempt_limit")
            if state.attempts.get(phase.value, 0) >= self.config.max_attempts_per_phase:
                return self._set_outcome("attempt_limit")
            self._save(replace(state, phase=phase, outcome=None, last_error=None, failure=None))
        return self._advance()

    def _resume_phase(self, state):
        """Choose a retry phase using the persisted result of the last agent run."""
        reason = state.failure.reason
        if reason == "targeted_failed":
            agent_artifact = state.artifacts.get("agent")
            if agent_artifact:
                try:
                    document = json.loads(Path(agent_artifact).read_text(encoding="utf-8"))
                except (OSError, TypeError, ValueError):
                    document = None
                if document is not None and document.get("files_touched") == []:
                    return LoopPhase.IMPLEMENT
        return _FAILURE_PHASES.get(reason)

    def _start(self, state: LoopState, *, overwrite=False) -> None:
        self.ledger = Ledger(self.ledger_path, state)
        self.run_dir = self.runtime_dir / "runs" / state.loop_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        if overwrite or not self.ledger_path.exists():
            self._save(state)

    def _advance(self) -> RunOutcome:
        while True:
            state = self.ledger.state
            if state.phase is LoopPhase.PREFLIGHT:
                self._transition(LoopPhase.PREFLIGHT, LoopPhase.DISCOVER)
                continue
            if state.phase is LoopPhase.DISCOVER:
                candidates = self._discover()
                if not candidates:
                    return self._park("no_candidate", "no observable candidate")
                task = candidates[0]
                task_path = self._write_json_artifact("task", task.to_dict())
                self._save(
                    replace(
                        self.ledger.state,
                        task=task,
                        artifacts={**self.ledger.state.artifacts, "task": task_path},
                    )
                )
                self._transition(LoopPhase.DISCOVER, LoopPhase.RESEARCH)
                continue
            if state.phase is LoopPhase.RESEARCH:
                try:
                    evidence = self._attempt(LoopPhase.RESEARCH, self._research, state.task)
                except MissingSourceRequired as error:
                    return self._park_manual_source(str(error))
                except NlmEvidenceRequired as error:
                    return self._park_manual_source(
                        f"{error}\nArquivo de pendencias: {error.manual_request_path}"
                    )
                except Exception as error:
                    if self._looks_like_missing_source(error):
                        return self._park_manual_source(str(error))
                    reason = "command_timeout" if isinstance(error, NlmCommandTimeout) else "research_error"
                    return self._park(reason, str(error))
                self._write_json_artifact("evidence", evidence.to_dict())
                self._save(replace(self.ledger.state, evidence=evidence))
                self._transition(LoopPhase.RESEARCH, LoopPhase.PLAN)
                continue
            if state.phase is LoopPhase.PLAN:
                try:
                    plan = self._attempt(LoopPhase.PLAN, self._plan, state.task, state.evidence)
                except Exception as error:
                    return self._park("research_error", f"plan: {error}")
                plan_path = self._write_text_artifact("plan", str(plan))
                self._save(replace(self.ledger.state, artifacts={**state.artifacts, "plan": plan_path}))
                if self.config.mode == "dry-run":
                    return self._finish_park("dry_run")
                try:
                    worktree = self.ledger.state.worktree or self._create_worktree()
                    self._save(replace(self.ledger.state, worktree=worktree))
                    baseline = self._tests_baseline()
                    baseline_path = self._write_json_artifact("baseline", baseline.to_dict())
                    self._save(
                        replace(
                            self.ledger.state,
                            worktree=worktree,
                            artifacts={**self.ledger.state.artifacts, "baseline": baseline_path},
                        )
                    )
                except Exception as error:
                    return self._park("implementation_error", f"worktree/baseline: {error}")
                self._transition(LoopPhase.PLAN, LoopPhase.RED)
                continue
            if state.phase is LoopPhase.RED:
                try:
                    red_result = self._attempt(LoopPhase.RED, self._red, state.task, state.evidence, self._plan_text())
                except Exception as error:
                    return self._park("red_failed", str(error))
                self._red_result = red_result
                red_document = red_result.to_dict() if hasattr(red_result, "to_dict") else (
                    red_result if isinstance(red_result, dict) else {
                        "kind": "red",
                        "successful": _successful_bool(red_result),
                    }
                )
                red_path = self._write_json_artifact("red", red_document)
                self._save(replace(self.ledger.state, artifacts={**self.ledger.state.artifacts, "red": red_path}))
                if not _successful_bool(red_result):
                    return self._park("red_failed", "target test did not fail before implementation")
                self._transition(LoopPhase.RED, LoopPhase.IMPLEMENT)
                continue
            if state.phase is LoopPhase.IMPLEMENT:
                recovered = self._recover_interrupted_implementation(state)
                if recovered is not None:
                    self._transition(LoopPhase.IMPLEMENT, LoopPhase.VERIFY)
                    continue
                try:
                    result = self._attempt(LoopPhase.IMPLEMENT, self._agent, state.task, state.evidence, self._plan_text(), state.worktree)
                except Exception as error:
                    return self._park("implementation_error", str(error))
                result_path = self._write_json_artifact("agent", result.to_dict())
                self._save(replace(self.ledger.state, artifacts={**state.artifacts, "agent": result_path}))
                if getattr(result, "timed_out", False):
                    return self._park("command_timeout", "implementation agent timed out")
                if not _successful_bool(result):
                    return self._park("implementation_error", "implementation agent failed")
                if not self._implementation_changed(result, state.worktree):
                    return self._park(
                        "implementation_no_change",
                        "implementation agent completed without changing the worktree",
                    )
                self._transition(LoopPhase.IMPLEMENT, LoopPhase.VERIFY)
                continue
            if state.phase is LoopPhase.VERIFY:
                result = self._verify()
                if result is not None:
                    return result
                self._transition(LoopPhase.VERIFY, LoopPhase.REVIEW)
                continue
            if state.phase is LoopPhase.REVIEW:
                self._hydrate_verification()
                result = self._review()
                if result is not None:
                    return result
                self._transition(LoopPhase.REVIEW, LoopPhase.RECORD)
                continue
            if state.phase is LoopPhase.RECORD:
                summary_path = self._write_session_summary()
                self._save(replace(self.ledger.state, artifacts={**state.artifacts, "session_summary": summary_path}))
                try:
                    self._assert_root_stable()
                except Exception as error:
                    if "external" in str(error).casefold():
                        return self._park("external_change", str(error))
                    return self._park("implementation_error", str(error))
                self._transition(LoopPhase.RECORD, LoopPhase.PROMOTE)
                continue
            if state.phase is LoopPhase.PROMOTE:
                if state.outcome == "promoted":
                    self._record_completion(state, state.artifacts.get("promoted_commit"))
                    return self._outcome("promoted")
                try:
                    self._assert_root_stable()
                    commit = self._promote()
                except Exception as error:
                    return self._park("implementation_error", str(error))
                self._save(
                    replace(
                        self.ledger.state,
                        outcome="promoted",
                        artifacts={**self.ledger.state.artifacts, "promoted_commit": commit},
                    )
                )
                self._record_completion(self.ledger.state, commit)
                return self._outcome("promoted")
            if state.phase is LoopPhase.PARK:
                return self._outcome(state.outcome or "parked")
            raise ValueError(f"unsupported supervisor phase: {state.phase}")

    def _discover(self):
        value = self.deps.discover(self.project_root) if callable(self.deps.discover) else self.deps.discover.discover_candidates(self.project_root)
        completed = self._completed_task_ids()
        excluded = completed | frozenset(getattr(self.config, "excluded_task_ids", ()))
        return tuple(candidate for candidate in value if candidate.id not in excluded)

    def _completed_task_ids(self):
        if not self.completed_tasks_path.exists():
            return frozenset()
        document = json.loads(self.completed_tasks_path.read_text(encoding="utf-8"))
        tasks = document.get("tasks", {})
        if not isinstance(tasks, dict):
            raise ValueError("completed task registry must contain an object at tasks")
        return frozenset(tasks)

    def _record_completion(self, state, promoted_commit):
        if state.task is None:
            return
        document = {"schema_version": 1, "tasks": {}}
        if self.completed_tasks_path.exists():
            document = json.loads(self.completed_tasks_path.read_text(encoding="utf-8"))
        tasks = document.setdefault("tasks", {})
        tasks[state.task.id] = {
            "loop_id": state.loop_id,
            "title": state.task.title,
            "topic": state.task.topic,
            "promoted_commit": promoted_commit,
        }
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.completed_tasks_path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _research(self, candidate):
        try:
            value = self.deps.research(candidate) if callable(self.deps.research) else self.deps.research.research(candidate)
        except NlmEvidenceRequired:
            cached = self._cached_evidence(candidate)
            if cached is None:
                raise
            self._research_cache_hit = True
            return cached
        if getattr(value, "manual_request", None) and not getattr(value, "citations", ()):
            raise MissingSourceRequired(value.manual_request)
        return value

    def _cached_evidence(self, candidate):
        runs_dir = self.runtime_dir / "runs"
        if not runs_dir.is_dir():
            return None
        for run_dir in sorted(
            (path for path in runs_dir.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        ):
            task_path = run_dir / "task.json"
            evidence_path = run_dir / "evidence.json"
            if not task_path.is_file() or not evidence_path.is_file():
                continue
            try:
                cached_task = self._load_task(task_path)
                if cached_task.to_dict() != candidate.to_dict():
                    continue
                evidence = self._load_evidence(evidence_path)
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
            if self._evidence_matches_local_sources(evidence):
                return evidence
        return None

    @staticmethod
    def _load_task(path):
        from .models import TaskCandidate

        return TaskCandidate.from_dict(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _load_evidence(path):
        from .models import EvidenceBundle

        return EvidenceBundle.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _evidence_matches_local_sources(self, evidence):
        if not evidence.source_ids or not evidence.citations:
            return False
        source_by_id = {source.source_id: source for source in evidence.sources}
        if set(source_by_id) != set(evidence.source_ids):
            return False
        if any(
            citation.source_id not in evidence.source_ids or not citation.cited_text.strip()
            for citation in evidence.citations
        ):
            return False
        for source in evidence.sources:
            if type(source.status) is not int or source.status != 2:
                return False
            if not source.local_path or not source.local_hash:
                return False
            path = self._local_source_path(source.local_path)
            if path is None or not path.is_file():
                return False
            digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
            if digest != source.local_hash.upper():
                return False
        return True

    def _local_source_path(self, local_path):
        source_root = (self.project_root / "fontes").resolve()
        normalized = str(local_path).replace("\\", "/")
        if normalized.casefold().startswith("fontes/"):
            normalized = normalized.split("/", 1)[1]
        candidate = (source_root / Path(*PurePosixPath(normalized).parts)).resolve()
        try:
            candidate.relative_to(source_root)
        except ValueError:
            return None
        return candidate

    def _plan(self, candidate, evidence):
        if callable(self.deps.planner):
            return self.deps.planner(candidate, evidence)
        return self.deps.planner.plan(candidate, evidence)

    def _red(self, candidate, evidence, plan):
        if callable(self.deps.red):
            return self.deps.red(candidate, evidence, plan, self.ledger.state.worktree)
        return self.deps.red.run(candidate, evidence, plan, self.ledger.state.worktree)

    def _agent(self, candidate, evidence, plan, worktree):
        red_result = getattr(self, "_red_result", None)
        if red_result is None:
            red_result = self._load_json_artifact("red") or self._load_json_artifact("targeted")
        request = AgentRequest(
            task=candidate,
            evidence=evidence,
            plan=plan,
            worktree=worktree,
            test_paths=tuple(candidate.suggested_tests),
            artifact_path=str(self.run_dir / "agent-last-message.txt"),
            timeout_seconds=self.config.command_timeout_seconds,
            red_result=red_result,
        )
        return self.deps.agent.run(request) if hasattr(self.deps.agent, "run") else self.deps.agent(request)

    def _tests_baseline(self):
        return self._tests_adapter().baseline()

    def _tests_adapter(self):
        factory = self.deps.tests_factory
        if factory is None:
            return self.deps.tests
        if callable(factory):
            return factory(self.ledger.state.worktree)
        if hasattr(factory, "for_worktree"):
            return factory.for_worktree(self.ledger.state.worktree)
        raise TypeError("tests_factory must be callable or expose for_worktree")

    def _verify(self):
        state = self.ledger.state
        tests = self._tests_adapter()
        try:
            self._save(state)
            targeted = tests.targeted(state.task.suggested_tests)
            targeted_path = self._write_json_artifact("targeted", targeted.to_dict())
            self._save(replace(self.ledger.state, artifacts={**state.artifacts, "targeted": targeted_path}))
            if targeted.timed_out:
                return self._park("command_timeout", "targeted test gate timed out")
            if not targeted.successful:
                return self._park("targeted_failed", "targeted test gate failed")
            regression = tests.regression()
            regression_path = self._write_json_artifact("regression", regression.to_dict())
            self._save(replace(self.ledger.state, artifacts={**self.ledger.state.artifacts, "regression": regression_path}))
            if regression.timed_out:
                return self._park("command_timeout", "regression gate timed out")
            baseline = self._load_snapshot("baseline")
            delta = compare_snapshots(baseline, regression)
            delta_path = self._write_json_artifact("test-delta", delta.to_dict())
            self._save(replace(self.ledger.state, artifacts={**self.ledger.state.artifacts, "test_delta": delta_path}))
            self._verify_targeted = targeted
            self._verify_regression = regression
            self._verify_delta = delta
            if not delta.promotion_allowed:
                return self._park("regression_failed", "regression gate failed")
            if self.deps.build_required or getattr(state.task, "requires_build", False):
                build = tests.build()
                build_path = self._write_json_artifact("build", build.to_dict())
                self._save(replace(self.ledger.state, artifacts={**self.ledger.state.artifacts, "build": build_path}))
                self._verify_build = build
                if not build.successful:
                    return self._park("command_timeout" if build.timed_out else "build_failed", "build gate failed")
            return None
        except Exception as error:
            return self._park("command_timeout" if "timeout" in str(error).casefold() else "regression_failed", str(error))

    def _review(self):
        state = self.ledger.state
        self._hydrate_agent()
        diff = self._git_diff(state.worktree)
        files = tuple(getattr(self._agent_result, "files_touched", ())) if hasattr(self, "_agent_result") else ()
        if not files:
            files = _diff_paths(diff)
        if not files:
            files = self._worktree_files(state.worktree)
        if not diff:
            diff = "\n".join(f"diff --git a/{path} b/{path}" for path in files)
        request = ReviewerRequest(
            task=state.task,
            evidence=state.evidence,
            test_delta=self._verify_delta,
            diff=diff,
            worktree=state.worktree,
            allowed_paths=self.deps.allowed_paths or files,
            files_touched=files,
            test_paths=tuple(state.task.suggested_tests),
            targeted=self._verify_targeted,
            regression=self._verify_regression,
        )
        result = self.deps.reviewer.review(request)
        result_path = self._write_json_artifact("review", result.to_dict())
        self._save(replace(state, artifacts={**state.artifacts, "review": result_path}))
        if not result.approved:
            return self._park("review_rejected", "; ".join(result.reasons))
        return None

    def _hydrate_verification(self):
        if hasattr(self, "_verify_delta"):
            return
        self._verify_targeted = self._load_snapshot("targeted")
        self._verify_regression = self._load_snapshot("regression")
        self._verify_delta = self._load_delta()

    def _hydrate_agent(self):
        if hasattr(self, "_agent_result"):
            return
        artifact = self.ledger.state.artifacts.get("agent")
        if not artifact or not Path(artifact).is_file():
            return
        document = json.loads(Path(artifact).read_text(encoding="utf-8"))
        self._agent_result = AgentResult(
            executor=document["executor"],
            argv=tuple(document["argv"]),
            cwd=document["cwd"],
            returncode=document["returncode"],
            duration_seconds=document["duration_seconds"],
            stdout=document["stdout"],
            stderr=document["stderr"],
            files_touched=tuple(document.get("files_touched", ())),
            artifact_path=document.get("artifact_path"),
            timed_out=document.get("timed_out", False),
        )


    def _create_worktree(self):
        return self.deps.worktrees.create(self.ledger.state.loop_id, self.ledger.state.base_commit)

    def _promote(self):
        if self.deps.promote is not None:
            return self.deps.promote(self.ledger.state.worktree, self.ledger.state.loop_id)
        return _default_promote(self.ledger.state.worktree, self.ledger.state.loop_id)

    def _attempt(self, phase, function, *args):
        name = phase.value
        attempts = dict(self.ledger.state.attempts)
        current = attempts.get(name, 0)
        if current >= self.config.max_attempts_per_phase:
            raise RuntimeError(f"attempt limit reached for {name}")
        attempts[name] = current + 1
        self._save(replace(self.ledger.state, attempts=attempts))
        result = function(*args)
        if phase is LoopPhase.IMPLEMENT:
            self._agent_result = result
        return result

    def _transition(self, expected, target):
        self.ledger.transition(expected, target)
        self.transition_count += 1

    def _save(self, state):
        self.ledger.save(state)

    def _park_manual_source(self, detail):
        path = self._write_text_artifact("manual-source-requests", detail)
        self._save(replace(self.ledger.state, artifacts={**self.ledger.state.artifacts, "manual_source_request": path}))
        result = self._park("missing_source", detail)
        self._save(replace(self.ledger.state, outcome="manual_source_required"))
        return self._outcome("manual_source_required")

    def _park(self, reason, detail):
        if self.ledger.state.phase is not LoopPhase.PARK:
            self._transition(self.ledger.state.phase, LoopPhase.PARK)
        self.ledger.record_failure(reason, None, tuple(self.ledger.state.artifacts.values()), detail)
        self._save(replace(self.ledger.state, outcome=reason, last_error=detail))
        return self._outcome(reason)

    def _finish_park(self, outcome):
        if self.ledger.state.phase is not LoopPhase.PARK:
            self._transition(self.ledger.state.phase, LoopPhase.PARK)
        self._save(replace(self.ledger.state, outcome=outcome))
        return self._outcome(outcome)

    def _set_outcome(self, outcome):
        self._save(replace(self.ledger.state, outcome=outcome))
        return self._outcome(outcome)

    def _outcome(self, outcome):
        return RunOutcome(self.ledger.state.loop_id, outcome, self.ledger.state.phase, self.ledger.state, self.transition_count)

    def _write_json_artifact(self, name, value):
        path = self.run_dir / f"{name}.json"
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return str(path)

    def _write_text_artifact(self, name, value):
        path = self.run_dir / f"{name}.md"
        path.write_text(str(value), encoding="utf-8")
        return str(path)

    def _load_snapshot(self, name):
        from .tests_runner import TestSnapshot

        return TestSnapshot(**json.loads((self.run_dir / f"{name}.json").read_text(encoding="utf-8")))

    def _load_json_artifact(self, name):
        artifact = self.ledger.state.artifacts.get(name) if self.ledger is not None else None
        path = Path(artifact) if artifact else self.run_dir / f"{name}.json"
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            return None

    def _load_delta(self):
        from .tests_runner import TestDelta

        document = json.loads((self.run_dir / "test-delta.json").read_text(encoding="utf-8"))
        return TestDelta(
            baseline= self._load_snapshot_from_dict(document["baseline"]),
            current=self._load_snapshot_from_dict(document["current"]),
            preexisting_failures=tuple(document["preexisting_failures"]),
            new_failures=tuple(document["new_failures"]),
            resolved_failures=tuple(document["resolved_failures"]),
            preexisting_errors=tuple(document["preexisting_errors"]),
            new_errors=tuple(document["new_errors"]),
            resolved_errors=tuple(document["resolved_errors"]),
            promotion_allowed=bool(document["promotion_allowed"]),
        )

    @staticmethod
    def _load_snapshot_from_dict(document):
        from .tests_runner import TestSnapshot

        return TestSnapshot(**document)

    def _plan_text(self):
        return (self.run_dir / "plan.md").read_text(encoding="utf-8")

    def _write_session_summary(self):
        return self._write_text_artifact(
            "session-summary",
            f"# Loop {self.ledger.state.loop_id}\n\n- outcome: {self.ledger.state.outcome or 'ready_for_promotion'}\n- task: {self.ledger.state.task.title}\n",
        )

    def _git_diff(self, worktree):
        try:
            return subprocess.run(
                ["git", "-C", str(worktree), "diff", "HEAD"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            ).stdout
        except OSError:
            return ""

    def _implementation_changed(self, result, worktree):
        if tuple(getattr(result, "files_touched", ())):
            return True
        return bool(self._git_diff(worktree) or self._worktree_files(worktree))

    def _recover_interrupted_implementation(self, state):
        """Rehydrate a change left on disk if the supervisor died before saving the agent result."""
        if not state.worktree:
            return None
        files = self._worktree_files(state.worktree)
        if not files and not self._git_diff(state.worktree):
            return None
        result = AgentResult(
            executor="recovered-worktree",
            argv=(),
            cwd=str(state.worktree),
            returncode=0,
            duration_seconds=0.0,
            stdout="implementation recovered from persisted worktree",
            stderr="",
            files_touched=files or _diff_paths(self._git_diff(state.worktree)),
        )
        path = self._write_json_artifact("agent-recovered", result.to_dict())
        self._agent_result = result
        self._save(replace(self.ledger.state, artifacts={**state.artifacts, "agent": path}))
        return result

    def _assert_root_stable(self):
        """Allow only audited loop-infrastructure commits made after loop start."""
        base_commit = self.ledger.state.base_commit
        try:
            self.deps.worktrees.assert_base_unchanged(base_commit)
            return
        except Exception as error:
            if "external" not in str(error).casefold():
                raise
        current_head = self._root_head()
        changed_paths = self._root_changed_paths(base_commit, current_head)
        if not changed_paths or any(not path.startswith("tools/loops/") for path in changed_paths):
            raise RuntimeError(
                f"external change: root advanced outside loop infrastructure ({', '.join(changed_paths)})"
            )
        self._save(replace(self.ledger.state, base_commit=current_head))

    def _root_changed_paths(self, base_commit, current_head):
        try:
            result = subprocess.run(
                ["git", "-C", str(self.project_root), "diff", "--name-only", f"{base_commit}..{current_head}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError:
            return ()
        if result.returncode != 0:
            return ()
        return tuple(path.replace("\\", "/") for path in result.stdout.splitlines() if path)

    @staticmethod
    def _worktree_files(worktree):
        try:
            result = subprocess.run(
                ["git", "-C", str(worktree), "status", "--short", "--untracked-files=all"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError:
            return ()
        paths = []
        for line in result.stdout.splitlines():
            if len(line) >= 4:
                path = line[3:].strip().replace("\\", "/")
                if " -> " in path:
                    path = path.split(" -> ", 1)[1]
                if path and path not in paths:
                    paths.append(path)
        return tuple(sorted(paths))

    def _looks_like_missing_source(self, error):
        message = str(error).casefold()
        if "no requested sources are ready" in message or "source" in message and "ready" in message:
            return True
        path = getattr(self.deps.research, "manual_request_path", None)
        return bool(path and Path(path).exists())

    def _root_head(self):
        return subprocess.run(
            ["git", "-C", str(self.project_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def _validate_config(self):
        if self.config.mode not in {"dry-run", "supervised", "autonomous"}:
            raise ValueError("invalid loop mode")
        for name in (
            "max_iterations",
            "max_attempts_per_phase",
            "command_timeout_seconds",
            "build_timeout_seconds",
        ):
            value = getattr(self.config, name, None)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer")

    @staticmethod
    def _new_loop_id():
        return "loop-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _successful_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        return bool(value.get("successful", False))
    return bool(getattr(value, "successful", False))


def _diff_paths(diff):
    paths = []
    for line in diff.splitlines():
        if line.startswith("diff --git a/"):
            value = line.split(" b/", 1)[0].removeprefix("diff --git a/")
            if value not in paths:
                paths.append(value)
    return tuple(paths)


def _default_promote(worktree, loop_id):
    subprocess.run(["git", "-C", worktree, "add", "--all"], check=True)
    result = subprocess.run(
        ["git", "-C", worktree, "commit", "-m", f"loop: {loop_id}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return subprocess.run(
        ["git", "-C", worktree, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
