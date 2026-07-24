"""Viga de cobertura PRE-TRACIONADA (concreto protendido, NBR 6118) - viga_protendida.py.

A aritmetica de tensoes de borda e aferida contra o exemplo resolvido de Bastos
("Fundamentos do Concreto Protendido", Cap.1, laje 30x30, Mg=Mq=28,13 kN.m) - lido do
PDF, nao de memoria. Checa ato (17.2.4.3.2), servico nivel 2 (Tab.13.4) e ELU flexao.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import viga_protendida as vp


def test_cordoalha_cp190_e_estiramento():
    assert vp.FPTK_CP190 == 1900e3                 # CP-190: 1900 MPa
    assert abs(vp.FPYK_CP190 - 0.9 * 1900e3) < 1   # RB: 0,9 fptk
    # estiramento pre-tracao (9.6.1.2.1): min(0,77 fptk ; 0,90 fpyk)
    assert abs(vp.SIGMA_PI_MAX - min(0.77 * 1900e3, 0.90 * 0.9 * 1900e3)) < 1
    assert vp.AP_CORDOALHA[12.7] == 1.01e-4        # NBR 7483


def test_tensoes_afere_bastos_axial():
    # laje 30x30, Mg+Mq=56,26 kN.m ; protensao axial P=1125 -> base ~ 0
    st, sb = vp.tensoes_borda(1125.0, 0.0, 56.26, 0.30, 0.30)
    assert abs(sb / 1000.0) < 0.05                 # base ~ 0 MPa
    # so a carga: base +12,5 MPa (tracao), topo -12,5 MPa (compressao)
    st0, sb0 = vp.tensoes_borda(0.0, 0.0, 56.26, 0.30, 0.30)
    assert abs(sb0 / 1000.0 - 12.5) < 0.1 and abs(st0 / 1000.0 + 12.5) < 0.1


def test_tensoes_afere_bastos_nucleo_e_ep_max():
    # ep=h/6=0,05 (nucleo central): topo da protensao ~ 0, base = -2P/Ac
    st, sb = vp.tensoes_borda(562.5, 0.05, 0.0, 0.30, 0.30)
    assert abs(st / 1000.0) < 0.05                 # topo ~ 0
    assert abs(sb / 1000.0 + 12.5) < 0.2           # base -12,5 MPa
    # ep=0,10 (max): topo da protensao = +P/Ac = +4,17 MPa (tracao). Bastos: +4,2
    stm, _ = vp.tensoes_borda(375.0, 0.10, 0.0, 0.30, 0.30)
    assert abs(stm / 1000.0 - 4.17) < 0.1


def test_ato_limites_norma():
    r = vp.verifica_viga_protendida({"vao": 14.0, "b": 0.20, "h": 0.60, "fck": 40e3,
                                     "q": 4.0, "n_cordoalhas": 6})
    a = r["ato"]
    assert abs(a["lim_comp"] + 0.70 * 40e3) < 1    # 0,7 fckj (compressao)
    assert abs(a["lim_trac"] - 1.20 * vp._fctm(40e3)) < 1   # 1,2 fctm,j (tracao)


def test_servico_nivel2_els_f_e_els_d():
    r = vp.verifica_viga_protendida({"vao": 15.0, "b": 0.25, "h": 0.70, "fck": 40e3,
                                     "q": 5.0, "n_cordoalhas": 8})
    s = r["servico"]
    assert "els_f_ok" in s and "els_d_ok" in s
    assert abs(s["fct_f"] - 1.5 * vp._fctm(40e3)) < 1   # fct,f = 1,5 fctm


def test_vao_grande_fecha_com_protensao():
    # 16 m: o CA nao vence, mas a protensao fecha (ato+servico+ELU)
    r = vp.dimensiona_viga_protendida({"vao": 16.0, "fck": 40e3, "q": 5.0})
    assert r["OK"]
    assert r["ato"]["ok"] and r["servico"]["ok"] and r["elu"]["ok"]
    assert r["n_cordoalhas"] >= 2


def test_pouca_protensao_reprova_elu_ou_servico():
    # 18 m com so 2 cordoalhas: insuficiente -> reprova (nao mascara)
    r = vp.verifica_viga_protendida({"vao": 18.0, "b": 0.20, "h": 0.60, "fck": 40e3,
                                     "q": 6.0, "n_cordoalhas": 2})
    assert not r["OK"]


def test_selftest_roda():
    vp._selftest()
