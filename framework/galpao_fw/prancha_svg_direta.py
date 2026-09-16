# ============================================================================
# prancha_svg_direta.py - G104: PRANCHAS A1 SEM freecad.exe (disciplinas de esquema puro)
# Rota SVG -> PDF em Python puro (fitz), para hidraulica, incendio e climatizacao.
# Essas tres disciplinas NAO tem 3D: o esquema e' SVG do desenho_* e o quadro e'
# tabela+notas do config_de_spec. Pagar uma instancia grafica de freecad.exe so
# para carimbar esse conteudo numa A1 e' a causa medida do custo (G96/D118, G104).
#
# REUSO, nao reescrita (convecoes do lote G99-G105):
#   - caderno_casa_edificio.svg_para_png (pixmap do fitz; doc.save() direto sobre
#     SVG falha - G94) para rasterizar o esquema;
#   - techdraw_hidraulica/incendio/climatizacao.config_de_spec (o conteudo: esquema
#     SVG + dim_hdr/dim_rows + notas) e _carimbo_hid/_carimbo_inc/_carimbo_cli (o
#     carimbo A1: titulo/numero/escala/folha/material/norma/departamento);
#   - dossie._add_paginas_texto NAO serve aqui (A4 retrato); a pagina A1 e' propria.
# O caminho FreeCAD CONTINUA existindo (backend="freecad" nos montar_pranchas);
# este modulo e' a rota alternativa que o G105 usa para medir sem GUI.
#
# Pagina A1 paisagem (ISO 5457): 841 x 594 mm = 2384 x 1684 pt. O esquema entra
# como imagem escalada preservando proporcao; o quadro entra como texto
# monoespacado (conteudo verbatim do cfg, sem reinterpretar numeros).
# ============================================================================
"""Pranchas A1 em Python puro para as disciplinas de esquema SVG (G104).

Rota alternativa ao freecad.exe: esquema SVG -> PNG (fitz pixmap) -> pagina A1,
quadro de dimensionamento + notas + carimbo em pagina A1 de texto. So fitz +
stdlib; testavel em CI. O caminho FreeCAD nao e' removido.
"""

from __future__ import annotations

import datetime
import os
import tempfile

# A1 paisagem em pontos (pt): 841 x 594 mm. Mesmo valor do _pdf_dummy de
# caderno_turnkey (2384.0 x 1684.0).
A1_W_PT = 2384.0
A1_H_PT = 1684.0

DISCIPLINAS = ("hidraulica", "incendio", "climatizacao")

# Nomes de arquivo iguais aos das paginas FreeCAD, para que
# caderno_turnkey._coletar_pdfs (glob *.pdf) encontre sem mudanca.
ARQUIVOS = {
    "hidraulica": ("HID01_ESQUEMA", "HID02_QUADRO"),
    "incendio": ("INC01_PLANTA", "INC02_RESUMO"),
    "climatizacao": ("CLI01_ESQUEMA", "CLI02_QUADRO"),
}

PRANCHAS = {
    "hidraulica": ("PE-HID-01", "PE-HID-02"),
    "incendio": ("PE-INC-01", "PE-INC-02"),
    "climatizacao": ("PE-CLI-01", "PE-CLI-02"),
}

TITULOS = {
    "hidraulica": ("ESQUEMA REDE HIDRAULICA",
                   "DIMENSIONAMENTO E MEMORIAL"),
    "incendio": ("SEGURANCA CONTRA INCENDIO",
                 "QUADRO-RESUMO E MEMORIAL"),
    "climatizacao": ("ESQUEMA REDE HVAC",
                     "QUADRO CAPACIDADE/MEMORIAL"),
}


def _cfg_da_disciplina(disciplina, r, out_dir, spec=None):
    """config_de_spec da disciplina (conteudo JA computado, sem recalcular)."""
    if disciplina == "hidraulica":
        import techdraw_hidraulica as TD
        return TD.config_de_spec(r, str(out_dir), spec), TD
    if disciplina == "incendio":
        import techdraw_incendio as TD
        return TD.config_de_spec(r, str(out_dir), spec), TD
    if disciplina == "climatizacao":
        import techdraw_climatizacao as TD
        return TD.config_de_spec(r, str(out_dir), spec), TD
    return None, None


