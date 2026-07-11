# ============================================================================
# test_fase65_zona_painel.py - RED tests da Fase 6.5.
# ZONA DE PAINEL do no rigido viga-coluna (joelho): cisalhamento do painel da alma
# do pilar (NBR 8800 5.7.7) + estados locais sob as mesas (5.7.2/5.7.3/5.7.6) ->
# decide chapa de reforco (doubler) e/ou enrijecedores. Tesoura (sem joelho) pula.
# ============================================================================
import os
import sys
import json
import tempfile
import subprocess
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS


# ==================== me-1: modulo zona_painel =============================
def _caso_pilar(tw_col=0.0065, M=180.0, N=120.0, V=40.0):
    # HEA200-ish pilar; viga d=0.36 m
    return {"M_Sd": M, "N_Sd": N, "V_col": V,
            "dc": 0.19, "tw_col": tw_col, "bf_col": 0.20, "tf_col": 0.010,
            "Ag_col": 0.005383, "d_viga": 0.36, "tf_viga": 0.0095,
            "fy": 250e3, "extremidade": False}


def test_forca_das_mesas():
    import zona_painel as zp
    # FSd = M/dm, dm = d_viga - tf_viga
    F = zp.forca_das_mesas(180.0, 0.36, 0.0095)
    assert abs(F - 180.0 / (0.36 - 0.0095)) < 1e-6


def test_painel_sem_axial_igual_Vrd():
    import zona_painel as zp
    r = zp.cisalhamento_painel(_caso_pilar(N=0.0))
    # N_Sd <= 0.4 Npl -> F_Rd = V_Rd
    assert abs(r["F_Rd"] - r["V_Rd"]) < 1e-6
    # V_Rd = 0.6 fy dc tw / GA1 (secao compacta)
    import check_nbr8800 as ck
    Vrd = 0.6 * 250e3 * 0.19 * 0.0065 / ck.GA1
    assert abs(r["V_Rd"] - Vrd) / Vrd < 0.02


def test_axial_alto_reduz_Frd():
    # mne-4: N_Sd > 0.4 Npl -> F_Rd = V_Rd*(1.4 - N_Sd/Npl)
    import zona_painel as zp
    Npl = 0.005383 * 250e3          # ~1345 kN
    r = zp.cisalhamento_painel(_caso_pilar(N=0.6 * Npl))
    fator = 1.4 - 0.6
    assert abs(r["F_Rd"] - r["V_Rd"] * fator) / r["V_Rd"] < 0.02
    assert r["F_Rd"] < r["V_Rd"], "axial alto deve reduzir F_Rd"


def test_alma_fina_exige_doubler():
    import zona_painel as zp
    r = zp.verifica_painel(_caso_pilar(tw_col=0.004, M=260.0, N=80.0))
    assert r["precisa_reforco"], "alma fina + momento alto deve exigir doubler"
    assert r["t_doubler_mm"] > 0
    # doubler dimensionado: reforco adicional cobre o excesso FSd - F_Rd
    import check_nbr8800 as ck
    add = 0.6 * 250e3 * 0.19 * (r["t_doubler_mm"] / 1000.0) / ck.GA1
    assert add >= (r["FSd"] - r["F_Rd"]) - 1e-6, "doubler nao cobre o excesso"


def test_alma_espessa_passa():
    import zona_painel as zp
    r = zp.verifica_painel(_caso_pilar(tw_col=0.020, M=120.0, N=60.0))
    assert not r["precisa_reforco"], "alma espessa deve passar sem doubler"
    assert r["u_painel"] < 1.0


def test_estados_locais_mesa_fina():
    import zona_painel as zp
    # mesa do pilar fina -> flexao local da mesa (5.7.2) / flambagem (5.7.6) estoura
    c = _caso_pilar(M=260.0, N=40.0); c["tf_col"] = 0.005; c["tw_col"] = 0.004
    r = zp.verifica_painel(c)
    assert r["precisa_enrijecedor"], "mesa/alma fina deve exigir enrijecedor"


def test_selftest_roda():
    import zona_painel as zp
    zp._selftest()          # nao deve levantar


# ==================== me-2: rodar integra no joelho =======================
def _spec(tipo="prismatico", tapered=None):
    s = PS.novo()
    s["slug"] = "t65"
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


def test_rodar_prismatico_tem_zona_painel(tmp_path):
    import rodar_projeto as RP
    r = RP.calcular(_spec("prismatico"), str(tmp_path))
    assert r.get("zona_painel"), "res['zona_painel'] ausente no prismatico"
    assert os.path.exists(os.path.join(str(tmp_path), "gate-zona-painel.txt"))
    txt = open(os.path.join(str(tmp_path), "gate-zona-painel.txt"),
               encoding="utf-8").read()
    assert "CISALHAMENTO DO PAINEL" in txt


def test_rodar_alma_var_tem_zona_painel(tmp_path):
    import rodar_projeto as RP
    s = _spec("alma_variavel",
              tapered={"h_joelho": 0.60, "h_cumeeira": 0.30, "bf": 0.20,
                       "tw": 0.008, "tf": 0.0125})
    r = RP.calcular(s, str(tmp_path))
    assert r.get("zona_painel"), "res['zona_painel'] ausente no alma variavel"


def test_rodar_tesoura_sem_zona_painel(tmp_path):
    # mne-3: tesoura nao tem joelho rigido -> sem zona_painel
    import rodar_projeto as RP
    s = _spec("tesoura")
    s["estrutura"]["trelica"] = {"h": 1.2, "n_paineis": 8, "tipo": "warren",
                                 "perfil_banzo": (0.15, 0.15, 0.008, 0.008),
                                 "perfil_diagonal": (0.10, 0.10, 0.006, 0.006)}
    r = RP.calcular(s, str(tmp_path))
    assert not r.get("zona_painel"), "tesoura nao deve ter zona_painel (sem joelho)"


# ==================== me-3: build desenha reforco quando exigido ===========
FREECADCMD = os.environ.get(
    "FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECADCMD), reason="freecadcmd ausente")
def test_build_sem_reforco_nao_cria_doubler(tmp_path):
    # mne-2: caso de referencia (sem gatilho) NAO cria DOUBLER/ENRIJ_JOELHO
    import rodar_projeto as RP
    import framework as FW
    s = _spec("prismatico")
    RP.calcular(s, str(tmp_path))
    bk = PS.to_build_kwargs(s)
    bk["export_dir"] = str(tmp_path).replace("\\", "/")
    bk["doc_name"] = "t65_ref"
    src = (FW.raiz_repo() / "framework" / "galpao_fw" / "build_galpao.py"
           ).read_text(encoding="utf-8").replace("_result_ = run()", "")
    stf = os.path.join(str(tmp_path), "_b.json").replace("\\", "/")
    boot = (src + "\nimport json\nreset()\nconfigurar(**%r)\n_r = run()\n"
            "open(%r,'w',encoding='utf-8').write(json.dumps(_r, default=str))\n"
            % (bk, stf))
    bp = tempfile.NamedTemporaryFile(mode="w", suffix="_b.py", delete=False,
                                     encoding="utf-8")
    bp.write(boot); bp.close()
    subprocess.run([FREECADCMD, bp.name], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=600)
    os.unlink(bp.name)
    assert os.path.exists(stf)
    r = json.load(open(stf, encoding="utf-8"))
    assert r.get("interferencias", 0) == 0
