import json

import project_loop as project_loop_module
from project_loop import (describe_adapters, register_adapter, register_artifact,
                          run_project)


def _external_runner(normalized, run_dir):
    return {"disciplinas": {"arquitetura": {"rodou": True}}}, {
        "arquitetura": {
            "status": "passed", "native_atende": True,
            "reprovados": [], "gates": {}, "warnings": [],
            "errors": [], "artifacts": [],
        },
    }


def test_registered_external_adapter_accepts_its_discipline_without_galpao_calls(
        tmp_path):
    register_adapter(
        "teste-arquitetura", _external_runner,
        project_types=("residencial",),
        disciplines=("arquitetura",),
        deliverables=("ifc",),
    )
    result = run_project(
        {"adapter": "teste-arquitetura",
         "project": {"slug": "casa-teste", "type": "residencial"},
         "geometria": {"comprimento": 10, "vao": 8, "pe_direito": 3},
         "arquitetura": {"programa": "pendente"}},
        tmp_path, options={"generate_ifc": False},
    )

    assert result["status"] == "needs_review"
    assert result["disciplines"]["arquitetura"]["status"] == "passed"
    assert result["preflight"]["adapter_capabilities"]["disciplines"] == [
        "arquitetura"]
    assert result["coordination"]["status"] == "not_available"
    assert result["deliverables"]["ifc"]["status"] == "not_requested"
    report = tmp_path / "reports" / "adapter-result.json"
    assert report.exists()
    assert json.loads(report.read_text(encoding="utf-8"))["disciplinas"]


def test_adapter_blocks_an_explicitly_unsupported_project_type(tmp_path):
    register_adapter(
        "teste-arquitetura-tipo", _external_runner,
        project_types=("residencial",), disciplines=("arquitetura",),
    )
    result = run_project(
        {"adapter": "teste-arquitetura-tipo",
         "project": {"slug": "galpao-incompativel", "type": "industrial"},
         "geometria": {"comprimento": 10, "vao": 8, "pe_direito": 3},
         "arquitetura": {"programa": "pendente"}},
        tmp_path, options={"generate_ifc": False},
    )

    assert result["status"] == "blocked"
    issue = next(item for item in result["preflight"]["errors"]
                 if item["code"] == "unsupported_project_type")
    assert issue["project_type"] == "industrial"
    assert issue["supported_project_types"] == ["residencial"]
    assert not (tmp_path / "disciplines").exists()


def test_unknown_adapter_lists_registered_capabilities(tmp_path):
    result = run_project(
        {"adapter": "nao-existe",
         "geometria": {"comprimento": 10, "vao": 8, "pe_direito": 3}},
        tmp_path,
    )

    error = next(item for item in result["preflight"]["errors"]
                 if item["code"] == "unsupported_adapter")
    assert "galpao" in error["supported_adapters"]


def test_external_adapter_hook_can_register_its_own_ifc(tmp_path):
    def emit_ifc(manifest, run_dir, normalized, options, adapter_result):
        path = tmp_path / "bim" / "arquitetura.ifc"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("IFC-ARQUITETURA", encoding="utf-8")
        manifest["deliverables"]["ifc"] = {
            "status": "generated", "artifacts": ["bim/arquitetura.ifc"]}
        manifest["artifacts"].append(
            register_artifact(run_dir, path, "ifc-discipline",
                              discipline="arquitetura"))

    register_adapter(
        "teste-arquitetura-ifc", _external_runner,
        project_types=("residencial",), disciplines=("arquitetura",),
        deliverables=("ifc",), hooks={"ifc": emit_ifc},
    )
    result = run_project(
        {"adapter": "teste-arquitetura-ifc",
         "project": {"slug": "casa-ifc"},
         "geometria": {"comprimento": 10, "vao": 8, "pe_direito": 3},
         "arquitetura": {"programa": "pendente"}},
        tmp_path, options={"generate_ifc": True},
    )

    assert result["deliverables"]["ifc"]["status"] == "generated"
    assert any(item["path"] == "bim/arquitetura.ifc"
               for item in result["artifacts"])
    assert result["coordination"]["status"] == "not_available"


def test_galpao_capabilities_are_json_safe_and_descriptive():
    galpao = next(item for item in describe_adapters()
                  if item["name"] == "galpao")

    assert galpao["project_types"] == ["galpao", "industrial"]
    assert galpao["disciplines"] == [
        "concreto", "aco", "eletrico", "incendio",
        "climatizacao", "hidraulica"]
    assert galpao["deliverables"] == [
        "ifc", "model_3d", "drawings", "coordination", "iteration"]


def test_galpao_report_is_registered_as_a_native_hook(tmp_path, turnkey_fixture):
    assert callable(project_loop_module._PROJECT_HOOKS["galpao"]["report"])
    result = run_project(turnkey_fixture(), tmp_path,
                         options={"generate_ifc": False})
    artifact = next(item for item in result["artifacts"]
                    if item["path"] == "reports/turnkey.txt")
    assert artifact["kind"] == "turnkey-report"
    assert len(artifact["sha256"]) == 64
