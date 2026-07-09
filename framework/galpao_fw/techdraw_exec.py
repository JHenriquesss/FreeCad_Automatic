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

# Prefixos de solidos que, DE PROPOSITO, nao precisam aparecer desenhados numa
# vista/detalhe (cobertos por quadros/especificacao ou auxiliares). O guard de
# cobertura (_cobertura) so aceita como "ok" o que estiver desenhado OU listado
# aqui -- assim um tipo de elemento novo do build_galpao acusa falha ate ser
# classificado, em vez de sumir silenciosamente das pranchas.
PREFIXOS_SEM_DESENHO = (
    "VAO",                      # auxiliar de vao livre (nao e peca)
    # Miudezas de LIGACAO sem detalhe grafico dedicado: sao dimensionadas e
    # especificadas no memorial/quadro de ligacoes, nao desenhadas em corte
    # proprio. Se um projeto exigir o detalhe, criar a prancha e remover daqui.
    "CLIPE_GIRT",               # clipes de fixacao das girts
    "CONEX_CONSOLE",            # chapa de ligacao do console da ponte rolante
    "CONEX_CUMEEIRA",           # ligacao de cumeeira
    "CONEX_GUSSET",             # gussets dos contraventamentos
)


def _prefixo_label(lbl):
    """Prefixo alfabetico do Label (ate o 1o bloco numerico). Ex.:
    PORTICO_01_C00 -> PORTICO ; TERCA_BEIRAL_E -> TERCA_BEIRAL."""
    import re
    m = re.match(r"^([A-Z]+(?:_[A-Z]+)*)", lbl)
    return m.group(1) if m else lbl


def _bb_overlap(a, b):
    return (a.XMin <= b.XMax and a.XMax >= b.XMin and
            a.YMin <= b.YMax and a.YMax >= b.YMin and
            a.ZMin <= b.ZMax and a.ZMax >= b.ZMin)


def _cobertura(doc, todos):
    """Verifica (pos-geracao) que todo TIPO de solido do modelo aparece em ao
    menos uma prancha: como Source de alguma vista, ou dentro da janela de um
    corte de detalhe. Retorna prefixos desenhados e nao-cobertos."""
    desenhados_nomes = set()
    janelas = []
    for o in doc.Objects:
        if o.TypeId != "TechDraw::DrawViewPart":
            continue
        for s in getattr(o, "Source", []) or []:
            nome = getattr(s, "Name", "") or ""
            lbl = getattr(s, "Label", "") or ""
            if nome.endswith("_CROP") or lbl.endswith("_CROP"):
                try:
                    janelas.append(s.Shape.BoundBox)
                except Exception:
                    pass
            else:
                desenhados_nomes.add(nome)
    prefixos_todos = set()
    prefixos_ok = set()
    for o in todos:
        p = _prefixo_label(o.Label)
        prefixos_todos.add(p)
        coberto = o.Name in desenhados_nomes
        if not coberto:
            try:
                bb = o.Shape.BoundBox
                coberto = any(_bb_overlap(bb, w) for w in janelas)
            except Exception:
                pass
        if coberto:
            prefixos_ok.add(p)
    nao = sorted(p for p in (prefixos_todos - prefixos_ok)
                 if not any(p.startswith(sd) for sd in PREFIXOS_SEM_DESENHO))
    return {"desenhados": sorted(prefixos_ok), "nao_cobertos": nao}


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


def _dims_no_eixo(bbox, axis):
    """(largura, altura) do MODELO projetado no plano da vista, por eixo."""
    if axis == "z":
        return abs(bbox.XLength), abs(bbox.YLength)
    if axis == "x":
        return abs(bbox.YLength), abs(bbox.ZLength)
    return abs(bbox.XLength), abs(bbox.ZLength)  # 'y'


def _paper_half(bbox, scale, axis):
    """Meia-largura/altura da vista NO PAPEL (mm), conforme o eixo de projecao."""
    if bbox is None:
        return 100.0, 100.0
    w, h = _dims_no_eixo(bbox, axis)
    return w * scale / 2.0, h * scale / 2.0


# Escalas normalizadas de desenho (arquitetura/estrutura), maior -> menor.
_ESCALAS = [1 / 5., 1 / 10., 1 / 15., 1 / 20., 1 / 25., 1 / 33.33, 1 / 50.,
            1 / 75., 1 / 100., 1 / 125., 1 / 150., 1 / 200., 1 / 250., 1 / 300.,
            1 / 400., 1 / 500.]

_ESC_NOME = {1 / 5.: "1:5", 1 / 10.: "1:10", 1 / 15.: "1:15", 1 / 20.: "1:20",
             1 / 25.: "1:25", 1 / 33.33: "1:33", 1 / 50.: "1:50",
             1 / 75.: "1:75", 1 / 100.: "1:100", 1 / 125.: "1:125",
             1 / 150.: "1:150", 1 / 200.: "1:200", 1 / 250.: "1:250",
             1 / 300.: "1:300", 1 / 400.: "1:400", 1 / 500.: "1:500"}


