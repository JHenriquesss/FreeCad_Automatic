"""Calculador residencial isolado para designs explícitos de circuitos.

O módulo valida o contrato residencial e delega as tabelas normativas aos
calculadores genéricos existentes (`condutores_nbr5410` e `protecao_nbr5410`).
Não infere valores ausentes e não possui efeitos externos.
"""

from __future__ import annotations

import copy
import math

import condutores_nbr5410 as cd
import protecao_nbr5410 as pr


_REQUIRED_DESIGN_FIELDS = {
    "id",
    "point_ids",
    "length_m",
    "system",
    "conductors_loaded",
    "insulation",
    "reference_method",
    "ambient_temperature_C",
    "grouping_count",
    "power_factor",
    "voltage_drop_limit_pct",
    "use",
    "protection",
}

_SYSTEMS = {"monofasico", "trifasico"}
_CONDUCTORS_LOADED = {2, 3}
_INSULATIONS = {"PVC", "EPR", "XLPE"}
_REFERENCE_METHODS = {"B1", "F"}
_USES = {"iluminacao", "forca"}
_POINT_KINDS = {"lighting", "tug", "tue"}
_LOCATIONS = {"seco", "molhado", "banheiro", "cozinha", "externo", "area_externa"}
_EXPOSURES = {"direta", "rede_aerea", "indireta", "quadro", "equipamento_sensivel"}
_GROUPING_COUNTS = {1, 2, 3, 4, 6, 9}
_POWER_FACTORS = {0.8, 0.95, 1.0}
_NBR5410_SOURCE_ID = "d213019d-6e5c-4f18-8151-bf5a74c11b5d"
_NORMATIVE_REFERENCES = ["5.3.4.1", "5.3.5", "6.2.5", "6.2.6.1.1", "6.2.7"]


def calculate_residential_circuit_designs(circuits: dict, source_refs: list[dict]) -> dict:
    """Valida e dimensiona designs residenciais explícitos sem efeitos externos."""
    source_ids = _nbr5410_source_ids(source_refs)
    safe_points = _safe_input_list(circuits, "points")
    safe_routes = _safe_input_list(circuits, "routes")
    errors = _validate_circuits(circuits)
    if errors:
        return _result(False, errors, [], _scope("not_evaluated"), safe_points, safe_routes)

    points = {point["id"]: point for point in circuits.get("points", [])}
    designs = []
    calculation_errors = []

    for design in circuits["designs"]:
        design_result, error = _calculate_design(design, points, source_ids)
        if error:
            calculation_errors.append(error)
            continue
        designs.append(design_result)

    if calculation_errors:
        scope = _scope("not_evaluated")
        warnings = _short_circuit_warnings(scope)
        return _result(False, calculation_errors, designs, scope, safe_points, safe_routes, warnings)

    scope = _scope(_short_circuit_evaluation(designs))
    warnings = _short_circuit_warnings(scope)
    return _result(True, [], designs, scope, safe_points, safe_routes, warnings)


