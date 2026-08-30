# ============================================================================
# casa_residencial.py - O QUE ESTE ADAPTADOR FAZ
# Adaptador REAL de casa residencial do Project Loop. Ao contrario da fixture
# casa_residencial_sintetica (que declara tres disciplinas e nao calcula
# nenhuma), aqui cada disciplina declarada e' efetivamente dimensionada:
#
#   arquitetura -> arquitetura_residencial: programa de ambientes com geometria
#                  conferida (rotulo x geometria) + previsao de carga da
#                  NBR 5410:2004 9.5.2 (iluminacao e pontos de tomada);
#   eletrico    -> residencial_eletrica (verticais das Fases 6A/6B: demanda
#                  Enel, padrao de entrada, condutores e protecoes NBR 5410),
#                  MAIS a conferencia ponto declarado x minimo normativo;
#   hidraulica  -> hidraulica_residencial: agua fria (NBR 5626:2020), esgoto e
#                  ventilacao (NBR 8160) e pluvial (NBR 10844).
#
# A CONFERENCIA e' a costura que faltava: a vertical eletrica exige que o
# projetista declare ponto a ponto e nunca soube dizer se o que ele declarou
# atende ao minimo da norma para aquela planta. Aqui a planta (arquitetura) e a
# instalacao (eletrico) se olham: ponto faltando REPROVA, e ponto que aponta
# para um ambiente inexistente tambem (um filtro de nome morto devolveria zero
# pontos em silencio).
#
# Nenhuma disciplina e' marcada 'passed': aprovacao para obra continua sendo
# decisao de responsavel tecnico. O adaptador nao importa nem chama
# galpao_turnkey.
# ============================================================================
"""Adaptador residencial real: arquitetura + eletrico + hidraulica, com a
conferencia NBR 5410 9.5.2 entre a planta e a instalacao declarada."""

from __future__ import annotations

import copy
import unicodedata
from typing import Any

import arquitetura_residencial as arq
import hidraulica_residencial as hid
from residencial_eletrica import run_residential_electrical


ADAPTER_NAME = "casa-residencial"
DISCIPLINES = ("arquitetura", "eletrico", "hidraulica")
DELIVERABLES = ("report", "drawings")
SCHEMA = "freecad-automatic/residential-house-result"
SCHEMA_VERSION = 1
# 'lighting' conta para o ponto de luz de 9.5.2.1.1; 'tug' conta para os pontos
# de tomada de 9.5.2.2.1. 'tue' e' ponto de utilizacao dedicado (9.5.3.1) e nao
# substitui uma TUG.
KIND_ILUMINACAO = "lighting"
KIND_TOMADA = "tug"


def _erro(code: str, detail: str, **ctx: Any) -> dict[str, Any]:
    registro = {"code": code, "detail": detail}
    if ctx:
        registro.update(ctx)
    return registro


def _chave_ambiente(nome: Any) -> str:
    """Normaliza o nome do ambiente para casar planta x circuito.

    Acento, caixa e espaco extra nao podem transformar 'Área de serviço' e
    'Area de Servico' em ambientes diferentes - esse e' o filtro de nome morto
    que ja custou um PR neste repositorio."""
    texto = unicodedata.normalize("NFKD", str(nome or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.strip().casefold().split())


def conferir_geometria_layout(resultado_arquitetura, circuitos):
    """Confere a geometria do layout eletrico contra o programa de arquitetura.

    ROTULO x GEOMETRIA entre disciplinas: o programa declara area e perimetro
    do ambiente; o layout eletrico declara width_m x depth_m do MESMO ambiente.
    Se os dois discordam, a planta desenhada nao e' a planta calculada - e o
    numero de tomadas foi tirado de uma e conferido contra a outra."""
    layout = (circuitos or {}).get("layout")
    comodos = (layout or {}).get("rooms")
    if not isinstance(comodos, list) or not comodos:
        return {"declarado": False, "ok": None, "erros": [], "por_ambiente": []}

    por_chave = {}
    for comodo in comodos:
        if isinstance(comodo, dict):
            por_chave[_chave_ambiente(comodo.get("id") or comodo.get("name"))] = comodo
    erros = []
    por_ambiente = []
    for ambiente in resultado_arquitetura.get("ambientes", []):
        if not ambiente.get("geometria_ok"):
            continue
        comodo = por_chave.get(_chave_ambiente(ambiente["nome"]))
        if comodo is None:
            erros.append(_erro(
                "ambiente_ausente_no_layout",
                "ambiente do programa nao aparece no layout eletrico",
                ambiente=ambiente["nome"]))
            continue
        largura = comodo.get("width_m")
        profundidade = comodo.get("depth_m")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                   for v in (largura, profundidade)):
            continue
        area_layout = float(largura) * float(profundidade)
        registro = {"ambiente": ambiente["nome"],
                    "area_programa_m2": ambiente["area_m2"],
                    "area_layout_m2": round(area_layout, 4)}
        por_ambiente.append(registro)
        if abs(area_layout - ambiente["area_m2"]) > 1e-3 * max(
                area_layout, ambiente["area_m2"], 1.0):
            erros.append(_erro(
                "area_do_layout_diverge_do_programa",
                "o comodo desenhado no layout eletrico tem area diferente da "
                "do programa de arquitetura",
                ambiente=ambiente["nome"],
                area_programa_m2=ambiente["area_m2"],
                area_layout_m2=round(area_layout, 4)))
    return {"declarado": True, "ok": not erros, "erros": erros,
            "por_ambiente": por_ambiente}


