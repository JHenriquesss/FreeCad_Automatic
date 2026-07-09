# ============================================================================
# techdraw_exec.py - PROJETO EXECUTIVO via TechDraw (headless, freecad.exe)
# ----------------------------------------------------------------------------
# Gera o conjunto completo de pranchas A1 (ISO 5457) a partir do modelo 3D
# JA SALVO (.FCStd). Roda dentro do freecad.exe (GUI disponivel -> export PDF),
# mas sem interacao: o job e disparado por QTimer, a pagina e aberta na MDI
# para construir a cena grafica, e a janela fecha sozinha ao terminar.
#
# Descobertas que moldam este modulo (validadas ao vivo, FreeCAD 1.1.1):
#   * freecadcmd (console) NAO exporta PDF: "Cannot load Gui module".
#   * freecad.exe roda script no startup COM Gui -> exportPageAsPdf funciona.
#   * export so tem conteudo se a cena for construida: preciso abrir a MDI da
#     page (page.ViewObject.doubleClicked()) e chamar Gui.updateGui() antes.
#   * HLR (DrawViewPart) e caro por solido; o modelo tem ~569. Por isso NENHUMA
#     vista projeta o modelo inteiro em HLR: vistas de contexto usam CoarseView
#     (silhueta, rapida) e vistas de detalhe usam HLR em subconjuntos pequenos.
#   * Cotas: DrawViewDimension ancorada em vertices cosmeticos 3D projetados;
#     os vertices entram no fim da lista da vista, indices previsiveis.
#
# Este arquivo roda em DOIS contextos:
#   - FORA do FreeCAD: config_de_spec(), codigo_fonte(), script_bootstrap().
#   - DENTRO do freecad.exe: gerar_executivo() e helpers (importam FreeCAD/Gui).
# ============================================================================
import os

TPL_REL = ("Mod", "TechDraw", "Templates", "ISO",
           "A1_Landscape_ISO5457_advanced.svg")

# Miudezas: poluem e encarecem as vistas gerais; entram so nos detalhes.
_MIUDEZAS = ("PORCA", "ARRUELA", "CLIPE", "CONEX", "CHUMBADOR", "ESTICADOR")


# ─────────────────────────────────────────────────────────────────────────
# HELPERS DE GEOMETRIA (rodam dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def _bbox(objs):
    bb = None
    for o in objs:
        if hasattr(o, "Shape") and not o.Shape.isNull():
            b = o.Shape.BoundBox
            bb = b if bb is None else bb.united(b)
    return bb


def _pref(objs, prefixos):
    return [o for o in objs if any(o.Label.startswith(p) for p in prefixos)]


def _cx(o):
    b = o.Shape.BoundBox
    return (b.XMin + b.XMax) / 2.0


def _cy(o):
    b = o.Shape.BoundBox
    return (b.YMin + b.YMax) / 2.0


def _faixa(objs, eixo, centro, meia):
    """Objetos cujo centro do bbox cai em [centro +- meia] no eixo x|y."""
    f = _cx if eixo == "x" else _cy
    return [o for o in objs
            if hasattr(o, "Shape") and not o.Shape.isNull()
            and abs(f(o) - centro) <= meia]


# ─────────────────────────────────────────────────────────────────────────
# HELPERS DE PRANCHA (rodam dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def _tpl_path():
    import FreeCAD as App
    return os.path.join(App.getResourceDir(), *TPL_REL)


def _nova_prancha(doc, nome, campos):
    page = doc.addObject("TechDraw::DrawPage", nome)
    tpl = doc.addObject("TechDraw::DrawSVGTemplate", nome + "_tpl")
    tpl.Template = _tpl_path()
    et = tpl.EditableTexts
    for k, v in campos.items():
        if k in et:
            et[k] = str(v)
    tpl.EditableTexts = et
    page.Template = tpl
    return page


def _vista(doc, page, nome, fontes, direcao, xdir, escala, x, y, coarse=False):
    import FreeCAD as App
    if not fontes:
        return None
    v = doc.addObject("TechDraw::DrawViewPart", nome)
    v.Source = list(fontes)
    v.Direction = App.Vector(*direcao)
    if xdir is not None:
        v.XDirection = App.Vector(*xdir)
    v.ScaleType = "Custom"
    v.Scale = escala
    v.CoarseView = bool(coarse)
    page.addView(v)
    v.X, v.Y = float(x), float(y)
    return v


def _n_verts(view):
    i = 0
    while True:
        try:
            if view.getVertexByIndex(i) is None:
                break
        except Exception:
            break
        i += 1
    return i


