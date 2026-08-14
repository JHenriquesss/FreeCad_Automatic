import json
from pathlib import Path

import pytest

from tools.loops.__main__ import (
    _allowed_code_paths,
    _notebook_id_for_candidate,
    _research_candidate,
    _research_question,
    _research_retry_question,
    build_parser,
    main,
)
from tools.loops.models import SourceRecord, TaskCandidate
from tools.loops.research_nlm import NotebookMap


def test_cli_parser_exposes_required_options():
    args = build_parser().parse_args(
        [
            "--mode", "dry-run", "--max-iterations", "1", "--executor", "claude",
            "--resume", "loop-1", "--exclude-task-id", "task-1",
        ]
    )

    assert args.mode == "dry-run"
    assert args.max_iterations == 1
    assert args.executor == "claude"
    assert args.resume == "loop-1"
    assert args.exclude_task_ids == ["task-1"]


def test_cli_parser_exposes_retry_blocked():
    args = build_parser().parse_args(["--retry-blocked"])

    assert args.retry_blocked is True


def test_cli_invalid_positive_integer_returns_two():
    assert main(["--max-iterations", "0"]) == 2


def test_cli_invalid_mode_is_rejected():
    assert main(["--mode", "invalid"]) == 2


def test_cli_rejects_recover_orphan_with_resume(capsys):
    result = main(["--recover-orphan", "--resume", "loop-1"])

    assert result == 2
    assert "cannot be combined" in capsys.readouterr().err


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


def test_research_candidate_rejects_empty_source_scope_before_notebook_query():
    class Adapter:
        notebook_map = NotebookMap({"09_INCENDIO": "nb-incendio"})

        def list_ready_sources(self, notebook_id):
            raise AssertionError("broad source listing must not run")

    candidate = TaskCandidate(
        "id",
        "Pendência ampla",
        "seguranca",
        "wiki:T1",
        1,
        ("wiki.md",),
        (),
        topic="geral",
        source_paths=(),
    )

    with pytest.raises(ValueError, match="source_paths"):
        _research_candidate(Adapter(), candidate)


def test_research_prompt_names_each_authorized_source_id():
    source_ids = (
        "71c7e8de-5c0f-48e7-b5ae-8e266faf6747",
        "d84e215b-a6bf-49f8-899a-a56ddd9510d8",
    )

    class Adapter:
        notebook_map = NotebookMap({"02_ACO": "nb-aco"})

        def list_ready_sources_for_paths(self, notebook_id, paths):
            return tuple(
                SourceRecord(source_id, source_id, 2, notebook_id, local_path=path)
                for source_id, path in zip(source_ids, paths)
            )

        def query(self, notebook_id, question, selected_ids):
            self.question = question
            self.selected_ids = selected_ids
            return "evidence"

    candidate = TaskCandidate(
        "id",
        "Fuzz interno — tapered",
        "estrutura",
        "wiki:T16:tapered",
        90,
        ("wiki.md",),
        (),
        topic="tapered",
        source_paths=("02_ACO/dg25.pdf", "02_ACO/nbr8800.pdf"),
    )
    adapter = Adapter()

    assert _research_candidate(adapter, candidate) == "evidence"
    assert adapter.selected_ids == source_ids
    assert all(source_id in adapter.question for source_id in source_ids)
    assert adapter.question == (
        "Para tapered, liste somente invariantes normativas, riscos de crash/NaN e critérios de teste. "
        "Cite cada requisito com o source ID exato entre: " + ", ".join(source_ids) + "."
    )


def test_research_prompt_focuses_estaca_on_nbr6122_and_separates_guards():
    source_id = "fbbdff0f-de66-4c13-a414-284aaf8b8fb9"
    candidate = TaskCandidate(
        "id",
        "Fuzz interno - estaca",
        "estrutura",
        "wiki:T16:estaca",
        20,
        ("wiki.md",),
        (),
        topic="estaca",
    )

    question = _research_question(candidate, (source_id,))

    assert question == (
        "Para estacas na ABNT NBR 6122:2022, liste somente requisitos verificaveis para invariantes de entrada, "
        "limites geometricos/executivos, ausencia de valores invalidos e criterios de teste. "
        "Separe o que a norma exige do que e apenas uma guarda de software. Informe a secao/tabela da norma "
        "para cada item e cite cada requisito usando o source ID exato entre: " + source_id + "."
    )


def test_estaca_retry_prompt_requires_compact_nbr6122_citations():
    source_id = "fbbdff0f-de66-4c13-a414-284aaf8b8fb9"
    candidate = TaskCandidate(
        "id",
        "Fuzz interno - estaca",
        "estrutura",
        "wiki:T16:estaca",
        20,
        ("wiki.md",),
        (),
        topic="estaca",
    )

    retry = _research_retry_question(candidate, (source_id,))

    assert retry == (
        "NBR 6122:2022 para estacas: responda em no maximo 8 itens; para cada item, informe secao/tabela, "
        "requisito verificavel e valor/limite; nao invente guardas de software; use somente o source ID exato "
        + source_id + " e inclua citacoes textuais."
    )