def _fit_escala(bbox, axis, avail_w, avail_h):
    """Maior escala normalizada em que a vista cabe em avail_w x avail_h (mm de
    papel). Retorna (escala, nome). Preenche a folha em vez de deixar minuscula."""
    w, h = _dims_no_eixo(bbox, axis)
    w = max(w, 1.0); h = max(h, 1.0)
    smax = min(avail_w / w, avail_h / h)
    for s in _ESCALAS:
        if s <= smax:
            return s, _ESC_NOME[s]
    return _ESCALAS[-1], _ESC_NOME[_ESCALAS[-1]]


def _fmt_m(mm):
    """Cota em metros, virgula decimal, com unidade: 10000 -> '10,00 m'."""
    return ("%.2f m" % (mm / 1000.0)).replace(".", ",")


def _fmt_mm(mm):
    """Cota em milimetros inteiros com unidade: 500 -> '500 mm'."""
    return "%d mm" % int(round(mm))


class _Cotador:
    """Cotas TechDraw ancoradas em pontos 3D. Registradas na montagem e
    aplicadas em lote apos o 1o recompute (vista ja projetada).

    Posiciona cada cota para NAO sobrepor: horizontais empilhadas abaixo da
    peca, verticais empilhadas a esquerda, com passo constante. As posicoes
    (dim.X, dim.Y) sao em mm de papel, origem no centro da vista."""

    MARGEM = 16.0
    PASSO = 13.0
    FONTE = 5.0

    def __init__(self, doc, page, view, halfw=100.0, halfh=100.0):
        self.doc, self.page, self.view = doc, page, view
        self.halfw, self.halfh = halfw, halfh
        self.itens = []

    def d(self, p1, p2, tipo, rotulo, lado=None, nivel=None):
        """Registra uma cota com rotulo JA formatado (com unidade).
        lado: 'baixo'|'cima' p/ horizontais, 'esq'|'dir' p/ verticais.
        nivel: forca a linha de cota (mm de afastamento = MARGEM+nivel*PASSO);
        None -> auto-empilha. Use nivel igual p/ cotas em cadeia (ex. baias)."""
        if self.view is not None:
            self.itens.append((p1, p2, tipo, rotulo, lado, nivel))
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
        cont = {"baixo": 0, "cima": 0, "esq": 0, "dir": 0}
        for j, it in enumerate(self.itens):
            p1, p2, tipo, rotulo, lado, nivel = it
            vert = (tipo == "DistanceY")
            if lado is None:
                lado = "esq" if vert else "baixo"
            try:
                dm = self.doc.addObject("TechDraw::DrawViewDimension",
                                        self.view.Name + "_dim")
                dm.Type = tipo
                dm.References2D = [(self.view, "Vertex%d" % (base + 2 * j)),
                                   (self.view, "Vertex%d" % (base + 2 * j + 1))]
                # Arbitrary=True -> FormatSpec exibido literalmente (rotulo com
                # unidade). Evita a ambiguidade do esquema de unidades.
                dm.Arbitrary = True
                dm.FormatSpec = rotulo
                self.page.addView(dm)
                if nivel is None:
                    k = cont[lado]; cont[lado] += 1
                else:
                    k = nivel
                off = self.MARGEM + k * self.PASSO
                if lado == "esq":
                    dm.X, dm.Y = -(self.halfw + off), 0.0
                elif lado == "dir":
                    dm.X, dm.Y = (self.halfw + off), 0.0
                elif lado == "cima":
                    dm.X, dm.Y = 0.0, (self.halfh + off)
                else:  # baixo
                    dm.X, dm.Y = 0.0, -(self.halfh + off)
                try:
                    dm.ViewObject.Fontsize = self.FONTE
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


def _tabela(doc, page, nome, header, rows, x, y, tam=6.0, larguras=None):
    """Tabela estilizada: cabecalho em negrito/sombreado, larguras de coluna,
    alinhamento. Renderizada como DrawViewSpreadsheet."""
    ss = doc.addObject("Spreadsheet::Sheet", nome + "_ss")
    ncol = len(header)
    cols = [chr(ord("A") + i) for i in range(ncol)]
    for i, h in enumerate(header):
        a = "%s1" % cols[i]
        ss.set(a, str(h))
        try:
            ss.setStyle(a, "bold")
            ss.setBackground(a, (0.82, 0.82, 0.82))
            ss.setAlignment(a, "center|vcenter")
        except Exception:
            pass
    for r, row in enumerate(rows, start=2):
        for i, val in enumerate(row):
            a = "%s%d" % (cols[i], r)
            ss.set(a, str(val))
            try:
                ss.setAlignment(a, ("left" if i == 0 else "center") + "|vcenter")
            except Exception:
                pass
    if larguras:
        for i, w in enumerate(larguras):
            try:
                ss.setColumnWidth(cols[i], int(w))
            except Exception:
                pass
    doc.recompute()
    v = doc.addObject("TechDraw::DrawViewSpreadsheet", nome)
    v.Source = ss
    v.CellStart = "A1"
    v.CellEnd = "%s%d" % (cols[-1], len(rows) + 1)
    v.TextSize = tam
    page.addView(v)
    v.X, v.Y = float(x), float(y)
    return v