def _paper_half(bbox, scale, axis):
    """Meia-largura/altura da vista NO PAPEL (mm), conforme o eixo de projecao.
    axis: 'z' (planta), 'x' (olha ao longo de X), 'y' (olha ao longo de Y)."""
    if bbox is None:
        return 100.0, 100.0
    if axis == "z":
        w, h = bbox.XLength, bbox.YLength
    elif axis == "x":
        w, h = bbox.YLength, bbox.ZLength
    else:  # 'y'
        w, h = bbox.XLength, bbox.ZLength
    return abs(w) * scale / 2.0, abs(h) * scale / 2.0


class _Cotador:
    """Cotas TechDraw ancoradas em pontos 3D. Registradas na montagem e
    aplicadas em lote apos o 1o recompute (vista ja projetada).

    Posiciona cada cota para NAO sobrepor: horizontais empilhadas abaixo da
    peca, verticais empilhadas a esquerda, com passo constante. As posicoes
    (dim.X, dim.Y) sao em mm de papel, origem no centro da vista."""

    MARGEM = 14.0
    PASSO = 11.0

    def __init__(self, doc, page, view, halfw=100.0, halfh=100.0):
        self.doc, self.page, self.view = doc, page, view
        self.halfw, self.halfh = halfw, halfh
        self.itens = []

    def d(self, p1, p2, tipo="Distance", valor=None):
        """Registra uma cota. valor (mm): se dado, fixa o rotulo nesse numero
        (evita ambiguidade do esquema de unidades e cota o valor de projeto)."""
        if self.view is not None:
            self.itens.append((p1, p2, tipo, valor))
        return self

    def aplica(self):
        import FreeCAD as App
        if self.view is None or not self.itens:
            return
        for it in self.itens:
            self.view.makeCosmeticVertex3d(App.Vector(*it[0]))
            self.view.makeCosmeticVertex3d(App.Vector(*it[1]))
        self.view.recompute()
        base = _n_verts(self.view) - 2 * len(self.itens)
        iv = ih = 0
        for j, it in enumerate(self.itens):
            p1, p2, tipo, valor = it
            try:
                dm = self.doc.addObject("TechDraw::DrawViewDimension",
                                        self.view.Name + "_dim")
                dm.Type = tipo
                dm.References2D = [(self.view, "Vertex%d" % (base + 2 * j)),
                                   (self.view, "Vertex%d" % (base + 2 * j + 1))]
                # Arbitrary=True -> FormatSpec e exibido literalmente. Cotamos o
                # valor de PROJETO (mm inteiros), inequivoco e sem depender do
                # esquema de unidades (que exibia vao em metros: "10" p/ 10000).
                if valor is not None:
                    dm.Arbitrary = True
                    dm.FormatSpec = "%d" % int(round(valor))
                else:
                    dm.FormatSpec = "%.0f"
                self.page.addView(dm)
                if tipo == "DistanceY":       # vertical -> a esquerda
                    dm.X = -(self.halfw + self.MARGEM + iv * self.PASSO)
                    dm.Y = 0.0
                    iv += 1
                else:                          # horizontal -> abaixo
                    dm.X = 0.0
                    dm.Y = -(self.halfh + self.MARGEM + ih * self.PASSO)
                    ih += 1
                try:
                    dm.ViewObject.Fontsize = 5.0
                    dm.ViewObject.ArrowSize = 2.5
                except Exception:
                    pass
            except Exception:
                pass


def _anot(doc, page, nome, linhas, x, y, tam=4.0):
    a = doc.addObject("TechDraw::DrawViewAnnotation", nome)
    a.Text = linhas if isinstance(linhas, list) else [linhas]
    a.TextSize = tam
    page.addView(a)
    a.X, a.Y = float(x), float(y)
    return a


def _planilha(doc, page, nome, celulas, cell_end, x, y, tam=3.5):
    ss = doc.addObject("Spreadsheet::Sheet", nome + "_ss")
    for addr, val in celulas.items():
        ss.set(addr, str(val))
    doc.recompute()
    v = doc.addObject("TechDraw::DrawViewSpreadsheet", nome)
    v.Source = ss
    v.CellStart = "A1"
    v.CellEnd = cell_end
    v.TextSize = tam
    page.addView(v)
    v.X, v.Y = float(x), float(y)
    return v


