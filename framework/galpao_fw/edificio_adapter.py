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
#   alvenaria_estrutural-> bloqueada por fonte (NBR 16868 ausente do acervo).
#
# `vibracao_piso` DEIXOU de ser uma delas (G11): o ELS do Anexo L da NBR 8800 e o
# desempenho da NBR 15575 passam a ser calculados. O que continua fora sao os
# requisitos da 15575 que se verificam por ENSAIO e nao por conta - impacto de
# corpo mole/duro, a carga concentrada de 1 kN da parte 3 e o deslocamento
# residual de fachada da parte 4 - e eles ficam NOMEADOS no escopo.
#
# A FUNDACAO deixou de ser uma delas (G9): a descida sempre entregou N_base por
# pilar, e os modulos de calculo ja existiam aferidos. Ela passa a ser
# implemented QUANDO a sondagem (ou a tensao admissivel) e' DECLARADA - sem esse
# dado o escopo volta a dizer not_available, porque uma fundacao assentada numa
# tensao de solo arbitrada nao e' fundacao.
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
import gestao_edificio as ge


ADAPTER_NAME = "edificio-multipavimento"
PROJECT_TYPES = ("edificio",)
# G12: o predio saia calculado, desenhado e modelado - e legalmente inocupavel,
# porque nenhuma rota de abandono, nenhuma coluna de agua e nenhuma prumada
# eletrica eram dimensionadas. Cada disciplina nova entra por uma FRONTEIRA
# (incendio_edificio / hidraulica_edificio / eletrica_edificio) no mesmo formato
# do G9, e so aparece no resultado quando o spec a declara: turnkey.incendio,
# turnkey.hidraulica, turnkey.eletrico. Disciplina nao declarada e'
# not_requested, nunca um projeto inventado a partir do envelope.
DISCIPLINES = ("estrutura", "incendio", "hidraulica", "eletrico")
# A ordem dos extras e a ordem de execucao: o cronograma custeia as suas
# atividades com a planilha que o orcamento acabou de gravar (G14).
DELIVERABLES = ("report", "drawings", "ifc", "model_3d", "orcamento",
                "cronograma", "caderno_encargos", "pacote_legal")
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
)

# Requisitos da NBR 15575 que a norma verifica por ENSAIO em prototipo ou obra
# (15575-2 7.4 corpo mole/duro; 15575-3 Anexo B para a carga concentrada de
# 1 kN; 15575-4 Tabela 1 para o deslocamento residual de fachada). Nao sao
# calculaveis a partir do modelo, e por isso ficam publicados como ausentes em
# vez de embutidos num 'desempenho: implemented' que os cobriria por tabela.
ESCOPO_15575_ENSAIO = (
    "desempenho_15575_impacto_corpo_mole_duro",
    "desempenho_15575_carga_concentrada_piso",
    "desempenho_15575_fachada",
)

# Itens da fundacao publicados no escopo. `fundacao` vira implemented so com a
# sondagem declarada; os demais sao as fronteiras do que o G9 entrega, nomeadas
# em vez de omitidas (ver fundacao_edificio, nota de acao horizontal).
ESCOPO_FUNDACAO_DEPENDENTE = ("fundacao",)
ESCOPO_FUNDACAO_ABERTO = ("viga_baldrame", "recalque_diferencial")

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


def _escopo(com_vento: bool = False, com_fundacao: bool = False,
            com_momento: bool = False,
            instalacoes: dict | None = None) -> dict[str, str]:
    escopo = {"superestrutura": "implemented",
              "aprovacao_legal": "not_claimed",
              "construction_readiness": "not_claimed"}
    # G12: as tres disciplinas de instalacoes. Declarada no spec = implemented
    # (a fronteira roda e publica os seus proprios gates); nao declarada =
    # not_available, dito em voz alta em vez de omitido do escopo.
    for nome, _executor, _motor in _DISCIPLINAS_INSTALACOES:
        escopo[nome] = ("implemented" if (instalacoes or {}).get(nome)
                        else "not_available")
    for chave in ESCOPO_NAO_COBERTO:
        escopo[chave] = "not_available"
    # G11: ELS de vibracao (NBR 8800 11.4/Anexo L) e desempenho NBR 15575.
    escopo["vibracao_piso"] = "implemented"
    escopo["desempenho_15575"] = "implemented"
    for chave in ESCOPO_15575_ENSAIO:
        escopo[chave] = "not_available"
    for chave in ESCOPO_DEPENDE_DO_VENTO:
        escopo[chave] = "implemented" if com_vento else "not_available"
    for chave in ESCOPO_FUNDACAO_DEPENDENTE:
        escopo[chave] = "implemented" if com_fundacao else "not_available"
    for chave in ESCOPO_FUNDACAO_ABERTO:
        escopo[chave] = "not_available"
    # G17: momento na base por pilar deixa de ser not_available quando ha vento
    # (portico heterogeneo, secao bruta) – alimenta a fundacao com M_x/M_y por
    # prumada e distingue canto vs centro. Sem vento, segue not_available.
    escopo["momento_base_pilar"] = "implemented" if com_momento else "not_available"
    # G17: sapata de divisa / viga de equilibrio deixam de ser ignoradas – o
    # criterio e' a posicao do pilar (canto/extremidade vs interno) quando ha
    # momento. Publica a capacidade quando o momento existe.
    escopo["sapata_divisa"] = "implemented" if com_momento else "not_available"
    escopo["viga_equilibrio"] = "implemented" if com_momento else "not_available"
    return escopo


