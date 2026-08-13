from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import tools.loops.agents as agents_module
from tools.loops.agents import (
    AgentRequest,
    ClaudePrintAdapter,
    CodexExecAdapter,
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


def request(tmp_path, *, evidence_bundle=None, artifact_path=None):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return AgentRequest(
        task=task(),
        evidence=evidence_bundle or evidence(),
        plan="Implementar a menor mudanca e registrar a incerteza.",
        worktree=str(worktree),
        test_paths=("tests/test_validacao.py",),
        artifact_path=str(artifact_path) if artifact_path else None,
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
    assert "--sandbox" in argv and argv[argv.index("--sandbox") + 1] == "workspace-write"
    assert "--approve-for-me" in argv
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

    def fake_run(argv, **kwargs):
        calls.append((tuple(argv), kwargs))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(agents_module.shutil, "which", lambda value: "C:/bin/codex.cmd")
    monkeypatch.setattr(agents_module.subprocess, "run", fake_run)

    result = agents_module._run_process(("codex", "--version"), tmp_path, "", 5)

    assert result.returncode == 0
    assert calls[0][0][0] == "C:/bin/codex.cmd"
    assert calls[0][0][1] == "--version"


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
