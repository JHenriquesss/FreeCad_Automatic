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
#                  ventilacao (NBR 8160) e pluvial (NBR 10844);
#   estrutura   -> estrutura_casa (G13): carga NBR 6120 -> laje -> viga continua
#                  VERIFICADA -> pilar -> viga baldrame -> fundacao. Era a
#                  disciplina que faltava: a casa tinha instalacoes e nao tinha
#                  laje, viga, pilar nem fundacao, e o escopo dizia
#                  `estrutura: not_available` em voz alta desde o G4.
#
# A CONFERENCIA e' a costura que faltava: a vertical eletrica exige que o
# projetista declare ponto a ponto e nunca soube dizer se o que ele declarou
# atende ao minimo da norma para aquela planta. Aqui a planta (arquitetura) e a
# instalacao (eletrico) se olham: ponto faltando REPROVA, e ponto que aponta
# para um ambiente inexistente tambem (um filtro de nome morto devolveria zero
# pontos em silencio).
#
# A ESTRUTURA ENTRA NA MESMA COSTURA. A malha estrutural e o programa de
# ambientes sao duas declaracoes da MESMA casa: a area util do programa nao pode
# passar da area coberta pela malha (haveria comodo sem estrutura em cima), e o
# pe-direito declarado na arquitetura tem de ser o pe-direito com que os pilares
# foram dimensionados. Com o layout declarado a conferencia fica geometrica: todo
# retangulo de comodo tem de caber DENTRO do retangulo da malha. Sem essa
# costura, o Loop desenharia uma planta e calcularia outra estrutura.
#
# Nenhuma disciplina e' marcada 'passed': aprovacao para obra continua sendo
# decisao de responsavel tecnico. O adaptador nao importa nem chama
# galpao_turnkey.
# ============================================================================
"""Adaptador residencial real: arquitetura, estrutura, eletrico e hidraulica,
com as costuras entre a planta, a instalacao declarada e a malha estrutural."""

from __future__ import annotations

import copy
import unicodedata
from typing import Any

import arquitetura_residencial as arq
import estrutura_casa as est
import hidraulica_residencial as hid
from residencial_eletrica import run_residential_electrical


ADAPTER_NAME = "casa-residencial"
DISCIPLINES = ("arquitetura", "estrutura", "eletrico", "hidraulica")
DELIVERABLES = ("report", "drawings", "ifc", "model_3d")
SCHEMA = "freecad-automatic/residential-house-result"
SCHEMA_VERSION = 1
# 'lighting' conta para o ponto de luz de 9.5.2.1.1; 'tug' conta para os pontos
# de tomada de 9.5.2.2.1. 'tue' e' ponto de utilizacao dedicado (9.5.3.1) e nao
# substitui uma TUG.
KIND_ILUMINACAO = "lighting"
KIND_TOMADA = "tug"

# Tolerancias da costura arquitetura x estrutura. Sao de DIGITACAO do spec, nao
# de projeto: acima delas as duas declaracoes descrevem casas diferentes.
TOL_AREA_M2 = 0.01           # 100 cm2
TOL_PE_DIREITO_M = 0.010     # 10 mm
TOL_GEOM_M = 0.010           # 10 mm


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


