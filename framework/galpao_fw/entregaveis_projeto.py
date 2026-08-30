# ============================================================================
# entregaveis_projeto.py - A CAMADA DE ENTREGA (o que sai da rodada, alem do
# calculo). Reune os hooks de entregavel do Project Loop que NAO sao do nucleo
# (IFC/3D/desenhos/coordenacao) e que transformam o resultado do turnkey nos
# documentos que fazem um projeto ser ENTREGAVEL, nao so correto:
#   - orcamento        : planilha 5D + curva ABC (orcamento.py)
#   - cronograma       : rede CPM 4D + curva S, custeada pelo orcamento
#   - caderno_encargos : especificacoes tecnicas por disciplina
#   - pacote_legal     : indice de pranchas, ART, PPCI/AVCB, LOD, O&M, memorial
#   - obras_sitio      : terraplenagem/drenagem + esgoto/reuso (dados do SITIO)
#   - fotovoltaico     : FV na cobertura + comissionamento NBR 16274
#   - desenhos_concreto: pranchas SVG puro-Python do vertical de concreto
# NADA aqui calcula engenharia: todo numero vem dos modulos ja aferidos. Este
# modulo so decide QUANDO rodar, com QUE entrada, e grava o artefato no
# manifesto (com hash) - a alcancabilidade que faltava.
# Contrato do hook (o mesmo do nucleo):
#     hook(manifest, run_dir, normalized, options, turnkey_result) -> None
# e cada hook preenche manifest["deliverables"][<nome>].
# ============================================================================
"""Hooks dos entregaveis de gestao/sitio/desenho do adaptador de galpao."""

from __future__ import annotations

import json
from pathlib import Path

from project_loop import _add_artifact, _write_json


# ------------------------------- entrada do spec -----------------------------
def _bloco(normalized, secao, chave):
    """Le ``spec[secao][chave]`` como dict; {} quando ausente ou malformado.

    ``secao='site'`` usa o bloco de sitio ja normalizado; ``secao='gestao'`` le
    ``raw_spec['gestao']`` (o loop nao normaliza dados de gestao).
    """
    if secao == "gestao":
        raiz = (normalized.get("raw_spec") or {}).get("gestao")
    else:
        raiz = normalized.get(secao)
    if not isinstance(raiz, dict):
        return {}
    valor = raiz.get(chave)
    return dict(valor) if isinstance(valor, dict) else {}


def _nao_solicitado(manifest, nome, detalhe):
    manifest["deliverables"][nome] = {"status": "not_requested", "detail": detalhe}


def _dir(run_dir, nome):
    caminho = Path(run_dir) / nome
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def _texto(manifest, run_dir, caminho, conteudo, kind):
    Path(caminho).write_text(conteudo, encoding="utf-8")
    return _add_artifact(manifest, run_dir, caminho, kind)


def _json(manifest, run_dir, caminho, valor, kind):
    _write_json(Path(caminho), valor)
    return _add_artifact(manifest, run_dir, caminho, kind)


# --------------------------------- orcamento ---------------------------------
# De qual atividade do cronograma cada item do orcamento paga a conta. Serve
# APENAS para distribuir o custo na curva S; nao altera a planilha.
_CUSTO_POR_ATIVIDADE = {
    "fundacao_concreto": "fund", "estaca": "fund",
    "concreto_estrut": "estr", "aco_estrutural": "estr",
    "armadura": "estr", "forma": "estr",
    "telha_cobertura": "cob", "fechamento_lateral": "cob",
    "piso_industrial": "piso",
    "eletrica_ponto": "inst", "hidraulica_ponto": "inst",
}


