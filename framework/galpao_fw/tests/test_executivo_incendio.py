"""Executivo da SEGURANCA CONTRA INCENDIO: planta de seguranca / rotas de fuga
(desenho_incendio, SVG puro) e pranchas A1 (techdraw_incendio). Camada pura em CI;
a geracao real das pranchas roda no freecad.exe (guarda `build`, skip sem FreeCAD)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_seguranca_incendio as gsi
import desenho_incendio as di
import techdraw_incendio as tdi

FREECAD_EXE = os.environ.get("FREECAD_EXE", r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe")


def _spec(**kw):
    base = {"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
            "deteccao": {"viga_m": 0.0}, "sprinklers": {"altura_estoque_m": 3.0}}
    base.update(kw)
    return base


def _r(**kw):
    return gsi.rodar(_spec(**kw))


# ------------------------------ desenho (SVG puro) ---------------------------
def test_desenho_selftest():
    di._selftest()


def test_planta_svg_tem_elementos():
    svg = di.planta_seguranca_svg(_r())
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    for termo in ("PLANTA DE SEGURANCA", "LEGENDA", "RESUMO", "Detector",
                  "Chuveiro", "Saida de emergencia", "Rota de fuga", "Acionador"):
        assert termo in svg, termo


def test_planta_desenha_contagens_da_norma():
    # a planta reflete as contagens do rodar() (drawing == data)
    r = _r()
    g = r["gates"]
    svg = di.planta_seguranca_svg(r)
    # o resumo cita os numeros calculados
    assert "%d (pontual)" % g["deteccao_alarme"]["N_detectores"] in svg
    assert "Chuveiros: %d" % g["sprinklers"]["N_chuveiros"] in svg
    assert "Reserva: %.0f m3" % g["sprinklers"]["reserva_m3"] in svg


def test_planta_sem_sprinklers_nao_quebra():
    r = gsi.rodar({"geometria": {"L": 30.0, "W": 15.0, "H": 5.0},
                   "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0}})
    svg = di.planta_seguranca_svg(r)
    assert svg.startswith("<svg") and "Chuveiro" in svg          # legenda existe
    # sem sprinklers, o resumo NAO cita reserva
    assert "Reserva:" not in svg


def test_grade_proporcional():
    c, r = di._grade(10, 40.0, 20.0)
    assert c * r >= 10 and c >= r                                # galpao comprido -> +colunas
    assert di._grade(1, 40.0, 20.0) == (1, 1)


def test_gerar_planta_escreve_arquivo(tmp_path):
    p = di.gerar_planta(_r(), str(tmp_path / "planta.svg"))
    assert os.path.exists(p) and os.path.getsize(p) > 0


# ------------------------------ config (puro) --------------------------------
def test_config_de_spec_incendio():
    cfg = tdi.config_de_spec(_r(), "/out", _spec())
    assert cfg["planta_svg"].startswith("<svg")
    assert cfg["resumo_hdr"] == ["SISTEMA", "QUANTIDADE", "NORMA"]
    # o carimbo NAO vaza material/norma de aco
    assert cfg["carimbo_material"] == "SEG. INCENDIO"
    # o resumo tem uma linha por sistema, cada uma com a norma
    normas = {row[2] for row in cfg["resumo"]}
    assert {"NBR 10898", "NBR 16820", "NBR 17240", "NBR 10897"} <= normas


def test_config_notas_citam_hidrantes_e_avcb():
    cfg = tdi.config_de_spec(_r(), "/out")
    txt = "\n".join(cfg["notas"])
    assert "NBR 13714" in txt and "reserva de incendio" in txt     # hidrantes na reserva
    assert "AVCB" in txt


def test_carimbo_nao_vaza_campos_estruturais():
    # o carimbo generico traz defaults de ACO/ESTRUTURA; o de incendio corrige TODOS
    cfg = tdi.config_de_spec(_r(), "/out")
    car = tdi._carimbo_inc(cfg, "PLANTA", "PE-INC-01", "S/ESC", "01/02")
    assert "ESTRUTURAL" not in car["document_type"]
    assert car["responsible_department"] == "SEG. INCENDIO"
    assert car["part_material"] == "SEG. INCENDIO"
    assert "8800" not in car["general_tolerances"] and "6118" not in car["general_tolerances"]


def test_script_bootstrap_injeta_svg_e_entry():
    cfg = tdi.config_de_spec(_r(), "/out")
    src = tdi.script_bootstrap(cfg)
    assert "_entry_incendio" in src and "QTimer" in src
    assert "TechDraw::DrawViewSymbol" in tdi.codigo_fonte()


# ------------------------------ build (freecad.exe) --------------------------
@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECAD_EXE), reason="freecad.exe ausente")
def test_build_gera_pranchas_pdf(tmp_path):
    r = _r()
    out = str(tmp_path).replace("\\", "/")
    res = gsi.montar_pranchas(r, out, spec=_spec(), timeout=1200)
    assert res.get("ok"), res
    assert len(res.get("pranchas", [])) == 2
    pdfs = [a for a in res.get("arquivos", []) if a.endswith(".pdf")]
    assert len(pdfs) == 2 and all(os.path.exists(p) and os.path.getsize(p) > 0
                                  for p in pdfs), res
