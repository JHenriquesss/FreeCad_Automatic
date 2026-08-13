"""Checklist rastreavel de comissionamento de sistemas fotovoltaicos.

The module is pure: it validates supplied commissioning evidence and never
pretends to perform a field measurement.
"""

from __future__ import annotations

from copy import deepcopy
import math


_SOURCE_ID = "4e6d55ec-65cf-4fc0-bf03-0d2648a6f731"
_NORMA = "ABNT NBR 16274:2014"
_STATUS = frozenset({"APROVADO", "REPROVADO", "REVISAO_MANUAL", "NAO_AVALIADO"})

def _referencia(secao):
    return {"norma": _NORMA, "secao": secao, "source_id": _SOURCE_ID}


def _item(item_id, grupo, tipo, secao, criterio):
    return {
        "id": item_id,
        "grupo": grupo,
        "tipo": tipo,
        "secao": secao,
        "criterio": criterio,
        "referencia": _referencia(secao),
    }


# The entries are deliberately split at the level of the auditable requirements
# returned by NotebookLM. A single True must not silently attest to an entire
# section containing several independent checks.
_CHECKLIST = (
    _item(
        "documentacao_sistema", "documentacao", "documento", "4.2.1",
        "Informacoes basicas do sistema devem ser fornecidas na documentacao.",
    ),
    _item(
        "diagrama_unifilar", "documentacao", "documento", "4.3.1",
        "Deve ser fornecido no minimo um diagrama unifilar do sistema.",
    ),
    _item(
        "diagrama_especificacoes_arranjo", "documentacao", "documento", "4.3.2",
        "O diagrama deve registrar modulos, quantidades, series e modulos por serie.",
    ),
    _item(
        "diagrama_informacoes_series", "documentacao", "documento", "4.3.3",
        "O diagrama deve registrar condutores, protecoes e diodos de bloqueio das series.",
    ),
    _item(
        "diagrama_detalhes_arranjo_cc", "documentacao", "documento", "4.3.4",
        "O diagrama deve registrar condutores, caixas, chaves e protecoes do arranjo c.c.",
    ),
    _item(
        "diagrama_aterramento_sobretensao", "documentacao", "documento", "4.3.5",
        "O diagrama deve registrar aterramento, equipotencializacao, SPDA e DPS c.a./c.c.",
    ),
    _item(
        "inspecao_projeto_iec", "inspecao", "inspecao", "5.2.2, alinea a",
        "O sistema c.c. deve ser projetado, especificado e instalado conforme IEC 60364 e IEC 60364-7-712.",
    ),
    _item(
        "inspecao_componentes_cc", "inspecao", "inspecao", "5.2.2, alinea b",
        "Componentes c.c. devem ser classificados para a maxima tensao e corrente de falta do sistema.",
    ),
    _item(
        "inspecao_isolamento_classe_ii", "inspecao", "inspecao", "5.2.2, alinea c",
        "Protecao por isolamento classe II ou equivalente deve ser adotada no lado c.c.",
    ),
    _item(
        "inspecao_cabos_curto_falta", "inspecao", "inspecao", "5.2.2, alinea d",
        "Cabos c.c. devem ser selecionados e montados para minimizar faltas a terra e curto-circuitos.",
    ),
    _item(
        "inspecao_cabos_influencias", "inspecao", "inspecao", "5.2.2, alinea e",
        "Cabos devem resistir as influencias externas esperadas, incluindo vento, gelo, temperatura e radiacao solar.",
    ),
    _item(
        "inspecao_ir_corrente_reversa", "inspecao", "inspecao", "5.2.2, alinea f",
        "Sem protecao de sobrecorrente, Ir do modulo deve superar a corrente reversa e cabos devem suportar falta combinada.",
    ),
    _item(
        "inspecao_protecao_sobrecorrente", "inspecao", "inspecao", "5.2.2, alinea g",
        "Com protecao de sobrecorrente, o dispositivo deve estar corretamente posicionado e especificado.",
    ),
    _item(
        "inspecao_desconexao_series", "inspecao", "inspecao", "5.2.2, alinea h",
        "Meios de desconexao devem existir nas series e subarranjos conforme IEC 60364-7-712.",
    ),
    _item(
        "inspecao_chave_cc_inversor", "inspecao", "inspecao", "5.2.2, alinea i",
        "Uma chave c.c. deve estar instalada no lado c.c. do inversor.",
    ),
    _item(
        "inspecao_diodos_bloqueio", "inspecao", "inspecao", "5.2.2, alinea j",
        "Quando houver diodos de bloqueio, sua tensao reversa deve atender a IEC 60364-7-712.",
    ),
    _item(
        "inspecao_condutor_terra_cc", "inspecao", "inspecao", "5.2.2, alinea k",
        "Condutor c.c. aterrado, separacao entre c.a./c.c. e conexoes de terra devem evitar corrosao.",
    ),
    _item(
        "inspecao_conectores_cc", "inspecao", "inspecao", "5.2.2, alinea l",
        "Plugues e soquetes conectados entre si devem ser do mesmo tipo e fabricante.",
    ),
    _item(
        "inspecao_sinalizacao_circuitos", "inspecao", "inspecao", "5.2.5, alinea a",
        "Circuitos, protecoes, chaves e terminais devem estar identificados e etiquetados.",
    ),
    _item(
        "inspecao_sinalizacao_caixas", "inspecao", "inspecao", "5.2.5, alinea b",
        "Caixas c.c. devem alertar que partes vivas continuam energizadas apos o seccionamento.",
    ),
    _item(
        "inspecao_sinalizacao_interconexao", "inspecao", "inspecao", "5.2.5, alinea c",
        "Etiquetas de advertencia devem estar fixadas no ponto de interconexao com a rede.",
    ),
    _item(
        "inspecao_diagrama_local", "inspecao", "inspecao", "5.2.5, alinea d",
        "O diagrama unifilar deve estar exibido no local.",
    ),
    _item(
        "inspecao_configuracoes_inversor", "inspecao", "inspecao", "5.2.5, alinea e",
        "Configuracoes de protecao do inversor e informacoes do instalador devem estar no local.",
    ),
    _item(
        "inspecao_desligamento_emergencia", "inspecao", "inspecao", "5.2.5, alinea f",
        "Procedimentos de desligamento de emergencia devem estar exibidos no local.",
    ),
    _item(
        "inspecao_durabilidade_sinais", "inspecao", "inspecao", "5.2.5, alinea g",
        "Sinais e etiquetas devem estar fixados e ser duraveis.",
    ),
    _item(
        "inspecao_ventilacao", "inspecao", "inspecao", "5.2.6, alinea a",
        "Deve haver ventilacao possivel por tras do arranjo.",
    ),
    _item(
        "inspecao_corrosao", "inspecao", "inspecao", "5.2.6, alinea b",
        "A armacao e os materiais do arranjo devem ser a prova de corrosao.",
    ),
    _item(
        "inspecao_fixacao_intemperies", "inspecao", "inspecao", "5.2.6, alinea c",
        "A armacao deve estar fixa e estavel e as fixacoes no telhado a prova de intempéries.",
    ),
    _item(
        "inspecao_entradas_cabos", "inspecao", "inspecao", "5.2.6, alinea d",
        "As entradas de cabos devem ser a prova de intempéries.",
    ),
    _item(
        "continuidade_terra", "ensaio", "ensaio", "6.1",
        "A continuidade dos condutores de aterramento e equipotencializacao deve ser verificada.",
    ),
    _item(
        "polaridade_cc", "ensaio", "ensaio", "6.2",
        "A polaridade de todos os cabos c.c. deve ser verificada antes dos demais ensaios.",
    ),
    _item(
        "corrente_isc", "ensaio", "ensaio", "6.4.2",
        "A corrente de curto-circuito de cada serie fotovoltaica deve ser medida.",
    ),
    _item(
        "tensao_voc", "ensaio", "ensaio", "6.5",
        "A tensao de circuito aberto de cada serie deve ser medida e comparada ao esperado.",
    ),
    _item(
        "ensaios_funcionais", "ensaio", "ensaio", "6.6",
        "Dispositivos de seccionamento e inversores devem ter funcionamento verificado.",
    ),
    _item(
        "isolamento_cc", "ensaio", "ensaio", "6.7.3, Tabela 1",
        "A resistencia de isolamento deve atender a tensao de ensaio e ao minimo da Tabela 1.",
    ),
    _item(
        "relatorio_sistema", "relatorio", "registro", "9.1, alinea a",
        "O relatorio deve descrever resumidamente o sistema.",
    ),
    _item(
        "relatorio_circuitos", "relatorio", "registro", "9.1, alinea b",
        "O relatorio deve listar os circuitos inspecionados e ensaiados.",
    ),
    _item(
        "relatorio_fotografico", "relatorio", "registro", "9.1, alinea c",
        "O relatorio deve incluir registro da inspecao, inclusive fotografico.",
    ),
    _item(
        "relatorio_resultados_ensaios", "relatorio", "registro", "9.1, alinea d",
        "O relatorio deve registrar os resultados dos ensaios para cada circuito.",
    ),
    _item(
        "relatorio_proxima_verificacao", "relatorio", "registro", "9.1, alinea e",
        "O relatorio deve registrar o intervalo recomendado ate a proxima verificacao.",
    ),
    _item(
        "relatorio_assinatura", "relatorio", "registro", "9.1, alinea f",
        "O relatorio deve conter a assinatura de quem realizou a verificacao.",
    ),
)


