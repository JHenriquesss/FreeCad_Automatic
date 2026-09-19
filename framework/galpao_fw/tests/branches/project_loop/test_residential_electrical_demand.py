import math

import pytest

from demanda_residencial_enel import _MOTOR_TABLE_KVA, calculate_residential_demand


def _payload(**overrides):
    value = {
        "network": {"location_factor": 1.0},
        "rooms": {
            "quarto": 2, "sala": 1, "banheiro": 1,
            "cozinha": 1, "area_servico": 1, "outros": 0,
        },
        "loads": {"installed_load_kw": 7.5, "heating": [],
                  "motors": [], "special_lighting": []},
    }
    value.update(overrides)
    return value


def test_room_modules_use_kitchen_one_for_up_to_two_bedrooms():
    result = calculate_residential_demand(_payload())
    assert result["ok"] is True
    assert result["calculation"]["rooms"]["kitchen_module"] == 1.50
    assert result["calculation"]["rooms"]["subtotal_kva"] == pytest.approx(10.30)
    assert result["calculation"]["rooms"]["diversity_divisor"] == pytest.approx(1.20)
    assert result["calculation"]["demand"]["rooms_kva"] == pytest.approx(10.30 / 1.20)


def test_three_bedrooms_use_kitchen_two():
    payload = _payload()
    payload["rooms"]["quarto"] = 3
    result = calculate_residential_demand(payload)
    assert result["ok"] is True
    assert result["calculation"]["rooms"]["kitchen_module"] == 2.10


def test_one_bedroom_uses_divisor_1_4():
    payload = _payload()
    payload["rooms"]["quarto"] = 1
    result = calculate_residential_demand(payload)
    assert result["calculation"]["rooms"]["diversity_divisor"] == pytest.approx(1.40)


def test_location_factor_is_applied_and_never_defaulted():
    payload = _payload()
    payload["network"]["location_factor"] = 0.88
    result = calculate_residential_demand(payload)
    assert result["calculation"]["location_factor"] == pytest.approx(0.88)
    assert result["calculation"]["demand"]["final_kva"] == pytest.approx(
        (10.30 / 1.20) * 0.88
    )

    missing = _payload()
    del missing["network"]["location_factor"]
    blocked = calculate_residential_demand(missing)
    assert blocked["ok"] is False
    assert any(error["code"] == "missing_location_factor"
               for error in blocked["errors"])


def test_heating_table_uses_power_band_and_quantity():
    payload = _payload()
    payload["loads"]["heating"] = [{"quantity": 2, "power_kw": 4.0}]
    result = calculate_residential_demand(payload)
    heating = result["calculation"]["heating"]
    assert heating["items"][0]["factor_percent"] == pytest.approx(65.0)
    assert heating["demand_kva"] == pytest.approx(2 * 4.0 * 0.65)


def test_final_demand_combines_a_major_group_and_remaining_groups():
    payload = _payload()
    payload["loads"]["special_lighting"] = [{"power_kw": 4.0, "kind": "incandescent"}]
    payload["loads"]["heating"] = [{"quantity": 2, "power_kw": 4.0}]
    payload["loads"]["motors"] = [{"quantity": 1, "power_cv": 1.0,
                                      "connection": "trifasica"}]
    result = calculate_residential_demand(payload)
    assert result["ok"] is True
    demand = result["calculation"]["demand"]
    assert demand["a"] == pytest.approx(10.30 / 1.20)
    assert demand["b"] == pytest.approx(5.2)
    assert demand["c"] == pytest.approx(1.52)
    assert demand["d"] == pytest.approx(4.0)
    assert result["calculation"]["heating"]["demand_kva"] == pytest.approx(5.2)
    assert result["calculation"]["motors"]["demand_kva"] == pytest.approx(1.52)
    assert result["calculation"]["special_lighting"]["demand_kva"] == pytest.approx(4.0)
    assert demand["final_kva"] == pytest.approx(17.6473333333)


