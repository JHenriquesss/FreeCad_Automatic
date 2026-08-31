# ============================================================================
# eletrica_edificio.py - CARGA, PRUMADA, QUADRO POR PAVIMENTO E ENTRADA
#
# O vertical eletrico do framework tinha os dois extremos: `residencial_eletrica`
# projeta os circuitos terminais de UMA casa e `galpao_eletrico` projeta uma
# instalacao industrial. Faltava o meio - o predio: n unidades por pavimento, um
# quadro por pavimento e UMA PRUMADA que sobe alimentando todos eles. Este modulo
# e' essa fronteira; nao reimplementa tabela nenhuma.
#
#     ambientes da unidade-tipo
#          -> carga por unidade      (NBR 5410 9.5.2, via arquitetura_residencial)
#          -> carga e quadro POR PAVIMENTO  (condutores + protecao 5410)
#          -> PRUMADA trecho a trecho: cada trecho conduz a carga dos pavimentos
#             ACIMA dele, e a queda de tensao ACUMULA ate o quadro mais alto
#          -> entrada: demanda total, tipo de fornecimento, protecao geral, DPS
#          -> gates
#
# O TRECHO E' O PONTO. Dimensionar a prumada por uma corrente so - a do pe da
# coluna - da a secao certa e a queda de tensao ERRADA: a corrente cai a cada
# pavimento que se atende, mas o comprimento cresce. Uma prumada verificada so no
# pe passa com folga e entrega 220 V curtos no ultimo andar. Aqui a queda e'
# SOMADA trecho a trecho ate o quadro mais desfavoravel, que e' o mais alto.
#
# DIVERSIDADE ENTRE UNIDADES - o piso conservador. O fator de demanda entre
# unidades consumidoras e' dado da CONCESSIONARIA (Enel CNC-NDBR-DBR-25-1580,
# fornecimento BT em conexao coletiva), nao da NBR 5410. Sem ele declarado, este
# modulo NAO inventa um: soma as unidades sem diversidade nenhuma, que e' o TETO
# da demanda, e publica `fator_de_demanda_entre_unidades: not_available` com
# aviso. Uma prumada assim sai cara, e cara e' o lado certo de errar - mas o
# projeto tem de saber que a reducao existe e nao foi aplicada.
#
# O QUE NAO ENTRA (publicado no escopo): os CIRCUITOS TERMINAIS dentro da unidade
# (divisao em circuitos, DR por circuito, leiaute de pontos - isso e'
# `residencial_eletrica`/`instalacao_eletrica` sobre a planta da unidade, que o
# framework nao tem para o edificio); o curto-circuito calculado (a Icc presumida
# e' DECLARADA, vinda da concessionaria); a subestacao/transformacao propria
# quando a carga passa dos 75 kW da conexao BT; o SPDA; e os servicos de uso
# comum alem da carga declarada (elevador, bomba de recalque, iluminacao de
# emergencia - suas cargas entram se declaradas, nao sao presumidas).
#
# Unidades: VA, A, V, m, mm2. STATELESS.
# CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# ============================================================================
"""Eletrica do edificio multipavimento: carga por unidade (NBR 5410 9.5.2),
quadro por pavimento, prumada verificada trecho a trecho e entrada."""

from __future__ import annotations

import math

import arquitetura_residencial as ar
import condutores_nbr5410 as cd
import protecao_nbr5410 as pr

SISTEMAS = ("monofasico", "bifasico", "trifasico")
# NBR 5410 6.2.7 / limites em `condutores_nbr5410.DV_LIMITE`: 5 % a partir do
# ponto de entrega da rede publica, 7 % com transformacao propria.
ORIGENS = tuple(cd.DV_LIMITE)
# Enel CNC-NDBR-DBR-25-1580 7.8.3 / nota do item de conexao coletiva: carga
# instalada acima de 75 kW nao e' atendida em baixa tensao. O limite entra como
# GATE porque, ultrapassado, o projeto muda de natureza (subestacao propria) e
# nao apenas de bitola.
CARGA_MAX_BT_KW = 75.0
FP_PADRAO = 0.92


class EntradaEletrica(ValueError):
    """A entrada declarada nao permite dimensionar a eletrica do edificio."""