def conferir_arquitetura_estrutura(resultado_arquitetura, spec_estrutura,
                                   layout=None):
    """Costura ARQUITETURA x ESTRUTURA: a mesma casa, declarada duas vezes.

    Tres conferencias, da mais barata para a mais forte:

    1. AREA - a area util do programa nao pode passar da area coberta pela
       malha estrutural. Se passa, ha metros quadrados de casa sem laje, viga
       nem pilar em cima. Roda SEMPRE, mesmo sem layout declarado, porque o
       programa sempre tem area.
    2. PE-DIREITO - o da arquitetura e o com que os lances de pilar foram
       dimensionados tem de ser o mesmo numero. Divergir e' desenhar uma casa e
       calcular outra.
    3. GEOMETRIA (so com layout declarado) - todo retangulo de comodo tem de
       caber DENTRO do retangulo da malha. E' a versao geometrica da conferencia
       1: a area pode fechar com um quarto pendurado para fora da estrutura.

    Devolve {'ok', 'erros', 'avisos', 'area_programa_m2', 'area_malha_m2', ...}.
    """
    geo = (spec_estrutura or {}).get("geometria") or {}
    vaos_x = geo.get("vaos_x") or []
    vaos_y = geo.get("vaos_y") or []
    if not vaos_x or not vaos_y:
        return {"ok": None, "erros": [], "avisos": [],
                "detail": "sem malha estrutural declarada"}
    Lx = float(sum(vaos_x))
    Ly = float(sum(vaos_y))
    area_malha = Lx * Ly
    area_programa = float(
        ((resultado_arquitetura or {}).get("totais") or {}).get("area_util_m2")
        or 0.0)
    erros = []
    avisos = []
    if area_programa > area_malha + TOL_AREA_M2:
        erros.append(_erro(
            "programa_maior_que_a_malha_estrutural",
            "a area util do programa de ambientes (%.2f m2) passa da area "
            "coberta pela malha estrutural (%.2f x %.2f = %.2f m2): ha comodo "
            "sem laje, viga ou pilar por cima"
            % (area_programa, Lx, Ly, area_malha),
            area_programa_m2=round(area_programa, 3),
            area_malha_m2=round(area_malha, 3)))

    pe_arq = (resultado_arquitetura or {}).get("pe_direito_m")
    pe_est = geo.get("pe_direito")
    if (isinstance(pe_arq, (int, float)) and not isinstance(pe_arq, bool)
            and isinstance(pe_est, (int, float))):
        if abs(float(pe_arq) - float(pe_est)) > TOL_PE_DIREITO_M:
            erros.append(_erro(
                "pe_direito_diverge",
                "o pe-direito da arquitetura (%.3f m) diverge do que dimensionou "
                "os pilares (%.3f m)" % (float(pe_arq), float(pe_est)),
                arquitetura_m=float(pe_arq), estrutura_m=float(pe_est)))
    elif pe_arq is None:
        avisos.append(_erro(
            "pe_direito_nao_declarado_na_arquitetura",
            "arquitetura.pe_direito_m nao foi declarado: a conferencia contra o "
            "pe-direito da estrutura nao pode ser feita (e o BIM da arquitetura "
            "tambem depende dele)"))

    fora = []
    comodos = (layout or {}).get("rooms")
    # `conferido` distingue "nenhum comodo fora da malha" de "a conferencia
    # geometrica nao rodou". Sem essa distincao, um layout que nao chegou ate
    # aqui (nao declarado, ou rejeitado pela validacao do eletrico) passaria por
    # aprovado - ausencia silenciosa disfarcada de aprovacao.
    conferido = isinstance(comodos, list) and bool(comodos)
    if isinstance(comodos, list):
        for comodo in comodos:
            if not isinstance(comodo, dict):
                continue
            try:
                x0 = float(comodo["x_m"]); y0 = float(comodo["y_m"])
                x1 = x0 + float(comodo["width_m"])
                y1 = y0 + float(comodo["depth_m"])
            except (KeyError, TypeError, ValueError):
                continue
            if (x0 < -TOL_GEOM_M or y0 < -TOL_GEOM_M
                    or x1 > Lx + TOL_GEOM_M or y1 > Ly + TOL_GEOM_M):
                fora.append({"ambiente": comodo.get("name") or comodo.get("id"),
                             "x": [round(x0, 3), round(x1, 3)],
                             "y": [round(y0, 3), round(y1, 3)]})
        if fora:
            erros.append(_erro(
                "comodo_fora_da_malha_estrutural",
                "ha comodo cujo retangulo sai da malha estrutural "
                "(0..%.2f x 0..%.2f m): essa parte da casa nao tem estrutura"
                % (Lx, Ly), comodos=fora))
    if not conferido:
        avisos.append(_erro(
            "conferencia_geometrica_nao_executada",
            "nenhum layout de ambientes chegou ate a estrutura (nao declarado, "
            "ou o layout do eletrico foi rejeitado): so a AREA foi conferida "
            "contra a malha, nao a posicao de cada comodo"))
    return {"ok": not erros, "erros": erros, "avisos": avisos,
            "area_programa_m2": round(area_programa, 3),
            "area_malha_m2": round(area_malha, 3),
            "malha_m": [round(Lx, 3), round(Ly, 3)],
            "layout_conferido": conferido,
            "comodos_fora_da_malha": fora}


