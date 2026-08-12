import json
from pathlib import Path

from .models import LoopConfig


_DEFAULTS = {
    "runtime_dir": ".loop-runtime",
    "mode": "supervised",
    "max_iterations": 1,
    "max_attempts_per_phase": 3,
    "command_timeout_seconds": 900,
    "build_timeout_seconds": 1800,
    "executor": "codex",
}


def load_config(path, project_root):
    root = Path(project_root).expanduser().resolve()
    config_path = Path(path).expanduser()
    if not config_path.is_absolute():
        config_path = root / config_path
    document = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("loop config must be an object")

    values = {**_DEFAULTS, **document}
    runtime_dir = Path(values["runtime_dir"]).expanduser()
    if not runtime_dir.is_absolute():
        runtime_dir = root / runtime_dir

    for name in (
        "max_iterations",
        "max_attempts_per_phase",
        "command_timeout_seconds",
        "build_timeout_seconds",
    ):
        value = values[name]
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"{name} must be a positive integer")

    if values["mode"] not in {"dry-run", "supervised", "autonomous"}:
        raise ValueError("mode must be dry-run, supervised, or autonomous")
    if not isinstance(values["executor"], str) or not values["executor"]:
        raise ValueError("executor must be a non-empty string")

    return LoopConfig(
        project_root=str(root),
        runtime_dir=str(runtime_dir.resolve()),
        mode=values["mode"],
        max_iterations=values["max_iterations"],
        max_attempts_per_phase=values["max_attempts_per_phase"],
        command_timeout_seconds=values["command_timeout_seconds"],
        build_timeout_seconds=values["build_timeout_seconds"],
        executor=values["executor"],
    )