def declarada(spec_eletrico) -> bool:
    """Ha o minimo: os ambientes (ou a carga) da unidade-tipo e a tensao?"""
    if not isinstance(spec_eletrico, dict):
        return False
    unidade = spec_eletrico.get("unidade") or {}
    if not isinstance(unidade, dict):
        return False
    tem_carga = bool(unidade.get("ambientes")) or bool(unidade.get("carga_VA"))
    return bool(tem_carga and spec_eletrico.get("tensao"))


def _positivo(valor):
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor) and valor > 0)


def _valida(spec):
    erros = []
    unidade = spec.get("unidade")
    if not isinstance(unidade, dict):
        erros.append("eletrico.unidade deve ser um objeto")
    else:
        ambientes = unidade.get("ambientes")
        if ambientes is not None:
            if not isinstance(ambientes, list) or not ambientes:
                erros.append("eletrico.unidade.ambientes deve ser uma lista nao "
                             "vazia de comodos da unidade-tipo")
            else:
                for i, amb in enumerate(ambientes):
                    if not isinstance(amb, dict):
                        erros.append("ambientes[%d] deve ser um objeto" % i)
                        continue
                    if not amb.get("tipo"):
                        erros.append("ambientes[%d].tipo e' obrigatorio "
                                     "(9.5.2.2.1 depende dele)" % i)
                    if not _positivo(amb.get("area_m2")):
                        erros.append("ambientes[%d].area_m2 deve ser > 0" % i)
                    if not _positivo(amb.get("perimetro_m")):
                        erros.append("ambientes[%d].perimetro_m deve ser > 0 "
                                     "(9.5.2.2.1 conta tomadas por PERIMETRO)" % i)
        elif not _positivo(unidade.get("carga_VA")):
            erros.append("declare eletrico.unidade.ambientes (para a previsao de "
                         "carga da NBR 5410 9.5.2) ou eletrico.unidade.carga_VA")
        if not _positivo(unidade.get("unidades_por_pavimento")):
            erros.append("eletrico.unidade.unidades_por_pavimento deve ser > 0")
    tensao = spec.get("tensao")
    if not isinstance(tensao, dict):
        erros.append("eletrico.tensao deve declarar o sistema e as tensoes")
    else:
        if tensao.get("sistema") not in SISTEMAS:
            erros.append("eletrico.tensao.sistema deve ser um de %s"
                         % (list(SISTEMAS),))
        if not _positivo(tensao.get("V")):
            erros.append("eletrico.tensao.V deve ser > 0 (tensao de referencia "
                         "do calculo de queda: fase-fase no trifasico, "
                         "fase-neutro no monofasico)")
    fator = spec.get("fator_demanda_entre_unidades")
    if fator is not None and not (isinstance(fator, (int, float))
                                  and not isinstance(fator, bool)
                                  and 0 < fator <= 1.0):
        erros.append("fator_demanda_entre_unidades deve estar em (0; 1]")
    origem = spec.get("entrada", {}).get("origem", "rede_publica")
    if origem not in ORIGENS:
        erros.append("entrada.origem deve ser uma de %s" % (list(ORIGENS),))
    if erros:
        raise EntradaEletrica("; ".join(erros))


def carga_da_unidade(unidade):
    """Previsao de carga de UMA unidade autonoma pela NBR 5410 9.5.2.

    Reusa as primitivas ja aferidas de `arquitetura_residencial`
    (carga_iluminacao_va / criterio_tomadas / carga_tomadas_va): uma so
    implementacao da 9.5.2 no framework.
    """
    if unidade.get("carga_VA"):
        return {"carga_VA": float(unidade["carga_VA"]),
                "iluminacao_VA": None, "tomadas_VA": None,
                "especiais_VA": 0.0, "ambientes": [],
                "proveniencia": "carga da unidade DECLARADA no spec"}
    linhas = []
    ilum = tomadas = 0.0
    for amb in unidade["ambientes"]:
        area = float(amb["area_m2"])
        perimetro = float(amb["perimetro_m"])
        va_ilum = ar.carga_iluminacao_va(area)
        criterio, n_pontos, molhado, _notas = ar.criterio_tomadas(
            amb["tipo"], area, perimetro)
        va_tug = ar.carga_tomadas_va(n_pontos, molhado)
        ilum += va_ilum
        tomadas += va_tug
        linhas.append({"nome": amb.get("nome", amb["tipo"]), "tipo": amb["tipo"],
                       "area_m2": area, "perimetro_m": perimetro,
                       "iluminacao_VA": va_ilum, "criterio_tomadas": criterio,
                       "n_tomadas": n_pontos, "tomadas_VA": va_tug})
    especiais = dict(unidade.get("cargas_especiais_VA") or {})
    for nome, valor in especiais.items():
        if not _positivo(valor):
            raise EntradaEletrica("carga especial %r deve ser > 0 VA" % nome)
    total_especiais = math.fsum(especiais.values())
    return {
        "carga_VA": ilum + tomadas + total_especiais,
        "iluminacao_VA": ilum, "tomadas_VA": tomadas,
        "especiais_VA": total_especiais, "cargas_especiais": especiais,
        "ambientes": linhas,
        "proveniencia": "NBR 5410:2004 9.5.2 sobre os ambientes declarados "
                        "(iluminacao 9.5.2.1.2 + tomadas 9.5.2.2.1/9.5.2.2.2) "
                        "mais as cargas especiais declaradas",
    }


