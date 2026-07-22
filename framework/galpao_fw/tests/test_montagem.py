"""Plano de montagem / escoramento (NBR 8800 12.3 + AISC 303 + Bellei)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import montagem as M


def test_prumo_montagem_h_500():
    # 12.3.3.1.1: max(H/500 ; 5 mm) ; global 25 mm
    pr = M.tolerancia_prumo_montagem(6000.0)
    assert abs(pr["tol_mm"] - 12.0) < 1e-9 and pr["global_mm"] == 25.0


def test_prumo_montagem_piso_de_5mm():
    # coluna baixa: H/500 < 5 -> governa o piso de 5 mm
    assert abs(M.tolerancia_prumo_montagem(2000.0)["tol_mm"] - 5.0) < 1e-9


def test_peca_mais_pesada_considera_rafter_pre_montado():
    pecas = [{"marca": "C1", "peso_unit_kg": 253.5},
             {"marca": "V1", "peso_unit_kg": 320.0}]
    pp = M.peca_mais_pesada(pecas)                 # 2x320 (viga pre-montada)
    assert pp["marca"] == "V1" and abs(pp["peso_kg"] - 640.0) < 1e-9


def test_peca_mais_pesada_sem_pre_montagem():
    pecas = [{"marca": "C1", "peso_unit_kg": 253.5},
             {"marca": "V1", "peso_unit_kg": 320.0}]
    pp = M.peca_mais_pesada(pecas, rafter_pre_montado=False)
    assert abs(pp["peso_kg"] - 320.0) < 1e-9


def test_guindaste_impacto_e_momento_de_carga():
    g = M.guindaste_requerido(640.0, 8.0, 7.0, coef_impacto=1.10)
    assert abs(g["peso_icamento_kg"] - 704.0) < 1e-9
    assert abs(g["momento_carga_tm"] - 0.704 * 8.0) < 1e-2   # t.m
    assert "4.2.6" in g["obs"]                                # cita a norma


def test_estai_equilibrio_horizontal():
    # T = F/(n.cos a) ; comp = ancor = T.sen a
    e = M.estai_provisorio(10.0, 45.0, 1)
    assert abs(e["tracao_cabo_kN"] - 10.0 / math.cos(math.radians(45))) < 1e-2
    assert abs(e["comp_adicional_coluna_kN"] - 10.0) < 1e-2
    assert abs(e["forca_ancoragem_kN"] - 10.0) < 1e-2


def test_estai_dois_cabos_dividem_a_tracao():
    e1 = M.estai_provisorio(10.0, 45.0, 1)
    e2 = M.estai_provisorio(10.0, 45.0, 2)
    assert abs(e2["tracao_cabo_kN"] - e1["tracao_cabo_kN"] / 2.0) < 1e-2


def test_forca_montagem_aplica_gamma_construcao():
    # NBR 8800 4.9.6.5: gamma = 1,30
    assert abs(M.forca_lateral_montagem(1.0, 10.0) - 13.0) < 1e-9
    assert abs(M.GAMMA_CONSTRUCAO - 1.30) < 1e-9


def test_sequencia_tem_estai_e_ordem():
    seq = M.sequencia_montagem(1)
    assert len(seq) == 10
    joined = " ".join(seq).upper()
    assert "ESTAIAR" in joined and "CONTRAVENTAMENTO" in joined
    # o estai (passo 4) vem antes de remove-lo (passo 6)
    assert seq[3].startswith("4.") and "ESTAIAR" in seq[3].upper()


def test_plano_sem_dados_de_canteiro_marca_a_confirmar():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    pl = M.plano_montagem(geo, [{"marca": "V1", "peso_unit_kg": 320.0}])
    assert pl["n_porticos"] == 9
    assert "A CONFIRMAR" in pl["estai"]["obs"]        # sem q/area
    assert "A CONFIRMAR" in pl["guindaste"]["obs"]    # sem raio


def test_plano_completo_dimensiona():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    pl = M.plano_montagem(geo, [{"marca": "V1", "peso_unit_kg": 320.0}],
                          q_kNm2=0.8, area_exposta_m2=12.0, raio_m=8.0, n_estais=2)
    assert pl["estai"]["tracao_cabo_kN"] > 0
    assert pl["guindaste"]["momento_carga_tm"] > 0
    txt = M.relatorio_pt(pl)
    assert "PLANO DE MONTAGEM" in txt and "12.3.3.1.1" in txt


def test_plano_multivao_conta_colunas_internas():
    geo = {"spans": [10.0, 10.0], "comprimento": 30.0, "eave": 6.0,
           "ridge": 7.5, "bay": 6.0}
    pl = M.plano_montagem(geo, [{"marca": "V1", "peso_unit_kg": 300.0}])
    assert pl["nvaos"] == 2
    # passo 3 menciona colunas internas quando nvaos>1
    assert "interna" in pl["sequencia"][2].lower()
