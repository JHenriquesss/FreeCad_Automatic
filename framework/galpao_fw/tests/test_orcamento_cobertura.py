# ============================================================================
# test_orcamento_cobertura.py - G7: A CAMADA RELIGADA RODA, MAS ESTAVA ERRADA.
# G6 provou que orcamento/cronograma/caderno/pacote SAEM da rodada. Estes testes
# travam o que G6 nao olhou: se o que sai esta CERTO.
#   (1) o orcamento de um galpao METALICO nao pode ignorar o aco (o peso ja
#       existia no raw do vertical, a uma chave de distancia - filtro-de-nome-morto);
#   (2) sapata nao e' superestrutura (rotulo x geometria: mesmo m3, outro preco);
#   (3) orcamento que cobre 1 insumo nao pode se apresentar como fechado;
#   (4) a curva S que satura em 100% antes do fim tem que dizer isso NO ARTEFATO;
#   (5) o caderno nao especifica piso que ninguem dimensionou e o pacote legal
#       nao promete LOD de disciplina que nao rodou.
# ============================================================================
"""Correcao (nao so alcancabilidade) dos entregaveis de gestao."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import caderno_encargos as ce
import cronograma as cr
import orcamento as orc
import pacote_legal as pl


def _R_aco(kg=19705.9):
    return {"executadas": ["aco"],
            "disciplinas": {"aco": {"rodou": True,
                                    "raw": {"romaneio_peso_primario_kg": kg}}}}


# ------------------------------- (1) o aco entra ------------------------------
def test_aco_estrutural_sai_do_romaneio_do_vertical():
    q = orc.quantitativos_de_turnkey(_R_aco())
    assert q["aco_estrutural"] == 19705.9


def test_aco_domina_a_curva_abc_do_galpao_metalico():
    # 19,7 t x R$ 18/kg = R$ 354 mil: sem ele o orcamento errava por ordem de
    # grandeza, e nada avisava.
    res = orc.compor_orcamento(orc.quantitativos_de_turnkey(_R_aco()))
    assert res["planilha"]["custo_direto"] > 300000.0
    assert res["abc"]["itens"][0]["codigo"] == "aco_estrutural"


def test_aco_nao_rodou_nao_inventa_peso():
    q = orc.quantitativos_de_turnkey(
        {"disciplinas": {"aco": {"rodou": False, "raw": None}}})
    assert "aco_estrutural" not in q


def test_peso_do_romaneio_invalido_nao_vira_quantitativo():
    for ruim in (None, "", "n/a", 0):
        q = orc.quantitativos_de_turnkey(_R_aco(kg=ruim))
        assert "aco_estrutural" not in q, ruim


# --------------------- (2) sapata nao e' superestrutura -----------------------
def test_sapata_vai_para_fundacao_e_nao_para_concreto_estrutural():
    import galpao_turnkey as tk
    R = tk.rodar({"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
                  "concreto": {"vao": 20.0, "comprimento": 40.0, "n_porticos": 7,
                               "v0": 40.0, "cat": "IV", "classe": "B", "s1": 1.0,
                               "s3": 1.0, "G_roof": 0.30, "Q_roof": 0.25,
                               "fck": 30e3, "fyk": 500e3, "sigma_solo_adm": 250.0,
                               "travamento_longitudinal": "topo"}})
    q = orc.quantitativos_de_turnkey(R)
    assert q["fundacao_concreto"] > 0 and q["concreto_estrut"] > 0
    # o volume das sapatas domina; se tudo caisse em concreto_estrut, o preco
    # unitario aplicado seria o da superestrutura (620 vs 780 R$/m3).
    assert q["fundacao_concreto"] > q["concreto_estrut"]


# ---------------------- (3) orcamento parcial se declara ----------------------
def test_orcamento_de_um_insumo_declara_o_que_nao_cobre():
    res = orc.compor_orcamento({"concreto_estrut": 76.3})
    assert "aco_estrutural" in res["sem_quantidade"]
    assert res["cobertura_pct"] < 20.0
    assert "ORCAMENTO PARCIAL" in orc.relatorio_pt(res)


def test_orcamento_completo_nao_grita_sem_motivo():
    tudo = {c: 1.0 for c in orc.preco_ref()}
    res = orc.compor_orcamento(tudo)
    assert res["sem_quantidade"] == [] and res["cobertura_pct"] == 100.0
    assert "ORCAMENTO PARCIAL" not in orc.relatorio_pt(res)


# ------------------ (4) saturacao da curva S visivel no artefato --------------
def _crono_parcial():
    ats = cr.aplica_custos([dict(a) for a in cr._WBS_GALPAO], {"estr": 50000.0})
    return cr.cronograma(ats)


def test_curva_s_saturada_avisa_no_relatorio_e_no_svg():
    crono = _crono_parcial()
    txt = cr.relatorio_pt(crono, cr.curva_s(crono))
    assert "ATENCAO" in txt and "satura" in txt
    assert "satura" in cr.curva_s_svg(crono)


def test_curva_s_totalmente_custeada_nao_avisa():
    custos = {a["id"]: 1000.0 for a in cr._WBS_GALPAO}
    crono = cr.cronograma(cr.aplica_custos([dict(a) for a in cr._WBS_GALPAO], custos))
    assert cr.aviso_custeio(crono) == ""
    assert "ATENCAO" not in cr.relatorio_pt(crono, cr.curva_s(crono))


def test_svg_com_aviso_continua_xml_valido():
    import xml.dom.minidom as md
    md.parseString(cr.curva_s_svg(_crono_parcial()))


# ------------- (5) caderno e pacote nao prometem o que nao existe -------------
def test_pacote_legal_nao_promete_lod_de_disciplina_que_nao_rodou():
    pac = pl.gerar_pacote(disciplinas=["concreto"])
    grupos = [c["grupo"] for c in pac["checklist_lod_bim"]]
    assert "Instalacoes eletricas" not in grupos
    assert "Incendio" not in grupos
    assert "Estrutura (pilares/vigas/fundacoes)" in grupos
    assert "Coordenacao/federado" in grupos          # o federado e do pacote


def test_pacote_legal_com_eletrico_mantem_o_grupo():
    pac = pl.gerar_pacote(disciplinas=["concreto", "eletrico"])
    assert "Instalacoes eletricas" in [c["grupo"] for c in pac["checklist_lod_bim"]]


def test_caderno_nao_especifica_piso_nao_dimensionado():
    R = {"executadas": ["concreto"],
         "disciplinas": {"concreto": {"raw": {"piso": None}}}}
    discs = {s["disciplina"] for s in ce.caderno_de_turnkey(R)["secoes"]}
    assert "piso" not in discs and "fundacao" in discs


# ---------- (6) uma frente do sitio nao pode levar as outras junto ------------
def _spec_sitio(esgoto):
    return {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "concreto": {"vao": 20.0, "comprimento": 40.0, "n_porticos": 7, "v0": 40.0,
                     "cat": "IV", "classe": "B", "s1": 1.0, "s3": 1.0,
                     "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
                     "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"},
        "site": {"terraplenagem": {"grid_terreno": [[101.0, 100.5], [100.2, 99.8]],
                                   "cota_plataforma": 100.0, "area_celula_m2": 100.0,
                                   "empolamento": 1.25},
                 "saneamento": {"esgoto": esgoto}},
    }


def test_esgoto_incompleto_nao_apaga_a_terraplenagem(tmp_path):
    import galpao_adapter  # noqa: F401  (registra o adaptador)
    from project_loop import run_project
    # falta 'N' no esgoto: antes o hook inteiro morria com "KeyError: 'N'" e o
    # corte/aterro JA calculado ia junto.
    m = run_project(_spec_sitio({"C": 130, "T": 1.0, "K": 65, "Lf": 1.0}),
                    tmp_path, {"generate_ifc": False})
    ent = m["deliverables"]["obras_sitio"]
    assert ent["status"] == "partial"
    assert "terraplenagem" in ent["frentes"]
    falha = ent["frentes_com_falha"][0]
    assert falha["frente"] == "esgoto" and "N" in falha["erro"]


def test_sitio_completo_fica_generated(tmp_path):
    import galpao_adapter  # noqa: F401
    from project_loop import run_project
    m = run_project(_spec_sitio({"N": 40, "C": 130, "T": 1.0, "K": 65, "Lf": 1.0}),
                    tmp_path, {"generate_ifc": False})
    ent = m["deliverables"]["obras_sitio"]
    assert ent["status"] == "generated" and ent["frentes_com_falha"] == []
