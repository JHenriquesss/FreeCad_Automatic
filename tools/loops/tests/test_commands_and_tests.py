import sys
from pathlib import Path

from tools.loops.commands import CommandRunner
from tools.loops.models import CommandResult
from tools.loops.tests_runner import (
    TestRunner as LoopTestRunner,
    TestSnapshot as LoopTestSnapshot,
    compare_snapshots,
    parse_test_result,
    promotion_allowed,
)


class FakeCommandRunner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def run(self, argv, cwd, timeout_seconds):
        self.calls.append((tuple(argv), str(cwd), timeout_seconds))
        return self.results.pop(0)


def result(*, stdout="", stderr="", returncode=0, duration=0.25, timed_out=False):
    return CommandResult(
        argv=(sys.executable, "-m", "pytest"),
        cwd=".",
        returncode=returncode,
        duration_seconds=duration,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
    )


def test_command_runner_captures_stdout_and_stderr(tmp_path):
    command = (
        sys.executable,
        "-c",
        "import sys; print('out'); print('err', file=sys.stderr)",
    )

    captured = CommandRunner().run(command, tmp_path, timeout_seconds=5)

    assert captured.returncode == 0
    assert captured.timed_out is False
    assert "out" in captured.stdout
    assert "err" in captured.stderr


def test_command_runner_marks_timeout(tmp_path):
    # D81: o filho precisa de tempo REAL para chegar a imprimir antes de dormir.
    # Com timeout_seconds=0.1 o teste reprovava sob `pytest -n 4` porque a
    # partida do interpretador no Windows (~0,15 s medidos) ja estourava o
    # prazo: 'before' nunca era escrito e o assert de saida parcial caia por
    # CARGA DE MAQUINA, nao por defeito. 2,0 s fica bem acima da partida e bem
    # abaixo do sleep de 10 s, entao o caminho de timeout continua sendo o
    # exercitado - a semantica do teste nao muda, so deixa de ser corrida.
    command = (sys.executable, "-c", "import time; print('before', flush=True); time.sleep(10)")

    captured = CommandRunner().run(command, tmp_path, timeout_seconds=2.0)

    assert captured.returncode == -1
    assert captured.timed_out is True
    assert "before" in captured.stdout


def test_snapshot_parser_handles_pytest_summary():
    captured = result(
        stdout=(
            "FAILED tests/test_a.py::test_bad - assertion\n"
            "ERROR tests/test_b.py::test_error - setup\n"
            "===== 1 failed, 3 passed, 2 skipped, 1 error in 1.25s =====\n"
        )
    )

    snapshot = parse_test_result(captured, kind="regression")

    assert snapshot.passed == 3
    assert snapshot.failed == 1
    assert snapshot.skipped == 2
    assert snapshot.errors == 1
    assert snapshot.duration_seconds == 1.25
    assert snapshot.failed_tests == ("tests/test_a.py::test_bad",)
    assert snapshot.error_tests == ("tests/test_b.py::test_error",)
    assert snapshot.stdout == captured.stdout


def test_delta_distinguishes_new_failure_from_baseline_failure():
    baseline = LoopTestSnapshot(
        kind="baseline",
        failed=1,
        failed_tests=("tests/test_old.py::test_old",),
        returncode=1,
    )
    current = LoopTestSnapshot(
        kind="regression",
        failed=2,
        failed_tests=("tests/test_old.py::test_old", "tests/test_new.py::test_new"),
        returncode=1,
    )

    delta = compare_snapshots(baseline, current)

    assert delta.preexisting_failures == ("tests/test_old.py::test_old",)
    assert delta.new_failures == ("tests/test_new.py::test_new",)
    assert delta.promotion_allowed is False


def test_build_policy_is_separate_from_unit_regression(tmp_path):
    clean = result(stdout="===== 4 passed in 0.20s =====\n")
    fake = FakeCommandRunner([clean, clean])
    runner = LoopTestRunner(tmp_path, command_runner=fake, command_timeout_seconds=7, build_timeout_seconds=11)

    regression = runner.regression()
    build = runner.build()

    assert "run_tests.py" in regression.command[-1]
    assert regression.cwd == str(tmp_path / "framework" / "galpao_fw")
    assert build.command[-1].endswith("tools/run_build_suite.ps1")
    assert build.cwd == str(tmp_path)
    assert fake.calls[0][2] == 7
    assert fake.calls[1][2] == 11
    assert promotion_allowed(regression=regression, build_required=False)
    assert not promotion_allowed(regression=regression, build_required=True)


def test_targeted_failure_blocks_promotion():
    baseline = LoopTestSnapshot(kind="baseline", returncode=0)
    targeted = LoopTestSnapshot(
        kind="targeted",
        failed=1,
        failed_tests=("tests/test_target.py::test_target",),
        returncode=1,
    )

    delta = compare_snapshots(baseline, targeted)

    assert delta.promotion_allowed is False
    assert not promotion_allowed(targeted=targeted, regression=targeted)


def test_skipped_target_does_not_count_as_passed():
    targeted = LoopTestSnapshot(
        kind="targeted",
        target_paths=("tests/test_target.py",),
        skipped=1,
        returncode=0,
    )

    assert targeted.successful is False
    assert not promotion_allowed(targeted=targeted)


def test_runner_preserves_full_output_as_artifacts(tmp_path):
    fake = FakeCommandRunner([result(stdout="full stdout\n", stderr="full stderr\n")])
    runner = LoopTestRunner(tmp_path, command_runner=fake, artifact_dir=tmp_path / "artifacts")

    snapshot = runner.regression()

    assert "full stdout" in Path(snapshot.artifacts[0]).read_text(encoding="utf-8")
    assert "full stderr" in Path(snapshot.artifacts[1]).read_text(encoding="utf-8")


def test_targeted_runner_normalizes_project_relative_framework_path(tmp_path):
    test_file = tmp_path / "framework" / "galpao_fw" / "tests" / "test_modulo.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("", encoding="utf-8")
    fake = FakeCommandRunner([result(stdout="===== 1 passed in 0.01s =====\n")])
    runner = LoopTestRunner(tmp_path, command_runner=fake)

    runner.targeted(("framework/galpao_fw/tests/test_modulo.py",))

    assert fake.calls[0][0][-1] == "tests/test_modulo.py"
