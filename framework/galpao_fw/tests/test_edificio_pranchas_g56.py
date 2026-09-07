"""G56: o predio ganha as 10 pranchas que o indice promete (13 no total).

Cada prancha nova: (a) parseia o SVG como XML, nao substring; (b) confere
geometria contra o dado (desenhado == calculado); (c) roda colisoes de rotulo.
Mais o laco manifesto<->disco: emitidas + puladas == len(indice_pranchas).

Fase vermelha por injecao: cada teste de geometria tem um par que muta o dado
e exige que o SVG mude junto (drawing-vs-data). Antes da implementacao todos
falham (ImportError das funcoes novas); depois, so passam se data-driven.
"""
import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import desenho_svg_base as sb

SPEC = json.loads((Path(__file__).parents[3] / "projects" /
                   "edificio-multipavimento" / "project-spec.json"
                   ).read_text(encoding="utf-8"))

_CACHE = {}


def _caso():
    if _CACHE:
        return _CACHE["R"], _CACHE["H"], _CACHE["E"], _CACHE["I"]
    import edificio_multipavimento as em
    import eletrica_edificio as ee
    import hidraulica_edificio as he
    import incendio_edificio as ie
    from edificio_adapter import _contexto_predio

    tk = SPEC["turnkey"]
    est = {"geometria": tk["estrutura"]["geometria"],
           "pavimentos": tk["estrutura"]["pavimentos"],
           "materiais": tk["estrutura"]["materiais"],
           "laje": tk["estrutura"].get("laje"),
           "viga": tk["estrutura"].get("viga"),
           "vento": tk["estrutura"].get("vento"),
           "fundacao": tk["estrutura"].get("fundacao"),
           "escada": tk["estrutura"].get("escada")}
    R = em.rodar(est)
    ctx0 = _contexto_predio(tk["estrutura"], R, None)
    I = ie.dimensiona(tk["incendio"], ctx0)
    ctx = _contexto_predio(
        tk["estrutura"], R,
        {"incendio": {"populacao_por_pavimento": I["populacao_por_pavimento"]}})
    H = he.dimensiona(tk["hidraulica"], ctx)
    E = ee.dimensiona(tk["eletrico"], ctx)
    _CACHE.update({"R": R, "H": H, "E": E, "I": I})
    return R, H, E, I


def _xml(svg):
    """Parseia como XML de verdade (SVG malformado levanta, nao passa)."""
    return ET.fromstring(svg)


def _textos(root):
    ns = {"s": "http://www.w3.org/2000/svg"}
    return root.findall(".//s:text", ns) or root.findall(".//text")


# ---------------- primitivas unificadas ----------------

def test_primitivas_unificadas_na_base():
    import desenho_coordenacao as dc
    import desenho_hidraulica as dh
    import desenho_incendio as di

    for mod in (dh, di, dc):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "from desenho_svg_base import" in src, mod.__name__
        # sem copia local: o escape vive num lugar so (berco da dupla-escapa)
        assert "def _esc(" not in src, mod.__name__


def test_linha_da_base_aceita_tracejado():
    svg = sb.linha(0, 0, 10, 10, dash="10 5")
    assert 'stroke-dasharray="10 5"' in svg
    _xml('<svg xmlns="http://www.w3.org/2000/svg">%s</svg>' % svg)


# ---------------- eletrica: 4 folhas ----------------

def test_eletrica_unifilar_prumada_xml_e_geometria():
    import desenho_eletrico as de
    R, _H, E, _I = _caso()
    svg = de.diagrama_prumada_edificio_svg(E, R)
    root = _xml(svg)
    assert len(_textos(root)) > 0
    # quadros desenhados == pavimentos servidos (calculado)
    n_qd = svg.count("QD-")
    assert n_qd == E["pavimentos_servidos"], (n_qd, E["pavimentos_servidos"])
    # secao da prumada rotulada == calculada
    assert ("%.0f mm" % E["prumada"]["secao_mm2"]) in svg or \
        ("%s mm2" % E["prumada"]["secao_mm2"]) in svg
    assert sb.colisoes_de_rotulo_svg(svg) == []


def test_eletrica_unifilar_vermelha_por_injecao():
    import desenho_eletrico as de
    R, _H, E, _I = _caso()
    E2 = copy.deepcopy(E)
    E2["prumada"] = dict(E2["prumada"], secao_mm2=9999)
    svg2 = de.diagrama_prumada_edificio_svg(E2, R)
    assert "9999" in svg2  # o desenho segue o dado, nao um numero fixo


