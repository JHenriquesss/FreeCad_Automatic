"""Fase 3 (plano de 2026-10-08) - pranchas do galpao pelo Blender + Bonsai, sem janela.

Abre o IFC gerado pelo motor (ifc_emit), cria as vistas enquadradas no modelo,
cota pelos eixos lidos dos proprios pilares do IFC, monta a folha com carimbo e
grava tudo ao lado do IFC (drawings/, layouts/, sheets/). Nada e' editado a mao:
alterou o projeto, regenera o IFC e roda de novo.

Uso (o IFC e' COPIADO para uma pasta de trabalho antes: o Bonsai grava nele):
    blender -b --python pranchas_bonsai.py -- <caminho.ifc> [titulo=...] [revisao=..]
                                              [lista=<tabela.svg>] [VISTA ...]

`lista=` e' o SVG da lista de material (escrito por `pranchas_ifc.svg_da_lista`
na pasta do IFC): entra numa folha propria, depois das demais.

Sem VISTA, gera todas. Imprime uma linha `RELATORIO_JSON {...}` com o tempo de
cada passo, os eixos lidos e os avisos.

Medido no Blender 5.2.1 LTS + Bonsai (extensions.blender.org) em 2026-10-08.
Tres coisas que o Bonsai nao faz sozinho e este script resolve:
  - a camera nasce na origem com quadro de 50 x 50 m: posicao, largura, altura e
    profundidade saem do envelope do modelo;
  - a resolucao da cena so acompanha largura/altura na ATIVACAO do desenho: sem
    reatribuir, as cotas saem deslocadas de (largura - altura) / 2;
  - o nome do arquivo SVG vem do nome do desenho na criacao: renomear pelo
    nucleo (`core.update_drawing_name`) antes de gerar.
"""
import json
import math
import os
import sys
import time
import traceback

import bpy
import mathutils

MARGEM_M = 11.0       # folga em volta do modelo: bolhas dos eixos, cotas e marca de corte
ESCALA_GERAL, ESCALA_DETALHE = 100, 10
JANELA_DETALHE_M = 2.2          # lado da janela dos detalhes de ligacao
# Folha A1 (mm, y para baixo como no SVG). A area util para acima do carimbo do
# modelo do Bonsai, que ocupa a faixa de baixo da folha (medido no A1.svg).
AREA_UTIL = (30.0, 30.0, 811.0, 505.0)
VAO_MM, TITULO_MM = 12.0, 16.0
# ordem em que as vistas entram nas folhas
ORDEM = ("PLANTA-BAIXA", "CORTE-TRANSVERSAL", "ELEVACAO-FRONTAL", "ELEVACAO-LATERAL",
         "PLANTA-FUNDACAO", "PLANTA-COBERTURA",
         "DET-BASE-ELEVACAO", "DET-BASE-PLANTA", "DET-JOELHO", "DET-CUMEEIRA",
         "DET-CONTRAVENTAMENTO", "DET-TERCA", "DET-LONGARINA")
# rotulos do carimbo padrao do Bonsai -> portugues
CARIMBO_PT = {"DRAWING NUMBER": "FOLHA", "DRAWING TITLE": "TITULO", "GRID NORTH": "NORTE",
              "COMPANY": "RESP. TECNICO", "REV. NO.": "REV.", "DESCRIPTION": "DESCRICAO",
              "AUTHOR": "AUTOR", "ISSUED": "EMISSAO", "NOTES": "NOTAS", "DATE": "DATA",
              "DO NOT SCALE DRAWINGS": "NAO MEDIR NO DESENHO"}
# titulo curto de cada vista no carimbo (a celula do titulo tem ~80 mm)
TITULO_CURTO = {"PLANTA-BAIXA": "PLANTA", "CORTE-TRANSVERSAL": "CORTE",
                "ELEVACAO-FRONTAL": "ELEV. FRONTAL", "ELEVACAO-LATERAL": "ELEV. LATERAL",
                "PLANTA-FUNDACAO": "FUNDACAO", "PLANTA-COBERTURA": "COBERTURA",
                "DET-BASE-ELEVACAO": "DET. BASE", "DET-BASE-PLANTA": "BASE (PLANTA)",
                "DET-JOELHO": "DET. JOELHO", "DET-CUMEEIRA": "DET. CUMEEIRA",
                "DET-CONTRAVENTAMENTO": "DET. CONTRAV.", "DET-TERCA": "DET. TERCA",
                "DET-LONGARINA": "DET. LONGARINA"}


def distribuir(tamanhos, area=AREA_UTIL, vao=VAO_MM, titulo=TITULO_MM):
    """Reparte as vistas em folhas, em prateleiras (esquerda->direita, de cima
    para baixo), reservando a faixa do titulo sob cada vista. `tamanhos` =
    [(nome, largura_mm, altura_mm)] na ordem de entrada. Devolve
    [[(nome, x, y), ...] por folha]. Vista maior que a area util levanta: nao
    existe folha em que ela caiba nesta escala."""
    x0, y0, x1, y1 = area
    folhas, atual = [], []
    x, y, alt_linha = x0, y0, 0.0
    for nome, larg, alt in tamanhos:
        if larg > x1 - x0 or alt + titulo > y1 - y0:
            raise ValueError("%s (%.0f x %.0f mm) nao cabe na area util da folha"
                             % (nome, larg, alt))
        if x + larg > x1:                              # proxima prateleira
            x, y, alt_linha = x0, y + alt_linha + titulo + vao, 0.0
        if y + alt + titulo > y1:                      # proxima folha
            folhas.append(atual)
            atual, x, y, alt_linha = [], x0, y0, 0.0
        atual.append((nome, x, y))
        x += larg + vao
        alt_linha = max(alt_linha, alt)
    if atual:
        folhas.append(atual)
    return folhas


