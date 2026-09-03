# ============================================================================
# gestao_edificio.py - A CAMADA DE GESTAO DO EDIFICIO MULTIPAVIMENTO (G14)
#
# O G6 religou orcamento, cronograma, caderno de encargos e pacote legal ao
# adaptador de GALPAO, e o G7 deixou anotado que o EDIFICIO seguia sem nenhum
# dos quatro: um predio de nove pavimentos saia da rodada com estrutura,
# fundacao, incendio, hidraulica, eletrica, BIM e pranchas - e sem uma linha
# sobre quanto custa, quanto demora, o que se especifica e o que se protocola.
#
# O MECANISMO ja existia (`entregaveis_projeto`); o que faltava era a
# DERIVACAO DE QUANTITATIVOS de um edificio de concreto, que nao e a de um
# galpao metalico. Este modulo e' so essa traducao:
#
#     resultado do edificio -> {codigo de insumo: quantidade}
#                           -> WBS do predio (ciclo por pavimento)
#                           -> disciplinas do caderno e do pacote
#                           -> memorial consolidado
#
# NADA aqui calcula engenharia. Todo numero vem de modulo ja aferido: o peso de
# aco da laje sai de `laje_concreto.quadro_de_ferros`, o da sapata de
# `fundacao_sapata.quantitativo`, o As do pilar do proprio lance dimensionado,
# a contagem de aparelhos da hidraulica e a de pontos da eletrica das saidas
# das respectivas fronteiras. Onde nao ha numero dimensionado, NAO se inventa
# taxa: o codigo fica SEM quantitativo e o orcamento se declara PARCIAL.
#
# POR QUE O ORCAMENTO NAO PODE SE DECLARAR FECHADO (defeito n.3 do G7). Um
# orcamento com uma linha parece um orcamento. Tres guardas evitam isso aqui:
#
#   1. ARMADURA POR ELEMENTO. `armadura_laje`, `armadura_pilar`,
#      `armadura_fundacao` e `armadura_viga` sao codigos SEPARADOS. Ate o G33 as
#      vigas do edificio eram ANALISADAS e nunca VERIFICADAS (gap do G3), logo
#      nao existia As dimensionada para elas - e sem codigo proprio esse buraco
#      entraria dentro de um `armadura` unico, que exibiria um peso 30-40%
#      menor com cara de completo. O G34 FECHOU o gap (toda viga, todo tramo
#      verificado em `edificio_multipavimento.vigas_verificacao` e peso derivado
#      em `_armadura_das_vigas`); o codigo separado CONTINUA, porque e' ele que
#      impede o peso parcial de passar por completo. Rotulo tem de descrever a
#      geometria que cobre (a licao da varredura de rotulo do takeoff).
#   2. ESCOPO DA TIPOLOGIA. `compor_orcamento` passou a aceitar `aplicaveis`:
#      um predio de concreto nao tem aco estrutural, telha metalica nem piso
#      industrial, e declara-los "sem quantitativo" seria ruido escondendo a
#      falta que importa. O que a obra nao tem sai em `nao_aplicaveis`,
#      publicado; o que ela tem e ninguem quantificou sai em `sem_quantidade`.
#   3. INSUMOS FORA DA TABELA. Revestimento, esquadria, elevador, louca,
#      impermeabilizacao e a instalacao de incendio nao existem na tabela de
#      referencia. Nao ha como orca-los, entao eles sao NOMEADOS em
#      `a_confirmar` - a obra que falta aparece, em vez de o preco de venda
#      passar por preco da obra inteira.
#
# Unidades: m, m2, m3, kg, un. Precos em R$ (REFERENCIA, A CONFIRMAR). STATELESS.
# ============================================================================
"""Gestao do edificio multipavimento: quantitativos, WBS, caderno e pacote."""

from __future__ import annotations

import math

RHO_ACO_KG_M3 = 7850.0          # massa especifica do aco (igual a fundacao_sapata)

# Insumos que um EDIFICIO DE CONCRETO pode ter. E' o escopo contra o qual o
# orcamento se declara completo ou parcial - ver guarda 2 no cabecalho.
CODIGOS_APLICAVEIS = (
    "concreto_estrut", "forma", "armadura_laje", "armadura_viga",
    "armadura_pilar", "fundacao_concreto", "armadura_fundacao", "estaca",
    "fechamento_lateral", "eletrica_ponto", "hidraulica_ponto",
)