def _registro(status: str, com_vento: bool = False, com_fundacao: bool = False,
              com_momento: bool = False,
              **campos: Any) -> dict[str, Any]:
    registro = {"status": status, "native_atende": None, "reprovados": [],
                "gates": {}, "warnings": [], "artifacts": [],
                "scope": _escopo(com_vento, com_fundacao, com_momento), "errors": []}
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
    fundacao = estrutura.get("fundacao")
    if fundacao is not None and not isinstance(fundacao, dict):
        erros.append(_erro("invalid_structure_input",
                           "estrutura.fundacao deve ser um objeto JSON",
                           path="fundacao"))
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
                     "parede_sem_posicao_pp", "escada", "vento", "lajes_lisas",
                     "fundacao", "desempenho", "vibracao", "habitacional"):
        if estrutura.get(opcional) is not None:
            calculo[opcional] = copy.deepcopy(estrutura[opcional])
    return calculo


def _fundacao_declarada(estrutura: Any) -> bool:
    """A sondagem (ou a tensao assumida) esta declarada?

    Delegado a `fundacao_edificio.declarada` para que a pergunta tenha UMA
    resposta: o adaptador nao pode publicar 'implemented' com um criterio e o
    calculo pular a fundacao com outro.
    """
    import fundacao_edificio as fe

    return isinstance(estrutura, dict) and fe.declarada(estrutura.get("fundacao"))


