# ============================================================================
# circuitos_planta.py - PONTOS, DIVISAO EM CIRCUITOS E QUADRO DE CARGAS A PARTIR
# DOS AMBIENTES DA PLANTA (plano de 2026-10-08, Fase 5, segundo
# passo). Entra a previsao de carga que o motor ja calcula por ambiente
# (arquitetura_residencial.rodar, alimentado por ambientes_dxf); sai a lista de
# pontos no formato do motor de dimensionamento, os circuitos e o quadro.
#
# REGRAS DE DIVISAO (lidas no acervo, edicao 2004 da norma de instalacoes de
# baixa tensao, paginas 18-19 e 184):
#   4.2.5.5  circuitos terminais distintos para iluminacao e para tomadas;
#   9.5.3.2  tomadas de cozinha, copa, copa-cozinha, area de servico, lavanderia
#            e analogos em circuitos SO de tomadas desses locais;
#   9.5.3.1  equipamento com corrente nominal acima de 10 A em circuito
#            independente.
# A excecao de 9.5.3.3 (circuito comum de iluminacao e tomadas) NAO e' usada.
#
# O QUE A NORMA NAO DA E NAO SE INVENTA AQUI: quantos volt-amperes cabem num
# circuito, a tensao, o numero de fases e os equipamentos de uso especifico.
# Tudo isso e' CRITERIO DECLARADO por quem responde pelo projeto; criterio
# ausente e' erro nomeado e nenhum circuito sai.
#
# DIMENSIONAMENTO (terceiro passo): `dimensionar` monta os circuitos no
# contrato do motor que ja existe (dimensionamento_eletrico_residencial) e o
# chama; nenhuma tabela e' reescrita aqui. O que o motor pede e a planta nao
# tem (isolacao, metodo de instalacao, temperatura, agrupamento, fator de
# potencia, limite de queda, exposicao) e' DECLARADO em `instalacao`.
#
# COMPRIMENTO: ou vem declarado circuito a circuito, ou e' ESTIMADO pela
# planta: distancia ortogonal (|dx| + |dy|) do quadro ao vertice mais distante
# do ambiente mais distante do circuito, vezes um fator de tracado declarado,
# mais um acrescimo vertical declarado. E' estimativa de anteprojeto, marcada
# como tal na saida; o comprimento do tracado real substitui.
#
# DEMANDA E PADRAO DE ENTRADA (sexto passo): `demanda_e_entrada` monta a
# entrada dos dois motores da distribuidora que ja existem
# (demanda_residencial_enel e entrada_enel_bt) e os chama. A ponte NAO
# interpreta a regra da distribuidora: ambiente cujo tipo nao e' exatamente um
# dos modulos do motor so entra com o modulo DECLARADO para aquele tipo;
# cada equipamento DECLARA o seu grupo de demanda: "aquecimento" (a ponte
# monta o item), "motor" (o motor eletrico vem descrito em demanda.motores, no
# contrato do calculador: quantidade, potencia em CV e ligacao) ou "nenhum"
# (nao entra em grupo acessorio). Motores e iluminacao especial sao listas
# declaradas, vazias se nao ha. A rede (fator locacional, tensao, tipo de
# fornecimento, rede aerea ou nao) e' declarada.
#
# O que NAO se faz aqui: curto-circuito.
#
# Biblioteca: quem a chama pela linha de comando e' o ambientes_dxf
# (python ambientes_dxf.py <planta.dxf> [camada] [mm|cm|m] criterios=<json>).
# ============================================================================
"""Pontos minimos, divisao em circuitos e quadro de cargas dos ambientes."""

from __future__ import annotations

import math

# 9.5.3.1 (pagina 184 do acervo): "corrente nominal superior a 10 A"
CORRENTE_CIRCUITO_INDEPENDENTE_A = 10.0

CLASSE_ILUMINACAO = "iluminacao"
CLASSE_TOMADAS = "tomadas"
CLASSE_TOMADAS_EXCLUSIVAS = "tomadas_exclusivas"      # locais de 9.5.3.2
CLASSE_EQUIPAMENTO = "equipamento"
CLASSES_COM_LIMITE = (CLASSE_ILUMINACAO, CLASSE_TOMADAS, CLASSE_TOMADAS_EXCLUSIVAS)
PREFIXO = {CLASSE_ILUMINACAO: "IL", CLASSE_TOMADAS: "TG",
           CLASSE_TOMADAS_EXCLUSIVAS: "TE", CLASSE_EQUIPAMENTO: "EQ"}