# ─────────────────────────────────────────────────────────────────────────
# CARIMBO
# ─────────────────────────────────────────────────────────────────────────
def _carimbo(cfg, titulo, numero, escala, folha):
    import datetime
    return {
        "title": titulo,
        "supplementary_title_1": cfg.get("descricao", ""),
        "supplementary_title_2": "",
        "drawing_number": numero,
        "scale": escala,
        "sheet_number": folha,
        "date_of_issue": datetime.date.today().strftime("%d/%m/%Y"),
        "creator": cfg.get("autor", "galpao_fw"),
        "approval_person": "",
        "legal_owner_1": cfg.get("slug", "galpao"),
        "legal_owner_2": "", "legal_owner_3": "", "legal_owner_4": "",
        "document_type": "PROJETO EXECUTIVO ESTRUTURAL",
        "document_status": "PARA APROVACAO",
        "revision_index": "00",
        "language_code": "PT",
        "responsible_department": "ESTRUTURAS",
        "general_tolerances": "NBR 8800 / NBR 6118",
        "part_material": "ACO MR250 / CONCRETO fck 25 MPa",
    }


# ─────────────────────────────────────────────────────────────────────────
# PRANCHAS
# ─────────────────────────────────────────────────────────────────────────
def _pr_cobertura(doc, cfg, objs):
    g = cfg["geo"]
    page = _nova_prancha(doc, "PE01_COBERTURA",
                         _carimbo(cfg, "PLANTA DE COBERTURA", "PE-01",
                                  "1:100", "01/09"))
    bb = _bbox(objs)
    v = _vista(doc, page, "V01_COB", objs, (0, 0, 1), (1, 0, 0),
               1 / 100.0, 420, 320, coarse=True)
    hw, hh = _paper_half(bb, 1 / 100.0, "z")
    c = _Cotador(doc, page, v, hw, hh)
    z = bb.ZMax
    comp, span, bay = g["comprimento"], g["span"], g.get("bay")
    c.d((0, 0, z), (comp, 0, z), "DistanceX", comp)      # comprimento
    c.d((0, 0, z), (0, span, z), "DistanceY", span)      # vao
    if bay:
        c.d((0, span, z), (bay, span, z), "DistanceX", bay)  # 1 vao de baia
    _anot(doc, page, "A01", ["PLANTA DE COBERTURA   ESC 1:100",
                             "Inclinacao: %.0f%%" % (g.get("slope", 0.1) * 100)],
          200, 120, 5)
    return [page], [c]


def _pr_fundacoes(doc, cfg, objs):
    page = _nova_prancha(doc, "PE02_FUNDACOES",
                         _carimbo(cfg, "PLANTA DE FUNDACOES", "PE-02",
                                  "1:100", "02/09"))
    fund = _pref(objs, ("SAPATA", "PEDESTAL", "PLACA"))
    if not fund:
        return [page], []
    bf = _bbox(fund)
    v = _vista(doc, page, "V02_FUND", fund, (0, 0, 1), (1, 0, 0),
               1 / 100.0, 400, 330, coarse=True)
    g = cfg["geo"]
    hw, hh = _paper_half(bf, 1 / 100.0, "z")
    c = _Cotador(doc, page, v, hw, hh)
    z = bf.ZMax
    comp, span = g["comprimento"], g["span"]
    c.d((0, 0, z), (comp, 0, z), "DistanceX", comp)      # entre eixos (comp)
    c.d((0, 0, z), (0, span, z), "DistanceY", span)      # entre eixos (vao)
    sap = _pref(fund, ("SAPATA",))
    if sap:
        b1 = sap[0].Shape.BoundBox
        c.d((b1.XMin, b1.YMin, b1.ZMax), (b1.XMax, b1.YMin, b1.ZMax),
            "DistanceX", b1.XLength)                     # B da sapata
        c.d((b1.XMin, b1.YMin, b1.ZMax), (b1.XMin, b1.YMax, b1.ZMax),
            "DistanceY", b1.YLength)                     # L da sapata
    sp = cfg.get("sapata")
    if sp:
        _planilha(doc, page, "Q02", {
            "A1": "SAPATA", "B1": "B (m)", "C1": "L (m)", "D1": "h (m)",
            "A2": "S1", "B2": "%.2f" % sp["B"], "C2": "%.2f" % sp["L"],
            "D2": "%.2f" % sp["h"]}, "D2", 150, 180, 4)
    _anot(doc, page, "A02", ["PLANTA DE FUNDACOES   ESC 1:100"], 200, 120, 5)
    return [page], [c]


