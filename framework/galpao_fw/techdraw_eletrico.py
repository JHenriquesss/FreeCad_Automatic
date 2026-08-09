# ============================================================================
# techdraw_eletrico.py - PROJETO EXECUTIVO (pranchas A1 TechDraw) do PROJETO
# ELETRICO do galpao, a partir do modelo 3D salvo (build_eletrico -> .FCStd) e do
# resultado de galpao_eletrico.rodar().
# ----------------------------------------------------------------------------
# Roda DENTRO do freecad.exe (GUI -> exportPageAsPdf), disparado por QTimer, sem
# interacao (mesma mecanica do techdraw_concreto). freecadcmd NAO exporta PDF.
# Reusa os HELPERS GENERICOS do techdraw_exec (template ISO A1, _vista, _tabela,
# _carimbo, ...) importando o modulo IRMAO num freecad.exe NOVO (processo limpo).
#
# 3 pranchas: PE-EL-01 DIAGRAMA UNIFILAR (SVG do desenho_eletrico embutido via
# DrawViewSymbol - e esquema, nao vista do 3D); PE-EL-02 PLANTA (vista de topo do
# 3D: eletrocalha + malha de aterramento + descidas de SPDA); PE-EL-03 QUADRO DE
# CARGAS + NOTAS. Eixos do build_eletrico: X=comprimento, Y=vao, Z=altura.
#
# Roda em DOIS contextos: FORA do FreeCAD (config_de_spec, codigo_fonte,
# script_bootstrap) e DENTRO (gerar_executivo/_entry + helpers com FreeCAD).
# ============================================================================
import os

from techdraw_exec import (
    _nova_prancha, _vista, _Cotador, _anot, _tabela, _bloco_texto,
    _carimbo, _fit_escala, _bbox, _fmt_m, _paper_half, _svg_para_png, AREA_1V)


def _carimbo_elet(cfg, titulo, numero, escala, folha):
    """Carimbo do eletrico: corrige os defaults ESTRUTURAIS do carimbo generico
    (material/norma/tipo/depto). Sem isso a prancha eletrica sairia com
    'ACO MR250' / 'NBR 8800' e, no rodape, 'PROJETO EXECUTIVO ESTRUTURAL' /
    'ESTRUTURAS' (mesma classe do vazamento de material; as demais disciplinas
    -- hid/inc/cli/coord -- ja sobrescrevem tipo+depto)."""
    car = _carimbo(cfg, titulo, numero, escala, folha)
    car["part_material"] = cfg.get("carimbo_material", "BT 380V")
    car["general_tolerances"] = "NBR 5410/5419"
    car["document_type"] = "PROJETO ELETRICO"
    car["responsible_department"] = "ELETRICA"
    return car


# ─────────────────────────────────────────────────────────────────────────
# PRANCHAS (rodam dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def _pr_unifilar(doc, cfg):
    """PE-EL-01 - DIAGRAMA UNIFILAR: embute o SVG (desenho_eletrico) como
    TechDraw::DrawViewSymbol na prancha A1."""
    page = _nova_prancha(doc, "PE01_UNIFILAR",
                         _carimbo_elet(cfg, "DIAGRAMA UNIFILAR GERAL", "PE-EL-01",
                                       "S/ESC", "01/04"))
    sym = doc.addObject("TechDraw::DrawViewSymbol", "UNIFILAR")
    sym.Symbol = cfg["unifilar_svg"]
    page.addView(sym)
    try:
        sym.X = 420.0                     # centro da A1 (841 x 594 mm)
        sym.Y = 300.0
        sym.Scale = 8.0                   # o SVG (940x640) preenche ~570x390 mm
    except Exception:
        pass
    return [page], []


