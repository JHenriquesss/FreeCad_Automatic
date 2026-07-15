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
    # fundacao PROFUNDA: grava a geometria dimensionada (estaca + bloco + baldrame)
    # p/ o build 3D desenhar exatamente o que o calculo produziu (nada inventado).
    if res.get("estaca"):
        e = res["estaca"]
        spec.setdefault("estrutura", {})
        spec["estrutura"]["estaca_adotada"] = {
            "D": e["D"], "L": e["L"], "n": e["n_estacas"],
            "espacamento": e["espacamento"], "tipo": e["tipo"],
            "uplift": e.get("uplift", False)}
        spec["estrutura"]["bloco_adotado"] = {
            "h": e["bloco_h"], "a": e["bloco_a"]}
    if res.get("baldrame"):
        b = res["baldrame"]
        spec.setdefault("estrutura", {})
        spec["estrutura"]["baldrame_adotado"] = {
            "b": b["b"], "h": b["h"], "vao": b["vao"]}
    if res.get("joelho_adotado"):
        spec.setdefault("estrutura", {})
        spec["estrutura"]["joelho_adotado"] = res["joelho_adotado"]
    if res.get("n_tirante_parede") is not None:
        spec.setdefault("estrutura", {})
        spec["estrutura"]["n_tirante_parede"] = res["n_tirante_parede"]
        spec["estrutura"]["perfil_escora"] = res.get("perfil_escora")
        spec["estrutura"]["perfil_montante"] = res.get("perfil_montante")
    if res.get("gusset_adotado"):
        spec.setdefault("estrutura", {})["gusset_adotado"] = res["gusset_adotado"]
    if res.get("zona_painel"):
        spec.setdefault("estrutura", {})["zona_painel_adotado"] = res["zona_painel"]
    if res.get("console_adotado"):
        spec.setdefault("estrutura", {})["console_adotado"] = res["console_adotado"]
    if res.get("terca_dims"):
        spec.setdefault("estrutura", {})["terca_dims"] = res["terca_dims"]
    if res.get("longarina_dims"):
        spec.setdefault("estrutura", {})["longarina_dims"] = res["longarina_dims"]
        spec["estrutura"]["longarina_perfil"] = res.get("longarina_perfil")
    # quadro de verificacoes (utilizacoes/resultados) para as pranchas. Inclui os
    # sub-sistemas novos (tesoura, telha, contravento/gusset, console, fogo,
    # estaca/baldrame/travamento, sismo, junta, calha, divisa, escada, plataforma,
    # zona de painel, terreno) - antes so continha os elementos antigos.
    def _flag(ok):                       # None (nao rodou) / "OK" / "NAO ATENDE"
        return None if ok is None else ("OK" if ok else "NAO ATENDE")
    def _u(d, f="u_max"):                # util aninhada
        return d.get(f) if isinstance(d, dict) else None
    resultados = {
        "Maxima": res.get("interacao_max"), "Coluna": res.get("interacao_col"),
        "Viga": res.get("interacao_raf"), "Tesoura": _u(res.get("tesoura")),
        "Flecha portico": res.get("flecha_util"),
        "Base": res.get("base_util"), "Sapata": res.get("sapata_util"),
        "Joelho": res.get("joelho_util"), "Zona painel": _u(res.get("zona_painel")),
        "Terca": res.get("terca_inter"), "Telha": res.get("telha_util"),
        "Longarina": res.get("longarina_inter"), "Escora": res.get("escora_inter"),
        "Montante": res.get("montante_inter"), "Verga": res.get("verga_inter"),
        "Contrav./tirantes": res.get("barras_u_max"), "Gusset": res.get("gusset_u_max"),
        "Viga rolamento": res.get("ponte_viga_inter"), "Console": res.get("console_u_max"),
        "Fogo (theta/theta_cr)": res.get("fogo_util"),
    }
    # estados booleanos (OK/NAO ATENDE/None) dos gates que nao tem util numerica
    estados = {
        "Estaca": _flag((res.get("estaca") or {}).get("ok") if res.get("estaca") else None),
        "Travamento transv.": _flag((res.get("travamento_transversal") or {}).get("ok") if res.get("travamento_transversal") else None),
        "Baldrame long.": _flag((res.get("baldrame") or {}).get("ok") if res.get("baldrame") else None),
        "Sismo (theta)": _flag((res.get("sismo_theta") or {}).get("ok") if res.get("sismo_theta") else None),
        "Junta dilatacao": _flag((not res["junta_dilatacao"]["precisa"]) if res.get("junta_dilatacao") else None),
        "Calha": _flag((res.get("calha") or {}).get("ok") if res.get("calha") else None),
        "Divisa": _flag((res.get("divisa") or {}).get("ok") if res.get("divisa") else None),
        "Terreno": _flag((res.get("terreno") or {}).get("ok") if res.get("terreno") else None),
        "Escada": _flag(res.get("escada_ok") if "escada_ok" in res else None),
        "Plataforma": _flag(res.get("plataforma_ok") if "plataforma_ok" in res else None),
    }
    spec.setdefault("estrutura", {})["resultados"] = resultados
    spec["estrutura"]["estados"] = {k: v for k, v in estados.items() if v is not None}
    return res


