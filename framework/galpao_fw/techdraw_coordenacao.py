# ============================================================================
# techdraw_coordenacao.py - PRANCHA A1 TechDraw da COORDENACAO do modelo FEDERADO
# do galpao turnkey, a partir de galpao_turnkey.rodar() + checa_interferencia_federada().
# ----------------------------------------------------------------------------
# Como o incendio (techdraw_incendio), a coordenacao NAO tem um FCStd proprio: a
# prancha e' um ESQUEMA das 6 disciplinas juntas (planta + elevacao coloridas por
# disciplina + clash), gerado em SVG por desenho_coordenacao e embutido via
# TechDraw::DrawViewSymbol. Cria-se um documento VAZIO e montam-se as pranchas so
# com o SVG + tabelas.
#
# 2 pranchas A1: PE-COORD-01 PLANTA DE COORDENACAO (modelo federado, SVG embutido);
# PE-COORD-02 QUADRO DE CLASH (A REVISAR / ESPERADOS) + NOTAS. Carimbo proprio
# (_carimbo_coord) evita o vazamento de material/norma de ACO do carimbo generico.
#
# Roda DENTRO do freecad.exe (GUI -> exportPageAsPdf), disparado por QTimer, como os
# demais techdraw_*. Contextos: FORA (config_de_spec/codigo_fonte/script_bootstrap) e
# DENTRO (gerar_executivo_coordenacao/_entry_coordenacao).
# ============================================================================
import os

from techdraw_exec import (
    _nova_prancha, _anot, _tabela, _bloco_texto, _carimbo, _svg_para_png)


def _carimbo_coord(cfg, titulo, numero, escala, folha):
    """Carimbo da coordenacao: corrige os defaults ESTRUTURAIS do carimbo generico
    (material/norma/tipo/dept.), como o incendio faz - senao a prancha de coordenacao
    sairia como 'PROJETO EXECUTIVO ESTRUTURAL' / dept. 'ESTRUTURAS'."""
    car = _carimbo(cfg, titulo, numero, escala, folha)
    car["part_material"] = cfg.get("carimbo_material", "COORDENACAO")
    car["general_tolerances"] = "BIM/IFC4"
    car["document_type"] = "PRANCHA DE COORDENACAO (FEDERADO)"
    car["responsible_department"] = "COORDENACAO"
    return car


# ─────────────────────────────────────────────────────────────────────────
# PRANCHAS (rodam dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def _pr_planta(doc, cfg):
    """PE-COORD-01 - PLANTA DE COORDENACAO: embute o SVG (desenho_coordenacao) como
    TechDraw::DrawViewSymbol na prancha A1."""
    page = _nova_prancha(doc, "COORD01_PLANTA",
                         _carimbo_coord(cfg, "PLANTA DE COORDENACAO - MODELO FEDERADO",
                                        "PE-COORD-01", "S/ESC", "01/02"))
    sym = doc.addObject("TechDraw::DrawViewSymbol", "PLANTA_COORD")
    sym.Symbol = cfg["coord_svg"]
    page.addView(sym)
    try:
        sym.X = 420.0                     # centro da A1 (841 x 594 mm)
        sym.Y = 300.0
        sym.Scale = 7.0                   # o SVG (1000x700) preenche ~570x400 mm
    except Exception:
        pass
    return [page]


def _pr_clash(doc, cfg):
    """PE-COORD-02 - QUADRO DE CLASH + NOTAS."""
    page = _nova_prancha(doc, "COORD02_CLASH",
                         _carimbo_coord(cfg, "QUADRO DE CLASH E NOTAS",
                                        "PE-COORD-02", "-", "02/02"))
    _anot(doc, page, "A02c", ["QUADRO DE INTERFERENCIAS (CLASH) - COORDENACAO"],
          175, 520, 6)
    _tabela(doc, page, "Q02C", cfg["clash_hdr"], cfg["clash_rows"],
            175, 455, tam=6, larguras=[150, 150, 130, 150], escala=1.3)
    _bloco_texto(doc, page, "N02c", cfg["notas"], 175, 250, tam=5, largura=580,
                 escala=1.3)
    return [page]


# ─────────────────────────────────────────────────────────────────────────
# ORQUESTRACAO (dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def gerar_executivo_coordenacao(cfg):
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

    doc = App.newDocument("executivo_coordenacao")     # SEM FCStd: e' esquema

    paginas = []
    for fn in (_pr_planta, _pr_clash):
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
    fcstd_out = os.path.join(out, "executivo_coordenacao.FCStd")
    try:
        doc.saveAs(fcstd_out)
    except Exception:
        pass
    return {"ok": True, "pranchas": [p.Name for p in paginas],
            "arquivos": arquivos, "fcstd": fcstd_out}


