# ============================================================================
# edificio_multipavimento.py - O QUE ESTE SCRIPT FAZ / CALCULA
# ORQUESTRADOR do edificio multipavimento (G3): um `rodar(spec)` despacha a cadeia
# inteira e consolida os gates num ATENDE global, no mesmo padrao STATELESS dos
# demais verticais do framework (`galpao_concreto.rodar`, `galpao_turnkey.rodar`).
#
#     spec -> pavimento-tipo -> descida de cargas (6.12) -> pilares continuos
#          -> lajes -> vigas continuas -> escada -> planta de formas -> gates
#
# DIMENSIONAMENTO AUTOMATICO DOS PILARES: cada pilar e percorrido do TOPO para a
# BASE e, em cada lance, adota-se a MENOR secao da lista que atende E que nao seja
# menor que a do lance de cima (a secao de um pilar continuo nao pode encolher ao
# descer). Se nenhuma secao da lista atender um lance, o pilar sai REPROVADO com o
# lance nomeado - nunca a ultima tentada dada por boa.
#
# O ATENDE global e a conjuncao dos gates. Cada disciplina falha ISOLADA: um pilar
# reprovado nao impede que os demais sejam dimensionados e reportados, para que o
# projetista veja o quadro inteiro numa passada.
#
# Unidades: m, kN ; fck/fyk em kN/m2. Saidas em portugues.
# ============================================================================
"""Orquestrador do edificio multipavimento: um rodar(spec) encadeia pavimento-tipo,
descida de cargas, pilares continuos, lajes, vigas, escada e planta de formas, e
consolida os gates."""

from __future__ import annotations

import os

import descida_cargas as dc
import laje_concreto as lj
import pavimento_tipo as pt
import pilar_continuo as pcn

# secoes de pilar tentadas, da menor para a maior (b, h) em m
SECOES_PILAR = ((0.19, 0.30), (0.19, 0.40), (0.20, 0.50), (0.25, 0.50),
                (0.25, 0.60), (0.30, 0.60), (0.30, 0.70), (0.35, 0.70),
                (0.40, 0.80), (0.50, 0.90))


def _maior_ou_igual(sec, minimo):
    """True se `sec` nao e menor que `minimo` em nenhuma das duas dimensoes."""
    return sec[0] >= minimo[0] - 1e-9 and sec[1] >= minimo[1] - 1e-9


def dimensiona_pilar_continuo(lances, fck, fyk, secoes=SECOES_PILAR):
    """Percorre os lances do topo para a base adotando, em cada um, a MENOR secao
    que atende e que nao seja menor que a do lance de cima.

    Devolve (lances_com_secao, erros). `erros` nomeia os lances em que nenhuma secao
    da lista serviu - o resultado desses lances traz a MAIOR secao tentada, marcada
    como reprovada, e nunca e apresentado como bom."""
    escolhidos = []
    erros = []
    minimo = (0.0, 0.0)
    N_acum = 0.0                 # N que CHEGA ao topo do lance
    for lc in lances:
        N_topo = N_acum + lc["N_aplicado"]
        adotada = None
        peso = 0.0
        for sec in secoes:
            if not _maior_ou_igual(sec, minimo):
                continue
            # o lance e verificado ISOLADO com o N ja acumulado ate aqui. O
            # `peso_proprio=True` faz o proprio pcn somar o peso DESTE lance, igual
            # ao que a verificacao final da pilha fara - se a selecao usasse um N
            # menor que a verificacao, ela poderia adotar uma secao que a
            # verificacao final reprova, e o pilar sairia reprovado sem que nenhuma
            # secao maior chegasse a ser tentada.
            r = pcn.dimensiona({"lances": [dict(lc, b=sec[0], h=sec[1],
                                                N_aplicado=N_topo)],
                                "fck": fck, "fyk": fyk, "peso_proprio": True})
            if r["OK"]:
                adotada = sec
                peso = r["lances"][0]["peso_proprio_k"]
                break
        if adotada is None:
            adotada = secoes[-1]
            r = pcn.dimensiona({"lances": [dict(lc, b=adotada[0], h=adotada[1],
                                                N_aplicado=N_topo)],
                                "fck": fck, "fyk": fyk, "peso_proprio": True})
            peso = r["lances"][0]["peso_proprio_k"]
            erros.append("lance '%s': nenhuma secao da lista atende (a maior tentada "
                         "foi %.2f x %.2f m)" % (lc.get("nome"), adotada[0], adotada[1]))
        minimo = adotada
        escolhidos.append(dict(lc, b=adotada[0], h=adotada[1]))
        # o acumulado que desce carrega tambem o PESO PROPRIO do lance, exatamente
        # como faz pilar_continuo.dimensiona ao percorrer a pilha
        N_acum = N_topo + peso
    return escolhidos, erros


