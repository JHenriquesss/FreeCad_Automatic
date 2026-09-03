# -*- coding: utf-8 -*-
"""
G24 — Protocolo de Fonte Externa: testes do protocolo

Valida que:
  - registro existe e é válido
  - hierarquia licitacao_executada > ... > material_comercial
  - veredito é enum fechado (5 valores) escrito antes de ver resultado
  - só framework_errado + citação normativa autoriza mudar framework
  - todo número no fixture carrega pagina + trecho_literal (guarda fabricação)
  - valor sem procedência reprova
  - rótulo CONCORDANCIA ENTRE CALCULISTAS aparece em 4 lugares
  - extrator tools/extrai_fonte_externa.py roda por URL e grava procedência
"""

import json
import pathlib
import subprocess
import sys
import tempfile
import shutil

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
REGISTRO = REPO / "fontes_externas" / "registro.json"
README = REPO / "fontes_externas" / "README.md"
FW = REPO / "framework" / "galpao_fw"

# importa protocolo
sys.path.insert(0, str(FW))
import fontes_externas_protocolo as PROTO


# ---------------------------------------------------------------------------
# Registro existe e é válido
# ---------------------------------------------------------------------------
def test_g24_registro_existe():
    assert REGISTRO.is_file(), f"registro não existe: {REGISTRO} — G24 bloqueia comparações antes disto"
    data = json.loads(REGISTRO.read_text(encoding="utf-8"))
    erros = PROTO.validar_registro(data)
    assert not erros, f"registro inválido: {erros}"


def test_g24_registro_entrada_tem_campos_obrigatorios():
    data = json.loads(REGISTRO.read_text(encoding="utf-8"))
    assert "fontes" in data and isinstance(data["fontes"], list)
    assert len(data["fontes"]) >= 1, "registro deve ter ao menos 1 entrada exemplo"
    for entry in data["fontes"]:
        for campo in ["id", "url", "sha256", "data_coleta", "autor", "classe_autoridade"]:
            assert campo in entry, f"campo {campo} ausente em {entry.get('id')}"
        assert PROTO.SUFIXO_DIRETORIO in entry["id"], f"id sem sufixo {PROTO.SUFIXO_DIRETORIO}: {entry['id']}"
        assert PROTO.ROTULO_CONCORDANCIA in entry["rotulo"], f"rotulo sem CONCORDANCIA: {entry}"
        ok, msg = PROTO.validar_sha256(entry["sha256"])
        assert ok, msg
        ok, msg = PROTO.validar_url(entry["url"])
        assert ok, msg
        ok, msg = PROTO.validar_classe_autoridade(entry["classe_autoridade"])
        assert ok, msg


def test_g24_hierarquia_ordenada():
    # ordem escrita no protocolo deve ser exatamente a do enunciado
    assert PROTO.CLASSES_AUTORIDADE == [
        "licitacao_executada",
        "projeto_licitado",
        "livro_exemplo_resolvido",
        "tcc_academico",
        "material_comercial",
    ]
    # rank crescente (0 = maior autoridade)
    assert PROTO.hierarquia_rank("licitacao_executada") < PROTO.hierarquia_rank("tcc_academico")
    assert PROTO.hierarquia_rank("tcc_academico") < PROTO.hierarquia_rank("material_comercial")
    # tcc nunca supera licitacao
    assert PROTO.hierarquia_rank("licitacao_executada") == 0
    assert PROTO.hierarquia_rank("material_comercial") == 4


def test_g24_veredito_enum_fechado():
    assert set(PROTO.VEREDITOS) == {
        "concorda",
        "framework_errado",
        "fonte_errada",
        "hipotese_divergente",
        "nao_comparavel",
        "nao_conclusivo",
    }
    # cada veredito deve ser aceito
    for v in PROTO.VEREDITOS:
        ok, msg = PROTO.validar_veredito(v)
        assert ok, msg
    # veredito fora do enum reprova
    ok, msg = PROTO.validar_veredito("invento_novo")
    assert not ok
    ok, msg = PROTO.validar_veredito("concordo_com_fonte")
    assert not ok
    # nao_comparavel deve mencionar d·sen45 na descrição (guarda)
    assert "sen" in PROTO.VEREDITO_DESCRICAO["nao_comparavel"].lower() or "d·sen" in PROTO.VEREDITO_DESCRICAO["nao_comparavel"] or "d*sen" in PROTO.VEREDITO_DESCRICAO["nao_comparavel"].lower()
    # G31: concorda deve existir e mencionar tolerancia
    assert "concorda" in PROTO.VEREDITO_DESCRICAO
    assert "tolerancia" in PROTO.VEREDITO_DESCRICAO["concorda"].lower()


