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
# quando a carga passa dos 75 kW da conexao BT.
#
# G57: o SPDA e a alimentacao de emergencia ENTRAM, em regime declarado:
#   - SPDA (NBR 5419-1..4, reuso de `spda_nbr5419`): o retangulo LxWxH do galpao
#     vira o envelope do predio (C=sum(vaos_x), L=sum(vaos_y), H=H_total). Ng
#     (densidade de descargas, dado de sitio) e entorno/Cd/R1 sao DECLARADOS,
#     nunca default - a mesma regra do SPT no G9. Sem `eletrico.spda` no spec,
#     o escopo segue `not_available` com o motivo escrito. Limitacao nomeada:
#     equipotencializacao por pavimento e a escolha gaiola-vs-captor dedicado
#     de edificio alto seguem fora do escopo;
#   - emergencia: a fonte e' dimensionada pela CARGA ESSENCIAL (elevador,
#     pressurizacao da escada, bombas de incendio, iluminacao de emergencia),
#     nao pela total. Cada parcela e' DECLARADA em VA (`eletrico.emergencia`),
#     nunca presumida; a essencial e' a SOMA delas (derivada, nao constante).
#     Sem o bloco, o escopo segue `not_available` com o motivo escrito;
#   - recarga de veiculos (NBR 17019:2022): a norma ESTA no acervo
#     (fontes/05_ELETRICA, F056, catalogada) - o item segue `not_available`
#     por falta de projeto dedicado (modo de carga/potencia por vaga nao
#     dimensionado), nunca com motivo "fonte ausente".
# Os servicos de uso comum alem da carga declarada (elevador, bomba de recalque,
# iluminacao de emergencia - suas cargas entram se declaradas, nao sao presumidas).
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
# G57: parcelas da carga essencial que a fonte de emergencia deve atender.
# Cada uma e' potencia DECLARADA em VA; a essencial e' a SOMA, nunca constante.
PARCELAS_ESSENCIAIS = ("elevador_VA", "pressurizacao_VA", "bombas_incendio_VA",
                       "iluminacao_emergencia_VA")
# Niveis de protecao da NBR 5419-1 Tab.4 (reuso: a validacao do NP vive em
# `spda_nbr5419`; aqui so se recusa lixo cedo, com mensagem do predio).
NPS_SPDA = ("I", "II", "III", "IV")
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
    # G57: SPDA - tudo declarado, nada com default. Ng e' dado de sitio
    # (densidade de descargas/km2.ano); sem ele nao ha avaliacao de risco.
    spda = spec.get("spda")
    if spda is not None:
        if not isinstance(spda, dict):
            erros.append("eletrico.spda deve ser um objeto")
        else:
            if spda.get("NP") is not None and spda.get("NP") not in NPS_SPDA:
                erros.append("eletrico.spda.NP deve ser um de %s"
                             % (list(NPS_SPDA),))
            for chave in ("Ng", "R1"):
                valor = spda.get(chave)
                if valor is not None and not _positivo(valor):
                    erros.append("eletrico.spda.%s deve ser > 0" % chave)
            cd_spda = spda.get("Cd")
            if cd_spda is not None and not _positivo(cd_spda):
                erros.append("eletrico.spda.Cd deve ser > 0")
    # G57: emergencia - parcelas declaradas em VA; a soma e' a essencial.
    emergencia = spec.get("emergencia")
    if emergencia is not None:
        if not isinstance(emergencia, dict):
            erros.append("eletrico.emergencia deve ser um objeto")
        else:
            for chave in PARCELAS_ESSENCIAIS:
                valor = emergencia.get(chave)
                if valor is not None and not _positivo(valor):
                    erros.append("eletrico.emergencia.%s deve ser > 0 VA"
                                 % chave)
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


