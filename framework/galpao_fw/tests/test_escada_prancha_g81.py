# G81: a escada era calculada e nao tinha folha (so texto no quadro do PPCI).
"""PE-IN-03 escada de emergencia (planta + corte): um rect por degrau,
medidas desenhadas == dimensionadas, Blondel e largura exigida x adotada
visiveis, patamar declarado com o minimo da 9050 citado.

Convecoes do repo (caras, cada uma custou um bug):
1. baseline nos dois sentidos (verde no bom, vermelho no injetado);
2. vermelho por injecao em dado copiado, nunca mutando o repo;
3. substring -> parse -> renderizar (XML + confere_folha_svg; o olhar fica no
   PNG da amostragem, gerado e aberto nesta rodada);
4. saturacao silenciosa (o portao e' o detalhamento entregue);
5. assercao tautologica (o esperado vem do calculo + gates, nunca do SVG).
"""
import copy
import xml.etree.ElementTree as ET

import desenho_svg_base as sb
from tests.test_edificio_pranchas_g56 import _caso


def _escada_incendio():
    R, _H, _E, I = _caso()
    esc = R.get("escada")
    assert isinstance(esc, dict) and isinstance(esc.get("geometria"), dict), \
        "o caso do predio precisa vir com escada dimensionada"
    assert I["gates"].get("escada_largura"), "o incendio precisa verificar a largura"
    return esc, I


def test_folha_passa_na_guarda_e_no_parse():
    import desenho_escada_edificio as dee

    esc, I = _escada_incendio()
    svg = dee.planta_escada_svg(esc, I)
    ET.fromstring(svg)  # XML de verdade; malformado levanta
    c = sb.confere_folha_svg(svg)
    assert c["ok"], c["motivo"]
    assert sb.colisoes_de_rotulo_svg(svg) == []


def test_drawing_vs_data_degraus_e_medidas():
    """Count-driven por PARSE: degraus desenhados == n_degraus, espelho /
    piso / patamar / larguras desenhados == calculados (nunca substring)."""
    import desenho_escada_edificio as dee

    esc, I = _escada_incendio()
    svg = dee.planta_escada_svg(esc, I)
    conf = dee.confere_desenho_escada(esc, svg, I)
    assert conf["ok"], conf["motivo"]
    n = esc["geometria"]["n_degraus"]
    assert conf["n_esperado"] == n == conf["n_desenhado"]


def test_vermelho_por_injecao_espelho_muda_o_desenho():
    """Baseline nos dois sentidos: espelho adulterado TEM de sair no desenho
    e o confere contra o ORIGINAL TEM de acusar."""
    import desenho_escada_edificio as dee

    esc, I = _escada_incendio()
    svg_bom = dee.planta_escada_svg(esc, I)
    assert dee.confere_desenho_escada(esc, svg_bom, I)["ok"]

    esc2 = copy.deepcopy(esc)
    esc2["geometria"] = dict(esc2["geometria"], espelho=0.19)
    svg2 = dee.planta_escada_svg(esc2, I)
    # sentido 1: o desenho segue o dado injetado
    assert "19.0 cm" in svg2
    # sentido 2: o confere contra o ORIGINAL acusa
    conf = dee.confere_desenho_escada(esc, svg2, I)
    assert not conf["ok"], conf
    assert any("espelho" in d for d in conf["divergencias"])


def test_vermelho_por_injecao_largura_muda_o_desenho():
    import desenho_escada_edificio as dee

    esc, I = _escada_incendio()
    esc2 = copy.deepcopy(esc)
    esc2["largura_m"] = 2.00
    svg2 = dee.planta_escada_svg(esc2, I)
    assert "2.00 m" in svg2
    conf = dee.confere_desenho_escada(esc, svg2, I)
    assert not conf["ok"], conf
    assert any("largura" in d for d in conf["divergencias"])


