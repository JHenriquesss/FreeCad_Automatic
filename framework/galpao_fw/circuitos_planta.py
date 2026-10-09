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
# O que este passo NAO faz: comprimento de circuito, secao de condutor,
# disjuntor, demanda e entrada. O quadro aqui e' de CARGA INSTALADA.
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

