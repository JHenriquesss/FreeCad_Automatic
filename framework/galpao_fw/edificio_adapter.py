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
#   alvenaria_estrutural-> o CALCULO existe desde o G60
#                          (alvenaria_estrutural.py, NBR 16868-1:2020 +
#                          Er1:2021: compressao 11.2, flexao 11.3.3, tetos
#                          de esbeltez da Tab.9). O que segue fora e a
#                          COSTURA no Loop: descida alimentando o Nd da
#                          parede, contraventamento por rigidez, BIM e
#                          pranchas - proximo lote, dito no escopo do
#                          modulo (bim_alvenaria/pranchas: not_available).
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
DELIVERABLES = ("report", "drawings", "ifc", "model_3d", "coordination",
                "orcamento", "cronograma", "caderno_encargos", "pacote_legal")
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
            instalacoes: dict | None = None,
            com_baldrame: bool = False,
            com_recalque: bool = False) -> dict[str, str]:
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
    # G18: viga baldrame e recalque deixam de ser not_available quando declarados.
    # Declarados = implemented (fronteira calculada); nao declarados = not_available
    # (capacidade publicada, mas nao calculada). Mesmo formato do G9/G12.
    escopo["viga_baldrame"] = "implemented" if com_baldrame else "not_available"
    escopo["recalque_diferencial"] = "implemented" if com_recalque else "not_available"
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
              com_baldrame: bool = False, com_recalque: bool = False,
              **campos: Any) -> dict[str, Any]:
    registro = {"status": status, "native_atende": None, "reprovados": [],
                "gates": {}, "warnings": [], "artifacts": [],
                "scope": _escopo(com_vento, com_fundacao, com_momento, None,
                                 com_baldrame, com_recalque), "errors": []}
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


def _baldrame_declarada(estrutura: Any) -> bool:
    """Viga baldrame declarada? Delega a `viga_baldrame_edificio.declarada`."""
    if not isinstance(estrutura, dict):
        return False
    try:
        import viga_baldrame_edificio as vbe
        return vbe.declarada(estrutura.get("fundacao"))
    except Exception:  # noqa: BLE001
        return False


def _recalque_declarada(estrutura: Any) -> bool:
    """Recalque diferencial declarado? Delega a `recalque_edificio.declarada`."""
    if not isinstance(estrutura, dict):
        return False
    try:
        import recalque_edificio as rce
        return rce.declarada(estrutura.get("fundacao"))
    except Exception:  # noqa: BLE001
        return False


