# ============================================================================
# test_fase618_viga_equilibrio.py - RED tests da Fase 6.18.
# Bloco de divisa sobre estacas + viga de equilibrio (variante PROFUNDA da
# fundacao de divisa). Estatica de corpo rigido R'=P.l/(l-e) (Alonso/Velloso),
# ja validada em sapata_divisa; aqui aplicada a grupo de estacas + viga RC.
# ============================================================================
import os
import sys
import math
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import viga_equilibrio as ve


def _r(**kw):
    base = dict(P_divisa=1400.0, P_interno=1900.0, dist_eixos=5.5, dist_divisa=0.20,
                P_estaca_adm=700.0, a_pilar=0.40, D_estaca=0.40)
    base.update(kw)
    return ve.dimensiona_viga_equilibrio(**base)


def test_reacao_amplificada_pelo_braco():
    r = _r()
    e = r["divisa"]["e"]
    R_esp = 1400.0 * 5.5 / (5.5 - e)
    assert abs(r["divisa"]["R"] - R_esp) < 1.0
    assert r["divisa"]["R"] > 1400.0                 # amplifica


def test_excentricidade_maior_amplifica_mais():
    r1 = _r(e=0.5)
    r2 = _r(e=1.0)
    assert r2["divisa"]["R"] > r1["divisa"]["R"]


def test_numero_de_estacas_cobre_reacao():
    r = _r()
    d = r["divisa"]
    assert d["n_estacas"] >= math.ceil(d["R"] / 700.0)
    assert d["carga_estaca"] <= 700.0 + 1e-6


def test_alivio_no_pilar_interno():
    r = _r()
    i = r["interno"]
    assert i["delta_P"] > 0
    assert i["P_ajust"] < 1900.0
    assert abs(i["P_ajust"] - (1900.0 - 0.5 * i["delta_P"])) < 0.2


def test_viga_tracao_superior_passa():
    r = _r()
    v = r["viga"]
    assert v["ok_flexao"] is True
    assert v["M_max_kNm"] > 0 and v["As_adot_cm2"] >= v["As_min_cm2"]


def test_momento_viga_e_P_vezes_e_nao_R():
    # parecer item 48: estatica de corpo rigido -> M = P_divisa*e (NAO R'*e).
    r = _r()
    d = r["divisa"]; v = r["viga"]
    assert abs(v["M_max_kNm"] - 1400.0 * d["e"]) < 0.02        # M = P*e
    assert v["M_max_kNm"] < d["R"] * d["e"] - 1.0              # estritamente < R*e (antigo)
    # coerencia: Delta_P*(l-e) == P*e
    dP = r["interno"]["delta_P"]
    assert abs(dP * (5.5 - d["e"]) - 1400.0 * d["e"]) < 1.0


def test_viga_verifica_cisalhamento():
    # cortante obrigatorio (NBR 6118 17.4): V = Delta_P; biela VRd2 nao esmaga; estribo.
    r = _r()
    v = r["viga"]; i = r["interno"]
    assert abs(v["V_max_kN"] - i["delta_P"]) < 0.2            # V = Delta_P
    assert v["ok_cortante"] is True and v["VRd2_kN"] > v["V_d_kN"]
    assert v["s_estribo_cm"] > 0 and v["VRd3_min_kN"] > 0


def test_peso_proprio_conta_nas_estacas():
    # peso proprio (~5%) majora a reacao usada na contagem de estacas
    r = _r()
    d = r["divisa"]
    assert d["n_estacas"] >= math.ceil(1.05 * d["R"] / 700.0)


def test_excentricidade_estimada_geometrica():
    e = ve.excentricidade_estimada(dist_divisa=0.20, D_estaca=0.40)
    # 2 estacas, s=3D=1.2: x_centroide = 0.2 + 0.15 + 0.6 = 0.95; e = 0.95-0.20=0.75
    assert abs(e - 0.75) < 1e-9


def test_relatorio_pt_gera():
    txt = ve.relatorio_pt(_r())
    assert "VIGA DE EQUILIBRIO" in txt and "A CONFIRMAR" in txt


def test_wiring_rodar_galpao_escolhe_estaca():
    # com estaca + divisa, rodar_galpao deve produzir res["divisa"]["tipo"]=="estaca"
    import rodar_galpao as rg
    import inspect
    src = inspect.getsource(rg.calcular) if hasattr(rg, "calcular") else ""
    # a fonte deve conter o branch de viga_equilibrio p/ o caso estaca
    fonte = inspect.getsource(rg)
    assert "viga_equilibrio" in fonte and 'res.get("estaca")' in fonte
