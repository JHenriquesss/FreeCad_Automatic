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
        # n_terca + perfil da terca -> o emissor IFC puro (ifc_emit) coloca as tercas
        spec["estrutura"]["n_terca"] = res.get("n_terca")
        spec["estrutura"]["terca_perfil"] = res.get("terca_perfil")
    if res.get("longarina_dims"):
        spec.setdefault("estrutura", {})["longarina_dims"] = res["longarina_dims"]
        spec["estrutura"]["longarina_perfil"] = res.get("longarina_perfil")
    # DRENAGEM: a secao da calha e o diametro do condutor sao DIMENSIONADOS
    # (calhas.dimensiona: escada de secoes ate drenar a vazao + borda livre +
    # Bellei; condutor por vazao, NBR 10844). Ficavam fixos no build (200x300 e
    # d100) -> o 3D/prancha/takeoff desenhavam calha de 300 mm de altura enquanto
    # a memoria dizia 150. Grava p/ o to_build_kwargs levar ao modelo.
    if res.get("calha"):
        spec.setdefault("estrutura", {})["calha_adotada"] = res["calha"]
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
        # A peca da mao-francesa (gate 7b, NBR 8800 4.11.3.4). Estava SO na linha
        # de resumo "ELEMENTOS QUE NAO ATENDEM": o quadro que o engenheiro le item
        # a item omitia justamente o elemento que reprovava.
        "Mao-francesa (peca)": res.get("mf_peca_u"),
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
    spec["estrutura"]["romaneio"] = res.get("romaneio_itens")   # marcas de peca -> PE09
    return res


def _ship_build_src(src_path):
    """Fonte de build_galpao.py PRONTA p/ enviar ao FreeCAD (execute), com o dir do
    galpao_fw prependado no sys.path. build_galpao vai como FONTE (nao importado);
    seus imports de MODULOS IRMAOS (ex. mao_francesa_geom) so resolvem se o dir
    estiver no sys.path do FreeCAD - senao ModuleNotFoundError no build 3D. Helper
    testavel (test_ship_build_src) p/ a regressao nao voltar silenciosa. Caca sessao 14.

    O processo do freecad.exe da ponte PERSISTE entre execucoes: um modulo irmao
    ja importado fica em sys.modules e o build continuaria rodando a versao ANTIGA
    ate reiniciar o FreeCAD. Isso mascara em SILENCIO correcoes ja mergeadas - o
    fix das pontas da mao-francesa (PR #41) ficou fora do modelo por isso, com o
    3D mostrando 20/24 bracos tocando a terca enquanto o codigo ja dizia 24/24.
    Por isso o bootstrap DESCARTA os modulos irmaos do cache antes de rodar."""
    from pathlib import Path
    src_path = Path(src_path)
    gdir = str(src_path.parent).replace("\\", "/")
    irmaos = tuple(sorted(p.stem for p in src_path.parent.glob("*.py")))
    boot = ("import sys\n"
            "if %r not in sys.path: sys.path.insert(0, %r)\n"
            "for _m in [n for n in list(sys.modules) if n in %r]:\n"
            "    del sys.modules[_m]\n" % (gdir, gdir, irmaos))
    return boot + src_path.read_text(encoding="utf-8").replace("_result_ = run()", "")


def montar_modelo(spec, out_dir, doc_name, mf_stride=None, n_tirante_parede=None,
                  n_terca=None, host="http://localhost:9875", timeout=180):
    """Desenha o modelo 3D via MCP (FreeCAD).

    mf_stride/n_terca vem do CALC (nao do spec): sao auto-dimensionados pelo gate 7.
    n_terca em especial define o VAO DA TELHA - se o 3D usar outro valor, o modelo,
    as pranchas e o takeoff contradizem a memoria de calculo."""
    import xmlrpc.client, socket
    PS.exigir_completo(spec)
    bk = PS.to_build_kwargs(spec)
    if mf_stride is not None:
        bk["mf_stride"] = mf_stride
    if n_terca is not None:
        bk["n_terca"] = n_terca
    if n_tirante_parede is not None:
        bk["n_tirante_parede"] = n_tirante_parede
    bk["export_dir"] = str(out_dir).replace("\\", "/")
    bk["doc_name"] = doc_name
    src_path = FW.raiz_repo() / "framework" / "galpao_fw" / "build_galpao.py"
    src = _ship_build_src(src_path)
    call = "reset()\nconfigurar(**%r)\n_result_ = run()\n" % (bk,)
    socket.setdefaulttimeout(timeout)
    srv = xmlrpc.client.ServerProxy(host)
    r = srv.execute(src + call)
    resm = r.get("result") if isinstance(r, dict) else None
    if isinstance(resm, dict) and resm.get("por_grupo"):
        spec.setdefault("estrutura", {})["takeoff"] = resm["por_grupo"]
    if isinstance(resm, dict) and resm.get("por_marca"):
        spec.setdefault("estrutura", {})["por_marca"] = resm["por_marca"]  # lista de corte/marcas
    if isinstance(resm, dict) and resm.get("ifc"):
        spec.setdefault("estrutura", {})["ifc"] = resm["ifc"]  # entregavel BIM (IFC4 p/ Revit)
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
    try:
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
    finally:
        # SEMPRE encerra o freecad.exe (sucesso, erro, timeout). Antes so matava no
        # timeout, e via proc.kill() (TerminateProcess), que NAO derruba um freecad.exe
        # TRAVADO (estado ininterruptivel) nem processos-filho -> ficava pendurado
        # segurando a porta 9875 (zumbis - ver memoria freecad-zumbis-wmi-kill). Agora
        # mata a ARVORE de forma forcada em qualquer saida.
        _matar_processo_freecad(proc)
        try:
            os.unlink(boot.name)
        except OSError:
            pass
    spec.setdefault("estrutura", {})["executivo"] = res
    return res