def _registro_estrutura_bloqueado(erro, escopo=None):
    return {"status": "blocked", "native_atende": None, "reprovados": [],
            "gates": {}, "warnings": [], "errors": [erro], "artifacts": [],
            "scope": escopo or est.escopo(False, False)}


def _registro_estrutura(payload, resultado_arquitetura, layout=None):
    """Roda a cadeia estrutural da casa e costura o resultado com o programa.

    `layout` e' o layout de ambientes (do arquiteto ou do projeto eletrico, ver
    `layout_arquitetonico`) usado SO na conferencia geometrica. Ele nunca vira
    entrada de calculo: a malha estrutural continua sendo a que o projetista
    declarou, nunca deduzida das posicoes dos comodos.
    """
    if not isinstance(payload, dict):
        return _registro_estrutura_bloqueado(_erro(
            "invalid_structure_payload",
            "turnkey.estrutura deve ser um objeto JSON")), None
    entrada = copy.deepcopy(payload)
    conferencia = conferir_arquitetura_estrutura(resultado_arquitetura, entrada,
                                                 layout)
    import fundacao_edificio as fe

    # o escopo do registro BLOQUEADO tambem tem de dizer a verdade sobre o que
    # foi declarado; a pergunta "ha fundacao?" e' delegada a `fundacao_edificio`
    # para que ela tenha UMA resposta em todo o framework
    com_baldrame = bool(entrada.get("baldrame"))
    com_fundacao = fe.declarada(entrada.get("fundacao"))

    try:
        resultado = est.rodar(entrada)
    except est.EntradaEstrutura as exc:
        return _registro_estrutura_bloqueado(
            _erro("structure_input_rejected", str(exc)),
            est.escopo(com_baldrame, com_fundacao)), None
    except Exception as exc:                                # noqa: BLE001
        registro = _registro_estrutura_bloqueado(
            _erro("structure_run_failed", "%s: %s" % (type(exc).__name__, exc)),
            est.escopo(com_baldrame, com_fundacao))
        registro["status"] = "failed"
        return registro, None

    avisos = list(conferencia.get("avisos") or [])
    if resultado["reprovados"]:
        avisos.append(_erro("structure_gates_failed",
                            "gates reprovados: %s"
                            % ", ".join(resultado["reprovados"]),
                            reprovados=list(resultado["reprovados"])))
    avisos.append(_erro("reducao_6120_registrada", resultado["registro_6120"]))
    avisos.append(_erro(
        "acao_horizontal_nao_avaliada",
        "esta cadeia e' GRAVITACIONAL: vento, desaprumo, gamma_z e o ELS de "
        "deslocamento lateral nao sao avaliados para casa terrea ou sobrado"))
    if resultado.get("baldrame") is None:
        avisos.append(_erro(
            "viga_baldrame_nao_declarada",
            "estrutura.baldrame nao foi declarado: o peso da alvenaria do "
            "terreo NAO desce para a fundacao (ele nao passa pelos pilares). "
            "As sapatas estao dimensionadas so para o que as lajes entregaram"))
    if resultado.get("baldrame_erro"):
        avisos.append(_erro("viga_baldrame_rejeitada",
                            resultado["baldrame_erro"]))
    if resultado.get("fundacao") is None and not resultado.get("fundacao_erro"):
        avisos.append(_erro(
            "fundacao_nao_declarada",
            "estrutura.fundacao nao foi declarada (perfil_spt da sondagem ou "
            "sigma_solo_adm): a carga desce ate a base do pilar e para ali. A "
            "tensao admissivel do solo nao e' arbitrada por este framework"))
    if resultado.get("fundacao"):
        avisos.extend(_erro(item["code"], item["detail"])
                      for item in resultado["fundacao"]["avisos"])

    erros = list(conferencia.get("erros") or [])
    if resultado.get("fundacao_erro"):
        erros.append(_erro("foundation_input_rejected",
                           resultado["fundacao_erro"]))
    registro = {
        "status": "blocked" if erros else "needs_review",
        "native_atende": bool(resultado["ATENDE"]),
        "reprovados": list(resultado["reprovados"]),
        "gates": copy.deepcopy(resultado["gates"]),
        "warnings": avisos,
        "errors": erros,
        "artifacts": [],
        "scope": copy.deepcopy(resultado["escopo"]),
        "conferencia_arquitetura": copy.deepcopy(conferencia),
        "tipologia": resultado["tipologia"],
        "N_fundacao_k": copy.deepcopy(resultado["N_fundacao_k"]),
    }
    registro["gates"]["conferencia_arquitetura"] = {
        "OK": conferencia["ok"] is not False,
        "area_programa_m2": conferencia.get("area_programa_m2"),
        "area_malha_m2": conferencia.get("area_malha_m2")}
    if conferencia["ok"] is False:
        registro["native_atende"] = False
        registro["reprovados"] = list(registro["reprovados"]) + [
            "conferencia_arquitetura"]
    if resultado.get("fundacao"):
        fundacao = resultado["fundacao"]
        registro["foundation"] = {
            "tipo": fundacao["tipo"],
            "sigma_solo_adm_kNm2": fundacao["sigma_solo_adm"],
            "proveniencia_sigma": fundacao["proveniencia_sigma"],
            "por_pilar": {nome: {"N_dimensionamento_kN": r["N_dimensionamento_kN"],
                                 "geometria": r["geometria"], "OK": r["OK"]}
                          for nome, r in fundacao["por_pilar"].items()},
            "scope": copy.deepcopy(fundacao["escopo"]),
        }
    return registro, resultado


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

    # A ESTRUTURA roda DEPOIS do eletrico porque a conferencia geometrica aceita
    # o layout de qualquer uma das duas proveniencias (ver `layout_arquitetonico`),
    # e a do eletrico so existe com o resultado eletrico ja calculado.
    resultado_estrutura = None
    if "estrutura" in solicitadas:
        payload = turnkey.get("estrutura")
        if payload is None:
            registros["estrutura"] = _registro_estrutura_bloqueado(_erro(
                "missing_structure_input",
                "turnkey.estrutura nao foi declarado"))
        else:
            layout, _proveniencia = layout_arquitetonico(
                turnkey, {"eletrico": resultado_eletrico})
            registros["estrutura"], resultado_estrutura = _registro_estrutura(
                payload, resultado_arquitetura, layout)
        disciplinas["estrutura"] = {
            "engine": "estrutura_casa",
            "status": registros["estrutura"]["status"]}

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
        "estrutura": copy.deepcopy(resultado_estrutura),
        "scope": {
            "arquitetura": "implemented",
            "eletrico": "implemented",
            "hidraulica": "implemented",
            # G13: deixou de ser not_available. Continua dependendo de ser
            # DECLARADA - disciplina que o spec nao pede nao e' projeto inventado
            # a partir do envelope.
            "estrutura": ("implemented" if resultado_estrutura is not None
                          else "not_available"),
            "aprovacao_legal": "not_claimed",
            "construction_readiness": "not_claimed",
        },
    }
    if resultado_estrutura is not None:
        resultado["scope"].update(resultado_estrutura["escopo"])
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


