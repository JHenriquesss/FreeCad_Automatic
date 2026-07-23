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


# As coords do modelo_neutro estão em MM, mas o modelo IFC usa unidade MILÍMETRO e os
# helpers do ifcopenshell (edit_object_placement / add_profile_representation) esperam
# o INPUT em METROS (SI) e reconvertem p/ a unidade do modelo (x1000). Sem converter, um
# pilar de 6 m saía com 6.000.000 mm (1000x). _MM_M leva a TRANSLAÇÃO da matriz (e o
# comprimento de extrusão) de mm p/ m antes de passar a esses helpers.
_MM_M = 1000.0


def _mat_m(mat):
    """Matriz 4x4 (mm) -> cópia com a TRANSLAÇÃO em metros (rotação intacta), p/ o
    edit_object_placement do ifcopenshell (que espera SI e reconverte p/ a unidade)."""
    import numpy as np
    out = np.array(mat, dtype=float).copy()
    out[:3, 3] = out[:3, 3] / _MM_M
    return out


_IFC_CLASS = {"Column": ("IfcColumn", "COLUMN"), "Beam": ("IfcBeam", "BEAM"),
              "Member": ("IfcMember", "MEMBER"), "Plate": ("IfcPlate", "SHEET"),
              "Covering": ("IfcCovering", "ROOFING"),
              "Cladding": ("IfcCovering", "CLADDING"),
              "Fastener": ("IfcMechanicalFastener", "ANCHORBOLT"),
              "Pile": ("IfcPile", "BORED")}


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm3(a):
    n = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-9 else (1.0, 0.0, 0.0)


def _plano_local(corners):
    """Eixos locais (u, v, n) do plano do poligono: n = normal (1a aresta x 1a nao
    colinear), u = 1a aresta normalizada, v = n x u. origem = corners[0]."""
    o = corners[0]
    e1 = _norm3(_sub(corners[1], o))
    n = None
    for k in range(2, len(corners)):
        c = _cross(e1, _sub(corners[k], o))
        if math.sqrt(c[0] ** 2 + c[1] ** 2 + c[2] ** 2) > 1e-6:
            n = _norm3(c)
            break
    if n is None:
        n = (0.0, 1.0, 0.0)
    u = e1
    v = _norm3(_cross(n, u))
    return o, u, v, n


def _painel_ifc(m, body, sto, mb, guid):
    """Emite um PAINEL poligonal (tapamento/pele) como IfcCovering com o perfil
    (poligono + vazios das aberturas) extrudado pela espessura ao longo da normal.
    mb: {poligono (3D mm), esp (mm), aberturas [((x0,x1),(y0,y1),(z0,z1)), ...], tipo}."""
    import numpy as np
    corners = mb["poligono"]
    o, u, v, n = _plano_local(corners)

    def _uv(p):
        d = _sub(p, o)
        return (_dot(d, u), _dot(d, v))

    def _polyline(pts2d):
        cpts = [m.create_entity("IfcCartesianPoint", Coordinates=(float(a), float(b)))
                for (a, b) in pts2d]
        cpts.append(cpts[0])                          # fecha o contorno
        return m.create_entity("IfcPolyline", Points=cpts)

    outer = _polyline([_uv(c) for c in corners])
    voids = []
    for (xr, yr, zr) in mb.get("aberturas", []):
        # projeta os 8 cantos da caixa no plano (u,v) e toma o retangulo min/max
        us, vs = [], []
        for x in xr:
            for y in yr:
                for z in zr:
                    a, b = _uv((x, y, z))
                    us.append(a); vs.append(b)
        u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
        voids.append(_polyline([(u0, v0), (u1, v0), (u1, v1), (u0, v1)]))
    if voids:
        prof = m.create_entity("IfcArbitraryProfileDefWithVoids", ProfileType="AREA",
                               ProfileName=mb.get("perfil"), OuterCurve=outer,
                               InnerCurves=voids)
    else:
        prof = m.create_entity("IfcArbitraryClosedProfileDef", ProfileType="AREA",
                               ProfileName=mb.get("perfil"), OuterCurve=outer)
    pos = m.create_entity(
        "IfcAxis2Placement3D",
        Location=m.create_entity("IfcCartesianPoint", Coordinates=tuple(float(c) for c in o)),
        Axis=m.create_entity("IfcDirection", DirectionRatios=tuple(float(c) for c in n)),
        RefDirection=m.create_entity("IfcDirection", DirectionRatios=tuple(float(c) for c in u)))
    solid = m.create_entity("IfcExtrudedAreaSolid", SweptArea=prof, Position=pos,
                            ExtrudedDirection=m.create_entity("IfcDirection",
                                                              DirectionRatios=(0.0, 0.0, 1.0)),
                            Depth=float(mb["esp"]))
    shp = m.create_entity("IfcShapeRepresentation", ContextOfItems=body,
                          RepresentationIdentifier="Body", RepresentationType="SweptSolid",
                          Items=[solid])
    cls, pdt = _IFC_CLASS.get(mb["tipo"], ("IfcCovering", "CLADDING"))
    from ifcopenshell.api import run
    el = run("root.create_entity", m, ifc_class=cls, predefined_type=pdt,
             name=mb.get("marca") or mb["perfil"])
    el.Representation = m.create_entity("IfcProductDefinitionShape", Representations=[shp])
    run("geometry.edit_object_placement", m, product=el, matrix=np.eye(4))
    run("spatial.assign_container", m, relating_structure=sto, products=[el])
    return el


