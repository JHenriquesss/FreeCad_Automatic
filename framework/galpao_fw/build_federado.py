# ============================================================================
# build_federado.py - O QUE ESTE SCRIPT FAZ / CONSTROI
# Build 3D SOLIDO FEDERADO do galpao turnkey: renderiza os membros NEUTROS das 4
# disciplinas (concreto+eletrico+incendio+aco, ja no FRAME COMUM de galpao_turnkey.
# _membros_federados) num UNICO documento FreeCAD e roda a interferencia REAL (OCCT
# common().Volume) ENTRE disciplinas. Espelha o contrato dos build_* (payload = lista
# de membros; import de FreeCAD LOCAL dentro de run/export -> `solidos()` e' testavel
# em pytest puro). Exporta FCStd + STEP + IFC4.
#
# Convencao (identica a galpao_turnkey/_membros_federados):
#  - COORDENADAS em mm; eixos X=comprimento, Y=largura, Z=altura;
#  - disciplina pela marca prefixada C-/E-/I-/A- (concreto/eletrico/incendio/aco);
#  - dims de CAIXA: ESTRUTURAL (concreto/aco) em METROS (x1000), INSTALACOES
#    (eletrico/incendio) em MM; secao de BARRA sempre em METROS.
#  - RENDER: caixa -> Part.makeBox; barra RECT -> prisma orientado p1->p2 (secao
#    bf x d); barra ROUND -> cilindro orientado (D); painel (poligono) -> ignorado.
# ============================================================================
"""Build 3D solido FEDERADO do turnkey (4 disciplinas num doc) + interferencia OCCT
entre disciplinas. `solidos()` puro (CI); realizacao e export em FreeCAD."""

import math
import os

MEMBROS = []
EXPORT_DIR = "exports"
DOC_NAME = "galpao_federado"

# dims de CAIXA -> mm: concreto em METROS (x1000); aco (modelo_neutro), eletrico e
# incendio ja em MM (x1). Secao de BARRA e' sempre metros (tratada a parte).
_ESCALA_M = {"concreto": 1000.0, "aco": 1.0, "eletrico": 1.0, "incendio": 1.0}
_DISC_DE_MARCA = {"C": "concreto", "E": "eletrico", "I": "incendio", "A": "aco"}
_TIPOS_IGNORADOS = {"Covering", "Cladding"}          # fechamento/telha: fora do clash


def reset():
    global MEMBROS, EXPORT_DIR, DOC_NAME
    MEMBROS = []
    EXPORT_DIR = "exports"
    DOC_NAME = "galpao_federado"


def configurar(membros=None, export_dir=None, doc_name=None):
    """Recebe o payload do modelo federado (lista de membros ja no frame comum, com
    marca prefixada por disciplina)."""
    global MEMBROS, EXPORT_DIR, DOC_NAME
    if membros is not None:
        MEMBROS = membros
    if export_dir is not None:
        EXPORT_DIR = export_dir
    if doc_name is not None:
        DOC_NAME = doc_name


def _disc(mb):
    return _DISC_DE_MARCA.get(str(mb.get("marca", ""))[:1])


