from pathlib import Path

import pytest

import caderno_turnkey
import ifc_emit
import galpao_turnkey
from project_loop import run_project


def test_optional_freecad_deliverables_are_explicit_when_executable_is_missing(
        tmp_path, turnkey_fixture):
    missing_exe = str(tmp_path / "freecad-nao-existe.exe")
    result = run_project(
        turnkey_fixture(), tmp_path,
        options={"generate_ifc": False, "generate_3d": True,
                 "generate_2d": True, "generate_caderno": True,
                 "freecad_exe": missing_exe},
    )
    assert result["deliverables"]["model_3d"]["status"] == "not_available"
    assert result["deliverables"]["drawings"]["status"] == "not_available"
    assert result["status"] == "needs_review"


def test_caderno_uses_global_deadline_and_records_skipped_stages(monkeypatch,
                                                                 tmp_path):
    clock = [0.0]
    calls = []
    native = {
        "geometria": {"comprimento": 40.0, "vao": 20.0,
                      "pe_direito": 6.0},
        "executadas": ["incendio", "hidraulica"],
        "reprovados": [],
        "ATENDE": True,
        "disciplinas": {
            "incendio": {"rodou": True, "ATENDE": True, "reprovados": []},
            "hidraulica": {"rodou": True, "ATENDE": True, "reprovados": []},
        },
    }

    monkeypatch.setattr(caderno_turnkey, "_monotonic",
                        lambda: clock[0])
    monkeypatch.setattr(galpao_turnkey, "rodar",
                        lambda spec, out_dir: native)
    monkeypatch.setattr(galpao_turnkey, "checa_interferencia_federada",
                        lambda result, spec: {"n_clashes": 0})

    def consume_deadline(*args, **kwargs):
        clock[0] = 2.0
        return {"vistas": []}

    monkeypatch.setattr(galpao_turnkey, "render_federado", consume_deadline)
    monkeypatch.setattr(
        caderno_turnkey, "_dispatch_pranchas",
        lambda *args, **kwargs: calls.append(kwargs["timeout"]) or {"ok": True},
    )

    result = caderno_turnkey.montar_caderno(
        {"slug": "prazo-global"}, tmp_path, disciplinas=native["executadas"],
        freecad_exe="freecad.exe", timeout=1,
    )

    assert result["timed_out"] is True
    assert result["timeout_seconds"] == 1
    assert result["status"]["incendio"]["timeout"] is True
    assert result["status"]["hidraulica"]["timeout"] is True
    assert calls == []
    assert Path(result["path"]).is_file()


def test_caderno_shares_budget_between_render_and_disciplines(monkeypatch,
                                                               tmp_path):
    clock = [0.0]
    render_timeouts = []
    dispatch_timeouts = []
    native = {
        "geometria": {"comprimento": 40.0, "vao": 20.0,
                      "pe_direito": 6.0},
        "executadas": ["incendio", "hidraulica"],
        "reprovados": [],
        "ATENDE": True,
        "disciplinas": {
            "incendio": {"rodou": True, "ATENDE": True, "reprovados": []},
            "hidraulica": {"rodou": True, "ATENDE": True, "reprovados": []},
        },
    }

    monkeypatch.setattr(caderno_turnkey, "_monotonic",
                        lambda: clock[0])
    monkeypatch.setattr(galpao_turnkey, "rodar",
                        lambda spec, out_dir: native)
    monkeypatch.setattr(galpao_turnkey, "checa_interferencia_federada",
                        lambda result, spec: {"n_clashes": 0})

    def capture_render(*args, **kwargs):
        render_timeouts.append(kwargs["timeout"])
        return {"vistas": []}

    def consume_dispatch(*args, **kwargs):
        timeout = args[-1]
        dispatch_timeouts.append(timeout)
        clock[0] += timeout
        return {"ok": True}

    monkeypatch.setattr(galpao_turnkey, "render_federado", capture_render)
    monkeypatch.setattr(caderno_turnkey, "_dispatch_pranchas",
                        consume_dispatch)

    result = caderno_turnkey.montar_caderno(
        {"slug": "prazo-compartilhado"}, tmp_path,
        disciplinas=native["executadas"], freecad_exe="freecad.exe", timeout=9,
    )

    assert result["timed_out"] is False
    assert 0 < render_timeouts[0] < 9
    assert len(dispatch_timeouts) == 2
    assert all(0 < value < 9 for value in dispatch_timeouts)
    assert sum(dispatch_timeouts) <= 9


