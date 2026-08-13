# ============================================================================
# fotovoltaico.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Dimensiona o SISTEMA FOTOVOLTAICO na cobertura do galpao (geracao distribuida,
# on-grid): a cobertura e' a usina natural. Da AREA de telhado disponivel deriva a
# POTENCIA instalavel, a GERACAO de energia e o quanto do CONSUMO ela compensa, com
# o numero de modulos e inversores.
#   - potencia_instalavel: P_kWp = area_util . densidade_kWp_m2 (modulos modernos
#     ~0,18 kWp/m2 de area de modulo; aproveitamento do telhado desconta sombras/
#     caminhos/orientacao).
#   - geracao: E = P_kWp . HSP . PR . dias  (metodo consagrado, CRESESB). HSP =
#     horas de sol pico do SITIO (irradiacao diaria media, kWh/m2/dia) - DADO DE
#     SITIO (A CONFIRMAR: CRESESB/INPE p/ a cidade). PR = performance ratio (~0,78,
#     perdas de temperatura/cabeamento/inversor).
#   - n_modulos / n_inversores: por potencia de modulo (Wp) e do inversor (kW), com
#     FDI (fator de dimensionamento do inversor) tipico 0,75-1,0.
#   - dimensiona_fv: limita a potencia pelo MENOR entre o alvo (compensar o consumo)
#     e o teto de area; devolve geracao, cobertura do consumo (%), area usada.
# Refs: NBR 16690 (instalacoes eletricas de arranjos FV) e ANEEL REN 1000/2023
# (geracao distribuida / compensacao). Specs de modulo/inversor = CATALOGO
# (A CONFIRMAR). STATELESS. Unidades: m2, kWp, kWh, V.
# ============================================================================
"""Sistema fotovoltaico na cobertura (on-grid): area -> potencia -> geracao ->
compensacao do consumo. HSP e catalogo A CONFIRMAR. STATELESS."""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation

DENS_KWP_M2 = 0.18              # densidade de potencia (kWp por m2 de modulo, ~550 Wp)
APROVEITAMENTO = 0.70          # fracao util do telhado (sombra/caminhos/orientacao)
PR_PADRAO = 0.78               # performance ratio tipico (perdas do sistema)
P_MODULO_WP = 550.0            # potencia do modulo (Wp) - CATALOGO (A CONFIRMAR)
AREA_MODULO_M2 = 2.6           # area de um modulo de ~550 Wp (~2,3 x 1,13 m)
FDI = 0.85                     # fator de dimensionamento do inversor (Pinv/Pfv)
DIAS_MES = 30.4                # dias medios por mes

_NBR16690_SOURCE_ID = "1d06923f-04d7-4b39-afbd-da6ab91567a9"
_NBR16149_SOURCE_ID = "7f85f8f0-9ff2-492a-9188-bf345529f2b6"
_TIPOS_PROTECAO_CC = frozenset({
    "gPV",
    "disjuntor_cc_60947-2",
    "disjuntor_cc_60898-2",
})


def _tipo_protecao_cc_valido(value):
    return isinstance(value, str) and value in _TIPOS_PROTECAO_CC


def _referencia_fv(secao, source_id=_NBR16690_SOURCE_ID):
    norma = "ABNT NBR 16149:2013" if source_id == _NBR16149_SOURCE_ID else "ABNT NBR 16690:2019"
    return {"norma": norma, "secao": secao, "source_id": source_id}


def _falha_fv(codigo, mensagem, secao="6.1.1", source_id=_NBR16690_SOURCE_ID):
    return {
        "codigo": codigo,
        "mensagem": mensagem,
        "referencia": _referencia_fv(secao, source_id),
    }


def _numero_fv(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError):
        return False


def _produto_fv(*values):
    if not values:
        return None
    try:
        resultado = values[0]
        for value in values[1:]:
            resultado *= value
    except (OverflowError, TypeError):
        return None
    return resultado if _numero_fv(resultado) else None


def _subtracao_fv(left, right):
    try:
        resultado = left - right
    except (OverflowError, TypeError):
        return None
    return resultado if _numero_fv(resultado) else None


