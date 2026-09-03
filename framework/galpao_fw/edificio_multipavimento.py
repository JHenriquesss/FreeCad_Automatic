# ============================================================================
# edificio_multipavimento.py - O QUE ESTE SCRIPT FAZ / CALCULA
# ORQUESTRADOR do edificio multipavimento (G3): um `rodar(spec)` despacha a cadeia
# inteira e consolida os gates num ATENDE global, no mesmo padrao STATELESS dos
# demais verticais do framework (`galpao_concreto.rodar`, `galpao_turnkey.rodar`).
#
#     spec -> pavimento-tipo -> escada -> descida de cargas (6.12, com a reacao
#          da escada realimentada nos lances) -> pilares continuos
#          -> lajes -> vigas continuas -> planta de formas -> gates
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

import cargas_nbr6120 as cg
import descida_cargas as dc
import desempenho_nbr15575 as des
import estrutura_casa as ec_vigas
import fundacao_edificio as fe
import laje_concreto as lj
import pavimento_tipo as pt
import pilar_continuo as pcn
import vibracao_piso as vib
import viga_concreto as vgc

# teto de iteracoes do ponto fixo espessura-da-laje x carga (ver `rodar`)
MAX_ITER_LAJE = 6

# A selecao da secao lance a lance mora em `pilar_continuo` (e' regra de pilar,
# nao de edificio) desde que a CASA do G13 passou a usar a mesma com outra lista
# de secoes. Re-exportadas aqui porque este modulo e' a porta por onde o G3
# sempre as ofereceu.
SECOES_PILAR = pcn.SECOES_PILAR
dimensiona_pilar_continuo = pcn.dimensiona_pilar_continuo


def _eixos(vaos):
    """Coordenadas (m) das linhas de eixo a partir da lista de vaos."""
    xs = [0.0]
    for v in vaos:
        xs.append(xs[-1] + float(v))
    return xs


def _carga_escada_por_pavimento(r_escada, cfg_escada):
    """Reacao caracteristica da escada, POR pavimento, separada em g e q (kN).

    G38: a escada era dimensionada DEPOIS da descida e o seu peso jamais chegava
    a pilar nenhum - carga que some, com todos os gates dizendo OK. A escada
    agora e' dimensionada ANTES da descida e a sua reacao realimenta os lances.

    Hipoteses EXPLICITAS (nada arbitrado em silencio):
      - a escada declarada repete-se em cada pavimento: o peso que desce por
        nivel e' o de UM lance como dimensionado, vezes 'n_lances_por_pavimento'
        (default 1). Quem tem 2 lances de meio pe-direito por andar declara 2;
      - a reacao total do lance (W = (g+q).L.largura) e' dividida entre os
        'apoios' declarados (nomes de pilares); sem 'apoios', divide-se
        uniformemente entre TODOS os pilares e isso fica registrado em
        'distribuicao' - aproximacao conservadora no TOTAL, a refinar com apoios;
      - SEM 'largura' nao ha como calcular W: a carga e' INDEFINIDA, nao zero.
        Nesse caso devolve 'erro' e quem chama REPROVA o fechamento em vez de
        seguir com pilares mais leves (o padrao fail-closed do framework).
      - o q da escada so recebe o alpha_n de 6.12 se o uso for REDUTIVEL pela
        Tabela 10; q explicito ('informado explicitamente') nao reduz
        (conservador: sem Tabela, sem bonificacao)."""
    largura = r_escada.get("largura_m")
    if largura is None:
        return {"erro": ("escada sem 'largura' declarada: a reacao "
                         "(g+q).L.largura e' indefinida e nao pode descer aos "
                         "pilares; declare a largura para que o peso entre na "
                         "descida"),
                "W_g": 0.0, "W_q": 0.0}
    try:
        n_lances = int(cfg_escada.get("n_lances_por_pavimento", 1))
    except (TypeError, ValueError):
        return {"erro": ("'n_lances_por_pavimento' deve ser inteiro >= 1 "
                         "(recebido %r)" % (cfg_escada.get("n_lances_por_pavimento"),)),
                "W_g": 0.0, "W_q": 0.0}
    if n_lances < 1:
        return {"erro": "'n_lances_por_pavimento' deve ser >= 1",
                "W_g": 0.0, "W_q": 0.0}
    L = float(r_escada["vao_calculo_m"])
    W_g = float(r_escada["g_kN_m2"]) * L * float(largura) * n_lances
    W_q = float(r_escada["q_kN_m2"]) * L * float(largura) * n_lances
    uso = r_escada.get("uso", "")
    if uso in cg.CARGAS_USO:
        redutivel = bool(cg.CARGAS_USO[uso].get("redutivel", False))
    else:
        # q explicito, sem Tabela 10: sem bonificacao de 6.12
        redutivel = False
    apoios = cfg_escada.get("apoios")
    if apoios is not None:
        apoios = list(apoios)
    return {"W_g": round(W_g, 3), "W_q": round(W_q, 3), "uso": uso,
            "redutivel": redutivel, "largura_m": float(largura),
            "vao_m": round(L, 4), "n_lances_por_pavimento": n_lances,
            "apoios": apoios, "erro": None}


