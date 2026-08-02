"""Build 3D do PROJETO ELETRICO do galpao (FreeCAD), a partir do modelo NEUTRO ja
calculado (galpao_eletrico.membros_bim). Espelha o contrato do build_concreto.py:
expoe reset()/configurar()/run() e e ENVIADO como FONTE ao FreeCAD (bridge XMLRPC
9875 ou freecadcmd headless) pelo rodar_projeto.

Como no concreto (memoria cache-modulo-irmao-freecad): recebe a geometria como
PAYLOAD DE DADOS (`membros`, plain list de dicts) - NAO importa modulos irmaos, entao
a armadilha do "freecad.exe roda a versao ANTIGA do modulo irmao" nao existe aqui.

Geometria = 2 solidos: CAIXA (Part::Box) p/ quadros/trafo e eletrocalha (bandeja);
CILINDRO (Part::Cylinder) p/ os condutores redondos (aterramento, hastes, captacao
SPDA, descidas). Eixos: X=comprimento, Y=vao, Z=altura; COORDENADAS em mm. Convencao
de secao: CAIXA-membro dims em MM (ja vem assim do membros_bim eletrico); BARRA secao
em m (bf/d/D) - convertida p/ mm aqui.

`import FreeCAD` e LOCAL (dentro de run/_monta_doc/_export): assim `caixas()` e
`_takeoff()` sao testaveis em pytest puro, sem FreeCAD (licao do 3D: a green bar de
calculo nao cobre o layout; a orientacao/posicao e travada em caixas() no CI, e o
build real e conferido por um teste `build` headless com freecadcmd).
"""

import math
import os

# ---- estado (restaurado por reset(); povoado por configurar()) --------------
MEMBROS = None
EXPORT_DIR = "exports"
DOC_NAME = "galpao_eletrico"

# nome do membro neutro -> tipo IFC (mapa LOCAL; casa com ifc_emit._IFC_CLASS)
_IFC_TIPO = {"Board": "IfcElectricDistributionBoard", "Transformer": "IfcTransformer",
             "CableCarrier": "IfcCableCarrierSegment", "Cable": "IfcCableSegment",
             "Earthing": "IfcCableSegment"}


def reset():
    """Zera o estado mutavel (evita vazamento entre projetos na MESMA sessao do
    FreeCAD - a armadilha do _CFG global). Chamado no inicio de run()."""
    global MEMBROS, EXPORT_DIR, DOC_NAME
    MEMBROS = None
    EXPORT_DIR = "exports"
    DOC_NAME = "galpao_eletrico"


def configurar(membros=None, export_dir=None, doc_name=None):
    """Recebe o payload do modelo neutro (galpao_eletrico.membros_bim)."""
    global MEMBROS, EXPORT_DIR, DOC_NAME
    if membros is not None:
        MEMBROS = membros
    if export_dir is not None:
        EXPORT_DIR = export_dir
    if doc_name is not None:
        DOC_NAME = doc_name


def _eixo(p1, p2):
    """Eixo dominante (0=X,1=Y,2=Z), comprimento (mm) e vetor de um membro barra."""
    d = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
    L = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
    ax = max(range(3), key=lambda i: abs(d[i]))
    return ax, L, d


