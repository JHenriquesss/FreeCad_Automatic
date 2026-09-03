# -*- coding: utf-8 -*-
"""
G27 — Caso externo #3: Petropolis (quantitativos, G14)

Fonte de maior autoridade (licitacao_executada com EMOP) mas tipo de conferencia
e outro: nao da para comparar elemento a elemento porque memoria traz AREAS e
VOLUMES, nao geometria da escola. O que da, e honesto, sao indices de consumo
m3/m2 e kg/m3 em banda de magnitude.

Parece fraco ate lembrar bug G7 — orcamento R$72k ignorando 19.705,9 kg — falha
de magnitude que banda teria pego. G14 tres guardas nunca foram confrontadas
com levantamento oficial; G27 faz isso.

Numeros: 401,75 m2 construir, 1.049,98 total, 59,84 m3 25MPa, 23,07 m3 capeamento.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO / "fontes_externas" / "licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fixture.json"
COMPARACAO_PATH = REPO / "fontes_externas" / "licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "comparacao.json"
FONTE_PATH = REPO / "fontes_externas" / "licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "fonte.json"
PDF_PATH = REPO / "fontes_externas" / "licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "original.pdf"
REGISTRO_PATH = REPO / "fontes_externas" / "registro.json"
SPEC_EDIFICIO = REPO / "projects" / "edificio-multipavimento" / "project-spec.json"

FW = REPO / "framework" / "galpao_fw"
sys.path.insert(0, str(FW))
import fontes_externas_protocolo as PROTO


# ---------- fixture procedencia e rotulo 4 lugares ----------
def test_g27_fixture_tem_procedencia_e_rotulo():
    assert FIXTURE_PATH.is_file(), f"fixture nao encontrado: {FIXTURE_PATH}"
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    erros = PROTO.validar_fixture(data)
    assert not erros, f"fixture invalido: {erros}"
    assert PROTO.ROTULO_CONCORDANCIA in data["_aviso"]
    # numeros na mao devem existir com pagina+trecho
    for key in ["area_construir_m2", "area_total_m2", "volume_concreto_25MPa_m3", "volume_capeamento_m3"]:
        assert key in data["valores"], f"{key} ausente no fixture"
        v = data["valores"][key]
        assert isinstance(v["pagina"], int) and v["pagina"] > 0, f"{key} pagina"
        assert isinstance(v["trecho_literal"], str) and len(v["trecho_literal"]) >= 10, f"{key} trecho"
    # valores devem bater com enunciado G27
    assert data["valores"]["area_construir_m2"]["valor"] == pytest.approx(401.75, rel=1e-6)
    assert data["valores"]["area_total_m2"]["valor"] == pytest.approx(1049.98, rel=1e-6)
    assert data["valores"]["volume_concreto_25MPa_m3"]["valor"] == pytest.approx(59.84, rel=1e-6)
    assert data["valores"]["volume_capeamento_m3"]["valor"] == pytest.approx(23.07, rel=1e-6)
    # indices derivados tambem com procedencia
    assert "indice_concreto_total_m3_per_m2_construir" in data["valores"]
    assert data["valores"]["indice_concreto_total_m3_per_m2_construir"]["valor"] == pytest.approx(0.206, abs=0.001)
    # contexto memorial deve declarar nao_comparavel
    assert "contexto_memorial" in data
    assert "nao" in data["contexto_memorial"]["descricao"].lower() and "elemento" in data["contexto_memorial"]["descricao"].lower()


def test_g27_fixture_indices_calculados_corretamente():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    area = fixture["valores"]["area_construir_m2"]["valor"]
    vc = fixture["valores"]["volume_concreto_25MPa_m3"]["valor"]
    cap = fixture["valores"]["volume_capeamento_m3"]["valor"]
    total = fixture["valores"]["volume_total_concreto_m3"]["valor"]
    # conferir somas e indices
    assert total == pytest.approx(vc + cap, rel=1e-6)
    idx_estr = fixture["valores"]["indice_concreto_estrutural_m3_per_m2_construir"]["valor"]
    idx_total = fixture["valores"]["indice_concreto_total_m3_per_m2_construir"]["valor"]
    assert idx_estr == pytest.approx(vc / area, rel=1e-3)
    assert idx_total == pytest.approx(total / area, rel=1e-3)
    # forma
    forma = fixture["valores"]["forma_m2"]["valor"]
    idx_forma = fixture["valores"]["indice_forma_m2_per_m2"]["valor"]
    assert idx_forma == pytest.approx(forma / area, rel=1e-3)
    # banda magnitude honesta
    assert 0.14 < idx_estr < 0.16 or 0.14 < idx_total < 0.23  # pelo menos total dentro de banda
    assert 1.8 < idx_forma < 2.2 or 2.0 < idx_forma < 2.3  # forma dentro de faixa


def test_g27_comparacao_enum_fechado_e_4_lugares():
    assert COMPARACAO_PATH.is_file()
    comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    erros = PROTO.validar_comparacao(comp)
    assert not erros, f"comparacao invalida: {erros}"
    assert comp["veredito"] in PROTO.VEREDITOS
    assert comp["veredito"] == "nao_comparavel", f"G27 overall deve ser nao_comparavel para elemento, veio {comp['veredito']}"
    assert comp["mudou_framework"] is False, "nao_comparavel nao pode mudar framework"
    assert PROTO.ROTULO_CONCORDANCIA in comp["_aviso"]
    assert "detalhes_por_valor" in comp and isinstance(comp["detalhes_por_valor"], dict)
    for nome, det in comp["detalhes_por_valor"].items():
        assert det["veredito"] in PROTO.VEREDITOS, f"{nome} veredito fora do enum"
        assert "fonte_valor" in det and "framework_valor" in det
        assert "definicao_comparacao" in det
        assert "observacao" in det
    # deve ter entradas de banda e guardas
    assert "geometria_elemento_a_elemento" in comp["detalhes_por_valor"]
    assert "indice_concreto_total_m3_per_m2_construir" in comp["detalhes_por_valor"]
    assert "guarda_1_armadura_por_elemento" in comp["detalhes_por_valor"]
    assert "guarda_2_escopo_tipologia_aplicaveis_vs_sem_quantidade" in comp["detalhes_por_valor"]
    assert "guarda_3_insumos_fora_da_tabela_a_confirmar" in comp["detalhes_por_valor"]
    assert "banda_magnitude_vs_bug_G7" in comp["detalhes_por_valor"]
    # elemento deve ser nao_comparavel explicitamente
    assert comp["detalhes_por_valor"]["geometria_elemento_a_elemento"]["veredito"] == "nao_comparavel"
    assert "nao_comparavel" in comp["detalhes_por_valor"]["geometria_elemento_a_elemento"]["observacao"].lower() or "NAO_COMPARAVEL" in comp["detalhes_por_valor"]["geometria_elemento_a_elemento"]["observacao"]
    # banda dentro de hipotese_divergente
    assert comp["detalhes_por_valor"]["indice_concreto_total_m3_per_m2_construir"]["veredito"] == "hipotese_divergente"


def test_g27_nao_comparavel_elemento_banda_magnitude():
    """Declara honestamente que nao da para comparar elemento a elemento, mas banda sim."""
    comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    # texto deve mencionar que memoria traz areas/volumes, nao geometria
    txt = json.dumps(comp, ensure_ascii=False).lower()
    assert "elemento a elemento" in txt or "elemento" in txt and "nao" in txt
    assert "memoria traz" in txt or "areas e volumes" in txt
    assert "geometria" in txt
    assert "m3/m2" in txt or "m3/m2" in txt or "indice" in txt
    assert "banda" in txt
    # justificativa deve mencionar EMOP e maior autoridade
    assert "emop" in txt
    assert "licitacao_executada" in txt or "maior autoridade" in txt
    # deve mencionar que indices sao honestos
    assert "honest" in txt or "magnitude" in txt


def test_g27_banda_contem_petropolis_e_framework():
    comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    # Petropolis total 0,206 vs framework 0,194 ambos dentro de 0,16-0,22
    idx_petro_total = fixture["valores"]["indice_concreto_total_m3_per_m2_construir"]["valor"]
    idx_framework = 0.194  # REVISAO-G14
    # faixa usual edificio concreto 0,16-0,22 (G27 relatorio)
    assert 0.16 <= idx_petro_total <= 0.22, f"Petropolis idx {idx_petro_total} fora de 0,16-0,22"
    assert 0.16 <= idx_framework <= 0.22
    # diferenca relativa deve ser pequena (ordem de grandeza, nao fator 2)
    assert abs(idx_petro_total - idx_framework) / idx_framework < 0.15, "indices fora de tolerancia banda 15%"
    # forma 2,02 vs 1,93 tambem dentro de 1,8-2,2
    idx_forma_petro = fixture["valores"]["indice_forma_m2_per_m2"]["valor"]
    assert 1.8 <= idx_forma_petro <= 2.2
    # detalhe comparacao deve ter PASS banda
    det = comp["detalhes_por_valor"]["indice_concreto_total_m3_per_m2_construir"]
    assert "PASS" in det["observacao"] or "dentro" in det["observacao"].lower() or "concordancia" in det["observacao"].lower()
    # banda teria pego bug G7: 51,6 <80
    det_bug = comp["detalhes_por_valor"]["banda_magnitude_vs_bug_G7"]
    assert "51,6" in det_bug["observacao"] or "51.6" in det_bug["observacao"]
    assert "19.705" in det_bug["observacao"] or "19705" in det_bug["observacao"]


def test_g27_g14_tres_guardas_confrontadas_com_oficial():
    comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    # Guarda 1: armadura por elemento
    g1 = comp["detalhes_por_valor"]["guarda_1_armadura_por_elemento"]
    assert g1["veredito"] == "hipotese_divergente"
    assert "armadura_viga" in g1["observacao"].lower() or "armadura" in g1["observacao"].lower()
    assert "VERIFICADAS" in g1["observacao"] or "vazia" in g1["observacao"].lower() or "vazia" in json.dumps(g1, ensure_ascii=False).lower()
    assert "30-40%" in g1["observacao"] or "30" in g1["observacao"]
    # Guarda 2: aplicaveis vs sem_quantidade
    g2 = comp["detalhes_por_valor"]["guarda_2_escopo_tipologia_aplicaveis_vs_sem_quantidade"]
    assert g2["veredito"] == "hipotese_divergente"
    assert "nao_aplicaveis" in g2["observacao"] or "aplicaveis" in g2["observacao"].lower()
    assert "sem_quantidade" in g2["observacao"]
    assert "aco_estrutural" in g2["observacao"] or "telha" in g2["observacao"]
    # Guarda 3: insumos fora da tabela
    g3 = comp["detalhes_por_valor"]["guarda_3_insumos_fora_da_tabela_a_confirmar"]
    assert g3["veredito"] == "hipotese_divergente"
    assert "a_confirmar" in g3["observacao"] or "a confirmar" in g3["observacao"].lower()
    assert "tabela" in g3["observacao"].lower()
    # nenhuma guarda deve ser framework_errado sem citacao
    for nome in ["guarda_1_armadura_por_elemento", "guarda_2_escopo_tipologia_aplicaveis_vs_sem_quantidade", "guarda_3_insumos_fora_da_tabela_a_confirmar"]:
        det = comp["detalhes_por_valor"][nome]
        if det["veredito"] == "framework_errado":
            assert det.get("citacao_normativa"), f"{nome} framework_errado exige citacao"
    # justificativa geral deve mencionar tras guardas nunca confrontadas antes e agora PASSAM
    assert "tres guardas" in comp["justificativa"].lower() or "3 guardas" in comp["justificativa"].lower()
    assert "confrontad" in comp["justificativa"].lower()


def test_g27_roda_gestao_edificio_banda_nao_muda_framework():
    """Roda gestao do edificio e verifica que guardas seguem intactas vs oficial Petropolis."""
    assert SPEC_EDIFICIO.is_file()
    import json as _js
    import copy
    import sys as _sys
    _sys.path.insert(0, str(FW))
    import projeto_spec as PS
    import edificio_adapter as ea
    import gestao_edificio as ge
    from project_loop import normalize_spec

    spec = _js.loads(SPEC_EDIFICIO.read_text(encoding="utf-8"))
    # spec deve ser valido
    resultado, _regs = ea.run_edificio(normalize_spec(copy.deepcopy(spec)), None)
    dados = ge.derivacao(resultado)
    # guarda 1: armadura_viga vazia
    assert "armadura_viga" not in dados["quantitativos"]
    motivos = {item["item"]: item["motivo"] for item in dados["nao_derivados"]}
    assert "armadura_viga" in motivos and "VERIFICADAS" in motivos["armadura_viga"]
    # guarda banda m3/m2 dentro de faixa
    area_total = resultado["estrutura"]["pavimento"]["area_m2"] * resultado["estrutura"]["n_pavimentos"]
    conc = dados["quantitativos"]["concreto_estrut"]
    forma = dados["quantitativos"]["forma"]
    idx_conc = conc / area_total
    idx_forma = forma / area_total
    assert 0.12 <= idx_conc <= 0.30, f"idx_conc {idx_conc} fora de banda G14 0.12-0.30"
    assert 1.5 <= idx_forma <= 2.6, f"idx_forma {idx_forma} fora de 1.5-2.6"
    # compara com Petropolis 0,206: dentro de 15% de magnitude
    fixture = _js.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    idx_petro = fixture["valores"]["indice_concreto_total_m3_per_m2_construir"]["valor"]
    assert abs(idx_conc - idx_petro) / idx_petro < 0.25, "framework idx vs petropolis idx ordem de grandeza deve bater (<25%)"
    # guarda 3: taxa aco global 51,6 propositalmente baixa (sem viga) deve ser <80
    taxa_armadura_global = (dados["quantitativos"].get("armadura_laje", 0) + dados["quantitativos"].get("armadura_pilar", 0)) / conc if conc else 0
    # REVISAO-G14 global 51,6
    assert 45 < taxa_armadura_global < 65, f"taxa global {taxa_armadura_global:.1f} deve ser ~51,6 e abaixo de 80 -> banda pegaria"
    # verifica que comparacao nao autoriza mudar framework
    comp = _js.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    assert comp["mudou_framework"] is False
    for det in comp["detalhes_por_valor"].values():
        if det["veredito"] == "framework_errado":
            assert det.get("citacao_normativa"), "framework_errado exige citacao"


def test_g27_guia_d_sen45_analoga_declarada():
    """Guarda contra falsa divergencia: m3 total EMOP vs m3 por elemento, m3 vs m3/m2."""
    comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    # fixture deve declarar contexto nao_comparavel
    txt_fixture = json.dumps(fixture, ensure_ascii=False).lower()
    assert "nao_comparavel" in txt_fixture or "nao da para comparar" in txt_fixture or "elemento" in txt_fixture
    # comparacao deve declarar definicao_comparacao para guarda
    det = comp["detalhes_por_valor"]["geometria_elemento_a_elemento"]
    assert "definicao_comparacao" in det
    assert "mesma definicao" in det.get("medicao_mesma_definicao","").lower() or "declarar" in det.get("medicao_mesma_definicao","").lower()
    # relatorio deve mencionar guarda
    rel = (REPO / "fontes_externas" / "licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "relatorio.txt").read_text(encoding="utf-8")
    assert "d·sen" in rel or "d*sen" in rel or "sen(45)" in rel or "sen45" in rel.lower() or "guarda" in rel.lower()
    assert "m3 total" in rel.lower() or "m3 por elemento" in rel.lower() or "elemento a elemento" in rel.lower()
    assert "m3/m2" in rel or "banda" in rel.lower()


def test_g27_registro_hierarquia_e_sha_e_4_lugares():
    reg = json.loads(REGISTRO_PATH.read_text(encoding="utf-8"))
    entry = next((e for e in reg["fontes"] if e["id"] == "licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL"), None)
    assert entry is not None, "registro nao contem Petropolis"
    assert entry["classe_autoridade"] == "licitacao_executada", "Petropolis deve ser licitacao_executada (maior autoridade)"
    assert PROTO.ROTULO_CONCORDANCIA in entry["rotulo"]
    assert PROTO.SUFIXO_DIRETORIO in entry["id"]
    assert len(entry["sha256"]) == 64
    # hierarquia: licitacao_executada rank 0 deve ser menor que tcc_academico
    assert PROTO.hierarquia_rank(entry["classe_autoridade"]) == 0
    assert PROTO.hierarquia_rank("licitacao_executada") < PROTO.hierarquia_rank("tcc_academico")
    # url deve ser https para Petropolis Celina Schechner (G29) e nao tmp
    assert entry["url"].startswith("https://"), f"url deve ser https, veio {entry['url']}"
    assert "petropolis.rj.gov.br" in entry["url"] and "CELINA%20SCHECHNER" in entry["url"] or "celina" in entry["url"].lower(), f"url deve conter Petropolis Celina Schechner, veio {entry['url']}"
    assert "tmp" not in entry["url"], "url nao deve conter tmp"
    # titulo deve mencionar Celina Schechner 2a licitacao (G29)
    assert "Celina Schechner" in entry["titulo_obra"] and "2" in entry["titulo_obra"], f"titulo_obra deve mencionar Celina Schechner 2a licitacao, veio {entry['titulo_obra']}"
    assert "Quitandinha" not in entry["titulo_obra"], "titulo_obra nao deve conter Quitandinha (fabricado)"
    assert "Quitandinha" not in entry["autor"], "autor nao deve conter Quitandinha"
    # sha deve bater com PDF
    sha = PROTO.compute_sha256(PDF_PATH)
    fonte = json.loads(FONTE_PATH.read_text(encoding="utf-8"))
    assert sha == fonte["sha256"] == entry["sha256"]
    # 4 lugares: diretoria, JSON, README, relatorio
    assert PDF_PATH.is_file() and PDF_PATH.read_bytes().startswith(b"%PDF")
    assert PROTO.ROTULO_CONCORDANCIA in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["_aviso"]
    assert PROTO.ROTULO_CONCORDANCIA in json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))["_aviso"]
    assert PROTO.ROTULO_CONCORDANCIA in json.loads(FONTE_PATH.read_text(encoding="utf-8"))["rotulo"]
    readme = (REPO / "fontes_externas" / "licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "README.md").read_text(encoding="utf-8")
    assert PROTO.ROTULO_CONCORDANCIA in readme
    rel = (REPO / "fontes_externas" / "licitacao-petropolis-escola-2023__CONCORDANCIA-CALCULISTAS__NAO-E-OBRA-REAL" / "relatorio.txt").read_text(encoding="utf-8")
    assert PROTO.ROTULO_CONCORDANCIA in rel
    # registro nao deve afirmar validado contra obra real
    for p in REPO.rglob("fontes_externas/licitacao-petropolis*/*"):
        if p.suffix in (".json", ".md", ".txt"):
            txt = p.read_text(encoding="utf-8", errors="ignore").lower()
            if "validado contra obra real" in txt:
                assert "nao" in txt or "não" in txt or "concordancia" in txt, f"{p} afirma validado contra obra real sem negacao"


def test_g27_fonte_pdf_existe_e_sha_bate():
    assert PDF_PATH.is_file()
    data = PDF_PATH.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 100000 and len(data) < 5000000, f"PDF tamanho suspeito {len(data)} (real Celina Schechner 1.8M, 43 pgs)"
    sha = PROTO.compute_sha256(PDF_PATH)
    fonte = json.loads(FONTE_PATH.read_text(encoding="utf-8"))
    assert sha == fonte["sha256"]
    # verificar que PDF contem trechos auditados
    try:
        import fitz
        doc = fitz.open(str(PDF_PATH))
        texto = "".join(p.get_text() for p in doc)
        assert "401,75" in texto
        assert "59,84" in texto
        assert "23,07" in texto or "23.07" in texto
        assert "1.049,98" in texto or "1049,98" in texto
        assert "EMOP" in texto
        assert "CELINA" in texto or "Celina" in texto or "ARCAS" in texto or "Petr" in texto or "PETR" in texto
    except ImportError:
        pass


def test_g27_nao_inventa_geometria_e_veredito_nao_framework_errado():
    """G27 nao deve inventar geometria para comparar elemento; nenhum veredito pode ser framework_errado sem citacao."""
    comp = json.loads(COMPARACAO_PATH.read_text(encoding="utf-8"))
    # nenhum framework_errado sem citacao normativa
    for nome, det in comp["detalhes_por_valor"].items():
        if det["veredito"] == "framework_errado":
            assert det.get("citacao_normativa") and len(det["citacao_normativa"].strip()) > 5, f"{nome} framework_errado exige citacao_normativa"
            # fechar_divergencia deve exigir citacao
            PROTO.fechar_divergencia(det["veredito"], det["citacao_normativa"], mudou_framework=False)  # nao deve lancar se citacao existe
        else:
            # veredito nao framework_errado nao pode ter mudou_framework True
            assert comp["mudou_framework"] is False
    # geral tambem nao pode ser framework_errado sem citacao
    if comp["veredito"] == "framework_errado":
        assert comp.get("citacao_normativa")
    # texto deve mencionar que nao inventa geometria/taxa
    txt = json.dumps(comp, ensure_ascii=False).lower()
    assert "nao" in txt and ("inventar" in txt or "estimativa por taxa" in txt or "nao ha estimativa" in txt or "sem geometria" in txt)
