# G79: terraplenagem calcula e nao desenha - PE-TP-01 e PE-TP-02.
"""As duas folhas leem o que terraplenagem.py ja calcula. Count-driven por
PARSE (nunca substring): celulas desenhadas == celulas da malha; canaletas
desenhadas == dimensionadas. Baseline nos dois sentidos: cada portao tem o
caso bom (verde) e o defeito injetado EM MEMORIA (vermelho) - nunca mutando
o repo (convecao 2). Valores de comparacao sao contas a mao (fonte
independente, convecao 5), nunca o proprio desenho."""
import sys
import os
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import pytest

import desenho_svg_base as sb
import desenho_terraplenagem as dt
import terraplenagem as tp

GRID = [[102.3, 101.8, 101.2], [101.5, 101.0, 100.4], [100.6, 100.1, 99.5]]
COTA = 101.0
AREA = 400.0
EMP = 1.25
CASO = {"C": 0.75, "i_mm_h": 130.0, "area_ha": 1.2,
        "largura_canaleta_m": 0.4, "declividade": 0.008}


def _dados_tp01():
    vols = tp.volumes_corte_aterro(GRID, COTA, AREA)
    return {"grid_terreno": GRID, "cota_plataforma": COTA,
            "area_celula_m2": AREA, "empolamento": EMP, "volumes": vols,
            "greide": tp.greide_equilibrio(GRID, AREA, empolamento=EMP),
            "movimento": tp.movimento_terra(vols["corte_m3"], vols["aterro_m3"],
                                            EMP)}


def _dados_tp02():
    return {"caso": dict(CASO), "resultado": tp.dimensiona_drenagem(CASO)}


def _conta(svg, attr):
    raiz = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    n = 0
    for tag in ("rect", "line"):
        for el in list(raiz.iter(ns + tag)) + list(raiz.iter(tag)):
            if el.get(attr) is not None:
                n += 1
    return n


# --- escada degrau 2: parse + guarda ---------------------------------------

def test_tp01_passa_na_guarda():
    svg = dt.mapa_corte_aterro_svg(_dados_tp01())
    ET.fromstring(svg)
    c = sb.confere_folha_svg(svg)
    assert c["ok"], c["motivo"]


def test_tp02_passa_na_guarda():
    svg = dt.planta_drenagem_svg(_dados_tp02())
    ET.fromstring(svg)
    c = sb.confere_folha_svg(svg)
    assert c["ok"], c["motivo"]


# --- drawing-vs-data count-driven, baseline nos dois sentidos ---------------

def test_tp01_celulas_desenhadas_iguais_as_da_malha():
    svg = dt.mapa_corte_aterro_svg(_dados_tp01())
    assert _conta(svg, "data-celula") == 9 == len(GRID) * len(GRID[0])


def test_tp01_portao_acusa_celula_faltando():
    """Vermelho por injecao (em memoria): uma celula removida do XML."""
    svg = dt.mapa_corte_aterro_svg(_dados_tp01())
    raiz = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    for el in list(raiz.iter(ns + "rect")) + list(raiz.iter("rect")):
        if el.get("data-celula") == "0-0":
            # esvazia a marca da celula (o desenho perdeu uma celula)
            del el.attrib["data-celula"]
            break
    import io
    buf = io.BytesIO()
    ET.ElementTree(raiz).write(buf, encoding="utf-8", xml_declaration=False)
    svg_inj = buf.getvalue().decode("utf-8")
    assert _conta(svg_inj, "data-celula") == 8
    assert _conta(svg_inj, "data-celula") != 9  # o portao acusaria


def test_tp02_canaletas_desenhadas_iguais_as_dimensionadas():
    dados = _dados_tp02()
    dados["trechos"] = [{"nome": "C1"}, {"nome": "C2"}]
    svg = dt.planta_drenagem_svg(dados)
    # 2 linhas de planta com data-canaleta (a secao usa outro valor)
    raiz = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    linhas = [el for tag in ("line",)
               for el in list(raiz.iter(ns + tag)) + list(raiz.iter(tag))
               if el.get("data-canaleta") in ("C1", "C2")]
    assert len(linhas) == 2 == len(dados["trechos"])


def test_tp02_portao_acusa_canaleta_faltando():
    """Vermelho por injecao: trecho dimensionado sem linha desenhada."""
    dados = _dados_tp02()
    dados["trechos"] = [{"nome": "C1"}, {"nome": "C2"}]
    svg = dt.planta_drenagem_svg(dados)
    svg_inj = svg.replace('data-canaleta="C2"', 'data-canaleta="X"')
    assert _conta(svg_inj, "data-canaleta") == _conta(svg, "data-canaleta")
    raiz = ET.fromstring(svg_inj)
    ns = "{http://www.w3.org/2000/svg}"
    nomes = {el.get("data-canaleta")
             for tag in ("line",)
             for el in list(raiz.iter(ns + tag)) + list(raiz.iter(tag))}
    assert "C2" not in nomes  # o portao (por nome) acusaria a falta


# --- fonte independente (convencao 5): conta a mao --------------------------

