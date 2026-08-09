"""Executivo do projeto eletrico (Fase 6): diagrama unifilar + quadro de cargas
(desenho_eletrico, SVG puro) e pranchas A1 (techdraw_eletrico). Camada pura em CI;
a geracao real das pranchas roda no freecad.exe (guarda `build`, skip sem FreeCAD)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_eletrico as ge
import desenho_eletrico as de
import techdraw_eletrico as tde

FREECAD_EXE = os.environ.get("FREECAD_EXE", r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe")
FREECADCMD = os.environ.get("FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


def _spec(**kw):
    base = {"tensao_V": 380.0, "sistema": "trifasico", "origem": "subestacao_propria",
            "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2},
                                   {"P_cv": 30.0, "eta": 0.90, "Fp": 0.86, "n": 3}],
                       "iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
            "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR", "temp_amb": 40.0},
            "transformador": {"Sn_kVA": 300.0, "z_pct": 4.5},
            "geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "spda": {"NP": "III", "Ng": 5.0, "R1": 2e-5},
            "aterramento": {"tipo": "malha", "rho": 100.0, "A": 800.0, "L_cond": 400.0}}
    base.update(kw)
    return base


def _r(**kw):
    return ge.rodar(_spec(**kw))


# ------------------------------ desenho (SVG puro) ---------------------------
def test_unifilar_svg_tem_elementos():
    uni = de.diagrama_unifilar_svg(_r())
    assert uni.startswith("<svg") and uni.rstrip().endswith("</svg>")
    for tok in ("DIAGRAMA UNIFILAR", "QGF", "TR1", "DISJ. GERAL", "DPS",
                "ATERRAMENTO", "SPDA NP III", "motores", "BANCO CAP"):
        assert tok in uni, tok


def test_unifilar_sem_subestacao_entrada_bt():
    sp = _spec()
    sp.pop("transformador")
    sp["cargas"] = {"iluminacao_kW": 10.0, "ilum_fp": 0.92, "ocupacao": "industrial"}
    uni = de.diagrama_unifilar_svg(ge.rodar(sp))
    assert "ENTRADA BT" in uni and "TR1" not in uni


def test_quadro_cargas_svg():
    qc = de.quadro_cargas_svg(_r())
    assert "QUADRO DE CARGAS" in qc and "Alimentador geral" in qc


def test_svgs_sao_xml_bem_formado():
    """REGRESSAO: SVG e' XML - tem de fazer PARSE, nao so conter substrings.
    O bug era 'R <= 10 ohm' (aterramento A CONFIRMAR) com '<' cru -> unifilar
    inteiro malformado, recusado pelo QtSvg/DrawViewSymbol da prancha A1. O
    _spec() padrao tem aterramento com R calculado (emite 'R = ...'), desviando
    do caminho quebrado; aqui forcamos o caminho 'A CONFIRMAR' (sem aterramento)."""
    from xml.dom.minidom import parseString
    sp = _spec()
    sp.pop("aterramento", None)          # -> 'R <= 10 ohm (A CONFIRMAR)'
    r = ge.rodar(sp)
    uni = de.diagrama_unifilar_svg(r)
    assert "&lt;" in uni                 # o '<' do texto foi escapado
    parseString(uni.encode("utf-8"))     # levanta se malformado
    parseString(de.quadro_cargas_svg(r).encode("utf-8"))


# ------------------------------ techdraw (config puro) -----------------------
def test_config_de_spec_eletrico():
    cfg = tde.config_de_spec(_r(), "x.FCStd", "/out", _spec())
    assert cfg["carimbo_material"].startswith("MT 13.8 kV / BT 380")
    assert cfg["geo"]["L"] == 40000.0 and cfg["geo"]["W"] == 20000.0
    assert cfg["unifilar_svg"].startswith("<svg")
    assert cfg["quadro_cargas"][0][0] == "Alimentador geral (QGF)"
    assert any("NBR 5410" in n for n in cfg["notas"])
    assert any("SPDA" in n for n in cfg["notas"])


def test_carimbo_nao_vaza_aco():
    cfg = tde.config_de_spec(_r(), "x.FCStd", "/out", _spec())
    car = tde._carimbo_elet(cfg, "DIAGRAMA UNIFILAR", "PE-EL-01", "S/ESC", "01/03")
    assert "MR250" not in car["part_material"] and "ACO" not in car["part_material"]
    assert "BT 380" in car["part_material"]
    assert car["general_tolerances"] == "NBR 5410/5419"


def test_bootstrap_injeta_entry_e_fonte():
    cfg = tde.config_de_spec(_r(), "x.FCStd", "/out", _spec())
    src = tde.script_bootstrap(cfg)
    assert "sys.path.insert" in src
    assert "_entry_eletrico(_CFG_)" in src
    assert "def _pr_unifilar" in src and "QTimer" in src
    cfg_line = next(l for l in src.splitlines() if l.startswith("_CFG_ = "))
    assert "np.float64" not in cfg_line


def test_codigo_fonte_tem_as_pranchas():
    txt = tde.codigo_fonte()
    for fn in ("_pr_unifilar", "_pr_planta", "_pr_quadros",
               "gerar_executivo_eletrico", "_entry_eletrico"):
        assert "def %s" % fn in txt


# ------------------------------ build (freecad.exe) --------------------------
@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECAD_EXE), reason="freecad.exe ausente")
def test_build_gera_pranchas_pdf(tmp_path):
    r = _r()
    out = str(tmp_path).replace("\\", "/")
    m = ge.montar_3d(r, out, doc_name="t_exec_elet", headless=True, timeout=400)
    fcstd = (m.get("result") or {}).get("fcstd")
    assert fcstd and os.path.exists(fcstd), m
    res = ge.montar_pranchas(r, out, fcstd, spec=_spec(), timeout=1200)
    assert res.get("ok"), res
    assert len(res.get("pranchas", [])) == 3
    pdfs = [a for a in res.get("arquivos", []) if a.endswith(".pdf")]
    assert len(pdfs) == 3 and all(os.path.exists(p) and os.path.getsize(p) > 0
                                  for p in pdfs), res
