"""Vertical de seguranca contra incendio (NBR 10898/16820/17240): iluminacao de
emergencia, sinalizacao e deteccao/alarme + orquestrador. Tudo PURO -> CI. Aferido
contra os valores das normas lidos via NotebookLM."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import iluminacao_emergencia_nbr10898 as ie
import sinalizacao_nbr16820 as sn
import deteccao_alarme_nbr17240 as da
import galpao_seguranca_incendio as si


def test_selftests_dos_modulos():
    ie._selftest()
    sn._selftest()
    da._selftest()


# --------------------------- iluminacao de emergencia ------------------------
def test_emergencia_niveis_e_espacamento():
    assert ie.iluminancia_minima("plano") == 3.0 and ie.iluminancia_minima("obstaculo") == 5.0
    assert ie.espacamento_aclaramento(6.0) == 15.0        # pd > 3,75 -> 15 m
    assert ie.espacamento_aclaramento(3.0, 3.0) == 12.0   # 4*h
    r = ie.dimensiona_iluminacao_emergencia({"C": 40.0, "L": 20.0, "pe_direito": 6.0,
                                             "fluxo_bloco_lm": 350.0})
    assert r["N_aclaramento"] == 6 and r["autonomia_h"] == 2.0 and r["comutacao_max_s"] == 2.0


def test_emergencia_fluxo_insuficiente_reprova():
    r = ie.dimensiona_iluminacao_emergencia({"C": 40.0, "L": 20.0, "pe_direito": 6.0,
                                             "fluxo_bloco_lm": 200.0})
    assert not r["OK"]


# --------------------------------- sinalizacao -------------------------------
def test_sinalizacao_distancia_e_placa():
    assert sn.distancia_visualizacao(100) == 4.0 and sn.distancia_visualizacao(300) == 12.0
    assert sn.placa_minima(10.0) == 250
    assert abs(sn.altura_letra_minima_mm(4.0) - 32.0) < 1e-9


def test_sinalizacao_numero_placas():
    assert sn.numero_placas_orientacao(60.0) == 5
    assert sn.numero_placas_orientacao(60.0, rota_continuada=True) == 21


# ------------------------------ deteccao e alarme ----------------------------
def test_deteccao_cobertura_por_viga():
    assert da.cobertura_detector(6.0) == 81.0
    assert abs(da.cobertura_detector(6.0, 0.3) - 54.0) < 1e-9
    assert da.cobertura_detector(6.0, 0.7) == 40.5
    assert da.cobertura_detector(9.0) is None             # teto > 8 m


def test_deteccao_pontual_vs_linear():
    assert da.numero_detectores_pontuais(800.0, 6.0) == 10
    d = da.dimensiona_deteccao_alarme({"C": 40.0, "L": 20.0, "altura_teto": 12.0})
    assert d["tipo_detector"] == "linear"                 # teto alto
    dp = da.dimensiona_deteccao_alarme({"C": 40.0, "L": 20.0, "altura_teto": 6.0})
    assert dp["tipo_detector"] == "pontual" and dp["N_detectores"] == 10


def test_deteccao_exemplo_nbr_12x23():
    # NBR 17240: 12 x 23 m -> 4 detectores pontuais
    assert da.numero_detectores_pontuais(12.0 * 23.0, 6.0) == 4


# --------------------------------- orquestrador ------------------------------
def _spec(**kw):
    base = {"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
            "deteccao": {"viga_m": 0.0}}
    base.update(kw)
    return base


def test_rodar_gates_completos():
    r = si.rodar(_spec())
    g = r["gates"]
    for k in ("iluminacao_emergencia", "sinalizacao", "deteccao_alarme"):
        assert k in g and "OK" in g[k]
    assert r["ATENDE"] is True
    assert g["deteccao_alarme"]["N_detectores"] == 10
    assert g["iluminacao_emergencia"]["N_aclaramento"] == 6
    assert g["sinalizacao"]["placa_lado_mm"] == 600


def test_galpao_alto_usa_detector_linear():
    r = si.rodar(_spec(geometria={"L": 40.0, "W": 20.0, "H": 12.0}))
    assert r["gates"]["deteccao_alarme"]["tipo_detector"] == "linear"
    # pe-direito alto (>3,75) mantem espacamento de aclaramento de 15 m
    assert r["iluminacao_emergencia"]["espacamento_max_m"] == 15.0


def test_relatorio_tem_virgula():
    txt = si.relatorio_pt(si.rodar(_spec()))
    assert "SEGURANCA CONTRA INCENDIO" in txt and "," in txt and "ATENDE" in txt
