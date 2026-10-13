"""Render de apresentacao do tanque-base (Blender + Bonsai, sem janela).

Usa os materiais do render do galpao (docs/fase3-bonsai/scripts/
render_apresentacao.py). Mudam duas coisas que aquele script nao precisava:
  - a camera e' afastada ate' TODO o modelo caber no quadro (a do galpao mira
    abaixo do centro e cortava o conteiner em cima da base);
  - o conteiner de referencia sai translucido, para a base aparecer por baixo.

Uso: blender -b --python render_tanque.py -- <caminho.ifc> <saida.png> [CYCLES|...]
Imprime `RELATORIO_JSON {...}`.
"""
import json
import math
import os
import sys
import time
import traceback

import bpy
import mathutils

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(
    AQUI, "..", "..", "..", "docs", "fase3-bonsai", "scripts")))
import render_apresentacao as RA   # noqa: E402

DIRECAO_DA_CAMERA = (-0.62, -0.78, 0.42)     # do centro do modelo para a camera
FOLGA_DO_QUADRO = 0.80        # a esfera envolvente sobra: o modelo e' comprido e baixo
# marca da peca -> (nome, cor RGBA, metalico, rugosidade)
POR_MARCA = {
    "CONTEINER": ("conteiner", (0.80, 0.82, 0.84, 0.28), 0.0, 0.6),
    "RESPIRO": ("tubo", (0.85, 0.85, 0.85, 1), 0.2, 0.5),
    "ENTRADA": ("tubo", (0.85, 0.85, 0.85, 1), 0.2, 0.5),
    "SUCCAO": ("tubo", (0.85, 0.85, 0.85, 1), 0.2, 0.5),
    "LAVAGEM": ("tubo", (0.85, 0.85, 0.85, 1), 0.2, 0.5),
    "CONE": ("cone", (0.95, 0.75, 0.10, 1), 0.6, 0.4),
    "PESCADOR": ("tubo", (0.85, 0.85, 0.85, 1), 0.2, 0.5),
    "QUEBRA-VACUO": ("cone", (0.95, 0.75, 0.10, 1), 0.6, 0.4),
    "SENSOR-NIVEL": ("cone", (0.95, 0.75, 0.10, 1), 0.6, 0.4),
    "CHAVE-HH": ("cone", (0.95, 0.75, 0.10, 1), 0.6, 0.4),
    "DEGRAU": ("degrau", (0.45, 0.47, 0.50, 1), 0.7, 0.5),
    "BANZO": ("degrau", (0.45, 0.47, 0.50, 1), 0.7, 0.5),
    "CORRIMAO": ("cone", (0.95, 0.75, 0.10, 1), 0.6, 0.4),
    "FLANGE": ("tubo", (0.85, 0.85, 0.85, 1), 0.2, 0.5),
    "VALVULA": ("valvula", (0.10, 0.25, 0.60, 1), 0.5, 0.4),
    "ENGATE": ("cone", (0.95, 0.75, 0.10, 1), 0.6, 0.4),
}


def _translucido(nome, cor, metal, rug):
    m = RA._material(nome, cor, metal, rug)
    m.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value = cor[3]
    if hasattr(m, "blend_method"):
        m.blend_method = "BLEND"
    return m


