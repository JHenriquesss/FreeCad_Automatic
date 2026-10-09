# ============================================================================
# ambientes_ifc.py - AMBIENTES LIDOS DE UM MODELO IFC (plano de 2026-10-08, Fase
# 5, quinto passo). Mesmo contrato do leitor de planta DXF: sai o AMBIENTE
# abstrato (nome, tipo, area, perimetro), o poligono de cada um e a posicao do
# quadro; quem calcula e' o motor que ja existe.
#
# DE ONDE VEM CADA DADO
#   - ambiente: cada IfcSpace do pavimento;
#   - nome: o Name do IfcSpace (se vazio, o LongName);
#   - tipo: ObjectType, senao LongName, senao Name, passado pelo normalizador
#     de quem chama (o mesmo do leitor de DXF);
#   - area, perimetro e poligono: da GEOMETRIA do IfcSpace (a face de baixo do
#     solido), nao das quantidades escritas no arquivo. Se o arquivo traz a
#     quantidade de area e ela diverge da geometria, e' erro nomeado: rotulo e
#     geometria discordando nao se resolve escolhendo um;
#   - quadro: o unico IfcElectricDistributionBoard do modelo, se houver.
#
# O QUE VIRA ERRO NOMEADO EM VEZ DE PALPITE: IfcSpace sem geometria, piso com
# vazio (pegada em mais de um contorno), ambientes em mais de um pavimento sem
# o pavimento ser escolhido, mais de um quadro.
#
# Biblioteca: quem a chama pela linha de comando e' o ambientes_dxf (que aceita
# arquivo .ifc no lugar da planta).
# ============================================================================
"""Ambientes (tipo, area, perimetro, poligono) lidos dos IfcSpace de um IFC."""

from __future__ import annotations

# rotulo (quantidade escrita no IFC) x geometria: tolerancia relativa da conferencia
TOL_AREA_REL = 0.01
QUANTIDADES_DE_AREA = ("NetFloorArea", "GrossFloorArea")
# faces de baixo: triangulos com todos os vertices a menos disto do z minimo (m)
TOL_Z_M = 1e-4


def _pegada(verts, faces):
    """Contornos (listas de (x, y)) da face de baixo de um solido triangulado."""
    zmin = min(v[2] for v in verts)
    contagem = {}
    for a, b, c in faces:
        if max(verts[a][2], verts[b][2], verts[c][2]) - zmin > TOL_Z_M:
            continue
        for i, j in ((a, b), (b, c), (c, a)):
            chave = (min(i, j), max(i, j))
            contagem[chave] = contagem[chave] + 1 if chave in contagem else 1
    vizinhos = {}
    for (i, j), n in contagem.items():
        if n == 1:                                     # aresta de borda
            vizinhos.setdefault(i, []).append(j)
            vizinhos.setdefault(j, []).append(i)
    contornos, vistos = [], set()
    for inicio in sorted(vizinhos):
        if inicio in vistos:
            continue
        laco, anterior, atual = [inicio], None, inicio
        while True:
            vistos.add(atual)
            proximos = [v for v in vizinhos[atual] if v != anterior]
            if not proximos or proximos[0] == inicio:
                break
            anterior, atual = atual, proximos[0]
            if atual in vistos:
                break
            laco.append(atual)
        contornos.append([(verts[i][0], verts[i][1]) for i in laco])
    return contornos


def _sem_colineares(pts):
    """Tira os vertices que a triangulacao poe no meio de um lado reto."""
    saida = []
    n = len(pts)
    for k in range(n):
        (x0, y0), (x1, y1), (x2, y2) = pts[k - 1], pts[k], pts[(k + 1) % n]
        if abs((x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1)) > 1e-9:
            saida.append(pts[k])
    return saida


def _area_e_perimetro(pts):
    area2 = perim = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        area2 += x0 * y1 - x1 * y0
        perim += ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    return abs(area2) / 2.0, perim


def _quantidade_de_area(espaco, escala_area):
    """Area escrita no arquivo (m2), ou None."""
    import ifcopenshell.util.element as ue

    for _conjunto, props in ue.get_psets(espaco, qtos_only=True).items():
        for nome in QUANTIDADES_DE_AREA:
            if nome in props and isinstance(props[nome], (int, float)):
                return float(props[nome]) * escala_area
    return None


def _pavimento(espaco):
    import ifcopenshell.util.element as ue

    pai = ue.get_aggregate(espaco) or ue.get_container(espaco)
    return pai.Name if pai is not None and pai.is_a("IfcBuildingStorey") else None