def test_caderno_reserva_mais_tempo_para_aco_no_lote_federado(monkeypatch,
                                                               tmp_path):
    clock = [0.0]
    render_timeouts = []
    dispatch_timeouts = {}
    disciplines = ["concreto", "aco", "eletrico", "incendio",
                   "climatizacao", "hidraulica"]
    native = {
        "geometria": {"comprimento": 40.0, "vao": 20.0,
                      "pe_direito": 6.0},
        "executadas": disciplines,
        "reprovados": [],
        "ATENDE": True,
        "disciplinas": {
            name: {"rodou": True, "ATENDE": True, "reprovados": []}
            for name in disciplines
        },
    }

    monkeypatch.setattr(caderno_turnkey, "_monotonic",
                        lambda: clock[0])
    monkeypatch.setattr(galpao_turnkey, "rodar",
                        lambda spec, out_dir: native)
    monkeypatch.setattr(galpao_turnkey, "checa_interferencia_federada",
                        lambda result, spec: {"n_clashes": 0})

    def consume_render(*args, **kwargs):
        timeout = kwargs["timeout"]
        render_timeouts.append(timeout)
        clock[0] += timeout
        return {"vistas": []}

    def consume_dispatch(*args, **kwargs):
        name = args[0]
        timeout = args[-1]
        dispatch_timeouts[name] = timeout
        clock[0] += timeout
        return {"ok": True}

    monkeypatch.setattr(galpao_turnkey, "render_federado", consume_render)
    monkeypatch.setattr(caderno_turnkey, "_dispatch_pranchas",
                        consume_dispatch)

    result = caderno_turnkey.montar_caderno(
        {"slug": "rateio-federado"}, tmp_path,
        disciplinas=disciplines, freecad_exe="freecad.exe", timeout=1800,
    )

    assert result["timed_out"] is False
    assert set(dispatch_timeouts) == set(disciplines)
    assert dispatch_timeouts["aco"] > 800
    assert sum(render_timeouts) + sum(dispatch_timeouts.values()) == \
        pytest.approx(1800, abs=1e-6)


def test_aco_dispatch_splits_stage_timeout_between_model_and_executive(
        monkeypatch, tmp_path):
    import rodar_projeto
    seen = {}

    def fake_rodar_tudo(spec, out_dir=None, **kwargs):
        seen.update(kwargs)
        return {"executivo": {"ok": True}, "atende": True}

    monkeypatch.setattr(rodar_projeto, "rodar_tudo", fake_rodar_tudo)
    result = caderno_turnkey._dispatch_pranchas(
        "aco", {}, str(tmp_path), {}, "freecad.exe", 20,
    )

    assert result["ok"] is True
    assert 0 < seen["timeout_3d"] < 20
    assert 0 < seen["timeout_exec"] < 20
    assert seen["timeout_3d"] + seen["timeout_exec"] <= 20


def test_project_manifest_preserves_caderno_timeout_diagnostic(
        monkeypatch, tmp_path, turnkey_fixture):
    freecad = tmp_path / "freecad.exe"
    freecad.write_bytes(b"placeholder")

    def timed_out_caderno(spec, out_dir, **kwargs):
        caderno = Path(out_dir) / "CADERNO.pdf"
        caderno.parent.mkdir(parents=True, exist_ok=True)
        caderno.write_bytes(b"partial-pdf")
        return {
            "path": str(caderno),
            "erro": "timeout global do caderno (1s)",
            "timed_out": True,
            "timeout_seconds": 1.0,
            "status": {"concreto": {"timeout": True}},
        }

    monkeypatch.setattr(caderno_turnkey, "montar_caderno", timed_out_caderno)

    result = run_project(
        turnkey_fixture(), tmp_path / "run",
        options={"generate_ifc": False, "generate_2d": True,
                 "generate_caderno": True, "freecad_exe": str(freecad)},
    )

    drawings = result["deliverables"]["drawings"]
    assert drawings["status"] == "failed"
    assert drawings["result"]["timed_out"] is True
    assert drawings["result"]["timeout_seconds"] == 1.0
    assert any(item["path"] == "drawings/CADERNO.pdf"
               for item in result["artifacts"])
    assert result["status"] == "failed"
    assert result["verification"]["ok"] is True