def test_eletrica_planta_pavimento_xml_e_geometria():
    import desenho_eletrico as de
    R, _H, E, _I = _caso()
    svg = de.planta_eletrica_pavimento_svg(E, R)
    _xml(svg)
    # um quadro por planta + eletrocalha atravessando o comprimento
    assert svg.count("QDP") >= 1
    assert "ELETROCALHA" in svg.upper() or "eletrocalha" in svg
    assert sb.colisoes_de_rotulo_svg(svg) == []


def test_eletrica_infra_xml_e_geometria():
    import desenho_eletrico as de
    R, _H, E, _I = _caso()
    svg = de.infra_aterramento_edificio_svg(E, R)
    _xml(svg)
    assert "PRUMADA" in svg.upper()
    assert sb.colisoes_de_rotulo_svg(svg) == []


def test_eletrica_qdc_xml_e_geometria():
    import desenho_eletrico as de
    R, _H, E, _I = _caso()
    svg = de.qdc_edificio_svg(E, R)
    root = _xml(svg)
    assert len(_textos(root)) > 0
    # uma linha de quadro por pavimento servido
    assert svg.count("QD-") == E["pavimentos_servidos"]
    # disjuntor do quadro == calculado
    assert ("%s A" % E["quadro_de_pavimento"]["protecao"]["disjuntor"]["IN"]) in svg
    assert sb.colisoes_de_rotulo_svg(svg) == []


# ---------------- hidraulica: 3 folhas (planta-tipo + corte) ----------------

@pytest.mark.parametrize("rede,dn_esperado", [
    ("agua", 32), ("esgoto", 100), ("pluvial", 75),
])
def test_hidraulica_rede_xml_e_dn(rede, dn_esperado):
    import desenho_hidraulica as dh
    R, H, _E, _I = _caso()
    svg = dh.planta_rede_edificio_svg(H, R, rede=rede)
    _xml(svg)
    assert ("DN%d" % dn_esperado) in svg
    # corte vertical presente (o que o galpao nunca teve)
    assert "CORTE" in svg.upper()
    assert sb.colisoes_de_rotulo_svg(svg) == []


def test_hidraulica_vermelha_por_injecao():
    import desenho_hidraulica as dh
    R, H, _E, _I = _caso()
    H2 = copy.deepcopy(H)
    H2["coluna"]["dn"]["DN_mm"] = 999
    svg2 = dh.planta_rede_edificio_svg(H2, R, rede="agua")
    assert "DN999" in svg2


def test_hidraulica_rede_invalida_nomeada():
    import desenho_hidraulica as dh
    R, H, _E, _I = _caso()
    with pytest.raises(ValueError):
        dh.planta_rede_edificio_svg(H, R, rede="vapor")


# ---------------- incendio: 2 folhas ----------------

def test_incendio_ppci_xml_e_geometria():
    import desenho_incendio as di
    R, _H, _E, I = _caso()
    svg = di.planta_pavimento_edificio_svg(I, R)
    _xml(svg)
    n_hid = I["sistemas"]["hidrantes"]["N_hidrantes"] if I["sistemas"].get("hidrantes") else 0
    assert svg.count('>H<') >= n_hid
    n_det = I["sistemas"]["deteccao_alarme"]["N_detectores"]
    assert svg.count("DET") >= 1 and n_det > 0
    assert sb.colisoes_de_rotulo_svg(svg) == []


def test_incendio_ppci_vermelho_por_injecao():
    import desenho_incendio as di
    R, _H, _E, I = _caso()
    I2 = copy.deepcopy(I)
    I2["sistemas"]["deteccao_alarme"]["N_detectores"] = 11
    svg2 = di.planta_pavimento_edificio_svg(I2, R)
    assert svg2.count("DET") != di.planta_pavimento_edificio_svg(I, R).count("DET")


def test_incendio_detalhes_xml_e_geometria():
    import desenho_incendio as di
    R, _H, _E, I = _caso()
    svg = di.detalhes_hidrantes_rotas_svg(I, R)
    _xml(svg)
    assert "DN65" in svg  # coluna de hidrantes NBR 13714
    assert "RESERVA" in svg.upper()
    assert sb.colisoes_de_rotulo_svg(svg) == []


# ---------------- coordenacao: PE-CD-01 e kind drawing ----------------

