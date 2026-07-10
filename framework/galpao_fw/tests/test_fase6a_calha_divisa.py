# ============================================================================
# test_fase6a_calha_divisa.py - RED tests da Fase 6.a.
# Liga 2 modulos homologados ORFAOS ao pipeline: dimensionamento de CALHA
# (hidraulico, NBR 10844/Bellei) e SAPATA DE DIVISA (excentrica + viga alavanca,
# Alonso). Calc ja existe (calhas.py / sapata_divisa.py, homologados); esta fase
# e wiring: gate -> rodar_galpao -> res -> memorial. Nada de numero inventado.
# ============================================================================
import os
import sys
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS


def _spec(divisa=None, chuva_I=None):
    s = PS.novo()
    s["slug"] = "t6a"
    s["terreno"].update(area_lote_m2=4000, to_max=0.6, ca_max=1.0, tp_min=0.2,
                        recuos={"frente": 5, "lateral": 3, "fundos": 3})
    s["geometria"].update(span=10.0, comprimento=20.0, eave=6.0, ridge=6.5,
                          bay=5.0, base_fixed=True)
    s["cobertura"].update(aguas=2, slope=0.10, telha_tipo="trapezoidal",
                          telha_peso=0.10, calha=True)
    if chuva_I is not None:
        s["cobertura"]["chuva_I_mm_h"] = chuva_I
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
    if divisa is not None:
        s["fundacao"]["divisa"] = divisa
    return s


# ============================ me-4: gates no spec ===========================
def test_novo_tem_chuva_I_default():
    s = PS.novo()
    assert s["cobertura"].get("chuva_I_mm_h") == 150.0, \
        "cobertura.chuva_I_mm_h deve nascer com default 150 (A CONFIRMAR)"


def test_novo_tem_divisa_none():
    s = PS.novo()
    assert s["fundacao"].get("divisa", "MISSING") is None, \
        "fundacao.divisa deve nascer None (sem pilar de divisa)"


def test_gates_nao_bloqueiam():
    # calha/divisa tem default/None -> nao entram em REQUERIDOS (nao bloqueiam)
    s = _spec()
    assert PS.validar(s)["ok"], PS.validar(s)["faltando"]


def test_mapper_passa_divisa_e_chuva():
    s = _spec(divisa={"dist_divisa": 0.30}, chuva_I=120.0)
    p = PS.to_rodar_params(s)
    assert p.get("divisa") == {"dist_divisa": 0.30}, "mapper deve passar divisa"
    assert p.get("chuva_I_mm_h") == 120.0, "mapper deve passar chuva_I_mm_h"


def test_mapper_sem_divisa_nao_passa():
    s = _spec()                                   # sem divisa
    p = PS.to_rodar_params(s)
    assert not p.get("divisa"), "sem gate divisa -> nao roda (mne-3)"


# ==================== me-1/me-2: calc wired (rodar) =========================
def test_calcular_roda_calha(tmp_path):
    import rodar_projeto as RP
    s = _spec()
    RP.calcular(s, str(tmp_path))
    assert os.path.exists(os.path.join(str(tmp_path), "gate-calha.txt")), \
        "faltou gate-calha.txt (calha nao rodou)"


def test_calcular_roda_divisa_quando_setado(tmp_path):
    import rodar_projeto as RP
    s = _spec(divisa={"dist_divisa": 0.30})
    r = RP.calcular(s, str(tmp_path))
    assert r.get("divisa"), "res['divisa'] ausente (sapata de divisa nao rodou)"
    assert os.path.exists(os.path.join(str(tmp_path), "gate7-divisa.txt"))


def test_calcular_sem_divisa_nao_roda(tmp_path):
    import rodar_projeto as RP
    s = _spec()
    r = RP.calcular(s, str(tmp_path))
    assert not r.get("divisa"), "divisa rodou sem gate (mne-3)"


# ==================== me-3: memorial METODOS ================================
def test_metodos_tem_estaca_calha_divisa():
    import relatorio_calculo as RC
    chaves = " ".join(RC.METODOS.keys()).lower()
    textos = " ".join(RC.METODOS.values()).lower()
    assert "calha" in chaves, "METODOS sem entrada de calha"
    assert "divisa" in chaves, "METODOS sem entrada de divisa"
    assert "aoki" in textos, "METODOS sem metodo da estaca (Aoki)"
