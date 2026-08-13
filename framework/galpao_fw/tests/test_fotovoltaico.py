"""Sistema fotovoltaico na cobertura (on-grid): area -> potencia -> geracao ->
compensacao do consumo. HSP e catalogo A CONFIRMAR. Camada PURA (CI)."""
import math
import os
import sys

from xml.dom.minidom import parseString

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import fotovoltaico as fv


def _caso_compatibilidade(**changes):
    caso = {
        "voc_modulo_v": 49.5,
        "modulos_serie": 20,
        "isc_modulo_a": 13.2,
        "series_paralelo": 1,
        "fator_correcao_tensao": 1.10,
        "componentes_cc": [{
            "nome": "inversor",
            "tensao_nominal_v": 1200.0,
            "corrente_nominal_a": 20.0,
            "adequado_cc": True,
        }],
        "usa_conectores": False,
    }
    caso.update(changes)
    return caso


def test_selftest():
    assert fv._selftest() is True


def test_potencia_instalavel():
    # 1000 m2 x 0,7 x 0,18 = 126 kWp
    assert abs(fv.potencia_instalavel(1000.0) - 126.0) < 1e-9
    with pytest.raises(ValueError):
        fv.potencia_instalavel(0)


def test_geracao_formula_cresesb():
    # E = P.HSP.PR ; 100 kWp x 5 x 0,78 = 390 kWh/dia
    g = fv.geracao(100.0, 5.0)
    assert abs(g["kwh_dia"] - 390.0) < 1e-9
    assert abs(g["kwh_ano"] - 390.0 * 365) < 1e-6
    with pytest.raises(ValueError):
        fv.geracao(100.0, 0)          # HSP nao informado


def test_n_modulos_e_inversores():
    assert fv.n_modulos(100.0) == math.ceil(100000.0 / 550.0)
    assert fv.n_inversores(100.0, 75.0) == 2
    with pytest.raises(ValueError):
        fv.n_inversores(100.0, 0)


def test_dimensiona_limitado_por_area():
    r = fv.dimensiona_fv({"area_cobertura_m2": 500.0, "HSP": 5.0,
                          "consumo_kwh_mes": 100000.0})
    assert r["OK"] and r["limitado_por"].startswith("area")
    assert r["potencia_kWp"] == r["potencia_teto_area_kWp"]
    assert r["cobertura_consumo_pct"] < 100.0


def test_dimensiona_limitado_por_consumo():
    r = fv.dimensiona_fv({"area_cobertura_m2": 2000.0, "HSP": 5.5,
                          "consumo_kwh_mes": 20000.0})
    assert r["limitado_por"].startswith("consumo")
    assert r["potencia_kWp"] < r["potencia_teto_area_kWp"]
    assert abs(r["cobertura_consumo_pct"] - 100.0) < 3.0


def test_sem_hsp_a_confirmar():
    r = fv.dimensiona_fv({"area_cobertura_m2": 800.0})
    assert r["OK"] is False and "A CONFIRMAR" in r["motivo"]
    assert r["potencia_teto_area_kWp"] > 0        # teto de area ainda e' util


def test_consumo_por_demanda_horas():
    r = fv.dimensiona_fv({"area_cobertura_m2": 2000.0, "HSP": 5.0,
                          "demanda_kW": 50.0, "horas_dia": 8.0})
    assert r["consumo_kwh_mes"] == round(50.0 * 8.0 * fv.DIAS_MES, 1)


def test_pr_e_hsp_ecoados_sem_arredondar():
    """PR e HSP sao inputs ecoados; nao devem virar 0,8 por arredondamento."""
    r = fv.dimensiona_fv({"area_cobertura_m2": 800.0, "HSP": 5.2,
                          "consumo_kwh_mes": 18000.0})
    assert r["geracao"]["PR"] == fv.PR_PADRAO      # 0,78 (nao 0,8)
    assert r["geracao"]["HSP"] == 5.2


def test_area_invalida_levanta():
    with pytest.raises(ValueError):
        fv.dimensiona_fv({"area_cobertura_m2": 0, "HSP": 5.0})


def test_grafico_svg_xml_valido():
    r = fv.dimensiona_fv({"area_cobertura_m2": 800.0, "HSP": 5.2,
                          "consumo_kwh_mes": 18000.0})
    svg = fv.grafico_svg(r)
    assert svg.startswith("<svg") and "SISTEMA FOTOVOLTAICO" in svg
    parseString(svg.encode("utf-8"))
    parseString(fv.grafico_svg({"OK": False, "motivo": "x"}).encode("utf-8"))


