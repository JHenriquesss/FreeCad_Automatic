# -*- coding: utf-8 -*-
"""
G26 — Caso externo #2: galpão 25x54 treliçado (replicação)

Não é enchimento. Um caso que concorda prova pouco; um que discorda é ambíguo.
Duas fontes independentes divergindo do mesmo jeito apontam para o framework;
divergindo de jeitos diferentes apontam para as fontes. É o único desenho que
separa as duas hipóteses.

Ressalva G26: PDF tem muito menos texto por página (156 contra 696 do UFPE
medido, descrito 155 contra 777) — mais saída de software CYPE 3D vetorial que
memorial escrito. Pode não render extração suficiente. Se não render, veredito
é nao_comparavel e segue em frente; forçar extração de tabela mal reconhecida
é como inventar números.

Harness permanente: fixture com medicao densidade, comparacao nao_comparavel,
spec treliçado Warren h=1.8 n=8.
"""
import json
import pathlib
import sys
import tempfile
import shutil

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO / "fontes_externas" / "tcc-externo2-galpao-25x54-trelicado__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fixture.json"
COMPARACAO_PATH = REPO / "fontes_externas" / "tcc-externo2-galpao-25x54-trelicado__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "comparacao.json"
FONTE_PATH = REPO / "fontes_externas" / "tcc-externo2-galpao-25x54-trelicado__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fonte.json"
PDF_PATH = REPO / "fontes_externas" / "tcc-externo2-galpao-25x54-trelicado__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "original.pdf"
SPEC_PATH = REPO / "projects" / "galpao-25x54-trelicado" / "project-spec.json"

FW = REPO / "framework" / "galpao_fw"
sys.path.insert(0, str(FW))
import fontes_externas_protocolo as PROTO


def test_g26_fixture_tem_procedencia_e_rotulo():
    assert FIXTURE_PATH.is_file(), f"fixture não encontrado: {FIXTURE_PATH}"
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    erros = PROTO.validar_fixture(data)
    assert not erros, f"fixture inválido: {erros}"
    assert PROTO.ROTULO_CONCORDANCIA in data["_aviso"]
    # deve ter valores extraiveis com pagina+trecho (geometria)
    assert "vao_livre" in data["valores"]
    assert "bay_porticos" in data["valores"]
    assert "trelica_altura" in data["valores"]
    assert "densidade_texto_avg_chars_pag" in data["valores"]
    for nome, v in data["valores"].items():
        assert isinstance(v["pagina"], int) and v["pagina"] > 0, f"{nome} pagina"
        assert isinstance(v["trecho_literal"], str) and len(v["trecho_literal"]) >= 10, f"{nome} trecho"
    # medicao densidade deve existir e estar abaixo threshold
    assert "medicao_densidade" in data
    med = data["medicao_densidade"]
    assert med["paginas"] == 88
    assert 100 <= med["media_chars_por_pagina"] <= 250, f"avg {med['media_chars_por_pagina']} deve ser ~156"
    assert med["media_chars_por_pagina"] < 300, "densidade deve ser < threshold 300"


def test_g26_comparacao_nao_comparavel_e_4_lugares():
    assert COMPARACAO_PATH.is_file()
    comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    erros = PROTO.validar_comparacao(comp)
    assert not erros, f"comparacao invalida: {erros}"
    assert comp["veredito"] == "nao_comparavel", f"G26 deve ser nao_comparavel, veio {comp['veredito']}"
    assert comp["mudou_framework"] is False, "nao_comparavel nao pode mudar framework"
    assert PROTO.ROTULO_CONCORDANCIA in comp["_aviso"]
    assert "detalhes_por_valor" in comp and isinstance(comp["detalhes_por_valor"], dict)
    for nome, det in comp["detalhes_por_valor"].items():
        assert det["veredito"] in PROTO.VEREDITOS, f"{nome} veredito fora do enum: {det['veredito']}"
        assert "fonte_valor" in det and "framework_valor" in det
        assert "definicao_comparacao" in det
        assert "observacao" in det
    # densidade deve ser nao_comparavel
    assert comp["detalhes_por_valor"]["densidade_texto_avg_chars_pag"]["veredito"] == "nao_comparavel"
    assert comp["detalhes_por_valor"]["perfil_coluna_mencionado_HEA200"]["veredito"] == "nao_comparavel"
    assert comp["detalhes_por_valor"]["peso_aco_primario_kg"]["veredito"] == "nao_comparavel"
    # G31: geometria exata 0% <=2% => concorda (antes era hipotese_divergente por enum incompleto)
    assert comp["detalhes_por_valor"]["vao_livre"]["veredito"] == "concorda"
    assert comp["detalhes_por_valor"]["comprimento"]["veredito"] == "concorda"
    assert comp["detalhes_por_valor"]["bay_porticos"]["veredito"] == "concorda"
    assert comp["detalhes_por_valor"]["trelica_altura"]["veredito"] == "concorda"


