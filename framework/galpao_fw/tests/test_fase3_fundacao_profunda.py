# ============================================================================
# test_fase3_fundacao_profunda.py - RED tests da Fase 3.
# Integra a fundacao PROFUNDA (estaca Aoki-Velloso + bloco de coroamento + viga
# de baldrame) no ProjetoSpec (gates + validar + mappers) e no build 3D.
# O CALCULO ja existe (rodar_galpao 411/426); estes testes travam o WIRING de
# spec e a GEOMETRIA. Zero-erro: nada de dado geometrico inventado; o perfil SPT
# e da sondagem (PENDENTE bloqueia).
#
# Fast (pure-python): me-1..me-4 + nao-regressao da sapata.
# Build (freecadcmd, marcado 'build'): me-5 geometria da estaca/bloco/baldrame.
# ============================================================================
import os
import sys
import copy
import shutil
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import projeto_spec as PS


# --- helper: spec completo com fundacao profunda ----------------------------
_PERFIL_SPT = [                     # sondagem (dado de sitio) - topo -> ponta
    {"tipo": "argila_siltosa", "N": 5, "dz": 3.0},
    {"tipo": "silte_arenoso", "N": 12, "dz": 4.0},
    {"tipo": "areia_siltosa", "N": 25, "dz": 5.0},
]


def _spec_base(tipo_fundacao="sapata"):
    s = PS.novo()
    s["slug"] = "t3"
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
    s["fundacao"]["tipo"] = tipo_fundacao
    if tipo_fundacao == "estaca":
        s["fundacao"]["estaca"] = {
            "perfil_spt": copy.deepcopy(_PERFIL_SPT),
            "tipo_estaca": "pre_moldada", "D": 0.30, "L": 10.0, "FS": 3.0,
            "bloco": {"a_pilar": 0.30, "fck": 25e3, "fyk": 500e3},
        }
        s["baldrame"] = {"b": 0.20, "h": 0.40, "q_parede": 0.0,
                         "continuidade": "simples"}
    return s


# ============================ me-1: gate + validar ==========================
def test_novo_tem_fundacao_tipo_pendente():
    s = PS.novo()
    assert s["fundacao"].get("tipo") == PS.PENDENTE, \
        "fundacao.tipo deve nascer PENDENTE (bloqueia ate decidir sapata/estaca)"


def test_fundacao_tipo_e_requerido():
    paths = [p for p, _ in PS.REQUERIDOS]
    assert "fundacao.tipo" in paths, "fundacao.tipo deve ser REQUERIDO"


def test_estaca_perfil_spt_nao_tem_default():
    # o perfil SPT e da sondagem: nao pode nascer com valor hardcoded (mne-3)
    s = PS.novo()
    est = s["fundacao"].get("estaca")
    if est not in (None, PS.PENDENTE):
        assert not est.get("perfil_spt"), "perfil SPT nao pode ter default (sondagem)"


def test_tipo_estaca_sem_perfil_bloqueia():
    s = _spec_base("estaca")
    s["fundacao"]["estaca"]["perfil_spt"] = None       # falta a sondagem
    r = PS.validar(s)
    assert not r["ok"], "tipo=estaca sem perfil SPT deve BLOQUEAR"


def test_tipo_estaca_completo_valida():
    s = _spec_base("estaca")
    r = PS.validar(s)
    assert r["ok"], "estaca completa deve validar; faltando=%s" % r["faltando"]


def test_tipo_invalido_bloqueia():
    s = _spec_base("sapata")
    s["fundacao"]["tipo"] = "radier_magico"
    r = PS.validar(s)
    assert not r["ok"], "fundacao.tipo fora de {sapata,estaca} deve bloquear"


def test_fs_menor_que_3_sem_prova_bloqueia():
    # NBR 6122: semi-empirico s/ prova de carga -> FS >= 3,0
    s = _spec_base("estaca")
    s["fundacao"]["estaca"]["FS"] = 2.0
    r = PS.validar(s)
    assert not r["ok"] and any("FS" in p for p, _ in r["faltando"]), \
        "FS<3,0 sem prova de carga deve BLOQUEAR"


def test_fs_2_com_prova_de_carga_valida():
    s = _spec_base("estaca")
    s["fundacao"]["estaca"]["FS"] = 2.0
    s["fundacao"]["estaca"]["prova_de_carga"] = True
    assert PS.validar(s)["ok"], "FS=2,0 COM prova de carga deve validar"