def rodar(spec):
    """Dimensiona o edificio multipavimento e devolve os gates.

    spec: {
      'geometria' : {'vaos_x': [...], 'vaos_y': [...], 'pe_direito': m};
      'pavimentos': lista do TOPO para a BASE, cada um {'nome', 'uso'} (chave da
                    Tabela 10 da NBR 6120). O pavimento-tipo e montado uma vez por
                    uso distinto;
      'laje'      : {'h': m, 'revestimento_kN_m2': opc};
      'viga'      : {'b','h'} (m);
      'materiais' : {'fck','fyk'} (kN/m2);
      'parede_sobre_vigas' : opc, ver pavimento_tipo;
      'parede_sem_posicao_pp' : opc (kN/m), Tabela 11;
      'escada'    : opc, sub-spec de escada_concreto.dimensiona;
      'out_dir'   : opc - se dado, escreve a planta de formas (SVG).
    }"""
    geo = spec["geometria"]
    mat = spec["materiais"]
    laje = spec.get("laje", {})
    viga = spec.get("viga", {})
    fck, fyk = mat["fck"], mat["fyk"]

    def _tipo_para(uso):
        d = {"vaos_x": geo["vaos_x"], "vaos_y": geo["vaos_y"],
             "h_laje": laje.get("h", 0.10),
             "revestimento_kN_m2": laje.get("revestimento_kN_m2", 1.0),
             "uso": uso,
             "b_viga": viga.get("b", 0.20), "h_viga": viga.get("h", 0.50),
             "fck": fck, "fyk": fyk, "pe_direito": geo["pe_direito"]}
        if spec.get("parede_sobre_vigas"):
            d["parede_sobre_vigas"] = spec["parede_sobre_vigas"]
        if spec.get("parede_sem_posicao_pp"):
            d["parede_sem_posicao_pp"] = spec["parede_sem_posicao_pp"]
        return d

    # um objeto de configuracao POR USO (a descida usa id() para nao remontar)
    por_uso = {}
    pavs = []
    for pv in spec["pavimentos"]:
        uso = pv["uso"]
        if uso not in por_uso:
            por_uso[uso] = _tipo_para(uso)
        pavs.append({"nome": pv["nome"], "pavimento": por_uso[uso],
                     "pe_direito": geo["pe_direito"]})

    # ------------------------------------------------------ PAVIMENTO-TIPO
    pav = pt.monta(por_uso[spec["pavimentos"][-1]["uso"]])
    fech = pt.verifica_fechamento(pav)

    # -------------------------------------------------------- DESCIDA (6.12)
    desc = dc.descer({"pavimentos": pavs, "elemento": "pilar"})
    red = dc.verifica_reducao(desc)

    # -------------------------------------------------------------- PILARES
    pilares = {}
    erros_pilar = []
    secoes_base = []
    for nome in sorted(desc["pilares"]):
        lances = dc.lances_para_pilar(desc, nome)
        escolhidos, erros = dimensiona_pilar_continuo(lances, fck, fyk)
        r = pcn.dimensiona({"lances": escolhidos, "fck": fck, "fyk": fyk})
        if erros:
            r = dict(r, OK=False)
            r["erros"] = list(r["erros"]) + erros
        pilares[nome] = r
        secoes_base.append((escolhidos[-1]["b"], escolhidos[-1]["h"]))
        if not r["OK"]:
            erros_pilar.append(nome)

    # ----------------------------------------------------------------- LAJE
    # painel critico = o de maior area
    crit = max(pav["paineis"], key=lambda p: p["lx"] * p["ly"])
    r_laje = lj.dimensiona_laje({
        "caso": crit["caso"], "lx": min(crit["lx"], crit["ly"]),
        "ly": max(crit["lx"], crit["ly"]), "h": laje.get("h", 0.10),
        "g": pav["g_kN_m2"], "q": pav["q_kN_m2"], "fck": fck, "fyk": fyk})

    # ---------------------------------------------------------------- VIGAS
    vigas = list(pav["vigas_x"]) + list(pav["vigas_y"])
    vigas_ok = all(v["OK"] for v in vigas)

    # --------------------------------------------------------------- ESCADA
    r_escada = None
    if spec.get("escada"):
        import escada_concreto as ec
        e = dict(spec["escada"])
        e.setdefault("fck", fck)
        e.setdefault("fyk", fyk)
        e.setdefault("desnivel", geo["pe_direito"] / 2.0)
        r_escada = ec.dimensiona(e)

    # --------------------------------------------------------------- PLANTA
    planta = None
    if spec.get("out_dir"):
        import desenho_pavimento as dp
        os.makedirs(spec["out_dir"], exist_ok=True)
        planta = dp.gerar_planta_formas(
            pav, os.path.join(spec["out_dir"], "planta-formas-pavimento-tipo.svg"),
            descida=desc)

    # ------------------------------------------- ESTABILIDADE HORIZONTAL
    # Fecha os itens 1 e 2 da secao 10 da REVISAO-G3. So roda quando o vento e'
    # declarado: sem Ca (abaco da Fig.4 da NBR 6123) nao ha o que calcular, e
    # arbitrar um valor seria inventar acao de projeto.
    estabilidade = None
    if spec.get("vento"):
        import estabilidade_edificio as ee
        # carga vertical caracteristica de cada pavimento, da BASE para o topo
        montados = {}
        for pv in spec["pavimentos"]:
            uso = pv["uso"]
            if uso not in montados:
                montados[uso] = (pav if por_uso[uso] is por_uso[
                    spec["pavimentos"][-1]["uso"]] else pt.monta(por_uso[uso]))
        cargas_k = [montados[pv["uso"]]["N_total_k"]
                    for pv in reversed(spec["pavimentos"])]
        # Secao do portico global: a MENOR das secoes adotadas no lance da base.
        # E' a escolha conservadora (menor rigidez -> maior gamma_z e maior
        # deslocamento); o modelo de portico plano usa uma secao unica.
        b_min, h_min = min(secoes_base, key=lambda s: s[0] * s[1] ** 3)
        estabilidade = ee.verifica({
            "geometria": geo, "n_pavimentos": len(pavs),
            "materiais": {"fck": fck},
            "secoes": {"pilar": {"b": b_min, "h": h_min},
                       "viga": {"b": viga.get("b", 0.20),
                                "h": viga.get("h", 0.50)}},
            "cargas_verticais_kN": cargas_k,
            "lajes_lisas": bool(spec.get("lajes_lisas")),
            "vento": spec["vento"]})

    # ---------------------------------------------------------------- GATES
    gates = {
        "fechamento_carga": {"OK": fech["ok"], "erro_rel": fech["erro_rel"],
                             "N_pilares": fech["N_pilares"],
                             "esperado": fech["carga_esperada"]},
        "reducao_6120": {"OK": red["ok"], "reduzidos": red["reduzidos"],
                         "alivio_pct": red["alivio_pct_max"],
                         "violacoes": red["violacoes"]},
        "pilares": {"OK": not erros_pilar, "reprovados": erros_pilar,
                    "n": len(pilares)},
        "laje": {"OK": bool(r_laje.get("OK")), "h_cm": r_laje.get("h", 0) * 100},
        "vigas": {"OK": vigas_ok, "n": len(vigas),
                  "reprovadas": [v["nome"] for v in vigas if not v["OK"]]},
    }
    if r_escada is not None:
        gates["escada"] = {"OK": r_escada["OK"]}
    if estabilidade is not None:
        gates["estabilidade_horizontal"] = {
            "OK": bool(estabilidade["OK"]),
            "gamma_z": estabilidade["gamma_z"]["gamma_z"],
            "nos": estabilidade["gamma_z"]["nos"],
            "direcao_critica": estabilidade["direcao_critica"],
            "els_OK": estabilidade["els_OK"],
            "H_sobre_u_topo": estabilidade["els"]["H_sobre_u"]}

    reprovados = [k for k, g in gates.items() if not g["OK"]]
    return {
        "ATENDE": not reprovados, "reprovados": reprovados, "gates": gates,
        "pavimento": pav, "descida": desc, "pilares": pilares,
        "laje": r_laje, "vigas": vigas, "escada": r_escada, "planta": planta,
        "estabilidade": estabilidade,
        "n_pavimentos": len(pavs),
        "N_base_max_k": max(p["N_base_k"] for p in pilares.values()),
        "registro_6120": desc["registro_6120"],
    }


