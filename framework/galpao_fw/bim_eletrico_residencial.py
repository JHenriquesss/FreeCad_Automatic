"""BIM (IFC4) da instalação elétrica residencial, puro-Python via `ifc_emit`.

Converte o resultado validado do adaptador residencial + o layout declarado em
membros do modelo neutro (`ifc_emit.emitir_ifc`): quadro de distribuição,
luminárias, tomadas e os condutores de cada circuito. Não calcula seção nem
proteção — só posiciona o que já foi dimensionado.

Convenções do modelo neutro (iguais aos demais verticais): coordenadas em mm;
seção de barra em metros; caixa (`dims`) em mm.

Checagem RÓTULO × GEOMETRIA: o comprimento declarado do circuito
(`declared_length_m`, a entrada do dimensionamento) é comparado com a distância
3D quadro→ponto do layout. Se a distância já é maior que o comprimento
declarado, o comprimento usado no cálculo de queda de tensão é fisicamente
impossível para essa planta, e isso vira aviso explícito.
"""

from __future__ import annotations

import math


MM = 1000.0
_CAIXA_QUADRO_MM = (400.0, 120.0, 500.0)
_CAIXA_LUMINARIA_MM = (200.0, 200.0, 80.0)
_CAIXA_TOMADA_MM = (80.0, 40.0, 80.0)
_COBRE = "Cobre"


def _layout(result):
    circuits = (result or {}).get("circuits") or {}
    validacao = circuits.get("layout_validation")
    if isinstance(validacao, dict) and validacao.get("ok"):
        return validacao["layout"]
    return None


def _designs(result):
    circuits = (result or {}).get("circuits") or {}
    designs = circuits.get("designs")
    return list(designs) if isinstance(designs, list) else []


def _points_by_id(result):
    circuits = (result or {}).get("circuits") or {}
    points = circuits.get("points")
    if not isinstance(points, list):
        return {}
    return {point["id"]: point for point in points
            if isinstance(point, dict) and isinstance(point.get("id"), str)}


def _diametro_equivalente_m(secao_mm2):
    """Diâmetro do condutor equivalente à seção calculada (m, p/ o perfil IFC)."""
    if not isinstance(secao_mm2, (int, float)) or isinstance(secao_mm2, bool):
        return None
    if float(secao_mm2) <= 0.0:
        return None
    return 2.0 * math.sqrt(float(secao_mm2) / math.pi) / MM


def membros_bim(result):
    """Modelo neutro dos elementos físicos da instalação residencial.

    Retorna lista vazia quando não há layout válido — sem posição declarada não
    existe elemento BIM honesto a emitir.
    """
    layout = _layout(result)
    if layout is None:
        return []
    pontos = _points_by_id(result)
    posicoes = {item["id"]: item for item in layout["points"]}
    quadro = layout["board"]
    qx, qy, qz = (quadro["x_m"] * MM, quadro["y_m"] * MM, quadro["z_m"] * MM)

    membros = [{
        "tipo": "Board",
        "perfil": "Quadro de distribuição",
        "marca": quadro["id"],
        "dims": list(_CAIXA_QUADRO_MM),
        "centro": [qx, qy, qz],
        "material": "Aco",
    }]

    for point_id, posicao in posicoes.items():
        kind = pontos.get(point_id, {}).get("kind")
        px, py, pz = (posicao["x_m"] * MM, posicao["y_m"] * MM, posicao["z_m"] * MM)
        if kind == "lighting":
            membros.append({"tipo": "Luminaire", "perfil": "Ponto de luz",
                            "marca": point_id, "dims": list(_CAIXA_LUMINARIA_MM),
                            "centro": [px, py, pz], "material": "Policarbonato"})
        else:
            membros.append({"tipo": "Outlet", "perfil": "Tomada",
                            "marca": point_id, "dims": list(_CAIXA_TOMADA_MM),
                            "centro": [px, py, pz], "material": "Termoplastico"})

    for design in _designs(result):
        secao = (design.get("conductor") or {}).get("secao_mm2")
        diametro = _diametro_equivalente_m(secao)
        if diametro is None:
            continue
        for ordem, point_id in enumerate(design["point_ids"], 1):
            posicao = posicoes.get(point_id)
            if posicao is None:
                continue
            destino = [posicao["x_m"] * MM, posicao["y_m"] * MM,
                       posicao["z_m"] * MM]
            if _distancia([qx, qy, qz], destino) <= 0.0:
                continue
            membros.append({
                "tipo": "Cable",
                "perfil": "Condutor %g mm2" % float(secao),
                "marca": "%s-%d" % (design["id"], ordem),
                "secao": {"forma": "ROUND", "D": diametro},
                "p1": [qx, qy, qz],
                "p2": destino,
                "material": _COBRE,
            })
    return membros


def _distancia(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def verificar_comprimentos(result, tolerancia_m=0.0):
    """RÓTULO × GEOMETRIA: comprimento declarado × distância real do layout.

    A distância reta quadro→ponto é o MÍNIMO fisicamente possível para o ramal.
    Se o comprimento declarado (usado na queda de tensão) for menor que esse
    mínimo, o cálculo está otimista e o aviso precisa aparecer.
    """
    layout = _layout(result)
    if layout is None:
        return []
    posicoes = {item["id"]: item for item in layout["points"]}
    quadro = layout["board"]
    origem = [quadro["x_m"], quadro["y_m"], quadro["z_m"]]
    avisos = []
    for design in _designs(result):
        declarado = design.get("declared_length_m")
        if not isinstance(declarado, (int, float)) or isinstance(declarado, bool):
            continue
        maior = 0.0
        ponto_critico = None
        for point_id in design["point_ids"]:
            posicao = posicoes.get(point_id)
            if posicao is None:
                continue
            distancia = _distancia(origem, [posicao["x_m"], posicao["y_m"],
                                            posicao["z_m"]])
            if distancia > maior:
                maior, ponto_critico = distancia, point_id
        if ponto_critico is None:
            continue
        if maior > float(declarado) + tolerancia_m:
            avisos.append({
                "code": "declared_length_shorter_than_layout_distance",
                "design_id": design["id"],
                "point": ponto_critico,
                "declared_length_m": float(declarado),
                "layout_distance_m": maior,
            })
    return avisos


def emitir_bim(result, path, nome="CasaResidencialEletrica"):
    """Escreve o IFC4 da instalação residencial. None se não houver o que emitir."""
    import ifc_emit

    if not ifc_emit.disponivel():
        return None
    membros = membros_bim(result)
    if not membros:
        return None
    return ifc_emit.emitir_ifc(membros, path, nome=nome, secao_em_metros=True)
