import json
from pathlib import Path

from project_loop import (iterate_project, review_project, run_project_file,
                          verify_project_run)


def _project_spec(turnkey_fixture_with_hvac_and_hydraulic):
    return {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "galpao-sjb", "description": "galpao de teste"},
        "site": {"city": "São João da Barra", "state": "RJ", "utility": "ENEL"},
        "source_refs": {
            "eletrico": [{"notebook_id": "nb-eletrico", "source_id": "src-5410",
                           "title": "NBR 5410"}],
            "hidraulica": [{"notebook_id": "nb-hidraulica", "source_id": "src-5626",
                             "title": "NBR 5626"}],
        },
        "turnkey": turnkey_fixture_with_hvac_and_hydraulic,
    }


def test_golden_journey_project_to_manifest_coordination_and_iteration(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    spec = _project_spec(turnkey_fixture_with_hvac_and_hydraulic)
    source = tmp_path / "project-spec.json"
    source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    first = run_project_file(source, tmp_path / "iteration-001",
                             options={"generate_ifc": False})

    assert first["project_id"] == "galpao-sjb"
    assert first["site"] == {"city": "São João da Barra", "state": "RJ",
                              "utility": "ENEL"}
    assert (tmp_path / "iteration-001" / "project-run.json").exists()
    assert (tmp_path / "iteration-001" / "coordination" / "clash.json").exists()
    assert (tmp_path / "iteration-001" / "coordination" / "relatorio.txt").read_text(
        encoding="utf-8").find("CLASH FEDERADO") >= 0
    assert first["coordination"]["n_revisar"] >= 1

    second = iterate_project(
        first,
        updates={
            "turnkey.hidraulica.aparelhos_agua": {"bacia_caixa": 2},
            "turnkey.hidraulica.aparelhos_esgoto": {"bacia": 2},
        },
        options={"generate_ifc": False},
    )
    assert second["iteration"] == 2
    assert second["parent_run_id"] == first["run_id"]
    assert second["input"]["turnkey"]["hidraulica"]["aparelhos_esgoto"] == {"bacia": 2}
    assert second["input_sha256"] != first["input_sha256"]
    assert (tmp_path / "iteration-002" / "project-run.json").exists()

    persisted = json.loads((tmp_path / "iteration-002" / "project-run.json").read_text(
        encoding="utf-8"))
    assert persisted["parent_run_id"] == first["run_id"]
    assert all(not item["path"].startswith("C:") for item in persisted["artifacts"])

    review_plan = {
        "schema": "freecad-automatic/coordination-resolution-plan",
        "schema_version": 1,
        "parent_run_id": second["run_id"],
        "project_id": second["project_id"],
        "decisions": [],
    }
    third = review_project(
        second, review_plan, tmp_path / "iteration-003",
        options={"generate_ifc": False},
    )
    assert third["iteration"] == 3
    assert third["parent_run_id"] == second["run_id"]
    assert third["coordination"]["review_status"] == "needs_review"
    assert (tmp_path / "iteration-003" / "coordination" /
            "resolution-plan.json").exists()
    assert (tmp_path / "iteration-003" / "coordination" /
            "review-report.json").exists()
    assert verify_project_run(tmp_path / "iteration-003")["ok"] is True

    repository_root = (Path(__file__).resolve().parents[3].parent.parent /
                       Path(__file__).resolve().parents[4].name)
    house_spec = (repository_root / "projects" /
                  "casa-residencial-sintetica" / "project-spec.json")
    house = run_project_file(
        house_spec, tmp_path / "residencial",
        options={"generate_ifc": False},
    )
    assert house["adapter"] == "casa-residencial-sintetica"
    assert house["status"] == "needs_review"
    assert verify_project_run(tmp_path / "residencial")["ok"] is True
