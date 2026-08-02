"""Hidrantes e mangotinhos (NBR 13714:2000): tipo de sistema por ocupacao, vazao por
saida, 2 jatos simultaneos, reserva V=Q*t e numero de hidrantes; e a integracao como
5o gate do vertical de seguranca contra incendio. Tudo PURO -> CI."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import hidrantes_nbr13714 as hd
import galpao_seguranca_incendio as gsi


def test_selftest():
    hd._selftest()


# ------------------------------ NBR 13714 (Tabela 1 / Anexo D / 5.4.2) --------
def test_tabela1_valores():
    assert hd.TIPO_SISTEMA[1]["vazao_Lmin"] == 100 and hd.TIPO_SISTEMA[1]["mangueira_mm"] == (25, 32)
    assert hd.TIPO_SISTEMA[2]["vazao_Lmin"] == 300 and hd.TIPO_SISTEMA[2]["orificio_mm"] == 16
    assert hd.TIPO_SISTEMA[3]["vazao_Lmin"] == 900 and hd.TIPO_SISTEMA[3]["orificio_mm"] == 25
    assert hd.TIPO_SISTEMA[3]["mangueira_mm"] == (65,)
    for t in (1, 2, 3):
        assert hd.TIPO_SISTEMA[t]["comp_max_m"] == 30


def test_anexo_D_galpao_industrial():
    # galpao/industria = Grupo I: I-1/I-2 -> Tipo 2 ; I-3 -> Tipo 3
    assert hd.tipo_por_ocupacao("industrial_I1") == (2, None)
    assert hd.tipo_por_ocupacao("industrial_I2") == (2, None)
    assert hd.tipo_por_ocupacao("industrial_I3") == (3, None)
    assert hd.tipo_por_ocupacao("residencial_A") == (1, 80)


def test_ocupacao_desconhecida_nao_inventa():
    with pytest.raises(ValueError):
        hd.tipo_por_ocupacao("inexistente")


def test_exigencia_area_altura():
    assert hd.exige_sistema(800.0, 6.0)          # area > 750
    assert hd.exige_sistema(500.0, 15.0)         # altura > 12
    assert not hd.exige_sistema(500.0, 6.0)


def test_reserva_V_igual_Q_vezes_t():
    # 5.4.2: Q = 2 saidas ; t = 60 (tipos 1/2) / 30 (tipo 3)
    assert hd.reserva_incendio(2) == (36000.0, 600.0, 60)     # 2*300*60
    assert hd.reserva_incendio(3) == (54000.0, 1800.0, 30)    # 2*900*30
    assert hd.reserva_incendio(1, 80)[0] == 9600.0            # 2*80*60


def test_dois_jatos_simultaneos():
    assert hd.N_JATOS_SIMULTANEOS == 2
    r = hd.dimensiona_hidrantes({"C": 40.0, "L": 20.0, "altura_m": 6.0})
    assert r["n_jatos_simultaneos"] == 2
    # vazao total = 2 x vazao de saida
    assert r["vazao_total_Lmin"] == 2 * r["vazao_saida_Lmin"]


def test_numero_hidrantes_min_dois_p_hidrante():
    # tipos 2/3 precisam de 2 esguichos em qualquer ponto -> minimo 2
    assert hd.numero_hidrantes(10.0, 10.0, 2) >= 2
    assert hd.numero_hidrantes(10.0, 10.0, 3) >= 2
    # galpao grande -> mais hidrantes (cobertura por mangueira 30 m)
    assert hd.numero_hidrantes(120.0, 60.0, 2) > hd.numero_hidrantes(40.0, 20.0, 2)


def test_alto_risco_tipo3_mangueira_65():
    r = hd.dimensiona_hidrantes({"C": 40.0, "L": 20.0, "altura_m": 6.0,
                                 "ocupacao": "industrial_I3"})
    assert r["tipo"] == 3 and r["mangueira_mm"] == (65,)
    assert r["reserva_incendio_m3"] == 54.0 and r["orificio_esguicho_mm"] == 25


def test_tipo_override():
    r = hd.dimensiona_hidrantes({"C": 40.0, "L": 20.0, "tipo": 1, "vazao_saida": 80})
    assert r["tipo"] == 1 and r["reserva_incendio_L"] == 9600.0


# ------------------------------ integracao no orquestrador -------------------
def test_gate_hidrantes_no_orquestrador():
    r = gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                   "hidrantes": {"ocupacao": "industrial_I2"}})
    h = r["gates"]["hidrantes"]
    assert h["tipo"] == 2 and h["reserva_m3"] == 36.0 and h["N_hidrantes"] >= 2 and h["OK"]


def test_gate_hidrantes_informativo_sem_spec():
    # sem spec de hidrantes, o gate e' informativo (OK, com nota) e nao reprova
    r = gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0}})
    h = r["gates"]["hidrantes"]
    assert h["tipo"] is None and h["OK"] and "nao informados" in h["nota"]


def test_altura_acionador_corrigida_5_5_2():
    import deteccao_alarme_nbr17240 as da
    # NBR 17240 5.5.2: 0,90 a 1,35 m (antes estava 1,40)
    assert da.ACIONADOR_ALTURA_M == (0.90, 1.35)
