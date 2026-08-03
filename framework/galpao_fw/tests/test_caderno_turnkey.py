"""Caderno executivo UNICO do turnkey (caderno_turnkey): mesclagem de PDFs de
pranchas de varias disciplinas num so caderno (capa + indice + divisorias +
pranchas). Camada de MERGE testada com PDFs sinteticos (PyMuPDF), sem FreeCAD -> CI.
A orquestracao viva (freecad.exe) e' `build`."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import caderno_turnkey as ct

fitz = pytest.importorskip("fitz")


def _R(**kw):
    base = {"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
            "executadas": ["eletrico", "incendio"], "reprovados": [], "ATENDE": True,
            "disciplinas": {"eletrico": {"rodou": True, "ATENDE": True, "reprovados": []},
                            "incendio": {"rodou": True, "ATENDE": True, "reprovados": []}}}
    base.update(kw)
    return base


def _prancha(tmp, nome, folhas):
    prd = os.path.join(tmp, nome, "pranchas")
    os.makedirs(prd, exist_ok=True)
    for f in folhas:
        ct._pdf_dummy(os.path.join(prd, f + ".pdf"), f)
    return ct._coletar_pdfs(tmp, nome)


def test_selftest():
    ct._selftest()


def test_caderno_mescla_multidisciplina(tmp_path):
    tmp = str(tmp_path)
    pdfs = {"eletrico": _prancha(tmp, "eletrico", ["PE-EL-01", "PE-EL-02", "PE-EL-03"]),
            "incendio": _prancha(tmp, "incendio", ["PE-INC-01", "PE-INC-02"])}
    res = ct.montar_caderno_de_pdfs(pdfs, os.path.join(tmp, "CAD.pdf"), _R(), {"slug": "g"})
    assert res["n_pranchas"] == 5 and res["disciplinas"] == {"eletrico": 3, "incendio": 2}
    assert res["faltando"] == []
    # capa + indice + 2 divisorias + 5 pranchas
    assert res["n_paginas"] >= 7


def test_capa_traz_veredito_global_e_indice(tmp_path):
    tmp = str(tmp_path)
    pdfs = {"incendio": _prancha(tmp, "incendio", ["PE-INC-01"])}
    res = ct.montar_caderno_de_pdfs(pdfs, os.path.join(tmp, "CAD.pdf"),
                                    _R(executadas=["incendio"]), {"slug": "g"})
    with fitz.open(res["path"]) as d:
        txt = "".join(p.get_text() for p in d)
    assert "CADERNO EXECUTIVO" in txt and "VEREDITO GLOBAL: ATENDE" in txt
    assert "INDICE DE PRANCHAS" in txt and "PE-INC-01.pdf" in txt


def test_capa_mostra_reprovacao(tmp_path):
    tmp = str(tmp_path)
    pdfs = {"eletrico": _prancha(tmp, "eletrico", ["PE-EL-01"])}
    R = _R(executadas=["eletrico"], reprovados=["eletrico"], ATENDE=False,
           disciplinas={"eletrico": {"rodou": True, "ATENDE": False, "reprovados": ["curto"]}})
    res = ct.montar_caderno_de_pdfs(pdfs, os.path.join(tmp, "CAD.pdf"), R, {"slug": "g"})
    with fitz.open(res["path"]) as d:
        capa = d[0].get_text()
    assert "REPROVA" in capa and "eletrico" in capa


def test_disciplina_pulada_aparece_na_capa(tmp_path):
    tmp = str(tmp_path)
    R = _R(executadas=["incendio"],
           disciplinas={"incendio": {"rodou": True, "ATENDE": True, "reprovados": []},
                        "aco": {"rodou": False, "ATENDE": None, "reprovados": [],
                                "nota": "vertical de aco requer out_dir - nao executado"}})
    pdfs = {"incendio": _prancha(tmp, "incendio", ["PE-INC-01"])}
    res = ct.montar_caderno_de_pdfs(pdfs, os.path.join(tmp, "CAD.pdf"), R, {"slug": "g"})
    with fitz.open(res["path"]) as d:
        capa = d[0].get_text()
    assert "PULADA" in capa and "ACO" in capa.upper()


def test_ordem_das_disciplinas_no_indice(tmp_path):
    # o indice segue ORDEM (concreto, aco, eletrico, incendio), nao a ordem do dict
    tmp = str(tmp_path)
    pdfs = {"incendio": _prancha(tmp, "incendio", ["PE-INC-01"]),
            "eletrico": _prancha(tmp, "eletrico", ["PE-EL-01"])}
    linhas = ct._linhas_indice(pdfs)
    txt = "\n".join(linhas)
    assert txt.index("ELETRICAS") < txt.index("INCENDIO")     # eletrico antes de incendio


def test_caderno_vazio_reporta_faltando(tmp_path):
    res = ct.montar_caderno_de_pdfs({}, os.path.join(str(tmp_path), "CAD.pdf"),
                                    _R(executadas=[]), {"slug": "g"})
    assert res["n_pranchas"] == 0
    assert any("nenhum" in f for f in res["faltando"])
    assert os.path.exists(res["path"])                        # ainda gera capa+indice


def _clash_fixture():
    # 1 REVISAR (eletrocalha x viga) + 1 ESPERADO (aterramento x sapata)
    rev = {"a": "E-CALHA-P", "b": "C-VC2", "disciplinas": "concretoxeletrico",
           "tipos": "CableCarrierxBeam", "vol_mm3": 1000000.0, "esperado": False}
    esp = {"a": "C-SAP1E", "b": "E-HASTE1", "disciplinas": "concretoxeletrico",
           "tipos": "FootingxEarthing", "vol_mm3": 44775.0, "esperado": True}
    return {"n_membros": 188, "n_clashes": 2, "n_revisar": 1, "n_esperado": 1,
            "clashes": [rev, esp], "revisar": [rev], "esperados": [esp],
            "por_par": {"concretoxeletrico": 2}, "OK": False, "OK_revisar": False}


def test_caderno_apendice_de_clash(tmp_path):
    # apendice de coordenacao: o clash federado vira paginas de texto no caderno, com
    # a TRIAGEM esperado x revisar.
    tmp = str(tmp_path)
    pdfs = {"incendio": _prancha(tmp, "incendio", ["PE-INC-01"])}
    res = ct.montar_caderno_de_pdfs(pdfs, os.path.join(tmp, "CAD.pdf"), _R(), {"slug": "g"},
                                    clash=_clash_fixture())
    assert res["n_clashes"] == 2
    with fitz.open(res["path"]) as d:
        txt = "".join(p.get_text() for p in d)
    assert "CLASH FEDERADO" in txt and "A REVISAR" in txt and "ESPERADOS" in txt
    assert "E-CALHA-P" in txt and "C-VC2" in txt          # o item a revisar aparece
    assert "E-HASTE1" in txt                              # o esperado tambem
    assert "NBR 5419" in txt                              # justificativa dos esperados


def _png_dummy(path):
    """PNG de verdade (via pixmap) p/ testar a pagina-imagem de coordenacao."""
    d = fitz.open()
    pg = d.new_page(width=800, height=500)
    pg.draw_rect(fitz.Rect(40, 40, 760, 460), fill=(0.85, 0.85, 0.92))
    pg.insert_text((100, 250), "MODELO 3D FEDERADO", fontsize=28)
    pg.get_pixmap().save(path)
    d.close()
    return path


def test_caderno_prancha_de_coordenacao_com_render(tmp_path):
    # a PRANCHA DE COORDENACAO embute o RENDER isometrico do federado + a tabela de clash
    tmp = str(tmp_path)
    pdfs = {"incendio": _prancha(tmp, "incendio", ["PE-INC-01"])}
    png = _png_dummy(os.path.join(tmp, "iso.png"))
    res = ct.montar_caderno_de_pdfs(pdfs, os.path.join(tmp, "CAD.pdf"), _R(), {"slug": "g"},
                                    clash=_clash_fixture(), render_png=png)
    assert res["render"] is True
    with fitz.open(res["path"]) as d:
        n_imgs = sum(len(p.get_images()) for p in d)
        txt = "".join(p.get_text() for p in d)
    assert n_imgs >= 1                                    # a imagem foi embutida
    assert "PRANCHA DE COORDENACAO" in txt               # titulo da prancha
    assert "CLASH FEDERADO" in txt                       # a tabela de clash tambem


def test_caderno_render_png_invalido_degrada(tmp_path):
    # PNG ausente/invalido -> render False, caderno ainda monta (best-effort)
    tmp = str(tmp_path)
    pdfs = {"incendio": _prancha(tmp, "incendio", ["PE-INC-01"])}
    res = ct.montar_caderno_de_pdfs(pdfs, os.path.join(tmp, "CAD.pdf"), _R(), {"slug": "g"},
                                    clash=_clash_fixture(),
                                    render_png=os.path.join(tmp, "nao_existe.png"))
    assert res["render"] is False and os.path.exists(res["path"])


def test_add_pagina_imagem_png_ausente_retorna_false(tmp_path):
    import fitz as _f
    doc = _f.open()
    assert ct._add_pagina_imagem(doc, None, "t") is False
    assert ct._add_pagina_imagem(doc, os.path.join(str(tmp_path), "x.png"), "t") is False
    png = _png_dummy(os.path.join(str(tmp_path), "ok.png"))
    assert ct._add_pagina_imagem(doc, png, "titulo") is True


def test_caderno_sem_clash_backward_compat(tmp_path):
    # sem o arg clash: nenhum apendice, n_clashes None (comportamento anterior)
    tmp = str(tmp_path)
    pdfs = {"incendio": _prancha(tmp, "incendio", ["PE-INC-01"])}
    res = ct.montar_caderno_de_pdfs(pdfs, os.path.join(tmp, "CAD.pdf"), _R(), {"slug": "g"})
    assert res["n_clashes"] is None
    with fitz.open(res["path"]) as d:
        txt = "".join(p.get_text() for p in d)
    assert "CLASH FEDERADO" not in txt


def test_linhas_clash_sem_conflitos():
    L = "\n".join(ct._linhas_clash({"n_membros": 10, "n_clashes": 0, "n_revisar": 0,
                                    "n_esperado": 0, "por_par": {}, "clashes": [],
                                    "revisar": [], "esperados": []}))
    assert "nada a revisar" in L and "(nenhum)" in L


def test_aco_dispatch_existe_e_roteia_p_rodar_projeto():
    # o dispatch do aco deve existir e chamar rodar_projeto.rodar_tudo (nao o
    # placeholder antigo). Checa a fonte (sem FreeCAD).
    import inspect
    src = inspect.getsource(ct._dispatch_pranchas)
    assert 'nome == "aco"' in src and "rodar_projeto" in src and "rodar_tudo" in src
    assert "aco emite as pranchas no proprio" not in src        # placeholder removido


def test_aco_incompleto_degrada_sem_crash(tmp_path):
    # aco com spec INCOMPLETO: calcular/exigir_completo levanta -> tk ISOLA -> aco nao
    # executa -> o caderno ainda monta (capa+indice), 0 pranchas, sem crash e sem FreeCAD.
    import galpao_turnkey as tk
    sp = {"geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
          "aco": {"incompleto": True}, "slug": "t"}
    R = tk.rodar(sp, str(tmp_path))
    assert R["disciplinas"]["aco"]["rodou"] is False and "erro" in R["disciplinas"]["aco"]
    res = ct.montar_caderno(sp, str(tmp_path), disciplinas=["aco"], timeout=5)
    assert res["n_pranchas"] == 0 and os.path.exists(res["path"])   # capa+indice mesmo assim


def test_coletar_pdfs_ordenado(tmp_path):
    tmp = str(tmp_path)
    _prancha(tmp, "eletrico", ["PE-EL-03", "PE-EL-01", "PE-EL-02"])
    achados = [os.path.basename(p) for p in ct._coletar_pdfs(tmp, "eletrico")]
    assert achados == ["PE-EL-01.pdf", "PE-EL-02.pdf", "PE-EL-03.pdf"]     # ordenado


# ------------------------------ build (freecad.exe) --------------------------
FREECAD_EXE = os.environ.get("FREECAD_EXE", r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe")


@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECAD_EXE), reason="freecad.exe ausente")
def test_montar_caderno_vivo_incendio(tmp_path):
    # caderno vivo SO com incendio (sem 3D -> rapido): prova o dispatch + merge fim a fim
    spec = {"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
            "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                         "deteccao": {"viga_m": 0.0}, "sprinklers": {"altura_estoque_m": 3.0}},
            "slug": "galpao_turnkey"}
    res = ct.montar_caderno(spec, str(tmp_path), disciplinas=["incendio"], timeout=1100)
    assert res["n_pranchas"] == 2, res
    assert os.path.exists(res["path"]) and os.path.getsize(res["path"]) > 0