def _bloco_texto(doc, page, nome, linhas, x, y, tam=5.0, largura=520):
    """Bloco de texto ALINHADO A ESQUERDA (1 coluna). Usa spreadsheet pois o
    DrawViewAnnotation centraliza o texto (ruim p/ listas/notas)."""
    ss = doc.addObject("Spreadsheet::Sheet", nome + "_ss")
    for i, l in enumerate(linhas, start=1):
        a = "A%d" % i
        ss.set(a, str(l))
        try:
            ss.setAlignment(a, "left|vcenter")
        except Exception:
            pass
    try:
        ss.setColumnWidth("A", int(largura))
    except Exception:
        pass
    doc.recompute()
    v = doc.addObject("TechDraw::DrawViewSpreadsheet", nome)
    v.Source = ss
    v.CellStart = "A1"
    v.CellEnd = "A%d" % len(linhas)
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
# Area util de desenho na A1 (mm de papel): folha 841x594, descontando margem,
# carimbo (canto inf. direito) e faixa de anotacao (base).
AREA_1V = (700.0, 380.0)     # vista unica
AREA_2V = (330.0, 360.0)     # cada vista quando ha 2 lado a lado


def _pr_cobertura(doc, cfg, objs):
    g = cfg["geo"]
    bb = _bbox(objs)
    esc, nome = _fit_escala(bb, "z", *AREA_1V)
    page = _nova_prancha(doc, "PE01_COBERTURA",
                         _carimbo(cfg, "PLANTA DE COBERTURA", "PE-01",
                                  nome, "01/09"))
    v = _vista(doc, page, "V01_COB", objs, (0, 0, 1), (1, 0, 0),
               esc, 410, 350, coarse=True)
    hw, hh = _paper_half(bb, esc, "z")
    c = _Cotador(doc, page, v, hw, hh)
    z = bb.ZMax
    comp, span, bay = g["comprimento"], g["span"], g.get("bay")
    n = int(round(comp / bay)) if bay else 0
    for i in range(n):                                   # cadeia de baias
        c.d((i * bay, 0, z), ((i + 1) * bay, 0, z), "DistanceX",
            _fmt_m(bay), "baixo", nivel=0)
    c.d((0, 0, z), (comp, 0, z), "DistanceX", _fmt_m(comp), "baixo", nivel=1)
    c.d((0, 0, z), (0, span, z), "DistanceY", _fmt_m(span), "esq")
    _anot(doc, page, "A01", ["PLANTA DE COBERTURA   ESCALA %s" % nome,
                             "Inclinacao: %.0f%%" % (g.get("slope", 0.1) * 100),
                             "Cotas em metros."],
          200, 70, 6)
    return [page], [c]


def _pr_fundacoes(doc, cfg, objs):
    g = cfg["geo"]
    fund = _pref(objs, ("SAPATA", "PEDESTAL", "PLACA", "NERVURA"))
    if not fund:
        page = _nova_prancha(doc, "PE02_FUNDACOES",
                             _carimbo(cfg, "PLANTA DE FUNDACOES", "PE-02",
                                      "-", "02/09"))
        return [page], []
    bf = _bbox(fund)
    esc, nome = _fit_escala(bf, "z", *AREA_1V)
    page = _nova_prancha(doc, "PE02_FUNDACOES",
                         _carimbo(cfg, "PLANTA DE FUNDACOES", "PE-02",
                                  nome, "02/09"))
    v = _vista(doc, page, "V02_FUND", fund, (0, 0, 1), (1, 0, 0),
               esc, 410, 350, coarse=True)
    hw, hh = _paper_half(bf, esc, "z")
    c = _Cotador(doc, page, v, hw, hh)
    z = bf.ZMax
    comp, span, bay = g["comprimento"], g["span"], g.get("bay")
    n = int(round(comp / bay)) if bay else 0
    for i in range(n):
        c.d((i * bay, 0, z), ((i + 1) * bay, 0, z), "DistanceX",
            _fmt_m(bay), "baixo", nivel=0)
    c.d((0, 0, z), (comp, 0, z), "DistanceX", _fmt_m(comp), "baixo", nivel=1)
    c.d((0, 0, z), (0, span, z), "DistanceY", _fmt_m(span), "esq")
    sap = _pref(fund, ("SAPATA",))
    if sap:
        b1 = sap[0].Shape.BoundBox
        c.d((b1.XMin, b1.YMin, b1.ZMax), (b1.XMax, b1.YMin, b1.ZMax),
            "DistanceX", _fmt_mm(b1.XLength), "cima", nivel=0)
    sp = cfg.get("sapata")
    if sp:
        _anot(doc, page, "A02q", ["QUADRO DE SAPATAS"], 120, 175, 6)
        _tabela(doc, page, "Q02",
                ["TIPO", "B (cm)", "L (cm)", "h (cm)"],
                [["S1", "%.0f" % (sp["B"] * 100), "%.0f" % (sp["L"] * 100),
                  "%.0f" % (sp["h"] * 100)]],
                120, 150, tam=6, larguras=[90, 70, 70, 70])
    _anot(doc, page, "A02", ["PLANTA DE FUNDACOES   ESCALA %s" % nome,
                             "Cotas em metros; sapatas em cm."], 200, 70, 6)
    return [page], [c]