def conferir_previsao_nbr5410(resultado_arquitetura, circuitos):
    """Confere os pontos declarados contra o minimo da NBR 5410 9.5.2.

    resultado_arquitetura: saida de arquitetura_residencial.rodar.
    circuitos: bloco turnkey.eletrico.circuits (com 'points').
    Retorna {ok, por_ambiente, erros, avisos, totais}."""
    ambientes = [a for a in resultado_arquitetura.get("ambientes", [])
                 if a.get("geometria_ok")]
    pontos = (circuitos or {}).get("points")
    pontos = pontos if isinstance(pontos, list) else []

    por_chave = {_chave_ambiente(a["nome"]): a for a in ambientes}
    contagem = {chave: {KIND_ILUMINACAO: 0, KIND_TOMADA: 0, "va_tug": 0.0,
                        "va_lighting": 0.0}
                for chave in por_chave}
    erros = []
    avisos = []
    orfaos = {}
    for indice, ponto in enumerate(pontos):
        if not isinstance(ponto, dict):
            continue
        chave = _chave_ambiente(ponto.get("room"))
        if chave not in contagem:
            # ponto que aponta para um ambiente inexistente no programa: sem
            # este erro a conferencia devolveria zero pontos em silencio
            orfaos.setdefault(chave or "(vazio)", []).append(
                ponto.get("id") or "ponto[%d]" % indice)
            continue
        kind = ponto.get("kind")
        if kind in (KIND_ILUMINACAO, KIND_TOMADA):
            contagem[chave][kind] += 1
        potencia = ponto.get("power_va")
        if isinstance(potencia, (int, float)) and not isinstance(potencia, bool):
            if kind == KIND_TOMADA:
                contagem[chave]["va_tug"] += float(potencia)
            elif kind == KIND_ILUMINACAO:
                contagem[chave]["va_lighting"] += float(potencia)

    for chave, ids in sorted(orfaos.items()):
        erros.append(_erro(
            "ambiente_desconhecido_no_circuito",
            "ponto declarado em ambiente que nao existe no programa de "
            "arquitetura", room=chave, points=ids))

    por_ambiente = []
    for ambiente in ambientes:
        chave = _chave_ambiente(ambiente["nome"])
        atual = contagem[chave]
        registro = {
            "ambiente": ambiente["nome"], "tipo": ambiente["tipo"],
            "criterio_tomadas": ambiente["criterio_tomadas"],
            "tomadas_minimo": ambiente["n_tomadas_min"],
            "tomadas_declaradas": atual[KIND_TOMADA],
            "pontos_luz_minimo": ambiente["n_pontos_luz_min"],
            "pontos_luz_declarados": atual[KIND_ILUMINACAO],
            "carga_tomadas_minima_va": ambiente["carga_tomadas_va"],
            "carga_tomadas_declarada_va": round(atual["va_tug"], 2),
            "carga_iluminacao_minima_va": ambiente["carga_iluminacao_va"],
            "carga_iluminacao_declarada_va": round(atual["va_lighting"], 2),
        }
        if atual[KIND_TOMADA] < ambiente["n_tomadas_min"]:
            erros.append(_erro(
                "tomadas_abaixo_do_minimo_nbr5410",
                "ambiente com menos pontos de tomada que o minimo de "
                "9.5.2.2.1", ambiente=ambiente["nome"],
                criterio=ambiente["criterio_tomadas"],
                minimo=ambiente["n_tomadas_min"],
                declarado=atual[KIND_TOMADA]))
        if atual[KIND_ILUMINACAO] < ambiente["n_pontos_luz_min"]:
            erros.append(_erro(
                "ponto_de_luz_ausente_nbr5410",
                "9.5.2.1.1 exige ao menos um ponto de luz fixo no teto por "
                "comodo", ambiente=ambiente["nome"],
                minimo=ambiente["n_pontos_luz_min"],
                declarado=atual[KIND_ILUMINACAO]))
        if (atual[KIND_TOMADA] >= ambiente["n_tomadas_min"]
                and atual["va_tug"] + 1e-6 < ambiente["carga_tomadas_va"]):
            erros.append(_erro(
                "carga_de_tomadas_abaixo_do_minimo_nbr5410",
                "potencia declarada menor que o minimo de 9.5.2.2.2",
                ambiente=ambiente["nome"],
                minimo_va=ambiente["carga_tomadas_va"],
                declarado_va=round(atual["va_tug"], 2)))
        if (atual[KIND_ILUMINACAO] >= ambiente["n_pontos_luz_min"]
                and atual["va_lighting"] + 1e-6 < ambiente["carga_iluminacao_va"]):
            erros.append(_erro(
                "carga_de_iluminacao_abaixo_do_minimo_nbr5410",
                "potencia declarada menor que o minimo de 9.5.2.1.2",
                ambiente=ambiente["nome"],
                minimo_va=ambiente["carga_iluminacao_va"],
                declarado_va=round(atual["va_lighting"], 2)))
        por_ambiente.append(registro)

    if not pontos:
        avisos.append(_erro("conferencia_sem_pontos_declarados",
                            "nenhum ponto de circuito declarado para conferir"))
    totais = {
        "tomadas_minimo": sum(r["tomadas_minimo"] for r in por_ambiente),
        "tomadas_declaradas": sum(r["tomadas_declaradas"] for r in por_ambiente),
        "pontos_luz_minimo": sum(r["pontos_luz_minimo"] for r in por_ambiente),
        "pontos_luz_declarados": sum(r["pontos_luz_declarados"]
                                     for r in por_ambiente),
        "pontos_orfaos": sum(len(ids) for ids in orfaos.values()),
    }
    return {"ok": not erros, "por_ambiente": por_ambiente, "erros": erros,
            "avisos": avisos, "totais": totais,
            "fonte": "ABNT NBR 5410:2004 9.5.2"}


