import pytest

from entrada_enel_bt import select_enel_bt_entry


def test_annex_a_selects_b1_for_127_220_and_7_5_kw():
    result = select_enel_bt_entry(
        voltage_system="127/220", supply_type="B", installed_load_kw=7.5
    )
    assert result["ok"] is True
    assert result["entry"]["row"] == "B1"
    assert result["entry"]["breaker_a"] == 50
    assert result["entry"]["reference"]["page"] == 72


def test_annex_a_requires_type_when_ranges_overlap():
    result = select_enel_bt_entry(
        voltage_system="127/220", supply_type=None, installed_load_kw=7.5
    )
    assert result["ok"] is False
    assert any(error["code"] == "missing_supply_type"
               for error in result["errors"])


def test_annex_a_selects_c3_without_silently_changing_type():
    result = select_enel_bt_entry(
        voltage_system="127/220", supply_type="C", installed_load_kw=20.0
    )
    assert result["ok"] is True
    assert result["entry"]["row"] == "C3"
    assert result["entry"]["point_of_connection"] == "medidor"


def test_annex_c_selects_b1_for_120_240():
    result = select_enel_bt_entry(
        voltage_system="120/240", supply_type="B", installed_load_kw=10.0
    )
    assert result["ok"] is True
    assert result["entry"]["row"] == "B1"
    assert result["entry"]["breaker_a"] == 50
    assert result["entry"]["reference"]["page"] == 77


@pytest.mark.parametrize("voltage", ["220/380", "127", "120/208"])
def test_unsupported_voltage_is_blocked(voltage):
    result = select_enel_bt_entry(
        voltage_system=voltage, supply_type="B", installed_load_kw=7.5
    )
    assert result["ok"] is False
    assert any(error["code"] == "unsupported_voltage_system"
               for error in result["errors"])


def test_load_without_matching_row_is_blocked():
    result = select_enel_bt_entry(
        voltage_system="120/240", supply_type="B", installed_load_kw=20.0
    )
    assert result["ok"] is False
    assert any(error["code"] == "no_entry_table_row"
               for error in result["errors"])