def _geometria_spda(contexto, servidos):
    """Envelope do predio para o SPDA: C=sum(vaos_x), L=sum(vaos_y), H=H_total.

    Reuso direto de `spda_nbr5419` (o retangulo do galpao vira o envelope do
    predio; a fisica da area de exposicao nao muda com a tipologia). Sem
    geometria legivel nao ha SPDA: retorna None em vez de arbitrar dimensao.
    """
    try:
        C = float(contexto.get("C"))
        L = float(contexto.get("L"))
    except (TypeError, ValueError):
        return None
    H = contexto.get("H_total_m")
    if H is None:
        try:
            H = float(contexto.get("pe_direito")) * int(servidos)
        except (TypeError, ValueError):
            return None
    try:
        H = float(H)
    except (TypeError, ValueError):
        return None
    if not (C > 0 and L > 0 and H > 0):
        return None
    return {"L": C, "W": L, "H": H}


def _spda_do_predio(spec_eletrico, contexto, servidos):
    """SPDA do predio (NBR 5419-1..4) por reuso de `spda_nbr5419`.

    O bloco `eletrico.spda` e' OPCIONAL: ausente, o SPDA segue `not_available`
    com aviso nomeado (um predio sem avaliacao de SPDA nao e' aprovavel, e o
    pacote legal tem de dize-lo). Presente, Ng/Cd/R1/NP sao todos DECLARADOS:
    Ng e' dado de sitio (densidade de descargas/km2.ano) e nunca recebe default
    - sem ele, Nd nao e' calculado e o aviso diz isso em voz alta.
    A avaliacao de risco e' o PORTAO (NBR 5419-2, 6.2.3): com R1 declarado e
    R1 <= RT, a protecao e' DISPENSADA (`dispensada_por_risco`) - avaliacao
    feita, resultado dispensa, sem captacao prescrita e sem pendencia no
    pacote. Sem R1, nao ha portao a aplicar e a captacao sai pelo NP.
    """
    import spda_nbr5419 as spda

    bloco = spec_eletrico.get("spda")
    if bloco is None:
        return None, {
            "code": "spda_nao_avaliado",
            "detail": "eletrico.spda nao declarado: sem avaliacao de risco da "
                      "NBR 5419-2 (Ng do sitio, entorno) nao ha NP, captacao "
                      "nem descidas. Predio sem SPDA avaliado nao e' aprovavel; "
                      "o checklist do pacote legal registra a pendencia"}
    geo = _geometria_spda(contexto, servidos)
    if geo is None:
        return None, {
            "code": "spda_sem_geometria",
            "detail": "eletrico.spda declarado mas o envelope do predio (C, L, "
                      "H_total) nao foi legivel no contexto: nada foi arbitrado"}
    caso = {"L": geo["L"], "W": geo["W"], "H": geo["H"],
            "NP": bloco.get("NP"), "Ng": bloco.get("Ng"),
            "Cd": bloco.get("Cd", 1.0), "R1": bloco.get("R1")}
    resultado = spda.dimensiona_spda(caso)
    # G57/G9: Ng e Cd (entorno, Tab.A.1) sao dados de sitio - nunca default.
    # O 1.0 acima so move a geometria (Ad/NP/descidas nao dependem de Cd);
    # o Nd so e' publicado SO com os dois declarados.
    ausentes = [chave for chave in ("Ng", "Cd") if bloco.get(chave) is None]
    if ausentes:
        resultado["Nd_ano"] = None
    resultado["dados_de_sitio_ausentes"] = ausentes
    resultado["NP_declarado"] = bloco.get("NP") is not None
    # o PORTAO da parte 2: R1 declarado e abaixo do toleravel dispensa a
    # protecao - e dispensa de verdade (sem NP/descidas prescritos).
    resultado["dispensada_por_risco"] = (
        resultado.get("R1") is not None
        and resultado.get("protecao_necessaria") is False)
    resultado["geometria"] = {"C_m": geo["L"], "L_m": geo["W"],
                              "H_total_m": geo["H"],
                              "proveniencia": "envelope do predio "
                              "(sum(vaos_x), sum(vaos_y), H_total); a fisica "
                              "da area de exposicao e' a mesma do galpao"}
    resultado["referencia"] = "ABNT NBR 5419-1/2/3/4:2026"
    resultado["limitacoes"] = (
        "equipotencializacao por pavimento e a escolha gaiola-vs-captor "
        "dedicado de edificio alto seguem fora do escopo")
    return resultado, None


