"""Adaptador residencial sintetico: fixture de contrato do nucleo.

Este adaptador nao executa dimensionamento, nao gera entregaveis de engenharia
e NAO deve ser usado como projeto para obra. O resultado carrega
``synthetic_fixture: True``; os adaptadores reais carregam ``False``.

POR QUE CONTINUA REGISTRADO (decisao G10, ver REVISAO-G10-FIXTURE-SINTETICA.md)
------------------------------------------------------------------------------
Desde o G4 existe um adaptador residencial REAL (``casa_residencial``), e desde
a Fase 6B um segundo (``residencial_eletrica``). Os tres declaram
``project_types=("residencial",)``, o que nao gera ambiguidade: o Loop escolhe o
adaptador pelo NOME declarado no spec, e ``project_types`` e' apenas o gate de
compatibilidade do preflight.

O que esta fixture guarda, e nenhum adaptador real consegue guardar, e' o
caminho SEM HOOK do nucleo: ela e' o unico adaptador registrado com
``hooks={}``. Quando o chamador pede IFC, 3D e 2D de um adaptador que nao sabe
emitir nenhum deles, o nucleo tem de responder ``not_available`` e nao produzir
UM artefato sequer fora do conjunto generico - em vez de falhar, ou pior, de
inventar um entregavel vazio e chama-lo de gerado. Todo adaptador real declara
hooks; por construcao, nenhum deles pode exercer esse caminho.

Ver ``tests/branches/project_loop/test_project_loop_generalization.py``:
``test_residential_missing_hooks_are_not_available_when_requested``.

Portanto: NAO remover, e NAO dar hooks a esta fixture. Dar-lhe um hook apaga a
cobertura sem quebrar nada - por isso ha um teste-guarda explicito.
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
