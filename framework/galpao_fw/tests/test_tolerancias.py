"""Tolerancias de fabricacao/montagem (NBR 8800 + Bellei) - modulo puro."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tolerancias_fabricacao as T


def test_folga_furo_padrao_nbr8800_tab12():
    # NBR 8800:2024, Tabela 14 (D232): 20 -> 22 ; 22 -> 24 ; 24 -> 27 ; 30 -> 33
    assert abs(T.folga_furo(20.0) - 22.0) < 1e-9      # db<24 -> +2
    assert abs(T.folga_furo(22.0) - 24.0) < 1e-9
    assert abs(T.folga_furo(24.0) - 27.0) < 1e-9      # db>=24 -> +3
    assert abs(T.folga_furo(30.0) - 33.0) < 1e-9


def test_linhas_tem_fabricacao_montagem_furacao():
    ls = T.linhas_quadro()
    grupos = {g for g, *_ in ls}
    assert {"FABRICACAO", "MONTAGEM", "FURACAO"} <= grupos


def test_toda_linha_tem_fonte():
    for g, item, tol, fonte in T.linhas_quadro(db_mm=24.0):
        assert fonte and item and tol


def test_furacao_usa_db_quando_dado():
    ls = T.linhas_quadro(db_mm=24.0)
    furacao = [t for t in ls if t[0] == "FURACAO"][0]
    assert "27.0" in furacao[2]                        # db=24 -> 27,0 mm
    ls0 = T.linhas_quadro()
    furacao0 = [t for t in ls0 if t[0] == "FURACAO"][0]
    assert "db+2" in furacao0[2]


def test_prumo_e_empenamento_citam_nbr():
    ls = T.linhas_quadro()
    txt = " ".join(t[3] for t in ls)
    assert "NBR 8800" in txt
    # retilineidade L/1000 presente
    assert any("L/1000" in t[2] for t in ls)