def _pr_elevacoes(doc, cfg, objs):
    g = cfg["geo"]
    page = _nova_prancha(doc, "PE03_ELEVACOES",
                         _carimbo(cfg, "ELEVACOES", "PE-03", "1:100", "03/09"))
    bb = _bbox(objs)
    comp_x = (bb.XLength >= bb.YLength)
    # oitao: olha ao longo do comprimento
    dfr = (-1, 0, 0) if comp_x else (0, -1, 0)
    xfr = (0, -1, 0) if comp_x else (1, 0, 0)
    v1 = _vista(doc, page, "V03_OITAO", objs, dfr, xfr, 1 / 100.0,
                230, 380, coarse=True)
    span, comp = g["span"], g["comprimento"]
    hw1, hh1 = _paper_half(bb, 1 / 100.0, "x" if comp_x else "y")
    c1 = _Cotador(doc, page, v1, hw1, hh1)
    # oitao: vao na horizontal, alturas eave/cumeeira
    if comp_x:
        c1.d((0, 0, 0.0), (0, span, 0.0), "DistanceX", span)
    else:
        c1.d((0, 0, 0.0), (span, 0, 0.0), "DistanceX", span)
    c1.d((0, 0, 0.0), (0, 0, g["eave"]), "DistanceY", g["eave"])
    c1.d((0, 0, 0.0), (0, 0, g["ridge"]), "DistanceY", g["ridge"])
    # lateral
    dlt = (0, -1, 0) if comp_x else (-1, 0, 0)
    xlt = (1, 0, 0) if comp_x else (0, -1, 0)
    v2 = _vista(doc, page, "V03_LATERAL", objs, dlt, xlt, 1 / 100.0,
                560, 380, coarse=True)
    bay = g.get("bay")
    hw2, hh2 = _paper_half(bb, 1 / 100.0, "y" if comp_x else "x")
    c2 = _Cotador(doc, page, v2, hw2, hh2)
    # lateral: comprimento total + 1 baia, altura eave
    if comp_x:
        c2.d((0, 0, 0.0), (comp, 0, 0.0), "DistanceX", comp)
        if bay:
            c2.d((0, 0, 0.0), (bay, 0, 0.0), "DistanceX", bay)
    else:
        c2.d((0, 0, 0.0), (0, comp, 0.0), "DistanceX", comp)
        if bay:
            c2.d((0, 0, 0.0), (0, bay, 0.0), "DistanceX", bay)
    c2.d((0, 0, 0.0), (0, 0, g["eave"]), "DistanceY", g["eave"])
    _anot(doc, page, "A03a", ["ELEVACAO FRONTAL (OITAO)  1:100"], 230, 170, 5)
    _anot(doc, page, "A03b", ["ELEVACAO LATERAL  1:100"], 560, 170, 5)
    return [page], [c1, c2]


def _pr_portico(doc, cfg, objs):
    g = cfg["geo"]
    page = _nova_prancha(doc, "PE04_PORTICO",
                         _carimbo(cfg, "PORTICO TIPICO", "PE-04",
                                  "1:50", "04/09"))
    bb = _bbox(objs)
    comp_x = (bb.XLength >= bb.YLength)
    eixo = "x" if comp_x else "y"
    meio = (bb.XMin + bb.XMax) / 2 if comp_x else (bb.YMin + bb.YMax) / 2
    bay = g.get("bay") or 5000.0
    frame = _faixa(_pref(objs, ("PORTICO", "NERVURA", "MAO", "PLACA",
                                "PEDESTAL", "SAPATA")),
                   eixo, meio, bay * 0.45)
    if not frame:
        frame = objs
    dv = (-1, 0, 0) if comp_x else (0, -1, 0)
    xv = (0, -1, 0) if comp_x else (1, 0, 0)
    v = _vista(doc, page, "V04_PORTICO", frame, dv, xv, 1 / 50.0, 420, 330)
    fb = _bbox(frame)
    span = g["span"]
    # eixo do portico (linha do frame) no eixo perpendicular ao vao
    linha = meio
    hw, hh = _paper_half(fb, 1 / 50.0, "x" if comp_x else "y")
    c = _Cotador(doc, page, v, hw, hh)
    # vao entre eixos de coluna (nao o bbox, que inclui sapatas); alturas em z0
    if comp_x:
        c.d((linha, 0, 0.0), (linha, span, 0.0), "DistanceX", span)
    else:
        c.d((0, linha, 0.0), (span, linha, 0.0), "DistanceX", span)
    ax = (linha, 0, 0.0) if comp_x else (0, linha, 0.0)
    ae = (linha, 0, g["eave"]) if comp_x else (0, linha, g["eave"])
    ar = (linha, 0, g["ridge"]) if comp_x else (0, linha, g["ridge"])
    c.d(ax, ae, "DistanceY", g["eave"])
    c.d(ax, ar, "DistanceY", g["ridge"])
    _anot(doc, page, "A04", [
        "PORTICO TIPICO   ESC 1:50",
        "Colunas: %s   Vigas: %s" % (cfg.get("perfil_col", "?"),
                                     cfg.get("perfil_raf", "?"))],
          200, 130, 4.5)
    return [page], [c]


