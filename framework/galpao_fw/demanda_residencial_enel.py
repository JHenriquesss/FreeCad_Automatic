"""Cálculo auditável da demanda residencial BT segundo a base WKI/Enel.

Este módulo é deliberadamente puro: não conhece FreeCAD, o orquestrador nem
qualquer adaptador de tipologia. Entradas incompletas ou fora das tabelas são
erros estruturados, nunca valores padrão silenciosos.
"""

from __future__ import annotations

from numbers import Real
from typing import Any


ROOM_MODULES_KVA = {
    "quarto": 1.50,
    "sala": 1.60,
    "banheiro": 2.30,
    "cozinha_1": 1.50,
    "cozinha_2": 2.10,
    "area_servico": 1.90,
    "outros": 0.35,
}

LOCATION_FACTORS = (1.00, 0.88, 0.75, 0.55)

# WKI - Tabela 1: (quantidade mínima, fator <= 3,5 kW, fator > 3,5 kW).
_HEATING_TABLE = (
    (1, 80.0, 80.0),
    (2, 75.0, 65.0),
    (3, 70.0, 55.0),
    (4, 66.0, 50.0),
    (5, 62.0, 45.0),
    (6, 59.0, 43.0),
    (7, 56.0, 40.0),
    (8, 53.0, 36.0),
    (9, 51.0, 35.0),
    (10, 49.0, 34.0),
    (11, 47.0, 32.0),
    (12, 45.0, 32.0),
    (13, 43.0, 32.0),
    (14, 41.0, 32.0),
    (15, 40.0, 32.0),
    (16, 39.0, 28.0),
    (17, 38.0, 28.0),
    (18, 37.0, 28.0),
    (19, 36.0, 28.0),
    (20, 35.0, 28.0),
    (21, 34.0, 26.0),
    (22, 33.0, 26.0),
    (23, 32.0, 26.0),
    (24, 31.0, 26.0),
    (25, 30.0, 26.0),
    (26, 30.0, 24.0),
    (31, 30.0, 22.0),
    (41, 30.0, 20.0),
    (51, 30.0, 18.0),
    (61, 30.0, 16.0),
)

# WKI motor table: somente a combinação prevista no contrato desta primeira
# fatia foi liberada. Combinações sem linha exata devem ser revisadas, não
# interpoladas.
_MOTOR_TABLE_KVA = {
    ("trifasica", 1.0, 1): 1.52,
}


def calculate_residential_demand(payload: dict[str, Any]) -> dict[str, Any]:
    """Calcula a demanda residencial e retorna um envelope estável e auditável."""
    errors = _validate_payload(payload)
    if errors:
        return {"ok": False, "errors": errors, "warnings": [], "calculation": {}}

    location_factor = float(payload["network"]["location_factor"])
    rooms = _calculate_rooms(payload["rooms"], location_factor)
    try:
        heating = _calculate_heating(payload["loads"]["heating"])
        motors = _calculate_motors(payload["loads"]["motors"])
        special = _calculate_special_lighting(payload["loads"]["special_lighting"])
    except ValueError as exc:
        return {"ok": False, "errors": [_error("invalid_load", str(exc))],
                "warnings": [], "calculation": {}}
    errors = motors.pop("errors", [])
    return _compose_result(rooms, heating, motors, special, errors, location_factor)


def _is_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def _error(code: str, message: str, **context: Any) -> dict[str, Any]:
    result = {"code": code, "message": message}
    if context:
        result["context"] = context
    return result


def _validate_payload(payload: Any) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return [_error("invalid_payload", "payload deve ser um objeto")]

    network = payload.get("network")
    rooms = payload.get("rooms")
    loads = payload.get("loads")
    if not isinstance(network, dict):
        errors.append(_error("missing_network", "network deve ser informado"))
    elif "location_factor" not in network:
        errors.append(_error("missing_location_factor", "fator locacional é obrigatório"))
    elif network["location_factor"] not in LOCATION_FACTORS:
        errors.append(_error("invalid_location_factor", "fator locacional fora da tabela",
                             value=network["location_factor"]))

    if not isinstance(rooms, dict):
        errors.append(_error("missing_rooms", "rooms deve ser informado"))
    else:
        for name, count in rooms.items():
            if name not in {"quarto", "sala", "banheiro", "cozinha", "area_servico", "outros"}:
                errors.append(_error("unknown_room", "cômodo fora do contrato", room=name))
            elif not isinstance(count, int) or isinstance(count, bool) or count < 0:
                errors.append(_error("invalid_room_count", "quantidade de cômodo deve ser inteiro não negativo",
                                     room=name, value=count))

    if not isinstance(loads, dict):
        errors.append(_error("missing_loads", "loads deve ser informado"))
    else:
        for key in ("heating", "motors", "special_lighting"):
            if not isinstance(loads.get(key), list):
                errors.append(_error("invalid_load_group", "grupo de cargas deve ser uma lista", group=key))
    return errors


