# ============================================================================
# techdraw_hidraulica.py - PRANCHAS A1 TechDraw do EXECUTIVO de HIDRAULICA PREDIAL
# do galpao, a partir de galpao_hidraulica.rodar(). Nivela a hidraulica com as demais
# disciplinas (concreto/aco/eletrico/incendio), que ja tem executivo A1 proprio.
# ----------------------------------------------------------------------------
# Como o incendio (techdraw_incendio), a hidraulica NAO tem FCStd proprio: o esquema
# da rede e' gerado em SVG por desenho_hidraulica e embutido via DrawViewSymbol.
# 2 pranchas A1: PE-HID-01 ESQUEMA DA REDE (pluvial/esgoto/agua, diametros rotulados,
# SVG embutido); PE-HID-02 QUADRO DE DIMENSIONAMENTO + NOTAS/MEMORIAL (normas).
# Carimbo proprio (_carimbo_hid). Roda dentro do freecad.exe (QTimer).
# ============================================================================
import os

from techdraw_exec import (
    _nova_prancha, _anot, _tabela, _bloco_texto, _carimbo, _svg_para_png)


def _carimbo_hid(cfg, titulo, numero, escala, folha):
    """Carimbo da hidraulica: corrige os defaults ESTRUTURAIS do carimbo generico."""
    car = _carimbo(cfg, titulo, numero, escala, folha)
    car["part_material"] = cfg.get("carimbo_material", "HIDRAULICA")
    car["general_tolerances"] = "NBR 5626/8160/10844"
    car["document_type"] = "PROJETO DE HIDRAULICA PREDIAL"
    car["responsible_department"] = "HIDRAULICA"
    return car


def _pr_esquema(doc, cfg):
    """PE-HID-01 - ESQUEMA DA REDE: embute o SVG (desenho_hidraulica)."""
    page = _nova_prancha(doc, "HID01_ESQUEMA",
                         _carimbo_hid(cfg, "ESQUEMA DA REDE HIDRAULICA PREDIAL",
                                      "PE-HID-01", "S/ESC", "01/02"))
    sym = doc.addObject("TechDraw::DrawViewSymbol", "ESQUEMA_HID")
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
    """PE-HID-02 - QUADRO DE DIMENSIONAMENTO + NOTAS."""
    page = _nova_prancha(doc, "HID02_QUADRO",
                         _carimbo_hid(cfg, "QUADRO DE DIMENSIONAMENTO E MEMORIAL",
                                      "PE-HID-02", "-", "02/02"))
    _anot(doc, page, "A02h", ["QUADRO DE DIMENSIONAMENTO - HIDRAULICA PREDIAL"], 175, 520, 6)
    _tabela(doc, page, "Q02H", cfg["dim_hdr"], cfg["dim_rows"],
            175, 455, tam=6, larguras=[210, 150, 220], escala=1.3)
    _bloco_texto(doc, page, "N02h", cfg["notas"], 175, 290, tam=5, largura=580, escala=1.3)
    return [page]


def gerar_executivo_hidraulica(cfg):
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
    doc = App.newDocument("executivo_hidraulica")

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
    fcstd_out = os.path.join(out, "executivo_hidraulica.FCStd")
    try:
        doc.saveAs(fcstd_out)
    except Exception:
        pass
    return {"ok": True, "pranchas": [p.Name for p in paginas],
            "arquivos": arquivos, "fcstd": fcstd_out}


