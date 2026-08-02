"""Revisao total (gaps/bugs): entrada DEGENERADA (geometria/tensao/area/fator = 0 ou
negativa) deve virar ValueError LIMPO no padrao da casa, nao ZeroDivisionError cru.
Todos os pontos foram achados por harness adversarial. Puro -> CI."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_seguranca_incendio as gsi
import galpao_eletrico as ge
import galpao_concreto as gc
import luminotecnica_nbr8995 as lt


def test_incendio_geometria_nao_positiva():
    for geo in ({"L": 0, "W": 20, "H": 6}, {"L": 40, "W": 0, "H": 6},
                {"L": 40, "W": 20, "H": 0}, {"L": -40, "W": 20, "H": 6}):
        with pytest.raises(ValueError):
            gsi.rodar({"geometria": geo})
    # geometria valida ainda roda
    assert isinstance(gsi.rodar({"geometria": {"L": 40, "W": 20, "H": 6}})["ATENDE"], bool)


def test_eletrico_tensao_nao_positiva():
    with pytest.raises(ValueError):
        ge.rodar({"tensao_V": 0, "cargas": {"iluminacao_kW": 10}, "alimentador": {"L_km": 0.05}})
    with pytest.raises(ValueError):
        ge.rodar({"tensao_V": -380, "cargas": {"iluminacao_kW": 10}, "alimentador": {"L_km": 0.05}})


def test_concreto_geometria_nao_positiva():
    with pytest.raises(ValueError):
        gc.rodar({"vao": 0, "comprimento": 40, "pe_direito": 6, "sigma_solo_adm": 250})
    with pytest.raises(ValueError):
        gc.rodar({"vao": 10, "comprimento": 40, "pe_direito": 0, "sigma_solo_adm": 250})


def test_luminotecnica_area_e_fatores():
    base = {"pe_direito": 6, "atividade": "producao", "ambiente": "medio",
            "luminaria": "high_bay_led_100W"}
    with pytest.raises(ValueError):
        lt.projeto_luminotecnico(dict(base, C=0, L=0, Fu=0.6))
    with pytest.raises(ValueError):
        lt.projeto_luminotecnico(dict(base, C=40, L=20, Fu=0.0))
    # valido roda
    assert lt.projeto_luminotecnico(dict(base, C=40, L=20, Fu=0.6))["N_luminarias"] > 0


def test_turnkey_isola_geometria_invalida():
    # no turnkey, a geometria invalida vira ERRO ISOLADO da disciplina (nao derruba tudo)
    import galpao_turnkey as tk
    R = tk.rodar({"geometria": {"L": 0, "W": 0, "H": 0}, "incendio": {}})
    assert R["disciplinas"]["incendio"]["rodou"] is False
    assert "erro" in R["disciplinas"]["incendio"] and R["ATENDE"] is False
