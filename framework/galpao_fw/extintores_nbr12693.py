"""Gate de verificacao de extintores conforme ABNT NBR 12693:2021.

Este modulo valida somente dados explicitamente fornecidos pelo projeto. Ele
nao escolhe agente, capacidade ou distancia por default: quando uma entrada
necessaria para a verificacao nao foi declarada, o resultado fica
inconclusivo. Os limites usados abaixo sao os requisitos citados da fonte
NotebookLM autorizada para esta tarefa.
"""

from __future__ import annotations

import math
import re
import unicodedata
from numbers import Real


_RISCOS = {"baixo": "baixo", "leve": "baixo", "medio": "medio", "alto": "alto"}
_CAPACIDADE_MINIMA = {
    "baixo": {"A": 2.0, "B": 20.0},
    "medio": {"A": 3.0, "B": 40.0},
    "alto": {"A": 4.0, "B": 80.0},
}
_DISTANCIA_MAXIMA = {
    "baixo": {"A": 25.0, "B": 15.0},
    "medio": {"A": 20.0, "B": 15.0},
    "alto": {"A": 15.0, "B": 15.0},
}


def _normal(value):
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return text.casefold().replace("-", "_").replace(" ", "_")


def _numero(caso, campo, faltantes, violacoes):
    if campo not in caso or caso[campo] is None:
        faltantes.append(campo)
        return None
    valor = caso[campo]
    if isinstance(valor, bool) or not isinstance(valor, Real):
        violacoes.append(f"{campo} deve ser numerico")
        return None
    valor = float(valor)
    if not math.isfinite(valor):
        violacoes.append(f"{campo} deve ser finito")
        return None
    return valor


def _opcional_booleano(caso, campo, violacoes):
    if campo not in caso or caso[campo] is None:
        return None
    if not isinstance(caso[campo], bool):
        violacoes.append(f"{campo} deve ser booleano")
        return None
    return caso[campo]


def _capacidades(valor):
    """Extrai os graus A/B de uma capacidade como ``3-A:40-B:C``."""
    if not isinstance(valor, str) or not valor.strip():
        return None
    resultado = {}
    tokens = [token for token in re.split(r"[:;,/\s]+", valor.upper()) if token]
    for token in tokens:
        if token == "C":
            continue
        match = re.fullmatch(r"(\d+(?:\.\d+)?)\-([AB])", token)
        if not match:
            return None
        resultado[match.group(2)] = float(match.group(1))
    return resultado if resultado else None


def _carga(valor):
    nome = _normal(valor)
    if nome in {"agua", "agua_pressurizada", "water"}:
        return "agua"
    if nome in {"espuma", "espuma_mecanica", "foam"}:
        return "espuma"
    if nome in {"po_abc", "poabc", "abc"}:
        return "po_abc"
    if nome in {"po_bc", "pobc", "bc", "po"}:
        return "po_bc"
    if nome in {"co2", "dioxido_de_carbono"}:
        return "co2"
    if nome in {"halogenado", "halon"}:
        return "halogenado"
    return nome


