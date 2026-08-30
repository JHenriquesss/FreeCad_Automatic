import json
from pathlib import Path

import pytest

from project_io import (ProjectSpecFileError, load_project_spec,
                        run_project_file)
from project_loop_cli import main

# O caminho do template e' resolvido a partir do arquivo de teste: a suite roda
# tanto com CWD na raiz do repositorio quanto em framework/galpao_fw (CI).
SJB_TEMPLATE = (Path(__file__).resolve().parents[5]
                / "projects" / "galpao-sjb" / "project-spec.template.json")


def _write_minimal_spec(path):
    spec = {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "cli-arquivo"},
        "turnkey": {
            "geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
            "incendio": {
                "iluminacao_emergencia": {"fluxo_bloco_lm": 350}},
        },
    }
    path.write_text(json.dumps(spec), encoding="utf-8")
    return spec


def test_json_file_entry_uses_the_project_loop_and_persists_input_hash(
        tmp_path, turnkey_fixture):
    spec = {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "arquivo"},
        "turnkey": {
            "geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
            "incendio": {
                "iluminacao_emergencia": {"fluxo_bloco_lm": 350}},
        },
    }
    source = tmp_path / "project-spec.json"
    source.write_text(json.dumps(spec), encoding="utf-8")

    result = run_project_file(source, tmp_path / "run",
                              options={"generate_ifc": False})

    assert result["project_id"] == "arquivo"
    assert result["status"] in {"passed", "needs_review"}
    persisted = json.loads(
        (tmp_path / "run" / "project-run.json").read_text(encoding="utf-8"))
    assert persisted["input"] == spec
    assert len(persisted["input_sha256"]) == 64


def test_sjb_enel_template_is_blocked_without_inventing_engineering_data(tmp_path):
    template = SJB_TEMPLATE
    result = run_project_file(template, tmp_path / "run",
                              options={"generate_ifc": False})

    assert result["status"] == "blocked"
    assert any(item["code"] == "invalid_common_geometry"
               for item in result["preflight"]["errors"])
    assert any(item["code"] == "pending_discipline_input"
               for item in result["preflight"]["errors"])
    assert {
        item["discipline"] for item in result["preflight"]["errors"]
        if item["code"] == "pending_discipline_input"
    } == {"concreto", "aco", "eletrico", "incendio",
          "climatizacao", "hidraulica"}
    assert {
        (item["discipline"], tuple(item["paths"]))
        for item in result["preflight"]["errors"]
        if item["code"] == "pending_discipline_input"
    } == {
        (discipline, ("turnkey.%s._status" % discipline,))
        for discipline in ("concreto", "aco", "eletrico", "incendio",
                           "climatizacao", "hidraulica")
    }
    assert result["site"] == {
        "city": "São João da Barra", "state": "RJ", "utility": "ENEL"}
    assert result["input"]["project"]["type"] == "galpao"


def test_sjb_enel_template_has_auditable_notebook_source_refs():
    template = SJB_TEMPLATE
    spec = json.loads(template.read_text(encoding="utf-8"))

    expected = {"concreto", "aco", "eletrico", "incendio",
                "climatizacao", "hidraulica"}
    refs = spec["source_refs"]

    assert set(refs) == expected
    assert all(ref["notebook_id"] and ref["source_id"] and ref["status"] == 2
               for discipline_refs in refs.values()
               for ref in discipline_refs)


def test_invalid_json_and_schema_are_reported_as_input_errors(tmp_path):
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ProjectSpecFileError, match="JSON de spec invalido"):
        load_project_spec(invalid)

    unsupported = tmp_path / "unsupported.json"
    unsupported.write_text(json.dumps({
        "schema": "outro/schema", "schema_version": 1}), encoding="utf-8")
    with pytest.raises(ProjectSpecFileError, match="schema de spec nao suportado"):
        load_project_spec(unsupported)

    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps({"geometria": {}}), encoding="utf-8")
    with pytest.raises(ProjectSpecFileError, match="spec legado recusado"):
        load_project_spec(legacy, allow_legacy=False)

    missing_version = tmp_path / "missing-version.json"
    missing_version.write_text(json.dumps({
        "schema": "freecad-automatic/project-spec"}), encoding="utf-8")
    with pytest.raises(ProjectSpecFileError, match="schema_version nao suportado"):
        load_project_spec(missing_version)

    unsupported_version = tmp_path / "unsupported-version.json"
    unsupported_version.write_text(json.dumps({
        "schema": "freecad-automatic/project-spec",
        "schema_version": 99}), encoding="utf-8")
    with pytest.raises(ProjectSpecFileError, match="schema_version nao suportado"):
        load_project_spec(unsupported_version)

    invalid_utf8 = tmp_path / "invalid-utf8.json"
    invalid_utf8.write_bytes(b"\xff\xfe")
    with pytest.raises(ProjectSpecFileError, match="spec nao esta em UTF-8"):
        load_project_spec(invalid_utf8)


