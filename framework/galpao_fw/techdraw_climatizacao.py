# ============================================================================
# techdraw_climatizacao.py - PRANCHAS A1 TechDraw do EXECUTIVO de CLIMATIZACAO (HVAC)
# do galpao, a partir de galpao_climatizacao.rodar(). Nivela a climatizacao com as demais
# disciplinas. Como o incendio/hidraulica, NAO tem FCStd: o esquema (SVG do
# desenho_climatizacao) e' embutido via DrawViewSymbol.
# 2 pranchas A1: PE-CLI-01 ESQUEMA DA REDE (tronco/ramais/UTA, SVG); PE-CLI-02 QUADRO
# DE CAPACIDADE + NOTAS/MEMORIAL. Carimbo proprio. Roda dentro do freecad.exe (QTimer).
# ============================================================================
import os

from techdraw_exec import (
    _nova_prancha, _anot, _tabela, _bloco_texto, _carimbo, _svg_para_png)


def _carimbo_cli(cfg, titulo, numero, escala, folha):
    car = _carimbo(cfg, titulo, numero, escala, folha)
    car["part_material"] = cfg.get("carimbo_material", "CLIMATIZACAO")
    car["general_tolerances"] = "NBR 16401"
    car["document_type"] = "PROJETO DE CLIMATIZACAO (HVAC)"
    car["responsible_department"] = "CLIMATIZACAO"
    return car


def _pr_esquema(doc, cfg):
    page = _nova_prancha(doc, "CLI01_ESQUEMA",
                         _carimbo_cli(cfg, "ESQUEMA DA REDE DE CLIMATIZACAO (HVAC)",
                                      "PE-CLI-01", "S/ESC", "01/02"))
    sym = doc.addObject("TechDraw::DrawViewSymbol", "ESQUEMA_CLI")
    sym.Symbol = cfg["esquema_svg"]
    page.addView(sym)
    try:
        sym.X = 420.0
        sym.Y = 300.0
        sym.Scale = 7.0
    except Exception:
        pass
    return [page]


def _pr_quadro(doc, cfg):
    page = _nova_prancha(doc, "CLI02_QUADRO",
                         _carimbo_cli(cfg, "QUADRO DE CAPACIDADE E MEMORIAL",
                                      "PE-CLI-02", "-", "02/02"))
    # views ancoradas pelo CENTRO -> x=420 centraliza na folha A1 (em vez de x=175 a esquerda)
    _anot(doc, page, "A02c", ["QUADRO DE CAPACIDADE - CLIMATIZACAO (HVAC)"], 420, 520, 6)
    _tabela(doc, page, "Q02C", cfg["dim_hdr"], cfg["dim_rows"],
            420, 455, tam=6, larguras=[210, 160, 210], escala=1.5)
    _bloco_texto(doc, page, "N02c", cfg["notas"], 420, 300, tam=5, largura=580, escala=1.5)
    return [page]


def gerar_executivo_climatizacao(cfg):
    import FreeCAD as App
    import FreeCADGui as Gui
    import TechDrawGui
    import time

    try:
        App.Units.setSchema(0)
    except Exception:
        pass
    out = os.path.join(cfg["out"], "pranchas")
    os.makedirs(out, exist_ok=True)
    doc = App.newDocument("executivo_climatizacao")

    paginas = []
    for fn in (_pr_esquema, _pr_quadro):
        try:
            paginas += fn(doc, cfg)
        except Exception as ex:
            App.Console.PrintError("Prancha %s: %s\n" % (fn.__name__, ex))

    doc.recompute()
    for p in paginas:
        try:
            p.ViewObject.doubleClicked()
        except Exception:
            pass
    Gui.updateGui()
    time.sleep(1.0)
    Gui.updateGui()
    doc.recompute()
    Gui.updateGui()
    time.sleep(0.3)
    Gui.updateGui()

    arquivos = []
    for p in paginas:
        base = os.path.join(out, p.Name)
        try:
            TechDrawGui.exportPageAsPdf(p, base + ".pdf")
            arquivos.append(base + ".pdf")
        except Exception as ex:
            App.Console.PrintError("PDF %s: %s\n" % (p.Name, ex))
        try:
            TechDrawGui.exportPageAsSvg(p, base + ".svg")
            arquivos.append(base + ".svg")
            _svg_para_png(base + ".svg", base + ".png")
        except Exception:
            pass
    fcstd_out = os.path.join(out, "executivo_climatizacao.FCStd")
    try:
        doc.saveAs(fcstd_out)
    except Exception:
        pass
    return {"ok": True, "pranchas": [p.Name for p in paginas],
            "arquivos": arquivos, "fcstd": fcstd_out}


