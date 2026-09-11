# G111: a PE-CO-03 desenhava UM painel de seis sem dizer qual.
"""Drawing-vs-data da laje (opcao (a) do goal: todos os paineis detalhados).

A casa do spec persistido tem 6 paineis (vaos_x=[3.5,3.5,3.4],
vaos_y=[4.0,4.0] -> 3x2) e `estrutura["laje"]` e UM dict - o painel
critico `crit` que `estrutura_casa` passa a `dimensiona_laje` para
convergir a espessura. A folha (`desenho_concreto.planta_laje_svg`)
titulava "painel 3.50 x 4.00" sem dizer que e o critico, nem que
existem outros cinco, nem que a armadura deles nao foi detalhada.

Medido antes de escrever "governa" (2026-09-11, carga real do spec:
q=1.0 cobertura_manutencao, h=0.10, fck=25 MPa): `max(area)` empata em
14.0 m2 entre caso 4 (0,0)/(0,1) e caso 8 (1,0)/(1,1); o `max()` pega o
primeiro por ordem - neste spec o caso 4 governa (m_x 2.70 > 2.37,
x_x 6.34 > 5.37 kN.m/m, As_neg 2.18 > 1.83 cm2/m, positivas todas no
minimo 1.01), mas o criterio area nao prova governancia em geral
(caso 8 tem OUTRAS vinculacoes nas mesmas dimensoes). Por isso a
opcao (a): um `dimensiona_laje` por painel, mesma h adotada, um
quadro de ferros por painel - em vez de declarar governancia.

A escada: substring -> parse -> renderizar. A lente CONTA por parse
XML (atributo `data-painel="i,j"` que o emissor novo carimba em cada
grupo de painel), nunca por substring solta; o terceiro degrau
(renderizar-e-olhar) fica no `test_folha_renderiza_e_cabe_no_png`
abaixo (fitz presente: a folha de 6 paineis foi aberta em PNG e lida
em 2026-09-11 - titulo com "critico L11 (1 de 6)", 6 quadros ATENDE,
nada cortado; caso 8 pesa MAIS aco total (59.7 kg) que o caso 4
critico (54.8 kg): "governar" por momento nao e governar por custo -
mais um motivo da opcao (a)).

Convecoes do lote: baseline nos dois sentidos (cada teste tem o lado
vermelho por injecao em `tmp_path`, nunca mutando o repo); `except`
novo registra `type(exc).__name__: exc` no motivo.
"""
import copy
import pathlib
import xml.etree.ElementTree as ET

import pytest

GALPAO = pathlib.Path(__file__).resolve().parents[1]

VAOS_X = [3.5, 3.5, 3.4]
VAOS_Y = [4.0, 4.0]
PAINEIS_ESPERADOS = {(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)}


# ===========================================================================
# a lente: drawing-vs-data por parse XML
# ===========================================================================

def paineis_na_folha(svg):
    """Devolve o conjunto {(i,j)} de paineis que a folha declara.

    Conta por parse XML (grupos `<g data-painel="i,j">`), nunca por
    substring: um `L11` solto no texto nao prova quadro detalhado.
    Folha legada (sem o atributo) devolve o conjunto vazio.
    """
    raiz = ET.fromstring(svg)
    achados = set()
    for el in raiz.iter():
        tag = el.tag
        if isinstance(tag, str) and tag.endswith("}g"):
            tag_g = True
        else:
            tag_g = (tag == "g")
        if not tag_g:
            continue
        dp = el.get("data-painel")
        if dp is None:
            continue
        try:
            i_s, j_s = dp.split(",")
            achados.add((int(i_s), int(j_s)))
        except (ValueError, AttributeError):
            continue
    return achados


def confere_laje_todos_paineis(svg, paineis):
    """A folha lista (desenhados ou detalhados) exatamente os paineis do
    resultado. Devolve {"ok", "motivo", "na_folha", "esperados"}."""
    try:
        na_folha = paineis_na_folha(svg)
    except ET.ParseError as exc:
        return {"ok": False,
                "motivo": "svg-malformado: %s: %s"
                          % (type(exc).__name__, exc),
                "na_folha": set(), "esperados": set(paineis)}
    esperados = {(p["i"], p["j"]) for p in paineis}
    faltando = sorted(esperados - na_folha)
    sobrando = sorted(na_folha - esperados)
    if faltando or sobrando:
        return {"ok": False,
                "motivo": "folha-diz-outra-coisa: faltando=%r sobrando=%r "
                          "(folha tem %d, resultado tem %d)"
                          % (faltando, sobrando, len(na_folha),
                             len(esperados)),
                "na_folha": na_folha, "esperados": esperados}
    return {"ok": True, "motivo": "", "na_folha": na_folha,
            "esperados": esperados}


def _pavimento_6():
    import pavimento_tipo as pt
    cfg = {"vaos_x": list(VAOS_X), "vaos_y": list(VAOS_Y), "h_laje": 0.10,
           "uso": "cobertura_manutencao", "revestimento_kN_m2": 1.0,
           "fck": 25000.0, "fyk": 500000.0}
    return pt.monta(cfg), cfg