def _calculate_rooms(rooms: dict[str, int], location_factor: float) -> dict[str, Any]:
    bedrooms = rooms.get("quarto", 0)
    kitchen_module = 1.50 if bedrooms <= 2 else 2.10
    modules = {
        "quarto": bedrooms * ROOM_MODULES_KVA["quarto"],
        "sala": rooms.get("sala", 0) * ROOM_MODULES_KVA["sala"],
        "banheiro": rooms.get("banheiro", 0) * ROOM_MODULES_KVA["banheiro"],
        "cozinha": rooms.get("cozinha", 0) * kitchen_module,
        "area_servico": rooms.get("area_servico", 0) * ROOM_MODULES_KVA["area_servico"],
        "outros": rooms.get("outros", 0) * ROOM_MODULES_KVA["outros"],
    }
    subtotal = sum(modules.values())
    divisor = 1.40 if bedrooms == 1 else 1.20
    return {
        "modules_kva": modules,
        "kitchen_module": kitchen_module,
        "subtotal_kva": subtotal,
        "diversity_divisor": divisor,
        "demand_kva": (subtotal / divisor) * location_factor,
    }


def _heating_factor(quantity: int, power_kw: float) -> float:
    for minimum, low, high in _HEATING_TABLE:
        if quantity < minimum:
            break
        factor = high if power_kw > 3.5 else low
    return factor


def _calculate_heating(items: list[dict[str, Any]]) -> dict[str, Any]:
    result_items = []
    installed = 0.0
    demand = 0.0
    for index, item in enumerate(items):
        quantity = item.get("quantity")
        power_kw = item.get("power_kw")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise ValueError(f"heating[{index}].quantity inválido")
        if not _is_number(power_kw) or power_kw <= 0:
            raise ValueError(f"heating[{index}].power_kw inválido")
        factor = _heating_factor(quantity, float(power_kw))
        item_demand = quantity * float(power_kw) * factor / 100.0
        installed += quantity * float(power_kw)
        demand += item_demand
        result_items.append({"quantity": quantity, "power_kw": float(power_kw),
                             "factor_percent": factor, "demand_kw": item_demand})
    return {"items": result_items, "installed_kw": installed, "demand_kw": demand}


def _calculate_motors(items: list[dict[str, Any]]) -> dict[str, Any]:
    result_items = []
    errors = []
    installed = 0.0
    demand = 0.0
    for index, item in enumerate(items):
        quantity = item.get("quantity")
        power_cv = item.get("power_cv")
        connection = item.get("connection")
        key = (connection, power_cv, quantity)
        value = _MOTOR_TABLE_KVA.get(key)
        if value is None:
            errors.append(_error("motor_outside_table", "combinação de motor sem linha exata na tabela WKI",
                                 index=index, connection=connection, power_cv=power_cv,
                                 quantity=quantity))
            continue
        installed += float(quantity) * float(power_cv) * 0.736
        item_demand = float(value)
        demand += item_demand
        result_items.append({"quantity": quantity, "power_cv": float(power_cv),
                             "connection": connection, "demand_kva": item_demand})
    return {"items": result_items, "installed_kw": installed, "demand_kw": demand,
            "errors": errors}


def _calculate_special_lighting(items: list[dict[str, Any]]) -> dict[str, Any]:
    result_items = []
    demand = 0.0
    for index, item in enumerate(items):
        power_kw = item.get("power_kw")
        factor = item.get("factor")
        if not _is_number(power_kw) or power_kw < 0:
            raise ValueError(f"special_lighting[{index}].power_kw inválido")
        if not _is_number(factor) or factor < 0:
            raise ValueError(f"special_lighting[{index}].factor inválido")
        item_demand = float(power_kw) * float(factor)
        demand += item_demand
        result_items.append({"power_kw": float(power_kw), "factor": float(factor),
                             "demand_kw": item_demand})
    return {"items": result_items, "demand_kw": demand}


def _compose_result(rooms: dict[str, Any], heating: dict[str, Any],
                    motors: dict[str, Any], special: dict[str, Any],
                    errors: list[dict[str, Any]], location_factor: float) -> dict[str, Any]:
    a = rooms["demand_kva"]
    b = heating["demand_kw"]
    c = motors["demand_kw"]
    d = special["demand_kw"]
    accessory_groups = [b, c, d]
    major = max(accessory_groups, default=0.0)
    final = a + major + sum(value * 0.70 for value in accessory_groups if value != major)
    calculation = {
        "location_factor": location_factor,
        "rooms": rooms,
        "heating": heating,
        "special_lighting": special,
        "motors": motors,
        "demand": {"a": a, "b": b, "c": c, "d": d,
                   "rooms_kva": a, "final_kva": final},
    }
    return {"ok": not errors, "errors": errors, "warnings": [], "calculation": calculation}