def _pr_contravent(doc, cfg, objs):
    page = _nova_prancha(doc, "PE05_CONTRAVENTAMENTO",
                         _carimbo(cfg, "CONTRAVENTAMENTOS", "PE-05",
                                  "1:100", "05/09"))
    cv = _pref(objs, ("CONTRAV", "ESTICADOR", "TIRANTE", "PORTICO"))
    if not _pref(objs, ("CONTRAV", "TIRANTE")):
        return [page], []
    bb = _bbox(objs)
    comp_x = (bb.XLength >= bb.YLength)
    dlt = (0, -1, 0) if comp_x else (-1, 0, 0)
    xlt = (1, 0, 0) if comp_x else (0, -1, 0)
    _vista(doc, page, "V05_CV_LAT", cv, dlt, xlt, 1 / 100.0, 300, 400, coarse=True)
    _vista(doc, page, "V05_CV_COB", _pref(objs, ("CONTRAV", "TIRANTE", "PORTICO")),
           (0, 0, 1), (1, 0, 0), 1 / 100.0, 300, 180, coarse=True)
    _anot(doc, page, "A05a", ["CONTRAVENTAMENTO VERTICAL  1:100"], 200, 300, 5)
    _anot(doc, page, "A05b", ["CONTRAVENTAMENTO DE COBERTURA  1:100"], 200, 90, 5)
    return [page], []


def _pr_base(doc, cfg, objs, todos):
    page = _nova_prancha(doc, "PE06_DET_BASE",
                         _carimbo(cfg, "DETALHE - BASE DE COLUNA", "PE-06",
                                  "1:10", "06/09"))
    # usa 'todos' (inclui chumbadores/porcas/arruelas, que sao miudezas
    # excluidas das vistas gerais) para o detalhe mostrar a ancoragem.
    base = _pref(todos, ("PLACA", "CHUMBADOR", "PEDESTAL", "PORCA", "ARRUELA"))
    if not base:
        return [page], []
    b0 = base[0].Shape.BoundBox
    cx, cy = (b0.XMin + b0.XMax) / 2, (b0.YMin + b0.YMax) / 2
    um = _faixa(_faixa(base, "x", cx, 500), "y", cy, 500)
    um = um or base[:6]
    db = _bbox(um)
    # vista frontal
    v1 = _vista(doc, page, "V06_BASE_FR", um, (0, -1, 0), (1, 0, 0),
                1 / 10.0, 300, 350)
    hw1, hh1 = _paper_half(db, 1 / 10.0, "y")
    c1 = _Cotador(doc, page, v1, hw1, hh1)
    c1.d((db.XMin, db.YMin, db.ZMin), (db.XMin, db.YMin, db.ZMax),
         "DistanceY", db.ZLength)
    c1.d((db.XMin, db.YMin, db.ZMax), (db.XMax, db.YMin, db.ZMax),
         "DistanceX", db.XLength)
    # vista superior (placa + furos)
    v2 = _vista(doc, page, "V06_BASE_TOP", _pref(um, ("PLACA", "CHUMBADOR")),
                (0, 0, 1), (1, 0, 0), 1 / 10.0, 560, 350)
    pb = _bbox(_pref(um, ("PLACA",)) or um)
    hw2, hh2 = _paper_half(pb, 1 / 10.0, "z")
    c2 = _Cotador(doc, page, v2, hw2, hh2)
    c2.d((pb.XMin, pb.YMin, pb.ZMax), (pb.XMax, pb.YMin, pb.ZMax),
         "DistanceX", pb.XLength)
    c2.d((pb.XMin, pb.YMin, pb.ZMax), (pb.XMin, pb.YMax, pb.ZMax),
         "DistanceY", pb.YLength)
    ba = cfg.get("base")
    if ba:
        _anot(doc, page, "A06", [
            "DETALHE DA BASE   ESC 1:10",
            "Placa %.0fx%.0fx%.0f mm" % (ba["B"], ba["L"], ba["t"]),
            "%dx chumbadores d%.0f mm" % (ba["n"], ba["db"])],
              180, 150, 4.5)
    return [page], [c1, c2]