def _carimbo_da_disciplina(TD, cfg, titulo, numero, folha):
    """Carimbo A1 via a funcao propria da disciplina (nunca o generico)."""
    if hasattr(TD, "_carimbo_hid"):
        return TD._carimbo_hid(cfg, titulo, numero, "S/ESC" if "01" in folha else "-", folha)
    if hasattr(TD, "_carimbo_inc"):
        return TD._carimbo_inc(cfg, titulo, numero, "S/ESC" if "01" in folha else "-", folha)
    if hasattr(TD, "_carimbo_cli"):
        return TD._carimbo_cli(cfg, titulo, numero, "S/ESC" if "01" in folha else "-", folha)
    from techdraw_exec import _carimbo
    return _carimbo(cfg, titulo, numero, "S/ESC", folha)


def _linhas_carimbo(carimbo):
    """Linhas de rodape com os campos do carimbo (verbatim, sem inventar)."""
    return [
        "%s | %s | %s" % (carimbo.get("drawing_number", "?"),
                           carimbo.get("title", "?"),
                           carimbo.get("scale", "?")),
        "%s | %s | %s" % (carimbo.get("document_type", "?"),
                           carimbo.get("responsible_department", "?"),
                           carimbo.get("general_tolerances", "?")),
        "Folha %s | %s | %s | %s" % (carimbo.get("sheet_number", "?"),
                                      carimbo.get("date_of_issue", ""),
                                      carimbo.get("creator", ""),
                                      carimbo.get("legal_owner_1", "")),
    ]


def pagina_esquema_a1(doc, esquema_svg, carimbo, titulo_pagina, subtitulo="",
                       dpi=150):
    """Adiciona a pagina A1 do esquema: rasteriza o SVG via pixmap do fitz e
    embute escalado com titulo + carimbo. Retorna True; False sem derrubar (o
    chamador declara o motivo)."""
    import fitz

    from caderno_casa_edificio import svg_para_png

    if not esquema_svg or not str(esquema_svg).lstrip().startswith("<svg"):
        return False
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(esquema_svg)
    except Exception:
        return False
    with tempfile.TemporaryDirectory(prefix="prancha_svg_") as tmp:
        svg_path = os.path.join(tmp, "esquema.svg")
        png_path = os.path.join(tmp, "esquema.png")
        try:
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(esquema_svg)
        except OSError:
            return False
        if not svg_para_png(svg_path, png_path, dpi=dpi):
            return False
        try:
            page = doc.new_page(width=A1_W_PT, height=A1_H_PT)
            margem, topo = 72.0, 190.0
            rodape_h = 110.0
            page.insert_text((margem, 70), str(titulo_pagina), fontname="helv",
                             fontsize=34)
            if subtitulo:
                # Uma linha so cabe aqui: o corpo encolhe ate caber, nunca
                # corta (o [:160] apagava o fim do subtitulo - G106).
                sub = str(subtitulo)
                corpo = min(20.0, _LARG_UTIL_PT / (max(len(sub), 1) * 0.7))
                page.insert_text((margem, 120), sub, fontname="helv",
                                 fontsize=corpo)
            car = _linhas_carimbo(carimbo)
            page.insert_text((margem, 155), car[0], fontname="helv", fontsize=16)
            pix = fitz.Pixmap(png_path)
            try:
                iw, ih = float(pix.width), float(pix.height)
            finally:
                try:
                    pix = None
                except Exception:
                    pass
            if not iw or not ih:
                return False
            aw, ah = A1_W_PT - 2 * margem, A1_H_PT - topo - rodape_h - margem
            esc = min(aw / iw, ah / ih)
            w, h = iw * esc, ih * esc
            x0 = margem + (aw - w) / 2.0
            y0 = topo + (ah - h) / 2.0
            page.insert_image(fitz.Rect(x0, y0, x0 + w, y0 + h),
                              filename=png_path)
            yb = A1_H_PT - rodape_h + 10.0
            for i, ln in enumerate(car):
                page.insert_text((margem, yb + i * 28), ln, fontname="helv",
                                 fontsize=16)
            return True
        except Exception:
            return False


# Largura util da A1 (2384 - 2 x 72 pt). Courier ocupa 0,6 do corpo por
# caractere; helv (proporcional, caixa alta nos titulos) usa 0,7 por
# seguranca. E a conta que diz quantos caracteres cabem por linha.
_MARGEM_PT = 72.0
_LARG_UTIL_PT = A1_W_PT - 2 * _MARGEM_PT


