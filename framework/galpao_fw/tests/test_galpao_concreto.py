"""Galpao de concreto pre-moldado - orquestrador galpao_concreto.py.

Sistema: pilares engastados (balanco) + viga de cobertura biapoiada + sapata,
reusando vento_nbr6123 / viga_concreto / pilar_concreto / fundacao_sapata.
STATELESS (rodar(spec) recebe dict explicito - sem estado global).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import galpao_concreto as gc


def _spec(vao=10.0, **kw):
    base = {"vao": vao, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
            "v0": 40.0, "cat": "IV", "classe": "B", "s1": 1.0, "s3": 1.0,
            "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
            "sigma_solo_adm": 250.0}
    base.update(kw)
    return base


def test_galpao_rc_tipico_atende():
    r = gc.rodar(_spec(vao=10.0))
    assert r["ATENDE"] and not r["reprovados"]
    for k in ("vento", "viga_cobertura", "pilar", "fundacao"):
        assert r["gates"][k]["OK"], k


def test_vento_gera_momento_de_base():
    # w_h = (Cpe_bar - Cpe_sot)*q*s = 1,30*q*s ; M_base = w_h*H^2/2
    r = gc.rodar(_spec())
    q = r["vento"]["q_kN_m2"]; s = r["spec"]["s"]; H = r["spec"]["H"]
    assert abs(r["gates"]["vento"]["w_h"] - 1.30 * q * s) < 0.05
    assert abs(r["gates"]["vento"]["M_base_k"] - 1.30 * q * s * H ** 2 / 2.0) < 0.5


def test_pilar_e_balanco_le_2H():
    r = gc.rodar(_spec())
    # o pilar do galpao e balanco: le = 2H em ambas direcoes
    assert abs(r["pilar"]["dir"]["x"]["le"] - 2 * r["spec"]["H"]) < 1e-9


def test_vao_grande_reprova_viga_rc():
    # 15 m biapoiado em concreto armado nao fecha -> gate da viga REPROVA (honesto)
    r = gc.rodar(_spec(vao=15.0))
    assert not r["gates"]["viga_cobertura"]["OK"]
    assert not r["ATENDE"] and "viga_cobertura" in r["reprovados"]


def test_solo_fraco_reprova_fundacao_ou_cresce():
    # solo muito fraco: a sapata cresce; se nem a maior passa, gate REPROVA
    r = gc.rodar(_spec(sigma_solo_adm=40.0))
    # nao deve estourar; fundacao decide OK/REPROVA sem exception
    assert isinstance(r["gates"]["fundacao"]["OK"], bool)


def test_stateless_dois_specs_nao_interferem():
    r1 = gc.rodar(_spec(vao=8.0))
    r2 = gc.rodar(_spec(vao=12.0))
    assert r1["spec"]["vao"] == 8.0 and r2["spec"]["vao"] == 12.0
    assert r1["viga"]["h"] <= r2["viga"]["h"]      # vao maior -> viga maior/igual


def test_selftest_roda():
    gc._selftest()
