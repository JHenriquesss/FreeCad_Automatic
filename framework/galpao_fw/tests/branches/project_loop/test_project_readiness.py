import json

import pytest

import project_loop as project_loop_module
from project_io import ProjectSpecFileError, preflight_project_file
from project_loop import preflight_project
from project_loop_cli import main

from pathlib import Path

# Ver nota em test_project_spec_file_input.py: caminho ancorado no arquivo.
SJB_TEMPLATE = (Path(__file__).resolve().parents[5]
                / "projects" / "galpao-sjb" / "project-spec.template.json")


def _ready_spec(**extra):
    spec = {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "pronto"},
        "site": {"city": "São João da Barra", "state": "RJ",
                  "utility": "ENEL"},
        "turnkey": {
            "geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
            "incendio": {
                "iluminacao_emergencia": {"fluxo_bloco_lm": 350}},
        },
    }
    spec.update(extra)
    return spec


def test_preflight_only_returns_ready_without_running_adapter(tmp_path, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("o adapter nao pode rodar no preflight-only")

    monkeypatch.setitem(project_loop_module._PROJECT_ADAPTERS,
                        "galpao", fail_if_called)
    out_dir = tmp_path / "readiness"

    result = preflight_project(_ready_spec(), out_dir,
                               options={"require_source_refs": False})

    assert result["status"] == "ready"
    assert result["can_start_project_loop"] is True
    assert result["preflight"]["ok"] is True
    assert (out_dir / "project-readiness.json").is_file()
    assert (out_dir / "reports" / "preflight.json").is_file()
    assert not (out_dir / "project-run.json").exists()
    assert not (out_dir / "disciplines").exists()


def test_preflight_only_marks_stale_source_for_review(tmp_path):
    spec = _ready_spec(source_refs={
        "incendio": [{"notebook_id": "nb-incendio",
                       "source_id": "src-stale", "status": 2,
                       "is_stale": True}],
    })

    result = preflight_project(spec, tmp_path)

    assert result["status"] == "needs_review"
    assert result["can_start_project_loop"] is False
    assert result["preflight"]["warnings"][0]["code"] == "stale_source"


def test_preflight_only_blocks_unfilled_sjb_template_without_project_run(
        tmp_path):
    result = preflight_project_file(
        str(SJB_TEMPLATE), tmp_path,
        options={"generate_ifc": False},
    )

    assert result["status"] == "blocked"
    assert result["can_start_project_loop"] is False
    assert result["preflight"]["pending_inputs"]
    assert (tmp_path / "project-readiness.json").is_file()
    assert not (tmp_path / "project-run.json").exists()


def test_cli_preflight_only_returns_readiness_code_and_manifest(tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    source.write_text(json.dumps(_ready_spec(), ensure_ascii=False),
                      encoding="utf-8")
    out_dir = tmp_path / "cli-readiness"

    code = main(["--spec", str(source), "--out-dir", str(out_dir),
                 "--preflight-only"])

    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ready"
    persisted = json.loads(
        (out_dir / "project-readiness.json").read_text(encoding="utf-8"))
    assert persisted["can_start_project_loop"] is True
    assert not (out_dir / "project-run.json").exists()


def test_cli_preflight_only_returns_review_code_for_stale_source(tmp_path,
                                                                 capsys):
    source = tmp_path / "stale-spec.json"
    source.write_text(json.dumps(_ready_spec(source_refs={
        "incendio": [{"notebook_id": "nb-incendio",
                       "source_id": "src-stale", "status": 2,
                       "is_stale": True}],
    }), ensure_ascii=False), encoding="utf-8")

    code = main(["--spec", str(source), "--out-dir",
                 str(tmp_path / "stale-readiness"), "--preflight-only"])

    assert code == 1
    assert json.loads(capsys.readouterr().out)["status"] == "needs_review"


def test_preflight_only_rejects_non_auditable_source_reference(tmp_path):
    spec = _ready_spec(source_refs={"incendio": [{}]})

    result = preflight_project(
        spec, tmp_path, options={"require_source_refs": True})

    assert result["status"] == "blocked"
    assert any(item["code"] == "invalid_source_ref"
               for item in result["preflight"]["errors"])


@pytest.mark.parametrize("invalid_source_refs", ["", False, 0])
def test_preflight_only_rejects_falsy_non_mapping_source_refs(
        tmp_path, invalid_source_refs):
    result = preflight_project(
        _ready_spec(source_refs=invalid_source_refs), tmp_path)

    assert result["status"] == "blocked"
    assert any(item["code"] == "invalid_source_refs"
               for item in result["preflight"]["errors"])


def test_preflight_only_rejects_non_mapping_source_refs(tmp_path):
    result = preflight_project(
        _ready_spec(source_refs="not-a-source-map"), tmp_path)

    assert result["status"] == "blocked"
    assert any(item["code"] == "invalid_source_refs"
               for item in result["preflight"]["errors"])


def test_preflight_only_accepts_id_fallback_when_source_id_is_empty(tmp_path):
    spec = _ready_spec(source_refs={
        "incendio": [{"source_id": "", "id": "catalog-1",
                       "notebook_id": "nb-incendio"}],
    })

    result = preflight_project(
        spec, tmp_path, options={"require_source_refs": True})

    assert result["status"] == "ready"


def test_preflight_only_rejects_non_mapping_discipline_payload(tmp_path):
    spec = _ready_spec()
    spec["turnkey"]["eletrico"] = "invalid"

    result = preflight_project(spec, tmp_path)

    assert result["status"] == "blocked"
    assert any(item["code"] == "invalid_discipline_input"
               and item["discipline"] == "eletrico"
               for item in result["preflight"]["errors"])


def test_cli_preflight_only_returns_input_code_for_semantically_invalid_json(
        tmp_path, capsys):
    source = tmp_path / "invalid-shape.json"
    source.write_text(json.dumps({
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "invalid-shape"},
        "turnkey": "not-an-object",
    }), encoding="utf-8")

    code = main(["--spec", str(source), "--out-dir",
                 str(tmp_path / "invalid-readiness"), "--preflight-only"])

    assert code == 4
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"


def test_cli_preflight_only_returns_input_code_for_non_mapping_geometry(
        tmp_path, capsys):
    source = tmp_path / "invalid-geometry.json"
    source.write_text(json.dumps({
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "invalid-geometry"},
        "turnkey": {"geometria": "not-an-object"},
    }), encoding="utf-8")

    code = main(["--spec", str(source), "--out-dir",
                 str(tmp_path / "invalid-geometry-readiness"),
                 "--preflight-only"])

    assert code == 4
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"


def test_preflight_only_refuses_directory_with_existing_project_run(tmp_path):
    out_dir = tmp_path / "mixed"
    out_dir.mkdir()
    (out_dir / "project-run.json").write_text("{}", encoding="utf-8")
    source = tmp_path / "project-spec.json"
    source.write_text(json.dumps(_ready_spec(), ensure_ascii=False),
                      encoding="utf-8")

    with pytest.raises(ProjectSpecFileError, match="project-run.json"):
        preflight_project_file(source, out_dir)

    assert not (out_dir / "input").exists()
    assert not (out_dir / "project-readiness.json").exists()
