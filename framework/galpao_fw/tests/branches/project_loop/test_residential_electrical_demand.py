import pytest

from demanda_residencial_enel import calculate_residential_demand


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
    assert heating["demand_kw"] == pytest.approx(2 * 4.0 * 0.65)


def test_final_demand_combines_a_major_group_and_remaining_groups():
    payload = _payload()
    payload["loads"]["special_lighting"] = [{"power_kw": 4.0, "factor": 1.0}]
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
    assert demand["final_kva"] == pytest.approx(17.6473333333)


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