def _perfil_ifc(m, nome, s, esc):
    """Cria o perfil IFC da secao. Perfil formado a frio (terca: forma 'C' ou tem
    'lip') -> IfcCShapeProfileDef (canaleta enrijecida). Laminado -> IfcIShapeProfileDef.
    Dims em m * esc (mm). `d`/`h` = altura, `bf` = largura, `tw`/`t` = espessura."""
    forma = str(s.get("forma", "")).upper()
    if forma == "ROUND":                              # barra redonda (tirante/contrav)
        return m.create_entity("IfcCircleProfileDef", ProfileType="AREA",
                               ProfileName=nome, Radius=float(s.get("D") or 0.0) * esc / 2.0)
    if forma == "RECT":                               # laje/painel (telha): bf x d (t)
        return m.create_entity("IfcRectangleProfileDef", ProfileType="AREA",
                               ProfileName=nome, XDim=float(s.get("bf") or 0.0) * esc,
                               YDim=float(s.get("d") or 0.0) * esc)
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
    if forma == "L":                                  # cantoneira (mao-francesa)
        return m.create_entity("IfcLShapeProfileDef", ProfileType="AREA",
                               ProfileName=nome, Depth=h, Width=bf,
                               Thickness=float(s.get("t") or 0.0) * esc)
    return m.create_entity("IfcIShapeProfileDef", ProfileType="AREA", ProfileName=nome,
                           OverallWidth=bf, OverallDepth=h,
                           WebThickness=float(s.get("tw") or 0.0) * esc,
                           FlangeThickness=float(s.get("tf") or 0.0) * esc)