def test_validar_compatibilidade_arranjo_fv_calcula_limites_cc():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_compatibilidade())

    assert resultado["ok"] is True
    assert resultado["falhas"] == []
    assert resultado["avisos"] == []
    assert resultado["valores_calculados"]["voc_arranjo_v"] == 990.0
    assert resultado["valores_calculados"]["v_max_arranjo_v"] == 1089.0
    assert resultado["valores_calculados"]["isc_arranjo_a"] == 13.2
    assert resultado["valores_calculados"]["corrente_minima_arranjo_a"] == 16.5
    assert resultado["valores_calculados"]["corrente_referencia_componentes_a"] == 16.5
    assert resultado["valores_calculados"]["protecao_series_requerida"] is False
    assert resultado["referencias"]


def test_validar_compatibilidade_arranjo_fv_aceita_tensao_maxima_do_fabricante():
    resultado = fv.validar_compatibilidade_arranjo_fv(
        _caso_compatibilidade(
            fator_correcao_tensao=None,
            v_max_arranjo_v=1089.0,
        )
    )

    assert resultado["ok"] is True
    assert resultado["valores_calculados"]["voc_arranjo_v"] == 990.0
    assert resultado["valores_calculados"]["v_max_arranjo_v"] == 1089.0


@pytest.mark.parametrize(
    "changes",
    [
        {"fator_correcao_tensao": 1.10, "v_max_arranjo_v": 1089.0},
        {"fator_correcao_tensao": None},
    ],
)
def test_validar_compatibilidade_rejeita_tensao_maxima_ambigua(changes):
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_compatibilidade(**changes))

    assert resultado["ok"] is False
    assert "TENSAO_MAXIMA_AMBIGUA" in {item["codigo"] for item in resultado["falhas"]}


@pytest.mark.parametrize(
    "changes, codigo",
    [
        ({"voc_modulo_v": float("nan")}, "NUMERO_INVALIDO"),
        ({"voc_modulo_v": float("inf")}, "NUMERO_INVALIDO"),
        ({"voc_modulo_v": 0.0}, "NUMERO_INVALIDO"),
        ({"voc_modulo_v": -1.0}, "NUMERO_INVALIDO"),
        ({"voc_modulo_v": True}, "NUMERO_INVALIDO"),
        ({"modulos_serie": 0}, "NUMERO_INVALIDO"),
        ({"isc_modulo_a": False}, "NUMERO_INVALIDO"),
    ],
)
def test_validar_compatibilidade_rejeita_entradas_numericas_invalidas(changes, codigo):
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_compatibilidade(**changes))

    assert resultado["ok"] is False
    assert codigo in {item["codigo"] for item in resultado["falhas"]}


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("voc_modulo_v", 10**400),
        ("modulos_serie", 10**400),
        ("isc_modulo_a", 10**400),
        ("series_paralelo", 10**400),
        ("fator_correcao_tensao", 10**400),
    ],
)
def test_validar_compatibilidade_rejeita_inteiro_enorme_sem_excecao(campo, valor):
    resultado = fv.validar_compatibilidade_arranjo_fv(
        _caso_compatibilidade(**{campo: valor})
    )

    assert resultado["ok"] is False
    assert "NUMERO_INVALIDO" in {item["codigo"] for item in resultado["falhas"]}


def test_validar_compatibilidade_rejeita_overflow_de_calculo_sem_inf():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_compatibilidade(
        voc_modulo_v=10**308,
        modulos_serie=2,
        fator_correcao_tensao=2.0,
    ))

    assert resultado["ok"] is False
    assert "NUMERO_INVALIDO" in {item["codigo"] for item in resultado["falhas"]}
    assert all(
        value is None or math.isfinite(value)
        for value in resultado["valores_calculados"].values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    )


def test_validar_compatibilidade_rejeita_overflow_dos_limites_de_protecao():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_compatibilidade(
        isc_modulo_a=10**308,
        series_paralelo=1,
        imod_max_ocpr_a=10**308,
        protecao_series={
            "modo": "individual",
            "corrente_nominal_a": 20.0,
            "tipo": "gPV",
        },
    ))

    assert resultado["ok"] is False
    assert "NUMERO_INVALIDO" in {item["codigo"] for item in resultado["falhas"]}