def test_g31_concorda_tolerancia_separa_hipotese():
    # G31 — regra escrita ANTES de reclassificar: tolerancia que separa concorda de hipotese_divergente
    # Deve existir constante TOLERANCIA_CONCORDA_PCT e helpers
    assert hasattr(PROTO, "TOLERANCIA_CONCORDA_PCT")
    assert hasattr(PROTO, "tolerancia_concorda_pct")
    assert hasattr(PROTO, "erro_relativo_pct")
    assert hasattr(PROTO, "classifica_concorda_ou_hipotese")
    # valores derivados de G15, não inventados para o caso
    assert PROTO.TOLERANCIA_CONCORDA_PCT["geometria"] == 2.0  # G15 eletrica 2%
    assert PROTO.TOLERANCIA_CONCORDA_PCT["massa_linear"] == 10.0  # G15 peso 10%
    assert PROTO.TOLERANCIA_CONCORDA_PCT["esforco"] == 15.0  # G15 M/H 15%
    # bay 7,5 vs 7,5 = 0% <=2% => concorda
    assert PROTO.erro_relativo_pct(7.5, 7.5) == 0.0
    assert PROTO.classifica_concorda_ou_hipotese(0.0, "geometria") == "concorda"
    assert PROTO.classifica_concorda_ou_hipotese(PROTO.erro_relativo_pct(7.5, 7.5), "geometria") == "concorda"
    # tapamento 13 vs 14 (framework ~14, fonte 13 => erro 7,1% se 13/14; 14 vs 13 => 7,7% se 13 vs UPE140 14)
    # Ambas <=10% massa_linear => concorda
    assert PROTO.classifica_concorda_ou_hipotese(7.7, "massa_linear") == "concorda"
    assert PROTO.classifica_concorda_ou_hipotese(7.14, "massa_linear") == "concorda"  # 13/14=7.14% alternativo
    # acima da tolerancia => hipotese_divergente (ainda defensavel, premissa diferente)
    assert PROTO.classifica_concorda_ou_hipotese(10.01, "massa_linear") == "hipotese_divergente"
    assert PROTO.classifica_concorda_ou_hipotese(2.01, "geometria") == "hipotese_divergente"
    # limite exato => concorda
    assert PROTO.classifica_concorda_ou_hipotese(10.0, "massa_linear") == "concorda"
    assert PROTO.classifica_concorda_ou_hipotese(2.0, "geometria") == "concorda"
    # helper tipo_grandeza
    assert PROTO.tipo_grandeza_para_comparacao("bay_porticos") == "geometria"
    assert PROTO.tipo_grandeza_para_comparacao("perfil_viga_tapamento") == "massa_linear"
    # concorda nunca autoriza mexer no framework (so framework_errado autoriza)
    import pytest as _pt
    with _pt.raises(ValueError, match="nao autoriza mexer no framework"):
        PROTO.fechar_divergencia("concorda", "NBR 8800 §", mudou_framework=True)


def test_g24_fechar_divergencia_somente_framework_errado_com_citacao():
    # só framework_errado com citação autoriza mudar framework
    PROTO.fechar_divergencia("framework_errado", "NBR 8800:2024 §5.4.3 p.60 eq.5.4-10", mudou_framework=True)  # pass

    # sem citação -> deve falhar
    with pytest.raises(ValueError, match="citacao_normativa"):
        PROTO.fechar_divergencia("framework_errado", "", mudou_framework=True)
    with pytest.raises(ValueError, match="citacao_normativa"):
        PROTO.fechar_divergencia("framework_errado", "   ", mudou_framework=True)

    # veredito diferente não autoriza mudar framework, mesmo com citação
    for v in ["fonte_errada", "hipotese_divergente", "nao_comparavel", "nao_conclusivo"]:
        with pytest.raises(ValueError, match="nao autoriza mexer no framework"):
            PROTO.fechar_divergencia(v, "NBR 8800 §5.4.3", mudou_framework=True)

    # concordar com fonte nunca é justificativa: veredito hipotese_divergente + mudou=True deve falhar
    with pytest.raises(ValueError):
        PROTO.fechar_divergencia("hipotese_divergente", "qualquer citacao", mudou_framework=True)

    # sem mudar framework, qualquer veredito é permitido (não mexe)
    for v in PROTO.VEREDITOS:
        PROTO.fechar_divergencia(v, "", mudou_framework=False)  # não deve lançar
        PROTO.fechar_divergencia(v, "NBR 8800 §", mudou_framework=False)

    # veredito inválido deve falhar mesmo sem mudar
    with pytest.raises(ValueError, match="fora do enum"):
        PROTO.fechar_divergencia("invalido", "", mudou_framework=False)


