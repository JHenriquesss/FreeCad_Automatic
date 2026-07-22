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
# Cobertura: toda peca do modelo aparece desenhada, EXCETO os prefixos abaixo.
# So auxiliares que nao sao peca fisica. As ligacoes (cumeeira/gusset/console/
# clipe) tem prancha de detalhe propria via _pr_ligacoes (PE10+).
PREFIXOS_SEM_DESENHO = (
    "VAO",
)


def _prefixo_label(lbl):
    """Prefixo alfabetico do Label (ate o 1o bloco numerico). Ex.:
    PORTICO_01_C00 -> PORTICO ; TERCA_BEIRAL_E -> TERCA_BEIRAL."""
    import re
    m = re.match(r"^([A-Z]+(?:_[A-Z]+)*)", lbl)
    return m.group(1) if m else lbl


# Sufixos de LADO/posicao: a mesma peca espelhada (esq/dir, frente/fundo). Para
# a cobertura, D e E sao o MESMO tipo -- o detalhe desenha so um representante.
_LADOS = ("D", "E", "FRENTE", "FUNDO")


def _tipo_solido(lbl):
    """Tipo de peca ignorando o lado: CONEX_GUSSET_PAR_D -> CONEX_GUSSET_PAR ;
    MONTANTE_OITAO_FRENTE -> MONTANTE_OITAO ; CONEX_GUSSET_COB (COB nao e lado)."""
    parts = _prefixo_label(lbl).split("_")
    while len(parts) > 1 and parts[-1] in _LADOS:
        parts.pop()
    return "_".join(parts)


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
        p = _tipo_solido(o.Label)      # tipo sem lado (D/E = mesmo tipo)
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


# Avisos de CONTEUDO de prancha (a prancha desenhou algo diferente do que o
# carimbo promete). Coletados durante a geracao e devolvidos no resultado, para
# nao morrer no stdout do freecad.exe. Ver _aviso_prancha.
AVISOS_PRANCHA = []


def _aviso_prancha(prancha, msg):
    """Registra (e imprime) que uma prancha nao tem o conteudo que promete.

    POR QUE existir: `_cobertura` so garante que cada TIPO de solido aparece em
    ALGUMA prancha - o portico aparecia nas elevacoes, entao PE04 (portico) e
    PE07 (joelho) podiam desenhar peca errada e passar. Esta guarda e POR PRANCHA.
    Nao levanta excecao: uma prancha errada nao deve derrubar as outras 12."""
    AVISOS_PRANCHA.append({"prancha": prancha, "aviso": msg})
    print("[!] PRANCHA %s: %s" % (prancha, msg))


def _snap_portico(objs, eixo, centro):
    """Move `centro` para o eixo do PORTICO mais proximo.

    POR QUE: as pranchas de portico (PE04) e de joelho (PE07) fatiam uma faixa
    +-0,45*bay em torno do MEIO do comprimento. Como 0,45 < 0,5 do vao, se o meio
    cair ENTRE dois porticos a faixa nao pega NENHUM - o que acontece com numero
    IMPAR de vaos (= numero PAR de porticos), quando o meio fica a meio-vao dos
    dois porticos centrais. A amostra (5 vaos / 6 porticos) e esse caso.
    O sintoma nao e erro: e uma prancha que desenha o que sobrou
    (tercas/calha/tapamento, que atravessam o comprimento e tem centro no meio) e
    CARIMBA como se fosse o portico/joelho. Achado 2x (PE04 e PE07, sessao 16).
    Sem PORTICO no modelo devolve o centro original (o caller trata)."""
    _c = _cx if eixo == "x" else _cy
    eixos = sorted({_c(o) for o in _pref(objs, ("PORTICO",))
                    if hasattr(o, "Shape") and not o.Shape.isNull()})
    return min(eixos, key=lambda x: abs(x - centro)) if eixos else centro


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


def _n_edges(view):
    """Numero de arestas projetadas na vista. Serve de proxy anti-silhueta:
    uma caixa chapada tem poucas arestas; uma elevacao real de perfis+furos
    tem dezenas."""
    i = 0
    while True:
        try:
            if view.getEdgeByIndex(i) is None:
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


def _tabela(doc, page, nome, header, rows, x, y, tam=6.0, larguras=None, escala=1.0):
    """Tabela estilizada: cabecalho em negrito/sombreado, larguras de coluna,
    alinhamento. Renderizada como DrawViewSpreadsheet. escala>1 amplia celula+texto
    juntos (legibilidade em A1, sem clipar)."""
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
    try:
        v.Scale = float(escala)
    except Exception:
        pass
    page.addView(v)
    v.X, v.Y = float(x), float(y)
    return v


def _bloco_texto(doc, page, nome, linhas, x, y, tam=5.0, largura=520, escala=1.0):
    """Bloco de texto ALINHADO A ESQUERDA (1 coluna). Usa spreadsheet pois o
    DrawViewAnnotation centraliza o texto (ruim p/ listas/notas). escala>1 amplia."""
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
    try:
        v.Scale = float(escala)
    except Exception:
        pass
    page.addView(v)
    v.X, v.Y = float(x), float(y)
    return v


# ─────────────────────────────────────────────────────────────────────────
# LAYOUT DO QUADRO / NUMERACAO (puros e testaveis - sem FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def _meia_alt_view(nlin, escala):
    """Meia-altura aproximada (mm de papel) de um DrawViewSpreadsheet de nlin
    linhas (incl. cabecalho) na escala dada. As views sao ancoradas pelo CENTRO
    (v.X/v.Y), entao a metade importa. Calibrado no fator 7/linha (meia-linha em
    escala 1,5) que ancora as tabelas do quadro."""
    return nlin * (7.0 / 1.5) * escala


def _pos_notas(n_verif, n_mat, n_notas, y_topo=480.0, dy_por_linha=7.0,
               esc_tab=1.5, esc_notas=1.4, margem=20.0, piso=70.0):
    """Y (centro) do bloco de NOTAS TECNICAS, SEMPRE abaixo das tabelas do quadro.
    As tabelas ancoram o centro em y = y_topo - nrows*dy_por_linha e crescem
    simetricamente; antes as notas ficavam num y FIXO (240) e colidiam com a
    tabela quando ela tinha muitas linhas (bug do overlap na PE09). Aqui o y das
    notas e derivado da base da tabela mais baixa. Pura (testavel sem FreeCAD)."""
    bases = []
    if n_verif > 0:
        yv = y_topo - n_verif * dy_por_linha
        bases.append(yv - _meia_alt_view(n_verif + 1, esc_tab))     # +1 cabecalho
    if n_mat > 0:
        ym = y_topo - n_mat * dy_por_linha
        bases.append(ym - _meia_alt_view(n_mat + 1, esc_tab))
    base = min(bases) if bases else (y_topo - 10.0)
    y = base - margem - _meia_alt_view(n_notas, esc_notas)
    return max(y, piso)


def _codigo_prancha(page_name, ordem, total):
    """(drawing_number, sheet_number) de uma prancha. drawing_number = codigo de
    TIPO derivado do nome ('PEnn_...' -> 'PE-nn'), batendo com o nome do arquivo;
    sheet_number = posicao sequencial 'NN/TOTAL'. Antes o drawing_number era
    sobrescrito pela ORDEM (arquivo PE11 exibia 'PE-09') - inconsistencia
    corrigida. Pura (testavel sem FreeCAD)."""
    import re
    m = re.match(r"PE0*(\d+)", str(page_name or ""))
    numero = ("PE-%02d" % int(m.group(1))) if m else ("PE-%02d" % ordem)
    return numero, "%02d/%02d" % (ordem, total)


