# ============================================================================
# gestao_casa.py - A CAMADA DE GESTAO DA CASA RESIDENCIAL (G58)
#
# O G14 ligou orcamento, cronograma, caderno e pacote ao EDIFICIO, e a casa -
# a tipologia mais numerosa - seguia com 4 entregaveis. Os motores ja existiam
# (`entregaveis_projeto`); o que faltava era a DERIVACAO DE QUANTITATIVOS de
# uma casa de alvenaria com telhado, que NAO e a de um predio de concreto.
# Este modulo e' so essa traducao:
#
#     resultado da casa -> {codigo de insumo: quantidade}
#                       -> WBS da casa (terrea/sobrado, com cobertura)
#                       -> disciplinas do caderno e do pacote
#                       -> memorial consolidado
#
# NADA aqui calcula engenharia. Todo numero vem de modulo ja aferido.
#
# POR QUE OS QUANTITATIVOS DO PREDIO NAO SERVEM (a armadilha do G58). A
# derivacao do predio (`gestao_edificio`) mede laje/viga/pilar por pavimento
# de um edificio de concreto. A casa tem:
#   - ALVENARIA de vedacao + VIGA BALDRAME que leva o peso do terreo a sapata
#     por fora da descida (estrutura_casa);
#   - TELHADO (cobertura com area declarada, estrutura de madeira fora do
#     escopo): herdar a WBS do predio zera o telhado em silencio;
#   - ESTRUTURA OPCIONAL (G13): disciplina declarada = implemented, nao
#     declarada = not_available - nunca concreto inventado do envelope.
#
# As guardas do G7/G14 valem aqui, exercidas pela PRIMEIRA vez contra outra
# tipologia:
#   1. ARMADURA POR ELEMENTO (laje/viga/pilar/fundacao separados);
#   2. ESCOPO DA TIPOLOGIA (`aplicaveis` da CASA): o que a casa nao tem
#      (aco estrutural, piso industrial) sai em `nao_aplicaveis`; o que ela
#      tem e ninguem quantificou (telhado sem area, baldrame sem peso) sai
#      em `sem_quantidade`. Herdar a lista do predio e' o defeito que este
#      modulo existe para nao cometer;
#   3. INSUMOS FORA DA TABELA nomeados em `a_confirmar`.
#
# FRONTEIRA (G13): a cadeia estrutural cobre ate 2 pavimentos e RECUSA mais
# que isso. A derivacao le SO o resultado calculado - nunca o spec direto
# para medir geometria. Casa recusada (>2 pav) nao tem estrutura calculada,
# logo nao tem quantitativo de concreto: o orcamento fica sem base com o
# motivo nomeado, em vez de contornar a fronteira medindo o spec.
#
# Unidades: m, m2, m3, kg, un. Precos em R$ (REFERENCIA, A CONFIRMAR). STATELESS.
# ============================================================================
"""Gestao da casa residencial: quantitativos, WBS, caderno e pacote (G58)."""

from __future__ import annotations

import math

import estrutura_casa as _ec

RHO_ACO_KG_M3 = 7850.0

# Insumos que uma CASA pode ter. E' o escopo contra o qual o orcamento se
# declara completo ou parcial (guarda 2, primeira vez fora do predio):
# a casa TEM telhado e o predio nao o nomeava; a casa NAO tem aco estrutural
# nem piso industrial (esses dois seguem nao_aplicaveis, como no predio).
CODIGOS_APLICAVEIS = (
    "concreto_estrut", "forma", "armadura_laje", "armadura_viga",
    "armadura_pilar", "fundacao_concreto", "armadura_fundacao", "estaca",
    "fechamento_lateral", "telha_cobertura",
    "eletrica_ponto", "hidraulica_ponto",
)