def _registro_arquitetura(payload):
    if not isinstance(payload, dict):
        return arq_registro_bloqueado(_erro(
            "invalid_architecture_payload",
            "turnkey.arquitetura deve ser um objeto JSON")), None
    try:
        resultado = arq.rodar(payload)
    except (TypeError, ValueError) as exc:
        return arq_registro_bloqueado(_erro(
            "architecture_calculation_failed",
            "%s: %s" % (type(exc).__name__, exc))), None
    registro = {
        "status": "blocked" if resultado["erros"] else "needs_review",
        "native_atende": resultado["ATENDE"],
        "reprovados": list(resultado["reprovados"]),
        "gates": copy.deepcopy(resultado["gates"]),
        "warnings": copy.deepcopy(resultado["avisos"]),
        "errors": copy.deepcopy(resultado["erros"]),
        "artifacts": [],
        "programa": copy.deepcopy(resultado["ambientes"]),
        "totais": copy.deepcopy(resultado["totais"]),
        "scope": copy.deepcopy(resultado["escopo"]),
    }
    return registro, resultado


def arq_registro_bloqueado(erro):
    return {"status": "blocked", "native_atende": None, "reprovados": [],
            "gates": {}, "warnings": [], "errors": [erro], "artifacts": [],
            "programa": [], "totais": {}, "scope": {}}


