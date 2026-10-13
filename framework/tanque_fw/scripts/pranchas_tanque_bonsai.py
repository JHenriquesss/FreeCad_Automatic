"""Pranchas do tanque-base pelo Blender + Bonsai, sem janela.

Mesmo fluxo do galpao (docs/fase3-bonsai/scripts/pranchas_bonsai.py), de onde
vem o que ja' foi medido la': enquadramento pelo envelope, cota e texto pelo
nucleo do Bonsai, simbolo de solda, reposicionamento das vistas na folha,
carimbo em portugues e as duas passadas (as anotacoes de referencia so' entram
no SVG depois de recarregar o IFC). Aqui mudam as vistas - conjunto a 1:20 e
detalhes a 1:5 - e as cotas, que saem do envelope das pecas do proprio modelo.

Uso (o IFC e' COPIADO antes: o Bonsai grava nele):
    blender -b --python pranchas_tanque_bonsai.py -- <caminho.ifc> [titulo=..]
                                            [revisao=..] [lista=<tabela.svg>]
Imprime `RELATORIO_JSON {...}`, no mesmo formato do script do galpao.
"""
import json
import math
import os
import sys
import time
import traceback

import bpy

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(
    AQUI, "..", "..", "..", "docs", "fase3-bonsai", "scripts")))
import pranchas_bonsai as PB   # noqa: E402

ESCALA_GERAL = 20       # 1:25 nao existe na lista de escalas do Bonsai
ESCALA_DETALHE = 5
MARGEM_M = 1.3          # folga para as cotas em volta do modelo
FOLGA_ESCADA_M = 0.5
ORDEM = ("PLANTA", "CORTE-TRANSV", "ELEVACAO-LATERAL", "CORTE-LONGIT", "VISTA-TESTA",
         "DET-CANTO", "DET-TRAVESSA", "DET-BAIA")
ESCALA_TESTA = 10
# pecas que saem da projecao da gaiola e nao entram no enquadramento nem nas cotas gerais
FORA_DO_ENVELOPE = ("OLHAL", "CALCO")
# SVG com notas gerais, tabela de soldas e componentes (escrito por pranchas_tanque.py)
VAR_NOTAS = "TANQUE_NOTAS_SVG"
PREFIXO_FOLHA = "TQ"
# o corte transversal passa no meio de um vao: com 0,33 m alcanca a travessa seguinte
PROF_CORTE_TRANSV = 0.33
# pernas dos filetes do calculo (spec["perna_solda"] e spec["perna_solda_travessa"]), mm
PERNA_QUADRO, PERNA_TRAVESSA = "5", "4"


def _pontos(tool, el):
    import mathutils
    o = tool.Ifc.get_object(el)
    if o is None or o.type != "MESH":
        return []
    return [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]


def _mn_mx(pts):
    return ([min(p[i] for p in pts) for i in range(3)],
            [max(p[i] for p in pts) for i in range(3)])


def _envelope_da_base(tool):
    """Envelope da gaiola: sem conexoes (o respiro sobe alem do conteiner) nem apoios."""
    pts = []
    for el in tool.Ifc.get().by_type("IfcElement"):
        if (el.is_a() not in ("IfcBuildingElementProxy", "IfcFooting", "IfcOpeningElement")
                and el.Name not in FORA_DO_ENVELOPE):
            pts += _pontos(tool, el)
    return _mn_mx(pts)


def _caixa(tool, marca):
    """Envelope (mn, mx) de todas as pecas com esse nome."""
    pts = []
    for el in tool.Ifc.get().by_type("IfcElement"):
        if el.Name == marca:
            pts += _pontos(tool, el)
    return _mn_mx(pts)


def _peca(tool, marca, ponto):
    """A peca de nome `marca` mais proxima do ponto (x, y, z)."""
    melhor = None
    for el in tool.Ifc.get().by_type("IfcElement"):
        if el.Name != marca:
            continue
        pts = _pontos(tool, el)
        if not pts:
            continue
        c = [sum(p[i] for p in pts) / len(pts) for i in range(3)]
        d = math.dist(c, ponto)
        if melhor is None or d < melhor[0]:
            melhor = (d, el)
    return None if melhor is None else melhor[1]


