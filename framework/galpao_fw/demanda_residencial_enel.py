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

def _motor_table_rows(
    connection: str,
    rows: tuple[tuple[str, tuple[float, ...]], ...],
) -> dict[tuple[str, str, int], float]:
    return {
        (connection, power_cv, quantity): demand_kva
        for power_cv, values in rows
        for quantity, demand_kva in enumerate(values, start=1)
    }


# WKI TABELA 2 (PDF p. 14): three-phase motors, complete source transcription.
# The source prints 33.29 for 15 CV and 4 motors; keep that cell unchanged.
_MOTOR_TABLE_KVA = {
    **_motor_table_rows(
        "trifasica",
        (
            ("1/3", (0.65, 0.98, 1.24, 1.50, 1.76, 1.95, 2.15, 2.34, 2.53, 2.73)),
            ("1/2", (0.87, 1.31, 1.65, 2.00, 2.35, 2.61, 2.87, 3.13, 3.39, 3.65)),
            ("3/4", (1.26, 1.89, 2.39, 2.90, 3.40, 3.78, 4.16, 4.54, 4.91, 5.29)),
            ("1", (1.52, 2.28, 2.89, 3.50, 4.10, 4.56, 5.02, 5.47, 5.93, 6.38)),
            ("1 1/2", (2.17, 3.26, 4.12, 4.99, 5.86, 6.51, 7.16, 7.81, 8.46, 9.11)),
            ("2", (2.70, 4.05, 5.13, 6.21, 7.29, 8.10, 8.91, 9.72, 10.53, 11.34)),
            ("3", (4.04, 6.06, 7.68, 9.29, 10.91, 12.12, 13.13, 14.54, 15.76, 16.97)),
            ("4", (5.03, 7.55, 9.56, 11.57, 13.58, 15.09, 16.60, 18.11, 19.62, 21.13)),
            ("5", (6.02, 9.03, 11.44, 13.85, 16.25, 18.86, 19.87, 21.67, 23.48, 25.28)),
            ("7 1/2", (8.65, 12.98, 16.44, 19.90, 23.36, 25.95, 28.55, 31.14, 33.74, 36.33)),
            ("10", (11.54, 17.31, 21.93, 26.54, 31.16, 34.62, 38.08, 41.54, 45.01, 48.47)),
            ("12 1/2", (14.09, 21.14, 26.77, 32.41, 38.04, 42.27, 46.50, 50.72, 54.95, 59.18)),
            ("15", (16.65, 24.98, 31.63, 33.29, 44.96, 49.95, 54.95, 59.94, 64.93, 69.93)),
            ("20", (22.10, 33.15, 41.99, 50.83, 59.67, 66.30, 72.93, 79.56, 86.19, 92.82)),
            ("25", (25.83, 38.75, 49.08, 59.41, 69.74, 77.49, 85.24, 92.99, 100.74, 108.49)),
            ("30", (30.52, 45.78, 57.99, 70.20, 82.40, 91.56, 100.72, 109.87, 119.03, 128.18)),
            ("40", (39.74, 59.61, 75.51, 91.40, 107.30, 119.22, 131.14, 143.06, 154.99, 166.91)),
            ("50", (48.73, 73.10, 92.59, 112.08, 131.57, 146.19, 160.81, 175.43, 190.05, 204.67)),
            ("60", (58.15, 87.23, 110.49, 133.74, 157.01, 174.45, 191.90, 209.34, 226.79, 244.23)),
            ("75", (72.28, 108.42, 137.33, 166.24, 195.16, 216.84, 238.52, 260.21, 281.89, 303.58)),
            ("100", (95.56, 143.34, 181.56, 219.79, 258.01, 286.68, 315.35, 344.02, 372.68, 401.35)),
            ("125", (117.05, 175.58, 222.40, 269.22, 316.04, 351.15, 386.27, 421.38, 456.50, 491.61)),
            ("150", (141.29, 211.94, 263.45, 324.97, 381.43, 423.87, 466.26, 508.64, 551.03, 593.42)),
            ("200", (190.18, 285.27, 361.34, 437.41, 513.49, 570.54, 627.59, 684.65, 741.70, 789.76)),
        ),
    ),
    # WKI TABELA 3 (PDF p. 14): single-phase motors, complete source transcription.
    # The source prints 2.53 for 1 1/2 CV and 2 motors, and 33.41 for 10 CV
    # and 7 motors; those cells are intentionally not corrected.
    **_motor_table_rows(
        "monofasica",
        (
            ("1/4", (0.66, 0.99, 1.25, 1.52, 1.78, 1.98, 2.18, 2.38, 2.57, 2.77)),
            ("1/3", (0.77, 1.16, 1.46, 1.77, 2.08, 2.31, 2.54, 2.77, 3.00, 3.23)),
            ("1/2", (1.18, 1.77, 2.24, 2.71, 3.19, 3.54, 3.89, 4.25, 4.60, 4.96)),
            ("3/4", (1.34, 2.01, 2.55, 3.03, 3.62, 4.02, 4.42, 4.82, 5.23, 5.63)),
            ("1", (1.56, 2.34, 2.96, 3.59, 4.21, 4.68, 5.01, 5.62, 6.08, 6.55)),
            ("1 1/2", (2.35, 2.53, 4.47, 5.41, 6.35, 7.05, 7.76, 8.46, 9.17, 9.87)),
            ("2", (2.97, 4.46, 5.64, 6.83, 8.02, 8.91, 9.80, 10.69, 11.58, 12.47)),
            ("3", (4.07, 6.11, 7.73, 9.36, 10.99, 12.21, 13.43, 14.65, 15.87, 17.09)),
            ("5", (6.16, 9.24, 11.70, 14.17, 16.63, 18.48, 20.33, 22.18, 24.02, 25.87)),
            ("7 1/2", (8.84, 13.26, 16.80, 20.33, 23.87, 26.52, 29.17, 31.82, 34.48, 37.13)),
            ("10", (11.64, 17.46, 22.12, 26.77, 31.43, 34.92, 33.41, 41.90, 45.40, 48.89)),
            ("12 1/2", (14.94, 22.41, 28.39, 34.03, 40.34, 44.02, 49.30, 53.78, 58.27, 62.75)),
            ("15", (16.94, 25.41, 32.19, 38.96, 45.74, 50.82, 55.90, 60.98, 66.07, 71.15)),
        ),
    ),
}


