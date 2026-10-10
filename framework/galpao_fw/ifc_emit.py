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

import fronteiras as _FR  # contratos F01/F03/F04/F05 (dims mm, secao m, ancoragem)


def disponivel():
    """True se o ifcopenshell estiver instalado (emissor puro utilizavel)."""
    try:
        import ifcopenshell  # noqa: F401
        return True
    except Exception:
        return False


def _base_axes(p1, p2, ref_hint=None):
    """Eixos locais (x, y, z) da barra p1->p2: z = eixo; x ~ ref perpendicular
    a z; y = z x x (destro). Retorna (x, y, z, L) com L o comprimento.

    `ref_hint`: (opc) vetor de referencia (ex.: a normal do plano do
    portico, chave `plano_normal` do membro). Sem ele vale o default
    historico (global X, exceto barra paralela a X). Com ele, x sai do
    plano e y (o eixo de `d` no RECT) cai no plano - a guarda do G72
    contra a barra retangular girada 90 graus (G3). Retrocompativel:
    membro sem a chave segue identico.
    """
    dz = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
    L = math.sqrt(dz[0] ** 2 + dz[1] ** 2 + dz[2] ** 2)
    if L < 1e-9:
        return (1, 0, 0), (0, 1, 0), (0, 0, 1), 0.0
    z = (dz[0] / L, dz[1] / L, dz[2] / L)
    if ref_hint is not None:
        try:
            rn = math.sqrt(ref_hint[0] ** 2 + ref_hint[1] ** 2
                           + ref_hint[2] ** 2)
            ref = (ref_hint[0] / rn, ref_hint[1] / rn, ref_hint[2] / rn)
        except (TypeError, IndexError, ZeroDivisionError):
            ref = None
        if ref is not None:
            d0 = ref[0] * z[0] + ref[1] * z[1] + ref[2] * z[2]
            if abs(abs(d0) - 1.0) > 1e-6:
                ref_usar = ref
            else:
                ref_usar = None
        else:
            ref_usar = None
        if ref_usar is None:
            ref_usar = ((1.0, 0.0, 0.0) if abs(z[0]) < 0.9
                        else (0.0, 1.0, 0.0))
        ref = ref_usar
    else:
        ref = (1.0, 0.0, 0.0) if abs(z[0]) < 0.9 else (0.0, 1.0, 0.0)
    # x = ref perpendicular a z
    d = ref[0] * z[0] + ref[1] * z[1] + ref[2] * z[2]
    x = (ref[0] - d * z[0], ref[1] - d * z[1], ref[2] - d * z[2])
    nx = math.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
    x = (x[0] / nx, x[1] / nx, x[2] / nx)
    # y = z cross x
    y = (z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0])
    return x, y, z, L


def _matriz(p1, p2, ref_hint=None):
    import numpy as np
    x, y, z, L = _base_axes(p1, p2, ref_hint=ref_hint)
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
              "Pile": ("IfcPile", "BORED"),
              # --- eletrico (vertical do projeto eletrico) ---------------------
              "CableCarrier": ("IfcCableCarrierSegment", "CABLETRAYSEGMENT"),
              "Conduit": ("IfcCableCarrierSegment", "CONDUITSEGMENT"),
              "Cable": ("IfcCableSegment", "CABLESEGMENT"),
              "Earthing": ("IfcCableSegment", "CONDUCTORSEGMENT"),
              "Board": ("IfcElectricDistributionBoard", "DISTRIBUTIONBOARD"),
              "Transformer": ("IfcTransformer", "VOLTAGE"),
              "Luminaire": ("IfcLightFixture", "POINTSOURCE"),
              "Outlet": ("IfcOutlet", "POWEROUTLET"),
              # --- seguranca contra incendio (vertical de seg. incendio) --------
              "Sprinkler": ("IfcFireSuppressionTerminal", "SPRINKLER"),
              "Hydrant": ("IfcFireSuppressionTerminal", "FIREHYDRANT"),
              "HoseReel": ("IfcFireSuppressionTerminal", "HOSEREEL"),
              "SmokeSensor": ("IfcSensor", "SMOKESENSOR"),
              "ManualCall": ("IfcAlarm", "MANUALPULLBOX"),
              "EmergencyLight": ("IfcLightFixture", "SECURITYLIGHTING"),
              "Sign": ("IfcBuildingElementProxy", "ELEMENT"),
              "Extinguisher": ("IfcBuildingElementProxy", "ELEMENT"),
              "WaterTank": ("IfcTank", "STORAGE"),
              # --- climatizacao / HVAC (vertical de climatizacao) --------------
              "Duct": ("IfcDuctSegment", "RIGIDSEGMENT"),
              "AirHandler": ("IfcUnitaryEquipment", "AIRHANDLER"),
              # --- hidraulica predial (vertical de hidraulica) -----------------
              "Pipe": ("IfcPipeSegment", "RIGIDSEGMENT"),
              # --- edificacao (edificio multipavimento / casa residencial) ------
              "Slab": ("IfcSlab", "FLOOR"),
              "Roof": ("IfcSlab", "ROOF"),
              "Wall": ("IfcWall", "SOLIDWALL"),
              "Space": ("IfcSpace", "INTERNAL")}


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
    mat, L = _matriz(mb["p1"], mb["p2"], ref_hint=mb.get("plano_normal"))
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