PRECOS_CASA = {
    "armadura_laje": ("Armadura CA-50 de laje (corte/dobra/montagem)", "kg", 13.50),
    "armadura_viga": ("Armadura CA-50 de viga (corte/dobra/montagem)", "kg", 14.50),
    "armadura_pilar": ("Armadura CA-50 de pilar (corte/dobra/montagem)", "kg", 14.50),
    "armadura_fundacao": ("Armadura CA-50 de fundacao", "kg", 13.00),
}

# O que a casa TEM e a tabela de referencia NAO precifica. Sem esta lista o
# preco de venda passaria por preco da casa inteira.
INSUMOS_FORA_DA_TABELA = (
    "alvenaria de vedacao e revestimentos (chapisco/emboco/reboco, pintura)",
    "esquadrias, vidros, loucas e metais",
    "estrutura de madeira do telhado (tesouras, tercas, ripas)",
    "impermeabilizacao (baldrame, areas molhadas)",
    "escavacao, reaterro e canteiro de obra",
)

# ------------------------------- cronograma ---------------------------------
# Casa terrea/sobrado: a estrutura nao e' ciclo por pavimento como no predio
# (12 dias/pav). Sao frentes curtas em serie, com a COBERTURA como frente
# propria - a WBS do predio nao tem cobertura e zeraria o telhado no prazo
# como zeraria no custo. Duracoes PRODUTIVIDADE DE OBRA, A CONFIRMAR.
DUR_FUND_DIAS = 12
DUR_ESTR_DIAS_POR_PAV = 15
DUR_VEDACAO_DIAS = 15
DUR_COBERTURA_DIAS = 10
DUR_INST_DIAS = 15
DUR_ACAB_DIAS = 20

CUSTO_POR_ATIVIDADE = {
    "fundacao_concreto": "fund", "armadura_fundacao": "fund", "estaca": "fund",
    "concreto_estrut": "estr", "forma": "estr",
    "armadura_laje": "estr", "armadura_viga": "estr", "armadura_pilar": "estr",
    "fechamento_lateral": "vedacao",
    "telha_cobertura": "cob",
    "eletrica_ponto": "inst", "hidraulica_ponto": "inst",
}


def wbs(n_pavimentos):
    """WBS-esqueleto de uma casa terrea/sobrado, com cobertura propria."""
    n = max(int(n_pavimentos or 1), 1)
    return [
        {"id": "serv", "nome": "Servicos preliminares/canteiro", "dur": 7,
         "pred": []},
        {"id": "fund", "nome": "Fundacoes e baldrame", "dur": DUR_FUND_DIAS,
         "pred": ["serv"]},
        {"id": "estr", "nome": "Estrutura de concreto (%d pav)" % n,
         "dur": n * DUR_ESTR_DIAS_POR_PAV, "pred": ["fund"]},
        {"id": "vedacao", "nome": "Alvenaria de vedacao", "dur": DUR_VEDACAO_DIAS,
         "pred": ["estr"]},
        {"id": "cob", "nome": "Cobertura/telhado", "dur": DUR_COBERTURA_DIAS,
         "pred": ["vedacao"]},
        {"id": "inst", "nome": "Instalacoes (elet/hidr)", "dur": DUR_INST_DIAS,
         "pred": ["cob"]},
        {"id": "acab", "nome": "Revestimentos e acabamento", "dur": DUR_ACAB_DIAS,
         "pred": ["inst"]},
        {"id": "entrega", "nome": "Limpeza e entrega", "dur": 5,
         "pred": ["acab"]},
    ]


