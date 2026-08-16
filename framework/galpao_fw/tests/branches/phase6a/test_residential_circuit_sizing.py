import copy
import math

import pytest

from dimensionamento_eletrico_residencial import (
    calculate_residential_circuit_designs,
)


SOURCE_REFS = [
    {
        "notebook_id": "78cd2efd-0652-484e-b312-c5c5a7648962",
        "source_id": "d213019d-6e5c-4f18-8151-bf5a74c11b5d",
        "title": "ABNT NBR 5410:2004",
        "edition": "2004",
        "status": 2,
        "is_stale": False,
    }
]


def _design(point_id="TUE-01", design_id=None, **overrides):
    design = {
        "id": design_id or f"C-{point_id}",
        "point_ids": [point_id],
        "length_m": 18.0,
        "system": "monofasico",
        "conductors_loaded": 2,
        "insulation": "PVC",
        "reference_method": "B1",
        "ambient_temperature_C": 30.0,
        "grouping_count": 3,
        "power_factor": 1.0,
        "voltage_drop_limit_pct": 4.0,
        "use": "forca",
        "protection": {"location": "banheiro", "exposure": "quadro"},
    }
    design.update(overrides)
    return design


def _circuits(point=None, design=None, *, points=None, designs=None):
    if points is None:
        points = [point or {
            "id": "TUE-01",
            "room": "banheiro",
            "kind": "tue",
            "power_va": 6000,
            "voltage_v": 220,
        }]
    if designs is None:
        designs = [design or _design(points[0]["id"])]
    return {"points": points, "routes": [], "designs": designs}


def test_chuveiro_residencial_dimensiona_resultado_final_coordenado():
    result = calculate_residential_circuit_designs(_circuits(), SOURCE_REFS)

    item = result["designs"][0]
    assert result["ok"] is True
    assert item["load"]["current_a"] == pytest.approx(6000 / 220)
    assert item["conductor"]["secao_mm2"] == 10
    assert item["base_conductor"]["secao_mm2"] == 6
    assert item["protection"]["disjuntor"]["IN"] == 32
    assert item["protection"]["OK"] is True
    assert item["voltage_drop_reference_fp"] == 0.95


def test_publica_o_resultado_da_segunda_passagem_coordenada():
    result = calculate_residential_circuit_designs(_circuits(), SOURCE_REFS)
    item = result["designs"][0]
    assert item["base_conductor"]["secao_mm2"] == 6
    assert item["conductor"]["secao_mm2"] == 10
    assert item["protection"]["disjuntor"]["IN"] == 32
    assert item["conductor"]["Iz"] >= item["protection"]["disjuntor"]["IN"]


def test_ponto_malformado_nao_gera_excecao():
    circuits = _circuits()
    circuits["points"].append({"id": "P-INVALIDO", "room": "sala"})
    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)
    assert result["ok"] is False
    assert any(error["code"] == "invalid_circuit_point"
               for error in result["errors"])


@pytest.mark.parametrize("field", ["room", "kind"])
def test_campo_estrutural_de_ponto_e_obrigatorio(field):
    circuits = _circuits()
    circuits["points"][0].pop(field)
    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)
    assert result["ok"] is False
    assert any(error["code"] == "invalid_circuit_point"
               and error.get("field") == field for error in result["errors"])


def test_queda_de_tensao_pode_ser_o_criterio_governante():
    circuits = _circuits(
        point={"id": "TUG-01", "room": "sala", "kind": "tug",
               "power_va": 2000, "voltage_v": 127},
        design=_design("TUG-01", length_m=80.0, use="forca",
                       protection={"location": "seco", "exposure": "quadro"},
                       power_factor=0.8),
    )

    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)

    assert result["ok"] is True
    assert result["designs"][0]["conductor"]["governante"] == "queda"


def test_sem_curto_explica_revisao_sem_inventar_icc():
    circuits = _circuits(
        point={"id": "L-01", "room": "sala", "kind": "lighting",
               "power_va": 100, "voltage_v": 127},
        design=_design("L-01", length_m=10.0, use="iluminacao",
                       protection={"location": "seco", "exposure": "quadro"}),
    )

    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)

    assert result["ok"] is True
    assert result["designs"][0]["short_circuit"] == {"status": "not_evaluated"}
    assert result["scope"]["short_circuit_evaluation"] == "not_evaluated"