def _quebra(texto, corpo, fator=0.6):
    """Quebra `texto` em linhas que cabem na largura util - nunca corta.

    G106: a versao anterior fazia `ln[:220]` e parava no fim da pagina com
    `break`; a nota de 403 caracteres da hidraulica saia pela metade e
    linha de quadro alem da pagina sumia, sem aviso (saturacao silenciosa,
    convencao 4)."""
    import textwrap

    cabem = max(20, int(_LARG_UTIL_PT / (corpo * fator)))
    return textwrap.wrap(str(texto), width=cabem, break_long_words=True,
                         break_on_hyphens=False) or [""]


def _nova_pagina_quadro(doc, carimbo, titulo_pagina, indice):
    page = doc.new_page(width=A1_W_PT, height=A1_H_PT)
    titulo = str(titulo_pagina)
    if indice:
        titulo += " (continuacao %d)" % indice
    page.insert_text((_MARGEM_PT, 110.0), titulo, fontname="helv",
                     fontsize=34)
    yb = A1_H_PT - 100.0
    for i, ln in enumerate(_linhas_carimbo(carimbo)):
        page.insert_text((_MARGEM_PT, yb + i * 28), ln, fontname="helv",
                         fontsize=16)
    return page


def pagina_quadro_a1(doc, carimbo, titulo_pagina, subtitulo, header, rows,
                     notas, carimbos=None):
    """Adiciona a(s) pagina(s) A1 do quadro: header+rows verbatim do cfg e
    notas verbatim, em texto monoespacado, com o carimbo no rodape de cada
    pagina. Linha longa quebra; quadro que nao cabe continua em nova pagina
    A1 do mesmo PDF - nada e' cortado. Pura (so fitz). Devolve o numero de
    paginas escritas.

    G151: `carimbos` (lista de dicts, opcional) da coerencia ao sheet_number
    quando o quadro derrama em N>1 paginas: pagina k usa carimbos[k] (se
    houver) em vez do mesmo `carimbo` em todas. Sem ele, o comportamento
    historico permanece (mesmo carimbo + "(continuacao N)" no titulo)."""
    itens = []                              # (texto, fonte, corpo, passo)
    if subtitulo:
        itens += [(ln, "helv", 20, 44.0) for ln in _quebra(subtitulo, 20, 0.7)]
    itens.append(("", "courier", 10, 10.0))
    cabecalho = " | ".join(str(h) for h in (header or []))
    itens += [(ln, "courier", 20, 40.0) for ln in _quebra(cabecalho, 20)]
    for row in (rows or []):
        itens += [(ln, "courier", 18, 34.0)
                  for ln in _quebra(" | ".join(str(c) for c in row), 18)]
    itens.append(("", "courier", 10, 20.0))
    for nota in (notas or []):
        itens += [(ln, "courier", 16, 30.0) for ln in _quebra(nota, 16)]

    limite = A1_H_PT - 160.0                # acima do carimbo
    page, y, paginas = None, 0.0, 0
    for texto, fonte, corpo, passo in itens:
        if page is None or y + passo > limite:
            car_k = carimbo
            if isinstance(carimbos, (list, tuple)) and paginas < len(carimbos) and isinstance(carimbos[paginas], dict):
                car_k = carimbos[paginas]
            page = _nova_pagina_quadro(doc, car_k, titulo_pagina, paginas)
            paginas += 1
            y = 160.0
        if texto:
            page.insert_text((_MARGEM_PT, y), texto, fontname=fonte,
                             fontsize=corpo)
        y += passo
    return paginas


