# ============================================================================
# test_fase611_vento_zona_tesoura.py - RED tests da Fase 6.11.
# Vento por ZONA (por agua) na tesoura: NBR 6123 Tabela 5 da Cpe por agua
# (barlavento EF / sotavento GH) atuando SIMULTANEAMENTE - o estado de projeto
# real. Hoje a tesoura usa min(net_cob) UNIFORME (estado ficticio, super-
# conservador). Cada agua recebe seu Cpe na sua metade da trelica; envelope das
# 2 direcoes de vento.
# ============================================================================
import os
import sys
import math
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, HERE)

import tesoura as TS

_PERF = (0.150, 0.100, 0.006, 0.009)
# telhado LEVE + succao alta -> a combinacao de UPLIFT governa (senao a gravidade
# domina e a distribuicao por zona seria irrelevante).
_BASE = {"L": 20.0, "h": 2.5, "n_paineis": 8, "tipo": "warren",
         "w_grav_kN_m": 1.2, "w_dead_kN_m": 0.9, "fy": 250e3, "fu": 400e3,
         "perfil_banzo": _PERF, "perfil_diagonal": _PERF}


def _cfg(**kw):
    c = dict(_BASE); c.update(kw); return c


# ==================== me-1/me-2: API e consistencia ======================
def test_zonas_iguais_reproduz_escalar():
    # w_barl == w_sot deve reproduzir EXATAMENTE o caso escalar equivalente.
    r_esc = TS.verifica_tesoura(_cfg(w_vento_kN_m=-2.0))
    r_zon = TS.verifica_tesoura(_cfg(w_vento_zonas=(-2.0, -2.0)))
    assert r_zon["u_max"] == pytest.approx(r_esc["u_max"], rel=1e-9), \
        "zonas iguais devem reproduzir o caso uniforme escalar"


def test_zonas_diferentes_cargas_diferem():
    # cargas nodais de vento das duas metades DIFEREM quando w_barl != w_sot.
    P = TS.cargas_vento_zonas(_cfg(), w_barl=-1.0, w_sot=-3.0, direction=+1)
    # no da metade esquerda (x<L/2) vs direita (x>L/2)
    t = TS.gera_trelica(20.0, 2.5, 8, "warren")
    nos = t["nos"]
    left = [i for i in range(t["n_paineis"] + 1) if nos[i][0] < 10.0 - 1e-9]
    right = [i for i in range(t["n_paineis"] + 1) if nos[i][0] > 10.0 + 1e-9]
    fy_left = P[left[1]][1]; fy_right = P[right[1]][1]
    assert abs(fy_left - fy_right) > 1e-6, "metades devem receber cargas de vento diferentes"


def test_envelope_2_direcoes_simetrico():
    # o envelope deve independer de qual agua e nomeada barlavento na entrada.
    r_a = TS.verifica_tesoura(_cfg(w_vento_zonas=(-1.0, -3.0)))
    r_b = TS.verifica_tesoura(_cfg(w_vento_zonas=(-3.0, -1.0)))
    assert r_a["u_max"] == pytest.approx(r_b["u_max"], rel=1e-9), \
        "envelope das 2 direcoes deve ser simetrico (trelica simetrica)"


def test_zona_menos_ou_igual_aco():
    # caso realista: ambas as aguas em succao, |barl| < |sot|. Por zona nao pode
    # dar MAIS aco que o uniforme-pior (min aplicado em tudo).
    r_uni = TS.verifica_tesoura(_cfg(w_vento_kN_m=-3.0))            # pior uniforme
    r_zon = TS.verifica_tesoura(_cfg(w_vento_zonas=(-1.5, -3.0)))
    assert r_zon["u_max"] <= r_uni["u_max"] + 1e-9, \
        "vento por zona nao pode superar o uniforme-pior nesta geometria"


def test_agua_em_pressao_sinal_correto():
    # uma agua em PRESSAO (Cpe>0, carga p/ baixo) nao pode virar alivio: aquela
    # metade soma a gravidade (Fy<0), a outra (succao) alivia (Fy>0).
    P = TS.cargas_vento_zonas(_cfg(), w_barl=+1.0, w_sot=-3.0, direction=+1)
    t = TS.gera_trelica(20.0, 2.5, 8, "warren"); nos = t["nos"]
    left = [i for i in range(t["n_paineis"] + 1) if nos[i][0] < 10.0 - 1e-9]
    right = [i for i in range(t["n_paineis"] + 1) if nos[i][0] > 10.0 + 1e-9]
    assert P[left[1]][1] < 0, "agua em pressao: carga para BAIXO (soma a gravidade)"
    assert P[right[1]][1] > 0, "agua em succao forte: carga para CIMA (uplift)"


