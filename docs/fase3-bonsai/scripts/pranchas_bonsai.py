"""Fase 3 (plano de 2026-10-08) - pranchas do galpao pelo Blender + Bonsai, sem janela.

Abre o IFC gerado pelo motor (ifc_emit), cria as vistas enquadradas no modelo,
cota pelos eixos lidos dos proprios pilares do IFC, monta a folha com carimbo e
grava tudo ao lado do IFC (drawings/, layouts/, sheets/). Nada e' editado a mao:
alterou o projeto, regenera o IFC e roda de novo.

Uso (o IFC e' COPIADO para uma pasta de trabalho antes: o Bonsai grava nele):
    blender -b --python pranchas_bonsai.py -- <caminho.ifc> [titulo=...] [VISTA ...]

Sem VISTA, gera todas. Imprime uma linha `RELATORIO_JSON {...}` com o tempo de
cada passo, os eixos lidos e os avisos.

Medido no Blender 5.2.1 LTS + Bonsai (extensions.blender.org) em 2026-10-08.
Tres coisas que o Bonsai nao faz sozinho e este script resolve:
  - a camera nasce na origem com quadro de 50 x 50 m: posicao, largura, altura e
    profundidade saem do envelope do modelo;
  - a resolucao da cena so acompanha largura/altura na ATIVACAO do desenho: sem
    reatribuir, as cotas saem deslocadas de (largura - altura) / 2;
  - o nome do arquivo SVG vem do nome do desenho na criacao: renomear pelo
    nucleo (`core.update_drawing_name`) antes de gerar.
"""
import json
import math
import os
import sys
import time
import traceback

import bpy
import mathutils

MARGEM_M = 9.0        # folga em volta do modelo, para as cotas
ESCALA = "1:100|1/100"
MM_POR_M = 10.0       # papel a 1:100
# Folha A1 (mm, y para baixo como no SVG). A area util para acima do carimbo do
# modelo do Bonsai, que ocupa a faixa de baixo da folha (medido no A1.svg).
AREA_UTIL = (30.0, 30.0, 811.0, 505.0)
VAO_MM, TITULO_MM = 12.0, 16.0
# ordem em que as vistas entram nas folhas
ORDEM = ("PLANTA-BAIXA", "CORTE-TRANSVERSAL", "ELEVACAO-FRONTAL", "ELEVACAO-LATERAL",
         "PLANTA-FUNDACAO", "PLANTA-COBERTURA")
# rotulos do carimbo padrao do Bonsai -> portugues
CARIMBO_PT = {"DRAWING NUMBER": "FOLHA", "DRAWING TITLE": "TITULO", "GRID NORTH": "NORTE",
              "COMPANY": "RESP. TECNICO", "REV. NO.": "REV.", "DESCRIPTION": "DESCRICAO",
              "AUTHOR": "AUTOR", "ISSUED": "EMISSAO", "NOTES": "NOTAS", "DATE": "DATA",
              "DO NOT SCALE DRAWINGS": "NAO MEDIR NO DESENHO"}
# titulo curto de cada vista no carimbo (a celula do titulo tem ~80 mm)
TITULO_CURTO = {"PLANTA-BAIXA": "PLANTA", "CORTE-TRANSVERSAL": "CORTE",
                "ELEVACAO-FRONTAL": "ELEV. FRONTAL", "ELEVACAO-LATERAL": "ELEV. LATERAL",
                "PLANTA-FUNDACAO": "FUNDACAO", "PLANTA-COBERTURA": "COBERTURA"}