def _pr_joelho(doc, cfg, objs, todos):
    page = _nova_prancha(doc, "PE07_DET_JOELHO",
                         _carimbo(cfg, "DETALHE - LIGACAO JOELHO/CUMEEIRA",
                                  "PE-07", "1:10", "07/09"))
    g = cfg["geo"]
    bb = _bbox(objs)
    comp_x = (bb.XLength >= bb.YLength)
    eixo = "x" if comp_x else "y"
    meio = (bb.XMin + bb.XMax) / 2 if comp_x else (bb.YMin + bb.YMax) / 2
    bay = g.get("bay") or 5000.0
    # inclui miudezas (parafusos/chapas de ligacao CONEX) no detalhe do joelho
    frame = _faixa(todos, eixo, meio, bay * 0.45)
    # regiao do joelho: topo da coluna (z ~ eave)
    joelho = [o for o in frame
              if hasattr(o, "Shape") and not o.Shape.isNull()
              and o.Shape.BoundBox.ZMax >= g["eave"] - 800
              and o.Shape.BoundBox.ZMin <= g["eave"] + 800]
    if not joelho:
        return [page], []
    dv = (-1, 0, 0) if comp_x else (0, -1, 0)
    xv = (0, -1, 0) if comp_x else (1, 0, 0)
    v = _vista(doc, page, "V07_JOELHO", joelho, dv, xv, 1 / 10.0, 420, 320)
    _anot(doc, page, "A07", ["LIGACAO DE JOELHO   ESC 1:10",
                             "Ver quadro de ligacoes / memoria de calculo"],
          200, 130, 4.5)
    return [page], []


def _pr_fechamento(doc, cfg, objs):
    page = _nova_prancha(doc, "PE08_FECHAMENTO",
                         _carimbo(cfg, "FECHAMENTO / TERCAS / MAO-FRANCESA",
                                  "PE-08", "1:100", "08/09"))
    fch = _pref(objs, ("TERCA", "TAPAMENTO", "MAO", "MONTANTE", "TELHA",
                       "CALHA", "PORTICO"))
    if not _pref(objs, ("TERCA", "TAPAMENTO", "MAO")):
        return [page], []
    bb = _bbox(objs)
    comp_x = (bb.XLength >= bb.YLength)
    dlt = (0, -1, 0) if comp_x else (-1, 0, 0)
    xlt = (1, 0, 0) if comp_x else (0, -1, 0)
    _vista(doc, page, "V08_FECH", fch, dlt, xlt, 1 / 100.0, 420, 340, coarse=True)
    tc = cfg.get("terca")
    linhas = ["FECHAMENTO E TERCAS   ESC 1:100"]
    if tc:
        linhas.append("Terca Ue %s" % tc)
    _anot(doc, page, "A08", linhas, 200, 140, 4.5)
    return [page], []


