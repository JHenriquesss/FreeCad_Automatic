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
    """Gera as vistas 2D no FreeCAD e exporta DXF. Retorna o path."""
    import os
    return rodar_vistas(spec, out_dir)


def rodar_vistas(spec, out_dir, host="http://localhost:9875", timeout=300):
    """Gera vistas 2D com texto real (Draft::Text) diretamente no FreeCAD.
    Cria documento separado 'Vistas2D_*' e exporta DXF."""
    import xmlrpc.client, socket, os
    import vistas_fc as VF
    PS.exigir_completo(spec)
    design = VF.design_de_spec(spec)
    design["resultados"] = spec.get("estrutura", {}).get("resultados", {})
    design["takeoff"] = spec.get("estrutura", {}).get("takeoff", [])
    design["dxf_out"] = str(out_dir).replace("\\", "/") + "/vistas_2d.dxf"

    src = VF.codigo_fonte()
    # Monta codigo que executa dentro do FreeCAD: define _result_ com o design,
    # carrega o modulo, chama gerar_vistas e captura o resultado final
    slug = design.get("slug", "galpao")
    dxf_out = design.get("dxf_out", "")
    code = (f'_result_ = {repr(design)}\n' + src +
            f'\ntry:\n'
            f'    doc = App.newDocument("Vistas2D_{slug}")\n'
            f'    gerar_vistas(_result_, doc, r"{dxf_out}")\n'
            f'    _result_ = {{"ok": True, "objetos": len(doc.Objects)}}\n'
            f'except Exception as ex:\n'
            f'    import traceback\n'
            f'    _result_ = {{"erro": str(ex), "traceback": traceback.format_exc()}}\n')
    socket.setdefaulttimeout(timeout)
    srv = xmlrpc.client.ServerProxy(host, allow_none=True)
    r = srv.execute(code)
    if isinstance(r, dict) and r.get("result"):
        spec.setdefault("estrutura", {})["vistas2d"] = r["result"]
    os.makedirs(str(out_dir), exist_ok=True)
    return os.path.join(str(out_dir), "vistas_2d.dxf")


def montar_modelo(spec, out_dir, doc_name, mf_stride=None, n_tirante_parede=None,
                  host="http://localhost:9875", timeout=180):
    """Desenha o modelo 3D + vistas 2D via MCP (FreeCAD)."""
    import xmlrpc.client, socket
    import vistas_fc as VF
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
    if isinstance(resm, dict) and resm.get("por_grupo"):
        spec.setdefault("estrutura", {})["takeoff"] = resm["por_grupo"]
    # Gera vistas 2D
    try:
        design = VF.design_de_spec(spec)
        design["resultados"] = spec.get("estrutura", {}).get("resultados", {})
        design["takeoff"] = spec.get("estrutura", {}).get("takeoff", [])
        design["dxf_out"] = str(out_dir).replace("\\", "/") + "/vistas_2d.dxf"
        vfsrc = VF.codigo_fonte()
        slug = design.get("slug", "galpao")
        dxf_out = design.get("dxf_out", "")
        code2 = (f'_result_ = {repr(design)}\n' + vfsrc +
                 f'\ntry:\n'
                 f'    doc = App.newDocument("Vistas2D_{slug}")\n'
                 f'    gerar_vistas(_result_, doc, r"{dxf_out}")\n'
                 f'    _result_ = {{"ok": True, "objetos": len(doc.Objects)}}\n'
                 f'except Exception as ex:\n'
                 f'    import traceback\n'
                 f'    _result_ = {{"erro": str(ex), "traceback": traceback.format_exc()}}\n')
        socket.setdefaulttimeout(timeout)
        r2 = srv.execute(code2)
        if isinstance(r2, dict) and r2.get("result"):
            spec.setdefault("estrutura", {})["vistas2d"] = r2["result"]
    except Exception as ex:
        print(f"2D views error: {ex}")
    return r
