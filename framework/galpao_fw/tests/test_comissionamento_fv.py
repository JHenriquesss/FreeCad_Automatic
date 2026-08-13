"""Testes do checklist rastreÃ¡vel de comissionamento fotovoltaico."""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import comissionamento_fv as cf


CHECKLIST_IDS = (
    "documentacao_sistema",
    "diagrama_unifilar",
    "diagrama_especificacoes_arranjo",
    "diagrama_informacoes_series",
    "diagrama_detalhes_arranjo_cc",
    "diagrama_aterramento_sobretensao",
    "inspecao_projeto_iec",
    "inspecao_componentes_cc",
    "inspecao_isolamento_classe_ii",
    "inspecao_cabos_curto_falta",
    "inspecao_cabos_influencias",
    "inspecao_ir_corrente_reversa",
    "inspecao_protecao_sobrecorrente",
    "inspecao_desconexao_series",
    "inspecao_chave_cc_inversor",
    "inspecao_diodos_bloqueio",
    "inspecao_condutor_terra_cc",
    "inspecao_conectores_cc",
    "inspecao_sinalizacao_circuitos",
    "inspecao_sinalizacao_caixas",
    "inspecao_sinalizacao_interconexao",
    "inspecao_diagrama_local",
    "inspecao_configuracoes_inversor",
    "inspecao_desligamento_emergencia",
    "inspecao_durabilidade_sinais",
    "inspecao_ventilacao",
    "inspecao_corrosao",
    "inspecao_fixacao_intemperies",
    "inspecao_entradas_cabos",
    "continuidade_terra",
    "polaridade_cc",
    "corrente_isc",
    "tensao_voc",
    "ensaios_funcionais",
    "isolamento_cc",
    "relatorio_sistema",
    "relatorio_circuitos",
    "relatorio_fotografico",
    "relatorio_resultados_ensaios",
    "relatorio_proxima_verificacao",
    "relatorio_assinatura",
)

EXPECTED_SECTIONS = {
    "documentacao_sistema": "4.2.1",
    "diagrama_unifilar": "4.3.1",
    "diagrama_especificacoes_arranjo": "4.3.2",
    "diagrama_informacoes_series": "4.3.3",
    "diagrama_detalhes_arranjo_cc": "4.3.4",
    "diagrama_aterramento_sobretensao": "4.3.5",
    "inspecao_projeto_iec": "5.2.2, alinea a",
    "inspecao_isolamento_classe_ii": "5.2.2, alinea c",
    "inspecao_cabos_curto_falta": "5.2.2, alinea d",
    "inspecao_cabos_influencias": "5.2.2, alinea e",
    "inspecao_ir_corrente_reversa": "5.2.2, alinea f",
    "inspecao_protecao_sobrecorrente": "5.2.2, alinea g",
    "inspecao_desconexao_series": "5.2.2, alinea h",
    "inspecao_chave_cc_inversor": "5.2.2, alinea i",
    "inspecao_diodos_bloqueio": "5.2.2, alinea j",
    "inspecao_condutor_terra_cc": "5.2.2, alinea k",
    "inspecao_componentes_cc": "5.2.2, alinea b",
    "inspecao_conectores_cc": "5.2.2, alinea l",
    "inspecao_sinalizacao_circuitos": "5.2.5, alinea a",
    "inspecao_sinalizacao_caixas": "5.2.5, alinea b",
    "inspecao_sinalizacao_interconexao": "5.2.5, alinea c",
    "inspecao_diagrama_local": "5.2.5, alinea d",
    "inspecao_configuracoes_inversor": "5.2.5, alinea e",
    "inspecao_desligamento_emergencia": "5.2.5, alinea f",
    "inspecao_durabilidade_sinais": "5.2.5, alinea g",
    "inspecao_ventilacao": "5.2.6, alinea a",
    "inspecao_corrosao": "5.2.6, alinea b",
    "inspecao_fixacao_intemperies": "5.2.6, alinea c",
    "inspecao_entradas_cabos": "5.2.6, alinea d",
    "continuidade_terra": "6.1",
    "polaridade_cc": "6.2",
    "corrente_isc": "6.4.2",
    "tensao_voc": "6.5",
    "ensaios_funcionais": "6.6",
    "isolamento_cc": "6.7.3, Tabela 1",
    "relatorio_sistema": "9.1, alinea a",
    "relatorio_circuitos": "9.1, alinea b",
    "relatorio_fotografico": "9.1, alinea c",
    "relatorio_resultados_ensaios": "9.1, alinea d",
    "relatorio_proxima_verificacao": "9.1, alinea e",
    "relatorio_assinatura": "9.1, alinea f",
}


