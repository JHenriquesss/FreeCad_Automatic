# ============================================================================
# dxf_prancha.py - SCRIPT AVULSO: PRANCHA DXF EDITAVEL A PARTIR DO DESENHO DO
# MODELO IFC (plano de 2026-10-08, Fase 4). Entregavel para quem revisa no
# AutoCAD: geometria em tamanho real no espaco do modelo, uma folha por vista
# no espaco de papel, com viewport na escala, carimbo como bloco com atributos,
# camadas por disciplina e cotas que sao entidades DIMENSION (o CAD mede a
# geometria; o numero nao e' texto copiado).
#
# ENTRADA: os SVG de desenho que o ifcopenshell.draw escreve (hoje pelo
# Blender + Bonsai, docs/fase3-bonsai/scripts/pranchas_bonsai.py): cada
# elemento IFC e' um grupo com a classe, o material, a marca e o GUID; cada
# cota e' uma <line> de classe PredefinedType-DIMENSION; cada eixo da grade do
# IFC e' uma <line> de classe PredefinedType-GRID com o rotulo num <text
# class="GRID"> em cada ponta. O grupo raiz traz a matriz papel<-modelo
# (ifc:matrix3), de onde sai a escala de origem.
#
# O desenho e' DERIVADO do modelo: corrigir o projeto e' corrigir o modelo e
# gerar de novo, nunca editar o DXF.
#
# Uso:  python dxf_prancha.py <pasta com os .svg> <saida.dxf> [chave=valor ...]
#       (chaves do carimbo: PROJETO, CLIENTE, RESPONSAVEL, DATA, REVISAO)
#
# ADOTADO, A CONFERIR (a norma de desenho tecnico ainda nao esta na biblioteca
# de normas): margens de 25 mm a esquerda e 10 mm nas demais, carimbo de 175 mm
# de largura no canto inferior direito, texto de 2,5 mm, espessuras 0,50 mm no
# corte e 0,25/0,18 mm na vista.
# ============================================================================
"""Prancha DXF editavel (ezdxf) a partir dos SVG de desenho do modelo IFC."""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

NS_SVG = "{http://www.w3.org/2000/svg}"
NS_IFC = "{http://www.ifcopenshell.org/ns}"

# escalas e formatos que o plano pede, na ordem de preferencia: a maior escala
# que cabe, na menor folha em que ela cabe
ESCALAS = (50, 75, 100)
ESCALAS_DE_ESCAPE = (125, 150, 200, 250, 500)   # vista que nao cabe em A1 a 1:100
FORMATOS = (("A3", 420.0, 297.0), ("A2", 594.0, 420.0), ("A1", 841.0, 594.0))
MARGEM_ESQ, MARGEM = 25.0, 10.0
CARIMBO_L, CARIMBO_H = 175.0, 40.0
ALTURA_TEXTO = 2.5

# classe IFC -> (camada, cor ACI, espessura em centesimos de mm)
CAMADAS = {
    "IfcColumn": ("EST-PILAR", 1, 25),
    "IfcBeam": ("EST-VIGA", 5, 25),
    "IfcMember": ("EST-SECUNDARIO", 3, 18),
    "IfcPlate": ("EST-CHAPA", 2, 18),
    "IfcMechanicalFastener": ("EST-FIXADOR", 8, 13),
    "IfcFooting": ("FUN-BLOCO", 6, 25),
    "IfcPile": ("FUN-ESTACA", 6, 25),
    "IfcCovering": ("FEC-FECHAMENTO", 9, 13),
    "IfcSlab": ("EST-LAJE", 4, 25),
    "IfcWall": ("ARQ-PAREDE", 7, 25),
}
ESPESSURA_CORTE = 50
CAMADA_COTA, CAMADA_TEXTO = "ANOT-COTA", "ANOT-TEXTO"
CAMADA_EIXO = "ANOT-EIXO"
RAIO_BOLHA, ALTURA_ROTULO_EIXO = 4.0, 3.5      # mm de papel
CAMADA_FOLHA, CAMADA_VIEWPORT = "FOLHA-CARIMBO", "FOLHA-VIEWPORT"
CAMPOS_CARIMBO = ("PROJETO", "CLIENTE", "TITULO", "ESCALA", "FOLHA", "DATA",
                  "RESPONSAVEL", "REVISAO")


def _camada(classe, corte):
    nome, cor, esp = CAMADAS.get(classe, ("GERAL-" + classe.upper()[3:], 7, 18))
    if corte:
        return nome + "-CORTE", cor, ESPESSURA_CORTE
    return nome, cor, esp