def distribuir(tamanhos, area=AREA_UTIL, vao=VAO_MM, titulo=TITULO_MM):
    """Reparte as vistas em folhas, em prateleiras (esquerda->direita, de cima
    para baixo), reservando a faixa do titulo sob cada vista. `tamanhos` =
    [(nome, largura_mm, altura_mm)] na ordem de entrada. Devolve
    [[(nome, x, y), ...] por folha]. Vista maior que a area util levanta: nao
    existe folha em que ela caiba nesta escala."""
    x0, y0, x1, y1 = area
    folhas, atual = [], []
    x, y, alt_linha = x0, y0, 0.0
    for nome, larg, alt in tamanhos:
        if larg > x1 - x0 or alt + titulo > y1 - y0:
            raise ValueError("%s (%.0f x %.0f mm) nao cabe na area util da folha"
                             % (nome, larg, alt))
        if x + larg > x1:                              # proxima prateleira
            x, y, alt_linha = x0, y + alt_linha + titulo + vao, 0.0
        if y + alt + titulo > y1:                      # proxima folha
            folhas.append(atual)
            atual, x, y, alt_linha = [], x0, y0, 0.0
        atual.append((nome, x, y))
        x += larg + vao
        alt_linha = max(alt_linha, alt)
    if atual:
        folhas.append(atual)
    return folhas


def _reposicionar(pasta_layouts, posicoes):
    """Grava no arquivo de disposicao de cada folha a posicao calculada (o
    Bonsai empilha os desenhos sem conferir se cabem)."""
    import re
    mexidos = 0
    for arq in os.listdir(pasta_layouts):
        if not arq.lower().endswith(".svg"):
            continue
        caminho = os.path.join(pasta_layouts, arq)
        txt = open(caminho, encoding="utf-8").read()

        def _grupo(m):
            nonlocal mexidos
            g = m.group(0)
            ref = re.search(r'data-type="foreground" xlink:href="([^"]+)"', g)
            nome = os.path.splitext(os.path.basename(ref.group(1).replace("\\", "/")))[0] if ref else None
            if nome not in posicoes:
                return g
            x, y = posicoes[nome]
            alt = float(re.search(r'data-type="foreground"[^>]*height="([^"]+)"', g).group(1))
            g = re.sub(r'(data-type="foreground"[^>]*? x=")[^"]+(" y=")[^"]+', r"\g<1>%s\g<2>%s" % (x, y), g)
            g = re.sub(r'(data-type="view-title"[^>]*? x=")[^"]+(" y=")[^"]+',
                       r"\g<1>%s\g<2>%s" % (x, y + alt + 4.0), g)
            mexidos += 1
            return g

        novo = re.sub(r'<g data-type="drawing".*?</g>', _grupo, txt, flags=re.S)
        if novo != txt:
            open(caminho, "w", encoding="utf-8").write(novo)
    return mexidos


def _carimbo_em_portugues(caminho):
    txt = open(caminho, encoding="utf-8").read()
    for en, pt in CARIMBO_PT.items():
        txt = txt.replace(">%s<" % en, ">%s<" % pt)
    open(caminho, "w", encoding="utf-8").write(txt)