def _cap_titulo(t, maxlen=26):
    """Encurta o titulo do carimbo p/ caber na celula (evita o overflow que
    invadia o campo 'Created by'). Remove o prefixo redundante 'DETALHE - ' (a
    prancha ja e um detalhe), abrevia termos longos e, no limite, corta com
    reticencia. Pura (testavel sem FreeCAD)."""
    t = str(t or "").strip()
    t = t.replace("DETALHE - ", "").replace("DETALHE ", "")
    if len(t) <= maxlen:
        return t
    t = (t.replace("CONTRAV.", "CONTR.")
         .replace(" / MAO-FRANCESA", "")
         .replace(" (VIGA-COLUNA)", ""))
    if len(t) <= maxlen:
        return t
    return t[:maxlen - 1].rstrip() + "…"


def _fmt_terca(tc):
    """Formata a bitola da terca Ue (bw,bf,D,t em mm) como 'Ue bw x bf x D x t mm'
    em vez do repr cru da lista/tupla. Pura (testavel sem FreeCAD)."""
    try:
        bw, bf, dl, t = (float(x) for x in tc)
        return "Ue %g x %g x %g x %.2f mm" % (bw, bf, dl, t)
    except Exception:
        return str(tc)


def _quadro_fundacao(cfg, tem_estaca=None):
    """(titulo, headers, rows, nota) do quadro de fundacao COERENTE com o tipo:
    fundacao profunda -> 'QUADRO DE ESTACAS / BLOCOS' (nao 'SAPATAS', que vazava
    na fundacao profunda); rasa -> 'QUADRO DE SAPATAS'. tem_estaca None deduz de
    cfg. rows vazio => nao desenha quadro. Pura (testavel sem FreeCAD)."""
    if tem_estaca is None:
        tem_estaca = bool(cfg.get("estaca"))
    if tem_estaca:
        e = cfg.get("estaca") or {}
        b = cfg.get("bloco") or {}
        rows = []
        if e:
            rows.append(["Estaca", "D=%.0f" % (e.get("D", 0) * 100),
                         "L=%.0f" % (e.get("L", 0) * 100), "%s" % (e.get("n", "") or "")])
        if b:
            rows.append(["Bloco", "a=%.0f" % (b.get("a", 0) * 100),
                         "h=%.0f" % (b.get("h", 0) * 100), ""])
        return ("QUADRO DE ESTACAS / BLOCOS", ["ELEM", "DIM1 (cm)", "DIM2 (cm)", "N"],
                rows, "Cotas em metros; estacas/blocos em cm.")
    sp = cfg.get("sapata")
    if sp:
        rows = [["S1", "%.0f" % (sp["B"] * 100), "%.0f" % (sp["L"] * 100),
                 "%.0f" % (sp["h"] * 100)]]
        return ("QUADRO DE SAPATAS", ["TIPO", "B (cm)", "L (cm)", "h (cm)"],
                rows, "Cotas em metros; sapatas em cm.")
    return (None, None, [], "Cotas em metros.")


def _pos_corte_ligacao(dupla, xpos, x_notas=200.0, larg_notas=360.0):
    """(x, y) do corte seccionado de um detalhe de ligacao. No caso 'dupla'
    (elevacao + vista da chapa) o corte vai para a DIREITA (sob a vista da chapa),
    FORA da faixa horizontal do bloco de notas (canto inf. esquerdo) - que ele
    invadia na cumeeira (overlap). No caso simples, mantem sob a elevacao (xpos),
    onde nunca colidiu. Pura (testavel sem FreeCAD)."""
    if dupla:
        return (600.0, 140.0)
    return (float(xpos), 120.0)


def _callout_bloco(cfg, a_cm=None, h_cm=None):
    """Linhas de nota do detalhe do bloco de coroamento (fundacao profunda). As
    dimensoes do bloco (a_cm/h_cm) devem vir da GEOMETRIA REAL desenhada (bbox do
    bloco 3D, que inclui a coroa) p/ bater com o desenho; None cai no cfg (envoltoria
    das estacas, menor). Pura (testavel sem FreeCAD)."""
    e = cfg.get("estaca") or {}
    b = cfg.get("bloco") or {}
    if a_cm is None:
        a_cm = b.get("a", 0) * 100
    if h_cm is None:
        h_cm = b.get("h", 0) * 100
    L = []
    if a_cm and h_cm:
        L.append("Bloco: %.0f x %.0f x h=%.0f cm (concreto fck 25 MPa)"
                 % (a_cm, a_cm, h_cm))
    if e:
        n = e.get("n", "") or ""
        tipo = e.get("tipo") or e.get("tipo_estaca") or ""
        L.append("Estaca: %s x D=%.0f cm, L=%.1f m%s"
                 % (n, e.get("D", 0) * 100, e.get("L", 0),
                    (" (%s)" % tipo if tipo else "")))
    L.append("Armadura e ancoragem conforme memoria de calculo "
             "(modelo biela-tirante, NBR 6118).")
    return L


