"""Exporta o IFC do tanque-base para GLB (modelo 3D que abre sem Blender).

O GLB abre no Visualizador 3D do Windows, no navegador e na maioria dos
visualizadores de celular. Usa os mesmos materiais do render.

Uso: blender -b --python exportar_glb.py -- <caminho.ifc> <saida.glb>
Imprime `RELATORIO_JSON {...}`.
"""
import json
import os
import sys
import traceback

import bpy

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.normpath(os.path.join(
    AQUI, "..", "..", "..", "docs", "fase3-bonsai", "scripts")))
import render_apresentacao as RA   # noqa: E402
import render_tanque as RT         # noqa: E402


def main(ifc_path, saida):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.bim.load_project(filepath=ifc_path, use_relative_path=False,
                             should_start_fresh_session=False)
    import bonsai.tool as tool
    mats = {classe: RA._material(*dados) for classe, dados in RA.MATERIAIS.items()}
    por_marca = {}
    n = 0
    for el in tool.Ifc.get().by_type("IfcElement"):
        o = tool.Ifc.get_object(el)
        if not o or o.type != "MESH":
            continue
        if el.is_a() == "IfcOpeningElement":
            o.hide_render = True
            o.hide_set(True)
            continue
        dados = RT.POR_MARCA.get(el.Name)
        if dados:
            if dados[0] not in por_marca:
                por_marca[dados[0]] = (RT._translucido if dados[1][3] < 1 else RA._material)(*dados)
            mat = por_marca[dados[0]]
        else:
            mat = mats.get(el.is_a())
        if mat:
            o.data.materials.clear()
            o.data.materials.append(mat)
        n += 1
    bpy.ops.export_scene.gltf(filepath=saida, export_format="GLB", use_visible=True,
                              export_apply=True)
    return {"glb": saida, "objetos": n, "bytes": os.path.getsize(saida)}


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    try:
        rel = main(args[0], args[1])
    except Exception:
        rel = {"erro": traceback.format_exc()}
    print("RELATORIO_JSON " + json.dumps(rel, ensure_ascii=False))
