# ============================================================================
# test_carga_parede.py - o peso da parede de fechamento tem de CHEGAR ao calculo
# (coluna + fundacao + baldrame). Antes era coletado no spec e IGNORADO
# (contra-seguranca). Ver memoria carga-fechamento-parede-nao-aplicada.
# ============================================================================
import os
import sys
import math
import copy

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS
import galpao_portico as gp


# ---- funcao pura: distribuicao do peso de parede -----------------------------
def test_cargas_parede_telha_vs_alvenaria():
    telha = PS.cargas_parede({"tipo": "telha", "peso": 0.10}, eave=8.0, bay=5.7)
    alv = PS.cargas_parede({"tipo": "alvenaria", "peso": 1.5}, eave=8.0, bay=5.7)
    # telha leve -> COLUNA (w_col>0), nada de alvenaria
    assert telha["w_col_kN_m"] > 0 and telha["w_masonry_kN_m"] == 0
    assert telha["N_masonry_ext_kN"] == 0
    # alvenaria autoportante -> FUNDACAO/baldrame, NAO na coluna de aco (w_col==0)
    assert alv["w_col_kN_m"] == 0
    assert alv["w_masonry_kN_m"] > 0 and alv["N_masonry_ext_kN"] > 0
    # coerencia: N_masonry_ext = w_masonry * bay
    assert alv["N_masonry_ext_kN"] == pytest.approx(alv["w_masonry_kN_m"] * 5.7)


def test_cargas_parede_alvenaria_telha_split():
    r = PS.cargas_parede({"tipo": "alvenaria_telha", "peso": 1.5,
                          "altura_alvenaria": 3.0}, eave=8.0, bay=5.7, telha_peso=0.10)
    # alvenaria ate 3 m -> baldrame/fundacao; telha de 3 a 8 m -> coluna
    assert r["w_masonry_kN_m"] == pytest.approx(1.5 * 3.0)
    assert r["N_masonry_ext_kN"] == pytest.approx(1.5 * 3.0 * 5.7)
    assert r["w_col_kN_m"] == pytest.approx(0.10 * 5.0 * 5.7 / 8.0, abs=1e-3)  # so a telha


# ---- o UDL de parede NAO quebra o equilibrio (UDL, nao nodal) -----------------
def test_parede_udl_preserva_equilibrio():
    gp.configurar(span=10, eave=6, ridge=7, bay=6)
    try:
        for w in (0.0, 7.0):
            gp.W_WALL_COL = w
            fr, ix = gp._frame(); gp.case_G(fr, ix); fr.solve(); R = fr.reactions()
            aplic = sum(fy for _, (fx, fy, m) in fr.nodal_loads.items())
            for eidx, (wx, wy) in fr.member_udl.items():
                xi, yi = fr.nodes[fr.elements[eidx]["i"]]
                xj, yj = fr.nodes[fr.elements[eidx]["j"]]
                aplic += wy * math.hypot(xj - xi, yj - yi)
            reac = sum(R[3 * b + 1] for b in ix["nBases"])
            assert abs(abs(aplic) - abs(reac)) / abs(aplic) < 1e-9
    finally:
        gp.W_WALL_COL = 0.0


# ---- integracao: a parede chega na coluna, na base e no baldrame --------------
def _spec_amostra():
    p = os.path.join(GALPAO, "spec_amostra_engenheiro.json")
    if not os.path.exists(p):
        pytest.skip("spec_amostra_engenheiro.json ausente")
    import json
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.build
def test_parede_chega_na_base_e_no_baldrame(tmp_path):
    import rodar_galpao as R
    spec = _spec_amostra()

    def _rodar(tipo, peso):
        s = copy.deepcopy(spec)
        s["fechamento"]["tipo"] = tipo
        s["fechamento"]["peso"] = peso
        return R.rodar(PS.to_rodar_params(s), str(tmp_path / (tipo + str(peso))))

    res_t = _rodar("telha", 0.10)
    res_a = _rodar("alvenaria", 1.5)
    # o baldrame passa a carregar o peso da alvenaria (q_parede > 0)
    w_bald_a = res_a["baldrame"]["N_tie_kN"]
    assert res_a["baldrame"] is not None
    # a reacao de compressao de base cresce (|N| maior) com a alvenaria
    Na = max(abs(n) for _, n, _, _ in R._casos_base_envelope())
    assert Na > 0


def test_params_ref_sem_parede_nao_regride():
    # PARAMS_REF nao tem bloco 'parede' -> W_WALL_COL fica 0 -> referencia intacta
    import rodar_galpao as R
    assert "parede" not in R.PARAMS_REF
    par = R.PARAMS_REF.get("parede") or {}
    assert par.get("w_col_kN_m", 0.0) == 0.0