# ─────────────────────────────────────────────────────────────────────────
# CARIMBO
# ─────────────────────────────────────────────────────────────────────────
def _carimbo(cfg, titulo, numero, escala, folha):
    import datetime
    return {
        "title": _cap_titulo(titulo),
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
        # compacto p/ caber na celula estreita do ISO5457 (evita colisao com scale)
        "general_tolerances": "NBR 8800/6118",
        # DO PROJETO (nao literal): ver _materiais_de_spec.
        "part_material": _txt_material(cfg.get("materiais")),
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
    fund = _pref(objs, ("SAPATA", "PEDESTAL", "PLACA", "NERVURA",
                        "ESTACA", "BLOCO", "BALDRAME"))
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
    # quadro COERENTE com o tipo de fundacao (estaca/bloco vs sapata) - detecta a
    # fundacao profunda pelos objetos 3D (ESTACA/BLOCO), nao so pelo cfg.
    tem_estaca = bool(_pref(fund, ("ESTACA", "BLOCO", "BALDRAME")))
    titq, hdrq, rowsq, nota = _quadro_fundacao(cfg, tem_estaca)
    if rowsq:
        _anot(doc, page, "A02q", [titq], 120, 175, 6)
        _tabela(doc, page, "Q02", hdrq, rowsq, 120, 150, tam=6,
                larguras=[90, 70, 70, 70])
    _anot(doc, page, "A02", ["PLANTA DE FUNDACOES   ESCALA %s" % nome, nota],
          200, 70, 6)
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
    # SNAP ao eixo do portico mais proximo; sem isso a faixa nao pegava nenhum
    # portico e caia no fallback 'frame=objs' (predio inteiro) -> escala errada e
    # o portico transbordava a folha. Ver _snap_portico.
    meio = _snap_portico(objs, eixo, meio)
    # inclui console e viga de rolamento da ponte (quando houver) no portico
    frame = _faixa(_pref(objs, ("PORTICO", "NERVURA", "MAO", "PLACA",
                                "PEDESTAL", "SAPATA", "CONSOLE_PONTE",
                                "VIGA_ROLAMENTO", "TRELICA")),
                   eixo, meio, bay * 0.45)
    if not _pref(frame, ("PORTICO",)):
        # fallback historico (predio inteiro): mantido para nao ficar sem desenho,
        # mas AGORA acusa - era exatamente o caminho que quebrava a escala do PE04.
        _aviso_prancha("PE04_PORTICO", "faixa nao capturou nenhum PORTICO - "
                       "usando o modelo inteiro (escala/enquadramento suspeitos)")
        frame = frame or objs
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
    import Part
    import FreeCAD as App
    b0 = base[0].Shape.BoundBox
    cx, cy = (b0.XMin + b0.XMax) / 2, (b0.YMin + b0.YMax) / 2
    um = _faixa(_faixa(base, "x", cx, 500), "y", cy, 500) or base[:6]
    db = _bbox(um)
    # TOCO DA COLUNA: sem ele o "detalhe da base de coluna" mostrava placa +
    # chumbadores + pedestal e NAO mostrava a coluna nem a solda coluna-placa -
    # justamente o que o montador precisa ver. A coluna INTEIRA estouraria a
    # escala, entao recorta-se so o trecho logo acima da placa (como no joelho).
    Z_TOCO = 600.0
    fonte = list(um)
    cxt = Part.makeBox(db.XLength + 400.0, db.YLength + 400.0,
                       (db.ZMax + Z_TOCO) - db.ZMin,
                       App.Vector(db.XMin - 200.0, db.YMin - 200.0, db.ZMin))
    toco = []
    for o in _pref(todos, ("PORTICO",)):
        try:
            if not _bb_overlap(o.Shape.BoundBox, cxt.BoundBox):
                continue
            com = o.Shape.common(cxt)
            if com.Edges:
                toco.append(com)
        except Exception:
            pass
    if toco:
        ft = doc.addObject("Part::Feature", "COLUNA_BASE_CROP")
        ft.Shape = Part.makeCompound(toco)
        fonte.append(ft)
    else:
        _aviso_prancha("PE06_DET_BASE", "sem toco de coluna no detalhe da base "
                       "(solda coluna-placa nao representada)")
    db = _bbox(fonte)
    esc, nome = _fit_escala(db, "y", *AREA_2V)
    page = _nova_prancha(doc, "PE06_DET_BASE",
                         _carimbo(cfg, "DETALHE - BASE DE COLUNA", "PE-06",
                                  nome, "06/09"))
    # vista frontal (placa + chumbadores + pedestal + toco da coluna)
    v1 = _vista(doc, page, "V06_BASE_FR", fonte, (0, -1, 0), (1, 0, 0),
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


def _pr_bloco(doc, cfg, objs, todos):
    """Detalhe do BLOCO DE COROAMENTO (so na fundacao PROFUNDA). Recorta a regiao
    de UM bloco (pedestal acima + bloco + topo das estacas) numa caixa (Part.common,
    padrao do _detalhe_ligacao) e mostra elevacao + planta + notas do calculo.
    Sem bloco (fundacao rasa) -> nenhuma prancha (retorna [],[]) - so aparece
    quando ha fundacao profunda."""
    import Part
    import FreeCAD as App
    blocos = _pref(objs, ("BLOCO",))
    if not blocos:
        return [], []
    fund = _pref(todos, ("BLOCO", "ESTACA", "PEDESTAL"))
    bbm = _bbox(objs)
    cx = (bbm.XMin + bbm.XMax) / 2.0
    cy = (bbm.YMin + bbm.YMax) / 2.0
    alvo = min(blocos, key=lambda o: abs(o.Shape.BoundBox.Center.x - cx)
               + abs(o.Shape.BoundBox.Center.y - cy))
    bc = alvo.Shape.BoundBox
    W = max(bc.XLength, bc.YLength) * 1.7
    ztop = bc.ZMax + 900.0             # inclui o pedestal acima do bloco
    zbot = bc.ZMin - 1100.0            # inclui o embutimento + trecho da estaca
    caixa = Part.makeBox(W, W, ztop - zbot,
                         App.Vector(bc.Center.x - W / 2, bc.Center.y - W / 2, zbot))
    cbb = caixa.BoundBox
    crops = []
    for o in fund:
        try:
            if not _bb_overlap(o.Shape.BoundBox, cbb):
                continue
            com = o.Shape.common(caixa)
            if com.Edges:
                crops.append(com)
        except Exception:
            pass
    if not crops:
        return [], []
    feat = doc.addObject("Part::Feature", "BLOCO_CROP")
    feat.Shape = Part.makeCompound(crops)
    jb = feat.Shape.BoundBox
    esc, nome = _fit_escala(jb, "y", *AREA_2V)
    page = _nova_prancha(doc, "PE15_DET_BLOCO",
                         _carimbo(cfg, "DETALHE - BLOCO DE COROAMENTO", "-", nome, "-"))
    # elevacao (frontal): pedestal + bloco + estacas descendo
    v1 = _vista(doc, page, "V15_BLOCO_FR", [feat], (0, -1, 0), (1, 0, 0),
                esc, 230, 350)
    hw1, hh1 = _paper_half(jb, esc, "y")
    c1 = _Cotador(doc, page, v1, hw1, hh1)
    c1.d((jb.XMin, jb.YMin, jb.ZMin), (jb.XMin, jb.YMin, jb.ZMax),
         "DistanceY", _fmt_mm(jb.ZLength), "esq")
    c1.d((jb.XMin, jb.YMin, jb.ZMax), (jb.XMax, jb.YMin, jb.ZMax),
         "DistanceX", _fmt_mm(jb.XLength), "baixo")
    # planta (topo): contorno do bloco + estacas + pedestal
    e2, n2 = _fit_escala(jb, "z", *AREA_2V)
    v2 = _vista(doc, page, "V15_BLOCO_TOP", [feat], (0, 0, 1), (1, 0, 0),
                e2, 600, 350)
    hw2, hh2 = _paper_half(jb, e2, "z")
    c2 = _Cotador(doc, page, v2, hw2, hh2)
    c2.d((jb.XMin, jb.YMin, jb.ZMax), (jb.XMax, jb.YMin, jb.ZMax),
         "DistanceX", _fmt_mm(jb.XLength), "baixo")
    c2.d((jb.XMin, jb.YMin, jb.ZMax), (jb.XMin, jb.YMax, jb.ZMax),
         "DistanceY", _fmt_mm(jb.YLength), "esq")
    linhas = ["BLOCO DE COROAMENTO   ESCALA %s" % nome,
              "Elevacao ESC %s   Planta ESC %s" % (nome, n2)]
    # dimensoes do bloco DA GEOMETRIA REAL desenhada (inclui a coroa) -> callout
    # bate com o desenho (nao a envoltoria menor do cfg).
    a_cm = round(max(bc.XLength, bc.YLength) / 10.0)
    h_cm = round(bc.ZLength / 10.0)
    linhas += _callout_bloco(cfg, a_cm=a_cm, h_cm=h_cm)
    linhas.append("Cotas em milimetros.")
    _anot(doc, page, "A15", linhas, 200, 95, 5)
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
    # SNAP ao eixo do portico mais proximo ANTES de fatiar e de posicionar a caixa
    # de recorte. Sem isso a janela ficava centrada no VAZIO entre dois porticos e
    # o "detalhe do joelho" saia sem coluna e sem rafter - so as pecas
    # longitudinais (terca/calha/tapamento) que cruzam o recorte, carimbadas como
    # se fossem o no viga-coluna. Mesmo bug do PE04. Ver _snap_portico.
    meio = _snap_portico(objs, eixo, meio)
    # Corta a janela em torno do no e mostra TUDO que cai dentro dela (sem
    # curadoria por prefixo): coluna, viga, mao-francesa, chapas, terca de
    # beiral, calha, tapamento etc. O que estiver no modelo aparece no corte.
    frame = _faixa(todos, eixo, meio, bay * 0.45)
    # canto do joelho (topo da coluna no lado y=0 / x=0)
    if comp_x:
        cx0, cy0, cz0 = meio, bb.YMin + 100.0, g["eave"]
    else:
        cx0, cy0, cz0 = bb.XMin + 100.0, meio, g["eave"]
    KW = 1500.0                                       # meia-janela horizontal (mm)
    # janela VERTICAL menor e assimetrica: o no do joelho e compacto em Z. Uma caixa
    # cubica (2KW=3 m) pegava ~1,5 m de coluna ABAIXO do beiral -> recorte alto-e-fino
    # -> _fit_escala reduzia a escala e a ligacao renderizava MINUSCULA (PE07). Agora
    # pega ~0,7 m de coluna (end plate + toco) abaixo e ~1,0 m de rafter acima do
    # beiral -> aspecto proximo do quadrado, ligacao grande. Caca sessao 14.
    Z_BELOW, Z_ABOVE = 700.0, 1000.0
    caixa = Part.makeBox(2 * KW, 2 * KW, Z_BELOW + Z_ABOVE,
                         App.Vector(cx0 - KW, cy0 - KW, cz0 - Z_BELOW))
    crops = []
    mao_bb = None
    tem_portico = False
    for o in frame:
        try:
            com = o.Shape.common(caixa)
            if com.Edges:
                crops.append(com)
                if o.Label.startswith("PORTICO"):
                    tem_portico = True
                if o.Label.startswith("MAO"):
                    mao_bb = com.BoundBox
        except Exception:
            pass
    # GUARDA DE CONTEUDO: um "detalhe do joelho" sem coluna/rafter no recorte nao
    # e um detalhe - e uma prancha que carimba tercas/calha como se fossem o no.
    # Nao aborta o executivo (o resto das pranchas e valido), mas ACUSA alto: sem
    # isto a falha e invisivel (o desenho fica bonito, so nao e o que promete).
    if crops and not tem_portico:
        _aviso_prancha("PE07_DET_JOELHO", "recorte do joelho nao contem PORTICO "
                       "(coluna/rafter) - detalhe nao representa o no viga-coluna")
    if not crops:
        _aviso_prancha("PE07_DET_JOELHO", "recorte vazio - prancha sem desenho")
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
    fab07 = _callout_fab(cfg, "joelho")
    _anot(doc, page, "A07", [
        "DETALHE DO NO VIGA-COLUNA (JOELHO)   ESCALA %s" % nome,
        "Colunas: %s   Vigas: %s" % (cfg.get("perfil_col", "?"),
                                     cfg.get("perfil_raf", "?"))]
        + fab07 + [
        "Mao-francesa, chapas e parafusos conforme memoria de calculo.",
        "Cotas em milimetros."], 200, 80 + 6 * len(fab07), 5)
    return [page], [c]


# Eixos de vista: (direcao, xdirection, eixo-de-profundidade p/ escala/cotas).
_AXES = {
    "x": ((-1, 0, 0), (0, -1, 0), "x"),   # elevacao olhando ao longo do comp.
    "y": ((0, -1, 0), (1, 0, 0), "y"),    # elevacao olhando ao longo do vao
    "z": ((0, 0, 1), (1, 0, 0), "z"),     # vista de topo (plano horizontal)
}

# Vedacao/cobertura nao entra em detalhe de ligacao de aco (placas chapadas).
_EXCLUI_LIGACAO = ("TELHA", "TAPAMENTO", "CALHA")

# Detalhes de ligacao: um por tipo presente no modelo. Eixo da elevacao CURADO
# por tipo (nao heuristica): os perfis conectados aparecem como perfil (linhas),
# como no joelho. `chapa` = eixo da 2a vista (face da chapa) ou None.
# (prefixo, titulo, base_pagina, KW_mm, elev_axis, chapa_axis)
LIGACOES = [
    # (prefixo, titulo, base, KW, elev, chapa, callout, sec_normal) - callout =
    # chave do cfg com a spec de fabricacao (do CALCULO); None => so "conforme
    # memorial". sec_normal = eixo da NORMAL do corte A-A; None = perpendicular a
    # elevacao (comportamento historico, bom quando a peca e uma CHAPA).
    # Para a FIXACAO DE GIRT o corte informativo e HORIZONTAL (normal z) = corte em
    # PLANTA na altura do clipe: mostra a secao do pilar, o clipe e a girt em planta,
    # que e como esse detalhe e desenhado na pratica. MEDIDO com o harness
    # scratchpad/probe_pe13.py (gera so este detalhe dentro do freecad.exe, onde a
    # cena grafica existe e getEdgeByIndex popula):
    #     normal y (historico) 14 arestas  -> abaixo do LIMIAR_SEC=15
    #     normal x (transversal a girt) 15 -> passava por UMA aresta
    #     normal z (planta)             25 -> corte de fato informativo
    ("CONEX_CUMEEIRA",   "DETALHE - LIGACAO DE CUMEEIRA",       "CUMEEIRA",   700, "x", "y", "joelho", None),
    ("CONEX_GUSSET_COB", "DETALHE - GUSSET CONTRAV. COBERTURA", "GUSSET_COB", 350, "z", None, "gusset", None),
    ("CONEX_GUSSET_PAR", "DETALHE - GUSSET CONTRAV. PAREDE",    "GUSSET_PAR", 350, "y", None, "gusset", None),
    ("CLIPE_GIRT",       "DETALHE - FIXACAO DE GIRT",           "CLIPE_GIRT", 400, "x", "y", None, "z"),
    ("CONEX_CONSOLE",    "DETALHE - CONSOLE DA PONTE ROLANTE",  "CONSOLE",    900, "x", None, "console", None),
]


def _svg_solda_filete(perna_mm, campo=False, todo_contorno=False, lado="arrow"):
    """SVG do simbolo AWS A2.4 de solda de FILETE. A perna vertical do triangulo fica
    SEMPRE a esquerda; a POSICAO em relacao a linha de referencia segue a norma:
      lado='arrow' -> triangulo ABAIXO da linha  = solda no lado da seta (arrow-side)
      lado='other' -> triangulo ACIMA  da linha  = solda no lado oposto (other-side)
      lado='both'  -> triangulos espelhados nos dois lados (ambos os lados)
    A linha de referencia esta em y=14. campo=bandeira (solda de campo);
    todo_contorno=circulo na dobra. Renderizado headless via DrawViewSymbol."""
    perna = ("%g" % perna_mm) if perna_mm else ""
    flag = ('<path d="M10,14 L10,7 L17,9 Z" fill="black"/>' if campo else "")
    circ = ('<circle cx="10" cy="14" r="2.6" fill="none" stroke="black" '
            'stroke-width="1"/>' if todo_contorno else "")
    tri_arrow = '<polygon points="30,14 38,14 30,24" fill="black"/>'   # abaixo (arrow)
    tri_other = '<polygon points="30,14 38,14 30,4" fill="black"/>'    # acima (other)
    if lado == "other":
        tri = tri_other
        txt = ('<text x="20" y="11" font-size="9" font-family="sans-serif">%s</text>'
               % perna if perna else "")
    elif lado == "both":
        tri = tri_arrow + tri_other
        txt = ('<text x="20" y="23" font-size="9" font-family="sans-serif">%s</text>'
               % perna if perna else "")
    else:                                                             # arrow (default)
        tri = tri_arrow
        txt = ('<text x="20" y="23" font-size="9" font-family="sans-serif">%s</text>'
               % perna if perna else "")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="34" '
        'viewBox="0 0 64 34">'
        '<g stroke="black" stroke-width="1" fill="none">'
        '<line x1="10" y1="14" x2="58" y2="14"/>'            # linha de referencia
        '<line x1="10" y1="14" x2="2" y2="26"/>'             # leader ate a junta
        '</g>'
        '<polygon points="2,26 8,22 7,25.5" fill="black"/>'  # ponta da seta
        + tri + circ + flag + txt +
        '</svg>')


def _glifo_solda(doc, page, nome, perna_mm, x, y, escala=1.6, campo=False,
                 todo_contorno=False, lado="arrow"):
    """Coloca o simbolo grafico de solda de filete (SVG AWS) na prancha, ligado ao
    dado do calculo (perna em mm). Substitui o DrawWeldSymbol (feature so-GUI).
    lado: arrow-side / other-side / both (AWS A2.4) - vem do dado de fabricacao."""
    try:
        sym = doc.addObject("TechDraw::DrawViewSymbol", nome)
        sym.Symbol = _svg_solda_filete(perna_mm, campo, todo_contorno, lado)
        try:
            sym.Scale = float(escala)
        except Exception:
            pass
        page.addView(sym)
        sym.X, sym.Y = float(x), float(y)
        return sym
    except Exception:
        return None


def _callout_fab(cfg, key):
    """Linha(s) de callout de fabricacao a partir do CFG (numeros do calculo).
    Retorna [] se nao houver dado -> mantem 'conforme memorial'."""
    d = cfg.get(key) if key else None
    if not d:
        return []
    if key == "joelho":
        return ["Parafusos: %d x %s   Chapa de topo t = %s"
                % (d["n"], _fmt_mm(d["db"]), _fmt_mm(d["t"]))]
    if key in ("gusset", "console"):
        return ["Chapa t = %s   Solda filete perna = %s"
                % (_fmt_mm(d["t_mm"]), _fmt_mm(d["perna_solda_mm"]))]
    return []


def _secao_ligacao(doc, page, base, feat, base_view, normal_corte, escala, x, y,
                   origem=None):
    """Corte SECCIONADO (TechDraw::DrawViewSection) do detalhe de ligacao: plano de
    corte por `origem`, normal = normal_corte, superficie cortada HACHURADA.
    Revela a espessura das chapas e a secao dos parafusos. Retorna a view, ou None
    se o corte nao produzir arestas (vazio -> nao engana o guard).

    `origem` = ponto por onde o plano passa; default = centro do bbox do compound.
    PASSE O CENTRO DA PECA DETALHADA: o compound inclui os perfis conectados
    (coluna, terca), que dominam o bbox e puxam o centro para FORA do conector.
    Foi o que quebrou o PE13 (clipe de girt): o plano passava ao lado do clipe e
    o "corte hachurado" saia um retangulo vazio (10 arestas vs 39/66/74 dos
    outros cortes) - texto prometia hachura e o desenho nao tinha nenhuma.

    NOTA: o blocker historico (T6, 'failed to create section CS' headless) foi
    resolvido no FreeCAD 1.1 - a secao constroi via freecadcmd/freecad.exe."""
    import FreeCAD as App
    if base_view is None or feat is None:
        return None
    try:
        sec = doc.addObject("TechDraw::DrawViewSection", "VLIG_SEC_" + base)
        sec.BaseView = base_view
        sec.Source = [feat]
        c = origem if origem is not None else feat.Shape.BoundBox.Center
        sec.SectionOrigin = App.Vector(c.x, c.y, c.z)
        sec.SectionNormal = App.Vector(*normal_corte)
        sec.SectionDirection = "Right"
        sec.ScaleType = "Custom"
        sec.Scale = escala
        # superficie cortada hachurada. Enum valido da TechDraw 1.1:
        # ['Hide','Color','SvgHatch','PatHatch']. SvgHatch usa o padrao svg
        # embutido (sem depender de .pat externo -> robusto headless).
        try:
            sec.CutSurfaceDisplay = "SvgHatch"
        except Exception:
            pass
        page.addView(sec)
        sec.X, sec.Y = float(x), float(y)
        # forca o recompute do proprio corte + do doc. No freecad.exe (GUI headless)
        # a geometria da secao pode computar DEFERIDA -> nao descartamos aqui pelo
        # n_edges (falso zero); o guard mne-1 (secao vazia) e checado no fim, apos
        # o render/export completo (detalhes_secoes).
        try:
            sec.recompute()
        except Exception:
            pass
        doc.recompute()
        return sec
    except Exception:
        return None


def _detalhe_ligacao(doc, cfg, todos, prefixo, titulo, base, KW, elev, chapa,
                     page_name, callout=None, sec_normal=None):
    """Uma prancha de detalhe de ligacao: elevacao (perfis edge-on = linhas)
    + opcional vista da chapa (face), recortando UMA instancia representativa
    (a mais proxima do centro do galpao) numa janela. Espelha o padrao do
    _pr_joelho. Retorna (page, [cotadores]) ou (None, None) se o tipo ausente."""
    import Part
    import FreeCAD as App
    pcs = _pref(todos, (prefixo,))
    if not pcs:
        return None, None
    bbm = _bbox(todos)
    cx = (bbm.XMin + bbm.XMax) / 2.0
    alvo = min(pcs, key=lambda o: abs(o.Shape.BoundBox.Center.x - cx))
    c0 = alvo.Shape.BoundBox.Center
    caixa = Part.makeBox(2 * KW, 2 * KW, 2 * KW,
                         App.Vector(c0.x - KW, c0.y - KW, c0.z - KW))
    cbb = caixa.BoundBox
    # telha/tapamento/calha nao fazem parte de um detalhe de LIGACAO de aco e
    # so poluem o corte (placas grandes chapadas). Exclui do crop; os perfis
    # estruturais e a ferragem (parafusos/chumbadores) ficam.
    crops = []
    for o in todos:
        try:
            if any(o.Label.startswith(p) for p in _EXCLUI_LIGACAO):
                continue
            if not _bb_overlap(o.Shape.BoundBox, cbb):
                continue
            com = o.Shape.common(caixa)
            if com.Edges:
                crops.append(com)
        except Exception:
            pass
    if not crops:
        return None, None
    feat = doc.addObject("Part::Feature", prefixo + "_CROP")
    feat.Shape = Part.makeCompound(crops)
    jb = feat.Shape.BoundBox
    dupla = chapa is not None
    dv, xv, ax = _AXES[elev]
    aw = 300.0 if dupla else 620.0
    esc, nome = _fit_escala(jb, ax, aw, 400)
    page = _nova_prancha(doc, page_name, _carimbo(cfg, titulo, "-", nome, "-"))
    xpos = 230.0 if dupla else 410.0
    v = _vista(doc, page, "VLIG_ELEV_" + base, [feat], dv, xv, esc, xpos, 350)
    hw, hh = _paper_half(jb, esc, ax)
    c = _Cotador(doc, page, v, hw, hh)
    # cota a altura (Z) da janela do detalhe
    c.d((jb.XMin, jb.YMin, jb.ZMin), (jb.XMin, jb.YMin, jb.ZMax),
        "DistanceY", _fmt_mm(jb.ZLength), "esq")
    cots = [c]
    n2 = None
    if dupla:
        dv2, xv2, ax2 = _AXES[chapa]
        e2, n2 = _fit_escala(jb, ax2, 300.0, 400)
        v2 = _vista(doc, page, "VLIG_CHAPA_" + base, [feat], dv2, xv2, e2, 600, 350)
        hw2, hh2 = _paper_half(jb, e2, ax2)
        c2 = _Cotador(doc, page, v2, hw2, hh2)
        # cota largura+altura da face da chapa
        if ax2 == "y":
            c2.d((jb.XMin, jb.YMin, jb.ZMax), (jb.XMax, jb.YMin, jb.ZMax),
                 "DistanceX", _fmt_mm(jb.XLength), "baixo")
        else:
            c2.d((jb.XMin, jb.YMin, jb.ZMax), (jb.XMin, jb.YMax, jb.ZMax),
                 "DistanceY", _fmt_mm(jb.YLength), "esq")
        cots.append(c2)
    # CORTE SECCIONADO: hachura a superficie de material cortada (espessura das
    # chapas + secao dos parafusos). Normal do corte = xdir da elevacao (corta
    # perpendicular a ela, pelo centro). Best-effort: se vazio, nao desenha.
    _sx, _sy = _pos_corte_ligacao(dupla, xpos)
    # corta pelo centro da PECA detalhada (c0 = o conector alvo), nao pelo centro
    # do compound - este ultimo e puxado pelos perfis conectados. Ver _secao_ligacao.
    _nrm = _AXES[sec_normal][0] if sec_normal else xv
    # NAO deslocar a origem do plano de corte: tentei desloca-la 25% para fora do
    # plano medio da peca (hipotese: plano tangente a alma da coluna gerava corte
    # degenerado) e o TechDraw TRAVOU - o executivo estourou 1200 s sem gerar
    # nenhuma prancha. Origem = centro da peca alvo, como antes.
    sec = _secao_ligacao(doc, page, base, feat, v, _nrm, esc, _sx, _sy, origem=c0)
    tem_sec = sec is not None
    linhas = ["%s   ESCALA %s" % (titulo, nome)]
    if n2:
        linhas.append("Elevacao ESC %s   Vista da chapa ESC %s" % (nome, n2))
    if tem_sec:
        linhas.append("Corte A-A seccionado (material hachurado) ESC %s" % nome)
    fab = _callout_fab(cfg, callout)
    linhas += fab
    linhas += ["Chapas, solda e parafusos conforme memoria de calculo.",
               "Cotas em milimetros."]
    _anot(doc, page, "ALIG_" + base, linhas, 200, 80 + 6 * len(fab), 5)
    # simbolo grafico AWS de solda de filete (quando o callout tras a perna do
    # calculo): glyph ligado ao dado, headless via DrawViewSymbol (nao DrawWeldSymbol).
    dfab = cfg.get(callout) if callout else None
    if isinstance(dfab, dict) and dfab.get("perna_solda_mm"):
        # lado/campo vem do dado de fabricacao (AWS A2.4); default arrow-side + campo?
        lado = dfab.get("lado_solda", "arrow")
        campo = bool(dfab.get("solda_campo", False))
        _anot(doc, page, "WLDt_" + base, ["SIMBOLO DE SOLDA (AWS A2.4):"], 150, 200, 4)
        _glifo_solda(doc, page, "WLD_" + base, dfab["perna_solda_mm"],
                     x=210, y=170, escala=7.0, todo_contorno=True,
                     campo=campo, lado=lado)
    return page, cots


def _pr_ligacoes(doc, cfg, objs, todos):
    """Uma prancha de detalhe por tipo de ligacao presente no modelo."""
    paginas, cotadores = [], []
    for i, (pref, titulo, base, KW, elev, chapa, callout, sec_n) in enumerate(LIGACOES):
        pg_name = "PE%02d_DET_%s" % (10 + i, base)
        try:
            pg, cts = _detalhe_ligacao(doc, cfg, todos, pref, titulo, base,
                                       KW, elev, chapa, pg_name, callout,
                                       sec_normal=sec_n)
        except Exception as ex:
            import FreeCAD as App
            App.Console.PrintError("Detalhe ligacao %s: %s\n" % (pref, ex))
            pg, cts = None, None
        if pg is not None:
            paginas.append(pg)
            cotadores += cts or []
    return paginas, cotadores


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
        linhas.append("Terca: %s" % _fmt_terca(tc))
    linhas.append("Cotas em metros.")
    _anot(doc, page, "A08", linhas, 200, 80, 5)
    return [page], [c]


def _notas_do_modelo(doc):
    """Notas tecnicas cujos numeros sao MEDIDOS no modelo, nao afirmados.

    Estas notas vao para a OBRA. Duas estavam erradas por serem texto fixo:
      - "RN +0,00 = topo do concreto (base das placas)": Z=0 nao e nem um nem
        outro. Medido: topo do concreto -100, base da placa -70, topo +30. Quem
        locasse cotas por essa nota erraria 100 mm.
      - "Chumbadores ... com gancho 180 mm": o gancho do modelo tem 60 mm.
    Retorna {"niveis":..., "chumbador":..., "contrav":...} (None se ausente).
    """
    out = {}
    try:
        alvo = {}
        for o in doc.Objects:
            if not hasattr(o, "Shape") or o.Shape.isNull() or o.Shape.Volume <= 0:
                continue
            for pref in ("PLACA_BASE", "PEDESTAL", "BLOCO", "SAPATA",
                         "CHUMBADOR_GANCHO", "CONTRAV"):
                if o.Name.startswith(pref) and pref not in alvo:
                    alvo[pref] = o.Shape.BoundBox
        pl = alvo.get("PLACA_BASE")
        conc = alvo.get("PEDESTAL") or alvo.get("BLOCO") or alvo.get("SAPATA")
        if pl is not None and conc is not None:
            out["niveis"] = (
                "2. RN +0,00 = referencia do modelo. Topo do concreto %+.0f mm; "
                "face inf. da placa %+.0f mm (graute %.0f mm); face sup. %+.0f mm."
                % (conc.ZMax, pl.ZMin, pl.ZMin - conc.ZMax, pl.ZMax))
        g = alvo.get("CHUMBADOR_GANCHO")
        if g is not None:
            out["chumbador"] = ("7. Chumbadores ASTM A36, gancho %.0f mm."
                                % max(g.XLength, g.YLength, g.ZLength))
        c = alvo.get("CONTRAV")
        if c is not None:
            import math as _m
            _L = _m.sqrt(c.XLength ** 2 + c.YLength ** 2 + c.ZLength ** 2)
            _d = 2.0 * (_area_barra(doc, "CONTRAV") / _m.pi) ** 0.5 if _L else 0.0
            if _d > 0:
                out["contrav"] = ("8. Contraventamento: barras d%.0f "
                                  "pretensionadas c/ esticador." % _d)
    except Exception:
        pass
    return out


def _area_barra(doc, pref):
    """Area da secao de uma barra redonda = Volume / comprimento do eixo."""
    import math as _m
    for o in doc.Objects:
        if o.Name.startswith(pref) and hasattr(o, "Shape") and o.Shape.Volume > 0:
            b = o.Shape.BoundBox
            L = _m.sqrt(b.XLength ** 2 + b.YLength ** 2 + b.ZLength ** 2)
            return o.Shape.Volume / L if L > 1e-6 else 0.0
    return 0.0


def _pr_quadros(doc, cfg):
    page = _nova_prancha(doc, "PE09_QUADROS",
                         _carimbo(cfg, "QUADROS E NOTAS TECNICAS", "PE-09",
                                  "-", "09/09"))
    # QUADRO DE VERIFICACOES (utilizacoes do calculo, NBR 8800)
    res = [(k, v) for k, v in (cfg.get("resultados") or {}).items()
           if v is not None]
    ESC_Q = 1.5                      # ampliacao dos quadros p/ legibilidade em A1
    n_verif = 0
    if res:
        _anot(doc, page, "A09v",
              ["QUADRO DE VERIFICACOES ESTRUTURAIS (NBR 8800)"], 210, 510, 9)
        rows = [[k, "%.2f" % float(v), "OK" if float(v) <= 1.001 else "REVER"]
                for k, v in res]
        n_verif = len(rows)
        _tabela(doc, page, "Q09V", ["ELEMENTO", "UTILIZACAO n/Rd", "SITUACAO"],
                rows, 210, 480 - n_verif * 7, tam=6, larguras=[170, 130, 100],
                escala=ESC_Q)
    # QUADRO DE MATERIAIS (takeoff do modelo 3D)
    tk = [r for r in (cfg.get("takeoff") or []) if "Alvenaria" not in str(r[0])]
    n_mat = 0
    if not tk and not (cfg.get("romaneio")):
        # O takeoff vem de spec["estrutura"]["takeoff"], que SO o montar_modelo
        # grava. Mas `rodar_executivo` e projetado para rodar SOZINHO sobre um
        # FCStd ja salvo - e nesse caminho o QUADRO DE MATERIAIS sumia da prancha
        # em SILENCIO, deixando meia folha em branco numa prancha intitulada
        # "QUADROS E NOTAS TECNICAS". A guarda por prancha reportava 0 avisos.
        _aviso_prancha("PE09_QUADROS",
                       "QUADRO DE MATERIAIS ausente: cfg['takeoff'] vazio (rode "
                       "montar_modelo antes, ou use rodar_tudo)")
        _anot(doc, page, "A09m",
              ["QUADRO DE MATERIAIS - ACO",
               "NAO DISPONIVEL NESTA EXECUCAO",
               "(quantitativo sai do modelo 3D - ver takeoff/*.csv)"],
              560, 510, 9)
    if tk:
        tk = sorted(tk, key=lambda r: -float(r[4]))[:16]
        rows_m = [[str(r[0]), str(r[1]), str(r[2]), "%.0f" % float(r[4])]
                  for r in tk]
        rows_m.append(["TOTAL", "", "", "%.0f" % sum(float(r[4]) for r in tk)])
        n_mat = len(rows_m)
        _anot(doc, page, "A09m", ["QUADRO DE MATERIAIS - ACO"], 560, 510, 9)
        _tabela(doc, page, "Q09M", ["ELEMENTO", "PERFIL", "QTD", "MASSA (kg)"],
                rows_m, 560, 480 - n_mat * 7, tam=6,
                larguras=[150, 130, 60, 110], escala=ESC_Q)
    # ROMANEIO - MARCAS DE PECA (entregavel de fabricacao, do calculo). Lista as
    # pecas PRIMARIAS com marca (C1, V1..) / qtd / peso. Definitivo (secundarios,
    # chapas, furacao) sai do modelo 3D. Renderizado abaixo do quadro de materiais.
    rom = cfg.get("romaneio") or []
    if rom:
        rows_r = [[str(it["marca"]), str(it["descricao"])[:20], str(it["perfil"]),
                   str(it["qtd"]), "%.0f" % float(it["peso_total_kg"])] for it in rom]
        rows_r.append(["TOTAL", "", "", "", "%.0f" % sum(float(i["peso_total_kg"]) for i in rom)])
        # posicao FIXA na zona inferior-direita vazia da folha (limpa tanto com
        # quadro de materiais longo quanto sem ele) -> nunca sobrepoe. _tabela
        # posiciona pelo CENTRO da view; cabecalho logo acima.
        rom_centro = 210.0
        _anot(doc, page, "A09r", ["ROMANEIO - MARCAS DE PECA (primarias; do calculo)"],
              560, rom_centro + (len(rows_r) + 1) * 7 + 10, 9)
        _tabela(doc, page, "Q09R", ["MARCA", "DESCRICAO", "PERFIL", "QTD", "PESO (kg)"],
                rows_r, 560, rom_centro, tam=6,
                larguras=[70, 180, 100, 50, 100], escala=ESC_Q)
    # NOTAS TECNICAS - posicionadas SEMPRE abaixo das tabelas (evita o overlap)
    _mt = cfg.get("materiais") or {}
    # notas 3 e 4 DO PROJETO. Sem o dado, a nota diz "conforme memorial" em vez de
    # imprimir um numero fixo que pode contradizer o calculo (o desenho vai p/ a obra).
    _n3 = "3. Aco estrutural %s (NBR 8800). Armadura CA-%d." % (
        _mt.get("aco", "MR250"), round((_mt.get("fyk_MPa") or 500) / 10.0))
    _cob = _mt.get("cobrimento_cm") or 5
    _n4 = ("4. Concreto fck %d MPa. Cobrimento %s cm (fund.), 3 cm (sup.)."
           % (_mt["fck_MPa"], ("%g" % _cob).replace(".", ","))
           if _mt.get("fck_MPa") else
           "4. Concreto e cobrimento conforme memorial de calculo.")
    # notas com numero: MEDIDAS no modelo (ver _notas_do_modelo). O texto fixo
    # dizia "RN +0,00 = topo do concreto (base das placas)" - falso nos dois lados
    # - e "gancho 180 mm" contra 60 mm reais.
    _nm = _notas_do_modelo(doc)
    # ligacoes de campo: soldadas (padrao dos galpoes) ou parafusadas (escolha do
    # eng. no wizard). O desenho vai p/ a obra -> a nota indica o metodo adotado.
    _lig = (_mt.get("tipo_ligacao") or "soldada").lower()
    if _lig == "parafusada":
        _n5 = "5. LIGACOES DE CAMPO PARAFUSADAS. Parafusos A325 (fub 825 MPa) protendidos."
        _n6 = "6. Soldas E70XX (fw 485 MPa) nas ligacoes de fabrica; filete minimo 6 mm."
    else:
        _n5 = "5. LIGACOES DE CAMPO SOLDADAS. Soldas E70XX (fw 485 MPa), filete minimo 6 mm."
        _n6 = "6. Parafusos A325 (fub 825 MPa) apenas nas ligacoes de montagem indicadas."
    notas = cfg.get("notas") or [
        "NOTAS TECNICAS GERAIS",
        "1. Cotas em metros nas vistas gerais; em mm nos detalhes.",
        _nm.get("niveis", "2. Niveis conforme memorial de calculo."),
        _n3,
        _n4,
        _n5,
        _n6,
        _nm.get("chumbador", "7. Chumbadores ASTM A36 conforme detalhe da base."),
        _nm.get("contrav", "8. Contraventamento pretensionado c/ esticador."),
        "9. Tercas Ue formado a frio (NBR 14762).",
        "10. Projeto executivo sujeito a revisao e ART.",
    ]
    notas_y = _pos_notas(n_verif, n_mat, len(notas))
    _bloco_texto(doc, page, "A09n", notas, 210, notas_y, tam=5, largura=560,
                 escala=1.4)
    return [page], []


# ─────────────────────────────────────────────────────────────────────────
# ORQUESTRACAO (roda dentro do freecad.exe, disparada por QTimer)
# ─────────────────────────────────────────────────────────────────────────
def gerar_executivo(cfg):
    import FreeCAD as App
    import FreeCADGui as Gui

    # zera os avisos: estado de MODULO herdaria os avisos do projeto anterior se
    # dois executivos rodassem no mesmo processo (mesma armadilha do _CFG do vento).
    del AVISOS_PRANCHA[:]

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
                    _pr_contravent, _pr_base, _pr_joelho, _pr_fechamento,
                    _pr_ligacoes, _pr_bloco]
    for fn in construtores:
        try:
            if fn in (_pr_base, _pr_joelho, _pr_contravent, _pr_ligacoes,
                      _pr_bloco):
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

    # Numeracao dinamica: o total de pranchas varia por projeto (detalhes de
    # ligacao so saem se o tipo existe). O drawing_number segue o codigo de TIPO
    # da prancha (do nome 'PEnn_...', batendo com o nome do arquivo); o
    # sheet_number e a posicao sequencial 'NN/TOTAL'. Antes o drawing_number era
    # sobrescrito pela ordem (arquivo PE11 exibia 'PE-09') - ver _codigo_prancha.
    total = len(paginas)
    for i, p in enumerate(paginas, 1):
        try:
            tpl = p.Template
            et = tpl.EditableTexts
            nome_pg = getattr(p, "Name", "") or getattr(p, "Label", "")
            numero, folha = _codigo_prancha(nome_pg, i, total)
            if "drawing_number" in et:
                et["drawing_number"] = numero
            if "sheet_number" in et:
                et["sheet_number"] = folha
            tpl.EditableTexts = et
        except Exception:
            pass

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

    # edge-count das elevacoes de ligacao (proxy anti-silhueta chapada) e das
    # SECOES seccionadas (corte hachurado - Fase 5).
    edges = {}
    secoes = {}
    for o in doc.Objects:
        try:
            if o.Name.startswith("VLIG_ELEV") and o.TypeId == "TechDraw::DrawViewPart":
                edges[o.Name] = _n_edges(o)
            elif o.Name.startswith("VLIG_SEC"):
                secoes[o.Name] = _n_edges(o)
        except Exception:
            pass

    return {"ok": True, "pranchas": [p.Name for p in paginas],
            "arquivos": arquivos, "fcstd": fcstd_out, "cobertura": cob,
            "avisos_prancha": list(AVISOS_PRANCHA),
            "detalhes_edges": edges, "detalhes_secoes": secoes}


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