def _registro_hidraulica(payload, resultado_arquitetura):
    if not isinstance(payload, dict):
        return {"status": "blocked", "native_atende": None, "reprovados": [],
                "gates": {}, "warnings": [], "artifacts": [], "redes": {},
                "scope": {},
                "errors": [_erro("invalid_hydraulic_payload",
                                 "turnkey.hidraulica deve ser um objeto JSON")]}, None
    entrada = copy.deepcopy(payload)
    if resultado_arquitetura is not None and "ambientes" not in entrada:
        # a conferencia arquitetura x hidraulica so existe se o programa chegar
        # ate aqui; sem isso um banheiro sem aparelho passaria despercebido
        entrada["ambientes"] = [
            {"nome": a["nome"], "tipo": a["tipo"]}
            for a in resultado_arquitetura.get("ambientes", [])]
    try:
        resultado = hid.rodar(entrada)
    except (TypeError, ValueError) as exc:
        return {"status": "blocked", "native_atende": None, "reprovados": [],
                "gates": {}, "warnings": [], "artifacts": [], "redes": {},
                "scope": {},
                "errors": [_erro("hydraulic_calculation_failed",
                                 "%s: %s" % (type(exc).__name__, exc))]}, None
    registro = {
        "status": "blocked" if resultado["erros"] else "needs_review",
        "native_atende": resultado["ATENDE"],
        "reprovados": list(resultado["reprovados"]),
        "gates": copy.deepcopy(resultado["gates"]),
        "warnings": copy.deepcopy(resultado["avisos"]),
        "errors": copy.deepcopy(resultado["erros"]),
        "artifacts": [],
        "redes": copy.deepcopy(resultado["redes"]),
        "dimensionamento": resultado["dimensionamento"],
        "scope": copy.deepcopy(resultado["escopo"]),
    }
    return registro, resultado


def _registro_eletrico(normalized, run_dir, preflight, resultado_arquitetura):
    resultado, registros = run_residential_electrical(normalized, run_dir, preflight)
    registro = registros["eletrico"]
    turnkey = normalized.get("turnkey_spec")
    payload = turnkey.get("eletrico") if isinstance(turnkey, dict) else None
    circuitos = payload.get("circuits") if isinstance(payload, dict) else {}

    if resultado_arquitetura is None:
        registro["warnings"] = list(registro.get("warnings", [])) + [_erro(
            "conferencia_nbr5410_nao_executada",
            "sem programa de arquitetura valido nao ha como conferir os pontos "
            "declarados contra o minimo de 9.5.2")]
        registro["conferencia_nbr5410"] = {
            "ok": None, "por_ambiente": [], "erros": [], "avisos": [],
            "totais": {}, "fonte": "ABNT NBR 5410:2004 9.5.2"}
        resultado["conferencia_nbr5410"] = copy.deepcopy(
            registro["conferencia_nbr5410"])
        return registro, resultado

    conferencia = conferir_previsao_nbr5410(resultado_arquitetura, circuitos)
    geometria = conferir_geometria_layout(resultado_arquitetura, circuitos)
    conferencia["geometria_layout"] = geometria
    if geometria["erros"]:
        conferencia["erros"] = list(conferencia["erros"]) + copy.deepcopy(
            geometria["erros"])
        conferencia["ok"] = False
    registro["conferencia_nbr5410"] = copy.deepcopy(conferencia)
    registro["gates"] = dict(registro.get("gates", {}))
    registro["gates"]["previsao_nbr5410_atendida"] = bool(conferencia["ok"])
    registro["errors"] = list(registro.get("errors", [])) + copy.deepcopy(
        conferencia["erros"])
    registro["warnings"] = list(registro.get("warnings", [])) + copy.deepcopy(
        conferencia["avisos"])
    if not conferencia["ok"]:
        registro["status"] = "blocked"
        registro["native_atende"] = False
        registro["reprovados"] = list(registro.get("reprovados", [])) + [
            "previsao_nbr5410"]
    resultado["conferencia_nbr5410"] = copy.deepcopy(conferencia)
    resultado["errors"] = list(resultado.get("errors", [])) + copy.deepcopy(
        conferencia["erros"])
    if not conferencia["ok"]:
        resultado["status"] = "blocked"
    return registro, resultado