def _perfil(tool, marca):
    """Nome do perfil gravado no IFC para a peca (o texto da prancha sai do modelo)."""
    for el in tool.Ifc.get().by_type("IfcElement"):
        if el.Name == marca and el.Representation:
            item = el.Representation.Representations[0].Items[0]
            return getattr(getattr(item, "SweptArea", None), "ProfileName", None) or marca
    return marca


def vistas_do_tanque(tool):
    """(nome, tipo, posicao, rotacao, largura, altura, profundidade, cotas, escala, textos).

    Texto = (ponto, literal, marca da peca a que se liga, simbolo ou None)."""
    mn, mx = _envelope_da_base(tool)
    c_y = (mn[1] + mx[1]) / 2
    fmn, fmx = _caixa(tool, "CH-FUNDO")       # o fundo tem a projecao do tanque
    tmn, tmx = _caixa(tool, "CH-TAMPA")
    mmn, mmx = _caixa(tool, "M")              # montantes: eixos dos apoios
    lmn, lmx = _mn_mx(_pontos(tool, _peca(tool, "L-INF", (mn[0], mn[1], mn[2]))))
    smn, smx = _caixa(tool, "L-SUP")
    timn, timx = _caixa(tool, "TI")
    tsmn, tsmx = _caixa(tool, "TS")
    # testeiras traseiras (lado da baia tecnica)
    temn, temx = _mn_mx(_pontos(tool, _peca(tool, "TE-INF", (mx[0], c_y, mn[2]))))
    tspn, tspx = _mn_mx(_pontos(tool, _peca(tool, "TE-SUP", (mx[0], c_y, mx[2]))))
    sumn, sumx = _caixa(tool, "SUCCAO")
    ctmn, ctmx = _mn_mx(_pontos(tool, _peca(tool, "CT", (mn[0], mn[1], mx[2]))))
    c = [(a + b) / 2 for a, b in zip(mn, mx)]
    d = [b - a for a, b in zip(mn, mx)]
    r = math.radians
    x_meio_apoio = (mmn[0] + mmx[0]) / 2
    x_apoio = mmn[0] + 0.075

    planta = [((mn[0], mn[1] - 0.75, 0), (mx[0], mn[1] - 0.75, 0)),
              ((fmn[0], mn[1] - 0.40, 0), (fmx[0], mn[1] - 0.40, 0)),
              # cotas de largura do lado da baia: na frente fica a escada
              ((mx[0] + 0.75, mn[1], 0), (mx[0] + 0.75, mx[1], 0)),
              ((mx[0] + 0.40, fmn[1], 0), (mx[0] + 0.40, fmx[1], 0)),
              ((fmx[0], mx[1] + 0.40, 0), (mx[0], mx[1] + 0.40, 0))]      # baia + testeira
    # bocais da tampa: posicao ao longo do comprimento, a partir da frente da base
    xs_bocais = sorted(set(round((a[0] + b[0]) / 2, 4) for a, b in (
        _mn_mx(_pontos(tool, el)) for el in tool.Ifc.get().by_type("IfcElement")
        if el.Name in ("ENTRADA", "RESPIRO"))))
    planta += [((a, mx[1] + 0.75, 0), (b, mx[1] + 0.75, 0))
               for a, b in zip([mn[0]] + xs_bocais, xs_bocais)]
    elev = [((x_apoio, 0, mn[2] - 0.55), (x_meio_apoio, 0, mn[2] - 0.55)),
            ((x_meio_apoio, 0, mn[2] - 0.55), (mx[0] - 0.075, 0, mn[2] - 0.55)),
            ((mx[0] + 0.45, 0, mn[2]), (mx[0] + 0.45, 0, mx[2]))]
    corte_l = [((fmn[0], 0, mn[2] - 0.40), (fmx[0], 0, mn[2] - 0.40)),
               ((mn[0] - 0.40, 0, fmn[2]), (mn[0] - 0.40, 0, tmx[2])),
               ((mx[0] + 0.45, 0, mn[2]), (mx[0] + 0.45, 0, mx[2]))]
    corte_t = [((0, mn[1], mn[2] - 0.60), (0, mx[1], mn[2] - 0.60)),
               ((0, fmn[1], mn[2] - 0.30), (0, fmx[1], mn[2] - 0.30)),
               ((0, mx[1] + 0.45, fmn[2]), (0, mx[1] + 0.45, tmx[2])),
               ((0, mn[1] - 0.45, mn[2]), (0, mn[1] - 0.45, mx[2]))]
    # a escada sai FOLGA_ESCADA_M alem da margem, na frente: o quadro cresce so' desse lado
    lx = d[0] + 2 * MARGEM_M + FOLGA_ESCADA_M
    ly, lz = d[1] + 2 * MARGEM_M, d[2] + 2 * MARGEM_M
    cxv = c[0] - FOLGA_ESCADA_M / 2
    # o corte transversal passa no meio do vao entre a 2a e a 3a travessa
    x_corte = fmn[0] + 1.5 * (fmx[0] - fmn[0]) / 11.0
    # o corte longitudinal fica fora do eixo: no eixo, a linha do corte passava por
    # cima do texto das cotas de largura da planta
    y_corte = c[1] + 0.40
    gerais = [
        ("PLANTA", "PLAN_VIEW", (cxv, c[1], mx[2] + 0.30), (0, 0, 0),
         lx, ly, d[2] + 0.60, planta),
        ("ELEVACAO-LATERAL", "ELEVATION_VIEW", (cxv, mn[1] - 1.0, c[2]), (r(90), 0, 0),
         lx, lz, 1.0 + 0.12, elev),
        ("CORTE-LONGIT", "SECTION_VIEW", (cxv, y_corte, c[2]), (r(90), 0, 0),
         lx, lz, mx[1] - y_corte + 0.05, corte_l),
        ("CORTE-TRANSV", "SECTION_VIEW", (x_corte, c[1], c[2]), (r(90), 0, r(-90)),
         ly, lz, PROF_CORTE_TRANSV, corte_t),
    ]
    vistas = [v + (ESCALA_GERAL, []) for v in gerais]

    # --- testa do tanque vista da baia tecnica: posicao de cada bocal ---
    def centro(marca):
        a, b = _caixa(tool, marca)
        return [(a[i] + b[i]) / 2 for i in range(3)]

    bimn, bimx = _caixa(tool, "BI")
    xt_ = fmx[0]
    c_suc, c_lav, c_sen, c_hh = (centro(k) for k in ("SUCCAO", "LAVAGEM", "SENSOR-NIVEL",
                                                    "CHAVE-HH"))
    ys = sorted([mn[1], c_suc[1], c_sen[1], bimn[1], bimx[1], c_lav[1], mx[1]])
    testa = ([((0, a, mn[2] - 0.30), (0, b, mn[2] - 0.30)) for a, b in zip(ys, ys[1:])]
             + [((0, mx[1] + 0.25, mn[2]), (0, mx[1] + 0.25, c_suc[2])),
                ((0, mx[1] + 0.45, mn[2]), (0, mx[1] + 0.45, c_lav[2])),
                ((0, mn[1] - 0.25, mn[2]), (0, mn[1] - 0.25, c_hh[2])),
                ((0, mn[1] - 0.45, mn[2]), (0, mn[1] - 0.45, bimn[2])),
                ((0, mn[1] - 0.65, mn[2]), (0, mn[1] - 0.65, bimx[2]))])
    vistas.append((
        "VISTA-TESTA", "SECTION_VIEW", (xt_ + 0.36, c[1], c[2]), (r(90), 0, r(90)),
        d[1] + 2.0, d[2] + 1.5, 0.40, testa, ESCALA_TESTA,
        [((0, c_suc[1] + 0.10, c_suc[2] + 0.10), "SUCCAO %s" % _perfil(tool, "SUCCAO"),
          "SUCCAO", None),
         ((0, c_lav[1] + 0.05, c_lav[2] + 0.03), "LAVAGEM %s" % _perfil(tool, "LAVAGEM"),
          "LAVAGEM", None),
         ((0, bimn[1] + 0.06, (bimn[2] + bimx[2]) / 2), "BOCA DE INSPECAO", "BI", None),
         ((0, c_hh[1] - 0.50, c_hh[2] + 0.03), "CHAVE DE NIVEL ALTO-ALTO", "CHAVE-HH", None),
         ((0, c_sen[1] + 0.06, c_sen[2] - 0.02), "TRANSMISSOR DE NIVEL", "SENSOR-NIVEL", None)]))

    tubo_q, tubo_ti, tubo_ts = _perfil(tool, "L-INF"), _perfil(tool, "TI"), _perfil(tool, "TS")
    solda = PB.SIMBOLO_SOLDA
    # --- canto: montante, chapa de topo e cone, visto de fora ---
    x1 = mn[0]
    det_canto = (
        "DET-CANTO", "ELEVATION_VIEW", (x1 + 0.36, mn[1] - 1.0, 0.33), (r(90), 0, 0),
        1.10, 1.30, 1.0 + 0.12,
        [((x1 - 0.07, 0, mn[2]), (x1 - 0.07, 0, mx[2])),
         ((x1 - 0.14, 0, ctmn[2]), (x1 - 0.14, 0, ctmx[2])),
         ((ctmn[0], 0, mx[2] + 0.16), (ctmx[0], 0, mx[2] + 0.16)),
         ((x1 + 0.55, 0, lmx[2]), (x1 + 0.55, 0, smn[2]))],
        ESCALA_DETALHE,
        [((x1 + 0.26, 0, mx[2] + 0.02), "CHAPA DE TOPO %s + CONE ISO 1161" % _perfil(tool, "CT"),
          "CT", None),
         ((x1 + 0.26, 0, 0.60), "LONGARINA SUP. %s" % tubo_q, "L-SUP", None),
         ((x1 + 0.26, 0, 0.075), "LONGARINA INF. %s" % tubo_q, "L-INF", None),
         ((x1 + 0.17, 0, 0.36), "MONTANTE %s" % tubo_q, "M", None),
         ((x1 + 0.30, 0, 0.47), PERNA_QUADRO, "L-SUP", solda),
         ((x1 + 0.26, 0, -0.14), "APOIO 350 x 350 MIN. (REFERENCIA)", "APOIO", None)])
    # --- apoio do tanque: corte transversal junto a uma longarina ---
    y1 = mn[1]
    det_trav = (
        "DET-TRAVESSA", "SECTION_VIEW", (x_corte, y1 + 0.30, 0.33), (r(90), 0, r(-90)),
        1.20, 1.30, PROF_CORTE_TRANSV,
        [((0, y1, mn[2] - 0.12), (0, lmx[1], mn[2] - 0.12)),
         ((0, lmx[1], mn[2] - 0.12), (0, fmn[1], mn[2] - 0.12)),
         ((0, y1 - 0.14, mn[2]), (0, y1 - 0.14, timx[2])),
         ((0, y1 - 0.14, fmn[2]), (0, y1 - 0.14, tmx[2])),
         ((0, y1 - 0.14, tsmn[2]), (0, y1 - 0.14, tsmx[2])),
         ((0, y1 - 0.23, mn[2]), (0, y1 - 0.23, mx[2]))],
        ESCALA_DETALHE,
        [((0, y1 + 0.85, 0.72), "TRAVESSA SUP. %s (DEITADA)" % tubo_ts, "TS", None),
         ((0, y1 + 0.85, 0.555), "TAMPA %s" % _perfil(tool, "CH-TAMPA"), "CH-TAMPA", None),
         ((0, y1 + 0.85, 0.36), "LATERAL %s - SOLDA CONTINUA ESTANQUE"
           % _perfil(tool, "CH-LATERAL"), "CH-LATERAL", None),
         ((0, y1 + 0.85, 0.135), "FUNDO %s" % _perfil(tool, "CH-FUNDO"), "CH-FUNDO", None),
         ((0, y1 + 0.85, -0.07), "TRAVESSA INF. %s (EM PE)" % tubo_ti, "TI", None),
         ((0, y1 + 0.60, 0.20), PERNA_TRAVESSA, "TI", solda)])
    # --- baia tecnica: corte longitudinal pelo eixo da succao ---
    y_s = (sumn[1] + sumx[1]) / 2
    xt = fmx[0]
    det_baia = (
        "DET-BAIA", "SECTION_VIEW", (xt + 0.03, y_s, 0.36), (r(90), 0, 0),
        1.45, 1.40, mx[1] - y_s + 0.05,
        [((xt, 0, mn[2] - 0.12), (temn[0], 0, mn[2] - 0.12)),
         ((mx[0] + 0.14, 0, temx[2]), (mx[0] + 0.14, 0, tspn[2])),
         ((xt - 0.50, 0, fmx[2]), (xt - 0.50, 0, (sumn[2] + sumx[2]) / 2))],
        ESCALA_DETALHE,
        [((xt - 0.66, 0, 0.27), "SUCCAO %s COM PESCADOR" % _perfil(tool, "SUCCAO"),
          "SUCCAO", None),
         ((xt - 0.66, 0, 0.50), "LAVAGEM %s" % _perfil(tool, "LAVAGEM"), "LAVAGEM", None),
         ((xt - 0.66, 0, 0.38), "BOCA DE INSPECAO - FLANGE CEGA %s" % _perfil(tool, "BI"),
          "BI", None),
         ((xt - 0.66, 0, 0.80), "RESPIRO %s PELA TAMPA (SOBE POR SHAFT)"
           % _perfil(tool, "RESPIRO"), "RESPIRO", None),
         ((xt - 0.66, 0, -0.10), "POCO DO PESCADOR %s (PROF. 80)" % _perfil(tool, "POCO"),
          "POCO", None),
         ((xt + 0.02, 0, -0.26), "BAIA TECNICA - ACESSO PELA TRASEIRA", "TE-INF", None)])
    return vistas + [det_canto, det_trav, det_baia]


