# ============================================================================
# caderno_casa_edificio.py - O QUE ESTE MODULO FAZ / MONTA (G94)
# CADERNO EXECUTIVO em PDF para a casa residencial e para o edificio
# multipavimento: capa + indice + uma pagina por folha do indice de pranchas
# (pacote_legal.indice_de_pranchas). Como as folhas de casa e predio sao SVG
# puro, a rota e' SVG -> PNG -> pagina (ponte fitz pixmap, a mesma de CI; o
# renderizador do repo continua sendo o Edge headless, regra 3 - sem
# cairosvg/svglib).
#
# REUSO, nao reescrita (G94):
#   - caderno_turnkey._add_pagina_imagem (PNG -> pagina A3 paisagem com titulo);
#   - dossie._add_paginas_texto (paginas A4 de texto: capa, indice, declaracao).
# A capa/indice daqui sao construidas por _linhas_capa_caderno /
# _linhas_indice_caderno PROPRIAS: caderno_turnkey._linhas_capa espera o R do
# turnkey do galpao (geometria/executadas), que os resultados de casa/edificio
# nao tem - fabricar um R seria dado inventado.
#
# DUAS CAMADAS: `montar_caderno_svg` e' PURA (so fitz + os dois helpers
# reusados + stdlib; testavel em CI); `emitir_caderno_casa` e
# `emitir_caderno_edificio` sao os hooks do project_loop (escrevem
# manifest["deliverables"]["caderno"], kind "executive-dossier", o mesmo kind
# que galpao_adapter.py:370 usa).
#
# REGRA DO PORTAO (G94): n_pranchas + n_declaradas == len(indice). Folha
# prometida sem arquivo E sem motivo vira `faltando` com o codigo nomeado e
# OK=False (o gate adotado x necessario: detalhamento que evapora em silencio
# reprova o caderno em vez de sair menor que o indice).
# ============================================================================
"""Caderno executivo em PDF para casa e edificio: SVG -> PNG -> pagina + as
folhas declaradas ausentes como paginas de declaracao. Camada pura testavel
em CI; hooks do project_loop para as duas tipologias."""

from __future__ import annotations

import datetime
import os
import tempfile


def svg_para_png(svg_path, png_path, dpi=110):
    """Converte um SVG em PNG via pixmap do PyMuPDF (fitz 1.27.2.3, CI).

    Rota provada em 2026-09-10: fitz.open(svg).load_page(0).get_pixmap(dpi).
    O doc.save() direto sobre um documento SVG FALHA - sempre passar pelo
    pixmap. Retorna True no sucesso, False quando o SVG falta ou nao rende
    (best-effort: quem chama decide entre prancha e declaracao).
    """
    try:
        import fitz

        if not svg_path or not os.path.exists(svg_path):
            return False
        doc = fitz.open(svg_path)
        try:
            pix = doc.load_page(0).get_pixmap(dpi=int(dpi))
            pix.save(png_path)
        finally:
            doc.close()
        return os.path.exists(png_path)
    except Exception:
        return False


def _linhas_capa_caderno(titulo, projeto, n_indice, veredito=None):
    """Texto monoespacado da CAPA do caderno de casa/edificio.

    Nunca inventa veredito: a linha de veredito so entra quando `veredito`
    e' passado explicitamente.
    """
    L = ["", "=" * 68, "",
         "        %s" % titulo,
         "",
         "        %s" % projeto,
         "", "=" * 68, "",
         "  Projeto:      %s" % projeto,
         "  Emissao:      %s" % datetime.date.today().strftime("%d/%m/%Y"),
         "  Pranchas no indice: %d" % int(n_indice)]
    if veredito is not None:
        L.append("  Veredito:     %s" % veredito)
    L += ["", "-" * 68,
          "  Material CONCEITUAL, gerado automaticamente. NAO substitui o",
          "  projeto assinado: os calculos e as pranchas devem ser REVISADOS",
          "  e ASSINADOS por engenheiro habilitado, com ART/RRT no CREA/CAU",
          "  (Lei 5194/1966).",
          "-" * 68, ""]
    return L


def _linhas_indice_caderno(folhas):
    """Texto do INDICE DE PRANCHAS do caderno (codigo - titulo, por folha)."""
    L = ["", "=" * 68, "  INDICE DE PRANCHAS", "=" * 68, ""]
    for i, f in enumerate(folhas, start=1):
        L.append("    %02d.  %s - %s (%s)" % (
            i, f.get("codigo", "?"), f.get("titulo", "?"),
            f.get("disciplina", "?")))
    if not folhas:
        L.append("  (nenhuma prancha)")
    L.append("")
    return L


