from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import subprocess

import tools.loops.agents as agents_module
from tools.loops.agents import (
    AgentRequest,
    ClaudePrintAdapter,
    CodexExecAdapter,
    build_implementation_prompt,
)
from tools.loops.models import Citation, EvidenceBundle, SourceRecord, TaskCandidate
from tools.loops.reviewer import ReviewAdapter, ReviewerRequest
from tools.loops.tests_runner import TestSnapshot, compare_snapshots

TestSnapshot.__test__ = False


def task():
    return TaskCandidate(
        id="T-1",
        title="Corrigir validacao",
        discipline="estrutura",
        origin="wiki/T1",
        priority=80,
        evidence_paths=("framework/galpao_fw/wiki/T1.md",),
        suggested_tests=("tests/test_validacao.py",),
    )


def evidence(*, citations=True):
    source = SourceRecord("SRC-1", "NBR 6118", 2, "nb-estrutura")
    return EvidenceBundle(
        notebook_id="nb-estrutura",
        source_ids=("SRC-1",),
        sources=(source,),
        question="Qual criterio deve ser aplicado?",
        answer="Aplicar o criterio citado.",
        conversation_id="conv-1",
        citations=(Citation("1", "SRC-1", "trecho citado"),) if citations else (),
        retrieved_at="2026-08-12T20:00:00Z",
    )


def request(tmp_path, *, evidence_bundle=None, artifact_path=None, plan=None, red_result=None):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return AgentRequest(
        task=task(),
        evidence=evidence_bundle or evidence(),
        plan=plan or "Implementar a menor mudanca e registrar a incerteza.",
        worktree=str(worktree),
        test_paths=("tests/test_validacao.py",),
        artifact_path=str(artifact_path) if artifact_path else None,
        red_result=red_result,
    )


class FakeAgentRunner:
    def __init__(self, stdout="agent output", returncode=0):
        self.stdout = stdout
        self.returncode = returncode
        self.calls = []

    def __call__(self, argv, cwd, input_text, timeout_seconds):
        self.calls.append(
            {
                "argv": tuple(argv),
                "cwd": str(cwd),
                "input": input_text,
                "timeout": timeout_seconds,
            }
        )
        return SimpleNamespace(returncode=self.returncode, stdout=self.stdout, stderr="")


def test_codex_command_uses_workspace_write_and_no_permission_bypass(tmp_path):
    fake = FakeAgentRunner()
    artifact = tmp_path / "agent-last-message.txt"
    adapter = CodexExecAdapter(runner=fake, timeout_seconds=30)

    result = adapter.run(request(tmp_path, artifact_path=artifact))
    argv = fake.calls[0]["argv"]

    assert argv[:2] == ("codex", "exec")
    assert "--cd" in argv and fake.calls[0]["cwd"] == str(tmp_path / "worktree")
    assert "--approve-for-me" in argv
    assert "--sandbox" not in argv
    assert "--ask-for-approval" not in argv
    assert "--output-last-message" in argv
    assert argv[-1] == "-"
    assert not any("dangerously" in value or "skip" in value for value in argv)
    assert "citation" in fake.calls[0]["input"].casefold()
    assert result.argv == tuple(value for value in argv)
    assert artifact.read_text(encoding="utf-8") == "agent output"


def test_agent_output_and_artifact_redact_credentials(tmp_path):
    fake = FakeAgentRunner(stdout='token=abc123 cookie=xyz789 {"password":"pw"}')
    artifact = tmp_path / "agent.txt"
    adapter = CodexExecAdapter(runner=fake)

    result = adapter.run(request(tmp_path, artifact_path=artifact))
    safe = result.stdout + artifact.read_text(encoding="utf-8")

    assert "abc123" not in safe
    assert "xyz789" not in safe
    assert '"pw"' not in safe
    assert safe.count("[REDACTED]") >= 3