def _pr_elevacoes(doc, cfg, objs):
    g = cfg["geo"]
    bb = _bbox(objs)
    comp_x = True  # convencao build_galpao: comprimento em X, vao em Y (nao inferir por bbox: quebra se vao>comp)
    span, comp, bay = g["span"], g["comprimento"], g.get("bay")
    ax_fr = "x" if comp_x else "y"
    ax_lt = "y" if comp_x else "x"
    e1, n1 = _fit_escala(bb, ax_fr, *AREA_2V)
    e2, n2 = _fit_escala(bb, ax_lt, *AREA_2V)
    esc = min(e1, e2)                                    # mesma escala p/ as 2
    nome = _ESC_NOME[esc]
    page = _nova_prancha(doc, "PE03_ELEVACOES",
                         _carimbo(cfg, "ELEVACOES", "PE-03", nome, "03/09"))
    # oitao (olha ao longo do comprimento)
    dfr = (-1, 0, 0) if comp_x else (0, -1, 0)
    xfr = (0, -1, 0) if comp_x else (1, 0, 0)
    v1 = _vista(doc, page, "V03_OITAO", objs, dfr, xfr, esc, 220, 360,
                coarse=True)
    hw1, hh1 = _paper_half(bb, esc, ax_fr)
    c1 = _Cotador(doc, page, v1, hw1, hh1)
    if comp_x:
        c1.d((0, 0, 0.), (0, span, 0.), "DistanceX", _fmt_m(span), "baixo")
    else:
        c1.d((0, 0, 0.), (span, 0, 0.), "DistanceX", _fmt_m(span), "baixo")
    c1.d((0, 0, 0.), (0, 0, g["eave"]), "DistanceY", _fmt_m(g["eave"]), "esq")
    c1.d((0, 0, 0.), (0, 0, g["ridge"]), "DistanceY", _fmt_m(g["ridge"]), "esq")
    # lateral
    dlt = (0, -1, 0) if comp_x else (-1, 0, 0)
    xlt = (1, 0, 0) if comp_x else (0, -1, 0)
    v2 = _vista(doc, page, "V03_LATERAL", objs, dlt, xlt, esc, 590, 360,
                coarse=True)
    hw2, hh2 = _paper_half(bb, esc, ax_lt)
    c2 = _Cotador(doc, page, v2, hw2, hh2)
    n = int(round(comp / bay)) if bay else 0
    for i in range(n):                                   # cadeia de baias
        a = (i * bay, 0, 0.) if comp_x else (0, i * bay, 0.)
        b = ((i + 1) * bay, 0, 0.) if comp_x else (0, (i + 1) * bay, 0.)
        c2.d(a, b, "DistanceX", _fmt_m(bay), "baixo", nivel=0)
    if comp_x:
        c2.d((0, 0, 0.), (comp, 0, 0.), "DistanceX", _fmt_m(comp),
             "baixo", nivel=1)
    else:
        c2.d((0, 0, 0.), (0, comp, 0.), "DistanceX", _fmt_m(comp),
             "baixo", nivel=1)
    c2.d((0, 0, 0.), (0, 0, g["eave"]), "DistanceY", _fmt_m(g["eave"]), "esq")
    _anot(doc, page, "A03a", ["ELEVACAO FRONTAL (OITAO)   ESC %s" % nome],
          120, 150, 5)
    _anot(doc, page, "A03b", ["ELEVACAO LATERAL   ESC %s" % nome], 490, 150, 5)
    _anot(doc, page, "A03c", ["Cotas em metros. RN +0,00 = topo do concreto."],
          200, 60, 5)
    return [page], [c1, c2]


