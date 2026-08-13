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

    fuzz = next(item for item in candidates if item.topic == "calhas")

    assert fuzz.discipline == "hidraulica"
    assert fuzz.origin == "framework/galpao_fw/wiki/06-open-threads.md:T16:calhas"
    assert fuzz.source_paths == (
        "08_ESGOTO_PLUVIAL_REUSO/PLUVIAL__NBR__NBR-10844-1989__aguas-pluviais.pdf",
    )
    assert fuzz.suggested_tests
    assert fuzz.suggested_tests == (
        "framework/galpao_fw/tests/test_calha_calc_3d.py",
        "framework/galpao_fw/tests/test_calhas_robustez.py",
        "framework/galpao_fw/tests/test_fase6a_calha_divisa.py",
    )


def test_t16_is_decomposed_into_atomic_topics_with_single_source_scope():
    candidates = discover_candidates(PROJECT_ROOT)

    fuzz = [item for item in candidates if ":T16:" in item.origin]
    assert {item.topic for item in fuzz} == {
        "base_chumbador",
        "tapered",
        "sismo",
        "fogo",
        "estaca",
        "gusset",
        "ligacoes",
        "calhas",
    }
    assert len(fuzz) == 8
    assert all(item.source_paths for item in fuzz)
    assert all(len({path.split("/", 1)[0] for path in item.source_paths}) == 1 for item in fuzz)
    assert not any(
        item.origin == "framework/galpao_fw/wiki/06-open-threads.md:T16"
        and "fuzz interno" in item.title.casefold()
        for item in candidates
    )


def test_atomic_topics_are_ranked_by_explicit_execution_order():
    candidates = discover_candidates(PROJECT_ROOT)

    fuzz_topics = [item.topic for item in candidates if ":T16:" in item.origin]

    assert fuzz_topics == [
        "calhas",
        "tapered",
        "sismo",
        "gusset",
        "ligacoes",
        "base_chumbador",
        "fogo",
        "estaca",
    ]


def test_gusset_unit_does_not_inherit_broad_terca_build_crosscheck():
    candidates = discover_candidates(PROJECT_ROOT)

    gusset = next(item for item in candidates if item.topic == "gusset")

    assert gusset.suggested_tests == (
        "framework/galpao_fw/tests/test_gusset_espessura_3d.py",
        "framework/galpao_fw/tests/test_gusset_robustez.py",
        "framework/galpao_fw/tests/test_pecas_conexao_encaixe.py",
    )


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

    first_fuzz = next(item for item in first if item.topic == "calhas")
    second_fuzz = next(item for item in second if item.topic == "calhas")

    assert first_fuzz.id == second_fuzz.id
    assert len(first_fuzz.id) == 12


def test_same_repository_state_has_same_order():
    first = discover_candidates(PROJECT_ROOT)
    second = discover_candidates(PROJECT_ROOT)

    assert first == second

    assert first == rank_candidates(first)


def test_conditional_future_backlog_item_is_not_discovered():
    candidates = discover_candidates(PROJECT_ROOT)

    assert not any(
        "monossimétricas extremas" in item.title.casefold()
        or "monossimetria" in item.title.casefold()
        for item in candidates
    )


def test_implemented_input_gate_is_not_discovered():
    candidates = discover_candidates(PROJECT_ROOT)

    assert not any(
        "validar() passa a bloquear quando spec[\"ponte\"]" in item.title
        for item in candidates
    )


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