FASES = ("A", "B", "C")
# do mais restritivo ao menos; so rotula o local do circuito para o motor de
# protecao decidir o dispositivo diferencial
ORDEM_LOCAL = ("banheiro", "molhado", "externo", "seco")
CAMPOS_INSTALACAO = ("isolacao", "metodo_referencia", "temperatura_ambiente_c",
                     "circuitos_agrupados", "queda_tensao_max_pct", "exposicao_dps")
CLASSES = CLASSES_COM_LIMITE + (CLASSE_EQUIPAMENTO,)


def _positivo(valor):
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor) and valor > 0)


def _erros_dos_criterios(criterios):
    """Tudo o que quem projeta tem de declarar. Sem valor padrao."""
    if not isinstance(criterios, dict):
        return [{"code": "criterio_ausente", "campo": "criterios",
                 "detail": "os criterios de divisao devem ser um objeto"}]
    erros = []
    if "tensao_v" not in criterios or not _positivo(criterios["tensao_v"]):
        erros.append({"code": "criterio_ausente", "campo": "tensao_v",
                      "detail": "tensao dos circuitos de iluminacao e tomadas, em volts"})
    if "n_fases" not in criterios or criterios["n_fases"] not in (1, 2, 3):
        erros.append({"code": "criterio_ausente", "campo": "n_fases",
                      "detail": "numero de fases do quadro: 1, 2 ou 3"})
    limites = criterios["limite_va"] if "limite_va" in criterios else None
    for classe in CLASSES_COM_LIMITE:
        if not isinstance(limites, dict) or classe not in limites or not _positivo(limites[classe]):
            erros.append({"code": "criterio_ausente", "campo": "limite_va.%s" % classe,
                          "detail": "potencia maxima por circuito desta classe, em VA "
                                    "(criterio de projeto; a norma nao fixa)"})
    if "equipamentos" not in criterios or not isinstance(criterios["equipamentos"], list):
        erros.append({"code": "criterio_ausente", "campo": "equipamentos",
                      "detail": "lista dos equipamentos de uso especifico (vazia se nao ha)"})
    return erros


def pontos_dos_ambientes(previsao, tensao_v):
    """Um ponto de luz por ambiente com a carga minima de iluminacao e os
    pontos de tomada minimos, cada um com a potencia que o motor atribui.
    Devolve [(classe, ponto)] na ordem da planta."""
    import arquitetura_residencial as AR

    saida = []
    for i, amb in enumerate(previsao["ambientes"], start=1):
        if not amb["geometria_ok"]:
            continue
        saida.append((CLASSE_ILUMINACAO, {
            "id": "L%02d" % i, "room": amb["nome"], "kind": "lighting",
            "power_va": float(amb["carga_iluminacao_va"]), "voltage_v": float(tensao_v)}))
        n = int(amb["n_tomadas_min"])
        molhado = bool(amb["molhado"])
        potencias = [AR.carga_tomadas_va(k, molhado) - AR.carga_tomadas_va(k - 1, molhado)
                     for k in range(1, n + 1)]
        if abs(sum(potencias) - float(amb["carga_tomadas_va"])) > 1e-6:
            raise ValueError(
                "%s: a soma dos pontos de tomada (%.1f VA) nao fecha com a previsao do "
                "motor (%.1f VA)" % (amb["nome"], sum(potencias), amb["carga_tomadas_va"]))
        classe = (CLASSE_TOMADAS_EXCLUSIVAS if amb["tipo"] in AR.TIPOS_MOLHADOS_PERIMETRO
                  else CLASSE_TOMADAS)
        for k, pot in enumerate(potencias, start=1):
            saida.append((classe, {
                "id": "T%02d.%d" % (i, k), "room": amb["nome"], "kind": "tug",
                "power_va": float(pot), "voltage_v": float(tensao_v)}))
    return saida


def _empacota(classe, pontos, limite_va, erros):
    """Enche circuitos na ordem da planta; ponto que nao cabe abre o proximo."""
    circuitos, atual, soma = [], [], 0.0
    for p in pontos:
        if p["power_va"] > limite_va + 1e-9:
            erros.append({"code": "ponto_maior_que_limite", "ponto": p["id"],
                          "ambiente": p["room"], "potencia_va": p["power_va"],
                          "limite_va": limite_va,
                          "detail": "um ponto sozinho passa do limite declarado para a classe"})
            continue
        if atual and soma + p["power_va"] > limite_va + 1e-9:
            circuitos.append(atual)
            atual, soma = [], 0.0
        atual.append(p)
        soma += p["power_va"]
    if atual:
        circuitos.append(atual)
    return [{"classe": classe, "pontos": c} for c in circuitos]