def _pr_planta_instalacao(doc, cfg):
    """PE-EL-02 - PLANTA DE ILUMINACAO E TOMADAS: embute o SVG (desenho_eletrico.
    planta_eletrica_svg) com os pontos de luz, tomadas, interruptores, QGF e os
    circuitos (ilum/TUG separados, NBR 5410 4.2.5.5). E' a planta de INSTALACAO
    (leiaute dos pontos), complementar a planta de eletrocalhas/aterramento (PE-EL-03)."""
    page = _nova_prancha(doc, "PE02_PLANTA_INST",
                         _carimbo_elet(cfg, "PLANTA DE ILUMINACAO E TOMADAS", "PE-EL-02",
                                       "S/ESC", "02/04"))
    sym = doc.addObject("TechDraw::DrawViewSymbol", "PLANTA_INST")
    sym.Symbol = cfg["planta_eletrica_svg"]
    page.addView(sym)
    try:
        sym.X = 420.0
        sym.Y = 300.0
        sym.Scale = 6.5                   # o SVG (1180x760) preenche ~a folha util
    except Exception:
        pass
    return [page], []


def _pr_planta(doc, cfg, objs):
    """PE-EL-03 - PLANTA DE ELETROCALHAS + ATERRAMENTO/SPDA: vista de topo do 3D
    (eletrocalha, anel de aterramento, hastes e descidas), cotada no comprimento
    e no vao. Complementa a planta de instalacao (PE-EL-02)."""
    g = cfg["geo"]
    bb = _bbox(objs)
    esc, nome = _fit_escala(bb, "z", *AREA_1V)
    page = _nova_prancha(doc, "PE03_PLANTA_INFRA",
                         _carimbo_elet(cfg, "PLANTA - ELETROCALHAS E ATERRAMENTO",
                                       "PE-EL-03", nome, "03/04"))
    v = _vista(doc, page, "V02_PLANTA", objs, (0, 0, 1), (1, 0, 0),
               esc, 410, 350, coarse=True)
    hw, hh = _paper_half(bb, esc, "z")
    c = _Cotador(doc, page, v, hw, hh)
    L, W = g["L"], g["W"]                 # mm (geo em mm)
    z = bb.ZMax
    c.d((0.0, 0.0, z), (L, 0.0, z), "DistanceX", _fmt_m(L), "baixo")   # _fmt_m espera mm
    c.d((0.0, 0.0, z), (0.0, W, z), "DistanceY", _fmt_m(W), "esq")
    _anot(doc, page, "A02",
          ["PLANTA - ELETROCALHAS E ATERRAMENTO   ESCALA %s" % nome,
           "Eletrocalha principal sob o beiral; anel de aterramento no perimetro",
           "(cabo Cu 50 mm2) + hastes de canto; descidas de SPDA nas colunas.",
           "Cotas em metros."],
          200, 74, 6)
    return [page], [c]


def _pr_quadros(doc, cfg):
    """PE-EL-04 - QUADRO DE CARGAS + NOTAS."""
    page = _nova_prancha(doc, "PE04_QUADROS",
                         _carimbo_elet(cfg, "QUADRO DE CARGAS E ESPECIFICACOES",
                                       "PE-EL-04", "-", "04/04"))
    # views ancoradas pelo CENTRO -> x=420 centraliza na folha A1 (841 mm), em vez de
    # x=175 (encostado a esquerda, deixando ~2/3 da folha vazios). escala 1,5 p/ legibilidade.
    _anot(doc, page, "A03q", ["QUADRO DE CARGAS"], 420, 520, 8)
    _tabela(doc, page, "Q03C", cfg["quadro_cargas_hdr"], cfg["quadro_cargas"],
            420, 480, tam=6, larguras=[190, 150, 110, 100], escala=1.4)
    # QDC - Quadro de Distribuicao de Circuitos (por circuito: secao/disjuntor/eletroduto)
    if cfg.get("qdc_rows"):
        _anot(doc, page, "A03qdc", ["QUADRO DE DISTRIBUICAO DE CIRCUITOS (QDC)"], 420, 380, 7)
        _tabela(doc, page, "Q03QDC", cfg["qdc_hdr"], cfg["qdc_rows"],
                420, 340, tam=5, larguras=[85, 55, 35, 65, 55, 65, 50, 55, 40], escala=1.2)
    _bloco_texto(doc, page, "N03", cfg["notas"], 420, 150, tam=5, largura=580,
                 escala=1.35)
    return [page], []


