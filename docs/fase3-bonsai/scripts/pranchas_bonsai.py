"""Fase 3 (plano de 2026-10-08) - pranchas do galpao pelo Blender + Bonsai, sem janela.

Abre o IFC gerado pelo motor (ifc_emit), cria as vistas enquadradas no modelo,
cota pelos eixos lidos dos proprios pilares do IFC, monta a folha com carimbo e
grava tudo ao lado do IFC (drawings/, layouts/, sheets/). Nada e' editado a mao:
alterou o projeto, regenera o IFC e roda de novo.

Uso (o IFC e' COPIADO para uma pasta de trabalho antes: o Bonsai grava nele):
    blender -b --python pranchas_bonsai.py -- <caminho.ifc> [VISTA ...]

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
# desenhos por folha A1 (medido: planta + corte + elevacao frontal cabem; duas
# plantas de 40 m na mesma folha nao cabem)
FOLHAS = [("PLANTA-BAIXA", "CORTE-TRANSVERSAL", "ELEVACAO-FRONTAL"),
          ("PLANTA-FUNDACAO", "ELEVACAO-LATERAL"),
          ("PLANTA-COBERTURA",)]
ESCALA = "1:100|1/100"


def _envelope():
    pts = []
    for o in bpy.data.objects:
        if o.type == "MESH":
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


def vistas_do_galpao(mn, mx, xs, ys, alt_col):
    """(nome, tipo, posicao, rotacao, largura, altura, profundidade, cotas, filtro)."""
    c = [(a + b) / 2 for a, b in zip(mn, mx)]
    d = [b - a for a, b in zip(mn, mx)]
    r = math.radians
    x0, x1, y0, y1 = xs[0], xs[-1], ys[0], ys[-1]
    topo = mx[2]
    x_corte = (xs[1] + xs[2]) / 2 if len(xs) > 2 else c[0]
    planta = ([((a, y0 - 3.0, 0), (b, y0 - 3.0, 0)) for a, b in zip(xs, xs[1:])]
              + [((x0, y0 - 4.5, 0), (x1, y0 - 4.5, 0))]
              + [((x0 - 3.0, a, 0), (x0 - 3.0, b, 0)) for a, b in zip(ys, ys[1:])])
    corte = [((0, y0, -3.2), (0, y1, -3.2)),
             ((0, y0 - 2.5, 0.0), (0, y0 - 2.5, alt_col)),
             ((0, y1 + 2.5, 0.0), (0, y1 + 2.5, topo))]
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


def main(ifc_path, so_estas=()):
    rel = {"passos": [], "avisos": [], "cotas": {}}

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
    mn, mx = _envelope()
    xs, ys, alt_col = _eixos(ifc)
    rel["envelope_m"] = [[round(a, 2), round(b, 2)] for a, b in zip(mn, mx)]
    rel["eixos_m"] = {"x": xs, "y": ys, "altura_pilar": alt_col}
    props = bpy.context.scene.DocProperties
    cena = bpy.context.scene
    feitos = {a.id() for a in ifc.by_type("IfcAnnotation") if a.ObjectType == "DRAWING"}

    for nome, tipo, pos, rot, larg, alt, prof, cotas, filtro in vistas_do_galpao(
            mn, mx, xs, ys, alt_col):
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
            bpy.ops.bim.create_drawing(print_all=False, open_viewer=False)

        passo(nome, _vista)

    def _folhas():
        # o Bonsai empilha os desenhos na folha sem conferir se cabem: uma folha
        # por grupo que cabe num A1 em 1:100
        props.titleblock = "A1"
        feitas = []
        for grupo in FOLHAS:
            nomes = [n for n in grupo if n in rel["cotas"]]
            if not nomes:
                continue
            bpy.ops.bim.add_sheet()
            bpy.ops.bim.load_sheets()
            bpy.ops.bim.load_drawings()
            for item in props.drawings:
                if not item.is_drawing:
                    item.is_expanded = True
            tool.Drawing.import_drawings()
            props.active_sheet_index = max(i for i, sh in enumerate(props.sheets) if sh.is_sheet)
            for nome in nomes:
                for i, item in enumerate(props.drawings):
                    if item.is_drawing and item.name == nome:
                        props.active_drawing_index = i
                        bpy.ops.bim.add_drawing_to_sheet()
            feitas.append(nomes)
        bpy.ops.bim.create_sheets(create_all=True, open_viewer=False)
        rel["folhas"] = feitas

    passo("folhas A1", _folhas)
    passo("salvar IFC", lambda: bpy.ops.bim.save_project(filepath=ifc_path,
                                                         should_save_as=False))
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
    main(args[0], tuple(args[1:]))
