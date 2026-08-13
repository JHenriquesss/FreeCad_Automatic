from dataclasses import dataclass, replace
import json
from pathlib import Path
import subprocess

import pytest

from tools.loops.agents import AgentResult
from tools.loops.ledger import Ledger
from tools.loops.models import (
    Citation,
    EvidenceBundle,
    LoopConfig,
    LoopPhase,
    LoopState,
    SourceRecord,
    TaskCandidate,
)
from tools.loops.reviewer import ReviewResult
from tools.loops.research_nlm import NlmCommandTimeout, NlmEvidenceRequired
from tools.loops.supervisor import (
    DevelopmentSupervisor,
    MissingSourceRequired,
    SupervisorDeps,
)
from tools.loops.tests_runner import TestSnapshot

TestSnapshot.__test__ = False


def git(*args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    git("init", "-b", "main", cwd=root)
    git("config", "user.name", "Supervisor Test", cwd=root)
    git("config", "user.email", "supervisor@example.test", cwd=root)
    (root / "framework" / "galpao_fw").mkdir(parents=True)
    (root / "framework" / "galpao_fw" / "tools").mkdir()
    (root / "framework" / "galpao_fw" / "tools" / "run_tests.py").write_text(
        "print('ok')\n", encoding="utf-8"
    )
    (root / "tracked.txt").write_text("base\n", encoding="utf-8")
    (root / ".gitignore").write_text(".loop-runtime/\n", encoding="utf-8")
    git("add", ".", cwd=root)
    git("commit", "-m", "initial", cwd=root)
    return root, git("rev-parse", "HEAD", cwd=root)


def config(root, *, mode="supervised", max_attempts=3):
    return LoopConfig(
        project_root=str(root),
        runtime_dir=str(root / ".loop-runtime"),
        mode=mode,
        max_iterations=1,
        max_attempts_per_phase=max_attempts,
        command_timeout_seconds=10,
        build_timeout_seconds=10,
        executor="codex",
    )


def task():
    return TaskCandidate(
        id="task-1",
        title="Validar modulo",
        discipline="estrutura",
        origin="wiki/T1",
        priority=80,
        evidence_paths=("wiki/T1.md",),
        suggested_tests=("tests/test_modulo.py",),
    )


def evidence():
    source = SourceRecord("src-1", "NBR teste", 2, "nb-1")
    return EvidenceBundle(
        notebook_id="nb-1",
        source_ids=("src-1",),
        sources=(source,),
        question="Qual criterio?",
        answer="Aplicar o criterio.",
        conversation_id="conv-1",
        citations=(Citation("1", "src-1", "trecho"),),
        retrieved_at="2026-08-12T00:00:00Z",
    )


class FakeDiscover:
    def __init__(self, candidates=(None,)):
        self.calls = 0
        self.candidates = tuple(candidates)

    def __call__(self, project_root):
        self.calls += 1
        return tuple(candidate for candidate in self.candidates if candidate is not None)


class FakeResearch:
    def __init__(self, value=None):
        self.calls = 0
        self.value = value or evidence()
        self.error = None

    def __call__(self, candidate):
        self.calls += 1
        if self.error:
            raise self.error
        return self.value


class FakePlanner:
    def __init__(self):
        self.calls = 0

    def __call__(self, candidate, evidence_bundle):
        self.calls += 1
        return "plano de teste"


class FakeRed:
    def __init__(self, value=True):
        self.calls = 0
        self.value = value

    def __call__(self, candidate, evidence_bundle, plan, worktree):
        self.calls += 1
        return self.value


class FakeAgent:
    def __init__(self, value=None):
        self.calls = 0
        self.value = value or AgentResult(
            executor="fake",
            argv=("fake",),
            cwd=".",
            returncode=0,
            duration_seconds=0.1,
            stdout="ok",
            stderr="",
            files_touched=("tools/fix.py",),
        )

    def run(self, request):
        self.calls += 1
        return self.value


class FakeTests:
    def __init__(self, *, targeted_failed=False, regression_failed=False):
        self.calls = []
        self.targeted_failed = targeted_failed
        self.regression_failed = regression_failed

    def baseline(self):
        self.calls.append("baseline")
        return TestSnapshot(kind="baseline", returncode=0, passed=2)

    def targeted(self, paths):
        self.calls.append("targeted")
        return TestSnapshot(
            kind="targeted",
            target_paths=tuple(paths),
            returncode=1 if self.targeted_failed else 0,
            passed=0 if self.targeted_failed else 1,
            failed=1 if self.targeted_failed else 0,
            failed_tests=("tests/test_modulo.py::test_fail",) if self.targeted_failed else (),
        )

    def regression(self):
        self.calls.append("regression")
        return TestSnapshot(
            kind="regression",
            returncode=1 if self.regression_failed else 0,
            passed=1 if self.regression_failed else 2,
            failed=1 if self.regression_failed else 0,
            failed_tests=("tests/test_regressao.py::test_nova",) if self.regression_failed else (),
        )

    def build(self):
        self.calls.append("build")
        return TestSnapshot(kind="build", returncode=0, passed=1)


class FakeReviewer:
    def __init__(self, approved=True):
        self.calls = 0
        self.approved = approved

    def review(self, request):
        self.calls += 1
        return ReviewResult(
            approved=self.approved,
            reasons=() if self.approved else ("review rejected",),
            scope_ok=self.approved,
            evidence_ok=self.approved,
            targeted_ok=self.approved,
            regression_ok=self.approved,
            remote_sources_ok=self.approved,
        )


class FakeWorktrees:
    def __init__(self, root, base_commit, *, external=False):
        self.root = root
        self.base_commit = base_commit
        self.external = external
        self.create_calls = 0
        self.assert_calls = 0

    def create(self, loop_id, base_commit):
        self.create_calls += 1
        path = self.root / "worktree" / loop_id
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def assert_base_unchanged(self, base_commit):
        self.assert_calls += 1
        if self.external:
            raise RuntimeError("external change")


class FakePromote:
    def __init__(self):
        self.calls = 0

    def __call__(self, worktree, loop_id):
        self.calls += 1
        return "local-commit"


@dataclass
class Harness:
    root: Path
    base: str
    discover: FakeDiscover
    research: FakeResearch
    planner: FakePlanner
    red: FakeRed
    agent: FakeAgent
    tests: FakeTests
    reviewer: FakeReviewer
    worktrees: FakeWorktrees
    promote: FakePromote
    deps: SupervisorDeps


def harness(tmp_path, *, mode="supervised", targeted_failed=False, regression_failed=False, external=False, build_required=False):
    root, base = project(tmp_path)
    discover = FakeDiscover((task(),))
    research = FakeResearch()
    planner = FakePlanner()
    red = FakeRed()
    agent = FakeAgent()
    tests = FakeTests(targeted_failed=targeted_failed, regression_failed=regression_failed)
    reviewer = FakeReviewer()
    worktrees = FakeWorktrees(root, base, external=external)
    promote = FakePromote()
    deps = SupervisorDeps(
        discover=discover,
        research=research,
        planner=planner,
        red=red,
        agent=agent,
        tests=tests,
        reviewer=reviewer,
        worktrees=worktrees,
        promote=promote,
        allowed_paths=("tools/fix.py",),
        build_required=build_required,
    )
    return Harness(root, base, discover, research, planner, red, agent, tests, reviewer, worktrees, promote, deps), config(root, mode=mode)


def make_supervisor(harness_value, config_value):
    return DevelopmentSupervisor(config_value, harness_value.deps)


def test_dry_run_stops_before_external_mutation(tmp_path):
    h, cfg = harness(tmp_path, mode="dry-run")

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "dry_run"
    assert outcome.phase is LoopPhase.PARK
    assert h.discover.calls == 1
    assert h.research.calls == 1
    assert h.planner.calls == 1
    assert h.worktrees.create_calls == 0
    assert h.red.calls == 0
    assert h.agent.calls == 0
    assert h.tests.calls == []
    assert h.reviewer.calls == 0


def test_missing_source_parks_and_writes_manual_request(tmp_path):
    h, cfg = harness(tmp_path)
    h.research.error = MissingSourceRequired("fonte ausente")

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "manual_source_required"
    assert outcome.phase is LoopPhase.PARK
    request_path = Path(outcome.state.artifacts["manual_source_request"])
    assert request_path.exists()
    assert "fonte ausente" in request_path.read_text(encoding="utf-8")
    assert h.worktrees.create_calls == 0


def test_targeted_failure_parks_loop(tmp_path):
    h, cfg = harness(tmp_path, targeted_failed=True)

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "targeted_failed"
    assert outcome.phase is LoopPhase.PARK
    assert h.tests.calls == ["baseline", "targeted"]
    assert h.reviewer.calls == 0
    assert h.promote.calls == 0


def test_regression_failure_parks_loop(tmp_path):
    h, cfg = harness(tmp_path, regression_failed=True)

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "regression_failed"
    assert outcome.phase is LoopPhase.PARK
    assert h.tests.calls == ["baseline", "targeted", "regression"]
    assert h.reviewer.calls == 0


def test_regression_timeout_parks_as_command_timeout(tmp_path):
    h, cfg = harness(tmp_path)

    def timed_out_regression():
        h.tests.calls.append("regression")
        return TestSnapshot(kind="regression", returncode=-1, timed_out=True)

    h.tests.regression = timed_out_regression

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "command_timeout"
    assert outcome.state.failure.reason == "command_timeout"
    assert h.reviewer.calls == 0


def test_timeout_parks_with_command_timeout_reason(tmp_path):
    h, cfg = harness(tmp_path)
    h.tests.targeted_failed = True

    def timed_out_target(paths):
        h.tests.calls.append("targeted")
        return TestSnapshot(kind="targeted", target_paths=tuple(paths), returncode=-1, timed_out=True)

    h.tests.targeted = timed_out_target
    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "command_timeout"
    assert outcome.state.failure.reason == "command_timeout"


def test_research_timeout_parks_with_command_timeout_reason(tmp_path):
    h, cfg = harness(tmp_path)
    h.research.error = NlmCommandTimeout("nlm command timed out")

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "command_timeout"
    assert outcome.state.failure.reason == "command_timeout"


def test_research_evidence_gap_parks_as_manual_source_required(tmp_path):
    h, cfg = harness(tmp_path)
    request = tmp_path / "manual-source-requests.md"
    request.write_text("fonte sem citacao", encoding="utf-8")
    h.research.error = NlmEvidenceRequired("no auditable citations", request)

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "manual_source_required"
    assert outcome.state.failure.reason == "missing_source"
    assert "no auditable citations" in Path(outcome.state.artifacts["manual_source_request"]).read_text(encoding="utf-8")


def test_required_build_is_executed_and_failure_parks(tmp_path):
    h, cfg = harness(tmp_path, build_required=True)

    def failed_build():
        h.tests.calls.append("build")
        return TestSnapshot(kind="build", returncode=1, failed=1)

    h.tests.build = failed_build
    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "build_failed"
    assert h.tests.calls[-1] == "build"
    assert h.reviewer.calls == 0


def test_supervised_cycle_promotes_only_local_worktree(tmp_path):
    h, cfg = harness(tmp_path)

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "promoted"
    assert outcome.phase is LoopPhase.PROMOTE
    assert h.promote.calls == 1
    assert h.worktrees.assert_calls >= 1
    assert outcome.state.artifacts["promoted_commit"] == "local-commit"
    assert git("status", "--porcelain", cwd=h.root) == ""


def test_next_run_skips_a_candidate_already_promoted(tmp_path):
    h, cfg = harness(tmp_path)
    next_task = replace(task(), id="task-2", title="Validar segundo modulo")

    first = make_supervisor(h, cfg).run_once()
    assert first.outcome == "promoted"

    h.discover.candidates = (task(), next_task)
    second = make_supervisor(h, cfg).run_once()

    assert second.outcome == "promoted"
    assert second.state.task.id == "task-2"


def test_all_code_gates_use_iteration_worktree(tmp_path):
    h, cfg = harness(tmp_path)
    factory_paths = []

    def tests_factory(worktree):
        factory_paths.append(str(worktree))
        return h.tests

    h.deps = replace(h.deps, tests_factory=tests_factory)

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "promoted"
    assert factory_paths
    assert all(path == outcome.state.worktree for path in factory_paths)
    assert str(h.root) not in factory_paths


def test_resume_restarts_from_persisted_phase(tmp_path):
    h, cfg = harness(tmp_path)
    loop_id = "resume-1"
    runtime = Path(cfg.runtime_dir)
    runtime.mkdir(parents=True)
    state = LoopState(
        schema_version=1,
        loop_id=loop_id,
        mode="supervised",
        iteration=1,
        phase=LoopPhase.IMPLEMENT,
        task=task(),
        base_commit=h.base,
        worktree=str(h.root / "worktree" / loop_id),
        evidence=evidence(),
        attempts={"preflight": 1, "discover": 1, "research": 1, "plan": 1, "red": 1, "implement": 0},
        artifacts={},
        outcome=None,
        last_error=None,
        failure=None,
    )
    baseline = TestSnapshot(kind="baseline", returncode=0, passed=2)
    (Path(cfg.runtime_dir) / "runs" / loop_id).mkdir(parents=True)
    (Path(cfg.runtime_dir) / "runs" / loop_id / "baseline.json").write_text(
        json.dumps(baseline.to_dict()), encoding="utf-8"
    )
    Path(state.worktree).mkdir(parents=True)
    (Path(cfg.runtime_dir) / "runs" / loop_id / "plan.md").write_text("plano persistido", encoding="utf-8")
    Ledger(runtime / "ledger.json", state).save()

    outcome = make_supervisor(h, cfg).resume(loop_id)

    assert outcome.outcome == "promoted"
    assert h.discover.calls == 0
    assert h.research.calls == 0
    assert h.agent.calls == 1


def test_resume_from_plan_reuses_persisted_worktree(tmp_path):
    h, cfg = harness(tmp_path)
    loop_id = "resume-plan"
    runtime = Path(cfg.runtime_dir)
    worktree = h.root / "worktree" / loop_id
    worktree.mkdir(parents=True)
    state = LoopState(
        schema_version=1,
        loop_id=loop_id,
        mode="supervised",
        iteration=1,
        phase=LoopPhase.PLAN,
        task=task(),
        base_commit=h.base,
        worktree=str(worktree),
        evidence=evidence(),
        attempts={"plan": 0},
        artifacts={},
        outcome=None,
        last_error=None,
        failure=None,
    )
    Ledger(runtime / "ledger.json", state).save()

    outcome = make_supervisor(h, cfg).resume(loop_id)

    assert outcome.outcome == "promoted"
    assert h.worktrees.create_calls == 0
    assert outcome.state.worktree == str(worktree)


def test_resume_from_review_rehydrates_persisted_verification(tmp_path):
    h, cfg = harness(tmp_path)
    loop_id = "resume-review"
    runtime = Path(cfg.runtime_dir)
    run_dir = runtime / "runs" / loop_id
    run_dir.mkdir(parents=True)
    baseline = TestSnapshot(kind="baseline", returncode=0, passed=2)
    targeted = TestSnapshot(kind="targeted", target_paths=("tests/test_modulo.py",), returncode=0, passed=1)
    regression = TestSnapshot(kind="regression", returncode=0, passed=2)
    from tools.loops.tests_runner import compare_snapshots
    delta = compare_snapshots(baseline, regression)
    for name, value in (("baseline", baseline), ("targeted", targeted), ("regression", regression)):
        (run_dir / f"{name}.json").write_text(json.dumps(value.to_dict()), encoding="utf-8")
    (run_dir / "test-delta.json").write_text(json.dumps(delta.to_dict()), encoding="utf-8")
    (run_dir / "plan.md").write_text("plano", encoding="utf-8")
    worktree = h.root / "worktree" / loop_id
    worktree.mkdir(parents=True)
    state = LoopState(
        schema_version=1,
        loop_id=loop_id,
        mode="supervised",
        iteration=1,
        phase=LoopPhase.REVIEW,
        task=task(),
        base_commit=h.base,
        worktree=str(worktree),
        evidence=evidence(),
        attempts={"verify": 1},
        artifacts={},
        outcome=None,
        last_error=None,
        failure=None,
    )
    Ledger(runtime / "ledger.json", state).save()

    outcome = make_supervisor(h, cfg).resume(loop_id)

    assert outcome.outcome == "promoted"
    assert h.tests.calls == []


def test_external_head_change_prevents_promotion(tmp_path):
    h, cfg = harness(tmp_path, external=True)

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "external_change"
    assert outcome.phase is LoopPhase.PARK
    assert h.promote.calls == 0


def test_every_transition_is_persisted(tmp_path):
    h, cfg = harness(tmp_path)
    outcome = make_supervisor(h, cfg).run_once()

    document = json.loads((Path(cfg.runtime_dir) / "ledger.json").read_text(encoding="utf-8"))
    assert document["phase"] == "promote"
    assert outcome.transition_count >= 9
    assert outcome.state.artifacts["session_summary"]
    summary = Path(outcome.state.artifacts["session_summary"]).read_text(encoding="utf-8")
    assert "outcome: ready_for_promotion" in summary


def test_attempt_limit_prevents_infinite_retry(tmp_path):
    h, cfg = harness(tmp_path)
    cfg = config(h.root, max_attempts=1)
    h.red.value = False
    supervisor = make_supervisor(h, cfg)

    first = supervisor.run_once()
    second = supervisor.resume(first.loop_id)

    assert first.outcome == "red_failed"
    assert second.outcome == "attempt_limit"
    assert h.red.calls == 1


def test_active_ledger_must_be_resumed_before_new_run(tmp_path):
    h, cfg = harness(tmp_path)
    first = make_supervisor(h, cfg).run_once()
    assert first.outcome == "promoted"
    (Path(cfg.runtime_dir) / "ledger.json").write_text(
        (Path(cfg.runtime_dir) / "ledger.json").read_text(encoding="utf-8").replace('"phase": "promote"', '"phase": "implement"'),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="active loop"):
        make_supervisor(h, cfg).run_once()