# ─────────────────────────────────────────────────────────────────────────
# ORQUESTRACAO (dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def gerar_executivo_eletrico(cfg):
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

    doc = App.openDocument(cfg["fcstd"])
    objs = [o for o in doc.Objects if o.TypeId == "Part::Feature"
            and hasattr(o, "Shape") and not o.Shape.isNull()]
    for nome in [o.Name for o in doc.Objects
                 if o.TypeId.startswith("TechDraw::") or o.TypeId == "Spreadsheet::Sheet"]:
        if doc.getObject(nome) is not None:
            try:
                doc.removeObject(nome)
            except Exception:
                pass

    paginas, cotadores = [], []
    for fn, args in ((_pr_unifilar, ()), (_pr_planta_instalacao, ()),
                     (_pr_planta, (objs,)), (_pr_quadros, ())):
        try:
            pgs, cts = fn(doc, cfg, *args)
            paginas += pgs
            cotadores += cts
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
    for c in cotadores:
        try:
            c.aplica()
        except Exception:
            pass
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
    fcstd_out = os.path.join(out, "executivo_eletrico.FCStd")
    try:
        doc.saveAs(fcstd_out)
    except Exception:
        pass
    return {"ok": True, "pranchas": [p.Name for p in paginas],
            "arquivos": arquivos, "fcstd": fcstd_out}


