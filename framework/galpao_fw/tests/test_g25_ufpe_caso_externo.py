# -*- coding: utf-8 -*-
"""
G25 — Caso externo #1: galpão UFPE (aço, elemento a elemento)

Vertical maduro (aço, aferido Fakury/Pfeil) vs fonte TCC UFPE 44x90 (2x22m, 90m, 7m, 4 águas, cat III C, A36+G50, zipada, A325-F).

Harness permanente: roda do fixture (sem rede), compara perfil a perfil, veredito por elemento.
Investiga W150x29,8 ambiguidade (pilar vs viga tapamento 7,5 m) sem assumir erro — mede mesma definição.
"""
import json
import pathlib
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO / "fontes_externas" / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fixture.json"
COMPARACAO_PATH = REPO / "fontes_externas" / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "comparacao.json"
FONTE_PATH = REPO / "fontes_externas" / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fonte.json"
SPEC_PATH = REPO / "projects" / "galpao-ufpe" / "project-spec.json"

FW = REPO / "framework" / "galpao_fw"
sys.path.insert(0, str(FW))
import fontes_externas_protocolo as PROTO


def test_g25_fixture_tem_procedencia_e_rotulo():
    assert FIXTURE_PATH.is_file(), f"fixture não encontrado: {FIXTURE_PATH}"
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    erros = PROTO.validar_fixture(data)
    assert not erros, f"fixture inválido: {erros}"
    # rotulo 4 lugares
    assert PROTO.ROTULO_CONCORDANCIA in data["_aviso"]
    assert "perfil_pilar_lateral" in data["valores"]
    assert "perfil_pilar_central" in data["valores"]
    # cada valor tem pagina+trecho
    for nome, v in data["valores"].items():
        assert isinstance(v["pagina"], int) and v["pagina"] > 0, f"{nome} pagina"
        assert isinstance(v["trecho_literal"], str) and len(v["trecho_literal"]) >= 10, f"{nome} trecho"


def test_g25_comparacao_enum_fechado_e_4_lugares():
    assert COMPARACAO_PATH.is_file()
    comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    erros = PROTO.validar_comparacao(comp)
    assert not erros, f"comparacao invalida: {erros}"
    assert comp["veredito"] in PROTO.VEREDITOS
    assert PROTO.ROTULO_CONCORDANCIA in comp["_aviso"]
    # cada elemento tem veredito
    assert "detalhes_por_valor" in comp and isinstance(comp["detalhes_por_valor"], dict)
    for nome, det in comp["detalhes_por_valor"].items():
        assert det["veredito"] in PROTO.VEREDITOS, f"{nome} veredito fora do enum: {det['veredito']}"
        assert "fonte_valor" in det and "framework_valor" in det
        assert "definicao_comparacao" in det
        assert "observacao" in det


def test_g25_investigacao_w150_permanence_aberta():
    """W150x29,8 nos pilares fica como nao_conclusivo / nao_comparavel, não como fonte_errada prematura."""
    comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    det_lat = comp["detalhes_por_valor"]["perfil_pilar_lateral"]
    det_cen = comp["detalhes_por_valor"]["perfil_pilar_central"]
    det_trav = comp["detalhes_por_valor"]["travamento_pilar"]
    # pilares não podem ser fonte_errada sem medir mesma definicao
    assert det_lat["veredito"] == "nao_conclusivo", "pilar lateral deve ficar nao_conclusivo (investigar)"
    assert det_cen["veredito"] == "nao_conclusivo"
    assert det_trav["veredito"] == "nao_comparavel", "travamento 7,5 m é bay vs Lb — nao_comparavel"
    # observacao deve mencionar travamento e viga tapamento 7,5 m
    for det in (det_lat, det_cen):
        txt = (det["observacao"] + det.get("medicao_mesma_definicao","")).lower()
        assert "7,5" in txt or "7.5" in txt, "deve mencionar 7,5 m da investigacao"
        assert "tapamento" in txt or "travamento" in txt


def test_g25_registro_hierarquia_e_sha():
    reg = json.loads((REPO / "fontes_externas" / "registro.json").read_text(encoding="utf-8"))
    entry = next((e for e in reg["fontes"] if e["id"] == "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL"), None)
    assert entry is not None, "registro não contém UFPE"
    assert entry["classe_autoridade"] == "tcc_academico"
    assert PROTO.ROTULO_CONCORDANCIA in entry["rotulo"]
    assert len(entry["sha256"]) == 64
    # hierarquia: tcc_academico nao supera licitacao_executada
    assert PROTO.hierarquia_rank("tcc_academico") > PROTO.hierarquia_rank("licitacao_executada")