def _por_id(itens):
    return {item["id"]: item for item in itens}


def test_montar_checklist_tem_ordem_estavel_e_referencias_rastreaveis():
    primeiro = cf.montar_checklist_comissionamento_fv()
    segundo = cf.montar_checklist_comissionamento_fv()

    assert primeiro == segundo
    assert primeiro is not segundo
    assert [item["id"] for item in primeiro] == list(CHECKLIST_IDS)
    assert {item["id"]: item["secao"] for item in primeiro} == EXPECTED_SECTIONS
    assert {item["grupo"] for item in primeiro} == {
        "documentacao",
        "inspecao",
        "ensaio",
        "relatorio",
    }
    assert all(
        set(item) >= {"id", "grupo", "tipo", "secao", "criterio", "referencia"}
        for item in primeiro
    )
    assert all(
        item["referencia"]["norma"] == "ABNT NBR 16274:2014"
        and item["referencia"]["source_id"]
        == "4e6d55ec-65cf-4fc0-bf03-0d2648a6f731"
        for item in primeiro
    )

    primeiro[0]["referencia"]["secao"] = "alterada no consumidor"
    assert segundo[0]["referencia"]["secao"] != "alterada no consumidor"


def test_validar_estados_qualitativos_e_precedencia_do_resultado():
    resultado = cf.validar_comissionamento_fv(
        {
            "verificacoes": {
                "documentacao_sistema": True,
                "diagrama_unifilar": {"status": "APROVADO", "observacao": "emitido"},
                "inspecao_componentes_cc": False,
                "inspecao_sinalizacao_circuitos": {"status": "REVISAO_MANUAL"},
            }
        }
    )

    itens = _por_id(resultado["itens"])
    assert itens["documentacao_sistema"]["status"] == "APROVADO"
    assert itens["diagrama_unifilar"]["status"] == "APROVADO"
    assert itens["inspecao_componentes_cc"]["status"] == "REPROVADO"
    assert itens["inspecao_sinalizacao_circuitos"]["status"] == "REVISAO_MANUAL"
    assert itens["inspecao_ventilacao"]["status"] == "NAO_AVALIADO"
    assert resultado["status"] == "REPROVADO"
    assert resultado["ok"] is False
    assert resultado["referencias"]


def test_referencias_de_cada_item_preservam_a_secao_exata():
    itens = _por_id(cf.montar_checklist_comissionamento_fv())

    assert {
        item_id: item["referencia"]["secao"]
        for item_id, item in itens.items()
    } == EXPECTED_SECTIONS


def test_chaves_desconhecidas_em_verificacoes_nao_podem_aprovar_o_caso():
    verificacoes = {
        item_id: True
        for item_id in CHECKLIST_IDS
        if item_id not in {"corrente_isc", "tensao_voc", "isolamento_cc"}
    }
    verificacoes.update({
        "corrente_isc": {"medido_a": 10.0, "referencia_a": 10.0, "confirmado": True},
        "tensao_voc": {"medido_v": 1000.0, "referencia_v": 1000.0, "confirmado": True},
        "isolamento_cc": {
            "metodo": "metodo_1", "voc_stc_v": 240.0,
            "tensao_ensaio_v": 500.0, "resistencia_mohm": 1.0,
        },
        "campo_inventado": True,
    })

    resultado = cf.validar_comissionamento_fv({"verificacoes": verificacoes})

    assert resultado["ok"] is False
    assert resultado["status"] == "NAO_AVALIADO"
    assert any(falha["codigo"] == "CHAVE_DESCONHECIDA" for falha in resultado["falhas"])


def test_registro_qualitativo_com_campos_desconhecidos_nao_aprova():
    resultado = cf.validar_comissionamento_fv({
        "verificacoes": {
            "documentacao_sistema": {"status": "APROVADO", "campo_inventado": True},
        }
    })

    item = _por_id(resultado["itens"])["documentacao_sistema"]
    assert item["status"] == "NAO_AVALIADO"
    assert resultado["ok"] is False
    assert any(falha["codigo"] == "CAMPO_DESCONHECIDO" for falha in resultado["falhas"])