def test_cumeeira_carga_media():
    # parecer item 41 (pt.1): o no da cumeeira (x=L/2) tem area tributaria metade
    # barlavento + metade sotavento -> carga da MEDIA (w_barl+w_sot)/2, nao o min.
    import tesoura as TS
    wb, ws = -2.0, -6.0
    P = TS.cargas_vento_zonas(_cfg(), w_barl=wb, w_sot=ws, direction=+1)
    t = TS.gera_trelica(20.0, 2.5, 8, "warren"); nos = t["nos"]
    ridge = [i for i in range(t["n_paineis"] + 1) if abs(nos[i][0] - 10.0) < 1e-9][0]
    trib, _ = TS._trib_sup(t)
    w_dead = _cfg()["w_dead_kN_m"]
    w_media = 1.4 * ((wb + ws) / 2.0) + 0.9 * w_dead
    assert P[ridge][1] == pytest.approx(-w_media * trib[ridge], rel=1e-9), \
        "cumeeira deve receber a carga da media das duas aguas"


def test_pressao_dead_desfavoravel():
    # parecer item 41 (pt.3): agua em PRESSAO (wv>0, p/ baixo) -> peso e DESFAVORAVEL
    # -> gamma_g = 1,4 (nao 0,9). Sucao mantem 0,9 (peso favoravel ao uplift).
    import tesoura as TS
    P = TS.cargas_vento_zonas(_cfg(), w_barl=+1.5, w_sot=-6.0, direction=+1)
    t = TS.gera_trelica(20.0, 2.5, 8, "warren"); nos = t["nos"]
    trib, _ = TS._trib_sup(t)
    wd = _cfg()["w_dead_kN_m"]
    left = [i for i in range(t["n_paineis"] + 1) if nos[i][0] < 10.0 - 1e-9]
    right = [i for i in range(t["n_paineis"] + 1) if nos[i][0] > 10.0 + 1e-9]
    # barlavento em pressao: 1,4*1,5 + 1,4*wd (peso desfavoravel)
    w_press = 1.4 * 1.5 + 1.4 * wd
    assert P[left[1]][1] == pytest.approx(-w_press * trib[left[1]], rel=1e-9), \
        "agua em pressao: peso com gamma_g=1,4 (desfavoravel)"
    # sotavento em sucao: 1,4*(-6) + 0,9*wd (peso favoravel)
    w_suc = 1.4 * (-6.0) + 0.9 * wd
    assert P[right[1]][1] == pytest.approx(-w_suc * trib[right[1]], rel=1e-9), \
        "agua em sucao: peso com gamma_g=0,9 (favoravel)"


def test_backcompat_escalar():
    # sem w_vento_zonas: comportamento atual (escalar) inalterado.
    r = TS.verifica_tesoura(_cfg(w_vento_kN_m=-2.0))
    assert r["u_max"] > 0 and r["barra_governante"]


def test_selftest_roda():
    TS._selftest()


# ==================== me-3: integracao rodar =============================
def test_cpe_longitudinal_tabela5():
    # parecer item 41 (pt.2): vento a 0 (longitudinal) - Tabela 5 colunas alpha=0.
    # EG (barlavento do comprimento) mais negativo que FH; valores verbatim.
    import vento_nbr6123 as v
    cl5 = v.cpe_telhado_longitudinal(5.0)
    assert cl5["cobertura_long_EG"] == -0.90 and cl5["cobertura_long_FH"] == -0.60
    cl10 = v.cpe_telhado_longitudinal(10.0)
    assert cl10["cobertura_long_EG"] == -0.80 and cl10["cobertura_long_FH"] == -0.60


def test_integra_reporta_zonas(tmp_path):
    import rodar_projeto as RP
    from test_fase6c_tesoura import _spec, _TREL
    s = _spec("tesoura", _TREL)
    r = RP.calcular(s, str(tmp_path))
    tz = r.get("tesoura", {})
    # 90 (por agua) + 0 (longitudinal simetrico) + governante enveloped
    for k in ("w_vento_barl_kN_m", "w_vento_sot_kN_m", "w_vento_long_kN_m",
              "vento_caso_governante", "w_vento_uniforme_kN_m"):
        assert k in tz, f"res['tesoura'] deve reportar {k}"
    assert tz["w_vento_long_kN_m"] < 0, "vento 0 (longitudinal) deve ser succao"
    assert "90" in tz["vento_caso_governante"] or "0" in tz["vento_caso_governante"]
