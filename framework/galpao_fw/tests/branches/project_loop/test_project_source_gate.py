import json

from project_source_gate import verify_project_source_refs


def _spec_with_refs():
    return {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "source-gate"},
        "source_refs": {
            "concreto": [{
                "notebook_id": "nb-concreto",
                "source_id": "src-concreto",
                "status": 2,
            }],
            "eletrico": [{
                "notebook_id": "nb-eletrico",
                "source_id": "src-eletrico",
                "status": 2,
            }],
        },
        "turnkey": {
            "geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
            "concreto": {},
            "eletrico": {},
        },
    }


def test_source_gate_confirms_declared_ids_and_remote_status():
    calls = []

    def runner(argv):
        calls.append(tuple(argv))
        notebook_id = argv[3]
        source_id = {
            "nb-concreto": "src-concreto",
            "nb-eletrico": "src-eletrico",
        }[notebook_id]
        return json.dumps([{
            "id": source_id,
            "title": notebook_id,
            "status": 2,
            "is_stale": False,
        }])

    report = verify_project_source_refs(_spec_with_refs(), runner=runner)

    assert report["status"] == "ready"
    assert report["ok"] is True
    assert report["checked_references"] == 2
    assert report["notebooks_checked"] == 2
    assert report["errors"] == []
    assert all("--json" in call and "--full" in call for call in calls)


def test_source_gate_rejects_missing_unready_and_stale_sources():
    spec = _spec_with_refs()
    spec["source_refs"]["incendio"] = [{
        "notebook_id": "nb-fire",
        "source_id": "src-fire",
        "status": 2,
    }]
    spec["turnkey"]["incendio"] = {}

    def runner(argv):
        notebook_id = argv[3]
        payloads = {
            "nb-concreto": [{
                "id": "src-concreto", "status": 3, "is_stale": False,
            }],
            "nb-eletrico": [{
                "id": "src-eletrico", "status": 2, "is_stale": True,
            }],
            "nb-fire": [],
        }
        return json.dumps(payloads[notebook_id])

    report = verify_project_source_refs(spec, runner=runner)

    assert report["status"] == "blocked"
    assert report["ok"] is False
    assert {item["code"] for item in report["errors"]} == {
        "source_not_ready", "source_stale", "source_not_found",
        "source_snapshot_mismatch",
    }
    assert {item["discipline"] for item in report["errors"]} == {
        "concreto", "eletrico", "incendio",
    }


def test_source_gate_records_query_failures_without_fabricating_ready_state():
    def runner(argv):
        raise RuntimeError("credenciais expiradas")

    report = verify_project_source_refs(_spec_with_refs(), runner=runner)

    assert report["status"] == "blocked"
    assert report["ok"] is False
    assert len(report["errors"]) == 2
    assert {item["code"] for item in report["errors"]} == {
        "notebook_query_failed",
    }


def test_source_gate_rejects_invalid_source_ref_before_query():
    spec = _spec_with_refs()
    spec["source_refs"]["concreto"][0].pop("source_id")

    def runner(argv):
        raise AssertionError("não deve consultar notebook com ref inválida")

    report = verify_project_source_refs(spec, runner=runner)

    assert report["status"] == "blocked"
    assert report["errors"][0]["code"] == "invalid_source_ref"
