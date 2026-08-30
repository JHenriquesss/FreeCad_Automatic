# ============================================================================
# edificio_adapter.py - O QUE ESTE ADAPTADOR FAZ
# Tipologia 'edificio' do Project Loop. O G3 entregou a cadeia de calculo do
# edificio multipavimento (carga NBR 6120 -> laje -> viga continua -> pilar ->
# descida com alpha_n), mas `edificio_multipavimento` era uma ilha: nenhum
# modulo o importava e ele nao registrava adaptador, entao o Loop nao
# conseguia rodar um edificio de ponta a ponta. Este modulo e' a fronteira.
#
# O que ele NAO faz, e declara como tal no escopo (itens abertos da
# REVISAO-G3-MULTIPAVIMENTO, secao 10):
#
#   vento               -> a descida implementada e' GRAVITACIONAL;
#   desaprumo           -> 11.3.3.4.1 nao entra nos esforcos;
#   estabilidade_global -> nada alimenta gamma_z com dM_tot_d de multiplos
#                          pavimentos; estabilidade_b1b2 segue preso a 1 pav.;
#   alvenaria_estrutural-> bloqueada por fonte (NBR 16868 ausente do acervo);
#   fundacao            -> a descida entrega N_base, ninguem a dimensiona aqui;
#   vibracao_piso       -> aberto desde a auditoria de gaps do G2.
#
# Capacidade nao declarada e' capacidade que nao existe: o adaptador declara
# report e drawings, e nenhuma disciplina e' marcada 'passed' - aprovacao para
# obra continua sendo decisao de responsavel tecnico com ART.
#
# CONFERENCIA rotulo x geometria: a geometria comum do Loop (comprimento, vao)
# e os vaos da estrutura sao duas declaracoes do MESMO predio. Divergir e' erro
# de entrada; sem essa costura o Loop coordenaria um envelope e a estrutura
# calcularia outro, em silencio.
# ============================================================================
"""Adaptador da tipologia edificio: encadeia o G3 no Project Loop com estados
honestos para o que ainda nao e' calculado."""

from __future__ import annotations

import copy
from typing import Any

import edificio_multipavimento as em


ADAPTER_NAME = "edificio-multipavimento"
PROJECT_TYPES = ("edificio",)
DISCIPLINES = ("estrutura",)
DELIVERABLES = ("report", "drawings")
SCHEMA = "freecad-automatic/building-result"
SCHEMA_VERSION = 1

# Tolerancia da conferencia de envelope. 10 mm: abaixo disso e' arredondamento
# de digitacao do spec, acima e' outro predio.
TOL_ENVELOPE_M = 0.010

# Itens que este adaptador ainda NAO cobre em nenhuma hipotese. Ficam aqui para
# que o manifesto os PUBLIQUE em vez de omiti-los - ausencia silenciosa e' o que
# este framework trata como bug.
ESCOPO_NAO_COBERTO = (
    "alvenaria_estrutural",
    "fundacao",
    "vibracao_piso",
)

# Estes tres dependem do vento estar declarado no spec. Com Ca declarado saem
# calculados; sem ele continuam not_available, porque o Ca da NBR 6123 e' abaco
# e arbitrar um valor seria inventar acao de projeto.
ESCOPO_DEPENDE_DO_VENTO = (
    "vento",
    "desaprumo",
    "estabilidade_global",
    "deslocamento_lateral_els",
)


def _erro(code: str, detail: str, **ctx: Any) -> dict[str, Any]:
    registro = {"code": code, "detail": detail}
    if ctx:
        registro.update(ctx)
    return registro


def _escopo(com_vento: bool = False) -> dict[str, str]:
    escopo = {"superestrutura": "implemented",
              "aprovacao_legal": "not_claimed",
              "construction_readiness": "not_claimed"}
    for chave in ESCOPO_NAO_COBERTO:
        escopo[chave] = "not_available"
    for chave in ESCOPO_DEPENDE_DO_VENTO:
        escopo[chave] = "implemented" if com_vento else "not_available"
    return escopo


def _registro(status: str, com_vento: bool = False, **campos: Any) -> dict[str, Any]:
    registro = {"status": status, "native_atende": None, "reprovados": [],
                "gates": {}, "warnings": [], "artifacts": [],
                "scope": _escopo(com_vento), "errors": []}
    registro.update(campos)
    return registro


def _numero_positivo(valor: Any) -> bool:
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and valor > 0)