def _pr_portico(doc, cfg, objs):
    g = cfg["geo"]
    bb = _bbox(objs)
    comp_x = True  # convencao build_galpao: comprimento em X, vao em Y (nao inferir por bbox: quebra se vao>comp)
    eixo = "x" if comp_x else "y"
    meio = (bb.XMin + bb.XMax) / 2 if comp_x else (bb.YMin + bb.YMax) / 2
    bay = g.get("bay") or 5000.0
    # inclui console e viga de rolamento da ponte (quando houver) no portico
    frame = _faixa(_pref(objs, ("PORTICO", "NERVURA", "MAO", "PLACA",
                                "PEDESTAL", "SAPATA", "CONSOLE_PONTE",
                                "VIGA_ROLAMENTO")),
                   eixo, meio, bay * 0.45)
    if not frame:
        frame = objs
    fb = _bbox(frame)
    ax = "x" if comp_x else "y"
    esc, nome = _fit_escala(fb, ax, *AREA_1V)
    page = _nova_prancha(doc, "PE04_PORTICO",
                         _carimbo(cfg, "PORTICO TIPICO", "PE-04",
                                  nome, "04/09"))
    dv = (-1, 0, 0) if comp_x else (0, -1, 0)
    xv = (0, -1, 0) if comp_x else (1, 0, 0)
    v = _vista(doc, page, "V04_PORTICO", frame, dv, xv, esc, 410, 350)
    span = g["span"]
    linha = meio
    hw, hh = _paper_half(fb, esc, ax)
    c = _Cotador(doc, page, v, hw, hh)
    if comp_x:
        c.d((linha, 0, 0.), (linha, span, 0.), "DistanceX", _fmt_m(span),
            "baixo")
    else:
        c.d((0, linha, 0.), (span, linha, 0.), "DistanceX", _fmt_m(span),
            "baixo")
    a0 = (linha, 0, 0.) if comp_x else (0, linha, 0.)
    ae = (linha, 0, g["eave"]) if comp_x else (0, linha, g["eave"])
    ar = (linha, 0, g["ridge"]) if comp_x else (0, linha, g["ridge"])
    c.d(a0, ae, "DistanceY", _fmt_m(g["eave"]), "esq")
    c.d(a0, ar, "DistanceY", _fmt_m(g["ridge"]), "esq")
    pt = cfg.get("ponte")
    if pt:  # cota o nivel do trilho da ponte
        at = (linha, 0, pt["Hvr"]) if comp_x else (0, linha, pt["Hvr"])
        c.d(a0, at, "DistanceY", _fmt_m(pt["Hvr"]), "esq")
    linhas = ["PORTICO TIPICO   ESCALA %s" % nome,
              "Colunas: %s    Vigas: %s" % (cfg.get("perfil_col", "?"),
                                            cfg.get("perfil_raf", "?"))]
    if pt:
        cap = (" %.0f kN" % pt["Q"]) if pt.get("Q") else ""
        linhas.append("Ponte rolante%s: viga de rolamento no nivel +%s" %
                      (cap, _fmt_m(pt["Hvr"])))
    linhas.append("Cotas em metros.")
    _anot(doc, page, "A04", linhas, 200, 70, 6)
    return [page], [c]


def _pr_contravent(doc, cfg, objs, todos):
    if not _pref(objs, ("CONTRAV", "TIRANTE")):
        page = _nova_prancha(doc, "PE05_CONTRAVENTAMENTO",
                             _carimbo(cfg, "CONTRAVENTAMENTOS", "PE-05",
                                      "-", "05/09"))
        return [page], []
    # esticadores sao miudezas (fora de `objs`); puxa de `todos` para o sistema
    # de contraventamento aparecer completo (barra + esticador) nesta prancha.
    est = _pref(todos, ("ESTICADOR",))
    cv = _pref(objs, ("CONTRAV", "TIRANTE", "PORTICO")) + est
    cob = _pref(objs, ("CONTRAV", "TIRANTE", "PORTICO")) + est
    bb = _bbox(objs)
    comp_x = True  # convencao build_galpao: comprimento em X, vao em Y (nao inferir por bbox: quebra se vao>comp)
    ax_lt = "y" if comp_x else "x"
    e1, _ = _fit_escala(bb, ax_lt, 720, 200)
    e2, _ = _fit_escala(_bbox(cob), "z", 720, 200)
    esc = min(e1, e2); nome = _ESC_NOME[esc]
    page = _nova_prancha(doc, "PE05_CONTRAVENTAMENTO",
                         _carimbo(cfg, "CONTRAVENTAMENTOS", "PE-05",
                                  nome, "05/09"))
    g = cfg["geo"]
    comp, bay = g["comprimento"], g.get("bay") or 5000.0
    dlt = (0, -1, 0) if comp_x else (-1, 0, 0)
    xlt = (1, 0, 0) if comp_x else (0, -1, 0)
    v1 = _vista(doc, page, "V05_CV_LAT", cv, dlt, xlt, esc, 410, 430,
                coarse=True)
    hw1, hh1 = _paper_half(bb, esc, "y" if comp_x else "x")
    c1 = _Cotador(doc, page, v1, hw1, hh1)
    # baia contraventada + altura
    a = (0, 0, 0.) if comp_x else (0, 0, 0.)
    b = (bay, 0, 0.) if comp_x else (0, bay, 0.)
    c1.d(a, b, "DistanceX", _fmt_m(bay), "baixo")
    if comp_x:
        c1.d((comp, 0, 0.), (comp, 0, g["eave"]), "DistanceY",
             _fmt_m(g["eave"]), "dir")
    else:
        c1.d((0, comp, 0.), (0, comp, g["eave"]), "DistanceY",
             _fmt_m(g["eave"]), "dir")
    _vista(doc, page, "V05_CV_COB", cob, (0, 0, 1), (1, 0, 0), esc,
           410, 220, coarse=True)
    _anot(doc, page, "A05a", ["CONTRAVENTAMENTO VERTICAL   ESC %s" % nome,
                              "Barras redondas pretensionadas c/ esticador."],
          200, 345, 5)
    _anot(doc, page, "A05b", ["CONTRAVENTAMENTO DE COBERTURA   ESC %s" % nome,
                              "Cotas em metros."], 200, 120, 5)
    return [page], [c1]