def test_cli_runs_a_file_and_persists_the_real_manifest(tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    _write_minimal_spec(source)
    out_dir = tmp_path / "cli-run"

    code = main(["--spec", str(source), "--out-dir", str(out_dir), "--no-ifc"])

    assert code == 0
    persisted = json.loads(
        (out_dir / "project-run.json").read_text(encoding="utf-8"))
    assert persisted["project_id"] == "cli-arquivo"
    assert json.loads(capsys.readouterr().out)["status"] in {
        "passed", "needs_review"}


def test_cli_iterates_from_parent_manifest_with_json_update_and_resolution(
        tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    _write_minimal_spec(source)
    first_dir = tmp_path / "iteration-001"
    assert main(["--spec", str(source), "--out-dir", str(first_dir),
                 "--no-ifc"]) == 0
    capsys.readouterr()

    second_dir = tmp_path / "iteration-002"
    code = main([
        "--iterate-from", str(first_dir), "--out-dir", str(second_dir),
        "--no-ifc",
        "--update", "turnkey.incendio.iluminacao_emergencia.fluxo_bloco_lm=400",
        "--resolution", json.dumps({
            "issue_id": "CLH-001", "status": "reviewed",
            "note": "revisado pelo engenheiro",
        }),
    ])

    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] in {"passed", "needs_review"}
    persisted = json.loads(
        (second_dir / "project-run.json").read_text(encoding="utf-8"))
    assert persisted["iteration"] == 2
    assert persisted["parent_run_id"]
    assert persisted["changes"] == {
        "turnkey.incendio.iluminacao_emergencia.fluxo_bloco_lm": 400}
    assert persisted["resolutions"] == [{
        "issue_id": "CLH-001", "status": "reviewed",
        "note": "revisado pelo engenheiro",
    }]


def test_cli_reviews_parent_with_resolution_plan_and_persists_child(
        tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    _write_minimal_spec(source)
    parent_dir = tmp_path / "loop-2"
    assert main(["--spec", str(source), "--out-dir", str(parent_dir),
                 "--no-ifc"]) == 0
    capsys.readouterr()
    parent = json.loads(
        (parent_dir / "project-run.json").read_text(encoding="utf-8"))
    plan = tmp_path / "resolution-plan.json"
    plan.write_text(json.dumps({
        "schema": "freecad-automatic/coordination-resolution-plan",
        "schema_version": 1,
        "parent_run_id": parent["run_id"],
        "project_id": parent["project_id"],
        "decisions": [],
    }), encoding="utf-8")
    child_dir = tmp_path / "loop-3"

    code = main([
        "--review-from", str(parent_dir),
        "--resolution-plan", str(plan),
        "--out-dir", str(child_dir), "--no-ifc",
    ])

    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["manifest"] == str(child_dir.resolve() / "project-run.json")
    child = json.loads(
        (child_dir / "project-run.json").read_text(encoding="utf-8"))
    assert child["parent_run_id"] == parent["run_id"]
    assert (child_dir / "coordination" / "resolution-plan.json").exists()
    assert (child_dir / "coordination" / "review-report.json").exists()


def test_cli_rejects_ambiguous_review_and_iteration_modes(tmp_path, capsys):
    code = main([
        "--review-from", str(tmp_path / "parent"),
        "--resolution-plan", str(tmp_path / "plan.json"),
        "--iterate-from", str(tmp_path / "other"),
        "--out-dir", str(tmp_path / "child"),
    ])

    assert code == 4
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"
    assert not (tmp_path / "child").exists()


def test_cli_iteration_rejects_invalid_update_without_partial_output(
        tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    _write_minimal_spec(source)
    first_dir = tmp_path / "iteration-001"
    assert main(["--spec", str(source), "--out-dir", str(first_dir),
                 "--no-ifc"]) == 0
    capsys.readouterr()

    second_dir = tmp_path / "invalid-iteration"
    code = main([
        "--iterate-from", str(first_dir), "--out-dir", str(second_dir),
        "--no-ifc", "--update", "turnkey.incendio=not-json",
    ])

    assert code == 4
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"
    assert not (second_dir / "project-run.json").exists()


def test_cli_iteration_accepts_a_complete_spec_override(tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    _write_minimal_spec(source)
    first_dir = tmp_path / "iteration-001"
    assert main(["--spec", str(source), "--out-dir", str(first_dir),
                 "--no-ifc"]) == 0
    capsys.readouterr()

    override = _write_minimal_spec(tmp_path / "override.json")
    override["turnkey"]["incendio"]["iluminacao_emergencia"][
        "fluxo_bloco_lm"] = 450
    (tmp_path / "override.json").write_text(
        json.dumps(override), encoding="utf-8")

    second_dir = tmp_path / "iteration-002"
    code = main([
        "--iterate-from", str(first_dir), "--spec", str(tmp_path / "override.json"),
        "--out-dir", str(second_dir), "--no-ifc",
    ])

    assert code == 0
    capsys.readouterr()
    persisted = json.loads(
        (second_dir / "project-run.json").read_text(encoding="utf-8"))
    assert persisted["iteration"] == 2
    assert persisted["changes"] == {}
    assert persisted["input"]["turnkey"]["incendio"][
        "iluminacao_emergencia"]["fluxo_bloco_lm"] == 450


def test_cli_verifies_manifest_and_returns_failure_for_changed_artifact(
        tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    _write_minimal_spec(source)
    out_dir = tmp_path / "run"
    assert main(["--spec", str(source), "--out-dir", str(out_dir),
                 "--no-ifc"]) == 0
    capsys.readouterr()

    code = main(["--verify-run", str(out_dir)])
    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["ok"] is True

    artifact = next(item for item in report["errors"] + json.loads(
        (out_dir / "project-run.json").read_text(encoding="utf-8"))["artifacts"]
                     if item.get("sha256"))
    (out_dir / artifact["path"]).write_text("adulterado", encoding="utf-8")

    code = main(["--verify-run", str(out_dir)])
    report = json.loads(capsys.readouterr().out)
    assert code == 3
    assert report["ok"] is False
    assert any(item["code"] == "artifact_hash_mismatch"
               for item in report["errors"])


def test_cli_runs_an_explicit_iteration_plan(tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    spec = _write_minimal_spec(source)
    plan = tmp_path / "iteration-plan.json"
    plan.write_text(json.dumps({"steps": [{
        "updates": {
            "turnkey.incendio.iluminacao_emergencia.fluxo_bloco_lm": 400,
        },
    }]}), encoding="utf-8")
    readiness = tmp_path / "readiness.json"
    readiness.write_text(json.dumps({
        "schema": "freecad-automatic/project-readiness",
        "schema_version": 1,
        "project_id": "cli-arquivo",
        "input": spec,
        "status": "ready",
        "can_start_project_loop": True,
    }), encoding="utf-8")
    out_dir = tmp_path / "sequence"

    code = main([
        "--spec", str(source), "--iteration-plan", str(plan),
        "--readiness", str(readiness),
        "--out-dir", str(out_dir), "--no-ifc",
    ])

    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] in {"passed", "needs_review"}
    persisted = json.loads(
        (out_dir / "project-sequence.json").read_text(encoding="utf-8"))
    assert persisted["completed_iterations"] == 2
    assert (out_dir / "iteration-002" / "project-run.json").exists()


def test_cli_iteration_plan_requires_readiness_argument(tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    _write_minimal_spec(source)
    plan = tmp_path / "iteration-plan.json"
    plan.write_text(json.dumps({"steps": []}), encoding="utf-8")
    out_dir = tmp_path / "sequence"

    code = main([
        "--spec", str(source), "--iteration-plan", str(plan),
        "--out-dir", str(out_dir), "--no-ifc",
    ])

    assert code == 4
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "invalid_input"
    assert not out_dir.exists()


def test_cli_verifies_live_source_refs_and_persists_gate_report(
        tmp_path, capsys, monkeypatch):
    source = tmp_path / "project-spec.json"
    spec = _write_minimal_spec(source)
    spec["source_refs"] = {"incendio": [{
        "notebook_id": "nb-fire",
        "source_id": "src-fire",
        "status": 2,
    }]}
    source.write_text(json.dumps(spec), encoding="utf-8")
    out_dir = tmp_path / "source-gate"
    expected = {
        "schema": "freecad-automatic/project-source-verification",
        "schema_version": 1,
        "project_id": "cli-arquivo",
        "status": "ready",
        "ok": True,
        "errors": [],
    }

    import project_source_gate
    monkeypatch.setattr(
        project_source_gate, "verify_project_source_refs",
        lambda value: expected.copy())

    code = main([
        "--spec", str(source), "--verify-source-refs",
        "--out-dir", str(out_dir),
    ])

    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ready"
    persisted = json.loads(
        (out_dir / "source-verification.json").read_text(encoding="utf-8"))
    assert persisted == expected


def test_cli_combines_source_gate_with_preflight_and_blocks_readiness(
        tmp_path, capsys, monkeypatch):
    source = tmp_path / "project-spec.json"
    _write_minimal_spec(source)
    out_dir = tmp_path / "combined-readiness"
    source_report = {
        "schema": "freecad-automatic/project-source-verification",
        "schema_version": 1,
        "project_id": "cli-arquivo",
        "status": "blocked",
        "ok": False,
        "checked_references": 1,
        "errors": [{"code": "source_not_ready"}],
    }

    import project_source_gate
    monkeypatch.setattr(
        project_source_gate, "verify_project_source_refs",
        lambda value: source_report.copy())

    code = main([
        "--spec", str(source), "--verify-source-refs", "--preflight-only",
        "--out-dir", str(out_dir),
    ])

    assert code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    readiness = json.loads(
        (out_dir / "project-readiness.json").read_text(encoding="utf-8"))
    assert readiness["status"] == "blocked"
    assert readiness["can_start_project_loop"] is False
    assert readiness["source_verification"] == source_report
    assert json.loads(
        (out_dir / "reports" / "source-verification.json").read_text(
            encoding="utf-8")) == source_report
    assert not (out_dir / "project-run.json").exists()


def test_cli_initial_execution_requires_approved_readiness(
        tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    spec = _write_minimal_spec(source)
    spec["source_refs"] = {"incendio": [{
        "notebook_id": "nb-fire",
        "source_id": "src-fire",
        "status": 2,
    }]}
    source.write_text(json.dumps(spec), encoding="utf-8")
    readiness = tmp_path / "readiness"
    readiness.mkdir()
    readiness_doc = {
        "schema": "freecad-automatic/project-readiness",
        "schema_version": 1,
        "project_id": "cli-arquivo",
        "input": spec,
        "status": "ready",
        "can_start_project_loop": True,
        "source_verification": {
            "status": "ready", "ok": True,
        },
    }
    (readiness / "project-readiness.json").write_text(
        json.dumps(readiness_doc), encoding="utf-8")
    out_dir = tmp_path / "run"

    code = main([
        "--spec", str(source), "--readiness", str(readiness),
        "--require-source-refs", "--out-dir", str(out_dir), "--no-ifc",
    ])

    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["readiness"] == str(readiness / "project-readiness.json")
    assert (out_dir / "project-run.json").exists()
    persisted = json.loads(
        (out_dir / "project-run.json").read_text(encoding="utf-8"))
    assert persisted["readiness"]["status"] == "ready"
    assert persisted["readiness"]["project_id"] == "cli-arquivo"
    assert len(persisted["readiness"]["sha256"]) == 64


def test_cli_iteration_plan_requires_and_records_approved_readiness(
        tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    spec = _write_minimal_spec(source)
    spec["source_refs"] = {"incendio": [{
        "notebook_id": "nb-fire",
        "source_id": "src-fire",
        "status": 2,
    }]}
    source.write_text(json.dumps(spec), encoding="utf-8")
    plan = tmp_path / "iteration-plan.json"
    plan.write_text(json.dumps({"steps": [{
        "updates": {
            "turnkey.incendio.iluminacao_emergencia.fluxo_bloco_lm": 400,
        },
    }]}), encoding="utf-8")
    readiness = tmp_path / "readiness.json"
    readiness.write_text(json.dumps({
        "schema": "freecad-automatic/project-readiness",
        "schema_version": 1,
        "project_id": "cli-arquivo",
        "input": spec,
        "status": "ready",
        "can_start_project_loop": True,
        "source_verification": {"status": "ready", "ok": True},
    }), encoding="utf-8")
    out_dir = tmp_path / "sequence"

    code = main([
        "--spec", str(source), "--iteration-plan", str(plan),
        "--readiness", str(readiness), "--require-source-refs",
        "--out-dir", str(out_dir), "--no-ifc",
    ])

    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["readiness"] == str(readiness.resolve())
    persisted = json.loads(
        (out_dir / "project-sequence.json").read_text(encoding="utf-8"))
    assert persisted["completed_iterations"] == 2
    assert persisted["readiness"]["status"] == "ready"
    child = json.loads(
        (out_dir / "iteration-002" / "project-run.json").read_text(
            encoding="utf-8"))
    assert child["readiness"] == persisted["readiness"]
    assert (out_dir / "iteration-002" / "project-run.json").exists()


def test_cli_iteration_plan_refuses_blocked_readiness_without_output(
        tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    spec = _write_minimal_spec(source)
    plan = tmp_path / "iteration-plan.json"
    plan.write_text(json.dumps({"steps": []}), encoding="utf-8")
    readiness = tmp_path / "readiness.json"
    readiness.write_text(json.dumps({
        "schema": "freecad-automatic/project-readiness",
        "schema_version": 1,
        "project_id": "cli-arquivo",
        "input": spec,
        "status": "blocked",
        "can_start_project_loop": False,
    }), encoding="utf-8")
    out_dir = tmp_path / "sequence"

    code = main([
        "--spec", str(source), "--iteration-plan", str(plan),
        "--readiness", str(readiness), "--out-dir", str(out_dir),
        "--no-ifc",
    ])

    assert code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert not out_dir.exists()


def test_cli_refuses_blocked_readiness_without_creating_run(tmp_path, capsys):
    source = tmp_path / "project-spec.json"
    spec = _write_minimal_spec(source)
    readiness = tmp_path / "readiness.json"
    readiness.write_text(json.dumps({
        "schema": "freecad-automatic/project-readiness",
        "schema_version": 1,
        "project_id": "cli-arquivo",
        "input": spec,
        "status": "blocked",
        "can_start_project_loop": False,
    }), encoding="utf-8")
    out_dir = tmp_path / "run"

    code = main([
        "--spec", str(source), "--readiness", str(readiness),
        "--out-dir", str(out_dir), "--no-ifc",
    ])

    assert code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert not out_dir.exists()


def test_cli_returns_blocked_gate_code_for_the_unfilled_template(tmp_path):
    code = main([
        "--spec", str(SJB_TEMPLATE),
        "--out-dir", str(tmp_path / "blocked"), "--no-ifc",
    ])

    assert code == 2


def test_cli_returns_input_error_without_creating_a_partial_manifest(tmp_path):
    out_dir = tmp_path / "invalid-run"

    code = main(["--spec", str(tmp_path / "missing.json"),
                 "--out-dir", str(out_dir)])

    assert code == 4
    assert not (out_dir / "project-run.json").exists()


def test_cli_returns_failed_code_when_a_discipline_fails(tmp_path):
    source = tmp_path / "failed-spec.json"
    source.write_text(json.dumps({
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "cli-failed"},
        "turnkey": {
            "geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
            "eletrico": "invalid",
        },
    }), encoding="utf-8")
    out_dir = tmp_path / "failed-run"

    code = main(["--spec", str(source), "--out-dir", str(out_dir), "--no-ifc"])

    assert code == 3
    persisted = json.loads(
        (out_dir / "project-run.json").read_text(encoding="utf-8"))
    assert persisted["status"] == "failed"
