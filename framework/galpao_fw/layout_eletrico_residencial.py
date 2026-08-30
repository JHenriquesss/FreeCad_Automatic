"""Contrato de LAYOUT da instalação elétrica residencial (entrada de geometria).

O dimensionamento (`dimensionamento_eletrico_residencial`) não conhece
coordenadas: ele calcula sobre comprimentos declarados. Já os entregáveis
gráficos (planta 2D) e o BIM (IFC) precisam de POSIÇÃO. Este módulo valida a
seção opcional ``circuits.layout`` sem inventar nada:

- se o layout não for declarado, o resultado é ``declared=False`` e os
  entregáveis geométricos ficam indisponíveis com motivo explícito;
- se for declarado, ele precisa estar completo e coerente — cada ponto de
  circuito tem uma e somente uma posição, e a posição precisa cair DENTRO do
  cômodo que o próprio ponto declara (rótulo × geometria).

Nenhuma função aqui desenha ou emite arquivo.
"""

from __future__ import annotations

import copy
import math


_ROOM_FIELDS = ("id", "name", "x_m", "y_m", "width_m", "depth_m")
_POINT_FIELDS = ("id", "x_m", "y_m", "z_m")
_BOARD_FIELDS = ("id", "x_m", "y_m", "z_m")


def _error(code, **context):
    error = {"code": code}
    if context:
        error.update(context)
    return error


def _finite(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(float(value)))


def _finite_positive(value):
    return _finite(value) and float(value) > 0.0


def _non_empty_str(value):
    return type(value) is str and bool(value.strip())


def layout_declared(circuits) -> bool:
    """True se a seção de layout existir na entrada (mesmo que inválida)."""
    return isinstance(circuits, dict) and "layout" in circuits


def validate_electrical_layout(circuits) -> dict:
    """Valida ``circuits.layout`` contra os pontos declarados.

    Retorna ``{"declared", "ok", "errors", "layout"}``. ``layout`` só vem
    preenchido quando ``ok`` é verdadeiro; nunca há valor inventado.
    """
    if not isinstance(circuits, dict) or "layout" not in circuits:
        return {"declared": False, "ok": False, "errors": [], "layout": None}

    layout = circuits["layout"]
    if not isinstance(layout, dict):
        return {"declared": True, "ok": False, "layout": None,
                "errors": [_error("invalid_layout",
                                  detail="circuits.layout deve ser um objeto")]}

    errors: list[dict] = []
    if layout.get("units") != "m":
        errors.append(_error("invalid_layout_value", field="units",
                             detail="layout.units deve ser metro"))

    rooms = _validate_rooms(layout, errors)
    board = _validate_board(layout, errors)
    positions = _validate_points(layout, errors)
    _cross_check_points(circuits, rooms, positions, errors)
    _cross_check_board(rooms, board, errors)

    if errors:
        return {"declared": True, "ok": False, "errors": errors, "layout": None}
    return {
        "declared": True,
        "ok": True,
        "errors": [],
        "layout": {
            "units": "m",
            "board": copy.deepcopy(board),
            "rooms": copy.deepcopy(list(rooms.values())),
            "points": copy.deepcopy(list(positions.values())),
        },
    }


def _validate_rooms(layout, errors):
    rooms_raw = layout.get("rooms")
    if not isinstance(rooms_raw, list) or not rooms_raw:
        errors.append(_error("missing_layout_field", field="rooms",
                             detail="layout.rooms deve ser uma lista nao vazia"))
        return {}
    rooms: dict[str, dict] = {}
    for index, room in enumerate(rooms_raw):
        if not isinstance(room, dict):
            errors.append(_error("invalid_layout_value", field="rooms", index=index))
            continue
        missing = [field for field in _ROOM_FIELDS if field not in room]
        if missing:
            errors.append(_error("missing_layout_field", field="rooms",
                                 index=index, missing=sorted(missing)))
            continue
        room_id = room["id"]
        if not _non_empty_str(room_id) or not _non_empty_str(room["name"]):
            errors.append(_error("invalid_layout_value", field="rooms.id", index=index))
            continue
        if not (_finite(room["x_m"]) and _finite(room["y_m"])
                and _finite_positive(room["width_m"])
                and _finite_positive(room["depth_m"])):
            errors.append(_error("invalid_layout_value", field="rooms.geometry",
                                 index=index, room=room_id))
            continue
        if room_id in rooms:
            errors.append(_error("duplicate_layout_room", room=room_id))
            continue
        rooms[room_id] = {field: room[field] for field in _ROOM_FIELDS}
    _reject_overlaps(rooms, errors)
    return rooms


