"""G104: rota SVG-direta sem freecad.exe (hidraulica/incendio/climatizacao).

Portao da rota alternativa (prancha_svg_direta): o esquema SVG puro vira 2 PDFs
A1 com carimbo sem instanciar o freecad.exe grafico. O caminho FreeCAD continua
existindo (backend="freecad") e e' provado aqui sem executar (exe inexistente
-> erro nomeado). Tudo em tmp_path: nenhum teste muta a arvore viva (regra 2).

Escada (regra 3): substring -> ET.fromstring -> confere_folha_svg -> svg_para_png
(render). Anti-tautologia (regra 5): os numeros cobrados no PDF vem do rodar()
(DN/capacidade calculados), nunca do proprio PDF. Saturacao (regra 4): o quadro
tem de conter as linhas adotadas (nao basta OK=True).
"""
import inspect
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_hidraulica as ghi
import galpao_seguranca_incendio as gsi
import galpao_climatizacao as gcl
import prancha_svg_direta as PSD
from desenho_svg_base import confere_folha_svg
from caderno_casa_edificio import svg_para_png


def _r_hid():
    return ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                      "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2},
                                     "aparelhos_esgoto": {"bacia": 2, "lavatorio": 2}}})


def _r_inc():
    return gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                      "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                      "deteccao": {"viga_m": 0.0},
                      "sprinklers": {"altura_estoque_m": 3.0}})


def _r_cli():
    return gcl.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "tipo": "galpao"})


def _esquema_svg(disciplina, r):
    cfg, _ = PSD._cfg_da_disciplina(disciplina, r, "/tmp/x")
    return cfg.get("esquema_svg") or cfg.get("planta_svg") or ""


# ------------------------- baseline: lado bom -------------------------
def test_rota_svg_hidraulica_emite_2_pdfs_a1(tmp_path):
    res = ghi.montar_pranchas(_r_hid(), str(tmp_path))
    assert res.get("ok") is True, res
    assert res.get("rota") == "svg-direta", res
    assert res.get("fcstd") is None, res
    assert len(res.get("arquivos", [])) == 2, res
    for pdf in res["arquivos"]:
        assert os.path.exists(pdf) and os.path.getsize(pdf) > 0, pdf
    import fitz
    for pdf in res["arquivos"]:
        with fitz.open(pdf) as d:
            assert d.page_count >= 1
            rect = d[0].rect
            assert abs(rect.width - PSD.A1_W_PT) < 2.0, (rect.width, rect.height)
            assert abs(rect.height - PSD.A1_H_PT) < 2.0, (rect.width, rect.height)


def test_rota_svg_incendio_emite_2_pdfs_a1(tmp_path):
    # G138: a rota do incendio emite 3 PDFs (planta + quadro + PE-IN-02
    # detalhes de hidrantes adaptados do calculo, sem recalcular).
    res = gsi.montar_pranchas(_r_inc(), str(tmp_path))
    assert res.get("ok") is True, res
    assert len(res.get("arquivos", [])) == 3, res
    assert res.get("pranchas", [])[-1] == "INC03_DETALHES", res
    for pdf in res["arquivos"]:
        assert os.path.exists(pdf) and os.path.getsize(pdf) > 0, pdf


def test_rota_svg_climatizacao_emite_2_pdfs_a1(tmp_path):
    res = gcl.montar_pranchas(_r_cli(), str(tmp_path))
    assert res.get("ok") is True, res
    assert len(res.get("arquivos", [])) == 2, res
    for pdf in res["arquivos"]:
        assert os.path.exists(pdf) and os.path.getsize(pdf) > 0, pdf


# ------------------------- escada: parse + guarda + render -------------------------
def test_rota_svg_esquemas_passam_na_guarda_e_no_parse():
    for disciplina, r in (("hidraulica", _r_hid()), ("incendio", _r_inc()),
                          ("climatizacao", _r_cli())):
        svg = _esquema_svg(disciplina, r)
        assert svg.startswith("<svg"), disciplina
        ET.fromstring(svg)
        g = confere_folha_svg(svg)
        assert g["ok"], (disciplina, g)


def test_rota_svg_esquemas_renderizam_no_fitz(tmp_path):
    for disciplina, r in (("hidraulica", _r_hid()), ("incendio", _r_inc()),
                          ("climatizacao", _r_cli())):
        svg = _esquema_svg(disciplina, r)
        p_svg = str(tmp_path / ("%s.svg" % disciplina))
        p_png = str(tmp_path / ("%s.png" % disciplina))
        with open(p_svg, "w", encoding="utf-8") as f:
            f.write(svg)
        assert svg_para_png(p_svg, p_png) is True, disciplina
        assert os.path.getsize(p_png) > 0, disciplina


# ------------------------- conteudo: carimbo + quadro (anti-saturacao) -------------------------
def test_rota_svg_quadro_contem_numeros_do_calculo(tmp_path):
    import fitz
    rh = _r_hid()
    res = ghi.montar_pranchas(rh, str(tmp_path))
    assert res.get("ok"), res
    quadro = [a for a in res["arquivos"] if "QUADRO" in a]
    assert len(quadro) == 1, res
    with fitz.open(quadro[0]) as d:
        txt = "\n".join(p.get_text() for p in d)
    dn_pluvial = "DN %.0f" % rh["redes"]["pluvial"]["D_mm"]
    assert dn_pluvial in txt, (dn_pluvial, txt[:600])
    assert "NBR 10844" in txt and "NBR 8160" in txt and "NBR 5626" in txt
    assert "PE-HID-02" in txt


