"""Flexao composta OBLIQUA (biaxial) do pilar - NBR 6118 17.2.5 / 15.8.3.3.5.

Interacao (Mx/Mrd,xx)^alpha + (My/Mrd,yy)^alpha <= 1, alpha=1,2 (secao retangular,
17.2.5 literal). Mrd,xx e Mrd,yy sao os momentos resistentes UNIAXIAIS - o solver ja
aferido contra Bastos - com o As total em 4 cantos: validacao por composicao.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pilar_concreto as pc


def _canto(Nk=900.0, Max=180.0, May=120.0, **kw):
    caso = {"b": 0.30, "h": 0.40, "Nk": Nk, "le_x": 3.0, "le_y": 3.0,
            "fck": 30e3, "fyk": 500e3, "dl": 0.04,
            "M1d_x": {"tipo": "biapoiado", "Ma": Max, "Mb": Max},
            "M1d_y": {"tipo": "biapoiado", "Ma": May, "Mb": May}}
    caso.update(kw)
    return caso


def test_alpha_retangular_1_2():
    assert pc.ALPHA_BIAXIAL_RECT == 1.2            # 17.2.5: secao retangular


def test_momento_nas_duas_direcoes_ativa_biaxial():
    r = pc.dimensiona_pilar(_canto())
    assert r["modo"] == "biaxial"
    assert "biaxial" in r and r["biaxial"]["alpha"] == 1.2


def test_interacao_converge_para_um_e_e_binding():
    r = pc.dimensiona_pilar(_canto())
    b = r["biaxial"]
    assert r["As_cm2"] > r["As_min_cm2"]           # a interacao (nao o minimo) governa
    assert abs(b["util"] - 1.0) < 0.01             # bisseccao converge a util=1
    # halving As viola a interacao (monotonia): confirma que e binding
    As = r["As_cm2"] / 1e4
    u_half = pc.verifica_biaxial(r["Nd"], b["Md_x"], b["Md_y"], 0.30, 0.40, 0.04,
                                 30e3, 500e3, As * 0.5)["util"]
    assert u_half > 1.0


def test_biaxial_pede_mais_aco_que_uniaxial():
    # o mesmo pilar SEM o momento em y (uniaxial) precisa de menos armadura
    r_bi = pc.dimensiona_pilar(_canto())
    r_uni = pc.dimensiona_pilar(_canto(M1d_y=None))
    assert r_uni["modo"] == "uniaxial"
    assert r_bi["As_cm2"] > r_uni["As_cm2"] + 1.0  # a demanda obliqua adiciona aco


def test_degenerado_reduz_ao_uniaxial():
    # com My=0 LITERAL a interacao vira (Mx/Mrd,xx)^a <= 1, i.e. Mx <= Mrd,xx: o As
    # da armadura_biaxial tem que coincidir com o da flexao composta normal na dir x.
    # (Isola a matematica da interacao do envelope de momento minimo, que e por
    # direcao - por isso o dimensionamento combinado e conservador, nao identico.)
    Nd, Mx = 840.0, 180.0
    As_bi, ok = pc.armadura_biaxial(Nd, Mx, 0.0, 0.30, 0.40, 0.04, 30e3, 500e3, 0.08 * 0.12)
    As_uni, ok2 = pc.armadura_flexao_composta(Nd, Mx, 0.30, 0.40, 0.04, 30e3, 500e3,
                                              As_max=0.08 * 0.12)
    assert abs(As_bi - As_uni) / max(As_uni, 1e-9) < 0.02


def test_so_um_momento_real_fica_uniaxial():
    # momento real so em x (pilar de extremidade) -> NAO ativa biaxial
    caso = {"b": 0.30, "h": 0.40, "Nk": 700.0, "le_x": 3.0, "le_y": 3.0,
            "fck": 30e3, "fyk": 500e3, "dl": 0.04,
            "M1d_x": {"tipo": "biapoiado", "Ma": 80.0}}
    r = pc.dimensiona_pilar(caso)
    assert r["modo"] == "uniaxial" and "biaxial" not in r


def test_secao_pequena_biaxial_reprova():
    # 20x20 sob N e momentos altos nas 2 direcoes: nem As_max satisfaz -> REPROVA
    r = pc.dimensiona_pilar(_canto(Nk=1200.0, Max=120.0, May=120.0, b=0.20, h=0.20))
    assert not r["biaxial"]["ok"] or not r["OK"]