# =============================================================================
# QUANTITATIVOS
# =============================================================================
def _num(valor, default=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def _acima_do_teto(turnkey_estrutura) -> bool:
    """O spec pede mais pavimentos que a tipologia cobre (fronteira G13)?"""
    try:
        pavs = (turnkey_estrutura or {}).get("pavimentos") or []
        return len(pavs) > _ec.MAX_PAVIMENTOS
    except Exception:  # noqa: BLE001
        return False


def _pe_direito(est):
    pilares = est.get("pilares") or {}
    if not pilares:
        return 0.0
    return _num(pilares[sorted(pilares)[0]]["lances"][0]["pe_direito"])


def _volume_e_forma_da_estrutura(est):
    """Concreto (m3) e forma (m2) da superestrutura, por elemento.

    MESMA convencao de medicao do predio (laje area x h adotada; viga eixo a
    eixo descontando a faixa da laje; pilar descontando o no): a casa e' a
    mesma geometria de concreto com menos andares, e a convencao viaja junto
    para o numero continuar comparavel ao IFC.
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


def _armadura_das_lajes(est, notas):
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
        "%.0f m2 de laje da casa - os demais paineis sao menos armados, entao "
        "o peso e CONSERVADOR (mais caro)" % (taxa, laje.get("caso"), area_total))
    return taxa * area_total


def _armadura_dos_pilares(est):
    peso = 0.0
    for pilar in est["pilares"].values():
        for lance in pilar["lances"]:
            As_m2 = _num(lance.get("As_cm2")) * 1e-4
            peso += As_m2 * _num(lance.get("pe_direito")) * RHO_ACO_KG_M3
    return peso


def _armadura_das_vigas(est, notas):
    """Peso de aco das VIGAS da casa, da verificacao tramo a tramo.

    A casa verifica cada tramo em `estrutura_casa.verifica_vigas` (flexao,
    cortante, ancoragem, ELS) e publica As_inf/As_sup por tramo - o mesmo
    contrato do predio, na chave `vigas` em vez de `vigas_verificacao`.
    Sem verificacao, o codigo continua VAZIO de proposito.
    """
    vv = (est or {}).get("vigas")
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
        "por tramo, %d tramos do pavimento-tipo x %d pavimentos. Traspasses, "
        "perdas de corte e armadura alem da minima nao incluidos"
        % (total, n_tramos, max(n_pav, 1)))
    return total


def _fundacao(est, notas, nao_derivados, escopo):
    """Concreto, armadura e metros de estaca da fundacao ja dimensionada.

    O TIPO decide o escopo (guarda 2): obra sobre sapatas nao tem metro de
    estaca - cobra-lo faria o orcamento se declarar parcial por um insumo que
    a obra nao tem. O contrario nao vale (bloco de coroamento segue falta
    nomeada quando a fundacao e' em estacas).
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
            "pedestal, lastro, escavacao e reaterro nao estao no volume")
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
    """Alvenaria de fechamento - so quando ha parede DECLARADA na estrutura."""
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
        "SEM desconto de vaos de janela e porta (a arquitetura da casa nao "
        "modela esquadrias)" % area)
    return {"fechamento_lateral": round(area, 1)}


def _pontos_eletricos(result, notas, nao_derivados):
    """Pontos de luz e tomadas da casa, dos pontos DECLARADOS e conferidos.

    Le os pontos do resultado eletrico (circuits.points, ja conferidos contra
    a NBR 5410 9.5.2 pela costura do adaptador). TUE conta como ponto dedicado:
    tambem custa eletroduto, condutor e disjuntor.
    """
    elet = (result or {}).get("eletrico") or {}
    circuitos = elet.get("circuits") or {}
    pontos = circuitos.get("points")
    if not isinstance(pontos, list) or not pontos:
        nao_derivados.append({
            "item": "eletrica_ponto",
            "motivo": "nenhum ponto de circuito declarado no resultado eletrico"})
        return {}
    n_luz = sum(1 for p in pontos if isinstance(p, dict) and p.get("kind") == "lighting")
    n_tug = sum(1 for p in pontos if isinstance(p, dict) and p.get("kind") == "tug")
    n_tue = sum(1 for p in pontos if isinstance(p, dict) and p.get("kind") == "tue")
    total = n_luz + n_tug + n_tue
    if not total:
        return {}
    notas.append(
        "eletrica_ponto: %d pontos declarados e conferidos (%d luz + %d TUG + "
        "%d TUE dedicados, NBR 5410 9.5.2)" % (total, n_luz, n_tug, n_tue))
    return {"eletrica_ponto": total}


