# ============================================================================
# test_shed.py - telhado de UMA AGUA (shed): portico assimetrico (2 colunas de
# alturas diferentes, 1 rafter, sem cumeeira). Vento NBR 6123 Tabela 6.
# So 1 vao. Ver memory normas-bloco-shed.
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
import galpao_portico as gp
import vento_nbr6123 as v


def test_cpe_telhado_1agua_succao():
    c = v.cpe_telhado_1agua(5.71)
    # NBR 6123 Tabela 6: barlavento sempre succao forte; sotavento menos
    assert c["vento90"]["H"] <= -0.9      # barlavento (metade baixa) suga forte
    assert c["vento_90"]["L"] <= -0.9     # barlavento (metade alta) suga forte
    assert all(x < 0 for d in c.values() for x in d.values())   # tudo succao


def test_shed_frame_colunas_de_alturas_diferentes():
    gp.configurar(span=15, eave=6, ridge=6.75, bay=6, aguas=1, base_fixed=True)
    try:
        fr, ix = gp._frame()
        assert ix.get("shed") is True
        z = [fr.nodes[e][1] for e in ix["nEaves"]]
        assert z[0] == pytest.approx(6.0)         # coluna baixa
        assert z[1] == pytest.approx(7.5)         # coluna alta (6 + 0.1*15)
        assert ix["nRidges"] == []                # sem cumeeira
    finally:
        gp.configurar(aguas=2)


def test_shed_gravidade_e_vento_em_equilibrio():
    gp.configurar(span=15, eave=6, ridge=6.75, bay=6, aguas=1, base_fixed=False)
    gp.W_WALL_COL = 0.0
    v.configurar(v0=45, cat="II", s3=0.95, z=7.5, theta=math.degrees(gp.THETA))
    try:
        for load in (gp.case_G, gp._wind("portao_barlavento")[0]):
            fr, ix = gp._frame(); load(fr, ix); fr.solve(); R = fr.reactions()
            av = sum(fy for _, (fx, fy, m) in fr.nodal_loads.items())
            for e, (wx, wy) in fr.member_udl.items():
                xi, yi = fr.nodes[fr.elements[e]["i"]]; xj, yj = fr.nodes[fr.elements[e]["j"]]
                av += wy * math.hypot(xj - xi, yj - yi)
            rv = sum(R[3 * b + 1] for b in ix["nBases"])
            assert abs(av + rv) < 1e-6
        # o vento no telhado do shed e SUCCAO (uplift): wy > 0
        fr, ix = gp._frame(); gp._wind("portao_barlavento")[0](fr, ix)
        assert fr.member_udl[ix["rafts"][0][0][0]][1] > 0
    finally:
        gp.configurar(aguas=2); gp.W_WALL_COL = 0.0


def test_shed_1vao_valida_multivao_bloqueia():
    def _spec(nv):
        r = dict(area_lote_m2=1200, span=15, comprimento=30, eave=6, v0=40,
                 sigma_solo=250, fund_tipo="sapata", aguas=1, n_vaos=nv)
        return WZ.construir_spec(r, slug="s")
    assert PS.validar(_spec(1))["ok"] is True                 # shed 1 vao: OK
    assert PS.validar(_spec(2))["ok"] is False                # shed multi-vao: bloqueia


@pytest.mark.build
def test_shed_pipeline_duas_colunas_distintas(tmp_path):
    import rodar_galpao as R
    r = dict(area_lote_m2=1200, span=15, comprimento=30, eave=6, bay=6, aguas=1,
             slope=0.10, v0=45, cat="II", sigma_solo=250, fund_tipo="sapata")
    s = WZ.construir_spec(r, slug="shed")
    res = R.rodar(PS.to_rodar_params(s), str(tmp_path))
    assert res.get("atende") is True
    # shed assimetrico: as 2 colunas (baixa e alta) podem ter perfis diferentes
    assert len(res["perfil_colunas"]) == 2