def test_pile_foundation_context_does_not_inherit_cross_discipline_tests():
    candidates = discover_candidates(PROJECT_ROOT)

    pile = next(item for item in candidates if "FS = 2,0" in item.title)

    assert pile.discipline == "estrutura"
    assert pile.suggested_tests
    assert all(
        not any(term in path.casefold() for term in ("eletrico", "incendio", "calha"))
        for path in pile.suggested_tests
    )
    assert any(
        any(term in path.casefold() for term in ("estaca", "fundacao", "geotec", "validacao"))
        for path in pile.suggested_tests
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
    fuzz = next(item for item in candidates if item.topic == "calhas")

    expected = sha1(f"{fuzz.origin}\n{fuzz.title}".encode("utf-8")).hexdigest()[:12]

    assert fuzz.id == expected


def test_discovery_creates_atomic_photovoltaic_validator_with_two_normative_sources():
    candidates = discover_candidates(PROJECT_ROOT)

    fv = next(item for item in candidates if item.topic == "fotovoltaico")

    assert fv.discipline == "eletrica"
    assert fv.origin.endswith(":fv-string-validator")
    assert fv.source_paths == (
        "05_ELETRICA/ELETRICA__NBR__NBR-16690-2019__instalacoes-arranjos-fotovoltaicos.pdf",
        "05_ELETRICA/ELETRICA__NBR__NBR-16149-2013__interface-fv-rede-distribuicao.pdf",
    )
    assert "framework/galpao_fw/tests/test_fotovoltaico.py" in fv.suggested_tests


def test_atomic_photovoltaic_candidate_precedes_broad_validity_pending_item():
    candidates = discover_candidates(PROJECT_ROOT)

    fv_index = next(index for index, item in enumerate(candidates) if item.topic == "fotovoltaico")
    broad_index = next(
        index
        for index, item in enumerate(candidates)
        if "vigência das normas fotovoltaicas" in item.title
    )

    assert fv_index < broad_index
    assert candidates[broad_index].topic == "geral"
    assert candidates[broad_index].source_paths == ()


def test_discovery_creates_atomic_photovoltaic_commissioning_candidate_with_one_source():
    candidates = discover_candidates(PROJECT_ROOT)

    commissioning = next(
        item for item in candidates
        if item.origin.endswith(":fv-commissioning-checklist")
    )

    assert commissioning.topic == "fotovoltaico"
    assert commissioning.discipline == "eletrica"
    assert commissioning.priority == 65
    assert commissioning.source_paths == (
        "05_ELETRICA/ELETRICA__NBR__NBR-16274-2014__documentacao-comissionamento-fv.pdf",
    )
    assert commissioning.suggested_tests == (
        "framework/galpao_fw/tests/test_comissionamento_fv.py",
    )


def test_photovoltaic_commissioning_candidate_is_before_broad_pending_item():
    candidates = discover_candidates(PROJECT_ROOT)

    commissioning_index = next(
        index for index, item in enumerate(candidates)
        if item.origin.endswith(":fv-commissioning-checklist")
    )
    broad_index = next(
        index for index, item in enumerate(candidates)
        if "vigência das normas fotovoltaicas" in item.title
    )

    assert commissioning_index < broad_index


def test_discovery_creates_atomic_emergency_sign_area_candidate(tmp_path):
    wiki = tmp_path / "framework" / "galpao_fw" / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "06-open-threads.md").write_text(
        "# Threads\n"
        "## T42 — sinalização\n"
        "- [ ] Validar a área mínima das placas de emergência conforme NBR 16820:2020.\n",
        encoding="utf-8",
    )
    tests = tmp_path / "framework" / "galpao_fw" / "tests"
    tests.mkdir(parents=True)
    for name in (
        "test_incendio_robustez.py",
        "test_saturacao_verdito.py",
        "test_seguranca_incendio.py",
        "test_sinalizacao_nbr16820.py",
    ):
        (tests / name).write_text("", encoding="utf-8")

    candidates = discover_candidates(tmp_path)

    signage = next(
        item for item in candidates
        if item.origin == (
            "framework/galpao_fw/wiki/06-open-threads.md:T42:sinalizacao-area-minima"
        )
    )

    assert signage.origin == (
        "framework/galpao_fw/wiki/06-open-threads.md:T42:sinalizacao-area-minima"
    )
    assert signage.topic == "sinalizacao"
    assert signage.discipline == "seguranca"
    assert signage.priority == 75
    assert signage.source_paths == (
        "09_INCENDIO/INCENDIO__NBR__NBR-16820-2020__sinalizacao-emergencia.pdf",
    )
    assert signage.suggested_tests == (
        "framework/galpao_fw/tests/test_incendio_robustez.py",
        "framework/galpao_fw/tests/test_saturacao_verdito.py",
        "framework/galpao_fw/tests/test_seguranca_incendio.py",
        "framework/galpao_fw/tests/test_sinalizacao_nbr16820.py",
    )


def test_closed_emergency_sign_thread_is_not_discovered():
    candidates = discover_candidates(PROJECT_ROOT)

    assert not any(item.topic == "sinalizacao" for item in candidates)


def test_discovery_does_not_decompose_area_item_from_another_thread(tmp_path):
    wiki = tmp_path / "framework" / "galpao_fw" / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "06-open-threads.md").write_text(
        "# Threads\n"
        "## T43 — outra thread\n"
        "- [ ] Validar a área mínima das placas de emergência conforme NBR 16820:2020.\n",
        encoding="utf-8",
    )

    candidates = discover_candidates(tmp_path)

    assert not any(item.topic == "sinalizacao" for item in candidates)