def layout_arquitetonico(turnkey, result):
    """De onde sai o layout da casa, e com que PROVENIENCIA.

    Prioridade:
      1. `turnkey.arquitetura.layout` - a declaracao do proprio arquiteto;
      2. os comodos do layout ELETRICO ja validado - que a eletrica exige para
         posicionar pontos de circuito, e que descrevem a MESMA casa.

    A segunda fonte e' reuso, nao invencao: o retangulo veio do projetista, so
    que declarado noutra secao do spec. Mas a proveniencia viaja junto ate o
    manifesto, porque um layout que a arquitetura nao declarou nao pode ser
    lido como se ela o tivesse declarado. Seja qual for a fonte, o retangulo
    ainda tem de reproduzir area e perimetro do programa (`validar_layout`).
    """
    arquitetura = turnkey.get("arquitetura")
    if isinstance(arquitetura, dict) and arquitetura.get("layout") is not None:
        return arquitetura["layout"], "arquitetura.layout"
    validacao = (((result or {}).get("eletrico") or {}).get("circuits")
                 or {}).get("layout_validation") or {}
    if validacao.get("ok") and isinstance(validacao.get("layout"), dict):
        eletrico = validacao["layout"]
        return {"units": eletrico.get("units"),
                "rooms": copy.deepcopy(eletrico.get("rooms") or [])}, \
               "eletrico.circuits.layout"
    return None, None


def _estrutura_calculada(result):
    """O resultado da estrutura, ou None se a rodada nao a produziu."""
    estrutura = result.get("estrutura") if isinstance(result, dict) else None
    return estrutura if isinstance(estrutura, dict) and estrutura else None