# ===========================================================================
# vermelho permanente: a folha legada (1 painel) nunca passa nesta lente
# ===========================================================================

def test_folha_legada_de_um_painel_reprova_na_lente():
    """O defeito do G111, congelado: a folha antiga titula um painel e a
    lente acusa os outros cinco ausentes. Se um dia a legada passar aqui,
    a lente quebrou (assercao tautologica) - nao a folha que melhorou."""
    import desenho_concreto as dc
    import laje_concreto as lj
    pav, _cfg = _pavimento_6()
    assert len(pav["paineis"]) == 6
    crit = max(pav["paineis"], key=lambda p: p["lx"] * p["ly"])
    r = lj.dimensiona_laje({"caso": crit["caso"],
                            "lx": min(crit["lx"], crit["ly"]),
                            "ly": max(crit["lx"], crit["ly"]), "h": 0.10,
                            "g": 1.0, "q": pav["q_kN_m2"],
                            "fck": 25000.0, "fyk": 500000.0})
    svg = dc.planta_laje_svg(r)
    c = confere_laje_todos_paineis(svg, pav["paineis"])
    assert not c["ok"], "a legada passou na lente: %r" % (c,)
    assert "faltando" in c["motivo"] and len(c["na_folha"]) == 0, c


# ===========================================================================
# verde: produtor (mesma h) + folha com os 6 quadros
# ===========================================================================

def test_produtor_detalha_os_6_paineis_com_a_mesma_h():
    """Um `dimensiona_laje` por painel, mesma h adotada; cada resultado
    traz o seu caso de vinculacao (nao o do critico copiado)."""
    import laje_concreto as lj
    pav, cfg = _pavimento_6()
    det = lj.detalha_lajes_por_painel(
        pav["paineis"],
        {"h": 0.10, "g": 1.0, "q": pav["q_kN_m2"], "fck": 25000.0,
         "fyk": 500000.0})
    assert len(det["paineis"]) == len(pav["paineis"]) == 6
    casos = {}
    for item in det["paineis"]:
        r = item["resultado"]
        assert r["h"] == pytest.approx(0.10), (item["painel"], r["h"])
        casos[(item["painel"]["i"], item["painel"]["j"])] = r["caso"]
    assert casos[(0, 0)] == 4 and casos[(1, 0)] == 8, casos
    assert {p["caso"] for p in pav["paineis"]} == set(casos.values())


def test_folha_nova_lista_os_6_paineis_e_passa_na_guarda():
    """O aceite do G111: desenhados ou listados, sao 6 == len(paineis)."""
    import desenho_concreto as dc
    import desenho_svg_base as sb
    import laje_concreto as lj
    pav, _cfg = _pavimento_6()
    det = lj.detalha_lajes_por_painel(
        pav["paineis"],
        {"h": 0.10, "g": 1.0, "q": pav["q_kN_m2"], "fck": 25000.0,
         "fyk": 500000.0})
    svg = dc.planta_lajes_todos_paineis_svg(det)
    ET.fromstring(svg)
    g = sb.confere_folha_svg(svg)
    assert g["ok"], g
    c = confere_laje_todos_paineis(svg, pav["paineis"])
    assert c["ok"], c["motivo"]
    assert c["na_folha"] == PAINEIS_ESPERADOS, c


def test_estrutura_da_casa_publica_os_6_paineis_e_wrapper_lista_todos():
    """Integracao: `estrutura_casa.rodar` publica `lajes_por_painel` e o
    wrapper da PE-CO-03 emite a folha que passa na lente (reuso do BASE
    do G62, mesma malha 3x2 do spec persistido)."""
    import copy
    import desenho_casa_residencial as dcr
    import estrutura_casa as ec
    from tests.test_alvenaria_bim_pranchas_g62 import BASE
    r = ec.rodar(copy.deepcopy(BASE))
    assert r["ATENDE"], r["reprovados"]
    det = r.get("lajes_por_painel")
    assert isinstance(det, dict) and len(det["paineis"]) == 6, (
        det.keys() if isinstance(det, dict) else det)
    svg = dcr.detalhes_concreto_casa_svg(r)
    c = confere_laje_todos_paineis(svg, r["pavimento"]["paineis"])
    assert c["ok"], c["motivo"]


def test_gerar_planta_laje_com_todos_os_paineis(tmp_path):
    """O caminho do adaptador do predio (`gerar_planta_laje` com
    `lajes_por_painel`) escreve a folha que passa na lente."""
    import desenho_concreto as dc
    import laje_concreto as lj
    pav, _cfg = _pavimento_6()
    det = lj.detalha_lajes_por_painel(
        pav["paineis"],
        {"h": 0.10, "g": 1.0, "q": pav["q_kN_m2"], "fck": 25000.0,
         "fyk": 500000.0})
    dest = tmp_path / "planta-laje-pavimento-tipo.svg"
    dc.gerar_planta_laje(det["paineis"][0]["resultado"], str(dest),
                         lajes_por_painel=det)
    c = confere_laje_todos_paineis(
        dest.read_text(encoding="utf-8"), pav["paineis"])
    assert c["ok"], c["motivo"]