def _entry_eletrico(cfg):
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
        res = gerar_executivo_eletrico(cfg)
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
def config_de_spec(r, fcstd_path, out_dir, spec=None):
    """Monta o cfg (dados JA computados) a partir do resultado de
    galpao_eletrico.rodar(r) + o FCStd do build_eletrico. O SVG do unifilar e do
    quadro sao gerados AQUI (desenho_eletrico) e injetados como string - nada e
    recalculado dentro do FreeCAD."""
    import desenho_eletrico as de
    spec = spec or {}
    g = r["gates"]
    geo = r.get("geometria") or {"L": 40.0, "W": 20.0, "H": 6.0}
    V = r["spec"]["tensao_V"]

    import instalacao_eletrica as ie
    unifilar_svg = de.diagrama_unifilar_svg(r)
    planta_eletrica_svg = de.planta_eletrica_svg(r)   # leiaute ilum/tomadas (instalacao_eletrica)

    # QDC - Quadro de Distribuicao de Circuitos (dimensionamento por circuito)
    inst = ie.projeto_instalacao(r)
    qdc_hdr = ["CIRCUITO", "TIPO", "PTS", "POT (VA)", "IB (A)", "SECAO", "DISJ", "ELETRO.", "dV%"]
    qdc_rows = [[d["circuito"], d["tipo"][:4].upper(), "%d" % d["n_pontos"],
                 "%.0f" % d["potencia_VA"], "%.1f" % d["IB_A"], "%s mm2" % d["secao_mm2"],
                 "%s A" % d["disjuntor_A"], "o%s" % d["eletroduto_mm"],
                 "%.1f" % (d["queda_pct"] or 0.0)] for d in inst.get("qdc", [])]

    quadro_cargas_hdr = ["CIRCUITO", "DEMANDA", "CONDUTOR", "PROTECAO"]
    quadro_cargas = [["Alimentador geral (QGF)", "%.0f kVA" % g["cargas"]["D_kVA"],
                      "%s mm2" % g["alimentador"]["secao_mm2"],
                      "%s A" % g["protecao"]["IN_geral_A"]]]
    for grp, d in r["cargas"]["por_grupo"].items():
        quadro_cargas.append([grp, "%.1f kW" % d["D_kW"], "-", "-"])
    if g["fator_potencia"]["precisa_corrigir"]:
        quadro_cargas.append(["Banco de capacitores",
                              "%.0f kVAr" % g["fator_potencia"]["Qc_kVAr"], "-", "-"])

    # carimbo: BT (+ MT se subestacao)
    carimbo_mat = "BT %gV" % V
    if g["subestacao"]["necessaria"]:
        carimbo_mat = "MT %g kV / BT %g V" % (r["subestacao"]["V_primaria_kV"], V)

    icc_txt = ("%g kA" % g["curto"]["Icc_kA"]) if g["curto"]["Icc_kA"] else "A CONFIRMAR"
    at_txt = ("%g ohm" % g["aterramento"]["R_ohm"]) if g["aterramento"]["R_ohm"] else "A CONFIRMAR"
    notas = [
        "NOTAS TECNICAS E ESPECIFICACOES",
        "1. Tensao de distribuicao: %g V, %s. Fornecimento: %s." % (
            V, r["spec"]["sistema"], r["spec"]["origem"].replace("_", " ")),
        "2. Alimentador do QGF: %s mm2 (%s) ; queda de tensao %s%%." % (
            g["alimentador"]["secao_mm2"], g["alimentador"]["isolacao"],
            g["alimentador"]["dv_pct"]),
        "3. Protecao geral: disjuntor %s A ; DPS classe %s ; Icc presumida = %s." % (
            g["protecao"]["IN_geral_A"], g["protecao"]["dps_classe"], icc_txt),
        "4. Correcao de fator de potencia: %s -> %s (banco %s kVAr)." % (
            g["fator_potencia"]["fp_atual"], g["fator_potencia"]["fp_alvo"],
            g["fator_potencia"]["Qc_kVAr"]),
    ]
    if g["subestacao"]["necessaria"]:
        notas.append("5. Subestacao: trafo %g kVA %g/%g kV ; protecao %s (NBR 14039)." % (
            r["subestacao"]["Sn_kVA"], r["subestacao"]["V_primaria_kV"],
            V / 1000.0, r["subestacao"]["protecao"]["tipo"].replace("_", " ")))
    if g["luminotecnica"]["E_lux"]:
        notas.append("5b. Iluminacao (metodo dos lumens, NBR ISO/CIE 8995-1): "
                     "E = %s lux ; %s luminarias ; %s kW (%s W/m2)." % (
                         g["luminotecnica"]["E_lux"], g["luminotecnica"]["N_luminarias"],
                         g["luminotecnica"]["P_kW"], g["luminotecnica"]["densidade_W_m2"]))
    notas += [
        "6. Aterramento: resistencia de terra = %s (limite 10 ohm, NBR 5419)." % at_txt,
        "7. SPDA: %s (NBR 5419-1/2/3)." % (
            "nivel de protecao %s, %s descidas" % (g["spda"]["NP"], g["spda"]["n_descidas"])
            if g["spda"]["NP"] else "A CONFIRMAR (estudo de risco NBR 5419-2)"),
        "8. Normas: NBR 5410, NBR 14039, NBR 5419, NBR 15749.",
        "Dados de sitio (rho do solo, demanda contratada, R1) A CONFIRMAR - ver memoria.",
    ]

    return {
        "fcstd": str(fcstd_path).replace("\\", "/"),
        "out": str(out_dir).replace("\\", "/"),
        "slug": spec.get("slug", "galpao_eletrico"),
        "descricao": spec.get("descricao", "Galpao industrial - Projeto Eletrico"),
        "autor": spec.get("autor", "galpao_fw"),
        "geo": {"L": geo["L"] * 1000.0, "W": geo["W"] * 1000.0, "H": geo["H"] * 1000.0},
        "unifilar_svg": unifilar_svg,
        "planta_eletrica_svg": planta_eletrica_svg,
        "qdc_hdr": qdc_hdr, "qdc_rows": qdc_rows,
        "quadro_cargas_hdr": quadro_cargas_hdr, "quadro_cargas": quadro_cargas,
        "carimbo_material": carimbo_mat,
        "notas": notas,
        "materiais": None,
    }


def codigo_fonte():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "techdraw_eletrico.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _para_nativo(o):
    import techdraw_exec as TE
    return TE._para_nativo(o)


def script_bootstrap(cfg):
    """Script que o freecad.exe roda: prepende o dir do galpao_fw no sys.path,
    injeta cfg + a fonte, e dispara _entry_eletrico via QTimer. O SVG do unifilar
    ja vem pronto em cfg (desenho_eletrico rodou fora)."""
    galpao_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
    return ("# -*- coding: utf-8 -*-\n"
            "import sys\n"
            "if %r not in sys.path: sys.path.insert(0, %r)\n" % (galpao_dir, galpao_dir)
            + "_CFG_ = %r\n" % (_para_nativo(cfg),)
            + codigo_fonte()
            + "\nfrom PySide import QtCore\n"
            "QtCore.QTimer.singleShot(1500, lambda: _entry_eletrico(_CFG_))\n")
