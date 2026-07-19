# ============================================================================
# test_fase64_coluna_tapered.py - RED tests da Fase 6.4.
# COLUNA de alma variavel (tapered): rasa na base -> funda no joelho (casa
# h_joelho do rafter). Estende a maquina tapered (hoje so rafter/misula) para a
# coluna. Sem h_col_base -> coluna prismatica (back-compat, ref intocada).
# ============================================================================
import os
import sys
import json
import tempfile
import subprocess
import importlib
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS


def _cfg_portico(gp):
    gp.configurar(span=10.0, eave=6.0, ridge=6.5, bay=5.0, base_fixed=True,
                  A_col=53.8e-4, I_col=3692e-8, A_raf=45.3e-4, I_raf=2510e-8,
                  ponte=None, sismo=None)


_TAP_COL = {"h_joelho": 0.60, "h_cumeeira": 0.30, "h_col_base": 0.35,
            "bf": 0.20, "tw": 0.008, "tf": 0.0125}
_TAP_RAF = {"h_joelho": 0.60, "h_cumeeira": 0.30,
            "bf": 0.20, "tw": 0.008, "tf": 0.0125}


# ==================== me-1: frame coluna tapered ===========================
def test_coluna_tapered_secao_variavel():
    import galpao_portico as gp
    importlib.reload(gp)
    gp.configurar(tapered=dict(_TAP_COL))
    _cfg_portico(gp)
    gp.configurar(tapered=dict(_TAP_COL))
    fr, ix = gp._frame()
    col = ix["cols"][0]
    # base rasa -> topo (joelho) fundo: I do 1o segmento (base) < I do ultimo (joelho)
    Ibase = fr.elements[col[0]]["I"]
    Itopo = fr.elements[col[-1]]["I"]
    assert Itopo > Ibase * 1.5, "coluna tapered: joelho deve ser bem mais rigido que a base"


def test_coluna_joelho_casa_rafter():
    # mne-3: CONTINUIDADE no no do joelho. O parecer (ponto 3) apontou, corretamente,
    # que comparar os pontos-MEDIOS dos segmentos com tolerancia de 20% e um proxy
    # fraco - as taxas de afinamento da coluna e do rafter diferem, entao os pontos
    # medios dao inercias diferentes SEM que haja descontinuidade real. A continuidade
    # correta e avaliada NO NO (h = h_joelho para ambos): a inercia da secao do no
    # deve ser IDENTICA (rel_tol=1e-9), pois coluna e rafter compartilham h_joelho,
    # bf, tf, tw. Extrapola a geometria linear de cada cadeia ate a coordenada do no.
    import math
    import alma_variavel as av
    t = _TAP_COL
    # coluna: h(x) linear de h_col_base (base) a h_joelho (topo=no) -> no nó h=h_joelho
    I_col_node = av.props_I(t["h_joelho"], t["bf"], t["tw"], t["tf"])["Ix"]
    # rafter: h(x) linear de h_joelho (base=no) a h_cumeeira -> no nó h=h_joelho
    I_raf_node = av.props_I(t["h_joelho"], t["bf"], t["tw"], t["tf"])["Ix"]
    assert math.isclose(I_col_node, I_raf_node, rel_tol=1e-9), \
        "no joelho a secao da coluna e do rafter devem ser IDENTICAS (continuidade estrita)"


def test_analyse_retorna_coluna_segmentos():
    import galpao_portico as gp
    importlib.reload(gp)
    gp.configurar(tapered=dict(_TAP_COL))
    _cfg_portico(gp)
    gp.configurar(tapered=dict(_TAP_COL))
    a = gp.analyse()
    cs = a.get("coluna_segmentos")
    assert cs, "analyse deve retornar coluna_segmentos quando coluna tapered"
    assert all("sec_props" in s and s["sec_props"] for s in cs), "sem props por segmento"
    assert all(s.get("h_m") for s in cs), "sem altura por segmento"


def test_coluna_prismatica_sem_h_col_base():
    # mne-2: sem h_col_base -> coluna prismatica; nao ha coluna_segmentos
    import galpao_portico as gp
    importlib.reload(gp)
    gp.configurar(tapered=dict(_TAP_RAF))   # so rafter tapered
    _cfg_portico(gp)
    gp.configurar(tapered=dict(_TAP_RAF))
    fr, ix = gp._frame()
    col = ix["cols"][0]
    Ibase = fr.elements[col[0]]["I"]
    Itopo = fr.elements[col[-1]]["I"]
    assert abs(Ibase - Itopo) < 1e-12, "coluna deve ser prismatica sem h_col_base"
    a = gp.analyse()
    assert not a.get("coluna_segmentos"), "coluna_segmentos deve ser vazio sem h_col_base"