def solidos(membros):
    """PURO (sem FreeCAD): converte a lista de membros federados em especificacoes de
    SOLIDO prontas p/ realizar no FreeCAD. Retorna lista de dicts:
      caixa: {name, disc, tipo, kind:'box', origem:(mm), dims:(mm), vol_m3}
      barra: {name, disc, tipo, kind:'bar_rect'|'bar_round', p1, p2, sec:(bf,d)|(D,),
              comprimento_mm, dir:(ux,uy,uz), vol_m3}
    Ignora paineis (poligono) e tipos de fechamento (Covering/Cladding)."""
    out = []
    for mb in membros:
        disc = _disc(mb)
        if disc is None or mb.get("tipo") in _TIPOS_IGNORADOS or "poligono" in mb:
            continue
        nome = str(mb.get("marca", mb.get("tipo", "PECA")))
        tipo = mb.get("tipo")
        if "dims" in mb and "centro" in mb:                       # CAIXA
            sc = _ESCALA_M.get(disc, 1.0)
            dx, dy, dz = (mb["dims"][0] * sc, mb["dims"][1] * sc, mb["dims"][2] * sc)
            cx, cy, cz = mb["centro"]
            origem = (cx - dx / 2.0, cy - dy / 2.0, cz - dz / 2.0)
            out.append({"name": nome, "disc": disc, "tipo": tipo, "kind": "box",
                        "origem": origem, "dims": (dx, dy, dz),
                        "vol_m3": dx * dy * dz / 1e9})
            continue
        if "p1" in mb and "p2" in mb and "secao" in mb:           # BARRA
            p1, p2 = tuple(mb["p1"]), tuple(mb["p2"])
            L = math.dist(p1, p2)
            if L <= 0:
                continue
            d3 = tuple((b - a) / L for a, b in zip(p1, p2))
            s = mb["secao"]
            if s.get("forma") == "ROUND" or ("D" in s and "bf" not in s):
                D = s.get("D", 0.02) * 1000.0
                out.append({"name": nome, "disc": disc, "tipo": tipo, "kind": "bar_round",
                            "p1": p1, "p2": p2, "sec": (D,), "comprimento_mm": L,
                            "dir": d3, "vol_m3": math.pi * (D / 2.0) ** 2 * L / 1e9})
            else:
                bf = s.get("bf", 0.05) * 1000.0
                d = s.get("d", 0.05) * 1000.0
                out.append({"name": nome, "disc": disc, "tipo": tipo, "kind": "bar_rect",
                            "p1": p1, "p2": p2, "sec": (bf, d), "comprimento_mm": L,
                            "dir": d3, "vol_m3": bf * d * L / 1e9})
    return out


def _por_disciplina(sols):
    """Quantitativo por disciplina (n de solidos + volume m3). Puro."""
    por = {}
    for c in sols:
        v = por.setdefault(c["disc"], {"n": 0, "vol_m3": 0.0})
        v["n"] += 1
        v["vol_m3"] += c["vol_m3"]
    for v in por.values():
        v["vol_m3"] = round(v["vol_m3"], 3)
    return por


# ---------------------------------------------------------------------------
# Dali para baixo: precisa do FreeCAD. Imports LOCAIS (solidos()/_por_disciplina
# ficam testaveis em pytest puro).
# ---------------------------------------------------------------------------
def _fc_name(nome, doc):
    import re
    base = re.sub(r"[^0-9A-Za-z_]", "_", str(nome)) or "PECA"
    cand, i = base, 1
    existentes = {o.Name for o in doc.Objects}
    while cand in existentes:
        i += 1
        cand = "%s_%d" % (base, i)
    return cand


def _shape_de_solido(c):
    """Constroi a Shape (Part) de um solido: caixa, prisma RECT orientado ou cilindro
    ROUND orientado p1->p2."""
    import FreeCAD as App
    import Part
    if c["kind"] == "box":
        s = Part.makeBox(*c["dims"])
        s.translate(App.Vector(*c["origem"]))
        return s
    p1 = App.Vector(*c["p1"])
    dirv = App.Vector(*c["dir"])
    rot = App.Rotation(App.Vector(0, 0, 1), dirv)          # eixo local Z -> p1->p2
    if c["kind"] == "bar_round":
        (D,) = c["sec"]
        s = Part.makeCylinder(D / 2.0, c["comprimento_mm"])
        s.Placement = App.Placement(p1, rot)
        return s
    bf, d = c["sec"]                                        # bar_rect
    # base do box em (-bf/2,-d/2,0) -> secao CENTRADA no eixo p1->p2 (linha do centroide).
    # Usar o ponto-base do makeBox: translate()+Placement se perde (a secao descia d/2).
    s = Part.makeBox(bf, d, c["comprimento_mm"], App.Vector(-bf / 2.0, -d / 2.0, 0.0))
    s.Placement = App.Placement(p1, rot)
    return s