def run_casa_residencial(normalized, run_dir, preflight=None):
    """Executa as tres disciplinas da casa e devolve (resultado, registros)."""
    if not isinstance(normalized, dict):
        raise TypeError("normalized deve ser um objeto")
    turnkey = normalized.get("turnkey_spec")
    turnkey = turnkey if isinstance(turnkey, dict) else {}
    solicitadas = list(normalized.get("requested_disciplines") or DISCIPLINES)

    registros = {}
    disciplinas = {}
    resultado_arquitetura = None

    if "arquitetura" in solicitadas:
        payload = turnkey.get("arquitetura")
        if payload is None:
            registros["arquitetura"] = arq_registro_bloqueado(_erro(
                "missing_architecture_input",
                "turnkey.arquitetura nao foi declarado"))
        else:
            registros["arquitetura"], resultado_arquitetura = _registro_arquitetura(
                payload)
        disciplinas["arquitetura"] = {
            "engine": "arquitetura_residencial",
            "status": registros["arquitetura"]["status"]}

    if "eletrico" in solicitadas:
        registro, resultado_eletrico = _registro_eletrico(
            normalized, run_dir, preflight, resultado_arquitetura)
        registros["eletrico"] = registro
        disciplinas["eletrico"] = {
            "engine": "residencial_eletrica", "status": registro["status"]}
    else:
        resultado_eletrico = None

    resultado_hidraulico = None
    if "hidraulica" in solicitadas:
        payload = turnkey.get("hidraulica")
        if payload is None:
            registros["hidraulica"] = {
                "status": "blocked", "native_atende": None, "reprovados": [],
                "gates": {}, "warnings": [], "artifacts": [], "redes": {},
                "scope": {},
                "errors": [_erro("missing_hydraulic_input",
                                 "turnkey.hidraulica nao foi declarado")]}
        else:
            registros["hidraulica"], resultado_hidraulico = _registro_hidraulica(
                payload, resultado_arquitetura)
        disciplinas["hidraulica"] = {
            "engine": "hidraulica_residencial",
            "status": registros["hidraulica"]["status"]}

    resultado = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "adapter": ADAPTER_NAME,
        "synthetic_fixture": False,
        "project_id": normalized.get("project_id"),
        "disciplines": disciplinas,
        "arquitetura": copy.deepcopy(resultado_arquitetura),
        "eletrico": copy.deepcopy(resultado_eletrico),
        "hidraulica": copy.deepcopy(resultado_hidraulico),
        "scope": {
            "arquitetura": "implemented",
            "eletrico": "implemented",
            "hidraulica": "implemented",
            "estrutura": "not_available",
            "aprovacao_legal": "not_claimed",
            "construction_readiness": "not_claimed",
        },
    }
    resultado["status"] = ("blocked" if any(
        r["status"] == "blocked" for r in registros.values()) else "needs_review")
    return resultado, registros


def _erro_entregavel(exc: Exception) -> str:
    return "%s: %s" % (type(exc).__name__, exc)


def _emitir_desenhos(manifest, run_dir, normalized, options, result):
    """Hook de desenhos: planta de ambientes + quadro de previsao de carga.

    Nao depende de FreeCAD: le o JSON ja calculado. Ausencia de dado vira
    motivo explicito no manifesto, nunca um arquivo vazio."""
    from pathlib import Path

    import desenho_casa_residencial as dcr
    from project_loop import _add_artifact

    del normalized
    if not (options.generate_2d or options.generate_caderno):
        manifest["deliverables"]["drawings"] = {"status": "not_requested"}
        return
    destino = Path(run_dir) / "drawings"
    try:
        emitido = dcr.gerar_desenhos_casa(result, destino)
    except Exception as exc:                                # noqa: BLE001
        manifest["deliverables"]["drawings"] = {
            "status": "failed", "detail": _erro_entregavel(exc)}
        return
    for nome in emitido["files"]:
        _add_artifact(manifest, run_dir, destino / nome, "drawing")
    manifest["deliverables"]["drawings"] = {
        "status": "generated" if emitido["files"] else "not_available",
        "artifacts": ["drawings/" + nome for nome in emitido["files"]],
        "skipped": emitido["skipped"],
    }


def register_casa_residencial_adapter() -> None:
    """Registra o adaptador residencial real no Project Loop."""
    from project_loop import register_adapter

    register_adapter(
        ADAPTER_NAME,
        run_casa_residencial,
        project_types=("residencial",),
        disciplines=DISCIPLINES,
        deliverables=DELIVERABLES,
        hooks={"drawings": _emitir_desenhos},
    )
