"""Projeto executivo (pranchas A1 TechDraw) do galpao de concreto.

Duas camadas:
  1. PURO (sem FreeCAD): config_de_spec/script_bootstrap - os quadros, notas e o
     script injetado. techdraw_concreto so importa `os` + helpers do techdraw_exec
     (FreeCAD local), entao roda no CI.
  2. `build` (freecad.exe GUI): monta o 3D e GERA as pranchas de verdade (PDF/SVG).
     So na guarda local (skip sem freecad.exe).
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_concreto as gc
import techdraw_concreto as tdc

FREECAD_EXE = os.environ.get("FREECAD_EXE", r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe")


def _spec(vao=10.0, n=7, **kw):
    base = {"vao": vao, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": n,
            "v0": 40.0, "cat": "IV", "classe": "B", "s1": 1.0, "s3": 1.0,
            "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
            "sigma_solo_adm": 250.0}
    base.update(kw)
    return base


# ============================ camada 1: PURO ================================
def test_config_quadros_sapata():
    r = gc.rodar(_spec(vao=10.0))
    cfg = tdc.config_de_spec(r, "x.FCStd", "/out", _spec())
    assert cfg["geo"]["vao"] == 10000.0 and cfg["geo"]["comprimento"] == 40000.0
    assert cfg["geo"]["H"] == 6000.0 and cfg["geo"]["n"] == 7
    assert cfg["quadro_pilares"][0][1] == r["gates"]["pilar"]["secao"]
    assert cfg["quadro_fund_titulo"] == "QUADRO DE SAPATAS"
    B = r["sapata"]["aprovado"][0]
    assert cfg["quadro_fund"][0][1] == "%.0f" % (B * 100)   # B em cm
    # notas trazem fck e cobrimento REAIS (nao inventados)
    assert any("fck = 30 MPa" in l for l in cfg["notas"])
    assert any("30 mm" in l for l in cfg["notas"])           # cobrimento default
    assert any("CA-50" in l for l in cfg["notas"])           # fyk 500 -> CA-50


def test_carimbo_nao_vaza_aco_do_template_de_steel():
    # o carimbo generico defaulta 'ACO MR250' + tolerancias 'NBR 8800': numa prancha
    # de CONCRETO isso e material/norma errados. _carimbo_conc corrige.
    r = gc.rodar(_spec())
    cfg = tdc.config_de_spec(r, "x.FCStd", "/out", _spec())
    car = tdc._carimbo_conc(cfg, "PLANTA DE FORMAS", "PE-01", "1:100", "01/03")
    assert "MR250" not in car["part_material"]
    assert "CONCRETO C30" in car["part_material"]
    assert "CA-50" in car["part_material"]
    assert car["general_tolerances"] == "NBR 6118/9062"


def test_config_estaca_muda_quadro():
    perfil = [{"tipo": "argila", "N": 5, "dz": 3.0},
              {"tipo": "areia", "N": 25, "dz": 8.0}]
    r = gc.rodar(_spec(tipo_fundacao="estaca", perfil_spt=perfil,
                       D_estaca=0.30, L_estaca=10.0))
    cfg = tdc.config_de_spec(r, "x.FCStd", "/out", _spec())
    assert cfg["quadro_fund_titulo"] == "QUADRO DE ESTACAS"
    assert cfg["quadro_fund"][0][0] == "Estaca"
    assert cfg["quadro_fund"][0][1] == "30"       # D = 0,30 m -> 30 cm


def test_config_viga_protendida_quadro():
    r = gc.rodar(_spec(vao=15.0))               # vao grande -> protendida
    assert r["tipo_viga"] == "protendida"
    cfg = tdc.config_de_spec(r, "x.FCStd", "/out", _spec(vao=15.0))
    assert cfg["quadro_vigas_hdr"][2] == "PROTENSAO"
    assert "cord" in cfg["quadro_vigas"][0][2].lower()
    assert "cordoalhas" in cfg["viga_arm_lbl"]


def test_bootstrap_injeta_syspath_e_entry():
    r = gc.rodar(_spec())
    cfg = tdc.config_de_spec(r, "x.FCStd", "/out", _spec())
    src = tdc.script_bootstrap(cfg)
    assert "sys.path.insert" in src                          # resolve o irmao
    assert "_entry_concreto(_CFG_)" in src
    assert "QTimer" in src
    assert "def _pr_formas" in src                           # a fonte foi embutida
    # cfg embutido sem repr de numpy (np.float64(...) quebraria no freecad): checa
    # so a LINHA do _CFG_ (a fonte do modulo cita 'np.float64' num comentario)
    cfg_line = next(l for l in src.splitlines() if l.startswith("_CFG_ = "))
    assert "np.float64" not in cfg_line


def test_codigo_fonte_tem_as_pranchas():
    txt = tdc.codigo_fonte()
    for fn in ("_pr_formas", "_pr_portico", "_pr_quadros",
               "gerar_executivo_concreto", "_entry_concreto"):
        assert "def %s" % fn in txt


# ============================ camada 2: build ==============================
@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECAD_EXE), reason="freecad.exe ausente")
def test_build_gera_pranchas_pdf(tmp_path):
    r = gc.rodar(_spec(n=5))
    out = str(tmp_path).replace("\\", "/")
    # 1) modelo 3D (headless) -> FCStd
    m = gc.montar_3d(r, out, doc_name="t_exec_conc", headless=True, timeout=400)
    fcstd = (m.get("result") or {}).get("fcstd")
    assert fcstd and os.path.exists(fcstd), m
    # 2) pranchas A1 (freecad.exe GUI)
    res = gc.montar_pranchas(r, out, fcstd, spec=_spec(n=5), timeout=1200)
    assert res.get("ok"), res
    assert len(res.get("pranchas", [])) == 3
    pdfs = [a for a in res.get("arquivos", []) if a.endswith(".pdf")]
    assert len(pdfs) == 3 and all(os.path.exists(p) and os.path.getsize(p) > 0
                                  for p in pdfs), res