def _ancorar(mat, mb, secao, esc):
    """Aplica a ANCORAGEM do membro: onde a linha p1->p2 fica na secao.

    'eixo' (padrao, e o que o galpao de aco sempre usou): a linha e' o eixo
    centroidal, e o perfil fica centrado nela. 'base': a linha e' a FACE
    INFERIOR da peca, que e' como uma viga apoiada no topo de um pilar e' mais
    natural de descrever - a peca sobe `d` a partir dali.

    Por que a chave existe: o build FreeCAD (build_concreto) sempre desenhou a
    viga a partir da face inferior e o emissor IFC sempre a centrou no eixo. As
    duas descricoes da MESMA viga de cobertura discordavam em d/2 - no galpao de
    concreto, meia viga (35 cm) enterrada dentro do pilar e o telhado 35 cm mais
    baixo no IFC do que no 3D. A ancoragem passa a ser DECLARADA pelo membro, em
    vez de implicita e diferente em cada emissor.

    So se aplica a barra HORIZONTAL (o deslocamento e' em Z global): numa coluna
    'base' nao tem significado, e o membro segue centrado.
    Contrato F05: default e' _FR.UNIDADE_ANCORAGEM_ENUM[0]=="eixo".
    """
    _ancoragem_padrao = _FR.UNIDADE_ANCORAGEM_ENUM[0]
    if mb.get("ancoragem", _ancoragem_padrao) != "base":
        return mat
    p1, p2 = mb["p1"], mb["p2"]
    if abs(p2[2] - p1[2]) > 1e-6:                     # barra inclinada/vertical
        return mat
    mat = mat.copy()
    mat[2, 3] += float(secao.get("d") or 0.0) * esc / 2.0
    return mat


def _espaco_ifc(m, body, sto, mb, run):
    """Emite um AMBIENTE (comodo) como IfcSpace: caixa `dims` (mm) no `centro` (mm).

    IfcSpace e' elemento da ESTRUTURA ESPACIAL, nao um produto contido nela: entra
    no pavimento por AGREGACAO (IfcRelAggregates), nao por
    IfcRelContainedInSpatialStructure. Trocar as duas e' o erro que faz o comodo
    aparecer no 3D mas nao na arvore de ambientes do visualizador.
    """
    import numpy as np
    B, L, h = mb["dims"]
    cx, cy, cz = mb["centro"]
    prof = m.create_entity("IfcRectangleProfileDef", ProfileType="AREA",
                           ProfileName=mb.get("perfil"), XDim=float(B), YDim=float(L))
    esp = run("root.create_entity", m, ifc_class="IfcSpace",
              predefined_type="INTERNAL", name=mb.get("marca") or mb.get("perfil"))
    rep = run("geometry.add_profile_representation", m, context=body, profile=prof,
              depth=float(h) / _MM_M)                 # depth em METROS (helper SI)
    run("geometry.assign_representation", m, product=esp, representation=rep)
    mat = np.eye(4)
    mat[:3, 3] = [cx, cy, cz - h / 2.0]               # origem no piso do ambiente
    run("geometry.edit_object_placement", m, product=esp, matrix=_mat_m(mat))
    run("aggregate.assign_object", m, relating_object=sto, products=[esp])
    return esp


