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
    if res.get("perfil_col"):
        spec.setdefault("estrutura", {})
        spec["estrutura"]["perfil_col_adotado"] = res["perfil_col"]
        spec["estrutura"]["perfil_raf_adotado"] = res["perfil_raf"]
    if res.get("base_adotada"):
        spec.setdefault("estrutura", {})
        spec["estrutura"]["base_adotada"] = res["base_adotada"]
    return res


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
    return srv.execute(src + call)
