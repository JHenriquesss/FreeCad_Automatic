"""Command-line entry point for the supervised development loop."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import subprocess

from .config import load_config
from .discovery import discover_candidates
from .research_nlm import CatalogIndex, NlmCliAdapter, NotebookMap
from .reviewer import ReviewAdapter
from .supervisor import DevelopmentSupervisor, SupervisorDeps
from .agents import ClaudePrintAdapter, CodexExecAdapter
from .tests_runner import TestRunner
from .worktrees import WorktreeManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Loop supervisionado de desenvolvimento do framework")
    parser.add_argument("--mode", choices=("dry-run", "supervised", "autonomous"), default="supervised")
    parser.add_argument("--max-iterations", type=_positive_int, default=1)
    parser.add_argument("--executor", choices=("codex", "claude"), default="codex")
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--config", default=None)
    parser.add_argument("--resume", default=None)
    parser.add_argument("--max-attempts-per-phase", type=_positive_int, default=3)
    parser.add_argument("--command-timeout", type=_positive_int, default=900)
    parser.add_argument("--build-timeout", type=_positive_int, default=1800)
    parser.add_argument("--notebook-map", default="fontes/notebooklm-mapa.md")
    parser.add_argument("--catalog", default="fontes/catalogo.csv")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    try:
        root = _detect_root(args.project_root)
        config = _load_cli_config(args, root)
        deps = _build_deps(args, config, root)
        supervisor = DevelopmentSupervisor(config, deps)
        outcome = supervisor.resume(args.resume) if args.resume else supervisor.run_once()
        print(f"loop_id={outcome.loop_id} outcome={outcome.outcome} phase={outcome.phase.value}")
        return 0
    except (ValueError, FileNotFoundError, argparse.ArgumentError) as error:
        print(f"configuração inválida: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        print(f"erro do loop: {error}", file=sys.stderr)
        return 1


def _detect_root(value):
    if value:
        return Path(value).expanduser().resolve()
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "framework" / "galpao_fw").is_dir() and (candidate / ".git").exists():
            return candidate
    return current


def _load_cli_config(args, root):
    if args.config:
        config = load_config(args.config, root)
        return type(config)(
            project_root=config.project_root,
            runtime_dir=config.runtime_dir,
            mode=args.mode,
            max_iterations=args.max_iterations,
            max_attempts_per_phase=args.max_attempts_per_phase,
            command_timeout_seconds=args.command_timeout,
            build_timeout_seconds=args.build_timeout,
            executor=args.executor,
        )
    from .models import LoopConfig

    return LoopConfig(
        project_root=str(root),
        runtime_dir=str(root / ".loop-runtime"),
        mode=args.mode,
        max_iterations=args.max_iterations,
        max_attempts_per_phase=args.max_attempts_per_phase,
        command_timeout_seconds=args.command_timeout,
        build_timeout_seconds=args.build_timeout,
        executor=args.executor,
    )


def _build_deps(args, config, root):
    map_path = root / args.notebook_map
    catalog_path = root / args.catalog
    notebook_map = NotebookMap.load(map_path)
    catalog = CatalogIndex.load(catalog_path)
    research = NlmCliAdapter(
        notebook_map,
        catalog,
        artifact_dir=Path(config.runtime_dir) / "artifacts",
        manual_request_path=Path(config.runtime_dir) / "manual-source-requests.md",
        timeout_seconds=min(config.command_timeout_seconds, 180),
    )
    agent_class = CodexExecAdapter if config.executor == "codex" else ClaudePrintAdapter
    test_runner = TestRunner(
        root,
        artifact_dir=Path(config.runtime_dir) / "test-results",
        command_timeout_seconds=config.command_timeout_seconds,
        build_timeout_seconds=config.build_timeout_seconds,
    )
    return SupervisorDeps(
        discover=discover_candidates,
        research=lambda candidate: _research_candidate(research, candidate),
        planner=_default_plan,
        red=lambda candidate, evidence, plan, worktree: _red_gate(
            test_runner, candidate, worktree, config
        ),
        agent=agent_class(timeout_seconds=config.command_timeout_seconds),
        tests=test_runner,
        reviewer=ReviewAdapter(),
        worktrees=WorktreeManager(root, config.runtime_dir),
        allowed_paths=_allowed_code_paths(root),
    )


def _red_gate(test_runner, candidate, worktree, config):
    runner = TestRunner(
        worktree,
        artifact_dir=Path(config.runtime_dir) / "red-results",
        command_timeout_seconds=config.command_timeout_seconds,
        build_timeout_seconds=config.build_timeout_seconds,
    )
    snapshot = runner.targeted(candidate.suggested_tests)
    return (
        not snapshot.timed_out
        and snapshot.returncode != 0
        and (snapshot.failed > 0 or snapshot.errors > 0)
    )


def _research_candidate(adapter, candidate):
    notebook_id = _notebook_id_for_candidate(adapter.notebook_map, candidate)
    if not notebook_id:
        raise ValueError("no notebook mapped for candidate discipline")
    if candidate.source_paths:
        sources = adapter.list_ready_sources_for_paths(notebook_id, candidate.source_paths)
    else:
        sources = adapter.list_ready_sources(notebook_id)
    source_ids = tuple(source.source_id for source in sources)
    if not source_ids:
        raise ValueError("no requested sources are ready")
    question = (
        f"Para a tarefa temática '{candidate.topic}' — '{candidate.title}', identifique apenas requisitos normativos "
        "aplicáveis, lacunas verificáveis e critérios de teste. Cite os source IDs."
    )
    return adapter.query(notebook_id, question, source_ids)


def _notebook_id_for_candidate(notebook_map, candidate):
    declared_paths = tuple(getattr(candidate, "source_paths", ()) or ())
    if declared_paths:
        notebook_ids = {
            notebook_map.notebook_id_for_path(path)
            for path in declared_paths
        }
        if None in notebook_ids:
            raise ValueError("source scope contains an unmapped local path")
        if len(notebook_ids) > 1:
            raise ValueError("source scope maps to multiple notebooks")
        return next(iter(notebook_ids))
    text = " ".join(
        (
            str(candidate.title),
            str(candidate.origin),
            *(str(path) for path in candidate.evidence_paths),
        )
    ).casefold()
    discipline_to_folder = {
        "estrutura": ("01_CONCRETO", "02_ACO", "03_FUNDACOES_GEOTECNIA", "04_ACOES_EQUIPAMENTOS"),
        "eletrica": ("05_ELETRICA",),
        "hidraulica": ("07_HIDRAULICA",),
        "esgoto": ("08_ESGOTO_PLUVIAL_REUSO",),
        "seguranca": ("09_INCENDIO", "11_ACESSIBILIDADE_SEGURANCA"),
        "bim_ifc": ("12_CATALOGOS_BIM",),
        "documentacao": ("00_FRAMEWORK",),
    }
    if candidate.discipline in {"estrutura", "seguranca"}:
        if any(term in text for term in ("funda", "geotec", "estaca", "sapata", "spt")):
            folders = ("03_FUNDACOES_GEOTECNIA",)
        elif any(term in text for term in ("concreto", "armadura", "baldrame")):
            folders = ("01_CONCRETO",)
        elif any(term in text for term in ("aço", "aco", "solda", "terca", "portico", "tapered", "gusset", "ligac")):
            folders = ("02_ACO",)
        elif any(term in text for term in ("ponte", "rolante", "equipamento")):
            folders = ("04_ACOES_EQUIPAMENTOS",)
        else:
            folders = discipline_to_folder.get(candidate.discipline, ("00_FRAMEWORK",))
    else:
        folders = discipline_to_folder.get(candidate.discipline, ("00_FRAMEWORK",))
    for folder in folders:
        notebook_id = notebook_map.notebook_ids_by_folder.get(folder)
        if notebook_id:
            return notebook_id
    return None


def _allowed_code_paths(root):
    """Build a conservative code-only allowlist; sources and runtime stay out."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return ()
    paths = []
    for value in result.stdout.splitlines():
        path = value.replace("\\", "/")
        if path.startswith(("fontes/", ".loop-runtime/", ".git/")):
            continue
        if path.startswith(("framework/galpao_fw/", "tools/")) and path not in paths:
            paths.append(path)
    return tuple(sorted(paths))


def _default_plan(candidate, evidence):
    return (
        f"Tarefa: {candidate.title}\n"
        f"Origem: {candidate.origin}\n"
        f"Testes sugeridos: {', '.join(candidate.suggested_tests) or 'definir teste local'}\n"
        "Usar somente as citações registradas e pedir decisão humana para incerteza."
    )


def _positive_int(value):
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError("deve ser inteiro positivo")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