def _registro_estrutura(estrutura: Any, turnkey: dict):
    com_vento = isinstance(estrutura, dict) and bool(estrutura.get("vento"))
    com_fundacao = _fundacao_declarada(estrutura)
    com_baldrame_decl = _baldrame_declarada(estrutura)
    com_recalque_decl = _recalque_declarada(estrutura)
    erros = _erros_de_forma(estrutura)
    if erros:
        return _registro("blocked", com_vento, com_fundacao,
                         com_momento=False,
                         com_baldrame=com_baldrame_decl,
                         com_recalque=com_recalque_decl,
                         errors=erros), None
    erros = _erros_de_envelope(estrutura, turnkey)
    if erros:
        return _registro("blocked", com_vento, com_fundacao,
                         com_momento=False,
                         com_baldrame=com_baldrame_decl,
                         com_recalque=com_recalque_decl,
                         errors=erros), None

    try:
        resultado = em.rodar(_spec_do_calculo(estrutura))
    except Exception as exc:                                # noqa: BLE001
        return _registro("failed", com_vento, com_fundacao,
                         com_momento=False,
                         com_baldrame=com_baldrame_decl,
                         com_recalque=com_recalque_decl,
                         errors=[_erro(
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
    baldrame = resultado.get("viga_baldrame")
    recalque = resultado.get("recalque_diferencial")
    baldrame_erro = resultado.get("viga_baldrame_erro")
    recalque_erro = resultado.get("recalque_erro")
    # D94/G59: sem declaracao o escopo diz not_available - e o motivo tem de
    # estar escrito aqui, como a casa faz (viga_baldrame_nao_declarada). Sem
    # isso, um baldrame nao declarado significa a alvenaria do terreo sem
    # caminho ate a fundacao (o achado do G13 na casa) em silencio.
    if baldrame is None and baldrame_erro is None:
        avisos.append(_erro(
            "viga_baldrame_nao_declarada",
            "estrutura.fundacao.viga_baldrame nao foi declarada (q_parede ou "
            "parede Tabela 2 da NBR 6120 + secao): o peso do fechamento do "
            "terreo NAO entra na fundacao (ele nao passa pelos pilares) e a "
            "reacao horizontal da base (N_amarracao, G23) fica sem caminho de "
            "amarracao. Carga de parede nao e' arbitrada por este framework"))
    if recalque is None and recalque_erro is None:
        avisos.append(_erro(
            "recalque_nao_declarado",
            "estrutura.fundacao.recalque nao foi declarado (Es do laudo ou "
            "perfil SPT para correlacao): o recalque total/diferencial NAO "
            "foi verificado. O modulo de deformabilidade do solo nao e' "
            "arbitrado por este framework"))
    # G17: momento por pilar disponivel quando ha vento e o portico heterogeneo rodou
    momentos = resultado.get("momentos_base")
    com_momento = bool(com_vento and isinstance(momentos, dict)
                       and any(not k.startswith("_") for k in momentos)
                       and not momentos.get("_erro"))
    # G18: baldrame e recalque viram implemented quando declarados e calculados
    # (ou quando ha erro nomeado, o scope ja diz implemented mas o status e' blocked)
    com_baldrame = bool(com_baldrame_decl and (baldrame is not None or baldrame_erro is not None))
    # Se nao ha erro nomeado, mas foi declarado e o calculo nao rodou (fundacao ausente),
    # ainda publica implemented para nao esconder a capacidade declarada que falhou.
    if com_baldrame_decl and not com_baldrame and fundacao is None:
        com_baldrame = True
    com_recalque = bool(com_recalque_decl and (recalque is not None or recalque_erro is not None))
    if com_recalque_decl and not com_recalque and fundacao is None:
        com_recalque = True
    # Se recalque foi calculado mas Es nao declarado, o modulo devolve gate com
    # motivo mas ainda conta como implemented (fronteira honesta: dado pedido, nao inventado)
    if recalque is not None and recalque.get("Es_kNm2") is None:
        # Es nao declarado: nao deveria contar como implemented, mas avisado
        # Mantem com_recalque como True para publicar not_available? Na verdade
        # recalque_declarada so e' True quando Es declarado, entao este ramo nao deve ocorrer.
        pass
    if resultado.get("fundacao_erro"):
        # entrada declarada que nao permite dimensionar: erro nomeado, nunca
        # uma fundacao que some do resultado sem explicacao.
        erros_fund = [_erro("foundation_input_rejected",
                            resultado["fundacao_erro"])]
        return _registro(
            "blocked", com_vento, com_fundacao, com_momento,
            com_baldrame=com_baldrame, com_recalque=com_recalque,
            native_atende=bool(resultado["ATENDE"]),
            reprovados=list(resultado["reprovados"]),
            gates=copy.deepcopy(resultado["gates"]),
            warnings=avisos, errors=erros_fund), resultado
    if baldrame_erro:
        erros_bld = [_erro("baldrame_input_rejected", baldrame_erro)]
        return _registro(
            "blocked", com_vento, com_fundacao, com_momento,
            com_baldrame=com_baldrame, com_recalque=com_recalque,
            native_atende=bool(resultado["ATENDE"]),
            reprovados=list(resultado["reprovados"]),
            gates=copy.deepcopy(resultado["gates"]),
            warnings=avisos, errors=erros_bld), resultado
    if recalque_erro:
        erros_rec = [_erro("recalque_input_rejected", recalque_erro)]
        return _registro(
            "blocked", com_vento, com_fundacao, com_momento,
            com_baldrame=com_baldrame, com_recalque=com_recalque,
            native_atende=bool(resultado["ATENDE"]),
            reprovados=list(resultado["reprovados"]),
            gates=copy.deepcopy(resultado["gates"]),
            warnings=avisos, errors=erros_rec), resultado
    if fundacao:
        avisos.extend(_erro(item["code"], item["detail"])
                      for item in fundacao["avisos"])
        # se a fundacao ja trouxe momento, garante que o escopo do registro
        # reflita – o _avisos de fundacao ja publicou momento_base_pilar
        if fundacao.get("escopo", {}).get("momento_base_pilar") == "implemented":
            com_momento = True
    # Avisos de baldrame e recalque (quando calculados)
    if baldrame:
        avisos.extend(_erro(item["code"], item["detail"])
                      for item in baldrame.get("avisos") or [])
    if recalque:
        avisos.extend(_erro(item["code"], item["detail"])
                      for item in recalque.get("avisos") or [])

    registro = _registro(
        "needs_review", com_vento, com_fundacao, com_momento,
        com_baldrame=com_baldrame, com_recalque=com_recalque,
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
    if baldrame:
        registro["viga_baldrame"] = {
            "secao": baldrame["secao"],
            "q_parede_kN_m": baldrame["q_parede_kN_m"],
            "N_amarracao_kN": baldrame["N_amarracao_kN"],
            "por_pilar": copy.deepcopy(baldrame["por_pilar"]),
            "verificacao": copy.deepcopy(baldrame["verificacao"]),
            "gate": copy.deepcopy(baldrame["gate"]),
            "scope": copy.deepcopy(baldrame["escopo"]),
        }
    if recalque:
        registro["recalque_diferencial"] = {
            "por_pilar": copy.deepcopy(recalque["por_pilar"]),
            "recalque_max_mm": recalque.get("recalque_max_mm"),
            "recalque_min_mm": recalque.get("recalque_min_mm"),
            "diferencial_mm": recalque.get("diferencial_mm"),
            "distorcao_L": recalque.get("distorcao_L"),
            "Es_kNm2": recalque.get("Es_kNm2"),
            "gate": copy.deepcopy(recalque["gate"]),
            "scope": copy.deepcopy(recalque["escopo"]),
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


def _resumo_incendio(saida: dict | None) -> dict[str, Any] | None:
    """O que a eletrica precisa saber do incendio (G57): qual carga essencial
    o incendio CRIA. Tipo de escada exigido (pressurizacao?), blocos autonomos
    da 10898 e presenca de hidrantes (bombas). So leitura, sem recalculo."""
    if not isinstance(saida, dict):
        return None
    sistemas = saida.get("sistemas") or {}
    gates = saida.get("gates") or {}
    ilum = sistemas.get("iluminacao_emergencia") or {}
    totais = sistemas.get("totais_edificio") or {}
    return {
        "tipo_escada_exigido": (gates.get("escada_tipo") or {}).get("tipo_exigido"),
        "blocos_por_pavimento": ilum.get("N_blocos_total"),
        "blocos_total_edificio": totais.get("blocos_autonomos"),
        "tem_hidrantes": sistemas.get("hidrantes") is not None,
    }


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
        # G57: a carga essencial da emergencia e' derivada do que o incendio
        # CRIA (tipo de escada, blocos da 10898, hidrantes) - o resumo viaja no
        # contexto para a eletrica ler em vez de pedir redigitacao.
        "incendio": _resumo_incendio((instalacoes or {}).get("incendio")),
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
        # G57: o portao do pacote legal le o escopo; o retrato vai junto para
        # quem consome o registro sem abrir o escopo.
        "spda_NP": (saida.get("spda") or {}).get("NP") if saida.get("spda") else None,
        "carga_essencial_VA": ((saida.get("emergencia") or {})
                               .get("carga_essencial_VA")
                               if saida.get("emergencia") else None),
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
    # G18: baldrame e recalque declarados no spec? O scope global publica o que foi
    # pedido, mas o registro da estrutura ja reflete o que foi CALCULADO (com
    # sucesso ou com erro nomeado). Para o manifesto global, usamos a declaracao.
    com_baldrame_global = _baldrame_declarada(turnkey.get("estrutura"))
    com_recalque_global = _recalque_declarada(turnkey.get("estrutura"))
    # Se a fundacao nao foi calculada, o baldrame/recalque nao tem como ser
    # implementado (falta base), mas o scope global ainda diz not_available
    # quando nao ha fundacao - capacidade declarada sem chao nao e' fundacao.
    if not com_fund_global:
        com_baldrame_global = False
        com_recalque_global = False
    # Se o resultado da estrutura ja tem o calculo, usa o estado REAL (implemented
    # vs blocked) para o scope global, em vez da mera declaracao.
    if isinstance(resultado_estrutura, dict):
        # baldrame: considera implemented quando ha resultado ou erro nomeado
        if resultado_estrutura.get("viga_baldrame") is not None or resultado_estrutura.get("viga_baldrame_erro"):
            com_baldrame_global = True
        elif com_baldrame_global and resultado_estrutura.get("viga_baldrame") is None and not resultado_estrutura.get("viga_baldrame_erro"):
            # declarado mas nao calculado (ex.: fundacao ausente) -> not_available
            com_baldrame_global = False
        if resultado_estrutura.get("recalque_diferencial") is not None or resultado_estrutura.get("recalque_erro"):
            com_recalque_global = True
        elif com_recalque_global and resultado_estrutura.get("recalque_diferencial") is None and not resultado_estrutura.get("recalque_erro"):
            com_recalque_global = False
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
                         instalacoes, com_baldrame_global, com_recalque_global),
    }
    resultado["status"] = ("blocked" if any(
        r["status"] == "blocked" for r in registros.values()) else "needs_review")
    return resultado, registros


def _erro_entregavel(exc: Exception) -> str:
    return "%s: %s" % (type(exc).__name__, exc)


def _emitir_desenhos(manifest, run_dir, normalized, options, result):
    """Hook de desenhos: as 13 pranchas do indice (G56).

    Nao depende de FreeCAD - le o resultado ja calculado. Estrutura bloqueada
    vira motivo explicito no manifesto, nunca um SVG vazio que parece prancha.
    Cada folha do indice que a rodada nao emitir aparece em `skipped` com o
    motivo: emitidas + puladas == len(indice_pranchas), o laco manifesto<->disco
    do G52 aplicado ao indice.
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
    # Prancha de ARMACAO DE VIGAS (G34). Toda viga, todo tramo verificado, com
    # As_inf/As_sup, estribos, ancoragem e flecha -- o executivo que faltava
    # para a armadura_viga sair do papel e ir para a obra.
    nome_vigas = "armacao-vigas-pavimento-tipo.svg"
    vv = estrutura.get("vigas_verificacao")
    if isinstance(vv, dict) and vv.get("por_linha"):
        try:
            dp.gerar_prancha_armacao_vigas(vv, str(destino / nome_vigas))
        except Exception as exc:                            # noqa: BLE001
            puladas.append({"prancha": nome_vigas, "motivo": _erro_entregavel(exc)})
        else:
            _add_artifact(manifest, run_dir, destino / nome_vigas, "drawing")
            emitidas.append("drawings/" + nome_vigas)
    else:
        puladas.append({"prancha": nome_vigas,
                        "motivo": "vigas nao verificadas nesta rodada "
                                  "(sem vigas_verificacao tramo a tramo)"})
    # Instalacoes (G56): eletrica, hidraulica e incendio calculam desde o G12
    # e tem posicao desde o G53 - e nao tinham uma folha sequer. Cada emissor
    # nasceu para o galpao (um pavimento); aqui sai por pavimento-tipo e com
    # o corte vertical das prumadas, por parametro, sem modulo paralelo.
    instalacoes = (result.get("instalacoes")
                   if isinstance(result, dict) else None) or {}
    _emitir_eletrica(manifest, run_dir, destino, estrutura, instalacoes,
                     emitidas, puladas)
    _emitir_hidraulica(manifest, run_dir, destino, estrutura, instalacoes,
                       emitidas, puladas)
    _emitir_incendio(manifest, run_dir, destino, estrutura, instalacoes,
                     emitidas, puladas)
    emit_c, pula_c = _emitir_coordenacao(manifest, run_dir, None,
                                         options, result)
    emitidas.extend(emit_c)
    puladas.extend(pula_c)
    # Laco indice<->disco: toda folha do indice tem de estar emitida ou nomeada
    # como pulada. O que nao puder sair, sai nomeado - nunca some.
    try:
        import gestao_edificio as ge
        import pacote_legal as pl

        indice = pl.indice_de_pranchas(ge.disciplinas_pacote(result) + ["coordenacao"])
        ja = {Path(a).name for a in emitidas}
        ja.update(p.get("prancha") for p in puladas if isinstance(p, dict))
        for folha in indice:
            esperado = _PRANCHA_ARQUIVO.get(folha["codigo"])
            if esperado and esperado not in ja:
                puladas.append({"prancha": esperado,
                                "motivo": "folha %s (%s) nao emitida nesta rodada"
                                          % (folha["codigo"], folha["titulo"])})
                ja.add(esperado)
    except Exception as exc:                                # noqa: BLE001
        # O laco e' a garantia de que nenhuma folha do indice evapora. Se ele
        # proprio falhar, a garantia cai -- e cair em silencio seria a
        # saturacao silenciosa vestida de rede de seguranca. O manifesto diz
        # que a conferencia nao aconteceu, com o erro nomeado.
        puladas.append({"prancha": "(indice)",
                        "motivo": "laco indice<->disco nao pode ser conferido: "
                                  + _erro_entregavel(exc)})
    manifest["deliverables"]["drawings"] = {
        "status": "generated",
        "artifacts": emitidas,
        "skipped": puladas,
    }


# codigo do indice (pacote_legal) -> arquivo em drawings/. A coordenacao tem
# folha (PE-CD-01, a projecao do federado com clashes), nao a matriz: a matriz
# sai com kind coordination-matrix e nao conta no laco do indice.
_PRANCHA_ARQUIVO = {
    "PE-CO-01": "planta-formas-pavimento-tipo.svg",
    "PE-CO-02": "armacao-vigas-pavimento-tipo.svg",
    "PE-CO-03": "planta-laje-pavimento-tipo.svg",
    "PE-EL-01": "eletrica-unifilar-prumada.svg",
    "PE-EL-02": "eletrica-planta-pavimento-tipo.svg",
    "PE-EL-03": "eletrica-infra-aterramento.svg",
    "PE-EL-04": "eletrica-qdc-quadros.svg",
    "PE-HI-01": "hidraulica-agua-fria.svg",
    "PE-HI-02": "hidraulica-esgoto-ventilacao.svg",
    "PE-HI-03": "hidraulica-pluvial.svg",
    "PE-IN-01": "incendio-ppci-pavimento-tipo.svg",
    "PE-IN-02": "incendio-detalhes-hidrantes-rotas.svg",
    "PE-CD-01": "coordenacao-federado.svg",
}


def _emitir_uma(manifest, run_dir, destino, nome, fn, emitidas, puladas):
    """Emite uma prancha via fn(path); falha vira pulada nomeada, nunca some."""
    from project_loop import _add_artifact

    try:
        fn(str(destino / nome))
    except Exception as exc:                                # noqa: BLE001
        puladas.append({"prancha": nome, "motivo": _erro_entregavel(exc)})
        return
    if not (destino / nome).is_file():
        puladas.append({"prancha": nome,
                        "motivo": "emissor nao gravou o arquivo"})
        return
    _add_artifact(manifest, run_dir, destino / nome, "drawing")
    emitidas.append("drawings/" + nome)


def _emitir_eletrica(manifest, run_dir, destino, estrutura, instalacoes,
                     emitidas, puladas):
    """PE-EL-01..04: unifilar da prumada, planta do pavimento-tipo,
    infraestrutura/aterramento e QDC - tudo do eletrica_edificio calculado."""
    import desenho_eletrico as de

    ele = instalacoes.get("eletrico")
    nomes = ["eletrica-unifilar-prumada.svg",
             "eletrica-planta-pavimento-tipo.svg",
             "eletrica-infra-aterramento.svg",
             "eletrica-qdc-quadros.svg"]
    if not isinstance(ele, dict) or not ele:
        for nome in nomes:
            puladas.append({"prancha": nome,
                            "motivo": "eletrica nao calculada nesta rodada"})
        return
    _emitir_uma(manifest, run_dir, destino, nomes[0],
                lambda p: de.gerar_prumada_edificio(ele, estrutura, p),
                emitidas, puladas)
    _emitir_uma(manifest, run_dir, destino, nomes[1],
                lambda p: de.gerar_planta_pavimento_edificio(ele, estrutura, p),
                emitidas, puladas)
    _emitir_uma(manifest, run_dir, destino, nomes[2],
                lambda p: de.gerar_infra_edificio(ele, estrutura, p),
                emitidas, puladas)
    _emitir_uma(manifest, run_dir, destino, nomes[3],
                lambda p: de.gerar_qdc_edificio(ele, estrutura, p),
                emitidas, puladas)


def _emitir_hidraulica(manifest, run_dir, destino, estrutura, instalacoes,
                       emitidas, puladas):
    """PE-HI-01..03: uma folha por rede (agua fria, esgoto/ventilacao, pluvial),
    cada uma com planta do pavimento-tipo + corte vertical da prumada."""
    import desenho_hidraulica as dh

    hid = instalacoes.get("hidraulica")
    folhas = [("hidraulica-agua-fria.svg", "agua"),
              ("hidraulica-esgoto-ventilacao.svg", "esgoto"),
              ("hidraulica-pluvial.svg", "pluvial")]
    if not isinstance(hid, dict) or not hid:
        for nome, _rede in folhas:
            puladas.append({"prancha": nome,
                            "motivo": "hidraulica nao calculada nesta rodada"})
        return
    for nome, rede in folhas:
        if rede == "esgoto" and not hid.get("esgoto"):
            puladas.append({"prancha": nome,
                            "motivo": "tubo de queda nao dimensionado "
                                      "(sem aparelhos de esgoto declarados)"})
            continue
        _emitir_uma(manifest, run_dir, destino, nome,
                    lambda p, r=rede: dh.gerar_rede_edificio(
                        hid, estrutura, p, rede=r),
                    emitidas, puladas)


def _emitir_incendio(manifest, run_dir, destino, estrutura, instalacoes,
                     emitidas, puladas):
    """PE-IN-01..02: PPCI do pavimento-tipo + detalhes de hidrantes/rotas."""
    import desenho_incendio as di

    inc = instalacoes.get("incendio")
    nomes = ["incendio-ppci-pavimento-tipo.svg",
             "incendio-detalhes-hidrantes-rotas.svg"]
    if not isinstance(inc, dict) or not inc:
        for nome in nomes:
            puladas.append({"prancha": nome,
                            "motivo": "incendio nao calculado nesta rodada"})
        return
    _emitir_uma(manifest, run_dir, destino, nomes[0],
                lambda p: di.gerar_ppci_pavimento(inc, estrutura, p),
                emitidas, puladas)
    _emitir_uma(manifest, run_dir, destino, nomes[1],
                lambda p: di.gerar_detalhes_hidrantes(inc, estrutura, p),
                emitidas, puladas)


def _emitir_coordenacao(manifest, run_dir, normalized, options, result):
    """PE-CD-01: a projecao do federado com os clashes marcados (a prancha que
    o galpao ja emite), registrada com kind drawing para contar no indice.

    Devolve (emitidas, puladas). Sem geometria de instalacao, motivo nomeado
    em vez de prancha vazia."""
    from pathlib import Path

    import bim_instalacoes_edificio as bie
    import desenho_coordenacao as dc
    from project_loop import _add_artifact

    nome = "coordenacao-federado.svg"
    estrutura = (result.get("estrutura")
                 if isinstance(result, dict) else None)
    instalacoes = (result.get("instalacoes")
                   if isinstance(result, dict) else None) or {}
    if not isinstance(estrutura, dict) or not estrutura:
        return [], [{"prancha": nome,
                     "motivo": "estrutura nao calculada; sem federado"}]
    tem_instalacao = any(isinstance(v, dict) and v
                         for v in instalacoes.values())
    if not tem_instalacao:
        return [], [{"prancha": nome,
                     "motivo": "sem geometria de instalacao; nenhuma disciplina "
                               "de instalacao calculada nesta rodada"}]
    try:
        fed, _disc = bie.membros_federados_edificio(estrutura, instalacoes)
        clash = bie.checa_interferencia_edificio(estrutura, instalacoes)
    except Exception as exc:                                # noqa: BLE001
        return [], [{"prancha": nome, "motivo": _erro_entregavel(exc)}]
    if not fed:
        return [], [{"prancha": nome,
                     "motivo": "federado vazio; sem membros para projetar"}]
    destino = Path(run_dir) / "drawings"
    destino.mkdir(parents=True, exist_ok=True)
    try:
        dc.gerar_prancha(fed, clash, str(destino / nome),
                         titulo="COORDENACAO - MODELO FEDERADO DO EDIFICIO")
    except Exception as exc:                                # noqa: BLE001
        return [], [{"prancha": nome, "motivo": _erro_entregavel(exc)}]
    if manifest is not None:
        _add_artifact(manifest, run_dir, destino / nome, "drawing")
    return ["drawings/" + nome], []


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
    # G53: federado estrutura + instalacoes no MESMO frame + clash. As
    # instalacoes saem do `result['instalacoes']` que run_edificio ja guarda;
    # sem elas, o federado e' so a estrutura e o clash sai vazio (honesto).
    try:
        import bim_instalacoes_edificio as bie

        inst = (result.get("instalacoes")
                if isinstance(result, dict) else None) or {}
        fed, disc_fed = bie.membros_federados_edificio(estrutura, inst)
        clash = bie.checa_interferencia_edificio(estrutura, inst)
        fed_path = destino / "edificio-federado.ifc"
        ifc_emit.emitir_ifc(fed, str(fed_path), nome="EdificioFederado",
                            pavimentos=bim.pavimentos_ifc(
                                estrutura, bim._pe_direito(
                                    estrutura["pilares"])))
        if fed_path.is_file():
            _add_artifact(manifest, run_dir, fed_path, "ifc",
                          discipline="federado")
            registro["artifacts"].append("bim/edificio-federado.ifc")
            registro["federado"] = {
                "n_membros": len(fed), "disciplinas": disc_fed,
                "n_clashes": clash["n_clashes"],
                "por_par": clash["por_par"],
                "clashes": clash["clashes"][:50],
            }
    except Exception as exc:                                # noqa: BLE001
        registro["federado_erro"] = _erro_entregavel(exc)
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


def _write_coordination(manifest, run_dir, normalized, options, turnkey_result):
    """Hook de compatibilizacao: clash instalacoes x estrutura no mesmo frame.

    Reuso quase total do caminho do galpao (compatibilizacao + matriz/BCF), com
    o motor do G53 (`bim_instalacoes_edificio.checa_interferencia_edificio`).
    A guarda e' a diferenca: sem geometria de instalacao nao ha federado para
    coordenar, e a rodada devolve `not_available` em vez de um relatorio vazio
    com zero conflitos que pareceria um predio coordenado.
    """
    import copy as _copy
    from pathlib import Path as _Path

    from project_loop import _add_artifact, _write_json

    del normalized
    policy = _copy.deepcopy(manifest.get("coordination_policy") or {
        "enabled": True,
        "folga_mm": options.folga_mm,
        "vol_min_mm3": options.vol_min_mm3,
        "resolution_mode": "manual_approval",
    })
    if policy.get("enabled") is False:
        manifest["coordination"] = {
            "status": "disabled",
            "open": 0,
            "n_clashes": 0,
            "n_revisar": 0,
            "policy": policy,
            "resolution_requests": (manifest.get("coordination") or {}).get(
                "resolution_requests", []),
        }
        return

    estrutura = (turnkey_result.get("estrutura")
                 if isinstance(turnkey_result, dict) else None)
    instalacoes = (turnkey_result.get("instalacoes")
                   if isinstance(turnkey_result, dict) else None)
    if not isinstance(estrutura, dict) or not estrutura:
        manifest["coordination"] = {
            "status": "not_available",
            "open": 0,
            "n_clashes": 0,
            "n_revisar": 0,
            "policy": policy,
            "resolution_requests": (manifest.get("coordination") or {}).get(
                "resolution_requests", []),
            "detail": "estrutura nao calculada; sem geometria para compatibilizar",
        }
        return
    tem_instalacao = (isinstance(instalacoes, dict)
                      and any(isinstance(v, dict) and v
                              for v in instalacoes.values()))
    if not tem_instalacao:
        manifest["coordination"] = {
            "status": "not_available",
            "open": 0,
            "n_clashes": 0,
            "n_revisar": 0,
            "policy": policy,
            "resolution_requests": (manifest.get("coordination") or {}).get(
                "resolution_requests", []),
            "detail": ("sem geometria de instalacao; nenhuma disciplina de "
                       "instalacao calculada nesta rodada"),
        }
        return

    import bim_instalacoes_edificio as bie
    import compatibilizacao as cp

    try:
        _fed, disc_fed = bie.membros_federados_edificio(
            estrutura, instalacoes)
    except Exception:
        _fed, disc_fed = [], ["estrutura"]
    if len([d for d in (disc_fed or []) if d != "estrutura"]) == 0:
        manifest["coordination"] = {
            "status": "not_available",
            "open": 0,
            "n_clashes": 0,
            "n_revisar": 0,
            "policy": policy,
            "resolution_requests": (manifest.get("coordination") or {}).get(
                "resolution_requests", []),
            "detail": ("sem geometria de instalacao; o federado tem so a "
                       "estrutura e nao ha par entre disciplinas para o clash"),
        }
        return

    coordination_dir = _Path(run_dir) / "coordination"
    coordination_dir.mkdir(parents=True, exist_ok=True)
    report = bie.checa_interferencia_edificio(
        estrutura, instalacoes,
        folga=policy.get("folga_mm", options.folga_mm),
        vol_min=policy.get("vol_min_mm3", options.vol_min_mm3))
    # G55: geometria declarada do cruzamento (transversal x longitudinal) -
    # sem ela, BeamxPipe nao distingue furo de conflito. So Beam/Slab ganham
    # hint; pilar/fundacao/caixa seguem conflito.
    hints = bie.cruzamentos_edificio(_fed, report)
    pendencias = cp.gerar_pendencias(report, cruzamentos=hints)
    # G55: resolucoes registradas fecham furos (com aprovador+justificativa).
    # Request invalida (sem justificativa, de reprovado/conflito) LEVANTA e o
    # hook vira failed - aprovar sem lastro nao pode passar em silencio.
    reqs = (manifest.get("coordination") or {}).get("resolution_requests", [])
    pendencias = cp.aplicar_resolucoes(pendencias, reqs)
    summary = cp.resumo(pendencias)
    _write_json(coordination_dir / "clash.json", report)
    _write_json(coordination_dir / "pendencias.json", pendencias)
    _write_json(coordination_dir / "pendencias.bcf.json", cp.bcf_topics(pendencias))
    (coordination_dir / "matriz.svg").write_text(
        cp.matriz_svg(report, pendencias), encoding="utf-8")
    (coordination_dir / "relatorio.txt").write_text(
        bie.relatorio_pt(report) + "\n\n" + cp.relatorio_pt(pendencias, summary),
        encoding="utf-8")
    manifest["coordination"] = {
        "status": "generated",
        "n_membros": report.get("n_membros", 0),
        "n_clashes": report.get("n_clashes", 0),
        "n_revisar": summary.get("abertas", 0),
        "n_esperado": report.get("n_esperado", 0),
        "n_resolvidas": summary.get("resolvidas", 0),
        "open": summary.get("abertas", 0),
        "OK": cp.gate_ok(pendencias),
        "OK_revisar": cp.gate_ok(pendencias),
        "disciplinas": list(disc_fed or []),
        "policy": policy,
        "resolution_requests": (manifest.get("coordination") or {}).get(
            "resolution_requests", []),
    }
    for relative, kind in (
        ("coordination/clash.json", "clash-report"),
        ("coordination/pendencias.json", "coordination-issues"),
        ("coordination/pendencias.bcf.json", "bcf-topics"),
        ("coordination/matriz.svg", "coordination-matrix"),
        ("coordination/relatorio.txt", "coordination-report"),
    ):
        _add_artifact(manifest, run_dir, _Path(run_dir) / relative, kind)


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
               "coordination": _write_coordination,
               "ifc": _emitir_ifc,
               "model_3d": _emitir_modelo_3d,
               "orcamento": ge.emitir_orcamento,
               "cronograma": ge.emitir_cronograma,
               "caderno_encargos": ge.emitir_caderno_encargos,
               "pacote_legal": ge.emitir_pacote_legal},
    )