def ler_ambientes(caminho, normaliza, pavimento=None):
    """{ambientes: [{nome, tipo, area_m2, perimetro_m}], geometria: {nome:
    [[x_m, y_m], ...]}, quadro_m, pavimento, erros}. `normaliza` leva o texto
    do tipo ao formato do motor; `pavimento` escolhe o andar quando ha
    ambientes em mais de um."""
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.unit as uu

    modelo = ifcopenshell.open(caminho)
    escala = uu.calculate_unit_scale(modelo)           # unidade do arquivo -> metros
    erros = []
    espacos = [(e, _pavimento(e)) for e in modelo.by_type("IfcSpace")]
    andares = sorted({p for _e, p in espacos if p is not None})
    if pavimento is None and len(andares) > 1:
        erros.append({"code": "varios_pavimentos", "pavimentos": andares,
                      "detail": "ha ambientes em mais de um pavimento; escolha um"})
        espacos = []
    elif pavimento is not None:
        if pavimento not in andares:
            erros.append({"code": "pavimento_desconhecido", "pavimento": pavimento,
                          "pavimentos": andares,
                          "detail": "o pavimento pedido nao tem ambientes no modelo"})
        espacos = [(e, p) for e, p in espacos if p == pavimento]

    ajustes = ifcopenshell.geom.settings()
    ajustes.set("use-world-coords", True)
    ambientes, geometria = [], {}
    for espaco, _andar in espacos:
        nome = (espaco.Name or espaco.LongName or "").strip()
        rotulo = (espaco.ObjectType or espaco.LongName or espaco.Name or "").strip()
        if not nome or not rotulo:
            erros.append({"code": "ambiente_sem_nome", "guid": espaco.GlobalId,
                          "detail": "IfcSpace sem Name nem LongName"})
            continue
        if espaco.Representation is None:
            erros.append({"code": "ambiente_sem_geometria", "ambiente": nome,
                          "detail": "IfcSpace sem representacao: area nao pode ser lida"})
            continue
        try:
            forma = ifcopenshell.geom.create_shape(ajustes, espaco)
        except RuntimeError as exc:
            erros.append({"code": "ambiente_sem_geometria", "ambiente": nome,
                          "detail": "geometria nao processada: %s" % exc})
            continue
        v, f = forma.geometry.verts, forma.geometry.faces
        verts = [(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v), 3)]
        faces = [(f[i], f[i + 1], f[i + 2]) for i in range(0, len(f), 3)]
        contornos = _pegada(verts, faces)
        if len(contornos) != 1:
            erros.append({"code": "ambiente_com_vazio" if len(contornos) > 1
                          else "ambiente_sem_geometria", "ambiente": nome,
                          "n_contornos": len(contornos),
                          "detail": "a face de baixo do ambiente tem de ter um contorno so"})
            continue
        pts = _sem_colineares(contornos[0])
        area, perim = _area_e_perimetro(pts)
        escrita = _quantidade_de_area(espaco, escala * escala)
        if escrita is not None and abs(escrita - area) > TOL_AREA_REL * area:
            erros.append({"code": "area_diverge_da_quantidade", "ambiente": nome,
                          "area_geometria_m2": round(area, 4),
                          "area_escrita_m2": round(escrita, 4),
                          "detail": "a quantidade de area do arquivo nao bate com a "
                                    "geometria do ambiente"})
            continue
        ambientes.append({"nome": nome, "tipo": normaliza(rotulo),
                          "area_m2": round(area, 4), "perimetro_m": round(perim, 4)})
        geometria[nome] = [[round(x, 4), round(y, 4)] for x, y in pts]

    quadro = None
    quadros = modelo.by_type("IfcElectricDistributionBoard")
    if len(quadros) > 1:
        erros.append({"code": "varios_quadros", "n": len(quadros),
                      "detail": "o modelo tem de ter UM quadro de distribuicao"})
    elif quadros:
        import ifcopenshell.util.placement as up

        m = up.get_local_placement(quadros[0].ObjectPlacement)
        quadro = [round(float(m[0, 3]) * escala, 4), round(float(m[1, 3]) * escala, 4)]
    return {"ambientes": ambientes, "erros": erros, "geometria": geometria,
            "quadro_m": quadro, "pavimento": pavimento,
            "pavimentos": andares, "metros_por_unidade": 1.0}


def previsao_de_cargas(caminho, normaliza, pavimento=None):
    """Le os ambientes do IFC e roda o motor de previsao de carga. Erro de
    leitura impede o ATENDE, como no leitor de DXF."""
    import arquitetura_residencial as AR

    lido = ler_ambientes(caminho, normaliza, pavimento)
    resultado = AR.rodar({"ambientes": lido["ambientes"]})
    # mesma chave do leitor de DXF: e' o que a divisao e o comprimento leem
    resultado["leitura_dxf"] = {"arquivo": caminho, "origem": "ifc",
                                "pavimento": lido["pavimento"],
                                "metros_por_unidade": lido["metros_por_unidade"],
                                "geometria": lido["geometria"],
                                "quadro_m": lido["quadro_m"], "erros": lido["erros"]}
    if lido["erros"]:
        resultado["ATENDE"] = False
    return resultado