def _pontos(d):
    """Polilinhas de um atributo `d` so com M/L/Z (o que o ifcopenshell.draw
    escreve). Outro comando levanta: curva ignorada seria linha sumida."""
    polis, atual = [], []
    for cmd, resto in re.findall(r"([A-Za-z])([^A-Za-z]*)", d):
        if cmd not in "MLZz":
            raise ValueError("comando de caminho SVG nao tratado: %r" % cmd)
        if cmd in "Zz":
            if atual:
                atual.append(atual[0])
            continue
        nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", resto)]
        pares = list(zip(nums[0::2], nums[1::2]))
        if cmd == "M":
            if len(atual) > 1:
                polis.append(atual)
            atual = pares[:]
        else:
            atual.extend(pares)
    if len(atual) > 1:
        polis.append(atual)
    return polis


def ler_desenho(caminho):
    """Le um SVG de desenho e devolve tudo em MILIMETROS REAIS, y para cima,
    com a origem no ponto que a matriz do desenho chama de (0, 0) do modelo."""
    raiz = ET.parse(caminho).getroot()
    secao = next((g for g in raiz.iter(NS_SVG + "g") if g.get(NS_IFC + "matrix3")), None)
    if secao is None:
        raise ValueError("%s: sem ifc:matrix3 (nao e' SVG de desenho do modelo)" % caminho)
    m3 = json.loads(secao.get(NS_IFC + "matrix3"))
    mm_por_m, tx, ty = m3[0][0], m3[0][2], m3[1][2]
    if mm_por_m <= 0 or abs(m3[1][1] - mm_por_m) > 1e-9:
        raise ValueError("%s: matriz do desenho sem escala uniforme" % caminho)

    def real(x, y):
        return ((x - tx) / mm_por_m * 1000.0, -(y - ty) / mm_por_m * 1000.0)

    def _mm(valor):
        return float(re.sub(r"[^0-9.eE+-]", "", valor))

    elementos = []
    for g in raiz.iter(NS_SVG + "g"):
        classes = (g.get("class") or "").split()
        if not classes or not classes[0].startswith("Ifc") or not g.get(NS_IFC + "guid"):
            continue
        polis = []
        for p in g.findall(NS_SVG + "path"):
            polis += [[real(x, y) for x, y in poli] for poli in _pontos(p.get("d") or "")]
        if not polis:
            continue
        material = next((c[len("material-"):] for c in classes if c.startswith("material-")), None)
        elementos.append({"classe": classes[0], "corte": "cut" in classes,
                          "material": None if material == "null" else material,
                          "marca": g.get(NS_IFC + "name"), "guid": g.get(NS_IFC + "guid"),
                          "polilinhas": polis})
    cotas = []
    for ln in raiz.iter(NS_SVG + "line"):
        if "PredefinedType-DIMENSION" in (ln.get("class") or ""):
            cotas.append((real(float(ln.get("x1")), float(ln.get("y1"))),
                          real(float(ln.get("x2")), float(ln.get("y2")))))
    # eixos da grade: a linha e o rotulo que o desenho pos em cada ponta
    rotulos = [((float(t.get("x")), float(t.get("y"))), (t.text or "").strip())
               for t in raiz.iter(NS_SVG + "text") if (t.get("class") or "") == "GRID"]
    eixos = []
    for ln in raiz.iter(NS_SVG + "line"):
        if "PredefinedType-GRID" not in (ln.get("class") or ""):
            continue
        a = (float(ln.get("x1")), float(ln.get("y1")))
        b = (float(ln.get("x2")), float(ln.get("y2")))
        nomes = {r for (x, y), r in rotulos
                 if r and min(abs(x - q[0]) + abs(y - q[1]) for q in (a, b)) < 1e-3}
        if len(nomes) != 1:
            raise ValueError("%s: eixo da grade com %d rotulos nas pontas (esperado 1): %r"
                             % (caminho, len(nomes), sorted(nomes)))
        eixos.append((real(*a), real(*b), nomes.pop()))
    larg, alt = _mm(raiz.get("width")), _mm(raiz.get("height"))
    x0, y1 = real(0.0, 0.0)
    x1, y0 = real(larg, alt)
    return {"nome": os.path.splitext(os.path.basename(caminho))[0],
            "escala_origem": round(1000.0 / mm_por_m),
            "quadro": (x0, y0, x1, y1),          # mm reais: xmin, ymin, xmax, ymax
            "elementos": elementos, "cotas": cotas, "eixos": eixos}