def test_validar_compatibilidade_rejeita_overflow_dos_limites_agrupados():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_compatibilidade(
        isc_modulo_a=6e307,
        series_paralelo=2,
        imod_max_ocpr_a=1e308,
        componentes_cc=[{
            "nome": "caixa de junção",
            "tensao_nominal_v": 1200.0,
            "corrente_nominal_a": 1.5e308,
            "adequado_cc": True,
        }],
        protecao_series={
            "modo": "grupo",
            "corrente_nominal_a": 1.0,
            "tipo": "gPV",
            "series_grupo": 2,
        },
    ))

    assert resultado["ok"] is False
    assert "NUMERO_INVALIDO" in {item["codigo"] for item in resultado["falhas"]}


@pytest.mark.parametrize("valor", [(), ("gPV",)])
def test_validar_compatibilidade_rejeita_tipo_de_protecao_tuplado_sem_excecao(valor):
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_protecao(
        protecao_series={
            "modo": "individual",
            "corrente_nominal_a": 20.0,
            "tipo": valor,
        }
    ))

    assert resultado["ok"] is False
    assert "TIPO_PROTECAO_CC_INVALIDO" in {
        item["codigo"] for item in resultado["falhas"]
    }


def test_validar_compatibilidade_rejeita_campo_obrigatorio_ausente_sem_excecao():
    caso = _caso_compatibilidade()
    del caso["isc_modulo_a"]

    resultado = fv.validar_compatibilidade_arranjo_fv(caso)

    assert resultado["ok"] is False
    assert "ENTRADA_AUSENTE" in {item["codigo"] for item in resultado["falhas"]}


@pytest.mark.parametrize(
    "changes, codigo",
    [
        (
            {
                "componentes_cc": [{
                    "nome": "inversor",
                    "tensao_nominal_v": 1000.0,
                    "corrente_nominal_a": 20.0,
                    "adequado_cc": True,
                }]
            },
            "TENSAO_COMPONENTE_INSUFICIENTE",
        ),
        (
            {
                "componentes_cc": [{
                    "nome": "cabo",
                    "tensao_nominal_v": 1200.0,
                    "corrente_nominal_a": 10.0,
                    "adequado_cc": True,
                }]
            },
            "CORRENTE_COMPONENTE_INSUFICIENTE",
        ),
        (
            {
                "componentes_cc": [{
                    "nome": "componente-ca",
                    "tensao_nominal_v": 1200.0,
                    "corrente_nominal_a": 20.0,
                    "adequado_cc": False,
                }]
            },
            "COMPONENTE_NAO_CC",
        ),
    ],
)
def test_validar_compatibilidade_rejeita_componente_incompativel(changes, codigo):
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_compatibilidade(**changes))

    assert resultado["ok"] is False
    assert codigo in {item["codigo"] for item in resultado["falhas"]}


@pytest.mark.parametrize("nome", ["", None])
def test_validar_compatibilidade_rejeita_componente_sem_nome(nome):
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_compatibilidade(
        componentes_cc=[{
            "nome": nome,
            "tensao_nominal_v": 1200.0,
            "corrente_nominal_a": 20.0,
            "adequado_cc": True,
        }]
    ))

    assert resultado["ok"] is False
    assert "ENTRADA_AUSENTE" in {item["codigo"] for item in resultado["falhas"]}


def _caso_protecao(**changes):
    caso = _caso_compatibilidade(
        series_paralelo=3,
        imod_max_ocpr_a=25.0,
        componentes_cc=[{
            "nome": "caixa de junção",
            "tensao_nominal_v": 1200.0,
            "corrente_nominal_a": 50.0,
            "adequado_cc": True,
        }]
    )
    caso.update(changes)
    return caso


def test_validar_compatibilidade_usa_protecao_do_arranjo_na_referencia_de_corrente():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_protecao(
        protecao_arranjo={
            "corrente_nominal_a": 35.0,
            "tipo": "gPV",
        },
        protecao_series={
            "modo": "individual",
            "corrente_nominal_a": 20.0,
            "tipo": "gPV",
        },
    ))

    assert resultado["ok"] is True
    assert resultado["valores_calculados"]["isc_arranjo_a"] == pytest.approx(39.6)
    assert resultado["valores_calculados"]["corrente_minima_arranjo_a"] == pytest.approx(49.5)
    assert resultado["valores_calculados"]["corrente_referencia_componentes_a"] == pytest.approx(35.0)
    assert resultado["valores_calculados"]["protecao_series_requerida"] is True


