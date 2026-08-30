"""Build 3D do GALPAO DE CONCRETO pre-moldado (FreeCAD), a partir do modelo
NEUTRO ja calculado (galpao_concreto.membros_bim). Espelha o contrato do
build_galpao.py do aco: expoe reset()/configurar()/run() e e ENVIADO como FONTE
ao FreeCAD (bridge XMLRPC 9875 ou freecadcmd headless) pelo rodar_projeto.

DECISAO (memoria vertical-concreto + cache-modulo-irmao-freecad): o concreto usa
o emissor IFC PURO (nao um build FreeCAD cheio como o aco). Este build recebe a
geometria como PAYLOAD DE DADOS (`membros`, plain list de dicts) - NAO importa
modulos irmaos. Assim a armadilha do "freecad.exe persiste e roda a versao ANTIGA
do modulo irmao" simplesmente nao existe aqui: nao ha modulo irmao para cachear.

Geometria = caixas (Part::Box). Pilar (RECT vertical), viga de cobertura (RECT
apoiada SOBRE o topo do pilar) e sapata (caixa sob o pilar). Eixos: X=vao (largura),
Y=comprimento, Z=altura; unidades de COORDENADA em mm, dims de secao/fundacao em m
(mesma convencao do membros_bim/ifc_emit).

`import FreeCAD` e LOCAL (dentro de run/export) de proposito: assim `caixas()` -
a funcao que converte membros->caixas (posicao/orientacao/volume) - e importavel e
TESTAVEL em pytest puro, sem FreeCAD. (Lição do 3D: green bar de calculo nao cobre
o layout; a orientacao viga/pilar/sapata e verificada em caixas() no CI, e o build
real e conferido por um teste `build` headless com freecadcmd.)
"""

import math
import os

# ---- estado (restaurado por reset(); povoado por configurar()) --------------
MEMBROS = None
EXPORT_DIR = "exports"
DOC_NAME = "galpao_concreto"

DENSIDADE_CONCRETO = 2500.0        # kg/m3 (NBR 6118 8.2.2 - concreto armado)

# nome do membro neutro -> tipo IFC (mapa LOCAL: nao depende do ifc_map irmao,
# que nao esta no sys.path do freecadcmd/bridge). Casa com o emissor puro.
_IFC_TIPO = {"Column": "IfcColumn", "Beam": "IfcBeam", "Footing": "IfcFooting",
             "Slab": "IfcSlab", "Wall": "IfcWall", "Pile": "IfcPile"}

# Tipos que NAO viram solido: IfcSpace e' volume de AMBIENTE, nao peca. Levado ao
# 3D, cada comodo colidiria com todas as paredes e pisos que o delimitam e a
# varredura de interferencia viraria ruido. O ambiente existe so no IFC.
_SEM_SOLIDO = frozenset({"Space"})


def reset():
    """Zera o estado mutavel (evita vazamento entre projetos na MESMA sessao do
    FreeCAD - a armadilha do _CFG global). Chamado no inicio de run()."""
    global MEMBROS, EXPORT_DIR, DOC_NAME
    MEMBROS = None
    EXPORT_DIR = "exports"
    DOC_NAME = "galpao_concreto"


def configurar(membros=None, export_dir=None, doc_name=None):
    """Recebe o payload do modelo neutro. `membros` = lista de dicts de
    galpao_concreto.membros_bim (Column/Beam/Footing com p1/p2/secao ou
    dims/centro). export_dir/doc_name controlam a gravacao."""
    global MEMBROS, EXPORT_DIR, DOC_NAME
    if membros is not None:
        MEMBROS = membros
    if export_dir is not None:
        EXPORT_DIR = export_dir
    if doc_name is not None:
        DOC_NAME = doc_name