def caixas(membros):
    """PURO (sem FreeCAD): converte os membros neutros eletricos em especificacoes
    de solido para Part. Retorna lista de dicts, um por peca:
      - CAIXA:    {solido:'box', name, tipo, ifc, origem(mm), dims(mm), vol_m3, material}
      - CILINDRO: {solido:'cyl', name, tipo, ifc, p1(mm), p2(mm), raio_mm, L_mm, vol_m3, material}
    Regras de orientacao (o que o teste trava):
      - Board/Transformer: dims(mm)+centro(mm) -> box centrado no centro.
      - CableCarrier (eletrocalha, secao RECT bf x d em m): box axis-aligned ao longo
        do eixo dominante da barra; secao bf/d nas duas direcoes perpendiculares.
      - Cable/Earthing (condutor, secao ROUND D em m): cilindro de raio D/2 ao longo
        do eixo p1->p2.
    """
    out = []
    for mb in membros:
        tipo = mb["tipo"]
        ifc = _IFC_TIPO.get(tipo, "IfcBuildingElementProxy")
        nome = mb.get("marca") or mb.get("perfil") or tipo
        mat = mb.get("material", "Aco")
        if "dims" in mb and "centro" in mb:                # CAIXA (quadro/trafo): dims em MM
            dx, dy, dz = [float(v) for v in mb["dims"]]
            cx, cy, cz = mb["centro"]
            origem = (cx - dx / 2.0, cy - dy / 2.0, cz - dz / 2.0)
            out.append({"solido": "box", "name": nome, "tipo": tipo, "ifc": ifc,
                        "origem": origem, "dims": (dx, dy, dz),
                        "vol_m3": (dx * dy * dz) / 1e9, "material": mat})
            continue
        p1, p2 = mb["p1"], mb["p2"]
        s = mb["secao"]
        forma = str(s.get("forma", "")).upper()
        ax, L, _ = _eixo(p1, p2)
        if forma == "ROUND":                               # CONDUTOR -> cilindro
            raio = s["D"] * 1000.0 / 2.0                    # m -> mm, raio
            vol = math.pi * raio ** 2 * L / 1e9
            out.append({"solido": "cyl", "name": nome, "tipo": tipo, "ifc": ifc,
                        "p1": tuple(float(v) for v in p1), "p2": tuple(float(v) for v in p2),
                        "raio_mm": raio, "L_mm": L, "vol_m3": vol, "material": mat})
        else:                                              # RECT -> box ao longo do eixo
            bf = s["bf"] * 1000.0                           # m -> mm
            d = s["d"] * 1000.0
            perp = [i for i in range(3) if i != ax]         # 2 eixos perpendiculares
            dims = [0.0, 0.0, 0.0]
            dims[ax] = L
            dims[perp[0]] = bf
            dims[perp[1]] = d
            origem = [0.0, 0.0, 0.0]
            origem[ax] = min(p1[ax], p2[ax])
            origem[perp[0]] = p1[perp[0]] - bf / 2.0
            origem[perp[1]] = p1[perp[1]] - d / 2.0
            out.append({"solido": "box", "name": nome, "tipo": tipo, "ifc": ifc,
                        "origem": tuple(origem), "dims": tuple(dims),
                        "vol_m3": (dims[0] * dims[1] * dims[2]) / 1e9, "material": mat})
    return out


def _takeoff(cxs):
    """Quantitativo por tipo de peca: n, comprimento (m, p/ barras/condutores) e
    volume (m3). Puro (sem FreeCAD)."""
    por = {}
    for c in cxs:
        v = por.setdefault(c["tipo"], {"n": 0, "comp_m": 0.0, "vol_m3": 0.0})
        v["n"] += 1
        v["vol_m3"] += c["vol_m3"]
        if c["solido"] == "cyl":
            v["comp_m"] += c["L_mm"] / 1000.0
        else:
            v["comp_m"] += max(c["dims"]) / 1000.0
    for v in por.values():
        v["comp_m"] = round(v["comp_m"], 2)
        v["vol_m3"] = round(v["vol_m3"], 4)
    return {"por_tipo": por,
            "comp_condutor_m": round(sum(c["L_mm"] / 1000.0 for c in cxs
                                         if c["solido"] == "cyl"), 2)}


# ---------------------------------------------------------------------------
# Dali para baixo: precisa do FreeCAD. Imports LOCAIS para manter caixas()/
# _takeoff() testaveis em pytest puro.
# ---------------------------------------------------------------------------
def _monta_doc(cxs):
    """Cria o documento FreeCAD: Part::Box p/ 'box' e Part::Cylinder (com direcao)
    p/ 'cyl', tipado com IfcType. Retorna o doc."""
    import FreeCAD as App
    import Part
    name = DOC_NAME
    for dd in list(App.listDocuments().values()):
        if dd.Name == name:
            App.closeDocument(name)
            break
    doc = App.newDocument(name)
    for c in cxs:
        if c["solido"] == "box":
            shape = Part.makeBox(*c["dims"])
            shape.translate(App.Vector(*c["origem"]))
        else:                                              # cilindro ao longo de p1->p2
            p1, p2 = c["p1"], c["p2"]
            d = App.Vector(p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
            shape = Part.makeCylinder(c["raio_mm"], c["L_mm"], App.Vector(*p1),
                                      d.normalize())
        ob = doc.addObject("Part::Feature", _fc_name(c["name"], doc))
        ob.Shape = shape
        try:
            if not hasattr(ob, "IfcType"):
                ob.addProperty("App::PropertyString", "IfcType", "IFC")
            ob.IfcType = c["ifc"]
        except Exception:
            pass
    doc.recompute()
    return doc


def _fc_name(nome, doc):
    """Nome de objeto FreeCAD valido e unico (sem acento/espaco)."""
    import re
    base = re.sub(r"[^0-9A-Za-z_]", "_", str(nome)) or "PECA"
    cand = base
    i = 1
    existentes = {o.Name for o in doc.Objects}
    while cand in existentes:
        i += 1
        cand = f"{base}_{i}"
    return cand


def _dist_pt_seg(p, a, b):
    """Distancia (mm) do ponto p ao segmento a-b (3D)."""
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ap = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
    den = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2
    t = 0.0 if den < 1e-12 else max(0.0, min(1.0, (ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]) / den))
    q = (a[0] + t * ab[0], a[1] + t * ab[1], a[2] + t * ab[2])
    return math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2)