def _ifc_da_arquitetura(destino, normalized, result):
    """IFC4 dos AMBIENTES (+ piso e paredes declaradas). Ver a nota do hook."""
    import bim_casa_residencial as bim

    arquitetura = result.get("arquitetura") if isinstance(result, dict) else None
    if not isinstance(arquitetura, dict) or not arquitetura:
        return {"status": "not_available",
                "detail": "arquitetura nao calculada; sem programa para modelar"}
    turnkey = normalized.get("turnkey_spec")
    turnkey = turnkey if isinstance(turnkey, dict) else {}
    layout, proveniencia = layout_arquitetonico(turnkey, result)
    if layout is None:
        return {"status": "not_available",
                "detail": "nenhum layout de ambientes declarado (arquitetura.layout "
                          "ou o layout do projeto eletrico): sem posicao nao ha "
                          "modelo honesto a emitir"}
    validacao = bim.validar_layout(layout, arquitetura)
    if not validacao["ok"]:
        return {"status": "blocked",
                "detail": "o layout nao confere com o programa de ambientes",
                "layout_origem": proveniencia,
                "errors": validacao["errors"]}
    membros = bim.membros_bim(arquitetura, validacao["layout"])
    conferencia = bim.confere_areas(arquitetura, membros)
    solidos = bim.confere_solidos(membros)
    arquivo = destino / "arquitetura-residencial.ifc"
    escrito = bim.emitir_bim(arquitetura, validacao["layout"], str(arquivo))
    if not escrito or not arquivo.is_file():
        return {"status": "not_available",
                "detail": "nenhum elemento BIM emitido (pe-direito nao declarado?)"}
    registro = {
        "status": ("generated" if (conferencia["ok"] and solidos["OK"])
                   else "failed"),
        "arquivo": arquivo, "artifact": "bim/arquitetura-residencial.ifc",
        "disciplina": "arquitetura",
        "layout_origem": proveniencia,
        "n_elementos": len(membros),
        "conferencia_areas": conferencia,
        "interferencias": solidos["conflitos"],
        # o que o layout NAO declarou fica dito, em vez de sumir
        "escopo": {
            "ambientes": "implemented",
            "piso": ("implemented" if validacao["layout"].get("piso_espessura_m")
                     else "not_declared"),
            "paredes": ("implemented" if validacao["layout"].get("paredes")
                        else "not_declared"),
            "esquadrias": "not_declared",
        },
    }
    if not conferencia["ok"]:
        registro["detail"] = ("a area dos ambientes emitidos nao reproduz o "
                              "programa calculado")
    elif not solidos["OK"]:
        registro["detail"] = ("pecas declaradas se interpenetram no modelo; "
                              "veja 'interferencias'")
    return registro


def _ifc_da_estrutura(destino, result):
    """IFC4 da ESTRUTURA: laje, viga, pilar, baldrame e fundacao.

    Reusa `bim_edificio` inteiro - a casa e' a mesma geometria de concreto do
    edificio com menos andares, e o resultado de `estrutura_casa` usa as mesmas
    chaves de proposito. O modelo e' CONFERIDO contra o calculo (contagem por
    tipo e interpenetracao) antes de ser publicado: um IFC que perdeu pilares no
    caminho abre normalmente no visualizador e nao denuncia nada.
    """
    import bim_edificio as bim

    estrutura = _estrutura_calculada(result)
    if estrutura is None:
        return {"status": "not_available",
                "detail": "estrutura nao calculada; sem pecas estruturais a emitir"}
    try:
        membros = bim.membros_bim(estrutura)
        conferencia = bim.confere_modelo(estrutura, membros)
        empilhamento = bim.confere_empilhamento(membros)
        arquivo = destino / "estrutura-residencial.ifc"
        bim.emitir_bim(estrutura, str(arquivo), nome="CasaResidencial")
    except bim.GeometriaIncoerente as exc:
        return {"status": "blocked", "detail": _erro_entregavel(exc)}
    if not arquivo.is_file():
        return {"status": "not_available",
                "detail": "nenhum elemento estrutural emitido"}
    registro = {
        "status": ("generated" if (conferencia["ok"] and empilhamento["OK"])
                   else "failed"),
        "arquivo": arquivo, "artifact": "bim/estrutura-residencial.ifc",
        "disciplina": "estrutura",
        "n_elementos": len(membros),
        "conferencia_modelo": conferencia,
        "interferencias": empilhamento["conflitos"],
        "quantitativo": bim.quantitativo(membros),
    }
    if registro["status"] != "generated":
        registro["detail"] = ("o modelo emitido nao reproduz o calculo "
                              "(contagem por tipo ou interpenetracao)")
    return registro


