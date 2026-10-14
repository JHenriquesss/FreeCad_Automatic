# ============================================================================
# pranchas_ifc.py - PRANCHAS DO MODELO IFC NUM PASSO SO (plano de 2026-10-08,
# Fases 3 e 4). Do IFC que o motor grava saem, sem editar nada a mao:
#   1. os desenhos e as folhas A1 pelo Blender + Bonsai sem janela
#      (docs/fase3-bonsai/scripts/pranchas_bonsai.py);
#   2. a prancha DXF editavel (dxf_prancha), com a lista de material contada
#      no proprio IFC;
#   3. o DWG pelo ODA File Converter;
#   4. o PDF de cada folha pelo Inkscape.
#   5. (pedido) o render de apresentacao do mesmo modelo
#      (docs/fase3-bonsai/scripts/render_apresentacao.py);
#   6. a conferencia do arquivo entregue (o DWG; sem ele, o DXF) pelo
#      CADCraft sem janela: outro programa abre o arquivo, audita e imprime
#      cada folha em PDF. O CADCraft so' LE: nao grava nada da entrega.
# A lista de material e' contada uma vez no IFC (dxf_prancha.lista_do_ifc) e
# vai, com os mesmos textos, a uma folha do DXF e a uma folha do Bonsai.
#
# Blender, ODA, Inkscape e CADCraft sao programas de fora: cada um e' procurado na
# maquina e, se nao estiver, o passo dele fica NAO GERADO com o motivo
# escrito - nada e' dado como entregue sem o arquivo existir. Sem o Blender
# nao ha desenho e nada mais sai.
#
# O Bonsai GRAVA no IFC que abre: o IFC do motor e' copiado para a pasta de
# trabalho e o original nao e' tocado. Pasta de trabalho de uma corrida
# anterior e' renomeada (arquivada), nunca apagada nem reaproveitada: desenho
# velho nao entra em prancha nova.
# ============================================================================
"""Pranchas (Bonsai), DXF, DWG e PDF a partir do IFC do motor."""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import time

import dxf_prancha

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT_BONSAI = os.path.normpath(os.path.join(
    HERE, "..", "..", "docs", "fase3-bonsai", "scripts", "pranchas_bonsai.py"))
SCRIPT_RENDER = os.path.normpath(os.path.join(
    HERE, "..", "..", "docs", "fase3-bonsai", "scripts", "render_apresentacao.py"))
MOTOR_DE_RENDER = "CYCLES"      # no EEVEE sem janela a sombra do sol nao sai (D219)
MARCA_RELATORIO = "RELATORIO_JSON "
NOME_LISTA = "LISTA-DE-MATERIAL"
# tabela da lista na folha do Bonsai (mm): passo da linha, altura do texto e
# a area util da folha A1 acima do carimbo (a mesma do script do Bonsai)
PASSO_LISTA_MM, TEXTO_LISTA_MM = 6.0, 2.5
AREA_LISTA_MM = (781.0, 475.0)
VERSAO_DWG = "ACAD2018"

# programa -> (variavel de ambiente, padroes de busca na maquina, nome no PATH)
PROGRAMAS = {
    "blender": ("BLENDER_EXE",
                (r"C:\Program Files\Blender Foundation\Blender*\blender.exe",), "blender"),
    "oda": ("ODA_EXE",
            (r"C:\Program Files\ODA\ODAFileConverter*\ODAFileConverter.exe",),
            "ODAFileConverter"),
    "inkscape": ("INKSCAPE_EXE",
                 (r"C:\Program Files\Inkscape\bin\inkscape.com",), "inkscape"),
    "cadcraft": ("CADCRAFT_CLI",
                 (os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "CADCraft",
                               "cadcraft-cli.exe"),), "cadcraft-cli"),
}


def localizar(nome, ambiente=None):
    """Caminho do programa, ou None. Ordem: variavel de ambiente (que, se
    declarada, tem de apontar para arquivo existente), pastas de instalacao
    (a de nome mais alto), PATH."""
    variavel, padroes, no_path = PROGRAMAS[nome]
    ambiente = os.environ if ambiente is None else ambiente
    if variavel in ambiente and ambiente[variavel]:
        if not os.path.isfile(ambiente[variavel]):
            raise FileNotFoundError("%s aponta para %s, que nao existe"
                                    % (variavel, ambiente[variavel]))
        return ambiente[variavel]
    achados = sorted(c for p in padroes for c in glob.glob(p))
    if achados:
        return achados[-1]
    return shutil.which(no_path)