def _pr_base(doc, cfg, objs, todos):
    base = _pref(todos, ("PLACA", "CHUMBADOR", "PEDESTAL", "PORCA", "ARRUELA"))
    if not base:
        page = _nova_prancha(doc, "PE06_DET_BASE",
                             _carimbo(cfg, "DETALHE - BASE DE COLUNA", "PE-06",
                                      "-", "06/09"))
        return [page], []
    b0 = base[0].Shape.BoundBox
    cx, cy = (b0.XMin + b0.XMax) / 2, (b0.YMin + b0.YMax) / 2
    um = _faixa(_faixa(base, "x", cx, 500), "y", cy, 500) or base[:6]
    db = _bbox(um)
    esc, nome = _fit_escala(db, "y", *AREA_2V)
    page = _nova_prancha(doc, "PE06_DET_BASE",
                         _carimbo(cfg, "DETALHE - BASE DE COLUNA", "PE-06",
                                  nome, "06/09"))
    # vista frontal
    v1 = _vista(doc, page, "V06_BASE_FR", um, (0, -1, 0), (1, 0, 0),
                esc, 230, 350)
    hw1, hh1 = _paper_half(db, esc, "y")
    c1 = _Cotador(doc, page, v1, hw1, hh1)
    c1.d((db.XMin, db.YMin, db.ZMin), (db.XMin, db.YMin, db.ZMax),
         "DistanceY", _fmt_mm(db.ZLength), "esq")
    c1.d((db.XMin, db.YMin, db.ZMax), (db.XMax, db.YMin, db.ZMax),
         "DistanceX", _fmt_mm(db.XLength), "baixo")
    # vista superior (placa + furos)
    pl = _pref(um, ("PLACA", "CHUMBADOR"))
    pb = _bbox(_pref(um, ("PLACA",)) or um)
    e2, n2 = _fit_escala(pb, "z", *AREA_2V)
    v2 = _vista(doc, page, "V06_BASE_TOP", pl, (0, 0, 1), (1, 0, 0),
                e2, 600, 350)
    hw2, hh2 = _paper_half(pb, e2, "z")
    c2 = _Cotador(doc, page, v2, hw2, hh2)
    c2.d((pb.XMin, pb.YMin, pb.ZMax), (pb.XMax, pb.YMin, pb.ZMax),
         "DistanceX", _fmt_mm(pb.XLength), "baixo")
    c2.d((pb.XMin, pb.YMin, pb.ZMax), (pb.XMin, pb.YMax, pb.ZMax),
         "DistanceY", _fmt_mm(pb.YLength), "esq")
    ba = cfg.get("base")
    linhas = ["DETALHE DA BASE",
              "Vista frontal ESC %s   Vista superior ESC %s" % (nome, n2),
              "Cotas em milimetros."]
    if ba:
        linhas += ["Placa %.0f x %.0f x %.0f mm" % (ba["B"], ba["L"], ba["t"]),
                   "%dx chumbadores d %.0f mm" % (ba["n"], ba["db"])]
    _anot(doc, page, "A06", linhas, 200, 90, 5)
    return [page], [c1, c2]