def caixas(membros):
    """PURO (sem FreeCAD): converte a lista de membros neutros em especificacoes
    de caixa prontas para Part.makeBox. Retorna lista de dicts:
        {name, tipo, ifc, origem:(ox,oy,oz mm), dims:(dx,dy,dz mm), vol_m3, material}
    A ORIENTACAO por tipo de peca e o coracao deste modulo (o que o teste trava):

    - Column (vertical, corre em Z): secao bf(X) x d(Y), altura = |z2-z1|. O
      membros_bim usa sec_pil={bf: hy, d: hx} -> hy no plano X, hx no plano Y.
    - Beam/Wall (horizontal, corre em X ou em Y): a secao {bf: b, d: h} e LARGURA
      b (no eixo horizontal TRANSVERSAL ao da barra) e ALTURA h (em Z). Onde a
      linha p1/p2 cai na secao e' declarado pelo membro em `ancoragem`:
      'base' = face inferior (a viga apoia no topo do pilar e sobe h, sem
      interpenetrar) ; 'eixo' (padrao) = eixo centroidal. A MESMA chave e' lida
      pelo emissor IFC - era aqui que as duas descricoes divergiam em h/2.
    - Footing (caixa): dims=[B,L,hf] (mm) em X,Y,Z; centro dado (topo em z=0).
      A caixa vem em MILIMETROS, mesma unidade do `dims` que o ifc_emit consome -
      uma unica convencao para os dois emissores (era m aqui e mm la, e a sapata
      saia 1000x menor no IFC).
    """
    out = []
    for mb in membros:
        tipo = mb["tipo"]
        if tipo in _SEM_SOLIDO:
            continue
        ifc = _IFC_TIPO.get(tipo, "IfcBuildingElementProxy")
        nome = mb.get("marca") or mb.get("perfil") or tipo
        if "dims" in mb and "centro" in mb:                # FOOTING/SLAB (caixa)
            B, L, hf = mb["dims"]                          # ja em mm
            cx, cy, cz = mb["centro"]
            origem = (cx - B / 2.0, cy - L / 2.0, cz - hf / 2.0)
            dims = (B, L, hf)
        elif str((mb.get("secao") or {}).get("forma", "")).upper() == "ROUND":
            # ESTACA (barra circular): cilindro, nao prisma. Um prisma DxD daria
            # 4/pi = 27 % a mais de concreto no quantitativo, e o cross-check com
            # o emissor IFC (que extruda um IfcCircleProfileDef) reprovaria.
            p1, p2 = mb["p1"], mb["p2"]
            D = float(mb["secao"]["D"]) * 1000.0            # m -> mm
            comprimento = math.dist(p1, p2)
            out.append({"name": nome, "tipo": tipo, "ifc": ifc, "solido": "cyl",
                        "origem": (p1[0], p1[1], min(p1[2], p2[2])),
                        "dims": (D, D, comprimento),
                        "raio_mm": D / 2.0, "altura_mm": comprimento,
                        "vol_m3": math.pi * (D / 2.0) ** 2 * comprimento / 1e9,
                        "material": mb.get("material", "Concreto")})
            continue
        else:
            p1, p2 = mb["p1"], mb["p2"]
            bf = mb["secao"]["bf"] * 1000.0                # m -> mm
            d = mb["secao"]["d"] * 1000.0
            if tipo in ("Beam", "Wall"):                   # barra HORIZONTAL
                # corre no eixo de maior extensao; a secao fica com a largura bf
                # no eixo horizontal transversal e a altura d em Z.
                dx_eixo = abs(p2[0] - p1[0])
                dy_eixo = abs(p2[1] - p1[1])
                dz = d                                     # altura -> Z
                if dx_eixo >= dy_eixo:                     # corre em X
                    dx, dy = dx_eixo, bf
                else:                                      # corre em Y
                    dx, dy = bf, dy_eixo
                # ANCORAGEM (mesma chave que o ifc_emit le): 'base' = p1/p2 e' a
                # face inferior e a peca sobe d; 'eixo' (padrao) = a linha e' o
                # eixo centroidal e a peca fica centrada nela. Os dois emissores
                # liam a mesma chave de formas diferentes; agora leem igual.
                z0 = p1[2] if mb.get("ancoragem") == "base" else p1[2] - dz / 2.0
                origem = (min(p1[0], p2[0]) - (0.0 if dx_eixo >= dy_eixo else dx / 2.0),
                          min(p1[1], p2[1]) - (dy / 2.0 if dx_eixo >= dy_eixo else 0.0),
                          z0)
                dims = (dx, dy, dz)
            else:                                          # COLUMN (corre em Z)
                dz = abs(p2[2] - p1[2])
                dx = bf                                    # hy -> X
                dy = d                                     # hx -> Y
                origem = (p1[0] - dx / 2.0, p1[1] - dy / 2.0, min(p1[2], p2[2]))
                dims = (dx, dy, dz)
        vol_m3 = (dims[0] * dims[1] * dims[2]) / 1e9       # mm3 -> m3
        out.append({"name": nome, "tipo": tipo, "ifc": ifc, "solido": "box",
                    "origem": origem, "dims": dims, "vol_m3": vol_m3,
                    "material": mb.get("material", "Concreto")})
    return out