# ============================ me-2: to_rodar_params =========================
def test_rodar_params_injeta_estaca():
    s = _spec_base("estaca")
    p = PS.to_rodar_params(s)
    assert p.get("estaca"), "to_rodar_params deve trazer 'estaca' quando tipo=estaca"
    assert p["estaca"].get("perfil"), "cfg da estaca precisa da chave 'perfil' (SPT)"
    assert p["estaca"]["D"] == 0.30 and p["estaca"]["L"] == 10.0


def test_rodar_params_injeta_baldrame():
    s = _spec_base("estaca")
    p = PS.to_rodar_params(s)
    assert p.get("baldrame"), "to_rodar_params deve trazer 'baldrame' quando informado"


def test_sapata_nao_injeta_estaca():
    s = _spec_base("sapata")
    p = PS.to_rodar_params(s)
    assert not p.get("estaca"), "tipo=sapata NAO deve injetar estaca (exclusivo)"


# ==================== me-3/me-4: calcular grava + to_build_kwargs ===========
def test_calcular_grava_estaca_adotada(tmp_path):
    # roda o calculo (sem FreeCAD) e confere que o spec recebe as dims p/ desenhar
    import rodar_projeto as RP
    s = _spec_base("estaca")
    RP.calcular(s, str(tmp_path))
    ea = s["estrutura"].get("estaca_adotada")
    assert ea, "calcular deve gravar estaca_adotada no spec"
    for k in ("D", "L", "n"):
        assert k in ea, "estaca_adotada sem '%s' (necessario p/ geometria)" % k
    assert s["estrutura"].get("bloco_adotado"), "faltou bloco_adotado"
    assert s["estrutura"].get("baldrame_adotado"), "faltou baldrame_adotado"


def test_build_kwargs_tem_estaca_em_mm(tmp_path):
    import rodar_projeto as RP
    s = _spec_base("estaca")
    RP.calcular(s, str(tmp_path))
    bk = PS.to_build_kwargs(s)
    assert bk.get("estaca"), "to_build_kwargs deve passar 'estaca' (tipo=estaca)"
    assert bk["estaca"]["D"] >= 100.0, "D da estaca deve ir em mm (>=100)"
    assert bk.get("bloco") and bk.get("baldrame")
    assert not bk.get("sapata"), "tipo=estaca nao desenha sapata (mne-2)"


def test_build_kwargs_sapata_nao_tem_estaca(tmp_path):
    import rodar_projeto as RP
    s = _spec_base("sapata")
    RP.calcular(s, str(tmp_path))
    bk = PS.to_build_kwargs(s)
    assert not bk.get("estaca"), "tipo=sapata nao passa estaca"


# ==================== me-6: nao-regressao da sapata =========================
def test_spec_sapata_default_inalterado():
    # a fundacao rasa (sapata) continua sendo o caminho default e nao ganha
    # chaves de estaca no build kwargs.
    s = _spec_base("sapata")
    r = PS.validar(s)
    assert r["ok"], "spec de sapata deve validar (nao-regressao): %s" % r["faltando"]


# ============================ me-5: geometria 3D (build) ====================
FREECADCMD = os.environ.get(
    "FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECADCMD), reason="freecadcmd ausente")
def test_build_desenha_estaca_bloco_baldrame(tmp_path):
    import json, tempfile, subprocess
    import rodar_projeto as RP
    import framework as FW
    s = _spec_base("estaca")
    RP.calcular(s, str(tmp_path))
    bk = PS.to_build_kwargs(s)
    bk["export_dir"] = str(tmp_path).replace("\\", "/")
    bk["doc_name"] = "t3_estaca"
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
    assert os.path.exists(stf), "build headless nao gerou resultado"
    r = json.load(open(stf, encoding="utf-8"))
    # por_grupo = lista (cat, prof, cnt, comp, massa)
    cats = " | ".join(str(row[0]) for row in (r.get("por_grupo") or []))
    assert "Estacas" in cats, "modelo sem Estacas (concreto): %s" % cats
    assert "Blocos de coroamento" in cats, "modelo sem Blocos de coroamento"
    assert "Vigas de baldrame" in cats, "modelo sem Vigas de baldrame"
    assert "Sapatas" not in cats, "tipo=estaca nao deve desenhar sapata (mne-2)"
    # auditoria: sem interferencia
    assert r.get("interferencias", 0) == 0, "estaca/bloco com interferencia"