def montar_cena(ifc_path, motor):
    """Carrega o IFC, aplica materiais, piso, camera, sol e ceu. Nao renderiza.

    Devolve (rel, cena, camera, centro, distancia): o video reusa a mesma cena."""
    rel = {"motor": motor}
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.bim.load_project(filepath=ifc_path, use_relative_path=False,
                             should_start_fresh_session=False)
    import bonsai.tool as tool
    ifc = tool.Ifc.get()
    mats = {classe: RA._material(*dados) for classe, dados in RA.MATERIAIS.items()}
    mats_marca = {}
    pts = []
    # sem o conteiner, o respiro (que sobe alem dele) nao entra no enquadramento
    tem_conteiner = any(e.Name == "CONTEINER" for e in ifc.by_type("IfcElement"))
    for el in ifc.by_type("IfcElement"):
        o = tool.Ifc.get_object(el)
        if not o or o.type != "MESH":
            continue
        if el.Name in POR_MARCA:
            dados = POR_MARCA[el.Name]
            if dados[0] not in mats_marca:
                mats_marca[dados[0]] = (_translucido if dados[1][3] < 1 else RA._material)(*dados)
            o.data.materials.clear()
            o.data.materials.append(mats_marca[dados[0]])
        elif el.is_a() in mats:
            o.data.materials.clear()
            o.data.materials.append(mats[el.is_a()])
        if tem_conteiner or el.Name != "RESPIRO":
            pts += [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    if not pts:
        raise RuntimeError("o IFC nao trouxe nenhum elemento com geometria")
    mn = mathutils.Vector([min(p[i] for p in pts) for i in range(3)])
    mx = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
    c = (mn + mx) / 2
    raio = max((p - c).length for p in pts)

    bpy.ops.mesh.primitive_plane_add(size=raio * 14, location=(c.x, c.y, mn.z - 0.005))
    bpy.context.active_object.data.materials.append(
        RA._material("piso", (0.30, 0.33, 0.27, 1), 0.0, 0.95))
    cena = bpy.context.scene
    cena.render.resolution_x, cena.render.resolution_y = 1920, 1080
    dados_cam = bpy.data.cameras.new("Cam")
    dados_cam.lens = 40
    cam = bpy.data.objects.new("Cam", dados_cam)
    cena.collection.objects.link(cam)
    # a esfera que envolve o modelo tem de caber no menor angulo do quadro
    ang_h = 2 * math.atan(dados_cam.sensor_width / 2 / dados_cam.lens)
    ang_v = 2 * math.atan(math.tan(ang_h / 2) * 1080 / 1920)
    dist = raio * FOLGA_DO_QUADRO / math.sin(min(ang_h, ang_v) / 2)
    direcao = mathutils.Vector(DIRECAO_DA_CAMERA).normalized()
    cam.location = c + direcao * dist
    dados_cam.clip_end = dist * 20
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    cena.camera = cam
    rel["distancia_m"] = round(dist, 2)

    dados_sol = bpy.data.lights.new("Sol", "SUN")
    dados_sol.energy = 4.5
    dados_sol.angle = math.radians(1.5)
    sol = bpy.data.objects.new("Sol", dados_sol)
    cena.collection.objects.link(sol)
    sol.rotation_euler = mathutils.Vector(RA.DIRECAO_DO_SOL).to_track_quat("-Z", "Y").to_euler()

    ceu = bpy.data.worlds.new("Ceu")
    ceu.use_nodes = True
    cena.world = ceu
    fundo = ceu.node_tree.nodes["Background"]
    fundo.inputs[0].default_value = (0.50, 0.68, 0.95, 1)
    fundo.inputs[1].default_value = 0.7

    cena.render.engine = motor
    cena.view_settings.view_transform = "AgX"
    try:
        cena.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        rel["contraste"] = "padrao"
    if motor == "CYCLES":
        cena.cycles.samples = RA.AMOSTRAS_CYCLES
        cena.cycles.use_denoising = True
        cena.cycles.device = "CPU"
    return rel, cena, cam, c, dist


def main(ifc_path, out_png, motor):
    rel, cena, _cam, _c, _dist = montar_cena(ifc_path, motor)
    cena.render.filepath = out_png
    cena.render.image_settings.file_format = "PNG"
    t = time.time()
    bpy.ops.render.render(write_still=True)
    rel.update(tempo_s=round(time.time() - t, 1), png=out_png)
    return rel


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    try:
        rel = main(args[0], args[1], args[2] if len(args) > 2 else "CYCLES")
    except Exception:
        rel = {"erro": traceback.format_exc()}
    print("RELATORIO_JSON " + json.dumps(rel, ensure_ascii=False))
