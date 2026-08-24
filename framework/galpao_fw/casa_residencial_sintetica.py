"""Adaptador residencial sintético para validar o contrato universal.

Este adaptador representa apenas uma fixture de integração. Ele não executa
dimensionamento, não gera entregáveis de engenharia e não deve ser usado como
projeto para obra.
"""

from project_loop import register_adapter


ADAPTER_NAME = "casa-residencial-sintetica"
DISCIPLINES = ("arquitetura", "eletrico", "hidraulica")


def _run_residential_synthetic(normalized, run_dir):
    """Executa a fixture residencial sem produzir artefatos técnicos."""
    del run_dir
    records = {}
    result_disciplines = {}
    warning = {
        "code": "synthetic_fixture",
        "detail": "resultado de contrato; não é dimensionamento para obra",
    }

    turnkey_spec = normalized["turnkey_spec"]
    for name in normalized["requested_disciplines"]:
        present = isinstance(turnkey_spec.get(name), dict)
        result_disciplines[name] = {"input_present": present}
        common = {
            "native_atende": None,
            "reprovados": [],
            "warnings": [warning.copy()],
            "artifacts": [],
        }
        if present:
            records[name] = {
                **common,
                "status": "needs_review",
                "gates": {"synthetic_fixture": True},
                "errors": [],
            }
        else:
            records[name] = {
                **common,
                "status": "blocked",
                "gates": {},
                "errors": [{"code": "missing_synthetic_input"}],
            }

    return {
        "schema": "freecad-automatic/synthetic-adapter-result",
        "schema_version": 1,
        "adapter": ADAPTER_NAME,
        "synthetic_fixture": True,
        "project_id": normalized["project_id"],
        "disciplines": result_disciplines,
    }, records


def register_residential_adapter():
    register_adapter(
        ADAPTER_NAME,
        _run_residential_synthetic,
        project_types=("residencial",),
        disciplines=DISCIPLINES,
        deliverables=("report",),
    )
