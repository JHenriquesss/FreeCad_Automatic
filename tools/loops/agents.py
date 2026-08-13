"""Bounded adapters for implementation agents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import time


@dataclass(frozen=True)
class AgentRequest:
    task: object
    evidence: object
    plan: str
    worktree: str
    test_paths: tuple[str, ...]
    artifact_path: str | None = None
    timeout_seconds: int = 1800

    def __post_init__(self):
        object.__setattr__(self, "test_paths", tuple(str(path) for path in self.test_paths))


@dataclass(frozen=True)
class AgentResult:
    executor: str
    argv: tuple[str, ...]
    cwd: str
    returncode: int
    duration_seconds: float
    stdout: str
    stderr: str
    files_touched: tuple[str, ...] = ()
    artifact_path: str | None = None
    timed_out: bool = False

    @property
    def successful(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def duration(self) -> float:
        return self.duration_seconds

    def to_dict(self) -> dict:
        return {
            "executor": self.executor,
            "argv": list(self.argv),
            "cwd": self.cwd,
            "returncode": self.returncode,
            "duration_seconds": self.duration_seconds,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "files_touched": list(self.files_touched),
            "artifact_path": self.artifact_path,
            "timed_out": self.timed_out,
        }


class CodexExecAdapter:
    """Run Codex in a worktree with workspace-write and bounded execution."""

    def __init__(self, *, runner=None, timeout_seconds: int = 1800, clock=time.monotonic):
        self.runner = runner or _run_process
        self.timeout_seconds = timeout_seconds
        self.clock = clock

    def run(self, request: AgentRequest) -> AgentResult:
        worktree = str(Path(request.worktree).expanduser().resolve())
        artifact = _artifact_path(request, worktree)
        artifact.parent.mkdir(parents=True, exist_ok=True)
        argv = (
            "codex",
            "exec",
            "--cd",
            worktree,
            "--sandbox",
            "workspace-write",
            "--ask-for-approval",
            "never",
            "--output-last-message",
            str(artifact),
            "-",
        )
        prompt = build_implementation_prompt(request)
        return self._execute("codex", argv, worktree, prompt, artifact, request)

    def _execute(self, executor, argv, worktree, prompt, artifact, request):
        started = self.clock()
        raw = self.runner(
            argv,
            worktree,
            _redact_text(prompt),
            min(self.timeout_seconds, request.timeout_seconds),
        )
        result = _normalize_process_result(raw)
        safe_stdout = _redact_text(result.stdout)
        safe_stderr = _redact_text(result.stderr)
        _write_safe_artifact(artifact, safe_stdout)
        files = _files_touched(worktree)
        return AgentResult(
            executor=executor,
            argv=_sanitize_argv(argv),
            cwd=worktree,
            returncode=result.returncode,
            duration_seconds=max(result.duration_seconds, self.clock() - started),
            stdout=safe_stdout,
            stderr=safe_stderr,
            files_touched=files,
            artifact_path=str(artifact),
            timed_out=result.timed_out,
        )


class ClaudePrintAdapter(CodexExecAdapter):
    """Run Claude in noninteractive print mode, scoped to the worktree."""

    def run(self, request: AgentRequest) -> AgentResult:
        worktree = str(Path(request.worktree).expanduser().resolve())
        artifact = _artifact_path(request, worktree)
        prompt = _redact_text(build_implementation_prompt(request))
        argv = (
            "claude",
            "-p",
            "--add-dir",
            worktree,
            "--permission-mode",
            "acceptEdits",
            "--output-format",
            "json",
            "--no-session-persistence",
            prompt,
        )
        started = self.clock()
        raw = self.runner(argv, worktree, "", min(self.timeout_seconds, request.timeout_seconds))
        result = _normalize_process_result(raw)
        safe_stdout = _redact_text(result.stdout)
        safe_stderr = _redact_text(result.stderr)
        _write_safe_artifact(artifact, safe_stdout)
        return AgentResult(
            executor="claude",
            argv=_sanitize_argv(argv),
            cwd=worktree,
            returncode=result.returncode,
            duration_seconds=max(result.duration_seconds, self.clock() - started),
            stdout=safe_stdout,
            stderr=safe_stderr,
            files_touched=_files_touched(worktree),
            artifact_path=str(artifact),
            timed_out=result.timed_out,
        )


def build_implementation_prompt(request: AgentRequest) -> str:
    task = request.task
    evidence = request.evidence
    source_ids = ", ".join(getattr(evidence, "source_ids", ())) or "nenhum"
    citations = getattr(evidence, "citations", ())
    citation_text = "; ".join(
        f"[{item.number}] {item.source_id}: {item.cited_text}" for item in citations
    ) or "nenhuma citacao registrada"
    tests = ", ".join(request.test_paths) or "teste alvo a definir"
    return (
        "Implementar a tarefa abaixo na worktree delimitada.\n\n"
        f"Tarefa: {getattr(task, 'title', task)}\n"
        f"ID/origem: {getattr(task, 'id', '')} / {getattr(task, 'origin', '')}\n"
        f"Plano: {request.plan}\n"
        f"Testes alvo: {tests}\n"
        f"Source IDs autorizados: {source_ids}\n"
        f"Citations NotebookLM (citacoes): {citation_text}\n\n"
        "Obrigatorio: consultar e usar somente as citacoes fornecidas para a decisao normativa; "
        "escrever ou confirmar o teste RED antes da correcao; fazer a menor mudanca em escopo; "
        "preservar arquivos fora da tarefa; registrar qualquer incerteza ou premissa. "
        "Nao buscar fontes remotas, nao alterar fontes, nao fazer push/merge/reset destrutivo "
        "e nao ocultar uma falha de teste. Ao terminar, informe arquivos tocados, comandos e resultado."
    )


def _artifact_path(request: AgentRequest, worktree: str) -> Path:
    if request.artifact_path:
        return Path(request.artifact_path).expanduser().resolve()
    return Path(worktree) / ".loop-runtime" / "agent-last-message.txt"


_SENSITIVE_TEXT_RE = re.compile(
    r"(?i)(\b(?:authorization|bearer|token|cookie|password|api[_-]?key|secret)\b\s*[:=]\s*)([^\s,;}\]]+)"
)
_SENSITIVE_JSON_RE = re.compile(
    r"(?i)((?:\"|')?(?:authorization|bearer|token|cookie|password|api[_-]?key|secret)(?:\"|')?\s*:\s*[\"'])(.*?)([\"'])"
)


def _redact_text(value: str) -> str:
    text = _text(value)
    text = _SENSITIVE_JSON_RE.sub(r"\1[REDACTED]\3", text)
    return _SENSITIVE_TEXT_RE.sub(r"\1[REDACTED]", text)


def _write_safe_artifact(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            existing = ""
    safe_content = _redact_text(existing if existing else content)
    path.write_text(safe_content, encoding="utf-8")


def _run_process(argv, cwd, input_text, timeout_seconds):
    started = time.monotonic()
    try:
        completed = subprocess.run(
            _resolve_command(argv),
            cwd=cwd,
            input=input_text or None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        return _RawProcessResult(
            completed.returncode,
            completed.stdout or "",
            completed.stderr or "",
            time.monotonic() - started,
            False,
        )
    except subprocess.TimeoutExpired as error:
        return _RawProcessResult(
            -1,
            _text(error.stdout),
            _text(error.stderr),
            time.monotonic() - started,
            True,
        )
    except OSError as error:
        return _RawProcessResult(-1, "", str(error), time.monotonic() - started, False)


def _resolve_command(argv):
    """Resolve executable shims such as ``codex.cmd`` on Windows.

    The logical argv remains unchanged in ``AgentResult`` for auditability; only
    the subprocess invocation needs the concrete path accepted by CreateProcess.
    """
    command = [str(value) for value in argv]
    if command:
        resolved = shutil.which(command[0])
        if resolved:
            command[0] = resolved
    return command


@dataclass(frozen=True)
class _RawProcessResult:
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool


def _normalize_process_result(value) -> _RawProcessResult:
    if isinstance(value, _RawProcessResult):
        return value
    return _RawProcessResult(
        int(getattr(value, "returncode", -1)),
        _text(getattr(value, "stdout", "")),
        _text(getattr(value, "stderr", "")),
        float(getattr(value, "duration_seconds", 0.0)),
        bool(getattr(value, "timed_out", False)),
    )


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _sanitize_argv(argv) -> tuple[str, ...]:
    secret_flags = {"--token", "--cookie", "--password", "--api-key", "--secret"}
    sanitized = []
    redact_next = False
    for value in argv:
        text = str(value)
        if redact_next:
            sanitized.append("[REDACTED]")
            redact_next = False
        elif text.casefold() in secret_flags:
            sanitized.append(text)
            redact_next = True
        else:
            sanitized.append(
                re.sub(r"(?i)(token|cookie|password|api[_-]?key)=([^\s]+)", r"\1=[REDACTED]", text)
            )
    return tuple(sanitized)


def _files_touched(worktree: str) -> tuple[str, ...]:
    try:
        completed = subprocess.run(
            ["git", "-C", worktree, "status", "--short", "--untracked-files=all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return ()
    paths = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path and path not in paths:
            paths.append(path)
    return tuple(sorted(paths))
