# ============================================================================
# techdraw_concreto.py - PROJETO EXECUTIVO (pranchas A1 TechDraw) do GALPAO DE
# CONCRETO PRE-MOLDADO, a partir do modelo 3D salvo (build_concreto -> .FCStd).
# ----------------------------------------------------------------------------
# Roda DENTRO do freecad.exe (GUI -> exportPageAsPdf), disparado por QTimer, sem
# interacao (mesma mecanica do techdraw_exec do aco: abre a MDI da page p/ montar
# a cena, exporta, fecha sozinho). freecadcmd (console) NAO exporta PDF.
#
# Reusa os HELPERS GENERICOS do techdraw_exec (template ISO A1, _vista, _Cotador,
# _carimbo, _fit_escala, _tabela, ...) importando o modulo IRMAO. O executivo e
# lancado num freecad.exe NOVO a cada projeto (subprocess), entao esse import de
# irmao roda em processo LIMPO - a armadilha de cache-de-modulo do bridge nao se
# aplica (ver memoria cache-modulo-irmao-freecad).
#
# CONVENCAO DE EIXOS (build_concreto, OPOSTA ao aco): X = vao (largura), Y =
# comprimento, Z = altura. As pecas do modelo tem Label = MARCA: P1E/P1D (pilar),
# VC1 (viga de cobertura), SAP1E/SAP1D (sapata).
#
# Roda em DOIS contextos: FORA do FreeCAD (config_de_spec, codigo_fonte,
# script_bootstrap) e DENTRO (gerar_executivo/_entry + helpers com FreeCAD).
# ============================================================================
import os

# Helpers genericos do irmao (sem FreeCAD no topo do techdraw_exec -> import seguro
# tanto fora quanto dentro do freecad.exe, desde que o dir do galpao_fw esteja no
# sys.path - o script_bootstrap prepende).
from techdraw_exec import (
    _nova_prancha, _vista, _Cotador, _anot, _tabela, _bloco_texto,
    _carimbo, _fit_escala, _bbox, _fmt_m, _fmt_mm, _paper_half, _ESC_NOME,
    _svg_para_png, AREA_1V, AREA_2V)


# ─────────────────────────────────────────────────────────────────────────
# SELECAO DE PECAS (dentro do FreeCAD) - por MARCA (Label)
# ─────────────────────────────────────────────────────────────────────────
def _por_marca(objs, *prefixos):
    """Objetos cujo Label comeca por um dos prefixos de marca (P/VC/SAP)."""
    return [o for o in objs if any(o.Label.startswith(p) for p in prefixos)]


def _carimbo_conc(cfg, titulo, numero, escala, folha):
    """Carimbo do concreto: reusa o generico do techdraw_exec, mas CORRIGE os
    campos com default de ACO (o modelo e de concreto). Sem isso o carimbo saía
    'ACO MR250 / CONCRETO fck 30 MPa' e tolerancias 'NBR 8800/6118' - normas de
    ACO numa prancha de concreto armado."""
    car = _carimbo(cfg, titulo, numero, escala, folha)
    # compacto (celula estreita do ISO5457): notacao BR 'C30' evita transbordar
    # para o campo de tolerancias.
    car["part_material"] = "CONCRETO C%d / %s" % (int(cfg["fck_MPa"]), cfg["aco"])
    car["general_tolerances"] = "NBR 6118/9062"
    return car


def _cy(o):
    b = o.Shape.BoundBox
    return (b.YMin + b.YMax) / 2.0