def _linhas_declaracao(folha):
    """Texto da pagina de DECLARACAO de folha ausente: o dado que falta, com
    nome (o motivo entra verbatim - nunca "nao disponivel" sozinho)."""
    return ["", "=" * 68,
            "  DECLARACAO DE PRANCHA NAO EMITIDA",
            "=" * 68, "",
            "  Codigo:      %s" % folha.get("codigo", "?"),
            "  Titulo:      %s" % folha.get("titulo", "?"),
            "  Disciplina:  %s" % folha.get("disciplina", "?"),
            "",
            "  Esta prancha do indice nao foi emitida nesta rodada.",
            "  Motivo:",
            "  %s" % (folha.get("motivo") or "(motivo nao informado)"),
            ""]


def montar_caderno_svg(folhas, out_pdf, titulo, projeto, veredito=None):
    """PURO (so fitz + helpers reusados + stdlib): monta o caderno a partir
    de folhas SVG JA emitidas.

    `folhas`: lista de {codigo, titulo, disciplina, svg|None, motivo|None}.
    Por folha: svg existente -> pagina de prancha com carimbo
    (titulo=codigo+titulo, subtitulo=disciplina | projeto); sem svg mas com
    motivo -> pagina de declaracao com codigo, titulo e o motivo verbatim;
    sem svg E sem motivo -> entrada em `faltando` (codigo nomeado, OK=False).

    Retorna {path, n_paginas, n_pranchas, n_declaradas, n_indice, faltando,
    OK}. `veredito` so aparece na capa quando passado explicitamente.
    """
    import fitz

    from caderno_turnkey import _add_pagina_imagem
    from dossie import _add_paginas_texto

    folhas = list(folhas or [])
    faltando = []
    n_pranchas = 0
    n_declaradas = 0
    doc = fitz.open()
    _add_paginas_texto(doc, _linhas_capa_caderno(titulo, projeto,
                                                len(folhas), veredito))
    _add_paginas_texto(doc, _linhas_indice_caderno(folhas))
    with tempfile.TemporaryDirectory(prefix="caderno_svg_") as tmp:
        for i, folha in enumerate(folhas):
            codigo = folha.get("codigo", "?")
            svg = folha.get("svg")
            motivo = folha.get("motivo")
            if svg and os.path.exists(svg):
                png = os.path.join(tmp, "folha_%03d.png" % i)
                if svg_para_png(svg, png):
                    ok = _add_pagina_imagem(
                        doc, png,
                        "%s - %s" % (codigo, folha.get("titulo", "?")),
                        "%s | %s" % (folha.get("disciplina", "?"), projeto))
                    if ok:
                        n_pranchas += 1
                        continue
                if motivo:
                    _add_paginas_texto(doc, _linhas_declaracao(folha))
                    n_declaradas += 1
                else:
                    faltando.append(codigo)
            elif motivo:
                _add_paginas_texto(doc, _linhas_declaracao(folha))
                n_declaradas += 1
            else:
                faltando.append(codigo)
    n_pag = doc.page_count
    doc.save(out_pdf, garbage=3, deflate=True)
    doc.close()
    return {"path": out_pdf, "n_paginas": n_pag, "n_pranchas": n_pranchas,
            "n_declaradas": n_declaradas, "n_indice": len(folhas),
            "faltando": faltando, "OK": not faltando}


def _erro_entregavel(exc):
    return "%s: %s" % (type(exc).__name__, exc)


