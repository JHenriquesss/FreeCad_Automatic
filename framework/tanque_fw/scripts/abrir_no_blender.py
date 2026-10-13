"""Abre o IFC do tanque-base no Blender COM janela (Bonsai), para olhar o modelo.

Uso: blender --python abrir_no_blender.py -- <caminho.ifc>
Abra a copia de trabalho das pranchas (pranchas/bonsai/...ifc) para ver tambem os
desenhos e as folhas na aba de documentacao do Bonsai.
"""
import sys

import bpy

IFC = sys.argv[sys.argv.index("--") + 1]


def _enquadrar():
    for janela in bpy.context.window_manager.windows:
        for area in janela.screen.areas:
            if area.type != "VIEW_3D":
                continue
            regiao = [r for r in area.regions if r.type == "WINDOW"][0]
            with bpy.context.temp_override(window=janela, area=area, region=regiao):
                bpy.ops.view3d.view_all(center=False)
            area.spaces.active.shading.type = "SOLID"


def _abrir():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.bim.load_project(filepath=IFC, use_relative_path=False,
                             should_start_fresh_session=False)
    _enquadrar()
    return None      # nao repete o temporizador


# a janela precisa existir antes de carregar e enquadrar
bpy.app.timers.register(_abrir, first_interval=1.5)