def montar_pranchas_rota_direta(r, out_dir, disciplina, spec=None, dpi=150):
    """Rota SVG-direta (sem freecad.exe) para hidraulica/incendio/climatizacao.

    Usa o config_de_spec da disciplina (mesmo conteudo do FreeCAD) e grava 2
    PDFs A1 em out_dir/pranchas com os mesmos basenames das paginas FreeCAD.
    Retorna {ok, pranchas, arquivos, fcstd, rota} | {erro} (nunca silencioso).
    """
    import fitz

    if disciplina not in DISCIPLINAS:
        return {"erro": "disciplina sem rota svg-direta: %r (esperado %s)"
                % (disciplina, list(DISCIPLINAS))}
    try:
        cfg, TD = _cfg_da_disciplina(disciplina, r, out_dir, spec)
    except Exception as exc:
        return {"erro": "%s: %s" % (type(exc).__name__, exc)}
    esquema_svg = (cfg.get("esquema_svg") or cfg.get("planta_svg") or "")
    dim_hdr = cfg.get("dim_hdr") or cfg.get("resumo_hdr") or []
    dim_rows = cfg.get("dim_rows") or cfg.get("resumo") or []
    notas = cfg.get("notas") or []
    if not esquema_svg:
        return {"erro": "esquema SVG ausente no cfg de %s" % disciplina}
    if not dim_rows:
        return {"erro": "quadro de dimensionamento vazio no cfg de %s"
                % disciplina}

    base_esq, base_qua = ARQUIVOS[disciplina]
    cod_esq, cod_qua = PRANCHAS[disciplina]
    tit_esq, tit_qua = TITULOS[disciplina]
    slug = str(cfg.get("slug") or disciplina)
    car_esq = _carimbo_da_disciplina(TD, cfg, tit_esq, cod_esq, "01/02")
    car_qua = _carimbo_da_disciplina(TD, cfg, tit_qua, cod_qua, "02/02")
    subt = "%s | %s" % (cfg.get("descricao", slug), slug)

    prdir = os.path.join(str(out_dir), "pranchas")
    try:
        os.makedirs(prdir, exist_ok=True)
    except OSError as exc:
        return {"erro": "nao cria pranchas: %s" % exc}

    pdf_esq = os.path.join(prdir, base_esq + ".pdf")
    doc = fitz.open()
    try:
        ok = pagina_esquema_a1(doc, esquema_svg, car_esq,
                                "%s - %s" % (cod_esq, tit_esq), subt, dpi=dpi)
        if not ok:
            doc.close()
            return {"erro": "esquema SVG de %s nao rasterizou (svg_para_png)"
                    % disciplina}
        doc.save(pdf_esq, garbage=3, deflate=True)
    finally:
        try:
            doc.close()
        except Exception:
            pass
    if not os.path.exists(pdf_esq):
        return {"erro": "PDF do esquema nao gravado: %s" % pdf_esq}

    pdf_qua = os.path.join(prdir, base_qua + ".pdf")
    doc2 = fitz.open()
    try:
        if not pagina_quadro_a1(doc2, car_qua, "%s - %s" % (cod_qua, tit_qua),
                                subt, dim_hdr, dim_rows, notas):
            return {"erro": "quadro de %s sem pagina escrita" % disciplina}
        doc2.save(pdf_qua, garbage=3, deflate=True)
    finally:
        try:
            doc2.close()
        except Exception:
            pass
    if not os.path.exists(pdf_qua):
        return {"erro": "PDF do quadro nao gravado: %s" % pdf_qua}

    return {"ok": True, "pranchas": [base_esq, base_qua],
            "arquivos": [pdf_esq, pdf_qua], "fcstd": None,
            "rota": "svg-direta",
            "emitido_em": datetime.date.today().strftime("%d/%m/%Y")}


def _selftest():
    import galpao_hidraulica as ghi
    import galpao_seguranca_incendio as gsi
    import galpao_climatizacao as gcl
    import tempfile
    out = tempfile.mkdtemp(prefix="prancha_svg_")
    rh = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                    "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2},
                                   "aparelhos_esgoto": {"bacia": 2, "lavatorio": 2}}})
    ri = gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                    "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                    "deteccao": {"viga_m": 0.0},
                    "sprinklers": {"altura_estoque_m": 3.0}})
    rc = gcl.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "tipo": "galpao"})
    for disc, rr in (("hidraulica", rh), ("incendio", ri), ("climatizacao", rc)):
        res = montar_pranchas_rota_direta(rr, out, disc)
        assert res.get("ok"), (disc, res)
        assert len(res["arquivos"]) == 2 and res["fcstd"] is None, res
        for pdf in res["arquivos"]:
            assert os.path.exists(pdf) and os.path.getsize(pdf) > 0, pdf
    print("prancha_svg_direta self-test PASSED")


if __name__ == "__main__":
    _selftest()