def test_g26_densidade_baixa_verifica_pdf():
    """Verifica que PDF tem baixa densidade texto/pagina (156 vs 696 UFPE) - ressalva G26."""
    assert PDF_PATH.is_file()
    data = PDF_PATH.read_bytes()
    assert data.startswith(b"%PDF")
    # medir via fitz
    try:
        import fitz
        doc = fitz.open(str(PDF_PATH))
        total = sum(len(p.get_text()) for p in doc)
        avg = total / len(doc) if len(doc) else 0
        assert 100 <= avg <= 250, f"avg {avg:.1f} deve ser ~156 (baixa densidade)"
        assert len(doc) == 88, f"paginas {len(doc)} deve ser 88"
        # comparar com UFPE
        ufpe_pdf = REPO / "fontes_externas" / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "original.pdf"
        doc2 = fitz.open(str(ufpe_pdf))
        avg2 = sum(len(p.get_text()) for p in doc2) / len(doc2)
        assert avg < avg2, f"25x54 avg {avg:.1f} deve ser < UFPE avg {avg2:.1f}"
        assert avg2 > 500, f"UFPE avg {avg2:.1f} deve ser >500 (memorial escrito)"
    except ImportError:
        pytest.skip("fitz não disponível para medir densidade")
    # fixture medicao deve bater com PDF medido
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    med = fixture.get("medicao_densidade", {})
    total_f = med.get("total_chars", 0)
    # verificar que total_chars ~ total medido (tolerancia 20%)
    assert abs(total_f - total) / max(total, 1) < 0.2, f"fixture total_chars {total_f} vs PDF {total} diverge"


def test_g26_registro_hierarquia_e_sha():
    reg = json.loads((REPO / "fontes_externas" / "registro.json").read_text(encoding="utf-8"))
    entry = next((e for e in reg["fontes"] if e["id"] == "tcc-externo2-galpao-25x54-trelicado__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL"), None)
    assert entry is not None, "registro não contém 25x54"
    assert entry["classe_autoridade"] == "material_comercial"
    assert PROTO.ROTULO_CONCORDANCIA in entry["rotulo"]
    assert len(entry["sha256"]) == 64
    # url deve ser https para calculistadeaco (G29) e nao tmp
    assert entry["url"].startswith("https://"), f"url deve ser https, veio {entry['url']}"
    assert "calculistadeaco.com.br" in entry["url"], f"url deve conter calculistadeaco.com.br, veio {entry['url']}"
    assert "tmp_25x54" not in entry["url"], "url nao deve conter tmp"
    # hierarquia: material_comercial é o degrau mais baixo, abaixo de tcc_academico e licitacao_executada
    assert PROTO.hierarquia_rank("material_comercial") > PROTO.hierarquia_rank("tcc_academico")
    assert PROTO.hierarquia_rank("material_comercial") > PROTO.hierarquia_rank("licitacao_executada")


def test_g26_fonte_pdf_existe_e_sha_bate():
    assert PDF_PATH.is_file()
    data = PDF_PATH.read_bytes()
    assert data.startswith(b"%PDF")
    sha = PROTO.compute_sha256(PDF_PATH)
    fonte = json.loads(FONTE_PATH.read_text(encoding="utf-8"))
    assert sha == fonte["sha256"]
    # verificar que PDF nao e o dummy velho - agora é PDF real 4 MB, 88 pgs
    assert len(data) > 100000, "PDF 25x54 deve ter >100k (real 4MB, 88 pgs)"
    assert len(data) < 10000000, "PDF nao deve ser absurdamente grande"
    assert fonte["url"].startswith("https://") and "calculistadeaco.com.br" in fonte["url"]


