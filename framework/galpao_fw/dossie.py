# ============================================================================
# dossie.py - DOSSIE EXECUTIVO UNICO (PDF)
# Junta num UNICO PDF entregavel, na ordem de um caderno de projeto:
#   1. CAPA (identificacao + carimbo de responsabilidade/ART)
#   2. RELATORIO CONSOLIDADO (veredito + gates + escopo)
#   3. MEMORIAL DE CALCULO (o PDF do relatorio_calculo, se existir)
#   4. PRANCHAS EXECUTIVAS (todas as PE*.pdf, em ordem)
# Usa PyMuPDF (fitz) para criar as paginas de texto e MESCLAR os PDFs existentes
# (as pranchas vem do FreeCAD; o memorial do reportlab). Nada e regerado aqui.
# ============================================================================
"""Dossie executivo unico: capa + relatorio + memorial + pranchas num PDF so."""

from __future__ import annotations

import glob
import os


def _linhas_capa(spec, carimbo="framework galpao_fw"):
    import datetime
    g = spec.get("geometria", {})
    spans = g.get("spans") if isinstance(g.get("spans"), (list, tuple)) else None
    if spans and len(spans) > 1:
        dim = "Galpao %sx%.0f m (%d vaos de %g m)" % (
            g.get("comprimento", "?"), sum(spans), len(spans), spans[0])
    else:
        dim = "Galpao %sx%s m" % (g.get("comprimento", "?"), g.get("span", "?"))
    L = ["", "=" * 68, "",
         "        PROJETO EXECUTIVO ESTRUTURAL - GALPAO EM ACO",
         "",
         "        %s" % spec.get("descricao", spec.get("slug", "galpao")),
         "        %s" % dim,
         "", "=" * 68, "",
         "  Projeto:      %s" % spec.get("slug", "galpao"),
         "  Emissao:      %s" % datetime.date.today().strftime("%d/%m/%Y"),
         "  Ferramenta:   %s" % carimbo,
         "  Normas:       NBR 8800 / 6118 / 6122 / 6123 / 14762 / 14323",
         "",
         "-" * 68,
         "  RESPONSABILIDADE TECNICA",
         "-" * 68,
         "  Material CONCEITUAL, gerado automaticamente. NAO substitui o",
         "  projeto assinado: os calculos, o modelo 3D e as pranchas devem",
         "  ser REVISADOS e ASSINADOS por engenheiro habilitado, com ART/RRT",
         "  no CREA/CAU (Lei 5194/1966). Dados de sitio (solo/sondagem) e de",
         "  fabricante sao de responsabilidade de quem os informou.",
         "-" * 68,
         "",
         "  SUMARIO",
         "    1. Relatorio consolidado (veredito, gates, escopo)",
         "    2. Memorial de calculo",
         "    3. Pranchas executivas (PE01 ...)",
         ]
    return L


def _add_paginas_texto(doc, linhas, fonte=9.0, margem=42.0):
    """Adiciona paginas A4 com texto MONOESPACADO (preserva quadros/carimbos ASCII).
    Pagina automaticamente. Usa PyMuPDF (fitz)."""
    import fitz
    W, H = 595.0, 842.0                       # A4 retrato (pt)
    lh = fonte * 1.32
    page = None
    y = 0.0
    for ln in linhas:
        if page is None or y > H - margem:
            page = doc.new_page(width=W, height=H)
            y = margem
        # corta linhas muito longas (seguranca; o relatorio usa ~70 colunas)
        page.insert_text((margem, y), str(ln)[:110], fontname="courier",
                         fontsize=fonte)
        y += lh
    return doc


def _memorial_pdf(out_dir, spec):
    """Path do memorial de calculo (PDF). Preferencia: o gravado no spec; senao
    procura no out_dir (memorial*.pdf / MEMORIAL*.pdf)."""
    mp = (spec.get("estrutura", {}) or {}).get("memorial_pdf")
    if mp and os.path.exists(mp):
        return mp
    for pat in ("memorial*.pdf", "MEMORIAL*.pdf", "*memorial*.pdf"):
        achados = sorted(glob.glob(os.path.join(out_dir, pat)))
        if achados:
            return achados[0]
    return None


def _pranchas_pdf(out_dir):
    """Lista ordenada das pranchas PE*.pdf (zero-padded -> ordem alfabetica = PE01..PE15)."""
    prdir = os.path.join(out_dir, "pranchas")
    return sorted(glob.glob(os.path.join(prdir, "PE*.pdf")))


def gerar_dossie(out_dir, spec, dossie_path=None, relatorio=None,
                 carimbo="framework galpao_fw"):
    """Monta o DOSSIE unico (capa + relatorio + memorial + pranchas) em um PDF.
    `relatorio` (texto do RELATORIO-CONSOLIDADO); se None, le o .txt do out_dir.
    Retorna {path, n_paginas, memorial, n_pranchas, faltando}."""
    import fitz
    slug = spec.get("slug", "galpao")
    dossie_path = dossie_path or os.path.join(out_dir, "DOSSIE-%s.pdf" % slug)

    if relatorio is None:
        rp = os.path.join(out_dir, "RELATORIO-CONSOLIDADO.txt")
        relatorio = open(rp, encoding="utf-8").read() if os.path.exists(rp) else \
            "(relatorio consolidado ausente)"

    faltando = []
    doc = fitz.open()                          # PDF novo, vazio
    # 1) CAPA + 2) RELATORIO CONSOLIDADO (texto monoespacado)
    _add_paginas_texto(doc, _linhas_capa(spec, carimbo))
    _add_paginas_texto(doc, ["", "=" * 70, "1-2. RELATORIO CONSOLIDADO", "=" * 70, ""]
                       + relatorio.splitlines())
    # 3) MEMORIAL DE CALCULO
    mem = _memorial_pdf(out_dir, spec)
    if mem:
        try:
            with fitz.open(mem) as m:
                doc.insert_pdf(m)
        except Exception as ex:
            faltando.append("memorial (%s)" % ex)
    else:
        faltando.append("memorial (nao encontrado)")
    # 4) PRANCHAS EXECUTIVAS
    pranchas = _pranchas_pdf(out_dir)
    for pp in pranchas:
        try:
            with fitz.open(pp) as pr:
                doc.insert_pdf(pr)
        except Exception as ex:
            faltando.append("%s (%s)" % (os.path.basename(pp), ex))
    if not pranchas:
        faltando.append("pranchas (nenhuma PE*.pdf)")

    n_pag = doc.page_count
    doc.save(dossie_path, garbage=3, deflate=True)
    doc.close()
    return {"path": dossie_path, "n_paginas": n_pag, "memorial": mem,
            "n_pranchas": len(pranchas), "faltando": faltando}


def _selftest():
    # sem FreeCAD: gera um dossie so com capa+relatorio (sem memorial/pranchas)
    import tempfile
    out = tempfile.mkdtemp(prefix="dossie_")
    spec = {"slug": "t", "descricao": "teste", "geometria": {"comprimento": 20, "span": 10}}
    r = gerar_dossie(out, spec, relatorio="VEREDITO: ATENDE\nlinha 2\nlinha 3")
    assert os.path.exists(r["path"]) and r["n_paginas"] >= 1, r
    assert "memorial (nao encontrado)" in r["faltando"]      # sem memorial no dir
    import fitz
    with fitz.open(r["path"]) as d:
        txt = d[0].get_text()
    assert "PROJETO EXECUTIVO ESTRUTURAL" in txt
    print("dossie self-test PASSED")
    print("  paginas=%d ; faltando=%s" % (r["n_paginas"], r["faltando"]))


if __name__ == "__main__":
    _selftest()
