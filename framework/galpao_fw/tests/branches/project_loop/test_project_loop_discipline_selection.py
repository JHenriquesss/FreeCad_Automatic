import galpao_turnkey

from project_loop import run_project


def test_required_disciplines_scope_is_applied_to_runner_coordination_and_ifc(
        monkeypatch, tmp_path, turnkey_fixture):
    seen = {}
    original_rodar = galpao_turnkey.rodar
    original_clash = galpao_turnkey.checa_interferencia_federada
    original_ifc = galpao_turnkey.emitir_bim

    def capture_rodar(spec, out_dir=None):
        seen["runner"] = spec
        return original_rodar(spec, out_dir)

    def capture_clash(result, spec=None, **kwargs):
        seen["coordination"] = spec
        return original_clash(result, spec, **kwargs)

    def capture_ifc(result, out_dir, spec=None, **kwargs):
        seen["ifc"] = spec
        return original_ifc(result, out_dir, spec=spec, **kwargs)

    monkeypatch.setattr(galpao_turnkey, "rodar", capture_rodar)
    monkeypatch.setattr(galpao_turnkey,
                        "checa_interferencia_federada", capture_clash)
    monkeypatch.setattr(galpao_turnkey, "emitir_bim", capture_ifc)

    result = run_project(
        turnkey_fixture(), tmp_path,
        options={"required_disciplines": ("incendio",),
                 "generate_ifc": True},
    )

    expected_keys = {"geometria", "incendio"}
    assert set(seen["runner"]) == expected_keys
    assert set(seen["coordination"]) == expected_keys
    assert set(seen["ifc"]) == expected_keys
    assert set(result["disciplines"]) == {"incendio"}
    assert result["verification"]["ok"] is True
