import json

from project_source_gate import verify_project_source_refs


class UnhashableString(str):
    __hash__ = None


def test_unhashable_notebook_id_returns_blocked_source_report_without_exception():
    notebook_id = UnhashableString("nb-eletrico")
    spec = {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "source-gate-totalidade"},
        "source_refs": {"eletrico": [{
            "notebook_id": notebook_id,
            "source_id": "src-eletrico",
            "status": 2,
        }]},
        "turnkey": {
            "geometria": {"comprimento": 10, "vao": 8, "pe_direito": 3},
            "eletrico": {},
        },
    }

    report = verify_project_source_refs(
        spec,
        runner=lambda argv: json.dumps([{
            "id": "src-eletrico",
            "status": 2,
            "is_stale": False,
        }]),
    )

    assert report["status"] == "blocked"
    assert report["ok"] is False
    assert any(error["code"] == "invalid_source_ref"
               for error in report["errors"])
