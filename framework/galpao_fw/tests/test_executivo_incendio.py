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
    assert "Reserva chuv.: %.0f m3" % g["sprinklers"]["reserva_m3"] in svg


def test_planta_desenha_contagem_exata():
    # BUG achado na revisao: a grade desenhava cols*rows (>= N), nao EXATAMENTE N.
    r = _r()
    g = r["gates"]
    svg = di.planta_seguranca_svg(r)
    det = svg.count('r="2" fill="#111"') - 1                 # -1 do simbolo da legenda
    spr = svg.count('stroke="#c02128" stroke-width="1.4"') - 1
    assert det == g["deteccao_alarme"]["N_detectores"], (det, g["deteccao_alarme"]["N_detectores"])
    assert spr == g["sprinklers"]["N_chuveiros"], (spr, g["sprinklers"]["N_chuveiros"])


def test_planta_iluminacao_emergencia_count_driven():
    # BUG (drawing != data): a grade de blocos era FIXA 2x2 (=4), divergindo de
    # N_aclaramento (=6) e ignorando N_balizamento. Agora ambos EXATAMENTE == resumo.
    r = _r()
    g = r["gates"]
    svg = di.planta_seguranca_svg(r)
    acl = svg.count('fill="#f2c200" stroke="#7a6300" stroke-width="1"') - 1   # -1 legenda
    bal = svg.count('fill="#f2c200" stroke="#7a6300" stroke-width="0.8"') - 1  # -1 legenda
    assert acl == g["iluminacao_emergencia"]["N_aclaramento"], acl
    assert bal == g["iluminacao_emergencia"]["N_balizamento"], bal
    # o resumo tambem cita as duas contagens separadamente
    assert "Aclaramento: %d" % g["iluminacao_emergencia"]["N_aclaramento"] in svg
    assert "Balizamento: %d" % g["iluminacao_emergencia"]["N_balizamento"] in svg


def test_pontos_exatos_corta_em_n():
    assert len(di._pontos_exatos(10, 0, 0, 640, 480, 40.0, 20.0)) == 10
    assert len(di._pontos_exatos(67, 0, 0, 640, 480, 40.0, 20.0)) == 67
    assert di._pontos_exatos(0, 0, 0, 640, 480, 40.0, 20.0) == []


def test_pontos_perimetro_conta_exata_e_fecha():
    pts = di._pontos_perimetro(31, 0.0, 0.0, 640.0, 480.0)
    assert len(pts) == 31                                    # EXATAMENTE n
    assert di._pontos_perimetro(0, 0, 0, 640, 480) == []
    # todos os pontos ficam sobre o perimetro recuado (nenhum no miolo)
    for (px, py) in pts:
        na_borda = (abs(px - 8) < 1 or abs(px - 632) < 1 or
                    abs(py - 8) < 1 or abs(py - 472) < 1)
        assert na_borda, (px, py)


def test_planta_sem_sprinklers_nao_quebra():
    """G77: a legenda diz o que a PLANTA mostra, nao o que o catalogo tem.

    Este teste exigia "Chuveiro" na legenda de um galpao SEM chuveiro - estava
    cristalizando o defeito: a folha entregue anunciava um simbolo que nao
    aparece no desenho, e o leitor procurava na planta o que ninguem
    dimensionou. Agora mede os dois sentidos.
    """
    r = gsi.rodar({"geometria": {"L": 30.0, "W": 15.0, "H": 5.0},
                   "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0}})
    assert not r["gates"]["sprinklers"]["N_chuveiros"]
    svg = di.planta_seguranca_svg(r)
    assert svg.startswith("<svg")
    assert "LEGENDA" in svg and "Saida de emergencia" in svg      # legenda existe
    assert "Chuveiro" not in svg                                 # e nao mente
    # sem sprinklers, o resumo NAO cita reserva
    assert "Reserva:" not in svg


def test_legenda_da_planta_de_incendio_so_traz_o_que_foi_desenhado():
    """Baseline nos dois sentidos: com o equipamento, a legenda o traz."""
    com = gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                     "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                     "deteccao": {"viga_m": 0.0},
                     "sprinklers": {"altura_estoque_m": 3.0},
                     "hidrantes": {"tipo": "2"}})
    svg_com = di.planta_seguranca_svg(com)
    assert com["gates"]["sprinklers"]["N_chuveiros"] > 0
    assert "Chuveiro automatico" in svg_com
    if com["gates"]["hidrantes"]["N_hidrantes"]:
        assert "Hidrante" in svg_com
    else:                                       # sem hidrante projetado
        assert "Hidrante (NBR 13714)" not in svg_com
        assert "Hidrantes: nao calculados" in svg_com  # G145 declara no RESUMO

    sem = gsi.rodar({"geometria": {"L": 30.0, "W": 15.0, "H": 5.0},
                     "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0}})
    svg_sem = di.planta_seguranca_svg(sem)
    assert not sem["gates"]["hidrantes"]["N_hidrantes"]
    assert "Hidrante (NBR 13714)" not in svg_sem  # legenda: o defeito que o G77 achou
    assert "Hidrantes: nao calculados" in svg_sem  # G145: o RESUMO declara, nunca 0


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
    assert len(res.get("pranchas", [])) == 3, res
    pdfs = [a for a in res.get("arquivos", []) if a.endswith(".pdf")]
    assert len(pdfs) == 3 and all(os.path.exists(p) and os.path.getsize(p) > 0
                                 for p in pdfs), res


def test_caixa_da_legenda_nao_invade_o_quadro_resumo():
    """A legenda cresce com o numero de itens; o RESUMO fica logo abaixo.

    Guarda geometrica (mede o retangulo, nao o texto): mesmo com a legenda
    mais cheia que a planta consegue produzir, a caixa termina antes de o
    quadro-resumo comecar.
    """
    import xml.etree.ElementTree as ET

    r = gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                   "deteccao": {"viga_m": 0.0},
                   "sprinklers": {"altura_estoque_m": 3.0},
                   "hidrantes": {"tipo": "2"}})
    raiz = ET.fromstring(di.planta_seguranca_svg(r))
    ns = "{http://www.w3.org/2000/svg}"
    caixas = [(float(e.get("y")), float(e.get("y")) + float(e.get("height")))
              for e in raiz.iter(ns + "rect")
              if e.get("x") == "730" and e.get("width") == "230"]
    assert len(caixas) == 2, caixas              # legenda e resumo
    (topo_leg, base_leg), (topo_res, _b) = sorted(caixas)
    assert base_leg < topo_res, (base_leg, topo_res)
