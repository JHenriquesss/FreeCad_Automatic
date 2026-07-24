"""Concreto em situacao de INCENDIO - metodo tabular NBR 15200:2024 (fogo_nbr15200.py).

Valores das tabelas conferidos no PDF da NBR 15200:2024 (NotebookLM), nao de memoria:
- Tabela 4 (vigas biapoiadas): bmin/c1 alternativos + bw,min por TRRF.
- Tabela 12 (pilar 1 face): 155/25 (30/60/90) ; 175/35 (120) ; 230/55 (180).
- Tabela 13 (pilar-parede): por mu_fi (0,35/0,70) e nº de faces.
Protendido: c1 exigido soma 10 mm (barra) / 15 mm (fio/cordoalha).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fogo_nbr15200 as fogo


def test_viga_tabela4_combo_governante():
    # 200x600, c1=45, TRRF 60: combo 190/30 (maior bmin<=200) -> c1_req 30 -> ATENDE
    v = fogo.verifica_viga_fogo(200, 45, 60)
    assert v["OK"] and v["c1_req"] == 30


def test_viga_reprova_largura_menor_que_bmin():
    v = fogo.verifica_viga_fogo(100, 60, 60)     # menor bmin da Tab.4/TRRF60 e 120
    assert not v["OK"] and "largura" in v["motivo"]


def test_viga_protendida_acrescenta_c1():
    # combo 300/25 no TRRF 60, protendida com cordoalha -> c1_req 25+15 = 40
    vp = fogo.verifica_viga_fogo(300, 40, 60, protendida=True, cordoalha=True)
    assert vp["c1_req"] == 40 and vp["OK"]
    # barra protendida: +10
    vb = fogo.verifica_viga_fogo(300, 40, 60, protendida=True, cordoalha=False)
    assert vb["c1_req"] == 25 + 10


def test_pilar_1face_tabela12():
    p = fogo.verifica_pilar_fogo(160, 30, 120, faces_expostas=1)
    assert p["bmin_req"] == 175 and p["c1_req"] == 35   # TRRF 120 -> 175/35
    assert not p["OK"]                                    # 160 < 175
    p2 = fogo.verifica_pilar_fogo(180, 40, 120, faces_expostas=1)
    assert p2["OK"]


def test_pilar_multiface_exige_anexo_E():
    # pilar retangular comum com >1 face exposta: tabular simples nao cobre
    p = fogo.verifica_pilar_fogo(200, 30, 90, faces_expostas=4)
    assert p["OK"] is None and p["requer_anexo_E"]


def test_pilar_parede_tabela13():
    # mu_fi 0,70 ; 2 faces ; TRRF 120 -> 220/35
    pp = fogo.verifica_pilar_fogo(220, 35, 120, faces_expostas=2, pilar_parede=True, mu_fi=0.70)
    assert pp["bmin_req"] == 220 and pp["c1_req"] == 35 and pp["OK"]
    # carga menor (mu_fi 0,35) alivia: 160/25 no mesmo TRRF
    pp2 = fogo.verifica_pilar_fogo(160, 25, 120, faces_expostas=2, pilar_parede=True, mu_fi=0.35)
    assert pp2["bmin_req"] == 160 and pp2["c1_req"] == 25 and pp2["OK"]


def test_trrf_invalido_levanta():
    try:
        fogo.verifica_viga_fogo(200, 40, 45)
        assert False
    except ValueError:
        pass


def test_c1_efetivo_geometrico():
    # c1 = cob + estribo + phi/2
    assert fogo.c1_efetivo(30, 5, 20) == 30 + 5 + 10


def test_selftest_roda():
    fogo._selftest()