def _equipamentos(criterios, ambientes, erros):
    """Cada equipamento declarado vira um ponto e um circuito so dele."""
    saida = []
    for j, eq in enumerate(criterios["equipamentos"], start=1):
        faltam = [c for c in ("nome", "ambiente", "potencia_va", "tensao_v", "n_fases")
                  if not isinstance(eq, dict) or c not in eq]
        if faltam:
            erros.append({"code": "equipamento_incompleto", "indice": j, "campos": faltam,
                          "detail": "equipamento precisa de nome, ambiente, potencia_va, "
                                    "tensao_v e n_fases"})
            continue
        if (not _positivo(eq["potencia_va"]) or not _positivo(eq["tensao_v"])
                or eq["n_fases"] not in (1, 2, 3) or eq["n_fases"] > criterios["n_fases"]):
            erros.append({"code": "equipamento_invalido", "equipamento": eq["nome"],
                          "detail": "potencia e tensao positivas; n_fases 1 a 3 e nao maior "
                                    "que o do quadro"})
            continue
        if eq["ambiente"] not in ambientes:
            erros.append({"code": "equipamento_em_ambiente_desconhecido",
                          "equipamento": eq["nome"], "ambiente": eq["ambiente"],
                          "detail": "o ambiente nao esta entre os lidos da planta"})
            continue
        saida.append((eq, {"id": "E%02d" % j, "room": eq["ambiente"], "kind": "tue",
                           "power_va": float(eq["potencia_va"]),
                           "voltage_v": float(eq["tensao_v"]), "nome": eq["nome"]}))
    return saida


def _local_do_ambiente(amb):
    import arquitetura_residencial as AR

    if amb["tipo"] in AR.TIPOS_BANHEIRO:
        return "banheiro"
    if amb["molhado"]:
        return "molhado"
    if amb["tipo"] in AR.TIPOS_VARANDA:
        return "externo"
    return "seco"


def _distribui_fases(circuitos, n_fases):
    """Maior carga primeiro, sempre na fase menos carregada. E' uma heuristica
    de equilibrio (4.2.5.6 pede 'o maior equilibrio possivel', sem numero)."""
    carga = {f: 0.0 for f in FASES[:n_fases]}
    for c in sorted(circuitos, key=lambda c: (-c["potencia_va"], c["id"])):
        escolhidas = sorted(carga, key=lambda f: (carga[f], f))[:c["n_fases"]]
        for f in escolhidas:
            carga[f] += c["potencia_va"] / c["n_fases"]
        c["fases"] = sorted(escolhidas)
    return carga