# ---------------------------------------------------------------------------
# Guarda contra fabricação — pagina + trecho_literal
# ---------------------------------------------------------------------------
def test_g24_valor_sem_pagina_reprova():
    # valor sem pagina deve reprovar
    erros = PROTO.validar_valor_com_procedencia("Mcol_kNm", {"valor": 235.9, "trecho_literal": "Momento 235,9 kNm p.42"})
    assert any("pagina" in e for e in erros), f"deveria reprovar sem pagina, veio {erros}"

    # valor sem trecho_literal deve reprovar
    erros = PROTO.validar_valor_com_procedencia("peso_kg", {"valor": 23206, "pagina": 42})
    assert any("trecho_literal" in e for e in erros)

    # valor sem ambos reprova
    erros = PROTO.validar_valor_com_procedencia("Mcol", {"valor": 1.0})
    assert len(erros) >= 2

    # página zero ou negativa reprova
    erros = PROTO.validar_valor_com_procedencia("Mcol", {"valor": 1.0, "pagina": 0, "trecho_literal": "trecho com mais de dez chars aqui"})
    assert any("pagina" in e for e in erros)

    # trecho muito curto reprova (<10 chars)
    erros = PROTO.validar_valor_com_procedencia("Mcol", {"valor": 1.0, "pagina": 1, "trecho_literal": "curto"})
    assert any("trecho_literal" in e for e in erros)


def test_g24_valor_sem_procedencia_reprova_em_fixture():
    fixture_sem = {
        "_aviso": PROTO.ROTULO_CONCORDANCIA,
        "fonte_id": f"teste-g24-sem-pagina{PROTO.SUFIXO_DIRETORIO}",
        "valores": {
            "Mcol_kNm": {"valor": 235.9}  # sem pagina/trecho
        }
    }
    erros = PROTO.validar_fixture(fixture_sem)
    assert any("pagina" in e or "trecho_literal" in e for e in erros), f"fixture sem procedencia deveria reprovar, veio {erros}"


def test_g24_valor_com_procedencia_passa():
    erros = PROTO.validar_valor_com_procedencia("Mcol_kNm", {
        "valor": 235.9,
        "pagina": 42,
        "trecho_literal": "Momento fletor máximo no topo do pilar: 235,9 kNm (Tab. 4.2, p.42)",
    })
    assert not erros, f"valor com procedencia deveria passar, veio {erros}"


def test_g24_fixture_com_procedencia_passa():
    fixture_ok = {
        "_aviso": PROTO.ROTULO_CONCORDANCIA,
        "fonte_id": f"exemplo-tcc{PROTO.SUFIXO_DIRETORIO}",
        "valores": {
            "Mcol_kNm": {"valor": 235.9, "pagina": 42, "trecho_literal": "Momento fletor 235,9 kNm na pagina 42, tabela 4.2 do TCC"},
            "peso_kg": {"valor": 23206, "pagina": 10, "trecho_literal": "Peso de aco primario 23206 kg na pagina 10 do memorial"},
        }
    }
    erros = PROTO.validar_fixture(fixture_ok)
    assert not erros, f"fixture valido deveria passar, veio {erros}"


def test_g24_fixture_exemplo_tem_procedencia():
    # G35: o fixture-exemplo sintetico mora em tests/fixtures (nao e fonte real)
    exemplo = REPO / "tests" / "fixtures" / "fonte_exemplo_sintetica" / f"tcc-exemplo-ufmg-2023-galpao-24x36{PROTO.SUFIXO_DIRETORIO}" / "fixture.json"
    assert exemplo.is_file(), f"fixture exemplo não encontrado: {exemplo}"
    data = json.loads(exemplo.read_text(encoding="utf-8"))
    erros = PROTO.validar_fixture(data)
    assert not erros, f"fixture exemplo deveria passar, veio {erros}"