def emitir_orcamento(manifest, run_dir, normalized, options, turnkey_result):
    """Planilha orcamentaria + curva ABC a partir dos quantitativos da rodada.

    Quantitativos derivados do turnkey; o que o usuario declarar em
    ``gestao.orcamento.quantitativos`` SOBREPOE o derivado (ele conhece a obra).
    Precos: tabela de REFERENCIA (A CONFIRMAR) salvo override em ``precos``.
    """
    import orcamento as orc

    cfg = _bloco(normalized, "gestao", "orcamento")
    quantitativos = orc.quantitativos_de_turnkey(turnkey_result)
    declarados = cfg.get("quantitativos")
    if isinstance(declarados, dict):
        quantitativos.update(declarados)
    if not quantitativos:
        _nao_solicitado(
            manifest, "orcamento",
            "sem quantitativos: nada derivavel das disciplinas executadas e nada "
            "declarado em gestao.orcamento.quantitativos")
        return

    precos = cfg.get("precos") if isinstance(cfg.get("precos"), dict) else None
    bdi = float(cfg.get("bdi_pct", orc.BDI_PADRAO_PCT))
    resultado = orc.compor_orcamento(quantitativos, precos, bdi)

    pasta = _dir(run_dir, "orcamento")
    artefatos = [
        _json(manifest, run_dir, pasta / "planilha.json", resultado["planilha"],
              "budget-sheet"),
        _json(manifest, run_dir, pasta / "curva-abc.json", resultado["abc"],
              "budget-abc"),
        _texto(manifest, run_dir, pasta / "relatorio.txt",
               orc.relatorio_pt(resultado) + "\n", "budget-report"),
    ]
    a_confirmar = [] if precos else [
        "precos unitarios da tabela de REFERENCIA - substituir pela SINAPI vigente "
        "(UF, data-base, regime de desoneracao)"]
    if "bdi_pct" not in cfg:
        a_confirmar.append("BDI de %.1f%% e o padrao do modulo - confirmar o da obra"
                           % bdi)
    # ORCAMENTO PARCIAL: os insumos sem quantitativo nesta rodada nao entram no
    # preco de venda. Sem isto o manifesto anunciava um orcamento "generated" que
    # podia cobrir um unico insumo - custo omitido lido como obra barata.
    faltando = resultado.get("sem_quantidade") or []
    if faltando:
        a_confirmar.append(
            "orcamento PARCIAL: %d insumo(s) da tabela sem quantitativo derivavel "
            "(%s) - completar em gestao.orcamento.quantitativos antes de usar o "
            "preco de venda" % (len(faltando), ", ".join(faltando)))
    if "aco_estrutural" in quantitativos and "aco_estrutural" not in (declarados or {}):
        a_confirmar.append(orc.NOTA_ACO_PRIMARIO)
    manifest["deliverables"]["orcamento"] = {
        "status": "generated",
        "artifacts": [item["path"] for item in artefatos],
        "custo_direto": resultado["planilha"]["custo_direto"],
        "preco_venda": resultado["planilha"]["preco_venda"],
        "bdi_pct": bdi,
        "codigos": sorted(quantitativos),
        "sem_preco": resultado["sem_preco"],
        "sem_quantidade": faltando,
        "cobertura_pct": resultado.get("cobertura_pct"),
        "a_confirmar": a_confirmar,
    }


# --------------------------------- cronograma --------------------------------
def emitir_cronograma(manifest, run_dir, normalized, options, turnkey_result):
    """Rede CPM (caminho critico) + curva S, custeada pelo orcamento da rodada.

    Roda DEPOIS do orcamento (ordem declarada em ``deliverables``): quando a
    planilha existe, cada item entra na atividade que o executa; sem planilha o
    cronograma sai so fisico (custo zero), o que o manifesto declara.
    """
    import cronograma as cr

    cfg = _bloco(normalized, "gestao", "cronograma")
    atividades = cfg.get("atividades")
    if atividades is not None and not isinstance(atividades, list):
        raise TypeError("gestao.cronograma.atividades deve ser uma lista")
    if atividades is None:
        atividades = [dict(item) for item in cr._WBS_GALPAO]

    custos = {}
    orcado = manifest["deliverables"].get("orcamento") or {}
    planilha = Path(run_dir) / "orcamento" / "planilha.json"
    if orcado.get("status") == "generated" and planilha.is_file():
        dados = json.loads(planilha.read_text(encoding="utf-8"))
        for linha in dados.get("linhas", []):
            atividade = _CUSTO_POR_ATIVIDADE.get(linha.get("codigo"))
            if atividade:
                custos[atividade] = custos.get(atividade, 0.0) + linha["custo"]
    if custos:
        atividades = cr.aplica_custos(atividades, custos)

    crono = cr.cronograma(atividades)
    curva = cr.curva_s(crono)
    pasta = _dir(run_dir, "cronograma")
    artefatos = [
        _json(manifest, run_dir, pasta / "cpm.json", crono, "schedule-cpm"),
        _json(manifest, run_dir, pasta / "curva-s.json", curva, "schedule-scurve"),
        _texto(manifest, run_dir, pasta / "curva-s.svg",
               cr.curva_s_svg(crono, curva), "schedule-scurve-svg"),
        _texto(manifest, run_dir, pasta / "relatorio.txt",
               cr.relatorio_pt(crono, curva) + "\n", "schedule-report"),
    ]
    # A curva S pesa o avanco FISICO pelo custo. Se so parte das atividades tem
    # custo, ela chega a 100% antes do fim da obra - e verdade sobre o dinheiro
    # conhecido, mentira sobre o cronograma fisico. Isso e declarado, nao mascarado
    # (nem se inventa custo para as atividades que o orcamento nao cobre).
    com_custo = sum(1 for item in crono["atividades"] if item["custo"])
    total = len(crono["atividades"])
    avisos = ([] if cfg.get("atividades") else
              ["duracoes do WBS-esqueleto do modulo - confirmar com o "
               "planejamento da obra"])
    if 0 < com_custo < total:
        avisos.append(
            "curva S custeada em %d de %d atividades: o avanco fisico e ponderado "
            "pelo custo, entao ele satura antes do fim da obra enquanto as demais "
            "atividades nao tiverem custo" % (com_custo, total))
    manifest["deliverables"]["cronograma"] = {
        "status": "generated",
        "artifacts": [item["path"] for item in artefatos],
        "duracao_total_dias": crono["duracao_total_dias"],
        "caminho_critico": crono["caminho_critico"],
        "custo_total": crono["custo_total"],
        "custeado_pelo_orcamento": bool(custos),
        "atividades_custeadas": com_custo,
        "atividades_totais": total,
        "a_confirmar": avisos,
    }