def emitir_ifc(membros, path, nome="Galpao", secao_em_metros=True, pavimentos=None,
               eixos=None):
    """Escreve um IFC4 com os `membros` (do modelo_neutro) em `path`. Cada barra ->
    IfcColumn/IfcBeam com perfil I extrudado ao longo do eixo. Retorna o path (ou
    levanta se o ifcopenshell faltar). secao_em_metros: as dims da secao (d/bf/tw/
    tf) estao em m (catalogo) e sao convertidas p/ mm.

    pavimentos: (opc) lista [{'nome', 'elevacao_mm'}] - cria um IfcBuildingStorey
    POR PAVIMENTO e conteineriza cada membro no pavimento que ele declara em
    `mb['pavimento']`. Sem isso o edificio de 9 pavimentos abriria no visualizador
    como um unico 'Terreo' com tudo dentro, e a arvore do modelo (o que o
    projetista navega) nao teria relacao com o predio calculado. Omitido =
    comportamento historico do galpao: um unico pavimento 'Terreo'.

    eixos: (opc) {'x': [mm...], 'y': [mm...]} - grava um IfcGrid com um eixo
    numerado (1, 2, ...) em cada posicao de x e um eixo com letra (A, B, ...)
    em cada posicao de y, para as plantas sairem com os eixos nomeados. Omitido
    = sem grade (as outras tipologias seguem identicas)."""
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
    run("aggregate.assign_object", m, relating_object=proj, products=[site])
    run("aggregate.assign_object", m, relating_object=site, products=[bld])
    andares = {}
    if pavimentos:
        for pv in pavimentos:
            st = run("root.create_entity", m, ifc_class="IfcBuildingStorey",
                     name=pv["nome"])
            st.Elevation = float(pv.get("elevacao_mm", 0.0))   # unidade do modelo: mm
            andares[pv["nome"]] = st
        run("aggregate.assign_object", m, relating_object=bld,
            products=list(andares.values()))
        sto = andares[pavimentos[0]["nome"]]
    else:
        sto = run("root.create_entity", m, ifc_class="IfcBuildingStorey",
                  name="Terreo")
        run("aggregate.assign_object", m, relating_object=bld, products=[sto])

    def _sto(mb):
        """Pavimento do membro. Membro sem 'pavimento' (ou com um nome que nao foi
        declarado) cai no primeiro - nunca fica FORA da arvore espacial, que e' o
        que faz um elemento sumir do navegador do visualizador."""
        return andares.get(mb.get("pavimento"), sto)

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

    def _assoc_armadura(el, mb):
        """Anexa um Pset_Armadura ao elemento com o quantitativo de ferragem
        (As, nº de barras, phi, estribos...) quando o membro declara 'armadura'.
        Backward-compatible: sem a chave, nao faz nada (BIM de aco intacto). Assim o
        modelo IFC carrega a armadura calculada (Revit/visualizadores leem o Pset)."""
        arm = mb.get("armadura")
        if not arm:
            return
        _pset(el, "Pset_Armadura", arm)

    def _pset(el, nome, valores, pula_ausente=False):
        """Anexa um IfcPropertySet `nome` ao elemento. Com `pula_ausente`, valor
        None fica FORA do pset (dado ausente nao vira zero no modelo)."""
        props = []
        for k, v in valores.items():
            if v is None and pula_ausente:
                continue
            if isinstance(v, str):
                nv = m.create_entity("IfcLabel", v)
            elif isinstance(v, bool):
                nv = m.create_entity("IfcBoolean", v)
            else:
                nv = m.create_entity("IfcReal", float(v))
            props.append(m.create_entity("IfcPropertySingleValue", Name=str(k),
                                         NominalValue=nv))
        if pula_ausente and not props:
            return
        pset = m.create_entity("IfcPropertySet", GlobalId=_guid(), Name=nome,
                               HasProperties=props)
        m.create_entity("IfcRelDefinesByProperties", GlobalId=_guid(),
                        RelatedObjects=[el], RelatingPropertyDefinition=pset)

    def _assoc_calculo(el, mb):
        """Anexa os resultados do calculo que o membro declara em 'propriedades'
        ({nome_do_pset: {propriedade: valor}}). Backward-compatible: sem a chave,
        nao faz nada."""
        for nome_pset, valores in (mb.get("propriedades") or {}).items():
            _pset(el, nome_pset, valores, pula_ausente=True)

    for mb in membros:
        if "poligono" in mb:                          # painel (tapamento): poligono+vazios
            el = _painel_ifc(m, body, _sto(mb), mb, _guid)
            _assoc_calculo(el, mb)                    # chapa poligonal (ex.: misula)
            continue
        if "secao2" in mb:                            # barra de ALMA VARIÁVEL (tapered)
            el = _tapered_ifc(m, body, _sto(mb), mb, esc)
            _assoc_mat(el, mb)
            _assoc_calculo(el, mb)
            continue
        if "dims" in mb and "centro" in mb:           # CAIXA num ponto (fundação/chapa)
            import numpy as np
            B, L, h = mb["dims"]
            cx, cy, cz = mb["centro"]
            if mb["tipo"] == "Footing":                # sapata/bloco -> IfcFooting
                cls, pdt = "IfcFooting", "PAD_FOOTING"
            else:                                      # placa de base etc. -> IfcPlate
                cls, pdt = _IFC_CLASS.get(mb["tipo"], ("IfcPlate", "SHEET"))
            if cls == "IfcSpace":                      # ambiente: AGREGA no pavimento
                _espaco_ifc(m, body, _sto(mb), mb, run)
                continue
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
            run("spatial.assign_container", m, relating_structure=_sto(mb),
                products=[fo])
            _assoc_mat(fo, mb)
            _assoc_armadura(fo, mb)
            _assoc_calculo(fo, mb)
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
        mat, L = _matriz(mb["p1"], mb["p2"], ref_hint=mb.get("plano_normal"))
        mat = _ancorar(mat, mb, s, esc)
        rep = run("geometry.add_profile_representation", m, context=body,
                  profile=prof, depth=L / _MM_M)              # depth em METROS (helper SI)
        run("geometry.assign_representation", m, product=el, representation=rep)
        run("geometry.edit_object_placement", m, product=el, matrix=_mat_m(mat))
        run("spatial.assign_container", m, relating_structure=_sto(mb), products=[el])
        _assoc_mat(el, mb)
        _assoc_armadura(el, mb)
        _assoc_calculo(el, mb)
    if eixos and eixos.get("x") and eixos.get("y"):
        _grade_ifc(m, sto, eixos, run)
    m.write(path)
    return path