def corrente_de_protecao(IB):
    """O menor disjuntor da serie comercial com IN >= IB.

    A ORDEM importa. Dimensionar o condutor so por IB pode devolver uma secao
    cujo Iz fica ENTRE dois degraus de disjuntor (IB = 65,5 A -> 10 mm2 com
    Iz = 66 A: nao existe disjuntor com 65,5 <= IN <= 66, e a coordenacao de
    5.3.4.1 fica sem solucao). Escolhendo IN antes e dimensionando a ampacidade
    para ELE, a condicao IB <= IN <= IZ sempre fecha. `dimensiona_condutor` ja
    aceita `I_protecao` exatamente para isso.
    """
    return next((i for i in pr.IN_DISJUNTORES if i >= IB - 1e-9), None)


def corrente(S_va, sistema, V):
    """Corrente de projeto (A) da potencia aparente."""
    if sistema == "trifasico":
        return S_va / (math.sqrt(3.0) * V)
    return S_va / V


def _quadro_de_pavimento(spec, carga_unidade_va, tensao, fp, n_por_pav):
    """Quadro de um pavimento: carga, corrente, condutor do ramal e protecao."""
    ramal = spec.get("ramal_de_pavimento") or {}
    S = carga_unidade_va * n_por_pav
    IB = corrente(S, tensao["sistema"], float(tensao["V"]))
    circ = {
        "IB": IB, "V": float(tensao["V"]),
        "L_km": float(ramal.get("comprimento_m", 5.0)) / 1000.0,
        "sistema": tensao["sistema"],
        "n_cond": 3 if tensao["sistema"] == "trifasico" else 2,
        "isolacao": ramal.get("isolacao", "PVC"),
        "metodo": ramal.get("metodo", "B1"),
        "fp": fp, "temp_amb": float(ramal.get("temp_amb", 30.0)),
        "n_agrupados": int(ramal.get("n_agrupados", 1)),
        "uso": "forca",
        "origem": spec.get("entrada", {}).get("origem", "rede_publica"),
    }
    IN_previo = corrente_de_protecao(IB)
    if IN_previo is not None:
        circ["I_protecao"] = IN_previo
    cond = cd.dimensiona_condutor(circ)
    protecao = pr.dimensiona_protecao({
        "IB": IB, "IZ": cond["Iz"] or IB,
        "uso": "forca", "local": "quadro",
        "Icc": spec.get("entrada", {}).get("Icc_A"),
        "exposicao_dps": "quadro"})
    return {"carga_VA": S, "IB_A": round(IB, 2), "unidades": n_por_pav,
            "condutor": cond, "protecao": protecao}