def _emitir_caderno(manifest, run_dir, normalized, options, result, *,
                    tipologia):
    """Nucleo comum dos dois hooks: indice independente -> folhas -> caderno.

    O indice vem de pacote_legal.indice_de_pranchas(disciplinas_pacote(...)),
    a MESMA fonte do pacote legal (anti-tautologia: nunca do proprio
    caderno). Arquivos emitidos sao casados por BASENAME contra os artifacts
    de drawings do manifesto; pulados viram declaracao com o motivo verbatim;
    prometido sem arquivo nem motivo vira faltando (OK=False).
    Degrada com graca: drawings ausente/nao pedido -> caderno not_available
    com o detalhe nomeado, nunca derruba a rodada.
    """
    from pathlib import Path

    from project_loop import _add_artifact

    if tipologia == "casa":
        import gestao_casa as gg
        import pacote_legal as pl

        nome_pdf = "CADERNO-EXECUTIVO-CASA.pdf"
        titulo = "CADERNO EXECUTIVO - CASA RESIDENCIAL"
        projeto = ((normalized or {}).get("slug")
                   if isinstance(normalized, dict) else None) \
            or "casa-residencial"
        indice = pl.indice_de_pranchas(gg.disciplinas_pacote(result))
    else:
        import gestao_edificio as gg
        import pacote_legal as pl

        nome_pdf = "CADERNO-EXECUTIVO-EDIFICIO.pdf"
        titulo = "CADERNO EXECUTIVO - EDIFICIO MULTIPAVIMENTO"
        projeto = ((normalized or {}).get("slug")
                   if isinstance(normalized, dict) else None) \
            or "edificio-multipavimento"
        indice = pl.indice_de_pranchas(
            gg.disciplinas_pacote(result) + ["coordenacao"])

    desenhos = (manifest.get("deliverables") or {}).get("drawings") \
        if isinstance(manifest.get("deliverables"), dict) else None
    if not isinstance(desenhos, dict) \
            or desenhos.get("status") in (None, "not_requested") \
            or (desenhos.get("status") not in ("generated", "not_available")
                and not desenhos.get("artifacts")
                and desenhos.get("skipped") is None):
        manifest["deliverables"]["caderno"] = {
            "status": "not_available",
            "detail": ("drawings %s; caderno sem folhas para consolidar"
                       % (("status=%s" % desenhos.get("status"))
                          if isinstance(desenhos, dict)
                          else "ausente no manifesto")),
        }
        return
    if desenhos.get("status") == "failed":
        manifest["deliverables"]["caderno"] = {
            "status": "not_available",
            "detail": ("drawings failed (%s); caderno sem folhas para "
                       "consolidar" % desenhos.get("detail", "?")),
        }
        return

    if tipologia == "casa":
        import casa_residencial as adaptador

        mapa = dict(adaptador._PRANCHA_ARQUIVO_CASA)
    else:
        import edificio_adapter as adaptador

        mapa = dict(adaptador._PRANCHA_ARQUIVO)

    emitidos = {}
    for artefato in (desenhos.get("artifacts") or []):
        base = str(artefato).split("/")[-1]
        caminho = Path(run_dir) / "drawings" / base
        if caminho.is_file():
            emitidos.setdefault(base, str(caminho))
    pulados = desenhos.get("skipped")
    if isinstance(pulados, dict):                    # casa: {arquivo: motivo}
        motivos = {str(k).split("/")[-1]: v for k, v in pulados.items()}
    else:                                            # edificio: [{prancha, motivo}]
        motivos = {}
        for item in (pulados or []):
            if isinstance(item, dict) and item.get("prancha"):
                motivos[str(item["prancha"]).split("/")[-1]] = \
                    item.get("motivo")

    folhas = []
    for folha in indice:
        codigo = folha["codigo"]
        esperado = mapa.get(codigo)
        if esperado and esperado in emitidos:
            folhas.append({"codigo": codigo, "titulo": folha["titulo"],
                           "disciplina": folha["disciplina"],
                           "svg": emitidos[esperado], "motivo": None})
        elif esperado and esperado in motivos:
            folhas.append({"codigo": codigo, "titulo": folha["titulo"],
                           "disciplina": folha["disciplina"],
                           "svg": None, "motivo": motivos[esperado]})
        else:
            folhas.append({"codigo": codigo, "titulo": folha["titulo"],
                           "disciplina": folha["disciplina"],
                           "svg": None, "motivo": None})

    destino = Path(run_dir) / nome_pdf
    try:
        res = montar_caderno_svg(folhas, str(destino), titulo, projeto)
    except Exception as exc:                                # noqa: BLE001
        manifest["deliverables"]["caderno"] = {
            "status": "failed", "detail": _erro_entregavel(exc)}
        return
    _add_artifact(manifest, run_dir, destino, "executive-dossier")
    manifest["deliverables"]["caderno"] = {
        "status": "generated",
        "artifacts": [nome_pdf],
        "n_paginas": res["n_paginas"],
        "n_pranchas": res["n_pranchas"],
        "n_declaradas": res["n_declaradas"],
        "n_indice": res["n_indice"],
        "faltando": res["faltando"],
        "OK": res["OK"],
    }


def emitir_caderno_casa(manifest, run_dir, normalized, options, result):
    """Hook do caderno da casa (project_loop, extra, depois de drawings)."""
    _emitir_caderno(manifest, run_dir, normalized, options, result,
                    tipologia="casa")


def emitir_caderno_edificio(manifest, run_dir, normalized, options, result):
    """Hook do caderno do edificio (project_loop, extra, depois de drawings)."""
    _emitir_caderno(manifest, run_dir, normalized, options, result,
                    tipologia="edificio")
