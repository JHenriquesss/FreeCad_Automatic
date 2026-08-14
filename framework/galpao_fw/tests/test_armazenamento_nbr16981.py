import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import armazenamento_nbr16981 as ar


def _base(**changes):
    case = {
        "mercadoria_risco_mais_grave_declarada": True,
        "altura_armazenamento_m": 3.7,
        "altura_teto_m": 6.0,
        "interpolacao_densidade_area": False,
    }
    case.update(changes)
    return case


def _high(**changes):
    case = _base(
        altura_armazenamento_m=4.0,
        densidade_projeto_Lmin_m2=6.1,
        area_operacao_m2=186.0,
    )
    case.update(changes)
    return case


def test_empty_case_is_inconclusive_without_normative_defaults():
    result = ar.verifica_armazenamento_nbr16981({})

    assert result["OK"] is False
    assert result["inconclusivo"] is True
    assert "mercadoria_risco_mais_grave_declarada" in result["faltantes"]
    assert "altura_armazenamento_m" in result["faltantes"]
    assert "altura_teto_m" in result["faltantes"]


def test_complete_storage_up_to_37m_is_ok():
    result = ar.verifica_armazenamento_nbr16981(_base())

    assert result["OK"] is True
    assert result["inconclusivo"] is False
    assert result["violacoes"] == []
    assert result["requisitos_aplicados"]


@pytest.mark.parametrize(
    "changes",
    (
        {"densidade_projeto_Lmin_m2": 6.0, "area_operacao_m2": 186.0},
        {"densidade_projeto_Lmin_m2": 6.1, "area_operacao_m2": 185.9},
    ),
)
def test_high_storage_rejects_density_or_operation_area_below_limit(changes):
    result = ar.verifica_armazenamento_nbr16981(_high(**changes))

    assert result["OK"] is False
    assert result["inconclusivo"] is False
    assert result["violacoes"]


def test_high_storage_missing_density_or_area_is_inconclusive():
    result = ar.verifica_armazenamento_nbr16981(
        _base(altura_armazenamento_m=4.0)
    )

    assert result["OK"] is False
    assert result["inconclusivo"] is True
    assert "densidade_projeto_Lmin_m2" in result["faltantes"]
    assert "area_operacao_m2" in result["faltantes"]


def test_interpolation_is_a_known_violation():
    result = ar.verifica_armazenamento_nbr16981(
        _high(interpolacao_densidade_area=True)
    )

    assert result["OK"] is False
    assert result["inconclusivo"] is False
    assert any("interpola" in item.casefold() for item in result["violacoes"])


def test_encapsulated_storage_requires_at_least_25_percent_density_increase():
    result = ar.verifica_armazenamento_nbr16981(
        _base(
            armazenamento_encapsulado=True,
            densidade_base_Lmin_m2=8.0,
            densidade_projeto_Lmin_m2=10.0,
        )
    )

    assert result["OK"] is True
    assert result["inconclusivo"] is False

    rejected = ar.verifica_armazenamento_nbr16981(
        _base(
            armazenamento_encapsulado=True,
            densidade_base_Lmin_m2=8.0,
            densidade_projeto_Lmin_m2=9.99,
        )
    )
    assert rejected["OK"] is False
    assert rejected["inconclusivo"] is False
    assert rejected["violacoes"]


def test_esfr_requires_smoke_condition_twelve_sprinklers_and_three_branches():
    result = ar.verifica_armazenamento_nbr16981(
        _base(
            sistema_esfr=True,
            sem_extracao_ou_barreira_fumaca=True,
            n_chuveiros_operacao=12,
            n_ramais_operacao=3,
        )
    )

    assert result["OK"] is True

    rejected = ar.verifica_armazenamento_nbr16981(
        _base(
            sistema_esfr=True,
            sem_extracao_ou_barreira_fumaca=True,
            n_chuveiros_operacao=11,
            n_ramais_operacao=2,
        )
    )
    assert rejected["OK"] is False
    assert rejected["inconclusivo"] is False
    assert len(rejected["violacoes"]) >= 2


def test_intrarack_storage_checks_area_without_inventing_undetermined_flow_limit():
    result = ar.verifica_armazenamento_nbr16981(
        _high(
            chuveiros_intraprateleiras=True,
            area_porta_paletes_m2=3700.0,
        )
    )
    assert result["OK"] is True

    rejected = ar.verifica_armazenamento_nbr16981(
        _high(
            chuveiros_intraprateleiras=True,
            area_porta_paletes_m2=3700.1,
        )
    )
    assert rejected["OK"] is False
    assert rejected["inconclusivo"] is False
    assert rejected["violacoes"]


def test_paper_coils_require_high_temperature_and_area_density_range():
    result = ar.verifica_armazenamento_nbr16981(
        _high(
            altura_armazenamento_m=4.6,
            bobinas_papel=True,
            chuveiro_temperatura_alta=True,
            metodo_area_densidade=True,
            area_por_chuveiro_m2=6.5,
        )
    )
    assert result["OK"] is True

    rejected = ar.verifica_armazenamento_nbr16981(
        _high(
            altura_armazenamento_m=4.6,
            bobinas_papel=True,
            chuveiro_temperatura_alta=False,
            metodo_area_densidade=True,
            area_por_chuveiro_m2=9.31,
        )
    )
    assert rejected["OK"] is False
    assert rejected["inconclusivo"] is False
    assert len(rejected["violacoes"]) >= 2


def test_tissue_above_61m_remains_inconclusive_without_invented_criterion():
    result = ar.verifica_armazenamento_nbr16981(
        _high(altura_armazenamento_m=6.2, papel_tissue=True)
    )

    assert result["OK"] is False
    assert result["inconclusivo"] is True
    assert result["violacoes"] == []
    assert any("tissue" in item.casefold() for item in result["faltantes"])
