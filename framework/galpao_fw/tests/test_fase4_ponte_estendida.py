# ============================================================================
# test_fase4_ponte_estendida.py - RED tests da Fase 4 (ponte rolante estendida).
#  (a) frac_long nas RODAS MOTORAS (mecanica NBR 8800).
#  (b) coef. dinamico phi + n de ciclos da NBR 8400-1:2019 (Tab.12 / Tab.9),
#      lidos do PDF (zero-erro) -> alimentam impacto e fadiga Anexo K.
#  (c) gate de validacao da ponte no ProjetoSpec (dados do fabricante bloqueiam).
# ============================================================================
import os
import sys
import copy
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS
import ponte_rolante as pr


# ======================= me-1: NBR 8400 (phi + ciclos) ======================
def test_nbr8400_coef_dinamico_tab12():
    import nbr8400 as n8
    # Psi = Psimin + beta2*Vh (Tab.12). Vh=0 -> Psimin.
    assert abs(n8.coef_dinamico("HC1", 0.0) - 1.05) < 1e-9
    assert abs(n8.coef_dinamico("HC2", 0.0) - 1.10) < 1e-9
    assert abs(n8.coef_dinamico("HC3", 0.0) - 1.15) < 1e-9
    assert abs(n8.coef_dinamico("HC4", 0.0) - 1.20) < 1e-9
    # HC4, Vh=1,0 m/s -> 1,20 + 0,68*1,0 = 1,88
    assert abs(n8.coef_dinamico("HC4", 1.0) - 1.88) < 1e-9


def test_nbr8400_coef_dinamico_cap_vh():
    import nbr8400 as n8
    # Vh limitado a 1,5 m/s (acima nao aumenta Psi)
    assert n8.coef_dinamico("HC2", 2.0) == n8.coef_dinamico("HC2", 1.5)


def test_nbr8400_coef_classe_invalida():
    import nbr8400 as n8
    with pytest.raises(Exception):
        n8.coef_dinamico("HC9", 0.5)


def test_nbr8400_n_ciclos_tab9():
    import nbr8400 as n8
    # Tab.9: B7 = 1e6 <= n < 2e6 ; representativo conservador = limite superior
    assert n8.n_ciclos("B7") == 2_000_000
    assert n8.n_ciclos("B0") == 16_000
    assert n8.n_ciclos("B10") >= 8_000_000
    # monotonico
    assert n8.n_ciclos("B3") < n8.n_ciclos("B6")


# ============= me-2: frac_long nas rodas motoras (mecanica) ==================
def test_frac_long_rodas_motoras():
    # 1 roda motora de 2 -> metade da forca longitudinal
    _, Hl2 = pr.forcas_horizontais(100.0, 15.0, 80.0, n_rodas_lado=2,
                                   frac_lateral=0.10, frac_long=0.10,
                                   n_rodas_motoras=2)
    _, Hl1 = pr.forcas_horizontais(100.0, 15.0, 80.0, n_rodas_lado=2,
                                   frac_lateral=0.10, frac_long=0.10,
                                   n_rodas_motoras=1)
    assert abs(Hl1 - Hl2 / 2.0) < 1e-9


def test_frac_long_default_todas_motoras():
    # sem n_rodas_motoras -> comportamento atual (todas motoras = n_rodas_lado)
    _, Hl = pr.forcas_horizontais(100.0, 15.0, 80.0, n_rodas_lado=2,
                                  frac_lateral=0.10, frac_long=0.10)
    assert abs(Hl - 0.10 * 80.0 * 2) < 1e-9


def test_motoras_maior_que_lado_erro():
    with pytest.raises(Exception):
        pr.forcas_horizontais(100.0, 15.0, 80.0, n_rodas_lado=2,
                              frac_lateral=0.10, frac_long=0.10,
                              n_rodas_motoras=3)