# ------------------------------ caderno de encargos --------------------------
def emitir_caderno_encargos(manifest, run_dir, normalized, options, turnkey_result):
    """Especificacoes tecnicas das disciplinas efetivamente executadas."""
    import caderno_encargos as ce

    cfg = _bloco(normalized, "gestao", "caderno_encargos")
    disciplinas = cfg.get("disciplinas")
    caderno = (ce.gerar_caderno(list(disciplinas)) if disciplinas
               else ce.caderno_de_turnkey(turnkey_result))
    pasta = _dir(run_dir, "documentos")
    artefatos = [
        _texto(manifest, run_dir, pasta / "caderno-encargos.md",
               ce.markdown(caderno) + "\n", "specification-book"),
        _json(manifest, run_dir, pasta / "caderno-encargos.json", caderno,
              "specification-book-data"),
    ]
    manifest["deliverables"]["caderno_encargos"] = {
        "status": "generated",
        "artifacts": [item["path"] for item in artefatos],
        "disciplinas": [secao["disciplina"] for secao in caderno["secoes"]],
        "n_clausulas": caderno["n_clausulas"],
        "normas_referenciadas": caderno["normas_referenciadas"],
    }


# --------------------------------- pacote legal ------------------------------
def emitir_pacote_legal(manifest, run_dir, normalized, options, turnkey_result):
    """Indice de pranchas, ART/RRT, PPCI/AVCB, LOD do BIM, O&M e memorial."""
    import pacote_legal as pl

    pacote = pl.gerar_pacote(R=turnkey_result, spec=normalized.get("turnkey_spec"))
    pasta = _dir(run_dir, "documentos")
    artefatos = [
        _texto(manifest, run_dir, pasta / "pacote-legal.md",
               pl.markdown(pacote) + "\n", "legal-package"),
        _json(manifest, run_dir, pasta / "pacote-legal.json", pacote,
              "legal-package-data"),
    ]
    manifest["deliverables"]["pacote_legal"] = {
        "status": "generated",
        "artifacts": [item["path"] for item in artefatos],
        "n_pranchas": len(pacote["indice_pranchas"]),
        "n_art": len(pacote["lista_art"]),
        "a_confirmar": ["responsavel tecnico (nome, CREA/CAU, numero da ART) nao e "
                        "inventado pelo modulo - preencher antes de protocolar"],
    }


# --------------------------------- obras do sitio ----------------------------
# Cada frente do sitio (corte/aterro, drenagem, esgoto, reuso) le um bloco de
# entrada DIFERENTE. Sem isolamento, um dado faltando numa frente descartava as
# outras JA calculadas e o manifesto so mostrava "KeyError: 'N'" - sem dizer de
# qual frente nem qual entrada. Mesmo principio do galpao_turnkey: falha isolada.
def _frente(falhas, nome, fn):
    """Executa uma frente do sitio; registra a falha em vez de propagar. None se falhou."""
    try:
        return fn()
    except KeyError as exc:
        falhas.append({"frente": nome, "erro": "entrada obrigatoria ausente: %s"
                       % exc.args[0], "codigo": "missing_input"})
    except Exception as exc:                            # noqa: BLE001
        falhas.append({"frente": nome,
                       "erro": "%s: %s" % (type(exc).__name__, exc),
                       "codigo": "frente_error"})
    return None