def dividir(previsao, criterios):
    """{pontos, circuitos, quadro, erros, ATENDE}. `previsao` e' a saida de
    arquitetura_residencial.rodar; `criterios` = {tensao_v, n_fases,
    limite_va: {iluminacao, tomadas, tomadas_exclusivas},
    equipamentos: [{nome, ambiente, potencia_va, tensao_v, n_fases}]}."""
    erros = _erros_dos_criterios(criterios)
    if erros:
        return {"pontos": [], "circuitos": [], "quadro": None, "erros": erros, "ATENDE": False}
    classificados = pontos_dos_ambientes(previsao, criterios["tensao_v"])
    nomes = {a["nome"] for a in previsao["ambientes"] if a["geometria_ok"]}
    brutos = []
    for classe in CLASSES_COM_LIMITE:
        brutos += _empacota(classe, [p for c, p in classificados if c == classe],
                            float(criterios["limite_va"][classe]), erros)
    equipamentos = _equipamentos(criterios, nomes, erros)
    pontos = [p for _c, p in classificados] + [p for _e, p in equipamentos]

    circuitos, ordem = [], {}
    for bruto in brutos:
        ordem[bruto["classe"]] = ordem[bruto["classe"]] + 1 if bruto["classe"] in ordem else 1
        pot = sum(p["power_va"] for p in bruto["pontos"])
        circuitos.append({
            "id": "%s%d" % (PREFIXO[bruto["classe"]], ordem[bruto["classe"]]),
            "classe": bruto["classe"],
            "use": "iluminacao" if bruto["classe"] == CLASSE_ILUMINACAO else "forca",
            "point_ids": [p["id"] for p in bruto["pontos"]],
            "ambientes": sorted({p["room"] for p in bruto["pontos"]}),
            "potencia_va": pot, "tensao_v": float(criterios["tensao_v"]), "n_fases": 1,
            "corrente_a": pot / float(criterios["tensao_v"])})
    for k, (eq, ponto) in enumerate(equipamentos, start=1):
        divisor = math.sqrt(3.0) if eq["n_fases"] == 3 else 1.0
        corrente = ponto["power_va"] / (divisor * ponto["voltage_v"])
        circuitos.append({
            "id": "%s%d" % (PREFIXO[CLASSE_EQUIPAMENTO], k), "classe": CLASSE_EQUIPAMENTO,
            "use": "forca", "point_ids": [ponto["id"]], "ambientes": [ponto["room"]],
            "equipamento": eq["nome"], "potencia_va": ponto["power_va"],
            "tensao_v": ponto["voltage_v"], "n_fases": eq["n_fases"], "corrente_a": corrente,
            # o circuito e' proprio de todo jeito; aqui fica dito se a norma o EXIGE
            "independente_exigido_9_5_3_1": corrente > CORRENTE_CIRCUITO_INDEPENDENTE_A})

    local_de = {a["nome"]: _local_do_ambiente(a) for a in previsao["ambientes"]
                if a["geometria_ok"]}
    for c in circuitos:
        c["local"] = min((local_de[nome] for nome in c["ambientes"]), key=ORDEM_LOCAL.index)
    por_fase = _distribui_fases(circuitos, criterios["n_fases"])
    maior, menor = max(por_fase.values()), min(por_fase.values())
    quadro = {
        "carga_instalada_va": sum(c["potencia_va"] for c in circuitos),
        "n_circuitos": len(circuitos), "n_pontos": len(pontos),
        "carga_por_fase_va": por_fase,
        "desequilibrio_pct": (100.0 * (maior - menor) / maior) if maior > 0 else 0.0,
        "escopo": "carga instalada; sem demanda, sem condutor e sem protecao"}
    atende = bool(previsao["ATENDE"]) and not erros and bool(circuitos)
    return {"pontos": pontos, "circuitos": circuitos, "quadro": quadro, "erros": erros,
            "criterios": criterios, "ATENDE": atende}


def relatorio_pt(resultado):
    if resultado["quadro"] is None:
        return "DIVISAO NAO FEITA - criterios ausentes:\n" + "\n".join(
            "  %s: %s" % (e["campo"], e["detail"]) for e in resultado["erros"])
    linhas = ["QUADRO DE CARGAS (carga instalada)",
              "%-5s %-19s %5s %9s %7s %8s %-5s  %s" % (
                  "circ", "classe", "pts", "VA", "V", "A", "fase", "ambientes")]
    for c in resultado["circuitos"]:
        linhas.append("%-5s %-19s %5d %9.0f %7.0f %8.2f %-5s  %s" % (
            c["id"], c["classe"], len(c["point_ids"]), c["potencia_va"], c["tensao_v"],
            c["corrente_a"], "".join(c["fases"]), ", ".join(c["ambientes"])))
    q = resultado["quadro"]
    linhas.append("total %.0f VA em %d circuitos; por fase: %s; desequilibrio %.1f %%" % (
        q["carga_instalada_va"], q["n_circuitos"],
        ", ".join("%s=%.0f" % par for par in sorted(q["carga_por_fase_va"].items())),
        q["desequilibrio_pct"]))
    for e in resultado["erros"]:
        linhas.append("ERRO %s: %s" % (e["code"], e["detail"]))
    linhas.append("ATENDE: %s" % resultado["ATENDE"])
    return "\n".join(linhas)



def _nao_negativo(valor):
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor) and valor >= 0)


