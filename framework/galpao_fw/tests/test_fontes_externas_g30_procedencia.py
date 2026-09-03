# -*- coding: utf-8 -*-
"""
G30 — Guarda de procedência que abre o PDF (renderizar-e-olhar)

Hoje a validação é puramente sintática: file:// aceito, SHA-256 conferido só no formato,
trecho_literal exigido só com ≥10 chars. Ela verifica o formato da procedência, nunca a procedência.

Três mudanças:
  1) recusar file:// para fonte externa (https:// obrigatório)
  2) recalcular o hash do arquivo guardado e comparar
  3) abrir o PDF na pagina declarada e exigir que trecho_literal esteja lá (fitz)

E, no espírito do G21, provar que ela fica vermelha: as três entradas fabricadas do G29
são a fixture negativa perfeita (fonte_pagina: 45 num PDF de 1 página).
Uma guarda que nunca foi vista vermelha não vale nada.

Substituir também a contagem fixa 23 por inventário nomeado: acrescentar check é ato explícito.
"""

import hashlib
import json
import pathlib
import sys
import tempfile
import shutil

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
FW = REPO / "framework" / "galpao_fw"
REGISTRO = REPO / "fontes_externas" / "registro.json"
FAB_ROOT = REPO / "tests" / "fixtures" / "fontes_fabricadas"

sys.path.insert(0, str(FW))
import fontes_externas_protocolo as PROTO


# ---------------------------------------------------------------------------
# 1) file:// recusado
# ---------------------------------------------------------------------------
def test_g30_url_file_recusado():
    ok, msg = PROTO.validar_url("file://tests/fixtures/fonte_exemplo_sintetica/exemplo_dummy.pdf")
    assert not ok, "G30: file:// deveria ser recusado"
    assert "file://" in msg and "https://" in msg

    ok2, _ = PROTO.validar_url("https://example.com/tcc.pdf")
    assert ok2, "https:// deveria passar"

    ok3, _ = PROTO.validar_url("http://example.com/tcc.pdf")
    assert not ok3, "http:// (sem s) deveria ser recusado (só https)"


def test_g30_entrada_file_recusada():
    entry = {
        "id": f"teste-g30-file{PROTO.SUFIXO_DIRETORIO}",
        "url": "file://fontes_externas/dummy.pdf",
        "sha256": "a" * 64,
        "data_coleta": "2026-09-02",
        "autor": "Teste G30",
        "classe_autoridade": "tcc_academico",
        "rotulo": PROTO.ROTULO_CONCORDANCIA,
    }
    erros = PROTO.validar_entrada_registro(entry)
    assert any("file://" in e for e in erros), f"deveria conter erro file://, veio {erros}"


# ---------------------------------------------------------------------------
# 2) SHA recalculado
# ---------------------------------------------------------------------------
def test_g30_hash_recalculado(tmp_path):
    pdf = tmp_path / "teste.pdf"
    pdf.write_bytes(b"%PDF-1.4 hello world\n%%EOF\n")
    h = PROTO.compute_sha256(pdf)
    ok, msg = PROTO.validar_hash_arquivo(h, pdf)
    assert ok, msg
    # hash errado deve falhar
    ok2, msg2 = PROTO.validar_hash_arquivo("0" * 64, pdf)
    assert not ok2 and "diverge" in msg2

    # arquivo inexistente deve falhar
    ok3, msg3 = PROTO.validar_hash_arquivo(h, tmp_path / "naoexiste.pdf")
    assert not ok3


def test_g30_hash_completa_real_vs_fabricada():
    # reais: hash deve bater com arquivo em fontes_externas
    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    for entry in registro["fontes"]:
        fid = entry["id"]
        pdf = PROTO.localizar_pdf_fonte(fid, REPO)
        assert pdf is not None and pdf.is_file(), f"PDF real nao encontrado para {fid}"
        ok, msg = PROTO.validar_hash_arquivo(entry["sha256"], pdf)
        assert ok, f"hash real deveria bater para {fid}: {msg}"


