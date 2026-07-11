# ============================================================================
# test_fase66_flt_misula.py - RED tests da Fase 6.6.
# FLT de misula (barra de secao variavel) por NBR 8800 Anexo J: lambda da secao de
# MAIOR altura (J.4.2), Cb por analise racional (J.4.1, formula 5.4.2.3a), demanda
# na secao de MAIOR tensao de compressao nas mesas (max M/Wx). Substitui o metodo
# conservador (secao mais funda + Cb=1,0 + M_max cego).
# ============================================================================
import os
import sys
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS


# ==================== me-1: modulo flt_misula ==============================
def test_cb_momento_uniforme():
    import flt_misula as fm
    # momento uniforme ao longo de Lb -> Cb = 1,0
    cb = fm.cb_momento([100.0, 100.0, 100.0, 100.0, 100.0])
    assert abs(cb - 1.0) < 1e-6


def test_cb_momento_gradiente():
    import flt_misula as fm
    # gradiente linear M_max -> 0 (viga em balanco tipico): Cb ~ 1,67, sempre > 1
    cb = fm.cb_momento([100.0, 75.0, 50.0, 25.0, 0.0])
    assert cb > 1.3, "gradiente deve elevar Cb acima de 1"
    assert cb <= 3.0, "Cb nao pode exceder o teto 3,0"


def test_cb_teto_3():
    import flt_misula as fm
    # pico agudo isolado -> Cb tende ao teto; nunca ultrapassa 3,0
    cb = fm.cb_momento([100.0, 5.0, 2.0, 5.0, 3.0])
    assert cb <= 3.0 + 1e-9


def _segs_tapered():
    # rafter tapered 600->300 mm em 8 segmentos, com esforcos decrescendo do joelho
    import alma_variavel as av
    secs = av.secao_tapered(0.60, 0.30, 0.20, 0.008, 0.0125, nseg=8)
    Ms = [180.0, 150.0, 125.0, 105.0, 88.0, 74.0, 62.0, 52.0]   # kN.m por segmento
    return [{"M": Ms[i], "props": s["props"], "h_m": s["h_m"]}
            for i, s in enumerate(secs)]


def test_flt_misula_usa_secao_maior_altura():
    import flt_misula as fm
    segs = _segs_tapered()
    r = fm.flt_misula(segs, fy=250e3, Lb=4.0)
    # J.4.2: lambda da secao de MAIOR altura -> a secao usada e a mais funda (h max)
    hmax = max(s["h_m"] for s in segs)
    assert abs(r["h_secao_flt"] - hmax) < 1e-6, "FLT deve usar a secao de maior altura"


def test_flt_misula_cb_reduz_util():
    import flt_misula as fm
    segs = _segs_tapered()
    r_racional = fm.flt_misula(segs, fy=250e3, Lb=4.0)          # Cb racional (J.4.1)
    r_conserv = fm.flt_misula(segs, fy=250e3, Lb=4.0, cb=1.0)   # forcado Cb=1,0
    assert r_racional["Cb"] > 1.0, "Cb racional deve ser > 1 neste gradiente"
    assert r_racional["util"] < r_conserv["util"], "Cb>1 deve REDUZIR a utilizacao"
    assert r_racional["M_Rd"] > r_conserv["M_Rd"], "Cb>1 deve elevar M_Rd"


def test_flt_misula_demanda_max_sigma():
    import flt_misula as fm
    segs = _segs_tapered()
    r = fm.flt_misula(segs, fy=250e3, Lb=4.0)
    # J.4.1: demanda = secao de maior tensao M/Wx (nao necessariamente M_max)
    sig = [s["M"] / s["props"]["Wx"] for s in segs]
    k_sig = sig.index(max(sig))
    assert r["secao_critica"] == k_sig, "demanda deve ser a secao de max M/Wx"


def test_selftest_roda():
    import flt_misula as fm
    fm._selftest()


# ==================== me-2: rodar usa Anexo J ==============================
def _spec(tipo="alma_variavel", tapered=None):
    s = PS.novo()
    s["slug"] = "t66"
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
    if tapered is not None:
        s["estrutura"]["tapered"] = tapered
    return s


def test_rodar_flt_misula_cita_anexo_j(tmp_path):
    import rodar_projeto as RP
    s = _spec(tapered={"h_joelho": 0.60, "h_cumeeira": 0.30, "bf": 0.20,
                       "tw": 0.008, "tf": 0.0125})
    r = RP.calcular(s, str(tmp_path))
    av = r["alma_variavel"]
    assert av.get("cb_misula_raf") is not None, "sem Cb de misula da rafter"
    assert av["cb_misula_raf"] >= 1.0
    txt = open(os.path.join(str(tmp_path), "gate6-alma-variavel.txt"),
               encoding="utf-8").read()
    assert "Anexo J" in txt, "gate deve citar o Anexo J"
    # campos/headers da fase 6.b preservados (nao-regressao de contrato)
    assert av.get("util_flt_trecho") is not None
    assert "FLT DE TRECHO" in txt


def test_rodar_coluna_tapered_cb(tmp_path):
    import rodar_projeto as RP
    s = _spec(tapered={"h_joelho": 0.60, "h_cumeeira": 0.30, "h_col_base": 0.35,
                       "bf": 0.20, "tw": 0.008, "tf": 0.0125})
    r = RP.calcular(s, str(tmp_path))
    av = r["alma_variavel"]
    assert av.get("cb_misula_col") is not None, "sem Cb de misula da coluna"
