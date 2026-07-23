# ============================================================================
# ifc_emit.py - EMISSOR IFC4 PURO-PYTHON (via ifcopenshell), SEM FreeCAD. Consome
# o modelo_neutro (barras com perfil + extremidades) e escreve um .ifc abrivel no
# Revit/Eberick. Item 2 do roteiro: tira o FreeCAD do caminho critico do
# entregavel BIM. Cada barra vira IfcColumn/IfcBeam com o PERFIL I extrudado ao
# longo do proprio eixo, tipada e nomeada pela marca.
#
# DEPENDENCIA: ifcopenshell (pip install ifcopenshell). Fica isolado aqui - o resto
# do framework nao importa ifcopenshell. Se ausente, `disponivel()` retorna False e
# o chamador cai para o export via FreeCAD (build_galpao._export_ifc).
#
# Orientacao da secao: eixo local Z = eixo da barra; X local = global X (fora do
# plano do portico) exceto se a barra for paralela a X; Y local = Z x X. Assim a
# ALMA (profundidade d) fica no plano do portico (Y-Z), como no calculo/FreeCAD.
# Coordenadas em mm.
# ============================================================================
"""Emissor IFC4 puro-Python (ifcopenshell) a partir do modelo_neutro."""

from __future__ import annotations

import math


def disponivel():
    """True se o ifcopenshell estiver instalado (emissor puro utilizavel)."""
    try:
        import ifcopenshell  # noqa: F401
        return True
    except Exception:
        return False


def _base_axes(p1, p2):
    """Eixos locais (x, y, z) da barra p1->p2: z = eixo; x ~ global X perpendicular
    a z; y = z x x (destro). Retorna (x, y, z, L) com L o comprimento."""
    dz = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
    L = math.sqrt(dz[0] ** 2 + dz[1] ** 2 + dz[2] ** 2)
    if L < 1e-9:
        return (1, 0, 0), (0, 1, 0), (0, 0, 1), 0.0
    z = (dz[0] / L, dz[1] / L, dz[2] / L)
    ref = (1.0, 0.0, 0.0) if abs(z[0]) < 0.9 else (0.0, 1.0, 0.0)
    # x = ref perpendicular a z
    d = ref[0] * z[0] + ref[1] * z[1] + ref[2] * z[2]
    x = (ref[0] - d * z[0], ref[1] - d * z[1], ref[2] - d * z[2])
    nx = math.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
    x = (x[0] / nx, x[1] / nx, x[2] / nx)
    # y = z cross x
    y = (z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0])
    return x, y, z, L


def _matriz(p1, p2):
    import numpy as np
    x, y, z, L = _base_axes(p1, p2)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, p1
    return m, L


_IFC_CLASS = {"Column": ("IfcColumn", "COLUMN"), "Beam": ("IfcBeam", "BEAM"),
              "Member": ("IfcMember", "MEMBER"), "Plate": ("IfcPlate", "SHEET")}


def _perfil_ifc(m, nome, s, esc):
    """Cria o perfil IFC da secao. Perfil formado a frio (terca: forma 'C' ou tem
    'lip') -> IfcCShapeProfileDef (canaleta enrijecida). Laminado -> IfcIShapeProfileDef.
    Dims em m * esc (mm). `d`/`h` = altura, `bf` = largura, `tw`/`t` = espessura."""
    forma = str(s.get("forma", "")).upper()
    if forma == "ROUND":                              # barra redonda (tirante/contrav)
        return m.create_entity("IfcCircleProfileDef", ProfileType="AREA",
                               ProfileName=nome, Radius=float(s.get("D") or 0.0) * esc / 2.0)
    h = float(s.get("d") or s.get("h") or 0.0) * esc
    bf = float(s.get("bf") or 0.0) * esc
    if forma == "C" or s.get("lip") is not None:      # formado a frio Ue (com labio)
        t = float(s.get("t") or s.get("tw") or 0.0) * esc
        lip = float(s.get("lip") or 0.0) * esc
        return m.create_entity("IfcCShapeProfileDef", ProfileType="AREA",
                               ProfileName=nome, Depth=h, Width=bf, WallThickness=t,
                               Girth=lip)
    if forma == "U":                                  # perfil U / canaleta (UPE) girt
        return m.create_entity("IfcUShapeProfileDef", ProfileType="AREA",
                               ProfileName=nome, Depth=h, FlangeWidth=bf,
                               WebThickness=float(s.get("tw") or 0.0) * esc,
                               FlangeThickness=float(s.get("tf") or 0.0) * esc)
    return m.create_entity("IfcIShapeProfileDef", ProfileType="AREA", ProfileName=nome,
                           OverallWidth=bf, OverallDepth=h,
                           WebThickness=float(s.get("tw") or 0.0) * esc,
                           FlangeThickness=float(s.get("tf") or 0.0) * esc)


