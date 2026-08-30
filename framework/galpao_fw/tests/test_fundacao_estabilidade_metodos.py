"""Contrato dos métodos de estabilidade de fundações rasas.

Fase 49: os testes começam pelo contrato público e devem falhar antes de qualquer
alteração no motor de fundacao_sapata.
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import fundacao_sapata as fs


def test_normaliza_nbr_usa_fatores_e_tipo_de_acao():
    caso = {"verificacao_estabilidade": {
        "metodo": "nbr6122_valores_calculo",
        "tipo_acoes": "caracteristicas",
        "N_acao_desfavoravel_kN": 80.0,
        "peso_favoravel_superestrutura_kN": 20.0,
    }}

    resultado = fs.normaliza_verificacao(caso)

    assert resultado["metodo"] == "nbr6122_valores_calculo"
    assert resultado["tipo_acoes"] == "caracteristicas"
    assert resultado["gamma_f"] == pytest.approx(1.4)
    assert resultado["gamma_peso_favoravel"] == pytest.approx(1.2)


def test_normaliza_legacy_exige_fs_explicito():
    caso = {"verificacao_estabilidade": {
        "metodo": "fs_global_legacy",
        "tipo_acoes": "caracteristicas",
    }}

    with pytest.raises(ValueError, match="fs_tombamento|fs_deslizamento"):
        fs.normaliza_verificacao(caso)


def test_normaliza_sem_configuracao_marca_compatibilidade():
    resultado = fs.normaliza_verificacao({})

    assert resultado["metodo"] == "compatibilidade_legacy"
    assert resultado["avisos"]


def _caso_base(**extra):
    caso = {
        "N": 100.0,
        "V": 0.0,
        "M": 0.0,
        "B": 2.0,
        "L": 2.0,
        "h": 0.40,
        "mu": 0.50,
        "coesao": 0.0,
        "sigma_solo_adm": 250.0,
        "fck": 25e3,
        "fyk": 500e3,
        "h_reaterro": 0.0,
        "d_ped": 0.30,
        "b_ped": 0.30,
        "h_ped": 0.50,
    }
    caso.update(extra)
    return caso


def test_nbr_calculo_nao_reaplica_gamma_f_em_v_m():
    resultado = fs.verifica_sapata_A(_caso_base(
        V=20.0,
        M=10.0,
        verificacao_estabilidade={
            "metodo": "nbr6122_valores_calculo",
            "tipo_acoes": "calculo",
        },
    ))

    assert resultado["tipo_acoes"] == "calculo"
    assert resultado["fatores_verificacao"]["gamma_f"] == pytest.approx(1.4)
    assert resultado["V_verificacao"] == pytest.approx(20.0)
    assert resultado["M_verificacao"] == pytest.approx(10.0)
    assert resultado["limite_area_comprimida"] == pytest.approx(0.50)


def test_nbr_caracteristico_majora_v_m_e_mostra_limite_de_contato():
    resultado = fs.verifica_sapata_A(_caso_base(
        V=20.0,
        M=10.0,
        verificacao_estabilidade={
            "metodo": "nbr6122_valores_calculo",
            "tipo_acoes": "caracteristicas",
            "N_acao_desfavoravel_kN": 100.0,
            "peso_favoravel_superestrutura_kN": 0.0,
        },
    ))

    assert resultado["V_verificacao"] == pytest.approx(28.0)
    assert resultado["M_verificacao"] == pytest.approx(14.0)
    assert resultado["limite_area_comprimida"] == pytest.approx(2.0 / 3.0)


def test_contato_legado_caracteristico_exige_dois_tercos():
    resultado = fs.verifica_sapata_A(_caso_base(
        M=120.0,
        verificacao_estabilidade={
            "metodo": "fs_global_legacy",
            "tipo_acoes": "caracteristicas",
            "fs_tombamento": 1.0,
            "fs_deslizamento": 1.0,
        },
    ))

    assert resultado["limite_area_comprimida"] == pytest.approx(2.0 / 3.0)
    assert resultado["area_comprimida_ratio"] < resultado["limite_area_comprimida"]
    assert not resultado["ok_contato"]


def test_empuxo_passivo_so_entra_com_solo_nao_removivel():
    caso = _caso_base(
        V=80.0,
        M=20.0,
        verificacao_estabilidade={
            "metodo": "nbr6122_valores_calculo",
            "tipo_acoes": "calculo",
            "empuxo_passivo_kN": 100.0,
        },
    )
    sem_solo_permanente = fs.verifica_sapata_A(caso)
    caso["verificacao_estabilidade"]["solo_nao_removivel"] = True
    com_solo_permanente = fs.verifica_sapata_A(caso)

    assert sem_solo_permanente["empuxo_passivo_verificacao_kN"] == pytest.approx(0.0)
    assert com_solo_permanente["empuxo_passivo_verificacao_kN"] == pytest.approx(50.0 / 1.4)
    assert any("remov" in aviso.lower() for aviso in sem_solo_permanente["avisos_verificacao"])


def test_nbr_rejeita_fs_global_misturado():
    caso = _caso_base(verificacao_estabilidade={
        "metodo": "nbr6122_valores_calculo",
        "tipo_acoes": "calculo",
        "fs_tombamento": 1.5,
        "fs_deslizamento": 1.5,
    })

    with pytest.raises(ValueError, match="FS|fs"):
        fs.verifica_sapata_A(caso)


def test_sem_configuracao_e_compatibilidade_explicita():
    resultado = fs.verifica_sapata_A(_caso_base())

    assert resultado["metodo_verificacao"] == "compatibilidade_legacy"
    assert any("legado" in aviso.lower() for aviso in resultado["avisos_verificacao"])


def test_nbr_caracteristico_sem_decomposicao_vertical_fica_inconclusivo():
    resultado = fs.verifica_sapata_A(_caso_base(
        V=20.0,
        M=10.0,
        verificacao_estabilidade={
            "metodo": "nbr6122_valores_calculo",
            "tipo_acoes": "caracteristicas",
        },
    ))

    assert resultado["inconclusivo"] is True
    assert resultado["OK_A"] is False
    assert any("decompos" in aviso.lower() for aviso in resultado["avisos_verificacao"])


def test_relatorio_do_envelope_declara_metodo_e_limite_de_contato():
    caso = _caso_base(verificacao_estabilidade={
        "metodo": "nbr6122_valores_calculo",
        "tipo_acoes": "calculo",
    })
    dimensao = fs.dimensiona_sapata_env(caso, [("C1", 100.0, 0.0, 0.0)])

    assert "nbr6122_valores_calculo" in dimensao["tabela"]
    assert "50%" in dimensao["tabela"]


def test_relatorio_sapata_usa_fs_legacy_configurado():
    caso = _caso_base(verificacao_estabilidade={
        "metodo": "fs_global_legacy",
        "tipo_acoes": "caracteristicas",
        "fs_tombamento": 1.2,
        "fs_deslizamento": 1.3,
    })
    dimensao = fs.dimensiona_sapata(caso)

    assert "FS_tomb>=1,2" in dimensao["tabela"]
    assert "FS_desl>=1,3" in dimensao["tabela"]
