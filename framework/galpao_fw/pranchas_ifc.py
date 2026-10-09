# ============================================================================
# pranchas_ifc.py - PRANCHAS DO MODELO IFC NUM PASSO SO (plano de 2026-10-08,
# Fases 3 e 4). Do IFC que o motor grava saem, sem editar nada a mao:
#   1. os desenhos e as folhas A1 pelo Blender + Bonsai sem janela
#      (docs/fase3-bonsai/scripts/pranchas_bonsai.py);
#   2. a prancha DXF editavel (dxf_prancha), com a lista de material contada
#      no proprio IFC;
#   3. o DWG pelo ODA File Converter;
#   4. o PDF de cada folha pelo Inkscape.
#
# Blender, ODA e Inkscape sao programas de fora: cada um e' procurado na
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
MARCA_RELATORIO = "RELATORIO_JSON "
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


def gerar(ifc, pasta, titulo, revisao, carimbo=None, timeout_bonsai=3600,
          timeout_conversao=600, ambiente=None, rodar=_rodar):
    """Gera desenhos, folhas, DXF, DWG e PDF do `ifc` em `pasta`.

    Devolve um dicionario com `gerado` (ha desenho e DXF), o caminho de cada
    entrega feita e, em `nao_gerado`, o motivo de cada entrega que faltou.
    `titulo` e `revisao` vao ao carimbo das folhas do Bonsai; `carimbo` sao os
    campos do carimbo do DXF (PROJETO, CLIENTE, RESPONSAVEL, DATA) - campo nao
    declarado sai em branco."""
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

    codigo, saida = rodar([blender, "-b", "--python", SCRIPT_BONSAI, "--", copia,
                           "titulo=%s" % titulo, "revisao=%s" % revisao], timeout_bonsai)
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
    res["dxf_resumo"] = dxf_prancha.gerar_de_pasta(desenhos, dxf, campos, ifc=ifc)
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
    res["segundos"] = round(time.time() - t0, 1)
    return res


def resumo_pt(res):
    """Uma linha por entrega, para o registro do pipeline."""
    linhas = []
    if res["gerado"]:
        linhas.append("desenhos: %d; DXF: %s (%d folhas)" % (
            len(res["desenhos"]), res["dxf"], len(res["dxf_resumo"]["folhas"])
            + (1 if "lista" in res["dxf_resumo"] else 0)))
    for chave in ("dwg", "pdf"):
        if chave in res:
            linhas.append("%s: %s" % (chave.upper(), res[chave] if chave == "dwg"
                                      else "%d folhas" % len(res[chave])))
    for chave in sorted(res["nao_gerado"]):
        linhas.append("%s: NAO GERADO (%s)" % (chave, res["nao_gerado"][chave]))
    if "passos_com_erro" in res and res["passos_com_erro"]:
        linhas.append("INCOMPLETO - passos do Bonsai com erro: %s"
                      % ", ".join(res["passos_com_erro"]))
    for aviso in res["avisos"]:
        linhas.append("aviso do Bonsai: %s" % aviso.strip().splitlines()[-1])
    return linhas