def test_rota_svg_carimbo_preservado_nas_duas_paginas(tmp_path):
    import fitz
    ri = _r_inc()
    res = gsi.montar_pranchas(ri, str(tmp_path))
    assert res.get("ok"), res
    for pdf in res["arquivos"]:
        with fitz.open(pdf) as d:
            txt = d[0].get_text()
        assert "SEG. INCENDIO" in txt, (pdf, txt[:400])
        assert "NBR 10898" in txt or "NBR 17240" in txt, (pdf, txt[:400])


def test_rota_svg_climatizacao_quadro_contem_capacidade(tmp_path):
    import fitz
    rc = _r_cli()
    res = gcl.montar_pranchas(rc, str(tmp_path))
    assert res.get("ok"), res
    with fitz.open(res["arquivos"][1]) as d:
        txt = "\n".join(p.get_text() for p in d)
    assert "%.1f TR" % rc["gates"]["capacidade"]["TR"] in txt
    assert "NBR 16401" in txt and "PE-CLI-02" in txt


def _so_palavras(texto):
    return " ".join(str(texto).split())


def test_rota_svg_quadro_nao_corta_nota_nem_linha(tmp_path):
    """G106: a pagina do quadro cortava cada linha em 220 caracteres e
    parava no fim da A1 com `break` - a nota de ~400 caracteres da
    hidraulica saia pela metade, em silencio. Cada nota e cada linha do cfg
    (fonte: o config_de_spec, nunca o PDF) tem de estar INTEIRA no texto do
    PDF, com a quebra de linha desfeita."""
    import fitz
    rh = _r_hid()
    cfg, _ = PSD._cfg_da_disciplina("hidraulica", rh, str(tmp_path))
    notas = cfg.get("notas") or []
    assert max(len(str(n)) for n in notas) > 220, (
        "a fixture perdeu a nota longa que prova o corte")
    res = ghi.montar_pranchas(rh, str(tmp_path))
    assert res.get("ok"), res
    quadro = [a for a in res["arquivos"] if "QUADRO" in a][0]
    with fitz.open(quadro) as d:
        texto = _so_palavras(" ".join(p.get_text() for p in d))
    faltam = [str(n)[:60] for n in notas if _so_palavras(n) not in texto]
    faltam += [" | ".join(str(c) for c in row)[:60]
               for row in (cfg.get("dim_rows") or [])
               if _so_palavras(" | ".join(str(c) for c in row)) not in texto]
    assert not faltam, "cortado do quadro A1: %r" % (faltam,)


def test_rota_svg_quadro_longo_continua_em_nova_pagina(tmp_path):
    """Injecao (tmp_path): 120 linhas nao cabem numa A1. Todas saem, em
    paginas de continuacao do mesmo PDF, cada uma com o carimbo."""
    import fitz
    linhas = [["TRECHO-%03d" % i, "DN %d" % (50 + i), "ok"] for i in range(120)]
    doc = fitz.open()
    try:
        n = PSD.pagina_quadro_a1(doc, {"drawing_number": "PE-X-02"}, "TIT",
                                 "SUB", ["trecho", "DN", "status"], linhas,
                                 ["nota"])
        caminho = str(tmp_path / "longo.pdf")
        doc.save(caminho)
    finally:
        doc.close()
    assert n > 1, n
    with fitz.open(caminho) as d:
        assert d.page_count == n
        paginas = [p.get_text() for p in d]
    texto = " ".join(paginas)
    faltam = [l[0] for l in linhas if l[0] not in texto]
    assert not faltam, faltam
    assert all("PE-X-02" in p for p in paginas), "carimbo sumiu na continuacao"


# ------------------------- baseline: lado vermelho (injecao em tmp_path) -------------------------
def test_rota_svg_svg_corrompido_nao_gera_pdf(tmp_path):
    import fitz
    doc = fitz.open()
    try:
        ok = PSD.pagina_esquema_a1(doc, "<svg>quebrado sem fechar", {}, "TIT", "SUB")
    finally:
        doc.close()
    assert ok is False


def test_rota_svg_disciplina_desconhecida_e_erro_nomeado(tmp_path):
    res = PSD.montar_pranchas_rota_direta(_r_hid(), str(tmp_path), "aco")
    assert "erro" in res and "aco" in res["erro"], res


def test_rota_svg_caminho_freecad_continua_existindo():
    for mod in (ghi, gsi, gcl):
        sig = inspect.signature(mod.montar_pranchas)
        assert "backend" in sig.parameters, mod.__name__
        assert sig.parameters["backend"].default == "svg", mod.__name__


def test_rota_svg_backend_freecad_sem_exe_e_erro_nomeado(tmp_path):
    res = ghi.montar_pranchas(_r_hid(), str(tmp_path),
                              freecad_exe="/nao/existe.exe", backend="freecad")
    assert "erro" in res, res
    res2 = gsi.montar_pranchas(_r_inc(), str(tmp_path),
                               freecad_exe="/nao/existe.exe", backend="freecad")
    assert "erro" in res2, res2
    res3 = gcl.montar_pranchas(_r_cli(), str(tmp_path),
                               freecad_exe="/nao/existe.exe", backend="freecad")
    assert "erro" in res3, res3