def _calculate_design(design, points, source_ids):
    selected_points = [points[point_id] for point_id in design["point_ids"]]
    power_va = sum(float(point["power_va"]) for point in selected_points)
    voltage_v = float(selected_points[0]["voltage_v"])
    fp = float(design["power_factor"])

    if design["system"] == "monofasico":
        current_a = power_va / voltage_v
    else:
        current_a = power_va / (math.sqrt(3.0) * voltage_v)

    conductor_input = {
        "IB": current_a,
        "V": voltage_v,
        "L_km": float(design["length_m"]) / 1000.0,
        "sistema": design["system"],
        "n_cond": int(design["conductors_loaded"]),
        "isolacao": design["insulation"],
        "metodo": design["reference_method"],
        "fp": fp,
        "temp_amb": float(design["ambient_temperature_C"]),
        "n_agrupados": int(design["grouping_count"]),
        "uso": design["use"],
        "dv_max": float(design["voltage_drop_limit_pct"]),
    }
    short_circuit = design.get("short_circuit")
    if short_circuit:
        conductor_input["Icc"] = float(short_circuit["Icc_A"])
        conductor_input["t_curto_s"] = float(short_circuit["t_s"])

    try:
        base_conductor = cd.dimensiona_condutor(conductor_input)
        protection_input = _protection_input(design, current_a, base_conductor, short_circuit)
        base_protection = pr.dimensiona_protecao(protection_input)

        coordination = None
        candidate = base_protection["disjuntor"].get("IN")
        if candidate is not None:
            coordination_input = dict(conductor_input)
            coordination_input["I_protecao"] = candidate
            coordination_conductor = cd.dimensiona_condutor(coordination_input)
            coordination_protection = pr.dimensiona_protecao(
                _protection_input(design, current_a, coordination_conductor, short_circuit)
            )
            coordination = {
                "conductor": coordination_conductor,
                "protection": coordination_protection,
            }
    except (KeyError, TypeError, ValueError) as exc:
        return None, {
            "code": "circuit_design_calculation_failed",
            "design_id": design["id"],
            "exception": type(exc).__name__,
        }

    if not _coordinated(base_conductor, base_protection, coordination):
        return None, {"code": "no_protection_candidate", "design_id": design["id"]}

    conductor = coordination["conductor"]
    protection = coordination["protection"]

    return {
        "id": design["id"],
        "point_ids": list(design["point_ids"]),
        "load": {
            "power_va": power_va,
            "voltage_v": voltage_v,
            "current_a": current_a,
        },
        "base_conductor": base_conductor,
        "base_protection": base_protection,
        "conductor": conductor,
        "protection": protection,
        "voltage_drop_reference_fp": _voltage_drop_reference_fp(fp),
        "short_circuit": _short_circuit_result(short_circuit, conductor, protection),
        "traceability": {
            "source_ids": source_ids,
            "normative_references": list(_NORMATIVE_REFERENCES),
        },
    }, None


def _protection_input(design, current_a, conductor, short_circuit):
    protection = design["protection"]
    payload = {
        "IB": current_a,
        "IZ": conductor.get("Iz") or 0.0,
        "uso": design["use"],
        "local": protection["location"],
        "exposicao_dps": protection["exposure"],
    }
    if short_circuit:
        payload["Icc"] = float(short_circuit["Icc_A"])
        payload["Icu"] = float(short_circuit["Icu_A"])
    return payload


def _coordinated(conductor, protection, coordination):
    if conductor.get("n_paralelo", 1) != 1:
        return False
    if not conductor.get("OK") or not protection.get("OK"):
        return False
    if protection["disjuntor"].get("IN") is None:
        return False
    if coordination is None:
        return False
    if coordination["conductor"].get("n_paralelo", 1) != 1:
        return False
    return bool(coordination["conductor"].get("OK") and coordination["protection"].get("OK"))


def _short_circuit_result(short_circuit, conductor, protection):
    if not short_circuit:
        return {"status": "not_evaluated"}
    return {
        "status": "evaluated",
        "Icc_A": float(short_circuit["Icc_A"]),
        "t_s": float(short_circuit["t_s"]),
        "Icu_A": float(short_circuit["Icu_A"]),
        "conductor_ok": bool(conductor.get("curto_ok")),
        "interruption_ok": bool(
            protection.get("disjuntor", {}).get("interrupcao", {}).get("OK")
        ),
    }


def _validate_circuits(circuits):
    errors = []
    if not isinstance(circuits, dict):
        return [{"code": "missing_circuit_designs"}]
    designs = circuits.get("designs")
    if not isinstance(designs, list) or not designs:
        return [{"code": "missing_circuit_designs"}]

    points = circuits.get("points")
    if not isinstance(points, list):
        points = []

    point_map, point_errors = _validate_points(points)
    if point_errors:
        return point_errors

    design_ids = set()
    used_points = {}
    for index, design in enumerate(designs):
        if not isinstance(design, dict):
            errors.append({"code": "invalid_design_field", "design_index": index})
            continue
        missing = sorted(_REQUIRED_DESIGN_FIELDS - set(design))
        for field in missing:
            errors.append({"code": "missing_design_field", "design_id": design.get("id"), "field": field})
        if missing:
            continue

        design_id = design["id"]
        if not isinstance(design_id, str) or not design_id.strip():
            errors.append({"code": "invalid_design_field", "design_id": design_id, "field": "id"})
        elif design_id in design_ids:
            errors.append({"code": "duplicate_design_id", "design_id": design_id})
        else:
            design_ids.add(design_id)

        _validate_design_values(design, errors)
        _validate_design_points(design, point_map, used_points, errors)
        _validate_short_circuit(design, errors)

    return errors