def _decimal_fv(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _comparar_limite_individual_fv(corrente, isc_modulo, imod_max_ocpr):
    corrente_decimal = _decimal_fv(corrente)
    isc_decimal = _decimal_fv(isc_modulo)
    imod_decimal = _decimal_fv(imod_max_ocpr)
    if corrente_decimal is None or isc_decimal is None or imod_decimal is None:
        return None
    return (
        corrente_decimal > Decimal("1.5") * isc_decimal
        and corrente_decimal < Decimal("2.4") * isc_decimal
        and corrente_decimal <= imod_decimal
    )


def _comparar_limite_grupo_fv(corrente, series_grupo, isc_modulo, imod_max_ocpr):
    corrente_decimal = _decimal_fv(corrente)
    grupo_decimal = _decimal_fv(series_grupo)
    isc_decimal = _decimal_fv(isc_modulo)
    imod_decimal = _decimal_fv(imod_max_ocpr)
    if (
        corrente_decimal is None
        or grupo_decimal is None
        or isc_decimal is None
        or imod_decimal is None
    ):
        return None
    return (
        corrente_decimal > Decimal("1.5") * grupo_decimal * isc_decimal
        and corrente_decimal < imod_decimal - ((grupo_decimal - 1) * isc_decimal)
    )


def _registrar_calculo_invalido(falhas, mensagem, secao="6.1.1"):
    falhas.append(_falha_fv("NUMERO_INVALIDO", mensagem, secao))


def _validar_numero_fv(caso, nome, falhas, *, inteiro=False):
    if nome not in caso:
        falhas.append(_falha_fv("ENTRADA_AUSENTE", "campo obrigatório ausente: %s" % nome))
        return None
    value = caso[nome]
    valido = _numero_fv(value) and value > 0
    if inteiro:
        valido = valido and isinstance(value, int)
    if not valido:
        falhas.append(_falha_fv("NUMERO_INVALIDO", "campo numérico inválido: %s" % nome))
        return None
    return value


def validar_compatibilidade_arranjo_fv(caso):
    """Valida limites elétricos básicos de um arranjo FV em corrente contínua.

    As regras implementadas são as citadas na ABNT NBR 16690:2019. A função é
    deliberadamente pura: não escolhe dados de catálogo, fatores térmicos ou
    parâmetros da distribuidora.
    """
    if not isinstance(caso, dict):
        return {
            "ok": False,
            "falhas": [_falha_fv("ENTRADA_AUSENTE", "caso deve ser um dicionário")],
            "avisos": [],
            "valores_calculados": {},
            "referencias": [_referencia_fv("6.1.1")],
        }

    falhas = []
    avisos = []
    voc_modulo = _validar_numero_fv(caso, "voc_modulo_v", falhas)
    modulos_serie = _validar_numero_fv(caso, "modulos_serie", falhas, inteiro=True)
    isc_modulo = _validar_numero_fv(caso, "isc_modulo_a", falhas)
    series_paralelo = _validar_numero_fv(caso, "series_paralelo", falhas, inteiro=True)

    tem_fator = caso.get("fator_correcao_tensao") is not None
    tem_vmax = caso.get("v_max_arranjo_v") is not None
    if tem_fator == tem_vmax:
        falhas.append(_falha_fv(
            "TENSAO_MAXIMA_AMBIGUA",
            "forneça exatamente fator_correcao_tensao ou v_max_arranjo_v",
            "6.1.3",
        ))

    fator = None
    v_max_fornecida = None
    if tem_fator:
        fator = _validar_numero_fv(caso, "fator_correcao_tensao", falhas)
    elif tem_vmax:
        v_max_fornecida = _validar_numero_fv(caso, "v_max_arranjo_v", falhas)

    componentes = caso.get("componentes_cc")
    if not isinstance(componentes, list) or not componentes:
        falhas.append(_falha_fv("ENTRADA_AUSENTE", "componentes_cc deve ser lista não vazia"))
        componentes = []

    valores = {
        "voc_arranjo_v": None,
        "v_max_arranjo_v": None,
        "isc_arranjo_a": None,
        "corrente_minima_arranjo_a": None,
        "corrente_referencia_componentes_a": None,
        "protecao_series_requerida": False,
    }
    if voc_modulo is not None and modulos_serie is not None:
        voc_arranjo = _produto_fv(voc_modulo, modulos_serie)
        if voc_arranjo is None:
            _registrar_calculo_invalido(falhas, "VOC_ARRANJO excede o limite numérico", "3.1.42")
        else:
            valores["voc_arranjo_v"] = voc_arranjo
            if fator is not None:
                v_max_arranjo = _produto_fv(voc_arranjo, fator)
                if v_max_arranjo is None:
                    _registrar_calculo_invalido(falhas, "V_MAX_ARRANJO excede o limite numérico", "6.1.3")
                else:
                    valores["v_max_arranjo_v"] = v_max_arranjo
            elif v_max_fornecida is not None:
                valores["v_max_arranjo_v"] = v_max_fornecida
    if isc_modulo is not None and series_paralelo is not None:
        isc_arranjo = _produto_fv(isc_modulo, series_paralelo)
        if isc_arranjo is None:
            _registrar_calculo_invalido(falhas, "ISC_ARRANJO excede o limite numérico", "3.1.42")
        else:
            corrente_minima = _produto_fv(1.25, isc_arranjo)
            if corrente_minima is None:
                _registrar_calculo_invalido(falhas, "corrente mínima do arranjo excede o limite numérico", "6.1.1")
            else:
                valores["isc_arranjo_a"] = isc_arranjo
                valores["corrente_minima_arranjo_a"] = corrente_minima
                valores["corrente_referencia_componentes_a"] = corrente_minima

    if isinstance(caso.get("usa_conectores"), bool) is False:
        falhas.append(_falha_fv("ENTRADA_AUSENTE", "usa_conectores deve ser booleano"))

    imod_max_ocpr = None
    if "imod_max_ocpr_a" in caso:
        imod_max_ocpr = _validar_numero_fv(caso, "imod_max_ocpr_a", falhas)

    if (
        series_paralelo is not None
        and series_paralelo > 1
        and "imod_max_ocpr_a" not in caso
    ):
        falhas.append(_falha_fv(
            "ENTRADA_AUSENTE",
            "imod_max_ocpr_a é obrigatório para séries em paralelo",
            "5.3.9",
        ))
    elif "protecao_series" in caso and caso.get("protecao_series") is not None:
        if "imod_max_ocpr_a" not in caso:
            falhas.append(_falha_fv(
                "ENTRADA_AUSENTE",
                "imod_max_ocpr_a é obrigatório quando protecao_series é declarada",
                "5.3.11.1",
            ))

    protecao_arranjo = caso.get("protecao_arranjo")
    if protecao_arranjo is not None:
        if not isinstance(protecao_arranjo, dict):
            falhas.append(_falha_fv("TIPO_PROTECAO_CC_INVALIDO", "protecao_arranjo deve ser um dicionário", "5.3.9"))
        else:
            tipo_arranjo = protecao_arranjo.get("tipo")
            corrente_arranjo = protecao_arranjo.get("corrente_nominal_a")
            if not _tipo_protecao_cc_valido(tipo_arranjo):
                falhas.append(_falha_fv(
                    "TIPO_PROTECAO_CC_INVALIDO",
                    f"tipo de proteção do arranjo não é autorizado: {tipo_arranjo!r}",
                    "5.3.9",
                ))
            if not _numero_fv(corrente_arranjo) or corrente_arranjo <= 0:
                falhas.append(_falha_fv(
                    "NUMERO_INVALIDO",
                    "corrente nominal da proteção do arranjo inválida",
                    "5.3.9",
                ))
            else:
                valores["corrente_referencia_componentes_a"] = corrente_arranjo

    protecao_series = caso.get("protecao_series")
    protecao_requerida = False
    if (
        isc_modulo is not None
        and series_paralelo is not None
        and series_paralelo > 1
        and imod_max_ocpr is not None
    ):
        corrente_reversa = _produto_fv(series_paralelo - 1, isc_modulo)
        if corrente_reversa is None:
            _registrar_calculo_invalido(
                falhas,
                "corrente reversa das séries excede o limite numérico",
                "5.3.9",
            )
        else:
            protecao_requerida = corrente_reversa > imod_max_ocpr
            valores["protecao_series_requerida"] = protecao_requerida
            if protecao_requerida and protecao_series is None:
                falhas.append(_falha_fv(
                    "PROTECAO_SERIE_AUSENTE",
                    "proteção contra sobrecorrente da série é obrigatória",
                    "5.3.9",
                ))
    if protecao_series is not None:
        if not isinstance(protecao_series, dict):
            falhas.append(_falha_fv("TIPO_PROTECAO_CC_INVALIDO", "protecao_series deve ser um dicionário", "5.3.11.1"))
        else:
            modo = protecao_series.get("modo")
            tipo = protecao_series.get("tipo")
            corrente = protecao_series.get("corrente_nominal_a")
            if not _tipo_protecao_cc_valido(tipo):
                falhas.append(_falha_fv(
                    "TIPO_PROTECAO_CC_INVALIDO",
                    f"tipo de proteção da série não é autorizado: {tipo!r}",
                    "5.3.9",
                ))
            if not _numero_fv(corrente) or corrente <= 0:
                falhas.append(_falha_fv(
                    "NUMERO_INVALIDO",
                    "corrente nominal da proteção da série inválida",
                    "5.3.11.1",
                ))
            elif modo == "individual" and _numero_fv(isc_modulo) and imod_max_ocpr is not None:
                limite_inferior = _produto_fv(1.5, isc_modulo)
                limite_superior = _produto_fv(2.4, isc_modulo)
                faixa_individual_valida = _comparar_limite_individual_fv(
                    corrente,
                    isc_modulo,
                    imod_max_ocpr,
                )
                if limite_inferior is None or limite_superior is None or faixa_individual_valida is None:
                    _registrar_calculo_invalido(
                        falhas,
                        "limites da proteção individual excedem o limite numérico",
                        "5.3.11.1",
                    )
                elif not faixa_individual_valida:
                    falhas.append(_falha_fv(
                        "PROTECAO_INDIVIDUAL_FORA_DA_FAIXA",
                        "corrente individual fora das desigualdades de 5.3.11.1",
                        "5.3.11.1",
                    ))
            elif modo == "grupo" and _numero_fv(isc_modulo) and imod_max_ocpr is not None:
                series_grupo = protecao_series.get("series_grupo")
                faixa_grupo_valida = False
                calculo_grupo_invalido = False
                if (
                    isinstance(series_grupo, int)
                    and not isinstance(series_grupo, bool)
                    and series_grupo >= 1
                    and series_paralelo is not None
                    and series_grupo <= series_paralelo
                ):
                    limite_inferior = _produto_fv(1.5, series_grupo, isc_modulo)
                    offset_superior = _produto_fv(series_grupo - 1, isc_modulo)
                    limite_superior = (
                        _subtracao_fv(imod_max_ocpr, offset_superior)
                        if offset_superior is not None
                        else None
                    )
                    if limite_inferior is None or limite_superior is None:
                        calculo_grupo_invalido = True
                        _registrar_calculo_invalido(
                            falhas,
                            "limites da proteção agrupada excedem o limite numérico",
                            "5.3.11.1",
                        )
                    else:
                        faixa_grupo_valida = _comparar_limite_grupo_fv(
                            corrente,
                            series_grupo,
                            isc_modulo,
                            imod_max_ocpr,
                        ) is True
                if not faixa_grupo_valida and not calculo_grupo_invalido:
                    falhas.append(_falha_fv(
                        "PROTECAO_GRUPO_FORA_DA_FAIXA",
                        "proteção agrupada fora das desigualdades de 5.3.11.1",
                        "5.3.11.1",
                    ))
            elif modo not in ("individual", "grupo"):
                falhas.append(_falha_fv(
                    "TIPO_PROTECAO_CC_INVALIDO",
                    f"modo de proteção de série inválido: {modo!r}",
                    "5.3.11.1",
                ))

    if caso.get("usa_conectores") is True:
        conectores = caso.get("conectores")
        if not isinstance(conectores, dict):
            falhas.append(_falha_fv(
                "ENTRADA_AUSENTE",
                "conectores deve conter macho e femea",
                "6.2.8.1",
            ))
        else:
            macho = conectores.get("macho")
            femea = conectores.get("femea")
            if not isinstance(macho, dict) or not isinstance(femea, dict):
                falhas.append(_falha_fv(
                    "ENTRADA_AUSENTE",
                    "conectores deve conter macho e femea",
                    "6.2.8.1",
                ))
            else:
                campos_conectores_validos = True
                for conector_nome, conector in (("macho", macho), ("femea", femea)):
                    for campo in ("fabricante", "tipo"):
                        valor = conector.get(campo)
                        if not isinstance(valor, str) or not valor.strip():
                            campos_conectores_validos = False
                            falhas.append(_falha_fv(
                                "ENTRADA_AUSENTE",
                                "conector %s deve ter %s não vazio" % (conector_nome, campo),
                                "6.2.8.1",
                            ))
                if campos_conectores_validos and macho.get("fabricante") != femea.get("fabricante"):
                    falhas.append(_falha_fv(
                        "CONECTOR_FABRICANTE_INCOMPATIVEL",
                        "conectores da mesma conexão devem ter o mesmo fabricante",
                        "6.2.8.1",
                    ))
                if campos_conectores_validos and macho.get("tipo") != femea.get("tipo"):
                    falhas.append(_falha_fv(
                        "CONECTOR_TIPO_INCOMPATIVEL",
                        "conectores da mesma conexão devem ter o mesmo tipo",
                        "6.2.8.1",
                    ))

    corrente_referencia = valores["corrente_referencia_componentes_a"]
    v_max = valores["v_max_arranjo_v"]
    for componente in componentes:
        if not isinstance(componente, dict):
            falhas.append(_falha_fv("NUMERO_INVALIDO", "componente CC deve ser um dicionário"))
            continue
        nome = componente.get("nome")
        if not isinstance(nome, str) or not nome.strip():
            falhas.append(_falha_fv(
                "ENTRADA_AUSENTE",
                "componente CC deve ter nome não vazio",
            ))
            nome = "componente"
        if componente.get("adequado_cc") is not True:
            falhas.append(_falha_fv(
                "COMPONENTE_NAO_CC",
                "%s não foi declarado apropriado para corrente contínua" % nome,
            ))
        tensao = componente.get("tensao_nominal_v")
        if not _numero_fv(tensao) or tensao <= 0:
            falhas.append(_falha_fv("NUMERO_INVALIDO", "tensão nominal inválida: %s" % nome))
        elif v_max is not None and tensao < v_max:
            falhas.append(_falha_fv(
                "TENSAO_COMPONENTE_INSUFICIENTE",
                "%s: %.3f V < Vmax %.3f V" % (nome, tensao, v_max),
            ))
        corrente = componente.get("corrente_nominal_a")
        if not _numero_fv(corrente) or corrente <= 0:
            falhas.append(_falha_fv("NUMERO_INVALIDO", "corrente nominal inválida: %s" % nome))
        elif corrente_referencia is not None and corrente < corrente_referencia:
            falhas.append(_falha_fv(
                "CORRENTE_COMPONENTE_INSUFICIENTE",
                "%s: %.3f A < referência %.3f A"
                % (nome, corrente, corrente_referencia),
            ))

    referencias = [
        _referencia_fv("3.1.42"),
        _referencia_fv("5.3.9"),
        _referencia_fv("5.3.11.1"),
        _referencia_fv("6.1.1"),
        _referencia_fv("6.1.3"),
        _referencia_fv("6.2.5"),
        _referencia_fv("6.2.8.1"),
        _referencia_fv("6.2.8.2"),
        _referencia_fv("5.5-5.7", _NBR16149_SOURCE_ID),
    ]
    return {
        "ok": not falhas,
        "falhas": falhas,
        "avisos": avisos,
        "valores_calculados": valores,
        "referencias": referencias,
    }


def potencia_instalavel(area_m2, aproveitamento=APROVEITAMENTO, densidade=DENS_KWP_M2):
    """Potencia FV instalavel (kWp) numa area de telhado. area_util = area x
    aproveitamento; P = area_util x densidade."""
    if area_m2 <= 0:
        raise ValueError("area de cobertura invalida: %r" % area_m2)
    area_util = area_m2 * aproveitamento
    return area_util * densidade


def geracao(P_kWp, HSP, PR=PR_PADRAO):
    """Energia gerada (metodo CRESESB): E = P.HSP.PR.dias. HSP = horas de sol pico
    (kWh/m2/dia) do sitio. Retorna dict com diaria/mensal/anual (kWh)."""
    if HSP <= 0:
        raise ValueError("[A CONFIRMAR] HSP (irradiacao) do sitio nao informado")
    e_dia = P_kWp * HSP * PR
    return {"kwh_dia": e_dia, "kwh_mes": e_dia * DIAS_MES, "kwh_ano": e_dia * 365.0,
            "HSP": HSP, "PR": PR}


def n_modulos(P_kWp, P_modulo_Wp=P_MODULO_WP):
    """Numero de modulos = teto(P_kWp*1000 / P_modulo_Wp)."""
    return int(math.ceil(P_kWp * 1000.0 / P_modulo_Wp))


def n_inversores(P_kWp, P_inversor_kW, fdi=FDI):
    """Numero de inversores: a potencia total dos inversores >= P_kWp*fdi
    (subdimensionamento controlado do inversor). teto(P_kWp*fdi / P_inv)."""
    if P_inversor_kW <= 0:
        raise ValueError("potencia do inversor invalida")
    return max(1, int(math.ceil(P_kWp * fdi / P_inversor_kW)))


def dimensiona_fv(caso):
    """Dimensiona o sistema FV. caso:
      'area_cobertura_m2' : area de telhado disponivel (m2). OBRIGATORIO.
      'HSP'               : horas de sol pico do sitio (kWh/m2/dia) [A CONFIRMAR].
      'consumo_kwh_mes'   : consumo a compensar (opc). Alternativa: 'demanda_kW' +
                            'horas_dia' -> consumo estimado.
      'aproveitamento','PR','P_modulo_Wp','P_inversor_kW','densidade' : opcionais.
    Limita a potencia pelo MENOR entre (alvo p/ compensar o consumo) e (teto de
    area). Retorna potencia, geracao, cobertura do consumo, modulos e inversores."""
    area = caso.get("area_cobertura_m2")
    if not area or area <= 0:
        raise ValueError("[A CONFIRMAR] area_cobertura_m2 nao informada")
    HSP = caso.get("HSP")
    apr = caso.get("aproveitamento", APROVEITAMENTO)
    PR = caso.get("PR", PR_PADRAO)
    dens = caso.get("densidade", DENS_KWP_M2)
    P_mod = caso.get("P_modulo_Wp", P_MODULO_WP)
    P_inv = caso.get("P_inversor_kW", 75.0)

    P_teto_area = potencia_instalavel(area, apr, dens)

    # consumo alvo (kWh/mes): direto ou por demanda x horas
    consumo = caso.get("consumo_kwh_mes")
    if consumo is None and caso.get("demanda_kW"):
        horas = caso.get("horas_dia", 8.0)
        consumo = caso["demanda_kW"] * horas * DIAS_MES

    if HSP is None:
        return {"OK": False, "motivo": "[A CONFIRMAR] HSP (irradiacao do sitio) - "
                "obter no CRESESB/INPE para a cidade.",
                "potencia_teto_area_kWp": round(P_teto_area, 1)}

    # potencia p/ compensar 100% do consumo (se dado): P = consumo_mes/(HSP.PR.dias)
    P_alvo = None
    if consumo:
        P_alvo = consumo / (HSP * PR * DIAS_MES)

    P_kWp = P_teto_area if P_alvo is None else min(P_teto_area, P_alvo)
    limitado_por = ("area (telhado nao comporta 100% do consumo)"
                    if (P_alvo is not None and P_teto_area < P_alvo) else
                    ("consumo (alvo)" if P_alvo is not None else "area (sem consumo alvo)"))

    ger = geracao(P_kWp, HSP, PR)
    nmod = n_modulos(P_kWp, P_mod)
    ninv = n_inversores(P_kWp, P_inv)
    area_usada = nmod * (caso.get("area_modulo_m2", AREA_MODULO_M2))
    cobertura = (100.0 * ger["kwh_mes"] / consumo) if consumo else None

    return {"OK": True, "potencia_kWp": round(P_kWp, 1),
            "potencia_teto_area_kWp": round(P_teto_area, 1),
            "limitado_por": limitado_por,
            "geracao": {"kwh_dia": round(ger["kwh_dia"], 1),
                        "kwh_mes": round(ger["kwh_mes"], 1),
                        "kwh_ano": round(ger["kwh_ano"], 1),
                        "HSP": HSP, "PR": PR},
            "consumo_kwh_mes": round(consumo, 1) if consumo else None,
            "cobertura_consumo_pct": round(cobertura, 1) if cobertura else None,
            "n_modulos": nmod, "P_modulo_Wp": P_mod,
            "n_inversores": ninv, "P_inversor_kW": P_inv,
            "area_modulos_m2": round(area_usada, 1),
            "area_cobertura_m2": area, "aproveitamento": apr,
            # fator de emissao medio do SIN ~0,0817 tCO2/MWh (A CONFIRMAR ano-base MCTI)
            "co2_evitado_ton_ano": round(ger["kwh_ano"] / 1000.0 * 0.0817, 2),
            "norma": "Geracao: E=P.HSP.PR (CRESESB); NBR 16690 (arranjo FV); ANEEL "
                     "REN 1000/2023 (GD/compensacao). HSP e catalogo A CONFIRMAR."}


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def grafico_svg(r):
    """Grafico do sistema FV: barras geracao x consumo (kWh/mes) + resumo. SVG puro,
    XML-valido (parse). r = saida de dimensiona_fv."""
    W, H = 900, 560

    def _t(x, y, s, size=13, anchor="middle", weight="normal", color="#111"):
        return (f'<text x="{x:.0f}" y="{y:.0f}" font-family="Arial" font-size="{size}"'
                f' text-anchor="{anchor}" font-weight="{weight}" fill="{color}">'
                f'{_esc(s)}</text>')

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Arial">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           _t(W / 2, 42, "SISTEMA FOTOVOLTAICO NA COBERTURA", 21, weight="bold")]
    if not r.get("OK"):
        out.append(_t(W / 2, H / 2, r.get("motivo", "FV nao dimensionado"), 14,
                      color="#b00"))
        out.append("</svg>"); return "\n".join(out)

    ger = r["geracao"]["kwh_mes"]; cons = r.get("consumo_kwh_mes") or ger
    base = max(ger, cons) or 1.0
    bx, by, bw, bh = 130, 120, 150, 300
    for i, (lbl, val, cor) in enumerate([("Geracao FV", ger, "#f39c12"),
                                         ("Consumo", cons, "#3498db")]):
        x = bx + i * 220
        hh = bh * val / base
        out.append(f'<rect x="{x}" y="{by + bh - hh:.0f}" width="{bw}" height="{hh:.0f}" '
                   f'fill="{cor}"/>')
        out.append(_t(x + bw / 2, by + bh - hh - 10, "%.0f kWh/mes" % val, 13, weight="bold"))
        out.append(_t(x + bw / 2, by + bh + 24, lbl, 14))
    out.append(f'<line x1="{bx-20}" y1="{by+bh}" x2="{bx+2*220}" y2="{by+bh}" '
               f'stroke="#111" stroke-width="1.5"/>')

    # resumo (direita)
    qx = 590
    linhas = [("Potencia instalada", "%.1f kWp" % r["potencia_kWp"]),
              ("Modulos", "%d x %.0f Wp" % (r["n_modulos"], r["P_modulo_Wp"])),
              ("Inversores", "%d x %.0f kW" % (r["n_inversores"], r["P_inversor_kW"])),
              ("Geracao anual", "%.0f kWh/ano" % r["geracao"]["kwh_ano"]),
              ("Cobertura do consumo", ("%.0f%%" % r["cobertura_consumo_pct"]
                                        if r.get("cobertura_consumo_pct") else "-")),
              ("Limitado por", r["limitado_por"][:22]),
              ("Area de modulos", "%.0f m2 / %.0f m2" % (r["area_modulos_m2"],
                                                         r["area_cobertura_m2"])),
              ("HSP (sitio)", "%.1f kWh/m2.dia" % r["geracao"]["HSP"]),
              ("CO2 evitado", "%.1f t/ano" % r["co2_evitado_ton_ano"])]
    out.append(f'<rect x="{qx}" y="110" width="270" height="{28*len(linhas)+40}" '
               f'fill="#fafafa" stroke="#111" stroke-width="1.2"/>')
    out.append(_t(qx + 135, 136, "RESUMO DO SISTEMA", 14, weight="bold"))
    for i, (k, v) in enumerate(linhas):
        yy = 162 + i * 28
        out.append(_t(qx + 12, yy, k, 12, anchor="start", color="#333"))
        out.append(_t(qx + 258, yy, v, 12, anchor="end", weight="bold"))
    out.append(_t(W / 2, H - 20, "E = P.HSP.PR (CRESESB) | NBR 16690 / ANEEL REN "
                  "1000 | HSP e catalogo A CONFIRMAR", 11, color="#666"))
    out.append("</svg>")
    return "\n".join(out)


# ----------------------------------- selftest --------------------------------
def _selftest():
    # potencia instalavel: 1000 m2 x 0,7 x 0,18 = 126 kWp
    assert abs(potencia_instalavel(1000.0) - 126.0) < 1e-9

    # geracao: 100 kWp x 5 HSP x 0,78 = 390 kWh/dia
    g = geracao(100.0, 5.0)
    assert abs(g["kwh_dia"] - 390.0) < 1e-9
    assert abs(g["kwh_ano"] - 390.0 * 365) < 1e-6

    # n modulos: 100 kWp / 550 Wp = 182 modulos (teto)
    assert n_modulos(100.0) == math.ceil(100000.0 / 550.0)
    # n inversores: 100 kWp x 0,85 / 75 kW = 2 (teto)
    assert n_inversores(100.0, 75.0) == 2

    # dimensiona limitado por AREA (telhado pequeno, consumo alto)
    r = dimensiona_fv({"area_cobertura_m2": 500.0, "HSP": 5.0,
                       "consumo_kwh_mes": 100000.0})
    assert r["OK"] and r["limitado_por"].startswith("area")
    assert r["potencia_kWp"] == r["potencia_teto_area_kWp"]
    assert r["cobertura_consumo_pct"] < 100.0        # nao compensa 100%

    # dimensiona limitado por CONSUMO (telhado grande, consumo modesto)
    r2 = dimensiona_fv({"area_cobertura_m2": 2000.0, "HSP": 5.5,
                        "consumo_kwh_mes": 20000.0})
    assert r2["limitado_por"].startswith("consumo")
    assert abs(r2["cobertura_consumo_pct"] - 100.0) < 2.0   # ~compensa 100%
    assert r2["potencia_kWp"] < r2["potencia_teto_area_kWp"]

    # sem HSP -> A CONFIRMAR (nao inventa)
    assert dimensiona_fv({"area_cobertura_m2": 800.0}).get("OK") is False

    # consumo por demanda x horas
    r3 = dimensiona_fv({"area_cobertura_m2": 2000.0, "HSP": 5.0,
                        "demanda_kW": 50.0, "horas_dia": 8.0})
    assert r3["consumo_kwh_mes"] == round(50.0 * 8.0 * DIAS_MES, 1)

    # area invalida levanta
    try:
        dimensiona_fv({"area_cobertura_m2": 0, "HSP": 5.0}); assert False
    except ValueError:
        pass

    # grafico SVG e' XML valido (parse)
    from xml.dom.minidom import parseString
    svg = grafico_svg(r2)
    assert svg.startswith("<svg") and "SISTEMA FOTOVOLTAICO" in svg
    parseString(svg.encode("utf-8"))
    parseString(grafico_svg({"OK": False, "motivo": "x"}).encode("utf-8"))
    return True


if __name__ == "__main__":
    _selftest()
    import json
    demo = dimensiona_fv({"area_cobertura_m2": 800.0, "HSP": 5.2,
                          "consumo_kwh_mes": 18000.0, "P_inversor_kW": 75.0})
    print(json.dumps(demo, indent=2, ensure_ascii=False))
    print("selftest OK")
