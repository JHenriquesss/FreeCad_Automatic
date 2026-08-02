"""Robustez e cobertura do projeto eletrico: LUMINOTECNICA (metodo dos lumens),
CONDUTORES EM PARALELO (galpao grande) e varredura de galpoes variados (pequeno BT,
medio MT, gigante, so iluminacao, monofasico, alimentador longo). Tudo PURO -> CI."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import condutores_nbr5410 as cd
import luminotecnica_nbr8995 as lt
import galpao_eletrico as ge


# ------------------------------ luminotecnica --------------------------------
def test_luminotecnica_selftest():
    lt._selftest()


def test_metodo_dos_lumens_producao():
    p = lt.projeto_luminotecnico({"C": 40.0, "L": 20.0, "pe_direito": 6.0,
                                  "atividade": "producao", "ambiente": "medio",
                                  "Fu": 0.6, "luminaria": "high_bay_led_100W"})
    assert p["E_lux"] == 500 and p["A_m2"] == 800.0
    assert p["N_luminarias"] == 74          # 500*800/(13000*0,6*0,7)=73,3 -> 74
    assert abs(p["P_total_kW"] - 7.4) < 1e-9


def test_iluminancia_e_indice():
    assert lt.iluminancia_recomendada("armazem_volumes") == 200
    assert abs(lt.indice_recinto(40.0, 20.0, 5.0) - 2.6667) < 0.001


def test_atividade_desconhecida_nao_inventa():
    import pytest
    with pytest.raises(ValueError):
        lt.iluminancia_recomendada("inexistente")


def test_luminotecnica_alimenta_cargas():
    # sem informar iluminacao_kW: a carga vem do metodo dos lumens
    spec = {"tensao_V": 380.0, "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2}]},
            "luminotecnica": {"atividade": "producao", "ambiente": "medio", "Fu": 0.6,
                              "luminaria": "high_bay_led_100W"},
            "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"},
            "geometria": {"L": 40.0, "W": 20.0, "H": 6.0}}
    r = ge.rodar(spec)
    assert r["gates"]["luminotecnica"]["N_luminarias"] == 74
    assert abs(r["gates"]["luminotecnica"]["P_kW"] - 7.4) < 1e-9
    assert abs(r["cargas"]["por_grupo"]["iluminacao"]["D_kW"] - 7.4) < 1e-9


def test_sem_luminotecnica_gate_informativo():
    spec = {"tensao_V": 380.0, "cargas": {"iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
            "alimentador": {"L_km": 0.05}}
    r = ge.rodar(spec)
    assert r["gates"]["luminotecnica"]["E_lux"] is None
    assert r["gates"]["luminotecnica"]["OK"] and "informada" in r["gates"]["luminotecnica"]["nota"]


# ------------------------------ condutores em paralelo -----------------------
def test_condutor_paralelo_900A():
    r = cd.dimensiona_condutor({"IB": 900.0, "V": 380.0, "L_km": 0.05,
                                "sistema": "trifasico", "n_cond": 3, "isolacao": "EPR",
                                "metodo": "F", "fp": 0.85, "dv_max": 7.0})
    assert r["n_paralelo"] == 2 and r["secao_mm2"] == 300
    assert r["Iz"] == 736 * 2 and r["OK"]


def test_condutor_secao_grande_unica():
    # 400 A cabe em secao unica grande (nao vira paralelo)
    r = cd.dimensiona_condutor({"IB": 400.0, "V": 380.0, "L_km": 0.05,
                                "sistema": "trifasico", "n_cond": 3, "isolacao": "EPR",
                                "metodo": "F", "fp": 0.85, "dv_max": 7.0})
    assert r["n_paralelo"] == 1 and r["secao_mm2"] in (120, 150)


def test_secoes_estendidas_ate_300():
    assert 300 in cd.SECOES and 150 in cd.SECOES
    assert cd.AMPACIDADE["EPR"]["F"][3][300] == 736


# ------------------------------ varredura de galpoes -------------------------
def _base(**kw):
    b = {"tensao_V": 380.0, "sistema": "trifasico", "origem": "subestacao_propria",
         "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2}],
                    "iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
         "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}}
    b.update(kw)
    return b


def test_varredura_nao_quebra():
    cenarios = [
        ("pequeno_BT", {"tensao_V": 220.0, "cargas": {"iluminacao_kW": 8.0, "ilum_fp": 0.92, "ocupacao": "industrial"}, "alimentador": {"L_km": 0.02}}),
        ("gigante", _base(cargas={"motores": [{"P_cv": 250.0, "eta": 0.95, "Fp": 0.88, "n": 40}], "iluminacao_kW": 200.0, "ilum_fp": 0.92, "ocupacao": "industrial"})),
        ("so_ilum", _base(cargas={"iluminacao_kW": 120.0, "ilum_fp": 0.95, "ocupacao": "industrial"})),
        ("monofasico", {"tensao_V": 220.0, "sistema": "monofasico", "cargas": {"iluminacao_kW": 5.0, "ilum_fp": 0.95, "ocupacao": "industrial"}, "alimentador": {"L_km": 0.03, "n_cond": 2}}),
        ("alim_longo", _base(alimentador={"L_km": 0.30, "metodo": "F", "isolacao": "EPR"}, transformador={"Sn_kVA": 300.0, "z_pct": 4.5})),
    ]
    for nome, spec in cenarios:
        r = ge.rodar(spec)
        for k, gate in r["gates"].items():
            assert isinstance(gate.get("OK"), bool), (nome, k, gate)
        assert isinstance(r["ATENDE"], bool), nome
        # o alimentador nunca reporta a secao minima 2,5 num galpao com carga real
        al = r["gates"]["alimentador"]
        if r["gates"]["cargas"]["D_kVA"] > 100:
            assert al["secao_mm2"] is None or al["secao_mm2"] >= 25, (nome, al["secao_mm2"])


def test_iluminacao_externa_e_climatizacao_viram_carga():
    # o loop fechado: iluminacao externa (NBR 5101) e climatizacao (NBR 16401) entram
    # como cargas do QGF e sobem a demanda.
    sp = _base(iluminacao_externa={"comprimento_m": 100.0, "Lp": 8.0, "H": 10.0,
                                   "area_tipo": "estacionamento",
                                   "luminaria": {"fluxo_lm": 15000.0, "P_W": 100.0}},
               climatizacao={"tipo": "galpao"})
    r = ge.rodar(sp)
    pg = r["cargas"]["por_grupo"]
    assert "iluminacao_externa" in pg and "climatizacao" in pg
    assert r["gates"]["climatizacao"]["capacidade_TR"] > 0
    assert r["gates"]["iluminacao_externa"]["N_postes"] > 0
    # a climatizacao entra pela POTENCIA ELETRICA (< capacidade termica)
    assert pg["climatizacao"]["D_kW"] < r["gates"]["climatizacao"]["capacidade_TR"] * 3.517


def test_coordenacao_disjuntor_upsize_condutor():
    # IB entre degraus de disjuntor + condutor marginal: o alimentador e dimensionado
    # p/ o disjuntor (IB <= IN <= IZ), nao so p/ IB -> protecao ATENDE.
    sp = _base(cargas={"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2}]},
               climatizacao={"tipo": "galpao"},
               iluminacao_externa={"comprimento_m": 100.0, "Lp": 8.0, "H": 10.0,
                                   "area_tipo": "estacionamento",
                                   "luminaria": {"fluxo_lm": 15000.0, "P_W": 100.0}})
    r = ge.rodar(sp)
    al = r["gates"]["alimentador"]; pr_g = r["gates"]["protecao"]
    assert al["OK"] and pr_g["OK"] and pr_g["IN_geral_A"] is not None
    assert pr_g["IN_geral_A"] <= al["Iz"]                  # IN <= IZ (coordenado)


def test_alim_longo_queda_governa():
    r = ge.rodar(_base(alimentador={"L_km": 0.30, "metodo": "F", "isolacao": "EPR"},
                       transformador={"Sn_kVA": 300.0, "z_pct": 4.5}))
    al = r["gates"]["alimentador"]
    assert al["OK"] and al["governante"] == "queda"         # trecho longo -> queda dita a secao
    assert al["secao_mm2"] >= 95 and al["dv_pct"] <= 7.0
