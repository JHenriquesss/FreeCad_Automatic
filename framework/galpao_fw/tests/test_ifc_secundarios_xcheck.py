"""CROSS-CHECK (build): a colocacao de tercas do modelo_neutro (emissor IFC puro)
bate com o build_galpao (FreeCAD). Guarda contra o anti-padrao "duas descricoes da
mesma coisa, uma envelhece": se o build mudar a logica das tercas, este teste falha.
Marcado `build` (exige freecadcmd) -> roda na guarda local, nao no CI de nuvem.
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

import projeto_spec as PS
import rodar_projeto as RP
import framework as FW
import modelo_neutro as MN

FREECADCMD = os.environ.get(
    "FREECADCMD", r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")


def _terca_sec(est):
    td = est["terca_dims"]
    return {"nome": "Ue", "forma": "C", "d": td[0] / 1000.0, "bf": td[1] / 1000.0,
            "lip": td[2] / 1000.0, "t": td[3] / 1000.0}


@pytest.mark.build
@pytest.mark.skipif(not os.path.exists(FREECADCMD), reason="freecadcmd ausente")
def test_terca_puro_bate_com_o_build(tmp_path):
    spec = json.load(open(os.path.join(GALPAO, "spec_amostra_engenheiro.json"),
                          encoding="utf-8"))
    RP.calcular(spec, str(tmp_path))
    est = spec["estrutura"]
    g = spec["geometria"]
    # modelo PURO: contagem de tercas de cobertura
    geo = {"span": g["span"], "spans": g.get("spans"), "comprimento": g["comprimento"],
           "eave": g["eave"], "ridge": g["ridge"], "bay": g["bay"], "raf_d": 0.3}
    n_puro = len(MN.tercas(geo, est["n_terca"], _terca_sec(est)))

    # BUILD (FreeCAD): conta TERCA de COBERTURA (S* intermediarias + BEIRAL),
    # excluindo os girts de parede (TERCA_PAREDE). MESMO n_terca do calc.
    bk = PS.to_build_kwargs(spec)
    bk["n_terca"] = est["n_terca"]
    bk["export_dir"] = str(tmp_path).replace("\\", "/")
    bk["doc_name"] = "xc_terca"
    src = RP._ship_build_src(FW.raiz_repo() / "framework" / "galpao_fw" / "build_galpao.py")
    stf = os.path.join(str(tmp_path), "_xc.json").replace("\\", "/")
    boot = (src + "\nimport json, FreeCAD as App\nreset()\nconfigurar(**%r)\n_r=run()\n"
            "doc=App.ActiveDocument\n"
            "nt=sum(1 for o in doc.Objects if o.Name.startswith('TERCA_S') "
            "or o.Name.startswith('TERCA_BEIRAL'))\n"
            "open(%r,'w').write(json.dumps({'nt':nt}))\n" % (bk, stf))
    bp = tempfile.NamedTemporaryFile(mode="w", suffix="_b.py", delete=False,
                                     encoding="utf-8")
    bp.write(boot); bp.close()
    subprocess.run([FREECADCMD, bp.name], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=600)
    os.unlink(bp.name)
    assert os.path.exists(stf), "build nao gerou o cross-check"
    n_build = json.load(open(stf))["nt"]

    assert n_puro == n_build, (
        "tercas do modelo_neutro (%d) divergem do build_galpao (%d) - a logica de "
        "colocacao das tercas mudou num lado so" % (n_puro, n_build))
