"""Testes da planta de formas do pavimento-tipo.

Tres guardas, cada uma correspondendo a um achado real do historico do projeto:

1. PARSE, nao substring. O SVG e XML; um '<' cru quebra o desenho inteiro em
   renderizadores estritos (QtSvg/TechDraw). Procurar a string no arquivo passa
   mesmo com o XML malformado - por isso aqui se faz ET.fromstring.
2. DRAWING-VS-DATA. O laco de desenho tem de emitir exatamente tantos pilares e
   paineis quantos existem nos dados. Um laco que recalcula a contagem por conta
   propria (cols*rows) desenha uma grade que nao e a calculada.
3. COLISAO GEOMETRICA DE TEXTO. Um rotulo desenhado por baixo do quadro de cargas
   esta no arquivo e nao se ve. A checagem tem de ser de geometria, nao de string.
"""

import xml.etree.ElementTree as ET

import pytest

import descida_cargas as dc
import desenho_pavimento as dp
import pavimento_tipo as pt

NS = "{http://www.w3.org/2000/svg}"


def _tipo(**kw):
    base = {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5], "h_laje": 0.10,
            "uso": "residencial_dormitorio", "b_viga": 0.20, "h_viga": 0.50,
            "fck": 30e3, "fyk": 500e3, "pe_direito": 2.90}
    base.update(kw)
    return base


def _pav(**kw):
    return pt.monta(_tipo(**kw))


def _root(svg):
    return ET.fromstring(svg)


# ---------------------------------------------------------------------------
# 1. o SVG e XML
# ---------------------------------------------------------------------------
def test_svg_e_xml_valido():
    root = _root(dp.planta_formas_svg(_pav()))
    assert root.tag == NS + "svg"


def test_svg_continua_xml_com_rotulos_que_tem_caracteres_perigosos():
    """Se algum rotulo trouxer '<' ou '&', o escape tem de segurar. A planta usa
    desenho_svg_base.esc em todo texto justamente por isso."""
    pav = _pav()
    pav["pilares"][0]["posicao"] = "canto <interno> & externo"
    root = _root(dp.planta_formas_svg(pav))
    assert root.tag == NS + "svg"


# ---------------------------------------------------------------------------
# 2. drawing-vs-data
# ---------------------------------------------------------------------------
def test_desenha_exatamente_os_pilares_dos_dados():
    pav = _pav()
    root = _root(dp.planta_formas_svg(pav))
    rects = root.findall(".//" + NS + "rect")
    desenhados = sum(1 for r in rects if r.get("fill") == dp.COR_PILAR)
    assert desenhados == dp.confere_desenho(pav)["n_pilares"] == len(pav["pilares"])


def test_desenha_exatamente_os_paineis_dos_dados():
    pav = _pav()
    root = _root(dp.planta_formas_svg(pav))
    rects = root.findall(".//" + NS + "rect")
    desenhados = sum(1 for r in rects if r.get("fill") == dp.COR_LAJE)
    assert desenhados == dp.confere_desenho(pav)["n_paineis"] == len(pav["paineis"])


@pytest.mark.parametrize("vx,vy", [([5.0], [4.0]), ([4.0, 4.0], [4.0]),
                                   ([6.0, 3.0, 5.0], [4.5, 3.0, 5.5]),
                                   ([4.0] * 4, [4.0] * 3)])
def test_contagens_batem_em_varias_malhas(vx, vy):
    pav = _pav(vaos_x=vx, vaos_y=vy)
    root = _root(dp.planta_formas_svg(pav))
    rects = root.findall(".//" + NS + "rect")
    c = dp.confere_desenho(pav)
    assert sum(1 for r in rects if r.get("fill") == dp.COR_PILAR) == c["n_pilares"]
    assert sum(1 for r in rects if r.get("fill") == dp.COR_LAJE) == c["n_paineis"]


