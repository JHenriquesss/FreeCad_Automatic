"""Pacote legal/gestao: indice de pranchas, memorial consolidado, lista de ART,
checklists PPCI-AVCB e LOD-BIM, manual O&M. Camada PURA (CI)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import pacote_legal as pl


def test_selftest():
    assert pl._selftest() is True


def test_indice_pranchas_codigos_unicos():
    idx = pl.indice_de_pranchas(["concreto", "aco", "eletrico", "coordenacao"])
    cods = [p["codigo"] for p in idx]
    assert len(cods) == len(set(cods))
    assert all(c.startswith("PE-") for c in cods)


def test_art_rrt_por_conselho():
    arq = pl.lista_art(["arquitetura"])[0]
    assert arq["instrumento"] == "RRT" and arq["conselho"] == "CAU"
    eng = pl.lista_art(["concreto"])[0]
    assert eng["instrumento"] == "ART" and eng["conselho"] == "CREA"


def test_art_dados_rt_a_confirmar():
    """AR300: nome/registro/numero da ART sao A CONFIRMAR (nao inventados)."""
    for a in pl.lista_art(["concreto", "eletrico"]):
        assert a["responsavel_tecnico"] == "A CONFIRMAR"
        assert a["registro"] == "A CONFIRMAR" and a["numero_art"] == "A CONFIRMAR"


def test_checklist_ppci_avcb():
    ck = pl.checklist_ppci_avcb()
    assert len(ck) >= 5 and any("AVCB" in s for s in ck)


def test_checklist_lod_bim():
    lod = pl.checklist_lod_bim()
    assert all(c["lod"].startswith("LOD") for c in lod)
    assert any("federado" in c["grupo"].lower() for c in lod)


def test_manual_oem():
    om = pl.manual_oem(["concreto", "incendio"])
    discs = {o["disciplina"] for o in om}
    assert "concreto" in discs and "incendio" in discs
    assert all(o["rotina"] and o["periodicidade"] for o in om)


def test_memorial_consolidado_do_turnkey():
    R = {"geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
         "executadas": ["concreto", "eletrico"], "puladas": [],
         "disciplinas": {"concreto": {"ATENDE": True, "reprovados": []},
                         "eletrico": {"ATENDE": False, "reprovados": ["curto"]}},
         "ATENDE": False}
    m = pl.memorial_consolidado(R)
    vered = {it["disciplina"]: it["veredito"] for it in m["disciplinas"]}
    assert vered["concreto"] == "ATENDE" and vered["eletrico"] == "REPROVA"
    assert m["atende_global"] is False


def test_gerar_pacote_e_markdown():
    R = {"geometria": {"comprimento": 40}, "executadas": ["concreto"], "puladas": [],
         "disciplinas": {"concreto": {"ATENDE": True, "reprovados": []}}, "ATENDE": True}
    pac = pl.gerar_pacote(R=R)
    md = pl.markdown(pac)
    for sec in ("Indice de pranchas", "Lista de ART", "Checklist PPCI/AVCB",
                "Checklist LOD", "Manual de O&M", "Memorial descritivo"):
        assert sec in md