def relatorio_pt(r):
    """Quadro-resumo do edificio multipavimento."""
    pav = r["pavimento"]
    L = ["EDIFICIO MULTIPAVIMENTO - quadro-resumo",
         "  %d pavimentos ; malha %d x %d vaos ; %.1f m2 por pavimento"
         % (r["n_pavimentos"], len(pav["vaos_x"]), len(pav["vaos_y"]),
            pav["area_m2"]),
         "  g = %.2f kN/m2 ; q = %.2f kN/m2 (NBR 6120 Tab.10)"
         % (pav["g_kN_m2"], pav["q_kN_m2"]),
         ""]
    g = r["gates"]
    L += ["  FECHAMENTO DE CARGA: %.1f kN nos pilares x %.1f kN esperados "
          "(erro %.3f%%) -> %s"
          % (g["fechamento_carga"]["N_pilares"], g["fechamento_carga"]["esperado"],
             100 * g["fechamento_carga"]["erro_rel"],
             "OK" if g["fechamento_carga"]["OK"] else "NAO FECHA"),
          "  REDUCAO NBR 6120 6.12: %d pavimentos reduzidos ; alivio maximo %.1f%% "
          "-> %s" % (len(g["reducao_6120"]["reduzidos"]),
                     g["reducao_6120"]["alivio_pct"],
                     "OK" if g["reducao_6120"]["OK"] else "REPROVA"),
          "  LAJE: h = %.0f cm -> %s" % (g["laje"]["h_cm"],
                                         "ATENDE" if g["laje"]["OK"] else "REPROVA"),
          "  VIGAS CONTINUAS: %d linhas -> %s"
          % (g["vigas"]["n"], "ATENDE" if g["vigas"]["OK"]
             else "REPROVA em " + ", ".join(g["vigas"]["reprovadas"])),
          "  PILARES CONTINUOS: %d -> %s"
          % (g["pilares"]["n"], "ATENDE" if g["pilares"]["OK"]
             else "REPROVA em " + ", ".join(g["pilares"]["reprovados"]))]
    if "escada" in g:
        L.append("  ESCADA DE CONCRETO: %s" % ("ATENDE" if g["escada"]["OK"]
                                               else "REPROVA"))
    if "estabilidade_horizontal" in g:
        eh = g["estabilidade_horizontal"]
        L.append("  ESTABILIDADE HORIZONTAL: gamma_z = %.3f (%s, direcao %s) ; "
                 "ELS topo H/%.0f -> %s"
                 % (eh["gamma_z"], "nos " + eh["nos"], eh["direcao_critica"],
                    eh["H_sobre_u_topo"], "ATENDE" if eh["OK"] else "REPROVA"))
    L += ["", "  PILAR MAIS CARREGADO: N = %.1f kN na base" % r["N_base_max_k"], ""]
    L.append("%-8s %-13s %12s %14s" % ("PILAR", "POSICAO", "N_base(kN)", "SECAO BASE"))
    L.append("  " + "-" * 52)
    for nome in sorted(r["pilares"]):
        p = r["pilares"][nome]
        base = p["lances"][-1]
        pos = r["descida"]["pilares"][nome]["posicao"]
        L.append("%-8s %-13s %12.1f %10.2f x %.2f"
                 % (nome, pos, p["N_base_k"], base["b"], base["h"]))
    if r.get("planta"):
        L += ["", "  Planta de formas: %s" % r["planta"]]
    L += ["", "  RESULTADO GLOBAL: %s"
          % ("ATENDE" if r["ATENDE"] else "REPROVA -> " + ", ".join(r["reprovados"]))]
    if "estabilidade_horizontal" not in g:
        L.append("  [ACAO HORIZONTAL NAO AVALIADA: sem 'vento' no spec a descida e'")
        L.append("   apenas GRAVITACIONAL - vento, desaprumo, gamma_z e ELS ficam de fora.]")
    L += ["  [A CONFIRMAR: alvenaria ESTRUTURAL nao dimensionada (NBR 16868 ausente",
          "   do acervo); fundacao e vibracao de piso fora do escopo deste modulo.]"]
    return "\n".join(L)
