"""CLASH DETECTION FEDERADO do turnkey: interferencia ENTRE disciplinas sobre o modelo
federado (AABB, puro-Python, CI). Convencao de dims: estrutural (concreto/aco) em metros,
instalacoes (eletrico/incendio) em mm; secao de barra sempre em metros. So pares de
disciplinas DIFERENTES (o intra-disciplina e' de cada vertical). Os clashes sao CANDIDATOS."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

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


# ------------------------------- AABB por convencao --------------------------
def test_aabb_caixa_estrutural_em_metros():
    # concreto/aco: dims de caixa em METROS -> x1000
    mb = {"marca": "C-SAP1", "dims": [2.0, 2.5, 0.7], "centro": [0.0, 0.0, 0.0]}
    a = tk._aabb_federado(mb, "concreto")
    assert a == (-1000.0, 1000.0, -1250.0, 1250.0, -350.0, 350.0)


def test_aabb_caixa_instalacao_em_mm():
    # eletrico/incendio: dims de caixa em MM -> x1
    mb = {"marca": "I-DET1", "dims": [120.0, 120.0, 60.0], "centro": [0.0, 0.0, 0.0]}
    a = tk._aabb_federado(mb, "incendio")
    assert a == (-60.0, 60.0, -60.0, 60.0, -30.0, 30.0)


def test_aabb_barra_engorda_pela_secao():
    mb = {"marca": "E-CALHA", "p1": [0.0, 0.0, 0.0], "p2": [1000.0, 0.0, 0.0],
          "secao": {"bf": 0.10, "d": 0.05}}
    x0, x1, y0, y1, z0, z1 = tk._aabb_federado(mb, "eletrico")
    assert (x0, x1) == (-50.0, 1050.0) and (y0, y1) == (-25.0, 25.0)


def test_aabb_barra_round_usa_D():
    mb = {"marca": "E-HASTE", "p1": [0.0, 0.0, 0.0], "p2": [0.0, 0.0, -3000.0],
          "secao": {"forma": "ROUND", "D": 0.016}}
    a = tk._aabb_federado(mb, "eletrico")
    assert a[0] == -8.0 and a[1] == 8.0                  # engorda +-D/2 = +-8 mm


def test_aabb_painel_ignorado():
    assert tk._aabb_federado({"marca": "A-P1", "poligono": [(0, 0, 0)]}, "aco") is None


def test_overlap_vol_toque_de_face_e_zero():
    a = (0.0, 100.0, 0.0, 100.0, 0.0, 100.0)
    b = (100.0, 200.0, 0.0, 100.0, 0.0, 100.0)           # encostam em x=100
    assert tk._overlap_vol(a, b) == 0.0
    c = (50.0, 150.0, 0.0, 100.0, 0.0, 100.0)            # penetra 50 em x
    assert tk._overlap_vol(a, c) > 0.0


# ------------------------- clash federado (sobre o modelo real) --------------
def test_clash_so_entre_disciplinas_diferentes():
    R = tk.rodar(_spec())
    rep = tk.checa_interferencia_federada(R, _spec())
    assert rep["n_clashes"] >= 1                          # o galpao tem conflitos reais
    for c in rep["clashes"]:
        da, db = c["disciplinas"].split("x")
        assert da != db                                  # nunca intra-disciplina
    # por_par soma o total e nenhuma chave repete disciplina
    assert sum(rep["por_par"].values()) == rep["n_clashes"]
    assert rep["OK"] is (rep["n_clashes"] == 0)


def test_clash_ordenado_por_volume_desc():
    rep = tk.checa_interferencia_federada(tk.rodar(_spec()), _spec())
    vols = [c["vol_mm3"] for c in rep["clashes"]]
    assert vols == sorted(vols, reverse=True)             # maiores primeiro


def test_clash_pega_spda_vs_estrutura():
    # o caso REAL conhecido: descida SPDA / haste de aterramento vs pilar/sapata (canto)
    rep = tk.checa_interferencia_federada(tk.rodar(_spec()), _spec())
    tipos = {c["tipos"] for c in rep["clashes"]}
    assert any("Cable" in t or "Earthing" in t for t in tipos)
    assert all(c["disciplinas"] == "concretoxeletrico" for c in rep["clashes"])


def test_vol_min_filtra_grazes():
    R = tk.rodar(_spec())
    baixo = tk.checa_interferencia_federada(R, _spec(), vol_min=1.0)
    alto = tk.checa_interferencia_federada(R, _spec(), vol_min=1e9)
    assert alto["n_clashes"] <= baixo["n_clashes"]       # limite maior -> menos (ou igual)
    assert alto["n_clashes"] == 0                         # 1e9 mm3 = 1 m3, nada tao grande


def test_relatorio_clash_pt_cita_candidatos():
    rep = tk.checa_interferencia_federada(tk.rodar(_spec()), _spec())
    txt = tk.relatorio_clash_pt(rep)
    assert "CLASH FEDERADO" in txt and "candidatos" in txt
    assert "concretoxeletrico" in txt


def test_clash_sem_disciplinas_vazio():
    # spec so com uma disciplina -> nenhum PAR entre disciplinas -> 0 clashes
    R = tk.rodar({"geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
                  "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0}}})
    rep = tk.checa_interferencia_federada(R)
    assert rep["n_clashes"] == 0 and rep["OK"] is True
