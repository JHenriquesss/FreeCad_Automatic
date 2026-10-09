import sys, time, json, math, traceback
import bpy, mathutils
argv = sys.argv[sys.argv.index("--") + 1:]
ifc_path, out_png, motor = argv[0], argv[1], argv[2]
rel = {}
try:
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    bpy.ops.bim.load_project(filepath=ifc_path, use_relative_path=False, should_start_fresh_session=False)
    import bonsai.tool as tool
    f = tool.Ifc.get()
    def mat(nome, cor, metal=0.0, rug=0.6):
        m = bpy.data.materials.new(nome); m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = cor; b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rug
        m.diffuse_color = cor
        return m
    mats = {"IfcColumn": mat("aco_portico", (0.55, 0.08, 0.06, 1), 0.6, 0.45), "IfcBeam": mat("aco_viga", (0.55, 0.08, 0.06, 1), 0.6, 0.45),
            "IfcMember": mat("aco_sec", (0.62, 0.64, 0.66, 1), 0.8, 0.35), "IfcPlate": mat("chapa", (0.3, 0.3, 0.32, 1), 0.7, 0.4),
            "IfcMechanicalFastener": mat("paraf", (0.15, 0.15, 0.15, 1), 0.8, 0.4), "IfcFooting": mat("concreto", (0.62, 0.61, 0.58, 1), 0.0, 0.9),
            "IfcCovering": mat("telha", (0.82, 0.84, 0.86, 1), 0.5, 0.4)}
    pts = []
    for el in f.by_type("IfcElement"):
        o = tool.Ifc.get_object(el)
        if not o or o.type != "MESH": continue
        m = mats.get(el.is_a())
        if m:
            o.data.materials.clear(); o.data.materials.append(m)
        pts += [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    # tapamento lateral transparente o bastante para ver a estrutura: oculta so o fechamento, mantem a telha
    for el in f.by_type("IfcCovering"):
        if el.PredefinedType == "CLADDING":
            o = tool.Ifc.get_object(el); o.hide_render = True
    mn = mathutils.Vector([min(p[i] for p in pts) for i in range(3)]); mx = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
    c = (mn + mx) / 2; diag = (mx - mn).length
    bpy.ops.mesh.primitive_plane_add(size=diag * 6, location=(c.x, c.y, -0.02))
    chao = bpy.context.active_object; chao.data.materials.append(mat("piso", (0.42, 0.45, 0.38, 1), 0.0, 0.95))
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(cam)
    cam.location = c + mathutils.Vector((-0.62, -0.78, 0.22)) * diag; cd.lens = 32; cd.clip_end = diag * 20
    cam.rotation_euler = ((c + mathutils.Vector((0, 0, -1.0))) - cam.location).to_track_quat("-Z", "Y").to_euler(); sc.camera = cam
    sd = bpy.data.lights.new("Sol", "SUN"); sd.energy = 4.0; sd.angle = math.radians(2)
    sol = bpy.data.objects.new("Sol", sd); sc.collection.objects.link(sol); sol.rotation_euler = (math.radians(52), 0, math.radians(-40))
    w = bpy.data.worlds.new("Ceu"); w.use_nodes = True; sc.world = w
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.75, 0.92, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.filepath = out_png; sc.render.image_settings.file_format = "PNG"
    sc.render.engine = motor
    sc.view_settings.view_transform = "Standard"
    t = time.time(); bpy.ops.render.render(write_still=True)
    rel.update(motor=motor, tempo_s=round(time.time() - t, 1), png=out_png)
except Exception:
    rel["erro"] = traceback.format_exc()[-1200:]
print("RELATORIO_JSON " + json.dumps(rel, ensure_ascii=False))
