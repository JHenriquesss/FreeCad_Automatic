"""Cálculo auditável da demanda residencial BT segundo a base WKI/Enel.

Este módulo é deliberadamente puro: não conhece FreeCAD, o orquestrador nem
qualquer adaptador de tipologia. Entradas incompletas ou fora das tabelas são
erros estruturados, nunca valores padrão silenciosos. O campo
``loads.installed_load_kw`` é consumido pela seleção do padrão de entrada e
deliberadamente não altera este cálculo de demanda.
"""

from __future__ import annotations

import math
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

_ROOM_NAMES = (
    "quarto", "sala", "banheiro", "cozinha", "area_servico", "outros",
)

# WKI 6.2.3.3: lâmpadas incandescentes são kW=kVA; lâmpadas a vapor são
# convertidas dividindo a potência ativa por cos(phi)=0,9.
_SPECIAL_LIGHTING_POWER_FACTORS = {
    "incandescent": 1.0,
    "vapor_mercury": 0.9,
    "vapor_sodium": 0.9,
    "vapor_metallic": 0.9,
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
    result = _compose_result(rooms, heating, motors, special, errors, location_factor)
    if not _is_finite_structure(result["calculation"]):
        return {
            "ok": False,
            "errors": [_error("non_finite_calculation", "cálculo produziu valor não finito")],
            "warnings": [],
            "calculation": {},
        }
    return result


def _is_number(value: Any) -> bool:
    if not isinstance(value, Real) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, TypeError, ValueError):
        return False


def _error(code: str, message: str, **context: Any) -> dict[str, Any]:
    result = {"code": code, "message": message}
    if context:
        result["context"] = context
    return result


def _is_finite_structure(value: Any) -> bool:
    if isinstance(value, Real):
        return _is_number(value)
    if isinstance(value, dict):
        return all(_is_finite_structure(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_is_finite_structure(item) for item in value)
    return True


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
    elif (not _is_number(network["location_factor"])
          or network["location_factor"] not in LOCATION_FACTORS):
        errors.append(_error("invalid_location_factor", "fator locacional fora da tabela"))

    if not isinstance(rooms, dict):
        errors.append(_error("missing_rooms", "rooms deve ser informado"))
    else:
        for name in _ROOM_NAMES:
            if name not in rooms:
                errors.append(_error("missing_room_count", "contagem de cômodo é obrigatória",
                                     room=name))
        for name, count in rooms.items():
            if name not in _ROOM_NAMES:
                errors.append(_error("unknown_room", "cômodo fora do contrato", room=name))
            elif (not isinstance(count, int) or isinstance(count, bool)
                  or not _is_number(count) or count < 0):
                errors.append(_error("invalid_room_count", "quantidade de cômodo deve ser inteiro não negativo",
                                     room=name))
            elif name == "quarto" and count < 1:
                errors.append(_error("invalid_room_count", "deve existir pelo menos um quarto",
                                     room=name))

    if not isinstance(loads, dict):
        errors.append(_error("missing_loads", "loads deve ser informado"))
    else:
        for key in ("heating", "motors", "special_lighting"):
            items = loads.get(key)
            if not isinstance(items, list):
                errors.append(_error("invalid_load_group", "grupo de cargas deve ser uma lista", group=key))
                continue
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    errors.append(_error("invalid_load_item", "item de carga deve ser um objeto",
                                         group=key, index=index))
                    continue
                if key == "heating":
                    _validate_positive_integer(errors, key, index, item, "quantity")
                    _validate_positive_number(errors, key, index, item, "power_kw")
                elif key == "motors":
                    _validate_positive_integer(errors, key, index, item, "quantity")
                    _validate_positive_number(errors, key, index, item, "power_cv")
                else:
                    _validate_positive_number(errors, key, index, item, "power_kw")
                    if "factor" in item:
                        errors.append(_error(
                            "unsupported_special_lighting_factor",
                            "factor arbitrário não faz parte do contrato",
                            group=key, index=index,
                        ))
                    if "kind" not in item:
                        errors.append(_error(
                            "missing_special_lighting_kind",
                            "tipo de iluminação especial é obrigatório",
                            group=key, index=index,
                        ))
                    elif (not isinstance(item["kind"], str)
                          or item["kind"] not in _SPECIAL_LIGHTING_POWER_FACTORS):
                        errors.append(_error(
                            "invalid_special_lighting_kind",
                            "tipo de iluminação especial fora do contrato",
                            group=key, index=index,
                        ))
    return errors


def _validate_positive_integer(errors: list[dict[str, Any]], group: str,
                               index: int, item: dict[str, Any], field: str) -> None:
    value = item.get(field)
    if (not isinstance(value, int) or isinstance(value, bool)
            or not _is_number(value) or value < 1):
        errors.append(_error("invalid_load_value", "carga deve informar inteiro positivo",
                             group=group, index=index, field=field))


def _validate_positive_number(errors: list[dict[str, Any]], group: str,
                              index: int, item: dict[str, Any], field: str) -> None:
    value = item.get(field)
    if not _is_number(value) or value <= 0:
        errors.append(_error("invalid_load_value", "carga deve informar número finito positivo",
                             group=group, index=index, field=field))


def _calculate_rooms(rooms: dict[str, int], location_factor: float) -> dict[str, Any]:
    bedrooms = rooms["quarto"]
    kitchen_module = 1.50 if bedrooms <= 2 else 2.10
    modules = {
        "quarto": bedrooms * ROOM_MODULES_KVA["quarto"],
        "sala": rooms["sala"] * ROOM_MODULES_KVA["sala"],
        "banheiro": rooms["banheiro"] * ROOM_MODULES_KVA["banheiro"],
        "cozinha": rooms["cozinha"] * kitchen_module,
        "area_servico": rooms["area_servico"] * ROOM_MODULES_KVA["area_servico"],
        "outros": rooms["outros"] * ROOM_MODULES_KVA["outros"],
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
                             "factor_percent": factor, "demand_kva": item_demand})
    return {"items": result_items, "installed_kw": installed, "demand_kva": demand}


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
    return {"items": result_items, "installed_kw": installed, "demand_kva": demand,
            "errors": errors}


def _calculate_special_lighting(items: list[dict[str, Any]]) -> dict[str, Any]:
    result_items = []
    demand_kva = 0.0
    for index, item in enumerate(items):
        power_kw = item.get("power_kw")
        kind = item.get("kind")
        if not _is_number(power_kw) or power_kw <= 0:
            raise ValueError(f"special_lighting[{index}].power_kw inválido")
        power_factor = _SPECIAL_LIGHTING_POWER_FACTORS[kind]
        item_demand = float(power_kw) / power_factor
        demand_kva += item_demand
        result_items.append({"power_kw": float(power_kw), "kind": kind,
                             "power_factor": power_factor,
                             "demand_kva": item_demand})
    return {"items": result_items, "demand_kva": demand_kva}


def _compose_result(rooms: dict[str, Any], heating: dict[str, Any],
                    motors: dict[str, Any], special: dict[str, Any],
                    errors: list[dict[str, Any]], location_factor: float) -> dict[str, Any]:
    a = rooms["demand_kva"]
    b = heating["demand_kva"]
    c = motors["demand_kva"]
    d = special["demand_kva"]
    accessory_groups = [b, c, d]
    major_index = max(range(len(accessory_groups)),
                      key=lambda index: accessory_groups[index])
    major = accessory_groups[major_index]
    final = a + major + sum(
        value * 0.70 for index, value in enumerate(accessory_groups)
        if index != major_index
    )
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
