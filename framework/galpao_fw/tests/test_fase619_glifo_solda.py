# ============================================================================
# test_fase619_glifo_solda.py - RED tests da Fase 6.19.
# Simbolo grafico AWS de solda de filete (SVG) para os detalhes de ligacao,
# renderizado headless via DrawViewSymbol (substitui o DrawWeldSymbol so-GUI).
# Testa o gerador de SVG (puro); o render foi validado visualmente (PE14/PE11).
# ============================================================================
import os
import sys
import xml.dom.minidom as minidom

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import techdraw_exec as TD


def test_svg_bem_formado():
    s = TD._svg_solda_filete(6.0)
    d = minidom.parseString(s)                # nao lanca -> XML valido
    assert d.documentElement.tagName == "svg"


def test_svg_contem_perna_e_triangulo():
    s = TD._svg_solda_filete(8.0)
    assert ">8<" in s                         # perna renderizada
    assert "polygon" in s                     # triangulo do filete + seta
    assert "<line" in s                       # linha de referencia


def test_svg_todo_contorno_adiciona_circulo():
    assert "circle" not in TD._svg_solda_filete(6.0)
    assert "circle" in TD._svg_solda_filete(6.0, todo_contorno=True)


def test_svg_campo_adiciona_bandeira():
    base = TD._svg_solda_filete(6.0)
    campo = TD._svg_solda_filete(6.0, campo=True)
    assert campo.count("path") > base.count("path")   # bandeira = <path>


def test_svg_sem_perna_omite_texto():
    s = TD._svg_solda_filete(0)
    assert "<text" not in s                   # sem perna -> sem numero