def _monta_doc(sols):
    """Cria o documento FreeCAD com um Part::Feature por solido; guarda a disciplina
    de cada objeto. Retorna (doc, {obj_name: disc})."""
    import FreeCAD as App
    name = DOC_NAME
    for dd in list(App.listDocuments().values()):
        if dd.Name == name:
            App.closeDocument(name)
            break
    doc = App.newDocument(name)
    disc_de = {}
    for c in sols:
        try:
            shp = _shape_de_solido(c)
        except Exception:
            continue
        ob = doc.addObject("Part::Feature", _fc_name(c["name"], doc))
        ob.Shape = shp
        ob.Label = c["name"]
        disc_de[ob.Name] = c["disc"]
    doc.recompute()
    return doc, disc_de


def _interferencias_cross(doc, disc_de, vol_min=1000.0):
    """Interpenetracao REAL (OCCT common().Volume) ENTRE disciplinas diferentes, com
    pre-filtro de BoundBox. Retorna lista (a, b, disc_a, disc_b, vol_mm3)."""
    objs = [o for o in doc.Objects if hasattr(o, "Shape") and o.Shape.Volume > 0]
    itf = []
    for a in range(len(objs)):
        oa = objs[a]; da = disc_de.get(oa.Name)
        ba = oa.Shape.BoundBox
        for b in range(a + 1, len(objs)):
            ob = objs[b]; db = disc_de.get(ob.Name)
            if da == db or da is None or db is None:
                continue
            if not ba.intersect(ob.Shape.BoundBox):
                continue
            try:
                v = oa.Shape.common(ob.Shape).Volume
            except Exception:
                continue
            if v > vol_min:
                itf.append((oa.Label, ob.Label, da, db, round(v, 1)))
    itf.sort(key=lambda t: -t[4])
    return itf


def _export(doc):
    """Grava FCStd + STEP + IFC4 (exportador nativo do FreeCAD). Best-effort no IFC."""
    import FreeCAD as App
    import Part
    os.makedirs("%s/freecad" % EXPORT_DIR, exist_ok=True)
    os.makedirs("%s/step" % EXPORT_DIR, exist_ok=True)
    fcstd = "%s/freecad/%s.FCStd" % (EXPORT_DIR, DOC_NAME)
    step = "%s/step/%s.step" % (EXPORT_DIR, DOC_NAME)
    doc.saveAs(fcstd)
    shapes = [o.Shape for o in doc.Objects if hasattr(o, "Shape")]
    if shapes:
        comp = Part.makeCompound(shapes)
        comp.exportStep(step)
    ifc = None
    try:
        import exportIFC
        os.makedirs("%s/ifc" % EXPORT_DIR, exist_ok=True)
        ifc = "%s/ifc/%s.ifc" % (EXPORT_DIR, DOC_NAME)
        exportIFC.export([o for o in doc.Objects if hasattr(o, "Shape")], ifc)
    except Exception:
        ifc = None
    return {"fcstd": fcstd, "step": step, "ifc": ifc}


def run():
    """Entry-point do dispatch (bridge/headless). Monta os solidos federados,
    exporta e roda a interferencia OCCT entre disciplinas. Retorna dict-resultado."""
    sols = solidos(MEMBROS)
    if not sols:
        return {"erro": "sem solidos (configurar(membros=...) antes de run())"}
    doc, disc_de = _monta_doc(sols)
    arquivos = _export(doc)
    itf = _interferencias_cross(doc, disc_de)
    return {"n_solidos": len(sols), "por_disciplina": _por_disciplina(sols),
            "n_interferencias_cross": len(itf), "interferencias_cross": itf, **arquivos}


if __name__ == "__main__":
    # smoke puro (sem FreeCAD): so a decomposicao em solidos
    demo = [{"marca": "C-P1", "tipo": "Column", "p1": [0, 0, 0], "p2": [0, 0, 6000],
             "secao": {"bf": 0.3, "d": 0.3}},
            {"marca": "I-SPK1", "tipo": "Sprinkler", "dims": [100, 100, 100],
             "centro": [5000, 5000, 5800]}]
    print(solidos(demo))