def montar_checklist_comissionamento_fv():
    """Return an independent, ordered copy of the normative checklist."""
    return deepcopy(_CHECKLIST)


def _resultado(item_id, status, observacao="", valores=None):
    resultado = {"id": item_id, "status": status, "observacao": observacao}
    if valores is not None:
        resultado["valores"] = valores
    return resultado


def _falha(codigo, mensagem, item):
    return {
        "codigo": codigo,
        "mensagem": mensagem,
        "item_id": item["id"],
        "referencia": deepcopy(item["referencia"]),
    }


def _estado_qualitativo(valor):
    if isinstance(valor, bool):
        return "APROVADO" if valor else "REPROVADO", ""
    if isinstance(valor, dict):
        if set(valor) - {"status", "observacao"}:
            return "NAO_AVALIADO", "registro qualitativo contem campos desconhecidos"
        status = valor.get("status")
        if status in _STATUS:
            return status, str(valor.get("observacao", ""))
    return "NAO_AVALIADO", "valor de verificacao nao reconhecido"


def _agregar_status(statuses):
    statuses = set(statuses)
    for status in ("REPROVADO", "REVISAO_MANUAL", "NAO_AVALIADO", "APROVADO"):
        if status in statuses:
            return status
    return "NAO_AVALIADO"