def _reposicionar(pasta_layouts, posicoes):
    """Grava no arquivo de disposicao de cada folha a posicao calculada (o
    Bonsai empilha os desenhos sem conferir se cabem)."""
    import re
    mexidos = 0
    for arq in os.listdir(pasta_layouts):
        if not arq.lower().endswith(".svg"):
            continue
        caminho = os.path.join(pasta_layouts, arq)
        txt = open(caminho, encoding="utf-8").read()

        def _grupo(m):
            nonlocal mexidos
            g = m.group(0)
            ref = re.search(r'data-type="foreground" xlink:href="([^"]+)"', g)
            nome = os.path.splitext(os.path.basename(ref.group(1).replace("\\", "/")))[0] if ref else None
            if nome not in posicoes:
                return g
            x, y = posicoes[nome]
            alt = float(re.search(r'data-type="foreground"[^>]*height="([^"]+)"', g).group(1))
            g = re.sub(r'(data-type="foreground"[^>]*? x=")[^"]+(" y=")[^"]+', r"\g<1>%s\g<2>%s" % (x, y), g)
            g = re.sub(r'(data-type="view-title"[^>]*? x=")[^"]+(" y=")[^"]+',
                       r"\g<1>%s\g<2>%s" % (x, y + alt + 4.0), g)
            mexidos += 1
            return g

        novo = re.sub(r'<g data-type="drawing".*?</g>', _grupo, txt, flags=re.S)
        if novo != txt:
            open(caminho, "w", encoding="utf-8").write(novo)
    return mexidos


BORDA_MM = 8.0        # folga para a bolha do eixo e a seta do corte nao serem cortadas


def puxar_para_dentro(caminho, borda=BORDA_MM):
    """O Bonsai leva a linha de cada eixo e de cada corte ate a borda da vista,
    e a bolha ou a seta da ponta sai cortada pela metade. Encurta essas linhas
    para `borda` mm dentro da vista e leva junto o rotulo e o simbolo que
    estavam na ponta. Devolve quantas pontas mexeu."""
    import re
    txt = open(caminho, encoding="utf-8").read()
    cab = re.search(r"<svg[^>]*>", txt).group(0)
    larg = float(re.search(r'viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)"', cab).group(1))
    alt = float(re.search(r'viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)"', cab).group(2))

    def _dentro(x, y):
        return (min(max(x, borda), larg - borda), min(max(y, borda), alt - borda))

    desloc = []                                       # (ponto antigo, delta)
    fora = []                                         # pontas de linhas que nao passam na vista

    def _linha(m):
        tag = m.group(0)
        v = {k: float(re.search(r'\b%s="([-\d.eE]+)"' % k, tag).group(1))
             for k in ("x1", "y1", "x2", "y2")}
        vertical = abs(v["x1"] - v["x2"]) < abs(v["y1"] - v["y2"])
        # eixo que nao cruza a vista (ex.: o eixo B num detalhe do eixo A): o
        # Bonsai o deixa fora do quadro; nao pode ser trazido para dentro
        if (vertical and not 0.0 <= v["x1"] <= larg) or \
                (not vertical and not 0.0 <= v["y1"] <= alt):
            fora.extend([(v["x1"], v["y1"]), (v["x2"], v["y2"])])
            return ""
        for kx, ky in (("x1", "y1"), ("x2", "y2")):
            nx, ny = _dentro(v[kx], v[ky])
            if vertical:
                nx = v[kx]                            # encurta so ao longo da linha
            else:
                ny = v[ky]
            if (nx, ny) != (v[kx], v[ky]):
                desloc.append(((v[kx], v[ky]), (nx - v[kx], ny - v[ky])))
                tag = re.sub(r'\b%s="[-\d.eE]+"' % kx, '%s="%s"' % (kx, nx), tag)
                tag = re.sub(r'\b%s="[-\d.eE]+"' % ky, '%s="%s"' % (ky, ny), tag)
        return tag

    txt = re.sub(r"<line[^>]*PredefinedType-(?:GRID|SECTION)[^>]*>", _linha, txt)
    if not desloc and not fora:
        return 0

    def _delta(x, y):
        for (px, py), d in desloc:
            if abs(x - px) < 4.0 and abs(y - py) < 4.0:
                return d
        return None

    def _rotulo(m):
        tag = m.group(0)
        mx_ = re.search(r'\bx="([-\d.eE]+)"', tag)
        my_ = re.search(r'\by="([-\d.eE]+)"', tag)
        if not (mx_ and my_):
            return tag
        x, y = float(mx_.group(1)), float(my_.group(1))
        if any(abs(x - fx) < 4.0 and abs(y - fy) < 4.0 for fx, fy in fora):
            # rotulo de eixo que nao passa na vista: sai junto com a linha
            return "<text data-remover=\"1\">" if tag.startswith("<text") else ""
        d = _delta(x, y)
        if d is None:
            return tag
        tag = re.sub(r'\bx="[-\d.eE]+"', 'x="%s"' % (x + d[0]), tag, count=1)
        tag = re.sub(r'\by="[-\d.eE]+"', 'y="%s"' % (y + d[1]), tag, count=1)
        rot = re.search(r"rotate\(([-\d.eE]+), ([-\d.eE]+), ([-\d.eE]+)\)", tag)
        if rot:
            tag = tag.replace(rot.group(0), "rotate(%s, %s, %s)" % (
                rot.group(1), float(rot.group(2)) + d[0], float(rot.group(3)) + d[1]))
        return tag

    txt = re.sub(r"<(?:text|use)\b[^>]*>", _rotulo, txt)
    txt = re.sub(r'<text data-remover="1">[^<]*</text>', "", txt)
    open(caminho, "w", encoding="utf-8").write(txt)
    return len(desloc)