def _envelope(tool):
    """Envelope dos ELEMENTOS do modelo (a grade de eixos passa dos pilares de
    proposito e nao entra na conta do enquadramento)."""
    pts = []
    for el in tool.Ifc.get().by_type("IfcElement"):
        o = tool.Ifc.get_object(el)
        if o is not None and o.type == "MESH":
            pts += [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    mn = [min(p[i] for p in pts) for i in range(3)]
    mx = [max(p[i] for p in pts) for i in range(3)]
    return mn, mx


def _eixos(ifc):
    """Eixos X e Y e altura dos pilares, lidos do IFC (metros)."""
    import ifcopenshell.util.placement as up
    import ifcopenshell.util.unit as uu
    esc = uu.calculate_unit_scale(ifc)
    cols = ifc.by_type("IfcColumn")
    mats = [up.get_local_placement(e.ObjectPlacement) for e in cols]
    xs = sorted({round(m[0, 3] * esc, 3) for m in mats})
    ys = sorted({round(m[1, 3] * esc, 3) for m in mats})
    alt = max(e.Representation.Representations[0].Items[0].Depth * esc for e in cols)
    return xs, ys, alt


def _cumeeira(ifc):
    """Cota (m) do ponto mais alto do EIXO das vigas do portico (marca V<n>):
    a ponta da extrusao de cada viga, lida da posicao e do comprimento no IFC.
    None se o modelo nao tiver viga de portico."""
    import re

    import ifcopenshell.util.placement as up
    import ifcopenshell.util.unit as uu
    import numpy as np
    esc = uu.calculate_unit_scale(ifc)
    topo = None
    for v in ifc.by_type("IfcBeam"):
        if not re.fullmatch(r"V\d+", v.Name or ""):
            continue
        item = v.Representation.Representations[0].Items[0]
        if not item.is_a("IfcExtrudedAreaSolid"):
            continue
        m = up.get_local_placement(v.ObjectPlacement)
        for comp in (0.0, float(item.Depth)):
            z = float((m @ np.array([0.0, 0.0, comp, 1.0]))[2]) * esc
            topo = z if topo is None else max(topo, z)
    return topo


def _cota(tool, desenho, p1, p2):
    """Cota linear entre dois pontos do MUNDO (m), no plano do desenho."""
    import bonsai.bim.module.drawing.annotation as ann
    tipo = "DIMENSION"
    vista = tool.Drawing.get_drawing_target_view(desenho)
    ctx = (tool.Drawing.get_annotation_context(vista, tipo)
           or tool.Drawing.create_annotation_context(vista, tipo))
    obj = ann.Annotator.get_annotation_obj(
        desenho, tipo, tool.Drawing.get_annotation_data_type(tipo))
    cam = tool.Ifc.get_object(desenho)
    inv = cam.matrix_world.inverted()
    z_plano = (inv @ obj.matrix_world.translation).z
    l1, l2 = inv @ mathutils.Vector(p1), inv @ mathutils.Vector(p2)
    # texto sempre legivel: da esquerda para a direita, de baixo para cima
    if (round(l1.x, 6), round(l1.y, 6)) > (round(l2.x, 6), round(l2.y, 6)):
        l1, l2 = l2, l1
    l1.z = l2.z = z_plano
    ann.Annotator.add_line_to_annotation(obj, cam.matrix_world @ l1, cam.matrix_world @ l2)
    el = tool.Drawing.run_root_assign_class(
        obj=obj, ifc_class="IfcAnnotation", predefined_type=tipo,
        should_add_representation=True, context=ctx,
        ifc_representation_class=tool.Drawing.get_ifc_representation_class(tipo))
    tool.Ifc.run("group.assign_group",
                 group=tool.Drawing.get_drawing_group(desenho), products=[el])
    tool.Collector.assign(obj, should_clean_users_collection=True)
    return el


def vistas_do_galpao(mn, mx, xs, ys, alt_col, cumeeira=None):
    """(nome, tipo, posicao, rotacao, largura, altura, profundidade, cotas, filtro)."""
    c = [(a + b) / 2 for a, b in zip(mn, mx)]
    d = [b - a for a, b in zip(mn, mx)]
    r = math.radians
    x0, x1, y0, y1 = xs[0], xs[-1], ys[0], ys[-1]
    topo = mx[2]
    x_corte = (xs[1] + xs[2]) / 2 if len(xs) > 2 else c[0]
    # as bolhas dos eixos da grade ficam a 2,5 m da ultima linha de pilares e
    # tem ~1,1 m de diametro a 1:100: as cotas passam por fora delas
    planta = ([((a, y0 - 4.2, 0), (b, y0 - 4.2, 0)) for a, b in zip(xs, xs[1:])]
              + [((x0, y0 - 5.4, 0), (x1, y0 - 5.4, 0))]
              + [((x0 - 4.3, a, 0), (x0 - 4.3, b, 0)) for a, b in zip(ys, ys[1:])])
    alto = cumeeira if cumeeira is not None else topo
    corte = [((0, y0, -3.2), (0, y1, -3.2)),
             ((0, y0 - 2.5, 0.0), (0, y0 - 2.5, alt_col)),
             ((0, y1 + 2.5, 0.0), (0, y1 + 2.5, alto))]
    larg_x, larg_y, alt = d[0] + MARGEM_M, d[1] + MARGEM_M, d[2] + MARGEM_M
    return [
        ("PLANTA-BAIXA", "PLAN_VIEW", (c[0], c[1], 1.50), (0, 0, 0),
         larg_x, larg_y, 1.50 - mn[2] + 0.2, planta, None),
        ("ELEVACAO-LATERAL", "ELEVATION_VIEW", (c[0], mn[1] - 1.0, c[2]), (r(90), 0, 0),
         larg_x, alt, ys[0] - mn[1] + 1.6, [], None),   # ate passar a linha dos pilares
        ("ELEVACAO-FRONTAL", "ELEVATION_VIEW", (mn[0] - 1.0, c[1], c[2]), (r(90), 0, r(-90)),
         larg_y, alt, xs[0] - mn[0] + 1.6, [], None),
        ("CORTE-TRANSVERSAL", "SECTION_VIEW", (x_corte, c[1], c[2]), (r(90), 0, r(-90)),
         larg_y, alt, 3.5, corte, None),
        # a mesma maquete filtrada por disciplina: consulta do seletor IFC no desenho
        ("PLANTA-FUNDACAO", "PLAN_VIEW", (c[0], c[1], 0.30), (0, 0, 0),
         larg_x, larg_y, 0.30 - mn[2] + 0.2, planta, "IfcFooting, IfcColumn"),
        ("PLANTA-COBERTURA", "PLAN_VIEW", (c[0], c[1], topo + 1.0), (0, 0, 0),
         larg_x, larg_y, topo + 1.0 - alt_col + 0.6, planta, "IfcBeam, IfcMember"),
    ]


def main(ifc_path, so_estas=(), titulo="GALPAO", revisao="00"):
    rel = {"passos": [], "avisos": [], "cotas": {}, "papel_mm": {}}

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
    mn, mx = _envelope(tool)
    xs, ys, alt_col = _eixos(ifc)
    cumeeira = _cumeeira(ifc)
    rel["envelope_m"] = [[round(a, 2), round(b, 2)] for a, b in zip(mn, mx)]
    rel["eixos_m"] = {"x": xs, "y": ys, "altura_pilar": alt_col, "cumeeira": cumeeira}
    props = bpy.context.scene.DocProperties
    cena = bpy.context.scene
    feitos = {a.id() for a in ifc.by_type("IfcAnnotation") if a.ObjectType == "DRAWING"}

    for nome, tipo, pos, rot, larg, alt, prof, cotas, filtro in vistas_do_galpao(
            mn, mx, xs, ys, alt_col, cumeeira):
        if so_estas and nome not in so_estas:
            continue

        def _vista():
            props.target_view = tipo
            bpy.ops.bim.add_drawing()
            des = [a for a in ifc.by_type("IfcAnnotation")
                   if a.ObjectType == "DRAWING" and a.id() not in feitos][0]
            feitos.add(des.id())
            core.update_drawing_name(tool.Ifc, tool.Drawing, drawing=des, name=nome)
            if filtro:
                ifcopenshell.api.pset.edit_pset(
                    ifc, pset=tool.Pset.get_element_pset(des, "EPset_Drawing"),
                    properties={"Include": filtro})
            bpy.ops.bim.activate_drawing(drawing=des.id(), should_view_from_camera=False)
            cam = cena.camera
            cam.location, cam.rotation_euler = pos, rot
            cp = cam.data.BIMCameraProperties
            cp.diagram_scale = ESCALA
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
                _cota(tool, des, p1, p2)
            rel["cotas"][nome] = len(cotas)
            rel["papel_mm"][nome] = (round(larg * MM_POR_M, 1), round(alt * MM_POR_M, 1))
            # sync=True cria no IFC as anotacoes de referencia (eixos da grade,
            # marcas de corte e de elevacao). Elas so entram no SVG depois de o
            # projeto ser RECARREGADO: por isso a segunda passada, la embaixo.
            bpy.ops.bim.create_drawing(print_all=False, open_viewer=False, sync=True)

        passo(nome, _vista)

    def _folhas():
        raiz = os.path.dirname(ifc_path)
        tamanhos = [(n,) + tuple(rel["papel_mm"][n]) for n in ORDEM if n in rel["papel_mm"]]
        plano = distribuir(tamanhos)
        props.titleblock = "A1"
        for k, folha in enumerate(plano, 1):
            antes = {sh.ifc_definition_id for sh in props.sheets if sh.is_sheet}
            bpy.ops.bim.add_sheet()
            if k == 1:
                _carimbo_em_portugues(os.path.join(raiz, "layouts", "titleblocks", "A1.svg"))
            bpy.ops.bim.load_sheets()
            bpy.ops.bim.load_drawings()
            for item in props.drawings:
                if not item.is_drawing:
                    item.is_expanded = True
            tool.Drawing.import_drawings()
            # a lista vem ordenada pela identificacao: a folha nova nao e' a ultima
            idx = [i for i, sh in enumerate(props.sheets)
                   if sh.is_sheet and sh.ifc_definition_id not in antes][0]
            props.active_sheet_index = idx
            for nome, _x, _y in folha:
                for i, item in enumerate(props.drawings):
                    if item.is_drawing and item.name == nome:
                        props.active_drawing_index = i
                        bpy.ops.bim.add_drawing_to_sheet()
            nova = ifc.by_id(props.sheets[idx].ifc_definition_id)
            core.rename_sheet(
                tool.Ifc, tool.Drawing, sheet=nova,
                identification="EST-%02d" % k,
                name=" / ".join(TITULO_CURTO.get(n, n) for n, _x, _y in folha))
            tool.Ifc.run("document.edit_information", information=nova,
                         attributes={"Revision": revisao})
        posicoes = {n: (x, y) for folha in plano for n, x, y in folha}
        rel["reposicionados"] = _reposicionar(os.path.join(raiz, "layouts"), posicoes)
        bpy.ops.bim.load_sheets()
        bpy.ops.bim.create_sheets(create_all=True, open_viewer=False)
        rel["folhas"] = [[n for n, _x, _y in folha] for folha in plano]

    passo("folhas A1", _folhas)
    passo("salvar IFC", lambda: bpy.ops.bim.save_project(filepath=ifc_path,
                                                         should_save_as=False))

    def _segunda_passada():
        """Recarrega o IFC salvo e gera de novo desenhos e folhas: medido, as
        anotacoes de referencia criadas na primeira passada (25 eixos no galpao
        de 20 x 28,5 m) so aparecem no SVG numa sessao que ja abre com elas."""
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o)
        bpy.ops.bim.load_project(filepath=ifc_path, use_relative_path=False,
                                 should_start_fresh_session=False)
        novo = tool.Ifc.get()
        cena2 = bpy.context.scene
        feitos2 = 0
        for des in novo.by_type("IfcAnnotation"):
            if des.ObjectType != "DRAWING" or des.Name not in rel["cotas"]:
                continue
            bpy.ops.bim.activate_drawing(drawing=des.id(), should_view_from_camera=False)
            cp = cena2.camera.data.BIMCameraProperties
            cena2.render.resolution_x, cena2.render.resolution_y = cp.raster_x, cp.raster_y
            bpy.ops.bim.create_drawing(print_all=False, open_viewer=False)
            feitos2 += 1
        bpy.ops.bim.load_sheets()
        bpy.ops.bim.create_sheets(create_all=True, open_viewer=False)
        return feitos2

    rel["segunda_passada"] = passo("segunda passada", _segunda_passada)
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
    main(args[0], tuple(a for a in args[1:] if "=" not in a),
         titulo=opcoes.get("titulo", "GALPAO"), revisao=opcoes.get("revisao", "00"))