FOLGA_EIXO_MM = 2500.0     # quanto o eixo passa da ultima linha de pilares


def letra_do_eixo(i):
    """0 -> A, 25 -> Z, 26 -> AA (rotulo dos eixos longitudinais)."""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def eixos_dos_pilares(membros):
    """Posicoes (mm) das linhas de pilar do portico: {'x': [...], 'y': [...]}.
    Lidas dos proprios membros (marca C<n>), nao recalculadas da geometria."""
    import re
    bases = [mb["p1"] for mb in membros
             if mb.get("tipo") == "Column" and re.fullmatch(r"C\d+", mb.get("marca") or "")
             and "p1" in mb]
    return {"x": sorted({round(p[0], 3) for p in bases}),
            "y": sorted({round(p[1], 3) for p in bases})}


def _grade_ifc(m, sto, eixos, run):
    xs, ys = list(eixos["x"]), list(eixos["y"])
    x0, x1 = xs[0] - FOLGA_EIXO_MM, xs[-1] + FOLGA_EIXO_MM
    y0, y1 = ys[0] - FOLGA_EIXO_MM, ys[-1] + FOLGA_EIXO_MM

    def _eixo(rotulo, a, b):
        linha = m.create_entity("IfcPolyline", Points=[
            m.create_entity("IfcCartesianPoint", Coordinates=(float(a[0]), float(a[1]))),
            m.create_entity("IfcCartesianPoint", Coordinates=(float(b[0]), float(b[1])))])
        return m.create_entity("IfcGridAxis", AxisTag=rotulo, AxisCurve=linha, SameSense=True)

    grade = run("root.create_entity", m, ifc_class="IfcGrid", name="Eixos")
    grade.UAxes = [_eixo(str(i + 1), (x, y0), (x, y1)) for i, x in enumerate(xs)]
    grade.VAxes = [_eixo(letra_do_eixo(i), (x0, y), (x1, y)) for i, y in enumerate(ys)]
    run("geometry.edit_object_placement", m, product=grade)
    run("spatial.assign_container", m, relating_structure=sto, products=[grade])
    return grade


