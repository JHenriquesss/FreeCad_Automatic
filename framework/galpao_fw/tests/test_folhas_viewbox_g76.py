# G76: as 40 folhas que ninguem olhou - guarda generica da folha.
"""Guarda generica viewBox==WxH + contem desenho, varredura do remendo-por-string.

Licao: substring -> parse -> renderizar. So o terceiro pega geometria de folha.
A elevacao da alvenaria era XML valido com height 2477 e viewBox de altura 100
(remendo por string que nunca casava) e nenhuma guarda pegava sem pixels.
"""
import copy
import pathlib
import re
import xml.etree.ElementTree as ET

import pytest

import desenho_svg_base as sb

GALPAO = pathlib.Path(__file__).resolve().parents[1]


def _folha(w, h, corpo, titulo="T"):
    return "\n".join(sb.abre_svg(w, h, titulo) + [corpo]) + "\n</svg>"


def test_confere_folha_ok_no_caso_base():
    svg = _folha(900, 400, '<rect x="10" y="10" width="100" height="50"/>')
    c = sb.confere_folha_svg(svg)
    assert c["ok"], c
    assert c["w"] == 900 and c["h"] == 400


def test_confere_folha_pega_viewbox_antiga_da_elevacao():
    # Injecao do emissor antigo: height 2477 com viewBox de altura 100.
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="1100.0" '
           'height="2477" viewBox="0 0 1100.0 100" font-family="Arial">'
           '<rect x="0" y="0" width="1100.0" height="2477" fill="white"/>'
           '<rect x="70" y="100" width="360" height="243" fill="#f1f5f9"/>'
           "</svg>")
    c = sb.confere_folha_svg(svg)
    assert not c["ok"] and "viewBox-nao-e-WxH" in c["motivo"], c


def test_confere_folha_pega_desenho_fora_da_folha():
    svg = _folha(500, 300, '<rect x="10" y="10" width="600" height="50"/>')
    c = sb.confere_folha_svg(svg)
    assert not c["ok"] and "fora-da-folha" in c["motivo"], c
    # Baseline no outro sentido: dentro passa.
    svg2 = _folha(500, 300, '<rect x="10" y="10" width="100" height="50"/>')
    assert sb.confere_folha_svg(svg2)["ok"]


def test_varredura_sem_remendo_de_cabecalho_por_string():
    """O padrao que causou o defeito: cabecalho antes das medidas + replace.

    Medido na arvore: nenhum desenho remenda width/height/viewBox por string;
    a elevacao (unico caso) ja sai com o cabecalho no fim. Se alguem repor o
    padrao, este teste fica vermelho.
    """
    alvos = sorted(GALPAO.glob("desenho_*.py"))
    assert len(alvos) >= 10
    achados = []
    for p in alvos:
        txt = p.read_text(encoding="utf-8")
        for i, linha in enumerate(txt.splitlines(), 1):
            s = linha.strip()
            if ".replace(" in s and ("width" in s or "viewBox" in s
                                     or "height" in s or '"100"' in s
                                     or "'100'" in s):
                achados.append("%s:%d:%s" % (p.name, i, s[:120]))
    assert achados == [], achados
    # E o abre_svg declara viewBox com as mesmas variaveis (coerente).
    base = (GALPAO / "desenho_svg_base.py").read_text(encoding="utf-8")
    assert 'viewBox="0 0 {largura} {altura}"' in base


def test_folha_da_laje_passam_na_guarda_generica():
    import desenho_concreto as dc
    import laje_concreto as lj

    r = lj.verifica_laje(dict(lx=4.0, ly=6.0, h=0.12, fck=20e3, fyk=500e3,
                              caso=4, g=0.56, q=3.0, phi_mm=10.0))
    svg = dc.planta_laje_svg(r)
    ET.fromstring(svg)
    c = sb.confere_folha_svg(svg)
    assert c["ok"], c


def test_folhas_de_alvenaria_passam_na_guarda_generica():
    import copy as _cp

    import desenho_alvenaria as da
    import estrutura_casa as ec
    from tests.test_alvenaria_bim_pranchas_g62 import BASE

    r = ec.rodar(_cp.deepcopy(BASE))
    assert r["ATENDE"], r["reprovados"]
    alv = r["alvenaria"]
    pe = r["H_total_m"] / r["n_pavimentos"]
    for svg in (da.elevacao_paredes_svg(alv, pe, alv["te_m"]),
                da.planta_fiadas_svg(alv, r["pavimento"]["vaos_x"],
                                     r["pavimento"]["vaos_y"], alv["te_m"])):
        ET.fromstring(svg)
        c = sb.confere_folha_svg(svg)
        assert c["ok"], c


def test_prancha_da_tesoura_passam_na_guarda_generica():
    import desenho_casa_residencial as dcr
    import telhado_casa_madeira as tm
    from tests.test_telhado_madeira_g66 import TELHADO_VIGA

    t = tm.rodar(copy.deepcopy(TELHADO_VIGA))
    svg = dcr.telhado_tesoura_svg(t)
    ET.fromstring(svg)
    c = sb.confere_folha_svg(svg)
    assert c["ok"], c