def _pr_joelho(doc, cfg, objs, todos):
    """Detalhe REAL do no viga-coluna: recorta a geometria numa janela em torno
    de UM joelho (Part.common com uma caixa) para ter um close-up limpo, em vez
    de mostrar o topo inteiro do portico. Projeta o compound recortado."""
    import Part
    import FreeCAD as App
    g = cfg["geo"]
    bb = _bbox(objs)
    comp_x = True  # convencao build_galpao: comprimento em X, vao em Y (nao inferir por bbox: quebra se vao>comp)
    eixo = "x" if comp_x else "y"
    meio = (bb.XMin + bb.XMax) / 2 if comp_x else (bb.YMin + bb.YMax) / 2
    bay = g.get("bay") or 5000.0
    # Corta a janela em torno do no e mostra TUDO que cai dentro dela (sem
    # curadoria por prefixo): coluna, viga, mao-francesa, chapas, terca de
    # beiral, calha, tapamento etc. O que estiver no modelo aparece no corte.
    frame = _faixa(todos, eixo, meio, bay * 0.45)
    # canto do joelho (topo da coluna no lado y=0 / x=0)
    if comp_x:
        cx0, cy0, cz0 = meio, bb.YMin + 100.0, g["eave"]
    else:
        cx0, cy0, cz0 = bb.XMin + 100.0, meio, g["eave"]
    KW = 1500.0                                       # meia-janela do no (mm)
    caixa = Part.makeBox(2 * KW, 2 * KW, 2 * KW,
                         App.Vector(cx0 - KW, cy0 - KW, cz0 - KW))
    crops = []
    mao_bb = None
    for o in frame:
        try:
            com = o.Shape.common(caixa)
            if com.Edges:
                crops.append(com)
                if o.Label.startswith("MAO"):
                    mao_bb = com.BoundBox
        except Exception:
            pass
    if not crops:
        page = _nova_prancha(doc, "PE07_DET_JOELHO",
                             _carimbo(cfg, "DETALHE - LIGACAO JOELHO", "PE-07",
                                      "-", "07/09"))
        return [page], []
    feat = doc.addObject("Part::Feature", "JOELHO_CROP")
    feat.Shape = Part.makeCompound(crops)
    jb = feat.Shape.BoundBox
    ax = "x" if comp_x else "y"
    esc, nome = _fit_escala(jb, ax, 620, 400)
    page = _nova_prancha(doc, "PE07_DET_JOELHO",
                         _carimbo(cfg, "DETALHE - LIGACAO JOELHO (VIGA-COLUNA)",
                                  "PE-07", nome, "07/09"))
    dv = (-1, 0, 0) if comp_x else (0, -1, 0)
    xv = (0, -1, 0) if comp_x else (1, 0, 0)
    v = _vista(doc, page, "V07_JOELHO", [feat], dv, xv, esc, 410, 350)
    hw, hh = _paper_half(jb, esc, ax)
    c = _Cotador(doc, page, v, hw, hh)
    # altura da janela + dimensoes reais da mao-francesa (se identificada)
    c.d((jb.XMin, jb.YMin, jb.ZMin), (jb.XMin, jb.YMin, jb.ZMax),
        "DistanceY", _fmt_mm(jb.ZLength), "esq")
    if mao_bb:
        if comp_x:
            c.d((jb.XMin, mao_bb.YMin, mao_bb.ZMin),
                (jb.XMin, mao_bb.YMax, mao_bb.ZMin),
                "DistanceX", _fmt_mm(mao_bb.YLength), "baixo")
        else:
            c.d((mao_bb.XMin, jb.YMin, mao_bb.ZMin),
                (mao_bb.XMax, jb.YMin, mao_bb.ZMin),
                "DistanceX", _fmt_mm(mao_bb.XLength), "baixo")
    _anot(doc, page, "A07", [
        "DETALHE DO NO VIGA-COLUNA (JOELHO)   ESCALA %s" % nome,
        "Colunas: %s   Vigas: %s" % (cfg.get("perfil_col", "?"),
                                     cfg.get("perfil_raf", "?")),
        "Mao-francesa, chapas e parafusos conforme memoria de calculo.",
        "Cotas em milimetros."], 200, 80, 5)
    return [page], [c]


def _pr_fechamento(doc, cfg, objs):
    if not _pref(objs, ("TERCA", "TAPAMENTO", "MAO")):
        page = _nova_prancha(doc, "PE08_FECHAMENTO",
                             _carimbo(cfg, "FECHAMENTO / TERCAS", "PE-08",
                                      "-", "08/09"))
        return [page], []
    fch = _pref(objs, ("TERCA", "TAPAMENTO", "MAO", "MONTANTE", "TELHA",
                       "CALHA", "PORTICO"))
    g = cfg["geo"]
    bb = _bbox(objs)
    comp_x = True  # convencao build_galpao: comprimento em X, vao em Y (nao inferir por bbox: quebra se vao>comp)
    ax = "y" if comp_x else "x"
    esc, nome = _fit_escala(bb, ax, *AREA_1V)
    page = _nova_prancha(doc, "PE08_FECHAMENTO",
                         _carimbo(cfg, "FECHAMENTO / TERCAS / MAO-FRANCESA",
                                  "PE-08", nome, "08/09"))
    dlt = (0, -1, 0) if comp_x else (-1, 0, 0)
    xlt = (1, 0, 0) if comp_x else (0, -1, 0)
    v = _vista(doc, page, "V08_FECH", fch, dlt, xlt, esc, 410, 360,
               coarse=True)
    comp, bay = g["comprimento"], g.get("bay") or 5000.0
    hw, hh = _paper_half(bb, esc, "y" if comp_x else "x")
    c = _Cotador(doc, page, v, hw, hh)
    # comprimento + baia + altura (espacamento das tercas via eixos de baia)
    if comp_x:
        c.d((0, 0, 0.), (comp, 0, 0.), "DistanceX", _fmt_m(comp), "baixo", nivel=1)
        c.d((0, 0, 0.), (bay, 0, 0.), "DistanceX", _fmt_m(bay), "baixo", nivel=0)
        c.d((0, 0, 0.), (0, 0, g["eave"]), "DistanceY", _fmt_m(g["eave"]), "esq")
    else:
        c.d((0, 0, 0.), (0, comp, 0.), "DistanceX", _fmt_m(comp), "baixo", nivel=1)
        c.d((0, 0, 0.), (0, bay, 0.), "DistanceX", _fmt_m(bay), "baixo", nivel=0)
        c.d((0, 0, 0.), (0, 0, g["eave"]), "DistanceY", _fmt_m(g["eave"]), "esq")
    tc = cfg.get("terca")
    linhas = ["FECHAMENTO E TERCAS (VISTA LATERAL)   ESCALA %s" % nome]
    if tc:
        linhas.append("Terca Ue: %s" % tc)
    linhas.append("Cotas em metros.")
    _anot(doc, page, "A08", linhas, 200, 80, 5)
    return [page], [c]