def _pontos_hidraulicos(spec_hidraulica, notas, nao_derivados):
    """Um ponto por aparelho declarado (agua + esgoto)."""
    spec_hidraulica = spec_hidraulica or {}
    agua = spec_hidraulica.get("aparelhos_agua") or {}
    esgoto = spec_hidraulica.get("aparelhos_esgoto") or {}
    if not isinstance(agua, dict):
        agua = {}
    if not isinstance(esgoto, dict):
        esgoto = {}
    total = sum(int(v) for v in list(agua.values()) + list(esgoto.values())
                if isinstance(v, (int, float)) and not isinstance(v, bool))
    if not total:
        nao_derivados.append({
            "item": "hidraulica_ponto",
            "motivo": "nenhum aparelho hidraulico declarado em "
                      "turnkey.hidraulica.aparelhos_agua/aparelhos_esgoto"})
        return {}
    notas.append(
        "hidraulica_ponto: %d aparelhos declarados (agua + esgoto). Ramais, "
        "prumadas, coletor e calhas estao na composicao do insumo, mas rede "
        "externa e reservatorio nao" % total)
    return {"hidraulica_ponto": total}


def _telha(spec_hidraulica, notas, nao_derivados):
    """Area de telha da cobertura - projecao declarada, SEM inclinacao.

    A estrutura de madeira do telhado esta fora do escopo (nomeda em
    INSUMOS_FORA_DA_TABELA); a telha sai pela area de projecao que a
    hidraulica ja declara para o pluvial. Sem ela, o codigo fica VAZIO e o
    orcamento se declara parcial - nunca zerado em silencio.
    """
    cobertura = (spec_hidraulica or {}).get("cobertura") or {}
    area = cobertura.get("area_m2")
    try:
        area_f = float(area)
    except (TypeError, ValueError):
        area_f = 0.0
    if area_f <= 0:
        nao_derivados.append({
            "item": "telha_cobertura",
            "motivo": "cobertura.area_m2 nao declarada em turnkey.hidraulica: "
                      "sem projecao nao ha area de telha a orcar (o telhado "
                      "existe e nao pode sair zerado)"})
        return {}
    notas.append(
        "telha_cobertura: %.1f m2 = projecao horizontal declarada "
        "(cobertura.area_m2), SEM fator de inclinacao/cumeeira: a area real "
        "de telha e' maior. Estrutura de madeira fora do preco" % area_f)
    return {"telha_cobertura": round(area_f, 1)}