def test_g35_registro_sem_entrada_sintetica_example_com():
    # G35: a entrada sintetica do example.com saiu do registro — registro so tem fontes reais
    data = json.loads(REGISTRO.read_text(encoding="utf-8"))
    for entry in data["fontes"]:
        assert "example.com" not in entry.get("url", ""), f"registro ainda contem URL sintetica: {entry['id']}"
        assert "tcc-exemplo-ufmg" not in entry.get("id", ""), f"registro ainda contem entrada sintetica: {entry['id']}"
    assert len(data["fontes"]) == 3, f"registro deve ter as 3 fontes reais, veio {len(data['fontes'])}"
    # a entrada removida esta preservada como auditoria em tests/fixtures
    entry_path = REPO / "tests" / "fixtures" / "fonte_exemplo_sintetica" / "registro_entry.json"
    assert entry_path.is_file(), f"entrada sintetica preservada ausente: {entry_path}"
    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    assert "example.com" in entry["url"]


# ---------------------------------------------------------------------------
# Rótulo em 4 lugares
# ---------------------------------------------------------------------------
def test_g24_rotulo_quatro_lugares():
    # 1) nome do diretório — G35: usa fonte REAL (o exemplo sintetico mudou para tests/fixtures)
    exemplo_dir = REPO / "fontes_externas" / f"tcc-ufpe-galpao-44x90{PROTO.SUFIXO_DIRETORIO}"
    assert exemplo_dir.is_dir(), f"diretório exemplo não existe: {exemplo_dir}"
    assert PROTO.SUFIXO_DIRETORIO in exemplo_dir.name

    # 2) JSON (registro.json e fixture.json e comparacao.json)
    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
    assert PROTO.ROTULO_CONCORDANCIA in registro["_aviso"]
    assert "_rotulo_quatro_lugares" in registro

    fixture = json.loads((exemplo_dir / "fixture.json").read_text(encoding="utf-8"))
    assert PROTO.ROTULO_CONCORDANCIA in fixture["_aviso"]

    comparacao = json.loads((exemplo_dir / "comparacao.json").read_text(encoding="utf-8"))
    assert PROTO.ROTULO_CONCORDANCIA in comparacao["_aviso"]

    fonte = json.loads((exemplo_dir / "fonte.json").read_text(encoding="utf-8"))
    assert PROTO.ROTULO_CONCORDANCIA in fonte["rotulo"]

    # 3) README (principal + por obra)
    readme_text = README.read_text(encoding="utf-8")
    assert PROTO.ROTULO_CONCORDANCIA in readme_text
    assert "quatro lugares" in readme_text.lower()
    assert "nome do diretório" in readme_text.lower()
    assert "relatório" in readme_text.lower()
    # README por obra (quarto lugar per-obra)
    readme_obra = exemplo_dir / "README.md"
    assert readme_obra.is_file(), f"README por obra ausente: {readme_obra}"
    assert PROTO.ROTULO_CONCORDANCIA in readme_obra.read_text(encoding="utf-8")

    # 4) relatório
    relatorio = exemplo_dir / "relatorio.txt"
    assert relatorio.is_file()
    rel_text = relatorio.read_text(encoding="utf-8")
    assert PROTO.ROTULO_CONCORDANCIA in rel_text
    # relatório não deve conter "validado contra obra real"
    assert "validado contra obra real" not in rel_text.lower() or "nao afirmar" in rel_text.lower() or "nao e obra" in rel_text.lower()
    # deve conter cabeçalho de concordância
    assert "CONCORDANCIA ENTRE CALCULISTAS" in rel_text


def test_g24_registro_nao_diz_validado_contra_obra_real():
    # guarda semântica: nenhum arquivo em fontes_externas deve afirmar validação contra obra real sem negação
    for path in REPO.rglob("fontes_externas/**/*"):
        if path.is_file() and path.suffix in (".json", ".md", ".txt"):
            txt = path.read_text(encoding="utf-8", errors="ignore").lower()
            # se mencionar "validado contra obra real" sem "nao" por perto, falha
            if "validado contra obra real" in txt:
                # deve estar acompanhado de negação / aviso
                assert "nao" in txt or "não" in txt or "concordancia" in txt, f"{path} afirma 'validado contra obra real' sem negação"


