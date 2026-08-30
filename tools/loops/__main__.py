"""Command-line entry point for the supervised development loop."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
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
    parser.add_argument(
        "--retry-blocked",
        action="store_true",
        help="reconsiderar nesta execu\u00e7\u00e3o tarefas bloqueadas por fontes",
    )
    parser.add_argument(
        "--recover-orphan",
        action="store_true",
        help="estacionar explicitamente um ledger ativo deixado por processo interrompido",
    )
    parser.add_argument(
        "--exclude-task-id",
        dest="exclude_task_ids",
        action="append",
        default=[],
        help="adiar um candidato nesta execução; pode ser repetido",
    )
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
        if args.recover_orphan and args.resume:
            print(
                "configuração inválida: --recover-orphan cannot be combined with --resume",
                file=sys.stderr,
            )
            return 2
        root = _detect_root(args.project_root)
        config = _load_cli_config(args, root)

        def supervisor_factory(iteration_config):
            return DevelopmentSupervisor(
                iteration_config,
                _build_deps(args, iteration_config, root),
            )

        if args.recover_orphan:
            outcome = supervisor_factory(config).recover_orphan()
            _write_scheduler_summary(
                config,
                [outcome],
                config.excluded_task_ids,
                "orphan_recovered",
            )
            print(f"loop_id={outcome.loop_id} outcome={outcome.outcome} phase={outcome.phase.value}")
            return 0

        outcomes = _run_iterations(config, supervisor_factory, resume=args.resume)
        outcome = outcomes[-1]
        print(f"loop_id={outcome.loop_id} outcome={outcome.outcome} phase={outcome.phase.value}")
        return 0
    except (ValueError, FileNotFoundError, argparse.ArgumentError) as error:
        print(f"configuração inválida: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        print(f"erro do loop: {error}", file=sys.stderr)
        return 1


def _run_iterations(config, supervisor_factory, *, resume=None):
    """Run independent iterations, skipping only tasks blocked by sources.

    A source gap is local to one candidate: it is recorded by that candidate's
    ledger and the scheduler may try another candidate. Any implementation,
    test, review, or timeout failure stops the scheduler for human diagnosis.
    ``dry-run`` deliberately remains one iteration even when the configured
    limit is larger.
    """
    outcomes = []
    excluded = list(config.excluded_task_ids)
    next_resume = resume
    stop_reason = None

    max_iterations = 1 if config.mode == "dry-run" else config.max_iterations
    for _ in range(max_iterations):
        iteration_config = replace(config, excluded_task_ids=tuple(excluded))
        supervisor = supervisor_factory(iteration_config)
        outcome = supervisor.resume(next_resume) if next_resume else supervisor.run_once()
        next_resume = None
        outcomes.append(outcome)

        if outcome.outcome == "manual_source_required":
            task = getattr(getattr(outcome, "state", None), "task", None)
            task_id = getattr(task, "id", None)
            if not task_id or task_id in excluded:
                stop_reason = "manual_source_required_repeated"
                break
            excluded.append(task_id)
            continue

        if outcome.outcome == "promoted":
            continue

        stop_reason = outcome.outcome
        break
    else:
        stop_reason = "max_iterations"

    _write_scheduler_summary(config, outcomes, excluded, stop_reason)
    return outcomes


def _write_scheduler_summary(config, outcomes, excluded, stop_reason):
    runtime_dir = Path(config.runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for outcome in outcomes:
        task = getattr(getattr(outcome, "state", None), "task", None)
        rows.append(
            {
                "loop_id": getattr(outcome, "loop_id", None),
                "outcome": getattr(outcome, "outcome", None),
                "phase": getattr(getattr(outcome, "phase", None), "value", None),
                "task_id": getattr(task, "id", None),
            }
        )
    payload = {
        "mode": config.mode,
        "max_iterations": config.max_iterations,
        "iterations_run": len(rows),
        "excluded_task_ids": list(excluded),
        "stop_reason": stop_reason,
        "outcomes": rows,
    }
    (runtime_dir / "scheduler-last.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


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
            excluded_task_ids=tuple(args.exclude_task_ids) or config.excluded_task_ids,
            retry_blocked=args.retry_blocked or config.retry_blocked,
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
        excluded_task_ids=tuple(args.exclude_task_ids),
        retry_blocked=args.retry_blocked,
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
        source_root=root / "fontes",
    )
    agent_class = CodexExecAdapter if config.executor == "codex" else ClaudePrintAdapter
    def tests_factory(worktree):
        return TestRunner(
            worktree,
            artifact_dir=Path(config.runtime_dir) / "test-results",
            command_timeout_seconds=config.command_timeout_seconds,
            build_timeout_seconds=config.build_timeout_seconds,
        )

    test_runner = tests_factory(root)
    agent = agent_class(timeout_seconds=config.command_timeout_seconds)
    return SupervisorDeps(
        discover=discover_candidates,
        research=lambda candidate: _research_candidate(research, candidate),
        planner=_default_plan,
        red=lambda candidate, evidence, plan, worktree: _red_gate(
            test_runner, candidate, worktree, config
        ),
        agent=agent,
        red_author=agent,
        tests=test_runner,
        tests_factory=tests_factory,
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
    missing_test_paths = [
        path for path in candidate.suggested_tests if not _test_path_exists(worktree, path)
    ]
    if missing_test_paths:
        status = "missing_red_test"
    elif snapshot.timed_out:
        status = "timeout"
    elif snapshot.returncode == 0 and snapshot.failed == 0 and snapshot.errors == 0:
        status = "green_target"
    elif snapshot.returncode != 0 and (snapshot.failed > 0 or snapshot.errors > 0):
        status = "red_observed"
    else:
        status = "execution_error"
    return {
        "kind": "red",
        "status": status,
        "successful": (
            not snapshot.timed_out
            and snapshot.returncode != 0
            and (snapshot.failed > 0 or snapshot.errors > 0)
        ),
        "returncode": snapshot.returncode,
        "failed": snapshot.failed,
        "errors": snapshot.errors,
        "failed_tests": list(snapshot.failed_tests),
        "error_tests": list(snapshot.error_tests),
        "target_paths": list(snapshot.target_paths),
        "missing_test_paths": missing_test_paths,
        "timed_out": snapshot.timed_out,
    }


def _test_path_exists(worktree, path):
    value = Path(str(path))
    if value.is_absolute():
        return value.exists()
    candidates = (
        Path(worktree) / value,
        Path(worktree) / "framework" / "galpao_fw" / value,
    )
    return any(candidate.exists() for candidate in candidates)


def _research_candidate(adapter, candidate):
    notebook_id = _notebook_id_for_candidate(adapter.notebook_map, candidate)
    if not notebook_id:
        raise ValueError("no notebook mapped for candidate discipline")
    if not candidate.source_paths:
        raise ValueError(
            "candidate source scope is required; declare source_paths before querying NotebookLM"
        )
    sources = adapter.list_ready_sources_for_paths(notebook_id, candidate.source_paths)
    source_ids = tuple(source.source_id for source in sources)
    if not source_ids:
        raise ValueError("no requested sources are ready")
    question = _research_question(candidate, source_ids)
    retry_question = _research_retry_question(candidate, source_ids)
    if retry_question is None:
        return adapter.query(notebook_id, question, source_ids)
    return adapter.query(notebook_id, question, source_ids, retry_question=retry_question)


def _research_question(candidate, source_ids):
    authorized_ids = ", ".join(source_ids)
    if candidate.topic == "fogo_armazenamento":
        return (
            "Para armazenamento protegido por chuveiros na ABNT NBR 16981:2021, consulte somente as secoes "
            "4.1.1, 4.6.1, 5.2.2.4, 6.3.1.2.1, 6.3.4.3.1, 8.3.2.3, 8.3.3.3, 9.1.4.1.4, 9.1.4.1.5, B.2.2.1 e B.4.3.1 "
            "da fonte autorizada. Liste requisitos verificaveis para risco da mercadoria, "
            "altura, densidade, area de operacao, encapsulamento, ESFR, chuveiros intraprateleiras, bobinas de papel "
            "e a lacuna de papel tissue. Verifique o limite de 115 L/min acima de 7,6 m. Informe secao/tabela, condicao e limite quando a fonte trouxer. Dados "
            "ausentes, tabelas nao citadas e criterios nao determinados devem retornar como lacuna; nao invente "
            "defaults, nao use NBR 10897, NBR 13792, instrucao estadual ou fabricante, e cite cada item usando "
            f"o source ID exato entre: {authorized_ids}."
        )
    if candidate.topic == "estaca":
        return (
            "Para estacas na ABNT NBR 6122:2022, liste somente requisitos verificaveis para invariantes de entrada, "
            "limites geometricos/executivos, ausencia de valores invalidos e criterios de teste. "
            "Separe o que a norma exige do que e apenas uma guarda de software. Informe a secao/tabela da norma "
            "para cada item e cite cada requisito usando o source ID exato entre: "
            f"{authorized_ids}."
        )
    if candidate.topic == "fundacao_estabilidade":
        return (
            "Para estabilidade geotecnica de fundacoes na ABNT NBR 6122:2022, liste somente requisitos "
            "verificaveis para fatores de seguranca, tombamento e deslizamento. Separe o que a norma "
            "define do que e premissa de software, informe secao/tabela, declare lacunas sem valor "
            "universal e cite cada item usando o source ID exato entre: "
            f"{authorized_ids}."
        )
    if candidate.topic == "gusset":
        return (
            "Para gusset e ligações, liste somente requisitos verificáveis da NBR 8800 "
            "para espessura, furos, bordas, soldas e ausência de valores inválidos. "
            f"Cite cada item usando o source ID exato entre: {authorized_ids}."
        )
    if candidate.topic == "ligacoes":
        return (
            "Para ligações, liste somente requisitos verificáveis da NBR 8800 para furos, "
            "bordas, espaçamentos, block shear e valores inválidos. "
            f"Cite cada item usando o source ID exato entre: {authorized_ids}."
        )
    if candidate.topic == "base_chumbador":
        return (
            "Para base_chumbador, liste somente requisitos verificáveis da NBR 8800 para placas de base, "
            "chumbadores/parafusos, furos, esmagamento, tração e cisalhamento; se a norma não cobrir "
            "breakout/concreto, declare isso. "
            f"Cite cada item usando o source ID exato entre: {authorized_ids}."
        )
    if candidate.topic == "populacao_saida":
        return (
            "Para população de depósitos, consulte somente a NBR 9077:2025, seções 5.1, 5.1.2, 5.2 e Tabela 4: "
            "informe quais áreas entram ou saem da área computável, confirme a densidade de 1 pessoa por 30 m² "
            "para depósitos em geral, calcule sem arredondar e declare explicitamente se a norma define regra de "
            "arredondamento. Cite cada item usando o source ID exato entre: "
            f"{authorized_ids}."
        )
    if candidate.topic == "extintores":
        return (
            "Para proteção por extintores na ABNT NBR 12693 (edição da fonte), liste somente requisitos "
            "verificáveis de seleção, distribuição, capacidade/quantidade, posicionamento e limitações "
            "expressamente presentes no texto. Informe seção/tabela para cada item, declare quando a norma "
            "não cobrir o ponto e cite cada requisito usando o source ID exato entre: "
            f"{authorized_ids}."
        )
    if candidate.topic == "sinalizacao_incendio":
        return (
            "Para sinalização de segurança contra incêndio na ABNT NBR 16820:2022, liste somente "
            "requisitos verificáveis de tipos, finalidade, características, localização e aplicação "
            "expressamente presentes no texto. Informe seção/tabela para cada item, declare quando a norma "
            "não cobrir o ponto e cite cada requisito usando o source ID exato entre: "
            f"{authorized_ids}."
        )
    if candidate.topic == "fogo_concreto":
        return (
            "Para concreto em situação de incêndio na ABNT NBR 15200 (edição da fonte), liste somente "
            "requisitos verificáveis de dimensionamento, detalhamento, resistência e critérios de exposição "
            "expressamente presentes no texto. Informe seção/tabela para cada item, declare quando a norma "
            "não cobrir o ponto e cite cada requisito usando o source ID exato entre: "
            f"{authorized_ids}."
        )
    if candidate.topic == "resistencia_fogo":
        return (
            "Para exigências de resistência ao fogo na ABNT NBR 14432 (edição da fonte), liste somente "
            "requisitos verificáveis de classificação, tempos requeridos, aplicação e critérios de "
            "resistência expressamente presentes no texto. Informe seção/tabela para cada item, declare "
            "quando a norma não cobrir o ponto e cite cada requisito usando o source ID exato entre: "
            f"{authorized_ids}."
        )
    if candidate.topic == "fogo_aco":
        return (
            "Para estruturas de aço e mistas em situação de incêndio na ABNT NBR 14323 (edição da fonte), "
            "liste somente requisitos verificáveis de análise, dimensionamento, proteção e resistência "
            "expressamente presentes no texto. Informe seção/tabela para cada item, declare quando a norma "
            "não cobrir o ponto e cite cada requisito usando o source ID exato entre: "
            f"{authorized_ids}."
        )
    if candidate.topic == "agua_quente_segura":
        return (
            "Para a segurança da rede predial de água quente na ABNT NBR 5626:2020, liste somente requisitos "
            "verificáveis das seções 6.7, 6.9, 6.10, 6.11, 6.12 e 6.13 para vazões explicitadas, pressões, "
            "temperatura, prevenção de escaldamento, superfícies, dilatação, perdas térmicas e dispositivos de "
            "segurança. Informe a seção/condição de cada requisito, declare lacunas sem parâmetros universais, "
            "não invente limites nem use outra norma, e cite cada item usando o source ID exato entre: "
            f"{authorized_ids}."
        )
    return (
        f"Para {candidate.topic}, liste somente invariantes normativas, riscos de crash/NaN e critérios de teste. "
        f"Cite cada requisito com o source ID exato entre: {authorized_ids}."
    )


def _research_retry_question(candidate, source_ids):
    authorized_ids = ", ".join(source_ids)
    if candidate.topic == "fogo_armazenamento":
        return (
            "NBR 16981:2021 para armazenamento: responda em no maximo 12 itens; cite somente as secoes 4.1.1, "
            "4.6.1, 5.2.2.4, 6.3.1.2.1, 6.3.4.3.1, 8.3.2.3, 8.3.3.3, 9.1.4.1.4, 9.1.4.1.5, B.2.2.1 e B.4.3.1, "
            "informe requisito e limite/condicao, declare lacunas sem criterio na fonte, nao invente "
            "defaults nem use outra norma, inclua citacoes textuais e use somente o source ID exato "
            f"{authorized_ids}."
        )
    if candidate.topic == "estaca":
        return (
            "NBR 6122:2022 para estacas: responda em no maximo 8 itens; para cada item, informe secao/tabela, "
            "requisito verificavel e valor/limite; nao invente guardas de software; use somente o source ID exato "
            f"{authorized_ids} e inclua citacoes textuais."
        )
    if candidate.topic == "fundacao_estabilidade":
        return (
            "NBR 6122:2022 para estabilidade de fundacoes: responda em no maximo 8 itens; informe "
            "secao/tabela, fator ou criterio verificavel, aplicacao a tombamento/deslizamento e lacunas; "
            "nao invente valores nem use outra norma; use somente o source ID exato "
            f"{authorized_ids} e inclua citacoes textuais."
        )
    if candidate.topic == "gusset":
        return (
            "Gusset na NBR 8800: cite somente requisitos verificáveis para tração, compressão, "
            "solda, furos e block shear; informe limites físicos inválidos. "
            f"Use somente o source ID exato {authorized_ids}."
        )
    if candidate.topic == "ligacoes":
        return (
            "Ligações NBR 8800: cite requisitos verificáveis de furos, bordas, espaçamentos, "
            "block shear e valores inválidos. Use somente o source ID exato "
            f"{authorized_ids}."
        )
    if candidate.topic == "base_chumbador":
        return (
            "Base/chumbador NBR 8800: cite regras de placas de base, chumbadores/parafusos, furos, "
            "esmagamento, tração/cisalhamento e limites inválidos; declare ausência de regra quando aplicável. "
            f"Use somente o source ID exato {authorized_ids}."
        )
    if candidate.topic == "populacao_saida":
        return (
            "População NBR 9077:2025: cite somente as seções 5.1, 5.1.2, 5.2 e Tabela 4, áreas computáveis, "
            "30 m² por pessoa e a presença ou ausência de regra de arredondamento. Use somente o source ID exato "
            f"{authorized_ids}."
        )
    if candidate.topic == "extintores":
        return (
            "NBR 12693 para extintores: responda em no máximo 8 itens; informe seção/tabela, requisito "
            "verificável e limite ou condição; não invente regras fora da fonte e inclua citações textuais. "
            f"Use somente o source ID exato {authorized_ids}."
        )
    if candidate.topic == "sinalizacao_incendio":
        return (
            "NBR 16820:2022 para sinalização de segurança contra incêndio: responda em no máximo 8 itens; informe "
            "seção/tabela, requisito verificável e condição de aplicação; não invente regras fora da fonte e "
            "inclua citações textuais. "
            f"Use somente o source ID exato {authorized_ids}."
        )
    if candidate.topic == "fogo_concreto":
        return (
            "NBR 15200 para concreto em situação de incêndio: responda em no máximo 8 itens; informe "
            "seção/tabela, requisito verificável e limite ou condição; não invente regras fora da fonte, "
            "declare lacunas de cobertura e inclua citações textuais. "
            f"Use somente o source ID exato {authorized_ids}."
        )
    if candidate.topic == "resistencia_fogo":
        return (
            "NBR 14432 para exigências de resistência ao fogo: responda em no máximo 8 itens; informe "
            "seção/tabela, requisito verificável e classificação/tempo quando a fonte trouxer; não invente "
            "regras fora da fonte, declare lacunas de cobertura e inclua citações textuais. "
            f"Use somente o source ID exato {authorized_ids}."
        )
    if candidate.topic == "fogo_aco":
        return (
            "NBR 14323 para estruturas de aço e mistas em situação de incêndio: responda em no máximo 8 itens; "
            "informe seção/tabela, requisito verificável e limite ou condição; não invente regras fora da fonte, "
            "declare lacunas de cobertura e inclua citações textuais. "
            f"Use somente o source ID exato {authorized_ids}."
        )
    if candidate.topic == "agua_quente_segura":
        return (
            "NBR 5626:2020 para segurança de água quente: responda em no máximo 10 itens; informe seção/condição, "
            "requisito verificável e condição de aplicação para as seções 6.7, 6.9, 6.10, 6.11, 6.12 e 6.13; "
            "inclua citações textuais, declare lacunas sem valor universal, não invente regras e use somente o source ID exato "
            f"{authorized_ids}."
        )
    return None


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
        "Usar somente as citações registradas; se houver conflito normativo real não resolvido, "
        "estacionar para decisão humana sem reabrir contrato já demonstrado pelos testes."
    )


def _positive_int(value):
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError("deve ser inteiro positivo")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