def test_discovery_creates_atomic_nbr9077_population_candidate(tmp_path):
    wiki = tmp_path / "framework" / "galpao_fw" / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "06-open-threads.md").write_text(
        "# Threads\n"
        "## T43 — população de depósitos\n"
        "- [ ] Calcular a população de projeto de depósitos pela área computável da NBR 9077:2025.\n",
        encoding="utf-8",
    )
    tests = tmp_path / "framework" / "galpao_fw" / "tests"
    tests.mkdir(parents=True)
    for name in (
        "test_populacao_nbr9077.py",
        "test_seguranca_incendio.py",
        "test_guardas_entrada.py",
    ):
        (tests / name).write_text("", encoding="utf-8")

    candidates = discover_candidates(tmp_path)

    population = next(
        item for item in candidates
        if item.origin == (
            "framework/galpao_fw/wiki/06-open-threads.md:T43:populacao-nbr9077"
        )
    )

    assert population.title == "Validar a população de depósitos conforme NBR 9077:2025."
    assert population.topic == "populacao_saida"
    assert population.discipline == "seguranca"
    assert population.priority == 80
    assert population.source_paths == (
        "09_INCENDIO/INCENDIO__NBR__NBR-9077-2025__saidas-emergencia.pdf",
    )
    assert population.suggested_tests == (
        "framework/galpao_fw/tests/test_populacao_nbr9077.py",
        "framework/galpao_fw/tests/test_seguranca_incendio.py",
        "framework/galpao_fw/tests/test_guardas_entrada.py",
    )


def test_discovery_does_not_decompose_nbr9077_population_from_another_thread(tmp_path):
    wiki = tmp_path / "framework" / "galpao_fw" / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "06-open-threads.md").write_text(
        "# Threads\n"
        "## T44 — outra thread\n"
        "- [ ] Calcular a população de projeto de depósitos pela área computável da NBR 9077:2025.\n",
        encoding="utf-8",
    )

    candidates = discover_candidates(tmp_path)

    assert not any(item.topic == "populacao_saida" for item in candidates)


def test_fire_pending_decomposes_into_two_atomic_norm_candidates(tmp_path):
    source_pending = tmp_path / "fontes"
    source_pending.mkdir(parents=True)
    (source_pending / "fontes-faltantes.md").write_text(
        "# Fontes faltantes\n"
        "## P1 — atualizações normativas e segurança industrial\n"
        "- Proteção contra incêndio: NBR 16981:2021 já cobre áreas de armazenamento e "
        "substitui a NBR 13792:1997; ainda faltam NBR 12693 e NBR 13434.\n",
        encoding="utf-8",
    )
    tests = tmp_path / "framework" / "galpao_fw" / "tests"
    tests.mkdir(parents=True)
    for name in (
        "test_incendio_robustez.py",
        "test_seguranca_incendio.py",
        "test_incendio_bim.py",
    ):
        (tests / name).write_text("", encoding="utf-8")

    candidates = discover_candidates(tmp_path)

    extinguishers = next(
        item for item in candidates if item.origin.endswith(":nbr12693")
    )
    signage = next(
        item for item in candidates if item.origin.endswith(":nbr13434")
    )
    broad = next(
        item for item in candidates
        if item.title.startswith("Proteção contra incêndio:")
    )

    assert extinguishers.topic == "extintores"
    assert extinguishers.discipline == "seguranca"
    assert extinguishers.source_paths == (
        "09_INCENDIO/INCENDIO__NBR__NBR-12693__sistemas-extintores.pdf",
    )
    assert extinguishers.suggested_tests == (
        "framework/galpao_fw/tests/test_incendio_robustez.py",
        "framework/galpao_fw/tests/test_seguranca_incendio.py",
        "framework/galpao_fw/tests/test_incendio_bim.py",
    )
    assert signage.topic == "sinalizacao_incendio"
    assert signage.discipline == "seguranca"
    assert signage.source_paths == (
        "09_INCENDIO/INCENDIO__NBR__NBR-13434__sinalizacao-seguranca.pdf",
    )
    assert signage.suggested_tests == extinguishers.suggested_tests
    assert broad.source_paths == ()

    first_run = tuple((item.id, item.origin, item.source_paths) for item in candidates)
    second_run = tuple(
        (item.id, item.origin, item.source_paths)
        for item in discover_candidates(tmp_path)
    )
    assert first_run == second_run