def test_folha_renderiza_e_cabe_no_png(tmp_path):
    """Terceiro degrau da escada: a folha rende PNG e o desenho cabe nele."""
    import desenho_concreto as dc
    import laje_concreto as lj
    from caderno_casa_edificio import svg_para_png
    pav, _cfg = _pavimento_6()
    det = lj.detalha_lajes_por_painel(
        pav["paineis"],
        {"h": 0.10, "g": 1.0, "q": pav["q_kN_m2"], "fck": 25000.0,
         "fyk": 500000.0})
    svg = dc.planta_lajes_todos_paineis_svg(det)
    dest = tmp_path / "planta-lajes.svg"
    dest.write_text(svg, encoding="utf-8")
    png = tmp_path / "planta-lajes.png"
    assert svg_para_png(str(dest), str(png)), "fitz nao rendeu a folha"
    assert png.exists() and png.stat().st_size > 0


def test_injecao_painel_a_mais_no_resultado_reprova_a_folha_antiga(tmp_path):
    """O aceite literal: painel a mais no resultado, em `tmp_path`."""
    import desenho_concreto as dc
    import laje_concreto as lj
    pav, _cfg = _pavimento_6()
    det = lj.detalha_lajes_por_painel(
        pav["paineis"],
        {"h": 0.10, "g": 1.0, "q": pav["q_kN_m2"], "fck": 25000.0,
         "fyk": 500000.0})
    svg = dc.planta_lajes_todos_paineis_svg(det)
    (tmp_path / "planta-laje.svg").write_text(svg, encoding="utf-8")
    paineis_7 = copy.deepcopy(pav["paineis"]) + [
        {"i": 3, "j": 0, "lx": 3.5, "ly": 4.0, "caso": 4}]
    c = confere_laje_todos_paineis(
        (tmp_path / "planta-laje.svg").read_text(encoding="utf-8"),
        paineis_7)
    assert not c["ok"], c
    assert "sobrando" in c["motivo"] or "faltando" in c["motivo"], c


def test_folha_regenerada_cobre_o_painel_injetado(tmp_path):
    """O outro sentido: regenerada sobre o resultado novo, a folha volta
    a passar - o portao cobra folha atual, nao folha congelada."""
    import desenho_concreto as dc
    import desenho_svg_base as sb
    import laje_concreto as lj
    pav, _cfg = _pavimento_6()
    paineis_7 = copy.deepcopy(pav["paineis"]) + [
        {"i": 3, "j": 0, "lx": 3.5, "ly": 4.0, "caso": 4}]
    det = lj.detalha_lajes_por_painel(
        paineis_7,
        {"h": 0.10, "g": 1.0, "q": pav["q_kN_m2"], "fck": 25000.0,
         "fyk": 500000.0})
    svg = dc.planta_lajes_todos_paineis_svg(det)
    (tmp_path / "planta-laje-7.svg").write_text(svg, encoding="utf-8")
    ET.fromstring(svg)
    assert sb.confere_folha_svg(svg)["ok"]
    c = confere_laje_todos_paineis(svg, paineis_7)
    assert c["ok"], c["motivo"]

def test_painel_que_reprova_com_a_h_do_critico_reprova_a_estrutura(monkeypatch):
    """G113: o G111 detalha os 6 paineis com a h que convergiu pelo critico,
    mas o OK por painel nao chegava ao veredito - um painel REPROVA na folha
    convivia com ATENDE na estrutura (saturacao silenciosa). Injecao: um
    painel nao critico reprova; a estrutura tem de reprovar e nomea-lo. O
    caso bom (sem injecao) segue ATENDE."""
    import copy
    import estrutura_casa as ec
    import laje_concreto as lj
    from tests.test_alvenaria_bim_pranchas_g62 import BASE

    bom = ec.rodar(copy.deepcopy(BASE))
    assert bom["ATENDE"] and bom["gates"]["lajes_por_painel"]["OK"], (
        bom["reprovados"])
    original = lj.detalha_lajes_por_painel

    def _um_reprova(paineis, cfg):
        det = original(paineis, cfg)
        alvo = det["paineis"][-1]
        alvo["resultado"] = dict(alvo["resultado"], OK=False)
        return det

    monkeypatch.setattr(lj, "detalha_lajes_por_painel", _um_reprova)
    mau = ec.rodar(copy.deepcopy(BASE))
    g = mau["gates"]["lajes_por_painel"]
    assert not mau["ATENDE"] and "lajes_por_painel" in mau["reprovados"], (
        mau["reprovados"])
    assert g["reprovados"] == ["painel 2,1"] and g["n_paineis"] == 6, g
