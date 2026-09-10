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

# Tolerancia RELATIVA da costura programa x layout (G78). E' a mesma que
# `arquitetura_residencial` usa para conferir area declarada x largura x
# comprimento e que `bim_casa_residencial` usa no rotulo x geometria: uma so
# tolerancia para a mesma pergunta, em qualquer disciplina que a faca.
TOL_AREA_REL = 1e-3


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


def conferir_areas_programa_layout(ambientes, rooms, tol_rel=TOL_AREA_REL):
    """Cross-check G78: area do PROGRAMA x area do LAYOUT, por ambiente.

    As duas declaracoes descrevem a MESMA casa: o programa declara area (de
    largura x comprimento, ou area direta) e o layout declara width x depth do
    mesmo comodo. Sem este cruzamento as duas envelhecem e passam a discordar
    em silencio - o anti-padrao que este repo persegue por nome.

    `ambientes`: lista do resultado de `arquitetura_residencial.rodar`
    (cada item com nome/area_m2/geometria_ok). `rooms`: lista de comodos
    validados (id/name/width_m/depth_m). Ambientes sem geometria valida sao
    pulados sem erro: nao ha numero conferivel, e inventar um aqui seria
    repor o dado recusado la.

    Devolve {"ok", "erros", "por_ambiente"}. `por_ambiente` traz os dois
    numeros por comodo (o detalhamento entregue, nunca so o veredito).
    """
    import math as _math

    por_nome = {}
    for comodo in rooms or []:
        if isinstance(comodo, dict):
            chave = comodo.get("id") or comodo.get("name")
            if isinstance(chave, str):
                por_nome[chave] = comodo
    erros = []
    por_ambiente = []
    for ambiente in ambientes or []:
        if not isinstance(ambiente, dict):
            continue
        nome = ambiente.get("nome")
        if not ambiente.get("geometria_ok"):
            continue
        comodo = por_nome.get(nome)
        if comodo is None:
            erros.append(erro(
                "ambiente_ausente_no_layout",
                ambiente=nome,
                detail="ambiente do programa sem retangulo no layout"))
            continue
        largura = comodo.get("width_m")
        profundidade = comodo.get("depth_m")
        if not (finito_positivo(largura) and finito_positivo(profundidade)):
            continue
        area_layout = float(largura) * float(profundidade)
        area_programa = ambiente.get("area_m2")
        registro = {"ambiente": nome,
                    "area_programa_m2": area_programa,
                    "area_layout_m2": round(area_layout, 4)}
        por_ambiente.append(registro)
        if not isinstance(area_programa, (int, float)):
            continue
        if not _math.isclose(area_layout, float(area_programa),
                             rel_tol=tol_rel):
            erros.append(erro(
                "area_do_layout_diverge_do_programa",
                ambiente=nome,
                area_programa_m2=float(area_programa),
                area_layout_m2=round(area_layout, 4),
                detail="o retangulo do layout nao reproduz a area do programa "
                       "de arquitetura (tolerancia relativa %s)" % tol_rel))
    return {"ok": not erros, "erros": erros, "por_ambiente": por_ambiente}


def envolvente(comodos) -> dict:
    """Retangulo envolvente dos comodos declarados (m). So para enquadramento."""
    return {
        "x_min": min(c["x_m"] for c in comodos),
        "y_min": min(c["y_m"] for c in comodos),
        "x_max": max(c["x_m"] + c["width_m"] for c in comodos),
        "y_max": max(c["y_m"] + c["depth_m"] for c in comodos),
    }