def derivacao(result, spec_hidraulica=None):
    """Quantitativos da casa a partir do resultado do adaptador.

    Devolve {'quantitativos', 'composicao', 'a_confirmar', 'nao_derivados',
    'aplicaveis'}. Nunca levanta por dado ausente nem contorna a fronteira
    dos 2 pavimentos: sem estrutura calculada nao ha geometria de concreto a
    medir - mas eletrica, hidraulica e telha (que nao passam pela estrutura)
    continuam derivadas, e os insumos de concreto saem em `sem_quantidade`
    via `aplicaveis` em vez de sumirem (a estrutura da casa pode nao existir,
    G13; o orcamento parcial se declara parcial).
    """
    est = (result or {}).get("estrutura")
    if isinstance(est, dict) and int(est.get("n_pavimentos") or 0) > _ec.MAX_PAVIMENTOS:
        return {"quantitativos": {}, "composicao": {},
                "aplicaveis": sorted(CODIGOS_APLICAVEIS), "a_confirmar": [],
                "nao_derivados": [{
                    "item": "estrutura",
                    "motivo": "n_pavimentos=%s acima do teto da tipologia "
                              "(max %d): a derivacao nao mede o spec direto"
                              % (est.get("n_pavimentos"), _ec.MAX_PAVIMENTOS)}]}
    notas = []
    nao_derivados = []
    q = {}
    escopo = set(CODIGOS_APLICAVEIS)
    composicao = {}

    if isinstance(est, dict) and est.get("pavimento"):
        geo = _volume_e_forma_da_estrutura(est)
        concreto = geo["laje_m3"] + geo["viga_m3"] + geo["pilar_m3"]
        forma = geo["forma_laje_m2"] + geo["forma_viga_m2"] + geo["forma_pilar_m2"]

        q["concreto_estrut"] = round(concreto, 2)
        q["forma"] = round(forma, 1)

        peso_laje = _armadura_das_lajes(est, notas)
        if peso_laje:
            q["armadura_laje"] = round(peso_laje, 1)
        else:
            nao_derivados.append({
                "item": "armadura_laje",
                "motivo": "laje sem painel dimensionado no resultado: sem As nao "
                          "ha peso a derivar"})
        peso_pilar = _armadura_dos_pilares(est)
        if peso_pilar:
            q["armadura_pilar"] = round(peso_pilar, 1)
            notas.append(
                "armadura_pilar: so a armadura LONGITUDINAL (As adotada x altura do "
                "lance). Estribos, traspasses e arranques nao estao no peso")
        else:
            nao_derivados.append({
                "item": "armadura_pilar",
                "motivo": "pilares sem As adotada no resultado"})
        peso_viga = _armadura_das_vigas(est, notas)
        if peso_viga:
            q["armadura_viga"] = round(peso_viga, 1)
        else:
            nao_derivados.append({
                "item": "armadura_viga",
                "motivo": "vigas sem verificacao tramo a tramo no resultado: nao "
                          "ha As dimensionada para derivar peso"})

        q.update(_fundacao(est, notas, nao_derivados, escopo))
        q.update(_fechamento(est, notas, nao_derivados))
        composicao = {"laje_m3": round(geo["laje_m3"], 2),
                      "viga_m3": round(geo["viga_m3"], 2),
                      "pilar_m3": round(geo["pilar_m3"], 2),
                      "forma_m2": round(forma, 1),
                      "comprimento_vigas_m": round(geo["comprimento_vigas_m"], 2),
                      "n_pavimentos": geo["n_pavimentos"],
                      "tipologia": est.get("tipologia")}
    else:
        nao_derivados.append({
            "item": "estrutura",
            "motivo": "estrutura nao calculada (nao declarada ou recusada): "
                      "concreto, forma, armaduras, fundacao e fechamento ficam "
                      "sem quantitativo"})
    q.update(_pontos_eletricos(result, notas, nao_derivados))
    q.update(_pontos_hidraulicos(spec_hidraulica, notas, nao_derivados))
    q.update(_telha(spec_hidraulica, notas, nao_derivados))

    notas.append(
        "vazios de escada e shafts NAO sao descontados da area de laje")
    notas.append(
        "viga medida EIXO A EIXO (o no viga-pilar pertence a viga): o IFC "
        "descreve a mesma estrutura com as vigas face a face em uma das "
        "direcoes, entao o volume de viga do orcamento supera o do IFC na "
        "soma dos nos. Convencao, nao erro")
    notas.append(
        "insumos que a casa tem e a tabela de referencia NAO tem, portanto "
        "FORA do preco de venda: %s" % "; ".join(INSUMOS_FORA_DA_TABELA))
    return {"quantitativos": q, "composicao": composicao, "a_confirmar": notas,
            "nao_derivados": nao_derivados, "aplicaveis": sorted(escopo)}


# =============================================================================
# CADERNO DE ENCARGOS E PACOTE LEGAL
# =============================================================================
# disciplina da casa -> disciplina da biblioteca de clausulas/pranchas.
# A arquitetura nao tem clausulas na biblioteca (o caderno especifica COMO
# executar; o programa de ambientes e' memorial, nao servico): ela entra no
# pacote e no memorial, nunca no caderno.
_DISCIPLINAS_DA_CASA = (
    ("estrutura", "concreto"),
    ("hidraulica", "hidraulica"),
    ("eletrico", "eletrico"),
)

