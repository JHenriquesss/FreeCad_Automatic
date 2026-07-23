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
    # modelo PURO: contagem de tercas de cobertura + girts de parede
    geo = {"span": g["span"], "spans": g.get("spans"), "comprimento": g["comprimento"],
           "eave": g["eave"], "ridge": g["ridge"], "bay": g["bay"], "raf_d": 0.3}
    n_puro = len(MN.tercas(geo, est["n_terca"], _terca_sec(est)))
    ld = est.get("longarina_dims")
    import perfis
    col_d = (perfis.PERFIS.get(est.get("perfil_col_adotado"), {}) or {}).get("d", 0.0)
    gsec = ({"nome": "U", "forma": "U", "d": ld[0] / 1000.0, "bf": ld[1] / 1000.0,
             "tw": ld[2] / 1000.0, "tf": ld[3] / 1000.0} if ld else None)
    n_girt_puro = len(MN.girts(geo, gsec, col_d)) if gsec else 0
    girt_d = ld[0] / 1000.0 if ld else 0.0
    n_tir_puro = len(MN.tirantes_parede(geo, est.get("n_tirante_parede"), 16.0,
                                        col_d, girt_d)) if est.get("n_tirante_parede") else 0
    n_cv_puro = len(MN.contrav_cobertura(geo, 20.0))
    sa = est.get("sapata_adotada")
    fsec = ({"B": sa["B"], "L": sa["L"], "h": sa["h"], "tipo": sa.get("tipo")}
            if sa and all(k in sa for k in ("B", "L", "h")) else None)
    n_fund_puro = len(MN.fundacoes(geo, fsec)) if fsec else 0
    n_telha_puro = len(MN.telhas(geo))
    n_tap_puro = len(MN.tapamentos(geo, fechamento=spec.get("fechamento"),
                                   aberturas=spec.get("aberturas")))
    ba = est.get("base_adotada")
    bsec = ({"B": ba["B"], "L": ba["L"], "t": ba["t"]}
            if ba and all(k in ba for k in ("B", "L", "t")) else None)
    n_base_puro = len(MN.placas_base(geo, bsec)) if bsec else 0
    n_nerv_puro = (len(MN.nervuras_base(geo, col_d, bsec["L"]))
                   if bsec and col_d else 0)
    n_clip_puro = (len(MN.clipes_terca(geo, est["n_terca"], _terca_sec(est)))
                   + (len(MN.clipes_girt(geo)) if gsec else 0))

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
            "ng=sum(1 for o in doc.Objects if o.Name.startswith('TERCA_PAREDE'))\n"
            "ntir=sum(1 for o in doc.Objects if o.Name.startswith('TIRANTE_PAREDE'))\n"
            "ncv=sum(1 for o in doc.Objects if o.Name.startswith('CONTRAV_COBERTURA'))\n"
            "nf=sum(1 for o in doc.Objects if o.Name.startswith('SAPATA_') "
            "or o.Name.startswith('BLOCO_'))\n"
            "ntel=sum(1 for o in doc.Objects if o.Name.startswith('TELHA_S'))\n"
            "ntap=sum(1 for o in doc.Objects if o.Name.startswith('TAPAMENTO'))\n"
            "nbase=sum(1 for o in doc.Objects if o.Name.startswith('PLACA_BASE'))\n"
            "nnerv=sum(1 for o in doc.Objects if o.Name.startswith('NERVURA_BASE'))\n"
            "nclip=sum(1 for o in doc.Objects if o.Name.startswith('CLIPE'))\n"
            "open(%r,'w').write(json.dumps({'nt':nt,'ng':ng,'ntir':ntir,'ncv':ncv,"
            "'nf':nf,'ntel':ntel,'ntap':ntap,'nbase':nbase,'nnerv':nnerv,'nclip':nclip}))\n"
            % (bk, stf))
    bp = tempfile.NamedTemporaryFile(mode="w", suffix="_b.py", delete=False,
                                     encoding="utf-8")
    bp.write(boot); bp.close()
    subprocess.run([FREECADCMD, bp.name], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=600)
    os.unlink(bp.name)
    assert os.path.exists(stf), "build nao gerou o cross-check"
    d = json.load(open(stf))

    assert n_puro == d["nt"], (
        "tercas do modelo_neutro (%d) divergem do build_galpao (%d) - a logica de "
        "colocacao das tercas mudou num lado so" % (n_puro, d["nt"]))
    # girts: valido so sem porta lateral (que segmentaria a parede no build)
    if not spec.get("aberturas", {}).get("porta_lateral"):
        assert n_girt_puro == d["ng"], (
            "girts do modelo_neutro (%d) divergem do build_galpao (%d)"
            % (n_girt_puro, d["ng"]))
    assert n_tir_puro == d["ntir"], (
        "tirantes de parede do modelo_neutro (%d) divergem do build (%d)"
        % (n_tir_puro, d["ntir"]))
    assert n_cv_puro == d["ncv"], (
        "contraventamento do modelo_neutro (%d) diverge do build (%d)"
        % (n_cv_puro, d["ncv"]))
    assert n_fund_puro == d["nf"], (
        "fundacoes do modelo_neutro (%d) divergem do build (%d)"
        % (n_fund_puro, d["nf"]))
    assert n_telha_puro == d["ntel"], (
        "telhas do modelo_neutro (%d) divergem do build (%d)"
        % (n_telha_puro, d["ntel"]))
    assert n_tap_puro == d["ntap"], (
        "tapamentos do modelo_neutro (%d) divergem do build (%d) - a logica de "
        "fechamento de parede mudou num lado so" % (n_tap_puro, d["ntap"]))
    assert n_base_puro == d["nbase"], (
        "placas de base do modelo_neutro (%d) divergem do build (%d)"
        % (n_base_puro, d["nbase"]))
    assert n_nerv_puro == d["nnerv"], (
        "nervuras de base do modelo_neutro (%d) divergem do build (%d)"
        % (n_nerv_puro, d["nnerv"]))
    assert n_clip_puro == d["nclip"], (
        "clipes (terça+girt) do modelo_neutro (%d) divergem do build (%d)"
        % (n_clip_puro, d["nclip"]))