# ---------------------------------------------------------------------------
# Extrator roda por URL e grava procedência
# ---------------------------------------------------------------------------
def test_g24_extrator_roda_por_url_e_grava_procedencia(tmp_path):
    # cria PDF temporário mínimo
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
    # calcula hash esperado
    import hashlib
    sha_expected = hashlib.sha256(pdf_bytes).hexdigest()
    pdf_path = tmp_path / "teste_g24.pdf"
    pdf_path.write_bytes(pdf_bytes)

    # roda extrator via file:// URL com id temporário
    id_teste = "teste-extrator-g24-tmp"
    # garante que não existe antes
    obra_dir = REPO / "fontes_externas" / f"{id_teste}{PROTO.SUFIXO_DIRETORIO}"
    if obra_dir.exists():
        shutil.rmtree(obra_dir)

    # chama extrator como subprocesso (testa CLI real)
    # usa file:// URL absoluta
    url = f"file://{pdf_path.as_posix()}"
    cmd = [
        sys.executable, "tools/extrai_fonte_externa.py",
        "--url", url,
        "--autor", "Teste Automatizado - G24",
        "--classe", "tcc_academico",
        "--id", id_teste,
        "--titulo", "Teste Extrator G24 - PDF temporario",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO), timeout=30)
    assert res.returncode == 0, f"extrator falhou: stdout={res.stdout}\nstderr={res.stderr}"

    try:
        # verifica registro
        registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
        entry = next((e for e in registro["fontes"] if e["id"] == f"{id_teste}{PROTO.SUFIXO_DIRETORIO}"), None)
        assert entry is not None, f"entrada {id_teste} não encontrada no registro após extração"
        assert entry["sha256"] == sha_expected, f"sha mismatch: {entry['sha256']} vs {sha_expected}"
        assert entry["url"] == url
        assert entry["classe_autoridade"] == "tcc_academico"
        assert PROTO.ROTULO_CONCORDANCIA in entry["rotulo"]

        # verifica fonte.json
        fonte_path = obra_dir / "fonte.json"
        assert fonte_path.is_file()
        fonte = json.loads(fonte_path.read_text(encoding="utf-8"))
        assert fonte["sha256"] == sha_expected
        assert PROTO.ROTULO_CONCORDANCIA in fonte["_aviso"]

        # verifica fixture.json esqueleto tem pagina+trecho como null (BLOQUEADO até preencher, mas estrutura existe)
        fixture_path = obra_dir / "fixture.json"
        assert fixture_path.is_file()
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        assert PROTO.ROTULO_CONCORDANCIA in fixture["_aviso"]
        assert "valores" in fixture
        # esqueleto deve ter pagina = null para forçar preenchimento
        for nome, v in fixture["valores"].items():
            assert "pagina" in v and "trecho_literal" in v, f"{nome} sem pagina/trecho no esqueleto"

        # valida que fixture esqueleto (com null) reprova - guarda funciona
        erros = PROTO.validar_fixture(fixture)
        assert any("pagina" in e or "trecho_literal" in e for e in erros), "fixture esqueleto deveria reprovar até preencher pagina+trecho"

        # verifica comparacao.json esqueleto com veredito fechado
        comp_path = obra_dir / "comparacao.json"
        assert comp_path.is_file()
        comp = json.loads(comp_path.read_text(encoding="utf-8"))
        assert comp["veredito"] in PROTO.VEREDITOS
        assert PROTO.ROTULO_CONCORDANCIA in comp["_aviso"]

        # verifica README por obra (4o lugar)
        readme_obra = obra_dir / "README.md"
        assert readme_obra.is_file(), f"README por obra não criado pelo extrator: {readme_obra}"
        assert PROTO.ROTULO_CONCORDANCIA in readme_obra.read_text(encoding="utf-8")

        # G30: --check agora deve FALHAR para file:// (guarda https)
        # file:// é recusado para fonte externa, mesmo que hash bata
        ok_url, msg_url = PROTO.validar_url(entry["url"])
        assert not ok_url and "file://" in msg_url, f"G30: file:// deveria ser recusado, veio ok={ok_url} msg={msg_url}"
        # guarda completa deve falhar (file:// + fixture esqueleto)
        # Forca fixture com pagina 1 para testar guarda completa: cria fixture minima valida
        # mas ainda com file:// deve falhar
        erros_completa = PROTO.validar_fonte_externa_completa(entry, None, REPO)
        assert any("file://" in e for e in erros_completa), f"G30 guarda completa deveria falhar por file://, veio {erros_completa}"
        cmd_check = [sys.executable, "tools/extrai_fonte_externa.py", "--check", "--id", id_teste]
        res2 = subprocess.run(cmd_check, capture_output=True, text=True, cwd=str(REPO), timeout=15)
        # G30: check deve agora reportar falha de URL (file://)
        assert res2.returncode != 0, f"G30: check com file:// deveria falhar, mas retornou 0: {res2.stdout} {res2.stderr}"
        assert "file://" in res2.stdout.lower() or "file://" in res2.stderr.lower() or "recusado" in res2.stdout.lower() or "recusado" in res2.stderr.lower(), f"check deveria mencionar file:// recusado: {res2.stdout} {res2.stderr}"

    finally:
        # cleanup: remover entrada do registro e diretório criado
        try:
            registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
            registro["fontes"] = [e for e in registro["fontes"] if e["id"] != f"{id_teste}{PROTO.SUFIXO_DIRETORIO}"]
            REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass
        if obra_dir.exists():
            shutil.rmtree(obra_dir, ignore_errors=True)