FUNDACAO_COBERTA_POR = "concreto"


def disciplinas(result):
    """Disciplinas EXECUTADAS na rodada, no vocabulario do caderno/pacote.

    So entra o que rodou. A fundacao acompanha o concreto SO quando
    dimensionada (secao propria no caderno).
    """
    encontradas = []
    if isinstance((result or {}).get("estrutura"), dict) and result["estrutura"]:
        encontradas.append("concreto")
    if isinstance((result or {}).get("hidraulica"), dict) and result["hidraulica"]:
        encontradas.append("hidraulica")
    if isinstance((result or {}).get("eletrico"), dict) and result["eletrico"]:
        eletrico = result["eletrico"]
        circuitos = eletrico.get("circuits") if isinstance(eletrico, dict) else None
        if circuitos or eletrico.get("calculation"):
            encontradas.append("eletrico")
    est = (result or {}).get("estrutura") or {}
    if "concreto" in encontradas and est.get("fundacao"):
        encontradas.append("fundacao")
    return encontradas


def disciplinas_pacote(result):
    """Disciplinas no vocabulario do INDICE de pranchas.

    A arquitetura entra no pacote (PE-AR: implantacao, planta baixa, cortes)
    quando o programa foi calculado; a fundacao e' coberta pela folha de
    concreto PE-CO-01, como no predio (D89).
    """
    trad = []
    if isinstance((result or {}).get("arquitetura"), dict) and result["arquitetura"]:
        trad.append("arquitetura")
    for d in disciplinas(result):
        d2 = FUNDACAO_COBERTA_POR if d == "fundacao" else d
        if d2 not in trad:
            trad.append(d2)
    return trad


def memorial(result):
    """Memorial consolidado da casa."""
    est = (result or {}).get("estrutura") or {}
    arq = (result or {}).get("arquitetura") or {}
    geometria = {}
    if arq:
        totais = arq.get("totais") or {}
        geometria = {
            "area_util_m2": totais.get("area_util_m2"),
            "n_ambientes": totais.get("n_ambientes"),
            "tipologia": est.get("tipologia"),
            "n_pavimentos": est.get("n_pavimentos"),
        }
    itens = []
    for nome in ("arquitetura", "estrutura", "eletrico", "hidraulica"):
        saida = (result or {}).get(nome)
        if not isinstance(saida, dict) or not saida:
            continue
        atende = saida.get("ATENDE")
        if atende is None:
            erros = saida.get("errors") or saida.get("erros") or []
            atende = not erros
        itens.append({"disciplina": nome,
                      "veredito": "ATENDE" if atende else "REPROVA",
                      "reprovados": list(saida.get("reprovados") or [])})
    executadas = [item["disciplina"] for item in itens]
    return {"geometria": geometria, "disciplinas": itens,
            "atende_global": all(item["veredito"] == "ATENDE" for item in itens)
            and bool(itens),
            "executadas": executadas, "puladas": []}


# =============================================================================
# HOOKS DO PROJECT LOOP
# =============================================================================
def _camada():
    import entregaveis_projeto as ep
    return ep


def _spec_hidraulica(normalized):
    turnkey = (normalized or {}).get("turnkey_spec") or {}
    hid = turnkey.get("hidraulica")
    return hid if isinstance(hid, dict) else {}


