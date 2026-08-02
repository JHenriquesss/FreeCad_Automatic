"""Nucleo BT do projeto eletrico (Fase 1): cargas, condutores, curto, protecao,
fator de potencia e o orquestrador galpao_eletrico. Tudo PURO (sem FreeCAD) -> CI.
Aferido contra exemplos resolvidos de Mamede/Creder lidos via NotebookLM."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import cargas_eletricas as ce
import condutores_nbr5410 as cd
import curto_circuito as cc
import protecao_nbr5410 as pr
import fator_potencia as fp
import aterramento_nbr15749 as at
import spda_nbr5419 as spda
import subestacao_nbr14039 as se
import galpao_eletrico as ge


# ---------------------- self-tests de cada modulo (aferidos em livro) --------
def test_selftests_dos_modulos():
    ce._selftest()
    cd._selftest()
    cc._selftest()
    pr._selftest()
    fp._selftest()
    at._selftest()
    spda._selftest()
    se._selftest()


# ------------------------------- cargas --------------------------------------
def test_demanda_motor_75cv_mamede():
    m = ce.demanda_motor({"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 1})
    assert abs(m["p_eixo_cv"] - 65.25) < 1e-6
    assert abs(m["D_kW"] - 52.2) < 0.1
    assert abs(m["D_kVA"] - 60.7) < 0.1


def test_fator_demanda_ocupacao_degraus():
    # escritorio: 100% ate 20 kW, 70% acima -> 30 kW = 27 kW
    assert abs(ce.fator_demanda_ocupacao(30.0, "escritorio") - 27.0) < 1e-9
    # industrial: sem degrau
    assert abs(ce.fator_demanda_ocupacao(50.0, "industrial") - 50.0) < 1e-9


def test_ocupacao_desconhecida_nao_inventa():
    import pytest
    with pytest.raises(ValueError):
        ce.fator_demanda_ocupacao(10.0, "inexistente")


# ------------------------------- condutores ----------------------------------
def test_condutor_chuveiro_creder_6mm2():
    IB = 6000.0 / 220.0
    r = cd.dimensiona_condutor({"IB": IB, "V": 220.0, "L_km": 0.018,
                                "sistema": "monofasico", "n_cond": 2, "isolacao": "PVC",
                                "metodo": "B1", "fp": 1.0, "temp_amb": 30.0,
                                "n_agrupados": 3, "uso": "forca", "dv_max": 4.0})
    assert r["secao_mm2"] == 6 and r["governante"] == "ampacidade"
    assert abs(r["dv_pct"] - 1.58) < 0.05


def test_condutor_curto_governa_secao():
    # Icc alto force a secao pelo criterio de curto
    r = cd.dimensiona_condutor({"IB": 20.0, "V": 380.0, "L_km": 0.01,
                                "sistema": "trifasico", "n_cond": 3, "isolacao": "PVC",
                                "metodo": "B1", "fp": 0.8, "temp_amb": 30.0,
                                "n_agrupados": 1, "uso": "forca", "dv_max": 5.0,
                                "Icc": 8000.0, "t_curto_s": 0.1})
    assert r["secao_curto"] is not None
    assert r["secao_mm2"] >= r["secao_curto"]


def test_fatores_correcao_tabelas():
    assert cd.fct(40, "PVC") == 0.87 and cd.fct(40, "EPR") == 0.91
    assert cd.fca(3) == 0.70 and cd.fca(6) == 0.57
    assert cd.K_CURTO["PVC"] == 115 and cd.K_CURTO["EPR"] == 143


# ------------------------------- curto ---------------------------------------
def test_icc_trafo_300kva_mamede():
    r = cc.icc_simetrica(300.0, 0.38, 4.5)
    assert abs(r["In"] - 455.8) < 0.1
    assert abs(r["Ik3"] - 10128.9) < 2.0


def test_fator_assimetria_limite():
    import math
    assert cc.fator_assimetria(1e6) < math.sqrt(3.0) + 1e-6


# ------------------------------- protecao ------------------------------------
def test_disjuntor_coordenacao():
    r = pr.dimensiona_disjuntor(27.27, 41.0)
    assert r["IN"] == 32 and r["OK"]
    assert pr.dimensiona_disjuntor(50.0, 41.0)["IN"] is None    # IB>IZ -> impossivel


def test_dps_por_exposicao():
    assert pr.classe_dps("direta")["classe"] == "I"
    assert pr.classe_dps("quadro")["classe"] == "II"


# ------------------------------- fator de potencia ---------------------------
def test_banco_capacitores_mamede():
    Qc = fp.potencia_reativa_capacitiva(500.0, 0.65, 0.90)
    assert abs(Qc - 342.4) < 1.0
    assert fp.corrige_fator_potencia(500.0, 0.95)["Qc_kVAr"] == 0.0


# ------------------------------- aterramento ---------------------------------
def test_haste_negrisoli_33ohm():
    R = at.resistencia_haste(100.0, 3.0, 0.02)
    assert abs(R - 33.9) < 0.1


def test_wenner_resistividade():
    assert abs(at.resistividade_wenner(4.0, 2.0) - 50.265) < 0.01


def test_malha_atinge_limite():
    r = at.dimensiona_aterramento({"tipo": "malha", "rho": 100.0, "A": 800.0,
                                   "L_cond": 400.0})
    assert r["R_ohm"] < at.R_MAX_SPDA and r["OK"]


# ------------------------------- spda ----------------------------------------
def test_area_exposicao_galpao():
    Ad = spda.area_exposicao(40.0, 20.0, 6.0)
    assert abs(Ad - 3977.88) < 0.1


def test_spda_niveis_e_descidas():
    assert spda.NIVEL_PROTECAO["I"]["esfera_m"] == 20
    assert spda.numero_descidas(120.0, "III") == 8
    r = spda.dimensiona_spda({"L": 40.0, "W": 20.0, "H": 6.0, "NP": "III",
                              "Ng": 5.0, "R1": 2e-5})
    assert r["secao_descida_mm2"] == 16 and r["secao_eletrodo_mm2"] == 50
    assert r["protecao_necessaria"] is True


# ------------------------------- subestacao MT -------------------------------
def test_subestacao_mamede_225kva():
    r = se.dimensiona_subestacao({"D_kVA": 210.0, "V_primaria_kV": 13.8,
                                  "V_secundaria_V": 380.0})
    assert r["Sn_kVA"] == 225 and abs(r["Inp_A"] - 9.41) < 0.02
    assert abs(r["Ins_A"] - 341.8) < 0.2
    assert r["protecao"]["tipo"] == "chave_fusivel_HH" and r["protecao"]["fusivel_HH_A"] == 16


def test_subestacao_acima_300_exige_disjuntor():
    r = se.dimensiona_subestacao({"D_kVA": 450.0})
    assert r["Sn_kVA"] == 500 and r["protecao"]["tipo"] == "disjuntor_rele"


def test_criterio_media_tensao():
    assert not se.exige_media_tensao(60.0)["media_tensao"]
    assert se.exige_media_tensao(200.0)["media_tensao"]
    assert se.exige_media_tensao(3000.0)["alta_tensao"]


# ------------------------------- orquestrador --------------------------------
def _spec(**kw):
    base = {"tensao_V": 380.0, "sistema": "trifasico", "origem": "subestacao_propria",
            "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2},
                                   {"P_cv": 30.0, "eta": 0.90, "Fp": 0.86, "n": 3}],
                       "iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
            "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR",
                            "temp_amb": 40.0, "n_agrupados": 1},
            "transformador": {"Sn_kVA": 300.0, "z_pct": 4.5}, "fp_desejado": 0.92,
            "geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "spda": {"NP": "III", "Ng": 5.0, "R1": 2e-5},
            "aterramento": {"tipo": "malha", "rho": 100.0, "A": 800.0, "L_cond": 400.0}}
    base.update(kw)
    return base


def test_rodar_gates_completos():
    r = ge.rodar(_spec())
    g = r["gates"]
    for k in ("cargas", "alimentador", "curto", "protecao", "fator_potencia", "circuitos"):
        assert k in g and "OK" in g[k]
    assert r["ATENDE"] is True
    assert g["cargas"]["D_kVA"] > 150 and g["cargas"]["fp_resultante"] < 0.92
    assert abs(g["curto"]["Icc_kA"] - 10.13) < 0.1
    assert g["alimentador"]["secao_mm2"] is not None
    assert g["fator_potencia"]["precisa_corrigir"] is True   # FP resultante < 0,92
    assert g["spda"]["NP"] == "III" and g["spda"]["n_descidas"] == 8
    assert g["aterramento"]["R_ohm"] is not None and g["aterramento"]["OK"]
    assert g["subestacao"]["necessaria"] and g["subestacao"]["Sn_kVA"] == 225


def test_sem_trafo_usa_trafo_da_subestacao():
    # sem transformador explicito, o curto cai no trafo escolhido pela subestacao
    sp = _spec()
    sp.pop("transformador")
    r = ge.rodar(sp)
    assert r["gates"]["curto"]["Icc_kA"] is not None          # veio da subestacao (225 kVA)
    assert r["gates"]["subestacao"]["Sn_kVA"] == 225


def test_carga_bt_sem_subestacao_icc_a_confirmar():
    # carga pequena (<= 75 kW): atendimento em BT, sem subestacao nem trafo -> Icc A CONFIRMAR
    sp = _spec(cargas={"iluminacao_kW": 10.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
               circuitos=[])
    sp.pop("transformador")
    r = ge.rodar(sp)
    assert r["gates"]["subestacao"]["necessaria"] is False
    assert r["gates"]["curto"]["Icc_kA"] is None
    assert "A CONFIRMAR" in r["gates"]["curto"]["nota"] and r["gates"]["curto"]["OK"]


def test_circuitos_terminais():
    sp = _spec(circuitos=[{"nome": "motor 75cv", "IB": 90.0, "V": 380.0, "L_km": 0.03,
                           "sistema": "trifasico", "n_cond": 3, "isolacao": "EPR",
                           "metodo": "F", "fp": 0.86, "temp_amb": 40.0,
                           "n_agrupados": 1, "uso": "forca", "dv_max": 5.0}])
    r = ge.rodar(sp)
    assert r["gates"]["circuitos"]["n"] == 1
    assert len(r["circuitos"]) == 1 and "condutor" in r["circuitos"][0]


def test_sem_geometria_spda_a_confirmar():
    sp = _spec()
    sp.pop("geometria"); sp.pop("spda"); sp.pop("aterramento")
    r = ge.rodar(sp)
    assert r["gates"]["spda"]["NP"] is None
    assert "A CONFIRMAR" in r["gates"]["spda"]["nota"] and r["gates"]["spda"]["OK"]
    assert "A CONFIRMAR" in r["gates"]["aterramento"]["nota"]


def test_relatorio_tem_virgula_decimal():
    r = ge.rodar(_spec())
    txt = ge.relatorio_pt(r)
    assert "kVA" in txt and "," in txt and "ATENDE" in txt
    assert "SPDA" in txt and "Aterramento" in txt