def _validate_points(points):
    errors = []
    point_map = {}
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            errors.append({"code": "invalid_circuit_point", "index": index})
            continue

        for field in ("id", "room", "kind", "power_va", "voltage_v"):
            if field not in point:
                errors.append({"code": "invalid_circuit_point", "index": index, "field": field})

        point_id = point.get("id")
        if "id" in point and (not isinstance(point_id, str) or not point_id.strip()):
            errors.append({"code": "invalid_circuit_point", "index": index, "field": "id"})
        elif isinstance(point_id, str) and point_id.strip():
            if point_id in point_map:
                errors.append({"code": "invalid_circuit_point", "index": index, "field": "id"})
            else:
                point_map[point_id] = point

        if "room" in point and (not isinstance(point["room"], str) or not point["room"].strip()):
            errors.append({"code": "invalid_circuit_point", "index": index, "field": "room"})

        if "kind" in point and (
                not isinstance(point["kind"], str) or point["kind"] not in _POINT_KINDS):
            errors.append({"code": "invalid_circuit_point", "index": index, "field": "kind"})

        if "power_va" in point and (not _finite_number(point["power_va"]) or float(point["power_va"]) <= 0):
            errors.append({"code": "invalid_circuit_point", "index": index, "field": "power_va"})

        if "voltage_v" in point and (not _finite_number(point["voltage_v"]) or float(point["voltage_v"]) <= 0):
            errors.append({"code": "invalid_circuit_point", "index": index, "field": "voltage_v"})

    return point_map, errors


def _validate_design_values(design, errors):
    _enum(design, "system", _SYSTEMS, errors, str)
    _enum(design, "conductors_loaded", _CONDUCTORS_LOADED, errors, int)
    _enum(design, "insulation", _INSULATIONS, errors, str)
    _enum(design, "reference_method", _REFERENCE_METHODS, errors, str)
    _enum(design, "use", _USES, errors, str)

    _positive_number(design, "length_m", errors)
    _positive_number(design, "grouping_count", errors, integer=True)
    _bounded_number(design, "ambient_temperature_C", errors, lower=10.0, upper=60.0)
    _bounded_number(design, "power_factor", errors, lower=0.0, upper=1.0, strict_lower=True)
    _bounded_number(design, "voltage_drop_limit_pct", errors, lower=0.0, upper=4.0, strict_lower=True)
    _supported_grouping_count(design, errors)
    _supported_power_factor(design, errors)

    protection = design.get("protection")
    if not isinstance(protection, dict):
        errors.append({"code": "invalid_design_field", "design_id": design.get("id"), "field": "protection"})
        return
    for field in ("location", "exposure"):
        if field not in protection:
            errors.append({"code": "missing_design_field", "design_id": design.get("id"), "field": f"protection.{field}"})
    if "location" in protection:
        _enum_value(design, "protection.location", protection["location"], _LOCATIONS, errors, str)
    if "exposure" in protection:
        _enum_value(design, "protection.exposure", protection["exposure"], _EXPOSURES, errors, str)


def _validate_design_points(design, point_map, used_points, errors):
    point_ids = design.get("point_ids")
    if not isinstance(point_ids, list) or not point_ids:
        errors.append({"code": "invalid_design_field", "design_id": design.get("id"), "field": "point_ids"})
        return

    local_seen = set()
    voltages = set()
    for point_id in point_ids:
        if not isinstance(point_id, str) or not point_id:
            errors.append({"code": "invalid_design_value", "design_id": design.get("id"), "field": "point_ids"})
            continue
        if point_id in local_seen or point_id in used_points:
            errors.append({"code": "duplicate_design_point", "design_id": design.get("id"), "point_id": point_id})
        local_seen.add(point_id)
        used_points.setdefault(point_id, design.get("id"))
        point = point_map.get(point_id)
        if point is None:
            errors.append({"code": "unknown_design_point", "design_id": design.get("id"), "point_id": point_id})
            continue
        if not _finite_number(point.get("power_va")) or float(point["power_va"]) <= 0:
            errors.append({"code": "invalid_design_value", "design_id": design.get("id"), "field": f"points.{point_id}.power_va"})
        if not _finite_number(point.get("voltage_v")) or float(point["voltage_v"]) <= 0:
            errors.append({"code": "invalid_design_value", "design_id": design.get("id"), "field": f"points.{point_id}.voltage_v"})
        else:
            voltages.add(float(point["voltage_v"]))
    if len(voltages) > 1:
        errors.append({"code": "inconsistent_design_voltage", "design_id": design.get("id")})