def test_motor_tables_are_complete_and_preserve_source_cells():
    assert len(_MOTOR_TABLE_KVA) == 370
    assert _MOTOR_TABLE_KVA[("trifasica", "15", 4)] == pytest.approx(33.29)
    assert _MOTOR_TABLE_KVA[("monofasica", "1 1/2", 2)] == pytest.approx(2.53)
    assert _MOTOR_TABLE_KVA[("monofasica", "10", 7)] == pytest.approx(33.41)


def test_motor_demand_diversifies_different_powers():
    payload = _payload()
    payload["loads"]["motors"] = [
        {"quantity": 1, "power_cv": 1, "connection": "trifasica"},
        {"quantity": 1, "power_cv": "2", "connection": "monofasica"},
    ]

    result = calculate_residential_demand(payload)

    assert result["ok"] is True
    assert result["calculation"]["motors"]["demand_kva"] == pytest.approx(2.97 + 0.70 * 1.52)


def test_real_project_motor_case_uses_source_spelling_and_diversification():
    payload = _payload()
    payload["loads"]["motors"] = [
        {"quantity": 1, "power_cv": "1", "connection": "trifasica"},
        {"quantity": 2, "power_cv": "1/2", "connection": "trifasica"},
    ]

    result = calculate_residential_demand(payload)

    assert result["ok"] is True
    assert result["calculation"]["motors"]["demand_kva"] == pytest.approx(2.437)


@pytest.mark.parametrize(
    ("rendimento", "installed_kw", "basis"),
    [
        (0.736, 1.0, "rendimento_da_placa"),
        (None, 1.5, "sem_placa_1500_w_por_cv"),
    ],
)
def test_motor_installed_power_uses_efficiency_or_source_fallback(
    rendimento, installed_kw, basis
):
    payload = _payload()
    motor = {"quantity": 1, "power_cv": "1", "connection": "trifasica"}
    if rendimento is not None:
        motor["rendimento"] = rendimento
    payload["loads"]["motors"] = [motor]

    result = calculate_residential_demand(payload)

    assert result["ok"] is True
    item = result["calculation"]["motors"]["items"][0]
    assert item["installed_power_kw"] == pytest.approx(installed_kw)
    assert item["installed_power_basis"] == basis
    assert item["installed_power_source"] == "WKI Enel item 6.1, PDF p. 5"
    assert result["calculation"]["motors"]["installed_kw"] == pytest.approx(installed_kw)
    assert result["calculation"]["motors"]["demand_kva"] == pytest.approx(1.52)


@pytest.mark.parametrize("rendimento", [0, -0.1, 1.01, 2])
def test_motor_efficiency_must_be_between_zero_and_one(rendimento):
    payload = _payload()
    payload["loads"]["motors"] = [{
        "quantity": 1,
        "power_cv": "1",
        "connection": "trifasica",
        "rendimento": rendimento,
    }]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(
        error["code"] == "invalid_load_value"
        and error.get("context", {}).get("field") == "rendimento"
        for error in result["errors"]
    )


def test_motor_quantity_above_table_limit_is_rejected():
    payload = _payload()
    payload["loads"]["motors"] = [{
        "quantity": 11,
        "power_cv": "1",
        "connection": "trifasica",
    }]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "motor_outside_table" for error in result["errors"])


def test_bifasica_motor_is_rejected_with_table_reason():
    payload = _payload()
    payload["loads"]["motors"] = [{
        "quantity": 1,
        "power_cv": "1",
        "connection": "bifasica",
    }]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(
        error["code"] == "motor_outside_table"
        and "TABELAS 2 e 3" in error["message"]
        and "monofásicos" in error["message"]
        and "trifásicos" in error["message"]
        for error in result["errors"]
    )