def _motor_power_cv_number(power_cv: str) -> float:
    if "/" not in power_cv:
        return float(power_cv)
    if " " in power_cv:
        whole, fraction = power_cv.split(" ", 1)
    else:
        whole, fraction = "0", power_cv
    numerator, denominator = fraction.split("/", 1)
    return float(whole) + float(numerator) / float(denominator)


_MOTOR_POWER_CV = {
    power_cv: _motor_power_cv_number(power_cv)
    for _, power_cv, _ in _MOTOR_TABLE_KVA
}

_MOTOR_INSTALLED_POWER_SOURCE = "WKI Enel item 6.1, PDF p. 5"
_MOTOR_TABLE_MAX_QUANTITY = 10
_MOTOR_NO_PLATE_KW_PER_CV = 1.5

# G162: a folha declara de onde veio o numero (fonte + item), pela mesma
# regra do G154 (declarado vs modelo) e do G131 (a entrega declara o que a
# conta usou). Fonte unica desta linha: este modulo (a conta), lida pela
# folha via `fonte_demanda_linha`. Nada aqui decide veredito.
DEMANDA_FONTE_CODIGO = "WKI-OMBR-MAT-18-0263-INBR-R01"
DEMANDA_FONTE_ACERVO = "F131"
DEMANDA_FONTE_ITENS = ("itens 6.1, 6.2.3.2, 6.2.3.3, notas 1 e 2 p. 7, "
                       "TABELA 1")


def fonte_demanda(calculation):
    """Proveniencia da demanda lida do resultado, sem decidir nada.

    Devolve {"codigo", "acervo", "itens", "fator_locacional"} ou None
    quando o calculo nao traz o fator usado (recusa ou secao ausente):
    a folha declara a ausencia, nunca um default.
    """
    if not isinstance(calculation, dict):
        return None
    fator = calculation.get("location_factor")
    if not _is_number(fator):
        return None
    return {"codigo": DEMANDA_FONTE_CODIGO,
            "acervo": DEMANDA_FONTE_ACERVO,
            "itens": DEMANDA_FONTE_ITENS,
            "fator_locacional": float(fator)}


