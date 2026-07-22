"""Despacho bridge vs headless do montar_modelo (item 3: nao depender do FreeCAD
aberto). Testa a LOGICA de escolha/fallback sem subir FreeCAD (monkeypatch dos
dois construtores e do preparo do spec)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rodar_projeto as RP


def _stub_prep(monkeypatch, called):
    """Neutraliza o preparo (spec/build src) e instrumenta os 2 construtores."""
    monkeypatch.setattr(RP.PS, "exigir_completo", lambda s: None)
    monkeypatch.setattr(RP.PS, "to_build_kwargs", lambda s: {})
    monkeypatch.setattr(RP, "_ship_build_src", lambda p: "SRC")

    def _bridge(src, bk, host, timeout):
        called["bridge"] = True
        return {"result": {"via": "bridge", "elementos": 1}}

    def _headless(src, bk, out_dir, timeout, exe=None):
        called["headless"] = True
        return {"result": {"via": "headless", "elementos": 2}}

    monkeypatch.setattr(RP, "_montar_bridge", _bridge)
    monkeypatch.setattr(RP, "_montar_headless", _headless)


def test_headless_true_forca_headless(monkeypatch, tmp_path):
    called = {}
    _stub_prep(monkeypatch, called)
    r = RP.montar_modelo({}, str(tmp_path), "d", headless=True)
    assert called.get("headless") and not called.get("bridge")
    assert r["result"]["via"] == "headless"


def test_headless_false_usa_bridge(monkeypatch, tmp_path):
    called = {}
    _stub_prep(monkeypatch, called)
    r = RP.montar_modelo({}, str(tmp_path), "d", headless=False)
    assert called.get("bridge") and not called.get("headless")
    assert r["result"]["via"] == "bridge"


def test_default_prefere_bridge_quando_disponivel(monkeypatch, tmp_path):
    called = {}
    _stub_prep(monkeypatch, called)
    monkeypatch.delenv("FREECAD_HEADLESS", raising=False)
    r = RP.montar_modelo({}, str(tmp_path), "d")           # headless=None
    assert called.get("bridge") and not called.get("headless")


def test_fallback_para_headless_quando_bridge_recusa(monkeypatch, tmp_path):
    called = {}
    _stub_prep(monkeypatch, called)
    monkeypatch.delenv("FREECAD_HEADLESS", raising=False)

    def _bridge_down(src, bk, host, timeout):
        called["bridge"] = True
        raise ConnectionRefusedError("porta 9875 recusada")

    monkeypatch.setattr(RP, "_montar_bridge", _bridge_down)
    r = RP.montar_modelo({}, str(tmp_path), "d")           # None -> tenta bridge, cai
    assert called.get("bridge") and called.get("headless")
    assert r["result"]["via"] == "headless"


def test_erro_real_de_build_NAO_cai_para_headless(monkeypatch, tmp_path):
    # o bridge retorna erro como DICT (nao excecao) -> nao aciona fallback headless
    called = {}
    _stub_prep(monkeypatch, called)
    monkeypatch.delenv("FREECAD_HEADLESS", raising=False)

    def _bridge_erro(src, bk, host, timeout):
        called["bridge"] = True
        return {"error": "build quebrou dentro do FreeCAD"}

    monkeypatch.setattr(RP, "_montar_bridge", _bridge_erro)
    r = RP.montar_modelo({}, str(tmp_path), "d")
    assert called.get("bridge") and not called.get("headless")
    assert "error" in r


def test_env_freecad_headless_forca(monkeypatch, tmp_path):
    called = {}
    _stub_prep(monkeypatch, called)
    monkeypatch.setenv("FREECAD_HEADLESS", "1")
    r = RP.montar_modelo({}, str(tmp_path), "d")           # None + env -> headless
    assert called.get("headless") and not called.get("bridge")