def _entry_climatizacao(cfg):
    import json
    import FreeCAD as App
    out = os.path.join(cfg["out"], "pranchas")
    try:
        os.makedirs(out, exist_ok=True)
    except Exception:
        pass
    status = os.path.join(out, "_status_cli.json")
    try:
        res = gerar_executivo_climatizacao(cfg)
    except Exception:
        import traceback
        res = {"erro": traceback.format_exc()}
    try:
        with open(status, "w", encoding="utf-8") as f:
            json.dump(res, f, default=str)
    except Exception:
        pass
    try:
        import FreeCADGui as Gui
        from PySide import QtCore

        def _quit():
            try:
                for nome in list(App.listDocuments().keys()):
                    App.closeDocument(nome)
            except Exception:
                pass
            try:
                QtCore.QCoreApplication.quit()
            except Exception:
                try:
                    Gui.getMainWindow().close()
                except Exception:
                    pass
        QtCore.QTimer.singleShot(400, _quit)
    except Exception:
        pass


def config_de_spec(r, out_dir, spec=None):
    """Monta o cfg (dados JA computados) a partir de galpao_climatizacao.rodar(r)."""
    import desenho_climatizacao as dcl
    spec = spec or {}
    cap = r["gates"]["capacidade"]; dp = r["gates"]["duto_principal"]
    duto = r["duto"]

    esquema_svg = dcl.esquema_climatizacao_svg(r)

    dim_hdr = ["GRANDEZA", "VALOR", "NORMA / CRITERIO"]
    dim_rows = [
        ["Capacidade termica", "%.1f TR (%.0f kW)" % (cap["TR"], cap["kW"]),
         "NBR 16401 (carga termica)"],
        ["Vazao de insuflamento", "%.0f m3/h" % dp["vazao_m3h"],
         "NBR 16401-2 (Q = cap / (0,335.dT))"],
        ["Duto principal (tronco)", "%.2f x %.2f m" % (duto["largura_m"], duto["altura_m"]),
         "NBR 16401-1 (secao por vazao/vel.)"],
        ["Velocidade no duto", "%.1f m/s (max %.1f)" % (dp["vel_ms"], dp["vel_max_ms"]),
         "NBR 16401-1 Tab.1 (classe %d Pa)" % dp["classe_pa"]],
        ["Ramais transversais", "%d" % int(r.get("n_ramais", 4)), "distribuicao no forro"],
    ]
    notas = [
        "NOTAS TECNICAS E MEMORIAL - CLIMATIZACAO (HVAC)",
        "1. Capacidade termica: %.1f TR (%.0f kW ; %.0f BTU/h), pela NBR 16401 (carga "
        "termica do galpao)." % (cap["TR"], cap["kW"], cap["BTU_h"]),
        "2. Vazao de insuflamento %.0f m3/h ; duto tronco %.2f x %.2f m @ %.1f m/s." % (
            dp["vazao_m3h"], duto["largura_m"], duto["altura_m"], dp["vel_ms"]),
        "3. Velocidade limitada a %.1f m/s (NBR 16401-1 Tab.1, classe de pressao %d Pa) "
        "para controle de ruido e perda de carga." % (dp["vel_max_ms"], dp["classe_pa"]),
        "4. dT de insuflamento e' parametro de projeto (a NBR 16401 nao o fixa - depende "
        "da psicrometria do ar de insuflamento) - confirmar em projeto detalhado.",
        "5. Posicoes esquematicas (tronco no eixo, ramais transversais, UTA na empena) - "
        "ajustar ao leiaute e ao zoneamento termico reais.",
    ]

    return {
        "out": str(out_dir).replace("\\", "/"),
        "slug": spec.get("slug", "galpao_climatizacao"),
        "descricao": spec.get("descricao", "Galpao industrial - Climatizacao (HVAC)"),
        "autor": spec.get("autor", "galpao_fw"),
        "esquema_svg": esquema_svg,
        "dim_hdr": dim_hdr, "dim_rows": dim_rows,
        "carimbo_material": "CLIMATIZACAO",
        "notas": notas,
        "materiais": None,
    }


def codigo_fonte():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "techdraw_climatizacao.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _para_nativo(o):
    import techdraw_exec as TE
    return TE._para_nativo(o)


def script_bootstrap(cfg):
    galpao_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
    return ("# -*- coding: utf-8 -*-\n"
            "import sys\n"
            "if %r not in sys.path: sys.path.insert(0, %r)\n" % (galpao_dir, galpao_dir)
            + "_CFG_ = %r\n" % (_para_nativo(cfg),)
            + codigo_fonte()
            + "\nfrom PySide import QtCore\n"
            "QtCore.QTimer.singleShot(1500, lambda: _entry_climatizacao(_CFG_))\n")
