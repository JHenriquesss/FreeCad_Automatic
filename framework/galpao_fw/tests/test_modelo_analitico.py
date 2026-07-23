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


def test_analitico_do_spec_anexa_esforcos():
    # esforcos de projeto (do calculo) no spec -> anexados a cada barra por grupo
    spec = {"geometria": {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0,
                          "bay": 5.0, "base_fixed": True},
            "estrutura": {"perfil_col_adotado": "HEA200", "perfil_raf_adotado": "HEA180",
                          "esf_coluna": {"M_kNm": 120.0, "N_kN": 50.0, "V_kN": 20.0, "combo": "C1"},
                          "esf_rafter": {"M_kNm": 90.0, "N_kN": 40.0, "V_kN": 35.0, "combo": "C2"}}}
    m = MN.analitico_do_spec(spec)
    col = [b for b in m["barras"] if b["grupo"] == "coluna"][0]
    raf = [b for b in m["barras"] if b["grupo"] == "rafter"][0]
    assert col["esforcos"]["M_kNm"] == 120.0 and col["esforcos"]["combo"] == "C1"
    assert raf["esforcos"]["M_kNm"] == 90.0 and raf["esforcos"]["V_kN"] == 35.0


def test_analitico_do_spec_sem_esforcos_ok():
    # sem esf no spec -> barras sem 'esforcos' (so geometria), nao quebra
    spec = {"geometria": {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0,
                          "bay": 5.0, "base_fixed": True},
            "estrutura": {"perfil_col_adotado": "HEA200", "perfil_raf_adotado": "HEA180"}}
    m = MN.analitico_do_spec(spec)
    assert all("esforcos" not in b for b in m["barras"])


def test_analitico_do_spec_sem_perfil_none():
    # prismático SEM perfil laminado e SEM tapered -> None (via FreeCAD)
    spec = {"geometria": {"span": 20.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0},
            "estrutura": {"perfil_col_adotado": None, "perfil_raf_adotado": None}}
    assert MN.analitico_do_spec(spec) is None


_TAP = {"h_joelho": 0.90, "h_cumeeira": 0.40, "bf": 0.25, "tw": 0.008,
        "tf": 0.0125, "h_col_base": 0.45}


def test_analitico_tapered_nao_none_e_secao_variavel():
    # alma variável: agora tem analítico (antes None). A/I das seções soldadas
    # (av.props_I); cada barra carrega a seção de ponta em 'secao_var'.
    spec = {"geometria": {"span": 30.0, "comprimento": 40.0, "eave": 7.0, "ridge": 9.0,
                          "bay": 5.0, "base_fixed": True},
            "estrutura": {"tipo_portico": "alma_variavel", "tapered": _TAP}}
    m = MN.analitico_do_spec(spec)
    assert m and len(m["nos"]) == 5 and len(m["barras"]) == 4
    assert m["secoes"]["coluna"].startswith("VAR")
    col = [b for b in m["barras"] if b["grupo"] == "coluna"][0]
    raf = [b for b in m["barras"] if b["grupo"] == "rafter"][0]
    # coluna afina 450 -> 900 mm; rafter funda no joelho 900 -> rasa 400 mm
    assert abs(col["secao_var"]["d_i"] - 0.45) < 1e-9 and abs(col["secao_var"]["d_j"] - 0.90) < 1e-9
    assert abs(raf["secao_var"]["d_i"] - 0.90) < 1e-9 and abs(raf["secao_var"]["d_j"] - 0.40) < 1e-9
    # A/I representativos (barra) = seção do joelho (a mais funda)
    import alma_variavel as av
    pj = av.props_I(0.90, 0.25, 0.008, 0.0125)
    assert abs(col["A"] - pj["A"]) < 1e-9 and abs(col["I"] - pj["Ix"]) < 1e-12


def test_analitico_tapered_sem_h_col_base_coluna_constante():
    tap = {k: v for k, v in _TAP.items() if k != "h_col_base"}
    spec = {"geometria": {"span": 30.0, "comprimento": 40.0, "eave": 7.0, "ridge": 9.0,
                          "bay": 5.0, "base_fixed": True},
            "estrutura": {"tipo_portico": "alma_variavel", "tapered": tap}}
    m = MN.analitico_do_spec(spec)
    col = [b for b in m["barras"] if b["grupo"] == "coluna"][0]
    # sem h_col_base -> coluna constante na altura do joelho (d_i == d_j)
    assert abs(col["secao_var"]["d_i"] - 0.90) < 1e-9 and abs(col["secao_var"]["d_j"] - 0.90) < 1e-9