def _tapered_ifc(m, body, sto, mb, esc):
    """Emite uma barra de ALMA VARIÁVEL (tapered): perfil I que interpola da seção de
    início (`secao`) à de fim (`secao2`) ao longo do eixo -> IfcExtrudedAreaSolidTapered
    (loft entre dois IfcIShapeProfileDef de mesma mesa, alturas diferentes). Mesma
    orientação/posicionamento do caminho prismático (matriz do eixo)."""
    import numpy as np
    from ifcopenshell.api import run
    p_ini = _perfil_ifc(m, (mb.get("perfil") or "") + "_i", mb["secao"], esc)
    p_fim = _perfil_ifc(m, (mb.get("perfil") or "") + "_j", mb["secao2"], esc)
    mat, L = _matriz(mb["p1"], mb["p2"])
    pos = m.create_entity(
        "IfcAxis2Placement3D",
        Location=m.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)))
    solid = m.create_entity(
        "IfcExtrudedAreaSolidTapered", SweptArea=p_ini, Position=pos, Depth=float(L),
        ExtrudedDirection=m.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
        EndSweptArea=p_fim)
    shp = m.create_entity("IfcShapeRepresentation", ContextOfItems=body,
                          RepresentationIdentifier="Body", RepresentationType="SweptSolid",
                          Items=[solid])
    cls, pdt = _IFC_CLASS.get(mb["tipo"], ("IfcMember", "MEMBER"))
    el = run("root.create_entity", m, ifc_class=cls, predefined_type=pdt,
             name=mb.get("marca") or mb.get("perfil"))
    el.Representation = m.create_entity("IfcProductDefinitionShape", Representations=[shp])
    run("geometry.edit_object_placement", m, product=el, matrix=_mat_m(mat))
    run("spatial.assign_container", m, relating_structure=sto, products=[el])
    return el


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

    from ifcopenshell.guid import new as _guid
    perfis_ifc = {}                                   # cache de perfil IFC por nome
    mats_ifc = {}                                     # cache de IfcMaterial por nome

    def _assoc_mat(el, mb):
        """Associa um IfcMaterial ao elemento se o membro declarar 'material'
        (ex.: 'Concreto C30', 'Aco ASTM A572'). Backward-compatible: sem a chave,
        nao faz nada (o BIM de aco existente segue identico)."""
        nome_mat = mb.get("material")
        if not nome_mat:
            return
        mat = mats_ifc.get(nome_mat)
        if mat is None:
            mat = m.create_entity("IfcMaterial", Name=nome_mat)
            mats_ifc[nome_mat] = mat
        m.create_entity("IfcRelAssociatesMaterial", GlobalId=_guid(),
                        RelatedObjects=[el], RelatingMaterial=mat)

    for mb in membros:
        if "poligono" in mb:                          # painel (tapamento): poligono+vazios
            _painel_ifc(m, body, sto, mb, _guid)
            continue
        if "secao2" in mb:                            # barra de ALMA VARIÁVEL (tapered)
            _tapered_ifc(m, body, sto, mb, esc)
            continue
        if "dims" in mb and "centro" in mb:           # CAIXA num ponto (fundação/chapa)
            import numpy as np
            B, L, h = mb["dims"]
            cx, cy, cz = mb["centro"]
            if mb["tipo"] == "Footing":                # sapata/bloco -> IfcFooting
                cls, pdt = "IfcFooting", "PAD_FOOTING"
            else:                                      # placa de base etc. -> IfcPlate
                cls, pdt = _IFC_CLASS.get(mb["tipo"], ("IfcPlate", "SHEET"))
            prof = m.create_entity("IfcRectangleProfileDef", ProfileType="AREA",
                                   ProfileName=mb["perfil"], XDim=float(B), YDim=float(L))
            fo = run("root.create_entity", m, ifc_class=cls, predefined_type=pdt,
                     name=mb.get("marca") or mb["perfil"])
            rep = run("geometry.add_profile_representation", m, context=body,
                      profile=prof, depth=float(h) / _MM_M)   # depth em METROS (helper SI)
            run("geometry.assign_representation", m, product=fo, representation=rep)
            mat = np.eye(4)
            mat[:3, 3] = [cx, cy, cz - h / 2.0]        # origem no fundo da caixa (mm)
            run("geometry.edit_object_placement", m, product=fo, matrix=_mat_m(mat))
            run("spatial.assign_container", m, relating_structure=sto, products=[fo])
            _assoc_mat(fo, mb)
            continue
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
                  profile=prof, depth=L / _MM_M)              # depth em METROS (helper SI)
        run("geometry.assign_representation", m, product=el, representation=rep)
        run("geometry.edit_object_placement", m, product=el, matrix=_mat_m(mat))
        run("spatial.assign_container", m, relating_structure=sto, products=[el])
        _assoc_mat(el, mb)
    m.write(path)
    return path