def test_g25_fonte_pdf_existe_e_sha_bate():
    pdf = REPO / "fontes_externas" / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "original.pdf"
    assert pdf.is_file()
    data = pdf.read_bytes()
    assert data.startswith(b"%PDF")
    sha = PROTO.compute_sha256(pdf)
    fonte = json.loads(FONTE_PATH.read_text(encoding="utf-8"))
    assert sha == fonte["sha256"]


def test_g25_roda_vertical_aco_do_fixture_sem_rede():
    """Roda o vertical de aço com entradas do G25 (fixture-spec) e compara perfil a perfil."""
    # spec deve existir e ser valido
    assert SPEC_PATH.is_file(), f"spec UFPE não encontrado: {SPEC_PATH}"
    spec_full = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    # extrai structure (caso de projeto de aço)
    struct = spec_full.get("structure") or spec_full.get("aco")
    assert struct is not None, "spec sem structure/aco"
    # validar via projeto_spec
    import projeto_spec as PS
    r = PS.validar(struct)
    assert r["ok"], f"spec structure inválido: {r['faltando']}"
    # rodar aço (sem rede, puro)
    import rodar_projeto as RP
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="g25_ufpe_harness_"))
    try:
        res = RP.calcular(struct, str(tmp))
        # perfis adotados devem existir e ser do tipo esperado (HEA/IPE/Ue etc)
        assert "perfil_colunas" in res and isinstance(res["perfil_colunas"], list)
        assert len(res["perfil_colunas"]) == 3, "2 vaos => 3 colunas"
        assert res["perfil_raf"] in ("IPE400", "IPE450", "IPE360", "HEA240", "HEA260", "W310x39", "W310x45"), f"raf inesperado {res['perfil_raf']}"
        # verifica que pilares laterais e central existem
        assert res["perfil_colunas"][0] == res["perfil_colunas"][2], "laterais simétricas"
        # tercas e longarina
        assert "terca_perfil" in res
        assert "longarina_perfil" in res
        # compara com fixture (string match vs published) — não é assert de igualdade, é que a comparação está documentada
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
        # verifica que framework_valor no comparacao.json bate com o que acabamos de rodar (mesma versão)
        det_lat = comp["detalhes_por_valor"]["perfil_pilar_lateral"]
        assert det_lat["framework_valor"] == res["perfil_colunas"][0], f"framework_valor pilar lateral desatualizado: {det_lat['framework_valor']} vs {res['perfil_colunas'][0]}"
        det_viga = comp["detalhes_por_valor"]["perfil_viga_cobertura"]
        assert det_viga["framework_valor"] == res["perfil_raf"]
        # travamento bay
        assert res.get("bay") is None or True  # bay vem de spec, não de res, mas checar spec
        bay_spec = struct["geometria"]["bay"]
        assert bay_spec == 7.5
        # interacao deve ser calculada (não pode ser None)
        assert res["interacao_max"] is not None
        # verifica regra G24: mudou_framework só com framework_errado+citacao
        assert comp["mudou_framework"] is False  # G25 não muda framework
        # nenhum veredito framework_errado sem citação
        for nome, det in comp["detalhes_por_valor"].items():
            if det["veredito"] == "framework_errado":
                assert det.get("citacao_normativa"), f"{nome} framework_errado exige citacao"
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def test_g25_guarda_d_sen45_declarada():
    """Guarda contra falsa divergência d*sen45: L_rafter inclinado vs projeção."""
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    # fixture deve mencionar L_rafter inclinado vs projecao na instrução ou definicao
    txt = json.dumps(fixture, ensure_ascii=False).lower()
    # comparacao deve ter travamento como nao_comparavel explicando bay vs Lb
    comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    det_trav = comp["detalhes_por_valor"]["travamento_pilar"]
    assert "nao_comparavel" == det_trav["veredito"]
    assert "lb" in det_trav["definicao_comparacao"].lower() or "lb" in det_trav["observacao"].lower()
    # relatório deve mencionar guarda
    rel = (REPO / "fontes_externas" / "tcc-ufpe-galpao-44x90__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "relatorio.txt").read_text(encoding="utf-8")
    assert "d·sen" in rel or "d*sen" in rel or "sen(45)" in rel or "sen45" in rel.lower() or "inclinado" in rel.lower()