def comprimentos_pela_planta(divisao, geometria, quadro_m, tracado):
    """{comprimentos: {circuito: {comprimento_m, origem, ...}}, erros}.
    `geometria` = {ambiente: [[x_m, y_m], ...]}; `quadro_m` = [x, y];
    `tracado` = {fator (>= 1), acrescimo_vertical_m (>= 0)}, declarados."""
    erros = []
    if (not isinstance(tracado, dict) or "fator" not in tracado
            or not _positivo(tracado["fator"]) or tracado["fator"] < 1.0):
        erros.append({"code": "criterio_ausente", "campo": "tracado.fator",
                      "detail": "fator (>= 1) que leva a distancia ortogonal ao comprimento "
                                "do tracado"})
    if (not isinstance(tracado, dict) or "acrescimo_vertical_m" not in tracado
            or not _nao_negativo(tracado["acrescimo_vertical_m"])):
        erros.append({"code": "criterio_ausente", "campo": "tracado.acrescimo_vertical_m",
                      "detail": "metros de subida e descida somados a cada circuito"})
    if quadro_m is None:
        erros.append({"code": "quadro_nao_marcado", "campo": "quadro",
                      "detail": "sem a posicao do quadro na planta nao ha comprimento "
                                "estimado; marque o quadro ou declare os comprimentos"})
    saida = {}
    if erros:
        return {"comprimentos": saida, "erros": erros}
    qx, qy = quadro_m
    for c in divisao["circuitos"]:
        longe = None
        for nome in c["ambientes"]:
            if nome not in geometria:
                erros.append({"code": "ambiente_sem_geometria", "circuito": c["id"],
                              "ambiente": nome, "campo": "geometria",
                              "detail": "ambiente do circuito sem poligono lido da planta"})
                longe = None
                break
            d = max(abs(x - qx) + abs(y - qy) for x, y in geometria[nome])
            if longe is None or d > longe[0]:
                longe = (d, nome)
        if longe is None:
            continue
        saida[c["id"]] = {
            "comprimento_m": tracado["fator"] * longe[0] + tracado["acrescimo_vertical_m"],
            "origem": "estimado_pela_planta", "distancia_ortogonal_m": longe[0],
            "ambiente_mais_distante": longe[1]}
    return {"comprimentos": saida, "erros": erros}


def _erros_da_instalacao(instalacao):
    if not isinstance(instalacao, dict):
        return [{"code": "criterio_ausente", "campo": "instalacao",
                 "detail": "os dados de instalacao devem ser um objeto"}]
    erros = [{"code": "criterio_ausente", "campo": "instalacao.%s" % campo,
              "detail": "dado de instalacao declarado por quem projeta"}
             for campo in CAMPOS_INSTALACAO if campo not in instalacao]
    fps = instalacao["fator_potencia"] if "fator_potencia" in instalacao else None
    for classe in CLASSES:
        if not isinstance(fps, dict) or classe not in fps:
            erros.append({"code": "criterio_ausente",
                          "campo": "instalacao.fator_potencia.%s" % classe,
                          "detail": "fator de potencia adotado para a classe"})
    return erros


def dimensionar(divisao, instalacao, comprimentos):
    """Condutor e protecao de cada circuito pelo motor residencial.
    `comprimentos` = {circuito: {comprimento_m, origem}}. Devolve {circuits:
    <saida do motor ou None>, resumo, comprimentos, erros, ATENDE}."""
    import dimensionamento_eletrico_residencial as DR

    erros = list(_erros_da_instalacao(instalacao))
    if divisao["quadro"] is None:
        erros.append({"code": "divisao_nao_feita", "campo": "divisao",
                      "detail": "sem circuitos nao ha o que dimensionar"})
    for c in divisao["circuitos"]:
        if c["id"] not in comprimentos or not _positivo(comprimentos[c["id"]]["comprimento_m"]):
            erros.append({"code": "comprimento_ausente", "campo": "comprimento",
                          "circuito": c["id"],
                          "detail": "circuito sem comprimento declarado nem estimado"})
    if erros:
        return {"circuits": None, "resumo": [], "comprimentos": comprimentos,
                "erros": erros, "ATENDE": False}
    designs = []
    for c in divisao["circuitos"]:
        trifasico = c["n_fases"] == 3
        designs.append({
            "id": c["id"], "point_ids": list(c["point_ids"]),
            "length_m": float(comprimentos[c["id"]]["comprimento_m"]),
            "system": "trifasico" if trifasico else "monofasico",
            "conductors_loaded": 3 if trifasico else 2,
            "insulation": instalacao["isolacao"],
            "reference_method": instalacao["metodo_referencia"],
            "ambient_temperature_C": instalacao["temperatura_ambiente_c"],
            "grouping_count": instalacao["circuitos_agrupados"],
            "power_factor": instalacao["fator_potencia"][c["classe"]],
            "voltage_drop_limit_pct": instalacao["queda_tensao_max_pct"],
            "use": c["use"],
            "protection": {"location": c["local"], "exposure": instalacao["exposicao_dps"]}})
    pontos = [{k: p[k] for k in ("id", "room", "kind", "power_va", "voltage_v")}
              for p in divisao["pontos"]]
    calculo = DR.calculate_residential_circuit_designs({"points": pontos, "designs": designs}, [])
    feitos = {d["id"]: d for d in calculo["designs"]}
    resumo = []
    for c in divisao["circuitos"]:
        if c["id"] not in feitos:
            continue
        d = feitos[c["id"]]
        resumo.append({
            "id": c["id"], "classe": c["classe"], "local": c["local"],
            "comprimento_m": d["declared_length_m"],
            "origem_comprimento": comprimentos[c["id"]]["origem"],
            "corrente_a": d["load"]["current_a"],
            "secao_mm2": d["conductor"]["secao_mm2"],
            "governante": d["conductor"]["governante"],
            "queda_pct": d["conductor"]["dv_pct"],
            "disjuntor_a": d["protection"]["disjuntor"]["IN"],
            "dr": bool(d["protection"]["dr"]["requer_DR"])})
    atende = (bool(divisao["ATENDE"]) and calculo["ok"] is True
              and len(resumo) == len(divisao["circuitos"]))
    return {"circuits": calculo, "resumo": resumo, "comprimentos": comprimentos,
            "erros": list(calculo["errors"]), "ATENDE": atende}