def _descreve_perfis(est):
    """Rotulo (perfil_col, perfil_raf) para o callout. Em portico de ALMA VARIAVEL
    a viga (e a coluna, se h_col_base) e chapa soldada tapered - NAO um laminado;
    descreve a chapa a partir do dict tapered do calculo. Em TESOURA descreve a
    trelica. Caso contrario usa os perfis laminados adotados."""
    col = est.get("perfil_col_adotado", "?")
    raf = est.get("perfil_raf_adotado", "?")
    tipo = est.get("tipo_portico", "prismatico")
    tp = est.get("tapered")
    if tipo == "alma_variavel" and isinstance(tp, dict):
        hj = tp.get("h_joelho", 0) * 1000.0; hc = tp.get("h_cumeeira", 0) * 1000.0
        tw = tp.get("tw", 0) * 1000.0; bf = tp.get("bf", 0) * 1000.0
        tf = tp.get("tf", 0) * 1000.0
        raf = ("Alma variavel h=%.0f->%.0f (tw=%.0f, mesa %.0fx%.1f) mm"
               % (hj, hc, tw, bf, tf))
        if tp.get("h_col_base"):
            hcb = tp["h_col_base"] * 1000.0
            col = ("Alma variavel h=%.0f->%.0f (tw=%.0f, mesa %.0fx%.1f) mm"
                   % (hcb, hj, tw, bf, tf))
    elif tipo == "tesoura" and isinstance(est.get("trelica"), dict):
        tr = est["trelica"]
        raf = ("Trelica %s h=%.0f mm, %d paineis (banzo/diagonal cfg calculo)"
               % (tr.get("tipo", "warren"), tr.get("h", 0) * 1000.0,
                  tr.get("n_paineis", 0)))
    return col, raf