def _numero_positivo(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return False
    try:
        return math.isfinite(valor) and valor > 0
    except (OverflowError, TypeError):
        return False


def _validar_voc_ou_isc(item, registro, *, medido, referencia, unidade, falhas, avisos):
    if not isinstance(registro, dict):
        mensagem = "registro quantitativo deve ser um dicionario"
        falhas.append(_falha("ENTRADA_INVALIDA", mensagem, item))
        return _resultado(item["id"], "NAO_AVALIADO", mensagem)
    campos_permitidos = {medido, referencia, "confirmado"}
    if set(registro) - campos_permitidos:
        mensagem = "registro quantitativo contem campos desconhecidos"
        falhas.append(_falha("CAMPO_DESCONHECIDO", mensagem, item))
        return _resultado(item["id"], "NAO_AVALIADO", mensagem)
    medicao = registro.get(medido)
    esperado = registro.get(referencia)
    if not _numero_positivo(medicao) or not _numero_positivo(esperado):
        mensagem = "medicao e referencia devem ser numeros positivos e finitos"
        falhas.append(_falha("ENTRADA_INVALIDA", mensagem, item))
        return _resultado(item["id"], "NAO_AVALIADO", mensagem)
    try:
        desvio = abs(medicao - esperado) / esperado * 100.0
    except (OverflowError, TypeError, ZeroDivisionError):
        desvio = None
    if desvio is None or not math.isfinite(desvio):
        mensagem = "desvio percentual nao pode ser representado como numero finito"
        falhas.append(_falha("CALCULO_NAO_FINITO", mensagem, item))
        return _resultado(item["id"], "NAO_AVALIADO", mensagem)
    valores = {
        "medido": medicao,
        "referencia": esperado,
        "unidade": unidade,
        "desvio_percentual": desvio,
        "limite_tipico_percentual": 5.0,
    }
    if desvio > 5.0:
        avisos.append({
            "codigo": "AVALIACAO_TIPICA_5_PORCENTO",
            "mensagem": f"desvio de {item['id']} excede o valor tipico de 5% e requer avaliacao",
            "item_id": item["id"],
            "referencia": deepcopy(item["referencia"]),
        })
    confirmado = registro.get("confirmado")
    if confirmado is True:
        return _resultado(item["id"], "APROVADO", "resultado confirmado pelo responsavel", valores)
    if confirmado is False or confirmado is None:
        return _resultado(item["id"], "REVISAO_MANUAL", "confirmacao do responsavel ausente", valores)
    mensagem = "confirmado deve ser booleano"
    falhas.append(_falha("ENTRADA_INVALIDA", mensagem, item))
    return _resultado(item["id"], "NAO_AVALIADO", mensagem, valores)


def _validar_isolamento(item, registro, falhas):
    if not isinstance(registro, dict):
        mensagem = "registro de isolamento deve ser um dicionario"
        falhas.append(_falha("ENTRADA_INVALIDA", mensagem, item))
        return _resultado(item["id"], "NAO_AVALIADO", mensagem)
    campos_permitidos = {"metodo", "voc_stc_v", "tensao_ensaio_v", "resistencia_mohm"}
    if set(registro) - campos_permitidos:
        mensagem = "registro de isolamento contem campos desconhecidos"
        falhas.append(_falha("CAMPO_DESCONHECIDO", mensagem, item))
        return _resultado(item["id"], "NAO_AVALIADO", mensagem)
    metodo = registro.get("metodo")
    voc_stc = registro.get("voc_stc_v")
    tensao_ensaio = registro.get("tensao_ensaio_v")
    resistencia = registro.get("resistencia_mohm")
    if (
        metodo not in {"metodo_1", "metodo_2"}
        or not _numero_positivo(voc_stc)
        or not _numero_positivo(tensao_ensaio)
        or not _numero_positivo(resistencia)
    ):
        mensagem = "metodo, Voc STC e valores de isolamento devem ser validos e positivos"
        falhas.append(_falha("ENTRADA_INVALIDA", mensagem, item))
        return _resultado(item["id"], "NAO_AVALIADO", mensagem)
    try:
        tensao_sistema = voc_stc * 1.25
    except (OverflowError, TypeError):
        tensao_sistema = None
    if tensao_sistema is None or not math.isfinite(tensao_sistema):
        mensagem = "Voc STC x 1,25 nao pode ser representado como numero finito"
        falhas.append(_falha("CALCULO_NAO_FINITO", mensagem, item))
        return _resultado(item["id"], "NAO_AVALIADO", mensagem)
    if tensao_sistema < 120.0:
        tensao_requerida, resistencia_minima = 250.0, 0.5
    elif tensao_sistema <= 500.0:
        tensao_requerida, resistencia_minima = 500.0, 1.0
    else:
        tensao_requerida, resistencia_minima = 1000.0, 1.0
    valores = {
        "metodo": metodo,
        "voc_stc_v": voc_stc,
        "fator_tensao_sistema": 1.25,
        "tensao_sistema_v": tensao_sistema,
        "tensao_ensaio_v": tensao_ensaio,
        "tensao_ensaio_requerida_v": tensao_requerida,
        "resistencia_mohm": resistencia,
        "resistencia_minima_mohm": resistencia_minima,
    }
    if tensao_ensaio != tensao_requerida:
        mensagem = "tensao de ensaio diferente da Tabela 1"
        falhas.append(_falha("TENSAO_ENSAIO_INCORRETA", mensagem, item))
        return _resultado(item["id"], "REPROVADO", mensagem, valores)
    if resistencia < resistencia_minima:
        mensagem = "resistencia de isolamento abaixo da Tabela 1"
        falhas.append(_falha("RESISTENCIA_ISOLAMENTO_INSUFICIENTE", mensagem, item))
        return _resultado(item["id"], "REPROVADO", mensagem, valores)
    return _resultado(item["id"], "APROVADO", "Tabela 1 atendida", valores)


def validar_comissionamento_fv(caso):
    """Validate commissioning evidence without inventing measurements."""
    checklist = montar_checklist_comissionamento_fv()
    falhas = []
    avisos = []
    verificacoes = caso.get("verificacoes") if isinstance(caso, dict) else None
    if not isinstance(verificacoes, dict):
        falhas.append({
            "codigo": "ENTRADA_AUSENTE" if isinstance(caso, dict) else "ENTRADA_INVALIDA",
            "mensagem": "verificacoes deve ser um dicionario",
        })
        verificacoes = {}

    itens = []
    ids_checklist = {item["id"] for item in checklist}
    for chave in sorted(set(verificacoes) - ids_checklist, key=repr):
        falhas.append({
            "codigo": "CHAVE_DESCONHECIDA",
            "mensagem": f"chave de verificacao desconhecida: {chave}",
        })
    for item in checklist:
        item_id = item["id"]
        if item_id not in verificacoes:
            itens.append(_resultado(item_id, "NAO_AVALIADO", "verificacao ausente"))
            continue
        valor = verificacoes[item_id]
        if item_id == "tensao_voc":
            itens.append(_validar_voc_ou_isc(
                item, valor, medido="medido_v", referencia="referencia_v",
                unidade="V", falhas=falhas, avisos=avisos,
            ))
            continue
        if item_id == "corrente_isc":
            itens.append(_validar_voc_ou_isc(
                item, valor, medido="medido_a", referencia="referencia_a",
                unidade="A", falhas=falhas, avisos=avisos,
            ))
            continue
        if item_id == "isolamento_cc":
            itens.append(_validar_isolamento(item, valor, falhas))
            continue
        status, observacao = _estado_qualitativo(valor)
        itens.append(_resultado(item_id, status, observacao))
        if status == "NAO_AVALIADO":
            codigo = (
                "CAMPO_DESCONHECIDO"
                if isinstance(valor, dict) and set(valor) - {"status", "observacao"}
                else "VALOR_NAO_RECONHECIDO"
            )
            falhas.append(_falha(codigo, observacao, item))

    status = _agregar_status(item["status"] for item in itens)
    if any(falha["codigo"] in {"CHAVE_DESCONHECIDA"} for falha in falhas):
        status = _agregar_status((status, "NAO_AVALIADO"))
    return {
        "ok": status == "APROVADO",
        "status": status,
        "itens": itens,
        "falhas": falhas,
        "avisos": avisos,
        "referencias": [deepcopy(item["referencia"]) for item in checklist],
    }
