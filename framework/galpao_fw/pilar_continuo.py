# ============================================================================
# pilar_continuo.py - O QUE ESTE SCRIPT FAZ / CALCULA
# PILAR CONTINUO de edificio multipavimento (ABNT NBR 6118:2014): a coluna que
# atravessa varios pavimentos, dividida em LANCES (um por pe-direito), com a forca
# normal ACUMULANDO de cima para baixo e com MUDANCA DE SECAO ao longo da altura.
# Ate aqui o framework so conhecia o pilar do galpao: UM lance em balanco, secao
# unica, `n_andares=1` fixo.
#
#   1) COMPRIMENTO EQUIVALENTE por lance e por direcao (15.6): o pilar contido entre
#      dois pavimentos e "suposto vinculado em ambas as extremidades", logo
#      le = min(l0 + h ; l), com l0 = distancia entre as FACES INTERNAS dos elementos
#      horizontais que vinculam o pilar, h = altura da secao NAQUELA direcao e
#      l = distancia entre os EIXOS desses elementos. Note que h entra por direcao:
#      le_x usa hx e le_y usa hy - sao dois le diferentes na mesma barra.
#   2) DESCIDA DA FORCA NORMAL: N no topo do lance = N que vem de cima + reacoes das
#      vigas daquele nivel; o peso proprio do lance entra ao descer para o lance
#      seguinte. O N que sai na base e o que a fundacao recebe.
#   3) MUDANCA DE SECAO: cada lance e dimensionado com a SUA secao (o pilar-padrao de
#      15.8.1 exige secao constante ao longo do eixo - o que vale POR LANCE, nao para
#      a coluna inteira). Gate proprio: secao que DIMINUI ao descer e erro de projeto,
#      e sai reprovado com o nivel onde ocorre.
#   4) MOMENTOS DE 1a ORDEM vindos da viga: o engastamento parcial de 14.6.6.1-c
#      reparte o momento de engastamento perfeito entre a viga e os tramos SUPERIOR e
#      INFERIOR do pilar - `viga_continua.analisa` ja devolve essas duas parcelas em
#      'momentos_no_pilar', e elas entram aqui como M1d do lance de cima e do de baixo.
#   5) FAIXA DE VALIDADE (15.8.1 / 15.8.3.3.2 / 15.8.4): reusa o gate de
#      `pilar_concreto.valida_esbeltez`. Num pilar contINUO a esbeltez cai muito em
#      relacao ao balanco (le ~ H em vez de 2H), mas o lance de pe-direito duplo (pe
#      direito de loja, pilotis) volta a estourar - e sem gate isso passa calado.
#
# Reuso por PRIMITIVA (licao da Fase 6B): toda a flexo-composta, esbeltez limite,
# 2a ordem, gamma_n de secao pequena e armadura minima/maxima vem de
# `pilar_concreto.dimensiona_pilar`, ja aferido contra Bastos. Aqui so entram a
# geometria do lance, a descida do N e os gates de continuidade.
#
# Unidades: m, kN ; fck/fyk em kN/m2. Saidas em portugues.
# ============================================================================
"""Pilar continuo de edificio multipavimento (NBR 6118:2014): lances, comprimento
equivalente de 15.6, descida da forca normal, mudanca de secao e gates de
continuidade, reusando pilar_concreto para o dimensionamento de cada lance."""

from __future__ import annotations

import pilar_concreto as pc

GAMMA_CONC = 25.0        # peso especifico do concreto armado (kN/m3), NBR 6120 Tab.1