def _prumada(spec, carga_por_pavimento_va, tensao, fp, n_pavimentos,
             pe_direito, carga_comum_va):
    """Prumada trecho a trecho, da entrada ate o quadro mais alto.

    O trecho i (entre o pavimento i-1 e o i) conduz a carga de TODOS os
    pavimentos de i para cima. A secao e' a do trecho mais carregado (o de
    baixo), e a queda de tensao e' a SOMA das quedas dos trechos ate o quadro
    considerado - a do quadro mais alto e' a critica.
    """
    prumada_spec = spec.get("prumada") or {}
    l_trecho_m = float(prumada_spec.get("comprimento_por_pavimento_m", pe_direito))
    l_entrada_m = float(prumada_spec.get("comprimento_ate_o_primeiro_quadro_m",
                                         pe_direito))
    V = float(tensao["V"])
    sistema = tensao["sistema"]
    origem = spec.get("entrada", {}).get("origem", "rede_publica")
    dv_max = cd.DV_LIMITE[origem]

    # a carga de uso comum (elevador, bombas, iluminacao de areas comuns) e'
    # DECLARADA e entra no pe da coluna: ela nao sobe com os pavimentos.
    S_base = carga_por_pavimento_va * n_pavimentos + carga_comum_va
    IB_base = corrente(S_base, sistema, V)
    circ = {
        "IB": IB_base, "V": V,
        "L_km": (l_entrada_m + (n_pavimentos - 1) * l_trecho_m) / 1000.0,
        "sistema": sistema,
        "n_cond": 3 if sistema == "trifasico" else 2,
        "isolacao": prumada_spec.get("isolacao", "PVC"),
        "metodo": prumada_spec.get("metodo", "B1"),
        "fp": fp, "temp_amb": float(prumada_spec.get("temp_amb", 30.0)),
        "n_agrupados": int(prumada_spec.get("n_agrupados", 1)),
        "uso": "forca", "origem": origem,
    }
    IN_previo = corrente_de_protecao(IB_base)
    if IN_previo is not None:
        circ["I_protecao"] = IN_previo
    cond = cd.dimensiona_condutor(circ)
    secao = cond["secao_mm2"]
    n_paralelo = cond.get("n_paralelo", 1) or 1

    trechos = []
    dv_acumulada = 0.0
    comprimento = 0.0
    for i in range(1, n_pavimentos + 1):
        # do pe ate o quadro do pavimento i
        l_m = l_entrada_m if i == 1 else l_trecho_m
        comprimento += l_m
        # o trecho i conduz a carga dos pavimentos i..n (os que estao acima
        # dele), mais a carga comum apenas no primeiro trecho.
        pav_acima = n_pavimentos - i + 1
        S_trecho = carga_por_pavimento_va * pav_acima + (carga_comum_va if i == 1
                                                         else 0.0)
        IB_trecho = corrente(S_trecho, sistema, V)
        dv = cd.queda_pct(secao, IB_trecho / n_paralelo, l_m / 1000.0, V,
                          sistema, fp)
        dv_acumulada += dv
        trechos.append({
            "trecho": i, "pavimentos_acima": pav_acima,
            "comprimento_m": round(comprimento, 2), "L_trecho_m": round(l_m, 2),
            "carga_VA": round(S_trecho, 1), "IB_A": round(IB_trecho, 2),
            "dv_trecho_pct": round(dv, 4),
            "dv_acumulada_pct": round(dv_acumulada, 3)})
    dv_critica = trechos[-1]["dv_acumulada_pct"] if trechos else 0.0
    return {
        "carga_base_VA": S_base, "IB_base_A": round(IB_base, 2),
        "secao_mm2": secao, "n_paralelo": n_paralelo, "condutor": cond,
        "comprimento_total_m": round(comprimento, 2),
        "trechos": trechos,
        "dv_critica_pct": dv_critica, "dv_max_pct": dv_max,
        "quadro_critico": "pavimento %d (o mais alto)" % n_pavimentos,
        "gate": {
            "OK": dv_critica <= dv_max + 1e-9,
            "dv_acumulada_pct": dv_critica, "dv_max_pct": dv_max,
            "origem": origem,
            "criterio": "queda ACUMULADA da entrada ate o quadro mais alto; "
                        "verificar so o pe da coluna daria a secao certa e a "
                        "queda errada",
            "referencia": "NBR 5410:2004 6.2.7"},
    }


