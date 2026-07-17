# ============================================================================
# test_crashes_wiki07.py - crashes de pipeline (wiki 07 itens C, E). O pipeline
# tem de DEGRADAR com veredito, nunca estourar excecao.
# ============================================================================
import os
import sys
import copy

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS
import wizard as WZ
import rodar_galpao as R


def test_reprovacao_nao_crasha(tmp_path):
    # item E: galpao que REPROVA (vao/vento severos) deve retornar atende=False,
    # nao IndexError em res['perfil_colunas'] (era N_VAOS, o loop pede N_VAOS+1).
    r = dict(area_lote_m2=5000, span=40, comprimento=30, eave=9, bay=6,
             base_fixed=False, fech_tipo="telha", fech_peso=0.10, v0=50, cat="I",
             G=0.15, Q=0.25, sigma_solo=200, fund_tipo="sapata")
    s = WZ.construir_spec(r, slug="reprova")
    res = R.rodar(PS.to_rodar_params(s), str(tmp_path))
    assert res.get("atende") is False
    assert len(res["perfil_colunas"]) == R.gp.N_VAOS + 1


def test_ponte_sem_Hvr_nao_crasha(tmp_path):
    # item C: Hvr e opcional no bloco ponte; o orquestrador nao pode quebrar com
    # KeyError ao montar a config do portico.
    p = copy.deepcopy(R.PARAMS_REF)
    p["ponte"] = {"Q": 100.0, "peso_ponte": 60.0, "peso_trole": 15.0,
                  "aprox_min": 1.0, "n_rodas_lado": 2, "n_rodas_motoras": 2,
                  "phi": 1.10, "frac_lateral": 0.10, "frac_long": 0.10,
                  "d_rodas": 3.0, "fy": 250e3, "perfil_viga": R.pr.VS500,
                  "siderurgica": False, "excentricidade": 0.30,
                  "E_Ix": R.pr.ck.E * R.pr.VS500["Ix"]}   # SEM 'Hvr'
    res = R.rodar(p, str(tmp_path))
    assert "atende" in res     # rodou ate o fim


def test_solo_invalido_bloqueia_no_validar():
    # item D: tipo de solo fora da lista Aoki-Velloso deve BLOQUEAR no validar,
    # nao passar e quebrar com ValueError no meio da orquestracao.
    def _est(tipo):
        r = dict(area_lote_m2=1200, span=12, comprimento=30, eave=6.5, v0=38,
                 sigma_solo=150, fund_tipo="estaca", est_tipo="pre_moldada",
                 est_D=0.30, est_L=12.0, est_FS=3.0, spt_tipo=tipo, spt_N=12, spt_dz=8.0)
        return WZ.construir_spec(r, slug="t")
    assert PS.validar(_est("rocha"))["ok"] is False
    assert PS.validar(_est("areia_siltosa"))["ok"] is True


def test_dossie_rotulo_vaos_desiguais():
    # item K: vaos DESIGUAIS nao podem ser rotulados como "N vaos de X m".
    import dossie
    hetero = dossie._linhas_capa({"geometria": {"comprimento": 30, "spans": [10, 15]}})
    igual = dossie._linhas_capa({"geometria": {"comprimento": 30, "spans": [10, 10]}})
    assert any("10+15" in ln for ln in hetero)
    assert any("2 vaos de 10" in ln for ln in igual)
