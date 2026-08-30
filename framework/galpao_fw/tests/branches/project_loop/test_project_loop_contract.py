import os

import pytest

from project_loop import run_project


def test_structural_legacy_spec_is_registered_as_steel_and_blocks_missing_fields(tmp_path):
    result = run_project({"geometria": {"span": 20}}, tmp_path)
    assert result["status"] == "blocked"
    assert result["disciplines"]["aco"]["status"] == "blocked"
    assert (tmp_path / "project-run.json").exists()
    assert (tmp_path / "input" / "spec.json").exists()
    assert (tmp_path / "reports" / "preflight.json").exists()


def test_turnkey_spec_keeps_explicit_disciplines_and_derives_only_common_geometry(tmp_path):
    spec = {"slug": "g", "geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
            "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350}}}
    result = run_project(spec, tmp_path, options={"generate_ifc": False})
    assert result["project_id"] == "g"
    assert result["disciplines"]["incendio"]["status"] in {"passed", "needs_review"}
    assert result["preflight"]["derivations"] == []


def test_versioned_envelope_preserves_sources_and_requires_them_when_requested(tmp_path):
    spec = {"schema": "freecad-automatic/project-spec", "schema_version": 1,
            "project": {"slug": "g"},
            "site": {"city": "São João da Barra", "state": "RJ", "utility": "ENEL"},
            "source_refs": {}, "turnkey": {
                "geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
                "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350}}}}
    result = run_project(spec, tmp_path, options={"require_source_refs": True,
                                                   "generate_ifc": False})
    assert result["status"] == "blocked"
    assert result["disciplines"]["incendio"]["status"] == "blocked"
    assert result["sources"] == {}


def test_unknown_project_adapter_is_blocked_and_persisted(tmp_path):
    result = run_project({"adapter": "edificio_desconhecido",
                          "geometria": {"comprimento": 10, "vao": 10,
                                         "pe_direito": 3}}, tmp_path)
    assert result["status"] == "blocked"
    assert result["adapter"] == "edificio_desconhecido"
    assert any(item["code"] == "unsupported_adapter"
               for item in result["preflight"]["errors"])


def test_unsupported_required_discipline_is_explicitly_blocked(tmp_path):
    spec = {
        "geometria": {"comprimento": 10, "vao": 10, "pe_direito": 3},
        "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350}},
    }
    result = run_project(
        spec, tmp_path,
        options={"required_disciplines": ("incendio", "spda"),
                 "generate_ifc": False},
    )

    assert result["status"] == "blocked"
    assert result["disciplines"]["incendio"]["status"] != "blocked"
    assert result["disciplines"]["spda"]["status"] == "blocked"
    assert any(item["code"] == "unsupported_discipline"
               for item in result["preflight"]["errors"]
               if item.get("discipline") == "spda")
    assert any(item["code"] == "unsupported_discipline"
               for item in result["disciplines"]["spda"]["errors"])


def test_explicitly_unready_source_blocks_the_discipline(tmp_path):
    spec = {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "g"},
        "source_refs": {
            "incendio": [{"notebook_id": "nb-incendio",
                           "source_id": "src-failed", "status": 3}],
        },
        "turnkey": {
            "geometria": {"comprimento": 10, "vao": 10, "pe_direito": 3},
            "incendio": {"iluminacao_emergencia": {
                "fluxo_bloco_lm": 350}},
        },
    }
    result = run_project(spec, tmp_path, options={"generate_ifc": False})

    assert result["status"] == "blocked"
    assert result["disciplines"]["incendio"]["status"] == "blocked"
    assert result["preflight"]["source_issues"]["incendio"][0]["status"] == 3
    assert any(item["code"] == "source_not_ready"
               for item in result["preflight"]["errors"])


def test_run_project_refuses_to_overwrite_a_completed_iteration(
        tmp_path, turnkey_fixture):
    out_dir = tmp_path / "iteration-001"
    first = run_project(turnkey_fixture(), out_dir,
                        options={"generate_ifc": False})

    with pytest.raises(ValueError, match="use uma pasta nova"):
        run_project(turnkey_fixture(), out_dir,
                    options={"generate_ifc": False})

    persisted = (out_dir / "project-run.json").read_text(encoding="utf-8")
    assert first["run_id"] in persisted


def test_run_project_refuses_to_mix_with_a_partial_output_directory(
        tmp_path, turnkey_fixture):
    out_dir = tmp_path / "interrompida"
    out_dir.mkdir()
    (out_dir / "partial.marker").write_text("interrompida", encoding="utf-8")

    with pytest.raises(ValueError, match="deve estar vazia"):
        run_project(turnkey_fixture(), out_dir,
                    options={"generate_ifc": False})

    assert (out_dir / "partial.marker").read_text(encoding="utf-8") == \
        "interrompida"
