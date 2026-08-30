"""Planta de formas/armacao da laje: DESENHO x DADOS.

A barra verde nao cobre o artefato final. Duas licoes do projeto guiam este
arquivo: (1) o SVG tem de ser XML BEM-FORMADO e PARSEAVEL, nao apenas conter as
substrings certas (o unifilar saiu quebrado em S41 porque ~1281 testes so
checavam substring); (2) o desenho tem de bater com os DADOS - foi comparando a
planta (que mostrava DUAS faixas de armadura negativa no caso 9) com o quadro de
ferros (que contava UM conjunto) que apareceu o erro de contagem das barras
negativas, corrigido em quadro_de_ferros.
"""

import xml.dom.minidom as md

import pytest

import desenho_concreto as dc
import laje_concreto as lj

FCK, FYK = 20e3, 500e3


def _laje(caso=4, **over):
    cfg = dict(lx=4.0, ly=6.0, h=0.12, fck=FCK, fyk=FYK, caso=caso, g=0.56,
               q=3.0, phi_mm=10.0)
    cfg.update(over)
    return lj.verifica_laje(cfg)


def _dom(svg):
    return md.parseString(svg)


@pytest.mark.parametrize("caso", [1, 2, 3, 4, 5, 6, 7, 8, 9])
def test_svg_e_xml_bem_formado_em_todos_os_casos(caso):
    dom = _dom(dc.planta_laje_svg(_laje(caso)))
    assert dom.documentElement.tagName == "svg"


def test_svg_de_laje_armada_em_uma_direcao_tambem_e_bem_formado():
    r = _laje(caso=1, lx=2.0, ly=6.0, h=0.10)
    assert r["duas_direcoes"] is False
    dom = _dom(dc.planta_laje_svg(r))
    assert dom.documentElement.tagName == "svg"


def test_texto_do_desenho_e_escapado():
    """Um '<' cru quebra o SVG inteiro em renderers estritos. Injetando um rotulo
    perigoso no quadro de ferros, o desenho tem de continuar PARSEAVEL e o texto
    tem de sair escapado (o mesmo bug do unifilar em S41)."""
    r = _laje()
    q = lj.quadro_de_ferros(r)
    q[0] = dict(q[0], pos="N1 <A&B>")
    svg = dc.planta_laje_svg(r, q)
    dom = _dom(svg)                       # a garantia real: parseia
    textos = [n.firstChild.nodeValue for n in dom.getElementsByTagName("text")
              if n.firstChild]
    assert "N1 <A&B>" in textos           # o parser devolve o texto original
    assert "&lt;A&amp;B&gt;" in svg       # ... porque foi escapado na fonte


def _rects_por_cor(svg, cor):
    dom = _dom(svg)
    return [n for n in dom.getElementsByTagName("rect")
            if n.getAttribute("fill") == cor]


@pytest.mark.parametrize("caso,n_faixas", [(1, 0), (2, 1), (3, 1), (4, 2),
                                           (5, 2), (6, 2), (7, 3), (9, 4)])
def test_uma_faixa_de_armadura_negativa_por_borda_engastada(caso, n_faixas):
    """DESENHO x DADOS: a quantidade de faixas vermelhas tem de ser exatamente a
    quantidade de bordas engastadas do caso."""
    svg = dc.planta_laje_svg(_laje(caso))
    assert len(_rects_por_cor(svg, "#fbe4e4")) == n_faixas
    assert len(lj.ENGASTES[caso]) == n_faixas


def test_faixa_negativa_nao_usa_fill_opacity():
    """fill-opacity nao e honrado por renderizadores estritos (QtSvg/TechDraw/
    svglib): a faixa virava um bloco solido que apagava a malha. Visto ao ABRIR
    o PNG - por isso a cor e solida e clara."""
    assert "fill-opacity" not in dc.planta_laje_svg(_laje())


def test_desenho_declara_o_mesmo_peso_de_aco_do_quadro():
    """O total impresso na prancha tem de ser o total calculado (o quadro de
    materiais ja sumiu em silencio uma vez neste projeto)."""
    r = _laje(caso=9)
    q = lj.quadro_de_ferros(r)
    svg = dc.planta_laje_svg(r, q)
    assert "TOTAL %.1f kg" % lj.peso_total_aco(q) in svg
    for f in q:
        assert f["pos"] in svg


