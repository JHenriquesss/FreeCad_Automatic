# ============================================================================
# test_fase6c_tesoura.py - RED tests da Fase 6.c (portico trelicado / tesoura).
# tesoura.py so gerava GEOMETRIA (nos+barras, isostatica). Esta fase constroi o
# CALCULO novo: solver de esforcos (metodo dos nos) + verificacao das barras
# (reusa check_nbr8800) + wiring (spec/rodar) + 3D das barras.
# ============================================================================
import os
import sys
import math
import json
import tempfile
import subprocess
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS
import tesoura as TS


# ==================== me-1: solver isostatico (equilibrio) =================
def test_resolve_trelica_equilibrio():
    t = TS.gera_trelica(20.0, 2.5, 8, "warren")
    # carga vertical para baixo em cada no do banzo superior (0..n_paineis)
    P = {}
    for i in range(t["n_paineis"] + 1):
        P[i] = (0.0, -10.0)                     # 10 kN por no, para baixo
    sol = TS.resolve_trelica(t, P)
    assert "N_barras" in sol and "reacoes" in sol
    # equilibrio GLOBAL: soma das reacoes verticais = soma das cargas (90 kN)
    Rv = sum(r[1] for r in sol["reacoes"].values())
    assert abs(Rv - 90.0) < 1e-6, "reacoes verticais nao equilibram a carga: %s" % Rv
    # equilibrio horizontal: soma Rx = 0 (so carga vertical)
    Rx = sum(r[0] for r in sol["reacoes"].values())
    assert abs(Rx) < 1e-6, "reacao horizontal espuria: %s" % Rx


def test_resolve_trelica_numero_de_esforcos():
    t = TS.gera_trelica(20.0, 2.5, 8, "pratt")
    P = {i: (0.0, -10.0) for i in range(t["n_paineis"] + 1)}
    sol = TS.resolve_trelica(t, P)
    nb = (len(t["banzo_sup"]) + len(t["banzo_inf"]) + len(t["diagonais"])
          + len(t["montantes"]))
    assert len(sol["N_barras"]) == nb, "um esforco por barra"


def test_banzo_inferior_traciona():
    # tesoura biapoiada sob gravidade: banzo INFERIOR traciona, SUPERIOR comprime
    t = TS.gera_trelica(20.0, 2.5, 8, "warren")
    P = {i: (0.0, -10.0) for i in range(t["n_paineis"] + 1)}
    sol = TS.resolve_trelica(t, P)
    Ninf = [sol["N_barras"][k] for k in sol["idx_banzo_inf"]]
    assert max(Ninf) > 0, "banzo inferior deveria tracionar (N>0)"


# ==================== me-2: verifica_tesoura ================================
def test_verifica_tesoura_util():
    cfg = {"L": 20.0, "h": 2.5, "n_paineis": 8, "tipo": "warren",
           "w_grav_kN_m": 5.0, "w_vento_kN_m": -3.0, "fy": 250e3,
           "perfil_banzo": (0.150, 0.100, 0.006, 0.009),   # I (h,b,tw,tf) em m
           "perfil_diagonal": (0.100, 0.075, 0.005, 0.008)}
    r = TS.verifica_tesoura(cfg)
    assert "u_max" in r and r["u_max"] > 0, "util maxima ausente/invalida"
    assert "barra_governante" in r
    assert "N_banzo_sup_max" in r and "N_banzo_inf_max" in r


# ==================== me-3: gate no spec ====================================
def _spec(tipo="prismatico", trelica=None):
    s = PS.novo()
    s["slug"] = "t6c"
    s["terreno"].update(area_lote_m2=4000, to_max=0.6, ca_max=1.0, tp_min=0.2,
                        recuos={"frente": 5, "lateral": 3, "fundos": 3})
    s["geometria"].update(span=20.0, comprimento=30.0, eave=6.0, ridge=8.0,
                          bay=5.0, base_fixed=True)
    s["cobertura"].update(aguas=2, slope=0.20, telha_tipo="trapezoidal",
                          telha_peso=0.10, calha=True)
    s["fechamento"].update(tipo="telha", altura_alvenaria=0, peso=0.05,
                          mesa_interna_travada=True, n_maos_francesas=2)
    s["aberturas"] = {"portao_frente": (4000, 4500), "porta_fundo": (900, 2130),
                      "janelas_laterais": (4300, 5300)}
    s["vento"].update(v0=40, cat="II", classe="B", s3=0.95, z=8.0,
                      abertura_dominante="portao_oitao")
    s["ponte"] = None
    s["cargas"].update(G=0.27, Q=0.25, self=0.35, tapamento=0.05)
    s["fundacao"]["sigma_solo_adm"] = 200.0
    s["fundacao"]["tipo"] = "sapata"
    s["estrutura"]["tipo_portico"] = tipo
    if trelica is not None:
        s["estrutura"]["trelica"] = trelica
    return s


_TREL = {"h": 2.5, "n_paineis": 8, "tipo": "warren",
         "perfil_banzo": (0.150, 0.100, 0.006, 0.009),
         "perfil_diagonal": (0.100, 0.075, 0.005, 0.008)}


def test_tipo_tesoura_valida():
    s = _spec("tesoura", _TREL)
    assert PS.validar(s)["ok"], PS.validar(s)["faltando"]


def test_mapper_passa_trelica():
    s = _spec("tesoura", _TREL)
    p = PS.to_rodar_params(s)
    assert p.get("tipo_portico") == "tesoura"
    assert p.get("trelica", {}).get("n_paineis") == 8


# ==================== me-4: rodar_galpao roteia ============================
def test_calcular_roda_tesoura(tmp_path):
    import rodar_projeto as RP
    s = _spec("tesoura", _TREL)
    r = RP.calcular(s, str(tmp_path))
    assert r.get("tesoura"), "res['tesoura'] ausente"
    assert os.path.exists(os.path.join(str(tmp_path), "gate6-tesoura.txt"))


# ==================== me-5: build 3D barras (freecadcmd) ===================
FREECADCMD = os.environ.get(
    "FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECADCMD), reason="freecadcmd ausente")
def test_build_tesoura_barras(tmp_path):
    import rodar_projeto as RP
    import framework as FW
    s = _spec("tesoura", _TREL)
    RP.calcular(s, str(tmp_path))
    bk = PS.to_build_kwargs(s)
    assert bk.get("tipo_portico") == "tesoura" and bk.get("trelica"), \
        "build_kwargs sem tesoura"
    bk["export_dir"] = str(tmp_path).replace("\\", "/")
    bk["doc_name"] = "t6c_tes"
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
    assert os.path.exists(stf), "build tesoura nao gerou resultado"
    r = json.load(open(stf, encoding="utf-8"))
    cats = " ".join(str(row[0]) for row in (r.get("por_grupo") or []))
    assert "reli" in cats or "TRELICA" in cats or "anzo" in cats, \
        "sem barras de trelica no take-off: %s" % cats
    assert r.get("interferencias", 0) == 0, "trelica com interferencia"
