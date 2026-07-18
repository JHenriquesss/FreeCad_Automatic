# ============================================================================
# test_terreno_mapper.py - a viabilidade urbanistica (TO/CA/TP + recuos) coletada
# pelo wizard tem de CHEGAR ao gate. Antes to_rodar_params nao passava
# params[terreno] -> o gate era sempre pulado (campos mortos). Ver varredura
# campo-do-wizard -> consumidor (item 9).
# ============================================================================
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS
import wizard as WZ
import terreno


def _spec(**kw):
    r = dict(area_lote_m2=957, to_max=0.60, recuo_frente=8, recuo_lateral=1.5,
             recuo_fundos=0, span=20, comprimento=28.5, eave=8, v0=45,
             sigma_solo=150, fund_tipo="sapata")
    r.update(kw)
    return WZ.construir_spec(r, slug="t_terr")


def test_mapper_passa_terreno():
    p = PS.to_rodar_params(_spec())
    assert "terreno" in p, "to_rodar_params nao mapeou o terreno (gate seria pulado)"
    assert p["terreno"]["area_lote_m2"] == 957
    assert p["terreno"]["to_max"] == 0.60
    assert p["terreno"]["recuo_frente"] == 8


def test_gate_area_only_verifica_TO_CA_TP():
    p = PS.to_rodar_params(_spec())
    terr = terreno.analisa_terreno(p["terreno"])
    ver = terreno.verifica_galpao(terr, 28.5, 20.0)
    # 570 m2 de footprint <= 0,60*957 = 574 -> passa no limite
    assert ver["checks"]["TO (footprint)"][2] is True
    # sem poligono do lote: recuos ficam PENDENTES (nao reprovam, mas sinalizam)
    assert ver["recuos_pendentes"] is True
    assert "Recuos (cabe no retangulo)" not in ver["checks"]


def test_gate_area_only_reprova_TO_excedido():
    # galpao grande demais p/ a TO -> reprova
    p = PS.to_rodar_params(_spec(to_max=0.50))     # 570 > 0,50*957=478,5
    terr = terreno.analisa_terreno(p["terreno"])
    ver = terreno.verifica_galpao(terr, 28.5, 20.0)
    assert ver["checks"]["TO (footprint)"][2] is False
    assert ver["OK"] is False


def test_analisa_terreno_poligono_ainda_funciona():
    # modo com poligono (KML/pts) intacto: recuos verificados
    cfg = {"pts_xy": [(0, 0), (50, 0), (50, 20), (0, 20)],
           "to_max": 0.6, "ca_max": 1.0, "tp_min": 0.2,
           "recuo_frente": 5, "recuo_lateral": 1.5, "recuo_fundos": 3}
    terr = terreno.analisa_terreno(cfg)
    assert terr["retangulo_construivel_m"] is not None
    ver = terreno.verifica_galpao(terr, 30, 15)
    assert "Recuos (cabe no retangulo)" in ver["checks"]
    assert ver["recuos_pendentes"] is False