def test_chamadas_das_posicoes_ficam_dentro_do_painel():
    """As chamadas N1..N4 nao podem vazar do painel (a de N3 saia metade fora
    quando a faixa de 0,25 lx e estreita)."""
    dom = _dom(dc.planta_laje_svg(_laje(caso=9, lx=2.0, ly=4.0)))
    painel = max((n for n in dom.getElementsByTagName("rect")
                  if n.getAttribute("stroke-width") == "3"),
                 key=lambda n: float(n.getAttribute("width")))
    x0 = float(painel.getAttribute("x"))
    x1 = x0 + float(painel.getAttribute("width"))
    caixas = [n for n in dom.getElementsByTagName("rect")
              if n.getAttribute("height") == "16"]
    assert caixas
    for c in caixas:
        cx0 = float(c.getAttribute("x"))
        cx1 = cx0 + float(c.getAttribute("width"))
        assert x0 - 1 <= cx0 and cx1 <= x1 + 1, (cx0, cx1, x0, x1)


def test_veredito_do_desenho_acompanha_o_calculo():
    ok = _laje(caso=9)
    ruim = _laje(caso=1, lx=7.0, ly=7.0, h=0.08, q=8.0)
    assert ok["OK"] is True and "RESULTADO: ATENDE" in dc.planta_laje_svg(ok)
    assert ruim["OK"] is False and "RESULTADO: NAO ATENDE" in dc.planta_laje_svg(ruim)


def test_gerar_planta_laje_escreve_arquivo(tmp_path):
    caminho = tmp_path / "laje.svg"
    dc.gerar_planta_laje(_laje(), str(caminho))
    conteudo = caminho.read_text(encoding="utf-8")
    _dom(conteudo)
    assert conteudo.startswith("<svg")


# ---------------------------------------------------------------------------
# Quadro de ferros (o dado que alimenta o desenho e o orcamento)
# ---------------------------------------------------------------------------

def test_barras_negativas_contam_uma_vez_por_borda_engastada():
    """O erro que o desenho revelou: no caso 9 ha DUAS bordas engastadas em cada
    direcao, logo dois conjuntos de barras negativas."""
    um = lj.quadro_de_ferros(_laje(caso=3))       # so x0 engastada
    dois = lj.quadro_de_ferros(_laje(caso=6))     # x0 e x1 engastadas
    n3_um = next(f for f in um if f["pos"] == "N3")
    n3_dois = next(f for f in dois if f["pos"] == "N3")
    assert n3_um["n_bordas"] == 1 and n3_dois["n_bordas"] == 2
    assert n3_dois["n"] == 2 * (n3_dois["n"] // 2)


def test_comprimentos_das_barras_seguem_o_criterio_do_livro():
    """Positiva: l - 2c + 2g (600 - 2*6 + 2*7 = 602 cm no exemplo do Cap.7).
    Negativa: 0,25 lx para dentro de cada laje + ancoragem reta nas pontas."""
    assert lj.comprimento_positivo(6.00) == pytest.approx(6.02)
    assert lj.comprimento_positivo(4.00) == pytest.approx(4.02)
    lb = lj.ancoragem_laje(10.0, FCK, FYK, gancho=False)["lb_nec_mm"] / 1000.0
    assert lj.comprimento_negativo(4.0, 4.0, 10.0, FCK, FYK) == pytest.approx(
        0.25 * 8.0 + 2 * lb)


def test_taxa_de_aco_fica_na_ordem_de_grandeza_de_uma_laje():
    """Sanidade de grandeza (rotulo x geometria): laje macica de edificio fica
    tipicamente entre 3 e 12 kg/m2. Um erro de fator 2 na contagem sai daqui."""
    for caso in (1, 4, 9):
        r = _laje(caso)
        taxa = lj.peso_total_aco(lj.quadro_de_ferros(r)) / (r["lx"] * r["ly"])
        assert 3.0 <= taxa <= 12.0, (caso, taxa)


def test_mais_engastes_significa_mais_aco():
    def taxa(caso):
        r = _laje(caso)
        return lj.peso_total_aco(lj.quadro_de_ferros(r)) / (r["lx"] * r["ly"])
    assert taxa(1) < taxa(3) < taxa(9)