def main(ifc_path, titulo="TANQUE-BASE", revisao="02", lista=None):
    rel = {"passos": [], "avisos": [], "cotas": {}, "papel_mm": {},
           "primeira_passada_incompleta": []}

    def passo(nome, fn):
        t = time.time()
        try:
            r = fn()
            rel["passos"].append([nome, "ok", round(time.time() - t, 1)])
            return r
        except Exception:
            rel["passos"].append([nome, "ERRO", round(time.time() - t, 1)])
            rel["avisos"].append("%s: %s" % (nome, traceback.format_exc()[-600:]))

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.bim.load_project(filepath=ifc_path, use_relative_path=False,
                             should_start_fresh_session=False)
    import bonsai.core.drawing as core
    import bonsai.tool as tool
    import ifcopenshell.api.pset
    ifc = tool.Ifc.get()
    mn, mx = _envelope_da_base(tool)
    rel["envelope_m"] = [[round(a, 3), round(b, 3)] for a, b in zip(mn, mx)]
    props = bpy.context.scene.DocProperties
    cena = bpy.context.scene
    feitos = {a.id() for a in ifc.by_type("IfcAnnotation") if a.ObjectType == "DRAWING"}

    for nome, tipo, pos, rot, larg, alt, prof, cotas, escala, textos in vistas_do_tanque(tool):

        def _vista():
            props.target_view = tipo
            bpy.ops.bim.add_drawing()
            des = [a for a in ifc.by_type("IfcAnnotation")
                   if a.ObjectType == "DRAWING" and a.id() not in feitos][0]
            feitos.add(des.id())
            core.update_drawing_name(tool.Ifc, tool.Drawing, drawing=des, name=nome)
            if escala != ESCALA_GERAL:
                # detalhe nao aparece como marca nas vistas gerais
                ifcopenshell.api.pset.edit_pset(
                    ifc, pset=tool.Pset.get_element_pset(des, "EPset_Drawing"),
                    properties={"GlobalReferencing": False})
            bpy.ops.bim.activate_drawing(drawing=des.id(), should_view_from_camera=False)
            cam = cena.camera
            cam.location, cam.rotation_euler = pos, rot
            cp = cam.data.BIMCameraProperties
            cp.diagram_scale = "1:%d|1/%d" % (escala, escala)
            cp.width, cp.height = larg, alt
            cam.data.clip_start, cam.data.clip_end = 0.0, prof
            bpy.context.view_layer.update()
            for o in bpy.context.selected_objects:
                o.select_set(False)
            cam.select_set(True)
            bpy.context.view_layer.objects.active = cam
            bpy.ops.bim.edit_object_placement()
            cena.render.resolution_x, cena.render.resolution_y = cp.raster_x, cp.raster_y
            for p1, p2 in cotas:
                PB._cota(tool, des, p1, p2)
            for ponto, literal, marca, simbolo in textos:
                produto = _peca(tool, marca, ponto)
                if produto is None:
                    rel["avisos"].append("%s: sem peca %s para o texto %r"
                                         % (nome, marca, literal))
                    continue
                PB._texto(tool, des, ponto, literal, produto, simbolo)
            rel["cotas"][nome] = len(cotas)
            rel["papel_mm"][nome] = (round(larg * 1000.0 / escala, 1),
                                     round(alt * 1000.0 / escala, 1))
            try:
                bpy.ops.bim.create_drawing(print_all=False, open_viewer=False, sync=True)
            except Exception as exc:
                motivo = [ln for ln in str(exc).splitlines() if "Error" in ln] or [str(exc)]
                rel["primeira_passada_incompleta"].append("%s: %s" % (nome, motivo[-1][:120]))

        passo(nome, _vista)

    passo("salvar IFC", lambda: bpy.ops.bim.save_project(filepath=ifc_path,
                                                         should_save_as=False))

    def _segunda_passada():
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o)
        bpy.ops.bim.load_project(filepath=ifc_path, use_relative_path=False,
                                 should_start_fresh_session=False)
        cena2 = bpy.context.scene
        PB.garantir_simbolo_de_solda(
            os.path.join(os.path.dirname(ifc_path), "drawings", "assets"))
        n = 0
        for des in tool.Ifc.get().by_type("IfcAnnotation"):
            if des.ObjectType != "DRAWING" or des.Name not in rel["cotas"]:
                continue
            bpy.ops.bim.activate_drawing(drawing=des.id(), should_view_from_camera=False)
            cp = cena2.camera.data.BIMCameraProperties
            cena2.render.resolution_x, cena2.render.resolution_y = cp.raster_x, cp.raster_y
            bpy.ops.bim.create_drawing(print_all=False, open_viewer=False)
            n += 1
        pasta = os.path.join(os.path.dirname(ifc_path), "drawings")
        rel["pontas_puxadas"] = {
            a[:-4]: PB.puxar_para_dentro(os.path.join(pasta, a))
            for a in sorted(os.listdir(pasta)) if a.lower().endswith(".svg")}
        return n

    rel["segunda_passada"] = passo("segunda passada", _segunda_passada)
    props = bpy.context.scene.DocProperties          # a sessao foi recarregada

    def _folha_nova():
        antes = {sh.ifc_definition_id for sh in props.sheets if sh.is_sheet}
        bpy.ops.bim.add_sheet()
        return antes

    def _indice_da_nova(antes):
        return [i for i, sh in enumerate(props.sheets)
                if sh.is_sheet and sh.ifc_definition_id not in antes][0]

    def _folhas():
        raiz = os.path.dirname(ifc_path)
        tamanhos = [(n,) + tuple(rel["papel_mm"][n]) for n in ORDEM if n in rel["papel_mm"]]
        gerais = [t for t in tamanhos if not t[0].startswith("DET-")]
        dets = [t for t in tamanhos if t[0].startswith("DET-")]
        plano_g = PB.distribuir(gerais)
        plano = plano_g + (PB.distribuir(dets) if dets else [])
        props.titleblock = "A1"
        for k, folha in enumerate(plano, 1):
            antes = _folha_nova()
            if k == 1:
                PB._carimbo_em_portugues(os.path.join(raiz, "layouts", "titleblocks", "A1.svg"))
            bpy.ops.bim.load_sheets()
            bpy.ops.bim.load_drawings()
            for item in props.drawings:
                if not item.is_drawing:
                    item.is_expanded = True
            tool.Drawing.import_drawings()
            idx = _indice_da_nova(antes)
            props.active_sheet_index = idx
            for nome, _x, _y in folha:
                for i, item in enumerate(props.drawings):
                    if item.is_drawing and item.name == nome:
                        props.active_drawing_index = i
                        bpy.ops.bim.add_drawing_to_sheet()
            nova = tool.Ifc.get().by_id(props.sheets[idx].ifc_definition_id)
            if k > len(plano_g):
                nome_folha = "%s - DETALHES" % titulo
            elif len(plano_g) == 1:
                nome_folha = "%s - CONJUNTO" % titulo
            else:
                nome_folha = "%s - CONJUNTO %d" % (titulo, k)
            core.rename_sheet(tool.Ifc, tool.Drawing, sheet=nova,
                              identification="%s-%02d" % (PREFIXO_FOLHA, k), name=nome_folha)
            tool.Ifc.run("document.edit_information", information=nova,
                         attributes={"Revision": revisao})
        extras = [(lista, "LISTA DE MATERIAL", "folha_da_lista")] if lista else []
        notas = os.environ.get(VAR_NOTAS)
        if notas and os.path.isfile(notas):
            import shutil
            destino = os.path.join(raiz, "references", os.path.basename(notas))
            shutil.copyfile(notas, destino)
            extras.append((destino, "NOTAS E SOLDAS", "folha_das_notas"))
        for n_extra, (ref_svg, nome_extra, chave_rel) in enumerate(extras, 1):
            k = len(plano) + n_extra
            antes = _folha_nova()
            bpy.ops.bim.load_sheets()
            idx = _indice_da_nova(antes)
            props.active_sheet_index = idx
            core.add_document(tool.Ifc, tool.Drawing, "REFERENCE",
                              uri=os.path.relpath(ref_svg, raiz).replace("\\", "/"))
            nome_ref = os.path.splitext(os.path.basename(ref_svg))[0]
            props.active_reference_index = [
                i for i, r in enumerate(props.references) if r.name == nome_ref][0]
            bpy.ops.bim.add_reference_to_sheet()
            nova = tool.Ifc.get().by_id(props.sheets[idx].ifc_definition_id)
            core.rename_sheet(tool.Ifc, tool.Drawing, sheet=nova,
                              identification="%s-%02d" % (PREFIXO_FOLHA, k), name=nome_extra)
            tool.Ifc.run("document.edit_information", information=nova,
                         attributes={"Revision": revisao})
            rel[chave_rel] = "%s-%02d" % (PREFIXO_FOLHA, k)
        posicoes = {n: (x, y) for folha in plano for n, x, y in folha}
        rel["reposicionados"] = PB._reposicionar(os.path.join(raiz, "layouts"), posicoes)
        bpy.ops.bim.load_sheets()
        bpy.ops.bim.create_sheets(create_all=True, open_viewer=False)
        rel["folhas"] = [[n for n, _x, _y in folha] for folha in plano]

    passo("folhas A1", _folhas)
    passo("salvar IFC com as folhas", lambda: bpy.ops.bim.save_project(
        filepath=ifc_path, should_save_as=False))
    raiz = os.path.dirname(ifc_path)
    rel["arquivos"] = sorted(
        os.path.relpath(os.path.join(b, x), raiz).replace("\\", "/")
        for b, _d, fs in os.walk(raiz) for x in fs
        if "assets" not in b and "cache" not in b and "titleblocks" not in b)
    if not rel["avisos"]:
        del rel["avisos"]
    print("RELATORIO_JSON " + json.dumps(rel, ensure_ascii=False))


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    opcoes = dict(a.split("=", 1) for a in args[1:] if "=" in a)
    main(args[0], titulo=opcoes.get("titulo", "TANQUE-BASE"),
         revisao=opcoes.get("revisao", "02"), lista=opcoes.get("lista"))