def emitir_obras_sitio(manifest, run_dir, normalized, options, turnkey_result):
    """Terraplenagem/drenagem e esgoto/reuso - dependem de DADOS DO SITIO.

    Sem ``site.terraplenagem`` nem ``site.saneamento`` no spec nao ha o que
    calcular (nem se inventa cota de terreno ou taxa de infiltracao): o
    entregavel fica ``not_requested``.
    """
    terra_cfg = _bloco(normalized, "site", "terraplenagem")
    san_cfg = _bloco(normalized, "site", "saneamento")
    if not terra_cfg and not san_cfg:
        _nao_solicitado(
            manifest, "obras_sitio",
            "sem site.terraplenagem/site.saneamento no spec (cota do terreno, IDF "
            "e taxa de infiltracao sao dados de sitio, nao default)")
        return

    resultado = {}
    falhas = []
    if terra_cfg:
        import terraplenagem as tp
        bloco = {}
        if terra_cfg.get("grid_terreno") is not None:
            def _movimento():
                corte = tp.volumes_corte_aterro(
                    terra_cfg["grid_terreno"], terra_cfg["cota_plataforma"],
                    terra_cfg["area_celula_m2"])
                saida = {"corte_aterro": corte,
                         "movimento_terra": tp.movimento_terra(
                             corte["corte_m3"], corte["aterro_m3"],
                             terra_cfg.get("empolamento", 1.0))}
                if terra_cfg.get("greide_equilibrio"):
                    saida["greide_equilibrio_m"] = tp.greide_equilibrio(
                        terra_cfg["grid_terreno"], terra_cfg["area_celula_m2"],
                        terra_cfg.get("empolamento", 1.0))
                return saida
            bloco.update(_frente(falhas, "corte_aterro", _movimento) or {})
        if terra_cfg.get("drenagem"):
            drenagem = _frente(falhas, "drenagem",
                               lambda: tp.dimensiona_drenagem(terra_cfg["drenagem"]))
            if drenagem is not None:
                bloco["drenagem"] = drenagem
        if bloco:
            resultado["terraplenagem"] = bloco
    if san_cfg:
        import esgoto_reuso as er
        bloco = {}
        if san_cfg.get("esgoto"):
            esgoto = _frente(falhas, "esgoto",
                             lambda: er.dimensiona_esgoto(san_cfg["esgoto"]))
            if esgoto is not None:
                bloco["esgoto"] = esgoto
        reuso = san_cfg.get("reuso")
        if reuso:
            cisterna = _frente(falhas, "reuso", lambda: er.cisterna_rippl(
                reuso["precip_mm_mes"], reuso["area_captacao_m2"],
                reuso["demanda_L_mes"],
                reuso.get("runoff", er.RUNOFF_TELHA_METALICA)))
            if cisterna is not None:
                bloco["reuso"] = cisterna
        if bloco:
            resultado["saneamento"] = bloco
    if not resultado:
        manifest["deliverables"]["obras_sitio"] = {
            "status": "failed",
            "detail": "nenhuma frente do sitio pode ser calculada",
            "frentes_com_falha": falhas,
        }
        return

    pasta = _dir(run_dir, "sitio")
    artefato = _json(manifest, run_dir, pasta / "obras-sitio.json", resultado,
                     "site-works")
    manifest["deliverables"]["obras_sitio"] = {
        "status": "generated" if not falhas else "partial",
        "artifacts": [artefato["path"]],
        "frentes": sorted(resultado),
        "frentes_com_falha": falhas,
        "a_confirmar": ["empolamento/compactacao, coeficiente de escoamento, IDF e "
                        "taxa de infiltracao sao ensaio/dado local (os coeficientes "
                        "da NBR 7229 e a IDF da cidade sao entrada)"],
    }