def membros_do_spec(spec):
    """Constroi a LISTA DE MEMBROS (modelo neutro do ifc_emit) da estrutura de aco
    direto do CALCULO (spec), SEM FreeCAD. Pórtico de perfil laminado (perfil_col_
    adotado/perfil_raf_adotado + catalogo `perfis`) OU de ALMA VARIÁVEL (tipo_portico=
    alma_variavel + tapered, I soldado de altura variável) -> ambos no caminho puro.
    Tesoura (treliça) / prismático sem perfil -> retorna None (segue via FreeCAD).
    Convencao (modelo_neutro): mm, X=comprimento[0..], Y=vao transversal[0..], Z=altura
    -> MESMO frame de eletrico/incendio (federavel sem transformacao)."""
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
                                joelho_lig=est.get("joelho_adotado"),
                                fechamento=spec.get("fechamento"),
                                aberturas=spec.get("aberturas"))
    _anotar_calculo(membros, spec)
    return membros


PSET_CALCULO = "Calc_VerificacaoEstrutural"
PSET_QUANTITATIVO = "Calc_Quantitativo"
DIAMETRO = "Ø"        # simbolo de diametro nas descricoes de ligacao
# barras SECUNDARIAS de aco cuja secao e' a real (a que o calculo verificou ou a
# barra macica desenhada): so essas sao pesadas pela secao. Calha, condutor e
# bocal sao pecas representativas (o condutor e' um cilindro cheio no modelo) e
# ficam fora: pesa-las pelo desenho daria um peso que nao existe.
BARRAS_PESADAS_PELA_SECAO = ("T1", "G1", "EB1", "CM1", "MO1", "MF1", "CV1", "TR1", "TC1")


def _area_de_aco(mb, est):
    """(area bruta da secao em m2, de onde ela veio) de uma barra secundaria,
    ou None quando o motor nao tem a area dessa secao. A area e' a MESMA que o
    calculo usa (catalogo de perfis, tabela UPE, cantoneira sem raio) ou a
    geometria exata da secao declarada (barra macica, Ue de cantos vivos);
    nada e' estimado pelo desenho."""
    import math

    import perfis
    sec = mb.get("secao") or {}
    marca, nome = mb.get("marca"), mb.get("perfil")
    if marca not in BARRAS_PESADAS_PELA_SECAO:
        return None
    if sec.get("forma") == "round":
        return math.pi * float(sec["D"]) ** 2 / 4.0, "barra redonda macica"
    if sec.get("forma") == "L":
        return (perfis.cantoneira(float(sec["bf"]) * 1000.0, float(sec["t"]) * 1000.0)["A"],
                "cantoneira sem raio de concordancia")
    if marca == "T1":
        td = est.get("terca_dims")
        if not td or len(td) < 4:
            return None
        # Ue bw x bf x D x t, medidas EXTERNAS: area = espessura x desenvolvimento
        # da linha media = t (bw + 2 bf + 2 D - 4 t), cantos vivos. O calculo da
        # terca toma as medidas externas como linha media (t x (bw + 2 bf + 2 D),
        # 2 a 3 % a mais): a favor da seguranca na carga, a mais no peso da lista.
        bw, bf, lip, t = (float(v) for v in td[:4])
        return (t * (bw + 2.0 * bf + 2.0 * lip - 4.0 * t) * 1.0e-6,
                "Ue de cantos vivos, espessura x desenvolvimento")
    if marca == "G1":
        import secundarios_nbr8800
        for perfil_u in secundarios_nbr8800.ESCADA_UPE:
            if perfil_u["nome"] == nome:
                return perfil_u["A"], "tabela UPE do calculo"
        return None
    if nome in perfis.PERFIS:
        return perfis.PERFIS[nome]["A"], "catalogo de perfis do calculo"
    return None