def linha_fonte_demanda(calculation):
    """Linha curta que a folha carimba (fonte unica). None sem o que declarar."""
    fonte = fonte_demanda(calculation)
    if fonte is None:
        return None
    return ("%s (%s; %s; fator locacional %.2f)"
            % (fonte["codigo"], fonte["acervo"], fonte["itens"],
               fonte["fator_locacional"]))


def _motor_power_key(value: Any) -> str | None:
    if isinstance(value, str):
        candidate = value.strip()
    elif _is_number(value) and float(value).is_integer():
        candidate = str(int(value))
    else:
        return None
    return candidate if candidate in _MOTOR_POWER_CV else None

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
                    _validate_motor_power(errors, key, index, item)
                    _validate_motor_efficiency(errors, key, index, item)
                    if not _is_concrete_hashable_string(item.get("connection")):
                        errors.append(_error(
                            "invalid_load_value",
                            "conexão do motor deve ser texto",
                            group=key, index=index, field="connection",
                        ))
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
                    elif (not _is_concrete_hashable_string(item["kind"])
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


def _validate_motor_power(
    errors: list[dict[str, Any]],
    group: str,
    index: int,
    item: dict[str, Any],
) -> None:
    value = item.get("power_cv")
    if isinstance(value, str):
        valid = bool(value.strip())
    else:
        valid = _is_number(value) and value > 0
    if not valid:
        errors.append(_error(
            "invalid_load_value",
            "carga deve informar potência de motor em CV",
            group=group,
            index=index,
            field="power_cv",
        ))


def _validate_motor_efficiency(
    errors: list[dict[str, Any]],
    group: str,
    index: int,
    item: dict[str, Any],
) -> None:
    if "rendimento" not in item:
        return
    value = item.get("rendimento")
    if not _is_number(value) or not 0 < float(value) <= 1:
        errors.append(_error(
            "invalid_load_value",
            "rendimento do motor deve ser maior que zero e menor ou igual a 1",
            group=group,
            index=index,
            field="rendimento",
        ))


def _is_concrete_hashable_string(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        hash(value)
    except TypeError:
        return False
    return True


def _calculate_rooms(rooms: dict[str, int], location_factor: float) -> dict[str, Any]:
    bedrooms = rooms["quarto"]
    # WKI notes 1 and 2 (p. 7): up to 2 bedrooms uses the COZINHA 1 module, 3 or more uses
    # COZINHA 2. The values come from the transcribed table, never from a second literal.
    kitchen_module = ROOM_MODULES_KVA["cozinha_1" if bedrooms <= 2 else "cozinha_2"]
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
    """Resolve a demanda de motores da WKI.

    O item 6.2.3.2 lê a demanda nas TABELAS 2 e 3 pela quantidade de motores de
    MESMA potência, então declarações que repetem o par ligação/potência são
    consolidadas em uma única linha da tabela antes da consulta. A potência
    instalada continua por declaração, porque o item 6.1 deixa cada motor trazer o
    rendimento da sua própria placa.
    """
    result_items = []
    errors = []
    installed = 0.0
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for index, item in enumerate(items):
        quantity = item.get("quantity")
        power_cv = item.get("power_cv")
        connection = item.get("connection")
        if connection == "bifasica":
            errors.append(_error(
                "motor_outside_table",
                "motor bifásico recusado: as TABELAS 2 e 3 da WKI (PDF p. 14) "
                "cobrem somente motores monofásicos e trifásicos",
                index=index,
                connection=connection,
                power_cv=power_cv,
                quantity=quantity,
            ))
            continue
        power_key = _motor_power_key(power_cv)
        if power_key is None or connection not in ("monofasica", "trifasica"):
            errors.append(_error(
                "motor_outside_table",
                "combinação de motor sem linha exata nas TABELAS 2 e 3 da WKI "
                "(PDF p. 14); CV fora da grafia da fonte não é interpolado",
                index=index,
                connection=connection,
                power_cv=power_cv,
                quantity=quantity,
            ))
            continue
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            errors.append(_error(
                "motor_outside_table",
                "quantidade de motores deve ser inteiro ≥ 1 para entrar nas "
                "TABELAS 2 e 3 da WKI (PDF p. 14)",
                index=index,
                connection=connection,
                power_cv=power_cv,
                quantity=quantity,
            ))
            continue
        rendimento = item.get("rendimento")
        cv = _MOTOR_POWER_CV[power_key]
        if rendimento is None:
            installed_power_kw = float(quantity) * cv * _MOTOR_NO_PLATE_KW_PER_CV
            installed_power_basis = "sem_placa_1500_w_por_cv"
        else:
            installed_power_kw = float(quantity) * cv * 0.736 / float(rendimento)
            installed_power_basis = "rendimento_da_placa"
        grupo = groups.setdefault(
            (connection, power_key),
            {"connection": connection, "power_cv": power_key, "quantity": 0, "items": []},
        )
        grupo["quantity"] += quantity
        grupo["items"].append({
            "index": index,
            "quantity": quantity,
            "power_cv": power_key,
            "connection": connection,
            "rendimento": float(rendimento) if rendimento is not None else None,
            "installed_power_kw": installed_power_kw,
            "installed_power_basis": installed_power_basis,
            "installed_power_source": _MOTOR_INSTALLED_POWER_SOURCE,
        })

    result_groups = []
    for (connection, power_key), grupo in groups.items():
        indexes = [item["index"] for item in grupo["items"]]
        if grupo["quantity"] > _MOTOR_TABLE_MAX_QUANTITY:
            errors.append(_error(
                "motor_outside_table",
                "quantidade de motores acima de 10 recusada: as TABELAS 2 e 3 "
                "da WKI (PDF p. 14) têm somente as colunas de 1 a 10",
                indexes=indexes,
                connection=connection,
                power_cv=power_key,
                quantity=grupo["quantity"],
            ))
            continue
        value = _MOTOR_TABLE_KVA.get((connection, power_key, grupo["quantity"]))
        if value is None:
            errors.append(_error(
                "motor_outside_table",
                "combinação de motor sem linha exata nas TABELAS 2 e 3 da WKI "
                "(PDF p. 14); CV fora da grafia da fonte não é interpolado",
                indexes=indexes,
                connection=connection,
                power_cv=power_key,
                quantity=grupo["quantity"],
            ))
            continue
        for item in grupo["items"]:
            installed += item["installed_power_kw"]
            result_items.append(item)
        result_groups.append({
            "connection": connection,
            "power_cv": power_key,
            "quantity": grupo["quantity"],
            "declarations": indexes,
            "demand_kva": float(value),
        })

    if result_groups:
        major_index = max(
            range(len(result_groups)),
            key=lambda index: result_groups[index]["demand_kva"],
        )
        demand = 0.0
        for index, grupo in enumerate(result_groups):
            factor = 1.0 if index == major_index else 0.70
            grupo["diversity_factor"] = factor
            grupo["demand_contribution_kva"] = grupo["demand_kva"] * factor
            demand += grupo["demand_contribution_kva"]
    else:
        demand = 0.0
    return {"items": result_items, "groups": result_groups, "installed_kw": installed,
            "demand_kva": demand, "errors": errors}


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
        # G162: a entrega declara o que a conta usou (G131). A folha le a
        # fonte daqui (fonte_demanda/linha_fonte_demanda); a composicao
        # viaja no mesmo envelope das duas chamadas da vertical, entao o
        # warning da segunda chamada nunca diverge do calculo da primeira.
        "fonte": {"codigo": DEMANDA_FONTE_CODIGO,
                  "acervo": DEMANDA_FONTE_ACERVO,
                  "itens": DEMANDA_FONTE_ITENS,
                  "fator_locacional": float(location_factor)},
        "rooms": rooms,
        "heating": heating,
        "special_lighting": special,
        "motors": motors,
        "demand": {"a": a, "b": b, "c": c, "d": d,
                   "rooms_kva": a, "final_kva": final},
    }
    return {"ok": not errors, "errors": errors, "warnings": [], "calculation": calculation}