def test_tp01_quadro_bate_com_conta_a_mao():
    """Grade 2x2 plana em 10, plataforma 8, area 100 -> corte 800, aterro 0
    (conta a mao, nao o desenho)."""
    grid = [[10.0, 10.0], [10.0, 10.0]]
    svg = dt.mapa_corte_aterro_svg(
        {"grid_terreno": grid, "cota_plataforma": 8.0,
         "area_celula_m2": 100.0, "empolamento": 1.0,
         "volumes": tp.volumes_corte_aterro(grid, 8.0, 100.0),
         "greide": tp.greide_equilibrio(grid, 100.0, empolamento=1.0),
         "movimento": tp.movimento_terra(800.0, 0.0, 1.0)})
    assert "800.0 m3" in svg
    assert "0.0 m3" in svg


def test_tp02_quadro_bate_com_conta_a_mao():
    """Q = C.i.A/360 = 0.75*130*1.2/360 = 0.325 m3/s (conta a mao)."""
    svg = dt.planta_drenagem_svg(_dados_tp02())
    assert "0.3250 m3/s" in svg
    assert "b=0.40 m" in svg


# --- saturacao silenciosa (convencao 4): veredito aparece --------------------

def test_tp02_canaleta_insuficiente_carimba_reprova():
    caso = {"C": 0.9, "i_mm_h": 200.0, "area_ha": 5.0,
            "largura_canaleta_m": 0.3, "declividade": 0.005,
            "altura_max_m": 0.5}
    res = tp.dimensiona_drenagem(caso)
    assert res["canaleta"]["OK"] is False
    svg = dt.planta_drenagem_svg({"caso": caso, "resultado": res})
    ET.fromstring(svg)
    assert sb.confere_folha_svg(svg)["ok"]
    assert "INSUFICIENTE" in svg and "REPROVA" in svg
    assert ">OK<" not in svg  # o veredito ruim aparece, nao some


def test_tp01_empolamento_ausente_nao_vira_default_silencioso():
    dados = {"grid_terreno": GRID, "cota_plataforma": COTA,
             "area_celula_m2": AREA}
    svg = dt.mapa_corte_aterro_svg(dados)
    ET.fromstring(svg)
    assert sb.confere_folha_svg(svg)["ok"]
    assert "... nao declarado" in svg


# ===========================================================================
# G89: o laco indice<->disco. O G79 entregou os dois emissores, registrou em
# FOLHAS e parou ai: nenhum adaptador os importava, e `desenho_terraplenagem`
# era ILHA (a propria test_alcancabilidade acusou). Os testes acima provam
# que a folha esta CERTA; estes provam que ela SAI. Sem eles, arrancar a
# ligacao em `entregaveis_projeto.emitir_obras_sitio` deixa a suite verde -
# que e exatamente como o buraco nasceu.
# ===========================================================================
def _emite_sitio(tmp_path, terra_cfg):
    import project_loop                                    # registra adaptadores
    assert project_loop is not None
    import entregaveis_projeto as ep
    manifest = {"deliverables": {}, "artifacts": []}
    ep.emitir_obras_sitio(manifest, tmp_path,
                          {"site": {"terraplenagem": terra_cfg}}, None, {})
    return manifest["deliverables"]["obras_sitio"]


def _cfg_completo():
    return {"grid_terreno": GRID, "cota_plataforma": COTA,
            "area_celula_m2": AREA, "empolamento": EMP,
            "greide_equilibrio": True, "drenagem": dict(CASO)}


def test_g89_obras_sitio_emite_as_duas_folhas_no_disco(tmp_path):
    """PE-TP-01 e PE-TP-02 chegam ao run_dir, e cada uma passa na guarda de
    folha. Fonte independente: os nomes vem do contrato, nao do resultado."""
    saida = _emite_sitio(tmp_path, _cfg_completo())
    assert saida["status"] == "generated", saida
    assert saida["frentes_com_falha"] == []
    esperados = {"terraplenagem-corte-aterro.svg", "terraplenagem-drenagem.svg"}
    no_disco = {p.name for p in (tmp_path / "drawings").glob("*.svg")}
    assert esperados <= no_disco, no_disco
    # e cada folha entra no manifesto como artefato (senao some do indice)
    artefatos = set(saida["artifacts"])
    for nome in esperados:
        assert "drawings/" + nome in artefatos, artefatos
        svg = (tmp_path / "drawings" / nome).read_text(encoding="utf-8")
        ET.fromstring(svg)
        assert sb.confere_folha_svg(svg)["ok"], nome


def test_g89_frente_ausente_nao_vira_folha_vazia(tmp_path):
    """So a grade declarada: sai PE-TP-01 e NAO sai PE-TP-02. Folha que o
    dado nao sustenta nao e emitida vazia - o outro sentido do baseline."""
    cfg = _cfg_completo()
    cfg.pop("drenagem")
    saida = _emite_sitio(tmp_path, cfg)
    no_disco = {p.name for p in (tmp_path / "drawings").glob("*.svg")}
    assert no_disco == {"terraplenagem-corte-aterro.svg"}, no_disco
    assert saida["frentes_com_falha"] == []


def test_g89_desenho_terraplenagem_nao_e_ilha():
    """Vermelho por injecao do defeito REAL que existia: se ninguem no Loop
    importar o emissor, ele volta a ser ilha. Mede a aresta, nao o texto."""
    import ast
    import pathlib
    fonte = pathlib.Path(GALPAO, "entregaveis_projeto.py").read_text(
        encoding="utf-8")
    nomes = {n.names[0].name for n in ast.walk(ast.parse(fonte))
             if isinstance(n, ast.Import)}
    assert "desenho_terraplenagem" in nomes, (
        "emissor das PE-TP sem importador no Loop: volta a ser ilha "
        "(test_alcancabilidade acusa) e o indice promete folha que nao sai")