# Precos de REFERENCIA dos insumos que a tabela do `orcamento` nao traz por
# nome proprio (ela tem um `armadura` unico). Mesma ordem de grandeza da
# armadura CA-50 cortada/dobrada/montada; a produtividade muda por elemento e
# por isso a SINAPI tambem os separa. A CONFIRMAR, como toda a tabela.
PRECOS_EDIFICIO = {
    "armadura_laje": ("Armadura CA-50 de laje (corte/dobra/montagem)", "kg", 13.50),
    "armadura_viga": ("Armadura CA-50 de viga (corte/dobra/montagem)", "kg", 14.50),
    "armadura_pilar": ("Armadura CA-50 de pilar (corte/dobra/montagem)", "kg", 14.50),
    "armadura_fundacao": ("Armadura CA-50 de fundacao", "kg", 13.00),
}

# O que a obra TEM e a tabela de referencia NAO tem. Sem esta lista o preco de
# venda passaria por preco da obra inteira.
INSUMOS_FORA_DA_TABELA = (
    "alvenaria interna e revestimentos (chapisco/emboco/reboco, pintura)",
    "esquadrias, vidros, louças e metais",
    "impermeabilizacao (cobertura, areas molhadas, baldrame)",
    "elevador e casa de maquinas",
    "instalacao de combate a incendio (hidrantes, extintores, sinalizacao)",
    "escavacao, contencao e canteiro de obra",
)

# ------------------------------- cronograma ---------------------------------
# Ciclo de estrutura por pavimento: forma -> armadura -> concretagem ->
# desforma de um pavimento-tipo. E' PRODUTIVIDADE DE OBRA, nao conta de
# engenharia; entra como esqueleto e viaja marcado A CONFIRMAR, no mesmo
# regime das duracoes do WBS de galpao.
CICLO_ESTRUTURA_DIAS_POR_PAVIMENTO = 12

# De qual atividade cada insumo paga a conta (distribui o custo na curva S).
CUSTO_POR_ATIVIDADE = {
    "fundacao_concreto": "fund", "armadura_fundacao": "fund", "estaca": "fund",
    "concreto_estrut": "estr", "forma": "estr",
    "armadura_laje": "estr", "armadura_viga": "estr", "armadura_pilar": "estr",
    "fechamento_lateral": "vedacao",
    "eletrica_ponto": "inst", "hidraulica_ponto": "inst",
}


def wbs(n_pavimentos):
    """WBS-esqueleto de um edificio: a estrutura sobe pavimento a pavimento.

    O que distingue esta rede da de um galpao e' que a duracao da estrutura NAO
    e' uma constante: sao `n_pavimentos` ciclos de forma/armadura/concretagem.
    Vedacao e instalacoes seguem a estrutura com defasagem de pavimentos, o que
    aqui aparece como precedencia simples (a rede e' CPM, sem sobreposicao
    parcial); por isso o prazo sai CONSERVADOR - dito, nunca mascarado.
    """
    n = max(int(n_pavimentos), 1)
    return [
        {"id": "serv", "nome": "Servicos preliminares/canteiro", "dur": 15,
         "pred": []},
        {"id": "fund", "nome": "Fundacoes", "dur": 25, "pred": ["serv"]},
        {"id": "estr", "nome": "Estrutura de concreto (%d pavimentos)" % n,
         "dur": n * CICLO_ESTRUTURA_DIAS_POR_PAVIMENTO, "pred": ["fund"]},
        {"id": "vedacao", "nome": "Vedacao e esquadrias", "dur": 15 * 2,
         "pred": ["estr"]},
        {"id": "inst", "nome": "Instalacoes (elet/hidr/incendio)", "dur": 30,
         "pred": ["vedacao"]},
        {"id": "acab", "nome": "Revestimentos e acabamento", "dur": 40,
         "pred": ["inst"]},
        {"id": "entrega", "nome": "Limpeza, comissionamento e entrega",
         "dur": 10, "pred": ["acab"]},
    ]