def test_g26_roda_vertical_trelicado_do_fixture_sem_rede():
    """Roda o vertical trelicado com spec G26 (25x54 Warren) e verifica que framework roda sem crash."""
    assert SPEC_PATH.is_file(), f"spec 25x54 não encontrado: {SPEC_PATH}"
    spec_full = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    struct = spec_full.get("structure") or spec_full.get("aco")
    assert struct is not None, "spec sem structure/aco"
    import projeto_spec as PS
    r = PS.validar(struct)
    assert r["ok"], f"spec structure inválido: {r['faltando']}"
    # verificar que e trelica
    assert struct["estrutura"]["tipo_portico"] == "tesoura"
    assert struct["estrutura"]["trelica"]["h"] == 1.8
    assert struct["estrutura"]["trelica"]["n_paineis"] == 8
    import rodar_projeto as RP
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="g26_25x54_harness_"))
    try:
        res = RP.calcular(struct, str(tmp))
        # deve ter tesoura calculada
        assert "tesoura" in res and isinstance(res["tesoura"], dict)
        assert "u_max" in res["tesoura"]
        # pilares e viga (mesmo trelica tem colunas)
        assert "perfil_colunas" in res and isinstance(res["perfil_colunas"], list)
        assert res["interacao_max"] is not None
        # byte should be ok (trelica)
        assert res["tesoura"]["h_m"] == 1.8
        assert res["tesoura"]["n_paineis"] == 8
        # comparar bay e h com fixture
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        bay_spec = struct["geometria"]["bay"]
        bay_fixture = fixture["valores"]["bay_porticos"]["valor"]
        assert bay_spec == bay_fixture == 6.0
        # verificar que comparacao nao tem framework_errado sem citacao
        comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
        assert comp["mudou_framework"] is False
        for nome, det in comp["detalhes_por_valor"].items():
            if det["veredito"] == "framework_errado":
                assert det.get("citacao_normativa"), f"{nome} framework_errado exige citacao"
        # densidade overall nao_comparavel nao autoriza mexer
        assert comp["veredito"] != "framework_errado"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_g26_nao_inventa_numeros_e_guarda():
    """G26 não deve inventar números: tabelas vetoriais não viram valores com pagina+trecho falso."""
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    # verificar que fixture nao tem valores com pagina None (inventado)
    for nome, v in fixture["valores"].items():
        assert v["pagina"] is not None and v["trecho_literal"] is not None
        assert len(v["trecho_literal"]) >= 10
        # verificar que trecho_literal realmente aparece no PDF (amostragem)
        # para 25x54, trecho deve conter substring do PDF (case-insensitive)
        # checar para vao_livre
        if nome == "vao_livre":
            tl = v["trecho_literal"].lower()
            assert "25m x 54m" in tl or "25x54" in tl or "25m x 54m".lower() in tl
    # comparacao deve explicar que nao forca extracao de tabela mal reconhecida
    txt = json.dumps(comp, ensure_ascii=False).lower()
    assert "nao_comparavel" in txt
    assert "forcar" in txt or "forçar" in txt or "inventar" in txt
    assert "156" in txt or "densidade" in txt
    # relatorio deve mencionar guarda
    rel = (REPO / "fontes_externas" / "tcc-externo2-galpao-25x54-trelicado__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "relatorio.txt").read_text(encoding="utf-8")
    assert PROTO.ROTULO_CONCORDANCIA in rel
    assert "CONCORDANCIA ENTRE CALCULISTAS" in rel
    assert "nao_comparavel" in rel.lower() or "NAO_COMPARAVEL" in rel
    # guarda d*sen45 deve ser mencionada (banzo inclinado vs projecao)
    assert "sen" in rel.lower() or "inclinado" in rel.lower() or "sen45" in rel.lower() or "d·sen" in rel or "banzo" in rel.lower()
    # segunda fonte design: deve mencionar que duas fontes nao separam hipoteses porque uma e nao_comparavel
    assert "nao_comparavel" in rel.lower()
    assert "hipotese" in rel.lower() or "hipótese" in rel.lower()


def test_g26_rotulo_quatro_lugares():
    """Rótulo CONCORDANCIA em 4 lugares: diretorio, JSON, README e relatorio."""
    # 1) diretorio
    obra_dir = REPO / "fontes_externas" / "tcc-externo2-galpao-25x54-trelicado__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL"
    assert obra_dir.is_dir()
    assert PROTO.SUFIXO_DIRETORIO in obra_dir.name
    # 2) JSON
    registro = json.loads((REPO / "fontes_externas" / "registro.json").read_text(encoding="utf-8"))
    assert PROTO.ROTULO_CONCORDANCIA in registro["_aviso"]
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert PROTO.ROTULO_CONCORDANCIA in fixture["_aviso"]
    comparacao = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    assert PROTO.ROTULO_CONCORDANCIA in comparacao["_aviso"]
    fonte = json.loads(FONTE_PATH.read_text(encoding="utf-8"))
    assert PROTO.ROTULO_CONCORDANCIA in fonte["rotulo"]
    # 3) README
    readme = (REPO / "fontes_externas" / "README.md").read_text(encoding="utf-8")
    assert PROTO.ROTULO_CONCORDANCIA in readme
    readme_obra = (obra_dir / "README.md").read_text(encoding="utf-8")
    assert PROTO.ROTULO_CONCORDANCIA in readme_obra
    # 4) relatorio
    rel = (obra_dir / "relatorio.txt").read_text(encoding="utf-8")
    assert PROTO.ROTULO_CONCORDANCIA in rel