def _pr_quadros(doc, cfg):
    page = _nova_prancha(doc, "PE09_QUADROS",
                         _carimbo(cfg, "QUADROS E NOTAS TECNICAS", "PE-09",
                                  "-", "09/09"))
    # verificacoes
    res = [(k, v) for k, v in (cfg.get("resultados") or {}).items()
           if v is not None]
    if res:
        cel = {"A1": "ELEMENTO", "B1": "UTILIZACAO", "C1": "SITUACAO"}
        for i, (k, v) in enumerate(res, start=2):
            cel["A%d" % i] = k
            cel["B%d" % i] = "%.2f" % float(v)
            cel["C%d" % i] = "OK" if float(v) <= 1.001 else "REVER"
        _planilha(doc, page, "Q09V", cel, "C%d" % (len(res) + 1), 200, 400, 4)
        _anot(doc, page, "A09v", ["QUADRO DE VERIFICACOES (NBR 8800)"], 200, 470, 5)
    # materiais
    tk = [r for r in (cfg.get("takeoff") or []) if "Alvenaria" not in str(r[0])]
    if tk:
        tk = sorted(tk, key=lambda r: -float(r[4]))[:18]
        cel = {"A1": "ELEMENTO", "B1": "PERFIL", "C1": "QTDE", "D1": "MASSA kg"}
        tot = 0.0
        for i, r in enumerate(tk, start=2):
            cel["A%d" % i] = str(r[0]); cel["B%d" % i] = str(r[1])
            cel["C%d" % i] = str(r[2]); cel["D%d" % i] = "%.0f" % float(r[4])
            tot += float(r[4])
        n = len(tk) + 2
        cel["A%d" % n] = "TOTAL"; cel["D%d" % n] = "%.0f" % tot
        _planilha(doc, page, "Q09M", cel, "D%d" % n, 470, 400, 4)
        _anot(doc, page, "A09m", ["QUADRO DE MATERIAIS (ACO)"], 470, 470, 5)
    # notas
    notas = cfg.get("notas") or [
        "NOTAS TECNICAS GERAIS",
        "1. COTAS EM MM SALVO INDICACAO.",
        "2. RN +0,00 = TOPO DO CONCRETO (BASE DAS PLACAS).",
        "3. ACO ESTRUTURAL MR250 (NBR 8800). ARMADURA CA-50.",
        "4. CONCRETO fck 25 MPa. COBRIMENTO 5 cm (FUND.), 3 cm (SUP.).",
        "5. PARAFUSOS A325 (fub 825 MPa) OU A307 CONFORME LIGACAO.",
        "6. SOLDAS E70XX (fw 485 MPa). FILETE MINIMO 6 mm.",
        "7. CHUMBADORES ASTM A36 COM GANCHO 180 mm.",
        "8. CONTRAVENTAMENTO: BARRAS D20 PRETENSIONADAS C/ ESTICADOR.",
        "9. TERCAS Ue FORMADO A FRIO (NBR 14762).",
        "10. PROJETO EXECUTIVO SUJEITO A REVISAO E ART.",
    ]
    _anot(doc, page, "A09n", notas, 350, 200, 4)
    return [page], []


_BUILDERS = [
    ("modelo", _pr_cobertura),
    ("modelo", _pr_fundacoes),
    ("modelo", _pr_elevacoes),
    ("modelo", _pr_portico),
    ("modelo", _pr_contravent),
    ("modelo", _pr_base),
    ("modelo", _pr_joelho),
    ("modelo", _pr_fechamento),
    ("quadros", None),  # _pr_quadros (sem objs)
]


# ─────────────────────────────────────────────────────────────────────────
# ORQUESTRACAO (roda dentro do freecad.exe, disparada por QTimer)
# ─────────────────────────────────────────────────────────────────────────
def gerar_executivo(cfg):
    import FreeCAD as App
    import FreeCADGui as Gui

    # Esquema de unidades = Standard (mm): garante que as cotas exibam
    # milimetros inteiros com FormatSpec "%.0f" (evita metros -> "13" em vez
    # de "13000"). Schema 0 = Standard mm/kg/s.
    try:
        App.Units.setSchema(0)
    except Exception:
        pass

    out = os.path.join(cfg["out"], "pranchas")
    os.makedirs(out, exist_ok=True)

    doc = App.openDocument(cfg["fcstd"])
    todos = [o for o in doc.Objects
             if o.TypeId == "Part::Feature" and hasattr(o, "Shape")
             and not o.Shape.isNull()]
    objs = [o for o in todos
            if not any(o.Label.startswith(p) for p in _MIUDEZAS)]

    # remove pranchas/planilhas antigas (idempotente). Remover uma page apaga
    # em cascata template/views, invalidando outros itens do snapshot, entao
    # coletamos nomes e checamos existencia a cada passo.
    velhos = [o.Name for o in doc.Objects
              if o.TypeId.startswith("TechDraw::")
              or o.TypeId == "Spreadsheet::Sheet"]
    for nome in velhos:
        if doc.getObject(nome) is not None:
            try:
                doc.removeObject(nome)
            except Exception:
                pass

    paginas, cotadores = [], []
    construtores = [_pr_cobertura, _pr_fundacoes, _pr_elevacoes, _pr_portico,
                    _pr_contravent, _pr_base, _pr_joelho, _pr_fechamento]
    for fn in construtores:
        try:
            if fn in (_pr_base, _pr_joelho):
                pgs, cts = fn(doc, cfg, objs, todos)  # detalhes usam miudezas
            else:
                pgs, cts = fn(doc, cfg, objs)
            paginas += pgs
            cotadores += cts
        except Exception as ex:
            App.Console.PrintError("Prancha %s: %s\n" % (fn.__name__, ex))
    try:
        pgs, _ = _pr_quadros(doc, cfg)
        paginas += pgs
    except Exception as ex:
        App.Console.PrintError("Prancha quadros: %s\n" % ex)

    doc.recompute()                      # projeta todas as vistas

    # Assenta a geometria ANTES de ancorar cotas: abrir a page na MDI +
    # updateGui dispara um recompute da vista que renumera os vertices. Se as
    # cotas fossem criadas antes, os indices dos vertices cosmeticos mudariam
    # e as cotas mediriam vertices errados (bug observado: vao lia "13").
    import TechDrawGui
    import time
    arquivos = []
    for p in paginas:
        try:
            p.ViewObject.doubleClicked()
        except Exception:
            pass
    Gui.updateGui()
    time.sleep(1.0)
    Gui.updateGui()

    # Agora a geometria esta estavel: ancora as cotas (vertices cosmeticos no
    # fim da lista, indices previsiveis) e renderiza sem novo recompute de HLR.
    for c in cotadores:
        try:
            c.aplica()
        except Exception:
            pass
    doc.recompute()
    Gui.updateGui()
    time.sleep(0.3)
    Gui.updateGui()

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
            _svg_para_png(base + ".svg", base + ".png")  # preview raster
        except Exception:
            pass
        try:
            import TechDraw
            TechDraw.writeDXFPage(p, base + ".dxf")
            arquivos.append(base + ".dxf")
        except Exception:
            pass

    # salva FCStd das pranchas ao lado do modelo
    fcstd_out = os.path.join(out, "executivo.FCStd")
    try:
        doc.saveAs(fcstd_out)
    except Exception:
        pass

    return {"ok": True, "pranchas": [p.Name for p in paginas],
            "arquivos": arquivos, "fcstd": fcstd_out}


