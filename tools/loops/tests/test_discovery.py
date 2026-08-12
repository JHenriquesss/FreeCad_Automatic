from dataclasses import replace
from pathlib import Path

from tools.loops.discovery import discover_candidates, rank_candidates
from tools.loops.models import TaskCandidate


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def candidate(**changes):
    base = TaskCandidate(
        id="candidate-id",
        title="Candidate",
        discipline="estrutura",
        origin="framework/galpao_fw/wiki/06-open-threads.md:T16",
        priority=0,
        evidence_paths=("framework/galpao_fw/wiki/06-open-threads.md",),
        suggested_tests=("framework/galpao_fw/tests/test_frame2d_hardening.py",),
    )
    return replace(base, **changes)


def test_discovery_finds_unverified_fuzz_item():
    candidates = discover_candidates(PROJECT_ROOT)

    fuzz = next(item for item in candidates if "Fuzz interno dos motores" in item.title)

    assert fuzz.discipline == "estrutura"
    assert fuzz.origin == "framework/galpao_fw/wiki/06-open-threads.md:T16"
    assert fuzz.suggested_tests


def test_discovery_ignores_resolved_item():
    candidates = discover_candidates(PROJECT_ROOT)

    assert not any("dupla-conversão de janela" in item.title for item in candidates)
    assert any("multi-vão heterogêneo" in item.title for item in candidates)


def test_rank_prioritizes_structural_safety_over_documentation():
    documentation = candidate(
        id="documentation",
        title="Atualizar documentação",
        discipline="documentacao",
        origin="framework/galpao_fw/REVISAO-INDICE.md:1",
        priority=1,
    )
    structural_safety = candidate(
        id="structural-safety",
        title="Validar entrada estrutural contra segurança",
        discipline="estrutura",
        origin="framework/galpao_fw/wiki/06-open-threads.md:T16",
        priority=1,
    )

    assert rank_candidates((documentation, structural_safety)) == (
        structural_safety,
        documentation,
    )


def test_candidate_id_is_stable():
    first = discover_candidates(PROJECT_ROOT)
    second = discover_candidates(PROJECT_ROOT)

    first_fuzz = next(item for item in first if "Fuzz interno dos motores" in item.title)
    second_fuzz = next(item for item in second if "Fuzz interno dos motores" in item.title)

    assert first_fuzz.id == second_fuzz.id
    assert len(first_fuzz.id) == 12


def test_same_repository_state_has_same_order():
    first = discover_candidates(PROJECT_ROOT)
    second = discover_candidates(PROJECT_ROOT)

    assert first == second
    assert first == rank_candidates(first)