def _emitir_ifc(manifest, run_dir, normalized, options, result):
    """Hook BIM: IFC4 da ARQUITETURA e, desde o G13, da ESTRUTURA.

    O modelo da casa nunca existiu porque o programa declara area e perimetro,
    nao posicoes - e desenhar comodos em posicoes inventadas seria pior que nao
    desenhar. O que destrava o BIM da arquitetura e' o LAYOUT declarado; sem ele
    o entregavel fica not_available com o motivo escrito, nunca um IFC vazio. A
    estrutura NAO depende do layout: a malha e' declarada e ja esta calculada -
    por isso ela sai mesmo quando a casa nao tem posicao de comodo nenhuma.

    DOIS ARQUIVOS, NAO UM FEDERADO. A alvenaria da arquitetura e os pilares da
    estrutura ocupam legitimamente o mesmo plano; num arquivo unico a varredura
    de interpenetracao acusaria dezenas de conflitos que sao embutimento de
    proposito, e o entregavel se anunciaria falho sem nada estar errado. Cada
    modelo e' conferido contra o SEU calculo.
    """
    from pathlib import Path

    from project_loop import _add_artifact

    if not options.generate_ifc:
        manifest["deliverables"]["ifc"] = {"status": "not_requested"}
        return
    try:
        import ifc_emit
        if not ifc_emit.disponivel():
            manifest["deliverables"]["ifc"] = {
                "status": "not_available", "detail": "ifcopenshell ausente"}
            return
    except Exception as exc:                                # noqa: BLE001
        manifest["deliverables"]["ifc"] = {
            "status": "failed", "detail": _erro_entregavel(exc)}
        return

    destino = Path(run_dir) / "bim"
    destino.mkdir(parents=True, exist_ok=True)
    partes = {}
    for nome, emissor in (
            ("arquitetura",
             lambda: _ifc_da_arquitetura(destino, normalized, result)),
            ("estrutura", lambda: _ifc_da_estrutura(destino, result))):
        try:
            partes[nome] = emissor()
        except Exception as exc:                            # noqa: BLE001
            partes[nome] = {"status": "failed", "detail": _erro_entregavel(exc)}

    artefatos = []
    for nome, parte in partes.items():
        arquivo = parte.pop("arquivo", None)
        if arquivo is not None:
            _add_artifact(manifest, run_dir, arquivo, "ifc",
                          discipline=parte.get("disciplina", nome))
            artefatos.append(parte["artifact"])
    if not artefatos:
        # nenhum modelo saiu: o motivo de cada parte viaja em `partes`, e o
        # `detail` repete o da estrutura (a que nao depende de layout declarado)
        motivo = (partes["estrutura"].get("detail")
                  or partes["arquitetura"].get("detail")
                  or "nenhum elemento BIM emitido")
        status = ("blocked" if any(p["status"] == "blocked"
                                   for p in partes.values())
                  else "failed" if any(p["status"] == "failed"
                                       for p in partes.values())
                  else "not_available")
        manifest["deliverables"]["ifc"] = {"status": status, "detail": motivo,
                                           "partes": partes}
        return
    emitidas = [p for p in partes.values() if p.get("artifact")]
    registro = {
        "status": ("generated"
                   if all(p["status"] == "generated" for p in emitidas)
                   else "failed"),
        "artifacts": artefatos,
        "n_elementos": sum(p.get("n_elementos", 0) for p in emitidas),
        "partes": partes,
    }
    if registro["status"] != "generated":
        registro["detail"] = ("ao menos um dos modelos emitidos nao reproduz o "
                              "calculo que o gerou")
    manifest["deliverables"]["ifc"] = registro


# tolerancia do cross-check de volume entre o modelo puro e o do FreeCAD (m3).
# Os dois somam as MESMAS caixas, em ordens diferentes e arredondando a 3 casas;
# acima disso ja nao e' arredondamento, e' geometria diferente.
TOL_VOLUME_M3 = 0.005


