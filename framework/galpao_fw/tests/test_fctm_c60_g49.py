"""G49 — fctm C55-C90 (NBR 6118 8.2.5): um teste por modulo tocado + transversal.

Regra: ate C50 fctm = 0,3*fck^(2/3); acima: fctm = 2,12*ln(1+0,11*fck).
A formula errada (extrapolar C50) da fctm MAIOR -> contra a seguranca
(Vc maior, rho_sw menor, ancoragem menor). Cada teste compara C50 e C60
e exige C60 < extrapolacao errada (sinal do fix + direcao conservadora).

Referencias (nao reescritas, so conferidas): fissuracao_nbr6118.fctm e
premoldado_nbr9062._fctm ja tratam a faixa alta.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import base_chumbador as bc
import estaca_profunda as ep
import fundacao_sapata as fs
import laje_concreto as lj
import pilar_concreto as pc
import piso_industrial as pi
import viga_baldrame as vb
import viga_protendida as vp
import fissuracao_nbr6118 as fis
import premoldado_nbr9062 as pm


def fctm_errada_MPa(fck_MPa):
    return 0.3 * fck_MPa ** (2.0 / 3.0)


def fctm_certa_MPa(fck_MPa):
    if fck_MPa <= 50.0:
        return 0.3 * fck_MPa ** (2.0 / 3.0)
    return 2.12 * math.log(1.0 + 0.11 * fck_MPa)


def test_referencias_ja_certas():
    # fissuracao e premoldado servem de referencia: conferir, nao reescrever.
    assert abs(fis.fctm(60e3) / 1000.0 - fctm_certa_MPa(60.0)) < 1e-9
    assert abs(pm._fctm(60e3) / 1000.0 - fctm_certa_MPa(60.0)) < 1e-9
    assert fis.fctm(60e3) < fctm_errada_MPa(60.0) * 1000.0


def test_base_chumbador_c60_conservador():
    a50 = bc.ancoragem_chumbador(10.0, 0.020, 50e3, 250e3)
    a60 = bc.ancoragem_chumbador(10.0, 0.020, 60e3, 250e3)
    fctd_err60 = 0.7 * fctm_errada_MPa(60.0) / 1.4 * 1000.0
    # C50 inalterado (continuidade)
    assert abs(a50["fctd"] - 0.7 * fctm_errada_MPa(50.0) / 1.4 * 1000.0) < 1e-6
    # C60 abaixo da extrapolacao errada -> fbd menor -> lb maior (conservador)
    assert a60["fctd"] < fctd_err60
    assert a60["fbd"] < 1.0 * 1.0 * 1.0 * fctd_err60
    assert a60["lb"] > (0.020 / 4.0) * ((250e3 / 1.15) / fctd_err60)


def test_estaca_profunda_c60_conservador():
    a50 = ep.ancoragem_tirante(0.020, 50e3, 500e3)
    a60 = ep.ancoragem_tirante(0.020, 60e3, 500e3)
    assert abs(a50["fctm_MPa"] - fctm_errada_MPa(50.0)) < 0.01  # round(...,2)
    assert a60["fctm_MPa"] < fctm_errada_MPa(60.0)
    assert abs(a60["fctm_MPa"] - fctm_certa_MPa(60.0)) < 0.01


def test_fundacao_sapata_c60_conservador():
    r50 = fs.comprimento_ancoragem(20.0, 50.0)
    r60 = fs.comprimento_ancoragem(20.0, 60.0)
    fbd_err60 = 2.25 * 0.7 * fctm_errada_MPa(60.0) / 1.4
    assert abs(r50["fbd_MPa"] - round(2.25 * 0.7 * fctm_errada_MPa(50.0) / 1.4, 2)) < 0.02
    assert r60["fbd_MPa"] < fbd_err60
    # fbd menor -> lb maior
    assert r60["lb_mm"] > (20.0 / 4.0) * ((500 / 1.15) / fbd_err60) - 1.0


def test_laje_concreto_c60_conservador():
    r50 = lj.cortante_laje(50.0, 1.0, 0.10, 50e3, 5e-4)
    r60 = lj.cortante_laje(50.0, 1.0, 0.10, 60e3, 5e-4)
    fctd_err60 = 0.7 * fctm_errada_MPa(60.0) / 1.4 * 1000.0
    tau_err60 = 0.25 * fctd_err60
    assert r60["tau_rd"] < tau_err60
    assert r60["V_rd1"] < r50["V_rd1"] * 3.0  # sanidade: nao explode
    # prova conservadora: V_rd1 com formula certa < com errada (mesmo k, rho)
    k = r60["k"]
    rho1 = r60["rho1"]
    v_err = (tau_err60 * k * (1.2 + 40.0 * rho1)) * 1.0 * 0.10
    assert r60["V_rd1"] < v_err


def test_pilar_concreto_c60_conservador():
    c50 = pc.verifica_cortante_pilar(100.0, 0.20, 0.45, 50e3, 500e3)
    c60 = pc.verifica_cortante_pilar(100.0, 0.20, 0.45, 60e3, 500e3)
    vc_err60 = 0.6 * (0.7 * fctm_errada_MPa(60.0) / 1.4) * 1000.0 * 0.20 * 0.45
    rho_err60 = 0.2 * fctm_errada_MPa(60.0) / 500.0
    assert c60["Vc"] < vc_err60
    assert c60["rho_sw_min"] < rho_err60
    assert c50["Vc"] > 0 and c60["Vc"] > 0


def test_piso_industrial_c60_conservador():
    f50 = pi.resistencia_flexao_projeto(50.0)
    f60 = pi.resistencia_flexao_projeto(60.0)
    assert abs(f50 - fctm_errada_MPa(50.0) / 1.4) < 1e-9
    assert f60 < fctm_errada_MPa(60.0) / 1.4
    assert abs(f60 - fctm_certa_MPa(60.0) / 1.4) < 1e-9


def test_viga_baldrame_cortante_c60_conservador():
    c50 = vb._verifica_cortante(100.0, 0.20, 0.45, 50e3, 500e3)
    c60 = vb._verifica_cortante(100.0, 0.20, 0.45, 60e3, 500e3)
    vc_err60 = 0.6 * (0.7 * fctm_errada_MPa(60.0) / 1.4) * 1000.0 * 0.20 * 0.45
    assert c60["Vc"] < vc_err60
    assert c60["rho_sw_min"] < 0.2 * fctm_errada_MPa(60.0) / 500.0


def test_viga_baldrame_flecha_mr_c60_conservador():
    r50 = vb._flecha_alvenaria(0.20, 0.50, 0.45, 4.0, 10.0, 50e3, 4e-4, False)
    r60 = vb._flecha_alvenaria(0.20, 0.50, 0.45, 4.0, 10.0, 60e3, 4e-4, False)
    mr_err60 = 1.5 * (fctm_errada_MPa(60.0) * 1000.0) * (0.20 * 0.50 ** 3 / 12.0) / 0.25
    assert r60["Mr"] < mr_err60
    assert r50["Mr"] > 0


def test_viga_protendida_c60_conservador():
    f50 = vp._fctm(50e3)
    f60 = vp._fctm(60e3)
    assert abs(f50 - fctm_errada_MPa(50.0) * 1000.0) < 1e-6
    assert f60 < fctm_errada_MPa(60.0) * 1000.0
    assert abs(f60 - fctm_certa_MPa(60.0) * 1000.0) < 1e-6


def test_transversal_nenhum_modulo_usa_c50_acima_de_c50():
    """Varre os modulos: falha se algum ainda aplicar a expressao de C50 em C60."""
    errs = []
    # pilar / baldrame-cortante via Vc
    for nome, fn in [
        ("pilar_concreto", lambda: pc.verifica_cortante_pilar(10.0, 0.20, 0.45, 60e3, 500e3)["Vc"]),
        ("viga_baldrame.cortante", lambda: vb._verifica_cortante(10.0, 0.20, 0.45, 60e3, 500e3)["Vc"]),
        ("viga_baldrame.flecha.Mr", lambda: vb._flecha_alvenaria(0.20, 0.50, 0.45, 4.0, 10.0, 60e3, 4e-4, False)["Mr"]),
        ("viga_protendida._fctm", lambda: vp._fctm(60e3)),
        ("piso_industrial", lambda: pi.resistencia_flexao_projeto(60.0) * 1000.0),
        ("laje_concreto.V_rd1", lambda: lj.cortante_laje(10.0, 1.0, 0.10, 60e3, 5e-4)["V_rd1"]),
        ("base_chumbador.fctd", lambda: bc.ancoragem_chumbador(10.0, 0.020, 60e3, 250e3)["fctd"]),
        ("estaca_profunda.fctm", lambda: ep.ancoragem_tirante(0.020, 60e3, 500e3)["fctm_MPa"] * 1000.0),
        ("fundacao_sapata.fbd", lambda: fs.comprimento_ancoragem(20.0, 60.0)["fbd_MPa"] * 1000.0),
    ]:
        val = fn()
        # teto da expressao errada convertido para a grandeza comparavel:
        # todas as grandezas acima sao PROPORCIONAIS a fctm (ou fctm/1.4 etc.),
        # logo devem ficar abaixo do valor com fctm errada. Checagem generica:
        # fctm certa < errada => qualquer multiplo positivo preserva a ordem.
        # Aqui verificamos via fctm equivalente: val/val50 * fctm50 < errada.
        if nome == "pilar_concreto":
            ref = pc.verifica_cortante_pilar(10.0, 0.20, 0.45, 50e3, 500e3)["Vc"]
            fct50 = fctm_errada_MPa(50.0)
            fct_eq = val / ref * fct50
        elif nome == "viga_baldrame.cortante":
            ref = vb._verifica_cortante(10.0, 0.20, 0.45, 50e3, 500e3)["Vc"]
            fct50 = fctm_errada_MPa(50.0)
            fct_eq = val / ref * fct50
        elif nome == "viga_baldrame.flecha.Mr":
            ref = vb._flecha_alvenaria(0.20, 0.50, 0.45, 4.0, 10.0, 50e3, 4e-4, False)["Mr"]
            fct50 = fctm_errada_MPa(50.0)
            fct_eq = val / ref * fct50
        elif nome == "viga_protendida._fctm":
            fct_eq = val / 1000.0
        elif nome == "piso_industrial":
            fct_eq = val / 1000.0 * 1.4
        elif nome == "laje_concreto.V_rd1":
            ref = lj.cortante_laje(10.0, 1.0, 0.10, 50e3, 5e-4)["V_rd1"]
            # V_rd1 nao e' estritamente proporcional (k, rho iguais aqui) -> e' proporcional a fctd
            fct50 = fctm_errada_MPa(50.0)
            fct_eq = val / ref * fct50
        elif nome == "base_chumbador.fctd":
            fct_eq = val / 1000.0 / 0.7 * 1.4
        elif nome == "estaca_profunda.fctm":
            fct_eq = val / 1000.0
        elif nome == "fundacao_sapata.fbd":
            fct_eq = val / 1000.0 / 2.25 / 0.7 * 1.4
        else:
            fct_eq = float("inf")
        if not (fct_eq < fctm_errada_MPa(60.0) - 1e-9):
            errs.append("%s: fctm_eq %.4f >= errada %.4f" % (nome, fct_eq, fctm_errada_MPa(60.0)))
    assert not errs, "modulos ainda com formula C50 em C60: %s" % "; ".join(errs)


def test_nota_dutilidade_c55_c90_aplicada():
    """NOTA 18.4.3 (recomenda-se): s_max -50% + gancho 135 em C55-C90. G49 APLICA."""
    base = {"b": 0.30, "h": 0.30, "Nk": 800.0, "le_x": 2.80, "le_y": 2.80,
            "fck": 50e3, "fyk": 500e3, "dl": 0.04, "Vd": 50.0}
    r50 = pc.dimensiona_pilar(dict(base))
    r60 = pc.dimensiona_pilar(dict(base, fck=60e3))
    assert r50["nota_ductilidade_C55_C90"] is False
    assert r60["nota_ductilidade_C55_C90"] is True
    assert r60["gancho_135_exigido"] is True
    assert r60["s_estribo_max"] <= 0.5 * r50["s_estribo_max"] + 1e-9
    assert r60["s_limite_governante"] == "18.4.3 NOTA C55-C90 50% (G49)"