def _nome_aco(spec, fy_kPa):
    """Designacao do aco p/ o carimbo. Prefere a CLASSE escolhida no spec; sem
    ela, deriva do fy pela tabela de `acos` (fonte: Pfeil/NBR 8800 Cap.1).
    Nao inventa designacao: fy sem correspondencia sai como "fy=XXX MPa"."""
    import acos
    esc = (spec.get("estrutura", {}) or {}).get("aco")
    return acos.normaliza(esc) or acos.nome_por_fy(fy_kPa)


def _materiais_de_spec(spec):
    """Materiais do projeto p/ o carimbo e as notas (MPa / cm). Le do spec; sem o
    campo, devolve None no item -> o texto omite em vez de MENTIR um valor."""
    fu = spec.get("fundacao", {}) or {}

    def _mpa(v):                       # spec guarda em kPa
        return round(v / 1000.0) if isinstance(v, (int, float)) and v else None

    def _cm(v):                        # spec guarda em m
        return round(v * 100.0, 1) if isinstance(v, (int, float)) and v else None
    import acos
    est = spec.get("estrutura", {}) or {}
    fy_kPa = acos.propriedades(est.get("aco") or acos.PADRAO)[0]
    return {"fy_MPa": round(fy_kPa / 1000.0), "aco": _nome_aco(spec, fy_kPa),
            "fck_MPa": _mpa(fu.get("fck")), "fyk_MPa": _mpa(fu.get("fyk")),
            "cobrimento_cm": _cm(fu.get("cobrimento")),
            "tipo_ligacao": (est.get("tipo_ligacao") or "soldada").lower()}