def _matar_processo_freecad(proc):
    """Encerra o freecad.exe do executivo e seus filhos, com escalonamento: kill()
    -> taskkill /F /T -> (Windows) WMI Terminate (unico que derruba freecad.exe
    travado em estado ininterruptivel). Best-effort, nunca levanta."""
    import subprocess, sys, time
    if proc.poll() is not None:
        return
    try:
        proc.kill()
    except Exception:
        pass
    time.sleep(1.0)
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        pid = proc.pid
        try:                                    # arvore inteira (freecad + filhos)
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        except Exception:
            pass
        time.sleep(1.0)
        if proc.poll() is None:                 # travado: WMI Terminate (NtTerminateProcess)
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "$p=Get-CimInstance Win32_Process -Filter \"ProcessId=%d\";"
                     "if($p){Invoke-CimMethod -InputObject $p -MethodName Terminate|Out-Null}" % pid],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            except Exception:
                pass


def _fmt_quadro(spec):
    """Quadro de utilizacoes/estados gravado pelo calcular() -> linhas de texto."""
    est = spec.get("estrutura", {})
    L = []
    res_u = est.get("resultados", {}) or {}
    for nome, u in res_u.items():
        if u is None:
            continue
        tag = "OK" if isinstance(u, (int, float)) and u <= 1.0 else "NAO ATENDE"
        val = f"{u:.2f}" if isinstance(u, (int, float)) else str(u)
        L.append(f"    {nome:<24} u={val:>6}  {tag}")
    for nome, flag in (est.get("estados", {}) or {}).items():
        L.append(f"    {nome:<24}         {flag}")
    return L