def _pr_quadros(doc, cfg):
    page = _nova_prancha(doc, "PE09_QUADROS",
                         _carimbo(cfg, "QUADROS E NOTAS TECNICAS", "PE-09",
                                  "-", "09/09"))
    # QUADRO DE VERIFICACOES (utilizacoes do calculo, NBR 8800)
    res = [(k, v) for k, v in (cfg.get("resultados") or {}).items()
           if v is not None]
    if res:
        _anot(doc, page, "A09v",
              ["QUADRO DE VERIFICACOES ESTRUTURAIS (NBR 8800)"], 240, 500, 7)
        rows = [[k, "%.2f" % float(v), "OK" if float(v) <= 1.001 else "REVER"]
                for k, v in res]
        _tabela(doc, page, "Q09V", ["ELEMENTO", "UTILIZACAO n/Rd", "SITUACAO"],
                rows, 240, 470 - len(rows) * 5, tam=6, larguras=[170, 130, 100])
    # QUADRO DE MATERIAIS (takeoff do modelo 3D)
    tk = [r for r in (cfg.get("takeoff") or []) if "Alvenaria" not in str(r[0])]
    if tk:
        tk = sorted(tk, key=lambda r: -float(r[4]))[:16]
        rows = [[str(r[0]), str(r[1]), str(r[2]), "%.0f" % float(r[4])]
                for r in tk]
        rows.append(["TOTAL", "", "", "%.0f" % sum(float(r[4]) for r in tk)])
        _anot(doc, page, "A09m", ["QUADRO DE MATERIAIS - ACO"], 600, 500, 7)
        _tabela(doc, page, "Q09M", ["ELEMENTO", "PERFIL", "QTD", "MASSA (kg)"],
                rows, 600, 470 - len(rows) * 5, tam=6,
                larguras=[150, 130, 60, 110])
    # NOTAS TECNICAS
    notas = cfg.get("notas") or [
        "NOTAS TECNICAS GERAIS",
        "1. Cotas em metros nas vistas gerais; em mm nos detalhes.",
        "2. RN +0,00 = topo do concreto (base das placas).",
        "3. Aco estrutural MR250 (NBR 8800). Armadura CA-50.",
        "4. Concreto fck 25 MPa. Cobrimento 5 cm (fund.), 3 cm (sup.).",
        "5. Parafusos A325 (fub 825 MPa) ou A307 conforme ligacao.",
        "6. Soldas E70XX (fw 485 MPa). Filete minimo 6 mm.",
        "7. Chumbadores ASTM A36 com gancho 180 mm.",
        "8. Contraventamento: barras d20 pretensionadas c/ esticador.",
        "9. Tercas Ue formado a frio (NBR 14762).",
        "10. Projeto executivo sujeito a revisao e ART.",
    ]
    _bloco_texto(doc, page, "A09n", notas, 240, 250, tam=5, largura=560)
    return [page], []


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
            if fn in (_pr_base, _pr_joelho, _pr_contravent):
                pgs, cts = fn(doc, cfg, objs, todos)  # precisam de miudezas
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

    try:
        cob = _cobertura(doc, todos)
    except Exception:
        cob = {"desenhados": [], "nao_cobertos": []}

    return {"ok": True, "pranchas": [p.Name for p in paginas],
            "arquivos": arquivos, "fcstd": fcstd_out, "cobertura": cob}


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
    # Fecha limpo: primeiro fecha TODOS os documentos sem prompt (via API, que
    # nao dispara o dialogo "salvar/descartar"), depois encerra o app. Sem isso
    # o close() da janela abre o dialogo com doc sujo e a instancia fica zumbi.
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
def _limpo(v, padrao):
    """Valor de spec, tratando PENDENTE/vazio/None como nao preenchido."""
    if v is None or v == "__PENDENTE__" or str(v).strip() == "":
        return padrao
    return v


def config_de_spec(spec, fcstd_path, out_dir):
    g = spec["geometria"]
    est = spec.get("estrutura", {})
    ba = est.get("base_adotada")
    sp = est.get("sapata_adotada")
    return {
        "fcstd": str(fcstd_path).replace("\\", "/"),
        "out": str(out_dir).replace("\\", "/"),
        "slug": _limpo(spec.get("slug"), "galpao"),
        "descricao": _limpo(spec.get("descricao"),
                            "Galpao em aco - Projeto Estrutural"),
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
        "ponte": ({"Hvr": spec["ponte"].get("Hvr", 4.5) * 1000.0,
                   "Q": spec["ponte"].get("Q")}
                  if spec.get("ponte") else None),
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
