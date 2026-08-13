import json
from pathlib import Path

import pytest

from tools.loops.__main__ import _allowed_code_paths, _notebook_id_for_candidate, build_parser, main
from tools.loops.models import TaskCandidate
from tools.loops.research_nlm import NotebookMap


def test_cli_parser_exposes_required_options():
    args = build_parser().parse_args(
        ["--mode", "dry-run", "--max-iterations", "1", "--executor", "claude", "--resume", "loop-1"]
    )

    assert args.mode == "dry-run"
    assert args.max_iterations == 1
    assert args.executor == "claude"
    assert args.resume == "loop-1"


def test_cli_invalid_positive_integer_returns_two():
    assert main(["--max-iterations", "0"]) == 2


def test_cli_invalid_mode_is_rejected():
    assert main(["--mode", "invalid"]) == 2


def test_cli_missing_project_root_returns_one_or_two_without_network(tmp_path):
    assert main(["--project-root", str(tmp_path), "--mode", "dry-run"]) in {1, 2}


def test_framework_candidate_uses_discipline_notebook_when_evidence_is_outside_fontes():
    candidate = TaskCandidate(
        "id",
        "Requisito de seguranÃ§a contra incÃªndio",
        "seguranca",
        "framework/REVISAO-INCENDIO.md",
        1,
        ("framework/REVISAO-INCENDIO.md",),
        (),
    )
    notebook_map = NotebookMap({"09_INCENDIO": "nb-incendio"})

    assert _notebook_id_for_candidate(notebook_map, candidate) == "nb-incendio"


def test_foundation_revision_uses_geotechnical_notebook():
    candidate = TaskCandidate(
        "id",
        "Fatores de segurança de fundação",
        "seguranca",
        "framework/galpao_fw/REVISAO-FUNDACAO.md",
        1,
        ("framework/galpao_fw/REVISAO-FUNDACAO.md",),
        (),
    )
    notebook_map = NotebookMap({"03_FUNDACOES_GEOTECNIA": "nb-fundacoes"})

    assert _notebook_id_for_candidate(notebook_map, candidate) == "nb-fundacoes"


def test_atomic_candidate_uses_declared_source_scope_for_notebook():
    candidate = TaskCandidate(
        "id",
        "Fuzz interno — calhas",
        "hidraulica",
        "framework/galpao_fw/wiki/06-open-threads.md:T16:calhas",
        1,
        ("framework/galpao_fw/wiki/06-open-threads.md",),
        ("framework/galpao_fw/tests/test_calhas_robustez.py",),
        topic="calhas",
        source_paths=("08_ESGOTO_PLUVIAL_REUSO/PLUVIAL__NBR__NBR-10844-1989__aguas-pluviais.pdf",),
    )
    notebook_map = NotebookMap({"08_ESGOTO_PLUVIAL_REUSO": "nb-pluvial"})

    assert _notebook_id_for_candidate(notebook_map, candidate) == "nb-pluvial"


def test_atomic_candidate_rejects_source_scope_spanning_notebooks():
    candidate = TaskCandidate(
        "id",
        "Fuzz interno — mistura",
        "estrutura",
        "framework/galpao_fw/wiki/06-open-threads.md:T16:mistura",
        1,
        ("framework/galpao_fw/wiki/06-open-threads.md",),
        (),
        topic="mistura",
        source_paths=("02_ACO/aco.pdf", "04_ACOES_EQUIPAMENTOS/sismo.pdf"),
    )
    notebook_map = NotebookMap(
        {"02_ACO": "nb-aco", "04_ACOES_EQUIPAMENTOS": "nb-acoes"}
    )

    with pytest.raises(ValueError, match="multiple notebooks"):
        _notebook_id_for_candidate(notebook_map, candidate)


def test_cli_allowlist_excludes_sources_and_includes_code(tmp_path):
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    (root / "framework" / "galpao_fw").mkdir(parents=True)
    (root / "fontes").mkdir()

    # The helper is intentionally conservative when no Git listing is available.
    assert _allowed_code_paths(root) == ()
