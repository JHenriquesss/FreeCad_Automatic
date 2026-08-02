# ============================================================================
# techdraw_incendio.py - PROJETO EXECUTIVO (pranchas A1 TechDraw) da SEGURANCA
# CONTRA INCENDIO do galpao (planta do AVCB), a partir de
# galpao_seguranca_incendio.rodar().
# ----------------------------------------------------------------------------
# DIFERENCA p/ os outros executivos: o vertical de incendio NAO tem modelo 3D -
# a planta de seguranca e' um ESQUEMA de leiaute (rotas de fuga/simbolos), gerada
# em SVG por desenho_incendio e embutida via TechDraw::DrawViewSymbol. Logo aqui
# NAO se abre um FCStd nem se faz _vista: cria-se um documento VAZIO e montam-se as
# pranchas so com o SVG + tabelas.
#
# 2 pranchas A1: PE-INC-01 PLANTA DE SEGURANCA (rotas de fuga + detectores +
# chuveiros + sinalizacao, SVG embutido); PE-INC-02 QUADRO-RESUMO + NOTAS/MEMORIAL
# (contagens por sistema + normas). Carimbo proprio (_carimbo_inc) evita o vazamento
# de material/norma de ACO do carimbo generico.
#
# Roda DENTRO do freecad.exe (GUI -> exportPageAsPdf), disparado por QTimer, como os
# demais techdraw_*. Contextos: FORA (config_de_spec/codigo_fonte/script_bootstrap)
# e DENTRO (gerar_executivo_incendio/_entry_incendio).
# ============================================================================
import os

from techdraw_exec import (
    _nova_prancha, _anot, _tabela, _bloco_texto, _carimbo, _svg_para_png)


def _carimbo_inc(cfg, titulo, numero, escala, folha):
    """Carimbo do incendio: corrige TODOS os defaults ESTRUTURAIS do carimbo generico
    (material, norma, tipo de documento e departamento). Sem isso a prancha de
    incendio sairia como 'PROJETO EXECUTIVO ESTRUTURAL' / dept. 'ESTRUTURAS' /
    'NBR 8800/6118' - a mesma classe do vazamento aco/concreto que ja pegamos."""
    car = _carimbo(cfg, titulo, numero, escala, folha)
    car["part_material"] = cfg.get("carimbo_material", "SEG. INCENDIO")
    car["general_tolerances"] = "NBR 10898/17240"      # compacto (celula estreita)
    car["document_type"] = "PROJETO DE SEG. CONTRA INCENDIO"
    car["responsible_department"] = "SEG. INCENDIO"
    return car


# ─────────────────────────────────────────────────────────────────────────
# PRANCHAS (rodam dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def _pr_planta(doc, cfg):
    """PE-INC-01 - PLANTA DE SEGURANCA: embute o SVG (desenho_incendio) como
    TechDraw::DrawViewSymbol na prancha A1."""
    page = _nova_prancha(doc, "INC01_PLANTA",
                         _carimbo_inc(cfg, "PLANTA DE SEGURANCA CONTRA INCENDIO",
                                      "PE-INC-01", "S/ESC", "01/02"))
    sym = doc.addObject("TechDraw::DrawViewSymbol", "PLANTA_INC")
    sym.Symbol = cfg["planta_svg"]
    page.addView(sym)
    try:
        sym.X = 420.0                     # centro da A1 (841 x 594 mm)
        sym.Y = 300.0
        sym.Scale = 7.0                   # o SVG (1000x620) preenche ~570x390 mm
    except Exception:
        pass
    return [page]