def _build_3d(saida, membros, run_dir, manifest, extra=None, volume_puro=None):
    """Traduz o retorno do build FreeCAD em registro de entregavel.

    Uma so leitura do retorno para os dois modelos (arquitetura e estrutura):
    FreeCAD ausente e' indisponibilidade de AMBIENTE, nao falha do projeto; e o
    3D so e' 'generated' quando reproduz o modelo puro peca a peca e sai sem
    interpenetracao.
    """
    from pathlib import Path

    from project_loop import _add_artifact

    if not isinstance(saida, dict) or saida.get("erro"):
        motivo = (saida or {}).get("erro", "o build nao devolveu resultado")
        indisponivel = any(t in str(motivo).lower() for t in
                           ("nao encontrado", "indisponivel", "ausente"))
        return {"status": "not_available" if indisponivel else "failed",
                "detail": motivo}
    modelo = saida.get("result") or {}
    artefatos = []
    for chave, kind in (("fcstd", "model-3d"), ("step", "model-3d"),
                        ("ifc", "ifc-freecad")):
        caminho = modelo.get(chave)
        if caminho and Path(caminho).is_file():
            artefatos.append(_add_artifact(manifest, run_dir, Path(caminho), kind))
    # CROSS-CHECK de VOLUME: contar pecas nao pega uma caixa que mudou de
    # tamanho. Sao duas descricoes da mesma estrutura por caminhos independentes
    # (emissor puro e OCCT), e comparar o concreto e' o que impede uma delas de
    # envelhecer sem que ninguem perceba.
    vol_freecad = modelo.get("vol_concreto_m3")
    volume_ok = True
    if volume_puro is not None:
        volume_ok = (vol_freecad is not None
                     and abs(float(vol_freecad) - float(volume_puro))
                     <= TOL_VOLUME_M3)
    registro = {
        "status": ("generated"
                   if (artefatos and modelo.get("elementos") == len(membros)
                       and volume_ok and not modelo.get("interferencias"))
                   else "failed"),
        "artifacts": [item["path"] for item in artefatos],
        "n_pecas_puro": len(membros),
        "n_pecas_freecad": modelo.get("elementos"),
        "interferencias": modelo.get("interferencias"),
        "interferencias_lista": modelo.get("interferencias_lista"),
    }
    if volume_puro is not None:
        registro["cross_check_volume"] = {
            "ok": bool(volume_ok),
            "vol_concreto_puro_m3": round(float(volume_puro), 4),
            "vol_concreto_freecad_m3": vol_freecad}
    registro.update(extra or {})
    if registro["status"] == "failed":
        registro["detail"] = ("o 3D diverge do modelo puro (contagem ou volume) "
                              "ou acusa interpenetracao entre pecas declaradas")
    return registro


def _modelo_3d_arquitetura(manifest, run_dir, normalized, options, result):
    """Solidos do que TEM solido na arquitetura: piso e paredes declaradas.

    O ambiente (IfcSpace) e' volume de uso, nao peca construida, e nao vai para
    o 3D. Se o layout so declarou os retangulos dos comodos, nao ha nenhum
    solido a montar - e o entregavel diz isso, em vez de gerar um FCStd vazio.
    """
    from pathlib import Path

    import bim_casa_residencial as bim

    arquitetura = result.get("arquitetura") if isinstance(result, dict) else None
    turnkey = normalized.get("turnkey_spec")
    turnkey = turnkey if isinstance(turnkey, dict) else {}
    layout, proveniencia = layout_arquitetonico(turnkey, result)
    if not isinstance(arquitetura, dict) or layout is None:
        return {"status": "not_available",
                "detail": "sem arquitetura calculada ou sem layout declarado"}
    validacao = bim.validar_layout(layout, arquitetura)
    if not validacao["ok"]:
        return {"status": "blocked",
                "detail": "o layout nao confere com o programa de ambientes",
                "layout_origem": proveniencia,
                "errors": validacao["errors"]}
    membros = [m for m in bim.membros_bim(arquitetura, validacao["layout"])
               if m["tipo"] != "Space"]
    if not membros:
        return {"status": "not_available",
                "detail": "o layout declara ambientes mas nenhum solido (piso ou "
                          "parede); nao ha 3D a montar",
                "layout_origem": proveniencia}
    destino = Path(run_dir) / "model" / "arquitetura"
    destino.mkdir(parents=True, exist_ok=True)
    saida = bim.montar_3d(
        membros, str(destino),
        doc_name="%s-arquitetura" % (normalized.get("project_id") or "casa"),
        timeout=options.timeout_seconds)
    return _build_3d(saida, membros, run_dir, manifest,
                     {"layout_origem": proveniencia})