# ============= me-3: analisa usa classe 8400 quando dada ====================
def _cfg_ponte(**over):
    cfg = {"Q": 100.0, "peso_ponte": 60.0, "peso_trole": 15.0, "vao_ponte": 9.5,
           "aprox_min": 1.0, "n_rodas_lado": 2, "phi": 1.10, "frac_lateral": 0.10,
           "frac_long": 0.10, "vao_viga": 5.0, "d_rodas": 3.0, "fy": 250e3,
           "perfil_viga": pr.VS500, "siderurgica": False, "excentricidade": 0.30,
           "E_Ix": pr.ck.E * pr.VS500["Ix"]}
    cfg.update(over)
    return cfg


def test_analisa_phi_da_classe_hc():
    import nbr8400 as n8
    cfg = _cfg_ponte(classe_hc="HC2", Vh_elevacao=0.5)
    esf, viga, reac = pr.analisa(cfg)
    assert abs(esf["phi"] - n8.coef_dinamico("HC2", 0.5)) < 1e-9


def test_analisa_nciclos_da_classe_b():
    import nbr8400 as n8
    cfg = _cfg_ponte(classe_b="B7")
    esf, viga, reac = pr.analisa(cfg)
    assert viga["fadiga"]["N"] == n8.n_ciclos("B7")


def test_analisa_sem_classe_usa_input():
    # sem classe 8400 -> phi de input (retrocompat), sem quebrar
    cfg = _cfg_ponte()
    esf, viga, reac = pr.analisa(cfg)
    assert abs(esf["phi"] - 1.10) < 1e-9


# ============= me-4: gate de validacao da ponte no spec =====================
def _spec_ponte(ponte):
    s = PS.novo()
    s["slug"] = "t4"
    s["terreno"].update(area_lote_m2=4000, to_max=0.6, ca_max=1.0, tp_min=0.2,
                        recuos={"frente": 5, "lateral": 3, "fundos": 3})
    s["geometria"].update(span=15.0, comprimento=20.0, eave=7.0, ridge=7.75,
                          bay=5.0, base_fixed=True)
    s["cobertura"].update(aguas=2, slope=0.10, telha_tipo="trapezoidal",
                          telha_peso=0.10, calha=True)
    s["fechamento"].update(tipo="telha", altura_alvenaria=0, peso=0.05,
                          mesa_interna_travada=True, n_maos_francesas=2)
    s["aberturas"] = {"portao_frente": (4000, 4500), "porta_fundo": (900, 2130),
                      "janelas_laterais": (4300, 5300)}
    s["vento"].update(v0=40, cat="II", classe="B", s3=0.95, z=7.75,
                      abertura_dominante="portao_oitao")
    s["cargas"].update(G=0.27, Q=0.25, self=0.35, tapamento=0.05)
    s["fundacao"]["sigma_solo_adm"] = 200.0
    s["fundacao"]["tipo"] = "sapata"
    s["ponte"] = ponte
    return s


_PONTE_OK = {"Q": 100.0, "peso_ponte": 60.0, "peso_trole": 15.0, "aprox_min": 1.0,
             "n_rodas_lado": 2, "n_rodas_motoras": 1, "phi": 1.10,
             "frac_lateral": 0.10, "frac_long": 0.10, "d_rodas": 3.0,
             "excentricidade": 0.30, "Hvr": 4.5}


def test_ponte_none_valido():
    s = _spec_ponte(None)                # galpao SEM ponte -> valido
    assert PS.validar(s)["ok"], PS.validar(s)["faltando"]


def test_ponte_completa_valida():
    s = _spec_ponte(dict(_PONTE_OK))
    assert PS.validar(s)["ok"], PS.validar(s)["faltando"]


def test_ponte_incompleta_bloqueia():
    p = dict(_PONTE_OK); del p["Q"]      # falta dado do fabricante
    s = _spec_ponte(p)
    assert not PS.validar(s)["ok"], "ponte sem Q deve bloquear"


def test_mapper_passa_n_rodas_motoras():
    s = _spec_ponte(dict(_PONTE_OK))
    p = PS.to_rodar_params(s)
    assert p["ponte"].get("n_rodas_motoras") == 1