def _pr_resumo(doc, cfg):
    """PE-INC-02 - QUADRO-RESUMO + NOTAS/MEMORIAL."""
    page = _nova_prancha(doc, "INC02_RESUMO",
                         _carimbo_inc(cfg, "QUADRO-RESUMO E MEMORIAL",
                                      "PE-INC-02", "-", "02/02"))
    # titulo BEM acima da tabela (a colisao titulo x cabecalho apareceu no
    # render-and-look da 1a versao: titulo tam=7 a 30 mm da tabela invadia as linhas).
    _anot(doc, page, "A02r", ["QUADRO-RESUMO DOS SISTEMAS DE SEGURANCA"], 175, 520, 6)
    _tabela(doc, page, "Q02R", cfg["resumo_hdr"], cfg["resumo"],
            175, 455, tam=6, larguras=[260, 140, 180], escala=1.3)
    _bloco_texto(doc, page, "N02", cfg["notas"], 175, 300, tam=5, largura=580,
                 escala=1.3)
    return [page]


# ─────────────────────────────────────────────────────────────────────────
# ORQUESTRACAO (dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def gerar_executivo_incendio(cfg):
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

    doc = App.newDocument("executivo_incendio")        # SEM FCStd: planta e' esquema

    paginas = []
    for fn in (_pr_planta, _pr_resumo):
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
    fcstd_out = os.path.join(out, "executivo_incendio.FCStd")
    try:
        doc.saveAs(fcstd_out)
    except Exception:
        pass
    return {"ok": True, "pranchas": [p.Name for p in paginas],
            "arquivos": arquivos, "fcstd": fcstd_out}