def test_motor_cv_not_printed_in_source_is_rejected_without_interpolation():
    payload = _payload()
    payload["loads"]["motors"] = [{
        "quantity": 1,
        "power_cv": "0.6",
        "connection": "trifasica",
    }]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "motor_outside_table" for error in result["errors"])


def test_final_demand_applies_seventy_percent_to_tied_second_major_group():
    payload = _payload()
    payload["loads"]["heating"] = [{"quantity": 1, "power_kw": 12.5}]
    payload["loads"]["special_lighting"] = [{"power_kw": 10.0, "kind": "incandescent"}]
    result = calculate_residential_demand(payload)
    assert result["ok"] is True
    demand = result["calculation"]["demand"]
    assert demand["b"] == pytest.approx(10.0)
    assert demand["d"] == pytest.approx(10.0)
    assert demand["final_kva"] == pytest.approx(10.30 / 1.20 + 10.0 + 0.70 * 10.0)


def test_unknown_room_count_and_out_of_table_motor_are_blocked():
    payload = _payload()
    payload["rooms"]["varanda"] = 1
    invalid_room = calculate_residential_demand(payload)
    assert invalid_room["ok"] is False
    assert any(error["code"] == "unknown_room"
               for error in invalid_room["errors"])

    motor_payload = _payload()
    motor_payload["loads"]["motors"] = [{"quantity": 1, "power_cv": 999,
                                           "connection": "trifasica"}]
    invalid_motor = calculate_residential_demand(motor_payload)
    assert invalid_motor["ok"] is False
    assert any(error["code"] == "motor_outside_table"
               for error in invalid_motor["errors"])


def test_non_object_load_item_returns_structured_invalid_load_item_error():
    payload = _payload()
    payload["loads"]["heating"] = [None]
    result = calculate_residential_demand(payload)
    assert result["ok"] is False
    assert any(error["code"] == "invalid_load_item"
               for error in result["errors"])


def test_boolean_location_factor_returns_structured_invalid_factor_error():
    payload = _payload()
    payload["network"]["location_factor"] = True
    result = calculate_residential_demand(payload)
    assert result["ok"] is False
    assert any(error["code"] == "invalid_location_factor"
               for error in result["errors"])


def test_non_finite_location_factor_is_rejected_without_non_finite_output():
    payload = _payload()
    payload["network"]["location_factor"] = math.nan

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_location_factor"
               for error in result["errors"])
    assert not _contains_non_finite(result)


def test_unhashable_special_lighting_kind_returns_structured_error():
    payload = _payload()
    payload["loads"]["special_lighting"] = [
        {"power_kw": 1.0, "kind": []},
    ]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_special_lighting_kind"
               for error in result["errors"])


def test_unhashable_string_special_lighting_kind_returns_structured_error():
    class UnhashableString(str):
        __hash__ = None

    payload = _payload()
    payload["loads"]["special_lighting"] = [
        {"power_kw": 1.0, "kind": UnhashableString("incandescent")},
    ]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_special_lighting_kind"
               for error in result["errors"])


def test_overflowing_room_count_is_blocked_without_non_finite_output():
    payload = _payload()
    payload["rooms"]["quarto"] = 10**400

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_room_count"
               for error in result["errors"])
    assert not _contains_non_finite(result)


def test_overflowing_heating_calculation_is_blocked_without_non_finite_output():
    payload = _payload()
    payload["loads"]["heating"] = [{"quantity": 10**307, "power_kw": 4.0}]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "non_finite_calculation"
               for error in result["errors"])
    assert not _contains_non_finite(result)


def test_incandescent_special_lighting_is_normalized_to_kva():
    payload = _payload()
    payload["loads"]["special_lighting"] = [
        {"power_kw": 3.0, "kind": "incandescent"},
    ]

    result = calculate_residential_demand(payload)

    assert result["ok"] is True
    special = result["calculation"]["special_lighting"]
    assert special["items"][0]["kind"] == "incandescent"
    assert special["items"][0]["demand_kva"] == pytest.approx(3.0)
    assert special["demand_kva"] == pytest.approx(3.0)


