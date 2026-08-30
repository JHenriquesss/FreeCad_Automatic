"""Bounded adapters for implementation agents."""

from __future__ import annotations

from dataclasses import dataclass
import os
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
    red_result: object | None = None
    red_test_only: bool = False

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
            "--approve-for-me",
            "--output-last-message",
            str(artifact),
            "-",
        )
        prompt = (
            build_red_test_prompt(request)
            if request.red_test_only
            else build_implementation_prompt(request)
        )
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
        prompt = _redact_text(
            build_red_test_prompt(request)
            if request.red_test_only
            else build_implementation_prompt(request)
        )
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
    red_contract = _red_contract(request.red_result)
    return (
        "Implementar a tarefa abaixo na worktree delimitada.\n\n"
        f"Tarefa: {getattr(task, 'title', task)}\n"
        f"ID/origem: {getattr(task, 'id', '')} / {getattr(task, 'origin', '')}\n"
        f"Plano: {request.plan}\n"
        "Contrato executavel do RED (prioridade maxima): abra os testes alvo e trate cada assercao "
        "observavel, inclusive pytest.raises, como requisito ja decidido; nao peca aprovacao para "
        "interpretar um contrato demonstrado pelo teste.\n"
        f"Resultado RED: {red_contract}\n"
        f"Testes alvo: {tests}\n"
        f"Source IDs autorizados: {source_ids}\n"
        f"Citations NotebookLM (citacoes): {citation_text}\n\n"
        "A fase e o desenho ja foram aprovados pelo supervisor; esta chamada esta em modo de execucao. "
        "Nao invoque brainstorming, nao faca perguntas de aprovacao e nao pause para obter nova autorizacao; "
        "implemente agora conforme o RED confirmado e as restricoes abaixo. "
        "Obrigatorio: consultar e usar somente as citacoes fornecidas para a decisao normativa; "
        "o plano pode conter orientacao generica ou legada; o resultado do gate RED e as instrucoes "
        "explicitas deste prompt prevalecem sobre qualquer pedido generico de decisao humana; "
        "o teste RED ja foi confirmado pelo supervisor, portanto nao peca nova decisao sobre o contrato "
        "demonstrado; se houver conflito nao resolvido entre evidencia e teste, pare e registre-o; "
        "implemente a menor mudanca em escopo; "
        "preservar arquivos fora da tarefa; registrar qualquer incerteza ou premissa. "
        "Nao buscar fontes remotas, nao alterar fontes, nao fazer push/merge/reset destrutivo "
        "e nao ocultar uma falha de teste. Ao terminar, informe arquivos tocados, comandos e resultado."
    )


def build_red_test_prompt(request: AgentRequest) -> str:
    task = request.task
    evidence = request.evidence
    source_ids = ", ".join(getattr(evidence, "source_ids", ())) or "nenhum"
    citations = getattr(evidence, "citations", ())
    citation_text = "; ".join(
        f"[{item.number}] {item.source_id}: {item.cited_text[:900]}"
        for item in citations
    ) or "nenhuma citação auditável registrada"
    tests = ", ".join(request.test_paths) or "teste alvo a definir"
    return (
        "Criar somente o teste RED da tarefa abaixo na worktree delimitada.\n\n"
        f"Tarefa: {getattr(task, 'title', task)}\n"
        f"ID/origem: {getattr(task, 'id', '')} / {getattr(task, 'origin', '')}\n"
        f"Plano: {request.plan}\n"
        f"Testes alvo existentes ou sugeridos: {tests}\n"
        f"Source IDs autorizados: {source_ids}\n"
        f"Citações auditáveis autorizadas: {citation_text}\n"
        "Esta e uma etapa de reconciliação do Loop 1.5. O objetivo e tornar observavel, por meio de uma "
        "asserção focada, o comportamento que a tarefa precisa implementar e que ainda nao esta demonstrado. "
        "Crie um novo teste Python dentro de um diretorio tests, preferencialmente um arquivo dedicado; nao "
        "altere codigo de produção, nao altere testes existentes, nao implemente a correção e nao remova "
        "cobertura. O teste deve falhar contra o estado atual por uma razão funcional clara, sem depender de "
        "rede, NotebookLM ou ambiente externo. Execute o teste criado e deixe o resultado RED reproduzível. "
        "Use o texto das citações como autoridade normativa: uma pendência, README, plano legado ou premissa "
        "local nunca pode virar requisito só porque aparece no título da tarefa. Se uma premissa local conflitar "
        "com a citação, não a codifique; escolha uma asserção diretamente sustentada pelo trecho citado ou "
        "estacione registrando o conflito. Não busque fontes remotas, não altere fontes, não faça "
        "push/merge/reset destrutivo e registre premissas. Ao terminar, informe o arquivo criado, a asserção "
        "demonstrada e o comando executado."
    )


