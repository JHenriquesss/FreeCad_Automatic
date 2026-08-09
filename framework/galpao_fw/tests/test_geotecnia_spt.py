"""Ponte geotecnica SPT -> tensao admissivel + escolha de fundacao (rasa x
profunda). sigma_adm = N/50 (Exercicios de Fundacoes); Terzaghi (fatores de forma
do PDF); recalque elastico; recomendador sapata x estaca. Camada PURA (CI)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import geotecnia_spt as g


def test_selftest():
    assert g._selftest() is True


def test_sigma_adm_n_sobre_50():
    """PDF (Exercicios): sigma_adm = N/50 MPa p/ N>=20."""
    assert abs(g.sigma_adm_spt(25.0)[0] - 0.50) < 1e-9
    assert abs(g.sigma_adm_spt(30.0)[0] - 0.60) < 1e-9
    assert "valido" in g.sigma_adm_spt(20.0)[1]


def test_sigma_adm_faixas():
    """8<=N<20 presumido c/ alerta; N<8 -> None (fundacao profunda)."""
    v, nota = g.sigma_adm_spt(12.0)
    assert abs(v - 0.24) < 1e-9 and "PRESUMIDO" in nota
    assert g.sigma_adm_spt(6.0)[0] is None


def test_terzaghi_cresce_com_phi():
    a = g.capacidade_terzaghi(0.0, 18.0, 2.0, 10.0, 28.0, "quadrada")
    b = g.capacidade_terzaghi(0.0, 18.0, 2.0, 10.0, 38.0, "quadrada")
    assert b["sigma_adm_kNm2"] > a["sigma_adm_kNm2"] > 0


def test_terzaghi_argila_phi_zero():
    """phi=0 (argila): Nc=5,14, Nq=1, Ngama=0 (Prandtl)."""
    r = g.capacidade_terzaghi(50.0, 18.0, 2.0, 10.0, 0.0, "quadrada")
    assert abs(r["Nc"] - 5.14) < 0.02
    assert abs(r["Nq"] - 1.0) < 1e-9 and r["Ngama"] == 0.0


def test_terzaghi_fatores_forma_do_pdf():
    """Tab.4.1 lida do PDF: quadrada Sc=1,3 (>corrida 1,0) -> em argila (so o termo
    da coesao), quadrada da mais capacidade que corrida."""
    q = g.capacidade_terzaghi(50.0, 18.0, 2.0, 10.0, 0.0, "quadrada")
    c = g.capacidade_terzaghi(50.0, 18.0, 2.0, 10.0, 0.0, "corrida")
    assert q["sigma_R_kNm2"] > c["sigma_R_kNm2"]
    with pytest.raises(ValueError):
        g.capacidade_terzaghi(0, 18, 2, 10, 30, "hexagonal")


def test_recalque_monotono():
    r_alta = g.recalque_elastico(400.0, 2.0, 20000.0)
    r_baixa = g.recalque_elastico(200.0, 2.0, 20000.0)
    r_rigido = g.recalque_elastico(400.0, 2.0, 40000.0)
    assert r_alta > r_baixa > 0 and r_rigido < r_alta


def test_recomenda_sapata_solo_competente():
    rec = g.recomenda_fundacao([{"tipo": "areia", "N": 25, "dz": 6.0}], 600.0)
    assert rec["tipo"] == "sapata" and rec["sapata"]["sigma_adm_MPa"] > 0


def test_recomenda_estaca_solo_mole():
    perfil = [{"tipo": "argila", "N": 2, "dz": 6.0},
              {"tipo": "areia", "N": 32, "dz": 8.0}]
    rec = g.recomenda_fundacao(perfil, 700.0)
    assert rec["tipo"] == "estaca" and rec["z_camada_competente_m"] == 14.0


def test_recomenda_revisar_sem_camada_competente():
    perfil = [{"tipo": "argila", "N": 2, "dz": 6.0},
              {"tipo": "argila", "N": 4, "dz": 6.0}]
    rec = g.recomenda_fundacao(perfil, 700.0)
    assert rec["tipo"] == "revisar"


def test_n_medio_bulbo_pondera_por_espessura():
    """O N medio no bulbo (~2.B) pondera as camadas pela espessura interceptada."""
    perfil = [{"N": 10, "dz": 1.0}, {"N": 30, "dz": 10.0}]
    # cota_apoio 0.5, B=1 -> bulbo [0.5, 2.5]: 0.5 m de N=10 + 1.5 m de N=30
    N = g._n_medio_bulbo(perfil, 0.5, 1.0)
    assert abs(N - (10 * 0.5 + 30 * 1.5) / 2.0) < 1e-9


# ------------------- integracao com galpao_concreto --------------------------
def test_integra_galpao_concreto_deriva_sigma_do_spt():
    import galpao_concreto as gc
    spec = {"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0, "v0": 45.0,
            "perfil_spt": [{"tipo": "areia", "N": 24, "dz": 8.0}]}
    r = gc.rodar(spec)
    assert r["geotecnia"]["tipo"] == "sapata"
    assert r["tipo_fundacao"] == "sapata"          # auto-selecionado pelo SPT


def test_integra_galpao_concreto_auto_estaca():
    import galpao_concreto as gc
    spec = {"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0, "v0": 45.0,
            "perfil_spt": [{"tipo": "argila_arenosa", "N": 3, "dz": 6.0},
                           {"tipo": "areia", "N": 30, "dz": 8.0}]}
    r = gc.rodar(spec)
    assert r["tipo_fundacao"] == "estaca"          # SPT recomenda profunda


def test_integra_explicito_vence_recomendacao():
    """tipo_fundacao explicito do spec sempre vence a recomendacao do SPT."""
    import galpao_concreto as gc
    spec = {"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0, "v0": 45.0,
            "tipo_fundacao": "sapata", "sigma_solo_adm": 300.0,
            "perfil_spt": [{"tipo": "argila", "N": 2, "dz": 6.0},
                           {"tipo": "areia", "N": 30, "dz": 8.0}]}
    r = gc.rodar(spec)
    assert r["tipo_fundacao"] == "sapata"