def relatorio_consolidado(spec, res, modelo=None, executivo=None, out_dir=None):
    """Relatorio unico: VEREDITO + gates (faltando/a_confirmar/avisos) + quadro de
    verificacoes + escopo + estagios (memorial/3D/executivo) + carimbo ART. Se
    out_dir, grava RELATORIO-CONSOLIDADO.txt. Retorna o texto."""
    import projeto_spec as PS
    import escopo as ESC
    try:
        import framework as FW
        carimbo = FW.carimbo_versao()
    except Exception:
        carimbo = "framework galpao_fw"
    g = spec.get("geometria", {})
    val = PS.validar(spec)
    # veredito GLOBAL: agrega TODOS os gates que rodaram (res["atende_global"]),
    # nao so o portico (res["atende"]). Fallback p/ o do portico se ausente.
    if isinstance(res, dict) and "atende_global" in res:
        atende = bool(res["atende_global"])
    else:
        atende = bool(res.get("atende")) if isinstance(res, dict) else False
    falhas = res.get("falhas_verificacao", []) if isinstance(res, dict) else []
    L = ["=" * 70,
         f"RELATORIO CONSOLIDADO - {spec.get('slug', '?')} "
         f"(GALPAO {g.get('comprimento', '?')}x{g.get('span', '?')} m)",
         carimbo, "=" * 70, "",
         f"VEREDITO DO DIMENSIONAMENTO: {'ATENDE' if atende else 'NAO ATENDE'}"]
    if falhas:
        L.append(f"  ELEMENTOS QUE NAO ATENDEM (util > 1,0) - REVER: "
                 + "; ".join(f"{n}={u:.2f}" for n, u in falhas))
        # acoes de reforco que o proprio calculo ja indica (o veredito segue
        # NAO ATENDE ate o engenheiro adotar o reforco): torna o "reforco exigido"
        # acionavel em vez de so apontar a falha.
        acoes = []
        zp = res.get("zona_painel") if isinstance(res, dict) else None
        if isinstance(zp, dict) and zp.get("precisa_reforco"):
            td = zp.get("t_doubler_mm")
            acoes.append(f"Zona de painel: doubler t={td:.0f} mm (2 lados) OU joelho "
                         f"misulado (tipo_portico=alma_variavel)"
                         if td else "Zona de painel: adotar doubler/misula no joelho")
        if isinstance(zp, dict) and zp.get("precisa_enrijecedor"):
            a = zp.get("enrij_a_sug_mm")
            acoes.append(f"Alma do joelho: enrijecedores a cada {a:.0f} mm"
                         if a else "Alma do joelho: enrijecedores transversais")
        cal = res.get("calha") if isinstance(res, dict) else None
        if isinstance(cal, dict) and not cal.get("ok", True):
            acoes.append("Calha: ampliar secao/condutores ou rever a intensidade "
                         "pluviometrica (chuva_I_mm_h) - secao default nao fechou")
        if acoes:
            L.append("  ACOES DE REFORCO INDICADAS PELO CALCULO:")
            L += [f"    -> {a}" for a in acoes]
    L.append("")
    # gates de entrada
    if val["faltando"]:
        L.append(f"PENDENTE (bloqueia) - {len(val['faltando'])}:")
        L += [f"    - {p} : {d}" for p, d in val["faltando"]]
    else:
        L.append("Entradas: COMPLETAS (todos os gates decididos).")
    if val["a_confirmar"]:
        L.append(f"A CONFIRMAR (valor provisorio) - {len(val['a_confirmar'])}:")
        L += [f"    - {p}" for p in val["a_confirmar"]]
    if val["avisos"]:
        L.append(f"AVISOS NORMATIVOS (auditoria/ART) - {len(val['avisos'])}:")
        L += [f"    - {p}: {d}" for p, d in val["avisos"]]
    # quadro de verificacoes
    L += ["", "QUADRO DE VERIFICACOES:"]
    q = _fmt_quadro(spec)
    L += q if q else ["    (sem quadro - calcular() nao populou resultados)"]
    # estagios (o que foi de fato gerado)
    L += ["", "ENTREGAVEIS GERADOS:"]
    mem = (spec.get("estrutura", {}) or {}).get("memorial_pdf")
    L.append(f"    Memoriais/PDF : {mem or out_dir or '(ver out_dir)'}")
    if isinstance(modelo, dict):
        rm = modelo.get("result") if "result" in modelo else modelo
        if isinstance(rm, dict) and rm.get("elementos") is not None:
            L.append(f"    Modelo 3D     : {rm.get('elementos')} objetos, "
                     f"{rm.get('interferencias', '?')} interf., "
                     f"{rm.get('massa_aco_kg', '?')} kg de aco -> {rm.get('fcstd')}")
        else:
            L.append(f"    Modelo 3D     : NAO GERADO ({modelo.get('erro', modelo)})")
    else:
        L.append("    Modelo 3D     : NAO SOLICITADO (com_3d=False)")
    if isinstance(executivo, dict):
        if executivo.get("ok"):
            L.append(f"    Pranchas 2D   : {len(executivo.get('pranchas', []))} pranchas")
        else:
            L.append(f"    Pranchas 2D   : NAO GERADO ({executivo.get('erro', executivo)})")
    else:
        L.append("    Pranchas 2D   : NAO SOLICITADO (com_executivo=False)")
    # escopo + carimbo ART
    L += ["", ESC.relatorio_escopo(spec, res, carimbo)]
    txt = "\n".join(str(x) for x in L)
    if out_dir:
        import os
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(str(out_dir), "RELATORIO-CONSOLIDADO.txt"),
                  "w", encoding="utf-8") as f:
            f.write(txt)
    return txt