def _erros_de_forma(estrutura: Any) -> list[dict[str, Any]]:
    """Recusa a entrada malformada em vez de deixar o solver estourar fundo."""
    if not isinstance(estrutura, dict):
        return [_erro("invalid_structure_input",
                      "turnkey.estrutura deve ser um objeto JSON")]
    erros = []
    geo = estrutura.get("geometria")
    if not isinstance(geo, dict):
        erros.append(_erro("invalid_structure_input",
                           "estrutura.geometria deve ser um objeto JSON"))
    else:
        for eixo in ("vaos_x", "vaos_y"):
            vaos = geo.get(eixo)
            if not isinstance(vaos, list) or not vaos:
                erros.append(_erro("invalid_structure_input",
                                   "estrutura.geometria.%s deve ser uma lista "
                                   "nao vazia de vaos" % eixo, path=eixo))
            elif not all(_numero_positivo(v) for v in vaos):
                erros.append(_erro("invalid_structure_input",
                                   "todo vao de %s deve ser numerico > 0" % eixo,
                                   path=eixo))
        if not _numero_positivo(geo.get("pe_direito")):
            erros.append(_erro("invalid_structure_input",
                               "estrutura.geometria.pe_direito deve ser > 0",
                               path="pe_direito"))
    pavimentos = estrutura.get("pavimentos")
    if not isinstance(pavimentos, list) or not pavimentos:
        erros.append(_erro("invalid_structure_input",
                           "estrutura.pavimentos deve ser uma lista nao vazia, "
                           "do topo para a base"))
    else:
        for i, pav in enumerate(pavimentos):
            if not isinstance(pav, dict) or not pav.get("uso") or not pav.get("nome"):
                erros.append(_erro("invalid_structure_input",
                                   "cada pavimento precisa de 'nome' e 'uso'",
                                   path="pavimentos[%d]" % i))
    materiais = estrutura.get("materiais")
    if not isinstance(materiais, dict):
        erros.append(_erro("invalid_structure_input",
                           "estrutura.materiais deve declarar fck e fyk"))
    else:
        for chave in ("fck", "fyk"):
            if not _numero_positivo(materiais.get(chave)):
                erros.append(_erro("invalid_structure_input",
                                   "materiais.%s deve ser numerico > 0" % chave,
                                   path=chave))
    return erros


def _erros_de_envelope(estrutura: dict, turnkey: dict) -> list[dict[str, Any]]:
    """Rotulo x geometria: o envelope declarado x a soma dos vaos.

    A geometria comum e' o que o Loop usa para coordenar; os vaos sao o que a
    estrutura calcula. Se as duas divergem, uma delas esta errada e o projeto
    nao pode seguir escolhendo silenciosamente uma.
    """
    comum = turnkey.get("geometria") or turnkey.get("geometry") or {}
    if not isinstance(comum, dict):
        return []
    geo = estrutura["geometria"]
    erros = []
    for chave, eixo in (("comprimento", "vaos_x"), ("vao", "vaos_y")):
        declarado = comum.get(chave)
        if not _numero_positivo(declarado):
            continue
        somado = float(sum(geo[eixo]))
        if abs(float(declarado) - somado) > TOL_ENVELOPE_M:
            erros.append(_erro(
                "geometry_mismatch",
                "geometria.%s declarada (%.3f m) diverge da soma de %s "
                "(%.3f m)" % (chave, float(declarado), eixo, somado),
                path=chave, declarado=float(declarado), somado=somado))
    pe_comum = comum.get("pe_direito")
    if _numero_positivo(pe_comum):
        pe_estrutura = float(geo["pe_direito"])
        if abs(float(pe_comum) - pe_estrutura) > TOL_ENVELOPE_M:
            erros.append(_erro(
                "geometry_mismatch",
                "geometria.pe_direito declarado (%.3f m) diverge do pe-direito "
                "da estrutura (%.3f m)" % (float(pe_comum), pe_estrutura),
                path="pe_direito", declarado=float(pe_comum),
                somado=pe_estrutura))
    return erros


def _spec_do_calculo(estrutura: dict) -> dict[str, Any]:
    """Traduz o payload do spec para a entrada de edificio_multipavimento.

    Repassa APENAS o que o projetista declarou. Nenhum default de engenharia e'
    inventado aqui: o que falta, falta no orquestrador, que tem os seus.
    """
    calculo = {
        "geometria": copy.deepcopy(estrutura["geometria"]),
        "pavimentos": copy.deepcopy(estrutura["pavimentos"]),
        "materiais": copy.deepcopy(estrutura["materiais"]),
    }
    for opcional in ("laje", "viga", "parede_sobre_vigas",
                     "parede_sem_posicao_pp", "escada", "vento", "lajes_lisas"):
        if estrutura.get(opcional) is not None:
            calculo[opcional] = copy.deepcopy(estrutura[opcional])
    return calculo


