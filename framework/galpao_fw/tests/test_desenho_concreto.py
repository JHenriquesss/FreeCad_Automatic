"""Desenho de formas + armacao (SVG) do galpao de concreto - desenho_concreto.py.

Puro-Python (sem FreeCAD). Alem de bem-formado, o SVG precisa CABER na prancha: a
sapata e em metros e, sem escala propria, estourava o canvas e cobria a viga (bug
pego na verificacao visual). O guard de bounding-box abaixo trava essa regressao.
"""
import os
import re
import sys
import xml.dom.minidom as md

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import galpao_concreto as gc
import desenho_concreto as dc


def _r():
    return gc.rodar({"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
                     "v0": 40.0, "cat": "IV", "classe": "B", "G_roof": 0.30,
                     "Q_roof": 0.25, "fck": 30e3, "sigma_solo_adm": 250.0})


def test_svg_bem_formado_e_tres_secoes():
    svg = dc.prancha_armacao_svg(_r())
    dom = md.parseString(svg)
    assert dom.documentElement.tagName == "svg"
    for marca in ("PILAR", "VIGA COB.", "SAPATA"):
        assert marca in svg, marca


def test_desenha_barras_do_pilar():
    svg = dc.prancha_armacao_svg(_r())
    assert svg.count("<circle") >= 4               # barras longitudinais


def test_tudo_cabe_no_canvas():
    # REGRESSAO: a sapata (metros) tem que ser reescalada p/ caber. Nenhuma coord
    # x de rect/circle/line pode passar da largura do SVG.
    svg = dc.prancha_armacao_svg(_r())
    W = int(re.search(r'width="(\d+)"', svg).group(1))
    xs = [float(v) for v in re.findall(r'[ (]x="([\d.]+)"', svg)]
    xs += [float(v) for v in re.findall(r'cx="([\d.]+)"', svg)]
    xs += [float(v) for v in re.findall(r'x1="([\d.]+)"', svg)]
    xs += [float(v) for v in re.findall(r'x2="([\d.]+)"', svg)]
    # tolerancia p/ a largura de um retangulo desenhado a partir de x
    largs = [float(v) for v in re.findall(r'width="([\d.]+)"', svg)]
    assert max(xs) <= W + 5, (max(xs), W)
    # a maior largura de elemento interno nao pode exceder o canvas
    assert max(largs) <= W + 1


def test_gera_arquivo_svg(tmp_path):
    p = str(tmp_path / "armacao.svg")
    dc.gerar_prancha(_r(), p)
    assert os.path.getsize(p) > 500
    md.parse(p)                                     # abre e valida como XML


def test_planta_formas_bem_formada_e_completa():
    r = _r()
    svg = dc.planta_formas_svg(r)
    dom = md.parseString(svg)
    assert dom.documentElement.tagName == "svg"
    assert "PLANTA DE FORMAS" in svg
    # 2 pilares por portico -> 14 pilares (rects escuros) + 14 sapatas + contorno
    n_port = r["spec"]["n_porticos"]
    assert svg.count("<rect") >= 2 * n_port          # ao menos 1 rect por pilar
    # 1 viga (linha) por portico
    assert svg.count('stroke="#888"') >= n_port


def test_planta_cabe_no_canvas():
    svg = dc.planta_formas_svg(_r())
    W = int(re.search(r'width="(\d+)"', svg).group(1))
    H = int(re.search(r'height="(\d+)"', svg).group(1))
    xs = [float(v) for v in re.findall(r'[ (]x="([-\d.]+)"', svg)]
    xs += [float(v) for v in re.findall(r'cx="([-\d.]+)"', svg)]
    ys = [float(v) for v in re.findall(r'[ (]y="([-\d.]+)"', svg)]
    ys += [float(v) for v in re.findall(r'cy="([-\d.]+)"', svg)]
    assert min(xs) >= -1 and max(xs) <= W + 5
    assert min(ys) >= -1 and max(ys) <= H + 5


def test_gera_planta_formas_arquivo(tmp_path):
    p = str(tmp_path / "planta.svg")
    dc.gerar_planta_formas(_r(), p)
    assert os.path.getsize(p) > 500
    md.parse(p)


def test_selftest_roda():
    dc._selftest()
