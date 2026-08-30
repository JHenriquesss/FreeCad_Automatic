# ============================================================================
# descida_cargas.py - O QUE ESTE SCRIPT FAZ / CALCULA
# DESCIDA DE CARGAS do edificio multipavimento: empilha os pavimentos-tipo, soma
# pavimento a pavimento a carga que cada pilar recebe e entrega, para cada PILAR,
# a lista de LANCES pronta para o `pilar_continuo` - e para a fundacao, a forca
# normal na base.
#
#   1) SUPERPOSICAO g / q: `pavimento_tipo` devolve a reacao de cada pilar separada
#      em permanente (N_g) e variavel (N_q). A separacao nao e um detalhe: a reducao
#      do item 6.12 da NBR 6120 incide APENAS sobre a parcela variavel. Reduzir a
#      reacao total reduziria tambem o peso proprio - o que a norma nao permite e
#      nenhum gate de flexo-compressao acusaria.
#   2) MULTIPLICADOR alpha_n (NBR 6120 6.12 / Tab.19): cada pavimento recebe o seu
#      proprio multiplicador conforme a posicao na contagem descendente do grupo de
#      pisos adjacentes de mesmo uso, e a carga acumulada e a soma das parcelas ja
#      multiplicadas piso a piso (ver cargas_nbr6120.multiplicadores_pavimentos).
#      Pavimento de carga NAO REDUTIVEL entra com alpha = 1,0 e nao interrompe a
#      sequencia do grupo.
#   3) REGISTRO: "as reducoes adotadas devem ser registradas nos documentos do
#      projeto" (6.12). O registro sai no relatorio, nao so no calculo.
#
# GATE PROPRIO (o mesmo padrao da saturacao silenciosa): a reducao de 6.12 e uma
# BONIFICACAO, nao uma verificacao - ela so faz o pilar ficar mais leve. Se for
# aplicada onde a norma nao permite (garagem, cobertura, area de estoque, ou a
# vigas e lajes), nada reprova: o pilar simplesmente sai subdimensionado. Por isso
# a permissao vem marcada linha a linha na Tabela 10 e e conferida aqui, e o
# relatorio mostra explicitamente qual pavimento foi reduzido e por quanto.
#
# Unidades: m, kN. Saidas em portugues.
# ============================================================================
"""Descida de cargas do edificio multipavimento: empilha pavimentos-tipo, aplica a
reducao de cargas variaveis de 6.12 sobre a parcela variavel e monta os lances de
cada pilar continuo."""

from __future__ import annotations

import cargas_nbr6120 as cg
import pavimento_tipo as pt


def descer(cfg):
    """Empilha os pavimentos e devolve a descida de cargas por pilar.

    cfg: {
      'pavimentos': lista do TOPO para a BASE, cada um:
          {'nome'      : rotulo ('Cobertura', 'Tipo 5', 'Terreo'...);
           'pavimento' : dict de configuracao do `pavimento_tipo.monta`
                         (pode ser o MESMO objeto em varios pavimentos - o
                         pavimento-tipo propriamente dito, calculado uma vez so);
           'pe_direito': (opc) distancia entre eixos de viga do lance (m);
           'secao'     : (opc) {'b','h'} da secao do pilar naquele lance;
           'redutivel' : (opc) sobrescreve o que a Tabela 10 diz para aquele uso}
      'elemento' : 'pilar' (default) ou 'fundacao' - a reducao de 6.12 so vale
                   para esses dois; qualquer outro valor desliga a reducao.
    }

    Retorna {'pavimentos', 'pilares', 'linhas_reducao', 'registro_6120'}, com
    'pilares' mapeando o nome do pilar para {'lances', 'N_base_k', ...}."""
    pavs = cfg["pavimentos"]
    if not pavs:
        raise ValueError("a descida de cargas precisa de pelo menos um pavimento")
    elemento = cfg.get("elemento", "pilar")

    # --- calcula (uma vez por configuracao distinta) o pavimento-tipo --------
    cache = {}
    montados = []
    for pv in pavs:
        chave = id(pv["pavimento"])
        if chave not in cache:
            cache[chave] = pt.monta(pv["pavimento"])
        montados.append(cache[chave])

    # --- multiplicadores de 6.12, pavimento a pavimento ---------------------
    entrada = []
    for pv, m in zip(pavs, montados):
        linha = {"nome": pv.get("nome"), "uso": pv["pavimento"]["uso"],
                 "area": m["area_m2"]}
        if "redutivel" in pv:
            linha["redutivel"] = pv["redutivel"]
        entrada.append(linha)
    linhas = cg.multiplicadores_pavimentos(entrada, elemento=elemento)

    # --- acumula por pilar ---------------------------------------------------
    nomes = [p["nome"] for p in montados[0]["pilares"]]
    for m in montados:
        if [p["nome"] for p in m["pilares"]] != nomes:
            raise ValueError(
                "os pavimentos empilhados tem malhas de pilares diferentes; a descida "
                "de cargas exige a mesma malha em toda a altura (ou um pilar de "
                "transicao, que este modulo nao trata)")

    pilares = {}
    for nome in nomes:
        acum_g = acum_q = 0.0
        lances = []
        for pv, m, lin in zip(pavs, montados, linhas):
            p = next(x for x in m["pilares"] if x["nome"] == nome)
            n_g = p["N_g_k"]
            n_q = p["N_q_k"] * lin["alpha"]
            acum_g += n_g
            acum_q += n_q
            sec = pv.get("secao") or {}
            lances.append({
                "nome": pv.get("nome"),
                "b": sec.get("b", 0.25), "h": sec.get("h", 0.50),
                "pe_direito": pv.get("pe_direito", 2.90),
                "h_viga": pv["pavimento"].get("h_viga", 0.50),
                "N_aplicado": round(n_g + n_q, 3),
                "N_g_pav": round(n_g, 3), "N_q_pav_bruto": round(p["N_q_k"], 3),
                "alpha_n": lin["alpha"], "N_q_pav_reduzido": round(n_q, 3),
                "N_acum_k": round(acum_g + acum_q, 2),
            })
        pilares[nome] = {
            "nome": nome, "posicao": next(x["posicao"] for x in montados[0]["pilares"]
                                          if x["nome"] == nome),
            "lances": lances,
            "N_base_k": round(acum_g + acum_q, 2),
            "N_base_g_k": round(acum_g, 2), "N_base_q_k": round(acum_q, 2),
            "N_base_sem_reducao_k": round(
                sum(l["N_g_pav"] + l["N_q_pav_bruto"] for l in lances), 2),
        }

    return {
        "n_pavimentos": len(pavs), "elemento": elemento,
        "pavimentos": [{"nome": pv.get("nome"), "uso": pv["pavimento"]["uso"],
                        "alpha_n": lin["alpha"], "n_grupo": lin["n_grupo"],
                        "redutivel": lin["redutivel"], "motivo": lin["motivo"]}
                       for pv, lin in zip(pavs, linhas)],
        "linhas_reducao": linhas,
        "pilares": pilares,
        "registro_6120": cg.registro_reducoes(linhas),
    }