def _txt_material(mat):
    """Linha compacta do carimbo (celula estreita do ISO5457)."""
    mat = mat or {}
    p = ["ACO %s" % mat.get("aco", "MR250")]
    if mat.get("fck_MPa"):
        p.append("CONCRETO fck %d MPa" % mat["fck_MPa"])
    # tipo de ligacao NAO entra aqui (celula estreita do ISO5457 estoura); vai na
    # nota tecnica 5 da PE09 (lugar canonico das notas gerais).
    return " / ".join(p)


def config_de_spec(spec, fcstd_path, out_dir):
    g = spec["geometria"]
    est = spec.get("estrutura", {})
    ba = est.get("base_adotada")
    sp = est.get("sapata_adotada")
    jo = est.get("joelho_adotado")
    perfil_col, perfil_raf = _descreve_perfis(est)
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
        "perfil_col": perfil_col,
        "perfil_raf": perfil_raf,
        "base": ({"B": ba["B"] * 1000.0, "L": ba["L"] * 1000.0,
                  "t": ba["t"] * 1000.0, "db": ba["db"] * 1000.0,
                  "n": ba["n"]} if ba else None),
        "sapata": ({"B": sp["B"], "L": sp["L"], "h": sp["h"]} if sp else None),
        # fundacao PROFUNDA (estaca/bloco) - alimenta o quadro correto na PE02
        # (nao "QUADRO DE SAPATAS"). Dims em m (o quadro converte p/ cm).
        "estaca": est.get("estaca_adotada"),
        "bloco": est.get("bloco_adotado"),
        # ligacoes (para callouts de fabricacao): joelho {n, db, t} do calculo;
        # gusset/console ja em mm/adotado do calculo.
        "joelho": ({"n": jo["n"], "db": jo["db"] * 1000.0, "t": jo["t"] * 1000.0}
                   if jo else None),
        "gusset": est.get("gusset_adotado"),
        "console": est.get("console_adotado"),
        "terca": est.get("terca_dims"),
        "ponte": ({"Hvr": spec["ponte"].get("Hvr", 4.5) * 1000.0,
                   "Q": spec["ponte"].get("Q")}
                  if spec.get("ponte") else None),
        # MATERIAIS do projeto (MPa / cm). O carimbo e as notas tecnicas imprimiam
        # "ACO MR250 / CONCRETO fck 25 MPa" e "Cobrimento 5 cm" FIXOS: um projeto
        # com fck 40 e cobrimento 7,5 cm (classe de agressividade mais severa)
        # recebia prancha mandando executar 25 MPa e 5 cm. O desenho vai p/ a OBRA.
        "materiais": _materiais_de_spec(spec),
        "resultados": est.get("resultados", {}),
        "takeoff": est.get("takeoff", []),
        "romaneio": est.get("romaneio") or [],
    }