def dimensiona(spec_eletrico, contexto):
    """Eletrica do edificio: carga, quadro por pavimento, prumada e entrada.

    spec_eletrico: {
      'unidade': {'unidades_por_pavimento', 'ambientes' [{nome,tipo,area_m2,
                  perimetro_m}] ou 'carga_VA', 'cargas_especiais_VA'};
      'tensao' : {'sistema', 'V'};
      'areas_comuns_VA': opc - elevador, bombas, iluminacao comum (DECLARADAS);
      'fator_demanda_entre_unidades': opc (dado da CONCESSIONARIA);
      'prumada': {'comprimento_por_pavimento_m', 'isolacao', 'metodo',
                  'temp_amb', 'n_agrupados'};
      'ramal_de_pavimento': {'comprimento_m', ...};
      'entrada': {'origem', 'Icc_A', 'Icu_A'};
      'pavimentos_servidos': opc.
    }
    """
    if not isinstance(spec_eletrico, dict):
        raise EntradaEletrica("eletrico deve ser um objeto JSON")
    _valida(spec_eletrico)
    unidade = spec_eletrico["unidade"]
    tensao = spec_eletrico["tensao"]
    fp = float(spec_eletrico.get("fp", FP_PADRAO))
    n_por_pav = int(unidade["unidades_por_pavimento"])

    servidos = spec_eletrico.get("pavimentos_servidos")
    if servidos is None:
        da_9077 = contexto.get("populacao_por_pavimento")
        servidos = (sum(1 for linha in da_9077 if linha["ocupado"]) if da_9077
                    else len(contexto["pavimentos"]))
    servidos = int(servidos)
    if servidos < 1:
        raise EntradaEletrica("pavimentos_servidos deve ser >= 1")

    carga = carga_da_unidade(unidade)
    carga_unidade_va = carga["carga_VA"]
    carga_comum_va = float(spec_eletrico.get("areas_comuns_VA") or 0.0)

    quadro = _quadro_de_pavimento(spec_eletrico, carga_unidade_va, tensao, fp,
                                  n_por_pav)

    # DIVERSIDADE: sem o fator da concessionaria, soma sem reducao nenhuma.
    fator = spec_eletrico.get("fator_demanda_entre_unidades")
    carga_pav_para_prumada = quadro["carga_VA"] * (fator if fator else 1.0)
    prumada = _prumada(spec_eletrico, carga_pav_para_prumada, tensao, fp,
                       servidos, contexto["pe_direito"], carga_comum_va)

    entrada_spec = spec_eletrico.get("entrada") or {}
    S_total = prumada["carga_base_VA"]
    P_kW = S_total * fp / 1000.0
    IB_entrada = prumada["IB_base_A"]
    iz = prumada["condutor"]["Iz"] or IB_entrada
    protecao_geral = pr.dimensiona_protecao({
        "IB": IB_entrada, "IZ": iz, "uso": "forca", "local": "entrada",
        "Icc": entrada_spec.get("Icc_A"), "Icu": entrada_spec.get("Icu_A"),
        "exposicao_dps": entrada_spec.get("exposicao_dps", "rede_aerea")})

    gates = {
        "carga_por_unidade": {
            "OK": carga_unidade_va > 0,
            "carga_VA": round(carga_unidade_va, 1),
            "iluminacao_VA": carga["iluminacao_VA"],
            "tomadas_VA": carga["tomadas_VA"],
            "especiais_VA": carga["especiais_VA"],
            "referencia": "NBR 5410:2004 9.5.2"},
        "quadro_de_pavimento": {
            "OK": bool(quadro["condutor"]["OK"] and quadro["protecao"]["OK"]),
            "carga_VA": round(quadro["carga_VA"], 1), "IB_A": quadro["IB_A"],
            "secao_mm2": quadro["condutor"]["secao_mm2"],
            "disjuntor_A": quadro["protecao"]["disjuntor"]["IN"],
            "referencia": "NBR 5410:2004 6.2.5 + 6.2.7 + 5.3.4.1"},
        "prumada": {
            "OK": bool(prumada["condutor"]["OK"]),
            "secao_mm2": prumada["secao_mm2"],
            "n_paralelo": prumada["n_paralelo"],
            "IB_base_A": prumada["IB_base_A"],
            "referencia": "NBR 5410:2004 6.2.5 (+ 6.2.5.7 em paralelo)"},
        "queda_de_tensao_prumada": prumada["gate"],
        "protecao_geral": {
            "OK": bool(protecao_geral["OK"]),
            "disjuntor_A": protecao_geral["disjuntor"]["IN"],
            "dps": protecao_geral["dps"],
            "Icc_declarada_A": entrada_spec.get("Icc_A"),
            "referencia": "NBR 5410:2004 5.3.4.1 + 5.3.5 + 6.3.5.2"},
        "limite_de_baixa_tensao": {
            "OK": P_kW <= CARGA_MAX_BT_KW + 1e-9,
            "carga_instalada_kW": round(P_kW, 2),
            "limite_kW": CARGA_MAX_BT_KW,
            "referencia": "Enel CNC-NDBR-DBR-25-1580 (conexao coletiva BT): "
                          "acima deste limite o atendimento e' em media tensao, "
                          "com subestacao propria - que este modulo nao projeta"},
    }
    avisos = _avisos(spec_eletrico, fator, carga, prumada, entrada_spec)
    reprovados = sorted(k for k, g in gates.items() if not g["OK"])
    return {
        "carga_por_unidade": carga,
        "unidades_por_pavimento": n_por_pav,
        "pavimentos_servidos": servidos,
        "carga_areas_comuns_VA": carga_comum_va,
        "fator_demanda_entre_unidades": fator,
        "quadro_de_pavimento": quadro,
        "prumada": prumada,
        "entrada": {"carga_total_VA": round(S_total, 1),
                    "carga_instalada_kW": round(P_kW, 2),
                    "IB_A": IB_entrada, "protecao": protecao_geral,
                    "origem": entrada_spec.get("origem", "rede_publica")},
        "gates": gates, "reprovados": reprovados, "ATENDE": not reprovados,
        "escopo": _escopo(fator is not None),
        "avisos": avisos,
    }