def test_vapor_special_lighting_uses_point_nine_power_factor_conversion():
    payload = _payload()
    payload["loads"]["special_lighting"] = [
        {"power_kw": 0.9, "kind": "vapor_mercury"},
    ]

    result = calculate_residential_demand(payload)

    assert result["ok"] is True
    assert result["calculation"]["special_lighting"]["demand_kva"] == pytest.approx(1.0)


def test_non_finite_heating_power_is_blocked_with_structured_error():
    payload = _payload()
    payload["loads"]["heating"] = [{"quantity": 1, "power_kw": math.nan}]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_load_value"
               for error in result["errors"])


def test_non_finite_special_lighting_power_is_blocked_with_structured_error():
    payload = _payload()
    payload["loads"]["special_lighting"] = [
        {"power_kw": math.inf, "kind": "incandescent"},
    ]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_load_value"
               for error in result["errors"])


def test_boolean_motor_values_are_not_coerced_into_the_motor_table():
    payload = _payload()
    payload["loads"]["motors"] = [{
        "quantity": True,
        "power_cv": True,
        "connection": "trifasica",
    }]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_load_value"
               for error in result["errors"])


@pytest.mark.parametrize("connection", [[], {}, True])
def test_non_string_motor_connection_returns_structured_error(connection):
    payload = _payload()
    payload["loads"]["motors"] = [{
        "quantity": 1,
        "power_cv": 1.0,
        "connection": connection,
    }]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(
        error["code"] == "invalid_load_value"
        and error.get("context", {}).get("field") == "connection"
        for error in result["errors"]
    )


def test_unhashable_string_motor_connection_returns_structured_error():
    class UnhashableString(str):
        __hash__ = None

    payload = _payload()
    payload["loads"]["motors"] = [{
        "quantity": 1,
        "power_cv": 1.0,
        "connection": UnhashableString("trifasica"),
    }]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(
        error["code"] == "invalid_load_value"
        and error.get("context", {}).get("field") == "connection"
        for error in result["errors"]
    )


def test_missing_room_count_is_blocked_instead_of_defaulting_to_zero():
    payload = _payload()
    del payload["rooms"]["sala"]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "missing_room_count"
               for error in result["errors"])


def test_zero_bedrooms_are_blocked_instead_of_using_the_two_bedroom_divisor():
    payload = _payload()
    payload["rooms"]["quarto"] = 0

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_room_count"
               for error in result["errors"])


def test_special_lighting_rejects_legacy_arbitrary_factor_without_kind():
    payload = _payload()
    payload["loads"]["special_lighting"] = [
        {"power_kw": 1.0, "factor": 2.5},
    ]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "missing_special_lighting_kind"
               for error in result["errors"])


@pytest.mark.parametrize(
    ("group", "item"),
    [
        ("heating", {"quantity": 0, "power_kw": 1.0}),
        ("motors", {"quantity": 0, "power_cv": 1.0, "connection": "trifasica"}),
        ("motors", {"quantity": 1, "power_cv": 0, "connection": "trifasica"}),
        ("special_lighting", {"power_kw": 0, "kind": "incandescent"}),
    ],
)
def test_non_positive_load_values_are_blocked(group, item):
    payload = _payload()
    payload["loads"][group] = [item]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "invalid_load_value"
               for error in result["errors"])


def test_special_lighting_rejects_arbitrary_factor_even_with_a_valid_kind():
    payload = _payload()
    payload["loads"]["special_lighting"] = [
        {"power_kw": 1.0, "kind": "incandescent", "factor": 2.5},
    ]

    result = calculate_residential_demand(payload)

    assert result["ok"] is False
    assert any(error["code"] == "unsupported_special_lighting_factor"
               for error in result["errors"])


def _contains_non_finite(value):
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_contains_non_finite(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_non_finite(item) for item in value)
    return False