def lances_para_pilar(r, nome):
    """Lista de lances do pilar `nome`, no formato que `pilar_continuo.dimensiona`
    espera (topo -> base)."""
    if nome not in r["pilares"]:
        raise KeyError("pilar '%s' nao existe na descida (pilares: %s)"
                       % (nome, ", ".join(sorted(r["pilares"]))))
    return [{"nome": l["nome"], "b": l["b"], "h": l["h"],
             "pe_direito": l["pe_direito"], "h_viga": l["h_viga"],
             "N_aplicado": l["N_aplicado"]} for l in r["pilares"][nome]["lances"]]


def verifica_reducao(r):
    """Confere que a reducao so foi aplicada onde a norma permite e mede quanto ela
    aliviou. Devolve {'ok', 'reduzidos', 'alivio_pct_max', 'violacoes'}.

    'ok' False significa que algum pavimento NAO REDUTIVEL saiu com alpha < 1 - o que
    seria um subdimensionamento silencioso do pilar e da fundacao."""
    violacoes = []
    for lin in r["linhas_reducao"]:
        if (not lin["redutivel"]) and lin["alpha"] < 1.0 - 1e-12:
            violacoes.append(
                "pavimento '%s' (uso %s) e de carga variavel NAO REDUTIVEL e recebeu "
                "alpha_n = %.2f" % (lin["nome"], lin["uso"], lin["alpha"]))
    reduzidos = [lin["nome"] for lin in r["linhas_reducao"] if lin["alpha"] < 1.0]
    alivio = 0.0
    for p in r["pilares"].values():
        bruto = p["N_base_sem_reducao_k"]
        if bruto > 0:
            alivio = max(alivio, 100.0 * (bruto - p["N_base_k"]) / bruto)
    return {"ok": not violacoes, "reduzidos": reduzidos,
            "alivio_pct_max": round(alivio, 2), "violacoes": violacoes}


def relatorio(r):
    """Memoria da descida de cargas, incluindo o registro exigido por 6.12."""
    L = ["DESCIDA DE CARGAS - edificio de %d pavimentos" % r["n_pavimentos"],
         "Reducao de cargas variaveis aplicada ao elemento: %s" % r["elemento"],
         "",
         "%-14s %-28s %7s %8s" % ("PAVIMENTO", "USO", "alpha", "grupo")]
    L.append("-" * 62)
    for pv in r["pavimentos"]:
        L.append("%-14s %-28s %7.2f %8s"
                 % (str(pv["nome"])[:14], str(pv["uso"])[:28], pv["alpha_n"],
                    pv["n_grupo"] if pv["n_grupo"] is not None else "-"))
    L.append("-" * 62)
    L += ["", "%-8s %-13s %12s %12s %12s"
          % ("PILAR", "POSICAO", "N_g (kN)", "N_q (kN)", "N_base (kN)")]
    L.append("-" * 62)
    for nome in sorted(r["pilares"]):
        p = r["pilares"][nome]
        L.append("%-8s %-13s %12.1f %12.1f %12.1f"
                 % (p["nome"], p["posicao"], p["N_base_g_k"], p["N_base_q_k"],
                    p["N_base_k"]))
    L.append("-" * 62)
    v = verifica_reducao(r)
    L += ["", "Alivio maximo pela reducao de 6.12: %.1f%% da forca normal na base"
          % v["alivio_pct_max"]]
    if v["violacoes"]:
        L += ["REPROVA - reducao aplicada onde a norma nao permite:"]
        L += ["  X " + x for x in v["violacoes"]]
    L += ["", r["registro_6120"]]
    return "\n".join(L)