def montar_modelo(spec, out_dir, doc_name, mf_stride=None, n_tirante_parede=None,
                  host="http://localhost:9875", timeout=180):
    """Desenha o modelo 3D via MCP (FreeCAD)."""
    import xmlrpc.client, socket
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
    return r


def rodar_executivo(spec, out_dir, fcstd_path, freecad_exe=None, timeout=1200):
    """Gera o projeto executivo COMPLETO (pranchas A1 TechDraw) a partir do
    modelo 3D ja SALVO em fcstd_path. Roda o freecad.exe em modo headless
    (GUI disponivel p/ exportar PDF, sem interacao: job por QTimer, janela
    fecha sozinha). Exporta PDF + SVG + DXF por prancha em out_dir/pranchas.

    Nao usa o servidor MCP (que corta em ~30 s e nao aguenta a projecao do
    modelo cheio). Le o resultado de out_dir/pranchas/_status.json."""
    import os, json, time, tempfile, subprocess
    import techdraw_exec as TD
    PS.exigir_completo(spec)

    exe = freecad_exe or os.environ.get("FREECAD_EXE") or \
        r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe"
    if not os.path.exists(exe):
        return {"erro": f"freecad.exe nao encontrado: {exe}"}

    cfg = TD.config_de_spec(spec, fcstd_path, str(out_dir))
    prdir = os.path.join(str(out_dir), "pranchas")
    os.makedirs(prdir, exist_ok=True)
    status = os.path.join(prdir, "_status.json")
    try:
        os.remove(status)
    except OSError:
        pass

    boot = tempfile.NamedTemporaryFile(
        mode="w", suffix="_exec.py", delete=False, encoding="utf-8")
    boot.write(TD.script_bootstrap(cfg))
    boot.close()

    proc = subprocess.Popen([exe, boot.name],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    res = None
    while time.time() - t0 < timeout:
        if os.path.exists(status):
            time.sleep(0.5)
            with open(status, encoding="utf-8") as f:
                res = json.load(f)
            break
        if proc.poll() is not None and not os.path.exists(status):
            time.sleep(2)  # processo saiu; da uma ultima chance ao arquivo
            if os.path.exists(status):
                with open(status, encoding="utf-8") as f:
                    res = json.load(f)
            else:
                res = {"erro": "freecad.exe encerrou sem gerar _status.json"}
            break
        time.sleep(2)
    if res is None:
        res = {"erro": f"timeout {timeout}s aguardando pranchas"}
        try:
            proc.kill()
        except Exception:
            pass
    try:
        os.unlink(boot.name)
    except OSError:
        pass
    spec.setdefault("estrutura", {})["executivo"] = res
    return res
