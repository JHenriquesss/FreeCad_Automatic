# ============================================================================
# rodar_projeto.py - RUNNER LIMPO de um projeto (spec -> calculo + modelo)
# Sequencia segura e portavel: reset (estado limpo) -> validar (trava se
# incompleto) -> calculo (memoriais) -> modelo via MCP (reset+configurar+run).
# Caminhos relativos (framework.raiz_repo). Chamavel de qualquer PC / projeto.
# ============================================================================
"""Runner de projeto: reset -> validar -> calculo -> modelo. Portavel e isolado."""

from __future__ import annotations

import framework as FW
import projeto_spec as PS
import rodar_galpao as R


def calcular(spec, out_dir):
    """Roda o calculo (Gates 5-11) do spec. Reseta o estado antes; valida (trava
    se incompleto). Retorna o dict de resultados; memoriais em out_dir."""
    FW.reset_tudo()
    PS.exigir_completo(spec)
    params = PS.to_rodar_params(spec)
    res = R.rodar(params, str(out_dir))
    # grava o perfil ADOTADO no spec -> o modelo desenha o que o calculo dimensionou
    if res.get("perfil_colunas"):
        spec.setdefault("estrutura", {})
        spec["estrutura"]["perfil_col_adotado"] = res["perfil_colunas"][0]
        spec["estrutura"]["perfil_raf_adotado"] = res["perfil_raf"]
    if res.get("base_adotada"):
        spec.setdefault("estrutura", {})
        spec["estrutura"]["base_adotada"] = res["base_adotada"]
    if res.get("sapata_adotada"):
        spec.setdefault("estrutura", {})
        spec["estrutura"]["sapata_adotada"] = res["sapata_adotada"]
        spec["estrutura"]["sapata_quant"] = res.get("sapata_quant")
    if res.get("joelho_adotado"):
        spec.setdefault("estrutura", {})
        spec["estrutura"]["joelho_adotado"] = res["joelho_adotado"]
    if res.get("n_tirante_parede") is not None:
        spec.setdefault("estrutura", {})
        spec["estrutura"]["n_tirante_parede"] = res["n_tirante_parede"]
        spec["estrutura"]["perfil_escora"] = res.get("perfil_escora")
        spec["estrutura"]["perfil_montante"] = res.get("perfil_montante")
    if res.get("terca_dims"):
        spec.setdefault("estrutura", {})["terca_dims"] = res["terca_dims"]
    if res.get("longarina_dims"):
        spec.setdefault("estrutura", {})["longarina_dims"] = res["longarina_dims"]
        spec["estrutura"]["longarina_perfil"] = res.get("longarina_perfil")
    # quadro de verificacoes (utilizacoes/resultados) para o DXF
    spec.setdefault("estrutura", {})["resultados"] = {
        "Maxima": res.get("interacao_max"), "Coluna": res.get("interacao_col"), "Viga": res.get("interacao_raf"),
        "Flecha portico": res.get("flecha_util"),
        "Base": res.get("base_util"), "Sapata": res.get("sapata_util"),
        "Joelho": res.get("joelho_util"), "Terca": res.get("terca_inter"),
        "Longarina": res.get("longarina_inter"), "Escora": res.get("escora_inter"),
        "Montante": res.get("montante_inter"), "Verga": res.get("verga_inter"),
        "Viga rolamento": res.get("ponte_viga_inter"),
    }
    return res


def gerar_dxf(spec, out_dir, nome=None):
    """Gera o DXF com as vistas (portico, elevacao, planta, legenda) a partir do
    spec com perfil/base ADOTADOS (rodar calcular() antes). Retorna o path."""
    import os
    import dxf_vistas as dv
    PS.exigir_completo(spec)
    os.makedirs(str(out_dir), exist_ok=True)
    path = os.path.join(str(out_dir), (nome or spec.get("slug", "galpao")) + ".dxf")
    return dv.gerar_dxf(dv.design_de_spec(spec), path)


def montar_modelo(spec, out_dir, doc_name, mf_stride=None, n_tirante_parede=None,
                  host="http://localhost:9875", timeout=180):
    """Desenha o modelo via MCP (FreeCAD). reset() ANTES de configurar (slate
    limpo) - so desenha o que o spec pede. Retorna o result do bridge."""
    import xmlrpc.client
    import socket
    PS.exigir_completo(spec)
    bk = PS.to_build_kwargs(spec)
    if mf_stride is not None:
        bk["mf_stride"] = mf_stride
    if n_tirante_parede is not None:
        bk["n_tirante_parede"] = n_tirante_parede
    bk["export_dir"] = str(out_dir).replace("\\", "/")
    bk["doc_name"] = doc_name
    src_path = FW.raiz_repo() / "framework" / "galpao_fw" / "build_galpao.py"
    src = src_path.read_text(encoding="utf-8").replace("_result_ = run()", "")
    call = "reset()\nconfigurar(**%r)\n_result_ = run()\n" % (bk,)
    socket.setdefaulttimeout(timeout)
    srv = xmlrpc.client.ServerProxy(host)
    r = srv.execute(src + call)
    resm = r.get("result") if isinstance(r, dict) else None
    if isinstance(resm, dict) and resm.get("por_grupo"):     # takeoff -> DXF
        spec.setdefault("estrutura", {})["takeoff"] = resm["por_grupo"]
    return r