def _emergencia(spec_eletrico, carga_total_va, contexto=None):
    """Carga essencial e fonte de emergencia: SOMA declarada, nunca constante.

    G57: o QUE entra na essencial e' derivado dos modulos que criam a carga,
    lidos no contexto (o resumo que `edificio_adapter` monta do incendio):
    tipo de escada exigido (pressurizacao?), blocos autonomos da NBR 10898 e
    presenca de hidrantes (bombas). So a POTENCIA de cada parcela e' declarada
    em VA - nenhum modulo a calcula (elevador, ventilador de pressurizacao,
    bomba de incendio e bloco autonomo tem potencia de equipamento, nao de
    conta). A essencial e' a soma: mudar uma parcela muda a essencial (e' isso
    que "derivada, nao redigitada" significa aqui). Sem o bloco, segue
    `not_available`.
    """
    bloco = spec_eletrico.get("emergencia")
    resumo = ((contexto or {}).get("incendio")
              if isinstance(contexto, dict) else None)
    if bloco is None:
        detalhe = ("eletrico.emergencia nao declarado: elevador, "
                   "pressurizacao da escada (NBR 9077, via incendio), "
                   "bombas de incendio e iluminacao de emergencia existem "
                   "num predio e nao sao presumidos aqui. Sem as potencias "
                   "declaradas nao ha fonte dimensionada; o checklist do "
                   "pacote legal registra a pendencia")
        if isinstance(resumo, dict):
            pede = []
            if resumo.get("tipo_escada_exigido") == "prova_de_fumaca":
                pede.append("escada a prova de fumaca (pressurizacao)")
            if resumo.get("tem_hidrantes"):
                pede.append("hidrantes (bombas)")
            if (resumo.get("blocos_total_edificio") or 0) > 0:
                pede.append("%s blocos autonomos da NBR 10898"
                            % resumo["blocos_total_edificio"])
            if pede:
                detalhe += ": o incendio desta rodada CRIA %s" % ", ".join(pede)
        return None, {"code": "emergencia_nao_dimensionada",
                      "detail": detalhe}, []
    parcelas = {}
    for chave in PARCELAS_ESSENCIAIS:
        valor = bloco.get(chave)
        if valor is not None:
            parcelas[chave] = float(valor)
    essencial = math.fsum(parcelas.values())
    if essencial <= 0:
        return None, {
            "code": "emergencia_sem_parcelas",
            "detail": "eletrico.emergencia declarado sem nenhuma parcela > 0 "
                      "VA (elevador, pressurizacao, bombas de incendio, "
                      "iluminacao de emergencia): nada a dimensionar"}, []
    total = float(carga_total_va)
    tipo_escada = (resumo or {}).get("tipo_escada_exigido")
    tem_hidrantes = (resumo or {}).get("tem_hidrantes")
    blocos_total = (resumo or {}).get("blocos_total_edificio")
    proveniencia = {
        "elevador_VA": "potencia declarada (nenhum modulo a calcula)",
        "pressurizacao_VA": ("potencia declarada; necessidade derivada do "
                             "incendio (tipo de escada exigido: %s)"
                             % tipo_escada),
        "bombas_incendio_VA": ("potencia declarada; necessidade derivada do "
                               "incendio (hidrantes: %s)"
                               % ("com hidrantes" if tem_hidrantes
                                  else "sem hidrantes nesta rodada")),
        "iluminacao_emergencia_VA": ("potencia declarada; %s blocos autonomos "
                                    "derivados da NBR 10898 no incendio"
                                    % blocos_total),
    }
    coerencia = []
    if tipo_escada == "prova_de_fumaca" and "pressurizacao_VA" not in parcelas:
        coerencia.append({
            "code": "emergencia_pressurizacao_nao_declarada",
            "detail": "o incendio exige escada a prova de fumaca e a "
                      "pressurizacao (NBR 14880, fora do acervo e fora do "
                      "escopo) nao teve potencia declarada: a essencial sai "
                      "SEM ela, e a fonte fica subdimensionada para esse "
                      "ventilador"})
    if tem_hidrantes and "bombas_incendio_VA" not in parcelas:
        coerencia.append({
            "code": "emergencia_bombas_nao_declaradas",
            "detail": "o incendio tem hidrantes e nenhuma potencia de bomba "
                      "foi declarada: a essencial sai SEM as bombas de "
                      "incendio"})
    if (isinstance(blocos_total, (int, float)) and blocos_total > 0
            and "iluminacao_emergencia_VA" not in parcelas):
        coerencia.append({
            "code": "emergencia_iluminacao_nao_declarada",
            "detail": "o incendio dimensionou %d blocos autonomos (NBR 10898) "
                      "e nenhuma potencia de iluminacao de emergencia foi "
                      "declarada: a essencial sai SEM eles" % blocos_total})
    resultado = {
        "parcelas_VA": {k: round(v, 1) for k, v in parcelas.items()},
        "carga_essencial_VA": round(essencial, 1),
        "carga_total_VA": round(total, 1),
        "fracao_da_total": round(essencial / total, 4) if total > 0 else None,
        "proveniencia_parcelas": {k: proveniencia[k] for k in parcelas},
        "proveniencia": "soma das parcelas declaradas em eletrico.emergencia; "
                        "o CONJUNTO de parcelas e' derivado do incendio "
                        "(tipo de escada, hidrantes, blocos da 10898); a "
                        "fonte e' dimensionada pela essencial, nao pela total",
        "referencia": "NBR 5410 (servicos de seguranca) + NBR 9077/10898/13714 "
                      "(cargas que a criam)",
    }
    if ("iluminacao_emergencia_VA" in parcelas
            and isinstance(blocos_total, (int, float)) and blocos_total > 0):
        resultado["w_por_bloco_implicito"] = round(
            parcelas["iluminacao_emergencia_VA"] / blocos_total, 2)
    return resultado, None, coerencia


