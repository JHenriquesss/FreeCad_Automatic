"""Torcao de vigas - NBR 6118:2014 17.5 (torcao_nbr6118.py).

Formulas conferidas no PDF NBR 6118:2014 (NotebookLM), nao de memoria:
- secao vazada equiv. (17.5.1.4.1): he = A/u (>= 2 c1) ; Ae dentro da linha media.
- biela (17.5.1.5): TRd2 = 0,50 alpha_v2 fcd Ae he sen(2 theta).
- estribo (17.5.1.6a): A90/s = Td/(fywd 2 Ae cotg theta).
- longitudinal (17.5.1.6b): Asl = Td ue tg(theta)/(fywd 2 Ae).
- V+T (17.7.2.2): Vsd/VRd2 + Tsd/TRd2 <= 1.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torcao_nbr6118 as tor


def test_secao_vazada_equivalente():
    g = tor.secao_vazada_equivalente(0.20, 0.50, 0.04)
    # he = A/u mas nao menor que 2 c1 = 0,08
    assert abs(g["he"] - max(0.10 / 1.4, 0.08)) < 1e-9
    assert g["Ae"] == (0.20 - g["he"]) * (0.50 - g["he"])


def test_biela_trd2_formula():
    r = tor.verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3, theta_deg=45.0)
    g = tor.secao_vazada_equivalente(0.20, 0.50, 0.04)
    fcd = 30e3 / 1.4; av2 = 1 - 30.0 / 250.0
    esperado = 0.50 * av2 * fcd * g["Ae"] * g["he"] * math.sin(math.radians(90))
    assert abs(r["TRd2"] - esperado) < 1.0


def test_theta_maior_trd2_maior():
    r30 = tor.verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3, theta_deg=30.0)
    r45 = tor.verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3, theta_deg=45.0)
    assert r45["TRd2"] > r30["TRd2"]              # sen(2*45)=1 > sen(60)


def test_torcao_alta_esmaga_biela():
    r = tor.verifica_torcao(300.0, 0.20, 0.50, 0.04, 30e3)
    assert not r["biela_ok"] and not r["OK"]


def test_armaduras_positivas():
    r = tor.verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3)
    assert r["A90_s_cm2_m"] > 0 and r["Asl_cm2"] > 0


def test_interacao_v_mais_t():
    it = tor.interacao_torcao_cortante(100.0, 400.0, 15.0, 60.0)
    assert abs(it["razao"] - 0.5) < 1e-9 and it["OK"]
    assert not tor.interacao_torcao_cortante(400.0, 400.0, 60.0, 60.0)["OK"]


def test_viga_concreto_wira_torcao():
    import viga_concreto as vc
    r = vc.verifica_viga({"vao": 6.0, "b": 0.20, "h": 0.50, "fck": 30e3, "fyk": 500e3,
                          "q": 15.0, "T_d": 18.0})
    assert r["torcao"] is not None and r["tor_ok"]
    assert "interacao" in r["torcao"]
    # sem T_d, torcao nao roda e nao interfere
    r0 = vc.verifica_viga({"vao": 6.0, "b": 0.20, "h": 0.50, "fck": 30e3, "fyk": 500e3,
                           "q": 15.0})
    assert r0["torcao"] is None and r0["tor_ok"]


def test_selftest_roda():
    tor._selftest()