def comprimento_equivalente(l_eixos, h_viga, h_secao):
    """le de um lance de pilar contINUO, numa direcao (15.6):
        le = min(l0 + h ; l)
    l_eixos : distancia entre os EIXOS dos elementos horizontais que vinculam o
              pilar (m) - na pratica o pe-direito de piso a piso.
    h_viga  : altura da viga que vincula o topo do lance (m). l0 = l - h_viga.
    h_secao : altura da secao do PILAR na direcao considerada (m).

    Devolve (le, l0). Repare que le nunca passa de l: quando a viga e baixa,
    l0 + h_secao pode superar l e o minimo corta - e isso e a norma, nao um clamp
    arbitrario."""
    if l_eixos <= 0:
        raise ValueError("distancia entre eixos deve ser > 0")
    if h_viga < 0 or h_viga >= l_eixos:
        raise ValueError("altura da viga (%.3f m) deve estar em [0 ; l) com l = %.3f m"
                         % (h_viga, l_eixos))
    l0 = l_eixos - h_viga
    return min(l0 + h_secao, l_eixos), l0


def _valida_continuidade(lances):
    """Gates geometricos da coluna contINUA, do topo para a base."""
    erros, avisos = [], []
    for k in range(1, len(lances)):
        cima, baixo = lances[k - 1], lances[k]
        # secao nao pode ENCOLHER ao descer: o lance de baixo carrega tudo o que esta
        # acima. Encolher e erro de lancamento, e nenhum gate de flexo-compressao
        # acusaria isso como tal (o lance so ficaria com mais armadura, ou reprovaria
        # por taxa, sem dizer o motivo real).
        if (baixo["b"] < cima["b"] - 1e-9) or (baixo["h"] < cima["h"] - 1e-9):
            erros.append(
                "lance '%s' (%.2f x %.2f m) e MENOR que o lance de cima '%s' "
                "(%.2f x %.2f m): a secao de um pilar continuo nao pode diminuir ao "
                "descer, pois o lance inferior acumula toda a carga de cima"
                % (baixo.get("nome", k), baixo["b"], baixo["h"],
                   cima.get("nome", k - 1), cima["b"], cima["h"]))
        # transicao brusca: aviso (exige detalhe de transicao / mudanca de eixo)
        for dim in ("b", "h"):
            if baixo[dim] > cima[dim] + 1e-9:
                salto = baixo[dim] - cima[dim]
                if salto > 0.20 + 1e-9:
                    avisos.append(
                        "lance '%s': a dimensao %s salta %.0f cm em relacao ao lance de "
                        "cima - transicao brusca, exige detalhe de arranque/transicao"
                        % (baixo.get("nome", k), dim, salto * 100))
    return erros, avisos