def dimensiona(spec_eletrico, contexto):
    """Eletrica do edificio: carga, quadro por pavimento, prumada e entrada.

    spec_eletrico: {
      'unidade': {'unidades_por_pavimento', 'ambientes' [{nome,tipo,area_m2,
                   perimetro_m}] ou 'carga_VA', 'cargas_especiais_VA'};
      'tensao' : {'sistema', 'V'};
      'areas_comuns_VA': opc - elevador, bombas, iluminacao comum (DECLARADAS);
      'fator_demanda_entre_unidades': opc (dado da CONCESSIONARIA);
      'spda': opc {'NP', 'Ng', 'Cd', 'R1'} - todos DECLARADOS (G57; Ng e'
             dado de sitio, nunca default);
      'emergencia': opc {'elevador_VA', 'pressurizacao_VA',
             'bombas_incendio_VA', 'iluminacao_emergencia_VA'} - parcelas
             DECLARADAS; a essencial e' a SOMA (G57);
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

    # G57: SPDA (reuso) e carga essencial (soma declarada). Nenhum dos dois
    # entra na prumada/entrada: a essencial dimensiona a FONTE de emergencia,
    # nao o alimentador normal.
    spda_res, aviso_spda = _spda_do_predio(spec_eletrico, contexto, servidos)
    emergencia_res, aviso_emerg, coerencia_emerg = _emergencia(
        spec_eletrico, S_total, contexto)

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
        "spda": ({
            "OK": True,
            "NP": (None if spda_res["dispensada_por_risco"]
                   else spda_res["NP"]),
            "n_descidas": (None if spda_res["dispensada_por_risco"]
                           else spda_res["n_descidas"]),
            "Nd_ano": spda_res["Nd_ano"],
            "dispensada_por_risco": bool(spda_res["dispensada_por_risco"]),
            "avaliacao_de_risco": (
                "R1 <= RT: protecao DISPENSADA (NBR 5419-2 6.2.3)"
                if spda_res["dispensada_por_risco"]
                else ("com Ng e Cd declarados" if spda_res["Nd_ano"]
                      is not None else "sem dado de sitio: captacao/descidas "
                      "dimensionadas, risco nao avaliado")),
            "referencia": spda_res["referencia"],
        } if spda_res is not None else {
            "OK": True,
            "NP": None,
            "motivo": "eletrico.spda nao declarado",
            "referencia": "ABNT NBR 5419-1/2/3/4:2026"}),
        "carga_essencial": ({
            "OK": 0 < emergencia_res["carga_essencial_VA"] < S_total,
            "carga_essencial_VA": emergencia_res["carga_essencial_VA"],
            "carga_total_VA": emergencia_res["carga_total_VA"],
            "fracao_da_total": emergencia_res["fracao_da_total"],
            "criterio": "fonte dimensionada pela essencial (soma das parcelas "
                        "declaradas), nao pela total",
            "referencia": emergencia_res["referencia"],
        } if emergencia_res is not None else {
            "OK": True,
            "carga_essencial_VA": None,
            "motivo": "eletrico.emergencia nao declarado",
            "referencia": "NBR 5410 (servicos de seguranca)"}),
    }
    avisos = _avisos(spec_eletrico, fator, carga, prumada, entrada_spec,
                     aviso_spda, aviso_emerg, spda_res, coerencia_emerg)
    reprovados = sorted(k for k, g in gates.items() if not g["OK"])
    return {
        "carga_por_unidade": carga,
        "unidades_por_pavimento": n_por_pav,
        "pavimentos_servidos": servidos,
        "carga_areas_comuns_VA": carga_comum_va,
        "fator_demanda_entre_unidades": fator,
        "quadro_de_pavimento": quadro,
        "prumada": prumada,
        "spda": spda_res,
        "emergencia": emergencia_res,
        "entrada": {"carga_total_VA": round(S_total, 1),
                    "carga_instalada_kW": round(P_kW, 2),
                    "IB_A": IB_entrada, "protecao": protecao_geral,
                    "origem": entrada_spec.get("origem", "rede_publica")},
        "gates": gates, "reprovados": reprovados, "ATENDE": not reprovados,
        "escopo": _escopo(fator is not None, spda_res is not None,
                          emergencia_res is not None),
        "avisos": avisos,
    }


def _escopo(com_fator, com_spda=False, com_emergencia=False):
    return {
        "previsao_de_carga_9_5_2": "implemented",
        "quadro_por_pavimento": "implemented",
        "prumada": "implemented",
        "queda_de_tensao_acumulada": "implemented",
        "entrada_e_protecao_geral": "implemented",
        "fator_de_demanda_entre_unidades": ("implemented" if com_fator
                                            else "not_available"),
        # G57: SPDA e emergencia passam a implemented QUANDO declarados; sem
        # eles, not_available com o motivo escrito no aviso (e no checklist do
        # pacote legal do predio - o portao deste goal).
        "spda_nbr5419": ("implemented" if com_spda else "not_available"),
        "grupo_gerador_e_alimentacao_de_emergencia": (
            "implemented" if com_emergencia else "not_available"),
        # nomeado em vez de omitido:
        "circuitos_terminais_da_unidade": "not_available",
        "curto_circuito_calculado": "not_available",
        "subestacao_propria": "not_available",
        # G57: NBR 17019:2022 ESTA no acervo (fontes/05_ELETRICA, F056). O item
        # segue not_available por falta de projeto dedicado (modo de carga e
        # potencia por vaga nao dimensionados) - nunca "fonte ausente".
        "recarga_de_veiculos_nbr17019": "not_available",
        # G53: prumada + eletrocalha por pavimento no frame da estrutura
        # (bim_instalacoes_edificio). O leiaute dentro da unidade continua
        # fora (planta da unidade). D94/G59: a chave dizia
        # `tracado_e_prumadas_reais` e o tracado e' CONVENCIONAL em shaft
        # (mesma decisao declarada da hidraulica) - a palavra tem de caber
        # no que existe, entao a chave carrega "convencional" no nome.
        "tracado_convencional_das_prumadas": "implemented",
        "aprovacao_legal": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def _avisos(spec, fator, carga, prumada, entrada_spec, aviso_spda=None,
            aviso_emerg=None, spda_res=None, coerencia_emerg=None):
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
    # G57: os tres not_available com motivo escrito (o portao le o escopo; o
    # motivo vive aqui, no aviso).
    if aviso_spda is not None:
        avisos.append(aviso_spda)
    elif spda_res is not None and spda_res.get("Nd_ano") is None:
        faltam = spda_res.get("dados_de_sitio_ausentes") or ["Ng"]
        avisos.append({
            "code": "spda_sem_Ng_declarado",
            "detail": "eletrico.spda sem %s: captacao e descidas sairam pelo "
                      "NP %s, mas Nd (NBR 5419-2 A.3) NAO foi calculado. "
                      "Densidade de descargas e entorno sao dados de sitio e "
                      "nunca recebem default - mesma regra do SPT no G9"
                      % (" e ".join(faltam), spda_res["NP"])})
    if spda_res is not None:
        if spda_res.get("dispensada_por_risco"):
            avisos.append({
                "code": "spda_dispensada_por_risco",
                "detail": "avaliacao de risco da NBR 5419-2 com R1 declarado: "
                          "R1 <= RT, protecao DISPENSADA (6.2.3). Nenhuma "
                          "captacao/descida prescrita e nenhuma pendencia de "
                          "SPDA no pacote - avaliacao feita, resultado "
                          "dispensa"})
        else:
            if not spda_res.get("NP_declarado"):
                avisos.append({
                    "code": "spda_np_adotado",
                    "detail": "eletrico.spda sem NP: captacao e descidas sairam "
                              "pelo NP III ADOTADO por conservadorismo (meio da "
                              "tabela), nao por avaliacao de risco declarada. "
                              "Confirmar o nivel com o responsavel tecnico"})
            avisos.append({
                "code": "spda_limites_de_edificio_alto",
                "detail": "SPDA pelo envelope (C x L x H_total) via spda_nbr5419: "
                          "%s. %s"
                          % ("NP %s, %d descidas, captor 35 mm2 / descida %d mm2 / "
                             "eletrodo 50 mm2" % (spda_res["NP"],
                                                  spda_res["n_descidas"],
                                                  spda_res["secao_descida_mm2"],
                                                  ),
                             spda_res["limitacoes"])})
    if aviso_emerg is not None:
        avisos.append(aviso_emerg)
    for item in (coerencia_emerg or []):
        avisos.append(item)
    avisos.append({
        "code": "recarga_veiculos_sem_projeto",
        "detail": "recarga de veiculos (NBR 17019:2022) sem projeto dedicado: "
                  "modo de carga e potencia por vaga nao dimensionados. A "
                  "norma ESTA no acervo (fontes/05_ELETRICA, F056 catalogada) "
                  "- o motivo nao e' fonte ausente"})
    avisos.append({
        "code": "tracado_das_prumadas_convencional",
        "detail": "a prumada e' dimensionada como UMA prumada servindo todos "
                  "os pavimentos e e' POSICIONADA num shaft convencional "
                  "(bim_instalacoes_edificio, 1,0 m do canto, no frame da "
                  "estrutura) para que o clash ache o furo. O numero real de "
                  "prumadas e os ramais por unidade dependem da planta de "
                  "arquitetura, que este framework nao tem para o edificio"})
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
    spda_r = r.get("spda")
    if spda_r is not None:
        if spda_r.get("dispensada_por_risco"):
            linhas.append(
                "  SPDA (NBR 5419): DISPENSADA por avaliacao de risco "
                "(R1=%s <= RT, 6.2.3)" % spda_r["R1"])
        else:
            linhas.append(
                "  SPDA (NBR 5419): NP %s, %d descidas, Nd=%s (envelope %.1f x "
                "%.1f x %.1f m)" % (spda_r["NP"], spda_r["n_descidas"],
                                    spda_r["Nd_ano"], spda_r["geometria"]["C_m"],
                                    spda_r["geometria"]["L_m"],
                                    spda_r["geometria"]["H_total_m"]))
    em_r = r.get("emergencia")
    if em_r is not None:
        linhas.append(
            "  EMERGENCIA: essencial %.0f VA (de %.0f VA total) = %s" % (
                em_r["carga_essencial_VA"], em_r["carga_total_VA"],
                " + ".join("%s %.0f" % (k.replace("_VA", ""), v)
                           for k, v in em_r["parcelas_VA"].items())))
    for aviso in r["avisos"]:
        linhas.append("  [aviso] %s" % aviso["detail"])
    return "\n".join(linhas)
