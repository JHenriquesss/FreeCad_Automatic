import json
from pathlib import Path

import project_loop
from project_loop import iterate_project, run_project


def _complete_synthetic_structural_spec():
    """Base estrutural independente do empreendimento real SJB/ENEL."""
    # Ancorado no arquivo de teste: a suite roda com CWD na raiz do
    # repositorio ou em framework/galpao_fw (CI).
    source = (Path(__file__).resolve().parents[3]
              / "spec_amostra_engenheiro.json")
    structural = json.loads(source.read_text(encoding="utf-8"))
    structural["terreno"].update({
        "kml": None,
        "area_lote_m2": 5000.0,
        "to_max": 0.6,
        "ca_max": 1.0,
        "tp_min": 0.2,
        "recuos": {"frente": 8.0, "lateral": 1.5, "fundos": 0.0},
    })
    structural["estrutura"].update({
        "perfil_col": "HEA200",
        "perfil_raf": "HEA180",
        "contraventamento": "d20",
    })
    structural["geometria"].update({
        "span": 20.0, "comprimento": 40.0, "eave": 6.0,
        "ridge": 7.0, "bay": 40.0 / 7.0,
    })
    structural["vento"].update({
        "v0": 40.0, "cat": "IV", "s3": 1.0, "z": 7.0,
    })
    structural["cargas"].update({
        "G": 0.30, "Q": 0.25, "self": 0.35, "tapamento": 0.10,
    })
    structural["fundacao"]["sigma_solo_adm"] = 250.0
    return structural


def test_real_turnkey_execution_isolated_and_persists_native_gates(tmp_path, turnkey_fixture):
    result = run_project(turnkey_fixture(), tmp_path,
                         options={"generate_ifc": False})
    assert set(result["disciplines"]) == {"concreto", "eletrico", "incendio"}
    assert result["disciplines"]["concreto"]["native_atende"] is True
    assert result["disciplines"]["eletrico"]["gates"]
    assert (tmp_path / "reports" / "disciplinas.json").exists()


def test_complete_synthetic_project_runs_six_disciplines_detects_and_iterates(
        tmp_path, turnkey_fixture):
    structural = _complete_synthetic_structural_spec()
    turnkey = turnkey_fixture(climatizacao={"tipo": "galpao"}, hidraulica={})
    turnkey["aco"] = structural
    spec = {
        "schema": "freecad-automatic/project-spec",
        "schema_version": 1,
        "project": {"slug": "turnkey-all-disciplines-smoke", "type": "galpao"},
        "site": {"city": "São João da Barra", "state": "RJ", "utility": "ENEL"},
        "structure": structural,
        "turnkey": turnkey,
    }

    first = run_project(spec, tmp_path / "iteration-001",
                        options={"generate_ifc": False})

    assert set(first["disciplines"]) == {
        "concreto", "aco", "eletrico", "incendio", "climatizacao", "hidraulica"}
    assert all(item["status"] in {"passed", "needs_review"}
               for item in first["disciplines"].values())
    assert first["coordination"]["status"] == "generated"
    assert first["coordination"]["n_clashes"] > 0
    assert (tmp_path / "iteration-001" / "coordination" / "clash.json").exists()
    assert first["verification"]["ok"] is True

    second = iterate_project(
        first,
        updates={"turnkey.geometria.pe_direito": 6.5},
        options={"generate_ifc": False},
    )

    assert second["iteration"] == 2
    assert second["parent_run_id"] == first["run_id"]
    assert second["input"]["turnkey"]["geometria"]["pe_direito"] == 6.5
    assert second["coordination"]["status"] == "generated"
    assert second["verification"]["ok"] is True
    assert (tmp_path / "iteration-002" / "project-run.json").exists()


def test_hydraulic_default_is_never_project_passed(tmp_path, turnkey_fixture):
    result = run_project(turnkey_fixture(hidraulica={}), tmp_path,
                         options={"generate_ifc": False})
    assert result["disciplines"]["hidraulica"]["status"] == "needs_review"
    assert result["status"] == "needs_review"
    assert result["atende"] is False


def test_invalid_discipline_does_not_hide_independent_discipline(tmp_path,
                                                                  turnkey_fixture):
    result = run_project(turnkey_fixture(eletrico="invalid", incendio={
        "iluminacao_emergencia": {"fluxo_bloco_lm": 350}}), tmp_path,
        options={"generate_ifc": False})
    assert result["disciplines"]["eletrico"]["status"] == "failed"
    assert result["disciplines"]["incendio"]["status"] != "failed"
    assert result["status"] == "failed"


def test_unexpected_adapter_exception_persists_failed_manifest(
        tmp_path, turnkey_fixture, monkeypatch):
    def broken_adapter(normalized, run_dir):
        (run_dir / "reports" / "partial-output.bin").write_bytes(b"partial")
        raise RuntimeError("falha inesperada do adaptador")

    monkeypatch.setitem(project_loop._PROJECT_ADAPTERS, "galpao", broken_adapter)

    result = run_project(turnkey_fixture(), tmp_path,
                         options={"generate_ifc": False})

    assert result["status"] == "failed"
    assert result["atende"] is False
    assert result["errors"][0]["code"] == "execution_failed"
    assert result["verification"]["ok"] is True
    persisted = json.loads(
        (tmp_path / "project-run.json").read_text(encoding="utf-8"))
    assert persisted["status"] == "failed"
    assert persisted["errors"] == result["errors"]
    assert (tmp_path / "reports" / "execution-error.json").exists()
    partial = next(item for item in persisted["artifacts"]
                   if item["path"] == "reports/partial-output.bin")
    assert partial["status"] == "partial"
    assert result["verification"]["valid_artifacts"] == \
        result["verification"]["artifact_count"]