@pytest.mark.parametrize(
    "item_id, registro",
    [
        (
            "tensao_voc",
            {"medido_v": 1000.0, "referencia_v": 1000.0, "confirmado": True, "extra": 1},
        ),
        (
            "corrente_isc",
            {"medido_a": 10.0, "referencia_a": 10.0, "confirmado": True, "extra": 1},
        ),
        (
            "isolamento_cc",
            {
                "metodo": "metodo_1", "voc_stc_v": 240.0,
                "tensao_ensaio_v": 500.0, "resistencia_mohm": 1.0, "extra": 1,
            },
        ),
    ],
)
def test_registros_quantitativos_com_campos_desconhecidos_nao_aprovam(item_id, registro):
    resultado = cf.validar_comissionamento_fv(_caso_quantitativo(**{item_id: registro}))

    item = _por_id(resultado["itens"])[item_id]
    assert item["status"] == "NAO_AVALIADO"
    assert resultado["ok"] is False
    assert any(
        falha["codigo"] == "CAMPO_DESCONHECIDO" and falha["item_id"] == item_id
        for falha in resultado["falhas"]
    )


def test_chaves_desconhecidas_com_tipos_mistos_nao_causam_crash():
    caso = _caso_quantitativo()
    caso["verificacoes"][1] = True
    caso["verificacoes"]["campo_inventado"] = True

    resultado = cf.validar_comissionamento_fv(caso)

    assert resultado["status"] == "NAO_AVALIADO"
    assert resultado["ok"] is False
    assert sum(falha["codigo"] == "CHAVE_DESCONHECIDA" for falha in resultado["falhas"]) == 2


def test_chave_desconhecida_nao_esconde_reprovacao_mais_grave():
    caso = _caso_quantitativo()
    caso["verificacoes"]["campo_inventado"] = True
    caso["verificacoes"]["inspecao_projeto_iec"] = False

    resultado = cf.validar_comissionamento_fv(caso)

    assert resultado["status"] == "REPROVADO"
    assert resultado["ok"] is False


def test_caso_sem_verificacoes_e_nao_avaliado():
    resultado = cf.validar_comissionamento_fv({})

    assert resultado["status"] == "NAO_AVALIADO"
    assert resultado["ok"] is False
    assert len(resultado["itens"]) == len(CHECKLIST_IDS)
    assert {item["status"] for item in resultado["itens"]} == {"NAO_AVALIADO"}
    assert any(item["codigo"] == "ENTRADA_AUSENTE" for item in resultado["falhas"])


def _caso_quantitativo(**changes):
    verificacoes = {
        item_id: True
        for item_id in CHECKLIST_IDS
        if item_id not in {"corrente_isc", "tensao_voc", "isolamento_cc"}
    }
    verificacoes.update({
        "tensao_voc": {
            "medido_v": 1000.0,
            "referencia_v": 1000.0,
            "confirmado": True,
        },
        "corrente_isc": {
            "medido_a": 10.0,
            "referencia_a": 10.0,
            "confirmado": True,
        },
        "isolamento_cc": {
            "metodo": "metodo_1",
            "voc_stc_v": 240.0,
            "tensao_ensaio_v": 500.0,
            "resistencia_mohm": 1.0,
        },
    })
    verificacoes.update(changes)
    return {"verificacoes": verificacoes}


def test_voc_e_isc_aprovados_com_confirmacao_e_desvio_calculado():
    resultado = cf.validar_comissionamento_fv(_caso_quantitativo())
    itens = _por_id(resultado["itens"])

    assert itens["tensao_voc"]["status"] == "APROVADO"
    assert itens["tensao_voc"]["valores"]["desvio_percentual"] == 0.0
    assert itens["corrente_isc"]["status"] == "APROVADO"
    assert itens["corrente_isc"]["valores"]["desvio_percentual"] == 0.0
    assert resultado["status"] == "APROVADO"
    assert resultado["ok"] is True


def test_voc_e_isc_fora_do_valor_tipico_exigem_revisao_sem_reprovar_automaticamente():
    resultado = cf.validar_comissionamento_fv(_caso_quantitativo(
        tensao_voc={"medido_v": 1060.0, "referencia_v": 1000.0, "confirmado": False},
        corrente_isc={"medido_a": 10.6, "referencia_a": 10.0, "confirmado": False},
    ))
    itens = _por_id(resultado["itens"])

    assert itens["tensao_voc"]["status"] == "REVISAO_MANUAL"
    assert itens["corrente_isc"]["status"] == "REVISAO_MANUAL"
    assert resultado["status"] == "REVISAO_MANUAL"
    assert not any(
        falha["item_id"] in {"tensao_voc", "corrente_isc"}
        and falha["codigo"] == "LIMITE_EXCEDIDO"
        for falha in resultado["falhas"]
    )
    assert any("5%" in aviso["mensagem"] for aviso in resultado["avisos"])