def emitir_orcamento(manifest, run_dir, normalized, options, result):
    """Planilha 5D + curva ABC da casa (quantitativos derivados acima)."""
    del options
    ep = _camada()
    if _acima_do_teto((normalized.get("turnkey_spec") or {}).get("estrutura")):
        manifest["deliverables"]["orcamento"] = {
            "status": "not_available",
            "detail": "estrutura com mais de %d pavimentos: acima do teto "
                      "da tipologia casa (G13) - use 'edificio'; sem "
                      "estrutura calculada nao ha quantitativo honesto"
                      % _ec.MAX_PAVIMENTOS}
        return
    dados = derivacao(result, _spec_hidraulica(normalized))
    ep.orcamento_no_manifesto(
        manifest, run_dir, normalized, dados["quantitativos"],
        aplicaveis=dados["aplicaveis"], precos_extra=PRECOS_CASA,
        notas=dados["a_confirmar"],
        extras={"composicao": dados["composicao"],
                "nao_derivados": dados["nao_derivados"]},
        detalhe_vazio="estrutura nao calculada: sem geometria nao ha "
                      "quantitativo, e nada foi declarado em "
                      "gestao.orcamento.quantitativos")


def emitir_cronograma(manifest, run_dir, normalized, options, result):
    """Rede CPM + curva S da casa, custeada pelo orcamento da rodada."""
    del options
    ep = _camada()
    if _acima_do_teto((normalized.get("turnkey_spec") or {}).get("estrutura")):
        manifest["deliverables"]["cronograma"] = {
            "status": "not_available",
            "detail": "estrutura com mais de %d pavimentos: WBS de casa nao "
                      "se aplica (G13) - use 'edificio'" % _ec.MAX_PAVIMENTOS}
        return
    est = (result or {}).get("estrutura") or {}
    ep.cronograma_no_manifesto(
        manifest, run_dir, normalized, wbs(est.get("n_pavimentos") or 1),
        CUSTO_POR_ATIVIDADE,
        nota_padrao="WBS-esqueleto da casa terrea/sobrado (frentes em SERIE, "
                    "com cobertura propria): duracoes PRODUTIVIDADE DE OBRA - "
                    "confirmar com o planejamento")


def emitir_caderno_encargos(manifest, run_dir, normalized, options, result):
    """Especificacoes tecnicas das disciplinas executadas na casa."""
    del options
    ep = _camada()
    ep.caderno_no_manifesto(manifest, run_dir, normalized, disciplinas(result))


def emitir_pacote_legal(manifest, run_dir, normalized, options, result):
    """Indice de pranchas, ART/RRT, PPCI/AVCB, LOD, O&M e memorial da casa."""
    del options
    ep = _camada()
    ep.pacote_no_manifesto(manifest, run_dir, disciplinas_pacote(result),
                           memorial(result))


# ----------------------------------- selftest --------------------------------
def _selftest():
    import cronograma as cr

    c1 = {x["id"]: x for x in wbs(1)}
    c2 = {x["id"]: x for x in wbs(2)}
    assert c2["estr"]["dur"] > c1["estr"]["dur"]
    assert "cob" in c1 and c1["cob"]["dur"] == DUR_COBERTURA_DIAS
    crono = cr.cronograma(wbs(1))
    assert crono["duracao_total_dias"] > 0 and "estr" in crono["caminho_critico"]

    vazio = derivacao({"estrutura": None})
    assert vazio["quantitativos"] == {} and vazio["nao_derivados"]
    assert "telha_cobertura" in vazio["aplicaveis"]
    assert "aco_estrutural" not in vazio["aplicaveis"]
    assert "piso_industrial" not in vazio["aplicaveis"]

    r = {"estrutura": {"fundacao": {"por_pilar": {"P11": {}}}},
         "eletrico": {"circuits": {"points": [{"id": "L1"}]}},
         "hidraulica": {"redes": {"agua_fria": {}}},
         "arquitetura": {"ambientes": []}}
    assert disciplinas(r) == ["concreto", "hidraulica", "eletrico", "fundacao"]
    assert disciplinas_pacote(r) == ["arquitetura", "concreto", "hidraulica",
                                     "eletrico"]
    assert disciplinas({}) == []
    return True


if __name__ == "__main__":
    _selftest()
    print("gestao_casa: selftest OK")