def _entry_incendio(cfg):
    """Ponto unico chamado pelo bootstrap (via QTimer). Grava status e fecha."""
    import json
    import FreeCAD as App
    out = os.path.join(cfg["out"], "pranchas")
    try:
        os.makedirs(out, exist_ok=True)
    except Exception:
        pass
    status = os.path.join(out, "_status.json")
    try:
        res = gerar_executivo_incendio(cfg)
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
def config_de_spec(r, out_dir, spec=None):
    """Monta o cfg (dados JA computados) a partir de galpao_seguranca_incendio.rodar(r).
    O SVG da planta e' gerado AQUI (desenho_incendio) e injetado como string - nada e'
    recalculado dentro do FreeCAD. Nao precisa de FCStd (a planta e' esquema)."""
    import desenho_incendio as di
    spec = spec or {}
    g = r["gates"]

    planta_svg = di.planta_seguranca_svg(r)

    resumo_hdr = ["SISTEMA", "QUANTIDADE", "NORMA"]
    resumo = [
        ["Iluminacao de emergencia (aclaramento)",
         "%d pontos" % g["iluminacao_emergencia"]["N_aclaramento"], "NBR 10898"],
        ["Balizamento",
         "%d pontos" % g["iluminacao_emergencia"]["N_balizamento"], "NBR 10898"],
        ["Sinalizacao de rota", "%d placas" % g["sinalizacao"]["N_placas"], "NBR 16820"],
        ["Deteccao de fumaca (%s)" % g["deteccao_alarme"]["tipo_detector"],
         "%d detectores" % g["deteccao_alarme"]["N_detectores"], "NBR 17240"],
        ["Acionadores manuais",
         "%d unidades" % g["deteccao_alarme"]["N_acionadores"], "NBR 17240"],
    ]
    if g["sprinklers"]["N_chuveiros"]:
        resumo.append(["Chuveiros automaticos (%s)" % g["sprinklers"]["risco"],
                       "%d unidades" % g["sprinklers"]["N_chuveiros"], "NBR 10897"])
        resumo.append(["Reserva de incendio (chuveiros)",
                       "%.0f m3" % g["sprinklers"]["reserva_m3"], "NBR 10897"])
    if g["hidrantes"]["tipo"]:
        resumo.append(["Hidrantes/mangotinhos (tipo %d)" % g["hidrantes"]["tipo"],
                       "%d hidrantes" % g["hidrantes"]["N_hidrantes"], "NBR 13714"])
        resumo.append(["Reserva de incendio (hidrantes)",
                       "%.0f m3" % g["hidrantes"]["reserva_m3"], "NBR 13714"])

    e = g["iluminacao_emergencia"]; a = g["deteccao_alarme"]; sn = g["sinalizacao"]
    notas = [
        "NOTAS TECNICAS E MEMORIAL - SEGURANCA CONTRA INCENDIO",
        "1. Iluminacao de emergencia (NBR 10898): E >= %.0f lux ; autonomia %.0f h ; "
        "comutacao <= %.0f s ; %d pontos de aclaramento + %d de balizamento." % (
            e["E_min_lux"], e["autonomia_h"], e["comutacao_max_s"],
            e["N_aclaramento"], e["N_balizamento"]),
        "2. Sinalizacao de abandono (NBR 16820): placa lado %d mm ; letra >= %d mm ; "
        "espacamento <= %.0f m ; %d placas." % (
            sn["placa_lado_mm"], sn["letra_min_mm"], sn["espacamento_m"], sn["N_placas"]),
        "3. Deteccao e alarme (NBR 17240): %d detectores (%s) + %d acionadores ; "
        "central %s Vcc ; supervisao %.0f h + alarme 15 min." % (
            a["N_detectores"], a["tipo_detector"], a["N_acionadores"],
            "%g" % a["tensao_Vcc"], a["autonomia_supervisao_h"]),
    ]
    if g["sprinklers"]["N_chuveiros"]:
        sp = g["sprinklers"]
        notas.append("4. Chuveiros automaticos (NBR 10897): risco %s ; %d chuveiros ; "
                     "pressao %.2f bar ; reserva de incendio %.0f m3 (chuveiros + "
                     "hidrantes, Tab.24)." % (sp["risco"], sp["N_chuveiros"],
                                              sp["pressao_bar"], sp["reserva_m3"]))
    else:
        notas.append("4. Chuveiros automaticos: nao exigidos/nao informados - verificar a "
                     "IT do Corpo de Bombeiros por area/altura/ocupacao.")
    if g["hidrantes"]["tipo"]:
        h = g["hidrantes"]
        notas.append("5. Sistema de hidrantes/mangotinhos (NBR 13714): sistema tipo %d (%s) ; "
                     "%d hidrantes ; 2 jatos simultaneos = %.0f L/min ; reserva %.0f m3 "
                     "(V = 2 saidas x tempo, 5.4.2)." % (
                         h["tipo"], h["sistema"], h["N_hidrantes"],
                         h["vazao_total_Lmin"], h["reserva_m3"]))
    else:
        notas.append("5. Sistema de hidrantes (NBR 13714): exigido se area > 750 m2 e/ou "
                     "> 12 m; a demanda de hidrantes tambem integra a reserva de incendio "
                     "dos chuveiros (NBR 10897 Tab.24).")
    notas += [
        "6. Simbologia conforme NBR 13434. Posicoes esquematicas - ajustar ao leiaute real.",
        "7. Documentacao para o AVCB (Auto de Vistoria do Corpo de Bombeiros).",
    ]

    return {
        "out": str(out_dir).replace("\\", "/"),
        "slug": spec.get("slug", "galpao_incendio"),
        "descricao": spec.get("descricao", "Galpao industrial - Seguranca contra Incendio"),
        "autor": spec.get("autor", "galpao_fw"),
        "planta_svg": planta_svg,
        "resumo_hdr": resumo_hdr, "resumo": resumo,
        "carimbo_material": "SEG. INCENDIO",
        "notas": notas,
        "materiais": None,
    }


def codigo_fonte():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "techdraw_incendio.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _para_nativo(o):
    import techdraw_exec as TE
    return TE._para_nativo(o)


def script_bootstrap(cfg):
    """Script que o freecad.exe roda: prepende o dir do galpao_fw no sys.path,
    injeta cfg + a fonte, e dispara _entry_incendio via QTimer. O SVG da planta ja
    vem pronto em cfg (desenho_incendio rodou fora)."""
    galpao_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
    return ("# -*- coding: utf-8 -*-\n"
            "import sys\n"
            "if %r not in sys.path: sys.path.insert(0, %r)\n" % (galpao_dir, galpao_dir)
            + "_CFG_ = %r\n" % (_para_nativo(cfg),)
            + codigo_fonte()
            + "\nfrom PySide import QtCore\n"
            "QtCore.QTimer.singleShot(1500, lambda: _entry_incendio(_CFG_))\n")