def _modelo_3d_estrutura(manifest, run_dir, normalized, options, result):
    """Solidos da estrutura (laje, viga, pilar, baldrame, fundacao).

    Reusa `bim_edificio.montar_3d`, o mesmo build de caixas de concreto do
    edificio. Vale por uma pergunta que o emissor puro nao responde:
    interferencia sobre SOLIDOS REAIS (OCCT common()), nao sobre caixas
    envolventes - e serve de CROSS-CHECK do modelo neutro que gerou o IFC.
    """
    from pathlib import Path

    import bim_edificio as bim

    estrutura = _estrutura_calculada(result)
    if estrutura is None:
        return {"status": "not_available",
                "detail": "estrutura nao calculada; sem pecas a montar"}
    try:
        membros = bim.membros_bim(estrutura)
    except bim.GeometriaIncoerente as exc:
        return {"status": "blocked", "detail": _erro_entregavel(exc)}
    destino = Path(run_dir) / "model" / "estrutura"
    destino.mkdir(parents=True, exist_ok=True)
    saida = bim.montar_3d(
        estrutura, str(destino),
        doc_name="%s-estrutura" % (normalized.get("project_id") or "casa"),
        timeout=options.timeout_seconds)
    return _build_3d(saida, membros, run_dir, manifest,
                     volume_puro=bim.quantitativo(membros)["vol_concreto_m3"])


def _emitir_modelo_3d(manifest, run_dir, normalized, options, result):
    """Hook 3D: dois modelos solidos, arquitetura e (desde o G13) estrutura.

    Separados pelo mesmo motivo do IFC: alvenaria e pilar dividem o mesmo plano
    de proposito, e um documento unico acusaria interpenetracao onde nao ha erro.
    Cada modelo e' conferido contra o SEU modelo neutro.
    """
    if not options.generate_3d:
        manifest["deliverables"]["model_3d"] = {"status": "not_requested"}
        return
    partes = {}
    for nome, montador in (("arquitetura", _modelo_3d_arquitetura),
                           ("estrutura", _modelo_3d_estrutura)):
        try:
            partes[nome] = montador(manifest, run_dir, normalized, options, result)
        except Exception as exc:                            # noqa: BLE001
            partes[nome] = {"status": "failed", "detail": _erro_entregavel(exc)}

    montados = [p for p in partes.values() if p.get("artifacts")]
    if not montados:
        motivo = (partes["estrutura"].get("detail")
                  or partes["arquitetura"].get("detail")
                  or "nenhum modelo 3D montado")
        status = ("blocked" if any(p["status"] == "blocked"
                                   for p in partes.values())
                  else "failed" if any(p["status"] == "failed"
                                       for p in partes.values())
                  else "not_available")
        manifest["deliverables"]["model_3d"] = {
            "status": status, "detail": motivo, "partes": partes}
        return
    registro = {
        "status": ("generated"
                   if all(p["status"] == "generated" for p in montados)
                   else "failed"),
        "artifacts": [caminho for p in montados for caminho in p["artifacts"]],
        "n_pecas_puro": sum(p.get("n_pecas_puro", 0) for p in montados),
        "partes": partes,
    }
    if registro["status"] != "generated":
        registro["detail"] = ("ao menos um dos modelos 3D diverge do modelo puro "
                              "ou acusa interpenetracao")
    manifest["deliverables"]["model_3d"] = registro


def register_casa_residencial_adapter() -> None:
    """Registra o adaptador residencial real no Project Loop."""
    from project_loop import register_adapter

    register_adapter(
        ADAPTER_NAME,
        run_casa_residencial,
        project_types=("residencial",),
        disciplines=DISCIPLINES,
        deliverables=DELIVERABLES,
        hooks={"drawings": _emitir_desenhos,
               "ifc": _emitir_ifc,
               "model_3d": _emitir_modelo_3d},
    )
