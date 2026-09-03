# -*- coding: utf-8 -*-
"""
G35 — --check-remote no extrator (rebuscar a URL e comparar hash).

O G30 confere o fixture contra o PDF LOCAL, nunca que o PDF local é o que a
URL serve. A entrada sintética do example.com passava no G30 por construção
(ver test_g30_dummy_sintetico_pass, agora ancorado em tests/fixtures) com URL
que dá 404. O --check-remote fecha esse buraco refazendo o que foi feito à
mão no G29: rebuscar a URL ao vivo e comparar o SHA-256 com o registrado.

Somente leitura: não toca em registro.json nem nos arquivos guardados.
"""

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
REGISTRO = REPO / "fontes_externas" / "registro.json"
SINT = REPO / "tests" / "fixtures" / "fonte_exemplo_sintetica"
EXTRATOR = REPO / "tools" / "extrai_fonte_externa.py"


def _load_extrator():
    spec = importlib.util.spec_from_file_location("extrai_fonte_externa_g35", EXTRATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Args:
    def __init__(self, id):
        self.id = id


def _entrada_real():
    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    return registro["fontes"][0]


# ---------------------------------------------------------------------------
# Lógica pura (sem rede): sha do que a URL serve vs registrado
# ---------------------------------------------------------------------------
def test_g35_check_remote_pass_quando_hash_bate(monkeypatch):
    ext = _load_extrator()
    entry = _entrada_real()
    pdf_bytes = b"%PDF-1.4 remoto ok\n%%EOF\n"
    import hashlib
    sha = hashlib.sha256(pdf_bytes).hexdigest()
    entry = dict(entry, sha256=sha)
    monkeypatch.setattr(ext, "_download", lambda url: (pdf_bytes, sha))
    # cmd_check_remote lê o registro do disco; grava temporário de verdade
    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    registro["fontes"] = [entry]
    original = REGISTRO.read_text(encoding="utf-8")
    try:
        REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rc = ext.cmd_check_remote(_Args(entry["id"]))
    finally:
        REGISTRO.write_text(original, encoding="utf-8")
    assert rc == 0


def test_g35_check_remote_falha_quando_hash_diverge(monkeypatch):
    ext = _load_extrator()
    entry = _entrada_real()
    monkeypatch.setattr(ext, "_download", lambda url: (b"%PDF-1.4 outro conteudo\n%%EOF\n", "b" * 64))
    rc = ext.cmd_check_remote(_Args(entry["id"]))
    assert rc == 1


def test_g35_check_remote_falha_quando_download_quebra(monkeypatch):
    ext = _load_extrator()
    entry = _entrada_real()

    def _boom(url):
        raise OSError("404 Not Found (simulado)")

    monkeypatch.setattr(ext, "_download", _boom)
    rc = ext.cmd_check_remote(_Args(entry["id"]))
    assert rc == 1


def test_g35_check_remote_recusa_file():
    ext = _load_extrator()
    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    original = REGISTRO.read_text(encoding="utf-8")
    entry = {
        "id": "teste-g35-file__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL",
        "url": "file://tests/fixtures/fonte_exemplo_sintetica/exemplo_dummy.pdf",
        "sha256": "a" * 64,
        "data_coleta": "2026-09-03",
        "autor": "Teste G35",
        "classe_autoridade": "tcc_academico",
        "rotulo": "CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA",
    }
    try:
        registro["fontes"] = registro["fontes"] + [entry]
        REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rc = ext.cmd_check_remote(_Args(entry["id"]))
    finally:
        REGISTRO.write_text(original, encoding="utf-8")
    assert rc == 1


def test_g35_check_remote_id_desconhecido():
    ext = _load_extrator()
    assert ext.cmd_check_remote(_Args("nao-existe-g35")) == 1
    assert ext.cmd_check_remote(_Args("")) == 2


# ---------------------------------------------------------------------------
# Ponta a ponta via CLI
# ---------------------------------------------------------------------------
def test_g35_cli_help_menciona_check_remote():
    res = subprocess.run(
        [sys.executable, "tools/extrai_fonte_externa.py", "--help"],
        capture_output=True, text=True, cwd=str(REPO), timeout=30,
    )
    assert res.returncode == 0
    assert "--check-remote" in res.stdout


def test_g35_check_remote_sintetico_example_com_falha():
    # A prova do limite do G30: a entrada sintética passa no G30 local por
    # construção, mas a URL example.com dá 404 (ou a rede falha) — o
    # --check-remote FALHA de qualquer jeito, com ou sem internet.
    entry = json.loads((SINT / "registro_entry.json").read_text(encoding="utf-8"))
    assert "example.com" in entry["url"]
    original = REGISTRO.read_text(encoding="utf-8")
    try:
        registro = json.loads(original)
        registro["fontes"] = registro["fontes"] + [entry]
        REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        res = subprocess.run(
            [sys.executable, "tools/extrai_fonte_externa.py", "--check-remote", "--id", entry["id"]],
            capture_output=True, text=True, cwd=str(REPO), timeout=90,
        )
    finally:
        REGISTRO.write_text(original, encoding="utf-8")
    assert res.returncode != 0, f"check-remote deveria FALHAR para URL example.com 404: {res.stdout} {res.stderr}"
    combined = (res.stdout + res.stderr).lower()
    assert "falha" in combined or "404" in combined or "não foi possível" in combined or "nao foi possivel" in combined
