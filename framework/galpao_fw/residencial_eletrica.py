"""Runner auditável da primeira vertical elétrica residencial BT/Enel.

O módulo apenas compõe entradas explícitas, cálculo de demanda e seleção do
padrão de entrada. Não consulta NotebookLM, não cria pontos a partir de
cômodos e não dimensiona condutores ou proteções nesta fatia.
"""

from __future__ import annotations

import copy
from math import isfinite
from numbers import Real
from typing import Any

from demanda_residencial_enel import calculate_residential_demand
from entrada_enel_bt import select_enel_bt_entry


ADAPTER_NAME = "casa-residencial-eletrica"
ELECTRICAL_NOTEBOOK_ID = "78cd2efd-0652-484e-b312-c5c5a7648962"
REQUIRED_SOURCE_IDS = frozenset({
    "d213019d-6e5c-4f18-8151-bf5a74c11b5d",
    "5129118d-2ff6-4187-a9d2-d1828d61afdf",
    "5bc6c2f1-c8b8-4a04-8b82-be0e937b4749",
    "4c71daf6-ff91-44d1-a5e7-d7f881ab66f8",
})
REQUIRED_SOURCE_REFS = frozenset(
    (ELECTRICAL_NOTEBOOK_ID, source_id) for source_id in REQUIRED_SOURCE_IDS
)
MOTOR_TABLE_COVERAGE = {
    "status": "limited",
    "supported": [{
        "connection": "trifasica",
        "power_cv": 1.0,
        "quantity": 1,
    }],
    "demand_field": "demand_kva",
}


def _error(code: str, detail: str, **context: Any) -> dict[str, Any]:
    result = {"code": code, "detail": detail}
    if context:
        result["context"] = context
    return result


def _finite_positive(value: Any) -> bool:
    return (isinstance(value, Real) and not isinstance(value, bool)
            and isfinite(float(value)) and value > 0)


def validate_circuit_points(circuits: dict) -> dict[str, Any]:
    """Valida somente os pontos declarados pelo usuário, sem reparos."""
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if not isinstance(circuits, dict):
        return {"ok": False, "errors": [_error(
            "invalid_circuits", "circuits deve ser um objeto JSON")],
            "warnings": warnings, "points": [], "routes": []}

    points = circuits.get("points")
    if not isinstance(points, list):
        errors.append(_error("missing_circuit_points",
                             "circuits.points deve ser uma lista"))
        points = []
    elif not points:
        errors.append(_error("missing_circuit_points",
                             "circuits.points não pode ser vazio"))

    routes = circuits.get("routes", [])
    if not isinstance(routes, list):
        errors.append(_error("invalid_circuit_routes",
                             "circuits.routes deve ser uma lista"))
        routes = []

    validated: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            errors.append(_error("invalid_circuit_point",
                                 "ponto de circuito deve ser um objeto", index=index))
            continue
        point_id = point.get("id")
        room = point.get("room")
        kind = point.get("kind")
        power_va = point.get("power_va")
        voltage_v = point.get("voltage_v")
        valid = True
        if not isinstance(point_id, str) or not point_id.strip():
            errors.append(_error("missing_circuit_id", "ponto requer id não vazio",
                                 index=index))
            valid = False
        elif point_id in identifiers:
            errors.append(_error("duplicate_circuit_id", "id de ponto repetido",
                                 index=index, id=point_id))
            valid = False
        else:
            identifiers.add(point_id)
        if not isinstance(room, str) or not room.strip():
            errors.append(_error("missing_circuit_room", "ponto requer room não vazio",
                                 index=index))
            valid = False
        if kind not in {"lighting", "tug", "tue"}:
            errors.append(_error("unsupported_circuit_kind",
                                 "kind deve ser lighting, tug ou tue", index=index))
            valid = False
        if not _finite_positive(power_va):
            errors.append(_error("missing_circuit_power",
                                 "ponto requer power_va finito maior que zero", index=index))
            valid = False
        if not _finite_positive(voltage_v):
            errors.append(_error("missing_circuit_voltage",
                                 "ponto requer voltage_v finito maior que zero", index=index))
            valid = False
        if valid:
            validated.append(copy.deepcopy(point))

    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "points": validated, "routes": copy.deepcopy(routes)}


