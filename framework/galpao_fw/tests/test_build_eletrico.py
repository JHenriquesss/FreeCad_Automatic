"""Build 3D do projeto eletrico (Fase 5). Camada PURA (caixas/_takeoff/classificador
de conexao) roda no CI; a camada `build` monta o 3D de verdade no freecadcmd headless
(skip sem FreeCAD)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_eletrico as ge
import build_eletrico as be

FREECADCMD = os.environ.get("FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


def _r(**kw):
    spec = {"tensao_V": 380.0, "sistema": "trifasico", "origem": "subestacao_propria",
            "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2},
                                   {"P_cv": 30.0, "eta": 0.90, "Fp": 0.86, "n": 3}],
                       "iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
            "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR", "temp_amb": 40.0},
            "geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "spda": {"NP": "III", "Ng": 5.0, "R1": 2e-5},
            "aterramento": {"tipo": "malha", "rho": 100.0, "A": 800.0, "L_cond": 400.0}}
    spec.update(kw)
    return ge.rodar(spec)


# ------------------------------ camada PURA ----------------------------------
def test_caixas_box_e_cilindro():
    mb = ge.membros_bim(_r())
    n_lum = sum(1 for m in mb if m["tipo"] == "Luminaire")
    n_tug = sum(1 for m in mb if m["tipo"] == "Outlet")
    cx = be.caixas(mb)
    box = [c for c in cx if c["solido"] == "box"]
    cyl = [c for c in cx if c["solido"] == "cyl"]
    # QGF + trafo + eletrocalha (3) + luminarias + tomadas (instalacao, tambem boxes)
    assert len(box) == 3 + n_lum + n_tug
    assert len(cyl) == 20           # 8 aterramento + 12 SPDA
    assert len(cx) == 23 + n_lum + n_tug
    assert n_lum >= 1 and n_tug >= 1


def test_haste_vertical_cilindro():
    cx = be.caixas(ge.membros_bim(_r()))
    haste = next(c for c in cx if c["name"].startswith("HASTE"))
    assert haste["solido"] == "cyl"
    assert haste["p1"][2] == -500.0 and haste["p2"][2] == -3500.0   # 3 m enterrada
    assert abs(haste["raio_mm"] - 8.0) < 1e-9                       # D=16mm


def test_eletrocalha_box_ao_longo_do_comprimento():
    cx = be.caixas(ge.membros_bim(_r()))
    calha = next(c for c in cx if c["tipo"] == "CableCarrier")
    assert calha["solido"] == "box"
    assert max(calha["dims"]) == 40000.0                            # corre no comprimento
    assert 100.0 in calha["dims"] and 50.0 in calha["dims"]         # secao 100x50 mm


def test_board_box_centrado():
    cx = be.caixas(ge.membros_bim(_r()))
    qgf = next(c for c in cx if c["tipo"] == "Board")
    # centro (1000,300,1000), dims (800,300,2000) -> origem no canto
    assert qgf["origem"] == (600.0, 150.0, 0.0)
    assert qgf["dims"] == (800.0, 300.0, 2000.0)


def test_classificador_de_conexao():
    # dois segmentos do anel que se encontram no canto (L,0) -> conexao
    a = {"solido": "cyl", "p1": (0.0, 0.0, 0.0), "p2": (40000.0, 0.0, 0.0)}
    b = {"solido": "cyl", "p1": (40000.0, 0.0, 0.0), "p2": (40000.0, 20000.0, 0.0)}
    assert be._conexao_condutores(a, b) is True
    # descida (endpoint sobre o corpo do anel) -> conexao
    desc = {"solido": "cyl", "p1": (10000.0, 0.0, 6000.0), "p2": (10000.0, 0.0, -500.0)}
    anel = {"solido": "cyl", "p1": (0.0, 0.0, -500.0), "p2": (40000.0, 0.0, -500.0)}
    assert be._conexao_condutores(desc, anel) is True
    # dois condutores distantes -> NAO conexao
    c = {"solido": "cyl", "p1": (0.0, 0.0, 5000.0), "p2": (0.0, 20000.0, 5000.0)}
    d = {"solido": "cyl", "p1": (20000.0, 10000.0, 0.0), "p2": (20000.0, 10000.0, 3000.0)}
    assert be._conexao_condutores(c, d) is False


def test_takeoff_comp_condutor():
    tk = be._takeoff(be.caixas(ge.membros_bim(_r())))
    assert tk["comp_condutor_m"] > 100.0            # anel+hastes+captacao+descidas
    assert "Cable" in tk["por_tipo"] and "Earthing" in tk["por_tipo"]


def test_tomadas_bim_recuam_da_linha_do_spda():
    membros = ge.membros_bim(_r())
    L, W = 40_000.0, 20_000.0
    tomadas = [m for m in membros if m["tipo"] == "Outlet"]

    assert tomadas
    assert all(min(m["centro"][0], L - m["centro"][0],
                   m["centro"][1], W - m["centro"][1]) >= 100.0
               for m in tomadas)


# ------------------------------ camada build ---------------------------------
@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECADCMD), reason="freecadcmd ausente")
def test_build_headless_gera_solidos_sem_clash(tmp_path):
    out = str(tmp_path).replace("\\", "/")
    res = ge.montar_3d(_r(), out, doc_name="t_elet_build", headless=True, timeout=400)
    rr = res.get("result") or {}
    assert rr.get("elementos") == len(be.caixas(ge.membros_bim(_r()))), res
    assert rr.get("interferencias") == 0, rr.get("interferencias_lista")
    assert rr.get("conexoes", 0) > 0               # a rede bonda nas juncoes
    fc = rr.get("fcstd")
    assert fc and os.path.exists(fc)
    assert rr.get("ifc") and rr.get("step")
