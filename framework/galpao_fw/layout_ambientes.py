"""Primitiva de LAYOUT DE AMBIENTES: retangulos de comodo em planta.

Nasceu dentro de `layout_eletrico_residencial`, que precisava dos comodos para
posicionar pontos de circuito. O BIM da arquitetura (`bim_casa_residencial`)
precisa exatamente da mesma validacao - retangulo finito, id unico, nenhum par
se sobrepondo. Duas copias da mesma regra e' o anti-padrao que este projeto
persegue (uma envelhece e as duas passam a discordar em silencio), entao a regra
mora aqui e as duas disciplinas a importam.

Nenhuma funcao deste modulo desenha, emite arquivo ou inventa posicao: layout
nao declarado e' ausencia de dado, nao um layout vazio.

Unidades: metro.
"""

from __future__ import annotations

import math


ROOM_FIELDS = ("id", "name", "x_m", "y_m", "width_m", "depth_m")


def erro(code, **context):
    registro = {"code": code}
    if context:
        registro.update(context)
    return registro


def finito(valor):
    return (not isinstance(valor, bool) and isinstance(valor, (int, float))
            and math.isfinite(float(valor)))


def finito_positivo(valor):
    return finito(valor) and float(valor) > 0.0


def texto_nao_vazio(valor):
    return type(valor) is str and bool(valor.strip())


def validar_comodos(layout, errors):
    """Valida `layout['rooms']` e devolve {id: comodo}. Acumula em `errors`."""
    brutos = layout.get("rooms")
    if not isinstance(brutos, list) or not brutos:
        errors.append(erro("missing_layout_field", field="rooms",
                           detail="layout.rooms deve ser uma lista nao vazia"))
        return {}
    comodos: dict[str, dict] = {}
    for indice, comodo in enumerate(brutos):
        if not isinstance(comodo, dict):
            errors.append(erro("invalid_layout_value", field="rooms", index=indice))
            continue
        faltando = [campo for campo in ROOM_FIELDS if campo not in comodo]
        if faltando:
            errors.append(erro("missing_layout_field", field="rooms",
                               index=indice, missing=sorted(faltando)))
            continue
        room_id = comodo["id"]
        if not texto_nao_vazio(room_id) or not texto_nao_vazio(comodo["name"]):
            errors.append(erro("invalid_layout_value", field="rooms.id", index=indice))
            continue
        if not (finito(comodo["x_m"]) and finito(comodo["y_m"])
                and finito_positivo(comodo["width_m"])
                and finito_positivo(comodo["depth_m"])):
            errors.append(erro("invalid_layout_value", field="rooms.geometry",
                               index=indice, room=room_id))
            continue
        if room_id in comodos:
            errors.append(erro("duplicate_layout_room", room=room_id))
            continue
        comodos[room_id] = {campo: comodo[campo] for campo in ROOM_FIELDS}
    rejeitar_sobreposicao(comodos, errors)
    return comodos


def rejeitar_sobreposicao(comodos, errors):
    """Dois comodos nao podem ocupar a mesma area: seria planta impossivel."""
    itens = list(comodos.values())
    for i, a in enumerate(itens):
        for b in itens[i + 1:]:
            sobra_x = (min(a["x_m"] + a["width_m"], b["x_m"] + b["width_m"])
                       - max(a["x_m"], b["x_m"]))
            sobra_y = (min(a["y_m"] + a["depth_m"], b["y_m"] + b["depth_m"])
                       - max(a["y_m"], b["y_m"]))
            if sobra_x > 1e-9 and sobra_y > 1e-9:
                errors.append(erro("overlapping_layout_rooms",
                                   rooms=sorted([a["id"], b["id"]])))


def dentro(comodo, x, y):
    return (comodo["x_m"] - 1e-9 <= x <= comodo["x_m"] + comodo["width_m"] + 1e-9
            and comodo["y_m"] - 1e-9 <= y <= comodo["y_m"] + comodo["depth_m"] + 1e-9)


def envolvente(comodos) -> dict:
    """Retangulo envolvente dos comodos declarados (m). So para enquadramento."""
    return {
        "x_min": min(c["x_m"] for c in comodos),
        "y_min": min(c["y_m"] for c in comodos),
        "x_max": max(c["x_m"] + c["width_m"] for c in comodos),
        "y_max": max(c["y_m"] + c["depth_m"] for c in comodos),
    }
