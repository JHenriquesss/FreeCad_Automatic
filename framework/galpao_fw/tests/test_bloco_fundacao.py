# ============================================================================
# test_bloco_fundacao.py - BLOCO DE FUNDACAO (NBR 6122:2022 item 7.8.2): fundacao
# rasa de concreto SIMPLES, altura pelo angulo beta >= 60 graus, SEM armadura.
# Novo fund_tipo='bloco'. Ver memory normas-bloco-shed / bloco-fundacao-tipo-futuro.
# ============================================================================
import os
import sys
import math

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS
import wizard as WZ
import fundacao_sapata as fs


def test_bloco_beta_minimo_60():
    caso = {"sigma_solo_adm": 250.0, "mu": 0.5, "fck": 20e3, "b_ped": 0.30, "d_ped": 0.30}
    casos = [("C1_grav", 300.0, 20.0, 40.0), ("C1_uplift", 50.0, 30.0, 60.0)]
    r = fs.dimensiona_bloco_env(caso, casos)
    assert r["aprovado"] is not None
    B, L, h, beta = r["aprovado"]
    assert beta >= 60.0 - 1e-6, "bloco tem de ter beta >= 60 (NBR 6122 7.8.2)"
    # altura coerente com tan(60)*balanco
    bal = max((B - 0.30) / 2.0, (L - 0.30) / 2.0)
    assert h >= math.tan(math.radians(60.0)) * bal - 1e-9
    # concreto simples: sem armadura (a tabela nao traz As)
    assert "As_L" not in r["linhas"][0]
    assert r["sigma_t_adm"] <= 800.0 + 1e-6      # fck/25 <= 0,8 MPa


def test_bloco_e_tipo_valido():
    r = dict(area_lote_m2=1200, span=15, comprimento=30, eave=6, v0=40,
             sigma_solo=250, fund_tipo="bloco")
    s = WZ.construir_spec(r, slug="b")
    assert PS.validar(s)["ok"] is True
    assert "bloco" in PS.TIPOS_FUNDACAO
    p = PS.to_rodar_params(s)
    assert p["fundacao"]["tipo"] == "bloco"        # mapper leva o tipo ao rodar


def test_bloco_desenha_como_bloco_alto_no_3d():
    r = dict(area_lote_m2=1200, span=15, comprimento=30, eave=6, v0=40,
             sigma_solo=250, fund_tipo="bloco")
    s = WZ.construir_spec(r, slug="b")
    s.setdefault("estrutura", {})["sapata_adotada"] = {"B": 2.0, "L": 2.5, "h": 1.95,
                                                       "tipo": "bloco"}
    bk = PS.to_build_kwargs(s)
    assert bk["sapata"] and bk["sapata"]["h"] == 1950.0   # bloco alto desenhado
    assert bk.get("estaca") is None                        # nao e fundacao profunda


@pytest.mark.build
def test_bloco_roda_pipeline(tmp_path):
    import rodar_galpao as R
    r = dict(area_lote_m2=1200, span=15, comprimento=30, eave=6, bay=6, v0=40,
             sigma_solo=250, fund_tipo="bloco")
    s = WZ.construir_spec(r, slug="b")
    res = R.rodar(PS.to_rodar_params(s), str(tmp_path))
    sa = res["sapata_adotada"]
    assert sa and sa["tipo"] == "bloco" and sa["beta"] >= 60.0
    txt = open(os.path.join(str(tmp_path), "gate7-fundacao.txt"), encoding="utf-8").read()
    assert "BLOCO DE FUNDACAO" in txt and "NBR 6122" in txt