def _takeoff(cxs):
    """Quantitativo de concreto por tipo de peca (volume m3 + massa kg), a partir
    das caixas. Puro (sem FreeCAD)."""
    por = {}
    for c in cxs:
        v = por.setdefault(c["tipo"], {"n": 0, "vol_m3": 0.0})
        v["n"] += 1
        v["vol_m3"] += c["vol_m3"]
    vol_tot = sum(v["vol_m3"] for v in por.values())
    for v in por.values():
        v["vol_m3"] = round(v["vol_m3"], 3)
        v["massa_kg"] = round(v["vol_m3"] * DENSIDADE_CONCRETO, 1)
    return {"por_tipo": por, "vol_concreto_m3": round(vol_tot, 3),
            "massa_concreto_kg": round(vol_tot * DENSIDADE_CONCRETO, 1)}


# ---------------------------------------------------------------------------
# Dali para baixo: precisa do FreeCAD. Imports LOCAIS para manter caixas()/
# _takeoff() testaveis em pytest puro.
# ---------------------------------------------------------------------------
def _monta_doc(cxs):
    """Cria o documento FreeCAD e adiciona uma Part::Box por caixa, tipada com
    IfcType para o Revit. Retorna o doc."""
    import FreeCAD as App
    import Part
    name = DOC_NAME
    for dd in list(App.listDocuments().values()):
        if dd.Name == name:
            App.closeDocument(name)
            break
    doc = App.newDocument(name)
    for c in cxs:
        if c.get("solido") == "cyl":                # ESTACA: cilindro real
            solido = Part.makeCylinder(c["raio_mm"], c["altura_mm"])
        else:
            solido = Part.makeBox(*c["dims"])
        solido.translate(App.Vector(*c["origem"]))
        ob = doc.addObject("Part::Feature", _fc_name(c["name"], doc))
        ob.Shape = solido
        try:                                       # tipa p/ o IFC/Revit
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


def _interferencias(doc, tol=1.0, vol_min=1.0):
    """Interpenetracao REAL entre solidos, via OCCT (common().Volume), com
    pre-filtro de BoundBox. Toques de face (viga sobre pilar, sapata sob pilar)
    tem volume comum ~0 e nao contam. tol/vol_min em mm/mm3."""
    objs = [o for o in doc.Objects if hasattr(o, "Shape") and o.Shape.Volume > 0]
    itf = []
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
            if v > vol_min:
                itf.append((na, ob.Name, round(v, 1)))
    return itf


def _export(doc):
    """Grava FCStd + STEP + IFC4. IFC reusa o exportador NATIVO do FreeCAD
    (exportIFC + ifcopenshell, EMBUTIDOS no FreeCAD 1.1). Best-effort no IFC:
    sem BIM disponivel -> ifc=None (nao quebra o build)."""
    import FreeCAD as App
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


def _capturar_vistas(doc):
    """Screenshots das vistas padrao (so com GUI). Best-effort."""
    import time
    out = []
    try:
        import FreeCAD
        if not FreeCAD.GuiUp:
            return out
        import FreeCADGui as Gui
        vdir = f"{EXPORT_DIR}/vistas"
        os.makedirs(vdir, exist_ok=True)
        Gui.setActiveDocument(doc.Name)
        view = Gui.ActiveDocument.ActiveView
        for nome, metodo in (("isometrica", "viewIsometric"), ("frontal", "viewFront"),
                             ("lateral_dir", "viewRight"), ("superior", "viewTop")):
            getattr(view, metodo)()
            view.fitAll()
            time.sleep(0.3)
            Gui.updateGui()
            path = f"{vdir}/{nome}.png"
            view.saveImage(path, 1200, 800, "#FFFFFF")
            out.append(path)
    except Exception:
        pass
    return out


def run():
    """Constroi o 3D do galpao de concreto e exporta. Retorna o resumo (mesma
    FORMA do build do aco: elementos/interferencias/por_grupo/fcstd/step/ifc)."""
    if not MEMBROS:
        return {"erro": "sem membros (configurar(membros=...) antes de run())"}
    cxs = caixas(MEMBROS)
    doc = _monta_doc(cxs)
    itf = _interferencias(doc)
    tk = _takeoff(cxs)
    fcstd, step, ifc = _export(doc)
    vistas = _capturar_vistas(doc)
    elementos = len([o for o in doc.Objects if hasattr(o, "Shape")])
    return {"elementos": elementos, "interferencias": len(itf),
            "interferencias_lista": itf,
            "por_grupo": tk["por_tipo"],
            "vol_concreto_m3": tk["vol_concreto_m3"],
            "massa_concreto_kg": tk["massa_concreto_kg"],
            "fcstd": fcstd, "step": step, "ifc": ifc, "vistas": vistas}
