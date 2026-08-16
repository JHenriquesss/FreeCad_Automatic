import pytest

from entrada_enel_bt import select_enel_bt_entry


class _UnhashableString(str):
    __hash__ = None


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


def test_unhashable_supply_type_is_blocked_without_exception():
    result = select_enel_bt_entry(
        voltage_system="127/220",
        supply_type=_UnhashableString("A"),
        installed_load_kw=5.0,
    )
    assert result["ok"] is False
    assert any(error["code"] == "invalid_supply_type"
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


@pytest.mark.parametrize(
    ("load_kw", "expected_row"),
    [(11.0, "B1"), (11.05, None), (11.1, None), (11.11, "B2")],
)
def test_annex_a_type_b_published_boundaries(load_kw, expected_row):
    result = select_enel_bt_entry(
        voltage_system="127/220", supply_type="B", installed_load_kw=load_kw
    )
    if expected_row is None:
        assert result["ok"] is False
        assert any(error["code"] == "no_entry_table_row"
                   for error in result["errors"])
    else:
        assert result["ok"] is True
        assert result["entry"]["row"] == expected_row


@pytest.mark.parametrize(
    ("load_kw", "expected_row"),
    [
        (15.0, "C1"),
        (15.05, None),
        (15.1, None),
        (15.11, "C2"),
        (19.1, "C2"),
        (19.11, "C3"),
        (24.0, "C3"),
        (24.05, None),
        (24.11, "C4"),
        (30.0, "C4"),
        (30.05, None),
        (30.1, None),
        (30.11, "C5"),
    ],
)
def test_annex_a_type_c_published_boundaries(load_kw, expected_row):
    result = select_enel_bt_entry(
        voltage_system="127/220", supply_type="C", installed_load_kw=load_kw
    )
    if expected_row is None:
        assert result["ok"] is False
        assert any(error["code"] == "no_entry_table_row"
                   for error in result["errors"])
    else:
        assert result["ok"] is True
        assert result["entry"]["row"] == expected_row


@pytest.mark.parametrize(
    ("load_kw", "expected_row"),
    [(5.0, "A1"), (5.01, "A2"), (5.05, "A2")],
)
def test_annex_a_type_a_uses_published_exclusive_lower_boundary(load_kw, expected_row):
    result = select_enel_bt_entry(
        voltage_system="127/220", supply_type="A", installed_load_kw=load_kw
    )
    assert result["ok"] is True
    assert result["entry"]["row"] == expected_row


@pytest.mark.parametrize(
    ("supply_type", "load_kw", "expected_row"),
    [
        ("A", 5.0, "A1"),
        ("A", 5.05, None),
        ("A", 5.1, None),
        ("A", 5.11, "A2"),
        ("A", 6.0, "A2"),
        ("A", 6.05, None),
        ("A", 6.1, None),
        ("B", 6.11, "B1"),
    ],
)
def test_annex_c_published_boundaries(supply_type, load_kw, expected_row):
    result = select_enel_bt_entry(
        voltage_system="120/240", supply_type=supply_type, installed_load_kw=load_kw
    )
    if expected_row is None:
        assert result["ok"] is False
        assert any(error["code"] == "no_entry_table_row"
                   for error in result["errors"])
    else:
        assert result["ok"] is True
        assert result["entry"]["row"] == expected_row


@pytest.mark.parametrize(
    ("voltage_system", "supply_type", "load_kw", "annex", "page"),
    [
        ("127/220", "A", 5.0, "A", 72),
        ("127/220", "C", 24.0, "A", 72),
        ("120/240", "B", 10.0, "C", 77),
    ],
)
def test_entry_reference_is_traceable(
    voltage_system, supply_type, load_kw, annex, page
):
    result = select_enel_bt_entry(
        voltage_system=voltage_system,
        supply_type=supply_type,
        installed_load_kw=load_kw,
    )
    reference = result["entry"]["reference"]
    assert reference["document"] == "CNC-NDBR-DBR-24-1569-EDBR"
    assert reference["edition"] == "R02/2025"
    assert reference["annex"] == annex
    assert reference["page"] == page


def test_annex_a_c4_requires_distributor_consultation_for_metering():
    result = select_enel_bt_entry(
        voltage_system="127/220", supply_type="C", installed_load_kw=25.0
    )
    assert result["ok"] is True
    assert result["entry"]["row"] == "C4"
    assert result["entry"]["metering"] == "direct_consultation_required"
    assert any(
        warning["code"] == "not_transcribed"
        and warning["field"] in {"entry_conductors", "grounding_conductor_mm2"}
        for warning in result["warnings"]
    )