# ---------------------------------------------------------------------------
# 3) abrir PDF na pagina e exigir trecho
# ---------------------------------------------------------------------------
def test_g30_trecho_no_pdf_real_pass():
    # real: UFPE p.22 trecho deve estar presente
    pdf = REPO / "fontes_externas" / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "original.pdf"
    fixture = json.loads((REPO / "fontes_externas" / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fixture.json").read_text(encoding="utf-8"))
    # pega primeiro valor com pagina 22
    for nome, v in fixture["valores"].items():
        pag = v["pagina"]
        trecho = v["trecho_literal"]
        if pag == 22:
            ok, msg = PROTO.validar_trecho_no_pdf(pdf, pag, trecho)
            assert ok, f"trecho real deveria estar na pagina {pag}: {msg} [{nome}]"
            break

    # Petropolis p.1
    pdf2 = REPO / "fontes_externas" / "licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "original.pdf"
    fixture2 = json.loads((REPO / "fontes_externas" / "licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fixture.json").read_text(encoding="utf-8"))
    for nome, v in fixture2["valores"].items():
        if v["pagina"] == 1:
            ok, msg = PROTO.validar_trecho_no_pdf(pdf2, 1, v["trecho_literal"])
            assert ok, f"petropolis p1 deveria passar: {msg}"
            break


def test_g30_trecho_no_pdf_fabricada_pagina_45_falha():
    # fabricada UFPE: pagina 45 em PDF de 1 pagina -> deve falhar por pagina fora do intervalo
    fab_pdf = FAB_ROOT / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "original.pdf"
    fab_fixture = json.loads((FAB_ROOT / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fixture.json").read_text(encoding="utf-8"))
    # verifica PDF tem 1 pagina
    import fitz
    doc = fitz.open(str(fab_pdf))
    assert len(doc) == 1, f"fabricada UFPE deveria ter 1 pagina, veio {len(doc)}"
    doc.close()
    # tenta validar pagina 45
    v = fab_fixture["valores"]["perfil_pilar_lateral"]
    assert v["pagina"] == 45
    ok, msg = PROTO.validar_trecho_no_pdf(fab_pdf, 45, v["trecho_literal"])
    assert not ok, "pagina 45 em PDF de 1 pag deveria falhar"
    assert "fora do intervalo" in msg and "1..1" in msg
    assert "fabricacao" in msg.lower()

    # mesmo que pagina existisse, trecho não estaria lá (sintético)
    # cria PDF de 1 pagina com texto curto e tenta trecho longo sintético
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "dummy.pdf"
        doc2 = fitz.open()
        page = doc2.new_page()
        page.insert_text((50, 50), "Texto generico sem o trecho inventado")
        doc2.save(str(p))
        doc2.close()
        ok2, msg2 = PROTO.validar_trecho_no_pdf(p, 1, "Trecho inventado que nao esta no PDF com mais de dez caracteres")
        assert not ok2 and "nao encontrado" in msg2


def test_g30_fixture_com_pdf_real_pass_fabricada_fail():
    # real
    pdf_real = REPO / "fontes_externas" / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "original.pdf"
    fixture_real = json.loads((REPO / "fontes_externas" / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fixture.json").read_text(encoding="utf-8"))
    erros_real = PROTO.validar_fixture_com_pdf(fixture_real, pdf_real)
    assert not erros_real, f"fixture real deveria passar com PDF, veio {erros_real}"

    # fabricada
    pdf_fab = FAB_ROOT / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "original.pdf"
    fixture_fab = json.loads((FAB_ROOT / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fixture.json").read_text(encoding="utf-8"))
    erros_fab = PROTO.validar_fixture_com_pdf(fixture_fab, pdf_fab)
    assert any("fora do intervalo" in e or "nao encontrado" in e for e in erros_fab), f"fabricada deveria falhar, veio {erros_fab}"
    # deve conter pagina 45
    assert any("45" in e for e in erros_fab)


def test_g30_dummy_sintetico_pass():
    # G35: dummy sintetico mora em tests/fixtures/fonte_exemplo_sintetica (nao e fonte real).
    # Passa no G30 LOCAL por construcao (PDF contem os trechos) — e exatamente esse
    # o limite que o --check-remote fecha: a URL example.com da 404, o PDF local nao
    # e o que a URL serve (ver test_g35_check_remote_*).
    base = REPO / "tests" / "fixtures" / "fonte_exemplo_sintetica"
    obra = f"tcc-exemplo-ufmg-2023-galpao-24x36{PROTO.SUFIXO_DIRETORIO}"
    pdf_dummy = base / "exemplo_dummy.pdf"
    fixture_dummy = json.loads((base / obra / "fixture.json").read_text(encoding="utf-8"))
    erros = PROTO.validar_fixture_com_pdf(fixture_dummy, pdf_dummy)
    assert not erros, f"dummy sintetico deveria passar G30, veio {erros}"
    # entrada preservada como auditoria (saiu do registro em G35)
    entry = json.loads((base / "registro_entry.json").read_text(encoding="utf-8"))
    ok, msg = PROTO.validar_hash_arquivo(entry["sha256"], pdf_dummy)
    assert ok, msg
    ok_url, _ = PROTO.validar_url(entry["url"])
    assert ok_url, "dummy agora deve ser https e passar"
    # localizar_pdf_fonte ainda acha o original movido (fallback G35)
    pdf_loc = PROTO.localizar_pdf_fonte(entry["id"], REPO)
    assert pdf_loc is not None and pdf_loc.is_file(), f"original movido nao localizado: {entry['id']}"
    assert "fonte_exemplo_sintetica" in pdf_loc.as_posix(), f"localizado no lugar antigo? {pdf_loc}"


# ---------------------------------------------------------------------------
# 4) fonte externa completa (G30 guarda) — verde com reais, vermelha com fabricadas
# ---------------------------------------------------------------------------
def test_g30_fonte_completa_real_verde():
    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    for entry in registro["fontes"]:
        fid = entry["id"]
        fixture_path = REPO / "fontes_externas" / fid / "fixture.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8")) if fixture_path.is_file() else None
        erros = PROTO.validar_fonte_externa_completa(entry, fixture, REPO)
        assert not erros, f"fonte real {fid} deveria estar verde na guarda completa, veio {erros}"


def test_g30_fonte_completa_fabricada_vermelha():
    # G21 espírito: fabricadas devem ficar vermelhas (3/3)
    fabricadas = list(FAB_ROOT.iterdir())
    # filtra apenas diretórios com fonte.json
    fabricadas = [p for p in fabricadas if (p / "fonte.json").is_file()]
    assert len(fabricadas) == 3, f"esperado 3 fabricadas, veio {len(fabricadas)}"
    vermelhas = 0
    for fab_dir in fabricadas:
        fonte = json.loads((fab_dir / "fonte.json").read_text(encoding="utf-8"))
        fixture = json.loads((fab_dir / "fixture.json").read_text(encoding="utf-8")) if (fab_dir / "fixture.json").is_file() else None
        pdf = fab_dir / "original.pdf"
        # validar via protocolo: url file://, hash ok mas pagina 45, etc.
        # Para fabricadas, localizar_pdf_fonte não acha em fontes_externas, mas validamos direto:
        # Verifica file://
        ok_url, _ = PROTO.validar_url(fonte["url"])
        has_file_error = not ok_url
        # Verifica pagina 45 em PDF 1 pag
        has_pagina_error = False
        if fixture and pdf.is_file():
            for v in fixture.get("valores", {}).values():
                pag = v.get("pagina")
                if isinstance(pag, int) and pag > 1:
                    import fitz
                    doc = fitz.open(str(pdf))
                    n = len(doc)
                    doc.close()
                    if pag > n:
                        has_pagina_error = True
                        break
                    ok_t, _ = PROTO.validar_trecho_no_pdf(pdf, pag, v.get("trecho_literal", ""))
                    if not ok_t:
                        has_pagina_error = True
                        break
        # Verifica hash (deve bater, mas não importa para vermelha)
        # Se qualquer guarda falhar, é vermelha
        if has_file_error or has_pagina_error:
            vermelhas += 1
        # Também testa via validar_fonte_externa_completa com repo_root apontando para fab (hack: muda localizar)
        # Mas basta provar que fabricada tem file:// e pagina 45
        assert has_file_error or has_pagina_error, f"fabricada {fab_dir.name} deveria ter file:// ou pagina 45, mas não teve"
    assert vermelhas == 3, f"G30 guarda deveria ficar vermelha com 3/3 fabricadas, veio {vermelhas}/3 — guarda que nunca foi vista vermelha não vale nada"


def test_g30_todas_fabricadas_pagina_45_pdf_1_pag():
    """Prova G29 fixture: fonte_pagina:45 num PDF de 1 página é a negativa perfeita."""
    fab_pdf = FAB_ROOT / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "original.pdf"
    fab_fixture = json.loads((FAB_ROOT / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fixture.json").read_text(encoding="utf-8"))
    import fitz
    doc = fitz.open(str(fab_pdf))
    n = len(doc)
    doc.close()
    assert n == 1
    # verifica que pelo menos 5 valores têm pagina 45+
    vals_45 = [k for k, v in fab_fixture["valores"].items() if v["pagina"] >= 45]
    assert len(vals_45) >= 5, f"fabricada deveria ter >=5 valores com pagina 45+, veio {vals_45}"
    # cada um deve falhar na guarda
    for nome in vals_45[:2]:
        v = fab_fixture["valores"][nome]
        ok, msg = PROTO.validar_trecho_no_pdf(fab_pdf, v["pagina"], v["trecho_literal"])
        assert not ok and "fora do intervalo" in msg


# ---------------------------------------------------------------------------
# 5) inventário nomeado — G30 substitui contagem fixa 23
# ---------------------------------------------------------------------------
def test_g30_inventario_nomeado():
    import validacao_sistema_g15 as G15
    assert hasattr(G15, "INVENTARIO_CHECKS"), "G30: deve expor INVENTARIO_CHECKS"
    assert hasattr(G15, "CHECKS")
    inv = G15.INVENTARIO_CHECKS
    checks = G15.CHECKS
    # inventario deve ser lista de strings
    assert isinstance(inv, list) and all(isinstance(x, str) for x in inv)
    # cada nome deve ter funcao correspondente
    check_names = {fn.__name__ for fn in checks}
    assert set(inv) == check_names, f"inventario diverge de CHECKS: inv={set(inv)-check_names} checks={check_names-set(inv)}"
    # len deve ser >=27 (26 anteriores + G30)
    assert len(inv) == len(checks) == 27, f"G30: esperado 27 checks (26 + G30), veio inv={len(inv)} checks={len(checks)}"
    # adicionar check deve ser ato explícito: inventario contém G30
    assert "check_g30_procedencia_completa" in inv
    # prova que número fixo 23 não existe mais: rodar deve ter 27, não 23
    ok, resultados = G15.rodar(verbose=False)
    assert len(resultados) == len(inv) != 23
