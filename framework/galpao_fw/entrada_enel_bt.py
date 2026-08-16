"""Seleção do padrão de entrada BT da Enel Brasil.

As tabelas abaixo são uma transcrição mínima dos Anexos A e C do documento
local da Enel. Este módulo é deliberadamente independente do domínio do
galpão, do FreeCAD e do orquestrador de projetos.
"""

from __future__ import annotations

from math import isfinite
from numbers import Real


_DOCUMENT = "CNC-NDBR-DBR-24-1569-EDBR"
_EDITION = "R02/2025"

# row, supply type, lower bound (exclusive), upper bound (inclusive), breaker,
# connection conductors, entry conductors, grounding, conduit, connection point
ANNEX_A_127_220 = (
    ("A1", "A", None, 5.0, 40, "1x10 (10)", "10 (10)", 10, 50, "medidor", "direct_table_7"),
    ("A2", "A", 5.1, 8.0, 63, "1x16 (10)", "16 (10)", 16, 50, "medidor", "direct_table_7"),
    ("B1", "B", 0.0, 11.0, 50, "2x10 (10)", "10 (10)", 10, 50, "medidor", "direct_table_7"),
    ("B2", "B", 11.1, 14.0, 63, "2x16 (10)", "16 (10)", 16, 60, "medidor", "direct_table_7"),
    ("C1", "C", 10.0, 15.0, 40, "3x10 (10)", "10 (10)", 10, 50, "medidor", "direct_table_7"),
    ("C2", "C", 15.1, 19.1, 50, "3x10 (10)", "10 (10)", None, 50, "medidor", "direct_table_7"),
    ("C3", "C", 19.1, 24.0, 63, "3x16 (16)", "25 (25)", 16, 60, "medidor", "direct_table_7"),
    ("C4", "C", 24.1, 30.0, 80, "3x35 (54.6)", None, None, 40, "poste", "direct_consultation_required"),
    ("C5", "C", 30.1, 38.0, 100, "3x35 (54.6)", "35 (25)", None, 40, "poste", "direct_consultation_required"),
    ("C6", "C", 38.1, 48.0, 125, "3x35 (54.6)", "50 (25)", 25, 50, "poste", "direct_consultation_required"),
    ("C7", "C", 48.1, 57.1, 150, "3x50 (54.6)", "70 (35)", 35, None, "poste", "direct_consultation_required"),
    ("C8", "C", 57.2, 67.0, 175, "3x50 (54.6)", "95 (50)", 50, None, "poste", "direct_consultation_required"),
    ("C9", "C", 67.1, 75.0, 200, "3x95 (54.6)", "95 (50)", 25, None, "poste", "direct_consultation_required"),
)

ANNEX_C_120_240 = (
    ("A1", "A", None, 5.0, 40, "1x10 (10)", "10 (10)", 10, 50, "medidor", "direct_table_7"),
    ("A2", "A", 5.1, 6.0, 50, "1x16 (16)", "16 (16)", 16, 50, "medidor", "direct_table_7"),
    ("B1", "B", 6.1, 12.0, 50, "2x16 (16)", "16 (16)", 16, 60, "medidor", "direct_table_7"),
)


def _error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _reference(annex: str, page: int) -> dict[str, str | int]:
    return {
        "document": _DOCUMENT,
        "edition": _EDITION,
        "annex": annex,
        "page": page,
    }


def _table_for_voltage(voltage_system: str) -> tuple[str, int, tuple[tuple, ...]] | None:
    if voltage_system == "127/220":
        return "A", 72, ANNEX_A_127_220
    if voltage_system == "120/240":
        return "C", 77, ANNEX_C_120_240
    return None


def select_enel_bt_entry(
    *, voltage_system: str, supply_type: str | None, installed_load_kw: Real
) -> dict:
    """Seleciona uma linha dos Anexos A ou C para a carga instalada.

    Os limites inferiores das faixas seguintes são exclusivos; o limite
    superior da linha anterior é inclusivo. Assim, uma carga exatamente no
    limite não salta para a próxima faixa.
    """

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    table_info = _table_for_voltage(voltage_system)
    if table_info is None:
        errors.append(
            _error(
                "unsupported_voltage_system",
                f"Sistema de tensão não suportado: {voltage_system!r}",
            )
        )

    if supply_type is None or supply_type == "":
        errors.append(_error("missing_supply_type", "Tipo de fornecimento é obrigatório"))
    elif not isinstance(supply_type, str) or supply_type not in {"A", "B", "C"}:
        errors.append(_error("invalid_supply_type", "Tipo de fornecimento deve ser A, B ou C"))

    valid_load = isinstance(installed_load_kw, Real) and not isinstance(
        installed_load_kw, bool
    ) and isfinite(float(installed_load_kw)) and installed_load_kw > 0
    if not valid_load:
        errors.append(
            _error(
                "invalid_installed_load",
                "Carga instalada deve ser um número finito maior que zero",
            )
        )

    if errors:
        return {"ok": False, "entry": None, "errors": errors, "warnings": warnings}

    annex, page, table = table_info
    load = float(installed_load_kw)
    row = next(
        (
            candidate
            for candidate in table
            if candidate[1] == supply_type
            and (candidate[2] is None or load > candidate[2])
            and load <= candidate[3]
        ),
        None,
    )
    if row is None:
        return {
            "ok": False,
            "entry": None,
            "errors": [
                _error(
                    "no_entry_table_row",
                    f"Não existe linha no Anexo {annex} para tipo {supply_type} e carga {load:g} kW",
                )
            ],
            "warnings": warnings,
        }

    (
        row_name,
        row_type,
        lower_kw,
        upper_kw,
        breaker_a,
        connection_conductors,
        entry_conductors,
        grounding_conductor_mm2,
        conduit_mm,
        point_of_connection,
        metering,
    ) = row
    not_transcribed = (
        ("entry_conductors", entry_conductors),
        ("grounding_conductor_mm2", grounding_conductor_mm2),
        ("conduit_mm", conduit_mm),
    )
    for field, value in not_transcribed:
        if value is None:
            warnings.append(
                {
                    "code": "not_transcribed",
                    "field": field,
                    "message": f"Campo {field} não foi transcrito na fonte local",
                }
            )

    return {
        "ok": True,
        "entry": {
            "row": row_name,
            "voltage_system": voltage_system,
            "supply_type": row_type,
            "load_range_kw": {"min_exclusive_kw": lower_kw, "max_kw": upper_kw},
            "breaker_a": breaker_a,
            "connection_conductors": connection_conductors,
            "entry_conductors": entry_conductors,
            "grounding_conductor_mm2": grounding_conductor_mm2,
            "conduit_mm": conduit_mm,
            "point_of_connection": point_of_connection,
            "metering": metering,
            "reference": _reference(annex, page),
        },
        "errors": errors,
        "warnings": warnings,
    }