def dimensionar_da_planta(divisao, leitura, criterios):
    """Junta comprimento e dimensionamento: `criterios["comprimentos_m"]`
    (declarado, por circuito) vence a estimativa pela planta; o que faltar e'
    estimado com `criterios["tracado"]` e a posicao do quadro lida."""
    declarados = criterios["comprimentos_m"] if "comprimentos_m" in criterios else {}
    comprimentos = {cid: {"comprimento_m": v, "origem": "declarado"}
                    for cid, v in declarados.items()}
    erros = []
    if any(c["id"] not in comprimentos for c in divisao["circuitos"]):
        est = comprimentos_pela_planta(
            divisao, leitura["geometria"], leitura["quadro_m"],
            criterios["tracado"] if "tracado" in criterios else None)
        erros = est["erros"]
        for cid, dado in est["comprimentos"].items():
            if cid not in comprimentos:
                comprimentos[cid] = dado
    resultado = dimensionar(divisao, criterios["instalacao"], comprimentos)
    resultado["erros"] = erros + resultado["erros"]
    return resultado


def relatorio_dimensionamento_pt(resultado):
    linhas = ["DIMENSIONAMENTO DOS CIRCUITOS",
              "%-5s %-9s %8s %-10s %8s %7s %-16s %7s %6s %-3s" % (
                  "circ", "local", "L (m)", "origem", "IB (A)", "mm2", "governa",
                  "dV (%)", "DJ (A)", "DR")]
    for r in resultado["resumo"]:
        linhas.append("%-5s %-9s %8.1f %-10s %8.2f %7.1f %-16s %7.2f %6d %-3s" % (
            r["id"], r["local"], r["comprimento_m"],
            "declarado" if r["origem_comprimento"] == "declarado" else "estimado",
            r["corrente_a"], r["secao_mm2"], r["governante"], r["queda_pct"],
            r["disjuntor_a"], "sim" if r["dr"] else "nao"))
    for e in resultado["erros"]:
        linhas.append("ERRO %s%s" % (e["code"], "".join(
            " %s=%s" % (k, e[k]) for k in ("campo", "circuito", "design_id", "field") if k in e)))
    linhas.append("ATENDE: %s" % resultado["ATENDE"])
    return "\n".join(linhas)


def desenhos(resultado, pasta, entrada=None):
    """Unifilar e quadro de cargas em SVG pelo emissor residencial que ja
    existe. Sem dimensionamento nao ha desenho (devolve o motivo). `entrada`
    (saida de demanda_e_entrada) leva demanda e padrao de entrada ao desenho;
    sem ela o emissor escreve que estao a confirmar."""
    if resultado["circuits"] is None:
        return {"files": [], "skipped": {"unifilar.svg": "circuitos_nao_dimensionados",
                                         "quadro-cargas.svg": "circuitos_nao_dimensionados"}}
    import desenho_eletrico_residencial as DER

    fonte = {"circuits": resultado["circuits"]}
    if entrada is not None:
        fonte["calculation"] = entrada["calculation"]
        fonte["service_entry"] = entrada["service_entry"]
    return DER.gerar_desenhos_residenciais(fonte, pasta)