def _quantitativo(mb, est):
    """Pset do peso de uma peca que o romaneio do calculo nao traz: barra
    secundaria (area da secao x comprimento do modelo) e placa de base (volume
    bruto da chapa que o calculo adotou). Sem traspasse, furos nem perdas. None
    quando a peca nao e' pesada assim."""
    import math

    import romaneio
    if mb.get("perfil") == "PlacaBase" and "dims" in mb:
        bx, ly, t = (float(v) / 1000.0 for v in mb["dims"])
        return {"Peso_kg": round(bx * ly * t * romaneio.RHO_ACO, 2),
                "Origem": "volume bruto da chapa adotada no calculo, sem furos"}
    if "p1" not in mb or "p2" not in mb:
        return None
    area = _area_de_aco(mb, est)
    if area is None:
        return None
    compr = math.dist(mb["p1"], mb["p2"]) / 1000.0
    return {"Perfil": mb.get("perfil"), "Comprimento_m": round(compr, 3),
            "AreaDaSecao_cm2": round(area[0] * 1.0e4, 3),
            "Peso_kg": round(romaneio.massa_por_metro(area[0]) * compr, 2),
            "Origem": "area da secao (%s) x comprimento do modelo" % area[1]}


def _anotar_calculo(membros, spec):
    """Grava em cada peca do portico e da fundacao o MATERIAL declarado e o
    RESULTADO do calculo (perfil adotado, esforcos de calculo, utilizacao), para
    quem revisa o modelo ler a verificacao no proprio elemento. So copia o que o
    calculo deixou em spec.estrutura: chave ausente fica fora do pset, nunca
    vira valor inventado. Coluna = marca C<n>, viga do portico = marca V<n>
    (modelo_neutro); as demais barras (escoras, tercas, tirantes) nao tem
    esforco proprio no spec e seguem sem o pset da verificacao - levam so o do
    quantitativo (`_quantitativo`: peso pela secao), para a lista de material."""
    import re

    import acos
    import projeto_spec
    est = spec.get("estrutura", {}) or {}
    res = est.get("resultados") or {}

    def _decidido(valor):
        """Perfil deixado para o calculo escolher (marcador PENDENTE do spec) nao
        e' dado: fica fora do pset, como chave ausente."""
        return None if valor == projeto_spec.PENDENTE else valor
    veredito = (est.get("veredito_aco") or {}).get("atende")
    classe = acos.normaliza(est.get("aco") or acos.PADRAO)
    fy, fu = acos.propriedades(classe)
    aco = "Aco %s" % classe

    # romaneio do calculo (pecas primarias), por marca: comprimento e peso
    romaneio = {r.get("marca"): r for r in (est.get("romaneio") or []) if r.get("marca")}

    def _barra(esf, util, perfil_inicial, perfil_adotado, marca):
        esf = esf or {}
        rom = romaneio.get(marca) or {}
        # sem `.get` nas chaves do romaneio (a lente G75 conta `get` de chave de
        # calculo): peca sem linha no romaneio fica SEM a propriedade no pset,
        # nunca com um valor padrao
        compr = rom["comprimento_m"] if "comprimento_m" in rom else None
        peso = rom["peso_unit_kg"] if "peso_unit_kg" in rom else None
        return {PSET_CALCULO: {
            "Comprimento_m": compr, "Peso_kg": peso,
            "PerfilAdotado": perfil_adotado, "PerfilInicial": _decidido(perfil_inicial),
            "Aco": classe, "fy_MPa": fy / 1000.0, "fu_MPa": fu / 1000.0,
            "Nsd_kN": esf.get("N_kN"), "Vsd_kN": esf.get("V_kN"),
            "Msd_kNm": esf.get("M_kNm"), "ComboGovernante": esf.get("combo"),
            "Utilizacao": util, "VereditoAcoAtende": veredito}}

    col = _barra(est.get("esf_coluna"), res.get("Coluna"), est.get("perfil_col"),
                 est.get("perfil_col_adotado"), "C1")
    raf = _barra(est.get("esf_rafter"), res.get("Viga"), est.get("perfil_raf"),
                 est.get("perfil_raf_adotado"), "V1")
    fck = (spec.get("fundacao") or {}).get("fck")          # kPa
    sa = est.get("sapata_adotada") or {}

    def _mm(valor_m):
        return "%g" % round(float(valor_m) * 1000.0, 1)

    # LIGACOES: o que o calculo adotou vai, ja em texto de prancha, a placa de
    # base e a misula do joelho, para o detalhe ler do proprio elemento. So
    # monta a descricao quando o calculo deixou TODAS as medidas dela.
    placa_base = joelho = None
    ba = est.get("base_adotada") or {}
    if all(k in ba for k in ("B", "L", "t")):
        placa_base = {"Descricao": "%s x %s x %s mm" % (_mm(ba["B"]), _mm(ba["L"]), _mm(ba["t"])),
                      "Utilizacao": res.get("Base")}
        if "n" in ba and "db" in ba:
            placa_base["Chumbadores"] = "%d %s%s" % (int(ba["n"]), DIAMETRO, _mm(ba["db"]))
    # gusset do contraventamento: espessura e perna da solda de filete que o
    # calculo adotou (a mesma que o executivo do FreeCAD poe no simbolo de solda)
    gusset = None
    ga = est.get("gusset_adotado") or {}
    if "t_mm" in ga:
        gusset = {"Descricao": "chapa %g mm" % float(ga["t_mm"]),
                  "SoldaFiletePerna_mm": ga["perna_solda_mm"] if "perna_solda_mm" in ga else None,
                  "Utilizacao": res.get("Gusset")}
    ja = est.get("joelho_adotado") or {}
    if all(k in ja for k in ("n", "db", "t")):
        joelho = {"Descricao": "%d parafusos %s%s, chapa %s mm"
                               % (int(ja["n"]), DIAMETRO, _mm(ja["db"]), _mm(ja["t"])),
                  "Utilizacao": res.get("Joelho")}
    for mb in membros:
        marca = mb.get("marca") or ""
        if mb.get("tipo") == "Column" and re.fullmatch(r"C\d+", marca):
            mb.setdefault("material", aco)
            mb.setdefault("propriedades", col)
        elif mb.get("tipo") == "Beam" and re.fullmatch(r"V\d+", marca):
            mb.setdefault("material", aco)
            mb.setdefault("propriedades", raf)
        elif mb.get("perfil") == "PlacaBase" and placa_base:
            mb.setdefault("propriedades", {PSET_CALCULO: placa_base})
        elif mb.get("perfil") == "Misula" and joelho:
            mb.setdefault("propriedades", {PSET_CALCULO: joelho})
        elif mb.get("perfil") == "GussetContrav" and gusset:
            mb.setdefault("propriedades", {PSET_CALCULO: gusset})
        elif mb.get("tipo") == "Footing":
            if fck:
                mb.setdefault("material", "Concreto C%d" % round(fck / 1000.0))
            mb.setdefault("propriedades", {PSET_CALCULO: {
                "Tipo": sa.get("tipo"), "Utilizacao": res.get("Sapata"),
                "fck_MPa": (fck / 1000.0) if fck else None}})
        quant = _quantitativo(mb, est)
        if quant:
            # dicionario proprio da peca: o das colunas e o das vigas sao partilhados
            mb["propriedades"] = dict(mb.get("propriedades") or {})
            mb["propriedades"][PSET_QUANTITATIVO] = quant