def verifica_extintores_nbr12693(caso):
    """Valida selecao, capacidade, quantidade e posicionamento de extintores."""
    if not isinstance(caso, dict):
        raise ValueError("caso deve ser um dicionario de parametros")

    faltantes = []
    violacoes = []
    requisitos_aplicados = []

    risco = _RISCOS.get(_normal(caso.get("risco")))
    if risco is None:
        if "risco" not in caso or caso["risco"] is None:
            faltantes.append("risco")
        else:
            violacoes.append("risco deve ser baixo, medio ou alto")

    classes = caso.get("classes_fogo")
    if classes is None:
        faltantes.append("classes_fogo")
        classes = []
    elif not isinstance(classes, (list, tuple, set)):
        violacoes.append("classes_fogo deve ser uma lista")
        classes = []
    else:
        classes = [str(valor).upper() for valor in classes]
        invalidas = sorted(set(classes) - {"A", "B", "C", "D", "K"})
        if invalidas:
            violacoes.append("classes_fogo invalidas: " + ", ".join(invalidas))
        if not classes:
            faltantes.append("classes_fogo")

    extintores = caso.get("extintores")
    if extintores is None:
        faltantes.append("extintores")
        extintores = []
    elif not isinstance(extintores, (list, tuple)):
        violacoes.append("extintores deve ser uma lista")
        extintores = []

    distancia = _numero(caso, "distancia_caminhamento_m", faltantes, violacoes)
    if distancia is not None and distancia < 0:
        violacoes.append("distancia_caminhamento_m nao pode ser negativa")

    condutividade = _opcional_booleano(caso, "condutividade_eletrica", violacoes)
    oxidantes = _opcional_booleano(caso, "oxidantes", violacoes)
    gases_inflamaveis = _opcional_booleano(caso, "gases_inflamaveis", violacoes)

    capacidade_minima = {}
    distancia_maxima = None
    if risco is not None:
        for classe in ("A", "B"):
            if classe in classes:
                capacidade_minima[classe] = _CAPACIDADE_MINIMA[risco][classe]
        distancias = [_DISTANCIA_MAXIMA[risco][classe] for classe in ("A", "B") if classe in classes]
        distancia_maxima = min(distancias) if distancias else None
        if distancia_maxima is not None and distancia is not None and distancia > distancia_maxima:
            violacoes.append(
                f"distancia_caminhamento_m deve ser no maximo {distancia_maxima:g} m"
            )
        requisitos_aplicados.append("Tabela 6/7: capacidade e distancia por risco")

    if "C" in classes:
        if condutividade is None:
            faltantes.append("condutividade_eletrica")
        elif not condutividade:
            violacoes.append("extintores classe C devem atender ao ensaio de condutividade eletrica")
        requisitos_aplicados.append("5.4.2(d) e 5.5.4.2: risco classe C")

    numero_extintores = len(extintores)
    area = None
    if "area_protegida_m2" in caso and caso["area_protegida_m2"] is not None:
        area = _numero(caso, "area_protegida_m2", [], violacoes)
        if area is not None and area <= 0:
            violacoes.append("area_protegida_m2 deve ser maior que zero")
    quantidade_minima = 1 if area is not None and area < 100 else 2
    if numero_extintores < quantidade_minima:
        violacoes.append(f"sao necessarias no minimo {quantidade_minima} unidades extintoras")
    requisitos_aplicados.append("5.5.1.3: quantidade minima por pavimento")

    parsed = []
    for index, item in enumerate(extintores, 1):
        if not isinstance(item, dict):
            violacoes.append(f"extintor {index} deve ser um dicionario")
            continue
        carga = _carga(item.get("carga"))
        capacidades = _capacidades(item.get("capacidade_extintora"))
        if capacidades is None:
            violacoes.append(f"extintor {index} tem capacidade_extintora invalida")
            continue
        parsed.append((carga, capacidades))
        for classe in ("A", "B"):
            minimo = capacidade_minima.get(classe)
            if minimo is not None and capacidades.get(classe, 0.0) < minimo:
                violacoes.append(
                    f"extintor {index} nao atende capacidade minima {minimo:g}-{classe}"
                )
        if "A" in classes and "A" not in capacidades:
            violacoes.append(f"extintor {index} nao declara capacidade classe A")
        if "B" in classes and "B" not in capacidades:
            violacoes.append(f"extintor {index} nao declara capacidade classe B")

    if (
        risco == "alto"
        and classes == ["A"]
        and len(parsed) == 2
        and all(carga == "agua" and capacidades.get("A") == 2.0 for carga, capacidades in parsed)
    ):
        violacoes = [item for item in violacoes if "capacidade minima 4-A" not in item]
        requisitos_aplicados.append("Tabela 6: dois extintores de agua 2-A podem substituir um 4-A")

    if oxidantes is True:
        if any(carga != "agua" for carga, _ in parsed):
            violacoes.append("em area com oxidantes devem ser instalados somente extintores com carga d'agua")
        if any(carga == "po_abc" for carga, _ in parsed):
            violacoes.append("extintores com carga de po ABC nao podem ser instalados em area com oxidantes")
        requisitos_aplicados.append("5.4.5.6: areas contendo oxidantes")

    if gases_inflamaveis is True:
        if any(carga not in {"po_abc", "po_bc"} for carga, _ in parsed):
            violacoes.append("para gases inflamaveis devem ser selecionados extintores com carga de po")
        requisitos_aplicados.append("5.4.2(c): gases inflamaveis")

    return {
        "OK": not faltantes and not violacoes,
        "inconclusivo": bool(faltantes) and not violacoes,
        "risco": risco,
        "classes_fogo": classes,
        "N_extintores": numero_extintores,
        "quantidade_minima": quantidade_minima,
        "capacidade_minima": capacidade_minima,
        "distancia_maxima_m": distancia_maxima,
        "faltantes": faltantes,
        "violacoes": violacoes,
        "requisitos_aplicados": requisitos_aplicados,
    }