def escolher_folha(larg_real_mm, alt_real_mm, escalas=ESCALAS,
                   escape=ESCALAS_DE_ESCAPE):
    """(escala, formato, largura, altura, de_escape): a maior escala que cabe,
    na menor folha em que ela cabe. Vista que nao cabe em nenhuma escala do
    plano cai numa escala de escape e o retorno DIZ isso."""
    for de_escape, lista in ((False, escalas), (True, escape)):
        for esc in lista:
            for nome, w, h in FORMATOS:
                util_w = w - MARGEM_ESQ - MARGEM
                util_h = h - 2 * MARGEM - CARIMBO_H
                if larg_real_mm / esc <= util_w and alt_real_mm / esc <= util_h:
                    return esc, nome, w, h, de_escape
    raise ValueError("vista de %.0f x %.0f mm nao cabe em A1 nem a 1:%d"
                     % (larg_real_mm, alt_real_mm, escape[-1]))


def _bloco_carimbo(doc):
    blk = doc.blocks.new("CARIMBO")
    cam = {"layer": CAMADA_FOLHA}
    blk.add_lwpolyline([(0, 0), (CARIMBO_L, 0), (CARIMBO_L, CARIMBO_H), (0, CARIMBO_H)],
                       close=True, dxfattribs=cam)
    linhas = CARIMBO_H / 4.0
    for i in (1, 2, 3):
        blk.add_line((0, i * linhas), (CARIMBO_L, i * linhas), dxfattribs=cam)
    meio = CARIMBO_L / 2.0
    for i in (0, 1):
        blk.add_line((meio, i * linhas), (meio, (i + 1) * linhas), dxfattribs=cam)
    # (campo, x, linha de baixo para cima, largura util)
    celulas = [("PROJETO", 0, 3), ("CLIENTE", 0, 2), ("TITULO", 0, 1), ("ESCALA", meio, 1),
               ("RESPONSAVEL", 0, 0), ("FOLHA", meio, 0)]
    for campo, x, lin in celulas:
        y = lin * linhas
        blk.add_text(campo.capitalize(), dxfattribs={
            "layer": CAMADA_FOLHA, "height": 1.8, "style": "TEXTO",
            "insert": (x + 1.5, y + linhas - 3.0)})
        blk.add_attdef(campo, (x + 1.5, y + 1.8), dxfattribs={
            "layer": CAMADA_FOLHA, "height": 3.0, "style": "TEXTO", "prompt": campo})
    for campo, dx in (("DATA", 45.0), ("REVISAO", 20.0)):
        blk.add_attdef(campo, (CARIMBO_L - dx, 3 * linhas + 1.8), dxfattribs={
            "layer": CAMADA_FOLHA, "height": 2.5, "style": "TEXTO", "prompt": campo})
    return blk


def _estilo_cota(doc, escala):
    nome = "COTA-1-%d" % escala
    if nome not in doc.dimstyles:
        doc.dimstyles.new(nome, dxfattribs={
            "dimtxsty": "TEXTO", "dimtxt": ALTURA_TEXTO, "dimasz": 2.0, "dimtsz": 1.5,
            "dimexe": 1.5, "dimexo": 1.5, "dimgap": 1.0, "dimtad": 1, "dimdec": 0,
            "dimzin": 8, "dimscale": float(escala), "dimlfac": 1.0, "dimclrd": 256,
            "dimclre": 256, "dimclrt": 256})
    return nome


