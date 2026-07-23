"""Modelo neutro do portico primario (puro, sem FreeCAD) - item 2 do roteiro."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import modelo_neutro as MN

_SEC = {"col": {"nome": "HEA200", "d": 0.190, "bf": 0.200, "tw": 0.0065, "tf": 0.010},
        "raf": {"nome": "HEA180", "d": 0.171, "bf": 0.180, "tw": 0.006, "tf": 0.0095}}


def test_um_vao_conta_colunas_e_rafters():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    M = MN.frame_primario(geo, _SEC)
    r = MN.resumo(M)
    assert r["Column"] == 18 and r["Beam"] == 18       # 9 porticos x (2 col + 2 raf)


def test_coluna_vertical_da_base_ao_beiral():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    c = [m for m in MN.frame_primario(geo, _SEC) if m["tipo"] == "Column"][0]
    assert c["p1"][2] == 0.0 and abs(c["p2"][2] - 6000.0) < 1e-6
    assert c["p1"][0] == c["p2"][0] and c["p1"][1] == c["p2"][1]   # so Z varia


def test_rafter_sobe_do_beiral_a_cumeeira_no_meio_do_vao():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    v = [m for m in MN.frame_primario(geo, _SEC) if m["tipo"] == "Beam"][0]
    assert abs(v["p1"][2] - 6000.0) < 1e-6 and abs(v["p2"][2] - 7000.0) < 1e-6
    assert abs(v["p2"][1] - 10000.0) < 1e-6            # cumeeira no meio do vao 20 m


def test_multivao_colunas_internas_e_marcas():
    geo = {"spans": [10.0, 12.0], "comprimento": 30.0, "eave": 6.0,
           "ridge": 7.5, "bay": 6.0}
    M = MN.frame_primario(geo, _SEC)
    r = MN.resumo(M)
    assert r["Column"] == 18 and r["Beam"] == 24       # 6 porticos x (3 col + 4 raf)
    assert {m["marca"] for m in M if m["tipo"] == "Beam"} == {"V1", "V2"}


def test_n_porticos_escala_com_comprimento():
    base = {"span": 20.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    c30 = MN.resumo(MN.frame_primario({**base, "comprimento": 30.0}, _SEC))["Column"]
    c50 = MN.resumo(MN.frame_primario({**base, "comprimento": 50.0}, _SEC))["Column"]
    assert c30 == 2 * 7 and c50 == 2 * 11              # 30/5->7 ; 50/5->11 porticos


def test_secao_preservada_no_membro():
    geo = {"span": 20.0, "comprimento": 10.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    M = MN.frame_primario(geo, _SEC)
    c = [m for m in M if m["tipo"] == "Column"][0]
    assert c["secao"]["nome"] == "HEA200" and c["perfil"] == "HEA200"


_TERCA = {"nome": "Ue300", "forma": "C", "d": 0.300, "bf": 0.085, "lip": 0.025, "t": 0.00335}


def test_tercas_contagem_por_agua_e_vao():
    # n_terca-1 tercas intermediarias por AGUA, 2 aguas por vao (1 vao aqui)
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0,
           "raf_d": 0.171}
    t = MN.tercas(geo, n_terca=5, terca_sec=_TERCA)
    assert len(t) == 2 * (5 - 1) + 2                   # 8 interm. + 2 beiral = 10
    assert all(m["tipo"] == "Member" for m in t)


def test_tercas_sao_longitudinais():
    # terca corre em X (0->comprimento) a Y e Z fixos
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0,
           "raf_d": 0.171}
    t = MN.tercas(geo, 5, _TERCA)[0]
    assert t["p1"][0] == 0.0 and abs(t["p2"][0] - 40000.0) < 1e-6
    assert abs(t["p1"][1] - t["p2"][1]) < 1e-9 and abs(t["p1"][2] - t["p2"][2]) < 1e-9


def test_tercas_multivao_escalam():
    geo = {"spans": [10.0, 10.0], "comprimento": 30.0, "eave": 6.0, "ridge": 7.5,
           "bay": 6.0, "raf_d": 0.171}
    t = MN.tercas(geo, 4, _TERCA)
    assert len(t) == 2 * (4 - 1) * 2 + 2                # interm. 12 + 2 beiral = 14


def test_frame_completo_soma_primario_e_tercas():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    sec = _SEC
    M = MN.frame_completo(geo, sec, n_terca=5, terca_sec=_TERCA)
    r = MN.resumo(M)
    assert r["Column"] == 18 and r["Beam"] == 18 and r["Member"] == 10


def test_frame_completo_sem_terca_igual_primario():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    assert MN.resumo(MN.frame_completo(geo, _SEC)) == MN.resumo(MN.frame_primario(geo, _SEC))


_GIRT = {"nome": "UPE140", "forma": "U", "d": 0.140, "bf": 0.065, "tw": 0.005, "tf": 0.009}


def test_girts_dois_niveis_duas_paredes():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 8.0, "ridge": 9.0, "bay": 5.0}
    g = MN.girts(geo, _GIRT, col_d=0.5)
    assert len(g) == 2 * 2                              # 2 niveis (2/4 m) x 2 paredes
    assert all(m["tipo"] == "Member" for m in g)
    # longitudinais (X 0->comp), Y = -GOFF e SPAN+GOFF
    ys = sorted({round(m["p1"][1], 1) for m in g})
    goff = (0.5 / 2 + 0.140 / 2) * 1000.0
    assert abs(ys[0] + goff) < 1e-3 and abs(ys[-1] - (20000.0 + goff)) < 1e-3


def test_girts_descarta_nivel_acima_do_beiral():
    # beiral 3 m: o nivel de 4 m nao existe -> so o de 2 m (x2 paredes)
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 3.0, "ridge": 4.0, "bay": 5.0}
    assert len(MN.girts(geo, _GIRT, col_d=0.5)) == 2


def test_frame_completo_com_girts():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 8.0, "ridge": 9.0, "bay": 5.0}
    M = MN.frame_completo(geo, _SEC, n_terca=5, terca_sec=_TERCA, girt_sec=_GIRT,
                          col_d=0.5)
    r = MN.resumo(M)
    assert r["Member"] == 10 + 4                        # 10 tercas + 4 girts


def test_tirantes_parede_bays_x_n_x_2paredes():
    # 40/5=8 -> 9 porticos -> 8 vaos ; n=2 ; 2 paredes -> 8*2*2 = 32
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    t = MN.tirantes_parede(geo, n_tirante=2, d_mm=16.0, col_d=0.5, girt_d=0.14)
    assert len(t) == 8 * 2 * 2
    # verticais (mesmo X e Y, Z 0->eave), redondas
    assert t[0]["p1"][0] == t[0]["p2"][0] and t[0]["p1"][1] == t[0]["p2"][1]
    assert t[0]["p1"][2] == 0.0 and abs(t[0]["p2"][2] - 6000.0) < 1e-6
    assert t[0]["secao"]["forma"] == "round"


def test_contrav_cobertura_vaos_de_extremidade():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    c = MN.contrav_cobertura(geo, 20.0)
    assert len(c) == 4                                 # 2 vaos extremos x 2 diagonais
    # diagonal cruza o beiral (Y 0 <-> span) no plano do eave
    assert abs(c[0]["p1"][2] - 6000.0) < 1e-6 and abs(c[0]["p2"][2] - 6000.0) < 1e-6
    assert c[0]["p1"][1] == 0.0 and abs(c[0]["p2"][1] - 20000.0) < 1e-6


def test_contrav_um_vao_so_duas_diagonais():
    # comprimento = bay -> 2 porticos -> 1 vao -> so 2 diagonais (nao duplica)
    geo = {"span": 20.0, "comprimento": 5.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    assert len(MN.contrav_cobertura(geo, 20.0)) == 2


def test_frame_completo_com_tirantes_e_contrav():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 8.0, "ridge": 9.0, "bay": 5.0}
    M = MN.frame_completo(geo, _SEC, n_terca=5, terca_sec=_TERCA, girt_sec=_GIRT,
                          col_d=0.5, n_tirante_parede=2, contrav=True)
    r = MN.resumo(M)
    # 10 tercas + 4 girts + 8*2*2 tirantes + 4 contrav
    assert r["Member"] == 10 + 4 + 8 * 2 * 2 + 4


_FUND = {"B": 2.5, "L": 3.0, "h": 2.35, "tipo": "bloco"}


def test_fundacoes_uma_por_base():
    # 40/5=8 -> 9 porticos ; 2 linhas de coluna (1 vao) -> 18 fundacoes
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    fs = MN.fundacoes(geo, _FUND)
    assert len(fs) == 9 * 2
    f0 = fs[0]
    assert f0["tipo"] == "Footing" and f0["perfil"] == "Bloco"
    assert f0["dims"] == (2500.0, 3000.0, 2350.0)      # mm
    # topo no solo (Z0=0), centro em -h/2
    assert abs(f0["centro"][2] + 2350.0 / 2.0) < 1e-6


def test_fundacoes_multivao():
    geo = {"spans": [10.0, 12.0], "comprimento": 30.0, "eave": 6.0, "ridge": 7.5, "bay": 6.0}
    # 30/6=5 -> 6 porticos ; 3 linhas -> 18
    assert len(MN.fundacoes(geo, _FUND)) == 6 * 3


def test_frame_completo_com_fundacoes():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 8.0, "ridge": 9.0, "bay": 5.0}
    M = MN.frame_completo(geo, _SEC, fund_sec=_FUND)
    r = MN.resumo(M)
    assert r["Footing"] == 9 * 2 and r["Column"] == 18


def test_selftest_modulo():
    MN._selftest()