def _escopo(com_fator):
    return {
        "previsao_de_carga_9_5_2": "implemented",
        "quadro_por_pavimento": "implemented",
        "prumada": "implemented",
        "queda_de_tensao_acumulada": "implemented",
        "entrada_e_protecao_geral": "implemented",
        "fator_de_demanda_entre_unidades": ("implemented" if com_fator
                                            else "not_available"),
        # nomeado em vez de omitido:
        "circuitos_terminais_da_unidade": "not_available",
        "curto_circuito_calculado": "not_available",
        "subestacao_propria": "not_available",
        "spda_nbr5419": "not_available",
        "grupo_gerador_e_alimentacao_de_emergencia": "not_available",
        "recarga_de_veiculos_nbr17019": "not_available",
        "tracado_e_prumadas_reais": "not_available",
        "aprovacao_legal": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def _avisos(spec, fator, carga, prumada, entrada_spec):
    avisos = []
    if not fator:
        avisos.append({
            "code": "sem_fator_de_demanda_entre_unidades",
            "detail": "eletrico.fator_demanda_entre_unidades nao declarado: a "
                      "prumada e a entrada foram dimensionadas somando TODAS as "
                      "unidades sem diversidade nenhuma - o TETO da demanda. O "
                      "fator e' dado da concessionaria (Enel CNC-NDBR-DBR-25-1580, "
                      "fornecimento BT em conexao coletiva) e nao e' arbitrado "
                      "aqui; com ele, a secao provavelmente cai"})
    if carga["ambientes"] and not carga["cargas_especiais"]:
        avisos.append({
            "code": "sem_cargas_especiais_declaradas",
            "detail": "nenhuma carga especial declarada na unidade (chuveiro, "
                      "torneira eletrica, ar-condicionado): 9.5.2 preve as cargas "
                      "MINIMAS de iluminacao e tomadas, e um apartamento real "
                      "quase sempre tem mais que isso"})
    if not spec.get("areas_comuns_VA"):
        avisos.append({
            "code": "sem_carga_de_uso_comum",
            "detail": "eletrico.areas_comuns_VA nao declarado: elevador, bomba "
                      "de recalque, iluminacao das areas comuns e a alimentacao "
                      "dos sistemas de emergencia NAO entraram na prumada nem na "
                      "entrada. Num predio de multiplos pavimentos essa carga "
                      "existe, e ela nao e' presumida aqui"})
    if entrada_spec.get("Icc_A") is None:
        avisos.append({
            "code": "icc_nao_declarada",
            "detail": "entrada.Icc_A nao declarada: a capacidade de interrupcao "
                      "do disjuntor geral (5.3.5) NAO foi verificada. A corrente "
                      "de curto presumida no ponto de entrega vem da "
                      "concessionaria"})
    if prumada["n_paralelo"] > 1:
        avisos.append({
            "code": "prumada_em_condutores_paralelos",
            "detail": "a prumada saiu com %d condutores por fase em paralelo "
                      "(6.2.5.7): eles tem de ser IGUAIS em secao, material, "
                      "comprimento e percurso, e o projeto executivo precisa "
                      "garantir isso" % prumada["n_paralelo"]})
    avisos.append({
        "code": "circuitos_terminais_fora_do_escopo",
        "detail": "este modulo vai da entrada ate o QUADRO de cada pavimento. A "
                  "divisao em circuitos terminais dentro da unidade, o DR por "
                  "circuito e o leiaute dos pontos dependem da planta da unidade "
                  "e sao feitos por residencial_eletrica/instalacao_eletrica"})
    return avisos


def relatorio_pt(resultado):
    """Quadro da eletrica do edificio."""
    r = resultado
    carga = r["carga_por_unidade"]
    pru = r["prumada"]
    linhas = [
        "ELETRICA DO EDIFICIO MULTIPAVIMENTO - ABNT NBR 5410:2004",
        "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
        "  Carga da unidade-tipo: %.0f VA (%s)"
        % (carga["carga_VA"], carga["proveniencia"]),
    ]
    if carga["ambientes"]:
        linhas.append("    iluminacao %.0f VA + tomadas %.0f VA + especiais %.0f VA"
                      % (carga["iluminacao_VA"], carga["tomadas_VA"],
                         carga["especiais_VA"]))
        linhas.append("")
        linhas.append("    %-16s %-14s %8s %8s %6s"
                      % ("ambiente", "tipo", "ilum(VA)", "tug(VA)", "tugs"))
        linhas.append("    " + "-" * 58)
        for amb in carga["ambientes"]:
            linhas.append("    %-16s %-14s %8.0f %8.0f %6d"
                          % (amb["nome"][:16], amb["tipo"][:14],
                             amb["iluminacao_VA"], amb["tomadas_VA"],
                             amb["n_tomadas"]))
    quadro = r["quadro_de_pavimento"]
    linhas += [
        "",
        "  QUADRO DE PAVIMENTO (%d unidade(s))" % r["unidades_por_pavimento"],
        "    carga %.0f VA -> IB %.1f A -> secao %s mm2, disjuntor %s A"
        % (quadro["carga_VA"], quadro["IB_A"],
           quadro["condutor"]["secao_mm2"],
           quadro["protecao"]["disjuntor"]["IN"]),
        "",
        "  PRUMADA (%d pavimentos, %.1f m)"
        % (r["pavimentos_servidos"], pru["comprimento_total_m"]),
        "    carga no pe %.0f VA -> IB %.1f A -> secao %s mm2%s"
        % (pru["carga_base_VA"], pru["IB_base_A"], pru["secao_mm2"],
           "" if pru["n_paralelo"] == 1 else " x%d em paralelo" % pru["n_paralelo"]),
        "",
        "    %-8s %10s %10s %10s %12s" % ("trecho", "pav.acima", "IB(A)",
                                          "dV(%)", "dV acum(%)"),
        "    " + "-" * 54,
    ]
    for t in pru["trechos"]:
        linhas.append("    %-8d %10d %10.1f %10.3f %12.3f"
                      % (t["trecho"], t["pavimentos_acima"], t["IB_A"],
                         t["dv_trecho_pct"], t["dv_acumulada_pct"]))
    linhas += [
        "    queda ate o quadro mais alto: %.2f %% (max %.1f %%) -> %s"
        % (pru["dv_critica_pct"], pru["dv_max_pct"],
           "ATENDE" if pru["gate"]["OK"] else "REPROVA"),
        "",
        "  ENTRADA: %.0f VA (%.1f kW instalados) -> IB %.1f A, disjuntor geral %s A"
        % (r["entrada"]["carga_total_VA"], r["entrada"]["carga_instalada_kW"],
           r["entrada"]["IB_A"],
           r["entrada"]["protecao"]["disjuntor"]["IN"]),
        "",
        "  Gate: %s%s" % ("ATENDE" if r["ATENDE"] else "REPROVA",
                          "" if r["ATENDE"] else " (%s)" % ", ".join(r["reprovados"])),
    ]
    for aviso in r["avisos"]:
        linhas.append("  [aviso] %s" % aviso["detail"])
    return "\n".join(linhas)