def _descer_escada(desc, stair):
    """Soma a reacao da escada aos lances da descida, pavimento a pavimento.

    Devolve o detalhe da distribuicao. A parcela variavel recebe o MESMO alpha_n
    do pavimento (quando o uso da escada for redutivel); a permanente desce
    integral. Os acumulados N_acum_k / N_base_* sao recompostos - nunca ajustados
    por diferenca, para nao carregar arredondamento lance a lance."""
    nomes = sorted(desc["pilares"])
    dest = list(stair["apoios"]) if stair["apoios"] else list(nomes)
    desconhecidos = [n for n in dest if n not in desc["pilares"]]
    if desconhecidos:
        raise ValueError("apoios da escada inexistentes na malha de pilares: %s "
                         "(pilares: %s)" % (", ".join(desconhecidos),
                                            ", ".join(nomes)))
    n_dest = len(dest)
    dg = stair["W_g"] / n_dest
    dq_bruto = stair["W_q"] / n_dest
    distribuicao = ("apoios declarados (%d pilares)" % n_dest if stair["apoios"]
                    else "uniforme entre os %d pilares (sem 'apoios' declarados)" % n_dest)
    for nome in dest:
        p = desc["pilares"][nome]
        acum_g = acum_q = 0.0
        for lance, pav in zip(p["lances"], desc["pavimentos"]):
            alpha = pav["alpha_n"] if stair["redutivel"] else 1.0
            dq = dq_bruto * alpha
            lance["N_g_pav"] = round(lance["N_g_pav"] + dg, 3)
            lance["N_q_pav_bruto"] = round(lance["N_q_pav_bruto"] + dq_bruto, 3)
            lance["N_q_pav_reduzido"] = round(lance["N_q_pav_reduzido"] + dq, 3)
            lance["N_aplicado"] = round(lance["N_aplicado"] + dg + dq, 3)
            lance["N_esc_g"] = round(lance.get("N_esc_g", 0.0) + dg, 3)
            lance["N_esc_q_bruto"] = round(lance.get("N_esc_q_bruto", 0.0) + dq_bruto, 3)
            lance["N_esc_q"] = round(lance.get("N_esc_q", 0.0) + dq, 3)
            acum_g += lance["N_g_pav"]
            acum_q += lance["N_q_pav_reduzido"]
            lance["N_acum_k"] = round(acum_g + acum_q, 2)
        bruto = sum(l["N_g_pav"] + l["N_q_pav_bruto"] for l in p["lances"])
        p["N_base_k"] = round(acum_g + acum_q, 2)
        p["N_base_g_k"] = round(acum_g, 2)
        p["N_base_q_k"] = round(acum_q, 2)
        p["N_base_sem_reducao_k"] = round(bruto, 2)
    return {"distribuicao": distribuicao, "pilares": dest,
            "W_g_por_pav_kN": round(stair["W_g"], 3),
            "W_q_por_pav_kN": round(stair["W_q"], 3)}


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
      'escada'    : opc, sub-spec de escada_concreto.dimensiona + chaves proprias:
                    'largura' OBRIGATORIA para a descida (sem ela a reacao e'
                    indefinida e o fechamento REPROVA); 'apoios' opc, lista de
                    pilares que recebem a escada (sem ele, distribui-se
                    uniformemente entre todos os pilares); 'n_lances_por_pavimento'
                    opc, default 1 (a escada declarada repete-se por pavimento);
      'fundacao'  : opc, sub-spec de fundacao_edificio.dimensiona (perfil_spt da
                    sondagem e/ou sigma_solo_adm). SEM ele nao ha fundacao - a
                    tensao do solo nunca e' arbitrada;
      'out_dir'   : opc - se dado, escreve a planta de formas (SVG).
    }"""
    geo = spec["geometria"]
    mat = spec["materiais"]
    laje = spec.get("laje", {})
    viga = spec.get("viga", {})
    fck, fyk = mat["fck"], mat["fyk"]

    def _tipo_para(uso, h_laje=None):
        d = {"vaos_x": geo["vaos_x"], "vaos_y": geo["vaos_y"],
             "h_laje": laje.get("h", 0.10) if h_laje is None else h_laje,
             "revestimento_kN_m2": laje.get("revestimento_kN_m2", 1.0),
             "uso": uso,
             "b_viga": viga.get("b", 0.20), "h_viga": viga.get("h", 0.50),
             "fck": fck, "fyk": fyk, "pe_direito": geo["pe_direito"]}
        if spec.get("parede_sobre_vigas"):
            d["parede_sobre_vigas"] = spec["parede_sobre_vigas"]
        if spec.get("parede_sem_posicao_pp"):
            d["parede_sem_posicao_pp"] = spec["parede_sem_posicao_pp"]
        return d

    # -------------------------------- PAVIMENTO-TIPO + LAJE (ponto fixo em h)
    # `dimensiona_laje` ADOTA a menor espessura que atende, que pode ser MAIOR
    # que a declarada. Se a cadeia seguisse com a espessura declarada, vigas,
    # pilares e fundacao seriam dimensionados para o peso proprio de uma laje
    # que nao e' a que vai ser construida - carga permanente subestimada em
    # 25 kN/m3 x delta_h, com todos os gates dizendo OK. Entao a espessura
    # adotada REALIMENTA a carga, e o laco repete ate a espessura parar de
    # crescer (`dimensiona_laje` so sobe na lista finita de espessuras, logo o
    # ponto fixo e' alcancado; MAX_ITER_LAJE e' um teto de seguranca, e nao
    # atingi-lo vira gate REPROVADO, nunca um resultado dado por bom).
    h_laje = laje.get("h", 0.10)
    h_declarada = h_laje
    iteracoes = 0
    convergiu = False
    por_uso, pavs, pav, r_laje = {}, [], None, None
    for iteracoes in range(1, MAX_ITER_LAJE + 1):
        por_uso, pavs = {}, []
        for pv in spec["pavimentos"]:
            uso = pv["uso"]
            if uso not in por_uso:
                por_uso[uso] = _tipo_para(uso, h_laje)
            pavs.append({"nome": pv["nome"], "pavimento": por_uso[uso],
                         "pe_direito": geo["pe_direito"]})
        pav = pt.monta(por_uso[spec["pavimentos"][-1]["uso"]])
        crit = max(pav["paineis"], key=lambda p: p["lx"] * p["ly"])
        r_laje = lj.dimensiona_laje({
            "caso": crit["caso"], "lx": min(crit["lx"], crit["ly"]),
            "ly": max(crit["lx"], crit["ly"]), "h": h_laje,
            "g": pav["g_kN_m2"], "q": pav["q_kN_m2"], "fck": fck, "fyk": fyk})
        if r_laje["h"] <= h_laje + 1e-9:
            convergiu = True
            break
        h_laje = r_laje["h"]
    fech = pt.verifica_fechamento(pav)

    # --------------------------------------------------------------- ESCADA
    # G38: a escada e' dimensionada ANTES da descida porque a sua reacao
    # REALIMENTA os lances. Antes ela era calculada depois (a reacao so
    # existia a partir daqui) e o peso dela jamais descia para pilar nenhum:
    # entrava no gate 'escada', saia no relatorio, e sumia da estrutura.
    r_escada = None
    stair = None
    escada_erro = None
    detalhe_escada = None
    if spec.get("escada"):
        import escada_concreto as ec
        e = dict(spec["escada"])
        e.setdefault("fck", fck)
        e.setdefault("fyk", fyk)
        e.setdefault("desnivel", geo["pe_direito"] / 2.0)
        r_escada = ec.dimensiona(e)
        stair = _carga_escada_por_pavimento(r_escada, spec["escada"])
        if stair.get("erro"):
            # carga INDEFINIDA (sem largura): nao ha o que descer, e seguir com
            # os pilares mais leves seria repetir o G38 de outro jeito
            escada_erro = stair["erro"]
            stair = None

    # -------------------------------------------------------- DESCIDA (6.12)
    desc = dc.descer({"pavimentos": pavs, "elemento": "pilar"})
    if stair is not None:
        detalhe_escada = _descer_escada(desc, stair)
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

    # ---------------------------------------------------------------- VIGAS
    # G34: TODA viga, TODO tramo VERIFICADO (nao so analisado). `pavimento_tipo`
    # entrega a envoltoria (14.6.6) mas nao confere a secao. Aqui cada tramo
    # passa por `viga_concreto.verifica_viga` com M_d/M_d_neg/V_d da envoltoria
    # (o mesmo padrao da casa em `estrutura_casa.verifica_vigas`): flexao M+/M-,
    # cortante, ancoragem, flecha Tab.13.3 e fissuracao. O M- da envoltoria e'
    # passado explicitamente porque o w.L2/10 de tabela e' MENOR que o w.L2/8 de
    # um apoio interno de dois vaos.
    vigas = list(pav["vigas_x"]) + list(pav["vigas_y"])
    vigas_ok_env = all(v["OK"] for v in vigas)
    r_vigas = ec_vigas.verifica_vigas(pav, fck, fyk,
                                      com_alvenaria=pav["g_parede_kN_m"] > 0)
    vigas_ok = bool(r_vigas["OK"] and vigas_ok_env)

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
    momentos_base = None
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
        # G17 - momento na base por prumada (heterogeneo, secao bruta).
        # Nao reusa o modelo uniforme/reduzido de gamma_z para M_base: vide
        # estabilidade_edificio._portico_plano_heterogeneo docstring.
        try:
            pilares_mom = []
            for nome in sorted(desc["pilares"]):
                registro = next(x for x in pav["pilares"] if x["nome"] == nome)
                lance_base = pilares[nome]["lances"][-1]
                pilares_mom.append({
                    "nome": nome, "i": registro["i"], "j": registro["j"],
                    "posicao": registro["posicao"],
                    "secao": (lance_base["b"], lance_base["h"]),
                })
            spec_mom = {
                "geometria": geo, "n_pavimentos": len(pavs),
                "materiais": {"fck": fck},
                "secoes": {"viga": {"b": viga.get("b", 0.20),
                                    "h": viga.get("h", 0.50)}},
                "cargas_verticais_kN": cargas_k,
                "vento": spec["vento"],
                "lajes_lisas": bool(spec.get("lajes_lisas")),
            }
            momentos_base = ee.momentos_base_por_pilar(spec_mom, pilares_mom,
                                                       estabilidade)
            estabilidade["momentos_base"] = momentos_base
        except Exception as exc:  # noqa: BLE001
            # momento nao extraido nao derruba estabilidade; vira erro nomeado
            estabilidade["momentos_base_erro"] = "%s: %s" % (type(exc).__name__, exc)

    # ------------------------------------------------------------- FUNDACAO
    # A descida sempre entregou N_base por pilar e ninguem o dimensionava. Agora
    # dimensiona - mas SO com sondagem (ou tensao) DECLARADA: sem isso a
    # fundacao continua ausente e o escopo continua dizendo not_available, em vez
    # de uma sapata assentada numa tensao de solo arbitrada.
    fundacao = None
    erro_fundacao = None
    if fe.declarada(spec.get("fundacao")):
        pilares_fund = []
        for nome in sorted(desc["pilares"]):
            registro = next(x for x in pav["pilares"] if x["nome"] == nome)
            lance_base = pilares[nome]["lances"][-1]
            pilares_fund.append({
                "nome": nome, "i": registro["i"], "j": registro["j"],
                "posicao": registro["posicao"],
                "N_base_k": desc["pilares"][nome]["N_base_k"],
                # a fundacao recebe a secao do lance da BASE - e' ela que define
                # o balanco da sapata e a rigidez de 22.6.1
                "secao": (lance_base["b"], lance_base["h"]),
            })
        try:
            fundacao = fe.dimensiona(spec["fundacao"], {
                "pilares": pilares_fund,
                "eixos_x": _eixos(geo["vaos_x"]),
                "eixos_y": _eixos(geo["vaos_y"]),
                "materiais": {"fck": fck, "fyk": fyk},
                "estabilidade": estabilidade,
                "momentos_base": momentos_base})
        except fe.EntradaFundacao as exc:
            # entrada declarada que nao permite dimensionar e' REPROVACAO com
            # motivo, nunca uma fundacao silenciosamente ausente.
            erro_fundacao = str(exc)

    # ------------------------------------------------- G18: VIGA BALDRAME + RECALQUE
    # Fronteiras dentro da fundacao (ESCOPO_FUNDACAO_ABERTO). O G9 entregou a
    # sapata/bloco/estaca mas deixou baldrame e recalque como not_available.
    # O G18 fecha a fronteira: quando a parede (q_parede/parede) e a secao sao
    # declaradas, o baldrame e' verificado via viga_baldrame.py (ELU + ELS
    # Tab 13.3); quando Es e' declarado, o recalque elastico por pilar e o
    # diferencial max-min sao calculados via geotecnia_spt / fundacao_sapata.
    # N_amarracao vem da fundacao (max|V| das combinacoes, G23); recalque usa
    # N_dimensionamento caracteristico (G23 pode alimentar N_serv distinto).
    baldrame = None
    baldrame_erro = None
    recalque = None
    recalque_erro = None
    # baldrame
    try:
        import viga_baldrame_edificio as vbe
        if vbe.declarada(spec.get("fundacao")):
            if fundacao is None:
                # Declarado mas sem fundacao dimensionada: nao ha base a amarrar.
                # Erro nomeado, nunca baldrame inventado sem chao.
                raise vbe.EntradaBaldrame(
                    "viga_baldrame declarada mas fundacao nao dimensionada (sem sondagem/tensao): sem fundacao nao ha baldrame a amarrar")
            # Contexto para o baldrame: malha e fundacao (para N_amarracao)
            baldrame = vbe.dimensiona(spec["fundacao"], {
                "vaos_x": geo["vaos_x"], "vaos_y": geo["vaos_y"],
                "eixos_x": _eixos(geo["vaos_x"]), "eixos_y": _eixos(geo["vaos_y"]),
                "pilares": pilares_fund,
                "fundacao": fundacao,
                "materiais": {"fck": fck, "fyk": fyk},
                "estabilidade": estabilidade,
                "momentos_base": momentos_base})
    except Exception as exc:  # noqa: BLE001
        # So registra erro se baldrame foi declarado; caso contrario e' not_available silencioso.
        try:
            import viga_baldrame_edificio as vbe2
            if vbe2.declarada(spec.get("fundacao")):
                baldrame_erro = "%s: %s" % (type(exc).__name__, exc)
        except Exception:  # noqa: BLE001
            pass
    # recalque diferencial
    try:
        import recalque_edificio as rce
        if rce.declarada(spec.get("fundacao")):
            if fundacao is None:
                raise rce.EntradaRecalque(
                    "recalque declarado mas fundacao nao dimensionada (sem sondagem/tensao): sem fundacao nao ha recalque a calcular")
            recalque = rce.calcula(spec["fundacao"], fundacao, {
                "eixos_x": _eixos(geo["vaos_x"]), "eixos_y": _eixos(geo["vaos_y"]),
                "vaos_x": geo["vaos_x"], "vaos_y": geo["vaos_y"],
                "pilares": pilares_fund})
    except Exception as exc:  # noqa: BLE001
        try:
            import recalque_edificio as rce2
            if rce2.declarada(spec.get("fundacao")):
                recalque_erro = "%s: %s" % (type(exc).__name__, exc)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------ ELS DE VIBRACAO (Anexo L)
    # Fecha o item `vibracao_piso`, aberto desde a auditoria de gaps do G2.
    # A viga critica NAO e' a de maior vao e sim a de maior w_freq * L^4, que e'
    # a grandeza a que a flecha biapoiada e' proporcional: com carregamentos
    # diferentes por linha (as de contorno levam parede), o vao maior nem sempre
    # e o que mais flecha.
    uso_tipo = spec["pavimentos"][-1]["uso"]
    classe_vib, linha_vib = vib.classifica(uso_tipo)
    viga_vib = None
    if classe_vib in (None, vib.CLASSE_NAO_APLICAVEL):
        # sem classe (ou sem criterio aplicavel) nao ha o que calcular; o proprio
        # modulo devolve o registro nomeado em vez de um OK mudo.
        vibracao = vib.verifica({"uso": uso_tipo, "fck": fck, "g": pav["g_kN_m2"],
                                 "q": pav["q_kN_m2"], "laje": {}, "viga": {}})
    else:
        p1 = vib.psi_1(linha_vib)
        crit_v, crit_k, crit_sev = None, 0, -1.0
        for v in list(pav["vigas_x"]) + list(pav["vigas_y"]):
            for k, Lk in enumerate(v["vaos"]):
                sev = (v["g_tramos"][k] + p1 * v["q_tramos"][k]) * Lk ** 4
                if sev > crit_sev:
                    crit_sev, crit_v, crit_k = sev, v, k
        L_v = crit_v["vaos"][crit_k]
        # a armadura REAL do tramo critico: sem ela a flecha so poderia sair de
        # secao bruta, que subestima assim que a viga fissura. M_positivo da
        # analise e CARACTERISTICO (viga_continua nao pondera), dai o gamma_f.
        rv = vgc.verifica_viga({"vao": L_v, "b": crit_v["b"], "h": crit_v["h"],
                                "fck": fck, "fyk": fyk,
                                "M_d": 1.4 * crit_v["M_positivo"][crit_k],
                                "V_d": 1.4 * crit_v["V_max"][crit_k]})
        viga_vib = {"linha": crit_v["nome"], "tramo": crit_k + 1, "L": L_v,
                    "As_cm2": rv["As_inf_cm2"]}
        gn_l, p_k_l = r_laje["gamma_n"], r_laje["p_k"]
        M_k_laje = abs(r_laje["momentos"]["m_x"]) / (1.4 * gn_l)
        p_freq_laje = pav["g_kN_m2"] + p1 * pav["q_kN_m2"]
        vibracao = vib.verifica({
            "uso": uso_tipo, "fck": fck,
            "g": pav["g_kN_m2"], "q": pav["q_kN_m2"],
            "laje": {"caso": r_laje["caso"], "lx": r_laje["lx"],
                     "ly": r_laje["ly"], "h": r_laje["h"], "d": r_laje["d"],
                     "As_m2": r_laje["armaduras"]["m_x"]["As_adotada"],
                     "M_servico": (M_k_laje * p_freq_laje / p_k_l
                                   if p_k_l else M_k_laje)},
            "viga": {"L": L_v, "b": crit_v["b"], "h": crit_v["h"], "d": rv["d"],
                     "As_m2": rv["As_inf_cm2"] * 1e-4,
                     "g_kN_m": crit_v["g_tramos"][crit_k],
                     "q_kN_m": crit_v["q_tramos"][crit_k]},
            "f_n_Hz": (spec.get("vibracao") or {}).get("f_n_Hz")})
    if viga_vib:
        vibracao["viga_critica"] = viga_vib

    # ------------------------------------------- DESEMPENHO NBR 15575
    # A 15575 so e' exigivel para edificacao HABITACIONAL, e ela traz limites
    # MAIS RESTRITIVOS que a 6118 em varios pontos - um predio residencial
    # passava em todos os gates deste framework e reprovaria na 15575.
    # `habitacional` e deduzido dos usos da Tabela 10 da NBR 6120 (que sao dado
    # declarado, nao arbitrado) e pode ser sobreposto no spec.
    habitacional = spec.get("habitacional")
    if habitacional is None:
        habitacional = any(pv["uso"].startswith("residencial_") or pv["uso"] == "sotao"
                           for pv in spec["pavimentos"])
    cfg15575 = {"habitacional": bool(habitacional)}
    H_total = len(pavs) * geo["pe_direito"]
    if estabilidade is not None:
        cfg15575["topo"] = {"u_m": estabilidade["els"]["u_topo_m"],
                            "H_total_m": H_total,
                            "u_norma_m": estabilidade["els"]["limite_topo_m"]}
    if r_laje.get("fissuracao"):
        cfg15575["fissura"] = {"wk_mm": r_laje["fissuracao"]["wk_mm"],
                               "wk_lim_norma_mm": r_laje["fissuracao"]["wk_lim_mm"]}
    linha_fl = (spec.get("desempenho") or {}).get("linha_flecha")
    if linha_fl:
        # A Tabela 2 tem combinacao PROPRIA (Sgk + 0,7 Sqk) e convencao PROPRIA
        # de flecha final (rigidez pela metade, nota c) - nenhuma das duas e a
        # que a laje ja calculou para a Tabela 13.3 da 6118. Recalcular e o que
        # impede comparar a flecha de uma combinacao com o limite de outra.
        p_155 = pav["g_kN_m2"] + des.PSI_TAB2 * pav["q_kN_m2"]
        gn_l, p_k_l = r_laje["gamma_n"], r_laje["p_k"]
        M_k_laje = abs(r_laje["momentos"]["m_x"]) / (1.4 * gn_l)
        fl155 = lj.flecha_laje(
            r_laje["caso"], r_laje["lx"], r_laje["ly"], p_155, r_laje["h"], fck,
            As_tracao=r_laje["armaduras"]["m_x"]["As_adotada"],
            M_servico=(M_k_laje * p_155 / p_k_l if p_k_l else M_k_laje),
            d=r_laje["d"])
        cfg15575["flechas"] = [
            {"nome": "laje do pavimento-tipo (imediata)", "linha": linha_fl,
             "coluna": "Sgk+0,7Sqk", "L": r_laje["lx"],
             "flecha_m": fl155["f_imediata"]},
            {"nome": "laje do pavimento-tipo (final)", "linha": linha_fl,
             "coluna": "final", "L": r_laje["lx"],
             "flecha_m": des.flecha_final(fl155["f_imediata"]),
             "lim_norma_m": r_laje["lim_flecha"]}]
    desempenho = des.verifica(cfg15575)

    # ---------------- FECHAMENTO DO EDIFICIO CONTRA A CARGA DECLARADA (G38)
    # O gate antigo fechava o total DO QUE FOI INCLUIDO: `verifica_fechamento`
    # confere UM pavimento-tipo contra a sua propria carga, entao a escada -
    # que nunca entrava nem no pavimento nem na descida - era invisivel por
    # construcao. E' o irmao do achado do G3 (la o total fechava e a carga ia
    # para o pilar errado; aqui o total fecha e a carga nunca existiu).
    # O fechamento agora confere a BASE DA DESCIDA (bruta, sem reducao de 6.12)
    # contra a carga DECLARADA: a soma dos N_total_k de cada pavimento (cada
    # uso com o seu montante) MAIS o peso bruto total da escada. Se a escada
    # foi declarada sem largura (reacao indefinida), o fechamento REPROVA em
    # vez de fechar sem ela.
    montados_fech = {}
    for _pv in spec["pavimentos"]:
        _uso = _pv["uso"]
        if _uso not in montados_fech:
            montados_fech[_uso] = (
                pav if por_uso[_uso] is por_uso[spec["pavimentos"][-1]["uso"]]
                else pt.monta(por_uso[_uso]))
    esperado_pavs = sum(montados_fech[_pv["uso"]]["N_total_k"]
                        for _pv in spec["pavimentos"])
    escada_bruto_total = 0.0
    if stair is not None:
        escada_bruto_total = len(pavs) * (stair["W_g"] + stair["W_q"])
    elif spec.get("escada"):
        escada_bruto_total = 0.0  # indefinida: o gate reprova abaixo, nao soma zero
    esperado_total = esperado_pavs + escada_bruto_total
    N_desc_total = sum(p["N_base_sem_reducao_k"] for p in desc["pilares"].values())
    erro_total = (abs(N_desc_total - esperado_total) / esperado_total
                  if esperado_total > 0 else 0.0)
    fechamento_ok = bool(fech["ok"] and erro_total <= 0.02 and escada_erro is None)

    # ---------------------------------------------------------------- GATES
    gates = {
        "fechamento_carga": {"OK": fechamento_ok, "erro_rel": fech["erro_rel"],
                             "N_pilares": fech["N_pilares"],
                             "esperado": fech["carga_esperada"],
                             "N_desc_total_k": round(N_desc_total, 2),
                             "esperado_total_k": round(esperado_total, 2),
                             "erro_total": round(erro_total, 5),
                             "escada_total_kN": round(escada_bruto_total, 2),
                             "escada_distribuicao": (detalhe_escada["distribuicao"]
                                                     if detalhe_escada else None),
                             "escada_erro": escada_erro},
        "reducao_6120": {"OK": red["ok"], "reduzidos": red["reduzidos"],
                         "alivio_pct": red["alivio_pct_max"],
                         "violacoes": red["violacoes"]},
        "pilares": {"OK": not erros_pilar, "reprovados": erros_pilar,
                    "n": len(pilares)},
        "laje": {"OK": bool(r_laje.get("OK")), "h_cm": r_laje.get("h", 0) * 100},
        # a carga que desceu foi calculada com a espessura que a laje ADOTOU
        "laje_compatibilizada": {
            "OK": convergiu and abs(pav["h_laje_usada"] - r_laje["h"]) <= 1e-9,
            "h_declarada_cm": h_declarada * 100,
            "h_adotada_cm": r_laje["h"] * 100,
            "h_na_carga_cm": pav["h_laje_usada"] * 100,
            "iteracoes": iteracoes},
        "vigas": {"OK": vigas_ok, "n": len(vigas),
                  "n_linhas": len(r_vigas["por_linha"]),
                  "n_tramos": r_vigas["n_tramos"],
                  "reprovadas": ([v["nome"] for v in vigas if not v["OK"]]
                                  + list(r_vigas["reprovados"]))},
        # ELS de vibracao (NBR 8800 Anexo L). `aplicavel` False (cobertura, forro)
        # sai OK - nao ha criterio - mas fica NOMEADO no gate, nunca omitido.
        "vibracao_piso": {
            "OK": bool(vibracao["OK"]), "classe": vibracao.get("classe"),
            "aplicavel": vibracao.get("aplicavel"),
            "avaliacao": vibracao.get("avaliacao"),
            "d_total_mm": vibracao.get("d_total_mm"),
            "d_lim_mm": vibracao.get("d_lim_mm"),
            "f_n_Hz": vibracao.get("f_n_Hz"),
            "motivo": vibracao.get("motivo")},
        # Desempenho NBR 15575. `nao_verificados` viaja no gate porque a 15575
        # exige mais do que este framework calcula (carga concentrada de 1 kN da
        # parte 3, fachada da parte 4): o que nao foi verificado tem de aparecer
        # em vez de ser confundido com aprovado.
        "desempenho_15575": {
            "OK": bool(desempenho["OK"]), "aplicavel": desempenho["aplicavel"],
            "completo": desempenho["completo"],
            "reprovados": desempenho["reprovados"],
            "nao_verificados": desempenho["nao_verificados"]},
    }
    if fundacao is not None:
        gates["fundacao"] = dict(fundacao["gate"])
    elif erro_fundacao is not None:
        gates["fundacao"] = {"OK": False, "erro": erro_fundacao}
    # G18: baldrame e recalque entram como gates proprios quando declarados
    if baldrame is not None:
        gates["viga_baldrame"] = {"OK": bool(baldrame["gate"]["OK"]),
                                  "secao": baldrame["secao"],
                                  "fechamento_ok": baldrame["gate"]["fechamento_ok"],
                                  "N_amarracao_kN": baldrame["N_amarracao_kN"]}
    elif baldrame_erro is not None:
        gates["viga_baldrame"] = {"OK": False, "erro": baldrame_erro}
    if recalque is not None:
        gates["recalque_diferencial"] = {"OK": bool(recalque["gate"]["OK"]),
                                         "recalque_max_mm": recalque.get("recalque_max_mm"),
                                         "diferencial_mm": recalque.get("diferencial_mm"),
                                         "distorcao_L": recalque.get("distorcao_L")}
    elif recalque_erro is not None:
        gates["recalque_diferencial"] = {"OK": False, "erro": recalque_erro}
    if r_escada is not None:
        gates["escada"] = {
            "OK": bool(r_escada["OK"]) and escada_erro is None,
            "desceu_aos_pilares": detalhe_escada is not None,
            "W_g_por_pav_kN": (stair["W_g"] if stair is not None else None),
            "W_q_por_pav_kN": (stair["W_q"] if stair is not None else None),
            "distribuicao": (detalhe_escada["distribuicao"]
                             if detalhe_escada else None),
            "erro": escada_erro}
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
        "laje": r_laje, "vigas": vigas, "vigas_verificacao": r_vigas,
        "escada": r_escada, "planta": planta,
        "escada_descida": detalhe_escada, "escada_erro": escada_erro,
        "fundacao": fundacao, "fundacao_erro": erro_fundacao,
        "estabilidade": estabilidade,
        "momentos_base": momentos_base,
        "vibracao": vibracao, "desempenho": desempenho,
        "H_total_m": H_total,
        "n_pavimentos": len(pavs),
        "h_laje_adotada": r_laje["h"], "h_laje_declarada": h_declarada,
        "N_base_max_k": max(p["N_base_k"] for p in pilares.values()),
        "registro_6120": desc["registro_6120"],
        "viga_baldrame": baldrame,
        "viga_baldrame_erro": baldrame_erro,
        "recalque_diferencial": recalque,
        "recalque_erro": recalque_erro,
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
          "  VIGAS CONTINUAS: %d linhas / %d tramos VERIFICADOS -> %s"
          % (g["vigas"]["n"], g["vigas"].get("n_tramos", 0),
             "ATENDE" if g["vigas"]["OK"]
             else "REPROVA em " + ", ".join(g["vigas"]["reprovadas"])),
          "  PILARES CONTINUOS: %d -> %s"
          % (g["pilares"]["n"], "ATENDE" if g["pilares"]["OK"]
             else "REPROVA em " + ", ".join(g["pilares"]["reprovados"]))]
    if "escada" in g:
        if g["escada"].get("desceu_aos_pilares"):
            L.append("  ESCADA DE CONCRETO: %s (%.1f kN por pav x %d pavs = "
                     "%.1f kN desceram aos pilares; %s)"
                     % ("ATENDE" if g["escada"]["OK"] else "REPROVA",
                        (g["escada"]["W_g_por_pav_kN"] or 0.0)
                        + (g["escada"]["W_q_por_pav_kN"] or 0.0),
                        r["n_pavimentos"],
                        g["fechamento_carga"]["escada_total_kN"],
                        g["escada"]["distribuicao"]))
        elif g["escada"].get("erro"):
            L.append("  ESCADA DE CONCRETO: REPROVA - %s" % g["escada"]["erro"])
        else:
            L.append("  ESCADA DE CONCRETO: %s" % ("ATENDE" if g["escada"]["OK"]
                                                   else "REPROVA"))
    if "estabilidade_horizontal" in g:
        eh = g["estabilidade_horizontal"]
        L.append("  ESTABILIDADE HORIZONTAL: gamma_z = %.3f (%s, direcao %s) ; "
                 "ELS topo H/%.0f -> %s"
                 % (eh["gamma_z"], "nos " + eh["nos"], eh["direcao_critica"],
                    eh["H_sobre_u_topo"], "ATENDE" if eh["OK"] else "REPROVA"))
    vb_ = g["vibracao_piso"]
    if not vb_.get("aplicavel"):
        L.append("  VIBRACAO DE PISO: criterio do Anexo L nao aplicavel a este uso")
    elif vb_.get("d_total_mm") is None:
        # uso sem classe do Anexo L: nao ha limite a aplicar e, portanto, nao ha
        # deslocamento a exibir - imprimir 0,0 mm sugeriria um piso rigidissimo.
        L.append("  VIBRACAO DE PISO: uso NAO CLASSIFICADO no Anexo L -> REPROVA")
    else:
        L.append("  VIBRACAO DE PISO (NBR 8800 Anexo L, %s): %.1f mm <= %.0f mm "
                 "-> %s" % (vb_["classe"], vb_["d_total_mm"], vb_["d_lim_mm"],
                            "ATENDE" if vb_["OK"] else "REPROVA"))
    d15_ = g["desempenho_15575"]
    if d15_["aplicavel"]:
        L.append("  DESEMPENHO NBR 15575: %s%s"
                 % ("ATENDE" if d15_["OK"] else
                    "REPROVA em " + ", ".join(d15_["reprovados"]),
                    "" if d15_["completo"] else
                    " (NAO verificados: %s)" % ", ".join(d15_["nao_verificados"])))
    else:
        L.append("  DESEMPENHO NBR 15575: nao aplicavel (edificacao nao habitacional)")
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
          "   do acervo). Os requisitos da NBR 15575 que se verificam por ENSAIO",
          "   (impacto de corpo mole/duro, carga concentrada de 1 kN da parte 3 e",
          "   deslocamento residual de fachada da parte 4) nao sao calculados aqui.]"]
    return "\n".join(L)