def _reject_overlaps(rooms, errors):
    """Dois cômodos não podem ocupar a mesma área: seria planta impossível."""
    items = list(rooms.values())
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            overlap_x = (min(a["x_m"] + a["width_m"], b["x_m"] + b["width_m"])
                         - max(a["x_m"], b["x_m"]))
            overlap_y = (min(a["y_m"] + a["depth_m"], b["y_m"] + b["depth_m"])
                         - max(a["y_m"], b["y_m"]))
            if overlap_x > 1e-9 and overlap_y > 1e-9:
                errors.append(_error("overlapping_layout_rooms",
                                     rooms=sorted([a["id"], b["id"]])))


def _validate_board(layout, errors):
    board = layout.get("board")
    if not isinstance(board, dict):
        errors.append(_error("missing_layout_field", field="board",
                             detail="layout.board deve ser um objeto"))
        return None
    missing = [field for field in _BOARD_FIELDS if field not in board]
    if missing:
        errors.append(_error("missing_layout_field", field="board",
                             missing=sorted(missing)))
        return None
    if not _non_empty_str(board["id"]):
        errors.append(_error("invalid_layout_value", field="board.id"))
        return None
    if not all(_finite(board[field]) for field in ("x_m", "y_m", "z_m")):
        errors.append(_error("invalid_layout_value", field="board.position"))
        return None
    if float(board["z_m"]) <= 0.0:
        errors.append(_error("invalid_layout_value", field="board.z_m",
                             detail="quadro deve estar acima do piso"))
        return None
    return {field: board[field] for field in _BOARD_FIELDS}


def _validate_points(layout, errors):
    points_raw = layout.get("points")
    if not isinstance(points_raw, list) or not points_raw:
        errors.append(_error("missing_layout_field", field="points",
                             detail="layout.points deve ser uma lista nao vazia"))
        return {}
    positions: dict[str, dict] = {}
    for index, point in enumerate(points_raw):
        if not isinstance(point, dict):
            errors.append(_error("invalid_layout_value", field="points", index=index))
            continue
        missing = [field for field in _POINT_FIELDS if field not in point]
        if missing:
            errors.append(_error("missing_layout_field", field="points",
                                 index=index, missing=sorted(missing)))
            continue
        point_id = point["id"]
        if not _non_empty_str(point_id):
            errors.append(_error("invalid_layout_value", field="points.id", index=index))
            continue
        if not all(_finite(point[field]) for field in ("x_m", "y_m", "z_m")):
            errors.append(_error("invalid_layout_value", field="points.position",
                                 point=point_id))
            continue
        if float(point["z_m"]) < 0.0:
            errors.append(_error("invalid_layout_value", field="points.z_m",
                                 point=point_id))
            continue
        if point_id in positions:
            errors.append(_error("duplicate_layout_point", point=point_id))
            continue
        positions[point_id] = {field: point[field] for field in _POINT_FIELDS}
    return positions


def _cross_check_points(circuits, rooms, positions, errors):
    """Cada ponto declarado tem posição, e a posição cai no cômodo declarado."""
    declared = circuits.get("points")
    if not isinstance(declared, list):
        return
    known: set[str] = set()
    for point in declared:
        if not isinstance(point, dict) or not _non_empty_str(point.get("id")):
            continue
        point_id = point["id"]
        known.add(point_id)
        position = positions.get(point_id)
        if position is None:
            errors.append(_error("missing_layout_point", point=point_id))
            continue
        room_id = point.get("room")
        if not _non_empty_str(room_id):
            continue
        room = rooms.get(room_id)
        if room is None:
            if rooms:
                errors.append(_error("unknown_layout_room", point=point_id,
                                     room=room_id))
            continue
        if not _inside(room, position["x_m"], position["y_m"]):
            errors.append(_error("point_outside_declared_room", point=point_id,
                                 room=room_id,
                                 position=[position["x_m"], position["y_m"]]))
    for point_id in positions:
        if point_id not in known:
            errors.append(_error("unknown_layout_point", point=point_id))


def _cross_check_board(rooms, board, errors):
    if board is None or not rooms:
        return
    if not any(_inside(room, board["x_m"], board["y_m"]) for room in rooms.values()):
        errors.append(_error("board_outside_declared_rooms", board=board["id"],
                             position=[board["x_m"], board["y_m"]]))


def _inside(room, x, y):
    return (room["x_m"] - 1e-9 <= x <= room["x_m"] + room["width_m"] + 1e-9
            and room["y_m"] - 1e-9 <= y <= room["y_m"] + room["depth_m"] + 1e-9)


def bounds(layout) -> dict:
    """Retângulo envolvente dos cômodos declarados (m). Só para enquadramento."""
    rooms = layout["rooms"]
    return {
        "x_min": min(room["x_m"] for room in rooms),
        "y_min": min(room["y_m"] for room in rooms),
        "x_max": max(room["x_m"] + room["width_m"] for room in rooms),
        "y_max": max(room["y_m"] + room["depth_m"] for room in rooms),
    }