def test_quadro_declara_exigida_x_adotada_blondel_e_patamar():
    """Detalhamento entregue (convecao 4): largura exigida x adotada, Blondel
    com a faixa, patamar declarado com o A CONFIRMAR visivel."""
    import desenho_escada_edificio as dee

    esc, I = _escada_incendio()
    svg = dee.planta_escada_svg(esc, I)
    exig = I["gates"]["escada_largura"]["largura_exigida_m"]
    assert ("%.2f m" % exig) in svg
    assert ("%.2f m" % esc["largura_m"]) in svg
    assert "Blondel" in svg
    assert "A CONFIRMAR" in svg
    assert ("%.2f m" % esc["patamar_m"]) in svg


def test_patamar_triagem_minimo_9050_e_lance_unico():
    """A triagem do G81 amarrada a fonte independente (nao a folha): o
    patamar declarado atende ao minimo 9050 6.8.8 e o desnivel cabe num
    lance so (6.8.7) - e' por isso que a folha desenha 1 lance + patamar
    de chegada, sem patamar intermediario inventado."""
    import incendio_edificio as ie

    esc, _I = _escada_incendio()
    assert esc["patamar_m"] + 1e-9 >= ie.PATAMAR_MIN_M
    desnivel = esc["geometria"]["n_degraus"] * esc["geometria"]["espelho"]
    assert desnivel <= ie.DESNIVEL_MAX_SEM_PATAMAR_M + 1e-9


def test_sem_escada_nao_ha_folha():
    """Sem estrutura.escada dimensionada nao ha folha: recusa com endereco
    (o hook transforma em pulada nomeada, nunca SVG vazio)."""
    import desenho_escada_edificio as dee

    try:
        dee.planta_escada_svg(None, None)
    except ValueError as exc:
        assert "escada nao dimensionada" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("devia recusar sem escada")


def test_indice_ganha_a_entrada_e_o_hook_emite(tmp_path):
    """D89: sem entrada em _PRANCHAS a folha evapora no continue do indice.
    O indice tem PE-IN-03, o adapter mapeia, e o hook emite o arquivo."""
    import edificio_adapter as ea
    import gestao_edificio as ge
    import pacote_legal as pl

    R, H, E, I = _caso()
    result = {"estrutura": R,
              "instalacoes": {"hidraulica": H, "eletrico": E, "incendio": I}}
    indice = pl.indice_de_pranchas(ge.disciplinas_pacote(result)
                                   + ["coordenacao"])
    cods = [p["codigo"] for p in indice]
    assert "PE-IN-03" in cods, cods
    assert ea._PRANCHA_ARQUIVO.get("PE-IN-03") == \
        "incendio-escada-planta-corte.svg"

    manifest = {"artifacts": [], "deliverables": {}}
    opt = type("O", (), {"generate_2d": True, "generate_caderno": True})()
    ea._emitir_desenhos(manifest, str(tmp_path), {}, opt, result)
    reg = manifest["deliverables"]["drawings"]
    nomes = [a.split("/")[-1] for a in reg["artifacts"]]
    puladas = [p.get("prancha") for p in reg.get("skipped", [])
               if isinstance(p, dict)]
    assert "incendio-escada-planta-corte.svg" in nomes, (nomes, puladas)
    # laco indice<->disco continua fechando com a folha nova
    assert len(reg["artifacts"]) + len(reg.get("skipped", [])) == len(indice)


def test_hook_nomeia_a_pulada_sem_escada(tmp_path):
    """Sem escada declarada nao ha folha: motivo nomeado, nunca SVG vazio
    que parece prancha."""
    import copy as _copy

    import edificio_adapter as ea

    R, H, E, I = _caso()
    R2 = _copy.deepcopy(R)
    R2.pop("escada", None)
    result = {"estrutura": R2,
              "instalacoes": {"hidraulica": H, "eletrico": E, "incendio": I}}
    manifest = {"artifacts": [], "deliverables": {}}
    opt = type("O", (), {"generate_2d": True, "generate_caderno": True})()
    ea._emitir_desenhos(manifest, str(tmp_path), {}, opt, result)
    reg = manifest["deliverables"]["drawings"]
    motivos = {p.get("prancha"): p.get("motivo") for p in reg.get("skipped", [])
               if isinstance(p, dict)}
    assert "incendio-escada-planta-corte.svg" in motivos, motivos
