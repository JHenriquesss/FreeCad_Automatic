"""Video de apresentacao do tanque-base: a camera da' uma volta em torno do modelo.

Reusa a cena do render (render_tanque.montar_cena). Grava os quadros em PNG e
depois junta num MP4 (H.264), que abre em celular e computador.

Uso: blender -b --python video_tanque.py -- <caminho.ifc> <saida.mp4>
                                           [segundos=8] [motor=BLENDER_EEVEE]
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
sys.path.insert(0, AQUI)
import render_tanque as RT   # noqa: E402

QUADROS_POR_SEGUNDO = 24
RESOLUCAO = (1280, 720)
ALTURA_DA_CAMERA = 0.42      # componente vertical da direcao, como no render parado
AMOSTRAS_CYCLES_VIDEO = 12
# visto de ponta, o modelo fica mais perto da camera e a base saia cortada embaixo:
# o video usa a camera mais longe que o render parado
AFASTAMENTO = 1.30


def _saida_de_video(cena, caminho):
    cena.render.filepath = caminho
    img = cena.render.image_settings
    if hasattr(img, "media_type"):          # Blender 5: o tipo de midia vem antes do formato
        img.media_type = "VIDEO"
    img.file_format = "FFMPEG"
    cena.render.ffmpeg.format = "MPEG4"
    cena.render.ffmpeg.codec = "H264"
    cena.render.ffmpeg.constant_rate_factor = "HIGH"


def main(ifc_path, saida, segundos=8.0, motor="BLENDER_EEVEE"):
    rel, cena, cam, centro, dist = RT.montar_cena(ifc_path, motor)
    dist *= AFASTAMENTO
    if motor == "CYCLES":
        cena.cycles.samples = AMOSTRAS_CYCLES_VIDEO
    else:
        # no EEVEE sem janela a sombra do sol sai em manchas enormes no piso, que mudam
        # a cada quadro (medido em 2026-10-12): o video fica sem sombra projetada
        for luz in bpy.data.lights:
            luz.use_shadow = False
    n = int(round(segundos * QUADROS_POR_SEGUNDO))
    cena.render.resolution_x, cena.render.resolution_y = RESOLUCAO
    cena.render.fps = QUADROS_POR_SEGUNDO
    cena.frame_start, cena.frame_end = 1, n
    # uma volta completa, comecando da mesma posicao do render parado
    inicio = math.atan2(RT.DIRECAO_DA_CAMERA[1], RT.DIRECAO_DA_CAMERA[0])
    horizontal = math.sqrt(1 - ALTURA_DA_CAMERA ** 2 / (
        sum(v * v for v in RT.DIRECAO_DA_CAMERA)))
    vertical = math.sqrt(1 - horizontal ** 2)
    for k in range(1, n + 1):
        ang = inicio + 2 * math.pi * (k - 1) / n
        direcao = mathutils.Vector((math.cos(ang) * horizontal, math.sin(ang) * horizontal,
                                    vertical))
        cam.location = centro + direcao * dist
        cam.rotation_euler = (centro - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.keyframe_insert("location", frame=k)
        cam.keyframe_insert("rotation_euler", frame=k)
    _saida_de_video(cena, saida)
    t = time.time()
    bpy.ops.render.render(animation=True)
    rel.update(quadros=n, tempo_s=round(time.time() - t, 1), mp4=saida,
               bytes=os.path.getsize(saida) if os.path.isfile(saida) else 0)
    return rel


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    op = dict(a.split("=", 1) for a in args[2:] if "=" in a)
    try:
        rel = main(args[0], args[1], float(op.get("segundos", 8)),
                   op.get("motor", "BLENDER_EEVEE"))
    except Exception:
        rel = {"erro": traceback.format_exc()}
    print("RELATORIO_JSON " + json.dumps(rel, ensure_ascii=False))
