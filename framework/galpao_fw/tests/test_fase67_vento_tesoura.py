# ============================================================================
# test_fase67_vento_tesoura.py - RED tests da Fase 6.7.
# Succao de vento (NBR 6123) auto-acoplada a tesoura: w_vento = envelope da zona de
# cobertura (Cpe-Cpi) * q * bay (uplift, negativo), em vez de INPUT manual (0).
# Override explicito (trelica.w_vento_kN_m) continua honrado.
# ============================================================================
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS


def _spec(tipo="tesoura", w_vento=None):
    s = PS.novo()
    s["slug"] = "t67"
    s["terreno"].update(area_lote_m2=4000, to_max=0.6, ca_max=1.0, tp_min=0.2,
                        recuos={"frente": 5, "lateral": 3, "fundos": 3})
    s["geometria"].update(span=10.0, comprimento=20.0, eave=6.0, ridge=6.5,
                          bay=5.0, base_fixed=True)
    s["cobertura"].update(aguas=2, slope=0.10, telha_tipo="trapezoidal",
                          telha_peso=0.10, calha=True)
    s["fechamento"].update(tipo="telha", altura_alvenaria=0, peso=0.05,
                          mesa_interna_travada=True, n_maos_francesas=2)
    s["aberturas"] = {"portao_frente": (4000, 4500), "porta_fundo": (900, 2130),
                      "janelas_laterais": (4300, 5300)}
    s["vento"].update(v0=40, cat="II", classe="B", s3=0.95, z=6.5,
                      abertura_dominante="portao_oitao")
    s["ponte"] = None
    s["cargas"].update(G=0.27, Q=0.25, self=0.35, tapamento=0.05)
    s["fundacao"]["sigma_solo_adm"] = 200.0
    s["fundacao"]["tipo"] = "sapata"
    s["estrutura"]["tipo_portico"] = tipo
    if tipo == "tesoura":
        tr = {"h": 1.2, "n_paineis": 8, "tipo": "warren",
              "perfil_banzo": (0.15, 0.15, 0.008, 0.008),
              "perfil_diagonal": (0.10, 0.10, 0.006, 0.006)}
        if w_vento is not None:
            tr["w_vento_kN_m"] = w_vento
        s["estrutura"]["trelica"] = tr
    return s


def test_succao_auto_negativa(tmp_path):
    import rodar_projeto as RP
    r = RP.calcular(_spec(), str(tmp_path))
    t = r["tesoura"]
    assert t.get("w_vento_auto_kN_m") is not None, "sem w_vento auto"
    assert t["w_vento_auto_kN_m"] < 0, "succao de cobertura deve ser uplift (negativa)"
    assert t.get("w_vento_fonte") == "auto"


def test_succao_auto_casa_net_q_bay(tmp_path):
    import rodar_projeto as RP
    import vento_nbr6123 as v
    r = RP.calcular(_spec(), str(tmp_path))
    v.configurar(v0=40, cat="II", classe="B", s3=0.95, z=6.5)
    vr = v.compute(larg_b=10.0, alt_h=6.0, comp_a=20.0)
    net_cob = [vr["net"][c][s] for c in vr["net"] for s in vr["net"][c]
               if s.startswith("cobertura")]
    esperado = min(net_cob) * vr["q_kN_m2"] * 5.0        # bay=5
    assert abs(r["tesoura"]["w_vento_auto_kN_m"] - esperado) < 0.05, \
        "w_vento auto deve casar min(net_cobertura)*q*bay"


def test_override_honrado(tmp_path):
    import rodar_projeto as RP
    r = RP.calcular(_spec(w_vento=-3.0), str(tmp_path))
    t = r["tesoura"]
    assert t.get("w_vento_fonte") == "input", "override do usuario deve vencer o auto"


def test_gate_cita_nbr6123(tmp_path):
    import rodar_projeto as RP
    RP.calcular(_spec(), str(tmp_path))
    txt = open(os.path.join(str(tmp_path), "gate6-tesoura.txt"),
               encoding="utf-8").read()
    assert "6123" in txt, "gate deve citar NBR 6123 no acoplamento de succao"


def test_prismatico_sem_w_vento_auto(tmp_path):
    # mne-4: acoplamento so na tesoura
    import rodar_projeto as RP
    r = RP.calcular(_spec(tipo="prismatico"), str(tmp_path))
    assert not (r.get("tesoura") or {}).get("w_vento_auto_kN_m"), \
        "prismatico nao deve ter w_vento_auto"
