import os
import sys

import pytest

GALPAO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)


@pytest.fixture
def turnkey_fixture():
    def make(**overrides):
        value = {
            "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
            "concreto": {"vao": 20.0, "n_porticos": 7, "v0": 40.0, "cat": "IV",
                         "classe": "B", "s1": 1.0, "s3": 1.0, "G_roof": 0.30,
                         "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
                         "sigma_solo_adm": 250.0},
            "eletrico": {"tensao_V": 380.0,
                         "cargas": {"iluminacao_kW": 20.0, "ilum_fp": 0.92,
                                    "ocupacao": "industrial"},
                         "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}},
            "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                         "deteccao": {"viga_m": 0.0}},
        }
        for key, value_override in overrides.items():
            value[key] = value_override
        return value

    return make


@pytest.fixture
def turnkey_fixture_with_hvac_and_hydraulic(turnkey_fixture):
    return turnkey_fixture(climatizacao={"tipo": "galpao"}, hidraulica={})