@pytest.mark.parametrize(
    "tensao_sistema, voc_stc, tensao_ensaio, minimo",
    [
        (119.99, 119.99 / 1.25, 250.0, 0.5),
        (120.0, 120.0 / 1.25, 500.0, 1.0),
        (500.0, 500.0 / 1.25, 500.0, 1.0),
        (500.01, 500.01 / 1.25, 1000.0, 1.0),
    ],
)
def test_isolamento_aplica_tabela_1_nas_faixas_e_fronteiras(
    tensao_sistema, voc_stc, tensao_ensaio, minimo
):
    resultado = cf.validar_comissionamento_fv(_caso_quantitativo(
        isolamento_cc={
            "metodo": "metodo_1",
            "voc_stc_v": voc_stc,
            "tensao_ensaio_v": tensao_ensaio,
            "resistencia_mohm": minimo,
        }
    ))

    item = _por_id(resultado["itens"])["isolamento_cc"]
    assert item["status"] == "APROVADO"
    assert item["valores"]["tensao_sistema_v"] == pytest.approx(tensao_sistema)
    assert item["valores"]["resistencia_minima_mohm"] == minimo


def test_isolamento_reprova_tensao_de_ensaio_errada_ou_resistencia_insuficiente():
    tensao_errada = cf.validar_comissionamento_fv(_caso_quantitativo(
        isolamento_cc={
            "metodo": "metodo_1",
            "voc_stc_v": 240.0,
            "tensao_ensaio_v": 250.0,
            "resistencia_mohm": 10.0,
        }
    ))
    resistencia_baixa = cf.validar_comissionamento_fv(_caso_quantitativo(
        isolamento_cc={
            "metodo": "metodo_2",
            "voc_stc_v": 560.0,
            "tensao_ensaio_v": 1000.0,
            "resistencia_mohm": 0.99,
        }
    ))

    assert _por_id(tensao_errada["itens"])["isolamento_cc"]["status"] == "REPROVADO"
    assert _por_id(resistencia_baixa["itens"])["isolamento_cc"]["status"] == "REPROVADO"


def test_isolamento_nao_aceita_tensao_sistema_informada_sem_voc_stc():
    resultado = cf.validar_comissionamento_fv(_caso_quantitativo(
        isolamento_cc={
            "metodo": "metodo_1",
            "tensao_sistema_v": 300.0,
            "tensao_ensaio_v": 500.0,
            "resistencia_mohm": 1.0,
        }
    ))

    item = _por_id(resultado["itens"])["isolamento_cc"]
    assert item["status"] == "NAO_AVALIADO"
    assert any(falha["codigo"] == "CAMPO_DESCONHECIDO" for falha in resultado["falhas"])


@pytest.mark.parametrize(
    "registro",
    [
        {"metodo": "metodo_1", "voc_stc_v": 0, "tensao_ensaio_v": 250, "resistencia_mohm": 1},
        {"metodo": "metodo_1", "voc_stc_v": float("inf"), "tensao_ensaio_v": 250, "resistencia_mohm": 1},
        {"metodo": "desconhecido", "voc_stc_v": 100, "tensao_ensaio_v": 250, "resistencia_mohm": 1},
        {"metodo": "metodo_1", "voc_stc_v": 100, "tensao_ensaio_v": 250, "resistencia_mohm": -1},
        {"metodo": "metodo_1", "voc_stc_v": 1.5e308, "tensao_ensaio_v": 1000, "resistencia_mohm": 1},
    ],
)
def test_entradas_invalidas_de_ensaios_nao_criam_aprovacao(registro):
    resultado = cf.validar_comissionamento_fv(_caso_quantitativo(isolamento_cc=registro))

    item = _por_id(resultado["itens"])["isolamento_cc"]
    assert item["status"] == "NAO_AVALIADO"
    assert resultado["ok"] is False


def test_desvio_quantitativo_que_estoura_float_nao_vaza_inf_ou_aprovacao():
    resultado = cf.validar_comissionamento_fv(_caso_quantitativo(
        tensao_voc={
            "medido_v": 1.0e308,
            "referencia_v": 1.0e-308,
            "confirmado": True,
        }
    ))

    item = _por_id(resultado["itens"])["tensao_voc"]
    assert item["status"] == "NAO_AVALIADO"
    assert resultado["ok"] is False
    assert all(
        valor == valor and valor not in {float("inf"), float("-inf")}
        for valor in item.get("valores", {}).values()
        if isinstance(valor, float)
    )