def _validate_short_circuit(design, errors):
    if "short_circuit" not in design:
        return
    short_circuit = design["short_circuit"]
    if not isinstance(short_circuit, dict):
        errors.append({"code": "invalid_short_circuit", "design_id": design.get("id")})
        return
    if set(short_circuit) != {"Icc_A", "t_s", "Icu_A"}:
        errors.append({"code": "invalid_short_circuit", "design_id": design.get("id")})
        return
    if any(not _finite_number(short_circuit[field]) or float(short_circuit[field]) <= 0 for field in short_circuit):
        errors.append({"code": "invalid_short_circuit", "design_id": design.get("id")})


def _enum(design, field, allowed, errors, expected_type):
    value = design.get(field)
    if _is_bool_or_not_type(value, expected_type) or value not in allowed:
        errors.append({"code": "invalid_design_value", "design_id": design.get("id"), "field": field})


def _enum_value(design, field, value, allowed, errors, expected_type):
    if _is_bool_or_not_type(value, expected_type) or value not in allowed:
        errors.append({"code": "invalid_design_value", "design_id": design.get("id"), "field": field})


def _is_bool_or_not_type(value, expected_type):
    return isinstance(value, bool) or not isinstance(value, expected_type)


def _positive_number(design, field, errors, integer=False):
    value = design.get(field)
    if not _finite_number(value) or float(value) <= 0:
        errors.append({"code": "invalid_design_value", "design_id": design.get("id"), "field": field})
        return
    if integer and int(value) != value:
        errors.append({"code": "invalid_design_value", "design_id": design.get("id"), "field": field})


def _bounded_number(design, field, errors, lower, upper, strict_lower=False):
    value = design.get(field)
    if not _finite_number(value):
        errors.append({"code": "invalid_design_value", "design_id": design.get("id"), "field": field})
        return
    value = float(value)
    if (value <= lower if strict_lower else value < lower) or value > upper:
        errors.append({"code": "invalid_design_value", "design_id": design.get("id"), "field": field})


def _finite_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def _supported_grouping_count(design, errors):
    value = design.get("grouping_count")
    if not _finite_number(value) or int(value) != value:
        return
    if int(value) not in _GROUPING_COUNTS:
        errors.append({
            "code": "unsupported_design_domain",
            "design_id": design.get("id"),
            "field": "grouping_count",
            "value": value,
        })


def _supported_power_factor(design, errors):
    value = design.get("power_factor")
    if not _finite_number(value):
        return
    value = float(value)
    if value <= 0.0 or value > 1.0:
        return
    if value not in _POWER_FACTORS:
        errors.append({
            "code": "unsupported_design_domain",
            "design_id": design.get("id"),
            "field": "power_factor",
            "value": value,
        })


def _voltage_drop_reference_fp(fp):
    return 0.95 if fp >= 0.90 else 0.8


def _nbr5410_source_ids(source_refs):
    ids = []
    for source in source_refs or []:
        if not isinstance(source, dict):
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            continue
        if source_id == _NBR5410_SOURCE_ID:
            if source_id not in ids:
                ids.append(source_id)
    return ids


def _scope(short_circuit_evaluation):
    return {
        "conductor_sizing": "implemented",
        "protection_sizing": "implemented",
        "short_circuit_evaluation": short_circuit_evaluation,
        "executive_deliverables": "not_implemented",
        "enel_approval": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def _short_circuit_evaluation(designs):
    if designs and all(
            design.get("short_circuit", {}).get("status") == "evaluated"
            for design in designs):
        return "implemented"
    return "not_evaluated"


def _short_circuit_warnings(scope):
    if scope["short_circuit_evaluation"] == "implemented":
        return []
    return [{"code": "short_circuit_not_evaluated"}]


def _safe_input_list(circuits, field):
    if not isinstance(circuits, dict):
        return []
    value = circuits.get(field, [])
    if not isinstance(value, list):
        return []
    return copy.deepcopy(value)


def _result(ok, errors, designs, scope, points, routes, warnings=None):
    return {
        "ok": ok,
        "errors": errors,
        "warnings": warnings or [],
        "points": points,
        "routes": routes,
        "designs": designs,
        "scope": scope,
    }