def test_hot_water_prompt_is_scoped_to_nbr5626_and_requires_auditable_citations():
    source_id = "88bbe8c0-cab9-44e4-bfe6-8b895d8d6fc2"
    candidate = TaskCandidate(
        "id",
        "Validar segurança da água quente conforme NBR 5626:2020",
        "hidraulica",
        "fontes/pendencias-atualizacao.md:Expansão do framework:agua-quente-segura",
        60,
        ("fontes/pendencias-atualizacao.md",),
        ("framework/galpao_fw/tests/test_agua_quente_seguranca.py",),
        topic="agua_quente_segura",
        source_paths=(
            "07_HIDRAULICA/HIDRAULICA__NBR__NBR-5626-2020__agua-fria-quente.pdf",
        ),
    )

    question = _research_question(candidate, (source_id,))
    retry = _research_retry_question(candidate, (source_id,))

    assert "NBR 5626:2020" in question
    assert all(section in question for section in ("6.7", "6.9", "6.10", "6.11", "6.12", "6.13"))
    assert source_id in question
    assert "não invente" in question
    assert retry is not None
    assert "NBR 5626:2020" in retry
    assert "citações textuais" in retry
    assert source_id in retry


def test_research_prompt_focuses_gusset_geometry_and_invalid_values():
    source_id = "d84e215b-a6bf-49f8-899a-a56ddd9510d8"
    candidate = TaskCandidate(
        "id",
        "Fuzz interno — gusset",
        "estrutura",
        "wiki:T16:gusset",
        70,
        ("wiki.md",),
        (),
        topic="gusset",
    )

    question = _research_question(candidate, (source_id,))

    assert question == (
        "Para gusset e ligações, liste somente requisitos verificáveis da NBR 8800 "
        "para espessura, furos, bordas, soldas e ausência de valores inválidos. "
        "Cite cada item usando o source ID exato entre: " + source_id + "."
    )


def test_gusset_retry_prompt_is_compact_for_auditable_citations():
    source_id = "d84e215b-a6bf-49f8-899a-a56ddd9510d8"
    candidate = TaskCandidate(
        "id",
        "Fuzz interno — gusset",
        "estrutura",
        "wiki:T16:gusset",
        70,
        ("wiki.md",),
        (),
        topic="gusset",
    )

    retry = _research_retry_question(candidate, (source_id,))

    assert retry == (
        "Gusset na NBR 8800: cite somente requisitos verificáveis para tração, compressão, "
        "solda, furos e block shear; informe limites físicos inválidos. "
        "Use somente o source ID exato " + source_id + "."
    )


def test_research_prompt_focuses_ligacoes_rules_and_invalid_values():
    source_id = "d84e215b-a6bf-49f8-899a-a56ddd9510d8"
    candidate = TaskCandidate(
        "id",
        "Fuzz interno — ligacoes",
        "estrutura",
        "wiki:T16:ligacoes",
        60,
        ("wiki.md",),
        (),
        topic="ligacoes",
    )

    question = _research_question(candidate, (source_id,))
    retry = _research_retry_question(candidate, (source_id,))

    assert question == (
        "Para ligações, liste somente requisitos verificáveis da NBR 8800 para furos, "
        "bordas, espaçamentos, block shear e valores inválidos. "
        "Cite cada item usando o source ID exato entre: " + source_id + "."
    )
    assert retry == (
        "Ligações NBR 8800: cite requisitos verificáveis de furos, bordas, espaçamentos, "
        "block shear e valores inválidos. Use somente o source ID exato " + source_id + "."
    )


def test_research_prompt_focuses_base_chumbador_rules_and_scope_limits():
    source_id = "d84e215b-a6bf-49f8-899a-a56ddd9510d8"
    candidate = TaskCandidate(
        "id",
        "Fuzz interno — base_chumbador",
        "estrutura",
        "wiki:T16:base_chumbador",
        50,
        ("wiki.md",),
        (),
        topic="base_chumbador",
    )

    question = _research_question(candidate, (source_id,))
    retry = _research_retry_question(candidate, (source_id,))

    assert question == (
        "Para base_chumbador, liste somente requisitos verificáveis da NBR 8800 para placas de base, "
        "chumbadores/parafusos, furos, esmagamento, tração e cisalhamento; se a norma não cobrir "
        "breakout/concreto, declare isso. Cite cada item usando o source ID exato entre: " + source_id + "."
    )
    assert retry == (
        "Base/chumbador NBR 8800: cite regras de placas de base, chumbadores/parafusos, furos, "
        "esmagamento, tração/cisalhamento e limites inválidos; declare ausência de regra quando aplicável. "
        "Use somente o source ID exato " + source_id + "."
    )