@pytest.mark.parametrize("mutator, code", [
    (lambda c: c.pop("designs"), "missing_circuit_designs"),
    (lambda c: c["designs"][0].pop("length_m"), "missing_design_field"),
    (lambda c: c["designs"][0].update({"point_ids": ["UNKNOWN"]}),
     "unknown_design_point"),
    (lambda c: c["designs"].append(copy.deepcopy(c["designs"][0])),
     "duplicate_design_id"),
    (lambda c: c["designs"][0].update({
        "short_circuit": {"Icc_A": 5000}
    }), "invalid_short_circuit"),
])
def test_contrato_invalido_bloqueia_sem_heuristica(mutator, code):
    circuits = _circuits()
    mutator(circuits)

    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)

    assert result["ok"] is False
    assert isinstance(result["errors"], list)
    assert any(error["code"] == code for error in result["errors"])


def test_tensao_inconsistente_no_mesmo_design_e_rejeitada():
    points = [
        {"id": "TUG-01", "room": "sala", "kind": "tug",
         "power_va": 1000, "voltage_v": 127},
        {"id": "TUE-01", "room": "cozinha", "kind": "tue",
         "power_va": 2000, "voltage_v": 220},
    ]
    circuits = _circuits(
        points=points,
        designs=[_design("TUG-01", point_ids=["TUG-01", "TUE-01"],
                         protection={"location": "seco", "exposure": "quadro"})],
    )

    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)

    assert result["ok"] is False
    assert any(error["code"] == "inconsistent_design_voltage"
               for error in result["errors"])


def test_mesmo_ponto_em_dois_designs_e_rejeitado():
    circuits = _circuits(designs=[
        _design("TUE-01", design_id="C-01"),
        _design("TUE-01", design_id="C-02"),
    ])

    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)

    assert result["ok"] is False
    assert any(error["code"] == "duplicate_design_point"
               for error in result["errors"])


@pytest.mark.parametrize("field, value", [
    ("reference_method", "desconhecido"),
    ("insulation", "desconhecida"),
])
def test_metodo_ou_isolacao_desconhecidos_geram_erro_estruturado(field, value):
    circuits = _circuits()
    circuits["designs"][0][field] = value

    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)

    assert result["ok"] is False
    assert isinstance(result["errors"], list)
    assert any(error["code"] in {"invalid_design_field", "invalid_design_value"}
               for error in result["errors"])


@pytest.mark.parametrize("field, value", [
    ("length_m", math.nan),
    ("ambient_temperature_C", math.inf),
    ("power_factor", -math.inf),
])
def test_numeros_nao_finitos_geram_erro_estruturado_sem_excecao(field, value):
    circuits = _circuits()
    circuits["designs"][0][field] = value

    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)

    assert result["ok"] is False
    assert isinstance(result["errors"], list)
    assert any(error["code"] in {"invalid_design_field", "invalid_design_value"}
               for error in result["errors"])


def test_carga_sem_candidato_de_protecao_bloqueia_dimensionamento():
    circuits = _circuits(
        point={"id": "TUE-01", "room": "banheiro", "kind": "tue",
               "power_va": 100000, "voltage_v": 220},
    )

    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)

    assert result["ok"] is False
    assert any(error["code"] == "no_protection_candidate"
               for error in result["errors"])


def test_power_va_nao_divide_novamente_pelo_fator_de_potencia():
    circuits = _circuits(
        point={"id": "TUG-01", "room": "sala", "kind": "tug",
               "power_va": 1000, "voltage_v": 127},
        design=_design("TUG-01", power_factor=0.8,
                       protection={"location": "seco", "exposure": "quadro"}),
    )
    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)
    assert result["designs"][0]["load"]["current_a"] == pytest.approx(1000 / 127)


@pytest.mark.parametrize("field, value", [
    ("grouping_count", 5),
    ("grouping_count", 100),
    ("power_factor", 0.85),
])
def test_dominios_sem_coluna_tabelada_bloqueiam(field, value):
    circuits = _circuits()
    circuits["designs"][0][field] = value
    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)
    assert result["ok"] is False
    assert any(error["code"] == "unsupported_design_domain"
               for error in result["errors"])