def gerar_dxf(desenhos, destino, carimbo=None, folga_entre_vistas_mm=5000.0):
    """Escreve o DXF com uma folha por desenho. Devolve o resumo do que entrou
    (por folha: escala, formato, entidades por camada, cotas)."""
    import ezdxf
    from ezdxf import units
    from ezdxf.enums import TextEntityAlignment

    carimbo = dict(carimbo or {})
    carimbo.setdefault("DATA", datetime.date.today().strftime("%d/%m/%Y"))
    doc = ezdxf.new("R2018", setup=["linetypes"])       # traz o tipo de linha CENTER
    doc.units = units.MM
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LWDISPLAY"] = 1
    doc.styles.new("TEXTO", dxfattribs={"font": "arial.ttf"})
    doc.layers.add(CAMADA_COTA, color=7, lineweight=13)
    doc.layers.add(CAMADA_EIXO, color=8, lineweight=13, linetype="CENTER")
    doc.layers.add(CAMADA_TEXTO, color=7, lineweight=18)
    doc.layers.add(CAMADA_FOLHA, color=7, lineweight=35)
    vp = doc.layers.add(CAMADA_VIEWPORT, color=8)
    vp.dxf.plot = 0                                    # moldura da viewport nao imprime
    _bloco_carimbo(doc)
    msp = doc.modelspace()
    resumo = {"destino": destino, "folhas": []}
    x_base = 0.0
    for k, des in enumerate(desenhos, 1):
        x0, y0, x1, y1 = des["quadro"]
        larg, alt = x1 - x0, y1 - y0
        esc, formato, fw, fh, de_escape = escolher_folha(larg, alt)
        dx, dy = x_base - x0, -y0                      # vista ao lado da anterior
        por_camada = {}
        for el in des["elementos"]:
            camada, cor, esp = _camada(el["classe"], el["corte"])
            if camada not in doc.layers:
                doc.layers.add(camada, color=cor, lineweight=esp)
            for poli in el["polilinhas"]:
                pts = [(x + dx, y + dy) for x, y in poli]
                if len(pts) == 2:
                    msp.add_line(pts[0], pts[1], dxfattribs={"layer": camada})
                else:
                    msp.add_lwpolyline(pts, dxfattribs={"layer": camada})
                por_camada[camada] = por_camada.get(camada, 0) + 1
        estilo = _estilo_cota(doc, esc)
        for (ax, ay), (bx, by) in des["cotas"]:
            dim = msp.add_aligned_dim(p1=(ax + dx, ay + dy), p2=(bx + dx, by + dy),
                                      distance=0, dimstyle=estilo,
                                      dxfattribs={"layer": CAMADA_COTA})
            dim.render()
        for (ax, ay), (bx, by), rotulo in des.get("eixos", ()):
            cam_eixo = {"layer": CAMADA_EIXO}
            msp.add_line((ax + dx, ay + dy), (bx + dx, by + dy),
                         dxfattribs=dict(cam_eixo, ltscale=float(esc)))
            for px, py in ((ax, ay), (bx, by)):
                msp.add_circle((px + dx, py + dy), RAIO_BOLHA * esc,
                               dxfattribs=dict(cam_eixo, linetype="CONTINUOUS"))
                msp.add_text(rotulo, height=ALTURA_ROTULO_EIXO * esc, dxfattribs={
                    "layer": CAMADA_EIXO, "style": "TEXTO"}).set_placement(
                        (px + dx, py + dy), align=TextEntityAlignment.MIDDLE_CENTER)
        # ---- folha no espaco de papel --------------------------------------
        nome_folha = "%02d-%s" % (k, des["nome"])[:31]
        folha = doc.layouts.new(nome_folha)
        folha.page_setup(size=(fw, fh), margins=(0, 0, 0, 0), units="mm")
        cam = {"layer": CAMADA_FOLHA}
        folha.add_lwpolyline([(0, 0), (fw, 0), (fw, fh), (0, fh)], close=True,
                             dxfattribs={"layer": CAMADA_VIEWPORT})
        qx0, qy0, qx1, qy1 = MARGEM_ESQ, MARGEM, fw - MARGEM, fh - MARGEM
        folha.add_lwpolyline([(qx0, qy0), (qx1, qy0), (qx1, qy1), (qx0, qy1)],
                             close=True, dxfattribs=cam)
        valores = dict(carimbo, TITULO=des["nome"], ESCALA="1:%d" % esc,
                       FOLHA="%02d/%02d  %s" % (k, len(desenhos), formato))
        ref = folha.add_blockref("CARIMBO", (qx1 - CARIMBO_L, qy0), dxfattribs=cam)
        ref.add_auto_attribs({c: str(valores.get(c, "")) for c in CAMPOS_CARIMBO})
        util_cx = (qx0 + qx1) / 2.0
        util_cy = (qy0 + CARIMBO_H + qy1) / 2.0
        folha.add_viewport(
            center=(util_cx, util_cy), size=(larg / esc, alt / esc),
            view_center_point=(x_base + larg / 2.0, alt / 2.0),
            view_height=alt, dxfattribs={"layer": CAMADA_VIEWPORT})
        resumo["folhas"].append({
            "folha": nome_folha, "desenho": des["nome"], "escala": esc,
            "formato": formato, "escala_de_escape": de_escape,
            "escala_origem": des["escala_origem"], "entidades": por_camada,
            "cotas": len(des["cotas"]), "eixos": len(des.get("eixos", ())),
            "largura_real_mm": round(larg, 1),
            "altura_real_mm": round(alt, 1)})
        x_base += larg + folga_entre_vistas_mm
    if "Layout1" in doc.layouts and resumo["folhas"]:
        doc.layouts.delete("Layout1")                  # folha vazia que o ezdxf cria
    doc.saveas(destino)
    return resumo


def gerar_de_pasta(pasta, destino, carimbo=None):
    svgs = sorted(os.path.join(pasta, f) for f in os.listdir(pasta) if f.lower().endswith(".svg"))
    if not svgs:
        raise ValueError("nenhum .svg em %s" % pasta)
    return gerar_dxf([ler_desenho(p) for p in svgs], destino, carimbo)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__ + "\nuso: python dxf_prancha.py <pasta dos svg> <saida.dxf> [CHAVE=valor ...]")
    campos = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)
    print(json.dumps(gerar_de_pasta(sys.argv[1], sys.argv[2], campos),
                     ensure_ascii=False, indent=1))