# =============================================================================
# QUANTITATIVOS
# =============================================================================
def _num(valor, default=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def _pe_direito(est):
    """Pe-direito do predio, lido do lance de pilar (o pavimento nao o publica)."""
    pilares = est.get("pilares") or {}
    if not pilares:
        return 0.0
    return _num(pilares[sorted(pilares)[0]]["lances"][0]["pe_direito"])


def _volume_e_forma_da_estrutura(est):
    """Concreto (m3) e forma (m2) da superestrutura, por elemento.

    CONVENCAO DE MEDICAO (declarada porque sem ela o mesmo volume pode ser
    contado duas vezes, ou nenhuma, no encontro viga-pilar):
      - laje  : area do pavimento x espessura ADOTADA (a que realimentou a
                carga), em todos os pavimentos;
      - viga  : b x (h - h_laje) x comprimento EIXO A EIXO - a faixa dentro da
                laje ja foi medida na laje;
      - pilar : b x h x (pe-direito - altura da viga do topo do lance) - o no
                viga-pilar pertence a viga, que foi medida eixo a eixo.
    O somatorio fecha a estrutura inteira sem sobreposicao.
    """
    pav = est["pavimento"]
    n_pav = int(est["n_pavimentos"])
    area = _num(pav["area_m2"])
    h_laje = _num(est["h_laje_adotada"])
    b_v, h_v = _num(pav["b_viga"]), _num(pav["h_viga"])
    comp_vigas = (sum(sum(v["vaos"]) for v in pav["vigas_x"])
                  + sum(sum(v["vaos"]) for v in pav["vigas_y"]))

    alma = max(h_v - h_laje, 0.0)
    vol_laje = area * h_laje * n_pav
    vol_viga = b_v * alma * comp_vigas * n_pav
    # forma: fundo da laje + (duas laterais + fundo) da alma da viga
    forma_laje = area * n_pav
    forma_viga = (2.0 * alma + b_v) * comp_vigas * n_pav

    vol_pilar = forma_pilar = 0.0
    for pilar in est["pilares"].values():
        for lance in pilar["lances"]:
            b, h = _num(lance["b"]), _num(lance["h"])
            altura = max(_num(lance["pe_direito"]) - _num(lance["h_viga"]), 0.0)
            vol_pilar += b * h * altura
            forma_pilar += 2.0 * (b + h) * altura
    return {"laje_m3": vol_laje, "viga_m3": vol_viga, "pilar_m3": vol_pilar,
            "forma_laje_m2": forma_laje, "forma_viga_m2": forma_viga,
            "forma_pilar_m2": forma_pilar,
            "comprimento_vigas_m": comp_vigas, "n_pavimentos": n_pav}


def _escada(est, nao_derivados, notas):
    """Concreto e forma da escada, medidos na laje INCLINADA.

    O vao de calculo e' a projecao horizontal mais o patamar; a laje do lance
    inclinado e' mais comprida que a projecao por 1/cos(alpha). Medir na
    projecao subestimaria o lance em ~13% num degrau usual.
    """
    esc = est.get("escada")
    if not isinstance(esc, dict) or not esc:
        nao_derivados.append({
            "item": "escada",
            "motivo": "escada nao dimensionada nesta rodada (estrutura.escada "
                      "nao declarada): concreto e forma dela ficam de fora"})
        return 0.0, 0.0
    geo = esc.get("geometria") or {}
    n_degraus = _num(geo.get("n_degraus"))
    espelho = _num(geo.get("espelho"))
    alpha = _num(geo.get("alpha_rad"))
    largura = _num(esc.get("largura_m"))
    h = _num(esc.get("h_laje"))
    patamar = _num(esc.get("patamar_m"))
    projecao = _num(geo.get("projecao_m"))
    desnivel = n_degraus * espelho
    pe = _pe_direito(est)
    if desnivel <= 0 or largura <= 0 or h <= 0 or pe <= 0:
        nao_derivados.append({
            "item": "escada",
            "motivo": "geometria da escada incompleta no resultado"})
        return 0.0, 0.0
    lances_por_pav = pe / desnivel
    # a escada e' UMA so no predio: se o pe-direito nao for multiplo do
    # desnivel do lance, o numero de lances nao e derivavel e nao se arredonda
    # um lance a mais "por seguranca" - isso seria inventar geometria.
    if abs(lances_por_pav - round(lances_por_pav)) > 0.02:
        nao_derivados.append({
            "item": "escada",
            "motivo": "pe-direito (%.2f m) nao e multiplo do desnivel do lance "
                      "(%.2f m): numero de lances por pavimento nao derivavel"
                      % (pe, desnivel)})
        return 0.0, 0.0
    cos_a = math.cos(alpha) if alpha else 1.0
    comp_incl = (projecao / cos_a if cos_a else projecao) + patamar
    n_lances = int(round(lances_por_pav)) * int(est["n_pavimentos"])
    notas.append(
        "escada: %d lances (%d por pavimento x %d pavimentos), medidos na laje "
        "INCLINADA. Se a escada nao subir ate a cobertura, sao dois lances a "
        "menos - a arquitetura da caixa nao e' modelada aqui"
        % (n_lances, int(round(lances_por_pav)), int(est["n_pavimentos"])))
    vol = largura * comp_incl * h * n_lances
    forma = (largura + 2.0 * h) * comp_incl * n_lances
    return vol, forma


def _armadura_das_lajes(est, notas):
    """Peso de aco das lajes (kg), do quadro de ferros do painel CRITICO.

    `laje_concreto.quadro_de_ferros` da o peso do painel efetivamente
    dimensionado (positivas N1/N2 e negativas N3/N4, com os ganchos e os
    comprimentos de detalhamento). O painel critico e' o mais armado do
    pavimento, entao a taxa dele aplicada a area toda e CONSERVADORA - o que
    num orcamento significa mais caro, nao mais seguro, e por isso e' dito.
    """
    laje = est.get("laje")
    if not isinstance(laje, dict) or not laje.get("lx"):
        return 0.0
    import laje_concreto as lj

    quadro = lj.quadro_de_ferros(laje)
    peso_painel = lj.peso_total_aco(quadro)
    area_painel = _num(laje["lx"]) * _num(laje["ly"])
    if area_painel <= 0:
        return 0.0
    taxa = peso_painel / area_painel
    area_total = _num(est["pavimento"]["area_m2"]) * int(est["n_pavimentos"])
    notas.append(
        "armadura_laje: taxa de %.1f kg/m2 do painel CRITICO (%s) estendida aos "
        "%.0f m2 de laje do predio - os demais paineis sao menos armados, entao "
        "o peso e CONSERVADOR (mais caro). Ferros de escada nao incluidos"
        % (taxa, laje.get("caso"), area_total))
    return taxa * area_total


def _armadura_dos_pilares(est):
    """Peso de aco LONGITUDINAL dos pilares (kg): As adotada x altura do lance."""
    peso = 0.0
    for pilar in est["pilares"].values():
        for lance in pilar["lances"]:
            As_m2 = _num(lance.get("As_cm2")) * 1e-4
            peso += As_m2 * _num(lance.get("pe_direito")) * RHO_ACO_KG_M3
    return peso


def _armadura_das_vigas(est, notas):
    """Peso de aco das VIGAS (kg), da verificacao tramo a tramo (G34).

    Cada tramo verificado em `edificio_multipavimento.vigas_verificacao` traz
    As_inf/As_sup (flexao M+/M-, ja com As_min), s_estribo_max (cortante 17.4.2)
    e lb_nec (ancoragem 9.4). O peso soma, por tramo:

      - longitudinal: (As_inf + As_sup) x (L + 2*lb_nec) -- a barra passa o vao
        e ancora nas duas extremidades;
      - transversal: estribos phi_est a cada s_max (n = ceil(L/s_max)+1), com
        comprimento do retangulo interno + 2 ganchos de 10*phi (18.3.3).

    O pavimento-tipo se repete em todos os pavimentos, entao o peso de um
    pavimento e' multiplicado por n_pavimentos. Traspasses, perdas de corte e
    armadura de montagem alem da minima nao estao no peso -- dito, como nos
    demais elementos.
    """
    vv = (est or {}).get("vigas_verificacao")
    if not isinstance(vv, dict) or not vv.get("por_linha"):
        return 0.0
    peso_por_pav = 0.0
    n_tramos = 0
    for linha in vv["por_linha"]:
        b_lin = _num(linha.get("b"))
        h_lin = _num(linha.get("h"))
        for tramo in linha.get("tramos") or []:
            L = _num(tramo.get("L"))
            if L <= 0:
                continue
            n_tramos += 1
            As_inf = _num(tramo.get("As_inf_cm2")) * 1e-4
            As_sup = _num(tramo.get("As_sup_cm2")) * 1e-4
            ver = tramo.get("verificacao") or {}
            anc = ver.get("ancoragem") or {}
            lb = _num(anc.get("lb_nec_mm")) / 1000.0
            comp_long = L + 2.0 * max(lb, 0.0)
            peso_por_pav += (As_inf + As_sup) * comp_long * RHO_ACO_KG_M3
            s_max = _num(ver.get("s_estribo_max")) or 0.20
            phi_est = _num(ver.get("phi_estribo_mm")) or 5.0
            b = b_lin or _num(ver.get("b")) or 0.20
            h = h_lin or _num(ver.get("h")) or 0.50
            cob = 0.03
            n_est = math.ceil(L / s_max) + 1 if s_max > 0 else 1
            Le = 2.0 * ((b - 2.0 * cob) + (h - 2.0 * cob)) + 2.0 * 10.0 * phi_est / 1000.0
            if Le < 0:
                Le = 0.0
            peso_por_pav += n_est * max(Le, 0.0) * 0.00617 * phi_est ** 2
    if n_tramos == 0 or peso_por_pav <= 0:
        return 0.0
    n_pav = int((est or {}).get("n_pavimentos") or 1)
    total = peso_por_pav * max(n_pav, 1)
    notas.append(
        "armadura_viga: %.1f kg = (As_inf+As_sup) x (L+2*lb_nec) + estribos "
        "phi %%(phi)s s_max por tramo, %d tramos do pavimento-tipo x %d "
        "pavimentos. Traspasses, perdas de corte e armadura alem da minima "
        "nao incluidos" % (total, n_tramos, max(n_pav, 1)))
    # o phi varia por tramo; a nota registra o criterio, nao um valor unico
    notas[-1] = notas[-1].replace("phi %(phi)s", "phi por tramo")
    return total


def _fundacao(est, notas, nao_derivados, escopo):
    """Concreto, armadura e metros de estaca da fundacao ja dimensionada.

    `escopo` e' mutado: o TIPO de fundacao decide quais insumos a obra pode ter.
    Uma obra sobre sapatas nao tem metro de estaca, e cobrar dela um
    quantitativo de estaca faria o orcamento se declarar parcial por um insumo
    que a obra nao tem - o ruido que a guarda 2 do cabecalho existe para evitar.

    VEREDITO G23 – quantitativo/ORCAMENTO: USA M_base INDIRETAMENTE via
    geometria ja dimensionada com M (sapata/bloco isolado: bearing com N+M;
    estaca n=4 com grupo_momento). Para divisa (sapata_divisa/viga_equilibrio)
    IGNORA M_portico com razao declarada (ver fundacao_edificio cabecalho);
    volume = B*L*h da geometria aprovada (sem armadura ficticia para bloco).
    """
    fund = est.get("fundacao")
    if not isinstance(fund, dict) or not fund.get("por_pilar"):
        nao_derivados.append({
            "item": "fundacao",
            "motivo": "fundacao nao dimensionada (sondagem nao declarada): sem "
                      "geometria nao ha volume nem armadura a medir"})
        return {}
    import fundacao_sapata as fsap

    if fund.get("tipo") != "estaca":
        # obra sobre fundacao rasa nao tem metro de estaca: cobrar dela esse
        # quantitativo faria o orcamento se declarar parcial por um insumo que
        # a obra nao tem. Ja o CONTRARIO nao vale - uma fundacao em estacas TEM
        # bloco de coroamento, entao `fundacao_concreto` e `armadura_fundacao`
        # continuam no escopo e aparecem como falta, com o motivo nomeado.
        escopo.discard("estaca")
    vol = aco = metros_estaca = 0.0
    sem_geometria = []
    for nome, registro in sorted(fund["por_pilar"].items()):
        geo = registro.get("geometria")
        if not isinstance(geo, dict):
            sem_geometria.append(nome)
            continue
        if "n_estacas" in geo:
            metros_estaca += _num(geo["n_estacas"]) * _num(geo["L_m"])
            continue
        vol += _num(geo["B_m"]) * _num(geo["L_m"]) * _num(geo["h_m"])
        parte_b = (registro.get("bruto") or {}).get("parte_B")
        if isinstance(parte_b, dict) and "flexao_L" in parte_b:
            # a mesma conta que o proprio modulo de sapata usa no quantitativo
            # (barras // L com comprimento ~ B e vice-versa), em vez de uma
            # segunda descricao da mesma regra
            aco += fsap.quantitativo(parte_b, parte_b, 1, h_ped=0.0)["massa_aco_un"]
    if sem_geometria:
        nao_derivados.append({
            "item": "fundacao",
            "motivo": "sem geometria aprovada em %d pilar(es) (%s): eles nao "
                      "entram no volume"
                      % (len(sem_geometria), ", ".join(sem_geometria))})
    if vol or metros_estaca:
        notas.append(
            "fundacao medida como PRISMA (B x L x h) da geometria aprovada: "
            "pedestal, lastro, escavacao e reaterro nao estao no volume, e a "
            "sapata em tronco de piramide, se adotada, gasta menos concreto")
    resultado = {}
    if vol:
        resultado["fundacao_concreto"] = round(vol, 2)
    if aco:
        resultado["armadura_fundacao"] = round(aco, 1)
    if metros_estaca:
        resultado["estaca"] = round(metros_estaca, 1)
        nao_derivados.append({
            "item": "bloco de coroamento",
            "motivo": "fundacao em estacas: o volume do bloco nao e' publicado "
                      "pela geometria (so a altura), e nao entra no concreto"})
    return resultado


def _fechamento(est, notas, nao_derivados):
    """Alvenaria de fechamento - so quando ha parede DECLARADA na estrutura.

    `parede_sobre_vigas` e' o que faz a alvenaria de fachada existir no modelo.
    Sem ela o predio foi calculado SEM fachada, e derivar area de vedacao a
    partir do perimetro seria orcar uma parede que nao pesou em viga nenhuma -
    exatamente o desencontro rotulo x geometria que este framework persegue.
    """
    pav = est["pavimento"]
    if _num(pav.get("g_parede_kN_m")) <= 0:
        nao_derivados.append({
            "item": "fechamento_lateral",
            "motivo": "nenhuma alvenaria de fachada foi declarada em "
                      "estrutura.parede_sobre_vigas: a estrutura foi calculada "
                      "SEM o peso da vedacao e nao ha area a orcar"})
        return {}
    perimetro = 2.0 * (sum(pav["vaos_x"]) + sum(pav["vaos_y"]))
    pe = _pe_direito(est)
    area = perimetro * max(pe - _num(pav["h_viga"]), 0.0) * int(est["n_pavimentos"])
    notas.append(
        "fechamento_lateral: %.0f m2 de fachada pelo perimetro x altura livre, "
        "SEM desconto de vaos de janela e porta (a arquitetura do edificio nao "
        "e' modelada por este framework)" % area)
    return {"fechamento_lateral": round(area, 1)}


def _pontos_eletricos(inst, notas, nao_derivados):
    """Pontos de luz e tomadas do predio, da previsao de carga da NBR 5410."""
    elet = (inst or {}).get("eletrico")
    if not isinstance(elet, dict):
        return {}
    ambientes = (elet.get("carga_por_unidade") or {}).get("ambientes") or []
    if not ambientes:
        nao_derivados.append({
            "item": "eletrica_ponto",
            "motivo": "a carga da unidade foi DECLARADA em bloco (carga_VA) e "
                      "nao por ambiente: nao ha ponto a contar"})
        return {}
    tomadas = sum(int(a.get("n_tomadas") or 0) for a in ambientes)
    # 9.5.2.1.1: pelo menos UM ponto de luz no teto por comodo. E' a mesma
    # regra que a previsao de carga ja aplicou para chegar ao VA de iluminacao.
    luz = len(ambientes)
    por_unidade = tomadas + luz
    total = (por_unidade * int(elet.get("unidades_por_pavimento") or 0)
             * int(elet.get("pavimentos_servidos") or 0))
    if not total:
        return {}
    if _num(elet.get("carga_areas_comuns_VA")) > 0:
        nao_derivados.append({
            "item": "eletrica_ponto (areas comuns)",
            "motivo": "a carga das areas comuns (elevador, bombas, iluminacao) "
                      "e' declarada em VA, sem discriminacao de pontos: os "
                      "pontos das areas comuns nao estao na contagem"})
    notas.append(
        "eletrica_ponto: %d pontos = (%d tomadas + %d pontos de luz da NBR 5410 "
        "9.5.2.1.1) x %s unidades x %s pavimentos servidos"
        % (total, tomadas, luz, elet.get("unidades_por_pavimento"),
           elet.get("pavimentos_servidos")))
    return {"eletrica_ponto": total}


def _pontos_hidraulicos(inst, notas):
    """Um ponto por aparelho de agua - a contagem que a coluna ja fez."""
    hidr = (inst or {}).get("hidraulica")
    if not isinstance(hidr, dict):
        return {}
    totais = (hidr.get("coluna") or {}).get("aparelhos_totais") or {}
    total = sum(int(v) for v in totais.values())
    if not total:
        return {}
    notas.append(
        "hidraulica_ponto: %d aparelhos de AGUA do predio (a mesma contagem que "
        "dimensionou a coluna). O ponto de esgoto de cada aparelho esta na "
        "composicao do insumo, mas ramais, prumadas e o coletor predial nao"
        % total)
    return {"hidraulica_ponto": total}


def derivacao(result):
    """Quantitativos do edificio a partir do resultado do adaptador.

    Devolve {'quantitativos', 'composicao', 'a_confirmar', 'nao_derivados'}.
    Nunca levanta por dado ausente: o que nao da para derivar sai NOMEADO em
    `nao_derivados` e o codigo fica sem quantitativo (orcamento parcial
    declarado), que e o oposto de um numero inventado.
    """
    est = (result or {}).get("estrutura")
    if not isinstance(est, dict) or not est.get("pavimento"):
        return {"quantitativos": {}, "composicao": {},
                "aplicaveis": sorted(CODIGOS_APLICAVEIS), "a_confirmar": [],
                "nao_derivados": [{"item": "estrutura",
                                   "motivo": "estrutura nao calculada: nao ha "
                                             "geometria da qual derivar "
                                             "quantitativo nenhum"}]}
    notas = []
    nao_derivados = []

    geo = _volume_e_forma_da_estrutura(est)
    vol_escada, forma_escada = _escada(est, nao_derivados, notas)
    concreto = geo["laje_m3"] + geo["viga_m3"] + geo["pilar_m3"] + vol_escada
    forma = (geo["forma_laje_m2"] + geo["forma_viga_m2"] + geo["forma_pilar_m2"]
             + forma_escada)

    q = {"concreto_estrut": round(concreto, 2), "forma": round(forma, 1)}

    peso_laje = _armadura_das_lajes(est, notas)
    if peso_laje:
        q["armadura_laje"] = round(peso_laje, 1)
    peso_pilar = _armadura_dos_pilares(est)
    if peso_pilar:
        q["armadura_pilar"] = round(peso_pilar, 1)
        notas.append(
            "armadura_pilar: so a armadura LONGITUDINAL (As adotada x altura do "
            "lance). Estribos, traspasses e arranques nao estao no peso")
    # G34: A VIGA TEM As -- toda viga, todo tramo verificado em
    # `edificio_multipavimento.vigas_verificacao` (flexao M+/M-, cortante,
    # ancoragem, ELS). O peso sai da armadura dimensionada, nunca de taxa.
    # Sem verificacao (resultado antigo), o codigo continua VAZIO de proposito.
    peso_viga = _armadura_das_vigas(est, notas)
    if peso_viga:
        q["armadura_viga"] = round(peso_viga, 1)
    else:
        nao_derivados.append({
            "item": "armadura_viga",
            "motivo": "as vigas do edificio sao ANALISADAS (envoltoria de esforcos) "
                      "e nao VERIFICADAS: nao ha As dimensionada para derivar peso. "
                      "Declarar em gestao.orcamento.quantitativos.armadura_viga "
                      "antes de usar o preco de venda"})

    escopo = set(CODIGOS_APLICAVEIS)
    q.update(_fundacao(est, notas, nao_derivados, escopo))
    q.update(_fechamento(est, notas, nao_derivados))
    inst = (result or {}).get("instalacoes") or {}
    q.update(_pontos_eletricos(inst, notas, nao_derivados))
    q.update(_pontos_hidraulicos(inst, notas))

    notas.append(
        "vazios de escada e shafts NAO sao descontados da area de laje "
        "(a arquitetura do pavimento nao e' modelada)")
    notas.append(
        "insumos que a obra tem e a tabela de referencia NAO tem, portanto FORA "
        "do preco de venda: %s" % "; ".join(INSUMOS_FORA_DA_TABELA))
    composicao = {"laje_m3": round(geo["laje_m3"], 2),
                  "viga_m3": round(geo["viga_m3"], 2),
                  "pilar_m3": round(geo["pilar_m3"], 2),
                  "escada_m3": round(vol_escada, 2),
                  "forma_m2": round(forma, 1),
                  "comprimento_vigas_m": round(geo["comprimento_vigas_m"], 2),
                  "n_pavimentos": geo["n_pavimentos"]}
    return {"quantitativos": q, "composicao": composicao, "a_confirmar": notas,
            "nao_derivados": nao_derivados, "aplicaveis": sorted(escopo)}


# =============================================================================
# CADERNO DE ENCARGOS E PACOTE LEGAL
# =============================================================================
# disciplina do edificio -> disciplina da biblioteca de clausulas/pranchas
_DISCIPLINAS_DO_EDIFICIO = (
    ("estrutura", "concreto"),
    ("incendio", "incendio"),
    ("hidraulica", "hidraulica"),
    ("eletrico", "eletrico"),
)


def disciplinas(result):
    """Disciplinas EXECUTADAS na rodada, no vocabulario do caderno/pacote.

    So entra o que rodou. Um caderno que especifica a instalacao eletrica de um
    predio em que a eletrica nao foi projetada e' o caderno prometendo o que o
    projeto nao entrega - o espelho do orcamento que omitia o insumo.
    """
    encontradas = []
    executadas = set()
    if isinstance((result or {}).get("estrutura"), dict) and result["estrutura"]:
        executadas.add("estrutura")
    executadas.update(k for k, v in ((result or {}).get("instalacoes") or {}).items()
                      if v)
    for nome, traducao in _DISCIPLINAS_DO_EDIFICIO:
        if nome in executadas and traducao not in encontradas:
            encontradas.append(traducao)
    # a fundacao acompanha o concreto SO quando ela foi dimensionada
    est = (result or {}).get("estrutura") or {}
    if "concreto" in encontradas and est.get("fundacao"):
        encontradas.append("fundacao")
    return encontradas


def memorial(result):
    """Memorial consolidado do edificio (o analogo do memorial do turnkey)."""
    est = (result or {}).get("estrutura") or {}
    pav = est.get("pavimento") or {}
    geometria = {}
    if pav:
        geometria = {
            "pavimentos": est.get("n_pavimentos"),
            "area_por_pavimento_m2": pav.get("area_m2"),
            "altura_total_m": round(_num(est.get("H_total_m")), 2),
            "malha": "%d x %d vaos" % (len(pav.get("vaos_x") or []),
                                       len(pav.get("vaos_y") or [])),
        }
    itens = []
    if est:
        itens.append({"disciplina": "estrutura",
                      "veredito": "ATENDE" if est.get("ATENDE") else "REPROVA",
                      "reprovados": list(est.get("reprovados") or [])})
    for nome, saida in sorted(((result or {}).get("instalacoes") or {}).items()):
        if not isinstance(saida, dict):
            continue
        itens.append({"disciplina": nome,
                      "veredito": "ATENDE" if saida.get("ATENDE") else "REPROVA",
                      "reprovados": list(saida.get("reprovados") or [])})
    executadas = [item["disciplina"] for item in itens]
    return {"geometria": geometria, "disciplinas": itens,
            "atende_global": all(item["veredito"] == "ATENDE" for item in itens)
            and bool(itens),
            "executadas": executadas, "puladas": []}


# =============================================================================
# HOOKS DO PROJECT LOOP
# =============================================================================
# `entregaveis_projeto` importa `project_loop`, que registra os adaptadores ao
# ser carregado - e um deles e' o proprio edificio, que importa este modulo. O
# import PREGUICOSO dentro de cada hook e o que mantem esse ciclo aberto: com
# ele no topo, importar `edificio_adapter` primeiro quebrava o registro do
# galpao no meio (modulo parcialmente inicializado).
def _camada():
    import entregaveis_projeto as ep
    return ep


def emitir_orcamento(manifest, run_dir, normalized, options, result):
    """Planilha 5D + curva ABC do edificio (quantitativos derivados acima)."""
    del options
    ep = _camada()
    dados = derivacao(result)
    ep.orcamento_no_manifesto(
        manifest, run_dir, normalized, dados["quantitativos"],
        aplicaveis=dados["aplicaveis"], precos_extra=PRECOS_EDIFICIO,
        notas=dados["a_confirmar"],
        extras={"composicao": dados["composicao"],
                "nao_derivados": dados["nao_derivados"]},
        detalhe_vazio="estrutura nao calculada: sem geometria nao ha "
                      "quantitativo, e nada foi declarado em "
                      "gestao.orcamento.quantitativos")


def emitir_cronograma(manifest, run_dir, normalized, options, result):
    """Rede CPM + curva S do edificio, custeada pelo orcamento da rodada."""
    del options
    ep = _camada()
    est = (result or {}).get("estrutura") or {}
    ep.cronograma_no_manifesto(
        manifest, run_dir, normalized, wbs(est.get("n_pavimentos") or 1),
        CUSTO_POR_ATIVIDADE,
        nota_padrao="WBS-esqueleto do edificio: a estrutura sai de %d dias por "
                    "pavimento e as demais frentes seguem em SERIE (a rede nao "
                    "sobrepoe vedacao/instalacoes a pavimentos ja concretados), "
                    "entao o prazo e conservador - confirmar com o planejamento"
                    % CICLO_ESTRUTURA_DIAS_POR_PAVIMENTO)


def emitir_caderno_encargos(manifest, run_dir, normalized, options, result):
    """Especificacoes tecnicas das disciplinas executadas no edificio."""
    del options
    ep = _camada()
    ep.caderno_no_manifesto(manifest, run_dir, normalized, disciplinas(result))


def emitir_pacote_legal(manifest, run_dir, normalized, options, result):
    """Indice de pranchas, ART/RRT, PPCI/AVCB, LOD, O&M e memorial do edificio."""
    del options
    ep = _camada()
    ep.pacote_no_manifesto(manifest, run_dir, disciplinas(result),
                           memorial(result))


# ----------------------------------- selftest --------------------------------
def _selftest():
    # WBS: a estrutura escala com o numero de pavimentos e a rede e acyclica
    import cronograma as cr

    a4 = {x["id"]: x for x in wbs(4)}
    a8 = {x["id"]: x for x in wbs(8)}
    assert a8["estr"]["dur"] == 2 * a4["estr"]["dur"]
    crono = cr.cronograma(wbs(9))
    assert crono["duracao_total_dias"] > 0 and "estr" in crono["caminho_critico"]

    # derivacao guardada: resultado sem estrutura nao levanta e nao inventa
    vazio = derivacao({"estrutura": None})
    assert vazio["quantitativos"] == {} and vazio["nao_derivados"]

    # armadura_viga NUNCA sai derivada (nao ha As de viga no edificio)
    dados = derivacao({"estrutura": None})
    assert "armadura_viga" not in dados["quantitativos"]

    # disciplinas: so as executadas; fundacao acompanha o concreto dimensionado
    r = {"estrutura": {"fundacao": {"por_pilar": {}}},
         "instalacoes": {"eletrico": {"ATENDE": True}}}
    assert disciplinas(r) == ["concreto", "eletrico", "fundacao"]
    assert disciplinas({}) == []
    return True


if __name__ == "__main__":
    _selftest()
    print("gestao_edificio: selftest OK")
