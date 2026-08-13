"""Testes do scheduler que encadeia iterações independentes."""

from pathlib import Path
from types import SimpleNamespace

from tools.loops.__main__ import _run_iterations
from tools.loops.models import LoopConfig, LoopPhase, TaskCandidate


def _config(tmp_path, *, mode="supervised", max_iterations=3):
    return LoopConfig(
        project_root=str(tmp_path),
        runtime_dir=str(tmp_path / ".loop-runtime"),
        mode=mode,
        max_iterations=max_iterations,
        max_attempts_per_phase=2,
        command_timeout_seconds=10,
        build_timeout_seconds=10,
        executor="codex",
    )


def _task(task_id):
    return TaskCandidate(
        id=task_id,
        title=f"Tarefa {task_id}",
        discipline="estrutura",
        origin="wiki:T1",
        priority=1,
        evidence_paths=("wiki:T1",),
        suggested_tests=(),
    )


def _outcome(loop_id, outcome, task=None):
    return SimpleNamespace(
        loop_id=loop_id,
        outcome=outcome,
        phase=LoopPhase.PARK,
        state=SimpleNamespace(task=task),
    )


def test_scheduler_adia_fonte_bloqueada_e_executa_proxima_tarefa(tmp_path):
    bloqueada = _task("bloqueada")
    promovida = _task("promovida")
    outcomes = iter(
        (
            _outcome("loop-1", "manual_source_required", bloqueada),
            _outcome("loop-2", "promoted", promovida),
            _outcome("loop-3", "no_candidate"),
        )
    )
    configs = []

    class FakeSupervisor:
        def run_once(self):
            return next(outcomes)

        def resume(self, loop_id):
            raise AssertionError(f"resume inesperado: {loop_id}")

    def factory(config):
        configs.append(config)
        return FakeSupervisor()

    result = _run_iterations(_config(tmp_path), factory)

    assert [item.outcome for item in result] == [
        "manual_source_required", "promoted", "no_candidate"
    ]
    assert configs[0].excluded_task_ids == ()
    assert configs[1].excluded_task_ids == ("bloqueada",)
    assert configs[2].excluded_task_ids == ("bloqueada",)
    summary = Path(_config(tmp_path).runtime_dir) / "scheduler-last.json"
    assert summary.exists()
    assert "bloqueada" in summary.read_text(encoding="utf-8")


def test_scheduler_dry_run_executa_somente_uma_iteracao(tmp_path):
    outcomes = iter((_outcome("loop-1", "dry_run"), _outcome("loop-2", "promoted")))
    calls = []

    class FakeSupervisor:
        def run_once(self):
            calls.append("run_once")
            return next(outcomes)

        def resume(self, loop_id):
            raise AssertionError(f"resume inesperado: {loop_id}")

    result = _run_iterations(
        _config(tmp_path, mode="dry-run", max_iterations=3),
        lambda config: FakeSupervisor(),
    )

    assert [item.outcome for item in result] == ["dry_run"]
    assert calls == ["run_once"]


def test_scheduler_para_em_timeout_e_nao_tenta_proxima_tarefa(tmp_path):
    primeira = _task("primeira")
    outcomes = iter((_outcome("loop-1", "command_timeout", primeira),))
    calls = []

    class FakeSupervisor:
        def run_once(self):
            calls.append("run_once")
            return next(outcomes)

        def resume(self, loop_id):
            raise AssertionError(f"resume inesperado: {loop_id}")

    result = _run_iterations(_config(tmp_path), lambda config: FakeSupervisor())

    assert [item.outcome for item in result] == ["command_timeout"]
    assert calls == ["run_once"]
    summary = Path(_config(tmp_path).runtime_dir) / "scheduler-last.json"
    assert '"stop_reason": "command_timeout"' in summary.read_text(encoding="utf-8")