def emitir_ifc_do_spec(spec, path):
    """Emite o IFC4 da estrutura de aco direto do spec, SEM FreeCAD (thin wrapper de
    membros_do_spec + emitir_ifc). Retorna o path, ou None quando o caminho puro nao
    cobre a estrutura (tesoura/prismático sem perfil -> segue via FreeCAD)."""
    membros = membros_do_spec(spec)
    if membros is None:
        return None
    return emitir_ifc(membros, path, nome=spec.get("slug") or "Galpao",
                      eixos=eixos_dos_pilares(membros))


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
    # Axis e' obrigatorio no IFC4 (direcao que fixa o eixo z local da barra): o
    # portico esta no plano XY do modelo, entao z local = fora do plano.
    eixo_z = m.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
    for k, b in enumerate(modelo["barras"], 1):
        vi, vj = vert[b["no_i"]], vert[b["no_j"]]
        edge = m.create_entity("IfcEdge", EdgeStart=vi, EdgeEnd=vj)
        top = m.create_entity("IfcTopologyRepresentation", ContextOfItems=ctx,
                              RepresentationIdentifier="Reference",
                              RepresentationType="Edge", Items=[edge])
        pdef = m.create_entity("IfcProductDefinitionShape", Representations=[top])
        cm = m.create_entity("IfcStructuralCurveMember", GlobalId=guid(),
                             Name="%s%d" % (b["grupo"][:3].upper(), k),
                             PredefinedType="RIGID_JOINED_MEMBER", Representation=pdef,
                             Axis=eixo_z)
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
