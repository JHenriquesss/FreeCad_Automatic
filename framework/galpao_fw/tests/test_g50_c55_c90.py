"""G50 — resto da familia C55-C90 (NBR 6118): 4 correcoes + continuidade C50.

1. 17.2.2 + 14.6.4.3 em fundacao_sapata._armadura_flexao: lambda, alpha_c e XD_LIM
   por fck. Guarda: sweep C55-C90 sem nenhum ok_dominio=True com x/d > 0,35.
2. 8.2.8 Eci em primitiva unica (fissuracao_nbr6118.eci): C60/C90 menor que a
   extrapolacao 5600*sqrt(fck), flecha maior que com a extrapolacao.
3. 8.2.10.1 em pilar_concreto: eps_cu, eps_c2 e expoente n por fck.
4. gancho_135_exigido no ARTEFATO (SVG/quadro), nao so no dict.
Direcao conservadora + C50 bit-a-bit inalterado.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import fundacao_sapata as fs
import fissuracao_nbr6118 as fis
import pilar_concreto as pc
import viga_baldrame as vb


def eci_errado_MPa(fck_MPa):
    return 5600.0 * math.sqrt(fck_MPa)


def test_01_xd_lim_c55_c90():
    assert fs.xd_lim(50.0) == 0.45
    assert fs.xd_lim(55.0) == 0.35
    assert fs.xd_lim(90.0) == 0.35
    assert abs(fs.lambda_bloco(50.0) - 0.80) < 1e-12
    assert abs(fs.lambda_bloco(60.0) - 0.775) < 1e-12
    assert abs(fs.lambda_bloco(90.0) - 0.70) < 1e-12
    assert abs(fs.alpha_c(50.0) - 0.85) < 1e-12
    assert abs(fs.alpha_c(60.0) - 0.8075) < 1e-12
    assert abs(fs.alpha_c(90.0) - 0.68) < 1e-12


def test_01_sweep_sem_ok_acima_035():
    viol = []
    for fck_MPa in (55, 60, 65, 70, 75, 80, 85, 90):
        for M in (10, 30, 60, 100, 150, 200, 300, 400, 500):
            for b in (0.2, 0.5, 1.0):
                for d in (0.3, 0.45, 0.6, 0.8):
                    As, xd, z, ok = fs._armadura_flexao(
                        M, b, d, fck_MPa * 1e3, 500e3)
                    if ok and xd > 0.35 + 1e-9:
                        viol.append((fck_MPa, M, b, d, xd))
    assert not viol, "ok_dominio com x/d>0,35 em C55-C90: %s" % viol[:5]


def test_01_c50_continuidade():
    As, xd, z, ok = fs._armadura_flexao(100.0, 1.0, 0.5, 50e3, 500e3)
    fcd = 50e3 / 1.4
    mu = 100.0 / (1.0 * 0.5 ** 2 * 0.85 * fcd)
    xd_ref = (1.0 - math.sqrt(1.0 - 2.0 * mu)) / 0.80
    assert abs(xd - xd_ref) < 1e-12
    assert ok == (xd <= 0.45 + 1e-9)


def test_02_eci_primitiva_unica():
    for fck in (60.0, 90.0):
        novo = fis.eci_MPa(fck)
        assert novo < eci_errado_MPa(fck)
    assert fis.eci_MPa(50.0) == eci_errado_MPa(50.0)
    assert fis.eci(50e3) == 5600.0 * math.sqrt(50.0) * 1000.0
    # 6 sitios usam a primitiva: confere 2 representantes + modulo_secante
    import piso_industrial as pi
    import perdas_protensao_nbr6118 as pp
    assert pi.modulo_elasticidade_concreto(60.0) < eci_errado_MPa(60.0) * min(
        1.0, 0.8 + 0.2 * 60.0 / 80.0)
    assert pp._eci(60e3) < eci_errado_MPa(60.0) * 1000.0
    assert pp._eci(50e3) == 5600.0 * math.sqrt(50.0) * 1000.0


def test_02_flecha_maior_que_extrapolacao():
    """MEDE a flecha nos dois mundos. A versao anterior comparava d_pos com
    d_pos*(Ecs_novo/Ecs_err), razao < 1 -> tautologia: passava com qualquer
    implementacao. Aqui a extrapolacao errada e' injetada de fato."""
    args = (0.20, 0.50, 0.45, 4.0, 10.0, 60e3, 4e-4, False)
    d_certo = vb._flecha_alvenaria(*args)["d_pos_parede_mm"]
    orig = fis.eci
    try:
        fis.eci = lambda fck, alpha_e=1.0: eci_errado_MPa(fck / 1000.0) * 1000.0
        d_errado = vb._flecha_alvenaria(*args)["d_pos_parede_mm"]
    finally:
        fis.eci = orig
    assert d_certo > d_errado, (d_certo, d_errado)   # Eci menor -> flecha maior
    assert fis.modulo_secante(60e3) < min(0.8 + 0.2 * 60.0 / 80.0, 1.0) *         eci_errado_MPa(60.0) * 1000.0
    # C50: a injecao nao muda nada (continuidade)
    args50 = (0.20, 0.50, 0.45, 4.0, 10.0, 50e3, 4e-4, False)
    d50 = vb._flecha_alvenaria(*args50)["d_pos_parede_mm"]
    try:
        fis.eci = lambda fck, alpha_e=1.0: eci_errado_MPa(fck / 1000.0) * 1000.0
        d50_inj = vb._flecha_alvenaria(*args50)["d_pos_parede_mm"]
    finally:
        fis.eci = orig
    assert d50 > 0 and d50 == d50_inj


