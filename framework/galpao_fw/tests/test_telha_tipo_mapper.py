# ============================================================================
# test_telha_tipo_mapper.py - o TIPO de telha (cobertura.telha_tipo) coletado
# pelo wizard tem de CHEGAR ao gate 7 e DIFERENCIAR a verificacao. Antes o gate
# rodava SEMPRE com TELHA_EXEMPLO (trapezoidal): "ondulada"/"sanduiche" davam a
# mesma verificacao e o mesmo n de tercas -> telha mais fraca ficava sub-provida.
# Ver varredura campo-do-wizard -> consumidor (telha_tipo, antes "cosmetico").
# ============================================================================
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS
import wizard as WZ
import telha_cobertura as T


def _spec(telha_tipo="trapezoidal", telha_peso=None):
    r = dict(area_lote_m2=957, to_max=0.60, span=20, comprimento=28.5, eave=8,
             v0=45, sigma_solo=150, fund_tipo="sapata",
             telha_tipo=telha_tipo)
    if telha_peso is not None:
        r["telha_peso"] = telha_peso
    return WZ.construir_spec(r, slug="t_telha")


def test_mapper_liga_telha_tipo_ao_perfil():
    """to_rodar_params deve injetar params['telha']['perfil'] a partir do tipo."""
    p = PS.to_rodar_params(_spec("ondulada"))
    assert "telha" in p and "perfil" in p["telha"], "telha_tipo nao chegou ao gate"
    assert p["telha"]["perfil"]["tipo"] == "ondulada"


@pytest.mark.parametrize("tipo,wef", [("ondulada", 3.0), ("trapezoidal", 7.5),
                                       ("sanduiche", 15.0)])
def test_tipo_seleciona_perfil_correto(tipo, wef):
    p = PS.to_rodar_params(_spec(tipo))
    assert p["telha"]["perfil"]["Wef"] == wef
    assert p["telha"]["perfil"]["ilustrativo"] is True


def test_tipos_dao_vao_max_ordenado():
    """Ordem fisica de rigidez: ondulada < trapezoidal < sanduiche -> vao_max
    admissivel crescente (telha mais forte vence vao maior)."""
    cfg = {"continuidade": "simples", "W_sucao": -2.0, "Q": 0.25}
    vmax = {}
    for tipo in ("ondulada", "trapezoidal", "sanduiche"):
        perfil = PS.to_rodar_params(_spec(tipo))["telha"]["perfil"]
        vmax[tipo] = T.vao_max(perfil, cfg)["vao_max_m"]
    assert vmax["ondulada"] < vmax["trapezoidal"] < vmax["sanduiche"], vmax


def test_telha_peso_do_usuario_sobrepoe():
    """cobertura.telha_peso (dado real do usuario) substitui o peso ilustrativo."""
    p = PS.to_rodar_params(_spec("trapezoidal", telha_peso=0.13))
    assert abs(p["telha"]["perfil"]["peso"] - 0.13) < 1e-9


def test_perfil_fabricante_sobrepoe_e_tira_flag_ilustrativo():
    """Se o spec traz o catalogo real (cobertura.telha_perfil com Wef), ele vence
    e o resultado deixa de ser ilustrativo."""
    s = _spec("ondulada")
    s["cobertura"]["telha_perfil"] = {"nome": "Fab X", "Wef": 9.9, "Ief": 25.0,
                                      "peso": 0.07, "fy": 300.0, "t": 0.8}
    p = PS.to_rodar_params(s)
    perf = p["telha"]["perfil"]
    assert perf["Wef"] == 9.9 and perf["ilustrativo"] is False


def test_verifica_telha_reporta_ilustrativo():
    perfil = T.catalogo_por_tipo("ondulada")
    r = T.verifica_telha(perfil, {"vao": 1.2, "continuidade": "simples",
                                  "W_sucao": -1.5})
    assert r["ilustrativo"] is True
    assert "ILUSTRATIVO" in T.relatorio_pt(r)
