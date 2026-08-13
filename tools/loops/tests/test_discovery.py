from dataclasses import replace
from hashlib import sha1
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


def test_resolved_status_markers_are_ignored(tmp_path):
    wiki = tmp_path / "framework" / "galpao_fw" / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "06-open-threads.md").write_text(
        "\n".join(
            [
                "# Threads",
                "## T01 — RESOLVIDO",
                "- falta corrigir o item antigo",
                "## T02 — MERGED",
                "- pendente apenas no histórico",
                "## T03 — FECHADO",
                "- ainda aberto apenas no registro antigo",
                "## T04 — HOMOLOGADO",
                "- fuzz executado no passado",
                "## T05 — APROVADO",
                "- não verificado na auditoria anterior",
                "## T06 — FEITO",
                "- bloqueado antes da correção",
                "## T07 — acompanhamento",
                "- não re-verificado no estado atual",
            ]
        ),
        encoding="utf-8",
    )

    candidates = discover_candidates(tmp_path)

    assert not any(item.origin.endswith(":T01") for item in candidates)
    assert not any(item.origin.endswith(":T02") for item in candidates)
    assert not any(item.origin.endswith(":T03") for item in candidates)
    assert not any(item.origin.endswith(":T04") for item in candidates)
    assert not any(item.origin.endswith(":T05") for item in candidates)
    assert not any(item.origin.endswith(":T06") for item in candidates)
    assert any(item.origin.endswith(":T07") for item in candidates)


def test_open_source_checkbox_is_discovered_and_checked_checkbox_is_ignored():
    candidates = discover_candidates(PROJECT_ROOT)

    open_item = next(
        item
        for item in candidates
        if "NBR 6118" in item.title
        and item.origin.startswith("fontes/pendencias-atualizacao.md:")
    )

    assert open_item.origin.startswith("fontes/pendencias-atualizacao.md:")
    assert not any("Organizar a" in item.title for item in candidates)


def test_foundation_pending_item_is_structural_and_uses_relevant_tests():
    candidates = discover_candidates(PROJECT_ROOT)

    foundation = next(item for item in candidates if "Fatores de segurança 1,5" in item.title)

    assert foundation.discipline == "estrutura"
    assert foundation.suggested_tests
    assert all(
        not any(term in path.casefold() for term in ("eletrico", "incendio", "calha"))
        for path in foundation.suggested_tests
    )
    assert any(
        any(term in path.casefold() for term in ("fundacao", "geotec", "validacao"))
        for path in foundation.suggested_tests
    )


def test_normative_prose_is_not_discovered():
    candidates = discover_candidates(PROJECT_ROOT)

    assert not any("retilineidade" in item.title.casefold() for item in candidates)
    assert not any(item.origin.lower().endswith(".txt") for item in candidates)


def test_revision_index_table_does_not_become_a_candidate():
    candidates = discover_candidates(PROJECT_ROOT)

    assert not any("REVISAO-INDICE.md" in item.origin for item in candidates)


def test_explicit_historical_item_is_ignored():
    candidates = discover_candidates(PROJECT_ROOT)

    assert not any("PNG da" in item.title for item in candidates)


def test_completed_revision_statuses_are_ignored(tmp_path):
    revision_root = tmp_path / "framework" / "galpao_fw"
    revision_root.mkdir(parents=True)
    (revision_root / "REVISAO-TESTE.md").write_text(
        "\n".join(
            [
                "# Revisao",
                "## Parecer",
                "- validar o item - JA IMPLEMENTADO",
                "- confirmar o ponto - ATENDE",
                "- conferir a regra - CORRIGIDO",
                "- confirmar a pendencia - ACATADO",
                "- confirmar a pendencia - PENDENTE",
            ]
        ),
        encoding="utf-8",
    )

    candidates = discover_candidates(tmp_path)

    assert len(candidates) == 1
    assert "PENDENTE" in candidates[0].title


def test_candidate_id_matches_required_formula():
    candidates = discover_candidates(PROJECT_ROOT)
    fuzz = next(item for item in candidates if "Fuzz interno dos motores" in item.title)

    expected = sha1(f"{fuzz.origin}\n{fuzz.title}".encode("utf-8")).hexdigest()[:12]

    assert fuzz.id == expected