def test_process_resolves_windows_command_shim(monkeypatch, tmp_path):
    calls = []

    class FinishedProcess:
        returncode = 0

        def communicate(self, input=None, timeout=None):
            calls.append(("communicate", input, timeout))
            return "ok", ""

    def fake_popen(argv, **kwargs):
        calls.append((tuple(argv), kwargs))
        return FinishedProcess()

    monkeypatch.setattr(agents_module.shutil, "which", lambda value: "C:/bin/codex.cmd")
    monkeypatch.setattr(agents_module.subprocess, "Popen", fake_popen)

    result = agents_module._run_process(("codex", "--version"), tmp_path, "", 5)

    assert result.returncode == 0
    assert calls[0][0][0] == "C:/bin/codex.cmd"
    assert calls[0][0][1] == "--version"
    assert calls[1] == ("communicate", None, 5)


def test_process_timeout_terminates_windows_executor_tree(monkeypatch, tmp_path):
    calls = []

    class HangingProcess:
        pid = 9876
        returncode = None

        def communicate(self, input=None, timeout=None):
            calls.append(("communicate", input, timeout))
            if len([item for item in calls if item[0] == "communicate"]) == 1:
                raise subprocess.TimeoutExpired(
                    ["codex"], timeout, output="partial", stderr="warning"
                )
            self.returncode = -9
            return "tail", ""

        def terminate(self):
            calls.append(("terminate",))

        def kill(self):
            calls.append(("kill",))

    process = HangingProcess()
    taskkill_calls = []

    def fake_popen(argv, **kwargs):
        calls.append(("popen", tuple(argv), kwargs))
        return process

    def fake_run(argv, **kwargs):
        taskkill_calls.append((tuple(argv), kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(agents_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(agents_module.subprocess, "run", fake_run)

    result = agents_module._run_process(("codex", "exec"), tmp_path, "prompt", 3)

    assert result.returncode == -1
    assert result.timed_out is True
    assert "partial" in result.stdout
    assert "tail" in result.stdout
    assert calls[1] == ("communicate", "prompt", 3)
    assert calls[-1] == ("communicate", None, 1)
    if agents_module.os.name == "nt":
        assert taskkill_calls[0][0] == ("taskkill", "/PID", "9876", "/T", "/F")
    else:
        assert ("terminate",) in calls or ("kill",) in calls


def test_claude_command_is_noninteractive_and_scoped(tmp_path):
    fake = FakeAgentRunner(stdout='{"result":"done"}')
    adapter = ClaudePrintAdapter(runner=fake, timeout_seconds=30)

    result = adapter.run(request(tmp_path))
    argv = fake.calls[0]["argv"]

    assert argv[:2] == ("claude", "-p")
    assert argv[argv.index("--add-dir") + 1] == str(tmp_path / "worktree")
    assert argv[argv.index("--permission-mode") + 1] == "acceptEdits"
    assert argv[argv.index("--output-format") + 1] == "json"
    assert "--no-session-persistence" in argv
    assert argv[-1].startswith("Implementacao") or "Implementar" in argv[-1]
    assert not any("dangerously" in value or "skip-permissions" in value for value in argv)
    assert result.successful
    assert Path(result.artifact_path).read_text(encoding="utf-8") == '{"result":"done"}'


def test_implementation_prompt_requires_citations_and_red_test():
    prompt = Path("tools/loops/prompts/implementation.md").read_text(encoding="utf-8").casefold()

    assert "cit" in prompt
    assert "red" in prompt
    assert "escopo" in prompt or "scope" in prompt
    assert "incerteza" in prompt or "uncertainty" in prompt


def test_implementation_prompt_does_not_reopen_a_confirmed_red_contract(tmp_path):
    prompt = build_implementation_prompt(request(tmp_path))

    assert "teste red ja foi confirmado" in prompt.casefold()
    assert "nao peca nova decisao" in prompt.casefold()
    assert "conflito nao resolvido" in prompt.casefold()


def test_implementation_prompt_keeps_approved_phase_in_execution_mode(tmp_path):
    prompt = build_implementation_prompt(request(tmp_path)).casefold()

    assert "fase e o desenho ja foram aprovados" in prompt
    assert "nao invoque brainstorming" in prompt
    assert "nao faca perguntas de aprovacao" in prompt


def test_implementation_prompt_overrides_legacy_plan_decision_request(tmp_path):
    prompt = build_implementation_prompt(
        request(
            tmp_path,
            plan="O plano legado diz: pedir decisao humana para esta incerteza antes de alterar o codigo.",
        )
    ).casefold()

    assert "plano pode conter orientacao generica ou legada" in prompt
    assert "nao peca nova decisao" in prompt
    assert "resultado do gate red" in prompt


def test_implementation_prompt_includes_observed_red_contract(tmp_path):
    prompt = build_implementation_prompt(
        request(
            tmp_path,
            red_result={
                "kind": "red",
                "returncode": 1,
                "failed": 2,
                "errors": 0,
                "failed_tests": ["tests/test_validacao.py::test_lb_zero", "tests/test_validacao.py::test_lb_nan"],
            },
        )
    ).casefold()

    assert "contrato executavel do red" in prompt
    assert "pytest.raises" in prompt
    assert "test_lb_zero" in prompt
    assert "test_lb_nan" in prompt


def test_reviewer_rejects_missing_citation(tmp_path):
    baseline = TestSnapshot(kind="baseline", returncode=0)
    targeted = TestSnapshot(kind="targeted", target_paths=("tests/test_validacao.py",), returncode=0, passed=1)
    delta = compare_snapshots(baseline, targeted)
    review = ReviewAdapter().review(
        ReviewerRequest(
            task=task(),
            evidence=evidence(citations=False),
            test_delta=delta,
            diff="diff --git a/tools/validacao.py b/tools/validacao.py",
            worktree=str(tmp_path),
            allowed_paths=("tools/validacao.py",),
        )
    )

    assert not review.approved
    assert any("citation" in reason.casefold() for reason in review.reasons)


def test_reviewer_rejects_citation_outside_requested_source_ids(tmp_path):
    bundle = evidence()
    bundle = replace(
        bundle,
        source_ids=("SRC-OTHER",),
    )
    baseline = TestSnapshot(kind="baseline", returncode=0)
    targeted = TestSnapshot(kind="targeted", target_paths=("tests/test_validacao.py",), returncode=0, passed=1)
    delta = compare_snapshots(baseline, targeted)

    review = ReviewAdapter().review(
        ReviewerRequest(
            task=task(),
            evidence=bundle,
            test_delta=delta,
            diff="diff --git a/tools/validacao.py b/tools/validacao.py",
            worktree=str(tmp_path),
            allowed_paths=("tools/validacao.py",),
        )
    )

    assert not review.approved
    assert not review.evidence_ok


def test_reviewer_rejects_new_regression(tmp_path):
    baseline = TestSnapshot(kind="baseline", returncode=0, passed=2)
    current = TestSnapshot(
        kind="regression",
        returncode=1,
        failed=1,
        failed_tests=("tests/test_new.py::test_new",),
    )
    delta = compare_snapshots(baseline, current)

    review = ReviewAdapter().review(
        ReviewerRequest(
            task=task(),
            evidence=evidence(),
            test_delta=delta,
            diff="diff --git a/tools/validacao.py b/tools/validacao.py",
            worktree=str(tmp_path),
            allowed_paths=("tools/validacao.py",),
            test_paths=("tests/test_validacao.py",),
        )
    )

    assert not review.approved
    assert any("regress" in reason.casefold() for reason in review.reasons)


def test_reviewer_accepts_verified_in_scope_change(tmp_path):
    baseline = TestSnapshot(kind="baseline", returncode=0, passed=2)
    targeted = TestSnapshot(kind="targeted", target_paths=("tests/test_validacao.py",), returncode=0, passed=1)
    delta = compare_snapshots(baseline, targeted)

    review = ReviewAdapter().review(
        ReviewerRequest(
            task=task(),
            evidence=evidence(),
            test_delta=delta,
            diff="diff --git a/tools/validacao.py b/tools/validacao.py\n+++ b/tools/validacao.py",
            worktree=str(tmp_path),
            allowed_paths=("tools/validacao.py",),
            test_paths=("tests/test_validacao.py",),
        )
    )

    assert review.approved
    assert review.scope_ok
    assert review.targeted_ok
    assert review.regression_ok


def test_reviewer_accepts_new_python_module_inside_code_root(tmp_path):
    baseline = TestSnapshot(kind="baseline", returncode=0, passed=2)
    targeted = TestSnapshot(kind="targeted", target_paths=("tests/test_validacao.py",), returncode=0, passed=1)
    delta = compare_snapshots(baseline, targeted)

    review = ReviewAdapter().review(
        ReviewerRequest(
            task=task(),
            evidence=evidence(),
            test_delta=delta,
            diff="diff --git a/framework/galpao_fw/novo_modulo.py b/framework/galpao_fw/novo_modulo.py\n+++ b/framework/galpao_fw/novo_modulo.py",
            worktree=str(tmp_path),
            allowed_paths=("framework/galpao_fw/galpao_seguranca_incendio.py",),
            test_paths=("tests/test_validacao.py",),
        )
    )

    assert review.approved
    assert review.scope_ok


def test_reviewer_uses_task_suggested_test_when_path_not_explicit(tmp_path):
    baseline = TestSnapshot(kind="baseline", returncode=0)
    targeted = TestSnapshot(kind="targeted", target_paths=("tests/test_validacao.py",), returncode=0, passed=1)
    delta = compare_snapshots(baseline, targeted)

    review = ReviewAdapter().review(
        ReviewerRequest(
            task=task(),
            evidence=evidence(),
            test_delta=delta,
            diff="diff --git a/tools/validacao.py b/tools/validacao.py",
            worktree=str(tmp_path),
            allowed_paths=("tools/validacao.py",),
        )
    )

    assert review.approved


def test_reviewer_requires_explicit_test_path_when_target_is_injected(tmp_path):
    baseline = TestSnapshot(kind="baseline", returncode=0)
    targeted = TestSnapshot(kind="targeted", target_paths=("tests/other.py",), returncode=0, passed=1)
    delta = compare_snapshots(baseline, targeted)

    review = ReviewAdapter().review(
        ReviewerRequest(
            task=task(),
            evidence=evidence(),
            test_delta=delta,
            targeted=targeted,
            test_paths=("tests/test_validacao.py",),
            diff="diff --git a/tools/validacao.py b/tools/validacao.py",
            worktree=str(tmp_path),
            allowed_paths=("tools/validacao.py",),
        )
    )

    assert not review.approved
    assert not review.targeted_ok


def test_reviewer_rejects_source_change_and_out_of_scope_file(tmp_path):
    baseline = TestSnapshot(kind="baseline", returncode=0)
    targeted = TestSnapshot(kind="targeted", target_paths=("tests/test_validacao.py",), returncode=0, passed=1)
    delta = compare_snapshots(baseline, targeted)

    review = ReviewAdapter().review(
        ReviewerRequest(
            task=task(),
            evidence=evidence(),
            test_delta=delta,
            diff="diff --git a/fontes/NBR.pdf b/fontes/NBR.pdf\n+++ b/fontes/NBR.pdf",
            worktree=str(tmp_path),
            allowed_paths=("tools/validacao.py",),
        )
    )

    assert not review.approved
    assert not review.scope_ok
    assert any("escopo" in reason.casefold() or "fonte" in reason.casefold() for reason in review.reasons)