def dimensiona(cfg):
    """Dimensiona um pilar continuo, lance a lance, do TOPO para a BASE.

    cfg: {
      'lances': lista do topo para a base, cada um:
          {'nome'      : rotulo do pavimento;
           'b','h'     : secao do lance (m). 'h' e a dimensao na direcao x.
           'pe_direito': distancia entre EIXOS das vigas (m);
           'h_viga'    : altura da viga que vincula o topo do lance (m, default 0,50);
           'N_aplicado': forca normal CARACTERISTICA que os pavimentos daquele nivel
                         entregam ao pilar (kN) - ja com a reducao de 6.12 aplicada
                         por quem montou a descida de cargas (ver cargas_nbr6120);
           'M1d_x','M1d_y': (opc) dict de momento de 1a ordem de CALCULO por direcao,
                         no formato de pilar_concreto.dimensiona_pilar}
      'fck','fyk' : resistencias (kN/m2). 'dl' : d' (m, default 0,04).
      'gamma_f'   : default 1,4.
      'peso_proprio': default True - soma o peso do lance ao descer.
    }

    Retorna {'OK', 'lances': [...], 'N_base', 'erros', 'avisos'}."""
    lances = cfg["lances"]
    if not lances:
        raise ValueError("o pilar continuo precisa de pelo menos um lance")
    fck, fyk = cfg["fck"], cfg["fyk"]
    considera_pp = cfg.get("peso_proprio", True)

    erros, avisos = _valida_continuidade(lances)

    saida = []
    N_acum = 0.0
    for k, lc in enumerate(lances):
        b, h = lc["b"], lc["h"]
        H = lc["pe_direito"]
        h_viga = lc.get("h_viga", 0.50)
        N_acum += float(lc.get("N_aplicado", 0.0))
        N_topo = N_acum

        # le por DIRECAO: x usa h (hx), y usa b (hy) - dois le distintos (15.6)
        le_x, l0 = comprimento_equivalente(H, h_viga, h)
        le_y, _ = comprimento_equivalente(H, h_viga, b)

        # o dimensionamento usa a secao critica do lance = a BASE (N maximo do lance)
        peso = GAMMA_CONC * b * h * H if considera_pp else 0.0
        N_base = N_topo + peso

        caso = {"b": b, "h": h, "Nk": N_base, "le_x": le_x, "le_y": le_y,
                "fck": fck, "fyk": fyk, "dl": cfg.get("dl", 0.04),
                "gamma_f": cfg.get("gamma_f", 1.4)}
        for key in ("M1d_x", "M1d_y"):
            if lc.get(key):
                caso[key] = lc[key]
        if lc.get("forcar_biaxial"):
            caso["forcar_biaxial"] = True
        r = pc.dimensiona_pilar(caso)

        saida.append({
            "nome": lc.get("nome", "lance %d" % (k + 1)),
            "b": b, "h": h, "pe_direito": H, "h_viga": h_viga, "l0": round(l0, 3),
            "le_x": round(le_x, 3), "le_y": round(le_y, 3),
            "lambda_x": r["dir"]["x"]["lambda"], "lambda_y": r["dir"]["y"]["lambda"],
            "N_topo_k": round(N_topo, 1), "peso_proprio_k": round(peso, 1),
            "N_base_k": round(N_base, 1), "Nd": r["Nd"],
            "As_cm2": r["As_cm2"], "taxa_pct": r["taxa_pct"],
            "esbeltez_valida": r["esbeltez_valida"],
            "avisos_esbeltez": r["avisos_esbeltez"],
            "OK": r["OK"], "detalhe": r,
        })
        N_acum = N_base

    ok_lances = all(x["OK"] for x in saida)
    OK = ok_lances and not erros
    return {"OK": OK, "n_lances": len(saida), "lances": saida,
            "N_base_k": round(N_acum, 1), "erros": erros, "avisos": avisos,
            "reprovados": [x["nome"] for x in saida if not x["OK"]]}


def relatorio(r):
    """Memoria de calculo da descida do pilar continuo."""
    L = ["PILAR CONTINUO - ABNT NBR 6118:2014 (le de 15.6 ; 2a ordem local de 15.8)",
         "%d lances ; forca normal caracteristica na base: %.1f kN"
         % (r["n_lances"], r["N_base_k"]),
         "",
         "%-14s %11s %8s %8s %8s %8s %10s %9s %6s"
         % ("LANCE", "SECAO (m)", "le_x", "le_y", "lam_x", "lam_y", "N_base(kN)",
            "As(cm2)", "OK")]
    L.append("-" * 100)
    for x in r["lances"]:
        L.append("%-14s %5.2fx%-5.2f %8.2f %8.2f %8.1f %8.1f %10.1f %9.1f %6s"
                 % (str(x["nome"])[:14], x["b"], x["h"], x["le_x"], x["le_y"],
                    x["lambda_x"], x["lambda_y"], x["N_base_k"], x["As_cm2"],
                    "sim" if x["OK"] else "NAO"))
    L.append("-" * 100)
    for x in r["lances"]:
        for a in x["avisos_esbeltez"]:
            L.append("  ! %s: %s" % (x["nome"], a))
    if r["erros"]:
        L += ["", "ERROS DE CONTINUIDADE:"] + ["  X " + e for e in r["erros"]]
    if r["avisos"]:
        L += ["", "Avisos:"] + ["  ! " + a for a in r["avisos"]]
    L += ["", "RESULTADO: %s" % ("ATENDE" if r["OK"]
                                 else "REPROVADO em " + ", ".join(r["reprovados"] or
                                                                 ["continuidade"]))]
    return "\n".join(L)
