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
def _registro_temporario(monkeypatch, ext, entries, tmp_path):
    """D81/G45: cmd_check_remote le o registro do disco. A versao anterior
    reescrevia o REGISTRO VIVO e restaurava no finally — sob `pytest -n 4`
    outro worker lia o arquivo no meio da escrita (JSON vazio) e ficava
    vermelho por CONTAMINACAO, nao por defeito (reproduzido: serial 7/7,
    paralelo 2-3 falhas variando por rodada). O ponto do G22/G21-Parte-C:
    mutar copia, nunca o repositorio vivo. Aqui a copia e um registro
    temporario e ext.REGISTRO aponta para ele so neste teste."""
    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    registro["fontes"] = list(entries)
    tmp_reg = tmp_path / "registro.json"
    tmp_reg.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # o extrator resolve o registro via _registro_path() (gancho
    # FONTES_EXTERNAS_ROOT); apontar para a copia temporaria.
    monkeypatch.setattr(ext, "_registro_path", lambda: tmp_reg)
    return tmp_reg


def test_g35_check_remote_pass_quando_hash_bate(monkeypatch, tmp_path):
    ext = _load_extrator()
    entry = _entrada_real()
    pdf_bytes = b"%PDF-1.4 remoto ok\n%%EOF\n"
    import hashlib
    sha = hashlib.sha256(pdf_bytes).hexdigest()
    entry = dict(entry, sha256=sha)
    monkeypatch.setattr(ext, "_download", lambda url: (pdf_bytes, sha))
    # cmd_check_remote lê o registro do disco; usa copia temporaria (D81)
    _registro_temporario(monkeypatch, ext, [entry], tmp_path)
    rc = ext.cmd_check_remote(_Args(entry["id"]))
    assert rc == 0
    # o repositorio vivo nunca foi tocado
    assert json.loads(REGISTRO.read_text(encoding="utf-8"))["fontes"][0]["id"] == _entrada_real()["id"]


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


def test_g35_check_remote_recusa_file(monkeypatch, tmp_path):
    ext = _load_extrator()
    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    entry = {
        "id": "teste-g35-file__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL",
        "url": "file://tests/fixtures/fonte_exemplo_sintetica/exemplo_dummy.pdf",
        "sha256": "a" * 64,
        "data_coleta": "2026-09-03",
        "autor": "Teste G35",
        "classe_autoridade": "tcc_academico",
        "rotulo": "CONCORDANCIA ENTRE CALCULISTAS - NAO E OBRA CONSTRUIDA",
    }
    # copia temporaria (D81): nao muta o REGISTRO vivo
    _registro_temporario(monkeypatch, ext, registro["fontes"] + [entry], tmp_path)
    rc = ext.cmd_check_remote(_Args(entry["id"]))
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


def test_g35_check_remote_sintetico_example_com_falha(monkeypatch, tmp_path, capsys):
    # A prova do limite do G30: a entrada sintética passa no G30 local por
    # construção, mas a URL example.com dá 404 (ou a rede falha).
    #
    # D81/G45: a versao anterior fazia isso com REDE AO VIVO (timeout 90 s)
    # + mutacao do REGISTRO VIVO + subprocesso — tres tracos da classe D81
    # num teste so: veredito dependia de carga/rede/escalonamento e o
    # read-modify-write no registro vivo contaminava os vizinhos sob -n 4
    # (JSONDecodeError em testes que nem tocam em rede). O caminho em
    # processo com _download mockado prova o mesmo limite de forma
    # deterministica: URL sintetica example.com nunca passa no check-remote,
    # com ou sem internet — o motivo (404/timeout) e detalhe do transporte,
    # nao do guarda.
    entry = json.loads((SINT / "registro_entry.json").read_text(encoding="utf-8"))
    assert "example.com" in entry["url"]
    ext = _load_extrator()
    _registro_temporario(monkeypatch, ext, [entry], tmp_path)

    def _boom(url):
        raise OSError("404 Not Found (simulado; equivale ao example.com ao vivo)")

    monkeypatch.setattr(ext, "_download", _boom)
    rc = ext.cmd_check_remote(_Args(entry["id"]))
    out = capsys.readouterr()
    assert rc != 0, f"check-remote deveria FALHAR para URL example.com 404"
    combined = (out.out + out.err).lower()
    assert "falha" in combined or "404" in combined or "não foi possível" in combined or "nao foi possivel" in combined
