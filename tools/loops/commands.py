"""Bounded subprocess execution for the development loop."""

from __future__ import annotations

import subprocess
from pathlib import Path
import time

from .models import CommandResult


class CommandRunner:
    """Run one external command while retaining all observable output."""

    def __init__(self, *, popen_factory=None, clock=time.monotonic):
        self._popen_factory = popen_factory or subprocess.Popen
        self._clock = clock

    def run(self, argv, cwd, timeout_seconds) -> CommandResult:
        command = tuple(str(value) for value in argv)
        if not command:
            raise ValueError("command must contain at least one argument")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        working_directory = str(Path(cwd).resolve())
        started = self._clock()
        process = None
        try:
            process = self._popen_factory(
                list(command),
                cwd=working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout_seconds)
                returncode = process.returncode
                timed_out = False
            except subprocess.TimeoutExpired as timeout_error:
                stdout, stderr = self._stop_after_timeout(process)
                stdout = _merge_partial_output(timeout_error.output, stdout)
                stderr = _merge_partial_output(timeout_error.stderr, stderr)
                returncode = -1
                timed_out = True
        except OSError as error:
            stdout = ""
            stderr = str(error)
            returncode = -1
            timed_out = False

        duration = max(0.0, self._clock() - started)
        return CommandResult(
            argv=command,
            cwd=working_directory,
            returncode=returncode,
            duration_seconds=duration,
            stdout=_as_text(stdout),
            stderr=_as_text(stderr),
            timed_out=timed_out,
        )

    @staticmethod
    def _stop_after_timeout(process):
        try:
            process.terminate()
        except (AttributeError, OSError):
            try:
                process.kill()
            except (AttributeError, OSError):
                pass
        try:
            return process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except (AttributeError, OSError):
                pass
            return process.communicate()


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _merge_partial_output(partial, complete) -> str:
    partial_text = _as_text(partial)
    complete_text = _as_text(complete)
    if not partial_text:
        return complete_text
    if not complete_text:
        return partial_text
    if partial_text in complete_text:
        return complete_text
    return partial_text + complete_text
