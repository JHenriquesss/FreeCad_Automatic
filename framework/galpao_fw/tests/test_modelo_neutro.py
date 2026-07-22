"""Modelo neutro do portico primario (puro, sem FreeCAD) - item 2 do roteiro."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import modelo_neutro as MN

_SEC = {"col": {"nome": "HEA200", "d": 0.190, "bf": 0.200, "tw": 0.0065, "tf": 0.010},
        "raf": {"nome": "HEA180", "d": 0.171, "bf": 0.180, "tw": 0.006, "tf": 0.0095}}


def test_um_vao_conta_colunas_e_rafters():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    M = MN.frame_primario(geo, _SEC)
    r = MN.resumo(M)
    assert r["Column"] == 18 and r["Beam"] == 18       # 9 porticos x (2 col + 2 raf)


def test_coluna_vertical_da_base_ao_beiral():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    c = [m for m in MN.frame_primario(geo, _SEC) if m["tipo"] == "Column"][0]
    assert c["p1"][2] == 0.0 and abs(c["p2"][2] - 6000.0) < 1e-6
    assert c["p1"][0] == c["p2"][0] and c["p1"][1] == c["p2"][1]   # so Z varia


def test_rafter_sobe_do_beiral_a_cumeeira_no_meio_do_vao():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    v = [m for m in MN.frame_primario(geo, _SEC) if m["tipo"] == "Beam"][0]
    assert abs(v["p1"][2] - 6000.0) < 1e-6 and abs(v["p2"][2] - 7000.0) < 1e-6
    assert abs(v["p2"][1] - 10000.0) < 1e-6            # cumeeira no meio do vao 20 m


def test_multivao_colunas_internas_e_marcas():
    geo = {"spans": [10.0, 12.0], "comprimento": 30.0, "eave": 6.0,
           "ridge": 7.5, "bay": 6.0}
    M = MN.frame_primario(geo, _SEC)
    r = MN.resumo(M)
    assert r["Column"] == 18 and r["Beam"] == 24       # 6 porticos x (3 col + 4 raf)
    assert {m["marca"] for m in M if m["tipo"] == "Beam"} == {"V1", "V2"}


def test_n_porticos_escala_com_comprimento():
    base = {"span": 20.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    c30 = MN.resumo(MN.frame_primario({**base, "comprimento": 30.0}, _SEC))["Column"]
    c50 = MN.resumo(MN.frame_primario({**base, "comprimento": 50.0}, _SEC))["Column"]
    assert c30 == 2 * 7 and c50 == 2 * 11              # 30/5->7 ; 50/5->11 porticos


def test_secao_preservada_no_membro():
    geo = {"span": 20.0, "comprimento": 10.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    M = MN.frame_primario(geo, _SEC)
    c = [m for m in M if m["tipo"] == "Column"][0]
    assert c["secao"]["nome"] == "HEA200" and c["perfil"] == "HEA200"


def test_selftest_modulo():
    MN._selftest()
