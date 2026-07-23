"""Modelo ANALITICO 2D do portico (nos/barras/apoios) - item 2, intercambio rico.

Extraido do galpao_portico (calculo, puro), NAO do build 3D -> sem risco de drift
com o FreeCAD. E a base do intercambio analitico (IFC-structural / SAF).
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import galpao_portico as gp
import modelo_neutro as MN

_SEC = dict(A_col=53.8e-4, I_col=3692e-8, A_raf=45.3e-4, I_raf=2510e-8)


@pytest.fixture(autouse=True)
def _reset_gp():
    # estado do galpao_portico e GLOBAL (SEC_COLS_PORTICO etc.); outro teste pode
    # te-lo sujado -> reset antes de cada teste deste modulo.
    gp.reset()
    yield


def test_um_vao_5nos_4barras():
    gp.configurar(span=20.0, eave=6.0, ridge=7.0, bay=5.0, base_fixed=True, **_SEC)
    m = gp.modelo_analitico()
    assert len(m["nos"]) == 5                          # 2 bases + 2 beirais + 1 cumeeira
    assert len(m["barras"]) == 4                       # 2 colunas + 2 rafters
    assert len(m["apoios"]) == 2
    assert {b["grupo"] for b in m["barras"]} == {"coluna", "rafter"}


def test_coordenadas_dos_nos():
    gp.configurar(span=20.0, eave=6.0, ridge=7.0, bay=5.0, base_fixed=True, **_SEC)
    m = gp.modelo_analitico()
    bases = [n for n in m["nos"] if n["papel"] == "base"]
    beirais = [n for n in m["nos"] if n["papel"] == "beiral"]
    cumeeira = [n for n in m["nos"] if n["papel"] == "cumeeira"][0]
    assert all(abs(b["y"]) < 1e-9 for b in bases)      # base em y=0
    assert all(abs(b["y"] - 6.0) < 1e-9 for b in beirais)   # beiral em y=eave
    assert abs(cumeeira["x"] - 10.0) < 1e-9 and abs(cumeeira["y"] - 7.0) < 1e-9


def test_apoio_engaste_vs_rotula():
    gp.configurar(span=20.0, eave=6.0, ridge=7.0, bay=5.0, base_fixed=True, **_SEC)
    assert gp.modelo_analitico()["apoios"][0]["tipo"] == "engaste"
    gp.configurar(span=20.0, eave=6.0, ridge=7.0, bay=5.0, base_fixed=False, **_SEC)
    a = gp.modelo_analitico()["apoios"][0]
    assert a["tipo"] == "rotula" and a["rot"] is False and a["v"] is True


def test_multivao_conta_colunas_internas():
    gp.configurar(spans=[10.0, 12.0], eave=6.0, ridge=7.5, bay=6.0, base_fixed=False, **_SEC)
    m = gp.modelo_analitico()
    assert len(m["nos"]) == 8                          # 3 bases + 3 beirais + 2 cumeeiras
    assert len(m["barras"]) == 7                       # 3 colunas + 4 rafters
    assert len(m["apoios"]) == 3


def test_barra_carrega_secao_AI():
    gp.configurar(span=20.0, eave=6.0, ridge=7.0, bay=5.0, base_fixed=True, **_SEC)
    col = [b for b in gp.modelo_analitico()["barras"] if b["grupo"] == "coluna"][0]
    assert abs(col["A"] - 53.8e-4) < 1e-9 and abs(col["I"] - 3692e-8) < 1e-12


def test_analitico_do_spec_e_json():
    spec = {"geometria": {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0,
                          "bay": 5.0, "base_fixed": True},
            "estrutura": {"perfil_col_adotado": "HEA200", "perfil_raf_adotado": "HEA180"}}
    m = MN.analitico_do_spec(spec)
    assert m and len(m["nos"]) == 5 and len(m["barras"]) == 4
    assert m["n_porticos"] == 9                        # 40/5 + 1
    assert m["secoes"]["coluna"] == "HEA200"
    f = os.path.join(tempfile.mkdtemp(), "a.json")
    MN.analitico_json(m, f)
    m2 = json.load(open(f, encoding="utf-8"))
    assert m2["barras"] == m["barras"] and m2["nos"] == m["nos"]


def test_analitico_do_spec_tapered_none():
    spec = {"geometria": {"span": 20.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0},
            "estrutura": {"perfil_col_adotado": None, "perfil_raf_adotado": None}}
    assert MN.analitico_do_spec(spec) is None