def _carimbo_em_portugues(caminho):
    txt = open(caminho, encoding="utf-8").read()
    for en, pt in CARIMBO_PT.items():
        txt = txt.replace(">%s<" % en, ">%s<" % pt)
    open(caminho, "w", encoding="utf-8").write(txt)


def _envelope(tool):
    """Envelope dos ELEMENTOS do modelo (a grade de eixos passa dos pilares de
    proposito e nao entra na conta do enquadramento)."""
    pts = []
    for el in tool.Ifc.get().by_type("IfcElement"):
        o = tool.Ifc.get_object(el)
        if o is not None and o.type == "MESH":
            pts += [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    mn = [min(p[i] for p in pts) for i in range(3)]
    mx = [max(p[i] for p in pts) for i in range(3)]
    return mn, mx


def _eixos(ifc):
    """Eixos X e Y e altura dos pilares, lidos do IFC (metros)."""
    import ifcopenshell.util.placement as up
    import ifcopenshell.util.unit as uu
    esc = uu.calculate_unit_scale(ifc)
    cols = ifc.by_type("IfcColumn")
    mats = [up.get_local_placement(e.ObjectPlacement) for e in cols]
    xs = sorted({round(m[0, 3] * esc, 3) for m in mats})
    ys = sorted({round(m[1, 3] * esc, 3) for m in mats})
    alt = max(e.Representation.Representations[0].Items[0].Depth * esc for e in cols)
    return xs, ys, alt


def _cumeeira(ifc):
    """Cota (m) do ponto mais alto do EIXO das vigas do portico (marca V<n>):
    a ponta da extrusao de cada viga, lida da posicao e do comprimento no IFC.
    None se o modelo nao tiver viga de portico."""
    import re

    import ifcopenshell.util.placement as up
    import ifcopenshell.util.unit as uu
    import numpy as np
    esc = uu.calculate_unit_scale(ifc)
    topo = None
    for v in ifc.by_type("IfcBeam"):
        if not re.fullmatch(r"V\d+", v.Name or ""):
            continue
        item = v.Representation.Representations[0].Items[0]
        if not item.is_a("IfcExtrudedAreaSolid"):
            continue
        m = up.get_local_placement(v.ObjectPlacement)
        for comp in (0.0, float(item.Depth)):
            z = float((m @ np.array([0.0, 0.0, comp, 1.0]))[2]) * esc
            topo = z if topo is None else max(topo, z)
    return topo


def _placa_de_base(tool, x, y):
    """Envelope (min, max), em metros, da placa de base (marca PB<n>) mais
    proxima do pilar em (x, y). None se o modelo nao tiver placa de base."""
    melhor = None
    for el in tool.Ifc.get().by_type("IfcPlate"):
        if not (el.Name or "").startswith("PB"):
            continue
        o = tool.Ifc.get_object(el)
        if o is None or o.type != "MESH":
            continue
        pts = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        mn = [min(p[i] for p in pts) for i in range(3)]
        mx = [max(p[i] for p in pts) for i in range(3)]
        dist = math.hypot((mn[0] + mx[0]) / 2 - x, (mn[1] + mx[1]) / 2 - y)
        if melhor is None or dist < melhor[0]:
            melhor = (dist, mn, mx)
    return None if melhor is None else (melhor[1], melhor[2])


def detalhes_do_galpao(xs, ys, alt_col, placa, cumeeira=None, apoios=None):
    """Detalhes de ligacao a 1:10, tirados do MESMO modelo: base do pilar em
    corte e em planta (cotas lidas do envelope da placa no modelo) e o no
    viga-pilar. Pilar do segundo portico, linha A (o primeiro tem os montantes
    do oitao na frente)."""
    r = math.radians
    xb, yb = (xs[1] if len(xs) > 1 else xs[0]), ys[0]
    jan = JANELA_DETALHE_M
    vistas = []
    if placa:
        (px0, py0, pz0), (px1, py1, pz1) = placa
        corte = [((0, py0, pz0 - 0.30), (0, py1, pz0 - 0.30)),
                 ((0, py0 - 0.30, pz0), (0, py0 - 0.30, pz1))]
        planta = [((px0, py0 - 0.30, 0), (px1, py0 - 0.30, 0)),
                  ((px0 - 0.30, py0, 0), (px0 - 0.30, py1, 0))]
        vistas += [
            # camera 1,3 m antes do eixo do pilar, fora do bloco: o corte pelo
            # eixo preenchia de preto a alma do pilar e o bloco inteiro
            ("DET-BASE-ELEVACAO", "ELEVATION_VIEW", (xb - 1.3, yb, 0.15), (r(90), 0, r(-90)),
             jan, jan, 1.90, corte, None, ESCALA_DETALHE,
             [((xb, yb + 0.98, 0.95), "PILAR {{Calc_VerificacaoEstrutural.PerfilAdotado}} - ACO {{Calc_VerificacaoEstrutural.Aco}}", "C"),
              ((xb, yb + 0.98, -0.62), "PLACA DE BASE {{Calc_VerificacaoEstrutural.Descricao}}", "PB"),
              ((xb, yb + 0.98, -0.74), "CHUMBADORES {{Calc_VerificacaoEstrutural.Chumbadores}}", "PB")]),
            ("DET-BASE-PLANTA", "PLAN_VIEW", (xb, yb, pz1 + 0.25), (0, 0, 0),
             jan, jan, 0.60, planta, None, ESCALA_DETALHE,
             [((xb + 0.42, yb + 0.80, 0), "PLACA {{Calc_VerificacaoEstrutural.Descricao}}", "PB"),
              ((xb + 0.42, yb + 0.68, 0), "{{Calc_VerificacaoEstrutural.Chumbadores}}", "PB")]),
        ]
    vistas.append(("DET-JOELHO", "ELEVATION_VIEW", (xb - 0.6, yb + 0.55, alt_col + 0.15),
                   (r(90), 0, r(-90)), jan + 0.4, jan, 1.20, [], None, ESCALA_DETALHE,
                   [((xb, yb + 1.80, alt_col - 0.55), "VIGA {{Calc_VerificacaoEstrutural.PerfilAdotado}}", "V"),
                    ((xb, yb + 1.80, alt_col - 0.67), "PILAR {{Calc_VerificacaoEstrutural.PerfilAdotado}}", "C"),
                    ((xb, yb + 1.80, alt_col - 0.79), "JOELHO: {{Calc_VerificacaoEstrutural.Descricao}}", "MI")]))
    if cumeeira is not None and len(ys) > 1:
        # apice do primeiro vao, no segundo portico: as duas vigas, a chapa de
        # topo e os parafusos, em vista (camera 0,6 m antes do portico)
        y_apice = (ys[0] + ys[1]) / 2.0
        vistas.append(("DET-CUMEEIRA", "ELEVATION_VIEW", (xb - 0.6, y_apice, cumeeira - 0.15),
                       (r(90), 0, r(-90)), jan + 0.4, jan, 1.20, [], None, ESCALA_DETALHE,
                       [((xb, y_apice + 1.20, cumeeira - 0.95), "VIGA {{Calc_VerificacaoEstrutural.PerfilAdotado}}", "V"),
                        ((xb, y_apice + 1.20, cumeeira - 1.07), "CHAPA DE TOPO E PARAFUSOS: "
                         "{{Calc_VerificacaoEstrutural.Descricao}}", "MI")]))
    estrutura = "IfcColumn, IfcBeam, IfcMember, IfcPlate, IfcMechanicalFastener"
    # contraventamento da PAREDE, canto inferior do primeiro vao, visto de fora:
    # na planta da cobertura a chapa de gusset ficava escondida sob a viga
    vistas.append(("DET-CONTRAVENTAMENTO", "ELEVATION_VIEW",
                   (xs[0] + 0.75, ys[0] - 0.6, 0.80), (r(90), 0, 0),
                   jan, jan, 1.20, [], estrutura, ESCALA_DETALHE,
                   [((xs[0] + 0.55, ys[0], 1.55), "CONTRAVENTAMENTO {{Name}}", "CV"),
                    # duas linhas: numa so, a frase passava da janela de 2,2 m e saia
                    # cortada na folha (visto ao abrir o DXF num CAD)
                    ((xs[0] + 0.55, ys[0], 1.43),
                     "GUSSET: {{Calc_VerificacaoEstrutural.Descricao}}", "GC"),
                    ((xs[0] + 0.55, ys[0], 1.33),
                     "SOLDA DE FILETE, PERNA "
                     "{{Calc_VerificacaoEstrutural.SoldaFiletePerna_mm}} mm, TODO O CONTORNO", "GC"),
                    ((xs[0] + 0.75, ys[0], 1.20), "{{Calc_VerificacaoEstrutural.SoldaFiletePerna_mm}}", "GC",
                     SIMBOLO_SOLDA)]))
    for nome, prefixo, rotulo in (("DET-TERCA", "T", "TERCA"), ("DET-LONGARINA", "G", "LONGARINA")):
        alvo = (apoios or {}).get(prefixo)
        if alvo is None:
            continue
        # vista ao longo do comprimento, no segundo portico: a peca em secao
        # sobre a viga (terca) ou sobre o pilar (longarina), com o clipe
        _cx, cy, cz = alvo
        vistas.append((nome, "ELEVATION_VIEW", (xb - 0.6, cy, cz), (r(90), 0, r(-90)),
                       jan * 0.7, jan * 0.7, 1.20, [], estrutura, ESCALA_DETALHE,
                       [((xb, cy + 0.62, cz - 0.55), rotulo + " {{Name}}", prefixo)]))
    return vistas


def _apoio_secundario(tool, prefixo, y_ref, z_ref):
    """Centro (m), no plano do portico, da peca secundaria de marca `prefixo`<n>
    (T = terca, G = longarina) mais proxima do ponto (y_ref, z_ref)."""
    melhor = None
    for el in tool.Ifc.get().by_type("IfcMember"):
        nome = el.Name or ""
        if not (nome.startswith(prefixo) and nome[len(prefixo):].isdigit()):
            continue
        o = tool.Ifc.get_object(el)
        if o is None or o.type != "MESH":
            continue
        pts = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        c = [sum(p[i] for p in pts) / 8.0 for i in range(3)]
        dist = math.hypot(c[1] - y_ref, c[2] - z_ref)
        if melhor is None or dist < melhor[0]:
            melhor = (dist, tuple(c))
    return None if melhor is None else melhor[1]


def _mais_proximo(tool, prefixo, x, y):
    """Elemento IFC cuja marca comeca por `prefixo` (C, V, PB, MI...) e seguida
    so de digitos, mais proximo do eixo do pilar em (x, y)."""
    melhor = None
    for el in tool.Ifc.get().by_type("IfcElement"):
        nome = el.Name or ""
        if not (nome.startswith(prefixo) and nome[len(prefixo):].isdigit()):
            continue
        o = tool.Ifc.get_object(el)
        if o is None or o.type != "MESH":
            continue
        pts = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        cx = sum(p[0] for p in pts) / 8.0
        cy = sum(p[1] for p in pts) / 8.0
        dist = math.hypot(cx - x, cy - y)
        if melhor is None or dist < melhor[0]:
            melhor = (dist, el)
    return None if melhor is None else melhor[1]


SIMBOLO_SOLDA = "solda-filete-contorno"
# Simbolo de solda de FILETE em todo o contorno (mm de papel): linha de
# referencia, seta, circulo de "todo o contorno" na dobra e o triangulo do
# filete ABAIXO da linha (lado da seta), com a perna vertical a esquerda - a
# mesma leitura do glifo do executivo do FreeCAD (`_svg_solda_filete`). O campo
# de texto recebe a perna, lida do elemento.
SVG_SIMBOLO_SOLDA = """
    <g id="%s">
        <path d="M 0,0 L 22,0" style="fill: none; stroke: black; stroke-width: 0.25;" />
        <path d="M 0,0 L -7,7" style="fill: none; stroke: black; stroke-width: 0.25;" />
        <path d="M -7,7 L -4.6,6.2 L -6.2,4.6 Z" style="fill: black; stroke: none;" />
        <circle cx="0" cy="0" r="1.3" style="fill: white; stroke: black; stroke-width: 0.25;" />
        <path d="M 8,0 L 8,5 L 13,0 Z" style="fill: black; stroke: none;" />
        <text x="6.5" y="3" class="regular" text-anchor="end" dominant-baseline="middle" data-type="text-template"></text>
    </g>
""" % SIMBOLO_SOLDA


def garantir_simbolo_de_solda(pasta_assets):
    """Acrescenta o simbolo de solda ao `symbols.svg` do projeto (o Bonsai so
    conhece os simbolos que estao nesse arquivo). Idempotente."""
    caminho = os.path.join(pasta_assets, "symbols.svg")
    txt = open(caminho, encoding="utf-8").read()
    if 'id="%s"' % SIMBOLO_SOLDA in txt:
        return False
    fim = txt.rindex("</svg>")
    open(caminho, "w", encoding="utf-8").write(txt[:fim] + SVG_SIMBOLO_SOLDA + txt[fim:])
    return True


def _texto(tool, desenho, ponto, literal, produto, simbolo=None):
    """Texto de chamada ligado a um elemento do modelo: o `literal` traz
    variaveis `{{Pset.Propriedade}}` que o Bonsai resolve no elemento associado
    ao gerar o desenho. O numero na prancha e' o do IFC, nao texto digitado."""
    import bonsai.bim.module.drawing.annotation as ann
    tipo = "TEXT"
    vista = tool.Drawing.get_drawing_target_view(desenho)
    ctx = (tool.Drawing.get_annotation_context(vista, tipo)
           or tool.Drawing.create_annotation_context(vista, tipo))
    obj = ann.Annotator.get_annotation_obj(
        desenho, tipo, tool.Drawing.get_annotation_data_type(tipo))
    cam = tool.Ifc.get_object(desenho)
    inv = cam.matrix_world.inverted()
    local = inv @ mathutils.Vector(ponto)
    local.z = (inv @ obj.matrix_world.translation).z
    matriz = obj.matrix_world.copy()
    matriz.translation = cam.matrix_world @ local
    obj.matrix_world = matriz
    bpy.context.view_layer.update()
    el = tool.Drawing.run_root_assign_class(
        obj=obj, ifc_class="IfcAnnotation", predefined_type=tipo,
        should_add_representation=True, context=ctx,
        ifc_representation_class=tool.Drawing.get_ifc_representation_class(tipo))
    tool.Ifc.run("group.assign_group",
                 group=tool.Drawing.get_drawing_group(desenho), products=[el])
    tool.Collector.assign(obj, should_clean_users_collection=True)
    tool.Drawing.edit_text_literals(obj, [{"Literal": literal, "BoxAlignment": "bottom-left"}])
    tool.Ifc.run("drawing.assign_product", relating_product=produto, related_object=el)
    if simbolo:
        tool.Drawing.edit_text_symbol(obj, simbolo)
    return el


def _cota(tool, desenho, p1, p2):
    """Cota linear entre dois pontos do MUNDO (m), no plano do desenho."""
    import bonsai.bim.module.drawing.annotation as ann
    tipo = "DIMENSION"
    vista = tool.Drawing.get_drawing_target_view(desenho)
    ctx = (tool.Drawing.get_annotation_context(vista, tipo)
           or tool.Drawing.create_annotation_context(vista, tipo))
    obj = ann.Annotator.get_annotation_obj(
        desenho, tipo, tool.Drawing.get_annotation_data_type(tipo))
    cam = tool.Ifc.get_object(desenho)
    inv = cam.matrix_world.inverted()
    z_plano = (inv @ obj.matrix_world.translation).z
    l1, l2 = inv @ mathutils.Vector(p1), inv @ mathutils.Vector(p2)
    # texto sempre legivel: da esquerda para a direita, de baixo para cima
    if (round(l1.x, 6), round(l1.y, 6)) > (round(l2.x, 6), round(l2.y, 6)):
        l1, l2 = l2, l1
    l1.z = l2.z = z_plano
    ann.Annotator.add_line_to_annotation(obj, cam.matrix_world @ l1, cam.matrix_world @ l2)
    el = tool.Drawing.run_root_assign_class(
        obj=obj, ifc_class="IfcAnnotation", predefined_type=tipo,
        should_add_representation=True, context=ctx,
        ifc_representation_class=tool.Drawing.get_ifc_representation_class(tipo))
    tool.Ifc.run("group.assign_group",
                 group=tool.Drawing.get_drawing_group(desenho), products=[el])
    tool.Collector.assign(obj, should_clean_users_collection=True)
    return el


def vistas_do_galpao(mn, mx, xs, ys, alt_col, cumeeira=None):
    """(nome, tipo, posicao, rotacao, largura, altura, profundidade, cotas, filtro)."""
    c = [(a + b) / 2 for a, b in zip(mn, mx)]
    d = [b - a for a, b in zip(mn, mx)]
    r = math.radians
    x0, x1, y0, y1 = xs[0], xs[-1], ys[0], ys[-1]
    topo = mx[2]
    x_corte = (xs[1] + xs[2]) / 2 if len(xs) > 2 else c[0]
    # as bolhas dos eixos da grade ficam a 2,5 m da ultima linha de pilares e
    # tem ~1,1 m de diametro a 1:100: as cotas passam por fora delas
    planta = ([((a, y0 - 4.2, 0), (b, y0 - 4.2, 0)) for a, b in zip(xs, xs[1:])]
              + [((x0, y0 - 5.2, 0), (x1, y0 - 5.2, 0))]
              + [((x0 - 4.3, a, 0), (x0 - 4.3, b, 0)) for a, b in zip(ys, ys[1:])])
    alto = cumeeira if cumeeira is not None else topo
    corte = [((0, y0, -3.2), (0, y1, -3.2)),
             # a 3,8 m: a marca da elevacao lateral fica a 2,5 m da linha de pilares
             ((0, y0 - 3.8, 0.0), (0, y0 - 3.8, alt_col)),
             ((0, y1 + 3.8, 0.0), (0, y1 + 3.8, alto))]
    larg_x, larg_y, alt = d[0] + MARGEM_M, d[1] + MARGEM_M, d[2] + MARGEM_M
    gerais = [
        ("PLANTA-BAIXA", "PLAN_VIEW", (c[0], c[1], 1.50), (0, 0, 0),
         larg_x, larg_y, 1.50 - mn[2] + 0.2, planta, None),
        ("ELEVACAO-LATERAL", "ELEVATION_VIEW", (c[0], mn[1] - 1.0, c[2]), (r(90), 0, 0),
         larg_x, alt, ys[0] - mn[1] + 1.6, [], None),   # ate passar a linha dos pilares
        ("ELEVACAO-FRONTAL", "ELEVATION_VIEW", (mn[0] - 1.0, c[1], c[2]), (r(90), 0, r(-90)),
         larg_y, alt, xs[0] - mn[0] + 1.6, [], None),
        ("CORTE-TRANSVERSAL", "SECTION_VIEW", (x_corte, c[1], c[2]), (r(90), 0, r(-90)),
         larg_y, alt, 3.5, corte, None),
        # a mesma maquete filtrada por disciplina: consulta do seletor IFC no desenho
        ("PLANTA-FUNDACAO", "PLAN_VIEW", (c[0], c[1], 0.30), (0, 0, 0),
         larg_x, larg_y, 0.30 - mn[2] + 0.2, planta, "IfcFooting, IfcColumn"),
        ("PLANTA-COBERTURA", "PLAN_VIEW", (c[0], c[1], topo + 1.0), (0, 0, 0),
         larg_x, larg_y, topo + 1.0 - alt_col + 0.6, planta, "IfcBeam, IfcMember"),
    ]
    return [v + (ESCALA_GERAL, []) for v in gerais]


def main(ifc_path, so_estas=(), titulo="GALPAO", revisao="00", lista=None):
    rel = {"passos": [], "avisos": [], "cotas": {}, "papel_mm": {},
           "primeira_passada_incompleta": []}

    def passo(nome, fn):
        t = time.time()
        try:
            r = fn()
            rel["passos"].append([nome, "ok", round(time.time() - t, 1)])
            return r
        except Exception:
            rel["passos"].append([nome, "ERRO", round(time.time() - t, 1)])
            rel["avisos"].append("%s: %s" % (nome, traceback.format_exc()[-600:]))

    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.bim.load_project(filepath=ifc_path, use_relative_path=False,
                             should_start_fresh_session=False)
    import bonsai.core.drawing as core
    import bonsai.tool as tool
    import ifcopenshell.api.pset
    ifc = tool.Ifc.get()
    mn, mx = _envelope(tool)
    xs, ys, alt_col = _eixos(ifc)
    cumeeira = _cumeeira(ifc)
    rel["envelope_m"] = [[round(a, 2), round(b, 2)] for a, b in zip(mn, mx)]
    rel["eixos_m"] = {"x": xs, "y": ys, "altura_pilar": alt_col, "cumeeira": cumeeira}
    props = bpy.context.scene.DocProperties
    cena = bpy.context.scene
    feitos = {a.id() for a in ifc.by_type("IfcAnnotation") if a.ObjectType == "DRAWING"}

    xb, yb = (xs[1] if len(xs) > 1 else xs[0]), ys[0]
    todas = (vistas_do_galpao(mn, mx, xs, ys, alt_col, cumeeira)
             + detalhes_do_galpao(
                 xs, ys, alt_col, _placa_de_base(tool, xb, yb), cumeeira,
                 apoios={"T": _apoio_secundario(tool, "T", yb + 3.0, alt_col + 0.5),
                         "G": _apoio_secundario(tool, "G", yb, alt_col * 0.5)}))
    for nome, tipo, pos, rot, larg, alt, prof, cotas, filtro, escala, textos in todas:
        if so_estas and nome not in so_estas:
            continue

        def _vista():
            props.target_view = tipo
            bpy.ops.bim.add_drawing()
            des = [a for a in ifc.by_type("IfcAnnotation")
                   if a.ObjectType == "DRAWING" and a.id() not in feitos][0]
            feitos.add(des.id())
            core.update_drawing_name(tool.Ifc, tool.Drawing, drawing=des, name=nome)
            if filtro:
                ifcopenshell.api.pset.edit_pset(
                    ifc, pset=tool.Pset.get_element_pset(des, "EPset_Drawing"),
                    properties={"Include": filtro})
            if escala == ESCALA_DETALHE:
                # detalhe nao aparece como marca nas vistas gerais
                ifcopenshell.api.pset.edit_pset(
                    ifc, pset=tool.Pset.get_element_pset(des, "EPset_Drawing"),
                    properties={"GlobalReferencing": False})
            bpy.ops.bim.activate_drawing(drawing=des.id(), should_view_from_camera=False)
            cam = cena.camera
            cam.location, cam.rotation_euler = pos, rot
            cp = cam.data.BIMCameraProperties
            cp.diagram_scale = "1:%d|1/%d" % (escala, escala)
            cp.width, cp.height = larg, alt
            cam.data.clip_start, cam.data.clip_end = 0.0, prof
            bpy.context.view_layer.update()
            for o in bpy.context.selected_objects:
                o.select_set(False)
            cam.select_set(True)
            bpy.context.view_layer.objects.active = cam
            bpy.ops.bim.edit_object_placement()
            cena.render.resolution_x, cena.render.resolution_y = cp.raster_x, cp.raster_y
            for p1, p2 in cotas:
                _cota(tool, des, p1, p2)
            for ponto, literal, prefixo, *resto in textos:
                # o texto se liga ao elemento mais proximo do PONTO do texto (o
                # gusset do canto do detalhe, nao o do segundo portico)
                produto = _mais_proximo(tool, prefixo, ponto[0], ponto[1])
                if produto is None:
                    rel["avisos"].append("%s: sem elemento %s* para o texto %r"
                                         % (nome, prefixo, literal))
                    continue
                _texto(tool, des, ponto, literal, produto, *resto)
            rel["cotas"][nome] = len(cotas)
            rel["papel_mm"][nome] = (round(larg * 1000.0 / escala, 1),
                                     round(alt * 1000.0 / escala, 1))
            # PRIMEIRA PASSADA: so interessa o que fica no IFC (camera, cotas e,
            # pelo sync=True, as anotacoes de referencia: eixos da grade, marcas
            # de corte, de elevacao e de nivel). O SVG desta passada e' descartado:
            # as referencias nascem com geometria de comprimento zero ate o IFC ser
            # recarregado, e o Bonsai chega a quebrar ao desenha-las num corte
            # (svgwriter: angle_signed de vetor nulo). A falha aqui e' esperada e
            # fica anotada; quem tem de sair certo e' a segunda passada.
            try:
                bpy.ops.bim.create_drawing(print_all=False, open_viewer=False, sync=True)
            except Exception as exc:
                motivo = [ln for ln in str(exc).splitlines() if "Error" in ln] or [str(exc)]
                rel["primeira_passada_incompleta"].append("%s: %s" % (nome, motivo[-1][:120]))

        passo(nome, _vista)

    def _folhas():
        raiz = os.path.dirname(ifc_path)
        tamanhos = [(n,) + tuple(rel["papel_mm"][n]) for n in ORDEM if n in rel["papel_mm"]]
        # detalhes (1:10) em folha propria, depois das vistas gerais
        gerais = [t for t in tamanhos if not t[0].startswith("DET-")]
        dets = [t for t in tamanhos if t[0].startswith("DET-")]
        plano = distribuir(gerais) + (distribuir(dets) if dets else [])
        props.titleblock = "A1"
        for k, folha in enumerate(plano, 1):
            antes = {sh.ifc_definition_id for sh in props.sheets if sh.is_sheet}
            bpy.ops.bim.add_sheet()
            if k == 1:
                _carimbo_em_portugues(os.path.join(raiz, "layouts", "titleblocks", "A1.svg"))
            bpy.ops.bim.load_sheets()
            bpy.ops.bim.load_drawings()
            for item in props.drawings:
                if not item.is_drawing:
                    item.is_expanded = True
            tool.Drawing.import_drawings()
            # a lista vem ordenada pela identificacao: a folha nova nao e' a ultima
            idx = [i for i, sh in enumerate(props.sheets)
                   if sh.is_sheet and sh.ifc_definition_id not in antes][0]
            props.active_sheet_index = idx
            for nome, _x, _y in folha:
                for i, item in enumerate(props.drawings):
                    if item.is_drawing and item.name == nome:
                        props.active_drawing_index = i
                        bpy.ops.bim.add_drawing_to_sheet()
            nova = tool.Ifc.get().by_id(props.sheets[idx].ifc_definition_id)
            core.rename_sheet(
                tool.Ifc, tool.Drawing, sheet=nova,
                identification="EST-%02d" % k,
                name=("DETALHES DE LIGACAO" if all(n.startswith("DET-") for n, _x, _y in folha)
                      else " / ".join(TITULO_CURTO.get(n, n) for n, _x, _y in folha)))
            tool.Ifc.run("document.edit_information", information=nova,
                         attributes={"Revision": revisao})
        if lista:
            # lista de material: SVG pronto (contado no IFC pelo motor), posto
            # numa folha propria como referencia do projeto
            k = len(plano) + 1
            antes = {sh.ifc_definition_id for sh in props.sheets if sh.is_sheet}
            bpy.ops.bim.add_sheet()
            bpy.ops.bim.load_sheets()
            idx = [i for i, sh in enumerate(props.sheets)
                   if sh.is_sheet and sh.ifc_definition_id not in antes][0]
            props.active_sheet_index = idx
            core.add_document(tool.Ifc, tool.Drawing, "REFERENCE",
                              uri=os.path.relpath(lista, raiz).replace("\\", "/"))
            nome_ref = os.path.splitext(os.path.basename(lista))[0]
            props.active_reference_index = [
                i for i, r in enumerate(props.references) if r.name == nome_ref][0]
            bpy.ops.bim.add_reference_to_sheet()
            nova = tool.Ifc.get().by_id(props.sheets[idx].ifc_definition_id)
            if not [r for r in tool.Drawing.get_document_references(nova)
                    if tool.Drawing.get_reference_description(r) == "REFERENCE"]:
                raise RuntimeError("o Bonsai nao pos a lista de material na folha")
            core.rename_sheet(tool.Ifc, tool.Drawing, sheet=nova,
                              identification="EST-%02d" % k, name="LISTA DE MATERIAL")
            tool.Ifc.run("document.edit_information", information=nova,
                         attributes={"Revision": revisao})
            rel["folha_da_lista"] = "EST-%02d" % k
        posicoes = {n: (x, y) for folha in plano for n, x, y in folha}
        rel["reposicionados"] = _reposicionar(os.path.join(raiz, "layouts"), posicoes)
        bpy.ops.bim.load_sheets()
        bpy.ops.bim.create_sheets(create_all=True, open_viewer=False)
        rel["folhas"] = [[n for n, _x, _y in folha] for folha in plano]

    passo("salvar IFC", lambda: bpy.ops.bim.save_project(filepath=ifc_path,
                                                         should_save_as=False))

    def _segunda_passada():
        """Recarrega o IFC salvo e gera os desenhos: medido, as anotacoes de
        referencia criadas na primeira passada (25 eixos no galpao de 20 x 28,5
        m) so aparecem no SVG numa sessao que ja abre com elas."""
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o)
        bpy.ops.bim.load_project(filepath=ifc_path, use_relative_path=False,
                                 should_start_fresh_session=False)
        novo = tool.Ifc.get()
        cena2 = bpy.context.scene
        garantir_simbolo_de_solda(os.path.join(os.path.dirname(ifc_path), "drawings", "assets"))
        feitos2 = 0
        for des in novo.by_type("IfcAnnotation"):
            if des.ObjectType != "DRAWING" or des.Name not in rel["cotas"]:
                continue
            bpy.ops.bim.activate_drawing(drawing=des.id(), should_view_from_camera=False)
            cp = cena2.camera.data.BIMCameraProperties
            cena2.render.resolution_x, cena2.render.resolution_y = cp.raster_x, cp.raster_y
            bpy.ops.bim.create_drawing(print_all=False, open_viewer=False)
            feitos2 += 1
        pasta = os.path.join(os.path.dirname(ifc_path), "drawings")
        rel["pontas_puxadas"] = {
            a[:-4]: puxar_para_dentro(os.path.join(pasta, a))
            for a in sorted(os.listdir(pasta)) if a.lower().endswith(".svg")}
        return feitos2

    rel["segunda_passada"] = passo("segunda passada", _segunda_passada)
    props = bpy.context.scene.DocProperties          # a sessao foi recarregada
    passo("folhas A1", _folhas)
    passo("salvar IFC com as folhas", lambda: bpy.ops.bim.save_project(
        filepath=ifc_path, should_save_as=False))
    raiz = os.path.dirname(ifc_path)
    rel["arquivos"] = sorted(
        os.path.relpath(os.path.join(b, x), raiz).replace("\\", "/")
        for b, _d, fs in os.walk(raiz) for x in fs
        if "assets" not in b and "cache" not in b and "titleblocks" not in b)
    if not rel["avisos"]:
        del rel["avisos"]
    print("RELATORIO_JSON " + json.dumps(rel, ensure_ascii=False))


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    opcoes = dict(a.split("=", 1) for a in args[1:] if "=" in a)
    main(args[0], tuple(a for a in args[1:] if "=" not in a),
         titulo=opcoes.get("titulo", "GALPAO"), revisao=opcoes.get("revisao", "00"),
         lista=opcoes.get("lista"))
