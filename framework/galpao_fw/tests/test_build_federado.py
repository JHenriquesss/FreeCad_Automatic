"""Build 3D SOLIDO FEDERADO (build_federado): decomposicao dos membros neutros das 4
disciplinas em solidos (caixa / prisma orientado / cilindro), no frame comum. A camada
`solidos()`/`_por_disciplina` e' pura (CI); a realizacao OCCT + interferencia entre
disciplinas roda so com o freecadcmd (build)."""
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import build_federado as bf
import galpao_turnkey as tk


def _spec():
    return {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "concreto": {"vao": 20.0, "n_porticos": 7, "v0": 40.0, "cat": "IV",
                     "classe": "B", "s1": 1.0, "s3": 1.0, "G_roof": 0.30,
                     "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3, "sigma_solo_adm": 250.0},
        "eletrico": {"tensao_V": 380.0,
                     "cargas": {"iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
                     "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}},
        "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                     "deteccao": {"viga_m": 0.0}, "sprinklers": {"altura_estoque_m": 3.0}},
    }


# ------------------------------- camada PURA (CI) ----------------------------
def test_solidos_classifica_e_escala():
    membros = [
        {"marca": "C-P1", "tipo": "Column", "p1": [0, 0, 0], "p2": [0, 0, 6000],
         "secao": {"bf": 0.3, "d": 0.3}},
        {"marca": "E-HASTE", "tipo": "Earthing", "p1": [0, 0, -500], "p2": [0, 0, -3500],
         "secao": {"forma": "ROUND", "D": 0.016}},
        {"marca": "I-SPK", "tipo": "Sprinkler", "dims": [100, 100, 100], "centro": [0, 0, 5800]},
        {"marca": "C-SAP", "tipo": "Footing", "dims": [2.0, 2.5, 0.7], "centro": [0, 0, -350]},
        {"marca": "A-PANEL", "tipo": "Cladding", "poligono": [(0, 0, 0)]},   # ignorado
    ]
    sols = {s["name"]: s for s in bf.solidos(membros)}
    assert set(sols) == {"C-P1", "E-HASTE", "I-SPK", "C-SAP"}     # painel/cladding fora
    assert sols["C-P1"]["kind"] == "bar_rect" and sols["C-P1"]["comprimento_mm"] == 6000
    assert sols["E-HASTE"]["kind"] == "bar_round"
    # caixa estrutural em METROS (x1000): sapata 2x2.5x0.7 m -> 3.5 m3
    assert sols["C-SAP"]["kind"] == "box"
    assert abs(sols["C-SAP"]["vol_m3"] - 3.5) < 1e-9
    # caixa de instalacao em MM: sprinkler 100^3 mm = 1e-3 m3
    assert abs(sols["I-SPK"]["vol_m3"] - 0.001) < 1e-9


def test_solidos_barra_inclinada_dir_unitaria():
    mb = {"marca": "A-RAF", "tipo": "Beam", "p1": [0, 0, 6000], "p2": [3000, 10000, 7000],
          "secao": {"bf": 0.18, "d": 0.2}}
    s = bf.solidos([mb])[0]
    assert abs(s["comprimento_mm"] - math.dist(mb["p1"], mb["p2"])) < 1e-6
    assert abs(math.sqrt(sum(c * c for c in s["dir"])) - 1.0) < 1e-9   # unitaria


def test_por_disciplina_conta_e_soma():
    R = tk.rodar(_spec())
    membros, _ = tk._membros_federados(R, _spec())
    por = bf._por_disciplina(bf.solidos(membros))
    assert set(por) <= {"concreto", "eletrico", "incendio", "aco"}
    assert all(v["n"] > 0 and v["vol_m3"] >= 0 for v in por.values())


def test_caixa_aco_em_mm_nao_metros():
    # REGRESSAO (item 3): caixa do aco (Footing/Plate) ja em MM -> escala x1. O bug x1000
    # dava um bloco de km e um solido gigante que interferia com tudo no build federado.
    bloco = {"marca": "A-BLO1", "tipo": "Footing", "dims": [2500.0, 3000.0, 2350.0],
             "centro": [0.0, 0.0, -1175.0]}
    s = bf.solidos([bloco])[0]
    assert s["kind"] == "box" and s["dims"] == (2500.0, 3000.0, 2350.0)
    assert abs(s["vol_m3"] - (2.5 * 3.0 * 2.35)) < 1e-6         # ~17.6 m3, nao 1e9 m3
    # concreto continua em metros (x1000)
    sap = {"marca": "C-SAP", "tipo": "Footing", "dims": [2.0, 2.5, 0.7], "centro": [0, 0, -350]}
    sc = bf.solidos([sap])[0]
    assert sc["dims"] == (2000.0, 2500.0, 700.0)


def test_barra_comprimento_zero_ignorada():
    assert bf.solidos([{"marca": "E-X", "tipo": "Cable", "p1": [1, 2, 3],
                        "p2": [1, 2, 3], "secao": {"bf": 0.05, "d": 0.05}}]) == []


# ------------------------- build vivo (freecadcmd) ---------------------------
FCCMD = os.environ.get("FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FCCMD), reason="freecadcmd ausente")
def test_montar_3d_federado_vivo_e_consistente_com_aabb(tmp_path):
    R = tk.rodar(_spec())
    res = tk.montar_3d_federado(R, str(tmp_path), spec=_spec(), headless=True, timeout=480)
    r = res["result"]
    assert os.path.exists(r["fcstd"]) and os.path.exists(r["step"])
    assert r["n_solidos"] > 0
    # o OCCT (solido real) deve ser SUBSET do AABB (bounding) -> <= n_clashes do AABB
    aabb = tk.checa_interferencia_federada(R, _spec())
    assert r["n_interferencias_cross"] <= aabb["n_clashes"]


FCEXE = os.environ.get("FREECAD_EXE", r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe")


@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FCEXE), reason="freecad.exe (GUI) ausente")
def test_render_federado_gera_pngs(tmp_path):
    # render-and-look: freecad.exe GRAFICO -> PNGs isometrica/frontal/superior
    R = tk.rodar(_spec())
    res = tk.render_federado(R, str(tmp_path), spec=_spec(), timeout=420)
    assert res.get("erro") is None, res
    vistas = res.get("vistas") or []
    assert any("isometrica" in v for v in vistas)
    for v in vistas:
        assert os.path.exists(v) and os.path.getsize(v) > 0