GRUPO_AQUECIMENTO = "aquecimento"
GRUPO_MOTOR = "motor"
GRUPO_NENHUM = "nenhum"
GRUPOS_DE_DEMANDA = (GRUPO_AQUECIMENTO, GRUPO_MOTOR, GRUPO_NENHUM)
LISTAS_DE_DEMANDA = ("motores", "iluminacao_especial")
CAMPOS_REDE = ("location_factor", "voltage_system", "supply_type", "network_kind")


def demanda_e_entrada(previsao, divisao, criterios):
    """Demanda e padrao de entrada pelos motores da distribuidora.
    `criterios` traz `rede` = {location_factor, voltage_system, supply_type,
    network_kind}, `instalacao.fator_potencia` (para a carga instalada em kW),
    `equipamentos[].grupo_demanda` ("aquecimento", "motor" ou "nenhum"),
    `demanda` = {motores: [...], iluminacao_especial: [...]} no contrato do
    calculador (listas vazias se nao ha) e, se preciso,
    `demanda.modulo_por_tipo` = {tipo de ambiente: modulo}. Devolve {rooms, heating,
    installed_load_kw, calculation, service_entry, erros, ATENDE}."""
    import demanda_residencial_enel as DE
    import entrada_enel_bt as EE

    vazio = {"rooms": None, "heating": [], "installed_load_kw": None, "calculation": {},
             "service_entry": {"ok": False, "entry": None, "errors": [], "warnings": []}}
    erros = []
    rede = criterios["rede"] if "rede" in criterios else None
    for campo in CAMPOS_REDE:
        if not isinstance(rede, dict) or campo not in rede:
            erros.append({"code": "criterio_ausente", "campo": "rede.%s" % campo,
                          "detail": "dado da rede declarado por quem projeta"})
    if "instalacao" not in criterios:
        erros.append({"code": "criterio_ausente", "campo": "instalacao",
                      "detail": "os fatores de potencia levam a carga instalada a kW"})
    else:
        erros += [e for e in _erros_da_instalacao(criterios["instalacao"])
                  if e["campo"].startswith("instalacao.fator_potencia")]
    if divisao["quadro"] is None:
        erros.append({"code": "divisao_nao_feita", "campo": "divisao",
                      "detail": "sem circuitos nao ha carga instalada"})
    dem = criterios["demanda"] if "demanda" in criterios else None
    for lista in LISTAS_DE_DEMANDA:
        if not isinstance(dem, dict) or lista not in dem or not isinstance(dem[lista], list):
            erros.append({"code": "criterio_ausente", "campo": "demanda.%s" % lista,
                          "detail": "lista declarada no contrato do calculador de demanda "
                                    "(vazia se nao ha)"})
    if erros:
        return dict(vazio, erros=erros, ATENDE=False)

    declarado = dem["modulo_por_tipo"] if "modulo_por_tipo" in dem else {}
    modulos = tuple(DE._ROOM_NAMES)
    rooms = {m: 0 for m in modulos}
    for amb in previsao["ambientes"]:
        tipo = amb["tipo"]
        if tipo in declarado:
            modulo = declarado[tipo]
        elif tipo in modulos:
            modulo = tipo
        else:
            modulo = None
        if modulo not in modulos:
            erros.append({"code": "tipo_sem_modulo_de_demanda",
                          "campo": "demanda.modulo_por_tipo", "ambiente": amb["nome"],
                          "tipo": tipo, "modulos": list(modulos),
                          "detail": "declare em demanda.modulo_por_tipo o modulo de demanda "
                                    "deste tipo de ambiente"})
            continue
        rooms[modulo] += 1

    por_potencia = {}
    for eq in criterios["equipamentos"]:
        if not isinstance(eq, dict) or "grupo_demanda" not in eq:
            erros.append({"code": "equipamento_sem_grupo_de_demanda", "campo": "equipamentos",
                          "equipamento": eq["nome"] if isinstance(eq, dict) and "nome" in eq
                          else None,
                          "detail": "declare grupo_demanda no equipamento"})
        elif eq["grupo_demanda"] not in GRUPOS_DE_DEMANDA:
            erros.append({"code": "grupo_de_demanda_desconhecido", "campo": "equipamentos",
                          "equipamento": eq["nome"], "grupo": eq["grupo_demanda"],
                          "detail": "grupo_demanda e' um de: %s" % ", ".join(GRUPOS_DE_DEMANDA)})
        elif eq["grupo_demanda"] == GRUPO_MOTOR:
            if not dem["motores"]:
                erros.append({"code": "motor_sem_descricao_na_demanda",
                              "campo": "demanda.motores", "equipamento": eq["nome"],
                              "detail": "equipamento declarado como motor, mas "
                                        "demanda.motores esta vazia"})
        elif eq["grupo_demanda"] == GRUPO_AQUECIMENTO:  # resistivo: kVA = kW
            kw = float(eq["potencia_va"]) / 1000.0
            por_potencia[kw] = por_potencia[kw] + 1 if kw in por_potencia else 1
    heating = [{"quantity": n, "power_kw": kw} for kw, n in sorted(por_potencia.items())]

    fps = criterios["instalacao"]["fator_potencia"]
    instalada_kw = sum(c["potencia_va"] * fps[c["classe"]]
                       for c in divisao["circuitos"]) / 1000.0
    if erros:
        return dict(vazio, rooms=rooms, heating=heating, installed_load_kw=instalada_kw,
                    erros=erros, ATENDE=False)

    demanda = DE.calculate_residential_demand({
        "network": {"location_factor": rede["location_factor"]}, "rooms": rooms,
        "loads": {"heating": heating, "motors": list(dem["motores"]),
                  "special_lighting": list(dem["iluminacao_especial"])}})
    erros += list(demanda["errors"])
    entrada = dict(vazio["service_entry"])
    if rede["network_kind"] != "aerea":
        erros.append({"code": "rede_fora_das_tabelas", "campo": "rede.network_kind",
                      "detail": "as tabelas de padrao de entrada do motor sao de rede aerea"})
    elif demanda["ok"]:
        entrada = EE.select_enel_bt_entry(voltage_system=rede["voltage_system"],
                                          supply_type=rede["supply_type"],
                                          installed_load_kw=instalada_kw)
        erros += list(entrada["errors"])
        if entrada["ok"]:
            # o ramal da linha escolhida diz quantas fases chegam ("2x10 (10)")
            fases_do_ramal = int(entrada["entry"]["connection_conductors"].split("x")[0])
            if fases_do_ramal != criterios["n_fases"]:
                erros.append({"code": "fases_do_quadro_diferem_do_fornecimento",
                              "campo": "n_fases", "n_fases_quadro": criterios["n_fases"],
                              "n_fases_ramal": fases_do_ramal,
                              "detail": "os circuitos foram repartidos num numero de fases "
                                        "que o fornecimento escolhido nao entrega"})
    calculo = dict(demanda["calculation"])
    calculo["demand_errors"] = list(demanda["errors"])
    return {"rooms": rooms, "heating": heating, "installed_load_kw": instalada_kw,
            "calculation": calculo, "service_entry": entrada, "erros": erros,
            "ATENDE": bool(divisao["ATENDE"]) and not erros and entrada["ok"] is True}


def relatorio_entrada_pt(resultado):
    linhas = ["DEMANDA E PADRAO DE ENTRADA"]
    if resultado["rooms"] is not None:
        linhas.append("modulos: " + ", ".join(
            "%s=%d" % par for par in resultado["rooms"].items()))
    if resultado["installed_load_kw"] is not None:
        linhas.append("carga instalada: %.2f kW" % resultado["installed_load_kw"])
    if "demand" in resultado["calculation"]:
        linhas.append("demanda: %.2f kVA" % resultado["calculation"]["demand"]["final_kva"])
    entrada = resultado["service_entry"]["entry"]
    if entrada is not None:
        linhas.append("padrao de entrada: linha %s, tipo %s, disjuntor %s A, ramal %s" % (
            entrada["row"], entrada["supply_type"], entrada["breaker_a"],
            entrada["connection_conductors"]))
    for e in resultado["erros"]:
        linhas.append("ERRO %s%s" % (e["code"], "".join(
            " %s=%s" % (k, e[k]) for k in ("campo", "ambiente", "tipo", "equipamento")
            if k in e)))
    linhas.append("ATENDE: %s" % resultado["ATENDE"])
    return "\n".join(linhas)
