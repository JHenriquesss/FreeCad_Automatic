import pytest

from project_loop import iterate_project, run_project


def test_iteration_preserves_parent_and_changes_only_explicit_path(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    first_dir = tmp_path / "iteration-001"
    first = run_project(turnkey_fixture_with_hvac_and_hydraulic, first_dir,
                        options={"generate_ifc": False})
    second = iterate_project(first, updates={"geometria.pe_direito": 7.0},
                             options={"generate_ifc": False})
    assert second["iteration"] == 2
    assert second["parent_run_id"] == first["run_id"]
    assert second["changes"] == {"geometria.pe_direito": 7.0}
    assert first["input"]["geometria"]["pe_direito"] == 6.0
    assert second["input"]["geometria"]["pe_direito"] == 7.0
    assert (tmp_path / "iteration-002" / "project-run.json").exists()


def test_iteration_does_not_close_conflict_by_text_only(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    first = run_project(turnkey_fixture_with_hvac_and_hydraulic, tmp_path / "a",
                        options={"generate_ifc": False})
    second = iterate_project(
        first,
        resolutions=[{"issue_id": "CLH-001", "status": "approved",
                      "note": "revisado pelo engenheiro"}],
        options={"generate_ifc": False},
    )
    assert second["resolutions"][0]["status"] == "approved"
    assert second["coordination"]["open"] >= 0
    assert second["coordination"]["resolution_requests"]


def test_iteration_inherits_discipline_scope_when_options_are_partial(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    first = run_project(
        turnkey_fixture_with_hvac_and_hydraulic, tmp_path / "scope-001",
        options={"required_disciplines": ("incendio",),
                 "generate_ifc": False},
    )

    second = iterate_project(
        first,
        updates={"geometria.pe_direito": 7.0},
        options={"generate_ifc": False},
    )

    assert second["options"]["required_disciplines"] == ["incendio"]
    assert set(second["disciplines"]) == {"incendio"}


def test_iteration_refuses_to_continue_from_corrupted_parent(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    first_dir = tmp_path / "iteration-001"
    first = run_project(turnkey_fixture_with_hvac_and_hydraulic, first_dir,
                        options={"generate_ifc": False})
    artifact = next(item for item in first["artifacts"]
                    if item.get("sha256"))
    (first_dir / artifact["path"]).write_text("adulterado", encoding="utf-8")

    with pytest.raises(ValueError, match="execução pai não íntegra"):
        iterate_project(first, updates={"geometria.pe_direito": 7.0},
                        options={"generate_ifc": False})

    assert not (tmp_path / "iteration-002" / "project-run.json").exists()