def _electrical_source_refs(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    source_refs = normalized.get("source_refs")
    if isinstance(source_refs, list):
        return copy.deepcopy(source_refs)
    if not isinstance(source_refs, dict):
        return []
    refs = source_refs.get("eletrico", source_refs.get("all", []))
    return copy.deepcopy(refs) if isinstance(refs, list) else []


def _required_source_errors(source_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    declared = {
        (item.get("notebook_id"), item.get("source_id"))
        for item in source_refs if isinstance(item, dict)
    }
    return [
        _error(
            "missing_required_source",
            "fonte normativa obrigatória ausente no notebook elétrico",
            notebook_id=notebook_id,
            source_id=source_id,
        )
        for notebook_id, source_id in sorted(REQUIRED_SOURCE_REFS)
        if (notebook_id, source_id) not in declared
    ]


def _preflight_electrical_errors(preflight: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(preflight, dict):
        return []
    return [copy.deepcopy(item) for item in preflight.get("errors", [])
            if isinstance(item, dict) and item.get("discipline") == "eletrico"]


def _payload_errors(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return [_error("invalid_electrical_payload", "turnkey.eletrico deve ser um objeto")]
    errors: list[dict[str, Any]] = []
    network = payload.get("network")
    if not isinstance(network, dict):
        return [_error("missing_network", "network deve ser informado")]
    for field in ("voltage_system", "supply_type", "network_kind", "location_factor"):
        value = network.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(_error("missing_" + field, f"network.{field} é obrigatório"))
    if network.get("network_kind") not in {"aerea", "subterranea"}:
        errors.append(_error("invalid_network_kind",
                             "network_kind deve ser aerea ou subterranea"))
    if not isinstance(payload.get("rooms"), dict):
        errors.append(_error("missing_rooms", "rooms deve ser informado"))
    if not isinstance(payload.get("loads"), dict):
        errors.append(_error("missing_loads", "loads deve ser informado"))
    return errors


def _warning(code: str, **fields: Any) -> dict[str, Any]:
    return {"code": code, **fields}


def run_residential_electrical(normalized, run_dir, preflight=None):
    """Executa a vertical elétrica residencial sem efeitos externos."""
    del run_dir
    source_refs = _electrical_source_refs(normalized)
    turnkey_spec = normalized.get("turnkey_spec")
    payload = turnkey_spec.get("eletrico") if isinstance(turnkey_spec, dict) else None
    errors = _required_source_errors(source_refs)
    errors.extend(_preflight_electrical_errors(preflight))
    errors.extend(_payload_errors(payload))

    circuit_result = validate_circuit_points(
        payload.get("circuits") if isinstance(payload, dict) else {})
    errors.extend(circuit_result["errors"])
    calculation: dict[str, Any] = {}
    service_entry: dict[str, Any] = {"ok": False, "entry": None,
                                      "errors": [], "warnings": []}

    has_calculation_sections = (isinstance(payload, dict)
                                and isinstance(payload.get("network"), dict)
                                and isinstance(payload.get("rooms"), dict)
                                and isinstance(payload.get("loads"), dict))
    if has_calculation_sections:
        demand_result = calculate_residential_demand(payload)
        calculation = copy.deepcopy(demand_result.get("calculation", {}))
        errors.extend(copy.deepcopy(demand_result.get("errors", [])))
        network_kind = payload["network"].get("network_kind")
        if network_kind != "aerea":
            errors.append(_error(
                "unsupported_network_kind_for_entry",
                "as tabelas Enel transcritas nesta vertical são somente para rede aérea",
                network_kind=network_kind,
            ))
        elif demand_result.get("ok") and _finite_positive(
                payload["loads"].get("installed_load_kw")):
            service_entry = select_enel_bt_entry(
                voltage_system=payload["network"].get("voltage_system"),
                supply_type=payload["network"].get("supply_type"),
                installed_load_kw=payload["loads"]["installed_load_kw"],
            )
            errors.extend(copy.deepcopy(service_entry.get("errors", [])))
        elif not _finite_positive(payload["loads"].get("installed_load_kw")):
            errors.append(_error("invalid_installed_load",
                                 "loads.installed_load_kw deve ser finito e maior que zero"))

    warnings = [
        _warning("source_snapshot_requires_readiness"),
        _warning("executive_deliverables_not_implemented"),
    ]
    warnings.extend(copy.deepcopy(circuit_result["warnings"]))
    warnings.extend(copy.deepcopy(service_entry.get("warnings", [])))
    if isinstance(payload, dict):
        warnings.extend(copy.deepcopy(calculate_residential_demand(payload).get("warnings", []))
                        if has_calculation_sections else [])

    scope = {
        "conductor_sizing": "not_implemented",
        "protection_sizing": "not_implemented",
        "executive_deliverables": "not_implemented",
        "enel_approval": "not_claimed",
        "construction_readiness": "not_claimed",
        "motor_table_coverage": copy.deepcopy(MOTOR_TABLE_COVERAGE),
    }
    status = "needs_review" if not errors else "blocked"
    record = {
        "status": status,
        "native_atende": None,
        "reprovados": [],
        "warnings": warnings,
        "errors": errors,
        "gates": {
            "required_sources_declared": not _required_source_errors(source_refs),
            "explicit_network_inputs": not _payload_errors(payload),
            "explicit_circuit_points": circuit_result["ok"],
        },
        "calculation": calculation,
        "service_entry": service_entry,
        "circuits": circuit_result,
        "source_refs": source_refs,
        "scope": copy.deepcopy(scope),
        "artifacts": [],
    }
    result = {
        "schema": "freecad-automatic/residential-electrical-result",
        "schema_version": 1,
        "adapter": ADAPTER_NAME,
        "project_id": normalized.get("project_id"),
        "source_refs": source_refs,
        "calculation": calculation,
        "service_entry": service_entry,
        "circuits": circuit_result,
        "scope": scope,
    }
    return result, {"eletrico": record}


def register_residential_electrical_adapter() -> None:
    """Registra o adaptador; o carregamento global ocorre em tarefa própria."""
    from project_loop import register_adapter

    register_adapter(
        ADAPTER_NAME,
        run_residential_electrical,
        project_types=("residencial",),
        disciplines=("eletrico",),
        deliverables=("report",),
    )