def _frame_do_meio(objs, s_mm, n):
    """Objetos do PORTICO central (uma faixa em Y). O portico j fica em
    y = j*s; escolhe o mais proximo do meio do comprimento e recorta +-s/3."""
    jm = max(0, min(n - 1, n // 2))
    y = jm * s_mm
    meia = max(s_mm / 3.0, 300.0)
    frame = [o for o in objs if abs(_cy(o) - y) <= meia]
    return frame, y


# ─────────────────────────────────────────────────────────────────────────
# PRANCHAS (rodam dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def _pr_formas(doc, cfg, objs):
    """PE01 - PLANTA DE FORMAS: vista de topo (malha de pilares/sapatas + vigas),
    cotada no vao (X), no comprimento (Y) e na cadeia de vaos entre porticos."""
    g = cfg["geo"]
    bb = _bbox(objs)
    esc, nome = _fit_escala(bb, "z", *AREA_1V)
    page = _nova_prancha(doc, "PE01_FORMAS",
                         _carimbo_conc(cfg, "PLANTA DE FORMAS", "PE-01", nome, "01/03"))
    v = _vista(doc, page, "V01_FORMAS", objs, (0, 0, 1), (1, 0, 0),
               esc, 410, 350, coarse=True)
    hw, hh = _paper_half(bb, esc, "z")
    c = _Cotador(doc, page, v, hw, hh)
    vao, comp, s, n = g["vao"], g["comprimento"], g["s"], g["n"]
    z = bb.ZMax
    x0 = -vao / 2.0
    # cadeia de vaos entre porticos (ao longo de Y)
    for i in range(max(0, n - 1)):
        c.d((x0, i * s, z), (x0, (i + 1) * s, z), "DistanceY",
            _fmt_m(s), "esq", nivel=0)
    c.d((x0, 0, z), (x0, comp, z), "DistanceY", _fmt_m(comp), "esq", nivel=1)
    c.d((-vao / 2.0, 0, z), (vao / 2.0, 0, z), "DistanceX", _fmt_m(vao), "baixo")
    _anot(doc, page, "A01",
          ["PLANTA DE FORMAS   ESCALA %s" % nome,
           "Pilares %s cm  -  Vigas de cobertura %s cm" %
           (cfg["sec_pilar_lbl"], cfg["sec_viga_lbl"]),
           "Cotas em metros. RN +0,00 = topo da fundacao."],
          200, 70, 6)
    return [page], [c]


def _pr_portico(doc, cfg, objs):
    """PE02 - PORTICO TIPICO: elevacao de um portico (2 pilares + viga de
    cobertura), olhando ao longo do comprimento (Y). Cotada no vao e no pe-direito."""
    g = cfg["geo"]
    frame, _y = _frame_do_meio(objs, g["s"], g["n"])
    frame = frame or objs
    fb = _bbox(frame)
    esc, nome = _fit_escala(fb, "y", *AREA_1V)
    page = _nova_prancha(doc, "PE02_PORTICO",
                         _carimbo_conc(cfg, "PORTICO TIPICO", "PE-02", nome, "02/03"))
    # olha em -Y -> plano X-Z (vao na horizontal, altura na vertical)
    v = _vista(doc, page, "V02_PORTICO", frame, (0, -1, 0), (1, 0, 0),
               esc, 410, 350)
    hw, hh = _paper_half(fb, esc, "y")
    c = _Cotador(doc, page, v, hw, hh)
    vao, H = g["vao"], g["H"]
    yy = _y
    c.d((-vao / 2.0, yy, 0.0), (vao / 2.0, yy, 0.0), "DistanceX", _fmt_m(vao), "baixo")
    c.d((-vao / 2.0, yy, 0.0), (-vao / 2.0, yy, H), "DistanceY", _fmt_m(H), "esq")
    linhas = ["PORTICO TIPICO   ESCALA %s" % nome,
              "Pilar (balanco, engastado no calice): %s cm" % cfg["sec_pilar_lbl"],
              "Viga de cobertura: %s cm%s" % (cfg["sec_viga_lbl"], cfg["viga_arm_lbl"]),
              "Cotas em metros. Pilar pre-moldado, ligacao base por calice (NBR 9062)."]
    _anot(doc, page, "A02", linhas, 200, 72, 6)
    return [page], [c]


def _pr_quadros(doc, cfg):
    """PE03 - QUADROS + NOTAS: quadro de pilares, vigas e sapatas, notas de
    materiais e o quantitativo de concreto (volume/massa)."""
    page = _nova_prancha(doc, "PE03_QUADROS",
                         _carimbo_conc(cfg, "QUADROS E ESPECIFICACOES", "PE-03",
                                       "-", "03/03"))
    # QUADRO DE PILARES
    _anot(doc, page, "A03p", ["QUADRO DE PILARES"], 175, 500, 7)
    _tabela(doc, page, "Q03P", ["MARCA", "SECAO (cm)", "As (cm2)", "TAXA (%)"],
            cfg["quadro_pilares"], 175, 470, tam=6, larguras=[90, 110, 90, 90],
            escala=1.4)
    # QUADRO DE VIGAS
    _anot(doc, page, "A03v", ["QUADRO DE VIGAS DE COBERTURA"], 175, 380, 7)
    _tabela(doc, page, "Q03V", cfg["quadro_vigas_hdr"], cfg["quadro_vigas"],
            175, 350, tam=6, larguras=[90, 110, 160], escala=1.4)
    # QUADRO DE FUNDACAO
    _anot(doc, page, "A03f", [cfg["quadro_fund_titulo"]], 175, 270, 7)
    _tabela(doc, page, "Q03F", cfg["quadro_fund_hdr"], cfg["quadro_fund"],
            175, 240, tam=6, larguras=[90, 90, 90, 90], escala=1.4)
    # NOTAS + QUANTITATIVO (bloco de texto a esquerda)
    _bloco_texto(doc, page, "N03", cfg["notas"], 175, 130, tam=5, largura=560,
                 escala=1.3)
    return [page], []


# ─────────────────────────────────────────────────────────────────────────
# ORQUESTRACAO (dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def gerar_executivo_concreto(cfg):
    import FreeCAD as App
    import FreeCADGui as Gui
    import TechDrawGui
    import time

    try:
        App.Units.setSchema(0)            # mm inteiros nas cotas
    except Exception:
        pass
    out = os.path.join(cfg["out"], "pranchas")
    os.makedirs(out, exist_ok=True)

    doc = App.openDocument(cfg["fcstd"])
    objs = [o for o in doc.Objects if o.TypeId == "Part::Feature"
            and hasattr(o, "Shape") and not o.Shape.isNull()]
    # remove pranchas antigas (idempotente)
    for nome in [o.Name for o in doc.Objects
                 if o.TypeId.startswith("TechDraw::") or o.TypeId == "Spreadsheet::Sheet"]:
        if doc.getObject(nome) is not None:
            try:
                doc.removeObject(nome)
            except Exception:
                pass

    paginas, cotadores = [], []
    for fn, args in ((_pr_formas, (objs,)), (_pr_portico, (objs,)),
                     (_pr_quadros, ())):
        try:
            pgs, cts = fn(doc, cfg, *args)
            paginas += pgs
            cotadores += cts
        except Exception as ex:
            App.Console.PrintError("Prancha %s: %s\n" % (fn.__name__, ex))

    doc.recompute()
    for p in paginas:                     # abre a MDI p/ assentar a geometria
        try:
            p.ViewObject.doubleClicked()
        except Exception:
            pass
    Gui.updateGui()
    time.sleep(1.0)
    Gui.updateGui()
    for c in cotadores:                   # ancora as cotas (vertices ja estaveis)
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
    fcstd_out = os.path.join(out, "executivo_concreto.FCStd")
    try:
        doc.saveAs(fcstd_out)
    except Exception:
        pass
    return {"ok": True, "pranchas": [p.Name for p in paginas],
            "arquivos": arquivos, "fcstd": fcstd_out}


def _entry_concreto(cfg):
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
        res = gerar_executivo_concreto(cfg)
    except Exception:
        import traceback
        res = {"erro": traceback.format_exc()}
    try:
        with open(status, "w", encoding="utf-8") as f:
            json.dump(res, f, default=str)
    except Exception:
        pass
    # fecha limpo (mesma sequencia do techdraw_exec: fecha docs via API sem prompt,
    # depois encerra o app - senao o freecad.exe vira zumbi segurando recursos)
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
    """Monta o cfg (dados JA computados, mm) a partir do resultado de
    galpao_concreto.rodar(r) + o FCStd do build_concreto. Nada e recalculado
    dentro do FreeCAD; todos os quadros/notas vem daqui (nao inventa valores)."""
    spec = spec or {}
    sp = r["spec"]
    vao = sp["vao"] * 1000.0
    comp = sp["comprimento"] * 1000.0
    H = sp["H"] * 1000.0
    s = sp["s"] * 1000.0
    n = sp["n_porticos"]
    fckM = sp["fck_MPa"]
    hx = r["pilar"]["hx"]; hy = r["pilar"]["hy"]
    vb = r["viga"]["b"]; vh = r["viga"]["h"]
    sec_pil_lbl = r["gates"]["pilar"]["secao"]
    sec_vig_lbl = r["gates"]["viga_cobertura"]["secao"]
    protendida = r.get("tipo_viga") == "protendida" and r.get("viga_prot")
    if protendida:
        vp = r["viga_prot"]
        viga_arm_lbl = " (%d cordoalhas Ø%s)" % (vp["n_cordoalhas"], vp["phi_cord"])
        quadro_vigas_hdr = ["MARCA", "SECAO (cm)", "PROTENSAO"]
        arm_vig = "%d cord. Ø%s (CP)" % (vp["n_cordoalhas"], vp["phi_cord"])
    else:
        viga_arm_lbl = " (As %.2f cm2)" % r["viga"].get("As_inf_cm2", 0.0)
        quadro_vigas_hdr = ["MARCA", "SECAO (cm)", "As inf (cm2)"]
        arm_vig = "%.2f" % r["viga"].get("As_inf_cm2", 0.0)

    # quadros por MARCA (todas as pecas do galpao repetem a mesma marca-tipo)
    quadro_pilares = [["P (tipo)", sec_pil_lbl, "%.2f" % r["pilar"]["As_cm2"],
                       "%.2f" % r["pilar"]["taxa_pct"]]]
    quadro_vigas = [["VC (tipo)", sec_vig_lbl, arm_vig]]

    tem_estaca = r.get("tipo_fundacao") == "estaca" and r.get("estaca")
    if tem_estaca:
        cap = r["estaca"]["capacidade"]      # D/L da estaca (m); tipo
        gr = r["estaca"]["grupo"]            # n de estacas por pilar
        quadro_fund_titulo = "QUADRO DE ESTACAS"
        quadro_fund_hdr = ["ELEM", "D (cm)", "L (m)", "N/pilar"]
        quadro_fund = [["Estaca", "%.0f" % (cap["D"] * 100), "%.1f" % cap["L"],
                        "%s" % gr.get("n", "")]]
        fund_nota = ("Estacas %s conforme memoria (Aoki-Velloso/Decourt/Teixeira)."
                     % cap.get("tipo_estaca", ""))
    else:
        B, L, hf = r["sapata"]["aprovado"][:3]
        quadro_fund_titulo = "QUADRO DE SAPATAS"
        quadro_fund_hdr = ["MARCA", "B (cm)", "L (cm)", "h (cm)"]
        quadro_fund = [["S (tipo)", "%.0f" % (B * 100), "%.0f" % (L * 100),
                        "%.0f" % (hf * 100)]]
        fund_nota = "Sapatas de concreto armado sob calice (NBR 6122/6118)."

    cob_mm = spec.get("cobrimento_mm", 30.0)
    fyk = spec.get("fyk", 500e3)
    aco = "CA-50" if abs(fyk - 500e3) < 1e-6 else ("CA-60" if abs(fyk - 600e3) < 1e-6
                                                   else "fyk=%.0f MPa" % (fyk / 1000.0))
    # quantitativo de concreto (do build 3D, se veio no spec; senao omite)
    tk = ((spec.get("estrutura", {}) or {}).get("takeoff_concreto")
          if isinstance(spec, dict) else None)
    notas = [
        "NOTAS TECNICAS E ESPECIFICACOES",
        "1. Concreto: fck = %.0f MPa (concreto armado, gamma_c = 1,4)." % fckM,
        "2. Aco das armaduras: %s (fyk conforme quadro; gamma_s = 1,15)." % aco,
        "3. Cobrimento nominal das armaduras: %.0f mm (NBR 6118 Tab. 7.2)." % cob_mm,
        "4. Sistema pre-moldado: pilares engastados na base por CALICE de fundacao",
        "   (NBR 9062); viga de cobertura biapoiada sobre o topo dos pilares.",
        "5. %s" % fund_nota,
        "6. Normas: NBR 6118, NBR 6122, NBR 6123, NBR 9062, NBR 15200.",
        "7. Verificar situacoes transitorias de icamento/transporte (NBR 9062 5.3.2).",
    ]
    if tk:
        notas.append("8. Volume de concreto (modelo 3D): %s m3 (~%s kg)."
                     % (tk.get("vol_concreto_m3"), tk.get("massa_concreto_kg")))
    notas.append("Cotas em metros salvo indicacao. Confrontar com a memoria de calculo.")

    return {
        "fcstd": str(fcstd_path).replace("\\", "/"),
        "out": str(out_dir).replace("\\", "/"),
        "slug": spec.get("slug", "galpao_concreto"),
        "descricao": spec.get("descricao", "Galpao de concreto pre-moldado - Projeto Estrutural"),
        "autor": spec.get("autor", "galpao_fw"),
        "geo": {"vao": vao, "comprimento": comp, "H": H, "s": s, "n": n},
        "fck_MPa": int(fckM), "aco": aco, "cobrimento_mm": cob_mm,
        "sec_pilar_lbl": sec_pil_lbl, "sec_viga_lbl": sec_vig_lbl,
        "viga_arm_lbl": viga_arm_lbl,
        "quadro_pilares": quadro_pilares,
        "quadro_vigas_hdr": quadro_vigas_hdr, "quadro_vigas": quadro_vigas,
        "quadro_fund_titulo": quadro_fund_titulo, "quadro_fund_hdr": quadro_fund_hdr,
        "quadro_fund": quadro_fund,
        "notas": notas,
        # o carimbo do techdraw_exec le 'materiais' (pode ser None -> omite)
        "materiais": {"aco_MPa": None, "fck_MPa": int(fckM),
                      "cobrimento_cm": cob_mm / 10.0},
    }


def codigo_fonte():
    """Fonte deste modulo, para injetar no freecad.exe."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "techdraw_concreto.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _para_nativo(o):
    """Escalares/arrays numpy -> nativos (o repr de np.float64 quebra no freecad).
    Reusa a mesma logica do techdraw_exec."""
    import techdraw_exec as TE
    return TE._para_nativo(o)


def script_bootstrap(cfg):
    """Script que o freecad.exe roda: prepende o dir do galpao_fw no sys.path (p/
    o `from techdraw_exec import ...` deste modulo resolver o IRMAO num processo
    limpo), injeta cfg + a fonte, e dispara _entry_concreto via QTimer."""
    galpao_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
    return ("# -*- coding: utf-8 -*-\n"
            "import sys\n"
            "if %r not in sys.path: sys.path.insert(0, %r)\n" % (galpao_dir, galpao_dir)
            + "_CFG_ = %r\n" % (_para_nativo(cfg),)
            + codigo_fonte()
            + "\nfrom PySide import QtCore\n"
            "QtCore.QTimer.singleShot(1500, lambda: _entry_concreto(_CFG_))\n")