# --------------------------------- fotovoltaico ------------------------------
def emitir_fotovoltaico(manifest, run_dir, normalized, options, turnkey_result):
    """Sistema FV na cobertura + (quando ha evidencia) comissionamento NBR 16274.

    ``site.fotovoltaico`` e o caso de ``fotovoltaico.dimensiona_fv``; a area de
    cobertura, quando omitida, sai da geometria do galpao (vao x comprimento).
    """
    import comissionamento_fv as cfv
    import fotovoltaico as fv

    caso = _bloco(normalized, "site", "fotovoltaico")
    if not caso:
        _nao_solicitado(manifest, "fotovoltaico",
                        "sem site.fotovoltaico no spec (HSP do sitio e o consumo a "
                        "compensar sao dados do empreendimento)")
        return
    if not caso.get("area_cobertura_m2"):
        geometria = turnkey_result.get("geometria") or {}
        vao = geometria.get("vao")
        comprimento = geometria.get("comprimento")
        if vao and comprimento:
            caso["area_cobertura_m2"] = float(vao) * float(comprimento)
            caso["_area_derivada"] = True

    dimensionamento = fv.dimensiona_fv(caso)
    resultado = {"dimensionamento": dimensionamento}
    arranjo = caso.get("arranjo")
    if arranjo:
        resultado["arranjo"] = fv.validar_compatibilidade_arranjo_fv(arranjo)
    comissionamento = caso.get("comissionamento")
    if comissionamento:
        resultado["comissionamento"] = cfv.validar_comissionamento_fv(comissionamento)
    else:
        # Sem evidencia de campo nao se ATESTA nada: entrega-se o checklist a
        # preencher no comissionamento (NBR 16274), nunca um "APROVADO".
        resultado["comissionamento_checklist"] = \
            cfv.montar_checklist_comissionamento_fv()

    pasta = _dir(run_dir, "fotovoltaico")
    artefatos = [_json(manifest, run_dir, pasta / "fotovoltaico.json", resultado,
                       "pv-design")]
    if dimensionamento.get("OK"):
        artefatos.append(_texto(manifest, run_dir, pasta / "geracao.svg",
                                fv.grafico_svg(dimensionamento), "pv-chart"))
    manifest["deliverables"]["fotovoltaico"] = {
        "status": "generated" if dimensionamento.get("OK") else "not_available",
        "artifacts": [item["path"] for item in artefatos],
        "detail": dimensionamento.get("motivo"),
        "potencia_kWp": dimensionamento.get("potencia_kWp"),
        "geracao_kwh_mes": (dimensionamento.get("geracao") or {}).get("kwh_mes"),
        "comissionamento": ((resultado.get("comissionamento") or {}).get("status")
                            or "sem evidencia de campo (checklist emitido)"),
        "a_confirmar": (
            ["HSP (CRESESB/INPE da cidade) e catalogo de modulo/inversor"] +
            (["area de cobertura DERIVADA da projecao vao x comprimento (%.0f m2): "
              "nao desconta agua/inclinacao, shed, exaustores, claraboias nem "
              "sombreamento - informar site.fotovoltaico.area_cobertura_m2 real"
              % caso["area_cobertura_m2"]] if caso.get("_area_derivada") else [])),
    }


# ------------------------------ desenhos do concreto -------------------------
def emitir_desenhos_concreto(manifest, run_dir, normalized, options, turnkey_result):
    """Pranchas SVG puro-Python do vertical de concreto (sem FreeCAD).

    Formas + armacao do portico e a planta de juntas quando a rodada dimensionou
    o piso industrial.
    """
    concreto = (turnkey_result.get("disciplinas", {}) or {}).get("concreto") or {}
    bruto = concreto.get("raw")
    if not concreto.get("rodou") or not isinstance(bruto, dict):
        _nao_solicitado(manifest, "desenhos_concreto",
                        "disciplina de concreto nao executada nesta rodada")
        return

    import desenho_concreto as dc

    pasta = _dir(run_dir, "drawings-svg")
    artefatos = [
        _texto(manifest, run_dir, pasta / "concreto-armacao.svg",
               dc.prancha_armacao_svg(bruto), "drawing-svg"),
        _texto(manifest, run_dir, pasta / "concreto-formas.svg",
               dc.planta_formas_svg(bruto), "drawing-svg"),
    ]
    # (a planta de LAJE nao entra aqui: o galpao de portico nao tem laje. Ela e
    # emitida pelo adaptador do edificio multipavimento, que dimensiona lajes.)
    piso = bruto.get("piso")
    if isinstance(piso, dict) and piso.get("h_cm"):
        import desenho_piso as dp
        artefatos.append(_texto(manifest, run_dir, pasta / "piso-juntas.svg",
                                dp.planta_juntas_svg(piso), "drawing-svg"))

    manifest["deliverables"]["desenhos_concreto"] = {
        "status": "generated",
        "artifacts": [item["path"] for item in artefatos],
        "pranchas": [Path(item["path"]).name for item in artefatos],
    }