def test_g24_extrator_pdf_local_flag(tmp_path):
    # testa --pdf-local como alternativa a --url
    pdf_bytes = b"%PDF-1.4 teste pdf-local\n%%EOF\n"
    pdf_path = tmp_path / "local.pdf"
    pdf_path.write_bytes(pdf_bytes)
    id_teste = "teste-pdf-local-g24-tmp"
    obra_dir = REPO / "fontes_externas" / f"{id_teste}{PROTO.SUFIXO_DIRETORIO}"
    if obra_dir.exists():
        shutil.rmtree(obra_dir)
    cmd = [
        sys.executable, "tools/extrai_fonte_externa.py",
        "--pdf-local", str(pdf_path),
        "--autor", "Teste PDF Local",
        "--classe", "livro_exemplo_resolvido",
        "--id", id_teste,
        "--titulo", "Teste PDF Local G24",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO), timeout=15)
    assert res.returncode == 0, f"extrator --pdf-local falhou: {res.stdout} {res.stderr}"
    try:
        assert obra_dir.is_dir()
        assert (obra_dir / "original.pdf").is_file()
        assert (obra_dir / "README.md").is_file()
        assert PROTO.ROTULO_CONCORDANCIA in (obra_dir / "README.md").read_text(encoding="utf-8")
        # G30: pdf-local gera file:// que agora é recusado para fonte externa
        registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
        entry = next((e for e in registro["fontes"] if e["id"] == f"{id_teste}{PROTO.SUFIXO_DIRETORIO}"), None)
        assert entry is not None
        ok_url, _ = PROTO.validar_url(entry["url"])
        assert not ok_url, "G30: file:// de --pdf-local deveria ser recusado"
    finally:
        # cleanup
        try:
            registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
            registro["fontes"] = [e for e in registro["fontes"] if e["id"] != f"{id_teste}{PROTO.SUFIXO_DIRETORIO}"]
            REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass
        if obra_dir.exists():
            shutil.rmtree(obra_dir, ignore_errors=True)


def test_g24_comparacao_valida_enums():
    # comparacao com veredito fora do enum deve reprovar
    comp_bad = {
        "_aviso": PROTO.ROTULO_CONCORDANCIA,
        "veredito": "invento",
        "mudou_framework": False,
        "citacao_normativa": "",
    }
    erros = PROTO.validar_comparacao(comp_bad)
    assert any("fora do enum" in e for e in erros)

    # comparacao framework_errado sem citacao + mudou=True deve reprovar
    comp_bad2 = {
        "_aviso": PROTO.ROTULO_CONCORDANCIA,
        "veredito": "framework_errado",
        "mudou_framework": True,
        "citacao_normativa": "",
    }
    erros = PROTO.validar_comparacao(comp_bad2)
    assert any("citacao_normativa" in e for e in erros)

    # comparacao ok
    comp_ok = {
        "_aviso": PROTO.ROTULO_CONCORDANCIA,
        "veredito": "hipotese_divergente",
        "mudou_framework": False,
        "citacao_normativa": "",
    }
    assert not PROTO.validar_comparacao(comp_ok)


def test_g24_assert_registro_existe():
    # deve retornar caminho se existir
    p = PROTO.assert_registro_existe(REPO)
    assert p == REGISTRO
    # deve lançar se não existir (testa com tmp)
    with tempfile.TemporaryDirectory() as td:
        with pytest.raises(FileNotFoundError, match="Protocolo G24 ausente"):
            PROTO.assert_registro_existe(pathlib.Path(td))