def _svg_para_png(svg_path, png_path, w=2100, h=1485):
    """Renderiza um SVG (A1) para PNG usando QtSvg (QApplication da GUI)."""
    try:
        from PySide import QtSvg, QtGui, QtCore
        r = QtSvg.QSvgRenderer(svg_path)
        img = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32)
        img.fill(QtGui.QColor(255, 255, 255))
        p = QtGui.QPainter(img)
        r.render(p, QtCore.QRectF(0, 0, w, h))
        p.end()
        img.save(png_path)
    except Exception:
        pass


def _entry(cfg):
    """Ponto unico chamado pelo bootstrap (via QTimer). Escreve status e fecha."""
    import json
    import FreeCAD as App
    out = os.path.join(cfg["out"], "pranchas")
    try:
        os.makedirs(out, exist_ok=True)
    except Exception:
        pass
    status = os.path.join(out, "_status.json")
    try:
        res = gerar_executivo(cfg)
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
        QtCore.QTimer.singleShot(400, Gui.getMainWindow().close)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────
# API PUBLICA (roda FORA do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def config_de_spec(spec, fcstd_path, out_dir):
    g = spec["geometria"]
    est = spec.get("estrutura", {})
    ba = est.get("base_adotada")
    sp = est.get("sapata_adotada")
    return {
        "fcstd": str(fcstd_path).replace("\\", "/"),
        "out": str(out_dir).replace("\\", "/"),
        "slug": spec.get("slug", "galpao"),
        "descricao": spec.get("descricao", "Galpao em aco - Projeto Estrutural"),
        "geo": {
            "span": g["span"] * 1000.0,
            "comprimento": g["comprimento"] * 1000.0,
            "eave": g["eave"] * 1000.0,
            "ridge": g.get("ridge", g["eave"]) * 1000.0,
            "bay": g["bay"] * 1000.0,
            "slope": spec.get("cobertura", {}).get("slope", 0.1),
        },
        "perfil_col": est.get("perfil_col_adotado", "?"),
        "perfil_raf": est.get("perfil_raf_adotado", "?"),
        "base": ({"B": ba["B"] * 1000.0, "L": ba["L"] * 1000.0,
                  "t": ba["t"] * 1000.0, "db": ba["db"] * 1000.0,
                  "n": ba["n"]} if ba else None),
        "sapata": ({"B": sp["B"], "L": sp["L"], "h": sp["h"]} if sp else None),
        "terca": est.get("terca_dims"),
        "resultados": est.get("resultados", {}),
        "takeoff": est.get("takeoff", []),
    }


def codigo_fonte():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "techdraw_exec.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def script_bootstrap(cfg):
    """Monta o script que o freecad.exe roda: injeta cfg + fonte deste modulo
    e dispara _entry via QTimer (apos o loop de eventos subir)."""
    return ("# -*- coding: utf-8 -*-\n"
            "_CFG_ = %r\n" % (cfg,) + codigo_fonte() +
            "\nfrom PySide import QtCore\n"
            "QtCore.QTimer.singleShot(1500, lambda: _entry(_CFG_))\n")
