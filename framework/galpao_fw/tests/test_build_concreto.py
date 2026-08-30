"""Build 3D SOLIDO do galpao de concreto (build_concreto.py).

Duas camadas, como o resto do projeto (green bar de calculo NAO cobre o layout):
  1. PURO (sem FreeCAD): caixas()/_takeoff() - orientacao/posicao/volume de cada
     peca. build_concreto importa FreeCAD LOCALMENTE, entao isto roda no CI.
  2. `build` (freecadcmd headless): o build REAL gera FCStd + IFC, 0 interferencia,
     e a contagem de solidos bate. So roda na guarda local (skip sem freecadcmd).
"""
import json
import os
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import build_concreto as bc
import galpao_concreto as gc

FREECADCMD = os.environ.get(
    "FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


def _spec(vao=10.0, n=7, **kw):
    base = {"vao": vao, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": n,
            "v0": 40.0, "cat": "IV", "classe": "B", "s1": 1.0, "s3": 1.0,
            "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
            "sigma_solo_adm": 250.0}
    base.update(kw)
    return base


# ============================ camada 1: PURO ================================
def test_uma_caixa_por_membro():
    r = gc.rodar(_spec(n=7))
    ms = gc.membros_bim(r)
    cxs = bc.caixas(ms)
    assert len(cxs) == len(ms) == 7 * 2 + 7 * 2 + 7      # colunas+sapatas+vigas
    tipos = {c["name"]: c for c in cxs}
    assert all(c["dims"][0] > 0 and c["dims"][1] > 0 and c["dims"][2] > 0
               for c in cxs), "toda caixa tem 3 dimensoes positivas"
    del tipos


def test_pilar_orientacao_e_altura():
    # G7: hx e a dimensao NO PLANO DO PORTICO (// vento) e o frame tem X = vao ->
    # o solido tem hx em X e hy em Y. Estava trocado (eixo forte fora do plano):
    # ver tests/test_pilar_orientacao_concreto.py.
    r = gc.rodar(_spec())
    col = next(c for c in bc.caixas(gc.membros_bim(r)) if c["tipo"] == "Column")
    hx = r["pilar"]["hx"]; hy = r["pilar"]["hy"]; H = r["spec"]["H"]
    assert hx >= hy                                      # senao o teste nao prova nada
    assert abs(col["dims"][0] - hx * 1000.0) < 1e-6      # X (vao) = hx
    assert abs(col["dims"][1] - hy * 1000.0) < 1e-6      # Y (comprimento) = hy
    assert abs(col["dims"][2] - H * 1000.0) < 1e-6       # Z = pe-direito
    assert abs(col["origem"][2] - 0.0) < 1e-6            # base no chao
    assert col["ifc"] == "IfcColumn"


def test_viga_corre_em_X_e_apoia_no_topo_do_pilar():
    # a viga de cobertura corre no vao (X), largura b em Y, altura h em Z, e a face
    # INFERIOR fica no topo do pilar (z = H*1000) -> compartilha face, nao penetra.
    r = gc.rodar(_spec(vao=10.0))
    cxs = bc.caixas(gc.membros_bim(r))
    beam = next(c for c in cxs if c["tipo"] == "Beam")
    col = next(c for c in cxs if c["tipo"] == "Column")
    b = r["viga"]["b"]; h = r["viga"]["h"]; H = r["spec"]["H"]
    assert abs(beam["dims"][0] - r["spec"]["vao"] * 1000.0) < 1e-6   # X = vao
    assert abs(beam["dims"][1] - b * 1000.0) < 1e-6                  # Y = largura b
    assert abs(beam["dims"][2] - h * 1000.0) < 1e-6                  # Z = altura h
    topo_pilar = col["origem"][2] + col["dims"][2]
    assert abs(beam["origem"][2] - topo_pilar) < 1e-6               # apoia no topo
    assert abs(topo_pilar - H * 1000.0) < 1e-6
    assert beam["ifc"] == "IfcBeam"


def test_sapata_topo_no_nivel_zero():
    # sapata: dims B x L x hf; topo da sapata em z=0 (base do pilar) -> origem z = -hf
    r = gc.rodar(_spec())
    foot = next(c for c in bc.caixas(gc.membros_bim(r)) if c["tipo"] == "Footing")
    B, L, hf = r["sapata"]["aprovado"][:3]
    assert abs(foot["dims"][0] - B * 1000.0) < 1e-6
    assert abs(foot["dims"][1] - L * 1000.0) < 1e-6
    assert abs(foot["dims"][2] - hf * 1000.0) < 1e-6
    assert abs((foot["origem"][2] + foot["dims"][2]) - 0.0) < 1e-6   # topo em z=0
    assert foot["ifc"] == "IfcFooting"


def test_takeoff_volume_e_massa():
    r = gc.rodar(_spec())
    cxs = bc.caixas(gc.membros_bim(r))
    tk = bc._takeoff(cxs)
    assert tk["vol_concreto_m3"] > 0
    assert abs(tk["massa_concreto_kg"] - tk["vol_concreto_m3"] * 2500.0) < 1.0
    assert set(tk["por_tipo"]) == {"Column", "Beam", "Footing"}
    assert tk["por_tipo"]["Column"]["n"] == 7 * 2


def test_pilar_e_sapata_compartilham_face_sem_penetrar():
    # base do pilar (z=0) coincide com o topo da sapata (z=0): face compartilhada,
    # interpenetracao ZERO (o build real confirma via OCCT).
    r = gc.rodar(_spec())
    cxs = bc.caixas(gc.membros_bim(r))
    col = next(c for c in cxs if c["tipo"] == "Column")
    foot = next(c for c in cxs if c["tipo"] == "Footing")
    assert abs(col["origem"][2] - (foot["origem"][2] + foot["dims"][2])) < 1e-6


def test_estaca_omite_footing_no_3d():
    perfil = [{"tipo": "argila", "N": 5, "dz": 3.0},
              {"tipo": "areia", "N": 25, "dz": 8.0}]
    r = gc.rodar(_spec(tipo_fundacao="estaca", perfil_spt=perfil,
                       D_estaca=0.30, L_estaca=10.0))
    cxs = bc.caixas(gc.membros_bim(r))
    assert not any(c["tipo"] == "Footing" for c in cxs)
    assert any(c["tipo"] == "Column" for c in cxs)


# ============================ camada 2: build ==============================
@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECADCMD), reason="freecadcmd ausente")
def test_build_headless_gera_solidos_sem_interferencia(tmp_path):
    r = gc.rodar(_spec(n=5))
    ms = gc.membros_bim(r)
    bk = {"membros": ms, "export_dir": str(tmp_path).replace("\\", "/"),
          "doc_name": "t_conc3d"}
    import rodar_projeto as RP
    import framework as FW
    src = RP._ship_build_src(FW.raiz_repo() / "framework" / "galpao_fw" / "build_concreto.py")
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
    assert os.path.exists(stf), "build concreto nao gerou resultado"
    res = json.load(open(stf, encoding="utf-8"))
    assert res.get("elementos") == len(ms), (res.get("elementos"), len(ms))
    assert res.get("interferencias", 99) == 0, res.get("interferencias_lista")
    assert os.path.exists(res["fcstd"]), "FCStd nao gravado"
    assert res.get("vol_concreto_m3", 0) > 0