def _entry_hidraulica(cfg):
    import json
    import FreeCAD as App
    out = os.path.join(cfg["out"], "pranchas")
    try:
        os.makedirs(out, exist_ok=True)
    except Exception:
        pass
    status = os.path.join(out, "_status_hid.json")
    try:
        res = gerar_executivo_hidraulica(cfg)
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
    """Monta o cfg (dados JA computados) a partir de galpao_hidraulica.rodar(r).
    O SVG do esquema e' gerado AQUI (desenho_hidraulica) - nada e' recalculado no FreeCAD."""
    import desenho_hidraulica as dh
    spec = spec or {}
    redes = r["redes"]
    g = r["gates"]["rede"]

    esquema_svg = dh.esquema_hidraulica_svg(r)

    ag = redes["agua_fria"]; es = redes["esgoto"]; pl = redes["pluvial"]
    dim_hdr = ["COMPONENTE", "DIAMETRO", "NORMA / CRITERIO"]
    dim_rows = [
        ["Condutor pluvial (vertical)", "DN %.0f" % pl["D_mm"],
         "NBR 10844 (Q=i.A/60, Tab.4; DN>=75)"],
    ]
    if pl.get("calha_mm"):
        dim_rows.append(["Calha (semicircular)", "DN %.0f" % pl["calha_mm"],
                         "NBR 10844 Tab.3 (Manning-Strickler)"])
    dim_rows.append(["Coletor de esgoto", "DN %.0f" % es["D_mm"],
                     "NBR 8160 Tab.7 (UHC=%.0f)" % es.get("uhc", 0)])
    if es.get("ventilacao_coluna_mm"):
        dim_rows.append(["Ventilacao (ramal / coluna)",
                         "DN %.0f / %.0f" % (es.get("ventilacao_ramal_mm", 0),
                                             es["ventilacao_coluna_mm"]),
                         "NBR 8160 Tab.8 / Tab.D.1"])
    metodo = ag.get("metodo", "-")
    dim_rows.append(["Barrilete de agua fria", "DN %.0f" % ag["D_mm"],
                     "NBR 5626 (%s; v<=3 m/s)" % metodo])
    if ag.get("pressao"):
        vp = ag["pressao"]
        dim_rows.append(["Pressao residual no ponto", "%.0f kPa (min %.0f)"
                         % (vp["p_residual_kPa"], vp["p_min_kPa"]),
                         "NBR 5626:1998 A.2 (Fair-Whipple-Hsiao)"])

    notas = [
        "NOTAS TECNICAS E MEMORIAL - HIDRAULICA PREDIAL",
        "1. Aguas pluviais (NBR 10844): vazao Q=i.A/60 (i intensidade local - DADO DE "
        "SITIO, confirmar Tab.5 por cidade); condutor vertical DN interno >= 70 mm "
        "(Sec.5.6.3); calha semicircular pela Tab.3.",
        "2. Esgoto sanitario (NBR 8160): dimensionamento por Unidades Hunter de "
        "Contribuicao (UHC=%.0f); coletor predial DN minimo 100; declividade minima "
        "2%% (DN<=75) / 1%% (DN>=100)." % es.get("uhc", 0),
        "3. Ventilacao (NBR 8160 Sec.5.2.2): ramal por UHC (Tab.8), coluna pelo DN do "
        "esgoto (Tab.D.1). A ventilacao protege os fechos hidricos dos sifoes.",
        "4. Agua fria (NBR 5626): vazao pelo metodo '%s' (a 2020 Sec.6.14.2 admite metodo "
        "reconhecido, empirico ou probabilistico); diametro pela velocidade <= 3 m/s "
        "(Sec.6.8.3); pressao dinamica minima no ponto 10 kPa (5 caixa / 15 valvula)." % metodo,
    ]
    if ag.get("pressao") and ag["pressao"].get("p_alim_default"):
        notas.append("5. Pressao de alimentacao (p_alim) ASSUMIDA (rede/reservatorio) - "
                     "DADO DE SITIO a confirmar; a pressao residual e' indicativa.")
    notas.append("6. Posicoes esquematicas - ajustar ao leiaute real de projeto. "
                 "Dimensionamento: %s." % g["dimensionamento"])

    return {
        "out": str(out_dir).replace("\\", "/"),
        "slug": spec.get("slug", "galpao_hidraulica"),
        "descricao": spec.get("descricao", "Galpao industrial - Hidraulica Predial"),
        "autor": spec.get("autor", "galpao_fw"),
        "esquema_svg": esquema_svg,
        "dim_hdr": dim_hdr, "dim_rows": dim_rows,
        "carimbo_material": "HIDRAULICA",
        "notas": notas,
        "materiais": None,
    }


def codigo_fonte():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "techdraw_hidraulica.py")
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
            "QtCore.QTimer.singleShot(1500, lambda: _entry_hidraulica(_CFG_))\n")