def _registro_estrutura(estrutura: Any, turnkey: dict):
    com_vento = isinstance(estrutura, dict) and bool(estrutura.get("vento"))
    erros = _erros_de_forma(estrutura)
    if erros:
        return _registro("blocked", com_vento, errors=erros), None
    erros = _erros_de_envelope(estrutura, turnkey)
    if erros:
        return _registro("blocked", com_vento, errors=erros), None

    try:
        resultado = em.rodar(_spec_do_calculo(estrutura))
    except Exception as exc:                                # noqa: BLE001
        return _registro("failed", com_vento, errors=[_erro(
            "structure_run_failed", "%s: %s" % (type(exc).__name__, exc))]), None

    avisos = []
    if resultado["reprovados"]:
        avisos.append(_erro("structure_gates_failed",
                            "gates reprovados: %s"
                            % ", ".join(resultado["reprovados"]),
                            reprovados=list(resultado["reprovados"])))
    # A reducao de 6.12 e' exigencia normativa de REGISTRO, nao depuracao.
    avisos.append(_erro("reducao_6120_registrada", resultado["registro_6120"]))
    if not com_vento:
        avisos.append(_erro(
            "acao_horizontal_nao_avaliada",
            "estrutura.vento nao foi declarado: vento, desaprumo, gamma_z e "
            "deslocamento lateral nao foram avaliados. A descida e' apenas "
            "GRAVITACIONAL e o resultado nao fecha a estabilidade do edificio"))
    estab = resultado.get("estabilidade")
    if estab and estab["por_direcao"]["x"]["desaprumo"]["saturou"]:
        avisos.append(_erro(
            "desaprumo_saturou",
            "theta_1 saturou em %s (11.3.3.4.1)"
            % estab["por_direcao"]["x"]["desaprumo"]["saturou"]))

    registro = _registro(
        "needs_review", com_vento,
        native_atende=bool(resultado["ATENDE"]),
        reprovados=list(resultado["reprovados"]),
        gates=copy.deepcopy(resultado["gates"]),
        warnings=avisos)
    return registro, resultado


def run_edificio(normalized, run_dir, preflight=None):
    """Executa a estrutura do edificio e devolve (resultado, registros)."""
    del run_dir, preflight
    if not isinstance(normalized, dict):
        raise TypeError("normalized deve ser um objeto")
    turnkey = normalized.get("turnkey_spec")
    turnkey = turnkey if isinstance(turnkey, dict) else {}
    solicitadas = list(normalized.get("requested_disciplines") or DISCIPLINES)

    registros = {}
    disciplinas = {}
    resultado_estrutura = None

    if "estrutura" in solicitadas:
        payload = turnkey.get("estrutura")
        if payload is None:
            registros["estrutura"] = _registro("blocked", errors=[_erro(
                "missing_structure_input",
                "turnkey.estrutura nao foi declarado")])
        else:
            registros["estrutura"], resultado_estrutura = _registro_estrutura(
                payload, turnkey)
        disciplinas["estrutura"] = {
            "engine": "edificio_multipavimento",
            "status": registros["estrutura"]["status"]}

    resultado = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "adapter": ADAPTER_NAME,
        "synthetic_fixture": False,
        "project_id": normalized.get("project_id"),
        "disciplines": disciplinas,
        "estrutura": copy.deepcopy(resultado_estrutura),
        "scope": _escopo(bool(isinstance(turnkey.get("estrutura"), dict)
                             and turnkey["estrutura"].get("vento"))),
    }
    resultado["status"] = ("blocked" if any(
        r["status"] == "blocked" for r in registros.values()) else "needs_review")
    return resultado, registros


def _erro_entregavel(exc: Exception) -> str:
    return "%s: %s" % (type(exc).__name__, exc)


def _emitir_desenhos(manifest, run_dir, normalized, options, result):
    """Hook de desenhos: planta de formas do pavimento-tipo.

    Nao depende de FreeCAD - le o resultado ja calculado. Estrutura bloqueada
    vira motivo explicito no manifesto, nunca um SVG vazio que parece prancha.
    """
    from pathlib import Path

    import desenho_pavimento as dp
    from project_loop import _add_artifact

    del normalized
    if not (options.generate_2d or options.generate_caderno):
        manifest["deliverables"]["drawings"] = {"status": "not_requested"}
        return
    estrutura = result.get("estrutura") if isinstance(result, dict) else None
    if not isinstance(estrutura, dict):
        manifest["deliverables"]["drawings"] = {
            "status": "not_available",
            "detail": "estrutura nao calculada; sem pavimento para desenhar"}
        return
    destino = Path(run_dir) / "drawings"
    destino.mkdir(parents=True, exist_ok=True)
    nome = "planta-formas-pavimento-tipo.svg"
    try:
        dp.gerar_planta_formas(estrutura["pavimento"], str(destino / nome),
                               descida=estrutura["descida"])
    except Exception as exc:                                # noqa: BLE001
        manifest["deliverables"]["drawings"] = {
            "status": "failed", "detail": _erro_entregavel(exc)}
        return
    _add_artifact(manifest, run_dir, destino / nome, "drawing")
    manifest["deliverables"]["drawings"] = {
        "status": "generated",
        "artifacts": ["drawings/" + nome],
        "skipped": [],
    }


def register_edificio_adapter() -> None:
    """Registra a tipologia edificio no Project Loop."""
    from project_loop import register_adapter

    register_adapter(
        ADAPTER_NAME,
        run_edificio,
        project_types=PROJECT_TYPES,
        disciplines=DISCIPLINES,
        deliverables=DELIVERABLES,
        hooks={"drawings": _emitir_desenhos},
    )