def _red_contract(result) -> str:
    if result is None:
        return "RED confirmado; os testes alvo contem o contrato executavel."
    if isinstance(result, dict):
        get = result.get
    else:
        get = lambda name, default=None: getattr(result, name, default)
    failed_tests = tuple(get("failed_tests", ()) or ())
    error_tests = tuple(get("error_tests", ()) or ())
    identifiers = failed_tests + error_tests
    listed = ", ".join(str(item) for item in identifiers[:30]) or "ids nao persistidos; abrir os testes alvo"
    return (
        f"kind={get('kind', 'red')}, returncode={get('returncode', 'n/a')}, "
        f"failed={get('failed', 'n/a')}, errors={get('errors', 'n/a')}; "
        f"falhas observadas: {listed}"
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
    process = None
    try:
        process = subprocess.Popen(
            _resolve_command(argv),
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = process.communicate(input=input_text or None, timeout=timeout_seconds)
        return _RawProcessResult(
            process.returncode,
            stdout or "",
            stderr or "",
            time.monotonic() - started,
            False,
        )
    except subprocess.TimeoutExpired as error:
        stdout, stderr = _stop_after_timeout(process, error)
        return _RawProcessResult(
            -1,
            stdout,
            stderr,
            time.monotonic() - started,
            True,
        )
    except OSError as error:
        return _RawProcessResult(-1, "", str(error), time.monotonic() - started, False)


def _stop_after_timeout(process, timeout_error):
    """Stop an executor and collect all output already emitted.

    On Windows, Codex is normally launched through ``codex.cmd`` and a Node
    child. Terminating only the shim leaves that child alive and can keep the
    scheduler blocked indefinitely, so the whole process tree is killed.
    """
    partial_stdout = _text(timeout_error.stdout)
    partial_stderr = _text(timeout_error.stderr)
    if process is None:
        return partial_stdout, partial_stderr

    if os.name == "nt":
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if result.returncode == 0:
                return _collect_after_timeout(process, partial_stdout, partial_stderr)
        except OSError:
            pass
        _terminate_process(process)
    else:
        _terminate_process(process)

    return _collect_after_timeout(process, partial_stdout, partial_stderr)


def _collect_after_timeout(process, partial_stdout, partial_stderr):
    try:
        stdout, stderr = process.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        _kill_process(process)
        stdout, stderr = process.communicate()
    return _merge_output(partial_stdout, stdout), _merge_output(partial_stderr, stderr)


def _terminate_process(process):
    try:
        process.terminate()
    except (AttributeError, OSError):
        _kill_process(process)


def _kill_process(process):
    try:
        process.kill()
    except (AttributeError, OSError):
        pass


def _merge_output(partial, complete):
    partial_text = _text(partial)
    complete_text = _text(complete)
    if not partial_text:
        return complete_text
    if not complete_text:
        return partial_text
    if partial_text in complete_text:
        return complete_text
    return partial_text + complete_text


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