def test_validar_compatibilidade_rejeita_protecao_de_series_ausente_quando_necessaria():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_protecao())

    assert resultado["ok"] is False
    assert "PROTECAO_SERIE_AUSENTE" in {item["codigo"] for item in resultado["falhas"]}


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), True, 0.0, -1.0, "25"])
def test_validar_compatibilidade_rejeita_imod_max_ocpr_invalido(valor):
    resultado = fv.validar_compatibilidade_arranjo_fv(
        _caso_protecao(imod_max_ocpr_a=valor)
    )

    assert resultado["ok"] is False
    assert "NUMERO_INVALIDO" in {item["codigo"] for item in resultado["falhas"]}


def test_validar_compatibilidade_rejeita_imod_max_ocpr_invalido_mesmo_sem_paralelo():
    resultado = fv.validar_compatibilidade_arranjo_fv(
        _caso_compatibilidade(imod_max_ocpr_a=float("nan"))
    )

    assert resultado["ok"] is False
    assert "NUMERO_INVALIDO" in {item["codigo"] for item in resultado["falhas"]}


def test_validar_compatibilidade_aceita_protecao_individual_valida():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_protecao(
        protecao_series={
            "modo": "individual",
            "corrente_nominal_a": 20.0,
            "tipo": "gPV",
        }
    ))

    assert resultado["ok"] is True


def test_validar_compatibilidade_rejeita_protecao_de_series_sem_limite_ocpr():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_compatibilidade(
        protecao_series={
            "modo": "individual",
            "corrente_nominal_a": 20.0,
            "tipo": "gPV",
        }
    ))

    assert resultado["ok"] is False
    assert "ENTRADA_AUSENTE" in {item["codigo"] for item in resultado["falhas"]}


@pytest.mark.parametrize(
    "corrente, esperado",
    [
        (19.8, False),
        (math.nextafter(19.8, math.inf), True),
        (31.68, False),
        (math.nextafter(31.68, -math.inf), True),
    ],
)
def test_validar_compatibilidade_respeita_limites_individuais_estritos(corrente, esperado):
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_protecao(
        imod_max_ocpr_a=40.0,
        protecao_series={
            "modo": "individual",
            "corrente_nominal_a": corrente,
            "tipo": "gPV",
        },
    ))

    assert resultado["ok"] is esperado


@pytest.mark.parametrize(
    "corrente, esperado",
    [
        (39.6, False),
        (math.nextafter(39.6, math.inf), True),
        (86.8, False),
        (math.nextafter(86.8, -math.inf), True),
    ],
)
def test_validar_compatibilidade_respeita_limites_agrupados_estritos(corrente, esperado):
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_protecao(
        series_paralelo=5,
        imod_max_ocpr_a=100.0,
        componentes_cc=[{
            "nome": "caixa de junção",
            "tensao_nominal_v": 1200.0,
            "corrente_nominal_a": 100.0,
            "adequado_cc": True,
        }],
        protecao_series={
            "modo": "grupo",
            "corrente_nominal_a": corrente,
            "tipo": "gPV",
            "series_grupo": 2,
        },
    ))

    assert resultado["ok"] is esperado


@pytest.mark.parametrize(
    "protecao, codigo",
    [
        (
            {
                "modo": "individual",
                "corrente_nominal_a": 19.8,
                "tipo": "gPV",
            },
            "PROTECAO_INDIVIDUAL_FORA_DA_FAIXA",
        ),
        (
            {
                "modo": "individual",
                "corrente_nominal_a": 20.0,
                "tipo": "disjuntor_ca",
            },
            "TIPO_PROTECAO_CC_INVALIDO",
        ),
    ],
)
def test_validar_compatibilidade_rejeita_protecao_individual_invalida(protecao, codigo):
    resultado = fv.validar_compatibilidade_arranjo_fv(
        _caso_protecao(protecao_series=protecao)
    )

    assert resultado["ok"] is False
    assert codigo in {item["codigo"] for item in resultado["falhas"]}


@pytest.mark.parametrize("campo", ["protecao_arranjo", "protecao_series"])
def test_validar_compatibilidade_rejeita_tipo_de_protecao_nao_hashavel(campo):
    caso = _caso_protecao(
        protecao_series={
            "modo": "individual",
            "corrente_nominal_a": 20.0,
            "tipo": "gPV",
        }
    )
    if campo == "protecao_arranjo":
        caso["protecao_arranjo"] = {
            "corrente_nominal_a": 35.0,
            "tipo": [],
        }
    else:
        caso["protecao_series"]["tipo"] = []

    resultado = fv.validar_compatibilidade_arranjo_fv(caso)

    assert resultado["ok"] is False
    assert "TIPO_PROTECAO_CC_INVALIDO" in {
        item["codigo"] for item in resultado["falhas"]
    }


