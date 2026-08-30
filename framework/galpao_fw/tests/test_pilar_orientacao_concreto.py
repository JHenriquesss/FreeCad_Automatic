# ============================================================================
# test_pilar_orientacao_concreto.py - O EIXO FORTE TEM QUE ESTAR NO PLANO DO
# PORTICO. Achado em G7 abrindo a planta de formas (renderizar-e-olhar): o pilar
# saia desenhado com hy (25 cm) na direcao do vao e hx (50 cm) na longitudinal -
# girado 90 graus. O CALCULO estava certo (dimensiona_pilar recebe h=hx como a
# direcao do momento); quem errava era o que a obra le e o que o BIM entrega.
# Mesma familia do bug #35 (coluna de aco com eixo fraco no plano do portico).
# Testes GEOMETRICOS: medem o retangulo, nao procuram string.
# ============================================================================
"""Orientacao do pilar de concreto na planta de formas e no BIM."""

import os
import re
import sys
import xml.dom.minidom as md

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import desenho_concreto as dc
import galpao_concreto as gc


@pytest.fixture(scope="module")
def r():
    return gc.rodar({"vao": 20.0, "comprimento": 40.0, "n_porticos": 7, "pe_direito": 6.0, "v0": 40.0,
                     "cat": "IV", "classe": "B", "s1": 1.0, "s3": 1.0,
                     "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
                     "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"})


def test_a_secao_do_pilar_e_mesmo_assimetrica(r):
    # se hx == hy o teste de orientacao nao provaria nada
    assert r["pilar"]["hx"] > r["pilar"]["hy"]


def test_pilar_na_planta_e_mais_largo_no_vao_do_que_no_comprimento(r):
    svg = dc.planta_formas_svg(r)
    doc = md.parseString(svg)                      # e XML valido
    # o pilar e o retangulo preenchido escuro (fill #555)
    pilares = [n for n in doc.getElementsByTagName("rect")
               if n.getAttribute("fill") == "#555"]
    assert len(pilares) == 2 * r["spec"]["n_porticos"]
    hx, hy = r["pilar"]["hx"], r["pilar"]["hy"]
    for p in pilares:
        w = float(p.getAttribute("width")); h = float(p.getAttribute("height"))
        # papel: X = vao. hx (plano do portico) tem que ser a LARGURA.
        assert w > h, "pilar girado 90 graus na planta de formas (w=%s h=%s)" % (w, h)
        assert abs(w / h - hx / hy) < 0.02


def test_pilar_no_bim_tem_o_eixo_forte_no_plano_do_portico(r):
    membros = gc.membros_bim(r)
    colunas = [m for m in membros if m["tipo"] == "Column"]
    assert colunas
    hx, hy = r["pilar"]["hx"], r["pilar"]["hy"]
    for c in colunas:
        # convencao do _aabb/emissor: bf no eixo X global (= vao), d no eixo Y
        assert c["secao"]["bf"] == hx and c["secao"]["d"] == hy


def test_aabb_do_pilar_mede_hx_na_direcao_do_vao(r):
    coluna = next(m for m in gc.membros_bim(r) if m["tipo"] == "Column")
    x0, x1, y0, y1, _z0, _z1 = gc._aabb(coluna)
    dx, dy = x1 - x0, y1 - y0                       # mm
    assert abs(dx - r["pilar"]["hx"] * 1000.0) < 1.0
    assert abs(dy - r["pilar"]["hy"] * 1000.0) < 1.0
    assert dx > dy


# --------------------- a prancha nao inventa nem omite aco --------------------
def _grupos(svg):
    """(n_circulos, rotulo) por grupo da prancha de armacao."""
    doc = md.parseString(svg)
    saida = []
    for g in doc.getElementsByTagName("g"):
        textos = [t.firstChild.data for t in g.getElementsByTagName("text")
                  if t.firstChild]
        rot = next((t for t in textos
                    if t.startswith(("PILAR", "VIGA", "SAPATA"))), "")
        saida.append((len(g.getElementsByTagName("circle")), rot))
    return saida


def test_viga_protendida_aparece_como_protendida_na_prancha(r):
    # vao de 20 m -> viga protendida (arr_inf/arr_sup None). A prancha rotulava
    # "inf 0 f0.0" e caia num fallback que desenhava 2 f10 INEXISTENTES.
    assert r["tipo_viga"] == "protendida" and r["viga"]["n_cordoalhas"]
    n_circ, rot = next(g for g in _grupos(dc.prancha_armacao_svg(r))
                       if g[1].startswith("VIGA"))
    assert "PROTENDIDA" in rot and "f0.0" not in rot
    assert n_circ == r["viga"]["n_cordoalhas"]        # rotulo x geometria


def test_barras_desenhadas_do_pilar_batem_com_o_rotulo(r):
    n_circ, rot = next(g for g in _grupos(dc.prancha_armacao_svg(r))
                       if g[1].startswith("PILAR"))
    n_rotulo = int(re.search(r"- (\d+) f", rot).group(1))
    assert n_circ == n_rotulo


def test_viga_armada_continua_mostrando_a_armadura_passiva(r):
    # mesma prancha com viga CONVENCIONAL: o caminho passivo nao pode ter sido
    # perdido no conserto do caminho protendido.
    import copy
    r2 = copy.deepcopy(r)
    r2["tipo_viga"] = "convencional"
    r2["viga"].update({"protendida": False, "n_cordoalhas": 0,
                       "arr_inf": {"n": 4, "phi": 16.0}, "arr_sup": None,
                       "As_inf_cm2": 8.0})
    n_circ, rot = next(g for g in _grupos(dc.prancha_armacao_svg(r2))
                       if g[1].startswith("VIGA"))
    assert "inf 4 f16.0" in rot and n_circ == 4