def test_03_pilar_eps_n():
    assert pc.eps_cu(50.0) == 0.0035
    assert pc.eps_c2(50.0) == 0.0020
    assert pc.expoente_n(50.0) == 2.0
    assert pc.alpha_c_pilar(50.0) == 0.85
    # C60: ecu cai (2,88 por mil), ec2 sobe (2,29), n cai (1,59), alpha cai
    assert abs(pc.eps_cu(60.0) - 0.0028835) < 1e-6
    assert 0.0022 < pc.eps_c2(60.0) < 0.0024
    assert abs(pc.expoente_n(60.0) - 1.58954) < 1e-4
    assert abs(pc.alpha_c_pilar(60.0) - 0.8075) < 1e-12
    # C90: ecu 2,6 por mil, n 1,4
    assert abs(pc.eps_cu(90.0) - 0.0026) < 1e-12
    assert abs(pc.expoente_n(90.0) - 1.4) < 1e-12
    # C50 bit-a-bit: sigma identico ao legado
    fcd = 30e3 / 1.4
    assert pc._sigma_c(0.001, fcd) == pc._sigma_c(0.001, fcd, 30e3)


def test_04_gancho_no_artefato():
    import galpao_concreto as gc
    import desenho_concreto as dc
    import executivo_concreto as ex
    base = {"vao": 10.0, "comprimento": 30.0, "pe_direito": 6.0,
            "n_porticos": 5, "v0": 35.0, "cat": "III", "classe": "B",
            "G_roof": 0.30, "Q_roof": 0.25, "sigma_solo_adm": 250.0,
            "travamento_longitudinal": "topo"}
    r60 = gc.rodar(dict(base, fck=60e3))
    assert r60["pilar"]["gancho_135_exigido"] is True
    svg60 = dc.prancha_armacao_svg(r60)
    assert "gancho a 135 graus" in svg60 and "C55-C90" in svg60
    assert "gancho a 135 graus" in ex.relatorio_quadro_pt(r60)
    r50 = gc.rodar(dict(base, fck=50e3))
    svg50 = dc.prancha_armacao_svg(r50)
    assert "gancho a 135 graus" not in svg50 and "C55-C90" not in svg50
    assert "gancho a 135 graus" not in ex.relatorio_quadro_pt(r50)