def test_todo_pilar_aparece_nomeado_no_desenho():
    pav = _pav()
    textos = {t.text for t in _root(dp.planta_formas_svg(pav)).findall(".//" + NS + "text")}
    for p in pav["pilares"]:
        assert p["nome"] in textos, p["nome"]


def test_caso_de_vinculacao_de_cada_painel_aparece():
    pav = _pav()
    textos = [t.text for t in _root(dp.planta_formas_svg(pav)).findall(".//" + NS + "text")]
    for p in pav["paineis"]:
        assert ("caso %d" % p["caso"]) in textos


# ---------------------------------------------------------------------------
# 3. colisao geometrica de texto
# ---------------------------------------------------------------------------
def test_nenhum_rotulo_de_pilar_invade_o_quadro_de_cargas():
    """Foi o que o RENDERIZAR-E-OLHAR pegou: os rotulos da ultima coluna (P41/P42/P43)
    eram desenhados a direita do pilar e avancavam por baixo do quadro de cargas,
    saindo cortados. A string estava no SVG e todos os testes de substring passavam."""
    assert dp.colisoes_de_rotulo(_pav()) == []


@pytest.mark.parametrize("vx,vy", [([5.0], [4.0]), ([4.0, 4.0], [4.0]),
                                   ([6.0, 3.0, 5.0], [4.5, 3.0, 5.5]),
                                   ([4.0] * 4, [4.0] * 3), ([3.0] * 5, [3.0] * 4)])
def test_sem_colisao_em_varias_malhas(vx, vy):
    assert dp.colisoes_de_rotulo(_pav(vaos_x=vx, vaos_y=vy)) == []


def test_a_guarda_de_colisao_realmente_detecta():
    """Guarda da guarda: com o quadro deslocado para cima do desenho, a checagem tem
    de acusar. Um detector que nunca acusa nada nao protege de nada."""
    pav = _pav()
    d = dp.caixas_de_rotulo(pav)
    qx0 = d["quadro"][0]
    invasores = [r["nome"] for r in d["rotulos"] if r["caixa"][2] > qx0 - 400]
    assert invasores, "com o limite deslocado 400 px, algum rotulo tem de cair dentro"


def test_desenho_cabe_na_area_util():
    d = dp.caixas_de_rotulo(_pav())
    x0, y0, x1, y1 = d["limites_desenho"]
    assert x1 <= d["quadro"][0]
    assert x0 > 0 and y0 > 0


# ---------------------------------------------------------------------------
# integracao: quadro com a descida de cargas
# ---------------------------------------------------------------------------
def test_quadro_mostra_a_carga_da_descida_quando_ela_e_dada():
    tipo = _tipo()
    pav = pt.monta(tipo)
    pavs = ([{"nome": "Cobertura", "pavimento": _tipo(uso="cobertura_manutencao")}]
            + [{"nome": "Tipo %d" % i, "pavimento": tipo} for i in range(8, 0, -1)])
    d = dc.descer({"pavimentos": pavs})
    svg = dp.planta_formas_svg(pav, d)
    root = _root(svg)
    textos = [t.text for t in root.findall(".//" + NS + "text")]
    assert "CARGA NA BASE DO PILAR (kN)" in textos
    # o valor do pilar interno da descida (bem maior que o de um pavimento so)
    n_base = d["pilares"]["P22"]["N_base_k"]
    assert "%.1f" % n_base in textos
    assert n_base > pav["pilares"][0]["N_k"] * 5


def test_sem_descida_o_quadro_mostra_o_pavimento():
    textos = [t.text for t in _root(dp.planta_formas_svg(_pav())).findall(".//" + NS + "text")]
    assert "CARGA DO PAVIMENTO POR PILAR (kN)" in textos


def test_gerar_arquivo(tmp_path):
    p = dp.gerar_planta_formas(_pav(), str(tmp_path / "planta.svg"))
    with open(p, encoding="utf-8") as f:
        root = ET.fromstring(f.read())
    assert root.tag == NS + "svg"