def _registro_estrutura(estrutura: Any, turnkey: dict):
    com_vento = isinstance(estrutura, dict) and bool(estrutura.get("vento"))
    com_fundacao = _fundacao_declarada(estrutura)
    erros = _erros_de_forma(estrutura)
    if erros:
        return _registro("blocked", com_vento, com_fundacao, errors=erros), None
    erros = _erros_de_envelope(estrutura, turnkey)
    if erros:
        return _registro("blocked", com_vento, com_fundacao, errors=erros), None

    try:
        resultado = em.rodar(_spec_do_calculo(estrutura))
    except Exception as exc:                                # noqa: BLE001
        return _registro("failed", com_vento, com_fundacao, errors=[_erro(
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
    vib = resultado.get("vibracao") or {}
    if vib.get("aplicavel") and vib.get("avaliacao", "").startswith("simplificada"):
        # L.3.1 e' explicito: a via simplificada "pode nao constituir uma solucao
        # adequada para o problema". Atender 20/9/5 mm nao e' certificado de
        # conforto, e o manifesto nao pode deixar parecer que e'.
        avisos.append(_erro(
            "vibracao_avaliacao_simplificada",
            "o ELS de vibracao foi verificado pela via SIMPLIFICADA do Anexo L "
            "(deslocamento da combinacao frequente com as vigas biapoiadas). "
            "L.3.1: a opcao por esse tipo de avaliacao fica a criterio do "
            "projetista e pode nao constituir uma solucao adequada. A avaliacao "
            "precisa de L.2 (analise dinamica) nao e' feita aqui",
            d_total_mm=vib.get("d_total_mm"), d_lim_mm=vib.get("d_lim_mm")))
    dsp = resultado.get("desempenho") or {}
    if dsp.get("aplicavel") and not dsp.get("completo"):
        avisos.append(_erro(
            "desempenho_15575_incompleto",
            "edificacao HABITACIONAL: a NBR 15575 e' exigivel e estes requisitos "
            "NAO foram verificados (dado nao declarado ou verificacao por "
            "ensaio): %s" % ", ".join(dsp["nao_verificados"]),
            nao_verificados=list(dsp["nao_verificados"])))
    if not com_fundacao:
        avisos.append(_erro(
            "fundacao_nao_declarada",
            "estrutura.fundacao nao foi declarada (perfil_spt da sondagem ou "
            "sigma_solo_adm): a carga desce ate N_base e para ali. A tensao "
            "admissivel do solo nao e' arbitrada por este framework"))
    fundacao = resultado.get("fundacao")
    # G17: momento por pilar disponivel quando ha vento e o portico heterogeneo rodou
    momentos = resultado.get("momentos_base")
    com_momento = bool(com_vento and isinstance(momentos, dict)
                       and any(not k.startswith("_") for k in momentos)
                       and not momentos.get("_erro"))
    if resultado.get("fundacao_erro"):
        # entrada declarada que nao permite dimensionar: erro nomeado, nunca
        # uma fundacao que some do resultado sem explicacao.
        erros_fund = [_erro("foundation_input_rejected",
                            resultado["fundacao_erro"])]
        return _registro(
            "blocked", com_vento, com_fundacao, com_momento,
            native_atende=bool(resultado["ATENDE"]),
            reprovados=list(resultado["reprovados"]),
            gates=copy.deepcopy(resultado["gates"]),
            warnings=avisos, errors=erros_fund), resultado
    if fundacao:
        avisos.extend(_erro(item["code"], item["detail"])
                      for item in fundacao["avisos"])
        # se a fundacao ja trouxe momento, garante que o escopo do registro
        # reflita – o _avisos de fundacao ja publicou momento_base_pilar
        if fundacao.get("escopo", {}).get("momento_base_pilar") == "implemented":
            com_momento = True

    registro = _registro(
        "needs_review", com_vento, com_fundacao, com_momento,
        native_atende=bool(resultado["ATENDE"]),
        reprovados=list(resultado["reprovados"]),
        gates=copy.deepcopy(resultado["gates"]),
        warnings=avisos)
    if fundacao:
        registro["foundation"] = {
            "tipo": fundacao["tipo"],
            "sigma_solo_adm_kNm2": fundacao["sigma_solo_adm"],
            "proveniencia_sigma": fundacao["proveniencia_sigma"],
            "por_pilar": {nome: {"N_dimensionamento_kN": r["N_dimensionamento_kN"],
                                 "geometria": r["geometria"], "OK": r["OK"],
                                 "subtipo": r.get("subtipo"),
                                 "M_base_kNm": r.get("M_base_kNm"),
                                 "V_base_kN": r.get("V_base_kN"),
                                 "combinacoes": r.get("combinacoes")}
                          for nome, r in fundacao["por_pilar"].items()},
            "scope": copy.deepcopy(fundacao["escopo"]),
            "momentos_base": copy.deepcopy(momentos) if momentos else None,
        }
    # exposicao de momentos no registro da estrutura para auditoria
    if momentos and not momentos.get("_erro"):
        # resume por pilar para o manifesto (Mx, My, M_res)
        resumo = {nome: {"Mx_kNm": v.get("Mx_abs_kNm"),
                         "My_kNm": v.get("My_abs_kNm"),
                         "M_res_kNm": v.get("M_resultante_kNm"),
                         "posicao": v.get("posicao")}
                  for nome, v in momentos.items() if not nome.startswith("_")}
        registro["momentos_base_por_pilar"] = resumo
    return registro, resultado


def _registro_disciplina(status: str, escopo: dict, **campos: Any) -> dict[str, Any]:
    """Registro de uma disciplina nao-estrutural, com o ESCOPO da propria.

    O escopo do registro da estrutura descreve o que a estrutura cobre; publicar
    o mesmo escopo em incendio, hidraulica e eletrica faria o manifesto dizer
    'fundacao: implemented' num registro eletrico. Cada fronteira publica o seu.
    """
    registro = {"status": status, "native_atende": None, "reprovados": [],
                "gates": {}, "warnings": [], "artifacts": [],
                "scope": copy.deepcopy(escopo), "errors": []}
    registro.update(campos)
    return registro


def _contexto_predio(estrutura: dict, resultado,
                     instalacoes: dict | None = None) -> dict[str, Any]:
    """O predio como as disciplinas de instalacoes o enxergam.

    UMA leitura da geometria para as tres fronteiras: o envelope do pavimento, o
    pe-direito, a lista de pavimentos do topo para a base e a ESCADA como a
    estrutura a dimensionou. A escada viaja no contexto justamente para que a
    9077 verifique a largura DECLARADA em vez de propor outra.
    """
    geo = estrutura["geometria"]
    comprimento = float(sum(geo["vaos_x"]))
    largura = float(sum(geo["vaos_y"]))
    return {
        "pavimentos": [{"nome": pav["nome"], "uso": pav.get("uso")}
                       for pav in estrutura["pavimentos"]],
        "C": comprimento, "L": largura,
        "area_pavimento_m2": comprimento * largura,
        "pe_direito": float(geo["pe_direito"]),
        "escada": (resultado or {}).get("escada"),
        "H_total_m": (resultado or {}).get("H_total_m"),
        # a populacao do predio e' UMA: quando a NBR 9077 ja a calculou sobre os
        # dormitorios declarados, a hidraulica LE a mesma em vez de pedir uma
        # segunda declaracao que poderia divergir em silencio.
        "populacao_por_pavimento": (
            ((instalacoes or {}).get("incendio") or {})
            .get("populacao_por_pavimento")),
    }


def _sem_estrutura(disciplina: str, escopo: dict) -> dict[str, Any]:
    return _registro_disciplina("blocked", escopo, errors=[_erro(
        "structure_result_required",
        "a disciplina %s do edificio le a geometria, os pavimentos e a escada do "
        "resultado da estrutura; sem estrutura calculada nao ha predio a servir"
        % disciplina)])


def _registro_incendio(payload: Any, estrutura: Any, resultado, instalacoes=None):
    """Saidas de emergencia (NBR 9077:2025) sobre o predio ja calculado."""
    import incendio_edificio as ie

    escopo_vazio = {"populacao_nbr9077": "not_available",
                    "aprovacao_legal": "not_claimed",
                    "avcb": "not_claimed",
                    "construction_readiness": "not_claimed"}
    if not isinstance(estrutura, dict) or resultado is None:
        return _sem_estrutura("incendio", escopo_vazio), None
    if not ie.declarada(payload):
        return _registro_disciplina("blocked", escopo_vazio, errors=[_erro(
            "fire_input_not_declared",
            "turnkey.incendio precisa declarar 'pavimentos' (a atividade da "
            "Tabela 4 de cada pavimento) e 'velocidade_incendio' (Tabela 2). "
            "Nenhum dos dois tem default: sao classificacao de responsavel "
            "tecnico, e sem eles nao ha perfil de risco nem rota de saida")]), None
    contexto = _contexto_predio(estrutura, resultado)
    try:
        saida = ie.dimensiona(payload, contexto)
    except ie.EntradaIncendio as exc:
        return _registro_disciplina("blocked", escopo_vazio, errors=[_erro(
            "fire_input_rejected", str(exc))]), None
    except Exception as exc:                                # noqa: BLE001
        return _registro_disciplina("failed", escopo_vazio, errors=[_erro(
            "fire_run_failed", "%s: %s" % (type(exc).__name__, exc))]), None

    avisos = [_erro(item["code"], item["detail"]) for item in saida["avisos"]]
    if saida["reprovados"]:
        avisos.insert(0, _erro(
            "fire_gates_failed",
            "gates reprovados: %s" % ", ".join(saida["reprovados"]),
            reprovados=list(saida["reprovados"])))
    registro = _registro_disciplina(
        "needs_review", saida["escopo"],
        native_atende=bool(saida["ATENDE"]),
        reprovados=list(saida["reprovados"]),
        gates=copy.deepcopy(saida["gates"]),
        warnings=avisos)
    registro["fire"] = {
        "perfil_risco": saida["perfil_risco"],
        "ocupante": saida["ocupante"],
        "altura_edificacao_m": saida["altura_edificacao_m"],
        "populacao_total": saida["populacao_total"],
        "estrategia_abandono": saida["estrategia_abandono"],
    }
    return registro, saida


def _registro_hidraulica(payload: Any, estrutura: Any, resultado,
                         instalacoes=None):
    """Agua fria, esgoto e pluvial do predio (NBR 5626:2020 / 8160 / 10844)."""
    import hidraulica_edificio as he

    escopo_vazio = {"agua_fria_reservacao": "not_available",
                    "coluna_de_distribuicao": "not_available",
                    "aprovacao_legal": "not_claimed",
                    "construction_readiness": "not_claimed"}
    if not isinstance(estrutura, dict) or resultado is None:
        return _sem_estrutura("hidraulica", escopo_vazio), None
    if not he.declarada(payload):
        return _registro_disciplina("blocked", escopo_vazio, errors=[_erro(
            "hydraulic_input_not_declared",
            "turnkey.hidraulica precisa declarar 'consumo_per_capita_L_dia' e os "
            "aparelhos de uma unidade em 'unidade.aparelhos_agua'. A NBR "
            "5626:2020 6.5.4 NAO tabela consumo (ele vem de referencia tecnica, "
            "manual da concessionaria ou dado historico), e sem aparelhos nao ha "
            "vazao - um DN comercial plausivel nao e' projeto")]), None
    contexto = _contexto_predio(estrutura, resultado, instalacoes)
    try:
        saida = he.dimensiona(payload, contexto)
    except he.EntradaHidraulica as exc:
        return _registro_disciplina("blocked", escopo_vazio, errors=[_erro(
            "hydraulic_input_rejected", str(exc))]), None
    except Exception as exc:                                # noqa: BLE001
        return _registro_disciplina("failed", escopo_vazio, errors=[_erro(
            "hydraulic_run_failed", "%s: %s" % (type(exc).__name__, exc))]), None

    avisos = [_erro(item["code"], item["detail"]) for item in saida["avisos"]]
    if saida["reprovados"]:
        avisos.insert(0, _erro(
            "hydraulic_gates_failed",
            "gates reprovados: %s" % ", ".join(saida["reprovados"]),
            reprovados=list(saida["reprovados"])))
    registro = _registro_disciplina(
        "needs_review", saida["escopo"],
        native_atende=bool(saida["ATENDE"]),
        reprovados=list(saida["reprovados"]),
        gates=copy.deepcopy(saida["gates"]),
        warnings=avisos)
    registro["hydraulics"] = {
        "populacao": saida["populacao"],
        "populacao_proveniencia": saida["populacao_proveniencia"],
        "reservacao_total_L": saida["reservacao"]["total_L"],
        "consumo_diario_L": saida["reservacao"]["consumo_diario_L"],
        "coluna_DN_mm": saida["coluna"]["dn"]["DN_mm"],
    }
    return registro, saida


def _registro_eletrico(payload: Any, estrutura: Any, resultado, instalacoes=None):
    """Carga por unidade, quadro por pavimento, prumada e entrada (NBR 5410)."""
    import eletrica_edificio as ee

    escopo_vazio = {"previsao_de_carga_9_5_2": "not_available",
                    "prumada": "not_available",
                    "aprovacao_legal": "not_claimed",
                    "construction_readiness": "not_claimed"}
    if not isinstance(estrutura, dict) or resultado is None:
        return _sem_estrutura("eletrico", escopo_vazio), None
    if not ee.declarada(payload):
        return _registro_disciplina("blocked", escopo_vazio, errors=[_erro(
            "electrical_input_not_declared",
            "turnkey.eletrico precisa declarar a unidade-tipo "
            "('unidade.ambientes' para a previsao de carga da NBR 5410 9.5.2, ou "
            "'unidade.carga_VA') e a tensao ('tensao.sistema' e 'tensao.V'). A "
            "carga de um apartamento nao e' estimavel pela area do envelope "
            "estrutural")]), None
    contexto = _contexto_predio(estrutura, resultado, instalacoes)
    try:
        saida = ee.dimensiona(payload, contexto)
    except ee.EntradaEletrica as exc:
        return _registro_disciplina("blocked", escopo_vazio, errors=[_erro(
            "electrical_input_rejected", str(exc))]), None
    except Exception as exc:                                # noqa: BLE001
        return _registro_disciplina("failed", escopo_vazio, errors=[_erro(
            "electrical_run_failed", "%s: %s" % (type(exc).__name__, exc))]), None

    avisos = [_erro(item["code"], item["detail"]) for item in saida["avisos"]]
    if saida["reprovados"]:
        avisos.insert(0, _erro(
            "electrical_gates_failed",
            "gates reprovados: %s" % ", ".join(saida["reprovados"]),
            reprovados=list(saida["reprovados"])))
    registro = _registro_disciplina(
        "needs_review", saida["escopo"],
        native_atende=bool(saida["ATENDE"]),
        reprovados=list(saida["reprovados"]),
        gates=copy.deepcopy(saida["gates"]),
        warnings=avisos)
    registro["electrical"] = {
        "carga_por_unidade_VA": round(saida["carga_por_unidade"]["carga_VA"], 1),
        "carga_total_VA": saida["entrada"]["carga_total_VA"],
        "prumada_secao_mm2": saida["prumada"]["secao_mm2"],
        "dv_critica_pct": saida["prumada"]["dv_critica_pct"],
    }
    return registro, saida


# nome da disciplina no spec -> (funcao de registro, motor)
_DISCIPLINAS_INSTALACOES = (
    ("incendio", _registro_incendio, "incendio_edificio"),
    ("hidraulica", _registro_hidraulica, "hidraulica_edificio"),
    ("eletrico", _registro_eletrico, "eletrica_edificio"),
)


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

    # --- instalacoes: incendio, hidraulica e eletrica ----------------------
    # Cada uma so entra quando o spec a declara. Declarada e ausente do spec =
    # blocked com motivo nomeado; nao declarada = fora do resultado (o Loop ja
    # a marca not_requested). Falha de uma NAO derruba as outras.
    instalacoes = {}
    for nome, executor, motor in _DISCIPLINAS_INSTALACOES:
        if nome not in solicitadas:
            continue
        payload = turnkey.get(nome)
        if payload is None:
            registros[nome] = _registro_disciplina(
                "blocked", {"aprovacao_legal": "not_claimed"},
                errors=[_erro("missing_%s_input" % nome,
                              "turnkey.%s nao foi declarado" % nome)])
        else:
            registros[nome], instalacoes[nome] = executor(
                payload, turnkey.get("estrutura"), resultado_estrutura,
                instalacoes)
        disciplinas[nome] = {"engine": motor, "status": registros[nome]["status"]}

    com_vento_global = bool(isinstance(turnkey.get("estrutura"), dict)
                              and turnkey["estrutura"].get("vento"))
    com_fund_global = _fundacao_declarada(turnkey.get("estrutura"))
    com_momento_global = bool(
        com_vento_global and isinstance(resultado_estrutura, dict)
        and isinstance(resultado_estrutura.get("momentos_base"), dict)
        and any(not k.startswith("_") for k in resultado_estrutura["momentos_base"])
        and not resultado_estrutura["momentos_base"].get("_erro"))
    resultado = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "adapter": ADAPTER_NAME,
        "synthetic_fixture": False,
        "project_id": normalized.get("project_id"),
        "disciplines": disciplinas,
        "estrutura": copy.deepcopy(resultado_estrutura),
        "instalacoes": copy.deepcopy(instalacoes),
        "scope": _escopo(com_vento_global, com_fund_global, com_momento_global,
                         instalacoes),
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

    import desenho_concreto as dc
    import desenho_pavimento as dp
    from project_loop import _add_artifact

    del normalized
    if not (options.generate_2d or options.generate_caderno):
        manifest["deliverables"]["drawings"] = {"status": "not_requested"}
        return
    estrutura = result.get("estrutura") if isinstance(result, dict) else None
    if not isinstance(estrutura, dict):
        manifest["deliverables"]["drawings"] = _sem_geometria(
            result, "estrutura nao calculada; sem pavimento para desenhar")
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
    emitidas = ["drawings/" + nome]
    puladas = []
    # Planta da LAJE (formas + armadura + quadro de ferros). O edificio e a
    # tipologia que dimensiona laje; sem esta prancha o resultado da laje so
    # existia como numero no relatorio.
    laje = estrutura.get("laje")
    nome_laje = "planta-laje-pavimento-tipo.svg"
    if isinstance(laje, dict) and laje:
        try:
            dc.gerar_planta_laje(laje, str(destino / nome_laje))
        except Exception as exc:                            # noqa: BLE001
            puladas.append({"prancha": nome_laje, "motivo": _erro_entregavel(exc)})
        else:
            _add_artifact(manifest, run_dir, destino / nome_laje, "drawing")
            emitidas.append("drawings/" + nome_laje)
    else:
        puladas.append({"prancha": nome_laje,
                        "motivo": "laje nao dimensionada nesta rodada"})
    manifest["deliverables"]["drawings"] = {
        "status": "generated",
        "artifacts": emitidas,
        "skipped": puladas,
    }


def _estrutura_calculada(result):
    """O resultado da estrutura, ou None se a rodada nao produziu estrutura."""
    estrutura = result.get("estrutura") if isinstance(result, dict) else None
    return estrutura if isinstance(estrutura, dict) and estrutura else None


def _sem_geometria(result, detalhe: str) -> dict[str, Any]:
    """Registro de entregavel quando nao ha estrutura para desenhar/modelar.

    `blocked` e `not_available` NAO sao sinonimos neste framework: bloqueado e'
    entrada recusada, indisponivel e' capacidade que nao existe. Enquanto a
    tipologia so tinha a disciplina estrutura, uma rodada sem estrutura era
    curto-circuitada pelo Loop antes dos hooks e o entregavel saia `blocked` por
    tabela. Com o G12 a rodada CHEGA aos hooks (as instalacoes foram pedidas),
    e sem esta distincao o mesmo caso passaria a se anunciar como mera
    indisponibilidade - amaciando o estado de uma rodada recusada.
    """
    bloqueada = (isinstance(result, dict)
                 and (result.get("status") == "blocked"
                      or (result.get("disciplines") or {})
                      .get("estrutura", {}).get("status") in ("blocked", "failed")))
    return {"status": "blocked" if bloqueada else "not_available",
            "detail": detalhe}


def _emitir_ifc(manifest, run_dir, normalized, options, result):
    """Hook BIM: IFC4 do edificio, um IfcBuildingStorey por pavimento.

    Puro-Python (ifc_emit), sem FreeCAD - o caminho barato do roteiro de
    interoperabilidade, viavel aqui porque a malha do pavimento-tipo e' regular
    e ja esta calculada. Antes de publicar, o modelo e' CONFERIDO contra o
    calculo: contagem de pecas por tipo e ausencia de interpenetracao. Um IFC
    que perdeu pilares no caminho abre normalmente no visualizador e nao
    denuncia nada - so a contagem denuncia.
    """
    from pathlib import Path

    import bim_edificio as bim
    from project_loop import _add_artifact

    del normalized
    if not options.generate_ifc:
        manifest["deliverables"]["ifc"] = {"status": "not_requested"}
        return
    estrutura = _estrutura_calculada(result)
    if estrutura is None:
        manifest["deliverables"]["ifc"] = _sem_geometria(
            result, "estrutura nao calculada; sem geometria para o modelo")
        return
    try:
        import ifc_emit
        if not ifc_emit.disponivel():
            manifest["deliverables"]["ifc"] = {
                "status": "not_available", "detail": "ifcopenshell ausente"}
            return
        membros = bim.membros_bim(estrutura)
        conferencia = bim.confere_modelo(estrutura, membros)
        empilhamento = bim.confere_empilhamento(membros)
        destino = Path(run_dir) / "bim"
        destino.mkdir(parents=True, exist_ok=True)
        arquivo = destino / "edificio-estrutura.ifc"
        bim.emitir_bim(estrutura, str(arquivo))
    except bim.GeometriaIncoerente as exc:
        manifest["deliverables"]["ifc"] = {
            "status": "blocked", "detail": _erro_entregavel(exc)}
        return
    except Exception as exc:                                # noqa: BLE001
        manifest["deliverables"]["ifc"] = {
            "status": "failed", "detail": _erro_entregavel(exc)}
        return
    if not arquivo.is_file():
        manifest["deliverables"]["ifc"] = {
            "status": "not_available", "detail": "nenhum elemento BIM emitido"}
        return
    _add_artifact(manifest, run_dir, arquivo, "ifc", discipline="estrutura")
    registro = {
        "status": ("generated" if (conferencia["ok"] and empilhamento["OK"])
                   else "failed"),
        "artifacts": ["bim/edificio-estrutura.ifc"],
        "n_elementos": len(membros),
        "conferencia_modelo": conferencia,
        "interferencias": empilhamento["conflitos"],
        "quantitativo": bim.quantitativo(membros),
    }
    if registro["status"] == "failed":
        registro["detail"] = ("o modelo emitido nao reproduz o calculo "
                              "(contagem por tipo ou interpenetracao)")
    manifest["deliverables"]["ifc"] = registro


def _emitir_modelo_3d(manifest, run_dir, normalized, options, result):
    """Hook 3D: solidos no FreeCAD (FCStd + STEP + IFC) via build_concreto.

    O 3D responde a pergunta que o emissor puro nao responde - interferencia
    sobre SOLIDOS REAIS (OCCT common()), nao sobre caixas envolventes - e serve
    de CROSS-CHECK da geometria: as duas descricoes do mesmo predio tem de dar o
    mesmo numero de pecas e o mesmo volume de concreto.
    """
    from pathlib import Path

    import bim_edificio as bim
    from project_loop import _add_artifact

    if not options.generate_3d:
        manifest["deliverables"]["model_3d"] = {"status": "not_requested"}
        return
    estrutura = _estrutura_calculada(result)
    if estrutura is None:
        manifest["deliverables"]["model_3d"] = _sem_geometria(
            result, "estrutura nao calculada; sem geometria para o modelo")
        return
    destino = Path(run_dir) / "model"
    destino.mkdir(parents=True, exist_ok=True)
    try:
        saida = bim.montar_3d(
            estrutura, str(destino),
            doc_name=str(normalized.get("project_id") or "edificio"),
            timeout=options.timeout_seconds)
    except bim.GeometriaIncoerente as exc:
        manifest["deliverables"]["model_3d"] = {
            "status": "blocked", "detail": _erro_entregavel(exc)}
        return
    except Exception as exc:                                # noqa: BLE001
        manifest["deliverables"]["model_3d"] = {
            "status": "failed", "detail": _erro_entregavel(exc)}
        return
    if not isinstance(saida, dict) or saida.get("erro"):
        motivo = (saida or {}).get("erro", "o build nao devolveu resultado")
        # FreeCAD ausente e' indisponibilidade de AMBIENTE, nao falha do projeto
        indisponivel = any(t in str(motivo).lower() for t in
                           ("nao encontrado", "indisponivel", "ausente"))
        manifest["deliverables"]["model_3d"] = {
            "status": "not_available" if indisponivel else "failed",
            "detail": motivo}
        return
    modelo = saida.get("result") or {}
    artefatos = []
    for chave, kind in (("fcstd", "model-3d"), ("step", "model-3d"),
                        ("ifc", "ifc-freecad")):
        caminho = modelo.get(chave)
        if caminho and Path(caminho).is_file():
            artefatos.append(_add_artifact(manifest, run_dir, Path(caminho), kind))
    cruzamento = _cruzar_puro_com_freecad(bim.membros_bim(estrutura), modelo)
    registro = {
        "status": ("generated"
                   if artefatos and cruzamento["ok"]
                   and not modelo.get("interferencias") else "failed"),
        "artifacts": [item["path"] for item in artefatos],
        "interferencias": modelo.get("interferencias"),
        "cross_check_ifc_puro": cruzamento,
    }
    if registro["status"] == "failed":
        registro["detail"] = ("o 3D do FreeCAD diverge do modelo puro ou acusa "
                              "interpenetracao")
    manifest["deliverables"]["model_3d"] = registro


def _cruzar_puro_com_freecad(membros, modelo):
    """CROSS-CHECK: o 3D do FreeCAD x o modelo neutro que gerou o IFC.

    Sao duas descricoes da MESMA estrutura por caminhos independentes. Comparar
    numero de pecas e volume de concreto e' o que impede uma delas de envelhecer
    sem que ninguem perceba - foi assim que o galpao de aco travou as suas.
    """
    import bim_edificio as bim

    puro = bim.quantitativo(membros)
    n_freecad = modelo.get("elementos")
    vol_freecad = modelo.get("vol_concreto_m3")
    # 5 dm3 de tolerancia (0,0025% de um predio deste porte): os dois somam as
    # MESMAS caixas, so que em ordens diferentes e arredondando a 3 casas. Acima
    # disso ja nao e' arredondamento, e' geometria diferente.
    ok_volume = (vol_freecad is not None
                 and abs(float(vol_freecad) - puro["vol_concreto_m3"]) <= 0.005)
    return {
        "ok": bool(n_freecad == len(membros) and ok_volume),
        "n_pecas_puro": len(membros), "n_pecas_freecad": n_freecad,
        "vol_concreto_puro_m3": puro["vol_concreto_m3"],
        "vol_concreto_freecad_m3": vol_freecad,
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
        hooks={"drawings": _emitir_desenhos,
               "ifc": _emitir_ifc,
               "model_3d": _emitir_modelo_3d,
               "orcamento": ge.emitir_orcamento,
               "cronograma": ge.emitir_cronograma,
               "caderno_encargos": ge.emitir_caderno_encargos,
               "pacote_legal": ge.emitir_pacote_legal},
    )
