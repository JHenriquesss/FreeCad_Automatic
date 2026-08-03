"""Executivo A1 de HIDRAULICA e CLIMATIZACAO: desenho (SVG esquema) + techdraw
(cfg da prancha A1 + bootstrap). Partes CI (fora do FreeCAD); a geracao da prancha
em si (freecad.exe) e' build-gated. Nivela as duas com as demais disciplinas."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_hidraulica as ghi
import galpao_climatizacao as gcl
import desenho_hidraulica as dh
import desenho_climatizacao as dcl
import techdraw_hidraulica as tdh
import techdraw_climatizacao as tdc


def _r_hid():
    return ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                      "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2},
                                     "aparelhos_esgoto": {"bacia": 2, "lavatorio": 2}}})


def _r_cli():
    return gcl.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "tipo": "galpao"})


# ------------------------------ HIDRAULICA ----------------------------------
def test_desenho_hidraulica_selftest():
    dh._selftest()


def test_svg_hidraulica_sem_virgula_nas_coordenadas():
    # o SVG NAO pode ter virgula decimal nas coordenadas (corromperia o parse); os
    # rotulos usam ponto. Garante que a regressao da virgula no SVG nao volte.
    svg = dh.esquema_hidraulica_svg(_r_hid())
    import re
    for attr in re.findall(r'(?:x|y|cx|cy|width|height)="([^"]+)"', svg):
        assert "," not in attr, attr


def test_config_hidraulica_monta_cfg():
    cfg = tdh.config_de_spec(_r_hid(), "/tmp/x")
    assert cfg["esquema_svg"].startswith("<svg")
    assert cfg["dim_hdr"] == ["COMPONENTE", "DIAMETRO", "NORMA / CRITERIO"]
    # cita as 4 componentes (condutor/calha/coletor/ventilacao/agua) e o memorial
    rotulos = " ".join(row[0] for row in cfg["dim_rows"])
    assert "Condutor pluvial" in rotulos and "Coletor de esgoto" in rotulos
    assert "Ventilacao" in rotulos and "Barrilete de agua" in rotulos
    assert cfg["carimbo_material"] == "HIDRAULICA"
    txt = "\n".join(cfg["notas"])
    assert "NBR 10844" in txt and "NBR 8160" in txt and "NBR 5626" in txt


def test_bootstrap_hidraulica():
    cfg = tdh.config_de_spec(_r_hid(), "/tmp/x")
    boot = tdh.script_bootstrap(cfg)
    assert "_entry_hidraulica" in boot and "QTimer" in boot and "esquema_svg" in boot


def test_montar_pranchas_hidraulica_sem_freecad():
    res = ghi.montar_pranchas(_r_hid(), "/tmp/x", freecad_exe="/nao/existe.exe")
    assert "erro" in res


# ------------------------------ CLIMATIZACAO --------------------------------
def test_desenho_climatizacao_selftest():
    dcl._selftest()


def test_svg_climatizacao_sem_virgula_nas_coordenadas():
    svg = dcl.esquema_climatizacao_svg(_r_cli())
    import re
    for attr in re.findall(r'(?:x|y|cx|cy|width|height)="([^"]+)"', svg):
        assert "," not in attr, attr


def test_config_climatizacao_monta_cfg():
    cfg = tdc.config_de_spec(_r_cli(), "/tmp/x")
    assert cfg["esquema_svg"].startswith("<svg")
    rotulos = " ".join(row[0] for row in cfg["dim_rows"])
    assert "Capacidade termica" in rotulos and "Vazao de insuflamento" in rotulos
    assert "Velocidade no duto" in rotulos
    assert cfg["carimbo_material"] == "CLIMATIZACAO"
    assert "NBR 16401" in "\n".join(cfg["notas"])


def test_bootstrap_climatizacao():
    cfg = tdc.config_de_spec(_r_cli(), "/tmp/x")
    boot = tdc.script_bootstrap(cfg)
    assert "_entry_climatizacao" in boot and "QTimer" in boot


def test_montar_pranchas_climatizacao_sem_freecad():
    res = gcl.montar_pranchas(_r_cli(), "/tmp/x", freecad_exe="/nao/existe.exe")
    assert "erro" in res