def rodar_tudo(spec, out_dir=None, doc_name=None, com_3d=True, com_executivo=True,
               gerar_pdf=True, gerar_dossie=True, host="http://localhost:9875",
               timeout_3d=180, timeout_exec=1200, verbose=True):
    """ENTRADA UNICA: spec -> calculo + memorial PDF + modelo 3D + pranchas 2D +
    RELATORIO-CONSOLIDADO. Portavel (out_dir default = projects/<slug>/saida).
    Cada estagio degrada com gracia: se o FreeCAD (MCP/exe) nao estiver
    disponivel, o 3D/executivo ficam 'NAO GERADO' e o calculo/relatorio seguem.
    Retorna {res, modelo, executivo, relatorio, out_dir, atende}."""
    import os
    PS_ok = True
    try:
        import projeto_spec as PS
        PS.exigir_completo(spec)
    except Exception as ex:
        PS_ok = False
        if verbose:
            print(f"[rodar_tudo] spec incompleto: {ex}")
        raise
    slug = spec.get("slug") or "galpao"
    if out_dir is None:
        out_dir = str(FW.dir_projetos() / slug / "saida")
    os.makedirs(out_dir, exist_ok=True)
    doc_name = doc_name or slug

    def _log(m):
        if verbose:
            print(m)

    # 1) calculo (Gates 5-11) + memoriais
    _log(f"[1/4] Calculo -> {out_dir}")
    res = calcular(spec, out_dir)
    _log(f"      atende={res.get('atende')}")

    # 2) memorial PDF unico
    if gerar_pdf:
        try:
            import relatorio_calculo as RC
            g = spec.get("geometria", {})
            pdf = RC.gerar_pdf(out_dir, titulo="GALPAO %sx%s m"
                               % (g.get("comprimento", "?"), g.get("span", "?")),
                               spec=spec)
            spec.setdefault("estrutura", {})["memorial_pdf"] = pdf
            _log(f"[2/4] Memorial PDF -> {pdf}")
        except Exception as ex:
            _log(f"[2/4] Memorial PDF: FALHOU ({ex})")

    # 3) modelo 3D (FreeCAD via MCP) - opcional/gracioso
    modelo = None
    if com_3d:
        try:
            modelo = montar_modelo(spec, out_dir, doc_name,
                                   mf_stride=res.get("mf_stride"),
                                   n_tirante_parede=res.get("n_tirante_parede"),
                                   n_terca=res.get("n_terca"),
                                   host=host, timeout=timeout_3d)
            rm = modelo.get("result") if isinstance(modelo, dict) else None
            _log(f"[3/4] Modelo 3D -> {rm.get('elementos') if rm else modelo} objetos")
        except Exception as ex:
            modelo = {"erro": f"3D indisponivel ({ex})"}
            _log(f"[3/4] Modelo 3D: NAO GERADO ({ex})")

    # 4) pranchas executivas 2D - opcional/gracioso (precisa do .FCStd do passo 3)
    executivo = None
    if com_executivo:
        fcstd = None
        rm = modelo.get("result") if isinstance(modelo, dict) else None
        if isinstance(rm, dict):
            fcstd = rm.get("fcstd")
        fcstd = fcstd or f"{out_dir}/freecad/{doc_name}.FCStd".replace("\\", "/")
        if os.path.exists(fcstd):
            try:
                executivo = rodar_executivo(spec, out_dir, fcstd, timeout=timeout_exec)
                _log(f"[4/4] Pranchas -> {len(executivo.get('pranchas', [])) if isinstance(executivo, dict) else executivo}")
            except Exception as ex:
                executivo = {"erro": f"executivo falhou ({ex})"}
                _log(f"[4/4] Pranchas: NAO GERADO ({ex})")
        else:
            executivo = {"erro": f"FCStd ausente ({fcstd}) - rode o 3D antes"}
            _log(f"[4/4] Pranchas: NAO GERADO (sem FCStd)")

    rel = relatorio_consolidado(spec, res, modelo, executivo, out_dir)
    _log(f"\nRelatorio consolidado -> {out_dir}/RELATORIO-CONSOLIDADO.txt")

    # 5) DOSSIE unico (capa + relatorio + memorial + pranchas num PDF). Best-effort.
    dossie = None
    if gerar_dossie:
        try:
            import dossie as _dossie
            dossie = _dossie.gerar_dossie(out_dir, spec, relatorio=rel)
            spec.setdefault("estrutura", {})["dossie_pdf"] = dossie["path"]
            _log(f"[5] Dossie -> {dossie['path']} ({dossie['n_paginas']} paginas"
                 + (f", faltando: {dossie['faltando']}" if dossie['faltando'] else "") + ")")
        except Exception as ex:
            dossie = {"erro": str(ex)}
            _log(f"[5] Dossie: FALHOU ({ex})")

    # "atende" e o veredito GLOBAL (todos os gates), o mesmo que o RELATORIO
    # imprime. Era res["atende"] - so o portico: `rodar_tudo` devolvia True num
    # projeto cujo relatorio dizia NAO ATENDE, e quem consome a API por script
    # (CI, outro programa) aprovaria o projeto sem ver a falha. O veredito do
    # portico continua acessivel em res["atende"] e agora tambem aqui, nomeado.
    _global = (res.get("atende_global") if isinstance(res, dict)
               and "atende_global" in res else res.get("atende"))
    return {"res": res, "modelo": modelo, "executivo": executivo, "dossie": dossie,
            "relatorio": rel, "out_dir": out_dir, "atende": bool(_global),
            "atende_portico": bool(res.get("atende")) if isinstance(res, dict) else False,
            "falhas": (res.get("falhas_verificacao") or []) if isinstance(res, dict) else []}
