from pathlib import Path

from tools.loops.supervisor import DevelopmentSupervisor
from tools.loops.tests.test_supervisor import harness, make_supervisor


def test_fake_full_cycle_persists_all_phase_artifacts(tmp_path):
    h, cfg = harness(tmp_path)

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "promoted"
    run_dir = Path(cfg.runtime_dir) / "runs" / outcome.loop_id
    for name in ("task.json", "evidence.json", "plan.md", "baseline.json", "targeted.json", "regression.json", "test-delta.json", "review.json", "session-summary.md"):
        assert (run_dir / name).exists(), name
    assert (Path(cfg.runtime_dir) / "ledger.json").exists()


def test_fake_missing_source_cycle_parks_without_agent_or_network(tmp_path):
    h, cfg = harness(tmp_path)
    h.research.error = RuntimeError("no requested sources are ready")

    outcome = make_supervisor(h, cfg).run_once()

    assert outcome.outcome == "manual_source_required"
    assert h.agent.calls == 0
    assert h.tests.calls == []
    assert h.reviewer.calls == 0