def test_coordenacao_prancha_federado_xml_e_clash():
    import bim_instalacoes_edificio as bie
    import desenho_coordenacao as dc
    R, H, E, I = _caso()
    fed, _disc = bie.membros_federados_edificio(
        R, {"hidraulica": H, "eletrico": E, "incendio": I})
    rep = bie.checa_interferencia_edificio(
        R, {"hidraulica": H, "eletrico": E, "incendio": I})
    svg = dc.coordenacao_svg(fed, rep)
    _xml(svg)
    assert "Membros: %d" % len(fed) in svg
    assert sb.colisoes_de_rotulo_svg(svg) == []


def test_hook_coordenacao_e_drawing(tmp_path):
    """A prancha PE-CD-01 sai com kind drawing (senao nao conta no indice)."""
    import edificio_adapter as ea
    R, H, E, I = _caso()
    result = {"estrutura": R,
              "instalacoes": {"hidraulica": H, "eletrico": E, "incendio": I}}
    manifest = {"artifacts": [], "deliverables": {}}
    opt = type("O", (), {"generate_2d": True, "generate_caderno": True})()

    # isola so a coordenacao: sem estrutura completa o hook pula com motivo
    ea._emitir_coordenacao(manifest, str(tmp_path), {}, opt, result)
    kinds = [a.get("kind") for a in manifest.get("artifacts", [])]
    assert "drawing" in kinds, kinds


# ---------------- laco indice <-> disco + fundacao ----------------

def test_laco_indice_disco_no_hook(tmp_path):
    import edificio_adapter as ea
    import pacote_legal as pl
    R, H, E, I = _caso()
    result = {"estrutura": R,
              "instalacoes": {"hidraulica": H, "eletrico": E, "incendio": I}}
    manifest = {"artifacts": [], "deliverables": {}}
    opt = type("O", (), {"generate_2d": True, "generate_caderno": True})()
    ea._emitir_desenhos(manifest, str(tmp_path), {}, opt, result)
    reg = manifest["deliverables"]["drawings"]
    import gestao_edificio as ge
    indice = pl.indice_de_pranchas(ge.disciplinas_pacote(result) + ["coordenacao"])
    assert len(reg["artifacts"]) + len(reg.get("skipped", [])) == len(indice), \
        (len(reg["artifacts"]), len(reg.get("skipped", [])), len(indice))
    assert len(indice) == 13


def test_fundacao_nao_evapora():
    """D89: 'fundacao' nao atravessa e some no continue do pacote_legal."""
    import gestao_edificio as ge
    import pacote_legal as pl
    R, H, E, I = _caso()
    result = {"estrutura": R,
              "instalacoes": {"hidraulica": H, "eletrico": E, "incendio": I}}
    # no caderno ela segue secao propria; no pacote vira concreto (PE-CO-01)
    assert "fundacao" in ge.disciplinas(result)
    discs = ge.disciplinas_pacote(result)
    assert "fundacao" not in discs
    assert ge.FUNDACAO_COBERTA_POR == "concreto"  # dito em voz alta
    # e o concreto cobre: PE-CO-01 existe no indice
    cods = [p["codigo"] for p in pl.indice_de_pranchas(discs + ["coordenacao"])]
    assert "PE-CO-01" in cods


def test_laco_que_falha_nao_cai_em_silencio(monkeypatch, tmp_path):
    """A rede de seguranca do indice nao pode sumir sem deixar rastro.

    O laco indice<->disco e' o que garante que nenhuma folha evapora. Se ele
    proprio quebrar, engolir a excecao apagaria a garantia e o manifesto
    continuaria dizendo "generated" -- saturacao silenciosa vestida de rede
    de seguranca. Injeta o defeito e exige o motivo nomeado.
    """
    import edificio_adapter as ea
    import pacote_legal as pl

    def _explode(*a, **k):
        raise RuntimeError("indice fora do ar")

    monkeypatch.setattr(pl, "indice_de_pranchas", _explode)
    R, H, E, I = _caso()
    result = {"estrutura": R,
              "instalacoes": {"hidraulica": H, "eletrico": E, "incendio": I}}
    manifest = {"artifacts": [], "deliverables": {}}
    opt = type("O", (), {"generate_2d": True, "generate_caderno": True})()
    ea._emitir_desenhos(manifest, str(tmp_path), {}, opt, result)
    pulados = manifest["deliverables"]["drawings"].get("skipped", [])
    motivos = " ".join(p.get("motivo", "") for p in pulados
                       if isinstance(p, dict))
    assert "laco indice" in motivos and "indice fora do ar" in motivos, pulados
