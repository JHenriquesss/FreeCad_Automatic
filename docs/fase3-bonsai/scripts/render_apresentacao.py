"""Fase 3 (plano de 2026-10-08) - render de apresentacao do IFC do motor, sem janela.

Uso:
    blender -b --python render_apresentacao.py -- <modelo.ifc> <saida.png> [CYCLES|BLENDER_EEVEE]

Abre o IFC pelo Bonsai, da um material por classe IFC, esconde o tapamento
lateral (a telha fica) para a estrutura aparecer, enquadra pelo envelope do
modelo e grava a imagem. Imprime `RELATORIO_JSON {...}` com o motor e o tempo.

Medido no Blender 5.2.1 LTS em 2026-10-09: no EEVEE sem janela a luz do sol nao
entra na imagem (sai sem sombra, so com a luz do ceu); no CYCLES a sombra sai.
Por isso o motor padrao e' CYCLES (48 amostras com reducao de ruido, na CPU).
As cores, o sol e a camera sao escolha de apresentacao, nao dado do projeto.
"""
import json
import math
import sys
import time
import traceback

import bpy
import mathutils

AMOSTRAS_CYCLES = 48
DIRECAO_DO_SOL = (0.45, 0.55, -0.70)          # de onde a luz vem para onde vai
# classe IFC -> (nome, cor RGBA, metalico, rugosidade)
MATERIAIS = {
    "IfcColumn": ("aco_portico", (0.55, 0.08, 0.06, 1), 0.6, 0.45),
    "IfcBeam": ("aco_viga", (0.55, 0.08, 0.06, 1), 0.6, 0.45),
    "IfcMember": ("aco_sec", (0.62, 0.64, 0.66, 1), 0.8, 0.35),
    "IfcPlate": ("chapa", (0.3, 0.3, 0.32, 1), 0.7, 0.4),
    "IfcMechanicalFastener": ("paraf", (0.15, 0.15, 0.15, 1), 0.8, 0.4),
    "IfcFooting": ("concreto", (0.62, 0.61, 0.58, 1), 0.0, 0.9),
    "IfcCovering": ("telha", (0.82, 0.84, 0.86, 1), 0.5, 0.4),
}


def _material(nome, cor, metal, rug):
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = cor
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rug
    m.diffuse_color = cor
    return m


def main(ifc_path, out_png, motor):
    rel = {"motor": motor}
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.bim.load_project(filepath=ifc_path, use_relative_path=False,
                             should_start_fresh_session=False)
    import bonsai.tool as tool
    ifc = tool.Ifc.get()
    mats = {classe: _material(*dados) for classe, dados in MATERIAIS.items()}
    pts = []
    for el in ifc.by_type("IfcElement"):
        o = tool.Ifc.get_object(el)
        if not o or o.type != "MESH":
            continue
        if el.is_a() in mats:
            o.data.materials.clear()
            o.data.materials.append(mats[el.is_a()])
        pts += [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    if not pts:
        raise RuntimeError("o IFC nao trouxe nenhum elemento com geometria")
    # o tapamento lateral esconderia a estrutura; a telha da cobertura fica
    for el in ifc.by_type("IfcCovering"):
        if el.PredefinedType == "CLADDING":
            tool.Ifc.get_object(el).hide_render = True
    mn = mathutils.Vector([min(p[i] for p in pts) for i in range(3)])
    mx = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
    c = (mn + mx) / 2
    diag = (mx - mn).length

    bpy.ops.mesh.primitive_plane_add(size=diag * 6, location=(c.x, c.y, -0.02))
    bpy.context.active_object.data.materials.append(
        _material("piso", (0.30, 0.33, 0.27, 1), 0.0, 0.95))
    cena = bpy.context.scene
    dados_cam = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", dados_cam)
    cena.collection.objects.link(cam)
    cam.location = c + mathutils.Vector((-0.62, -0.78, 0.22)) * diag
    dados_cam.lens = 32
    dados_cam.clip_end = diag * 20
    cam.rotation_euler = ((c + mathutils.Vector((0, 0, -1.0))) - cam.location
                          ).to_track_quat("-Z", "Y").to_euler()
    cena.camera = cam

    dados_sol = bpy.data.lights.new("Sol", "SUN")
    dados_sol.energy = 4.5
    dados_sol.angle = math.radians(1.5)
    sol = bpy.data.objects.new("Sol", dados_sol)
    cena.collection.objects.link(sol)
    sol.rotation_euler = mathutils.Vector(DIRECAO_DO_SOL).to_track_quat("-Z", "Y").to_euler()

    ceu = bpy.data.worlds.new("Ceu")
    ceu.use_nodes = True
    cena.world = ceu
    fundo = ceu.node_tree.nodes["Background"]
    fundo.inputs[0].default_value = (0.50, 0.68, 0.95, 1)
    fundo.inputs[1].default_value = 0.7

    cena.render.resolution_x, cena.render.resolution_y = 1920, 1080
    cena.render.filepath = out_png
    cena.render.image_settings.file_format = "PNG"
    cena.render.engine = motor
    cena.view_settings.view_transform = "AgX"
    try:
        cena.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        rel["contraste"] = "padrao (o desta versao do Blender nao tem o nome esperado)"
    if motor == "CYCLES":
        cena.cycles.samples = AMOSTRAS_CYCLES
        cena.cycles.use_denoising = True
        cena.cycles.device = "CPU"
    t = time.time()
    bpy.ops.render.render(write_still=True)
    rel.update(tempo_s=round(time.time() - t, 1), png=out_png)
    return rel


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    try:
        relatorio = main(args[0], args[1], args[2] if len(args) > 2 else "CYCLES")
    except Exception:
        relatorio = {"erro": traceback.format_exc()[-1200:]}
    print("RELATORIO_JSON " + json.dumps(relatorio, ensure_ascii=False))