def emitir_ifc_do_spec(spec, path):
    """Emite o IFC4 da estrutura direto do CALCULO (spec), SEM FreeCAD. Pórtico de
    perfil laminado (perfil_col_adotado/perfil_raf_adotado + catalogo `perfis`) OU de
    ALMA VARIÁVEL (tipo_portico=alma_variavel + tapered, I soldado de altura variável)
    -> ambos no caminho puro. Tesoura (treliça) -> retorna None (segue via FreeCAD).
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

    # pórtico de alma variável (tapered): dims (m) do spec.estrutura.tapered
    tapered = (est.get("tapered") if est.get("tipo_portico") == "alma_variavel"
               and isinstance(est.get("tapered"), dict) else None)
    col = _sec(est.get("perfil_col_adotado"))
    raf = _sec(est.get("perfil_raf_adotado"))
    esc = _sec(est.get("perfil_escora"))              # escoras/cumeeiras/montantes
    # gussets do contravento: espessura do gusset_adotado (mm) + altura da escora
    gusset_c = None
    gt = (est.get("gusset_adotado") or {}).get("t_mm")
    if gt:
        gusset_c = {"t": gt, "esc_d": (esc or {}).get("d", 0.152)}
    # mísula (haunch) do joelho: seção do rafter no beiral (tapered = joelho). Só em
    # pórtico de 2 águas (tesoura/shed não têm joelho de momento).
    misula = None
    if est.get("tipo_portico") not in ("tesoura",):
        m_d = (tapered.get("h_joelho") if tapered else (raf or {}).get("d"))
        m_tw = (tapered.get("tw") if tapered else (raf or {}).get("tw"))
        if m_d and m_tw:
            misula = {"raf_d": m_d, "raf_tw": m_tw}
    if not tapered and (not col or not raf):
        return None                                   # tesoura/prismático sem perfil -> FreeCAD
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
    # fundacao rasa (sapata/bloco): caixa B x L x h por base, do sapata_adotada
    fund_sec = None
    sa = est.get("sapata_adotada")
    if sa and all(k in sa for k in ("B", "L", "h")):
        fund_sec = {"B": sa["B"], "L": sa["L"], "h": sa["h"], "tipo": sa.get("tipo")}
    # fundação PROFUNDA (estaca + bloco + pedestal), do estaca_adotada (m -> mm).
    # Requer sondagem (Ask-Do-Not-Invent) -> só emite quando o cálculo forneceu.
    fund_prof = None
    ea = est.get("estaca_adotada")
    if ea and ea.get("D") and ea.get("L"):
        bo = est.get("bloco_adotado") or {}
        fund_prof = {"estaca": {"D": ea["D"] * 1000.0, "L": ea["L"] * 1000.0,
                                "n": ea.get("n", 1),
                                "espacamento": (ea.get("espacamento") or 3.0 * ea["D"]) * 1000.0},
                     "bloco_h": (bo.get("h") or 0.0) * 1000.0 or None,
                     "col_d": (col or {}).get("d", 0.3),
                     "col_bf": (col or {}).get("bf", 0.3),
                     "base_t": (est.get("base_adotada") or {}).get("t", 0.1)}
    # ponte rolante: viga de rolamento + consoles. Do spec.ponte (Hvr, excentricidade,
    # perfil_viga [d,bf,tw,tf] mm). Console = perfil_escora (HEA160), como no build.
    ponte = None
    pm = spec.get("ponte")
    if pm and pm.get("Hvr") and pm.get("excentricidade"):
        pv = pm.get("perfil_viga") or [500.0, 250.0, 8.0, 16.0]
        vr = {"nome": "VR", "forma": "I", "d": pv[0] / 1000.0, "bf": pv[1] / 1000.0,
              "tw": pv[2] / 1000.0, "tf": pv[3] / 1000.0}
        cons = esc or {"nome": "HEA160", "d": 0.152, "bf": 0.16, "tw": 0.006, "tf": 0.009}
        ponte = {"hvr": pm["Hvr"], "ecc": pm["excentricidade"], "vr_sec": vr,
                 "console_sec": cons}
    # placa de base (chapa B x L x t por coluna), do base_adotada (m)
    base_sec = None
    base_full = None
    ba = est.get("base_adotada")
    if ba and all(k in ba for k in ("B", "L", "t")):
        base_sec = {"B": ba["B"], "L": ba["L"], "t": ba["t"]}
        if all(k in ba for k in ("db", "n")):         # conectores (chumbador/porca/arruela)
            base_full = {"B": ba["B"], "L": ba["L"], "t": ba["t"],
                         "db": ba["db"], "n": ba["n"]}
    # drenagem: calha (B/H) + condutor (mm) do calha_adotada; col_d/girt_h/base_L p/
    # posicionar. raf tapered = joelho p/ col_d beiral (aprox.).
    dren = None
    ca = est.get("calha_adotada")
    if ca and ca.get("B_mm") and ca.get("H_mm") and ca.get("condutor_mm"):
        cold = (tapered.get("h_joelho") if tapered else (col or {}).get("d"))
        girth = (ld[0] / 1000.0) if (ld and len(ld) >= 1) else 0.14
        basel = ba["L"] if (ba and ba.get("L")) else 0.6
        if cold:
            dren = {"calha_bh": (ca["B_mm"], ca["H_mm"]), "condutor_d": ca["condutor_mm"],
                    "col_d": cold, "girt_h": girth, "base_L": basel}
    # maos-francesas (trava da mesa inferior): mf_stride (calc) + secao do rafter +
    # altura da terca + cantoneira do eng. (mao_francesa b_mm/t_mm). raf tapered = joelho.
    mao_franc = None
    mfstr = est.get("mf_stride")
    if mfstr and n_terca:
        raf_d = (tapered.get("h_joelho") if tapered else (raf or {}).get("d"))
        raf_bf = (tapered.get("bf") if tapered else (raf or {}).get("bf"))
        ue_h = (td[0] / 1000.0) if (td and len(td) >= 1) else None
        mfd = est.get("mao_francesa") or {}
        mf_sec = ((mfd["b_mm"], mfd["t_mm"])
                  if mfd.get("b_mm") and mfd.get("t_mm") else None)
        if raf_d and raf_bf and ue_h:
            mao_franc = {"mf_stride": mfstr, "raf_d": raf_d, "raf_bf": raf_bf,
                         "ue_h": ue_h, "mf_sec": mf_sec}
    # col_d (recuo dos girts/altura no joelho): perfil laminado -> d; tapered -> h_joelho
    col_d = tapered.get("h_joelho") if tapered else col.get("d")
    secoes = None if tapered else {"col": col, "raf": raf}
    membros = MN.frame_completo(geo, secoes, tapered=tapered,
                                n_terca=n_terca, terca_sec=terca_sec,
                                girt_sec=girt_sec, col_d=col_d,
                                n_tirante_parede=est.get("n_tirante_parede"),
                                d_tirante_mm=16.0, contrav=True, d_contrav_mm=20.0,
                                fund_sec=fund_sec, base_sec=base_sec,
                                nervura_base=bool(base_sec), clipes=True, telha=True,
                                mao_francesa=mao_franc, esc_sec=esc,
                                montante_ab=spec.get("aberturas"), tirante_cob=True,
                                d_tirante_cob_mm=16.0, base_full=base_full,
                                drenagem_cfg=dren, gusset_contrav=gusset_c,
                                misula=misula, fund_profunda=fund_prof, ponte=ponte,
                                fechamento=spec.get("fechamento"),
                                aberturas=spec.get("aberturas"))
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
        sv = b.get("secao_var")                        # barra de ALMA VARIÁVEL (tapered)
        if sv:
            props += [
                m.create_entity("IfcPropertySingleValue", Name="Variavel",
                                NominalValue=m.create_entity("IfcBoolean", True)),
                m.create_entity("IfcPropertySingleValue", Name="Altura_i_m",
                                NominalValue=m.create_entity("IfcReal", float(sv["d_i"]))),
                m.create_entity("IfcPropertySingleValue", Name="Altura_j_m",
                                NominalValue=m.create_entity("IfcReal", float(sv["d_j"]))),
                m.create_entity("IfcPropertySingleValue", Name="Inercia_i_m4",
                                NominalValue=m.create_entity("IfcReal", float(sv["I_i"]))),
                m.create_entity("IfcPropertySingleValue", Name="Inercia_j_m4",
                                NominalValue=m.create_entity("IfcReal", float(sv["I_j"]))),
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