def _entry_coordenacao(cfg):
    """Ponto unico chamado pelo bootstrap (via QTimer). Grava status e fecha."""
    import json
    import FreeCAD as App
    out = os.path.join(cfg["out"], "pranchas")
    try:
        os.makedirs(out, exist_ok=True)
    except Exception:
        pass
    status = os.path.join(out, "_status_coord.json")
    try:
        res = gerar_executivo_coordenacao(cfg)
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


# ─────────────────────────────────────────────────────────────────────────
# API PUBLICA (roda FORA do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def config_de_spec(R, out_dir, spec=None, clash=None):
    """Monta o cfg (dados JA computados) a partir de galpao_turnkey.rodar(spec)=R.
    O SVG da coordenacao e' gerado AQUI (desenho_coordenacao, sobre os membros
    federados + clash) e injetado como string - nada e' recalculado no FreeCAD.
    clash: relatorio de checa_interferencia_federada (se None, e' computado aqui)."""
    import galpao_turnkey as tk
    import desenho_coordenacao as dc
    spec = spec or {}

    membros, disc = tk._membros_federados(R, spec)
    if clash is None:
        clash = tk.checa_interferencia_federada(R, spec)
    coord_svg = dc.coordenacao_svg(membros, clash)

    # tabela de clash: primeiro os A REVISAR (coordenacao real), depois os ESPERADOS
    revisar = clash.get("revisar", [c for c in clash.get("clashes", [])
                                     if not c.get("esperado")])
    esperados = clash.get("esperados", [c for c in clash.get("clashes", [])
                                        if c.get("esperado")])
    clash_hdr = ["ITEM A", "ITEM B", "DISCIPLINAS", "SITUACAO"]
    clash_rows = []
    for c in revisar[:22]:
        clash_rows.append([str(c.get("a", "")), str(c.get("b", "")),
                           str(c.get("disciplinas", "")), "A REVISAR"])
    for c in esperados[:8]:
        clash_rows.append([str(c.get("a", "")), str(c.get("b", "")),
                           str(c.get("disciplinas", "")), "esperado (montagem)"])
    if not clash_rows:
        clash_rows.append(["-", "-", "-", "sem interferencias > vol_min"])

    n_rev = clash.get("n_revisar", len(revisar))
    n_esp = clash.get("n_esperado", len(esperados))
    por_par = "; ".join("%s=%d" % (k, v) for k, v in sorted(clash.get("por_par", {}).items()))
    notas = [
        "NOTAS - COORDENACAO DO MODELO FEDERADO (BIM/IFC4)",
        "1. Disciplinas federadas: %s." % ", ".join(disc),
        "2. Frame comum: X=comprimento, Y=largura, Z=altura (mm). Cores por disciplina "
        "na legenda da planta.",
        "3. Clash entre disciplinas: %d membros ; %d conflitos = %d A REVISAR + %d "
        "esperados." % (clash.get("n_membros", len(membros)),
                        clash.get("n_clashes", n_rev + n_esp), n_rev, n_esp),
        "4. Por par de disciplinas: %s." % (por_par or "-"),
        "5. ESPERADOS = aterramento/SPDA cruzando a estrutura (NBR 5419) - montagem "
        "intencional, nao reprovam o calculo.",
        "6. A REVISAR = candidatos de conflito de obra (ex.: duto x viga, tubo x "
        "eletrocalha) - o coordenador decide o reroteamento.",
        "7. Posicoes esquematicas dos verticais (eletrico/incendio/HVAC/hidraulica) - "
        "ajustar ao leiaute real de projeto.",
    ]

    return {
        "out": str(out_dir).replace("\\", "/"),
        "slug": spec.get("slug", "galpao_coordenacao"),
        "descricao": spec.get("descricao", "Galpao industrial - Coordenacao (modelo federado)"),
        "autor": spec.get("autor", "galpao_fw"),
        "coord_svg": coord_svg,
        "clash_hdr": clash_hdr, "clash_rows": clash_rows,
        "carimbo_material": "COORDENACAO",
        "notas": notas,
        "materiais": None,
    }


def codigo_fonte():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "techdraw_coordenacao.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _para_nativo(o):
    import techdraw_exec as TE
    return TE._para_nativo(o)


def script_bootstrap(cfg):
    """Script que o freecad.exe roda: prepende o dir do galpao_fw no sys.path, injeta
    cfg + a fonte, e dispara _entry_coordenacao via QTimer. O SVG ja vem pronto em cfg."""
    galpao_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
    return ("# -*- coding: utf-8 -*-\n"
            "import sys\n"
            "if %r not in sys.path: sys.path.insert(0, %r)\n" % (galpao_dir, galpao_dir)
            + "_CFG_ = %r\n" % (_para_nativo(cfg),)
            + codigo_fonte()
            + "\nfrom PySide import QtCore\n"
            "QtCore.QTimer.singleShot(1500, lambda: _entry_coordenacao(_CFG_))\n")