def _conexao_condutores(ca, cb, tol=40.0):
    """True se dois condutores (cyl) se encontram numa JUNCAO (endpoint de um sobre o
    outro): e uma conexao intencional da rede (anel/haste/captacao/descida), nao clash.
    tol em mm (~ folga do raio dos condutores)."""
    if ca["solido"] != "cyl" or cb["solido"] != "cyl":
        return False
    for p in (ca["p1"], ca["p2"]):
        if _dist_pt_seg(p, cb["p1"], cb["p2"]) <= tol:
            return True
    for p in (cb["p1"], cb["p2"]):
        if _dist_pt_seg(p, ca["p1"], ca["p2"]) <= tol:
            return True
    return False


def _interferencias(doc, cxs, vol_min=1.0):
    """Interpenetracao REAL entre solidos, via OCCT (common().Volume), com pre-filtro
    de BoundBox. EXCLUI as junco~es intencionais da rede (condutor-condutor que se
    tocam nas pontas) - essas sao CONEXOES, nao clashes. Retorna (interferencias,
    conexoes). Ordem de doc.Objects (com Shape) casa com cxs."""
    objs = [o for o in doc.Objects if hasattr(o, "Shape") and o.Shape.Volume > 0]
    spec = {objs[i].Name: cxs[i] for i in range(min(len(objs), len(cxs)))}
    itf, conex = [], 0
    for a in range(len(objs)):
        sa, ba, na = objs[a].Shape, objs[a].Shape.BoundBox, objs[a].Name
        for b in range(a + 1, len(objs)):
            ob = objs[b]
            if not ba.intersect(ob.Shape.BoundBox):
                continue
            try:
                v = sa.common(ob.Shape).Volume
            except Exception:
                continue
            if v <= vol_min:
                continue
            ca, cb = spec.get(na), spec.get(ob.Name)
            if ca and cb and _conexao_condutores(ca, cb):
                conex += 1                              # bond intencional da rede
                continue
            itf.append((na, ob.Name, round(v, 1)))
    return itf, conex


def _export(doc):
    """Grava FCStd + STEP + IFC4 (exportador NATIVO do FreeCAD)."""
    import Part
    os.makedirs(f"{EXPORT_DIR}/freecad", exist_ok=True)
    os.makedirs(f"{EXPORT_DIR}/step", exist_ok=True)
    fcstd = f"{EXPORT_DIR}/freecad/{DOC_NAME}.FCStd"
    step = f"{EXPORT_DIR}/step/{DOC_NAME}.step"
    doc.saveAs(fcstd)
    Part.export([o for o in doc.Objects if hasattr(o, "Shape")], step)
    ifc = _export_ifc(doc)
    return fcstd, step, ifc


def _export_ifc(doc):
    import sys
    import FreeCAD as App
    os.makedirs(f"{EXPORT_DIR}/ifc", exist_ok=True)
    ifc = f"{EXPORT_DIR}/ifc/{DOC_NAME}.ifc"
    home = App.getHomePath()
    for sub in ("Mod/BIM/importers", "Mod/BIM", "Mod"):
        p = os.path.join(home, *sub.split("/"))
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    try:
        import exportIFC
    except Exception as e:
        App.Console.PrintWarning("IFC indisponivel (BIM ausente): %s\n" % e)
        return None
    try:
        App.ParamGet("User parameter:BaseApp/Preferences/Mod/BIM").SetString(
            "IfcVersion", "IFC4")
    except Exception:
        pass
    objs = [o for o in doc.Objects if hasattr(o, "Shape")
            and not o.Shape.isNull() and o.Shape.Volume > 0]
    try:
        exportIFC.export(objs, ifc)
        return ifc if (os.path.exists(ifc) and os.path.getsize(ifc) > 0) else None
    except Exception as e:
        App.Console.PrintWarning("IFC export falhou: %s\n" % e)
        return None


def run():
    """Constroi o 3D do projeto eletrico e exporta. Retorna o resumo (mesma FORMA
    do build do concreto)."""
    if not MEMBROS:
        return {"erro": "sem membros (configurar(membros=...) antes de run())"}
    cxs = caixas(MEMBROS)
    doc = _monta_doc(cxs)
    itf, conex = _interferencias(doc, cxs)
    tk = _takeoff(cxs)
    fcstd, step, ifc = _export(doc)
    elementos = len([o for o in doc.Objects if hasattr(o, "Shape")])
    return {"elementos": elementos, "interferencias": len(itf),
            "interferencias_lista": itf, "conexoes": conex,
            "por_grupo": tk["por_tipo"], "comp_condutor_m": tk["comp_condutor_m"],
            "fcstd": fcstd, "step": step, "ifc": ifc}
