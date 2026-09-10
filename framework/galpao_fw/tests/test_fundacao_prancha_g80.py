# G80: o predio dimensiona fundacao por pilar e nao entregava folha.
"""PE-CO-04 planta de locacao/formas da fundacao: um elemento desenhado por
pilar, dimensoes desenhadas == dimensionadas.

Convecoes do repo (caras, cada uma custou um bug):
1. baseline nos dois sentidos (verde no bom, vermelho no injetado);
2. vermelho por injecao em tmp_path, nunca mutando o repo;
3. substring -> parse -> renderizar (XML + confere_folha_svg; o olhar fica no
   G80 manual e no PNG da amostragem);
4. saturacao silenciosa (o portao e' o detalhamento entregue);
5. assercao tautologica (o esperado vem do calculo, nunca do SVG).
"""
import copy
import xml.etree.ElementTree as ET

import desenho_svg_base as sb
from tests.test_edificio_pranchas_g56 import _caso


def _fundacao_estrutura():
    R, _H, _E, _I = _caso()
    assert isinstance(R.get("fundacao"), dict) and R["fundacao"].get("por_pilar"), \
        "o caso do predio precisa vir com fundacao dimensionada"
    return R["fundacao"], R


def test_folha_passa_na_guarda_e_no_parse():
    import desenho_fundacao_edificio as dfe

    fund, R = _fundacao_estrutura()
    svg = dfe.planta_fundacao_svg(fund, R)
    ET.fromstring(svg)  # XML de verdade; malformado levanta
    c = sb.confere_folha_svg(svg)
    assert c["ok"], c["motivo"]
    assert sb.colisoes_de_rotulo_svg(svg) == []


def test_drawing_vs_data_um_elemento_por_pilar():
    """Count-driven: pilares desenhados == pilares dimensionados, B/L/h/Ndim
    desenhados == dimensionados (parse, nunca substring)."""
    import desenho_fundacao_edificio as dfe

    fund, R = _fundacao_estrutura()
    svg = dfe.planta_fundacao_svg(fund, R)
    conf = dfe.confere_desenho_fundacao(fund, svg)
    assert conf["ok"], conf["motivo"]
    assert conf["n_esperado"] == len(fund["por_pilar"]) == 12
    assert conf["n_desenhado"] == 12


def test_vermelho_por_injecao_dimensao_muda_o_desenho():
    """Baseline nos dois sentidos: o mesmo dado com B adulterado TEM de sair
    no desenho (o desenho segue o dado) e o confere contra o ORIGINAL TEM de
    acusar. Sem isso a suite fica verde com o gap dentro dela."""
    import desenho_fundacao_edificio as dfe

    fund, R = _fundacao_estrutura()
    svg_bom = dfe.planta_fundacao_svg(fund, R)
    assert dfe.confere_desenho_fundacao(fund, svg_bom)["ok"]

    fund2 = copy.deepcopy(fund)
    alvo = sorted(fund2["por_pilar"])[0]
    g2 = fund2["por_pilar"][alvo]["geometria"]
    assert g2.get("B_m") is not None, "o caso precisa de sapata retangular"
    g2["B_m"] = round(float(g2["B_m"]) + 0.5, 2)
    svg2 = dfe.planta_fundacao_svg(fund2, R)
    # sentido 1: o desenho segue o dado injetado
    assert ("%.2f" % g2["B_m"]) in svg2
    # sentido 2: o confere contra o ORIGINAL acusa
    conf = dfe.confere_desenho_fundacao(fund, svg2)
    assert not conf["ok"], conf
    assert any(alvo in d for d in conf["divergencias"])


def test_vermelho_por_injecao_pilar_faltando():
    """Pilar suprimido do desenho (simulado removendo do dado que alimenta a
    folha) e' acusado pelo confere contra o dado completo."""
    import desenho_fundacao_edificio as dfe

    fund, R = _fundacao_estrutura()
    fund2 = copy.deepcopy(fund)
    alvo = sorted(fund2["por_pilar"])[0]
    del fund2["por_pilar"][alvo]
    svg2 = dfe.planta_fundacao_svg(fund2, R)
    conf = dfe.confere_desenho_fundacao(fund, svg2)
    assert not conf["ok"]
    assert alvo in conf["faltando"]


def test_quadro_declara_tipo_e_tensao_nunca_arbitrada():
    """Detalhamento entregue (convecao 4): o quadro mostra o tipo escolhido e
    a tensao com a proveniencia; sem sigma nao ha folha inventada."""
    import desenho_fundacao_edificio as dfe

    fund, R = _fundacao_estrutura()
    svg = dfe.planta_fundacao_svg(fund, R)
    assert fund["tipo"] in svg
    assert ("%.1f" % float(fund["sigma_solo_adm"])) in svg
    # tensao sem fonte nao existe neste framework (SIGMA_SOLO_DEFAULT = None)
    import fundacao_edificio as fe

    assert fe.SIGMA_SOLO_DEFAULT is None


def test_indice_ganha_a_entrada_e_o_hook_emite(tmp_path):
    """D89: sem entrada em _PRANCHAS a folha evapora no continue do indice.
    O indice tem PE-CO-04, o adapter mapeia, e o hook emite o arquivo (ou
    nomeia a pulada quando nao ha fundacao)."""
    import edificio_adapter as ea
    import gestao_edificio as ge
    import pacote_legal as pl

    R, H, E, I = _caso()
    result = {"estrutura": R,
              "instalacoes": {"hidraulica": H, "eletrico": E, "incendio": I}}
    indice = pl.indice_de_pranchas(ge.disciplinas_pacote(result)
                                   + ["coordenacao"])
    cods = [p["codigo"] for p in indice]
    assert "PE-CO-04" in cods, cods
    assert ea._PRANCHA_ARQUIVO.get("PE-CO-04") == "fundacao-locacao-formas.svg"

    manifest = {"artifacts": [], "deliverables": {}}
    opt = type("O", (), {"generate_2d": True, "generate_caderno": True})()
    ea._emitir_desenhos(manifest, str(tmp_path), {}, opt, result)
    reg = manifest["deliverables"]["drawings"]
    nomes = [a.split("/")[-1] for a in reg["artifacts"]]
    puladas = [p.get("prancha") for p in reg.get("skipped", [])
               if isinstance(p, dict)]
    assert "fundacao-locacao-formas.svg" in nomes, (nomes, puladas)
    # laco indice<->disco continua fechando com a folha nova
    assert len(reg["artifacts"]) + len(reg.get("skipped", [])) == len(indice)


def test_hook_nomeia_a_pulada_sem_fundacao(tmp_path):
    """Sem sondagem/tensao nao ha fundacao e nao ha folha: motivo nomeado,
    nunca SVG vazio que parece prancha."""
    import copy as _copy

    import edificio_adapter as ea

    R, H, E, I = _caso()
    R2 = _copy.deepcopy(R)
    R2.pop("fundacao", None)
    R2["fundacao_erro"] = None
    result = {"estrutura": R2,
              "instalacoes": {"hidraulica": H, "eletrico": E, "incendio": I}}
    manifest = {"artifacts": [], "deliverables": {}}
    opt = type("O", (), {"generate_2d": True, "generate_caderno": True})()
    ea._emitir_desenhos(manifest, str(tmp_path), {}, opt, result)
    reg = manifest["deliverables"]["drawings"]
    motivos = {p.get("prancha"): p.get("motivo") for p in reg.get("skipped", [])
               if isinstance(p, dict)}
    assert "fundacao-locacao-formas.svg" in motivos, motivos