def test_project_manifest_rejects_partial_drawing_disciplines(
        monkeypatch, tmp_path, turnkey_fixture):
    freecad = tmp_path / "freecad.exe"
    freecad.write_bytes(b"placeholder")

    def partial_caderno(spec, out_dir, **kwargs):
        caderno = Path(out_dir) / "CADERNO.pdf"
        caderno.parent.mkdir(parents=True, exist_ok=True)
        caderno.write_bytes(b"partial-pdf")
        return {
            "path": str(caderno),
            "n_pranchas": 1,
            "disciplinas": {"incendio": 1, "eletrico": 1},
            "status": {"incendio": {"ok": True},
                        "eletrico": {"erro": "timeout aguardando pranchas"}},
            "timed_out": False,
        }

    monkeypatch.setattr(caderno_turnkey, "montar_caderno", partial_caderno)

    result = run_project(
        turnkey_fixture(), tmp_path / "run",
        options={"generate_ifc": False, "generate_2d": True,
                 "freecad_exe": str(freecad)},
    )

    drawings = result["deliverables"]["drawings"]
    assert drawings["status"] == "failed"
    assert drawings["result"]["missing_disciplines"] == ["concreto"]
    assert drawings["result"]["failed_disciplines"] == ["eletrico"]
    assert result["status"] == "failed"
    assert result["verification"]["ok"] is True


def test_project_manifest_rejects_partial_ifc_disciplines(
        monkeypatch, tmp_path, turnkey_fixture):
    def partial_ifc(result, out_dir, spec=None, **kwargs):
        bim = Path(out_dir) / "bim"
        bim.mkdir(parents=True, exist_ok=True)
        path = bim / "incendio.ifc"
        path.write_bytes(b"ifc")
        return {"dir": str(bim), "arquivos": {"incendio": str(path)},
                "federado": None}

    monkeypatch.setattr(ifc_emit, "disponivel", lambda: True)
    monkeypatch.setattr(galpao_turnkey, "emitir_bim", partial_ifc)

    result = run_project(
        turnkey_fixture(), tmp_path / "run",
        options={"required_disciplines": ("incendio", "eletrico"),
                 "generate_ifc": True},
    )

    ifc = result["deliverables"]["ifc"]
    assert ifc["status"] == "failed"
    assert ifc["missing_disciplines"] == ["eletrico"]
    assert result["status"] == "failed"
    assert result["verification"]["ok"] is True


def test_project_manifest_rejects_partial_model_disciplines(
        monkeypatch, tmp_path, turnkey_fixture):
    freecad = tmp_path / "freecad.exe"
    freecad.write_bytes(b"placeholder")

    def partial_model(result, out_dir, **kwargs):
        model = Path(out_dir)
        model.mkdir(parents=True, exist_ok=True)
        (model / "_montar_result.json").write_text(
            '{"por_disciplina":{"incendio":{"n":1}}}', encoding="utf-8")
        return {"result": {"por_disciplina": {"incendio": {"n": 1}}}}

    monkeypatch.setattr(galpao_turnkey, "montar_3d_federado", partial_model)

    result = run_project(
        turnkey_fixture(), tmp_path / "run",
        options={"required_disciplines": ("incendio", "eletrico"),
                 "generate_ifc": False, "generate_3d": True,
                 "freecad_exe": str(freecad)},
    )

    model = result["deliverables"]["model_3d"]
    assert model["status"] == "failed"
    assert model["missing_disciplines"] == ["eletrico"]
    assert result["status"] == "failed"
    assert result["verification"]["ok"] is True