@pytest.mark.parametrize("mutator", [
    lambda c: c["points"][0].update({"kind": []}),
    lambda c: c["designs"][0].update({"reference_method": []}),
    lambda c: c["designs"][0]["protection"].update({"location": []}),
])
def test_valores_nao_hashable_bloqueiam_sem_typeerror(mutator):
    circuits = _circuits()
    mutator(circuits)
    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)
    assert result["ok"] is False
    assert result["errors"]


def test_falha_de_dominio_da_tabela_vira_erro_estruturado():
    circuits = _circuits(design=_design("TUE-01", length_m=1e9))
    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)
    assert result["ok"] is False
    assert any(error["code"] == "circuit_design_calculation_failed"
               for error in result["errors"])


def test_curto_completo_e_rastreabilidade_por_id_sem_titulo():
    refs = [{"notebook_id": SOURCE_REFS[0]["notebook_id"],
             "source_id": SOURCE_REFS[0]["source_id"]}]
    circuits = _circuits(design=_design("TUE-01", grouping_count=1,
        short_circuit={"Icc_A": 5000.0, "t_s": 0.1, "Icu_A": 6000.0}))
    result = calculate_residential_circuit_designs(circuits, refs)
    assert result["ok"] is True
    assert result["scope"]["short_circuit_evaluation"] == "implemented"
    assert result["designs"][0]["short_circuit"]["status"] == "evaluated"
    assert result["designs"][0]["traceability"]["source_ids"] == [
        SOURCE_REFS[0]["source_id"]]


def test_rastreabilidade_nao_usa_fallback_por_titulo_ou_source_id_malformado():
    refs = [
        {"source_id": "outro-id", "title": "ABNT NBR 5410:2004"},
        {"source_id": None, "title": "ABNT NBR 5410:2004"},
    ]
    result = calculate_residential_circuit_designs(_circuits(), refs)
    assert result["ok"] is True
    assert result["designs"][0]["traceability"]["source_ids"] == []


def test_curto_misto_permanece_nao_avaliado_com_aviso():
    points = [
        {"id": "TUE-01", "room": "banheiro", "kind": "tue",
         "power_va": 6000, "voltage_v": 220},
        {"id": "L-01", "room": "sala", "kind": "lighting",
         "power_va": 100, "voltage_v": 127},
    ]
    designs = [
        _design("TUE-01", design_id="C-TUE", grouping_count=1,
                short_circuit={"Icc_A": 5000.0, "t_s": 0.1, "Icu_A": 6000.0}),
        _design("L-01", design_id="C-L", grouping_count=1,
                use="iluminacao",
                protection={"location": "seco", "exposure": "quadro"}),
    ]
    result = calculate_residential_circuit_designs(
        _circuits(points=points, designs=designs), SOURCE_REFS)
    assert result["ok"] is True
    assert result["scope"]["short_circuit_evaluation"] == "not_evaluated"
    assert any(item["code"] == "short_circuit_not_evaluated"
               for item in result["warnings"])


def test_curto_nao_implementado_quando_ha_erro_de_calculo_em_design_elegivel():
    points = [
        {"id": "TUE-01", "room": "banheiro", "kind": "tue",
         "power_va": 6000, "voltage_v": 220},
        {"id": "L-01", "room": "sala", "kind": "lighting",
         "power_va": 100, "voltage_v": 127},
    ]
    designs = [
        _design("TUE-01", design_id="C-TUE", grouping_count=1,
                short_circuit={"Icc_A": 5000.0, "t_s": 0.1, "Icu_A": 6000.0}),
        _design("L-01", design_id="C-L", grouping_count=1,
                length_m=1e9, use="iluminacao",
                protection={"location": "seco", "exposure": "quadro"},
                short_circuit={"Icc_A": 5000.0, "t_s": 0.1, "Icu_A": 6000.0}),
    ]
    result = calculate_residential_circuit_designs(
        _circuits(points=points, designs=designs), SOURCE_REFS)
    assert result["ok"] is False
    assert result["scope"]["short_circuit_evaluation"] == "not_evaluated"
    assert any(error["code"] == "circuit_design_calculation_failed"
               for error in result["errors"])


def test_envelope_direto_preserva_points_e_routes():
    circuits = _circuits()
    result = calculate_residential_circuit_designs(circuits, SOURCE_REFS)
    assert result["points"] == circuits["points"]
    assert result["routes"] == circuits["routes"]
