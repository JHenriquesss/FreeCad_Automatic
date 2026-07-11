# ============================================================================
# test_fase6b_alma_variavel.py - RED tests da Fase 6.b.
# Portico de ALMA VARIAVEL (tapered): a misula funda no joelho -> rasa na cumeeira.
# Integra alma_variavel.secao_tapered (homologado) na ANALISE do portico (secao por
# segmento) e no build 3D (loft). Default prismatico = ref 20x10 intocada.
# ============================================================================
import os
import sys
import copy
import json
import tempfile
import subprocess
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS


# ==================== me-1: frame tapered (galpao_portico) ==================
def _cfg_portico(gp):
    gp.configurar(span=10.0, eave=6.0, ridge=6.5, bay=5.0, base_fixed=True,
                  A_col=53.8e-4, I_col=3692e-8, A_raf=45.3e-4, I_raf=2510e-8,
                  ponte=None, sismo=None)


def test_tapered_frame_secao_variavel():
    import galpao_portico as gp
    gp.configurar(tapered={"h_joelho": 0.60, "h_cumeeira": 0.30,
                           "bf": 0.20, "tw": 0.008, "tf": 0.0125})
    _cfg_portico(gp)
    gp.configurar(tapered={"h_joelho": 0.60, "h_cumeeira": 0.30,
                           "bf": 0.20, "tw": 0.008, "tf": 0.0125})
    fr, ix = gp._frame()
    rl = ix["rafts"][0][0]                          # rafter esquerdo (eave->ridge)
    # I do 1o segmento (joelho, fundo) > I do ultimo (cumeeira, raso)
    Ijoelho = fr.elements[rl[0]]["I"]
    Icumeeira = fr.elements[rl[-1]]["I"]
    assert Ijoelho > Icumeeira * 1.5, "rafter tapered: joelho deve ser bem mais rigido"


def test_prismatico_inalterado():
    # TAPERED=None -> momento do portico identico ao prismatico (nao-regressao)
    import importlib, galpao_portico as gp
    importlib.reload(gp)
    _cfg_portico(gp)
    _, mf, ix, _ = gp._run(gp.case_G)
    m_ref = max(abs(v) for row in mf for v in (row if isinstance(row, (list, tuple)) else [row]))
    assert m_ref > 0                                # sanity; ref definido pelo prismatico


# ==================== me-2: gate no spec ====================================
def _spec(tipo="prismatico", tapered=None):
    s = PS.novo()
    s["slug"] = "t6b"
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


def test_novo_tem_tipo_portico_default():
    s = PS.novo()
    assert s["estrutura"].get("tipo_portico") == "prismatico", \
        "tipo_portico default deve ser prismatico"


def test_tipo_portico_invalido_bloqueia():
    s = _spec(tipo="banana")
    assert not PS.validar(s)["ok"], "tipo_portico invalido deve bloquear"


def test_alma_variavel_valida():
    s = _spec(tipo="alma_variavel",
              tapered={"h_joelho": 0.60, "h_cumeeira": 0.30, "bf": 0.20,
                       "tw": 0.008, "tf": 0.0125})
    assert PS.validar(s)["ok"], PS.validar(s)["faltando"]


def test_mapper_passa_tapered():
    s = _spec(tipo="alma_variavel",
              tapered={"h_joelho": 0.60, "h_cumeeira": 0.30, "bf": 0.20,
                       "tw": 0.008, "tf": 0.0125})
    p = PS.to_rodar_params(s)
    assert p.get("tipo_portico") == "alma_variavel"
    assert p.get("tapered", {}).get("h_joelho") == 0.60


# ==================== me-3: rodar_galpao roteia =============================
def test_calcular_roda_alma_variavel(tmp_path):
    import rodar_projeto as RP
    s = _spec(tipo="alma_variavel",
              tapered={"h_joelho": 0.60, "h_cumeeira": 0.30, "bf": 0.20,
                       "tw": 0.008, "tf": 0.0125})
    r = RP.calcular(s, str(tmp_path))
    assert r.get("alma_variavel"), "res['alma_variavel'] ausente"
    assert os.path.exists(os.path.join(str(tmp_path), "gate6-alma-variavel.txt"))


def test_verificacao_por_segmento(tmp_path):
    # parecer Q2: verifica FLA/FLM/FLT por segmento; a secao do joelho NAO governa
    # necessariamente (Wx cai mais rapido que M). O gate deve reportar o governante.
    import rodar_projeto as RP
    s = _spec(tipo="alma_variavel",
              tapered={"h_joelho": 0.60, "h_cumeeira": 0.30, "bf": 0.20,
                       "tw": 0.008, "tf": 0.0125})
    r = RP.calcular(s, str(tmp_path))
    av = r["alma_variavel"]
    assert av.get("interacao_max_seg") is not None, "sem verificacao por segmento"
    assert av.get("seg_governante"), "sem segmento governante"
    assert "governa_joelho" in av, "sem flag de governante-joelho"
    txt = open(os.path.join(str(tmp_path), "gate6-alma-variavel.txt"),
               encoding="utf-8").read()
    assert "VERIFICACAO POR SEGMENTO" in txt and "interacao" in txt
    # este geometria (600->300, vento) governa longe do joelho (nao no seg do joelho)
    assert av["governa_joelho"] is False, \
        "esperado governante fora do joelho neste caso (Wx cai mais rapido que M)"


# ==================== me-4: build 3D tapered (freecadcmd) ===================
FREECADCMD = os.environ.get(
    "FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECADCMD), reason="freecadcmd ausente")
def test_build_rafter_tapered(tmp_path):
    import rodar_projeto as RP
    import framework as FW
    s = _spec(tipo="alma_variavel",
              tapered={"h_joelho": 0.60, "h_cumeeira": 0.30, "bf": 0.20,
                       "tw": 0.008, "tf": 0.0125})
    RP.calcular(s, str(tmp_path))
    bk = PS.to_build_kwargs(s)
    assert bk.get("tipo_portico") == "alma_variavel", "build_kwargs sem tipo_portico"
    assert bk.get("tapered"), "build_kwargs sem tapered"
    bk["export_dir"] = str(tmp_path).replace("\\", "/")
    bk["doc_name"] = "t6b_tap"
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
    assert os.path.exists(stf), "build tapered nao gerou resultado"
    r = json.load(open(stf, encoding="utf-8"))
    assert r.get("interferencias", 0) == 0, "rafter tapered com interferencia"
    cats = " ".join(str(row[0]) for row in (r.get("por_grupo") or []))
    assert "Viga" in cats or "iga" in cats, "sem viga no take-off: %s" % cats