def emitir_ifc(membros, path, nome="Galpao", secao_em_metros=True):
    """Escreve um IFC4 com os `membros` (do modelo_neutro) em `path`. Cada barra ->
    IfcColumn/IfcBeam com perfil I extrudado ao longo do eixo. Retorna o path (ou
    levanta se o ifcopenshell faltar). secao_em_metros: as dims da secao (d/bf/tw/
    tf) estao em m (catalogo) e sao convertidas p/ mm."""
    import ifcopenshell
    from ifcopenshell.api import run

    esc = 1000.0 if secao_em_metros else 1.0
    m = ifcopenshell.file(schema="IFC4")
    proj = run("root.create_entity", m, ifc_class="IfcProject", name=nome)
    run("unit.assign_unit", m)                        # SI (mm via contexto)
    ctx = run("context.add_context", m, context_type="Model")
    body = run("context.add_context", m, context_type="Model",
               context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
    site = run("root.create_entity", m, ifc_class="IfcSite", name="Sitio")
    bld = run("root.create_entity", m, ifc_class="IfcBuilding", name=nome)
    sto = run("root.create_entity", m, ifc_class="IfcBuildingStorey", name="Terreo")
    run("aggregate.assign_object", m, relating_object=proj, products=[site])
    run("aggregate.assign_object", m, relating_object=site, products=[bld])
    run("aggregate.assign_object", m, relating_object=bld, products=[sto])

    perfis_ifc = {}                                   # cache de perfil IFC por nome
    for mb in membros:
        s = mb["secao"]
        key = mb["perfil"]
        prof = perfis_ifc.get(key)
        if prof is None:
            prof = _perfil_ifc(m, key, s, esc)
            perfis_ifc[key] = prof
        cls, pdt = _IFC_CLASS.get(mb["tipo"], ("IfcMember", "MEMBER"))
        el = run("root.create_entity", m, ifc_class=cls, predefined_type=pdt,
                 name=mb.get("marca") or mb["perfil"])
        mat, L = _matriz(mb["p1"], mb["p2"])
        rep = run("geometry.add_profile_representation", m, context=body,
                  profile=prof, depth=L)
        run("geometry.assign_representation", m, product=el, representation=rep)
        run("geometry.edit_object_placement", m, product=el, matrix=mat)
        run("spatial.assign_container", m, relating_structure=sto, products=[el])
    m.write(path)
    return path


def emitir_ifc_do_spec(spec, path):
    """Emite o IFC4 da estrutura PRIMARIA direto do CALCULO (spec), SEM FreeCAD.
    Usa os perfis laminados adotados (perfil_col_adotado/perfil_raf_adotado) +
    catalogo `perfis`. Portico tapered/tesoura (perfil nao-laminado/soldado) ->
    retorna None (esses seguem pelo export via FreeCAD, build_galpao, por ora).
    Retorna o path ou None. Entrada BIM FreeCAD-free do roteiro (item 2)."""
    import modelo_neutro as MN
    import perfis
    est = spec.get("estrutura", {}) or {}
    g = spec["geometria"]

    def _sec(nome):
        p = perfis.PERFIS.get(nome)
        if not p or not all(k in p for k in ("d", "bf", "tw", "tf")):
            return None
        return {"nome": nome, "d": p["d"], "bf": p["bf"], "tw": p["tw"], "tf": p["tf"]}

    col = _sec(est.get("perfil_col_adotado"))
    raf = _sec(est.get("perfil_raf_adotado"))
    if not col or not raf:
        return None                                   # tapered/tesoura -> via FreeCAD
    geo = {"span": g.get("span"), "spans": g.get("spans"),
           "comprimento": g.get("comprimento", 2 * (g.get("span") or 0)),
           "eave": g.get("eave"), "ridge": g.get("ridge", g.get("eave")),
           "bay": g.get("bay")}
    # terças (perfil formado a frio C/Ue), se o calculo forneceu n_terca+terca_dims
    n_terca = est.get("n_terca")
    td = est.get("terca_dims")                         # [h, bf, lip, t] em mm
    terca_sec = None
    if td and len(td) >= 4:
        terca_sec = {"nome": est.get("terca_perfil") or "Terca", "forma": "C",
                     "d": td[0] / 1000.0, "bf": td[1] / 1000.0,
                     "lip": td[2] / 1000.0, "t": td[3] / 1000.0}
    # girts de parede (longarina U), se o calculo forneceu longarina_dims
    ld = est.get("longarina_dims")                    # [h, bf, tw, tf] em mm
    girt_sec = None
    if ld and len(ld) >= 4:
        girt_sec = {"nome": est.get("longarina_perfil") or "Girt", "forma": "U",
                    "d": ld[0] / 1000.0, "bf": ld[1] / 1000.0,
                    "tw": ld[2] / 1000.0, "tf": ld[3] / 1000.0}
    membros = MN.frame_completo(geo, {"col": col, "raf": raf},
                                n_terca=n_terca, terca_sec=terca_sec,
                                girt_sec=girt_sec, col_d=col.get("d"),
                                n_tirante_parede=est.get("n_tirante_parede"),
                                d_tirante_mm=16.0, contrav=True, d_contrav_mm=20.0)
    return emitir_ifc(membros, path, nome=spec.get("slug") or "Galpao")


def emitir_ifc_analitico(modelo, path, nome="Galpao"):
    """Emite o MODELO ANALITICO (do modelo_neutro.analitico_do_spec) em IFC4-Structural
    (IfcStructuralAnalysisModel): nos = IfcStructuralPointConnection (com coord),
    barras = IfcStructuralCurveMember (topologia de aresta ligada aos 2 nos por
    IfcRelConnectsStructuralMember), apoios = IfcBoundaryNodeCondition. Importavel no
    modelo ANALITICO do Revit. Coords 2D (x transversal, y vertical) -> 3D (x,y,0) mm.
    Item 2: o intercambio analitico, sem FreeCAD."""
    import ifcopenshell
    from ifcopenshell.api import run
    from ifcopenshell.guid import new as guid

    m = ifcopenshell.file(schema="IFC4")
    run("root.create_entity", m, ifc_class="IfcProject", name=nome)
    run("unit.assign_unit", m)
    ctx = run("context.add_context", m, context_type="Model")
    sam = m.create_entity("IfcStructuralAnalysisModel", GlobalId=guid(),
                          Name=nome, PredefinedType="LOADING_3D")

    def _pc(nm, x, y):
        p = m.create_entity("IfcCartesianPoint",
                            Coordinates=(float(x) * 1000.0, float(y) * 1000.0, 0.0))
        v = m.create_entity("IfcVertexPoint", VertexGeometry=p)
        top = m.create_entity("IfcTopologyRepresentation", ContextOfItems=ctx,
                              RepresentationIdentifier="Reference",
                              RepresentationType="Vertex", Items=[v])
        pdef = m.create_entity("IfcProductDefinitionShape", Representations=[top])
        return m.create_entity("IfcStructuralPointConnection", GlobalId=guid(),
                               Name=nm, Representation=pdef), v

    conn, vert = {}, {}
    apoio_nos = {a["no"]: a for a in modelo.get("apoios", [])}
    for no in modelo["nos"]:
        pc, v = _pc("N%d" % no["id"], no["x"], no["y"])
        conn[no["id"]], vert[no["id"]] = pc, v
        a = apoio_nos.get(no["id"])
        if a:                                          # apoio -> condicao de contorno
            pc.AppliedCondition = m.create_entity("IfcBoundaryNodeCondition",
                                                   Name=a.get("tipo", "apoio"))
    membros = []
    for k, b in enumerate(modelo["barras"], 1):
        vi, vj = vert[b["no_i"]], vert[b["no_j"]]
        edge = m.create_entity("IfcEdge", EdgeStart=vi, EdgeEnd=vj)
        top = m.create_entity("IfcTopologyRepresentation", ContextOfItems=ctx,
                              RepresentationIdentifier="Reference",
                              RepresentationType="Edge", Items=[edge])
        pdef = m.create_entity("IfcProductDefinitionShape", Representations=[top])
        cm = m.create_entity("IfcStructuralCurveMember", GlobalId=guid(),
                             Name="%s%d" % (b["grupo"][:3].upper(), k),
                             PredefinedType="RIGID_JOINED_MEMBER", Representation=pdef)
        for nd in (conn[b["no_i"]], conn[b["no_j"]]):
            m.create_entity("IfcRelConnectsStructuralMember", GlobalId=guid(),
                            RelatingStructuralMember=cm, RelatedStructuralConnection=nd)
        # propriedades da SECAO na barra (A, I, grupo) - o membro analitico carrega a
        # secao (Revit/analise leem). Pset custom.
        props = [
            m.create_entity("IfcPropertySingleValue", Name="Grupo",
                            NominalValue=m.create_entity("IfcLabel", b["grupo"])),
            m.create_entity("IfcPropertySingleValue", Name="Area_m2",
                            NominalValue=m.create_entity("IfcReal", float(b["A"]))),
            m.create_entity("IfcPropertySingleValue", Name="Inercia_m4",
                            NominalValue=m.create_entity("IfcReal", float(b["I"]))),
        ]
        esf = b.get("esforcos")                        # esforcos de calculo (envelope ELU)
        if esf:
            props += [
                m.create_entity("IfcPropertySingleValue", Name="Nsd_kN",
                                NominalValue=m.create_entity("IfcReal", float(esf["N_kN"]))),
                m.create_entity("IfcPropertySingleValue", Name="Vsd_kN",
                                NominalValue=m.create_entity("IfcReal", float(esf["V_kN"]))),
                m.create_entity("IfcPropertySingleValue", Name="Msd_kNm",
                                NominalValue=m.create_entity("IfcReal", float(esf["M_kNm"]))),
                m.create_entity("IfcPropertySingleValue", Name="Combo_governante",
                                NominalValue=m.create_entity("IfcLabel", str(esf.get("combo") or "-"))),
            ]
        pset = m.create_entity("IfcPropertySet", GlobalId=guid(),
                               Name="Pset_SecaoAnalitica", HasProperties=props)
        m.create_entity("IfcRelDefinesByProperties", GlobalId=guid(),
                        RelatedObjects=[cm], RelatingPropertyDefinition=pset)
        membros.append(cm)
    m.create_entity("IfcRelAssignsToGroup", GlobalId=guid(),
                    RelatedObjects=list(conn.values()) + membros, RelatingGroup=sam)
    m.write(path)
    return path


def emitir_ifc_analitico_do_spec(spec, path):
    """Emite o IFC4-Structural direto do calculo (spec). None se perfil nao-laminado."""
    import modelo_neutro as MN
    mod = MN.analitico_do_spec(spec)
    if not mod:
        return None
    return emitir_ifc_analitico(mod, path, nome=spec.get("slug") or "Galpao")


def _selftest():
    if not disponivel():
        print("ifc_emit _selftest SKIP (ifcopenshell ausente)")
        return
    import modelo_neutro as MN
    import tempfile, os
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    sec = {"col": {"nome": "HEA200", "d": 0.190, "bf": 0.200, "tw": 0.0065, "tf": 0.010},
           "raf": {"nome": "HEA180", "d": 0.171, "bf": 0.180, "tw": 0.006, "tf": 0.0095}}
    membros = MN.frame_primario(geo, sec)             # 18 col + 18 beam
    f = os.path.join(tempfile.mkdtemp(), "g.ifc")
    emitir_ifc(membros, f, nome="Amostra")
    assert os.path.getsize(f) > 0
    import ifcopenshell
    m = ifcopenshell.open(f)
    assert m.schema == "IFC4"
    assert len(m.by_type("IfcColumn")) == 18, len(m.by_type("IfcColumn"))
    assert len(m.by_type("IfcBeam")) == 18, len(m.by_type("IfcBeam"))
    # 2 perfis distintos (col + raf) reusados
    assert len(m.by_type("IfcIShapeProfileDef")) == 2
    # nomes/marcas preservados
    nomes = {e.Name for e in m.by_type("IfcColumn")}
    assert nomes == {"C1"}, nomes
    assert {e.Name for e in m.by_type("IfcBeam")} == {"V1"}
    print("ifc_emit _selftest PASSED (IFC4: 18 IfcColumn + 18 IfcBeam, sem FreeCAD)")


if __name__ == "__main__":
    _selftest()