def codigo_fonte():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "techdraw_exec.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _para_nativo(o):
    """Converte RECURSIVAMENTE escalares/arrays numpy em tipos nativos do Python.
    Necessario porque o cfg e embutido no script do freecad.exe via repr (%r): no
    numpy>=2 o repr de um np.float64 e 'np.float64(0.91)', que quebra no freecad
    com 'name np is not defined' (o freecad nao importa numpy como np). Preserva
    dict/list/tuple. Sem importar numpy (duck typing por .item()/.tolist())."""
    if isinstance(o, dict):
        return {k: _para_nativo(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_para_nativo(v) for v in o]
    if isinstance(o, tuple):
        return tuple(_para_nativo(v) for v in o)
    if isinstance(o, (str, bytes, bool)) or o is None:
        return o
    if hasattr(o, "item") and not isinstance(o, (int, float)):   # np.float64/np.int_
        try:
            return o.item()
        except Exception:
            pass
    if hasattr(o, "tolist"):                                     # np.ndarray
        try:
            return o.tolist()
        except Exception:
            pass
    return o


def script_bootstrap(cfg):
    """Monta o script que o freecad.exe roda: injeta cfg + fonte deste modulo
    e dispara _entry via QTimer (apos o loop de eventos subir). O cfg passa por
    _para_nativo para nao vazar repr de numpy (np.float64(...)) - ver bug tesoura."""
    return ("# -*- coding: utf-8 -*-\n"
            "_CFG_ = %r\n" % (_para_nativo(cfg),) + codigo_fonte() +
            "\nfrom PySide import QtCore\n"
            "QtCore.QTimer.singleShot(1500, lambda: _entry(_CFG_))\n")