def test_validar_compatibilidade_aceita_protecao_agrupada_valida():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_protecao(
        series_paralelo=5,
        imod_max_ocpr_a=100.0,
        componentes_cc=[{
            "nome": "caixa de junção",
            "tensao_nominal_v": 1200.0,
            "corrente_nominal_a": 100.0,
            "adequado_cc": True,
        }],
        protecao_series={
            "modo": "grupo",
            "corrente_nominal_a": 45.0,
            "tipo": "disjuntor_cc_60947-2",
            "series_grupo": 2,
        }
    ))

    assert resultado["ok"] is True


def test_validar_compatibilidade_rejeita_protecao_agrupada_invalida():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_protecao(
        series_paralelo=5,
        imod_max_ocpr_a=100.0,
        componentes_cc=[{
            "nome": "caixa de junção",
            "tensao_nominal_v": 1200.0,
            "corrente_nominal_a": 100.0,
            "adequado_cc": True,
        }],
        protecao_series={
            "modo": "grupo",
            "corrente_nominal_a": 45.0,
            "tipo": "disjuntor_cc_60947-2",
            "series_grupo": 6,
        }
    ))

    assert resultado["ok"] is False
    assert "PROTECAO_GRUPO_FORA_DA_FAIXA" in {
        item["codigo"] for item in resultado["falhas"]
    }


def _caso_conectores(**changes):
    caso = _caso_compatibilidade(
        usa_conectores=True,
        conectores={
            "macho": {"fabricante": "Fabricante A", "tipo": "PV-01"},
            "femea": {"fabricante": "Fabricante A", "tipo": "PV-01"},
        }
    )
    caso.update(changes)
    return caso


def test_validar_compatibilidade_aceita_conectores_do_mesmo_tipo_e_fabricante():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_conectores())

    assert resultado["ok"] is True


@pytest.mark.parametrize(
    "conectores, codigo",
    [
        (
            {
                "macho": {"fabricante": "Fabricante A", "tipo": "PV-01"},
                "femea": {"fabricante": "Fabricante B", "tipo": "PV-01"},
            },
            "CONECTOR_FABRICANTE_INCOMPATIVEL",
        ),
        (
            {
                "macho": {"fabricante": "Fabricante A", "tipo": "PV-01"},
                "femea": {"fabricante": "Fabricante A", "tipo": "PV-02"},
            },
            "CONECTOR_TIPO_INCOMPATIVEL",
        ),
    ],
)
def test_validar_compatibilidade_rejeita_conectores_incompativeis(conectores, codigo):
    resultado = fv.validar_compatibilidade_arranjo_fv(
        _caso_conectores(conectores=conectores)
    )

    assert resultado["ok"] is False
    assert codigo in {item["codigo"] for item in resultado["falhas"]}


def test_validar_compatibilidade_rejeita_conectores_ausentes():
    resultado = fv.validar_compatibilidade_arranjo_fv(
        _caso_compatibilidade(usa_conectores=True)
    )

    assert resultado["ok"] is False
    assert "ENTRADA_AUSENTE" in {item["codigo"] for item in resultado["falhas"]}


def test_validar_compatibilidade_retorna_referencias_de_todas_as_regras_aplicadas():
    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_conectores(
        series_paralelo=3,
        imod_max_ocpr_a=25.0,
        componentes_cc=[{
            "nome": "caixa de junção",
            "tensao_nominal_v": 1200.0,
            "corrente_nominal_a": 50.0,
            "adequado_cc": True,
        }],
        protecao_series={
            "modo": "individual",
            "corrente_nominal_a": 20.0,
            "tipo": "gPV",
        },
    ))

    secoes = {item["secao"] for item in resultado["referencias"]}
    assert {"3.1.42", "5.3.9", "5.3.11.1", "6.1.1", "6.1.3",
            "6.2.5", "6.2.8.1", "6.2.8.2"}.issubset(secoes)


@pytest.mark.parametrize("campo", ["fabricante", "tipo"])
def test_validar_compatibilidade_rejeita_campo_de_conector_ausente(campo):
    macho = {"fabricante": "Fabricante A", "tipo": "PV-01"}
    femea = {"fabricante": "Fabricante A", "tipo": "PV-01"}
    macho.pop(campo)
    femea.pop(campo)

    resultado = fv.validar_compatibilidade_arranjo_fv(_caso_compatibilidade(
        usa_conectores=True,
        conectores={"macho": macho, "femea": femea},
    ))

    assert resultado["ok"] is False
    assert "ENTRADA_AUSENTE" in {item["codigo"] for item in resultado["falhas"]}