def _rodar(comando, timeout):
    r = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def ler_relatorio(saida):
    """O relatorio que o script do Bonsai imprime na ultima linha marcada."""
    linhas = [ln for ln in saida.splitlines() if ln.startswith(MARCA_RELATORIO)]
    if not linhas:
        raise ValueError("o script do Bonsai nao imprimiu o relatorio; fim da saida: %s"
                         % saida[-400:])
    return json.loads(linhas[-1][len(MARCA_RELATORIO):])


def _xml(texto):
    return (texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def svg_da_lista(tabela, destino, area_mm=AREA_LISTA_MM):
    """Grava a tabela da lista de material como SVG em milimetros, para entrar
    numa folha do Bonsai como referencia. Tabela que nao cabe na area util
    reprova (nada e' cortado). Devolve (largura, altura) em mm."""
    passo, alt_txt = PASSO_LISTA_MM, TEXTO_LISTA_MM
    larguras = tabela["larguras_mm"]
    larg_tabela = float(sum(larguras))
    blocos = [tabela["cabecalho"]] + tabela["linhas"]
    n_linhas = len(blocos) + (1 if tabela["total"] is not None else 0) + len(tabela["notas"])
    # nota e' texto corrido: a largura dela conta (0,6 da altura por letra, adotado)
    larg = max([larg_tabela] + [3.0 + len(n) * alt_txt * 0.6 for n in tabela["notas"]])
    alt = (n_linhas + 1) * passo
    if larg > area_mm[0] or alt > area_mm[1]:
        raise ValueError("lista de material de %.0f x %.0f mm (%d linhas) nao cabe na area "
                         "util de %.0f x %.0f mm da folha" % (
                             larg, alt, len(tabela["linhas"]), area_mm[0], area_mm[1]))
    estilo = ('font-family="Arial, sans-serif" font-size="%s" fill="#000000" stroke="none"'
              % alt_txt)
    traco = 'stroke="#000000" stroke-width="0.25" fill="none"'
    partes = ['<svg xmlns="http://www.w3.org/2000/svg" width="%smm" height="%smm" '
              'viewBox="0 0 %s %s">' % (larg, alt, larg, alt)]

    def _linha(celulas, y):
        x = 0.0
        for largura, texto in zip(larguras, celulas):
            if texto:
                partes.append('<text x="%s" y="%s" %s>%s</text>'
                              % (x + 1.5, y - 1.6, estilo, _xml(texto)))
            x += largura

    y = passo
    _linha(tabela["cabecalho"], y)
    partes.append('<line x1="0" y1="%s" x2="%s" y2="%s" %s/>' % (y, larg_tabela, y, traco))
    for celulas in tabela["linhas"]:
        y += passo
        _linha(celulas, y)
    partes.append('<line x1="0" y1="%s" x2="%s" y2="%s" %s/>' % (y, larg_tabela, y, traco))
    if tabela["total"] is not None:
        y += passo
        _linha(tabela["total"], y)
    for nota in tabela["notas"]:
        y += passo
        partes.append('<text x="1.5" y="%s" %s>%s</text>' % (y - 1.6, estilo, _xml(nota)))
    partes.append("</svg>")
    with open(destino, "w", encoding="utf-8") as f:
        f.write("\n".join(partes) + "\n")
    return larg, alt


def _pasta_de_trabalho(pasta):
    """Pasta nova e vazia; a de uma corrida anterior e' arquivada ao lado."""
    arquivada = None
    if os.path.isdir(pasta) and os.listdir(pasta):
        arquivada = "%s.anterior-%s" % (pasta, time.strftime("%Y%m%d-%H%M%S"))
        k = 1
        while os.path.exists(arquivada):
            k += 1
            arquivada = "%s.anterior-%s-%d" % (pasta, time.strftime("%Y%m%d-%H%M%S"), k)
        os.rename(pasta, arquivada)
    os.makedirs(pasta, exist_ok=True)
    return arquivada


def _dwg(oda, dxf, pasta_dwg, timeout, rodar):
    os.makedirs(pasta_dwg, exist_ok=True)
    codigo, saida = rodar([oda, os.path.dirname(dxf), pasta_dwg, VERSAO_DWG, "DWG",
                           "0", "1", "*.dxf"], timeout)
    dwg = os.path.join(pasta_dwg, os.path.splitext(os.path.basename(dxf))[0] + ".dwg")
    if not os.path.isfile(dwg) or os.path.getsize(dwg) == 0:
        raise RuntimeError("o ODA terminou (codigo %s) sem gravar %s: %s"
                           % (codigo, dwg, saida[-300:]))
    return dwg


def _pdfs(inkscape, pasta_folhas, pasta_pdf, timeout, rodar):
    folhas = sorted(f for f in os.listdir(pasta_folhas) if f.lower().endswith(".svg"))
    if not folhas:
        raise RuntimeError("nenhuma folha .svg em %s" % pasta_folhas)
    os.makedirs(pasta_pdf, exist_ok=True)
    feitos = []
    for f in folhas:
        pdf = os.path.join(pasta_pdf, os.path.splitext(f)[0] + ".pdf")
        codigo, saida = rodar([inkscape, os.path.join(pasta_folhas, f),
                               "--export-type=pdf", "--export-filename=" + pdf], timeout)
        if not os.path.isfile(pdf) or os.path.getsize(pdf) == 0:
            raise RuntimeError("o Inkscape terminou (codigo %s) sem gravar %s: %s"
                               % (codigo, pdf, saida[-300:]))
        feitos.append(pdf)
    return feitos


def _render(blender, ifc, png, timeout, rodar):
    """Render de apresentacao; so se diz feito com a imagem gravada."""
    os.makedirs(os.path.dirname(png), exist_ok=True)
    codigo, saida = rodar([blender, "-b", "--python", SCRIPT_RENDER, "--", ifc, png,
                           MOTOR_DE_RENDER], timeout)
    rel = ler_relatorio(saida)
    if "erro" in rel:
        raise RuntimeError("o render falhou: %s" % rel["erro"].strip().splitlines()[-1])
    if not os.path.isfile(png) or os.path.getsize(png) == 0:
        raise RuntimeError("o Blender terminou (codigo %s) sem gravar %s" % (codigo, png))
    return rel


def _json_da_saida(saida):
    """O primeiro objeto JSON da saida do cadcraft-cli (uma ou varias linhas)."""
    inicio = saida.find("{")
    if inicio < 0:
        raise ValueError("sem JSON na saida: %s" % saida.strip()[-300:])
    return json.JSONDecoder().raw_decode(saida[inicio:])[0]


def _conferencia(cadcraft, arquivo, folhas, pasta_conf, timeout, rodar, dxf=None):
    """Abre `arquivo` (o DWG ou o DXF da entrega) no CADCraft sem janela: conta
    as entidades, audita e imprime cada folha esperada em PDF. Devolve o
    resultado com `divergencias` (lista de frases; vazia = conferido). Se o
    arquivo e' o DWG e o `dxf` de origem e' dado, as contagens dos dois tem de
    ser iguais."""
    os.makedirs(pasta_conf, exist_ok=True)
    conf = {"arquivo": arquivo, "divergencias": [], "pdf": []}

    def _info(caminho):
        codigo, saida = rodar([cadcraft, "info", caminho], timeout)
        if codigo != 0:
            raise RuntimeError("o CADCraft nao abriu %s (codigo %s): %s"
                               % (caminho, codigo, saida.strip()[-300:]))
        return _json_da_saida(saida)

    info = _info(arquivo)
    conf["entidades"] = info["counts"]
    faltam = [f for f in folhas if f not in info["layouts"]]
    sobram = [f for f in info["layouts"] if f not in folhas]
    if faltam:
        conf["divergencias"].append("folhas ausentes no arquivo: %s" % ", ".join(faltam))
    if sobram:
        conf["divergencias"].append("folhas a mais no arquivo: %s" % ", ".join(sobram))
    if dxf and os.path.abspath(dxf) != os.path.abspath(arquivo):
        do_dxf = _info(dxf)["counts"]
        if do_dxf != info["counts"]:
            conf["divergencias"].append("o DWG e o DXF nao tem as mesmas entidades: %r x %r"
                                        % (info["counts"], do_dxf))
    codigo, saida = rodar([cadcraft, "run", arquivo, "--cmd", "audit {}"], timeout)
    if codigo != 0:
        raise RuntimeError("a auditoria do CADCraft falhou (codigo %s): %s"
                           % (codigo, saida.strip()[-300:]))
    aud = _json_da_saida(saida)
    conf["auditoria_erros"] = aud["errors"]
    for item in aud["issues"]:
        conf["divergencias"].append("auditoria: %s (%s)" % (item["message"], item["location"]))
    for folha in folhas:
        if folha in faltam:
            continue
        pdf = os.path.join(pasta_conf, folha + ".pdf")
        codigo, saida = rodar([cadcraft, "run", arquivo, "--cmd", "plot " + json.dumps(
            {"path": pdf, "layout": folha, "plotArea": "layout"})], timeout)
        if codigo != 0 or not os.path.isfile(pdf) or os.path.getsize(pdf) == 0:
            conf["divergencias"].append("a folha %s nao imprimiu (codigo %s): %s"
                                        % (folha, codigo, saida.strip()[-200:]))
        else:
            conf["pdf"].append(pdf)
    return conf


def gerar(ifc, pasta, titulo, revisao, carimbo=None, timeout_bonsai=3600,
          timeout_conversao=600, ambiente=None, rodar=_rodar, render=False):
    """Gera desenhos, folhas, DXF, DWG e PDF do `ifc` em `pasta` e confere o
    arquivo entregue em outro programa (`conferencia`).

    Devolve um dicionario com `gerado` (ha desenho e DXF), o caminho de cada
    entrega feita e, em `nao_gerado`, o motivo de cada entrega que faltou.
    `titulo` e `revisao` vao ao carimbo das folhas do Bonsai; `carimbo` sao os
    campos do carimbo do DXF (PROJETO, CLIENTE, RESPONSAVEL, DATA) - campo nao
    declarado sai em branco. `render=True` grava tambem a imagem de
    apresentacao (minutos a mais)."""
    if not os.path.isfile(ifc):
        raise FileNotFoundError("IFC ausente: %s" % ifc)
    t0 = time.time()
    res = {"gerado": False, "pasta": pasta, "nao_gerado": {}, "avisos": []}
    blender = localizar("blender", ambiente)
    if not blender:
        res["nao_gerado"]["desenhos"] = ("Blender nao encontrado (declare BLENDER_EXE); "
                                         "sem ele nao ha desenho, DXF, DWG nem PDF")
        return res
    if not os.path.isfile(SCRIPT_BONSAI):
        res["nao_gerado"]["desenhos"] = "script do Bonsai ausente: %s" % SCRIPT_BONSAI
        return res

    res["pasta_anterior_arquivada"] = _pasta_de_trabalho(pasta)
    trabalho = os.path.join(pasta, "bonsai")
    os.makedirs(trabalho)
    copia = os.path.join(trabalho, os.path.basename(ifc))
    shutil.copyfile(ifc, copia)

    # a lista de material e' contada no IFC do motor ANTES de o Bonsai gravar
    # desenhos e folhas na copia; o mesmo resultado vai ao DXF mais abaixo
    lista = dxf_prancha.lista_do_ifc(ifc)
    os.makedirs(os.path.join(trabalho, "references"))
    svg_lista = os.path.join(trabalho, "references", NOME_LISTA + ".svg")
    svg_da_lista(dxf_prancha.tabela_da_lista(lista), svg_lista)

    codigo, saida = rodar([blender, "-b", "--python", SCRIPT_BONSAI, "--", copia,
                           "titulo=%s" % titulo, "revisao=%s" % revisao,
                           "lista=%s" % svg_lista], timeout_bonsai)
    with open(os.path.join(pasta, "bonsai-saida.log"), "w", encoding="utf-8") as f:
        f.write(saida)
    try:
        rel = ler_relatorio(saida)
    except ValueError as ex:
        res["nao_gerado"]["desenhos"] = "Blender terminou com codigo %s: %s" % (codigo, ex)
        return res
    res["relatorio_bonsai"] = rel
    res["avisos"] += list(rel["avisos"]) if "avisos" in rel else []
    res["passos_com_erro"] = [p[0] for p in rel["passos"] if p[1] != "ok"]
    desenhos = os.path.join(trabalho, "drawings")
    svgs = (sorted(f for f in os.listdir(desenhos) if f.lower().endswith(".svg"))
            if os.path.isdir(desenhos) else [])
    if not svgs:
        res["nao_gerado"]["desenhos"] = "o Bonsai nao gravou desenho em %s" % desenhos
        return res
    res["desenhos"] = [os.path.join(desenhos, f) for f in svgs]

    pasta_dxf = os.path.join(pasta, "dxf")
    os.makedirs(pasta_dxf)
    dxf = os.path.join(pasta_dxf, os.path.splitext(os.path.basename(ifc))[0] + ".dxf")
    campos = dict(carimbo or {})
    campos["REVISAO"] = revisao
    res["dxf_resumo"] = dxf_prancha.gerar_dxf(
        [dxf_prancha.ler_desenho(p) for p in res["desenhos"]], dxf, campos, lista=lista)
    for folha in res["dxf_resumo"]["folhas"]:
        for frase in folha["textos_alem_do_quadro"]:
            res["avisos"].append("%s: texto passa da janela da vista e sai cortado na folha "
                                 "do DXF: %r" % (folha["folha"], frase))
    res["lista"] = {"linhas": len(lista["linhas"]), "peso_total_kg": lista["peso_total_kg"],
                    "linhas_sem_peso": lista["linhas_sem_peso"]}
    if "folha_da_lista" in rel:
        res["lista"]["folha_bonsai"] = rel["folha_da_lista"]
    else:
        res["nao_gerado"]["lista_no_bonsai"] = ("o script do Bonsai nao informou a folha "
                                                "da lista de material")
    res["dxf"] = dxf
    res["gerado"] = True

    oda = localizar("oda", ambiente)
    if not oda:
        res["nao_gerado"]["dwg"] = "ODA File Converter nao encontrado (declare ODA_EXE)"
    else:
        try:
            res["dwg"] = _dwg(oda, dxf, os.path.join(pasta, "dwg"), timeout_conversao, rodar)
        except Exception as ex:
            res["nao_gerado"]["dwg"] = str(ex)

    inkscape = localizar("inkscape", ambiente)
    if not inkscape:
        res["nao_gerado"]["pdf"] = "Inkscape nao encontrado (declare INKSCAPE_EXE)"
    else:
        try:
            res["pdf"] = _pdfs(inkscape, os.path.join(trabalho, "sheets"),
                               os.path.join(pasta, "pdf"), timeout_conversao, rodar)
        except Exception as ex:
            res["nao_gerado"]["pdf"] = str(ex)
    cadcraft = localizar("cadcraft", ambiente)
    if not cadcraft:
        res["nao_gerado"]["conferencia"] = ("CADCraft nao encontrado (declare CADCRAFT_CLI): "
                                            "DXF e DWG nao foram abertos em outro programa")
    else:
        folhas = [f["folha"] for f in res["dxf_resumo"]["folhas"]]
        if "lista" in res["dxf_resumo"]:
            folhas.append(res["dxf_resumo"]["lista"]["folha"])
        try:
            res["conferencia"] = _conferencia(
                cadcraft, res["dwg"] if "dwg" in res else dxf, folhas,
                os.path.join(pasta, "conferencia"), timeout_conversao, rodar, dxf=dxf)
        except Exception as ex:
            res["nao_gerado"]["conferencia"] = str(ex)
    if render:
        try:
            png = os.path.join(pasta, "render", "apresentacao.png")
            rel_render = _render(blender, copia, png, timeout_bonsai, rodar)
            res["render"] = png
            res["render_segundos"] = rel_render["tempo_s"] if "tempo_s" in rel_render else None
        except Exception as ex:
            res["nao_gerado"]["render"] = str(ex)
    res["segundos"] = round(time.time() - t0, 1)
    return res


def resumo_pt(res):
    """Uma linha por entrega, para o registro do pipeline."""
    linhas = []
    if res["gerado"]:
        linhas.append("desenhos: %d; DXF: %s (%d folhas)" % (
            len(res["desenhos"]), res["dxf"], len(res["dxf_resumo"]["folhas"])
            + (1 if "lista" in res["dxf_resumo"] else 0)))
    for chave in ("dwg", "pdf", "render"):
        if chave in res:
            linhas.append("%s: %s" % (chave.upper(), "%d folhas" % len(res[chave])
                                      if chave == "pdf" else res[chave]))
    if "conferencia" in res:
        conf = res["conferencia"]
        linhas.append("conferencia no CADCraft (%s): %d folhas impressas, %s" % (
            os.path.basename(conf["arquivo"]), len(conf["pdf"]),
            "sem divergencia" if not conf["divergencias"]
            else "%d DIVERGENCIA(S)" % len(conf["divergencias"])))
        for frase in conf["divergencias"]:
            linhas.append("conferencia: " + frase)
    for chave in sorted(res["nao_gerado"]):
        linhas.append("%s: NAO GERADO (%s)" % (chave, res["nao_gerado"][chave]))
    if "passos_com_erro" in res and res["passos_com_erro"]:
        linhas.append("INCOMPLETO - passos do Bonsai com erro: %s"
                      % ", ".join(res["passos_com_erro"]))
    for aviso in res["avisos"]:
        linhas.append("aviso do Bonsai: %s" % aviso.strip().splitlines()[-1])
    return linhas