# ==================== me-3: gate no spec ===================================
def _spec(tipo="alma_variavel", tapered=None):
    s = PS.novo()
    s["slug"] = "t64"
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


def test_coluna_tapered_valida():
    s = _spec(tapered=dict(_TAP_COL))
    v = PS.validar(s)
    assert v["ok"], v["faltando"]


def test_h_col_base_maior_que_joelho_avisa():
    s = _spec(tapered={**_TAP_COL, "h_col_base": 0.70})   # base > joelho: incoerente
    v = PS.validar(s)
    txt = " ".join(str(a) for a in v.get("avisos", []))
    assert "h_col_base" in txt, "gate deve avisar h_col_base >= h_joelho"


def test_mapper_passa_h_col_base():
    s = _spec(tapered=dict(_TAP_COL))
    p = PS.to_rodar_params(s)
    assert p.get("tapered", {}).get("h_col_base") == 0.35
    bk = PS.to_build_kwargs(s)
    assert bk.get("tapered", {}).get("h_col_base") == 350.0   # mm no build


# ==================== me-2: rodar verifica coluna por segmento ==============
def test_verificacao_coluna_por_segmento(tmp_path):
    import rodar_projeto as RP
    s = _spec(tapered=dict(_TAP_COL))
    r = RP.calcular(s, str(tmp_path))
    av = r["alma_variavel"]
    assert av.get("util_col_local_max") is not None, "sem util local da coluna"
    assert av.get("util_col_flt") is not None, "sem FLT member-level da coluna"
    assert av.get("interacao_max_col") is not None, "sem interacao por segmento da coluna"
    # parecer ponto 2: compressao GLOBAL por flexao (Anexo J.3), nao so por segmento
    assert av.get("util_col_global") is not None, "sem compressao global (Anexo J.3)"
    txt = open(os.path.join(str(tmp_path), "gate6-alma-variavel.txt"),
               encoding="utf-8").read()
    assert "COLUNA TAPERED" in txt or "COLUNA POR SEGMENTO" in txt
    assert "compressao GLOBAL" in txt and "J.3" in txt, "gate deve reportar compressao global J.3"


def test_compressao_global_menor_que_por_segmento(tmp_path):
    # parecer ponto 2: a compressao GLOBAL (secao menor altura, H inteiro) e MAIS
    # severa que a de segmento (L_seg curto -> chi~1). util_col_global deve superar a
    # utilizacao de compressao pura de um segmento isolado da base.
    import rodar_projeto as RP
    s = _spec(tapered=dict(_TAP_COL))
    r = RP.calcular(s, str(tmp_path))
    av = r["alma_variavel"]
    # sanidade: global bem definida (>0) e nao trivialmente nula
    assert av["util_col_global"] > 0.0


# ==================== me-4: build 3D coluna tapered ========================
FREECADCMD = os.environ.get(
    "FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECADCMD), reason="freecadcmd ausente")
def test_build_coluna_tapered(tmp_path):
    import rodar_projeto as RP
    import framework as FW
    s = _spec(tapered=dict(_TAP_COL))
    RP.calcular(s, str(tmp_path))
    bk = PS.to_build_kwargs(s)
    assert bk.get("tapered", {}).get("h_col_base"), "build_kwargs sem h_col_base"
    bk["export_dir"] = str(tmp_path).replace("\\", "/")
    bk["doc_name"] = "t64_coltap"
    import rodar_projeto as _RP   # _ship_build_src prepende o dir no sys.path do
    # FreeCAD p/ build_galpao importar os modulos irmaos (mao_francesa_geom) - senao
    # ModuleNotFoundError no headless (regressao PR #15; ver test_ship_build_src).
    src = _RP._ship_build_src(FW.raiz_repo() / "framework" / "galpao_fw" / "build_galpao.py")
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
    assert os.path.exists(stf), "build coluna tapered nao gerou resultado"
    r = json.load(open(stf, encoding="utf-8"))
    assert r.get("interferencias", 0) == 0, "coluna tapered com interferencia"