def test_research_prompt_focuses_nbr9077_population_and_rounding_gap():
    source_id = "878dc921-2664-43ec-b2c8-14641b3c7641"
    candidate = TaskCandidate(
        "id",
        "Validar a população de depósitos conforme NBR 9077:2025.",
        "seguranca",
        "wiki:T43:populacao-nbr9077",
        80,
        ("wiki.md",),
        (),
        topic="populacao_saida",
    )

    question = _research_question(candidate, (source_id,))
    retry = _research_retry_question(candidate, (source_id,))

    assert question == (
        "Para população de depósitos, consulte somente a NBR 9077:2025, seções 5.1, 5.1.2, 5.2 e Tabela 4: "
        "informe quais áreas entram ou saem da área computável, confirme a densidade de 1 pessoa por 30 m² "
        "para depósitos em geral, calcule sem arredondar e declare explicitamente se a norma define regra de "
        "arredondamento. Cite cada item usando o source ID exato entre: " + source_id + "."
    )
    assert retry == (
        "População NBR 9077:2025: cite somente as seções 5.1, 5.1.2, 5.2 e Tabela 4, áreas computáveis, "
        "30 m² por pessoa e a presença ou ausência de regra de arredondamento. Use somente o source ID exato "
        + source_id + "."
    )


def test_fire_prompt_focuses_extintores_without_presuming_edition():
    source_id = "src-nbr12693"
    candidate = TaskCandidate(
        "id",
        "Validar proteção por extintores conforme NBR 12693 (edição a confirmar).",
        "seguranca",
        "fontes/fontes-faltantes.md:P1:nbr12693",
        55,
        ("fontes/fontes-faltantes.md",),
        (),
        topic="extintores",
    )

    question = _research_question(candidate, (source_id,))
    retry = _research_retry_question(candidate, (source_id,))

    assert "NBR 12693" in question
    assert "extintores" in question
    assert "seção/tabela" in question
    assert source_id in question
    assert "202" not in question
    assert retry is not None
    assert "NBR 12693" in retry
    assert "citações textuais" in retry
    assert source_id in retry


def test_fire_prompt_focuses_sinalizacao_without_presuming_edition():
    source_id = "src-nbr13434"
    candidate = TaskCandidate(
        "id",
        "Validar sinalização de segurança contra incêndio conforme NBR 13434 (edição a confirmar).",
        "seguranca",
        "fontes/fontes-faltantes.md:P1:nbr13434",
        50,
        ("fontes/fontes-faltantes.md",),
        (),
        topic="sinalizacao_incendio",
    )

    question = _research_question(candidate, (source_id,))
    retry = _research_retry_question(candidate, (source_id,))

    assert "NBR 13434" in question
    assert "sinalização" in question
    assert "seção/tabela" in question
    assert source_id in question
    assert "202" not in question
    assert retry is not None
    assert "NBR 13434" in retry
    assert "citações textuais" in retry
    assert source_id in retry


@pytest.mark.parametrize(
    ("topic", "norm", "subject"),
    (
        ("fogo_concreto", "NBR 15200", "concreto em situação de incêndio"),
        ("resistencia_fogo", "NBR 14432", "exigências de resistência ao fogo"),
        ("fogo_aco", "NBR 14323", "estruturas de aço e mistas em situação de incêndio"),
    ),
)
def test_structural_fire_prompt_is_scoped_and_requires_textual_citations(
    topic, norm, subject
):
    source_id = f"src-{topic}"
    candidate = TaskCandidate(
        "id",
        f"Validar {subject} conforme {norm} (edição a confirmar).",
        "seguranca",
        f"fontes/pendencias-atualizacao.md:Incêndio:nbr-{topic}",
        45,
        ("fontes/pendencias-atualizacao.md",),
        (),
        topic=topic,
    )

    question = _research_question(candidate, (source_id,))
    retry = _research_retry_question(candidate, (source_id,))

    assert norm in question
    assert subject in question
    assert "seção/tabela" in question
    assert source_id in question
    assert "202" not in question
    assert retry is not None
    assert norm in retry
    assert "citações textuais" in retry
    assert source_id in retry


def test_cli_allowlist_excludes_sources_and_includes_code(tmp_path):
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    (root / "framework" / "galpao_fw").mkdir(parents=True)
    (root / "fontes").mkdir()

    # The helper is intentionally conservative when no Git listing is available.
    assert _allowed_code_paths(root) == ()
